"""Stades (map/s/<code>) pour le décor des cinématiques : morceaux (g01…, h001…, ao…), textures, éclairage cuit.

Trouvé le 13/11/2026 sur s10g001 (terrain en terre de l'école Raimon, celui des vidéos de référence) :
- chaque morceau = common/map/s/<code>/<morceau>/<morceau>.g4pkm + .g4mg, sommets déjà placés dans le monde ;
- les .g4tx des cartes n'ont PAS de noms : table des crc32 à 0x60 + n x 0x30 (comme les autres .g4tx), et le modèle
  (G4MD) a sa table des crc32 des textures qu'il utilise -> on relie par le crc ;
- matériau -> cases de 6 octets (5e = n° dans la table des textures du modèle, 6e = 3), comme les effets ;
- sommet : position (type 1), normale (2), couleur RGBA = éclairage cuit (type 8), UV (type 10), 2e UV (type 11) ;
- textures BC7 / DXT1 (+ 1 HDR ignorée) ; on décode un niveau réduit (512 px au plus) pour aller vite.
"""
import os, glob, struct, json, re, zlib
from . import g4
from lib import images  # noqa: E402  (Atelier Maillots)


def _g4tx_index(dossier_dx11):
    """{crc32: (fichier .g4tx, n°)} pour toutes les textures du stade"""
    from moteur import donnees_virtuelles as _dv
    idx = {}
    for f in glob.glob(os.path.join(dossier_dx11, '**', '*.g4tx'), recursive=True):
        b = _dv.debut(f, 8192)                    # lecture directe : en-tête sans sortir le fichier
        n = struct.unpack_from('<H', b, 0x20)[0]
        if 0x60 + n * 0x34 > len(b):
            b = _dv.debut(f, 0x60 + n * 0x34 + 16)
        for k, c in enumerate(struct.unpack_from('<%dI' % n, b, 0x60 + n * 0x30)):
            idx.setdefault(c, (f, k))
    return idx


