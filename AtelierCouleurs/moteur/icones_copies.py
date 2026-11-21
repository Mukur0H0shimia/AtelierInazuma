"""(16/11/2026) IMAGES DES COPIES FAITES TOUTES SEULES : portrait d'un nouveau joueur (menu/200_icon/10_icon_chr/face/<code>_l)
et portrait d'une copie d'esprit (…/aura_fs/<code>_l, celui de la grande plaque de l'esprit en match).

Les recolorations de l'Atelier sont peintes librement (bandes, motifs, ailes noires…) : un simple changement de teinte du
portrait d'origine ne peut pas les reproduire. L'image vient donc d'une PHOTO DU MODÈLE 3D RECOLORÉ prise dans l'Atelier
(web/app.js photoIcone : visage de face pour un joueur, buste pour un esprit, fond transparent, 256 x 256).

LU (portraits du jeu) : .g4tx à une ou deux images 256 x 256 en BC7 (DXGI 98), 1 niveau (face/c11260010_l : c11260010_1_l00
et _2_l00 ; aura_fs/k000010_l : k000010_l00). Toutes les images du fichier reçoivent la photo, encodée avec le même en-tête ;
les noms internes sont ensuite renommés (bustes.renommer, comme avant pour la copie du portrait d'origine).
"""
import os, re, base64, tempfile, shutil, struct
from lib import images, bustes                  # noqa: E402 (Atelier Maillots, mis dans le chemin par moteur.g4)
from . import bc7_fin                           # (16/11/2026) BC7 à deux groupes par bloc : sans « pixels bizarres »


def _rows(data_url, w, h, tmp):
    f = os.path.join(tmp, 'photo.png')
    open(f, 'wb').write(base64.b64decode(data_url.split(',', 1)[1]))
    W, H, rows = images.lire_png(f)
    if (W, H) != (w, h):                          # mise à la taille (plus proche voisin, la photo arrive déjà en 256)
        rows = [bytearray(b''.join(bytes(rows[y * H // h][(x * W // w) * 4:(x * W // w) * 4 + 4]) for x in range(w))) for y in range(h)]
    return [bytearray(r) for r in rows]


def portrait_photo(src_g4tx, data_url, anc, neuf):
    """octets du .g4tx du portrait : chaque image remplacée par la photo, noms renommés anc -> neuf"""
    g = images.G4TX(src_g4tx)
    tmp = tempfile.mkdtemp()
    try:
        rempl = {}
        for n, bl in zip(g.noms, g.blocs):
            h, w = struct.unpack_from('<II', bl, 12)
            rempl[n] = bc7_fin.dds_bc7(w, h, _rows(data_url, w, h, tmp), bl[:148], images.mips_dds(bl))
        return bustes.renommer(g.reconstruire(rempl), anc, neuf)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def paires_textures(tx_orig, tx_modif, anc, neuf):
    """(16/11/2026) textures d'origine / modifiées d'une copie (octets des deux .g4tx) -> [((w, h, rangées), (w, h, rangées))]
    pour transfert_couleurs ; images assez grandes (cheveux, peau, ailes…). Les images restées telles quelles servent aussi :
    elles disent quelles couleurs n'ont PAS changé (peau d'un visage gardé : sinon la peau de la photo passe pour le jaune
    pâle des pointes de cheveux). Aucune image changée -> []"""
    from . import g4
    o, m = images.G4TX(tx_orig), images.G4TX(tx_modif)
    res, change = [], False
    for n, bo in zip(o.noms, o.blocs):
        n2 = n if n in m.noms else n.replace(anc, neuf)
        if n2 not in m.noms:
            continue
        bm = m.blocs[m.noms.index(n2)]
        if struct.unpack_from('<II', bo, 12) != struct.unpack_from('<II', bm, 12):
            continue
        h, w = struct.unpack_from('<II', bo, 12)
        if w * h < 128 * 128 or re.search(r'(nml|oc|sp|spm|line|msk)$', n):
            continue                              # cartes techniques (ombre jaune/rouge, reflets…) : pas des couleurs (app.js carteTech)
        a = g4.decoder_texture(bo)
        res.append((a, a if bm == bo else g4.decoder_texture(bm)))
        change |= bm != bo
    return res if change else []


def portrait_dessin(src_g4tx, paires, data_url, anc, neuf):
    """(16/11/2026) le DESSIN du portrait d'origine recoloré comme les modifs (moteur/transfert_couleurs.py) ; la photo du
    modèle modifié (si l'Atelier l'envoie) dit où va chaque couleur d'une partie peinte en plusieurs couleurs"""
    from . import g4, transfert_couleurs as T
    co = T.combiner(*[T.correspondances(a, b) for a, b in paires])
    g = images.G4TX(src_g4tx)
    tmp = tempfile.mkdtemp()
    try:
        rempl = {}
        for n, bl in zip(g.noms, g.blocs):
            w, h, rows = g4.decoder_texture(bl)
            ph = (w, h, _rows(data_url, w, h, tmp)) if data_url else None
            rempl[n] = bc7_fin.dds_bc7(w, h, T.recolorer((w, h, rows), co, ph), bl[:148], images.mips_dds(bl))
        return bustes.renommer(g.reconstruire(rempl), anc, neuf)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def ecrire_portrait(src, dst, data_url, anc, neuf, paires=None):
    """src : portrait du jeu ; dst : portrait de la copie. Renvoie ce qui a été fait :
    'dessin' : (16/11/2026, par défaut) dessin d'origine recoloré comme les modifs (paires = textures d'origine / modifiées) ;
    'photo'  : photo du modèle recoloré (si le recoloriage échoue) ;
    False    : portrait de l'original renommé (rien n'a changé de couleur)"""
    b = open(src, 'rb').read()
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    if paires:
        try:
            open(dst, 'wb').write(portrait_dessin(b, paires, data_url, anc, neuf))
            return 'dessin'
        except Exception as e:                    # noqa: BLE001 — repli sur la photo, la copie ne doit pas échouer pour l'image
            print('portrait : recoloriage du dessin impossible (%s), photo à la place' % e)
    open(dst, 'wb').write(portrait_photo(b, data_url, anc, neuf) if data_url else bustes.renommer(b, anc, neuf))
    return 'photo' if data_url else False
