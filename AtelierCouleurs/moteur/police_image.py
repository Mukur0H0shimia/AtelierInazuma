"""(24/11/2026, demande de muku : « transforme-moi ça en police, le résultat doit être identique ») POLICES-IMAGES.

muku a fait deux planches d'alphabet dans le style de la bannière d'armure du jeu (polices_image/armure1.png sur fond blanc,
armure2.png sur fond transparent). Chaque caractère est DÉCOUPÉ dans la planche avec ses pixels exacts (remplissage, contour,
ombre, lueur), puis le texte est écrit lettre par lettre : les lettres sont celles de la planche, rien n'est redessiné.

Découpe : 6 lignes connues (LIGNES) ; le REMPLISSAGE (rouge-violet, opaque, pas le jaune) donne un morceau par caractère
(les morceaux qui se recouvrent une fois l'italique redressé = même caractère ; s'il en reste trop, les deux plus proches sont
réunis : « " », « = », « : »…) ; chaque pixel visible de la planche va au caractère le plus proche (croissance) : la lettre
ENTIÈRE avec sa lueur. Fond blanc : « couleur vers alpha » (le moins de blanc possible retiré à chaque pixel).
Écriture : lueurs et ombres de toutes les lettres d'abord, puis les lettres (une lueur ne passe jamais sur sa voisine) ;
agrandissement Lanczos (net) ; accents faits avec les signes de la planche (` ^ ~ . ,) ; ¡ ¿ = ! ? retournés.
"""
import os, json
import numpy as np

ICI = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DOSSIER = os.path.join(ICI, 'polices_image')
# (24/11, muku : « la 1 est horrible ») armure1 (fond blanc) n'est plus proposée : sa lueur et son ombre grise ne marchent que sur
# du blanc ; la retirer du fond laisse des bords bruns sur une bannière. Le fichier reste dans polices_image/.
PLANCHES = {'armure2': ('armure2.png', False)}      # (fichier, fond blanc)
LIGNES = ['ABCDEFGHIJKLM', 'NOPQRSTUVWXYZ', 'abcdefghijklm', 'nopqrstuvwxyz', '0123456789',
          "!?.,:;'‘\"-_~^`@#$%&*+=()[]{}"]
PENTE = 0.2                                   # italique des planches : x' = x + PENTE * (y - ligne de base)
VERSION = 4
SANS_JAMBAGE = set('ABCDEFGHIKLMNOPRSTUVWXYZacemnorsuvwxz0123456789!?:%&')


def _png(path):
    from .g4 import images as I
    w, h, rows = I.lire_png(path)
    a = np.frombuffer(b''.join(bytes(r) for r in rows), np.uint8).reshape(h, w, -1).astype(np.float32) / 255
    if a.shape[2] == 3:
        a = np.concatenate([a, np.ones((h, w, 1), np.float32)], -1)
    return a


def _ecrire_png(path, a):
    from .g4 import images as I
    im = (np.clip(a, 0, 1) * 255 + 0.5).astype(np.uint8)
    I.ecrire_png(path, im.shape[1], im.shape[0], [im[y].tobytes() for y in range(im.shape[0])])


LUEUR_PLANCHE = np.array([252, 236, 156], np.float32) / 255   # (armure1) la lueur = le jaune pâle du contour fondu dans le blanc


def blanc_en_alpha(a):
    """fond blanc -> transparence. La lueur de la planche est le jaune pâle du contour mêlé au blanc (MESURÉ : blanc ->
    251,228,176 -> contour 250,235,155) : ces pixels deviennent ce jaune, plus ou moins transparent (la « couleur vers alpha »
    ordinaire en faisait un jaune sombre, olive sur fond foncé). Les autres (remplissage, ombre) : couleur vers alpha."""
    fond = float(np.median(np.concatenate([a[0, :, :3].ravel(), a[-1, :, :3].ravel()])))
    rgb = a[..., :3]
    al = np.clip(np.max((fond - rgb) / fond, axis=-1), 0, 1)
    col = np.where(al[..., None] > 1e-4, (rgb - fond * (1 - al[..., None])) / np.maximum(al[..., None], 1e-4), 0)
    C = LUEUR_PLANCHE
    a1 = np.clip((fond - rgb[..., 2]) / (fond - C[2]), 0, 1)
    pred = fond * (1 - a1[..., None]) + C * a1[..., None]
    lueur = (np.abs(pred - rgb).max(-1) < 0.07) & (a1 < 0.999)
    col = np.where(lueur[..., None], C, col)
    al = np.where(lueur, a1, al)
    # le contour jaune pâle (au moins aussi jaune que la lueur) : OPAQUE, sa couleur (sinon un jaune transparent, terne)
    contour = (a1 >= 0.999) & (rgb[..., 0] > 0.8) & (rgb[..., 1] > 0.7) & (rgb[..., 2] < rgb[..., 1])
    col = np.where(contour[..., None], rgb, col)
    al = np.where(contour, 1.0, al)
    return np.concatenate([np.clip(col, 0, 1), al[..., None]], -1)


