"""Bustes des portraits (menu/200_icon/10_icon_chr/uniform/*.g4tx) pour un nouveau maillot.

Le jeu dessine les portraits des joueurs avec une image de buste par maillot, trouvée par son nom de fichier :
  <modèle>_<côté>_<variante>_l.g4tx  (ex. u110201_10_00_l)  et  <corps>_<modèle>_<côté>_00_l.g4tx (corps spéciaux)
Chaque fichier contient deux images 256 x 256 (BC7) : <...>_1 (cou + haut du maillot) et <...>_2 (masque du cou).
Sans ces fichiers, le buste est vide sur les portraits.

On reprend ceux du maillot de base : renommés pour le nouveau modèle (même longueur de nom : 7 caractères, comme
« u110201 », pour garder la structure du fichier), et le maillot recoloré (peau, cou, col blanc et contour gardés)."""
import os, re, glob, struct, zlib
from . import images, bc7


def bc7_mode6(px):
    """16 pixels RGBA -> 16 octets BC7 mode 6 (un sous-ensemble, extrémités RGBA 7 bits, indices 4 bits)"""
    lum = [p[0] * 299 + p[1] * 587 + p[2] * 114 + p[3] * 50 for p in px]
    e0, e1 = px[lum.index(min(lum))], px[lum.index(max(lum))]
    q0 = [min(127, (c + 1) >> 1) for c in e0]
    q1 = [min(127, (c + 1) >> 1) for c in e1]
    v0 = [c << 1 for c in q0]; v1 = [c << 1 for c in q1]
    W = bc7.W[4]
    pal = [tuple((v0[k] * (64 - w) + v1[k] * w + 32) >> 6 for k in range(4)) for w in W]
    ind = []
    for p in px:
        best, bi = 1 << 30, 0
        for k, q in enumerate(pal):
            d = (p[0] - q[0]) ** 2 + (p[1] - q[1]) ** 2 + (p[2] - q[2]) ** 2 + (p[3] - q[3]) ** 2
            if d < best:
                best, bi = d, k
        ind.append(bi)
    if ind[0] >= 8:
        q0, q1 = q1, q0
        ind = [15 - i for i in ind]
    bits, n = 0, 0
    def put(v, k):
        nonlocal bits, n
        bits |= (v & ((1 << k) - 1)) << n; n += k
    put(1 << 6, 7)
    for k in range(4):
        put(q0[k], 7); put(q1[k], 7)
    put(0, 1); put(0, 1)
    put(ind[0], 3)
    for i in ind[1:]:
        put(i, 4)
    return bits.to_bytes(16, 'little')


