"""Images pour l'Atelier Maillots : PNG (lecture / écriture), redimensionnement, textures DDS (BC1 / BC7) et
fichiers G4TX du jeu (PC). Tout en Python, sans bibliothèque à installer.

G4TX (relevé sur les maillots du jeu et du pack Orion Kits) :
  en-tête 0x60 : « G4TX », u16 nombre d'images à +0x20, u32 taille des données à +0x2C ;
  une entrée de 0x30 octets par image à partir de 0x60 : u32 décalage (depuis le début des données) à +4,
  u32 taille à +8 ; puis empreintes et noms ; les données (un fichier DDS par image, alignés sur 16 octets)
  commencent à « taille du fichier - taille des données »."""
import struct, zlib, re, os
from . import bc7

# --------------------------------------------------------------------------------------------- encodage rapide
# (21/11/2026) BC7 / BC1 encodés par AtelierCouleurs\moteur\natif\paquets.dll : MÊMES octets que le calcul Python
# ci-dessous (vérifié sur 56 encodages), ~150 fois plus vite et sur un seul cœur. Sans la DLL : le Python, comme avant.
_DLL_ENC = []


def _dll():
    if not _DLL_ENC:
        import ctypes
        ici = os.path.dirname(os.path.abspath(__file__))
        d = None
        for p in (os.path.join(ici, '..', '..', 'AtelierCouleurs', 'moteur', 'natif', 'paquets.dll'),   # AtelierMaillots\lib
                  os.path.join(ici, '..', 'natif', 'paquets.dll')):                                      # AtelierCouleurs\moteur\maillots
            try:
                d = ctypes.CDLL(os.path.normpath(p))
                d.encoder_dds.argtypes = (ctypes.c_char_p, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int,
                                          ctypes.c_char_p, ctypes.c_int64)
                d.encoder_dds.restype = ctypes.c_int64
                break
            except (OSError, AttributeError):
                d = None
        _DLL_ENC.append(d)
    return _DLL_ENC[0]


def encoder_rapide(w, h, rows, mips, format_):
    """blocs BC7 (format_ 7) ou BC1 (format_ 1) de tous les niveaux, ou None sans la DLL"""
    d = _dll()
    if d is None:
        return None
    import ctypes
    rgba = b''.join(bytes(r[:w * 4]) for r in rows[:h])
    n = d.encoder_dds(rgba, w, h, mips, format_, None, 0)
    if n <= 0:
        return None
    buf = ctypes.create_string_buffer(n)
    if d.encoder_dds(rgba, w, h, mips, format_, buf, n) != n:
        return None
    return buf.raw


def pool_encodage():
    """processus en parallèle pour l'encodage : seulement sans la DLL (avec elle, un cœur suffit et on évite de lancer
    une dizaine de processus) ; à utiliser avec « with images.pool_encodage() as pool: »"""
    import contextlib, multiprocessing
    if _dll() is not None:
        return contextlib.nullcontext(None)
    return multiprocessing.Pool(max(1, (os.cpu_count() or 2) - 1))

