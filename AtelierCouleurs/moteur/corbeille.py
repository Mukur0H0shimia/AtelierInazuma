"""(23/11/2026, muku : « une option pour voir et restaurer ce qu'on a supprimé, en voyant _retires et la corbeille, mais aussi
pour les supprimer définitivement pour garder de la place, et pouvoir vider le cache aussi sauf le terrain »)

Ce que l'Atelier a mis de côté au lieu de l'effacer :
- projets/corbeille/*.json : projets retirés du hub (🗑 de « À continuer ») ;
- sortie/<mod>/_retires/<date>/ : créations supprimées (« Supprimer » d'une carte de Terminées), avec _retire.json (fiche :
  entrée du registre, où remettre les fichiers) depuis le 23/11 ; avant, la fiche est retrouvée dans la copie du mod qui est
  dans le jeu (mods/<mod>/outil_*.json) quand elle y est encore ;
- maillots/mes_maillots.json.avant_suppression_*.json : liste des maillots avant chaque suppression (images dans travail/).
Restaurer remet tout comme avant ; « Supprimer définitivement » efface (place libérée) ; « Vider le cache » efface le cache
sauf le terrain (cache/carte_*, décor des cinématiques) et ce que la fenêtre ou le lanceur utilisent."""
import os, re, json, glob, shutil, datetime

TAMPON = re.compile(r'_(\d{8}_\d{6})$')
# gardés par « Vider le cache » : le terrain (stade des cinématiques, long à refaire), la fenêtre en cours (profil WebView2),
# le journal ouvert, les marques du lanceur (sans elles il « reprendrait » le cache d'une ancienne version), les bannières
# dessinées (rangées sous le projet, pas refaisables)
GARDER_CACHE = ('fenetre', 'webview2', 'bannieres_apercu', 'serveur.log', 'reprise.txt', 'debloque.txt',
                'data_jeu')           # data_jeu : le jeu lu directement dans ses paquets (version des joueurs), en service
TITRE_ONGLET = {'techniques': 'f-nom', 'esprits': 'p-nom', 'totems': 'p-nom', 'personnages': 'cp-nom', 'tenues': 'ct-nom',
                'armures': 'ca-nom', 'objets': 'oj-nom-copie'}
_memo_projets = {}


REPARSE = 0x400          # FILE_ATTRIBUTE_REPARSE_POINT : jonction, lien symbolique


def _est_lien(e):
    """(23/11) cache/racines : JONCTIONS vers data/ du jeu et vers les mods, fichiers du jeu en LIENS PHYSIQUES
    (moteur/racines.py) : on ne les suit JAMAIS (ni pour compter, ni pour effacer : seul le lien part)"""
    try:
        st = e.stat(follow_symlinks=False)
    except OSError:
        return True
    return e.is_symlink() or bool(getattr(st, 'st_file_attributes', 0) & REPARSE)


def _parcourir(p, effacer=False):
    """octets VRAIMENT occupés sous <p> (un fichier à plusieurs liens physiques, comme ceux du jeu, ne compte pas : l'effacer
    ne libère rien) ; effacer=True : efface aussi, liens compris (le lien seulement, jamais ce vers quoi il pointe)"""
    n = 0
    try:
        entrees = list(os.scandir(p))
    except OSError:
        return 0
    for e in entrees:
        if _est_lien(e):
            if effacer:
                try:
                    (os.rmdir if e.is_dir(follow_symlinks=False) or os.path.isdir(e.path) else os.unlink)(e.path)
                except OSError:
                    try:
                        os.unlink(e.path)
                    except OSError:
                        pass
            continue
        if e.is_dir(follow_symlinks=False):
            n += _parcourir(e.path, effacer)
            if effacer:
                try:
                    os.rmdir(e.path)
                except OSError:
                    pass
            continue
        try:
            st = os.lstat(e.path)
            un = st.st_nlink <= 1
        except OSError:
            continue
        if effacer:
            try:
                os.chmod(e.path, 0o666)
                os.remove(e.path)
            except OSError:
                continue
        if un:
            n += st.st_size
    return n


