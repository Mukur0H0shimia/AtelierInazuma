"""(17/11/2026) CINÉMATIQUES RECOMPOSÉES PAR VRFW ([[event]] cuts = … de content/anims, VRFW.anim/2), pour l'Atelier et le
lecteur natif : la cinématique d'origine (« from ») lue par moteur/anim.py est recomposée plan par plan, et les animations des
plans en .glb (Blender) sont converties au format des clips du jeu. Demande de muku (« fais les 3 »).

Règles (DÉDUIT des mods installés et des essais en jeu de Spectre chrono, voir mémoire / vault) :
- la nouvelle cinématique = la SUITE des entrées de `cuts`, plans renommés c0010, c0020… ;
- "c0030" = le plan c0030 d'origine tel quel ; { cut, trim = [a, b], sync = [[image d'origine, image nouvelle], …] } = un
  morceau du plan, recalé dans le temps (morceaux de droite ; sans sync : a -> 0) ; `hide` = acteurs / objets cachés ;
- { glb, action, slot, effects, copies } = les acteurs du .glb (racines « c000101_s00_p00 », os « <acteur>|<os> », temps =
  image / 60), le reste (caméra, points d'accroche, effets si effects = true) pris au plan `slot` d'origine ; copies = places
  ajoutées qui rejouent une autre place quand le .glb ne les anime pas ;
- [[camera]] event / cut / glb / action = caméra du .glb pour ce plan : nœud caméra (axe −Z), extras fovKeys (champ vertical
  en radians, comme le canal 31 du jeu) et targetDistance (distance de la cible).
Format des clips du jeu (moteur/anim.py) : {nom, debut, fin, fps, cibles: [{crc = crc32(os), canaux: [{type, interp, images,
prm, valeurs}]}]} ; types 1-3 échelle, 9 quaternion xyzw, 10-12 position ; caméra 22-24 œil, 26-28 cible, 30 roulis, 31 champ.
"""
import os, json, struct, zlib, copy, math, re
import numpy as np

# ---------------------------------------------------------------------------------------------------------- .glb
_glb = {}


def lire_glb(f):
    if f in _glb:
        return _glb[f]
    b = open(f, 'rb').read()
    n = struct.unpack_from('<I', b, 12)[0]
    j = json.loads(b[20:20 + n])
    o = 20 + n
    binaire = b[o + 8:o + 8 + struct.unpack_from('<I', b, o)[0]] if o + 8 <= len(b) else b''
    _glb[f] = (j, binaire)
    return _glb[f]


def _acces(j, binaire, i):
    a = j['accessors'][i]; v = j['bufferViews'][a['bufferView']]
    nb = {'SCALAR': 1, 'VEC2': 2, 'VEC3': 3, 'VEC4': 4}[a['type']]
    dt = {5126: np.float32, 5123: np.uint16, 5125: np.uint32, 5121: np.uint8}[a['componentType']]
    deb = v.get('byteOffset', 0) + a.get('byteOffset', 0)
    x = np.frombuffer(binaire, dt, count=a['count'] * nb, offset=deb).reshape(a['count'], nb).astype(np.float64)
    if a.get('normalized') and dt != np.float32:
        x /= np.iinfo(dt).max
    return x


def _canal(type_, images, valeurs):
    return {'type': type_, 'interp': 1, 'images': [int(round(i)) for i in images], 'prm': 0, 'valeurs': [list(map(float, v)) for v in valeurs]}


