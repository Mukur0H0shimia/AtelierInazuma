"""Export d'une technique recolorée en mod VRFW « MesTechniques » (une technique copiée : l'originale ne change pas).

Méthode (vérifiée en jeu avec « Lumière de Michael », mod Mukuro, 13/11/2026) :
- technique : [[technique]] key (code neuf whX96NNN), base, manual, event = "MesTechniques.<nom>", color (couleur du tir), textes ;
- cinématique : [[event]] from = <cinématique d'origine>, id = <id neuf evNN_89NN0>, telop = <key> ;
- couleurs : chaque objet d'effet est copié (même longueur de nom) et ses textures modifiées sont REMPLACÉES par des images
  ([recolor.images], comme Guardia celestial d'Inazuma Fantasy) ; option « lueurs » : teinte posée sur les couleurs des
  sommets, des matériaux et des particules ; [[event_command]] LOAD_ACTOR_RESOURCE pour charger les copies ;
- auras : copies recolorées (color = [[0, r, v, b, 0]]) + ATTACH_AURA remplacés ;
- traînée (tirs) : [[shot_aura]] aura = famille du jeu (ega0075 / ega0080 / ega0085) + color = élément ;
- bannière : content/telops/any/<key>.png (1728 x 352) + [[telop]] from = la bannière d'origine ;
- boutique : addons/InazumaFantasy/content/shops/<nom>.toml (boutique des supertechniques d'Inazuma Fantasy).
Pièges évités : UNE clé fausse et VRFW refuse tout un fichier -> chaque fichier est relu avec tomllib avant d'écrire ;
`material` d'un [[recolor.tint]] = un seul nom (non utilisé ici) ; copies d'objets = même longueur de nom.
"""
from moteur import outils_ext as _outils_ext  # noqa: E402  (ffmpeg fourni)
import os, sys, re, json, glob, base64, shutil, subprocess, tomllib, datetime, zlib, struct

MOD_ID = 'MesTechniques'


def _q(s):
    return json.dumps(s, ensure_ascii=False)


def _noms_utilises(cfg):
    """codes de techniques, ids de cinématiques et noms d'objets déjà pris (jeu + mods + cache VRFW)"""
    pris = set()
    data = cfg['data_dir']
    for p in glob.glob(os.path.join(data, 'dx11', 'menu', '220_img', 'telop_waza', '*', '*.g4tx')):
        pris.add(os.path.basename(p)[:-5])
    for p in glob.glob(os.path.join(data, 'common', 'event_cfg', 'evt', '*.cfg.bin')):
        pris.add(os.path.basename(p)[:-8])
    for p in glob.glob(os.path.join(data, 'common', 'effect', 'event', 'ev6*', '*')):
        pris.add(os.path.basename(p))
    mods = os.path.join(cfg['jeu_dir'], 'mods')
    motif = re.compile(r'\b(wh[sdkot]\d{5}|ev6\d_\d{5}|ev6\d{8})\b')
    for p in glob.glob(os.path.join(mods, '**', '*.toml'), recursive=True):
        if os.sep + MOD_ID + os.sep in p:
            continue
        try:
            pris.update(motif.findall(open(p, encoding='utf-8', errors='ignore').read()))
        except OSError:
            pass
    return pris


def _deja_dans_le_mod(sortie):
    """techniques déjà créées par l'outil (pour ne pas réutiliser leurs numéros)"""
    f = os.path.join(sortie, 'outil_techniques.json')
    return json.load(open(f, encoding='utf-8')) if os.path.exists(f) else {}


def nouveaux_numeros(cfg, code, cinematique, sortie, nom):
    """(key, id de cinématique) libres ; un même nom garde ses numéros d'un export à l'autre"""
    deja = _deja_dans_le_mod(sortie)
    if nom in deja:
        return deja[nom]['key'], deja[nom]['id']
    pris = _noms_utilises(cfg) | {v['key'] for v in deja.values()} | {v['id'] for v in deja.values()}
    for n in range(10, 1000):
        key = '%s96%03d' % (code[:3], n)
        ev = '%s_89%03d' % (cinematique[:4], n * 10 % 1000) if n < 100 else None
        if ev is None:
            break
        if key not in pris and ev not in pris and not any(p.startswith(cinematique[:4] + ev[5:9]) for p in pris):
            return key, ev
    raise RuntimeError('plus de numéro libre')


def ecrire_anim(sortie, nom, ev0, ev, key, assigne):
    _ecrire(os.path.join(sortie, 'content', 'anims', nom + '.toml'), '\n'.join([
        'schema = "VRFW.anim/2"', 'owner = "match"', '', '[[event]]', 'name = %s' % _q(nom), 'from = %s' % _q(ev0),
        'id = %s' % _q(ev), 'telop = %s' % _q(key)]
        + (['# esprit invoqué (<ASSIGN>, choisi pendant le match) : ses animations sont livrées sous %s (comme Mukuro)' % ev,
            'assigned = [%s]' % ', '.join(_q(k) for k in assigne)] if assigne else []) + ['']))


