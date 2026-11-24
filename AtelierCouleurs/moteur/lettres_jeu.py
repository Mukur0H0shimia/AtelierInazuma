"""(23/11/2026, demande de muku : « je veux les lettres du jeu pour les bannières de base ») LETTRES DES BANNIÈRES DU JEU.

Le jeu n'a PAS de police pour ses bannières de techniques : chacune est une image toute faite (dx11/menu/220_img/telop_waza/
fr/<code>.g4tx, 1728 x 352), texte compris (lettres remplies d'une image colorée, contour blanc, ombre). On connaît le texte
de chaque image (nom français de la technique, skill_text) : on DÉCOUPE les lettres de ces images pour en faire un alphabet,
puis on écrit n'importe quel nom avec.

Découpage (vérifié sur « Trampoline du tonnerre ») : l'intérieur coloré des lettres (saturation > 60, alpha > 200) donne un
morceau par lettre ; les petits morceaux au-dessus d'un autre (points, accents) lui sont rattachés. Une bannière n'est gardée
que si elle a exactement un morceau par lettre (sinon deux lettres collées) et une seule ligne. Chaque pixel visible de
l'image (contour, ombre) va au morceau le plus proche (croissance depuis les morceaux) : la lettre ENTIÈRE est découpée.
Mesures : ligne de base et hauteur des minuscules (a c e m n o r s u v w x z) de la bannière -> lettres ramenées à la même
taille. Un alphabet PAR ÉLÉMENT (couleur du remplissage : bleu air, rouge feu…).
"""
import os, glob, json, struct, zlib
import numpy as np

ELEMENTS = {1: 'wind', 2: 'forest', 3: 'fire', 4: 'mountain', 5: 'void'}
MINUSCULES = set('acemnorsuvwxz')
XH = 100.0                                   # hauteur des minuscules dans l'alphabet (pixels)
# (24/11, demande de danifdez : « ajoute le ñ comme le ç, et á í ó ú… ») les lettres absentes des bannières françaises sont prises
# dans les bannières du jeu des AUTRES langues (telop_waza/es, pt, de, it, en : ñ Cañón…, ó á í ú Á Í Ó Ú ¡ ã õ ä ö ü ß ù…) ;
# celles du français ne changent pas. Version de l'alphabet : un ancien cache est refait une fois au démarrage.
VERSION_ALPHABET = 2
LANGUES_EN_PLUS = ('es', 'pt', 'de', 'it', 'en')


def _noms_fr(data_dir, langue='fr'):
    """code -> (nom dans la langue, élément, bannière) des techniques du jeu (skill_config + text/<langue>/skill_text)"""
    from . import techniques
    noms = techniques._textes(data_dir, langue)
    sc = open(sorted(glob.glob(os.path.join(data_dir, 'common', 'gamedata', 'skill', 'skill_config_*.cfg.bin')))[-1], 'rb').read()
    out = {}
    for p in glob.glob(os.path.join(data_dir, 'dx11', 'menu', '220_img', 'telop_waza', langue, 'wh*.g4tx')):
        code = os.path.basename(p)[:-5]
        if '_' in code:
            continue
        i = sc.find(struct.pack('<I', zlib.crc32(code.encode())))
        if i < 8:
            continue
        r = struct.unpack_from('<20i', sc, i - 8)
        nom = noms.get(r[8])
        if nom:
            out[code] = (nom, ELEMENTS.get((r[13] & 0xFFFFFFFF) & 0xFF, 'neutre'), p, False)
    # (23/11) bannières des esprits guerriers et totems (k… / a…) : ligne du haut = nom court de la commande d'aura
    # (aura_skill_config : col. 2 = son texte, col. 7 = crc32 du modèle, col. 8 = élément) ; « Warborg » donne le W majuscule
    from . import cfgbin
    try:
        f = sorted(glob.glob(os.path.join(data_dir, 'common', 'gamedata', 'skill', 'aura_skill_config_*.cfg.bin')))[-1]
        tw = os.path.join(data_dir, 'dx11', 'menu', '220_img', 'telop_waza', langue)
        par_crc = {zlib.crc32(os.path.basename(p)[:-5].encode()): os.path.basename(p)[:-5] for p in glob.glob(os.path.join(tw, '[ak]0*.g4tx'))}
        for _, v in cfgbin.lire(open(f, 'rb').read()):
            if len(v) > 8 and isinstance(v[1], str) and v[1][:2] in ('wk', 'ws') and isinstance(v[7], int):
                k = par_crc.get(v[7] & 0xFFFFFFFF)
                if k and k not in out and noms.get(v[2]):
                    out[k] = (noms[v[2]], ELEMENTS.get(v[8], 'neutre'), os.path.join(tw, k + '.g4tx'), True)
    except Exception as ex:
        print('bannières des esprits :', ex)
    return out


def _composantes(m):
    h, w = m.shape
    lab = np.zeros((h, w), np.int32)
    out = []
    for y0, x0 in np.argwhere(m):
        if lab[y0, x0]:
            continue
        n = len(out) + 1
        pile = [(y0, x0)]; lab[y0, x0] = n; ys, xs = [], []
        while pile:
            y, x = pile.pop(); ys.append(y); xs.append(x)
            for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                yy, xx = y + dy, x + dx
                if 0 <= yy < h and 0 <= xx < w and m[yy, xx] and not lab[yy, xx]:
                    lab[yy, xx] = n; pile.append((yy, xx))
        out.append((np.array(ys), np.array(xs)))
    return out


def _croissance(visible, graines):
    """chaque pixel visible -> n° de la graine la plus proche (parcours en largeur depuis toutes les graines)"""
    h, w = visible.shape
    lab = np.zeros((h, w), np.int32)
    front = []
    for n, (ys, xs) in enumerate(graines, 1):
        lab[ys, xs] = n
        front += list(zip(ys.tolist(), xs.tolist()))
    while front:
        suivant = []
        for y, x in front:
            n = lab[y, x]
            for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                yy, xx = y + dy, x + dx
                if 0 <= yy < h and 0 <= xx < w and visible[yy, xx] and not lab[yy, xx]:
                    lab[yy, xx] = n; suivant.append((yy, xx))
        front = suivant
    return lab


def decouper(a, nom, haut_seulement=False, bas_seulement=False, clair=False, cap=None, fusion=False, sans_jaune=False):
    """a = image RGBA (352 x 1728) d'une bannière, nom = son texte -> [(lettre, image RGBA, gauche, haut, base, xh)] ou None"""
    lettres = [c for c in nom if not c.isspace()]
    ai = a.astype(np.int32)
    sat = ai[..., :3].max(-1) - ai[..., :3].min(-1)
    # (24/11) totems : lettres claires (dégradé cyan coupé d'une bande blanche) dans un contour bleu foncé -> l'intérieur CLAIR
    rempl = ((ai[..., 3] > 200) & ((ai[..., :3].max(-1) > 170) if clair else (sat > 60)))
    if sans_jaune:                                 # (24/11, armure) le contour jaune pâle relie les lettres : remplissage rouge-violet seul
        rempl &= ai[..., 1] < 140
    rempl = rempl[::2, ::2]
    comps = [c for c in _composantes(rempl) if len(c[0]) > 12]
    if not comps:
        return None
    comps.sort(key=lambda c: -len(c[0]))
    groupes = []                                  # gros morceaux d'abord ; un petit au-dessus d'un gros lui est rattaché
    for ys, xs in comps:
        x0, x1 = xs.min(), xs.max()
        for g in groupes:
            gx0, gx1 = g[1].min(), g[1].max()
            recouvre = min(x1, gx1) - max(x0, gx0)
            if len(ys) < 0.35 * len(g[0]) and recouvre > 0.5 * (x1 - x0 + 1) and ys.max() < g[0].min() + 0.5 * (g[0].max() - g[0].min()):
                g[0] = np.concatenate([g[0], ys]); g[1] = np.concatenate([g[1], xs]); break
        else:
            groupes.append([ys, xs])
    tous = list(groupes)                          # (tous les morceaux se partagent les pixels, même ceux de l'autre ligne)
    if haut_seulement and not bas_seulement:
        # (23/11) bannières d'esprits / totems : 2 lignes (« Warborg » / « Le titan des murailles ») ; seule celle du haut
        # (le nom court, connu) est lue : coupure au plus grand écart vertical entre les morceaux
        cy = sorted(g[0].mean() for g in groupes)
        ecarts = [(cy[i + 1] - cy[i], i) for i in range(len(cy) - 1)]
        if ecarts and max(ecarts)[0] > 35:
            lim = cy[max(ecarts)[1]] + max(ecarts)[0] / 2
            groupes = [g for g in groupes if g[0].mean() < lim]
    if bas_seulement:
        # (24/11) bannières de totems : « Totem » petit en haut, le NOM en grand dessous -> la ligne du bas seulement
        cy = sorted(g[0].mean() for g in groupes)
        ecarts = [(cy[i + 1] - cy[i], i) for i in range(len(cy) - 1)]
        if not ecarts or max(ecarts)[0] <= 25:
            return None
        lim = cy[max(ecarts)[1]] + max(ecarts)[0] / 2
        groupes = [g for g in groupes if g[0].mean() > lim]
    # (23/11) deux lettres collées (« rb » de Warborg) : le morceau le plus large (> 1,5 fois la largeur médiane) est coupé à la
    # colonne la plus mince de son milieu, tant qu'il manque des morceaux
    while 0 < len(groupes) < len(lettres):
        larg = [g[1].max() - g[1].min() + 1 for g in groupes]
        i = int(np.argmax(larg))
        if larg[i] < 1.5 * float(np.median(larg)):
            break
        ys, xs = groupes[i]
        x0 = xs.min()
        cols = np.bincount(xs - x0, minlength=larg[i])
        a_, b_ = int(larg[i] * 0.25), int(larg[i] * 0.75)
        coupe = x0 + a_ + int(np.argmin(cols[a_:b_ + 1]))
        gauche, droite = xs < coupe, xs >= coupe
        orig = groupes[i]
        groupes[i:i + 1] = [[ys[gauche], xs[gauche]], [ys[droite], xs[droite]]]
        tous = [g for g in tous if g is not orig] + groupes[i:i + 2]
    # (24/11, totems) un morceau de trop (reflet détaché d'une lettre) : le plus petit, s'il est petit, rejoint la lettre la plus proche
    while (clair or fusion) and len(groupes) > len(lettres) > 0:      # (+ point du « ! » sous la barre : armure)
        tailles = [len(g[0]) for g in groupes]
        i = int(np.argmin(tailles))
        if tailles[i] > 0.4 * float(np.median(tailles)):
            break
        petit = groupes.pop(i); ys, xs = petit
        j = int(np.argmin([abs(g[1].mean() - xs.mean()) + abs(g[0].mean() - ys.mean()) for g in groupes]))
        vieux = groupes[j]
        groupes[j] = [np.concatenate([vieux[0], ys]), np.concatenate([vieux[1], xs])]
        tous = [g for g in tous if g is not vieux and g is not petit] + [groupes[j]]
    if len(groupes) != len(lettres):
        return None
    groupes.sort(key=lambda g: g[1].mean())
    centres = [g[0].mean() for g in groupes]
    if max(centres) - min(centres) > 60:          # deux lignes (ou lettres très décalées) : pas gardée
        return None
    ref = [(g[0].max(), g[0].max() - g[0].min()) for g, c in zip(groupes, lettres) if c in MINUSCULES]
    if len(ref) < 2 and cap:
        # (24/11) mot tout en capitales (ARMED) : hauteur des capitales = cap x hauteur des minuscules (mesurée sur l'alphabet)
        ref = [(g[0].max(), (g[0].max() - g[0].min()) / cap) for g in groupes]
    if len(ref) < 2:
        return None
    base = float(np.median([r[0] for r in ref])) * 2
    xh = float(np.median([r[1] for r in ref])) * 2
    if xh < 30:
        return None
    # (23/11, retour de muku : « certaines lettres ont des ombres bizarres ») l'ombre des bannières du jeu est faite de pixels
    # NOIRS (LU : bloc noir décalé en bas à droite, alpha ~0,85, puis ombre douce) : elle n'est pas gardée dans les lettres
    # (coupée entre deux lettres, elle faisait des taches) ; composer() refait UNE ombre sous tout le texte
    noir = ai[..., :3].max(-1) < 30
    a = a.copy()
    a[..., 3] = np.where(noir, 0, a[..., 3])
    visible = (a[..., 3] > 8)[::2, ::2]
    autres = [g for g in tous if not any(g is h for h in groupes)]
    lab = _croissance(visible, [(g[0], g[1]) for g in groupes + autres])
    lab2 = np.kron(lab, np.ones((2, 2), np.int32))[:a.shape[0], :a.shape[1]]
    out = []
    for n, c in enumerate(lettres, 1):
        ys, xs = np.nonzero(lab2 == n)
        if not len(ys):
            return None
        y0, y1, x0, x1 = ys.min(), ys.max() + 1, xs.min(), xs.max() + 1
        im = a[y0:y1, x0:x1].copy()
        im[..., 3] = np.where(lab2[y0:y1, x0:x1] == n, im[..., 3], 0)
        out.append((c, im, int(x0), int(y0), base, xh))
    return out


