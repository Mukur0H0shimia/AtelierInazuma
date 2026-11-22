"""Copies d'esprits guerriers et de totems recolorés -> mod VRFW « MesEsprits ». L'ORIGINAL NE CHANGE JAMAIS.

Méthode = celle de Michael (k002090, copie de Victoria k002010, vérifiée en jeu, mod Mukuro) :
- code neuf de même longueur : esprits k0029NN (chr/_keshin), totems a0009NN (chr/_waza), libre dans le jeu, les mods et l'outil ;
- fichiers du modèle copiés et renommés (noms + crc32 + ordres triés) : .g4pkm (paquet G4PK, squelette G4SK, modèle G4MD),
  .g4mg (tel quel), .objbin, _p010.g4pk (s'il existe), .g4tx (textures retouchées réencodées en BC7, mêmes mips, renommées) ;
- scènes : chaque paquet d'animation <scène>_<ANC>_*.g4pk du jeu (invocation ev80 / ev83, cinématiques de ses techniques)
  est copié en <scène>_<NEUF>_*.g4pk (noms + crc32 des nœuds du modèle renommés) ;
- icône de menu (aura_fs / aura_soul) copiée sous le code neuf ;
- VRFW : [[character]] (code neuf, modèle neuf), [[aura_command]] (copie de la technique d'invocation, aura_chara = code neuf),
  [[event_env]] des scènes (tag_words = le code neuf lui-même, en gardant ceux des autres mods ; snd_tag_words = sons de l'original),
  textes (skill_text), vente dans la boutique d'entraînement d'Inazuma Fantasy.
"""
import os, re, json, glob, base64, datetime, struct, zlib, multiprocessing, tempfile, tomllib, unicodedata, shutil
from . import g4                           # met l'Atelier Maillots dans le chemin d'import
from lib import images, bustes             # noqa: E402  (Atelier Maillots)
from .export import _ecrire, _q

MOD_ID = 'MesEsprits'
PREFIXES = {'_keshin': 'k0029', '_waza': 'a0009'}
ICONES = {'_keshin': 'aura_fs', '_waza': 'aura_soul'}


def slug(t):
    t = unicodedata.normalize('NFD', t).encode('ascii', 'ignore').decode().lower()
    return re.sub(r'[^a-z0-9]+', '_', t).strip('_')[:24] or 'copie'


# ------------------------------------------------------------------ renommage (généralisé depuis Mukuro_atelier/ecrire_michael.py)
def remplacer_crc(b, noms, anc, neuf):
    """remplace les crc32 de chaque nom contenant anc par celui du nom avec neuf"""
    b = bytearray(b)
    for n in noms:
        a = struct.pack('<I', zlib.crc32(n.encode())); z = struct.pack('<I', zlib.crc32(n.replace(anc, neuf).encode()))
        k = 0
        while True:
            i = b.find(a, k)
            if i < 0:
                break
            b[i:i + 4] = z; k = i + 4
    return bytes(b)


def noms_contenant(b, anc):
    return sorted({m.group().decode() for m in re.finditer(re.escape(anc.encode()) + rb'[A-Za-z0-9_.]*', b)})


def renommer_paquet(b, anc, neuf):
    """paquet G4PK : nb d'entrées u16 à +0x20, (décalage, taille) par entrée à +0x40, crc32 des noms, ordre trié u16, noms"""
    b = bytearray(b)
    n = struct.unpack_from('<H', b, 0x20)[0]
    t = 0x40 + 8 * n
    noms = [m.group().decode() for m in re.finditer(rb'[A-Za-z0-9_]+\.g4[a-z]{2}', bytes(b[t:t + 0x40 * max(2, n)]))][:n]
    assert len(noms) == n, ('paquet', noms)
    nouveaux = [x.replace(anc, neuf) for x in noms]
    crcs = [zlib.crc32(x.encode()) for x in nouveaux]
    for k, c in enumerate(crcs):
        assert struct.unpack_from('<I', b, t + 4 * k)[0] == zlib.crc32(noms[k].encode()), 'crc du paquet'
        struct.pack_into('<I', b, t + 4 * k, c)
    for k, v in enumerate(sorted(range(n), key=lambda k: crcs[k])):
        struct.pack_into('<H', b, t + 4 * n + 2 * k, v)
    return bytes(b)


