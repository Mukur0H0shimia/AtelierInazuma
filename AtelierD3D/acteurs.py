"""Acteurs (joueurs, esprits guerriers, totems, ballon) dessinés par Direct3D avec les VRAIS shaders du jeu (13/11/2026).

- matériaux lus comme le jeu dans le G4MD (même lecture que moteur/g4.py pour les effets : tables de l'en-tête) :
  shader (+0x78, v4 >> 8), u_shaderParam0..7 (+0x6A, à partir de v1), couleurs (+0x66, v0), cases de texture
  (+0x68 refs, v3 / v6 & 0xFF ; crc32 des noms +0x76), u_texProj (+0x88, v7), fiche d'état (+0x6C, v2 / 8) ;
- PEAU : la page envoie seulement les matrices des os de chaque acteur (monde animé x inverse du repos, celles qu'elle
  utilise pour sa propre peau) ; le serveur fait la peau des positions, normales ET tangentes (numpy) : le VS chr_toon
  du jeu ne fait pas de peau (les sommets lui arrivent déjà placés) ;
- autres attributs (UV, couleur, TEXCOORD1…) lus TELS QUELS dans le .g4mg, d'après la déclaration du shader ;
- t7 « in_texGrd » = chrGrd_01 de dx11/chr/shader/texture/chr_tex.g4tx (nie.exe 0x140f9e990, voir textures_chr.py).
"""
import os, struct, zlib
import numpy as np


def _off(md, o):
    return struct.unpack_from('<H', md, 0x0A)[0] * 4 + struct.unpack_from('<H', md, o)[0] * 4


