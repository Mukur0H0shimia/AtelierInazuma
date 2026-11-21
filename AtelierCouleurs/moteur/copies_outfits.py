"""(15/11/2026) COPIE D'UNE TENUE = une NOUVELLE TENUE À ÉQUIPER (objet de la boutique) : n'importe quel joueur d'un corps
compatible peut la porter. La tenue du jeu ne change pas. Mod MesTenues.

Fait comme ChronicleDeluxe (story_outfits) et Inazuma Fantasy (Arion, styles alternatifs), LU dans leurs fichiers :
- [[VRFW.Outfit]] Name, Kit = { Uniform = "0x…" } (= crc32 de l'id du [[kit]], vérifié : « inazumafantasy_uni_arion_sherwind »
  -> 0x75D51491), IconKey, Who = { Body = [lignes de corps qui ont un maillage] } (ChronicleDeluxe : « group 1 stays out »
  quand sa ligne est vide), Price, Currency = "tk_bb000001", Text.<langue>.Name / Description ;
- [[kit]] id, from = 0x252CE113 (kit de Raimon : chaussures, gants, drapeaux, comme Inazuma Fantasy), [[kit.model]] type 0 et 1,
  fielder / keeper = le vêtement ;
- [[clothes]] model = neuf, from = le vêtement du jeu, rows = [{ upper_texture = … }, {}, …] (seule la ligne 0 porte la
  texture : les autres lignes, une par corps, prennent la même, LU dans chara_parts) ;
- icône 256 × 256 sur la planche icon_item09 (VRFW.image/1 [[texture]] atlas / name / png), comme Inazuma Fantasy.
"""
import os, json, zlib, datetime, struct, shutil, tempfile, multiprocessing, base64, tomllib
from . import copies_tenues as T, retouches
from .g4 import images
from .esprits import slug, _png
from .export import _ecrire, _q

MOD_ID = 'MesTenues'
KIT_BASE = 0x252CE113                      # kit de Raimon (IE1), comme Inazuma Fantasy pour l'uniforme d'Arion


def _sortie(cfg):
    return os.path.join(cfg['outil_dir'], 'sortie', MOD_ID)


def registre(cfg):
    f = os.path.join(_sortie(cfg), 'outil_tenues.json')
    return json.load(open(f, encoding='utf-8')) if os.path.exists(f) else {}


def vetement_de(cfg, entree):
    """(modèle de vêtement du jeu dont la ligne 0 porte cette texture, ses lignes, chemin de la texture) ou (None, None, chemin)"""
    rel = retouches.fichier_texture(cfg, entree)
    chemin = rel[len('chr/'):] if rel and rel.startswith('chr/') else rel
    P = T._parties(cfg['data_dir'])['clothes']
    for nom, l in sorted(P.items(), key=lambda a: -len(a[1])):          # le plus de corps d'abord
        if l and len(l[0]) > 1 and l[0][1] == chemin:
            return nom, l, chemin
    return None, None, chemin


