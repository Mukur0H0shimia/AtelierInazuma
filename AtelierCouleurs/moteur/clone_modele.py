"""COPIE RECOLORÉE D'UN MODÈLE DE PERSONNAGE (esprit guerrier, objet de technique…) pour le mod de l'Atelier (14/11/2026).
Méthode du mod Mukuro (Mukuro_atelier/ecrire_orbes.py, vérifiée en jeu) : seuls les noms des ENTRÉES du paquet changent
(avec leurs crc32 et l'ordre trié) ; les noms internes (nœuds, maillages, textures) restent ceux du modèle d'origine, pour
que les animations de la cinématique (rangées sous le nom de l'acteur) continuent de viser les mêmes pièces.
Textures retouchées : réencodées dans le format du jeu (BC7, même en-tête et même nombre de niveaux que l'original).
Lecture seule des fichiers du jeu ; n'écrit que dans le dossier du mod.

    python clone_modele.py <data_dir> <code_origine> <code_neuf> <dossier_assets_chr> <textures.json>
textures.json : {nom_texture: chemin_png}
"""
try:   # lecture directe des paquets du jeu (variable ATELIER_JEU_DIRECT posée par l'Atelier)
    import os as _os_v, sys as _sys_v
    _sys_v.path.insert(0, _os_v.path.join(_os_v.path.dirname(_os_v.path.dirname(_os_v.path.abspath(__file__)))))
    from moteur import donnees_virtuelles as _dv
    _dv.depuis_env()
except Exception as _ex_v:
    print('lecture directe :', _ex_v)
import sys, os, re, json, struct, zlib, multiprocessing

ICI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(ICI)), 'AtelierMaillots'))


def renommer_paquet(b, n_entrees, anc, neuf):
    """paquet G4PK : crc32 des noms d'entrées, ordre trié (u16) juste après, noms en clair (copie de Mukuro_atelier/ecrire_michael.py)"""
    b = bytearray(b)
    t = 0x40 + 8 * n_entrees
    noms = [m.group().decode() for m in re.finditer(rb'[a-z0-9_]+\.g4[a-z]{2}', bytes(b[t:t + 0x60]))][:n_entrees]
    nouveaux = [n.replace(anc, neuf) for n in noms]
    crcs = [zlib.crc32(n.encode()) for n in nouveaux]
    for k, c in enumerate(crcs):
        assert struct.unpack_from('<I', b, t + 4 * k)[0] == zlib.crc32(noms[k].encode()), 'paquet inattendu'
        struct.pack_into('<I', b, t + 4 * k, c)
    ordre = sorted(range(n_entrees), key=lambda k: crcs[k])
    for k, v in enumerate(ordre):
        struct.pack_into('<H', b, t + 4 * n_entrees + 2 * k, v)
    tete = bytes(b[:0x100]).replace(anc.encode(), neuf.encode())
    return tete + bytes(b[0x100:])


def dossier_chr(data_dir, code):
    for r, ds, fs in os.walk(os.path.join(data_dir, 'common', 'chr')):
        if os.path.basename(r) == code and code + '.objbin' in fs:
            return os.path.relpath(r, os.path.join(data_dir, 'common', 'chr')).replace('\\', '/')
    return None


def main():
    data, anc, neuf, sortie, f_tex = sys.argv[1:6]
    # (15/11/2026) même longueur obligatoire : renommer_paquet remplace le nom dans l'en-tête ; « ev60_00830 » -> « e007000 »
    # raccourcissait le fichier de 6 octets (squelette à 122 au lieu de 128) : modèle illisible, dragon invisible en jeu
    assert len(anc) == len(neuf), 'code neuf de longueur différente : %s -> %s' % (anc, neuf)
    from lib import images
    rel = dossier_chr(data, anc)
    assert rel, 'modèle introuvable : ' + anc
    src = os.path.join(data, 'common', 'chr', *rel.split('/'))
    out = os.path.join(sortie, *os.path.dirname(rel).split('/'), neuf) if '/' in rel else os.path.join(sortie, neuf)
    os.makedirs(out, exist_ok=True)
    pk = open(os.path.join(src, anc + '.g4pkm'), 'rb').read()
    n = struct.unpack_from('<H', pk, 0x20)[0]
    open(os.path.join(out, neuf + '.g4pkm'), 'wb').write(renommer_paquet(pk, n, anc, neuf))
    open(os.path.join(out, neuf + '.g4mg'), 'wb').write(open(os.path.join(src, anc + '.g4mg'), 'rb').read())
    open(os.path.join(out, neuf + '.objbin'), 'wb').write(open(os.path.join(src, anc + '.objbin'), 'rb').read().replace(anc.encode(), neuf.encode()))
    for f in os.listdir(src):                                       # paquets de poses (_p010…) : simple renommage
        if f.startswith(anc + '_') and f.endswith('.g4pk'):
            b = open(os.path.join(src, f), 'rb').read()
            open(os.path.join(out, f.replace(anc, neuf)), 'wb').write(renommer_paquet(b, struct.unpack_from('<H', b, 0x20)[0], anc, neuf))
            open(os.path.join(out, f), 'wb').write(b)   # (15/11/2026) aussi sous le nom d'origine (Zan 0.9.33-0.9.34)
    g = images.G4TX(open(os.path.join(data, 'dx11', 'chr', *rel.split('/'), anc + '.g4tx'), 'rb').read())
    rempl = {}
    textures = json.load(open(f_tex, encoding='utf-8'))
    with multiprocessing.Pool(max(1, (os.cpu_count() or 2) - 1)) as pool:
        for nom, png in textures.items():
            if nom not in g.noms:
                print('texture inconnue', nom); continue
            bl = g.blocs[g.noms.index(nom)]
            dxgi = struct.unpack_from('<I', bl, 128)[0] if bl[84:88] == b'DX10' else None
            if dxgi not in (98, 99):
                print('format non pris en charge (gardée)', nom, dxgi); continue
            w, h, r = images.lire_png(png)
            if (w, h) != g.taille(nom):
                print('taille différente (gardée)', nom, (w, h), g.taille(nom)); continue
            rempl[nom] = images.dds_bc7(w, h, [bytearray(x) for x in r], bl[:148], images.mips_dds(bl), pool)
    open(os.path.join(out, neuf + '.g4tx'), 'wb').write(g.reconstruire(rempl))
    print(json.dumps({'dossier': rel.rsplit('/', 1)[0] if '/' in rel else '', 'textures': sorted(rempl), 'sortie': out}))


if __name__ == '__main__':
    main()
