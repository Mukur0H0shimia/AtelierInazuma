"""Lecture des modèles 3D des maillots (G4MD = description, G4MG = sommets + indices) pour l'aperçu 3D.

G4MD : en-tête 0xA0 octets ; u16 nombre de maillages à +0x20 ; à +0x50 taille des sommets, +0x54 taille des indices,
+0x5C début des indices dans le G4MG ; maillages de 0x50 octets à partir de 0xA0 (octet de début des sommets,
octet de début des indices, nombre de sommets, nombre d'indices) ; puis la table des attributs (8 octets chacun :
type, position dans le sommet, format) ; les noms des maillages sont à la fin, après les matériaux.
Sommet : position = 3 flottants, coordonnées de texture = 2 x u16 normalisés (type 0x0A).
"""
import os, struct, math

TYPE_POSITION, TYPE_UV = 0x01, 0x0A


def _noms_fin(md, n):
    """les n derniers noms (chaînes ASCII terminées par 0) à la fin du fichier"""
    fin = md.rstrip(b'\0')
    morceaux = fin.split(b'\0')
    noms = []
    for m in reversed(morceaux):
        if not m or any(c < 0x20 or c > 0x7e for c in m):
            break
        noms.append(m.decode('ascii'))
        if len(noms) == n:
            break
    return list(reversed(noms))


def lire(chemin_md):
    """renvoie {nom: (positions [x,y,z,...], uvs [u,v,...], indices [...])} pour chaque maillage"""
    md = open(chemin_md, 'rb').read()
    mg = open(chemin_md[:-2] + 'mg', 'rb').read()
    if md[:4] != b'G4MD':
        raise ValueError('pas un modèle G4MD : ' + chemin_md)
    n = struct.unpack_from('<H', md, 0x20)[0]
    taille_ib, debut_ib = struct.unpack_from('<I', md, 0x54)[0], struct.unpack_from('<I', md, 0x5C)[0]
    maillages = [struct.unpack_from('<4I', md, 0xA0 + 0x50 * i) for i in range(n)]
    # table des attributs : juste après les maillages, commence par 00 0a 00 00 (nombre ?) puis 8 octets par attribut
    t = 0xA0 + 0x50 * n
    attrs = {}
    p = t + 8
    while p + 8 <= len(md):
        typ = md[p]
        fmt = struct.unpack_from('<I', md, p + 4)[0]
        if typ == 0 and fmt == 0:
            break
        attrs.setdefault(typ, (md[p + 1], fmt))
        p += 8
    if TYPE_POSITION not in attrs or TYPE_UV not in attrs:
        raise ValueError('attributs introuvables dans ' + chemin_md)
    # taille d'un sommet : taille totale des sommets / nombre total de sommets (les maillages ne sont pas
    # toujours rangés dans l'ordre du fichier)
    taille_vb = struct.unpack_from('<I', md, 0x50)[0]
    total = sum(m[2] for m in maillages)
    pas = taille_vb // total if total else 0
    o_pos, o_uv = attrs[TYPE_POSITION][0], attrs[TYPE_UV][0]
    noms = _noms_fin(md, n)
    if len(noms) == n:
        # l'octet +0x38 de chaque maillage donne, par son ordre de tri, sa place dans la liste des noms
        rang = sorted(range(n), key=lambda i: md[0xA0 + 0x50 * i + 0x38])
        par = {i: noms[r] for r, i in enumerate(rang)}
        noms = [par[i] for i in range(n)]
    else:
        noms = ['maillage_%d' % i for i in range(n)]
    sortie = {}
    for i, (nom, (vb, ib, nv, ni)) in enumerate(zip(noms, maillages)):
        # taille d'un sommet de ce maillage (octet +0x3E de sa description) : elle peut changer d'un maillage à l'autre
        p_ = md[0xA0 + 0x50 * i + 0x3E]
        p_ = p_ if 16 <= p_ <= 255 and vb + nv * p_ <= len(mg) else pas
        pos, uv = [], []
        for k in range(nv):
            b = vb + k * p_
            pos.extend(struct.unpack_from('<3f', mg, b + o_pos))
            u, v = struct.unpack_from('<2H', mg, b + o_uv)
            uv.extend((u / 65535.0, v / 65535.0))
        idx = list(struct.unpack_from('<%dH' % ni, mg, debut_ib + ib))
        if not all(math.isfinite(v) and abs(v) < 100 for v in pos) or (idx and max(idx) >= nv):
            continue                    # maillage illisible : ignoré plutôt que de casser l'aperçu
        sortie[nom] = (pos, uv, idx)
    return sortie


def _fusion(liste):
    pos, uv, idx = [], [], []
    for p, u, i in liste:
        base = len(pos) // 3
        pos.extend(p); uv.extend(u); idx.extend(k + base for k in i)
    return pos, uv, idx


def parties(chemin_md):
    """morceaux d'un modèle de maillot : {'haut': (pos, uv, idx), 'short': …, 'col10': …, 'col11': …, 'x22': …}
    d'après leur nom (_20 = image du haut, _30 = image du short, collar = col, autre numéro = pièce en plus
    avec sa propre image) ; sinon d'après leur forme"""
    import re
    ms = lire(chemin_md)
    groupes = {}
    for nom, m in ms.items():
        if 'LOD' in nom:
            continue
        if nom.startswith('collar_'):
            groupes.setdefault('col' + nom[-2:], []).append(m); continue
        r = re.search(r'_(\d\d)$', nom)
        if not r:
            groupes = None; break
        k = {'20': 'haut', '30': 'short'}.get(r.group(1), 'x' + r.group(1))
        groupes.setdefault(k, []).append(m)
    if groupes and 'haut' in groupes:
        return {k: (v[0] if len(v) == 1 else _fusion(v)) for k, v in groupes.items()}
    # noms illisibles : d'après la forme
    infos = []
    for nom, (pos, uv, idx) in ms.items():
        ys = pos[1::3]
        if ys:
            infos.append((min(ys), max(ys), len(ys), (pos, uv, idx)))
    out = {}
    H = max(i[1] for i in infos) if infos else 1.0
    hauts = [i for i in infos if i[0] >= 0.2 * H and i[1] > 0.7 * H and i[1] - i[0] > 0.15 * H]
    shorts = [i for i in infos if i[0] < 0.2 * H]
    cols = sorted([i for i in infos if i[0] > 0.8 * H and i[1] - i[0] < 0.1 * H], key=lambda i: i[2])
    if hauts:
        out['haut'] = max(hauts, key=lambda i: i[2])[3]
    if shorts:
        out['short' if hauts else 'haut'] = max(shorts, key=lambda i: i[2])[3]
    for k, c in zip(('col10', 'col11'), cols[:2]):
        out[k] = c[3]
    return out


def chemin_modele(donnees, tex10, corpulence=1):
    """modèle 3D d'un maillot : common/chr/_uniform/<dossier>/<dossier sans les 2 derniers chiffres><NN>.g4md"""
    dossier = os.path.basename(os.path.dirname(tex10))          # ex. u000101
    racine = os.path.join(donnees, 'common', 'chr', '_uniform', dossier)
    p = os.path.join(racine, '%s%02d.g4md' % (dossier[:-2], corpulence))
    if os.path.exists(p):
        return p
    p = os.path.join(racine, dossier + '.g4md')
    return p if os.path.exists(p) else None
