"""(27/11/2026, muku : « synergie marche avec une certaine condition dans le jeu et dans l'Atelier je ne crois pas que la modif
marche ») SYNERGIES : effets et conditions, pour CRÉER une vraie nouvelle synergie (recherche complète : side-session-notes,
recherche_synergies.md).

LU (jeu, VRFW, CharacterReforged « Chessboard ») : UN code relie tout — objet `icon_key = <code>` + `key_id = true` (id de
l'objet = crc32(code) ; VRFW met `linked` = cet id, et le jeu lit `linked` pour trouver le drapeau), ligne `[[add]] key = <code>`
de la table `skill/synergy_flag` (effets REF_EFFECT {effect, value, flag_9}, conditions REF_EXEC_COND {chara}), image 56 × 56
nommée <code> de la planche 30_icon_synergy/icon_synergy.g4tx (SpriteRedirect). Offensive = codes « sf » (sub_category 221),
défensive = « sp » (222) : la base choisit.
- effet = id d'un des 30 blocs de soccer/synergy_flag_effect_config (texte : GRAND_TOTAL_INFO [texte] -> skill_text NOUN_INFO) ;
  value = % affiché (le jeu : 1 à 10) ; flag_9 = 1 ligne principale (2 au plus), 0 ligne secondaire (1).
- condition du jeu = « tel personnage est titulaire (ou du staff) » : chara = crc32 de la clé chara_base (signé), 8 au plus, toutes
  obligatoires ; le panneau du jeu n'en montre que 3.
"""
import os, re, glob, zlib
from .maillots.cfgbin import parse

INVALID = -992181094                          # crc32("INVALID") : paramètres vides
COND_PERSO = -1462442246                      # cond_type « personnage dans l'équipe » (le seul que le jeu connaît)
EFFETS_ESSAI = {-1537728588, 1028738574, 1247182488, -734860485}    # effets d'essai du jeu (taux de chute, brèche)
_CACHE = {}


def _signe(n):
    n &= 0xFFFFFFFF
    return n - (1 << 32) if n >= 1 << 31 else n


def _dernier(motif):
    l = sorted(glob.glob(motif))
    return l[-1] if l else None


def _vrfw(rel):
    """fichier tel que VRFW l'a construit (jeu + mods), sinon None"""
    return _dernier(os.path.join(os.environ.get('LOCALAPPDATA', ''), 'VRFW', 'cache', 'VRFW', 'types', '*', 'data', *rel.split('/')))


def _propre(t):
    t = re.sub(r'<VALUE>', 'X', str(t))
    t = re.sub(r'<[^>]*>|\[C\]', '', t).replace('\\n', ' ').replace('\n', ' ')
    return re.sub(r'\s+', ' ', t).strip()


def catalogue_effets(data_dir):
    """-> [{'id': effet, 'textes': {fr, en, es}, 'essai': bool}] (les 30 effets de synergie du jeu)"""
    if 'effets' in _CACHE:
        return _CACHE['effets']
    f = _dernier(os.path.join(data_dir, 'common', 'gamedata', 'soccer', 'synergy_flag_effect_config_*.cfg.bin'))
    blocs, cur = [], None
    for k, v in parse(f):
        if k == 'SYNERGY_FLAG_EFFECT_INFO' and v:
            cur = {'id': _signe(v[0]), 'texte': None}; blocs.append(cur)
        elif k == 'SYNERGY_FLAG_EFFECT_INFO_GRAND_TOTAL_INFO' and cur and v:
            cur['texte'] = v[0] & 0xFFFFFFFF
    textes = {}
    for lg in ('fr', 'en', 'es'):
        t = {}
        f = os.path.join(data_dir, 'common', 'text', lg, 'skill_text.cfg.bin')
        if os.path.exists(f):
            for k, v in parse(f):
                if k == 'NOUN_INFO' and len(v) > 5 and isinstance(v[0], int) and isinstance(v[5], str):
                    t.setdefault(v[0] & 0xFFFFFFFF, v[5])
        textes[lg] = t
    out = [{'id': b['id'], 'essai': b['id'] in EFFETS_ESSAI,
            'textes': {lg: _propre(textes[lg].get(b['texte']) or '') or str(b['id']) for lg in ('fr', 'en', 'es')}} for b in blocs]
    _CACHE['effets'] = out
    return out


