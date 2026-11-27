"""(15/11/2026) TECHNIQUES D'UN JOUEUR ET TECHNIQUE LIÉE D'UN ESPRIT (pour « Mes créations »).

Règles LUES :
- chara_param (carte) : colonnes 11 à 28 = 9 emplacements [technique, niveau d'apprentissage] (5609 cartes sur 6176 en ont 9 ;
  VRFW : « the 9 learn slots are used ») ; technique = crc32(code) : 34641 « wh… », 11174 « wa… », 5539 « rh… », 190 « wk… »…,
  tous retrouvés dans skill_config / aura_skill_config. Colonne 10 ≠ 0 = la carte a son plateau de compétences (187 cartes) :
  VRFW dit qu'une technique ajoutée n'y apparaît que si le plateau la contient.
- VRFW.character/2, [[character.cards]] moves = [{ move = 0x…, level = N }, …] (Mukuro, qui marche en jeu : 4 techniques du jeu
  + son esprit 0xE2A57C99 = crc32("wks_mukuro_michael")).
- aura_skill_config : v[0] = crc32(code), v[1] = code, v[2] = id du nom, v[6] = crc32(technique liée) (wks02010 Victoria -> whs10200) ;
  VRFW.technique/3 [[aura_command]] cells.linked_skill = crc32(clé de la technique) (Mukuro : Michael -> « whs94200 »).
- skill_config : le crc32 du code est suivi, 24 octets plus loin, de l'id de son nom (moteur/techniques.py).
- une technique de MesTechniques = crc32(sa clé « whs96010 ») ; un esprit de MesEsprits = crc32(sa clé « wko_mesesprits_… »).
"""
import os, re, glob, json, zlib, struct
from . import cfgbin
from .personnages import _dernier
from .techniques import _textes

FAMILLES = [('whs', 'Tir'), ('who', 'Dribble'), ('whd', 'Défense'), ('whk', 'Gardien'),
            ('rhs', 'Tir simple'), ('rho', 'Dribble simple'), ('rhd', 'Défense simple'), ('rhk', 'Arrêt simple'),
            ('wk', 'Esprit guerrier'), ('wap', 'Aura'), ('wa', 'Armure'), ('wmm', 'Miximax'), ('ws', 'Totem'),
            ('wkt', 'Lien'), ('test_kizuna', 'Lien'), ('pv8', 'Lien'), ('awakening', 'Éveil'), ('mode_change', 'Mode')]
NB_EMPLACEMENTS = 9


def famille(code):
    if code.startswith('wkt'):
        return 'Lien'
    return next((g for p, g in FAMILLES if code.startswith(p)), 'Autre')


def catalogue(data_dir, cache_dir):
    """toutes les techniques du jeu qu'une carte peut apprendre : [{id, code, nom, genre}]"""
    f = os.path.join(cache_dir, 'index_coups_v2.json')          # (28/11) v2 : noms complets des esprits
    if os.path.exists(f):
        return json.load(open(f, encoding='utf-8'))
    noms = _textes(data_dir)
    noms_longs = _textes(data_dir, longs=True)          # (28/11) esprits / totems / armures : leur nom complet
    S = os.path.join(data_dir, 'common', 'gamedata', 'skill')
    out, vus = [], set()
    sc = open(_dernier(os.path.join(S, 'skill_config_*.cfg.bin')), 'rb').read()
    for code in sorted({m.group().decode() for m in re.finditer(rb'[a-z]{3}\d{5}', sc)}):
        i = sc.find(struct.pack('<I', zlib.crc32(code.encode())))
        nom = noms.get(struct.unpack_from('<i', sc, i + 24)[0]) if 8 <= i <= len(sc) - 28 else None
        if nom:
            out.append({'id': zlib.crc32(code.encode()), 'code': code, 'nom': nom, 'genre': famille(code)}); vus.add(code)
    for k, v in cfgbin.lire(open(_dernier(os.path.join(S, 'aura_skill_config_*.cfg.bin')), 'rb').read()):
        if len(v) > 6 and isinstance(v[1], str) and isinstance(v[0], int) and (v[0] & 0xFFFFFFFF) == zlib.crc32(v[1].encode()) and v[1] not in vus:
            nom = noms_longs.get(v[2]) if isinstance(v[2], int) else None
            if nom:
                out.append({'id': v[0] & 0xFFFFFFFF, 'code': v[1], 'nom': nom, 'genre': famille(v[1]),
                            'liee': v[6] & 0xFFFFFFFF if isinstance(v[6], int) else 0}); vus.add(v[1])
    json.dump(out, open(f, 'w', encoding='utf-8'), ensure_ascii=False, indent=0)
    return out


