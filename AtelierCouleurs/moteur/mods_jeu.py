"""(17/11/2026) Les modèles de TOUS les mods du dossier <jeu>/mods, activés ou non (demande de muku), rangés dans les
onglets de l'Atelier selon leur type (armure -> Armures, tête -> Personnages, tenue -> Tenues, le reste -> Objets).
Lecture seule, sur place (pas de copie : ~2,5 Go de modèles).

Où les mods rangent leurs fichiers (LU dans les mods installés le 17/11/2026) :
- assets/models/<type>/<nom>/common/*.g4md|g4mg et .../dx11/*.g4tx, déclarés par content/models/<type>/<nom>.toml
  (VRFW.model/1, format = "native", game_path = "chr/_armd/<nom>" : chemin du jeu) ;
- assets/<chemin du jeu sans common/ ni dx11/> : modèles et textures dans le même dossier (ex. CharacterReforged
  assets/chr/_armd/ka002201/ka002201_g1.g4md) ; s'il n'y a pas de texture dans le mod, c'est celle du jeu (DÉDUIT :
  le mod n'ajoute que des maillages, la texture d'origine est dans data/dx11/<chemin>) ;
- même chose dans addons/<mod>/assets (extensions d'un mod pour un autre).
Pas encore lus : modèles .glb (VRFW, kind = head / character), esprits en .objbin + .g4pk.
Le mod gagnant en jeu (ordre load_order.toml) n'est pas choisi ici : chaque mod a ses propres entrées.
"""
import os, re, glob, json, struct, zlib

try:
    import tomllib
except ImportError:                                   # Python < 3.11
    tomllib = None

TYPES = (('chr/_armd', 'Armure'), ('models/armours', 'Armure'), ('chr/_uniform', 'Tenue'), ('models/kits', 'Tenue'),
         ('chr/_face', 'Personnage'), ('models/characters', 'Personnage'), ('chr/_item', 'Objet'), ('models/items', 'Objet'),
         ('models/props', 'Décor'), ('chr/_keshin', 'Esprit'), ('models/effects', 'Effet'), ('effect', 'Effet'), ('map', 'Stade'))


# (17/11/2026, demande de muku : pas d'onglet à part) onglet de l'Atelier où va chaque modèle de mod
CATEGORIE = {'Armure': 'armures', 'Tenue': 'tenues', 'Personnage': 'personnages'}


def _type(rel):
    return next((t for p, t in TYPES if rel == p or rel.startswith(p + '/')), 'Modèle')


def _actifs(mods_dir):
    try:
        return set(tomllib.load(open(os.path.join(mods_dir, 'enabled.toml'), 'rb')).get('enabled') or [])
    except Exception:
        return set()


def _chemins_jeu(racine):
    """content/models/**/<nom>.toml -> {nom: game_path} (format natif)"""
    out = {}
    for f in glob.glob(os.path.join(racine, 'content', 'models', '**', '*.toml'), recursive=True):
        try:
            t = tomllib.load(open(f, 'rb'))
        except Exception:
            continue
        if t.get('game_path'):
            out[os.path.basename(f)[:-5]] = t['game_path'].replace('\\', '/').strip('/')
    return out


def _texture(dossiers, noms):
    for d in dossiers:
        if not d or not os.path.isdir(d):
            continue
        for n in noms:
            f = os.path.join(d, n + '.g4tx')
            if os.path.exists(f):
                return f
        l = sorted(glob.glob(os.path.join(d, '*.g4tx')))
        if l:
            return l[0]
    return None


def noms_g4tx(f):
    """noms des images d'un .g4tx en ne lisant QUE son en-tête (même règle que lib/images.G4TX : les noms sont avant les
    données, qui font les <u32 +0x2C> derniers octets ; il y a <u16 +0x20> images)"""
    from moteur import donnees_virtuelles as _dv           # lecture directe : en-tête sans sortir le fichier
    t = _dv.debut(f, 0x30)
    if t[:4] != b'G4TX':
        return []
    n = struct.unpack_from('<H', t, 0x20)[0]; total = struct.unpack_from('<I', t, 0x2C)[0]
    tete = _dv.debut(f, max(0, os.path.getsize(f) - total))
    return [m.group()[:-1].decode() for m in re.finditer(rb'[a-z][a-z0-9_]{3,40}\x00', tete)][-n:] if n else []


import threading as _th  # noqa: E402
_VERROU_INDEX = _th.Lock()                       # une seule construction à la fois (préparation + demande)
PROGRES = {'fait': 0, 'total': 0}                # avancement (écran de chargement)