def renommer_squelette(pk, anc, neuf):
    """section G4SK du paquet : crc32 des nœuds (table à 0x40 + 4 x u16[+0x28]) + ordre trié (u16[+0x2C]) + noms"""
    b = bytearray(pk)
    a = b.find(b'G4SK')
    n = struct.unpack_from('<H', b, a + 0x20)[0]
    offs = [a + 0x40 + 4 * o for o in struct.unpack_from('<11H', b, a + 0x24)]
    t_crc, t_tri, t_noms = offs[2], offs[4], offs[7]
    rel = struct.unpack_from('<%dH' % n, b, t_noms)
    noms = []
    for r in rel:
        i = t_noms + r
        noms.append(bytes(b[i:b.index(b'\0', i)]).decode())
    assert all(struct.unpack_from('<I', b, t_crc + 4 * k)[0] == zlib.crc32(noms[k].encode()) for k in range(n)), 'crc du squelette'
    nouveaux = [x.replace(anc, neuf) for x in noms]
    cr = [zlib.crc32(x.encode()) for x in nouveaux]
    for k in range(n):
        struct.pack_into('<I', b, t_crc + 4 * k, cr[k])
    for r, k in enumerate(sorted(range(n), key=lambda k: cr[k])):
        struct.pack_into('<H', b, t_tri + 2 * r, k)
    for k, r in enumerate(rel):
        i = t_noms + r
        b[i:i + len(noms[k])] = nouveaux[k].encode()
    return bytes(b), [x for x in noms if anc in x]


# ------------------------------------------------------------------ codes libres
def _pris(cfg, dossier):
    pris = set(os.listdir(os.path.join(cfg['data_dir'], 'common', 'chr', dossier)))
    motif = re.compile(r'\b([ka]\d{6})\b')
    for p in glob.glob(os.path.join(cfg['jeu_dir'], 'mods', '**', '*.toml'), recursive=True):
        if os.sep + MOD_ID + os.sep in p:
            continue
        try:
            pris.update(motif.findall(open(p, encoding='utf-8', errors='ignore').read()))
        except OSError:
            pass
    for p in glob.glob(os.path.join(cfg['jeu_dir'], 'mods', '*', 'assets', 'chr', dossier, '*')):
        pris.add(os.path.basename(p))
    return pris


def code_libre(cfg, dossier, registre):
    pris = _pris(cfg, dossier) | set(registre)
    base = open(glob.glob(os.path.join(cfg['data_dir'], 'common', 'gamedata', 'character', 'chara_base_*.cfg.bin'))[0], 'rb').read()
    for k in range(10, 100):
        c = PREFIXES[dossier] + '%02d' % k
        if c not in pris and struct.pack('<I', zlib.crc32(c.encode())) not in base:
            return c
    raise RuntimeError('plus de code libre')


# ------------------------------------------------------------------ fichiers
def _png(data_url, tmp):
    f = os.path.join(tmp, 'img.png')
    open(f, 'wb').write(base64.b64decode(data_url.split(',', 1)[1]))
    return images.lire_png(f)


def entrees_seules(b, anc, neuf):
    """(15/11/2026) RENOMMAGE QUI MARCHE EN JEU : seuls les NOMS DES ENTRÉES du paquet changent (leurs crc32 et l'index trié ;
    le nom en clair dans l'en-tête) ; les noms internes (os, maillages, textures, matières) restent ceux de l'original.
    LU : Mukuro (Mukuro_atelier/ecrire_orbes.py, vérifié en jeu) et ZanUltimateMod 0.9.28-0.9.34 (README : le dragon
    k000291 était INVISIBLE tant que les noms internes et leurs CRC étaient renommés — tables triées par CRC désorganisées —,
    visible avec les seules entrées renommées). Même longueur de code obligatoire (sinon tout le fichier est décalé)."""
    from .clone_modele import renommer_paquet as _entrees
    assert len(anc) == len(neuf), (anc, neuf)
    return _entrees(b, struct.unpack_from('<H', b, 0x20)[0], anc, neuf)


