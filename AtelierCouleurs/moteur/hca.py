"""(22/11/2026) Décodeur HCA (CRI) à nous, sans rien installer (muku : « le mieux serait de rien faire installer »).
Retour de muku : musique « énormément saturée ». ffmpeg 8.1 lit mal les HCA v3 du jeu : chaque bloc de 1024 échantillons
décodé SANS le bloc d'avant (vérifié : un bloc décodé seul = le même bloc dans le morceau, à l'échantillon près), et
ses coefficients ne correspondent à rien (aucune relation linéaire avec ceux lus ici, à aucun décalage) : le timbre
d'ensemble est juste (facteurs d'échelle lus d'abord), le détail est brouillé = saturation.

VÉRIFIÉ ici, sans référence extérieure (thème titre, 2962 blocs) :
- lecture des bits : 2373 blocs finissent à moins de 8 bits de leur fin, aucun ne déborde (une lecture fausse dérive) ;
- transformée : IMDCT standard (phase N/2) + fenêtre de Kaiser-Bessel dérivée alpha 4, choisie sur des critères
  physiques : jointures invisibles (1,009), niveau plat dans les 128 échantillons (±1,8 % ; alpha 3 : 6 %, alpha 5 : 4 %),
  rien au-dessus de 18 kHz ; normalisation 1/8 (orthonormée) ; même chronologie que ffmpeg (points de boucle valables).

Format (référence : clHCA de vgmstream) : en-tête de blocs « fmt » « comp » « loop » « ciph »…, puis des blocs de
taille fixe : 0xFFFF, niveau de bruit (9 bits), limite (7 bits), par canal : facteurs d'échelle (delta), résolutions
calculées, puis 8 sous-trames de 128 coefficients (codes à longueur variable), IMDCT 256 points, fenêtre,
recouvrement de 128 échantillons — gardé d'un bloc au suivant (c'est ce qu'oublie ffmpeg).

Pris en charge : non chiffré (ciph 0), sans bandes stéréo d'intensité ni HFR (tous les sons vus du jeu : bgm_title,
waza_stream, common, effect). Sinon : NonPris -> l'appelant garde ffmpeg.
"""
import struct, math
import numpy as np


class NonPris(Exception):
    pass


# ------------------------------------------------------------------ tables (clHCA)
MAX_BITS = [0, 2, 3, 3, 4, 4, 4, 4, 5, 6, 7, 8, 9, 10, 11, 12]
LUS_BITS = [0] * 16 + [1, 1, 2, 2] + [0] * 12 + [2, 2, 2, 2, 2, 2, 3, 3] + [0] * 8 + [2, 2, 3, 3, 3, 3, 3, 3] + [0] * 8 + \
    [3] * 14 + [4, 4] + [3] * 10 + [4] * 6 + [3] * 6 + [4] * 10 + [3, 3] + [4] * 14
VALEURS = [0] * 16 + [0, 0, 1, -1] + [0] * 12 + [0, 0, 1, 1, -1, -1, 2, -2] + [0] * 8 + [0, 0, 1, -1, 2, -2, 3, -3] + [0] * 8 + \
    [0, 0, 1, 1, -1, -1, 2, 2, -2, -2, 3, 3, -3, -3, 4, -4] + [0, 0, 1, 1, -1, -1, 2, 2, -2, -2, 3, -3, 4, -4, 5, -5] + \
    [0, 0, 1, 1, -1, -1, 2, -2, 3, -3, 4, -4, 5, -5, 6, -6] + [0, 0, 1, -1, 2, -2, 3, -3, 4, -4, 5, -5, 6, -6, 7, -7]
INVERSE = [14, 14, 14, 14, 14, 14, 13, 13, 13, 13, 13, 13, 12, 12, 12, 12, 12, 12, 11, 11, 11, 11, 11, 11, 10, 10, 10, 10,
           10, 10, 10, 9, 9, 9, 9, 9, 9, 8, 8, 8, 8, 8, 8, 7, 6, 6, 5, 4, 4, 4, 3, 3, 3, 2, 2, 2, 2, 1, 1, 1, 1, 1, 1, 1, 1, 1]
