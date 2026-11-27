"""(15/11/2026) LES OBJETS DU JEU (inventaire : crampons, bracelets, accessoires, consommables, emblèmes, titres…) :
nom, description, icône ; l'icône se recolore dans l'Atelier ; COPIE = un nouvel objet (mod MesObjets), l'original ne change pas.

Lu (LU) :
- gamedata/item/item_config : une famille par type de ligne (ITEM_SHOES_INFO, ITEM_MISANGA_INFO…) ; la clé de l'objet = sa
  1re chaîne (« eq_sh110001 ») ; nom = 1er id trouvé dans text/fr/item_text NOUN_INFO ([id, 0, …, nom en colonne 5]),
  description = 1er id trouvé dans TEXT_INFO ([id, 0, texte]) ;
- icônes : dx11/menu/200_icon/02_icon_item/icon_itemNN.g4tx, une image par objet, NOMMÉE PAR SA CLÉ (eq_sh010101…) ;
- copie, écrite comme les mods qui marchent (CharacterReforged classic_items, MesMaillots) :
  [[item]] name / base = l'objet du jeu / category / icon_key / key_id = true / [item.text.<langue>] name, description ;
  catégories vues dans les mods selon la base : eq_sh -> shoes, eq_ac -> pendant, eq_mi -> bracelet ou gloves, ti -> title,
  em -> emblem, sf / sp -> synergy, abl_ -> consumable, ke -> key ;
  icône sur la planche du mod (VRFW.image/1) + [[VRFW.SpriteRedirect]] atlas = planche du jeu, own_atlas = la nôtre ;
  boutique : VRFW.shop/2 [[edit]] target = "InazumaFantasy.general_store", [[edit.entry]] item, price, currency.
- DÉDUIT : eq_mi « gants » (CharacterReforged range en gloves les eq_mi dont le nom dit « Gants ») -> gloves, sinon bracelet.
"""
from moteur import langue as _langue  # noqa: E402  (FR / EN)
import os, re, json, glob, zlib, datetime, base64, tomllib, shutil
from .g4 import images
from . import g4
from .maillots.cfgbin import parse
from .esprits import slug, cle_libre
from .export import _ecrire, _q

MOD_ID = 'MesObjets'
FAMILLES = {   # type de ligne -> (libellé, catégorie VRFW de la copie ou None)
    'ITEM_SHOES_INFO': ('Crampons', 'shoes'), 'ITEM_MISANGA_INFO': ('Bracelets et gants', 'bracelet'),
    'ITEM_ACCESSORY_INFO': ('Accessoires', 'pendant'), 'ITEM_SPECIAL_INFO': ('Objets spéciaux', None),
    'ITEM_CONSUME_INFO': ('Consommables', 'consumable'), 'ITEM_FORMATION_INFO': ('Formations', None),
    'ITEM_SPECIAL_TACTICS_INFO': ('Tactiques', None), 'ITEM_SUPER_TACTICS_INFO': ('Super tactiques', None),
    'ITEM_SYNERGY_FLAG_INFO': ('Synergies', 'synergy'), 'ITEM_TITLE_INFO': ('Titres', 'title'),
    'ITEM_COSTUME_INFO': ('Tenues (costumes)', None), 'ITEM_EMBLEM_INFO': ('Emblèmes', 'emblem'),
    'ITEM_CRAFT_OBJ_INFO': ('Objets de construction', None), 'ITEM_ANIMAL_INFO': ('Animaux', None),
    'ITEM_KIZUNA_LINK_INFO': ('Autocollants', None), 'ITEM_NAME_PLATE_INFO': ('Plaques nominatives', None),
    'ITEM_USER_TITLE_INFO': ('Titres de joueur', None), 'ITEM_PERFORMANCE_INFO': ('Célébrations', None),
    'ITEM_IMPORTANT_INFO': ('Objets importants', 'key'), 'ITEM_SELECT_BOX_INFO': ('Boîtes à choisir', None),
    'CHARA_SELECT_BOX_INFO': ('Boîtes à choisir (joueurs)', None)}
# (26/11, muku : « fais tous les menus », captures de la boutique) le jeu vend les équipements (crampons, bracelets, pendentifs,
# spéciaux) à la BOUTIQUE D'ENTRAÎNEMENT, comme CharacterReforged (addons/InazumaFantasy/content/shops/classic_items.toml :
# target = "InazumaFantasy.training_shop") ; le reste reste à la boutique générale
EQUIPEMENTS = {'ITEM_SHOES_INFO', 'ITEM_MISANGA_INFO', 'ITEM_ACCESSORY_INFO', 'ITEM_SPECIAL_INFO'}
# (27/11, essai de tous les types) le jeu montre aussi les SYNERGIES (drapeau) et les TACTIQUES SPÉCIALES (« T ») dans la barre
# de la Boutique d'entraînement, et CharacterReforged y vend ses synergies (addons/InazumaFantasy/content/shops/synergies.toml)
ENTRAINEMENT = EQUIPEMENTS | {'ITEM_SYNERGY_FLAG_INFO', 'ITEM_SPECIAL_TACTICS_INFO'}
_LIB_FAMILLE = {lib: k for k, (lib, _c) in FAMILLES.items()}


# ---------------------------------------------------------------------------------------------------- icônes
# (15/11/2026, suite) LU : l'icône d'un objet est nommée par sa clé (planches 02_icon_item), SINON la ligne de l'objet donne
# le crc32 du nom de son icône (colonne 14, parfois 0 ou 16 : crampons dérivés -> eq_sh010701, objets importants ->
# btl_re000003…). Les icônes sont dans tout menu/ : planches à plusieurs images (02_icon_item, 22_icon_town/icon_town,
# icon_animal, 20_icon_deco, 30_icon_synergy) ou un fichier par icône (01_icon_emblem/<clé>.g4tx, 25_icon_nameplate/…).
def _noms_g4tx(f):
    """noms des images d'un .g4tx, lus dans son en-tête seulement (comme images.G4TX : noms avec point s'il y en a assez)"""
    import struct
    from moteur import donnees_virtuelles as _dv
    t = _dv.debut(f, 0x30)
    if t[:4] != b'G4TX':
        raise ValueError(f)
    n = struct.unpack_from('<H', t, 0x20)[0]
    h = _dv.debut(f, os.path.getsize(f) - struct.unpack_from('<I', t, 0x2C)[0])
    noms = [m.group()[:-1].decode() for m in re.finditer(rb'[a-z][a-z0-9_.]{3,40}\x00', h)]
    if len(noms) >= n:
        return noms[-n:]
    return [m.group()[:-1].decode() for m in re.finditer(rb'[a-z][a-z0-9_]{3,40}\x00', h)][-n:]


def _images_menu(data_dir, cache_dir):
    """nom d'image -> (fichier relatif à dx11, n° de l'image, nb d'images du fichier) ; gardé en cache"""
    if os.path.basename(cache_dir) == _langue.code() and _langue.code() != 'fr':
        cache_dir = os.path.dirname(cache_dir)
    f_cache = os.path.join(cache_dir, 'index_images_menu.json')
    if os.path.exists(f_cache):
        return {k: tuple(v) for k, v in json.load(open(f_cache, encoding='utf-8')).items()}
    out = {}
    from concurrent.futures import ThreadPoolExecutor
    fichiers = sorted(glob.glob(os.path.join(data_dir, 'dx11', 'menu', '**', '*.g4tx'), recursive=True))

    def lire_noms(f):
        try:
            return _noms_g4tx(f)
        except Exception:
            return None
    with ThreadPoolExecutor(8) as pool:                  # plusieurs fichiers à la fois (lecture directe des paquets)
        tous = list(pool.map(lire_noms, fichiers))
    for f, noms in zip(fichiers, tous):
        rel = os.path.relpath(f, os.path.join(data_dir, 'dx11')).replace(os.sep, '/')
        if noms is None:
            continue
        for k, n in enumerate(noms):
            out.setdefault(n, (rel, k, len(noms)))
        out.setdefault(os.path.basename(f)[:-5], (rel, 0, len(noms)))
    json.dump(out, open(f_cache, 'w', encoding='utf-8'))
    return out


