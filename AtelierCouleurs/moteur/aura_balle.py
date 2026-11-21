"""Aura du ballon pendant une cinématique (13/11/2026).

CORRIGÉ (13/11/2026, lu dans nie.exe et dans chr_toon_effstatus.pfxo) : c'est un EFFET DE STATUT (CStatusEffComponent) posé
sur le modèle du ballon, pas un modèle d'aura ajouté. Les courbes de la définition vont dans cb7 :
  courbe 1 -> u_charaStatusColor (couleur x), courbe 2 -> u_charaStatusRimColor (contour lumineux, HDR),
  courbe 3 -> u_charaStatusPowInOutDis (x = puissance du contour), courbes 4 / 5 -> u_charaStatusUvCenter / UvSclMove.
PS : couleur = couleur x StatusColor + R, avec p = (1 - N.V)^Pow, Rim = RimColor.rgb x RimColor.w (w = 5e valeur des clés x fondu : LU, voir plus bas),
  R = min(5a, 1) x (Rim x p - 0,3 sat(Rim x p)) + 0,3 sat(Rim x p).
(Texte d'origine ci-dessous, gardé pour l'historique.)

Trouvé dans les fichiers du jeu :
- commande 0xC3FB5CC5 du fichier <ev>_eff.cfg.bin : [acteur ballon, nom d'aura, 0 = début / 1 = fin, 1] ;
- définition : common/effect/effect_status_define_*.cfg.bin, lignes 0xAD401CFD = [nom, crc1, crc2, crc3, crc4, crc5, type, …] ;
- crc1..crc3 = courbes de common/effect/effect_define_*.cfg.bin : 0x3C57A91D [crc], 0x2096D587 [nb de clés],
  puis 0x74502ABA [temps, a, b, c, drapeau] par clé ;
- modèles d'aura de ballon : ega0020 / ega0060 / ega0065 (shader Effect_BallAura1 = ThresholdGrd, colonne du dégradé
  BallAura0010 donnée par le moteur ; colonne = « couleur de tir » de la technique : 0 montagne, 1 vent, 2 feu, 3 forêt, 4 vide).

LU dans nie.exe le 14/11/2026 (CStatusEffComponent, 0x140f08940 -> 0x140f0aa40, mise à jour 0x140f0a390) :
- ligne de la définition = [nom, courbe 1..5, durée (s), texture, crc, Distotion, UvScl x, y, défilement u, v, ?, fondu
  d'entrée (s), fondu de sortie (s), priorité, mode, genre, ?] (structure : durée +0x20, Distotion +0x38, UvScl +0x3C/+0x40,
  défilement +0x44/+0x48, fondus +0x50/+0x54, octets priorité +0x58, mode +0x59, genre +0x5A). L'ancienne clé 'type'
  (colonne 6) est en fait la DURÉE ;
- temps des courbes = temps / durée ; mode 0 = en boucle (fmod), 1 = arrêté à la fin puis fondu de sortie ;
- poids w : fondu d'entrée temps / fondu (puis 1), fondu de sortie 1 - temps / fondu ;
- couleur = (c - 1) w + 1 ; contour (4 composantes, la 5e valeur des clés = w) = (c - (1, 1, 1, 0)) w + (1, 1, 1, 0) ;
  puissance = (c - 10) w + 10 ; TexIn / TexOut = w c (pas lus par chr_toon_effstatus).
(Ancien texte, périmé depuis l'effet de statut LU : le modèle ega0020 n'est plus ajouté.) Ancienne hypothèse : le rôle des courbes (la 2e courbe sert
de teinte : l'Atelier choisit la colonne de la palette la plus proche).
"""
import os, glob

CMD_AURA = 0xC3FB5CC5
_cache = {}


def _lire(data_dir):
    if data_dir in _cache:
        return _cache[data_dir]
    from . import cfgbin
    defs, courbes = {}, {}
    try:
        f = sorted(glob.glob(os.path.join(data_dir, 'common', 'effect', 'effect_status_define_*.cfg.bin')))[-1]
        for c, v in cfgbin.lire(open(f, 'rb').read()):
            if (c & 0xFFFFFFFF) == 0xAD401CFD and v and isinstance(v[0], str) and len(v) > 6:
                defs[v[0]] = {'courbes': [x & 0xFFFFFFFF for x in v[1:6] if isinstance(x, int)], 'type': v[6],
                              'duree': float(v[6]), 'entree': float(v[15]), 'sortie': float(v[16]),
                              'boucle': (v[18] if len(v) > 18 and isinstance(v[18], int) else 0) == 0,
                              # (14/11/2026) LU : +0x58 priorité, +0x5A genre = n° de la fonction qui combine deux auras
                              # (table 0x141918a50 : 0 remplacement, 1 mélange linéaire, 2 passage par le neutre)
                              'priorite': v[17] if len(v) > 17 and isinstance(v[17], int) else 3,
                              'genre': v[19] if len(v) > 19 and isinstance(v[19], int) else 0}
        f = sorted(glob.glob(os.path.join(data_dir, 'common', 'effect', 'effect_define_*.cfg.bin')))[-1]
        cour = None
        for c, v in cfgbin.lire(open(f, 'rb').read()):
            c &= 0xFFFFFFFF
            if c == 0x3C57A91D and v and isinstance(v[0], int):
                cour = courbes.setdefault(v[0] & 0xFFFFFFFF, [])
            elif c == 0x74502ABA and cour is not None and len(v) >= 4:
                cour.append([float(x) for x in v[:5]])       # [temps, x, y, z, w] (w : 4e composante, LU 14/11/2026)
            elif c == 0x5F244B73:
                cour = None
    except (IndexError, OSError):
        pass
    _cache[data_dir] = (defs, courbes)
    return defs, courbes


def intervalles(data_dir, cmds):
    """[{acteur, nom, debut, fin, courbes: [[[t, a, b, c], …], …]}] d'après les commandes (image, crc, args)"""
    defs, courbes = _lire(data_dir)
    ouverts, out = {}, []
    for f, cmd, a in sorted(cmds, key=lambda x: x[0]):
        if cmd != CMD_AURA or len(a) < 3 or not isinstance(a[1], str):
            continue
        cle = (a[0], a[1])
        if a[2] == 0:
            ouverts[cle] = f
        elif cle in ouverts:
            d = defs.get(a[1], {})
            out.append({'acteur': a[0], 'nom': a[1], 'debut': ouverts.pop(cle), 'fin': f, 'type': d.get('type'),
                        'duree': d.get('duree', 1.0), 'entree': d.get('entree', 0.0), 'sortie': d.get('sortie', 0.0),
                        'boucle': d.get('boucle', True), 'priorite': d.get('priorite', 3), 'genre': d.get('genre', 0),
                        'courbes': [courbes.get(c, []) for c in d.get('courbes', [])]})
    for (acteur, nom), f in ouverts.items():
        d = defs.get(nom, {})
        out.append({'acteur': acteur, 'nom': nom, 'debut': f, 'fin': 10 ** 6, 'type': d.get('type'),
                    'duree': d.get('duree', 1.0), 'entree': d.get('entree', 0.0), 'sortie': d.get('sortie', 0.0),
                    'boucle': d.get('boucle', True), 'priorite': d.get('priorite', 3), 'genre': d.get('genre', 0),
                        'courbes': [courbes.get(c, []) for c in d.get('courbes', [])]})
    return sorted(out, key=lambda x: x['debut'])
