"""Aperçu 3D et Studio : petit serveur local (127.0.0.1 seulement) + pages ouvertes dans le navigateur.

- /          : aperçu 3D seul ; il suit les images (fichiers enregistrés dans Paint ou ailleurs, ou le studio)
- /studio    : le studio (patron à gauche, 3D en direct à droite, outils, formes, motifs, numéro)
La page demande /etat toutes les 0,4 s ; dès qu'une image change, elle recharge la texture.
"""
import os, json, threading, time
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
from . import modele3d, numeros, relief, atelier_mod as A

ICI_LIB = os.path.dirname(os.path.abspath(__file__))
PAGES = {'/': 'apercu3d.html', '/index.html': 'apercu3d.html', '/studio': 'studio.html', '/vue3d.js': 'vue3d.js'}
TYPES = {'.html': 'text/html; charset=utf-8', '.js': 'text/javascript; charset=utf-8'}
CLES = ('haut_dom', 'short_dom', 'haut_ext', 'short_ext')


def sources_maillot(m, d):
    """image utilisée pour chaque partie, comme à la construction du mod (voir atelier_mod.construire_mod)"""
    def perso(k):
        p = m.get(k)
        return p if p and os.path.exists(p) else None
    def base(k):
        p = os.path.join(d, A.FICHIER_BASE[k])
        return p if os.path.exists(p) else None
    s = {'haut_dom': perso('haut_dom') or base('haut_dom'),
         'short_dom': perso('short_dom') or base('short_dom')}
    if perso('haut_ext') or perso('short_ext'):
        s['haut_ext'] = perso('haut_ext') or perso('haut_dom') or base('haut_ext')
        s['short_ext'] = perso('short_ext') or perso('short_dom') or base('short_ext')
    elif perso('haut_dom') or perso('short_dom'):
        s['haut_ext'], s['short_ext'] = s['haut_dom'], s['short_dom']      # le mod reprend le domicile
    else:
        s['haut_ext'], s['short_ext'] = base('haut_ext'), base('short_ext')
    s['icone'] = perso('icone') or base('icone')
    s['embleme'] = perso('embleme')
    return s