def materiaux(md, noms_tex, tab_sh):
    """G4MD -> liste de matériaux {shader, vs, ps, tex (noms par case), params, diffuse, ambient, texproj, adressage, etat}
    noms_tex : noms des textures disponibles (tous les .g4tx de l'acteur) ; tab_sh : moteur.shaders.table"""
    nmat = struct.unpack_from('<H', md, 0x22)[0]
    t_mat, t_col, t_ref, f_ref, t_crc = _off(md, 0x64), _off(md, 0x66), _off(md, 0x68), _off(md, 0x6A), _off(md, 0x76)
    ntex = md[0x27]
    crc_t = {zlib.crc32(t.encode()): t for t in noms_tex}
    crcs = [struct.unpack_from('<I', md, t_crc + 4 * j)[0] for j in range(ntex)]
    table = [crc_t.get(c) or '?%08x' % c for c in crcs]
    nref = (f_ref - t_ref) // 6
    refs = [md[t_ref + 6 * j] for j in range(nref)]
    t_et, f_et = _off(md, 0x6C), _off(md, 0x6E)
    etats = [dict(zip(md[a:a + 16:2], md[a + 1:a + 16:2])) for a in range(t_et, f_et, 16)] if f_et > t_et else []
    t_sh, f_sh = _off(md, 0x78), _off(md, 0x7A)
    liste_sh = [struct.unpack_from('<I', md, a)[0] for a in range(t_sh, f_sh, 4)] if f_sh > t_sh else []
    t_par, f_par = _off(md, 0x6A), _off(md, 0x6C)
    t_tp, f_tp = _off(md, 0x88), _off(md, 0x8A)
    t_ad, f_ad = _off(md, 0x6E), _off(md, 0x70)
    conv = (0, 1, 2, 3, 5, 4)
    out = []
    for k in range(nmat):
        v = struct.unpack_from('<8H', md, t_mat + 16 * k)
        n, d = v[6] & 0xFF, v[3]
        tex = [table[refs[j]] for j in range(d, d + n) if j < nref and refs[j] < ntex]
        ad = []
        for j in range(d, d + n):
            if j < nref:
                r_ = t_ref + 6 * j
                cnt, o_ = md[r_ + 1], struct.unpack_from('<H', md, r_ + 4)[0]
                pr_ = {md[t_ad + 2 * (o_ + q)]: md[t_ad + 2 * (o_ + q) + 1] for q in range(cnt) if t_ad + 2 * (o_ + q) + 2 <= f_ad}
                ad.append([conv[pr_.get(1, 1)] if pr_.get(1, 1) < 6 else 1, conv[pr_.get(2, 1)] if pr_.get(2, 1) < 6 else 1])
        c = struct.unpack_from('<12f', md, t_col + 48 * v[0]) if t_col + 48 * v[0] + 48 <= len(md) else [1] * 4 + [0] * 8
        i_sh = v[4] >> 8
        sh = tab_sh.get(liste_sh[i_sh]) if i_sh < len(liste_sh) else None
        out.append({'shader': sh['nom'] if sh else None, 'vs': sh['vs'] if sh else None, 'ps': sh['ps'] if sh else None, 'tex': tex,
                    'params': [list(struct.unpack_from('<4f', md, t_par + 16 * (v[1] + j))) if t_par + 16 * (v[1] + j) + 16 <= f_par else [0] * 4
                               for j in range(8)],
                    'diffuse': list(c[0:4]), 'ambient': list(c[4:8]),
                    'texproj': [list(struct.unpack_from('<8f', md, t_tp + 32 * (v[7] + j))) for j in range(n) if t_tp + 32 * (v[7] + j) + 32 <= f_tp],
                    'adressage': ad, 'etat': etats[v[2] // 8] if v[2] // 8 < len(etats) else {}})
    return out


def maillages(md):
    """entrées des maillages du G4MD : vb, ib, nv, ni, pas, disposition {type: (décalage, format)}, matériau"""
    n = struct.unpack_from('<H', md, 0x20)[0]
    debut_ib = struct.unpack_from('<I', md, 0x5C)[0]
    q = 0xA0 + 0x50 * n
    groupes, g = [], []
    while q + 8 <= len(md):
        t, o = md[q], md[q + 1]; f = struct.unpack_from('<I', md, q + 4)[0]
        if t > 16 or o > 80 or f > 0x40:
            break
        if t == 0:
            groupes.append(g); g = []
        else:
            g.append((t, o, f))
        q += 8
    out = []
    for i in range(n):
        e = md[0xA0 + 0x50 * i: 0xA0 + 0x50 * (i + 1)]
        vb, ib, nv, ni = struct.unpack_from('<4I', e, 0)
        dsp = groupes[e[0x42] + 1] if e[0x42] + 1 < len(groupes) else []
        out.append({'vb': vb, 'ib': debut_ib + ib, 'nv': nv, 'ni': ni, 'pas': e[0x3E], 'mat': e[0x43], 'disp': {t: (o, f) for t, o, f in dsp}})
    return out


def _attr(mg, m, typ, comp):
    """attribut brut d'un maillage -> tableau nv x comp (flottants), ou None"""
    o, f = m['disp'].get(typ, (None, None))
    if o is None:
        return None
    nv, pas = m['nv'], m['pas']
    brut = np.frombuffer(mg, dtype=np.uint8, count=nv * pas, offset=m['vb']).reshape(nv, pas)
    if f == 2 or f == 0 or f == 1:                  # flottants (2 = 2 x f32 ; 0/1 : 3/4 x f32, APPROCHÉ)
        nb = {2: 2, 0: 3, 1: 4}[f]
        return np.ascontiguousarray(brut[:, o:o + 4 * nb]).view('<f4').reshape(nv, nb)[:, :comp]
    if f == 14:
        return np.ascontiguousarray(brut[:, o:o + 4]).view('<u2').reshape(nv, 2).astype(np.float32) / 65535
    if f == 18:
        return np.ascontiguousarray(brut[:, o:o + 4]).view('<i2').reshape(nv, 2).astype(np.float32) / 32767
    if f == 20:
        return np.ascontiguousarray(brut[:, o:o + 8]).view('<i2').reshape(nv, 4).astype(np.float32)[:, :comp] / 32767
    if f == 12:
        return brut[:, o:o + 4].astype(np.float32) / 255
    return None


class Acteur:
    """un modèle d'acteur tel que la page le charge (/api/modele) : pièces dans le MÊME ORDRE que ses pièces <acteur>/<i>.
    pièce = {md, mg, m (entrée du maillage), os (nv x 4, n° d'os du squelette), poids (nv x 4), mat (matériau du jeu),
    dossier (sous-dossier des PNG du cache), noir (joueur mannequin : laissé à la vue WebGL, choix de l'utilisateur)}"""

    def __init__(self, pieces):
        self.pieces = pieces

    def peau(self, i, mats):
        """positions, normales, tangentes (xyz + w brut) de la pièce i avec les matrices des os
        (une liste de 16 flottants par os, colonne par colonne : monde animé x inverse du repos, comme la vue)"""
        p = self.pieces[i]; mg, m = p['mg'], p['m']
        M = np.asarray(mats, dtype=np.float64).reshape(-1, 4, 4).transpose(0, 2, 1)     # -> lignes
        nv = m['nv']
        brut = np.frombuffer(mg, dtype=np.uint8, count=nv * m['pas'], offset=m['vb']).reshape(nv, m['pas'])
        pos = np.ascontiguousarray(brut[:, :12]).view('<f4').reshape(nv, 3).astype(np.float64)
        nor = _attr(mg, m, 2, 3); tan = _attr(mg, m, 3, 4)
        if nor is None:
            nor = np.tile([0.0, 1.0, 0.0], (nv, 1))
        if tan is None:
            tan = np.tile([1.0, 0.0, 0.0, 1.0], (nv, 1))
        jo = np.minimum(p['os'], len(M) - 1)
        Mv = (M[jo] * p['poids'][:, :, None, None]).sum(1)                              # nv x 4 x 4
        P = np.einsum('vij,vj->vi', Mv[:, :3, :3], pos) + Mv[:, :3, 3]
        N = np.einsum('vij,vj->vi', Mv[:, :3, :3], nor[:, :3])
        N /= np.maximum(np.linalg.norm(N, axis=1, keepdims=True), 1e-9)
        T = np.einsum('vij,vj->vi', Mv[:, :3, :3], tan[:, :3].astype(np.float64))
        T /= np.maximum(np.linalg.norm(T, axis=1, keepdims=True), 1e-9)
        return P.astype(np.float32), N.astype(np.float32), np.concatenate([T, tan[:, 3:4]], 1).astype(np.float32)

    def attributs(self, i):
        """attributs fixes de la pièce i : couleur de sommet (RGBA8, type 8), UV 0..5 (types 10..15), indices"""
        p = self.pieces[i]
        if '_fixe' not in p:
            mg, m = p['mg'], p['m']; nv = m['nv']
            o, f = m['disp'].get(8, (None, None))
            if o is not None and f == 12:
                brut = np.frombuffer(mg, dtype=np.uint8, count=nv * m['pas'], offset=m['vb']).reshape(nv, m['pas'])
                col = np.ascontiguousarray(brut[:, o:o + 4]).tobytes()
            else:
                col = bytes([255]) * (4 * nv)
            uv0 = _attr(mg, m, 10, 2)
            if uv0 is None:
                uv0 = np.full((nv, 2), 0.5, np.float32)
            uvs = [uv0] + [(_attr(mg, m, t, 2) if _attr(mg, m, t, 2) is not None else uv0) for t in (11, 12, 13, 14, 15)]
            idx = np.frombuffer(mg, dtype='<u2', count=m['ni'], offset=m['ib']).copy()
            p['_fixe'] = (col, [np.ascontiguousarray(u, dtype=np.float32) for u in uvs], idx)
        return p['_fixe']


# registre : (quoi, code) -> Acteur, rempli par le serveur de l'Atelier quand la page charge un modèle (/api/modele)
ACTEURS = {}


def enregistrer(quoi, code, maillages, tab_sh):
    """maillages = sortie de moteur.modele.lire (+ '_md', '_mg', '_i', '_dossier', '_noms' ajoutés par le serveur)"""
    pieces = []
    mats_cache = {}
    for m in maillages:
        md = m['_md']
        k = id(md)
        if k not in mats_cache:
            mats_cache[k] = (materiaux(md, m['_noms'], tab_sh), maillages_md(md))
        mats, ent = mats_cache[k]
        e = ent[m['_i']]
        pieces.append({'md': md, 'mg': m['_mg'], 'm': e, 'os': np.asarray(m['os'], dtype=np.int64).reshape(-1, 4),
                       'poids': np.asarray(m['poids'], dtype=np.float64).reshape(-1, 4),
                       'mat': mats[e['mat']] if e['mat'] < len(mats) else None, 'dossier': m['_dossier'], 'noir': bool(m.get('noir')),
                       'nom': m['nom']})
    ACTEURS[(quoi, code or '')] = Acteur(pieces)


maillages_md = maillages
