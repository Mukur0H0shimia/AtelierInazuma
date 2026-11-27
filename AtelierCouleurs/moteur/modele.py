"""Modèles avec os (joueurs, esprits guerriers, totems) pour l'animation des cinématiques.

Ce qui a été trouvé (13/11/2026, maillot u000101, tête mannequin c21000010, squelette c000101) :
- G4MD : u16 nb de maillages +0x20, nb de matériaux +0x22, **nb d'os +0x24** ; maillage (0x50 octets dès 0xA0) :
  sommets, indices, nb, nb (4 x u32), rang du nom +0x38, **début de palette u16 +0x3A, taille de palette u8 +0x3C**,
  pas +0x3E, disposition +0x42, matériau +0x43 ;
- sommet (68 octets) : position 3 flottants +0, **poids = 8 x u16 / 65535 (type 5, format 32)**, **os = 8 x u8 (type 6,
  format 24)** = numéros DANS LA PALETTE du maillage ; palette = tableau u16 de numéros d'os du squelette ;
- le modèle a SA liste d'os (nb d'os +0x24 ; crc32 des noms) : palette -> n° dans cette liste -> os du squelette
  par le crc32 (la tête mannequin n'a que 96 os ; le maillot en a 165, dans l'ordre du squelette) ;
- l'emplacement de la palette n'est pas lu dans l'en-tête : on essaie les positions possibles et on garde celle où
  chaque sommet est le plus près de son os principal (0x908 pour les maillots u000101 / u000102) ; résultat en cache ;
- noms des maillages : les n derniers noms du fichier (comme l'Atelier Maillots) ; la texture d'un maillage = la texture
  du même nom (u000101_20 -> u000101_20), sinon celle d'un autre maillage du même matériau.
Peau : position = somme des poids x (monde animé de l'os x inverse du monde au repos) x sommet.
"""
import os, struct, math, json, re

TYPES_POIDS, TYPE_OS, TYPE_UV, TYPE_NORMALE = 5, 6, 10, 2      # normale : 4 x s16 / 32767 (format 20) à +12


def _noms_fin(md, n):
    fin = md.rstrip(b'\0').split(b'\0')
    noms = []
    for m in reversed(fin):
        if not m or any(c < 0x20 or c > 0x7e for c in m):
            break
        noms.append(m.decode('ascii'))
        if len(noms) == n:
            break
    return list(reversed(noms))


def _dispositions(md, n):
    q = 0xA0 + 0x50 * n
    groupes, g = [], []
    while q + 8 <= len(md):
        t, o = md[q], md[q + 1]; f = struct.unpack_from('<I', md, q + 4)[0]
        if t > 16 or o > 80 or f > 0x40:
            break
        if t == 0:
            groupes.append(g); g = []
        else:
            g.append((t, o, f))
        q += 8
    return groupes


def _monde_repos(os_):
    """positions des os au repos (chaîne échelle / quaternion / position)"""
    def qm(q):
        x, y, z, w = q
        return [[1 - 2 * (y * y + z * z), 2 * (x * y - z * w), 2 * (x * z + y * w)],
                [2 * (x * y + z * w), 1 - 2 * (x * x + z * z), 2 * (y * z - x * w)],
                [2 * (x * z - y * w), 2 * (y * z + x * w), 1 - 2 * (x * x + y * y)]]
    W = []
    for o in os_:
        R = qm(o['r']); S = o['e']
        M = [[R[i][j] * S[j] for j in range(3)] + [o['t'][i]] for i in range(3)]
        if o['parent'] >= 0:
            P = W[o['parent']]
            M = [[sum(P[i][k] * M[k][j] for k in range(3)) + (P[i][3] if j == 3 else 0) for j in range(4)] for i in range(3)]
        W.append(M)
    return [(m[0][3], m[1][3], m[2][3]) for m in W]


def _table(md, o):
    """adresse d'une table de l'en-tête G4MD : base (u16 +0x0A x 4) + u16 à o x 4"""
    return struct.unpack_from('<H', md, 0x0A)[0] * 4 + struct.unpack_from('<H', md, o)[0] * 4


