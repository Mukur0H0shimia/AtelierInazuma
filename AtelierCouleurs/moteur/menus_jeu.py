"""(15/11/2026) IMAGES DES MENUS DU JEU pour le hub « Mes créations » (façon menus du jeu).

Lues dans data/dx11/menu (le jeu n'est jamais modifié), décodées une fois dans cache/menus_jeu/<nom>.png.
Les planches (plusieurs icônes sur une image) sont découpées en zones non transparentes (cache/menus_jeu/<nom>.json) :
le hub les affiche par background-position. Rien n'est publié : les images restent sur ce PC.

LU (images regardées le 15/11/2026) :
- mainmenu90_11 (bloc 8) : icônes BLANCHES des tuiles bleues du menu principal (éclair, car, BB, chariot, pièce de puzzle…) ;
- mainmenu90_01 (bloc 2) : les mêmes en bleu ;
- topmenu01_05 (bloc 1) : grandes icônes en couleur du menu (joueur, sac, fiche, cartes, classeur, cadeau, réglages…) ;
- topmenu01_08 (bloc 1) : petites icônes en couleur ;
- mainmenu90_00 (bloc 1) : fond bleu à empreintes de crampons et ballons ;
- member01_00 (bloc 3) : fond orange au « Y » (en-tête des menus d'équipe).
"""
import os, json
import numpy as np
from .g4 import images
from . import g4

MENU = os.path.join('dx11', 'menu')
FICHIERS = {
    'icones_tuiles': ('100_mainmenu/mainmenu90/mainmenu90_11/mainmenu90_11.g4tx', 8),
    'icones_bleues': ('100_mainmenu/mainmenu90/mainmenu90_01/mainmenu90_01.g4tx', 2),
    'icones_menu': ('100_topmenu/100_topmenu01/topmenu01_05/topmenu01_05.g4tx', 1),
    'petites_icones': ('100_topmenu/100_topmenu01/topmenu01_08/topmenu01_08.g4tx', 1),
    'fond': ('100_mainmenu/mainmenu90/mainmenu90_00/mainmenu90_00.g4tx', 1),
    'fond_orange': ('101_member/101_member01/member01_00/member01_00.g4tx', 3),
    # (22/11, menu des stats) icônes communes : éléments (carrés feu / forêt / vent, montagne), orbes des techniques
    'icones_communes': ('200_icon/15_icon_common/icon_common.g4tx', 0),
}
# (22/11) zones MESURÉES dans icon_common (composantes opaques ; regardées une à une) : [x, y, l, h]. La montagne n'a que
# son dessin opaque (son carré brun 150,90,0 a un alpha nul : le menu le redessine)
ZONES_NOMMEES = {'icones_communes': {
    'feu': [512, 1036, 50, 50], 'foret': [684, 1048, 50, 50], 'montagne': [746, 1046, 44, 36], 'vent': [892, 1052, 50, 50],
    'tir': [330, 998, 68, 68], 'tir_vert': [254, 998, 68, 68], 'mur': [10, 650, 80, 80], 'dribble': [110, 650, 80, 80],
    'dribble_vert': [210, 650, 80, 80], 'gant': [926, 970, 68, 68]}}


def _dossier(cache_dir):
    d = os.path.join(cache_dir, 'menus_jeu')
    os.makedirs(d, exist_ok=True)
    return d


def _decoder(data_dir, nom):
    rel, bloc = FICHIERS[nom]
    g = images.G4TX(open(os.path.join(data_dir, MENU, *rel.split('/')), 'rb').read())
    return g4.decoder_texture(g.blocs[bloc])          # (w, h, octets RGBA)


def image(data_dir, cache_dir, nom):
    """chemin du PNG (décodé au 1er appel) ; None si le nom n'est pas connu ou l'image illisible"""
    if nom not in FICHIERS:
        return None
    f = os.path.join(_dossier(cache_dir), nom + '.png')
    if not os.path.exists(f):
        r = _decoder(data_dir, nom)
        if not r:
            return None
        images.ecrire_png(f, *r)
    return f


