"""Textures communes des personnages du jeu : dx11/chr/shader/texture/chr_tex.g4tx (13/11/2026).

Lu dans nie.exe 0x140f9e990 : le moteur cherche 4 noms dans ce paquet (dichotomie 0x14052f1e0 sur les CRC32 des noms)
et les range dans l'objet de scène :
    +0x30A0 / +0x30F0  edgeTone01   (CRC 0x416ba845)
    +0x30A8 / +0x30F2  chrGrd_01    (CRC 0x376d65a8) -> t7 « in_texGrd » des shaders chr_toon* (0x14132c750 / 0x14132c7e0)
    +0x30B0 / +0x30F4  water_01     (CRC 0x07598008)
    +0x30B8 / +0x30F6  foot_01      (CRC 0x9aef933d)
Le paquet : 4 images (chrGrd_01 512 x 256 DXT5, edgeTone01 128 x 64 RGBA, foot 260 x 128 DXT1, water_01 128 x 128 DXT1),
6 noms (foot_01 / foot_02 = morceaux de « foot »).
Les images sont décodées une fois en PNG dans le cache de l'Atelier (cache/systeme/chr_tex/<nom>.png).
"""
import os, struct
import numpy as np


def _dxt5(bl, w, h):
    """DDS DXT5 (BC3) niveau 0 -> tableau h x w x 4 (octets)"""
    nb = ((w + 3) // 4) * ((h + 3) // 4)
    blocs = np.frombuffer(bl, dtype=np.uint8, count=nb * 16, offset=128).reshape(nb, 16)
    # alpha
    a0 = blocs[:, 0].astype(np.int32); a1 = blocs[:, 1].astype(np.int32)
    bits = np.zeros(nb, dtype=np.uint64)
    for k in range(6):
        bits |= blocs[:, 2 + k].astype(np.uint64) << np.uint64(8 * k)
    idx_a = np.stack([((bits >> np.uint64(3 * i)) & np.uint64(7)).astype(np.int32) for i in range(16)], 1)
    pal_a = np.zeros((nb, 8), dtype=np.int32)
    pal_a[:, 0] = a0; pal_a[:, 1] = a1
    grand = a0 > a1
    for i in range(1, 7):
        pal_a[:, i + 1] = np.where(grand, ((7 - i) * a0 + i * a1) // 7, 0)
    for i in range(1, 5):
        pal_a[:, i + 1] = np.where(grand, pal_a[:, i + 1], ((5 - i) * a0 + i * a1) // 5)
    pal_a[:, 6] = np.where(grand, pal_a[:, 6], 0); pal_a[:, 7] = np.where(grand, pal_a[:, 7], 255)
    alpha = np.take_along_axis(pal_a, idx_a, 1)
    # couleur (comme BC1, toujours 4 couleurs)
    c0 = blocs[:, 8].astype(np.int32) | (blocs[:, 9].astype(np.int32) << 8)
    c1 = blocs[:, 10].astype(np.int32) | (blocs[:, 11].astype(np.int32) << 8)
    def rgb(c):
        r = (c >> 11) & 31; g = (c >> 5) & 63; b = c & 31
        return np.stack([(r * 255 + 15) // 31, (g * 255 + 31) // 63, (b * 255 + 15) // 31], 1)
    p0, p1 = rgb(c0), rgb(c1)
    pal = np.stack([p0, p1, (2 * p0 + p1) // 3, (p0 + 2 * p1) // 3], 1)          # nb x 4 x 3
    ib = blocs[:, 12].astype(np.uint32) | (blocs[:, 13].astype(np.uint32) << 8) | (blocs[:, 14].astype(np.uint32) << 16) | (blocs[:, 15].astype(np.uint32) << 24)
    idx_c = np.stack([((ib >> np.uint32(2 * i)) & np.uint32(3)).astype(np.int64) for i in range(16)], 1)
    col = np.take_along_axis(pal, idx_c[:, :, None].repeat(3, 2), 1)                # nb x 16 x 3
    px = np.concatenate([col, alpha[:, :, None]], 2).astype(np.uint8)              # nb x 16 x 4
    bw, bh = (w + 3) // 4, (h + 3) // 4
    img = px.reshape(bh, bw, 4, 4, 4).transpose(0, 2, 1, 3, 4).reshape(bh * 4, bw * 4, 4)
    return img[:h, :w]


def _brut32(bl, w, h):
    masques = struct.unpack_from('<4I', bl, 92)
    v = np.frombuffer(bl, dtype='<u4', count=w * h, offset=128).reshape(h, w)
    out = np.zeros((h, w, 4), dtype=np.uint8)
    for k, m in enumerate(masques):
        out[:, :, k] = ((v >> (m.bit_length() - 8)) & 255) if m else 255
    return out


def lire_paquet(chemin):
    """chr_tex.g4tx -> {nom: tableau h x w x 4} (images entières seulement)"""
    b = open(chemin, 'rb').read()
    nimg = struct.unpack_from('<H', b, 0x20)[0]; nn = b[0x22]
    base = struct.unpack_from('<H', b, 10)[0]
    tab = (struct.unpack_from('<H', b, 0x46)[0] + base) * 4          # table des noms : décalages 16 bits depuis la table
    noms = []
    for k in range(nn):
        o = tab + struct.unpack_from('<H', b, tab + 2 * k)[0]
        noms.append(b[o:b.index(b'\0', o)].decode('ascii'))
    total = struct.unpack_from('<I', b, 0x2C)[0]; debut = len(b) - total
    out = {}
    for k in range(nimg):
        e = 0x60 + k * 0x30
        off, t = struct.unpack_from('<II', b, e + 4)
        bl = b[debut + off:debut + off + t]
        h, w = struct.unpack_from('<II', bl, 12)
        four = bl[84:88]
        if four == b'DXT5':
            out[noms[k]] = _dxt5(bl, w, h)
        elif four == b'\0\0\0\0' and struct.unpack_from('<I', bl, 88)[0] == 32:
            out[noms[k]] = _brut32(bl, w, h)
    return out


def preparer(data_dir, cache, ecrire_png):
    """écrit cache/systeme/chr_tex/<nom>.png (une fois) ; renvoie le dossier"""
    dos = os.path.join(cache, 'systeme', 'chr_tex')
    if os.path.exists(os.path.join(dos, 'chrGrd_01.png')):
        return dos
    os.makedirs(dos, exist_ok=True)
    for nom, img in lire_paquet(os.path.join(data_dir, 'dx11', 'chr', 'shader', 'texture', 'chr_tex.g4tx')).items():
        h, w = img.shape[:2]
        ecrire_png(os.path.join(dos, nom + '.png'), w, h, [bytes(img[y].tobytes()) for y in range(h)])
    return dos
