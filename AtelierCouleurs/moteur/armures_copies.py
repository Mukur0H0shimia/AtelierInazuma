"""(15/11/2026) COPIE D'ARMURE pour une de MES COPIES D'ESPRIT (mod MesEsprits) : une armure du jeu recolorée devient la
forme en armure de cette copie. L'armure d'origine ne change pas.

Fait comme l'armure de Victoria d'Inazuma Fantasy et celle de Michael (mods/Mukuro), LU dans leurs fichiers :
- texture : assets/chr/_armd/<modèle neuf>/<modèle neuf>_10.g4tx, avec les NOMS D'IMAGES DU MODÈLE D'ORIGINE (comme les
  maillots : u030701_10.g4tx contient « u000501_20 ») : les maillages restent ceux du jeu ;
- look VRFW.look/2 : [[clothes]] model = neuf, from = l'armure du jeu (CHARA_PARTS_CLOTHES_MODEL, ex. « ka000101 », 1 ligne),
  rows = [{ upper_texture = … }] (même écriture que MesMaillots, qui marche en jeu) ;
- personnage de la forme en armure : based_on = "c11600010", battle = false, clothes = crc32(neuf), shoes = 0, gloves = 0,
  force_kit = 1 (comme Inazuma Fantasy et Michael) ;
- [[aura_command]] « was_mesesprits_<copie> » from = l'armure du jeu de l'esprit d'origine (aura_skill_config : colonne 7 =
  crc32(esprit), colonne 13 = carte de la forme en armure), sinon « was00220 » (comme Inazuma Fantasy pour un esprit sans
  armure) ; cells aura_chara = crc32(code de ma copie), chara_param = la carte de la forme en armure ;
- transformation CharacterReforged (addons/CharacterReforged/content/transforms) : kind = "armour", source = la technique
  de ma copie d'esprit (comme Victoria et Michael) ;
- scène de mise en armure : si ma copie n'a pas de scène ev81 copiée, celle de l'armure « from » avec
  tag_words / snd_tag_words <ma copie> = <esprit de cette armure> (comme Michael : k002090 = k000220 sur ev81_00030).
"""
import os, re, glob, json, zlib, datetime, struct, shutil, tempfile, multiprocessing, tomllib
from . import cfgbin, retouches, esprits
from .g4 import images
from .personnages import _dernier
from .export import _ecrire, _q
from .esprits import slug, _png, _env_des_autres, _codes_sons

MOD_ID = esprits.MOD_ID                          # MesEsprits


def _sortie(cfg):
    return os.path.join(cfg['outil_dir'], 'sortie', MOD_ID)


def registre(cfg):
    f = os.path.join(_sortie(cfg), 'outil_armures.json')
    return json.load(open(f, encoding='utf-8')) if os.path.exists(f) else {}


def copies_esprits(cfg):
    """mes copies d'esprit (pas les totems) : [{code, nom, key, base}]"""
    return [{'code': k, 'nom': v['nom'], 'key': v['key'], 'base': v['base'], 'nom_base': v.get('nom_base')}
            for k, v in sorted(esprits.registre(_sortie(cfg)).items()) if v.get('dossier') == '_keshin']


def armure_du_jeu(data_dir, esprit):
    """1re armure (« was… ») du jeu de cet esprit : aura_skill_config, colonne 7 = crc32(esprit)"""
    c = os.path.join(data_dir, 'common')
    crc = zlib.crc32(esprit.encode())
    for k, v in cfgbin.lire(open(_dernier(os.path.join(c, 'gamedata', 'skill', 'aura_skill_config_*.cfg.bin')), 'rb').read()):
        if len(v) > 13 and isinstance(v[1], str) and v[1].startswith('was') and isinstance(v[7], int) and (v[7] & 0xFFFFFFFF) == crc:
            return v[1]
    return None


