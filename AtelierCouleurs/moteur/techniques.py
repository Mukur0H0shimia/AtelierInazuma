"""Index des techniques du jeu et lecture d'une cinématique (ce qu'elle charge : objets d'effet, auras, modèles).

- noms : text/<langue>/skill_text.cfg.bin (id du nom -> texte) ; skill_config : le crc32 du code de la technique est 24 octets
  avant l'id de son nom ; l'octet faible du mot à +4x13 (depuis code - 8) = élément, l'octet suivant = couleur du tir ;
- codes : les bannières de dx11/menu/220_img/telop_waza/fr/<code>.g4tx (toutes les techniques qui ont une bannière) ;
- cinématique : whs -> ev60, who -> ev61, whd -> ev62, whk -> ev63 (+ les 5 chiffres), si event_cfg/evt/<id>.cfg.bin existe.
"""
from moteur import langue as _langue  # noqa: E402  (FR / EN)
import os, re, glob, struct, zlib, json
from . import cfgbin

ELEMENTS = {1: 'wind', 2: 'forest', 3: 'fire', 4: 'mountain', 5: 'void'}
ELEMENTS_FR = {'wind': 'Air', 'forest': 'Forêt', 'fire': 'Feu', 'mountain': 'Montagne', 'void': 'Néant'}
GENRES = {'whs': ('ev60', 'Tir'), 'who': ('ev61', 'Dribble'), 'whd': ('ev62', 'Défense'), 'whk': ('ev63', 'Gardien')}
# lettre de la famille d'auras de tir du jeu (ega0075a-e...) par élément (d = Forêt et e = Néant vérifiés)
LETTRE_TIR = {'mountain': 'a', 'wind': 'b', 'fire': 'c', 'forest': 'd', 'void': 'e'}


def _textes(data_dir, langue=None):
    langue = langue or _langue.code()                  # (FR / EN)
    L = cfgbin.lire(open(os.path.join(data_dir, 'common', 'text', langue, 'skill_text.cfg.bin'), 'rb').read())
    t = {}
    for c, v in L:
        if len(v) > 5 and isinstance(v[0], int) and isinstance(v[5], str):
            t.setdefault(v[0], v[5])
    return t


_NOMS_EVT = {}


def _noms_evt(evt_dir):
    """crc32(nom) -> nom des configurations de cinématique (dossier event_cfg/evt)"""
    if evt_dir not in _NOMS_EVT:
        _NOMS_EVT[evt_dir] = {zlib.crc32(f[:-8].encode()): f[:-8] for f in os.listdir(evt_dir) if f.endswith('.cfg.bin')}
    return _NOMS_EVT[evt_dir]


