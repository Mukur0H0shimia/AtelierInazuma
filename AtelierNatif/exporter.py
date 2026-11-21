"""Exporte une scène pour le LECTEUR NATIF (C++ / Direct3D 11, dossier src) — 14/11/2026.

Le lecteur natif dessine EN DIRECT, comme le jeu, avec les vrais shaders du jeu. Ce fichier lui prépare une fois tout ce
qui ne bouge pas (résolu par le code du rendu Python, AtelierD3D/rendu_image.py, pour que les deux donnent la même image) :
shaders (DXBC du jeu), entrées des sommets, tampons de constantes (noms, décalages), géométrie, textures, matériaux,
cubemap, réglages de lumière (CLightData) ; puis, image par image, ce que l'animation de l'Atelier a calculé (caméra…).

Étape 1 : le stade (passe de profondeur + passe de couleur), caméra du jeu.

Format (petit-boutiste) : voir ecrire_scene() ; le lecteur C++ (src/lecteur.cpp) lit exactement dans le même ordre.
"""
import os, sys, struct, json, math

ICI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(ICI), 'AtelierD3D'))
import rendu_image as RI                     # lecture seule : on réutilise ses fonctions
import d3d11 as D
from lib import images

MAGIC_SCENE, MAGIC_IMAGES = b'INZ1', b'INZF'
VERSION_FORMAT = 6         # à changer à chaque modification du format (le décor gardé est alors refait)


class Sortie:
    def __init__(self):
        self.b = bytearray()

    def u32(self, *v):
        self.b += struct.pack('<%dI' % len(v), *[int(x) & 0xFFFFFFFF for x in v])

    def i32(self, *v):
        self.b += struct.pack('<%di' % len(v), *[int(x) for x in v])

    def f32(self, *v):
        self.b += struct.pack('<%df' % len(v), *[float(x) for x in v])

    def f64(self, *v):
        self.b += struct.pack('<%dd' % len(v), *[float(x) for x in v])

    def octets(self, x):
        self.u32(len(x)); self.b += bytes(x)
        self.b += b'\0' * ((-len(x)) % 4)

    def texte(self, s):
        self.octets(s.encode('utf-8'))


class Scene:
    def __init__(self):
        self.noms, self.noms_i = [], {}
        self.shaders, self.shaders_i = [], {}
        self.progs, self.progs_i = [], {}
        self.tex, self.tex_i = [], {}
        self.geo, self.geo_i = [], {}
        self.dessins = []

    def nom(self, s):
        if s not in self.noms_i:
            self.noms_i[s] = len(self.noms); self.noms.append(s)
        return self.noms_i[s]

    def shader(self, nom, ext):
        k = (nom, ext)
        if k not in self.shaders_i:
            code = RI.code_shader(nom, ext)
            if not code:
                return None
            self.shaders_i[k] = len(self.shaders); self.shaders.append(({'vfxo': 0, 'pfxo': 1, 'gfxo': 2}[ext], code))
        return self.shaders_i[k]

    def programme(self, vs, ps, couleur_f=False):
        """comme Rendu.programme : entrées du VS (formats identiques), tampons des deux étapes ; couleur_f = particules
        (couleur des sommets en flottants)"""
        k = (vs, ps, couleur_f)
        if k in self.progs_i:
            return self.progs_i[k]
        iv, ip = self.shader(vs, 'vfxo'), self.shader(ps, 'pfxo')
        if iv is None or ip is None:
            self.progs_i[k] = None
            return None
        cv, cp = RI.code_shader(vs, 'vfxo'), RI.code_shader(ps, 'pfxo')
        rv, rp = RI.reflexion(cv), RI.reflexion(cp)
        # geometry shader du jeu (FakeParticle), comme Rendu.programme : celui du PS, sinon celui du VS
        nom_g = ps if RI.code_shader(ps, 'gfxo') else vs if RI.code_shader(vs, 'gfxo') else None
        ig = self.shader(nom_g, 'gfxo') if nom_g else None
        rg = RI.reflexion(RI.code_shader(nom_g, 'gfxo')) if nom_g else {'cb': {}, 'vars': {}}
        fmt = {'POSITION': D.RGB32F, 'COLOR': D.RGBA32F if couleur_f else D.RGBA8, 'TEXCOORD': D.RG32F, 'TANGENT': D.RGBA32F,
               'BLENDWEIGHT': D.RGBA32F, 'BLENDINDICES': 3}
        el = [(n, i, fmt.get(n, D.RGB32F), s) for s, (n, i, masque, reg) in enumerate(rv['entrees']) if not n.startswith('SV_')]
        for n, *_ in el:                             # (noms enregistrés ICI : la table des noms est écrite avant les programmes)
            self.nom(n)
        etapes = []
        for r in (rv, rp, rg):
            cbs = []
            for nom_cb, slot in r['cb'].items():
                vs_ = r['vars'].get(nom_cb, [])
                taille = (max([o + t for _, o, t in vs_] + [16]) + 15) // 16 * 16
                cbs.append((self.nom(nom_cb), slot, taille, [(self.nom(v), o, t) for v, o, t in vs_]))
            etapes.append(cbs)
        self.progs_i[k] = len(self.progs)
        self.progs.append({'vs': iv, 'ps': ip, 'gs': ig, 'el': el, 'etapes': etapes, 'vs_tex': 1 if rv.get('tex') else 0,
                           'cles': (vs, ps), 't11': 't11' in rp.get('tex', {})})
        return self.progs_i[k]

    def texture(self, cle):
        """comme Rendu.texture : PNG du cache (RGBA8) ; « alpha:… » = alpha recopié dans les 4 canaux ; absente = blanc (-1)"""
        if not cle or cle.split('/')[-1].startswith('?'):
            return -1
        if cle in self.tex_i:
            return self.tex_i[cle]
        m = getattr(self, 'modifs', {}).get(cle)      # texture recolorée dans l'Atelier (pixels envoyés par la page)
        if m:
            self.tex_i[cle] = len(self.tex); self.tex.append((m[0], m[1], m[2], mips_texture(cle)))
            return self.tex_i[cle]
        alpha = cle.startswith('alpha:')
        f = os.path.join(RI.CACHE, *(cle[6:] if alpha else cle).split('/')) + '.png'
        if not os.path.exists(f):
            self.tex_i[cle] = -1
            return -1
        w, h, rows = images.lire_png(f)
        if alpha:
            px = bytearray()
            for r in rows:
                a = bytes(r[3:w * 4:4]); q = bytearray(4 * w); q[0::4] = a; q[1::4] = a; q[2::4] = a; q[3::4] = a; px += q
        else:
            px = b''.join(bytes(r[:w * 4]) for r in rows)
        self.tex_i[cle] = len(self.tex); self.tex.append((w, h, bytes(px), mips_texture(cle[6:] if alpha else cle)))
        return self.tex_i[cle]

    def geometrie(self, chemin, i, el):
        """comme Rendu.geometrie : un flux de sommets par entrée du VS"""
        k = (chemin, i, tuple(el))
        if k in self.geo_i:
            return self.geo_i[k]
        ob = _objet(chemin)
        pos, col, idx, uv = ob.geometrie(i)
        nv = len(pos) // 3
        sup = ob.uv_sup(i)
        flux = []
        for n, s_i, f, slot in el:
            if n == 'POSITION':
                b = struct.pack('<%df' % len(pos), *pos); p = 12
            elif n == 'COLOR':
                c = col if s_i == 0 else ob.couleur1(i)
                b = bytes(c) if c else b'\xff' * (4 * nv); p = 4
            elif n == 'TEXCOORD':
                u = uv if s_i == 0 else (sup[s_i - 1] if s_i - 1 < len(sup) else uv)
                b = struct.pack('<%df' % len(u), *u); p = 8
            elif n == 'TANGENT':
                v = RI.tangentes4(ob, i, nv)
                b = struct.pack('<%df' % len(v), *v); p = 16
            elif n == 'NORMAL':
                v = ob.normales(i, 'nor') or [0, 0, 1] * nv
                b = struct.pack('<%df' % len(v), *v); p = 12
            elif n in ('BLENDWEIGHT', 'BLENDINDICES'):
                pe = ob.peau(i) if hasattr(ob, 'peau') else None
                if n == 'BLENDWEIGHT':
                    b = struct.pack('<%df' % (4 * nv), *pe[0]) if pe else struct.pack('<4f', 1, 0, 0, 0) * nv
                else:
                    b = struct.pack('<%dI' % (4 * nv), *pe[1]) if pe else b'\0' * (16 * nv)
                p = 16
            else:
                b = b'\0' * (12 * nv); p = 12
            flux.append((p, b))
        self.geo_i[k] = len(self.geo); self.geo.append((flux, idx))
        return self.geo_i[k]

    def dessin(self, a, passe):
        """une pièce du stade pour une passe (0 profondeur, 1 couleur, 2 cartes d'ombre), résolue comme Rendu.dessiner.
        Cartes d'ombre (Rendu.ombres_stade) : TOUTES les pièces (niveaux de détail compris, pièces d'ombre seules), sauf
        « noshadow »."""
        if passe == 2:
            if a.get('sans_ombre'):
                return
        elif a.get('ombre_seule'):
            return
        if passe in (0, 2):
            vs = ps = 'depth_cutout' if a['cutout'] else 'depth'
            tex = [None, RI.masque_cutout(a)]
            ub = [1.0, 0, 0, a['seuil']]
        else:
            vs, ps = a['vs'], a['ps']
            tex = list(a['tex'])
            ub = [1.0, 0, 0, a['seuil']]      # (14/11/2026) seuil d'alpha du matériau aussi en passe couleur (LU 0x1405948f8)
        k = self.programme(vs, ps)
        if k is None:
            return
        P = self.progs[k]
        g = self.geometrie(a['chemin'], a['piece'], P['el'])
        ob = _objet(a['chemin'])
        noms_mat = ob.materiaux[ob.pieces[a['piece']]['materiau']].get('textures') or []
        tex = [t or (a['cle'].split('/')[0] + '/' + noms_mat[j].split('/')[-1] if j < len(noms_mat) else None) for j, t in enumerate(tex)]
        ids = []
        for j in range(6):
            cle = tex[j] if j < len(tex) else (tex[0] if tex else None)
            ids.append(self.texture(cle) if cle else -1)
        ad = a.get('adressage') or []
        adr = [list(ad[j]) if j < len(ad) else [1, 1] for j in range(6)]
        M = a.get('inst')
        lod_r = a.get('lod_r')
        self.dessins.append({'passe': passe, 'prog': k, 'geo': g, 'tex': ids, 'adr': adr, 'faces': a.get('faces') or 0,
                             'params': (a['params'] + [[0, 0, 0, 0]] * 8)[:8], 'diffuse': a['diffuse'], 'ambient': a['ambient'],
                             'uv': a['uv'], 'ub': ub, 'inst': M or [1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1],
                             'a_inst': 1 if M else 0, 'lod': a.get('lod', 0), 'lod_r': lod_r if lod_r is not None else float('nan')})