def copier_modele(cfg, anc, neuf, dossier, textures, sortie, pool, tmp, tx_existant=None):
    """(15/11/2026) copie à la façon de Mukuro / Zan (voir entrees_seules) : .g4pkm et _p010 (entrées renommées ; le _p010
    aussi sous son nom d'origine, comme Zan 0.9.33-0.9.34), .g4md à part (5 esprits en ont un, dont Pégase) et .g4mg tels
    quels, .objbin (chemin), .g4tx sous le nom neuf mais avec les NOMS D'IMAGES D'ORIGINE (recolorées).
    tx_existant : .g4tx déjà recoloré (réparation des copies faites avant), dont on remet les noms d'origine."""
    src_c = os.path.join(cfg['data_dir'], 'common', 'chr', dossier, anc)
    out = os.path.join(sortie, 'assets', 'chr', dossier, neuf)
    os.makedirs(out, exist_ok=True)
    pk = open(os.path.join(src_c, anc + '.g4pkm'), 'rb').read()
    open(os.path.join(out, neuf + '.g4pkm'), 'wb').write(entrees_seules(pk, anc, neuf))
    noeuds = []                                       # noms internes gardés : les animations visent les mêmes os
    open(os.path.join(out, neuf + '.g4mg'), 'wb').write(open(os.path.join(src_c, anc + '.g4mg'), 'rb').read())
    if os.path.exists(os.path.join(src_c, anc + '.g4md')):
        shutil.copy(os.path.join(src_c, anc + '.g4md'), os.path.join(out, neuf + '.g4md'))
    open(os.path.join(out, neuf + '.objbin'), 'wb').write(open(os.path.join(src_c, anc + '.objbin'), 'rb').read().replace(anc.encode(), neuf.encode()))
    p10 = os.path.join(src_c, anc + '_p010.g4pk')
    if os.path.exists(p10):
        b = open(p10, 'rb').read()
        open(os.path.join(out, neuf + '_p010.g4pk'), 'wb').write(entrees_seules(b, anc, neuf))
        shutil.copy(p10, os.path.join(out, anc + '_p010.g4pk'))
    if tx_existant is not None:
        open(os.path.join(out, neuf + '.g4tx'), 'wb').write(bustes.renommer(tx_existant, neuf, anc) if neuf.encode() in tx_existant else tx_existant)
        return noeuds, ['textures recolorées gardées (noms d\'origine remis)']
    # textures
    gt = images.G4TX(open(os.path.join(cfg['data_dir'], 'dx11', 'chr', dossier, anc, anc + '.g4tx'), 'rb').read())
    rempl, rapport = {}, []
    for nom, url in textures.items():
        bloc = gt.blocs[gt.noms.index(nom)]
        h0, w0 = struct.unpack_from('<II', bloc, 12)
        w, h, rows = _png(url, tmp)
        assert (w, h) == (w0, h0), '%s : %dx%d au lieu de %dx%d' % (nom, w, h, w0, h0)
        assert bloc[84:88] == b'DX10' and struct.unpack_from('<I', bloc, 128)[0] == 98, nom + ' : pas en BC7'
        rempl[nom] = images.dds_bc7(w, h, rows, bloc[:148], images.mips_dds(bloc), pool)
        rapport.append('%s (%dx%d)' % (nom, w, h))
    tx = gt.reconstruire(rempl)                       # noms d'images d'origine (Mukuro / Zan)
    open(os.path.join(out, neuf + '.g4tx'), 'wb').write(tx)
    return noeuds, rapport


def copier_scenes(cfg, anc, neuf, noeuds, sortie):
    """paquets d'animation <scène>_<anc>_*.g4pk -> <scène>_<neuf>_*.g4pk ; renvoie les scènes"""
    scenes = set()
    for f in sorted(glob.glob(os.path.join(cfg['data_dir'], 'common', 'event', '*', '*', '*_%s_*.g4pk' % anc))):
        scene = os.path.basename(os.path.dirname(f))
        if scene.startswith('ev99'):
            continue                          # scènes de test du jeu
        b = open(f, 'rb').read()
        b2 = entrees_seules(b, anc, neuf)             # (15/11/2026) seul le nom de la matière .g4mt change (Zan 0.9.29)
        assert len(b2) == len(b)
        rel = os.path.relpath(os.path.dirname(f), os.path.join(cfg['data_dir'], 'common'))
        d = os.path.join(sortie, 'assets', rel)
        os.makedirs(d, exist_ok=True)
        open(os.path.join(d, os.path.basename(f).replace(anc, neuf)), 'wb').write(b2)
        scenes.add(scene)
    return sorted(scenes)


