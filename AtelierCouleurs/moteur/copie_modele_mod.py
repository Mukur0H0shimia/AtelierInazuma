"""(25/11/2026) COPIE D'UNE TECHNIQUE DE MOD DONT UN MODÈLE VIENT D'UN .glb (retour de danifdez : « Tiger fang »).

Ce que fait le mod (LU, InazumaFantasy 25/11) :
  - content/models/props/tiger_fang/tiger_fang.toml : VRFW.model/1, kind « prop », target chr/_waza/ev63_86020/…, template
    chr/_waza/ev63_00300/… (Beast fang), glb + textures PNG dans assets/models/props/tiger_fang/ ;
  - content/characters/tiger_fang_model.toml : [[character]] base.name = « ev63_86020 », new_model from ev63_00300 ;
  - content/effects/tiger_fang.toml : [[event_command]] LOAD_ACTOR_RESOURCE set = [acteur, "ev63_86020"] pour les deux
    cinématiques (réussite ev63_86020, échec ev63_86021), copiées de Beast fang (content/anims, [[event]] from / id).
  VRFW construit le modèle au lancement (rien sur le disque du mod ; une version dans %LOCALAPPDATA%/VRFW/cache, lue
  seulement pour mesurer moteur/glb_vrfw.py).

Ce que fait la copie (DÉDUIT, pas encore vue en jeu) — les trois mêmes blocs que le mod, sous un code neuf :
  - notre propre VRFW.model/1 (même gabarit, .glb du mod recopié tel quel, PNG retouchés dans l'Atelier, les autres
    recopiés) dans content/models/<type>/<neuf>/ et assets/models/<type>/<neuf>/ ;
  - [[character]] base.name = neuf, based_on / new_model.from = le GABARIT du jeu (ev63_00300) ;
  - [[event_command]] LOAD_ACTOR_RESOURCE vers le code neuf, pour la cinématique copiée ET sa cinématique d'échec.
  La copie ne dépend pas du mod d'origine. Pourquoi pas [[recolor]] : VRFW refuse un objet fourni par un mod comme source
  (« no files (skipped) », essai en jeu du 23/11) ; pourquoi pas clone_modele.py : il ne réencode que le BC7 des fichiers
  du jeu et renomme des entrées que notre conversion ne porte pas.
Lecture seule des mods ; n'écrit que dans le dossier de sortie (MesTechniques).
"""
import os, re, json, zlib, base64, shutil

try:
    import tomllib
except ImportError:
    tomllib = None


# phrases entières (traduites telles quelles : web/i18n_en.js, web/i18n_es.js)
_FIN = ' : la copie n’est pas encore possible (aperçu et recoloration seulement).'
M_FICHIERS = 'Cette technique vient d’un mod qui a sa propre cinématique' + _FIN
M_PLANS = 'Cette technique vient d’un mod qui recompose la cinématique (plans, caméra)' + _FIN
M_AUCUN = 'Cette technique vient d’un mod qui ne change aucun modèle de la scène' + _FIN
M_PAS_GLB = 'Cette technique vient d’un mod dont le modèle n’est pas un .glb' + _FIN
M_AUTRE = 'Cette technique vient d’un mod qui change aussi d’autres choses dans la cinématique (effets, auras, commandes)' + _FIN
M_PAS_VU = ('Modèle d’un mod recopié par l’Atelier : pas encore vu en jeu. Après « Installer », lance le jeu et regarde '
            'le journal de VRFW (loader.log) : le modèle copié doit s’y charger sans erreur.')


def _q(s):
    return json.dumps(s, ensure_ascii=False)


def _valeur(v):
    if isinstance(v, bool):
        return 'true' if v else 'false'
    if isinstance(v, (int, float)):
        return repr(v)
    if isinstance(v, str):
        return _q(v)
    if isinstance(v, list):
        return '[%s]' % ', '.join(_valeur(x) for x in v)
    raise ValueError('valeur TOML non prise en charge : %r' % (v,))


