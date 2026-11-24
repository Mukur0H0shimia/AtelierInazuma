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
    """1re armure du jeu de cet esprit : aura_skill_config, colonne 7 = crc32(esprit). (23/11, retour de muku : « on voit
    l'esprit guerrier trop tôt » dans l'armure de Pégase (couleurs)) LU : l'armure de Pégase est « wao00010 » (scène
    ev81_00010), pas une « was… » ; on ne cherchait que « was » -> Reine sorcière (was00220) par défaut, dont les animations
    empruntées laissaient les ailes de Pégase visibles derrière le joueur. Ordre : was, puis wao / wad / wak."""
    c = os.path.join(data_dir, 'common')
    crc = zlib.crc32(esprit.encode())
    trouves = []
    for k, v in cfgbin.lire(open(_dernier(os.path.join(c, 'gamedata', 'skill', 'aura_skill_config_*.cfg.bin')), 'rb').read()):
        if len(v) > 13 and isinstance(v[1], str) and v[1][:3] in ('was', 'wao', 'wad', 'wak') and isinstance(v[7], int) and (v[7] & 0xFFFFFFFF) == crc:
            trouves.append(v[1])
    trouves.sort(key=lambda w: ('was', 'wao', 'wad', 'wak').index(w[:3]))
    return trouves[0] if trouves else None


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


_LIGNES_CR = {}


def lignes_par_corps(cfg, armure):
    """(23/11, un joueur : « l'esprit n'a pas l'option d'armure » sur son joueur) une armure a UN MODÈLE PAR GROUPE DE CORPS
    (3e colonne des lignes, 0 à 16) ; CharacterReforged ne propose l'armure qu'aux joueurs dont le corps en a un (LU :
    CharacterReforged/content/transforms/armour_rules.toml « every player whose body has a mesh for the armour »). Nos copies
    écrivaient `from = "<armure>"` avec UNE seule ligne (`rows = [{ upper_texture }]`) : la copie n'avait que le corps 0
    (celui d'Harper Evans, où elle marchait). Lignes complètes = celles que CharacterReforged déclare pour l'armure d'origine
    (content/looks/armour_clothes.toml, 17 corps pour ka000101), comme l'armure de Michael (Mukuro). [] si introuvables."""
    if armure in _LIGNES_CR:
        return _LIGNES_CR[armure]
    out = []
    for f in [os.path.join(cfg.get('jeu_dir') or '', 'mods', 'CharacterReforged', 'content', 'looks', 'armour_clothes.toml')]:
        try:
            t = tomllib.load(open(f, 'rb'))
        except (OSError, ValueError):
            continue
        for c in t.get('clothes') or []:
            if c.get('model') == armure and isinstance(c.get('rows'), list):
                out = [list(r) for r in c['rows'] if isinstance(r, list) and len(r) > 2]
    _LIGNES_CR[armure] = out
    return out


