"""(15/11/2026) COPIE D'UNE TENUE : un NOUVEAU JOUEUR (copie d'un personnage qui porte cette tenue) qui porte la tenue
recolorée. La tenue du jeu et le personnage d'origine ne changent pas. Mod MesPersonnages (avec les copies de têtes).

Lu (LU) dans le jeu et dans les mods qui marchent :
- chara_parts : CHARA_PARTS_CLOTHES_MODEL (nom) + _REF_INFO (début, nombre de lignes) -> CHARA_PARTS_CLOTHES_INFO ;
  idem SHOES et GLOVE (modèles en crc32 seulement : nom = nom de la texture de la 1re ligne, vérifié par crc32) ;
- ligne de vêtement : colonne 1 = upper_texture, 4 = lower_texture, 9 = sleeve_texture (MesMaillots et ChronicleDeluxe
  écrivent ces clés ; leurs chemins sont dans ces colonnes) ; chaussures / gants : colonne 1 = texture (clé « texture ») ;
- chara_model : colonne 5 = vêtement, 6 = chaussures, 7 = gants (crc32 du nom du modèle) ;
- look VRFW.look/2 : [[clothes]] model / from / rows, [[shoes]] et [[gloves]] id / from / rows (ChronicleDeluxe) ;
- personnage : new_model.cells clothes / shoes / gloves = crc32(modèle) et force_kit = 1 (Inazuma Fantasy, Michael,
  ChronicleDeluxe) : le joueur porte ses propres habits au lieu du maillot de l'équipe.
"""
from moteur import langue as _langue  # noqa: E402  (FR / EN)
import os, glob, zlib, json, datetime, struct, shutil, tempfile, multiprocessing
from . import cfgbin, retouches, copies_persos as CP
from .g4 import images
from .personnages import _japonais, _dernier
from .esprits import slug, _png
from .maillots.cfgbin import parse

GENRES = {'clothes': ('CLOTHES', 5, 'tz'), 'shoes': ('SHOES', 6, 'sz'), 'gloves': ('GLOVE', 7, 'gz')}
CLES_VET = {1: 'upper_texture', 4: 'lower_texture', 9: 'sleeve_texture'}
_cache = {}


def _parties(data_dir):
    """{genre: {nom du modèle: [lignes]}} (noms sûrs seulement)"""
    if 'parties' in _cache:
        return _cache['parties']
    parts = sorted(glob.glob(os.path.join(data_dir, 'common', 'gamedata', 'character', 'chara_parts_*.cfg.bin')))[-1]
    infos = {g: [] for g in GENRES}; mods = {g: [] for g in GENRES}; cur = None
    nomg = {v[0]: k for k, v in GENRES.items()}
    for k, v in parse(parts):
        for G, g in nomg.items():
            if k == 'CHARA_PARTS_%s_INFO' % G:
                infos[g].append(v)
            elif k == 'CHARA_PARTS_%s_MODEL' % G:
                cur = (g, v)
            elif k == 'CHARA_PARTS_%s_MODEL_REF_INFO' % G and cur and cur[0] == g:
                mods[g].append((cur[1], v[0], v[1])); cur = None
    out = {}
    for g in GENRES:
        out[g] = {}
        for m, d, n in mods[g]:
            lignes = infos[g][d:d + n]
            nom = next((x for x in m if isinstance(x, str)), None)
            if not nom:                                # chaussures / gants : nom = texture de la 1re ligne, si le crc32 concorde
                crc = next((x & 0xFFFFFFFF for x in m if isinstance(x, int)), None)
                tx = lignes[0][1] if lignes and len(lignes[0]) > 1 and isinstance(lignes[0][1], str) else None
                if tx and crc == zlib.crc32(os.path.basename(tx)[:-5].encode()):
                    nom = os.path.basename(tx)[:-5]
            if nom:
                out[g][nom] = lignes
    _cache['parties'] = out
    return out


