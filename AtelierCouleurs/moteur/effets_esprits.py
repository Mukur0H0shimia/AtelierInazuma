"""(23/11/2026, muku : « un autre truc qu'on ne peut pas modifier sur les esprits guerriers… tout sauf compatible ») BONUS et
EFFET UNIQUE d'un esprit guerrier / totem / armure.

LU :
- gamedata/skill/aura_skill_config : après chaque AURA_CMD_INFO, AURA_CMD_INFO_REF_UNIQUE_EFFECT / _REF_EFFECT / _REF_CHARA
  = (début, nombre) dans les listes AURA_CMD_UNIQUE_EFFECT / AURA_CMD_EFFECT / AURA_CMD_CHARA ; ligne d'effet = [effet (crc32),
  param_1 … param_8] (INVALID = -992181094 = crc32("INVALID")).
- gamedata/soccer/soccer_command_effect_config : SC_COMMAND_EFFECT_INFO [effet, texte, n] + SC_COMMAND_EFFECT_INFO_EFFECT_DATA
  [type, valeur…] (+ moment, cible, conditions). Bonus (27 dans le jeu, cible 2 = le joueur) : types 411591308 ATT,
  -2122239178 DÉF, 717094926 Vitesse, 1523905665 puissance des techniques spéciales, -1008884421 recharge des techniques
  spéciales (noms LUS dans les textes de special_tactics_effect_config). Effets uniques : 112 dans le jeu, 40 avec un texte
  (skill_text NOUN_INFO, « Après une passe, puissance de lien de l'équipe +<VALUE> % »…).
- Le 1er paramètre d'une ligne de bonus n'est pas toujours la valeur de l'effet (Pégase ATT : 40 dans l'effet, 50 dans la
  ligne ; un ATT +30 a 30 / 60 / 80 / 800 selon l'esprit) : sens NON LU -> l'Atelier propose les lignes TELLES QUE LE JEU les
  écrit (effet + 1er paramètre le plus fréquent), jamais une valeur inventée.
- VRFW (LU, winmm.dll) : [[aura]] / [[aura_command]] `unique_effects` (remplace la liste), `effects`, `charas` = lignes brutes
  (9 valeurs) ; exemple AuraOverhaul : unique_effects = [[0x5A0BABC5, -992181094 ×8]].
Tables lues dans le cache de VRFW (jeu + mods activés : AuraOverhaul remplace l'effet unique de 103 esprits) s'il existe.
"""
import os, glob, zlib, collections

INVALIDE = -992181094
TYPES = {411591308: ('ATT', '+'), -2122239178: ('DÉF', '+'), 717094926: ('Vitesse', '+'),
         1523905665: ('Puissance des techniques spéciales', '+'), -1008884421: ('Recharge des techniques spéciales', '−')}
TYPES_LG = {'en': {411591308: 'ATK', -2122239178: 'DEF', 717094926: 'Speed', 1523905665: 'Special move power', -1008884421: 'Special move cooldown'},
            'es': {411591308: 'ATQ', -2122239178: 'DEF', 717094926: 'Velocidad', 1523905665: 'Poder de las supertécnicas', -1008884421: 'Recarga de las supertécnicas'}}


def _type(ty, langue):
    return (TYPES_LG.get(langue) or {}).get(ty) or TYPES[ty][0]
_NOMS = {zlib.crc32(n.encode()): n for n in (
    'AURA_CMD_INFO', 'AURA_CMD_INFO_REF_UNIQUE_EFFECT', 'AURA_CMD_INFO_REF_EFFECT', 'AURA_CMD_INFO_REF_CHARA',
    'AURA_CMD_UNIQUE_EFFECT', 'AURA_CMD_EFFECT', 'AURA_CMD_CHARA', 'SC_COMMAND_EFFECT_INFO', 'SC_COMMAND_EFFECT_INFO_EFFECT_DATA',
    'SC_COMMAND_EFFECT_INFO_TARGET_DATA', 'NOUN_INFO', 'TEXT_INFO')}


def _nom(k):
    from . import cfgbin
    if isinstance(k, str):
        return k
    return cfgbin.NOMS.get(k) or _NOMS.get(k & 0xFFFFFFFF) or k


def _s32(x):
    return x - (1 << 32) if isinstance(x, int) and x >= (1 << 31) else x


def _fichier(cfg, type_vrfw, *motif):
    """le fichier tel que VRFW le sert (cache : jeu + mods activés), sinon celui du jeu"""
    c = os.path.join(os.environ.get('LOCALAPPDATA', ''), 'VRFW', 'cache', 'VRFW', 'types', type_vrfw, 'data', *motif)
    f = sorted(glob.glob(c))
    if f:
        return f[-1], 'jeu + mods'
    f = sorted(glob.glob(os.path.join(cfg['data_dir'], *motif)))
    return (f[-1], 'jeu') if f else (None, None)


def _lire(f):
    from . import cfgbin
    return [(_nom(k), v) for k, v in cfgbin.lire(open(f, 'rb').read())]


_CACHE = {}


def textes(cfg, langue='fr'):
    cle = ('t', langue)
    if cle not in _CACHE:
        f, _ = _fichier(cfg, os.path.join('text', 'engine'), 'common', 'text', langue, 'skill_text.cfg.bin')
        T = {}
        for n, v in (_lire(f) if f else []):
            if n in ('NOUN_INFO', 'TEXT_INFO') and isinstance(v, list) and v and isinstance(v[0], int):
                t = next((x for x in v[1:] if isinstance(x, str) and x), None)
                if t:
                    T.setdefault(_s32(v[0]), t.replace('\\n', ' '))
        _CACHE[cle] = T
    return _CACHE[cle]


