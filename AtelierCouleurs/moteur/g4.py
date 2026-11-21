"""Lecture d'un objet d'effet de cinématique du jeu (common/effect/event/evNN/<obj>/<obj>.g4pkm + .g4mg, dx11/.../<obj>.g4tx).

Ce qui a été décodé (13/11/2026, sur ev60102000 / ev60102001 d'Impact lumineux) :
- le .g4pkm est un paquet de sections G4SK (squelette), G4MD (maillages + matériaux), G4MT (mouvements), G4MA (animations des
  matériaux), G4TP ;
- G4MD : u16 nombre de pièces à +0x20, u16 nombre de matériaux à +0x22, début des indices (dans le .g4mg) à +0x5C ;
  une entrée de 0x50 octets par pièce à partir de 0xA0 : (début des sommets, début des indices, nb sommets, nb indices) en 4 x u32,
  rang du nom à +0x38 (les noms `_NNN_...` sont rangés dans cet ordre), taille d'un sommet à +0x3E, index du MATÉRIAU à +0x43 ;
- après les pièces : les dispositions des sommets (8 octets par attribut, groupes fermés par type 0), puis une fiche de 16 octets
  par matériau : (shader u8, ?, ?, 8, nb_cases u16, ?, ?, début_case u16, ?, ?) -> les cases [début, début + nb[ ;
- les cases : 6 octets chacune, 5e octet = index dans la table des textures, 6e octet = 3 ;
- la table des textures : les crc32 des noms des textures du .g4tx, dans l'ordre utilisé par les cases ;
- sommet : position = 3 flottants à +0, couleur = 4 octets (RVBA) à +20.
"""
import os, re, struct, zlib, json, sys, colorsys

ICI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(ICI)), 'AtelierMaillots'))
from lib import images  # noqa: E402  (BC7 / DXT1, PNG)


def est_donnees(nom):
    """(15/11/2026) texture de DONNÉES (pas une couleur) des fausses particules : _parPos (positions), _parRotZ / _parRotZPat
    (rotations). _parColor = _ColorAnimeTex des shaders Effect_FakeParticle* : la COULEUR des particules au fil du temps (RVB ;
    alpha = taille) -> modifiable. Avant : tout nom contenant « _par » (parColor compris) était bloqué."""
    import re as _re
    return bool(_re.search(r'_par(Pos|RotZ|RotZPat)$', nom or ''))


class _G4TXNoms(images.G4TX):
    """(14/11/2026) même lecture que lib.images.G4TX (Atelier Maillots, NON modifié), mais les noms de textures peuvent
    contenir un point : les modèles de techniques chr/_waza/ev6x_xxxxx ont « ev62_00510_01.1 / .2 / .a » (le train de
    « Train fou ») ; avant, aucune texture n'était lue pour ces modèles (train, passage à niveau gris)."""
    def __init__(self, octets):
        super().__init__(octets)
        noms = [m.group()[:-1].decode() for m in re.finditer(rb'[a-z][a-z0-9_.]{3,40}\x00', self.b[:self.debut])]
        if len(noms) >= self.n:
            self.noms = noms[-self.n:]


images.G4TX = _G4TXNoms          # dans ce programme seulement (le fichier de l'Atelier Maillots ne change pas)


def sections(pk):
    out = []
    for m in re.finditer(rb'G4SK|G4MD|G4MT|G4MA|G4TP', pk):
        if m.start() % 16 == 0:
            out.append((m.group().decode(), m.start()))
    res = {}
    for k, (nom, o) in enumerate(out):
        fin = out[k + 1][1] if k + 1 < len(out) else len(pk)
        res.setdefault(nom, (o, fin))
    return res


def noms_textures_g4tx(tx):
    n = struct.unpack_from('<H', tx, 0x20)[0]
    total = struct.unpack_from('<I', tx, 0x2C)[0]
    deb = len(tx) - total
    # un nom peut commencer par un CHIFFRE (« 100060_25 ») : avant, il était sauté et toute la liste se décalait (77 fichiers)
    l = [m.group()[:-1].decode() for m in re.finditer(rb'[A-Za-z0-9][A-Za-z0-9_]{2,40}\x00', tx[:deb])][-n:]
    # (15/11/2026) noms avec un point (objets du jeu : « gi001_gom01.1 ») sautés ci-dessus -> en-tête G4TX (seulement dans ce cas)
    if len(l) < n:
        try:
            l2 = images.G4TX(tx).noms
            if len(l2) == n:
                return list(l2)
        except Exception:
            pass
    return l


def _decoder_rapide(bloc):
    """BC7 / DXT1 par moteur/natif/paquets.dll (même calcul que lib/images) ; None si la DLL manque"""
    try:
        import ctypes
        from moteur import paquets_jeu as _pj
        if _pj._DLL is None:
            return None
        h, w = struct.unpack_from('<II', bloc, 12)
        if bloc[84:88] == b'DX10':
            if struct.unpack_from('<I', bloc, 128)[0] not in (98, 99):
                return None
            deb, fmt = 148, 7
        else:
            deb, fmt = 128, 1
        src = bytes(bloc[deb:])
        out = ctypes.create_string_buffer(w * h * 4)
        if _pj._DLL.decoder_bc(src, len(src), w, h, fmt, out) != 0:
            return None
        raw = out.raw
        return w, h, [bytearray(raw[y * w * 4:(y + 1) * w * 4]) for y in range(h)]
    except Exception:
        return None