def _signature(im, haut, h, larg):
    """forme d'une lettre : masque 16 x 16 de sa partie opaque + sa place (haut / hauteur / largeur en hauteurs de minuscule)"""
    m = (im[..., 3] > 128).astype(np.float32)
    ys = (np.arange(16) * m.shape[0] / 16).astype(int); xs = (np.arange(16) * m.shape[1] / 16).astype(int)
    return np.concatenate([m[ys][:, xs].ravel(), [haut * 4, h * 4, larg * 4]])


def construire(cfg, cache_dir, max_par_lettre=8, journal=print):
    """alphabet du jeu : cache/lettres_jeu/<élément>/<n° unicode>_<k>.png + alphabet.json (mesures en unités XH)"""
    from . import ui_jeu
    from .g4 import images as _img
    d = os.path.join(cache_dir, 'lettres_jeu')
    os.makedirs(d, exist_ok=True)
    alpha, signatures = {}, {}
    gardees = 0
    noms = _noms_fr(cfg['data_dir'])
    # français d'abord (toutes les lettres), puis les autres langues : seulement les lettres que le français n'a pas
    taches = [(code, v, None) for code, v in sorted(noms.items())]
    for lg in LANGUES_EN_PLUS:
        try:
            taches += [(code, v, lg) for code, v in sorted(_noms_fr(cfg['data_dir'], lg).items())]
        except Exception as ex:
            journal('bannières %s : %s' % (lg, ex))
    deja = None
    for k, (code, (nom, el, p, haut), lg) in enumerate(taches):
        if lg and deja is None:
            deja = set(signatures)                     # lettres déjà prises dans les bannières françaises
        if lg and not any(ch not in deja and ch.strip() for ch in nom):
            continue                                   # rien de nouveau dans ce nom : bannière pas lue
        try:
            _, _, g = ui_jeu.lire_planche(p)
            _, _, a = ui_jeu._rgba(g.blocs[0])
            r = decouper(a, nom, haut)
        except Exception as ex:
            journal('%s : %s' % (code, ex)); continue
        if not r:
            continue
        gardees += 1
        for c, im, x0, y0, base, xh in r:
            if lg and c in deja:
                continue
            sig = _signature(im, (y0 - base) / xh, im.shape[0] / xh, im.shape[1] / xh)
            signatures.setdefault(c, []).append(sig)
            L = alpha.setdefault(el, {}).setdefault(c, [])
            if len(L) >= max_par_lettre and xh <= min(x['xh'] for x in L):
                continue
            L.append({'im': im, 'x': x0, 'haut': (y0 - base) / xh, 'larg': im.shape[1] / xh, 'h': im.shape[0] / xh, 'xh': xh, 'code': code, 'sig': sig})
            L.sort(key=lambda x: -x['xh']); del L[max_par_lettre:]
        if k % 100 == 0:
            journal('lettres du jeu : %d / %d bannières, %d gardées' % (k, len(taches), gardees))
    # (23/11, essai : un « T » sorti en minuscule = une bannière mal découpée) chaque lettre : la forme MÉDIANE de tous ses
    # exemples (tous éléments) ; les exemples gardés sont triés par ressemblance, les trop différents sont écartés
    for c, S in signatures.items():
        S = np.array(S)
        med = S[np.argmin(((S[:, None] - S[None]) ** 2).sum(-1).sum(-1))] if len(S) <= 150 else np.median(S, 0)
        lim = np.percentile(((S - med) ** 2).sum(-1), 70) * 1.5 + 1e-6
        for el in alpha:
            L = alpha[el].get(c)
            if not L:
                continue
            for x in L:
                x['dist'] = float(((x['sig'] - med) ** 2).sum())
            L[:] = sorted([x for x in L if x['dist'] <= lim], key=lambda x: x['dist'])[:3]
            if not L:
                del alpha[el][c]
    index = {}
    for el, lettres in alpha.items():
        os.makedirs(os.path.join(d, el), exist_ok=True)
        for c, L in lettres.items():
            for i, x in enumerate(L):
                f = '%s/%d_%d.png' % (el, ord(c), i)
                im = x['im']
                _img.ecrire_png(os.path.join(d, f), im.shape[1], im.shape[0], [im[y].tobytes() for y in range(im.shape[0])])
                index.setdefault(el, {}).setdefault(c, []).append({'f': f, 'haut': x['haut'], 'larg': x['larg'], 'h': x['h'], 'xh': x['xh'], 'code': x['code']})
    json.dump({'version': VERSION_ALPHABET, 'bannieres': len(taches), 'gardees': gardees, 'alphabet': index},
              open(os.path.join(d, 'alphabet.json'), 'w', encoding='utf-8'), ensure_ascii=False)
    return index


# ------------------------------------------------------------------ écrire un nom avec les lettres du jeu
_ALPHA = {}


def _alphabet(cache_dir):
    f = os.path.join(cache_dir, 'lettres_jeu', 'alphabet.json')
    if f not in _ALPHA:
        j = json.load(open(f, encoding='utf-8')) if os.path.exists(f) else {}
        _ALPHA[f] = j['alphabet'] if j.get('version') == VERSION_ALPHABET else None     # ancien alphabet (français seul) : refait
        fs = os.path.join(cache_dir, 'lettres_jeu', 'styles.json')     # (24/11) + styles esprit guerrier / totem
        if _ALPHA[f] is not None and os.path.exists(fs):
            st = json.load(open(fs, encoding='utf-8'))
            if st.get('version') == VERSION_STYLES:
                _ALPHA[f] = dict(_ALPHA[f], **st['alphabet'])
                _ALPHA[f]['_totem_haut'] = st.get('totem_haut')
                _ALPHA[f]['_gains'] = st.get('gains_esprit') or {}
    return _ALPHA[f]


def styles_disponibles(cache_dir):
    fs = os.path.join(cache_dir, 'lettres_jeu', 'styles.json')
    try:
        return json.load(open(fs, encoding='utf-8')).get('version') == VERSION_STYLES
    except (OSError, ValueError):
        return False


def disponible(cache_dir):
    return bool(_alphabet(cache_dir))


def _lire(cache_dir, f):
    from .g4 import images as _img
    w, h, rows = _img.lire_png(os.path.join(cache_dir, 'lettres_jeu', f))
    return np.frombuffer(b''.join(bytes(r) for r in rows), np.uint8).reshape(h, w, 4).astype(np.float32) / 255


def _teinte(im):
    """teinte moyenne (cercle chromatique, 0-1) des pixels colorés d'une lettre"""
    rgb, a = im[..., :3], im[..., 3]
    mx, mn = rgb.max(-1), rgb.min(-1)
    m = (a > 0.8) & (mx - mn > 0.25)
    if not m.any():
        return None
    r, g, b = rgb[..., 0][m], rgb[..., 1][m], rgb[..., 2][m]
    ang = np.arctan2(np.sqrt(3) * (g - b), 2 * r - g - b)          # teinte en angle
    return float(np.arctan2(np.sin(ang).mean(), np.cos(ang).mean()))


_TEINTES = {}


def _teinte_element(cache_dir, el):
    """teinte des lettres de cet élément (mesurée sur ses « o », « e », « a »)"""
    if el not in _TEINTES:
        A = (_alphabet(cache_dir) or {}).get(el) or {}
        t = [x for c in 'oeaun' for x in [(_teinte(_lire(cache_dir, A[c][0]['f'])) if A.get(c) else None)] if x is not None]
        _TEINTES[el] = float(np.arctan2(np.mean(np.sin(t)), np.mean(np.cos(t)))) if t else None
    return _TEINTES[el]


def _recolorer(im, de, vers):
    """tourne la teinte des pixels colorés de « de » vers « vers » (lettre prise dans un autre élément)"""
    rgb = im[..., :3]
    gris = rgb.mean(-1, keepdims=True)
    v = rgb - gris                                   # partie colorée, tournée autour de l'axe des gris
    d = vers - de
    k = np.array([1, 1, 1], np.float32) / np.sqrt(3)
    c, s = np.cos(d), np.sin(d)
    rot = v * c + np.cross(k, v) * s + k * (v @ k)[..., None] * (1 - c)
    out = im.copy()
    out[..., :3] = np.clip(gris + rot, 0, 1)
    return out


_PALETTES = {}


def _palette_element(cache_dir, el):
    """(24/11) couleurs des lettres de cet élément rangées du plus sombre au plus clair (pixels colorés de ses o, e, a, u, n)"""
    if el not in _PALETTES:
        A = (_alphabet(cache_dir) or {}).get(el) or {}
        px = []
        for c in 'oeaun':
            if A.get(c):
                im = _lire(cache_dir, A[c][0]['f']); rgb, a = im[..., :3], im[..., 3]
                m = (a > 0.8) & (rgb.max(-1) - rgb.min(-1) > 0.12)
                px.append(rgb[m])
        if px:
            P = np.concatenate(px); P = P[np.argsort(P.mean(-1))]
            _PALETTES[el] = P[np.linspace(0, len(P) - 1, 256).astype(int)]
        else:
            _PALETTES[el] = None
    return _PALETTES[el]


def _vers_palette(im, pal):
    """(24/11, lettres espagnoles de danifdez) lettre d'un autre élément repeinte à la palette de celui-ci : chaque pixel coloré
    prend la couleur de même rang de clarté (le plus sombre -> le plus sombre…) ; contour blanc, reflets et ombre grise gardés.
    Avant : rotation de la teinte (un Á bleu tourné vers le feu sortait olive / vert)."""
    rgb, a = im[..., :3], im[..., 3]
    m = (a > 0.05) & (rgb.max(-1) - rgb.min(-1) > 0.12)
    if not m.any():
        return im
    lum = rgb[m].mean(-1)
    rang = np.argsort(np.argsort(lum)) / max(1, lum.size - 1)
    out = im.copy()
    out[..., :3][m] = pal[np.clip((rang * (len(pal) - 1)).astype(int), 0, len(pal) - 1)]
    return out


def _lettre(cache_dir, el, c):
    """(image RGBA float, mesures) de la lettre c : l'alphabet de l'élément ; sinon celle d'un autre élément RECOLORÉE à la
    teinte de cet élément ; sinon None"""
    A = _alphabet(cache_dir) or {}
    # (24/11) style « esprit:<élément> » : lettres des bannières d'esprits guerriers, puis celles de l'élément ; « totem » : lettres
    # du grand nom des bannières de totems ; « armure » : lettres Néant (le remplissage d'ARMED) teintées comme la bannière ARMED
    if el == 'totem':
        L = (A.get('totem') or {}).get(c)
        if L:
            return _lire(cache_dir, L[0]['f']), L[0]
        return None
    if el == 'armure':
        # (24/11, muku : « le style armure ne ressemble pas du tout ») LU : la bannière de mise en armure (aura_armed01) est
        # écrite dans chaque langue (« Armure ! », « Armourfy! », « ¡Armadura! », « Rüstung! », « Armatura! ») : remplissage
        # rouge -> violet, contour jaune pâle. Ses lettres découpées dans les 6 ; une lettre absente : celle d'un autre élément
        # habillée pareil (teinte de l'armure, contour blanc -> jaune pâle)
        L = (A.get('armure') or {}).get(c)
        if L:
            return _lire(cache_dir, L[0]['f']), L[0]
        r = _lettre(cache_dir, 'void', c)
        if r is not None:
            im = _habiller_armure(cache_dir, r[0], r[1].get('xh'))
            k = r[0].shape[0] / max(1e-6, r[1]['h'])               # pixels par unité (x-height)
            im2, dy, dx = _recadrer(im)
            pad_ = (im.shape[0] - r[0].shape[0]) / 2                   # marge ajoutée autour (contour dessiné)
            return im2, dict(r[1], haut=r[1]['haut'] + (dy - pad_) / k, h=im2.shape[0] / k, larg=im2.shape[1] / k)
        return None
    if el.startswith('esprit:'):                  # (essai 24/11 : les seules lettres des bannières d'esprits sont mal découpées)
        el = el[len('esprit:'):]
    for e in [el] + [x for x in ('wind', 'fire', 'forest', 'mountain', 'void', 'neutre') if x != el]:
        L = (A.get(e) or {}).get(c)
        if L:
            x = L[0]
            im = _lire(cache_dir, x['f'])
            if e != el:
                pal = _palette_element(cache_dir, el)
                if pal is not None:
                    im = _vers_palette(im, pal)
                else:
                    t0, t1 = _teinte(im), _teinte_element(cache_dir, el)
                    if t0 is not None and t1 is not None:
                        im = _recolorer(im, t0, t1)
            return im, x
    return None


def _redim(im, w, h):
    """redimensionnement bilinéaire (numpy seul)"""
    H, W = im.shape[:2]
    ys = np.clip((np.arange(h) + 0.5) * H / h - 0.5, 0, H - 1)
    xs = np.clip((np.arange(w) + 0.5) * W / w - 0.5, 0, W - 1)
    y0 = np.floor(ys).astype(int); x0 = np.floor(xs).astype(int)
    y1 = np.minimum(y0 + 1, H - 1); x1 = np.minimum(x0 + 1, W - 1)
    fy = (ys - y0)[:, None, None]; fx = (xs - x0)[None, :, None]
    p = im[..., :3] * im[..., 3:]                  # couleurs prémultipliées (pas de bord sombre)
    p = np.concatenate([p, im[..., 3:]], -1)
    r = (p[y0][:, x0] * (1 - fx) + p[y0][:, x1] * fx) * (1 - fy) + (p[y1][:, x0] * (1 - fx) + p[y1][:, x1] * fx) * fy
    a = r[..., 3:]
    return np.concatenate([np.where(a > 1e-4, r[..., :3] / np.maximum(a, 1e-4), 0), a], -1)


