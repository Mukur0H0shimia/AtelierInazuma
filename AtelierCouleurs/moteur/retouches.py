"""(15/11/2026) « METTRE DANS LE JEU » pour les tenues, armures, personnages (têtes) et objets : par REMPLACEMENT.

La texture recolorée est reconstruite (même G4TX, mêmes noms, mêmes tailles et formats, tous les niveaux de réduction)
et posée dans le mod MesRetouches au MÊME CHEMIN que celle du jeu : assets/chr/<dossier>/<fichier>.g4tx.
L'élément change donc PARTOUT dans le jeu (tous ceux qui portent cette tenue, cette armure, cette tête).

Lu (LU) avant de le faire :
- un fichier d'un mod dans assets/ au chemin d'un fichier du jeu le remplace : le mod BetterQoL pose ainsi la tête
  chr/_face/02_IE2/c02024760 (g4md, g4mg) ; Michael posé sur k002012 s'affichait à la place des 2 orbes d'Impact lumineux ;
- mods/load_order.toml (VRFW) : « top = highest priority: loads last and wins file / cell conflicts » ; un autre mod qui
  remplace le même fichier est signalé (conflit) ;
- formats des textures : BC7 (DX10, format 98) pour les têtes, armures, tenues ; DXT1 pour une partie des objets.
"""
import os, json, glob, base64, datetime, multiprocessing, struct, tempfile, shutil
from . import g4, jeu
from .g4 import images                      # bibliothèque de l'Atelier Maillots (BC7 / DXT1, PNG, G4TX)
from .export import _ecrire

MOD_ID = 'MesRetouches'


def _sortie(cfg):
    return os.path.join(cfg['outil_dir'], 'sortie', MOD_ID)


def registre(cfg):
    f = os.path.join(_sortie(cfg), 'outil_retouches.json')
    return json.load(open(f, encoding='utf-8')) if os.path.exists(f) else {}