def definitions(cfg):
    """{effet: {'texte_id', 'donnees': [(type, valeur)], 'cible'}} (soccer_command_effect_config)"""
    if 'def' not in _CACHE:
        f, _ = _fichier(cfg, 'table', 'common', 'gamedata', 'soccer', 'soccer_command_effect_config_*.cfg.bin')
        D, cur = {}, None
        for n, v in (_lire(f) if f else []):
            if n == 'SC_COMMAND_EFFECT_INFO':
                cur = _s32(v[0]); D[cur] = {'texte_id': _s32(v[1]), 'donnees': [], 'cible': None}
            elif n == 'SC_COMMAND_EFFECT_INFO_EFFECT_DATA' and cur is not None:
                D[cur]['donnees'].append((_s32(v[0]), v[1] if v[1] != INVALIDE else None))
            elif n == 'SC_COMMAND_EFFECT_INFO_TARGET_DATA' and cur is not None:
                D[cur]['cible'] = v[0] if v else None
        _CACHE['def'] = D
    return _CACHE['def']


def table_esprits(cfg):
    """{clé de technique (wko00010…): {'unique': [lignes], 'bonus': [lignes], 'charas': [lignes]}} + listes du jeu"""
    if 'aura' in _CACHE:
        return _CACHE['aura']
    f, source = _fichier(cfg, 'technique', 'common', 'gamedata', 'skill', 'aura_skill_config_*.cfg.bin')
    L = _lire(f) if f else []
    listes = {'AURA_CMD_UNIQUE_EFFECT': [], 'AURA_CMD_EFFECT': [], 'AURA_CMD_CHARA': []}
    for n, v in L:
        if n in listes:
            listes[n].append([_s32(x) for x in v])
    out, cur = {}, None
    for n, v in L:
        if n == 'AURA_CMD_INFO' and len(v) > 1:
            cur = out.setdefault(v[1], {'unique': [], 'bonus': [], 'charas': []})
        elif cur is not None and n in ('AURA_CMD_INFO_REF_UNIQUE_EFFECT', 'AURA_CMD_INFO_REF_EFFECT', 'AURA_CMD_INFO_REF_CHARA'):
            d, nb = v[0], v[1]
            liste = {'AURA_CMD_INFO_REF_UNIQUE_EFFECT': 'AURA_CMD_UNIQUE_EFFECT', 'AURA_CMD_INFO_REF_EFFECT': 'AURA_CMD_EFFECT',
                     'AURA_CMD_INFO_REF_CHARA': 'AURA_CMD_CHARA'}[n]
            cle = {'AURA_CMD_UNIQUE_EFFECT': 'unique', 'AURA_CMD_EFFECT': 'bonus', 'AURA_CMD_CHARA': 'charas'}[liste]
            cur[cle] = listes[liste][d:d + nb]
    _CACHE['aura'] = (out, listes, source)
    return _CACHE['aura']


def libelle(cfg, effet, langue='fr'):
    D, T = definitions(cfg), textes(cfg, langue)
    d = D.get(effet) or {}
    t = T.get(d.get('texte_id'))
    dons = d.get('donnees') or []
    val = next((v for _, v in dons if v is not None), None)
    if t:
        return t.replace('<VALUE>', str(val) if val is not None else '?').replace('[CPASSIVE01]', '').replace('[CTACTICS01]', '').replace('[C]', '')
    parts = []
    for ty, v in dons:
        if ty in TYPES:
            nom, signe = _type(ty, langue), TYPES[ty][1]
            parts.append('%s %s%s %%' % (nom, signe, v if v is not None else '?'))
    return ', '.join(parts) or 'effet %08X' % (effet & 0xFFFFFFFF)


def catalogue(cfg, langue='fr'):
    """choix proposés : bonus et effets uniques tels que le jeu (et les mods) les écrivent"""
    out, listes, source = table_esprits(cfg)
    bonus = collections.defaultdict(collections.Counter)
    for r in listes['AURA_CMD_EFFECT']:
        bonus[r[0]][tuple(r[1:])] += 1
    uniques = collections.defaultdict(collections.Counter)
    for r in listes['AURA_CMD_UNIQUE_EFFECT']:
        uniques[r[0]][tuple(r[1:])] += 1
    D = definitions(cfg)
    B = [{'ligne': [e] + list(c.most_common(1)[0][0]), 'nom': libelle(cfg, e, langue), 'emplois': sum(c.values()),
          'type': next((_type(t, langue) for t, _ in (D.get(e) or {}).get('donnees', []) if t in TYPES), '')} for e, c in bonus.items()]
    U = [{'ligne': [e] + list(c.most_common(1)[0][0]), 'nom': libelle(cfg, e, langue), 'emplois': sum(c.values()),
          'texte': bool(textes(cfg, langue).get((D.get(e) or {}).get('texte_id')))} for e, c in uniques.items()]
    B.sort(key=lambda x: (x['type'], x['nom'])); U.sort(key=lambda x: (not x['texte'], -x['emplois']))
    return {'bonus': B, 'uniques': U, 'source': source}


def de_l_original(cfg, technique, langue='fr'):
    out, _, source = table_esprits(cfg)
    e = out.get(technique) or {'unique': [], 'bonus': [], 'charas': []}
    f = lambda L: [{'ligne': r, 'nom': libelle(cfg, r[0], langue)} for r in L]
    return {'bonus': f(e['bonus']), 'uniques': f(e['unique']), 'charas': len(e['charas']), 'source': source}


def lignes_toml(L):
    return '[%s]' % ', '.join('[%s]' % ', '.join(('0x%08X' % (x & 0xFFFFFFFF)) if i == 0 else str(int(x)) for i, x in enumerate(r)) for r in L)
