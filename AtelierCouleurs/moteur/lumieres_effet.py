"""(23/11/2026, muku : « je veux tout modifier », choix « intensité seulement ») INTENSITÉ DES LUMIÈRES PONCTUELLES d'un objet
d'effet (celles qui éclairent les joueurs et le stade pendant la cinématique).

LU (Main céleste tigrée, objet ev63100700 ; moteur : nie.exe CCustomPointLight 0x140f77df0, CCustomParamRefBone 0x14057be20) :
- objbin : CCustomPointLight -> colorParamCrc (valeur nommée) ; CCustomParamRefBone nameCrc = cette valeur, boneRefType >> 4 = 2
  (ÉCHELLE de l'os boneNameCrc), masque & 15 (composantes x y z -> r v b) ;
- animation (.g4pkm, section G4MT) : pistes d'échelle de cet os, types 1 / 2 / 3 = x / y / z. Ex. : x (rouge) codec 2 sur
  16 bits, échelle n° 38 = 7,3 ; y (vert) échelle n° 39 = 5,5 ; z (bleu) = 0 (octet brut partagé avec 1 060 canaux).
VRFW n'a pas de réglage pour ces lumières : l'Atelier change l'animation SUR PLACE (même taille de fichier) :
- piste quantifiée (codec 2 / 3) : son échelle (table des échelles) × k, si cette échelle ne sert qu'aux pistes de la lumière ;
- piste en flottants (codec 1, 4 octets) : ses valeurs × k, si ses octets ne servent qu'à elle ;
- sinon (valeur partagée, entiers bruts) : laissée, et dit. Une valeur 0 reste 0 (pas de bleu ajouté : « intensité seulement »).
"""
import os, struct, zlib


def lumieres_objet(objbin):
    """-> [{'os': crc de l'os, 'composantes': masque xyz}] : os dont l'échelle donne la couleur d'une lumière ponctuelle"""
    from . import particules as _pt
    refs, lums, classe, cur = [], [], None, None
    for nom, vals in _pt.lire_brut(objbin):
        if nom == 'PROP_INFO_BGN':
            classe = vals[0][1] if vals else None
        elif nom == 'PROP_INFO_END':
            classe = None
        elif nom == 'PROP_PARAM_BGN':
            cur = {}
        elif nom == 'PROP_PARAM_END' and cur is not None:
            if classe == 'CCustomParamRefBone':
                refs.append(cur)
            elif classe == 'CCustomPointLight':
                lums.append(cur)
            cur = None
        elif nom == 'PROP_PARAM' and cur is not None and vals and vals[0][0] == 0 and len(vals) > 1:
            cur[vals[0][1]] = vals[1][1]
    out = []
    for l in lums:
        c = l.get('colorParamCrc', 0) & 0xFFFFFFFF
        for r in refs:
            if (r.get('nameCrc', 0) & 0xFFFFFFFF) == c and (int(r.get('boneRefType', 0)) >> 4) == 2:
                out.append({'os': int(r.get('boneNameCrc', 0)) & 0xFFFFFFFF, 'composantes': int(r.get('boneRefType', 0)) & 15})
    return out


def _g4mt(b):
    """position et tables de la section G4MT (même lecture que anim.lire_g4mt)"""
    a = b.find(b'G4MT')
    if a < 0:
        return None
    hw = struct.unpack_from('<H', b, a + 0x0A)[0]
    s0 = a
    nclips, ncibles = struct.unpack_from('<HH', b, s0 + 0x20)
    u_ti, u_ch, u_ech, u_hclip, u_hcib, u_noms, u_cles, u_data = struct.unpack_from('<8H', b, s0 + 0x24)
    sh = b[s0 + 0x36]
    T = {'a': a, 'nclips': nclips, 'o_ti': (hw + (u_ti << sh)) * 4, 'o_ch': (hw + (u_ch << sh)) * 4,
         'o_ech': (hw + u_ech) * 4, 'o_hclip': (hw + u_hclip) * 4, 'o_hcib': (hw + u_hcib) * 4,
         'o_data': (hw + (u_data << (2 * sh))) * 4}
    T['cibles'] = struct.unpack_from('<%dI' % ncibles, b, s0 + T['o_hcib'])
    T['nech'] = (T['o_hclip'] - T['o_ech']) // 4
    return T


