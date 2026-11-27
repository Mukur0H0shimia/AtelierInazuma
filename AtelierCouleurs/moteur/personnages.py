"""Liste des esprits guerriers (chr/_keshin/kNNNNNN) et des totems (chr/_waza/aNNNNNN) avec leur nom français.

Trouvé le 13/11/2026 :
- gamedata/character/chara_base_*.cfg.bin : une entrée par personnage [crc32(code), crc32(code), 0, id_du_nom, ...] ;
- text/fr/chara_text.cfg.bin : [id_du_nom, 0, ..., 'Nom', ...] (0 = nom complet) ;
- gamedata/skill/aura_skill_config_*.cfg.bin : [?, 'wso000010' (technique), id du nom (skill_text), ?, ?, ?, ?, crc32('a000010') (modèle), ...] ;
- les noms de chara_text sont souvent restés en japonais : on prend alors le nom de l'aura (skill_text : « Pégase », « Totem loup ») ;
- les totems s'invoquent dans la scène event/ev83/ev83_00010, les esprits dans ev80_000N0 / ev81_000N0.
"""
from moteur import langue as _langue  # noqa: E402  (FR / EN)
import os, glob, json, zlib
from . import cfgbin
from .techniques import _textes


def _japonais(t):
    return not t or any(ord(ch) > 0x2E80 for ch in t)


def _dernier(motif):
    f = sorted(glob.glob(motif))
    return f[-1] if f else None


def joueur(data_dir, code):
    """tête (chemin du .g4md) et corpulence (1-4) d'un personnage jouable, d'après chara_base -> chara_model
    (chara_model : [id du modèle, …, corpulence (col. 9), '_face/<série>/<code>/<code>.g4md' (col. 10), …])"""
    c = os.path.join(data_dir, 'common')
    crc = zlib.crc32(code.encode())
    id_modele = None
    for k, v in cfgbin.lire(open(_dernier(os.path.join(c, 'gamedata', 'character', 'chara_base_*.cfg.bin')), 'rb').read()):
        if len(v) > 6 and isinstance(v[0], int) and (v[0] & 0xFFFFFFFF) == crc:
            id_modele = v[6] & 0xFFFFFFFF
            break
    if id_modele is None:
        return None
    for k, v in cfgbin.lire(open(_dernier(os.path.join(c, 'gamedata', 'character', 'chara_model_1*.cfg.bin')), 'rb').read()):
        if len(v) > 10 and isinstance(v[0], int) and (v[0] & 0xFFFFFFFF) == id_modele and isinstance(v[10], str):
            lu = _corps_lu(c, v[4])
            corps = lu[0] if lu else (v[9] if isinstance(v[9], int) and 1 <= v[9] <= 4 else 1)
            return {'tete': v[10], 'corps': corps, 'ligne': lu[1] if lu else None}
    return None


def _corps_lu(c, cle_corps):
    """(15/11/2026) corpulence LUE : chara_model [4] -> CHARA_BODY_INFO (même table) [1] = squelette
    '_common/c000<t>01/c000<t>01(_edit).objbin' -> t (1 normal, 2 petit, 3 grand, 4 costaud). Avant : colonne 9, qui vaut
    10 pour Harper Evans (c11260010, squelette c000201 : sa tête allait sur la poitrine du corps 1). None si squelette spécial.
    Renvoie (corps, ligne) : ligne = CHARA_BODY_INFO [4] = rang du vêtement (u0001<ligne + 1> : 01-02 normal 1,30 m,
    03-04 petit 0,96 m, 05 / 08 grand 1,55 m, 06-07 costaud 1,80 m — hauteurs MESURÉES dans les .g4mg)."""
    import re
    from .maillots.cfgbin import parse
    if not isinstance(cle_corps, int):
        return None
    f = _dernier(os.path.join(c, 'gamedata', 'character', 'chara_model_1*.cfg.bin'))
    if _CORPS.get('f') != f:                          # table lue une fois (la cinématique demande jusqu'à 40 personnages)
        _CORPS.clear(); _CORPS['f'] = f
        for k, v in parse(f):
            if k == 'CHARA_BODY_INFO' and len(v) > 1 and isinstance(v[0], int):
                m = re.search(r'c000([1-4])01', str(v[1]))
                _CORPS[v[0] & 0xFFFFFFFF] = (int(m.group(1)), v[4] if len(v) > 4 and isinstance(v[4], int) else None) if m else None
    return _CORPS.get(cle_corps & 0xFFFFFFFF)


_CORPS = {}


