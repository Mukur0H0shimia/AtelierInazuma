# (28/11) copie de Chargeur/outils/rdbn.py pour l'Atelier (publié sans le dossier Chargeur)
"""Tables .cfg.bin au format RDBN (Level-5) : lecture ET réécriture à l'identique (17/11/2026).
`python rdbn.py <fichiers...>` vérifie que lire puis réécrire redonne les mêmes octets.

Disposition (LU sur les fichiers du jeu ; décalages en u32 comptés depuis 0x50) :
  0x00 'RDBN'  0x04 u16 0x50 (taille en-tête)  0x06 u16 0x64  0x08 u32 0x140000
  0x0C u32 taille du fichier - 0x50
  0x26 u16 nb de types        0x28 u16 fin des types (= début des colonnes)
  0x2A u16 nb de colonnes     0x2C u16 fin des colonnes (= début des listes)
  0x2E u16 nb de listes       0x30 u16 fin des listes (= début des crc des noms)
  0x32 u16 fin des crc        0x34 u16 nb de noms      0x36 u16 fin des places des noms (= début des données)
  0x38 u32 début du bloc des noms (après les données)
  type    (0x20) : crc nom, crc ?, u16 1re colonne, u16 nb de colonnes, ...
  colonne (0x20) : crc nom, u16 type, u16 ?, u32 taille, u32 place dans la ligne, u32 nombre, ...
  liste   (0x20) : u16 type, u16 ?, u32 début (depuis le début des données), u32 taille d'une ligne, u32 nb de lignes, crc nom, ...
  données : les lignes de chaque liste, à la suite ; puis le bloc des noms (textes en clair, terminés par 0).
"""
import struct, sys


class Table:
    def __init__(self, b):
        b = bytes(b)
        assert b[:4] == b'RDBN'
        self.b = b
        h = struct.unpack_from('<13H', b, 0x26)
        (self.ntypes, self.fin_types, self.ncols, self.fin_cols, self.nlistes, self.fin_listes,
         self.fin_crc, self.nnoms, self.debut_donnees) = h[:9]
        self.off_noms = struct.unpack_from('<I', b, 0x38)[0]
        self.D = 0x50 + 4 * self.debut_donnees
        self.listes = []
        for i in range(self.nlistes):
            o = 0x50 + 4 * self.fin_cols + 0x20 * i
            typ, x, deb, lg, n, crc, off_index, a_index = struct.unpack_from('<HHIIIIII', b, o)
            lignes = [b[self.D + deb + k * lg: self.D + deb + (k + 1) * lg] for k in range(n)]
            self.listes.append({'type': typ, 'lg': lg, 'crc': crc, 'lignes': lignes, 'brut': bytearray(b[o:o + 0x20]),
                                'deb': deb, 'index': a_index == 1})
        # ce qui suit les lignes de chaque liste (index trié, bourrage, ou autre chose qu'on garde tel quel)
        debs = sorted(set(l['deb'] for l in self.listes))
        fin_tout = 0x50 + self.off_noms - self.D
        for l in self.listes:
            fin = l['deb'] + l['lg'] * len(l['lignes'])
            suiv = min([d for d in debs if d > l['deb']] or [fin_tout])
            l['suite'] = b[self.D + fin:self.D + suiv] if suiv >= fin else b''
            # « simple » : rien d'autre qu'un index trié (s'il y en a un) et du bourrage jusqu'à 4
            attendu = (2 * len(l['lignes']) if l['index'] else 0)
            l['simple'] = len(l['suite']) - attendu < 4 + (fin % 4 != 0) * 4 and (not l['index'] or l['brut'][20:24] == struct.pack('<I', fin))
        self.ordre = sorted(range(self.nlistes), key=lambda i: self.listes[i]['deb'])
        self.noms = b[0x50 + self.off_noms:]
        # (LU) octets avant la 1re liste (certaines tables commencent à 8) ; alignement d'une liste = plus grande colonne
        self.avant = b[self.D:self.D + min([l['deb'] for l in self.listes] or [0])]
        for i, l in enumerate(self.listes):
            l['align'] = max([min(ta, 4) for c, ty, ta, pl in self.colonnes(i)] or [4])
        self._modifiable = all(l['simple'] for l in self.listes) and self.ecrire() == b

    def modifiable(self):
        """vrai si on sait réécrire la table en changeant le nombre de lignes : la règle de réécriture (alignements,
        index trié refait) redonne EXACTEMENT le fichier du jeu"""
        return self._modifiable

    def colonnes(self, liste):
        """[(crc nom, type, taille, place)] des colonnes du type de la liste"""
        t = self.listes[liste]['type']
        o = 0x50 + 0x20 * t
        c0, nc = struct.unpack_from('<HH', self.b, o + 8)
        out = []
        for k in range(c0, c0 + nc):
            oc = 0x50 + 4 * self.fin_types + 0x20 * k
            crc, ty, _, taille, place = struct.unpack_from('<IHHII', self.b, oc)
            out.append((crc, ty, taille, place))
        return out

    def ecrire(self):
        """réécrit ; les listes « simples » sont recalculées (bourrage à 4, index trié par la 1re colonne refait),
        les autres gardent ce qui suit leurs lignes tel quel"""
        tete = bytearray(self.b[:self.D])
        donnees = bytearray(self.avant)
        for i in self.ordre:
            l = self.listes[i]
            o = 0x50 + 4 * self.fin_cols + 0x20 * i
            while len(donnees) % l['align']:  # (LU) alignée sur sa plus grande colonne ; rien après la dernière
                donnees += b'\0'
            struct.pack_into('<I', tete, o + 4, len(donnees))
            struct.pack_into('<I', tete, o + 12, len(l['lignes']))
            for r in l['lignes']:
                assert len(r) == l['lg']
                donnees += r
            if l['simple']:
                if l['index']:
                    struct.pack_into('<I', tete, o + 20, len(donnees))
                    cle = lambda k: (struct.unpack_from('<I', l['lignes'][k], 0)[0] if l['lg'] >= 4 else l['lignes'][k][0], k)
                    for k in sorted(range(len(l['lignes'])), key=cle):
                        donnees += struct.pack('<H', k)
            else:
                donnees += l['suite']
        corps = tete + donnees
        struct.pack_into('<I', corps, 0x38, len(corps) - 0x50)
        sortie = corps + self.noms
        struct.pack_into('<I', sortie, 0x0C, len(sortie) - 0x50)
        return bytes(sortie)


if __name__ == '__main__':
    ok = ko = 0
    for f in sys.argv[1:]:
        b = open(f, 'rb').read()
        if b[:4] != b'RDBN':
            continue
        try:
            r = Table(b).ecrire()
        except Exception as e:
            print('ERREUR', f, e); ko += 1; continue
        if r == b:
            ok += 1
        else:
            ko += 1
            i = next((k for k in range(min(len(r), len(b))) if r[k] != b[k]), min(len(r), len(b)))
            print('DIFFÉRENT', f, len(b), len(r), 'premier écart', hex(i))
    print('identiques', ok, 'différents', ko)