def clips_glb(f, action):
    """{acteur (« c000101_s00_p00 ») : clip} de l'action « action » du .glb"""
    j, binaire = lire_glb(f)
    an = next((a for a in j.get('animations', []) if a.get('name') == action), None)
    if not an:
        return {}
    ex = an.get('extras') or {}
    fps = ex.get('fps', 60)
    par = {}
    for c in an['channels']:
        nd = j['nodes'][c['target']['node']]
        nom = nd.get('name', '')
        if '|' not in nom:
            continue
        acteur, os_ = nom.split('|', 1)
        s = an['samplers'][c['sampler']]
        t = _acces(j, binaire, s['input'])[:, 0] * fps
        v = _acces(j, binaire, s['output'])
        p = c['target']['path']
        cib = par.setdefault(acteur, {}).setdefault(os_, [])
        if p == 'translation':
            cib += [_canal(10 + k, t, v[:, k:k + 1]) for k in range(3)]
        elif p == 'rotation':
            cib.append(_canal(9, t, v[:, :4]))
        elif p == 'scale':
            cib += [_canal(1 + k, t, v[:, k:k + 1]) for k in range(3)]
    fin = int(ex.get('end', max((max(ch['images']) for c in par.values() for l in c.values() for ch in l), default=0)))
    return {a: {'nom': action, 'debut': 0, 'fin': fin, 'fps': 60,
                'cibles': [{'crc': zlib.crc32(o.encode()), 'canaux': l} for o, l in oss.items()]} for a, oss in par.items()}


def _qrot(q, v):
    x, y, z, w = q
    u = np.array([x, y, z]); v = np.asarray(v, float)
    return v + 2 * np.cross(u, np.cross(u, v) + w * v)


def camera_glb(f, action):
    """clip de caméra du jeu (types 22-24, 26-28, 30, 31) depuis l'action « camera:… » du .glb, ou None"""
    j, binaire = lire_glb(f)
    an = next((a for a in j.get('animations', []) if a.get('name') == action), None)
    if not an:
        return None
    ex = an.get('extras') or {}
    fps = ex.get('fps', 60)
    T = R = None
    for c in an['channels']:
        s = an['samplers'][c['sampler']]
        t = _acces(j, binaire, s['input'])[:, 0]
        if c['target']['path'] == 'translation':
            T = (t, _acces(j, binaire, s['output']))
        elif c['target']['path'] == 'rotation':
            R = (t, _acces(j, binaire, s['output']))
    if T is None or R is None:
        return None
    tt = T[0]
    rot = np.array([np.interp(tt, R[0], R[1][:, k]) for k in range(4)]).T
    rot /= np.linalg.norm(rot, axis=1, keepdims=True)

    def courbe(cle, defaut):
        k = ex.get(cle)
        if not k:
            return np.full(len(tt), defaut)
        k = np.asarray(k, float)
        return np.interp(tt, k[:, 0], k[:, 1])
    fov = courbe('fovKeys', (j.get('cameras') or [{}])[0].get('perspective', {}).get('yfov', math.pi / 4))
    dist = courbe('targetDistance', 3.0)
    oeil, cible, roulis = [], [], []
    for p, q, d in zip(T[1], rot, dist):
        fw = _qrot(q, [0, 0, -1]); xc = _qrot(q, [1, 0, 0])
        ci = p + fw * d
        z = (p - ci); z /= (np.linalg.norm(z) or 1)
        x = np.cross([0, 1, 0], z); x /= (np.linalg.norm(x) or 1); y = np.cross(z, x)
        r = math.atan2(float(np.dot(xc, y)), float(np.dot(xc, x)))      # vue : X = x cos r + y sin r, r = −canal 30
        oeil.append(p); cible.append(ci); roulis.append([-r])
    oeil, cible = np.array(oeil), np.array(cible)
    im = tt * fps
    can = [_canal(22 + k, im, oeil[:, k:k + 1]) for k in range(3)] + [_canal(26 + k, im, cible[:, k:k + 1]) for k in range(3)]
    can += [_canal(30, im, roulis), _canal(31, im, fov[:, None])]
    return {'nom': action, 'debut': 0, 'fin': int(round(im[-1])), 'fps': 60, 'cibles': [{'crc': CRC_CAMERA, 'canaux': can}]}


CRC_CAMERA = 1018227507             # cible des clips de caméra du jeu (lue dans ev61_10110 : une seule cible)


# ---------------------------------------------------------------------------------------------------------- temps
def _echantillon(ch, f):
    im, v = ch['images'], ch['valeurs']
    n = len(im)
    if n == 1 or f <= im[0]:
        return list(v[0])
    if f >= im[-1]:
        return list(v[-1])
    lo = max(i for i in range(n) if im[i] <= f); hi = lo + 1
    if not ch.get('interp'):
        return list(v[lo])
    t = (f - im[lo]) / ((im[hi] - im[lo]) or 1)
    a, b = v[lo], v[hi]
    if ch['type'] == 9 and len(a) == 4:
        s = -1 if sum(x * y for x, y in zip(a, b)) < 0 else 1
        q = [a[k] * (1 - t) + s * b[k] * t for k in range(4)]
        l = math.sqrt(sum(x * x for x in q)) or 1
        return [x / l for x in q]
    return [a[k] * (1 - t) + b[k] * t for k in range(len(a))]