def construire(data_dir, cache_dir):
    f_cache = os.path.join(cache_dir, 'index_objets_jeu_v2.json')        # (27/11) v2 : + icônes des planches à zones
    if os.path.exists(f_cache):
        l = json.load(open(f_cache, encoding='utf-8'))
        if l and 'icone' in l[0]:
            return l
    c = os.path.join(data_dir, 'common')
    noms, textes = {}, {}
    for k, v in parse(os.path.join(c, 'text', _langue.code(), 'item_text.cfg.bin')):
        if not v or not isinstance(v[0], int):
            continue
        if k == 'NOUN_INFO' and len(v) > 5 and v[1] == 0 and isinstance(v[5], str):
            noms.setdefault(v[0] & 0xFFFFFFFF, v[5])
        elif k == 'TEXT_INFO' and len(v) > 2 and v[1] == 0 and isinstance(v[2], str):
            textes.setdefault(v[0] & 0xFFFFFFFF, v[2])
    im = dict(_images_menu(data_dir, cache_dir))
    from . import ui_jeu
    for pz in PLANCHES_A_ZONES:                  # (27/11) les zones de ces planches sont des icônes (sp08001, ds01001, icon_wht10010…)
        try:
            t_, zs, _g = ui_jeu.lire_planche(os.path.join(data_dir, 'dx11', *pz.split('/')))
            for nz, z in zs.items():
                if (z[3], z[4]) != tuple(t_[z[0]]) and z[3] <= 512:      # pas la planche entière
                    im.setdefault(nz, (pz, z[0], len(t_)))
        except Exception as ex:
            print('zones de', pz, ':', ex)
    crc_im = {zlib.crc32(n.encode()): n for n in im}
    ic = sorted(glob.glob(os.path.join(c, 'gamedata', 'item', 'item_config_*.cfg.bin')))[-1]
    out, vus = [], set()
    for k, v in parse(ic):
        if k not in FAMILLES or not v:
            continue
        cle = next((x for x in v if isinstance(x, str)), None)
        if not cle or cle in vus:
            continue
        vus.add(cle)
        ints = [x & 0xFFFFFFFF for x in v if isinstance(x, int)]
        nom = next((noms[x] for x in ints if x in noms), None)
        desc = next((textes[x] for x in ints if x in textes), '')
        lib, cat = FAMILLES[k]
        if k == 'ITEM_MISANGA_INFO' and nom and 'gant' in nom.lower():
            cat = 'gloves'                                       # DÉDUIT (voir l'en-tête)
        icone_nom = cle if cle in im else ('icon_w' + cle if 'icon_w' + cle in im else None)   # (27/11) tactiques : icon_wht… (pas le bandeau allemand)
        if not icone_nom:
            for col in (14, 0, 16):
                x = v[col] if len(v) > col else None
                if isinstance(x, int) and (x & 0xFFFFFFFF) in crc_im:
                    icone_nom = crc_im[x & 0xFFFFFFFF]; break
        i = im.get(icone_nom) if icone_nom else None
        out.append({'code': cle, 'nom': re.sub(r'\s*\[\$[^\]]*\]', '', nom) if nom else cle, 'genre': lib, 'famille': k,
                    'description': desc, 'categorie': cat, 'type': 'objet',
                    'icone': {'nom': icone_nom, 'fichier': i[0], 'image': i[1], 'nb': i[2]} if i else None})
    json.dump(out, open(f_cache, 'w', encoding='utf-8'), ensure_ascii=False, indent=0)
    return out


def icone(data_dir, cache_dir, e):
    """PNG de l'icône d'un objet : cache/icones_objets/<clé>.png ; renvoie (w, h) ou None (pas d'image dans le jeu)"""
    ic = e.get('icone')
    if not ic:
        return None
    d = os.path.join(cache_dir, 'icones_objets'); os.makedirs(d, exist_ok=True)
    f = os.path.join(d, re.sub(r'[^\w~.-]', '_', e['code']) + '.png')
    if os.path.exists(f):
        w, h, _ = images.lire_png(f); return w, h
    if ic.get('png'):                                   # (27/11) icône d'un mod en PNG (tenues d'Inazuma Fantasy…)
        if ic.get('box'):                               # case d'une planche [x0, y0, x1, y1]
            W_, H_, rows = images.lire_png(ic['png']); x0, y0, x1, y1 = [int(v) for v in ic['box']]
            images.ecrire_png(f, x1 - x0, y1 - y0, [bytearray(r[x0 * 4:x1 * 4]) for r in rows[y0:y1]]); return x1 - x0, y1 - y0
        shutil.copy(ic['png'], f); w, h, _ = images.lire_png(f); return w, h
    # (17/11/2026) objets des mods : icône sur une planche du mod (« abs » = chemin sur le disque)
    g = images.G4TX(open(ic['abs'] if ic.get('abs') else os.path.join(data_dir, 'dx11', *ic['fichier'].split('/')), 'rb').read())
    r = g4.decoder_texture(g.blocs[ic['image']])
    if not r:
        return None
    # (27/11, essai de tous les types) icône rangée comme une ZONE d'une planche (synergies : 42 icônes dans une seule image) : on
    # découpe la zone (avant : toute la planche, en boutique comme dans l'onglet Objets)
    if not ic.get('abs'):
        try:
            from . import ui_jeu
            _t, zones, _g = ui_jeu.lire_planche(os.path.join(data_dir, 'dx11', *ic['fichier'].split('/')))
            z = zones.get(ic['nom'])
            if z and z[0] == ic['image'] and (z[3], z[4]) != (r[0], r[1]) and z[3] > 0 and z[4] > 0:
                r = (z[3], z[4], [bytearray(row[z[1] * 4:(z[1] + z[3]) * 4]) for row in r[2][z[2]:z[2] + z[4]]])
        except Exception as ex:
            print('zone de l’icône :', ex)
    images.ecrire_png(f, *r)
    return r[0], r[1]


# (27/11, muku : « il faut régler des trucs dans la création directement », recherche_equipements.md) BONUS DES ÉQUIPEMENTS : la
# ligne ITEM_<famille>_INFO_REGULAR_UNIQUE_BASE qui SUIT la ligne de l'objet, colonnes 0-6 = kick control technique pressure
# physical intelligence agility (catalogue de colonnes de VRFW). Valeurs EN JEU = celles de la table que VRFW construit
# (%LOCALAPPDATA%\VRFW\cache\VRFW	ypes\item\…\item_config_*.cfg.bin : jeu + InazumaFantasy [edit.stats] + CharacterReforged
# [edit.scale_stats] fractions de S = le plus grand bonus, 70 aujourd'hui). Une copie écrit TOUJOURS [item.scale_stats] (7 clés,
# fraction = valeur / S), comme les 167 équipements neufs de CharacterReforged (classic_items.toml).
STATS = ('kick', 'control', 'technique', 'pressure', 'physical', 'intelligence', 'agility')
SYNERGIE = 'ITEM_SYNERGY_FLAG_INFO'
# (27/11, recherche_autres_objets.md) le jeu choisit la PLANCHE d'une icône par le PRÉFIXE de la clé (menu_icon_manage_config
# MENU_ICON_IDPREFIX) : « mo_… » n'en est pas un (icône introuvable) ; MesMaillots « uni_mm_… », vu en jeu, garde le préfixe « uni ».
PREFIXES_ICONES = ('test_tk', 'tk_si', 'tk_ki', 'tk_vi', 'tk_bb', 'tk_st', 'btl_re', 'eq_sh', 'eq_mi', 'eq_ac', 'eq_sp', 'perf', 'mini',
                   'abl', 'uni', 'cos', 'coi', 'coa', 'num', 'tk', 'tr', 'gd', 'ex', 'ke', 'ds')
# planches faites d'UNE texture découpée en zones : l'icône d'une copie y est une [[sprite]] (comme CharacterReforged), pas une [[texture]]
PLANCHES_A_ZONES = ('menu/200_icon/30_icon_synergy/icon_synergy.g4tx', 'menu/200_icon/20_icon_deco/icon_deco.g4tx', 'menu/200_icon/13_icon_tactics/icon_tactics.g4tx')
# familles qu'une copie simple ne fait PAS marcher (le jeu range leur contenu ailleurs, par id) ou qui ont leur propre outil
PAS_DE_COPIE = {
    'CHARA_SELECT_BOX_INFO': 'ce n’est pas un objet (contenu d’une boîte)', 'ITEM_SELECT_BOX_INFO': 'ce n’est pas un objet (contenu d’une boîte)',
    'ITEM_FORMATION_INFO': 'une formation se crée avec VRFW.formation (pas une copie d’objet)',
    'ITEM_COSTUME_INFO': 'une tenue se crée dans l’onglet Tenues (elle doit être portable : VRFW.Outfit)'}
BOITES = {'ex0005', 'ex0006', 'ex0007', 'ex0008', 'ex0009', 'ex0010', 'ex0011'}     # (27/11) boîtes : contenu copié (contenu_boites), sauf ex0010 refusée
SANS_DESCRIPTION = {'ITEM_TITLE_INFO', 'ITEM_EMBLEM_INFO', 'ITEM_NAME_PLATE_INFO', 'ITEM_KIZUNA_LINK_INFO', 'ITEM_PERFORMANCE_INFO', 'ITEM_USER_TITLE_INFO',
                    'ITEM_ANIMAL_INFO', SYNERGIE}


PREFIXE_FAMILLE = {'ITEM_SHOES_INFO': 'eq_sh', 'ITEM_MISANGA_INFO': 'eq_mi', 'ITEM_ACCESSORY_INFO': 'eq_ac', 'ITEM_SPECIAL_INFO': 'eq_sp',
                   'ITEM_COSTUME_INFO': 'cos', 'ITEM_CRAFT_OBJ_INFO': 'coi', 'ITEM_ANIMAL_INFO': 'coa', 'ITEM_KIZUNA_LINK_INFO': 'ds',
                   'ITEM_IMPORTANT_INFO': 'ke', 'ITEM_PERFORMANCE_INFO': 'perf'}
TACTIQUES = {'ITEM_SPECIAL_TACTICS_INFO', 'ITEM_SUPER_TACTICS_INFO'}    # icône = celle de la TACTIQUE liée (pas celle de l'objet)


def _prefixe(code, famille=None):
    """préfixe d'icône du jeu : celui de la clé de la base, sinon celui de sa famille (bases de mods : « cro_eq_mi… »)"""
    return next((p for p in PREFIXES_ICONES if str(code).startswith(p)), None) or PREFIXE_FAMILLE.get(famille)


