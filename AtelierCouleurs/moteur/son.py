"""Son des cinématiques : banques CRI (sound_asset/*.acb + *.awb), audio HCA NON chiffré (ciph = 0), décodé par ffmpeg.

- la scène dit quoi jouer : event_cfg/snd/<id>_snd.cfg.bin, commande 0xBA67E844 [canal, ?, NOM DU SON, …] à l'image f
  (ex. Frappe stellaire : 'ev60_01430_me' à l'image 0 = tous les bruitages, dans waza_stream.acb) ;
- .acb = tables « @UTF » imbriquées (gros-boutiste) : CueNameTable (nom -> CueIndex) -> CueTable (ReferenceType,
  ReferenceIndex) -> SynthTable (ReferenceItems) / SequenceTable (TrackIndex) -> TrackTable (EventIndex) ->
  TrackEventTable (commandes 2000 = jouer (type, index)) -> WaveformTable (StreamAwbId / MemoryAwbId) ;
- .awb = « AFS2 » : liste d'ids, liste de décalages, extraits HCA alignés.
"""
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


def trouver_banque(data_dir, nom):
    """le .acb (de sound_asset, langues comprises) qui contient ce nom de son"""
    for f in sorted(glob.glob(os.path.join(data_dir, 'common', 'sound_asset', '**', '*.acb'), recursive=True)):
        if nom.encode() in open(f, 'rb').read():
            return f
    return None


def en_ogg(data_dir, nom, cache_dir, perso=None):
    """son « nom » -> cache/sons/<nom>.ogg (extraits HCA décodés par ffmpeg et mélangés) ; None si introuvable.
    perso : voix d'un personnage -> sa banque sound_asset/ja/<perso>.acb"""
    d = os.path.join(cache_dir, 'sons'); os.makedirs(d, exist_ok=True)
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
    hcas = []
    for k, i in enumerate(ids[:8]):
        f = os.path.join(d, '_%s_%d.hca' % (nom, k))
        open(f, 'wb').write(b.extrait(i))
        hcas.append(f)
    cmd = ['ffmpeg', '-v', 'error', '-y']
    for f in hcas:
        cmd += ['-i', f]
    if len(hcas) > 1:
        cmd += ['-filter_complex', 'amix=inputs=%d:normalize=0' % len(hcas)]
    cmd += ['-c:a', 'libvorbis', '-q:a', '4', out]
    r = subprocess.run(cmd, capture_output=True, text=True)
    for f in hcas:
        os.remove(f)
    return out if r.returncode == 0 and os.path.exists(out) else None
