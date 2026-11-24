"""(23/11/2026) POLICES DU JEU -> vraies polices web (.ttf) pour toute l'interface de l'Atelier (refonte « comme le jeu »).

LU dans les fichiers (rien n'est modifié dans le jeu) :
- dx11/font/font_def/font.g4tx : une planche 4096 x 2048 NON compressée (BGRA) ; chaque lettre est dans UN canal ;
- common/font/font/font_def/font.cfg.bin : en-tête [police, taille 46, hauteur de case 71, …] et une ligne par lettre
  [police, code Shift-JIS, code UTF-8 (entier), x, y, largeur, décalage, avance, canal (0 = R, 1 = V, 2 = B, 3 = A)] ;
- avance MESURÉE sur les captures du jeu : largeur dessinée + 1 (l'avance de la table donne un texte 11 % trop large).
- chiffres : dx11/menu/200_icon/100_num/num_menu01.g4tx (zones « num_menu01_01_<c> »), dessinés en blanc.

Les contours sont suivis sur l'image agrandie 4 fois (bilinéaire, seuil 50 %), simplifiés, et écrits dans un .ttf fait main
(tables head, hhea, maxp, OS/2, hmtx, cmap 4, loca, glyf, name, post) : aucune bibliothèque à installer.
"""
import os, struct, math, time

UPM = 1000
SUR = 4                     # suréchantillonnage pour le tracé


# ------------------------------------------------------------------------------------------------ lecture
def _planche_brute(chemin):
    from .g4 import images
    import numpy as np
    g = images.G4TX(open(chemin, 'rb').read())
    b = g.blocs[0]
    h, w = struct.unpack_from('<II', b, 12)
    a = np.frombuffer(b, np.uint8, count=w * h * 4, offset=128).reshape(h, w, 4)
    return a[..., [2, 1, 0, 3]]                      # BGRA -> RGBA : canal n de la table = colonne n