def nom_icone(code_base, cle, pris, famille=None):
    """clé d'icône d'une copie : préfixe de la base + « _mo_ » + nom (31 caractères au plus, unique)"""
    p = _prefixe(code_base, famille) or 'mo'
    n = re.sub(r'[^a-z0-9_]', '_', ('%s_mo_%s' % (p, cle)).lower())[:31]
    k = 2
    while n in pris:
        n = ('%s_%d' % (n[:28], k)); k += 1
    return n


def icone_remplacable(e):
    """l'icône d'une copie peut-elle être la sienne (recolorée / dessinée) ?"""
    ic = e.get('icone')
    if not ic or e.get('famille') in TACTIQUES:
        return False
    return ic['nb'] > 1 or ic['fichier'] in PLANCHES_A_ZONES or os.path.dirname(ic['fichier']) in ('menu/200_icon/01_icon_emblem', 'menu/200_icon/25_icon_nameplate')


def refus_copie(e):
    """raison pour laquelle une copie simple de cet objet ne marcherait pas (None : elle marche)"""
    if e.get('famille') in PAS_DE_COPIE:
        return PAS_DE_COPIE[e['famille']]
    if e.get('code') == 'ex0010':
        return 'l’effet de la Graine Basara est écrit dans le jeu pour son numéro : une copie ne ferait rien'
    if e.get('famille') == 'ITEM_CONSUME_INFO' and str(e.get('code')).startswith('abl_'):
        # (27/11) HissatsuReforged (config.toml ranks.raise_item = "abl_000001") reconnaît l'objet par son numéro
        return 'son effet est donné selon son numéro (Amélioration de technique de HissatsuReforged) : une copie ne ferait rien'
    if e.get('famille') == 'ITEM_IMPORTANT_INFO':
        # (27/11) tickets de stade / de ville (gd…), photos et objets de quête (ke…) : le jeu les reconnaît par leur numéro
        return 'un objet important sert par son numéro (ticket de stade, photo, objet de quête) : une copie ne ferait rien'
    if str(e.get('code')).startswith(('spirit', 'test_')) or e.get('code') in ('sf01000010', 'sf01000020'):
        return 'objet interne du jeu'
    if e.get('famille') == 'ITEM_CONSUME_INFO' and not str(e.get('code')).startswith(('ex', 'abl_')):
        # (27/11, VU EN JEU par muku : la copie de Guts Gear n'apparaît pas) la boutique ne montre que les consommables de catégorie 10
        # (orbes, ex…, abl_… : les seuls vendus, LU dans la table construite) ; objets de match (70), trésors / monnaies (220), fèves
        # (210) : leur ligne de boutique existe mais ne s'affiche pas
        return 'la boutique du jeu ne montre pas ce genre d’objet (objets de match, trésors, fèves) : la copie n’y apparaîtrait pas'
    return None


_LIGNES = {}


# (27/11, demande de muku) PLAQUES NOMINATIVES. LU : l'image d'une plaque n'est pas trouvée par la clé de l'objet mais par sa ligne
# de gamedata/user_name_plate (RDBN m_userNamePlateInfoList ; VRFW : table « user_name_plate/user_name_plate », colonnes
# user_name_plate_id, texture_file_name_text = « #/menu/200_icon/25_icon_nameplate/nm00002.g4tx », texture_file_name_crc =
# crc32 de ce texte, main_texture_name_crc = crc32(« nm00002_01 »), shadow_texture_name_crc = crc32(« nm00002_02 »), flag_index
# (0 pour 195 plaques sur 260)…, crc vérifiés) ; l'objet la cite par sa colonne 16 linked (VRFW « item/item_name_plate », = son
# propre id dans le jeu). Copie : fichier neuf nm9xxxx.g4tx (_01 recoloré, _02 ombre gardée), ligne de plaque ajoutée (from =
# celle de l'original), linked de l'objet = le nouvel id (= crc32 de sa clé, key_id).
PLAQUE = 'ITEM_NAME_PLATE_INFO'


def _tables_plaques(reg):
    """(fichier user_name_plate, fichier item_name_plate) : lignes VRFW.table/1 des plaques copiées"""
    add, lk = [], []
    for cle, x in sorted(reg.items()):
        if _LIB_FAMILLE.get(x.get('genre')) != PLAQUE or x.get('mode_icone') != 'fichier' or not x.get('icone'):
            continue
        c = x['icone']; tx = '#/menu/200_icon/25_icon_nameplate/%s.g4tx' % c
        add += ['# %s (copie de %s)' % (x.get('nom'), x['base']), '[[add]]', 'key = 0x%08X' % zlib.crc32(c.encode()), 'from = 0x%08X' % zlib.crc32(x['base'].encode()),
                'cells = { texture_file_name_text = %s, texture_file_name_crc = 0x%08X, main_texture_name_crc = 0x%08X, shadow_texture_name_crc = 0x%08X, flag_index = 0 }'
                % (_q(tx), zlib.crc32(tx.encode()), zlib.crc32((c + '_01').encode()), zlib.crc32((c + '_02').encode())), '']
        lk += ['[[set]]', 'key = %s' % _q(c), 'cells = { linked = 0x%08X }' % zlib.crc32(c.encode()), '']
    return add, lk


# (27/11, muku : « vérifie que les boîtes marchent aussi ») BOÎTES. LU : leur contenu est rangé par le NUMÉRO de la boîte dans
# d'autres listes (VRFW, noms lus dans winmm.dll) : « item/item_chara_select_box » CHARA_SELECT_BOX_INFO [id, box_item] +
# REF_INFO_CHARA [chara_param, rank] (ex0005 : 8 personnages rang 4) ; « item/item_select_box » ITEM_SELECT_BOX_INFO [id, box_item]
# + REF_INFO_ITEM [item, count] (ex0011 : 3 objets) ; « item/item_emission_rarity_table_config » (RDBN) [item_id, table_info ->
# table_id, emit_rarity, weight] (Boîtes de victoire ex0006-9). Copie : la même ligne de contenu sous le numéro de la copie, par
# VRFW.base_table/1 [[keyed]] [[keyed.add]] (comme CharacterReforged item_config, HissatsuReforged win_treasure_lot_table).
_BOITES = {}


def contenu_boites(data_dir):
    """{clé de la boîte du jeu : (sorte, [lignes du contenu])} ; sorte = 'chara' | 'objet' | 'tirage'"""
    if not _BOITES:
        import struct, sys
        f = sorted(glob.glob(os.path.join(data_dir, 'common', 'gamedata', 'item', 'item_config_*.cfg.bin')))[-1]
        cles = {zlib.crc32(('ex%04d' % n).encode()): 'ex%04d' % n for n in range(1, 100)}
        enfants, sorte = [], None
        for k, v in parse(f):
            if k in ('CHARA_SELECT_BOX_INFO_CHARA', 'ITEM_SELECT_BOX_INFO_ITEM'):
                enfants.append([x & 0xFFFFFFFF if isinstance(x, int) and abs(x) > 99999 else x for x in v])
            elif k in ('CHARA_SELECT_BOX_INFO', 'ITEM_SELECT_BOX_INFO'):
                sorte = ('chara' if k.startswith('CHARA') else 'objet', cles.get(v[1] & 0xFFFFFFFF))
            elif k.endswith('_REF_INFO_CHARA') or k.endswith('_REF_INFO_ITEM'):
                if sorte and sorte[1]:
                    _BOITES[sorte[1]] = (sorte[0], enfants[v[0]:v[0] + v[1]])
            elif k.endswith('_LIST_END') and 'SELECT_BOX_INFO_' in k and not k.startswith(('CHARA_SELECT_BOX_INFO_LIST', 'ITEM_SELECT_BOX_INFO_LIST')):
                pass
            if k in ('CHARA_SELECT_BOX_INFO_CHARA_LIST_BEG', 'ITEM_SELECT_BOX_INFO_ITEM_LIST_BEG'):
                enfants = []
        from . import rdbn       # (28/11) copié dans moteur/ : avant, pris dans Chargeur/outils (absent chez les autres -> erreur)
        fe = sorted(glob.glob(os.path.join(data_dir, 'common', 'gamedata', 'item', 'item_emission_rarity_table_config_*.cfg.bin')))
        if fe:
            t = rdbn.Table(open(fe[-1], 'rb').read())
            noms = {zlib.crc32(x): x.decode() for x in t.noms.split(b'\0') if x}
            L = {noms.get(l['crc']): i for i, l in enumerate(t.listes)}

            def lire(nom):
                i = L[nom]; cols = [(noms.get(c), ta, pl) for c, ty, ta, pl in t.colonnes(i)]
                return [{n: int.from_bytes(r[pl:pl + ta], 'little') for n, ta, pl in cols} for r in t.listes[i]['lignes']]
            info = lire('m_itemEmissionRarityTableConfigInfoList')
            for r in lire('m_itemEmissionRarityTableConfigList'):
                c = cles.get(r['itemId'])
                if c:
                    st, n = r['tableInfo'] & 0xFFFF, r['tableInfo'] >> 16
                    _BOITES[c] = ('tirage', [(x['tableId'], x['emitRarity'], x['weight']) for x in info[st:st + n]])
        _BOITES['_'] = None
    return {k: v for k, v in _BOITES.items() if v}