def copier_icone(cfg, anc, neuf, dossier, sortie, photo=None):
    """portrait de l'esprit (aura_fs/<code>_l, la grande plaque en match) : (16/11/2026) le dessin d'origine recoloré comme la
    copie (moteur/icones_copies.py ; 'dessin'), sinon la photo du modèle ('photo'), sinon celui de l'original renommé (True)"""
    rel = os.path.join('menu', '200_icon', '10_icon_chr', ICONES[dossier])
    src = os.path.join(cfg['data_dir'], 'dx11', rel, anc + '_l.g4tx')
    if not os.path.exists(src):
        return False
    from .icones_copies import ecrire_portrait, paires_textures
    # (16/11/2026) dessin d'origine recoloré comme les textures de la copie (la photo dit où va chaque couleur)
    paires = paires_textures(open(os.path.join(cfg['data_dir'], 'dx11', 'chr', dossier, anc, anc + '.g4tx'), 'rb').read(),
                             open(os.path.join(sortie, 'assets', 'chr', dossier, neuf, neuf + '.g4tx'), 'rb').read(), anc, neuf)
    return ecrire_portrait(src, os.path.join(sortie, 'assets', rel, neuf + '_l.g4tx'), photo, anc, neuf, paires) or True


# ------------------------------------------------------------------ déclarations VRFW (réécrites depuis le registre)
def _env_des_autres(cfg, scene):
    """tag_words / snd_tag_words que les autres mods posent déjà sur cette scène (à garder : sinon VRFW n'en garde qu'un)"""
    tags, snd = {}, {}
    for p in glob.glob(os.path.join(cfg['jeu_dir'], 'mods', '**', '*.toml'), recursive=True):
        if os.sep + MOD_ID + os.sep in p:
            continue
        try:
            t = open(p, encoding='utf-8', errors='ignore').read()
            if 'event_env' not in t or scene not in t:
                continue
            for e in tomllib.loads(t).get('event_env', []):
                if e.get('event') == scene:
                    tags.update((e.get('tag_words') or {}).get('set', {}))
                    snd.update((e.get('snd_tag_words') or {}).get('set', {}))
        except Exception:
            pass
    return tags, snd


def _codes_sons(cfg):
    """(14/11/2026) tous les esprits / armures du jeu et des mods installés. Une scène qui a une liste de sons (snd_tag_words)
    ne joue QUE les sons des codes qu'elle cite (LU dans event_tag_word_replace_config : 142 entrées sur 143 du jeu sont
    « code = code ») : chacun y est donc gardé sur ses propres sons, sinon l'esprit d'origine perd sa voix."""
    codes = set()
    for base in (os.path.join(cfg['data_dir'], 'common', 'chr'), os.path.join(cfg['jeu_dir'], 'mods')):
        for r, ds, fs in os.walk(base):
            codes.update(d for d in ds if re.fullmatch(r'(k|a|kx|me|mx)\d{6}', d))
    return codes


_GROUPES = {}


def groupes_scene(cfg, ev):
    """(15/11/2026) (groupe des mots, groupe des sons) d'une scène : event_env_config_soccer_demo, colonnes 52 et 54 (LU :
    ev80_00010 = 0xE35E00DF / 0xE35E00DF, ev61_00920 = 0xE35E00DF / 0). (None, None) si la scène n'y est pas."""
    if not _GROUPES:
        from .maillots.cfgbin import parse
        f = sorted(glob.glob(os.path.join(cfg['data_dir'], 'common', 'gamedata', 'event', 'event_env_config_soccer_demo_*.cfg.bin')))
        for k, v in (parse(f[-1]) if f else []):
            if k == 'EVENT_ENV_CONFIG' and len(v) > 54 and isinstance(v[0], int):
                _GROUPES[v[0] & 0xFFFFFFFF] = tuple((x & 0xFFFFFFFF) if isinstance(x, int) else None for x in (v[52], v[54]))
        _GROUPES.setdefault(-1, None)
    return _GROUPES.get(zlib.crc32(ev.encode()), (None, None))