def _decale(m, dy, dx):
    H, W = m.shape
    s = np.zeros_like(m)
    s[max(0, dy):H + min(0, dy), max(0, dx):W + min(0, dx)] = m[max(0, -dy):H + min(0, -dy), max(0, -dx):W + min(0, -dx)]
    return s


def _composantes(m):
    H, W = m.shape
    lab = np.where(m, np.arange(1, H * W + 1, dtype=np.int64).reshape(H, W), 0)
    while True:
        v = lab.copy()
        for dy in (-1, 0, 1):
            for dx in (-1, 0, 1):
                if dy or dx:
                    s = _decale(lab, dy, dx)
                    v = np.where(m & (s > 0), np.maximum(v, s), v)
        if (v == lab).all():
            break
        lab = v
    out = []
    for u in np.unique(lab[lab > 0]):
        ys, xs = np.nonzero(lab == u)
        out.append((ys, xs))
    return out


def _croissance(lab, visible, n=120):
    """étiquettes étendues à tout le visible (un pixel par passe, 4 voisins)"""
    for _ in range(n):
        libre = visible & (lab == 0)
        if not libre.any():
            break
        v = lab.copy()
        for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            s = _decale(lab, dy, dx)
            v = np.where(libre & (v == 0) & (s > 0), s, v)
        if (v == lab).all():
            break
        lab = v
    return lab


def construire(cle, cache_dir, journal=print):
    fichier, blanc = PLANCHES[cle]
    a = _png(os.path.join(DOSSIER, fichier))
    if blanc:
        a = blanc_en_alpha(a)
    rgb = a[..., :3]
    corps = (a[..., 3] > 0.85) & (rgb[..., 1] < 0.55) & (rgb.max(-1) - rgb.min(-1) > 0.25)
    comps = [c for c in _composantes(corps) if len(c[0]) >= 25]
    cy = np.array([c[0].mean() for c in comps]); ordre = np.argsort(cy)
    coupes = sorted(np.argsort(np.diff(cy[ordre]))[-5:])
    groupes, d = [], 0
    for k in coupes + [len(ordre) - 1]:
        groupes.append([comps[i] for i in ordre[d:k + 1]]); d = k + 1
    lab = np.zeros(a.shape[:2], np.int64)
    cars = []                                     # (caractère, n° de ligne, morceaux)
    for li, (txt, G) in enumerate(zip(LIGNES, groupes)):
        yc = np.mean([c[0].mean() for c in G])
        items = sorted(([(xs + PENTE * (ys - yc)).min(), (xs + PENTE * (ys - yc)).max(), [(ys, xs)]] for ys, xs in G), key=lambda t: t[0])
        fus = []
        for it in items:
            if fus and min(it[1], fus[-1][1]) - max(it[0], fus[-1][0]) > 0.3 * min(it[1] - it[0], fus[-1][1] - fus[-1][0]):
                fus[-1][1] = max(fus[-1][1], it[1]); fus[-1][2] += it[2]
            else:
                fus.append(it)
        while len(fus) > len(txt):
            g = [fus[i + 1][0] - fus[i][1] for i in range(len(fus) - 1)]
            i = int(np.argmin(g)); fus[i][1] = fus[i + 1][1]; fus[i][2] += fus[i + 1][2]; del fus[i + 1]
        if len(fus) != len(txt):
            raise ValueError('%s ligne %d : %d caractères trouvés pour %d' % (cle, li, len(fus), len(txt)))
        for c, f in zip(txt, fus):
            cars.append((c, li, f[2]))
            for ys, xs in f[2]:
                lab[ys, xs] = len(cars)
    lab = _croissance(lab, a[..., 3] > 0.01)
    # lignes de base (bas du remplissage des caractères sans jambage) et hauteur des capitales
    bas = {}
    for c, li, parts in cars:
        if c in SANS_JAMBAGE:
            bas.setdefault(li, []).append(max(p[0].max() for p in parts))
    base = {li: float(np.median(v)) for li, v in bas.items()}
    caps = [max(p[0].max() for p in parts) - min(p[0].min() for p in parts) for c, li, parts in cars if li < 2 and c not in 'QJ']
    H0 = float(np.median(caps))
    d = os.path.join(cache_dir, 'police_image', cle)
    os.makedirs(d, exist_ok=True)
    index, ecarts = {}, []
    for n, (c, li, parts) in enumerate(cars, 1):
        ys = np.concatenate([p[0] for p in parts]); xs = np.concatenate([p[1] for p in parts])
        b = base[li]
        xd = xs + PENTE * (ys - b)                 # remplissage, italique redressé
        m = lab == n
        Y, X = np.nonzero(m)
        y0, y1, x0, x1 = Y.min(), Y.max() + 1, X.min(), X.max() + 1
        im = a[y0:y1, x0:x1].copy()
        im[..., 3] = np.where(m[y0:y1, x0:x1], im[..., 3], 0)
        f = '%d.png' % ord(c)
        _ecrire_png(os.path.join(d, f), im)
        index[c] = {'f': f, 'gauche': float(xd.min()), 'larg': float(xd.max() - xd.min()), 'x0': int(x0), 'y0': float(y0 - b),
                    'haut': float(ys.min() - b), 'bas': float(ys.max() - b), 'cx': float((xd.min() + xd.max()) / 2)}
    for li, txt in enumerate(LIGNES[:2]):         # écart entre deux remplissages voisins : lignes des capitales (les minuscules
                                                  # et chiffres de la planche sont écartés pour remplir sa largeur)
        L = [index[c] for c in txt]
        ecarts += [L[i + 1]['gauche'] - (L[i]['gauche'] + L[i]['larg']) for i in range(len(L) - 1)]
    meta = {'version': VERSION, 'H0': H0, 'ecart': float(np.median(ecarts)), 'caracteres': index}
    json.dump(meta, open(os.path.join(d, 'police.json'), 'w', encoding='utf-8'), ensure_ascii=False)
    _META.pop(cle, None)
    journal('police-image %s : %d caractères, capitales %.0f px, écart %.1f px' % (cle, len(index), H0, meta['ecart']))
    return meta