def drapeaux(data_dir):
    """-> {id du drapeau (signé): {'effets': [[effet, valeur, flag_9]], 'conditions': [chara (signé)]}} tels qu'en jeu (table
    construite par VRFW, sinon le jeu)"""
    if 'drapeaux' in _CACHE:
        return _CACHE['drapeaux']
    f = _vrfw('common/gamedata/skill/synergy_flag_config_*.cfg.bin') or _dernier(os.path.join(data_dir, 'common', 'gamedata', 'skill', 'synergy_flag_config_*.cfg.bin'))
    infos, effets, conds, cur = [], [], [], None
    for k, v in parse(f):
        if k == 'SYNERGY_FLAG_INFO' and v:
            cur = {'id': _signe(v[0])}; infos.append(cur)
        elif k == 'SYNERGY_FLAG_INFO_REF_EFFECT' and cur:
            cur['e'] = v[:2]
        elif k == 'SYNERGY_FLAG_INFO_REF_EXEC_COND' and cur:
            cur['c'] = v[:2]
        elif k == 'SYNERGY_FLAG_EFFECT':
            effets.append([_signe(v[0]), int(v[1]), int(v[9]) if len(v) > 9 else 1])
        elif k == 'SYNERGY_FLAG_EXEC_COND':
            conds.append(_signe(v[1]))
    out = {}
    for x in infos:
        e0, ne = (x.get('e') or [0, 0]); c0, nc = (x.get('c') or [0, 0])
        out[x['id']] = {'effets': effets[e0:e0 + ne], 'conditions': conds[c0:c0 + nc]}
    _CACHE['drapeaux'] = out
    return out


def joueurs(data_dir, langue='fr'):
    """-> [{'id': crc32 signé de la clé chara_base, 'code': clé, 'nom': nom}] (personnages nommés, pour les conditions)"""
    cle = 'joueurs_' + langue
    if cle in _CACHE:
        return _CACHE[cle]
    noms = {}
    f = os.path.join(data_dir, 'common', 'text', langue if langue in ('fr', 'en', 'es') else 'fr', 'chara_text.cfg.bin')
    for k, v in parse(f):
        if len(v) > 5 and isinstance(v[0], int) and v[1] == 0 and isinstance(v[5], str):
            noms.setdefault(v[0] & 0xFFFFFFFF, v[5])
    out, vus = [], set()
    for k, v in parse(_dernier(os.path.join(data_dir, 'common', 'gamedata', 'character', 'chara_base_*.cfg.bin'))):
        if k != 'CHARA_BASE_INFO' or len(v) < 4 or not isinstance(v[1], str) or not v[1].startswith('c'):
            continue
        n = noms.get(v[3] & 0xFFFFFFFF) if isinstance(v[3], int) else None
        if not n or re.search(r'[぀-ヿ一-鿿]', n) or v[1] in vus:
            continue
        vus.add(v[1])
        out.append({'id': _signe(zlib.crc32(v[1].encode())), 'code': v[1], 'nom': re.sub(r'\s*\[\$[^\]]*\]', '', n)})
    _CACHE[cle] = out
    return out


def cle_libre(prefixe, pris):
    """nouvelle clé de synergie (sf19001… offensives, sp19001… défensives) : libre dans le jeu, les mods et mes copies.
    Pris : jeu sf01001…sf10001 / sp01001…sp09003, CharacterReforged sf11… / sp11…"""
    for n in range(19001, 99999):
        c = '%s%05d' % (prefixe, n)
        if c not in pris and _signe(zlib.crc32(c.encode())) not in pris:
            return c
    raise ValueError('plus de clé de synergie libre')