def carte(data_dir, id_carte):
    """techniques de la carte du jeu : ([{move, level}] dans l'ordre des emplacements, plateau oui/non)"""
    C = os.path.join(data_dir, 'common', 'gamedata', 'character')
    for k, v in cfgbin.lire(open(_dernier(os.path.join(C, 'chara_param_1*.cfg.bin')), 'rb').read()):
        if len(v) > 28 and isinstance(v[0], int) and (v[0] & 0xFFFFFFFF) == id_carte:
            coups = [{'move': v[i] & 0xFFFFFFFF, 'level': v[i + 1]} for i in range(11, 11 + 2 * NB_EMPLACEMENTS, 2)
                     if isinstance(v[i], int) and v[i]]
            return coups, bool(v[10])
    return [], False


def mes_coups(cfg):
    """mes techniques (MesTechniques) et mes esprits (MesEsprits) : [{id, code, nom, genre, mod}]"""
    out = []
    s = os.path.join(cfg['outil_dir'], 'sortie')
    f = os.path.join(s, 'MesTechniques', 'outil_techniques.json')
    if os.path.exists(f):
        for nom, e in sorted(json.load(open(f, encoding='utf-8')).items()):
            out.append({'id': zlib.crc32(e['key'].encode()), 'code': e['key'], 'nom': e.get('nom') or nom,
                        'genre': famille(e['key']), 'mod': 'MesTechniques', 'base': e.get('base')})
    f = os.path.join(s, 'MesEsprits', 'outil_esprits.json')
    if os.path.exists(f):
        for neuf, e in sorted(json.load(open(f, encoding='utf-8')).items()):
            out.append({'id': zlib.crc32(e['key'].encode()), 'code': e['key'], 'nom': e['nom'],
                        'genre': 'Totem' if neuf.startswith('a') else 'Esprit guerrier', 'mod': 'MesEsprits', 'copie': neuf,
                        'base': e.get('technique')})
    return out


# (15/11/2026) CharacterReforged (activé) : content/characters/learn_levels.toml, [VRFW.LearnLevels] (LU) :
#   AuraSlots = [9] : UNE case aura, la 9 ; VRFW y déplace l'aura écrite ailleurs (« aura(s) moved to an aura slot,
#   dropped from technique slots ») et retire la 2e (« a priority aura holds the aura slots ») ; AuraSlotPriority = [0, 3] :
#   esprit guerrier et totem passent avant les autres auras ; UnusedSlots = [7, 8] ; techniques = positions 1-6
#   (« is not a list position 1-6 ») ; Enforce = true + Tiers : niveaux d'apprentissage selon la puissance.
#   L'armure de l'esprit vient avec lui (extra_slots/skill_set.toml : RB + gauche = « the armour of the keshin »).
AURAS = {'Esprit guerrier', 'Totem', 'Armure', 'Aura', 'Miximax', 'Lien', 'Éveil', 'Mode'}
NB_TECHNIQUES = 6


def est_aura(x):
    return x.get('genre') in AURAS


def nettoyer(coups, connus):
    """liste reçue du navigateur -> [{move, level}] : 6 techniques au plus, puis UNE aura (esprit / totem…) en dernier
    (comme Mukuro : Michael après ses 4 techniques) ; connus = {id: fiche du catalogue}"""
    tech, aura, vus = [], [], set()
    for c in coups or []:
        try:
            m, n = int(c['move']) & 0xFFFFFFFF, int(c.get('level') or 1)
        except (KeyError, TypeError, ValueError):
            continue
        if not m or m in vus:
            continue
        x = connus.get(m)
        if not x:
            raise ValueError('technique 0x%08X inconnue (ni du jeu, ni de mes créations)' % m)
        vus.add(m)
        (aura if est_aura(x) else tech).append({'move': m, 'level': max(1, min(99, n))})
    if len(tech) > NB_TECHNIQUES:
        raise ValueError('%d techniques : 6 au plus (CharacterReforged : positions 1 à 6, cases 7 et 8 vides)' % len(tech))
    if len(aura) > 1:
        raise ValueError("un seul esprit guerrier / totem / armure : il n'y a qu'une case aura (la 9, CharacterReforged)")
    return tech + aura


_MODS = {}


