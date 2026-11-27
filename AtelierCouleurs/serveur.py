"""Atelier Inazuma (ex-Atelier Couleurs) : serveur local (http://127.0.0.1:8765) + fenêtre d'app.
Onglets : Techniques (copie recolorée -> mod MesTechniques), Esprits guerriers et Totems (couleurs remplacées -> mod
MesEsprits), Maillots (ouvre l'Atelier Maillots).
Lancer : double-clic sur « Atelier Inazuma.bat » (ou python serveur.py). L'app s'ouvre dans sa propre fenêtre (Edge en
mode app, sans barre d'adresse) ; sinon dans le navigateur.
Lecture seule des fichiers du jeu ; les exports écrivent dans sortie/<mod> ; l'installation copie dans <jeu>/mods
(jeu fermé, sauvegarde avant)."""
import os, sys, json, struct, threading, webbrowser, traceback, mimetypes, subprocess, zlib, glob, datetime
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, unquote, parse_qs

ICI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ICI)
# lancé par « Atelier Inazuma.exe » (pythonw : pas de console) -> messages et erreurs dans cache/serveur.log
if sys.stdout is None or sys.stderr is None:
    os.makedirs(os.path.join(ICI, 'cache'), exist_ok=True)
    sys.stdout = sys.stderr = open(os.path.join(ICI, 'cache', 'serveur.log'), 'a', encoding='utf-8', buffering=1)
if __name__ != '__mp_main__':                    # version et date en tête de chaque lancement (journal à envoyer en cas de souci)
    try:
        import datetime as _dt
        print('===== Atelier Inazuma %s · %s =====' % (open(os.path.join(ICI, 'version.txt'), encoding='utf-8').read().strip(),
                                                    _dt.datetime.now().strftime('%d/%m/%Y %H:%M')))
    except OSError:
        pass
from moteur import g4, techniques, export, personnages, esprits, anim, modele, carte, son, jeu, mes_maillots, retouches, copies_persos, armures_copies, copies_tenues, copies_outfits, objets_jeu, coups, menus_jeu  # noqa: E402

from moteur import config_auto, langue  # noqa: E402
# config.json : trouvé tout seul au 1er lancement (jeu de base ou copie de dépôt : celui qui a les mods ; données extraites)
_F_CFG = os.path.join(ICI, 'config.json')
CFG = json.load(open(_F_CFG, encoding='utf-8')) if os.path.isfile(_F_CFG) else {}
_JEU_CHOISI = sys.argv[sys.argv.index('--jeu') + 1] if '--jeu' in sys.argv[:-1] else None   # dossier choisi dans le lanceur
if _JEU_CHOISI:
    CFG['jeu_dir'] = _JEU_CHOISI
CFG, _cfg_change = config_auto.completer(CFG, ICI)
_cfg_change = _cfg_change or bool(_JEU_CHOISI)


def sauver_cfg():
    garde = {k: v for k, v in CFG.items() if k not in ('outil_dir', 'lecture_directe')}
    if CFG.get('lecture_directe') or not config_auto._data_ok(CFG.get('data_dir')):
        garde.pop('data_dir', None)                    # dossier virtuel : jamais écrit dans config.json
    json.dump(garde, open(_F_CFG, 'w', encoding='utf-8'), ensure_ascii=False, indent=2)


if _cfg_change:
    sauver_cfg()
JEU_AU_DEMARRAGE = CFG.get('jeu_dir')            # (22/11) dossier du jeu lu par l'Atelier (lecture directe, mods des onglets)
try:                                             # (22/11) enabled.toml créé par un Atelier d'avant (que nos mods) : tous les mods
    _r_en = export.reparer_enabled(os.path.join(CFG.get('jeu_dir') or '', 'mods', 'enabled.toml'),     # éteints -> réparé
                                   os.path.join(CFG.get('sauvegardes_dir') or os.path.join(ICI, 'sauvegardes'), 'enabled_toml'))
    if _r_en:
        print(_r_en)
except Exception as _ex:
    print('enabled.toml :', _ex)
if not config_auto._data_ok(CFG.get('data_dir')):
    # pas de fichiers extraits : LECTURE DIRECTE dans les paquets du jeu (moteur/donnees_virtuelles.py)
    if CFG.get('jeu_dir') and os.path.isfile(os.path.join(CFG['jeu_dir'], 'data', 'cpk_list.cfg.bin')):
        from moteur import donnees_virtuelles  # noqa: E402
        CFG['data_dir'] = donnees_virtuelles.activer(CFG['jeu_dir'], os.path.join(ICI, 'cache', 'data_jeu'))
        CFG['lecture_directe'] = True
        print('lecture directe des paquets du jeu / reading the game packs directly :', CFG['jeu_dir'])
        if not os.path.isfile(os.path.join(ICI, 'cache', 'index_tx_chr.json')):
            print('1er lancement : préparation des index, quelques minutes (une seule fois)...\n'
                  'First run: building the indexes, a few minutes (only once)...')
    else:
        print('JEU INTROUVABLE / GAME NOT FOUND : mettre dans config.json "jeu_dir" = dossier du jeu (celui de nie.exe) '
              '/ set "jeu_dir" in config.json to the game folder (the one with nie.exe)')
        sys.exit(1)
langue.regler(CFG.get('langue', 'fr'))
CFG['outil_dir'] = ICI
CACHE = os.path.join(ICI, 'cache')
WEB = os.path.join(ICI, 'web')
os.makedirs(CACHE, exist_ok=True)
from moteur import series as _series   # noqa: E402


def cache_txt():
    """cache des catalogues de NOMS (un par langue : cache/ en français, cache/en en anglais)"""
    d = CACHE if langue.code() == 'fr' else os.path.join(CACHE, langue.code())
    os.makedirs(d, exist_ok=True)
    return d


def noms_lisibles(nom):
    """codes que le jeu remplace par des noms (<FST:GARCILDO>, <MNT:KINUNS2>…) -> « Garcildo », « Kinuns »"""
    import re as _re
    return _re.sub(r'<[A-Z]+:([A-Za-z0-9_-]+?)\d*>', lambda m: m.group(1).replace('_', ' ').capitalize(), nom)


CATALOGUES_EN_ERREUR = []


def _essayer(nom, fn, defaut):
    """(22/11, 2.0 chez un joueur : chara_base illisible -> « Le serveur de l'atelier n'a pas démarré ») un fichier du jeu
    illisible (modifié par un autre outil de mod…) ne bloque plus tout l'Atelier : ce catalogue reste vide, le journal dit
    lequel et pourquoi (traceback), la page le signale (/api/etat : catalogues_en_erreur)"""
    try:
        return fn()
    except Exception as ex:
        import traceback
        print('CATALOGUE ILLISIBLE / UNREADABLE CATALOGUE : %s (%s)' % (nom, ex))
        traceback.print_exc()
        CATALOGUES_EN_ERREUR.append('%s : %s' % (nom, ex))
        return defaut


def charger_catalogues():
    """techniques, Keshin, personnages, tout le jeu, séries : dans la langue choisie (FR / EN)"""
    global INDEX, PAR_CODE, PERSOS, PERSO_CODE, VIDEOS, JEU, JEU_CODE, SERIES
    CT = cache_txt()
    del CATALOGUES_EN_ERREUR[:]
    INDEX = _essayer('techniques', lambda: techniques.construire_index(CFG['data_dir'], CT), [])
    PAR_CODE = {t['code']: t for t in INDEX}
    PERSOS = _essayer('esprits / totems (chara_base)', lambda: personnages.construire(CFG['data_dir'], CT), [])
    # vidéos officielles des techniques (site zukan.inazuma.jp, relevé le 13/11/2026) : code -> adresse ; lues sur le site, rien n'est copié
    # (21/11) fourni avec l'Atelier (AtelierCouleurs/videos_officielles.json : des adresses seulement) ; avant : seulement dans
    # le cache de muku -> « Vidéo du jeu » sans vidéo chez tous les autres
    VIDEOS = {}
    for _f in (os.path.join(ICI, 'videos_officielles.json'), os.path.join(CACHE, 'videos_officielles.json')):
        try:
            VIDEOS = json.load(open(_f, encoding='utf-8'))
            break
        except (OSError, ValueError):
            pass
    PERSO_CODE = {p['code']: p for p in PERSOS}
    # (15/11/2026) tout le jeu : maillots, tenues, armures, personnages (têtes), objets — ouverts comme les esprits
    JEU = _essayer('tout le jeu (maillots, tenues, armures, têtes)', lambda: jeu.construire(CFG['data_dir'], CT, mes_maillots.catalogue(CFG)), {})
    # (15/11/2026) onglet Objets = les OBJETS DU JEU (inventaire) ; les modèles 3D d'objets passent en « objets3d », et les
    # accessoires portés (lunettes, casquettes… : EXMESH) vont dans Tenues (genre « Accessoire ») avec leur copie « nouveau joueur »
    def _accessoires_3d():
        import glob as _g
        from moteur.maillots.cfgbin import parse as _p
        parts = sorted(_g.glob(os.path.join(CFG['data_dir'], 'common', 'gamedata', 'character', 'chara_parts_*.cfg.bin')))[-1]
        return {v[0].split('/')[1] for k, v in _p(parts) if k == 'CHARA_PARTS_EXMESH_INFO' and v and isinstance(v[0], str) and v[0].startswith('_item/')}
    if 'objets3d' not in JEU:
        JEU['objets3d'] = JEU.get('objets', [])
        _acc = _essayer('accessoires (chara_parts)', _accessoires_3d, set())
        _accs = [dict(x, nom='Accessoire ' + x['code'], genre='Accessoire') for x in JEU['objets3d'] if x['code'] in _acc]
        _essayer('noms des accessoires', lambda: jeu.nommer_accessoires(_accs, CFG['data_dir'], CT), None)   # (28/11) par couleurs
        JEU['tenues'] = JEU.get('tenues', []) + _accs
    JEU['objets'] = _essayer('objets', lambda: objets_jeu.construire(CFG['data_dir'], CT), [])
    # (23/11) maillots : noms dans la langue de l'Atelier (cache/index_jeu.json garde ceux du catalogue d'origine, en français)
    try:
        from moteur.maillots import atelier_mod as _am
        _nm = _am.noms_maillots(CFG['data_dir'])
        for _x in JEU.get('maillots', []):
            if _nm.get(_x.get('cle_maillot')):
                _x['nom'] = _nm[_x['cle_maillot']]
    except Exception as _ex:
        print('noms des maillots :', _ex)
    # (21/11) noms du jeu avec balises (« Maillot <FST:GARCILDO> Team ») : lisibles, comme dans l'Atelier Maillots
    for _l in JEU.values():
        if isinstance(_l, list):
            for _x in _l:
                if isinstance(_x, dict) and '<' in str(_x.get('nom') or ''):
                    _x['nom'] = noms_lisibles(_x['nom'])
    JEU_CODE = {(c, x['code']): x for c, l in JEU.items() if isinstance(l, list) for x in l}
    # (17/11/2026) SÉRIE de chaque élément (filtres IE1 … Victory Road) : moteur/series.py (têtes : dossier _face ; techniques,
    # esprits, totems : séries des personnages dont une carte les a ; armure ka00XY01 : celle de son esprit k000XY0)
    try:
        SERIES = _series.construire(CFG['data_dir'], CT)
    except Exception as _ex:
        print('séries :', _ex); SERIES = {'perso': {}, 'coup': {}, 'modele': {}}


SERIE_CODE = {'01': 'IE1', '02': 'IE2', '03': 'IE3', '04': 'GO 1', '05': 'GO 2', '06': 'GO 3', '07': 'Ares', '08': 'Orion', '11': 'Victory Road'}


def _depuis(l, premiere):
    """séries à partir de la première où ce genre existe (pas d'esprit en IE1 : un personnage dont la TÊTE vient d'IE1 peut
    avoir un esprit sur sa carte de Victory Road ; 17/11/2026, retour de muku « Fou blanc en IE1 »)"""
    o = _series.ORDRE
    return [x for x in l if o.index(x) >= o.index(premiere)]


def series_de(cat, x):
    """(17/11/2026) séries d'un élément de l'Atelier (filtres IE1 … Victory Road)"""
    import re as _re
    base = x.get('base') if x.get('mod') else None             # contenu d'un mod : la série de ce qu'il copie
    if cat == 'techniques':
        return SERIES['coup'].get(base or x['code'], [])
    if cat in ('esprits', 'totems'):
        return _depuis(_series.de_modele(SERIES, base or x['code']), 'GO 3' if x.get('genre') == 'Totem' else 'GO 1')
    if cat == 'personnages':
        s = _series.de_tete(x.get('chemin_jeu') or x.get('chemin') or '')
        return [s] if s else []
    if cat == 'armures':                                        # celle de son esprit ; armures d'esprits depuis GO 2
        m = _re.match(r'ka(\d{6})', os.path.basename(x.get('chemin_jeu') or x['code'])[:8])     # ka000101 -> k000010
        return _depuis(_series.de_modele(SERIES, 'k0%s' % m.group(1)[:5]), 'GO 2') if m else []
    if cat in ('tenues', 'maillots'):
        # LU (même numérotation que les dossiers des têtes chr/_face/01_IE1 … 11_VICTORY) : maillot u<NN>…, ex. u081201 Ombre
        # d'Orion -> 08 = Orion ; sinon (tenues, chaussures…) la série de ceux qui la portent
        c = str(x.get('maillot_du_jeu') or base or x['code'])
        c = c[4:] if c.startswith('uni_') else c
        m = _re.match(r'u(\d\d)\d{4}', c)
        if m and m.group(1) in SERIE_CODE:
            return [SERIE_CODE[m.group(1)]]
        if x.get('mod'):
            return []
        parts = (x.get('chemin') or '').split('|')
        t = parts[1] if len(parts) > 1 else ''
        t = t[len('dx11/chr/'):] if t.startswith('dx11/chr/') else t
        return SERIES.get('tex', {}).get(t, [])
    return []


def marquer_series():
    for _t in INDEX:
        _t['series'] = series_de('techniques', _t)
    for _p in PERSOS:
        _p['series'] = series_de('esprits', _p)
    for _c in ('armures', 'personnages', 'tenues', 'maillots'):
        for _x in JEU.get(_c, []):
            _x['series'] = series_de(_c, _x)


if __name__ != '__mp_main__':                    # (pas dans les processus de travail du décodage des textures)
    charger_catalogues()
    marquer_series()
else:                                            # processus de travail (copies, encodage) : catalogues VIDES mais définis,
    INDEX, PAR_CODE, PERSOS, PERSO_CODE, VIDEOS = [], {}, [], {}, {}    # sinon la suite du module plante et la
    JEU, JEU_CODE, SERIES = {}, {}, {}                                   # création de copie attend sans fin
_verrou_mods = threading.Lock()
MODS = {'liste': [], 'quand': 0}
MOD_CODE = {}                         # code -> entrée (tout ce qui vient des mods, tous onglets)


# (22/11, demande d'un joueur : « importer sa propre police d'écriture ») polices importées dans l'Atelier : dossier à soi
# (jamais copié dans le partage), servies comme celles de Windows (/police/<fichier>) ; fichier « perso_<nom>.ttf|otf »
POLICES_PERSO = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'polices')


def polices_perso():
    try:
        fs = sorted(f for f in os.listdir(POLICES_PERSO) if f.lower().endswith(('.ttf', '.otf')) and f.startswith('perso_'))
    except OSError:
        return []
    return [{'fichier': f, 'nom': os.path.splitext(f)[0][6:]} for f in fs]


def importer_police(nom, data_url):
    import base64, re
    ext = os.path.splitext(str(nom or ''))[1].lower()
    if ext not in ('.ttf', '.otf'):
        return {'ok': False, 'erreur': 'il faut un fichier .ttf ou .otf'}
    try:
        b = base64.b64decode(str(data_url).split(',', 1)[-1])
    except (ValueError, TypeError):
        return {'ok': False, 'erreur': 'fichier illisible'}
    if b[:4] not in (b'\x00\x01\x00\x00', b'OTTO', b'true') or len(b) > 30 * 1024 * 1024:
        return {'ok': False, 'erreur': "ce n'est pas une police TrueType / OpenType (ou plus de 30 Mo)"}
    tige = re.sub(r'[^\w\- ]', '', os.path.splitext(os.path.basename(str(nom)))[0]).strip()[:60] or 'police'
    os.makedirs(POLICES_PERSO, exist_ok=True)
    f = 'perso_' + tige + ext
    open(os.path.join(POLICES_PERSO, f), 'wb').write(b)
    return {'ok': True, 'fichier': f, 'nom': tige}


def polices_du_pc():
    """{nom du fichier en minuscules: chemin} des polices .ttf / .otf de Windows ET de celles installées pour l'utilisateur
    seul (%LOCALAPPDATA%\\Microsoft\\Windows\\Fonts) ; les polices d'Office (Cooper Black, Jokerman…) ne sont pas partout"""
    out = {}
    for d in (os.path.join(os.environ.get('WINDIR', r'C:\Windows'), 'Fonts'),
              os.path.join(os.environ.get('LOCALAPPDATA', ''), 'Microsoft', 'Windows', 'Fonts'), POLICES_PERSO,
              os.path.join(WEB, 'polices')):                 # (24/11) polices livrées avec l'Atelier (Armure Style Color)
        try:
            for f in os.listdir(d):
                if f.lower().endswith(('.ttf', '.otf')):
                    out.setdefault(f.lower(), os.path.join(d, f))
        except OSError:
            pass
    return out


def _sig_mods():
    """signature du dossier mods : change quand un mod est installé, retiré, activé ou modifié (dates des dossiers)"""
    racine = os.path.join(CFG.get('jeu_dir') or '', 'mods')
    sig = []
    for d, ds, fs in os.walk(racine):
        try:
            sig.append((d, os.stat(d).st_mtime_ns))
            if d == racine:
                sig += [(f, os.stat(os.path.join(d, f)).st_mtime_ns) for f in fs]
        except OSError:
            pass
    return hash(tuple(sig))


def mods_liste(cat=None, frais=False):
    """(17/11/2026) TOUT ce que les mods du dossier <jeu>/mods apportent, activés ou non, rangé dans l'onglet de son type :
    modèles (moteur/mods_jeu.py : armures, tenues, têtes) et contenu des .toml (moteur/mods_contenu.py : objets
    d'inventaire, maillots, techniques, esprits guerriers) ; relu au plus toutes les 10 s (un mod installé pendant que
    l'Atelier est ouvert apparaît) ; ~2 s (25 s la 1re fois : index des textures du jeu)"""
    import time
    from moteur import mods_jeu, mods_contenu
    with _verrou_mods:
        if frais or (time.time() - MODS['quand'] > 10 and _sig_mods() != MODS.get('sig')):
            MODS['sig'] = _sig_mods()
            try:
                l = [x for x in mods_jeu.construire(CFG, CACHE) if x.get('cat')]
                c = mods_contenu.construire(CFG, CACHE, mods_jeu._actifs(os.path.join(CFG['jeu_dir'], 'mods')), JEU.get('objets', []),
                                            PERSOS, INDEX, JEU.get('maillots', []))
                l += [x for v in c.values() for x in v]
            except Exception as ex:
                traceback.print_exc(); print('contenu des mods :', ex); l = MODS['liste']
            for x in l:
                x['series'] = series_de(x['cat'], x)
            for x in MODS['liste']:
                JEU_CODE.pop((x['cat'], x['code']), None)
            JEU_CODE.update({(x['cat'], x['code']): x for x in l})
            MOD_CODE.clear(); MOD_CODE.update({x['code']: x for x in l})
            MODS['liste'], MODS['quand'] = l, time.time()
        return [x for x in MODS['liste'] if cat is None or x['cat'] == cat]


def sans_chemins(l):
    """entrées envoyées à la page : sans les chemins sur le disque"""
    return [{k: v for k, v in x.items() if k not in ('md', 'tx', 'tx20', 'dossier_abs')} for x in l]


def entree_mod(code):
    if code not in MOD_CODE:
        mods_liste(frais=True)
    return MOD_CODE.get(code)


if __name__ != '__mp_main__':        # (23/11) pas dans les processus de travail (catalogues vides : KeyError 'modele' au journal)
    threading.Thread(target=mods_liste, kwargs={'frais': True}, daemon=True).start()   # (17/11/2026) lu dès le démarrage


def technique_invocation(code):
    """(23/11, demande de muku : « la preview des Keshin = l'animation d'invocation en match ») « invoc_<copie> » : la
    scène d'invocation d'une copie d'esprit guerrier (celle de l'élément choisi, sinon celle de l'original ; ses scènes sont
    copiées dans sortie/MesEsprits sous le code de la copie), lue dans la racine superposée de la SORTIE de l'Atelier
    (« atelier:MesEsprits » : pas besoin d'installer), l'esprit <ASSIGN> = la copie"""
    copie, _, choix = code.split('_', 1)[1].partition('~')
    c = esprits.registre(os.path.join(ICI, 'sortie', 'MesEsprits')).get(copie)
    if not c:
        return None
    inv = c.get('invocation') or {}
    donneur = inv.get('esprit') if inv.get('etat') == 'emprunt' else None
    if code.startswith('armure_') and choix:         # (23/11) fiche d'armure : mise en armure choisie / de l'élément, avant « Enregistrer »
        from moteur import armures_copies
        a = armures_copies.registre(CFG).get(copie)
        if not a:
            return None
        k0, scene_c = armures_copies.esprit_et_scene(CFG['data_dir'], a['was'])
        donneur = None if scene_c == 'ev81_00010' else k0
        if choix.startswith('@'):
            pl = armures_copies.plan_mise(CFG, dict(a, mise=None, stats=dict(a.get('stats') or {}, element=choix[1:])), copie)
            if pl:
                scene_c, donneur = pl['scene'], pl['esprit']
        else:
            scene_c, _, donneur = choix.partition('~')
        if not scene_c:
            return None
        return {'code': code, 'nom': a.get('nom'), 'genre': 'Invocation', 'cinematique': scene_c, 'racine_mod': 'atelier:MesEsprits',
                'vrfw_event': {'assigned': [copie]}, 'anim_assign': donneur, 'couleur_tir': 0, 'invocation_de': copie}
    if choix.startswith('@'):                        # (23/11) « Selon l'élément » : l'invocation de CET élément, avant « Enregistrer »
        essai = dict(c, stats=dict(c.get('stats') or {}, element=choix[1:]))
        essai.pop('invocation', None)                # (comme regler_stats : plan_invocation sur la copie modifiée)
        try:
            pl = esprits.plan_invocation(CFG, essai)
        except Exception as ex:
            print('invocation :', ex); pl = None
        if pl:
            scene_c, donneur = pl['scene'], pl.get('esprit')
        else:                                        # élément d'origine (ou pas un esprit wk) : l'invocation de l'original
            scene_c, donneur = esprits.invocation_du_jeu(CFG['data_dir'], c.get('technique'))[1], None
        if not scene_c:
            return None
        return {'code': code, 'nom': c.get('nom'), 'genre': 'Invocation', 'cinematique': scene_c, 'racine_mod': 'atelier:MesEsprits',
                'vrfw_event': {'assigned': [copie]}, 'anim_assign': donneur, 'couleur_tir': 0, 'invocation_de': copie}
    if choix:                                        # (23/11) aperçu d'une apparition choisie, avant « Enregistrer »
        scene_c, _, donneur = choix.partition('~')
        if scene_c in ('ev83_00010', 'ev83_00010_1'):                # (23/11) totem : la partie où il apparaît
            scene_c = 'ev83_00010_2'
        return {'code': code, 'nom': c.get('nom'), 'genre': 'Invocation', 'cinematique': scene_c, 'racine_mod': 'atelier:MesEsprits',
                'vrfw_event': {'assigned': [copie]}, 'anim_assign': donneur, 'couleur_tir': 0, 'invocation_de': copie}
    if code.startswith('armure_'):                   # (23/11) « armure_<copie> » : sa mise en armure (vérifications)
        from moteur import armures_copies
        e = armures_copies.registre(CFG).get(copie)
        scene = armures_copies.esprit_et_scene(CFG['data_dir'], e['was'])[1] if e else None
        pl = armures_copies.plan_mise(CFG, e, copie) if e else None      # (23/11) mise en armure enregistrée dans la fiche
        if pl and pl.get('scene') and pl.get('esprit'):
            scene, donneur = pl['scene'], pl['esprit']
            return {'code': code, 'nom': c.get('nom'), 'genre': 'Invocation', 'cinematique': scene, 'racine_mod': 'atelier:MesEsprits',
                    'vrfw_event': {'assigned': [copie]}, 'anim_assign': donneur, 'couleur_tir': 0, 'invocation_de': copie}
    else:
        scene = (c.get('invocation') or {}).get('scene') or esprits.invocation_du_jeu(CFG['data_dir'], c.get('technique'))[1]
        # (23/11, totems) invocation des totems = ev83_00010_1 (l'aura du joueur) + ev83_00010_2 (le TOTEM apparaît, plan c0020,
        # VU dans le lecteur du jeu : loup bleu de la copie) -> l'aperçu joue la 2e partie
        if scene in ('ev83_00010', 'ev83_00010_1'):
            scene = 'ev83_00010_2'
    if not scene:
        return None
    return {'code': code, 'nom': c.get('nom'), 'genre': 'Invocation', 'cinematique': scene, 'racine_mod': 'atelier:MesEsprits',
            'vrfw_event': {'assigned': [copie]}, 'anim_assign': donneur if code.startswith('invoc_') else None, 'couleur_tir': 0, 'invocation_de': copie}