def esprit_assigne(cfg, sortie, ev0, ev):
    """(15/11/2026) LU (VRFW + Mukuro) : dans une cinématique copiée, l'esprit invoqué (<ASSIGN>) est CACHÉ si le mod ne livre pas
    ses animations sous l'id neuf (« ships no packs of the assigned model(s) … hidden there ») : on copie
    <scène>_<esprit>_*.g4pk -> <id>_<esprit>_*.g4pk (nom de la scène + crc32 des noms de section, comme ev60_88200 de Mukuro)
    et on le déclare dans `assigned`. Renvoie les esprits livrés."""
    from .coups import esprits_de_scene, dossier_scene
    from .esprits import renommer_paquet
    d = dossier_scene(ev0)
    ks = esprits_de_scene(cfg['data_dir'], ev0)
    if not ks or len(d) != len(ev):
        return []
    out = os.path.join(sortie, 'assets', 'event', ev[:4], ev)
    for k in ks:
        for f in sorted(glob.glob(os.path.join(cfg['data_dir'], 'common', 'event', d[:4], d, '%s_%s_*.g4pk' % (d, k)))):
            b = open(f, 'rb').read()
            b2 = renommer_paquet(b, d, ev).replace(d.encode(), ev.encode())
            assert len(b2) == len(b) and d.encode() not in b2
            os.makedirs(out, exist_ok=True)
            open(os.path.join(out, os.path.basename(f).replace(d, ev, 1)), 'wb').write(b2)
    return ks


def assurer_esprit(cfg, key):
    """copie de technique déjà faite (avant le 15/11/2026, sans `assigned`) : livre les animations de son esprit et réécrit sa
    cinématique. Renvoie les esprits livrés ([] si sa cinématique n'en a pas)."""
    sortie = os.path.join(cfg['outil_dir'], 'sortie', MOD_ID)
    for nom, e in _deja_dans_le_mod(sortie).items():
        if e['key'] != key:
            continue
        f = os.path.join(sortie, 'content', 'anims', nom + '.toml')
        if not os.path.exists(f):
            return []
        x = tomllib.load(open(f, 'rb'))['event'][0]
        if x.get('assigned'):
            return x['assigned']
        assigne = esprit_assigne(cfg, sortie, x['from'], x['id'])
        if assigne:
            ecrire_anim(sortie, nom, x['from'], x['id'], x.get('telop') or key, assigne)
        return assigne
    return []


def copie_objet(nom_objet, id_neuf):
    """ev60102000 + ev60_89010 -> ev60890100 (même longueur : 4 premiers caractères, 4 chiffres de l'id, 2 derniers)"""
    return nom_objet[:4] + id_neuf[5:9] + nom_objet[-2:]


def slug(nom):
    s = re.sub(r'[^a-z0-9]+', '_', nom.lower().replace('é', 'e').replace('è', 'e').replace('ê', 'e').replace('à', 'a')
               .replace('ù', 'u').replace('ô', 'o').replace('î', 'i').replace('ç', 'c').replace('â', 'a').replace('û', 'u'))
    return s.strip('_') or 'technique'


def banniere(texte, couleur, contour, sortie_png):
    """bannière simple 1728 x 352, fond transparent (police Impact, contour) avec ffmpeg"""
    police = os.path.join(os.path.dirname(sortie_png), '_police.ttf')
    shutil.copy(r'C:\Windows\Fonts\impact.ttf', police)
    t = texte.replace('\\', '').replace("'", '\u2019').replace(':', '\\:')
    taille = max(60, min(150, int(1560 / (max(len(texte), 1) * 0.52))))      # Impact : ~0,52 x la taille par lettre
    base = "fontfile=_police.ttf:fontsize=%d:x=(w-text_w)/2:y=(h-text_h)/2:text='%s'" % (taille, t)
    vf = ("drawtext=%s:fontcolor=white:borderw=20:bordercolor=white,"
          "drawtext=%s:fontcolor=%s:borderw=12:bordercolor=%s,"
          "drawtext=%s:fontcolor=%s:borderw=2:bordercolor=white@0.6") % (base, base, contour, contour, base, couleur)
    env = dict(os.environ, MSYS2_ARG_CONV_EXCL='*')
    r = subprocess.run([_outils_ext.ffmpeg(), '-v', 'error', '-y', '-f', 'lavfi', '-i', 'color=c=black@0.0:s=1728x352,format=rgba', '-vf', vf,
                        '-frames:v', '1', '-update', '1', os.path.basename(sortie_png)], cwd=os.path.dirname(sortie_png),
                       capture_output=True, text=True, env=env)
    os.remove(police)
    if r.returncode:
        raise RuntimeError('bannière : ' + r.stderr[-300:])


def _ecrire(chemin, texte):
    tomllib.loads(texte)                      # une clé ou une syntaxe fausse -> on s'arrête AVANT d'écrire
    os.makedirs(os.path.dirname(chemin), exist_ok=True)
    open(chemin, 'w', encoding='utf-8').write(texte)


def _code_libre(cfg, anc, sortie, cle):
    """code neuf pour la copie d'un modèle de personnage (même lettre, 6 chiffres à partir de 7000) : absent du jeu, des
    mods installés et des copies déjà faites ; la même technique et le même acteur gardent le même code (outil_modeles.json)"""
    f = os.path.join(sortie, 'outil_modeles.json')
    reg = json.load(open(f, encoding='utf-8')) if os.path.exists(f) else {}
    if cle in reg and len(reg[cle]) == len(anc):      # (15/11/2026) un ancien code de longueur différente est refait
        return reg[cle], reg, f
    reg.pop(cle, None)
    pris = set(reg.values())
    for base in (os.path.join(cfg['data_dir'], 'common', 'chr'), os.path.join(cfg['data_dir'], 'common', 'event'),
                 os.path.join(cfg.get('jeu_dir', '') or '.', 'mods')):
        if os.path.isdir(base):
            for r, ds, fs in os.walk(base):
                pris.update(ds)
    # (15/11/2026) MÊME LONGUEUR que l'original (le renommage se fait sur place) : « k000020 » -> « k007000 »,
    # « ev60_00830 » -> « ev60_97000 » (avant : « e007000 », 3 caractères de moins = modèle illisible en jeu)
    m = re.fullmatch(r'([a-z]+\d*_?)(\d{4,6})', anc)
    tete, nb = (m.group(1), len(m.group(2))) if m else (anc[:-4], 4)
    n = 7000
    def code(k):
        return (tete + '9' + '%0*d' % (nb - 1, k)) if '_' in tete else (tete + '%0*d' % (nb, k))
    while code(n) in pris:
        n += 1
    reg[cle] = code(n)
    assert len(reg[cle]) == len(anc), (anc, reg[cle])
    return reg[cle], reg, f