def table_os(md, nos, os_):
    """liste d'os du modèle -> n° dans le squelette.
    LECTURE DU JEU (13/11/2026) : la liste des crc32 des os est la table de l'en-tête +0x74 (jusqu'à +0x76 = 4 x nb d'os).
    Avant, on la cherchait à l'aveugle : pour le maillot u000101 elle tombait 2 crans trop tôt -> short sur les os des pieds,
    jambes écartées. On ne garde la recherche que si l'en-tête ne colle pas (autre version du format)."""
    par_crc = {o['crc']: i for i, o in enumerate(os_)}
    try:
        a, b = _table(md, 0x74), _table(md, 0x76)
        if b - a == 4 * nos and b <= len(md):
            return [par_crc.get(c, 0) for c in struct.unpack_from('<%dI' % nos, md, a)]
    except struct.error:
        pass
    meilleur = (0, -1)
    for i in range(0, len(md) - 4 * nos + 1, 4):
        k = sum(struct.unpack_from('<I', md, i + 4 * j)[0] in par_crc for j in range(nos))
        if k > meilleur[0]:
            meilleur = (k, i)
            if k == nos:
                break
    if meilleur[0] < nos // 2:
        return None
    t = meilleur[1]
    return [par_crc.get(struct.unpack_from('<I', md, t + 4 * j)[0], 0) for j in range(nos)]


