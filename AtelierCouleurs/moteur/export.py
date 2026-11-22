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


def id_echec(ev):
    """(22/11) id de la cinématique d'ÉCHEC de la copie : <id>_2 (le jeu nomme ses deux parties <dossier>_1 / <dossier>_2,
    qui partagent le dossier d'animation <dossier> ; IECross : event = "ev62_95120_1", fail_event = "ev62_95120_2")"""
    return ev + '_2'


def ecrire_anim(sortie, nom, ev0, ev, key, assigne, echec=None):
    """echec = cinématique d'échec d'origine (<scène>_2) ou None ; None garde celle déjà écrite (réparations)"""
    f = os.path.join(sortie, 'content', 'anims', nom + '.toml')
    if echec is None and os.path.exists(f):
        try:
            echec = next((x['from'] for x in tomllib.load(open(f, 'rb'))['event'][1:] if x.get('name') == nom + '_echec'), None)
        except (OSError, ValueError, KeyError):
            echec = None
    def bloc(n, de, id_):
        return (['[[event]]', 'name = %s' % _q(n), 'from = %s' % _q(de), 'id = %s' % _q(id_), 'telop = %s' % _q(key)]
                + (['# esprit invoqué (<ASSIGN>, choisi pendant le match) : ses animations sont livrées sous %s (comme Mukuro)' % ev,
                    'assigned = [%s]' % ', '.join(_q(k) for k in assigne)] if assigne else []))
    _ecrire(f, '\n'.join(['schema = "VRFW.anim/2"', 'owner = "match"', ''] + bloc(nom, ev0, ev)
                         + (['', '# (22/11) cinématique d\'échec (fail_event de la technique)'] + bloc(nom + '_echec', echec, id_echec(ev)) if echec else [])
                         + ['']))


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


def nom_copie_aura(nom, aura, k):
    """(22/11, essai des 858 techniques avec couleurs changées : 45 sur 138 retombaient dans la copie automatique de VRFW, celle
    qui fait perdre son visage à l'adversaire) la scène livrée en fichiers remplace le nom de l'aura EN PLACE (scene_en_fichiers :
    « même longueur ») : « mestechniques_<nom>_0 » n'avait jamais la longueur de « ball_aura_sptskill_lion ». Nom de MÊME
    LONGUEUR : « mt » + crc32 (nom, aura, n°) en hexa + « _ » + la fin du nom d'origine (unique, lisible). Aura de moins de
    12 lettres (aucune dans le jeu) : ancien nom."""
    n = len(aura)
    if n < 12:
        return '%s_%s_%d' % (MOD_ID.lower(), nom, k)
    tete = 'mt%08x_' % zlib.crc32(('%s|%s|%d' % (nom, aura, k)).encode())
    return tete + aura[len(tete):]


def _commandes_echec(cfg, e, ev, ev0_2, ev_2):
    """(22/11) copie automatique de VRFW (scène qui ne passe pas en fichiers) : les [[event_command]] de la copie, refaites
    pour la cinématique d'échec, seulement pour les acteurs que la scène d'échec charge par la même commande"""
    from .anim import _commandes
    from . import cfgbin
    src = os.path.join(cfg['data_dir'], 'common', 'event_cfg')
    out = []
    for c in tomllib.loads('\n'.join(e) + '\n').get('event_command', []):
        if c.get('event') != ev:
            continue
        liste = c.get('list') or 'eff'
        f = os.path.join(src, liste, ev0_2 + ('' if liste == 'evt' else '_' + liste) + '.cfg.bin')
        if not any(c['command'] in (cfgbin.NOMS.get(cmd), 'CMD_%08X' % cmd) and a and list(a[:len(c['args'])]) == list(c['args'])
                   for _, cmd, a in _commandes(f)):
            continue
        out += (['[[event_command]]', 'event = %s' % _q(ev_2)] + (['list = %s' % _q(c['list'])] if c.get('list') else [])
                + ['command = %s' % _q(c['command']), 'args = [%s]' % ', '.join(_q(x) for x in c['args']),
                   'set = [%s]' % ', '.join(_q(x) for x in c['set']), ''])
    return out


def _chaines_changees(a, b):
    """(22/11) remplacements faits SUR PLACE dans une scène livrée en fichiers (fichier d'origine a, livré b, même longueur) :
    {chaîne d'origine : chaîne livrée} ; la bannière « soccer10_01_<base>[_<CHARA_ID>] » est rendue sous sa forme courte"""
    if len(a) != len(b):
        return None
    out, i, n = {}, 0, len(a)
    while i < n:
        if a[i] == b[i]:
            i += 1
            continue
        g = a.rfind(b'\0', 0, i) + 1
        d = a.find(b'\0', i)
        d = n if d < 0 else d
        o, v = a[g:d].decode('utf-8', 'replace'), b[g:d].split(b'\0')[0].decode('utf-8', 'replace')
        if o.startswith('soccer10_01_'):
            o = re.sub(r'_<[^>]*>$', '', o)
        out[o] = v
        i = d + 1
    return out


