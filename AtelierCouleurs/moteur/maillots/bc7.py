"""Décodeur BC7 (DDS DX10, DXGI 98/99) en Python pur + écriture PNG."""
import struct, zlib

P2 = [0xCCCC,0x8888,0xEEEE,0xECC8,0xC880,0xFEEC,0xFEC8,0xEC80,0xC800,0xFFEC,0xFE80,0xE800,0xFFE8,0xFF00,0xFFF0,0xF000,
      0xF710,0x008E,0x7100,0x08CE,0x008C,0x7310,0x3100,0x8CCE,0x088C,0x3110,0x6666,0x366C,0x17E8,0x0FF0,0x718E,0x399C,
      0xAAAA,0xF0F0,0x5A5A,0x33CC,0x3C3C,0x55AA,0x9696,0xA55A,0x73CE,0x13C8,0x324C,0x3BDC,0x6996,0xC33C,0x9966,0x0660,
      0x0272,0x04E4,0x4E40,0x2720,0xC936,0x936C,0x39C6,0x639C,0x9336,0x9CC6,0x817E,0xE718,0xCCF0,0x0FCC,0x7744,0xEE22]
P3 = [0xaa685050,0x6a5a5040,0x5a5a4200,0x5450a0a8,0xa5a50000,0xa0a05050,0x5555a0a0,0x5a5a5050,
      0xaa550000,0xaa555500,0xaaaa5500,0x90909090,0x94949494,0xa4a4a4a4,0xa9a59450,0x2a0a4250,
      0xa5945040,0x0a425054,0xa5a5a500,0x55a0a0a0,0xa8a85454,0x6a6a4040,0xa4a45000,0x1a1a0500,
      0x0050a4a4,0xaaa59090,0x14696914,0x69691400,0xa08585a0,0xaa821414,0x50a4a450,0x6a5a0200,
      0xa9a58000,0x5090a0a8,0xa8a09050,0x24242424,0x00aa5500,0x24924924,0x24499224,0x50a50a50,
      0x500aa550,0xaaaa4444,0x66660000,0xa5a0a5a0,0x50a050a0,0x69286928,0x44aaaa44,0x66666600,
      0xaa444444,0x54a854a8,0x95809580,0x96969600,0xa85454a8,0x80959580,0xaa141414,0x96960000,
      0xaaaa1414,0xa05050a0,0xa0a5a5a0,0x96000000,0x40804080,0xa9a8a9a8,0xaaaaaa44,0x2a4a5254]
A2 = [15,15,15,15,15,15,15,15,15,15,15,15,15,15,15,15,15,2,8,2,2,8,8,15,2,8,2,2,8,8,2,2,
      15,15,6,8,2,8,15,15,2,8,2,2,2,15,15,6,6,2,6,8,15,15,2,2,15,15,15,15,15,2,2,15]
A3a = [3,3,15,15,8,3,15,15,8,8,6,6,6,5,3,3,3,3,8,15,3,3,6,10,5,8,8,6,8,5,15,15,
       8,15,3,5,6,10,8,15,15,3,15,5,15,15,15,15,3,15,5,5,5,8,5,10,5,10,8,13,15,12,3,3]
A3b = [15,8,8,3,15,15,3,8,15,15,15,15,15,15,15,8,15,8,15,3,15,8,15,8,3,15,6,10,15,15,10,8,
       15,3,15,10,10,8,9,10,6,15,8,15,3,6,6,8,15,3,15,15,15,15,15,15,15,15,15,15,3,15,15,8]
W = {2: [0,21,43,64], 3: [0,9,18,27,37,46,55,64], 4: [0,4,9,13,17,21,26,30,34,38,43,47,51,55,60,64]}
# NS PB RB ISB CB AB EPB SPB IB IB2
MODES = [(3,4,0,0,4,0,1,0,3,0),(2,6,0,0,6,0,0,1,3,0),(3,6,0,0,5,0,0,0,2,0),(2,6,0,0,7,0,1,0,2,0),
         (1,0,2,1,5,6,0,0,2,3),(1,0,2,0,7,8,0,0,2,2),(1,0,0,0,7,7,1,0,4,0),(2,6,0,0,5,5,1,0,2,0)]

def _expand(v, n):
    v <<= (8 - n)
    return v | (v >> n)

def block(b):
    x = int.from_bytes(b, 'little')
    if x == 0:
        return [(0, 0, 0, 0)] * 16
    mode = (x & -x).bit_length() - 1
    if mode > 7:
        return [(0, 0, 0, 0)] * 16
    pos = mode + 1
    def rd(n):
        nonlocal pos
        v = (x >> pos) & ((1 << n) - 1); pos += n; return v
    NS, PB, RB, ISB, CB, AB, EPB, SPB, IB, IB2 = MODES[mode]
    part = rd(PB); rot = rd(RB); isel = rd(ISB)
    ne = NS * 2
    ep = [[0, 0, 0, 255] for _ in range(ne)]
    for c in range(3):
        for i in range(ne): ep[i][c] = rd(CB)
    if AB:
        for i in range(ne): ep[i][3] = rd(AB)
    cb, ab = CB, AB
    if EPB:
        for i in range(ne):
            p = rd(1)
            for c in range(4 if AB else 3): ep[i][c] = (ep[i][c] << 1) | p
        cb += 1; ab += 1 if AB else 0
    elif SPB:
        for s in range(NS):
            p = rd(1)
            for i in (2 * s, 2 * s + 1):
                for c in range(4 if AB else 3): ep[i][c] = (ep[i][c] << 1) | p
        cb += 1; ab += 1 if AB else 0
    for i in range(ne):
        for c in range(3): ep[i][c] = _expand(ep[i][c], cb)
        ep[i][3] = _expand(ep[i][3], ab) if AB else 255
    if NS == 1:
        sub = [0] * 16; anchors = {0}
    elif NS == 2:
        m = P2[part]; sub = [(m >> i) & 1 for i in range(16)]; anchors = {0, A2[part]}
    else:
        m = P3[part]; sub = [(m >> (2 * i)) & 3 for i in range(16)]; anchors = {0, A3a[part], A3b[part]}
    idx = []
    for i in range(16): idx.append(rd(IB - 1 if i in anchors else IB))
    idx2 = None
    if IB2:
        idx2 = []
        for i in range(16): idx2.append(rd(IB2 - 1 if i == 0 else IB2))
    out = []
    for i in range(16):
        s = sub[i]; e0, e1 = ep[2 * s], ep[2 * s + 1]
        if idx2 is None:
            w = W[IB][idx[i]]; wa = w
        elif isel:
            w = W[IB2][idx2[i]]; wa = W[IB][idx[i]]
        else:
            w = W[IB][idx[i]]; wa = W[IB2][idx2[i]]
        r = ((64 - w) * e0[0] + w * e1[0] + 32) >> 6
        g = ((64 - w) * e0[1] + w * e1[1] + 32) >> 6
        bb = ((64 - w) * e0[2] + w * e1[2] + 32) >> 6
        a = ((64 - wa) * e0[3] + wa * e1[3] + 32) >> 6
        if rot == 1: r, a = a, r
        elif rot == 2: g, a = a, g
        elif rot == 3: bb, a = a, bb
        out.append((r, g, bb, a))
    return out