def composer(texte, element, cache_dir, largeur=1728, hauteur=352):
    if not str(texte or '').strip():            # (24/11) texte vide (pendant la frappe) : bannière vide, pas d'erreur
        return np.zeros((hauteur, largeur, 4), np.uint8), []
    return _composer_texte(texte, element, cache_dir, largeur, hauteur)


def _composer_texte(texte, element, cache_dir, largeur=1728, hauteur=352):
    """-> image RGBA uint8 (hauteur x largeur) du texte écrit avec les lettres du jeu, centré comme les bannières du jeu
    (24/11) styles : « esprit:<élément> » (comme les bannières d'esprits guerriers : nom, et 2e ligne après « / »), « totem »
    (le « Totem » du jeu en petit, le nom en grand dessous), « armure » (comme ARMED)"""
    if element == 'armure':                       # (24/11) texte du jeu (« Armure ! », « Armourfy! »…) : sa bannière, exacte
        cle_ = ''.join(texte.split()).lower()
        for lg, t_ in TEXTES_ARMURE.items():
            f_ = os.path.join(cache_dir, 'lettres_jeu', 'armure_%s.png' % lg)
            if cle_ == t_.lower() and os.path.exists(f_) and largeur == 1728 and hauteur == 352:
                return (np.clip(_lire(cache_dir, 'armure_%s.png' % lg), 0, 1) * 255 + 0.5).astype(np.uint8), []
    if element == 'totem' or element.startswith('esprit:'):
        return _composer_lignes(texte, element, cache_dir, largeur, hauteur)
    return _composer_ligne(texte, element, cache_dir, largeur, hauteur)


def _lettres_de(texte, element, cache_dir, manquantes):
    lettres = []
    for c in texte:
        if c.isspace():
            lettres.append(None); continue
        if element == 'totem':                    # (24/11) l'échantillon qui suit la lettre d'avant dans la même bannière, si possible
            prev = lettres[-1][1] if lettres and lettres[-1] else None
            cands = ((_alphabet(cache_dir) or {}).get('totem') or {}).get(c) or []
            if cands:
                ch = next((x for x in cands if prev and x.get('code') == prev.get('code') and x.get('rang') == (prev.get('rang') or -9) + 1), cands[0])
                lettres.append((_lire(cache_dir, ch['f']), ch)); continue
        L = _lettre(cache_dir, element, c) or _lettre(cache_dir, element, c.lower()) or _lettre(cache_dir, element, c.upper())
        if L is None and c in "’'":                  # apostrophe : l'une ou l'autre
            L = _lettre(cache_dir, element, "'" if c == "’" else "’")
        if L is not None and element.startswith('esprit:'):   # bannières d'esprits : couleur mesurée sur celles du jeu (styles.json)
            gain = ((_alphabet(cache_dir) or {}).get('_gains') or {}).get(element[len('esprit:'):])
            if gain:
                im_ = L[0].copy(); rgb = im_[..., :3]
                coul = (rgb.max(-1) - rgb.min(-1) > 0.2)[..., None]
                im_[..., :3] = np.where(coul, np.clip(rgb * np.array(gain, np.float32), 0, 1), rgb)
                L = (im_, L[1])
        if L is not None and element.startswith('esprit:'):   # bannières d'esprits : lettres plus larges (LU k000010 / k000220)
            L = (L[0], dict(L[1], larg=L[1]['larg'] * 1.2))   # (24/11) mesuré : lettres des esprits plus larges (nos lettres viennent souvent de noms longs, serrés par le jeu)
        if L is None and element == 'totem':          # lettre absente des totems : celle des techniques, au bleu des totems
            L = _lettre(cache_dir, 'wind', c) or _lettre(cache_dir, 'wind', c.lower()) or _lettre(cache_dir, 'wind', c.upper())
        if L is None and c in '()[]':
            L = _parenthese(cache_dir, 'wind' if element == 'totem' else element, c)
        if L is None:                                   # (24/11) lettre accentuée qu'aucune bannière n'a (ì, ò…) : la lettre sans accent
            import unicodedata
            b_ = unicodedata.normalize('NFD', c)[0]
            if b_ != c and b_.strip():
                L = _lettre(cache_dir, element, b_) or _lettre(cache_dir, element, b_.lower())
                if L is None and element == 'totem':
                    L = _lettre(cache_dir, 'wind', b_)
        if L is None:
            manquantes.append(c); continue
        lettres.append(L)
    return lettres


def _gauches(lettres, chev=0.12, espace=0.45, paires=False):
    """bord gauche de chaque lettre (en xh, depuis 0) ; paires : deux lettres voisines de la même bannière du jeu -> écart du jeu"""
    out, cur, prev, prev_g = [], 0.0, None, 0.0
    for L in lettres:
        if L is None:
            out.append(None); cur += espace; prev = None; continue
        m = L[1]
        if paires and prev is not None and m.get('x') is not None and prev.get('code') == m.get('code') and m.get('rang') == (prev.get('rang') or -9) + 1:
            g = prev_g + (m['x'] - prev['x'])
        else:
            g = cur
        out.append(g); cur = g + m['larg'] - chev; prev, prev_g = m, g
    return out


def _poser(toile, lettres, x, base, xh, chev=0.12, espace=0.45, sans_halo=False, paires=False):
    x_depart = x
    gauches = _gauches(lettres, chev, espace, paires)
    for L, g_ in zip(lettres, gauches):
        if L is None:
            continue
        x = x_depart + g_ * xh
        im, m = L
        w, h = max(1, int(round(m['larg'] * xh))), max(1, int(round(m['h'] * xh)))
        g = _redim(im, w, h)
        if sans_halo:                             # (24/11) le halo coupé lettre par lettre faisait des marques : refait en un seul
            g = _sans_halo_ni_ombre(g, xh=xh)
        x0, y0 = int(round(x)), int(round(base + m['haut'] * xh))
        H_, W_ = toile.shape[:2]
        xa, ya, xb, yb = max(0, x0), max(0, y0), min(W_, x0 + w), min(H_, y0 + h)
        if xb > xa and yb > ya:
            s_ = g[ya - y0:yb - y0, xa - x0:xb - x0]
            d = toile[ya:yb, xa:xb]
            a = s_[..., 3:] + d[..., 3:] * (1 - s_[..., 3:])
            d[..., :3] = np.where(a > 1e-4, (s_[..., :3] * s_[..., 3:] + d[..., :3] * d[..., 3:] * (1 - s_[..., 3:])) / np.maximum(a, 1e-4), 0)
            d[..., 3:] = a


def _mesures(lettres, chev=0.12, espace=0.45, paires=False):
    gs = _gauches(lettres, chev, espace, paires)
    larg = max(g + L[1]['larg'] for L, g in zip(lettres, gs) if L)
    return larg, min(L[1]['haut'] for L in lettres if L), max(L[1]['haut'] + L[1]['h'] for L in lettres if L)


# (24/11, mesuré sur les bannières du jeu, fr/*.g4tx) : esprits guerriers et techniques = ombre noire, pas de halo ; totems =
# halo blanc (254,254,254), presque pas d'ombre ; armure = halo crème (248,224,200), presque pas d'ombre
HALOS = {'totem': (1.0, 1.0, 1.0), 'armure': (232 / 255, 212 / 255, 194 / 255)}   # armure : lueur claire (côté haut-gauche du jeu, 24/11)
# (24/11, muku : « des petits problèmes sur les ombrages ») LU : leurs lettres ont AUSSI une ombre grise décalée en bas à droite
# (totem a000020 : gris 90,90,92, alpha ~0,71 ; armure : 84,72,60) -> enlevée des lettres (coupée entre elles) et refaite d'un bloc
TEXTES_ARMURE = {'fr': 'Armure!', 'en': 'Armourfy!', 'es': '¡Armadura!', 'de': 'Rüstung!', 'it': 'Armatura!', 'pt': 'Armadura!'}
LUEUR2_ARMURE = (0.1, 0.3)                     # rayon (x-height), force de la lueur large
BORD_REMPL_ARMURE = 0.7
OMBRE_DESSUS = True                             # ombre au-dessus de la lueur (essais)
OMBRE_ARMURE = (0.06, 0.07, 0.5)              # décalage x, y (x-height), opacité de l'ombre de l'armure
LUEUR_ARMURE = (0.06, 2.0, 0.1, 0.9)          # rayon (x-height), gain, seuil, force — AJUSTÉ sur le profil du jeu, lueur sur l'ombre (24/11)
OMBRES = {'totem': (90 / 255, 90 / 255, 92 / 255), 'armure': (40 / 255, 33 / 255, 30 / 255)}   # armure : ombre sombre nette (zoom 24/11)


def _sans_halo_ni_ombre(g, large=False, xh=None):
    g = g.copy()
    rgb = g[..., :3]
    if xh:
        # (24/11, muku : « ça se voit qu'il y a des problèmes encore ») on garde seulement ce qui est PRÈS du remplissage de
        # la lettre (remplissage + épaisseur de son contour) : l'ombre de la lettre d'avant, prise dans la découpe, s'en va
        sat = rgb.max(-1) - rgb.min(-1)
        rempl = ((sat > 0.3) & (g[..., 3] > 0.5)).astype(np.float32)
        r = max(2, int((0.10 if large else 0.03) * xh))
        pres = _flou(rempl, r) > 0.01
        g[..., 3] = np.where(pres, g[..., 3], 0)
    gris = (rgb.max(-1) - rgb.min(-1) < 0.14) & (rgb.max(-1) > 0.15) & (rgb.max(-1) < 0.78)
    if large:                                     # armure : ombre mêlée au halo crème (brun clair, un peu coloré)
        r_, v_, b_ = rgb[..., 0], rgb[..., 1], rgb[..., 2]
        gris |= (r_ >= v_ - 0.02) & (v_ >= b_ - 0.02) & (r_ - b_ < 0.3) & (v_ > 0.2) & (rgb.max(-1) < 0.86)   # brun (ombre), jamais le violet
    g[..., 3] = np.where(gris, 0, np.clip((g[..., 3] - 0.45) / 0.35, 0, 1))
    return g


def _sur(dessus, dessous):
    """dessus par-dessus dessous (RGBA flottants)"""
    a = dessus[..., 3:] + dessous[..., 3:] * (1 - dessus[..., 3:])
    c = np.where(a > 1e-4, (dessus[..., :3] * dessus[..., 3:] + dessous[..., :3] * dessous[..., 3:] * (1 - dessus[..., 3:])) / np.maximum(a, 1e-4), 0)
    return np.concatenate([c, a], -1)


def _finir(toile, xh, element):
    if element not in HALOS:
        _ombre(toile, xh); return
    A = toile[..., 3]
    if element == 'armure':
        # (24/11, muku : « ne brille pas assez ») MESURÉ autour du contour du jeu : anneau chaud court (alpha 0,8 -> 0 en ~12 px
        # pour 13 px de contour), pas de brume large
        r_, k_, c_, f_ = LUEUR_ARMURE
        h = np.clip(_flou(A, max(2, int(r_ * xh))) * k_ - c_, 0, 1) * f_
        r2, f2 = LUEUR2_ARMURE                    # 2e couche : lueur large et faible (le jeu en a deux)
        if f2 > 0:
            h = np.maximum(h, np.clip(_flou(A, max(2, int(r2 * xh))) * 1.6, 0, 1) * f2)
    else:
        h = np.clip(_flou(A, max(2, int(0.10 * xh))) * 1.8, 0, 1) * 0.95
        h = np.maximum(h, _flou(A, max(3, int(0.22 * xh))) * 0.45)
    halo = np.concatenate([np.broadcast_to(np.array(HALOS[element], np.float32), A.shape + (3,)), h[..., None]], -1)
    o = _flou(_decale(A, 0.10 * xh, 0.09 * xh), max(1, int(0.02 * xh))) * 0.72 if element != 'armure' else \
        _flou(_decale(A, OMBRE_ARMURE[0] * xh, OMBRE_ARMURE[1] * xh), max(1, int(0.008 * xh))) * OMBRE_ARMURE[2]
    ombre = np.concatenate([np.broadcast_to(np.array(OMBRES[element], np.float32), A.shape + (3,)), o[..., None]], -1)
    # (24/11, zoom jeu / nous) l'ombre est SOUS la lueur : entre deux traits on voit la lueur claire, pas l'ombre
    toile[:] = _sur(toile, _sur(ombre, halo) if OMBRE_DESSUS else _sur(halo, ombre))


