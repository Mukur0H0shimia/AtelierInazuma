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
import os, re, json, glob, zlib, datetime, base64, tomllib
from .g4 import images
from . import g4
from .maillots.cfgbin import parse
from .esprits import slug
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
    f_cache = os.path.join(cache_dir, 'index_objets_jeu.json')
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
    im = _images_menu(data_dir, cache_dir)
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
        icone_nom = cle if cle in im else None
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
    # (17/11/2026) objets des mods : icône sur une planche du mod (« abs » = chemin sur le disque)
    g = images.G4TX(open(ic['abs'] if ic.get('abs') else os.path.join(data_dir, 'dx11', *ic['fichier'].split('/')), 'rb').read())
    r = g4.decoder_texture(g.blocs[ic['image']])
    if not r:
        return None
    images.ecrire_png(f, *r)
    return r[0], r[1]


def details(cfg, cache_dir, e):
    """comme un esprit, mais sans 3D : un « objet » qui n'a qu'une texture, son icône"""
    t = icone(cfg['data_dir'], cache_dir, e)
    tex = [{'nom': e['code'], 'lisible': bool(t), 'donnees': False, 'w': t[0] if t else 0, 'h': t[1] if t else 0}] if t else []
    o = {'acteur': e['code'], 'chemin': None, 'nom': 'icones_objets', 'role': 'icone', 'modeleActeur': True, 'pieces': [], 'textures': tex}
    return dict(e, objets_details=[o], auras=[], categorie='objets')


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


def exporter(cfg, demande, e):
    """demande = {code, nom, description, prix, icone (data URL PNG de l'icône recolorée, si l'objet en a une)}"""
    nom = str(demande.get('nom') or '').strip()
    if not nom:
        return {'ok': False, 'erreur': 'Donne un nom au nouvel objet.'}
    reg = registre(cfg); cle = slug(nom).strip('_') or 'objet'
    x = reg.get(cle) or {}
    if x and x.get('base') != e['code']:
        return {'ok': False, 'erreur': 'Le nom « %s » est déjà pris par une autre copie : choisis-en un autre.' % nom}
    ic = e.get('icone')
    sortie = _sortie(cfg)
    x.update(base=e['code'], nom=nom, description=str(demande.get('description') or e.get('description') or ''), categorie=e.get('categorie'),
             prix=max(1, int(demande.get('prix') or 10)), nom_origine=e['nom'], genre=e['genre'], date=datetime.datetime.now().isoformat(timespec='seconds'))
    rapport = []
    fichier_ok = ic and os.path.dirname(ic['fichier']) in ('menu/200_icon/01_icon_emblem', 'menu/200_icon/25_icon_nameplate')
    if ic and demande.get('icone') and (ic['nb'] > 1 or fichier_ok):
        png = base64.b64decode(demande['icone'].split(',', 1)[1])
        if ic['nb'] > 1 and not fichier_ok:               # planche à plusieurs images : notre planche + SpriteRedirect
            x.update(icone='mo_' + cle[:28], mode_icone='planche', planche='#/' + ic['fichier'])
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
    elif ic:
        x.update(icone=None, mode_icone=None); rapport.append('icône : celle de l’original (pas recolorée)')
    else:
        x.update(icone=None, mode_icone=None); rapport.append('pas d’image dans le jeu pour ce genre d’objet (affiché en texte)')
    reg[cle] = x
    os.makedirs(sortie, exist_ok=True)
    json.dump(reg, open(os.path.join(sortie, 'outil_objets.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    ecrire(cfg, reg)
    rapport.insert(0, '« %s » : copie de « %s » (%s, %s), %d jetons à la boutique générale d’Inazuma Fantasy'
                   % (nom, e['nom'], e['code'], ('catégorie ' + x['categorie']) if x['categorie'] else 'catégorie prise par VRFW sur l’original', x['prix']))
    return {'ok': True, 'dossier': sortie, 'rapport': rapport}


def ecrire(cfg, reg):
    sortie = _sortie(cfg)
    entete = '# Écrit par l\'Atelier Inazuma : copies d\'objets du jeu (réécrit à chaque export).\n'
    items, icones, boutique, par_planche = [], [], [], {}
    for cle, x in sorted(reg.items()):
        txt = []
        for lang in ('es', 'en', 'fr', 'de', 'it', 'pt', 'ja', 'zh_hans', 'zh_hant'):
            txt += ['  [item.text.%s]' % lang, '  name = %s' % _q(x['nom']), '  description = %s' % _q(x['description'])]
        items += ['# copie de « %s » (%s)' % (x.get('nom_origine', x['base']), x.get('genre', '')), '[[item]]', 'name = %s' % _q(cle), 'base = %s' % _q(x['base'])]
        if x.get('categorie'):
            items.append('category = %s' % _q(x['categorie']))
        if x.get('icone'):
            items += ['icon_key = %s' % _q(x['icone'])] + (['key_id = true'] if x.get('categorie') != 'title' else [])
        items += txt + ['']
        if x.get('mode_icone') == 'planche':
            icones += ['[[texture]]', 'atlas = "#/menu/200_icon/02_icon_item/mesobjets_icones.g4tx"', 'name = %s' % _q(x['icone']),
                       'png = %s' % _q('mesobjets_icones/%s.png' % x['icone']), '']
            par_planche.setdefault(x['planche'], []).append(x['icone'])
        boutique += ['  [[edit.entry]]', '  item = %s' % _q('%s.%s' % (MOD_ID, cle)), '  price = %d' % x['prix'], '  currency = "tk_bb000001"', '']
    sprites = []
    for pl, l in sorted(par_planche.items()):
        sprites += ['[[VRFW.SpriteRedirect]]', 'name = %s' % _q('mes_objets_' + re.sub(r'[^a-z0-9_]', '_', pl.split('/')[-1].split('.')[0])), 'atlas = %s' % _q(pl),
                    'own_atlas = "#/menu/200_icon/02_icon_item/mesobjets_icones.g4tx"', 'sprites = [%s]' % ', '.join(_q(s) for s in l), '']
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
    _ecrire(os.path.join(sortie, 'mod.toml'), '\n'.join([
        'id = "%s"' % MOD_ID, 'name = "Mes objets"', 'prefix = "%s"' % MOD_ID, 'folder = "%s"' % MOD_ID, 'version = "1.0.0"', 'author = "muku"',
        'description = "Copies d\'objets du jeu (icône, nom, description), créées avec l\'Atelier Inazuma. En vente à la boutique générale d\'Inazuma Fantasy."',
        'priority = 0', 'tags = ["Items"]', 'updated = "%s"' % datetime.date.today().isoformat(),
        'requires = ["VRFW>=0.3.0"]', 'optional = ["InazumaFantasy"]', 'conflicts = []', '']))
    for p in ('content/items/mes_objets.toml', 'addons/InazumaFantasy/content/shops/mes_objets.toml', 'mod.toml'):
        tomllib.load(open(os.path.join(sortie, *p.split('/')), 'rb'))


def contenu(cfg):
    return [dict(x, cle=k) for k, x in registre(cfg).items()]
