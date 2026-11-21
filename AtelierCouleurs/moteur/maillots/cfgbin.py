"""Lecteur minimal pour les fichiers Level-5 .cfg.bin (format T2B)."""
import struct, sys, json

def parse(path):
    d = open(path, 'rb').read()
    n_entries, st_off, st_len, st_cnt = struct.unpack_from('<4I', d, 0)
    strings = d[st_off:st_off + st_len]

    def get_str(off):
        if off < 0 or off >= len(strings):
            return None
        end = strings.index(b'\0', off)
        return strings[off:end].decode('utf-8', 'replace')

    # table des clés (noms) après la table de chaînes, alignée sur 16
    key_off = (st_off + st_len + 15) & ~15
    names = {}
    try:
        k_size, k_cnt, k_str_off, k_str_len = struct.unpack_from('<4I', d, key_off)
        kstr = d[key_off + k_str_off: key_off + k_str_off + k_str_len]
        for i in range(k_cnt):
            crc, so = struct.unpack_from('<2I', d, key_off + 16 + i * 8)
            names[crc] = kstr[so:kstr.index(b'\0', so)].decode('utf-8', 'replace')
    except Exception:
        pass

    entries = []
    p = 16
    for _ in range(n_entries):
        crc = struct.unpack_from('<I', d, p)[0]; p += 4
        cnt = d[p]; p += 1
        tbytes = d[p:p + (cnt + 3) // 4]; p += (cnt + 3) // 4
        p = (p + 3) & ~3
        types = [(tbytes[i // 4] >> ((i % 4) * 2)) & 3 for i in range(cnt)]
        vals = []
        for t in types:
            raw = d[p:p + 4]; p += 4
            if t == 0:
                vals.append(get_str(struct.unpack('<i', raw)[0]))
            elif t == 1:
                vals.append(struct.unpack('<i', raw)[0])
            elif t == 2:
                vals.append(round(struct.unpack('<f', raw)[0], 4))
            else:
                vals.append(raw.hex())
        entries.append((names.get(crc, f'{crc:08x}'), vals))
    return entries

if __name__ == '__main__':
    path = sys.argv[1]
    mode = sys.argv[2] if len(sys.argv) > 2 else 'raw'
    out = sys.stdout
    sys.stdout.reconfigure(encoding='utf-8')
    for name, vals in parse(path):
        print(name, json.dumps(vals, ensure_ascii=False))