def ecrire_vrfw(cfg, sortie, registre):
    ch, tech, txt, shop = [], [], [], []
    scenes, bases = {}, {}
    for k, (neuf, c) in enumerate(sorted(registre.items())):
        anc, dossier = c['base'], c['dossier']
        ch += ['[[character]]', 'name = %s' % _q('mesesprits_' + c['slug']), 'based_on = %s' % _q(anc), 'battle = false', '',
               '  [character.base]', '  id = 0x%08X                                         # crc32("%s")' % (zlib.crc32(neuf.encode()), neuf),
               '  name = %s' % _q(neuf), '',
               '  [character.new_model]', '  id = 0x%08X                                         # crc32("mdl_%s")' % (zlib.crc32(('mdl_' + neuf).encode()), neuf),
               '  from = 0x%08X                                       # crc32("mdl_%s") : modèle d\'origine (%s)' % (zlib.crc32(('mdl_' + anc).encode()), anc, c['nom_base']),
               '  [character.new_model.cells]', '  skeleton_path = %s' % _q('%s/%s/%s.objbin' % (dossier, neuf, neuf)), '']
        id_nom, id_desc = zlib.crc32(('%s.%s_nom' % (MOD_ID, c['slug'])).encode()), zlib.crc32(('%s.%s_desc' % (MOD_ID, c['slug'])).encode())
        # (15/11/2026) technique liée choisie au hub : cells.linked_skill = crc32(clé), comme Michael -> « whs94200 » (Mukuro) ;
        # sans choix, celle de l'esprit d'origine (aura_skill_config colonne 6, reprise par « from »)
        lie = c.get('technique_liee')
        cel_lie = ', linked_skill = 0x%08X' % lie['id'] if lie else ''
        # (22/11) stats réglées dans « En attente de stats » : colonnes power_min / power_max / element de AURA_CMD_INFO
        if c.get('stats'):
            from . import stats as _st
            cel_lie += _st.cellules_esprit(c['stats'], _st.jeu_esprit(cfg['data_dir'], c['technique']))
        tech += ['# %s : copie de %s (%s), code %s' % (c['nom'], c['nom_base'], anc, neuf),
                 '[[aura_command]]', 'key = %s' % _q(c['key']), 'id = 0x%08X                                  # crc32(key)' % zlib.crc32(c['key'].encode()),
                 'from = %s' % _q(c['technique']), 'manual = true',
                 'cells = { name_text = 0x%08X, desc_text = 0x%08X%s, aura_chara = 0x%08X, order = %d }   # aura_chara = crc32("%s")'
                 % (id_nom, id_desc, cel_lie, zlib.crc32(neuf.encode()), 150 + k, neuf)
                 + ('\n# technique liée : %s (%s)' % (lie.get('nom', ''), lie.get('code', '')) if lie else ''),
                 'charas = []', '']
        for nid, variant, texte, genre in ((id_nom, None, c['nom'], 'noun'), (id_nom, 11, c['nom'], 'noun'), (id_desc, None, c['description'] or c['nom'], 'text')):
            txt += ['[[row]]', 'id = 0x%08X  # %s.%s' % (nid, MOD_ID, c['slug']), 'kind = "%s"' % genre] + (['variant = %d' % variant] if variant else []) \
                + ['%s = %s' % (l, _q(texte)) for l in ('de', 'en', 'es', 'fr', 'it', 'ja', 'pt', 'zh_hans', 'zh_hant')] + ['']
        if c.get('prix'):
            shop += ['  [[edit.entry]]', '  item = %s' % _q(c['key']), '  after = "wks_fantasy_k002011"',
                     '  price = %d' % int(c['prix']), '  currency = "tk_bb000001"', '']
        for s in c['scenes']:
            scenes.setdefault(s, []).append((neuf, neuf, anc))      # ses animations copiées, les sons de l'original
        # (15/11/2026) cinématique de la technique liée : l'esprit y prend les animations (et les sons) de l'esprit de cette
        # technique quand tous ses os animés existent dans son squelette (comme Michael -> Reine sorcière dans ev81_00030)
        pl = (lie or {}).get('scene') or {}
        if pl.get('etat') in ('propre', 'emprunt') and (pl.get('copie') or pl['etat'] == 'emprunt'):
            for s in pl['scenes']:
                if s not in c['scenes']:
                    scenes.setdefault(s, []).append((neuf, pl['esprit'], pl['esprit']))
                    if pl.get('copie'):
                        bases[s] = pl.get('dossier') or s      # scène copiée par VRFW : la ligne de sa scène d'origine
    env = []
    for s, liste in sorted(scenes.items()):
        g_tag, g_snd = groupes_scene(cfg, bases.get(s, s))
        tags, snd = _env_des_autres(cfg, s)
        snd = dict({c: c for c in _codes_sons(cfg)}, **snd)        # chacun garde ses sons (voir _codes_sons)
        for neuf, tag, son_ in liste:
            tags[neuf] = tag
            snd[neuf] = son_
        f = lambda d: '{ ' + ', '.join('%s = %s' % (k, _q(v)) for k, v in sorted(d.items())) + ' }'
        # (15/11/2026) LU (event_env_config, col. 52 = groupe des mots, col. 54 = groupe des sons) : pas de liste là où la scène
        # n'a pas de groupe (ev61_00920 : sons 0 -> VRFW « group 0x00000000 is not in EVENT_ASSIGN_SND… (skipped) »)
        env += ['[[event_env]]', 'event = %s' % _q(s)] + (['tag_words = { set = %s }' % f(tags)] if g_tag != 0 else []) \
            + (['snd_tag_words = { set = %s }' % f(snd)] if g_snd != 0 else []) + ['']
    entete = '# Écrit par l\'Atelier Inazuma (ne pas modifier à la main : réécrit à chaque export).\n'
    _ecrire(os.path.join(sortie, 'content', 'characters', 'mes_esprits.toml'), 'schema = "VRFW.character/2"\n' + entete + 'default_lang = "en"\n\n' + '\n'.join(ch))
    _ecrire(os.path.join(sortie, 'content', 'techniques', 'mes_esprits.toml'), 'schema = "VRFW.technique/3"\n' + entete
            + '# scènes : animations copiées sous le code neuf ; sons = ceux de l\'original ; les mots des autres mods sont gardés\n\n'
            + '\n'.join(tech + env))
    _ecrire(os.path.join(sortie, 'text', 'rows', 'mes_esprits.toml'), 'schema = "VRFW.text/2"\ntable = "skill_text"\n' + entete + '\n' + '\n'.join(txt))
    f_shop = os.path.join(sortie, 'addons', 'InazumaFantasy', 'content', 'shops', 'mes_esprits.toml')
    if shop:
        _ecrire(f_shop, 'schema = "VRFW.shop/2"\n' + entete + '\n[[edit]]\ntarget = "InazumaFantasy.training_shop"   # Marché -> Boutique d\'entraînement\n\n' + '\n'.join(shop))
    elif os.path.exists(f_shop):
        os.replace(f_shop, f_shop + '.retire')
    _ecrire(os.path.join(sortie, 'mod.toml'), '\n'.join([
        'id = "%s"' % MOD_ID, 'name = "Mes esprits et totems"', 'prefix = "%s"' % MOD_ID, 'folder = "%s"' % MOD_ID,
        'version = "1.0.0"', 'author = "muku"',
        'description = "Copies recolorées d\'esprits guerriers et de totems, créées avec l\'Atelier Inazuma (les originaux ne changent pas). En vente dans la boutique d\'entraînement d\'Inazuma Fantasy."',
        'priority = 0', 'tags = ["Characters", "Techniques"]', 'updated = "%s"' % datetime.date.today().isoformat(),
        'requires = ["VRFW>=0.3.0"]', 'optional = ["InazumaFantasy", "CharacterReforged"%s]' % (', "MesTechniques"' if any(
            (c.get('technique_liee') or {}).get('mod') == 'MesTechniques' for c in registre.values()) else ''),
        'conflicts = []', '']))   # (CharacterReforged : armures ; MesTechniques : technique liée faite dans l'Atelier)