def ecrire_vrfw(cfg, reg):
    sortie = _sortie(cfg)
    entete = '# Écrit par l\'Atelier Inazuma : armures de mes copies d\'esprits (réécrit à chaque export).\n'
    ch, look, tech, txt, tr, env, par_scene = [], [], [], [], [], [], {}
    reg_esprits = esprits.registre(sortie)
    pris = set()                                     # (23/11) scènes de mise en armure à part (esprits.copier_scene)
    telops_a = ['schema = "VRFW.telop_list/2"', entete.strip(), "# bannières « ARMED » faites dans l'éditeur de bannières (une par armure)", '']
    for k, (code, e) in enumerate(sorted(reg.items())):
        m = e['modele']
        # (23/11) armure faite avant la correction (« was00220 » par défaut alors que l'esprit d'origine a la sienne, ex.
        # Pégase -> wao00010) : celle de l'esprit d'origine
        base_ = (reg_esprits.get(code) or {}).get('base')
        w_ = armure_du_jeu(cfg['data_dir'], base_) if base_ else None
        if w_ and e.get('was') == 'was00220' and w_ != 'was00220':
            e['was'] = w_
        tex = '_armd/%s/%s_10.g4tx' % (m, m)
        lignes = lignes_par_corps(cfg, e['armure'])
        if lignes:                       # une ligne par groupe de corps : modèles de l'armure d'origine, notre texture
            look += ['# %s : armure %s recolorée, un modèle par groupe de corps (lignes de CharacterReforged)' % (e['nom'], e['armure']),
                     '[[clothes]]', 'model = %s' % _q(m), 'rows = [']
            look += ['  [%s],' % ', '.join(_q(v) if isinstance(v, str) else str(v) for v in ([r[0], tex] + r[2:])) for r in lignes]
            look += [']', '']
        else:
            look += ['# %s : armure %s recolorée' % (e['nom'], e['armure']), '[[clothes]]', 'model = %s' % _q(m), 'from = %s' % _q(e['armure']),
                     'rows = [{ upper_texture = %s }]' % _q(tex), '']
        ch += ['[[character]]', 'name = %s' % _q('mesesprits_armure_' + m), 'based_on = "c11600010"', 'battle = false', '',
               '  [character.base]', '  id = 0x%08X                                         # crc32("evt_%s")' % (e['id'], m), '  name = %s' % _q('evt_' + m), '',
               '  [character.new_model]', '  id = 0x%08X' % e['id_modele'], '  from = "c11600010"',
               '  [character.new_model.cells]', '  clothes = 0x%08X                                    # crc32("%s")' % (zlib.crc32(m.encode()), m),
               '  shoes = 0', '  gloves = 0', '  force_kit = 1', '', '  [[character.cards]]', '  id = 0x%08X' % e['carte'], '']
        # (23/11, demande de muku) MISE EN ARMURE dans SA scène : copie de celle de l'armure « from » sous un numéro neuf
        # (comme ZanUltimateMod) ; ma copie y prend ses animations copiées, sinon celles de l'esprit de cette armure (comme
        # Michael : k002090 = "k000220") ; plus de [[event_env]] sur la scène du jeu partagée (conflits avec Mukuro…)
        k_from, scene = esprit_et_scene(cfg['data_dir'], e['was'])
        try:                                         # (23/11) mise en armure choisie dans la fiche, ou celle de l'élément réglé
            pl = plan_mise(cfg, e, code)
        except Exception as ex:
            print('mise en armure :', ex); pl = None
        if pl and pl.get('scene') and pl.get('esprit'):
            scene, k_from = pl['scene'], pl['esprit']
        cel_ev = ''
        if scene and k_from:
            ev = esprits.id_scene_copie(cfg, scene[:4], code, pris)
            if esprits.copier_scene(cfg, sortie, scene, ev):
                cel_ev = ', event = 0x%08X' % zlib.crc32(ev.encode())
                if banniere_armee_faite(cfg, code):      # (23/11) bannière ARMED faite dans l'éditeur : la scène copiée la cite
                    citer_banniere_armee(sortie, ev, code)
                    telops_a += ['[[telop]]', 'id = %s' % _q(id_banniere_armee(code)), 'from = "aura_armed01"', '']
                mot = code if scene in ((reg_esprits.get(code) or {}).get('scenes') or []) and k_from == base_ else k_from
                son = (base_ or k_from) if mot == code else mot      # sons : ceux de l'original (la copie n'en a pas)
                env += esprits.env_scene_copie(cfg, ev, scene, {code: mot}, {code: son}, 'mise en armure de %s (%s)' % (e['nom'], code))
        tech += ['# forme en armure de %s (%s)' % (e['nom'], code), '[[aura_command]]', 'key = %s' % _q(e['key']),
                 'id = 0x%08X                                  # crc32(key)' % zlib.crc32(e['key'].encode()), 'from = %s' % _q(e['was']),
                 'cells = { name_text = 0x%08X, desc_text = 0x%08X, aura_chara = 0x%08X, chara_param = 0x%08X%s, order = %d }'
                 % (e['nom_txt'], e['desc_txt'], zlib.crc32(code.encode()), e['carte'], cel_ev + _cel_stats(cfg, e), 190 + k), 'charas = []']
        ef = e.get('effets') or {}                   # (23/11) bonus / effet unique choisis dans la fiche (lignes brutes du jeu)
        if 'bonus' in ef:
            tech.append('effects = %s' % _lignes_ef(ef['bonus']))
        if 'uniques' in ef:
            tech.append('unique_effects = %s' % _lignes_ef(ef['uniques']))
        tech.append('')
        for nid, variant, texte, genre in ((e['nom_txt'], None, e['nom'], 'noun'), (e['nom_txt'], 11, e['nom'], 'noun'), (e['desc_txt'], None, e['nom'], 'text')):
            txt += ['[[row]]', 'id = 0x%08X  # %s armure %s' % (nid, MOD_ID, m), 'kind = "%s"' % genre] + (['variant = %d' % variant] if variant else []) \
                + ['%s = %s' % (l, _q(texte)) for l in ('de', 'en', 'es', 'fr', 'it', 'ja', 'pt', 'zh_hans', 'zh_hant')] + ['']
        tr += ['[[transform]]', 'name = %s' % _q(e['key']), 'kind = "armour"', 'source = { spirit = %s }' % _q(e['cle_esprit']),
               'techniques = { keep_spirit = true }', 'trigger = { cpu = true }', 'stats = { mode = "own" }', 'look = { no_uniform = true }',
               'audio = { voice = "wearer" }', 'ui = { plate = "armour" }',
               'text = { de = { tag = "Rüstung" }, en = { tag = "Armour" }, es = { tag = "Armadura" }, fr = { tag = "Armure" }, it = { tag = "Armatura" }, ja = { tag = "アームド" }, pt = { tag = "Armadura" }, zh_hans = { tag = "化身武装" }, zh_hant = { tag = "化身武裝" } }', '']
        # (23/11) plus de réglage de la scène partagée : voir la scène à part plus haut
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
    _ecrire(os.path.join(sortie, 'content', 'telops', 'any', 'armures.toml'), '\n'.join(telops_a))
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