_META, _IMG = {}, {}


def disponible(cle, cache_dir):
    try:
        return json.load(open(os.path.join(cache_dir, 'police_image', cle, 'police.json'), encoding='utf-8')).get('version') == VERSION
    except (OSError, ValueError):
        return False


def _meta(cle, cache_dir):
    if cle not in _META:
        _META[cle] = json.load(open(os.path.join(cache_dir, 'police_image', cle, 'police.json'), encoding='utf-8'))
    return _META[cle]


def _image(cle, cache_dir, f):
    k = (cle, f)
    if k not in _IMG:
        _IMG[k] = _png(os.path.join(cache_dir, 'police_image', cle, f))
    return _IMG[k]


# ------------------------------------------------------------------ agrandissement net (Lanczos 3, séparable)
def _lanczos(n_in, n_out):
    s = n_in / n_out
    x = (np.arange(n_out) + 0.5) * s - 0.5
    sup = 3 * max(1.0, s)
    i0 = np.floor(x - sup).astype(int) + 1
    taps = int(np.ceil(2 * sup)) + 1
    idx = i0[:, None] + np.arange(taps)[None, :]
    t = (x[:, None] - idx) / max(1.0, s)
    w = np.sinc(t) * np.sinc(t / 3) * (np.abs(t) < 3)
    w /= np.maximum(w.sum(1, keepdims=True), 1e-8)
    return np.clip(idx, 0, n_in - 1), w.astype(np.float32)


def redim(im, w, h):
    w, h = max(1, int(round(w))), max(1, int(round(h)))
    p = np.concatenate([im[..., :3] * im[..., 3:], im[..., 3:]], -1)      # prémultiplié
    iy, wy = _lanczos(p.shape[0], h)
    p = (p[iy] * wy[..., None, None]).sum(1)
    ix, wx = _lanczos(p.shape[1], w)
    p = (p[:, ix] * wx[None, :, :, None]).sum(2)
    p = np.clip(p, 0, None); a = np.clip(p[..., 3:], 0, 1)
    return np.concatenate([np.where(a > 1e-4, np.clip(p[..., :3] / np.maximum(a, 1e-4), 0, 1), 0), a], -1)