def decoder_texture(bloc):
    """DDS -> (w, h, rangées RGBA) ; BC7 / DXT1 par la bibliothèque, RGBA 32 bits non compressé ici ; None si autre format"""
    four = bloc[84:88]
    if four in (b'DX10', b'DXT1'):
        r = _decoder_rapide(bloc)
        if r:
            return r
        try:
            return images.decoder_dds(bloc)
        except Exception:
            return None
    h, w = struct.unpack_from('<II', bloc, 12)
    if four in (b'BC4U', b'ATI1'):                  # BC4 : un canal (masques « .a » des arbres) -> gris + alpha
        import numpy as np
        nb = ((w + 3) // 4) * ((h + 3) // 4)
        bl = np.frombuffer(bloc, dtype=np.uint8, count=nb * 8, offset=128).reshape(nb, 8)
        a0 = bl[:, 0].astype(np.int32); a1 = bl[:, 1].astype(np.int32)
        bits_ = np.zeros(nb, dtype=np.uint64)
        for k in range(6):
            bits_ |= bl[:, 2 + k].astype(np.uint64) << np.uint64(8 * k)
        ix = np.stack([((bits_ >> np.uint64(3 * i)) & np.uint64(7)).astype(np.int64) for i in range(16)], 1)
        pal = np.zeros((nb, 8), dtype=np.int32); pal[:, 0] = a0; pal[:, 1] = a1
        g = a0 > a1
        for i in range(1, 7):
            pal[:, i + 1] = np.where(g, ((7 - i) * a0 + i * a1) // 7, 0)
        for i in range(1, 5):
            pal[:, i + 1] = np.where(g, pal[:, i + 1], ((5 - i) * a0 + i * a1) // 5)
        pal[:, 6] = np.where(g, pal[:, 6], 0); pal[:, 7] = np.where(g, pal[:, 7], 255)
        v = np.take_along_axis(pal, ix, 1).astype(np.uint8)
        bw, bh = (w + 3) // 4, (h + 3) // 4
        img = v.reshape(bh, bw, 4, 4).transpose(0, 2, 1, 3).reshape(bh * 4, bw * 4)[:h, :w]
        rgba = np.repeat(img[:, :, None], 4, 2)
        return w, h, [bytearray(rgba[y].tobytes()) for y in range(h)]
    bits = struct.unpack_from('<I', bloc, 88)[0]
    if four == b'\0\0\0\0' and bits == 32:
        masques = struct.unpack_from('<4I', bloc, 92)
        dec = [(m.bit_length() - 8) if m else None for m in masques]
        raw = bloc[128:128 + w * h * 4]
        rows = []
        for y in range(h):
            row = bytearray(w * 4)
            for x in range(w):
                v = struct.unpack_from('<I', raw, (y * w + x) * 4)[0]
                row[x * 4:x * 4 + 4] = bytes(((v >> d) & 255) if d is not None else 255 for d in dec)
            rows.append(row)
        return w, h, rows
    return None


def resume_couleur(w, h, rows):
    """couleur moyenne des pixels visibles + part de pixels colorés + teinte dominante"""
    n = 0; s = [0, 0, 0]; colores = 0; teintes = []
    pas_y = max(1, h // 48); pas_x = max(1, w // 48)
    for y in range(0, h, pas_y):
        row = rows[y]
        for x in range(0, w, pas_x):
            r, g, b, a = row[x * 4:x * 4 + 4]
            if a < 20 or max(r, g, b) < 20:
                continue
            n += 1; s[0] += r; s[1] += g; s[2] += b
            hh, ss, vv = colorsys.rgb_to_hsv(r / 255, g / 255, b / 255)
            if ss > 0.25:
                colores += 1; teintes.append(hh * 360)
    teintes.sort()
    return {
        'moyenne': [round(c / max(n, 1)) for c in s],
        'colores': round(colores / max(n, 1), 3),
        'teinte': round(teintes[len(teintes) // 2]) if teintes else None,
    }


class ObjetEffet:
    def __init__(self, data_dir, chemin_objbin):
        """chemin_objbin : 'common/effect/event/ev60/ev60102000/ev60102000.objbin' (comme dans les .cfg.bin)"""
        rel = chemin_objbin.replace('\\', '/')
        if rel.startswith('common/'):
            rel = rel[len('common/'):]
        self.nom = os.path.basename(rel).rsplit('.', 1)[0]
        self.data_dir = data_dir
        self.dossier_rel = os.path.dirname(rel)                       # effect/event/ev60/ev60102000
        self.common = os.path.join(data_dir, 'common', *self.dossier_rel.split('/'))
        self.dx11 = os.path.join(data_dir, 'dx11', *self.dossier_rel.split('/'))
        self.pk = open(os.path.join(self.common, self.nom + '.g4pkm'), 'rb').read()
        self.mg = open(os.path.join(self.common, self.nom + '.g4mg'), 'rb').read()
        p_tx = os.path.join(self.dx11, self.nom + '.g4tx')
        self.tx = open(p_tx, 'rb').read() if os.path.exists(p_tx) else None
        self._lire()
        try:
            self.particules = self._lire_particules()
        except Exception as ex:          # (une erreur de lecture des particules ne doit pas empêcher l'effet de s'afficher)
            self.particules = {'emetteurs': [], 'erreur': str(ex)}
        try:
            self.lumieres = self._lire_lumieres()
        except Exception as ex:
            self.lumieres = {'erreur': str(ex)}

    # ------------------------------------------------------------------ lumières ponctuelles (lues dans nie.exe, 13/11/2026)
    def _lire_lumieres(self):
        """composants CCustomParamProperty (valeurs nommées), CCustomParamRefBone (valeurs prises sur un os) et
        CCustomPointLight (lumière = 2 valeurs : position + rayon, couleur). Voir Obsidian « Lumières ponctuelles - code du moteur »."""
        from . import particules as _pt
        p_obj = os.path.join(self.common, self.nom + '.objbin')
        if not os.path.exists(p_obj):
            return None
        params, refs, lums, sps = {}, [], [], []
        classe, cur = None, None
        for nom, vals in _pt.lire_brut(p_obj):
            if nom == 'PROP_INFO_BGN':
                classe = vals[0][1] if vals else None
            elif nom == 'PROP_INFO_END':
                classe = None
            elif nom == 'PROP_PARAM_BGN':
                cur = {}
            elif nom == 'PROP_PARAM_END' and cur is not None:
                if classe == 'CCustomParamProperty' and 'name' in cur:
                    params[str(zlib.crc32(cur['name'].encode()))] = (list(cur.get('param', [])) + [0, 0, 0, 0])[:4]
                elif classe == 'CCustomParamRefBone':
                    refs.append({k: cur.get(k, 0) for k in ('nameCrc', 'setType', 'objNameCrc', 'boneNameCrc', 'boneSpace', 'boneRefType')})
                elif classe == 'CCustomPointLight':
                    lums.append({k: cur.get(k, 0) for k in ('posParamCrc', 'colorParamCrc', 'type')})
                elif classe == 'CCustomShaderParam':
                    # (lu dans nie.exe 0x14057a7f0, 14/11/2026) : la valeur nommée refParamNameCrc est recopiée dans
                    # u_shaderParam[setShaderParamIdx] du matériau matNameCrc, composantes du masque refParamType
                    # (1 x, 2 y, 4 z, 8 w) ; nom 0 = rien n'est écrit
                    if cur.get('refParamNameCrc'):
                        sps.append({k: cur.get(k, 0) for k in ('matNameCrc', 'setShaderParamIdx', 'refParamNameCrc', 'refParamType')})
                cur = None
            elif nom == 'PROP_PARAM' and cur is not None and vals and vals[0][0] == 0:
                v = [x[1] for x in vals[1:]]
                if classe == 'CCustomParamProperty' and vals[0][1] == 'name':
                    cur['name'] = v[0]
                elif vals[0][1] == 'param':
                    cur['param'] = [float(x) for x in v]
                elif v:
                    cur[vals[0][1]] = (v[0] & 0xFFFFFFFF) if vals[0][1].endswith('Crc') else v[0]
        if not lums and not sps:
            return None
        return {'params': params, 'refs': refs, 'lumieres': lums, 'shader': sps}

    # ------------------------------------------------------------------ vraies particules (.ptlb, composant ParticleSetup)
    def _lire_particules(self):
        """émetteurs lus comme le jeu (moteur/particules.py) ; leurs textures rejoignent la liste de l'objet"""
        from . import particules as _pt, textures_ext as _tx, shaders as _sh
        p_obj = os.path.join(self.common, self.nom + '.objbin')
        if not os.path.exists(p_obj):
            return {'emetteurs': []}
        fichier, dans = None, False
        for nom, vals in _pt.lire_brut(p_obj):
            if nom == 'PROP_INFO_BGN':
                dans = bool(vals) and vals[0][1] == 'ParticleSetup'
            elif nom == 'PROP_INFO_END':
                dans = False
            elif dans and nom == 'PROP_PARAM' and len(vals) >= 2 and vals[0][1] == 'File':
                fichier = vals[1][1]
        if not fichier:
            return {'emetteurs': []}
        rel = fichier.replace('\\', '/')
        rel = rel[len('common/'):] if rel.startswith('common/') else rel
        chemin = os.path.join(self.data_dir, 'common', *rel.split('/'))
        if not os.path.exists(chemin):
            return {'emetteurs': [], 'erreur': 'fichier introuvable : ' + fichier}
        defs = _pt.lire(chemin)
        tab_sh = _sh.table(self.data_dir)
        for e in defs['emetteurs']:
            noms = []
            for pack, tex in e['materiau']['tex']:
                if not tex:
                    noms.append(None); continue
                if tex not in self.textures:
                    src = None
                    if pack and pack.startswith('#/'):          # paquet nommé : '#/effect/battle/common/effCmnTex/effCmnTex.g4tx'
                        rg = 'dx11/' + pack[2:]
                        try:
                            ns, table, deb = _tx._entete(os.path.join(self.data_dir, *rg.split('/')))
                            if tex in ns:
                                src = (rg, ns.index(tex))
                        except OSError:
                            pass
                    if src is None:
                        r = _tx.chercher(self.data_dir, os.path.join(os.path.dirname(os.path.dirname(__file__)), 'cache'),
                                         zlib.crc32(tex.encode()), 'dx11/' + self.dossier_rel)
                        if r:
                            src = (r[0], r[1])
                    if src:
                        self.src_ext[tex] = src; self.textures.append(tex)
                noms.append(tex if tex in self.textures else None)
            e['textures'] = noms
            sh = tab_sh.get(zlib.crc32((e['materiau']['shader'] or '').encode()))
            e['shader_ps'] = sh['ps'] if sh else (e['materiau']['shader'] or '')
            e['shader_vs'] = sh['vs'] if sh else (e['materiau']['shader'] or '')
        return defs

    # ------------------------------------------------------------------ G4MD
    def _lire(self):
        sec = sections(self.pk)
        a, b = sec['G4MD']
        md = self.md = self.pk[a:b]
        n = struct.unpack_from('<H', md, 0x20)[0]
        nmat = struct.unpack_from('<H', md, 0x22)[0]
        debut_ib = struct.unpack_from('<I', md, 0x5C)[0]
        entrees = [md[0xA0 + 0x50 * i: 0xA0 + 0x50 * (i + 1)] for i in range(n)]
        # NOM DE CHAQUE PIÈCE (corrigé le 14/11/2026) : u16 +0x38 de l'entrée = N° DE L'OS du squelette (G4SK) auquel la
        # pièce est collée ; nom = nom de cet os. Vérifié : Big Bang 98 / 98 identiques à l'ancienne recherche. Avant : textes
        # « _123_nom » cherchés dans le fichier et classés par ce champ — si un nom n'avait pas ce motif (Main céleste :
        # 74 trouvés pour 77 pièces), TOUS les noms étaient perdus et la main géante était collée au mauvais os.
        rang = [struct.unpack_from('<H', e, 0x38)[0] for e in entrees]
        nom_de = None
        try:
            from .anim import lire_g4sk
            os_sk = [o['nom'] for o in lire_g4sk(self.pk)]
            if all(r < len(os_sk) for r in rang):
                nom_de = {i: os_sk[rang[i]] for i in range(n)}
        except Exception:
            nom_de = None
        if nom_de is None:                               # sans squelette lisible : ancienne recherche
            noms = [m.decode() for m in re.findall(rb'_[0-9]{3}_[A-Za-z0-9_]+', md)]
            ordre = sorted(range(n), key=lambda i: rang[i])
            nom_de = {i: noms[r] for r, i in enumerate(ordre)} if len(noms) >= n else {i: 'piece_%03d' % i for i in range(n)}
        # dispositions puis fiches de matériaux
        q = 0xA0 + 0x50 * n
        self.dispositions = []; groupe = []
        while q + 8 <= len(md):
            t, o = md[q], md[q + 1]; f = struct.unpack_from('<I', md, q + 4)[0]
            if t > 16 or o > 80 or f > 0x40:
                break
            if t == 0:
                self.dispositions.append(groupe); groupe = []
            else:
                groupe.append((t, o, f))
            q += 8
        fiches = [struct.unpack_from('<4B6H', md, q + 16 * k) for k in range(nmat)]
        # textures : table des crc32 des noms
        self.textures = noms_textures_g4tx(self.tx) if self.tx else []
        crc_t = {zlib.crc32(t.encode()): t for t in self.textures}
        self.textures_ext = {}      # crc -> nom : textures prises dans le .g4tx d'un AUTRE effet (voir moteur/textures_ext.py)
        self.src_ext = {}           # nom -> (fichier .g4tx relatif, n° du bloc)
        nt = len(self.textures)
        table = []
        if nt:
            for i in range(0, len(md) - 4 * nt, 4):
                if all(struct.unpack_from('<I', md, i + 4 * j)[0] in crc_t for j in range(nt)):
                    table = [crc_t[struct.unpack_from('<I', md, i + 4 * j)[0]] for j in range(nt)]
                    pos_table = i
                    break
        # cases de texture : enregistrements de 6 octets [n° de texture, 3, …] (corrigé le 13/11/2026 : avant, le n° était
        # lu 4 octets plus loin, ce qui décalait d'une case quand les octets 2-5 ne sont pas nuls, cas des effets)
        cases = []
        if table:
            best = (0, 0)
            for s in range(q + 16 * nmat, pos_table):
                k = 0
                while s + 6 * k + 6 <= len(md) and md[s + 6 * k + 1] == 3 and md[s + 6 * k] < nt:
                    k += 1
                if k > best[1]:
                    best = (s, k)
            cases = [md[best[0] + 6 * k] for k in range(best[1])]
            # ancienne lecture (n° 4 octets plus loin, début = u16 +10) : gardée en secours pour les matériaux dont les
            # cases tombent après la fin de la liste (ev60014300 : 40 cases pour 92 demandées, suite introuvable)
            best2 = (0, 0)
            for s in range(q + 16 * nmat, pos_table):
                k = 0
                while s + 6 * k + 6 <= len(md) and md[s + 6 * k + 5] == 3 and md[s + 6 * k + 4] < nt:
                    k += 1
                if k > best2[1]:
                    best2 = (s, k)
            cases_ancien = [md[best2[0] + 6 * k + 4] for k in range(best2[1])]
        self.materiaux = []
        for f in fiches:
            nbc, debc = f[4], f[5]          # début des cases = u16 +6 (cumulatif ; corrigé le 13/11/2026, avant : +10)
            if cases and debc + nbc <= len(cases):
                texs = [table[cases[j]] for j in range(debc, debc + nbc)]
            else:                           # hors de la liste : ancienne lecture
                texs = [table[cases_ancien[j]] for j in range(f[7], f[7] + nbc) if j < len(cases_ancien)] if table else []
            self.materiaux.append({'shader': f[0], 'textures': texs})
        # LECTURE EXACTE par l'en-tête du G4MD (13/11/2026, d'après G4_Blender, vérifiée sur ev60014300) :
        # base = u16 +0x0A x 4 ; tables à base + u16 x 4 : +0x64 matériaux (8 x u16 chacun), +0x66 couleurs (12 flottants),
        # +0x68..+0x6A références de textures (6 octets : n° de texture, 3, …), +0x76 crc32 des textures (nb = u8 +0x27).
        # matériau : v0 = n° de couleur, v3 = début des références, v6 & 0xFF = nombre de textures.
        # couleur : [0:4] = couleur RVBA, [4] = gain additif (1 + valeur).
        try:
            base = struct.unpack_from('<H', md, 0x0A)[0] * 4
            off = lambda o: base + struct.unpack_from('<H', md, o)[0] * 4
            t_mat, t_col, t_ref, f_ref, t_crc = off(0x64), off(0x66), off(0x68), off(0x6A), off(0x76)
            ntex = md[0x27]
            # (avant : exigeait autant de textures dans le .g4tx que dans l'en-tête -> 4 500 matériaux sur 300 effets sans
            # lecture exacte ; maintenant une texture absente garde sa case sous le nom « ?<crc> »)
            if ntex and t_mat + 16 * nmat <= len(md) and t_crc + 4 * ntex <= len(md):
                crcs = [struct.unpack_from('<I', md, t_crc + 4 * j)[0] for j in range(ntex)]
                # textures absentes de notre .g4tx : cherchées dans les autres .g4tx d'effets (même dossier d'abord)
                if any(c not in crc_t for c in crcs):
                    from . import textures_ext as _tx
                    cache = os.path.join(os.path.dirname(ICI), 'cache')
                    dos = os.path.relpath(os.path.dirname(self.dx11), self.data_dir).replace(os.sep, '/')
                    for c in crcs:
                        if c not in crc_t:
                            r = _tx.chercher(self.data_dir, cache, c, dos)
                            if r and r[2] not in crc_t.values():
                                self.textures_ext[c] = r[2]
                                self.src_ext[r[2]] = (r[0], r[1])
                if sum(c in crc_t for c in crcs) * 2 >= len(crcs) or (self.textures_ext and all(c in crc_t or c in self.textures_ext for c in crcs)):
                    table2 = [crc_t.get(c) or self.textures_ext.get(c) or '?%08x' % c for c in crcs]
                    nref = (f_ref - t_ref) // 6
                    refs = [md[t_ref + 6 * j] for j in range(nref)]
                    # états de rendu : table +0x6C (jusqu'à +0x6E), fiches de 16 octets = 8 paires (clé, valeur) ;
                    # clé 0x0A = facteur de destination : 1 = additif, 5 = mélange normal ; 0x04 / 0x05 = test / écriture de profondeur.
                    # Le matériau choisit sa fiche par v2 / 8 (vérifié sur 600 effets)
                    t_et, f_et = off(0x6C), off(0x6E)
                    etats = [dict(zip(md[a:a + 16:2], md[a + 1:a + 16:2])) for a in range(t_et, f_et, 16)] if f_et > t_et else []   # la dernière fiche peut dépasser la fin de la table
                    # SHADERS DU JEU (13/11/2026, voir moteur/shaders.py) :
                    # - table +0x78..+0x7A = crc32 des noms de shaders ; matériau : v4 >> 8 = n° dans cette liste ;
                    # - table +0x6A..+0x6C = paramètres (vec4) : u_shaderParam0..7 du matériau = à partir du n° v1 ;
                    # - table +0x88..+0x8A = matrices de texture (u_texProj, 2 lignes de 4 flottants = 32 octets) :
                    #   case k du matériau = n° v7 + k ;
                    # - couleur (12 flottants) = u_diffuse (RVBA), u_ambient (x = intensité : RVB x (1 + x)), u_speculer.
                    from . import shaders as _sh
                    t_sh, f_sh = off(0x78), off(0x7A)
                    liste_sh = [struct.unpack_from('<I', md, a)[0] for a in range(t_sh, f_sh, 4)] if f_sh > t_sh else []
                    tab_sh = _sh.table(self.data_dir)
                    t_par, f_par = off(0x6A), off(0x6C)
                    t_tp, f_tp = off(0x88), off(0x8A)
                    for k in range(nmat):
                        v = struct.unpack_from('<8H', md, t_mat + 16 * k)
                        n, d = v[6] & 0xFF, v[3]
                        tx = [table2[refs[j]] for j in range(d, d + n) if j < nref and refs[j] < ntex]
                        c = struct.unpack_from('<12f', md, t_col + 48 * v[0]) if t_col + 48 * v[0] + 48 <= len(md) else None
                        self.materiaux[k]['textures'] = tx
                        # ADRESSAGE DES TEXTURES (13/11/2026, lu dans le code de nie.exe, fonction 0x140528eb0) : la table
                        # +0x6E..+0x70 est une liste de PAIRES d'octets (clé, valeur). Référence de texture (6 octets) :
                        # octet 1 = nombre de paires, u16 à +4 = première paire (compté en paires). Clés 1, 2, 3 = adressage
                        # U, V, W, converti par le tableau 00 01 02 03 05 04 du moteur ; clés 4, 5 = filtres.
                        # Valeurs (ordre Direct3D 11) : 1 répété, 2 miroir, 3 bloqué au bord, 4 bordure, 5 miroir une fois.
                        # Vérifié : quarts de disque sur carrés 0..2 -> 2 (miroir) ; grands fonds en mosaïque -> 1 (répété).
                        t_ad, f_ad = off(0x6E), off(0x70)
                        conv = (0, 1, 2, 3, 5, 4)
                        ad = []
                        for j in range(d, d + n):
                            if j < nref:
                                r_ = t_ref + 6 * j
                                cnt, o_ = md[r_ + 1], struct.unpack_from('<H', md, r_ + 4)[0]
                                pr_ = {md[t_ad + 2 * (o_ + q)]: md[t_ad + 2 * (o_ + q) + 1] for q in range(cnt)
                                       if t_ad + 2 * (o_ + q) + 2 <= f_ad}
                                # (14/11/2026) clé absente = état par défaut du moteur : octets +0x1141..+0x1143 du contexte = 3 (CLAMP),
                                # posés par 0x14049fa80 et lus par 0x1404a7560 (D3D11_SAMPLER_DESC.AddressU/V/W). Avant : 1 (WRAP), supposé.
                                ad.append([conv[pr_[1]] if 1 in pr_ and pr_[1] < 6 else 3, conv[pr_[2]] if 2 in pr_ and pr_[2] < 6 else 3])
                        self.materiaux[k]['adressage'] = ad
                        # (14/11/2026) fiche EXACTE du matériau : v2 = 1re paire, octet haut de v5 = nombre de paires (comme le
                        # moteur, 0x140528eb0). Avant : blocs fixes de 8 paires (v2 // 8), faux après une fiche de 5, 9 ou 10 paires.
                        _a, _n = t_et + 2 * v[2], v[5] >> 8
                        et = {md[_a + 2 * _j]: md[_a + 2 * _j + 1] for _j in range(_n) if _a + 2 * _j + 2 <= len(md)} if _n else None
                        # clé 0x06 = mélange activé (0 -> pièce OPAQUE : engrenages, rochers… ; vérifié sur ev60020900)
                        if et and et.get(0x06, 1) == 0:
                            self.materiaux[k]['melange'] = 'opaque'
                            self.materiaux[k]['ztest'] = bool(et.get(0x04, 1))
                            self.materiaux[k]['zecrit'] = bool(et.get(0x05, 1))
                        elif et and 0x0A in et:
                            # (14/11/2026) LU nie.exe 0x140528eb0 (traduction des paires au chargement, tables 0x141e7a920 /
                            # 0x141e7a968) : clé 6 -> mélange activé, 7 -> opération (table 0x141a73154 : 1 ADD, 5 REV_SUBTRACT),
                            # 9 / 0x0A -> facteurs source / destination (0 ZERO, 1 ONE, 4 SRC_ALPHA, 5 INV_SRC_ALPHA…)
                            self.materiaux[k]['melange'] = ('sous' if et.get(0x07) == 5 else 'add') if et[0x0A] == 1 else 'alpha'
                            self.materiaux[k]['ztest'] = bool(et.get(0x04, 1))
                            self.materiaux[k]['zecrit'] = bool(et.get(0x05, 0))
                        # clé 0x0E -> case 0x1B = CullMode (table 0x141a73140 : 0 -> NONE, 1 -> BACK ; FrontCounterClockwise = 1,
                        # 0x1404b83d0). 43 251 des 56 945 matériaux d'effets éliminent les faces arrière.
                        self.materiaux[k]['faces'] = 1 if (et and et.get(0x0E) == 1) else 0
                        # clé 0x0F -> case 0x1C : biais de profondeur (DepthBias = −valeur, plafond 15 ; LU 0x1404b83d0)
                        self.materiaux[k]['biais'] = int(et.get(0x0F, 0)) if et else 0
                        # (14/11/2026) COUCHE DE DESSIN : octet +8 de la fiche (v4 & 0xFF ; v4 >> 8 = shader). LU nie.exe 0x1405932c8 :
                        # n° de couche = base de l'objet (+0x101) + cet octet ; les étapes gmdCDrawObjModelPriority dessinent des plages
                        # de couches (0x140591cc0) : 0-24 avant le tone mapping, 25-49 = 40_Effect (après), 55-63 = étapes d'interface.
                        self.materiaux[k]['priorite'] = v[4] & 0xFF
                        # (14/11/2026) PIÈCE « PANNEAU » PAR MATÉRIAU : octet +0x0D de la fiche (v6 >> 8). LU nie.exe 0x140593632 :
                        # au dessin, si non nul, 0x140598bd0(monde de la pièce, mode, état de l'os, caméra) tourne la pièce vers la
                        # caméra ; modes 1 / 2 / 3 = mêmes formules que les os panneaux 0x14052a200 (vérifié dans l'émulateur,
                        # nie_outils/emu_panneau_mat.py, écart 0). Big Bang : 18 matériaux (lueurs e_light / i_light, anneaux).
                        self.materiaux[k]['panneau'] = (v[6] >> 8) & 0xFF
                        # (14/11/2026) SEUIL D'ALPHA (u_ubParam.w du tampon matériau), LU nie.exe 0x1405948f8 : -1 par défaut ;
                        # si la case d'état 1 (test d'alpha) est allumée : case 3 / 255 + 0,1 / 255. État par défaut du moteur
                        # (bloc +0xEA0 posé par 0x14049fa80) : case 1 = 1, case 3 = 0. -> 256 = test coupé, sinon la case 3.
                        _t1 = et.get(1, 1) if et else 1
                        self.materiaux[k]['seuil'] = (et.get(3, 0) if et else 0) if _t1 else 256
                        if c:
                            self.materiaux[k]['couleur'] = [round(x, 4) for x in c[:4]]
                            self.materiaux[k]['gain'] = round(1.0 + c[4], 4)
                            self.materiaux[k]['diffuse'] = [round(x, 5) for x in c[0:4]]
                            self.materiaux[k]['ambient'] = [round(x, 5) for x in c[4:8]]
                        i_sh = v[4] >> 8
                        if i_sh < len(liste_sh):
                            sh = tab_sh.get(liste_sh[i_sh])
                            self.materiaux[k]['shader_nom'] = sh['nom'] if sh else '%08x' % liste_sh[i_sh]
                            self.materiaux[k]['shader_ps'] = sh['ps'] if sh else ''
                        self.materiaux[k]['params'] = [[round(x, 5) for x in struct.unpack_from('<4f', md, t_par + 16 * (v[1] + j))]
                                                       for j in range(8) if t_par + 16 * (v[1] + j) + 16 <= f_par]
                        self.materiaux[k]['texproj'] = [[round(x, 5) for x in struct.unpack_from('<8f', md, t_tp + 32 * (v[7] + j))]
                                                        for j in range(n) if t_tp + 32 * (v[7] + j) + 32 <= f_tp]
            # les textures prises ailleurs rejoignent la liste (le navigateur les charge comme les autres)
            for nom in self.src_ext:
                if nom not in self.textures:
                    self.textures.append(nom)
        except (struct.error, IndexError):
            pass
        # noms des matériaux (affichage seulement : l'ordre peut être décalé)
        mn = []
        for m in re.finditer(rb'Effect_[A-Za-z0-9_]+', md):
            s = m.group().decode()
            if s not in mn:
                mn.append(s)
        for k, m in enumerate(self.materiaux):
            m['nom'] = mn[k] if k < len(mn) else 'materiau_%02d' % k
        # noms exacts : table des crc32 des noms de matériaux (même ordre que les fiches), si on la trouve
        crc_noms = {zlib.crc32(x.encode()): x for x in mn}          # seulement les noms de matériaux (Effect_...)
        for i in range(0, len(md) - 4 * nmat + 1, 4) if nmat else []:
            if all(struct.unpack_from('<I', md, i + 4 * j)[0] in crc_noms for j in range(nmat)):
                for j, m in enumerate(self.materiaux):
                    m['nom'] = crc_noms[struct.unpack_from('<I', md, i + 4 * j)[0]]
                break
        # LECTURE EXACTE (13/11/2026) : table +0x72..+0x74 de l'en-tête = crc32 du nom de chaque matériau, dans l'ordre des
        # fiches (vérifié : 72 / 72 sur Frappe stellaire, 18 / 18 sur Tir grenade). C'est ce crc que visent les animations
        # G4MA ; le nom en texte est retrouvé parmi les chaînes du fichier (« MA_whs0092_ef_04_alp », pas seulement « Effect_… »).
        try:
            base = struct.unpack_from('<H', md, 0x0A)[0] * 4
            a = base + struct.unpack_from('<H', md, 0x72)[0] * 4
            b = base + struct.unpack_from('<H', md, 0x74)[0] * 4
            if nmat and b - a == 4 * nmat and b <= len(md):
                cand = {zlib.crc32(x.group()): x.group().decode() for x in re.finditer(rb'[A-Za-z][A-Za-z0-9_]{3,60}', md)}
                for j, m in enumerate(self.materiaux):
                    c = struct.unpack_from('<I', md, a + 4 * j)[0]
                    m['crc'] = c
                    if c in cand:
                        m['nom'] = cand[c]
        except struct.error:
            pass
        # modèles de personnages (esprits guerriers, totems) : pas de cases trouvées -> le matériau k prend les textures
        # <code>_<k+1>0... (k002010 : 3 matériaux, textures _10*, _20*, _30*)
        if self.textures and not any(m['textures'] for m in self.materiaux):
            for k, m in enumerate(self.materiaux):
                pre = '%s_%d0' % (self.nom, k + 1)
                m['textures'] = [t for t in self.textures if t.startswith(pre) and not t[len(pre):len(pre) + 1].isdigit()]
                m['nom'] = 'partie_%d0' % (k + 1)
        self.pieces = []
        for i, e in enumerate(entrees):
            vb, ib, nv, ni = struct.unpack_from('<4I', e, 0)
            mat = e[0x43]
            # disposition des sommets : octet +0x42 = index dans les groupes (+1, le 1er groupe est vide) ;
            # UV (type 10) : format 2 = 2 flottants, 14 = 2 x u16 / 65535, 18 = 2 x s16 / 32767
            disp = self.dispositions[e[0x42] + 1] if e[0x42] + 1 < len(self.dispositions) else []
            uv = next(((o, f) for t, o, f in disp if t == 10), None)
            # jeux de coordonnées TEXCOORD1..4 = attributs de type 11..14 (les masques des shaders du jeu s'en servent)
            uvs = {t: (o, f) for t, o, f in disp if 11 <= t <= 15}
            col1 = next((o for t, o, f in disp if t == 9 and f == 12), None)     # COLOR1 (particules FakeParticle)
            nor = next((o for t, o, f in disp if t == 2 and f == 20), None)      # NORMAL : 4 x s16 / 32767 (reflets T1M1Rim)
            tan = next((o for t, o, f in disp if t == 3 and f == 20), None)      # TANGENT : 4 x s16 / 32767 (relief du Solid)
            # couleur des sommets : attribut de type 8 (format 12 = 4 octets RGBA) ; +20 pour les effets, +60 pour les personnages
            col = next((o for t, o, f in disp if t == 8 and f == 12), None)
            nom = nom_de[i]
            if nom.startswith('piece_') and mat < len(self.materiaux):
                nom = 'partie %d (%s)' % (i + 1, self.materiaux[mat]['nom'])
            self.pieces.append({'index': i, 'nom': nom, 'vb': vb, 'ib': debut_ib + ib, 'nv': nv, 'ni': ni,
                                'pas': e[0x3E], 'uv': uv, 'uvs': uvs, 'col1': col1, 'nor': nor, 'tan': tan, 'col': col, 'materiau': mat if mat < len(self.materiaux) else None})
        self._lire_peau(md, entrees)

    # ------------------------------------------------------------------ peau des maillages d'effets (14/11/2026)
    def _lire_peau(self, md, entrees):
        """Maillages à peau (main géante de la Main céleste…) : sommets avec poids (type 5) et n° d'os (type 6), comme les
        personnages (moteur/modele.py) : palette = u16 +0x3A (début) / u8 +0x3C (taille) de l'entrée, dans la table +0x82 de
        l'en-tête ; valeurs = n° dans la liste d'os du modèle (crc32, table +0x74) -> os du squelette G4SK. Le jeu les dessine
        avec la variante « _vb » du shader (u_mtxBone[] = cb8, 4 os par sommet). Vérifié sur ev63000100 : les sommets
        entourent leurs os au repos -> matrice de peau = monde animé de l'os x inverse du monde au repos."""
        try:
            from .anim import lire_g4sk
            from . import modele as _mo
            os_ = lire_g4sk(self.pk)
            nos = struct.unpack_from('<H', md, 0x24)[0]
            liste = _mo.table_os(md, nos, os_) if nos else None
            a, b = _mo._table(md, 0x82), _mo._table(md, 0x84)
        except Exception:
            return
        if not liste:
            return
        for p, e in zip(self.pieces, entrees):
            disp = self.dispositions[e[0x42] + 1] if e[0x42] + 1 < len(self.dispositions) else []
            d = {t: (o, f) for t, o, f in disp}
            s, c = struct.unpack_from('<H', e, 0x3A)[0], e[0x3C]
            if 5 in d and 6 in d and c and a + 2 * (s + c) <= b:
                pal = [liste[v] if v < len(liste) else 0 for v in struct.unpack_from('<%dH' % c, md, a + 2 * s)]
                p['peau'] = {'poids': d[5], 'os': d[6], 'palette': [os_[k]['nom'] for k in pal]}

    def peau(self, i):
        """(poids : 4 flottants, os : 4 n° DANS LA PALETTE) par sommet de la pièce i, ou None.
        Poids format 16 = 4 x u16 / 65535 (format 32 = 8 x u16) ; os format 8 = 4 x u8 (format 24 = 8 x u8) : les 4 premiers."""
        p = self.pieces[i]; pe = p.get('peau')
        if not pe or not p['nv']:
            return None
        (op, fp), (oo, fo) = pe['poids'], pe['os']
        poids, osv = [], []
        for k in range(p['nv']):
            o = p['vb'] + k * p['pas']
            poids.extend(v / 65535 for v in struct.unpack_from('<4H', self.mg, o + op))
            osv.extend(self.mg[o + oo:o + oo + 4])
        return poids, osv

    def normales(self, i, attr='nor'):
        """normales (ou tangentes : attr='tan') — 3 flottants par sommet, normalisés — de la pièce i, ou None"""
        p = self.pieces[i]
        if p.get(attr) is None:
            return None
        pos = self.geometrie(i)[0]
        out = []
        for k in range(len(pos) // 3):
            n = [x / 32767 for x in struct.unpack_from('<3h', self.mg, p['vb'] + k * p['pas'] + p[attr])]
            l = (n[0] * n[0] + n[1] * n[1] + n[2] * n[2]) ** 0.5 or 1
            out.extend(x / l for x in n)
        return out

    def couleur1(self, i):
        """COLOR1 (4 octets RVBA par sommet) de la pièce i, ou None"""
        p = self.pieces[i]
        if p.get('col1') is None:
            return None
        pos = self.geometrie(i)[0]
        return b''.join(self.mg[p['vb'] + k * p['pas'] + p['col1']:p['vb'] + k * p['pas'] + p['col1'] + 4] for k in range(len(pos) // 3))

    def uv_sup(self, i):
        """TEXCOORD1..5 de la pièce i (5 listes de flottants ; à défaut, TEXCOORD0)"""
        p = self.pieces[i]
        pos, col, idx, uv0 = self.geometrie(i)
        out = []
        for t in (11, 12, 13, 14, 15):
            o, f = p.get('uvs', {}).get(t, (None, None))
            if o is None or f not in (2, 14, 18) or not pos:
                out.append(uv0)
                continue
            uv = []
            for k in range(len(pos) // 3):
                a = p['vb'] + k * p['pas'] + o
                if f == 2:
                    uv.extend(struct.unpack_from('<2f', self.mg, a))
                elif f == 14:
                    uv.extend(x / 65535 for x in struct.unpack_from('<2H', self.mg, a))
                else:
                    uv.extend(x / 32767 for x in struct.unpack_from('<2h', self.mg, a))
            out.append(uv)
        return out

    def geometrie(self, i):
        """positions (liste de flottants), couleurs (RGBA 0-255), indices"""
        p = self.pieces[i]
        pas, vb, nv, ni = p['pas'], p['vb'], p['nv'], p['ni']
        # pièce vide ou hors du fichier : rien à dessiner. Pièce SANS indices (traits de vitesse ega0001, fausses
        # particules) : les sommets se lisent 3 par 3 (triangles à la suite)
        if not nv or pas < 12 or vb + nv * pas > len(self.mg) or (ni and p['ib'] + 2 * ni > len(self.mg)):
            return [], b'', [], []
        pos, col, uv = [], bytearray(), []
        uvo, uvf = p['uv'] if p.get('uv') else (None, None)
        for k in range(nv):
            o = vb + k * pas
            pos.extend(struct.unpack_from('<3f', self.mg, o))
            co = p.get('col')
            col.extend(self.mg[o + co:o + co + 4] if co is not None and co + 4 <= pas else b'\xff\xff\xff\xff')
            if uvf == 2:
                uv.extend(struct.unpack_from('<2f', self.mg, o + uvo))
            elif uvf == 14:
                uv.extend(x / 65535 for x in struct.unpack_from('<2H', self.mg, o + uvo))
            elif uvf == 18:
                uv.extend(x / 32767 for x in struct.unpack_from('<2h', self.mg, o + uvo))
            else:
                uv.extend((0.5, 0.5))
        idx = list(struct.unpack_from('<%dH' % ni, self.mg, p['ib'])) if ni else list(range(nv - nv % 3))
        if max(idx) >= nv or not all(abs(v) < 1e5 for v in pos):
            return [], b'', [], []
        return pos, bytes(col), idx, uv

    # ------------------------------------------------------------------ textures
    def extraire_textures(self, cache_dir):
        """PNG de chaque texture lisible dans cache_dir/<obj>/ ; renvoie {nom: info}"""
        d = os.path.join(cache_dir, self.nom)
        os.makedirs(d, exist_ok=True)
        f_info = os.path.join(d, '_infos.json')
        infos = json.load(open(f_info, encoding='utf-8')) if os.path.exists(f_info) else None
        if infos is not None and all(n in infos for n in self.src_ext):
            return infos
        if infos is None:
            infos = self._extraire_propres(d)
        from . import textures_ext as _tx
        for nom, (rel, k) in self.src_ext.items():                    # textures d'un autre effet
            if nom in infos:
                continue
            bl = _tx.bloc(self.data_dir, rel, k)
            r = decoder_texture(bl) if bl else None
            info = {'nom': nom, 'donnees': est_donnees(nom), 'lisible': r is not None, 'source': rel}
            if r:
                w, h, rows = r
                images.ecrire_png(os.path.join(d, nom + '.png'), w, h, rows)
                info.update({'w': w, 'h': h}, **resume_couleur(w, h, rows))
            infos[nom] = info
        json.dump(infos, open(f_info, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
        return infos

    def _extraire_propres(self, d):
        infos = {}
        if not self.tx:
            return infos
        g = images.G4TX(self.tx)
        propres = noms_textures_g4tx(self.tx)
        for k, nom in enumerate(propres):
            # cartes qui ne sont pas des couleurs : _parPos / _parRotZ(Pat) (effets), oc / sp / spm (ombrage, reflets des personnages)
            donnees = est_donnees(nom) or nom.endswith(('oc', 'sp', 'spm'))
            r = decoder_texture(g.blocs[k]) if k < len(g.blocs) else None
            info = {'nom': nom, 'donnees': donnees, 'lisible': r is not None}
            if r:
                w, h, rows = r
                images.ecrire_png(os.path.join(d, nom + '.png'), w, h, rows)
                info.update({'w': w, 'h': h}, **resume_couleur(w, h, rows))
            infos[nom] = info
        return infos


def decoder_png_bloc(args):
    """(15/11/2026) pour multiprocessing : (fichier .g4tx, n° d'image, PNG à écrire, copie partagée ou None) ; renvoie le PNG ou None"""
    import shutil
    src, k, f, partage = args
    try:
        g = images.G4TX(open(src, 'rb').read())
        r = decoder_texture(g.blocs[k])
    except Exception:
        return None
    if not r:
        return None
    images.ecrire_png(f, *r)
    if partage:
        os.makedirs(os.path.dirname(partage), exist_ok=True)
        shutil.copyfile(f, partage)
    return f