def coups_des_mods(cfg, code_perso, id_carte):
    """techniques que les mods activés donnent déjà à ce personnage (CharacterReforged : [[edit]] target = code, moves,
    ou [[edit.cards]] id = carte, moves) : [{move, level}] du dernier mod qui en donne, et son nom"""
    import tomllib
    mods = os.path.join(cfg['jeu_dir'], 'mods')
    from .mods_jeu import actifs_ordonnes         # (22/11, 2.0.4) sans enabled.toml : tous les mods sont actifs
    actifs = actifs_ordonnes(mods)
    trouve = None
    for m in actifs:
        if m not in _MODS:
            par_code, par_carte = {}, {}
            for f in glob.glob(os.path.join(mods, m, 'content', 'characters', '**', '*.toml'), recursive=True):
                try:
                    t = tomllib.load(open(f, 'rb'))
                except (OSError, ValueError):
                    continue
                for e in t.get('edit') or []:
                    if isinstance(e, dict) and e.get('moves') and isinstance(e.get('target'), str):
                        par_code[e['target']] = e['moves']
                    for c in (e.get('cards') or []) if isinstance(e, dict) else []:
                        if isinstance(c, dict) and c.get('moves') and isinstance(c.get('id'), int):
                            par_carte[c['id'] & 0xFFFFFFFF] = c['moves']
            _MODS[m] = (par_code, par_carte)
        par_code, par_carte = _MODS[m]
        L = par_carte.get(id_carte) or par_code.get(code_perso)
        if L:
            trouve = ([{'move': int(x['move']) & 0xFFFFFFFF, 'level': int(x.get('level') or 1)} for x in L if isinstance(x, dict) and 'move' in x], m)
    return trouve


# ------------------------------------------------------------------ (15/11/2026) l'esprit dans la cinématique de sa technique
# LU :
# - la cinématique d'une technique d'esprit ne charge pas l'esprit par son code : c'est l'esprit invoqué pendant le match
#   (<ASSIGN>, Mukuro) ; ses animations sont les paquets common/event/<evNN>/<scène>/<scène>_<code esprit>_*.g4pk.
#   83 techniques en ont, chacune pour UN seul esprit (le sien) ; « Choc de la vouivre » (ev60_00830) n'en a pas.
# - [[event_env]] tag_words = { <esprit> = "<autre>" } : l'esprit prend les animations de l'autre dans cette scène
#   (Mukuro, ev81_00030 : Michael k002090 -> Reine sorcière k000220, « ses 55 os animés existent tous dans le squelette »).
# - os : crc32 des noms ; squelette = G4SK du .g4pkm de l'esprit ; os animés = cibles des G4MT de ses paquets.
#   La cible 0x8207F2B1 (2181537457) est dans TOUS les paquets d'esprit et n'est pas un os : écartée.
# - scène copiée par VRFW (MesTechniques, « id » neuf) : « <ASSIGN> … its packs cannot be copied, it is hidden » et
#   « ships no packs of the assigned model(s) … hidden there » : le mod doit livrer <id>_<esprit>_*.g4pk et `assigned`
#   (Mukuro : ev60_88200_k002090_*, nom de la scène et crc32 du nom de section changés, assigned = ["k002090"]).
CIBLE_COMMUNE = 2181537457
# (22/11, Frappe du loup) les TOTEMS aussi (a000020 = loup) : avant, seuls les esprits (k…) étaient vus dans une scène
RE_ESPRIT = re.compile(r'_([ak]\d{6})_s\d\d_p\d\d_c\d+\.g4pk$')


def dossier_scene(ev):
    """ev63_01170_1 -> ev63_01170 (les deux parties partagent le dossier d'animation)"""
    return ev[:10] if re.fullmatch(r'ev\d\d_\d{5}(_\d)?', ev) else ev


def esprits_de_scene(data_dir, ev):
    d = dossier_scene(ev)
    return sorted({m.group(1) for f in glob.glob(os.path.join(data_dir, 'common', 'event', d[:4], d, '%s_[ak]*.g4pk' % d))
                   for m in [RE_ESPRIT.search(os.path.basename(f))] if m})


def os_squelette(data_dir, code):
    from . import anim
    for f in glob.glob(os.path.join(data_dir, 'common', 'chr', '*', code, code + '.g4pkm')):
        p = anim.lire_paquet(f)
        if 'squelette' in p:
            return {o['crc'] for o in p['squelette']}
    return set()


_OS_ANIMES = {}


def os_animes(data_dir, ev, code):
    """(23/11) gardé en mémoire : l'invocation d'une copie d'esprit lit tous les esprits d'une scène"""
    cle = (data_dir, ev, code)
    if cle not in _OS_ANIMES:
        _OS_ANIMES[cle] = _os_animes(data_dir, ev, code)
    return set(_OS_ANIMES[cle])