def _halo(toile, xh, couleur, force=0.95):
    A = toile[..., 3]
    h = np.clip(_flou(A, max(2, int(0.10 * xh))) * 1.8, 0, 1) * force
    h = np.maximum(h, _flou(A, max(3, int(0.22 * xh))) * 0.45)
    a = toile[..., 3:] + h[..., None] * (1 - toile[..., 3:])
    col = np.array(couleur, np.float32)
    toile[..., :3] = np.where(a > 1e-4, (toile[..., :3] * toile[..., 3:] + col * h[..., None] * (1 - toile[..., 3:])) / np.maximum(a, 1e-4), 0)
    toile[..., 3:] = a


def _ombre(toile, xh):
    A = toile[..., 3]
    dur = _flou(_decale(A, 0.09 * xh, 0.065 * xh), max(1, int(0.015 * xh))) * 0.85
    doux = _flou(_decale(A, 0.12 * xh, 0.10 * xh), max(2, int(0.12 * xh))) * 0.22
    ombre = np.maximum(dur, doux)[..., None]
    a = toile[..., 3:] + ombre * (1 - toile[..., 3:])
    toile[..., :3] = np.where(a > 1e-4, toile[..., :3] * toile[..., 3:] / np.maximum(a, 1e-4), 0)
    toile[..., 3:] = a


def _composer_lignes(texte, element, cache_dir, largeur, hauteur):
    """(24/11) deux lignes. Esprit guerrier (LU k000010 « Pégase / L'étalon ailé ») : deux lignes de même taille, centrées.
    Totem (LU a000020…) : « Totem » du jeu (image découpée, ~0,45 de la hauteur du nom) au-dessus du nom en grand."""
    manquantes = []
    toile = np.zeros((hauteur, largeur, 4), np.float32)
    if element == 'totem':
        nom = texte.strip()
        if nom.lower().startswith('totem '):
            nom = nom[6:].strip()
        nom = nom.replace('/', ' ').strip() or ' '
        nom = nom[:1].upper() + nom[1:]           # comme le jeu : « Loup », « Loup argenté »
        lettres = _lettres_de(nom, element, cache_dir, manquantes)
        if not any(lettres):
            raise ValueError('aucune lettre du jeu pour « %s »' % texte)
        th = (_alphabet(cache_dir) or {}).get('_totem_haut')
        haut_im = _lire(cache_dir, th['f']) if th else None
        larg_t, hmin, bmax = _mesures(lettres)
        if haut_im is not None and 'haut' in th:
            # (24/11) mesuré sur a000020 : « Totem » au-dessus du nom, à sa taille et sa place (nom : x-height 125 dans le jeu)
            larg_t, hmin, bmax = _mesures(lettres, chev=CHEV_REMPL_TOTEM, paires=True)
            hmin_t = min(hmin, th['haut'])
            xh = min(125.0, (largeur - 60) / larg_t, (hauteur - 24) / (bmax - hmin_t))
            base = (hauteur - (bmax - hmin_t) * xh) / 2 - hmin_t * xh
            x_nom = (largeur - larg_t * xh) / 2
            _poser(toile, lettres, x_nom, base, xh, chev=CHEV_REMPL_TOTEM, paires=True)
            _contour_totem(toile, xh)                 # (24/11, comme l'armure) UN contour bleu foncé autour de tout le nom
            g = _redim(haut_im, max(1, int(round(th['larg'] * xh))), max(1, int(round(th['h'] * xh))))
            y0 = int(round(base + th['haut'] * xh)); x0 = int(round(largeur / 2 + th['dx'] * xh - g.shape[1] / 2))
            ya, xa = max(0, y0), max(0, x0)
            d = toile[ya:y0 + g.shape[0], xa:x0 + g.shape[1]]
            g = g[ya - y0:ya - y0 + d.shape[0], xa - x0:xa - x0 + d.shape[1]]
            a = g[..., 3:] + d[..., 3:] * (1 - g[..., 3:])
            d[..., :3] = np.where(a > 1e-4, (g[..., :3] * g[..., 3:] + d[..., :3] * d[..., 3:] * (1 - g[..., 3:])) / np.maximum(a, 1e-4), 0)
            d[..., 3:] = a
            _finir_totem(toile, xh)
            return (np.clip(toile, 0, 1) * 255 + 0.5).astype(np.uint8), manquantes
        h_haut = 0.36 * hauteur if haut_im is not None else 0
        xh = min(150.0, (largeur - 60) / larg_t, (hauteur - 24 - h_haut) / (bmax - hmin))
        y_nom = h_haut + (hauteur - h_haut - (bmax - hmin) * xh) / 2 - 6
        _poser(toile, lettres, (largeur - larg_t * xh) / 2, y_nom - hmin * xh, xh, sans_halo=True)
        if haut_im is not None:                   # le « Totem » du jeu tel quel (ses couleurs, sans contour), centré au-dessus
            k = min(1.0, (h_haut - 6) / haut_im.shape[0])
            g = _redim(haut_im, max(1, int(haut_im.shape[1] * k)), max(1, int(haut_im.shape[0] * k)))
            y0 = max(0, int(y_nom - g.shape[0] - 0.04 * xh)); x0 = int((largeur - g.shape[1]) / 2)
            d = toile[y0:y0 + g.shape[0], x0:x0 + g.shape[1]]
            g = g[:d.shape[0], :d.shape[1]]
            a = g[..., 3:] + d[..., 3:] * (1 - g[..., 3:])
            d[..., :3] = np.where(a > 1e-4, (g[..., :3] * g[..., 3:] + d[..., :3] * d[..., 3:] * (1 - g[..., 3:])) / np.maximum(a, 1e-4), 0)
            d[..., 3:] = a
        _finir(toile, xh, 'totem')                # halo blanc autour des deux lignes, comme le jeu
        return (np.clip(toile, 0, 1) * 255 + 0.5).astype(np.uint8), manquantes
    lignes = [l.strip() for l in texte.split('/') if l.strip()][:2] or [' ']
    L_ = [_lettres_de(l, element, cache_dir, manquantes) for l in lignes]
    L_ = [l for l in L_ if any(l)]
    if not L_:
        raise ValueError('aucune lettre du jeu pour « %s »' % texte)
    M = [_mesures(l) for l in L_]
    ecart = -0.12
    tot_h = sum(b - h for _, h, b in M) + ecart * (len(M) - 1)
    xh = min(92.0 if len(M) > 1 else 115.0, (largeur - 60) / max(m[0] for m in M), (hauteur - 24) / tot_h)   # (24/11) mesuré : 92 (médiane, 55 bannières)
    y = (hauteur - tot_h * xh) / 2
    for l, (larg_t, hmin, bmax) in zip(L_, M):
        _poser(toile, l, (largeur - larg_t * xh) / 2, y - hmin * xh, xh)
        y += (bmax - hmin + ecart) * xh
    _ombre(toile, xh)
    return (np.clip(toile, 0, 1) * 255 + 0.5).astype(np.uint8), manquantes


def _composer_ligne(texte, element, cache_dir, largeur=1728, hauteur=352):
    lettres, manquantes = [], []
    for c in texte:
        if c.isspace():
            lettres.append(None); continue
        L = _lettre(cache_dir, element, c) or _lettre(cache_dir, element, c.lower()) or _lettre(cache_dir, element, c.upper())
        if L is None and c in '()[]':
            L = _parenthese(cache_dir, element, c)
        if L is None:                                   # (24/11) lettre accentuée qu'aucune bannière n'a (ì, ò…) : la lettre sans accent
            import unicodedata
            b_ = unicodedata.normalize('NFD', c)[0]
            if b_ != c and b_.strip():
                L = _lettre(cache_dir, element, b_) or _lettre(cache_dir, element, b_.lower())
        if L is None:
            manquantes.append(c); continue
        lettres.append(L)
    if not any(lettres):
        raise ValueError('aucune lettre du jeu pour « %s »' % texte)
    chev = 0.12                                  # recouvrement des contours (les lettres du jeu se touchent ; réglé à l'œil sur les bannières du jeu)
    if element == 'armure':                       # (24/11) lettres AVEC leur contour d'origine : leurs contours se chevauchent
        chev = _CHEV_ARMURE
    espace = 0.45
    larg_t = sum(espace if L is None else L[1]['larg'] - chev for L in lettres) + chev
    haut_min = min(L[1]['haut'] for L in lettres if L)
    bas_max = max(L[1]['haut'] + L[1]['h'] for L in lettres if L)
    xh = min(150.0, (largeur - 60) / larg_t, (hauteur - 24) / (bas_max - haut_min))
    toile = np.zeros((hauteur, largeur, 4), np.float32)
    x = (largeur - larg_t * xh) / 2
    base = (hauteur - (bas_max - haut_min) * xh) / 2 - haut_min * xh
    for L in lettres:
        if L is None:
            x += espace * xh; continue
        im, m = L
        w, h = max(1, int(round(m['larg'] * xh))), max(1, int(round(m['h'] * xh)))
        g = _redim(im, w, h)
        if element in HALOS and element != 'armure':           # (armure : lettres refaites, déjà propres)
            g = _sans_halo_ni_ombre(g, xh=xh)
        x0, y0 = int(round(x)), int(round(base + m['haut'] * xh))
        xa, ya, xb, yb = max(0, x0), max(0, y0), min(largeur, x0 + w), min(hauteur, y0 + h)
        if xb > xa and yb > ya:
            s = g[ya - y0:yb - y0, xa - x0:xb - x0]
            d = toile[ya:yb, xa:xb]
            a = s[..., 3:] + d[..., 3:] * (1 - s[..., 3:])
            d[..., :3] = np.where(a > 1e-4, (s[..., :3] * s[..., 3:] + d[..., :3] * d[..., 3:] * (1 - s[..., 3:])) / np.maximum(a, 1e-4), 0)
            d[..., 3:] = a
        x += (m['larg'] - chev) * xh
    if element == 'armure':
        _contour_armure_exact(toile, xh)
    if element in HALOS:                         # (24/11) armure : halo crème au lieu de l'ombre
        _finir(toile, xh, element)
        return (np.clip(toile, 0, 1) * 255 + 0.5).astype(np.uint8), manquantes
    # (23/11) UNE ombre sous tout le texte, comme les bannières du jeu (LU sur whs00010, minuscules de 140 px : bloc noir
    # décalé d'environ 12 px à droite et 9 px en bas, alpha ~0,85, bord doux ; puis une ombre très douce plus large)
    A = toile[..., 3]
    dur = _flou(_decale(A, 0.09 * xh, 0.065 * xh), max(1, int(0.015 * xh))) * 0.85
    doux = _flou(_decale(A, 0.12 * xh, 0.10 * xh), max(2, int(0.12 * xh))) * 0.22
    ombre = np.maximum(dur, doux)[..., None]
    a = toile[..., 3:] + ombre * (1 - toile[..., 3:])
    toile[..., :3] = np.where(a > 1e-4, toile[..., :3] * toile[..., 3:] / np.maximum(a, 1e-4), 0)
    toile[..., 3:] = a
    return (np.clip(toile, 0, 1) * 255 + 0.5).astype(np.uint8), manquantes


def _decale(A, dx, dy):
    dx, dy = int(round(dx)), int(round(dy))
    out = np.zeros_like(A)
    out[max(0, dy):, max(0, dx):] = A[:A.shape[0] - max(0, dy), :A.shape[1] - max(0, dx)]
    return out


def _flou(A, r):
    """flou en boîte (deux passes : presque gaussien), rayon r pixels"""
    for _ in range(2):
        for ax in (0, 1):
            c = np.cumsum(np.pad(A, [(r + 1, r)] * 1 + [(0, 0)] if ax == 0 else [(0, 0), (r + 1, r)]), axis=ax)
            A = ((c[2 * r + 1:] - c[:-2 * r - 1]) if ax == 0 else (c[:, 2 * r + 1:] - c[:, :-2 * r - 1])) / (2 * r + 1)
    return A


def _parenthese(cache_dir, el, c):
    """(23/11) les bannières du jeu n'ont AUCUNE parenthèse : fabriquée avec le « l » du jeu (même dessin, même couleur),
    courbé (le milieu poussé vers l'extérieur) ; [ ] : le « l » droit"""
    L = _lettre(cache_dir, el, 'l') or _lettre(cache_dir, el, 'I')
    if L is None:
        return None
    im, m = L
    h, w = im.shape[:2]
    if c in '[]':
        return im, m
    creux = 0.35 * w                             # profondeur de la courbe (pixels)
    sens = -1 if c == '(' else 1
    out = np.zeros((h, int(w + creux) + 2, 4), np.float32)
    for y in range(h):
        t = (y - h / 2) / (h / 2)
        dx = (1 - t * t) * creux                   # 0 aux bouts, creux au milieu
        x0 = int(round(dx if sens > 0 else creux - dx))
        out[y, x0:x0 + w] = im[y]
    m2 = dict(m, larg=m['larg'] * out.shape[1] / w)
    return out, m2


def ecrire(texte, element, cache_dir, png):
    from .g4 import images as _img
    im, manquantes = composer(texte, element, cache_dir)
    _img.ecrire_png(png, im.shape[1], im.shape[0], [im[y].tobytes() for y in range(im.shape[0])])
    return manquantes


