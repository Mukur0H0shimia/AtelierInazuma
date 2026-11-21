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


GENRES_TENUE = (('sk', 'Peau (bras, mains)'), ('sh', 'Tenue'), ('s', 'Chaussures'), ('u', 'Tenue'), ('e', 'Tenue'), ('f', 'Tenue'),
                ('g', 'Gants'), ('o', 'Tenue'), ('m', 'Manches'), ('n', 'Numéro'))


def construire(data_dir, cache_dir, catalogue_maillots=None):
    """{catégorie: [{code, nom, genre, chemin}]} ; gardé dans cache/index_jeu.json"""
    f_cache = os.path.join(cache_dir, 'index_jeu.json')
    if os.path.exists(f_cache):
        return json.load(open(f_cache, encoding='utf-8'))
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