def zones(parties):
    """zones du patron, reconnues sur le modèle 3D : {'haut': {zone: [u1, v1, u2, v2, u3, v3, ...]}, 'short': {...}}
    (le joueur fait face : sa gauche est du côté x > 0)"""
    out = {'haut': {}, 'short': {}}

    def par_iles(partie, pos, uv, idx, classer, coupe=()):
        """chaque pièce du patron (triangles reliés par leurs sommets) reçoit le nom de la majorité de sa surface"""
        n = len(pos) // 3
        parent = list(range(n))
        def racine(a):
            while parent[a] != a:
                parent[a] = parent[parent[a]]
                a = parent[a]
            return a
        for t in range(0, len(idx), 3):
            a, b, c = idx[t:t + 3]
            ra, rb, rc = racine(a), racine(b), racine(c)
            parent[rb] = ra
            parent[racine(rc)] = ra
        votes = {}
        for t in range(0, len(idx), 3):
            tri = idx[t:t + 3]
            (u1, v1), (u2, v2), (u3, v3) = [(uv[2 * k], uv[2 * k + 1]) for k in tri]
            aire = abs((u2 - u1) * (v3 - v1) - (u3 - u1) * (v2 - v1)) + 1e-9
            c = [sum(pos[3 * k + j] for k in tri) / 3 for j in range(3)]
            z = classer(*c)
            d = votes.setdefault(racine(tri[0]), {})
            d[z] = d.get(z, 0) + aire
        nom = {r: max(d, key=d.get) for r, d in votes.items()}
        # le devant et le dos sont souvent une seule pièce (reliée par les côtés) : on la coupe au milieu du patron,
        # et la 3D dit quelle moitié est le devant
        moities = {}
        for t in range(0, len(idx), 3):
            tri = idx[t:t + 3]
            if nom[racine(tri[0])] in coupe:
                u = sum(uv[2 * k] for k in tri) / 3
                c = [sum(pos[3 * k + j] for k in tri) / 3 for j in range(3)]
                d = moities.setdefault(u < 0.5, {})
                z = classer(*c)
                if z in coupe:
                    d[z] = d.get(z, 0) + 1
        nom_moitie = {m: max(d, key=d.get) for m, d in moities.items() if d}
        for t in range(0, len(idx), 3):
            tri = idx[t:t + 3]
            z = nom[racine(tri[0])]
            if z in coupe:
                z = nom_moitie.get(sum(uv[2 * k] for k in tri) / 3 < 0.5, z)
            l = out[partie].setdefault(z, [])
            for k in tri:
                l.extend((round(uv[2 * k], 4), round(uv[2 * k + 1], 4)))

    if 'haut' in parties:
        pos, uv, idx = parties['haut']
        X = max(abs(v) for v in pos[0::3]) or 1
        def classer_haut(x, y, z):
            if abs(x) > 0.55 * X:
                return 'manche_g' if x > 0 else 'manche_d'
            return 'devant' if z > 0 else 'dos'
        par_iles('haut', pos, uv, idx, classer_haut, ('devant', 'dos'))
    for c in ('col10', 'col11'):
        if c in parties:
            pos, uv, idx = parties[c]
            par_iles('haut', pos, uv, idx, lambda x, y, z: 'col')
    # encolure : le haut du maillot au ras du cou (souvent un liseré du maillot d'origine)
    if 'haut' in parties:
        pos, uv, idx = parties['haut']
        cols = [parties[c][0] for c in ('col10', 'col11') if c in parties]
        pts = [(p[i], p[i + 1], p[i + 2]) for p in cols for i in range(0, len(p), 3)]
        if pts:
            bas_col = min(q[1] for q in pts)
            pts = [q for q in pts if q[1] < bas_col + 0.02]          # le bas du col (là où il touche le maillot)
        ymax = max(pos[1::3])
        l = []
        for t in range(0, len(idx), 3):
            tri = idx[t:t + 3]
            c = [sum(pos[3 * k + j] for k in tri) / 3 for j in range(3)]
            if pts:
                proche = min((c[0] - q[0]) ** 2 + (c[1] - q[1]) ** 2 + (c[2] - q[2]) ** 2 for q in pts) < 0.035 ** 2
            else:
                proche = c[1] > ymax - 0.05 and abs(c[0]) < 0.12
            if proche:
                for k in tri:
                    l.extend((round(uv[2 * k], 4), round(uv[2 * k + 1], 4)))
        if l:
            out['haut']['encolure'] = l
    if 'short' in parties:
        pos, uv, idx = parties['short']
        ys = pos[1::3]
        bas, H = min(ys), (max(ys) - min(ys)) or 1
        def classer_short(x, y, z):
            y = (y - bas) / H
            if y > 0.53:
                return 'short_devant' if z > 0 else 'short_dos'
            if y < 0.40:
                return 'chaussette_g' if x > 0 else 'chaussette_d'
            return 'genoux'
        par_iles('short', pos, uv, idx, classer_short, ('short_devant', 'short_dos'))
    return out