def _os_animes(data_dir, ev, code):
    from . import anim
    d, s = dossier_scene(ev), set()
    for f in glob.glob(os.path.join(data_dir, 'common', 'event', d[:4], d, '%s_%s_*.g4pk' % (d, code))):
        for c in (anim.lire_paquet(f).get('G4MT') or {}).get('clips', []):
            s |= {ci['crc'] for ci in c['cibles']}
    return s - {CIBLE_COMMUNE}


def techniques_d_esprit(data_dir, cache_dir):
    """{code de technique: (dossier de scène, esprit animé)} pour les techniques dont la cinématique a un esprit"""
    f = os.path.join(cache_dir, 'index_techniques_esprit_2.json')      # (22/11) _2 : totems compris
    if os.path.exists(f):
        return json.load(open(f, encoding='utf-8'))
    from .techniques import construire_index
    out = {}
    for t in construire_index(data_dir, cache_dir):
        ks = esprits_de_scene(data_dir, t['cinematique'])
        if ks:
            out[t['code']] = [dossier_scene(t['cinematique']), ks[0]]
    json.dump(out, open(f, 'w', encoding='utf-8'), ensure_ascii=False, indent=0)
    return out


def compatibles(data_dir, cache_dir, esprit):
    """{code de technique: True / False} : tous les os animés de son esprit existent dans le squelette de « esprit »"""
    f = os.path.join(cache_dir, 'compat_esprits_2.json')               # (22/11) _2 : totems compris
    tout = json.load(open(f, encoding='utf-8')) if os.path.exists(f) else {}
    if esprit not in tout:
        sq = os_squelette(data_dir, esprit)
        tout[esprit] = {code: bool(sq) and (k == esprit or not (os_animes(data_dir, d, k) - sq))
                        for code, (d, k) in techniques_d_esprit(data_dir, cache_dir).items()}
        json.dump(tout, open(f, 'w', encoding='utf-8'), ensure_ascii=False)
    return tout[esprit]


def scene_de_technique(cfg, cache_dir, code):
    """technique (code du jeu ou clé de MesTechniques) -> {base: code du jeu, scenes: [noms d'évènements], dossier, copie: id neuf | None}"""
    from .techniques import construire_index
    idx = {t['code']: t for t in construire_index(cfg['data_dir'], cache_dir)}
    copie = None
    if code not in idx:
        f = os.path.join(cfg['outil_dir'], 'sortie', 'MesTechniques', 'outil_techniques.json')
        mes = json.load(open(f, encoding='utf-8')) if os.path.exists(f) else {}
        e = next((v for v in mes.values() if v['key'] == code), None)
        if not e or e.get('base') not in idx:
            return None
        copie, code = e['id'], e['base']
    t = idx[code]
    scenes = [copie] if copie else [t['cinematique']] + ([t['cinematique_2']] if t.get('cinematique_2') else [])
    return {'base': code, 'scenes': scenes, 'dossier': dossier_scene(t['cinematique']), 'copie': copie}


def plan_esprit(cfg, cache_dir, anc, technique):
    """comment la copie de l'esprit « anc » apparaît dans la cinématique de « technique » :
    {etat: sans_esprit | propre | emprunt | incompatible, esprit (dont les animations servent), scenes, copie}"""
    s = scene_de_technique(cfg, cache_dir, technique)
    if not s:
        return {'etat': 'inconnue'}
    te = techniques_d_esprit(cfg['data_dir'], cache_dir).get(s['base'])
    if not te:
        return dict(s, etat='sans_esprit')
    k = te[1]
    if k == anc:
        return dict(s, etat='propre', esprit=k)
    ok = compatibles(cfg['data_dir'], cache_dir, anc).get(s['base'])
    return dict(s, etat='emprunt' if ok else 'incompatible', esprit=k)


# ------------------------------------------------------------------ (15/11/2026) fiches des techniques (tableau des compétences)
# LU : skill_config, à partir du crc32 du code (position i) : +40 = u16 puissance min | u16 puissance max, +44 octet faible =
# élément (1 Air, 2 Forêt, 3 Feu, 4 Montagne, 5 Néant), +52 = flottant tension (« 90T »). Vérifié : Tir solaire whs00900 =
# 85 / 540, 90 dans le jeu de base ; HissatsuReforged (hissatsu_overhaul_power.toml) le met à power_min 90 / power_max 580 et
# tp 90 = les « 580 » et « 90T » de la capture du tableau des compétences. 927 techniques : valeurs toutes cohérentes.
ELEMENT = {1: 'Air', 2: 'Forêt', 3: 'Feu', 4: 'Montagne', 5: 'Néant'}