# ------------------------------------------------------------------ caractères absents : accents faits avec les signes
ACCENTS = {'é': ('e', '´'), 'è': ('e', '`'), 'ê': ('e', '^'), 'ë': ('e', '¨'), 'à': ('a', '`'), 'â': ('a', '^'), 'ä': ('a', '¨'),
           'á': ('a', '´'), 'î': ('i', '^'), 'ï': ('i', '¨'), 'í': ('i', '´'), 'ô': ('o', '^'), 'ö': ('o', '¨'), 'ó': ('o', '´'),
           'û': ('u', '^'), 'ü': ('u', '¨'), 'ù': ('u', '`'), 'ú': ('u', '´'), 'ñ': ('n', '~'), 'ç': ('c', '¸'),
           'É': ('E', '´'), 'È': ('E', '`'), 'Ê': ('E', '^'), 'À': ('A', '`'), 'Â': ('A', '^'), 'Ç': ('C', '¸'), 'Ñ': ('N', '~'),
           'Ü': ('U', '¨'), 'Ö': ('O', '¨'), 'Ä': ('A', '¨'), 'Ô': ('O', '^'), 'Î': ('I', '^'), 'Û': ('U', '^'), 'Ó': ('O', '´'),
           'Á': ('A', '´'), 'Í': ('I', '´'), 'Ú': ('U', '´')}
EQUIV = {'’': "'", '“': '"', '”': '"', '«': '"', '»': '"', '–': '-', '—': '-', '…': '.'}


def _glyphe(cle, cache_dir, c):
    """-> (image RGBA, métriques) dans les pixels de la planche ; None si impossible"""
    M = _meta(cle, cache_dir)['caracteres']
    c = EQUIV.get(c, c)
    if c in M:
        return _image(cle, cache_dir, M[c]['f']), M[c]
    if c in '¡¿':
        g = _glyphe(cle, cache_dir, '!' if c == '¡' else '?')
        if not g:
            return None
        im, m = g
        im = im[::-1, ::-1].copy()                 # retourné (rotation de 180°)
        h = im.shape[0]
        # la pointe en haut devient le bas : même encombrement, posé sur la ligne de base comme le « ! »
        return im, dict(m, y0=m['haut'] - (h - 1 - (m['bas'] - m['y0'])))     # même hauteur que « ! » / « ? »
    if c in ACCENTS:
        b, acc = ACCENTS[c]
        gb = _glyphe(cle, cache_dir, b)
        if not gb:
            return None
        im_b, mb = gb
        H0 = _meta(cle, cache_dir)['H0']
        if acc == '¨':
            gp = _glyphe(cle, cache_dir, '.')
            if not gp:
                return None
            pieces = [(gp[0], gp[1], 0.75, -0.17), (gp[0], gp[1], 0.75, 0.17)]
        elif acc == '´':
            gp = _glyphe(cle, cache_dir, '`')
            if not gp:
                return None
            pieces = [(gp[0][:, ::-1].copy(), gp[1], 0.9, 0.0)]
        elif acc == '¸':
            gp = _glyphe(cle, cache_dir, ',')
            if not gp:
                return None
            pieces = [(gp[0], gp[1], 0.7, 0.0)]
        else:
            gp = _glyphe(cle, cache_dir, acc)
            if not gp:
                return None
            pieces = [(gp[0], gp[1], 0.8, 0.0)]
        # toile assez grande, la lettre à sa place
        hb, wb = im_b.shape[:2]
        marge = int(H0)
        T = np.zeros((hb + 2 * marge, wb + 2 * marge, 4), np.float32)
        T[marge:marge + hb, marge:marge + wb] = im_b
        ox = mb['x0'] - marge; oy = mb['y0'] - marge          # origine de la toile (x planche, y relatif à la base)
        for im_a, ma, k, dx in pieces:
            g = redim(im_a, im_a.shape[1] * k, im_a.shape[0] * k)
            ha = (ma['bas'] - ma['haut']) * k                    # hauteur du signe (remplissage)
            if acc == '¸':
                y_haut = 0.02 * H0                                # sous la ligne de base
            else:
                y_haut = mb['haut'] - 0.1 * H0 - ha              # au-dessus de la lettre
            h_milieu = -(y_haut + ha / 2)                         # hauteur au-dessus de la base (pour l'italique)
            cx = mb['cx'] + dx * H0 + PENTE * h_milieu           # x réel du centre à cette hauteur
            # position de l'image du signe : son remplissage centré sur cx, son haut à y_haut
            ax = cx - (ma['cx'] - ma['x0'] + PENTE * 0) * k
            ay = y_haut - (ma['haut'] - ma['y0']) * k
            X, Y = int(round(ax - ox)), int(round(ay - oy))
            d = T[max(0, Y):Y + g.shape[0], max(0, X):X + g.shape[1]]
            gg = g[max(0, -Y):max(0, -Y) + d.shape[0], max(0, -X):max(0, -X) + d.shape[1]]
            al = gg[..., 3:] + d[..., 3:] * (1 - gg[..., 3:])
            d[..., :3] = np.where(al > 1e-4, (gg[..., :3] * gg[..., 3:] + d[..., :3] * d[..., 3:] * (1 - gg[..., 3:])) / np.maximum(al, 1e-4), 0)
            d[..., 3:] = al
        ys, xs = np.nonzero(T[..., 3] > 0.003)
        T = T[ys.min():ys.max() + 1, xs.min():xs.max() + 1]
        m = dict(mb, x0=ox + xs.min(), y0=oy + ys.min(), haut=min(mb['haut'], (ys.min() + oy) + 0.0) if acc != '¸' else mb['haut'])
        return T, m
    return None


