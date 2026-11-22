"""Atelier Maillots : catalogue des maillots du jeu, projet (liste de mes maillots) et construction du mod VRFW
« MesMaillots » (objets, tenues domicile / extérieur, icônes, boutique générale d'Inazuma Fantasy)."""
import os, json, glob, re, struct, zlib, shutil, unicodedata, time
from . import images, bustes, numeros, relief, bords, modele3d
from .cfgbin import parse

ICI = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REGLAGES = os.path.join(ICI, 'reglages.json')
PROJET = os.path.join(ICI, 'mes_maillots.json')
CATALOGUE = os.path.join(ICI, 'catalogue.json')
TRAVAIL = os.path.join(ICI, 'travail')
MOD_ID = 'MesMaillots'
VARIANTES = ('', '_slv', '_fld', '_dam', '_blyR')
CELLULES_JOUEUR = (('uniformFielderModelIdCrc', ''), ('uniformFielderShoulderBaringModelIdCrc', '_slv'),
                   ('uniformFielderShortSleeveRollUpArmModelIdCrc', '_fld'),
                   ('uniformFielderShoulderBaringPatternedModelIdCrc', '_dam'),
                   ('uniformFielderNavelBaringModelIdCrc', '_blyR'))
# le gardien porte les modèles des joueurs (une texture de joueur sur le modèle de gardien le rend invisible)
CELLULES_GARDIEN = (('uniformKeeperModelIdCrc', ''), ('uniformKeeperLongSleeveRollUpArmModelIdCrc', '_fld'),
                    ('uniformKeeperLongSleeveRollUpSleeveModelIdCrc', ''), ('uniformKeeperNavelBaringModelIdCrc', '_blyR'))
LANGUES = ('fr', 'en', 'es', 'de', 'it', 'pt', 'ja', 'zh_hans', 'zh_hant')

DEFAUT = {
    'donnees': os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'data'),
    'mods': r'C:\Program Files (x86)\Steam\steamapps\common\INAZUMA ELEVEN Victory Road\mods',
    'auteur': '',
}


def reglages():
    r = dict(DEFAUT)
    if os.path.exists(REGLAGES):
        r.update(json.load(open(REGLAGES, encoding='utf-8')))
    else:
        json.dump(r, open(REGLAGES, 'w', encoding='utf-8'), ensure_ascii=False, indent=2)
    v = os.environ.get('ATELIER_JEU_DIRECT')          # lancé par l'Atelier en lecture directe
    if not os.path.isfile(os.path.join(r['donnees'], 'common', 'text', 'fr', 'chara_text.cfg.bin')):
        if v:
            r['donnees'] = v.split(os.pathsep, 1)[1]
        else:                                          # (21/11) lancé SEUL sans fichiers extraits : lecture directe aussi
            ac, jeu = _jeu_de_l_atelier()
            if jeu and os.path.isfile(os.path.join(jeu, 'data', 'cpk_list.cfg.bin')):
                try:
                    from moteur import donnees_virtuelles as _dv
                    r['donnees'] = _dv.activer(jeu, os.path.join(ac, 'cache', 'data_jeu'))
                except Exception as ex:
                    print('lecture directe :', ex)
    # (21/11) dossier « mods » : celui du jeu de l'Atelier quand celui des réglages n'est pas dans un vrai jeu (avant :
    # chemin écrit en dur, faux pour un jeu dans une autre bibliothèque Steam ou une copie de dépôt -> maillots invisibles)
    if r.get('mods') == DEFAUT['mods'] or not os.path.isfile(os.path.join(os.path.dirname(os.path.normpath(r.get('mods') or '')), 'nie.exe')):
        jeu = _jeu_de_l_atelier()[1]
        if jeu:
            r['mods'] = os.path.join(jeu, 'mods')
    return r


def _jeu_de_l_atelier():
    """(dossier AtelierCouleurs, dossier du jeu) : celui de la config de l'Atelier, sinon trouvé comme lui le trouve"""
    ac = os.path.join(os.path.dirname(ICI), 'AtelierCouleurs')
    try:
        j = json.load(open(os.path.join(ac, 'config.json'), encoding='utf-8')).get('jeu_dir')
        if j and os.path.isfile(os.path.join(j, 'nie.exe')):
            return ac, j
    except (OSError, ValueError):
        pass
    try:
        import sys
        if ac not in sys.path:
            sys.path.insert(0, ac)
        from moteur import config_auto
        return ac, config_auto.trouver_jeu(ac)
    except Exception:
        return ac, None