# ------------------------------------------------------------------ export
def registre(sortie):
    f = os.path.join(sortie, 'outil_esprits.json')
    return json.load(open(f, encoding='utf-8')) if os.path.exists(f) else {}


def contenu(cfg):
    return registre(os.path.join(cfg['outil_dir'], 'sortie', MOD_ID))


def exporter(cfg, demande, infos):
    """demande : {code, nom, description, prix, textures: {nom: dataURL}} ; infos : fiche de l'index (dossier, nom, techniques)"""
    anc, dossier = demande['code'], infos['dossier']
    if not demande.get('textures'):
        return {'ok': False, 'erreur': 'Rien n\'est modifié : change d\'abord des couleurs.'}
    nom = (demande.get('nom') or '').strip()
    if not nom:
        return {'ok': False, 'erreur': 'Donne un nom à la copie.'}
    technique = next((t for t in infos['techniques'] if t[:2] in ('wk', 'ws')), None)
    if not technique:
        return {'ok': False, 'erreur': 'Technique d\'invocation introuvable pour %s.' % anc}
    sortie = os.path.join(cfg['outil_dir'], 'sortie', MOD_ID)
    reg = registre(sortie)
    s = slug(nom)
    neuf = next((k for k, v in reg.items() if v['slug'] == s and v['base'] == anc), None) or code_libre(cfg, dossier, reg)
    with tempfile.TemporaryDirectory() as tmp, multiprocessing.Pool(max(1, (os.cpu_count() or 2) - 1)) as pool:
        noeuds, rapport = copier_modele(cfg, anc, neuf, dossier, demande['textures'], sortie, pool, tmp)
    scenes = copier_scenes(cfg, anc, neuf, noeuds, sortie)
    icone = copier_icone(cfg, anc, neuf, dossier, sortie, demande.get('icone'))
    reg[neuf] = {'base': anc, 'nom_base': infos['nom'], 'genre': infos['genre'], 'dossier': dossier, 'nom': nom, 'slug': s,
                 'description': (demande.get('description') or '').strip(), 'prix': demande.get('prix'),
                 'technique': technique, 'key': '%s_mesesprits_%s' % (technique[:3], s), 'scenes': scenes,
                 'date': datetime.datetime.now().isoformat(timespec='seconds'),
                 **({'technique_liee': reg[neuf]['technique_liee']} if reg.get(neuf, {}).get('technique_liee') else {})}   # gardée si on refait la copie
    ecrire_vrfw(cfg, sortie, reg)
    json.dump(reg, open(os.path.join(sortie, 'outil_esprits.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    rapport = ['copie %s → code neuf %s (l\'original ne change pas)' % (anc, neuf)] + ['texture ' + r for r in rapport] \
        + ['scènes copiées : ' + (', '.join(scenes) or 'aucune'), 'icône : ' + ({'dessin': "dessin d'origine recoloré comme la copie", 'photo': 'photo du modèle recoloré'}.get(icone) or ('copiée' if icone else 'aucune')),
           'boutique d\'entraînement : %s' % ('%d points' % int(reg[neuf]['prix']) if reg[neuf]['prix'] else 'pas de vente')]
    return {'ok': True, 'dossier': sortie, 'code': neuf, 'rapport': rapport}


def lier_technique(cfg, neuf, technique, cache_dir=None):
    """(15/11/2026) « c'est la technique de cet esprit » : technique = {id, code, nom, mod} (du jeu ou de MesTechniques), None = celle d'origine"""
    sortie = os.path.join(cfg['outil_dir'], 'sortie', MOD_ID)
    reg = registre(sortie)
    if neuf not in reg:
        return {'ok': False, 'erreur': 'copie d\'esprit inconnue : %s' % neuf}
    if technique:
        try:
            t = {'id': int(technique['id']) & 0xFFFFFFFF, 'code': str(technique.get('code') or ''), 'nom': str(technique.get('nom') or ''),
                 'mod': technique.get('mod') or ''}
        except (KeyError, TypeError, ValueError):
            return {'ok': False, 'erreur': 'technique illisible'}
        if not t['code'][:3] in ('whs', 'who', 'whd', 'whk'):
            return {'ok': False, 'erreur': 'la technique liée doit être un tir, un dribble, une défense ou un arrêt (%s)' % t['code']}
        if cache_dir:                              # (15/11/2026) l'esprit dans la cinématique de cette technique (moteur/coups.py)
            from . import coups
            from .export import assurer_esprit
            t['scene'] = coups.plan_esprit(cfg, cache_dir, reg[neuf]['base'], t['code'])
            if t['scene'].get('copie') and t['scene']['etat'] in ('propre', 'emprunt'):
                assurer_esprit(cfg, t['code'])     # la copie de technique livre les animations de son esprit (`assigned`)
        reg[neuf]['technique_liee'] = t
    else:
        reg[neuf].pop('technique_liee', None)
    ecrire_vrfw(cfg, sortie, reg)
    json.dump(reg, open(os.path.join(sortie, 'outil_esprits.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    c = reg[neuf]
    rapport = ['%s : technique liée %s' % (c['nom'], '« %s » (%s)' % (c['technique_liee']['nom'], c['technique_liee']['code'])
                                            if c.get('technique_liee') else 'd\'origine (celle de %s)' % c['nom_base'])]
    pl = (c.get('technique_liee') or {}).get('scene') or {}
    try:                                      # nom de l'esprit (index des esprits de l'Atelier)
        nom_k = next((x['nom'] for x in json.load(open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'cache', 'index_personnages.json'), encoding='utf-8'))
                      if x['code'] == pl.get('esprit')), pl.get('esprit'))
    except (OSError, ValueError):
        nom_k = pl.get('esprit')
    pl = dict(pl, esprit=nom_k) if pl.get('esprit') else pl
    rapport.append({'propre': 'cinématique : %s y apparaît (animations de son esprit d\'origine)' % c['nom'],
                    'emprunt': 'cinématique : %s y apparaît avec les animations de %s (mêmes os)' % (c['nom'], pl.get('esprit')),
                    'incompatible': 'cinématique : faite pour l\'esprit %s, dont les os ne sont pas tous dans %s : il y sera caché' % (pl.get('esprit'), c['nom']),
                    'sans_esprit': 'cinématique : aucun esprit dedans (rien à faire)'}.get(pl.get('etat'), ''))
    if pl.get('copie') and pl.get('etat') in ('propre', 'emprunt'):
        rapport.append('MesTechniques : animations de %s livrées sous %s (à réinstaller aussi)' % (pl['esprit'], pl['copie']))
    return {'ok': True, 'dossier': sortie, 'rapport': [r for r in rapport if r]}



def reparer_copies(cfg):
    """(15/11/2026) copies d'esprit faites AVANT la méthode de Mukuro / Zan (noms internes renommés : esprit invisible en
    match, LU dans le journal de muku : invocation jouée, rien d'affiché) : fichiers du modèle et des scènes refaits, textures
    recolorées gardées. Sauvegarde de sortie/MesEsprits avant, dans « Sauvegardes Atelier Couleurs »."""
    sortie = os.path.join(cfg['outil_dir'], 'sortie', MOD_ID)
    reg = registre(sortie)
    if not reg:
        return {'ok': True, 'rapport': ['aucune copie d\'esprit']}
    sauv = os.path.join(cfg.get('sauvegardes_dir') or os.path.join(cfg['outil_dir'], 'sauvegardes'),
                        MOD_ID + '_avant_reparation_' + datetime.datetime.now().strftime('%Y%m%d_%H%M%S'))
    shutil.copytree(sortie, sauv)
    rapport = ['sauvegarde : ' + sauv]
    for neuf, c in sorted(reg.items()):
        anc, dossier = c['base'], c['dossier']
        f_tx = os.path.join(sortie, 'assets', 'chr', dossier, neuf, neuf + '.g4tx')
        tx = open(f_tx, 'rb').read() if os.path.exists(f_tx) else None
        if tx is None:
            rapport.append('%s : pas de texture, copie laissée' % c['nom']); continue
        copier_modele(cfg, anc, neuf, dossier, {}, sortie, None, None, tx_existant=tx)
        scenes = copier_scenes(cfg, anc, neuf, [], sortie)
        c['scenes'] = scenes
        rapport.append('%s (%s) : modèle et %d scène(s) refaits, textures gardées' % (c['nom'], neuf, len(scenes)))
    ecrire_vrfw(cfg, sortie, reg)
    json.dump(reg, open(os.path.join(sortie, 'outil_esprits.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    return {'ok': True, 'dossier': sortie, 'rapport': rapport}
