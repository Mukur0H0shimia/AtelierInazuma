"""Icône de « Atelier Inazuma.exe » : éclair doré sur un carré arrondi bleu nuit -> violet. Écrit lanceur/inazuma.ico
(images PNG 256, 64, 48, 32, 16 dans un .ico). Sans bibliothèque : dessin point par point, suréchantillonné."""
import os, struct, sys, io
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'AtelierMaillots'))
from lib import images  # noqa: E402

ICI = os.path.dirname(os.path.abspath(__file__))
# éclair (coordonnées dans un carré 0..1)
ECLAIR = [(0.60, 0.08), (0.26, 0.55), (0.47, 0.55), (0.36, 0.92), (0.76, 0.40), (0.54, 0.40), (0.66, 0.08)]


def dedans(x, y, poly):
    c = False
    for i in range(len(poly)):
        (x1, y1), (x2, y2) = poly[i], poly[i - 1]
        if (y1 > y) != (y2 > y) and x < (x2 - x1) * (y - y1) / (y2 - y1) + x1:
            c = not c
    return c


def dist_seg(px, py, a, b):
    (x1, y1), (x2, y2) = a, b
    dx, dy = x2 - x1, y2 - y1
    t = max(0, min(1, ((px - x1) * dx + (py - y1) * dy) / (dx * dx + dy * dy)))
    return ((px - x1 - t * dx) ** 2 + (py - y1 - t * dy) ** 2) ** 0.5


def pixel(x, y):
    """couleur RGBA (0-1) au point (x, y) du carré 0..1"""
    r = 0.18                                                     # coins arrondis
    cx, cy = min(max(x, r), 1 - r), min(max(y, r), 1 - r)
    if (x - cx) ** 2 + (y - cy) ** 2 > r * r or not (0 <= x <= 1 and 0 <= y <= 1):
        return (0, 0, 0, 0)
    t = y                                                        # fond : bleu nuit en haut -> violet en bas
    fond = (0.05 + 0.25 * t, 0.07 + 0.05 * t, 0.29 + 0.45 * t)
    d = min(dist_seg(x, y, ECLAIR[i], ECLAIR[i - 1]) for i in range(len(ECLAIR)))
    if dedans(x, y, ECLAIR):
        g = (y - 0.08) / 0.84                                    # or : clair en haut -> orangé en bas
        return (1.0, 0.93 - 0.25 * g, 0.55 - 0.45 * g, 1)
    if d < 0.035:
        return (0.04, 0.03, 0.12, 1)                             # contour foncé
    if d < 0.09:                                                 # lueur
        k = (0.09 - d) / 0.055 * 0.55
        return tuple(fond[i] * (1 - k) + (1.0, 0.8, 0.3)[i] * k for i in range(3)) + (1,)
    return fond + (1,)


def image(n, ss=4):
    rows = []
    for py in range(n):
        row = bytearray()
        for px in range(n):
            acc = [0.0] * 4
            for sy in range(ss):
                for sx in range(ss):
                    c = pixel((px + (sx + 0.5) / ss) / n, (py + (sy + 0.5) / ss) / n)
                    a = c[3]
                    acc[0] += c[0] * a; acc[1] += c[1] * a; acc[2] += c[2] * a; acc[3] += a
            a = acc[3] / (ss * ss)
            row += bytes([int(255 * acc[0] / acc[3]) if acc[3] else 0, int(255 * acc[1] / acc[3]) if acc[3] else 0,
                          int(255 * acc[2] / acc[3]) if acc[3] else 0, int(255 * a)])
        rows.append(row)
    return rows


def main():
    tailles = [256, 64, 48, 32, 16]
    pngs = []
    for n in tailles:
        f = os.path.join(ICI, '_icone_%d.png' % n)
        images.ecrire_png(f, n, n, image(n, 3 if n > 64 else 6))
        pngs.append(open(f, 'rb').read())
        if n != 256:
            os.remove(f)
    os.replace(os.path.join(ICI, '_icone_256.png'), os.path.join(ICI, 'inazuma_256.png'))
    tete = struct.pack('<HHH', 0, 1, len(pngs))
    off = 6 + 16 * len(pngs)
    dirs, data = b'', b''
    for n, p in zip(tailles, pngs):
        dirs += struct.pack('<BBBBHHII', n % 256, n % 256, 0, 0, 1, 32, len(p), off + len(data))
        data += p
    open(os.path.join(ICI, 'inazuma.ico'), 'wb').write(tete + dirs + data)
    print('icône écrite')


if __name__ == '__main__':
    main()