def _valeur_load(objet, anc, neuf):
    """2e argument de LOAD pour la copie : le code, ou le chemin du .objbin si la cinématique charge le modèle par son chemin"""
    ch = objet.get('cheminLoad')
    if ch:
        return ch.replace('/' + anc + '/', '/' + neuf + '/').replace(anc + '.objbin', neuf + '.objbin')
    return neuf


def copie_modele(cfg, sortie, nom, acteur, anc, imgs):
    """copie recolorée d'un modèle de personnage chargé par la cinématique (esprit guerrier…) : fichiers dans
    assets/chr/<dossier>/<neuf>/ (moteur/clone_modele.py), personnage VRFW neuf, puis la cinématique copiée charge la copie"""
    import subprocess, tempfile
    neuf, reg, f_reg = _code_libre(cfg, anc, sortie, nom + '|' + acteur)
    dos_png = os.path.join(sortie, 'assets', 'images', 'chr', nom)
    os.makedirs(dos_png, exist_ok=True)
    tex = {}
    for t, data in sorted(imgs.items()):
        png = os.path.join(dos_png, t + '.png')
        open(png, 'wb').write(base64.b64decode(data.split(',', 1)[1]))
        tex[t] = png
    f_tex = os.path.join(dos_png, '_textures.json')
    json.dump(tex, open(f_tex, 'w', encoding='utf-8'))
    r = subprocess.run([sys.executable, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'clone_modele.py'),
                        cfg['data_dir'], anc, neuf, os.path.join(sortie, 'assets', 'chr'), f_tex], capture_output=True, text=True, timeout=900)
    if r.returncode != 0:
        raise RuntimeError('copie du modèle %s : %s' % (anc, (r.stderr or r.stdout)[-400:]))
    info = json.loads(r.stdout.strip().splitlines()[-1])
    json.dump(reg, open(f_reg, 'w', encoding='utf-8'), indent=1)
    sous = (info['dossier'] + '/') if info['dossier'] else ''
    perso = ['[[character]]', 'name = %s' % _q('%s_%s' % (nom, neuf)), 'based_on = %s' % _q(anc), 'battle = false', '',
             '  [character.base]', '  id = 0x%08X                                         # crc32("%s")' % (zlib.crc32(neuf.encode()), neuf),
             '  name = %s' % _q(neuf), '', '  [character.new_model]',
             '  id = 0x%08X                                         # crc32("mdl_%s")' % (zlib.crc32(('mdl_' + neuf).encode()), neuf),
             '  from = 0x%08X                                       # crc32("mdl_%s") : modèle d\'origine' % (zlib.crc32(('mdl_' + anc).encode()), anc),
             '  [character.new_model.cells]', '  skeleton_path = %s' % _q('%s%s/%s.objbin' % (sous, neuf, neuf)), '']
    return neuf, info, perso


