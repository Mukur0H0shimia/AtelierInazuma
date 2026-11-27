"""Son des cinématiques : banques CRI (sound_asset/*.acb + *.awb), audio HCA NON chiffré (ciph = 0), décodé par ffmpeg.

- la scène dit quoi jouer : event_cfg/snd/<id>_snd.cfg.bin, commande 0xBA67E844 [canal, ?, NOM DU SON, …] à l'image f
  (ex. Frappe stellaire : 'ev60_01430_me' à l'image 0 = tous les bruitages, dans waza_stream.acb) ;
- .acb = tables « @UTF » imbriquées (gros-boutiste) : CueNameTable (nom -> CueIndex) -> CueTable (ReferenceType,
  ReferenceIndex) -> SynthTable (ReferenceItems) / SequenceTable (TrackIndex) -> TrackTable (EventIndex) ->
  TrackEventTable (commandes 2000 = jouer (type, index)) -> WaveformTable (StreamAwbId / MemoryAwbId) ;
- .awb = « AFS2 » : liste d'ids, liste de décalages, extraits HCA alignés.
"""
from moteur import outils_ext as _outils_ext  # noqa: E402  (ffmpeg fourni)
import os, struct, subprocess, glob


# ------------------------------------------------------------------ @UTF
def utf(b, o=0):
    """table @UTF -> liste de lignes {colonne: valeur}"""
    assert b[o:o + 4] == b'@UTF', 'pas une table @UTF'
    base = o + 8
    _, rows_off, str_off, data_off, name_off, ncol, row_w, nrows = struct.unpack_from('>HHIIIHHI', b, base)
    p = base + 24
    chaine = lambda x: b[base + str_off + x:b.index(b'\0', base + str_off + x)].decode('utf-8', 'replace')
    TAILLE = {0: 1, 1: 1, 2: 2, 3: 2, 4: 4, 5: 4, 6: 8, 7: 8, 8: 4, 9: 8, 0xA: 4, 0xB: 8}
    FMT = {0: '>B', 1: '>b', 2: '>H', 3: '>h', 4: '>I', 5: '>i', 6: '>Q', 7: '>q', 8: '>f', 9: '>d'}

    def valeur(t, at):
        if t in FMT:
            return struct.unpack_from(FMT[t], b, at)[0]
        if t == 0xA:
            return chaine(struct.unpack_from('>I', b, at)[0])
        if t == 0xB:
            do, ds = struct.unpack_from('>II', b, at)
            return b[base + data_off + do: base + data_off + do + ds]
        return None
    cols = []
    for _ in range(ncol):
        fl = b[p]; p += 1
        nom = chaine(struct.unpack_from('>I', b, p)[0]) if fl & 0x10 else ''
        if fl & 0x10:
            p += 4
        t = fl & 0x0F
        defaut = None
        if fl & 0x20:
            defaut = valeur(t, p); p += TAILLE.get(t, 0)
        cols.append((nom, t, fl, defaut))
    lignes = []
    for r in range(nrows):
        q = base + rows_off + r * row_w
        ligne = {}
        for nom, t, fl, defaut in cols:
            if fl & 0x40:
                ligne[nom] = valeur(t, q); q += TAILLE.get(t, 0)
            else:
                ligne[nom] = defaut
        lignes.append(ligne)
    return lignes


def _table(acb, nom):
    v = acb[0].get(nom)
    return utf(v) if isinstance(v, (bytes, bytearray)) and v[:4] == b'@UTF' else []


