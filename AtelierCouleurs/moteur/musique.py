"""(22/11/2026, idée de muku : « une petite musique de fond ») musique de fond de l'Atelier.

Le thème de l'écran titre du jeu (sound_asset/bgm_title.acb + .awb, son « bg00010 »), lu dans le jeu de la personne
(jamais copié dans le partage), décodé UNE fois en .ogg dans cache/musique (ffmpeg, comme moteur/son.py).
Petite banque (2 Mo) : en lecture directe des paquets, la sortir ne coûte rien (bgm.awb ferait 865 Mo).

Boucle comme le jeu : bloc « loop » de l'en-tête HCA (bloc de début, bloc de fin, décalage avant, remplissage après ;
1024 échantillons par bloc). ffmpeg garde le silence de tête de l'encodeur (durée = blocs × 1024), donc :
début = début × 1024 + avant ; fin = fin × 1024 + (1024 − après). Thème titre : 5,571 s -> 63,171 s.
"""
import os, json, struct, subprocess
from moteur import son, outils_ext

PISTES = {'titre': ('bgm_title', 'bg00010', "Thème de l'écran titre")}


def boucle_hca(h):
    """en-tête HCA -> (fréquence, début_s, fin_s) de la boucle, ou (fréquence, None, None) sans boucle"""
    assert h[:4] == b'HCA\0', 'pas un HCA'
    taille = struct.unpack_from('>H', h, 6)[0]
    o, rate, boucle = 8, 48000, None
    tailles = {b'comp': 16, b'dec\0': 12, b'ciph': 6, b'rva\0': 8, b'vbr\0': 8, b'ath\0': 6}
    while o < taille:
        nom = bytes(c & 0x7F for c in h[o:o + 4])
        if nom == b'fmt\0':
            rate = int.from_bytes(h[o + 5:o + 8], 'big'); o += 16
        elif nom == b'loop':
            boucle = struct.unpack_from('>IIHH', h, o + 4); o += 16
        elif nom == b'comm':
            o += 5 + h[o + 4]
        elif nom in tailles:
            o += tailles[nom]
        else:                                    # pad\0 ou inconnu : fin des blocs utiles
            break
    if not boucle:
        return rate, None, None
    ls, le, avant, apres = boucle
    return rate, (ls * 1024 + avant) / rate, (le * 1024 + (1024 - apres)) / rate


def ogg(data_dir, cache_dir, piste='titre'):
    """-> (chemin du .ogg, {'debut', 'fin', 'nom'}) ; (None, message) si impossible"""
    if piste not in PISTES:
        return None, 'musique inconnue'
    banque, nom, titre = PISTES[piste]
    d = os.path.join(cache_dir, 'musique'); os.makedirs(d, exist_ok=True)
    out, info = os.path.join(d, piste + '.ogg'), os.path.join(d, piste + '.json')
    if os.path.exists(out) and os.path.exists(info):
        try:
            return out, json.load(open(info, encoding='utf-8'))
        except (OSError, ValueError):
            pass
    acb = os.path.join(data_dir, 'common', 'sound_asset', banque + '.acb')
    if not os.path.exists(acb):
        return None, 'banque de musique introuvable dans le jeu'
    b = son.Banque(acb)
    ids = b.ondes(nom)
    if not ids:
        return None, 'musique introuvable dans la banque'
    h = b.extrait(ids[0])
    _, debut, fin = boucle_hca(h)
    hca, tmp = out[:-4] + '.tmp.hca', out[:-4] + '.tmp.ogg'
    # (22/11, « énormément saturée ») décodé par moteur/hca.py ; ffmpeg ne fait plus que l'encodage .ogg
    entree, pcm = ['-i', hca], None
    try:
        from moteur import hca as _hca
        x, e = _hca.decoder(h)
        pcm = x.astype('<f4').tobytes()
        entree = ['-f', 'f32le', '-ar', str(e['freq']), '-ac', str(e['canaux']), '-i', '-']
    except Exception as ex:                       # format non pris en charge : décodage de ffmpeg (moins bon)
        print('musique : décodeur HCA ->', ex)
        open(hca, 'wb').write(h)
    try:
        r = subprocess.run([outils_ext.ffmpeg(), '-v', 'error', '-y'] + entree + ['-c:a', 'libvorbis', '-q:a', '5', tmp],
                           input=pcm, capture_output=True)
        r.stderr = r.stderr.decode('utf-8', 'replace')
        if r.returncode != 0 or not os.path.exists(tmp):
            return None, 'décodage impossible : ' + (r.stderr or '')[:200]
        os.replace(tmp, out)
    except OSError as ex:
        return None, 'ffmpeg introuvable (%s)' % ex
    finally:
        for f in (hca, tmp):
            try:
                os.remove(f)
            except OSError:
                pass
    meta = {'debut': debut, 'fin': fin, 'nom': titre}
    json.dump(meta, open(info, 'w', encoding='utf-8'))
    return out, meta