def _index_jeu(data_dir, cache_dir):
    with _VERROU_INDEX:
        return _index_jeu_(data_dir, cache_dir)


def _index_jeu_(data_dir, cache_dir):
    """crc32(nom d'image) -> [.g4tx du jeu sous dx11/chr] (en cache : cache/index_tx_chr.json)"""
    f = os.path.join(cache_dir, 'index_tx_chr.json')
    if f in _MEMO:
        return _MEMO[f]
    if os.path.exists(f):
        _MEMO[f] = {int(k): v for k, v in json.load(open(f, encoding='utf-8')).items()}
        return _MEMO[f]
    out = {}
    from concurrent.futures import ThreadPoolExecutor
    fichiers = glob.glob(os.path.join(data_dir, 'dx11', 'chr', '**', '*.g4tx'), recursive=True)

    def lire(g):
        try:
            return noms_g4tx(g)
        except Exception:
            return []
    with ThreadPoolExecutor(8) as pool:                  # plusieurs fichiers à la fois (lecture directe des paquets)
        PROGRES['total'], PROGRES['fait'] = len(fichiers), 0
        for g, noms in zip(fichiers, pool.map(lire, fichiers)):
            PROGRES['fait'] += 1
            for n in noms:
                out.setdefault(zlib.crc32(n.encode()), []).append(g)
    json.dump(out, open(f, 'w', encoding='utf-8'))
    _MEMO[f] = out
    return out


_MEMO = {}


def crc_textures(md):
    """crc32 des noms des textures citées par le .g4md (table de l'en-tête +0x76, md[0x27] noms ; voir carte.py)"""
    base = struct.unpack_from('<H', md, 0x0A)[0] * 4
    t = base + struct.unpack_from('<H', md, 0x76)[0] * 4
    return [struct.unpack_from('<I', md, t + 4 * j)[0] for j in range(md[0x27]) if t + 4 * j + 4 <= len(md)]


def _par_noms(md_f, index):
    """le .g4tx qui contient le plus d'images citées par le modèle (coupes de tenues : texture rangée ailleurs)"""
    try:
        c = crc_textures(open(md_f, 'rb').read())
    except Exception:
        return None
    score = {}
    for x in c:
        for g in index.get(x, []):
            score[g] = score.get(g, 0) + 1
    return max(score, key=lambda g: (score[g], -len(g))) if score else None


def construire(cfg, cache_dir=None):
    """[{code, nom, genre, sorte, cat, chemin, mod, actif, md, tx, chemin_jeu}] ; cat = onglet de l'Atelier ;
    chemin = 'mod:/chr/<code>' (lu par serveur.objet)"""
    mods_dir = os.path.join(cfg.get('jeu_dir') or '', 'mods')
    data = cfg['data_dir']
    if not os.path.isdir(mods_dir):
        return []
    actifs = _actifs(mods_dir)
    out, vus = [], set()
    mod_index, jeu_index = {}, [None]
    for mod in sorted(os.listdir(mods_dir), key=str.lower):
        rmod = os.path.join(mods_dir, mod)
        if not os.path.isfile(os.path.join(rmod, 'mod.toml')):
            continue
        racines = [(rmod, '')] + [(a, os.path.basename(a)) for a in sorted(glob.glob(os.path.join(rmod, 'addons', '*'))) if os.path.isdir(a)]
        for racine, addon in racines:
            assets = os.path.join(racine, 'assets')
            if not os.path.isdir(assets):
                continue
            gp = _chemins_jeu(racine)
            for d, _, fichiers in os.walk(assets):
                mds = sorted(f for f in fichiers if f.endswith('.g4md') and f[:-5] + '.g4mg' in fichiers)
                if not mds:
                    continue
                rel = os.path.relpath(d, assets).replace('\\', '/')
                if rel.startswith('menu/'):
                    continue
                # assets/models/<type>/<nom>/common -> textures dans .../dx11, chemin du jeu donné par le .toml
                m = re.match(r'^(models/[^/]+/([^/]+))/common$', rel)
                if m:
                    jeu_rel = gp.get(m.group(2), m.group(1))
                    dx = [os.path.join(os.path.dirname(d), 'dx11')]
                else:
                    jeu_rel = rel
                    dx = [d]
                dx.append(os.path.join(data, 'dx11', *jeu_rel.split('/')))          # texture du jeu (le mod n'a que le maillage)
                dossier = os.path.basename(jeu_rel)
                for f in mds:
                    base = f[:-5]
                    tx = _texture(dx, (dossier, dossier + '_10', base, base + '_10'))
                    if not tx:                    # (coupe de tenue, peau) : la texture qui porte les noms cités par le modèle
                        mod_tx = [g for g in glob.glob(os.path.join(assets, '**', '*.g4tx'), recursive=True) if '/menu/' not in g.replace('\\', '/')] \
                            if mod_index.get(racine) is None else None
                        if mod_tx is not None:
                            mi = {}
                            for g in mod_tx:
                                try:
                                    for n in noms_g4tx(g):
                                        mi.setdefault(zlib.crc32(n.encode()), []).append(g)
                                except Exception:
                                    pass
                            mod_index[racine] = mi
                        tx = _par_noms(os.path.join(d, f), mod_index[racine])
                        if not tx and cache_dir:
                            if jeu_index[0] is None:
                                jeu_index[0] = _index_jeu(data, cache_dir)
                            tx = _par_noms(os.path.join(d, f), jeu_index[0])
                    code = re.sub(r'[^\w~-]', '_', '%s~%s' % (mod + ('~' + addon if addon else ''), base))
                    k, c0 = 2, code
                    while code in vus:
                        code = '%s~%d' % (c0, k); k += 1
                    vus.add(code)
                    t = _type(jeu_rel)
                    out.append({'code': code, 'nom': '%s · %s%s' % (base, mod, ' / ' + addon if addon else ''),
                                'genre': '%s · %s%s' % (t, mod, '' if mod in actifs else ' (désactivé)'),
                                'sorte': t, 'cat': CATEGORIE.get(t), 'mod': mod, 'addon': addon or None, 'actif': mod in actifs,
                                'chemin': 'mod:/chr/' + code, 'chemin_jeu': jeu_rel + '/' + f,
                                'md': os.path.join(d, f), 'tx': tx,
                                'tx_du_jeu': bool(tx) and os.path.normcase(tx).startswith(os.path.normcase(data))})
    return out