def encoder_bc7_bande(args):
    """une bande de 4 lignes -> blocs BC7 (fonction de premier niveau : utilisable par multiprocessing)"""
    w, lignes = args
    out = bytearray()
    for bx in range(0, w, 4):
        px = [tuple(lignes[i // 4][min(bx + i % 4, w - 1) * 4:min(bx + i % 4, w - 1) * 4 + 4]) for i in range(16)]
        out += bc7_mode6(px)
    return bytes(out)


def encoder_bc7(w, h, rows):
    rapide = images.encoder_rapide(w, h, rows, 1, 7)      # (paquets.dll : mêmes octets, bien plus vite)
    if rapide is not None:
        return rapide
    out = bytearray()
    for by in range(0, h, 4):
        for bx in range(0, w, 4):
            px = [tuple(rows[min(by + i // 4, h - 1)][min(bx + i % 4, w - 1) * 4:min(bx + i % 4, w - 1) * 4 + 4]) for i in range(16)]
            out += bc7_mode6(px)
    return bytes(out)


def _peau(R, G, B):
    return R > G > B and R - B > 40 and G - B < 75 and R > 90 and 30 < R - G < 105   # peaux claires et foncées, pas les rouges vifs


def recolorer(rows, w, h, couleur):
    """le maillot prend `couleur` d'un seul ton (les motifs du maillot de base disparaissent) ; gardés : transparent,
    contour sombre, peau, et le blanc du col (blanc à moins de 14 pixels sous le cou)"""
    px = lambda x, y: rows[y][x * 4:x * 4 + 4]
    # bas du cou par colonne (dernier pixel de peau en partant du haut, dans la moitié haute du buste)
    bas_cou = [-1] * w
    for x in range(w):
        for y in range(h):
            R, G, B, A = px(x, y)
            if A >= 8 and _peau(R, G, B):
                if bas_cou[x] < 0 and y > h * 0.72:      # peau qui commence bas : un bras, pas le cou
                    break
                bas_cou[x] = y
            elif bas_cou[x] >= 0 and A >= 8 and not _peau(R, G, B):
                break
    ombre = tuple(int(c * 0.72) for c in couleur)
    for y in range(h):
        r = rows[y]
        for x in range(w):
            R, G, B, A = r[x * 4:x * 4 + 4]
            if A < 8:
                continue
            mx, mn = max(R, G, B), min(R, G, B)
            if mx < 55 or _peau(R, G, B):                          # contour, peau (cou, bras)
                continue
            if mn > 190 and mx - mn < 45:                          # blanc : le col seulement s'il touche le cou
                proche = any(0 <= bas_cou[xx] < y <= bas_cou[xx] + 10 for xx in range(max(0, x - 4), min(w, x + 5)))
                if proche:
                    continue
            lum = (R * 299 + G * 587 + B * 114) / 1000.0
            c = ombre if mx < 80 else couleur                      # ombres du dessin (tons très sombres) gardées
            r[x * 4:x * 4 + 3] = bytes(c)


def appliquer_motif(rows, w, h, motif):
    """le maillot du buste prend le MOTIF (vue de face de la poitrine, faite par le studio), avec les ombres du dessin ;
    le col (blanc sous le cou) prend la couleur du col du maillot ; gardés : transparent, contour sombre, peau"""
    mw, mh, mr = motif
    px = lambda x, y: rows[y][x * 4:x * 4 + 4]
    bas_cou = [-1] * w
    for x in range(w):
        for y in range(h):
            R, G, B, A = px(x, y)
            if A >= 8 and _peau(R, G, B):
                if bas_cou[x] < 0 and y > h * 0.72:
                    break
                bas_cou[x] = y
            elif bas_cou[x] >= 0 and A >= 8 and not _peau(R, G, B):
                break
    maillot, col = [], []
    for y in range(h):
        r = rows[y]
        for x in range(w):
            R, G, B, A = r[x * 4:x * 4 + 4]
            if A < 8:
                continue
            mx, mn = max(R, G, B), min(R, G, B)
            if mx < 55 or _peau(R, G, B):
                continue
            lum = (R * 299 + G * 587 + B * 114) / 1000.0
            if mn > 190 and mx - mn < 45 and any(0 <= bas_cou[xx] < y <= bas_cou[xx] + 10 for xx in range(max(0, x - 4), min(w, x + 5))):
                col.append((x, y, lum))
            else:
                maillot.append((x, y, lum, mx < 80))
    if not maillot:
        return
    x0 = min(p[0] for p in maillot); x1 = max(p[0] for p in maillot); y0 = min(p[1] for p in maillot)
    larg = max(1, x1 - x0)
    ref = sorted(p[2] for p in maillot)[len(maillot) // 2] or 1
    def motif_en(x, y):
        u = (x - x0) / larg
        v = (y - y0) / larg                       # même échelle en hauteur qu'en largeur
        mxp = min(mw - 1, max(0, int(u * (mw - 1))))
        myp = min(mh - 1, max(0, int(v * (mw - 1))))
        return mr[myp][mxp * 4:mxp * 4 + 3]
    for x, y, lum, sombre in maillot:
        c = motif_en(x, y)
        f = 0.62 + 0.38 * min(1.4, lum / ref)     # ombres du dessin du buste, adoucies (le motif a déjà les siennes)
        if sombre:
            f *= 0.7
        rows[y][x * 4:x * 4 + 3] = bytes(min(255, int(v * f)) for v in c)
    # col : couleur du haut du motif, au milieu (le col du maillot)
    echant = [mr[y][x * 4:x * 4 + 3] for y in range(0, max(1, mh // 14)) for x in range(int(mw * 0.4), int(mw * 0.6))
              if mr[y][x * 4 + 3] > 128] if len(mr[0]) >= mw * 4 else []
    if echant and col:
        cc = [sorted(e[k] for e in echant)[len(echant) // 2] for k in range(3)]
        lc = sorted(p[2] for p in col)[len(col) // 2] or 1
        for x, y, lum in col:
            f = 0.75 + 0.25 * min(1.3, lum / lc)
            rows[y][x * 4:x * 4 + 3] = bytes(min(255, int(v * f)) for v in cc)


def renommer(octets, ancien, nouveau):
    """remplace le nom de modèle dans les noms d'images (même longueur), met à jour empreintes et ordre trié"""
    assert len(ancien) == len(nouveau)
    b = bytearray(octets)
    n = struct.unpack_from('<H', b, 0x20)[0]
    t = 0x60 + n * 0x30
    debut = len(b) - struct.unpack_from('<I', b, 0x2C)[0]
    zone = bytes(b[:debut])
    noms = [m.group()[:-1] for m in re.finditer(rb'[a-z][a-z0-9_]{3,60}\x00', zone[t:])][-n:]
    nouveaux = [x.replace(ancien.encode(), nouveau.encode()) for x in noms]
    for a, z in zip(noms, nouveaux):
        i = zone.index(a + b'\x00', t)
        b[i:i + len(a)] = z
    hs = [zlib.crc32(x) for x in nouveaux]
    for k, hv in enumerate(hs):
        struct.pack_into('<I', b, t + 4 * k, hv)
    ordre = sorted(range(n), key=lambda k: hs[k])
    for k, v in enumerate(ordre):
        b[t + 4 * n + k] = v
    return bytes(b)


def fichiers_base(dossier_bustes, code, cotes=('10', '20')):
    """bustes du maillot de base pour les côtés voulus, pour TOUS les corps : le jeu remplace les deux derniers chiffres
    du code par le numéro du corps (01-08 joueurs, 51-58 gardiens), ex. u110202_10_00_l, u110207_10_00_l, u110251_..."""
    pre = code[:5]
    out = []
    for p in glob.glob(os.path.join(dossier_bustes, '*%s*_l.g4tx' % pre)):
        f = os.path.basename(p)
        m = re.match(r'^(?:u\d{6}_)?%s(\d\d)_(\d\d)_(\d\d)_l\.g4tx$' % pre, f)
        if m and m.group(2) in cotes:
            out.append((p, m.group(2)))
    return sorted(out)


def faire_bustes(dossier_bustes, code_base, code_neuf, couleurs, sortie, journal=print, motifs=None):
    """couleurs : côté ('10' / '20') -> (r, g, b) ; écrit les bustes renommés (préfixe de 5 caractères du code) et
    recolorés dans `sortie`"""
    os.makedirs(sortie, exist_ok=True)
    pb, pn = code_base[:5], code_neuf[:5]
    faits = 0
    for p, cote in fichiers_base(dossier_bustes, code_base):
        b = renommer(open(p, 'rb').read(), pb, pn)
        g = images.G4TX(b)
        bb = bytearray(b)
        for k, nom in enumerate(g.noms):
            if not nom.endswith('_1'):
                continue
            bl = g.blocs[k]
            if bl[84:88] != b'DX10' or images.mips_dds(bl) != 1:
                continue
            w, h, rows = images.decoder_dds(bl)
            if motifs and motifs.get(cote):
                appliquer_motif(rows, w, h, motifs[cote])
            else:
                recolorer(rows, w, h, couleurs[cote])
            data = encoder_bc7(w, h, rows)
            debut = len(bb) - struct.unpack_from('<I', bb, 0x2C)[0]
            off = struct.unpack_from('<I', bb, 0x60 + k * 0x30 + 4)[0]
            pos = debut + off + 148
            assert len(data) == ((w + 3) // 4) * ((h + 3) // 4) * 16
            bb[pos:pos + len(data)] = data
        nom_f = os.path.basename(p).replace(pb, pn, 1) if os.path.basename(p).startswith(pb) else os.path.basename(p).replace('_' + pb, '_' + pn, 1)
        open(os.path.join(sortie, nom_f), 'wb').write(bytes(bb))
        faits += 1
    journal('bustes : %d fichier(s) pour %s' % (faits, code_neuf))
    return faits