def _tables_boites(data_dir, reg):
    """(lignes base_table item_config, lignes base_table item_emission_rarity_table_config) des boîtes copiées"""
    B = contenu_boites(data_dir)
    chara, objet, tirage = [], [], []
    for cle, x in sorted(reg.items()):
        b = B.get(x.get('base'))
        if not b:
            continue
        iid = zlib.crc32((x['icone'] if x.get('icone') else '%s.%s' % (MOD_ID, cle)).encode())
        rid = zlib.crc32(('%s.boite_%s' % (MOD_ID, cle)).encode())
        com = '  [[keyed.add]]                         # %s (copie de %s)' % (x.get('nom'), x['base'])
        if b[0] == 'chara':
            chara += [com, '  key = 0x%08X' % rid, '  cells = { box_item = 0x%08X, REF_INFO_CHARA = { set = [ %s ] } }'
                      % (iid, ', '.join('{ chara_param = 0x%08X, rank = %d }' % (c, r) for c, r in b[1]))]
        elif b[0] == 'objet':
            objet += [com, '  key = 0x%08X' % rid, '  cells = { box_item = 0x%08X, REF_INFO_ITEM = { set = [ %s ] } }'
                      % (iid, ', '.join('{ item = 0x%08X, count = %d }' % (i, n) for i, n in b[1]))]
        else:
            tirage += [com, '  key = 0x%08X' % iid, '  cells = { table_info = { set = [ %s ] } }'
                       % ', '.join('{ table_id = 0x%08X, emit_rarity = %d, weight = %d }' % t for t in b[1])]
    ic = (['[[keyed]]', 'table = "item/item_chara_select_box"'] + chara + [''] if chara else []) + \
         (['[[keyed]]', 'table = "item/item_select_box"'] + objet + [''] if objet else [])
    ie = ['[[keyed]]', 'table = "item/item_emission_rarity_table_config"'] + tirage + [''] if tirage else []
    return ic, ie


def unique(data_dir, code):
    """(27/11, VU EN JEU par muku : emblème, tactiques, synergies achetés plusieurs fois) objet qu'on n'a qu'une fois : le jeu
    lui met max_stack 1 (emblèmes, titres, tactiques, synergies, plaques, objets importants, célébrations…) et sa boutique ne le
    vend qu'une fois (SHOP_INFO_ITEM col 5 stock = 1, LU dans la table construite : em010001, ht10010, sf01001, nm00002 = 1,
    crampons = 0)"""
    v = ligne_objet(data_dir, code)
    return bool(v) and v[7] == 1


def ligne_objet(data_dir, code):
    """ligne item_config de l'objet telle qu'en jeu (table construite par VRFW, sinon le jeu)"""
    if not _LIGNES:
        l = sorted(glob.glob(os.path.join(os.environ.get('LOCALAPPDATA', ''), 'VRFW', 'cache', 'VRFW', 'types', 'item', 'data', 'common', 'gamedata', 'item', 'item_config_*.cfg.bin')))
        f = l[-1] if l else sorted(glob.glob(os.path.join(data_dir, 'common', 'gamedata', 'item', 'item_config_*.cfg.bin')))[-1]
        for k, v in parse(f):
            if k in FAMILLES and v and len(v) > 12 and isinstance(v[11], str):
                _LIGNES.setdefault(v[11], v)
        _LIGNES['_'] = True
    return _LIGNES.get(code)
PLANCHE_SYNERGIES = '#/menu/200_icon/30_icon_synergy/icon_synergy.g4tx'
_STATS_EQ = {}


def stats_equipement(data_dir):
    """-> ({clé d'objet: [7 bonus tels qu'en jeu]}, S)"""
    if _STATS_EQ:
        return _STATS_EQ['t'], _STATS_EQ['S']
    l = sorted(glob.glob(os.path.join(os.environ.get('LOCALAPPDATA', ''), 'VRFW', 'cache', 'VRFW', 'types', 'item', 'data', 'common', 'gamedata', 'item', 'item_config_*.cfg.bin')))
    f = l[-1] if l else sorted(glob.glob(os.path.join(data_dir, 'common', 'gamedata', 'item', 'item_config_*.cfg.bin')))[-1]
    t, prec = {}, None
    for k, v in parse(f):
        if k in EQUIPEMENTS and v:
            prec = next((x for x in v if isinstance(x, str)), None)
        elif k.endswith('_INFO_REGULAR_UNIQUE_BASE') and prec and v:
            t[prec] = [int(x) if isinstance(x, (int, float)) else 0 for x in v[:7]]; prec = None
        else:
            prec = None
    S = max([max(x) for x in t.values()] + [1]) if t else 70
    _STATS_EQ.update(t=t, S=S or 70)
    return t, _STATS_EQ['S']


def details(cfg, cache_dir, e):
    """comme un esprit, mais sans 3D : un « objet » qui n'a qu'une texture, son icône"""
    t = icone(cfg['data_dir'], cache_dir, e)
    tex = [{'nom': e['code'], 'lisible': bool(t), 'donnees': False, 'w': t[0] if t else 0, 'h': t[1] if t else 0}] if t else []
    o = {'acteur': e['code'], 'chemin': None, 'nom': 'icones_objets', 'role': 'icone', 'modeleActeur': True, 'pieces': [], 'textures': tex}
    plus = {}
    v = ligne_objet(cfg['data_dir'], e['code'])
    plus['commun'] = {'rarete': int(v[12]) if v and isinstance(v[12], int) else 1, 'max': int(v[7]) if v and isinstance(v[7], int) else 1,
                      'unique': unique(cfg['data_dir'], e['code']),
                      # (27/11, VU EN JEU par muku : fonds différents, « plusieurs types de titres ») la rareté n'a deux valeurs dans le
                      # jeu que pour les titres (1 = argenté, 2 = doré : 113 / 47) et les consommables (orbes) ; ailleurs toujours 1, et 2
                      # donne le fond brillant des objets rares : pas de choix
                      'choix_rarete': {'ITEM_TITLE_INFO': 'titre', 'ITEM_CONSUME_INFO': 'fond'}.get(e.get('famille')),
                      'description': e.get('famille') not in SANS_DESCRIPTION, 'refus': refus_copie(e), 'icone': icone_remplacable(e)}
    if e.get('famille') == SYNERGIE:             # (27/11) effets et conditions de la synergie d'origine, tels qu'en jeu
        from . import synergies
        d = synergies.drapeaux(cfg['data_dir']).get(synergies._signe(zlib.crc32(e['code'].encode()))) or {'effets': [], 'conditions': []}
        plus['synergie'] = dict(d, offensive=e['code'].startswith('sf'))
    if e.get('famille') in EQUIPEMENTS:          # (27/11) bonus de l'original, tels qu'en jeu (réglables dans la copie)
        t, S = stats_equipement(cfg['data_dir'])
        plus['equipement'] = {'stats': dict(zip(STATS, t.get(e['code'], [0] * 7))), 'S': S}
    return dict(e, objets_details=[o], auras=[], categorie='objets', **plus)


# ---------------------------------------------------------------------------------------------------- copie (TOUTES les familles)
# LU dans le code de VRFW (winmm.dll) : « give `base` (the game item it is cloned from) or `category` » : avec la base seule,
# VRFW prend la catégorie de l'objet copié ; catégories qu'il connaît : shoes gloves bracelet pendant accessory special
# consumable costume collectible name_plate craft synergy emblem title key kit currency. On écrit la catégorie quand un mod
# l'écrit pour cette famille (voir FAMILLES), sinon la base seule. « key_id needs icon_key » ; icon_key = nom de texture
# (a-z 0-9 _, 31 caractères au plus).
def _sortie(cfg):
    return os.path.join(cfg['outil_dir'], 'sortie', MOD_ID)


def registre(cfg):
    f = os.path.join(_sortie(cfg), 'outil_objets.json')
    return json.load(open(f, encoding='utf-8')) if os.path.exists(f) else {}


def _code_fichier(data_dir, ic, reg):
    """icône « un fichier par icône » (emblème, plaque…) : code neuf de même longueur, libre dans le jeu et dans mes copies"""
    dossier = os.path.dirname(ic['fichier']); base = ic['nom']
    pris = {x.get('icone') for x in reg.values()}
    for n in range(1, 10000):
        code = base[:-4] + '%04d' % n
        code = code[:2] + '9' + code[3:] if len(code) > 3 else code
        if code not in pris and not os.path.exists(os.path.join(data_dir, 'dx11', *dossier.split('/'), code + '.g4tx')):
            return code
    raise ValueError('plus de code libre')


# ---------------------------------------------------------------------------------------------------------- (27/11) MODÈLE 3D PORTÉ
# muku (vu en jeu) : « les équipements qui ont des modèles 3D, il faudrait changer la couleur aussi ». LU : item_config col 18 des
# crampons (et d'une paire de gants, cro_eq_mi110004) = un KIT de uniform_config (m_UniformInfoList nameId -> modelInfo = début |
# nombre << 16 dans m_UniformModelInfoList) ; le jeu en prend shoesFielderModelIdCrc (crampons) ou gloveModelIdCrc (gants).
# Ex. eq_sh110001 (Crampons simples) -> kit 0x394A731E -> s075101_10. Copie recolorée = comme ChronicleDeluxe (inazuma_japan_v) :
# [[shoes]] / [[gloves]] id neuf, from = celles du jeu, rows = [{ texture = neuve }, {}, …] + [[kit]] from = le kit du jeu, ses
# lignes avec shoes / glove = les neuves + l'objet model = { uniform = "MesObjets.<kit>" } (comme ChronicleDeluxe items/ie3_kits).
_MODELES = {}