def objet(cfg, entree):
    """modèle d'un mod lu comme un modèle du jeu (même lecteur, shaders du jeu) ; dossier du cache = mod_<code>"""
    from .jeu import ObjetModele
    o = ObjetModele.__new__(ObjetModele)
    md = entree['md']
    o.nom = os.path.basename(md)[:-5]                    # (le lecteur s'en sert pour les textures <nom>_<k>0 sans cases)
    o.data_dir = cfg['data_dir']                         # shaders et textures partagées : ceux du jeu
    o.dossier_rel = os.path.dirname(entree['chemin_jeu'])
    o.common = os.path.dirname(md)
    o.dx11 = os.path.dirname(entree['tx']) if entree.get('tx') else os.path.join(cfg['data_dir'], 'dx11', *o.dossier_rel.split('/'))
    o.pk = open(md, 'rb').read()
    o.mg = open(md[:-5] + '.g4mg', 'rb').read()
    o.tx = open(entree['tx'], 'rb').read() if entree.get('tx') else None
    o._lire()
    o.particules = {'emetteurs': []}
    o.lumieres = None
    o.nom = 'mod_' + entree['code']                      # textures en PNG dans cache/mod_<code>/ (pas celles du jeu)
    return o


def objet_esprit(cfg, entree):
    """(17/11/2026) esprit guerrier d'un mod (.g4pkm .g4mg .g4tx .objbin dans assets/chr/_keshin/<code>/ du mod) lu comme
    g4.ObjetEffet lit ceux du jeu (même __init__, dossiers du mod) ; dossier du cache = mod_<code>"""
    from . import g4
    o = g4.ObjetEffet.__new__(g4.ObjetEffet)
    d = entree['dossier_abs']
    o.nom = entree['modele']
    o.data_dir = cfg['data_dir']
    o.dossier_rel = os.path.dirname(entree['chemin_jeu'])
    o.common = o.dx11 = d
    o.pk = open(os.path.join(d, o.nom + '.g4pkm'), 'rb').read()
    o.mg = open(os.path.join(d, o.nom + '.g4mg'), 'rb').read()
    p_tx = os.path.join(d, o.nom + '.g4tx')
    o.tx = open(p_tx, 'rb').read() if os.path.exists(p_tx) else None
    o._lire()
    try:
        o.particules = o._lire_particules()
    except Exception as ex:
        o.particules = {'emetteurs': [], 'erreur': str(ex)}
    try:
        o.lumieres = o._lire_lumieres()
    except Exception as ex:
        o.lumieres = {'erreur': str(ex)}
    o.nom = 'mod_' + entree['code']
    return o