def _trouver_palette(md, mg, maillages, nos_sq, pos_os, o_poids, o_os, pas):
    L = max([s + c for (_, s, c) in maillages] or [0])
    if not L:
        return None
    meilleur = None
    for p in range(0x80, len(md) - 2 * L + 1, 2):
        pal = struct.unpack_from('<%dH' % L, md, p)
        if max(pal) >= len(nos_sq):
            continue
        pal = [nos_sq[v] for v in pal]
        tot = cnt = 0
        for (vb, nv), s, c in maillages:
            for k in range(0, nv, max(1, nv // 60)):
                o = vb + pas * k
                w = struct.unpack_from('<8H', mg, o + o_poids); ix = mg[o + o_os:o + o_os + 8]
                j = ix[max(range(8), key=lambda q: w[q])]
                if j >= c:
                    tot += 9; cnt += 1; continue
                tot += math.dist(struct.unpack_from('<3f', mg, o), pos_os[pal[s + j]]); cnt += 1
        score = tot / max(cnt, 1)
        if meilleur is None or score < meilleur[0]:
            meilleur = (score, p)
    return meilleur


def lire(md, mg, os_, textures, cache=None, cle=None, alias=None):
    """md, mg : octets du modèle ; os_ : squelette (anim.lire_g4sk) ; textures : noms disponibles.
    -> liste de maillages {nom, texture, pos, uv, os (4 par sommet, n° dans le squelette), poids (4), idx}"""
    n, nmat, nos = struct.unpack_from('<3H', md, 0x20)
    disp = _dispositions(md, n)
    noms = _noms_fin(md, n)
    if len(noms) < n:
        noms = ['maillage_%d' % i for i in range(n)]
    debut_ib = struct.unpack_from('<I', md, 0x5C)[0]
    entrees = []
    for i in range(n):
        e = md[0xA0 + 0x50 * i: 0xA0 + 0x50 * (i + 1)]
        vb, ib, nv, ni = struct.unpack_from('<4I', e, 0)
        d = disp[e[0x42] + 1] if e[0x42] + 1 < len(disp) else []
        entrees.append({'vb': vb, 'ib': debut_ib + ib, 'nv': nv, 'ni': ni, 'pas': e[0x3E], 'pal': (struct.unpack_from('<H', e, 0x3A)[0], e[0x3C]),
                        'mat': e[0x43], 'disp': {t: (o, f) for t, o, f in d}})
    pas = entrees[0]['pas'] if entrees else 68
    d0 = entrees[0]['disp'] if entrees else {}
    o_poids = d0.get(TYPES_POIDS, (36, 32))[0]; o_os = d0.get(TYPE_OS, (52, 24))[0]
    # palette (en cache : la recherche prend ~1 s)
    liste = table_os(md, nos, os_) if nos else None
    if liste is None:
        liste = list(range(len(os_)))
    # palette : LECTURE DU JEU = table de l'en-tête +0x82 (jusqu'à +0x84) ; vérifié sur maillot, peau, chaussures, tête
    p = None
    L0 = max([s + c for s, c in (x['pal'] for x in entrees)] or [0])
    try:
        a, b = _table(md, 0x82), _table(md, 0x84)
        if L0 and b - a >= 2 * L0 and b <= len(md):
            p = a
    except struct.error:
        pass
    if p is None and cache and cle:
        f = os.path.join(cache, 'palettes2.json')
        mem = json.load(open(f, encoding='utf-8')) if os.path.exists(f) else {}
        p = mem.get(cle)
    if p is None and TYPES_POIDS in d0:
        r = _trouver_palette(md, mg, [((x['vb'], x['nv']),) + x['pal'] for x in entrees], liste, _monde_repos(os_), o_poids, o_os, pas)
        p = r[1] if r else -1
        if cache and cle:
            mem[cle] = p
            json.dump(mem, open(f, 'w', encoding='utf-8'), indent=0)
    L = max([s + c for s, c in (x['pal'] for x in entrees)] or [0])
    palette = [liste[v] if v < len(liste) else 0 for v in struct.unpack_from('<%dH' % L, md, p)] if p and p > 0 and L else []
    # textures : même nom que le maillage, sinon celle du matériau
    def base(nom):
        b = re.sub(r'(_LOD\d+|M)$', '', nom)
        if b not in textures and alias:
            for motif, rempl in alias:
                b2 = re.sub(motif, rempl, b)
                if b2 in textures:
                    return b2
        return b
    tex_mat = {}
    for x, nom in zip(entrees, noms):
        if base(nom) in textures:
            tex_mat.setdefault(x['mat'], base(nom))
    out = []
    for i_m, (x, nom) in enumerate(zip(entrees, noms)):
        if '_LOD' in nom or nom.endswith('M') or not x['nv'] or not x['ni']:
            continue                                      # niveaux de détail lointains, ombres
        uvo, uvf = x['disp'].get(TYPE_UV, (None, None))
        no_ = x['disp'].get(TYPE_NORMALE, (None, None))[0]
        pos, uv, jo, po, nor = [], [], [], [], []
        s, c = x['pal']
        for k in range(x['nv']):
            o = x['vb'] + x['pas'] * k
            pos.extend(struct.unpack_from('<3f', mg, o))
            if no_ is not None:
                n3 = [v / 32767 for v in struct.unpack_from('<3h', mg, o + no_)]
                l = math.sqrt(sum(v * v for v in n3)) or 1
                nor.extend(v / l for v in n3)
            else:
                nor.extend((0.0, 1.0, 0.0))
            if uvf == 2:
                uv.extend(struct.unpack_from('<2f', mg, o + uvo))
            elif uvf == 14:
                uv.extend(v / 65535 for v in struct.unpack_from('<2H', mg, o + uvo))
            elif uvf == 18:
                uv.extend(v / 32767 for v in struct.unpack_from('<2h', mg, o + uvo))
            else:
                uv.extend((0.5, 0.5))
            if palette and TYPES_POIDS in x['disp']:
                w = struct.unpack_from('<8H', mg, o + o_poids); ix = mg[o + o_os:o + o_os + 8]
                paires = sorted(((w[q], ix[q]) for q in range(8) if w[q] and ix[q] < c), reverse=True)[:4]
                tot = sum(a for a, _ in paires) or 1
                paires += [(0, 0)] * (4 - len(paires))
                jo.extend(palette[s + j] if a else 0 for a, j in paires)
                po.extend(a / tot for a, _ in paires)
            else:
                jo.extend((0, 0, 0, 0)); po.extend((1, 0, 0, 0))
        idx = list(struct.unpack_from('<%dH' % x['ni'], mg, x['ib']))
        tex = base(nom) if base(nom) in textures else tex_mat.get(x['mat'])
        # _i : n° du maillage dans le G4MD (rendu Direct3D des acteurs : matériau et sommets bruts du jeu)
        out.append({'nom': nom, 'texture': tex, 'pos': pos, 'uv': uv, 'os': jo, 'poids': po, 'idx': idx, 'normales': nor, '_i': i_m})
    return out


def binaire(maillages):
    """en-tête JSON (nom, texture, ombre, contour, nv, ni) + pour chaque maillage : pos f32, normales f32, uv f32, os u16,
    poids f32, indices u16"""
    meta, morceaux = [], []
    for m in maillages:
        nv, ni = len(m['pos']) // 3, len(m['idx'])
        meta.append({'nom': m['nom'], 'texture': m['texture'], 'ombre': m.get('ombre'), 'contour': m.get('contour'), 'nv': nv, 'ni': ni,
                     'noir': bool(m.get('noir')), 'cle': m.get('cle'), 'seau': m.get('seau'),
                     **({'masque': m['masque']} if m.get('masque') else {})})    # (26/11) masque msk (peau du corps, joueurs)
        nor = m.get('normales') or [0.0, 1.0, 0.0] * nv
        morceaux.append(struct.pack('<%df' % (3 * nv), *m['pos']) + struct.pack('<%df' % (3 * nv), *nor) + struct.pack('<%df' % (2 * nv), *m['uv'])
                        + struct.pack('<%dH' % (4 * nv), *m['os']) + struct.pack('<%df' % (4 * nv), *m['poids'])
                        + struct.pack('<%dH' % ni, *m['idx']) + b'\0' * ((-2 * ni) % 4))
    entete = json.dumps(meta).encode()
    entete += b' ' * ((-len(entete)) % 4)
    return struct.pack('<I', len(entete)) + entete + b''.join(morceaux)