# ------------------------------------------------------------------ (23/11, demande de muku : « les armures maintenant »)
# FICHE D'ARMURE comme celle des esprits : l'armure du jeu a SA ligne AURA_CMD_INFO (wao00010, was00220…) : puissance, élément,
# bonus / effet unique (AURA_CMD_EFFECT / UNIQUE_EFFECT) et colonne 12 = scène de MISE EN ARMURE. LU : ev81_00010 = Pégase
# (k000010, k000330) ; ev81_00020…60 = une par élément (wind 20, forest 30, fire 40, mountain 50, void 60 ; was00220 forêt ->
# ev81_00030, was00100 feu -> ev81_00040), chacune avec les gestes de plusieurs esprits (comme les invocations ev80).
SCENES_ARMURE = {'wind': 'ev81_00020', 'forest': 'ev81_00030', 'fire': 'ev81_00040', 'mountain': 'ev81_00050', 'void': 'ev81_00060'}


def base_esprit(cfg, code):
    """esprit d'origine de ma copie d'esprit (k000010…)"""
    return (esprits.registre(_sortie(cfg)).get(code) or {}).get('base')


def mises_possibles(cfg, e, code):
    """toutes les mises en armure : [{scene, esprit, element, os_ok}] (os_ok : tous ses os animés existent chez l'esprit
    d'origine de ma copie ; les autres sont proposées aussi, comme pour les invocations)"""
    from . import coups
    dd, anc = cfg['data_dir'], base_esprit(cfg, code)
    sq = coups.os_squelette(dd, anc) if anc else set()
    el_de = {v: k for k, v in SCENES_ARMURE.items()}
    out = []
    for scene in ['ev81_00010'] + list(SCENES_ARMURE.values()):
        L = []
        for k in coups.esprits_de_scene(dd, scene):
            if k.startswith('k'):
                ok = k == anc or bool(sq and not (coups.os_animes(dd, scene, k) - sq))
                L.append({'scene': scene, 'esprit': k, 'element': el_de.get(scene, ''), 'os_ok': ok})
        out += sorted(L, key=lambda x: not x['os_ok'])
    return out


