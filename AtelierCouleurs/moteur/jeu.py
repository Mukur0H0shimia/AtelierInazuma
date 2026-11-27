"""(15/11/2026) TOUT LE JEU dans l'Atelier : maillots, tenues, armures, personnages (têtes), objets.

Chaque élément s'ouvre comme un esprit guerrier (même chemin : textures, vue 3D, mode dessin, projet sauvegardé).
Fichiers du jeu (LU, data/) :
- common/chr/_armd/<ka…>/<code>.g4md + .g4mg, textures dx11/chr/_armd/<code>/<code>_10.g4tx ;
- common/chr/_uniform/<dossier>/<dossier>.g4md (ou <dossier sans 2 chiffres><NN>.g4md : une version par corpulence),
  textures dx11/chr/_uniform/<dossier>/*.g4tx ;
- common/chr/_face/<série>/<code>/<code>.g4md, textures dx11/chr/_face/<série>/<code>/<code>.g4tx ;
- common/chr/_item/<code>/<code>.objbin (+ .g4pkm), comme les effets.
Noms : maillots = item_text (ITEM_FASHION_INFO « uni_<code> », comme l'Atelier Maillots) ; personnages = chara_base
(v[1] code, v[3] id du nom, v[6] id du modèle) -> chara_model (v[0] id du modèle, v[10] chemin de la tête) -> chara_text.
Le reste n'a pas de nom lisible trouvé : le code est montré.
"""
from moteur import langue as _langue  # noqa: E402  (FR / EN)
import os, glob, json, re
from . import g4, cfgbin
from .personnages import _japonais, _dernier


class ObjetModele(g4.ObjetEffet):
    """un modèle .g4md (+ .g4mg) du jeu, lu comme un objet d'effet (pièces, matériaux, textures, géométrie).
    chemin « <modèle>.g4md|<texture>.g4tx » : maillot = une COUPE (le modèle) + SA texture, rangée dans le dossier de la
    coupe (LU : ses images portent déjà les noms du modèle, ex. u030701_10.g4tx contient « u000501_20 »)"""
    def __init__(self, data_dir, chemin_md):
        chemin_md, _, tx_rel = chemin_md.partition('|')
        tx_rel, _, nom_force = tx_rel.partition('|')        # 3e partie : nom imposé (même texture dans deux dossiers)
        rel = chemin_md.replace('\\', '/')
        if rel.startswith('common/'):
            rel = rel[len('common/'):]
        self.nom = nom_md = os.path.basename(rel).rsplit('.', 1)[0]
        if tx_rel:                                  # maillot : nom = son code (dossier du cache à lui) ; tenue : nom du fichier
            b = os.path.basename(tx_rel).rsplit('.', 1)[0]
            self.nom = nom_force or (b.rsplit('_', 1)[0] if b.endswith('_10') else b)
        self.data_dir = data_dir
        self.dossier_rel = os.path.dirname(rel)
        self.common = os.path.join(data_dir, 'common', *self.dossier_rel.split('/'))
        self.dx11 = os.path.join(data_dir, 'dx11', *self.dossier_rel.split('/'))
        self.pk = open(os.path.join(self.common, nom_md + '.g4md'), 'rb').read()
        self.mg = open(os.path.join(self.common, nom_md + '.g4mg'), 'rb').read()
        self.tx = None
        f = os.path.join(data_dir, *tx_rel.split('/')) if tx_rel else texture_de(data_dir, chemin_md)
        if f:
            self.tx = open(f, 'rb').read()
        self._lire()
        self.particules = {'emetteurs': []}
        self.lumieres = None


def texture_de(data_dir, chemin_md):
    """fichier .g4tx principal d'un modèle : <dossier>.g4tx ou <dossier>_10.g4tx (domicile pour les maillots), sinon le 1er"""
    rel = os.path.dirname(chemin_md.replace('\\', '/'))
    if rel.startswith('common/'):
        rel = rel[len('common/'):]
    d = os.path.join(data_dir, 'dx11', *rel.split('/'))
    dossier = os.path.basename(d)
    for n in (dossier + '.g4tx', dossier + '_10.g4tx'):
        if os.path.exists(os.path.join(d, n)):
            return os.path.join(d, n)
    l = sorted(glob.glob(os.path.join(d, '*.g4tx')))
    return l[0] if l else None