# ------------------------------------------------------------------ banque
class Banque:
    def __init__(self, chemin_acb):
        b = open(chemin_acb, 'rb').read()
        self.acb = utf(b)
        self.awb = chemin_acb[:-4] + '.awb'
        self.cues = {r['CueName']: r['CueIndex'] for r in _table(self.acb, 'CueNameTable')}
        self.cue = _table(self.acb, 'CueTable')
        self.synth = _table(self.acb, 'SynthTable')
        self.seq = _table(self.acb, 'SequenceTable')
        self.track = _table(self.acb, 'TrackTable')
        self.events = _table(self.acb, 'TrackEventTable') or _table(self.acb, 'CommandTable')
        self.wave = _table(self.acb, 'WaveformTable')

    def _items(self, typ, idx, vus):
        """(type de référence, index) -> n° de formes d'onde"""
        if (typ, idx) in vus:
            return []
        vus.add((typ, idx))
        if typ == 1:
            return [idx]
        out = []
        if typ == 2 and idx < len(self.synth):
            ri = self.synth[idx].get('ReferenceItems') or b''
            for k in range(0, len(ri) - 3, 4):
                t, i = struct.unpack_from('>HH', ri, k)
                out += self._items(t, i, vus)
        elif typ in (3, 8) and idx < len(self.seq):
            ti = self.seq[idx].get('TrackIndex') or b''
            for k in range(0, len(ti) - 1, 2):
                out += self._piste(struct.unpack_from('>H', ti, k)[0], vus)
        return out

    def _piste(self, ti, vus):
        if ti >= len(self.track):
            return []
        ei = self.track[ti].get('EventIndex')
        if ei is None or ei >= len(self.events):
            return []
        cmd = self.events[ei].get('Command') or b''
        out, k = [], 0
        while k + 3 <= len(cmd):
            code, n = struct.unpack_from('>HB', cmd, k)
            if code in (2000, 2003) and n >= 4:              # jouer : (type, index)
                t, i = struct.unpack_from('>HH', cmd, k + 3)
                out += self._items(t, i, vus)
            k += 3 + n
        return out

    def ondes(self, nom):
        """n° (dans le .awb) des extraits joués par ce son"""
        if nom not in self.cues:
            return []
        c = self.cue[self.cues[nom]]
        ids = []
        for w in self._items(c.get('ReferenceType', 0), c.get('ReferenceIndex', 0), set()):
            if w < len(self.wave):
                r = self.wave[w]
                a = r.get('StreamAwbId') if r.get('Streaming') in (1, 2) and r.get('StreamAwbId') not in (None, 0xFFFF) else r.get('MemoryAwbId', r.get('Id'))
                if a is not None and a != 0xFFFF:
                    ids.append(a)
        return ids

    def extrait(self, awb_id):
        """octets HCA de l'extrait awb_id du .awb (AFS2)"""
        with open(self.awb, 'rb') as f:
            h = f.read(16)
            assert h[:4] == b'AFS2', 'pas un AFS2'
            taille_off, taille_id = h[5], h[6]
            n, align = struct.unpack_from('<IH', h, 8)
            f.seek(16)
            ids = struct.unpack('<%d%s' % (n, 'H' if taille_id == 2 else 'I'), f.read(n * taille_id))
            offs = [int.from_bytes(f.read(taille_off), 'little') for _ in range(n + 1)]
            k = ids.index(awb_id)
            debut = offs[k] + (-offs[k]) % align
            f.seek(debut)
            return f.read(offs[k + 1] - debut)


_BANQUES = {}


def trouver_banque(data_dir, nom):
    """le .acb (de sound_asset, langues comprises) qui contient ce nom de son.
    (27/11, essai de l'Atelier public en lecture directe : « Permission denied … ev07_01900.acb ») chaque son relisait TOUS les
    .acb (et, en lecture directe, les sortait des paquets) : un fichier tout juste sorti, encore tenu par Windows (antivirus),
    faisait planter le son. Réponse gardée en mémoire ; fichier illisible : réessayé, puis passé."""
    cle = (data_dir, nom)
    if cle in _BANQUES:
        return _BANQUES[cle]
    trouve = None
    for f in sorted(glob.glob(os.path.join(data_dir, 'common', 'sound_asset', '**', '*.acb'), recursive=True)):
        for essai in range(5):
            try:
                with open(f, 'rb') as fo:
                    lu = fo.read()
                break
            except PermissionError:
                import time
                time.sleep(0.2)
            except OSError:
                lu = b''
                break
        else:
            lu = b''
        if nom.encode() in lu:
            trouve = f
            break
    _BANQUES[cle] = trouve
    return trouve