def esprit_et_scene(data_dir, was):
    """esprit (colonne 7) et scène de mise en armure (colonne 12 = crc32 de la scène, LU : was00220 -> ev81_00030,
    was00100 -> ev81_00040, les scènes que prennent Michael et Inazuma Fantasy) de cette armure du jeu"""
    c = os.path.join(data_dir, 'common')
    codes = {zlib.crc32(d.encode()): d for d in os.listdir(os.path.join(c, 'chr', '_keshin'))}
    scenes = {zlib.crc32(s.encode()): s for s in os.listdir(os.path.join(c, 'event', 'ev81'))}
    for k, v in cfgbin.lire(open(_dernier(os.path.join(c, 'gamedata', 'skill', 'aura_skill_config_*.cfg.bin')), 'rb').read()):
        if len(v) > 12 and v[1] == was and isinstance(v[7], int):
            return codes.get(v[7] & 0xFFFFFFFF), scenes.get(v[12] & 0xFFFFFFFF) if isinstance(v[12], int) else None
    return None, None


def _modele_libre(cfg, reg):
    pris = {e['modele'] for e in reg.values()}
    parts = sorted(glob.glob(os.path.join(cfg['data_dir'], 'common', 'gamedata', 'character', 'chara_parts_*.cfg.bin')))
    txt = open(parts[-1], 'rb').read() if parts else b''
    mods = os.path.join(cfg['jeu_dir'], 'mods')
    for n in range(1, 10000):
        m = 'kz%06d' % n
        if m not in pris and m.encode() not in txt and not glob.glob(os.path.join(mods, '*', 'assets', 'chr', '_armd', m)):
            return m
    raise ValueError('plus de nom libre')


