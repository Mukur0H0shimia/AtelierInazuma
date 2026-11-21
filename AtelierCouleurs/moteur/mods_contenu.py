"""(17/11/2026) Ce que les MODS déclarent dans leurs .toml (VRFW), pour les onglets de l'Atelier (demande de muku : « ajoute
l'option mod sur les techniques, les esprits guerriers, totems, maillots » et les objets de BOUTIQUE, pas les modèles 3D).
TOUS les mods du dossier <jeu>/mods, activés ou non. Lecture seule.

Formes LUES dans les mods installés (17/11/2026) :
- objets (VRFW.item/2) : [[item]] name / base (objet du jeu copié) / category / icon_key / [item.text.fr] name, description ;
  [[VRFW.Outfit]] Name / IconKey / [VRFW.Outfit.Text.fr] Name, Description (tenues vendues) ;
- maillots : [[item]] category = "kit", model = { uniform = "Mod.kit" ou crc32 } -> [[kit]] name, [[kit.model]] type 0
  (domicile) / 1 (extérieur), cells.uniformFielderModelIdCrc = nom d'un [[clothes]] -> from (coupe du jeu, chara_parts)
  + rows[0].upper_texture (« _uniform/<dossier>/<fichier>.g4tx », dans assets/chr/ du mod ou dans le jeu) ;
- techniques (VRFW.technique/3) : [[technique]] name / base (technique du jeu) / event (cinématique : du jeu « ev63_… »
  ou du mod « Mod.nom ») / element / [technique.text.fr] name ;
- esprits (VRFW.character/2) : [[character]] based_on = k… (esprit du jeu) / new_model.cells.skeleton_path =
  « _keshin/<code>/<code>.objbin », fichiers dans assets/chr/_keshin/<code>/ (même forme que le jeu : .g4pkm .g4mg .g4tx).
Pas lus : esprits seulement en .glb (Michael astral k002093), cinématiques propres aux mods (la technique s'ouvre alors
avec la cinématique de sa technique de base).
"""
from moteur import langue as _langue  # noqa: E402  (FR / EN)
import os, re, glob, zlib

try:
    import tomllib
except ImportError:
    tomllib = None

_TOML = {}            # chemin -> (mtime, contenu)


def _tomls(mods_dir):
    """[(mod, fichier, contenu)] de tous les .toml de content/ (et addons/*/content) ; relus seulement s'ils ont changé"""
    out = []
    for mod in sorted(os.listdir(mods_dir), key=str.lower):
        r = os.path.join(mods_dir, mod)
        if not os.path.isfile(os.path.join(r, 'mod.toml')):
            continue
        for f in glob.glob(os.path.join(r, 'content', '**', '*.toml'), recursive=True) + \
                 glob.glob(os.path.join(r, 'addons', '*', 'content', '**', '*.toml'), recursive=True):
            try:
                m = os.path.getmtime(f)
                if _TOML.get(f, (None,))[0] != m:
                    _TOML[f] = (m, tomllib.load(open(f, 'rb')))
                out.append((mod, f, _TOML[f][1]))
            except Exception:
                continue
    return out


def _liste(t, cle):
    v = t
    for k in cle.split('.'):
        v = v.get(k) if isinstance(v, dict) else None
    return v if isinstance(v, list) else []


def _texte(x, champ='name', cles=('text', 'Text')):
    for c in cles:
        tx = x.get(c) or {}
        for lg in ('fr', 'en'):
            v = (tx.get(lg) or {}).get(champ) or (tx.get(lg) or {}).get(champ.capitalize())
            if v:
                return re.sub(r'\[([^/\]]*)/[^\]]*\]', r'\1', str(v))
    return None


def _code(mod, nom):
    return re.sub(r'[^\w~-]', '_', '%s~%s' % (mod, nom))


CATEGORIES = {'shoes': 'Crampons', 'gloves': 'Bracelets et gants', 'bracelet': 'Bracelets et gants', 'pendant': 'Accessoires',
              'accessory': 'Accessoires', 'special': 'Objets spéciaux', 'consumable': 'Consommables', 'costume': 'Tenues (costumes)',
              'synergy': 'Synergies', 'emblem': 'Emblèmes', 'title': 'Titres', 'key': 'Objets importants', 'name_plate': 'Plaques nominatives',
              'craft': 'Objets de construction', 'collectible': 'Objets spéciaux', 'currency': 'Monnaies'}


