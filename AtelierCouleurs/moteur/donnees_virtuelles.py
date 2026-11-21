r"""Dossier « data » VIRTUEL : l'Atelier lit le jeu directement dans ses paquets (moteur/paquets_jeu.py), sans
extraction. Le dossier des données devient AtelierCouleurs\cache\data_jeu ; quand l'Atelier demande un fichier qui
n'y est pas encore, il est sorti de son paquet à ce moment-là (une seule fois), puis lu normalement. Les listes de
dossiers (os.listdir, glob, os.walk…) répondent avec tous les fichiers du jeu, même pas encore sortis.
Ça marche aussi à travers les jonctions des « racines superposées » des mods (moteur/racines.py).

Virtual "data" folder: game files are taken out of their pack on first use, then read normally.
"""
import os, sys, glob, fnmatch, threading, builtins, shutil

_J = None            # paquets_jeu.Jeu
_RACINE = None       # dossier où les fichiers sortis sont rangés (normcase)
_RACINE_VRAIE = None
_verrou = threading.Lock()
_o = {}              # fonctions d'origine


def actif():
    return _J is not None


def _rel(p):
    """chemin « common/... » d'un chemin sous la racine virtuelle (aussi à travers une jonction), sinon None"""
    try:
        p = os.fspath(p)
    except TypeError:
        return None
    if isinstance(p, bytes):
        return None
    a = os.path.normcase(os.path.abspath(p))
    if a == _RACINE:
        return ''
    if a.startswith(_RACINE + os.sep):
        return a[len(_RACINE) + 1:].replace(os.sep, '/')
    if os.sep + 'racines' + os.sep in a:                # racine superposée d'un mod : jonctions vers data
        r = os.path.normcase(os.path.realpath(p))
        if r == _RACINE:
            return ''
        if r.startswith(_RACINE + os.sep):
            return r[len(_RACINE) + 1:].replace(os.sep, '/')
    return None


def _vers_reel(rel):
    return os.path.join(_RACINE_VRAIE, *rel.split('/')) if rel else _RACINE_VRAIE


def _mkdirs(d):
    """os.makedirs sans les fonctions remplacées (un dossier virtuel « existe » sans être sur le disque)"""
    if not _o['isdir'](d):
        _mkdirs(os.path.dirname(d))
        try:
            os.mkdir(d)
        except FileExistsError:
            pass


def sortir(p):
    """s'assure que le fichier p (chemin sous les données) existe sur le disque ; -> True s'il existe"""
    if _o['exists'](p):
        return True
    r = _rel(p)
    if not r or not _J.existe(r):
        return False
    with _verrou:
        dst = _vers_reel(r)
        if not _o['exists'](dst):
            try:
                d = _J.lire(r)
            except OSError:
                return False
            _mkdirs(os.path.dirname(dst))
            tmp = dst + '.%d.tmp' % threading.get_ident()
            with _o['open'](tmp, 'wb') as f:
                f.write(d)
            os.replace(tmp, dst)
    return True


def debut(p, n):
    """les n premiers octets du fichier p, sans le sortir de son paquet (marche aussi sans lecture directe)"""
    if _J is not None and not _o['exists'](p):
        r = _rel(p)
        if r and _J.existe(r):
            return _J.debut(r, n)
    with builtins.open(p, 'rb') as f:
        return f.read(n)


def _est_dossier_v(r):
    return r is not None and r.lower() in _J.dossiers


def _open(file, mode='r', *a, **k):
    if isinstance(file, (str, os.PathLike)) and not any(c in mode for c in 'wax+'):
        if not _o['exists'](file):
            sortir(file)
    return _o['open'](file, mode, *a, **k)


def _exists(p):
    if _o['exists'](p):
        return True
    r = _rel(p)
    return r is not None and (_J.existe(r) or _est_dossier_v(r))


def _isfile(p):
    if _o['isfile'](p):
        return True
    r = _rel(p)
    return bool(r) and _J.existe(r)


def _isdir(p):
    if _o['isdir'](p):
        return True
    return _est_dossier_v(_rel(p))


def _getsize(p):
    if not _o['exists'](p):
        r = _rel(p)
        if r and _J.existe(r):
            return _J.taille(r)
    return _o['getsize'](p)


def _getmtime(p):
    if not _o['exists'](p):
        r = _rel(p)
        if r is not None and (_J.existe(r) or _est_dossier_v(r)):
            return _o['getmtime'](os.path.join(_J.jeu, 'data', 'cpk_list.cfg.bin'))
    return _o['getmtime'](p)


def _stat(p, *a, **k):
    if isinstance(p, (str, os.PathLike)) and not _o['exists'](p):
        sortir(p)
    return _o['stat'](p, *a, **k)


def _samefile(a, b):
    ra, rb = _rel(a), _rel(b)
    if ra is not None and rb is not None and (not _o['exists'](a) or not _o['exists'](b)):
        return ra.lower() == rb.lower()                 # sans sortir les fichiers du jeu pour les comparer
    return _o['samefile'](a, b)


