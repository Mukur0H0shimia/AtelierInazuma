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
    # bibliothèques Steam aux endroits habituels de chaque disque (D:\SteamLibrary, E:\Steam…)
    for lettre in 'CDEFGHIJKLMNOPQRSTUVWXYZ':
        r = lettre + ':' + os.sep
        if os.path.isdir(r):
            for sous in ('SteamLibrary', 'Steam', r'Program Files (x86)\Steam', r'Program Files\Steam', r'Games\Steam',
                         r'Games\SteamLibrary', r'Jeux\Steam', r'Jeux\SteamLibrary'):
                out.append(os.path.join(r, sous))
    libs = []
    for r in out:
        libs.append(r)
        vdf = os.path.join(r, 'steamapps', 'libraryfolders.vdf')
        if os.path.isfile(vdf):
            with open(vdf, encoding='utf-8', errors='replace') as f_vdf:
                texte_vdf = f_vdf.read()
            for m in re.finditer(r'"path"\s+"([^"]+)"', texte_vdf):
                libs.append(os.path.normpath(m.group(1).replace('\\\\', '\\')))
    vus, res = set(), []
    for l in libs:
        if l.lower() not in vus and os.path.isdir(l):
            vus.add(l.lower()); res.append(l)
    return res


def jeu_valide(d):
    """un vrai dossier du jeu : nie.exe ET ses paquets (pas une simple copie de l'exe)"""
    return bool(d) and os.path.isfile(os.path.join(d, 'nie.exe')) and os.path.isfile(os.path.join(d, 'data', 'cpk_list.cfg.bin'))


def _nb_mods(d):
    m = os.path.join(d, 'mods')
    return len([x for x in os.listdir(m) if os.path.isdir(os.path.join(m, x))]) if os.path.isdir(m) else -1


def _pres_de(outil_dir):
    """jeu rangé près de l'Atelier (ex. « C:/Victory mods tools/<le jeu>/nie.exe ») : dossiers voisins, 2 niveaux"""
    c, vus = [], set()
    d = os.path.abspath(outil_dir or '.')
    for _ in range(3):                                  # AtelierCouleurs -> AtelierInazuma -> son dossier
        d = os.path.dirname(d)
        for motif in ('*', os.path.join('*', '*')):
            for x in glob.glob(os.path.join(d, motif, 'nie.exe')):
                x = os.path.dirname(x)
                if x.lower() not in vus:
                    vus.add(x.lower()); c.append(x)
    return c


def dossiers_du_jeu(outil_dir=None):
    """[(dossier, nombre de mods)] de toutes les installations trouvées (jeu de base et copies de dépôt)"""
    c = []
    for lib in _steam_racines():
        sa = os.path.join(lib, 'steamapps')
        c += glob.glob(os.path.join(sa, 'common', 'INAZUMA*'))
        c += glob.glob(os.path.join(sa, 'common', '*Victory Road*'))
        c += glob.glob(os.path.join(sa, 'content', 'app_' + APP, 'depot_*'))
    c += _pres_de(outil_dir)
    vus, out = set(), []
    for d in c:
        if d.lower() not in vus and jeu_valide(d):
            vus.add(d.lower()); out.append((d, _nb_mods(d)))
    return out


def trouver_jeu(outil_dir=None):
    l = sorted(dossiers_du_jeu(outil_dir), key=lambda x: -x[1])
    return l[0][0] if l else None


def _data_ok(d):
    """des fichiers du jeu vraiment EXTRAITS. Le dossier « data » du jeu lui-même est rangé en paquets .cpk, mais il peut
    contenir quelques fichiers libres (mods, patchs de traduction : common\\text\\fr\\chara_text.cfg.bin, dx11\\…) :
    on exige donc aussi les dossiers des personnages, qui n'existent que dans une extraction complète."""
    return bool(d) and os.path.isfile(os.path.join(d, 'common', 'text', 'fr', 'chara_text.cfg.bin')) \
        and os.path.isdir(os.path.join(d, 'common', 'chr', '_keshin')) \
        and os.path.isdir(os.path.join(d, 'dx11', 'chr'))


def completer(cfg, outil_dir):
    """complète cfg (dict) ; -> (cfg, changé ?)"""
    avant = dict(cfg)
    if not jeu_valide(cfg.get('jeu_dir')):
        j = trouver_jeu(outil_dir)
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