def _modele_uniforme(c, dossier):
    """modèle d'un dossier _uniform : <dossier>.g4md, sinon la version corpulence 1, sinon le 1er"""
    d = os.path.join(c, 'chr', '_uniform', dossier)
    for n in (dossier + '.g4md', dossier[:-2] + '01.g4md'):
        if os.path.exists(os.path.join(d, n)):
            return n
    l = sorted(f for f in os.listdir(d) if f.endswith('.g4md'))
    return l[0] if l else None


# (28/11) « e… » = CHAUSSURES des tenues (chara_parts : les 36 « e » sont dans shoes ; avant : « Tenue »)
GENRES_TENUE = (('sk', 'Peau (bras, mains)'), ('sh', 'Tenue'), ('s', 'Chaussures'), ('u', 'Tenue'), ('e', 'Chaussures'), ('f', 'Tenue'),
                ('g', 'Gants'), ('o', 'Tenue'), ('m', 'Manches'), ('n', 'Numéro'))


def noms_armures(data_dir, cache_dir):
    """(28/11, muku : « les armures n'ont pas de nom simple ») {ka…: « Armure · <esprit> »}. LU dans les tables :
    chara_model v[5] = crc32(armure) (vêtement de la forme en armure), v[0] = id du modèle -> chara_base v[6] = ce modèle,
    v[0] = id du personnage en armure, v[9] = personnage d'origine -> chara_param v[1] = ce personnage, v[0] = sa fiche ->
    aura_skill_config v[13] = cette fiche, v[7] = crc32(esprit). 87 armures sur 89 ; sinon le porteur (chara_text)."""
    import zlib
    from . import personnages
    c = os.path.join(data_dir, 'common')
    U = lambda x: x & 0xFFFFFFFF
    L = lambda motif: cfgbin.lire(open(_dernier(os.path.join(c, 'gamedata', *motif.split('/'))), 'rb').read())
    armures = {zlib.crc32(a.encode()): a for a in os.listdir(os.path.join(c, 'chr', '_armd'))}
    esprit = {zlib.crc32(p['code'].encode()): p['nom'] for p in personnages.construire(data_dir, cache_dir)
              if p.get('nom') and p['nom'] != p['code']}
    modele = {}
    for k, v in L('character/chara_model_1*.cfg.bin'):
        if len(v) > 5 and isinstance(v[0], int) and isinstance(v[5], int) and U(v[5]) in armures:
            modele.setdefault(U(v[0]), armures[U(v[5])])
    perso, porteur, id_nom = {}, {}, {}
    for k, v in L('character/chara_base_*.cfg.bin'):
        if len(v) > 3 and isinstance(v[0], int) and isinstance(v[3], int):
            id_nom.setdefault(U(v[0]), U(v[3]))
        if len(v) > 9 and isinstance(v[0], int) and isinstance(v[6], int) and U(v[6]) in modele:
            perso[U(v[0])] = modele[U(v[6])]
            porteur.setdefault(modele[U(v[6])], []).extend(U(x) for x in (v[9], v[0]) if isinstance(x, int))
    fiche = {}
    for k, v in L('character/chara_param_1*.cfg.bin'):
        if len(v) > 1 and isinstance(v[0], int) and isinstance(v[1], int) and U(v[1]) in perso:
            fiche[U(v[0])] = perso[U(v[1])]
    trouve = {}
    for k, v in L('skill/aura_skill_config_*.cfg.bin'):
        if len(v) > 13 and isinstance(v[13], int) and isinstance(v[7], int) and U(v[13]) in fiche and U(v[7]) in esprit:
            trouve.setdefault(fiche[U(v[13])], esprit[U(v[7])])
    textes = {}
    for k, v in cfgbin.lire(open(os.path.join(c, 'text', _langue.code(), 'chara_text.cfg.bin'), 'rb').read()):
        if len(v) > 5 and isinstance(v[0], int) and v[1] == 0 and isinstance(v[5], str):
            textes.setdefault(U(v[0]), v[5])
    out, vus = {}, {}
    for code in sorted(armures.values()):
        n = trouve.get(code)
        for p in ([] if n else porteur.get(code, [])):          # porteur d'origine, puis le personnage en armure
            t = textes.get(id_nom.get(p))
            if t and not _japonais(t):
                n = t; break
        if n:
            vus[n] = vus.get(n, 0) + 1
            out[code] = 'Armure · %s%s' % (n, ' %d' % vus[n] if vus[n] > 1 else '')
    return out


