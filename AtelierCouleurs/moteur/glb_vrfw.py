"""(17/11/2026) MODÈLES .glb DES MODS (VRFW.model/1 avec `glb`) convertis au format du jeu, comme VRFW le fait en mémoire
au lancement du jeu (rien n'est écrit sur le disque par VRFW : Michael astral k002093, le dôme vert de Spectre chrono…).
Demande de muku : « lis les .glb ». Les fichiers convertis vont dans cache/glb_vrfw/<mod>/… et la racine superposée du mod
(moteur/racines.py) les montre à leur place du jeu : l'aperçu, le rendu Direct3D et le lecteur natif les lisent sans
changement. Rien n'est modifié dans les mods ni dans le jeu.

Déclaration (LU dans les mods) : content/models/<type>/<nom>/<nom>.toml
  kind = "character" | "effect" | "head"…, target = « chr/_keshin/k002093/k002093.g4pkm » (chemin du jeu sans common/),
  template = paquet du jeu pris comme modèle, glb = fichier (à côté du .toml ou dans assets/models/<type>/<nom>/),
  [skeleton] mode = "template", [[material]] name (matériau du .glb) / from (matériau du gabarit) / textures,
  [[texture]] name (PNG dans <dossier du .glb>/textures/<name>.png), [textures] container = « dx11/….g4tx ».
Conversion (DÉDUIT, VRFW ne publie pas son code) :
  - chaque maillage du .glb remplace la pièce du gabarit de même nom (sinon celle dont le matériau est `from`) ; les pièces
    du gabarit sans maillage du .glb sont vidées ;
  - sommets écrits dans la disposition de la pièce du gabarit (types : 1 position, 2 normale, 13 normale de contour,
    3 tangente, 5 poids, 6 os, 8 couleur, 10-15 UV) ; couleur de sommet = COLOR_0 du .glb s'il en a (MESURÉ 25/11 contre le cache de VRFW), sinon la plus fréquente du gabarit (masque de contour :
    voir « Shader des armures - code du jeu ») ;
  - os : noms des articulations du .glb = os du gabarit ; palette « tous les os » réécrite dans la table +0x82 quand elle a
    assez de cases, sinon la palette de la pièce (os absent -> son parent) ;
  - textures : images RGBA non compressées, rangées sous les noms des cases du matériau du gabarit.
"""
import os, re, glob, json, struct, zlib, hashlib, collections
import numpy as np

try:
    import tomllib
except ImportError:
    tomllib = None

from .vrfw_anim import lire_glb, _acces


def trouver(cfg, seul=None):
    """[{mod, toml, def, glb, textures}] de tous les mods (activés ou non), ou du seul mod « seul »"""
    mods_dir = os.path.join(cfg.get('jeu_dir') or '', 'mods')
    out = []
    if not os.path.isdir(mods_dir):
        return out
    for mod in ([seul] if seul else sorted(os.listdir(mods_dir), key=str.lower)):
        for f in glob.glob(os.path.join(mods_dir, mod, 'content', 'models', '**', '*.toml'), recursive=True):
            try:
                t = tomllib.load(open(f, 'rb'))
            except Exception:
                continue
            if not isinstance(t.get('glb'), str) or not isinstance(t.get('target'), str) or not isinstance(t.get('template'), str):
                continue
            rel = os.path.relpath(os.path.dirname(f), os.path.join(mods_dir, mod, 'content'))
            cands = [os.path.join(os.path.dirname(f), t['glb']), os.path.join(mods_dir, mod, 'assets', rel, t['glb'])]
            g = next((c for c in cands if os.path.exists(c)), None)
            if g:
                out.append({'mod': mod, 'toml': f, 'def': t, 'glb': g, 'textures': os.path.join(os.path.dirname(g), 'textures')})
    return out


def _png_rgba(f):
    from .g4 import images
    w, h, rows = images.lire_png(f)
    a = np.frombuffer(b''.join(bytes(r) for r in rows), np.uint8)
    a = a.reshape(h, w, -1)
    if a.shape[2] == 3:
        a = np.concatenate([a, np.full((h, w, 1), 255, np.uint8)], 2)
    return w, h, a[:, :, :4]