def _sauver_registre(cfg, r):
    os.makedirs(_sortie(cfg), exist_ok=True)
    json.dump(r, open(os.path.join(_sortie(cfg), 'outil_retouches.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)


def fichier_texture(cfg, entree):
    """chemin (relatif à data/dx11) du .g4tx que l'élément utilise"""
    chemin = entree['chemin']
    md, _, tx_rel = chemin.partition('|')
    tx_rel = tx_rel.split('|')[0]                     # (3e partie éventuelle : nom imposé, voir jeu.ObjetModele)
    if tx_rel:
        return tx_rel[len('dx11/'):] if tx_rel.startswith('dx11/') else tx_rel
    if md.endswith('.g4md'):
        f = jeu.texture_de(cfg['data_dir'], md)
    else:                                          # objet .objbin : <dossier>/<nom>.g4tx
        rel = os.path.dirname(md)[len('common/'):]
        f = os.path.join(cfg['data_dir'], 'dx11', *rel.split('/'), os.path.basename(md).rsplit('.', 1)[0] + '.g4tx')
    if not f or not os.path.exists(f):
        return None
    return os.path.relpath(f, os.path.join(cfg['data_dir'], 'dx11')).replace('\\', '/')


def conflits(cfg, rel):
    """autres mods du dossier mods qui remplacent déjà ce fichier"""
    mods = os.path.join(cfg['jeu_dir'], 'mods')
    out = []
    for m in sorted(os.listdir(mods)) if os.path.isdir(mods) else []:
        if m != MOD_ID and os.path.isfile(os.path.join(mods, m, 'assets', *rel.split('/'))):
            out.append(m)
    return out


def _png(data_url, tmp):
    f = os.path.join(tmp, 'img.png')
    open(f, 'wb').write(base64.b64decode(data_url.split(',', 1)[1]))
    return images.lire_png(f)


def exporter(cfg, demande, entree):
    """demande = {cat, code, nom, textures: {nom de texture: data URL PNG}}"""
    textures = demande.get('textures') or {}
    if not textures:
        return {'ok': False, 'erreur': 'Rien n’est modifié : change d’abord des couleurs.'}
    rel = fichier_texture(cfg, entree)
    if not rel:
        return {'ok': False, 'erreur': 'texture du jeu introuvable pour ' + entree['code']}
    src = os.path.join(cfg['data_dir'], 'dx11', *rel.split('/'))
    gt = images.G4TX(open(src, 'rb').read())
    rempl, rapport, tmp = {}, [], tempfile.mkdtemp()
    try:
        with multiprocessing.Pool(max(1, (os.cpu_count() or 2) - 1)) as pool:
            for nom, url in textures.items():
                if nom not in gt.noms:
                    return {'ok': False, 'erreur': '%s n’est pas dans %s' % (nom, rel)}
                bloc = gt.blocs[gt.noms.index(nom)]
                h0, w0 = struct.unpack_from('<II', bloc, 12)
                w, h, rows = _png(url, tmp)
                while (w, h) != (w0, h0) and w >= 2 * w0 and h >= 2 * h0:      # image plus grande : réduite par moitiés
                    w, h, rows = images.moitie(w, h, rows)
                if (w, h) != (w0, h0):
                    return {'ok': False, 'erreur': '%s : %dx%d au lieu de %dx%d' % (nom, w, h, w0, h0)}
                mips = images.mips_dds(bloc)
                if bloc[84:88] == b'DX10' and struct.unpack_from('<I', bloc, 128)[0] == 98:
                    rempl[nom] = images.dds_bc7(w, h, rows, bloc[:148], mips, pool)
                elif bloc[84:88] == b'DXT1':
                    rempl[nom] = images.dds_bc1(w, h, rows, pool, mips=mips)
                else:
                    return {'ok': False, 'erreur': '%s : format de texture pas encore pris en charge' % nom}
                rapport.append('%s (%dx%d)' % (nom, w, h))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    sortie = _sortie(cfg)
    dest = os.path.join(sortie, 'assets', *rel.split('/'))
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    open(dest, 'wb').write(gt.reconstruire(rempl))
    r = registre(cfg)
    r['%s/%s' % (demande['cat'], entree['code'])] = {'cat': demande['cat'], 'code': entree['code'], 'nom': demande.get('nom') or entree.get('nom'),
                                                    'fichier': rel, 'textures': sorted(textures), 'date': datetime.datetime.now().isoformat(timespec='seconds')}
    _sauver_registre(cfg, r)
    _manifeste(sortie)
    c = conflits(cfg, rel)
    if c:
        rapport.append('ATTENTION : déjà remplacé par le mod %s (le mod le plus haut dans l’ordre gagne)' % ', '.join(c))
    return {'ok': True, 'dossier': sortie, 'fichier': 'assets/' + rel, 'rapport': rapport, 'conflits': c}


def retirer(cfg, cat, code):
    """remet l'élément comme dans le jeu : sa texture sort de MesRetouches (il faut réinstaller)"""
    r = registre(cfg)
    e = r.pop('%s/%s' % (cat, code), None)
    if not e:
        return {'ok': False, 'erreur': 'pas dans MesRetouches'}
    f = os.path.join(_sortie(cfg), 'assets', *e['fichier'].split('/'))
    if os.path.exists(f):                             # gardé hors de assets/ (rien n'est effacé ; le jeu ne le lit plus)
        g = os.path.join(_sortie(cfg), '_retires', datetime.datetime.now().strftime('%Y%m%d_%H%M%S'), *e['fichier'].split('/'))
        os.makedirs(os.path.dirname(g), exist_ok=True)
        os.replace(f, g)
    _sauver_registre(cfg, r)
    return {'ok': True}


def _manifeste(sortie):
    _ecrire(os.path.join(sortie, 'mod.toml'), '\n'.join([
        'id = "%s"' % MOD_ID, 'name = "Mes retouches"', 'prefix = "%s"' % MOD_ID, 'folder = "%s"' % MOD_ID,
        'version = "1.0.0"', 'author = "muku"',
        'description = "Tenues, armures, têtes et objets recolorés avec l\'Atelier Inazuma. Remplacement : l\'élément change partout dans le jeu."',
        'priority = 0', 'tags = ["Visual"]', 'updated = "%s"' % datetime.date.today().isoformat(),
        'requires = ["VRFW>=0.3.0"]', 'optional = []', 'conflicts = []', '']))


def contenu(cfg):
    """pour le hub (« Terminées »)"""
    return list(registre(cfg).values())