PAS = [0.0] + [2.0 / (2 * r + 1) for r in range(1, 8)] + [2.0 / ((1 << (r - 3)) - 1) for r in range(8, 16)]
# 2/3, 2/5 … 2/15 (tables de codes), puis 2/31, 2/63 … 2/4095 (codes signe + grandeur)
ECHELLE = [math.sqrt(128) * 2 ** ((i - 63) * 53 / 128) for i in range(64)]
CONVERSION = [0.0, 0.0] + [2 ** ((i - 64) * 53 / 128) for i in range(2, 128)]


def entete(h):
    if h[:4] != b'HCA\0':
        raise NonPris('pas un HCA')
    v, taille = struct.unpack_from('>HH', h, 4)
    e = {'version': v, 'taille': taille, 'ciph': 0, 'ath': 1 if v < 0x200 else 0, 'boucle': None}
    o = 8
    while o < taille:
        nom = bytes(c & 0x7F for c in h[o:o + 4])
        if nom == b'fmt\0':
            e['canaux'] = h[o + 4]; e['freq'] = int.from_bytes(h[o + 5:o + 8], 'big')
            e['blocs'], e['retard'], e['bourrage'] = struct.unpack_from('>IHH', h, o + 8); o += 16
        elif nom == b'comp':
            (e['bloc'],) = struct.unpack_from('>H', h, o + 4)
            e['res_min'], e['res_max'], e['pistes'], e['config'], e['bandes'], e['base'], e['stereo'], e['hfr'] = h[o + 6:o + 14]
            o += 16
        elif nom == b'dec\0':
            raise NonPris('ancien en-tête dec')
        elif nom == b'loop':
            e['boucle'] = struct.unpack_from('>IIHH', h, o + 4); o += 16
        elif nom == b'ath\0':
            e['ath'] = struct.unpack_from('>H', h, o + 4)[0]; o += 6
        elif nom == b'ciph':
            e['ciph'] = struct.unpack_from('>H', h, o + 4)[0]; o += 6
        elif nom == b'rva\0':
            e['volume'] = struct.unpack_from('>f', h, o + 4)[0]; o += 8
        elif nom == b'vbr\0':
            raise NonPris('débit variable')
        elif nom == b'comm':
            o += 5 + h[o + 4]
        else:
            break
    if e['ciph'] != 0:
        raise NonPris('HCA chiffré')
    if e['stereo'] or e['hfr'] or e['ath'] != 0:
        raise NonPris('bandes stéréo / HFR / ATH : non pris en charge')
    return e


def _imdct():
    n = np.arange(256)[:, None] + 0.5 + 64
    k = np.arange(128)[None, :] + 0.5
    return np.cos(np.pi / 128 * n * k)


