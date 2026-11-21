"""Numéros dans le dos : planches de chiffres (0 à 99) du jeu, modèle 3D du numéro, et numéro redimensionné / déplacé.

Dans le jeu, chaque ligne de [[clothes]] a un modèle de numéro (lower_mesh = _uniform/n000101/n0001NN.g4md, NN = corps)
et une planche de chiffres (lower_texture = _uniform/n000101/n00010P_10.g4tx, P = police 1 à 6). Les couleurs du numéro
se règlent avec [[number]] clothes = "<modèle>", fill = "RRGGBB", outline = "RRGGBB" (VRFW).
"""
import os, struct
from . import images, retouche, modele3d

POLICES = [(i, 'Police %d' % i, 'n00010%d_10.g4tx' % i) for i in range(1, 7)]
# corps du modèle de numéro pour chaque ligne des modèles de maillot (relevé sur les maillots du jeu)
CORPS_LIGNES = {'': [1, 2, 3, 4, 5, 6, 7, 8, 6, 7, 3, 4, 7, 7], '_slv': [1, 6], '_fld': [1], '_dam': [7], '_blyR': [2]}
DEFAUT = {'perso': False, 'remplissage': 'FFFFFF', 'contour': '1A1A1A', 'police': 1, 'taille': 1.0, 'hauteur': 0.0,
          'nom': False, 'lettres': 'jeu', 'chiffres': None}
# (16/11/2026) chiffres : police de l'ordinateur pour les chiffres (None = planche du jeu n00010<police>_10). La planche
# est dessinée dans l'Atelier (web/app.js mmPlanches) au format du jeu, LU sur n000101_10.g4tx : 2048 x 2048, 10 x 10 cases
# de 204,8 px (0 à 99 de gauche à droite, de haut en bas), image blanche (alpha = forme avec contour) + masque <nom>msk
# (vert = remplissage, bleu = contour).
# style « nom + numéro » : modèles n0002NN (numéro + nom du joueur au-dessus) et planches de n000201_10.g4tx
LETTRES = ('noms', 'noms_msk', 'num', 'num_msk')      # images faites par le studio : lettres_<x>.png


def params(m):
    p = dict(DEFAUT)
    p.update(m.get('numero') or {})
    return p


def dossier(donnees, sous='common'):
    return os.path.join(donnees, sous, 'chr', '_uniform', 'n000101')


def planche_png(donnees, police, cache_dir):
    """planche pour l'aperçu : R = masque du remplissage (le reste = contour), A = forme des chiffres ; 1024 x 1024"""
    os.makedirs(cache_dir, exist_ok=True)
    out = os.path.join(cache_dir, 'planche_numeros_%d.png' % police)
    if os.path.exists(out):
        return out
    f = os.path.join(dossier(donnees, 'dx11'), 'n00010%d_10.g4tx' % police)
    if police == 0:                    # style « nom + numéro » du jeu
        f = os.path.join(donnees, 'dx11', 'chr', '_uniform', 'n000201', 'n000201_10.g4tx')
    g = images.G4TX(open(f, 'rb').read())
    nom = next(n for n in g.noms if n.endswith('_10') and not n.startswith('name'))
    w, h, rows = g.image(nom)
    mw, mh, mrows = g.image(nom + 'msk') if (nom + 'msk') in g.noms else (w, h, None)
    w2, h2, r2 = w, h, rows
    while w2 > 1024:                   # réduction par moyenne (bords nets, contour gardé)
        w2, h2, r2 = images.moitie(w2, h2, r2)
    m2 = None
    if mrows is not None:
        mw2, mh2, m2 = mw, mh, mrows
        while mw2 > w2:
            mw2, mh2, m2 = images.moitie(mw2, mh2, m2)
        if (mw2, mh2) != (w2, h2):
            m2 = images.redimensionner(mw2, mh2, m2, w2, h2)
    sortie = []
    for y in range(h2):
        a, m = r2[y], (m2[y] if m2 is not None else None)
        o = bytearray(w2 * 4)
        for x in range(w2):
            o[x * 4] = m[x * 4 + 1] if m is not None else 255      # vert du masque = remplissage
            o[x * 4 + 3] = a[x * 4 + 3]
        sortie.append(o)
    images.ecrire_png(out, w2, h2, sortie)
    return out


def modele_numero(donnees, corps=1, famille='n0001'):
    base = os.path.join(donnees, 'common', 'chr', '_uniform', famille + '01')
    p = os.path.join(base, '%s%02d.g4md' % (famille, corps))
    if not os.path.exists(p):
        p = os.path.join(base, famille + '01.g4md')
    ms = modele3d.lire(p)
    nom = max((n for n in ms if 'LOD' not in n and not n.startswith('name')), key=lambda n: len(ms[n][0]))
    return ms[nom]


def transformer(pos, taille, hauteur, cy=None, zf=None):
    """agrandit le numéro autour de son centre (en suivant la courbure du dos) et le monte / descend (mètres)"""
    ys, zs = pos[1::3], pos[2::3]
    cy = (min(ys) + max(ys)) / 2 if cy is None else cy
    zf = min(zs) if zf is None else zf   # le milieu du dos (le plus en arrière)
    out = list(pos)
    for i in range(0, len(pos), 3):
        x, y, z = pos[i], pos[i + 1], pos[i + 2]
        out[i] = x * taille
        out[i + 1] = cy + (y - cy) * taille + hauteur
        out[i + 2] = zf + (z - zf) * taille - 0.002 * abs(taille - 1)
    return out


