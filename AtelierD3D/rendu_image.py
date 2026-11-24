"""Prototype (13/11/2026) : dessine une image d'une technique avec Direct3D 11 et les VRAIS shaders du jeu (.vfxo/.pfxo).

usage : python rendu_image.py etat.json sortie.png
etat.json = ce que l'Atelier Couleurs dessine à cette image (exporté depuis la page) : pour chaque pièce d'effet, dans
l'ordre, ses matrices, paramètres animés, textures, adressage, mélange.

Ce qui vient du jeu tel quel : shaders DXBC, géométrie, textures, adressage (paires de la table +0x6E, lu dans nie.exe).
(Texte d'origine, prototype du 13/11 : « valeurs APPROCHÉES : u_ubParam, u_softParticleParam, u_eyeNearFarInvAspect.zw… ».)
14/11/2026 : u_ubParam.w = seuil d'alpha LU (0x1405948f8) ; u_softParticleParam = cb6 +688 = CLightData +0x3F0
« softParticleDistance » (cb6 est une copie brute de CLightData dès +0x140) : LU, 1,0 par défaut.
"""
import sys, os, re, json, struct, zlib

ICI = os.path.dirname(os.path.abspath(__file__))
COULEURS = os.path.join(os.path.dirname(ICI), 'AtelierCouleurs')
sys.path.insert(0, COULEURS)
sys.path.insert(0, os.path.join(os.path.dirname(ICI), 'AtelierMaillots'))
from moteur import g4, shaders as _sh          # lecture seule
from lib import images
import d3d11 as D

CFG = json.load(open(os.path.join(COULEURS, 'config.json'), encoding='utf-8'))
DATA = CFG.get('data_dir') or ''
if not os.path.isfile(os.path.join(DATA, 'common', 'text', 'fr', 'chara_text.cfg.bin')):
    from moteur import donnees_virtuelles as _dv     # lecture directe des paquets du jeu
    DATA = (_dv._RACINE_VRAIE if _dv.actif() else _dv.depuis_env()) or \
        _dv.activer(CFG['jeu_dir'], os.path.join(COULEURS, 'cache', 'data_jeu'))
CACHE = os.path.join(COULEURS, 'cache')
DOS_SH = _sh._dossier(DATA)

# ------------------------------------------------------------------ réglages de lumière du jeu (13/11/2026)
# CLightData tel que le construit le jeu (constructeur 0x140f821c0 exécuté dans l'émulateur : nie_outils/gen_clightdata.py)
# + table nom -> décalage (déclarations 0x1402b4fd0). Les tampons des shaders sont des copies de cet objet :
# CBUSE_UB_LIGHT_IDX (cb6) = CLightData +0x140, CBUSE_UB_CHARA_LIGHT_IDX (cb7) = CLightData +0x6B0.
try:
    LUM_DEFAUT = open(os.path.join(ICI, 'clightdata_defaut.bin'), 'rb').read()
    LUM_CHAMPS = json.load(open(os.path.join(ICI, 'clightdata_champs.json'), encoding='utf-8'))
except OSError:
    LUM_DEFAUT, LUM_CHAMPS = None, {}
LUM_BLOCS = {'CBUSE_UB_LIGHT_IDX': 0x140, 'CBUSE_UB_CHARA_LIGHT_IDX': 0x6B0}
# brouillard : nie.exe 0x140f7f050(CLightData +0x140, cb5 +0x250) convertit CLightData +0x540…+0x61F -> cb5[37…50]
import brouillard_jeu
BROUILLARD_NOMS = {'u_RayleighColorP20', 'u_RayleighColorP10', 'u_RayleighColorO00', 'u_RayleighColorM10', 'u_RayleighColorM20',
                   'u_HeightRayleighColor', 'u_MieColorP20', 'u_MieColorO00', 'u_MieColorM20', 'u_fogWorldParam0',
                   'u_fogWorldParam1', 'u_fogHeightParam0', 'u_fogHeightParam1', 'u_RayleighBandRatio'}


_postfx = None


def intensite_postfx(nom, defaut=1.0):
    """réglages globaux des effets d'écran : common/property/posteffect/posteffect_data.cfg.bin (CPostEffectGlobalParam) ;
    ex. intensityDOF = 0,3 (copiée dans l'intensité du jeu de drapeaux n° 0, lue en mémoire le 14/11/2026)"""
    global _postfx
    if _postfx is None:
        _postfx = {}
        try:
            from moteur import particules as _pt
            for n, v in _pt.lire_brut(os.path.join(DATA, 'common', 'property', 'posteffect', 'posteffect_data.cfg.bin')):
                if n == 'PROP_PARAM' and v and isinstance(v[0][1], str) and len(v) > 1:
                    _postfx[v[0][1]] = v[1][1]
        except Exception:
            pass
    try:
        return float(_postfx.get(nom, defaut))
    except (TypeError, ValueError):
        return defaut