def cubemap(code):
    """comme Rendu.cubemap_jeu : bloc BC6H du stade + cb9"""
    import glob as _g, struct as _s
    from moteur import carte, particules as _pt
    crc = None
    for f in sorted(_g.glob(os.path.join(RI.DATA, 'common', 'map', 's', code, 'config', code + '_env_data_*.cfg.bin'))):
        for nom, v in _pt.lire_brut(f):
            if nom == 'TEXTURE_SET_INFO_GROUP_DATA' and len(v) >= 3 and v[2][1]:
                crc = v[2][1] & 0xFFFFFFFF; break
        if crc:
            break
    tex = carte._g4tx_index(os.path.join(RI.DATA, 'dx11', 'map', 's', code))
    if crc not in tex:
        return None
    f, k = tex[crc]
    b = open(f, 'rb').read()
    deb = len(b) - _s.unpack_from('<I', b, 0x2C)[0]
    o, size = _s.unpack_from('<II', b, 0x60 + k * 0x30 + 4)
    bloc = b[deb + o:deb + o + size]
    h, w = _s.unpack_from('<II', bloc, 12)
    mips = _s.unpack_from('<I', bloc, 28)[0]
    fmt = _s.unpack_from('<I', bloc, 128)[0]
    return w, h, mips, fmt, bloc[148:]


_MIPS = {}


def mips_texture(cle):
    """(14/11/2026) NOMBRE DE MIPS de la texture dans son .g4tx (entrée de 0x30 octets, octet +0x11 ; LU, voir « Format
    G4TX ») : 34 048 des 34 130 textures d'effets n'en ont qu'UN (le jeu les lit toujours en pleine résolution) ; les
    personnages en ont presque tous. 0 = .g4tx introuvable (le lecteur garde alors sa chaîne complète)."""
    if not cle or '/' not in cle:
        return 0
    obj, nom = cle.split('/', 1)
    if obj not in _MIPS:
        import glob
        from moteur import g4 as _g4
        t = {}
        for f in glob.glob(os.path.join(RI.DATA, 'dx11', '**', obj + '.g4tx'), recursive=True)[:1]:
            b = open(f, 'rb').read()
            try:
                noms = _g4.noms_textures_g4tx(b)
                n = struct.unpack_from('<H', b, 0x20)[0]
                for k in range(min(n, len(noms))):
                    t[noms[k]] = b[0x60 + k * 0x30 + 0x11]
            except Exception:
                pass
        _MIPS[obj] = t
    return _MIPS[obj].get(nom, 0)


