"""(16/11/2026) RECOLORER LE PORTRAIT DESSINÉ D'UNE COPIE « COMME LES MODIFS » (demande de muku : le dessin du jeu, pas une
photo ; le dessin d'un esprit est de trois quarts, une photo de face ne lui ressemble pas).

Les projets ne gardent que la texture finale (pas la liste des changements) : les changements sont DÉDUITS en comparant
pixel par pixel la texture d'origine et la texture modifiée.
1. couleurs de la texture d'origine regroupées (k-moyennes, ~12 groupes ; nuances proches et lumière/ombre d'une même
   couleur réunies) ;
2. pour chaque groupe : la part de ses pixels changés et la PALETTE d'arrivée (les couleurs principales des pixels changés :
   des cheveux bruns peints en bandes bleu / rouge / jaune donnent une palette de 3 couleurs) ;
3. dans le dessin, chaque pixel proche d'un groupe changé est repeint, avec sa propre lumière (ombres et reflets du dessin
   gardés : rapport de luminance au groupe) ; les traits noirs et les parties non touchées restent.
   - palette d'UNE couleur : cette couleur ;
   - palette de PLUSIEURS couleurs : la couleur est prise au même endroit sur une photo du modèle modifié (Atelier,
     photoIcone), mise au cadre du dessin par les boîtes des silhouettes ; un endroit de la photo qui n'est pas de cette
     palette (peau, fond…) prend la couleur de palette la plus proche autour (propagation).
Limite : la photo est de face ; un dessin de trois quarts (esprits) ne tombe qu'à peu près aux mêmes endroits.
"""
import numpy as np


def _px(w, h, rows):
    return np.frombuffer(b''.join(bytes(r) for r in rows), np.uint8)[:w * h * 4].reshape(h, w, 4).astype(np.float32)


def _lum(c):
    return c[..., 0] * 0.299 + c[..., 1] * 0.587 + c[..., 2] * 0.114


def _meme_teinte(a, b, ecart=0.035):
    """deux groupes = la lumière et l'ombre d'une même couleur (peau claire / peau d'ombre : mêmes proportions R:V:B) ;
    pas pour le noir, le blanc ni les gris (proportions instables)"""
    for c in (a, b):
        if c.sum() < 75 or c.min() > 215 or c.max() - c.min() < 40:
            return False
    return np.abs(a / a.sum() - b / b.sum()).max() < ecart