def construire_index(data_dir, cache_dir):
    f = os.path.join(cache_dir, 'index_techniques.json')
    if os.path.exists(f):
        return json.load(open(f, encoding='utf-8'))
    noms = _textes(data_dir)
    sc = open(glob.glob(os.path.join(data_dir, 'common', 'gamedata', 'skill', 'skill_config_*.cfg.bin'))[0], 'rb').read()
    codes = sorted({os.path.basename(p)[:-5] for p in glob.glob(os.path.join(data_dir, 'dx11', 'menu', '220_img', 'telop_waza', 'fr', 'wh*.g4tx'))})
    evt_dir = os.path.join(data_dir, 'common', 'event_cfg', 'evt')
    index = []
    for code in codes:
        prefixe = code[:3]
        if prefixe not in GENRES:
            continue
        i = sc.find(struct.pack('<I', zlib.crc32(code.encode())))
        if i < 8:
            continue
        r = struct.unpack_from('<20i', sc, i - 8)
        nom = noms.get(r[8])
        mot = r[13] & 0xFFFFFFFF
        element = ELEMENTS.get(mot & 0xFF)
        couleur = (mot >> 8) & 0xFF
        ev = '%s_%s' % (GENRES[prefixe][0], code[3:])
        ev2 = None
        if os.path.exists(os.path.join(evt_dir, ev + '.cfg.bin')) and os.path.exists(os.path.join(evt_dir, ev + '_1.cfg.bin')) \
                and _base_sans_chargement(data_dir, ev):
            # 14/11/2026 : 4 techniques (whd00110, whd00190, whd00420, whk01490) ont une configuration de base qui PILOTE son
            # effet principal (0xA9BDE997) sans jamais le CHARGER (pas de 0x799A1EBA) : elle ne peut pas montrer l'effet que
            # montre la vidéo officielle. Le jeu joue donc <ev>_1 / <ev>_2 (qui le chargent) : on prend ces deux parties.
            ev, ev2 = ev + '_1', ev + '_2' if os.path.exists(os.path.join(evt_dir, ev + '_2.cfg.bin')) else None
        elif not os.path.exists(os.path.join(evt_dir, ev + '.cfg.bin')):
            # gardiens (178) et une partie des défenses (44) : cinématique en DEUX parties <ev>_1 / <ev>_2 (deux issues),
            # qui partagent le dossier d'animation <ev> (13/11/2026 : avant, ces 222 techniques manquaient)
            if not os.path.exists(os.path.join(evt_dir, ev + '_1.cfg.bin')):
                continue
            ev, ev2 = ev + '_1', ev + '_2' if os.path.exists(os.path.join(evt_dir, ev + '_2.cfg.bin')) else None
        # (14/11/2026) CINÉMATIQUE LUE DANS LA FICHE DE COMPÉTENCE : le mot qui suit le crc du code (r[4]) est le crc32 du
        # nom de la cinématique jouée. Elle diffère du nom déduit du code pour 3 techniques : whs03280 Dernier recours Σ ->
        # ev60_03285 (version complète, 4 joueurs : durée et coupes identiques à la vidéo officielle), whs03180 -> ev60_03185,
        # whd01530 -> ev62_01535_1 (+ _2). Ailleurs (855) la fiche donne le même nom (ou sa base pour les _1 / _2).
        ev_fiche = _noms_evt(evt_dir).get(r[4] & 0xFFFFFFFF)
        if ev_fiche and ev_fiche != ev and ev_fiche != ev.rsplit('_', 1)[0] and ev_fiche != '%s_%s' % (GENRES[prefixe][0], code[3:]):
            ev = ev_fiche
            ev2 = ev[:-2] + '_2' if ev.endswith('_1') and os.path.exists(os.path.join(evt_dir, ev[:-2] + '_2.cfg.bin')) else None
        e = {'code': code, 'nom': nom or code, 'genre': GENRES[prefixe][1], 'element': element,
             'couleur_tir': couleur, 'cinematique': ev}
        if ev2:
            e['cinematique_2'] = ev2
        index.append(e)
    json.dump(index, open(f, 'w', encoding='utf-8'), ensure_ascii=False, indent=0)
    return index


def _base_sans_chargement(data_dir, ev):
    """vrai si la config de base <ev> pilote un effet (0xA9BDE997 [nom, plan, …]) qu'elle ne charge jamais (LOAD)"""
    base = os.path.join(data_dir, 'common', 'event_cfg')
    eff = _commandes(os.path.join(base, 'eff', ev + '_eff.cfg.bin'))
    evt = _commandes(os.path.join(base, 'evt', ev + '.cfg.bin'))
    pilotes = {a[0] for c, a in eff if c == 0xA9BDE997 and a and isinstance(a[0], str)}
    charges = {a[0] for c, a in eff + evt if c == LOAD and len(a) >= 2}
    return bool(pilotes - charges)


def _commandes(chemin):
    """liste des (crc de commande, arguments) d'un .cfg.bin d'événement"""
    if not os.path.exists(chemin):
        return []
    L = cfgbin.lire(open(chemin, 'rb').read())
    out = []
    for k in range(len(L) - 1):
        c, v = L[k]
        if cfgbin.NOMS.get(c) == 'EVENT_COMMAND_HEADER' and len(v) >= 2:
            out.append(((v[1] & 0xFFFFFFFF), L[k + 1][1]))
    return out


LOAD, ATTACH = 0x799A1EBA, 0xC3FB5CC5