class Morceau:
    """plan nouveau [N0, N0 + L] <- images d'origine, par morceaux de droite (paires (origine relative, nouveau relatif))"""

    def __init__(self, nom, N0, L, S0, paires, borne=None):
        self.nom, self.N0, self.L, self.S0 = nom, N0, L, S0
        self.p = sorted(paires, key=lambda x: x[1])
        self.borne = borne                                   # (glb plus long que le plan slot : origine tenue à la fin)

    def src(self, f):
        u = f - self.N0
        xs, ys = [b for a, b in self.p], [a for a, b in self.p]
        s = float(np.interp(u, xs, ys)) if len(self.p) > 1 else ys[0] + u
        if self.borne is not None:
            s = min(s, self.borne)
        return self.S0 + s

    def inv(self, s):
        r = s - self.S0
        xs, ys = [a for a, b in self.p], [b for a, b in self.p]
        if len(self.p) > 1 and not all(xs[i] < xs[i + 1] for i in range(len(xs) - 1)):
            return None
        if r < xs[0] - 1e-6 or r > xs[-1] + 1e-6:
            return None
        return self.N0 + float(np.interp(r, xs, ys))

    def dedans(self, s):
        return self.inv(s) is not None


def remap_clip(cl, d_s, d_n, m, nom):
    """clip d'origine joué depuis l'image d'origine d_s -> clip joué depuis l'image nouvelle d_n dans le morceau m
    (temps du clip = (image - depuis) x fps / 60) ; clés hors du morceau retirées, valeurs aux deux bords ajoutées"""
    k = (cl.get('fps') or 60) / 60
    lo, hi = max(d_n, m.N0), m.N0 + m.L
    out = dict(cl, nom=nom, debut=0)
    cib = []
    for c in cl['cibles']:
        can = []
        for ch in c['canaux']:
            pts = []
            for i, tau in enumerate(ch['images']):
                f = m.inv(d_s + (tau - cl['debut']) / k)
                if f is not None and lo - 1e-6 <= f <= hi + 1e-6:
                    pts.append(((f - d_n) * k, ch['valeurs'][i]))
            for f in (lo, hi):                                # bords : valeur échantillonnée
                tau = cl['debut'] + (m.src(f) - d_s) * k
                pts.append(((f - d_n) * k, _echantillon(ch, tau)))
            pts.sort(key=lambda x: x[0])
            dd = []
            for t, v in pts:
                if not dd or t > dd[-1][0] + 1e-6:
                    dd.append((t, v))
            can.append(dict(ch, images=[t for t, v in dd], valeurs=[list(v) for t, v in dd]))
        cib.append(dict(c, canaux=can))
    out['cibles'] = cib
    out['fin'] = int(math.ceil((hi - d_n) * k))
    return out


# ---------------------------------------------------------------------------------------------------------- recomposition
def _etat(ordres, s):
    st = {}
    for x in ordres:
        if x['image'] > s:
            break
        if 'visible' in x:
            st['visible'] = x['visible']
        if x.get('accroche'):
            st['accroche'] = x['accroche']
        if x.get('jouer'):
            st['jouer'], st['depuis'], st['boucle'] = x['jouer'], x['image'], x.get('boucle', False)
        if x.get('fondu'):
            st['fondu'] = x['fondu']
    return st


