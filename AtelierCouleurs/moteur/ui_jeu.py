"""(23/11/2026) KIT « INTERFACE DU JEU » pour la refonte graphique de l'Atelier (demande de muku : « copier le jeu »).

Sert au navigateur, à la demande, des morceaux EXACTS des menus du jeu (lecture seule, rien n'est modifié) :
- /ui_jeu/zone/<planche>/<zone>.png : une zone nommée d'une planche .g4tx des menus (ex. team00_30/sp_win_base01) ;
- /ui_jeu/img/<planche>/<n>.png : l'image n d'une planche ;
- /ui_jeu/fond.png : le fond des menus d'équipe (mainmenu90_00, avec la teinte que le jeu pose : mesurée sur une capture) ;
- /ui_jeu/inazuma_jeu.ttf, /ui_jeu/inazuma_chiffres.ttf : les polices du jeu (moteur/police_jeu.py).

LU (format, voir aussi la note « Menus du jeu redessinés ») :
- .g4tx : u16 +0x20 = nb d'images, u16 +0x22 = nb TOTAL de noms (images + zones) ; table des images (0x30 chacune) dès 0x60 ;
  zones (0x18 : u16 image, type, x, y, w, h) juste après ; puis (aligné sur 16) les crc32 de tous les noms ;
- ordre de recherche (comme en jeu, avec les mods du joueur) : le cache de VRFW (écrans construits avec les mods),
  puis les mods (<jeu>/mods/*/assets/menu), puis les données du jeu.
"""
import os, re, struct, zlib, glob, json, threading

_verrou = threading.Lock()
_index = {}
LANGUES = {'de', 'en', 'es', 'it', 'pt', 'ja', 'zh_hans', 'zh_hant', 'ko', 'fr'}
TEINTE_FOND = (0.87, 1.05, 1.08)          # MESURÉE : capture du jeu / image bg01 (zones vides), stable à ±0,01


def _vrfw():
    return os.path.join(os.environ.get('LOCALAPPDATA', ''), 'VRFW', 'cache', 'VRFW', 'types')


def _indexer(cfg):
    """{nom de fichier: [chemins]} des .g4tx de menus : cache VRFW, mods, jeu (dans cet ordre)"""
    with _verrou:
        if _index:
            return _index
        racines = []
        v = _vrfw()
        if os.path.isdir(v):
            racines += [os.path.join(v, t, 'data', 'dx11') for t in os.listdir(v)]
        jeu = cfg.get('jeu_dir') or ''
        if jeu and os.path.isdir(os.path.join(jeu, 'mods')):
            racines += glob.glob(os.path.join(jeu, 'mods', '*', 'assets', 'menu')) + glob.glob(os.path.join(jeu, 'mods', '*', 'assets', 'images'))
        racines += [os.path.join(cfg['data_dir'], 'dx11', 'menu'), os.path.join(cfg['data_dir'], 'dx11', 'font')]
        for r in racines:
            for dp, dn, fn in os.walk(r):
                for f in fn:
                    if f.endswith('.g4tx'):
                        _index.setdefault(f[:-5], []).append(os.path.join(dp, f))
        return _index


def trouver(cfg, nom, langue='fr'):
    c = _indexer(cfg).get(nom, [])
    for p in c:                                  # version de la langue de l'Atelier, sinon sans langue
        if os.sep + langue + os.sep in p:
            return p
    for p in c:
        if not (LANGUES & set(p.split(os.sep))):
            return p
    return c[0] if c else None


def lire_planche(chemin):
    """-> (images [(w, h)], zones {nom: (img, x, y, w, h)}, G4TX)"""
    from .g4 import images
    b = open(chemin, 'rb').read()
    n = struct.unpack_from('<H', b, 0x20)[0]
    nz = struct.unpack_from('<H', b, 0x22)[0] - n
    total = struct.unpack_from('<I', b, 0x2C)[0]
    debut = len(b) - total
    o_crc = (0x60 + 0x30 * n + 0x18 * nz + 15) // 16 * 16
    crcs = struct.unpack_from('<%dI' % (n + nz), b, o_crc)
    par_crc = {zlib.crc32(m.group()): m.group().decode() for m in re.finditer(rb'[A-Za-z0-9_]{2,}', b[:debut])}
    tailles = [struct.unpack_from('<HH', b, 0x60 + 0x30 * k + 0x18) for k in range(n)]
    zones = {}
    for i in range(nz):
        img, typ, x, y, w, h = struct.unpack_from('<HHHHHH', b, 0x60 + 0x30 * n + 0x18 * i)
        zones[par_crc.get(crcs[n + i], '%08x' % crcs[n + i])] = (img, x, y, w, h)
    for k in range(n):
        zones.setdefault(par_crc.get(crcs[k], '%08x' % crcs[k]), (k, 0, 0) + tailles[k])
    return tailles, zones, images.G4TX(b)