def porteurs(cfg, entree, limite=60):
    """qui porte cette tenue : [{code, nom, genre, modele}] (modèles du jeu dont une ligne utilise SA texture)"""
    rel = retouches.fichier_texture(cfg, entree)
    if not rel:
        return [], None
    chemin = rel[len('chr/'):] if rel.startswith('chr/') else rel        # « _uniform/<dossier>/<fichier>.g4tx »
    P = _parties(cfg['data_dir'])
    cols = {'clothes': (1, 4, 7, 9), 'shoes': (1,), 'gloves': (1,)}
    modeles = {}
    for g, ms in P.items():
        for nom, lignes in ms.items():
            if any(len(r) > i and r[i] == chemin for r in lignes for i in cols[g]):
                modeles[zlib.crc32(nom.encode())] = (g, nom)
    if not modeles:
        return [], chemin
    c = os.path.join(cfg['data_dir'], 'common')
    par_modele = {}
    for f in sorted(glob.glob(os.path.join(c, 'gamedata', 'character', 'chara_model_1*.cfg.bin'))):
        for k, v in cfgbin.lire(open(f, 'rb').read()):
            if not v or not isinstance(v[0], int):
                continue
            for g, (G, col, p) in GENRES.items():
                if len(v) > col and isinstance(v[col], int) and (v[col] & 0xFFFFFFFF) in modeles and modeles[v[col] & 0xFFFFFFFF][0] == g:
                    par_modele.setdefault(v[0] & 0xFFFFFFFF, modeles[v[col] & 0xFFFFFFFF])
    noms = {}
    for k, v in cfgbin.lire(open(os.path.join(c, 'text', _langue.code(), 'chara_text.cfg.bin'), 'rb').read()):
        if len(v) > 5 and isinstance(v[0], int) and v[1] == 0 and isinstance(v[5], str):
            noms.setdefault(v[0] & 0xFFFFFFFF, v[5])
    avec_carte = {v[1] & 0xFFFFFFFF for k, v in cfgbin.lire(open(_dernier(os.path.join(c, 'gamedata', 'character', 'chara_param_1*.cfg.bin')), 'rb').read())
                  if len(v) > 1 and isinstance(v[1], int)}               # seulement des JOUEURS (une carte à copier)
    out, vus = [], set()
    for k, v in cfgbin.lire(open(_dernier(os.path.join(c, 'gamedata', 'character', 'chara_base_*.cfg.bin')), 'rb').read()):
        if len(v) > 6 and isinstance(v[1], str) and isinstance(v[6], int) and (v[6] & 0xFFFFFFFF) in par_modele and v[1] not in vus \
                and zlib.crc32(v[1].encode()) in avec_carte and len(v[1]) == 9 and v[1][0] == 'c' and v[1][1:].isdigit():
            n = noms.get(v[3] & 0xFFFFFFFF) if isinstance(v[3], int) else None
            if not n or _japonais(n):
                continue
            vus.add(v[1]); g, m = par_modele[v[6] & 0xFFFFFFFF]
            out.append({'code': v[1], 'nom': n, 'genre': g, 'modele': m})
            if len(out) >= limite:
                break
    return out, chemin


def _nom_libre(cfg, prefixe, reg):
    pris = {x.get('vetement', {}).get('modele') for x in reg.values()}
    P = _parties(cfg['data_dir'])
    tous = set().union(*[set(m) for m in P.values()])
    mods = os.path.join(cfg['jeu_dir'], 'mods')
    for n in range(1, 100000):
        m = '%s%06d' % (prefixe, n)
        if m not in pris and m not in tous and not glob.glob(os.path.join(mods, '*', 'assets', 'chr', '_uniform', m)):
            return m
    raise ValueError('plus de nom libre')