def recomposer(res, ev, dossier_mod, cameras=()):
    """res = moteur/anim.cinematique(« from ») ; ev = [[event]] du mod (cuts…) ; renvoie la cinématique recomposée"""
    cuts = ev.get('cuts')
    if not cuts:
        return res
    plans = {p['nom']: p for p in res['plans']}
    morceaux, glb_de = [], {}
    N = 0
    for i, c in enumerate(cuts):
        nom = 'c%04d' % (10 * (i + 1))
        if isinstance(c, str):
            c = {'cut': c}
        if c.get('glb'):
            src = plans.get(c.get('slot')) or (res['plans'][-1] if res['plans'] else {'nom': '', 'debut': 0, 'fin': 0})
            f = os.path.join(dossier_mod, *c['glb'].split('/'))
            clips = clips_glb(f, c.get('action', nom)) if os.path.exists(f) else {}
            L = max([x['fin'] for x in clips.values()] or [src['fin'] - src['debut']])
            lc = src['fin'] - src['debut']
            m = Morceau(nom, N, L, src['debut'], [(0, 0), (lc, lc)], borne=lc)
            m.glb, m.effets, m.copies, m.cache = clips, bool(c.get('effects', True)), c.get('copies') or {}, set(c.get('hide') or [])
            m.slot = src['nom']
            # caméra du .glb (« camera:<action> ») : DÉDUIT, les .glb de duel de MissingContent en ont une sans [[camera]]
            m.camera = camera_glb(f, 'camera:' + c.get('action', nom)) if os.path.exists(f) else None
        else:
            src = plans.get(c.get('cut'))
            if not src:
                continue
            a, b = (c.get('trim') or [0, src['fin'] - src['debut']])[:2]
            p = [(x[0], x[1]) for x in c['sync']] if c.get('sync') else [(a, 0), (b, b - a)]
            L = max(y for x, y in p)
            m = Morceau(nom, N, L, src['debut'], p)
            m.glb, m.effets, m.copies, m.cache, m.slot = None, True, {}, set(c.get('hide') or []), src['nom']
        morceaux.append(m)
        N += m.L + 1
    out = dict(res)
    out['plans'] = [{'nom': m.nom, 'debut': m.N0, 'fin': m.N0 + m.L + 1} for m in morceaux]
    out['duree'] = N
    out['vrfw'] = {'cuts': len(morceaux), 'glb': sum(1 for m in morceaux if m.glb)}

    def par_plan(clips, glb_cam=None):
        """éléments dont le clip est choisi par le plan (caméra, points, ballon) : un clip par nouveau plan"""
        nv = {}
        for m in morceaux:
            if glb_cam and m.nom in glb_cam:
                nv[m.nom] = glb_cam[m.nom]
                continue
            cl = clips.get(m.slot)
            if cl:
                nv[m.nom] = remap_clip(cl, m.S0, m.N0, m, m.nom)
        return nv

    cams = {}
    for c in cameras:
        f = os.path.join(dossier_mod, *str(c.get('glb', '')).split('/'))
        if c.get('cut') and os.path.exists(f):
            k = camera_glb(f, c.get('action') or 'camera:' + c['cut'])
            if k:
                cams[c['cut']] = k
    for m in morceaux:                                        # caméra embarquée dans le .glb d'un plan (si pas de [[camera]])
        if getattr(m, 'camera', None) and m.nom not in cams:
            cams[m.nom] = m.camera
    if res.get('camera'):
        out['camera'] = par_plan(res['camera'], cams)
    elif cams:
        out['camera'] = cams
    for cle in ('point_eff', 'balle', 'point_s00'):
        if isinstance(res.get(cle), dict) and res[cle].get('clips') is not None:
            out[cle] = dict(res[cle], clips=par_plan(res[cle]['clips']))
    if isinstance(res.get('points'), dict):
        out['points'] = {k: dict(v, clips=par_plan(v.get('clips') or {})) for k, v in res['points'].items()}
    if isinstance(res.get('joueurs'), list):
        out['joueurs'] = [dict(j_, clips=par_plan(j_.get('clips') or {})) for j_ in res['joueurs']]
    if isinstance(res.get('lumiere_plans'), dict):
        lp = {'_base': res['lumiere_plans'].get('_base')} if '_base' in res['lumiere_plans'] else {}
        for m in morceaux:
            if m.slot in res['lumiere_plans']:
                lp[m.nom] = res['lumiere_plans'][m.slot]
        out['lumiere_plans'] = lp

    def suivre(el, nom_el, est_acteur, glb_clip=None, place=None):
        """nouveaux ordres et clips d'un élément à ordres (objet d'effet, acteur)"""
        clips, ordres = el.get('clips') or {}, el.get('ordres') or []
        extra = {k: dict(el.get(k) or {}) for k in ('vis', 'opa', 'uv') if isinstance(el.get(k), dict)}
        nc, no = {}, []
        nx = {k: {} for k in extra}

        def jouer(nom_clip, d_s, d_n, m):
            cl = clips.get(nom_clip)
            if not cl:
                return None
            n2 = '%s~%s' % (nom_clip, m.nom)
            if n2 not in nc:
                nc[n2] = remap_clip(cl, d_s, d_n, m, n2)
                for k in extra:
                    if extra[k].get(nom_clip):
                        nx[k][n2] = remap_clip(extra[k][nom_clip], d_s, d_n, m, n2)
            return n2
        for m in morceaux:
            cache = nom_el in m.cache or any(h in nom_el for h in m.cache)
            if m.glb is not None and not est_acteur and not m.effets:
                no.append({'image': m.N0, 'visible': False}); continue
            if est_acteur and m.glb is not None:
                g = glb_clip(m) if glb_clip else None
                st = _etat(ordres, m.S0) if ordres else {}
                if g:
                    n2 = '%s~glb' % m.nom
                    nc[n2] = g
                    o = {'image': m.N0, 'visible': not cache, 'jouer': n2}
                    if st.get('accroche'):
                        o['accroche'] = st['accroche']
                    no.append(o)
                else:
                    no.append({'image': m.N0, 'visible': False})
                continue
            s0 = m.src(m.N0)
            st = _etat(ordres, s0)
            o = {'image': m.N0, 'visible': bool(st.get('visible')) and not cache}
            if st.get('accroche'):
                o['accroche'] = st['accroche']
            if st.get('jouer'):
                n2 = jouer(st['jouer'], st['depuis'], m.N0, m)      # rejoué depuis le début du morceau (même temps de clip)
                if n2:
                    o['jouer'] = n2
                    if st.get('boucle'):
                        o['boucle'] = True
            no.append(o)
            for x in ordres:
                if x['image'] <= s0:
                    continue
                f = m.inv(x['image'])
                if f is None:
                    continue
                y = dict(x, image=int(round(f)))
                if x.get('jouer'):
                    n2 = jouer(x['jouer'], x['image'], f, m)
                    if not n2:
                        continue
                    y['jouer'] = n2
                if cache and 'visible' in y:
                    y['visible'] = False
                no.append(y)
        no.sort(key=lambda x: x['image'])
        # objets d'effet : les clips d'origine restent aussi (un [[event_effect]] peut en jouer un après la recomposition :
        # dôme vert de Spectre chrono, clip c0300 du gabarit)
        r = dict(el, clips=(nc if est_acteur else {**clips, **nc}), ordres=no)
        for k in nx:
            r[k] = nx[k] if est_acteur else {**extra[k], **nx[k]}
        return r

    out['objets'] = {a: suivre(o, a, False) for a, o in (res.get('objets') or {}).items()}

    def place_de(nom):
        mm = re.search(r'_(s\d\d)_', nom)
        return mm.group(1) if mm else 's00'

    def par_corps(a, r_, pl, src_pl=None):
        """joueurs : la page et le lecteur natif prennent les clips de la FAMILLE DE CORPS choisie (a['corps'][1..4] =
        c000101..c000401) -> mêmes ordres, clips recomposés pour chaque famille (plans .glb : la racine de cette famille)"""
        if not isinstance(a.get('corps'), dict):
            return r_
        nc = {}
        for n, cv in a['corps'].items():
            fam = 'c000%d01' % int(n)

            def gc(m, fam=fam):
                for p in (pl, src_pl, (m.copies or {}).get(pl)):
                    if p and m.glb and '%s_%s_p00' % (fam, p) in m.glb:
                        return m.glb['%s_%s_p00' % (fam, p)]
                return None
            rr = suivre(dict(a, clips=cv.get('clips') or {}), a['acteur'], True, gc)
            nc[n] = dict(cv, clips=rr['clips'])
        r_['corps'] = nc
        return r_

    acteurs = []
    for a in res.get('acteurs') or []:
        pl, code = place_de(a['acteur']), a.get('code') or ''

        def glb_clip(m, pl=pl, code=code):
            cand = ['%s_%s_p00' % (code, pl)] + [k for k in m.glb if k.startswith(code) and ('_%s_' % pl) in k]
            src_pl = m.copies.get(pl)
            if src_pl:
                cand.append('%s_%s_p00' % (code, src_pl))
            return next((m.glb[k] for k in cand if k in m.glb), None)
        acteurs.append(par_corps(a, suivre(a, a['acteur'], True, glb_clip), pl))
    # places ajoutées par `copies` (et animées par le .glb) : copies de l'acteur de la place d'origine
    deja = {place_de(a['acteur']) for a in acteurs}
    for m in morceaux:
        for pl, src_pl in (m.copies or {}).items():
            if pl in deja:
                continue
            modele = next((a for a in res.get('acteurs') or [] if place_de(a['acteur']) == src_pl and a.get('modele') == 'joueur'), None)
            if not modele:
                continue
            nouveau = dict(modele, acteur=modele['acteur'].replace('_%s_' % src_pl, '_%s_' % pl), ordres=[], clips={})
            code = modele.get('code') or ''

            def glb_clip(m, pl=pl, src_pl=src_pl, code=code):
                for k in ('%s_%s_p00' % (code, pl), '%s_%s_p00' % (code, src_pl)):
                    if m.glb and k in m.glb:
                        return m.glb[k]
                return None
            nouveau['ordres'] = [{'image': 0, 'visible': False}] + [dict(x) for x in modele.get('ordres') or [] if x.get('accroche')][:1]
            acteurs.append(par_corps(nouveau, suivre(nouveau, nouveau['acteur'], True, glb_clip), pl, src_pl))
            deja.add(pl)
    out['acteurs'] = acteurs

    def images(liste):
        r = []
        for x in liste or []:
            for m in morceaux:
                if m.glb is not None and not m.effets:
                    continue
                f = m.inv(x['image'])
                if f is not None:
                    r.append(dict(x, image=int(round(f))))
        return sorted(r, key=lambda x: x['image'])
    out['sons'] = images(res.get('sons'))
    out['decor'] = images(res.get('decor'))
    if isinstance(res.get('telop'), dict):
        t = dict(res['telop'])
        for k in ('debut', 'fin'):
            f = next((m.inv(t[k]) for m in morceaux if m.inv(t[k]) is not None), None)
            if f is not None:
                t[k] = int(round(f))
        out['telop'] = t
    return out


