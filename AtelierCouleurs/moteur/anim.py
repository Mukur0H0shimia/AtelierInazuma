"""Animation des cinématiques : squelettes (G4SK), mouvements (G4MT, et G4VS / G4MA / G4TP / G4CM qui ont le même conteneur).

Format des mouvements d'après G4_Blender (https://github.com/The-RealBobi/G4_Blender, GPL-3.0, lu comme documentation) et
vérifié sur Frappe stellaire (ev60_01430) :
- en-tête de section (0x40) : u16 nb de clips +0x20, nb de cibles +0x22, puis des « unités » u16 +0x24..+0x32
  (infos de cibles, canaux, échelles, crc des clips, crc des cibles, noms des clips, images clés, données) et un décalage u8 +0x36 ;
  octet = (mots d'en-tête + unités [<< décalage pour infos/canaux, << 2 x décalage pour clés/données]) x 4 ;
- clip (16 octets dès +0x40) : début, fin (images), début des infos de cibles, nb, drapeaux, fps, début (octet fort) ;
- info de cible (8) : n° de cible, début des canaux, nb de canaux, début (octet fort) ;
- canal (20) : type, codec, interpolation, variante, nb de composantes, octets par clé, n° d'échelle, -, puis début des clés
  (dans la table u16 des images), décalage des données (octets), nb de clés ;
- valeurs : codec 1 = brut (variante 1 int8, 2 int16, 4 float32) ; codec 2 = non signé (u8/255, u16/65535) x échelle ;
  codec 3 = signé (i8/127, i16/32767) x échelle (diviseurs lus dans nie.exe 0x140508be0…0x1405091a0, vérifiés à l'émulateur) ;
- types : 1-3 échelle x y z, 9 rotation (quaternion x y z w), 10-12 position x y z ; caméra : 22-24 position, 26-28 cible,
  30 roulis, 31 champ de vision ; les cibles sont reconnues par le crc32 de leur nom.
"""
import struct, re, zlib, os, json


def sections(b):
    """{magie: (début, fin)} des sections G4xx d'un fichier (paquet G4PK ou section seule)"""
    out = []
    for m in re.finditer(rb'G4(SK|MD|MT|MA|TP|VS|CM)', b):
        if m.start() % 16 == 0 and struct.unpack_from('<H', b, m.start() + 4)[0] == 0x40:
            out.append((m.group().decode(), m.start()))
    res = {}
    for nom, a in out:
        taille = struct.unpack_from('<I', b, a + 0x0C)[0]
        res.setdefault(nom, (a, a + 0x40 + taille))
    return res


# ------------------------------------------------------------------ squelette
def lire_g4sk(b, a=None):
    if a is None:
        a = b.find(b'G4SK')
    n = struct.unpack_from('<H', b, a + 0x20)[0]
    offs = [a + 0x40 + 4 * o for o in struct.unpack_from('<11H', b, a + 0x24)]
    parents = struct.unpack_from('<%dH' % n, b, offs[3])
    rel = struct.unpack_from('<%dH' % n, b, offs[7])
    crcs = struct.unpack_from('<%dI' % n, b, offs[2])
    # (14/11/2026, LU dans nie.exe 0x14052bfd0) table 5 : un octet par os ; (octet >> 1) & 0xF = mode « panneau » de l'os
    # (1 tourné vers la caméra, 2 autour de son axe Y, 3 aligné sur l'écran), appliqué si l'octet d'en-tête +0x22 a le bit 2
    draps = b[offs[5]:offs[5] + n]
    # (14/11/2026) table 0 (en-tête +0x24) : INVERSE DU MONDE DE LIAISON de chaque os, 3 lignes de 4 flottants (LU : la
    # fonction 0x140529600 de nie.exe retourne ses n x 12 flottants avec les tables +0x26 (locaux) et du début). Pour la peau :
    # monde animé x cette matrice. Elle diffère du repos des locaux quand le maillage a été lié dans une autre pose
    # (Main oméga ev63006900 : 29 os, jusqu'à 11,6 m ; Main céleste : identiques).
    lie = offs[0] + 48 * n <= len(b)
    par_crc = {zlib.crc32(m.group()): m.group().decode() for m in re.finditer(rb'[A-Za-z_][A-Za-z0-9_]{1,60}', b[a:])}
    os_ = []
    for k in range(n):
        i = offs[7] + rel[k]
        j = b.find(b'\0', i)
        nom = b[i:j if j >= 0 else len(b)].decode('ascii', 'replace')      # le dernier nom peut finir avec le fichier
        loc = struct.unpack_from('<12f', b, offs[1] + 48 * k)        # échelle xyz, -, quaternion xyzw, position xyz, -
        if zlib.crc32(nom.encode()) != crcs[k]:
            nom = par_crc.get(crcs[k], 'os_%d' % k)
        os_.append({'nom': nom, 'crc': crcs[k], 'parent': parents[k] if parents[k] < n and parents[k] != k else -1,
                    'e': [round(x, 6) for x in loc[0:3]], 'r': [round(x, 6) for x in loc[4:8]], 't': [round(x, 6) for x in loc[8:11]],
                    'drap': draps[k] if k < len(draps) else 0})
        if lie:
            os_[-1]['ib'] = [round(x, 6) for x in struct.unpack_from('<12f', b, offs[0] + 48 * k)]
    return os_


def entete_g4sk(chemin):
    """octet +0x22 de l'en-tête G4SK (bit 2 : calcul 0x14052bfd0 avec os « panneaux » ; LU dans nie.exe 0x1405110b0)"""
    try:
        b = open(chemin, 'rb').read()
        a = b.find(b'G4SK')
        return b[a + 0x22] if a >= 0 else 0
    except OSError:
        return 0


def non_uniforme(objbin):
    """propriété SETUP_PARAM « NonUniformScale » d'un objbin (gmdCObject) : 1 -> le jeu ne transmet pas l'échelle locale d'un os
    à ses enfants (0x140529aa0, choisie par 0x14052b100 / 0x14052bfd0 quand l'échelle locale du parent n'est pas (1, 1, 1)).
    LU dans nie.exe le 14/11/2026 (octet +0x1F1 du modèle, propriété de crc 0x57055864)."""
    try:
        from . import particules as _P
        for nom, v in _P.lire_brut(objbin):
            if nom == 'SETUP_PARAM' and v and v[0][1] == 'NonUniformScale':
                return bool(v[1][1]) if len(v) > 1 else False
    except Exception:
        pass
    return False


