"""BMP 32 bits du lecteur (--planche) -> PNG (vérifications). Usage : python bmp_png.py entree.bmp sortie.png [x0 y0 x1 y1]"""
import sys, os, struct
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'AtelierD3D'))
import rendu_image  # noqa (chemins)
from lib import images

b = open(sys.argv[1], 'rb').read()
off = struct.unpack_from('<I', b, 10)[0]
w, h = struct.unpack_from('<ii', b, 18)
h = abs(h)
x0, y0, x1, y1 = (int(v) for v in sys.argv[3:7]) if len(sys.argv) >= 7 else (0, 0, w, h)
rows = []
for y in range(y0, y1):
    r = bytearray(b[off + (y * w + x0) * 4: off + (y * w + x1) * 4])
    r[0::4], r[2::4] = r[2::4], r[0::4]
    rows.append(bytes(r))
images.ecrire_png(sys.argv[2], x1 - x0, y1 - y0, rows)