def _rgba(bloc):
    """(w, h, tableau RGBA) d'une image de planche ; le RGBA 32 bits non compressé est lu ici (le décodeur général le raye)"""
    import numpy as np
    from . import g4
    h, w = struct.unpack_from('<II', bloc, 12)
    four = bloc[84:88]
    if four == b'\0\0\0\0' and struct.unpack_from('<I', bloc, 88)[0] == 32:
        r_masque = struct.unpack_from('<I', bloc, 92)[0]
        a = np.frombuffer(bloc, np.uint8, count=w * h * 4, offset=128).reshape(h, w, 4)
        return w, h, (a[..., [2, 1, 0, 3]] if r_masque == 0xFF0000 else a).copy()
    r = g4.decoder_texture(bloc)
    if not r:
        return None
    w, h, px = r
    px = b''.join(bytes(x) for x in px) if not isinstance(px, (bytes, bytearray)) else bytes(px)
    return w, h, np.frombuffer(px, np.uint8)[:w * h * 4].reshape(h, w, 4).copy()


def _png(chemin, a):
    from .g4 import images
    h, w = a.shape[:2]
    images.ecrire_png(chemin, w, h, [bytes(a[y].tobytes()) for y in range(h)])


def _dossier(cache_dir, *p):
    d = os.path.join(cache_dir, 'ui_jeu', *p)
    os.makedirs(d, exist_ok=True)
    return d


def zone(cfg, cache_dir, planche, nom, langue='fr'):
    """chemin du PNG d'une zone nommée (fait une fois) ; (25/11) langue : planche de cette langue (marques d'évolution
    gaiji_game2 : « 2 » en français, « +1 » en anglais)"""
    planche, nom = os.path.basename(planche), os.path.basename(nom)
    langue = langue if langue in LANGUES else 'fr'
    f = os.path.join(_dossier(cache_dir, 'zone', planche if langue == 'fr' else planche + '_' + langue), nom + '.png')
    if os.path.exists(f):
        return f
    src = trouver(cfg, planche, langue)
    if not src:
        return None
    tailles, zones, g = lire_planche(src)
    z = zones.get(nom)
    if not z:
        return None
    r = _rgba(g.blocs[z[0]])
    if not r:
        return None
    _png(f, r[2][z[2]:z[2] + z[4], z[1]:z[1] + z[3]])
    return f


def image(cfg, cache_dir, planche, k):
    planche = os.path.basename(planche)
    f = os.path.join(_dossier(cache_dir, 'img', planche), '%d.png' % int(k))
    if os.path.exists(f):
        return f
    src = trouver(cfg, planche)
    if not src:
        return None
    tailles, zones, g = lire_planche(src)
    if int(k) >= len(g.blocs):
        return None
    r = _rgba(g.blocs[int(k)])
    if not r:
        return None
    _png(f, r[2])
    return f


def liste(cfg, planche):
    """zones d'une planche (pour le développement) : {nom: [img, x, y, w, h]}"""
    src = trouver(cfg, planche)
    if not src:
        return {}
    return {k: list(v) for k, v in lire_planche(src)[1].items()}


def fond(cfg, cache_dir):
    """fond des menus d'équipe : bg01 de mainmenu90_00 (2640 x 1080, centré sur 1920), teinte du jeu"""
    import numpy as np
    f = os.path.join(_dossier(cache_dir), 'fond.png')
    if os.path.exists(f):
        return f
    src = trouver(cfg, 'mainmenu90_00')
    tailles, zones, g = lire_planche(src)
    z = zones['bg01']
    w, h, a = _rgba(g.blocs[z[0]])
    a = a[z[2]:z[2] + z[4], z[1]:z[1] + z[3]].astype(np.float32)
    a = a[:, 360:360 + 1920]
    for c in range(3):
        a[..., c] = np.clip(a[..., c] * TEINTE_FOND[c], 0, 255)
    a[..., 3] = 255
    _png(f, a.astype(np.uint8))
    return f


def police(cfg, cache_dir, nom):
    from . import police_jeu
    p = police_jeu.polices(cfg['data_dir'], cache_dir)
    return p.get(os.path.basename(nom))


def servir(cfg, cache_dir, chemin):
    """chemin d'URL après /ui_jeu/ -> fichier (ou None)"""
    p = chemin.strip('/').split('/')
    try:
        if p[0] == 'zone' and len(p) == 3:
            return zone(cfg, cache_dir, p[1], p[2][:-4] if p[2].endswith('.png') else p[2])
        if p[0] == 'zone' and len(p) == 4:            # (25/11) /ui_jeu/zone/<planche>/<langue>/<nom>.png
            return zone(cfg, cache_dir, p[1], p[3][:-4] if p[3].endswith('.png') else p[3], p[2])
        if p[0] == 'img' and len(p) == 3:
            return image(cfg, cache_dir, p[1], p[2].split('.')[0])
        if p[0] == 'fond.png':
            return fond(cfg, cache_dir)
        if p[0].endswith('.ttf'):
            return police(cfg, cache_dir, p[0])
    except Exception:
        return None
    return None