def exporter(cfg, demande, entree):
    """demande = {code, nom, description, prix, textures {nom: data URL}, icone (data URL PNG, facultatif)}"""
    nom = str(demande.get('nom') or '').strip()
    if not nom:
        return {'ok': False, 'erreur': 'Donne un nom à la tenue.'}
    textures = demande.get('textures') or {}
    if not textures:
        return {'ok': False, 'erreur': 'Rien n’est modifié : recolore d’abord la tenue.'}
    source, lignes, chemin = vetement_de(cfg, entree)
    if not source:
        return {'ok': False, 'erreur': 'Ce n’est pas un vêtement que le jeu habille (chaussures, gants, peau… : « nouveau joueur »).'}
    propres = [i for i, r in enumerate(lignes) if isinstance(r[0], str)]
    infos = {c['ligne']: c for c in corps_tenue(cfg, entree)}
    corps = sorted({int(i) for i in demande['corps']}) if demande.get('corps') else propres      # (15/11/2026) choisis par muku
    if not corps:
        return {'ok': False, 'erreur': 'Choisis au moins une corpulence.'}
    emprunts = {}
    for i in corps:
        c = infos.get(i)
        if not c:
            return {'ok': False, 'erreur': 'corps %d inconnu' % i}
        if not c['propre']:
            if c['emprunt'] is None:
                return {'ok': False, 'erreur': 'Le corps « %s » n’a pas de version de cette tenue, ni de corps au même squelette à emprunter.' % c['libelle']}
            emprunts[i] = c['emprunt']
    reg = registre(cfg); cle = slug(nom)
    e = reg.get(cle) or {}
    if e and e.get('texture') != chemin:
        return {'ok': False, 'erreur': 'Le nom « %s » est déjà pris par une autre tenue : choisis-en un autre.' % nom}
    if not e:
        pris = {x['modele'] for x in reg.values()}
        tous = set(T._parties(cfg['data_dir'])['clothes'])
        e = {'modele': next('oz%06d' % n for n in range(1, 100000) if 'oz%06d' % n not in pris and 'oz%06d' % n not in tous)}
        e['kit'] = 'mestenues_uni_' + e['modele']
    m = e['modele']
    e.update(nom=nom, description=str(demande.get('description') or ''), prix=max(1, int(demande.get('prix') or 28)), source=source,
             texture=chemin, corps=corps, nom_origine=entree.get('nom'), icone='cos_mt_' + m, date=datetime.datetime.now().isoformat(timespec='seconds'))
    rows = []
    for r in lignes:
        o = {k: '_uniform/%s/%s_10.g4tx' % (m, m) for i, k in T.CLES_VET.items() if len(r) > i and r[i] == chemin}
        rows.append(o)
    e['rows'] = rows
    e['emprunts'] = {str(k): v for k, v in emprunts.items()}
    e['rows_tableau'] = _lignes_choisies(lignes, chemin, '_uniform/%s/%s_10.g4tx' % (m, m), corps, emprunts) if emprunts else None
    # texture : mêmes noms d'images (les maillages du jeu, un par corps, sont gardés)
    D = cfg['data_dir']
    gt = images.G4TX(open(os.path.join(D, 'dx11', 'chr', *chemin.split('/')), 'rb').read())
    rempl, rapport, tmp = {}, [], tempfile.mkdtemp()
    premiere = None
    try:
        with images.pool_encodage() as pool:
            for n_, url in textures.items():
                if n_ not in gt.noms:
                    return {'ok': False, 'erreur': '%s n’est pas dans %s' % (n_, chemin)}
                bloc = gt.blocs[gt.noms.index(n_)]
                h0, w0 = struct.unpack_from('<II', bloc, 12)
                w, h, rows_ = _png(url, tmp)
                if (w, h) != (w0, h0):
                    return {'ok': False, 'erreur': '%s : %dx%d au lieu de %dx%d' % (n_, w, h, w0, h0)}
                premiere = premiere or (w, h, rows_)
                if bloc[84:88] == b'DX10' and struct.unpack_from('<I', bloc, 128)[0] == 98:
                    rempl[n_] = images.dds_bc7(w, h, rows_, bloc[:148], images.mips_dds(bloc), pool)
                elif bloc[84:88] == b'DXT1':
                    rempl[n_] = images.dds_bc1(w, h, rows_, pool, mips=images.mips_dds(bloc))
                else:
                    return {'ok': False, 'erreur': '%s : format pas encore pris en charge' % n_}
                rapport.append('%s (%dx%d)' % (n_, w, h))
        sortie = _sortie(cfg)
        d = os.path.join(sortie, 'assets', 'chr', '_uniform', m); os.makedirs(d, exist_ok=True)
        open(os.path.join(d, m + '_10.g4tx'), 'wb').write(gt.reconstruire(rempl))
        # icône 256 x 256 : celle donnée, sinon la texture recolorée réduite
        di = os.path.join(sortie, 'content', 'images', 'menu', '200_icon', '02_icon_item', 'mes_tenues_icones'); os.makedirs(di, exist_ok=True)
        fi = os.path.join(di, e['icone'] + '.png')
        if demande.get('icone'):
            open(fi, 'wb').write(base64.b64decode(demande['icone'].split(',', 1)[1]))
        elif premiere:
            w, h, r_ = premiere
            while w > 256 or h > 256:
                w, h, r_ = images.moitie(w, h, r_)
            images.ecrire_png(fi, w, h, r_)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    reg[cle] = e
    os.makedirs(sortie, exist_ok=True)
    json.dump(reg, open(os.path.join(sortie, 'outil_tenues.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    ecrire(cfg, reg)
    rapport.insert(0, 'tenue « %s » : copie de %s (vêtement %s), à équiper par les corps %s, %d jetons' % (nom, entree.get('nom'), source, corps, e['prix']))
    return {'ok': True, 'dossier': sortie, 'rapport': rapport}


def ecrire(cfg, reg):
    sortie = _sortie(cfg)
    entete = '# Écrit par l\'Atelier Inazuma : tenues recolorées à équiper (réécrit à chaque export).\n'
    look, items, icones = [], [], []
    for cle, e in sorted(reg.items()):
        m = e['modele']
        if e.get('rows_tableau'):                     # des corps empruntent une version : lignes écrites en entier
            r = '\n' + ''.join('  [' + ', '.join(_q(x) if isinstance(x, str) else str(int(x)) for x in l) + '],\n' for l in e['rows_tableau'])
            look += ['# %s : copie de %s ; corps qui empruntent une version (même squelette) : %s' % (e['nom'], e['source'], e.get('emprunts')),
                     '[[clothes]]', 'model = %s' % _q(m), 'rows = [%s]' % r, '']
        else:
            r = ', '.join('{ ' + ', '.join('%s = %s' % (a, _q(b)) for a, b in x.items()) + ' }' if x else '{}' for x in e['rows'])
            look += ['# %s : copie de %s' % (e['nom'], e['source']), '[[clothes]]', 'model = %s' % _q(m), 'from = %s' % _q(e['source']), 'rows = [%s]' % r, '']
        look += [
                 '[[kit]]', 'id = %s' % _q(e['kit']), 'from = 0x%08X                          # kit de Raimon (chaussures, gants, drapeaux)' % KIT_BASE,
                 '  [[kit.model]]', '  type = 0', '  fielder = %s' % _q(m), '  keeper = %s' % _q(m),
                 '  [[kit.model]]', '  type = 1', '  fielder = %s' % _q(m), '  keeper = %s' % _q(m), '']
        txt = []
        for lang in ('es', 'en', 'fr', 'de', 'it', 'pt', 'ja', 'zh_hans', 'zh_hant'):
            txt += ['  [VRFW.Outfit.Text.%s]' % lang, '  Name = %s' % _q(e['nom']), '  Description = %s' % _q(e.get('description') or e['nom'])]
        items += ['[[VRFW.Outfit]]', 'Name = %s' % _q('mestenues_' + cle), 'Kit = { Uniform = "0x%08X" }' % zlib.crc32(e['kit'].encode()),
                  'IconKey = %s' % _q(e['icone']), 'Who = { Body = [%s] }' % ', '.join(str(i) for i in e['corps']),
                  'Price = %d' % e['prix'], 'Currency = "tk_bb000001"'] + txt + ['']
        icones += ['[[texture]]', 'atlas = "#/menu/200_icon/02_icon_item/icon_item09.g4tx"', 'name = %s' % _q(e['icone']),
                   'png = %s' % _q('mes_tenues_icones/%s.png' % e['icone']), '']
    _ecrire(os.path.join(sortie, 'content', 'looks', 'mes_tenues.toml'), 'schema = "VRFW.look/2"\n' + entete + '\n' + '\n'.join(look))
    _ecrire(os.path.join(sortie, 'content', 'items', 'mes_tenues.toml'), 'schema = "VRFW.item/2"\n' + entete + 'default_lang = "en"\n\n' + '\n'.join(items))
    _ecrire(os.path.join(sortie, 'content', 'images', 'menu', '200_icon', '02_icon_item', 'mes_tenues_icones.toml'),
            'schema = "VRFW.image/1"\n' + entete + '\n' + '\n'.join(icones))
    _ecrire(os.path.join(sortie, 'mod.toml'), '\n'.join([
        'id = "%s"' % MOD_ID, 'name = "Mes tenues"', 'prefix = "%s"' % MOD_ID, 'folder = "%s"' % MOD_ID, 'version = "1.0.0"', 'author = "muku"',
        'description = "Tenues du jeu recolorées avec l\'Atelier Inazuma, à équiper (copies : les tenues du jeu ne changent pas)."',
        'priority = 0', 'tags = ["Visual", "Items"]', 'updated = "%s"' % datetime.date.today().isoformat(),
        'requires = ["VRFW>=0.3.0"]', 'optional = []', 'conflicts = []', '']))
    for f in ('content/looks/mes_tenues.toml', 'content/items/mes_tenues.toml', 'mod.toml'):
        tomllib.load(open(os.path.join(sortie, *f.split('/')), 'rb'))


def contenu(cfg):
    return [dict(e, cle=k) for k, e in registre(cfg).items()]


# ---------------------------------------------------------------------------------------------------- (15/11/2026) CHOIX DES CORPS
# muku choisit quels corps peuvent mettre la tenue. Un corps qui a sa ligne (son maillage) dans le vêtement du jeu : rien à
# faire. Un corps sans maillage : il EMPRUNTE la ligne d'un corps au MÊME SQUELETTE (comme le jeu pour ChronicleDeluxe :
# « group 1 wears that mesh through the game's body fallback », groupe 1 et groupe 0 = squelette c000101). Lignes alors écrites
# en entier (22 colonnes, comme Inazuma Fantasy, Michael, BetterQoL) : la ligne empruntée, colonne 2 = le numéro du corps.
def corps_tenue(cfg, entree):
    source, lignes, chemin = vetement_de(cfg, entree)
    if not source:
        return []
    C = T.corps(cfg['data_dir'])
    propre = {i for i, r in enumerate(lignes) if isinstance(r[0], str)}
    out = []
    for i in sorted(k for k in C if k < 100):
        e = C[i]
        donneur = None
        if i not in propre:
            l = [j for j in propre if C.get(j, {}).get('squelette') == e['squelette']]
            donneur = max(l, key=lambda j: C[j]['nb']) if l else None
        out.append({'ligne': i, 'libelle': '%s%s' % (T.SQUELETTES.get(e['squelette'], e['squelette']), ' (ex. %s)' % e['exemple'] if e['exemple'] else ''),
                    'nb': e['nb'], 'propre': i in propre, 'emprunt': donneur})
    return out


def _lignes_choisies(lignes, chemin, nouveau, choix, emprunts):
    """lignes complètes (22 colonnes) : celles du jeu (texture remplacée) + les lignes empruntées pour les corps choisis"""
    n = max([len(lignes) - 1] + list(choix)) + 1
    out = []
    for i in range(n):
        if i in emprunts:
            r = list(lignes[emprunts[i]]); r[2] = i
        elif i < len(lignes):
            r = list(lignes[i])
        else:
            r = [0] * 22; r[2] = i                       # corps non choisi, au-delà des lignes du jeu : ligne vide
        out.append([nouveau if x == chemin else x for x in r])
    if out and not isinstance(out[0][1], str):          # la ligne 0 porte la texture (les autres : 0 = la même)
        out[0][1] = nouveau
    return out