def _palette(B, part=0.08, case=24):
    """couleurs principales (cases de 24 ; chacune >= 8 % des pixels), la plus fréquente d'abord"""
    q = (B // case).astype(np.int32)
    cle = q[:, 0] * 10000 + q[:, 1] * 100 + q[:, 2]
    v, n = np.unique(cle, return_counts=True)
    o = np.argsort(-n)
    pal = [B[cle == v[i]].mean(0) for i in o if n[i] >= part * len(B)] or [B[cle == v[o[0]]].mean(0)]
    # deux cases voisines de la même couleur (dégradé coupé par la grille) : une seule
    res = []
    for c in pal:
        if all(np.sqrt(((c - r) ** 2).sum()) > 40 for r in res):
            res.append(c)
    return np.array(res)


def correspondances(orig, modif, k=12, seuil=28.0, fusion=45.0):
    """orig, modif : (w, h, rangées) de même taille -> liste de groupes
    {'c': nuance d'origine RGB, 'lref': luminance du groupe, 'part': part changée, 'pal': couleurs d'arrivée (n, 3)}"""
    a, b = _px(*orig), _px(*modif)
    m = a[..., 3] > 16
    A, B = a[m][:, :3], b[m][:, :3]
    if len(A) > 120000:
        i = np.random.default_rng(1).choice(len(A), 120000, replace=False); A, B = A[i], B[i]
    C = A[np.random.default_rng(2).choice(len(A), k, replace=False)]
    for _ in range(12):                                      # k-moyennes
        lab = np.argmin(((A[:, None, :] - C[None]) ** 2).sum(2), 1)
        C = np.array([A[lab == j].mean(0) if (lab == j).any() else C[j] for j in range(k)])
    lab = np.argmin(((A[:, None, :] - C[None]) ** 2).sum(2), 1)
    # nuances proches (les bruns des cheveux) et lumière/ombre d'une couleur (peau) : un seul groupe
    # (16/11/2026) réunion « complète » : deux ensembles ne se réunissent que si TOUTES leurs nuances sont proches deux à
    # deux (sinon de proche en proche blanc -> crème -> jaune : le corps blanc et la crinière jaune d'un totem dans un seul
    # groupe, et repeindre la crinière repeindrait le corps)
    proche = np.array([[np.sqrt(((C[i] - C[j]) ** 2).sum()) < fusion or _meme_teinte(C[i], C[j]) for j in range(k)] for i in range(k)])
    ens = [{i} for i in range(k)]
    while True:
        paire = next(((a, b) for a in range(len(ens)) for b in range(a + 1, len(ens))
                      if all(proche[i, j] for i in ens[a] for j in ens[b])), None)
        if paire is None:
            break
        a, b = paire
        ens[a] |= ens.pop(b)
    racine = {i: min(e) for e in ens for i in e}
    parent = [racine[i] for i in range(k)]
    def f(x):
        return parent[x]
    C0, lab0 = C.copy(), lab
    lab = np.array([f(x) for x in range(k)])[lab]
    out = []
    for j in sorted(set(lab.tolist())):
        s = lab == j
        if s.sum() < 50:
            continue
        ch = np.sqrt(((B[s] - A[s]) ** 2).sum(1)) > seuil
        part = float(ch.mean())
        pal = _palette(B[s][ch] if ch.sum() >= 50 else B[s])
        lj = max(float(_lum(A[s].mean(0))), 8.0)
        # une entrée par nuance d'origine du groupe : un pixel d'ombre du dessin est reconnu par l'ombre du groupe
        for x in range(k):
            if f(x) == j and (lab0 == x).sum() >= 20:
                out.append({'c': C0[x], 'lref': lj, 'part': part, 'pal': pal, 'g': j})
    return out


def combiner(*listes, part_min=0.35, fusion=45.0):
    """plusieurs textures (cheveux + visage d'une tête) : un groupe resté tel quel dans l'une ne doit pas retenir la même
    nuance changée dans l'autre (brun des cheveux repeints / brun des sourcils du visage : sinon mèches restées brunes)"""
    tout = []
    for n, l in enumerate(listes):
        tout += [dict(g, g=(n, g['g'])) for g in l]
    ch = [g for g in tout if g['part'] >= part_min]
    return ch + [g for g in tout if g['part'] < part_min
                 and all(np.sqrt(((g['c'] - c['c']) ** 2).sum()) >= fusion for c in ch)]


def _cadre(alpha):
    ys, xs = np.nonzero(alpha > 128)
    return (xs.min(), ys.min(), xs.max() + 1, ys.max() + 1) if len(xs) else None


def _carte_palette(photo, pal, autres=None, ecart=45.0):
    """photo (h, w, 4) -> indice de la couleur de palette à chaque endroit (propagée aux endroits d'une autre couleur) ;
    autres : couleurs restées telles quelles (peau…) : un endroit plus proche d'elles n'est pas de la palette (sinon la peau
    passe pour le jaune pâle des pointes, et la frange se borde de jaune)"""
    h, w = photo.shape[:2]
    rgb = photo[..., :3]
    n = len(pal)
    if autres is not None and len(autres):
        pal = np.concatenate([pal, autres], 0)
    # écart à chaque couleur de palette, lumière de la photo mise à part (couleur x facteur 0,4 … 1,6)
    t = pal[None, None]                                              # (1, 1, n, 3)
    s = np.clip((rgb[..., None, :] * t).sum(3) / np.maximum((t * t).sum(3), 1), 0.4, 1.6)
    d = np.sqrt(((rgb[..., None, :] - t * s[..., None]) ** 2).sum(3))
    idx = np.argmin(d, 2)
    ok = (np.take_along_axis(d, idx[..., None], 2)[..., 0] < ecart) & (photo[..., 3] > 128) & (idx < n)
    if not ok.any():
        return None
    lab = np.where(ok, idx, -1)
    for _ in range(max(h, w)):                                       # propagation aux voisins (4 directions)
        vide = lab < 0
        if not vide.any():
            break
        n = lab.copy()
        for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            v = np.roll(lab, (dy, dx), (0, 1))
            n = np.where((n < 0) & (v >= 0), v, n)
        if (n == lab).all():
            break
        lab = n
    return lab


def _masse(m, r=2):
    """garde les grandes zones d'un masque et ce qui les touche ; enlève les traits fins isolés (cils, contour du visage,
    bouche : même brun que les cheveux dans le dessin, mais pas des cheveux)"""
    def er(x, k):
        for _ in range(k):
            x = x & np.roll(x, 1, 0) & np.roll(x, -1, 0) & np.roll(x, 1, 1) & np.roll(x, -1, 1)
        return x
    def di(x, k):
        for _ in range(k):
            x = x | np.roll(x, 1, 0) | np.roll(x, -1, 0) | np.roll(x, 1, 1) | np.roll(x, -1, 1)
        return x
    coeur = di(er(m, r), r + 2)
    for _ in range(6):                                 # traits du dessin DANS les cheveux (mèches) : rattachés de proche en proche
        coeur = di(coeur, 1) & m | coeur
    return m & coeur


def _lisse(lab, pal, r=3):
    """couleur de palette par endroit, bords adoucis (moyenne sur (2r+1)² : la photo agrandie au cadre fait des marches)"""
    h, w = lab.shape
    un = (lab[..., None] == np.arange(len(pal))[None, None]).astype(np.float32)
    s = np.pad(un, ((r + 1, r), (r + 1, r), (0, 0)), mode='edge').cumsum(0).cumsum(1)
    b = s[2 * r + 1:, 2 * r + 1:] - s[:h, 2 * r + 1:] - s[2 * r + 1:, :w] + s[:h, :w]
    b /= np.maximum(b.sum(2, keepdims=True), 1e-6)
    return b @ pal


def recolorer(img, corresp, photo=None, part_min=0.35, dist_max=90.0):
    """img : (w, h, rangées) du dessin ; photo : (w, h, rangées) du modèle modifié ou None -> rangées recolorées.
    (16/11/2026, « pixels bizarres un peu partout ») les pixels de TRANSITION du dessin (bord adouci entre une plume rouge et
    son trait noir, entre deux couleurs…) ne ressemblent à aucun groupe : avant, ils restaient d'origine (points rouges dans
    les ailes devenues noires). Maintenant chaque pixel est placé entre ses DEUX groupes les plus proches (position t sur le
    segment qui les relie) et prend le même mélange de leurs deux nouvelles couleurs."""
    w, h, rows = img
    p = _px(w, h, rows)
    rgb = p[..., :3]
    K = len(corresp)
    centres = np.array([g['c'] for g in corresp])
    d = np.sqrt(((rgb[..., None, :] - centres[None, None]) ** 2).sum(3))
    o = np.argsort(d, 2)
    j1, j2 = o[..., 0], (o[..., 1] if K > 1 else o[..., 0])
    c1, c2 = centres[j1], centres[j2]
    v = c2 - c1
    t = np.clip(((rgb - c1) * v).sum(2) / np.maximum((v * v).sum(2), 1e-6), 0, 1)
    r = np.sqrt(((rgb - (c1 + t[..., None] * v)) ** 2).sum(2))
    d1 = np.take_along_axis(d, j1[..., None], 2)[..., 0]
    t = np.where(r < d1, t, 0.0)                          # entre deux groupes seulement si le segment l'explique mieux
    dfit = np.minimum(r, d1)
    parts = np.array([g['part'] for g in corresp]); lrefs = np.array([g['lref'] for g in corresp])
    vis = p[..., 3] > 0
    # mise au cadre photo -> dessin (boîtes des silhouettes)
    ph = cd = cp = None
    if photo is not None:
        ph = _px(*photo)
        cd, cp = _cadre(p[..., 3]), _cadre(ph[..., 3])
    yy, xx = np.mgrid[0:h, 0:w]
    if cd and cp:
        px_ = np.clip(((xx - cd[0]) * (cp[2] - cp[0]) / max(cd[2] - cd[0], 1) + cp[0]).astype(int), 0, ph.shape[1] - 1)
        py_ = np.clip(((yy - cd[1]) * (cp[3] - cp[1]) / max(cd[3] - cd[1], 1) + cp[1]).astype(int), 0, ph.shape[0] - 1)
    autres = np.array([g['c'] for g in corresp if g['part'] < part_min])
    multi = np.array([len(g['pal']) > 1 for g in corresp])
    # parties en plusieurs couleurs (cheveux en bandes) : les traits fins isolés du même brun (cils, contour) n'en sont pas
    plus = vis & (parts[j1] >= part_min) & multi[j1] & (dfit <= dist_max)
    masse = _masse(plus) if plus.any() else plus
    # trait fin gardé quand même s'il est ENTOURÉ de parties changées (mèche brune au milieu d'une crinière repeinte) ;
    # un cil, entouré de peau et de blanc d'œil gardés, reste écarté
    if plus.any():
        chg = (vis & (parts[j1] >= part_min) & (dfit <= dist_max)).astype(np.float32)
        r_ = 4
        s_ = np.pad(chg, ((r_ + 1, r_), (r_ + 1, r_)), mode='edge').cumsum(0).cumsum(1)
        dens = (s_[2 * r_ + 1:, 2 * r_ + 1:] - s_[:h, 2 * r_ + 1:] - s_[2 * r_ + 1:, :w] + s_[:h, :w]) / (2 * r_ + 1) ** 2
        masse = masse | (plus & (dens > 0.6))
    faits = {}

    def couleur(k):
        """nouvelle couleur de base du groupe k, par pixel (h, w, 3)"""
        g = corresp[k]; pal = g['pal']
        if len(pal) == 1 or not (cd and cp):
            return np.broadcast_to(pal[0], rgb.shape)
        if id(pal) not in faits:
            lab = _carte_palette(ph, pal, autres)
            faits[id(pal)] = pal[0][None, None] * np.ones_like(rgb) if lab is None else _lisse(lab[py_, px_], pal)
        return faits[id(pal)]

    def recol(jj, autre):
        """le pixel recoloré comme s'il était du groupe jj ; groupe pas changé : le pixel d'origine, sauf sur une transition
        vers un groupe changé, où c'est la couleur du groupe (sinon un pixel entre un trait noir gardé et une plume rouge
        devenue noire garde du rouge)"""
        out = rgb.copy()
        trans = (t > 0) & (parts[autre] >= part_min) & (parts[jj] < part_min) & vis
        out[trans] = centres[jj][trans]
        ratio = np.clip(_lum(rgb) / lrefs[jj], 0.25, 2.2)[..., None]
        for k in range(K):
            if parts[k] < part_min:
                continue
            sel = (jj == k) & vis & (dfit <= dist_max)
            if multi[k]:
                sel &= masse
            if sel.any():
                out[sel] = np.clip(couleur(k)[sel] * ratio[sel], 0, 255)
        return out

    a, b = recol(j1, j2), recol(j2, j1)
    neuf = a + t[..., None] * (b - a)
    out = np.concatenate([np.clip(neuf, 0, 255), p[..., 3:]], 2).astype(np.uint8)
    return [bytearray(out[y].tobytes()) for y in range(h)]