# --------------------------------------------------------------------------------------------- PNG
def lire_png(chemin):
    """-> (largeur, hauteur, lignes RGBA en bytearray)"""
    d = open(chemin, 'rb').read()
    if d[:8] != b'\x89PNG\r\n\x1a\n':
        raise ValueError("ce n'est pas un fichier PNG : " + os.path.basename(chemin))
    o, idat, pal, trns = 8, [], None, None
    while o < len(d):
        n, t = struct.unpack('>I4s', d[o:o + 8])
        c = d[o + 8:o + 8 + n]
        if t == b'IHDR':
            w, h, bd, ct, _, _, inter = struct.unpack('>IIBBBBB', c)
        elif t == b'PLTE':
            pal = [c[i:i + 3] for i in range(0, len(c), 3)]
        elif t == b'tRNS':
            trns = c
        elif t == b'IDAT':
            idat.append(c)
        o += 12 + n
    if inter:
        raise ValueError("PNG entrelacé non pris en charge : réenregistre l'image sans entrelacement")
    if bd != 8 or ct not in (0, 2, 3, 4, 6):
        raise ValueError("PNG non pris en charge (profondeur %d bits, type %d) : réenregistre en PNG 24 ou 32 bits" % (bd, ct))
    bpp = {0: 1, 2: 3, 3: 1, 4: 2, 6: 4}[ct]
    raw = zlib.decompress(b''.join(idat))
    st = w * bpp
    rows, prev, i = [], bytearray(st), 0
    for y in range(h):
        f = raw[i]
        line = bytearray(raw[i + 1:i + 1 + st]); i += 1 + st
        if f == 1:
            for x in range(bpp, st): line[x] = (line[x] + line[x - bpp]) & 255
        elif f == 2:
            line = bytearray((a + b) & 255 for a, b in zip(line, prev))
        elif f == 3:
            for x in range(st): line[x] = (line[x] + ((line[x - bpp] if x >= bpp else 0) + prev[x]) // 2) & 255
        elif f == 4:
            for x in range(st):
                a = line[x - bpp] if x >= bpp else 0
                b = prev[x]; c = prev[x - bpp] if x >= bpp else 0
                p = a + b - c; pa, pb, pc = abs(p - a), abs(p - b), abs(p - c)
                line[x] = (line[x] + (a if pa <= pb and pa <= pc else (b if pb <= pc else c))) & 255
        prev = line
        if ct == 6:
            out = line
        elif ct == 2:
            out = bytearray(w * 4)
            out[0::4], out[1::4], out[2::4] = line[0::3], line[1::3], line[2::3]
            out[3::4] = b'\xff' * w
        elif ct == 0:
            out = bytearray(w * 4)
            out[0::4] = out[1::4] = out[2::4] = line
            out[3::4] = b'\xff' * w
        elif ct == 4:
            out = bytearray(w * 4)
            out[0::4] = out[1::4] = out[2::4] = line[0::2]
            out[3::4] = line[1::2]
        else:
            out = bytearray(w * 4)
            for x in range(w):
                k = line[x]
                c = pal[k] if pal and k < len(pal) else b'\0\0\0'
                a = trns[k] if trns and k < len(trns) else 255
                out[x * 4:x * 4 + 4] = bytes(c) + bytes((a,))
        rows.append(out)
    return w, h, rows


def ecrire_png(chemin, w, h, rows, niveau=6):
    raw = b''.join(b'\x00' + bytes(r) for r in rows)
    def chunk(t, c): return struct.pack('>I', len(c)) + t + c + struct.pack('>I', zlib.crc32(t + c) & 0xffffffff)
    png = b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', struct.pack('>IIBBBBB', w, h, 8, 6, 0, 0, 0)) \
        + chunk(b'IDAT', zlib.compress(raw, niveau)) + chunk(b'IEND', b'')
    with open(chemin, 'wb') as f:
        f.write(png)


def redimensionner(w, h, rows, nw, nh):
    """bilinéaire (agrandissement) ou moyenne de zone (réduction)"""
    if (w, h) == (nw, nh):
        return rows
    out = [bytearray(nw * 4) for _ in range(nh)]
    if nw <= w and nh <= h:
        for y in range(nh):
            y0, y1 = y * h // nh, max(y * h // nh + 1, (y + 1) * h // nh)
            for x in range(nw):
                x0, x1 = x * w // nw, max(x * w // nw + 1, (x + 1) * w // nw)
                acc = [0, 0, 0, 0]; n = 0
                for yy in range(y0, y1):
                    r = rows[yy]
                    for xx in range(x0, x1):
                        p = xx * 4
                        acc[0] += r[p]; acc[1] += r[p + 1]; acc[2] += r[p + 2]; acc[3] += r[p + 3]; n += 1
                out[y][x * 4:x * 4 + 4] = bytes(v // n for v in acc)
        return out
    for y in range(nh):
        fy = (y + 0.5) * h / nh - 0.5
        y0 = max(0, min(h - 1, int(fy))); y1 = min(h - 1, y0 + 1); ty = max(0.0, min(1.0, fy - y0))
        r0, r1 = rows[y0], rows[y1]
        for x in range(nw):
            fx = (x + 0.5) * w / nw - 0.5
            x0 = max(0, min(w - 1, int(fx))); x1 = min(w - 1, x0 + 1); tx = max(0.0, min(1.0, fx - x0))
            for k in range(4):
                a = r0[x0 * 4 + k] * (1 - tx) + r0[x1 * 4 + k] * tx
                b = r1[x0 * 4 + k] * (1 - tx) + r1[x1 * 4 + k] * tx
                out[y][x * 4 + k] = int(a * (1 - ty) + b * ty + 0.5)
    return out


# --------------------------------------------------------------------------------------- BC1 / BC7
def _c565(v):
    r, g, b = (v >> 11) & 31, (v >> 5) & 63, v & 31
    return (r << 3 | r >> 2, g << 2 | g >> 4, b << 3 | b >> 2)


def _bloc_bc1(blk):
    c0, c1, idx = struct.unpack('<HHI', blk)
    a, b = _c565(c0), _c565(c1)
    if c0 > c1:
        cs = [a + (255,), b + (255,), tuple((2 * x + y) // 3 for x, y in zip(a, b)) + (255,),
              tuple((x + 2 * y) // 3 for x, y in zip(a, b)) + (255,)]
    else:
        cs = [a + (255,), b + (255,), tuple((x + y) // 2 for x, y in zip(a, b)) + (255,), (0, 0, 0, 0)]
    return [cs[(idx >> (2 * i)) & 3] for i in range(16)]


def decoder_dds(dds):
    """fichier DDS (bytes) -> (largeur, hauteur, lignes RGBA) du niveau 0"""
    h, w = struct.unpack_from('<II', dds, 12)
    four = dds[84:88]
    if four == b'DX10':
        fmt = struct.unpack_from('<I', dds, 128)[0]
        if fmt not in (98, 99):
            raise ValueError('format DDS %d non pris en charge' % fmt)
        data, taille, fn = 148, 16, bc7.block
    elif four == b'DXT1':
        data, taille, fn = 128, 8, _bloc_bc1
    else:
        raise ValueError('format DDS %r non pris en charge' % four)
    rows = [bytearray(w * 4) for _ in range(h)]
    p = data
    for by in range((h + 3) // 4):
        for bx in range((w + 3) // 4):
            px = fn(dds[p:p + taille]); p += taille
            for i, c in enumerate(px):
                yy, xx = by * 4 + i // 4, bx * 4 + i % 4
                if yy < h and xx < w:
                    rows[yy][xx * 4:xx * 4 + 4] = bytes(c)
    return w, h, rows


def _vers565(r, g, b):
    return ((r * 31 + 127) // 255) << 11 | ((g * 63 + 127) // 255) << 5 | ((b * 31 + 127) // 255)


def encoder_bc1_lignes(args):
    """(largeur, lignes de 4 pixels de haut) -> octets BC1 de cette bande ; utilisé en parallèle"""
    w, bande = args
    out = bytearray()
    for bx in range(0, w, 4):
        px = []
        for yy in range(4):
            r = bande[yy]
            for xx in range(bx, bx + 4):
                p = min(xx, w - 1) * 4
                px.append((r[p], r[p + 1], r[p + 2]))
        if px.count(px[0]) == 16:
            c = _vers565(*px[0]); out += struct.pack('<HHI', c, c, 0); continue
        # extrémités : les deux pixels les plus éloignés sur l'axe principal (approché par la luminance)
        lum = [p[0] * 299 + p[1] * 587 + p[2] * 114 for p in px]
        hi, lo = px[lum.index(max(lum))], px[lum.index(min(lum))]
        c0, c1 = _vers565(*hi), _vers565(*lo)
        if c0 == c1:
            out += struct.pack('<HHI', c0, c1, 0); continue
        if c0 < c1:
            c0, c1 = c1, c0
        a, b = _c565(c0), _c565(c1)
        pal = (a, b, tuple((2 * x + y) // 3 for x, y in zip(a, b)), tuple((x + 2 * y) // 3 for x, y in zip(a, b)))
        idx = 0
        for i, p in enumerate(px):
            best, bi = 1 << 30, 0
            for k, q in enumerate(pal):
                d = (p[0] - q[0]) ** 2 + (p[1] - q[1]) ** 2 + (p[2] - q[2]) ** 2
                if d < best:
                    best, bi = d, k
            idx |= bi << (2 * i)
        out += struct.pack('<HHI', c0, c1, idx)
    return bytes(out)


def moitie(w, h, rows):
    """réduction par 2 (moyenne 2x2) pour le niveau suivant des mipmaps"""
    nw, nh = max(1, w // 2), max(1, h // 2)
    out = [bytearray(nw * 4) for _ in range(nh)]
    for y in range(nh):
        r0, r1 = rows[min(2 * y, h - 1)], rows[min(2 * y + 1, h - 1)]
        o = out[y]
        for x in range(nw):
            a, b = min(2 * x, w - 1) * 4, min(2 * x + 1, w - 1) * 4
            for k in range(4):
                o[x * 4 + k] = (r0[a + k] + r0[b + k] + r1[a + k] + r1[b + k] + 2) >> 2
    return nw, nh, out


def dds_bc1(w, h, rows, pool=None, progression=None, mips=10):
    """image RGBA -> fichier DDS DXT1 avec `mips` niveaux (le jeu déclare le nombre de niveaux dans la table du G4TX :
    il faut les fournir tous, sinon l'image disparaît de loin et sur les portraits)"""
    n_, lw, lh = 1, w, h                             # même nombre de niveaux que la boucle ci-dessous
    while n_ < mips and (lw > 1 or lh > 1):
        lw, lh, n_ = max(1, lw // 2), max(1, lh // 2), n_ + 1
    rapide = encoder_rapide(w, h, rows, n_, 1)
    if rapide is not None:
        if progression:
            progression(1.0)
        niveaux = [None] * n_
    else:
        niveaux = [(w, h, rows)]
        while len(niveaux) < mips and (niveaux[-1][0] > 1 or niveaux[-1][1] > 1):
            niveaux.append(moitie(*niveaux[-1]))
    mips = len(niveaux)
    hdr = bytearray(128)
    hdr[0:4] = b'DDS '
    struct.pack_into('<IIIIIII', hdr, 4, 124, 0x0A1007, h, w, max(1, (w + 3) // 4) * max(1, (h + 3) // 4) * 8, 0, mips)
    struct.pack_into('<II4s', hdr, 76, 32, 4, b'DXT1')
    struct.pack_into('<I', hdr, 108, 0x401008 if mips > 1 else 0x1000)
    if rapide is not None:
        return bytes(hdr) + rapide
    bandes = []
    for lw, lh, lr in niveaux:
        for by in range(0, lh, 4):
            bandes.append((lw, [lr[min(by + k, lh - 1)] for k in range(4)]))
    morceaux = []
    it = pool.imap(encoder_bc1_lignes, bandes, chunksize=8) if pool is not None else map(encoder_bc1_lignes, bandes)
    for i, m in enumerate(it):
        morceaux.append(m)
        if progression and i % 32 == 0:
            progression(i / len(bandes))
    return bytes(hdr) + b''.join(morceaux)


def dds_bc7(w, h, rows, entete, mips, pool=None):
    """image RGBA -> DDS BC7 (en-tête DX10 repris d'une texture du jeu de même taille), avec `mips` niveaux"""
    from . import bustes
    rapide = encoder_rapide(w, h, rows, mips, 7)
    if rapide is not None:
        return bytes(entete) + rapide
    niveaux = [(w, h, rows)]
    while len(niveaux) < mips:
        niveaux.append(moitie(*niveaux[-1]))
    bandes = []
    for lw, lh, lr in niveaux:
        for by in range(0, lh, 4):
            bandes.append((lw, [lr[min(by + k, lh - 1)] for k in range(4)]))
    it = pool.imap(bustes.encoder_bc7_bande, bandes, chunksize=16) if pool is not None else map(bustes.encoder_bc7_bande, bandes)
    return bytes(entete) + b''.join(it)


def mips_dds(dds):
    return max(1, struct.unpack_from('<I', dds, 28)[0])


# --------------------------------------------------------------------------------------------- G4TX
class G4TX:
    def __init__(self, octets):
        self.b = bytes(octets)
        if self.b[:4] != b'G4TX':
            raise ValueError("ce n'est pas un fichier G4TX")
        self.n = struct.unpack_from('<H', self.b, 0x20)[0]
        total = struct.unpack_from('<I', self.b, 0x2C)[0]
        self.debut = len(self.b) - total
        dds = [m.start() for m in re.finditer(rb'DDS \x7c\x00\x00\x00', self.b)]
        noms = [m.group()[:-1].decode() for m in re.finditer(rb'[a-z][a-z0-9_]{3,40}\x00', self.b[:self.debut])]
        self.noms = noms[-self.n:]
        self.blocs = []
        for k in range(self.n):
            off, taille = struct.unpack_from('<II', self.b, 0x60 + k * 0x30 + 4)
            self.blocs.append(self.b[self.debut + off:self.debut + off + taille])
        assert all(bl[:4] == b'DDS ' for bl in self.blocs), 'G4TX : table inattendue'

    def image(self, nom):
        return decoder_dds(self.blocs[self.noms.index(nom)])

    def taille(self, nom):
        bl = self.blocs[self.noms.index(nom)]
        h, w = struct.unpack_from('<II', bl, 12)
        return w, h

    def principal(self, suffixe):
        """nom de l'image principale finissant par _20 (haut) ou _30 (short)"""
        for n in self.noms:
            if n.endswith('_' + suffixe):
                return n
        return None

    def reconstruire(self, remplacements):
        """remplacements : nom -> fichier DDS ; renvoie le nouveau G4TX"""
        tete = bytearray(self.b[:self.debut])
        donnees = bytearray()
        for k in range(self.n):
            bl = remplacements.get(self.noms[k], self.blocs[k])
            while len(donnees) % 16:
                donnees += b'\0'
            struct.pack_into('<II', tete, 0x60 + k * 0x30 + 4, len(donnees), len(bl))
            if bl is not self.blocs[k]:
                # image agrandie : la table du G4TX donne aussi les pixels, le nombre de niveaux et la taille
                h, w = struct.unpack_from('<II', bl, 12)
                e = 0x60 + k * 0x30
                struct.pack_into('<I', tete, e + 0x0C, w * h)
                tete[e + 0x11] = mips_dds(bl)
                struct.pack_into('<HH', tete, e + 0x18, w, h)
            donnees += bl
        while len(donnees) % 16:          # comme le jeu : données complétées jusqu'à un multiple de 16
            donnees += b'\0'
        struct.pack_into('<I', tete, 0x2C, len(donnees))
        return bytes(tete) + bytes(donnees)


def icone_planche(chemin_planche, cle):
    """icône (256x256) d'une planche d'icônes du jeu (une image DDS par icône, noms dans le même ordre)"""
    b = open(chemin_planche, 'rb').read()
    dds = [m.start() for m in re.finditer(rb'DDS \x7c\x00\x00\x00', b)]
    debut = b.find(b'uni_u010101\x00')
    noms, o = [], debut
    while len(noms) < len(dds):
        f = b.index(b'\x00', o); noms.append(b[o:f].decode('ascii', 'replace')); o = f + 1
    if cle not in noms:
        return None
    i = noms.index(cle)
    fin = dds[i + 1] if i + 1 < len(dds) else len(b)
    return decoder_dds(b[dds[i]:fin])
