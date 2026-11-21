r"""Lecture DIRECTE des fichiers du jeu dans ses paquets (data\cpk_list.cfg.bin + data\packs\*.cpk) : plus besoin
d'extraire les 110 Go du jeu. Reprise du lecteur de notre chargeur de mods (Chargeur\outils\l5cpk.py), accélérée :
  - cpk_list.cfg.bin : AES-256-CBC (clé et IV du jeu, masqués) déchiffré par Windows (bcrypt.dll), sans dépendance ;
  - .cpk : XOR dont la clé = crc32(nom de l'archive), position comprise : calculé d'un coup avec numpy ;
  - archive CPK de CRI : tables @UTF ; fichiers parfois compressés en CRILAYLA.
Direct reading of the game files inside its packs: no need to extract the game (110 GB).
"""
import os, struct, zlib, threading, ctypes
import numpy as np

_T = np.zeros(256, np.uint32)
for _i in range(256):
    _c = _i
    for _ in range(8):
        _c = (_c >> 1) ^ 0xEDB88320 if _c & 1 else _c >> 1
    _T[_i] = _c


_DLL = None                                    # moteur/natif/paquets.dll (même calcul en C, ~100 fois plus vite)
try:
    _DLL = ctypes.CDLL(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'natif', 'paquets.dll'))
    _DLL.xor_cpk.argtypes = (ctypes.c_char_p, ctypes.c_int64, ctypes.c_int64, ctypes.c_uint32)
    _DLL.xor_cpk.restype = None
    _DLL.crilayla.argtypes = (ctypes.c_char_p, ctypes.c_int64, ctypes.c_char_p, ctypes.c_int64)
    _DLL.crilayla.restype = ctypes.c_int
    _DLL.decoder_bc.argtypes = (ctypes.c_char_p, ctypes.c_int64, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_char_p)
    _DLL.decoder_bc.restype = ctypes.c_int
except (OSError, AttributeError):
    _DLL = None