def _table(data_dir):
    from . import cfgbin
    L = cfgbin.lire(open(os.path.join(data_dir, 'common', 'font', 'font', 'font_def', 'font.cfg.bin'), 'rb').read())
    ent = next(v for k, v in L if k == 1901062515 and v and v[0] == 0)
    gl = {}
    for k, v in L:
        if k == 811081566 and v and v[0] == 0:
            try:
                ch = v[2].to_bytes((v[2].bit_length() + 7) // 8 or 1, 'big').decode('utf-8')
            except Exception:
                continue
            if len(ch) == 1:
                gl[ch] = v[3:9]
    return ent, gl


# ------------------------------------------------------------------------------------------------ tracé
def _agrandir(m, k):
    """bilinéaire x k (m : tableau 2D float 0..1)"""
    import numpy as np
    h, w = m.shape
    ys = (np.arange(h * k) + 0.5) / k - 0.5
    xs = (np.arange(w * k) + 0.5) / k - 0.5
    y0 = np.clip(np.floor(ys).astype(int), 0, h - 1); y1 = np.clip(y0 + 1, 0, h - 1); fy = np.clip(ys - y0, 0, 1)[:, None]
    x0 = np.clip(np.floor(xs).astype(int), 0, w - 1); x1 = np.clip(x0 + 1, 0, w - 1); fx = np.clip(xs - x0, 0, 1)[None, :]
    a = m[y0][:, x0]; b = m[y0][:, x1]; c = m[y1][:, x0]; d = m[y1][:, x1]
    return (a * (1 - fx) + b * fx) * (1 - fy) + (c * (1 - fx) + d * fx) * fy


def _contours(binaire):
    """bords des pixels pleins, chaînés en boucles ; intérieur à GAUCHE (repère y vers le bas)"""
    import numpy as np
    h, w = binaire.shape
    p = np.zeros((h + 2, w + 2), bool); p[1:-1, 1:-1] = binaire
    suiv = {}
    # arêtes orientées : intérieur à gauche quand on avance (y vers le bas)
    for y, x in zip(*np.nonzero(p)):
        X, Y = x - 1, y - 1                      # coin haut-gauche du pixel (repère de l'image)
        if not p[y - 1, x]: suiv.setdefault((X + 1, Y), []).append((X, Y))          # bord haut : vers la gauche
        if not p[y + 1, x]: suiv.setdefault((X, Y + 1), []).append((X + 1, Y + 1))  # bord bas : vers la droite
        if not p[y, x - 1]: suiv.setdefault((X, Y), []).append((X, Y + 1))          # bord gauche : vers le bas
        if not p[y, x + 1]: suiv.setdefault((X + 1, Y + 1), []).append((X + 1, Y))  # bord droit : vers le haut
    boucles = []
    while suiv:
        a = next(iter(suiv)); depart = a; b = [a]
        while True:
            n = suiv[a].pop()
            if not suiv[a]:
                del suiv[a]
            if n == depart:
                break
            b.append(n); a = n
            if a not in suiv:
                break
        if len(b) >= 4:
            boucles.append(b)
    return boucles


def _simplifier(pts, eps):
    """Douglas-Peucker sur une boucle fermée"""
    if len(pts) < 4:
        return pts
    # couper la boucle au point le plus loin du premier
    i = max(range(len(pts)), key=lambda k: (pts[k][0] - pts[0][0]) ** 2 + (pts[k][1] - pts[0][1]) ** 2)
    def dp(seg):
        if len(seg) < 3:
            return seg
        (x0, y0), (x1, y1) = seg[0], seg[-1]
        dx, dy = x1 - x0, y1 - y0; L = math.hypot(dx, dy) or 1e-9
        k, dm = 0, -1
        for j in range(1, len(seg) - 1):
            d = abs(dy * (seg[j][0] - x0) - dx * (seg[j][1] - y0)) / L
            if d > dm:
                k, dm = j, d
        if dm <= eps:
            return [seg[0], seg[-1]]
        g = dp(seg[:k + 1]); d2 = dp(seg[k:])
        return g[:-1] + d2
    a = dp(pts[:i + 1]); b = dp(pts[i:] + [pts[0]])
    r = a[:-1] + b[:-1]
    return r if len(r) >= 3 else pts


# ------------------------------------------------------------------------------------------------ écriture TTF
def _somme(b):
    b += b'\0' * ((-len(b)) % 4)
    return sum(struct.unpack('>%dI' % (len(b) // 4), b)) & 0xFFFFFFFF


def ecrire_ttf(chemin, nom, glyphes, ascent, descent):
    """glyphes : liste (caractère ou None, avance, [contours [(x, y) entiers, …]]) ; le 1er = .notdef"""
    n = len(glyphes)
    glyf, loca = b'', [0]
    xmin = ymin = 10 ** 6; xmax = ymax = -10 ** 6
    maxpts = maxcont = 0
    hmtx = b''
    for ch, av, conts in glyphes:
        conts = [c for c in conts if len(c) >= 3]
        if not conts:
            loca.append(len(glyf)); hmtx += struct.pack('>Hh', max(0, int(av)), 0); continue
        xs = [p[0] for c in conts for p in c]; ys = [p[1] for c in conts for p in c]
        bx0, by0, bx1, by1 = min(xs), min(ys), max(xs), max(ys)
        xmin, ymin, xmax, ymax = min(xmin, bx0), min(ymin, by0), max(xmax, bx1), max(ymax, by1)
        fin, k = [], -1
        for c in conts:
            k += len(c); fin.append(k)
        npts = k + 1; maxpts = max(maxpts, npts); maxcont = max(maxcont, len(conts))
        g = struct.pack('>hhhhh', len(conts), bx0, by0, bx1, by1) + struct.pack('>%dH' % len(fin), *fin) + struct.pack('>H', 0)
        g += bytes([1]) * npts                        # tous les points sur la courbe, coordonnées en int16
        px = py = 0; dxs = b''; dys = b''
        for c in conts:
            for x, y in c:
                dxs += struct.pack('>h', x - px); dys += struct.pack('>h', y - py); px, py = x, y
        g += dxs + dys
        g += b'\0' * ((-len(g)) % 4)
        glyf += g; loca.append(len(glyf))
        hmtx += struct.pack('>Hh', max(0, int(av)), bx0)
    loca_b = struct.pack('>%dI' % len(loca), *loca)
    tete = struct.pack('>IIIIHHqqhhhhHHhhh', 0x00010000, 0x00010000, 0, 0x5F0F3CF5, 0x000B, UPM,
                       0, 0, xmin, ymin, xmax, ymax, 0, 8, 2, 1, 0)
    avmax = max(int(g[1]) for g in glyphes)
    hhea = struct.pack('>IhhhHhhhhhhhhhhhH', 0x00010000, ascent, -descent, 0, avmax, xmin, 0, xmax, 1, 0, 0, 0, 0, 0, 0, 0, n)
    maxp = struct.pack('>IHHHHHHHHHHHHHH', 0x00010000, n, maxpts, maxcont, 0, 0, 2, 0, 0, 0, 0, 0, 0, 0, 0)
    # cmap format 4
    paires = sorted((ord(ch), i) for i, (ch, _, _) in enumerate(glyphes) if ch and ord(ch) < 0xFFFF)
    segs = []
    for c, gi in paires:
        if segs and c == segs[-1][1] + 1 and gi == segs[-1][3] + (c - segs[-1][0]):
            segs[-1][1] = c
        else:
            segs.append([c, c, gi - c, gi])
    segs.append([0xFFFF, 0xFFFF, 1, 0])
    sc = len(segs); sr = 2 * (2 ** int(math.log2(sc))); es = int(math.log2(sr // 2)); rs = 2 * sc - sr
    sub = struct.pack('>HHHHH', 2 * sc, sr, es, rs, 0)
    sub = struct.pack('>HHHHH', 2 * sc, sr, es, rs, 0)
    corps = struct.pack('>%dH' % sc, *[s[1] for s in segs]) + struct.pack('>H', 0) + struct.pack('>%dH' % sc, *[s[0] for s in segs]) \
        + struct.pack('>%dh' % sc, *[((s[2] + 32768) % 65536) - 32768 for s in segs]) + struct.pack('>%dH' % sc, *([0] * sc))
    f4 = struct.pack('>HHH', 4, 14 + len(corps), 0) + struct.pack('>HHHH', 2 * sc, sr, es, rs) + corps
    cmap = struct.pack('>HHHHI', 0, 1, 3, 1, 12) + f4
    def nm(i, s):
        return (i, s.encode('utf-16-be'))
    noms = [nm(1, nom), nm(2, 'Regular'), nm(4, nom), nm(6, nom.replace(' ', ''))]
    stock = b''.join(s for _, s in noms); off = 0; recs = b''
    for i, s in noms:
        recs += struct.pack('>HHHHHH', 3, 1, 0x409, i, len(s), off); off += len(s)
    name = struct.pack('>HHH', 0, len(noms), 6 + 12 * len(noms)) + recs + stock
    post = struct.pack('>IIhhIIIII', 0x00030000, 0, -75, 50, 0, 0, 0, 0, 0)
    os2 = struct.pack('>HhHHHhhhhhhhhhh', 4, avmax // 2, 400, 5, 0, 650, 700, 0, 140, 650, 700, 0, 480, 50, 250)
    codes = [ord(ch) for ch, _, _ in glyphes if ch]
    # sFamilyClass, panose, plages Unicode, fabricant, fsSelection, premier / dernier caractère
    os2 += struct.pack('>h', 0) + bytes(10) + struct.pack('>IIII', 1, 0, 0, 0) + b'MUKU' + struct.pack('>HHH', 0x40, min(codes), min(0xFFFF, max(codes)))
    os2 += struct.pack('>hhhHH', ascent, -descent, 0, ascent, descent) + struct.pack('>II', 1, 0)
    os2 += struct.pack('>hhHHH', 500, 700, 0, 32, 0)
    tables = {b'OS/2': os2, b'cmap': cmap, b'glyf': glyf, b'head': tete, b'hhea': hhea, b'hmtx': hmtx,
              b'loca': loca_b, b'maxp': maxp, b'name': name, b'post': post}
    nt = len(tables); sr2 = 16 * (2 ** int(math.log2(nt))); es2 = int(math.log2(sr2 // 16)); rs2 = nt * 16 - sr2
    entete = struct.pack('>IHHHH', 0x00010000, nt, sr2, es2, rs2)
    off = 12 + 16 * nt; dir_ = b''; donnees = b''
    for tag in sorted(tables):
        t = tables[tag]
        dir_ += struct.pack('>4sIII', tag, _somme(t), off + len(donnees), len(t))
        donnees += t + b'\0' * ((-len(t)) % 4)
    fichier = bytearray(entete + dir_ + donnees)
    # checkSumAdjustment de head
    i = fichier.find(b'head', 12)
    o_head = struct.unpack_from('>I', fichier, i + 8)[0]
    struct.pack_into('>I', fichier, o_head + 8, (0xB1B0AFBA - _somme(bytes(fichier))) & 0xFFFFFFFF)
    open(chemin, 'wb').write(bytes(fichier))


# ------------------------------------------------------------------------------------------------ polices
CARACTERES = ''.join(chr(c) for c in list(range(0x20, 0x7F)) + list(range(0xA0, 0x180))) + '‐–—‘’‚“”„•…‰‹›€™←↑→↓∞○●◎△▲▽▼□■◇◆★☆♪×÷・「」『』【】〜'


def _tracer(cell, k_unites, base_px, x_decal=0):
    """cellule (alpha 0..255, y vers le bas) -> contours en unités de police (y vers le haut, ligne de base = 0)"""
    import numpy as np
    m = _agrandir(cell.astype(np.float32) / 255.0, SUR) >= 0.5
    out = []
    for b in _contours(m):
        b = _simplifier(b, 0.55)
        c = [(int(round((x / SUR + x_decal) * k_unites)), int(round((base_px - y / SUR) * k_unites))) for x, y in b]
        d = [c[0]] + [p for i, p in enumerate(c[1:], 1) if p != c[i - 1]]
        if len(d) >= 3:
            out.append(d)
    return out


def police_texte(data_dir, sortie):
    """police du texte (font_def) -> <sortie> (.ttf)"""
    import numpy as np
    ent, gl = _table(data_dir)
    taille, case = ent[1], ent[2]
    P = _planche_brute(os.path.join(data_dir, 'dx11', 'font', 'font_def', 'font.g4tx'))
    k = UPM / taille
    # ligne de base : bas de l'encre de « H »
    x, y, w, dx, av, c = gl['H']
    cellH = P[y:y + case, x:x + w, c]
    lignes = np.nonzero(cellH.max(axis=1) > 128)[0]
    base = int(lignes.max()) + 1 if len(lignes) else int(case * 0.72)
    glyphes = [(None, int(taille * 0.5 * k), [])]
    for ch in sorted(set(CARACTERES)):
        g = gl.get(ch)
        if not g:
            continue
        x, y, w, dx, av, c = g
        avance = (w + 1) if w > 1 else av              # mesuré en jeu (voir l'en-tête)
        conts = _tracer(P[y:y + case, x:x + w, c], k, base) if w > 1 and ch != ' ' else []
        glyphes.append((ch, int(round(avance * k)), conts))
    ascent = int(round(base * k)); descent = int(round((case - base) * k))
    ecrire_ttf(sortie, 'Inazuma Jeu', glyphes, ascent, descent)
    return {'glyphes': len(glyphes), 'base': base, 'case': case}


def police_chiffres(data_dir, sortie):
    """chiffres du menu (num_menu01_01_*) -> <sortie> (.ttf), lettres blanches : forme = alpha"""
    import numpy as np, re, zlib
    from .g4 import images
    from . import g4
    f = os.path.join(data_dir, 'dx11', 'menu', '200_icon', '100_num', 'fr', 'num_menu01.g4tx')
    if not os.path.exists(f):
        f = os.path.join(data_dir, 'dx11', 'menu', '200_icon', '100_num', 'num_menu01.g4tx')
    b = open(f, 'rb').read()
    n = struct.unpack_from('<H', b, 0x20)[0]; nz = struct.unpack_from('<H', b, 0x22)[0] - n
    total = struct.unpack_from('<I', b, 0x2C)[0]; debut = len(b) - total
    o_crc = (0x60 + 0x30 * n + 0x18 * nz + 15) // 16 * 16
    crcs = struct.unpack_from('<%dI' % (n + nz), b, o_crc)
    par_crc = {zlib.crc32(m.group()): m.group().decode() for m in re.finditer(rb'[A-Za-z0-9_]{2,}', b[:debut])}
    zones = {}
    for i in range(nz):
        img, typ, x, y, w, h = struct.unpack_from('<HHHHHH', b, 0x60 + 0x30 * n + 0x18 * i)
        zones[par_crc.get(crcs[n + i], '')] = (img, x, y, w, h)
    w0, h0, px = g4.decoder_texture(images.G4TX(b).blocs[0])
    px = b''.join(bytes(r) for r in px) if not isinstance(px, (bytes, bytearray)) else bytes(px)
    A = np.frombuffer(px, np.uint8)[:w0 * h0 * 4].reshape(h0, w0, 4)[..., 3]
    hz = zones['num_menu01_01_0'][4]
    k = UPM / hz
    noms = {'%': 'per', '+': 'plus', '-': 'minus', '×': 'mul'}
    glyphes = [(None, int(UPM * 0.5), []), (' ', int(UPM * 0.3), [])]
    for ch in '0123456789%+-×':
        z = zones.get('num_menu01_01_' + noms.get(ch, ch))
        if not z:
            continue
        _, x, y, w, h = z
        cell = A[y:y + h, x:x + w]
        cols = np.nonzero(cell.max(axis=0) > 40)[0]
        x0, x1 = (int(cols.min()), int(cols.max()) + 1) if len(cols) else (0, w)
        conts = _tracer(cell[:, x0:x1], k, h * 0.86)
        glyphes.append((ch, int(round((x1 - x0 + 2) * k)), conts))
    ecrire_ttf(sortie, 'Inazuma Chiffres', glyphes, int(UPM * 0.86), int(UPM * 0.14))
    return {'glyphes': len(glyphes)}


def polices(data_dir, cache_dir):
    """les deux polices (faites une fois, en cache) -> {nom: chemin}"""
    d = os.path.join(cache_dir, 'ui_jeu'); os.makedirs(d, exist_ok=True)
    out = {}
    for nom, f in (('inazuma_jeu.ttf', police_texte), ('inazuma_chiffres.ttf', police_chiffres)):
        p = os.path.join(d, nom)
        if not os.path.exists(p):
            f(data_dir, p)
        out[nom] = p
    return out


if __name__ == '__main__':
    import sys
    t = time.time()
    print(police_texte(sys.argv[1], sys.argv[2]), round(time.time() - t, 1), 's')
    if len(sys.argv) > 3:
        print(police_chiffres(sys.argv[1], sys.argv[3]))