def exporter(cfg, demande, entree):
    """demande = {code (dossier de la tenue), porteur (code du personnage), nom, description, textures {nom: data URL}}"""
    nom = str(demande.get('nom') or '').strip()
    if not nom:
        return {'ok': False, 'erreur': 'Donne un nom au nouveau joueur.'}
    textures = demande.get('textures') or {}
    if not textures:
        return {'ok': False, 'erreur': 'Rien n’est modifié : recolore d’abord la tenue.'}
    liste, chemin = porteurs(cfg, entree, limite=100000)
    p = next((x for x in liste if x['code'] == demande.get('porteur')), None)
    if not p:
        return {'ok': False, 'erreur': 'Choisis qui portera la tenue (un personnage qui la porte déjà dans le jeu).'}
    D = cfg['data_dir']
    orig = CP.personnage_de_tete  # (non utilisé : la tête reste celle du porteur)
    reg = CP.registre(cfg); cle = CP.cle_creation(reg, demande, slug(nom), nom, lambda x: x.get('genre') == 'tenue' and x.get('base') == p['code'])   # (28/11) Modifier : LA création ; slug pris -> neuf
    e = reg.get(cle) or {}
    if e and (e.get('genre') != 'tenue' or e.get('base') != p['code']):
        return {'ok': False, 'erreur': 'Le nom « %s » est déjà pris par une autre copie : choisis-en un autre.' % nom}
    g = p['genre']; G, col, prefixe = GENRES[g]
    carte = _carte(D, p['code'])
    if carte is None:
        return {'ok': False, 'erreur': '%s n’a pas de carte de joueur à copier.' % p['nom']}
    if not e:
        pris = CP._ids_pris(cfg)
        neuf = CP._code_libre(cfg, p['code'], reg) if len(p['code']) == 9 and p['code'][0] == 'c' else None
        if not neuf:
            return {'ok': False, 'erreur': 'code de personnage inattendu : %s' % p['code']}
        modele = _nom_libre(cfg, prefixe, reg)
        e = {'genre': 'tenue', 'code': neuf, 'base': p['code'], 'carte_origine': carte, 'id': zlib.crc32(neuf.encode()),
             'modele': CP._id(CP.MOD_ID + '.' + cle + '.modele', pris), 'carte': CP._id(CP.MOD_ID + '.' + cle + '.carte', pris),
             'nom_txt': CP._id(CP.MOD_ID + '.' + cle + '.nom', pris), 'court_txt': CP._id(CP.MOD_ID + '.' + cle + '.court', pris),
             'desc_txt': CP._id(CP.MOD_ID + '.' + cle + '.description', pris), 'vetement': {'type': g, 'modele': modele}}
        if e['id'] in pris:
            return {'ok': False, 'erreur': 'crc32(%s) déjà utilisé : réessaie' % neuf}
    m = e['vetement']['modele']
    nouveau = '_uniform/%s/%s_10.g4tx' % (m, m)
    lignes = _parties(D)[g][p['modele']]
    rows, ignore = [], 0
    for r in lignes:
        o = {}
        if g == 'clothes':
            for i, k in CLES_VET.items():
                if len(r) > i and r[i] == chemin:
                    o[k] = nouveau
            if len(r) > 7 and r[7] == chemin:
                ignore += 1
        elif len(r) > 1 and r[1] == chemin:
            o['texture'] = nouveau
        rows.append(o)
    if not any(rows):
        return {'ok': False, 'erreur': 'cette texture n’est pas dans une colonne connue du vêtement %s' % p['modele']}
    e['vetement'].update(type=g, source=p['modele'], rows=rows, texture=chemin)
    e.update(nom=nom, description=str(demande.get('description') or ''), nom_origine=p['nom'], date=datetime.datetime.now().isoformat(timespec='seconds'),
             source_jeu=entree['code'])   # (28/11) la tenue / l'accessoire recoloré : « Modifier » rouvre CELUI-LÀ (onglet Tenues)
    # texture : mêmes noms d'images (les maillages du jeu sont gardés), posée au nouveau chemin
    src = os.path.join(D, 'dx11', 'chr', *chemin.split('/'))
    gt = images.G4TX(open(src, 'rb').read())
    rempl, rapport, tmp = {}, [], tempfile.mkdtemp()
    try:
        with images.pool_encodage() as pool:
            for n_, url in textures.items():
                if n_ not in gt.noms:
                    return {'ok': False, 'erreur': '%s n’est pas dans %s' % (n_, chemin)}
                bloc = gt.blocs[gt.noms.index(n_)]
                h0, w0 = struct.unpack_from('<II', bloc, 12)
                w, h, rows_ = _png(url, tmp)
                if (w, h) != (w0, h0):
                    return {'ok': False, 'erreur': '%s : %dx%d au lieu de %dx%d' % (n_, w, h, w0, h0)}
                if bloc[84:88] == b'DX10' and struct.unpack_from('<I', bloc, 128)[0] == 98:
                    rempl[n_] = images.dds_bc7(w, h, rows_, bloc[:148], images.mips_dds(bloc), pool)
                elif bloc[84:88] == b'DXT1':
                    rempl[n_] = images.dds_bc1(w, h, rows_, pool, mips=images.mips_dds(bloc))
                else:
                    return {'ok': False, 'erreur': '%s : format pas encore pris en charge' % n_}
                rapport.append('%s (%dx%d)' % (n_, w, h))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    sortie = CP._sortie(cfg)
    d = os.path.join(sortie, 'assets', 'chr', '_uniform', m); os.makedirs(d, exist_ok=True)
    open(os.path.join(d, m + '_10.g4tx'), 'wb').write(gt.reconstruire(rempl))
    # portrait : celui du porteur, au code neuf
    pp = os.path.join(D, 'dx11', 'menu', '200_icon', '10_icon_chr', 'face', p['code'] + '_l.g4tx')
    if os.path.exists(pp):
        dd = os.path.join(sortie, 'assets', 'menu', '200_icon', '10_icon_chr', 'face'); os.makedirs(dd, exist_ok=True)
        open(os.path.join(dd, e['code'] + '_l.g4tx'), 'wb').write(CP.bustes.renommer(open(pp, 'rb').read(), p['code'], e['code']))
    reg[cle] = e
    CP._sauver(cfg, reg); CP._ecrire_contenu(cfg, reg)
    rapport.insert(0, '%s : copie de %s (%s) qui porte la tenue recolorée (%s %s, copie de %s), code %s'
                   % (nom, p['nom'], p['code'], {'clothes': 'vêtement', 'shoes': 'chaussures', 'gloves': 'gants'}[g], m, p['modele'], e['code']))
    if ignore:
        rapport.append('ATTENTION : %d ligne(s) où la texture est en colonne 7 (nom de clé pas encore lu) : gardées comme dans le jeu' % ignore)
    return {'ok': True, 'dossier': sortie, 'code': e['code'], 'rapport': rapport}