def ecrire_base(o, S):
    """noms, shaders, programmes, textures, géométries (même format pour le décor et pour les effets)"""
    o.u32(len(S.noms))
    for n in S.noms:
        o.texte(n)
    o.u32(len(S.shaders))
    for genre, code_sh in S.shaders:
        o.u32(genre); o.octets(code_sh)
    o.u32(len(S.progs))
    for P in S.progs:
        o.u32(P['vs'], P['ps'], 0xFFFFFFFF if P.get('gs') is None else P['gs'], P['vs_tex'], 1 if P.get('t11') else 0)
        o.u32(len(P['el']))
        for n, i, f, s in P['el']:
            o.u32(S.nom(n), i, f, s)
        for cbs in P['etapes']:
            o.u32(len(cbs))
            for nom_cb, slot, taille, vs_ in cbs:
                o.u32(nom_cb, slot, taille, len(vs_))
                for v, off, t in vs_:
                    o.u32(v, off, t)
    o.u32(len(S.tex))
    for w, h, px, mips in S.tex:
        o.u32(w | (min(mips, 255) << 24), h); o.octets(px)   # octet haut = nombre de mips du .g4tx (0 : inconnu)
    o.u32(len(S.geo))
    for flux, idx in S.geo:
        o.u32(len(flux))
        for p, b in flux:
            o.u32(p); o.octets(b)
        o.octets(struct.pack('<%dH' % len(idx), *idx))


def ecrire_scene(chemin, code, reglages_liste):
    S = Scene()
    L = RI.stade_appels(code)
    for passe in (0, 1, 2):
        for a in L:
            S.dessin(a, passe)
    o = Sortie()
    o.b += MAGIC_SCENE
    ecrire_base(o, S)
    o.u32(len(S.dessins))
    for d in S.dessins:
        o.u32(d['passe'], d['prog'], d['geo']); o.i32(*d['tex'])
        for u, v in d['adr']:
            o.u32(u, v)
        o.u32(d['faces'], d['a_inst']); o.i32(d['lod']); o.f32(d['lod_r'])
        o.f32(*[x for p in d['params'] for x in (list(p) + [0, 0, 0, 0])[:4]])
        o.f32(*(list(d['diffuse']) + [0] * 4)[:4]); o.f32(*(list(d['ambient']) + [0] * 4)[:4])
        o.f32(*[x for m in d['uv'] for x in (list(m) + [0] * 8)[:8]])
        o.f32(*d['ub']); o.f64(*d['inst'])
    # réglages de lumière : une image CLightData (+ brouillard converti) par jeu de réglages des plans
    import brouillard_jeu
    o.u32(len(reglages_liste))
    for rg in reglages_liste:
        img = RI.image_lumiere(rg) or bytes(0x1000)
        o.octets(img); o.octets(brouillard_jeu.convertir(img[0x540:0x620]))
        o.f32(*reglages_resolus(rg, RI.image_lumiere(rg)))        # (étape 4 : passes d'écran)
    # cubemap (t14) + cb9 ; lumières ponctuelles vides (cb8, t17, t18) comme Rendu.lier_lumieres([])
    cm = None
    try:
        cm = cubemap(code)
    except Exception as ex:
        print('cubemap :', ex)
    if cm:
        w, h, mips, fmt, octs = cm
        o.u32(1, w, h, mips, fmt); o.octets(octs)
    else:
        o.u32(0)
    o.octets(struct.pack('<4I', 1 << 16 if cm else 0, 0, 0, 0) + bytes(16) + struct.pack('<IIff', 0, 0xFFFFFFFF, 1.0, 0) + bytes(4096))
    o.octets(struct.pack('<4I', 0, 0, 0, 0) + struct.pack('<4f', 1.0, 1.0, 0, 0) + bytes(32))
    o.octets(bytes(4) + bytes([255]) * 4)
    os.makedirs(os.path.dirname(chemin), exist_ok=True)
    open(chemin, 'wb').write(bytes(o.b))
    return {'dessins': len(S.dessins), 'programmes': len(S.progs), 'textures': len(S.tex), 'geometries': len(S.geo),
            'shaders': len(S.shaders), 'octets': len(o.b)}


I4 = [1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1]
MELANGES = {'opaque': 0, 'profondeur': 1, 'alpha': 2, 'add': 3, 'sous': 4}


def reglages_resolus(rg, img):
    """ÉTAPE 4 : réglages des passes d'écran, résolus EXACTEMENT comme rendu_image / post.py (mêmes valeurs par défaut)
    -> liste de 64 flottants (ordre lu par le lecteur : voir Reglages dans lecteur.cpp)"""
    import post as _post
    rg = rg or {}
    R = dict(_post.REGLAGES)
    v = lambda k, n, dft: (list(rg[k]) + list(dft))[:n] if k in rg else list(dft)
    if rg:
        R['subLum'] = tuple(v('bloomSubLumPost', 4, R['subLum'])); R['subLumPre'] = tuple(v('bloomSubLumMap', 4, R['subLumPre']))
        R['intensite'] = tuple(v('bloomIntensity', 3, R['intensite'])); R['alpha'] = tuple(v('bloomAlphaBlendRate', 3, R['alpha']))
        R['blanc'] = v('tonemapLumMax', 1, [R['blanc']])[0]; R['gris'] = v('tonemapLumMiddle', 1, [R['gris']])[0]
        R['actif'] = v('tonemapEnable', 1, [R['actif']])[0]; R['actif_joueurs'] = v('tonemapEnableChara', 1, [R['actif_joueurs']])[0]
    scr = (v('tonemapScrLumEnable', 1, [0.0])[0], v('tonemapScrLum', 1, [1.0])[0])
    taux = v('tonemapFadeSpeed', 1, [1.0])[0] / 60.0
    pas = list(v('bloomTexStepSize', 3, [1.0, 1.0, 1.0]))
    # SSAO (ssao_jeu) : cb0 sans les tailles d'écran
    import math
    ssao = [0.0] * 17
    if img and (rg.get('enableSSAO') or [0])[0]:
        num = int((rg.get('ssaoSamplingNum') or [8])[0])
        col = list(struct.unpack_from('<4f', img, 0xAB0))
        scale, longueur, angle, acc, rayon, enz = struct.unpack_from('<6f', img, 0xAC0)
        if scale > 0 and num:
            c = math.cos(angle * 0.01745329238474369)
            ssao = [1.0] + col + [1 / longueur if longueur > 0 else 1.0, c, 1 / (1 - c) if c != 1 else 1.0, scale] \
                + [10 ** acc, 10 ** -acc, 0, 0] + [rayon, enz, float(num), 0]
    rate = struct.unpack_from('<f', img, 0xADC)[0] if img else 0.0
    if rg.get('footShadowRate'):
        rate = float(rg['footShadowRate'][0])
    g = lambda k, dft: (rg.get(k) or dft)
    ciel = [float(bool((rg.get('useFogSky') or [1])[0])), float((rg.get('fogSkyRadius') or [4000])[0])]
    dof = [float(bool((rg.get('enableDoF', [1]) or [1])[0])), float(min(32, int(g('dofGaussCnt', [1])[0]))),
           float(g('dofFocusNearZ', [0.3])[0]), float(g('dofFocusFarZ', [10])[0]), float(g('dofFocusIn', [0.7])[0]),
           float(g('dofFocusOut', [30])[0]), float(g('dofFrontStrength', [1])[0]), float(g('dofBackStrength', [1])[0])]
    gp = list(g('dofGaussParam', [1.0, 2.0])) + [2.0]
    dof += [float(gp[0]), float(gp[1]), float(g('dofFocusTexelOffset', [1])[0]), float(int(g('dofUseAutoFocus', [1])[0]))]
    # (14/11/2026) scatter occlusion : CLightData +0xB68 Scale, +0xB70 Near, +0xB74 Far (LU 0x1413486d0 -> scène +0x2F34…)
    sc = list(struct.unpack_from('<f', img, 0xB68)) + list(struct.unpack_from('<2f', img, 0xB70)) if img else [0.0, 1.0, 40.0]
    for j, k in enumerate(('scatterOcclusionScale', 'scatterOcclusionNear', 'scatterOcclusionFar')):
        if rg.get(k):
            sc[j] = float(rg[k][0])
    out = list(R['subLum']) + list(R['subLumPre']) + list(R['intensite']) + list(R['alpha']) + [R['blanc'], R['gris'], R['actif'],
           R['actif_joueurs'], scr[0], scr[1], taux] + pas + ssao + [rate] + ciel + dof + sc
    return [float(x) for x in (out + [0.0] * 64)[:64]]