def taille(p):
    if os.path.isfile(p):
        return os.path.getsize(p)
    return _parcourir(p)


def effacer(p):
    """efface <p> sans jamais suivre une jonction ni un lien ; -> octets libérés"""
    if os.path.isfile(p):
        n = os.path.getsize(p)
        os.remove(p)
        return n
    n = _parcourir(p, effacer=True)
    try:
        os.rmdir(p)
    except OSError:
        pass
    return n


def _date_tampon(t):
    try:
        return datetime.datetime.strptime(t, '%Y%m%d_%H%M%S').isoformat(timespec='seconds')
    except ValueError:
        return None


def _fichier_sur(base, nom):
    """chemin dans <base> sans sortir du dossier (rien de « .. »)"""
    p = os.path.normpath(os.path.join(base, nom))
    if os.path.commonpath([os.path.abspath(p), os.path.abspath(base)]) != os.path.abspath(base):
        raise ValueError('chemin refusé')
    return p


# ---------------------------------------------------------------- liste
def _projets(ici):
    out = []
    for f in sorted(glob.glob(os.path.join(ici, 'projets', 'corbeille', '*.json'))):
        cle = os.path.basename(f)[:-5]
        st = os.stat(f)
        m = _memo_projets.get(f)
        if not m or m[0] != st.st_mtime:
            try:
                e = json.load(open(f, encoding='utf-8'))
            except (OSError, ValueError):
                e = {}
            ch = e.get('champs') or {}
            ong = e.get('onglet') or 'techniques'
            m = (st.st_mtime, {'titre': ch.get(TITRE_ONGLET.get(ong, '')) or ch.get('p-nom') or ch.get('f-nom') or e.get('nom') or cle,
                               'onglet': ong, 'base': e.get('nom'), 'code': e.get('code'), 'vignette': e.get('vignette'),
                               'textures': len(e.get('textures') or {})})
            _memo_projets[f] = m
        t = TAMPON.search(cle)
        out.append(dict(m[1], id='projet:' + cle, genre='projet', taille=st.st_size,
                        supprime=(t and _date_tampon(t.group(1))) or datetime.datetime.fromtimestamp(st.st_mtime).isoformat(timespec='seconds')))
    return out


def _registre_jeu(cfg, mod, fichier):
    f = os.path.join(cfg.get('jeu_dir') or '', 'mods', mod, fichier)
    try:
        return json.load(open(f, encoding='utf-8')) if os.path.isfile(f) else {}
    except (OSError, ValueError):
        return {}


def fiche(cfg, mod, dossier):
    """fiche d'une création retirée : _retire.json, sinon retrouvée (anciennes suppressions) ; None si on ne sait pas la remettre"""
    f = os.path.join(dossier, '_retire.json')
    if os.path.isfile(f):
        try:
            return json.load(open(f, encoding='utf-8'))
        except (OSError, ValueError):
            return None
    noms = os.listdir(dossier)
    if mod == 'MesPersonnages':
        code = next((n for n in noms if re.fullmatch(r'c\d{8}', n)), None)
        reg = _registre_jeu(cfg, mod, 'outil_personnages.json')
        cle = next((k for k, e in reg.items() if e.get('code') == code), None)
        if not code or cle is None or reg[cle].get('vetement'):
            return None
        e = reg[cle]
        return {'mod': mod, 'genre': 'personnages', 'code': code, 'nom': e.get('nom') or cle, 'cle': cle, 'entree': e, 'ancienne': True,
                'fichiers': {code: 'assets/chr/_face/%s/%s' % (e.get('serie'), code),
                             code + '_l.g4tx': 'assets/menu/200_icon/10_icon_chr/face/%s_l.g4tx' % code}}
    if mod == 'MesEsprits':
        codes = set()
        for d, ds, _ in os.walk(os.path.join(dossier, 'assets', 'chr')):
            for x in ds:
                if os.path.basename(d) in ('_keshin', '_waza', '_armd'):
                    codes.add(x)
        reg = _registre_jeu(cfg, mod, 'outil_esprits.json')
        code = next((c for c in codes if c in reg), None)
        if code:
            e = reg[code]
            return {'mod': mod, 'genre': e.get('genre') or 'esprit', 'code': code, 'nom': e.get('nom') or code, 'cle': code, 'entree': e, 'ancienne': True}
        reg = _registre_jeu(cfg, mod, 'outil_armures.json')
        k = next((k for k, e in reg.items() if e.get('modele') in codes), None)
        if k:
            e = reg[k]
            return {'mod': mod, 'genre': 'armures', 'code': e.get('modele'), 'nom': e.get('nom') or k, 'cle': k, 'entree': e, 'ancienne': True}
        return None
    if mod == 'MesTechniques':
        t = glob.glob(os.path.join(dossier, 'content', 'techniques', '*.toml'))
        if not t:
            return None
        nom = os.path.basename(t[0])[:-5]
        reg = _registre_jeu(cfg, mod, 'outil_techniques.json')
        if nom not in reg:
            return None
        mo = _registre_jeu(cfg, mod, 'outil_modeles.json')
        e = reg[nom]
        return {'mod': mod, 'genre': 'technique', 'code': e.get('key'), 'nom': e.get('nom') or nom, 'cle': nom, 'entree': e,
                'modeles': {k: v for k, v in mo.items() if k.startswith(nom + '|')}, 'bannieres': [], 'ancienne': True}
    return None


