"""Bords des pièces du patron : le fond autour des pièces (non utilisé par le modèle 3D) est rempli avec la couleur du
bord le plus proche. Sans ça, quand le jeu réduit l'image (de loin, mipmaps), la couleur du fond « bave » sur les
coutures et autour du col."""
from collections import deque
from . import images

N = 512                               # grille de travail (un carré = 4 pixels d'une image de 2048)


def masque(tris, n=N):
    """triangles UV [u1, v1, u2, v2, u3, v3, ...] -> bytearray n*n (1 = utilisé par le modèle)"""
    m = bytearray(n * n)
    for i in range(0, len(tris) - 5, 6):
        (x1, y1), (x2, y2), (x3, y3) = [(tris[i + 2 * k] * n, tris[i + 2 * k + 1] * n) for k in range(3)]
        d = (y2 - y3) * (x1 - x3) + (x3 - x2) * (y1 - y3)
        if not d:
            continue
        for y in range(max(0, int(min(y1, y2, y3)) - 1), min(n, int(max(y1, y2, y3)) + 2)):
            cy = y + 0.5
            for x in range(max(0, int(min(x1, x2, x3)) - 1), min(n, int(max(x1, x2, x3)) + 2)):
                cx = x + 0.5
                a = ((y2 - y3) * (cx - x3) + (x3 - x2) * (cy - y3)) / d
                b = ((y3 - y1) * (cx - x3) + (x1 - x3) * (cy - y3)) / d
                if a >= -0.15 and b >= -0.15 and a + b <= 1.15:      # un peu large : garde les bords des pièces
                    m[y * n + x] = 1
    return m


def remplir(w, h, rows, tris, n=N):
    """renvoie les lignes de l'image avec le fond (hors des pièces) rempli par la couleur du bord le plus proche"""
    if not tris:
        return rows
    m = masque(tris, n)
    if sum(m) < n * n // 50:
        return rows                   # presque rien : on ne touche pas
    # petite image n x n (moyenne) pour les couleurs des bords
    pw, ph, pr = w, h, rows
    while pw > n and ph > n:
        pw, ph, pr = images.moitie(pw, ph, pr)
    if (pw, ph) != (n, n):
        pr = images.redimensionner(pw, ph, pr, n, n)
    coul = [None] * (n * n)
    file = deque()
    for i in range(n * n):
        if m[i]:
            y, x = divmod(i, n)
            coul[i] = bytes(pr[y][x * 4:x * 4 + 3]) + b'\xff'
            file.append(i)
    while file:                       # chaque case vide prend la couleur de la pièce la plus proche
        i = file.popleft()
        y, x = divmod(i, n)
        for j in ((i - 1) if x else -1, (i + 1) if x < n - 1 else -1, i - n, i + n):
            if 0 <= j < n * n and coul[j] is None:
                coul[j] = coul[i]
                file.append(j)
    # on garde l'image d'origine sur les pièces (et une case autour) ; ailleurs, la couleur du bord
    garde = bytearray(m)
    for i in range(n * n):
        if m[i]:
            y, x = divmod(i, n)
            for j in (i - 1 if x else i, i + 1 if x < n - 1 else i, i - n if y else i, i + n if y < n - 1 else i):
                garde[j] = 1
    out = []
    for y in range(h):
        cy = (y * n // h) * n
        ligne = bytearray(rows[y])
        x = 0
        while x < w:
            c = cy + x * n // w
            fin = min(w, ((x * n // w) + 1) * w // n)
            if fin <= x:
                fin = x + 1
            if not garde[c]:
                ligne[x * 4:fin * 4] = coul[c] * (fin - x)
            x = fin
        out.append(ligne)
    return out
