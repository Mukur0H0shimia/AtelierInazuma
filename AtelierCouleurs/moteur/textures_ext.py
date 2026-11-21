"""Textures partagées entre effets (13/11/2026).

Constat : l'en-tête d'un effet (table +0x76 du G4MD = crc32 des noms de textures) cite parfois des textures qui ne sont
PAS dans son propre .g4tx, mais dans celui d'un autre effet du même dossier (ex. dx11/effect/event/ev60/…), ou dans la
bibliothèque commune dx11/effect/battle/common/effCmnTex. Sur 388 cas, 227 sont dans le même dossier.

Index : crc32(nom) -> [(fichier .g4tx relatif à data_dir, n° du bloc, nom)], construit en lisant SEULEMENT l'en-tête de
chaque .g4tx de dx11/effect (le nom et la table des blocs sont avant les images), gardé en cache (index_textures_effets.json).
Un bloc se lit ensuite directement (table à 0x60 + k x 0x30 + 4 : décalage, taille ; depuis le début des images).
"""
import os, re, struct, zlib, json, glob, threading

_verrou = threading.Lock()
_index = None


def _entete(chemin):
    """(noms, table [(décalage, taille)], début des images) d'un .g4tx, sans lire les images"""
    taille_f = os.path.getsize(chemin)
    from moteur import donnees_virtuelles as _dv           # lecture directe : en-tête sans sortir le fichier
    h = _dv.debut(chemin, 0x30)
    if h[:4] != b'G4TX':
        return [], [], 0
    n = struct.unpack_from('<H', h, 0x20)[0]
    total = struct.unpack_from('<I', h, 0x2C)[0]
    deb = taille_f - total
    if deb <= 0 or deb > 4 * 1024 * 1024:
        return [], [], 0
    tete = _dv.debut(chemin, deb)
    noms = [m.group()[:-1].decode() for m in re.finditer(rb'[A-Za-z0-9][A-Za-z0-9_]{2,40}\x00', tete)][-n:]
    table = [struct.unpack_from('<II', tete, 0x60 + k * 0x30 + 4) for k in range(n)] if 0x60 + n * 0x30 <= len(tete) else []
    return noms, table, deb


def index(data_dir, cache_dir):
    global _index
    with _verrou:
        if _index is not None:
            return _index
        f = os.path.join(cache_dir, 'index_textures_effets.json')
        if os.path.exists(f):
            _index = json.load(open(f, encoding='utf-8'))
            return _index
        idx = {}
        for g in sorted(glob.glob(os.path.join(data_dir, 'dx11', 'effect', '**', '*.g4tx'), recursive=True)):
            try:
                noms, table, deb = _entete(g)
            except (OSError, struct.error):
                continue
            rel = os.path.relpath(g, data_dir).replace(os.sep, '/')
            for k, nom in enumerate(noms):
                idx.setdefault('%08x' % zlib.crc32(nom.encode()), []).append([rel, k, nom])
        os.makedirs(cache_dir, exist_ok=True)
        json.dump(idx, open(f, 'w', encoding='utf-8'))
        _index = idx
        return idx


def chercher(data_dir, cache_dir, crc, dossier_rel):
    """(fichier, n° du bloc, nom) de la texture crc ; de préférence dans le même dossier (ex. 'dx11/effect/event/ev60')"""
    cands = index(data_dir, cache_dir).get('%08x' % crc) or []
    if not cands:
        return None
    meme = [c for c in cands if c[0].startswith(dossier_rel + '/')]
    return (meme or cands)[0]


def bloc(data_dir, rel, k):
    """octets DDS du bloc k d'un .g4tx"""
    chemin = os.path.join(data_dir, *rel.split('/'))
    noms, table, deb = _entete(chemin)
    if k >= len(table):
        return None
    off, taille = table[k]
    with open(chemin, 'rb') as f:
        f.seek(deb + off)
        b = f.read(taille)
    return b if b[:4] == b'DDS ' else None