PROGS_SPECIAUX = ['SSAO', 'foot_shadow_ao', 'map_fogsky', 'edge', 'edge_tone', 'edge_composi', 'gauss', 'depth_of_field', 'depth',
                  # (14/11/2026) scatter occlusion (LU 0x14133e290) : profondeur réduite, tranches, suréchantillonnage -> t13.z
                  ('2d_direct', '2d_depth_nt'), 'scatter_occlusion', ('2d_direct', 'scatter_occlusion_upsampling'),
                  # (14/11/2026) normale « simple » du SSAO (LU 0x14133c510) : reconstruite depuis la profondeur
                  ('2d_direct', 'simple_nrm_from_dep'),
                  # (14/11/2026) flou bilatéral de PreShading (LU 0x14133b950)
                  ('gauss_l', 'pre_shading_bilateral'),
                  # (14/11/2026) couches 37-38 au tiers de l'écran (LU 0x14132d760 / 0x14132d1b0)
                  ('2d_direct', '2d_direct_depth'), ('2d_direct', 'neighborhood_similarity_upsampling')]
PS_SEULS = ['shadow_ss', 'bloom_sublum_composi', 'bloom_gauss', 'bloom_composi', 'tonemap', 'taa', 'taa_oneframe']


def acteur_modele(quoi, code):
    """modèle d'acteur (AtelierD3D/acteurs.ACTEURS), chargé comme le serveur si la page ne l'a pas encore fait"""
    import acteurs as _A
    cle = ('joueur' if quoi == 'joueur' else 'chr', code or '')
    if cle not in _A.ACTEURS:
        _srv().modele_binaire('joueur' if quoi == 'joueur' else 'chr', code or None)
    return _A.ACTEURS.get(cle)