def _toml(d):
    """dictionnaire d'un VRFW.model -> texte TOML (scalaires, puis [tables], puis [[listes de tables]])"""
    L = []
    for k, v in d.items():
        if not isinstance(v, dict) and not (isinstance(v, list) and v and all(isinstance(x, dict) for x in v)):
            L.append('%s = %s' % (k, _valeur(v)))
    for k, v in d.items():
        if isinstance(v, dict):
            L += ['', '[%s]' % k] + ['%s = %s' % (a, _valeur(b)) for a, b in v.items()]
    for k, v in d.items():
        if isinstance(v, list) and v and all(isinstance(x, dict) for x in v):
            for x in v:
                L += ['', '[[%s]]' % k] + ['%s = %s' % (a, _valeur(b)) for a, b in x.items()]
    return '\n'.join(L) + '\n'


def _code(chemin):
    return os.path.basename(str(chemin)).rsplit('.', 1)[0]


def modele_glb(cfg, code):
    """le VRFW.model/1 (avec .glb) dont la cible est « code » : entrée de glb_vrfw.trouver, ou None"""
    from . import glb_vrfw
    return next((m for m in glb_vrfw.trouver(cfg) if _code(m['def'].get('target', '')) == code), None)


def possible(cfg, t, details):
    """(oui, raison) : la copie d'une technique de mod est faite seulement quand on sait tout reproduire : cinématique du
    jeu (pas de fichiers de cinématique du mod), pas de plans recomposés, et, pour cette cinématique, le mod ne fait que
    remplacer des modèles par des modèles .glb (aucune autre commande, aucun objet recoloré ou ajouté)"""
    from . import mods_recolor, vrfw_anim
    from .mods_contenu import _tomls, _liste
    if t.get('racine_mod'):
        return False, M_FICHIERS
    ev = t.get('vrfw_event') or {}
    if ev.get('cuts') or t.get('vrfw_cameras'):
        return False, M_PLANS
    if set(ev) - {'name', 'from', 'id'}:                 # son, esprit assigné, places… : pas encore repris par la copie
        return False, M_AUTRE
    mm = details.get('modeles_mod') or {}
    for acteur, (_, code) in mm.items():
        if not modele_glb(cfg, code):
            return False, M_PAS_GLB
    mod, evs = t.get('mod_effets'), {t.get('event_id')}
    for m, f, tt in _tomls(os.path.join(cfg.get('jeu_dir') or '', 'mods')):
        if m != mod:
            continue
        for c in _liste(tt, 'event_command'):
            if not isinstance(c, dict) or c.get('event') not in evs:
                continue
            s = c.get('set') or []
            est_load = str(c.get('command', '')).upper() in ('CMD_799A1EBA', 'LOAD_ACTOR_RESOURCE')
            if not (est_load and len(s) >= 2 and s[0] in mm and s[1] == mm[s[0]][1]):
                return False, M_AUTRE
    if vrfw_anim.effets_ajoutes(cfg, mod, t.get('event_id')):
        return False, M_AUTRE
    for o in details.get('objets_details') or []:
        if not o.get('modeleActeur') and mods_recolor.pour(cfg, mod, os.path.basename(str(o.get('chemin', ''))).rsplit('.', 1)[0]):
            return False, M_AUTRE
    if not mm:
        return False, M_AUCUN
    return True, ''


def _pris_par_les_mods(cfg):
    """codes de modèles annoncés seulement dans des .toml (cibles de VRFW.model, [[character]] base.name) : invisibles
    dans les dossiers, mais pris en jeu"""
    from .mods_contenu import _tomls, _liste
    pris = set()
    for m, f, tt in _tomls(os.path.join(cfg.get('jeu_dir') or '', 'mods')):
        if isinstance(tt.get('target'), str):
            pris.add(_code(tt['target']))
        for c in _liste(tt, 'character'):
            if isinstance(c, dict) and isinstance((c.get('base') or {}).get('name'), str):
                pris.add(c['base']['name'])
    return pris