def _dds_rgba(w, h, a):
    """DDS non compressé RGBA 8 bits (masques R 0xff, G 0xff00, B 0xff0000, A 0xff000000 : lu par g4.decoder_texture)"""
    hd = bytearray(128)
    hd[0:4] = b'DDS '
    struct.pack_into('<7I', hd, 4, 124, 0x100F, h, w, w * 4, 0, 1)
    struct.pack_into('<2I4s5I', hd, 76, 32, 0x41, b'\0\0\0\0', 32, 0xFF, 0xFF00, 0xFF0000, 0xFF000000)
    struct.pack_into('<I', hd, 108, 0x1000)
    return bytes(hd) + np.ascontiguousarray(a, np.uint8).tobytes()


def _table(md, o):
    base = struct.unpack_from('<H', md, 0x0A)[0] * 4
    return base + struct.unpack_from('<H', md, o)[0] * 4


def _ecrire_attr(buf, off, fmt, v):
    if fmt == 3:
        struct.pack_into('<3f', buf, off, *v[:3])
    elif fmt == 2:
        struct.pack_into('<2f', buf, off, *v[:2])
    elif fmt == 20:     # (25/11) arrondi (MESURÉ : VRFW arrondit, l'ancienne écriture tronquait d'une unité)
        struct.pack_into('<4h', buf, off, *[int(round(max(-1, min(1, x)) * 32767)) for x in (list(v) + [0, 0, 0, 0])[:4]])
    elif fmt == 14:
        struct.pack_into('<2H', buf, off, *[int(max(0, min(1, x)) * 65535 + 0.5) for x in v[:2]])
    elif fmt == 18:
        struct.pack_into('<2h', buf, off, *[int(max(-1, min(1, x)) * 32767) for x in v[:2]])
    elif fmt == 12:
        buf[off:off + 4] = bytes(v[:4])
    elif fmt == 32:
        struct.pack_into('<8H', buf, off, *v[:8])
    elif fmt == 24:
        buf[off:off + 8] = bytes(v[:8])


def _tangentes(P, N, U, I):
    T = np.zeros_like(P)
    tri = I.reshape(-1, 3)
    p0, p1, p2 = P[tri[:, 0]], P[tri[:, 1]], P[tri[:, 2]]
    u0, u1, u2 = U[tri[:, 0]], U[tri[:, 1]], U[tri[:, 2]]
    e1, e2 = p1 - p0, p2 - p0
    d1, d2 = u1 - u0, u2 - u0
    r = d1[:, 0] * d2[:, 1] - d2[:, 0] * d1[:, 1]
    r = np.where(np.abs(r) < 1e-12, 1e-12, r)
    t = (e1 * d2[:, 1:2] - e2 * d1[:, 1:2]) / r[:, None]
    for c in range(3):
        np.add.at(T, tri[:, c], t)
    T = T - N * (T * N).sum(1, keepdims=True)
    l = np.linalg.norm(T, axis=1, keepdims=True)
    return np.where(l > 1e-9, T / np.maximum(l, 1e-9), np.array([1.0, 0, 0]))


def _sens_bitangente(P, N, U, I, T):
    """(25/11) 4e composante de la tangente = sens de la bitangente (+1 / −1) ; MESURÉ dans le cache de VRFW (tiger_fang) :
    mêmes x y z que _tangentes, w = ±1 (avant : toujours 1)"""
    B = np.zeros_like(P)
    tri = I.reshape(-1, 3)
    p0, p1, p2 = P[tri[:, 0]], P[tri[:, 1]], P[tri[:, 2]]
    u0, u1, u2 = U[tri[:, 0]], U[tri[:, 1]], U[tri[:, 2]]
    e1, e2 = p1 - p0, p2 - p0
    d1, d2 = u1 - u0, u2 - u0
    r = d1[:, 0] * d2[:, 1] - d2[:, 0] * d1[:, 1]
    r = np.where(np.abs(r) < 1e-12, 1e-12, r)
    b = (e2 * d1[:, 0:1] - e1 * d2[:, 0:1]) / r[:, None]
    for c in range(3):
        np.add.at(B, tri[:, c], b)
    return np.where((np.cross(N, T) * B).sum(1) < 0, 1.0, -1.0)