def _listdir(p='.'):
    r = _rel(p)
    reel = _o['listdir'](p) if _o['isdir'](p) else None
    if r is None or not _est_dossier_v(r):
        if reel is None:
            return _o['listdir'](p)                     # erreur normale
        return reel
    # (21/11) sans doublon de casse : les fichiers sortis sont rangés en minuscules (« 20_edit ») et le jeu les écrit
    # « 20_EDIT » ; pour Windows c'est le même dossier (avant : jonction en double -> technique de mod impossible à ouvrir)
    noms = {}
    for n in _J.dossiers[r.lower()].keys():
        noms.setdefault(n.lower(), n)
    for n in reel or []:
        noms.setdefault(n.lower(), n)
    return sorted(noms.values())


def _walk(top, topdown=True, onerror=None, followlinks=False):
    if _rel(top) is None:
        yield from _o['walk'](top, topdown, onerror, followlinks)
        return
    try:
        noms = _listdir(top)
    except OSError as e:
        if onerror:
            onerror(e)
        return
    ds = [n for n in noms if _isdir(os.path.join(top, n))]
    fs = [n for n in noms if n not in ds]
    if topdown:
        yield top, ds, fs
    for d in ds:
        yield from _walk(os.path.join(top, d), topdown, onerror, followlinks)
    if not topdown:
        yield top, ds, fs


def _glob(pattern, *, root_dir=None, dir_fd=None, recursive=False, include_hidden=False):
    p = os.fspath(pattern)
    base = p
    while glob.has_magic(base):
        base = os.path.dirname(base)
    if root_dir is not None or _rel(base or '.') is None:
        # glob.glob d'origine appelle glob.iglob (remplacé) : on passe par l'iglob d'origine
        return list(_o['iglob'](pattern, root_dir=root_dir, dir_fd=dir_fd, recursive=recursive, include_hidden=include_hidden))
    morceaux = os.path.relpath(p, base).split(os.sep) if p != base else []
    out = [base]
    for i, m in enumerate(morceaux):
        suivants = []
        for c in out:
            if m == '**' and recursive:
                suivants += [x for x, _, _ in _walk(c)]
            elif glob.has_magic(m):
                if _isdir(c):
                    suivants += [os.path.join(c, n) for n in _listdir(c)
                                 if fnmatch.fnmatch(n, m) and (include_hidden or not n.startswith('.') or m.startswith('.'))]
            else:
                x = os.path.join(c, m)
                if _exists(x):
                    suivants.append(x)
        out = suivants
    return sorted(out) if morceaux else ([base] if _exists(base) else [])


def _iglob(pattern, **k):
    return iter(_glob(pattern, **k))


def _copier(nom):
    f = _o[nom]

    def g(src, dst, *a, **k):
        sortir(src)
        return f(src, dst, *a, **k)
    return g


def _jonction(src, dst):
    r = _rel(src)
    if r is not None:                                   # la cible d'une jonction doit être un vrai dossier
        _mkdirs(_vers_reel(r))
    return _o['jonction'](src, dst)


def _link(src, dst, *a, **k):
    sortir(src)
    return _o['link'](src, dst, *a, **k)


def activer(jeu_dir, racine):
    """lit le jeu jeu_dir dans ses paquets ; racine = dossier « data » virtuel (où les fichiers sont rangés)"""
    global _J, _RACINE, _RACINE_VRAIE
    if _J is not None:
        return racine
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from moteur import paquets_jeu
    os.makedirs(racine, exist_ok=True)
    _J = paquets_jeu.Jeu(jeu_dir, os.path.dirname(racine))
    _RACINE_VRAIE = os.path.abspath(racine)
    _RACINE = os.path.normcase(_RACINE_VRAIE)
    _o.update(open=builtins.open, exists=os.path.exists, isfile=os.path.isfile, isdir=os.path.isdir,
              getsize=os.path.getsize, getmtime=os.path.getmtime, stat=os.stat, listdir=os.listdir, walk=os.walk,
              glob=glob.glob, iglob=glob.iglob, link=os.link, samefile=os.path.samefile, copyfile=shutil.copyfile, copy=shutil.copy, copy2=shutil.copy2)
    builtins.open = _open
    import io
    io.open = _open
    os.path.exists, os.path.isfile, os.path.isdir = _exists, _isfile, _isdir
    os.path.getsize, os.path.getmtime = _getsize, _getmtime
    os.path.samefile = _samefile
    os.stat, os.listdir, os.walk, os.link = _stat, _listdir, _walk, _link
    glob.glob, glob.iglob = _glob, _iglob
    shutil.copyfile, shutil.copy, shutil.copy2 = _copier('copyfile'), _copier('copy'), _copier('copy2')
    try:
        import _winapi
        _o['jonction'] = _winapi.CreateJunction
        _winapi.CreateJunction = _jonction
    except (ImportError, AttributeError):
        pass
    # pour les programmes lancés par l'Atelier (clone_modele.py, Atelier Maillots)
    os.environ['ATELIER_JEU_DIRECT'] = jeu_dir + os.pathsep + racine
    return racine


def depuis_env():
    """dans un programme lancé par l'Atelier : même dossier virtuel que lui (ATELIER_JEU_DIRECT)"""
    v = os.environ.get('ATELIER_JEU_DIRECT')
    if v and os.pathsep in v:
        jeu, racine = v.split(os.pathsep, 1)
        return activer(jeu, racine)
    return None