# ---------------------------------------------------------------------------------------------------------- [[event_effect]]
# (17/11/2026) objets d'effet AJOUTÉS à une cinématique par un mod (content/effects, VRFW.effect/1), formes lues :
#   event (n° de la cinématique), object (« ev63005541 » ou « effect/event/…/x.objbin »), actor (défaut : le nom de l'objet),
#   cut + offset | cuts, clips = {plan de la cinématique : clip de l'objet}, clip_frames = [a, b] (images a à b du clip ;
#   a = b : pose figée — silhouettes de Spectre chrono), attach = {point, locator[, offset]}, until_cut + until_offset.
# Pas encore : attach.offset, follow, les [[event_effect]] d'auras (aura / actor / frame / until), les objets d'effet faits par
# VRFW à partir d'un .glb (VRFW.model/1 kind = "effect" : traînée et dôme de Spectre chrono).

def effets_ajoutes(cfg, mod, event_id):
    from .mods_contenu import _tomls, _liste
    mods_dir = os.path.join(cfg.get('jeu_dir') or '', 'mods')
    out = []
    for m, f, t in _tomls(mods_dir):
        if m != mod:
            continue
        for e in _liste(t, 'event_effect'):
            if isinstance(e, dict) and e.get('event') == event_id and isinstance(e.get('object'), str):
                out.append(e)
    return out


