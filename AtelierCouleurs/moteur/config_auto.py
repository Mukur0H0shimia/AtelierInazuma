r"""Réglages trouvés tout seuls au démarrage (config.json absent ou chemins faux) / settings found automatically.

- jeu_dir : le dossier du jeu QUI A LES MODS. Certains joueurs ont leurs mods dans le jeu de base
  (steamapps\common\INAZUMA ELEVEN  Victory Road), d'autres dans une copie de dépôt (steamapps\content\app_2799860\
  depot_*). On cherche dans toutes les bibliothèques Steam (registre + libraryfolders.vdf) et on garde celui qui a le
  plus de mods dans son dossier « mods ».
- data_dir : les données du jeu extraites (dossiers common\ et dx11\) : « data » à côté de l'Atelier ou dans le jeu.
- sauvegardes_dir, port, langue : valeurs par défaut.
Un chemin déjà réglé et valide n'est jamais changé.
"""
import os, re, glob

APP = '2799860'


def _steam_racines():
    out = []
    try:
        import winreg
        for ruche, cle, val in ((winreg.HKEY_CURRENT_USER, r'Software\Valve\Steam', 'SteamPath'),
                                (winreg.HKEY_LOCAL_MACHINE, r'SOFTWARE\WOW6432Node\Valve\Steam', 'InstallPath')):
            try:
                with winreg.OpenKey(ruche, cle) as k:
                    out.append(os.path.normpath(winreg.QueryValueEx(k, val)[0]))
            except OSError:
                pass
    except ImportError:
        pass
    out.append(os.path.join(os.environ.get('ProgramFiles(x86)', r'C:\Program Files (x86)'), 'Steam'))
    libs = []
    for r in out:
        libs.append(r)
        vdf = os.path.join(r, 'steamapps', 'libraryfolders.vdf')
        if os.path.isfile(vdf):
            for m in re.finditer(r'"path"\s+"([^"]+)"', open(vdf, encoding='utf-8', errors='replace').read()):
                libs.append(os.path.normpath(m.group(1).replace('\\\\', '\\')))
    vus, res = set(), []
    for l in libs:
        if l.lower() not in vus and os.path.isdir(l):
            vus.add(l.lower()); res.append(l)
    return res


def _nb_mods(d):
    m = os.path.join(d, 'mods')
    return len([x for x in os.listdir(m) if os.path.isdir(os.path.join(m, x))]) if os.path.isdir(m) else -1


def dossiers_du_jeu():
    """[(dossier, nombre de mods)] de toutes les installations trouvées (jeu de base et copies de dépôt)"""
    c = []
    for lib in _steam_racines():
        sa = os.path.join(lib, 'steamapps')
        c += glob.glob(os.path.join(sa, 'common', 'INAZUMA ELEVEN*Victory Road'))
        c += glob.glob(os.path.join(sa, 'content', 'app_' + APP, 'depot_*'))
    return [(d, _nb_mods(d)) for d in c if os.path.isfile(os.path.join(d, 'nie.exe'))]


def trouver_jeu():
    l = sorted(dossiers_du_jeu(), key=lambda x: -x[1])
    return l[0][0] if l else None


def _data_ok(d):
    # (le dossier « data » du jeu lui-même est rangé en paquets .cpk : il faut des fichiers EXTRAITS)
    return bool(d) and os.path.isfile(os.path.join(d, 'common', 'text', 'fr', 'chara_text.cfg.bin')) \
        and os.path.isdir(os.path.join(d, 'dx11'))


def completer(cfg, outil_dir):
    """complète cfg (dict) ; -> (cfg, changé ?)"""
    avant = dict(cfg)
    if not (cfg.get('jeu_dir') and os.path.isfile(os.path.join(cfg['jeu_dir'], 'nie.exe'))):
        j = trouver_jeu()
        if j:
            cfg['jeu_dir'] = j
    if not _data_ok(cfg.get('data_dir')):
        racine = os.path.dirname(outil_dir)
        for d in (os.path.join(racine, 'data'), os.path.join(outil_dir, 'data'),
                  os.path.join(cfg.get('jeu_dir') or '', 'data')):
            if _data_ok(d):
                cfg['data_dir'] = d
                break
    cfg.setdefault('sauvegardes_dir', os.path.join(os.path.dirname(outil_dir), 'Sauvegardes Atelier'))
    cfg.setdefault('port', 8765)
    cfg.setdefault('langue', 'fr')
    return cfg, cfg != avant
