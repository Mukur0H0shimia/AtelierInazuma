"""(15/11/2026) COPIE D'UN PERSONNAGE avec sa tête recolorée : un nouveau joueur, code neuf, l'original ne change pas.

Fait comme Mukuro (mods/Mukuro, qui marche en jeu) et les copies d'Inazuma Fantasy / ChronicleDeluxe (LU dans leurs fichiers) :
- tête copiée dans assets/chr/_face/<série>/<code neuf>/ : g4md avec les noms ET leurs crc32 renommés (vérifié sur Mukuro :
  plus aucun crc de l'ancien nom), g4mg identique (simple recoloration), g4tx réencodé + noms renommés (bustes.renommer) ;
- portrait assets/menu/200_icon/10_icon_chr/face/<code neuf>_l.g4tx (celui de l'original, renommé) ;
- content/characters : VRFW.character/2, based_on = l'original, [character.new_model] from = l'original et
  cells.head_mesh_path seul (comme Inazuma Fantasy : le corps vient de « from »), [[character.cards]] id neuf + from =
  carte de l'original (comme ChronicleDeluxe : statistiques et techniques reprises de cette carte) ;
- carte de l'original : chara_param, colonne 0 = id de la carte, colonne 1 = crc32(code du personnage) (LU) ;
- obtenu au tirage Kizuna de ChronicleDeluxe (comme Mukuro : VRFW.gacha/1, pool « ChronicleDeluxe.kizuna_coin_gacha »).
"""
from moteur import langue as _langue  # noqa: E402  (FR / EN)
import os, re, json, glob, zlib, datetime, struct, shutil, tempfile, multiprocessing
from . import cfgbin, retouches
from .g4 import images
from .personnages import _japonais, _dernier
from .esprits import remplacer_crc, noms_contenant, slug, _png, cle_libre
from .export import _ecrire, _q
from lib import bustes                       # noqa: E402 (Atelier Maillots : renommage des noms d'images)

MOD_ID = 'MesPersonnages'
POOL = 'ChronicleDeluxe.kizuna_coin_gacha'


def _sortie(cfg):
    return os.path.join(cfg['outil_dir'], 'sortie', MOD_ID)


def registre(cfg):
    f = os.path.join(_sortie(cfg), 'outil_personnages.json')
    return json.load(open(f, encoding='utf-8')) if os.path.exists(f) else {}