def exporter(cfg, demande, entree):
    """demande = {code (armure du jeu), esprit (code de ma copie), nom, textures {nom: data URL}}"""
    textures = demande.get('textures') or {}
    if not textures:
        return {'ok': False, 'erreur': 'Rien n’est modifié : recolore d’abord l’armure.'}
    copies = {c['code']: c for c in copies_esprits(cfg)}
    if not copies:
        return {'ok': False, 'erreur': 'Aucune copie d’esprit guerrier : crée-en d’abord une (onglet Esprits guerriers, « Créer le mod »).'}
    cible = copies.get(demande.get('esprit'))
    if not cible:
        return {'ok': False, 'erreur': 'Choisis la copie d’esprit qui portera cette armure.'}
    armure = entree['code']                                    # ka……, clothes model du jeu
    D = cfg['data_dir']; sortie = _sortie(cfg); reg = registre(cfg)
    e = reg.get(cible['code']) or {}
    if not e:
        pris = esprits_ids_pris(cfg)
        modele = _modele_libre(cfg, reg)
        e = {'modele': modele, 'id': zlib.crc32(('evt_' + modele).encode()), 'id_modele': zlib.crc32(('evt_%s_model' % modele).encode()),
             'carte': _id('%s.armure_%s_carte' % (MOD_ID, modele), pris), 'nom_txt': _id('%s.armure_%s_nom' % (MOD_ID, modele), pris),
             'desc_txt': _id('%s.armure_%s_desc' % (MOD_ID, modele), pris)}
        for k in ('id', 'id_modele'):
            if e[k] in pris:
                return {'ok': False, 'erreur': 'id déjà utilisé (%s) : réessaie' % k}
    was = armure_du_jeu(D, cible['base']) or 'was00220'
    e.update(armure=armure, esprit=cible['code'], cle_esprit=cible['key'], nom=str(demande.get('nom') or (cible['nom'] + ' (armure)')),
             was=was, key='was_mesesprits_' + slug(cible['nom']), date=datetime.datetime.now().isoformat(timespec='seconds'))
    # texture : mêmes noms d'images que l'armure du jeu (ses maillages sont gardés)
    rel = retouches.fichier_texture(cfg, entree)
    gt = images.G4TX(open(os.path.join(D, 'dx11', *rel.split('/')), 'rb').read())
    rempl, rapport, tmp = {}, [], tempfile.mkdtemp()
    try:
        with images.pool_encodage() as pool:
            for n_, url in textures.items():
                if n_ not in gt.noms:
                    return {'ok': False, 'erreur': '%s n’est pas dans %s' % (n_, rel)}
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
    d = os.path.join(sortie, 'assets', 'chr', '_armd', e['modele']); os.makedirs(d, exist_ok=True)
    open(os.path.join(d, e['modele'] + '_10.g4tx'), 'wb').write(gt.reconstruire(rempl))
    reg[cible['code']] = e
    os.makedirs(sortie, exist_ok=True)
    json.dump(reg, open(os.path.join(sortie, 'outil_armures.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    ecrire_vrfw(cfg, reg)
    rapport.insert(0, 'armure %s recolorée → forme en armure de « %s » (%s), modèle %s, technique %s (copiée de %s)'
                   % (armure, cible['nom'], cible['code'], e['modele'], e['key'], was))
    return {'ok': True, 'dossier': sortie, 'rapport': rapport}


def esprits_ids_pris(cfg):
    from .copies_persos import _ids_pris
    return _ids_pris(cfg)


def _id(graine, pris):
    k = 0
    while True:
        v = zlib.crc32(('%s#%d' % (graine, k) if k else graine).encode())
        if v not in pris and v:
            pris.add(v); return v
        k += 1


def ecrire_vrfw(cfg, reg):
    sortie = _sortie(cfg)
    entete = '# Écrit par l\'Atelier Inazuma : armures de mes copies d\'esprits (réécrit à chaque export).\n'
    ch, look, tech, txt, tr, env, par_scene = [], [], [], [], [], [], {}
    reg_esprits = esprits.registre(sortie)
    for k, (code, e) in enumerate(sorted(reg.items())):
        m = e['modele']
        look += ['# %s : armure %s recolorée' % (e['nom'], e['armure']), '[[clothes]]', 'model = %s' % _q(m), 'from = %s' % _q(e['armure']),
                 'rows = [{ upper_texture = %s }]' % _q('_armd/%s/%s_10.g4tx' % (m, m)), '']
        ch += ['[[character]]', 'name = %s' % _q('mesesprits_armure_' + m), 'based_on = "c11600010"', 'battle = false', '',
               '  [character.base]', '  id = 0x%08X                                         # crc32("evt_%s")' % (e['id'], m), '  name = %s' % _q('evt_' + m), '',
               '  [character.new_model]', '  id = 0x%08X' % e['id_modele'], '  from = "c11600010"',
               '  [character.new_model.cells]', '  clothes = 0x%08X                                    # crc32("%s")' % (zlib.crc32(m.encode()), m),
               '  shoes = 0', '  gloves = 0', '  force_kit = 1', '', '  [[character.cards]]', '  id = 0x%08X' % e['carte'], '']
        tech += ['# forme en armure de %s (%s)' % (e['nom'], code), '[[aura_command]]', 'key = %s' % _q(e['key']),
                 'id = 0x%08X                                  # crc32(key)' % zlib.crc32(e['key'].encode()), 'from = %s' % _q(e['was']),
                 'cells = { name_text = 0x%08X, desc_text = 0x%08X, aura_chara = 0x%08X, chara_param = 0x%08X, order = %d }'
                 % (e['nom_txt'], e['desc_txt'], zlib.crc32(code.encode()), e['carte'], 190 + k), 'charas = []', '']
        for nid, variant, texte, genre in ((e['nom_txt'], None, e['nom'], 'noun'), (e['nom_txt'], 11, e['nom'], 'noun'), (e['desc_txt'], None, e['nom'], 'text')):
            txt += ['[[row]]', 'id = 0x%08X  # %s armure %s' % (nid, MOD_ID, m), 'kind = "%s"' % genre] + (['variant = %d' % variant] if variant else []) \
                + ['%s = %s' % (l, _q(texte)) for l in ('de', 'en', 'es', 'fr', 'it', 'ja', 'pt', 'zh_hans', 'zh_hant')] + ['']
        tr += ['[[transform]]', 'name = %s' % _q(e['key']), 'kind = "armour"', 'source = { spirit = %s }' % _q(e['cle_esprit']),
               'techniques = { keep_spirit = true }', 'trigger = { cpu = true }', 'stats = { mode = "own" }', 'look = { no_uniform = true }',
               'audio = { voice = "wearer" }', 'ui = { plate = "armour" }',
               'text = { de = { tag = "Rüstung" }, en = { tag = "Armour" }, es = { tag = "Armadura" }, fr = { tag = "Armure" }, it = { tag = "Armatura" }, ja = { tag = "アームド" }, pt = { tag = "Armadura" }, zh_hans = { tag = "化身武装" }, zh_hant = { tag = "化身武裝" } }', '']
        # scène de mise en armure = celle de l'armure « from » ; ma copie y prend les animations et sons de l'esprit de cette
        # armure (comme Michael : k002090 = "k000220" sur ev81_00030), sauf si ses propres animations y sont déjà copiées
        k_from, scene = esprit_et_scene(cfg['data_dir'], e['was'])
        if scene and k_from and scene not in ((reg_esprits.get(code) or {}).get('scenes') or []):
            par_scene.setdefault(scene, {})[code] = k_from
    # une seule entrée par scène (VRFW n'en garde qu'une) : les mots des autres mods sont gardés ; une scène déjà écrite par
    # mes_esprits.toml (animations copiées d'une de mes copies) n'est pas réécrite ici
    deja = {s for v in reg_esprits.values() for s in (v.get('scenes') or [])}
    for s, mots in sorted(par_scene.items()):
        if s in deja:
            continue
        tags, snd = _env_des_autres(cfg, s)
        snd = dict({c: c for c in _codes_sons(cfg)}, **snd)
        tags.update(mots); snd.update(mots)
        f = lambda dd: '{ ' + ', '.join('%s = %s' % (a, _q(b)) for a, b in sorted(dd.items())) + ' }'
        env += ['# mise en armure de %s : scène de l’armure d’origine (comme Michael)' % ', '.join(sorted(mots)), '[[event_env]]', 'event = %s' % _q(s),
                'tag_words = { set = %s }' % f(tags), 'snd_tag_words = { set = %s }' % f(snd), '']
    _ecrire(os.path.join(sortie, 'content', 'looks', 'mes_armures.toml'), 'schema = "VRFW.look/2"\n' + entete + '\n' + '\n'.join(look))
    _ecrire(os.path.join(sortie, 'content', 'characters', 'mes_armures.toml'), 'schema = "VRFW.character/2"\n' + entete + 'default_lang = "en"\n\n' + '\n'.join(ch))
    _ecrire(os.path.join(sortie, 'content', 'techniques', 'mes_armures.toml'), 'schema = "VRFW.technique/3"\n' + entete + '\n' + '\n'.join(tech + env))
    _ecrire(os.path.join(sortie, 'text', 'rows', 'mes_armures.toml'), 'schema = "VRFW.text/2"\ntable = "skill_text"\n' + entete + '\n' + '\n'.join(txt))
    _ecrire(os.path.join(sortie, 'addons', 'CharacterReforged', 'content', 'transforms', 'mes_armures.toml'), 'schema = "VRFW.transform/2"\n' + entete + '\n' + '\n'.join(tr))
    mt = os.path.join(sortie, 'mod.toml')                    # CharacterReforged : la forme en armure passe par ses « transforms »
    if os.path.exists(mt):
        t = open(mt, encoding='utf-8').read()
        if '"CharacterReforged"' not in t:
            t = re.sub(r'optional = \[(.*?)\]', lambda mm: 'optional = [%s]' % ', '.join(x for x in [mm.group(1).strip(), '"CharacterReforged"'] if x), t, count=1)
            open(mt, 'w', encoding='utf-8').write(t)
    for f in glob.glob(os.path.join(sortie, '**', 'mes_armures.toml'), recursive=True):
        tomllib.load(open(f, 'rb'))


def contenu(cfg):
    return [dict(e, cle=k) for k, e in registre(cfg).items()]