def _niveau(bloc, maxi=512):
    """DDS réduit : le premier niveau (mip) dont le côté est <= maxi, avec un en-tête à 1 niveau"""
    h, w = struct.unpack_from('<II', bloc, 12)
    mips = images.mips_dds(bloc)
    dx10 = bloc[84:88] == b'DX10'
    entete = 148 if dx10 else 128
    fmt = struct.unpack_from('<I', bloc, 128)[0] if dx10 else bloc[84:88]
    taille_bloc = 8 if fmt in (b'DXT1', b'BC4U', b'ATI1', 70, 71, 72, 80, 81) else 16
    o, lw, lh, k = entete, w, h, 0
    while k < mips - 1 and max(lw, lh) > maxi:
        o += max(1, (lw + 3) // 4) * max(1, (lh + 3) // 4) * taille_bloc
        lw, lh, k = max(1, lw // 2), max(1, lh // 2), k + 1
    t = max(1, (lw + 3) // 4) * max(1, (lh + 3) // 4) * taille_bloc
    tete = bytearray(bloc[:entete])
    struct.pack_into('<II', tete, 12, lh, lw)
    struct.pack_into('<I', tete, 28, 1)
    return bytes(tete) + bloc[o:o + t], fmt


def texture_png(dossier_cache, f, k, crc):
    """PNG (réduit) de la texture n° k du fichier f -> cache ; renvoie le nom de fichier ou None"""
    out = os.path.join(dossier_cache, '%08x.png' % crc)
    if os.path.exists(out):
        return os.path.basename(out)
    b = open(f, 'rb').read()
    n = struct.unpack_from('<H', b, 0x20)[0]
    deb = len(b) - struct.unpack_from('<I', b, 0x2C)[0]
    off, size = struct.unpack_from('<II', b, 0x60 + k * 0x30 + 4)
    bloc = b[deb + off:deb + off + size]
    if bloc[:4] != b'DDS ':
        return None
    petit, fmt = _niveau(bloc)
    if fmt not in (98, 99, b'DXT1', b'BC4U', b'ATI1'):     # BC4 : masques « .a » des arbres (13/11/2026)
        return None                                      # HDR (BC6H) et autres : ignorés
    r = g4.decoder_texture(petit)
    if not r:
        return None
    images.ecrire_png(out, *r)
    return os.path.basename(out)


def morceaux(data_dir, code):
    """morceaux déjà placés dans le monde ; les objets « ao » (tours, poteaux…) sont à l'origine et placés par
    config/<code>_placement.cfg.bin : pas encore lus -> laissés de côté (sinon ils tombent au milieu de la scène)"""
    c = os.path.join(data_dir, 'common', 'map', 's', code)
    return sorted(x for x in os.listdir(c) if os.path.exists(os.path.join(c, x, x + '.g4pkm')) and not re.search(r'ao\d+$', x))


def _materiaux_exacts(md, tex, dc, code):
    """matériaux du stade lus comme ceux des effets (en-tête du G4MD, voir g4.py) : shader, textures PAR CASE (n° de case =
    ordre des références), u_shaderParam0..7, couleur (u_diffuse, u_ambient), matrices de texture (u_texProj)"""
    from . import shaders as _sh
    base = struct.unpack_from('<H', md, 0x0A)[0] * 4
    off = lambda o: base + struct.unpack_from('<H', md, o)[0] * 4
    nmat, ntex = struct.unpack_from('<H', md, 0x22)[0], md[0x27]
    t_mat, t_col, t_ref, f_ref, t_par, f_par, t_crc = off(0x64), off(0x66), off(0x68), off(0x6A), off(0x6A), off(0x6C), off(0x76)
    t_tp, f_tp, t_sh, f_sh = off(0x88), off(0x8A), off(0x78), off(0x7A)
    crcs = [struct.unpack_from('<I', md, t_crc + 4 * j)[0] for j in range(ntex)]
    lsh = [struct.unpack_from('<I', md, a)[0] for a in range(t_sh, f_sh, 4)] if f_sh > t_sh else []
    tab = _sh.table(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(tex and next(iter(tex.values()))[0] or '.'))))))
    nref = (f_ref - t_ref) // 6
    out = []
    for k in range(nmat):
        v = struct.unpack_from('<8H', md, t_mat + 16 * k)
        n, d = v[6] & 0xFF, v[3]
        cases = []
        for j in range(d, d + n):
            if j >= nref or md[t_ref + 6 * j] >= ntex:
                cases.append(None); continue
            c = crcs[md[t_ref + 6 * j]]
            nom = texture_png(dc, *tex[c], c) if c in tex else None
            cases.append('carte_%s/%s' % (code, nom[:-4]) if nom else None)
        c = struct.unpack_from('<12f', md, t_col + 48 * v[0]) if t_col + 48 * v[0] + 48 <= len(md) else [1, 1, 1, 1, 0, 0, 0, 1] + [0] * 4
        sh = tab.get(lsh[v[4] >> 8]) if (v[4] >> 8) < len(lsh) else None
        out.append({'shader': sh['nom'] if sh else None, 'tex': cases,
                    'params': [list(struct.unpack_from('<4f', md, t_par + 16 * (v[1] + j))) for j in range(8) if t_par + 16 * (v[1] + j) + 16 <= f_par],
                    'diffuse': list(c[0:4]), 'ambient': list(c[4:8]),
                    'texproj': [list(struct.unpack_from('<8f', md, t_tp + 32 * (v[7] + j))) for j in range(n) if t_tp + 32 * (v[7] + j) + 32 <= f_tp]})
    return out