def _sauver(cfg, r):
    os.makedirs(_sortie(cfg), exist_ok=True)
    json.dump(r, open(os.path.join(_sortie(cfg), 'outil_personnages.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)


def personnage_de_tete(data_dir, chemin_tete):
    """personnage qui porte cette tête : chara_model (v[10] = tête) -> chara_base (v[6] = modèle) ; sa carte (chara_param)"""
    c = os.path.join(data_dir, 'common')
    tete = chemin_tete.replace('\\', '/').split('/chr/', 1)[-1]
    modeles = set()
    for f in sorted(glob.glob(os.path.join(c, 'gamedata', 'character', 'chara_model_1*.cfg.bin'))):
        for k, v in cfgbin.lire(open(f, 'rb').read()):
            if len(v) > 10 and isinstance(v[0], int) and isinstance(v[10], str) and v[10].replace('\\', '/').lstrip('/') == tete:
                modeles.add(v[0] & 0xFFFFFFFF)
    noms = {}
    for k, v in cfgbin.lire(open(os.path.join(c, 'text', _langue.code(), 'chara_text.cfg.bin'), 'rb').read()):
        if len(v) > 5 and isinstance(v[0], int) and v[1] == 0 and isinstance(v[5], str):
            noms.setdefault(v[0] & 0xFFFFFFFF, v[5])
    candidats = []
    for k, v in cfgbin.lire(open(_dernier(os.path.join(c, 'gamedata', 'character', 'chara_base_*.cfg.bin')), 'rb').read()):
        if len(v) > 6 and isinstance(v[1], str) and isinstance(v[6], int) and (v[6] & 0xFFFFFFFF) in modeles:
            n = noms.get(v[3] & 0xFFFFFFFF) if isinstance(v[3], int) else None
            candidats.append({'code': v[1], 'nom': n if n and not _japonais(n) else v[1]})
    for p in candidats:
        crc = zlib.crc32(p['code'].encode())
        for k, v in cfgbin.lire(open(_dernier(os.path.join(c, 'gamedata', 'character', 'chara_param_1*.cfg.bin')), 'rb').read()):
            if len(v) > 1 and isinstance(v[1], int) and (v[1] & 0xFFFFFFFF) == crc and isinstance(v[0], int):
                p['carte'] = v[0] & 0xFFFFFFFF
                return p
    return None


def peau_origine(data_dir, code):
    """(26/11/2026, retour de jayden / WhiteRabbit : « la peau des bras et des jambes ne va pas avec la tête »)
    couleur de peau du CORPS d'un personnage du jeu : '#RRGGBB' ou None.
    LU : chara_model (CHARA_MODEL_INFO) colonne 16 = « skin_color » (nom du schéma de VRFW, winmm.dll), u32 RRGGBBAA, rangée à +4
    de l'enregistrement de 0xA8 octets (lecteur 0x140221ea0) ; chara_base v[6] = n° du modèle. La peau des bras (_uniform/sk…,
    texture blanche) et des jambes / du cou (c000N01_10, blanche) est peinte par le shader Chr_EditToon (chr_toon_edit.pfxo) :
    couleur = texture × lerp(1, u_skinColor, masque msk.r) ; la tête (Chr_ToonMetal, pas de masque) a sa peau peinte dans sa
    texture. MESURÉ : colonne 16 = la couleur dominante de l'atlas du visage (_10), ex. c11260010 (253, 192, 161), c01000010
    (241, 183, 135)."""
    return couleurs_corps(data_dir, code)['peau']


def couleurs_corps(data_dir, code):
    """(26/11/2026) {'peau': '#RRGGBB' ou None, 'parts_color': n° CHARA_PARTS_COLOR ou 0} du modèle de ce personnage.
    LU (tables + lecteur 0x140221ea0) : colonne 8 « parts_color » (u32 rangé à +0) = n° d'une ligne CHARA_PARTS_COLOR de
    chara_parts_*.cfg.bin = [n°, couleur RRGGBBAA, 2e couleur, 0]. MESURÉ sur les 6 527 modèles de personnages : colonne 16 et
    colonne 8 ne sont JAMAIS remplies ensemble ; 6 379 ont la colonne 16, 148 la colonne 8 (ex. Briar Bloomhurst c11010020 :
    0x8977FBE5 -> (179, 112, 93) = la couleur dominante de son visage ; 2e couleur toujours 0 pour eux), 689 aucune (animaux,
    objets, joueurs « Edit » c20…). DÉDUIT : colonne 16 vide -> la couleur de la ligne parts_color."""
    c = os.path.join(data_dir, 'common', 'gamedata', 'character')
    cle = (data_dir, code)
    if cle in _MEMO_CORPS:
        return _MEMO_CORPS[cle]
    out = {'peau': None, 'parts_color': 0}
    modele = None
    for k, v in cfgbin.lire(open(_dernier(os.path.join(c, 'chara_base_*.cfg.bin')), 'rb').read()):
        if len(v) > 6 and v[1] == code and isinstance(v[6], int):
            modele = v[6] & 0xFFFFFFFF
            break
    r = None
    if modele is not None:
        for f in sorted(glob.glob(os.path.join(c, 'chara_model_1*.cfg.bin'))):
            for k, v in cfgbin.lire(open(f, 'rb').read()):
                if len(v) > 16 and isinstance(v[0], int) and (v[0] & 0xFFFFFFFF) == modele:
                    r = v
                    break
            if r:
                break
    if r:
        x = r[16] & 0xFFFFFFFF if isinstance(r[16], int) else 0
        pc = r[8] & 0xFFFFFFFF if isinstance(r[8], int) else 0
        out['parts_color'] = pc
        if x:
            out['peau'] = '#%06X' % (x >> 8)
        elif pc:
            f = sorted(glob.glob(os.path.join(c, 'chara_parts_*.cfg.bin')))
            CRC = zlib.crc32(b'CHARA_PARTS_COLOR')
            for k, v in (cfgbin.lire(open(f[-1], 'rb').read()) if f else []):
                if k == CRC and len(v) > 1 and isinstance(v[0], int) and (v[0] & 0xFFFFFFFF) == pc and isinstance(v[1], int) and v[1]:
                    out['peau'] = '#%06X' % ((v[1] & 0xFFFFFFFF) >> 8)
                    break
    _MEMO_CORPS[cle] = out
    return out


_MEMO_CORPS = {}


# (27/11, muku : « ajouter une option pour choisir la morphologie quand on fait un joueur ») MORPHOLOGIE = le corps du modèle.
# LU : chara_model CHARA_MODEL_INFO [4] = n° d'une ligne CHARA_BODY_INFO (même table) = [n°, squelette '_common/c000<t>01/…objbin',
# chaussures, ?, rang (0-17), SORTE (0-7), ligne des vêtements (0-7)] ; les mods écrivent la cellule « body » du nouveau modèle
# (InazumaFantasy enma.toml : body = crc32("c90670000_body") ; ChronicleDeluxe galaxy_shadows : body = 0x00095CCB = corps de
# Mark Evans). SORTE, d'après les joueurs qui la portent (2 317 / 1 161 / 513… modèles) : 0 garçon normal (Mark Evans), 1 garçon
# petit (Tod Ironside), 2 garçon grand (Kevin Dragonfly), 3 garçon costaud (Jack Wallside), 4 fille normale (Samantha Moonlight),
# 5 fille petite (Maddie Moonlight), 6 fille grande (Yurina Kumai), 7 fille costaude (Daisy Fields). Le maillot de l'équipe suit
# tout seul (ligne des vêtements du corps), comme pour n'importe quel joueur de ce corps.
SORTES_CORPS = ['Garçon · normal', 'Garçon · petit', 'Garçon · grand', 'Garçon · costaud',
                'Fille · normale', 'Fille · petite', 'Fille · grande', 'Fille · costaude']


def morphologies(data_dir):
    """[{cle (n° CHARA_BODY_INFO), sorte (0-7), libelle, exemples [noms], nb}] : les corps COMMUNS du jeu (squelettes
    _common/c000N01), rangés par sorte puis du plus porté au moins porté (corps propres à un personnage, animaux : exclus)"""
    if _MEMO_MORPHO.get('d') == data_dir:
        return _MEMO_MORPHO['l']
    from .maillots.cfgbin import parse
    c = os.path.join(data_dir, 'common')
    f = _dernier(os.path.join(c, 'gamedata', 'character', 'chara_model_1*.cfg.bin'))
    corps, modele_corps = {}, {}
    for k, v in parse(f):
        if k == 'CHARA_BODY_INFO' and len(v) > 5 and isinstance(v[0], int) and '_common/c000' in str(v[1]) and isinstance(v[5], int) and 0 <= v[5] < 8:
            corps[v[0] & 0xFFFFFFFF] = {'cle': v[0] & 0xFFFFFFFF, 'sorte': v[5], 'libelle': SORTES_CORPS[v[5]], 'exemples': [], 'nb': 0}
        elif k == 'CHARA_MODEL_INFO' and len(v) > 4 and isinstance(v[0], int) and isinstance(v[4], int):
            modele_corps[v[0] & 0xFFFFFFFF] = v[4] & 0xFFFFFFFF
    noms = {}
    for k, v in cfgbin.lire(open(os.path.join(c, 'text', _langue.code(), 'chara_text.cfg.bin'), 'rb').read()):
        if len(v) > 5 and isinstance(v[0], int) and v[1] == 0 and isinstance(v[5], str):
            noms.setdefault(v[0] & 0xFFFFFFFF, v[5])
    for k, v in cfgbin.lire(open(_dernier(os.path.join(c, 'gamedata', 'character', 'chara_base_*.cfg.bin')), 'rb').read()):
        if len(v) > 6 and isinstance(v[6], int) and isinstance(v[1], str) and v[1].startswith('c'):
            b = corps.get(modele_corps.get(v[6] & 0xFFFFFFFF))
            if not b:
                continue
            b['nb'] += 1
            n = noms.get(v[3] & 0xFFFFFFFF) if isinstance(v[3], int) else None
            if n and not _japonais(n) and n not in b['exemples'] and len(b['exemples']) < 3:
                b['exemples'].append(n)
    # un seul porteur (0xC24D5909 : Destin Billows, colonne 3 à part) = corps spécial : pas proposé
    l = sorted((b for b in corps.values() if b['nb'] >= 2), key=lambda b: (b['sorte'], -b['nb']))
    _MEMO_MORPHO.update(d=data_dir, l=l)
    return l


_MEMO_MORPHO = {}


def corps_origine(data_dir, code):
    """n° CHARA_BODY_INFO du modèle du personnage « code » (chara_base v[6] -> chara_model [4]) ou None"""
    c = os.path.join(data_dir, 'common', 'gamedata', 'character')
    modele = None
    for k, v in cfgbin.lire(open(_dernier(os.path.join(c, 'chara_base_*.cfg.bin')), 'rb').read()):
        if len(v) > 6 and v[1] == code and isinstance(v[6], int):
            modele = v[6] & 0xFFFFFFFF
            break
    if modele is None:
        return None
    for f in sorted(glob.glob(os.path.join(c, 'chara_model_1*.cfg.bin'))):
        for k, v in cfgbin.lire(open(f, 'rb').read()):
            if len(v) > 4 and isinstance(v[0], int) and (v[0] & 0xFFFFFFFF) == modele and isinstance(v[4], int):
                return v[4] & 0xFFFFFFFF
    return None


def _libelle_corps(data_dir, cle):
    b = next((b for b in morphologies(data_dir) if b['cle'] == cle), None)
    # « Fille · costaude · Daisy Fields, Janine Brook » : morceaux séparés par « · », traduits un par un (web/i18n.js)
    return ('%s · %s' % (b['libelle'], ', '.join(b['exemples'][:2]))) if b and b['exemples'] else (b['libelle'] if b else '0x%08X' % cle)


def _peau_hex(v):
    """'#rrggbb' / 'rrggbb' -> 'RRGGBB' ; vide / invalide -> None"""
    v = str(v or '').strip().lstrip('#')
    return v.upper() if re.fullmatch(r'[0-9A-Fa-f]{6}', v) else None


def regler_peau(cfg, cle, peau):
    """(26/11/2026) couleur de peau des bras / jambes d'une copie déjà créée ('' = celle de l'original)"""
    reg = registre(cfg)
    if cle not in reg:
        return {'ok': False, 'erreur': 'copie de personnage inconnue'}
    p = _peau_hex(peau)
    if p:
        reg[cle]['peau'] = p
        reg[cle]['peau_main'] = True                     # gardée à la main : « Créer » en automatique ne la remplace pas
    else:
        reg[cle].pop('peau', None); reg[cle].pop('peau_main', None)
    _sauver(cfg, reg); _ecrire_contenu(cfg, reg)
    e = reg[cle]
    return {'ok': True, 'dossier': _sortie(cfg), 'peau': ('#' + p) if p else None,
            'rapport': ['%s : peau des bras et des jambes #%s' % (e['nom'], p) if p else
                        "%s : peau des bras et des jambes de l'original (%s)" % (e['nom'], e.get('nom_origine', ''))]}


def _ids_pris(cfg):
    """ids 32 bits déjà utilisés : textes et personnages du jeu, et tous les 0x… des mods installés"""
    c = os.path.join(cfg['data_dir'], 'common')
    pris = set()
    for f in [os.path.join(c, 'text', _langue.code(), 'chara_text.cfg.bin')] + sorted(glob.glob(os.path.join(c, 'gamedata', 'character', '*.cfg.bin'))):
        try:
            lignes = cfgbin.lire(open(f, 'rb').read())
        except Exception:                      # table illisible par notre lecteur : ignorée (les mods restent vérifiés)
            continue
        for k, v in lignes:
            if v and isinstance(v[0], int):
                pris.add(v[0] & 0xFFFFFFFF)
    mods = os.path.join(cfg['jeu_dir'], 'mods')
    for f in glob.glob(os.path.join(mods, '*', '**', '*.toml'), recursive=True):
        if os.sep + MOD_ID + os.sep in f:
            continue
        try:
            pris.update(int(x, 16) for x in re.findall(r'0x([0-9A-Fa-f]{8})', open(f, encoding='utf-8', errors='ignore').read()))
        except OSError:
            pass
    return pris


def _id(graine, pris):
    k = 0
    while True:
        v = zlib.crc32(('%s#%d' % (graine, k) if k else graine).encode())
        if v not in pris and v != 0:
            pris.add(v); return v
        k += 1


def _code_libre(cfg, anc, reg):
    """code de tête neuf, même longueur (cSS98NNNN) : pas dans le jeu, pas dans un mod, pas déjà pris par une de mes copies"""
    pris = {e['code'] for e in reg.values()}
    faces = os.path.join(cfg['data_dir'], 'common', 'chr', '_face')
    existants = {os.path.basename(p) for p in glob.glob(os.path.join(faces, '*', '*'))}
    mods = os.path.join(cfg['jeu_dir'], 'mods')
    existants |= {os.path.basename(p) for p in glob.glob(os.path.join(mods, '*', 'assets', 'chr', '_face', '*', '*'))}
    for n in range(1, 10000):
        c = '%s98%04d' % (anc[:3], n)
        if len(c) == len(anc) and c not in pris and c not in existants:
            return c
    raise ValueError('plus de code libre')


def cle_creation(reg, demande, cle, nom=None, meme=None):
    """(28/11, muku : « Modifier refait des doubles ») « Modifier » : demande['cle'] = code de LA création (c0198…) -> sa clé
    dans le registre (même si le nom a changé) ; sinon la clé du nom, rendue unique si elle est prise par une création d'un autre
    nom / d'une autre base (slug coupé à 24 : la 2e écrasait la 1re)"""
    if demande.get('cle'):
        k = next((k for k, v in reg.items() if str(v.get('code')) == str(demande['cle'])), None)
        if k:
            return k
    return cle_libre(reg, cle, nom, meme) if nom is not None else cle


def exporter(cfg, demande, entree):
    """demande = {code (tête), nom, description, textures {nom: data URL}} ; entree = élément « personnages » du catalogue"""
    nom = str(demande.get('nom') or '').strip()
    if not nom:
        return {'ok': False, 'erreur': 'Donne un nom au nouveau personnage.'}
    textures = demande.get('textures') or {}
    if not textures:
        return {'ok': False, 'erreur': 'Rien n’est modifié : recolore d’abord la tête.'}
    D = cfg['data_dir']
    md_rel = entree['chemin']                               # common/chr/_face/<série>/<code>/<code>.g4md
    anc = entree['code']; serie = md_rel.split('/')[3]
    orig = personnage_de_tete(D, md_rel)
    if not orig:
        return {'ok': False, 'erreur': 'Aucun personnage jouable ne porte cette tête (pas de carte à copier).'}
    reg = registre(cfg); cle = cle_creation(reg, demande, slug(nom), nom, lambda x: x.get('tete_origine') == anc and not x.get('genre'))
    e = reg.get(cle) or {}
    if e and e.get('tete_origine') != anc:
        return {'ok': False, 'erreur': 'Le nom « %s » est déjà pris par une autre copie : choisis-en un autre.' % nom}
    pris = _ids_pris(cfg)
    if not e:
        neuf = _code_libre(cfg, anc, reg)
        e = {'code': neuf, 'tete_origine': anc, 'base': orig['code'], 'carte_origine': orig['carte'],
             'id': zlib.crc32(neuf.encode()), 'modele': _id(MOD_ID + '.' + cle + '.modele', pris), 'carte': _id(MOD_ID + '.' + cle + '.carte', pris),
             'nom_txt': _id(MOD_ID + '.' + cle + '.nom', pris), 'court_txt': _id(MOD_ID + '.' + cle + '.court', pris),
             'desc_txt': _id(MOD_ID + '.' + cle + '.description', pris)}
        if e['id'] in pris:
            return {'ok': False, 'erreur': 'crc32(%s) déjà utilisé : réessaie' % neuf}
    neuf = e['code']
    e.update(nom=nom, description=str(demande.get('description') or ''), serie=serie, nom_origine=orig['nom'],
             date=datetime.datetime.now().isoformat(timespec='seconds'))
    if 'peau' in demande:                                  # (26/11) peau des bras / jambes (chara_model skin_color) ; vide = l'original
        p = _peau_hex(demande.get('peau'))
        if demande.get('peau_auto') and e.get('peau_main'):
            pass                                           # couleur gardée à la main avant (« Garder ») : l'automatique ne la remplace pas
        elif p and p != (_peau_hex(peau_origine(D, orig['code'])) or ''):
            e['peau'] = p
            e['peau_main'] = not demande.get('peau_auto')
            if not e['peau_main']:
                e.pop('peau_main')
        else:
            e.pop('peau', None); e.pop('peau_main', None)
    if 'corps' in demande:                                 # (27/11) morphologie : '' = celle de l'original
        try:
            k = int(str(demande.get('corps') or '0'), 0) & 0xFFFFFFFF
        except ValueError:
            return {'ok': False, 'erreur': 'Morphologie inconnue.'}
        if k and k != corps_origine(D, orig['code']):
            if not any(b['cle'] == k for b in morphologies(D)):
                return {'ok': False, 'erreur': 'Morphologie inconnue (0x%08X).' % k}
            e['corps'] = k
        else:
            e.pop('corps', None)
    sortie = _sortie(cfg)
    out = os.path.join(sortie, 'assets', 'chr', '_face', serie, neuf)
    os.makedirs(out, exist_ok=True)
    src = os.path.join(D, *md_rel.split('/'))
    # textures réencodées (comme MesRetouches), puis noms renommés
    tx_rel = retouches.fichier_texture(cfg, entree)
    gt = images.G4TX(open(os.path.join(D, 'dx11', *tx_rel.split('/')), 'rb').read())
    rempl, rapport, tmp = {}, [], tempfile.mkdtemp()
    try:
        with images.pool_encodage() as pool:
            for n_, url in textures.items():
                if n_ not in gt.noms:
                    return {'ok': False, 'erreur': '%s n’est pas dans %s' % (n_, tx_rel)}
                bloc = gt.blocs[gt.noms.index(n_)]
                h0, w0 = struct.unpack_from('<II', bloc, 12)
                w, h, rows = _png(url, tmp)
                if (w, h) != (w0, h0):
                    return {'ok': False, 'erreur': '%s : %dx%d au lieu de %dx%d' % (n_, w, h, w0, h0)}
                if bloc[84:88] == b'DX10' and struct.unpack_from('<I', bloc, 128)[0] == 98:
                    rempl[n_] = images.dds_bc7(w, h, rows, bloc[:148], images.mips_dds(bloc), pool)
                elif bloc[84:88] == b'DXT1':
                    rempl[n_] = images.dds_bc1(w, h, rows, pool, mips=images.mips_dds(bloc))
                else:
                    return {'ok': False, 'erreur': '%s : format pas encore pris en charge' % n_}
                rapport.append('%s (%dx%d)' % (n_, w, h))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    tx = bustes.renommer(gt.reconstruire(rempl), anc, neuf)
    open(os.path.join(out, neuf + '.g4tx'), 'wb').write(tx)
    # modèle : noms + crc32 (noms du g4md ET des images : certaines n'y sont qu'en crc32)
    md = open(src, 'rb').read()
    noms = set(noms_contenant(md, anc)) | {n_ for n_ in gt.noms if anc in n_}
    md2 = remplacer_crc(md, sorted(noms), anc, neuf).replace(anc.encode(), neuf.encode())
    assert len(md2) == len(md) and anc.encode() not in md2
    open(os.path.join(out, neuf + '.g4md'), 'wb').write(md2)
    shutil.copy(src[:-2] + 'mg', os.path.join(out, neuf + '.g4mg'))
    # portrait
    p = os.path.join(D, 'dx11', 'menu', '200_icon', '10_icon_chr', 'face', anc + '_l.g4tx')
    if os.path.exists(p):
        d = os.path.join(sortie, 'assets', 'menu', '200_icon', '10_icon_chr', 'face')
        from .icones_copies import ecrire_portrait, paires_textures
        # (16/11/2026) dessin d'origine recoloré comme les modifs ; la photo de la tête (web : photoIcone) dit où va chaque couleur
        fait = ecrire_portrait(p, os.path.join(d, neuf + '_l.g4tx'), demande.get('portrait'), anc, neuf,
                               paires_textures(open(os.path.join(D, 'dx11', *tx_rel.split('/')), 'rb').read(), tx, anc, neuf))
        if fait:
            rapport.append('portrait : ' + ('dessin d’origine recoloré comme la tête' if fait == 'dessin' else 'photo de la tête recolorée'))
        else:
            rapport.append('portrait : celui de %s (couleurs d’origine)' % orig['nom'])
    reg[cle] = e
    _sauver(cfg, reg)
    _ecrire_contenu(cfg, reg)
    rapport.insert(0, '%s : copie de %s (%s), code %s, carte 0x%08X copiée de 0x%08X' % (nom, orig['nom'], orig['code'], neuf, e['carte'], orig['carte']))
    if e.get('peau'):
        rapport.append('peau des bras et des jambes : #%s' % e['peau'])
    rapport.append('morphologie : %s' % (_libelle_corps(D, e['corps']) if e.get('corps') else "celle de l'original (%s)" % orig['nom']))
    return {'ok': True, 'dossier': sortie, 'code': neuf, 'rapport': rapport}


def _ecrire_contenu(cfg, reg):
    sortie = _sortie(cfg)
    entete = '# GÉNÉRÉ par l\'Atelier Inazuma (copies de personnages avec leur tête recolorée) : ne pas modifier à la main.\n'
    ch, cartes, look = [], [], []
    for cle, e in sorted(reg.items()):
        txt = []
        v = e.get('vetement')                       # (15/11/2026) copie de tenue : moteur/copies_tenues.py
        if v:
            if v['type'] == 'exmesh':                # accessoire (objet) : comme IECross / Inazuma Fantasy
                cellules = ['  exmesh_1 = 0x%08X                                 # crc32("%s") : objet recoloré' % (zlib.crc32(v['modele'].encode()), v['modele'])]
                look += ['# %s : objet %s recoloré' % (e['nom'], v['source']), '[[exmesh]]', 'model = %s' % _q(v['modele']),
                         'rows = [%s]' % ', '.join('[' + ', '.join(_q(x) if isinstance(x, str) else str(x) for x in r_) + ']' for r_ in v['rows']), '']
            else:
                cellules = ['  %s = 0x%08X                                    # crc32("%s") : tenue recolorée' % (v['type'], zlib.crc32(v['modele'].encode()), v['modele']),
                            '  force_kit = 1                                        # ses propres habits (comme Inazuma Fantasy, Michael)']
            cle_nom = 'model' if v['type'] == 'clothes' else 'id'
            r = ', '.join('{ ' + ', '.join('%s = %s' % (a, _q(b)) for a, b in x.items()) + ' }' if x else '{}' for x in v['rows']) if v['type'] != 'exmesh' else None
            if r is not None:
                look += ['# %s : %s %s recolorée' % (e['nom'], v['type'], v['source']), '[[%s]]' % v['type'], '%s = %s' % (cle_nom, _q(v['modele'])),
                         'from = %s' % _q(v['source']), 'rows = [%s]' % r, '']
        else:
            cellules = ['  head_mesh_path = "_face/%s/%s/%s.g4md"' % (e['serie'], e['code'], e['code'])]
            if e.get('corps'):       # (27/11) morphologie choisie : ligne CHARA_BODY_INFO du jeu (comme ChronicleDeluxe galaxy_shadows)
                cellules.insert(0, '  body = 0x%08X                                       # morphologie : %s' % (e['corps'], _libelle_corps(cfg['data_dir'], e['corps'])))
        if e.get('peau'):        # (26/11) chara_model col. 16 (comme InazumaFantasy, Enma) : bras, jambes, cou = texture blanche × cette couleur
            cellules.append('  skin_color = 0x%sFF                                # peau des bras et des jambes (comme la tête)' % e['peau'])
            if e.get('base') and couleurs_corps(cfg['data_dir'], e['base'])['parts_color']:
                # l'original prend sa peau dans CHARA_PARTS_COLOR (col. 8) : vidée, la copie n'a que skin_color (comme les 6 379 autres)
                cellules.append('  parts_color = 0                                      # (original : couleur CHARA_PARTS_COLOR)')
        for lang in ('en', 'fr'):
            txt += ['  [character.text.%s]' % lang, '  name = %s' % _q(e['nom']), '  short = %s' % _q(e['nom']),
                    '  description = %s' % _q(e.get('description') or ''), '']
        from . import stats as _st                   # (22/11) stats réglées dans « En attente de stats » (comme le mod Mukuro)
        st_perso, st_carte = _st.lignes_joueur(e.get('stats'))
        ch += ['[[character]]', 'name = "%s"                # copie de %s' % (cle, e.get('nom_origine', '')), 'based_on = "%s"' % e['base']] + st_perso + ['',
               '  [character.base]', '  id = 0x%08X' % e['id'], '  name = "%s"' % e['code'],
               '  name_text = 0x%08X' % e['nom_txt'], '  short_name_text = 0x%08X' % e['court_txt'], '  upper_name_text = 0x%08X' % e['nom_txt'],
               '  description_text = 0x%08X' % e['desc_txt'], '',
               '  [character.new_model]', '  id = 0x%08X' % e['modele'], '  from = "%s"' % e['base'],
               '  [character.new_model.cells]'] + cellules + [''] + txt + [
               '  [[character.cards]]', '  id = 0x%08X' % e['carte'], '  from = 0x%08X' % e['carte_origine']] + st_carte + _lignes_coups(e) + ['']
        cartes.append('"0x%08X"' % e['carte'])
    _ecrire(os.path.join(sortie, 'content', 'characters', 'mes_personnages.toml'), 'schema = "VRFW.character/2"\n' + entete + 'default_lang = "en"\n\n' + '\n'.join(ch))
    f_look = os.path.join(sortie, 'content', 'looks', 'mes_personnages.toml')
    if look:
        _ecrire(f_look, 'schema = "VRFW.look/2"\n' + entete + '\n' + '\n'.join(look))
    elif os.path.exists(f_look):
        os.remove(f_look)
    _ecrire(os.path.join(sortie, 'content', 'gacha', 'mes_personnages.toml'), 'schema = "VRFW.gacha/1"\n' + entete
            + '# ajoutés au tirage Kizuna de ChronicleDeluxe, comme Mukuro\n[[VRFW.GachaAdd]]\npool = "%s"\ncards = [%s]\n' % (POOL, ', '.join(cartes)))
    _ecrire(os.path.join(sortie, 'mod.toml'), '\n'.join([
        'id = "%s"' % MOD_ID, 'name = "Mes personnages"', 'prefix = "%s"' % MOD_ID, 'folder = "%s"' % MOD_ID,
        'version = "1.0.0"', 'author = "muku"',
        'description = "Copies de personnages avec leur tête recolorée, créées avec l\'Atelier Inazuma (les originaux ne changent pas). Au tirage Kizuna de ChronicleDeluxe."',
        'priority = 0', 'tags = ["Characters"]', 'updated = "%s"' % datetime.date.today().isoformat(),
        'requires = ["VRFW>=0.3.0", "ChronicleDeluxe"]',
        'optional = [%s]' % ', '.join('"%s"' % m for m in sorted({c.get('mod') for e in reg.values() for c in e.get('coups') or [] if c.get('mod')})),
        'conflicts = []', '']))      # optional : mes techniques / mes esprits choisis dans les techniques du joueur


def _lignes_coups(e):
    """(15/11/2026) techniques choisies au hub : moves = [...] remplace la liste de la carte d'origine (comme Mukuro) ; sans choix, rien
    (la carte garde celle de l'original, « from »)"""
    if not e.get('coups'):
        return []
    return ['  moves = ['] + ['    { move = 0x%08X, level = %d },%s# %s%s' % (c['move'], c['level'], ' ' * max(1, 22 - len(str(c['level']))),
                                                                    c.get('nom') or '', ' (%s)' % c['mod'] if c.get('mod') else '')
                               for c in e['coups']] + ['  ]']


def choisir_coups(cfg, cle, coups, catalogue_jeu, mes):
    """coups = [{move, level}] (9 au plus) ; None ou [] = celles de la carte d'origine"""
    from . import coups as C
    reg = registre(cfg)
    if cle not in reg:
        return {'ok': False, 'erreur': 'copie de personnage inconnue'}
    connus = {x['id']: x for x in catalogue_jeu}
    connus.update({x['id']: x for x in mes})
    try:
        L = C.nettoyer(coups, connus)
    except ValueError as ex:
        return {'ok': False, 'erreur': str(ex)}
    for c in L:
        x = connus[c['move']]
        c.update(code=x['code'], nom=x['nom'], **({'mod': x['mod']} if x.get('mod') else {}))
    if L:
        reg[cle]['coups'] = L
    else:
        reg[cle].pop('coups', None)
    _sauver(cfg, reg); _ecrire_contenu(cfg, reg)
    e = reg[cle]
    return {'ok': True, 'dossier': _sortie(cfg), 'rapport': ['%s : %s' % (e['nom'], '%d techniques choisies' % len(L) if L else "techniques de la carte d'origine (%s)" % e.get('nom_origine', ''))]
            + ['  niv. %d : %s' % (c['level'], c['nom']) for c in L]}


def retirer(cfg, cle):
    reg = registre(cfg)
    e = reg.pop(cle, None)
    if not e:
        return {'ok': False, 'erreur': 'copie inconnue'}
    d = os.path.join(_sortie(cfg), 'assets', 'chr', '_item' if e['vetement']['type'] == 'exmesh' else '_uniform', e['vetement']['modele']) if e.get('vetement') \
        else os.path.join(_sortie(cfg), 'assets', 'chr', '_face', e['serie'], e['code'])
    g = os.path.join(_sortie(cfg), '_retires', datetime.datetime.now().strftime('%Y%m%d_%H%M%S'))
    os.makedirs(g, exist_ok=True)
    p = os.path.join(_sortie(cfg), 'assets', 'menu', '200_icon', '10_icon_chr', 'face', e['code'] + '_l.g4tx')
    # (23/11) fiche pour la Corbeille (« Restaurer ») : son entrée du registre et où remettre chaque fichier
    fiche = {'mod': MOD_ID, 'genre': 'personnages', 'code': e['code'], 'nom': e.get('nom') or cle, 'cle': cle, 'entree': e,
             'date': datetime.datetime.now().isoformat(timespec='seconds'),
             'fichiers': {e['code']: os.path.relpath(d, _sortie(cfg)).replace(os.sep, '/'),
                          e['code'] + '_l.g4tx': os.path.relpath(p, _sortie(cfg)).replace(os.sep, '/')}}
    json.dump(fiche, open(os.path.join(g, '_retire.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    if os.path.isdir(d):
        shutil.move(d, os.path.join(g, e['code']))
    if os.path.exists(p):
        shutil.move(p, os.path.join(g, e['code'] + '_l.g4tx'))
    _sauver(cfg, reg); _ecrire_contenu(cfg, reg)
    return {'ok': True}


def contenu(cfg):
    return [dict(e, cle=k) for k, e in registre(cfg).items()]