def stats(data_dir, cache_dir):
    """{code: [puissance min, puissance max, coût PT, élément, 0, recharge (s), type d'évolution]} du jeu de base ;
    esprits : {code: [0, 0, 0, 0, modèle crc]}
    CORRIGÉ 25/11 (colonnes LUES par leur nom dans la table RDBN, stats._rdbn_lignes) : le flottant +52 lu avant comme
    « tension » est `recastTime` (recharge en secondes, 60 / 70 / 90) ; le coût PT est `consumeTp` (octet +49, 40-120) ;
    `growthType` (octet +47, 0-7) = type d'évolution (soccer_common GetSkillEvoCode : 1-3 God, 4-6 Infinity, 7 GO, 0 aucun)"""
    f = os.path.join(cache_dir, 'index_coups_stats_v2.json')
    if os.path.exists(f):
        return json.load(open(f, encoding='utf-8'))
    S = os.path.join(data_dir, 'common', 'gamedata', 'skill')
    sc = open(_dernier(os.path.join(S, 'skill_config_*.cfg.bin')), 'rb').read()
    from .stats import _rdbn_lignes
    T = _rdbn_lignes(sc, 'm_skillInfoList', ['skillID', 'power_min', 'power_max', 'consumeTp', 'element', 'recastTime', 'growthType'])
    out = {}
    for x in catalogue(data_dir, cache_dir):
        if x['code'][:2] in ('wh', 'rh'):
            r = T.get(x['id'])
            if r:
                rc = struct.unpack('<f', struct.pack('<I', r['recastTime'] & 0xFFFFFFFF))[0]
                out[x['code']] = [r['power_min'], r['power_max'], r['consumeTp'], r['element'], 0, round(rc, 1), r['growthType']]
    for k, v in cfgbin.lire(open(_dernier(os.path.join(S, 'aura_skill_config_*.cfg.bin')), 'rb').read()):
        if len(v) > 7 and isinstance(v[1], str) and isinstance(v[7], int):
            out.setdefault(v[1], [0, 0, 0, 0, v[7] & 0xFFFFFFFF])      # colonne 7 = crc32(code du modèle de l'esprit)
    json.dump(out, open(f, 'w', encoding='utf-8'))
    return out


def stats_mods(cfg):
    """changements des mods activés ([[edit]] target = code, power_min / power_max / tp, VRFW.technique/3), dans l'ordre de
    enabled.toml (le dernier gagne). DÉDUIT : les options des mods (if_mod = « power_changes ») sont prises comme activées."""
    import tomllib
    mods = os.path.join(cfg['jeu_dir'], 'mods')
    from .mods_jeu import actifs_ordonnes         # (22/11, 2.0.4) sans enabled.toml : tous les mods sont actifs
    actifs = actifs_ordonnes(mods)
    out = {}
    for m in actifs:
        for f in sorted(glob.glob(os.path.join(mods, m, 'content', 'techniques', '**', '*.toml'), recursive=True)):
            try:
                t = open(f, encoding='utf-8').read()
                if 'power_m' not in t and 'tp =' not in t and 'recast' not in t and 'growth' not in t:
                    continue
                d = tomllib.loads(t)
            except (OSError, ValueError):
                continue
            for e in d.get('edit') or []:
                if isinstance(e, dict) and isinstance(e.get('target'), str):
                    for cle, n in (('power_min', 0), ('power_max', 1), ('tp', 2), ('recast', 5), ('growth', 6)):   # (25/11) + recharge, évolution
                        if isinstance(e.get(cle), (int, float)):
                            out.setdefault(e['target'], {})[n] = e[cle]
    return out


def fiches(cfg, cache_dir, mes=()):
    """{code: [puissance max, coût PT, élément, modèle d'esprit, recharge (s), type d'évolution 0-7]} avec les mods ;
    mes techniques = celles de leur base. (25/11) [1] = coût PT `consumeTp` (avant : la recharge, lue par erreur)"""
    base, M = stats(cfg['data_dir'], cache_dir), stats_mods(cfg)
    out = {}
    for code, v in base.items():
        v = list(v) + [0] * (7 - len(v))
        for n, x in M.get(code, {}).items():
            v[n] = x
        out[code] = [v[1], v[2], v[3], v[4], v[5], v[6]]
    for x in mes:
        if x.get('base') in out and x['code'] not in out:
            out[x['code']] = out[x['base']]
    return out
