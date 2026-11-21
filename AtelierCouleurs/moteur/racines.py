"""(17/11/2026) RACINE SUPERPOSÉE d'un mod : le dossier du jeu (data/) avec les fichiers du mod par-dessus, pour lire les
cinématiques des techniques des mods avec les lecteurs habituels de l'Atelier (qui prennent un « data_dir »).

cache/racines/<mod>_<signature>/{common,dx11} :
- dossier que le mod ne touche pas -> JONCTION vers le dossier du jeu (rien n'est copié) ;
- dossier qui n'existe que dans le mod -> jonction vers le dossier du mod ;
- dossier mixte -> vrai dossier : fichiers du jeu en LIENS PHYSIQUES (même fichier, pas de copie), fichiers du mod copiés
  (ils passent devant ceux du jeu : c'est ce que le jeu moddé lit).
Rien n'est jamais modifié dans data/ ni dans les mods, et rien n'est effacé : une nouvelle version du mod donne un nouveau
dossier (signature = nombre, tailles et dates des fichiers du mod).

Fichiers du mod (LU, mods installés le 17/11/2026) : assets/<chemin du jeu sans common/ ni dx11/> (.g4tx -> dx11, le reste ->
common : event_cfg/eff|evt, event/evNN/…, effect/event/…) et assets/models/<type>/<nom>/{common,dx11} (game_path du .toml).
"""
import os, glob, json, shutil, hashlib, threading, _winapi

_verrou = threading.Lock()
_memo = {}
_vu = {}
DOSSIERS = ('event_cfg', 'event', 'effect', 'chr', 'sound', 'map')      # ce qu'une cinématique peut lire


def _fichiers_du_mod(mods_dir, mod):
    """{(« common » | « dx11 », chemin relatif du jeu): fichier du mod}"""
    from .mods_jeu import _chemins_jeu
    a = os.path.join(mods_dir, mod, 'assets')
    out = {}
    if not os.path.isdir(a):
        return out
    for d, _, fs in os.walk(a):
        rel = os.path.relpath(d, a).replace('\\', '/')
        if rel.split('/')[0] not in DOSSIERS:
            continue
        for f in fs:
            out[('dx11' if f.endswith('.g4tx') else 'common', (rel + '/' + f) if rel != '.' else f)] = os.path.join(d, f)
    gp = _chemins_jeu(os.path.join(mods_dir, mod))
    for nom, chemin in gp.items():
        if chemin.split('/')[0] not in DOSSIERS:
            continue
        for cote in ('common', 'dx11'):
            for f in glob.glob(os.path.join(a, 'models', '*', nom, cote, '*')):
                if os.path.isfile(f):
                    out.setdefault((cote, chemin + '/' + os.path.basename(f)), f)
    return out


def _arbre(fichiers, cote):
    t = {}
    for (c, rel), src in fichiers.items():
        if c != cote:
            continue
        n = t
        parties = rel.split('/')
        for p in parties[:-1]:
            n = n.setdefault(p, {})
            if not isinstance(n, dict):
                break
        else:
            n[parties[-1]] = src
    return t


def _source_unique(noeud):
    """dossier du mod d'où vient tout ce sous-arbre (pour une jonction), sinon None"""
    srcs = set()

    def parcourir(n):
        for v in n.values():
            if isinstance(v, dict):
                parcourir(v)
            else:
                srcs.add(os.path.dirname(v))
    parcourir(noeud)
    if not srcs:
        return None
    d = os.path.commonpath(list(srcs))
    return d if os.path.isdir(d) else None


def _fusion(dest, jeu, noeud):
    os.makedirs(dest, exist_ok=True)
    noms_jeu = os.listdir(jeu) if os.path.isdir(jeu) else []
    for nom in noms_jeu:                                   # ce que le mod ne touche pas : le jeu tel quel
        if nom in noeud:
            continue
        s, d = os.path.join(jeu, nom), os.path.join(dest, nom)
        if os.path.isdir(s):
            _winapi.CreateJunction(s, d)
        else:
            try:
                os.link(s, d)
            except OSError:
                shutil.copy2(s, d)
    for nom, v in noeud.items():
        d = os.path.join(dest, nom)
        if isinstance(v, dict):
            s_jeu = os.path.join(jeu, nom)
            src = _source_unique(v)
            # dossier absent du jeu et venu d'un seul dossier du mod, au même nom : jonction (pas de copie)
            if not os.path.exists(s_jeu) and src and os.path.basename(src) == nom and \
                    len(os.listdir(src)) == len(v) and all(not isinstance(x, dict) for x in v.values()):
                _winapi.CreateJunction(src, d)
            else:
                _fusion(d, s_jeu, v)
        else:
            try:                                           # fichier du mod : il passe devant celui du jeu
                os.link(v, d)                              # (lien quand c'est possible : fichiers convertis du cache)
            except OSError:
                shutil.copy2(v, d)


def racine(cfg, cache_dir, mod):
    """dossier « data » superposé (jeu + mod) ; None si le mod n'apporte aucun fichier de cinématique"""
    mods_dir = os.path.join(cfg.get('jeu_dir') or '', 'mods')
    import time
    with _verrou:
        if mod in _memo and time.time() - _vu.get(mod, 0) < 10:      # (signature relue au plus toutes les 10 s)
            return _memo[mod][1]
        _vu[mod] = time.time()
        fichiers = _fichiers_du_mod(mods_dir, mod)
        # (17/11/2026) modèles .glb du mod convertis au format du jeu (moteur/glb_vrfw.py), comme VRFW au lancement ;
        # un fichier que le mod fournit déjà garde la priorité
        try:
            from . import glb_vrfw
            for k, v in glb_vrfw.fichiers_du_mod(cfg, cache_dir, mod).items():
                fichiers.setdefault(k, v)
        except Exception as ex:
            print('glb du mod', mod, ex)
        if not fichiers:
            return None
        sig = hashlib.md5(json.dumps(sorted((k[0], k[1], os.path.getsize(v), int(os.path.getmtime(v))) for k, v in fichiers.items()))
                          .encode()).hexdigest()[:10]
        if _memo.get(mod, (None,))[0] == sig:
            return _memo[mod][1]
        r = os.path.join(cache_dir, 'racines', '%s_%s' % (mod, sig))
        fait = os.path.join(r, '_fini.json')
        if not os.path.exists(fait):
            if os.path.exists(r):                         # construction interrompue : on recommence ailleurs, sans effacer
                k = 2
                while os.path.exists(r + '_%d' % k):
                    k += 1
                r = r + '_%d' % k
                fait = os.path.join(r, '_fini.json')
            for cote in ('common', 'dx11'):
                _fusion(os.path.join(r, cote), os.path.join(cfg['data_dir'], cote), _arbre(fichiers, cote))
            for x in os.listdir(cfg['data_dir']):          # le reste de data/ (shader, …) : jonctions
                if x not in ('common', 'dx11') and os.path.isdir(os.path.join(cfg['data_dir'], x)) and not os.path.exists(os.path.join(r, x)):
                    _winapi.CreateJunction(os.path.join(cfg['data_dir'], x), os.path.join(r, x))
            json.dump({'mod': mod, 'fichiers': len(fichiers)}, open(fait, 'w'))
        _memo[mod] = (sig, r)
        return r


def mod_a_des_cinematiques(cfg, mod):
    a = os.path.join(cfg.get('jeu_dir') or '', 'mods', mod, 'assets', 'event_cfg')
    return os.path.isdir(a)