# ------------------------------------------------------------------ (24/11, muku : « proposer le style d'écriture des Keshin, totem
# et armure dans les polices ») STYLES : lettres des bannières d'ESPRITS GUERRIERS (k…, ligne du haut = leur nom court, par
# élément), du GRAND NOM des bannières de TOTEMS (a… « Totem loup » -> « Loup » ; lettres claires dans un contour bleu foncé :
# découpées par l'intérieur clair, 53 bannières sur 56) et le « Totem » du haut (image du jeu, a000020). ARMED : la bannière du jeu
# (aura_armed01) n'a que A R M E D -> lettres Néant teintées comme elle.
VERSION_STYLES = 41


def _teinte_armed(cache_dir):
    if 'armed' not in _TEINTES:
        f = os.path.join(cache_dir, 'lettres_jeu', 'armed01.png')
        _TEINTES['armed'] = _teinte(_lire(cache_dir, 'armed01.png')) if os.path.exists(f) else None
    return _TEINTES['armed']


def construire_styles(cfg, cache_dir, journal=print):
    from . import ui_jeu
    from .g4 import images as _img
    d = os.path.join(cache_dir, 'lettres_jeu')
    os.makedirs(d, exist_ok=True)
    noms = _noms_fr(cfg['data_dir'])
    alpha = {}

    def garder(cle, r, code):
        for k_, (c, im, x0, y0, base, xh) in enumerate(r):
            L = alpha.setdefault(cle, {}).setdefault(c, [])
            # (24/11) + place dans la bannière (x en xh) et rang dans le mot : deux lettres qui se suivent dans la même bannière
            # du jeu sont reposées comme le jeu (la lettre coupée par sa voisine reste cachée dessous)
            L.append({'im': im, 'haut': (y0 - base) / xh, 'larg': im.shape[1] / xh, 'h': im.shape[0] / xh, 'xh': xh, 'code': code,
                      'x': float(x0) / xh, 'rang': k_})
    totem_haut = None
    for code, (nom, el, p, haut) in sorted(noms.items()):
        if not haut:
            continue
        try:
            _, _, g = ui_jeu.lire_planche(p)
            _, _, a = ui_jeu._rgba(g.blocs[0])
        except Exception as ex:
            journal('%s : %s' % (code, ex)); continue
        if code.startswith('k'):
            r = decouper(a, nom, True)
            if r:
                garder('esprit:' + el, r, code)
        elif code.startswith('a'):
            mots = nom.split(' ', 1)
            if len(mots) < 2:
                continue
            r = decouper(a, mots[1][:1].upper() + mots[1][1:], False, True, True)
            if r:
                r_orig = r
                # (24/11, muku : « regarde les totems ») lettre = remplissage + contour bleu SEULS, pris dans la bannière entière
                # (aucun morceau de la voisine : marques grises aux jointures) ; lueur blanche et ombre refaites autour du mot
                r = [(c, im, x0, y0, b_, XH_TOTEM) for c, im, x0, y0, b_, xh in _totem_remplissage(a, r)]
                garder('totem', r, code)
                r = r_orig
                if totem_haut is None and code == 'a000020':
                    # (24/11) le « Totem » du haut : les pixels les plus proches de SA ligne (croissance depuis les deux lignes ;
                    # avant : coupe horizontale au-dessus du nom -> bas des lettres coupé), sans son halo (refait autour de tout)
                    lh = _ligne_haut(a)
                    if lh is not None:
                        im, y0h, x0h = lh
                        _img.ecrire_png(os.path.join(d, 'totem_haut.png'), im.shape[1], im.shape[0], [im[y].tobytes() for y in range(im.shape[0])])
                        base_n, xh_n = r[0][4], r[0][5]
                        g_n = min(x for _, _, x, _, _, _ in r); d_n = max(x + im_.shape[1] for _, im_, x, _, _, _ in r)
                        # place mesurée sur a000020, en hauteurs de minuscule du nom : haut, taille, décalage du centre
                        totem_haut = {'f': 'totem_haut.png', 'haut': (y0h - base_n) / xh_n, 'h': im.shape[0] / xh_n, 'larg': im.shape[1] / xh_n,
                                      'dx': ((x0h + im.shape[1] / 2) - (g_n + d_n) / 2) / xh_n}
    # ARMED du jeu : sa teinte (lettres Néant teintées)
    try:
        p = os.path.join(cfg['data_dir'], 'dx11', 'menu', '220_img', 'telop_waza', 'fr', 'aura_armed01.g4tx')
        _, _, g = ui_jeu.lire_planche(p); _, _, a = ui_jeu._rgba(g.blocs[0])
        _img.ecrire_png(os.path.join(d, 'armed01.png'), a.shape[1], a.shape[0], [a[y].tobytes() for y in range(a.shape[0])])
        for lg, txt in TEXTES_ARMURE.items():
            p_ = os.path.join(cfg['data_dir'], 'dx11', 'menu', '220_img', 'telop_waza', lg, 'aura_armed01.g4tx')
            if not os.path.exists(p_):
                continue
            _, _, g_ = ui_jeu.lire_planche(p_); _, _, a_ = ui_jeu._rgba(g_.blocs[0])
            # (24/11) la bannière du jeu telle quelle : utilisée quand le texte est exactement le sien (rien de refait)
            _img.ecrire_png(os.path.join(d, 'armure_%s.png' % lg), a_.shape[1], a_.shape[0], [a_[y].tobytes() for y in range(a_.shape[0])])
            ok_ = False
            for sj in (True, False):                   # les deux découpes (avec / sans le contour jaune) : chacune réussit sur d'autres
                r = decouper(a_, txt, fusion=True, sans_jaune=sj)
                if r:
                    # (24/11, muku : « fais-le toi-même si les scripts ne marchent pas ») chaque lettre REFAITE : son remplissage seul
                    # (jamais touché par les voisines) + le contour jaune pâle redessiné à l'épaisseur MESURÉE (13 px, 94-99 %)
                    # (24/11, muku : « toujours pas bon ») chaque lettre = son remplissage + SON contour D'ORIGINE (net), pris dans la
                    # bannière ENTIÈRE (pas coupé par la voisine) : tout ce qui est à moins de 15 px de son remplissage, sauf le
                    # remplissage des autres lettres et l'ombre sombre ; la lueur et l'ombre sont refaites d'un bloc
                    r = _armure_remplissage(a_, r)                 # (24/11) remplissage seul, propre ; contour dessiné à la composition
                    # (24/11, muku : « pourquoi le e est aussi gros ») les 6 bannières sont à la MÊME échelle (A = 206 px, r = 126…
                    # partout) mais la hauteur des minuscules mesurée variait (128 à 156) selon le mot : une seule mesure pour toutes
                    r = [(c, im, x0, y0, b_, XH_ARMURE) for c, im, x0, y0, b_, xh in r]
                    garder('armure', r, 'aura_armed01/' + lg); ok_ = True
            if not ok_:
                journal('armure %s : lettres non découpées' % lg)
    except Exception as ex:
        journal('ARMED : %s' % ex)
    # (24/11) couleur des bannières d'esprits par élément : remplissage moyen (pixels colorés opaques) des bannières k… / celui des
    # lettres de l'élément -> gain par canal
    gains = {}
    try:
        A0 = json.load(open(os.path.join(d, 'alphabet.json'), encoding='utf-8'))['alphabet']
        def moy(im):
            ai = im.astype(np.float32) / (255 if im.dtype == np.uint8 else 1)
            m = (ai[..., 3] > 0.8) & (ai[..., :3].max(-1) - ai[..., :3].min(-1) > 0.25) & (ai[..., :3].min(-1) < 0.7)
            return ai[..., :3][m].reshape(-1, 3) if m.any() else np.zeros((0, 3), np.float32)
        par_el = {}
        for code, (nom, el, p, haut) in noms.items():
            if code.startswith('k') and el in ELEMENTS.values():
                _, _, g = ui_jeu.lire_planche(p); _, _, a = ui_jeu._rgba(g.blocs[0])
                par_el.setdefault(el, []).append(moy(a))
        for el, L_ in par_el.items():
            k_ = np.concatenate(L_).mean(0) if L_ else None
            nos = [moy(_lire(cache_dir, x[0]['f'])) for c, x in (A0.get(el) or {}).items() if x]
            n_ = np.concatenate(nos).mean(0) if nos else None
            if k_ is not None and n_ is not None and len(k_) and len(n_):
                gains[el] = [float(v) for v in np.clip(k_ / np.maximum(n_, 1e-3), 0.6, 1.6)]
    except Exception as ex:
        journal('couleurs des esprits : %s' % ex)
    # (24/11) essai du dégradé du « o » sur toutes les lettres : rayures horizontales, reflet intérieur perdu -> pas utilisé
    if alpha.get('totem') and DEGRADE_DU_O:
        try:
            _degrade_du_o(alpha['totem'])
        except Exception as ex:
            journal('dégradé du o : %s' % ex)
    index = {}
    for cle, lettres in alpha.items():
        dos = cle.replace(':', '_')
        os.makedirs(os.path.join(d, dos), exist_ok=True)
        for c, L in lettres.items():
            L.sort(key=lambda x: -x['xh'])          # la plus grande (la plus nette) d'abord
            for i, x in enumerate(L[:8] if cle == 'totem' else L[:3]):
                f = '%s/%d_%d.png' % (dos, ord(c), i)
                im = x['im']
                _img.ecrire_png(os.path.join(d, f), im.shape[1], im.shape[0], [im[y].tobytes() for y in range(im.shape[0])])
                index.setdefault(cle, {}).setdefault(c, []).append({'f': f, 'haut': x['haut'], 'larg': x['larg'], 'h': x['h'], 'xh': x['xh'], 'code': x['code'],
                                                                    'x': x.get('x'), 'rang': x.get('rang')})
    json.dump({'version': VERSION_STYLES, 'alphabet': index, 'totem_haut': totem_haut, 'gains_esprit': gains}, open(os.path.join(d, 'styles.json'), 'w', encoding='utf-8'), ensure_ascii=False)
    _ALPHA.clear(); _TEINTES.pop('armed', None)
    return {k: len(v) for k, v in index.items()}



