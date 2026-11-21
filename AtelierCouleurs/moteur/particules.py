"""Particules du jeu (.ptlb) : lecture fidèle aux chargeurs de nie.exe (13/11/2026).

Chaque section est lue comme le fait le jeu (table 0x141cc8f60 -> une fonction par section, valeurs lues dans l'ordre,
avec les mêmes conversions) ; les valeurs par défaut sont celles du constructeur 0x1405b0dc0. Vérifié en exécutant les
chargeurs du jeu dans un émulateur (nie_outils/emu_ptl.py). Détail : coffre Obsidian, note « Particules - code du moteur ».

Résultat : une liste d'émetteurs (dictionnaires JSON) que web/particules.js simule à l'identique.
"""
import struct, math, os

DEG = 0.01745329238474369          # constante du jeu (0x141a7cb4c / 0x141a7e3f0)
F32 = lambda x: struct.unpack('<f', struct.pack('<f', x))[0]


def lire_brut(chemin):
    """[(nom de la section, [(type, valeur)])] ; types : 0 texte, 1 entier, 2 flottant (valeurs exactes, sans arrondi)"""
    b = open(chemin, 'rb').read()
    n, off_str, taille_str, n_str = struct.unpack_from('<4I', b, 0)
    chaines = b[off_str:off_str + taille_str]
    k0 = (off_str + taille_str + 15) & ~15
    noms = {}
    if k0 + 16 <= len(b):
        taille, nb, off_noms, taille_noms = struct.unpack_from('<4I', b, k0)
        tn = b[k0 + off_noms:k0 + off_noms + taille_noms]
        for i in range(nb):
            crc, on = struct.unpack_from('<II', b, k0 + 16 + 8 * i)
            if on < len(tn):
                noms[crc] = tn[on:tn.index(b'\0', on)].decode('utf-8', 'replace')
    p = 16; out = []
    for _ in range(n):
        crc, nb = struct.unpack_from('<IB', b, p); p += 5
        nt = (nb + 3) // 4
        types = [(b[p + k] >> (2 * j)) & 3 for k in range(nt) for j in range(4)]
        p += nt; p = (p + 3) & ~3
        vals = []
        for k in range(nb):
            raw = struct.unpack_from('<I', b, p)[0]; p += 4
            t = types[k]
            if t == 0:
                vals.append((0, None if raw == 0xFFFFFFFF else chaines[raw:chaines.index(b'\0', raw)].decode('utf-8', 'replace')))
            elif t == 1:
                vals.append((1, struct.unpack('<i', struct.pack('<I', raw))[0]))
            elif t == 2:
                vals.append((2, struct.unpack('<f', struct.pack('<I', raw))[0]))
            else:
                vals.append((t, raw))
        out.append((noms.get(crc, '%08x' % crc), vals))
    return out


class _L:
    """curseur sur les valeurs d'une section : mêmes conversions que FUN_140054af0 (entier) / 140054b70 (flottant)"""
    def __init__(self, vals):
        self.v = vals; self.k = 0

    def reste(self):
        return len(self.v) - self.k

    def i(self):
        t, x = self.v[self.k]; self.k += 1
        if t == 1: return x
        if t == 2: return int(x)          # cvttss2si : vers zéro
        return 0

    def f(self):
        t, x = self.v[self.k]; self.k += 1
        if t == 2: return x
        if t == 1: return float(x)
        return 0.0

    def s(self):
        t, x = self.v[self.k]; self.k += 1
        return x if t == 0 else None


def _courbe(L, n, dim=1):
    """courbe du jeu : n valeurs (dim composantes : toutes les x, puis les y…) puis n temps"""
    vals = [[L.f() for _ in range(n)] for _ in range(dim)]
    temps = [L.f() for _ in range(n)]
    return {'v': [list(c) for c in zip(*vals)] if dim > 1 else vals[0], 't': temps}