def code_neuf(cfg, anc, sortie, cle):
    """code neuf de même longueur (comme export._code_libre) qui n'est ni un dossier du jeu / des mods ni un code annoncé
    dans un .toml de mod ; gardé dans outil_modeles.json (la même technique et le même acteur gardent leur code)"""
    from . import export
    f = os.path.join(sortie, 'outil_modeles.json')
    reg0 = json.load(open(f, encoding='utf-8')) if os.path.exists(f) else {}
    if len(reg0.get(cle) or '') == len(anc):           # déjà donné à cette technique et cet acteur : le même (copie refaite ;
        return reg0[cle]                                # une fois installé, notre propre mod l'annonce aussi)
    extra = _pris_par_les_mods(cfg) - set(reg0.values())
    for _ in range(200):
        neuf, reg, f = export._code_libre(cfg, anc, sortie, cle)
        if neuf not in extra:
            json.dump(reg, open(f, 'w', encoding='utf-8'), indent=1)
            return neuf
        # code annoncé par un mod : réservé sous une clé à part, puis on redemande
        reg.pop(cle, None)
        reg['_pris_par_un_mod|' + neuf] = neuf
        json.dump(reg, open(f, 'w', encoding='utf-8'), indent=1)
    raise RuntimeError('plus de code libre pour une copie de ' + anc)


def correspondance_textures(cfg, m):
    """{case du gabarit (nom vu dans l'Atelier) : nom du PNG du mod} ; c'est sous les noms des cases que la conversion
    (moteur/glb_vrfw.py) range les images, donc que l'Atelier montre et retouche les textures"""
    from . import g4
    t = m['def']
    tpl = t['template'].replace('\\', '/').lstrip('/')
    tpl = tpl[len('common/'):] if tpl.startswith('common/') else tpl
    ob = g4.ObjetEffet(cfg['data_dir'], 'common/' + tpl[:-6] + '.objbin')
    mat_de = {x['nom']: k for k, x in enumerate(ob.materiaux)}
    out = {}
    for x in t.get('material') or []:
        if isinstance(x, dict) and x.get('from') in mat_de:
            for case, png in zip(ob.materiaux[mat_de[x['from']]].get('textures') or [], x.get('textures') or []):
                out.setdefault(case, png)
    return out


