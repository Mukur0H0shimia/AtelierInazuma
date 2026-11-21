"""Brouillard du jeu pour le rendu Direct3D : portage EXACT (flottants 32 bits) de nie.exe 0x140f7f050 (13/11/2026).
Entrée : CLightData +0x540…+0x61F (14 float4 bruts : fogRayleighColorP20/P10/O00/M10/M20, fogHeightRayleighColor,
fogMieColorP20/O00/M20, fogWorld*, fogHeight*, fogRayleighBandRatio). Sortie : les mêmes 0xE0 octets convertis, que le jeu
écrit dans CBUSE_UB_CAMERA_IDX (cb5) à +0x250 (registres cb5[37…50]). Vérifié contre le jeu : nie_outils/test_brouillard.py."""
import struct

_F = lambda x: struct.unpack('<f', struct.pack('<f', x))[0]
SEUIL = _F(0.01)                       # 0x141a7cb2c
K = _F(-9.999999747378752e-06)         # 0x141a7d244
C255 = _F(0.003921568859368563)        # 0x141a7cb04
C1003 = _F(1.003937005996704)          # 0x141a7cd54


def convertir(brut):
    f = list(struct.unpack('<56f', brut[:0xE0]))
    o = list(f)                                         # copie de tout (0x140f7f050 : param_2[0..0x1b])
    m = lambda a, b: _F(a * b)
    k = f[3]                                            # Rayleigh : P20 x w, w²
    o[0:4] = [m(k, f[0]), m(k, f[1]), m(k, f[2]), m(k, k)]
    der = 0
    for i in range(1, 5):
        w = f[4 * i + 3]
        if w < SEUIL:
            o[4 * i:4 * i + 4] = o[4 * der:4 * der + 4]
            continue
        o[4 * i:4 * i + 4] = [m(k, f[4 * i]), m(k, f[4 * i + 1]), m(k, f[4 * i + 2]), m(w, k)]
        n = i - der
        if n > 1:
            pas = _F(1.0 / _F(float(n)))
            for j in range(1, n):
                t = _F(_F(float(j)) * pas)
                o[4 * (der + j):4 * (der + j) + 4] = [_F(_F(_F(o[4 * i + q] - o[4 * der + q]) * t) + o[4 * der + q]) for q in range(4)]
        der = i
    k = f[23]                                           # couleur Rayleigh de hauteur
    o[20:24] = [m(k, f[20]), m(k, f[21]), m(k, f[22]), m(k, k)]
    k = f[27]                                           # Mie P20 / O00 / M20
    o[24:28] = [m(k, f[24]), m(k, f[25]), m(k, f[26]), m(k, k)]
    if f[31] < SEUIL:
        o[28:32] = o[24:28]; src = 24
    else:
        o[28:32] = [m(k, f[28]), m(k, f[29]), m(k, f[30]), m(k, f[31])]; src = 28
    if f[35] < SEUIL:
        o[32:36] = o[src:src + 4]
    else:
        o[32:36] = [m(k, f[32]), m(k, f[33]), m(k, f[34]), m(k, f[35])]
        if f[31] < SEUIL:
            o[28:32] = [_F(_F(o[24 + q] + o[32 + q]) * 0.5) for q in range(4)]
    t = _F(f[41] - C255)                                # occlusion
    if t <= 0.0:
        t = 0.0
    o[41] = _F(1.0 - _F(t * C1003))
    o[36] = -f[36]                                      # fogWorldNearScatterPush -> −x
    o[37] = m(f[37], K); o[38] = m(f[38], K); o[47] = m(f[47], K); o[48] = m(f[48], K)   # densités x −1e-5
    o[39] = _F(1.0 / f[39]) if f[39] != 0 else float('inf')
    o[45] = _F(1.0 / f[45]) if f[45] != 0 else float('inf')
    o[49] = _F(1.0 / f[49]) if f[49] != 0 else float('inf')
    o[46] = -f[46]                                      # fogHeightNearScatterPush -> −x
    return struct.pack('<56f', *o)