def utilisateurs(data_dir, technique, limite=40):
    """personnages qui ont cette technique (chara_param : [crc, code, …, crc des techniques…]) -> [{code, nom}]"""
    c = os.path.join(data_dir, 'common')
    t = zlib.crc32(technique.encode())
    noms = {}
    for crc, v in cfgbin.lire(open(os.path.join(c, 'text', _langue.code(), 'chara_text.cfg.bin'), 'rb').read()):
        if len(v) > 5 and isinstance(v[0], int) and v[1] == 0 and isinstance(v[5], str):
            noms.setdefault(v[0] & 0xFFFFFFFF, v[5])
    id_nom, code_de = {}, {}
    for crc, v in cfgbin.lire(open(_dernier(os.path.join(c, 'gamedata', 'character', 'chara_base_*.cfg.bin')), 'rb').read()):
        if len(v) > 3 and isinstance(v[0], int) and isinstance(v[1], str) and isinstance(v[3], int):
            id_nom.setdefault(v[1], v[3] & 0xFFFFFFFF)
            code_de.setdefault(v[0] & 0xFFFFFFFF, v[1])          # crc32(code) -> code
    out, vus = [], set()
    # chara_param : [crc de la ligne, crc32(code du personnage), …, crc32 des techniques…]
    for crc, v in cfgbin.lire(open(_dernier(os.path.join(c, 'gamedata', 'character', 'chara_param_1*.cfg.bin')), 'rb').read()):
        if len(v) < 2 or not isinstance(v[1], int):
            continue
        code = code_de.get(v[1] & 0xFFFFFFFF)
        if code and code not in vus and any(isinstance(x, int) and (x & 0xFFFFFFFF) == t for x in v):
            vus.add(code)
            nom = noms.get(id_nom.get(code))
            if nom and not _japonais(nom):
                out.append({'code': code, 'nom': nom})
            if len(out) >= limite:
                break
    return out


def _lire(f, abime):
    """(22/11, 2.0.1 : chez un joueur, chara_base illisible -> l'Atelier ne démarrait pas) fichier illisible (modifié par un
    autre outil de mod…) : ignoré, dit dans le journal ; les esprits restent listés, avec leur code si le nom manque"""
    try:
        return cfgbin.lire(open(f, 'rb').read())
    except Exception as ex:
        print('fichier du jeu illisible / unreadable game file : %s (%s)' % (f, ex))
        abime.append(f)
        return []


# (28/11) esprits spéciaux sans nom dans les tables du jeu (nom affiché dans l'Atelier ; vus dans l'Atelier)
NOMS_SPECIAUX = {c: 'Esprit spécial (%s)' % c for c in ('kx000010', 'me000010', 'mx000010')}


def construire(data_dir, cache_dir):
    f_cache = os.path.join(cache_dir, 'index_personnages_v3.json')     # (28/11) v3 : esprits spéciaux, noms complets
    if os.path.exists(f_cache):
        return json.load(open(f_cache, encoding='utf-8'))
    c = os.path.join(data_dir, 'common')
    noms = {}
    abime = []
    for crc, v in _lire(os.path.join(c, 'text', _langue.code(), 'chara_text.cfg.bin'), abime):
        if len(v) > 5 and isinstance(v[0], int) and v[1] == 0 and isinstance(v[5], str):
            noms.setdefault(v[0] & 0xFFFFFFFF, v[5])
    id_nom = {}
    base = _dernier(os.path.join(c, 'gamedata', 'character', 'chara_base_*.cfg.bin'))
    for crc, v in _lire(base, abime):
        if len(v) > 3 and isinstance(v[0], int) and isinstance(v[3], int):
            id_nom.setdefault(v[0] & 0xFFFFFFFF, v[3] & 0xFFFFFFFF)          # crc32 du code -> id du nom
    techniques, noms_aura = {}, {}
    aura = _dernier(os.path.join(c, 'gamedata', 'skill', 'aura_skill_config_*.cfg.bin'))
    for crc, v in _lire(aura, abime):
        if len(v) > 7 and isinstance(v[1], str) and isinstance(v[7], int):
            techniques.setdefault(v[7] & 0xFFFFFFFF, []).append(v[1])         # crc32 du modèle -> techniques
            if isinstance(v[2], int):
                noms_aura.setdefault(v[7] & 0xFFFFFFFF, v[2])                  # 3e champ = id du nom (skill_text)
    textes = _textes(data_dir, longs=True)          # (28/11) nom complet des esprits (« Éminent, le génie Majin »)
    liste = []
    for genre, dossier, prefixe in (('Esprit guerrier', '_keshin', 'k'), ('Totem', '_waza', 'a')):
        for code in sorted(os.listdir(os.path.join(c, 'chr', dossier))):
            # (28/11, retour d'un joueur : « l'esprit de Mark n'y est pas », c'est le Majin) esprits SPÉCIAUX du dossier _keshin
            # avec deux lettres (kx000010, mx000010, me000010) : avant, seuls « k » + chiffres étaient listés
            speciaux = dossier == '_keshin' and len(code) == 8 and code[:2].isalpha() and code[2:].isdigit()
            if not ((code.startswith(prefixe) and code[len(prefixe):].isdigit()) or speciaux):
                continue
            if not os.path.exists(os.path.join(c, 'chr', dossier, code, code + '.g4pkm')):
                continue
            crc = zlib.crc32(code.encode())
            nom = noms.get(id_nom.get(crc))
            if _japonais(nom):                     # beaucoup de noms d'esprits ne sont pas traduits dans chara_text
                nom = textes.get(noms_aura.get(crc)) or nom
            if not nom and code in NOMS_SPECIAUX:  # (28/11) sans nom dans les tables du jeu
                nom = NOMS_SPECIAUX[code]
            liste.append({'code': code, 'nom': nom or code, 'genre': genre, 'dossier': dossier,
                          'techniques': techniques.get(crc, [])})
    if not abime:                                  # liste incomplète (noms manquants) : pas gardée en cache
        json.dump(liste, open(f_cache, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    return liste