def _carte(data_dir, code):
    crc = zlib.crc32(code.encode())
    c = os.path.join(data_dir, 'common')
    for k, v in cfgbin.lire(open(_dernier(os.path.join(c, 'gamedata', 'character', 'chara_param_1*.cfg.bin')), 'rb').read()):
        if len(v) > 1 and isinstance(v[1], int) and (v[1] & 0xFFFFFFFF) == crc and isinstance(v[0], int):
            return v[0] & 0xFFFFFFFF
    return None


# ---------------------------------------------------------------------------------------------------- (15/11/2026) OBJETS
# Un objet du jeu (chr/_item) porté comme ACCESSOIRE (chara_parts EXMESH, LU : 50 modèles, lignes [g4md, g4tx, 0]) :
# copie = un nouveau joueur (copie du personnage choisi) qui porte l'accessoire recoloré. Écrit comme IECross et Inazuma
# Fantasy (LU) : [[exmesh]] model = …, rows = [[g4md, g4tx, 0]] ; personnage : exmesh_1 = crc32(modèle).
def lignes_accessoire(data_dir, code):
    """lignes EXMESH du jeu qui utilisent un fichier de chr/_item/<code>/ (None : pas un accessoire)"""
    parts = sorted(glob.glob(os.path.join(data_dir, 'common', 'gamedata', 'character', 'chara_parts_*.cfg.bin')))[-1]
    out = [v for k, v in parse(parts) if k == 'CHARA_PARTS_EXMESH_INFO' and v and isinstance(v[0], str) and v[0].startswith('_item/%s/' % code)]
    return out or None