def _emetteur_vide():
    """valeurs du constructeur 0x1405b0dc0"""
    return {
        'emetteur': {'duree': 1.0, 'boucle': False, 'retard': 0.0, 'figer': False, 'fin': 0.0, 'local': 0, 'max': 1000, 'mode': 0,
                     'debit': 10.0, 'sansEchelle': False, 'courbe': None},
        'materiau': {'tex': [[None, None], [None, None], [None, None]], 'b100': 1, 'b101': 1, 'b102': 1, 'melange': 0, 'priorite': 25,
                     'shader': None, 'adressage': [[1, 1], [1, 1], [1, 1]]},
        'sommets': [], 'shader': [0.0] * 32,
        'forme': {'type': 0, 'rayon': 1.0, 'angle': 25.0, 'taille': [1.0, 1.0, 1.0], 'coque': False, 'dirHasard': False},
        'vie': {'hasard': False, 'min': 1.0, 'max': 0.0, 'k': 1.0},
        'couleur': {'alpha': None, 'rgb': None, 'hasardA': False, 'alpha2': None, 'hasardC': False, 'rgb2': None},
        'vitesse': {'hasard': False, 'min': 5.0, 'max': 0.0, 'courbe': None},
        'taille': {'hasard': False, 'min': [1.0, 1.0, 1.0], 'max': [1.0, 1.0, 1.0], 'deux': False, 'unTirage': True, 'parAxe': 0,
                   'courbe': None, 'courbe2': None},
        'rotation': {'hasardA': True, 'a0': [0.0, 0.0, 0.0], 'a1': [0.0, 0.0, 0.0], 'hasardV': False, 'v0': [0.0, 0.0, 0.0],
                     'v1': [0.0, 0.0, 0.0], 'signe': True, 'suitEmetteur': False},
        'force': {'gravite': 0.0, 'b': 0, 'c': 1.0, 'nom': 0, 'd': 0.75, 'e': 1.0},
        'uv': [],
        'modele': {'m0': 0, 'larg': 1.0, 'haut': 1.0, 'type': 0, 'dec': [0.0, 0.0, 0.0], 'rot': [0.0, 0.0, 0.0], 'suitVitesse': False,
                   'ordre': 0, 'x7e0': 12},
        'vent': {'actif': False, 'force': 0.0, 'dir': [0.0, 0.0, 0.0], 'hasard': False, 'min': 1.0, 'max': 1.0, 'courbe': None},
        'motion': {'debut': [], 'fin': []},
    }


def _bool(x):
    return x != 0


def lire(chemin):
    """{'noeuds': [...], 'emetteurs': [...]} — lecture comme le jeu"""
    brut = lire_brut(chemin)
    noeuds, ems, cur = [], [], None
    for nom, vals in brut:
        if nom == 'PARTICLE_NODE_INFO':
            noeuds.append(vals[0][1] if vals else '')
        elif nom == 'PARTICLE_INFO_BGN':
            cur = _emetteur_vide()
        elif nom == 'PARTICLE_INFO_END':
            if cur is not None:
                ems.append(cur)
            cur = None
        elif cur is not None and vals:
            _section(cur, nom, _L(vals))
    for i, e in enumerate(ems):
        e['noeud'] = noeuds[i] if i < len(noeuds) else (noeuds[0] if noeuds else '')
    return {'noeuds': noeuds, 'emetteurs': ems}


