"""Relief du tissu : l'image « oc » d'un maillot du jeu (ombres des plis, canaux rouge et vert) contient souvent aussi
les coutures et décorations du maillot d'origine (cols en V, lignes, demi-lunes…), que le jeu dessine en relief
par-dessus le nouveau dessin. On les enlève en gardant les plis.

Modes : 'simples' (plis gardés, fines lignes et petits motifs enlevés), 'base' (comme le maillot du jeu), 'aucun' (tout plat).
"""
MODES = ('simples', 'base', 'aucun')


def _fermeture_canal(vals, w, h, r):
    """fermeture morphologique (max puis min sur une fenêtre de (2r+1)²) : efface les traits sombres plus fins que 2r"""
    def passe(v, f):
        # horizontal
        out = []
        for y in range(h):
            ligne = v[y * w:(y + 1) * w]
            out.extend(f(ligne[max(0, x - r):x + r + 1]) for x in range(w))
        # vertical
        res = [0] * (w * h)
        for x in range(w):
            col = out[x::w]
            for y in range(h):
                res[y * w + x] = f(col[max(0, y - r):y + r + 1])
        return res
    return passe(passe(vals, max), min)


def nettoyer_oc(w, h, rows, mode='simples', rayon=None):
    if mode == 'base':
        return rows
    out = [bytearray(r) for r in rows]
    if mode == 'aucun':
        for r in out:
            for i in range(0, len(r), 4):
                r[i] = r[i + 1] = 255
        return out
    rayon = rayon or max(2, w // 96)   # 5 px pour une image de 512
    for c in (0, 1):                   # rouge et vert (le bleu est vide)
        vals = [r[i] for r in rows for i in range(c, w * 4, 4)]
        vals = _fermeture_canal(vals, w, h, rayon)
        for y in range(h):
            ligne = out[y]
            base = y * w
            for x in range(w):
                ligne[x * 4 + c] = vals[base + x]
    return out


def uni(w, h, rows):
    """image d'une seule couleur (la plus courante) : pour les reflets « sp » qui suivent le dessin d'origine"""
    compte = {}
    for y in range(0, h, 4):
        r = rows[y]
        for x in range(0, w, 4):
            p = bytes(r[x * 4:x * 4 + 4])
            compte[p] = compte.get(p, 0) + 1
    p = max(compte, key=compte.get)
    return [bytearray(p * w) for _ in range(h)]


def _salete(w, h, rows):
    """plus c'est grand, plus l'ombrage contient de dessins (traits ou formes presque noirs sur le corps)"""
    n = 0
    for y in range(int(h * 0.47), h - h // 40, 2):
        r = rows[y]
        for x in range(w // 40, w - w // 40, 2):
            if r[x * 4] < 60 or r[x * 4 + 1] < 60:
                n += 1
    return n


def _oc(g, suf):
    from . import images
    n = next((x for x in g.noms if x.endswith('_%soc' % suf)), None)
    return (n, g.image(n)) if n else (None, None)


def reference(cat, dossier, cache_json, journal=print, essais=12):
    """maillot le plus uni (ombrage sans dessin) parmi ceux qui ont la même coupe (même dossier de textures)"""
    import os, json
    from . import images
    try:
        refs = json.load(open(cache_json, encoding='utf-8'))
    except Exception:
        refs = {}
    if dossier in refs:
        return refs[dossier]
    meme = sorted([c for c in cat if os.path.basename(os.path.dirname(c['tex10'])) == dossier], key=lambda c: c['cle'])
    journal('relief : recherche du maillot le plus uni de cette coupe (%d maillots, une seule fois)…' % min(len(meme), essais))
    meilleur = None
    for c in meme[:essais]:
        try:
            g = images.G4TX(open(c['tex10'], 'rb').read())
            n, im = _oc(g, '20')
            if not im:
                continue
            s = _salete(*im)
            if meilleur is None or s < meilleur[1]:
                meilleur = (c['cle'], s)
        except Exception:
            continue
    refs[dossier] = meilleur
    try:
        json.dump(refs, open(cache_json, 'w', encoding='utf-8'), indent=1)
    except OSError:
        pass
    return meilleur


def oc_pour(cat, base, suf, mode, cache_dir, journal=print):
    """ombrage (w, h, lignes) à mettre dans la texture du nouveau maillot pour la partie suf ('20' haut, '30' short),
    ou None pour garder celui du maillot de base"""
    import os
    from . import images
    if mode not in MODES or mode == 'base':
        return None
    os.makedirs(cache_dir, exist_ok=True)
    dossier = os.path.basename(os.path.dirname(base['tex10']))
    f = os.path.join(cache_dir, 'oc_%s_%s_%s_%s.png' % (dossier, base['cle'], suf, mode))
    if os.path.exists(f):
        return images.lire_png(f)
    g = images.G4TX(open(base['tex10'], 'rb').read())
    n, im = _oc(g, suf)
    if not im:
        return None
    if mode == 'aucun':
        res = (im[0], im[1], nettoyer_oc(*im, 'aucun'))
    else:
        ref = reference(cat, dossier, os.path.join(cache_dir, 'plis_reference.json'), journal)
        s_base = _salete(*_oc(g, '20')[1])
        PROPRE = 800                       # un ombrage uni (plis seuls) fait 350 à 600
        if s_base <= PROPRE:
            res = (im[0], im[1], nettoyer_oc(*im, 'simples'))          # déjà propre : juste les fines lignes
        else:
            pris = False
            if ref and ref[0] != base['cle'] and ref[1] <= PROPRE:
                rc = next(c for c in cat if c['cle'] == ref[0])
                n2, im2 = _oc(images.G4TX(open(rc['tex10'], 'rb').read()), suf)
                if im2 and im2[:2] == im[:2]:
                    im, pris = im2, True
            res = (im[0], im[1], nettoyer_oc(*im, 'simples'))
            if not pris:
                # formes épaisses qui restent : effacées seulement là où elles sont (le reste garde ses plis)
                w, h = im[0], im[1]
                fort = nettoyer_oc(*im, 'simples', max(4, w // 32))
                for y in range(int(h * 0.44), int(h * 0.93)):
                    a_, b_ = res[2][y], fort[y]
                    for x in range(w // 40, w - w // 40):
                        if a_[x * 4] < 70 or a_[x * 4 + 1] < 70:
                            a_[x * 4:x * 4 + 4] = b_[x * 4:x * 4 + 4]
            if not pris and _salete(*res) > PROPRE:
                res = (im[0], im[1], nettoyer_oc(*im, 'aucun'))            # trop dessiné : tout plat
    images.ecrire_png(f, *res)
    return res