# -------------------------------------------------------------------------------------------- catalogue
def construire_catalogue(donnees, journal=print):
    """maillots du jeu utilisables comme base : clé, nom, uniforme, textures domicile / extérieur, icône"""
    ic = sorted(glob.glob(os.path.join(donnees, 'common', 'gamedata', 'item', 'item_config_*.cfg.bin')))[-1]
    journal('lecture des noms des objets…')
    txt = {v[0] & 0xffffffff: v[5] for n, v in parse(os.path.join(donnees, 'common', 'text', 'fr', 'item_text.cfg.bin'))
           if n == 'NOUN_INFO' and v and v[1] == 0}
    uni = open(glob.glob(os.path.join(donnees, 'common', 'gamedata', 'character', 'uniform_config_*.cfg.bin'))[0], 'rb').read()
    # modèles de vêtements du jeu : nombre de lignes (corps) de chaque modèle, ex. u110201_10 -> 14, u110201_10_blyR -> 1
    lignes = {}
    parts = sorted(glob.glob(os.path.join(donnees, 'common', 'gamedata', 'character', 'chara_parts_*.cfg.bin')))
    if parts:
        dernier = None
        for n, v in parse(parts[-1]):
            if n == 'CHARA_PARTS_CLOTHES_MODEL' and len(v) > 1 and isinstance(v[1], str):
                dernier = v[1]
            elif n == 'CHARA_PARTS_CLOTHES_MODEL_REF_INFO' and dernier and len(v) > 1:
                lignes[dernier] = v[1]; dernier = None
    tex = {}
    for p in glob.glob(os.path.join(donnees, 'dx11', 'chr', '_uniform', '*', 'u*_*.g4tx')):
        tex[os.path.basename(p)[:-5]] = p
    journal('lecture des maillots du jeu…')
    cat = []
    for n, v in parse(ic):
        if n != 'ITEM_FASHION_INFO' or not v:
            continue
        cle = next((x for x in v if isinstance(x, str)), '')
        if not cle.startswith('uni_u') or cle.endswith('_20'):
            continue
        code = cle[4:]
        if (code + '_10') not in tex:
            continue
        def a(s): return struct.pack('<I', zlib.crc32(s.encode())) in uni
        # variantes de modèle qui existent (manches, etc.) et leur nombre de lignes ; le modèle principal est obligatoire
        var = {}
        for t in ('10', '20'):
            for s_ in VARIANTES:
                m_ = code + '_' + t + s_
                if a(m_) and (not lignes or m_ in lignes):
                    var[t + s_] = lignes.get(m_, {'': 14, '_slv': 2}.get(s_, 1))
        if '10' not in var:
            continue
        nom = next((txt[x & 0xffffffff] for x in v[1:5] if isinstance(x, int) and (x & 0xffffffff) in txt), cle)
        cat.append({'cle': cle, 'code': code, 'nom': nom, 'uniforme': v[-1] & 0xffffffff,
                    'tex10': tex[code + '_10'], 'tex20': tex.get(code + '_20'), 'variantes': var})
    cat.sort(key=lambda e: e['nom'].lower())
    json.dump(cat, open(CATALOGUE, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    journal('%d maillots du jeu utilisables comme base' % len(cat))
    return cat


def catalogue(donnees, journal=print):
    if os.path.exists(CATALOGUE):
        return json.load(open(CATALOGUE, encoding='utf-8'))
    return construire_catalogue(donnees, journal)


def planche_icones(donnees):
    return os.path.join(donnees, 'dx11', 'menu', '200_icon', '02_icon_item', 'icon_item07.g4tx')


# ------------------------------------------------------------------------------------------------ projet
def charger_projet():
    if os.path.exists(PROJET):
        return json.load(open(PROJET, encoding='utf-8'))
    return {'maillots': []}


def sauver_projet(p):
    tmp = PROJET + '.tmp'
    json.dump(p, open(tmp, 'w', encoding='utf-8'), ensure_ascii=False, indent=2)
    os.replace(tmp, PROJET)


def identifiant(nom, existants):
    s = unicodedata.normalize('NFKD', nom).encode('ascii', 'ignore').decode().lower()
    s = re.sub(r'[^a-z0-9]+', '_', s).strip('_')[:24] or 'maillot'
    base, k = s, 2
    while s in existants:
        s = '%s_%d' % (base, k); k += 1
    return s


def dossier_travail(m):
    d = os.path.join(TRAVAIL, m['id'])
    os.makedirs(d, exist_ok=True)
    _verifier_coupe(m, d)
    return d


def _verifier_coupe(m, d):
    """les images exportées (haut_domicile.png…) sont celles d'UNE coupe : si la coupe a changé, elles sont rangées
    dans « ancienne_coupe_<code> » (rien n'est effacé) pour que l'aperçu et « Modifier… » prennent la nouvelle"""
    base = m.get('base') or ''
    marque = os.path.join(d, 'coupe.txt')
    try:
        ancienne = open(marque, encoding='utf-8').read().strip() if os.path.exists(marque) else None
    except OSError:
        return
    if ancienne == base:
        return
    presents = [f for f in FICHIER_BASE.values() if os.path.exists(os.path.join(d, f))]
    if presents:
        utilises = {os.path.normcase(os.path.abspath(m[k])) for k in FICHIER_BASE if m.get(k)}
        rangement = os.path.join(d, 'ancienne_coupe_%s' % (ancienne or 'precedente'))
        for f in presents:
            p = os.path.join(d, f)
            if os.path.normcase(os.path.abspath(p)) in utilises:
                continue        # image choisie dans « Mes images » : on n'y touche pas
            try:
                os.makedirs(rangement, exist_ok=True)
                os.replace(p, os.path.join(rangement, f))
            except OSError:
                pass
    try:
        with open(marque, 'w', encoding='utf-8') as f:
            f.write(base)
    except OSError:
        pass


def exporter_base(m, cat_par_cle, donnees, journal=print):
    """images à modifier : haut / short domicile et extérieur du maillot de base, et son icône"""
    b = cat_par_cle[m['base']]
    d = dossier_travail(m)
    faits = []
    for cote, src in (('domicile', b['tex10']), ('exterieur', b['tex20'] or b['tex10'])):
        g = images.G4TX(open(src, 'rb').read())
        for partie, suf in (('haut', '20'), ('short', '30')):
            nom = g.principal(suf)
            if not nom:
                continue
            journal('export : %s %s…' % (partie, cote))
            w, h, rows = g.image(nom)
            p = os.path.join(d, '%s_%s.png' % (partie, cote))
            images.ecrire_png(p, w, h, rows)
            faits.append(p)
    ic = images.icone_planche(planche_icones(donnees), m['base'])
    if ic:
        p = os.path.join(d, 'icone.png')
        images.ecrire_png(p, *ic)
        faits.append(p)
    journal('images exportées dans ' + d)
    return d, faits


FICHIER_BASE = {'haut_dom': 'haut_domicile.png', 'short_dom': 'short_domicile.png', 'haut_ext': 'haut_exterieur.png',
                'short_ext': 'short_exterieur.png', 'icone': 'icone.png'}


def _couleur_rows(w, h, rows):
    compte = {}
    for y in range(0, h, 8):
        mv = memoryview(rows[y]).cast('I')
        for v in mv[::8]:
            if (v >> 24) < 128:
                continue
            k = ((v & 255) >> 3, ((v >> 8) & 255) >> 3, ((v >> 16) & 255) >> 3)
            compte[k] = compte.get(k, 0) + 1
    k = max(compte, key=compte.get)
    return tuple(min(255, (c << 3) + 4) for c in k)


def apercu(m, cat_par_cle, donnees):
    """images de l'aperçu : icône, portraits domicile / extérieur (comme sur les cartes), hauts domicile / extérieur"""
    b = cat_par_cle.get(m.get('base'))
    if not b:
        return {}
    d = dossier_travail(m)
    out = {}
    def haut(cle, defaut, tex):
        p = m.get(cle)
        if p and os.path.exists(p):
            return images.lire_png(p)
        e = os.path.join(d, FICHIER_BASE[defaut])
        if os.path.exists(e):
            return images.lire_png(e)
        g = images.G4TX(open(tex, 'rb').read())
        res = g.image(g.principal('20'))
        try:
            images.ecrire_png(e, *res)      # gardée : la prochaine fois l'aperçu est immédiat
        except OSError:
            pass
        return res
    h10 = haut('haut_dom', 'haut_dom', b['tex10'])
    h20 = haut('haut_ext', 'haut_ext', b['tex20'] or b['tex10']) if (m.get('haut_ext') or not m.get('haut_dom')) else h10
    out['h10'], out['h20'] = h10, h20
    dossier_bustes = os.path.join(donnees, 'dx11', 'menu', '200_icon', '10_icon_chr', 'uniform')
    for cote, hh, perso in (('10', h10, m.get('haut_dom')), ('20', h20, m.get('haut_ext') or m.get('haut_dom'))):
        f = os.path.join(dossier_bustes, '%s_%s_00_l.g4tx' % (b['code'], cote))
        if not os.path.exists(f):
            continue
        g = images.G4TX(open(f, 'rb').read())
        w, h, rows = g.image(g.noms[0])
        if perso:
            bustes.recolorer(rows, w, h, _couleur_rows(*hh))
        out['b' + cote] = (w, h, rows)
    ic = m.get('icone')
    if ic and os.path.exists(ic):
        out['icone'] = images.lire_png(ic)
    else:
        out['icone'] = images.icone_planche(planche_icones(donnees), m['base'])
    return out


# ------------------------------------------------------------------------------------------ construction
def _texture(base_g4tx, haut_png, short_png, pool, journal, etiquette, ocs=None, plis='base', tris=None):
    g = images.G4TX(open(base_g4tx, 'rb').read())
    rempl = {}
    # relief du tissu (ombrage « oc ») : sans les coutures et décorations du maillot d'origine
    for suf, im in (ocs or {}).items():
        n_oc = next((n for n in g.noms if n.endswith('_%soc' % suf)), None)
        if n_oc and im and (im[0], im[1]) == g.taille(n_oc):
            rempl[n_oc] = images.dds_bc1(im[0], im[1], im[2], pool, mips=images.mips_dds(g.blocs[g.noms.index(n_oc)]))
            journal('%s : relief du tissu (%s) : %s' % (etiquette, 'haut' if suf == '20' else 'short', plis))
            # reflets qui suivent le dessin d'origine : une seule teinte
            for n_sp in (n for n in g.noms if n.endswith('_%ssp' % suf) or n.endswith('_%sspm' % suf)):
                w_, h_, r_ = g.image(n_sp)
                rempl[n_sp] = images.dds_bc1(w_, h_, relief.uni(w_, h_, r_), pool, mips=images.mips_dds(g.blocs[g.noms.index(n_sp)]))
    for png, suf, partie in ((haut_png, '20', 'haut'), (short_png, '30', 'short')):
        if not png:
            continue
        nom = g.principal(suf)
        if not nom:
            raise ValueError('pas de « %s » dans %s' % (partie, os.path.basename(base_g4tx)))
        tw, th = g.taille(nom)
        journal('%s : lecture de %s…' % (etiquette, os.path.basename(png)))
        w, h, rows = images.lire_png(png)
        mips = images.mips_dds(g.blocs[g.noms.index(nom)])     # autant de niveaux que l'original du jeu
        if min(w, h) > tw and tw == th:
            # image plus grande que celle du jeu (ex. short de 128 px agrandi dans le studio) : on garde les détails
            n = min(2048, 1 << (min(w, h).bit_length() - 1))
            mips += (n.bit_length() - tw.bit_length())         # le jeu : niveaux = log2(taille) - 1
            journal('%s : %s agrandi de %dx%d à %dx%d' % (etiquette, partie, tw, th, n, n))
            tw = th = n
        if (w, h) != (tw, th):
            journal('%s : %s redimensionné de %dx%d à %dx%d' % (etiquette, partie, w, h, tw, th))
            rows = images.redimensionner(w, h, rows, tw, th)
        if tris and tris.get(suf):
            # fond autour des pièces : couleur du bord le plus proche (sinon il « bave » de loin, au col, aux coutures)
            rows = bords.remplir(tw, th, rows, tris[suf])
        t0 = time.time()
        rempl[nom] = images.dds_bc1(tw, th, rows, pool,
                                    lambda f: journal('%s : encodage du %s %d %%' % (etiquette, partie, int(f * 100)), True),
                                    mips=mips)
        journal('%s : %s encodé en %d s' % (etiquette, partie, time.time() - t0))
    return g.reconstruire(rempl)


def code_modele(m, base_code):
    """nom des modèles du maillot : même longueur que le code du maillot de base (7 caractères, ex. u110201),
    pour que les bustes des portraits puissent être renommés sans changer la structure de leurs fichiers"""
    # se termine par 01 (corps standard) : le jeu remplace ces 2 chiffres par le numéro du corps (02-08, gardiens 51-58)
    c = 'm%04x01' % (zlib.crc32(m['id'].encode()) & 0xffff)
    assert len(c) == len(base_code), (c, base_code)
    return c


def couleur_dominante(png):
    """couleur la plus présente d'une image (pour colorer les bustes des portraits)"""
    w, h, rows = images.lire_png(png)
    compte = {}
    for y in range(0, h, 4):
        r = rows[y]
        for x in range(0, w, 4):
            if r[x * 4 + 3] < 128:
                continue
            k = (r[x * 4] >> 3, r[x * 4 + 1] >> 3, r[x * 4 + 2] >> 3)
            compte[k] = compte.get(k, 0) + 1
    k = max(compte, key=compte.get)
    return tuple(min(255, (v << 3) + 4) for v in k)


def _signature(m):
    """empreinte des réglages et des images d'un maillot (pour ne réencoder que ce qui a changé)"""
    parts = [m['base'], 'plis:%s' % m.get('plis', 'simples'), 'v2', 'bords1']
    for k in ('buste_dom', 'buste_ext'):         # motif des portraits (fait par le studio)
        p = os.path.join(TRAVAIL, m['id'], '%s_modifie.png' % k)
        parts.append('%s:%s' % (k, os.path.getmtime(p) if os.path.exists(p) else '-'))
    for k in ('haut_dom', 'short_dom', 'haut_ext', 'short_ext'):
        p = m.get(k)
        parts.append('%s:%s:%s' % (k, p, os.path.getmtime(p) if p and os.path.exists(p) else '-'))
    return zlib.crc32('|'.join(parts).encode())


def _embleme(m, donnees, dest, journal):
    """emblème d'équipe du maillot : 2 textures (512 et 256, BC7 avec transparence) faites sur le modèle d'un emblème
    du jeu (em900012), renommées ; renvoie le code (em97xxxx)"""
    modele = os.path.join(donnees, 'dx11', 'menu', '200_icon', '01_icon_emblem', 'em900012')
    code = 'em97%04d' % (zlib.crc32(m['id'].encode()) % 10000)
    w, h, rows = images.lire_png(m['embleme'])
    os.makedirs(dest, exist_ok=True)
    for suffixe, taille in (('', 512), ('_s', 256)):
        g = images.G4TX(open(modele + suffixe + '.g4tx', 'rb').read())
        bl = g.blocs[0]
        tete = len(bl) - taille * taille                 # BC7 : 1 octet par pixel
        r = images.redimensionner(w, h, rows, taille, taille) if (w, h) != (taille, taille) else rows
        neuf = bytes(bl[:tete]) + bustes.encoder_bc7(taille, taille, r)
        o = bustes.renommer(g.reconstruire({g.noms[0]: neuf}), 'em900012', code)
        open(os.path.join(dest, code + suffixe + '.g4tx'), 'wb').write(o)
    journal('%s : emblème %s' % (m['nom'], code))
    return code


def _cache_ok(p):
    """texture du cache utilisable (une construction interrompue peut laisser un fichier vide ou coupé)"""
    try:
        if os.path.getsize(p) < 1024:
            return False
        images.G4TX(open(p, 'rb').read())
        return True
    except Exception:
        return False


def _ecrire_cache(p, octets):
    tmp = p + '.tmp'
    open(tmp, 'wb').write(octets)
    os.replace(tmp, p)


def construire_mod(projet, cat_par_cle, rgl, pool=None, journal=print):
    """écrit le mod dans un dossier temporaire puis remplace mods/MesMaillots ; active le mod"""
    mods = rgl['mods']
    cible = os.path.join(mods, MOD_ID)
    tmp = os.path.join(ICI, '_construction')
    if os.path.exists(tmp):
        shutil.rmtree(tmp)
    cache = os.path.join(ICI, 'cache_textures')
    os.makedirs(cache, exist_ok=True)
    tex_dir = os.path.join(tmp, 'assets', 'chr', '_uniform', 'mesmaillots')
    buste_dir = os.path.join(tmp, 'assets', 'menu', '200_icon', '10_icon_chr', 'uniform')
    ico_dir = os.path.join(tmp, 'assets', 'images', 'menu', '200_icon', '02_icon_item', 'mesmaillots_icones')
    for d in (tex_dir, buste_dir, ico_dir, os.path.join(tmp, 'content', 'looks'), os.path.join(tmp, 'content', 'items'),
              os.path.join(tmp, 'content', 'images', 'menu', '200_icon', '02_icon_item'),
              os.path.join(tmp, 'content', 'sprite_redirects'),
              os.path.join(tmp, 'addons', 'InazumaFantasy', 'content', 'shops'), os.path.join(tmp, 'text')):
        os.makedirs(d, exist_ok=True)
    looks = ['schema = "VRFW.look/2"', '# GÉNÉRÉ par l\'Atelier Maillots : ne pas modifier à la main.', '']
    items = ['schema = "VRFW.item/2"', '# GÉNÉRÉ par l\'Atelier Maillots : ne pas modifier à la main.', 'default_lang = "en"', '']
    icones = ['schema = "VRFW.image/1"', '# GÉNÉRÉ par l\'Atelier Maillots', '']
    boutique = ['schema = "VRFW.shop/2"', '# GÉNÉRÉ par l\'Atelier Maillots', '', '[[edit]]', 'target = "InazumaFantasy.general_store"', '']
    sprites = []
    for m in projet['maillots']:
        b = cat_par_cle.get(m['base'])
        if not b:
            raise ValueError('%s : maillot de base %s introuvable' % (m['nom'], m['base']))
        if not m.get('haut_dom'):
            raise ValueError('%s : il manque l\'image du haut (domicile)' % m['nom'])
        mid = m['id']
        # textures (réutilisées depuis le cache si rien n'a changé)
        sig = _signature(m)
        dom_c = os.path.join(cache, '%s_%08X_10.g4tx' % (mid, sig))
        ext_c = os.path.join(cache, '%s_%08X_20.g4tx' % (mid, sig))
        a_ext = bool(m.get('haut_ext') or m.get('short_ext'))
        plis = m.get('plis', 'simples')
        rel = os.path.join(cache, 'relief')
        tris = {'20': [], '30': []}            # morceaux du modèle 3D sur le patron (toutes les corpulences)
        try:
            for corps in range(1, 9):
                p_ = modele3d.chemin_modele(rgl['donnees'], b['tex10'], corps)
                for k_, (pos_, uv_, idx_) in (modele3d.parties(p_) if p_ else {}).items():
                    dest = '30' if k_ == 'short' else ('20' if k_ == 'haut' or k_.startswith('col') else None)
                    if dest:
                        for i_ in idx_:
                            tris[dest].extend((uv_[2 * i_], uv_[2 * i_ + 1]))
        except Exception as e:
            journal('%s : bords non traités (%s)' % (m['nom'], e))
            tris = None
        def ocs_pour(haut, short):
            o = {}
            for suf, png in (('20', haut), ('30', short)):
                if png and plis != 'base':
                    o[suf] = relief.oc_pour(list(cat_par_cle.values()), b, suf, plis, rel, journal)
            return o
        if not _cache_ok(dom_c):
            _ecrire_cache(dom_c, _texture(b['tex10'], m.get('haut_dom'), m.get('short_dom'), pool, journal, m['nom'] + ' (domicile)',
                                          ocs_pour(m.get('haut_dom'), m.get('short_dom')), plis, tris))
        if a_ext and not _cache_ok(ext_c):
            h_, s_ = m.get('haut_ext') or m.get('haut_dom'), m.get('short_ext') or m.get('short_dom')
            _ecrire_cache(ext_c, _texture(b['tex20'] or b['tex10'], h_, s_, pool, journal, m['nom'] + ' (extérieur)',
                                          ocs_pour(h_, s_), plis, tris))
        # bustes des portraits (sans eux, le buste est vide sur les cartes des joueurs)
        code = code_modele(m, b['code'])
        bc = os.path.join(cache, '%s_%08X_bustes' % (mid, sig))
        if not os.path.isdir(bc):
            c10 = couleur_dominante(m['haut_dom'])
            c20 = couleur_dominante(m.get('haut_ext') or m['haut_dom'])
            journal('%s : bustes des portraits (domicile %s, extérieur %s)…' % (m['nom'], c10, c20))
            if os.path.exists(bc + '.tmp'):
                shutil.rmtree(bc + '.tmp')
            motifs = {}
            for cote, k in (('10', 'buste_dom'), ('20', 'buste_ext')):
                p_ = os.path.join(dossier_travail(m), '%s_modifie.png' % k)
                if not os.path.exists(p_) and cote == '20':
                    p_ = os.path.join(dossier_travail(m), 'buste_dom_modifie.png')
                if os.path.exists(p_):
                    motifs[cote] = images.lire_png(p_)
            if motifs:
                journal('%s : motif du maillot sur les portraits' % m['nom'])
            bustes.faire_bustes(os.path.join(rgl['donnees'], 'dx11', 'menu', '200_icon', '10_icon_chr', 'uniform'),
                                b['code'], code, {'10': c10, '20': c20}, bc + '.tmp', journal, motifs)
            os.replace(bc + '.tmp', bc)
        for f in os.listdir(bc):
            shutil.copy(os.path.join(bc, f), os.path.join(buste_dir, f))
        # le nom du fichier de texture = le code des modèles : le jeu en tire le nom des bustes des portraits
        shutil.copy(dom_c, os.path.join(tex_dir, code + '_10.g4tx'))
        if a_ext:
            shutil.copy(ext_c, os.path.join(tex_dir, code + '_20.g4tx'))
        # numéro dans le dos (couleurs, police, taille / hauteur)
        num = numeros.params(m)
        redim = num['perso'] and (abs(num['taille'] - 1) > 0.01 or abs(num['hauteur']) > 0.001)
        avec_nom = num['perso'] and num.get('nom')                 # nom du joueur au-dessus du numéro
        famille = 'n0002' if avec_nom else 'n0001'
        nom_num = lambda c: ('y' if avec_nom else 'x') + '%s%02d' % (code[1:5], c)   # 7 caractères comme n000101
        if redim:
            for c in sorted({c for l in numeros.CORPS_LIGNES.values() for c in l}):
                numeros.ecrire_modele_transforme(rgl['donnees'], c, num['taille'], num['hauteur'] / 100.0, tex_dir, nom_num(c), famille)
        tex_num = '_uniform/n000101/n00010%d_10.g4tx' % int(num['police'])
        if avec_nom:
            tex_num = '_uniform/n000201/n000201_10.g4tx'
            if num.get('lettres', 'jeu') != 'jeu':
                f_ = 'n%s01_10.g4tx' % code[1:5]
                if numeros.texture_nom(rgl['donnees'], dossier_travail(m), os.path.join(tex_dir, f_), pool, journal):
                    tex_num = '_uniform/mesmaillots/' + f_
        # modèles : joueurs (les gardiens portent les mêmes)
        for cote, tex in (('10', code + '_10'), ('20', code + ('_20' if a_ext else '_10'))):
            var = b.get('variantes')
            cote_b = cote if (not var or (cote in var)) else '10'     # pas de modèle extérieur : celui du domicile
            for v in VARIANTES:
                if var is not None and (cote_b + v) not in var:
                    continue                     # variante absente de ce maillot du jeu
                nb = var[cote_b + v] if var else {'': 14, '_slv': 2}.get(v, 1)
                rows = []
                for i in range(nb):
                    ch = []
                    if i == 0:
                        ch.append('upper_texture = "_uniform/mesmaillots/%s.g4tx"' % tex)
                        if num['perso']:
                            ch.append('lower_texture = "%s"' % tex_num)
                    corps = numeros.CORPS_LIGNES[v][i] if i < len(numeros.CORPS_LIGNES[v]) else 1
                    if redim:
                        ch.append('lower_mesh = "_uniform/mesmaillots/%s.g4md"' % nom_num(corps))
                    elif avec_nom:
                        ch.append('lower_mesh = "_uniform/n000201/n0002%02d.g4md"' % corps)
                    rows.append('{ %s }' % ', '.join(ch) if ch else '{}')
                looks += ['[[clothes]]', 'model = "%s_%s%s"' % (code, cote, v), 'from = "%s_%s%s"' % (b['code'], cote_b, v),
                          'rows = [%s]' % ', '.join(rows), '']
                if num['perso']:
                    looks += ['[[number]]', 'clothes = "%s_%s%s"' % (code, cote, v),
                              'fill = "%s"' % num['remplissage'].lstrip('#').upper()[:6],
                              'outline = "%s"' % num['contour'].lstrip('#').upper()[:6], '']
        looks += ['[[kit]]', 'name = "kit_%s"' % mid, 'from = 0x%08X' % b['uniforme']]
        for t, cote in ((0, '10'), (1, '20')):
            looks += ['  [[kit.model]]', '  type = %d' % t, '  [kit.model.cells]']
            var = b.get('variantes')
            for cell, v in CELLULES_JOUEUR + CELLULES_GARDIEN:
                c_ = '10' if (var and cote not in var) else cote
                if var is not None and (c_ + v) not in var:
                    v = ''                       # variante absente : le modèle principal
                looks.append('  %s = "%s_%s%s"' % (cell, code, cote, v))
        looks.append('')
        # icône
        cle_ic = 'uni_mm_%s' % mid
        ic_png = os.path.join(ico_dir, cle_ic + '.png')
        src = m.get('icone')
        if src and os.path.exists(src):
            w, h, rows = images.lire_png(src)
            images.ecrire_png(ic_png, 256, 256, images.redimensionner(w, h, rows, 256, 256))
        else:
            ic = images.icone_planche(planche_icones(rgl['donnees']), m['base'])
            if not ic:
                raise ValueError('%s : pas d\'icône (ni la tienne, ni celle du maillot de base)' % m['nom'])
            images.ecrire_png(ic_png, *ic)
        icones += ['[[texture]]', 'atlas = "#/menu/200_icon/02_icon_item/mesmaillots_icones.g4tx"',
                   'name = "%s"' % cle_ic, 'png = "mesmaillots_icones/%s.png"' % cle_ic, '']
        sprites.append(cle_ic)
        # objet
        items += ['[[item]]', 'name = "kit_%s"' % mid, 'base = "%s"' % m['base'], 'category = "kit"',
                  'icon_key = "%s"' % cle_ic, 'model = { uniform = "%s.kit_%s" }' % (MOD_ID, mid)]
        for lg in LANGUES:
            items += ['  [item.text.%s]' % lg, '  name = %s' % json.dumps(m['nom'], ensure_ascii=False)]
        items.append('')
        boutique += ['  [[edit.entry]]', '  item = "%s.kit_%s"' % (MOD_ID, mid), '  price = %d' % int(m.get('prix', 1)),
                     '  currency = "tk_bb000001"', '  stock = 1', '']
        # emblème d'équipe (facultatif)
        if m.get('embleme') and os.path.exists(m['embleme']):
            code_em = _embleme(m, rgl['donnees'], os.path.join(tmp, 'assets', 'menu', '200_icon', '01_icon_emblem'), journal)
            items += ['[[item]]', 'name = "embleme_%s"' % mid, 'base = "em900012"', 'category = "emblem"',
                      'icon_key = "%s"' % code_em, 'key_id = true']
            for lg in LANGUES:
                court = re.sub(r'^(Maillot|Tenue)\s+', '', m['nom'])
                items += ['  [item.text.%s]' % lg, '  name = %s' % json.dumps('Emblème ' + court if lg == 'fr' else court + ' crest', ensure_ascii=False)]
            items.append('')
            boutique += ['  [[edit.entry]]', '  item = "%s.embleme_%s"' % (MOD_ID, mid), '  price = %d' % int(m.get('prix', 1)),
                         '  currency = "tk_bb000001"', '  stock = 1', '']
    ecr = lambda rel, lignes: open(os.path.join(tmp, rel), 'w', encoding='utf-8', newline='\n').write('\n'.join(lignes) + '\n')
    ecr('content/looks/mes_maillots.toml', looks)
    ecr('content/items/mes_maillots.toml', items)
    ecr('content/images/menu/200_icon/02_icon_item/mesmaillots_icones.toml', icones)
    ecr('content/sprite_redirects/mes_maillots.toml', [
        'schema = "VRFW.sprite_redirect/1"', '', '[[VRFW.SpriteRedirect]]', 'name = "mes_maillots_icones"',
        'atlas = "#/menu/200_icon/02_icon_item/icon_item07.g4tx"',
        'own_atlas = "#/menu/200_icon/02_icon_item/mesmaillots_icones.g4tx"',
        'sprites = [%s]' % ', '.join('"%s"' % s for s in sprites)])
    ecr('addons/InazumaFantasy/content/shops/general_store.toml', boutique)
    noms = ', '.join(m['nom'] for m in projet['maillots'])
    ecr('mod.toml', [
        'id = "%s"' % MOD_ID, '# GÉNÉRÉ par l\'Atelier Maillots (AtelierMaillots) : ne pas modifier à la main.',
        'name = "Mes maillots"', 'prefix = "%s"' % MOD_ID, 'folder = "%s"' % MOD_ID, 'version = "1.0.%d"' % int(time.time() // 60 % 100000),
        'author = %s' % json.dumps(rgl.get('auteur', 'muku'), ensure_ascii=False),
        'description = %s' % json.dumps('Maillots faits avec l\'Atelier Maillots, vendus à la boutique générale d\'Inazuma Fantasy : ' + noms, ensure_ascii=False),
        'priority = 0', 'tags = ["Teams"]', 'updated = "%s"' % time.strftime('%Y-%m-%d'),
        'requires = ["VRFW>=0.3.0"]', 'optional = ["InazumaFantasy"]', 'conflicts = []'])
    ecr('text/keys.toml', ['schema = "VRFW.text_key/1"', 'default_lang = "en"', '', '[en.new]', 'mod_name = "My kits"',
                           'mod_description = %s' % json.dumps('Kits made with the kit workshop: ' + noms, ensure_ascii=False), '',
                           '[fr.new]', 'mod_name = "Mes maillots"',
                           'mod_description = %s' % json.dumps('Maillots faits avec l\'Atelier Maillots : ' + noms, ensure_ascii=False)])
    # contrôle des TOML
    import tomllib
    for f in glob.glob(os.path.join(tmp, '**', '*.toml'), recursive=True):
        tomllib.load(open(f, 'rb'))
    # installation : copie de l'ancien mod puis remplacement
    if os.path.exists(cible):
        anc = os.path.join(ICI, 'ancien_mod')
        if os.path.exists(anc):
            shutil.rmtree(anc)
        shutil.copytree(cible, anc)
        shutil.rmtree(cible)
    shutil.copytree(tmp, cible)
    shutil.rmtree(tmp)
    # activation dans enabled.toml
    en = os.path.join(mods, 'enabled.toml')
    # (22/11, 2.0.4) sans enabled.toml, VRFW charge TOUS les mods : le créer avec « MesMaillots » seul éteignait VRFW et tous
    # les autres (joueur : « tous mes mods ne seront pas chargés ») -> jamais créé, seulement complété
    s = open(en, encoding='utf-8').read() if os.path.isfile(en) else None
    if s is None:
        journal('pas de mods/enabled.toml : VRFW charge déjà tous les mods, rien à activer')
    elif ('"%s"' % MOD_ID) not in s:
        sauv = os.path.join(ICI, 'enabled_avant_atelier.toml')
        if not os.path.exists(sauv) and os.path.isfile(en):
            shutil.copy(en, sauv)
        # (21/11) liste vide -> ["MesMaillots"] (avant : « [, "MesMaillots"] », TOML invalide ; et plantage sans le fichier)
        m_ = re.search(r'enabled\s*=\s*\[(.*?)\]', s, re.S)
        if m_:
            dedans = m_.group(1).strip().rstrip(',').strip()
            s = s[:m_.start()] + 'enabled = [%s"%s"]' % (dedans + ', ' if dedans else '', MOD_ID) + s[m_.end():]
        else:
            s = s.rstrip() + ('\n' if s.strip() else '') + 'enabled = ["%s"]\n' % MOD_ID
        import tomllib as _tl
        _tl.loads(s)
        os.makedirs(mods, exist_ok=True)
        open(en, 'w', encoding='utf-8').write(s)
        journal('mod « Mes maillots » activé')
    journal('mod installé : %d maillot(s) dans %s' % (len(projet['maillots']), cible))