def canaux(b, T):
    """tous les canaux : (clip, crc de la cible, type, codec, variante, nb de composantes, pas, n° d'échelle, n° 1re donnée, nb de clés, offset du canal)"""
    s0, out = T['a'], []
    for c in range(T['nclips']):
        deb, fin, ti0, nti, drap, fps, ti_haut = struct.unpack_from('<HHHHBBB', b, s0 + 0x40 + 16 * c)
        ti0 += ti_haut << 16
        for t in range(ti0, ti0 + nti):
            ic, ch0, nch, ch_haut, _ = struct.unpack_from('<HHBBH', b, s0 + T['o_ti'] + 8 * t)
            ch0 += ch_haut << 16
            for k in range(ch0, ch0 + nch):
                o = s0 + T['o_ch'] + 20 * k
                typ, codec, interp, var, nc, pas, iech, prm = b[o:o + 8]
                k0, d0, nk = struct.unpack_from('<III', b, o + 8)
                out.append((c, T['cibles'][ic], typ, codec, var, nc, pas, iech, d0, nk, o))
    return out


def regler_intensite(b, os_couleur, k):
    """b : octets du .g4pkm ; os_couleur : crc des os de couleur ; k : facteur (0 = éteinte, 1 = comme le jeu, 2 = double).
    -> (nouveaux octets, rapport). Taille inchangée."""
    T = _g4mt(b)
    if T is None:
        return b, ['pas de section G4MT : rien changé']
    b = bytearray(b)
    tous = canaux(b, T)
    cible = [x for x in tous if (x[1] & 0xFFFFFFFF) in os_couleur and x[2] in (1, 2, 3)]
    autres = [x for x in tous if x not in cible]
    rapport, faits_ech = [], set()
    ech_autres = {x[7] for x in autres if x[3] in (2, 3)}
    for (c, crc, typ, codec, var, nc, pas, iech, d0, nk, o) in cible:
        if codec in (2, 3):
            if iech in ech_autres:
                rapport.append('os %08X canal %d : échelle n° %d partagée avec d\'autres pistes -> laissée' % (crc, typ, iech)); continue
            if iech >= T['nech']:
                continue
            if iech not in faits_ech:
                p = T['a'] + T['o_ech'] + 4 * iech
                v = struct.unpack_from('<f', b, p)[0]
                struct.pack_into('<f', b, p, v * k)
                faits_ech.add(iech)
        elif codec == 1 and var == 4:
            zone = (d0, d0 + pas * nk)
            if any(x[8] < zone[1] and x[8] + max(1, x[6]) * x[9] > zone[0] for x in autres if x[3] == 1):
                rapport.append('os %08X canal %d : valeurs partagées avec d\'autres pistes -> laissées' % (crc, typ)); continue
            for j in range(nk):
                for q in range(nc):
                    p = T['a'] + T['o_data'] + d0 + j * pas + 4 * q
                    struct.pack_into('<f', b, p, struct.unpack_from('<f', b, p)[0] * k)
        else:
            # entiers bruts (souvent la constante 0 partagée : une composante éteinte) : rien à multiplier
            pass
    rapport.insert(0, '%d piste(s) de couleur de lumière, %d échelle(s) × %.2f' % (len(cible), len(faits_ech), k))
    return bytes(b), rapport


def renommer_paquet(b, ancien, neuf):
    """.g4pkm : noms des sections (« <stem>.g4sk »…) renommés (même longueur), leurs crc32 et l'index trié par crc refaits
    (LU sur une copie faite par VRFW : ev60008300 -> ev60891000, seuls ces octets de l'en-tête changent)"""
    assert len(ancien) == len(neuf)
    b = bytearray(b)
    n = struct.unpack_from('<I', b, 0x20)[0]                  # nombre de noms (5 : g4sk g4md g4mt g4ma g4tp)
    # table : n crc32 (u32) puis n index (u16), puis les décalages (u16) des noms, puis les noms
    o_crc = 0x68
    noms_o = []
    p = b.find(ancien.encode(), o_crc)
    for _ in range(n):
        if p < 0:
            break
        fin = b.index(b'\0', p)
        noms_o.append((p, b[p:fin].decode()))
        p = b.find(ancien.encode(), fin)
    if len(noms_o) != n:
        raise ValueError('noms du paquet introuvables (%d / %d)' % (len(noms_o), n))
    for p, nom in noms_o:
        b[p:p + len(nom)] = nom.replace(ancien, neuf).encode()
    crcs = [zlib.crc32(nom.replace(ancien, neuf).encode()) for _, nom in noms_o]
    for i, c in enumerate(crcs):
        struct.pack_into('<I', b, o_crc + 4 * i, c)
    ordre = sorted(range(n), key=lambda i: crcs[i])
    for i, x in enumerate(ordre):
        struct.pack_into('<H', b, o_crc + 4 * n + 2 * i, x)
    return bytes(b)