class Effets:
    """ÉTAPE 2 : pièces et particules des effets de la technique. Chaque dessin de la page (dans l'ordre) devient :
    un « élément » fixe (programme, géométrie, textures, adressage, mélange : effets.bin) + son état de l'image
    (matrices, paramètres animés, opacité, os, quadrilatères des particules : images.bin). Résolu comme
    Rendu.dessiner / Rendu.dessiner_particules."""

    def __init__(self, modifs):
        self.S = Scene(); self.S.modifs = modifs
        self.elems, self.elems_i = [], {}
        self.ignores = {}
        self.acteurs, self.acteurs_i = [], {}          # modèles d'acteurs : (quoi, code) -> n°
        # passes d'écran du jeu (étapes 3 et 4) : programmes complets, PS seuls (VS de l'Atelier), textures du système
        self.speciaux = [self.S.programme(*n) if isinstance(n, tuple) else self.S.programme(n, n) for n in PROGS_SPECIAUX]
        self.ps_seuls = []
        for n in PS_SEULS:
            code = RI.code_shader(n, 'pfxo')
            r = RI.reflexion(code)
            cbs = [(self.S.nom(nc), slot, (max([o + t for _, o, t in r['vars'].get(nc, [])] + [16]) + 15) // 16 * 16,
                    [(self.S.nom(v), o, t) for v, o, t in r['vars'].get(nc, [])]) for nc, slot in r['cb'].items()]
            self.ps_seuls.append((self.S.shader(n, 'pfxo'), cbs))
        try:
            import textures_chr
            textures_chr.preparer(RI.DATA, RI.CACHE, images.ecrire_png)
        except Exception as ex:
            print('textures du système :', ex)
        self.tex_sys = [self.S.texture('systeme/chr_tex/chrGrd_01'), self.S.texture('systeme/chr_tex/edgeTone01')]

    def acteur(self, quoi, code):
        """ÉTAPE 3 : un modèle d'acteur, résolu comme rendu_image.dessiner_acteur / acteurs.Acteur"""
        k = (quoi, code or '')
        if k in self.acteurs_i:
            return self.acteurs_i[k]
        ac = acteur_modele(quoi, code)
        if ac is None:
            self.acteurs_i[k] = None
            return None
        import numpy as np
        import acteurs as _A
        S = self.S
        pieces = []
        for p in ac.pieces:
            mg, m = p['mg'], p['m']; nv = m['nv']
            mat = p['mat'] or {}
            prog = S.programme(mat['vs'], mat['ps']) if mat.get('vs') and not p['noir'] else None
            ps2 = (mat.get('ps') or '') + '_effstatus'
            prog_st = S.programme(mat['vs'], ps2) if prog is not None and RI.code_shader(ps2, 'pfxo') else None
            brut = np.frombuffer(mg, dtype=np.uint8, count=nv * m['pas'], offset=m['vb']).reshape(nv, m['pas'])
            pos = np.ascontiguousarray(brut[:, :12]).view('<f4').reshape(nv, 3)
            nor = _A._attr(mg, m, 2, 3); tan = _A._attr(mg, m, 3, 4)
            nor = np.tile([0.0, 1.0, 0.0], (nv, 1)).astype(np.float32) if nor is None else nor.astype(np.float32)
            tan = np.tile([1.0, 0.0, 0.0, 1.0], (nv, 1)).astype(np.float32) if tan is None else tan.astype(np.float32)
            col, uvs, idx = ac.attributs(ac.pieces.index(p))
            tex = []
            for j in range(6):
                nom = mat['tex'][j] if j < len(mat.get('tex') or []) else None
                tex.append(S.texture(p['dossier'] + '/' + nom) if nom and not nom.startswith('?') else -1)
            ad = mat.get('adressage') or []
            tp = [(list(t) + [0] * 8)[:8] for t in (mat.get('texproj') or [])]
            pieces.append({'noir': bool(p['noir']), 'prog': -1 if prog is None else prog, 'prog_st': -1 if prog_st is None else prog_st,
                           'nv': nv, 'pos': pos.astype('<f4').tobytes(), 'nor': np.ascontiguousarray(nor[:, :3], '<f4').tobytes(),
                           'tan': np.ascontiguousarray(tan[:, :4], '<f4').tobytes(),
                           'os': np.ascontiguousarray(p['os'], '<u4').tobytes(), 'poids': np.ascontiguousarray(p['poids'], '<f8').tobytes(),
                           'col': bytes(col), 'uvs': [np.ascontiguousarray(u, '<f4').tobytes() for u in uvs], 'idx': idx.astype('<u2').tobytes(),
                           'tex': tex, 'adr': [list(ad[j]) if j < len(ad) else [1, 1] for j in range(6)],
                           'params': [(list(x) + [0] * 4)[:4] for x in (mat.get('params') or [])][:8] + [[0, 0, 0, 0]] * (8 - len((mat.get('params') or [])[:8])),
                           'diffuse': (list(mat.get('diffuse') or [1, 1, 1, 1]) + [0] * 4)[:4], 'ambient': (list(mat.get('ambient') or [0, 0, 0, 1]) + [0] * 4)[:4],
                           'uv': (tp + [[1, 0, 0, 0, 0, 1, 0, 0]] * 6)[:6], 'faces': 1 if (mat.get('etat') or {}).get(0x0E, 0) == 1 else 0})   # clé 0x0E -> CullMode BACK (LU 0x140528eb0)
        self.acteurs_i[k] = len(self.acteurs); self.acteurs.append(pieces)
        return self.acteurs_i[k]

    def element(self, a):
        S = self.S
        part = bool(a.get('geo'))
        if part:
            vs, ps = a.get('vs'), a.get('ps')
            k = S.programme(vs, ps, True)
            tex = a.get('tex') or []
            geo = -1
        else:
            ob = _objet(a['chemin'])
            vs, ps = (a['vs'], a['ps']) if a.get('vs') else RI.noms_shaders(ob, a['piece'])
            if a.get('os_peau'):
                vs = RI.variante_vb(vs)        # (14/11/2026) « X_low » -> « X_vb_low » (LU dans les .fxbin)
            k = S.programme(vs, ps)
            if k is None:
                self.ignores[(vs, ps)] = self.ignores.get((vs, ps), 0) + 1
                return None
            geo = S.geometrie(a['chemin'], a['piece'], S.progs[k]['el'])
            noms_mat = ob.materiaux[ob.pieces[a['piece']]['materiau']].get('textures') or []
            tex = [t or (a['cle'].split('/')[0] + '/' + noms_mat[j].split('/')[-1] if j < len(noms_mat) else None)
                   for j, t in enumerate(a['tex'])]
        if k is None:
            self.ignores[(vs, ps)] = self.ignores.get((vs, ps), 0) + 1
            return None
        ids = []
        for j in range(6):
            cle = tex[j] if j < len(tex) else (tex[0] if tex else None)
            ids.append(S.texture(cle) if cle else -1)
        ad = a.get('adressage') or []
        adr = tuple(tuple(ad[j]) if j < len(ad) else (1, 1) for j in range(6))
        mel = MELANGES.get(a.get('melange') or 'alpha', 2)
        if a.get('faces'):
            mel |= 0x100              # (14/11/2026) bit 8 : faces arrière éliminées (CullMode BACK du jeu, LU)
        mel |= (int(a.get('biais') or 0) & 0xFF) << 16      # bits 16-23 : biais de profondeur (case 0x1C du jeu, LU)
        mel |= (int(a.get('prio', 30)) & 0xFF) << 24         # bits 24-31 : couche de dessin (octet +8 du matériau / priorité des particules, LU)
        # (14/11/2026) 2e mot de l'élément : bit 0 = particules ; bits 8-16 = seuil d'alpha (256 = test coupé ; LU 0x1405948f8)
        part = (1 if part else 0) | ((int(a.get('seuil', 256)) & 0x1FF) << 8)
        cle = (k, geo, tuple(ids), adr, mel, part)
        if cle not in self.elems_i:
            self.elems_i[cle] = len(self.elems); self.elems.append(cle)
        return self.elems_i[cle]

    def ecrire(self, chemin):
        o = Sortie()
        o.b += b'INZE'
        ecrire_base(o, self.S)
        o.u32(len(self.elems))
        for k, geo, ids, adr, mel, part in self.elems:
            o.u32(k); o.i32(geo); o.i32(*ids)
            for u, v in adr:
                o.u32(u, v)
            o.u32(mel, part)
        # étapes 3 / 4 : programmes des passes d'écran, PS seuls, textures du système, acteurs
        o.i32(*[-1 if k is None else k for k in self.speciaux])
        o.u32(len(self.ps_seuls))
        for sh, cbs in self.ps_seuls:
            o.u32(sh, len(cbs))
            for nom_cb, slot, taille, vs_ in cbs:
                o.u32(nom_cb, slot, taille, len(vs_))
                for v, off, t in vs_:
                    o.u32(v, off, t)
        o.i32(*self.tex_sys)
        o.u32(len(self.acteurs))
        for pieces in self.acteurs:
            o.u32(len(pieces))
            for p in pieces:
                o.u32(1 if p['noir'] else 0); o.i32(p['prog'], p['prog_st']); o.u32(p['nv'], p['faces'])
                o.octets(p['pos']); o.octets(p['nor']); o.octets(p['tan']); o.octets(p['os']); o.octets(p['poids']); o.octets(p['col'])
                for u in p['uvs']:
                    o.octets(u)
                o.octets(p['idx']); o.i32(*p['tex'])
                for u, v in p['adr']:
                    o.u32(u, v)
                o.f32(*[x for q in p['params'] for x in q]); o.f32(*p['diffuse']); o.f32(*p['ambient'])
                o.f32(*[x for m in p['uv'] for x in m])
        open(chemin, 'wb').write(bytes(o.b))


def ecrire_dessin(o, e, a):
    """état d'un dessin d'effet à cette image (mêmes valeurs que celles que rendu_image.tampons reçoit)"""
    ecran = a.get('surEcran') or not a.get('ztest', True)
    o.u32(e, (1 if a.get('depthTest') else 0) | (2 if a.get('depthMask') else 0) | (4 if ecran else 0))
    o.f64(*(a.get('mvp') or I4)); o.f64(*(a.get('modele') or I4)); o.f64(*(a.get('V') or I4)); o.f64(*(a.get('P') or I4))
    P = (list(a.get('params') or []) + [[0, 0, 0, 0]] * 8)[:8]
    o.f32(*[x for p in P for x in (list(p) + [0, 0, 0, 0])[:4]])
    o.f32(*(list(a.get('diffuse') or [1, 1, 1, 1]) + [0] * 4)[:4]); o.f32(*(list(a.get('ambient') or [0, 0, 0, 1]) + [0] * 4)[:4])
    uv = [(list(a['uv'][k]) if k < len(a.get('uv') or []) else [1, 0, 0, 0, 0, 1, 0, 0]) for k in range(6)]
    o.f32(*[x for m in uv for x in (m + [0] * 8)[:8]])
    o.f32(P[2][3] if a.get('colonne') is not None else 0.0)
    os_ = a.get('os_peau') or []
    o.u32(len(os_))
    for m in os_:
        o.f64(*m)
    g = a.get('geo')
    if g:                                            # particules : quadrilatères de l'image (calculés par la page)
        nv = len(g['pos']) // 3
        o.u32(nv); o.f32(*g['pos']); o.f32(*g['col'])
        uvs = g.get('uv') or [[0.0] * (2 * nv)]
        for s in range(3):
            o.f32(*(uvs[s] if s < len(uvs) else uvs[0]))
        nor, tan = g.get('nor'), g.get('tan')
        o.u32(1 if nor else 0)
        if nor:
            o.f32(*nor)
        o.u32(1 if tan else 0)
        if tan:
            o.f32(*tan)
        o.octets(struct.pack('<%dH' % len(g['idx']), *g['idx']))