def _retires(ici, cfg):
    out = []
    for d in sorted(glob.glob(os.path.join(ici, 'sortie', '*', '_retires', '*'))):
        if not os.path.isdir(d):
            continue
        mod = os.path.basename(os.path.dirname(os.path.dirname(d)))
        st = os.path.basename(d)
        fi = fiche(cfg, mod, d)
        n = sum(len(fs) for _, _, fs in os.walk(d))
        exemples = sorted({os.path.splitext(f)[0] for _, _, fs in os.walk(d) for f in fs if f != '_retire.json'})[:4]
        out.append({'id': 'retire:%s/%s' % (mod, st), 'genre': 'creation', 'mod': mod, 'supprime': _date_tampon(st) or st,
                    'titre': (fi or {}).get('nom') or ', '.join(exemples) or st, 'sorte': (fi or {}).get('genre'),
                    'restaurable': bool(fi), 'ancienne': bool(fi and fi.get('ancienne')), 'fichiers': n, 'taille': taille(d)})
    return out


def _maillots_snap(ici):
    return sorted(glob.glob(os.path.join(ici, 'maillots', 'mes_maillots.json.avant_suppression_*.json')))


def _maillots(ici):
    try:
        actuels = {m.get('id') for m in json.load(open(os.path.join(ici, 'maillots', 'mes_maillots.json'), encoding='utf-8')).get('maillots', [])}
        lue = True
    except (OSError, ValueError):
        actuels, lue = set(), False
    vus = {}
    for f in _maillots_snap(ici):                       # du plus ancien au plus récent : la dernière version gagne
        try:
            for m in json.load(open(f, encoding='utf-8')).get('maillots', []):
                if m.get('id') and m['id'] not in actuels:
                    vus[m['id']] = (m, f)
        except (OSError, ValueError):
            continue
    out = []
    for i, (m, f) in vus.items():
        t = re.search(r'_(\d+)\.json$', f)
        tr = os.path.join(ici, 'maillots', 'travail', i)
        out.append({'id': 'maillot:' + i, 'genre': 'maillot', 'mod': 'MesMaillots', 'titre': m.get('nom') or i, 'restaurable': True,
                    'supprime': datetime.datetime.fromtimestamp(int(t.group(1))).isoformat(timespec='seconds') if t else None,
                    'taille': taille(tr) if os.path.isdir(tr) else 0, 'vignette': None})
    # images d'un maillot supprimé avant le 23/11 (la liste gardée ne l'avait pas) : effaçables seulement. Jamais quand la liste
    # des maillots n'a pas pu être lue (on prendrait ceux qui existent pour des restes)
    tr = os.path.join(ici, 'maillots', 'travail')
    if lue and os.path.isdir(tr):
        for i in sorted(os.listdir(tr)):
            if i in actuels or i in vus or not os.path.isdir(os.path.join(tr, i)):
                continue
            out.append({'id': 'maillot:' + i, 'genre': 'maillot', 'mod': 'MesMaillots', 'titre': i, 'restaurable': False,
                        'images_seules': True, 'supprime': datetime.datetime.fromtimestamp(os.path.getmtime(os.path.join(tr, i))).isoformat(timespec='seconds'),
                        'taille': taille(os.path.join(tr, i)), 'vignette': None})
    return out