def _kits_uniformes(data_dir):
    if not _MODELES:
        import sys, struct
        from . import rdbn       # (28/11) copié dans moteur/ : avant, pris dans Chargeur/outils (absent chez les autres -> erreur)
        f = sorted(glob.glob(os.path.join(data_dir, 'common', 'gamedata', 'character', 'uniform_config_*.cfg.bin')))[-1]
        t = rdbn.Table(open(f, 'rb').read())
        noms = {zlib.crc32(s): s.decode() for s in t.noms.split(b'\0') if s}
        L = {noms.get(l['crc']): i for i, l in enumerate(t.listes)}

        def lire(nom):
            i = L[nom]; cols = {noms.get(c, hex(c)): pl for c, ty, ta, pl in t.colonnes(i)}
            return [{k: struct.unpack_from('<I', r, pl)[0] for k, pl in cols.items() if pl + 4 <= len(r)} for r in t.listes[i]['lignes']]
        info, mod = lire('m_UniformInfoList'), lire('m_UniformModelInfoList')
        for r in info:
            st, n = r['modelInfo'] & 0xFFFF, r['modelInfo'] >> 16
            _MODELES[r['nameId']] = mod[st:st + n]
    return _MODELES


def modele_porte(data_dir, code):
    """{'sorte': 'shoes'|'gloves', 'cle': chaussures / gants du jeu, 'kit': id, 'types': [typeId…], 'lignes': lignes chara_parts}
    ou None (pendentifs, spéciaux, la plupart des bracelets : pas de modèle)"""
    v = ligne_objet(data_dir, code)
    if not v or len(v) <= 18 or not isinstance(v[18], int) or not v[18]:
        return None
    from . import copies_tenues as T
    rows = _kits_uniformes(data_dir).get(v[18] & 0xFFFFFFFF)
    if not rows:
        return None
    P = T._parties(data_dir)
    sorte, col = ('shoes', 'shoesFielderModelIdCrc') if str(code).startswith(('eq_sh', 'cro_eq_sh')) else ('gloves', 'gloveModelIdCrc')
    par = {zlib.crc32(k.encode()): k for k in P[sorte]}
    cle = next((par.get(r.get(col)) for r in rows if par.get(r.get(col))), None)
    if not cle:
        return None
    lignes = P[sorte][cle]
    return {'sorte': sorte, 'cle': cle, 'kit': v[18] & 0xFFFFFFFF, 'types': [r.get('typeId', i) for i, r in enumerate(rows)], 'lignes': lignes,
            'chemin': 'common/chr/%s|dx11/chr/%s|%s' % (lignes[0][0], lignes[0][1], cle) if lignes and isinstance(lignes[0][1], str) else None}


def _modele_recolore(cfg, x, e, textures, reg, rapport):
    """écrit la texture recolorée du modèle porté (g4tx du jeu, images remplacées) ; x['modele'] = ce qu'écrit ecrire()"""
    from . import copies_tenues as T
    m = modele_porte(cfg['data_dir'], e['code'])
    if not m or not m['chemin']:
        return
    chemin = m['lignes'][0][1]
    lettre = 'so' if m['sorte'] == 'shoes' else 'go'
    if not (x.get('modele') or {}).get('cle'):
        pris = {(v.get('modele') or {}).get('cle') for v in reg.values()} | set(T._parties(cfg['data_dir'])[m['sorte']])
        neuf = next('%s%06d' % (lettre, n) for n in range(1, 1000000) if '%s%06d' % (lettre, n) not in pris)
    else:
        neuf = x['modele']['cle']
    D = cfg['data_dir']
    gt = images.G4TX(open(os.path.join(D, 'dx11', 'chr', *chemin.split('/')), 'rb').read())
    rempl = {}
    import tempfile, struct
    from .esprits import _png
    tmp = tempfile.mkdtemp()
    try:
        with images.pool_encodage() as pool:
            for n_, url in textures.items():
                if n_ not in gt.noms:
                    continue
                bloc = gt.blocs[gt.noms.index(n_)]
                h0, w0 = struct.unpack_from('<II', bloc, 12)
                w, h, rows_ = _png(url, tmp)
                if (w, h) != (w0, h0):
                    rows_ = images.redimensionner(w, h, rows_, w0, h0); w, h = w0, h0
                if bloc[84:88] == b'DX10' and struct.unpack_from('<I', bloc, 128)[0] == 98:
                    rempl[n_] = images.dds_bc7(w, h, rows_, bloc[:148], images.mips_dds(bloc), pool)
                elif bloc[84:88] == b'DXT1':
                    rempl[n_] = images.dds_bc1(w, h, rows_, pool, mips=images.mips_dds(bloc))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    if not rempl:
        return
    d = os.path.join(_sortie(cfg), 'assets', 'chr', '_uniform', neuf); os.makedirs(d, exist_ok=True)
    open(os.path.join(d, neuf + '_10.g4tx'), 'wb').write(gt.reconstruire(rempl))
    x['modele'] = {'sorte': m['sorte'], 'cle': neuf, 'base': m['cle'], 'kit': m['kit'], 'types': m['types'],
                   'texture': '_uniform/%s/%s_10.g4tx' % (neuf, neuf), 'texture_base': chemin, 'nb_lignes': len(m['lignes'])}
    rapport.append('modèle 3D recoloré : %s %s (copie de %s, porté par le kit 0x%08X)' % ('crampons' if m['sorte'] == 'shoes' else 'gants', neuf, m['cle'], m['kit']))


def _look_modele(cle, x):
    """lignes VRFW.look/2 du modèle porté recoloré d'une copie (voir _modele_recolore)"""
    m = x.get('modele') or {}
    if not m.get('cle'):
        return []
    sorte, champ = m['sorte'], 'shoes' if m['sorte'] == 'shoes' else 'glove'
    rows = ', '.join(['{ texture = %s }' % _q(m['texture'])] + ['{}'] * (m.get('nb_lignes', 1) - 1))
    out = ['# %s : %s recolorés' % (x.get('nom'), 'crampons' if sorte == 'shoes' else 'gants'),
           '[[%s]]' % sorte, 'id = %s' % _q(m['cle']), 'from = %s' % _q(m['base']), 'rows = [%s]' % rows, '',
           '[[kit]]', 'name = %s' % _q('mo_' + cle), 'from = 0x%08X' % m['kit']]
    for ty in m.get('types') or [0, 1]:
        out += ['  [[kit.model]]', '  type = %d' % ty, '  %s = %s' % (champ, _q(m['cle']))]
    return out + ['']