def copier(cfg, sortie, nom, acteur, infos_modele, images, evenements):
    """copie du modèle .glb d'un mod pour la technique copiée « nom » : fichiers dans sortie ; renvoie
    {persos: lignes de content/characters, commandes: lignes de [[event_command]], rapport: […]}
    images : {case : dataURL PNG} retouchées dans l'Atelier ; evenements : cinématiques de la copie (réussite, échec)"""
    code_mod = infos_modele['modeleActeur']
    m = modele_glb(cfg, code_mod)
    if m is None:
        raise ValueError('modèle .glb introuvable : ' + code_mod)
    d = json.loads(json.dumps(m['def']))
    tpl = _code(d['template'])
    neuf = code_neuf(cfg, code_mod, sortie, nom + '|' + acteur)
    rel = os.path.relpath(os.path.dirname(m['toml']), os.path.join(cfg['jeu_dir'], 'mods', m['mod'], 'content', 'models'))
    genre = rel.replace('\\', '/').split('/')[0] or 'props'
    dc = os.path.join(sortie, 'content', 'models', genre, neuf)
    da = os.path.join(sortie, 'assets', 'models', genre, neuf)
    os.makedirs(os.path.join(da, 'textures'), exist_ok=True)

    def ren(s):
        return s.replace(code_mod, neuf) if isinstance(s, str) else s
    # noms des textures : celui du mod avec le code neuf (ev63_86020_10 -> ev63_97000_10) ; sans le code : préfixé
    noms_tex = {}
    for x in d.get('texture') or []:
        if isinstance(x, dict) and isinstance(x.get('name'), str):
            noms_tex[x['name']] = ren(x['name']) if code_mod in x['name'] else '%s_%s' % (neuf, x['name'])
    for x in d.get('material') or []:
        for n in (x.get('textures') or []) if isinstance(x, dict) else []:
            noms_tex.setdefault(n, ren(n) if code_mod in n else '%s_%s' % (neuf, n))
    # PNG : retouchés dans l'Atelier (par case du gabarit) ou recopiés du mod
    cases = correspondance_textures(cfg, m)
    png_de_case = {case: png for case, png in cases.items()}
    retouches = []
    for case, data in sorted((images or {}).items()):
        png = png_de_case.get(case)
        if not png or png not in noms_tex:
            continue
        open(os.path.join(da, 'textures', noms_tex[png] + '.png'), 'wb').write(base64.b64decode(data.split(',', 1)[1]))
        retouches.append(case)
    for ancien, nv in noms_tex.items():
        dst = os.path.join(da, 'textures', nv + '.png')
        src = os.path.join(m['textures'], ancien + '.png')
        if not os.path.exists(dst) and os.path.exists(src):
            shutil.copy2(src, dst)
    shutil.copy2(m['glb'], os.path.join(da, neuf + '.glb'))
    # déclaration : celle du mod, code neuf
    d['name'] = neuf
    d['target'] = ren(d['target'])
    d['glb'] = neuf + '.glb'
    for x in d.get('material') or []:
        if isinstance(x, dict):
            if isinstance(x.get('rename'), str):
                x['rename'] = ren(x['rename'])
            x['textures'] = [noms_tex.get(n, n) for n in x.get('textures') or []]
    for x in d.get('texture') or []:
        if isinstance(x, dict) and x.get('name') in noms_tex:
            x['name'] = noms_tex[x['name']]
    if isinstance((d.get('textures') or {}).get('container'), str):
        d['textures']['container'] = ren(d['textures']['container'])
    texte = '# Copie (Atelier Couleurs) du modèle %s du mod %s, pour « %s ».\n' % (code_mod, m['mod'], nom) + _toml(d)
    tomllib.loads(texte)
    os.makedirs(dc, exist_ok=True)
    open(os.path.join(dc, neuf + '.toml'), 'w', encoding='utf-8').write(texte)
    # [[character]] : comme le mod (base = code neuf), modèle d'origine = le gabarit du jeu
    cible = d['target'].replace('\\', '/')
    cible = cible[len('common/'):] if cible.startswith('common/') else cible
    sous = '/'.join(cible.split('/')[1:-1])            # « _waza/ev63_97000 »
    persos = ['[[character]]', 'name = %s' % _q('%s_%s' % (nom, neuf)), 'based_on = %s' % _q(tpl), 'battle = false', '',
              '  [character.base]', '  id = 0x%08X                                         # crc32("%s")' % (zlib.crc32(neuf.encode()), neuf),
              '  name = %s' % _q(neuf), '', '  [character.new_model]',
              '  id = 0x%08X                                         # crc32("mdl_%s")' % (zlib.crc32(('mdl_' + neuf).encode()), neuf),
              '  from = %s                                  # gabarit du modèle du mod, écrit comme le mod (LU : InazumaFantasy)' % _q(tpl),
              '  [character.new_model.cells]', '  skeleton_path = %s' % _q('%s/%s.objbin' % (sous, neuf)), '']
    commandes = []
    for ev in evenements:
        if not ev:
            continue
        commandes += ['# modèle %s du mod %s (acteur %s) -> copie %s' % (code_mod, m['mod'], acteur, neuf), '[[event_command]]',
                      'event = %s' % _q(ev), 'list = %s' % _q(infos_modele.get('liste') or 'evt'),
                      'command = "CMD_799A1EBA"                 # LOAD_ACTOR_RESOURCE',
                      'args = [%s]' % _q(acteur), 'set = [%s, %s]' % (_q(acteur), _q(neuf)), '']
    rapport = ['modèle %s du mod %s (.glb) -> copie %s : %d texture(s) retouchée(s), %d recopiée(s)'
               % (code_mod, m['mod'], neuf, len(retouches), len(noms_tex) - len(retouches)), M_PAS_VU]
    return {'persos': persos, 'commandes': commandes, 'rapport': rapport, 'neuf': neuf}