def ecrire_modele_transforme(donnees, corps, taille, hauteur, dest, nom, famille='n0001'):
    """copie <famille><corps>.g4md/.g4mg en <dest>/<nom>.g4md/.g4mg avec les positions transformées
    (tous les morceaux autour du même centre : le nom et le numéro restent ensemble)"""
    src = os.path.join(donnees, 'common', 'chr', '_uniform', famille + '01', '%s%02d.g4md' % (famille, corps))
    md = open(src, 'rb').read()
    mg = bytearray(open(src[:-2] + 'mg', 'rb').read())
    n = struct.unpack_from('<H', md, 0x20)[0]
    maillages = [struct.unpack_from('<4I', md, 0xA0 + 0x50 * i) for i in range(n)]
    total = sum(m[2] for m in maillages)
    pas = struct.unpack_from('<I', md, 0x50)[0] // total
    o_pos = 0                         # position = 1er attribut (3 flottants)
    tout = []
    for i, (vb, ib, nv, ni) in enumerate(maillages):
        p_ = md[0xA0 + 0x50 * i + 0x3E]
        p_ = p_ if 16 <= p_ <= 255 else pas
        for k in range(nv):
            tout.extend(struct.unpack_from('<3f', mg, vb + k * p_ + o_pos))
    cy = (min(tout[1::3]) + max(tout[1::3])) / 2
    zf = min(tout[2::3])
    for i, (vb, ib, nv, ni) in enumerate(maillages):
        p_ = md[0xA0 + 0x50 * i + 0x3E]
        pas = p_ if 16 <= p_ <= 255 else pas
        pos = []
        for k in range(nv):
            pos.extend(struct.unpack_from('<3f', mg, vb + k * pas + o_pos))
        nouv = transformer(pos, taille, hauteur, cy, zf)
        for k in range(nv):
            struct.pack_into('<3f', mg, vb + k * pas + o_pos, *nouv[k * 3:k * 3 + 3])
    os.makedirs(dest, exist_ok=True)
    open(os.path.join(dest, nom + '.g4md'), 'wb').write(md)
    open(os.path.join(dest, nom + '.g4mg'), 'wb').write(bytes(mg))


def texture_perso(donnees, dossier_kit, dest, avec_nom, pool=None, journal=print):
    """(16/11/2026) copie de la texture du numéro où les planches faites dans l'Atelier remplacent celles du jeu :
    chiffres (lettres_num / num_msk) et, avec le nom, lettres (lettres_noms / noms_msk) ; une planche absente reste celle du
    jeu. avec_nom False : n000101_10.g4tx (numéro seul), True : n000201_10.g4tx. False si rien à remplacer."""
    base = ('n000201', 'n000201_10.g4tx') if avec_nom else ('n000101', 'n000101_10.g4tx')
    g = images.G4TX(open(os.path.join(donnees, 'dx11', 'chr', '_uniform', base[0], base[1]), 'rb').read())
    paires = [(base[0] + '_10', 'num'), (base[0] + '_10msk', 'num_msk')]
    if avec_nom:
        paires += [('name_10', 'noms'), ('name_10msk', 'noms_msk')]
    rempl = {}
    for nom_img, cle in paires:
        f = os.path.join(dossier_kit, 'lettres_%s.png' % cle)
        if not os.path.exists(f) or nom_img not in g.noms:
            continue
        i = g.noms.index(nom_img)
        tw, th = g.taille(nom_img)
        w, h, rows = images.lire_png(f)
        if (w, h) != (tw, th):
            rows = images.redimensionner(w, h, rows, tw, th)
        if cle.startswith('noms'):                   # lignes 13 à 15 de la planche (ponctuation) : celles du jeu
            jw, jh, jr = g.image(nom_img)
            rows = [bytearray(r) for r in rows]
            for y in range(13 * th // 16, th):
                rows[y] = bytearray(jr[y])
        bl = g.blocs[i]
        journal('numéro : %s (%dx%d)…' % (nom_img, tw, th))
        rempl[nom_img] = images.dds_bc7(tw, th, rows, bl[:148], images.mips_dds(bl), pool)
    if not rempl:
        return False
    open(dest, 'wb').write(g.reconstruire(rempl))
    return True


def texture_nom(donnees, dossier_kit, dest, pool=None, journal=print):
    """texture « nom + numéro » avec les lettres et chiffres faits par le studio (lettres_*.png du maillot) :
    copie de n000201_10.g4tx dont les planches des noms et des numéros sont remplacées ; False si pas de lettres"""
    fichiers = {k: os.path.join(dossier_kit, 'lettres_%s.png' % k) for k in LETTRES}
    if not all(os.path.exists(f) for f in fichiers.values()):
        return False
    g = images.G4TX(open(os.path.join(donnees, 'dx11', 'chr', '_uniform', 'n000201', 'n000201_10.g4tx'), 'rb').read())
    rempl = {}
    for nom_img, cle in (('name_10', 'noms'), ('name_10msk', 'noms_msk'), ('n000201_10', 'num'), ('n000201_10msk', 'num_msk')):
        i = g.noms.index(nom_img)
        tw, th = g.taille(nom_img)
        w, h, rows = images.lire_png(fichiers[cle])
        if (w, h) != (tw, th):
            rows = images.redimensionner(w, h, rows, tw, th)
        if cle.startswith('noms'):
            # lignes 13 à 15 de la planche (ponctuation) : celles du jeu
            jw, jh, jr = g.image(nom_img)
            rows = [bytearray(r) for r in rows]
            for y in range(13 * th // 16, th):
                rows[y] = bytearray(jr[y])
        bl = g.blocs[i]
        journal('lettres : %s (%dx%d)…' % (nom_img, tw, th))
        rempl[nom_img] = images.dds_bc7(tw, th, rows, bl[:148], images.mips_dds(bl), pool)
    open(dest, 'wb').write(g.reconstruire(rempl))
    return True
