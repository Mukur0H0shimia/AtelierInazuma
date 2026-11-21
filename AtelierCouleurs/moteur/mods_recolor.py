"""(17/11/2026) RECOLORATIONS VRFW des mods ([[recolor]] de content/effects/*.toml), appliquées aux images que l'Atelier
montre (cache/<objet>/<texture>.png). VRFW les fait au lancement du jeu : les copies recolorées ne sont PAS sur le disque
(question de muku : « les recolor d'un certain mod ne s'affichent pas ? »).

Formes lues dans les mods (et écrites par l'Atelier, moteur/export.py ; sens noté dans le vault « Guide - créer une
technique recolorée ») :
- object = <objet d'effet> [, copy = <nouveau nom>] : la copie (même fichiers, autre nom) ou l'objet lui-même ;
- [recolor.images] "<texture>" = "assets/….png" : l'image entière est REMPLACÉE par celle du mod ;
- textures = [liste] | "all" | "none", hue = teinte posée (degrés), mode = "set", saturation et value = MULTIPLICATEURS,
  mask_hue = [a, b] : seulement les pixels dont la teinte est dans [a, b] ;
Pas encore appliqué : couleurs des sommets (vertex_colors), particules, matériaux (materials, [[recolor.tint]]), auras.
"""
import os, glob, json, hashlib
import numpy as np

from .mods_contenu import _tomls, _liste


def regles(cfg):
    """{mod: [règle]} de tous les mods (activés ou non)"""
    mods_dir = os.path.join(cfg.get('jeu_dir') or '', 'mods')
    out = {}
    for mod, f, t in _tomls(mods_dir):
        if os.sep + 'effects' + os.sep not in f and '/effects/' not in f.replace('\\', '/'):
            continue
        for r in _liste(t, 'recolor'):
            if isinstance(r, dict) and isinstance(r.get('object'), str) and '/' not in r['object']:
                out.setdefault(mod, []).append(dict(r, _racine=os.path.join(mods_dir, mod)))
    return out


def origine(cfg, mod, nom):
    """objet d'effet dont « nom » est la copie recolorée (règle copy = nom), dans ce mod d'abord ; sinon None"""
    R = regles(cfg)
    for m in [mod] + [x for x in R if x != mod]:
        for r in R.get(m, []):
            if r.get('copy') == nom:
                return r['object']
    return None


def pour(cfg, mod, nom):
    """règles qui touchent l'objet « nom » (sa création comme copie, puis celles posées sur lui), dans l'ordre du fichier"""
    return [r for r in regles(cfg).get(mod, []) if r.get('copy') == nom or (r['object'] == nom and not r.get('copy'))]


def _hsv(rgb):
    mx, mn = rgb.max(-1), rgb.min(-1); d = mx - mn
    h = np.zeros_like(mx)
    m = d > 1e-6
    r, g, b = rgb[..., 0], rgb[..., 1], rgb[..., 2]
    i = m & (mx == r); h[i] = ((g - b)[i] / d[i]) % 6
    i = m & (mx == g) & ~(mx == r); h[i] = (b - r)[i] / d[i] + 2
    i = m & (mx == b) & ~(mx == r) & ~(mx == g); h[i] = (r - g)[i] / d[i] + 4
    return h * 60, np.where(mx > 0, d / np.maximum(mx, 1e-6), 0), mx