def en_ogg(data_dir, nom, cache_dir, perso=None):
    """son « nom » -> cache/sons_hca/<nom>.ogg (extraits HCA décodés et mélangés) ; None si introuvable.
    perso : voix d'un personnage -> sa banque sound_asset/ja/<perso>.acb
    (22/11/2026) décodés par moteur/hca.py : ffmpeg 8.1 lit mal les HCA v3 du jeu (son saturé, cf. hca.py) ; ffmpeg ne
    fait plus que mélanger et encoder. Nouveau dossier de cache : les sons déjà faits par ffmpeg sont refaits."""
    d = os.path.join(cache_dir, 'sons_hca'); os.makedirs(d, exist_ok=True)
    out = os.path.join(d, (perso + '_' if perso else '') + nom + '.ogg')
    if os.path.exists(out):
        return out
    if perso:
        acb = os.path.join(data_dir, 'common', 'sound_asset', 'ja', perso + '.acb')
        if not os.path.exists(acb):
            return None
    else:
        acb = trouver_banque(data_dir, nom)
    if not acb:
        return None
    b = Banque(acb)
    ids = b.ondes(perso + '_' + nom) if perso else []          # voix : « <personnage>_<réplique> » (c11090070_sp020)
    ids = ids or b.ondes(nom)
    if not ids:
        return None
    # (21/11) fichiers temporaires PROPRES à cette demande : deux demandes du même son en même temps (la page en charge
    # plusieurs) s'effaçaient leurs fichiers -> erreur 500 ; le .ogg est écrit à part puis mis en place d'un coup
    import threading, uuid
    marque = '%d_%s' % (threading.get_ident(), uuid.uuid4().hex[:6])
    from moteur import hca as _hca
    import numpy as np
    extraits = [b.extrait(i) for i in ids[:8]]
    tmp = out[:-4] + '.%s.tmp.ogg' % marque
    hcas = []
    # (22/11) mélange fait ici : les extraits joués ensemble s'additionnent ; au-delà de 1 le son écrête (saturation,
    # crête jusqu'à 2,3 avant). Ramené à 0,89 seulement s'il dépasse (les autres sons gardent leur niveau) : l'encodage .ogg
    # ajoute jusqu'à ~9 % sur les attaques (mesuré : 0,98 -> 1,07), le fichier final reste sous 1.
    try:
        decodes = [_hca.decoder(h) for h in extraits]
        freq = decodes[0][1]['freq']
        if any(e['freq'] != freq for _, e in decodes):
            raise _hca.NonPris('fréquences différentes')
        nc = max(x.shape[1] for x, _ in decodes)
        mix = np.zeros((max(len(x) for x, _ in decodes), nc), np.float32)
        for x, _ in decodes:
            mix[:len(x)] += x if x.shape[1] == nc else np.repeat(x[:, :1], nc, axis=1)
        crete = float(np.abs(mix).max()) if len(mix) else 0.0
        if crete > 0.89:
            mix *= 0.89 / crete
        f = os.path.join(d, '_%s_%s.f32' % (nom, marque))
        open(f, 'wb').write(mix.astype('<f4').tobytes()); hcas.append(f)
        cmd = [_outils_ext.ffmpeg(), '-v', 'error', '-y', '-f', 'f32le', '-ar', str(freq), '-ac', str(nc), '-i', f]
    except Exception as ex:                            # format non pris en charge : décodage de ffmpeg (moins bon)
        print('son %s : décodeur HCA -> %s' % (nom, ex))
        cmd = [_outils_ext.ffmpeg(), '-v', 'error', '-y']
        for k, h in enumerate(extraits):
            f = os.path.join(d, '_%s_%d_%s.hca' % (nom, k, marque))
            open(f, 'wb').write(h); hcas.append(f); cmd += ['-i', f]
        cmd += ['-filter_complex', ('amix=inputs=%d:normalize=0,' % len(hcas) if len(hcas) > 1 else '') + 'alimiter=limit=0.89']
    cmd += ['-c:a', 'libvorbis', '-q:a', '4', tmp]
    try:
        r = subprocess.run(cmd, capture_output=True, text=True)
        ok = r.returncode == 0 and os.path.exists(tmp)
        # (22/11) crête du fichier ENCODÉ (le .ogg dépasse parfois de plus de 9 %, et pas toujours dans le même sens :
        # 0,866 a donné 1,054 là où 0,89 donnait 0,997) : mesurée, et refait plus bas tant qu'elle dépasse 0,99 (4 fois max)
        gain = 1.0
        for _ in range(4):
            if not (ok and cmd[4:6] == ['-f', 'f32le']):
                break
            lu = subprocess.run([_outils_ext.ffmpeg(), '-v', 'error', '-i', tmp, '-f', 'f32le', '-'], capture_output=True).stdout
            c2 = float(np.abs(np.frombuffer(lu, np.float32)).max()) if lu else 0.0
            if c2 <= 0.99:
                break
            gain *= 0.96 / c2
            open(hcas[0], 'wb').write((mix * gain).astype('<f4').tobytes())
            r = subprocess.run(cmd, capture_output=True, text=True)
            ok = r.returncode == 0 and os.path.exists(tmp)
    except OSError as ex:                              # ffmpeg introuvable : pas de son, mais pas d'erreur
        print('son :', ex)
        ok = False
    for f in hcas:
        try:
            os.remove(f)
        except OSError:
            pass
    if ok:
        try:
            os.replace(tmp, out)
        except OSError:                                # une autre demande l'a mis en place juste avant
            try:
                os.remove(tmp)
            except OSError:
                pass
    return out if os.path.exists(out) else None