def exporter(cfg, demande, e):
    """demande = {code, nom, description, prix, icone (data URL PNG de l'icône recolorée, si l'objet en a une)}"""
    nom = str(demande.get('nom') or '').strip()
    if not nom:
        return {'ok': False, 'erreur': 'Donne un nom au nouvel objet.'}
    if refus_copie(e):
        return {'ok': False, 'erreur': 'Pas de copie pour « %s » : %s.' % (e.get('nom'), refus_copie(e))}
    if e.get('famille') == PLAQUE and not demande.get('icone'):
        # (27/11) une plaque a TOUJOURS son fichier neuf (sa ligne user_name_plate en a besoin) : sans dessin, l'image de l'original
        cdir = os.path.join(cfg['outil_dir'], 'cache')
        fp = os.path.join(cdir, 'icones_objets', re.sub(r'[^\w~.-]', '_', e['code']) + '.png')
        if icone(cfg['data_dir'], cdir, e) and os.path.isfile(fp):
            demande = dict(demande, icone='data:image/png;base64,' + base64.b64encode(open(fp, 'rb').read()).decode())
    reg = registre(cfg); cle = demande.get('cle') or slug(nom).strip('_') or 'objet'     # (27/11) cle : la création à refaire (Cosmétique)
    if not demande.get('cle'):                       # (28/11) slug coupé à 24 : pris par une création d'un autre nom -> clé neuve
        cle = cle_libre(reg, cle, nom, lambda x: x.get('base') == e['code'])
    x = reg.get(cle) or {}
    if x and x.get('base') != e['code']:
        return {'ok': False, 'erreur': 'Le nom « %s » est déjà pris par une autre copie : choisis-en un autre.' % nom}
    ic = e.get('icone')
    sortie = _sortie(cfg)
    x.update(base=e['code'], nom=nom, description=str(demande.get('description') or e.get('description') or ''), categorie=e.get('categorie'),
             prix=max(1, int(demande.get('prix') or x.get('prix') or 10)), nom_origine=e['nom'], genre=e['genre'], date=datetime.datetime.now().isoformat(timespec='seconds'))
    if e.get('famille') in EQUIPEMENTS and isinstance(demande.get('stats'), dict):      # (27/11) bonus réglés dans la création
        _t, S = stats_equipement(cfg['data_dir'])
        x['stats'] = {k: max(-S, min(S, int(demande['stats'].get(k) or 0))) for k in STATS}
    rapport = []
    if demande.get('rarete') not in (None, '') and e.get('famille') in ('ITEM_TITLE_INFO', 'ITEM_CONSUME_INFO'):   # (27/11) 1-2
        x['rarete'] = max(1, min(2, int(demande['rarete'])))
    elif e.get('famille') not in ('ITEM_TITLE_INFO', 'ITEM_CONSUME_INFO'):
        x.pop('rarete', None)                            # celle de l'original (le jeu : toujours 1)
    if demande.get('max') not in (None, ''):
        x['max'] = max(1, min(999999, int(demande['max'])))
    if unique(cfg['data_dir'], e['code']):               # (27/11) une seule, comme le jeu
        x['max'] = 1
    if e.get('famille') == SYNERGIE:
        from . import synergies
        dr = synergies.drapeaux(cfg['data_dir'])
        base = dr.get(synergies._signe(zlib.crc32(e['code'].encode()))) or {'effets': [], 'conditions': []}
        sy = demande.get('synergie') if isinstance(demande.get('synergie'), dict) else {}
        cur = x.get('synergie') or base                  # (27/11) « Modifier » garde les effets réglés (avant : ceux de l'original)
        eff = [[int(a), max(1, min(100, int(b))), 1 if int(c) else 0] for a, b, c in (sy.get('effets') or cur['effets'])][:3]
        cond = [int(c) for c in (sy.get('conditions') or cur['conditions'])][:8]
        if not eff:
            return {'ok': False, 'erreur': 'Une synergie a besoin d’au moins un effet.'}
        if not cond:
            return {'ok': False, 'erreur': 'Une synergie a besoin d’au moins un joueur (sinon elle serait toujours active).'}
        if not x.get('syn_cle'):
            pris = set(dr) | {v.get('syn_cle') for v in reg.values() if v.get('syn_cle')}
            x['syn_cle'] = synergies.cle_libre('sf' if e['code'].startswith('sf') else 'sp', pris)
        x['synergie'] = {'effets': eff, 'conditions': cond}
        # icône : 56 × 56 (comme CharacterReforged), nommée par le code, sur notre planche (SpriteRedirect depuis icon_synergy)
        x.update(icone=x['syn_cle'], mode_icone='planche', planche=PLANCHE_SYNERGIES)
        d = os.path.join(sortie, 'content', 'images', 'menu', '200_icon', '02_icon_item', 'mesobjets_icones'); os.makedirs(d, exist_ok=True)
        f = os.path.join(d, x['icone'] + '.png')
        if demande.get('icone'):
            open(f, 'wb').write(base64.b64decode(demande['icone'].split(',', 1)[1]))
        elif not os.path.isfile(f):
            cdir = os.path.join(cfg['outil_dir'], 'cache')
            if ic and icone(cfg['data_dir'], cdir, e):
                import shutil as _sh
                _sh.copy(os.path.join(cdir, 'icones_objets', re.sub(r'[^\w~.-]', '_', e['code']) + '.png'), f)
        if os.path.isfile(f):
            w, h, rows = images.lire_png(f)
            if (w, h) != (56, 56):
                images.ecrire_png(f, 56, 56, images.redimensionner(w, h, rows, 56, 56))
        rapport.append('synergie %s %s : %d effet(s), %d joueur(s) nécessaire(s)' % ('offensive' if x['syn_cle'].startswith('sf') else 'défensive', x['syn_cle'], len(eff), len(cond)))
        ic = None                                          # (icône traitée ici)
    if e.get('famille') in TACTIQUES:                      # (27/11) l'icône vient de la tactique : celle de l'original
        if demande.get('icone'):
            rapport.append('icône : celle de la tactique d’origine (le jeu la prend dans la tactique, pas dans l’objet)')
        x.update(icone=None, mode_icone=None); ic = None
    fichier_ok = ic and os.path.dirname(ic['fichier']) in ('menu/200_icon/01_icon_emblem', 'menu/200_icon/25_icon_nameplate')
    if ic and demande.get('icone') and (ic['nb'] > 1 or fichier_ok or ic['fichier'] in PLANCHES_A_ZONES):
        png = base64.b64decode(demande['icone'].split(',', 1)[1])
        if (ic['nb'] > 1 or ic['fichier'] in PLANCHES_A_ZONES) and not fichier_ok:   # planche du jeu : notre planche + SpriteRedirect
            pris = {v.get('icone') for k_, v in reg.items() if k_ != cle}
            nouv = x.get('icone') if x.get('mode_icone') == 'planche' and str(x.get('icone')).startswith((_prefixe(e['code'], e.get('famille')) or 'mo') + '_mo_') else nom_icone(e['code'], cle, pris, e.get('famille'))
            x.update(icone=nouv, mode_icone='planche', planche='#/' + ic['fichier'])
            d = os.path.join(sortie, 'content', 'images', 'menu', '200_icon', '02_icon_item', 'mesobjets_icones'); os.makedirs(d, exist_ok=True)
            f = os.path.join(d, x['icone'] + '.png'); open(f, 'wb').write(png)
            w, h, rows = images.lire_png(f)
            if (w, h) != (256, 256):
                images.ecrire_png(f, 256, 256, images.redimensionner(w, h, rows, 256, 256))
            rapport.append('icône recolorée (planche %s)' % ic['fichier'].split('/')[-1])
        else:                                             # un fichier par icône (emblème, plaque…) : fichier neuf au code neuf
            code = x.get('icone') if x.get('mode_icone') == 'fichier' else _code_fichier(cfg['data_dir'], ic, reg)
            x.update(icone=code, mode_icone='fichier')
            dossier = os.path.dirname(ic['fichier'])
            tmp = os.path.join(sortie, '_tmp.png'); os.makedirs(sortie, exist_ok=True); open(tmp, 'wb').write(png)
            w0, h0, rows0 = images.lire_png(tmp); os.remove(tmp)
            for suf in ('', '_s', '_l'):
                src = os.path.join(cfg['data_dir'], 'dx11', *dossier.split('/'), ic['nom'] + suf + '.g4tx')
                if not os.path.exists(src):
                    continue
                g = images.G4TX(open(src, 'rb').read()); bl = g.blocs[0]
                import struct as _st
                hh, ww = _st.unpack_from('<II', bl, 12)
                rows = images.redimensionner(w0, h0, rows0, ww, hh) if (w0, h0) != (ww, hh) else rows0
                dds = images.dds_bc7(ww, hh, rows, bl[:148], images.mips_dds(bl)) if bl[84:88] == b'DX10' else images.dds_bc1(ww, hh, rows, mips=images.mips_dds(bl))
                from lib import bustes
                o = bustes.renommer(g.reconstruire({g.noms[0]: dds}), ic['nom'], code)
                dd = os.path.join(sortie, 'assets', *dossier.split('/'))          # comme MesMaillots : assets/menu/200_icon/01_icon_emblem
                os.makedirs(dd, exist_ok=True); open(os.path.join(dd, code + suf + '.g4tx'), 'wb').write(o)
            rapport.append('icône recolorée (fichier neuf %s, comme les emblèmes de ChronicleDeluxe et MesMaillots)' % code)
            # (27/11) aperçu de l'image (le mod n'a que des .g4tx dans ce cas) : Mes créations -> Cosmétique la montre
            dap = os.path.join(cfg['outil_dir'], 'cache', 'icones_objets'); os.makedirs(dap, exist_ok=True)
            open(os.path.join(dap, 'MesObjets~' + cle + '.png'), 'wb').write(png)
    elif e.get('famille') == SYNERGIE:
        pass
    elif ic:
        x.update(icone=None, mode_icone=None); rapport.append('icône : celle de l’original (pas recolorée)')
    elif e.get('famille') not in TACTIQUES:
        x.update(icone=None, mode_icone=None); rapport.append('pas d’image dans le jeu pour ce genre d’objet (affiché en texte)')
    if isinstance(demande.get('textures_modele'), dict) and demande['textures_modele']:     # (27/11) crampons / gants en 3D
        _modele_recolore(cfg, x, e, demande['textures_modele'], reg, rapport)
    reg[cle] = x
    os.makedirs(sortie, exist_ok=True)
    json.dump(reg, open(os.path.join(sortie, 'outil_objets.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    ecrire(cfg, reg)
    rapport.insert(0, '« %s » : copie de « %s » (%s, %s), %d jetons à la %s d’Inazuma Fantasy'
                   % (nom, e['nom'], e['code'], ('catégorie ' + x['categorie']) if x['categorie'] else 'catégorie prise par VRFW sur l’original', x['prix'],
                      'boutique d’entraînement' if e.get('famille') in ENTRAINEMENT else 'boutique générale'))   # (27/11) la vraie boutique
    # (28/11) code = clé de la création : l'Atelier relie le projet à CETTE copie (avant : rien -> deux copies d'Ogres
    # partageaient le même projet / les mêmes textures, et « Modifier » recréait l'objet en double)
    return {'ok': True, 'dossier': sortie, 'rapport': rapport, 'code': cle}


def ecrire(cfg, reg):
    sortie = _sortie(cfg)
    entete = '# Écrit par l\'Atelier Inazuma : copies d\'objets du jeu (réécrit à chaque export).\n'
    items, icones, boutique, entrainement, par_planche, zones, fusion, looks = [], [], [], [], {}, {}, [], []
    for cle, x in sorted(reg.items()):
        txt = []
        for lang in ('es', 'en', 'fr', 'de', 'it', 'pt', 'ja', 'zh_hans', 'zh_hant'):
            txt += ['  [item.text.%s]' % lang, '  name = %s' % _q(x['nom']), '  description = %s' % _q(x['description'])]
        items += ['# copie de « %s » (%s)' % (x.get('nom_origine', x['base']), x.get('genre', '')), '[[item]]', 'name = %s' % _q(cle), 'base = %s' % _q(x['base'])]
        if x.get('categorie'):
            items.append('category = %s' % _q(x['categorie']))
        if x.get('icone'):
            items += ['icon_key = %s' % _q(x['icone'])] + (['key_id = true'] if x.get('categorie') != 'title' else [])
        else:                                     # (27/11) sans icône à elle : celle de l'original (comme IECross), sinon rien à dessiner
            items.append('icon = %s' % _q(x['base']))
        if x.get('rarete'):
            items.append('rarity = %d' % x['rarete'])
        if (x.get('modele') or {}).get('cle'):            # (27/11) modèle 3D porté recoloré : notre kit (content/looks/mes_objets.toml)
            items.append('model = { uniform = %s }' % _q('%s.mo_%s' % (MOD_ID, cle)))
            looks += _look_modele(cle, x)
        seul = unique(cfg['data_dir'], x['base'])
        if seul:
            items.append('max_stack = 1                    # une seule, comme le jeu')
        elif x.get('max'):
            items.append('max_stack = %d' % x['max'])
        if _LIB_FAMILLE.get(x.get('genre')) in EQUIPEMENTS:   # (27/11) TOUJOURS les 7 bonus (sinon : non vu ce qu'hérite une copie)
            t, S = stats_equipement(cfg['data_dir'])
            st = x.get('stats') or dict(zip(STATS, t.get(x['base'], [0] * 7)))
            items += ['  [item.scale_stats]'] + ['  %s = %s' % (k, round(max(-S, min(S, int(st.get(k) or 0))) / S, 4)) for k in STATS]
        items += txt + ['']
        if x.get('mode_icone') == 'planche' and x.get('planche', '')[2:] in PLANCHES_A_ZONES:
            zones.setdefault(x['planche'], []).append(x['icone'])
        elif x.get('mode_icone') == 'planche':
            icones += ['[[texture]]', 'atlas = "#/menu/200_icon/02_icon_item/mesobjets_icones.g4tx"', 'name = %s' % _q(x['icone']),
                       'png = %s' % _q('mesobjets_icones/%s.png' % x['icone']), '']
            par_planche.setdefault(x['planche'], []).append(x['icone'])
        if _LIB_FAMILLE.get(x.get('genre')) == 'ITEM_CONSUME_INFO':
            # (27/11, VU EN JEU : le consommable n'apparaissait pas) un consommable que le jeu ne vend pas (« Guts Gear »…) : rangé par
            # la fusion des boutiques d'Inazuma Fantasy (ShopMergeAdd extra_items, comme ChronicleDeluxe), catégorie Consommables
            fusion.append('  { item = %s, price = %d, currency = "tk_bb000001", stock = 0 },' % (_q('%s.%s' % (MOD_ID, cle)), x['prix']))
        else:
            (entrainement if _LIB_FAMILLE.get(x.get('genre')) in ENTRAINEMENT else boutique).extend(
                ['  [[edit.entry]]', '  item = %s' % _q('%s.%s' % (MOD_ID, cle)), '  price = %d' % x['prix'], '  currency = "tk_bb000001"']
                + (['  stock = 1                        # une seule, comme le jeu'] if seul else []) + [''])
    # (27/11) planches à zones (synergies, autocollants, tactiques) : notre atlas = une texture où nos icônes sont posées côte à côte,
    # une [[sprite]] par icône (x, y, taille), comme CharacterReforged (30_icon_synergy/icon_synergy.toml) ; SpriteRedirect vers lui
    d_png = os.path.join(sortie, 'content', 'images', 'menu', '200_icon', '02_icon_item', 'mesobjets_icones')
    for pl, l in sorted(zones.items()):
        dossier = os.path.dirname(pl[2:]); base_at = 'mesobjets_' + os.path.basename(pl)[:-5]
        at = '#/%s/%s.g4tx' % (dossier, base_at)
        tailles = []
        for n in l:
            f = os.path.join(d_png, n + '.png')
            tailles.append(images.lire_png(f)[:2] if os.path.isfile(f) else (56, 56))
        larg, haut = sum(w for w, h in tailles), max(h for w, h in tailles)
        lignes_z = ['schema = "VRFW.image/1"', entete, '[[texture]]', 'atlas = %s' % _q(at), 'name = %s' % _q(base_at), 'size = [%d, %d]' % (larg, haut), '']
        xx = 0
        for n, (w, h) in zip(l, tailles):
            dz = os.path.join(sortie, 'content', 'images', *dossier.split('/'), 'mesobjets'); os.makedirs(dz, exist_ok=True)
            if os.path.isfile(os.path.join(d_png, n + '.png')):          # (png à côté du .toml, comme CharacterReforged / Inazuma Fantasy)
                shutil.copy(os.path.join(d_png, n + '.png'), os.path.join(dz, n + '.png'))
            lignes_z += ['[[sprite]]', 'atlas = %s' % _q(at), 'name = %s' % _q(n), 'texture = %s' % _q(base_at), 'x = %d' % xx, 'y = 0',
                         'size = [%d, %d]' % (w, h), 'png = %s' % _q('mesobjets/%s.png' % n), '']
            xx += w
        fz = os.path.join(sortie, 'content', 'images', *dossier.split('/'), base_at + '.toml')
        _ecrire(fz, '\n'.join(lignes_z)); tomllib.load(open(fz, 'rb'))
        par_planche.setdefault(pl, []).extend(l)
        zones[pl] = at
    sprites = []
    for pl, l in sorted(par_planche.items()):
        sprites += ['[[VRFW.SpriteRedirect]]', 'name = %s' % _q('mes_objets_' + re.sub(r'[^a-z0-9_]', '_', pl.split('/')[-1].split('.')[0])), 'atlas = %s' % _q(pl),
                    'own_atlas = %s' % _q(zones.get(pl) or '#/menu/200_icon/02_icon_item/mesobjets_icones.g4tx'), 'sprites = [%s]' % ', '.join(_q(s) for s in l), '']
    _ecrire(os.path.join(sortie, 'content', 'items', 'mes_objets.toml'), 'schema = "VRFW.item/2"\n' + entete + 'default_lang = "en"\n\n' + '\n'.join(items))
    for p, contenu in ((('content', 'images', 'menu', '200_icon', '02_icon_item', 'mesobjets_icones.toml'), 'schema = "VRFW.image/1"\n' + entete + '\n' + '\n'.join(icones)),
                       (('content', 'sprite_redirects', 'mes_objets.toml'), 'schema = "VRFW.sprite_redirect/1"\n' + entete + '\n' + '\n'.join(sprites))):
        f = os.path.join(sortie, *p)
        if icones:
            _ecrire(f, contenu)
        elif os.path.exists(f):
            os.remove(f)
    _ecrire(os.path.join(sortie, 'addons', 'InazumaFantasy', 'content', 'shops', 'mes_objets.toml'),
            'schema = "VRFW.shop/2"\n' + entete + '\n[[edit]]\ntarget = "InazumaFantasy.general_store"\n\n' + '\n'.join(boutique))
    add, lk = _tables_plaques(reg)
    for f, contenu in ((os.path.join(sortie, 'content', 'tables', 'common', 'gamedata', 'user_name_plate', 'user_name_plate_config.toml'),
                        'schema = "VRFW.table/1"\n' + entete + 'table = "user_name_plate/user_name_plate"\n\n' + '\n'.join(add)),
                       # (27/11, journal VRFW : « contradicts the path ») le fichier porte le nom du fichier du JEU qui a la table
                       (os.path.join(sortie, 'content', 'tables', 'common', 'gamedata', 'item', 'item_config.toml'),
                        'schema = "VRFW.table/1"\n' + entete + 'table = "item/item_name_plate"\n\n' + '\n'.join(lk))):
        if add:
            _ecrire(f, contenu); tomllib.load(open(f, 'rb'))
        elif os.path.exists(f):
            os.remove(f)
    ic, ie = _tables_boites(cfg['data_dir'], reg)
    for f, l in ((os.path.join(sortie, 'content', 'base_tables', 'gamedata', 'item', 'item_config.toml'), ic),
                 (os.path.join(sortie, 'content', 'base_tables', 'gamedata', 'item', 'item_emission_rarity_table_config.toml'), ie)):
        if l:
            _ecrire(f, 'schema = "VRFW.base_table/1"\n' + entete + '# contenu des boîtes copiées (celui de leur original, sous le numéro de la copie)\n\n' + '\n'.join(l))
            tomllib.load(open(f, 'rb'))
        elif os.path.exists(f):
            os.remove(f)
    f_l = os.path.join(sortie, 'content', 'looks', 'mes_objets.toml')
    if looks:
        _ecrire(f_l, 'schema = "VRFW.look/2"\n' + entete + '\n' + '\n'.join(looks))
        tomllib.load(open(f_l, 'rb'))
    elif os.path.exists(f_l):
        os.remove(f_l)
    f_f = os.path.join(sortie, 'addons', 'InazumaFantasy', 'content', 'shop_merges', 'mes_objets.toml')
    if fusion:
        _ecrire(f_f, 'schema = "VRFW.shop_merge/1"\n' + entete + '\n[[VRFW.ShopMergeAdd]]\nname = "mes_objets"\nmerge = "InazumaFantasy.shops"\nextra_items = [\n'
                + '\n'.join(fusion) + '\n]\n')
        tomllib.load(open(f_f, 'rb'))
    elif os.path.exists(f_f):
        os.remove(f_f)
    f_e = os.path.join(sortie, 'addons', 'InazumaFantasy', 'content', 'shops', 'mes_objets_entrainement.toml')
    if entrainement:
        _ecrire(f_e, 'schema = "VRFW.shop/2"\n' + entete + '\n[[edit]]\ntarget = "InazumaFantasy.training_shop"\n\n' + '\n'.join(entrainement))
        tomllib.load(open(f_e, 'rb'))
    elif os.path.exists(f_e):
        os.remove(f_e)
    syn = []
    for cle, x in sorted(reg.items()):
        if x.get('syn_cle') and x.get('synergie'):
            ef = ', '.join('{ effect = %d, value = %d, flag_9 = %d }' % tuple(v) for v in x['synergie']['effets'])
            co = ', '.join('{ chara = %d }' % c for c in x['synergie']['conditions'])
            syn += ['# « %s » (copie de %s)' % (x['nom'], x['base']), '[[add]]', 'key = %s' % _q(x['syn_cle']), 'from = %s' % _q(x['base']),
                    'cells = { REF_EFFECT = { set = [ %s ] }, REF_EXEC_COND = { set = [ %s ] } }' % (ef, co), '']
    f_syn = os.path.join(sortie, 'content', 'tables', 'common', 'gamedata', 'skill', 'synergy_flag_config.toml')
    if syn:
        _ecrire(f_syn, 'schema = "VRFW.table/1"\n' + entete + 'table = "skill/synergy_flag"\n\n' + '\n'.join(syn))
        tomllib.load(open(f_syn, 'rb'))
    elif os.path.exists(f_syn):
        os.remove(f_syn)
    orbes = _orbes(cfg, reg)
    f_s, f_t, f_g = (os.path.join(sortie, 'scripts', 'scripts.toml'), os.path.join(sortie, 'scripts', 'mes_objets_orbes.lua'),
                     os.path.join(sortie, 'content', 'game', 'mes_objets_orbes.toml'))
    if orbes:
        _ecrire(f_s, 'schema = "VRFW.script/1"\n' + entete + '\n# nos copies d\'orbes de niveau (Inazuma Fantasy)\n[[script]]\nfile = "mes_objets_orbes.lua"\n')
        os.makedirs(os.path.dirname(f_t), exist_ok=True)
        open(f_t, 'w', encoding='utf-8').write('-- ' + entete.strip('# \n') + '\n-- Nos copies des orbes de niveau d\'Inazuma Fantasy donnent les niveaux de leur original : Inazuma Fantasy ne connaît\n'
                '-- que ses orbes (config.toml [level_orbs.levels], par id) ; ce filtre de sa commande répond pour nos copies.\n'
                'local u32 = VRFW.ids.unsigned\nlocal NIVEAUX = {\n'
                + ''.join('  [0x%08X] = %d,   -- %s (copie de %s)\n' % (i, n, k, b) for i, n, k, b in orbes)
                + '}\nMesObjets = MesObjets or {}\nfunction MesObjets.NiveauxOrbe(item)\n  local n = NIVEAUX[u32(tonumber(item) or 0)]\n'
                '  if n then return true, n end\n  return false\nend\n')
        _ecrire(f_g, 'schema = "VRFW.game/1"\n' + entete + '\n# CMND_INAZUMAFANTASY_LEVEL_ORB_LEVELS (crc32 du nom) : 0 = pas une orbe de niveau ; nos copies -> les niveaux de leur original\n'
                '[[VRFW.CommandFilter]]\nname = "MesObjets.OrbesNiveaux"\ncommand = 0x%08X\nhandler = "MesObjets.NiveauxOrbe"\n' % zlib.crc32(b'CMND_INAZUMAFANTASY_LEVEL_ORB_LEVELS'))
    else:
        for f in (f_s, f_t, f_g):
            if os.path.exists(f):
                os.remove(f)
    _ecrire(os.path.join(sortie, 'mod.toml'), '\n'.join([
        'id = "%s"' % MOD_ID, 'name = "Mes objets"', 'prefix = "%s"' % MOD_ID, 'folder = "%s"' % MOD_ID, 'version = "1.0.0"', 'author = "muku"',
        'description = "Copies d\'objets du jeu (icône, nom, description), créées avec l\'Atelier Inazuma. En vente à la boutique générale d\'Inazuma Fantasy."',
        'priority = 0', 'tags = ["Items"]', 'updated = "%s"' % datetime.date.today().isoformat(),
        'requires = ["VRFW>=0.3.0"]', 'optional = ["InazumaFantasy"]', 'conflicts = []']
        + (['permissions = ["command"]', 'loader_modules = ["lua_bridge"]', 'loader_min = "1.7.0"'] if orbes else []) + ['']))
    for p in ('content/items/mes_objets.toml', 'addons/InazumaFantasy/content/shops/mes_objets.toml', 'mod.toml'):
        tomllib.load(open(os.path.join(sortie, *p.split('/')), 'rb'))


def niveaux_orbes(cfg):
    """(27/11) {clé d'orbe : niveaux} d'Inazuma Fantasy (son config.toml [level_orbs.levels]), sinon ses valeurs connues"""
    f = os.path.join(cfg.get('jeu_dir') or '', 'mods', 'InazumaFantasy', 'config.toml')
    try:
        d = tomllib.load(open(f, 'rb')).get('level_orbs', {}).get('levels', {})
        if d:
            return {k: int(v) for k, v in d.items() if isinstance(v, (int, float)) and v >= 1}
    except Exception:
        pass
    return {'ex0001': 1, 'ex0002': 5, 'ex0003': 10}


def _orbes(cfg, reg):
    """(27/11, VU EN JEU par muku : « le consommable que tu as fait ne donne aucun XP ») [(id de la copie, niveaux, clé, base)] :
    Inazuma Fantasy fait des orbes ex0001-3 des orbes de NIVEAU (+1 / +5 / +10) par leur id (scripts/level_orbs.lua) ; une copie
    n'y est pas et retombe sur l'EXP du jeu (500…), presque rien. Id d'une copie = crc32 de sa clé (key_id)"""
    N = niveaux_orbes(cfg)
    return [(zlib.crc32((x['icone'] if x.get('icone') else '%s.%s' % (MOD_ID, cle)).encode()), N[x['base']], cle, x['base'])
            for cle, x in sorted(reg.items()) if x.get('base') in N]


def appliquer_reglages(cfg, x, d):
    """(27/11, muku : « comme les techniques : le nom et la description dans la 3D », les stats dans Cosmétique) réglages d'une
    copie posés depuis l'étape Cosmétique : bonus d'un équipement, synergie (effets, joueurs), type de titre / fond, quantité max.
    Modifie x (l'entrée du registre) ; rend [rapport] ou lève ValueError"""
    fam, out = _LIB_FAMILLE.get(x.get('genre')), []
    if fam in EQUIPEMENTS and isinstance(d.get('stats'), dict):
        _t, S = stats_equipement(cfg['data_dir'])
        x['stats'] = {k: max(-S, min(S, int(d['stats'].get(k) or 0))) for k in STATS}
        out.append('bonus : ' + (', '.join('%s %+d' % (k, v) for k, v in x['stats'].items() if v) or 'aucun'))
    if fam in ('ITEM_TITLE_INFO', 'ITEM_CONSUME_INFO') and d.get('rarete') not in (None, ''):
        x['rarete'] = max(1, min(2, int(d['rarete'])))
        out.append({'ITEM_TITLE_INFO': 'titre ' + ('doré' if x['rarete'] == 2 else 'argenté')}.get(fam, 'fond ' + ('brillant' if x['rarete'] == 2 else 'normal')))
    if d.get('max') not in (None, '') and not unique(cfg['data_dir'], x['base']):
        x['max'] = max(1, min(999999, int(d['max']))); out.append('quantité max : %d' % x['max'])
    if fam == SYNERGIE and isinstance(d.get('synergie'), dict):
        sy = d['synergie']
        eff = [[int(a), max(1, min(100, int(b))), 1 if int(c) else 0] for a, b, c in (sy.get('effets') or [])][:3]
        cond = [int(c) for c in (sy.get('conditions') or [])][:8]
        if not eff:
            raise ValueError('Une synergie a besoin d’au moins un effet.')
        if not cond:
            raise ValueError('Une synergie a besoin d’au moins un joueur (sinon elle serait toujours active).')
        x['synergie'] = {'effets': eff, 'conditions': cond}
        out.append('synergie : %d effet(s), %d joueur(s) nécessaire(s)' % (len(eff), len(cond)))
    return out


def contenu(cfg):
    return [dict(x, cle=k) for k, x in registre(cfg).items()]