def lister(ici, cfg):
    l = _projets(ici) + _retires(ici, cfg) + _maillots(ici)
    l.sort(key=lambda x: x.get('supprime') or '', reverse=True)
    return {'ok': True, 'elements': l, 'taille': sum(x.get('taille') or 0 for x in l)}


# ---------------------------------------------------------------- restaurer
def _restaurer_projet(ici, cle):
    src = _fichier_sur(os.path.join(ici, 'projets', 'corbeille'), cle + '.json')
    if not os.path.isfile(src):
        return {'ok': False, 'erreur': 'introuvable'}
    base = TAMPON.sub('', cle) or cle
    dst, k = os.path.join(ici, 'projets', base + '.json'), 2
    while os.path.exists(dst):
        dst, k = os.path.join(ici, 'projets', '%s_%d.json' % (base, k)), k + 1
    os.replace(src, dst)
    return {'ok': True, 'message': 'Projet remis dans « À continuer ».'}


def _restaurer_creation(ici, cfg, mod, st):
    from moteur import esprits, armures_copies, copies_persos, copies_outfits, objets_jeu
    garde = _fichier_sur(os.path.join(ici, 'sortie', mod, '_retires'), st)
    sortie = os.path.join(ici, 'sortie', mod)
    fi = fiche(cfg, mod, garde) if os.path.isdir(garde) else None
    if not fi:
        return {'ok': False, 'erreur': 'Cette suppression est trop ancienne : ses fichiers sont là, mais pas sa fiche. '
                                        'Seul « Supprimer définitivement » est possible.'}
    # où va chaque fichier ; rien n'est déplacé si une place est déjà prise
    paires = []
    if fi.get('fichiers'):
        for k, v in fi['fichiers'].items():
            s = os.path.join(garde, k)
            if os.path.exists(s):
                paires.append((s, _fichier_sur(sortie, v)))
    else:
        for d, ds, fs in os.walk(garde):
            if os.path.relpath(d, garde).split(os.sep)[0] == '_jeu':   # la copie retirée du jeu : « Installer » la remettra
                continue
            for f in fs:
                if f != '_retire.json' or d != garde:
                    s = os.path.join(d, f)
                    paires.append((s, os.path.join(sortie, os.path.relpath(s, garde))))
    genre, cle, e = fi.get('genre'), fi.get('cle'), fi.get('entree') or {}
    if mod == 'MesPersonnages':
        reg = copies_persos.registre(cfg)
        pris = cle in reg or any(x.get('code') == fi.get('code') for x in reg.values())
    elif mod == 'MesEsprits' and genre == 'armures':
        reg = armures_copies.registre(cfg)
        pris = cle in reg or any(x.get('modele') == fi.get('code') for x in reg.values())
    elif mod == 'MesEsprits':
        reg = esprits.registre(sortie)
        pris = cle in reg or any(x.get('key') == e.get('key') for x in reg.values())
    elif mod == 'MesTenues':
        reg = copies_outfits.registre(cfg)
        pris = cle in reg
    elif mod == 'MesObjets':
        reg = objets_jeu.registre(cfg)
        pris = cle in reg
    elif mod == 'MesTechniques':
        f_reg = os.path.join(sortie, 'outil_techniques.json')
        reg = json.load(open(f_reg, encoding='utf-8')) if os.path.isfile(f_reg) else {}
        pris = cle in reg or any(x.get('key') == e.get('key') for x in reg.values())
    else:
        return {'ok': False, 'erreur': 'genre inconnu'}
    occupes = [d for _, d in paires if os.path.exists(d)]
    if pris or occupes:
        return {'ok': False, 'erreur': '« %s » ne peut pas revenir : une création porte déjà son nom ou son code%s. '
                                        'Supprime ou renomme celle-là d’abord.' % (fi.get('nom'), ' (%s)' % os.path.basename(occupes[0]) if occupes else '')}
    for s, d in paires:
        os.makedirs(os.path.dirname(d), exist_ok=True)
        shutil.move(s, d)
    reg[cle] = e
    if mod == 'MesPersonnages':
        copies_persos._sauver(cfg, reg)
        copies_persos._ecrire_contenu(cfg, reg)
    elif mod == 'MesEsprits' and genre == 'armures':
        json.dump(reg, open(os.path.join(sortie, 'outil_armures.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
        armures_copies.ecrire_vrfw(cfg, reg)
    elif mod == 'MesEsprits':
        esprits.ecrire_vrfw(cfg, sortie, reg)
        json.dump(reg, open(os.path.join(sortie, 'outil_esprits.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    elif mod == 'MesTenues':
        json.dump(reg, open(os.path.join(sortie, 'outil_tenues.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
        copies_outfits.ecrire(cfg, reg)
    elif mod == 'MesObjets':
        json.dump(reg, open(os.path.join(sortie, 'outil_objets.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
        objets_jeu.ecrire(cfg, reg)
    elif mod == 'MesTechniques':
        json.dump(reg, open(f_reg, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
        fm = os.path.join(sortie, 'outil_modeles.json')
        mo = json.load(open(fm, encoding='utf-8')) if os.path.isfile(fm) else {}
        mo.update(fi.get('modeles') or {})
        json.dump(mo, open(fm, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
        if fi.get('bannieres'):
            ft = os.path.join(sortie, 'content', 'telops', 'any', 'telops.toml')
            os.makedirs(os.path.dirname(ft), exist_ok=True)
            t = open(ft, encoding='utf-8').read() if os.path.isfile(ft) else 'schema = "VRFW.telop_list/2"\n\n'
            open(ft, 'w', encoding='utf-8').write(t.rstrip('\n') + '\n' + ''.join('\n[[telop]]' + b for b in fi['bannieres']))
    restes = [os.path.join(d, f) for d, _, fs in os.walk(garde) for f in fs if f != '_retire.json']
    if not restes:
        effacer(garde)
    else:                                               # (la copie du jeu, _jeu : gardée à part)
        try:
            os.replace(os.path.join(garde, '_retire.json'), os.path.join(garde, '_retire.restauree.json'))
        except OSError:
            pass
    return {'ok': True, 'message': '« %s » est de retour dans Mes créations. Pour le jeu : « Installer » sur sa carte.' % fi.get('nom')}


def _restaurer_maillot(ici, i, construire):
    from moteur.maillots import atelier_mod as A
    m = next((x for f in reversed(_maillots_snap(ici)) for x in json.load(open(f, encoding='utf-8')).get('maillots', []) if x.get('id') == i), None)
    if not m:
        return {'ok': False, 'erreur': 'introuvable'}
    p = A.charger_projet()
    if any(x.get('id') == i for x in p['maillots']):
        return {'ok': False, 'erreur': 'Ce maillot est déjà dans ta liste.'}
    p['maillots'].append(m)
    A.sauver_projet(p)
    r = construire() if construire else {'ok': True}
    return {'ok': bool(r.get('ok')), 'erreur': r.get('erreur'),
            'message': '« %s » est de retour (le mod « Mes maillots » est refait avec lui).' % (m.get('nom') or i)}


def restaurer(ici, cfg, id_, construire_maillots=None):
    sorte, _, quoi = str(id_).partition(':')
    try:
        if sorte == 'projet':
            return _restaurer_projet(ici, quoi)
        if sorte == 'retire':
            mod, _, st = quoi.partition('/')
            return _restaurer_creation(ici, cfg, os.path.basename(mod), os.path.basename(st))
        if sorte == 'maillot':
            return _restaurer_maillot(ici, quoi, construire_maillots)
    except (OSError, ValueError) as ex:
        return {'ok': False, 'erreur': str(ex)}
    return {'ok': False, 'erreur': 'élément inconnu'}


# ---------------------------------------------------------------- supprimer définitivement
def _effacer_maillot(ici, i):
    for f in _maillots_snap(ici):
        try:
            p = json.load(open(f, encoding='utf-8'))
        except (OSError, ValueError):
            continue
        reste = [m for m in p.get('maillots', []) if m.get('id') != i]
        if len(reste) != len(p.get('maillots', [])):
            p['maillots'] = reste
            json.dump(p, open(f, 'w', encoding='utf-8'), ensure_ascii=False, indent=2)
    tr = _fichier_sur(os.path.join(ici, 'maillots', 'travail'), i)
    if os.path.isdir(tr):
        effacer(tr)


def supprimer(ici, id_):
    """efface POUR DE BON (place libérée) ; -> octets libérés"""
    sorte, _, quoi = str(id_).partition(':')
    if sorte == 'projet':
        f = _fichier_sur(os.path.join(ici, 'projets', 'corbeille'), quoi + '.json')
        n = taille(f) if os.path.isfile(f) else 0
        if n:
            os.remove(f)
        return n
    if sorte == 'retire':
        mod, _, st = quoi.partition('/')
        d = _fichier_sur(os.path.join(ici, 'sortie', os.path.basename(mod), '_retires'), os.path.basename(st))
        n = effacer(d) if os.path.isdir(d) else 0
        r = os.path.dirname(d)
        if os.path.isdir(r) and not os.listdir(r):
            os.rmdir(r)
        return n
    if sorte == 'maillot':
        i = os.path.basename(quoi)
        try:
            actuels = {m.get('id') for m in json.load(open(os.path.join(ici, 'maillots', 'mes_maillots.json'), encoding='utf-8')).get('maillots', [])}
        except (OSError, ValueError):
            raise ValueError('liste des maillots illisible : rien n’est effacé')
        if i in actuels:                                 # un maillot de la liste : jamais
            raise ValueError('ce maillot est dans ta liste')
        tr = os.path.join(ici, 'maillots', 'travail', i)
        n = taille(tr) if os.path.isdir(tr) else 0
        _effacer_maillot(ici, i)
        return n
    raise ValueError('élément inconnu')


def vider(ici, cfg, ids=None):
    ids = ids if ids is not None else [x['id'] for x in lister(ici, cfg)['elements']]
    n, err = 0, []
    for i in ids:
        try:
            n += supprimer(ici, i)
        except (OSError, ValueError) as ex:
            err.append('%s : %s' % (i, ex))
    return {'ok': not err, 'libere': n, 'erreurs': err}


# ---------------------------------------------------------------- cache
def _garde_cache(nom):
    # + les catalogues d'une autre langue (cache/en, cache/es) : petits, et sans eux tout le jeu serait relu au démarrage
    return nom in GARDER_CACHE or nom.startswith('carte_') or (len(nom) == 2 and nom.isalpha())


def taille_cache(cache):
    t = g = 0
    for x in os.listdir(cache) if os.path.isdir(cache) else []:
        p = os.path.join(cache, x)
        if os.path.isdir(p):
            n = taille(p)
            t += n
            if _garde_cache(x):
                g += n
    return {'ok': True, 'total': t, 'garde': g, 'videable': t - g}


def vider_cache(cache):
    """efface les dossiers du cache (refaits au besoin : textures lues, cinématiques, copies des mods…) sauf le terrain et
    GARDER_CACHE ; les petits fichiers d'index (catalogues) restent : sans eux le prochain démarrage relirait tout le jeu"""
    n, bloques = 0, []
    for x in sorted(os.listdir(cache)) if os.path.isdir(cache) else []:
        p = os.path.join(cache, x)
        if not os.path.isdir(p) or _garde_cache(x):
            continue
        n += effacer(p)
        if os.path.exists(p):                       # fichier ouvert (utilisé en ce moment) : il reste
            bloques.append(x)
    try:
        from moteur import racines
        racines._memo.clear()                     # copies des mods : refaites à la prochaine ouverture
    except Exception:
        pass
    return {'ok': True, 'libere': n, 'bloques': bloques}