def spectres(h, e=None, classes=None):
    """coefficients dé-quantifiés : tableau (blocs, canaux, 8, 128) + nombre de bits lus par bloc (contrôle).
    classes : tableau int8 de même forme, rempli si donné (1 = table de codes, 2 = signe + grandeur, 3 = bruit)"""
    e = e or entete(h)
    nc, nb, tb, base = e['canaux'], e['blocs'], e['bloc'], e['base']
    S = np.zeros((nb, nc, 8, 128), np.float64)
    lus = []
    hasard = 1
    for b in range(nb):
        blk = h[e['taille'] + b * tb:e['taille'] + (b + 1) * tb]
        x = int.from_bytes(blk, 'big'); nbits = tb * 8
        pos = 0

        def lire(n):
            nonlocal pos
            if n == 0:
                return 0
            v = (x >> (nbits - pos - n)) & ((1 << n) - 1); pos += n
            return v
        if lire(16) != 0xFFFF:
            raise ValueError('bloc %d : pas de synchro' % b)
        bruit = lire(9); limite = lire(7)
        packed = (bruit << 8) - limite
        cans = []
        for c in range(nc):
            delta = lire(3)
            sf = [0] * base
            if delta >= 6:
                sf = [lire(6) for _ in range(base)]
            elif delta > 0:
                attendu = (1 << delta) - 1; extra = attendu >> 1
                p = lire(6); sf[0] = p
                for i in range(1, base):
                    d = lire(delta)
                    p = p + d - extra if d != attendu else lire(6)
                    sf[i] = p
            res = [0] * base; bruits, valides = [], []
            for i in range(base):
                if sf[i] > 0:
                    pos_c = ((packed + i) >> 8) + 1 - ((5 * sf[i]) >> 1)
                    r = 15 if pos_c < 0 else (INVERSE[pos_c] if pos_c <= 65 else 0)
                    r = max(e['res_min'], min(e['res_max'], r))
                    (bruits if r < 1 else valides).append(i)
                    res[i] = r
            gain = [ECHELLE[sf[i]] * PAS[res[i]] if 0 <= sf[i] < 64 else 0.0 for i in range(base)]
            cans.append((sf, res, gain, bruits, valides))
        for s in range(8):
            for c in range(nc):
                sf, res, gain, bruits, valides = cans[c]
                ligne = S[b, c, s]
                for i in range(base):
                    r = res[i]
                    if r == 0:
                        continue
                    nbit = MAX_BITS[r]; code = lire(nbit)
                    if r > 7:
                        q = (1 - ((code & 1) << 1)) * (code >> 1)
                        if q == 0:
                            pos -= 1
                    else:
                        j = (r << 4) + code
                        pos += LUS_BITS[j] - nbit
                        q = VALEURS[j]
                    ligne[i] = gain[i] * q
                    if classes is not None:
                        classes[b, c, s, i] = 2 if r > 7 else 1
                # bruit (v3, résolution minimale 0) : bandes sans bits = copie d'une bande codée au hasard, mise à l'échelle
                if e['res_min'] == 0 and valides and bruits:
                    for i in bruits:
                        hasard = (0x343FD * hasard + 0x269EC3) & 0xFFFFFFFF
                        v = valides[(((hasard & 0x7FFF) * len(valides)) >> 15)]
                        k = sf[i] - sf[v] + 62
                        ligne[i] = CONVERSION[k if k > 0 else 0] * ligne[v]
                        if classes is not None:
                            classes[b, c, s, i] = 3
        lus.append(pos)
    return S, lus


def fenetre(nom='kbd'):
    """fenêtre de 256 points (moitié montante utilisée deux fois)"""
    n = np.arange(256)
    if nom == 'sinus':
        return np.sin(np.pi * (n + 0.5) / 256)
    if nom == 'vorbis':
        return np.sin(np.pi / 2 * np.sin(np.pi * (n + 0.5) / 256) ** 2)
    # Kaiser-Bessel dérivée, alpha 4
    alpha = 4.0
    k = np.kaiser(129, np.pi * alpha)
    c = np.cumsum(k[:128]); w = np.sqrt(c / k.sum())
    return np.concatenate([w, w[::-1]])


def decoder(h, nom_fenetre='kbd', echelle=0.125):
    """-> (échantillons float32 (n, canaux), entête)"""
    e = entete(h)
    S, _ = spectres(h, e)
    nb, nc = S.shape[:2]
    C = _imdct(); w = fenetre(nom_fenetre)
    out = np.zeros((nb * 1024, nc), np.float32)
    for c in range(nc):
        X = S[:, c].reshape(-1, 128).T                     # (128, nb*8)
        Y = (C @ X).T * w * echelle                        # (nb*8, 256)
        sor = np.empty((Y.shape[0], 128))
        sor[:] = Y[:, :128]
        sor[1:] += Y[:-1, 128:]
        out[:, c] = sor.reshape(-1)
    return out, e
