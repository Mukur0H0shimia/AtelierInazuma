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
from .esprits import remplacer_crc, noms_contenant, slug, _png
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
    reg = registre(cfg); cle = slug(nom)
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
        for lang in ('en', 'fr'):
            txt += ['  [character.text.%s]' % lang, '  name = %s' % _q(e['nom']), '  short = %s' % _q(e['nom']),
                    '  description = %s' % _q(e.get('description') or ''), '']
        ch += ['[[character]]', 'name = "%s"                # copie de %s' % (cle, e.get('nom_origine', '')), 'based_on = "%s"' % e['base'], '',
               '  [character.base]', '  id = 0x%08X' % e['id'], '  name = "%s"' % e['code'],
               '  name_text = 0x%08X' % e['nom_txt'], '  short_name_text = 0x%08X' % e['court_txt'], '  upper_name_text = 0x%08X' % e['nom_txt'],
               '  description_text = 0x%08X' % e['desc_txt'], '',
               '  [character.new_model]', '  id = 0x%08X' % e['modele'], '  from = "%s"' % e['base'],
               '  [character.new_model.cells]'] + cellules + [''] + txt + [
               '  [[character.cards]]', '  id = 0x%08X' % e['carte'], '  from = 0x%08X' % e['carte_origine']] + _lignes_coups(e) + ['']
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
    if os.path.isdir(d):
        shutil.move(d, os.path.join(g, e['code']))
    p = os.path.join(_sortie(cfg), 'assets', 'menu', '200_icon', '10_icon_chr', 'face', e['code'] + '_l.g4tx')
    if os.path.exists(p):
        shutil.move(p, os.path.join(g, e['code'] + '_l.g4tx'))
    _sauver(cfg, reg); _ecrire_contenu(cfg, reg)
    return {'ok': True}


def contenu(cfg):
    return [dict(e, cle=k) for k, e in registre(cfg).items()]