def _section(E, nom, L):
    n = len(L.v)
    if nom == 'EMITTER_INFO':            # 0x1405c7110
        x = E['emetteur']; x['duree'] = L.f()
        if L.reste() > 0:
            x['boucle'] = _bool(L.i())
            if L.reste() > 0:
                if x['boucle'] and x['duree'] < 1.0:        # boucle : durée au moins 1 s (lu dans le chargeur)
                    x['duree'] = 1.0
                x['retard'] = L.f()
                if L.reste() > 0:
                    x['figer'] = L.f() != 0.0
                    if L.reste() > 0:
                        x['fin'] = L.f()
                        if L.reste() > 0:
                            x['local'] = L.i()
                            if L.reste() > 0:
                                x['max'] = L.i() & 0xFFFFFFFF
                                if L.reste() > 0:
                                    x['mode'] = L.i()
                                    if L.reste() > 0:
                                        x['debit'] = L.f()
                                        if L.reste() > 0:
                                            x['sansEchelle'] = _bool(L.i())
                                            if L.reste() > 0:
                                                k = L.i()
                                                if L.reste() > 0 and k:
                                                    x['courbe'] = _courbe(L, k)
    elif nom == 'MATERIAL_INFO':         # 0x1405c73c0
        m = E['materiau']; k = 0
        for j in range(3):
            pack = L.s(); tex = L.s(); m['tex'][j] = [pack, tex]
            if n <= k + 2:
                return
            k += 2
        m['b100'] = _bool(L.i())
        if k + 1 < n:
            m['b101'] = _bool(L.i()); k += 2
            if k < n:
                m['b102'] = _bool(L.i()); k += 1
                if k < n:
                    m['melange'] = L.i() & 0xFF; k += 1
                    if k < n:
                        m['priorite'] = L.i() & 0xFFFF
                        if k + 1 < n:
                            m['shader'] = L.s(); k += 2
                            conv = [1, 2, 3, 5, 4]
                            for j in range(3):
                                if k >= n: break
                                a = L.i(); k += 1; m['adressage'][j][0] = conv[a] if 0 <= a < 5 else 1
                                if k >= n: break
                                b = L.i(); k += 1; m['adressage'][j][1] = conv[b] if 0 <= b < 5 else 1
    elif nom == 'VERTEX_INFO':           # 0x1405c8e00 : un bit par valeur
        E['sommets'] = [L.i() for _ in range(n)]
    elif nom == 'SHADER_INFO':           # 0x1405c8af0 : u_shaderParam0..7
        E['shader'] = [L.f() for _ in range(min(n, 32))] + [0.0] * max(0, 32 - n)
    elif nom == 'SHAPE_INFO':            # 0x1405c7660
        s = E['forme']; s['type'] = L.i()
        if n > 1:
            s['rayon'] = abs(L.f())
            if n > 2:
                s['angle'] = F32(L.f() * DEG)
                if n > 3:
                    s['taille'] = [L.f(), L.f(), L.f()]
                    if n > 6:
                        s['coque'] = _bool(L.i())
                        if n > 7:
                            s['dirHasard'] = _bool(L.i())
    elif nom == 'LIFE_TIME_INFO':        # 0x1405c7780
        v = E['vie']; v['hasard'] = _bool(L.i())
        if n > 1:
            v['min'] = L.f()
            if n > 2:
                v['max'] = L.f()
                if n > 3:
                    v['k'] = L.f()
    elif nom == 'COLOR_INFO':            # 0x1405c7840
        c = E['couleur']; na = L.i()
        if n > 1:
            if na:
                c['alpha'] = _courbe(L, na)
            k = 2 * na
            if k + 1 < n:
                nc = L.i(); k += 2
                if k < n:
                    if nc:
                        c['rgb'] = _courbe(L, nc, 3)
                    k += nc * 4
                    if k < n:
                        c['hasardA'] = _bool(L.i()); k += 1
                        if k < n:
                            if na:
                                c['alpha2'] = {'v': [L.f() for _ in range(na)], 't': c['alpha']['t']}
                                k += na
                                if n <= k:
                                    return
                            c['hasardC'] = _bool(L.i())
                            if k + 1 < n and nc:
                                vals = [[L.f() for _ in range(nc)] for _ in range(3)]
                                c['rgb2'] = {'v': [list(t) for t in zip(*vals)], 't': c['rgb']['t']}
    elif nom == 'SPEED_INFO':            # 0x1405c7ba0
        s = E['vitesse']; s['hasard'] = _bool(L.i())
        if n > 1:
            s['min'] = L.f()
            if n > 2:
                s['max'] = L.f()
                if n > 3:
                    k = L.i()
                    if n > 4 and k:
                        s['courbe'] = _courbe(L, k)
    elif nom == 'SCALE_INFO':            # 0x1405c7d30
        s = E['taille']; s['hasard'] = _bool(L.i())
        if n > 1:
            s['min'] = [L.f(), L.f(), L.f()]
            if n > 4:
                s['max'] = [L.f(), L.f(), L.f()]
                if n > 7:
                    s['deux'] = _bool(L.i())
                    if n > 8:
                        s['unTirage'] = _bool(L.i())
                        if n > 9:
                            s['parAxe'] = L.i()
                            if n > 10:
                                k = L.i()
                                if n > 11 and k:
                                    s['courbe'] = _courbe(L, k, 3)
                                    if 11 + 4 * k < n and s['deux']:
                                        vals = [[L.f() for _ in range(k)] for _ in range(3)]
                                        s['courbe2'] = {'v': [list(t) for t in zip(*vals)], 't': s['courbe']['t']}
    elif nom == 'ROTATION_INFO':         # 0x1405c8060
        r = E['rotation']; r['hasardA'] = _bool(L.i())
        if n > 1:
            r['a0'] = [F32(L.f() * DEG) for _ in range(3)]
            if n > 4:
                r['a1'] = [F32(L.f() * DEG) for _ in range(3)]
                if n > 7:
                    r['hasardV'] = _bool(L.i())
                    if n > 8:
                        r['v0'] = [F32(L.f() * DEG) for _ in range(3)]
                        if n > 11:
                            r['v1'] = [F32(L.f() * DEG) for _ in range(3)]
                            if n > 14:
                                r['signe'] = _bool(L.i())
                                if n > 15:
                                    r['suitEmetteur'] = _bool(L.i())
    elif nom == 'FORCE_FIELD_INFO':      # 0x1405c8280
        f = E['force']; f['gravite'] = L.f()
        if n > 1:
            f['b'] = L.i()
            if n > 2:
                f['c'] = L.f()
                if n > 3:
                    f['nom'] = L.s()
                    if n > 4:
                        f['d'] = L.f()
                        if n > 5:
                            f['e'] = L.f()
    elif nom == 'UV_INFO':               # 0x1405c8390 (une couche de plus à chaque section)
        u = {'rep': [1.0, 1.0], 'b909': False, 'dec': [0.0, 0.0], 'defil': None, 'facteur': 1.0, 'mode': 0,
             'col': 0, 'lig': 0, 'invVit': 1.0, 'b90a': False, 'depHasard': False}
        u['rep'] = [L.f(), L.f()]
        if n > 2:
            u['b909'] = _bool(L.i())
            if n > 3:
                u['dec'] = [L.f(), L.f()]
                if n > 5:
                    k = L.i()
                    if n > 6:
                        if k:
                            u['defil'] = _courbe(L, k, 2)
                        j = (k + 2) * 3
                        if j < n:
                            u['facteur'] = L.f(); j += 1
                            if j < n:
                                u['mode'] = L.i() & 0xFF; j += 1
                                if j < n:
                                    col = L.i(); lig = L.i(); j += 2
                                    if j < n:
                                        v = L.f(); j += 1
                                        if j < n:
                                            u['col'] = col; u['lig'] = lig
                                            u['invVit'] = 1.0 / v if v > 0.0 else 1.0
                                            u['b90a'] = _bool(L.i())
                                            if j + 1 < n:
                                                u['depHasard'] = _bool(L.i())
        E['uv'].append(u)
    elif nom == 'MODEL_INFO':            # 0x1405c86f0
        m = E['modele']; m['m0'] = L.i()
        if n > 1:
            m['larg'] = L.f()
            if n > 2:
                m['haut'] = L.f()
                if n > 3:
                    m['type'] = L.i()
                    if n > 4:
                        m['dec'] = [L.f(), L.f(), L.f()]
                        if n > 7:
                            m['rot'] = [F32(L.f() * DEG) for _ in range(3)]
                            if n > 10:
                                m['suitVitesse'] = _bool(L.i())
                                if n > 11:
                                    m['ordre'] = L.i()
                                    if n > 12:
                                        m['x7e0'] = L.i()
    elif nom == 'WIND_INFO':             # 0x1405c8ea0
        w = E['vent']; w['actif'] = _bool(L.i())
        if L.reste() > 0:
            w['force'] = L.f()
            if L.reste() > 0:
                d = [L.f(), 0.0, 0.0]
                if L.reste() > 0:
                    d[1] = L.f()
                    if L.reste() > 0:
                        d[2] = L.f(); l = math.sqrt(d[0] ** 2 + d[1] ** 2 + d[2] ** 2)
                        w['dir'] = [x / l for x in d] if l > 0 and math.isfinite(l) else [0.0, 0.0, 0.0]
                        if L.reste() > 0:
                            w['hasard'] = _bool(L.i())
                            if L.reste() > 0:
                                w['min'] = L.f()
                                if L.reste() > 0:
                                    w['max'] = L.f()
                                    if L.reste() > 0:
                                        k = L.i()
                                        if L.reste() > 0 and k:
                                            w['courbe'] = _courbe(L, k)
    elif nom == 'MOTION_INFO':           # 0x1405c8900 : plans qui lancent l'émetteur, puis plans qui l'arrêtent (+ délai)
        mo = E['motion']; nd = L.i() & 0xFFFF; k = 1
        for j in range(min(nd, 8)):
            mo['debut'].append(L.s()); k += 1
            if k >= n:
                return
        mo['debut'] = [x for x in mo['debut'] if x]
        nf = L.i() & 0xFFFF; k += 1
        for j in range(min(nf, 8)):
            if k >= n:
                break
            nm = L.s(); k += 1
            if k >= n:
                mo['fin'].append([nm, 0.0]); break
            mo['fin'].append([nm, L.f()])
        mo['fin'] = [x for x in mo['fin'] if x[0]]


def textures(defs):
    """[(paquet, nom)] des textures citées par les émetteurs (paquet '#/effect/.../x.g4tx' ou None = l'effet lui-même)"""
    out = []
    for e in defs['emetteurs']:
        for pack, tex in e['materiau']['tex']:
            if tex and (pack, tex) not in out:
                out.append((pack, tex))
    return out


if __name__ == '__main__':
    import sys, json
    print(json.dumps(lire(sys.argv[1]), indent=1, ensure_ascii=False)[:6000])