def couleurs_apparition(demande):
    """(25/11, demande de muku : « modifier la couleur de l'animation quand on invoque un esprit guerrier ») COULEURS DE
    L'APPARITION d'une copie d'esprit guerrier, faites dans l'éditeur sur « invoc_<copie> » (objets d'effet de sa scène
    d'invocation, auras). Écrites comme ZanUltimateMod (Lancelot ev80_88500, marche en jeu) : la scène À PART de la copie
    (esprits.plans_apparition) est livrée avec le nom de chaque objet recoloré remplacé sur place (même longueur) et un
    [[recolor]] crée la copie de l'objet (export._couleurs, le même code que les techniques). Jamais sur la scène du jeu
    (elle sert à tous les esprits de l'élément). Le modèle de l'esprit lui-même n'est pas pris ici (ses couleurs = sa copie)."""
    copie = os.path.basename(str(demande.get('copie') or ''))
    sortie = os.path.join(ICI, 'sortie', 'MesEsprits')
    reg = esprits.registre(sortie)
    c = reg.get(copie)
    if not c:
        return {'ok': False, 'erreur': 'esprit guerrier inconnu : ' + copie}
    pl = esprits.plans_apparition(CFG, reg).get(copie) or {}
    if not pl.get('scene') or not pl.get('ev'):
        return {'ok': False, 'erreur': 'Cette apparition n’a pas encore de scène à part (totem, ou esprit sans invocation à lui) : '
                                       'ses couleurs ne peuvent pas encore être changées sans toucher celles des autres.'}
    d = details('invoc_' + copie)
    if not d or d.get('cinematique') != pl['scene']:
        return {'ok': False, 'erreur': 'L’apparition ouverte (%s) n’est pas celle enregistrée (%s) : « Enregistrer » d’abord la fiche de '
                                       'l’esprit, puis rouvre ses couleurs.' % ((d or {}).get('cinematique'), pl['scene'])}
    modeles = {o['acteur'] for o in d.get('objets_details') or [] if o.get('modeleActeur')}
    objets = {a: o for a, o in (demande.get('objets') or {}).items() if a not in modeles}
    # l'aperçu lit la scène dans la sortie (« racine:atelier:MesEsprits|chemin ») : en jeu, le chemin du jeu
    propre = lambda o: dict(o, chemin=o['chemin'].split('|', 1)[1]) if str(o.get('chemin', '')).startswith('racine:') else o
    d = dict(d, objets=[propre(o) for o in d.get('objets') or []], objets_details=[propre(o) for o in d.get('objets_details') or []])
    auras = demande.get('auras') or {}
    rapport = []
    if not objets and not auras:
        c.pop('couleurs_apparition', None)
        rapport.append('couleurs de l’apparition retirées (celles du jeu)')
    else:
        nom = 'apparition_' + copie
        ev_nom = pl['ev'][:5] + pl['ev'][6:10]            # 4 derniers chiffres de la scène à part (uniques) : noms des copies
        for a in objets:
            cp = export.copie_objet(a, ev_nom)
            if glob.glob(os.path.join(CFG['data_dir'], 'common', 'effect', '**', cp), recursive=True):
                return {'ok': False, 'erreur': 'nom de copie %s déjà pris dans le jeu' % cp}
        shutil_ = __import__('shutil')
        # images : l'ancien dossier mis de côté, remis si l'enregistrement échoue (le registre garde alors les anciennes couleurs)
        d_img = os.path.join(sortie, 'assets', 'images', 'fx', nom)
        d_bak = d_img + '.ancien'
        shutil_.rmtree(d_bak, ignore_errors=True)
        if os.path.isdir(d_img):
            os.replace(d_img, d_bak)
        try:
            e, persos = export._couleurs(CFG, {'nom': c.get('nom') or copie, 'objets': objets, 'auras': auras}, d, nom, ev_nom, pl['scene'], sortie, rapport)
            texte = '\n'.join(e) + '\n'
            import tomllib as _tl
            cmds = [x for x in _tl.loads('schema = "VRFW.effect/1"\n' + texte).get('event_command', []) if x.get('event') == ev_nom]
            remplacer = {'evt': {}, 'eff': {}, 'snd': {}}
            export.remplacements_commandes(CFG, cmds, pl['scene'], remplacer, rapport)
            # EFFET COMMUN (ega0001…) : chargé, créé et joué PAR SON NOM (commandes à une valeur, que remplacements_commandes
            # laisse) -> le nom entier remplacé partout dans la scène par celui de sa copie (même longueur, egz…)
            for x in cmds:
                a_, s_ = x.get('args') or [], x.get('set') or []
                if len(a_) == 1 and s_ and all(v == s_[0] for v in s_) and s_[0] != a_[0] and len(s_[0]) == len(a_[0]):
                    remplacer[x.get('list') or 'eff'][a_[0]] = s_[0]
                    if 'effet commun %s -> %s' % (a_[0], s_[0]) not in rapport:
                        rapport.append('effet commun %s -> %s' % (a_[0], s_[0]))
            import re as _re
            sans = _re.sub(r'\n\[\[event_command\]\]\nevent = "%s"\n(?:[^\[\n][^\n]*\n)*' % _re.escape(ev_nom), '\n', '\n' + texte)
            if not any(remplacer.values()):
                raise ValueError('aucun objet recoloré n’a pu être branché dans la scène d’apparition')
        except Exception as ex:
            shutil_.rmtree(d_img, ignore_errors=True)
            if os.path.isdir(d_bak):
                os.replace(d_bak, d_img)
            traceback.print_exc()
            return {'ok': False, 'erreur': str(ex) or ex.__class__.__name__, 'rapport': rapport}
        shutil_.rmtree(d_bak, ignore_errors=True)
        c['couleurs_apparition'] = {'scene': pl['scene'], 'ev': pl['ev'], 'effets': sans.strip(), 'remplacer': remplacer,
                                    'date': datetime.datetime.now().isoformat(timespec='seconds')}
        rapport.insert(0, 'couleurs de l’apparition de %s : scène à part %s (copie de %s)' % (c.get('nom') or copie, pl['ev'], pl['scene']))
    reg[copie] = c
    esprits.ecrire_vrfw(CFG, sortie, reg)
    json.dump(reg, open(os.path.join(sortie, 'outil_esprits.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    rapport.append('pas encore dans le jeu : « Installer » (Mes créations)')
    return {'ok': True, 'dossier': sortie, 'rapport': rapport}


def _png_url(f):
    import base64 as _b
    return 'data:image/png;base64,' + _b.b64encode(open(f, 'rb').read()).decode() if f and os.path.isfile(f) else None


def _entree_cosmetique(mod, code):
    """(26/11) l'entrée d'une création cosmétique : (registre, clé, entrée, enregistrer())"""
    from moteur import objets_jeu, copies_outfits
    if mod == 'MesObjets':
        reg = objets_jeu.registre(CFG)
        f = os.path.join(objets_jeu._sortie(CFG), 'outil_objets.json')
        return reg, code, reg.get(code), lambda: (json.dump(reg, open(f, 'w', encoding='utf-8'), ensure_ascii=False, indent=1), objets_jeu.ecrire(CFG, reg))
    if mod == 'MesTenues':
        reg = copies_outfits.registre(CFG)
        cle = code if code in reg else next((k for k, e in reg.items() if e.get('modele') == code), None)
        f = os.path.join(copies_outfits._sortie(CFG), 'outil_tenues.json')
        return reg, cle, reg.get(cle) if cle else None, lambda: (json.dump(reg, open(f, 'w', encoding='utf-8'), ensure_ascii=False, indent=1), copies_outfits.ecrire(CFG, reg))
    if mod == 'MesMaillots':
        A = mes_maillots.A
        p = A.charger_projet()
        m = next((x for x in p['maillots'] if x['id'] == code), None)
        return p, code, m, lambda: A.sauver_projet(p)
    return None, None, None, None


def _icone_tenue(e):
    from moteur import copies_outfits
    return os.path.join(copies_outfits._sortie(CFG), 'content', 'images', 'menu', '200_icon', '02_icon_item', 'mes_tenues_icones', str(e.get('icone')) + '.png')


def cosmetique_infos(mod, code):
    """(26/11, demande de muku) ÉTAPE « COSMÉTIQUE » des objets, tenues et maillots (comme « En attente de stats » pour les
    techniques) : ce qui s'y règle -> {prix, icone, embleme (data URL ou None), fait}"""
    reg, cle, e, _ = _entree_cosmetique(mod, code)
    if e is None:
        return {'ok': False, 'erreur': 'création inconnue'}
    out = {'ok': True, 'mod': mod, 'prix': e.get('prix'), 'fait': bool(e.get('cosmetique_ok')), 'icone': None, 'embleme': None,
           'boutique': 'general', 'famille': None}
    if mod == 'MesObjets':                          # (26/11) aperçu façon boutique : l'icône (recolorée, sinon celle de l'original)
        from moteur import objets_jeu
        # (26/11, muku : « fais tous les menus ») onglet de la boutique = famille de l'objet d'origine (item_config) ; les
        # équipements sont vendus à la boutique d'entraînement (objets_jeu.ecrire), le reste à la boutique générale
        try:
            o = next((x for x in objets_jeu.construire(CFG['data_dir'], CACHE) if x.get('code') == e.get('base')), None)
            out['famille'] = o.get('famille') if o else None
        except Exception as ex:
            print('famille de l’objet :', ex)
        out['boutique'] = 'entrainement' if out['famille'] in objets_jeu.ENTRAINEMENT else 'general'
        # (27/11) « Modifier » d'une copie : ses réglages (bonus, synergie) et ses textes reviennent dans la création
        out.update(nom=e.get('nom'), description=e.get('description'), stats=e.get('stats'), synergie=e.get('synergie'), rarete=e.get('rarete'), max=e.get('max'))
        try:
            o_ = next((x for x in objets_jeu.construire(CFG['data_dir'], CACHE) if x.get('code') == e.get('base')), None)
            out['dessin'] = bool(o_ and objets_jeu.icone_remplacable(o_))      # (27/11) tactiques : icône de la tactique, pas à dessiner
            if o_:                       # (27/11, muku) réglages de l'étape Cosmétique : ceux de l'original (unique, choix, bonus, synergie)
                dd = objets_jeu.details(CFG, CACHE, o_)
                out['reglages'] = {k: dd.get(k) for k in ('commun', 'equipement', 'synergie')}
                if out['reglages'].get('commun'):
                    out['reglages']['commun'] = dict(out['reglages']['commun'], refus=None)
        except Exception:
            out['dessin'] = True
        out['nom_embleme'] = None
        f = os.path.join(objets_jeu._sortie(CFG), 'content', 'images', 'menu', '200_icon', '02_icon_item', 'mesobjets_icones', str(e.get('icone')) + '.png')
        if e.get('mode_icone') == 'fichier':                 # (27/11) icône en fichier à part (emblème, plaque…) : son aperçu
            f = os.path.join(CFG['outil_dir'], 'cache', 'icones_objets', 'MesObjets~' + cle + '.png')
        if not os.path.isfile(f):
            try:
                import re
                o = next((x for x in objets_jeu.construire(CFG['data_dir'], CACHE) if x.get('code') == e.get('base')), None)
                if o and objets_jeu.icone(CFG['data_dir'], CACHE, o):
                    f = os.path.join(CACHE, 'icones_objets', re.sub(r'[^\w~.-]', '_', o['code']) + '.png')
            except Exception as ex:
                print('icône de l’objet :', ex)
        out['icone'] = _png_url(f)
    elif mod == 'MesTenues':
        out['icone'] = _png_url(_icone_tenue(e))
    elif mod == 'MesMaillots':
        out['icone'], out['embleme'] = _png_url(e.get('icone')), _png_url(e.get('embleme'))
        # nom de l'objet emblème tel que l'écrit le mod (moteur/maillots/atelier_mod.py) : « Emblème <nom sans Maillot> »
        import re as _re
        court = _re.sub(r'^(Maillot|Tenue)\s+', '', e.get('nom') or '')
        out['nom_embleme'] = {'fr': 'Emblème ' + court, 'en': court + ' crest', 'es': court + ' crest'}
    return out


def regler_cosmetique(d):
    """(26/11) « Enregistrer » (prix, icône, emblème) ou « Garder » de l'étape Cosmétique : la création passe dans Terminées.
    Objet : le prix (son icône EST son visuel, recolorée dans l'éditeur) ; tenue : prix + icône (256 × 256) ; maillot : prix +
    icône de boutique + emblème (le mod des maillots est reconstruit, comme « Ajouter au mod »)."""
    mod, code = str(d.get('mod') or ''), str(d.get('code') or '')
    reg, cle, e, sauver = _entree_cosmetique(mod, code)
    if e is None:
        return {'ok': False, 'erreur': 'création inconnue'}
    rapport = []
    if mod == 'MesTenues' and d.get('icone_auto') and d.get('icone'):
        # (27/11) icône « mannequin » faite toute seule juste après « Créer la tenue » : écrite, mais l'étape Cosmétique n'est pas
        # validée (la création reste « En attente : Cosmétique ») et une icône dessinée par muku n'est jamais remplacée
        if e.get('icone_perso'):
            return {'ok': True, 'rapport': ['icône dessinée gardée']}
        f = _icone_tenue(e); os.makedirs(os.path.dirname(f), exist_ok=True)
        import base64 as _b
        open(f, 'wb').write(_b.b64decode(d['icone'].split(',', 1)[1]))
        w, h, rows = g4.images.lire_png(f)
        if (w, h) != (256, 256):
            g4.images.ecrire_png(f, 256, 256, g4.images.redimensionner(w, h, rows, 256, 256))
        e['icone_auto'] = True; sauver()
        return {'ok': True, 'rapport': ['icône automatique (mannequin) écrite']}
    if not d.get('garder'):
        if d.get('prix') not in (None, ''):
            e['prix'] = max(1, int(d['prix'])); rapport.append('prix : %d' % e['prix'])
        if mod == 'MesTenues' and d.get('icone'):
            f = _icone_tenue(e); os.makedirs(os.path.dirname(f), exist_ok=True)
            import base64 as _b
            open(f, 'wb').write(_b.b64decode(d['icone'].split(',', 1)[1]))
            w, h, rows = g4.images.lire_png(f)
            if (w, h) != (256, 256):
                g4.images.ecrire_png(f, 256, 256, g4.images.redimensionner(w, h, rows, 256, 256))
            e['icone_perso'] = True; rapport.append('icône changée')
        if mod == 'MesObjets':                          # (27/11, muku) les réglages se font ici (comme « Régler les stats »)
            from moteur import objets_jeu
            try:
                rapport += objets_jeu.appliquer_reglages(CFG, e, d)
            except ValueError as ex:
                return {'ok': False, 'erreur': str(ex)}
        if mod == 'MesMaillots' and d.get('sans_embleme') and e.get('embleme'):
            # (27/11, muku : « un maillot ne fait pas forcément un emblème ») emblème retiré : le mod n'écrit plus l'objet emblème
            # (atelier_mod : « if m.get('embleme') and os.path.exists(...) »)
            e['embleme'] = None; rapport.append('emblème retiré (maillot vendu sans emblème)')
        if mod == 'MesMaillots':
            for k in ('icone', 'embleme'):
                if d.get(k):
                    mes_maillots._ecrire(e, k, d[k]); rapport.append(('icône' if k == 'icone' else 'emblème') + ' changé' + ('e' if k == 'icone' else ''))
    e['cosmetique_ok'] = True
    sauver()
    if mod == 'MesMaillots' and not d.get('garder'):            # « Garder » : rien ne change dans le mod
        r = mes_maillots.construire(CFG)
        rapport.append('mod des maillots reconstruit (en cours)' if r.get('ok') else 'mod des maillots : ' + str(r.get('erreur')))
    # (27/11, essai de tous les types) objets et tenues : le MOD est réécrit (avant : le nouveau prix restait dans le registre de
    # l'Atelier, la boutique du mod gardait l'ancien jusqu'au prochain « Créer »)
    if mod == 'MesObjets' and not d.get('garder'):
        from moteur import objets_jeu
        if d.get('icone'):                                   # icône dessinée dans la boutique : écrite comme à la création
            o = next((x for x in objets_jeu.construire(CFG['data_dir'], CACHE) if x.get('code') == e.get('base')), None)
            if o and o.get('icone'):
                r = objets_jeu.exporter(CFG, {'cle': cle, 'nom': e.get('nom'), 'description': e.get('description'), 'prix': e.get('prix'), 'icone': d['icone']}, o)
                rapport += (r.get('rapport') or [])[1:] if r.get('ok') else ['icône : ' + str(r.get('erreur'))]
            else:
                rapport.append('icône : cet objet n’a pas d’image dans le jeu')
        else:
            objets_jeu.ecrire(CFG, objets_jeu.registre(CFG)); rapport.append('mod « Mes objets » réécrit')
    if mod == 'MesTenues' and not d.get('garder'):
        from moteur import copies_outfits
        copies_outfits.ecrire(CFG, copies_outfits.registre(CFG)); rapport.append('mod « Mes tenues » réécrit')
    rapport.insert(0, ('valeurs gardées' if d.get('garder') else 'cosmétique enregistrée') + ' : « %s » passe dans Terminées' % (e.get('nom') or code))
    return {'ok': True, 'rapport': rapport}


def technique(code):
    """technique du jeu ou d'un mod (17/11/2026)"""
    t = PAR_CODE.get(code) or entree_mod(code) or (technique_invocation(code) if str(code).startswith(('invoc_', 'armure_')) else None)
    if t is None:
        raise KeyError(code)
    return t


def racine_de(t):
    """(17/11/2026) dossier « data » où lire la cinématique d'une technique : celui du jeu, ou la RACINE SUPERPOSÉE du mod qui
    a ses fichiers (moteur/racines.py : jeu + fichiers du mod, sans rien copier du jeu ni rien modifier)"""
    m = t.get('racine_mod') or t.get('mod_effets')         # (17/11/2026) + le mod de la technique : ses objets .glb convertis
    if m:                                                   # (dôme vert de Spectre chrono) sont dans sa racine
        from moteur import racines
        r = racines.racine(CFG, CACHE, m)
        if r:
            return r
    return CFG['data_dir']


def racine_avec_modele(code):
    """(17/11/2026) racine superposée du mod qui contient le modèle de personnage « code » (assets/chr/…/<code>/<code>.g4pkm),
    ou None ; les mods sont essayés par ordre alphabétique"""
    import glob as _g, re
    from moteur import racines
    mods_dir = os.path.join(CFG.get('jeu_dir') or '', 'mods')
    if not code or not re.fullmatch(r'[\w~-]+', str(code)):
        return None
    # (23/11) copie d'esprit de l'Atelier : sa version de la SORTIE d'abord (la dernière faite, même pas encore installée)
    for mod in ('MesEsprits', 'MesPersonnages'):
        if _g.glob(os.path.join(ICI, 'sortie', mod, 'assets', 'chr', '**', code, code + '.g4pkm'), recursive=True):
            return racines.racine(CFG, CACHE, 'atelier:' + mod)
    if not os.path.isdir(mods_dir):
        return None
    for mod in sorted(os.listdir(mods_dir), key=str.lower):
        if _g.glob(os.path.join(mods_dir, mod, 'assets', 'chr', '**', code, code + '.g4pkm'), recursive=True):
            return racines.racine(CFG, CACHE, mod)
    # (17/11/2026) modèle .glb d'un mod (VRFW.model/1, ex. Michael astral k002093) : converti au format du jeu
    from moteur import glb_vrfw
    for m in glb_vrfw.trouver(CFG):
        if os.path.basename(str(m['def'].get('target', ''))).rsplit('.', 1)[0] == code:
            return racines.racine(CFG, CACHE, m['mod'])
    return None


def modele_remplace(code):
    """(17/11/2026) [[character]] base.name = code, new_model.cells.skeleton_path = autre modèle : en jeu, « code » a
    l'apparence de cet autre modèle (Mukuro : k002090 -> k002093 Michael astral) ; renvoie l'autre code ou None"""
    from moteur.mods_contenu import _tomls, _liste
    for m, f, t in _tomls(os.path.join(CFG.get('jeu_dir') or '', 'mods')):
        for c in _liste(t, 'character'):
            if isinstance(c, dict) and (c.get('base') or {}).get('name') == code:
                sp = ((c.get('new_model') or {}).get('cells') or {}).get('skeleton_path')
                if isinstance(sp, str):
                    n = os.path.basename(os.path.dirname(sp.replace(chr(92), '/')))
                    if n and n != code:
                        return n
    return None


def _prefixe(t):
    """préfixe des chemins d'objets lus dans la racine d'un mod (« racine:<mod>|common/effect/… »)"""
    m = t.get('racine_mod') or t.get('mod_effets')
    return ('racine:%s|' % m) if m else ''


def cinematique_de(t, pour_anim=False):
    """(17/11/2026) cinématique d'une technique (du jeu ou d'un mod) : (dossier data, cinématique, préfixe des objets).
    Technique de mod : lue dans sa racine superposée ; les [[event_command]] LOAD_ACTOR_RESOURCE du mod remplacent le fichier
    chargé par un acteur (copie recolorée) ; pour l'animation (pour_anim), une copie que VRFW fabrique au lancement est lue
    dans son objet d'origine (mêmes os, mêmes clips)"""
    D_ = racine_de(t)
    cin = techniques.lire_cinematique(D_, t['cinematique'])
    pre = _prefixe(t)
    m = t.get('mod_effets')
    if m:
        from moteur import mods_recolor, vrfw_anim
        cin['effets_non_lus'] = []
        for e in vrfw_anim.effets_ajoutes(CFG, m, t.get('event_id')):     # objets ajoutés par [[event_effect]]
            act, ch = vrfw_anim.acteur_objet(e), vrfw_anim.chemin_objet(e)
            nom_ch = os.path.basename(ch).rsplit('.', 1)[0]
            # objet fait par VRFW au lancement à partir d'un .glb (VRFW.model/1 kind = "effect", ex. traînée de Spectre
            # chrono) : pas sur le disque, pas encore lu -> noté, pas affiché en erreur
            if not os.path.exists(os.path.join(D_, *ch.split('/'))) and not mods_recolor.origine(CFG, m, nom_ch):
                cin['effets_non_lus'].append(act)
                continue
            if act not in [o['acteur'] for o in cin['objets']]:
                cin['objets'].append({'acteur': act, 'chemin': ch, 'ajoute': True})
        sub = dict(mods_recolor.commandes(CFG, m, t.get('event_id')))
        # (25/11, retour de danifdez : « Tiger fang d'InazumaFantasy montre les textures de Beast fang ») LU dans le mod :
        # content/effects/tiger_fang.toml [[event_command]] LOAD_ACTOR_RESOURCE set = ["ev63_00300_s00_p<VARIATION>",
        # "ev63_86020"] = un CODE DE MODÈLE (pas un chemin d'objet d'effet) ; ce modèle vient d'un .glb du mod (VRFW.model/1,
        # converti par moteur/glb_vrfw.py dans la racine du mod). LU dans le cache de VRFW : la cinématique copiée charge
        # bien « ev63_86020 » pour cet acteur. Avant, seuls les objets d'effet étaient remplacés : l'acteur gardait ev63_00300.
        import re as _re
        cin['modeles_mod'] = {}
        for mo in cin.get('modeles') or []:
            v = sub.get(mo['acteur'])
            if isinstance(v, str) and _re.fullmatch(r'[\w~-]+', v) and v != mo['modele'] and \
                    anim._dossier_chr(os.path.join(D_, 'common'), v):
                cin['modeles_mod'][mo['acteur']] = [mo['modele'], v]
                mo['modele_origine'], mo['modele'] = mo['modele'], v
                mo.pop('chemin', None)
        for o in cin['objets']:
            if o['acteur'] in sub and o['acteur'] not in cin['modeles_mod']:
                o['chemin'] = sub[o['acteur']]
            if pour_anim and not os.path.exists(os.path.join(D_, *o['chemin'].split('/'))):
                nom = os.path.basename(o['chemin']).rsplit('.', 1)[0]
                b = mods_recolor.origine(CFG, m, nom)
                if b:
                    p_ = o['chemin'].split('/')
                    o['chemin'] = '/'.join(p_[:-3] + [b[:4], b, b + '.objbin'])
    return D_, cin, pre


_LIES = {}


def esprits_lies(cle):
    """(17/11/2026) codes des modèles d'esprit dont « cle » est la technique liée : jeu (aura_skill_config v[6] / v[7], LU) et
    mods ([[aura_command]] cells.linked_skill / aura_chara)"""
    import zlib as _z
    if not cle:
        return []
    if '_jeu' not in _LIES:
        from moteur import cfgbin
        from moteur.personnages import _dernier
        S = os.path.join(CFG['data_dir'], 'common', 'gamedata', 'skill')
        codes = {p['code'] for p in PERSOS}
        dj = os.path.join(CFG['data_dir'], 'common', 'chr', '_keshin')
        if os.path.isdir(dj):
            codes |= set(os.listdir(dj))
        _LIES['crc'] = {_z.crc32(c.encode()): c for c in codes}
        jeu = {}
        for k, v in cfgbin.lire(open(_dernier(os.path.join(S, 'aura_skill_config_*.cfg.bin')), 'rb').read()):
            if len(v) > 7 and isinstance(v[6], int) and isinstance(v[7], int) and (v[7] & 0xFFFFFFFF) in _LIES['crc']:
                jeu.setdefault(v[6] & 0xFFFFFFFF, []).append(_LIES['crc'][v[7] & 0xFFFFFFFF])
        _LIES['_jeu'] = jeu
    c = _z.crc32(str(cle).encode())
    out = list(_LIES['_jeu'].get(c, []))
    from moteur.mods_contenu import _tomls, _liste
    for m, f, tt in _tomls(os.path.join(CFG.get('jeu_dir') or '', 'mods')):
        for a in _liste(tt, 'aura_command'):
            cel = (a.get('cells') or {}) if isinstance(a, dict) else {}
            ls, ch = cel.get('linked_skill'), cel.get('aura_chara')
            if isinstance(ls, int) and (ls & 0xFFFFFFFF) == c and isinstance(ch, int):
                code = _LIES['crc'].get(ch & 0xFFFFFFFF) or next((x['modele'] for x in MODS['liste'] if x.get('cat') == 'esprits'
                                                                 and _z.crc32(str(x.get('base', '')).encode()) == (ch & 0xFFFFFFFF)), None)
                if code:
                    out.append(code)
    return out


def anim_de(t):
    """(17/11/2026) animation d'une technique pour l'aperçu et le lecteur natif : cinématique du jeu ou du mod, recomposée
    par VRFW ([[event]] cuts, plans en .glb, [[camera]] : moteur/vrfw_anim.py), objets ajoutés ([[event_effect]]) et son du
    mod (sound_cue, sound_delay) ; renvoie (dossier data, cinématique, animation)"""
    from moteur import vrfw_anim
    D_, cin, pre = cinematique_de(t, pour_anim=True)
    r = anim.cinematique(D_, t['cinematique'], cin['objets'], assign_anim=t.get('anim_assign'))
    ev = t.get('vrfw_event')
    if ev and ev.get('cuts'):
        r = vrfw_anim.recomposer(r, ev, os.path.join(CFG['jeu_dir'], 'mods', t.get('vrfw_mod') or ''), t.get('vrfw_cameras') or [])
    if t.get('mod_effets'):
        vrfw_anim.appliquer_effets(r, vrfw_anim.effets_ajoutes(CFG, t['mod_effets'], t.get('event_id')))
    # (25/11) modèle d'acteur remplacé par le mod (LOAD_ACTOR_RESOURCE vers un code de modèle, cinematique_de) : on montre le
    # modèle du mod ; les gestes restent ceux de la scène d'origine (mêmes os : le .glb du mod suit le squelette du gabarit)
    for a in r.get('acteurs') or []:
        x = (cin.get('modeles_mod') or {}).get(a.get('acteur'))
        if x and a.get('code') == x[0]:
            a['code'], a['code_origine'] = x[1], x[0]
    if ev and ev.get('assigned'):
        # (17/11/2026) [[event]] assigned = ["k002090"] : l'esprit « <ASSIGN> » de la cinématique est celui-là (Lumière de
        # Michael -> Michael, dont l'apparence est remplacée par Michael astral k002093 : modele_binaire / modele_remplace)
        for a in r.get('acteurs') or []:
            if str(a.get('acteur', '')).startswith('<ASSIGN>'):
                a['code'] = ev['assigned'][0]
    else:
        # (17/11/2026, retour de muku : « Vol angélique d'InazumaFantasy : un esprit dans l'Atelier, aucun en jeu »)
        # « <ASSIGN> » (modèle INVARID) = l'esprit du TIREUR ; il n'apparaît que si la technique est la technique LIÉE d'un
        # esprit (LU : aura_skill_config v[6] = crc32(technique), v[7] = crc32(modèle) ; mods : [[aura_command]]
        # cells.linked_skill / aura_chara). Vol du phénix whs02360 -> Phénix k000610 ; sa copie whs90236 : aucun -> caché.
        lies = esprits_lies(t.get('cle') if t.get('mod') else t.get('code'))
        for a in r.get('acteurs') or []:
            if not str(a.get('acteur', '')).startswith('<ASSIGN>'):
                continue
            if lies:
                if a.get('code') not in lies:
                    a['esprit_lie'] = lies[0]
            else:
                a['ordres'] = [{'image': 0, 'visible': False}]
                a['cache_raison'] = 'aucun esprit lié à cette technique'
    if ev and ev.get('sound_cue'):
        r['sons'] = [{'image': int(ev.get('sound_delay') or 0), 'nom': ev['sound_cue'], 'voix': False}] + \
                    [s for s in r.get('sons') or [] if s.get('voix')]
    return D_, cin, r


for _d, _code in (JEU.get('alias_tenues') or {}).items():   # (15/11/2026) anciens projets : une tenue = un dossier
    JEU_CODE.setdefault(('tenues', _d), JEU_CODE.get(('tenues', _code)))
MAILLOTS = os.path.join(os.path.dirname(ICI), 'AtelierMaillots', 'Atelier Maillots.exe')
_objets = {}
_verrou = threading.Lock()


def objet(chemin):
    if chemin.startswith('mod:/chr/'):                  # (17/11/2026) « mod:/chr/<code>[|20] » : modèle d'un mod, lu sur place
        code, _, cote = chemin[9:].partition('|')
        e = entree_mod(code)
        if e is None:
            raise ValueError('modèle de mod introuvable : ' + code)
    if chemin.startswith('racine:'):                    # (17/11/2026) objet lu dans la racine superposée d'un mod
        from moteur import racines
        mod_r, _, rel = chemin[7:].partition('|')
        R = racines.racine(CFG, CACHE, mod_r) or CFG['data_dir']
    with _verrou:
        if chemin not in _objets and chemin.startswith('racine:'):
            from moteur import mods_recolor
            nom_o = os.path.basename(rel).rsplit('.', 1)[0]
            mod_f = os.path.join(R, *rel.partition('|')[0].split('/'))
            src_rel = rel
            if not os.path.exists(mod_f):
                # (17/11/2026) copie recolorée que VRFW fabrique au lancement ([[recolor]] copy = nom_o) : son objet d'origine
                base = mods_recolor.origine(CFG, mod_r, nom_o)
                if base:
                    p_ = rel.split('/')
                    src_rel = '/'.join(p_[:-3] + [base[:4], base, base + '.' + p_[-1].rsplit('.', 1)[1]]) if len(p_) >= 3 else rel
            ob = jeu.ObjetModele(R, src_rel) if '.g4md' in src_rel else g4.ObjetEffet(R, src_rel)
            jeu_f = os.path.join(CFG['data_dir'], *rel.partition('|')[0].split('/'))
            ob._recolor = (mod_r, nom_o) if mods_recolor.pour(CFG, mod_r, nom_o) else None
            if src_rel != rel or ob._recolor or not (os.path.exists(jeu_f) and os.path.samefile(jeu_f, mod_f)):
                ob.nom = nom_o + '~' + mod_r               # fichier ou couleurs du mod : un dossier du cache à lui
            if ob._recolor:                                 # sommets, matériaux, particules, teintes du mod (en mémoire)
                try:
                    ob._recolor_resume = mods_recolor.appliquer_objet(CFG, ob, mod_r, nom_o)
                except Exception as ex:
                    print('recoloration (sommets / matériaux)', chemin, ex)
            _objets[chemin] = ob
        if chemin not in _objets:
            if chemin.startswith('mod:/chr/'):
                from moteur import mods_jeu
                _objets[chemin] = mods_jeu.objet_esprit(CFG, e) if e.get('dossier_abs') else                     mods_jeu.objet(CFG, dict(e, tx=e['tx20'], code=e['code'] + '_20') if cote == '20' and e.get('tx20') else e)
            else:
                _objets[chemin] = jeu.ObjetModele(CFG['data_dir'], chemin) if '.g4md' in chemin else g4.ObjetEffet(CFG['data_dir'], chemin)
        return _objets[chemin]


_verrou_d3d = threading.Lock()


def rendu_d3d(demande):
    """PROTOTYPE (13/11/2026) : la page envoie l'état de l'image (pièces d'effets dans l'ordre, matrices, paramètres) et la
    scène sans les effets (pixels RGBA) ; Direct3D 11 dessine les effets par-dessus avec les shaders du jeu
    (dossier AtelierD3D, à côté de l'Atelier). Réponse : pixels RGBA."""
    import base64, time
    d3d = os.path.join(os.path.dirname(ICI), 'AtelierD3D')
    if not os.path.exists(os.path.join(d3d, 'rendu_image.py')):
        return {'erreur': 'dossier AtelierD3D introuvable'}
    if d3d not in sys.path:
        sys.path.insert(0, d3d)
    import rendu_image
    t0 = time.time()
    fond = base64.b64decode(demande['fond']) if demande.get('fond') else None
    prof = base64.b64decode(demande['profondeur']) if demande.get('profondeur') else None
    prof_obj = base64.b64decode(demande['profondeur_objets']) if demande.get('profondeur_objets') else None
    modifs = {k: (v[0], v[1], base64.b64decode(v[2])) for k, v in (demande.get('modifs') or {}).items()}
    if demande.get('sauver'):                    # essais : demande gardée pour la rejouer hors du serveur
        json.dump({k: v for k, v in demande.items() if k != 'sauver'}, open(os.path.join(CACHE, 'derniere_demande_d3d.json'), 'w', encoding='utf-8'))
    t1 = time.time()
    with _verrou_d3d:
        if demande.get('profil'):                # mesure détaillée (cProfile) : les fonctions les plus lentes
            import cProfile, pstats, io
            pr = cProfile.Profile(); pr.enable()
        px, notes = rendu_image.rendre(demande['etat'], fond, modifs, prof, bool(demande.get('effets_ecran')), demande.get('lum_avant'),
                                       demande.get('reglages_ecran'), demande.get('ombre'), prof_obj)
        if demande.get('profil'):
            pr.disable(); s = io.StringIO(); pstats.Stats(pr, stream=s).sort_stats('tottime').print_stats(40)
            notes = list(notes) + [s.getvalue()]
    t2 = time.time()
    R = getattr(rendu_image, '_service', {}).get((demande['etat']['largeur'], demande['etat']['hauteur']))
    return {'image': base64.b64encode(px).decode(), 'notes': notes, 'ms': int((time.time() - t0) * 1000),
            'lum': getattr(R, 'lum_moyenne', None),     # luminosité adaptée de cette image (film : passée à la suivante)
            'ms_detail': {'decodage': int((t1 - t0) * 1000), 'rendu': int((t2 - t1) * 1000)}}


def lecteur_natif(demande):
    """LECTEUR NATIF (14/11/2026) : la page envoie l'animation calculée (caméra, réglages de lumière par image) ; le décor
    est exporté (AtelierNatif/exporter.py) puis AtelierNatif/lecteur.exe est lancé : il dessine EN DIRECT avec les shaders
    du jeu (C++ / Direct3D 11)."""
    import subprocess, time
    t0 = time.time()
    X = _natif()
    if X is None:
        return {'erreur': 'dossier AtelierNatif introuvable'}
    d = os.path.dirname(X.__file__)
    code = demande.get('technique')
    APERCU['projet'] = demande.get('projet') or None     # (21/11) bannière perso du projet ouvert (telop_apercu)
    if demande.get('images'):                    # VÉRIFICATION : animation calculée par la page (ancienne méthode), gardée
        dos = exporter_technique_natif(code)['dossier']
        json.dump(demande, open(os.path.join(dos, 'demande_page.json'), 'w', encoding='utf-8'))
        return {'dossier': dos, 'images': len(demande['images']), 'verification': True}
    # 14/11/2026 : l'ANIMATION EST CALCULÉE PAR LE LECTEUR (C++) ; ici seulement le décor (gardé par stade) et la technique
    # (gardée, exportée dès son ouverture dans l'Atelier) + les retouches de couleur et les pièces cachées
    with _verrou_d3d:
        s = X.exporter_stade(demande.get('stade') or 's10g001')
    r = exporter_technique_natif(code)
    n = X.ecrire_modifs(r['dossier'], demande.get('modifs'))
    # (14/11/2026) + couleurs de matériau choisies dans l'Atelier : {pièce : [r, v, b]} (remplacent u_diffuse.rgb)
    json.dump({'caches': demande.get('caches') or [], 'couleurs': demande.get('couleurs') or {},
               'sommets': demande.get('sommets') or {}, 'particules': demande.get('particules') or {},   # (14/11/2026) teintes
               'lumieres': demande.get('lumieres') or {},   # (23/11) intensité des lumières de l'effet
               'auras': demande.get('auras') or {},   # (25/11) couleurs d'aura choisies {nom : [r, v, b]} (0..1)
               'fil': demande.get('fil') or []},   # (25/11) pièces sélectionnées en fil de fer
              open(os.path.join(r['dossier'], 'options.json'), 'w', encoding='utf-8'))
    exe = os.path.join(d, 'lecteur.exe')
    if not os.path.exists(exe):
        return dict(r, erreur='lecteur.exe absent : lancer AtelierNatif/compiler.bat')
    with _verrou_natif:                          # (14/11/2026) deux lancements simultanés (Espace pendant le chargement) :
        return _lancer_natif(demande, exe, d, s, r, n, t0)   # l'un après l'autre, jamais deux lecteurs


def arreter_natifs(pid=None):
    """(14/11/2026) TOUS les lecteurs lancés par ce serveur : « quitter », puis arrêt forcé de ceux qui ne répondent pas
    (un lecteur encore en chargement ne lit pas ses commandes ; avant : il restait, fenêtre sans bordure impossible à fermer)"""
    import time
    with _verrou_natif:                          # (RLock : aussi appelé pendant un lancement)
        _arreter_natifs(time, pid)


def _arreter_natifs(time, pid):
    # pid : seulement CE lecteur (lancement annulé par la page pendant qu'il se faisait : jamais le lecteur suivant)
    if pid is None or (NATIF['proc'] is not None and NATIF['proc'].pid == pid):
        natif_commande('quitter')
    vivants = [p for p in NATIF['tous'] if p.poll() is None and (pid is None or p.pid == pid)]
    fin = time.time() + 0.6
    while vivants and time.time() < fin:
        time.sleep(0.05); vivants = [p for p in vivants if p.poll() is None]
    for p in vivants:
        try:
            p.kill(); p.wait(2)
        except Exception:
            pass
    NATIF['tous'] = [p for p in NATIF['tous'] if p.poll() is None]
    if NATIF['proc'] is not None and NATIF['proc'].poll() is not None:
        NATIF['proc'] = None


def _lancer_natif(demande, exe, d, s, r, n, t0):
    import subprocess, time
    arreter_natifs()                             # (un seul lecteur à la fois)
    args = [exe, s['dossier'], r['dossier'], str(int(demande.get('largeur', 1280))), str(int(demande.get('hauteur', 720)))]
    if demande.get('incruste'):                  # 14/11/2026 : dessiné DANS la vue de l'Atelier (fenêtre posée sur la vue 3D)
        import socket
        x = socket.socket(socket.AF_INET, socket.SOCK_DGRAM); x.bind(('127.0.0.1', 0)); port = x.getsockname()[1]; x.close()
        args += ['--incruste', str(port), '--parent', str(os.getpid())]   # (serveur fermé : le lecteur se ferme)
        if demande.get('jeton'):                 # (jeton que la page a mis dans son titre : retrouve SA fenêtre, quel que soit le navigateur)
            args += ['--fenetre', ''.join(ch for ch in str(demande['jeton']) if ch.isalnum())[:32]]
        NATIF['port'] = port
    else:
        NATIF['port'] = None
    NATIF['proc'] = subprocess.Popen(args, cwd=d); NATIF['tous'].append(NATIF['proc'])
    if demande.get('incruste') and demande.get('rect'):
        rc, proc = demande['rect'], NATIF['proc']
        # (23/11, retour de muku : lecteur posé à côté de l'aperçu, plus petit) zone de CE lancement envoyée à CE lecteur seulement :
        # avant, un lecteur lancé dans la seconde suivante (choix déjà en cache) recevait la zone de l'ancien (ex. la vue de
        # l'éditeur derrière la fenêtre) et la page ne la corrigeait plus (elle croyait l'avoir déjà envoyée)
        def _rect_lance():
            for k in (0.3, 0.4, 0.8):
                time.sleep(k)
                if NATIF['proc'] is not proc:
                    return
                natif_commande('rect %d %d %d %d %d %d' % tuple(int(v) for v in rc))
        threading.Thread(target=_rect_lance, daemon=True).start()
    return dict(r, pid=NATIF['proc'].pid, decor=s.get('decor', 'exporté'), retouches=n, secondes=round(time.time() - t0, 2), incruste=bool(demande.get('incruste')))


NATIF = {'proc': None, 'port': None, 'tous': []}
_verrou_natif = threading.RLock()


def natif_commande(cmd, attendre=False):
    """commande texte au lecteur incrusté (UDP 127.0.0.1) ; « etat » : renvoie sa réponse"""
    import socket
    p = NATIF.get('proc')
    if p is None or p.poll() is not None or not NATIF.get('port'):
        return {'actif': False}
    x = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        x.settimeout(0.25)
        x.sendto(cmd.encode(), ('127.0.0.1', NATIF['port']))
        if attendre:
            try:
                return {'actif': True, 'etat': x.recvfrom(1024)[0].decode()}
            except socket.timeout:
                return {'actif': True, 'etat': None}
        return {'actif': True}
    finally:
        x.close()


def planche_natif(code, temps):
    """COMPARAISON (14/11/2026) : instants t de la vidéo officielle (secondes) ; image du lecteur = (t + 0,3) x 60 (calage
    des vidéos). Le lecteur dessine toutes les images depuis 0 (adaptation de la luminosité) et garde celles demandées."""
    import subprocess, html
    X = _natif()
    APERCU['projet'] = None                      # (21/11) comparaison aux vidéos : toujours la bannière du jeu
    with _verrou_d3d:
        s = X.exporter_stade('s10g001')
    r = exporter_technique_natif(code)
    ts = [float(x) for x in temps.split(',') if x.strip()]
    fs = [int(round((t + 0.3) * 60)) for t in ts]
    for f in os.listdir(r['dossier']):
        if f.startswith('planche_'):
            os.remove(os.path.join(r['dossier'], f))
    d = os.path.dirname(X.__file__)
    subprocess.run([os.path.join(d, 'lecteur.exe'), s['dossier'], r['dossier'], '1280', '720', '--planche', r['dossier']] + [str(f) for f in fs], cwd=d, timeout=600)
    v = VIDEOS.get(code) or ''
    v = v[:-4] + '.webm' if v.endswith('.wmv') else v
    nom = os.path.basename(r['dossier'])
    lignes = ''.join('<tr><td>t = %.2f s<br>image %d</td><td><video muted preload="auto" src="%s#t=%.3f" width="640" height="360"></video></td>'
                     '<td><img src="/natif/%s/planche_%d.bmp" width="640" height="360"></td></tr>' % (t, f, html.escape(v), t, nom, f) for t, f in zip(ts, fs))
    return ('<!doctype html><meta charset="utf-8"><title>Planche %s</title><style>body{background:#111;color:#ddd;font:13px sans-serif;margin:4px}'
            'td{padding:2px;vertical-align:top}</style><table><tr><th></th><th>vidéo officielle</th><th>lecteur natif</th></tr>%s</table>' % (code, lignes))


_natif_mod = None
_verrous_tech = {}


def _natif():
    """module AtelierNatif/exporter.py (lecteur natif), avec ce serveur comme source des données (sans le réimporter)"""
    global _natif_mod
    if _natif_mod is None:
        d = os.path.join(os.path.dirname(ICI), 'AtelierNatif')
        if not os.path.exists(os.path.join(d, 'exporter.py')):
            return None
        if d not in sys.path:
            sys.path.insert(0, d)
        import exporter
        exporter.SRV = sys.modules[__name__]
        _natif_mod = exporter
    return _natif_mod


def exporter_technique_natif(code):
    """technique pour le lecteur natif (gardée dans AtelierNatif/scenes/tech_<code>) ; un seul export à la fois par
    technique (l'ouverture dans l'Atelier la prépare en arrière-plan, le bouton Lecture attend la fin s'il le faut)"""
    X = _natif()
    with _verrou:
        v = _verrous_tech.setdefault(code, threading.Lock())
    with v:
        if str(code).startswith('armure_'):         # (23/11) aperçu de mise en armure : refait quand l'armure a changé
            a_ = armures_copies.registre(CFG).get(code[len('armure_'):].split('~')[0]) or {}
            f_ = os.path.join(os.path.dirname(X.__file__), 'scenes', 'tech_' + code, 'copie_date.txt')
            neuf = json.dumps([a_.get('date'), a_.get('mise'), (a_.get('stats') or {}).get('element')])
            vieux = open(f_, encoding='utf-8').read() if os.path.exists(f_) else None
            r = X.exporter_technique(code, force=vieux != neuf)
            open(f_, 'w', encoding='utf-8').write(neuf)
            return r
        if str(code).startswith('invoc_'):          # (23/11) aperçu d'invocation : refait quand la copie a changé
            c = esprits.registre(os.path.join(ICI, 'sortie', 'MesEsprits')).get(code[len('invoc_'):].split('~')[0]) or {}
            f_ = os.path.join(os.path.dirname(X.__file__), 'scenes', 'tech_' + code, 'copie_date.txt')
            neuf = json.dumps([c.get('date'), c.get('invocation'), (c.get('stats') or {}).get('element')])
            vieux = open(f_, encoding='utf-8').read() if os.path.exists(f_) else None
            r = X.exporter_technique(code, force=vieux != neuf)
            open(f_, 'w', encoding='utf-8').write(neuf)
            return r
        return X.exporter_technique(code)


def preparer_natif(code):
    """en arrière-plan à l'ouverture d'une technique : le lecteur démarre ensuite tout de suite"""
    def f():
        try:
            if _natif() is not None:
                exporter_technique_natif(code)
                with _verrou_d3d:
                    _natif().exporter_stade('s10g001')
        except Exception as ex:
            print('lecteur natif (préparation) :', ex)
    threading.Thread(target=f, daemon=True).start()


def crc_uv(ob, p):
    """crc32('<matériau>_tex<n>') de la texture montrée par l'aperçu (la 1re texture de couleur du matériau) : cible du
    défilement de texture (G4TP)"""
    if p['materiau'] is None:
        return 0
    m = ob.materiaux[p['materiau']]
    for k, t in enumerate(m['textures']):
        if '_par' not in t:
            return zlib.crc32(('%s_tex%d' % (m['nom'], k)).encode())
    return 0


def _fini(x):
    """copie de x où les flottants non finis sont remplacés (voir _envoyer)"""
    import math
    if isinstance(x, float) and not math.isfinite(x):
        return 0.0 if math.isnan(x) else math.copysign(3.4028234663852886e38, x)
    if isinstance(x, dict):
        return {k: _fini(v) for k, v in x.items()}
    if isinstance(x, (list, tuple)):
        return [_fini(v) for v in x]
    return x


def details(code):
    t = technique(code)                                     # (17/11/2026) technique d'un mod : sa cinématique, lue dans la
    D_, cin, pre = cinematique_de(t)                        # racine superposée du mod quand ses fichiers sont dans le mod
    for o in cin['objets']:
        o['chemin'] = pre + o['chemin']
    objs = []
    for o in cin['objets']:
        try:
            ob = objet(o['chemin'])
        except Exception as ex:
            objs.append({'acteur': o['acteur'], 'erreur': str(ex)})
            continue
        try:
            infos = ob.extraire_textures(CACHE)
        except Exception as ex:                             # (17/11/2026) planche d'un format inconnu (InazumaFantasy) :
            print('textures illisibles', o['chemin'], ex)   # l'objet reste, ses textures sont « non lisibles »
            infos = {}
        if getattr(ob, '_recolor', None):                   # (17/11/2026) recolorations VRFW du mod (moteur/mods_recolor.py)
            try:
                from moteur import mods_recolor
                mods_recolor.appliquer(CFG, CACHE, ob, *ob._recolor)
            except Exception as ex:
                print('recoloration', o['chemin'], ex)
        objs.append({
            'acteur': o['acteur'], 'chemin': o['chemin'], 'nom': ob.nom, 'commun': bool(o.get('commun')),
            'pieces': [{'index': p['index'], 'nom': p['nom'], 'nv': p['nv'], 'materiau': p['materiau'],
                        'mat_crc': (ob.materiaux[p['materiau']].get('crc') or zlib.crc32(ob.materiaux[p['materiau']]['nom'].encode())) if p['materiau'] is not None else 0,
                        'uv_crc': crc_uv(ob, p),
                        'peau': (p.get('peau') or {}).get('palette'),          # os de la palette (maillage à peau)
                        'couleur': ob.materiaux[p['materiau']].get('couleur') if p['materiau'] is not None else None,
                        'gain': ob.materiaux[p['materiau']].get('gain', 1.0) if p['materiau'] is not None else 1.0,
                        'melange': ob.materiaux[p['materiau']].get('melange') if p['materiau'] is not None else None,
                        'ztest': ob.materiaux[p['materiau']].get('ztest', True) if p['materiau'] is not None else True,
                        'faces': ob.materiaux[p['materiau']].get('faces', 0) if p['materiau'] is not None else 0,
                        'biais': ob.materiaux[p['materiau']].get('biais', 0) if p['materiau'] is not None else 0,
                        'panneau': ob.materiaux[p['materiau']].get('panneau', 0) if p['materiau'] is not None else 0,   # pièce tournée vers la caméra (LU)
                        'prio': ob.materiaux[p['materiau']].get('priorite', 30) if p['materiau'] is not None else 30,   # couche de dessin (LU)
                        'seuil': ob.materiaux[p['materiau']].get('seuil', 256) if p['materiau'] is not None else 256,   # test d'alpha (LU)
                        'zecrit': bool(ob.materiaux[p['materiau']].get('zecrit', False)) if p['materiau'] is not None else False,   # clé 5 -> écriture de profondeur (LU)   # élimination des faces arrière (LU)
                        'shader': ob.materiaux[p['materiau']]['nom'] if p['materiau'] is not None else '',
                        # rendu du jeu : shader, couleurs, paramètres et matrices de texture du matériau ; défilement par case
                        'jeu': {x: ob.materiaux[p['materiau']].get(x) for x in ('shader_nom', 'shader_ps', 'diffuse', 'ambient', 'params', 'texproj', 'adressage')}
                               if p['materiau'] is not None else None,
                        'uv_crcs': [zlib.crc32(('%s_tex%d' % (ob.materiaux[p['materiau']]['nom'], k)).encode())
                                    for k in range(len(ob.materiaux[p['materiau']]['textures']))] if p['materiau'] is not None else [],
                        'textures': ob.materiaux[p['materiau']]['textures'] if p['materiau'] is not None else []} for p in ob.pieces],
            # vraies particules (.ptlb) : émetteurs lus comme le jeu (moteur/particules.py), simulés par web/particules.js
            'particules': getattr(ob, 'particules', None),
            'lumieres': getattr(ob, 'lumieres', None),
            # (15/11/2026) marquage « données » refait d'après le nom (le cache des textures garde l'ancienne règle « _par »)
            'textures': [dict(infos.get(n, {'nom': n, 'lisible': False}), donnees=g4.est_donnees(n)) for n in ob.textures],
        })
    # (14/11/2026) MODÈLES DE PERSONNAGES de la cinématique (esprit guerrier, objets : commande LOAD [acteur, code]) : leurs
    # textures sont proposées à la retouche comme celles des effets (même clé « <code>/<texture> » que le rendu des acteurs).
    # Aucune pièce : le modèle est dessiné par le lecteur d'animation (acteurs). Le mod en fait une copie recolorée
    # (moteur/clone_modele.py, moteur/export.py).
    for m in cin.get('modeles') or []:
        try:
            d = anim._dossier_chr(os.path.join(D_, 'common'), m['modele'])
            if not d:
                continue
            rel = os.path.relpath(d, os.path.join(D_, 'common')).replace('\\', '/')
            ch = pre + 'common/%s/%s.objbin' % (rel, m['modele'])          # dossier du modèle (chr/_keshin/<code>…)
            ob = objet(ch)
            infos = ob.extraire_textures(CACHE)
            objs.append({'acteur': m['acteur'], 'chemin': ch, 'nom': ob.nom, 'modeleActeur': m['modele'],
                         'modeleOrigine': m.get('modele_origine'),     # (25/11) modèle de la scène remplacé par celui du mod
                         'liste': m.get('liste', 'evt'), 'cheminLoad': m.get('chemin'), 'commandeLoad': m.get('commande'), 'espritDuJoueur': bool(m.get('esprit_du_joueur')), 'pieces': [],
                         'textures': [infos.get(n, {'nom': n, 'lisible': False, 'donnees': False}) for n in ob.textures]})
        except Exception as ex:
            print('modèle', m, ex)
    if t.get('mod_effets'):                                 # (17/11/2026) auras recolorées par le mod : couleur pré-remplie
        from moteur import mods_recolor
        for a in cin.get('auras') or []:
            c = mods_recolor.couleur_aura(CFG, t['mod_effets'], a['aura'])
            if c:
                a['origine'], a['couleur'] = c
    v = VIDEOS.get(t['code'])
    return dict(t, **cin, objets_details=objs, video=v[:-4] + '.webm' if v and v.endswith('.wmv') else v)


def details_personnage(code):
    """un esprit guerrier ou un totem : un seul « objet » (son modèle), présenté comme les objets d'effet des techniques"""
    p = PERSO_CODE.get(code) or entree_mod(code)            # (17/11/2026) esprit d'un mod : lu dans le dossier du mod
    if p is None:
        raise KeyError(code)
    chemin = p['chemin'] if p.get('mod') else 'common/chr/%s/%s/%s.objbin' % (p['dossier'], code, code)
    ob = objet(chemin)
    infos = ob.extraire_textures(CACHE)
    o = {'acteur': code, 'chemin': chemin, 'nom': ob.nom,
         'pieces': [{'index': x['index'], 'nom': x['nom'], 'nv': x['nv'], 'materiau': x['materiau'],
                     'textures': ob.materiaux[x['materiau']]['textures'] if x['materiau'] is not None else []} for x in ob.pieces],
         'textures': [infos.get(n, {'nom': n, 'lisible': False, 'donnees': False}) for n in ob.textures]}
    return dict(p, objets_details=[o], auras=[])


def _objet_details(chemin, acteur, role=None):
    ob = objet(chemin)
    infos = ob.extraire_textures(CACHE)
    return {'acteur': acteur, 'chemin': chemin, 'nom': ob.nom, 'role': role,
            'pieces': [{'index': x['index'], 'nom': x['nom'], 'nv': x['nv'], 'materiau': x['materiau'],
                        'textures': ob.materiaux[x['materiau']]['textures'] if x['materiau'] is not None else []} for x in ob.pieces],
            'textures': [infos.get(n, {'nom': n, 'lisible': False, 'donnees': False}) for n in ob.textures]}


def accessoires_maillot(code, cote):
    """(15/11/2026) chaussures et gants (gardiens) d'un maillot du jeu : LU, maillot u<n> -> chaussures s<n>_10 (168 sur 170),
    gants g<n>_10 (166 sur 170), extérieur _20 s'il existe ; tous cités dans uniform_config. Maillage et texture = ligne 0."""
    P = copies_tenues._parties(CFG['data_dir'])
    out = []
    for g, lettre, role in (('shoes', 's', 'chaussures'), ('gloves', 'g', 'gants')):
        nom = next((n for n in ('%s%s_%s' % (lettre, code[1:], cote), '%s%s_10' % (lettre, code[1:])) if n in P[g]), None)
        r = P[g][nom][0] if nom else None
        if r and isinstance(r[0], str) and isinstance(r[1], str):
            out.append({'role': role, 'modele': nom, 'chemin': 'common/chr/%s|dx11/chr/%s|%s' % (r[0], r[1], nom), 'texture': r[1]})
    return out


def details_jeu(cat, code, modele=None, cote=None):
    """(15/11/2026) un élément du jeu (maillot, tenue, armure, tête, objet) : comme un esprit, un seul objet (son modèle) ;
    modele = autre maillage du même dossier (corpulence : une tenue a un maillage par corps) ; maillots : côté (10 domicile,
    20 extérieur) et, en plus, ses chaussures et ses gants"""
    if (cat, code) not in JEU_CODE:                    # (17/11/2026) modèle d'un mod pas encore listé
        mods_liste(frais=True)
    p = JEU_CODE[(cat, code)]
    if cat == 'objets' and p.get('type') == 'objet':          # (15/11/2026) objet du jeu : son icône, pas de 3D
        d = objets_jeu.details(CFG, CACHE, p)
        # (27/11, muku) crampons / gants : leur MODÈLE 3D porté, à recolorer aussi (2e objet de l'éditeur, après l'icône)
        m = objets_jeu.modele_porte(CFG['data_dir'], code) if p.get('famille') in objets_jeu.EQUIPEMENTS else None
        if m and m.get('chemin'):
            try:
                d['objets_details'] = d['objets_details'] + [dict(_objet_details(m['chemin'], code, 'chaussures' if m['sorte'] == 'shoes' else 'gants'),
                                                                  modele_jeu=m['cle'])]
                d['modele_porte'] = {'sorte': m['sorte'], 'cle': m['cle']}
            except Exception as ex:
                print('modèle porté', code, ex)
        return d
    if cat == 'maillots' and p.get('modele_mod'):            # (17/11/2026) maillot d'un mod : sa coupe + sa texture (domicile / extérieur)
        cote = '20' if cote == '20' and p.get('tx20') else '10'
        o = _objet_details(p['chemin'] + ('|20' if cote == '20' else ''), p['code'], 'maillot')
        return dict(sans_chemins([p])[0], objets_details=[o], auras=[], categorie=cat, cote=cote, tex20_existe=bool(p.get('tx20')))
    if cat == 'maillots':
        cote = '20' if cote == '20' else '10'
        if cote == '20' and p.get('tex20'):
            md = p['chemin'].partition('|')[0]
            p = dict(p, chemin='%s|%s|%s_20' % (md, p['tex20'], code))
        objs = [_objet_details(p['chemin'], code, 'maillot')]
        acc = accessoires_maillot(code, cote)
        for a in acc:
            try:
                objs.append(dict(_objet_details(a['chemin'], code, a['role']), modele_jeu=a['modele'], texture_jeu=a['texture']))
            except Exception as ex:
                print('accessoire', a['modele'], ex)
        return dict(p, objets_details=objs, auras=[], categorie=cat, cote=cote, tex20_existe=bool(p.get('tex20')))
    if modele:
        md, sep, reste = p['chemin'].partition('|')
        if os.path.dirname(modele) == os.path.dirname(md) and modele.endswith('.g4md') and os.path.exists(os.path.join(CFG['data_dir'], modele)):
            p = dict(p, chemin=modele + sep + reste)
    ob = objet(p['chemin'])
    infos = ob.extraire_textures(CACHE)
    o = {'acteur': code, 'chemin': p['chemin'], 'nom': ob.nom,
         'pieces': [{'index': x['index'], 'nom': x['nom'], 'nv': x['nv'], 'materiau': x['materiau'],
                     'textures': ob.materiaux[x['materiau']]['textures'] if x['materiau'] is not None else []} for x in ob.pieces],
         'textures': [infos.get(n, {'nom': n, 'lisible': False, 'donnees': False}) for n in ob.textures]}
    return dict(p, objets_details=[o], auras=[], categorie=cat)


def telop_png(code):
    """bannière du jeu d'une technique (dx11/menu/220_img/telop_waza/fr/<code>.g4tx) en PNG, pour servir de modèle"""
    d = os.path.join(CACHE, 'telops'); os.makedirs(d, exist_ok=True)
    out = os.path.join(d, os.path.basename(code) + '.png')
    if not os.path.exists(out):
        base = os.path.join(CFG['data_dir'], 'dx11', 'menu', '220_img', 'telop_waza')
        src = next((p for p in (os.path.join(base, 'fr', code + '.g4tx'), os.path.join(base, code + '.g4tx')) if os.path.exists(p)), None)
        if not src:
            return out                                  # -> 404
        g = g4.images.G4TX(open(src, 'rb').read())
        r = g4.decoder_texture(g.blocs[0])
        if r:
            g4.images.ecrire_png(out, *r)
    return out


APERCU = {'projet': None}       # projet ouvert pour l'export du lecteur natif (lecteur_natif ; vide pour les planches de vérification)


def telop_apercu(code_tech, code_telop, projet=None):
    """(21/11) bannière à MONTRER dans les aperçus (web et lecteur natif) pour la technique code_tech :
    1. celle faite dans l'onglet Bannières pour CE PROJET (« Utiliser pour la technique ouverte ») :
       cache/bannieres_apercu/<projet>.png. (21/11, retour de muku : rangée avant sous le code de la technique DU JEU, elle
       remplaçait la vraie bannière de Choc de la vouivre partout, même ouverte sans son projet.) ;
    2. celle d'une copie déjà créée (sortie/<mod>/content/telops/any/<code>.png), ou d'un mod installé ;
    3. sinon celle du jeu (code_telop : la bannière de la cinématique d'origine)."""
    projet = APERCU['projet'] if projet is None else projet
    c = os.path.basename(code_tech or '')
    pj = os.path.basename(projet or '')
    if pj and os.path.isfile(os.path.join(CACHE, 'bannieres_apercu', pj + '.png')):
        return os.path.join(CACHE, 'bannieres_apercu', pj + '.png')
    if c:
        for p in glob.glob(os.path.join(ICI, 'sortie', '*', 'content', 'telops', 'any', c + '.png')) + \
                 glob.glob(os.path.join(CFG.get('jeu_dir') or ICI, 'mods', '*', 'content', 'telops', 'any', c + '.png')):
            if os.path.isfile(p):
                return p
    # (27/11, parcours de l'appli : 404 sur « whs02700_<CHARA_ID> ») bannière à balise (une par lanceur) : celle de la technique
    if code_telop and '<' in code_telop:
        code_telop = code_telop.split('_<')[0] if '_<' in code_telop else code_tech
    f = telop_png(code_telop or code_tech)
    return f if os.path.isfile(f) or not code_tech else telop_png(code_tech)


def telop_apercu_version(code_tech, projet=None):
    """date de la bannière perso du projet / de la technique (0 sans) : l'aperçu web recharge l'image quand elle change"""
    c = os.path.basename(code_tech or '')
    l = ([os.path.join(CACHE, 'bannieres_apercu', os.path.basename(projet) + '.png')] if projet else []) + \
        glob.glob(os.path.join(ICI, 'sortie', '*', 'content', 'telops', 'any', c + '.png'))
    return max([os.path.getmtime(x) for x in l if os.path.isfile(x)] or [0])


# joueur générique des cinématiques : maillot u000101 + chaussures s000101 + tête mannequin c21000010, squelette c000101
JOUEUR = [('common/chr/_uniform/u000101/u000101.g4md', 'dx11/chr/c000101/c000101.g4tx'),
          ('common/chr/_uniform/s000101/s000101.g4md', 'dx11/chr/c000101/c000101.g4tx'),
          ('common/chr/_face/21_MANNEQUIN/c21000010/c21000010.g4md', 'dx11/chr/_face/21_MANNEQUIN/c21000010/c21000010.g4tx')]
_modeles = {}


def _textures_png(dossier_cache, g4tx_chemins, tout=False, data_dir=None):
    """PNG des textures de couleur de ces fichiers .g4tx dans cache/<dossier_cache>/ ; renvoie les noms
    (tout=True : aussi les masques msk / sp / spm, que les shaders du jeu lisent dans le rendu Direct3D)
    (17/11/2026) data_dir : racine superposée d'un mod (modèle qui n'existe que dans un mod) ; défaut : le jeu"""
    D_ = data_dir or CFG['data_dir']
    du_mod = os.path.normcase(D_) != os.path.normcase(CFG['data_dir'])
    d = os.path.join(CACHE, dossier_cache); os.makedirs(d, exist_ok=True)
    noms, a_faire = [], []
    for rel in g4tx_chemins:
        g = g4.images.G4TX(open(os.path.join(D_, rel), 'rb').read())
        for k, n in enumerate(g.noms):
            noms.append(n)
            f = os.path.join(d, n + '.png')
            if os.path.exists(f) or (n.endswith(('msk', 'sp', 'spm')) and not tout):
                continue
            # (15/11/2026) une texture du jeu n'est décodée qu'une fois pour tous les dossiers (maillot, chaussures, peau :
            # avant, refaits pour chaque joueur, ~1 min 30 en BC7 Python) : cache/textures_partagees/<fichier>/<nom>.png
            partage = os.path.join(CACHE, 'textures_partagees', ('%s__' % os.path.basename(D_) if du_mod else '')    # (mod : à part)
                                   + rel.replace('/', '__')[:-5], n + '.png')
            if os.path.exists(partage):
                import shutil
                shutil.copyfile(partage, f)
                continue
            a_faire.append((os.path.join(D_, rel), k, f, partage))
    from moteur import paquets_jeu as _pj
    if len(a_faire) > 2 and _pj._DLL is None:     # plusieurs : en parallèle (sans paquets.dll : décodage Python lent)
        import multiprocessing
        with multiprocessing.Pool(max(1, min(len(a_faire), (os.cpu_count() or 2) - 1))) as pool:
            pool.map(g4.decoder_png_bloc, a_faire)
    else:
        for x in a_faire:
            g4.decoder_png_bloc(x)
    return noms


def couleur_moyenne(png):
    try:
        w, h, rows = g4.images.lire_png(png)
    except Exception:
        return None
    s = [0, 0, 0]
    for r in rows:
        for x in range(w):
            for k in range(3):
                s[k] += r[x * 4 + k]
    return [round(v / (w * h) / 255, 3) for v in s]


def modele_binaire(quoi, code=None, maillot=None, cote='10'):
    """modèle avec os, prêt pour la peau dans la vue : 'joueur' (générique) ou un esprit / totem (code) ;
    (15/11/2026) maillot = un maillot du jeu (u<n>) porté par le joueur, sur la ligne de son corps (aperçu des techniques)"""
    cle = (quoi, code, maillot, cote)
    with _verrou:
        if cle in _modeles:
            return _modeles[cle]
    D = CFG['data_dir']
    code_reg = code
    # (24/11, retour de muku : « pour l'armure il y a l'animation mais à la fin le personnage n'a pas l'armure ») « armure:<copie> » :
    # le joueur (mannequin) qui PORTE l'armure de ma copie. LU : la scène de mise en armure (ev81_*) charge un 2e joueur
    # « c00<TYPE><NO>_s01 » (plan c0020) = le joueur en armure ; l'armure est un vêtement (chara_parts CHARA_PARTS_CLOTHES
    # « ka000101 » : [maillage _armd/ka000101/ka000101.g4md, texture, ligne de corps…]) ; ma copie = la même forme avec SA
    # texture (sortie/MesEsprits/assets/chr/_armd/<modèle>/<modèle>_10.g4tx, noms internes ceux de l'armure du jeu).
    armure = code[len('armure:'):] if quoi == 'joueur' and code and str(code).startswith('armure:') else None
    if armure:
        code = None
    # (27/11, muku : « fais aussi les tenues en 3D comme sur le jeu ») « tenue:<copie> » : le MANNEQUIN du jeu (tête c21000010,
    # comme la boutique) qui porte le vêtement de ma tenue (chara_parts CLOTHES de sa source, ligne du corps normal, + peau des bras
    # et manches) avec SA texture (sortie/MesTenues/assets/chr/_uniform/<modèle>/<modèle>_10.g4tx, noms internes ceux du jeu) ;
    # pas noir (le mannequin de la boutique est gris)
    tenue = code[len('tenue:'):] if quoi == 'joueur' and code and str(code).startswith('tenue:') else None
    if tenue:
        code = None
    if quoi == 'joueur':
        # joueur générique, ou le vrai personnage « code » : sa tête + maillot / chaussures / squelette de sa corpulence
        info = personnages.joueur(D, code) if code else None
        t = info['corps'] if info else 1
        sk = anim.lire_paquet(os.path.join(D, 'common', 'chr', 'c000%d01' % t, 'c000%d01.g4sk' % t))['squelette']
        # maillot, chaussures, et la PEAU (avant-bras + mains) _uniform/sk000101/sk00010<corps> (sans elle : bras coupés)
        # (15/11/2026) rang du vêtement LU (CHARA_BODY_INFO [4], personnages.joueur) : u0001<rang + 1> et sk0001<rang + 1>
        # (avant : u00010<corps>, le petit corps 2 prenait u000102 = corps normal, et la tête allait sur la poitrine)
        n = (info.get('ligne') + 1) if info and isinstance(info.get('ligne'), int) else {1: 1, 2: 3, 3: 5, 4: 6}.get(t, 1)
        if not os.path.exists(os.path.join(D, 'common', 'chr', '_uniform', 'u000101', 'u0001%02d.g4md' % n)):
            n = {1: 1, 2: 3, 3: 5, 4: 6}.get(t, 1)
        tx_corps = 'dx11/chr/c000%d01/c000%d01.g4tx' % (t, t)
        if not os.path.exists(os.path.join(D, tx_corps)):
            tx_corps = 'dx11/chr/c000101/c000101.g4tx'
        parties = [('common/chr/_uniform/u000101/u0001%02d.g4md' % n, tx_corps),
                   ('common/chr/_uniform/s000101/s00010%d.g4md' % t, 'dx11/chr/c000101/c000101.g4tx'),
                   ('common/chr/_uniform/sk000101/sk0001%02d.g4md' % n, 'dx11/chr/_uniform/sk000101/sk000101_10.g4tx')]
        # (15/11/2026) VRAI MAILLOT (LU, chara_parts CHARA_PARTS_CLOTHES : une ligne par corps = [maillage du maillot, texture
        # (ligne 0 seulement), n° de ligne, numéro, …, peau des bras [6] / texture [7], manches [8] / texture [9], …] ; chaussures
        # du maillot s<n>_10 : 4 lignes [maillage s00010x, texture]). Le numéro n'est pas montré.
        P = copies_tenues._parties(D) if maillot else None
        lignes = P and (P['clothes'].get('%s_%s' % (maillot, cote)) or P['clothes'].get(maillot + '_10'))
        if lignes:
            li = info['ligne'] if info and isinstance(info.get('ligne'), int) else 0
            r, r0 = (lignes[li] if li < len(lignes) else lignes[0]), lignes[0]
            cm, cx = (lambda x: 'common/chr/' + x), (lambda x: 'dx11/chr/' + x)
            parties = [(cm(r[0]), cx(r0[1]))]
            for i_md, i_tx in ((6, 7), (8, 9)):             # peau des bras, manches
                if len(r) > i_md and isinstance(r[i_md], str) and isinstance(r0[i_tx], str):
                    parties.append((cm(r[i_md]), cx(r0[i_tx])))
            ch = P['shoes'].get('s%s_%s' % (maillot[1:], cote)) or P['shoes'].get('s%s_10' % maillot[1:])
            if ch and isinstance(ch[0][1], str):
                rs = ch[min(t - 1, len(ch) - 1)]
                parties.insert(1, (cm(rs[0]), cx(ch[0][1])))
            else:
                parties.insert(1, ('common/chr/_uniform/s000101/s00010%d.g4md' % t, 'dx11/chr/c000101/c000101.g4tx'))
        md_arm, tx_arm, D_arm, rel_arm = None, None, None, None
        if armure:
            a_ = armures_copies.registre(CFG).get(armure) or {}
            P_ = copies_tenues._parties(D)
            rows = P_['clothes'].get(a_.get('armure') or '') or []
            if rows:
                md_arm, tx_arm = 'common/chr/' + rows[0][0], 'dx11/chr/' + rows[0][1]
                parties = [(md_arm, tx_arm)] + [x for x in parties if '/_uniform/s000101/' in x[0]]     # armure (sans maillot) + chaussures
                D_arm = os.path.join(ICI, 'sortie', 'MesEsprits', 'assets')
                rel_arm = 'chr/_armd/%s/%s_10.g4tx' % (a_.get('modele'), a_.get('modele'))
                if not os.path.isfile(os.path.join(D_arm, rel_arm)):
                    D_arm = rel_arm = None                       # pas de texture à moi : celle de l'armure du jeu
        if tenue:
            e_ = copies_outfits.registre(CFG).get(tenue) or {}
            rows = copies_tenues._parties(D)['clothes'].get(e_.get('source') or '') or []
            if rows:
                r0, cm, cx = rows[0], (lambda x: 'common/chr/' + x), (lambda x: 'dx11/chr/' + x)
                md_arm, tx_arm = cm(r0[0]), cx(r0[1])
                parties = [(md_arm, tx_arm)]
                for i_md, i_tx in ((6, 7), (8, 9)):             # peau des bras, manches
                    if len(r0) > i_md and isinstance(r0[i_md], str) and isinstance(r0[i_tx], str):
                        parties.append((cm(r0[i_md]), cx(r0[i_tx])))
                parties.append(('common/chr/_uniform/s000101/s00010%d.g4md' % t, 'dx11/chr/c000101/c000101.g4tx'))   # chaussures
                D_arm = os.path.join(CFG['outil_dir'], 'sortie', 'MesTenues', 'assets')
                rel_arm = 'chr/_uniform/%s/%s_10.g4tx' % (e_.get('modele'), e_.get('modele'))
                if not os.path.isfile(os.path.join(D_arm, rel_arm)):
                    D_arm = rel_arm = None
        if info:
            tete = 'common/chr/' + info['tete']
            tx = [os.path.relpath(f, D).replace('\\', '/') for f in sorted(glob.glob(os.path.join(D, 'dx11', 'chr', os.path.dirname(info['tete']), '*.g4tx')))]
            parties.append((tete, None))
        else:
            tx = ['dx11/chr/_face/21_MANNEQUIN/c21000010/c21000010.g4tx']
            parties.append(('common/chr/_face/21_MANNEQUIN/c21000010/c21000010.g4md', None))
        dossier = 'joueur_' + (code or 'generique') + ('_' + maillot + '_' + cote if lignes else '')
        if md_arm:                                       # (24/11) dossier à part, refait quand la texture de ma copie change
            dossier = 'joueur_%s_%s_%d' % ('tenue' if tenue else 'armure', tenue or armure, int(os.path.getmtime(os.path.join(D_arm, rel_arm))) if rel_arm else 0)
        liste_tx = sorted({x for _, x in parties if x and not (rel_arm and x == tx_arm)} | set(tx))
        noms = _textures_png(dossier, liste_tx)
        if rel_arm:                                      # (24/11) + ses masques (msk / sp / spm) : les shaders du jeu les lisent
            noms = noms + _textures_png(dossier, [rel_arm], tout=True, data_dir=D_arm)
        elif md_arm:
            _textures_png(dossier, [tx_arm], tout=True)
        tete_code = os.path.basename(parties[-1][0])[:-5]
        alias = [(r'^u0001\d\d', 'u000101'), (r'^s00010\d', 's000101'), (r'^sk0001\d\d', 'sk000101'), (r'^(eye|mouth)_10$', tete_code + '_10')]
        ms = []
        for md, _ in parties:
            b_md, b_mg = open(os.path.join(D, md), 'rb').read(), open(os.path.join(D, md[:-2] + 'mg'), 'rb').read()
            lot = modele.lire(b_md, b_mg, sk, noms, CACHE, md + '#%d' % t, alias)
            for m in lot:                                  # pour le rendu Direct3D des acteurs (AtelierD3D/acteurs.py)
                m['_md'], m['_mg'] = b_md, b_mg
            # (15/11/2026) TEXTURE PAR LE MATÉRIAU (LU : tête c11260010, maillage 0 « c11260010_20M » -> matériau 2 -> c11260010_20,
            # yeux / bouche -> c11260010_10 = la planche d'expressions). Avant, par le nom du maillage : les noms lus ne sont pas dans
            # l'ordre des maillages et la planche d'expressions allait sur les cheveux.
            _texture_par_materiau(md, dict(parties).get(md) or (tx[0] if tx else None), lot, noms)
            # joueur mannequin : ENTIÈREMENT noir (maillot, chaussures, peau, tête ; choix de l'utilisateur, 13/11/2026)
            # (24/11) sauf l'armure qu'il porte (aperçu de mise en armure)
            if not info and md != md_arm and not tenue:   # (27/11) mannequin d'une tenue : gris, comme la boutique du jeu
                for m in lot:
                    m['noir'] = True
            ms += lot
    else:
        d = anim._dossier_chr(os.path.join(D, 'common'), code)          # chr/_keshin, chr/_waza ou chr/<code>
        if not d:
            # (17/11/2026, retour de muku : « dans la Botte du PD, Lancelot a disparu ») modèle qui n'existe que dans un mod
            # (k000021 = Lancelot de ZanUltimateMod, chargé par sa cinématique) : lu dans la racine superposée de ce mod
            D = racine_avec_modele(code) or D
            d = anim._dossier_chr(os.path.join(D, 'common'), code)
        code_f = code                                   # nom des fichiers du modèle
        nv_code = modele_remplace(code) if code and not os.path.exists(os.path.join(CFG['data_dir'], 'common', 'chr', '_keshin', code)) else None
        if nv_code:                                     # (17/11/2026) apparence remplacée par un mod ([[character]])
            D2 = racine_avec_modele(nv_code)
            d2 = anim._dossier_chr(os.path.join(D2, 'common'), nv_code) if D2 else None
            if d2:
                D, d, code_f = D2, d2, nv_code
        if not d:
            raise ValueError('modèle introuvable : ' + str(code))
        base = os.path.join(d, code_f)
        pk = open(base + '.g4pkm', 'rb').read()
        sk = anim.lire_g4sk(pk)
        a = pk.find(b'G4MD')
        rel = os.path.relpath(d, os.path.join(D, 'common')).replace('\\', '/')
        tx = 'dx11/%s/%s.g4tx' % (rel, code_f)
        liste_tx = [tx] if os.path.exists(os.path.join(D, tx)) else []
        # (25/11) modèle qui n'existe que dans un mod (Tiger fang ev63_86020, orbes k002091 de Mukuro) : ses textures sous
        # « <code>~<mod> », le même nom que l'objet lu dans la racine du mod (objet() : ob.nom) ; sans cela, une texture
        # retouchée dans la liste (clé « ev63_86020~InazumaFantasy/… ») n'atteignait pas l'acteur (clé « ev63_86020/… »)
        dossier = code_f
        if code_f == code and os.path.normcase(D) != os.path.normcase(CFG['data_dir']):
            from moteur import racines as _rac
            mod_d = next((k for k, v in list(_rac._memo.items()) if os.path.normcase(v[1] or '') == os.path.normcase(D)), None)
            if mod_d and ':' not in str(mod_d):
                dossier = '%s~%s' % (code_f, mod_d)
        noms = _textures_png(dossier, liste_tx, data_dir=D)
        b_md, b_mg = pk[a:], open(base + '.g4mg', 'rb').read()
        ms = modele.lire(b_md, b_mg, sk, noms, CACHE, dossier)
        for m in ms:
            m['_md'], m['_mg'] = b_md, b_mg
    # ombrage du jeu : carte d'ombres <texture>oc et couleur de contour <texture>line (8 x 8 unie)
    if quoi == 'joueur' and info:                       # (pas le mannequin noir des techniques : il n'en a pas besoin)
        # (26/11) masques msk tout de suite (avant : seulement plus tard, dans un fil, pour Direct3D) : la vue en tire la peau du
        # corps comme chr_toon_edit (couleur = texture × lerp(1, u_skinColor, msk.r))
        try:
            _textures_png(dossier, liste_tx, True)
        except Exception as ex:
            print('masques du joueur :', ex)
    for m in ms:
        t = m['texture']
        m['masque'] = (dossier + '/' + t + 'msk') if quoi == 'joueur' and t and (t + 'msk') in noms and not m.get('noir') \
            and os.path.exists(os.path.join(CACHE, dossier, t + 'msk.png')) else None
        m['ombre'] = (dossier + '/' + t + 'oc') if t and (t + 'oc') in noms else None
        m['contour'] = couleur_moyenne(os.path.join(CACHE, dossier, t + 'line.png')) if t and (t + 'line') in noms else None
        m['texture'] = (dossier + '/' + t) if t else None
    # rendu Direct3D (13/11/2026) : le modèle est aussi enregistré pour AtelierD3D (matériaux et sommets du jeu, vrais shaders)
    try:
        d3d = os.path.join(os.path.dirname(ICI), 'AtelierD3D')
        if d3d not in sys.path:
            sys.path.insert(0, d3d)
        import acteurs as _act
        from moteur import shaders as _shm
        for m in ms:
            m['_dossier'], m['_noms'] = dossier, noms
        threading.Thread(target=_textures_png, args=(dossier, liste_tx, True, D), daemon=True).start()   # masques (une fois)
        _act.enregistrer('joueur' if quoi == 'joueur' else 'chr', code_reg, ms, _shm.table(D))
        # (15/11/2026) maillage sans texture du même nom (objets de technique : maillage « ev60_01030_20 », texture
        # « ev60_00830_20 ») : la 1re texture de SON matériau (case 0, comme le rendu Direct3D)
        if quoi != 'joueur' and any(not m.get('texture') for m in ms):
            mats, ents = _act.materiaux(b_md, noms, _shm.table(D)), _act.maillages(b_md)
            for m in ms:
                i = m.get('_i')
                if m.get('texture') or i is None or i >= len(ents) or ents[i]['mat'] >= len(mats):
                    continue
                t0 = (mats[ents[i]['mat']].get('tex') or [None])[0]
                if t0 and not t0.startswith('?'):
                    m['texture'] = dossier + '/' + t0
    except Exception as ex:
        print('acteurs Direct3D :', ex)
    # (21/11, LU nie.exe 0x140591fc0 / 0x140591d60) ordre de dessin des pièces : clé = entier G4MD +0x72 du matériau, seau = octet +8
    # de la fiche du matériau (table +0x64) ; la page en tire l'ordre (app.js ordrePieces), comme le lecteur natif
    for m in ms:
        try:
            md_, i_ = m.get('_md'), m.get('_i')
            if md_ is None or i_ is None:
                continue
            b_, im_ = struct.unpack_from('<H', md_, 0x0A)[0], md_[0xA0 + 0x50 * i_ + 0x43]
            m['cle'] = struct.unpack_from('<I', md_, (b_ + struct.unpack_from('<H', md_, 0x72)[0] + im_) * 4)[0]
            m['seau'] = struct.unpack_from('<b', md_, (b_ + struct.unpack_from('<H', md_, 0x64)[0] + im_ * 4) * 4 + 8)[0]
        except struct.error:
            pass
    b = modele.binaire(ms)
    with _verrou:
        _modeles[cle] = b
    return b


def geometrie_binaire(chemin):
    """toutes les pièces d'un objet : en-tête JSON (longueurs) + flottants positions, octets couleurs, u16 indices"""
    ob = objet(chemin)
    morceaux, meta = [], []
    for i in range(len(ob.pieces)):
        pos, col, idx, uv = ob.geometrie(i)
        if '/chr/' in chemin:                   # personnages : l'attribut « couleur » sert à l'ombrage, pas à la couleur
            col = b'\xff' * len(col)
        sup = ob.uv_sup(i) if pos else []
        c1 = ob.couleur1(i) if pos else None
        nor = ob.normales(i) if pos and '/chr/' not in chemin else None
        tan = ob.normales(i, 'tan') if nor else None
        pe = ob.peau(i) if pos and '/chr/' not in chemin else None     # maillage à peau : 4 poids (f32) + 4 n° d'os (u8) par sommet
        meta.append({'nv': len(pos) // 3, 'ni': len(idx), 'uvs': len(sup), 'col1': bool(c1), 'nor': bool(nor), 'tan': bool(tan), 'peau': bool(pe)})
        morceaux.append(struct.pack('<%df' % len(pos), *pos) + bytes(col) + struct.pack('<%df' % len(uv), *uv)
                        + struct.pack('<%dH' % len(idx), *idx) + b'\0' * ((-2 * len(idx)) % 4)
                        + b''.join(struct.pack('<%df' % len(u), *u) for u in sup)      # TEXCOORD1..4
                        + (c1 or b'')                                                   # COLOR1
                        + (struct.pack('<%df' % len(nor), *nor) if nor else b'')        # NORMAL
                        + (struct.pack('<%df' % len(tan), *tan) if tan else b'')        # TANGENT
                        + (struct.pack('<%df' % len(pe[0]), *pe[0]) + bytes(pe[1]) if pe else b''))   # BLENDWEIGHT, BLENDINDICES
    entete = json.dumps(meta).encode()
    entete += b' ' * ((-len(entete)) % 4)
    return struct.pack('<I', len(entete)) + entete + b''.join(morceaux)


# (25/11/2026, demande d'un joueur : textures et modèles pour Substance Painter) fichier fait par la page (PNG d'une texture,
# .glb du modèle ouvert) -> dossier « exports » de l'Atelier ; l'Explorateur s'ouvre dessus, le fichier choisi
EXPORTS = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'exports')


def enregistrer_export(d):
    import base64, re
    nom = re.sub(r'[\\/:*?"<>|\x00-\x1f]+', '_', str(d.get('nom') or '')).strip(' .')[:120]
    if not nom or os.path.splitext(nom)[1].lower() not in ('.png', '.glb'):
        return {'ok': False, 'erreur': 'nom de fichier refusé'}
    os.makedirs(EXPORTS, exist_ok=True)
    chemin = os.path.join(EXPORTS, nom)
    with open(chemin, 'wb') as f:
        f.write(base64.b64decode(d.get('donnees') or ''))
    if d.get('ouvrir') and os.name == 'nt':
        try:
            subprocess.Popen(['explorer', '/select,', chemin])
        except Exception:
            pass
    return {'ok': True, 'chemin': chemin}


# (15/11/2026) préréglages de couleurs et projets en cours (sauvegarde automatique de l'Atelier)
PREREGLAGES =os.path.join(os.path.dirname(os.path.abspath(__file__)), 'prereglages.json')
PROJETS = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'projets')


def lire_prereglages():
    try:
        return json.load(open(PREREGLAGES, encoding='utf-8'))
    except (OSError, ValueError):
        return []


def fichier_projet(cle):
    import re
    return os.path.join(PROJETS, (re.sub(r'[^\w.-]', '_', str(cle)) or 'sans_nom')[:80] + '.json')


def liste_projets():
    """(15/11/2026) hub « Mes créations » : projets en cours (sauvegarde automatique), du plus récent au plus ancien"""
    out = []
    for f in glob.glob(os.path.join(PROJETS, '*.json')):
        # (15/11/2026) les .ancien.json (« Repartir de zéro », avant) sont aussi des créations : montrées au hub
        try:
            e = json.load(open(f, encoding='utf-8'))
        except (OSError, ValueError):
            continue
        ch = e.get('champs') or {}
        couleurs = list(e.get('apercu') or [])
        if not couleurs:                       # anciens projets : couleurs choisies (matériaux, teintes, remplacements)
            couleurs = [c.get('hex') for c in list((e.get('coulMat') or {}).values()) + list((e.get('teinteSom') or {}).values())
                        + list((e.get('teintePtl') or {}).values()) if isinstance(c, dict) and c.get('hex')]
            couleurs += [r.get('vers') for r in e.get('recette') or [] if r.get('vers')]
        vus = []
        for c in couleurs:
            if c and c not in vus:
                vus.append(c)
        perso = e.get('onglet') in ('esprits', 'totems')
        # (28/11) projets d'avant les noms d'armures (« Armure ka000101 ») : le nom actuel (« Armure · Pégase »)
        nom_ = e.get('nom')
        if e.get('onglet') == 'armures' and nom_ == 'Armure %s' % e.get('code'):
            nom_ = (JEU_CODE.get(('armures', e.get('code'))) or {}).get('nom') or nom_
        vign = e.get('vignette')
        if not vign:                           # pas encore d'image de l'aperçu : la 1re texture retouchée
            vign = next(iter((e.get('textures') or {}).values()), None)
        out.append({'vignette': vign, 'vignetteTexture': not e.get('vignette'),
                    'cle': os.path.basename(f)[:-5], 'code': e.get('code'), 'onglet': e.get('onglet') or 'techniques',
                    # (21/11) le champ de nom de SON onglet (avant : celui des techniques pour tout -> objets, tenues,
                    # armures… prenaient le nom de la dernière technique) ; sinon le nom de l'élément
                    'base': nom_, 'titre': ch.get({'techniques': 'f-nom', 'esprits': 'p-nom', 'totems': 'p-nom', 'personnages': 'cp-nom',
                                                          'tenues': 'ct-nom', 'armures': 'ca-nom', 'objets': 'oj-nom-copie'}.get(e.get('onglet') or 'techniques', ''))
                                                   or nom_, 'date': e.get('date'),
                    'textures': len(e.get('textures') or {}), 'materiaux': len(e.get('coulMat') or {}),
                    'teintes': len(e.get('teinteSom') or {}) + len(e.get('teintePtl') or {}), 'remplacements': len(e.get('recette') or []),
                    'couleurs': vus[:4], 'cree': e.get('cree')})       # (22/11) création faite depuis ce projet
    out.sort(key=lambda x: x.get('date') or '', reverse=True)
    return out


def lier_anciens_projets(projets, creations):
    """(23/11, muku : « test technique a eu ses textures reset », « mon Pégase couleurs aussi ») les créations faites AVANT le
    lien projet -> création (22/11) n'avaient pas de projet lié : leur projet restait dans « À continuer » comme un travail en
    cours ; retiré de la liste (🗑), « Modifier » rouvrait l'élément du jeu, couleurs d'origine. Chaque création sans projet lié
    adopte celui que « Modifier » ouvrait déjà (app.js projetDe) : même nom, sinon le plus récent sur le même élément quand
    une seule création en vient, enregistré AVANT la création. Lié : hors de « À continuer », il ne peut plus être jeté."""
    import datetime

    def quand(p):
        try:
            return datetime.datetime.fromisoformat(str(p.get('date')).replace('Z', '+00:00')).timestamp()
        except ValueError:
            return None
    lies = {(p['cree'].get('mod'), str(p['cree'].get('code'))) for p in projets if isinstance(p.get('cree'), dict)}
    for c in creations:
        if not c.get('mod') or c.get('code') is None or (c['mod'], str(c['code'])) in lies:
            continue
        libres = [p for p in projets if not p.get('cree') and p.get('onglet') == c.get('onglet') and str(p.get('code')) == str(c.get('base'))]
        p = next((p for p in libres if p.get('titre') == c.get('nom')), None)
        if p is None and sum(1 for x in creations if x.get('base') == c.get('base') and x.get('onglet') == c.get('onglet')) == 1:
            p = next((p for p in libres if quand(p) is not None and c.get('date') and quand(p) <= float(c['date']) + 120), None)
        if p is None:
            continue
        f = fichier_projet(p['cle'])
        try:
            e = json.load(open(f, encoding='utf-8'))
            e['cree'] = {'mod': c['mod'], 'code': str(c['code'])}
            tmp = f + '.tmp'
            json.dump(e, open(tmp, 'w', encoding='utf-8'), ensure_ascii=False)
            os.replace(tmp, f)
        except (OSError, ValueError):
            continue
        p['cree'] = e['cree']
        lies.add((c['mod'], str(c['code'])))
    return projets


def mod_a_jour(mod, _memo={}):
    """(15/11/2026) TOUS les fichiers de sortie/<mod> sont-ils dans <jeu>/mods/<mod> ? Avant, le hub ne comparait qu'un
    fichier texte par création : une réparation des modèles (fichiers .g4pkm, scènes) restait « Installé ». Taille + date
    (l'installation garde les dates) ; si la date diffère, contenu comparé pour les fichiers de moins de 4 Mo."""
    src = os.path.join(CFG['outil_dir'], 'sortie', mod)
    dst = os.path.join(CFG.get('jeu_dir') or '', 'mods', mod)
    if not os.path.isdir(src) or not os.path.isdir(dst):
        return False
    for r, ds, fs in os.walk(src):
        ds[:] = [d for d in ds if d not in ('_retires', '_construction', 'ancienne_sortie')]
        for f in fs:
            if f.startswith('outil_') and f.endswith('.json'):
                continue
            a = os.path.join(r, f)
            b = os.path.join(dst, os.path.relpath(a, src))
            if not os.path.isfile(b):
                return False
            sa, sb = os.stat(a), os.stat(b)
            if sa.st_size != sb.st_size:
                return False
            if abs(sa.st_mtime - sb.st_mtime) > 2:
                if sa.st_size > 4 * 1024 * 1024 or open(a, 'rb').read() != open(b, 'rb').read():
                    return False
    return True


# ------------------------------------------------------------------ (22/11) STATS : réglées après le visuel (moteur/stats.py)
def _creation_stats(mod, code):
    """-> (genre, registre, clé dans le registre, entrée, valeurs du jeu, sauver()) ; None si inconnue"""
    from moteur import stats as st
    if mod == 'MesTechniques':
        f = os.path.join(ICI, 'sortie', 'MesTechniques', 'outil_techniques.json')
        reg = json.load(open(f, encoding='utf-8')) if os.path.isfile(f) else {}
        k = next((n for n, e in reg.items() if e.get('key') == code), None)
        if k is None:
            return None
        jeu = st.jeu_technique(CFG['data_dir'], reg[k]['base'])
        # (25/11) copie d'une technique de mod (Tiger fang) : l'élément du mod est sa valeur « d'origine » et reste écrit
        em = reg[k].get('element_mod')

        def sauver():
            json.dump(reg, open(f, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
            toml = os.path.join(ICI, 'sortie', 'MesTechniques', 'content', 'techniques', k + '.toml')
            st.appliquer_technique(toml, st.lignes_technique(dict({'element': em} if em else {}, **(reg[k].get('stats') or {})), jeu))
        return 'technique', reg, k, reg[k], (dict(jeu, element=em) if em else jeu), sauver
    if mod == 'MesEsprits':
        sortie = os.path.join(ICI, 'sortie', 'MesEsprits')
        reg = esprits.registre(sortie)
        # (23/11, demande de muku : « les armures maintenant ») ARMURE (carte « Armure de … », code = son modèle kz…) : sa
        # ligne AURA_CMD_INFO (wao…/was…) comme un esprit ; registre outil_armures.json (clé = code de ma copie d'esprit)
        ra = armures_copies.registre(CFG)
        ka = next((x for x, a in ra.items() if a.get('modele') == code or x == code and code not in reg), None)
        if ka is not None and code not in reg:

            def sauver_a():
                json.dump(ra, open(os.path.join(sortie, 'outil_armures.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
                armures_copies.ecrire_vrfw(CFG, ra)
            return 'armure', ra, ka, ra[ka], st.jeu_esprit(CFG['data_dir'], ra[ka]['was']), sauver_a
        if code not in reg:
            return None

        def sauver():
            esprits.ecrire_vrfw(CFG, sortie, reg)
            json.dump(reg, open(os.path.join(sortie, 'outil_esprits.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
        return 'esprit', reg, code, reg[code], st.jeu_esprit(CFG['data_dir'], reg[code].get('technique')), sauver
    if mod == 'MesPersonnages':
        reg = copies_persos.registre(CFG)
        if code not in reg:
            return None

        def sauver():
            copies_persos._sauver(CFG, reg)
            copies_persos._ecrire_contenu(CFG, reg)
        return 'personnages', reg, code, reg[code], {}, sauver
    return None


def bannieres_esprits():
    """(23/11, muku : « tu n'as pas fait les bannières pour les totems et les armures ») éditeur de bannières : mes copies
    d'esprits et de totems (bannière = leur nom, faite automatiquement ; modèle = celle de l'original) et mes armures
    (bannière ARMED, commune dans le jeu : la leur à part)"""
    sortie = os.path.join(ICI, 'sortie', 'MesEsprits')
    reg = esprits.registre(sortie)
    out = []
    for k, c in sorted(reg.items()):
        totem = esprits.est_totem(c)
        el = (c.get('stats') or {}).get('element') or (None if totem else esprits.invocation_du_jeu(CFG['data_dir'], c.get('technique'))[0])
        out.append({'genre': 'totem' if totem else 'esprit', 'id': k, 'nom': c.get('nom') or k, 'base': c.get('base'),
                    'style': 'totem' if totem else 'esprit:' + (el or 'wind')})       # (24/11) police conseillée : celle du jeu
    for k, a in sorted(armures_copies.registre(CFG).items()):
        out.append({'genre': 'armure', 'id': armures_copies.id_banniere_armee(k), 'cle': k, 'nom': a.get('nom') or k, 'base': 'aura_armed01', 'style': 'armure'})   # (24/11) lettres du jeu (formes de la bannière d'armure)
    return out


def banniere_de(genre, k, e):
    """bannière d'un esprit / totem (son nom : automatique, ou faite dans l'éditeur) ou d'une armure (ARMED : celle du jeu,
    ou la sienne faite dans l'éditeur) : {id, base, editeur}"""
    sortie = os.path.join(ICI, 'sortie', 'MesEsprits')
    if genre == 'armure':
        return {'id': armures_copies.id_banniere_armee(k), 'base': 'aura_armed01', 'editeur': armures_copies.banniere_armee_faite(CFG, k)}
    try:
        suivi = json.load(open(os.path.join(sortie, 'outil_bannieres.json'), encoding='utf-8'))
    except (OSError, ValueError):
        suivi = {}
    return {'id': k, 'base': e.get('base'), 'editeur': suivi.get(k) == 'editeur'}


def telop_invocation(code_tech, code_telop):
    """(24/11, retour de muku : « pas de bannière sur la preview de l'esprit guerrier, le totem aussi ») bannière montrée par
    l'aperçu d'invocation / de mise en armure : « <CHARA_ID> » = ma copie (sa bannière de la sortie MesEsprits : son nom ou
    celle de l'éditeur ; sinon celle de l'original) ; « aura_armed01 » = la bannière ARMED de mon armure si je l'ai faite"""
    copie = str(code_tech).split('_', 1)[1].split('~')[0]
    if code_telop == '<CHARA_ID>':
        base = (esprits.registre(os.path.join(ICI, 'sortie', 'MesEsprits')).get(copie) or {}).get('base')
        return banniere_esprit_png(copie, base or copie)
    if code_telop == 'aura_armed01' and str(code_tech).startswith('armure_'):
        return banniere_esprit_png(armures_copies.id_banniere_armee(copie), 'aura_armed01')
    return telop_png(code_telop)


def banniere_esprit_png(id_, base):
    """image de la bannière actuelle : celle de la sortie MesEsprits si elle existe, sinon celle du jeu (modèle)"""
    f = os.path.join(ICI, 'sortie', 'MesEsprits', 'content', 'telops', 'any', os.path.basename(id_ or '') + '.png')
    return f if id_ and os.path.isfile(f) else telop_png(os.path.basename(base or ''))


def enregistrer_banniere_esprit(d):
    sortie = os.path.join(ICI, 'sortie', 'MesEsprits')
    cible = next((x for x in bannieres_esprits() if x['id'] == d.get('id') and x['genre'] == d.get('genre')), None)
    if not cible or not d.get('image'):
        return {'ok': False, 'erreur': 'création inconnue'}
    dos = os.path.join(sortie, 'content', 'telops', 'any'); os.makedirs(dos, exist_ok=True)
    export.ecrire_png_banniere(d['image'], os.path.join(dos, cible['id'] + '.png'))
    if cible['genre'] == 'armure':
        armures_copies.ecrire_vrfw(CFG, armures_copies.registre(CFG))     # scène copiée -> bannière à part, [[telop]]
        quoi = 'bannière ARMED de %s' % cible['nom']
    else:
        f_suivi = os.path.join(sortie, 'outil_bannieres.json')     # « editeur » : plus refaite automatiquement depuis le nom
        try:
            suivi = json.load(open(f_suivi, encoding='utf-8'))
        except (OSError, ValueError):
            suivi = {}
        suivi[cible['id']] = 'editeur'
        json.dump(suivi, open(f_suivi, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
        esprits.ecrire_bannieres(CFG, sortie, esprits.registre(sortie))
        quoi = 'bannière de %s' % cible['nom']
    return {'ok': True, 'rapport': ['%s remplacée' % quoi, 'pas encore dans le jeu : « Installer » sur sa carte dans Mes créations']}


def stats_creation(mod, code, langue='fr'):
    from moteur import stats as st
    c = _creation_stats(mod, code)
    if not c:
        return {'ok': False, 'erreur': 'création inconnue'}
    genre, _, k_reg, e, jeu, _ = c
    # (22/11) l'original COMME EN JEU pour le menu (l'écriture garde les valeurs du jeu de base : _creation_stats) :
    # technique = jeu + mods activés (HissatsuReforged…) ; joueur = carte de l'original (chara_param + mods qui la redéfinissent)
    try:
        if genre == 'technique':
            jeu = st.jeu_technique_en_jeu(CFG, e.get('base'))
        elif genre == 'personnages':
            jeu = st.jeu_joueur(CFG, e.get('carte_origine'))
    except Exception as ex:
        print('stats : original illisible', ex)
    src = jeu.pop('_source', None) if isinstance(jeu, dict) else None
    r = {'ok': True, 'genre': genre, 'nom': e.get('nom'), 'champs': st.CHAMPS[genre], 'jeu': jeu, 'stats': e.get('stats'), 'source': src}
    if genre == 'technique':               # (23/11) « En attente de stats / cosmétique » : couleur du tir, traînée, prix, bannière
        r['cosmetique'] = export.cosmetique_actuelle(os.path.join(ICI, 'sortie', 'MesTechniques'), k_reg)
        r['tir'] = str(e.get('base', '')).startswith('whs')
        r['degrades_tir'] = st.degrades_tir(CFG)       # (23/11) images des couleurs du tir (dégradé du jeu)
    if genre == 'esprit':       # (23/11, muku : carte Keshin du Tableau des compétences) sa technique (liée, sinon d'origine)
        try:
            lie = e.get('technique_liee')
            if not lie:
                cat = coups.catalogue(CFG['data_dir'], cache_txt())
                o = next((x for x in cat if x['code'] == e.get('technique')), {})
                lie = next((x for x in cat if x['id'] == o.get('liee')), None)
            if lie:
                r['technique'] = {'nom': lie.get('nom'), 'code': lie.get('code')}
        except Exception as ex:
            print('technique de l\'esprit :', ex)
    if genre in ('esprit', 'armure'):       # (24/11, muku : « un bouton comme les techniques pour faire sa bannière ») sa bannière
        r['banniere'] = banniere_de(genre, k_reg, e)
    if genre in ('esprit', 'armure'):       # (23/11, muku : « tout sauf compatible ») BONUS et EFFET UNIQUE (moteur/effets_esprits.py)
        try:
            from moteur import effets_esprits as EE
            lg = langue if langue in ('fr', 'en', 'es') else 'fr'     # textes des effets dans la langue de l'Atelier (textes du jeu)
            r['effets_origine'] = EE.de_l_original(CFG, e.get('was') if genre == 'armure' else e.get('technique'), lg)
            r['catalogue_effets'] = EE.catalogue(CFG, lg)
            r['effets'] = e.get('effets')
        except Exception as ex:
            print('effets de l\'esprit :', ex)
    if genre == 'esprit' and (e.get('dossier') == '_keshin' or esprits.est_totem(e)):      # (23/11) apparitions possibles (+ totems)
        try:
            noms = {p['code']: p['nom'] for p in PERSOS}
            el0, sc0 = esprits.invocation_du_jeu(CFG['data_dir'], e.get('technique'))
            sc0 = esprits.scene_invocation_choix(CFG, e)           # (23/11) totem : ev83_00010
            r['invocations'] = [dict(x, nom=noms.get(x['esprit'], x['esprit'])) for x in esprits.invocations_possibles(CFG, e)]
            r['invocation_origine'] = {'scene': sc0, 'esprit': e.get('base'), 'element': el0}
            inv = e.get('invocation') or {}
            r['invocation'] = {'scene': inv['scene'], 'esprit': inv['esprit'], 'choisie': bool(inv.get('choisie'))} if inv.get('etat') == 'emprunt' else None
        except Exception as ex:
            print('invocations :', ex)
    if genre == 'armure':       # (23/11) mises en armure possibles (scène ev81 + esprit dont ma copie prend les gestes)
        try:
            noms = {p['code']: p['nom'] for p in PERSOS}
            k0, sc0 = armures_copies.esprit_et_scene(CFG['data_dir'], e['was'])
            r['invocations'] = [dict(x, nom=noms.get(x['esprit'], x['esprit'])) for x in armures_copies.mises_possibles(CFG, e, k_reg)]
            r['invocation_origine'] = {'scene': sc0, 'esprit': armures_copies.base_esprit(CFG, k_reg) if sc0 == 'ev81_00010' else k0}
            m = e.get('mise') or {}
            r['invocation'] = {'scene': m['scene'], 'esprit': m['esprit'], 'choisie': True} if m.get('choisie') else None
            r['esprit'] = k_reg                    # ma copie d'esprit (portrait, aperçu « armure_<copie> »)
            # nom de l'armure du jeu (sa commande d'aura wao… / was…, dans la langue de l'Atelier), sinon celui de l'onglet Armures
            o_ = next((x for x in coups.catalogue(CFG['data_dir'], cache_txt()) if x['code'] == e.get('was')), {})
            r['nom_origine'] = o_.get('nom') or (JEU_CODE.get(('armures', e.get('armure'))) or {}).get('nom') or e.get('armure')
            r['esprit_origine'] = armures_copies.base_esprit(CFG, k_reg)
            r['element_origine_scene'] = {v: k for k, v in armures_copies.SCENES_ARMURE.items()}.get(sc0, '')
        except Exception as ex:
            print('mises en armure :', ex)
    return r


def _telop_origine(base):
    t = PAR_CODE.get(base or '')
    return (techniques.lire_cinematique(CFG['data_dir'], t['cinematique'])['telop'] if t else None) or base


def regler_stats(mod, code, brut, cosm=None, invoc=None, effets=None):
    from moteur import stats as st
    c = _creation_stats(mod, code)
    if not c:
        return {'ok': False, 'erreur': 'création inconnue'}
    genre, reg, k, e, jeu, sauver = c
    try:
        reg[k]['stats'] = st.nettoyer(genre, brut)
    except ValueError as ex:
        return {'ok': False, 'erreur': str(ex)}
    inv = None
    if genre == 'esprit' and isinstance(invoc, dict):       # (23/11) apparition choisie (ou « auto » : selon l'élément)
        reg[k].pop('invocation', None)
        if invoc.get('scene') and invoc.get('esprit'):
            ok = [x for x in esprits.invocations_possibles(CFG, reg[k]) if x['scene'] == invoc['scene'] and x['esprit'] == invoc['esprit']]
            if not ok:
                return {'ok': False, 'erreur': 'apparition impossible pour cette copie'}
            if not (ok[0]['esprit'] == reg[k]['base'] and ok[0]['scene'] == esprits.scene_invocation_choix(CFG, reg[k])):
                reg[k]['invocation'] = dict(ok[0], etat='emprunt', choisie=True)
    if genre == 'esprit':                  # (23/11) élément changé : l'invocation de cet élément (moteur/esprits.py)
        try:
            inv = esprits.plan_invocation(CFG, reg[k])
        except Exception as ex:            # (lecture des animations impossible : l'invocation d'origine reste)
            print('invocation :', ex)
        if inv:
            reg[k]['invocation'] = inv
        else:
            reg[k].pop('invocation', None)
    if genre == 'armure' and isinstance(invoc, dict):       # (23/11) mise en armure choisie (ou « auto » : selon l'élément)
        reg[k].pop('mise', None)
        if invoc.get('scene') and invoc.get('esprit'):
            ok = [x for x in armures_copies.mises_possibles(CFG, reg[k], k) if x['scene'] == invoc['scene'] and x['esprit'] == invoc['esprit']]
            if not ok:
                return {'ok': False, 'erreur': 'mise en armure impossible pour cette copie'}
            reg[k]['mise'] = dict(ok[0], choisie=True)
    if genre in ('esprit', 'armure') and isinstance(effets, dict):     # (23/11) bonus / effet unique : {bonus: [lignes], uniques: [lignes]} ou {} = l'original
        propres = {x: [[int(v) for v in l][:9] for l in effets.get(x) or [] if isinstance(l, list) and l]
                   for x in ('bonus', 'uniques') if effets.get(x) is not None}
        if propres:
            reg[k]['effets'] = propres
        else:
            reg[k].pop('effets', None)
    sauver()
    ch = st._changes(reg[k]['stats'], jeu) if genre != 'personnages' else reg[k]['stats']
    rapport = ['%s : %s' % (e.get('nom'), ', '.join('%s = %s' % (x, y) for x, y in ch.items()) if ch else "valeurs de l'original gardées")]
    nom_el = dict(st.CHOIX_ELEMENT).get((inv or {}).get('element'), '')
    if inv and inv['etat'] == 'emprunt':
        rapport.append('invocation : celle de l’élément %s (%s), avec les animations de %s' % (nom_el, inv['scene'], inv['esprit']))
    elif inv:
        rapport.append('invocation : aucun esprit de l’élément %s n’a les mêmes os, l’invocation d’origine reste' % nom_el)
    if genre == 'armure':
        try:
            pl = armures_copies.plan_mise(CFG, reg[k], k)
        except Exception as ex:
            print('mise en armure :', ex); pl = None
        if pl:
            rapport.append('mise en armure : %s, avec les gestes de %s' % (pl['scene'], pl['esprit']))
    if genre in ('esprit', 'armure') and reg[k].get('effets'):
        from moteur import effets_esprits as EE
        for x, nom in (('bonus', 'bonus'), ('uniques', 'effet unique')):
            if x in reg[k]['effets']:
                rapport.append('%s : %s' % (nom, ', '.join(EE.libelle(CFG, l[0]) for l in reg[k]['effets'][x]) or 'aucun'))
    if genre == 'technique' and isinstance(cosm, dict):
        rc = export.appliquer_cosmetique(CFG, k, cosm, _telop_origine(e.get('base')))
        if not rc.get('ok'):
            return rc
        rapport += rc['rapport'] or ['cosmétique : rien de changé']
    return {'ok': True, 'mod': mod, 'rapport': rapport}


# ------------------------------------------------------------------ (22/11, demande de muku) SUPPRIMER une création
def _ranger(racine, motifs, garde):
    """déplace dans <garde> les fichiers de <racine> dont le chemin contient un des motifs (nom, codes de la création) ;
    -> nombre de fichiers rangés (récupérables : rien n'est effacé)"""
    import re, shutil
    motifs = [m for m in motifs if m and len(m) >= 4]
    if not motifs or not os.path.isdir(racine):
        return 0
    rx = re.compile(r'(?<![0-9A-Za-z])(' + '|'.join(re.escape(m) for m in motifs) + r')(?![0-9])')
    n = 0
    for dossier in ('assets', 'content', 'addons', 'text'):
        for d, _, fs in os.walk(os.path.join(racine, dossier)):
            for f in fs:
                p = os.path.join(d, f)
                rel = os.path.relpath(p, racine)
                if rx.search(rel.replace(os.sep, '/')):
                    dst = os.path.join(garde, rel)
                    os.makedirs(os.path.dirname(dst), exist_ok=True)
                    shutil.move(p, dst)
                    n += 1
    for dossier in ('assets', 'content', 'addons', 'text'):            # dossiers restés vides
        for d, _, _ in sorted(os.walk(os.path.join(racine, dossier)), key=lambda x: -len(x[0])):
            try:
                if d != os.path.join(racine, dossier) and not os.listdir(d):
                    os.rmdir(d)
            except OSError:
                pass
    return n


def _retirer_bannieres(f, key):
    """enlève le [[telop]] id = key du fichier des bannières (partagé par toutes les techniques)"""
    if not os.path.isfile(f):
        return
    blocs = open(f, encoding='utf-8').read().split('\n[[telop]]')
    vise = lambda b: ('id = "%s"' % key) in b or ('id = "%s_' % key) in b      # + variantes
    garde = [blocs[0]] + [b for b in blocs[1:] if not vise(b)]
    open(f, 'w', encoding='utf-8').write('\n[[telop]]'.join(garde))
    return [b for b in blocs[1:] if vise(b)]          # (23/11) gardées avec la création retirée (corbeille : « Restaurer »)


def _noter_retrait(garde, **rec):
    """(23/11, muku : « voir et restaurer ce qu'on a supprimé ») fiche de la création retirée, à côté de ses fichiers :
    son entrée du registre (outil_*.json) et ce qu'il faut pour la remettre telle quelle (Corbeille de ⚙ Paramètres)"""
    os.makedirs(garde, exist_ok=True)
    rec['date'] = datetime.datetime.now().isoformat(timespec='seconds')
    json.dump(rec, open(os.path.join(garde, '_retire.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)


def supprimer_creation(mod, code, genre=None):
    from moteur import armures_copies, copies_outfits, objets_jeu
    sortie = os.path.join(ICI, 'sortie', mod or '')
    garde = os.path.join(sortie, '_retires', datetime.datetime.now().strftime('%Y%m%d_%H%M%S'))
    # utilisée ailleurs ? (techniques d'un joueur, technique liée d'un esprit) : on refuse, sinon le jeu chercherait un vide
    def utilisateurs(cle_mod, cle):
        u = ['%s (techniques du joueur)' % e.get('nom') for e in copies_persos.registre(CFG).values()
             if any(c.get('mod') == cle_mod and c.get('code') == cle for c in e.get('coups') or [])]
        if cle_mod == 'MesTechniques':
            u += ['%s (technique liée)' % e.get('nom') for e in esprits.contenu(CFG).values()
                  if ((e.get('technique_liee') or {}).get('code')) == cle]
        return u
    if mod == 'MesTechniques':
        f = os.path.join(sortie, 'outil_techniques.json')
        reg = json.load(open(f, encoding='utf-8')) if os.path.isfile(f) else {}
        nom = next((n for n, e in reg.items() if e.get('key') == code), None)
        u = utilisateurs('MesTechniques', code)
        if u:
            return {'ok': False, 'erreur': 'Utilisée par : ' + ', '.join(u) + '. Change-la d\'abord là-bas.'}
        if export.jeu_ouvert():
            return {'ok': False, 'erreur': 'Le jeu est ouvert : ferme-le d\'abord (la technique est aussi retirée du jeu).'}
        e = reg.get(nom) or {}
        if nom is None:                     # seulement dans le jeu : son nom et sa scène dans le registre ou les fichiers du mod du jeu
            jeu_ = os.path.join(CFG.get('jeu_dir') or '', 'mods', 'MesTechniques')
            fj_ = os.path.join(jeu_, 'outil_techniques.json')
            rj_ = json.load(open(fj_, encoding='utf-8')) if os.path.isfile(fj_) else {}
            nom = next((n for n, x in rj_.items() if x.get('key') == code), None)
            e = rj_.get(nom) or {}
            if nom is None:
                for t_ in glob.glob(os.path.join(jeu_, 'content', 'techniques', '*.toml')):
                    if ('key = "%s"' % code) in open(t_, encoding='utf-8').read():
                        nom = os.path.basename(t_)[:-5]
                        break
        fm = os.path.join(sortie, 'outil_modeles.json')
        modeles = json.load(open(fm, encoding='utf-8')) if os.path.isfile(fm) else {}
        codes_mod = [v for k, v in modeles.items() if nom and k.startswith(nom + '|')]
        motifs = [nom, code, e.get('id')] + codes_mod
        n = _ranger(sortie, motifs, garde) if nom else 0
        ban = _retirer_bannieres(os.path.join(sortie, 'content', 'telops', 'any', 'telops.toml'), code)
        if nom:
            _noter_retrait(garde, mod=mod, genre='technique', code=code, nom=e.get('nom') or nom, cle=nom, entree=e,
                           modeles={k: v for k, v in modeles.items() if k.startswith(nom + '|')}, bannieres=ban or [])
        # « Installer » ne fait qu'AJOUTER des techniques au jeu : celle-ci est donc aussi retirée du mod du jeu (rangée à part)
        jeu = os.path.join(CFG.get('jeu_dir') or '', 'mods', 'MesTechniques')
        nj = _ranger(jeu, motifs if nom else [code], os.path.join(garde, '_jeu'))
        _retirer_bannieres(os.path.join(jeu, 'content', 'telops', 'any', 'telops.toml'), code)
        if nom:
            reg.pop(nom, None)
            json.dump(reg, open(f, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
            for k in [k for k in modeles if k.startswith(nom + '|')]:
                modeles.pop(k)
            json.dump(modeles, open(fm, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
        fj = os.path.join(jeu, 'outil_techniques.json')
        if os.path.isfile(fj):
            rj = json.load(open(fj, encoding='utf-8'))
            if nom in rj or any(x.get('key') == code for x in rj.values()):
                rj = {k: x for k, x in rj.items() if k != nom and x.get('key') != code}
                json.dump(rj, open(fj, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
        return {'ok': True, 'rapport': ['technique supprimée : %d fichiers de l\'Atelier et %d du jeu rangés dans %s' % (n, nj, garde)]}
    if mod == 'MesEsprits' and genre == 'armures':
        reg = armures_copies.registre(CFG)
        k = next((k for k, e in reg.items() if e.get('modele') == code), None)
        if k is None:
            return {'ok': False, 'erreur': 'armure inconnue'}
        e = reg.pop(k)
        n = _ranger(sortie, [e.get('modele'), e.get('key')], garde)
        _noter_retrait(garde, mod=mod, genre='armures', code=code, nom=e.get('nom') or k, cle=k, entree=e)
        json.dump(reg, open(os.path.join(sortie, 'outil_armures.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
        armures_copies.ecrire_vrfw(CFG, reg)
        return {'ok': True, 'rapport': ['armure supprimée (%d fichiers rangés dans %s)' % (n, garde)]}
    if mod == 'MesEsprits':
        reg = esprits.registre(sortie)
        if code not in reg:
            return {'ok': False, 'erreur': 'esprit inconnu'}
        u = utilisateurs('MesEsprits', reg[code].get('key'))
        u += ['armure %s' % (a.get('nom') or k) for k, a in armures_copies.registre(CFG).items() if k == code]
        if u:
            return {'ok': False, 'erreur': 'Utilisé par : ' + ', '.join(u) + '. Change-le d\'abord là-bas.'}
        e = reg.pop(code)
        n = _ranger(sortie, [code, e.get('key'), e.get('slug') and 'mesesprits_' + e['slug']], garde)
        _noter_retrait(garde, mod=mod, genre=e.get('genre') or 'esprit', code=code, nom=e.get('nom') or code, cle=code, entree=e)
        esprits.ecrire_vrfw(CFG, sortie, reg)
        json.dump(reg, open(os.path.join(sortie, 'outil_esprits.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
        return {'ok': True, 'rapport': ['esprit guerrier supprimé (%d fichiers rangés dans %s)' % (n, garde)]}
    if mod == 'MesPersonnages':
        r = copies_persos.retirer(CFG, code)
        return dict(r, rapport=['personnage supprimé (fichiers rangés dans sortie/MesPersonnages/_retires)']) if r.get('ok') else r
    if mod == 'MesTenues':
        reg = copies_outfits.registre(CFG)
        k = next((k for k, e in reg.items() if e.get('modele') == code), None)
        if k is None:
            return {'ok': False, 'erreur': 'tenue inconnue'}
        e = reg.pop(k)
        n = _ranger(sortie, [e.get('modele'), k], garde)
        _noter_retrait(garde, mod=mod, genre='tenues', code=code, nom=e.get('nom') or k, cle=k, entree=e)
        json.dump(reg, open(os.path.join(sortie, 'outil_tenues.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
        copies_outfits.ecrire(CFG, reg)
        return {'ok': True, 'rapport': ['tenue supprimée (%d fichiers rangés dans %s)' % (n, garde)]}
    if mod == 'MesObjets':
        reg = objets_jeu.registre(CFG)
        if code not in reg:
            return {'ok': False, 'erreur': 'objet inconnu'}
        e = reg.pop(code)
        n = _ranger(sortie, [code], garde)
        _noter_retrait(garde, mod=mod, genre='objets', code=code, nom=(e or {}).get('nom') or code, cle=code, entree=e)
        json.dump(reg, open(os.path.join(sortie, 'outil_objets.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
        objets_jeu.ecrire(CFG, reg)
        return {'ok': True, 'rapport': ['objet supprimé (%d fichiers rangés dans %s)' % (n, garde)]}
    return {'ok': False, 'erreur': 'suppression pas prévue pour ce genre'}


def liste_creations():
    """(15/11/2026) hub : mods faits avec « Créer le mod » (AtelierCouleurs/sortie), installés ou non dans <jeu>/mods"""
    import re, tomllib
    out = []
    _aj = {}
    a_jour = lambda m: _aj.setdefault(m, mod_a_jour(m))     # (15/11/2026) une fois par mod et par lecture du hub
    jeu = os.path.join(CFG.get('jeu_dir') or '', 'mods')
    dos = os.path.join(ICI, 'sortie', 'MesTechniques', 'content', 'techniques')
    f_t = os.path.join(ICI, 'sortie', 'MesTechniques', 'outil_techniques.json')      # (22/11) stats réglées ?
    reg_t = json.load(open(f_t, encoding='utf-8')) if os.path.isfile(f_t) else {}
    for f in sorted(glob.glob(os.path.join(dos, '*.toml'))):
        try:
            t = tomllib.load(open(f, 'rb'))
        except (OSError, ValueError):
            continue
        inst = os.path.join(jeu, 'MesTechniques', 'content', 'techniques', os.path.basename(f))
        installe = os.path.isfile(inst) and open(inst, 'rb').read() == open(f, 'rb').read() and a_jour('MesTechniques')
        for x in t.get('technique') or []:
            e_t = next((e for e in reg_t.values() if e.get('key') == x.get('key')), None) or {'stats': 1}
            out.append({'genre': 'technique', 'mod': 'MesTechniques', 'nom': ((x.get('text') or {}).get(langue.code()) or (x.get('text') or {}).get('fr') or {}).get('name') or x.get('name'),
                        # (25/11) copie d'une technique de mod : rouverte sur la technique du mod (Tiger fang), pas sur sa base
                        'code': x.get('key'), 'base': e_t.get('source') or x.get('base'), 'onglet': 'techniques', 'installe': installe,
                        'attente': 'stats' not in e_t,
                        'date': os.path.getmtime(f)})
    # dans le jeu seulement (installées avant, plus dans sortie : « Installer » les remplacerait)
    noms_sortie = {os.path.basename(x) for x in glob.glob(os.path.join(dos, '*.toml'))}
    for f in sorted(glob.glob(os.path.join(jeu, 'MesTechniques', 'content', 'techniques', '*.toml'))):
        if os.path.basename(f) in noms_sortie:
            continue
        try:
            t = tomllib.load(open(f, 'rb'))
        except (OSError, ValueError):
            continue
        for x in t.get('technique') or []:
            out.append({'genre': 'technique', 'mod': 'MesTechniques', 'nom': ((x.get('text') or {}).get(langue.code()) or (x.get('text') or {}).get('fr') or {}).get('name') or x.get('name'),
                        'code': x.get('key'), 'base': x.get('base'), 'onglet': 'techniques', 'installe': True, 'jeuSeul': True,
                        'date': os.path.getmtime(f)})
    f = os.path.join(ICI, 'sortie', 'MesEsprits', 'content', 'techniques', 'mes_esprits.toml')
    if os.path.isfile(f):
        inst = os.path.join(jeu, 'MesEsprits', 'content', 'techniques', 'mes_esprits.toml')
        txt_inst = open(inst, encoding='utf-8').read() if os.path.isfile(inst) else ''
        reg_e = esprits.contenu(CFG)
        txt_sortie = open(f, encoding='utf-8').read()
        try:                                     # (28/11) installé = SA ligne du registre identique dans le jeu (voir _reg)
            reg_ej = json.load(open(os.path.join(jeu, 'MesEsprits', 'outil_esprits.json'), encoding='utf-8'))
        except (OSError, ValueError):
            reg_ej = None
        for m in re.finditer(r'^# (.+?) : copie de (.+?) \((\w+)\), code (\w+)', open(f, encoding='utf-8').read(), re.M):
            out.append({'genre': 'totem' if m.group(4).startswith('a') else 'esprit', 'mod': 'MesEsprits', 'nom': m.group(1),
                        'code': m.group(4), 'base': m.group(3), 'nom_base': m.group(2),
                        'onglet': 'totems' if m.group(4).startswith('a') else 'esprits', 'installe': (reg_ej.get(m.group(4)) == reg_e.get(m.group(4)) and m.group(4) in reg_ej) if reg_ej is not None and m.group(4) in reg_e
                                    else txt_inst == txt_sortie and a_jour('MesEsprits'),     # (15/11) fichier identique : une technique liée changée = à réinstaller
                        'liee': ((reg_e.get(m.group(4)) or {}).get('technique_liee') or {}).get('nom'),
                        'attente': m.group(4) in reg_e and 'stats' not in reg_e[m.group(4)],
                        'date': os.path.getmtime(f)})
    try:                                         # (28/11) installé = SA ligne du registre identique dans le jeu (voir _reg)
        reg_pj = json.load(open(os.path.join(jeu, 'MesPersonnages', 'outil_personnages.json'), encoding='utf-8'))
    except (OSError, ValueError):
        reg_pj = None
    for e in copies_persos.contenu(CFG):         # (15/11/2026) copies de personnages
        f_j = os.path.join(jeu, 'MesPersonnages', 'content', 'characters', 'mes_personnages.toml')
        f_s = os.path.join(ICI, 'sortie', 'MesPersonnages', 'content', 'characters', 'mes_personnages.toml')
        # (21/11) copies de TENUE aussi rangées ici : pas de « tete_origine », leur « base » (avant : accueil planté)
        # (28/11, banc d'essai) joueur fait depuis une TENUE ou un ACCESSOIRE (onglet Tenues) : « Modifier » rouvrait l'onglet
        # Personnages avec le code du porteur ; maintenant la tenue / l'accessoire recoloré (source_jeu, gardé depuis le 28/11)
        _src = e.get('source_jeu') if e.get('genre') in ('tenue', 'objet') else None
        out.append({'genre': 'personnages', 'mod': 'MesPersonnages', 'nom': e['nom'], 'code': e['code'], 'base': _src or e.get('tete_origine') or e.get('base'), 'nom_base': e.get('nom_origine'),
                    'cle': e['cle'], 'nb_coups': len(e.get('coups') or []), 'attente': 'stats' not in e and bool(e.get('tete_origine')),
                    'onglet': 'tenues' if _src else 'personnages', 'copie': e.get('genre'), 'installe': (e['cle'] in reg_pj and reg_pj[e['cle']] == {k: v for k, v in e.items() if k != 'cle'}) if reg_pj is not None
                    else os.path.isfile(f_j) and os.path.isfile(f_s) and open(f_j, 'rb').read() == open(f_s, 'rb').read() and a_jour('MesPersonnages'),
                    'date': datetime.datetime.fromisoformat(e['date']).timestamp() if e.get('date') else 0})
    # (21/11) tenues à équiper, objets et armures : créés et installables, mais absents de « Mes créations » (avant : une
    # tenue ou un objet fait n'apparaissait nulle part, ni bouton « Installer » dans l'accueil). Installé = registre identique.
    def _reg(mod, nom_json):
        f_s, f_j = os.path.join(ICI, 'sortie', mod, nom_json), os.path.join(jeu, mod, nom_json)
        try:
            reg = json.load(open(f_s, encoding='utf-8')) if os.path.isfile(f_s) else {}
        except (OSError, ValueError):
            reg = {}
        # (28/11, grand test) installée = SA ligne du registre est la même dans le jeu (l'installation copie tout le mod, registre
        # compris). Avant : registre ENTIER identique + mod entier à jour -> une seule nouvelle création non installée faisait
        # retomber toutes les autres (déjà dans le jeu) hors de « Terminées » (« Installées dans le jeu : 0 »)
        try:
            reg_j = json.load(open(f_j, encoding='utf-8')) if os.path.isfile(f_j) else {}
        except (OSError, ValueError):
            reg_j = {}
        return reg, (lambda cle: cle in reg_j and reg_j[cle] == reg.get(cle))
    def _date(e):
        try:
            return datetime.datetime.fromisoformat(e['date']).timestamp()
        except (KeyError, TypeError, ValueError):
            return 0
    reg, inst = _reg('MesTenues', 'outil_tenues.json')
    for cle, e in reg.items():
        out.append({'genre': 'tenues', 'mod': 'MesTenues', 'nom': e.get('nom') or cle, 'code': e.get('modele'), 'base': e.get('source'),
                    'nom_base': e.get('nom_origine'), 'onglet': 'tenues', 'installe': inst(cle), 'date': _date(e),
                    'cle': cle, 'attenteCosm': not e.get('cosmetique_ok') and not inst(cle)})   # (27/11, muku) installée = Terminées     # (26/11) étape « Cosmétique » (prix, icône)
    reg, inst = _reg('MesObjets', 'outil_objets.json')
    for cle, e in reg.items():
        out.append({'genre': 'objets', 'mod': 'MesObjets', 'nom': e.get('nom') or cle, 'code': cle, 'base': e.get('base'),
                    'nom_base': e.get('nom_origine'), 'onglet': 'objets', 'installe': inst(cle), 'date': _date(e),
                    'cle': cle, 'attenteCosm': not e.get('cosmetique_ok') and not inst(cle)})   # (27/11, muku) installée = Terminées     # (26/11) étape « Cosmétique » (prix)
    reg, inst = _reg('MesEsprits', 'outil_armures.json')
    for cle, e in reg.items():
        out.append({'genre': 'armures', 'mod': 'MesEsprits', 'nom': e.get('nom') or cle, 'code': e.get('modele'), 'base': e.get('armure'),
                    'nom_base': e.get('armure'), 'onglet': 'armures', 'installe': inst(cle), 'date': _date(e)})
    # (15/11/2026) maillots ajoutés au mod (sortie/MesMaillots, « Ajouter au mod » de l'onglet Maillots)
    s_mm =os.path.join(CFG['outil_dir'], 'sortie', 'MesMaillots')
    if os.path.isfile(os.path.join(s_mm, 'mod.toml')):
        def _txt(d):
            f = os.path.join(d, 'content', 'items', 'mes_maillots.toml')
            return open(f, encoding='utf-8').read() if os.path.isfile(f) else ''
        t_s, t_j = _txt(s_mm), _txt(os.path.join(jeu, 'MesMaillots'))
        try:
            mm = mes_maillots.liste(CFG)
        except Exception:
            mm = []
        for m in mm:
            if m['id'] not in t_s and json.dumps(m['nom'], ensure_ascii=False) not in t_s:
                continue
            out.append({'genre': 'maillots', 'mod': 'MesMaillots', 'nom': m['nom'], 'code': m['id'], 'base': m.get('code'), 'nom_base': m.get('nom_base'),
                        'onglet': 'maillots', 'installe': bool(t_j) and t_j == t_s and a_jour('MesMaillots'), 'maillot': m,
                        'attenteCosm': not m.get('cosmetique_ok') and not (bool(t_j) and t_j == t_s and a_jour('MesMaillots')),   # (27/11) installé = Terminées     # (26/11) étape « Cosmétique » (prix, icône, emblème)
                        'vignette': m.get('icone') or (m.get('images') or {}).get('haut_dom'),
                        'date': os.path.getmtime(os.path.join(s_mm, 'mod.toml'))})
    for x in out:                              # image gardée à « Créer le mod » (projets/vignettes/<code neuf>.jpg)
        f = os.path.join(PROJETS, 'vignettes', str(x.get('code')) + '.jpg')
        if os.path.isfile(f):
            import base64
            x.setdefault('vignette', 'data:image/jpeg;base64,' + base64.b64encode(open(f, 'rb').read()).decode())
    # (28/11, grand test en anglais : « Item · copy of Challenger du tournoi ») nom de l'ORIGINAL dans la langue de l'Atelier
    # (le registre garde celui du jour de la création, en français) ; armures : « Armure · Pégase » au lieu du code
    for x in out:
        o_, b_ = x.get('onglet'), x.get('base')
        try:
            v_ = (PAR_CODE.get(b_) if o_ == 'techniques' else PERSO_CODE.get(b_) if o_ in ('esprits', 'totems')
                  else JEU_CODE.get((o_, b_)) if o_ in ('tenues', 'armures', 'personnages', 'objets', 'maillots') else None) or {}
        except (TypeError, NameError):
            v_ = {}
        if v_.get('nom') and v_['nom'] != b_:
            x['nom_base'] = v_['nom']
    out.sort(key=lambda x: x['date'], reverse=True)
    return out


def infos_coups(cle):
    """(15/11/2026) fenêtre « Techniques » du hub : catalogue, mes créations, choix actuel, carte d'origine et ce que les mods lui donnent"""
    e = copies_persos.registre(CFG).get(cle)
    if not e:
        return {'ok': False, 'erreur': 'copie de personnage inconnue'}
    origine, plateau = coups.carte(CFG['data_dir'], e['carte_origine'])
    mods = coups.coups_des_mods(CFG, e['base'], e['carte_origine'])
    mes = coups.mes_coups(CFG)
    par_crc = {zlib.crc32(x['code'].encode()): x['code'] for x in PERSOS}
    F = coups.fiches(CFG, cache_txt(), mes)
    for x in mes:                                   # mes esprits : leur code neuf (icône copiée dans MesEsprits)
        if x.get('copie'):
            F[x['code']] = [0, 0, 0, zlib.crc32(x['copie'].encode())]
            par_crc[zlib.crc32(x['copie'].encode())] = x['copie']
    return {'ok': True, 'nom': e['nom'], 'nom_origine': e.get('nom_origine'), 'catalogue': coups.catalogue(CFG['data_dir'], cache_txt()),
            'code': e['code'], 'base': e['base'], 'tete': e.get('tete_origine'), 'vetement': bool(e.get('vetement')),
            'fiches': F, 'modeles_esprits': {str(k): v for k, v in par_crc.items()},
            'mes': mes, 'actuels': e.get('coups') or [], 'origine': origine, 'plateau': plateau,
            'mods': mods[0] if mods else [], 'mod': mods[1] if mods else None,
            'reforged': 'CharacterReforged' in (coups_actifs() or [])}


def _png_icone(dossier, rels, cle):
    """(15/11/2026) 1re image d'un .g4tx (portrait, icône d'esprit) en PNG dans cache/<dossier>/<cle>.png ; rels = chemins
    candidats (sortie de mes copies d'abord, puis le jeu)"""
    d = os.path.join(CACHE, dossier); os.makedirs(d, exist_ok=True)
    out = os.path.join(d, os.path.basename(cle) + '.png')
    src = next((f for f in rels if os.path.isfile(f)), None)
    if src and (not os.path.exists(out) or os.path.getmtime(out) < os.path.getmtime(src)):
        g = g4.images.G4TX(open(src, 'rb').read())
        r = g4.decoder_texture(g.blocs[0])
        if r:
            g4.images.ecrire_png(out, *r)
    return out if os.path.exists(out) else None


def portrait(code):
    code = os.path.basename(code)
    rel = ('assets', 'menu', '200_icon', '10_icon_chr', 'face', code + '_l.g4tx')
    return _png_icone('portraits', [os.path.join(CFG['outil_dir'], 'sortie', 'MesPersonnages', *rel),
                                    os.path.join(CFG['data_dir'], 'dx11', 'menu', '200_icon', '10_icon_chr', 'face', code + '_l.g4tx')], code)


def icone_esprit(code):
    code = os.path.basename(code)
    f = []
    for dos in ('aura_fs', 'aura_armed', 'aura_soul', 'aura'):      # (23/11) aura_soul = totems
        f += [os.path.join(CFG['outil_dir'], 'sortie', 'MesEsprits', 'assets', 'menu', '200_icon', '10_icon_chr', dos, code + '_l.g4tx'),
              os.path.join(CFG['data_dir'], 'dx11', 'menu', '200_icon', '10_icon_chr', dos, code + '_l.g4tx')]
    return _png_icone('icones_esprits', f, code)


def peau_perso(cle='', tete='', code=''):
    """(26/11/2026) couleur de peau du corps (bras, jambes, cou) : {'origine': '#RRGGBB' de l'original (chara_model col. 16),
    'copie': celle réglée sur la copie ou None, 'base': code du personnage}. cle = une copie, tete = code d'une tête de
    l'onglet Personnages, code = un personnage du jeu"""
    D = CFG['data_dir']
    e = copies_persos.registre(CFG).get(cle) if cle else None
    base = (e or {}).get('base') or code or None
    if not base and tete:
        t = JEU_CODE.get(('personnages', tete))
        p = copies_persos.personnage_de_tete(D, t['chemin']) if t else None
        base = p['code'] if p else None
    if not base:
        return {'ok': False, 'erreur': 'personnage inconnu'}
    p = (e or {}).get('peau')
    return {'ok': True, 'base': base, 'origine': copies_persos.peau_origine(D, base), 'copie': ('#' + p) if p else None}


def morphologie_perso(tete='', cree=''):
    """(27/11) choix de la morphologie d'un nouveau joueur : {'liste': corps communs du jeu, 'origine': n° du corps de
    l'original, 'copie': celui de la copie « cree » (code de la création, « Modifier ») ou None}"""
    D = CFG['data_dir']
    e = next((x for x in copies_persos.registre(CFG).values() if cree and str(x.get('code')) == str(cree)), None)
    base = (e or {}).get('base')
    if not base and tete:
        t = JEU_CODE.get(('personnages', tete))
        p = copies_persos.personnage_de_tete(D, t['chemin']) if t else None
        base = p['code'] if p else None
    if not base:
        return {'ok': False, 'erreur': 'personnage inconnu'}
    return {'ok': True, 'base': base, 'origine': copies_persos.corps_origine(D, base), 'copie': (e or {}).get('corps'),
            'liste': copies_persos.morphologies(D)}


def copie_textures(cle):
    """(15/11/2026) textures recolorées d'une copie de personnage (sa tête), pour l'aperçu du tableau des compétences :
    {nom de la texture d'origine: url du PNG}. Les noms de la copie portent le code neuf : on remet celui d'origine."""
    e = copies_persos.registre(CFG).get(cle)
    if not e or e.get('vetement'):
        return {}
    src = os.path.join(CFG['outil_dir'], 'sortie', 'MesPersonnages', 'assets', 'chr', '_face', e['serie'], e['code'], e['code'] + '.g4tx')
    if not os.path.isfile(src):
        return {}
    d = os.path.join(CACHE, 'copies_persos', e['code']); os.makedirs(d, exist_ok=True)
    g = g4.images.G4TX(open(src, 'rb').read())
    out = {}
    for n, bloc in zip(g.noms, g.blocs):
        f = os.path.join(d, n + '.png')
        if not os.path.exists(f) or os.path.getmtime(f) < os.path.getmtime(src):
            r = g4.decoder_texture(bloc)
            if not r:
                continue
            g4.images.ecrire_png(f, *r)
        out[n.replace(e['code'], e['tete_origine'])] = '/tex/copies_persos__%s/%s.png' % (e['code'], n)
    return out


_POSES = {}


_GARDIENS = {}


def maillot_gardien(code):
    """(26/11) LU : gamedata/character/uniform_config, m_UniformModelInfoList (colonnes par leur nom) = maillot des joueurs de
    champ (uniformFielderModelIdCrc = crc32 de « <coupe>_10 ») -> maillot du GARDIEN (uniformKeeperModelIdCrc). Ex. u080101 -> u080151"""
    import zlib as _z, struct as _s, glob as _g
    code = os.path.basename(str(code or ''))
    if code not in _GARDIENS:
        r = None
        try:
            from moteur import stats as _st
            f = sorted(_g.glob(os.path.join(CFG['data_dir'], 'common', 'gamedata', 'character', 'uniform_config_*.cfg.bin')))[-1]
            R = _st._rdbn_lignes(open(f, 'rb').read(), 'm_UniformModelInfoList', ['uniformFielderModelIdCrc', 'uniformKeeperModelIdCrc'])
            P = copies_tenues._parties(CFG['data_dir'])['clothes']
            par_crc = {_z.crc32(k.encode()): k for k in P}
            ligne = R.get(_z.crc32((code + '_10').encode()))
            g = ligne and par_crc.get(ligne['uniformKeeperModelIdCrc'])
            r = g[:-3] if g and g.endswith('_10') else None
        except Exception as ex:
            print('maillot du gardien :', ex)
        _GARDIENS[code] = r
    return {'ok': bool(_GARDIENS[code]), 'gardien': _GARDIENS[code]}


def pose_joueur(code, paquet='p010', clip=1):
    """(15/11/2026) aperçu du tableau des compétences : squelette de la corpulence du personnage + UN clip de ses mouvements
    (common/chr/c000<corps>01/c000<corps>01_<paquet>.g4pk). Sans clip, la tête du modèle reste à hauteur de poitrine : elle
    n'est mise sur le cou que par l'animation (comme dans les cinématiques)."""
    info = personnages.joueur(CFG['data_dir'], code) if code else None
    t = info['corps'] if info else 1
    cle = (t, paquet, clip)
    if cle not in _POSES:
        b = os.path.join(CFG['data_dir'], 'common', 'chr', 'c000%d01' % t)
        sk = os.path.join(b, 'c000%d01.g4sk' % t)
        pk = anim.lire_paquet(os.path.join(b, 'c000%d01_%s.g4pk' % (t, os.path.basename(paquet))))
        clips = (pk.get('G4MT') or {}).get('clips') or []
        if not clips:
            return {'ok': False, 'erreur': 'pas de mouvement'}
        _POSES[cle] = {'ok': True, 'os': anim.lire_paquet(sk)['squelette'], 'g4sk': anim.entete_g4sk(sk),
                       'nus': anim.non_uniforme(os.path.join(b, 'c000%d01.objbin' % t)), 'clip': clips[min(int(clip), len(clips) - 1)],
                       'nb': len(clips), 'corps': t}
    return _POSES[cle]


def _texture_par_materiau(md, tx_rel, lot, noms):
    """texture de couleur du matériau de chaque maillage (ObjetModele : pièce -> matériau -> textures)"""
    if not tx_rel:
        return
    try:
        ob = objet(md + '|' + tx_rel)
    except Exception:
        return
    par_i = {x['index']: x['materiau'] for x in ob.pieces}
    for m in lot:
        mat = par_i.get(m.get('_i'))
        if mat is None:
            continue
        t0 = next((n for n in ob.materiaux[mat]['textures'] if n in noms and not n.endswith(('line', 'oc', 'sp', 'spm', 'msk'))), None)
        if t0:
            m['texture'] = t0


def icone_copie(d):
    """(16/11/2026) portrait d'une copie déjà faite refait avec une photo : d = {genre: 'personnage' | 'esprit', cle | code, image}"""
    from moteur import icones_copies
    if not str(d.get('image') or '').startswith('data:image/png'):
        return {'ok': False, 'erreur': 'pas de photo'}
    if d.get('genre') == 'personnage':
        e = copies_persos.registre(CFG).get(d.get('cle'))
        if not e or e.get('vetement'):
            return {'ok': False, 'erreur': 'copie de personnage inconnue'}
        anc, neuf, rel = e['tete_origine'], e['code'], ('menu', '200_icon', '10_icon_chr', 'face')
        sortie = os.path.join(CFG['outil_dir'], 'sortie', 'MesPersonnages')
        dos = ('chr', '_face', e['serie'])
    else:
        c = esprits.contenu(CFG).get(d.get('code'))
        if not c:
            return {'ok': False, 'erreur': "copie d'esprit inconnue"}
        anc, neuf, rel = c['base'], d['code'], ('menu', '200_icon', '10_icon_chr', esprits.ICONES[c['dossier']])
        sortie = os.path.join(CFG['outil_dir'], 'sortie', esprits.MOD_ID)
        dos = ('chr', c['dossier'])
    src = os.path.join(CFG['data_dir'], 'dx11', *rel, anc + '_l.g4tx')
    if not os.path.isfile(src):
        return {'ok': False, 'erreur': "le jeu n'a pas de portrait pour " + anc}
    # (16/11/2026) le dessin d'origine recoloré comme les textures de la copie ; la photo dit où va chaque couleur
    to, tm = os.path.join(CFG['data_dir'], 'dx11', *dos, anc, anc + '.g4tx'), os.path.join(sortie, 'assets', *dos, neuf, neuf + '.g4tx')
    paires = icones_copies.paires_textures(open(to, 'rb').read(), open(tm, 'rb').read(), anc, neuf)         if os.path.isfile(to) and os.path.isfile(tm) else None
    fait = icones_copies.ecrire_portrait(src, os.path.join(sortie, 'assets', *rel, neuf + '_l.g4tx'), d['image'], anc, neuf, paires)
    return {'ok': True, 'rapport': ['portrait de %s refait : %s' % (neuf, "dessin d'origine recoloré" if fait == 'dessin' else 'photo du modèle recoloré')]}


def coups_actifs():
    from moteur.mods_jeu import actifs_ordonnes   # (22/11, 2.0.4) sans enabled.toml : tous les mods sont actifs
    return actifs_ordonnes(os.path.join(CFG.get('jeu_dir') or '', 'mods'))


def infos_technique_liee(code):
    """(15/11/2026) fenêtre « Technique liée » : tirs / dribbles / défenses / arrêts du jeu + mes techniques ; celle d'origine"""
    reg = esprits.contenu(CFG)
    c = reg.get(code)
    if not c:
        return {'ok': False, 'erreur': "copie d'esprit inconnue"}
    cat = coups.catalogue(CFG['data_dir'], cache_txt())
    origine = next((x for x in cat if x['code'] == c['technique']), {})
    par_id = {x['id']: x for x in cat}
    # (15/11/2026) l'esprit dans la cinématique : {code: [esprit animé, compatible]} (moteur/coups.py, os du squelette)
    te = coups.techniques_d_esprit(CFG['data_dir'], cache_txt())
    compat = coups.compatibles(CFG['data_dir'], cache_txt(), c['base'])
    mes = [x for x in coups.mes_coups(CFG) if x['mod'] == 'MesTechniques']
    noms_k = {x['code']: x['nom'] for x in PERSOS}
    esp = {code: [noms_k.get(k, k), code in compat and compat[code], k] for code, (d, k) in te.items()}
    for x in mes:
        if x.get('base') in esp:
            esp[x['code']] = esp[x['base']]
    return {'ok': True, 'nom': c['nom'], 'nom_base': c['nom_base'], 'base': c['base'],
            'catalogue': [x for x in cat if x['code'][:3] in ('whs', 'who', 'whd', 'whk')],
            'mes': mes, 'esprits': esp,
            'actuelle': c.get('technique_liee'), 'origine': par_id.get(origine.get('liee'))}


class Gestion(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def _envoyer(self, code, corps, type_='application/json; charset=utf-8'):
        if isinstance(corps, (dict, list)):
            # (14/11/2026) le JSON du navigateur refuse NaN / Infinity (ex. matrice de texture n° 1 d'une pièce des trois
            # « Dernier recours », lue telle quelle dans le G4MD) : pour la page seulement, NaN -> 0 et ±Infinity -> ±plus grand
            # flottant 32 bits (APPROCHÉ pour l'aperçu ; le lecteur natif lit tech.json avec les valeurs exactes)
            try:
                corps = json.dumps(corps, ensure_ascii=False, allow_nan=False).encode('utf-8')
            except ValueError:
                corps = json.dumps(_fini(corps), ensure_ascii=False).encode('utf-8')
        elif isinstance(corps, str):
            corps = corps.encode('utf-8')
        self.send_response(code)
        self.send_header('Content-Type', type_)
        self.send_header('Content-Length', str(len(corps)))
        self.send_header('Cache-Control', 'no-store')
        self.end_headers()
        self.wfile.write(corps)

    def do_GET(self):
        u = urlparse(self.path)
        q = parse_qs(u.query)
        try:
            if u.path in ('/', '/index.html'):
                return self._fichier(os.path.join(WEB, 'index.html'))
            if u.path.startswith('/web/'):
                return self._fichier(os.path.join(WEB, os.path.basename(u.path)))
            if u.path.startswith('/natif/'):              # images du lecteur natif (planches de comparaison)
                p = u.path.split('/')
                return self._fichier(os.path.join(os.path.dirname(ICI), 'AtelierNatif', 'scenes', os.path.basename(p[2]), os.path.basename(unquote(p[3]))))
            if u.path == '/api/planche':                  # vidéo officielle / lecteur natif côte à côte (vérifications)
                return self._envoyer(200, planche_natif(q['code'][0], q.get('t', ['1,3,5'])[0]).encode('utf-8'), 'text/html; charset=utf-8')
            if u.path == '/api/chargement':                # écran de chargement (1er lancement)
                from moteur import mods_jeu as _mj
                return self._envoyer(200, {'pret': PREPA['pret'], 'fait': _mj.PROGRES['fait'], 'total': _mj.PROGRES['total']})
            if u.path == '/api/langue':                    # FR / EN
                return self._envoyer(200, {'langue': langue.code()})
            if u.path == '/api/stats':                     # (22/11) « En attente de stats » : champs, valeurs du jeu, valeurs réglées
                return self._envoyer(200, stats_creation(q.get('mod', [''])[0], q.get('code', [''])[0], q.get('langue', ['fr'])[0]))
            if u.path == '/api/parametres':                # (22/11) ⚙ Paramètres (palette, musique) : gardés dans config.json
                return self._envoyer(200, parametres())
            if u.path == '/api/dossier_jeu':               # (22/11) ⚙ Paramètres : dossier du jeu où « Installer » met les mods
                return self._envoyer(200, dossier_jeu())
            if u.path == '/api/corbeille':                 # (23/11) ⚙ Paramètres : ce qui a été supprimé (projets, créations, maillots)
                from moteur import corbeille
                return self._envoyer(200, corbeille.lister(ICI, CFG))
            if u.path == '/api/cache_taille':              # (23/11) ⚙ Paramètres : place du cache (le terrain reste)
                from moteur import corbeille
                return self._envoyer(200, corbeille.taille_cache(CACHE))
            if u.path in ('/api/musique', '/api/musique.ogg'):   # (22/11) musique de fond : thème de l'écran titre du jeu
                from moteur import musique as _mu_
                f_, meta_ = _mu_.ogg(CFG['data_dir'], CACHE, (q.get('piste') or ['titre'])[0])
                if not f_:
                    return self._envoyer(200 if u.path == '/api/musique' else 404, {'ok': False, 'erreur': meta_})
                if u.path == '/api/musique':
                    return self._envoyer(200, dict(meta_, ok=True))
                return self._envoyer(200, open(f_, 'rb').read(), 'audio/ogg')
            if u.path == '/api/identite':                  # (21/11) le lanceur vérifie que ce serveur est le SIEN
                return self._envoyer(200, {'dossier': os.path.normpath(ICI), 'version': version_atelier()})
            if u.path == '/api/parent':                    # (21/11) une 2e fenêtre du même Atelier : surveillée aussi
                try:
                    PARENTS.add(int(q['pid'][0]))
                except (KeyError, ValueError):
                    pass
                return self._envoyer(200, {'ok': True})
            if u.path == '/api/detacher':                  # (21/11) affichage dans le navigateur : le serveur reste ouvert
                PARENTS.clear()
                return self._envoyer(200, {'ok': True})
            if u.path == '/api/techniques':                # (17/11/2026) + techniques des mods
                return self._envoyer(200, INDEX + sans_chemins(mods_liste('techniques')))
            if u.path == '/api/prereglages':              # (15/11/2026) préréglages de couleurs (réutilisables)
                return self._envoyer(200, {'liste': lire_prereglages()})
            if u.path == '/api/projets':                  # (15/11/2026) hub « Mes créations »
                _cr = liste_creations()
                return self._envoyer(200, {'projets': lier_anciens_projets(liste_projets(), _cr), 'creations': _cr})
            if u.path == '/api/projet':                   # (15/11/2026) projet en cours d'une technique (reprise)
                f = fichier_projet(q.get('cle', [''])[0])
                if not os.path.isfile(f):
                    return self._envoyer(200, {'existe': False})
                return self._envoyer(200, {'existe': True, 'etat': json.load(open(f, encoding='utf-8'))})
            if u.path in ('/api/technique', '/api/personnage'):
                # (22/11, chasse aux bugs) code inconnu (projet d'un élément venu d'un mod retiré / désactivé) : avant, erreur 500
                # « 'whs…' » illisible ; maintenant 404 avec une phrase
                code_ = (q.get('code') or [''])[0]
                try:
                    if u.path == '/api/technique':
                        return self._envoyer(200, details(code_))
                    if q.get('cat') and q['cat'][0] in JEU:               # (15/11/2026) maillots, tenues, armures, têtes, objets
                        return self._envoyer(200, details_jeu(q['cat'][0], code_, q.get('modele', [None])[0], q.get('cote', [None])[0]))
                    return self._envoyer(200, details_personnage(code_))
                except KeyError:
                    return self._envoyer(404, {'ok': False, 'erreur': '« %s » introuvable dans le jeu et les mods activés '
                                                                     '(il venait peut-être d’un mod retiré ou désactivé).' % code_[:80]})
            if u.path == '/api/personnages':              # (17/11/2026) + esprits guerriers des mods
                return self._envoyer(200, PERSOS + sans_chemins(mods_liste('esprits')))
            if u.path == '/api/porteurs':                  # (15/11/2026) qui porte cette tenue / cet objet est-il un accessoire
                cat, code = q.get('cat', [''])[0], q.get('code', [''])[0]
                e = JEU_CODE.get((cat, code))
                if not e or e.get('mod'):                    # (17/11/2026) modèle d'un mod : pas de porteur lu
                    return self._envoyer(200, {'porteurs': [], 'accessoire': False})
                if cat == 'objets' or e.get('genre') == 'Accessoire':
                    return self._envoyer(200, {'porteurs': [], 'accessoire': bool(copies_tenues.lignes_accessoire(CFG['data_dir'], code))})
                l, _ = copies_tenues.porteurs(CFG, e)
                vet, _, _ = copies_outfits.vetement_de(CFG, e)
                return self._envoyer(200, {'porteurs': l, 'accessoire': False, 'vetement': vet, 'corps': copies_tenues.corpulences(CFG, e),
                                          'corps_tenue': copies_outfits.corps_tenue(CFG, e) if vet else [],
                                          'chaussures': copies_outfits.chaussures_de(CFG['data_dir'], vet) if vet else None,
                                          'kit_jeu': copies_outfits.kit_du_jeu(CFG['data_dir'], vet) if vet else None})
            if u.path == '/api/coups':                   # (15/11/2026) techniques d'une copie de personnage (hub)
                return self._envoyer(200, infos_coups(q.get('cle', [''])[0]))
            if u.path == '/api/portrait':                 # (15/11/2026) tableau des compétences : portrait, icône d'esprit, tête recolorée
                f = portrait(q.get('code', [''])[0])
                return self._fichier(f) if f else self._envoyer(404, {'erreur': 'pas de portrait'})
            if u.path == '/api/icone_esprit':
                f = icone_esprit(q.get('code', [''])[0])
                return self._fichier(f) if f else self._envoyer(404, {'erreur': "pas d'icône"})
            if u.path == '/api/maillot_gardien':          # (26/11) maillot du gardien d'un maillot (boutique : joueurs habillés)
                return self._envoyer(200, maillot_gardien(q.get('code', [''])[0]))
            if u.path == '/api/synergies_listes':        # (27/11) création d'une synergie : effets du jeu + personnages (conditions)
                from moteur import synergies
                lg = q.get('langue', ['fr'])[0]
                return self._envoyer(200, {'ok': True, 'effets': [x for x in synergies.catalogue_effets(CFG['data_dir']) if not x['essai']],
                                           'joueurs': synergies.joueurs(CFG['data_dir'], lg if lg in ('fr', 'en', 'es') else 'fr')})
            if u.path == '/api/pose_joueur':
                return self._envoyer(200, pose_joueur(q.get('code', [''])[0], q.get('paquet', ['p010'])[0], q.get('clip', ['1'])[0]))
            if u.path == '/api/copie_textures':
                return self._envoyer(200, copie_textures(q.get('cle', [''])[0]))
            if u.path == '/api/peau_perso':              # (26/11) peau des bras / jambes : celle de l'original (chara_model col. 16) et de la copie
                return self._envoyer(200, peau_perso(q.get('cle', [''])[0], q.get('tete', [''])[0], q.get('code', [''])[0]))
            if u.path == '/api/morphologie_perso':       # (27/11) morphologies d'un nouveau joueur (corps du jeu)
                return self._envoyer(200, morphologie_perso(q.get('tete', [''])[0], q.get('cree', [''])[0]))
            if u.path == '/api/technique_liee':          # (15/11/2026) technique liée d'une copie d'esprit (hub)
                return self._envoyer(200, infos_technique_liee(q.get('code', [''])[0]))
            if u.path == '/api/copies_esprits':
                return self._envoyer(200, {'copies': armures_copies.copies_esprits(CFG), 'armures': armures_copies.contenu(CFG)})
            if u.path == '/api/retouches':
                return self._envoyer(200, {'liste': retouches.contenu(CFG), 'conflits': {}})
            if u.path == '/api/jeu':
                cat = q.get('cat', [''])[0]                    # (17/11/2026) + ce que les mods apportent à cet onglet
                return self._envoyer(200, JEU.get(cat, []) + sans_chemins(mods_liste(cat)))
            if u.path == '/api/mes_maillots':
                return self._envoyer(200, mes_maillots.liste(CFG))
            if u.path == '/api/maillot_icone_base':        # (24/11) icône de boutique du maillot de base (dessin de l'icône)
                f = mes_maillots.icone_base(CFG, q.get('base', [''])[0])
                return self._fichier(f) if f else self._envoyer(404, {'erreur': 'icône introuvable'})
            if u.path == '/api/maillot_etat':
                return self._envoyer(200, mes_maillots.etat())
            if u.path == '/api/menus_jeu':               # (15/11/2026) images des menus du jeu pour le hub (moteur/menus_jeu.py)
                return self._envoyer(200, menus_jeu.tout(CFG['data_dir'], CACHE))
            if u.path.startswith('/ui_jeu/'):              # (23/11) refonte « comme le jeu » : morceaux exacts des menus du jeu
                from moteur import ui_jeu
                if u.path == '/ui_jeu/liste':
                    return self._envoyer(200, ui_jeu.liste(CFG, q.get('planche', [''])[0]))
                f = ui_jeu.servir(CFG, CACHE, unquote(u.path[len('/ui_jeu/'):]))
                return self._fichier(f) if f else self._envoyer(404, {'erreur': 'image du jeu introuvable'})
            if u.path.startswith('/menu_jeu/'):
                f = menus_jeu.image(CFG['data_dir'], CACHE, os.path.basename(unquote(u.path))[:-4])
                return self._fichier(f) if f else self._envoyer(404, {'erreur': 'image introuvable'})
            if u.path.startswith('/maillot_img/'):
                _, _, id_, nom = u.path.split('/', 3)
                f = mes_maillots.image(unquote(id_), unquote(nom))
                return self._fichier(f) if f else self._envoyer(404, {'erreur': 'image introuvable'})
            if u.path == '/api/anim':
                t = technique(q['code'][0])                  # (17/11/2026) + techniques des mods (racine superposée)
                D_, cin, r = anim_de(t)
                # (liste des joueurs qui ont la technique retirée : jamais affichée, ~45 s à chaque animation)
                preparer_natif(q['code'][0])             # lecteur natif : technique exportée pendant que la page charge
                return self._envoyer(200, r)
            if u.path == '/api/son':                     # son d'une cinématique en .ogg (décodé une fois, puis en cache)
                f = son.en_ogg(CFG['data_dir'], os.path.basename(q['nom'][0]), CACHE, os.path.basename(q['perso'][0]) if q.get('perso') else None)
                if not f:                                   # (17/11/2026) son d'une cinématique de mod
                    from moteur import racines
                    for _sig, R in list(racines._memo.values()):
                        f = son.en_ogg(R, os.path.basename(q['nom'][0]), CACHE, os.path.basename(q['perso'][0]) if q.get('perso') else None)
                        if f:
                            break
                if not f:                                   # (17/11/2026) son ajouté par un mod ([[sfx]] add / file .wav)
                    from moteur import vrfw_anim
                    w = vrfw_anim.son_mod(CFG, os.path.basename(q['nom'][0]))
                    if w:
                        return self._envoyer(200, open(w, 'rb').read(), 'audio/wav' if w.lower().endswith('.wav') else 'audio/ogg')
                if not f:
                    return self._envoyer(404, {'erreur': 'son introuvable'})
                return self._envoyer(200, open(f, 'rb').read(), 'audio/ogg')
            if u.path == '/api/carte':                   # stade (décor des cinématiques), en cache après la 1re fois
                code = os.path.basename(q.get('code', ['s10g001'])[0])
                with _verrou:
                    b = _modeles.get(('carte', code))
                if b is None:
                    b = carte.binaire(carte.lire(CFG['data_dir'], code, CACHE))
                    with _verrou:
                        _modeles[('carte', code)] = b
                return self._envoyer(200, b, 'application/octet-stream')
            if u.path == '/api/cubemap':                 # cubemap HDR du stade (reflets du vrai shader map_pbrt1), en cache
                code = os.path.basename(q.get('code', ['s10g001'])[0])
                b = carte.cubemap(CFG['data_dir'], code, CACHE)
                return self._envoyer(200, b, 'application/octet-stream') if b else self._envoyer(404, {'erreur': 'cubemap introuvable'})
            if u.path == '/api/modele':
                return self._envoyer(200, modele_binaire(q['quoi'][0], q.get('code', [None])[0], q.get('maillot', [None])[0] or None,
                                                         '20' if q.get('cote', ['10'])[0] == '20' else '10'), 'application/octet-stream')
            if u.path == '/api/geometrie':
                return self._envoyer(200, geometrie_binaire(q['chemin'][0]), 'application/octet-stream')
            if u.path.startswith('/tex/'):
                _, _, obj, nom = u.path.split('/', 3)
                if obj.startswith('copies_persos__'):    # (15/11/2026) tête recolorée d'une copie (cache/copies_persos/<code>/)
                    return self._fichier(os.path.join(CACHE, 'copies_persos', os.path.basename(obj[15:]), os.path.basename(unquote(nom))))
                return self._fichier(os.path.join(CACHE, os.path.basename(obj), os.path.basename(unquote(nom))))
            if u.path == '/api/polices_perso':            # (22/11) polices importées dans l'Atelier
                return self._envoyer(200, polices_perso())
            if u.path == '/api/polices':                  # polices présentes sur CE PC (bannières : les autres sont cachées)
                return self._envoyer(200, sorted(polices_du_pc()))
            if u.path.startswith('/police/'):
                f = os.path.basename(unquote(u.path[len('/police/'):]))
                p = polices_du_pc().get(f.lower())
                if not f.lower().endswith(('.ttf', '.otf')) or not p:
                    return self._envoyer(404, {'erreur': 'police introuvable'})
                return self._envoyer(200, open(p, 'rb').read(), 'font/ttf')
            if u.path == '/api/planche_numero':         # (16/11/2026) aperçu du numéro : planche du jeu (R = remplissage, A = forme)
                from moteur.maillots import numeros as _num
                p_ = int(q.get('p', ['1'])[0])
                if p_ not in range(0, 7):
                    return self._envoyer(404, {'erreur': 'police inconnue'})
                return self._fichier(_num.planche_png(CFG['data_dir'], p_, os.path.join(CACHE, 'numeros')))
            if u.path == '/api/banniere_jeu':              # (23/11) bannière écrite avec les lettres du jeu (éditeur, aperçus)
                from moteur import lettres_jeu
                el_ = (q.get('element') or ['wind'])[0]
                if el_.startswith('image:'):                # (24/11) polices-images (planches de muku : moteur/police_image.py)
                    from moteur import police_image
                    cle_ = el_[len('image:'):]
                    if cle_ not in police_image.PLANCHES or not police_image.disponible(cle_, CACHE):
                        return self._envoyer(503, {'erreur': 'police pas encore prête (construction au démarrage, ~1 min)'})
                    import tempfile
                    fd_, f_ = tempfile.mkstemp(prefix='atelier_banniere_', suffix='.png'); os.close(fd_)
                    try:
                        police_image.ecrire((q.get('texte') or [''])[0] or ' ', cle_, CACHE, f_)
                        return self._envoyer(200, open(f_, 'rb').read(), 'image/png')
                    finally:
                        try:
                            os.remove(f_)
                        except OSError:
                            pass
                if not lettres_jeu.disponible(CACHE):
                    return self._envoyer(503, {'erreur': 'lettres du jeu pas encore prêtes (construction au démarrage, ~3 min)'})
                # (24/11) fichier PROPRE à cette demande : deux Atelier ouverts (ou deux demandes) écrivaient le même fichier temporaire
                # -> image coupée, l'éditeur passait à une police ordinaire
                import tempfile
                fd_, f_ = tempfile.mkstemp(prefix='atelier_banniere_', suffix='.png'); os.close(fd_)
                try:
                    lettres_jeu.ecrire((q.get('texte') or [''])[0] or ' ', (q.get('element') or ['wind'])[0], CACHE, f_)
                    return self._envoyer(200, open(f_, 'rb').read(), 'image/png')
                finally:
                    try:
                        os.remove(f_)
                    except OSError:
                        pass
            if u.path == '/api/banniere_esprit_png':      # (24/11) bannière actuelle d'un esprit / totem / armure (fiche)
                return self._fichier(banniere_esprit_png(q.get('id', [''])[0], q.get('base', [''])[0]))
            if u.path == '/api/texture_armure':           # (24/11) remplissage de l'armure (style « Armure », police Armure Style)
                from moteur import lettres_jeu
                return self._fichier(lettres_jeu.texture_armure(CACHE, CFG['data_dir']))
            if u.path == '/api/telop_png':
                return self._fichier(telop_png(q['code'][0]))
            if u.path == '/api/telop_apercu':              # bannière des aperçus : la perso si elle existe, sinon celle du jeu
                return self._fichier(telop_apercu(q.get('tech', [''])[0], q.get('telop', [''])[0], q.get('projet', [''])[0]))
            if u.path == '/api/telop_apercu_version':
                return self._envoyer(200, {'v': telop_apercu_version(q.get('tech', [''])[0], q.get('projet', [''])[0])})
            if u.path == '/api/bannieres_esprits':        # (23/11) copies d'esprits, de totems et armures pour l'éditeur de bannières
                return self._envoyer(200, bannieres_esprits())
            if u.path == '/api/etat':
                return self._envoyer(200, {'jeu_ouvert': export.jeu_ouvert(), 'deja': export._deja_dans_le_mod(os.path.join(ICI, 'sortie', export.MOD_ID)),
                                       'esprits': esprits.contenu(CFG), 'maillots': os.path.isfile(MAILLOTS),
                                       'catalogues_en_erreur': CATALOGUES_EN_ERREUR})
            return self._envoyer(404, {'erreur': 'introuvable'})
        except Exception as ex:
            traceback.print_exc()
            return self._envoyer(500, {'erreur': str(ex)})

    def do_POST(self):
        u = urlparse(self.path)
        try:
            n = int(self.headers.get('Content-Length', 0))
            demande = json.loads(self.rfile.read(n).decode('utf-8')) if n else {}
            if u.path == '/api/exporter' and demande.get('action') != 'retirer' and '~' in str(demande.get('code')) \
                    and entree_mod(str(demande.get('code'))) is not None:
                # (25/11, retour de danifdez : Tiger fang) technique d'un mod qui ne fait que remplacer des modèles de la scène
                # du jeu par des modèles .glb : copie possible (base = la technique du jeu, modèle du mod recopié sous un code
                # neuf : moteur/copie_modele_mod.py) ; sinon la phrase dit pourquoi
                from moteur import copie_modele_mod as _cmm
                t_ = technique(demande['code'])
                d_ = details(demande['code'])
                ok_, raison_ = _cmm.possible(CFG, t_, d_) if t_.get('base') else (False, None)
                if not ok_:
                    return self._envoyer(200, {'ok': False, 'erreur': raison_ or 'Cet élément vient d’un mod : la copie n’est pas '
                                                                                  'encore possible (aperçu et recoloration seulement).'})
                return self._envoyer(200, export.exporter(CFG, dict(demande, code=t_['base']), d_))
            if u.path in ('/api/copie_outfit', '/api/copie_tenue', '/api/copie_objet', '/api/copie_objet_jeu', '/api/copie_armure',
                          '/api/copie_personnage', '/api/exporter', '/api/exporter_personnage') and demande.get('action') != 'retirer' \
                    and '~' in str(demande.get('code')) and entree_mod(str(demande.get('code'))) is not None:
                # (17/11/2026) contenu des mods : aperçu et recoloration seulement (les copies lisent les fichiers du jeu)
                return self._envoyer(200, {'ok': False, 'erreur': 'Cet élément vient d’un mod : la copie n’est pas encore possible '
                                                                  '(aperçu et recoloration seulement).'})
            if u.path == '/api/stats':                     # (22/11) régler les stats d'une création (ou garder celles de l'original)
                return self._envoyer(200, regler_stats(demande.get('mod'), demande.get('code'), demande.get('stats') or {}, demande.get('cosmetique'), demande.get('invocation'), demande.get('effets')))
            if u.path == '/api/supprimer_creation':        # (22/11) « Supprimer » d'une carte de Terminées
                return self._envoyer(200, supprimer_creation(demande.get('mod'), str(demande.get('code') or ''), demande.get('genre')))
            if u.path == '/api/corbeille':                 # (23/11) Restaurer / Supprimer définitivement / Vider la corbeille
                from moteur import corbeille
                a = demande.get('action')
                if a == 'restaurer':
                    r = corbeille.restaurer(ICI, CFG, demande.get('id'), construire_maillots=lambda: mes_maillots.construire(CFG))
                    if r.get('ok'):
                        threading.Thread(target=mods_liste, kwargs={'frais': True}, daemon=True).start()
                    return self._envoyer(200, r)
                if a == 'supprimer':
                    try:
                        return self._envoyer(200, {'ok': True, 'libere': corbeille.supprimer(ICI, demande.get('id'))})
                    except (OSError, ValueError) as ex:
                        return self._envoyer(200, {'ok': False, 'erreur': str(ex)})
                if a == 'vider':
                    return self._envoyer(200, corbeille.vider(ICI, CFG, demande.get('ids')))
                return self._envoyer(200, {'ok': False, 'erreur': 'action inconnue'})
            if u.path == '/api/cache_vider':               # (23/11) vider le cache sauf le terrain
                from moteur import corbeille
                with _verrou:
                    _modeles.clear()                       # modèles lus gardés en mémoire : relus depuis le jeu
                return self._envoyer(200, corbeille.vider_cache(CACHE))
            if u.path == '/api/police_importer':          # (22/11) police .ttf / .otf importée (fichier en data URL)
                return self._envoyer(200, importer_police(demande.get('nom'), demande.get('data')))
            if u.path == '/api/police_retirer':
                f_ = os.path.basename(str(demande.get('fichier') or ''))
                if f_.startswith('perso_') and f_.lower().endswith(('.ttf', '.otf')):
                    try:
                        os.remove(os.path.join(POLICES_PERSO, f_))
                    except OSError:
                        pass
                return self._envoyer(200, {'ok': True, 'polices': polices_perso()})
            if u.path == '/api/dossier_jeu':               # (22/11) ⚙ Paramètres : changer le dossier du jeu
                return self._envoyer(200, choisir_dossier_jeu(demande.get('dossier')))
            if u.path == '/api/parametres':                # (22/11) ⚙ Paramètres
                p_ = parametres()
                for k_, ok_ in (('theme', lambda v: v in THEMES), ('musique', lambda v: isinstance(v, bool)),
                                ('volume', lambda v: isinstance(v, (int, float)) and 0 <= v <= 1)):
                    if k_ in demande and ok_(demande[k_]):
                        p_[k_] = demande[k_]
                if 'theme' in demande:
                    p_['theme_v2'] = True                   # (23/11) palette choisie après la refonte « Jeu »
                CFG['parametres'] = p_
                sauver_cfg()
                return self._envoyer(200, dict(p_, ok=True))
            if u.path == '/api/langue':                    # FR / EN : noms du jeu dans l'autre langue, sans relancer
                l_ = langue.regler(demande.get('langue'))
                CFG['langue'] = l_
                sauver_cfg()
                from moteur import techniques as _t_, coups as _c_, copies_tenues as _ct_, esprits as _e_
                for d_ in (_t_._NOMS_EVT, _c_._MODS, _ct_._cache, _e_._GROUPES):
                    d_.clear()
                charger_catalogues()
                marquer_series()
                MODS['quand'] = 0
                MODS['sig'] = None                          # contenu des mods relu dans la nouvelle langue
                return self._envoyer(200, {'ok': True, 'langue': l_})
            if u.path == '/api/exporter':
                return self._envoyer(200, export.exporter(CFG, demande, details(demande['code'])))
            if u.path == '/api/cosmetique':              # (26/11) étape « Cosmétique » des objets, tenues, maillots
                return self._envoyer(200, cosmetique_infos(str(demande.get('mod')), str(demande.get('code'))) if demande.get('lire') else regler_cosmetique(demande))
            if u.path == '/api/couleurs_apparition':     # (25/11) couleurs de l'apparition d'un esprit guerrier
                return self._envoyer(200, couleurs_apparition(demande))
            if u.path == '/api/prereglages':              # (15/11/2026) garder / supprimer un préréglage
                L = [p for p in lire_prereglages() if p.get('nom') != (demande.get('prereglage') or {}).get('nom', demande.get('nom'))]
                if demande.get('action') == 'garder':
                    p = demande.get('prereglage') or {}
                    if not str(p.get('nom', '')).strip():
                        return self._envoyer(200, {'ok': False, 'erreur': 'nom vide'})
                    L.append(p)
                tmp = PREREGLAGES + '.tmp'
                json.dump(L, open(tmp, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
                os.replace(tmp, PREREGLAGES)
                return self._envoyer(200, {'ok': True})
            if u.path == '/api/vignette':                 # (15/11/2026) image de l'aperçu gardée pour un mod créé (hub)
                import base64, re as _re
                code = _re.sub(r'[^\w-]', '_', str(demande.get('code', '')))[:40]
                img = str(demande.get('image', ''))
                if not code or not img.startswith('data:image/jpeg;base64,'):
                    return self._envoyer(200, {'ok': False})
                d = os.path.join(PROJETS, 'vignettes'); os.makedirs(d, exist_ok=True)
                open(os.path.join(d, code + '.jpg'), 'wb').write(base64.b64decode(img.split(',', 1)[1]))
                return self._envoyer(200, {'ok': True})
            if u.path == '/api/projet':                   # (15/11/2026) sauvegarde automatique du projet / repartir de zéro
                f = fichier_projet(demande.get('cle', ''))
                if demande.get('action') == 'oublier':
                    if os.path.isfile(f):
                        os.replace(f, f[:-5] + '.ancien.json')
                    return self._envoyer(200, {'ok': True})
                if demande.get('action') == 'supprimer':  # (15/11/2026) hub : rangé dans projets/corbeille (jamais effacé)
                    if os.path.isfile(f):
                        import datetime
                        c = os.path.join(PROJETS, 'corbeille'); os.makedirs(c, exist_ok=True)
                        os.replace(f, os.path.join(c, os.path.basename(f)[:-5] + datetime.datetime.now().strftime('_%Y%m%d_%H%M%S') + '.json'))
                    return self._envoyer(200, {'ok': True})
                if demande.get('action') == 'renommer':   # (15/11/2026) hub : nouveau nom (champ « Nom » du formulaire)
                    if not os.path.isfile(f):
                        return self._envoyer(200, {'ok': False, 'erreur': 'projet introuvable'})
                    e = json.load(open(f, encoding='utf-8'))
                    e.setdefault('champs', {})['p-nom' if e.get('onglet') in ('esprits', 'totems') else 'f-nom'] = str(demande.get('titre', ''))[:80]
                    tmp = f + '.tmp'
                    json.dump(e, open(tmp, 'w', encoding='utf-8'), ensure_ascii=False)
                    os.replace(tmp, f)
                    return self._envoyer(200, {'ok': True})
                os.makedirs(os.path.dirname(f), exist_ok=True)
                tmp = f + '.tmp'
                json.dump(demande.get('etat') or {}, open(tmp, 'w', encoding='utf-8'), ensure_ascii=False)
                os.replace(tmp, f)
                return self._envoyer(200, {'ok': True})
            if u.path == '/api/banniere_apercu':          # (21/11) bannière perso de la technique ouverte : aussi pour les aperçus
                c = os.path.basename(demande.get('projet') or '')       # (21/11) rangée sous le PROJET, pas sous le code du jeu
                if not c:
                    return self._envoyer(200, {'ok': False, 'erreur': 'projet inconnu'})
                f_ap = os.path.join(CACHE, 'bannieres_apercu', c + '.png')
                if demande.get('image'):
                    export.ecrire_png_banniere(demande['image'], f_ap)
                else:                                   # (23/11) depuis un texte (fenêtre de la technique : lettres du jeu / simple)
                    os.makedirs(os.path.dirname(f_ap), exist_ok=True)
                    export.banniere(str(demande.get('texte') or ' '), demande.get('couleur') or '#f5c842', demande.get('contour') or '#0d1a4a',
                                    f_ap, element=demande.get('element'), style=demande.get('style') or 'jeu')
                # (22/11, retour de muku : « faire sa bannière, puis recharger la technique : pas intuitif ») le lecteur natif ouvert
                # reçoit la nouvelle bannière TOUT DE SUITE : telop.bin de la scène réécrit, puis commande « telop » (relue sans relancer)
                X = _natif()
                tech = os.path.basename(str(demande.get('code') or ''))
                dos = os.path.join(os.path.dirname(X.__file__), 'scenes', 'tech_' + tech) if X is not None and tech else None
                if dos and os.path.isfile(os.path.join(dos, 'tech.json')):
                    try:
                        APERCU['projet'] = c
                        X._ecrire_telop(dos, tech, json.load(open(os.path.join(dos, 'tech.json'), encoding='utf-8')).get('telop'), sys.modules[__name__])
                        natif_commande('telop')
                    except Exception as ex:
                        print('bannière du lecteur natif :', ex)
                return self._envoyer(200, {'ok': True})
            if u.path == '/api/banniere_esprit':          # (23/11) bannière d'un esprit / totem (son nom) ou ARMED d'une armure, depuis l'éditeur
                return self._envoyer(200, enregistrer_banniere_esprit(demande))
            if u.path == '/api/banniere':
                t = PAR_CODE.get(demande.get('base', ''))
                telop = techniques.lire_cinematique(CFG['data_dir'], t['cinematique'])['telop'] if t else demande.get('base')
                r_ban = export.enregistrer_banniere(CFG, demande['nom'], demande['image'], telop or demande.get('base'))
                # (25/11, retour de muku : « j'ai changé la bannière mais sur la preview ça ne change pas ») l'aperçu prend d'abord
                # cache/bannieres_apercu/<projet>.png (telop_apercu, faite à la création avec le nom) : les projets liés à cette
                # copie reçoivent la même image, et le lecteur du jeu ouvert sur elle la relit
                if r_ban.get('ok') and r_ban.get('key'):
                    for f_pj in glob.glob(os.path.join(ICI, 'projets', '*.json')):
                        try:
                            cr = (json.load(open(f_pj, encoding='utf-8')) or {}).get('cree') or {}
                        except (OSError, ValueError, AttributeError):
                            continue
                        if cr.get('mod') == 'MesTechniques' and str(cr.get('code')) == r_ban['key']:
                            export.ecrire_png_banniere(demande['image'], os.path.join(CACHE, 'bannieres_apercu', os.path.basename(f_pj)[:-5] + '.png'))
                    X = _natif()
                    dos = os.path.join(os.path.dirname(X.__file__), 'scenes', 'tech_' + r_ban['key']) if X is not None else None
                    if dos and os.path.isfile(os.path.join(dos, 'tech.json')):
                        try:
                            X._ecrire_telop(dos, r_ban['key'], json.load(open(os.path.join(dos, 'tech.json'), encoding='utf-8')).get('telop'), sys.modules[__name__])
                            natif_commande('telop')
                        except Exception as ex:
                            print('bannière du lecteur natif :', ex)
                return self._envoyer(200, r_ban)
            if u.path == '/api/vignette':                # comparaison aux vidéos officielles : image de l'Atelier (JPEG) -> cache
                import base64, re as _re
                code = _re.sub(r'[^a-z0-9_]', '', demande.get('code', ''))
                d = os.path.join(CACHE, 'comparaison', code); os.makedirs(d, exist_ok=True)
                open(os.path.join(d, 'atelier_%04d.jpg' % int(demande['image'])), 'wb').write(base64.b64decode(demande['jpeg']))
                return self._envoyer(200, {'ok': True})
            if u.path == '/api/rendu_d3d':               # PROTOTYPE : effets dessinés par Direct3D 11 avec les vrais shaders du jeu
                return self._envoyer(200, rendu_d3d(demande))
            if u.path == '/api/natif_cmd':               # commande au lecteur incrusté (lecture, pause, image, zone…)
                if str(demande.get('cmd', '')) == 'quitter':    # (fermeture : aussi un lecteur encore en chargement)
                    arreter_natifs(int(demande['pid']) if demande.get('pid') else None); return self._envoyer(200, {'actif': False})
                return self._envoyer(200, natif_commande(str(demande.get('cmd', '')), bool(demande.get('attendre'))))
            if u.path == '/api/natif_textures':          # retouche de couleur PENDANT la lecture : modifs.bin réécrit, le lecteur le relit
                X = _natif()
                if X is None or not demande.get('technique'):
                    return self._envoyer(200, {'actif': False})
                dos = os.path.join(os.path.dirname(X.__file__), 'scenes', 'tech_' + os.path.basename(str(demande['technique'])))
                n = X.ecrire_modifs(dos, demande.get('modifs')) if os.path.isdir(dos) else 0
                return self._envoyer(200, dict(natif_commande('textures'), retouches=n))
            if u.path == '/api/natif_options':           # (15/11/2026) pièces cachées / couleurs PENDANT la lecture : options.json relu
                X = _natif()
                if X is None or not demande.get('technique'):
                    return self._envoyer(200, {'actif': False})
                dos = os.path.join(os.path.dirname(X.__file__), 'scenes', 'tech_' + os.path.basename(str(demande['technique'])))
                if os.path.isdir(dos):
                    json.dump({k: demande.get(k) or ([] if k in ('caches', 'fil') else {}) for k in ('caches', 'couleurs', 'sommets', 'particules', 'lumieres', 'auras', 'fil')},
                              open(os.path.join(dos, 'options.json'), 'w', encoding='utf-8'))
                return self._envoyer(200, natif_commande('options'))
            if u.path == '/api/natif':                   # lecteur natif (C++ / Direct3D 11) : export de la scène + lancement
                return self._envoyer(200, lecteur_natif(demande))
            if u.path == '/api/capture':                 # image de la vue 3D -> cache/captures (vérifications)
                import base64
                d = os.path.join(CACHE, 'captures'); os.makedirs(d, exist_ok=True)
                f = os.path.join(d, os.path.basename(demande.get('nom', 'capture')) + '.png')
                open(f, 'wb').write(base64.b64decode(demande['image'].split(',', 1)[1]))
                return self._envoyer(200, {'ok': True, 'fichier': f})
            if u.path == '/api/copie_outfit':             # (15/11/2026) tenue recolorée à équiper (MesTenues)
                e = JEU_CODE.get(('tenues', demande.get('code')))
                return self._envoyer(200, copies_outfits.exporter(CFG, demande, e) if e else {'ok': False, 'erreur': 'tenue inconnue'})
            if u.path == '/api/copie_tenue':              # (15/11/2026) nouveau joueur qui porte la tenue recolorée (MesPersonnages)
                e = JEU_CODE.get(('tenues', demande.get('code')))
                return self._envoyer(200, copies_tenues.exporter(CFG, demande, e) if e else {'ok': False, 'erreur': 'tenue inconnue'})
            if u.path == '/api/copie_objet':              # (15/11/2026) nouveau joueur qui porte l'objet recoloré (accessoire)
                e = JEU_CODE.get(('tenues', demande.get('code'))) or JEU_CODE.get(('objets3d', demande.get('code')))   # accessoire 3D
                return self._envoyer(200, copies_tenues.exporter_objet(CFG, demande, e) if e else {'ok': False, 'erreur': 'objet inconnu'})
            if u.path == '/api/copie_objet_jeu':         # (15/11/2026) copie d'un objet du jeu (MesObjets)
                e = JEU_CODE.get(('objets', demande.get('code')))
                return self._envoyer(200, objets_jeu.exporter(CFG, demande, e) if e else {'ok': False, 'erreur': 'objet inconnu'})
            if u.path == '/api/copie_armure':             # (15/11/2026) armure recolorée pour une de mes copies d'esprit (MesEsprits)
                e = JEU_CODE.get(('armures', demande.get('code')))
                if not e:
                    return self._envoyer(200, {'ok': False, 'erreur': 'armure inconnue'})
                return self._envoyer(200, armures_copies.exporter(CFG, demande, e))
            if u.path == '/api/coups':                   # (15/11/2026) choisir les techniques d'une copie de personnage
                return self._envoyer(200, copies_persos.choisir_coups(CFG, demande.get('cle'), demande.get('coups'),
                                                                      coups.catalogue(CFG['data_dir'], cache_txt()), coups.mes_coups(CFG)))
            if u.path == '/api/ouvrir_discord':          # (27/11, muku) bouton « Rejoins mon serveur » : adresse FIXE, navigateur par défaut
                return self._envoyer(200, {'ok': bool(webbrowser.open('https://discord.gg/D9DvjdnFVE'))})
            if u.path == '/api/peau_copie':              # (26/11) peau des bras / jambes d'une copie de personnage déjà créée
                return self._envoyer(200, copies_persos.regler_peau(CFG, demande.get('cle'), demande.get('peau')))
            if u.path == '/api/technique_liee':          # (15/11/2026) « c'est la technique de cet esprit »
                t = demande.get('technique')
                if t:
                    t = next((x for x in coups.catalogue(CFG['data_dir'], cache_txt()) + coups.mes_coups(CFG) if x['id'] == int(t)), None)
                    if not t:
                        return self._envoyer(200, {'ok': False, 'erreur': 'technique inconnue'})
                return self._envoyer(200, esprits.lier_technique(CFG, demande.get('code'), t, CACHE))
            if u.path == '/api/icone_copie':             # (16/11/2026) refaire le portrait d'une copie avec une photo du modèle
                return self._envoyer(200, icone_copie(demande))
            if u.path == '/api/copie_personnage':         # (15/11/2026) copie d'un personnage avec sa tête recolorée (MesPersonnages)
                if demande.get('action') == 'retirer':
                    return self._envoyer(200, copies_persos.retirer(CFG, demande.get('cle')))
                e = JEU_CODE.get(('personnages', demande.get('code')))
                if not e:
                    return self._envoyer(200, {'ok': False, 'erreur': 'tête inconnue'})
                return self._envoyer(200, copies_persos.exporter(CFG, demande, e))
            if u.path == '/api/retouche':                 # (15/11/2026) REMPLACEMENT RETIRÉ : seulement des copies (choix de muku)
                return self._envoyer(200, {'ok': False, 'erreur': 'L’Atelier ne remplace jamais l’original : seulement des copies.'})
                if demande.get('action') == 'retirer':
                    return self._envoyer(200, retouches.retirer(CFG, demande.get('cat'), demande.get('code')))
                e = JEU_CODE.get((demande.get('cat'), demande.get('code')))
                if not e or demande.get('cat') == 'maillots':
                    return self._envoyer(200, {'ok': False, 'erreur': 'élément inconnu'})
                return self._envoyer(200, retouches.exporter(CFG, demande, e))
            if u.path == '/api/maillot':                  # (15/11/2026) Atelier Maillots dans l'Atelier
                a = demande.get('action')
                if a == 'enregistrer':
                    return self._envoyer(200, mes_maillots.enregistrer(CFG, demande))
                if a == 'supprimer':
                    return self._envoyer(200, mes_maillots.supprimer(demande.get('id')))
                if a == 'construire':
                    return self._envoyer(200, mes_maillots.construire(CFG))
                return self._envoyer(200, {'ok': False, 'erreur': 'action inconnue'})
            if u.path == '/api/exporter_personnage':
                return self._envoyer(200, esprits.exporter(CFG, demande, PERSO_CODE[demande['code']]))
            if u.path == '/api/installer':
                return self._envoyer(200, export.installer(CFG, demande.get('mod', export.MOD_ID), forcer=bool(demande.get('forcer'))))
            if u.path == '/api/enregistrer_export':      # (25/11/2026) ⬇ PNG / ⬇ Modèle (.glb) : web/export_modele.js
                return self._envoyer(200, enregistrer_export(demande))
            if u.path == '/api/ouvrir_maillots':
                if not os.path.isfile(MAILLOTS):
                    return self._envoyer(200, {'ok': False, 'erreur': 'Atelier Maillots introuvable : ' + MAILLOTS})
                subprocess.Popen([MAILLOTS], cwd=os.path.dirname(MAILLOTS))
                return self._envoyer(200, {'ok': True})
            return self._envoyer(404, {'erreur': 'introuvable'})
        except Exception as ex:
            traceback.print_exc()
            return self._envoyer(500, {'ok': False, 'erreur': str(ex)})

    def _fichier(self, p):
        if not os.path.isfile(p):
            return self._envoyer(404, {'erreur': 'fichier introuvable'})
        t = mimetypes.guess_type(p)[0] or 'application/octet-stream'
        if p.endswith('.js'):
            t = 'text/javascript; charset=utf-8'
        return self._envoyer(200, open(p, 'rb').read(), t)


EDGE = [r'C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe', r'C:\Program Files\Microsoft\Edge\Application\msedge.exe']


THEMES = ('jeu', 'or', 'sobre', 'bleu', 'turquoise')


def parametres():
    """(22/11, idée de muku : « des paramètres, les gens pourront choisir ») réglages de l'interface, dans config.json
    (pas dans le navigateur : sa mémoire change avec le port). Musique coupée d'office.
    (23/11) palette « jeu » (refonte : les menus du jeu) par défaut ; une palette choisie AVANT la refonte ne compte plus."""
    p = dict(CFG.get('parametres') or {})
    th = p.get('theme') if p.get('theme') in THEMES and p.get('theme_v2') else 'jeu'
    return {'theme': th, 'musique': p.get('musique') is True, 'theme_v2': bool(p.get('theme_v2')),
            'volume': p['volume'] if isinstance(p.get('volume'), (int, float)) and 0 <= p['volume'] <= 1 else 0.35}


MES_MODS = ('MesTechniques', 'MesEsprits', 'MesPersonnages', 'MesTenues', 'MesObjets', 'MesMaillots')


def _infos_jeu(d):
    """un dossier du jeu : VRFW dans son dossier mods ? nos mods déjà installés ? nombre de mods"""
    m = os.path.join(d or '', 'mods')
    noms = [x for x in os.listdir(m) if os.path.isdir(os.path.join(m, x))] if os.path.isdir(m) else []
    return {'dossier': d, 'vrfw': 'VRFW' in noms, 'nb_mods': len(noms), 'mes_mods': [x for x in MES_MODS if x in noms]}


def dossier_jeu():
    """(22/11, retour d'un joueur : créations « Installed » dans l'Atelier mais absentes de son gestionnaire de mods) le dossier
    du jeu où « Installer » met les mods (jeu_dir) et les autres installations trouvées, pour le voir et le changer dans
    ⚙ Paramètres. Un même PC peut avoir le jeu de base (steamapps\\common) ET une copie de dépôt (steamapps\\content)."""
    vus, liste = set(), []
    for d, _n in [(CFG.get('jeu_dir'), 0)] + config_auto.dossiers_du_jeu(ICI):
        if d and d.lower() not in vus and config_auto.jeu_valide(d):
            vus.add(d.lower())
            liste.append(_infos_jeu(d))
    return {'actuel': CFG.get('jeu_dir'), 'demarrage': JEU_AU_DEMARRAGE, 'liste': liste}


def choisir_dossier_jeu(d):
    d = os.path.normpath(str(d or '').strip().strip('"')) if d else ''
    if not config_auto.jeu_valide(d):
        return {'ok': False, 'erreur': 'Ce dossier ne contient pas le jeu (nie.exe + data\\cpk_list.cfg.bin).'}
    CFG['jeu_dir'] = d
    sauver_cfg()
    return dict(dossier_jeu(), ok=True)


def ouvrir_fenetre(url, port=None):
    """(22/11, muku : « c'est censé être une appli, pas un truc sur Edge ») la VRAIE fenêtre de l'Atelier : Atelier Inazuma.exe
    (WinForms + WebView2) avec --port, qui reprend ce serveur (même dossier, même version : /api/identite) au lieu d'en lancer un.
    Edge --app / navigateur seulement si le programme manque (autre système, dossier incomplet)."""
    exe = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'Atelier Inazuma.exe')
    if os.name == 'nt' and os.path.isfile(exe):
        try:
            subprocess.Popen([exe] + (['--port', str(port)] if port else []), cwd=os.path.dirname(exe))
            return
        except OSError as ex:
            print("fenêtre de l'Atelier :", ex)
    edge = next((e for e in EDGE if os.path.isfile(e)), None)
    if edge:
        profil = os.path.join(CACHE, 'fenetre')        # profil à part : la fenêtre garde sa taille, rien ne se mélange
        subprocess.Popen([edge, '--app=' + url, '--user-data-dir=' + profil, '--window-size=1500,920', '--no-first-run'])
    else:
        webbrowser.open(url)


PREPA = {'pret': False}


def preparer_index():
    """au démarrage : index des textures du jeu (long au 1er lancement) puis contenu des mods, avant la 1re demande"""
    from moteur import mods_jeu
    try:
        mods_jeu._index_jeu(CFG['data_dir'], CACHE)
        mods_liste(frais=True)
    except Exception as ex:
        print('préparation :', ex)
    PREPA['pret'] = True
    if CFG.get('lecture_directe') and not os.path.isdir(os.path.join(CACHE, 'data_jeu', 'common', 'sound_asset')):
        try:                                       # 1er lancement : banques de sons sorties des paquets en arrière-plan
            son.trouver_banque(CFG['data_dir'], 'aucun_son_atelier_inazuma')    # (sinon ~70 s au tout 1er son)
        except Exception as ex:
            print('sons :', ex)


def reprendre_mods_installes():
    """(21/11) Atelier neuf (nouvelle version décompressée ailleurs, autre PC, sortie effacée) mais créations déjà dans le
    jeu : « Installer » remplaçait mods/<mod> par la sortie VIDE de cet Atelier -> toutes les créations d'avant disparaissaient
    du jeu. Au démarrage, un mod de l'Atelier présent dans le jeu (avec son registre outil_*.json) et absent de la sortie est
    recopié dans la sortie : les nouvelles créations s'y ajoutent, rien n'est perdu."""
    import shutil
    mods = os.path.join(CFG.get('jeu_dir') or '', 'mods')
    for mod_id in ('MesPersonnages', 'MesEsprits', 'MesObjets', 'MesTenues', 'MesTechniques'):
        src, dst = os.path.join(mods, mod_id), os.path.join(ICI, 'sortie', mod_id)
        try:
            if os.path.isfile(os.path.join(dst, 'mod.toml')) or not os.path.isfile(os.path.join(src, 'mod.toml')) \
                    or not glob.glob(os.path.join(src, 'outil_*.json')):
                continue
            shutil.copytree(src, dst, dirs_exist_ok=True)
            print('créations reprises du jeu / creations taken back from the game :', mod_id)
        except Exception as ex:
            print('reprise de %s impossible : %s' % (mod_id, ex))


def version_atelier():
    try:
        return open(os.path.join(ICI, 'version.txt'), encoding='utf-8').read().strip()
    except OSError:
        return ''


PARENTS = set()          # (21/11) fenêtres « Atelier Inazuma.exe » qui utilisent ce serveur (--parent PID, /api/parent)


def surveiller_parents():
    """(21/11) le lanceur tué, planté ou fermé par Windows sans arrêter le serveur : avant, pythonw restait ouvert en
    arrière-plan (processeur, port 8765 pris) et le lancement suivant, même d'une NOUVELLE version, réutilisait ce vieux
    serveur. Le serveur s'arrête maintenant quand plus aucune de ses fenêtres n'existe."""
    import ctypes, time
    k = ctypes.windll.kernel32
    k.OpenProcess.restype = ctypes.c_void_p
    def vivant(pid):
        h = k.OpenProcess(0x00100000, False, pid)            # SYNCHRONIZE
        if not h:
            return False
        try:
            return k.WaitForSingleObject(ctypes.c_void_p(h), 0) == 0x102     # WAIT_TIMEOUT : toujours en vie
        finally:
            k.CloseHandle(ctypes.c_void_p(h))
    while True:
        time.sleep(2)
        if PARENTS and not any(vivant(p) for p in list(PARENTS)):
            print('fenêtre de l\'Atelier fermée : arrêt du serveur')
            try:
                arreter_natifs()
            finally:
                os._exit(0)


def main():
    reprendre_mods_installes()
    if '--parent' in sys.argv and os.name == 'nt':
        try:
            PARENTS.add(int(sys.argv[sys.argv.index('--parent') + 1]))
            threading.Thread(target=surveiller_parents, daemon=True).start()
        except (IndexError, ValueError):
            pass
    port = int(sys.argv[sys.argv.index('--port') + 1]) if '--port' in sys.argv else CFG.get('port', 8765)   # --port N : autre port (essais)
    srv = ThreadingHTTPServer(('127.0.0.1', port), Gestion)
    threading.Thread(target=preparer_index, daemon=True).start()

    def _lettres_jeu():                  # (23/11) alphabet des bannières du jeu (moteur/lettres_jeu.py) : fait une fois, ~3 min
        try:
            from moteur import lettres_jeu
            if not lettres_jeu.disponible(CACHE):
                lettres_jeu.construire(CFG, CACHE, journal=lambda *a: None)
                lettres_jeu._ALPHA.clear()
                print('bannières : lettres du jeu prêtes')
            from moteur import police_image             # (24/11) polices-images des planches de muku (~1 min, une fois)
            for k_ in police_image.PLANCHES:
                if not police_image.disponible(k_, CACHE):
                    police_image.construire(k_, CACHE, journal=print)
            if not lettres_jeu.styles_disponibles(CACHE):      # (24/11) styles esprit guerrier / totem / ARMED (~30 s)
                lettres_jeu.construire_styles(CFG, CACHE, journal=lambda *a: None)
                # (24/11, essai du paquet 3.0) une bannière demandée PENDANT la construction gardait en mémoire l'alphabet sans
                # les styles (armure en lettres Néant teintées) jusqu'au redémarrage : on l'oublie, relu à la prochaine demande
                lettres_jeu._ALPHA.clear()
                print('bannières : styles esprit guerrier / totem prêts')
        except Exception as ex:
            print('lettres du jeu :', ex)
    threading.Thread(target=_lettres_jeu, daemon=True).start()
    url = 'http://127.0.0.1:%d/' % port
    print('Atelier Inazuma : %s  (%d techniques, %d esprits et totems)  -  fermer cette fenêtre pour arrêter' % (url, len(INDEX), len(PERSOS)))
    if '--sans-navigateur' not in sys.argv:
        threading.Timer(0.8, lambda: ouvrir_fenetre(url, port)).start()
    import atexit
    atexit.register(arreter_natifs)              # (serveur fermé : ses lecteurs aussi)
    srv.serve_forever()


if __name__ == '__main__':
    main()