def plan_mise(cfg, e, code):
    """mise en armure de ma copie : choisie dans l'Atelier, sinon celle de l'élément réglé s'il a changé (un esprit de
    cette scène dont tous les os existent), sinon None (celle de l'armure d'origine)"""
    from . import coups, stats as st
    m = e.get('mise') or {}
    if m.get('choisie'):
        return m
    el = (e.get('stats') or {}).get('element')
    el0 = st.jeu_esprit(cfg['data_dir'], e['was']).get('element')
    if el not in SCENES_ARMURE or el == el0:
        return None
    scene, dd, anc = SCENES_ARMURE[el], cfg['data_dir'], base_esprit(cfg, code)
    sq = coups.os_squelette(dd, anc) if anc else set()
    meilleur = None
    for k in coups.esprits_de_scene(dd, scene):
        if not k.startswith('k'):
            continue
        if k == anc:
            meilleur = (float('inf'), k)
            break
        a = coups.os_animes(dd, scene, k)
        if sq and not (a - sq) and (meilleur is None or len(a) > meilleur[0]):
            meilleur = (len(a), k)
    if not meilleur:
        return None
    return {'scene': scene, 'esprit': meilleur[1], 'element': el}


def _cel_stats(cfg, e):
    """(23/11) puissance / élément réglés dans la fiche : colonnes de AURA_CMD_INFO (comme les esprits)"""
    if not e.get('stats'):
        return ''
    from . import stats as st
    return st.cellules_esprit(e['stats'], st.jeu_esprit(cfg['data_dir'], e['was']))


def _lignes_ef(L):
    from .effets_esprits import lignes_toml
    return lignes_toml(L)



# ------------------------------------------------------------------ (23/11, muku : « tu n'as pas fait les bannières des totems et
# des armures ») BANNIÈRE « ARMED » d'une armure. LU : la scène de mise en armure (ev81_*.cfg.bin, evt) affiche
# « soccer10_01_<CHARA_ID> » (la bannière de l'esprit : celle de ma copie) PUIS « soccer10_01_aura_armed01 », la bannière
# ARMED COMMUNE à toutes les armures (7 fois le nom en clair, aucun crc). Ma copie a sa scène à part : on y remplace ce nom par
# « soccer10_01_aura_<code de ma copie> » (même longueur : 12 lettres -> fichier identique au reste près) et [[telop]] id =
# aura_<code>, from = aura_armed01, image = celle de l'éditeur. Sans bannière faite : la bannière ARMED du jeu reste.
def id_banniere_armee(code):
    i = 'aura_' + code
    return i if len(i) == len('aura_armed01') else i[:12].ljust(12, '0')


def banniere_armee_faite(cfg, code):
    return os.path.exists(os.path.join(_sortie(cfg), 'content', 'telops', 'any', id_banniere_armee(code) + '.png'))


def citer_banniere_armee(sortie, ev, code):
    f = os.path.join(sortie, 'assets', 'event_cfg', 'evt', ev + '.cfg.bin')
    if not os.path.exists(f):
        return False
    b = open(f, 'rb').read()
    a, n = b'soccer10_01_aura_armed01', ('soccer10_01_' + id_banniere_armee(code)).encode()
    if len(a) != len(n) or a not in b:
        return False
    open(f, 'wb').write(b.replace(a, n))
    return True
