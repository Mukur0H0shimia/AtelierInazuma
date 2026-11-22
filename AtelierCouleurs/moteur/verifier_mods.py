"""(22/11, chasse aux bugs) CONTRÔLE DE NOS MODS avant le jeu : les règles que VRFW a fait respecter dans le journal de muku
(%LOCALAPPDATA%\\VRFW\\logs\\loader.log / issues.log), vérifiées sur les fichiers de sortie/<mod> :
  1. [[event_env]] : la scène a sa ligne dans event_env_config_soccer_demo, ou `from`, ou une scène livrée par un de nos mods
     avec `from` (« ev83_00010 has no row … give `from` … (skipped) ») ;
  2. [[recolor]] images : chaque nom est dans la planche .g4tx de l'objet d'origine (« image not used: BallAura0010 (no such
     texture) ») ;
  3. une cinématique n'est pas à la fois livrée en fichiers (assets/event_cfg) ET copiée par VRFW (content/anims actif)
     (« id `ev60_89120` is already an event of the game or of a mod's files ») ;
  4. bannières : chaque [[telop]] a son image <id>.png ;
  5. (22/11) event / fail_event d'une technique désignent une scène qui existe (livrée, copie VRFW active, ou du jeu).
Lecture seule. -> liste de problèmes [(gravité, fichier, texte)] ; `python -m moteur.verifier_mods` pour l'Atelier."""
import glob, os, re, tomllib


def _toml(f):
    try:
        return tomllib.load(open(f, 'rb'))
    except (OSError, ValueError) as e:
        return {'_erreur': str(e)}


def verifier(cfg, racine_sortie):
    from .esprits import groupes_scene
    from . import g4
    pb = []
    mods = [m for m in ('MesTechniques', 'MesEsprits', 'MesPersonnages', 'MesTenues', 'MesObjets', 'MesMaillots')
            if os.path.isdir(os.path.join(racine_sortie, m))]
    # scènes livrées en fichiers / copiées par VRFW, dans tous nos mods
    fichiers_scene, anims_actifs, env_avec_from, noms_anims = {}, {}, set(), set()
    for m in mods:
        d = os.path.join(racine_sortie, m)
        for f in glob.glob(os.path.join(d, 'assets', 'event_cfg', 'evt', '*.cfg.bin')):
            fichiers_scene[os.path.basename(f)[:-len('.cfg.bin')]] = m
        for f in glob.glob(os.path.join(d, 'content', 'anims', '*.toml')):
            for e in _toml(f).get('event') or []:
                anims_actifs[e.get('id')] = os.path.relpath(f, racine_sortie)
                noms_anims.add('%s.%s' % (m, e.get('name')))
        for f in glob.glob(os.path.join(d, 'content', '**', '*.toml'), recursive=True):
            for e in _toml(f).get('event_env') or []:
                if e.get('from'):
                    env_avec_from.add(e.get('event'))
    for ev, f in anims_actifs.items():
        if ev in fichiers_scene:
            pb.append(('erreur', f, 'cinématique %s copiée par VRFW alors que %s la livre déjà en fichiers' % (ev, fichiers_scene[ev])))
    for m in mods:
        d = os.path.join(racine_sortie, m)
        for f in sorted(glob.glob(os.path.join(d, 'content', '**', '*.toml'), recursive=True)):
            rel = os.path.relpath(f, racine_sortie)
            t = _toml(f)
            if '_erreur' in t:
                pb.append(('erreur', rel, 'TOML illisible : ' + t['_erreur']))
                continue
            # 1. event_env
            for e in t.get('event_env') or []:
                ev = e.get('event')
                if e.get('from') or ev in env_avec_from or ev in fichiers_scene:
                    continue
                if groupes_scene(cfg, ev) == (None, None) and ev not in anims_actifs:
                    pb.append(('erreur', rel, '[[event_env]] %s : pas de ligne dans le jeu ni de `from` (VRFW l\'ignore)' % ev))
            # 2. recolor images
            for r in t.get('recolor') or []:
                objet, noms = r.get('object'), list((r.get('images') or {}))
                if not objet or not noms:
                    continue
                g = glob.glob(os.path.join(cfg['data_dir'], 'dx11', 'effect', '**', objet, objet + '.g4tx'), recursive=True)
                if not g:
                    continue
                try:
                    dans = set(g4.noms_textures_g4tx(open(g[0], 'rb').read()))   # même lecture que l'Atelier (G4TX.noms coupe)
                except Exception:
                    continue
                for n in noms:
                    if n not in dans:
                        pb.append(('avertissement', rel, '[[recolor]] %s : image %s absente de la planche de l\'objet (le jeu l\'ignore)' % (objet, n)))
            # 5. (22/11) event / fail_event d'une technique : une scène livrée en fichiers, une copie VRFW active
            # (« Mod.nom » = [[event]] name de content/anims) ou une scène du jeu
            for x in t.get('technique') or []:
                for cle in ('event', 'fail_event'):
                    v = x.get(cle)
                    if not isinstance(v, str):
                        continue
                    if '.' in v:
                        ok = v in noms_anims
                    else:
                        ok = v in fichiers_scene or os.path.exists(os.path.join(cfg['data_dir'], 'common', 'event_cfg', 'evt', v + '.cfg.bin'))
                    if not ok:
                        pb.append(('erreur', rel, 'technique %s : %s = %s introuvable (ni scène livrée, ni copie active, ni scène du jeu)'
                                   % (x.get('name'), cle, v)))
        # 4. bannières
        tt = os.path.join(d, 'content', 'telops', 'any', 'telops.toml')
        if os.path.exists(tt):
            for e in _toml(tt).get('telop') or []:
                if not os.path.exists(os.path.join(d, 'content', 'telops', 'any', str(e.get('id')) + '.png')):
                    pb.append(('avertissement', os.path.relpath(tt, racine_sortie), 'bannière %s sans image (celle du jeu sera montrée)' % e.get('id')))
    return pb


if __name__ == '__main__':
    import json, sys
    ici = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    sys.path.insert(0, ici)
    from moteur import donnees_virtuelles, config_auto
    cfg = json.load(open(os.path.join(ici, 'config.json'), encoding='utf-8'))
    if cfg.get('lecture_directe') or not config_auto._data_ok(cfg.get('data_dir')):
        cfg['data_dir'] = donnees_virtuelles.activer(cfg['jeu_dir'], os.path.join(ici, 'cache', 'data_jeu'))
    racine = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ici, 'sortie')
    p = verifier(cfg, racine)
    for g, f, t in p:
        print('%-13s %s : %s' % (g.upper(), f, t))
    print('%d problème(s)' % len(p))