def zones(data_dir, cache_dir, nom, pas=4, marge=3):
    """zones des icônes d'une planche : [[x, y, w, h], …] dans l'ordre de lecture (lignes puis colonnes).
    Pixels avec alpha > 24, réduits par « pas », élargis de « marge » cases pour garder ensemble les morceaux d'une icône."""
    f = os.path.join(_dossier(cache_dir), nom + '.json')
    if os.path.exists(f):
        return json.load(open(f, encoding='utf-8'))
    r = _decoder(data_dir, nom)
    if not r:
        return []
    w, h, rangees = r                                 # rangées RGBA (une par ligne)
    px = b''.join(bytes(x) for x in rangees) if not isinstance(rangees, (bytes, bytearray)) else bytes(rangees)
    a = np.frombuffer(px, np.uint8)[:w * h * 4].reshape(h, w, 4)[:, :, 3] > 24
    H, W = (h + pas - 1) // pas, (w + pas - 1) // pas
    g = np.zeros((H * pas, W * pas), bool); g[:h, :w] = a
    g = g.reshape(H, pas, W, pas).any(axis=(1, 3))
    d = g.copy()
    for k in range(1, marge + 1):                      # élargit (sans scipy)
        d[k:, :] |= g[:-k, :]; d[:-k, :] |= g[k:, :]
    g2 = d.copy()
    for k in range(1, marge + 1):
        d[:, k:] |= g2[:, :-k]; d[:, :-k] |= g2[:, k:]
    vu = np.zeros_like(d)
    out = []
    for y0, x0 in zip(*np.nonzero(d)):
        if vu[y0, x0]:
            continue
        pile = [(y0, x0)]; vu[y0, x0] = True
        ys, xs = [y0, y0], [x0, x0]
        while pile:
            y, x = pile.pop()
            ys[0] = min(ys[0], y); ys[1] = max(ys[1], y); xs[0] = min(xs[0], x); xs[1] = max(xs[1], x)
            for yy, xx in ((y - 1, x), (y + 1, x), (y, x - 1), (y, x + 1)):
                if 0 <= yy < H and 0 <= xx < W and d[yy, xx] and not vu[yy, xx]:
                    vu[yy, xx] = True; pile.append((yy, xx))
        x1, y1 = max(0, (xs[0] + marge) * pas), max(0, (ys[0] + marge) * pas)
        x2, y2 = min(w, (xs[1] - marge + 1) * pas), min(h, (ys[1] - marge + 1) * pas)
        if x2 - x1 >= 12 and y2 - y1 >= 12:
            out.append([int(x1), int(y1), int(x2 - x1), int(y2 - y1)])
    out.sort(key=lambda z: (round((z[1] + z[3] / 2) / 60), z[0]))
    json.dump(out, open(f, 'w', encoding='utf-8'))
    return out


GRILLES = {'icones_menu': (3, 3), 'petites_icones': (6, 5)}
# (le hub n'utilise que ces images ; les planches irrégulières des tuiles se découpent mal : icônes collées)
HUB = ('icones_menu', 'petites_icones', 'fond', 'fond_orange', 'icones_communes')


def tout(data_dir, cache_dir):
    """pour le hub : {nom: {url, w, h, zones}}"""
    res = {}
    for nom in HUB:
        f = image(data_dir, cache_dir, nom)
        if not f:
            continue
        w, h, _ = images.lire_png(f)
        if nom in GRILLES:                              # planches rangées en grille régulière (LU à l'œil : 3 x 3, 6 x 5)
            c, l = GRILLES[nom]
            z = [[int(i * w / c), int(j * h / l), int(w / c), int(h / l)] for j in range(l) for i in range(c)]
        elif nom.startswith('icones') and nom not in ZONES_NOMMEES:
            z = zones(data_dir, cache_dir, nom, pas=4, marge=1)
        else:
            z = []
        if nom in ZONES_NOMMEES:
            z = []
        res[nom] = {'url': '/menu_jeu/%s.png' % nom, 'w': w, 'h': h, 'zones': z, 'noms': ZONES_NOMMEES.get(nom, {})}
    return res