def _nommer_armures(out, data_dir, cache_dir):
    try:
        noms = noms_armures(data_dir, cache_dir)
    except Exception as ex:                          # (sans noms, la liste reste utilisable)
        print('noms des armures :', ex); return False
    for x in out.get('armures', []):
        if x.get('code') in noms:
            x['nom'] = noms[x['code']]
    return True


COULEURS_MOTS = {'fr': {'noir': 'noir', 'blanc': 'blanc', 'gris': 'gris', 'rouge': 'rouge', 'orange': 'orange', 'jaune': 'jaune', 'vert': 'vert',
                        'cyan': 'turquoise', 'bleu': 'bleu', 'violet': 'violet', 'rose': 'rose', 'et': 'et'},
                 'en': {'noir': 'black', 'blanc': 'white', 'gris': 'grey', 'rouge': 'red', 'orange': 'orange', 'jaune': 'yellow', 'vert': 'green',
                        'cyan': 'turquoise', 'bleu': 'blue', 'violet': 'purple', 'rose': 'pink', 'et': 'and'},
                 'es': {'noir': 'negro', 'blanc': 'blanco', 'gris': 'gris', 'rouge': 'rojo', 'orange': 'naranja', 'jaune': 'amarillo', 'vert': 'verde',
                        'cyan': 'turquesa', 'bleu': 'azul', 'violet': 'morado', 'rose': 'rosa', 'et': 'y'}}


def _nom_couleur(r, g, b):
    import colorsys
    h, s, v = colorsys.rgb_to_hsv(r / 255, g / 255, b / 255)
    if v < 0.18:
        return 'noir'
    if s < 0.18:
        return 'blanc' if v > 0.78 else 'gris'
    h *= 360
    for lim, n in ((12, 'rouge'), (40, 'orange'), (68, 'jaune'), (165, 'vert'), (195, 'cyan'), (255, 'bleu'), (290, 'violet'), (340, 'rose'), (361, 'rouge')):
        if h < lim:
            return n