def lire_cinematique(data_dir, ev):
    base = os.path.join(data_dir, 'common', 'event_cfg')
    eff = _commandes(os.path.join(base, 'eff', ev + '_eff.cfg.bin'))
    evt = _commandes(os.path.join(base, 'evt', ev + '.cfg.bin'))
    objets, auras, modeles, telop = [], [], [], None
    for k_, (cmd, a) in enumerate(eff + evt):
        liste = 'eff' if k_ < len(eff) else 'evt'      # (14/11/2026) liste de commandes (pour l'event_command du mod)
        if cmd == LOAD and len(a) >= 2 and isinstance(a[1], str):
            if a[1].endswith('.objbin') and '/effect/' in a[1] and a[0] not in [o['acteur'] for o in objets]:
                objets.append({'acteur': a[0], 'chemin': a[1]})
            elif not a[1].endswith(('.objbin', '.g4sk')) and a[1] not in ('b000001', 'INVARID') and a[0] not in [m['acteur'] for m in modeles]:
                modeles.append({'acteur': a[0], 'modele': a[1], 'liste': liste})
            elif a[1].endswith('.objbin') and '/chr/' in a[1] and a[0] not in [m['acteur'] for m in modeles]:
                # (14/11/2026) modèle de personnage chargé par son CHEMIN (ex. common/chr/i000001/i000001.objbin : 8 chargements)
                modeles.append({'acteur': a[0], 'modele': os.path.basename(a[1])[:-7], 'liste': liste, 'chemin': a[1]})
        elif cmd == ATTACH and len(a) >= 2 and isinstance(a[1], str):
            if a[1] not in [x['aura'] for x in auras]:
                auras.append({'aura': a[1], 'acteurs': []})
            x = next(x for x in auras if x['aura'] == a[1])
            if a[0] not in x['acteurs']:
                x['acteurs'].append(a[0])
    # effets de combat communs (ega0001 = traits de vitesse) : chargés par 0x96CCCA47 [nom], collés à la caméra
    for cmd, a in eff + evt:
        if cmd == 0x96CCCA47 and a and isinstance(a[0], str) and a[0].startswith('ega') and a[0] not in [o['acteur'] for o in objets]:
            ch = 'common/effect/battle/common/%s/%s.objbin' % (a[0], a[0])
            if os.path.exists(os.path.join(data_dir, *ch.split('/'))):
                objets.append({'acteur': a[0], 'chemin': ch, 'commun': True})
    # aura du ballon (commande 0xC3FB5CC5) : CORRIGÉ le 13/11/2026 — dans les cinématiques le jeu n'ajoute PAS de modèle
    # d'aura : c'est un EFFET DE STATUT (effect_status_define, CStatusEffComponent) posé sur le modèle du ballon
    # (shaders chr_toon*_effstatus, cb7 u_charaStatus*). L'ancien ajout du modèle ega0020 (supposé) dessinait un petit
    # tourbillon coloré au centre du ballon (Big Bang) qui n'existe pas dans le jeu. Voir moteur/aura_balle.py.
    if False and any(cmd == 0xC3FB5CC5 for cmd, a in eff + evt) and 'ega0020' not in [o['acteur'] for o in objets]:
        ch = 'common/effect/battle/common/ega0020/ega0020.objbin'
        if os.path.exists(os.path.join(data_dir, *ch.split('/'))):
            objets.append({'acteur': 'ega0020', 'chemin': ch, 'commun': True, 'aura_balle': True})
    for cmd, a in evt:
        for s in a:
            if isinstance(s, str) and s.startswith('soccer10_01_'):
                telop = s[len('soccer10_01_'):]
    # (14/11/2026) ESPRIT DU JOUEUR : « <ASSIGN>_s00_p<VARIATION> » chargé par 0x35746E60 avec INVARID (le jeu y met l'esprit du
    # joueur). Code = celui des animations de la cinématique (ev61_00920_k000010_… pour Éclair de Pégase), comme anim.py.
    try:
        from .anim import dossier_ev
        c = os.path.join(data_dir, 'common')
        dos = os.path.join(c, 'event', ev.split('_')[0], dossier_ev(c, ev))
        codes = sorted({m.group(1) for f in (os.listdir(dos) if os.path.isdir(dos) else []) for m in [re.match(r'.+?_([ka]\d{6})_s\d\d_', f)] if m})
        explicites = {m['modele'] for m in modeles}
        for k_, (cmd, a) in enumerate(eff + evt):
            if cmd == 0x35746E60 and len(a) >= 2 and isinstance(a[0], str) and a[0].startswith('<ASSIGN>') and a[0] not in [m['acteur'] for m in modeles]:
                code = next((x for x in codes if x not in explicites), None)
                if code:
                    modeles.append({'acteur': a[0], 'modele': code, 'liste': 'eff' if k_ < len(eff) else 'evt',
                                    'commande': 'CMD_35746E60', 'esprit_du_joueur': True})
    except Exception as ex:
        print('esprit du joueur', ev, ex)
    return {'cinematique': ev, 'objets': objets, 'auras': auras, 'modeles': modeles, 'telop': telop}