def lire(data_dir, code, cache_dir):
    """tous les maillages du stade : [{pos, nor, uv, col, idx, texture}] (texture = 'carte_<code>/<crc>' ou None)"""
    dc = os.path.join(cache_dir, 'carte_' + code)
    os.makedirs(dc, exist_ok=True)
    tex = _g4tx_index(os.path.join(data_dir, 'dx11', 'map', 's', code))
    sortie = []
    for m in morceaux(data_dir, code):
        try:
            ob = g4.ObjetEffet(data_dir, 'common/map/s/%s/%s/%s.objbin' % (code, m, m))
        except Exception:
            continue
        md = ob.md
        nmat = struct.unpack_from('<H', md, 0x22)[0]
        # table des crc des textures du modèle : la plus longue suite de crc connus
        meilleur = (0, 0)
        i = 0
        while i < len(md) - 4:
            k = 0
            while i + 4 * k + 4 <= len(md) and struct.unpack_from('<I', md, i + 4 * k)[0] in tex:
                k += 1
            if k > meilleur[1]:
                meilleur = (i, k)
            i += 4 * max(k, 1)
        t0, nt = meilleur
        table = [struct.unpack_from('<I', md, t0 + 4 * j)[0] for j in range(nt)]
        # cases (6 octets, 6e = 3) et fiches des matériaux
        n = struct.unpack_from('<H', md, 0x20)[0]
        q = 0xA0 + 0x50 * n
        while q + 8 <= len(md):
            tt, oo = md[q], md[q + 1]; ff = struct.unpack_from('<I', md, q + 4)[0]
            if tt > 16 or oo > 80 or ff > 0x40:
                break
            q += 8
        fiches = [struct.unpack_from('<4B6H', md, q + 16 * kk) for kk in range(nmat)]
        try:
            mats_jeu = _materiaux_exacts(md, tex, dc, code)
        except Exception:
            mats_jeu = []
        cases = []
        if nt:
            best = (0, 0)
            for s0 in range(q + 16 * nmat, t0 if t0 > q else len(md) - 6):
                kk = 0
                while s0 + 6 * kk + 6 <= len(md) and md[s0 + 6 * kk + 5] == 3 and md[s0 + 6 * kk + 4] < nt:
                    kk += 1
                if kk > best[1]:
                    best = (s0, kk)
            cases = [md[best[0] + 6 * kk + 4] for kk in range(best[1])]
        for p in ob.pieces:
            pos, col, idx, uv = ob.geometrie(p['index'])
            if not pos:
                continue
            texture = None
            if p['materiau'] is not None and p['materiau'] < len(fiches) and cases:
                # fiche de matériau des cartes : fin de ses cases = u16 +6 ; début = fin de la fiche précédente
                # 3 cases = [commune, COULEUR, relief] ; 2 cases = [COULEUR, ...] ; 1 case = COULEUR
                k = p['materiau']
                fin = fiches[k][5]; debut = fiches[k - 1][5] if k else 0
                cs = [cases[j] for j in range(debut, min(fin, len(cases))) if cases[j] < len(table)]
                ordre = ([cs[1]] if len(cs) == 3 else []) + cs
                for c in ordre:
                    crc = table[c]
                    nom = texture_png(dc, *tex[crc], crc)
                    if nom:
                        texture = 'carte_%s/%s' % (code, nom[:-4])
                        break
            col = bytearray(col)
            col[3::4] = b'\xff' * (len(col) // 4)          # éclairage cuit : on garde la couleur, pas la transparence
            try:
                nor = ob.normales(p['index'])       # normales (lumières ponctuelles : N.L du shader du stade)
            except Exception:
                nor = None
            if nor is not None and len(nor) != len(pos):
                nor = None
            try:
                pp = ob.pieces[p['index']]                 # tangentes BRUTES x, y, z, w (s16 / 32767) : le shader normalise en 4D
                tan = None if pp.get('tan') is None else [x / 32767 for k in range(len(pos) // 3)
                                                          for x in struct.unpack_from('<4h', ob.mg, pp['vb'] + k * pp['pas'] + pp['tan'])]
            except Exception:
                tan = None
            if tan is not None and len(tan) != len(pos) // 3 * 4:
                tan = None
            jeu = mats_jeu[p['materiau']] if p['materiau'] is not None and p['materiau'] < len(mats_jeu) else None
            sortie.append({'nom': '%s/%s' % (m, p['nom']), 'pos': pos, 'col': bytes(col), 'uv': uv, 'idx': idx, 'texture': texture, 'nor': nor, 'tan': tan, 'jeu': jeu})
    return sortie


def binaire(maillages):
    meta, morceaux_ = [], []
    for m in maillages:
        nv, ni = len(m['pos']) // 3, len(m['idx'])
        nor = m.get('nor')
        tan = m.get('tan') if nor is not None else None
        meta.append({'nom': m['nom'], 'texture': m['texture'], 'nv': nv, 'ni': ni, 'n': nor is not None, 't': tan is not None, 'jeu': m.get('jeu')})
        morceaux_.append(struct.pack('<%df' % (3 * nv), *m['pos']) + bytes(m['col']) + struct.pack('<%df' % (2 * nv), *m['uv'])
                         + struct.pack('<%dH' % ni, *m['idx']) + b'\0' * ((-2 * ni) % 4)
                         + (struct.pack('<%df' % (3 * nv), *nor) if nor is not None else b'')   # normales (après l'index)
                         + (struct.pack('<%df' % (4 * nv), *tan) if tan is not None else b''))  # tangentes (4 flottants)
    entete = json.dumps(meta).encode()
    entete += b' ' * ((-len(entete)) % 4)
    return struct.pack('<I', len(entete)) + entete + b''.join(morceaux_)


def cubemap(data_dir, code, cache_dir):
    """cubemap HDR du stade (BC6H, décodée par la carte graphique : AtelierD3D/bc6h.py) -> octets RGBA 8 bits
    [6 faces x 8 niveaux, face par face, niveaux du plus grand au plus petit] + en-tête JSON {taille, niveaux}.
    Laquelle : common/map/s/<code>/config/<code>_env_data_*.cfg.bin -> TEXTURE_SET_INFO_GROUP_DATA [0, 0, crc, …] (s10g001 : s10g001_03_cb)"""
    import sys
    sortie = os.path.join(cache_dir, 'carte_' + code, 'cubemap.bin')
    if os.path.exists(sortie):
        return open(sortie, 'rb').read()
    from . import particules as _pt
    crc = None
    for f in sorted(glob.glob(os.path.join(data_dir, 'common', 'map', 's', code, 'config', code + '_env_data_*.cfg.bin'))):
        for nom, v in _pt.lire_brut(f):
            if nom == 'TEXTURE_SET_INFO_GROUP_DATA' and len(v) >= 3 and v[2][1]:
                crc = v[2][1] & 0xFFFFFFFF; break
        if crc:
            break
    tex = _g4tx_index(os.path.join(data_dir, 'dx11', 'map', 's', code))
    if crc not in tex:
        return None
    f, k = tex[crc]
    b = open(f, 'rb').read()
    deb = len(b) - struct.unpack_from('<I', b, 0x2C)[0]
    o, size = struct.unpack_from('<II', b, 0x60 + k * 0x30 + 4)
    bloc = b[deb + o:deb + o + size]
    h, w = struct.unpack_from('<II', bloc, 12)
    mips = struct.unpack_from('<I', bloc, 28)[0]
    fmt = struct.unpack_from('<I', bloc, 128)[0]
    d3d = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'AtelierD3D')
    if d3d not in sys.path:
        sys.path.insert(0, d3d)
    import bc6h
    o, out = 148, bytearray()
    for face in range(6):
        niv, lu = bc6h.decoder(bloc[o:], w, h, mips, fmt == 96); o += lu
        for lw, lh, v in niv:
            out += bytes(max(0, min(255, int(round(x * 255)))) for x in v)
    entete = json.dumps({'taille': w, 'niveaux': mips, 'crc': crc}).encode()
    entete += b' ' * ((-len(entete)) % 4)
    r = struct.pack('<I', len(entete)) + entete + bytes(out)
    os.makedirs(os.path.dirname(sortie), exist_ok=True)
    open(sortie, 'wb').write(r)
    return r