def couleurs_tenues(data_dir, cache_dir, tenues):
    """(28/11, muku : « dans les tenues des trucs ne sont pas simplifiés ») tenues sans porteur connu (1 459 : kits d'équipes,
    chaussures, gants… que personne ne porte dans chara_model) -> leurs 2 couleurs principales, lues dans l'image de couleurs
    de leur texture. {code: ['rouge', 'blanc']} ; gardé dans cache/couleurs_tenues.json (le même pour toutes les langues)"""
    import collections
    racine = os.path.dirname(cache_dir) if os.path.basename(cache_dir) in COULEURS_MOTS else cache_dir
    f = os.path.join(racine, 'couleurs_tenues.json')
    deja = json.load(open(f, encoding='utf-8')) if os.path.exists(f) else {}
    manque = [x for x in tenues if x['code'] not in deja and '|' in x.get('chemin', '')]
    if manque:
        print('couleurs des tenues sans nom : %d (une seule fois)…' % len(manque))
    for x in manque:
        try:
            gt = g4.images.G4TX(open(os.path.join(data_dir, *x['chemin'].split('|')[1].split('/')), 'rb').read())
            i = next((k for k, n in enumerate(gt.noms) if not any(n.endswith(s) for s in ('line', 'msk', 'spm', 'nrm', 'sp', 'bc'))), 0)
            w, h, rows = g4.decoder_texture(gt.blocs[i])
            c = collections.Counter()
            for y in range(0, h, max(1, h // 64)):
                row = rows[y]
                for xx in range(0, w, max(1, w // 64)):
                    r, g_, b, a = row[xx * 4:xx * 4 + 4]
                    if a > 40:
                        c[_nom_couleur(r, g_, b)] += 1
            tot = sum(c.values()) or 1
            deja[x['code']] = [n for n, k in c.most_common(3) if k / tot > 0.12][:2]
        except Exception:
            deja[x['code']] = []
    if manque:
        json.dump(deja, open(f, 'w', encoding='utf-8'), ensure_ascii=False, indent=0)
    return deja


def _nommer_tenues(out, data_dir, cache_dir):
    """tenues encore nommées par leur code (« Chaussures e000401_10 ») -> « Chaussures · blanc et gris » (numérotées si répétées)"""
    sans = [x for x in out.get('tenues', []) if ' · ' not in (x.get('nom') or '') and '|' in x.get('chemin', '')
            and x.get('genre') and (x.get('nom') or '').startswith(x['genre'] + ' ')]
    try:
        coul = couleurs_tenues(data_dir, cache_dir, sans)
    except Exception as ex:
        print('couleurs des tenues :', ex); return False
    mots = COULEURS_MOTS.get(_langue.code(), COULEURS_MOTS['fr'])
    vus = {}
    for x in sans:
        l = [mots.get(c, c) for c in coul.get(x['code']) or []]
        if not l:
            continue
        n = '%s · %s' % (x['genre'], (' %s ' % mots['et']).join(l))
        vus[n] = vus.get(n, 0) + 1
        x['nom'] = n + (' %d' % vus[n] if vus[n] > 1 else '')
    return True


def nommer_accessoires(liste, data_dir, cache_dir):
    """(28/11) accessoires de l'onglet Tenues (« Accessoire it000101 ») : nommés par leurs couleurs, comme les tenues"""
    pseudo = []
    for x in liste:
        f = texture_de(data_dir, x.get('chemin', '').split('|')[0])
        if f:
            pseudo.append({'code': 'acc:' + x['code'], 'chemin': 'x|' + os.path.relpath(f, data_dir).replace(os.sep, '/'), 'x': x})
    try:
        coul = couleurs_tenues(data_dir, cache_dir, pseudo)
    except Exception as ex:
        print('couleurs des accessoires :', ex); return
    mots = COULEURS_MOTS.get(_langue.code(), COULEURS_MOTS['fr']); vus = {}
    for p in pseudo:
        l = [mots.get(c, c) for c in coul.get(p['code']) or []]
        if l:
            n = '%s · %s' % (p['x'].get('genre') or 'Accessoire', (' %s ' % mots['et']).join(l))
            vus[n] = vus.get(n, 0) + 1
            p['x']['nom'] = n + (' %d' % vus[n] if vus[n] > 1 else '')


def construire(data_dir, cache_dir, catalogue_maillots=None):
    """{catégorie: [{code, nom, genre, chemin}]} ; gardé dans cache/index_jeu.json"""
    f_cache = os.path.join(cache_dir, 'index_jeu.json')
    if os.path.exists(f_cache):
        out = json.load(open(f_cache, encoding='utf-8'))
        for x in out.get('tenues', []):          # (28/11) index déjà en cache : chaussures « e… » rangées sous « Tenue »
            if str(x.get('dossier', '')).startswith('e') and x.get('genre') == 'Tenue':
                x['genre'] = 'Chaussures'; x['nom'] = re.sub(r'^Tenue(?= )', 'Chaussures', x.get('nom') or '')
        if not out.get('armures_nommees'):         # (28/11) cache d'avant les noms d'armures
            if _nommer_armures(out, data_dir, cache_dir):
                out['armures_nommees'] = True
                json.dump(out, open(f_cache, 'w', encoding='utf-8'), ensure_ascii=False, indent=0)
        if not out.get('tenues_couleurs'):         # (28/11) cache d'avant les noms par couleurs
            if _nommer_tenues(out, data_dir, cache_dir):
                out['tenues_couleurs'] = True
                json.dump(out, open(f_cache, 'w', encoding='utf-8'), ensure_ascii=False, indent=0)
        return out
    c = os.path.join(data_dir, 'common')
    out = {'maillots': [], 'tenues': [], 'armures': [], 'personnages': [], 'objets': []}
    # --- maillots (noms de l'Atelier Maillots : item_text) et tenues
    # maillots (ceux de l'Atelier Maillots, item_text « uni_<code> ») : coupe = dossier de leur texture, + texture domicile
    vus = set()
    for k in catalogue_maillots or []:
        t = k['tex10'].replace('\\', '/'); i = t.find('/dx11/')
        dossier = os.path.basename(os.path.dirname(t))
        md = _modele_uniforme(c, dossier) if i >= 0 and os.path.isdir(os.path.join(c, 'chr', '_uniform', dossier)) else None
        if not md:
            continue
        vus.add(dossier)
        t20 = (k.get('tex20') or '').replace(chr(92), '/'); j = t20.find('/dx11/')
        out['maillots'].append({'code': k['code'], 'nom': k['nom'], 'genre': 'Maillot', 'cle_maillot': k['cle'],
                                'chemin': 'common/chr/_uniform/%s/%s|%s' % (dossier, md, t[i + 1:]),
                                'tex20': t20[j + 1:] if j >= 0 else None})          # (15/11/2026) côté extérieur
    # (15/11/2026) TENUES : UNE PAR TEXTURE (avant : une par dossier, soit 826 au lieu de 2 651 ; un dossier de coupe range
    # les tenues de beaucoup d'équipes, jusqu'à 271). Modèle = celui du dossier ; nom = qui la porte (joueurs d'abord).
    kits = {k['tex10'].replace('\\', '/').split('/dx11/')[-1] for k in catalogue_maillots or []} | \
           {(k.get('tex20') or '').replace('\\', '/').split('/dx11/')[-1] for k in catalogue_maillots or []}
    try:
        from .copies_tenues import noms_par_texture
        porte = noms_par_texture(data_dir)
    except Exception as ex:                         # (sans noms, la liste reste utilisable)
        print('noms des tenues :', ex); porte = {}
    out['alias_tenues'] = {}; deja = set()
    for dossier in sorted(os.listdir(os.path.join(c, 'chr', '_uniform'))):
        md = _modele_uniforme(c, dossier) if os.path.isdir(os.path.join(c, 'chr', '_uniform', dossier)) else None
        if not md:
            continue
        genre = next((g for p, g in GENRES_TENUE if dossier.startswith(p)), 'Tenue')
        principale = texture_de(data_dir, 'common/chr/_uniform/%s/%s' % (dossier, md))
        for f in sorted(glob.glob(os.path.join(data_dir, 'dx11', 'chr', '_uniform', dossier, '*.g4tx'))):
            base = os.path.basename(f)[:-5]
            rel = 'dx11/chr/_uniform/%s/%s.g4tx' % (dossier, base)
            if rel[len('dx11/'):] in kits or rel in kits:   # maillot de la boutique : dans « maillots »
                continue
            qui = porte.get('_uniform/%s/%s.g4tx' % (dossier, base)) or []
            code = base if base not in deja else '%s~%s' % (base, dossier)    # même nom de texture dans 2 dossiers
            deja.add(base)
            nom = '%s · %s%s' % (genre, qui[0], ' + %d' % (len(qui) - 1) if len(qui) > 1 else '') if qui else '%s %s' % (genre, base)
            out['tenues'].append({'code': code, 'nom': nom, 'genre': genre, 'dossier': dossier,
                                  'chemin': 'common/chr/_uniform/%s/%s|%s' % (dossier, md, rel) + ('|' + code.replace('~', '_') if code != base else '')})
            if principale and os.path.samefile(principale, f):
                out['alias_tenues'][dossier] = code          # anciens projets (une tenue = un dossier) : même texture
    # --- armures
    for code in sorted(os.listdir(os.path.join(c, 'chr', '_armd'))):
        chemin = 'common/chr/_armd/%s/%s.g4md' % (code, code)
        if os.path.exists(os.path.join(data_dir, chemin)) and texture_de(data_dir, chemin):
            out['armures'].append({'code': code, 'nom': 'Armure ' + code, 'genre': 'Armure', 'chemin': chemin})
    out['armures_nommees'] = _nommer_armures(out, data_dir, cache_dir)
    out['tenues_couleurs'] = _nommer_tenues(out, data_dir, cache_dir)
    # --- personnages : tête -> nom du personnage
    noms = {}
    for crc, v in cfgbin.lire(open(os.path.join(c, 'text', _langue.code(), 'chara_text.cfg.bin'), 'rb').read()):
        if len(v) > 5 and isinstance(v[0], int) and v[1] == 0 and isinstance(v[5], str):
            noms.setdefault(v[0] & 0xFFFFFFFF, v[5])
    modele_nom = {}
    for crc, v in cfgbin.lire(open(_dernier(os.path.join(c, 'gamedata', 'character', 'chara_base_*.cfg.bin')), 'rb').read()):
        if len(v) > 6 and isinstance(v[3], int) and isinstance(v[6], int):
            n = noms.get(v[3] & 0xFFFFFFFF)
            if n and not _japonais(n):
                modele_nom.setdefault(v[6] & 0xFFFFFFFF, n)
    tete_nom = {}
    for f in sorted(glob.glob(os.path.join(c, 'gamedata', 'character', 'chara_model_1*.cfg.bin'))):
        for crc, v in cfgbin.lire(open(f, 'rb').read()):
            if len(v) > 10 and isinstance(v[0], int) and isinstance(v[10], str):
                n = modele_nom.get(v[0] & 0xFFFFFFFF)
                if n:
                    tete_nom.setdefault(v[10].replace('\\', '/').lstrip('/'), n)
    for serie in sorted(os.listdir(os.path.join(c, 'chr', '_face'))):
        ds = os.path.join(c, 'chr', '_face', serie)
        if not os.path.isdir(ds):
            continue
        lib = re.sub(r'^\d+_', '', serie).replace('_', ' ')
        for code in sorted(os.listdir(ds)):
            chemin = 'common/chr/_face/%s/%s/%s.g4md' % (serie, code, code)
            if not os.path.exists(os.path.join(data_dir, chemin)) or not texture_de(data_dir, chemin):
                continue
            n = tete_nom.get('_face/%s/%s/%s.g4md' % (serie, code, code))
            out['personnages'].append({'code': code, 'nom': n or code, 'genre': 'Personnage · ' + lib, 'chemin': chemin})
    # --- objets (comme les effets : .objbin)
    for dossier, genre in (('_item', 'Objet'), ('_animal', 'Animal')):
        for code in sorted(os.listdir(os.path.join(c, 'chr', dossier))):
            chemin = 'common/chr/%s/%s/%s.objbin' % (dossier, code, code)
            md = 'common/chr/%s/%s/%s.g4md' % (dossier, code, code)
            if os.path.exists(os.path.join(data_dir, chemin)) and os.path.exists(os.path.join(data_dir, chemin[:-7] + '.g4pkm')):
                out['objets'].append({'code': code, 'nom': '%s %s' % (genre, code), 'genre': genre, 'chemin': chemin})
            elif os.path.exists(os.path.join(data_dir, md)) and texture_de(data_dir, md):     # (15/11/2026) accessoires : .g4md seul
                out['objets'].append({'code': code, 'nom': '%s %s' % (genre, code), 'genre': genre, 'chemin': md})
    json.dump(out, open(f_cache, 'w', encoding='utf-8'), ensure_ascii=False, indent=0)
    return out