def _rgb(h, s, v):
    c = v * s; x = c * (1 - np.abs((h / 60) % 2 - 1)); m = v - c
    z = np.zeros_like(h); k = (h // 60).astype(int) % 6
    r = np.select([k == 0, k == 1, k == 2, k == 3, k == 4, k == 5], [c, x, z, z, x, c])
    g = np.select([k == 0, k == 1, k == 2, k == 3, k == 4, k == 5], [x, c, c, x, z, z])
    b = np.select([k == 0, k == 1, k == 2, k == 3, k == 4, k == 5], [z, z, x, c, c, x])
    return np.stack([r + m, g + m, b + m], -1)


def _teinter(png, r):
    from .g4 import images
    w, h, rows = images.lire_png(png)
    a = np.frombuffer(b''.join(bytes(x) for x in rows), np.uint8).reshape(h, w, 4).astype(np.float32) / 255
    H, S, V = _hsv(a[..., :3])
    sel = np.ones(H.shape, bool)
    mh = r.get('mask_hue')
    if isinstance(mh, list) and len(mh) == 2:
        lo, hi = float(mh[0]), float(mh[1])
        sel = (H >= lo) & (H <= hi) if lo <= hi else (H >= lo) | (H <= hi)
    sel &= S > 0.02                                    # (gris et blancs : pas de teinte à poser) DÉDUIT
    H2 = np.where(sel, float(r.get('hue', 0)) % 360, H)
    S2 = np.where(sel, np.clip(S * float(r.get('saturation', 1.0)), 0, 1), S)
    V2 = np.where(sel, np.clip(V * float(r.get('value', 1.0)), 0, 1), V)
    a[..., :3] = _rgb(H2, S2, V2)
    px = (np.clip(a, 0, 1) * 255 + 0.5).astype(np.uint8)
    images.ecrire_png(png, w, h, [px[y].tobytes() for y in range(h)])


def appliquer(cfg, cache_dir, ob, mod, nom):
    """applique aux PNG de cache/<ob.nom>/ les règles qui touchent « nom » ; une seule fois (repère _recolor.json)"""
    rs = pour(cfg, mod, nom)
    if not rs:
        return 0
    d = os.path.join(cache_dir, ob.nom)
    sig = hashlib.md5(json.dumps([{k: v for k, v in r.items() if k != '_racine'} for r in rs], sort_keys=True, default=str).encode()).hexdigest()
    f_rep = os.path.join(d, '_recolor.json')
    if os.path.exists(f_rep) and json.load(open(f_rep)).get('sig') == sig:
        return 0
    import shutil
    n = 0
    for r in rs:
        for tex, img in ((r.get('images') or {}).items() if isinstance(r.get('images'), dict) else []):
            src = os.path.join(r['_racine'], *str(img).split('/'))
            if os.path.exists(src) and os.path.exists(os.path.join(d, tex + '.png')):
                shutil.copyfile(src, os.path.join(d, tex + '.png')); n += 1
        tx = r.get('textures', 'all' if 'hue' in r else 'none')
        if 'hue' not in r or tx == 'none':
            continue
        noms = [t for t in ob.textures] if tx == 'all' else [t for t in tx if isinstance(t, str)]
        for t in noms:
            png = os.path.join(d, t + '.png')
            if os.path.exists(png):
                _teinter(png, r); n += 1
    json.dump({'sig': sig, 'images': n}, open(f_rep, 'w'))
    return n


def commandes(cfg, mod, event_id):
    """[[event_command]] du mod pour la cinématique « event_id » : [(acteur, nouveau chemin)] des LOAD_ACTOR_RESOURCE
    (command = "CMD_799A1EBA", args = [acteur], set = [acteur, chemin]) que VRFW change au lancement (LU dans les mods)"""
    mods_dir = os.path.join(cfg.get('jeu_dir') or '', 'mods')
    out = []
    for m, f, t in _tomls(mods_dir):
        if m != mod:
            continue
        for c in _liste(t, 'event_command'):
            if isinstance(c, dict) and c.get('event') == event_id and str(c.get('command', '')).upper() in ('CMD_799A1EBA', 'LOAD_ACTOR_RESOURCE'):
                s = c.get('set') or []
                if len(s) >= 2 and isinstance(s[0], str) and isinstance(s[1], str):
                    out.append((s[0], s[1]))
    return out


# ---------------------------------------------------------------------------------------------- (17/11/2026) le reste
# Appliqué à l'objet EN MÉMOIRE (octets des sommets ob.mg, ob.materiaux, ob.particules) dès sa lecture : l'aperçu, le rendu
# Direct3D et le lecteur natif lisent tous ces mêmes valeurs. Sens (vault « Guide - créer une technique recolorée », règles
# écrites par l'Atelier et vues dans les mods) : teinte posée / saturation et valeur multipliées / mask_hue ;
# vertex_colors = "all" | [pièces] ; materials = "all" | [matériaux] ; particles = true ;
# [[recolor.tint]] mesh = [pièces] | material = nom, rgb = [r, v, b] (0-1), alpha, op = "set" : couleur / alpha POSÉS (DÉDUIT).

def _teinte_rgb(rgb, r):
    """teinte une liste de couleurs [[r, v, b], …] (0-1) selon la règle r"""
    a = np.asarray(rgb, np.float32).reshape(-1, 3)
    if not len(a):
        return a
    H, S, V = _hsv(a)
    sel = np.ones(H.shape, bool)
    mh = r.get('mask_hue')
    if isinstance(mh, list) and len(mh) == 2:
        lo, hi = float(mh[0]), float(mh[1])
        sel = (H >= lo) & (H <= hi) if lo <= hi else (H >= lo) | (H <= hi)
    sel &= S > 0.02
    H2 = np.where(sel, float(r.get('hue', 0)) % 360, H)
    S2 = np.where(sel, np.clip(S * float(r.get('saturation', 1.0)), 0, 1), S)
    V2 = np.where(sel, np.clip(V * float(r.get('value', 1.0)), 0, 1), V)
    return np.clip(_rgb(H2, S2, V2), 0, 1)


def _choisis(val, nom):
    return val == 'all' or (isinstance(val, list) and nom in val) or val is True


def appliquer_objet(cfg, ob, mod, nom):
    """couleurs des sommets, matériaux, particules et teintes du mod, sur l'objet chargé ; renvoie un résumé"""
    rs = pour(cfg, mod, nom)
    if not rs:
        return None
    mg = bytearray(ob.mg)
    res = {'sommets': 0, 'materiaux': 0, 'particules': 0, 'teintes': 0}

    def pieces_de(liste):
        return [i for i, p in enumerate(ob.pieces) if _choisis(liste, p.get('nom'))]

    def couleurs_sommets(i):
        p = ob.pieces[i]
        co = p.get('col')
        if co is None or co + 4 > p['pas']:
            return None
        return [p['vb'] + k * p['pas'] + co for k in range(p['nv'])]

    for r in rs:
        if 'hue' in r:
            if r.get('vertex_colors') not in (None, 'none', False):
                for i in pieces_de(r['vertex_colors']):
                    adr = couleurs_sommets(i)
                    if not adr:
                        continue
                    c = np.array([[mg[a], mg[a + 1], mg[a + 2]] for a in adr], np.float32) / 255
                    t = (_teinte_rgb(c, r) * 255 + 0.5).astype(np.uint8)
                    for a, v in zip(adr, t):
                        mg[a:a + 3] = bytes(v)
                    res['sommets'] += 1
            if r.get('materials') not in (None, 'none', False):
                for m in ob.materiaux:
                    if not _choisis(r['materials'], m.get('nom')):
                        continue
                    for cle in ('couleur', 'diffuse'):
                        if m.get(cle):
                            m[cle] = [round(float(x), 5) for x in _teinte_rgb([m[cle][:3]], r)[0]] + list(m[cle][3:])
                    res['materiaux'] += 1
            if r.get('particles'):
                for e in (getattr(ob, 'particules', None) or {}).get('emetteurs', []):
                    c = e.get('couleur') or {}
                    for cle in ('rgb', 'rgb2'):
                        if c.get(cle) and c[cle].get('v'):
                            c[cle]['v'] = [list(map(float, x)) for x in _teinte_rgb(c[cle]['v'], r)]
                    res['particules'] += 1
        for t in r.get('tint') or []:
            if not isinstance(t, dict):
                continue
            rgb, al = t.get('rgb'), t.get('alpha')
            if t.get('mesh') is not None:
                for i in pieces_de(t['mesh'] if isinstance(t['mesh'], list) else [t['mesh']]):
                    for a in couleurs_sommets(i) or []:
                        if rgb:
                            mg[a:a + 3] = bytes(int(max(0, min(1, float(x))) * 255 + 0.5) for x in rgb[:3])
                        if al is not None:
                            mg[a + 3] = int(max(0, min(1, float(al))) * 255 + 0.5)
                    res['teintes'] += 1
            if t.get('material') is not None:
                noms = t['material'] if isinstance(t['material'], list) else [t['material']]
                for m in ob.materiaux:
                    if m.get('nom') in noms:
                        for cle in ('couleur', 'diffuse'):
                            if m.get(cle):
                                v = list(m[cle])
                                if rgb:
                                    v[:3] = [float(x) for x in rgb[:3]]
                                if al is not None and len(v) > 3:
                                    v[3] = float(al)
                                m[cle] = v
                        res['teintes'] += 1
    ob.mg = bytes(mg)
    return res


def couleur_aura(cfg, mod, aura):
    """(17/11/2026) aura recolorée par le mod ([[recolor]] aura = X, copy = Y, color = [[t, r, v, b, a], …]) : (origine,
    « #rrvvbb ») pour une aura « aura » (copie ou originale recolorée), sinon None"""
    for r in regles_auras(cfg).get(mod, []):
        if aura in (r.get('copy'), r.get('aura')) and isinstance(r.get('color'), list) and r['color']:
            c = r['color'][0]
            if isinstance(c, list) and len(c) >= 4:
                return r.get('aura'), '#%02x%02x%02x' % tuple(int(max(0, min(1, float(x))) * 255 + 0.5) for x in c[1:4])
    return None


def regles_auras(cfg):
    mods_dir = os.path.join(cfg.get('jeu_dir') or '', 'mods')
    out = {}
    for mod, f, t in _tomls(mods_dir):
        for r in _liste(t, 'recolor'):
            if isinstance(r, dict) and isinstance(r.get('aura'), str):
                out.setdefault(mod, []).append(r)
    return out
