# Lecture d'un .cfg.bin (format T2B de Level-5) : liste des entrées (crc32 du nom, paramètres : texte / entier / flottant).
# Usage : python lire_cfg.py fichier.cfg.bin [filtre]
import sys, struct, zlib

NOMS = {zlib.crc32(n.encode()): n for n in (
    'LOAD_ACTOR_RESOURCE', 'ATTACH_AURA', 'DETACH_AURA', 'EVENT_COMMAND_ARGS', 'EVENT_COMMAND_HEADER', 'EVENT_COMMAND_NUM')}


def lire(b):
    n, off_str, taille_str, n_str = struct.unpack_from('<4I', b, 0)
    p = 16
    chaines = b[off_str:off_str + taille_str]

    def txt(o):
        if o == 0xFFFFFFFF:
            return None
        e = chaines.index(b'\0', o)
        return chaines[o:e].decode('utf-8', 'replace')
    sortie = []
    for _ in range(n):
        crc, nb = struct.unpack_from('<IB', b, p); p += 5
        nt = (nb + 3) // 4
        types = []
        for k in range(nt):
            octet = b[p + k]
            for j in range(4):
                types.append((octet >> (2 * j)) & 3)
        p += nt
        p = (p + 3) & ~3
        vals = []
        for k in range(nb):
            t = types[k]
            raw = struct.unpack_from('<I', b, p); p += 4
            if t == 0:
                vals.append(txt(raw[0]))
            elif t == 1:
                vals.append(struct.unpack('<i', struct.pack('<I', raw[0]))[0])
            elif t == 2:
                vals.append(round(struct.unpack('<f', struct.pack('<I', raw[0]))[0], 4))
            else:
                vals.append(raw[0])
        sortie.append((crc, vals))
    return sortie


if __name__ == '__main__':
    b = open(sys.argv[1], 'rb').read()
    filtre = sys.argv[2] if len(sys.argv) > 2 else None
    for crc, vals in lire(b):
        ligne = '%s %s' % (NOMS.get(crc, 'CMD_%08X' % crc), vals)
        if not filtre or filtre in ligne:
            print(ligne)