def construire(cfg, cache_dir, actifs, objets_jeu_liste, persos_jeu, techniques_jeu, maillots_jeu=()):
    """{'objets': [...], 'maillots': [...], 'techniques': [...], 'esprits': [...]} ; chaque entrée a mod, actif, code « Mod~nom »"""
    mods_dir = os.path.join(cfg.get('jeu_dir') or '', 'mods')
    D = cfg['data_dir']
    if not os.path.isdir(mods_dir):
        return {}
    T = _tomls(mods_dir)
    out = {'objets': [], 'maillots': [], 'techniques': [], 'esprits': []}
    vus = set()

    def ajouter(cat, e, mod):
        c0 = e['code']; k = 2
        while (cat, e['code']) in vus:
            e['code'] = '%s~%d' % (c0, k); k += 1
        vus.add((cat, e['code']))
        e.update(mod=mod, actif=mod in actifs, cat=cat)
        out[cat].append(e)

    # ---------------------------------------------------------------- icônes (jeu, puis planches du mod)
    from .objets_jeu import _images_menu
    from .mods_jeu import noms_g4tx
    im = _images_menu(D, cache_dir)
    obj_jeu = {o['code']: o for o in objets_jeu_liste}
    icones_mod = {}

    def icone(mod, cle):
        if not cle:
            return None
        if cle in im:
            f, k, n = im[cle]
            return {'nom': cle, 'fichier': f, 'image': k, 'nb': n}
        if mod not in icones_mod:
            d = {}
            for g in glob.glob(os.path.join(mods_dir, mod, 'assets', 'menu', '**', '*.g4tx'), recursive=True) + \
                     glob.glob(os.path.join(mods_dir, mod, 'assets', 'images', '**', '*.g4tx'), recursive=True):
                try:
                    l = noms_g4tx(g)
                except Exception:
                    continue
                for j, n in enumerate(l):
                    d.setdefault(n, (g, j, len(l)))
                d.setdefault(os.path.basename(g)[:-5], (g, 0, len(l)))
            icones_mod[mod] = d
        x = icones_mod[mod].get(cle)
        return {'nom': cle, 'abs': x[0], 'image': x[1], 'nb': x[2]} if x else None

    # ---------------------------------------------------------------- tables des maillots (tous les mods)
    kits, habits = {}, {}
    for mod, f, t in T:
        for k in _liste(t, 'kit'):
            if isinstance(k, dict) and isinstance(k.get('id'), int):          # forme IECross : id = crc32("Mod.kit")
                kits.setdefault(k['id'] & 0xFFFFFFFF, (mod, k))
            if isinstance(k, dict) and k.get('name'):
                kits.setdefault(k['name'], (mod, k))
                kits.setdefault(zlib.crc32(k['name'].encode()), (mod, k))
                kits.setdefault(zlib.crc32(('%s.%s' % (mod, k['name'])).encode()), (mod, k))
        for c in _liste(t, 'clothes'):
            if isinstance(c, dict) and c.get('model'):
                habits.setdefault(c['model'], (mod, c))
                habits.setdefault(zlib.crc32(str(c['model']).encode()), (mod, c))
    parties = None
    from .mods_jeu import _chemins_jeu
    gp = {}                                                     # mod -> {chemin du jeu (dossier): dossier assets/models/…}

    def fichier(mod, rel, cote):
        """fichier « chr/… » du jeu tel qu'un mod le fournit (assets/<chemin>, ou assets/models/<type>/<nom>/<common|dx11> dont le
        .toml donne game_path = ce dossier), sinon celui du jeu"""
        for m in [mod] + [x for x in os.listdir(mods_dir) if x != mod and os.path.isdir(os.path.join(mods_dir, x, 'assets'))]:
            f = os.path.join(mods_dir, m, 'assets', *rel.split('/'))
            if os.path.exists(f):
                return f
            if m not in gp:
                g = {}
                for nom, chemin in _chemins_jeu(os.path.join(mods_dir, m)).items():
                    for d in glob.glob(os.path.join(mods_dir, m, 'assets', 'models', '*', nom)):
                        g.setdefault(chemin, d)
                gp[m] = g
            d = gp[m].get(os.path.dirname(rel))
            if d and os.path.exists(os.path.join(d, cote, os.path.basename(rel))):
                return os.path.join(d, cote, os.path.basename(rel))
            if m == mod and os.path.exists(os.path.join(D, cote, *rel.split('/'))):
                return os.path.join(D, cote, *rel.split('/'))      # le jeu passe avant les AUTRES mods
        return os.path.join(D, cote, *rel.split('/'))

    def maillot(mod, it):
        nonlocal parties
        u = (it.get('model') or {}).get('uniform')
        k = kits.get(u.split('.', 1)[-1] if isinstance(u, str) else (u & 0xFFFFFFFF) if isinstance(u, int) else None)
        if not k:
            return None
        cotes = {}
        for m in k[1].get('model') or []:
            nom = ((m.get('cells') or {}).get('uniformFielderModelIdCrc')) or m.get('fielder')   # nom, ou crc32 du nom
            h = habits.get(nom & 0xFFFFFFFF if isinstance(nom, int) else nom)
            if not h:
                continue
            rows = h[1].get('rows') or [{}]
            r0 = rows[0] or {}
            if parties is None:
                from .copies_tenues import _parties
                parties = _parties(D)
            if isinstance(r0, list):              # forme IECross : ligne de chara_parts [coupe, texture, …]
                coupe, tex = r0[0] if r0 and isinstance(r0[0], str) else None, r0[1] if len(r0) > 1 and isinstance(r0[1], str) else None
            else:                                 # forme ChronicleDeluxe / MesMaillots : from = vêtement du jeu, upper_texture
                tex = r0.get('upper_texture')
                r = (parties['clothes'].get(h[1].get('from') or h[1]['model']) or [None])[0]
                coupe = r[0] if r and isinstance(r[0], str) else None
            if not coupe or not tex:
                continue
            r = [coupe]
            md = fichier(h[0], 'chr/' + coupe, 'common')
            tx = fichier(h[0], 'chr/' + tex, 'dx11')
            if os.path.exists(md) and os.path.exists(tx):
                cotes[m.get('type', 0)] = (md, tx, r[0])
        if 0 not in cotes:
            return None
        md, tx, rel = cotes[0]
        return {'md': md, 'tx': tx, 'chemin_jeu': rel, 'tx20': cotes.get(1, (None, None))[1]}

    # ---------------------------------------------------------------- objets et maillots
    mj = {x['code']: x for x in maillots_jeu}
    for mod, f, t in T:
        for it in _liste(t, 'item'):
            if not isinstance(it, dict) or not it.get('name'):
                continue
            nom = _texte(it) or it['name']
            if it.get('category') == 'kit':
                m = maillot(mod, it)
                if not m:
                    # (kit du jeu vendu par le mod, ex. ChronicleDeluxe rival_kits : model.uniform = id d'un kit de
                    # uniform_config) DÉDUIT : l'icône « uni_<maillot> » montre le maillot du jeu vendu
                    g = mj.get(str(it.get('icon_key') or '')[4:]) or mj.get(str(it.get('base') or '')[4:])
                    if g:
                        ajouter('maillots', dict(g, code=_code(mod, it['name']), nom='%s · %s' % (nom, mod), sorte='Maillot',
                                                  base=it.get('base'), maillot_du_jeu=g['code']), mod)
                    continue
                if m:
                    base = str(it.get('base') or '')
                    ajouter('maillots', dict(m, code=_code(mod, it['name']), nom='%s · %s' % (nom, mod), genre='Maillot',
                                              sorte='Maillot', base=base, chemin='mod:/chr/' + _code(mod, it['name']), modele_mod=True), mod)
                continue
            b = obj_jeu.get(str(it.get('base') or ''))
            genre = CATEGORIES.get(it.get('category')) or (b['genre'] if b else 'Objet')
            ic = icone(mod, it.get('icon_key')) or (b.get('icone') if b else None)
            ajouter('objets', {'code': _code(mod, it['name']), 'nom': '%s · %s' % (nom, mod), 'genre': genre, 'sorte': genre,
                               'description': _texte(it, 'description') or (b.get('description', '') if b else ''),
                               'categorie': it.get('category') or (b.get('categorie') if b else None), 'type': 'objet',
                               'base': it.get('base'), 'icone': ic}, mod)
        for o in _liste(t, 'VRFW.Outfit'):
            if not isinstance(o, dict) or not o.get('Name'):
                continue
            nom = _texte(o, 'name', ('Text', 'text')) or o['Name']
            ajouter('objets', {'code': _code(mod, o['Name']), 'nom': '%s · %s' % (nom, mod), 'genre': 'Tenues (costumes)',
                               'sorte': 'Tenues (costumes)', 'description': _texte(o, 'description', ('Text', 'text')) or '',
                               'categorie': 'costume', 'type': 'objet', 'icone': icone(mod, o.get('IconKey'))}, mod)
    # ---------------------------------------------------------------- techniques
    # (17/11/2026) cinématique d'une technique de mod, dans cet ordre :
    # 1. « evNN_… » dans le jeu -> celle du jeu ;
    # 2. « evNN_… » dans les fichiers d'un mod (assets/event_cfg/eff/<ev>_eff.cfg.bin) -> celle du mod, lue dans la RACINE
    #    SUPERPOSÉE de ce mod (moteur/racines.py) ;
    # 3. « Mod.nom » -> [[event]] name = nom de content/anims (VRFW.anim/2) : copie de la cinématique « from » (du jeu ou d'un
    #    mod) ; les recolorations VRFW de ses effets ([[recolor]] de content/effects) ne sont pas encore appliquées ;
    # 4. sinon la cinématique de la technique de base.
    par_code = {x['code']: x for x in techniques_jeu}
    ev_dir = os.path.join(D, 'common', 'event_cfg')            # cinématiques du jeu (techniques.lire_cinematique)
    anims, cameras_ev = {}, {}
    for mod, f, t in T:
        for e in _liste(t, 'event'):
            if isinstance(e, dict) and e.get('name') and isinstance(e.get('from'), str):
                anims.setdefault('%s.%s' % (mod, e['name']), e)
        for c in _liste(t, 'camera'):                  # (17/11/2026) [[camera]] event / cut / glb / action (caméra .glb d'un plan)
            if isinstance(c, dict) and c.get('event'):
                cameras_ev.setdefault('%s.%s' % (mod, c['event']), []).append(c)
    mods_ev = {}

    def ou_est(ev):
        """None = jeu, nom du mod qui a ses fichiers, ou False (introuvable)"""
        if os.path.exists(os.path.join(ev_dir, 'eff', ev + '_eff.cfg.bin')):
            return None
        if ev not in mods_ev:
            mods_ev[ev] = next((m for m in sorted(os.listdir(mods_dir)) if os.path.exists(
                os.path.join(mods_dir, m, 'assets', 'event_cfg', 'eff', ev + '_eff.cfg.bin'))), False)
        return mods_ev[ev]

    def resoudre(ev):
        """(cinématique, mod de sa racine ou None, cinématique VRFW « Mod.nom » ou None) ; None si introuvable"""
        if not isinstance(ev, str) or not ev:
            return None
        vrfw = None
        if '.' in ev:
            a = anims.get(ev)
            if not a:
                return None
            vrfw, ev = (ev, a.get('id')), a['from']
        o = ou_est(ev)
        return None if o is False else (ev, o, vrfw)

    for mod, f, t in T:
        for x in _liste(t, 'technique'):
            if not isinstance(x, dict) or not x.get('name'):
                continue
            b = par_code.get(str(x.get('base') or ''))
            r1, r2 = resoudre(x.get('event')), resoudre(x.get('fail_event'))
            if r1:
                cin, racine_mod, vrfw = r1
            elif b:
                cin, racine_mod, vrfw = b.get('cinematique'), None, None
            else:
                continue
            cin2 = r2[0] if r2 and r2[1] == racine_mod else (b.get('cinematique_2') if b and not racine_mod else None)
            ajouter('techniques', {'code': _code(mod, x['name']), 'nom': '%s · %s' % (_texte(x) or (b['nom'] if b else x['name']), mod),
                                   'genre': b['genre'] if b else 'Technique', 'element': x.get('element') or (b.get('element') if b else None),
                                   'couleur_tir': b.get('couleur_tir', 0) if b else 0, 'cinematique': cin, 'cinematique_2': cin2,
                                   'base': x.get('base'), 'racine_mod': racine_mod,
                                   'cle': x.get('key'),          # (17/11/2026) code de la technique en jeu (esprit lié)
                                   'cinematique_vrfw': vrfw[0] if vrfw else None,
                                   # (17/11/2026) mod dont on applique les [[recolor]] / [[event_command]] ; n° de la cinématique
                                   # pour ses [[event_command]] (id VRFW de la copie, sinon la cinématique elle-même)
                                   'mod_effets': mod, 'event_id': (vrfw[1] if vrfw and vrfw[1] else cin),
                                   # (17/11/2026) [[event]] VRFW (plans recomposés, .glb, son) et ses [[camera]] : moteur/vrfw_anim.py
                                   'vrfw_event': anims.get(vrfw[0]) if vrfw else None,
                                   'vrfw_cameras': cameras_ev.get(vrfw[0], []) if vrfw else [],
                                   'vrfw_mod': vrfw[0].split('.', 1)[0] if vrfw else None,
                                   'cinematique_de_base': not r1}, mod)
    # ---------------------------------------------------------------- esprits guerriers et totems
    # (17/11/2026) sources, dans l'ordre :
    #  - [[aura_command]] key = « wk… » (esprit) / « ws… » (totem) : cells.aura_chara = crc32(code du modèle) (LU),
    #    cells.name_text = id d'une ligne de text/rows/*.toml du mod ([[row]] id, fr) -> le NOM de l'esprit ;
    #  - [[character]] base.name = modèle, new_model.cells.skeleton_path = autre modèle : en jeu, l'esprit a l'apparence de
    #    cet autre modèle (Mukuro : k002090 -> k002093 = Michael astral, en .glb : converti, moteur/glb_vrfw.py) ;
    #  - modèle dans un mod (.g4pkm), converti depuis un .glb, ou dans le jeu.
    pj = {p['code']: p for p in persos_jeu}
    textes = {}
    for f in glob.glob(os.path.join(mods_dir, '*', 'text', 'rows', '*.toml')):
        try:
            for r in tomllib.load(open(f, 'rb')).get('row', []):
                if isinstance(r, dict) and isinstance(r.get('id'), int) and (r.get(_langue.code()) or r.get('fr')) and 'variant' not in r:
                    textes.setdefault(r['id'] & 0xFFFFFFFF, re.sub(r'\[([^/\]]*)/[^\]]*\]', r'\1', str(r.get(_langue.code()) or r['fr'])))
        except Exception:
            continue
    dossiers_mod = {}
    for d in glob.glob(os.path.join(mods_dir, '*', 'assets', 'chr', '*', '*')):
        if os.path.exists(os.path.join(d, os.path.basename(d) + '.g4pkm')):
            dossiers_mod.setdefault(os.path.basename(d), d)
    glb_de = {}                                          # code -> (mod, « chr/_keshin/<code> ») des modèles .glb des mods
    try:
        from .glb_vrfw import trouver as _trouver_glb
        for g in _trouver_glb(cfg):
            c_ = str(g['def'].get('target', '')).replace(chr(92), '/').lstrip('/')
            c_ = c_[len('common/'):] if c_.startswith('common/') else c_
            if c_.startswith('chr/'):
                glb_de[os.path.basename(c_).rsplit('.', 1)[0]] = (g['mod'], os.path.dirname(c_))
    except Exception:
        pass
    codes = set(pj) | set(dossiers_mod) | set(glb_de)
    for sous in ('_keshin', '_totem'):
        dj = os.path.join(D, 'common', 'chr', sous)
        if os.path.isdir(dj):
            codes |= set(os.listdir(dj))
    par_crc = {zlib.crc32(c.encode()): c for c in codes}
    remplace = {}
    for mod, f, t in T:
        for c in _liste(t, 'character'):
            if isinstance(c, dict):
                nb = (c.get('base') or {}).get('name')
                sp = ((c.get('new_model') or {}).get('cells') or {}).get('skeleton_path')
                if isinstance(nb, str) and isinstance(sp, str):
                    remplace[nb] = os.path.basename(os.path.dirname(sp.replace(chr(92), '/')))
    noms_aura = {}                                        # code du modèle -> nom (texte du mod)
    for mod, f, t in T:
        for a in _liste(t, 'aura_command'):
            if isinstance(a, dict) and str(a.get('key', '')).startswith(('wk', 'ws')):
                ch = (a.get('cells') or {}).get('aura_chara'); nt = (a.get('cells') or {}).get('name_text')
                cm = par_crc.get(ch & 0xFFFFFFFF) if isinstance(ch, int) else None
                if cm and isinstance(nt, int) and (nt & 0xFFFFFFFF) in textes:
                    noms_aura.setdefault(cm, textes[nt & 0xFFFFFFFF])

    def modele_de(code_m):
        """(chemin pour serveur.objet, dossier du mod ou None, « chr/… ») du modèle, ou None s'il n'est pas lisible"""
        if code_m in dossiers_mod:
            d = dossiers_mod[code_m]
            return None, d, d.replace(os.sep, '/').split('/assets/', 1)[1]
        if code_m in glb_de:
            mg, rel = glb_de[code_m]
            return 'racine:%s|common/%s/%s.objbin' % (mg, rel, code_m), None, rel
        dj = next((s for s in ('_keshin', '_totem') if os.path.exists(os.path.join(D, 'common', 'chr', s, code_m, code_m + '.g4pkm'))), None)
        if dj:
            rel = 'chr/%s/%s' % (dj, code_m)
            return 'common/%s/%s.objbin' % (rel, code_m), None, rel
        return None

    deja = set()

    def ajouter_esprit(mod, cle, code_m, base_jeu, nom, genre, extra):
        vu = remplace.get(code_m)
        reel = vu if vu and modele_de(vu) else code_m       # l'apparence qu'il a en jeu
        r = modele_de(reel)
        if not r or reel in deja:
            return
        chemin, dossier, rel = r
        p = pj.get(base_jeu) or pj.get(code_m) or {}
        code = _code(mod, cle)
        e = {'code': code, 'nom': '%s · %s' % (nom or noms_aura.get(code_m) or noms_aura.get(reel) or p.get('nom') or code_m, mod),
             'genre': genre or p.get('genre') or 'Esprit guerrier', 'dossier': rel.split('/')[1], 'base': base_jeu or code_m,
             'modele': reel, 'chemin_jeu': rel + '/' + reel + '.objbin', 'techniques': p.get('techniques', [])}
        e.update(extra)
        if dossier:
            e.update(dossier_abs=dossier, chemin='mod:/chr/' + code, modele_mod=True)
        else:
            e.update(chemin=chemin)
        ajouter('esprits', e, mod)
        deja.update({reel, code_m})

    for mod, f, t in T:
        for c in _liste(t, 'character'):
            if not isinstance(c, dict):
                continue
            b = str(c.get('based_on') or '')
            sp = ((c.get('new_model') or {}).get('cells') or {}).get('skeleton_path')
            if b not in pj or not isinstance(sp, str):
                continue
            code_m = os.path.basename(os.path.dirname(sp.replace(chr(92), '/')))
            nb = (c.get('base') or {}).get('name')
            nom = noms_aura.get(nb) if isinstance(nb, str) else None
            ajouter_esprit(mod, c.get('name') or code_m, code_m, b, nom, pj[b]['genre'], {})
    for mod, f, t in T:
        for a in _liste(t, 'aura_command'):
            if not isinstance(a, dict) or not str(a.get('key', '')).startswith(('wk', 'ws')):
                continue
            ch = (a.get('cells') or {}).get('aura_chara')
            code_m = par_crc.get(ch & 0xFFFFFFFF) if isinstance(ch, int) else None
            if not code_m or code_m in deja:
                continue
            ajouter_esprit(mod, a['key'], code_m, None, noms_aura.get(code_m),
                           'Totem' if str(a['key']).startswith('ws') and code_m not in pj else None, {'aura_command': a['key']})
    return out