def exporter(cfg, demande, infos_technique):
    """demande : {code, nom, description, couleur_tir, prix, banniere:{texte, couleur, contour}, trainee:{famille, element},
                 objets:{acteur:{textures:{nom: dataURL}, lueurs:{hue, saturation, value} | None}}, auras:{nom:[r,v,b]}}"""
    sortie = os.path.join(cfg['outil_dir'], 'sortie', MOD_ID)
    os.makedirs(sortie, exist_ok=True)
    nom = slug(demande['nom'])
    code, ev0 = demande['code'], infos_technique['cinematique']
    key, ev = nouveaux_numeros(cfg, code, ev0, sortie, nom)
    rapport = ['technique « %s » : code %s, cinématique %s (copie de %s)' % (demande['nom'], key, ev, ev0)]

    # --- mod.toml
    _ecrire(os.path.join(sortie, 'mod.toml'), '\n'.join([
        'id = "%s"' % MOD_ID, 'name = "Mes techniques"', 'prefix = "%s"' % MOD_ID, 'folder = "%s"' % MOD_ID,
        'version = "1.0.0"', 'author = "muku"',
        'description = "Techniques recolorées créées avec l\'Atelier Couleurs (copies : les techniques d\'origine ne changent pas)."',
        'priority = 0', 'tags = ["Techniques", "Visual"]', 'updated = "%s"' % datetime.date.today().isoformat(),
        'requires = ["VRFW>=0.3.0"]', 'optional = ["InazumaFantasy"]', 'conflicts = []', '']))

    # --- technique
    desc = demande.get('description') or ''
    lignes = ['schema = "VRFW.technique/3"',
              '# Créée par l\'Atelier Couleurs le %s : copie de %s (%s).' % (datetime.date.today().isoformat(), code, infos_technique.get('nom', '')),
              '', '[[technique]]', 'name = %s' % _q(nom), 'key = %s' % _q(key), 'base = %s' % _q(code), 'manual = true',
              'event = %s' % _q('%s.%s' % (MOD_ID, nom))]
    if demande.get('couleur_tir') is not None:
        lignes.append('color = %d' % int(demande['couleur_tir']))
    for lg in ('fr', 'en', 'es', 'de', 'it', 'pt'):
        lignes += ['  [technique.text.%s]' % lg, '  name = %s' % _q(demande['nom'])]
        if desc:
            lignes.append('  description = %s' % _q(desc))
    _ecrire(os.path.join(sortie, 'content', 'techniques', nom + '.toml'), '\n'.join(lignes) + '\n')

    # --- cinématique copiée (+ animations de l'esprit invoqué, sinon VRFW le cache : voir esprit_assigne)
    assigne = esprit_assigne(cfg, sortie, ev0, ev)
    ecrire_anim(sortie, nom, ev0, ev, key, assigne)
    if assigne:
        rapport.append('esprit dans la cinématique : animations de %s livrées sous %s' % (', '.join(assigne), ev))

    # --- couleurs
    e = ['schema = "VRFW.effect/1"', '# Couleurs de « %s » (Atelier Couleurs) : copies des objets d\'effet de %s.' % (demande['nom'], ev0), '']
    dossier_img = os.path.join(sortie, 'assets', 'images', 'fx', nom)
    objets = {o['acteur']: o for o in infos_technique['objets']}
    # (14/11/2026) modèles de personnages de la cinématique (esprit guerrier…) : copie recolorée du modèle
    modeles = {o['acteur']: o for o in infos_technique.get('objets_details') or [] if o.get('modeleActeur')}
    persos = ['schema = "VRFW.character/2"', '# Copies recolorées des modèles de « %s » (Atelier Couleurs).' % demande['nom'], 'default_lang = "en"', '']
    for acteur, reglage in (demande.get('objets') or {}).items():
        if acteur in modeles and reglage.get('textures'):
            anc = modeles[acteur]['modeleActeur']
            neuf, info, perso = copie_modele(cfg, sortie, nom, acteur, anc, reglage['textures'])
            persos += perso
            e += ['# modèle %s (acteur %s) -> copie recolorée %s' % (anc, acteur, neuf), '[[event_command]]', 'event = %s' % _q(ev), 'list = %s' % _q(modeles[acteur].get('liste') or 'evt'),
                  'command = %s' % _q(modeles[acteur].get('commandeLoad') or 'CMD_799A1EBA'), 'args = [%s]' % _q(acteur), 'set = [%s, %s]' % (_q(acteur), _q(_valeur_load(modeles[acteur], anc, neuf))), '']
            rapport.append('modèle %s -> %s : %d texture(s) remplacée(s)' % (anc, neuf, len(info['textures'])))
            continue
        if acteur not in objets:
            continue
        copie = copie_objet(acteur, ev)
        imgs = reglage.get('textures') or {}
        lueurs = reglage.get('lueurs')
        mats = reglage.get('materiaux') or {}      # (14/11/2026) couleurs de matériau : {nom ou crc : [r, v, b]}
        # (14/11/2026) teintes des sommets {pièce : [H, C]} et des particules [H, C] : un bloc [[recolor]] par teinte sur la copie
        # (hue + colorize, mode = "set", saturation = valeur = 1 ; vertex_colors = pièces, particles = true)
        groupes = {}
        for piece, (h, c) in sorted((reglage.get('sommets') or {}).items()):
            groupes.setdefault((round(float(h), 1), round(float(c), 3)), [[], False])[0].append(piece)
        if reglage.get('particules'):
            h, c = reglage['particules']
            groupes.setdefault((round(float(h), 1), round(float(c), 3)), [[], False])[1] = True
        if not imgs and not lueurs and not mats and not groupes:
            continue
        e += ['[[recolor]]', 'object = %s' % _q(acteur), 'copy = %s' % _q(copie)]
        def _teinte(h, c, pieces, ptl):
            t = ['textures = "none"', 'materials = "none"', 'hue = %.1f' % h, 'mode = "set"', 'saturation = 1.0', 'value = 1.0',
                 'colorize = %.3f' % c]
            if pieces:
                t.append('vertex_colors = [%s]' % ', '.join(_q(x) for x in pieces))
            if ptl:
                t.append('particles = true')
            return t
        g_liste = sorted(groupes.items())
        if not imgs and not lueurs:                 # pas de textures : le 1er bloc (la copie) porte la 1re teinte, ou rien
            if g_liste:
                (h, c), (pcs, ptl) = g_liste.pop(0)
                e += _teinte(h, c, pcs, ptl)
            else:
                e += ['textures = "none"', 'materials = "none"']
        if imgs:
            e += ['  [recolor.images]']
            for tex, data in sorted(imgs.items()):
                b = base64.b64decode(data.split(',', 1)[1])
                os.makedirs(dossier_img, exist_ok=True)
                open(os.path.join(dossier_img, tex + '.png'), 'wb').write(b)
                e.append('  %s = %s' % (_q(tex), _q('assets/images/fx/%s/%s.png' % (nom, tex))))
        elif lueurs:
            e += ['textures = "none"', 'hue = %.1f' % lueurs['hue'], 'mode = "set"']
        # VRFW (winmm.dll, fx_engine::decl::TintDecl) : « an explicit colour for one material » ; `material` = UN nom (ou son
        # crc) par bloc ; op = "set" : la couleur fixe du G4MD et ses pistes G4MA prennent cette couleur (l'alpha reste)
        for nm, rvb in sorted(mats.items()):
            e += ['  [[recolor.tint]]', '  material = %s' % _q(nm), '  rgb = [%.4f, %.4f, %.4f]' % tuple(float(c) for c in rvb[:3]), '  op = "set"']
        e.append('')
        if lueurs:
            e += ['[[recolor]]', 'object = %s' % _q(copie), 'textures = "none"', 'materials = "all"',
                  'hue = %.1f' % float(lueurs['hue']), 'mode = "set"', 'saturation = %.2f' % float(lueurs.get('saturation', 1.2)),
                  'value = %.2f' % float(lueurs.get('value', 1.0)), 'mask_hue = [70, 330]' if lueurs.get('garder_or') else 'mask_hue = [0, 360]',
                  'vertex_colors = "all"', 'particles = true', '']
        for (h, c), (pcs, ptl) in g_liste:          # teintes suivantes : sur la copie, APRÈS les lueurs (sinon écrasées)
            e += ['[[recolor]]', 'object = %s' % _q(copie)] + _teinte(h, c, pcs, ptl) + ['']
        e += ['[[event_command]]', 'event = %s' % _q(ev), 'command = "CMD_799A1EBA"', 'args = [%s]' % _q(acteur),
              'set = [%s, %s]' % (_q(acteur), _q(objets[acteur]['chemin'].replace('/' + acteur + '/', '/' + copie + '/').replace(acteur + '.objbin', copie + '.objbin'))), '']
        rapport.append('objet %s -> %s : %d texture(s) remplacée(s)%s%s' % (acteur, copie, len(imgs), ', lueurs recolorées' if lueurs else '',
                                                                          ', %d couleur(s) de matériau' % len(mats) if mats else '')
                       + (', %d teinte(s) de sommets / particules' % len(groupes) if groupes else ''))
    for k, (aura, rvb) in enumerate(sorted((demande.get('auras') or {}).items())):
        info = next((a for a in infos_technique['auras'] if a['aura'] == aura), None)
        if not info:
            continue
        copie = '%s_%s_%d' % (MOD_ID.lower(), nom, k)
        e += ['[[recolor]]', 'aura = %s' % _q(aura), 'copy = %s' % _q(copie),
              'color = [[0.0, %.3f, %.3f, %.3f, 0.0]]' % tuple(float(c) for c in rvb), '']
        for acteur in info['acteurs']:
            e += ['[[event_command]]', 'event = %s' % _q(ev), 'command = "CMD_C3FB5CC5"', 'args = [%s, %s]' % (_q(acteur), _q(aura)),
                  'set = [%s, %s]' % (_q(acteur), _q(copie)), '']
        rapport.append('aura %s -> %s' % (aura, copie))
    tr = demande.get('trainee')
    if tr and tr.get('famille') and code.startswith('whs'):
        e += ['[[shot_aura]]', 'name = %s' % _q(nom), 'when = { techniques = [%s] }' % _q(key),
              'aura = %s' % _q(tr['famille']), 'color = %s' % _q(tr.get('element') or 'void'), '']
        rapport.append('traînée : %s en %s' % (tr['famille'], tr.get('element')))
    _ecrire(os.path.join(sortie, 'content', 'effects', nom + '.toml'), '\n'.join(e) + '\n')
    f_perso = os.path.join(sortie, 'content', 'characters', nom + '.toml')
    if len(persos) > 4:
        _ecrire(f_perso, '\n'.join(persos) + '\n')
    elif os.path.exists(f_perso):
        os.remove(f_perso)

    # --- bannière
    b = demande.get('banniere') or {}
    if (b.get('image') or b.get('texte')) and infos_technique.get('telop'):
        png = os.path.join(sortie, 'content', 'telops', 'any', key + '.png')
        os.makedirs(os.path.dirname(png), exist_ok=True)
        if b.get('image'):                      # bannière faite dans l'éditeur de bannières
            ecrire_png_banniere(b['image'], png)
        else:
            banniere(b['texte'], b.get('couleur', '#f5c842'), b.get('contour', '#0d1a4a'), png)
        f = os.path.join(sortie, 'content', 'telops', 'any', 'telops.toml')
        t = open(f, encoding='utf-8').read() if os.path.exists(f) else 'schema = "VRFW.telop_list/2"\n'
        t = re.sub(r'\n\[\[telop\]\]\nid = "%s"\nfrom = "[^"]*"\n' % key, '\n', t)
        t += '\n[[telop]]\nid = "%s"\nfrom = "%s"\n' % (key, infos_technique['telop'])
        _ecrire(f, t)
        rapport.append('bannière ' + ('de l\'éditeur' if b.get('image') else '« %s »' % b['texte']))

    # --- boutique d'Inazuma Fantasy
    if demande.get('prix'):
        _ecrire(os.path.join(sortie, 'addons', 'InazumaFantasy', 'content', 'shops', nom + '.toml'), '\n'.join([
            'schema = "VRFW.shop/2"', '', '[[edit]]', 'target = "InazumaFantasy.technique_shop"', '',
            '  [[edit.entry]]', '  technique = %s' % _q(nom), '  price = %d' % int(demande['prix']), '  currency = "tk_bb000001"', '']))
        rapport.append('boutique : %d jetons' % int(demande['prix']))

    deja = _deja_dans_le_mod(sortie)
    deja[nom] = {'key': key, 'id': ev, 'base': code, 'nom': demande['nom'], 'date': datetime.datetime.now().isoformat(timespec='seconds')}
    json.dump(deja, open(os.path.join(sortie, 'outil_techniques.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    # (16/11/2026) PAR DÉFAUT : cinématique livrée en fichiers (scene_en_fichiers ; VÉRIFIÉ EN JEU le 16/11 par muku :
    # Feinte angélique (couleurs), l'adversaire garde son visage). Si la scène ne s'y prête pas, la copie automatique de
    # VRFW (content/anims) est gardée et le rapport le dit.
    r_ = os.path.join(sortie, 'content', 'anims', nom + '.toml.retire')
    if os.path.exists(r_):
        os.remove(r_)
    try:
        r = scene_en_fichiers(cfg, nom)
        rapport += r.get('rapport') or ['cinématique : copie automatique de VRFW gardée (%s)' % r.get('erreur')]
    except Exception as ex:
        rapport.append('cinématique : copie automatique de VRFW gardée (%s)' % ex)
    return {'ok': True, 'dossier': sortie, 'rapport': rapport, 'key': key, 'id': ev}


def ecrire_png_banniere(data_url, png):
    """PNG de l'éditeur (data URL) -> fichier, après vérification : PNG de 1728 x 352"""
    brut = base64.b64decode(data_url.split(',', 1)[1])
    assert brut[:8] == b'\x89PNG\r\n\x1a\n', 'pas un PNG'
    w, h = struct.unpack('>II', brut[16:24])
    assert (w, h) == (1728, 352), 'bannière de %dx%d au lieu de 1728x352' % (w, h)
    os.makedirs(os.path.dirname(png), exist_ok=True)
    open(png, 'wb').write(brut)


def enregistrer_banniere(cfg, nom, image, telop_origine):
    """remplace la bannière d'une technique déjà créée par l'outil (sortie/MesTechniques), sans refaire le reste"""
    sortie = os.path.join(cfg['outil_dir'], 'sortie', MOD_ID)
    deja = _deja_dans_le_mod(sortie)
    if nom not in deja:
        return {'ok': False, 'erreur': 'Technique « %s » introuvable dans MesTechniques.' % nom}
    key = deja[nom]['key']
    ecrire_png_banniere(image, os.path.join(sortie, 'content', 'telops', 'any', key + '.png'))
    f = os.path.join(sortie, 'content', 'telops', 'any', 'telops.toml')
    t = open(f, encoding='utf-8').read() if os.path.exists(f) else 'schema = "VRFW.telop_list/2"\n'
    if 'id = "%s"' % key not in t:
        t += '\n[[telop]]\nid = "%s"\nfrom = "%s"\n' % (key, telop_origine)
        _ecrire(f, t)
    return {'ok': True, 'dossier': sortie, 'rapport': ['bannière de %s (%s) remplacée' % (deja[nom]['nom'], key),
                                                       'pas encore dans le jeu : « Installer dans le jeu » (onglet Techniques)']}


def jeu_ouvert():
    r = subprocess.run(['tasklist'], capture_output=True, text=True)
    return 'nie.exe' in r.stdout.lower()


def installer(cfg, mod_id=MOD_ID):
    """copie sortie/<mod_id> (MesTechniques ou MesEsprits) dans <jeu>/mods (sauvegarde avant), ajoute le mod à
    enabled.toml ; jeu fermé seulement"""
    if mod_id not in ('MesTechniques', 'MesEsprits', 'MesPersonnages', 'MesTenues', 'MesObjets', 'MesMaillots'):   # (pas de MesRetouches : jamais de remplacement)   # (15/11/2026) MesRetouches : remplacements
        return {'ok': False, 'erreur': 'Mod inconnu : ' + str(mod_id)}
    if jeu_ouvert():
        return {'ok': False, 'erreur': 'Le jeu est ouvert : ferme-le avant d\'installer.'}
    src = os.path.join(cfg['outil_dir'], 'sortie', mod_id)
    if not os.path.isfile(os.path.join(src, 'mod.toml')):
        return {'ok': False, 'erreur': 'Rien à installer : crée d\'abord le mod.'}
    for p in glob.glob(os.path.join(src, '**', '*.toml'), recursive=True):
        tomllib.load(open(p, 'rb'))
    mods = os.path.join(cfg['jeu_dir'], 'mods')
    dst = os.path.join(mods, mod_id)
    sauv = os.path.join(cfg['sauvegardes_dir'], mod_id + '_' + datetime.datetime.now().strftime('%Y%m%d_%H%M%S'))
    os.makedirs(sauv, exist_ok=True)
    if os.path.isdir(dst):
        shutil.copytree(dst, os.path.join(sauv, mod_id), dirs_exist_ok=True)
    en = os.path.join(mods, 'enabled.toml')
    shutil.copy(en, os.path.join(sauv, 'enabled.toml'))
    # (15/11/2026) techniques : AJOUT au mod du jeu (les techniques déjà installées restent, ex. La Flamme absente de la
    # sortie). Avant : le mod du jeu était vidé puis remplacé, ce qui retirait ces techniques. Esprits : remplacé comme
    # avant (mes_esprits.toml liste tous les esprits de la sortie). Dans les deux cas, l'ancienne version est sauvegardée.
    if os.path.isdir(dst) and mod_id != 'MesTechniques':
        shutil.rmtree(dst)
    shutil.copytree(src, dst, dirs_exist_ok=True)
    # (16/11/2026) fichiers retirés dans la sortie (« x.toml.retire », ex. la copie automatique d'une cinématique livrée en
    # fichiers) : leur ancienne version installée est retirée aussi (elle est dans la sauvegarde ci-dessus)
    for r_ in glob.glob(os.path.join(src, '**', '*.toml.retire'), recursive=True):
        vieux = os.path.join(dst, os.path.relpath(r_, src))[:-len('.retire')]
        if os.path.isfile(vieux):
            os.remove(vieux)
    t = open(en, encoding='utf-8').read()
    if '"%s"' % mod_id not in t:
        t2 = re.sub(r'enabled = \[(.*?)\]', lambda m: 'enabled = [%s, "%s"]' % (m.group(1), mod_id), t, count=1, flags=re.S)
        tomllib.loads(t2)
        open(en, 'w', encoding='utf-8').write(t2)
    return {'ok': True, 'dossier': dst, 'sauvegarde': sauv}



def reparer_modeles(cfg):
    """(15/11/2026) copies de modèles de technique faites avec un code de longueur différente (« e007000 » pour « ev60_00830 ») :
    fichier du modèle décalé, objet invisible en jeu. Refaites sous un code de même longueur (mêmes images recolorées, gardées
    dans assets/images/chr/<technique>/_textures.json) ; personnage et cinématique du mod mis à jour. Sauvegarde avant."""
    import subprocess
    sortie = os.path.join(cfg['outil_dir'], 'sortie', MOD_ID)
    f = os.path.join(sortie, 'outil_modeles.json')
    reg = json.load(open(f, encoding='utf-8')) if os.path.exists(f) else {}
    rapport, faits = [], 0
    for cle, ancien in list(reg.items()):
        nom = cle.split('|', 1)[0]
        f_ch = os.path.join(sortie, 'content', 'characters', nom + '.toml')
        if not os.path.exists(f_ch):
            continue
        ch = next((x for x in tomllib.load(open(f_ch, 'rb')).get('character', []) if x.get('base', {}).get('name') == ancien), None)
        if not ch or len(ancien) == len(ch['based_on']):
            continue
        anc = ch['based_on']
        if not faits:
            sauv = os.path.join(cfg.get('sauvegardes_dir') or os.path.join(cfg['outil_dir'], 'sauvegardes'),
                                MOD_ID + '_avant_reparation_' + datetime.datetime.now().strftime('%Y%m%d_%H%M%S'))
            shutil.copytree(sortie, sauv)
            rapport.append('sauvegarde : ' + sauv)
        del reg[cle]
        neuf, reg, f = _code_libre(cfg, anc, sortie, cle)
        f_tex = os.path.join(sortie, 'assets', 'images', 'chr', nom, '_textures.json')
        r = subprocess.run([sys.executable, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'clone_modele.py'),
                            cfg['data_dir'], anc, neuf, os.path.join(sortie, 'assets', 'chr'), f_tex], capture_output=True, text=True, timeout=900)
        if r.returncode != 0:
            raise RuntimeError('copie du modèle %s : %s' % (anc, (r.stderr or r.stdout)[-400:]))
        info = json.loads(r.stdout.strip().splitlines()[-1])
        vieux = os.path.join(sortie, 'assets', 'chr', info['dossier'], ancien) if info['dossier'] else os.path.join(sortie, 'assets', 'chr', ancien)
        if os.path.isdir(vieux):
            shutil.rmtree(vieux)
        for g in (f_ch, os.path.join(sortie, 'content', 'effects', nom + '.toml')):
            if os.path.exists(g):
                t = open(g, encoding='utf-8').read()
                for a, b in ((zlib.crc32(('mdl_' + ancien).encode()), zlib.crc32(('mdl_' + neuf).encode())), (zlib.crc32(ancien.encode()), zlib.crc32(neuf.encode()))):
                    t = t.replace('0x%08X' % a, '0x%08X' % b)
                t = re.sub(r'(?<![A-Za-z0-9])%s(?![0-9])' % re.escape(ancien), neuf, t)
                _ecrire(g, t)
        json.dump(reg, open(f, 'w', encoding='utf-8'), indent=1)
        faits += 1
        rapport.append('%s : modèle %s refait sous %s (au lieu de %s)' % (nom, anc, neuf, ancien))
    return {'ok': True, 'dossier': sortie, 'rapport': rapport or ['rien à réparer']}


def scene_en_fichiers(cfg, nom):
    """(16/11/2026) LA CINÉMATIQUE DE LA COPIE LIVRÉE EN FICHIERS, sans la copie automatique de VRFW (content/anims) :
    test de muku (Feinte angélique (couleurs), ev61_89100) : l'adversaire perd son visage. VRFW RÉÉCRIT les paquets
    d'animation de la scène copiée (32 512 -> 39 680 octets, images clés des coupes 3 et 5 décalées, LU dans son cache) ;
    ZanUltimateMod a eu le même symptôme et livre la scène en fichiers (README 0.9.36, Astral : marche en jeu ; 0.9.168 / 0.9.170).
    Méthode (Zan) : assets/event_cfg/{evt,eff,snd}/<id>… = fichiers d'origine, les paquets restent ceux du dossier d'origine ;
    seules les valeurs des [[event_command]] de la copie (objet d'effet / modèle recolorés) et la bannière changent, sur place,
    à longueur égale ; technique : event = <id> + [[event_env]] from = <scène d'origine> ; content/anims retiré.
    DÉDUIT : que le visage revienne (à vérifier en jeu)."""
    sortie = os.path.join(cfg['outil_dir'], 'sortie', MOD_ID)
    e = _deja_dans_le_mod(sortie).get(nom)
    if not e:
        return {'ok': False, 'erreur': 'technique inconnue : ' + str(nom)}
    f_anim = os.path.join(sortie, 'content', 'anims', nom + '.toml')
    f_tech = os.path.join(sortie, 'content', 'techniques', nom + '.toml')
    f_eff = os.path.join(sortie, 'content', 'effects', nom + '.toml')
    if not os.path.exists(f_anim):
        return {'ok': False, 'erreur': 'déjà livrée en fichiers (pas de content/anims/%s.toml)' % nom}
    ev_o, ev = tomllib.load(open(f_anim, 'rb'))['event'][0]['from'], e['id']
    from .anim import _commandes
    from . import cfgbin
    src = os.path.join(cfg['data_dir'], 'common', 'event_cfg')
    remplacer = {'evt': {}, 'eff': {}, 'snd': {}}
    # bannière : soccer10_01_<base> -> soccer10_01_<clé> (seulement si le mod a la bannière de la clé)
    t_tel = os.path.join(sortie, 'content', 'telops', 'any', 'telops.toml')
    if os.path.exists(t_tel) and ('id = "%s"' % e['key']) in open(t_tel, encoding='utf-8').read() and len(e['key']) == len(e['base']):
        remplacer['evt']['soccer10_01_' + e['base']] = 'soccer10_01_' + e['key']
    # valeurs des commandes de chargement que la copie change ([[event_command]] de content/effects)
    blocs_gardes, rapport = [], []
    d_eff = tomllib.load(open(f_eff, 'rb')) if os.path.exists(f_eff) else {}
    for c in d_eff.get('event_command', []):
        if c.get('event') != ev:
            continue
        liste = c.get('list') or 'eff'
        fichier = os.path.join(src, liste, ev_o + ('' if liste == 'evt' else '_' + liste) + '.cfg.bin')
        anc = next((a for _, cmd, a in _commandes(fichier) if cfgbin.NOMS.get(cmd, 'CMD_%08X' % cmd) == c['command'] or 'CMD_%08X' % cmd == c['command']
                    if a and a[0] == c['args'][0]), None)
        if not anc or len(anc) < 2 or len(c['set']) < 2 or anc[1] == c['set'][1]:
            continue
        assert len(anc[1]) == len(c['set'][1]), (anc[1], c['set'][1])
        # la table des textes d'une scène est partagée : le texte à changer ne doit servir qu'aux commandes de cet acteur
        autres = [a for _, cmd, a in _commandes(fichier) if anc[1] in a and (not a or a[0] != c['args'][0])]
        assert not autres, 'texte %s partagé par une autre commande' % anc[1]
        remplacer[liste][anc[1]] = c['set'][1]
        rapport.append('%s : %s -> %s' % (liste, anc[1], c['set'][1]))
    # fichiers livrés
    for liste, suf in (('evt', ''), ('eff', '_eff'), ('snd', '_snd')):
        f = os.path.join(src, liste, ev_o + suf + '.cfg.bin')
        if not os.path.exists(f):
            continue
        b = open(f, 'rb').read()
        for a, n in remplacer[liste].items():          # chaînes entières seulement (deux pareilles côte à côte : toutes)
            motif = rb'(?<=\0)' + re.escape(a.encode()) + rb'(?=\0)'
            assert re.search(motif, b), (liste, a)
            b = re.sub(motif, n.encode(), b)
        cfgbin.lire(b)                                 # relu : le fichier reste lisible
        _ecrire_octets(os.path.join(sortie, 'assets', 'event_cfg', liste, ev + suf + '.cfg.bin'), b)
    # technique : la scène livrée + event_env (comme Zan) ; plus de copie automatique ni de commandes
    t = open(f_tech, encoding='utf-8').read()
    t = re.sub(r'(?m)^event = .*$', 'event = %s' % _q(ev), t, count=1)
    if '[[event_env]]' not in t:
        t += '\n# (16/11/2026) cinématique livrée en fichiers (assets/event_cfg) : sa ligne d\'environnement vient de %s\n' % ev_o \
             + '[[event_env]]\nevent = %s\nfrom = %s\n' % (_q(ev), _q(ev_o))
    _ecrire(f_tech, t)
    os.replace(f_anim, f_anim + '.retire')
    if d_eff:
        x = open(f_eff, encoding='utf-8').read()
        x = re.sub(r'\n\[\[event_command\]\]\nevent = "%s"\n(?:[^\[\n][^\n]*\n)*' % re.escape(ev), '\n', x + '\n')
        _ecrire(f_eff, x.rstrip() + '\n')
    deja = _deja_dans_le_mod(sortie)
    deja[nom]['scene_fichiers'] = True
    json.dump(deja, open(os.path.join(sortie, 'outil_techniques.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    return {'ok': True, 'dossier': sortie, 'rapport': ['%s : cinématique %s livrée en fichiers (copie de %s)' % (nom, ev, ev_o)] + rapport
            + ['bannière : %s' % ('soccer10_01_' + e['key'] if remplacer['evt'] else 'celle d\'origine')]}


def _ecrire_octets(chemin, b):
    os.makedirs(os.path.dirname(chemin), exist_ok=True)
    open(chemin, 'wb').write(b)