def convertir(cfg, cache_dir, m):
    """convertit un modèle .glb -> {(« common » | « dx11 », chemin relatif du jeu) : fichier converti} (gardé en cache)"""
    from . import g4, anim
    from .g4 import images
    D = cfg['data_dir']
    t = m['def']
    sig = hashlib.md5(json.dumps([os.path.getmtime(m['glb']), os.path.getmtime(m['toml'])] +
                                 sorted((f, os.path.getmtime(f)) for f in glob.glob(os.path.join(m['textures'], '*.png'))),
                                 default=str).encode() + b'v7').hexdigest()[:10]   # v7 (25/11) : couleurs de sommet, normales, tangentes
    cible = t['target'].replace('\\', '/').lstrip('/')
    cible = cible[len('common/'):] if cible.startswith('common/') else cible
    tpl = t['template'].replace('\\', '/').lstrip('/')
    tpl = tpl[len('common/'):] if tpl.startswith('common/') else tpl
    sortie = os.path.join(cache_dir, 'glb_vrfw', m['mod'], '%s_%s' % (os.path.basename(cible)[:-6], sig))
    cont = ((t.get('textures') or {}).get('container') or ('dx11/' + cible[:-6] + '.g4tx')).replace('\\', '/')
    cont = cont[len('dx11/'):] if cont.startswith('dx11/') else cont
    fichiers = {('common', cible): os.path.join(sortie, 'common', *cible.split('/')),
                ('common', cible[:-6] + '.g4mg'): os.path.join(sortie, 'common', *(cible[:-6] + '.g4mg').split('/')),
                ('dx11', cont): os.path.join(sortie, 'dx11', *cont.split('/'))}
    # .objbin : celui du gabarit (l'Atelier repère un objet d'effet par ce fichier ; le mod n'en a pas pour un effet)
    obj_tpl = os.path.join(D, 'common', *(tpl[:-6] + '.objbin').split('/'))
    if os.path.exists(obj_tpl):
        fichiers[('common', cible[:-6] + '.objbin')] = os.path.join(sortie, 'common', *(cible[:-6] + '.objbin').split('/'))
    if all(os.path.exists(f) for f in fichiers.values()):
        return fichiers
    # ------------------------------------------------------------------ gabarit
    pk = open(os.path.join(D, 'common', *tpl.split('/')), 'rb').read()
    a_md = pk.find(b'G4MD')
    md = bytearray(pk[a_md:])
    ob = g4.ObjetEffet(D, 'common/' + tpl[:-6] + '.objbin')
    import sys as _s
    _s.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'AtelierD3D'))
    import acteurs
    ents = acteurs.maillages_md(bytes(md))
    mg_tpl = open(os.path.join(D, 'common', *(tpl[:-6] + '.g4mg').split('/')), 'rb').read()
    n_m, _, nos = struct.unpack_from('<3H', md, 0x20)
    crc_os = list(struct.unpack_from('<%dI' % nos, md, _table(md, 0x74)))
    idx_os = {c: i for i, c in enumerate(crc_os)}
    sk = anim.lire_g4sk(pk) or []
    parent_crc = {}
    for o in sk:
        if o.get('parent', -1) >= 0:
            parent_crc[o['crc'] & 0xFFFFFFFF] = sk[o['parent']]['crc'] & 0xFFFFFFFF
    noms_pieces = [p['nom'] for p in ob.pieces]
    mat_de = {m_['nom']: k for k, m_ in enumerate(ob.materiaux)}
    defs_mat = {x.get('name'): x for x in t.get('material') or [] if isinstance(x, dict)}
    # ------------------------------------------------------------------ .glb
    j, binaire = lire_glb(m['glb'])
    meshes = []
    for nd in j.get('nodes', []):
        if 'mesh' not in nd:
            continue
        me = j['meshes'][nd['mesh']]
        sk_j = [j['nodes'][i].get('name', '') for i in j['skins'][nd['skin']]['joints']] if 'skin' in nd and j.get('skins') else None
        for p in me['primitives']:
            mat = j['materials'][p['material']].get('name') if 'material' in p and j.get('materials') else None
            meshes.append((me.get('name') or nd.get('name'), mat, p, sk_j))
    # quelle pièce du gabarit chaque maillage remplace
    pris = {}
    for nom, mat, p, skj in meshes:
        k = noms_pieces.index(nom) if nom in noms_pieces else None
        if k is None and mat in defs_mat and defs_mat[mat].get('from') in mat_de:
            k = next((i for i, e in enumerate(ents) if e['mat'] == mat_de[defs_mat[mat]['from']]), None)
        if k is None and len(ents) == 1:
            k = 0
        if k is not None:
            pris.setdefault(k, []).append((nom, mat, p, skj))
    if not pris:
        raise ValueError('aucun maillage du .glb ne correspond au gabarit')
    # palette « tous les os » si la table +0x82 a assez de cases
    t82 = _table(md, 0x82)
    cases = max((struct.unpack_from('<H', md, 0xA0 + 0x50 * i + 0x3A)[0] + md[0xA0 + 0x50 * i + 0x3C] for i in range(n_m)), default=0)
    pal_tout = cases >= nos and nos <= 255
    if pal_tout:
        struct.pack_into('<%dH' % nos, md, t82, *range(nos))
    mg = bytearray()
    ibs = []
    for i, e in enumerate(ents):
        eo = 0xA0 + 0x50 * i
        if i not in pris:
            struct.pack_into('<4I', md, eo, 0, 0, 0, 0)
            struct.pack_into('<I', md, eo + 0x30, 0)
            continue
        pas, disp = e['pas'], e['disp']
        # palette de la pièce (n° d'os du modèle)
        if pal_tout:
            struct.pack_into('<H', md, eo + 0x3A, 0); md[eo + 0x3C] = nos
            palette = list(range(nos))
        else:
            s0 = struct.unpack_from('<H', md, eo + 0x3A)[0]; c0 = md[eo + 0x3C]
            palette = list(struct.unpack_from('<%dH' % c0, md, t82 + 2 * s0)) if c0 else [0]
        pos_pal = {b: k for k, b in enumerate(palette)}

        def place(nom_os):
            c = zlib.crc32(nom_os.encode())
            for _ in range(64):
                b = idx_os.get(c)
                if b is not None and b in pos_pal:
                    return pos_pal[b]
                c = parent_crc.get(c)
                if c is None:
                    break
            return 0
        # sommets du gabarit pour les valeurs par défaut (couleur la plus fréquente, octets inconnus)
        v0 = bytes(mg_tpl[e['vb']:e['vb'] + pas]) if e['nv'] else bytes(pas)
        col = None
        if 8 in disp:
            # (25/11) MESURÉ dans le cache de VRFW (Michael astral k002093, dôme ev61873190 : .glb sans COLOR_0) : VRFW écrit
            # [255, 153, 191, 127] sur tous les sommets, pas la couleur la plus fréquente du gabarit (k002010 : 255, 102, 191, 127)
            col = bytes([255, 153, 191, 127])
        P_, N_, U_, I_, J_, W_, C_ = [], [], [], [], [], [], []
        for nom, mat, p, skj in pris[i]:
            at = p['attributes']
            P = _acces(j, binaire, at['POSITION'])[:, :3]
            # (25/11) COULEUR DE SOMMET du .glb (COLOR_0 : masque de contour, ex. tiger_fang [0, 0,30, 0, 0,5]) : MESURÉ dans
            # le cache de VRFW (ev63_86020), VRFW l'écrit telle quelle (0..1 -> 0..255) ; sans COLOR_0 : 255, 153, 191, 127 (plus bas)
            if 'COLOR_0' in at:
                c_ = _acces(j, binaire, at['COLOR_0'])
                c_ = np.concatenate([c_[:, :4], np.ones((len(c_), max(0, 4 - c_.shape[1])))], 1) if c_.shape[1] < 4 else c_[:, :4]
                C_.append(np.clip(np.round(c_ * 255), 0, 255).astype(int))
            else:
                C_.append(None)
            N = _acces(j, binaire, at['NORMAL'])[:, :3] if 'NORMAL' in at else np.tile([0, 1, 0], (len(P), 1)).astype(float)
            U = _acces(j, binaire, at['TEXCOORD_0'])[:, :2] if 'TEXCOORD_0' in at else np.zeros((len(P), 2))
            I = _acces(j, binaire, p['indices'])[:, 0].astype(np.int64) if 'indices' in p else np.arange(len(P))
            if 'JOINTS_0' in at and skj:
                Jt = _acces(j, binaire, at['JOINTS_0']).astype(int)
                Wt = _acces(j, binaire, at['WEIGHTS_0']) if 'WEIGHTS_0' in at else np.tile([1, 0, 0, 0], (len(P), 1)).astype(float)
                pl = np.array([place(n) for n in skj])
                J_.append(pl[Jt]); W_.append(Wt)
            else:
                J_.append(np.zeros((len(P), 4), int)); W_.append(np.tile([1.0, 0, 0, 0], (len(P), 1)))
            I_.append(I + sum(len(x) for x in P_))
            P_.append(P); N_.append(N); U_.append(U)
        P, N, U = np.concatenate(P_), np.concatenate(N_), np.concatenate(U_)
        I, J, W = np.concatenate(I_), np.concatenate(J_), np.concatenate(W_)
        C = None
        if any(c_ is not None for c_ in C_):
            defaut = np.array(list(col) if col is not None else [255, 255, 255, 255], int)
            C = np.concatenate([c_ if c_ is not None else np.tile(defaut, (len(p_), 1)) for c_, p_ in zip(C_, P_)])
        if len(P) >= 65535:
            raise ValueError('trop de sommets (%d)' % len(P))
        N = N / np.maximum(np.linalg.norm(N, axis=1, keepdims=True), 1e-9)
        T = _tangentes(P, N, U, I)
        TW = _sens_bitangente(P, N, U, I, T)
        # (25/11) normale de contour = moyenne des normales des sommets à la MÊME position exacte (MESURÉ dans le cache de
        # VRFW : 23692 / 23692 pour Michael astral, 2034 / 2034 pour tiger_fang ; avant : positions arrondies à 4 décimales,
        # deux points voisins fusionnés)
        cles = [tuple(np.round(p, 6)) for p in P]
        somme = {}
        for c, n in zip(cles, N):
            somme[c] = somme.get(c, 0) + n
        NC = np.array([somme[c] / (np.linalg.norm(somme[c]) or 1) for c in cles])
        vb = bytearray(v0 * len(P))
        for k in range(len(P)):
            o = k * pas
            ws = W[k] / (W[k].sum() or 1)
            wq = [int(round(x * 65535)) for x in ws]
            wq[int(np.argmax(wq))] += 65535 - sum(wq)
            for typ, (off, fmt) in disp.items():
                if typ == 1:
                    _ecrire_attr(vb, o + off, fmt, P[k])
                elif typ == 2:          # (25/11) 4e composante 1 (MESURÉ dans le cache de VRFW ; avant : 0)
                    _ecrire_attr(vb, o + off, fmt, list(N[k]) + [1])
                elif typ == 13:
                    _ecrire_attr(vb, o + off, fmt, list(NC[k]) + [1])
                elif typ == 3:
                    _ecrire_attr(vb, o + off, fmt, list(T[k]) + [TW[k]])
                elif typ == 5:
                    _ecrire_attr(vb, o + off, fmt, wq + [0, 0, 0, 0])
                elif typ == 6:
                    _ecrire_attr(vb, o + off, fmt, [int(x) for x in J[k]] + [0, 0, 0, 0])
                elif typ == 8 and C is not None:
                    _ecrire_attr(vb, o + off, fmt, [int(x) for x in C[k]])
                elif typ == 8 and col is not None:
                    _ecrire_attr(vb, o + off, fmt, list(col))
                elif 10 <= typ <= 15:
                    _ecrire_attr(vb, o + off, fmt, U[k])
        # zone des sommets puis zone des indices (LU, gabarits k002010 / ev60100902) : en-tête +0x50 = taille des sommets,
        # +0x54 = taille des indices, +0x5C = début des indices ; « ib » d'une pièce = position DANS la zone des indices
        vb_off = len(mg); mg += vb
        ibs.append((eo, struct.pack('<%dH' % len(I), *I.tolist())))
        struct.pack_into('<4I', md, eo, vb_off, 0, len(P), len(I))
        struct.pack_into('<I', md, eo + 0x30, len(I) // 3)
        lo, hi = P.min(0), P.max(0)
        struct.pack_into('<4f', md, eo + 0x10, *(((lo + hi) / 2).tolist() + [1.0]))
        struct.pack_into('<4f', md, eo + 0x20, *(((hi - lo) / 2).tolist() + [0.0]))
    taille_vb = len(mg)
    while len(mg) % 64:
        mg += b'\0'
    debut_ib = len(mg)
    for eo, ib in ibs:
        struct.pack_into('<I', md, eo + 4, len(mg) - debut_ib)
        mg += ib
        while len(mg) % 4:
            mg += b'\0'
    struct.pack_into('<2I', md, 0x50, taille_vb, len(mg) - debut_ib)
    struct.pack_into('<I', md, 0x5C, debut_ib)
    # ------------------------------------------------------------------ textures (cases des matériaux du gabarit)
    g = images.G4TX(open(os.path.join(D, 'dx11', *(tpl[:-6] + '.g4tx').split('/')), 'rb').read())
    rempl = {}
    crcs_tex = [struct.unpack_from('<I', md, _table(md, 0x76) + 4 * k)[0] for k in range(md[0x27])]
    nom_crc = {zlib.crc32(n.encode()): n for n in g.noms}
    for x in t.get('material') or []:
        if not isinstance(x, dict) or x.get('from') not in mat_de:
            continue
        cas = ob.materiaux[mat_de[x['from']]].get('textures') or []
        for c, nouveau in enumerate(x.get('textures') or []):
            if c < len(cas) and cas[c] in g.noms:
                png = os.path.join(m['textures'], nouveau + '.png')
                if os.path.exists(png) and cas[c] not in rempl:
                    rempl[cas[c]] = _dds_rgba(*_png_rgba(png))
    _ = crcs_tex, nom_crc
    tx = g.reconstruire(rempl) if rempl else g.b
    for (cote, rel), f in fichiers.items():
        os.makedirs(os.path.dirname(f), exist_ok=True)
    open(fichiers[('common', cible)], 'wb').write(pk[:a_md] + bytes(md))
    open(fichiers[('common', cible[:-6] + '.g4mg')], 'wb').write(bytes(mg))
    open(fichiers[('dx11', cont)], 'wb').write(tx)
    if ('common', cible[:-6] + '.objbin') in fichiers:
        open(fichiers[('common', cible[:-6] + '.objbin')], 'wb').write(open(obj_tpl, 'rb').read())
    json.dump({'mod': m['mod'], 'glb': m['glb'], 'pieces': {noms_pieces[k]: [x[0] for x in v] for k, v in pris.items()},
               'palette_tout': pal_tout, 'textures': sorted(rempl)}, open(os.path.join(sortie, 'conversion.json'), 'w'), ensure_ascii=False)
    return fichiers


def fichiers_du_mod(cfg, cache_dir, mod):
    """tous les fichiers convertis des .glb du mod : {(côté, chemin du jeu) : fichier} (conversion faite au besoin)"""
    out = {}
    for m in trouver(cfg, mod):
        try:
            out.update(convertir(cfg, cache_dir, m))
        except Exception as ex:
            print('glb', m['glb'], ex)
    return out