# ------------------------------------------------------------------ mouvements
def _valeur(codec, variante, nc, data, o, echelle):
    if codec == 1:
        f = {1: 'b', 2: 'h', 4: 'f'}[variante]
        return list(struct.unpack_from('<%d%s' % (nc, f), data, o))
    if codec == 2:
        f, d = {1: ('B', 255.0), 2: ('H', 65535.0)}[variante]
        return [v * echelle / d for v in struct.unpack_from('<%d%s' % (nc, f), data, o)]
    if codec == 3:
        f, d = {1: ('b', 127.0), 2: ('h', 32767.0)}[variante]
        return [v * echelle / d for v in struct.unpack_from('<%d%s' % (nc, f), data, o)]
    raise ValueError('codec %d/%d' % (codec, variante))


def lire_g4mt(b, a=None, magie='G4MT'):
    """-> {'clips': [{nom, debut, fin, fps, cibles: [{crc, canaux: [{type, interp, images, valeurs}]}]}]}"""
    if a is None:
        a = b.find(magie.encode())
    hw = struct.unpack_from('<H', b, a + 0x0A)[0]
    taille = struct.unpack_from('<I', b, a + 0x0C)[0]
    s = b[a:a + 0x40 + taille]
    nclips, ncibles = struct.unpack_from('<HH', s, 0x20)
    u_ti, u_ch, u_ech, u_hclip, u_hcib, u_noms, u_cles, u_data = struct.unpack_from('<8H', s, 0x24)
    sh = s[0x36]
    o_ti = (hw + (u_ti << sh)) * 4
    o_ch = (hw + (u_ch << sh)) * 4
    o_ech, o_hclip, o_hcib, o_noms = [(hw + u) * 4 for u in (u_ech, u_hclip, u_hcib, u_noms)]
    o_cles = (hw + (u_cles << (2 * sh))) * 4
    o_data = (hw + (u_data << (2 * sh))) * 4
    echelles = struct.unpack_from('<%df' % ((o_hclip - o_ech) // 4), s, o_ech)
    cibles = struct.unpack_from('<%dI' % ncibles, s, o_hcib)
    hclips = struct.unpack_from('<%dI' % nclips, s, o_hclip)
    # noms des clips : reconnus par leur crc32 parmi les chaînes de la table des noms
    noms = {zlib.crc32(m.group().encode()): m.group() for m in re.finditer(r'[A-Za-z0-9_]{2,40}', s[o_noms:o_cles].decode('latin-1'))}
    data = s[o_data:]
    clips = []
    for c in range(nclips):
        deb, fin, ti0, nti, drap, fps, ti_haut = struct.unpack_from('<HHHHBBB', s, 0x40 + 16 * c)
        ti0 += ti_haut << 16
        cl = {'nom': noms.get(hclips[c], 'clip%d' % c), 'debut': deb, 'fin': fin, 'fps': fps or 60, 'cibles': []}
        for t in range(ti0, ti0 + nti):
            ic, ch0, nch, ch_haut, _ = struct.unpack_from('<HHBBH', s, o_ti + 8 * t)
            ch0 += ch_haut << 16
            ci = {'crc': cibles[ic], 'canaux': []}
            for k in range(ch0, ch0 + nch):
                o = o_ch + 20 * k
                typ, codec, interp, var, nc, pas, iech, prm = s[o:o + 8]     # prm (octet 7) : n° du paramètre visé (G4MA 32-35)
                k0, d0, nk = struct.unpack_from('<III', s, o + 8)
                images = list(struct.unpack_from('<%dH' % nk, s, o_cles + 2 * k0))
                ech = echelles[iech] if iech < len(echelles) else 1.0
                vals = [_valeur(codec, var, nc, data, d0 + j * pas, ech) for j in range(nk)]
                ci['canaux'].append({'type': typ, 'interp': interp, 'images': images, 'prm': prm,
                                     'valeurs': [[round(v, 5) for v in x] for x in vals]})
            cl['cibles'].append(ci)
        clips.append(cl)
    return {'clips': clips}


def lire_paquet(chemin):
    """toutes les sections d'animation d'un fichier (.g4pk / .g4pkm / .g4cm / .g4sk)"""
    b = open(chemin, 'rb').read()
    out = {}
    for nom, (a, f) in sections(b).items():
        if nom == 'G4SK':
            out['squelette'] = lire_g4sk(b, a)
        elif nom in ('G4MT', 'G4VS', 'G4MA', 'G4TP', 'G4CM'):
            try:
                out[nom] = lire_g4mt(b, a, nom)
            except Exception as ex:
                out[nom] = {'erreur': str(ex)}
    return out


# ------------------------------------------------------------------ une cinématique complète
PLAN, LOAD, PLAY, VISIBLE, ATTACHE = 0xFD044302, 0x799A1EBA, 0xA9BDE997, 0xAFE3804D, 0xA2D1F942
EGA = 0x36E5B708          # effet commun (ega0001…) : relancé à l'image f
SON = 0xBA67E844          # son : [canal, genre, nom, …]
DECOR = 0x3DB3FBEB        # décor : [0] caché, [1] visible
TELOP = 0xFD6E24AB        # bannière : [0] apparaît, [1] disparaît
CHOIX = 0xFE393582        # [acteur modèle, 'TYPE', '01'] : la variante (corpulence) dont parle l'ordre suivant
FONDU = 0x48A58CDC        # [acteur, valeur 0..1, images, …] : fondu du modèle (LU 0x140f39730, voir plus bas)


def _commandes(chemin):
    from . import cfgbin
    if not os.path.exists(chemin):
        return []
    L = cfgbin.lire(open(chemin, 'rb').read())
    out = []
    for k in range(len(L) - 1):
        c, v = L[k]
        if cfgbin.NOMS.get(c) == 'EVENT_COMMAND_HEADER' and len(v) >= 2:
            out.append((v[0], v[1] & 0xFFFFFFFF, L[k + 1][1]))
    return out


def _clips(paquet, magie='G4MT'):
    m = paquet.get(magie) or {}
    return {c['nom']: c for c in m.get('clips', [])}


def dossier_ev(c, ev):
    """nom du dossier d'animation d'une cinématique : <ev>, ou <ev> sans « _1 » / « _2 » (cinématiques en deux parties)"""
    evx = ev.split('_')[0]
    if not os.path.isdir(os.path.join(c, 'event', evx, ev)) and re.search(r'_\d$', ev):
        return ev[:-2]
    return ev


def cinematique(data_dir, ev, objets, assign_anim=None):
    """tout ce qu'il faut pour rejouer la cinématique dans l'aperçu :
    plans, caméra, squelette + mouvements + visibilité de chaque objet d'effet, ballon, et les ordres (jouer / montrer / cacher)"""
    c = os.path.join(data_dir, 'common')
    evx = ev.split('_')[0]
    evd = dossier_ev(c, ev)                  # dossier et fichiers d'animation : <ev> sans « _1 » / « _2 » (gardiens…)
    dos = os.path.join(c, 'event', evx, evd)
    cmds = _commandes(os.path.join(c, 'event_cfg', 'evt', ev + '.cfg.bin')) + _commandes(os.path.join(c, 'event_cfg', 'eff', ev + '_eff.cfg.bin'))
    if not os.path.isdir(dos):
        # (17/11/2026) cinématique d'un mod sans dossier d'animation à son nom (ZanUltimateMod ev60_87400, MesTechniques
        # ev60_89100…) : LU, le jeu prend les animations aux chemins écrits dans ses commandes
        # (« common/event/ev60/ev60_01870/ev60_01870_camera.g4cm », « …_<CHARA>_<CUT>.g4pk ») -> ce dossier-là
        for _f, _cmd, _a in cmds:
            m_ = next((re.match(r'common/event/(ev\d\d)/(ev\d\d_\d+)/', x) for x in _a if isinstance(x, str)
                       and re.match(r'common/event/(ev\d\d)/(ev\d\d_\d+)/', x)), None)
            if m_ and os.path.isdir(os.path.join(c, 'event', m_.group(1), m_.group(2))):
                evx, evd = m_.group(1), m_.group(2)
                dos = os.path.join(c, 'event', evx, evd)
                break
    plans = []
    for f, cmd, a in cmds:
        if cmd == PLAN and len(a) >= 3 and isinstance(a[0], str):
            plans.append({'nom': a[0], 'debut': a[1], 'fin': a[2]})
    plans.sort(key=lambda p: p['debut'])
    res = {'ev': ev, 'fps': 60, 'plans': plans, 'duree': max([p['fin'] for p in plans] or [0]), 'objets': {}, 'camera': None, 'balle': None}
    cam = os.path.join(dos, evd + '_camera.g4cm')
    if os.path.exists(cam):
        res['camera'] = _clips(lire_paquet(cam), 'G4CM')
    # point d'accroche des effets (squelette point_eff animé par plan)
    sk_pe = os.path.join(c, 'event', 'ev_point', 'point_eff', 'point_eff.g4sk')
    if os.path.exists(sk_pe):
        pe = {'os': lire_paquet(sk_pe)['squelette'], 'clips': {}}
        for p in plans:
            f = os.path.join(dos, '%s_point_eff_%s.g4pk' % (evd, p['nom']))
            if os.path.exists(f):
                pe['clips'][p['nom']] = _clips(lire_paquet(f)).get(p['nom'])
        res['point_eff'] = pe
    # objets d'effet : squelette, clips, visibilité, ordres
    # aura du ballon = effet de statut (moteur/aura_balle.py) : intervalles et courbes, sans modèle d'aura
    try:
        from . import aura_balle as _ab
        res['aura_balle'] = _ab.intervalles(data_dir, cmds)
    except Exception:
        pass
    for o in objets:
        act = o['acteur']
        rel = o['chemin'].replace('\\', '/')
        rel = rel[len('common/'):] if rel.startswith('common/') else rel
        pk = os.path.join(c, *os.path.dirname(rel).split('/'), os.path.basename(rel).rsplit('.', 1)[0] + '.g4pkm')
        if not os.path.exists(pk):
            continue
        r = lire_paquet(pk)
        ordres = []
        for f, cmd, a in cmds:
            if not a or a[0] != act:
                continue
            if cmd == PLAY and len(a) >= 2:
                ordres.append({'image': f, 'jouer': a[1]})
            elif cmd == VISIBLE and len(a) >= 2:
                ordres.append({'image': f, 'visible': bool(a[1])})
            elif cmd == ATTACHE and len(a) >= 3:
                ordres.append({'image': f, 'accroche': [a[1], a[2]]})
            elif cmd == EGA and o.get('commun'):
                ordres.append({'image': f, 'jouer': None, 'boucle': True, 'visible': True, 'accroche': ['camera', '']})
        if o.get('aura_balle'):
            # aura du ballon : « in » au début de chaque aura, puis « loop » en boucle, « out » à la fin ; accrochée au centre
            # du ballon (os c_c_1_0). Deux auras qui s'enchaînent à la même image : pas de « out » entre les deux.
            from . import aura_balle
            cl = _clips(r)
            lg = lambda n: (cl[n]['fin'] - cl[n]['debut'] + 1) if n in cl else 0
            ordres = []
            iv = aura_balle.intervalles(data_dir, cmds)
            res['aura_balle'] = iv
            for k, x in enumerate(iv):
                suite = k + 1 < len(iv) and iv[k + 1]['debut'] == x['fin']
                prec = k > 0 and iv[k - 1]['fin'] == x['debut']
                if not prec:
                    ordres.append({'image': x['debut'], 'jouer': 'in', 'visible': True, 'accroche': [x['acteur'], 'c_c_1_0']})
                    ordres.append({'image': x['debut'] + lg('in'), 'jouer': 'loop', 'boucle': True})
                if not suite and x['fin'] < 10 ** 6:
                    ordres.append({'image': x['fin'], 'jouer': 'out'})
                    ordres.append({'image': x['fin'] + lg('out'), 'visible': False})
        elif o.get('commun'):
            # effet commun (ega0001 = traits de vitesse) : chaque commande EGA (0x36E5B708 [nom, 1, 0, 0, 0], au début de
            # chaque plan) relance son clip (« stand », 10 images) depuis le début, puis il tourne EN BOUCLE jusqu'à la
            # commande suivante. Vérifié le 13/11/2026 sur les vidéos officielles de Big Bang et de la Botte de Lancelot,
            # avec le bon calage (la vidéo commence 0,3 s après l'image 0) : traits présents presque en continu.
            # (L'ancienne règle « une seule bouffée de 10 images » venait d'une comparaison décalée de 0,3 s.)
            cl0 = next(iter(_clips(r).values()), None)
            for x in ordres:
                if 'boucle' in x:
                    x['jouer'] = cl0['nom'] if cl0 else None
                    x['boucle'] = True
        # opacité des matériaux (G4MA, canal 19) : seulement ce canal, pour alléger
        opa = {}
        for nom, cl in _clips(r, 'G4MA').items():
            # 19 = opacité (alpha de u_diffuse) ; 32-35 = u_shaderParam[octet 7].xyzw (seuils des nuages, etc.)
            # (14/11/2026) 16 à 19 = couleur[octet 7].rgba : octet 0 = u_diffuse (16-18 = rvb, vérifié : 1re valeur = couleur du
            # matériau), octet 1 = u_ambient (16 = x, le gain des effets : 2,0 = ambient.x du matériau de Tir météore)
            cibles = [{'crc': t['crc'], 'canaux': [ch for ch in t['canaux'] if 16 <= ch['type'] <= 19 or 32 <= ch['type'] <= 35]} for t in cl['cibles']]
            opa[nom] = dict(cl, cibles=[t for t in cibles if t['canaux']])
        # défilement des textures (G4TP) : cible = crc32('<matériau>_tex<n>') ; 1 / 2 = échelle u / v, 10 / 11 = décalage u / v
        res['objets'][act] = {'os': r.get('squelette', []), 'clips': _clips(r), 'vis': _clips(r, 'G4VS'), 'opa': opa, 'uv': _clips(r, 'G4TP'),
                              'ordres': sorted(ordres, key=lambda x: x['image']),
                              'g4sk': entete_g4sk(pk), 'nus': non_uniforme(os.path.join(c, *rel.split('/')))}
    # point d'accroche des personnages et du ballon (squelette point_s00, animé par plan)
    sk_ps = os.path.join(c, 'event', 'ev_point', 'point', 'point.g4sk')
    if os.path.exists(sk_ps):
        ps = {'os': lire_paquet(sk_ps)['squelette'], 'clips': {}}
        for p in plans:
            f = os.path.join(dos, '%s_point_s00_%s.g4pk' % (evd, p['nom']))
            if os.path.exists(f):
                ps['clips'][p['nom']] = _clips(lire_paquet(f)).get(p['nom'])
        res['point_s00'] = ps
    # accroches : « c00<TYPE><NO>_… » TYPE 01 -> evp01 … ; ballon -> evp05
    accroches, type_en_cours = {}, None
    for f, cmd, a in cmds:
        if cmd == CHOIX and len(a) >= 3 and a[1] == 'TYPE':
            type_en_cours = a[2]
        elif cmd == ATTACHE and len(a) >= 3 and isinstance(a[0], str) and a[1] == 'point_s00':
            cle = a[0] + ('#' + type_en_cours if '<TYPE>' in a[0] and type_en_cours else '')
            accroches.setdefault(cle, a[2])
            type_en_cours = None
    # le joueur (le tireur) : corpulence 01, n° 01 -> paquets <ev>_c000101_s00_p00_<plan>.g4pk sur le squelette c000101
    sk_j = os.path.join(c, 'chr', 'c000101', 'c000101.g4sk')
    clips_j = {}
    for p in plans:
        f = os.path.join(dos, '%s_c000101_s00_p00_%s.g4pk' % (evd, p['nom']))
        if os.path.exists(f):
            clips_j[p['nom']] = _clips(lire_paquet(f)).get(p['nom'])
    if clips_j and os.path.exists(sk_j):
        acc = next((v for k, v in accroches.items() if k.startswith('c00<TYPE><NO>') and k.endswith('#01')), 'evp01')
        res['joueurs'] = [{'acteur': 'c000101', 'modele': 'joueur', 'os': lire_paquet(sk_j)['squelette'], 'clips': clips_j, 'accroche': acc}]
    # ballon
    sk_b = os.path.join(c, 'chr', 'b000001', 'b000001.g4pkm')
    clips_b = {}
    for p in plans:
        f = os.path.join(dos, '%s_b000001_s00_p00_%s.g4pk' % (evd, p['nom']))
        if os.path.exists(f):
            clips_b[p['nom']] = _clips(lire_paquet(f)).get(p['nom'])
    if clips_b and os.path.exists(sk_b):
        acc = next((v for k, v in accroches.items() if k.startswith('b000001')), 'evp05')
        res['balle'] = {'os': lire_paquet(sk_b)['squelette'], 'clips': clips_b, 'os_balle': 'c_add_1_0', 'accroche': acc}
    res['points'], res['acteurs'] = points_et_acteurs(c, evd, dos, cmds, plans, assign_anim)
    # bannière : « soccer10_01_<code> » chargée, montrée (0xFD6E24AB [0]) puis cachée (0xFD6E24AB [1])
    # (24/11) plusieurs bannières : la commande nomme la sienne ([0|1, 'soccer10_01_<code>'] ; mise en armure : celle de
    # l'esprit « <CHARA_ID> » 35 -> 100 puis « aura_armed01 » 170 -> 240) ; sans nom (techniques, invocations) : la 1re chargée
    tels, premier = {}, None
    for f, cmd, a in cmds:
        for x in a:
            if isinstance(x, str) and x.startswith('soccer10_01_') and premier is None:
                premier = x[len('soccer10_01_'):]
        if cmd == TELOP and a:
            nom = a[1][len('soccer10_01_'):] if len(a) > 1 and isinstance(a[1], str) and a[1].startswith('soccer10_01_') else premier
            if not nom:
                continue
            t_ = tels.setdefault(nom, {'code': nom, 'debut': None, 'fin': None})
            if a[0] == 0 and t_['debut'] is None:
                t_['debut'] = f
            elif a[0] == 1 and t_['debut'] is not None and t_['fin'] is None:
                t_['fin'] = f
    L_tel = sorted((t_ for t_ in tels.values() if t_['debut'] is not None), key=lambda t_: t_['debut'])
    res['telop'] = L_tel[0] if L_tel else None
    res['telop2'] = L_tel[1] if len(L_tel) > 1 else None
    if res['telop']:
        # (14/11/2026) animation du modèle de menu du jeu (common/menu/00_soccer/soccer10/soccer10_01/soccer10_01.g4pkm) :
        # courbes LUES dans ses clips ; MESURÉ sur les vidéos (recalage image par image, corrélation 0,97) : bannière 1:1 dans
        # 1920 x 1080, centrée en (960, 856) (= os _pos_base01), entrée (« in ») jouée à 30 images/s dès « montrée »,
        # sortie (« out ») à 60 images/s dès « cachée » ; pas de glissement visible.
        try:
            pm = lire_paquet(os.path.join(c, 'menu', '00_soccer', 'soccer10', 'soccer10_01', 'soccer10_01.g4pkm'))
            def courbe(magie, nom, typ):
                for cl in (pm.get(magie) or {}).get('clips', []):
                    if cl['nom'] == nom:
                        for t in cl['cibles']:
                            for k in t['canaux']:
                                if k['type'] == typ:
                                    return [[float(i), float(v[0])] for i, v in zip(k['images'], k['valeurs'])]
                return None
            res['telop']['courbes'] = {'echelle_in': courbe('G4MT', '_mt_scl_in_01', 1), 'echelle_out': courbe('G4MT', '_mt_scl_out_01', 1),
                                       'fondu_in': courbe('G4MA', '_sma_fade_in_mat_01', 19), 'fondu_out': courbe('G4MA', '_sma_fade_out_mat_01', 19)}
            res['telop']['centre'] = [960, 856]
            res['telop']['vitesse_in'], res['telop']['vitesse_out'] = 0.5, 1.0
            if res['telop2']:                          # (24/11) même modèle de menu pour la 2e bannière
                for k_ in ('courbes', 'centre', 'vitesse_in', 'vitesse_out'):
                    res['telop2'][k_] = res['telop'][k_]
        except (OSError, ValueError, KeyError):
            pass
    # décor (stade) caché / remontré : 0x3DB3FBEB [0] / [1] (Frappe stellaire : caché de 57 à 302, la galaxie le remplace)
    # sons : event_cfg/snd/<id>_snd.cfg.bin, 0xBA67E844 [canal, genre (0 bruitage, 4 voix), nom, …] à l'image f
    res['sons'] = []
    for f, cmd, a in _commandes(os.path.join(c, 'event_cfg', 'snd', ev + '_snd.cfg.bin')):
        if cmd == SON and len(a) >= 3 and isinstance(a[2], str):
            res['sons'].append({'image': f, 'nom': a[2], 'voix': a[1] == 4})
    res['decor'] = sorted([{'image': f, 'visible': bool(a[0])} for f, cmd, a in cmds if cmd == DECOR and a], key=lambda x: x['image'])
    try:
        res['lumiere_plans'] = reglages_lumiere(data_dir, ev)
    except Exception:
        res['lumiere_plans'] = None
    # (essai du 14/11/2026 ANNULÉ : decalage_gardien déplaçait les points d'accroche au but, mais l'animation du gardien
    # contient déjà ce déplacement — corps à −44,6 quand sa racine est à +5,38. Fonction gardée, non utilisée.)
    res['decalage_points'] = None
    # (2e essai ANNULÉ : décalage du seul point_eff ; les os de l'effet sont déjà au but grâce à l'os d'échelle scale_01 x 10)
    res['decalage_eff'] = None
    return res


def decalage_gardien(ev, res):
    """CINÉMATIQUES DE GARDIEN (ev63) : la caméra est écrite dans le repère du TERRAIN (LU dans le jeu en marche le
    14/11/2026 : œil de la caméra dans le monde = valeur du fichier, sans rotation ni décalage, pour Main céleste,
    Triple défense et Poing ardent), alors que les points d'accroche (gardien, ballon, effets) sont près de l'origine.
    Le moteur pose donc les points au but. (FONCTION NON UTILISÉE depuis le 14/11 : ancienne hypothèse) décalage = ce que vise la 1re caméra (x, z) − position d'evp01
    (point_s00) au début du 1er plan ; les cibles des caméras de gardien tombent presque toutes vers z ≈ −44,4.
    -> [dx, 0, dz] ou None (autres techniques : caméra et points dans le même repère)."""
    if not ev.startswith('ev63') or not res.get('plans'):
        return None
    pl = res['plans'][0]['nom']
    cam = (res.get('camera') or {}).get(pl)
    pt = (res.get('points') or {}).get('point_s00')
    if not cam or not pt:
        return None
    ch = {k['type']: k for ci in cam['cibles'] for k in ci['canaux']}
    if 26 not in ch or 28 not in ch:
        return None
    tx, tz = ch[26]['valeurs'][0][0], ch[28]['valeurs'][0][0]
    crc = {o['crc']: o['nom'] for o in pt['os']}
    par = {o['nom']: (pt['os'][o['parent']]['nom'] if o['parent'] >= 0 else None) for o in pt['os']}
    pos = {o['nom']: list(o['t']) for o in pt['os']}
    cl = (pt.get('clips') or {}).get(pl)
    if cl:
        for ci in cl['cibles']:
            n = crc.get(ci.get('crc'))
            for k in ci['canaux']:
                if n in pos and k['type'] in (10, 11, 12):
                    pos[n][k['type'] - 10] = k['valeurs'][0][0]
    p, n = [0.0, 0.0, 0.0], 'evp01'
    while n:                                          # somme des positions jusqu'à la racine (rotations nulles dans ces points)
        p = [p[i] + pos.get(n, [0, 0, 0])[i] for i in range(3)]
        n = par.get(n)
    return [tx - p[0], 0.0, tz - p[2]]


# réglages de lumière utiles aux lumières ponctuelles (noms = registres des shaders, correspondance lue dans nie.exe)
_REGLAGES_PL = ('mapAmbient', 'mapPointLightPow', 'pointLightToonParam', 'pointLightBlendParam', 'pointLightRimParam', 'charaBlendRateParam',
                'lightDir', 'lightColor', 'lightAmbient', 'shadowColor', 'mapPbrLightInfo', 'mapPbrIBLInfo', 'mapPbrParamScaleInfo', 'ssaoBlendColor',   # + vrai shader du stade
                'bloomSubLumMap', 'bloomSubLumPost', 'bloomIntensity', 'bloomAlphaBlendRate', 'tonemapLumMax', 'tonemapLumMiddle',
                'tonemapEnable', 'tonemapEnableChara', 'tonemapFadeSpeed', 'tonemapScrLumEnable', 'tonemapScrLum',   # + effets d'écran
                # + brouillard (valeurs brutes ; conversion de nie.exe 0x140f7f050 faite dans vue3d.js : brouillardCB)
                'fogRayleighColorP20', 'fogRayleighColorP10', 'fogRayleighColorO00', 'fogRayleighColorM10', 'fogRayleighColorM20',
                'fogHeightRayleighColor', 'fogMieColorP20', 'fogMieColorO00', 'fogMieColorM20',
                'fogWorldNearScatterPush', 'fogWorldRayleighDensity', 'fogWorldMieDensity', 'fogWorldNormalDistanceRcp',
                'fogMiePhaseAnisotropy', 'fogOcclRate', 'fogHeightSeaLevel', 'fogHeightDistanceRcp', 'fogHeightNearScatterPush',
                'fogHeightRayleighDensity', 'fogHeightMieDensity', 'fogHeightNormalDistanceRcp', 'fogRayleighBandRatio',
                'charaGrTParam',
                # + cascades d'ombre (nie.exe 0x14133b1a0 / 0x141340de0)
                'shadowDir', 'useShadowDir', 'ref_scale', 'isAutoCascadeRange', 'autoCascadeFarMax', 'shadowCascadeNear', 'shadowCascadeFar', 'shadowBiasParam',
                'softParticleDistance',
                'charaAmbient', 'charaAmbLightParam', 'effectAmbientRate', 'effectPLightRate', 'effectShadowRate',
                'effectShadowContrast', 'effectShadowGrayScale', 'charaShadowParam',
                'edgeColor', 'edgeWeight0', 'edgeWeight1', 'edgePixel', 'charaEdgeFadeBegin', 'charaEdgeFadeEnd', 'useExtrutedEdge',
                'useFogSky', 'fogSkyRadius', 'cloudColor', 'mapCloudParam',
                'enableSSAO', 'ssaoBlendColor', 'ssaoShieldingScale', 'ssaoShieldingLenght', 'ssaoShieldingAngle',
                'ssaoNoiseAccuracy', 'ssaoRadius', 'ssaoEnableZ', 'ssaoSamplingNum',   # SSAO du jeu
                'dofFocusNearZ', 'dofFocusFarZ', 'dofFocusIn', 'dofFocusOut', 'dofFrontStrength', 'dofBackStrength',
                'dofGaussParam', 'dofGaussCnt', 'dofFocusTexelOffset', 'dofUseAutoFocus', 'dofUseFastVersion',   # profondeur de champ
                'footShadowRate',
                # rayons de soleil (nie.exe 0x1413311d0) et drapeaux des effets d'écran (CLightData +0x1C80…, table corrigée le 14/11/2026)
                'sunShaftColor', 'sunShaftAtten', 'sunShaftBlurScale', 'sunShaftBlurCount', 'enableSunShaft', 'enableDoF',
                'enableBloom', 'enableTonemap', 'enableLensFlare', 'enableAA',
                # (14/11/2026) ÉCLAIRAGE DES PERSONNAGES PAR PLAN : posé par les fichiers EventMap_fix_cXXXX de plus de 4 000 plans
                # (direction, force des deux ombres, seuil des reflets, liseré, occlusion…) et copié tel quel dans cb7 (CLightData
                # +0x6B0, LU) : avant, ces champs étaient ignorés (réglages du stade à la place) -> personnages et esprits trop clairs
                'charaLightDir', 'charaShadowRate1', 'charaShadowRate2', 'charaHighThreshold', 'charaUnderRimRate', 'occlusionParam',
                'charaHighColor', 'charaHighLightColor', 'charaShadow1', 'charaShadowColor1', 'charaShadow2', 'charaShadowColor2',
                'charaShadowBias', 'charaShadowEnable', 'charaSelfShadow', 'charaShadowAlphaRate', 'charaShadowBlendRate',
                'charaUnderRim', 'charaUnderRimColor', 'charaRimOutlineMax', 'charaMetalShadowRate', 'charaDropShadowRate',
                'charaDropShadowRateMax', 'charaProbLightParam', 'charaWeekLightRate', 'depthEdgeParam')   # ombre sous les pieds (FootShadowAO)   # ciel du jeu (Map_FogSky)   # contours d'écran   # Smoke2 / T1L   # particules douces (cb6[43].x)   # .w = part du brouillard sur les joueurs (chr_toon : cb7[37].w)


def _clightdata(chemin):
    from . import particules as _pt
    out = {}
    if os.path.exists(chemin):
        for nom, v in _pt.lire_brut(chemin):
            if nom == 'PROP_PARAM' and v and v[0][0] == 0:
                out[v[0][1]] = [x[1] for x in v[1:]]
    return out


def reglages_lumiere(data_dir, ev, stade='s10g001'):
    """réglages de lumière de chaque plan de la cinématique : ceux du stade (common/map/_light/<stade>_g1) remplacés par
    le fichier du plan (common/event/<ev>/<ev>_light/light_list.cfg.bin -> EV_LI_MAP_LIGHT [genre, plan, fichier])"""
    from . import particules as _pt
    c = os.path.join(data_dir, 'common')
    base = _clightdata(os.path.join(c, 'property', 'light', 'light_data.cfg.bin'))          # réglages par défaut (À LIRE EN MÉMOIRE : base de la lumière d'un plan, voir « Règles encore à lire »)
    base.update(_clightdata(os.path.join(c, 'map', '_light', stade + '_g1', stade + '_g1.objbin')))
    evx = ev.split('_')[0]
    evd = dossier_ev(c, ev)
    lst = os.path.join(c, 'event', evx, evd, evd + '_light', 'light_list.cfg.bin')
    out = {'_base': {k: base[k] for k in _REGLAGES_PL if k in base}}
    if os.path.exists(lst):
        for nom, v in _pt.lire_brut(lst):
            if nom == 'EV_LI_MAP_LIGHT' and len(v) >= 3 and isinstance(v[2][1], str):
                rel = v[2][1].replace(chr(92), '/')
                rel = rel[len('common/'):] if rel.startswith('common/') else rel
                d = dict(base); d.update(_clightdata(os.path.join(c, *rel.split('/'))))
                out[v[1][1]] = {k: d[k] for k in _REGLAGES_PL if k in d}
    return out


_collisions = {}


def collision_rendu(c, code):
    """OMBRE SOUS LES PIEDS (FootShadowAO), LU le 14/11/2026 dans nie.exe (0x141341c80, registre CRenderCollision) et dans
    la mémoire du jeu en marche : chaque personnage a un profil CRenderCollision_<X> (common/chr/<code>/<code>.objbin), décrit
    dans common/property/chara/render_collision.cfg.bin : parties m_ColPartInfo (os nullNameCrc, offsetPos, offsetRot,
    ellipse_width / depth / height ; shapeType 8 = ellipsoïde) et groupe m_aColGroup (celui des pieds). Facteur d'échelle du
    groupe = 1 (drapeau +4 du groupe = 0 en mémoire). -> [{'os': nom, 'decalage': xyz, 'rotation': xyz, 'taille': (l, p, h)}]"""
    if code in _collisions:
        return _collisions[code]
    from . import particules as _pt
    out = []
    try:
        ob = os.path.join(c, 'chr', code, code + '.objbin')
        lignes_ob = list(_pt.lire_brut(ob)) if os.path.exists(ob) else []
        profil = next((v[0][1] for n, v in lignes_ob if n == 'PROP_INFO_BGN' and v and isinstance(v[0][1], str)
                       and v[0][1].startswith('CRenderCollision')), None)
        if profil:
            sk = next((x for x in (os.path.join(c, 'chr', code, code + '.g4sk'), os.path.join(c, 'chr', code, code + '.g4pkm')) if os.path.exists(x)), None)
            noms = {o['crc'] & 0xFFFFFFFF: o['nom'] for o in lire_paquet(sk)['squelette']} if sk else {}
            # parties écrites dans l'objbin lui-même (le ballon b000001 : « CRenderCollision », sphère 0,2 sur c_c_1_0),
            # sinon celles du profil dans render_collision.cfg.bin
            dans_ob = any(n == 'PROP_PARAM_BGN' for n, v in lignes_ob[[i for i, (n, v) in enumerate(lignes_ob)
                          if n == 'PROP_INFO_BGN' and v and v[0][1] == profil][0] + 1:][:1])
            source = lignes_ob if dans_ob else list(_pt.lire_brut(os.path.join(c, 'property', 'chara', 'render_collision.cfg.bin')))
            parts, groupe, cur, p = {}, [], None, None
            for n, v in source:
                if n == 'PROP_INFO_BGN' and v:
                    cur = v[0][1]
                elif cur != profil:
                    continue
                elif n == 'PROP_PARAM_BGN' and v and v[0][1] == 'm_ColPartInfo':
                    p = {}
                elif n == 'PROP_PARAM' and p is not None and v:
                    k = v[0][1]; x = [y[1] for y in v[1:]]
                    p[k] = x[0] if len(x) == 1 else x
                elif n == 'PROP_PARAM_END' and p is not None:
                    parts[p.get('partNameCrc', 0) & 0xFFFFFFFF] = p; p = None
                elif n == 'PROP_PARAM' and v and v[0][1] == 'partNameCrc' and p is None:
                    groupe.append(v[1][1] & 0xFFFFFFFF)
            for crc in groupe or list(parts):
                q = parts.get(crc)
                if not q or q.get('shapeType') != 8:
                    continue
                nom = noms.get(q.get('nullNameCrc', 0) & 0xFFFFFFFF)
                if nom:
                    out.append({'os': nom, 'decalage': q.get('offsetPos') or [0, 0, 0], 'rotation': q.get('offsetRot') or [0, 0, 0],
                                'taille': [q.get('ellipse_width', 0.1), q.get('ellipse_depth', 0.1), q.get('ellipse_height', 0.1)]})
    except Exception:
        out = []
    _collisions[code] = out
    return out


LOAD_MODELE = 0x35746E60          # chargement d'un acteur « modèle » (c00<TYPE><NO>…, <ASSIGN>…)


def _dossier_chr(c, code):
    for d in (os.path.join(c, 'chr', '_keshin', code), os.path.join(c, 'chr', '_waza', code), os.path.join(c, 'chr', code)):
        if os.path.exists(os.path.join(d, code + '.g4pkm')):
            return d
    return None


def points_et_acteurs(c, ev, dos, cmds, plans, assign_anim=None):
    """squelettes « point » (point_eff, point_s00, point_s80…) et acteurs (joueur, esprit / totem, objets, ballon) :
    modèle, squelette, clips par plan, accroche (point, os) et ordres (jouer, montrer / cacher)"""
    points = {}
    for f, cmd, a in cmds:
        if cmd == LOAD and len(a) >= 2 and isinstance(a[1], str) and a[1].endswith('.g4sk'):
            sk = os.path.join(c, *a[1].split('/')[1:]) if a[1].startswith('common/') else os.path.join(c, a[1])
            if a[0] in points or not os.path.exists(sk):
                continue
            pt = {'os': lire_paquet(sk)['squelette'], 'clips': {}}
            for pl in plans:
                fp = os.path.join(dos, '%s_%s_%s.g4pk' % (ev, a[0], pl['nom']))
                if os.path.exists(fp):
                    pt['clips'][pl['nom']] = _clips(lire_paquet(fp)).get(pl['nom'])
            points[a[0]] = pt
    # codes des paquets d'animation du dossier de la scène (<ev>_<code>_s00_p00_<plan>.g4pk)
    codes = sorted({m.group(1) for m in (re.match(r'%s_([a-z]\d{6})_s00_p00_c\d{4}\.g4pk$' % re.escape(ev), x) for x in os.listdir(dos)) if m}) if os.path.isdir(dos) else []
    charges = {}
    for f, cmd, a in cmds:
        if cmd in (LOAD, LOAD_MODELE) and len(a) >= 2 and isinstance(a[0], str) and isinstance(a[1], str):
            if a[1].endswith(('.objbin', '.g4sk', '.g4cm', '.cfg.bin')) or a[0] in charges:
                continue
            charges[a[0]] = a[1]
    explicites = {v for v in charges.values() if re.fullmatch(r'[a-z]\d{6}', v)}
    acteurs = []
    for nom, src in charges.items():
        if nom.startswith('c00<TYPE><NO>'):
            code, modele = 'c000101', 'joueur'
        elif nom.startswith('<ASSIGN>'):
            # (23/11) assign_anim : l'esprit dont les gestes sont joués (invocation choisie dans l'Atelier : « apparition de
            # tel esprit » ; le modèle montré est remplacé ensuite par la copie, [[event]] assigned)
            code = assign_anim if assign_anim in codes else next((x for x in codes if x[0] in 'ka' and x not in explicites), None); modele = 'chr'
        elif re.fullmatch(r'[a-z]\d{6}', src):
            code, modele = src, 'chr'
        elif _dossier_chr(c, src):
            # CORRIGÉ 14/11/2026 : modèles propres à une technique, nommés comme la cinématique (chr/_waza/ev63_01230 = main
            # de sable de « Poing de sable », 215 modèles ev6x_xxxxx) : ils étaient ignorés (seuls les noms « k000123 » passaient)
            code, modele = src, 'chr'
        else:
            continue
        # (25/11) animations rangées sous le nom de l'ACTEUR quand le modèle chargé est un autre (LU dans le cache de VRFW :
        # copie Tiger fang ev63_86020, modèle ev63_86020, paquets « ev63_86020_ev63_00300_s00_p00_c0020.g4pk ») ; avant,
        # l'acteur était écarté (tigre absent de la copie de Tiger fang faite par l'Atelier, scène livrée en fichiers)
        code_clips = code
        a_m = re.match(r'(.+?)_s\d\d_p', nom)
        if code and code not in codes and a_m and a_m.group(1) != code and any(x.startswith('%s_%s_' % (ev, a_m.group(1))) for x in os.listdir(dos)):
            code_clips = a_m.group(1)
        if not code or (code_clips not in codes and not any(x.startswith('%s_%s_' % (ev, code_clips)) for x in os.listdir(dos))):
            continue
        # emplacement de l'acteur dans la scène : « …_s01_p<VARIATION> » -> s01 (2e joueur de Feu glacé…) ; s00 par défaut
        m_s = re.search(r'_(s\d\d)_p', nom)
        emp = m_s.group(1) if m_s else 's00'
        sk = os.path.join(c, 'chr', 'c000101', 'c000101.g4sk') if modele == 'joueur' else None
        if not sk:
            d = _dossier_chr(c, code)
            if not d:
                continue
            sk = os.path.join(d, code + '.g4pkm')
        clips = {}
        for pl in plans:
            fp = os.path.join(dos, '%s_%s_%s_p00_%s.g4pk' % (ev, code_clips, emp, pl['nom']))
            if os.path.exists(fp):
                cl = _clips(lire_paquet(fp)).get(pl['nom'])
                if cl:
                    clips[pl['nom']] = cl
        # ordres de cet acteur (pour le joueur : ceux de la corpulence 01)
        ordres, type_en_cours = [], None
        for f, cmd, a in cmds:
            if cmd == CHOIX and len(a) >= 3 and a[1] == 'TYPE':
                type_en_cours = a[2]; continue
            if not a or a[0] != nom:
                continue
            if cmd == ATTACHE and len(a) >= 3 and (type_en_cours in (None, '01') or '<TYPE>' not in nom):
                ordres.append({'image': f, 'accroche': [a[1], a[2]]})
            elif cmd == PLAY and len(a) >= 2:
                ordres.append({'image': f, 'jouer': a[1]})
            elif cmd == VISIBLE and len(a) >= 2:
                ordres.append({'image': f, 'visible': bool(a[1])})
            elif cmd == FONDU and len(a) >= 3:
                # FONDU D'UN MODÈLE (15/11/2026, LU nie.exe) : commande 0x48A58CDC [acteur, valeur, images, …] (gestionnaire 0x140f39730) ->
                #   0x141817db0 : couche « event » (crc 0x3bae0aa7) du contrôleur de fondu du modèle (+0x790) ; valeur bornée à 0..1, atteinte
                #   en images x 1/60 s, en ligne droite depuis la valeur du moment (0x140baa840) ; valeur de départ 1 (+0xA8 = 1,0).
                #   Modèle pas dessiné du tout si la valeur <= 0,001 (0x1417de6cf, constante 0x141a7cad4).
                ordres.append({'image': f, 'fondu': [min(1.0, max(0.0, float(a[1]))), max(0.0, float(a[2]))]})
            if cmd == ATTACHE:
                type_en_cours = None
        a = {'acteur': nom, 'code': code, 'modele': modele, 'os': lire_paquet(sk)['squelette'], 'clips': clips,
             'ordres': sorted(ordres, key=lambda x: x['image']), 'g4sk': entete_g4sk(sk),
             'nus': non_uniforme(os.path.join(os.path.dirname(sk), code + '.objbin'))}
        if modele == 'joueur':                       # mêmes gestes pour les 4 corpulences : squelette + clips de chacune
            a['corps'] = {}
            for t in (1, 2, 3, 4):
                ct = 'c000%d01' % t
                skt = os.path.join(c, 'chr', ct, ct + '.g4sk')
                cl = {}
                for pl in plans:
                    fp = os.path.join(dos, '%s_%s_%s_p00_%s.g4pk' % (ev, ct, emp, pl['nom']))
                    if os.path.exists(fp):
                        x = _clips(lire_paquet(fp)).get(pl['nom'])
                        if x:
                            cl[pl['nom']] = x
                if cl and os.path.exists(skt):
                    a['corps'][t] = {'os': lire_paquet(skt)['squelette'], 'clips': cl, 'collision': collision_rendu(c, ct),
                                     'g4sk': entete_g4sk(skt), 'nus': non_uniforme(os.path.join(c, 'chr', ct, ct + '.objbin'))}
        a['collision'] = collision_rendu(c, code)
        acteurs.append(a)
    return points, acteurs