def composer(texte, cle, cache_dir, largeur=1728, hauteur=352, capitale=None):
    """texte -> image RGBA uint8 (hauteur x largeur) écrite avec la police-image « cle », centrée"""
    if not str(texte or '').strip():            # (24/11) texte vide : bannière vide
        return np.zeros((hauteur, largeur, 4), np.uint8), []
    meta = _meta(cle, cache_dir)
    H0, ecart = meta['H0'], meta['ecart']
    espace = 0.38 * H0
    items, manquantes, x = [], [], 0.0
    for c in texte:
        if c.isspace():
            x += espace; continue
        g = _glyphe(cle, cache_dir, c)
        if not g:
            manquantes.append(c); continue
        im, m = g
        # place de l'image : son coin = x du stylo + (x0 - gauche redressée), corrigé de l'italique au haut de l'image
        px = x + (m['x0'] - m['gauche']) - PENTE * m['y0']
        items.append((im, px, m['y0']))
        x += m['larg'] + ecart
    if not items:
        raise ValueError('aucun caractère pour « %s »' % texte)
    gx = min(px for _, px, _ in items); dx = max(px + im.shape[1] for im, px, _ in items)
    hy = min(py for _, _, py in items); by = max(py + im.shape[0] for im, _, py in items)
    cap = capitale or 0.62 * hauteur
    s = min(cap / H0, (largeur - 40) / (dx - gx), (hauteur - 8) / (by - hy))
    toile_bas = np.zeros((hauteur, largeur, 4), np.float32)
    toile_haut = np.zeros((hauteur, largeur, 4), np.float32)
    ox = (largeur - (dx - gx) * s) / 2 - gx * s
    oy = (hauteur - (by - hy) * s) / 2 - hy * s

    def sur(dst, src, X, Y):
        d = dst[max(0, Y):Y + src.shape[0], max(0, X):X + src.shape[1]]
        g = src[max(0, -Y):max(0, -Y) + d.shape[0], max(0, -X):max(0, -X) + d.shape[1]]
        al = g[..., 3:] + d[..., 3:] * (1 - g[..., 3:])
        d[..., :3] = np.where(al > 1e-4, (g[..., :3] * g[..., 3:] + d[..., :3] * d[..., 3:] * (1 - g[..., 3:])) / np.maximum(al, 1e-4), 0)
        d[..., 3:] = al
    for im, px, py in items:
        g = redim(im, im.shape[1] * s, im.shape[0] * s) if abs(s - 1) > 1e-3 else im
        X, Y = int(round(ox + px * s)), int(round(oy + py * s))
        haut = (g[..., 3:] > 0.6).astype(np.float32)          # la lettre (remplissage, contour) : au-dessus des lueurs voisines
        sur(toile_bas, np.concatenate([g[..., :3], g[..., 3:] * (1 - haut)], -1), X, Y)
        sur(toile_haut, np.concatenate([g[..., :3], g[..., 3:] * haut], -1), X, Y)
    sur(toile_bas, toile_haut, 0, 0)
    return (np.clip(toile_bas, 0, 1) * 255 + 0.5).astype(np.uint8), manquantes


def ecrire(texte, cle, cache_dir, png):
    from .g4 import images as I
    im, manquantes = composer(texte, cle, cache_dir)
    I.ecrire_png(png, im.shape[1], im.shape[0], [im[y].tobytes() for y in range(im.shape[0])])
    return manquantes