def image_lumiere(reglages):
    """CLightData = défauts du constructeur + réglages du plan (light_data -> stade -> plan, envoyés par la page).
    Chaque valeur va à son décalage, sans déborder sur le champ suivant (taille = écart jusqu'au champ suivant, 16 octets
    au plus). Le brouillard (fog*) n'est pas dans cb6 / cb7 : le moteur le convertit dans un autre tampon (0x140f7f050)."""
    if LUM_DEFAUT is None:
        return None
    img = bytearray(LUM_DEFAUT)
    places = sorted(set(LUM_CHAMPS.values()))
    for nom, val in (reglages or {}).items():
        o = LUM_CHAMPS.get(nom)
        if o is None or not isinstance(val, (list, tuple)):
            continue
        suiv = next((q for q in places if q > o), o + 16)
        n = max(0, min(len(val), (suiv - o) // 4, 4))
        vals = [float(x) for x in val[:n] if isinstance(x, (int, float))]
        img[o:o + 4 * len(vals)] = struct.pack('<%df' % len(vals), *vals)
    return bytes(img)


# ------------------------------------------------------------------ matrices (tableaux WebGL : colonne par colonne)
def mul(a, b):
    """a x b (colonne par colonne) ; écrit sans boucles (appelé des dizaines de milliers de fois par image)"""
    a0, a1, a2, a3, a4, a5, a6, a7, a8, a9, a10, a11, a12, a13, a14, a15 = a
    out = []
    for c in (0, 4, 8, 12):
        b0, b1, b2, b3 = b[c], b[c + 1], b[c + 2], b[c + 3]
        out += (a0 * b0 + a4 * b1 + a8 * b2 + a12 * b3, a1 * b0 + a5 * b1 + a9 * b2 + a13 * b3,
                a2 * b0 + a6 * b1 + a10 * b2 + a14 * b3, a3 * b0 + a7 * b1 + a11 * b2 + a15 * b3)
    return out


GL_VERS_D3D = [1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0.5, 0, 0, 0, 0.5, 1]      # z : -1..1 -> 0..1


def proj_params(P):
    """projection perspective WebGL -> (near, far, tan(fov/2) x aspect, tan(fov/2)) ; autre projection : valeurs neutres"""
    try:
        if not P or abs(P[11] + 1) > 1e-6 or not P[0] or not P[5]:
            return [0.05, 8000, 1, 1]
        n, f = P[14] / (P[10] - 1), P[14] / (P[10] + 1)
        return [n, f, 1.0 / P[0], 1.0 / P[5]]
    except (IndexError, ZeroDivisionError, TypeError):
        return [0.05, 8000, 1, 1]


def inv4(m):
    """inverse d'une matrice 4 x 4 (tableau WebGL, colonne par colonne)"""
    import numpy as _np
    try:
        return [float(x) for x in _np.linalg.inv(_np.array(m, dtype=float).reshape(4, 4).T).T.reshape(16)]
    except _np.linalg.LinAlgError:                       # matrice non inversible (effet collé à l'écran…) : zéros
        return [0.0] * 16


def lignes(m):
    """matrice WebGL -> 16 flottants « row_major » HLSL (ligne r = (m[r], m[4+r], m[8+r], m[12+r]))"""
    return [m[c * 4 + r] for r in range(4) for c in range(4)]


# ------------------------------------------------------------------ shaders
_code = {}


def code_shader(nom, ext):
    cle = (nom, ext)
    if cle not in _code:
        f = os.path.join(DOS_SH, nom + '.' + ext)
        d = open(f, 'rb').read() if os.path.exists(f) else b''
        i = d.find(b'DXBC')
        _code[cle] = d[i:i + struct.unpack_from('<I', d, i + 24)[0]] if i >= 0 else None
    return _code[cle]


def teinter_hsv(c, H, C, S=1.0, V=1.0):
    """(14/11/2026) teinte de l'Atelier (opération « set » de VRFW) : même formule que particules.js / animation.h
    (23/11) S = `saturation` de VRFW, multiplicateur appliqué après colorize (émulé dans nie_outils/emu_vrfw.py)"""
    V = 1.0 if V is None else V                    # (23/11) `value` de VRFW : luminosité × V, gris compris (émulé)
    v, mn = max(c), min(c)
    if not v > 0:
        return c
    s = (v - mn) / v
    if s < 0.08:                                   # (15/11/2026) LU dans VRFW : seuil des gris 0,08 ; colorize pour eux seuls
        if not C > 0:
            return [x * V for x in c]
        s = max(s, C)
    s = min(1.0, s * (1.0 if S is None else S))
    v = v * V
    h = (H % 360) / 60.0; i = int(h) % 6; f = h - int(h)
    p, q, t = v * (1 - s), v * (1 - s * f), v * (1 - s * (1 - f))
    return [(v, t, p), (q, v, p), (p, v, t), (p, q, v), (t, p, v), (v, p, q)][i]


def couleurs_teintees(col, t):
    b = bytearray(col)
    for i in range(0, len(b) - 3, 4):
        r = teinter_hsv([b[i] / 255, b[i + 1] / 255, b[i + 2] / 255], t[0], t[1], t[2] if len(t) > 2 else 1.0, t[3] if len(t) > 3 else 1.0)
        for k in range(3):
            b[i + k] = max(0, min(255, int(r[k] * 255 + 0.5)))
    return bytes(b)


def variante_vb(vs):
    """VS « _vb » (peau : BLENDWEIGHT / BLENDINDICES, u_mtxBone) d'un VS d'effet. LU (14/11/2026) dans les .fxbin : la
    2e technique de effect_threshold_grd_low.fxbin est (Effect_ThresholdGrd_vb_low, Effect_ThresholdGrd_low) ; « _vb » se
    place AVANT les suffixes _low / _map / _inst… (Effect_T1_vb_low, Effect_T1M1_vb_low, Effect_ThresholdGrd_vb_inst).
    Avant : seulement vs + « _vb » -> les rubans de vent de Dernier recours (Effect_ThresholdGrd_low) restaient au repos."""
    if vs.endswith('_vb') or '_vb_' in vs:
        return vs
    if code_shader(vs + '_vb', 'vfxo'):
        return vs + '_vb'
    for suf in ('_instrw_alpha', '_inst_alpha', '_instrw', '_inst', '_low', '_map', '_bs'):
        if vs.endswith(suf) and code_shader(vs[:-len(suf)] + '_vb' + suf, 'vfxo'):
            return vs[:-len(suf)] + '_vb' + suf
    return vs


_refl = {}


def reflexion(code):
    """entrées du VS, tampons (nom -> slot, variables), textures/échantillonneurs, depuis le désassemblage"""
    k = zlib.crc32(code)
    if k in _refl:
        return _refl[k]
    t = D.desassembler(code)
    r = {'entrees': [], 'cb': {}, 'vars': {}, 'tex': {}}
    cb = None
    bloc = None
    for l in t.splitlines():
        if l.startswith('// Input signature'):
            bloc = 'in'; continue
        if l.startswith('// Output signature'):
            bloc = None; continue
        m = re.match(r'// cbuffer (\w+)', l)
        if m:
            cb = m.group(1); r['vars'][cb] = []; continue
        m = re.match(r'//\s+(?:row_major )?(\w+) (\w+)(?:\[(\d+)\])?;\s+// Offset:\s+(\d+) Size:\s+(\d+)', l)
        if m and cb:
            r['vars'][cb].append((m.group(2), int(m.group(4)), int(m.group(5)))); continue
        m = re.match(r'// (\w+)\s+(cbuffer|texture|sampler)\s+\S+\s+\S+\s+(cb|t|s)(\d+)\s+\d+', l)
        if m:
            if m.group(2) == 'cbuffer':
                r['cb'][m.group(1)] = int(m.group(4))
            else:
                r['tex'][m.group(3) + m.group(4)] = m.group(1)
            continue
        if bloc == 'in':
            m = re.match(r'// (\w+)\s+(\d+)\s+(\w+)\s+(\d+)\s+(\w+)\s+(\w+)', l)
            if m and m.group(1) != 'Name':
                r['entrees'].append((m.group(1), int(m.group(2)), m.group(3), int(m.group(4))))
    _refl[k] = r
    return r


# ------------------------------------------------------------------ objets du jeu
_obj = {}


def objet(chemin):
    if chemin not in _obj:
        _obj[chemin] = g4.ObjetEffet(DATA, chemin)
    return _obj[chemin]


def tangentes4(ob, i, nv):
    """tangentes x y z w du modèle : valeurs BRUTES (s16 / 32767) comme le jeu les donne au shader ; sinon tangentes lues + w = 1"""
    try:
        pp = ob.pieces[i]
        if pp.get('tan') is not None:
            return [x / 32767 for k in range(nv) for x in struct.unpack_from('<4h', ob.mg, pp['vb'] + k * pp['pas'] + pp['tan'])]
    except Exception:
        pass
    t = ob.normales(i, 'tan') or [1, 0, 0] * nv
    return [x for k in range(len(t) // 3) for x in (t[3 * k], t[3 * k + 1], t[3 * k + 2], 1.0)]


# ------------------------------------------------------------------ stade (décor) dessiné avec les vrais shaders du jeu
_stades = {}


def stade_appels(code):
    """morceaux du stade (common/map/s/<code>) : chemin, pièce et matériau EXACT du jeu (shader, textures par case,
    u_shaderParam, couleurs, u_texProj) ; lus comme pour l'aperçu WebGL (moteur/carte.py), une fois par stade"""
    if code in _stades:
        return _stades[code]
    from moteur import carte
    dc = os.path.join(CACHE, 'carte_' + code)
    os.makedirs(dc, exist_ok=True)
    tex = carte._g4tx_index(os.path.join(DATA, 'dx11', 'map', 's', code))
    out = []
    for m in carte.morceaux(DATA, code):
        chemin = 'common/map/s/%s/%s/%s.objbin' % (code, m, m)
        try:
            ob = objet(chemin)
            mats = carte._materiaux_exacts(ob.md, tex, dc, code)
        except Exception:
            continue
        out += _appels_objet(ob, chemin, mats, code, 'carte_%s/%s' % (code, m))
    try:                                                 # objets placés (herbes, arbres, objets « ao »)
        out += objets_places(code, dc, tex)
    except Exception as ex:
        print('objets placés :', ex)
    _stades[code] = out
    return out


_png_existe = {}
# valeurs propres à CHAQUE dessin (le reste des tampons ne dépend que de l'image : caméra, lumière, ombre)
PAR_DESSIN = {'u_mtxLW', 'u_mtxLV', 'u_mtxLP', 'u_mtxLWOld', 'u_mtxLVOld', 'u_ubParam', 'u_diffuse', 'u_ambient', 'u_speculer',
              'u_attachScale', 'u_grdValue', 'u_texProj', 'u_uvRange', 'u_mtxBone', 'u_charaStatusColor', 'u_charaStatusRimColor',
              'u_charaStatusPowInOutDis', 'u_skinColor', 'u_hairColor', 'u_subColor1', 'u_subColor2', 'u_pointLightHeader0',
              'u_pointLightHeader1'}


def masque_cutout(a):
    """in_texAlpha (t1) de depth_cutout = CASE 1 du matériau, comme le jeu (case k -> t_k) : masque « .a » (BC4) des
    arbres ; sans case 1 lisible : alpha de la texture de couleur (ancien choix, DÉDUIT)"""
    tx = a.get('tex') or []
    if len(tx) > 1 and tx[1]:
        ok = _png_existe.get(tx[1])
        if ok is None:                                   # (vérifié une fois par texture, pas à chaque dessin)
            ok = _png_existe[tx[1]] = os.path.exists(os.path.join(CACHE, *tx[1].split('/')) + '.png')
        if ok:
            return tx[1]
    return ('alpha:' + tx[0]) if tx and tx[0] else None


def visible_lod(a, oeil):
    """niveau de détail et distance d'affichage comme le jeu (LodDataParam.Lv01_Range, CMapAnnotateParam.m_farClip),
    distance œil -> position de l'instance"""
    M = a.get('inst')
    if not M or oeil is None:
        return a.get('lod', 0) != 2
    dist = ((M[12] - oeil[0]) ** 2 + (M[13] - oeil[1]) ** 2 + (M[14] - oeil[2]) ** 2) ** 0.5
    # (m_farClip de CMapAnnotateParam n'est PAS appliqué : rien ne montre qu'il règle l'affichage)
    r = a.get('lod_r')
    # (14/11/2026) LU (0x140527a80, portées rangées au carré par 0x140fb30a0, dernier niveau = 3,4e38) : niveau = premier i
    # avec d² < portée²[i] (boucle « tant que portée²[i] <= d² : i + 1 ») ; d = caméra -> origine de l'instance
    if a.get('lod') == 1:
        return r is None or dist < r
    if a.get('lod') == 2:
        return r is not None and dist >= r
    return True


def _matrice_srt(s):
    """SRT du placement : échelle (3), rotation (3, radians), position (3) -> matrice WebGL (colonne par colonne) T·Rz·Ry·Rx·S
    (14/11/2026) ordre des rotations LU : le lecteur des SRT (0x14025a970) range la rotation avec w = 10,0, marque des angles
    d'Euler pour l'aide 0x140091ef0, qui les lit comme Rz·Ry·Rx (émulée : la rotation donnée vaut celle de ses angles de
    sortie en ordre Y·X·Z, et aucun autre couple d'ordres). Avant : DÉDUIT (même ordre)."""
    import numpy as _np
    sx, sy, sz, rx, ry, rz, tx, ty, tz = [float(x) for x in s[:9]]
    cx, sx_, cy, sy_, cz, sz_ = _np.cos(rx), _np.sin(rx), _np.cos(ry), _np.sin(ry), _np.cos(rz), _np.sin(rz)
    Rx = _np.array([[1, 0, 0], [0, cx, -sx_], [0, sx_, cx]]); Ry = _np.array([[cy, 0, sy_], [0, 1, 0], [-sy_, 0, cy]])
    Rz = _np.array([[cz, -sz_, 0], [sz_, cz, 0], [0, 0, 1]])
    M = _np.identity(4); M[:3, :3] = Rz @ Ry @ Rx @ _np.diag([sx, sy, sz]); M[:3, 3] = [tx, ty, tz]
    return [float(v) for v in M.T.reshape(16)]


def objets_places(code, dc, tex):
    """config/<code>_placement.cfg.bin : NAME [modèle, 1re instance, nombre] puis SRT [échelle, rotation, position, nom] ;
    modèle dans le dossier du stade (s10ao001…) ou dans common/map/ar/<modèle> (textures dx11/map/ar)"""
    from moteur import carte, particules as _pt
    f = os.path.join(DATA, 'common', 'map', 's', code, 'config', code + '_placement.cfg.bin')
    if not os.path.exists(f):
        return []
    noms, srts = [], []
    for n, v in _pt.lire_brut(f):
        if n == 'NAME' and len(v) >= 3:
            noms.append((v[0][1], v[1][1], v[2][1]))
        elif n == 'SRT':
            srts.append([x[1] for x in v])
    out, tex_ar = [], None
    for nom, deb, nb in noms:
        if os.path.exists(os.path.join(DATA, 'common', 'map', 's', code, nom, nom + '.g4pkm')):
            chemin, tx = 'common/map/s/%s/%s/%s.objbin' % (code, nom, nom), tex
        elif os.path.exists(os.path.join(DATA, 'common', 'map', 'ar', nom, nom + '.g4pkm')):
            if tex_ar is None:
                tex_ar = carte._g4tx_index(os.path.join(DATA, 'dx11', 'map', 'ar'))
            chemin, tx = 'common/map/ar/%s/%s.objbin' % (nom, nom), tex_ar
        else:
            continue
        try:
            ob = objet(chemin)
            mats = carte._materiaux_exacts(ob.md, tx, dc, code)
        except Exception as ex:
            print('placé', nom, ex); continue
        base = _appels_objet(ob, chemin, mats, code, 'carte_%s/%s' % (code, nom), places=True)
        for s in srts[deb:deb + nb]:
            M = _matrice_srt(s)
            out += [dict(e, inst=M) for e in base]
    return out


def _appels_objet(ob, chemin, mats, code, cle, places=False):
        """pièces d'un objet du stade ; noms des maillages : « …sdw » = pièce d'ombre seulement (cartes d'ombre) ;
        niveaux de détail « lv1 » / « lv2 » (LodDataParam) : choisis par visible_lod selon la distance, comme le jeu (LU)."""
        from moteur import modele as _mo, anim as _an, particules as _pt
        out = []
        md = ob.md
        noms_m = _mo._noms_fin(md, struct.unpack_from('<H', md, 0x20)[0])
        # SQUELETTE DE L'OBJET (comme le jeu) : chaque maillage est sous l'os de même nom ; sous-arbres « noshadow » (couleur
        # seulement), « shadow » (cartes d'ombre seulement), « lv1 » / « lv2 » (niveaux de détail, LodDataParam de l'objbin)
        anc = {}
        try:
            sk = _an.lire_g4sk(ob.pk)
            par = {o['nom']: (sk[o['parent']]['nom'] if o['parent'] >= 0 else None) for o in sk}
            for nm0 in noms_m:
                a_, x = set(), par.get(nm0)
                while x:
                    a_.add(x); x = par.get(x)
                anc[nm0] = a_
        except Exception:
            pass
        lod_r, clip = None, None
        try:
            for nom_p, v in _pt.lire_brut(os.path.join(DATA, *chemin.split('/'))):
                if nom_p == 'PROP_PARAM' and v and v[0][1] == 'Lv01_Range':
                    lod_r = float(v[1][1])
                elif nom_p == 'PROP_PARAM' and v and v[0][1] == 'm_farClip':
                    clip = float(v[1][1])
        except Exception:
            pass
        base = struct.unpack_from('<H', md, 0x0A)[0] * 4
        off = lambda o: base + struct.unpack_from('<H', md, o)[0] * 4
        t_et, f_et, t_mat = off(0x6C), off(0x6E), off(0x64)
        etats = [dict(zip(md[x:x + 16:2], md[x + 1:x + 16:2])) for x in range(t_et, f_et, 16)] if f_et > t_et else []
        for p in ob.pieces:
            k = p.get('materiau')
            if k is None or k >= len(mats) or not mats[k].get('shader'):
                continue
            jeu = mats[k]
            nm = noms_m[p['index']] if p['index'] < len(noms_m) else ''
            an = anc.get(nm, set())
            lod = 1 if 'lv1' in an else 2 if 'lv2' in an else 0
            v2 = struct.unpack_from('<8H', md, t_mat + 16 * k)[2]
            # (14/11/2026) fiche EXACTE : 1re paire = v2, nombre de paires = octet haut de v5 (moteur 0x140528eb0) ; avant :
            # blocs fixes de 8 paires -> fiche fausse pour 11 153 des 11 596 matériaux du décor
            _v5 = struct.unpack_from('<H', md, t_mat + 16 * k + 10)[0] >> 8; _a = t_et + 2 * v2
            et = {md[_a + 2 * _j]: md[_a + 2 * _j + 1] for _j in range(_v5) if _a + 2 * _j + 2 <= len(md)}
            sh = next((t for t in _sh.table(DATA).values() if t.get('nom') == jeu['shader']), None)
            if not sh:
                continue
            tp = [(t + [0] * 8)[:8] for t in jeu.get('texproj') or []]
            out.append({'chemin': chemin, 'piece': p['index'], 'cle': cle, 'tex': jeu['tex'], 'vs': sh['vs'], 'ps': sh['ps'],
                        'params': (jeu['params'] + [[0, 0, 0, 0]] * 8)[:8], 'diffuse': jeu['diffuse'], 'ambient': jeu['ambient'],
                        'uv': (tp + [[1, 0, 0, 0, 0, 1, 0, 0]] * 6)[:6], 'adressage': [[1, 1]] * 6, 'melange': 'opaque',
                        'ztest': True, 'depthTest': True, 'depthMask': True, 'stade': True,
                        # passe de profondeur du jeu : depth_cutout (alpha < u_ubParam.w -> jeté) pour les « cutout », sinon depth ;
                        # seuil : voir 'seuil' ci-dessous (LU) ; l'ancien « sans clé : 0,5 » (APPROCHÉ) n'est plus utilisé
                        'ombre_seule': 'shadow' in an or 'sdw' in nm, 'sans_ombre': 'noshadow' in an,
                        'lod': lod, 'lod_r': lod_r, 'clip': clip, 'code_stade': code, 'cutout': 'cutout' in sh['ps'],
                        # seuil (LU 0x1405948f8) : clé 1 = test d'alpha (défaut 1), clé 3 (défaut 0) / 255 + 0,1 / 255, sinon -1 ;
                        # faces : clé 0x0E (0 NONE, 1 BACK ; sans clé : état par défaut +0xEBB = 3 BACK) ; avant : clé 1, faux
                        'seuil': (et.get(3, 0) / 255.0 + 0.1 / 255.0) if et.get(1, 1) else -1.0, 'faces': 1 if et.get(0x0E, 1) == 1 else 0})
        return out


def acteurs_appels(stade, notes):
    """acteurs envoyés par la page (modèle, pièces visibles, matrices des os) -> pièces à dessiner : géométrie après peau
    (positions, normales, tangentes du monde) + attributs fixes du .g4mg + matériau du jeu"""
    import acteurs as _A
    out = []
    for A in stade.get('acteurs') or []:
        ac = _A.ACTEURS.get((A.get('quoi'), A.get('code') or ''))
        if not ac:
            notes.append('acteur %s : modèle pas encore chargé' % A.get('acteur')); continue
        for i in A.get('pieces') or []:
            if i >= len(ac.pieces):
                continue
            p = ac.pieces[i]
            if p['noir'] or not p['mat'] or not p['mat'].get('vs'):
                continue
            P, N, T = ac.peau(i, A['mats'])
            col, uvs, idx = ac.attributs(i)
            mat = p['mat']
            st = stade.get('statut')
            if st and (st.get('acteur') == A['acteur'] or (str(st.get('acteur')).startswith('b000001') and A['acteur'].startswith('b000001'))):
                ps2 = mat['ps'] + '_effstatus'                 # aura du ballon : effet de statut du jeu (chr_toon_effstatus…)
                if code_shader(ps2, 'pfxo'):
                    mat = dict(mat, ps=ps2, statut=st)
            out.append({'geo': {'POSITION': P, 'NORMAL': N, 'TANGENT': T, 'COLOR': col, 'TEXCOORD': uvs, 'idx': idx},
                        'mat': mat, 'dossier': p['dossier'], 'cle': '%s/%d' % (A['acteur'], i)})
    return out


def noms_shaders(ob, piece):
    m = ob.materiaux[ob.pieces[piece]['materiau']]
    t = _sh.table(DATA).get(zlib.crc32(m.get('shader_nom', '').encode()))
    return (t['vs'], t['ps']) if t else (m.get('shader_nom'), m.get('shader_ps'))


class Rendu:
    def __init__(self, w, h):
        self.w, self.h = w, h
        self.d = d = D.Appareil()
        # image en HDR (16 bits flottants) : les effets additifs dépassent 1, ce qui alimente le halo du jeu
        self.rt = d.texture(w, h, D.RGBA16F, bind=D.BIND_RTV | D.BIND_SRV)
        self.rtv = d.cible(self.rt)
        self.rt_srv = d.image_shader(self.rt)
        self.fond_tex = d.texture(w, h, D.RGBA8, bind=D.BIND_SRV)
        self.fond_srv = d.image_shader(self.fond_tex)
        self.sortie_tex = d.texture(w, h, D.RGBA8, bind=D.BIND_RTV | D.BIND_SRV)
        self.sortie_rtv = d.cible(self.sortie_tex)
        self.post = None
        self.copie = d.texture(w, h, D.RGBA16F, bind=D.BIND_SRV)            # image de la scène (distorsions)
        self.copie_srv = d.image_shader(self.copie)
        self.ds, self.dsv, self.ds_srv = d.profondeur_lisible(w, h)      # lisible : contours d'écran du jeu (t2 « in_texDep »)
        # profondeur de la scène pour les « particules douces » (t12) : celle de la page si elle est envoyée (profondeur_scene)
        self.prof = self._prof_vide = d.image_shader(d.texture(4, 4, D.R32F, struct.pack('<16f', *[1.0] * 16), 16))
        self.blanc = d.image_shader(d.texture(1, 1, D.RGBA8, b'\xff\xff\xff\xff', 4))
        self.noir = d.image_shader(d.texture(1, 1, D.RGBA8, b'\x00\x00\x00\x00', 4))
        self.raster = d.raster()
        self._tex, self._ech, self._prog, self._geo, self._mel, self._pro = {}, {}, {}, {}, {}, {}
        d.effacer(self.rtv, self.dsv)
        d.sortie(self.rtv, self.dsv, w, h)
        self.notes = []

    _HLSL_SS = """
struct V2 { float4 pos : SV_Position; float4 col : COLOR0; float2 uv : TEXCOORD0; };
V2 vs(uint id : SV_VertexID) { V2 o; float2 p = float2((id << 1) & 2, id & 2); o.pos = float4(p * float2(2, -2) + float2(-1, 1), 0, 1);
  o.col = float4(1, 1, 1, 1); o.uv = p; return o; }"""

    def ombres_stade(self, L, stade, reglages):
        """OMBRES DU SOLEIL COMME LE JEU : 3 cartes de profondeur 1024 x 1024 (RT_ShadowCs0..2) vues des cascades
        (matrices de la page = cascadesOmbre, vérifiées à l'émulateur), dessinées avec depth / depth_cutout du jeu ; puis
        shadow_ss.pfxo du jeu (tableau des cartes en t1, profondeur de la scène en t0) -> t13 « PreShading » à moitié de la
        taille de l'écran (RT_PreShading 0,5), seulement R et A écrits (masque 9 = clé 0x0F de l'état courant +0xEC3 + clé, posé par 0x14133c9a0 : LU le 14/11/2026 ;
        le SSAO écrit ensuite le masque 2 = G, l'occlusion t13.y)."""
        d = self.d; o = stade['ombres']; T = int(o.get('taille', 1024))
        if getattr(self, '_csm', None) is None or self._csm[0] != T:
            self._csm = (T,) + d.profondeur_tableau(T, T, 3)
        _, tex, dsvs, srv = self._csm
        self.csm = {'vp': o['vp'], 'tranches': o['tranches'], 'T': T, 'srv': srv}
        I4 = [1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1]
        for k in range(3):
            D._meth(d.ctx, 53, None, D.c_void_p, D.c_uint, D.c_float, D.c_ubyte)(d.ctx, dsvs[k], 1, 1.0, 0)   # ClearDepthStencilView
            d.sortie(None, dsvs[k], T, T)
            for a in L:
                if a.get('sans_ombre'):
                    continue
                t0 = (a['tex'] or [None])[0]
                self.dessiner(dict(a, mvp=o['vp'][k], modele=a.get('inst') or I4, V=stade['V'], P=stade['P'], melange='profondeur', depthMask=True,
                                   vs='depth_cutout' if a['cutout'] else 'depth', ps='depth_cutout' if a['cutout'] else 'depth',
                                   tex=[None, masque_cutout(a)], ubParam=[1.0, 0, 0, a['seuil']]))
            for g in getattr(self, 'acteurs_cour', None) or []:      # les acteurs portent ombre (depth du jeu)
                self.dessiner_acteur(g, stade, cascade=o['vp'][k], cible=dsvs[k], taille=T)
        d.sortie(self.rtv, self.dsv, self.w, self.h)
        # tampon cb12 (CBUSE_UB_USER_DATA02_IDX), disposition lue dans nie.exe 0x14133c9a0
        V = stade['V']; Vi = inv4(V)
        dirm = list(o['dir'][:3]); dv = [V[0] * dirm[0] + V[4] * dirm[1] + V[8] * dirm[2], V[1] * dirm[0] + V[5] * dirm[1] + V[9] * dirm[2],
                                         V[2] * dirm[0] + V[6] * dirm[1] + V[10] * dirm[2]]
        tr = o['tranches']; near, far2 = tr[0][0], tr[2][1]
        cb = [dv[0], dv[1], dv[2], 0, T, T, 1.0 / T, 1.0 / T] + list(o['biais'][:3]) + [0]
        cb += [near, far2, 1.0 / (far2 - near), 0] + [self.w, self.h, 1.0 / self.w, 1.0 / self.h]
        for k in range(3):
            cb += [tr[k][0], tr[k][1], 0, 0]
        mats = [mul(mul(GL_VERS_D3D, o['vp'][k]), Vi) for k in range(3)]
        for m in mats:
            cb += lignes(m)
        for m in mats:
            cb += lignes(inv4(m))
        b12 = d.tampon(struct.pack('<%df' % len(cb), *cb), D.BIND_CB)
        # passe shadow_ss du jeu
        if getattr(self, '_t13', None) is None:
            tw, th = max(1, int(self.w * 0.5)), max(1, int(self.h * 0.5))
            t = d.texture(tw, th, D.RGBA16F, bind=D.BIND_RTV | D.BIND_SRV)
            self._t13 = (t, d.cible(t), d.image_shader(t), tw, th, d.shader('vs', D.compiler(self._HLSL_SS, 'vs', 'vs_5_0')),
                         d.shader('ps', code_shader('shadow_ss', 'pfxo')), d.melange(D.BLEND_ONE, D.BLEND_ZERO, False, masque=9),
                         d.etat_profondeur(False, False))
        t, rtv, t13s, tw, th, vs, ps, mel, pro = self._t13
        d.vider_srv()
        D._meth(d.ctx, 50, None, D.c_void_p, D.POINTER(D.c_float))(d.ctx, rtv, (D.c_float * 4)(0, 0, 0, 0))   # ClearRenderTargetView
        d.sortie(rtv, None, tw, th)
        prog_ps = reflexion(code_shader('shadow_ss', 'pfxo'))
        a = {'modele': I4, 'mvp': I4, 'V': V, 'P': stade['P'], 'uv': [], 'params': [], 'diffuse': [1, 1, 1, 1], 'ambient': [0, 0, 0, 0]}
        for nom_cb, (slot, octets) in {n: (s, b) for s, (n, b) in self.tampons(a, {'rv': {'cb': {}, 'vars': {}}, 'rp': prog_ps}).items()}.items():
            if nom_cb == 'CBUSE_UB_CAMERA_IDX':
                d.cb('ps', slot, d.tampon(octets, D.BIND_CB))
        d.cb('ps', 12, b12)
        d.shaders(vs, ps)
        d.srv('ps', 0, self.prof); d.ech('ps', 0, self.ech(3, 3))
        d.srv('ps', 1, srv); d.ech('ps', 1, self.ech_point(3, 3))
        d.etats(mel, pro, self.raster)
        d.dessiner_sans_sommets(3)
        d.vider_srv()
        d.sortie(self.rtv, self.dsv, self.w, self.h)
        self.t13_srv = t13s

    # ------------------------------------------------------------------ acteurs (joueurs, esprits, totems) : vrais shaders
    def _mrt(self):
        """images 1..3 écrites par les PS chr_toon* (o1 vitesse + profondeur, o2 masque, o3 normale), relues par la passe
        « edge » du jeu (contours à l'écran : edge.pfxo lit masque, normale, profondeur)"""
        if getattr(self, '_mrt_c', None) is None:
            d = self.d; L = []
            for fmt in (D.RGBA16F, D.RGBA8, D.RGBA8):
                t = d.texture(self.w, self.h, fmt, bind=D.BIND_RTV | D.BIND_SRV)
                L.append((t, d.cible(t), d.image_shader(t)))
            self._mrt_c = L
        return self._mrt_c

    def vider_mrt(self):
        for t, rtv, srv in self._mrt():
            D._meth(self.d.ctx, 50, None, D.c_void_p, D.POINTER(D.c_float))(self.d.ctx, rtv, (D.c_float * 4)(0, 0, 0, 0))

    def tampons_acteur(self, g, el):
        nv = len(g['POSITION']); tamp, pas = [], []
        for n, s_i, f, slot in el:
            if n == 'POSITION':
                b = g['POSITION'].tobytes(); p = 12
            elif n == 'NORMAL':
                b = g['NORMAL'].tobytes(); p = 12
            elif n == 'TANGENT':
                b = g['TANGENT'].tobytes(); p = 16
            elif n == 'COLOR':
                b = g['COLOR']; p = 4
            elif n == 'TEXCOORD':
                b = g['TEXCOORD'][min(s_i, len(g['TEXCOORD']) - 1)].tobytes(); p = 8
            else:
                b = bytes(12 * nv); p = 12
            tamp.append(self.d.tampon(b, D.BIND_VB)); pas.append(p)
        ib = self.d.tampon(g['idx'].tobytes(), D.BIND_IB)
        return tamp, pas, ib, len(g['idx'])

    def dessiner_acteur(self, a, stade, cascade=None, cible=None, taille=None):
        """une pièce d'acteur : shader du matériau du jeu (chr_toon / chr_toon_edit / chr_toon_metal…), ou depth pour les
        cartes d'ombre ; t7 = chrGrd_01 (chr_tex.g4tx), t12 profondeur, t13 PreShading, t15 cascades d'ombre"""
        d = self.d; m = a['mat']
        vs, ps = ('depth', 'depth') if cascade is not None else (m['vs'], m['ps'])
        prog = self.programme(vs, ps)
        if not prog:
            return 'shader introuvable %s/%s' % (vs, ps)
        tamp, pas, ib, n = self.tampons_acteur(a['geo'], prog['el'])
        d.shaders(prog['vs'], prog['ps'], prog['gs'])
        d.sommets(prog['disp'], tamp, pas, ib)
        I4 = [1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1]
        tp = [(t + [0] * 8)[:8] for t in m['texproj']]
        aa = {'modele': I4, 'mvp': cascade if cascade is not None else mul(stade['P'], stade['V']), 'V': stade['V'], 'P': stade['P'],
              'uv': (tp + [[1, 0, 0, 0, 0, 1, 0, 0]] * 6)[:6], 'params': m['params'], 'diffuse': m['diffuse'], 'ambient': m['ambient'],
              'acteur': True, 'statut': m.get('statut') if cascade is None else None}
        for slot, (nom_cb, b) in self.tampons(aa, prog).items():
            buf = d.tampon(b, D.BIND_CB)
            d.cb('vs', slot, buf); d.cb('ps', slot, buf)
        if cascade is None:
            self._lumieres_pl(prog)
            ad = m.get('adressage') or []
            for k in range(6):
                nom = m['tex'][k] if k < len(m['tex']) else None
                v = self.texture(a['dossier'] + '/' + nom) if nom and not nom.startswith('?') else self.blanc
                u, w_ = ad[k] if k < len(ad) else [1, 1]
                for e in ('vs', 'ps'):
                    d.srv(e, k, v); d.ech(e, k, self.ech(u, w_))
            if getattr(self, '_grd', None) is None:            # t7 « in_texGrd » : chrGrd_01 (nie.exe 0x140f9e990)
                import textures_chr
                textures_chr.preparer(DATA, CACHE, images.ecrire_png)
                self._grd = self.texture('systeme/chr_tex/chrGrd_01')
            d.srv('ps', 7, self._grd); d.ech('ps', 7, self.ech(3, 3))          # APPROCHÉ : adressage bloqué au bord
            d.srv('ps', 12, self.prof); d.ech('ps', 12, self.ech(3, 3))
            d.srv('ps', 13, getattr(self, 't13_srv', None) or self.noir); d.ech('ps', 13, self.ech(3, 3))
            c = getattr(self, 'csm', None)
            if c:
                if getattr(self, '_s15', None) is None:
                    self._s15 = d.echantillonneur(4, 4, 4, filtre=0x95, comparaison=5, bord=(1, 1, 1, 1))
                d.srv('ps', 15, c['srv']); d.ech('ps', 15, self._s15)
            d.sortie([self.rtv] + [x[1] for x in self._mrt()], self.dsv, self.w, self.h)
            d.etats(self.melange('opaque'), self.profondeur(True, True), self.raster_mat(m['etat'].get(1)))
        else:
            d.sortie(None, cible, taille, taille)
            d.etats(self.melange('profondeur'), self.profondeur(True, True), self.raster)
        d.dessiner(n)
        if cascade is None:
            d.vider_srv()
            d.sortie(self.rtv, self.dsv, self.w, self.h)
        return '%s/%s' % (vs, ps)

    # ------------------------------------------------------------------ contours des personnages : passes d'écran du jeu
    def contour_jeu(self, stade):
        """CONTOURS COMME LE JEU (nie.exe 0x1413371c0, shaders rangés par 0x1413444d0). Le jeu n'agrandit pas les modèles
        (useExtrutedEdge = 0) : il trace les contours à l'écran en 3 passes plein écran.
        1. Edge (edge.pfxo) -> RT_Temp n° 0 : t0 = masque (o2 des PS chr_toon), t1 = normales (o3), t2 = profondeur ;
           cb0 = (largeur, hauteur, 1/1920, 1/1080), edgeWeight0, (edgeWeight1.xyz, 0) [w = 0 ou 1 selon un réglage : 0 APPROCHÉ]
        2. EdgeTone (edge_tone.pfxo) -> RT_Temp n° 1 : t3 = résultat de Edge, t4 = edgeTone01 (chr_tex.g4tx) ; cb0 = idem
        3. EdgeComposi (edge_composi.pfxo) -> image : t2 = profondeur, t3 = résultat de EdgeTone ;
           cb0 = (edgeColor.rgb, edgeColor.a), (1/l, 1/h, 0,5/l, 0,5/h) ; cb2 = (1/l, 1/h, 0,5/l, 0,5/h),
           (charaEdgeFadeBegin, 1/(fadeEnd − fadeBegin) ou 0, 0,25 × k, 1/k) avec k = 4 × (1 + clamp(h/540 − 1, 0, 1)),
           (CLightData +0x9DC, 0, 0, 0). Sortie : couleur 1 − a, alpha a, et profondeur.
           État LU (14/11/2026) : le moteur copie les valeurs de la fiche d'état telles quelles dans les descriptions D3D11
           (0x1404b7fc0 mélange : clé 0x10 actif, 0x13 source, 0x14 destination, 0x11 opération, 0x15 / 0x16 alpha, 0x12 op. alpha ;
           0x1404b82a0 profondeur : clés 4 test, 5 écriture, 6 fonction). Composite : source 1 = ZERO, destination 3 = SRC_COLOR,
           alpha 1 / 2 = ZERO / ONE (image × couleur sortie) ; profondeur test 1, écriture 1, fonction 8 = ALWAYS.
           Passes Edge / EdgeTone : sans mélange, sans profondeur, masque 0xF."""
        d = self.d; w, h = self.w, self.h
        lum = getattr(self, 'lumiere', None)
        f4 = lambda o: list(struct.unpack_from('<4f', lum, o)) if lum else None
        ec = f4(0x9A0) or [0.3, 0.3, 0.3, 1]; w0 = f4(0x9B0) or [0.3, 0.3, 0, 0.05]; w1 = f4(0x9C0) or [0.3, 1, 1.5, 0]
        fb, fe, _, x9dc = f4(0x9D0) or [0, 0, 1, 0.5]
        if getattr(self, '_ct', None) is None:
            q = struct.pack('<16f', -1, 1, 0, 1,  1, 1, 0, 1,  -1, -1, 0, 1,  1, -1, 0, 1)
            uv = struct.pack('<8f', 0, 0, 1, 0, 0, 1, 1, 1)
            temp = []
            for _ in range(2):                           # RT_Temp n° 0 et 1 (pleine taille)
                t = d.texture(w, h, D.RGBA8, bind=D.BIND_RTV | D.BIND_SRV)
                temp.append((t, d.cible(t), d.image_shader(t)))
            cp_tex, cp_srv = d.copie_r32(w, h)
            self._ct = {'quad': ([d.tampon(q, D.BIND_VB), d.tampon(uv, D.BIND_VB)], [16, 8], d.tampon(struct.pack('<6H', 0, 1, 2, 2, 1, 3), D.BIND_IB)),
                        'temp': temp, 'prof': (cp_tex, cp_srv),
                        'mul': d.melange(D.BLEND_ZERO, D.BLEND_SRC_COLOR, True, D.BLEND_ZERO, D.BLEND_ONE)}
        C = self._ct
        if getattr(self, '_tone', None) is None:
            import textures_chr
            textures_chr.preparer(DATA, CACHE, images.ecrire_png)
            self._tone = self.texture('systeme/chr_tex/edgeTone01')
        d.vider_srv()
        d.sortie(None, None, w, h)
        d.copier(C['prof'][0], self.ds)                  # profondeur de la scène (t2)
        mrt = self._mrt()
        a = {'modele': [1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1], 'mvp': [1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1],
             'V': stade['V'], 'P': stade['P'], 'uv': [], 'params': [], 'diffuse': [1, 1, 1, 1], 'ambient': [0, 0, 0, 0]}
        # le jeu met 1/1920 et 1/1080 = UN pixel de son image 1080p ; notre image est plus petite : 1 pixel de notre image
        # (même aspect que le jeu en 1080p ; avec 1/1920 à 640 px de large, les lectures tombaient dans le même pixel)
        taille = [float(w), float(h), 1.0 / w, 1.0 / h]
        k = 4.0 * (1 + min(max(h / 540.0 - 1, 0.0), 1.0))
        passes = [('edge', C['temp'][0][1], [taille, w0, w1[:3] + [0.0]], None,
                   {0: mrt[1][2], 1: mrt[2][2], 2: C['prof'][1]}, self.melange('opaque'), self.profondeur(False, False)),
                  ('edge_tone', C['temp'][1][1], [taille], None,
                   {3: C['temp'][0][2], 4: self._tone}, self.melange('opaque'), self.profondeur(False, False)),
                  ('edge_composi', self.rtv, [ec, [1 / w, 1 / h, 0.5 / w, 0.5 / h]],
                   [[1 / w, 1 / h, 0.5 / w, 0.5 / h], [fb, (1 / (fe - fb)) if fe - fb > 0 else 0.0, k * 0.25, 1 / k], [x9dc, 0, 0, 0]],
                   {2: C['prof'][1], 3: C['temp'][1][2]}, C['mul'], self.profondeur(True, True, 8))]
        for nom, cible, cb0, cb2, tex, mel, pro in passes:
            prog = self.programme(nom, nom)
            if cible is not self.rtv:
                D._meth(d.ctx, 50, None, D.c_void_p, D.POINTER(D.c_float))(d.ctx, cible, (D.c_float * 4)(0, 0, 0, 0))
                d.sortie(cible, None, w, h)
            else:
                d.sortie(self.rtv, self.dsv, w, h)
            d.shaders(prog['vs'], prog['ps'], None)
            d.sommets(prog['disp'], C['quad'][0], C['quad'][1], C['quad'][2])
            for slot, (nom_cb, b) in self.tampons(a, prog).items():
                d.cb('ps', slot, d.tampon(b, D.BIND_CB))
            d.cb('ps', 0, d.tampon(struct.pack('<%df' % (4 * len(cb0)), *sum(cb0, [])), D.BIND_CB))
            if cb2:
                d.cb('ps', 2, d.tampon(struct.pack('<12f', *sum(cb2, [])), D.BIND_CB))
            for s, v in tex.items():                     # échantillonneurs : bloqués au bord, point (APPROCHÉ)
                d.srv('ps', s, v); d.ech('ps', s, self.ech_point(3, 3))
            d.etats(mel, pro, self.raster)
            d.dessiner(6)
            d.vider_srv()
        d.sortie(self.rtv, self.dsv, w, h)

    def cubemap_jeu(self, code):
        """CUBEMAP DU STADE COMME LE JEU : le bloc BC6H du .g4tx (choisi par config/<code>_env_data : s10g001_03_cb) chargé
        tel quel (HDR, 6 faces, 8 niveaux) en t14 ; cb9 (CBUSE_UB_CUBEMAP_IDX, lu dans map_pbrt1) :
        u_cubemapHeader0.x >> 16 = nombre de cubemaps globales, u_globalCubemaps[i] = (n° dans le tableau, masque, poids, 0).
        Le shader garde une cubemap si (masque & u_ubParam.z) et fait la MOYENNE pondérée de celles gardées.
        (14/11/2026) LU : u_ubParam.z = fiche de maillage +0x168 (0x140594710), mise à 0 par son constructeur (0x140561c20),
        puis copiée du masque de l'objet de carte (CMapLightData +0xD8, 0x140fd3000 ; CRefMapLightData +0x108).
        Le stade n'a qu'UNE cubemap par jeu de textures (env_data) : la moyenne d'un seul terme vaut cette cubemap pour
        tout masque qui la contient -> « tous les bits » donne la même image que le jeu."""
        if getattr(self, '_cube', None) is not None and self._cube[0] == code:
            return self._cube[1]
        srv = None
        try:
            from moteur import carte
            import glob as _g
            from moteur import particules as _pt
            crc = None
            for f in sorted(_g.glob(os.path.join(DATA, 'common', 'map', 's', code, 'config', code + '_env_data_*.cfg.bin'))):
                for nom, v in _pt.lire_brut(f):
                    if nom == 'TEXTURE_SET_INFO_GROUP_DATA' and len(v) >= 3 and v[2][1]:
                        crc = v[2][1] & 0xFFFFFFFF; break
                if crc:
                    break
            tex = carte._g4tx_index(os.path.join(DATA, 'dx11', 'map', 's', code))
            if crc in tex:
                f, k = tex[crc]
                b = open(f, 'rb').read()
                deb = len(b) - struct.unpack_from('<I', b, 0x2C)[0]
                o, size = struct.unpack_from('<II', b, 0x60 + k * 0x30 + 4)
                bloc = b[deb + o:deb + o + size]
                h, w = struct.unpack_from('<II', bloc, 12)
                mips = struct.unpack_from('<I', bloc, 28)[0]
                fmt = struct.unpack_from('<I', bloc, 128)[0]
                srv, lu = self.d.cube_bc(w, h, mips, fmt, bloc[148:])
        except Exception as ex:
            self.notes.append('cubemap : %s' % ex)
        cb = struct.pack('<4I', 1 << 16 if srv else 0, 0, 0, 0) + bytes(16) + struct.pack('<IIff', 0, 0xFFFFFFFF, 1.0, 0) + bytes(4096)
        self._cube = (code, (srv, self.d._tampon(cb, D.BIND_CB)))   # (gardé : hors du cache)
        return self._cube[1]

    def lier_lumieres(self, lumieres):
        """LUMIÈRES PONCTUELLES COMME LE JEU (lu dans les PS chr_toon / map_* : même format partout) :
        cb8 = u_pointLightHeader0 (uint4, inutilisé), u_pointLightHeader1.xy = taille de la grille d'écran,
        puis u_pointLights[i] = (wPos.xyz, attenuation = rayon), (clr.rgb, mask : bit 0 = personnages) ;
        t17 = case de la grille -> (nombre << 16) | début ; t18 (octets) : 4 octets, puis les n° de lumières (255 = vide).
        La grille du jeu découpe l'écran ; ici une seule case qui contient toutes les lumières (même résultat, plus lent)."""
        L = [l for l in (lumieres or []) if l.get('att')][:255]
        cb = struct.pack('<4I', len(L), 0, 0, 0) + struct.pack('<4f', 1.0, 1.0, 0, 0)
        for l in L:
            p, c = (list(l['pos']) + [0, 0, 0])[:3], (list(l['col']) + [0, 0, 0])[:3]
            cb += struct.pack('<4f', p[0], p[1], p[2], float(l['att'])) + struct.pack('<3fI', c[0], c[1], c[2], int(l.get('masque', 0xF7)) & 0xFFFFFFFF)
        cb += bytes(32)
        d = self.d
        self._pl = (d._tampon(cb, D.BIND_CB), d.image_shader(d.tampon(struct.pack('<4I', *[len(L) << 16] * 4), D.BIND_SRV, structure=4)),
                    d.tampon_brut(bytes(4) + bytes(range(len(L))) + bytes([255]) * (4 - len(L) % 4 if len(L) % 4 else 4)))

    def _lumieres_pl(self, prog):
        if getattr(self, '_pl', None) is None:
            self.lier_lumieres([])
        cb, g, idx = self._pl
        if 'CBUSE_UB_POINT_LIGHT_IDX' in prog['rp']['cb']:
            self.d.cb('ps', prog['rp']['cb']['CBUSE_UB_POINT_LIGHT_IDX'], cb)
        self.d.srv('ps', 17, g); self.d.srv('ps', 18, idx)

    def _copie_profondeur(self):
        if getattr(self, '_cprof', None) is None:
            self._cprof = self.d.copie_r32(self.w, self.h)
        self.d.vider_srv()
        self.d.sortie(None, None, self.w, self.h)
        self.d.copier(self._cprof[0], self.ds)
        return self._cprof[1]

    def ssao_jeu(self, stade, reglages):
        """SSAO DU JEU (nie.exe 0x14133d6a0, shader « SSAO » +0x513E) : condition ssaoShieldingScale > 0 et
        ssaoSamplingNum != 0 (et enableSSAO du stade). Écrit le canal G (masque 2) de RT_PreShading (t13.y).
        cb0 (0x50 octets, lu dans le code) :
          u_aoColor = ssaoBlendColor ; u_shielding = (1/ssaoShieldingLenght, cos(angle), 1/(1 − cos), ssaoShieldingScale) ;
          u_noiseParam = (10^ssaoNoiseAccuracy, 10^−acc, 0, 0) (powf) ; u_sampling = (ssaoRadius, ssaoEnableZ, nombre, 0) ;
          u_screenParam = (l, h, 1/l, 1/h) de la cible.
        t0 = profondeur, t2 = normale (o3 des shaders). APPROCHÉ : la normale est celle de cette image (1re passe), le jeu
        la lit dans une cible « SimpleNrm » ; ses n° 0x68 / 0x6C de u_noiseParam ne sont pas écrits (0)."""
        import math
        rg = reglages or {}
        lum = getattr(self, 'lumiere', None)
        if not lum or not (rg.get('enableSSAO') or [0])[0] or getattr(self, '_t13', None) is None:
            return False
        num = int((rg.get('ssaoSamplingNum') or [8])[0])
        col = list(struct.unpack_from('<4f', lum, 0xAB0))
        scale, longueur, angle, acc, rayon, enz = struct.unpack_from('<6f', lum, 0xAC0)
        if not (scale > 0 and num):
            return False
        d = self.d
        t, rtv, t13s, tw, th = self._t13[:5]
        c = math.cos(angle * 0.01745329238474369)
        cb0 = col + [1 / longueur if longueur > 0 else 1.0, c, 1 / (1 - c) if c != 1 else 1.0, scale]
        cb0 += [10 ** acc, 10 ** -acc, 0, 0] + [rayon, enz, float(num), 0] + [float(tw), float(th), 1.0 / tw, 1.0 / th]
        prof = self._copie_profondeur()
        if getattr(self, '_ssao_c', None) is None:
            q = struct.pack('<16f', -1, 1, 0, 1,  1, 1, 0, 1,  -1, -1, 0, 1,  1, -1, 0, 1)
            uv = struct.pack('<8f', 0, 0, 1, 0, 0, 1, 1, 1)
            self._ssao_c = ([d.tampon(q, D.BIND_VB), d.tampon(uv, D.BIND_VB)], [16, 8], d.tampon(struct.pack('<6H', 0, 1, 2, 2, 1, 3), D.BIND_IB),
                            d.melange(D.BLEND_ONE, D.BLEND_ZERO, False, masque=2))
        vb, pas, ib, mel = self._ssao_c
        prog = self.programme('SSAO', 'SSAO')
        d.sortie(rtv, None, tw, th)
        d.shaders(prog['vs'], prog['ps'], None)
        d.sommets(prog['disp'], vb, pas, ib)
        a = {'modele': [1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1], 'mvp': mul(stade['P'], stade['V']), 'V': stade['V'], 'P': stade['P'],
             'uv': [], 'params': [], 'diffuse': [1, 1, 1, 1], 'ambient': [0, 0, 0, 0]}
        for slot, (nom_cb, b) in self.tampons(a, prog).items():
            d.cb('ps', slot, d.tampon(b, D.BIND_CB))
        d.cb('ps', 0, d.tampon(struct.pack('<20f', *cb0), D.BIND_CB))
        d.srv('ps', 0, prof); d.ech('ps', 0, self.ech_point(3, 3))
        d.srv('ps', 2, self._mrt()[2][2]); d.ech('ps', 2, self.ech(3, 3))
        d.etats(mel, self.profondeur(False, False), self.raster)
        d.dessiner(6)
        d.vider_srv()
        d.sortie(self.rtv, self.dsv, self.w, self.h)
        return True

    _HLSL_COPIE = """
Texture2D t0 : register(t0); SamplerState s0 : register(s0);
struct V2 { float4 pos : SV_Position; float4 col : COLOR0; float2 uv : TEXCOORD0; };
float4 ps(V2 i) : SV_Target { return t0.Sample(s0, i.uv); }"""

    def dof_jeu(self, stade, reglages, src_srv=None, cible_rtv=None):
        """PROFONDEUR DE CHAMP DU JEU (nie.exe 0x141331ba0, shaders Gauss +0x5122 et DepthOfField +0x5132) :
        1. copie de l'image à mi-taille (RT_Half ; le jeu : shader 2d_direct, ici une copie linéaire équivalente) ;
        2. dofGaussCnt fois : flou horizontal puis vertical (gauss.vfxo/pfxo), cb6 = u_offs (dofGaussParam.x / taille),
           u_color = 1, u_weight0/1 = exp(−i²/2σ²) (i = 0..7, σ = dofGaussParam.y) / (2 (1 + Σ)) (0x14035c2b0) ;
        3. depth_of_field : l'image floue posée en mélange alpha (fiche : 0x13 = SRC_ALPHA, 0x14 = INV_SRC_ALPHA) ;
           VS cb6 v_offs = dofFocusTexelOffset / taille ; PS cb6 = (n·f, n − f, n − a, 1/(b − a)), (p, 1 − q, 1/p, 1/q),
           (dofFrontStrength, dofBackStrength) ; mise au point automatique : a, b, p, q depuis la distance œil -> point visé
           (scène +0x8CC) et dofFocusNearZ / FarZ / In / Out (multiplicateurs), sinon valeurs directes.
        Multiplicateur de qualité des réglages (+0x298) = 1 : MESURÉ dans le jeu pendant les techniques (14/11/2026)."""
        import math
        rg = reglages or {}
        g = lambda k, dft: (rg.get(k) or dft)
        cnt = min(32, int(g('dofGaussCnt', [1])[0]))
        if cnt <= 0 or not stade.get('P'):
            return False
        nz, fz = float(g('dofFocusNearZ', [0.3])[0]), float(g('dofFocusFarZ', [10])[0])
        fin, fout = float(g('dofFocusIn', [0.7])[0]), float(g('dofFocusOut', [30])[0])
        front, back = float(g('dofFrontStrength', [1])[0]), float(g('dofBackStrength', [1])[0])
        # LU le 14/11/2026 : le jeu multiplie front / back par l'intensité globale de la DOF (objet 0x1422e2f00 +0x298,
        # 0x141331ba0). Elle dépend du jeu de drapeaux : n° 0 (match) = intensityDOF 0,3 ; n° 1 = 1,0. Mesuré dans le jeu
        # en marche PENDANT les cinématiques des techniques : jeu n° 1, intensité 1,0 -> rien à multiplier ici.
        k_dof = 1.0
        front, back = front * k_dof, back * k_dof
        gp = list(g('dofGaussParam', [1.0, 2.0])) + [2.0]
        texoff = float(g('dofFocusTexelOffset', [1])[0])
        auto = int(g('dofUseAutoFocus', [1])[0])
        n, f = proj_params(stade['P'])[:2]
        if not auto:
            b_, a_ = fout + fz, nz - fin
            q = b_ - a_
            p, q = (fin / q, fout / q) if q else (0.0, 0.0)
        else:
            F = float(stade.get('foyer') or 10.0)
            f12 = F * nz; p = F * fin; f13 = f12 * fz; q = p * fout
            a_ = (F - f12) - p; b_ = f13 + F + q
            s_ = q + p + f13 + f12
            p, q = (p / s_, q / s_) if s_ else (0.0, 0.0)
        cb_ps = [n * f, n - f, n - a_, (1 / (b_ - a_)) if b_ != a_ else 0.0,
                 p, 1 - q, (1 / p) if p else 0.0, (1 / q) if q else 0.0, front, back, 0.0, 0.0]
        d = self.d; w, h = self.w, self.h
        hw, hh = max(1, int(w * 0.5)), max(1, int(h * 0.5))
        if getattr(self, '_dof', None) is None:
            q4 = struct.pack('<16f', -1, 1, 0, 1,  1, 1, 0, 1,  -1, -1, 0, 1,  1, -1, 0, 1)
            uv = struct.pack('<8f', 0, 0, 1, 0, 0, 1, 1, 1)
            mi = []
            for _ in range(2):
                t = d.texture(hw, hh, D.RGBA16F, bind=D.BIND_RTV | D.BIND_SRV)
                mi.append((t, d.cible(t), d.image_shader(t)))
            self._dof = {'vb': [d.tampon(q4, D.BIND_VB), d.tampon(uv, D.BIND_VB), d.tampon(bytes([255]) * 16, D.BIND_VB)],
                         'ib': d.tampon(struct.pack('<6H', 0, 1, 2, 2, 1, 3), D.BIND_IB), 'mi': mi,
                         'copie': (d.shader('vs', D.compiler(self._HLSL_SS, 'vs', 'vs_5_0')), d.shader('ps', D.compiler(self._HLSL_COPIE, 'ps', 'ps_5_0'))),
                         'alpha': d.melange(D.BLEND_SRC_ALPHA, D.BLEND_INV_SRC_ALPHA, True, D.BLEND_ONE, D.BLEND_ZERO, masque=7)}
        C = self._dof; A, B = C['mi']
        prof = self._copie_profondeur()

        def quad(prog):
            tamp, pas = [], []
            for nm, s_i, fm, slot in prog['el']:
                k = {'POSITION': 0, 'TEXCOORD': 1, 'COLOR': 2}.get(nm, 2)
                tamp.append(C['vb'][k]); pas.append((16, 8, 4)[k])
            d.sommets(prog['disp'], tamp, pas, C['ib'])
        # 1. copie à mi-taille
        d.vider_srv(); d.sortie(A[1], None, hw, hh)
        d.shaders(C['copie'][0], C['copie'][1], None)
        d.srv('ps', 0, src_srv or self.rt_srv); d.ech('ps', 0, self.ech(3, 3))
        d.etats(self.melange('opaque'), self.profondeur(False, False), self.raster)
        d.dessiner_sans_sommets(3)
        # 2. flou gaussien du jeu
        sig = float(gp[1]) or 2.0
        ws = [1.0] + [math.exp(-0.5 * i * i / (sig * sig)) for i in range(1, 8)]
        tot = 2 * sum(ws)
        ws = [x / tot for x in ws]
        prog = self.programme('gauss', 'gauss')
        for _ in range(cnt):
            for src, dst, offs in ((A, B, [float(gp[0]) / hw, 0, 0, 0]), (B, A, [0, float(gp[0]) / hh, 0, 0])):
                d.vider_srv(); d.sortie(dst[1], None, hw, hh)
                d.shaders(prog['vs'], prog['ps'], None); quad(prog)
                cb = d.tampon(struct.pack('<16f', *(offs + [1, 1, 1, 1] + ws)), D.BIND_CB)
                d.cb('vs', 6, cb); d.cb('ps', 6, cb)
                d.srv('ps', 0, src[2]); d.ech('ps', 0, self.ech(3, 3))
                d.etats(self.melange('opaque'), self.profondeur(False, False), self.raster)
                d.dessiner(6)
        # 3. composite depth_of_field
        d.vider_srv(); d.sortie(cible_rtv or self.rtv, None, w, h)
        prog = self.programme('depth_of_field', 'depth_of_field')
        d.shaders(prog['vs'], prog['ps'], None); quad(prog)
        a = {'modele': [1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1], 'mvp': mul(stade['P'], stade['V']), 'V': stade['V'], 'P': stade['P'],
             'uv': [], 'params': [], 'diffuse': [1, 1, 1, 1], 'ambient': [0, 0, 0, 0]}
        for slot, (nom_cb, b) in self.tampons(a, prog).items():
            if slot != 6:
                d.cb('ps', slot, d.tampon(b, D.BIND_CB))
        d.cb('vs', 6, d.tampon(struct.pack('<4f', texoff / w, texoff / h, 0, 0), D.BIND_CB))
        d.cb('ps', 6, d.tampon(struct.pack('<12f', *cb_ps), D.BIND_CB))
        d.srv('ps', 0, A[2]); d.ech('ps', 0, self.ech(3, 3))
        d.srv('ps', 1, prof); d.ech('ps', 1, self.ech_point(3, 3))
        d.etats(C['alpha'], self.profondeur(False, False), self.raster)
        d.dessiner(6)
        d.vider_srv(); d.sortie(self.rtv, self.dsv, w, h)
        return True

    def soleil_jeu(self, stade, reglages, cible_rtv):
        """RAYONS DE SOLEIL DU JEU (LU le 14/11/2026 : nie.exe 0x1413311d0 ; valeurs préparées par 0x1413486d0) :
        - soleil à l'écran : point = œil + lightDir × far × 0,9, projeté ; uv = (0,5 x + 0,5 ; 0,5 − 0,5 y) ;
        - fondu f = clamp((dot(regard, lightDir) − 0,1) × 4, 0, 1) × sunShaftColor.w ; couleur = sunShaftColor.rgb × f ;
        - 1. sun_shaft (RT_Quarter n° 0) : ciel seulement (profondeur ≥ 1) / (1 + |(uv − soleil) × sunShaftAtten × (tan × l/h, tan)|) ;
        - 2. RadialBlur (radial_blur) sunShaftBlurCount fois en alternant 2 images ; u_param = (soleil, pas), pas =
          sunShaftBlurScale × 0,1 × (tan × l/h, tan) ; u_color = 1 ;
        - 3. 2d_direct / 2d_multi5 (5 lectures × couleur × 0,2) AJOUTÉ (ONE / ONE) sur l'image tonemappée.
        Réglage global d'intensité (+0x29C) = 1 (lu dans le jeu en marche). Conditions : enableSunShaft, f > 0."""
        import math
        rg = reglages or {}
        lum = getattr(self, 'lumiere', None)
        if not lum or not stade.get('P') or not stade.get('V'):
            return False
        if not (rg.get('enableSunShaft') or [1])[0]:
            return False
        col = list(rg.get('sunShaftColor') or struct.unpack_from('<4f', lum, 0x620))
        col = (col + [0, 0, 0, 0])[:4]
        att = float((rg.get('sunShaftAtten') or [struct.unpack_from('<f', lum, 0x630)[0]])[0])
        echelle = float((rg.get('sunShaftBlurScale') or [struct.unpack_from('<f', lum, 0x634)[0]])[0])
        nb = int(round(float((rg.get('sunShaftBlurCount') or [0])[0]))) if rg.get('sunShaftBlurCount') else struct.unpack_from('<i', lum, 0x638)[0]
        nb = max(0, min(nb, 16))
        L = list(rg.get('lightDir') or struct.unpack_from('<3f', lum, 0x160))[:3]
        n_ = math.sqrt(sum(x * x for x in L)) or 1.0
        L = [x / n_ for x in L]
        V, P = stade['V'], stade['P']
        oeil = [-(V[i * 4] * V[12] + V[i * 4 + 1] * V[13] + V[i * 4 + 2] * V[14]) for i in range(3)]
        regard = [-V[2], -V[6], -V[10]]                  # WebGL : la caméra regarde vers −z (cible − œil, normalisé)
        f = min(max((sum(a * b for a, b in zip(regard, L)) - 0.1) * 4.0, 0.0), 1.0) * col[3]
        if f <= 0:
            return False
        near, far, tana, tanv = proj_params(P)
        pt = [oeil[i] + L[i] * far * 0.9 for i in range(3)] + [1.0]
        VP = mul(P, V)
        c = [sum(VP[k * 4 + r] * pt[k] for k in range(4)) for r in range(4)]
        wcl = c[3] if c[3] != 0 else 1e-7
        sx, sy = (c[0] / wcl + 1.0) * 0.5, 0.5 - (c[1] / wcl) * 0.5
        d = self.d; w, h = self.w, self.h
        qw, qh = max(1, int(w * 0.25)), max(1, int(h * 0.25))   # groupe 7 = RT_Quarter (comme le halo)
        if getattr(self, '_sol', None) is None:
            q4 = struct.pack('<16f', -1, 1, 0, 1,  1, 1, 0, 1,  -1, -1, 0, 1,  1, -1, 0, 1)
            uv = struct.pack('<8f', 0, 0, 1, 0, 0, 1, 1, 1)
            im = []
            for _ in range(2):
                t = d.texture(qw, qh, D.RGBA16F, bind=D.BIND_RTV | D.BIND_SRV)
                im.append((t, d.cible(t), d.image_shader(t)))
            self._sol = {'q': d.tampon(q4, D.BIND_VB), 'uv': d.tampon(uv, D.BIND_VB), 'ib': d.tampon(struct.pack('<6H', 0, 1, 2, 2, 1, 3), D.BIND_IB),
                         'im': im, 'add': d.melange(D.BLEND_ONE, D.BLEND_ONE, True, D.BLEND_ONE, D.BLEND_ONE, masque=7)}
        S = self._sol
        couleur = [col[0] * f, col[1] * f, col[2] * f, f]

        def quad(prog, coul=None):
            tamp, pas = [], []
            for nm, s_i, fm, slot in prog['el']:
                if nm == 'POSITION':
                    tamp.append(S['q']); pas.append(16)
                elif nm == 'TEXCOORD':
                    tamp.append(S['uv']); pas.append(8)
                elif nm == 'COLOR':
                    tamp.append(d.tampon(struct.pack('<16f', *(coul or [1, 1, 1, 1]) * 4), D.BIND_VB)); pas.append(16)
                else:
                    tamp.append(d.tampon(b'\0' * 64, D.BIND_VB)); pas.append(16)
            d.sommets(prog['disp'], tamp, pas, S['ib'])
        prof = self._copie_profondeur()
        cam = d.tampon(struct.pack('<16f', *([0.0] * 12), near, far, tana, tanv), D.BIND_CB)
        # 1. masque du soleil
        A, B = S['im']
        prog = self.programme('sun_shaft', 'sun_shaft')
        d.vider_srv(); d.sortie(A[1], None, qw, qh)
        d.shaders(prog['vs'], prog['ps'], None); quad(prog)
        d.cb('vs', 0, d.tampon(struct.pack('<4f', sx, sy, att, 0.0), D.BIND_CB)); d.cb('vs', 5, cam)
        d.srv('ps', 0, prof); d.ech('ps', 0, self.ech(3, 3))
        d.etats(self.melange('opaque'), self.profondeur(False, False), self.raster)
        d.dessiner(6)
        # 2. flou radial
        prog = self.programme('radial_blur', 'radial_blur')
        src, dst = A, B
        for _ in range(nb):
            d.vider_srv(); d.sortie(dst[1], None, qw, qh)
            d.shaders(prog['vs'], prog['ps'], None); quad(prog)
            d.cb('ps', 0, d.tampon(struct.pack('<8f', sx, sy, echelle * 0.1 * tana, echelle * 0.1 * tanv, 1, 1, 1, 1), D.BIND_CB))
            d.srv('ps', 0, src[2]); d.ech('ps', 0, self.ech(3, 3))
            d.etats(self.melange('opaque'), self.profondeur(False, False), self.raster)
            d.dessiner(6)
            src, dst = dst, src
        # 3. ajout sur l'image (2d_multi5 : 5 lectures x couleur x 0,2)
        prog = self.programme('2d_direct', '2d_multi5', True)
        d.vider_srv(); d.sortie(cible_rtv, None, w, h)
        d.shaders(prog['vs'], prog['ps'], None); quad(prog, couleur)
        d.cb('ps', 0, d.tampon(struct.pack('<4f', 1.0 / qw, 1.0 / qh, 0, 0), D.BIND_CB))
        d.srv('ps', 0, src[2]); d.ech('ps', 0, self.ech(3, 3))
        d.etats(S['add'], self.profondeur(False, False), self.raster)
        d.dessiner(6)
        d.vider_srv(); d.sortie(self.rtv, self.dsv, w, h)
        self.notes.append('soleil (%.2f, %.2f) f=%.2f' % (sx, sy, f))
        return True

    def pieds_jeu(self, stade, reglages):
        """OMBRE SOUS LES PIEDS DU JEU (FootShadowAO, nie.exe 0x14133d6a0 / instances 0x141341c80) : un ellipsoïde par os,
        shader foot_shadow_ao du jeu (VS : cb0[6i..6i+2] = matrice monde de l'instance ; PS : point du sol remonté depuis la
        profondeur, cb0[6i+3..6i+5] = matrice inverse, AO = (1 − min(|p|², 1)) × u_shodowClr), ajouté au canal G de
        RT_PreShading (t13.y) ; u_shodowClr = footShadowRate (CLightData +0xADC, scène +0xC6C) × 4 composantes.
        LU (14/11/2026) : ellipsoïdes CRenderCollision (render_collision.cfg.bin, profil de l'objbin : os l/r_foot_1_0,
        décalage, largeur / profondeur / hauteur), matrices calculées par la page ; vérifié dans la mémoire du jeu.
        Mélange : ajout (clé 0x13 = 2 = ONE ; valeurs D3D11 brutes)."""
        pieds = stade.get('pieds') or []
        lum = getattr(self, 'lumiere', None)
        rate = struct.unpack_from('<f', lum, 0xADC)[0] if lum else 0.0
        rg = reglages or {}
        if rg.get('footShadowRate'):
            rate = float(rg['footShadowRate'][0])
        if not pieds or rate <= 0 or getattr(self, '_t13', None) is None:
            return False
        d = self.d
        t, rtv, t13s, tw, th = self._t13[:5]
        if getattr(self, '_pied', None) is None:
            v = [(x, y, z) for x in (-1, 1) for y in (-1, 1) for z in (-1, 1)]
            idx = [0, 1, 2, 2, 1, 3, 4, 6, 5, 5, 6, 7, 0, 4, 1, 1, 4, 5, 2, 3, 6, 6, 3, 7, 0, 2, 4, 4, 2, 6, 1, 5, 3, 3, 5, 7]
            self._pied = (d.tampon(struct.pack('<24f', *sum(v, ())), D.BIND_VB), d.tampon(struct.pack('<36H', *idx), D.BIND_IB),
                          d.melange(D.BLEND_ONE, D.BLEND_ONE, True, D.BLEND_ONE, D.BLEND_ONE, masque=2))
        vb, ib, mel = self._pied
        prof = self._copie_profondeur()
        prog = self.programme('foot_shadow_ao', 'foot_shadow_ao')
        d.sortie(rtv, None, tw, th)
        d.shaders(prog['vs'], prog['ps'], None)
        tamp, pas = [], []
        for nm, s_i, fm, slot in prog['el']:
            if nm == 'POSITION':
                tamp.append(vb); pas.append(12)
        d.sommets(prog['disp'], tamp, pas, ib)
        a = {'modele': [1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1], 'mvp': mul(stade['P'], stade['V']), 'V': stade['V'], 'P': stade['P'],
             'uv': [], 'params': [], 'diffuse': [1, 1, 1, 1], 'ambient': [0, 0, 0, 0]}
        for slot, (nom_cb, b) in self.tampons(a, prog).items():
            if nom_cb == 'CBUSE_UB_CAMERA_IDX':
                buf = d.tampon(b, D.BIND_CB); d.cb('vs', slot, buf); d.cb('ps', slot, buf)
        d.cb('ps', 1, d.tampon(struct.pack('<4f', rate, rate, rate, rate), D.BIND_CB))
        d.srv('ps', 0, prof); d.ech('ps', 0, self.ech_point(3, 3))
        d.etats(mel, self.profondeur(False, False), self.raster)
        import numpy as _np
        r = 0.306
        for p in pieds:
            if len(p) == 12:                              # ellipsoïde CRenderCollision (3 lignes monde, LU le 14/11/2026)
                A4 = _np.vstack([_np.array(p, dtype=_np.float64).reshape(3, 4), [0, 0, 0, 1]])
                try:
                    Ai = _np.linalg.inv(A4)
                except _np.linalg.LinAlgError:
                    continue
                M = [float(x) for x in A4[:3].ravel()]; Mi = [float(x) for x in Ai[:3].ravel()]
            else:                                         # ancien format : position seule, sphère 0,306 (DÉDUIT)
                M = [r, 0, 0, p[0], 0, r, 0, p[1], 0, 0, r, p[2]]
                Mi = [1 / r, 0, 0, -p[0] / r, 0, 1 / r, 0, -p[1] / r, 0, 0, 1 / r, -p[2] / r]
            cb = d.tampon(struct.pack('<24f', *(M + Mi)), D.BIND_CB)
            d.cb('vs', 0, cb); d.cb('ps', 0, cb)
            d.dessiner(36)
        d.vider_srv()
        d.sortie(self.rtv, self.dsv, self.w, self.h)
        return True

    def ciel_jeu(self, stade, reglages):
        """CIEL DU JEU : le stade a useFogSky = 1 (s10g001_g1.objbin) -> passe plein écran Map_FogSky (map_fogsky.vfxo/pfxo) :
        le VS remonte chaque pixel au plan lointain (u_mtxPW), le PS calcule la couleur de l'atmosphère (brouillard
        Rayleigh / Mie de cb5, soleil cb6) à la distance cb0.z = fogSkyRadius. Dessinée au plan lointain (z = 1) : seulement là
        où rien n'est dessiné. État LU (0x141338920, 14/11/2026) : profondeur testée sans écriture, faces arrière retirées (clé 0x1B = 3),
        mélange et masque laissés par défaut (sans mélange, RVBA). Le lecteur natif suit ; ce prototype écrit encore RVB seulement."""
        rg = reglages or {}
        if not (rg.get('useFogSky') or [1])[0]:
            return
        d = self.d; w, h = self.w, self.h
        if getattr(self, '_ciel', None) is None:
            q = struct.pack('<16f', -1, 1, 0, 1,  1, 1, 0, 1,  -1, -1, 0, 1,  1, -1, 0, 1)
            uv = struct.pack('<8f', 0, 0, 1, 0, 0, 1, 1, 1)
            self._ciel = ([d.tampon(q, D.BIND_VB), d.tampon(uv, D.BIND_VB), d.tampon(bytes([255]) * 16, D.BIND_VB)],
                          d.tampon(struct.pack('<6H', 0, 1, 2, 2, 1, 3), D.BIND_IB), d.melange(D.BLEND_ONE, D.BLEND_ZERO, False, masque=7))
        vb, ib, mel = self._ciel
        prog = self.programme('map_fogsky', 'map_fogsky')
        tamp, pas = [], []
        for n, s_i, f, slot in prog['el']:
            k = {'POSITION': 0, 'TEXCOORD': 1, 'COLOR': 2}.get(n, 2)
            tamp.append(vb[k]); pas.append((16, 8, 4)[k])
        d.sortie(self.rtv, self.dsv, w, h)
        d.shaders(prog['vs'], prog['ps'], None)
        d.sommets(prog['disp'], tamp, pas, ib)
        a = {'modele': [1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1], 'mvp': mul(stade['P'], stade['V']), 'V': stade['V'], 'P': stade['P'],
             'uv': [], 'params': [], 'diffuse': [1, 1, 1, 1], 'ambient': [0, 0, 0, 0]}
        for slot, (nom_cb, b) in self.tampons(a, prog).items():
            buf = d.tampon(b, D.BIND_CB); d.cb('vs', slot, buf); d.cb('ps', slot, buf)
        r = float((rg.get('fogSkyRadius') or [4000])[0])
        b0 = d.tampon(struct.pack('<4f', 0, 0, r, 0), D.BIND_CB); d.cb('vs', 0, b0); d.cb('ps', 0, b0)
        d.srv('ps', 12, self.prof); d.ech('ps', 12, self.ech_point(3, 3))
        d.srv('ps', 13, getattr(self, 't13_srv', None) or self.noir); d.ech('ps', 13, self.ech(3, 3))
        d.etats(mel, self.profondeur(True, False), self.raster)
        d.dessiner(6)
        d.vider_srv()

    SENS_FACES = int(os.environ.get('ATELIER_SENS_FACES', '1'))   # vérifié : 0 montre l'intérieur des modèles

    def raster_mat(self, cle1):
        """fiche d'état du matériau, clé 0x01 (état[0xEC3 + clé], nie.exe 0x1404a4b28) : 0 = double face, 1 = faces
        arrière éliminées (0 sur tous les effets, 1 sur tous les esprits ; stade : feuillages à 0)"""
        if not cle1:
            return self.raster
        k = ('r', cle1)
        if k not in self._pro:
            self._pro[k] = self.d.raster(3, self.SENS_FACES)
        return self._pro[k]

    def ech_point(self, u, v):
        k = ('point', u, v)
        if k not in self._ech:
            self._ech[k] = self.d.echantillonneur(u, v, 3, filtre=0)
        return self._ech[k]

    def ombre_effets(self, ombre):
        """carte d'ombre de la cascade 0 calculée par la page (WebGL : profondeur rangée en RVB, lue par
        dot(rvb, (1, 1/255, 1/65025)) = profondeur de 0 à 1, comme Direct3D) -> t15 ; lignes retournées (en Direct3D,
        v = 0,5 − 0,5 y : la ligne du haut est y = +1)"""
        self.ombre_vp = None
        if not ombre or not ombre.get('px'):
            return
        import base64
        T = int(ombre['taille']); px = base64.b64decode(ombre['px'])
        if len(px) != T * T * 4:
            return
        import numpy as _np                              # (même calcul qu'avant, en numpy : 0,4 s -> quelques ms)
        a = _np.frombuffer(px, _np.uint8).reshape(T, T, 4)[::-1].astype(_np.float64)
        f = (a[..., 0] / 255 + a[..., 1] / 65025 + a[..., 2] / 16581375).astype(_np.float32)
        ancien = getattr(self, '_t15', None)
        tex = self.d.texture(T, T, D.R32F, f.tobytes(), T * 4)
        self._t15 = (T, self.d.image_shader(tex))
        if ancien and ancien[1]:                         # (avant : une texture perdue à chaque image)
            D.liberer(ancien[1]); D.liberer(getattr(self, '_t15_tex', None))
        self._t15_tex = tex
        self.ombre_vp = ombre['vp']

    def _ombre_t15(self):
        """t15 + s15 comme le jeu (LU : clé de la case 15 dans 0x14132c360 / 0x14133c9a0, créée par 0x1404a7560) :
        comparaison GREATER (5), adressage BORDER (4) à 1,0, filtre linéaire avec comparaison (0x95 : octets de filtre
        réglés à 1 par la passe d'ombre d'écran et gardés)"""
        t = getattr(self, '_t15', None)
        if not t or not t[1] or not getattr(self, 'ombre_vp', None):
            return
        if getattr(self, '_s15', None) is None:
            self._s15 = self.d.echantillonneur(4, 4, 4, filtre=0x95, comparaison=5, bord=(1, 1, 1, 1))
        for e in ('vs', 'ps'):
            self.d.srv(e, 15, t[1]); self.d.ech(e, 15, self._s15)

    def texture(self, cle):
        if cle in self._tex:
            return self._tex[cle]
        if cle.startswith('alpha:'):                    # alpha de la texture de couleur, dans les 4 canaux (lu en .x par depth_cutout)
            f = os.path.join(CACHE, *cle[6:].split('/')) + '.png'
            if not os.path.exists(f):
                self._tex[cle] = self.blanc
                return self.blanc
            w, h, rows = images.lire_png(f)
            px = bytearray()
            for r in rows:
                a = bytes(r[3:w * 4:4]); q = bytearray(4 * w); q[0::4] = a; q[1::4] = a; q[2::4] = a; q[3::4] = a; px += q
            t = self.d.texture(w, h, D.RGBA8, bytes(px), w * 4, bind=D.BIND_SRV | D.BIND_RTV, mips=0, misc=D.MISC_GENERATE_MIPS)
            v = self.d.image_shader(t); self.d.mips(v)
            self._tex[cle] = v
            return v
        f = os.path.join(CACHE, *cle.split('/')) + '.png'
        if not os.path.exists(f):
            self._tex[cle] = self.blanc
            return self.blanc
        w, h, rows = images.lire_png(f)
        d = self.d
        t = d.texture(w, h, D.RGBA8, b''.join(bytes(r[:w * 4]) for r in rows), w * 4, bind=D.BIND_SRV | D.BIND_RTV, mips=0,
                      misc=D.MISC_GENERATE_MIPS)
        v = d.image_shader(t)
        d.mips(v)
        self._tex[cle] = v
        return v

    def ech(self, u, v):
        k = (u, v)
        if k not in self._ech:
            self._ech[k] = self.d.echantillonneur(u, v, 1)
        return self._ech[k]

    def programme(self, vs, ps, couleur_f=False):
        k = (vs, ps, couleur_f)
        if k not in self._prog:
            cv, cp = code_shader(vs, 'vfxo'), code_shader(ps, 'pfxo')
            if not cv or not cp:
                self._prog[k] = None
            else:
                rv, rp = reflexion(cv), reflexion(cp)
                fmt = {'POSITION': D.RGB32F, 'COLOR': D.RGBA32F if couleur_f else D.RGBA8, 'TEXCOORD': D.RG32F,
                       'TANGENT': D.RGBA32F,   # particules : couleur en flottants ; tangente x y z + w (sens du repère)
                       'BLENDWEIGHT': D.RGBA32F, 'BLENDINDICES': 3}   # peau (shaders « _vb ») : 3 = R32G32B32A32_UINT
                el = [(n, i, fmt.get(n, D.RGB32F), s) for s, (n, i, masque, reg) in enumerate(rv['entrees']) if not n.startswith('SV_')]
                cg = code_shader(ps, 'gfxo') or code_shader(vs, 'gfxo')      # FakeParticle : geometry shader du jeu
                rg = reflexion(cg) if cg else None
                self._prog[k] = {'vs': self.d.shader('vs', cv), 'ps': self.d.shader('ps', cp), 'rv': rv, 'rp': rp,
                                 'gs': self.d.shader('gs', cg) if cg else None, 'rg': rg,
                                 'disp': self.d.disposition(el, cv), 'el': el}
        return self._prog[k]

    def geometrie(self, chemin, i, el, teinte=None):
        k = (chemin, i, tuple(el), tuple(teinte) if teinte else None)
        if k in self._geo:
            return self._geo[k]
        ob = objet(chemin)
        pos, col, idx, uv = ob.geometrie(i)
        nv = len(pos) // 3
        sup = ob.uv_sup(i)
        tamp, pas = [], []
        for n, s_i, f, slot in el:
            if n == 'POSITION':
                b = struct.pack('<%df' % len(pos), *pos); p = 12
            elif n == 'COLOR':
                c = col if s_i == 0 else ob.couleur1(i)
                b = bytes(c) if c else b'\xff' * (4 * nv); p = 4
                if teinte and s_i == 0:                      # (14/11/2026) teinte des sommets choisie dans l'Atelier
                    b = couleurs_teintees(b, teinte)
            elif n == 'TEXCOORD':
                u = uv if s_i == 0 else (sup[s_i - 1] if s_i - 1 < len(sup) else uv)
                b = struct.pack('<%df' % len(u), *u); p = 8
            elif n == 'TANGENT':
                v = tangentes4(ob, i, nv)
                b = struct.pack('<%df' % len(v), *v); p = 16
            elif n == 'NORMAL':
                v = ob.normales(i, 'nor') or [0, 0, 1] * nv
                b = struct.pack('<%df' % len(v), *v); p = 12
            elif n in ('BLENDWEIGHT', 'BLENDINDICES'):      # maillage à peau (g4.ObjetEffet.peau) : 4 poids / 4 n° d'os
                pe = ob.peau(i) if hasattr(ob, 'peau') else None
                if n == 'BLENDWEIGHT':
                    b = struct.pack('<%df' % (4 * nv), *pe[0]) if pe else struct.pack('<4f', 1, 0, 0, 0) * nv
                else:
                    b = struct.pack('<%dI' % (4 * nv), *pe[1]) if pe else b'\0' * (16 * nv)
                p = 16
            else:
                b = b'\0' * (12 * nv); p = 12
            tamp.append(self.d.tampon(b, D.BIND_VB)); pas.append(p)
        ib = self.d.tampon(struct.pack('<%dH' % len(idx), *idx), D.BIND_IB)
        self._geo[k] = (tamp, pas, ib, len(idx))
        return self._geo[k]

    def melange(self, genre):
        if genre not in self._mel:
            d = self.d
            if genre == 'add':
                self._mel[genre] = d.melange(D.BLEND_SRC_ALPHA, D.BLEND_ONE, True, D.BLEND_ZERO, D.BLEND_ONE)
            elif genre == 'sous':          # soustractif (MATERIAL_INFO[9] = 4) : destination - source x alpha
                self._mel[genre] = d.melange(D.BLEND_SRC_ALPHA, D.BLEND_ONE, True, D.BLEND_ZERO, D.BLEND_ONE, op=3)
            elif genre == 'opaque':
                self._mel[genre] = d.melange(D.BLEND_ONE, D.BLEND_ZERO, False)
            elif genre == 'profondeur':    # passe de profondeur : couleur non écrite
                self._mel[genre] = d.melange(D.BLEND_ONE, D.BLEND_ZERO, False, masque=0)
            else:
                self._mel[genre] = d.melange(D.BLEND_SRC_ALPHA, D.BLEND_INV_SRC_ALPHA, True, D.BLEND_ONE, D.BLEND_INV_SRC_ALPHA)
        return self._mel[genre]

    def profondeur(self, test, ecrire, fonction=4):
        """état de profondeur ; fonction = valeur D3D11 brute (4 LESS_EQUAL, 8 ALWAYS). Dans le jeu, les clés 4 / 5 / 6 de la
        fiche d'état (état[0xEC3 + clé]) vont telles quelles dans D3D11_DEPTH_STENCIL_DESC (0x1404b82a0 : test, écriture, fonction)"""
        k = (bool(test), bool(ecrire), int(fonction))
        if k not in self._pro:
            self._pro[k] = self.d.etat_profondeur(*k)
        return self._pro[k]

    def tampons(self, a, prog):
        """valeurs des tampons de constantes, d'après les noms des variables des shaders du jeu"""
        modele = a['modele']
        img = getattr(self, 'lumiere', None)
        Vw, Pj = a['V'] or [1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1], a['P']
        # VITESSE (14/11/2026) : tout ce qui ne dépend que de la caméra (V, P, mvp) est calculé une fois par image
        kc = (tuple(Vw), tuple(Pj) if Pj else None, tuple(a['mvp']))
        cam = self._cam_cache.get(kc) if hasattr(self, '_cam_cache') else None
        if cam is None:
            mvp = mul(GL_VERS_D3D, a['mvp'])
            vp = mul(GL_VERS_D3D, Pj) if Pj and len(Pj) == 16 else None
            ivw, imvp = lignes(inv4(Vw)), lignes(inv4(mvp))
            ivp = lignes(inv4(vp)) if vp else [0] * 16
            cam = {'_mvp': mvp,
                   'u_mtxVP': lignes(vp) if vp else lignes(GL_VERS_D3D), 'u_eyeMtxVP': lignes(vp) if vp else lignes(GL_VERS_D3D),
                   'u_mtxWV': lignes(Vw), 'u_mtxWP': lignes(mvp), 'u_eyeMtxWV': lignes(Vw), 'u_eyeMtxWP': lignes(mvp),
                   'u_eyeNearFarInvAspect': proj_params(Pj), 'u_eyeMtxPV': ivp,
                   'u_eyePos': [-(Vw[i * 4] * Vw[12] + Vw[i * 4 + 1] * Vw[13] + Vw[i * 4 + 2] * Vw[14]) for i in range(3)],
                   'u_eyeDir': [-Vw[2], -Vw[6], -Vw[10], 0], 'u_eyeUpDir': [Vw[1], Vw[5], Vw[9], 0],
                   # (14/11/2026) LU nie.exe 0x141348c27 : diag(0,5 ; -0,5 ; 0,5) x rotation de la vue, 4e colonne 0,5 (reflet du métal)
                   'u_mtxEyeSphere': [0.5 * Vw[0], 0.5 * Vw[4], 0.5 * Vw[8], 0.5, -0.5 * Vw[1], -0.5 * Vw[5], -0.5 * Vw[9], 0.5,
                                      0.5 * Vw[2], 0.5 * Vw[6], 0.5 * Vw[10], 0.5],
                   'u_mtxVW': ivw, 'u_eyeMtxVW': ivw, 'u_mtxPV': ivp, 'u_mtxPW': imvp, 'u_eyeMtxPW': imvp,
                   'u_mtxWVOld': lignes(Vw), 'u_mtxVPOld': lignes(vp) if vp else [0] * 16, 'u_mtxWPOld': lignes(mvp)}
            if not hasattr(self, '_cam_cache') or len(self._cam_cache) > 64:
                self._cam_cache = {}
            self._cam_cache[kc] = cam
        mvp = cam['_mvp']
        lw, lv = lignes(modele), lignes(mul(Vw, modele))
        val = dict(cam)
        val.update({
            'u_mtxLW': lw, 'u_mtxLV': lv, 'u_mtxLP': lignes(mul(mvp, modele)),
            'u_mtxLWOld': lw, 'u_mtxLVOld': lv,
            # u_ubParam.x = 1 : le jeu met 1,0 à +0 du tampon matériau (0x14059ff50, paquet de dessin) ; les shaders du stade
            # multiplient position.x et tangente par cette valeur (miroir). LU (0x140594710) pour les modèles : u_ubParam =
            # (1, 0, champ +0x168 de l'entrée de dessin de l'objet (masque des cubemaps, source non trouvée), seuil d'alpha)
            'u_ubParam': a.get('ubParam') or [1.0, 0, 0, 0],
            'u_diffuse': a['diffuse'], 'u_ambient': a['ambient'], 'u_speculer': [0, 0, 0, 0],
            # (cache caméra : u_eyeNearFarInvAspect = (near, far, tan(fov/2) x largeur/hauteur, tan(fov/2)) comme nie.exe
            # 0x1413486d0 ; u_eyePos = −Rᵀ t de la vue ; matrices « Old » = image d'avant, pas de mouvement ici)
            # APPROCHÉ : u_attachScale (cb11[0].xyz, diviseur de la lumière 2 de SmokePar1). Pour les particules du processeur, le jeu
            # ne lie pas cb11 (0x1405a01d0 ne sert qu'aux particules sur carte graphique) : la valeur reste celle d'un dessin
            # précédent, à lire par RenderDoc. 0 donnerait NaN (fumée noire) ; 1 = comme la traduction WebGL
            'u_attachScale': [1.0, 1.0, 1.0],
            'u_grdValue': [a['params'][2][3] if a.get('colonne') is not None else 0, 0, 0, 0],
            # ↑ u_grdValue.x = U du dégradé de Effect_BallAura1 (cb11[5].x). Colonne = couleur de tir (LU 0x140f12490, octet +0x75F).
            # LU (14/11/2026) : le moteur range la couleur de tir sous la clé 0x71EB98CA et lit la valeur dans SkillConfig
            # (0x141605810, objet +0x950 du gestionnaire = skill_config_5.00.07.00.cfg.bin, liste de 10 enregistrements de 0x18
            # octets, flottant à +4) : n° 0-9 -> ((n mod 5) + 0,5) / 128. Particules : cb11 non lié par le jeu (valeur d'exécution)
        })
        val.pop('_mvp', None)
        if a.get('acteur'):
            # couleurs « Edit » du joueur (cb10 / cb11 : peau, cheveux, couleurs secondaires) : valeurs NEUTRES (APPROCHÉ) ->
            # le shader garde les couleurs de la texture et u_shaderParam0 / 1 du matériau (cb11.w = 0)
            st = a.get('statut')
            if st:                                       # effet de statut (courbes de effect_status_define) -> cb7
                val.update({'u_charaStatusColor': list(st.get('col') or [1, 1, 1])[:3] + [1.0],
                            # .w = intensité du contour : LU (0x140f0aa40) = 5e valeur des clés × poids du fondu ('rim_w')
                            'u_charaStatusRimColor': list(st.get('rim') or [0, 0, 0])[:3] + [float(st.get('rim_w', 1.0))],
                            'u_charaStatusPowInOutDis': [float(st.get('pow') or 1), 0.0, 0.0, 0.0]})
            val.update({'u_skinColor': [1, 1, 1, 0], 'u_hairColor': [1, 1, 1, 0], 'u_subColor1': [0, 0, 0, 0], 'u_subColor2': [0, 0, 0, 0],
                        'u_pointLightHeader0': [0, 0, 0, 0], 'u_pointLightHeader1': [0, 0, 0, 0]})
            c = getattr(self, 'csm', None)
            if c:      # ombres : 3 cascades Direct3D (u_mtxLightWP[3] de cb6, choix de la cascade par u_shadowCascadeMinMax[k].y)
                val['u_mtxLightWP'] = sum((lignes(mul(GL_VERS_D3D, m)) for m in c['vp']), [])
                val['u_shadowCascadeMinMax'] = sum(([t[0], t[1], 0, 0] for t in c['tranches']), [])
                val['u_shadowSampleParams'] = [c['T'], c['T'], 1.0 / c['T'], 1.0 / c['T']]
        tp = []
        for k in range(6):
            m = a['uv'][k] if k < len(a['uv']) else [1, 0, 0, 0, 0, 1, 0, 0]
            tp += [m[0], m[1], m[2], 0, m[4], m[5], m[6], 0]
        val['u_texProj'] = tp
        val['u_uvRange'] = [0, 0, 1, 1] * 6
        for i in range(8):
            val['u_shaderParam%d' % i] = a['params'][i] if i < len(a['params']) else [0, 0, 0, 0]
        if a.get('os_peau'):     # peau : u_mtxBone[k] (float3x4 row_major) = 3 premières lignes de la matrice de l'os k
            val['u_mtxBone'] = sum((lignes(m)[:12] for m in a['os_peau']), [])
        if getattr(self, 'ombre_vp', None) and not a.get('acteur'):   # ombre des effets : u_mtxLightWP = cascade 0 (0x1413486d0)
            val['u_mtxLightWP'] = lignes(mul(GL_VERS_D3D, self.ombre_vp))
        out = {}
        # VITESSE (14/11/2026) : un tampon sans aucune valeur propre au dessin (caméra, lumière, brouillard…) est le même pour
        # tous les dessins de l'image -> fait une fois par image (mémo vidé au début de chaque image, voir rendre())
        memo = self.__dict__.setdefault('_cb_memo', {})
        pdes = self.__dict__.setdefault('_par_dessin', {})
        cle_img = (kc, id(img), bool(a.get('acteur')), id(getattr(self, 'csm', None)), id(getattr(self, 'ombre_vp', None)))
        for r in (prog['rv'], prog['rp'], prog.get('rg') or {'cb': {}, 'vars': {}}):
            for nom_cb, slot in r['cb'].items():
                kd = (id(r), nom_cb)
                pd = pdes.get(kd)
                if pd is None:
                    pd = pdes[kd] = any(v in PAR_DESSIN or v.startswith('u_shaderParam') for v, _, _ in r['vars'].get(nom_cb, []))
                km = None
                if not pd:
                    km = (cle_img, kd, slot, out[slot][1] if slot in out else None)
                    m = memo.get(km)
                    if m is not None:
                        out[slot] = (nom_cb, m)
                        continue
                taille = max([o + t for _, o, t in r['vars'].get(nom_cb, [])] + [16])
                bloc = LUM_BLOCS.get(nom_cb) if img is not None else None
                if slot in out:
                    base = out[slot][1]
                elif bloc is not None:                   # copie de CLightData, comme le jeu
                    base = img[bloc:bloc + (taille + 15) // 16 * 16]
                else:
                    base = b''
                buf = bytearray(base.ljust((taille + 15) // 16 * 16, b'\0'))
                brl = img is not None and nom_cb == 'CBUSE_UB_CAMERA_IDX' and slot not in out
                if brl and len(buf) > 0x250:             # brouillard converti comme le jeu (cb5 +0x250)
                    if getattr(self, '_brl', (None,))[0] is not img:          # (une fois par image : même CLightData)
                        self._brl = (img, brouillard_jeu.convertir(img[0x540:0x620]))
                    fb = self._brl[1]
                    n = min(0xE0, len(buf) - 0x250)
                    buf[0x250:0x250 + n] = fb[:n]
                for v, o, t in r['vars'].get(nom_cb, []):
                    if bloc is not None and v not in val:
                        continue                         # valeur de CLightData
                    if brl and v in BROUILLARD_NOMS:
                        continue
                    if v in val:
                        b = struct.pack('<%df' % len(val[v]), *val[v])
                        # (tableau d'os : la réflexion ne donne que u_mtxBone[4] ; le tampon va jusqu'à u_mtxBoneEnd)
                        b = b[:t] if v != 'u_mtxBone' else b[:len(buf) - o]
                        buf[o:o + len(b)] = b
                    elif v not in self.notes:
                        self.notes.append(v)
                out[slot] = (nom_cb, bytes(buf))
                if km is not None:
                    memo[km] = out[slot][1]
        return out

    def geometrie_fournie(self, g, el):
        """vraies particules : quadrilatères calculés par la page (position dans le repère caméra, couleur float, 3 UV)"""
        nv = 4 * g['n']; tamp, pas = [], []
        for n, s_i, f, slot in el:
            if n == 'POSITION':
                b = struct.pack('<%df' % len(g['pos']), *g['pos']); p = 12
            elif n == 'COLOR':
                b = struct.pack('<%df' % len(g['col']), *g['col']); p = 16
            elif n == 'TEXCOORD':
                u = g['uv'][s_i] if s_i < len(g['uv']) else g['uv'][0]
                b = struct.pack('<%df' % len(u), *u); p = 8
            elif n == 'NORMAL':
                b = struct.pack('<%df' % len(g['nor']), *g['nor']) if g.get('nor') else struct.pack('<3f', 0, 0, 1) * nv; p = 12
            elif n == 'TANGENT' and g.get('tan'):        # repère du quadrilatère x (1, 0, 0), w = 1 (table 0x141a7a5b0 du jeu)
                t = g['tan']; v = [x for k in range(len(t) // 3) for x in (t[3 * k], t[3 * k + 1], t[3 * k + 2], 1.0)]
                b = struct.pack('<%df' % len(v), *v); p = 16
            elif n == 'TANGENT':
                b = struct.pack('<4f', 1, 0, 0, 1) * nv; p = 16
            else:
                b = b'\0' * (12 * nv); p = 12
            tamp.append(self.d.tampon(b, D.BIND_VB)); pas.append(p)
        ib = self.d.tampon(struct.pack('<%dH' % len(g['idx']), *g['idx']), D.BIND_IB)
        return tamp, pas, ib, len(g['idx'])

    def dessiner(self, a):
        if a.get('geo'):
            return self.dessiner_particules(a)
        ob = objet(a['chemin'])
        vs, ps = (a['vs'], a['ps']) if a.get('vs') else noms_shaders(ob, a['piece'])
        # maillage à peau : variante « _vb » du vertex shader du jeu (BLENDWEIGHT / BLENDINDICES, u_mtxBone = cb8). En partie LU
        # (14/11/2026) : chaque <shader>.fxbin range les techniques dans l'ordre base, _vb, _bs, _vb_bs (VS différent, même PS) et
        # le moteur marque à leur chargement les shaders dont le nom contient « _vb » (0x1405d77b0, drapeau 0x20). Le test qui
        # choisit la variante au dessin n'est pas encore trouvé (pas de test direct de ce drapeau).
        if a.get('os_peau'):
            vs = variante_vb(vs)
        prog = self.programme(vs, ps)
        if not prog:
            return 'shader introuvable %s/%s' % (vs, ps)
        d = self.d
        tamp, pas, ib, n = self.geometrie(a['chemin'], a['piece'], prog['el'], a.get('teinte_sommets'))
        d.shaders(prog['vs'], prog['ps'], prog['gs'])
        d.sommets(prog['disp'], tamp, pas, ib)
        for slot, (nom_cb, b) in self.tampons(a, prog).items():
            if a.get('stade') and nom_cb == 'CBUSE_UB_MODEL_MATERIAL_IDX':
                b = b[:8] + struct.pack('<I', 0xFFFFFFFF) + b[12:]          # u_ubParam.z = masque des cubemaps (entier)
            buf = d.tampon(b, D.BIND_CB)
            d.cb('vs', slot, buf); d.cb('ps', slot, buf); d.cb('gs', slot, buf)
        # textures : case k -> t_k ; t11 = image de la scène, t12 = profondeur
        if 't11' in prog['rp']['tex']:
            d.sortie(None, self.dsv, self.w, self.h)
            d.copier(self.copie, self.rt)
            d.sortie(self.rtv, self.dsv, self.w, self.h)
        # noms des textures : ceux du matériau du jeu (l'état exporté met None pour les cartes de données des particules)
        noms_mat = ob.materiaux[ob.pieces[a['piece']]['materiau']].get('textures') or []
        tex = [t or (a['cle'].split('/')[0] + '/' + noms_mat[k].split('/')[-1] if k < len(noms_mat) else None)
               for k, t in enumerate(a['tex'])]
        # (étapes qui lisent des textures seulement : le VS n'en lit presque jamais, le GS n'existe que pour FakeParticle)
        etapes = ('ps',) + (('vs',) if prog['rv'].get('tex') else ()) + (('gs',) if prog['gs'] else ())
        ad = (a.get('adressage') or [])
        for k in range(6):
            cle = tex[k] if k < len(tex) else (tex[0] if tex else None)
            v = self.texture(cle) if cle and not cle.split('/')[-1].startswith('?') else self.blanc
            u, w_ = ad[k] if k < len(ad) else [1, 1]
            s = self.ech(u, w_)
            for e in etapes:
                d.srv(e, k, v); d.ech(e, k, s)
        d.srv('ps', 11, self.copie_srv); d.ech('ps', 11, self.ech(3, 3))
        d.srv('ps', 12, self.prof); d.ech('ps', 12, self.ech(3, 3))
        if a.get('stade'):
            self._lumieres_pl(prog)
            srv_c, cb9 = self.cubemap_jeu(a.get('code_stade') or 's10g001')
            if srv_c:
                d.srv('ps', 14, srv_c); d.ech('ps', 14, self.ech(3, 3))
                if 'CBUSE_UB_CUBEMAP_IDX' in prog['rp']['cb']:
                    d.cb('ps', prog['rp']['cb']['CBUSE_UB_CUBEMAP_IDX'], cb9)
        if a.get('stade'):          # t13 PreShading : x = ombre (shadow_ss du jeu) ; y = SSAO, z = scatter occlusion (LUS, faits dans le lecteur natif seulement ; ce prototype les laisse à 0) ; t14 non liée
            d.srv('ps', 13, getattr(self, 't13_srv', None) or self.noir); d.ech('ps', 13, self.ech(3, 3))
        self._ombre_t15()
        ecran = a.get('surEcran') or not a.get('ztest', True)
        d.etats(self.melange(a.get('melange') or 'alpha'), self.profondeur(a.get('depthTest') and not ecran, a.get('depthMask')),
                self.raster_mat(a.get('faces')))
        mrt = a.get('stade') and a.get('melange') != 'profondeur' and getattr(self, '_mrt_c', None)
        if mrt:                                          # les shaders du stade écrivent 4 images (o3 = normale : SSAO)
            d.sortie([self.rtv] + [x[1] for x in mrt], self.dsv, self.w, self.h)
        d.dessiner(n)
        if mrt:
            d.sortie(self.rtv, self.dsv, self.w, self.h)
        return '%s/%s' % (vs, ps)

    def dessiner_particules(self, a):
        t = _sh.table(DATA)
        vs, ps = a.get('vs'), a.get('ps')
        prog = self.programme(vs, ps, True)
        if not prog:
            return 'shader introuvable %s/%s' % (vs, ps)
        d = self.d
        tamp, pas, ib, n = self.geometrie_fournie(a['geo'], prog['el'])
        d.shaders(prog['vs'], prog['ps'], prog['gs'])
        d.sommets(prog['disp'], tamp, pas, ib)
        for slot, (nom_cb, b) in self.tampons(a, prog).items():
            buf = d.tampon(b, D.BIND_CB)
            d.cb('vs', slot, buf); d.cb('ps', slot, buf); d.cb('gs', slot, buf)
        tex = a.get('tex') or []
        # (étapes qui lisent des textures seulement : le VS n'en lit presque jamais, le GS n'existe que pour FakeParticle)
        etapes = ('ps',) + (('vs',) if prog['rv'].get('tex') else ()) + (('gs',) if prog['gs'] else ())
        ad = (a.get('adressage') or [])
        for k in range(6):
            cle = tex[k] if k < len(tex) else (tex[0] if tex else None)
            v = self.texture(cle) if cle and not cle.split('/')[-1].startswith('?') else self.blanc
            u, w_ = ad[k] if k < len(ad) else [1, 1]
            s = self.ech(u, w_)
            for e in etapes:
                d.srv(e, k, v); d.ech(e, k, s)
        d.srv('ps', 11, self.copie_srv); d.ech('ps', 11, self.ech(3, 3))
        d.srv('ps', 12, self.prof); d.ech('ps', 12, self.ech(3, 3))
        self._ombre_t15()
        ecran = a.get('surEcran') or not a.get('ztest', True)
        d.etats(self.melange(a.get('melange') or 'alpha'), self.profondeur(a.get('depthTest') and not ecran, a.get('depthMask')), self.raster)
        d.dessiner(n)
        return 'particules %s/%s' % (vs, ps)

    _HLSL_PROF = """
Texture2D t0 : register(t0);
float4 vs(uint id : SV_VertexID) : SV_Position { float2 p = float2((id << 1) & 2, id & 2); return float4(p * float2(2, -2) + float2(-1, 1), 0, 1); }
float ps(float4 pos : SV_Position) : SV_Depth {
  uint w, h; t0.GetDimensions(w, h);
  float4 c = t0.Load(int3(int(pos.x), int(h) - 1 - int(pos.y), 0));      // lignes WebGL : de bas en haut
  return c.a < 0.25 ? 1.0 : dot(c.rgb, float3(1.0, 1.0 / 255.0, 1.0 / 65025.0));   // alpha : 0 vide, 0.5 joueur, 1 décor
}
float ps_c(float4 pos : SV_Position) : SV_Target { return ps(pos); }     // même profondeur, en couleur (t12 des particules douces)
"""

    def profondeur_scene(self, rgba, tampon=True, t12=True):
        """profondeur du décor et des joueurs (passe de l'Atelier, 3 octets par pixel) -> tampon de profondeur (si tampon)
        et t12 des particules douces"""
        d = self.d
        if not hasattr(self, '_pp'):
            self._pp = (d.shader('vs', D.compiler(self._HLSL_PROF, 'vs', 'vs_5_0')), d.shader('ps', D.compiler(self._HLSL_PROF, 'ps', 'ps_5_0')),
                        d.melange(D.BLEND_ONE, D.BLEND_ZERO, False, masque=0), d.etat_profondeur(True, True, 8))
            self._pp_tex = d.texture(self.w, self.h, D.RGBA8, bind=D.BIND_SRV)
            self._pp_srv = d.image_shader(self._pp_tex)
        buf = D.ctypes.create_string_buffer(bytes(rgba), len(rgba))
        D._meth(d.ctx, 48, None, D.c_void_p, D.c_uint, D.c_void_p, D.c_void_p, D.c_uint, D.c_uint)(
            d.ctx, self._pp_tex, 0, None, D.cast(buf, D.c_void_p), self.w * 4, 0)
        vs, ps, mel, pro = self._pp
        if tampon:
            d.shaders(vs, ps)
            d.srv('ps', 0, self._pp_srv)
            d.etats(mel, pro, self.raster)
            d.dessiner_sans_sommets(3)
        if not t12:
            return
        # t12 du jeu (_profScene des particules douces) : la même profondeur de 0 à 1, rangée dans une image R32F
        if not hasattr(self, '_t12'):
            t = d.texture(self.w, self.h, D.R32F, bind=D.BIND_RTV | D.BIND_SRV)
            self._t12 = (d.cible(t), d.image_shader(t), d.shader('ps', D.compiler(self._HLSL_PROF, 'ps_c', 'ps_5_0')),
                         d.melange(D.BLEND_ONE, D.BLEND_ZERO, False), d.etat_profondeur(False, False))
        rtv, srv, psc, mel2, pro2 = self._t12
        d.srv('ps', 12, None)                      # délier t12 avant d'y écrire
        d.sortie(rtv, None, self.w, self.h)
        d.shaders(vs, psc)
        d.srv('ps', 0, self._pp_srv)
        d.etats(mel2, pro2, self.raster)
        d.dessiner_sans_sommets(3)
        d.sortie(self.rtv, self.dsv, self.w, self.h)
        self.prof = srv

    def debut(self, fond=None):
        """nouvelle image : fond = pixels RGBA (lignes de haut en bas) de la scène sans les effets, ou noir"""
        d = self.d
        d.effacer(self.rtv, self.dsv)
        self.prof = self._prof_vide                 # t12 : rien devant, sauf si la page envoie la profondeur de la scène
        if fond:                                    # fond 8 bits -> image HDR (recopie)
            d.maj(self.fond_tex, fond, self.w * 4)
            self._post().copier_vers(self.rtv, self.fond_srv)
        d.sortie(self.rtv, self.dsv, self.w, self.h)

    def _post(self):
        if self.post is None:
            import post
            self.post = post.Post(self.d, self.w, self.h)
        return self.post

    def texture_modifiee(self, cle, w, h, rgba):
        """texture recolorée dans l'Atelier (pixels RGBA) : remplace celle du cache pour cette clé"""
        k = (cle, zlib.crc32(rgba))
        if self._tex.get(('modif', cle)) == k:
            return
        t = self.d.texture(w, h, D.RGBA8, rgba, w * 4, bind=D.BIND_SRV | D.BIND_RTV, mips=0, misc=D.MISC_GENERATE_MIPS)
        v = self.d.image_shader(t)
        self.d.mips(v)
        self._tex[cle] = v
        self._tex[('modif', cle)] = k

    def pixels(self, effets_ecran=False, profondeur=None, lum_avant=None, reglages=None, apres_tonemap=None):
        P = self._post()
        self.lum_moyenne = None
        if effets_ecran:
            self.lum_moyenne = P.appliquer(self.rtv, self.rt_srv, self.sortie_rtv, profondeur, lum_avant, reglages, self.fond_srv,
                                           apres_tonemap=apres_tonemap)
        else:
            P.copier_vers(self.sortie_rtv, self.rt_srv)
        return b''.join(self.d.lire(self.sortie_tex, self.w, self.h))

    def enregistrer(self, f, effets_ecran=False):
        px = self.pixels(effets_ecran)
        rows = [px[y * self.w * 4:(y + 1) * self.w * 4] for y in range(self.h)]
        out = []
        for r in rows:
            b = bytearray(r)
            b[3::4] = b'\xff' * self.w
            out.append(b)
        images.ecrire_png(f, self.w, self.h, out)


_service = {}


def rendre(etat, fond=None, modifs=None, profondeur=None, effets_ecran=False, lum_avant=None, reglages=None, ombre=None, profondeur_objets=None):
    """pour le serveur de l'Atelier : -> (pixels RGBA, remarques). Un appareil Direct3D par taille d'image, gardé."""
    w, h = etat['largeur'], etat['hauteur']
    R = _service.get((w, h))
    if R is None:
        R = _service[(w, h)] = Rendu(w, h)
    for cle, (tw, th, px) in (modifs or {}).items():
        R.texture_modifiee(cle, tw, th, px)
    R.debut(fond)
    R._cb_memo = {}                                      # tampons communs à tous les dessins : refaits à chaque image
    stade = etat.get('stade')
    if stade and profondeur_objets and len(profondeur_objets) == w * h * 4:
        R.profondeur_scene(profondeur_objets, t12=False)     # objets de la page (ballon…) ; le stade écrit ensuite la sienne
    if profondeur and len(profondeur) == w * h * 4:
        R.profondeur_scene(profondeur, tampon=not stade)     # t12 (et tampon si le stade n'est pas dessiné par Direct3D)
    R.notes = []
    R.lumiere = image_lumiere(reglages)                  # cb6 / cb7 = copies de CLightData (défauts du jeu + réglages du plan)
    R.ombre_effets(ombre)                                # t15 + u_mtxLightWP
    faits = []
    if stade:                                            # décor dessiné par Direct3D avec les vrais shaders du jeu
        mvp = mul(stade['P'], stade['V'])
        I4 = [1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1]
        L = stade_appels(stade['code']) if stade.get('decor', True) else []   # décor caché par la cinématique : pas de stade
        R.t13_srv = None; R.csm = None
        R.lier_lumieres(stade.get('lumieres'))         # lumières ponctuelles des effets (calculées par la page)
        R.acteurs_cour = acteurs_appels(stade, R.notes)  # peau des acteurs faite ici (matrices des os envoyées par la page)
        if stade.get('ombres'):                          # 0. ombres du soleil : 3 cartes + shadow_ss du jeu -> t13
            try:
                R.ombres_stade(L, stade, reglages)
            except Exception as ex:                       # (pas d'ombre plutôt qu'une image ratée)
                R.notes.append('ombres : %s' % ex)
        Vw = stade['V']; oeil = [-(Vw[i * 4] * Vw[12] + Vw[i * 4 + 1] * Vw[13] + Vw[i * 4 + 2] * Vw[14]) for i in range(3)]
        L = [a for a in L if visible_lod(a, oeil)]      # niveaux de détail / distance d'affichage du jeu
        for a in L:                                      # 1. profondeur (depth / depth_cutout du jeu)
            if a.get('ombre_seule'):
                continue
            t0 = (a['tex'] or [None])[0]
            pr = dict(a, mvp=mvp, modele=a.get('inst') or I4, V=stade['V'], P=stade['P'], melange='profondeur',
                      vs='depth_cutout' if a['cutout'] else 'depth', ps='depth_cutout' if a['cutout'] else 'depth',
                      tex=[None, masque_cutout(a)], ubParam=[1.0, 0, 0, a['seuil']])
            R.dessiner(pr)
        def couleur():
            R.vider_mrt()
            out = []
            for a in L:                                  # 2. couleur : profondeur déjà écrite (LESS_EQUAL, sans écriture)
                if a.get('ombre_seule'):
                    continue
                out.append(R.dessiner(dict(a, mvp=mvp, modele=a.get('inst') or I4, V=stade['V'], P=stade['P'], depthMask=False)))
            for g in R.acteurs_cour or []:               # 3. acteurs avec les shaders chr_toon* du jeu (4 images écrites)
                try:
                    out.append(R.dessiner_acteur(g, stade))
                except Exception as ex:
                    R.notes.append('acteur %s : %s' % (g['cle'], ex))
            return out
        R._mrt()
        faits += couleur()
        try:                                             # SSAO du jeu (t13.y) avec les normales de cette image, puis 2e passe
            ok = R.ssao_jeu(stade, reglages)
            ok = R.pieds_jeu(stade, reglages) or ok    # ombre sous les pieds (même canal G)
            if ok:
                faits = faits[:0] + couleur()
        except Exception as ex:
            R.notes.append('ssao : %s' % ex)
        try:                                             # 3 b. ciel du jeu (atmosphère, useFogSky), derrière tout
            if stade.get('decor', True):
                R.ciel_jeu(stade, reglages)
        except Exception as ex:
            R.notes.append('ciel : %s' % ex)
        if R.acteurs_cour:
            try:                                         # 4. contours d'écran du jeu (Edge -> EdgeTone -> EdgeComposi)
                R.contour_jeu(stade)
            except Exception as ex:
                R.notes.append('contour : %s' % ex)
    faits += [R.dessiner(a) for a in etat['appels']]
    apres = None
    if etat.get('post_ancien'):                          # essais : ancien ordre (halo avant le tone mapping, DOF sur l'image HDR)
        if stade:
            try:
                R.dof_jeu(stade, reglages)
            except Exception as ex:
                R.notes.append('dof : %s' % ex)
        P = R._post()
        R.lum_moyenne = P.appliquer_ancien(R.rtv, R.rt_srv, R.sortie_rtv, profondeur if profondeur and len(profondeur) == w * h * 4 else None,
                                           lum_avant, reglages, R.fond_srv) if effets_ecran else None
        if not effets_ecran:
            P.copier_vers(R.sortie_rtv, R.rt_srv)
        px = b''.join(R.d.lire(R.sortie_tex, w, h))
        return px, ['ancien ordre'] + (['luminosité moyenne %.3f' % R.lum_moyenne] if R.lum_moyenne is not None else [])
    if stade and effets_ecran:
        # ORDRE DU JEU (LU le 14/11/2026, 0x140f9bdb0) : APRÈS le tone mapping, sur l'image finale : anticrénelage (pas
        # fait : TAA, dépend des images précédentes), profondeur de champ, rayons de soleil, reflets d'objectif (pas fait),
        # puis le halo (fait par post.appliquer)
        def apres(rtv, srv):
            if (reglages or {}).get('enableDoF', [1])[0]:
                try:
                    R.dof_jeu(stade, reglages, src_srv=srv, cible_rtv=rtv)
                except Exception as ex:
                    R.notes.append('dof : %s' % ex)
            # rayons de soleil et reflets d'objectif : COUPÉS pendant les cinématiques des techniques (jeu de drapeaux n° 1,
            # mesuré dans le jeu en marche le 14/11/2026) ; soleil_jeu ne sert qu'aux vues de match (etat['vue_match'])
            if etat.get('vue_match'):
                try:
                    R.soleil_jeu(stade, reglages, rtv)
                except Exception as ex:
                    R.notes.append('soleil : %s' % ex)
    elif stade:
        try:                                             # sans effets d'écran : profondeur de champ sur l'image HDR
            R.dof_jeu(stade, reglages)
        except Exception as ex:
            R.notes.append('dof : %s' % ex)
    px = R.pixels(effets_ecran, profondeur if profondeur and len(profondeur) == w * h * 4 else None, lum_avant, reglages, apres)
    if os.environ.get('ATELIER_D3D_IMAGE'):             # essais : copie de la dernière image (fichier donné par la variable)
        try:
            images.ecrire_png(os.environ['ATELIER_D3D_IMAGE'], w, h, [px[y * w * 4:(y + 1) * w * 4] for y in range(h)])
        except Exception:
            pass
    return px, [f for f in faits if f.startswith('shader introuvable')] + (['luminosité moyenne %.3f' % R.lum_moyenne] if R.lum_moyenne is not None else [])


if __name__ == '__main__':
    etat = json.load(open(sys.argv[1], encoding='utf-8'))
    R = Rendu(etat['largeur'], etat['hauteur'])
    for a in etat['appels']:
        print(a['cle'], '->', R.dessiner(a))
    R.enregistrer(sys.argv[2], len(sys.argv) > 3 and sys.argv[3] == 'ecran')
    if R.notes:
        print('variables sans valeur (mises à 0) :', ', '.join(R.notes))
    print('ok', sys.argv[2])
