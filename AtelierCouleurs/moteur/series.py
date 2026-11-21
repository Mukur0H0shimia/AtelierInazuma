"""(17/11/2026) SÉRIE de chaque élément de l'Atelier (filtres IE1 … Victory Road, demande de muku).

Règles LUES dans les tables du jeu (common/gamedata/character et skill) :
- tête : dossier chr/_face/<série>/ (01_IE1, 02_IE2, 03_IE3, 04_GO1, 05_GO2, 06_GO3, 07_ARES, 08_ORION, 11_VICTORY) ;
- chara_model : v[0] = id du modèle, v[10] = chemin de la tête ; chara_base : v[0] = id du personnage, v[6] = id du modèle ;
- chara_param (cartes) : v[1] = id du personnage (6161 cartes sur 6176), colonnes 11 à 28 = [technique (crc32 du code), niveau] ;
- aura_skill_config : v[1] = code de la technique d'esprit / d'armure / de totem, v[7] = crc32(code du modèle).
DÉDUIT : une technique, un esprit, un totem ou une armure est « de la série » des personnages dont une carte les a.
Un élément peut avoir plusieurs séries (ex. une technique apprise par des joueurs d'IE1 et de GO 1).
"""
import os, glob, json, zlib
from . import cfgbin
from .personnages import _dernier

SERIES = {'01_IE1': 'IE1', '02_IE2': 'IE2', '03_IE3': 'IE3', '04_GO1': 'GO 1', '05_GO2': 'GO 2', '06_GO3': 'GO 3',
          '07_ARES': 'Ares', '08_ORION': 'Orion', '11_VICTORY': 'Victory Road'}
ORDRE = list(SERIES.values())


def de_tete(chemin):
    """série d'un chemin de tête (« _face/01_IE1/c…/c….g4md » ou « chr/_face/… »)"""
    p = chemin.replace('\\', '/').split('/')
    if '_face' in p and p.index('_face') + 1 < len(p):
        return SERIES.get(p[p.index('_face') + 1])
    return None


def construire(data_dir, cache_dir):
    """{'perso': {id: série}, 'coup': {code: [séries]}, 'modele': {crc32(code du modèle): [séries]}} (en cache)"""
    f = os.path.join(cache_dir, 'index_series.json')
    if os.path.exists(f):
        return json.load(open(f, encoding='utf-8'))
    C = os.path.join(data_dir, 'common', 'gamedata', 'character')
    S = os.path.join(data_dir, 'common', 'gamedata', 'skill')
    modele_serie = {}
    for fm in sorted(glob.glob(os.path.join(C, 'chara_model_1*.cfg.bin'))):
        for k, v in cfgbin.lire(open(fm, 'rb').read()):
            if len(v) > 10 and isinstance(v[0], int) and isinstance(v[10], str):
                s = de_tete(v[10])
                if s:
                    modele_serie.setdefault(v[0] & 0xFFFFFFFF, s)
    perso = {}
    for k, v in cfgbin.lire(open(_dernier(os.path.join(C, 'chara_base_*.cfg.bin')), 'rb').read()):
        if len(v) > 6 and isinstance(v[0], int) and isinstance(v[6], int):
            s = modele_serie.get(v[6] & 0xFFFFFFFF)
            if s:
                perso[v[0] & 0xFFFFFFFF] = s
    par_crc = {}                                        # crc32(code de technique) -> séries
    for k, v in cfgbin.lire(open(_dernier(os.path.join(C, 'chara_param_1*.cfg.bin')), 'rb').read()):
        if len(v) > 28 and isinstance(v[1], int):
            s = perso.get(v[1] & 0xFFFFFFFF)
            if not s:
                continue
            for i in range(11, 29, 2):
                if isinstance(v[i], int) and v[i]:
                    par_crc.setdefault(v[i] & 0xFFFFFFFF, set()).add(s)
    coup, modele = {}, {}
    from .coups import catalogue
    for x in catalogue(data_dir, cache_dir):
        s = par_crc.get(x['id'])
        if s:
            coup[x['code']] = sorted(s, key=ORDRE.index)
    for k, v in cfgbin.lire(open(_dernier(os.path.join(S, 'aura_skill_config_*.cfg.bin')), 'rb').read()):
        if len(v) > 7 and isinstance(v[1], str) and isinstance(v[7], int):
            s = par_crc.get(zlib.crc32(v[1].encode()))
            if s:
                modele.setdefault(str(v[7] & 0xFFFFFFFF), set()).update(s)
    # tenues : texture « _uniform/<dossier>/<fichier>.g4tx » -> séries des modèles qui la portent (mêmes tables que
    # copies_tenues.noms_par_texture : chara_parts, chara_model colonnes des vêtements ; la tête du MÊME modèle donne la série)
    tex = {}
    try:
        from .copies_tenues import _parties, GENRES
        P = _parties(data_dir)
        cols = {'clothes': (1, 4, 7, 9), 'shoes': (1,), 'gloves': (1,)}
        tex_de = {}
        for g, ms in P.items():
            for nom, lignes in ms.items():
                s = {r[i] for r in lignes for i in cols.get(g, ()) if len(r) > i and isinstance(r[i], str) and r[i].endswith('.g4tx')}
                if s:
                    tex_de[(g, zlib.crc32(nom.encode()))] = s
        for fm in sorted(glob.glob(os.path.join(C, 'chara_model_1*.cfg.bin'))):
            for k, v in cfgbin.lire(open(fm, 'rb').read()):
                if len(v) > 10 and isinstance(v[0], int) and isinstance(v[10], str):
                    s = de_tete(v[10])
                    if not s:
                        continue
                    for g, (G, col, p) in GENRES.items():
                        if len(v) > col and isinstance(v[col], int):
                            for t in tex_de.get((g, v[col] & 0xFFFFFFFF), ()):
                                tex.setdefault(t, set()).add(s)
    except Exception as ex:
        print('séries des tenues :', ex)
    out = {'perso': {str(k): s for k, s in perso.items()}, 'coup': coup,
           'modele': {k: sorted(s, key=ORDRE.index) for k, s in modele.items()},
           'tex': {k: sorted(s, key=ORDRE.index) for k, s in tex.items()}}
    json.dump(out, open(f, 'w', encoding='utf-8'), ensure_ascii=False)
    return out


def de_modele(index, code):
    """séries d'un esprit / totem / armure par le code de son modèle (k000010, ka000101…)"""
    return index['modele'].get(str(zlib.crc32(code.encode())), [])