def exporter_objet(cfg, demande, entree):
    """demande = {code (objet), tete (code de la tête du personnage qui le portera), nom, description, textures}"""
    nom = str(demande.get('nom') or '').strip()
    if not nom:
        return {'ok': False, 'erreur': 'Donne un nom au nouveau joueur.'}
    textures = demande.get('textures') or {}
    if not textures:
        return {'ok': False, 'erreur': 'Rien n’est modifié : recolore d’abord l’objet.'}
    D = cfg['data_dir']; code = entree['code']
    lignes = lignes_accessoire(D, code)
    if not lignes:
        return {'ok': False, 'erreur': 'Cet objet n’est pas un accessoire que les personnages portent (véhicule, objet de décor…) : pas de copie possible.'}
    tete = next((x for x in json.load(open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'cache', 'index_jeu.json'), encoding='utf-8'))['personnages']
                 if x['code'] == demande.get('tete')), None)
    p = CP.personnage_de_tete(D, tete['chemin']) if tete else None
    if not p:
        return {'ok': False, 'erreur': 'Choisis le personnage qui portera l’objet (un joueur du jeu).'}
    reg = CP.registre(cfg); cle = CP.cle_creation(reg, demande, slug(nom), nom, lambda x: x.get('genre') == 'objet' and x.get('base') == p['code'])   # (28/11) Modifier : LA création ; slug pris -> neuf
    e = reg.get(cle) or {}
    if e and (e.get('genre') != 'objet' or e.get('base') != p['code']):
        return {'ok': False, 'erreur': 'Le nom « %s » est déjà pris par une autre copie : choisis-en un autre.' % nom}
    if not e:
        pris = CP._ids_pris(cfg)
        neuf = CP._code_libre(cfg, p['code'], reg)
        pris_m = {x.get('vetement', {}).get('modele') for x in reg.values()}
        modele = next('iz%06d' % n for n in range(1, 100000) if 'iz%06d' % n not in pris_m)
        e = {'genre': 'objet', 'code': neuf, 'base': p['code'], 'carte_origine': p['carte'], 'id': zlib.crc32(neuf.encode()),
             'modele': CP._id(CP.MOD_ID + '.' + cle + '.modele', pris), 'carte': CP._id(CP.MOD_ID + '.' + cle + '.carte', pris),
             'nom_txt': CP._id(CP.MOD_ID + '.' + cle + '.nom', pris), 'court_txt': CP._id(CP.MOD_ID + '.' + cle + '.court', pris),
             'desc_txt': CP._id(CP.MOD_ID + '.' + cle + '.description', pris), 'vetement': {'type': 'exmesh', 'modele': modele}}
        if e['id'] in pris:
            return {'ok': False, 'erreur': 'crc32(%s) déjà utilisé : réessaie' % neuf}
    m = e['vetement']['modele']
    rel = retouches.fichier_texture(cfg, entree)                 # chr/_item/<code>/<fichier>.g4tx
    chemin = rel[len('chr/'):]
    rows = [[r[0], ('_item/%s/%s.g4tx' % (m, m)) if (len(r) > 1 and r[1] == chemin) else r[1]] + list(r[2:]) for r in lignes]
    if not any(r[1] == '_item/%s/%s.g4tx' % (m, m) for r in rows):
        return {'ok': False, 'erreur': 'la texture %s n’est pas celle de l’accessoire' % chemin}
    e['vetement'].update(type='exmesh', source=code, rows=rows, texture=chemin)
    e.update(nom=nom, description=str(demande.get('description') or ''), nom_origine=p['nom'], date=datetime.datetime.now().isoformat(timespec='seconds'),
             source_jeu=entree['code'])   # (28/11) la tenue / l'accessoire recoloré : « Modifier » rouvre CELUI-LÀ (onglet Tenues)
    gt = images.G4TX(open(os.path.join(D, 'dx11', *rel.split('/')), 'rb').read())
    rempl, rapport, tmp = {}, [], tempfile.mkdtemp()
    try:
        with images.pool_encodage() as pool:
            for n_, url in textures.items():
                if n_ not in gt.noms:
                    return {'ok': False, 'erreur': '%s n’est pas dans %s' % (n_, rel)}
                bloc = gt.blocs[gt.noms.index(n_)]
                h0, w0 = struct.unpack_from('<II', bloc, 12)
                w, h, rows_ = _png(url, tmp)
                if (w, h) != (w0, h0):
                    return {'ok': False, 'erreur': '%s : %dx%d au lieu de %dx%d' % (n_, w, h, w0, h0)}
                if bloc[84:88] == b'DX10' and struct.unpack_from('<I', bloc, 128)[0] == 98:
                    rempl[n_] = images.dds_bc7(w, h, rows_, bloc[:148], images.mips_dds(bloc), pool)
                elif bloc[84:88] == b'DXT1':
                    rempl[n_] = images.dds_bc1(w, h, rows_, pool, mips=images.mips_dds(bloc))
                else:
                    return {'ok': False, 'erreur': '%s : format pas encore pris en charge' % n_}
                rapport.append('%s (%dx%d)' % (n_, w, h))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    sortie = CP._sortie(cfg)
    d = os.path.join(sortie, 'assets', 'chr', '_item', m); os.makedirs(d, exist_ok=True)
    open(os.path.join(d, m + '.g4tx'), 'wb').write(gt.reconstruire(rempl))
    pp = os.path.join(D, 'dx11', 'menu', '200_icon', '10_icon_chr', 'face', p['code'] + '_l.g4tx')
    if os.path.exists(pp):
        dd = os.path.join(sortie, 'assets', 'menu', '200_icon', '10_icon_chr', 'face'); os.makedirs(dd, exist_ok=True)
        open(os.path.join(dd, e['code'] + '_l.g4tx'), 'wb').write(CP.bustes.renommer(open(pp, 'rb').read(), p['code'], e['code']))
    reg[cle] = e
    CP._sauver(cfg, reg); CP._ecrire_contenu(cfg, reg)
    rapport.insert(0, '%s : copie de %s (%s) qui porte l’objet %s recoloré (accessoire %s), code %s' % (nom, p['nom'], p['code'], code, m, e['code']))
    return {'ok': True, 'dossier': sortie, 'code': e['code'], 'rapport': rapport}