def chemin_objet(e):
    o = e['object'].replace(chr(92), '/').lstrip('/')
    if '/' in o:
        return o if o.startswith('common/') else 'common/' + o
    return 'common/effect/event/%s/%s/%s.objbin' % (o[:4], o, o)


def acteur_objet(e):
    return e.get('actor') or os.path.basename(chemin_objet(e)).rsplit('.', 1)[0]


def _morceau_clip(cl, a, b, nom):
    """images a à b d'un clip (a = b : pose figée)"""
    out = dict(cl, nom=nom, debut=0, fin=max(0, int(b - a)))
    cib = []
    for c in cl['cibles']:
        can = []
        for ch in c['canaux']:
            pts = [(tau - cl['debut'] - a, v) for tau, v in zip(ch['images'], ch['valeurs']) if a < tau - cl['debut'] < b]
            pts = [(0, _echantillon(ch, cl['debut'] + a))] + pts + ([(b - a, _echantillon(ch, cl['debut'] + b))] if b > a else [])
            can.append(dict(ch, images=[p[0] for p in pts], valeurs=[list(p[1]) for p in pts]))
        cib.append(dict(c, canaux=can))
    out['cibles'] = cib
    return out


def appliquer_effets(res, regles):
    plans = {p['nom']: p for p in res.get('plans') or []}
    n = 0
    for e in regles:
        act = acteur_objet(e)
        o = (res.get('objets') or {}).get(act)
        if not o:
            continue
        cuts = e.get('cuts') or ([e['cut']] if e.get('cut') else [])
        att = e.get('attach') or {}
        acc = [att['point'], att.get('locator', '')] if att.get('point') else None
        ordres = [{'image': 0, 'visible': False}]
        ordre = res.get('plans') or []
        for i, c in enumerate(cuts):
            # plan par son nom, sinon par son RANG (DÉDUIT : VRFW renumérote les plans d'une cinématique copiée c0010, c0020…
            # — fist_of_justice_g5 : cuts c0010…c0060 sur ev63_00440_1 dont les plans s'appellent c0100…c0601)
            p = plans.get(c)
            if not p and re.fullmatch(r'c\d{4}', str(c)) and int(c[1:]) % 10 == 0 and 0 < int(c[1:]) // 10 <= len(ordre):
                p = ordre[int(c[1:]) // 10 - 1]
            nom_cl = (e.get('clips') or {}).get(c)
            if not p or nom_cl not in (o.get('clips') or {}):
                continue
            deb = p['debut'] + (int(e.get('offset', 0)) if e.get('cut') else 0)
            if e.get('clip_frames'):
                a, b = e['clip_frames'][:2]
                n2 = '%s@%s-%s' % (nom_cl, a, b)
                o['clips'][n2] = _morceau_clip(o['clips'][nom_cl], a, b, n2)
                for k in ('vis', 'opa', 'uv'):
                    if isinstance(o.get(k), dict) and o[k].get(nom_cl):
                        o[k][n2] = _morceau_clip(o[k][nom_cl], a, b, n2)
                nom_cl = n2
            x = {'image': deb, 'visible': True, 'jouer': nom_cl}
            if acc:
                x['accroche'] = acc
            ordres.append(x)
            u = e.get('until_cut')
            pu = plans.get(u) or (ordre[int(u[1:]) // 10 - 1] if u and re.fullmatch(r'c\d{4}', str(u)) and 0 < int(u[1:]) // 10 <= len(ordre) else None)
            if pu and i == len(cuts) - 1:
                fin = pu['debut'] + int(e.get('until_offset', 0))
            else:
                fin = p['fin']
            ordres.append({'image': fin, 'visible': False})
        ordres.sort(key=lambda x: (x['image'], bool(x.get('visible'))))
        o['ordres'] = ordres
        n += 1
    return n


def son_mod(cfg, nom):
    """fichier d'un son ajouté par un mod ([[sfx]] add = nom, file = « assets/….wav »), ou None"""
    from .mods_contenu import _tomls, _liste
    mods_dir = os.path.join(cfg.get('jeu_dir') or '', 'mods')
    for m, f, t in _tomls(mods_dir):
        for s in _liste(t, 'sfx'):
            if isinstance(s, dict) and s.get('add') == nom and isinstance(s.get('file'), str):
                p = os.path.join(mods_dir, m, *s['file'].split('/'))
                if os.path.exists(p):
                    return p
    return None