def _livrer_scene(src, sortie, ev_o, ev_n, remplacer, strict):
    """fichiers {evt, eff, snd} de la scène ev_o livrés sous ev_n avec les remplacements (chaînes entières, même longueur ;
    bannière complétée d'octets nuls). strict : chaque chaîne doit être trouvée. -> chaînes remplacées [(liste, a)]"""
    from . import cfgbin
    faits = []
    for liste, suf in (('evt', ''), ('eff', '_eff'), ('snd', '_snd')):
        f = os.path.join(src, liste, ev_o + suf + '.cfg.bin')
        if not os.path.exists(f):
            continue
        b = open(f, 'rb').read()
        for a, n in remplacer.get(liste, {}).items():          # chaînes entières seulement (deux pareilles côte à côte : toutes)
            if a.startswith('soccer10_01_'):
                motif = rb'(?<=\0)' + re.escape(a.encode()) + rb'(?:_<[^\0>]*>)?(?=\0)'
                rempl = lambda m_, n=n: n.encode() + b'\0' * (len(m_.group(0)) - len(n))
            else:
                motif = rb'(?<=\0)' + re.escape(a.encode()) + rb'(?=\0)'
                rempl = n.encode()
            if not re.search(motif, b):
                assert not strict, (liste, a)
                continue
            b = re.sub(motif, rempl, b)
            faits.append((liste, a))
        cfgbin.lire(b)                                 # relu : le fichier reste lisible
        _ecrire_octets(os.path.join(sortie, 'assets', 'event_cfg', liste, ev_n + suf + '.cfg.bin'), b)
    return faits


def livrer_echec(cfg, sortie, nom, ev0_2=None):
    """(22/11) CINÉMATIQUE D'ÉCHEC d'une copie livrée en fichiers : <scène>_2 livrée sous <id>_2 avec LES MÊMES remplacements
    que la première partie (relus en comparant les fichiers déjà livrés à ceux du jeu : marche aussi pour les copies faites
    avant le 22/11), technique : fail_event = <id>_2 + [[event_env]] from = <scène>_2. -> ligne de rapport, ou None (rien à faire)"""
    e = _deja_dans_le_mod(sortie).get(nom)
    if not e or not e.get('scene_fichiers'):
        return None
    f_tech = os.path.join(sortie, 'content', 'techniques', nom + '.toml')
    f_anim = os.path.join(sortie, 'content', 'anims', nom + '.toml.retire')
    if not os.path.exists(f_tech) or not os.path.exists(f_anim):
        return None
    evs = tomllib.load(open(f_anim, 'rb'))['event']
    ev_o, ev = evs[0]['from'], e['id']
    if ev0_2 is None:
        ev0_2 = next((x['from'] for x in evs[1:] if x.get('name') == nom + '_echec'), None)
    if ev0_2 is None:                                  # copie faite avant le 22/11 : 2e partie lue dans l'index du jeu
        from .techniques import construire_index
        t_ = next((t for t in construire_index(cfg['data_dir'], os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'cache'))
                   if t['code'] == e['base']), None)
        ev0_2 = (t_ or {}).get('cinematique_2') if (t_ or {}).get('cinematique') == ev_o else None
    src = os.path.join(cfg['data_dir'], 'common', 'event_cfg')
    if not ev0_2 or not os.path.exists(os.path.join(src, 'evt', ev0_2 + '.cfg.bin')):
        return None
    ev_2 = id_echec(ev)
    remplacer = {}
    for liste, suf in (('evt', ''), ('eff', '_eff'), ('snd', '_snd')):
        a_, b_ = os.path.join(src, liste, ev_o + suf + '.cfg.bin'), os.path.join(sortie, 'assets', 'event_cfg', liste, ev + suf + '.cfg.bin')
        if os.path.exists(a_) and os.path.exists(b_):
            ch = _chaines_changees(open(a_, 'rb').read(), open(b_, 'rb').read())
            if ch is None:
                return 'cinématique d\'échec : première partie illisible (%s), échec d\'origine gardé' % (ev + suf)
            remplacer[liste] = ch
    faits = _livrer_scene(src, sortie, ev0_2, ev_2, remplacer, strict=False)
    t = open(f_tech, encoding='utf-8').read()
    t = re.sub(r'(?m)^fail_event = .*\n', '', t)
    t = re.sub(r'(?m)^(event = .*)$', lambda m_: m_.group(1) + '\nfail_event = %s' % _q(ev_2), t, count=1)
    if not re.search(r'(?m)^event = %s$' % re.escape(_q(ev_2)), t):
        t += '\n# (22/11) cinématique d\'échec livrée en fichiers : sa ligne d\'environnement vient de %s\n' % ev0_2 \
             + '[[event_env]]\nevent = %s\nfrom = %s\n' % (_q(ev_2), _q(ev0_2))
    _ecrire(f_tech, t)
    oublies = sorted({a for l_, d_ in remplacer.items() for a in d_} - {a for _, a in faits})
    return ('cinématique d\'échec %s livrée en fichiers (copie de %s, %d changement(s) repris)' % (ev_2, ev0_2, len(faits))
            + (' ; absents de l\'échec : %s' % ', '.join(oublies) if oublies else ''))


def reparer_echecs(cfg, sortie):
    """(22/11) copies livrées en fichiers avant le 22/11 sans leur cinématique d'échec : livrée à l'installation"""
    faits = []
    for nom, e in _deja_dans_le_mod(sortie).items():
        f_tech = os.path.join(sortie, 'content', 'techniques', nom + '.toml')
        if not e.get('scene_fichiers') or not os.path.exists(f_tech) or re.search(r'(?m)^fail_event = ', open(f_tech, encoding='utf-8').read()):
            continue
        try:
            r = livrer_echec(cfg, sortie, nom)
        except Exception as ex:
            r = 'cinématique d\'échec de %s non livrée (%s)' % (nom, ex)
        if r:
            faits.append('%s : %s' % (e.get('nom') or nom, r))
    return faits