def noms_par_texture(data_dir):
    """(15/11/2026) pour nommer les tenues : texture « _uniform/<dossier>/<fichier>.g4tx » -> noms de ceux qui la portent
    (joueurs d'abord). Mêmes tables que porteurs() : chara_parts (lignes), chara_model (colonnes 5, 6, 7), chara_base."""
    P = _parties(data_dir)
    cols = {'clothes': (1, 4, 7, 9), 'shoes': (1,), 'gloves': (1,)}
    tex_de = {}                                          # (genre, crc du modèle) -> textures
    for g, ms in P.items():
        for nom, lignes in ms.items():
            s = {r[i] for r in lignes for i in cols[g] if len(r) > i and isinstance(r[i], str) and r[i].endswith('.g4tx')}
            if s:
                tex_de[(g, zlib.crc32(nom.encode()))] = s
    c = os.path.join(data_dir, 'common')
    modele_tex = {}
    for f in sorted(glob.glob(os.path.join(c, 'gamedata', 'character', 'chara_model_1*.cfg.bin'))):
        for k, v in cfgbin.lire(open(f, 'rb').read()):
            if not v or not isinstance(v[0], int):
                continue
            for g, (G, col, p) in GENRES.items():
                if len(v) > col and isinstance(v[col], int):
                    s = tex_de.get((g, v[col] & 0xFFFFFFFF))
                    if s:
                        modele_tex.setdefault(v[0] & 0xFFFFFFFF, set()).update(s)
    noms = {}
    for k, v in cfgbin.lire(open(os.path.join(c, 'text', _langue.code(), 'chara_text.cfg.bin'), 'rb').read()):
        if len(v) > 5 and isinstance(v[0], int) and v[1] == 0 and isinstance(v[5], str):
            noms.setdefault(v[0] & 0xFFFFFFFF, v[5])
    joueurs = {v[1] & 0xFFFFFFFF for k, v in cfgbin.lire(open(_dernier(os.path.join(c, 'gamedata', 'character', 'chara_param_1*.cfg.bin')), 'rb').read())
               if len(v) > 1 and isinstance(v[1], int)}
    out = {}
    for k, v in cfgbin.lire(open(_dernier(os.path.join(c, 'gamedata', 'character', 'chara_base_*.cfg.bin')), 'rb').read()):
        if len(v) > 6 and isinstance(v[1], str) and isinstance(v[6], int) and (v[6] & 0xFFFFFFFF) in modele_tex:
            n = noms.get(v[3] & 0xFFFFFFFF) if isinstance(v[3], int) else None
            if not n or _japonais(n):
                continue
            joueur = zlib.crc32(v[1].encode()) in joueurs and v[1][0] == 'c'
            for t in modele_tex[v[6] & 0xFFFFFFFF]:
                l = out.setdefault(t, [])
                if n not in [x[1] for x in l]:
                    l.append((0 if joueur else 1, n))
    return {t: [n for _, n in sorted(l)] for t, l in out.items()}


# ---------------------------------------------------------------------------------------------------- (15/11/2026) CORPULENCES
# LU : un modèle de vêtement a une ligne par CORPS (ligne i = corps i, colonne 2 = i) avec son maillage (u000101…u000108) ;
# seule la ligne 0 porte la texture (les autres : 0 = la même). Le corps d'un personnage = chara_model [4] ; sa ligne =
# CHARA_BODY_INFO [4] (vérifié : corps enfant 0x9A364093 -> ligne 10 -> maillage u000103 = sa variante [6] + 1).
SQUELETTES = {'c000101': 'taille normale', 'c000201': 'petit', 'c000301': 'grand', 'c000401': 'costaud'}