def ecrire_images(chemin, images_, effets=None):
    """images_ : [{'V': 16, 'P': 16, 'lum': n°, 'decor': bool, 'lumieres': […], 'appels': […]}] (matrices WebGL, colonne
    par colonne). Les dessins d'effets sont résolus par « effets » (éléments fixes de effets.bin)."""
    o = Sortie()
    o.b += MAGIC_IMAGES
    o.u32(len(images_))
    for im in images_:
        o.f64(*im['V']); o.f64(*im['P']); o.u32(im.get('lum', 0)); o.u32(1 if im.get('decor', True) else 0)
        L = [l for l in (im.get('lumieres') or []) if l.get('att')][:255]      # comme Rendu.lier_lumieres
        o.u32(len(L))
        for l in L:
            p, c = (list(l['pos']) + [0, 0, 0])[:3], (list(l['col']) + [0, 0, 0])[:3]
            o.f32(p[0], p[1], p[2], float(l['att']), c[0], c[1], c[2]); o.u32(int(l.get('masque', 0xF7)))
        ds = []
        for a in (im.get('appels') or []) if effets else []:
            e = effets.element(a)
            if e is not None:
                ds.append((e, a))
        o.u32(len(ds))
        for e, a in ds:
            ecrire_dessin(o, e, a)
        # étape 3 : ombres du soleil (cascades de la page), acteurs (matrices des os), ombre des pieds, mise au point
        st = (im.get('stade') or {}) if effets else {}
        om = st.get('ombres')
        o.u32(1 if om else 0)
        if om:
            o.u32(int(om.get('taille', 1024)))
            for m in om['vp']:
                o.f64(*m)
            for t in om['tranches']:
                o.f64(t[0], t[1])
            o.f64(*(list(om['dir']) + [0, 0, 0])[:3]); o.f64(*(list(om['biais']) + [0, 0, 0])[:3])
        sta = st.get('statut')
        acts = []
        for A in st.get('acteurs') or []:
            k = effets.acteur(A.get('quoi'), A.get('code')) if effets else None
            if k is not None:
                acts.append((k, A))
        o.u32(len(acts))
        for k, A in acts:
            o.u32(k, len(A.get('pieces') or [])); o.u32(*(A.get('pieces') or []))
            mats = A.get('mats') or []
            o.u32(len(mats) // 16); o.f64(*mats)
            app = bool(sta) and (sta.get('acteur') == A['acteur'] or (str(sta.get('acteur')).startswith('b000001') and str(A['acteur']).startswith('b000001')))
            o.u32(1 if app else 0)
            if app:
                o.f32(*(list(sta.get('col') or [1, 1, 1])[:3] + [1.0]), *(list(sta.get('rim') or [0, 0, 0])[:3] + [float(sta.get('rim_w', 1.0))]),
                      float(sta.get('pow') or 1), 0, 0, 0)
        pieds = [p for p in (st.get('pieds') or []) if len(p) == 12]
        o.u32(len(pieds))
        for p in pieds:
            o.f64(*p)
        o.f64(float(st.get('foyer') or 10.0))
    open(chemin, 'wb').write(bytes(o.b))


# ====================================================================== ANIMATION EN C++ (14/11/2026)
# Le lecteur calcule lui-même l'animation (port exact de web/anim3d.js, web/particules.js et de la partie « animation » de
# web/vue3d.js et web/app.js) : la page n'a plus rien à calculer. Ici, une fois par technique (gardé dans
# scenes/tech_<code>), ce que la page prépare au chargement : données d'animation (/api/anim), pièces dans l'ordre de la
# vue (V.pieces), émetteurs de particules, lumières ponctuelles, personnages, réglages de lumière des plans.
VERSION_TECH = 35           # (30 : 17/11/2026, techniques des mods recomposées par VRFW) à changer à chaque modification de tech.json / effets.bin (la technique est alors refaite)
VERSION_SCENE = 5          # décor seul (scene.bin) : ne dépend plus des réglages de la technique
SRV = None                 # module du serveur de l'Atelier (posé par serveur.py ; sinon importé)


def _objet(chemin):
    """(17/11/2026) objet d'effet : chemins des mods (« racine:<mod>|… », « mod:/chr/<code> ») lus par le serveur de l'Atelier
    (racine superposée, copies recolorées) ; les autres par rendu_image comme avant"""
    if chemin.startswith(('racine:', 'mod:/chr/')):
        return _srv().objet(chemin)
    return RI.objet(chemin)


def _srv():
    global SRV
    if SRV is None:
        sys.path.insert(0, RI.COULEURS)
        import serveur as _s
        SRV = _s
    return SRV


def mode_du_shader(ps):
    """web/app.js modeDuShader (seul le signe compte ici : < 0 = DofMask, pas dessiné)"""
    import re
    return -1 if re.match(r'^Effect_DofMask', ps or '') else 0


def _seulement_corps(an, corps=1):
    """comme chargerAnimation : le joueur prend le squelette et les gestes de la corpulence 1 (joueur noir)"""
    for a in an.get('acteurs') or []:
        c = a.get('corps')
        if a.get('modele') == 'joueur' and c:
            x = c.get(corps) or c.get(str(corps))
            if x:
                a['os'], a['clips'] = x['os'], x['clips']
                if x.get('collision'):
                    a['collision'] = x['collision']
                a['nus'], a['g4sk'] = x.get('nus'), x.get('g4sk')
        a.pop('corps', None)


def exporter_technique(code, force=False):
    """scenes/tech_<code>/ : tech.json (animation + pièces + émetteurs + lumières + personnages + réglages),
    effets.bin (ressources), lums.bin (CLightData par réglages), textures.json (clé -> n° de texture : retouches)."""
    import hashlib, time, re, zlib
    t0 = time.time()
    S_ = _srv()
    from moteur import techniques as _tq, anim as _an
    dos = os.path.join(ICI, 'scenes', 'tech_' + code)
    f_emp = os.path.join(dos, 'empreinte.txt')
    emp = 'tech %d / effets %d' % (VERSION_TECH, VERSION_FORMAT)
    if not force and os.path.exists(f_emp) and open(f_emp).read() == emp and os.path.exists(os.path.join(dos, 'tech.json')):
        return {'dossier': dos, 'technique': 'gardée'}
    os.makedirs(dos, exist_ok=True)
    t = S_.technique(code)                            # (17/11/2026) + techniques des mods : leur racine superposée
    det = S_.details(code)
    D_, cin, an = S_.anim_de(t)                       # (17/11/2026) + recomposition VRFW, objets ajoutés, son du mod
    _seulement_corps(an)
    telop = an.get('telop')
    for k in ('sons', 'telop', 'joueurs', 'utilisateurs'):
        an.pop(k, None)
    couleur_tir = det.get('couleur_tir') or 0
    # (14/11/2026) LU nie.exe 0x140f12490 / 0x140eff4c0 : la colonne du dégradé BallAura (u_grdValue) vient de la couleur de tir
    # du JOUEUR QUI A TIRÉ (octet +0x75F), sinon d'une clé par défaut liée à sa fiche (0x141605110 -> 0x140ebb5e0). Pour un
    # gardien, le ballon qui arrive est celui de l'adversaire : jamais la couleur du gardien. Vidéos officielles : jaune = 0 (MESURÉ)
    if code.startswith('whk'):
        couleur_tir = 0
    E = Effets({})
    objets_anim = {act: o for act, o in (an.get('objets') or {}).items() if o.get('os')}     # L.objets
    pieces, emetteurs, lumieres = [], [], []
    objs = [o for o in det['objets_details'] if not o.get('erreur')]
    for o in objs:                                    # 1) pièces de maillage (dans l'ordre de V.pieces)
        ob = S_.objet(o['chemin'])
        infos = {ti['nom']: ti for ti in o['textures']}
        cle_tex = lambda n: (o['nom'] + '/' + n) if n and n in infos and infos[n].get('lisible') and not infos[n].get('donnees') else None
        oa = objets_anim.get(o['acteur'])
        par_nom = {}
        if oa:
            for i, x in enumerate(oa['os']):
                par_nom[x['nom']] = i
        for p in o['pieces']:
            i = p['index']
            pos, col, idx, uv = ob.geometrie(i)
            ni = len(idx)
            a_peau = bool(pos) and '/chr/' not in o['chemin'] and bool(ob.peau(i))
            J = p.get('jeu')
            if not ni or not J or not J.get('shader_ps') or not J.get('diffuse') or not p.get('melange'):
                continue
            ps = J['shader_ps']
            if mode_du_shader(ps) < 0:
                continue
            tex = [cle_tex(n) for n in p['textures']]
            os_peau = bool(oa) and bool(p.get('peau')) and a_peau and p['nom'] in par_nom
            e = E.element({'chemin': o['chemin'], 'piece': i, 'cle': o['nom'] + '/' + str(i), 'tex': tex,
                           'adressage': J.get('adressage'), 'melange': p['melange'], 'os_peau': os_peau, 'faces': p.get('faces', 0), 'biais': p.get('biais', 0), 'prio': p.get('prio', 30), 'seuil': p.get('seuil', 256)})
            if e is None:
                continue
            nom_sur = not re.match(r'^(partie[ _]|materiau_)', p.get('shader') or '')
            x = {'cle': o['nom'] + '/' + str(i), 'elem': e, 'opaque': p['melange'] == 'opaque',
                 'ztest': p.get('ztest') is not False, 'zecrit': bool(p.get('zecrit')), 'params': J.get('params') or [], 'texproj': J.get('texproj') or [],
                 'diffuse': J['diffuse'], 'ambient': J.get('ambient') or [0, 0, 0, 1],
                 'uvCrcs': [c & 0xFFFFFFFF for c in (p.get('uv_crcs') or [])], 'alphaRepos': J['diffuse'][3] if nom_sur else 1,
                 'colonne': couleur_tir if re.match(r'^Effect_BallAura', ps) else None}
            if oa:
                x['anim'] = {'acteur': o['acteur'], 'os': par_nom.get(p['nom'], -1), 'mat': p['mat_crc'] & 0xFFFFFFFF,
                             'peau': [par_nom.get(n, -1) for n in p['peau']] if (p.get('peau') and a_peau) else None}
                x['surEcran'] = bool(o.get('commun'))
                x['panneau'] = int(p.get('panneau') or 0)      # (14/11/2026) pièce tournée vers la caméra au dessin (LU)
            pieces.append(x)
    for o in objs:                                    # 2) émetteurs de particules (ajouterEmetteurs), 3) lumières
        if o['acteur'] not in objets_anim:
            continue
        infos = {ti['nom']: ti for ti in o['textures']}
        cle_tex = lambda n: (o['nom'] + '/' + n) if n and n in infos and infos[n].get('lisible') and not infos[n].get('donnees') else None
        for k, dd in enumerate(((o.get('particules') or {}).get('emetteurs')) or []):
            M = dd['materiau']
            ps = dd.get('shader_ps') or M.get('shader') or 'Effect_T1'
            if mode_du_shader(ps) < 0:
                continue
            mel = 'add' if M.get('melange') == 3 else 'sous' if M.get('melange') == 4 else 'normal' if M.get('melange') == 2 else 'opaque'
            tex = [cle_tex(n) for n in (dd.get('textures') or [])] or [None]
            e = E.element({'geo': True, 'vs': dd.get('shader_vs') or ps, 'ps': ps, 'tex': tex,
                           'adressage': list(M.get('adressage') or []) + [[1, 1], [1, 1], [1, 1]], 'melange': mel, 'prio': M.get('priorite', 25)})
            if e is None:
                continue
            sh = dd.get('shader') or []
            graine = (0x9E3779B9 ^ ((k * 2654435761) & 0xFFFFFFFF)) & 0xFFFFFFFF
            emetteurs.append({'cle': o['nom'] + '/ptl' + str(k), 'elem': e, 'acteur': o['acteur'], 'graine': graine,
                              'opaque': mel == 'opaque', 'ztest': bool(M.get('b102')), 'surEcran': bool(o.get('commun')),
                              'monde': ps == 'Effect_SmokePar1',
                              'params': [sh[4 * j:4 * j + 4] for j in range(8)], 'grd': bool(re.match(r'^Effect_BallAura', ps)),
                              'def': {k2: v for k2, v in dd.items() if k2 not in ('shader', 'textures', 'sommets')}})
        L = o.get('lumieres')
        if L and ((L.get('lumieres') or []) or (L.get('shader') or [])):
            lumieres.append({'acteur': o['acteur'], 'def': L})
    acteurs = []                                      # 4) personnages (acteurs.Acteur) dans l'ordre de d.acteurs
    for a in an.get('acteurs') or []:
        quoi, c = ('joueur', '') if a.get('modele') == 'joueur' else ('chr', a.get('code'))
        try:
            k = E.acteur(quoi, c)
        except Exception as ex:
            print('acteur', a.get('acteur'), ex); k = None
        # (15/11/2026) VERSIONS D'UN OBJET DE TECHNIQUE (chr/_waza/evNN_…) : plusieurs maillages de MÊME TAILLE (nombre de sommets
        # et d'indices) = versions du même objet (Choc de la vouivre : dragon clair _10 / sombre _20, sommets identiques ; Cris
        # d'Eden : pomme orange / pomme violette croquée). Le jeu n'en montre qu'une par acteur. DÉDUIT de 2 vidéos officielles
        # (la règle n'est pas encore trouvée dans nie.exe) : acteur « _s00 » à « _s79 » -> 1re version, « _s80 » et plus -> 2e.
        # Les maillages sans double restent tous dessinés. Avant : tout était dessiné, la dernière version recouvrait la 1re.
        montrer = []
        if k is not None and quoi == 'chr' and re.match(r'^ev\d\d_', c or ''):
            ac_ = acteur_modele(quoi, c)
            tailles = [(p['m']['nv'], p['m']['ni']) for p in ac_.pieces] if ac_ is not None else []
            ms = re.search(r'_s(\d\d)_', a['acteur'])
            choix = 1 if ms and int(ms.group(1)) >= 80 else 0
            for i, t in enumerate(tailles):
                groupe = [j for j, u in enumerate(tailles) if u == t]
                montrer.append(len(groupe) == 1 or groupe[min(choix, len(groupe) - 1)] == i)
        acteurs.append({'acteur': a['acteur'], 'modele': -1 if k is None else k, 'pieces': 0 if k is None else len(E.acteurs[k]),
                        'montrer': montrer})
    LP = an.pop('lumiere_plans', None) or {}         # 5) réglages de lumière des plans -> jeux de réglages (lums.bin)
    regl, ri, plan_lum = [], {}, {}
    for nom, g in LP.items():
        kj = json.dumps(g, sort_keys=True)
        if kj not in ri:
            ri[kj] = len(regl); regl.append(g)
        plan_lum[nom] = ri[kj]
    if not regl:
        regl = [{}]
    o_ = Sortie(); o_.b += b'INZL'; o_.u32(len(regl))
    import brouillard_jeu
    for rg in regl:
        img = RI.image_lumiere(rg) or bytes(0x1000)
        o_.octets(img); o_.octets(brouillard_jeu.convertir(img[0x540:0x620])); o_.f32(*reglages_resolus(rg, RI.image_lumiere(rg)))
    open(os.path.join(dos, 'lums.bin'), 'wb').write(bytes(o_.b))
    # bannière (14/11/2026) : image de la technique (celle que montre l'Atelier : dx11/menu/220_img/telop_waza/fr) en RVBA brut
    # -> telop.bin (u32 largeur, hauteur, puis les pixels) ; instants et courbes du modèle de menu du jeu dans tech.json
    f_tel = os.path.join(dos, 'telop.bin')
    if os.path.exists(f_tel):
        os.remove(f_tel)
    if telop and telop.get('courbes'):
        try:
            png = S_.telop_png(telop['code'])
            if os.path.exists(png):
                w, h, rows = images.lire_png(png)
                n = len(rows[0]) // w
                px = bytearray()
                for r in rows:
                    if n == 4:
                        px += bytes(r[:4 * w])
                    else:
                        for x in range(w):
                            px += bytes(r[n * x:n * x + 3]) + b'\xff'
                open(f_tel, 'wb').write(struct.pack('<II', w, h) + bytes(px))
        except Exception as ex:
            print('bannière :', ex)
    tech = {'code': code, 'anim': an, 'pieces': pieces, 'emetteurs': emetteurs, 'lumieres': lumieres, 'acteurs': acteurs,
            'reglages': regl, 'plan_lum': plan_lum, 'telop': telop if (telop and os.path.exists(f_tel)) else None}
    json.dump(tech, open(os.path.join(dos, 'tech.json'), 'w', encoding='utf-8'), separators=(',', ':'))
    json.dump({k: v for k, v in E.S.tex_i.items() if v >= 0}, open(os.path.join(dos, 'textures.json'), 'w', encoding='utf-8'))
    E.ecrire(os.path.join(dos, 'effets.bin'))
    open(f_emp, 'w').write(emp)
    global _DERNIER_EFFETS
    _DERNIER_EFFETS = (code, E)                        # (vérifications : mêmes n° d'éléments pour une animation de la page)
    return {'dossier': dos, 'technique': 'exportée', 'secondes': round(time.time() - t0, 1), 'pieces': len(pieces),
            'emetteurs': len(emetteurs), 'elements': len(E.elems), 'acteurs': len(acteurs),
            'effets_ignores': ['%s/%s x%d' % (k[0], k[1], n) for k, n in E.ignores.items()]}


_DERNIER_EFFETS = None


def exporter_stade(code):
    """scenes/stade_<code>/scene.bin : le décor seul (gardé ; refait seulement si VERSION_SCENE change)"""
    dos = os.path.join(ICI, 'scenes', 'stade_' + code)
    os.makedirs(dos, exist_ok=True)
    f_scene, f_emp = os.path.join(dos, 'scene.bin'), os.path.join(dos, 'empreinte_scene.txt')
    emp = 'scene %d' % VERSION_SCENE
    if os.path.exists(f_scene) and os.path.exists(f_emp) and open(f_emp).read() == emp:
        return {'dossier': dos, 'decor': 'gardé'}
    st = ecrire_scene(f_scene, code, [{}])
    open(f_emp, 'w').write(emp)
    return dict(st, dossier=dos)


def ecrire_modifs(dos_tech, modifs):
    """textures recolorées dans l'Atelier -> modifs.bin (n° de texture d'effets.bin, largeur, hauteur, RGBA)"""
    import base64
    idx = json.load(open(os.path.join(dos_tech, 'textures.json'), encoding='utf-8'))
    o = Sortie(); o.b += b'INZM'
    L = [(idx[k], v) for k, v in (modifs or {}).items() if k in idx]
    o.u32(len(L))
    for i, (w, h, b64) in L:
        o.u32(i, w, h); o.octets(base64.b64decode(b64))
    open(os.path.join(dos_tech, 'modifs.bin'), 'wb').write(bytes(o.b))
    return len(L)


def exporter(demande):
    """demande de la page : {'stade': code, 'images': [{V, P, reglages: n°}], 'reglages': [dict…]}.
    Le décor (scene.bin, ~170 Mo) est gardé par stade et refait seulement si ce fichier (l'exporteur) ou les réglages
    de lumière changent ; images.bin est réécrit à chaque fois."""
    import hashlib
    code = demande['stade']
    dos = os.path.join(ICI, 'scenes', 'stade_' + code)
    os.makedirs(dos, exist_ok=True)
    regl = demande.get('reglages') or [{}]
    empreinte = hashlib.sha1((json.dumps(regl, sort_keys=True) + 'format %d' % VERSION_FORMAT).encode()).hexdigest()
    f_scene, f_emp = os.path.join(dos, 'scene.bin'), os.path.join(dos, 'empreinte.txt')
    st = {'decor': 'gardé'}
    if not (os.path.exists(f_scene) and os.path.exists(f_emp) and open(f_emp).read() == empreinte):
        st = ecrire_scene(f_scene, code, regl)
        open(f_emp, 'w').write(empreinte)
    import base64
    modifs = {k: (v[0], v[1], base64.b64decode(v[2])) for k, v in (demande.get('modifs') or {}).items()}
    E = Effets(modifs)
    ecrire_images(os.path.join(dos, 'images.bin'), [dict(x, lum=x.get('reglages', 0)) for x in demande['images']], E)
    E.ecrire(os.path.join(dos, 'effets.bin'))
    return dict(st, dossier=dos, images=len(demande['images']), elements=len(E.elems),
                effets_ignores=['%s/%s x%d' % (k[0], k[1], n) for k, n in E.ignores.items()])


if __name__ == '__main__':          # essai : stade seul, caméra fixe
    code = sys.argv[1] if len(sys.argv) > 1 else 's10g001'
    print(ecrire_scene(os.path.join(ICI, 'scenes', 'essai', 'scene.bin'), code, [{}]))