def reparer_assignes(cfg, sortie):
    """(22/11, Frappe du loup d'un ami : pas de loup en jeu) avant le 22/11, seuls les esprits (k…) d'une cinématique étaient
    vus : une copie d'une technique à TOTEM (loup a000020 dans ev60_02700) ne livrait pas ses animations sous l'id neuf, et
    VRFW cache alors <ASSIGN>. Réparé à l'installation : paquets livrés + `assigned` (cinématique VRFW ou livrée en fichiers)."""
    from .coups import esprits_de_scene
    faits = []
    for f in glob.glob(os.path.join(sortie, 'content', 'anims', '*.toml')) + glob.glob(os.path.join(sortie, 'content', 'anims', '*.toml.retire')):
        try:
            x = tomllib.load(open(f, 'rb'))['event'][0]
            ev0, ev = x['from'], x['id']
        except (OSError, ValueError, KeyError, IndexError):
            continue
        ks = esprits_de_scene(cfg['data_dir'], ev0)
        manque = [k for k in ks if not glob.glob(os.path.join(sortie, 'assets', 'event', ev[:4], ev, '%s_%s_*.g4pk' % (ev, k)))]
        if not manque and (f.endswith('.retire') or set(ks) <= set(x.get('assigned') or [])):
            continue
        assigne = esprit_assigne(cfg, sortie, ev0, ev)
        if assigne and f.endswith('.toml'):
            ecrire_anim(sortie, os.path.basename(f)[:-5], ev0, ev, x.get('telop') or x.get('name'), assigne)
        if assigne:
            faits.append('%s (%s)' % (x.get('name'), ', '.join(assigne)))
    return faits


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
    # (22/11) CINÉMATIQUE D'ÉCHEC : LU dans skill_config, la fiche d'une technique porte après le crc32 de sa cinématique
    # (r[4]) celui de sa 2e partie <scène>_2 (r[6]) : vrai pour les 227 techniques qui en ont une (gardiens, défenses). Sans
    # fail_event, la copie jouait la scène d'échec de l'ORIGINAL (couleurs d'origine). Copiée comme la première.
    ev0_2 = infos_technique.get('cinematique_2')
    if ev0_2 and not os.path.exists(os.path.join(cfg['data_dir'], 'common', 'event_cfg', 'evt', ev0_2 + '.cfg.bin')):
        ev0_2 = None
    ev_2 = id_echec(ev) if ev0_2 else None
    if ev0_2:
        lignes.append('fail_event = %s' % _q('%s.%s_echec' % (MOD_ID, nom)))
    if demande.get('couleur_tir') is not None:
        lignes.append('color = %d' % int(demande['couleur_tir']))
    # (22/11) stats réglées plus tard (« En attente de stats ») : gardées quand la technique est refaite
    _stats_avant = (_deja_dans_le_mod(sortie).get(nom) or {}).get('stats')
    if _stats_avant:
        from . import stats as _st
        lignes += _st.lignes_technique(_stats_avant, _st.jeu_technique(cfg['data_dir'], code))
    for lg in ('fr', 'en', 'es', 'de', 'it', 'pt'):
        lignes += ['  [technique.text.%s]' % lg, '  name = %s' % _q(demande['nom'])]
        if desc:
            lignes.append('  description = %s' % _q(desc))
    _ecrire(os.path.join(sortie, 'content', 'techniques', nom + '.toml'), '\n'.join(lignes) + '\n')

    # --- cinématique copiée (+ animations de l'esprit invoqué, sinon VRFW le cache : voir esprit_assigne)
    assigne = esprit_assigne(cfg, sortie, ev0, ev)
    ecrire_anim(sortie, nom, ev0, ev, key, assigne, echec=ev0_2 or '')
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
        if acteur in modeles and reglage.get('textures') and modeles[acteur].get('espritDuJoueur'):
            # (22/11, VU EN JEU par muku : Frappe du loup (couleurs), loup recoloré dans la technique -> en jeu c'est le loup du
            # TOTEM du joueur) <ASSIGN> + INVARID = totem / esprit du lanceur, remplacé par le jeu : la copie recolorée ne
            # sert à rien, et sa commande (texte INVARID partagé) empêchait la cinématique livrée en fichiers -> non copiée
            rapport.append('modèle %s : c’est le totem / l’esprit du joueur qui lance (le jeu le choisit) -> pas copié ; '
                           'pour le recolorer, fais une copie dans l’onglet Totems ou Esprits' % modeles[acteur]['modeleActeur'])
            continue
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
        # (22/11, chasse aux bugs : journal VRFW de muku « [[recolor]] 1 (ev62891050): image not used: BallAura0010 (no such
        # texture) ») une texture EMPRUNTÉE à un autre objet (info 'source', ex. BallAura0010 de ev62006200 dans Muraille
        # impénétrable) n'est pas dans la planche de cet objet : VRFW ne peut pas la recolorer ici -> pas écrite, dite
        emprunts = {t['nom']: t['source'] for o in infos_technique.get('objets_details') or [] if o.get('acteur') == acteur
                    for t in o.get('textures') or [] if t.get('source')}
        for t_ in sorted(set(imgs) & set(emprunts)):
            rapport.append('texture %s : prise dans un autre objet (%s), le jeu ne la recolore pas dans cette copie -> ignorée'
                           % (t_, os.path.basename(emprunts[t_]).split('.')[0]))
        imgs = {k: v for k, v in imgs.items() if k not in emprunts}
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
        if re.search(r'<[A-Z_0-9]+>', aura):            # (22/11, LU dans nie.exe : voir app.js) aura choisie par le match
            rapport.append('aura %s : choisie par le match (balise), pas recolorable -> ignorée' % aura)
            continue
        copie = nom_copie_aura(nom, aura, k)
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
    if ev_2:
        e += _commandes_echec(cfg, e, ev, ev0_2, ev_2)
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
        var_ = ecrire_telops(cfg, sortie, key, infos_technique['telop'])
        rapport.append('bannière ' + ('de l\'éditeur' if b.get('image') else '« %s »' % b['texte'])
                       + (' (aussi sous ses variantes %s)' % ', '.join(var_) if var_ else ''))

    # --- boutique d'Inazuma Fantasy
    if demande.get('prix'):
        _ecrire(os.path.join(sortie, 'addons', 'InazumaFantasy', 'content', 'shops', nom + '.toml'), '\n'.join([
            'schema = "VRFW.shop/2"', '', '[[edit]]', 'target = "InazumaFantasy.technique_shop"', '',
            '  [[edit.entry]]', '  technique = %s' % _q(nom), '  price = %d' % int(demande['prix']), '  currency = "tk_bb000001"', '']))
        rapport.append('boutique : %d jetons' % int(demande['prix']))

    deja = _deja_dans_le_mod(sortie)
    deja[nom] = dict({'key': key, 'id': ev, 'base': code, 'nom': demande['nom'], 'date': datetime.datetime.now().isoformat(timespec='seconds')},
                     **({'stats': _stats_avant} if _stats_avant is not None else {}))
    json.dump(deja, open(os.path.join(sortie, 'outil_techniques.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    # (16/11/2026) PAR DÉFAUT : cinématique livrée en fichiers (scene_en_fichiers ; VÉRIFIÉ EN JEU le 16/11 par muku :
    # Feinte angélique (couleurs), l'adversaire garde son visage). Si la scène ne s'y prête pas, la copie automatique de
    # VRFW (content/anims) est gardée et le rapport le dit.
    r_ = os.path.join(sortie, 'content', 'anims', nom + '.toml.retire')
    if os.path.exists(r_):
        os.remove(r_)
    # (22/11) scène livrée en fichiers par une version précédente : retirée (si la nouvelle ne s'y prête pas, ces fichiers
    # restaient et VRFW refusait la copie automatique : « id ev60_89120 is already an event of … a mod's files »)
    for f_ in glob.glob(os.path.join(sortie, 'assets', 'event_cfg', '*', ev + '*.cfg.bin')):
        if re.fullmatch(re.escape(ev) + r'(_2)?(_eff|_snd)?\.cfg\.bin', os.path.basename(f_)):
            os.remove(f_)
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


def ecrire_telops(cfg, sortie, key, telop_origine):
    """(22/11, retour d'un joueur : la bannière d'une copie de Frappe du loup n'apparaissait pas ; VRFW : « the game has no
    telop whs96010 … retail telop kept ») la scène nomme sa bannière « soccer10_01_<base>_<CHARA_ID> » : le jeu a une bannière
    par lanceur (whs02700.g4tx + whs02700_a000020 / _a000350 / _a000390 .g4tx, LU dans dx11/menu/220_img/telop_waza). On
    déclare donc la bannière de la copie sous <clé> (from = <base>) ET sous chaque variante <clé>_<suffixe> (même image)."""
    base = re.sub(r'_<[^>]+>$', '', str(telop_origine))
    d = os.path.join(sortie, 'content', 'telops', 'any')
    png = os.path.join(d, key + '.png')
    variantes = sorted({os.path.basename(p)[len(base):-5] for p in glob.glob(os.path.join(
        cfg['data_dir'], 'dx11', 'menu', '220_img', 'telop_waza', 'fr', base + '_*.g4tx'))})
    f = os.path.join(d, 'telops.toml')
    t = open(f, encoding='utf-8').read() if os.path.exists(f) else 'schema = "VRFW.telop_list/2"\n'
    t = re.sub(r'\n\[\[telop\]\]\nid = "%s(?:_[^"]*)?"\nfrom = "[^"]*"\n' % re.escape(key), '\n', t)
    t += '\n[[telop]]\nid = "%s"\nfrom = "%s"\n' % (key, base)
    for v in variantes:
        t += '\n[[telop]]\nid = "%s%s"\nfrom = "%s%s"\n' % (key, v, base, v)
        if os.path.exists(png):
            shutil.copyfile(png, os.path.join(d, key + v + '.png'))
    _ecrire(f, t)
    return variantes


def enregistrer_banniere(cfg, nom, image, telop_origine):
    """remplace la bannière d'une technique déjà créée par l'outil (sortie/MesTechniques), sans refaire le reste"""
    sortie = os.path.join(cfg['outil_dir'], 'sortie', MOD_ID)
    deja = _deja_dans_le_mod(sortie)
    if nom not in deja:
        return {'ok': False, 'erreur': 'Technique « %s » introuvable dans MesTechniques.' % nom}
    key = deja[nom]['key']
    ecrire_png_banniere(image, os.path.join(sortie, 'content', 'telops', 'any', key + '.png'))
    ecrire_telops(cfg, sortie, key, telop_origine)      # (22/11) + variantes par lanceur, images refaites
    return {'ok': True, 'dossier': sortie, 'rapport': ['bannière de %s (%s) remplacée' % (deja[nom]['nom'], key),
                                                       'pas encore dans le jeu : « Installer dans le jeu » (onglet Techniques)']}


def jeu_ouvert():
    """(22/11, chasse aux bugs) sortie de tasklist lue en OCTETS : elle est dans la page de code de la console (cp850 en
    français : « 12 345 Ko » avec l'octet 0xFF) ; lue en texte (mode UTF-8 de Python, ou un nom avec É / ü en cp1252), le
    décodage échouait, stdout valait None et /api/etat comme « Installer » plantaient"""
    r = subprocess.run(['tasklist', '/FI', 'IMAGENAME eq nie.exe', '/NH'], capture_output=True,
                       creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
    return b'nie.exe' in (r.stdout or b'').lower()


def perdus_a_l_installation(src, dst, mod_id):
    """(21/11) noms des créations présentes dans <jeu>/mods/<mod> mais PAS dans la sortie : « Installer » les retirerait du jeu
    (le mod du jeu est remplacé ; MesTechniques seul est complété). Registres outil_*.json ; maillots : objets du mod."""
    if mod_id == 'MesTechniques' or not os.path.isdir(dst):
        return []
    perdus = []
    for f_j in glob.glob(os.path.join(dst, 'outil_*.json')):
        try:
            reg_j = json.load(open(f_j, encoding='utf-8'))
            f_s = os.path.join(src, os.path.basename(f_j))
            reg_s = json.load(open(f_s, encoding='utf-8')) if os.path.isfile(f_s) else {}
        except (OSError, ValueError):
            continue
        if isinstance(reg_j, dict):
            perdus += [(v.get('nom') if isinstance(v, dict) else None) or k for k, v in reg_j.items() if k not in reg_s]
    if mod_id == 'MesMaillots':
        def objets(d):
            out = {}
            for p in glob.glob(os.path.join(d, 'content', 'items', '*.toml')):
                try:
                    for it in tomllib.load(open(p, 'rb')).get('item') or []:
                        txt = (it.get('text') or {})
                        out[it.get('name')] = ((txt.get('fr') or txt.get('en') or {}).get('name')) or it.get('name')
                except (OSError, ValueError):
                    pass
            return out
        o_s = objets(src)
        # (22/11) même nom qu'un maillot gardé (ex. deux « Maillot Mukuro », dont un fait hors de l'Atelier) : on le dit
        perdus += [n + (' (ancienne version du même nom ; celle de l\'Atelier reste)' if n in o_s.values() else '')
                   for k, n in objets(dst).items() if k not in o_s]
    return list(dict.fromkeys(perdus))                 # un nom une fois (maillot domicile + extérieur : même nom)


def installer(cfg, mod_id=MOD_ID, forcer=False):
    """copie sortie/<mod_id> (MesTechniques ou MesEsprits) dans <jeu>/mods (sauvegarde avant), ajoute le mod à
    enabled.toml ; jeu fermé seulement. (21/11) forcer=False : refuse si des créations du jeu absentes de la sortie
    seraient retirées (« perdus », la page demande confirmation puis renvoie forcer=True)."""
    if mod_id not in ('MesTechniques', 'MesEsprits', 'MesPersonnages', 'MesTenues', 'MesObjets', 'MesMaillots'):   # (pas de MesRetouches : jamais de remplacement)   # (15/11/2026) MesRetouches : remplacements
        return {'ok': False, 'erreur': 'Mod inconnu : ' + str(mod_id)}
    if jeu_ouvert():
        return {'ok': False, 'erreur': 'Le jeu est ouvert : ferme-le avant d\'installer.'}
    src = os.path.join(cfg['outil_dir'], 'sortie', mod_id)
    if not os.path.isfile(os.path.join(src, 'mod.toml')):
        return {'ok': False, 'erreur': 'Rien à installer : crée d\'abord le mod.'}
    repares = reparer_assignes(cfg, src) if mod_id == 'MesTechniques' else []      # (22/11) copies à totem faites avant
    if mod_id == 'MesTechniques':                       # (22/11) copies sans leur cinématique d'échec (fail_event)
        repares += reparer_echecs(cfg, src)
    textes_mod(src, mod_id)                             # (22/11) nom et description du mod : anglais + traductions
    for p in glob.glob(os.path.join(src, '**', '*.toml'), recursive=True):
        tomllib.load(open(p, 'rb'))
    mods = os.path.join(cfg['jeu_dir'], 'mods')
    dst = os.path.join(mods, mod_id)
    perdus = perdus_a_l_installation(src, dst, mod_id)
    if perdus and not forcer:
        return {'ok': False, 'perdus': perdus, 'erreur': 'Installer retirerait du jeu : %s (absents de cet Atelier).' % ', '.join(perdus)}
    sauv =os.path.join(cfg['sauvegardes_dir'], mod_id + '_' + datetime.datetime.now().strftime('%Y%m%d_%H%M%S'))
    os.makedirs(sauv, exist_ok=True)
    if os.path.isdir(dst):
        shutil.copytree(dst, os.path.join(sauv, mod_id), dirs_exist_ok=True)
    en = os.path.join(mods, 'enabled.toml')
    if os.path.isfile(en):                              # (21/11) jeu sans enabled.toml : rien à sauvegarder (avant : plantage)
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
    # (22/11) inverse : une copie revenue à la copie automatique de VRFW (content/anims/x.toml actif) ne doit plus avoir sa
    # scène en fichiers dans le jeu (restes d'une installation précédente ; ils sont dans la sauvegarde ci-dessus)
    if mod_id == 'MesTechniques':
        for a_ in glob.glob(os.path.join(src, 'content', 'anims', '*.toml')):
            try:
                ev_ = tomllib.load(open(a_, 'rb'))['event'][0]['id']
            except (OSError, ValueError, KeyError, IndexError):
                continue
            for f_ in glob.glob(os.path.join(dst, 'assets', 'event_cfg', '*', ev_ + '*.cfg.bin')):
                if re.fullmatch(re.escape(ev_) + r'(_2)?(_eff|_snd)?\.cfg\.bin', os.path.basename(f_)) \
                        and not os.path.exists(os.path.join(src, os.path.relpath(f_, dst))):
                    os.remove(f_)
            vieux = os.path.join(dst, 'content', 'anims', os.path.basename(a_) + '.retire')
            if os.path.isfile(vieux):
                os.remove(vieux)
    r_en = reparer_enabled(en, sauv)                     # (22/11) enabled.toml créé par un Atelier d'avant / VRFW absent
    if r_en:
        repares.append(r_en)
    activer_mod(en, mod_id)
    r = {'ok': True, 'dossier': dst, 'sauvegarde': sauv}
    if repares:
        r['repares'] = repares
    try:                                                 # (22/11) contrôle des règles de VRFW (moteur/verifier_mods.py)
        from .verifier_mods import verifier
        pb = [t for g, f, t in verifier(cfg, os.path.dirname(src)) if f.split(os.sep)[0] == mod_id]
        if pb:
            r['controle'] = pb
    except Exception as ex:
        print('contrôle des mods :', ex)
    if not os.path.isdir(os.path.join(mods, 'VRFW')):   # (21/11) sans le chargeur de mods, rien ne se charge en jeu
        # (22/11, journal d'un joueur : son gestionnaire de mods utilisait une AUTRE installation du jeu) le dossier est nommé
        r['avertissement'] = ('VRFW n’est pas dans le dossier mods de ce jeu (%s) : le mod ne se chargera pas. Si ton gestionnaire '
                              'de mods utilise une autre installation du jeu, choisis-la dans ⚙ Paramètres > Dossier du jeu, puis '
                              'installe à nouveau. Sinon, installe VRFW (avec Inazuma Fantasy).' % cfg['jeu_dir'])
    return r


MES_MODS = ('MesTechniques', 'MesEsprits', 'MesPersonnages', 'MesTenues', 'MesObjets', 'MesMaillots')

# (22/11, « ce que tous les utilisateurs voient doit être traduit ») nom et description de nos mods dans le gestionnaire de mods
# et l'écran Mods de VRFW. Comme les autres mods (LU : InazumaFantasy, CharacterReforged, BetterQoL) : mod.toml = l'anglais
# (« English fallback of the text keys mod_name / mod_description »), text/keys.toml = une section [<langue>.new] par langue.
TEXTES_MODS = {
    'MesTechniques': {
        'en': ('My techniques', 'Recoloured techniques made with the Atelier Inazuma (copies: the original techniques do not change).'),
        'fr': ('Mes techniques', "Techniques recolorées créées avec l'Atelier Inazuma (copies : les techniques d'origine ne changent pas)."),
        'es': ('Mis supertécnicas', 'Supertécnicas recoloreadas creadas con el Atelier Inazuma (copias: las supertécnicas originales no cambian).')},
    'MesEsprits': {
        'en': ('My Keshin and totems', 'Recoloured copies of Keshin and totems, made with the Atelier Inazuma (the originals do not change). On sale at the Inazuma Fantasy training shop.'),
        'fr': ('Mes esprits et totems', "Copies recolorées d'esprits guerriers et de totems, créées avec l'Atelier Inazuma (les originaux ne changent pas). En vente dans la boutique d'entraînement d'Inazuma Fantasy."),
        'es': ('Mis Keshin y tótems', 'Copias recoloreadas de Keshin y tótems, creadas con el Atelier Inazuma (los originales no cambian). A la venta en la tienda de entrenamiento de Inazuma Fantasy.')},
    'MesPersonnages': {
        'en': ('My characters', 'Copies of characters with their head recoloured, made with the Atelier Inazuma (the originals do not change). In the ChronicleDeluxe Kizuna draw.'),
        'fr': ('Mes personnages', "Copies de personnages avec leur tête recolorée, créées avec l'Atelier Inazuma (les originaux ne changent pas). Au tirage Kizuna de ChronicleDeluxe."),
        'es': ('Mis personajes', 'Copias de personajes con la cabeza recoloreada, creadas con el Atelier Inazuma (los originales no cambian). En el sorteo Kizuna de ChronicleDeluxe.')},
    'MesTenues': {
        'en': ('My outfits', "Game outfits recoloured with the Atelier Inazuma, to equip (copies: the game's outfits do not change)."),
        'fr': ('Mes tenues', "Tenues du jeu recolorées avec l'Atelier Inazuma, à équiper (copies : les tenues du jeu ne changent pas)."),
        'es': ('Mis atuendos', 'Atuendos del juego recoloreados con el Atelier Inazuma, para equipar (copias: los atuendos del juego no cambian).')},
    'MesObjets': {
        'en': ('My items', 'Copies of game items (icon, name, description), made with the Atelier Inazuma. On sale at the Inazuma Fantasy general store.'),
        'fr': ('Mes objets', "Copies d'objets du jeu (icône, nom, description), créées avec l'Atelier Inazuma. En vente à la boutique générale d'Inazuma Fantasy."),
        'es': ('Mis objetos', 'Copias de objetos del juego (icono, nombre, descripción), creadas con el Atelier Inazuma. A la venta en la tienda general de Inazuma Fantasy.')},
}


def textes_mod(dossier, mod_id):
    """mod.toml : nom et description en anglais ; text/keys.toml : mod_name / mod_description en anglais, français, espagnol.
    MesMaillots : son écrivain (moteur/maillots/atelier_mod.py) le fait lui-même (sa description liste les maillots).
    Renvoie True si quelque chose a changé."""
    t = TEXTES_MODS.get(mod_id)
    f = os.path.join(dossier, 'mod.toml')
    if not t or not os.path.isfile(f):
        return False
    avant = open(f, encoding='utf-8').read()
    m = re.sub(r'(?m)^name = .*$', lambda _: 'name = ' + json.dumps(t['en'][0], ensure_ascii=False), avant, count=1)
    m = re.sub(r'(?m)^description = .*$', lambda _: 'description = ' + json.dumps(t['en'][1], ensure_ascii=False), m, count=1)
    cles = ['schema = "VRFW.text_key/1"', 'default_lang = "en"', '# Écrit par l\'Atelier Inazuma (nom et description du mod).', '']
    for lg in ('en', 'fr', 'es'):
        cles += ['[%s.new]' % lg, 'mod_name = ' + json.dumps(t[lg][0], ensure_ascii=False),
                 'mod_description = ' + json.dumps(t[lg][1], ensure_ascii=False), '']
    k = os.path.join(dossier, 'text', 'keys.toml')
    k_avant = open(k, encoding='utf-8').read() if os.path.isfile(k) else None
    k_neuf = '\n'.join(cles)
    if m == avant and k_avant == k_neuf:
        return False
    if m != avant:
        _ecrire(f, m)
    if k_avant != k_neuf:
        _ecrire(k, k_neuf)
    return True


def reparer_enabled(en, sauv=None):
    """(22/11) enabled.toml CRÉÉ par un Atelier d'avant le 22/11 (le jeu n'en avait pas) : il ne liste que nos mods, donc VRFW et
    tous les autres mods sont éteints. Reconnu ainsi (que des Mes*, pas VRFW, d'autres mods installés) -> retiré (copie dans la
    sauvegarde) : VRFW recharge alors tous les mods, comme avant. Renvoie la ligne de rapport, ou None."""
    if not os.path.isfile(en):
        return None
    try:
        ids = tomllib.load(open(en, 'rb')).get('enabled')
    except (OSError, ValueError):
        return None
    d = os.path.dirname(en)
    autres = [x for x in os.listdir(d) if os.path.isfile(os.path.join(d, x, 'mod.toml')) and x not in MES_MODS]
    if not isinstance(ids, list) or not ids:
        return None
    if set(ids) <= set(MES_MODS) and autres:
        if sauv:
            os.makedirs(sauv, exist_ok=True)
            shutil.copy(en, os.path.join(sauv, 'enabled.toml.cree_par_l_atelier'))
        os.remove(en)
        return 'enabled.toml (créé par une version précédente de l’Atelier, il éteignait VRFW et tes autres mods) retiré'
    # (22/11, 2.0.4, loader.log du même joueur : « mods: 0 enabled », « X skipped: requires `VRFW`, which is not enabled ») son
    # gestionnaire de mods a ensuite rallumé ses mods dans ce fichier, mais pas VRFW (qu'il ne montre pas) : plus rien ne charge.
    # VRFW installé mais absent de la liste, avec d'autres mods listés -> remis en tête (« VRFW first: the base, always loads
    # before every other mod (pinned) », load_order.toml de VRFW)
    if 'VRFW' not in ids and os.path.isfile(os.path.join(d, 'VRFW', 'mod.toml')) and any(x != 'VRFW' for x in ids):
        t = open(en, encoding='utf-8').read()
        m = re.search(r'enabled\s*=\s*\[', t)
        if not m:
            return None
        t2 = t[:m.end()] + '"VRFW", ' + t[m.end():]
        if tomllib.loads(t2).get('enabled', [None])[0] != 'VRFW':
            return None
        if sauv:
            os.makedirs(sauv, exist_ok=True)
            shutil.copy(en, os.path.join(sauv, 'enabled.toml.sans_vrfw'))
        open(en, 'w', encoding='utf-8').write(t2)
        return 'VRFW remis dans enabled.toml (il en manquait : aucun mod ne se chargeait)'
    return None


def activer_mod(en, mod_id):
    """(21/11) ajoute mod_id à enabled.toml de VRFW (créé s'il manque) ; une liste vide donne ["mod"] (avant : « [, "mod"] »,
    TOML invalide). Renvoie True si le fichier a changé."""
    os.makedirs(os.path.dirname(en), exist_ok=True)
    # (22/11, joueur : après « Installer », TOUS ses mods « ne seront pas chargés ») sans enabled.toml, VRFW charge tous les
    # mods (LU dans winmm.dll : « : every mod enabled », « not in enabled.toml », « requires `VRFW`, which is not enabled ») ;
    # le créer avec nos seuls mods éteignait VRFW et tous les autres -> on ne le crée plus
    if not os.path.isfile(en):
        return False
    t = open(en, encoding='utf-8').read()
    if '"%s"' % mod_id in t:
        return False
    m = re.search(r'enabled\s*=\s*\[(.*?)\]', t, re.S)
    if m:
        dedans = m.group(1).strip().rstrip(',').strip()
        t2 = t[:m.start()] + 'enabled = [%s"%s"]' % (dedans + ', ' if dedans else '', mod_id) + t[m.end():]
    else:
        t2 = t.rstrip() + ('\n' if t.strip() else '') + 'enabled = ["%s"]\n' % mod_id
    tomllib.loads(t2)
    open(en, 'w', encoding='utf-8').write(t2)
    return True



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
                    if a and list(a[:len(c['args'])]) == list(c['args'])), None)
        # (22/11, essai des 227 cinématiques d'échec : 3 retombaient ici) un acteur qui porte DEUX auras (ball_aura_out30_<BALL_AURA>
        # et l'aura recolorée) : la commande est celle dont les arguments sont ceux du bloc (acteur, aura), pas la 1re de l'acteur
        if not anc or len(anc) < 2 or len(c['set']) < 2 or anc[1] == c['set'][1]:
            continue
        assert len(anc[1]) == len(c['set'][1]), (anc[1], c['set'][1])
        # la table des textes d'une scène est partagée : le texte à changer ne doit servir qu'aux commandes de cet acteur
        autres = [a for _, cmd, a in _commandes(fichier) if anc[1] in a and (not a or a[0] != c['args'][0])]
        # (22/11, essai des 858 techniques : 7 tombaient ici) une AURA (CMD_C3FB5CC5) est recolorée pour tous ses acteurs, et
        # les autres commandes qui la nomment (la retirer, la poser sur un autre acteur) doivent viser la copie aussi :
        # remplacer le texte partout est alors exactement ce qu'il faut
        if c['command'] != 'CMD_C3FB5CC5':
            assert not autres, 'texte %s partagé par une autre commande' % anc[1]
        remplacer[liste][anc[1]] = c['set'][1]
        if '%s : %s -> %s' % (liste, anc[1], c['set'][1]) not in rapport:     # (22/11) une aura à plusieurs acteurs : une ligne
            rapport.append('%s : %s -> %s' % (liste, anc[1], c['set'][1]))
    # (22/11, Frappe du loup) <ASSIGN> = le totem / l'esprit DU JOUEUR qui lance (nie.exe : remplacement des balises ; table
    # GDSEventTagWordReplaceConfig). ESSAYÉ EN JEU le 22/11 : écrire le totem (a000020) à sa place NE MARCHE PAS (ses paquets
    # ne sont jamais ouverts : un acteur « a000020_s00 » n'est pas un modèle à charger) -> retiré, <ASSIGN> gardé.
    # Bannière « soccer10_01_<base>_<CHARA_ID> » (une par lanceur) : l'objet de menu « soccer10_01_<clé>_<CHARA_ID> »
    # n'existe pas (VRFW : « banner object … not found: the move shows no banner ») ; VRFW fait « soccer10_01_<clé> » :
    # la chaîne entière devient « soccer10_01_<clé> » (suffixe retiré, complété d'octets nuls : même longueur).
    # fichiers livrés
    _livrer_scene(src, sortie, ev_o, ev, remplacer, strict=True)
    # technique : la scène livrée + event_env (comme Zan) ; plus de copie automatique ni de commandes
    t = open(f_tech, encoding='utf-8').read()
    t = re.sub(r'(?m)^event = .*$', 'event = %s' % _q(ev), t, count=1)
    t = re.sub(r'(?m)^fail_event = .*\n', '', t)       # (22/11) refaite ci-dessous (livrer_echec) pour la scène en fichiers
    if '[[event_env]]' not in t:
        t += '\n# (16/11/2026) cinématique livrée en fichiers (assets/event_cfg) : sa ligne d\'environnement vient de %s\n' % ev_o \
             + '[[event_env]]\nevent = %s\nfrom = %s\n' % (_q(ev), _q(ev_o))
    _ecrire(f_tech, t)
    ev0_2 = next((x['from'] for x in tomllib.load(open(f_anim, 'rb'))['event'][1:] if x.get('name') == nom + '_echec'), '')
    os.replace(f_anim, f_anim + '.retire')
    if d_eff:
        x = open(f_eff, encoding='utf-8').read()
        x = re.sub(r'\n\[\[event_command\]\]\nevent = "%s(?:_2)?"\n(?:[^\[\n][^\n]*\n)*' % re.escape(ev), '\n', x + '\n')
        _ecrire(f_eff, x.rstrip() + '\n')
    deja = _deja_dans_le_mod(sortie)
    deja[nom]['scene_fichiers'] = True
    json.dump(deja, open(os.path.join(sortie, 'outil_techniques.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    echec = []
    if ev0_2:
        try:
            echec = [livrer_echec(cfg, sortie, nom, ev0_2) or 'cinématique d\'échec : celle d\'origine']
        except Exception as ex:
            echec = ['cinématique d\'échec : celle d\'origine (%s)' % ex]
    return {'ok': True, 'dossier': sortie, 'rapport': ['%s : cinématique %s livrée en fichiers (copie de %s)' % (nom, ev, ev_o)] + rapport
            + ['bannière : %s' % ('soccer10_01_' + e['key'] if remplacer['evt'] else 'celle d\'origine')] + echec}


def _ecrire_octets(chemin, b):
    os.makedirs(os.path.dirname(chemin), exist_ok=True)
    open(chemin, 'wb').write(b)