class Apercu3D:
    def __init__(self, donnees, journal=print, cache_dir=None):
        self.donnees, self.journal = donnees, journal
        self.cache_dir = cache_dir or os.path.join(os.path.dirname(ICI_LIB), 'cache_textures', 'numeros')
        self.verrou = threading.Lock()
        self.sources = {}              # clé -> chemin d'un PNG
        self.direct = {}               # clé -> (numéro, octets PNG) : image en cours dans un éditeur
        self.n_direct = 0
        self.titre = ''
        self.corps = 1
        self.tex10 = None
        self.dossier = None            # dossier de travail du maillot (images enregistrées par le studio)
        self.numero, self.v_numero = dict(numeros.DEFAUT), 0
        self.quand_enregistre = None   # fonction (clé, chemin) appelée quand le studio enregistre une image
        self.quand_numero = None       # fonction (réglages) appelée quand le studio change le numéro
        self.plis, self.v_plis = 'simples', 0
        self.quand_plis = None         # fonction (mode) appelée quand le studio change le relief du tissu
        self.catalogue, self.base = [], None
        self._verrou_oc = threading.Lock()
        self.modele, self.v_modele, self._cle_modele = None, 0, None
        self._zones, self._cle_zones = None, None
        self.erreur_modele = ''
        self._verrou_planche = threading.Lock()
        moi = self

        class Gestion(BaseHTTPRequestHandler):
            def log_message(self, *a):
                pass

            def _envoyer(self, code, corps, type_='application/json'):
                self.send_response(code)
                self.send_header('Content-Type', type_)
                self.send_header('Cache-Control', 'no-store')
                self.send_header('Content-Length', str(len(corps)))
                self.end_headers()
                self.wfile.write(corps)

            def _json(self, o, code=200):
                self._envoyer(code, json.dumps(o).encode())

            def do_GET(self):
                try:
                    u = urlparse(self.path)
                    q = parse_qs(u.query)
                    if u.path in PAGES:
                        f = os.path.join(ICI_LIB, PAGES[u.path])
                        self._envoyer(200, open(f, 'rb').read(), TYPES[os.path.splitext(f)[1]])
                    elif u.path == '/etat':
                        self._json(moi.etat())
                    elif u.path == '/modele':
                        with moi.verrou:
                            mo = moi.modele
                        self._envoyer(200 if mo else 404, mo or b'{}')
                    elif u.path.startswith('/tex/'):
                        o = moi.image(u.path[5:])
                        self._envoyer(200, o, 'image/png') if o is not None else self._envoyer(404, b'')
                    elif u.path.startswith('/image/'):
                        o = moi.image(u.path[7:], direct=False)
                        self._envoyer(200, o, 'image/png') if o is not None else self._envoyer(404, b'')
                    elif u.path == '/corps':
                        moi.choisir_corps(max(1, min(8, int(q.get('n', ['1'])[0]))))
                        self._json({})
                    elif u.path == '/zones':
                        self._json(moi.zones())
                    elif u.path == '/numero':
                        self._json({'reglages': moi.numero, 'polices': [[i, n] for i, n, f in numeros.POLICES]})
                    elif u.path == '/numero/modele':
                        fam = 'n0002' if q.get('f', [''])[0] == 'n0002' else 'n0001'
                        pos, uv, idx = numeros.modele_numero(moi.donnees, moi.corps, fam)
                        self._json({'p': [round(v, 4) for v in pos], 't': [round(v, 5) for v in uv], 'i': idx})
                    elif u.path == '/plis':
                        self._json({'mode': moi.plis})
                    elif u.path == '/masque/encolure':
                        o = moi.masque_encolure()
                        self._envoyer(200, o, 'image/png') if o is not None else self._envoyer(404, b'')
                    elif u.path.startswith('/extra/'):
                        o = moi.extra(u.path[7:], q.get('c', ['dom'])[0])
                        self._envoyer(200, o, 'image/png') if o is not None else self._envoyer(404, b'')
                    elif u.path.startswith('/oc/'):
                        o = moi.ombrage(u.path[4:])
                        self._envoyer(200, o, 'image/png') if o is not None else self._envoyer(404, b'')
                    elif u.path == '/numero/planche':
                        p = max(0, min(6, int(q.get('p', ['1'])[0])))
                        with moi._verrou_planche:
                            f = numeros.planche_png(moi.donnees, p, moi.cache_dir)
                        self._envoyer(200, open(f, 'rb').read(), 'image/png')
                    else:
                        self._envoyer(404, b'')
                except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError):
                    pass
                except Exception as e:
                    moi.journal('studio : %s' % e)
                    try:
                        self._json({'erreur': str(e)}, 500)
                    except Exception:
                        pass

            def do_POST(self):
                try:
                    u = urlparse(self.path)
                    q = parse_qs(u.query)
                    n = int(self.headers.get('Content-Length') or 0)
                    corps = self.rfile.read(n) if n else b''
                    k = q.get('k', [''])[0]
                    if u.path == '/enregistrer':
                        self._json(moi.enregistrer(k, corps))
                    elif u.path == '/direct':
                        moi.en_direct(k, corps or None)
                        self._json({})
                    elif u.path == '/plis':
                        m = json.loads(corps.decode('utf-8')).get('mode')
                        if m in relief.MODES:
                            moi.plis = m; moi.v_plis += 1
                            if moi.quand_plis:
                                moi.quand_plis(m)
                        self._json({'mode': moi.plis})
                    elif u.path == '/lettres':
                        if k not in numeros.LETTRES or corps[:8] != b'\x89PNG\r\n\x1a\n' or not moi.dossier:
                            raise ValueError('image de lettres refusée')
                        f = os.path.join(moi.dossier, 'lettres_%s.png' % k)
                        open(f + '.tmp', 'wb').write(corps); os.replace(f + '.tmp', f)
                        self._json({'chemin': f})
                    elif u.path == '/numero':
                        moi.regler_numero(json.loads(corps.decode('utf-8')))
                        self._json({'reglages': moi.numero})
                    else:
                        self._envoyer(404, b'')
                except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError):
                    pass
                except Exception as e:
                    moi.journal('studio : %s' % e)
                    try:
                        self._json({'erreur': str(e)}, 500)
                    except Exception:
                        pass

        self.serveur = ThreadingHTTPServer(('127.0.0.1', 0), Gestion)
        self.serveur.daemon_threads = True
        threading.Thread(target=self.serveur.serve_forever, daemon=True).start()

    @property
    def url(self):
        return 'http://127.0.0.1:%d/' % self.serveur.server_address[1]

    def fermer(self):
        try:
            self.serveur.shutdown()
        except Exception:
            pass

    # ------------------------------------------------------------------------------------------ état
    def _version(self, k):
        with self.verrou:
            if k in self.direct:
                return 'd%d' % self.direct[k][0]
            p = self.sources.get(k)
        if not p:
            return ''
        try:
            st = os.stat(p)
        except OSError:
            return ''
        return 'f%d_%d_%d' % (hash(p) & 0xffffff, st.st_mtime_ns, st.st_size)

    def etat(self):
        return {'modele': self.v_modele, 'titre': self.titre, 'corps': self.corps, 'erreur': self.erreur_modele,
                'tex': {k: self._version(k) for k in CLES + ('icone',)}, 'numero': self.numero, 'v_numero': self.v_numero,
                'plis': self.plis, 'v_plis': self.v_plis, 'base': self.base['cle'] if self.base else ''}

    def image(self, k, direct=True):
        with self.verrou:
            if direct and k in self.direct:
                return self.direct[k][1]
            p = self.sources.get(k)
        if not p:
            if k == 'embleme':               # pas encore d'emblème : une image transparente de 512 x 512
                from . import retouche
                return retouche.png_memoire(512, 512, [bytearray(512 * 4) for _ in range(512)])
            return None
        for _ in range(5):                 # le fichier peut être en cours d'écriture (Paint…)
            try:
                o = open(p, 'rb').read()
                if o[:8] == b'\x89PNG\r\n\x1a\n' and o[-8:-4] == b'IEND':
                    return o
            except OSError:
                pass
            time.sleep(0.15)
        return None

    # ------------------------------------------------------------------------------------------ réglages
    def definir(self, titre, tex10, sources, dossier=None, numero=None, base=None, plis=None):
        with self.verrou:
            if base is not None:
                self.base = base
            if plis and plis != self.plis:
                self.plis = plis
                self.v_plis += 1
            self.titre = titre
            self.sources = dict(sources)
            if dossier:
                self.dossier = dossier
            if numero is not None and numero != self.numero:
                self.numero = dict(numero)
                self.v_numero += 1
        if tex10 != self.tex10:
            self.tex10 = tex10
            self._charger_modele()

    def choisir_corps(self, n):
        if n != self.corps:
            self.corps = n
            self._charger_modele()

    def en_direct(self, k, png):
        """image d'un éditeur (octets PNG) ; None = revenir au fichier"""
        with self.verrou:
            if png is None:
                self.direct.pop(k, None)
            else:
                self.n_direct += 1
                self.direct[k] = (self.n_direct, png)

    def enregistrer(self, k, png):
        if k not in CLES + ('icone', 'embleme', 'buste_dom', 'buste_ext'):
            raise ValueError('image inconnue : %s' % k)
        if png[:8] != b'\x89PNG\r\n\x1a\n':
            raise ValueError("ce n'est pas une image PNG")
        if not self.dossier:
            raise ValueError('aucun maillot choisi dans l\'atelier')
        chemin = os.path.join(self.dossier, '%s_modifie.png' % k)
        tmp = chemin + '.tmp'
        open(tmp, 'wb').write(png)
        os.replace(tmp, chemin)
        with self.verrou:
            self.direct.pop(k, None)
            self.sources[k] = chemin
        if self.quand_enregistre:
            self.quand_enregistre(k, chemin)
        return {'chemin': chemin}

    def regler_numero(self, r):
        p = dict(numeros.DEFAUT)
        p.update(self.numero)
        for cle, typ in (('perso', bool), ('remplissage', str), ('contour', str), ('police', int), ('taille', float), ('hauteur', float),
                         ('nom', bool), ('lettres', str)):
            if cle in r:
                p[cle] = typ(r[cle])
        p['police'] = max(1, min(6, p['police']))
        p['taille'] = max(0.6, min(1.5, p['taille']))
        p['hauteur'] = max(-10.0, min(10.0, p['hauteur']))
        with self.verrou:
            self.numero = p
            self.v_numero += 1
        if self.quand_numero:
            self.quand_numero(dict(p))

    def ombrage(self, partie):
        """ombrage (relief du tissu) tel que le mod le mettra, en PNG, pour l'aperçu 3D"""
        if not self.base or partie not in ('haut', 'short'):
            return None
        suf = '20' if partie == 'haut' else '30'
        cache = os.path.join(os.path.dirname(self.cache_dir), 'relief')
        with self._verrou_oc:
            if self.plis == 'base':
                f = os.path.join(cache, 'oc_base_%s_%s.png' % (self.base['cle'], suf))
                if not os.path.exists(f):
                    from . import images
                    g = images.G4TX(open(self.base['tex10'], 'rb').read())
                    n, im = relief._oc(g, suf)
                    if not im:
                        return None
                    os.makedirs(cache, exist_ok=True)
                    images.ecrire_png(f, *im)
            else:
                im = relief.oc_pour(self.catalogue, self.base, suf, self.plis, cache, self.journal)
                if not im:
                    return None
                f = os.path.join(cache, 'oc_%s_%s_%s_%s.png' % (os.path.basename(os.path.dirname(self.base['tex10'])),
                                                                 self.base['cle'], suf, self.plis))
        return open(f, 'rb').read()

    def extra(self, k, cote):
        """image du jeu d'une pièce en plus (k = 'x21', 'x22'…), pour l'aperçu 3D (réduite à 1024)"""
        if not self.base or not k.startswith('x') or not k[1:].isdigit():
            return None
        tex = self.base['tex20'] if cote == 'ext' and self.base.get('tex20') else self.base['tex10']
        cache = os.path.join(os.path.dirname(self.cache_dir), 'pieces')
        f = os.path.join(cache, '%s_%s.png' % (os.path.basename(tex)[:-5], k[1:]))
        with self._verrou_oc:
            if not os.path.exists(f):
                from . import images, retouche
                g = images.G4TX(open(tex, 'rb').read())
                n = next((x for x in g.noms if x.endswith('_' + k[1:])), None)
                if not n:
                    return None
                w, h, rows = g.image(n)
                while w > 1024:
                    w, h, rows = images.moitie(w, h, rows)
                os.makedirs(cache, exist_ok=True)
                images.ecrire_png(f, w, h, rows)
        return open(f, 'rb').read()

    def masque_encolure(self, n=1024, rayon=0.03):
        """bande autour du cou (pixels du patron à moins de `rayon` mètres du bas du col), en PNG n x n (alpha)"""
        if not self.tex10:
            return None
        cache = os.path.join(os.path.dirname(self.cache_dir), 'encolure')
        f = os.path.join(cache, '%s_%d_%d.png' % (os.path.basename(self.tex10)[:-5], n, int(rayon * 1000)))
        if os.path.exists(f):
            return open(f, 'rb').read()
        from . import images
        p = modele3d.chemin_modele(self.donnees, self.tex10, 1)
        pp = modele3d.parties(p) if p else {}
        if 'haut' not in pp:
            return None
        pos, uv, idx = pp['haut']
        cols = [pp[c][0] for c in ('col10', 'col11') if c in pp]
        pts = [(q[i], q[i + 1], q[i + 2]) for q in cols for i in range(0, len(q), 3)]
        if pts:
            bas = min(q[1] for q in pts)
            pts = [q for q in pts if q[1] < bas + 0.02]
        else:                         # pas de col séparé : le haut du maillot près du cou
            ymax = max(pos[1::3])
            pts = [(pos[i], pos[i + 1], pos[i + 2]) for i in range(0, len(pos), 3) if pos[i + 1] > ymax - 0.01 and abs(pos[i]) < 0.1]
        if not pts:
            return None
        pts = pts[::max(1, len(pts) // 60)]
        r2 = rayon * rayon
        a = bytearray(n * n)
        for t in range(0, len(idx), 3):
            tri = idx[t:t + 3]
            P = [(pos[3 * k], pos[3 * k + 1], pos[3 * k + 2]) for k in tri]
            c = [sum(q[j] for q in P) / 3 for j in range(3)]
            if min((c[0] - q[0]) ** 2 + (c[1] - q[1]) ** 2 + (c[2] - q[2]) ** 2 for q in pts) > (rayon + 0.08) ** 2:
                continue
            (u1, v1), (u2, v2), (u3, v3) = [(uv[2 * k] * n, uv[2 * k + 1] * n) for k in tri]
            d = (v2 - v3) * (u1 - u3) + (u3 - u2) * (v1 - v3)
            if not d:
                continue
            for y in range(max(0, int(min(v1, v2, v3))), min(n, int(max(v1, v2, v3)) + 1)):
                for x in range(max(0, int(min(u1, u2, u3))), min(n, int(max(u1, u2, u3)) + 1)):
                    l1 = ((v2 - v3) * (x + .5 - u3) + (u3 - u2) * (y + .5 - v3)) / d
                    l2 = ((v3 - v1) * (x + .5 - u3) + (u1 - u3) * (y + .5 - v3)) / d
                    l3 = 1 - l1 - l2
                    if l1 < -0.02 or l2 < -0.02 or l3 < -0.02:
                        continue
                    X = l1 * P[0][0] + l2 * P[1][0] + l3 * P[2][0]
                    Y = l1 * P[0][1] + l2 * P[1][1] + l3 * P[2][1]
                    Z = l1 * P[0][2] + l2 * P[1][2] + l3 * P[2][2]
                    for q in pts:
                        if (X - q[0]) ** 2 + (Y - q[1]) ** 2 + (Z - q[2]) ** 2 < r2:
                            a[y * n + x] = 255
                            break
        if not any(a):
            return None
        rows = [bytearray(n * 4) for _ in range(n)]
        for y in range(n):
            r = rows[y]
            for x in range(n):
                if a[y * n + x]:
                    r[x * 4:x * 4 + 4] = b'\xff\xff\xff\xff'
        os.makedirs(cache, exist_ok=True)
        images.ecrire_png(f, n, n, rows)
        return open(f, 'rb').read()

    def zones(self):
        if not self.tex10:
            return {'haut': {}, 'short': {}}
        if self._cle_zones != self.tex10:
            p = modele3d.chemin_modele(self.donnees, self.tex10, 1)
            self._zones = zones(modele3d.parties(p)) if p else {'haut': {}, 'short': {}}
            self._cle_zones = self.tex10
        return self._zones

    def _charger_modele(self):
        cle = (self.tex10, self.corps)
        if not self.tex10 or cle == self._cle_modele:
            return
        self._cle_modele = cle
        def run():
            try:
                p = modele3d.chemin_modele(self.donnees, self.tex10, self.corps)
                if not p:
                    raise FileNotFoundError('modèle 3D introuvable pour ' + os.path.basename(self.tex10))
                parties = {}
                ys = []
                for k, (pos, uv, idx) in modele3d.parties(p).items():
                    parties[k] = {'p': [round(v, 4) for v in pos], 't': [round(v, 5) for v in uv], 'i': idx}
                    ys.extend(pos[1::3])
                corps = json.dumps({'parties': parties, 'fichier': os.path.basename(p),
                                    'bas': min(ys), 'haut': max(ys)}).encode()
                with self.verrou:
                    if self._cle_modele == cle:
                        self.modele = corps
                        self.v_modele += 1
                        self.erreur_modele = ''
            except Exception as e:
                self.erreur_modele = str(e)
                self.journal('aperçu 3D : %s' % e)
        threading.Thread(target=run, daemon=True).start()