def _degrade_armure(cache_dir):
    """(24/11) couleurs du remplissage des lettres de l'armure : moyenne en haut (rouge-rose) et en bas (violet), mesurées sur
    ses lettres découpées (pixels colorés du tiers haut / bas de chaque lettre)"""
    if 'degrade_armure' not in _TEINTES:
        A = (_alphabet(cache_dir) or {}).get('armure') or {}
        hauts, bas = [], []
        for c, L in A.items():
            if not L or c in '!¡':
                continue
            im = _lire(cache_dir, L[0]['f'])
            rgb, al = im[..., :3], im[..., 3]
            m = (al > 0.8) & (rgb.max(-1) - rgb.min(-1) > 0.3) & (rgb[..., 1] < 0.55)
            h = im.shape[0]
            for zone, liste in ((m[:h // 3], hauts), (m[2 * h // 3:], bas)):
                if zone.any():
                    liste.append(rgb[:h // 3][zone].mean(0) if liste is hauts else rgb[2 * h // 3:][zone].mean(0))
        _TEINTES['degrade_armure'] = (np.mean(hauts, 0), np.mean(bas, 0)) if hauts and bas else None
    return _TEINTES['degrade_armure']


def _habiller_armure(cache_dir, im, xh_lettre=None):
    """une lettre d'un autre élément habillée comme celles de l'armure : remplissage au dégradé de l'armure (haut -> bas, ombré
    comme l'original), contour blanc -> jaune pâle"""
    d = _degrade_armure(cache_dir)
    im = im.copy()
    # (24/11) le contour d'origine (blanc) n'est pas gardé : seul le remplissage, peint au dégradé, puis contour jaune redessiné
    rgb0 = im[..., :3]
    rempl0 = (im[..., 3] > 0.6) & (rgb0.max(-1) - rgb0.min(-1) > 0.2) & (rgb0.min(-1) < 0.75)
    im[..., 3] = np.where(rempl0, im[..., 3], 0)
    rgb, al = im[..., :3], im[..., 3]
    lum = rgb.mean(-1)
    color = (rgb.max(-1) - rgb.min(-1) > 0.2) & (al > 0.05)
    if d is not None and color.any():
        h = im.shape[0]
        t = (np.arange(h, dtype=np.float32) / max(1, h - 1))[:, None, None]
        grad = d[0][None, None, :] * (1 - t) + d[1][None, None, :] * t
        k = (lum / max(1e-3, float(lum[color].mean())))[..., None]
        im[..., :3] = np.where(color[..., None], np.clip(grad * np.clip(k, 0.55, 1.35) * 0.85, 0, 1), rgb)   # (un peu plus sombre : reflets compris dans la moyenne)
    # épaisseur : 13 px pour la x-height des lettres de l'armure (médiane), ramenée à celle de cette lettre
    xs_ = [L[0]['xh'] for c, L in ((_alphabet(cache_dir) or {}).get('armure') or {}).items() if L]
    ep = 13 * (xh_lettre / float(np.median(xs_))) if xs_ and xh_lettre else 13
    return _armure_refaite(im, ep, deja_rempli=True, contour=False)



def _ligne_haut(a):
    """(24/11) pixels de la ligne du HAUT d'une bannière à deux lignes (RGBA uint8) -> image RGBA recadrée"""
    ai = a.astype(np.int32)
    rempl = ((ai[..., 3] > 200) & (ai[..., :3].max(-1) > 120))[::2, ::2]
    comps = [c for c in _composantes(rempl) if len(c[0]) > 12]
    if len(comps) < 2:
        return None
    cy = sorted(c[0].mean() for c in comps)
    ecarts = [(cy[i + 1] - cy[i], i) for i in range(len(cy) - 1)]
    lim = cy[max(ecarts)[1]] + max(ecarts)[0] / 2
    haut = [c for c in comps if c[0].mean() < lim]
    bas = [c for c in comps if c[0].mean() >= lim]
    vis = (a[..., 3] > 8)[::2, ::2]
    lab = _croissance(vis, haut + bas)
    m = np.kron((lab >= 1) & (lab <= len(haut)), np.ones((2, 2), bool))[:a.shape[0], :a.shape[1]]
    ys, xs = np.nonzero(m)
    if not len(ys):
        return None
    im = a[ys.min():ys.max() + 1, xs.min():xs.max() + 1].copy()
    im[..., 3] = np.where(m[ys.min():ys.max() + 1, xs.min():xs.max() + 1], im[..., 3], 0)
    im[..., 3] = (np.clip((im[..., 3].astype(np.float32) / 255 - 0.45) / 0.35, 0, 1) * 255).astype(np.uint8)   # sans halo
    return im, int(ys.min()), int(xs.min())



def _dilater(m, n):
    """dilatation de n pixels (alternance 4 / 8 voisins : forme presque ronde) -> distance (0 = dedans, k = atteint au pas k)"""
    dist = np.where(m, 0, 10 ** 6).astype(np.int32)
    cur = m.copy()
    for k in range(1, n + 2):
        d = cur.copy()
        d[1:] |= cur[:-1]; d[:-1] |= cur[1:]; d[:, 1:] |= cur[:, :-1]; d[:, :-1] |= cur[:, 1:]
        if k % 2 == 0:
            d[1:, 1:] |= cur[:-1, :-1]; d[:-1, :-1] |= cur[1:, 1:]; d[1:, :-1] |= cur[:-1, 1:]; d[:-1, 1:] |= cur[1:, :-1]
        dist[d & ~cur] = k
        cur = d
    return dist


CONTOUR_ARMURE = np.array([255, 249, 172], np.float32) / 255      # (24/11) cœur du contour du jeu (médiane des pixels pleins : 255,249,169)


def _armure_refaite(im, ep, deja_rempli=False, contour=True):
    """(24/11) lettre de l'armure REFAITE : remplissage rouge-violet seul (+ ses bords adoucis), contour jaune pâle redessiné
    autour à l'épaisseur ep (pixels de cette image), bord du contour adouci ; image agrandie de 16 px de chaque côté"""
    ep = max(2, int(round(ep)))
    pad = ep + 3 if contour else 3
    im = np.pad(im, ((pad, pad), (pad, pad), (0, 0)))
    rgb, al = im[..., :3], im[..., 3]
    if deja_rempli:
        F = al > 0.5
    else:
        # remplissage = opaque, ni le jaune pâle du contour, ni l'ombre grise / le halo ; puis trous bouchés (reflets, zones sombres)
        jaune = (rgb[..., 0] > 0.72) & (rgb[..., 1] > 0.62) & (rgb[..., 2] < 0.9) & (rgb[..., 1] > rgb[..., 2] - 0.05)
        gris = (rgb.max(-1) - rgb.min(-1)) < 0.12
        brun = (rgb[..., 1] >= rgb[..., 2] - 0.02) & (rgb[..., 1] > 0.15)   # ombre brune : plus de vert que de bleu (le rose / violet, jamais)
        F = (al > 0.6) & ~jaune & ~gris & ~brun
        F = _dilater(F, 3) <= 3                                    # fermeture : dilater 3 px…
        F = _dilater(~F, 3) > 3                                    # … puis éroder 3 px
        F &= al > 0.3
        F = _dilater(~F, 1) > 1                                    # bord du remplissage rogné de 1 px (ombre d'origine au bord ;
                                                                   # le contour redessiné le recouvre)
    if not F.any():
        return im
    dist = _dilater(F, ep) if contour else np.where(F, 0, 10 ** 6)
    a_c = np.clip((ep + 0.8 - dist) / 1.6, 0, 1) if contour else np.zeros(F.shape, np.float32)   # contour : plein jusqu'à ep
    out = np.zeros_like(im)
    out[..., :3] = CONTOUR_ARMURE
    out[..., 3] = a_c
    a_f = np.clip(_flou(F.astype(np.float32), 1) * 1.6, 0, 1)    # remplissage : ses couleurs, bord adouci d'un pixel
    a_f = np.where(F, 1.0, a_f)
    col = rgb.copy()
    # couleurs du bord : celles du remplissage voisin (pas le mélange avec l'ancien contour)
    voisin = np.where(F[..., None], rgb, 0)
    poids = _flou(F.astype(np.float32), 2)[..., None]
    moy = np.stack([_flou(voisin[..., i], 2) for i in range(3)], -1) / np.maximum(poids, 1e-4)
    col = np.where(F[..., None], rgb, np.clip(moy, 0, 1))
    a = a_f[..., None] + out[..., 3:] * (1 - a_f[..., None])
    out[..., :3] = np.where(a > 1e-4, (col * a_f[..., None] + out[..., :3] * out[..., 3:] * (1 - a_f[..., None])) / np.maximum(a, 1e-4), 0)
    out[..., 3:] = a
    return out



def _contour_armure(toile, xh, cache_dir):
    xs_ = [L[0]['xh'] for c, L in ((_alphabet(cache_dir) or {}).get('armure') or {}).items() if L]
    ep = max(2, int(round(9.5 * xh / float(np.median(xs_))))) if xs_ else max(2, int(round(0.085 * xh)))   # (24/11) profil mesuré : plein jusqu'à ~8 px du remplissage
    F = toile[..., 3] > 0.5
    # (24/11, muku : « des imperfections ») bord du contour LISSE : distance au remplissage (pas à pas) puis bord adouci par un
    # flou de la zone (avant : escalier de pixels visible)
    zone = (_dilater(F, ep) <= ep).astype(np.float32)
    a_c = np.clip((_flou(zone, 2) - 0.25) / 0.5, 0, 1)
    couche = np.concatenate([np.broadcast_to(CONTOUR_ARMURE, F.shape + (3,)), a_c[..., None]], -1).astype(np.float32)
    toile[:] = _sur(toile, couche)



def _recadrer(im, seuil=0.02):
    """image RGBA recadrée sur sa partie visible -> (image, décalage haut, décalage gauche)"""
    ys, xs = np.nonzero(im[..., 3] > seuil)
    if not len(ys):
        return im, 0, 0
    return im[ys.min():ys.max() + 1, xs.min():xs.max() + 1], int(ys.min()), int(xs.min())



XH_ARMURE = 140.0                 # hauteur des minuscules des bannières d'armure (toutes à la même échelle)
R_ARMURE = 11                     # (24/11) fenêtre du contour d'origine, ajustée sur le profil et la largeur du mot du jeu
_CHEV_ARMURE = -0.075             # écart entre lettres d'armure (largeur du mot = celle du jeu ; négatif = plus d'écart)


def _armure_d_origine(a, r, R=None):
    """(24/11) lettres de l'armure avec leur contour d'origine. a = bannière RGBA uint8 ; r = découpe (decouper) -> même liste,
    images refaites : pixels à moins de R px du remplissage de la lettre (bord adouci), hors remplissage des autres lettres et
    hors ombre sombre ; halo d'origine estompé au-delà du contour"""
    R = R or R_ARMURE
    af = a.astype(np.float32) / 255
    rgb, al = af[..., :3], af[..., 3]
    jaune = (rgb[..., 0] > 0.72) & (rgb[..., 1] > 0.62) & (rgb[..., 2] < 0.9) & (rgb[..., 1] > rgb[..., 2] - 0.05)
    gris = (rgb.max(-1) - rgb.min(-1)) < 0.12
    brun = (rgb[..., 1] >= rgb[..., 2] - 0.02) & (rgb[..., 1] > 0.15)
    Fg = (al > 0.6) & ~jaune & ~gris & ~brun                     # remplissage de toutes les lettres
    sombre = (rgb.max(-1) < 0.45) & ~Fg                          # ombre (sombre, hors remplissage)
    out = []
    for c, im, x0, y0, base, xh in r:
        h, w = im.shape[:2]
        Fl = np.zeros(Fg.shape, bool)
        sub = Fg[y0:y0 + h, x0:x0 + w] & (im[..., 3] > 150)      # son remplissage : dans sa découpe
        Fl[y0:y0 + h, x0:x0 + w] = sub
        Fl = _dilater(Fl, 2) <= 2; Fl = _dilater(~Fl, 2) > 2      # trous bouchés
        Fl &= Fg | (_dilater(Fg, 1) <= 1)
        ys, xs = np.nonzero(Fl)
        if not len(ys):
            continue
        Y0, Y1, X0, X1 = max(0, ys.min() - R - 4), min(a.shape[0], ys.max() + R + 5), max(0, xs.min() - R - 4), min(a.shape[1], xs.max() + R + 5)
        Fc = Fl[Y0:Y1, X0:X1]
        dist = _dilater(Fc, R + 3)
        poids = np.clip((R + 1.5 - dist) / 3.0, 0, 1)
        autres = Fg[Y0:Y1, X0:X1] & ~Fc
        garder = poids * (~autres) * (~sombre[Y0:Y1, X0:X1] | Fc)
        crop = af[Y0:Y1, X0:X1].copy()
        crop[..., 3] = crop[..., 3] * garder
        crop, dy, dx = _recadrer(crop)
        out.append((c, (crop * 255 + 0.5).astype(np.uint8), X0 + dx, Y0 + dy, base, xh))
    return out



# ------------------------------------------------------------------ (24/11, muku : « fais jusqu'à ce que ce soit parfait ») contour
# de l'armure DESSINÉ à la distance exacte du remplissage (bande régulière comme le jeu, bord lisse) ; épaisseur et couleur ajustées
EP_ARMURE = 9.0                                 # épaisseur (pixels pour une x-height de 150), AJUSTÉE sur le profil du jeu (24/11)
BORD_ARMURE = 1.0                                # fondu du bord extérieur (mesuré : plein jusqu'à ~8 px, fini à ~11)


def _distance(m, M=40):
    """distance euclidienne de chaque pixel au plus proche pixel vrai de m (limitée à M ; numpy seul)"""
    H, W = m.shape
    x = np.arange(W, dtype=np.float32)[None, :]
    inf = np.float32(1e6)
    g = np.full((H, W), inf, np.float32)
    idx = np.where(m, x, -inf)
    gauche = np.maximum.accumulate(idx, axis=1)
    idx2 = np.where(m, x, inf)
    droite = np.minimum.accumulate(idx2[:, ::-1], axis=1)[:, ::-1]
    g = np.minimum(x - gauche, droite - x)
    g2 = np.minimum(g, M + 1) ** 2
    D2 = g2.copy()
    for dy in range(1, M + 1):
        h = np.full_like(g2, (M + 1) ** 2)
        h[dy:] = g2[:-dy]; D2 = np.minimum(D2, h + dy * dy)
        h = np.full_like(g2, (M + 1) ** 2)
        h[:-dy] = g2[dy:]; D2 = np.minimum(D2, h + dy * dy)
    return np.sqrt(D2)


def _contour_armure_exact(toile, xh):
    ep = EP_ARMURE * xh / 150.0
    F = _flou(toile[..., 3], 1) > 0.5
    d = _distance(F, int(ep) + 4)
    s_ = max(1.0, BORD_ARMURE * xh / 150.0)      # bord extérieur fondu comme le jeu (mesuré : ~4 px)
    a_c = np.clip((ep - d) / s_ + 0.5, 0, 1).astype(np.float32)
    couche = np.concatenate([np.broadcast_to(CONTOUR_ARMURE, F.shape + (3,)), a_c[..., None]], -1).astype(np.float32)
    toile[:] = _sur(toile, couche)


def _armure_remplissage(a, r):
    """(24/11) lettres de l'armure : REMPLISSAGE seul, pris dans la bannière entière (pas de morceau de la voisine) ; bord : couleurs
    de l'intérieur (pas le mélange avec le contour jaune -> plus de liseré pâle), alpha lisse"""
    af = a.astype(np.float32) / 255
    rgb, al = af[..., :3], af[..., 3]
    Fg = _enclos_armure(af)
    out = []
    for c, im, x0, y0, base, xh in r:
        h, w = im.shape[:2]
        Fl = np.zeros(Fg.shape, bool)
        Fl[y0:y0 + h, x0:x0 + w] = Fg[y0:y0 + h, x0:x0 + w] & (im[..., 3] > 150)
        Fl = _dilater(Fl, 1) <= 1; Fl = _dilater(~Fl, 1) > 1          # petits trous bouchés
        # seulement le corps de la lettre (+ point d'un ! ou d'un i) : les poches enfermées entre deux contours voisins s'en vont
        ys_, xs_ = np.nonzero(Fl)
        if len(ys_):
            yb, xb = ys_.min(), xs_.min()
            sub = Fl[yb:ys_.max() + 1, xb:xs_.max() + 1]
            cs = _composantes(sub)
            if cs:
                gros = max(len(c_[0]) for c_ in cs)
                Fl[:] = False
                for cy_, cx_ in cs:
                    # (24/11, « t » avec un trait brun à gauche) un morceau à part n'est gardé que s'il est AU-DESSUS du corps
                    # (point d'un i, d'un !) ; un morceau sur le côté = bout d'une lettre voisine pris dans la découpe
                    corps_ = max(cs, key=lambda c_: len(c_[0]))
                    # « à côté » = à la même hauteur que le corps (les points de i, ü, !, ¡ sont au-dessus ou en dessous)
                    recouv = min(cy_.max(), corps_[0].max()) - max(cy_.min(), corps_[0].min())
                    a_cote = recouv > 0.3 * (cy_.max() - cy_.min() + 1) and len(cy_) < 0.5 * gros
                    if len(cy_) >= 0.04 * gros and not a_cote:
                        Fl[cy_ + yb, cx_ + xb] = True
        ys, xs = np.nonzero(Fl)
        if not len(ys):
            continue
        Y0, Y1, X0, X1 = max(0, ys.min() - 4), min(a.shape[0], ys.max() + 5), max(0, xs.min() - 4), min(a.shape[1], xs.max() + 5)
        Fc = Fl[Y0:Y1, X0:X1]
        coeur = _dilater(~Fc, 2) > 2                               # intérieur sûr (2 px du bord)
        col = rgb[Y0:Y1, X0:X1]
        if coeur.any():
            # couleurs du bord : moyenne de l'intérieur proche ; pointes fines (pas d'intérieur à 3 px) : rayon plus grand, sinon la
            # couleur d'origine (avant : noir -> point noir au bout d'un trait)
            moy = None
            for r_ in (3, 7, 14):
                poids = _flou(coeur.astype(np.float32), r_)[..., None]
                m_ = np.stack([_flou(np.where(coeur, col[..., i], 0), r_) for i in range(3)], -1) / np.maximum(poids, 1e-6)
                ok_ = poids > 1e-3
                moy = np.where(ok_, m_, moy if moy is not None else col)
            col = np.where(coeur[..., None], col, np.clip(moy, 0, 1))
        # (24/11, muku : « le nôtre est trop flou ») bord du remplissage net : l'alpha du jeu sur le bord, plus de flou
        alpha = np.where(Fc, 1.0, 0.0).astype(np.float32)
        # rien hors du remplissage (un pixel à demi transparent tombait sur le contour de la voisine : trous sombres) ; dernier pixel
        # du remplissage à 0,7 : le jaune dessous l'éclaircit, comme le bord du jeu (plus clair que l'intérieur, pas plus sombre)
        alpha = np.where(Fc & (_dilater(~Fc, 1) == 1), BORD_REMPL_ARMURE, alpha)
        crop = np.concatenate([col, alpha[..., None]], -1)
        crop, dy, dx = _recadrer(crop)
        out.append((c, (crop * 255 + 0.5).astype(np.uint8), X0 + dx, Y0 + dy, base, xh))
    return out



def _enclos_armure(af):
    """(24/11) REMPLISSAGE des lettres d'une bannière d'armure = ce qui est ENFERMÉ par le contour jaune (pas atteignable depuis le
    bord de l'image sans le traverser), sauf le contour lui-même et le blanc des creux (e, A) ; à la couleur, des reflets clairs
    passaient pour du contour (points blancs, encoches)"""
    rgb, al = af[..., :3], af[..., 3]
    jaune = (al > 0.5) & (rgb[..., 0] > 0.7) & (rgb[..., 1] > 0.55) & (rgb[..., 1] > rgb[..., 2] - 0.02)
    libre = ~jaune
    comps = _composantes(libre[::2, ::2])
    H2, W2 = libre[::2, ::2].shape
    enferme2 = np.zeros((H2, W2), bool)
    for ys, xs in comps:
        if ys.min() == 0 or xs.min() == 0 or ys.max() == H2 - 1 or xs.max() == W2 - 1:
            continue                                   # touche le bord : dehors
        enferme2[ys, xs] = True
    enferme = np.kron(enferme2, np.ones((2, 2), bool))[:af.shape[0], :af.shape[1]]
    enferme = (_dilater(enferme, 2) <= 2) & libre      # bord à pleine résolution (avant : blocs de 2 px, bord dentelé)
    sat = rgb.max(-1) - rgb.min(-1)
    blanc = (rgb.min(-1) > 0.62) & (sat < 0.3)         # creux des lettres (lueur blanche)
    return enferme & ~blanc & (al > 0.5)



# ------------------------------------------------------------------ (24/11, muku : police « Armure Style » = Noto Black Italic)
# TEXTURE du remplissage de l'armure : la bannière du jeu (fr) dont chaque pixel prend la couleur du remplissage le plus proche
# -> l'éditeur remplit les lettres de la police avec cette image (facettes et dégradé rose -> violet du jeu, à la même hauteur)
def texture_armure(cache_dir, data_dir):
    """(24/11) dégradé vertical = couleur moyenne du remplissage du jeu à chaque ligne (lissée), multiplié par le motif de facettes
    du jeu (le plus grand rectangle tout entier dans une lettre, divisé par sa moyenne de ligne, répété en miroir)"""
    f = os.path.join(cache_dir, 'lettres_jeu', 'texture_armure3.png')
    if os.path.exists(f):
        return f
    from . import ui_jeu
    from .g4 import images as _img
    _, _, g = ui_jeu.lire_planche(os.path.join(data_dir, 'dx11', 'menu', '220_img', 'telop_waza', 'fr', 'aura_armed01.g4tx'))
    _, _, a = ui_jeu._rgba(g.blocs[0])
    af = a.astype(np.float32) / 255
    F = _enclos_armure(af)
    F = _dilater(~F, 2) > 2
    H, W = F.shape
    rgb = af[..., :3]
    lignes = np.zeros((H, 3), np.float32); ok = F.sum(1) > 3
    for y in np.nonzero(ok)[0]:
        lignes[y] = rgb[y][F[y]].mean(0)
    ys = np.nonzero(ok)[0]
    for c in range(3):                               # lignes sans remplissage : prolongées ; puis lissage
        lignes[:, c] = np.interp(np.arange(H), ys, lignes[ys, c])
    k = np.ones(9) / 9
    lignes = np.stack([np.convolve(np.pad(lignes[:, c], 4, mode='edge'), k, 'valid') for c in range(3)], -1)
    # plus grand rectangle tout dans le remplissage (image intégrale)
    I = np.pad(F.astype(np.int32).cumsum(0).cumsum(1), ((1, 0), (1, 0)))
    best = None
    for h in range(120, 20, -4):
        for w in range(90, 14, -4):
            if best and h * w <= best[0]:
                continue
            S = I[h:, w:] - I[:-h, w:] - I[h:, :-w] + I[:-h, :-w]
            pos = np.argwhere(S == h * w)
            if len(pos):
                y0, x0 = pos[len(pos) // 2]; best = (h * w, y0, x0, h, w); break
    _, y0, x0, h, w = best
    tuile = rgb[y0:y0 + h, x0:x0 + w] / np.maximum(lignes[y0:y0 + h, None, :], 1e-3)
    ecart = float(np.std(tuile.mean(-1)))           # force des facettes MESURÉE dans le jeu
    # facettes : cellules irrégulières (Voronoï, ~45 px), chacune un peu plus claire ou sombre, sans répétition (une tuile de
    # 22 px répétée faisait des rayures)
    rng = np.random.default_rng(7)
    n = int(H * W / 45 ** 2 * 1.3)
    py, px = rng.uniform(0, H, n), rng.uniform(0, W, n)
    val = rng.normal(1.0, ecart, n).astype(np.float32)
    yy, xx = np.mgrid[0:H, 0:W]
    best_d = np.full((H, W), 1e9, np.float32); fac = np.ones((H, W), np.float32)
    for k in range(n):
        y_, x_ = int(py[k]), int(px[k]); r = 70
        sl = (slice(max(0, y_ - r), y_ + r), slice(max(0, x_ - r), x_ + r))
        d = (yy[sl] - py[k]) ** 2 + (xx[sl] - px[k]) ** 2
        m = d < best_d[sl]
        best_d[sl] = np.where(m, d, best_d[sl]); fac[sl] = np.where(m, val[k], fac[sl])
    fac = _flou(fac, 1)
    col = np.clip(lignes[:, None, :] * fac[..., None], 0, 1)
    im = np.concatenate([col, np.ones((H, W, 1), np.float32)], -1)
    im = (im * 255 + 0.5).astype(np.uint8)
    _img.ecrire_png(f, W, H, [im[y].tobytes() for y in range(H)])
    print('texture armure : rectangle', best, 'écart des facettes', round(ecart, 3))
    return f
    from . import ui_jeu
    from .g4 import images as _img
    _, _, g = ui_jeu.lire_planche(os.path.join(data_dir, 'dx11', 'menu', '220_img', 'telop_waza', 'fr', 'aura_armed01.g4tx'))
    _, _, a = ui_jeu._rgba(g.blocs[0])
    af = a.astype(np.float32) / 255
    F = _enclos_armure(af)
    F = _dilater(~F, 2) > 2                       # loin du bord (pas de mélange avec le contour)
    col = np.where(F[..., None], af[..., :3], 0)
    poids = F.astype(np.float32)
    # propagation : chaque pixel vide prend la moyenne de ses voisins remplis, jusqu'à tout couvrir
    for _ in range(400):
        if poids.min() > 0:
            break
        c2 = col.copy(); p2 = poids.copy()
        for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            c2 += np.roll(np.roll(col * poids[..., None], dy, 0), dx, 1)
            p2 += np.roll(np.roll(poids, dy, 0), dx, 1)
        vide = poids == 0
        nouv = p2 > 0
        col = np.where((vide & nouv)[..., None], c2 / np.maximum(p2, 1e-6)[..., None], col)
        poids = np.where(vide & nouv, 1.0, poids)
    im = np.concatenate([col, np.ones(col.shape[:2] + (1,), np.float32)], -1)
    im = (np.clip(im, 0, 1) * 255 + 0.5).astype(np.uint8)
    _img.ecrire_png(f, im.shape[1], im.shape[0], [im[y].tobytes() for y in range(im.shape[0])])
    return f



# ------------------------------------------------------------------ (24/11, muku : « regarde les totems, il y a un problème »)
# MESURÉ sur a000020 (« Totem / Loup ») : lettre = remplissage cyan + contour bleu foncé (~8 px) ; autour, une LUEUR BLANCHE
# collée au contour (alpha 0,89 à 1 px, 0,59 à 6, 0,25 à 10, 0 vers 21) ; en bas à droite une ombre grise sous la lueur.
DEGRADE_DU_O = False
FORCE_LUEUR_TOTEM = 0.45               # (24/11, muku : lueur « un peu trop forte »)
XH_TOTEM = 125.0                     # hauteur des minuscules du nom (toutes les bannières de totems, médiane de 53)
CHEV_TOTEM = 0.04                     # écart entre lettres (ajusté sur la largeur des noms du jeu)
# MESURÉ sur 5 bannières de totems (côté haut-gauche, hors ombre), depuis le même bord de lettre que _finir_totem
LUEUR_TOTEM = [(0, 0.83), (1, 0.831), (2, 0.816), (3, 0.821), (4, 0.72), (5, 0.657), (6, 0.54), (7, 0.426), (8, 0.361), (9, 0.289),
               (10, 0.223), (11, 0.168), (12, 0.129), (13, 0.105), (14, 0.084), (15, 0.068), (16, 0.056), (17, 0.042), (18, 0.032),
               (19, 0.023), (20, 0.017), (21, 0.012), (22, 0.008), (23, 0.005), (24, 0.0)]
OMBRE_TOTEM = (9.0, 9.0, 0.6, 70 / 255)   # décalage x, y (px pour x-height 125), force, gris (ajusté)


def _finir_totem(toile, xh):
    k = xh / XH_TOTEM
    F = _flou(toile[..., 3], 1) > 0.5            # même bord que la mesure
    d = _distance(F, int(24 * k * LARGEUR_LUEUR_TOTEM) + 2) / max(k, 1e-3) / LARGEUR_LUEUR_TOTEM
    xs, ys = zip(*LUEUR_TOTEM)
    g = (np.interp(d, xs, ys) * FORCE_LUEUR_TOTEM).astype(np.float32)
    lueur = np.concatenate([np.ones(F.shape + (3,), np.float32), g[..., None]], -1)
    ox, oy, force, gris = OMBRE_TOTEM
    Fo = np.zeros_like(F)
    dx, dy = int(round(ox * k)), int(round(oy * k))
    Fo[dy:, dx:] = F[:F.shape[0] - dy, :F.shape[1] - dx]
    do = _distance(Fo, int(24 * k) + 2) / max(k, 1e-3)
    go = (np.interp(do, xs, ys) * force).astype(np.float32)
    ombre = np.concatenate([np.full(F.shape + (3,), gris, np.float32), go[..., None]], -1)
    toile[:] = _sur(toile, _sur(ombre, lueur) if OMBRE_DESSUS_TOTEM else _sur(lueur, ombre))


def _totem_lettres(a, r, R=11):   # (24/11, muku : « des taches de lettres sur les ombres ») contour <= 9 px du remplissage (mesuré)
    """lettres d'une bannière de totem : remplissage + contour bleu (+ reflets blancs DANS le remplissage), chaque pixel à la
    lettre dont le remplissage est le plus proche ; ni lueur blanche, ni ombre grise"""
    af = a.astype(np.float32) / 255
    rgb, al = af[..., :3], af[..., 3]
    sat = rgb.max(-1) - rgb.min(-1)
    blanc = (rgb.min(-1) > 0.82) & (sat < 0.14)
    gris = (sat < 0.14) & ~blanc
    FI = (al > 0.7) & (rgb[..., 2] > rgb[..., 0] + 0.08) & (rgb.max(-1) > 0.66)        # remplissage cyan / bleu clair
    # (24/11, jointures) dans la bande du contour (<= 9 px d'un remplissage), un pixel assombri par l'ombre d'une voisine reste
    # du contour (avant : écarté -> trou entre deux lettres, l'ombre / la lueur se voyait)
    bande = _distance(FI, 10) <= 9
    strict = (al > 0.7) & ~blanc & ~gris
    ferme = _dilater(strict, 3) <= 3; ferme = _dilater(~ferme, 3) > 3          # creux étroits (<= ~6 px) dans le contour
    lettre = strict | (gris & bande & ferme & (al > 0.5))
    pres = _distance(FI, 4) <= 3                                                       # reflets blancs dans le remplissage
    lettre |= blanc & pres & (al > 0.7)
    dists = []
    for c, im, x0, y0, base, xh in r:
        h, w = im.shape[:2]
        S_ = np.zeros(FI.shape, bool)
        S_[y0:y0 + h, x0:x0 + w] = FI[y0:y0 + h, x0:x0 + w] & (im[..., 3] > 150)
        dists.append(_distance(S_, R + 2) if S_.any() else np.full(FI.shape, 1e6, np.float32))
    D = np.stack(dists)
    qui = np.argmin(D, 0); dmin = np.min(D, 0)
    out = []
    for i, (c, im, x0, y0, base, xh) in enumerate(r):
        m = lettre & (qui == i) & (dmin <= R)
        if not m.any():
            continue
        h, w = im.shape[:2]
        S_ = np.zeros(FI.shape, bool)
        S_[y0:y0 + h, x0:x0 + w] = FI[y0:y0 + h, x0:x0 + w] & (im[..., 3] > 150)
        ys, xs = np.nonzero(m)
        Y0, Y1, X0, X1 = max(0, ys.min() - 1), min(a.shape[0], ys.max() + 2), max(0, xs.min() - 1), min(a.shape[1], xs.max() + 2)
        mc, sc = m[Y0:Y1, X0:X1], S_[Y0:Y1, X0:X1]
        # (24/11, muku : « le L est coupé en deux ») seulement les morceaux RELIÉS à la lettre (un bout du « Totem » du dessus
        # flottait au-dessus du L)
        garde = np.zeros_like(mc)
        for cy_, cx_ in _composantes(mc):
            if sc[cy_, cx_].any():
                garde[cy_, cx_] = True
        mc = garde
        # trous fermés de la lettre (ombre grise d'une voisine sur elle, reflets écartés) : bouchés
        trou = np.zeros_like(mc)
        for cy_, cx_ in _composantes(~mc):
            if cy_.min() > 0 and cx_.min() > 0 and cy_.max() < mc.shape[0] - 1 and cx_.max() < mc.shape[1] - 1:
                trou[cy_, cx_] = True
        crop = af[Y0:Y1, X0:X1].copy()
        sat_c = crop[..., :3].max(-1) - crop[..., :3].min(-1)
        blanc_c = (crop[..., :3].min(-1) > 0.82) & (sat_c < 0.14)
        # (24/11, muku : « retire le bout de couleur moche ») à recolorer : les trous (sauf reflets blancs) et les pixels teintés
        # d'ombre (gris-bleu terne) -> couleur de la lettre autour ; le reste garde ses pixels du jeu
        terne = mc & (sat_c < 0.3) & (crop[..., :3].max(-1) < 0.75)
        refaire = (trou & ~(blanc_c & (crop[..., 3] > 0.7))) | terne
        mc = mc | trou
        vrai = mc & ~refaire
        # couleur du contour de CETTE lettre (bleu foncé) : pour tout ce qui est refait dans la bande du contour (avant : moyenne
        # avec le remplissage -> taches bleu pâle)
        cc_ = vrai & (crop[..., :3].max(-1) < 0.62) & (crop[..., 2] > crop[..., 0]) & (sat_c > 0.3)
        c_out = crop[..., :3][cc_].mean(0) if cc_.any() else np.array([0.04, 0.16, 0.55], np.float32)
        loin = _distance(sc, 6) > 2.5                  # à plus de 2,5 px du remplissage de la lettre : contour
        if refaire.any() and vrai.any():
            moy = None
            for r_ in (2, 4, 8, 16):
                w_ = _flou(vrai.astype(np.float32), r_)
                m_ = np.stack([_flou(np.where(vrai, crop[..., k], 0), r_) for k in range(3)], -1) / np.maximum(w_[..., None], 1e-6)
                moy = np.where((w_ > 1e-3)[..., None], m_, moy if moy is not None else crop[..., :3])
            crop[..., :3] = np.where(refaire[..., None], np.where(loin[..., None], c_out, moy), crop[..., :3])
            crop[..., 3] = np.where(refaire, 1.0, crop[..., 3])
        crop[..., 3] = np.where(mc, crop[..., 3], 0)
        crop, dy, dx = _recadrer(crop)
        out.append((c, (np.clip(crop, 0, 1) * 255 + 0.5).astype(np.uint8), int(X0 + dx), int(Y0 + dy), base, xh))
    return out



def _degrade_du_o(lettres, modele='o', code='a000020'):
    """(24/11, muku : « applique le dégradé du O, il est bien fait sur tout ») le remplissage de CHAQUE lettre de totem prend la
    couleur du « o » de « Totem loup » à la même hauteur (en hauteurs de minuscule depuis la ligne de base) ; le contour bleu et
    l'anti-crénelage gardent leur place : chaque pixel = mélange contour -> dégradé selon sa clarté"""
    L0 = [x for x in lettres.get(modele, []) if x['code'] == code] or lettres.get(modele, [])
    if not L0:
        return
    o = L0[0]
    im = o['im'].astype(np.float32) / 255
    rgb, al = im[..., :3], im[..., 3]
    lum = rgb.mean(-1)
    contour = (al > 0.7) & (rgb.max(-1) < 0.62) & (rgb[..., 2] > rgb[..., 0])
    rempl = (al > 0.7) & (lum > 0.62)
    c_contour = rgb[contour].mean(0) if contour.any() else np.array([0.04, 0.16, 0.55], np.float32)
    l_contour = float(lum[contour].mean()) if contour.any() else 0.25
    xh = o['xh']
    rel0 = o['haut']                              # haut de l'image du « o », en xh, depuis la base
    rangs, cols = [], []
    for y in range(im.shape[0]):
        m = rempl[y]
        if m.sum() >= 2:
            rangs.append(rel0 + y / xh); cols.append(rgb[y][m].mean(0))
    rangs, cols = np.array(rangs), np.array(cols)
    l_rempl = float(np.median(lum[rempl]))
    for c, L in lettres.items():
        for x in L:
            im2 = x['im'].astype(np.float32) / 255
            rgb2, al2 = im2[..., :3], im2[..., 3]
            lum2 = rgb2.mean(-1)
            rel = x['haut'] + np.arange(im2.shape[0], dtype=np.float32) / x['xh']
            grad = np.stack([np.interp(rel, rangs, cols[:, k]) for k in range(3)], -1)[:, None, :]
            t = np.clip((lum2 - l_contour) / max(1e-3, l_rempl - l_contour), 0, 1)[..., None]
            nouveau = c_contour * (1 - t) + grad * t
            m = (al2 > 0.05)[..., None]
            im2[..., :3] = np.where(m, nouveau, rgb2)
            x['im'] = (np.clip(im2, 0, 1) * 255 + 0.5).astype(np.uint8)



# ------------------------------------------------------------------ (24/11, muku : « tu ne peux pas faire comme pour l'armure ? »)
# Totems comme l'armure : chaque lettre = son REMPLISSAGE seul (cyan, reflets blancs et liseré clair compris : ce qui est ENFERMÉ
# par le contour bleu) ; le contour bleu foncé est DESSINÉ autour de tout le nom (épaisseur et couleur MESURÉES sur 5 bannières :
# ~6-7 px pour une x-height de 125, couleur 0,30,135), puis la lueur blanche. Plus de coupures ni de jointures entre lettres.
EP_TOTEM = 10.0                      # MESURÉ ligne par ligne (bleu 10 px sur 3 bannières)
LARGEUR_LUEUR_TOTEM = 0.8                 # (ajusté sur les profils ligne par ligne du jeu)
OMBRE_DESSUS_TOTEM = True
COUL_CONTOUR_TOTEM = np.array([0, 30, 135], np.float32) / 255
CHEV_REMPL_TOTEM = -0.12            # remplissages séparés par deux contours (0,04 d'avant - 2 x 6,5 / 125)


def _contour_totem(toile, xh):
    k = xh / XH_TOTEM
    ep = EP_TOTEM * k
    F = _flou(toile[..., 3], 1) > 0.5
    d = _distance(F, int(ep) + 4)
    a_c = np.clip(ep + 0.5 - d, 0, 1).astype(np.float32)
    couche = np.concatenate([np.broadcast_to(COUL_CONTOUR_TOTEM, F.shape + (3,)), a_c[..., None]], -1).astype(np.float32)
    toile[:] = _sur(toile, couche)


def _totem_remplissage(a, r):
    af = a.astype(np.float32) / 255
    rgb, al = af[..., :3], af[..., 3]
    sat = rgb.max(-1) - rgb.min(-1)
    bleu = (al > 0.5) & (rgb.max(-1) < 0.62) & (rgb[..., 2] > rgb[..., 0]) & (sat > 0.3)
    lum = rgb.mean(-1)
    FI = (al > 0.7) & (lum > 0.55) & (rgb[..., 2] >= rgb[..., 0])
    # enfermé par le contour bleu (pas atteignable depuis le bord de l'image) et contenant du remplissage
    libre2 = ~bleu[::2, ::2]
    H2, W2 = libre2.shape
    comps = []
    for ys, xs in _composantes(libre2):
        if ys.min() == 0 or xs.min() == 0 or ys.max() == H2 - 1 or xs.max() == W2 - 1:
            continue
        if FI[::2, ::2][ys, xs].sum() < 15:          # creux d'une lettre (fond, lueur) : pas du remplissage
            continue
        comps.append((ys, xs))
    out = []
    for c, im, x0, y0, base, xh in r:
        h, w = im.shape[:2]
        S2 = np.zeros((H2, W2), bool)
        S_ = np.zeros(FI.shape, bool)
        S_[y0:y0 + h, x0:x0 + w] = FI[y0:y0 + h, x0:x0 + w] & (im[..., 3] > 150)
        S2 = S_[::2, ::2]
        m2 = np.zeros((H2, W2), bool)
        for ys, xs in comps:
            if S2[ys, xs].any():
                m2[ys, xs] = True
        if not m2.any():
            continue
        m = np.kron(m2, np.ones((2, 2), bool))[:a.shape[0], :a.shape[1]]
        m = (_dilater(m, 1) <= 1) & ~bleu & (al > 0.5)      # bord à pleine résolution, sans le contour
        ys, xs = np.nonzero(m)
        Y0, Y1, X0, X1 = max(0, ys.min() - 2), min(a.shape[0], ys.max() + 3), max(0, xs.min() - 2), min(a.shape[1], xs.max() + 3)
        mc = m[Y0:Y1, X0:X1]
        crop = af[Y0:Y1, X0:X1].copy()
        # bord du remplissage : couleurs de l'intérieur (pas le mélange avec le bleu du contour)
        coeur = _dilater(~mc, 2) > 2
        if coeur.any():
            moy = None
            for r_ in (3, 7, 14):
                w_ = _flou(coeur.astype(np.float32), r_)
                m_ = np.stack([_flou(np.where(coeur, crop[..., k_], 0), r_) for k_ in range(3)], -1) / np.maximum(w_[..., None], 1e-6)
                moy = np.where((w_ > 1e-3)[..., None], m_, moy if moy is not None else crop[..., :3])
            crop[..., :3] = np.where((mc & ~coeur)[..., None], moy, crop[..., :3])
        crop[..., 3] = np.where(mc, 1.0, 0.0)
        crop[..., 3] = np.where(mc & (_dilater(~mc, 1) == 1), 0.7, crop[..., 3])
        crop, dy, dx = _recadrer(crop)
        out.append((c, (np.clip(crop, 0, 1) * 255 + 0.5).astype(np.uint8), int(X0 + dx), int(Y0 + dy), base, xh))
    return out
