"""Retouches rapides sur les images des maillots (lignes RGBA en bytearray), sans bibliothèque :
réduction pour l'affichage, remplacement de couleur (ombres gardées), logo, PNG en mémoire pour Tk."""
import struct, zlib, base64
import tkinter
from . import images


def copie(rows):
    return [bytearray(r) for r in rows]


def reduire(w, h, rows, taille_max):
    """réduction rapide (un pixel sur n) pour l'affichage"""
    n = max(1, -(-max(w, h) // taille_max))
    out = []
    for y in range(0, h, n):
        mv = memoryview(rows[y]).cast('I')
        out.append(bytearray(mv[::n].tobytes()))
    return len(out[0]) // 4, len(out), out


def png_memoire(w, h, rows):
    raw = b''.join(b'\x00' + bytes(r) for r in rows)
    def chunk(t, c): return struct.pack('>I', len(c)) + t + c + struct.pack('>I', zlib.crc32(t + c) & 0xffffffff)
    return b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', struct.pack('>IIBBBBB', w, h, 8, 6, 0, 0, 0)) \
        + chunk(b'IDAT', zlib.compress(raw, 1)) + chunk(b'IEND', b'')


def photo(tk, w, h, rows, fond=(60, 64, 72)):
    """PhotoImage (tk = la fenêtre) d'une image RGBA (la transparence est posée sur un fond uni)"""
    if fond is not None:
        rows = [bytearray(r) for r in rows]
        for r in rows:
            for x in range(3, len(r), 4):
                a = r[x]
                if a < 255:
                    for k in range(3):
                        r[x - 3 + k] = (r[x - 3 + k] * a + fond[k] * (255 - a)) // 255
                    r[x] = 255
    return tkinter.PhotoImage(master=tk, data=base64.b64encode(png_memoire(w, h, rows)))


def _lum(r, g, b):
    return (r * 299 + g * 587 + b * 114) / 1000.0


def remplacer_couleur(rows, source, cible, tolerance=60):
    """chaque pixel proche de `source` (teinte et saturation) prend `cible`, avec la même ombre relative.
    Rapide : une seule fois par couleur différente de l'image. Renvoie le nombre de pixels changés."""
    sr, sg, sb = source
    sl = max(1.0, _lum(sr, sg, sb))
    tr, tg, tb = cible
    # couleur « normalisée » de la source : on compare les directions de couleur (indépendamment de l'ombre)
    sn = max(1.0, (sr + sg + sb) / 3.0)
    sdir = (sr / sn, sg / sn, sb / sn)
    memo = {}
    tol = tolerance / 100.0
    n = 0
    for r in rows:
        mv = memoryview(r).cast('I')
        for i, v in enumerate(mv):
            res = memo.get(v)
            if res is None:
                R, G, B, A = v & 255, (v >> 8) & 255, (v >> 16) & 255, v >> 24
                m = max(1.0, (R + G + B) / 3.0)
                d = abs(R / m - sdir[0]) + abs(G / m - sdir[1]) + abs(B / m - sdir[2])
                L = _lum(R, G, B)
                # même teinte (direction) et luminosité pas trop éloignée (garde les contours noirs et les blancs)
                if A > 0 and d <= tol and 0.25 * sl <= L <= 2.2 * sl + 30:
                    f = L / sl
                    nr, ng, nb = (min(255, int(c * f)) for c in (tr, tg, tb))
                    res = nr | ng << 8 | nb << 16 | A << 24
                else:
                    res = v
                memo[v] = res
            if res != v:
                mv[i] = res
                n += 1
    return n


def poser_logo(rows, w, h, logo, cx, cy, taille):
    """colle le logo (w, h, lignes RGBA) centré en (cx, cy), redimensionné pour que son plus grand côté fasse `taille`"""
    lw, lh, lr = logo
    f = taille / float(max(lw, lh))
    nw, nh = max(1, int(lw * f)), max(1, int(lh * f))
    lr = images.redimensionner(lw, lh, lr, nw, nh)
    x0, y0 = int(cx - nw / 2), int(cy - nh / 2)
    for y in range(nh):
        yy = y0 + y
        if not 0 <= yy < h:
            continue
        src, dst = lr[y], rows[yy]
        for x in range(nw):
            xx = x0 + x
            if not 0 <= xx < w:
                continue
            a = src[x * 4 + 3]
            if a == 0:
                continue
            p = xx * 4
            for k in range(3):
                dst[p + k] = (src[x * 4 + k] * a + dst[p + k] * (255 - a)) // 255
            dst[p + 3] = max(dst[p + 3], a)


def pixel(rows, x, y):
    return tuple(rows[y][x * 4:x * 4 + 4])


def recadrer(w, h, rows, marge=4):
    """recadre sur la partie non transparente (pour agrandir les bustes dans l'aperçu), en carré"""
    x0, y0, x1, y1 = w, h, -1, -1
    for y in range(h):
        mv = memoryview(rows[y]).cast('I')
        for x in range(0, w, 2):
            if (mv[x] >> 24) > 16:
                if x < x0: x0 = x
                if x > x1: x1 = x
                if y < y0: y0 = y
                y1 = y
    if x1 < 0:
        return w, h, rows
    c = max(x1 - x0, y1 - y0) + 2 * marge
    cx, cy = (x0 + x1) // 2, (y0 + y1) // 2
    out = []
    for y in range(cy - c // 2, cy - c // 2 + c):
        ligne = bytearray(c * 4)
        if 0 <= y < h:
            for x in range(c):
                xx = cx - c // 2 + x
                if 0 <= xx < w:
                    ligne[x * 4:x * 4 + 4] = rows[y][xx * 4:xx * 4 + 4]
        out.append(ligne)
    return c, c, out


def peindre(rows, w, h, cx, cy, rayon, couleur=None, original=None):
    """disque de rayon `rayon` (bord adouci d'un pixel) centré en (cx, cy) :
    couleur = (r, g, b) -> pinceau (la transparence de l'image est gardée) ; original = lignes d'origine -> gomme"""
    import math
    r = max(0.5, float(rayon))
    if couleur is not None:
        cr, cg, cb = couleur
        rgb = cr | cg << 8 | cb << 16
        oct_r, oct_g, oct_b = bytes((cr,)), bytes((cg,)), bytes((cb,))
    for y in range(max(0, int(cy - r - 1)), min(h, int(cy + r + 2))):
        dy = y - cy
        if abs(dy) > r + 0.5:
            continue
        ext = math.sqrt(max(0.0, (r + 0.5) ** 2 - dy * dy))
        x0, x1 = max(0, int(math.floor(cx - ext))), min(w - 1, int(math.ceil(cx + ext)))
        inte = (r - 0.5) ** 2 - dy * dy
        if inte > 0:
            i = math.sqrt(inte)
            xs, xe = max(x0, int(math.ceil(cx - i))), min(x1, int(math.floor(cx + i)))
        else:
            xs, xe = 1, 0
        ligne = rows[y]
        if xs <= xe:            # milieu plein : copie rapide par tranches
            n = xe - xs + 1
            if original is not None:
                ligne[xs * 4:(xe + 1) * 4] = original[y][xs * 4:(xe + 1) * 4]
            else:
                ligne[xs * 4:(xe + 1) * 4:4] = oct_r * n
                ligne[xs * 4 + 1:(xe + 1) * 4:4] = oct_g * n
                ligne[xs * 4 + 2:(xe + 1) * 4:4] = oct_b * n
        mv = memoryview(ligne).cast('I')
        mo = memoryview(original[y]).cast('I') if original is not None else None
        for x in range(x0, x1 + 1):
            if xs <= x <= xe:
                continue
            a = r + 0.5 - math.sqrt((x - cx) ** 2 + dy * dy)
            if a <= 0:
                continue
            v = mv[x]
            src = mo[x] if mo is not None else (rgb | (v & 0xFF000000))
            if a >= 1:
                mv[x] = src
                continue
            res = 0
            for s in (0, 8, 16, 24):
                c = ((src >> s) & 255) * a + ((v >> s) & 255) * (1 - a)
                res |= int(c + 0.5) << s
            mv[x] = res


def trait(rows, w, h, a, b, rayon, couleur=None, original=None):
    """trait du point a au point b (une suite de disques rapprochés)"""
    import math
    (xa, ya), (xb, yb) = a, b
    d = math.hypot(xb - xa, yb - ya)
    pas = max(1.0, rayon / 3.0)
    n = max(1, int(d / pas))
    for k in range(1, n + 1):
        t = k / float(n)
        peindre(rows, w, h, xa + (xb - xa) * t, ya + (yb - ya) * t, rayon, couleur, original)