def corps(data_dir):
    """{ligne: {'squelette', 'nb', 'exemple'}} : chaque ligne de vêtement et le corps le plus courant qui la prend"""
    if 'corps' in _cache:
        return _cache['corps']
    c = os.path.join(data_dir, 'common')
    f = sorted(glob.glob(os.path.join(c, 'gamedata', 'character', 'chara_model_1*.cfg.bin')))[-1]
    infos, modele_corps = {}, {}
    for k, v in parse(f):
        if k == 'CHARA_BODY_INFO' and len(v) > 4 and isinstance(v[4], int):
            infos[v[0] & 0xFFFFFFFF] = (v[4], os.path.basename(str(v[1])).split('.')[0])
        elif k == 'CHARA_MODEL_INFO' and len(v) > 4 and isinstance(v[4], int):
            modele_corps[v[0] & 0xFFFFFFFF] = v[4] & 0xFFFFFFFF
    noms = {}
    for k, v in cfgbin.lire(open(os.path.join(c, 'text', _langue.code(), 'chara_text.cfg.bin'), 'rb').read()):
        if len(v) > 5 and isinstance(v[0], int) and v[1] == 0 and isinstance(v[5], str):
            noms.setdefault(v[0] & 0xFFFFFFFF, v[5])
    lignes = {}
    for k, v in cfgbin.lire(open(_dernier(os.path.join(c, 'gamedata', 'character', 'chara_base_*.cfg.bin')), 'rb').read()):
        if len(v) > 6 and isinstance(v[6], int):
            b = infos.get(modele_corps.get(v[6] & 0xFFFFFFFF))
            if not b:
                continue
            e = lignes.setdefault(b[0], {'squelette': b[1], 'nb': 0, 'exemple': None})
            e['nb'] += 1
            n = noms.get(v[3] & 0xFFFFFFFF) if isinstance(v[3], int) else None
            if not e['exemple'] and n and not _japonais(n) and isinstance(v[1], str) and v[1].startswith('c0'):
                e['exemple'] = n
    _cache['corps'] = lignes
    return lignes


def corpulences(cfg, entree):
    """maillages de cette tenue selon le corps : [{modele (chemin .g4md), lignes, libelle}] (vide : un seul corps)"""
    rel = retouches.fichier_texture(cfg, entree)
    if not rel:
        return []
    chemin = rel[len('chr/'):] if rel.startswith('chr/') else rel
    P = _parties(cfg['data_dir'])
    lignes = next((l for g in ('clothes', 'shoes', 'gloves') for l in P[g].values() if l and len(l[0]) > 1 and l[0][1] == chemin and len(l) > 1), None)
    if not lignes:
        return []
    C = corps(cfg['data_dir'])
    par_md = {}
    for i, r in enumerate(lignes):
        if isinstance(r[0], str):
            par_md.setdefault(r[0], []).append(i)
    out = []
    for md, ii in par_md.items():
        e = [C[i] for i in ii if i in C]
        e.sort(key=lambda x: -x['nb'])
        lib = ', '.join('%s%s' % (SQUELETTES.get(x['squelette'], x['squelette']), ' (ex. %s)' % x['exemple'] if x['exemple'] else '') for x in e[:2]) or 'corps %s' % ii
        out.append({'modele': 'common/chr/' + md, 'lignes': ii, 'libelle': lib, 'nb': sum(x['nb'] for x in e)})
    return out


def ligne_du_joueur(data_dir, code):
    """ligne de vêtement (corps) d'un personnage : chara_base [6] -> chara_model [4] -> CHARA_BODY_INFO [4]"""
    c = os.path.join(data_dir, 'common')
    f = sorted(glob.glob(os.path.join(c, 'gamedata', 'character', 'chara_model_1*.cfg.bin')))[-1]
    infos, modele_corps = {}, {}
    for k, v in parse(f):
        if k == 'CHARA_BODY_INFO' and len(v) > 4 and isinstance(v[4], int):
            infos[v[0] & 0xFFFFFFFF] = v[4]
        elif k == 'CHARA_MODEL_INFO' and len(v) > 4 and isinstance(v[4], int):
            modele_corps[v[0] & 0xFFFFFFFF] = v[4] & 0xFFFFFFFF
    for k, v in cfgbin.lire(open(_dernier(os.path.join(c, 'gamedata', 'character', 'chara_base_*.cfg.bin')), 'rb').read()):
        if len(v) > 6 and v[1] == code and isinstance(v[6], int):
            return infos.get(modele_corps.get(v[6] & 0xFFFFFFFF))
    return None