def xor(buf, pos, cle):
    """déchiffre (ou chiffre : même opération) buf, qui commence à la position pos du fichier"""
    n = len(buf)
    if not n:
        return b''
    if _DLL is not None:
        b = ctypes.create_string_buffer(bytes(buf), n)
        _DLL.xor_cpk(b, n, pos, cle & 0xffffffff)
        return b.raw
    p = np.arange(pos, pos + n, dtype=np.int64)
    blocs = np.arange(pos & ~3, ((pos + n - 1) & ~3) + 1, 4, dtype=np.int64)
    v = (~blocs.astype(np.uint32)) & np.uint32(0xffffffff)
    for k in range(4):
        v = (v >> np.uint32(8)) ^ _T[(v & np.uint32(0xff)) ^ np.uint32((cle >> (8 * k)) & 0xff)]
    K = (~v) & np.uint32(0xffffffff)
    K = K[((p & ~3) - blocs[0]) // 4].astype(np.uint32)
    s = (2 * (p & 3)).astype(np.uint32)
    x = (((((K >> (s + 8)) & 3) | (((K >> s) << 2) & 0xff)) << 2 | ((K >> (s + 16)) & 3)) << 2 | ((K >> (s + 24)) & 3))
    return (np.frombuffer(buf, np.uint8) ^ (x & 0xff).astype(np.uint8)).tobytes()


def _xor_petit(buf, pos, cle):
    """même calcul, en Python pur (pour les 32 octets de la clé)"""
    b = bytearray(buf)
    K = None
    for i in range(len(b)):
        p = pos + i
        if K is None or (p & 3) == 0:
            v = (~(p & 0xfffffffc)) & 0xffffffff
            for k in range(4):
                v = (v >> 8) ^ int(_T[(v & 0xff) ^ ((cle >> (8 * k)) & 0xff)])
            K = (~v) & 0xffffffff
        s = 2 * (p & 3)
        b[i] ^= ((((K >> (s + 8)) & 3) | (((K >> s) << 2) & 0xff)) << 2 | ((K >> (s + 16)) & 3)) << 2 & 0xff | ((K >> (s + 24)) & 3)
    return bytes(b)


_CLE = struct.pack('<8I', 0x72c9cb21, 0x178bf2f9, 0x6450e29d, 0x4da98cd1, 0x1e908d53, 0x750df696, 0x43d9a87a, 0x584fe242)
_IV = struct.pack('<4I', 0x3f8e4b6d, 0xf0c9492f, 0x3844e69d, 0xb0cb1ee3)


def _aes_cbc(donnees, cle, iv):
    """AES-CBC (déchiffrement) par Windows CNG (bcrypt.dll)"""
    bc = ctypes.WinDLL('bcrypt')
    h = ctypes.c_void_p()
    assert bc.BCryptOpenAlgorithmProvider(ctypes.byref(h), ctypes.c_wchar_p('AES'), None, 0) == 0
    mode = ctypes.create_unicode_buffer('ChainingModeCBC')
    assert bc.BCryptSetProperty(h, ctypes.c_wchar_p('ChainingMode'), mode, ctypes.sizeof(mode), 0) == 0
    k = ctypes.c_void_p()
    cb = ctypes.create_string_buffer(cle)
    assert bc.BCryptGenerateSymmetricKey(h, ctypes.byref(k), None, 0, cb, len(cle), 0) == 0
    entree = ctypes.create_string_buffer(donnees, len(donnees))
    sortie = ctypes.create_string_buffer(len(donnees))
    ivb = ctypes.create_string_buffer(iv, len(iv))
    n = ctypes.c_ulong()
    assert bc.BCryptDecrypt(k, entree, len(donnees), None, ivb, len(iv), sortie, len(donnees), ctypes.byref(n), 0) == 0
    bc.BCryptDestroyKey(k); bc.BCryptCloseAlgorithmProvider(h, 0)
    return sortie.raw[:n.value]


def _utf(b, o=0):
    """table @UTF de CRI -> liste de lignes {colonne: valeur}"""
    assert b[o:o + 4] == b'@UTF', b[o:o + 4]
    base = o + 8
    off_lignes, off_txt, off_don, nom, ncol, lg, nlig = struct.unpack_from('>IIII HHI', b, o + 8)
    off_lignes &= 0xffff

    def txt(x):
        a = base + off_txt + x
        return b[a:b.index(b'\0', a)].decode('utf-8', 'replace')
    TAILLE = {0: 'B', 1: 'b', 2: 'H', 3: 'h', 4: 'I', 5: 'i', 6: 'Q', 7: 'q', 8: 'f', 9: 'd'}

    def val(t, p):
        if t == 0xA:
            return txt(struct.unpack_from('>I', b, p)[0]), 4
        if t == 0xB:
            a, n = struct.unpack_from('>II', b, p)
            return b[base + off_don + a: base + off_don + a + n], 8
        f = '>' + TAILLE[t]
        return struct.unpack_from(f, b, p)[0], struct.calcsize(f)
    cols, p = [], o + 32
    for _ in range(ncol):
        fl = b[p]; nm = txt(struct.unpack_from('>I', b, p + 1)[0]); p += 5
        st, t = fl & 0xf0, fl & 0x0f
        c = None
        if st == 0x30:
            c, n = val(t, p); p += n
        cols.append((nm, st, t, c))
    lignes = []
    for r in range(nlig):
        p = base + off_lignes + r * lg
        d = {}
        for nm, st, t, c in cols:
            if st == 0x50:
                d[nm], n = val(t, p); p += n
            elif st == 0x30:
                d[nm] = c
            else:
                d[nm] = None
        lignes.append(d)
    return lignes


def crilayla(src):
    """décompression CRILAYLA (format public de CRI)"""
    taille, entete_off = struct.unpack_from('<II', src, 8)
    if _DLL is not None:
        out = ctypes.create_string_buffer(taille + 0x100)
        if _DLL.crilayla(bytes(src), len(src), out, taille + 0x100) == 0:
            return out.raw
    sortie = bytearray(taille + 0x100)
    sortie[:0x100] = src[entete_off + 0x10: entete_off + 0x110]
    pos_in = entete_off + 0x10 - 1
    bits, octet = 0, 0
    ecrits, fin = 0, taille
    T5 = (2, 3, 5, 8)
    while ecrits < fin:
        # lire(1)
        if bits == 0:
            octet = src[pos_in]; pos_in -= 1; bits = 8
        bits -= 1
        if (octet >> bits) & 1:
            v = 0; n = 13
            while n:
                if bits == 0:
                    octet = src[pos_in]; pos_in -= 1; bits = 8
                k = n if n < bits else bits
                v = (v << k) | ((octet >> (bits - k)) & ((1 << k) - 1)); bits -= k; n -= k
            recul = v + 3
            lg = 3
            i = 0
            while True:
                n = T5[i if i < 3 else 3]; v = 0; m = n
                while m:
                    if bits == 0:
                        octet = src[pos_in]; pos_in -= 1; bits = 8
                    k = m if m < bits else bits
                    v = (v << k) | ((octet >> (bits - k)) & ((1 << k) - 1)); bits -= k; m -= k
                lg += v
                if v != (1 << n) - 1:
                    break
                i += 1
            a = 0x100 + fin - 1 - ecrits
            for _ in range(lg):
                sortie[a] = sortie[a + recul]; a -= 1
            ecrits += lg
        else:
            v = 0; m = 8
            while m:
                if bits == 0:
                    octet = src[pos_in]; pos_in -= 1; bits = 8
                k = m if m < bits else bits
                v = (v << k) | ((octet >> (bits - k)) & ((1 << k) - 1)); bits -= k; m -= k
            sortie[0x100 + fin - 1 - ecrits] = v
            ecrits += 1
    return bytes(sortie)


class _Archive:
    def __init__(self, chemin):
        self.chemin = chemin
        self.cle = zlib.crc32(os.path.basename(chemin).encode())
        self.verrou = threading.Lock()
        self.f = open(chemin, 'rb')
        self.dernier = None                    # (nom, octets) du dernier fichier compressé lu par debut()
        h = self.lire(0, 0x800)
        assert h[:4] == b'CPK ', h[:4]
        n = struct.unpack_from('<I', h, 8)[0]
        tete = _utf(self.lire(0x10, n), 0)[0]
        self.toc = tete.get('TocOffset')
        t = self.lire(self.toc, 16)
        n = struct.unpack_from('<I', t, 8)[0]
        self.fichiers = {}
        for r in _utf(self.lire(self.toc + 0x10, n), 0):
            self.fichiers[((r.get('DirName') or '') + '/' + r['FileName']).strip('/').lower()] = r

    def lire(self, pos, n):
        with self.verrou:
            self.f.seek(pos)
            d = self.f.read(n)
        return xor(d, pos, self.cle)

    def extraire(self, nom):
        n = nom.lower()
        r = self.fichiers.get(n) or self.fichiers.get('data/' + n) or self.fichiers[n.split('/', 1)[-1]]
        d = self.lire(self.toc + r['FileOffset'], r['FileSize'])
        return crilayla(d) if d[:8] == b'CRILAYLA' else d

    def debut(self, nom, n):
        """les n premiers octets du fichier (sans lire tout le fichier s'il n'est pas compressé)"""
        k = nom.lower()
        r = self.fichiers.get(k) or self.fichiers.get('data/' + k) or self.fichiers[k.split('/', 1)[-1]]
        pos = self.toc + r['FileOffset']
        h = self.lire(pos, 16)
        if h[:8] == b'CRILAYLA':
            taille, eoff = struct.unpack_from('<II', h, 8)
            if n <= 0x100:                                   # CRILAYLA garde les 0x100 premiers octets tels quels
                return self.lire(pos + eoff + 0x10, min(n, 0x100, taille + 0x100))
            m = self.dernier                                 # sinon il faut tout décompresser (gardé pour l'appel suivant)
            if m is None or m[0] != k:
                m = self.dernier = (k, self.extraire(nom))
            return m[1][:n]
        return self.lire(pos, min(n, r['FileSize']))


class Jeu:
    """les fichiers d'un dossier de jeu (celui qui a nie.exe), lus dans ses paquets"""

    def __init__(self, jeu_dir, cache_dir):
        import json
        self.jeu = jeu_dir
        self.archives = {}
        self.verrou = threading.Lock()
        f = os.path.join(cache_dir, 'liste_paquets.json')
        src = os.path.join(jeu_dir, 'data', 'cpk_list.cfg.bin')
        sig = '%d-%d' % (os.path.getsize(src), int(os.path.getmtime(src)))
        L = None
        if os.path.isfile(f):
            try:
                j = json.load(open(f, encoding='utf-8'))
                if j.get('sig') == sig:
                    L = j['liste']
            except ValueError:
                pass
        if L is None:
            L = self._lire_liste(src)
            os.makedirs(cache_dir, exist_ok=True)
            json.dump({'sig': sig, 'liste': L}, open(f, 'w', encoding='utf-8'))
        self.liste = L                         # chemin (casse du jeu, « common/... ») -> [archive ou None, taille]
        self.bas = {k.lower(): k for k in L}
        self.dossiers = {}                     # dossier (minuscules) -> {nom: True si dossier}
        for k in L:
            parts = k.split('/')
            for i in range(len(parts)):
                d = '/'.join(parts[:i]).lower()
                self.dossiers.setdefault(d, {})[parts[i]] = i < len(parts) - 1 or self.dossiers.get(d, {}).get(parts[i], False)

    @staticmethod
    def _lire_liste(src):
        import sys
        d = _aes_cbc(open(src, 'rb').read(), _xor_petit(_CLE, 0, 0x8a90aba9), _xor_petit(_IV, 0, 0x4c801618))
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        from moteur import cfgbin
        out = {}
        for crc, v in cfgbin.lire(d):
            if len(v) == 5 and v[0] is not None and v[1] is not None:
                k = v[0] + v[1]
                k = k[5:] if k.lower().startswith('data/') else k      # « data/common/... » -> « common/... »
                out[k] = [(v[2] or '') + (v[3] or '') if v[3] else None, v[4]]
        return out

    def existe(self, rel):
        return rel.lower() in self.bas

    def taille(self, rel):
        return self.liste[self.bas[rel.lower()]][1]

    def _archive(self, arch):
        with self.verrou:
            a = self.archives.get(arch)
            if a is None:
                a = self.archives[arch] = _Archive(os.path.join(self.jeu, *arch.split('/')))
        return a

    def lire(self, rel):
        """octets du fichier « common/... » (ou « dx11/... »)"""
        k = self.bas[rel.lower()]
        arch = self.liste[k][0]
        if arch is None:                       # fichier libre dans data/
            return open(os.path.join(self.jeu, 'data', *k.split('/')), 'rb').read()
        return self._archive(arch).extraire(k)

    def debut(self, rel, n):
        """les n premiers octets du fichier (en-têtes : pas besoin de sortir le fichier entier)"""
        k = self.bas[rel.lower()]
        arch = self.liste[k][0]
        if arch is None:
            with open(os.path.join(self.jeu, 'data', *k.split('/')), 'rb') as f:
                return f.read(n)
        return self._archive(arch).debut(k, n)
