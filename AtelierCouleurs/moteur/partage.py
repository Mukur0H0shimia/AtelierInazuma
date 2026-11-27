"""(27/11/2026, demande de muku) PARTAGER UNE CRÉATION : clic droit sur une carte de Mes créations -> « Partager » -> un
fichier « <nom>.atelier » que les autres importent dans LEUR Atelier (« Importer une création »).

Le fichier contient la RECETTE, pas le mod tout fait : les codes d'une création (c01980004, ids crc32…) sont uniques chez
celui qui l'a faite ; copiés tels quels chez un autre, ils pourraient écraser ses propres créations (bug des doubles, 3 fois).
- techniques, esprits, totems, armures, tenues, joueurs, objets : le PROJET de la création (projets/<clé>.json :
  textures retouchées en PNG, couleurs des matériaux, teintes, recette, auras, calques, champs du formulaire). Importé, il
  arrive dans « À continuer » ; « Continuer » puis « Créer » le refait chez l'autre avec SES codes ;
- maillots (Atelier Maillots, mes_maillots.json + travail/<id>/*.png) : images du maillot, numéro, plis, chaussures et gants,
  icône, emblème. Importé, c'est un nouveau maillot dans son Atelier Maillots.
Format : JSON {format, version, genre, base, nom, …}. Lu comme des DONNÉES : clés connues seulement, images PNG en data URL."""
import os, re, json, base64, datetime

FORMAT = 'atelier-inazuma-creation'
VERSION = 1
TAILLE_MAX = 300 * 1024 * 1024          # 300 Mo : un projet de technique avec calques fait 15 Mo
CLES_PROJET = ('version', 'code', 'onglet', 'nom', 'textures', 'apercu', 'vignette', 'coulMat', 'teinteSom', 'teintePtl', 'lumK',
               'recette', 'champs', 'auras', 'calques')
ONGLETS = ('techniques', 'esprits', 'totems', 'armures', 'tenues', 'personnages', 'objets', 'maillots')
ACCESSOIRES = ('chaussures_dom', 'gants_dom', 'chaussures_ext', 'gants_ext')
IMAGES_MAILLOT = ('haut_dom', 'short_dom', 'haut_ext', 'short_ext')
LETTRES = ('noms', 'noms_msk', 'num', 'num_msk')


def nom_fichier(nom):
    n = re.sub(r'[\\/:*?"<>|\x00-\x1f]+', '_', str(nom or '')).strip(' .')[:100]
    return (n or 'creation') + '.atelier'


def _png(chemin):
    return 'data:image/png;base64,' + base64.b64encode(open(chemin, 'rb').read()).decode() if chemin and os.path.isfile(chemin) else None


def _est_png(v):
    return isinstance(v, str) and v.startswith('data:image/png;base64,')


def exporter(projets_dir, exports_dir, mod, code, cle_projet, nom, champ, version_atelier, maillots=None, reglages=None):
    """-> {'ok', 'chemin'} ; maillots = module mes_maillots (pour un maillot)"""
    paquet = {'format': FORMAT, 'version': VERSION, 'atelier': version_atelier, 'date': datetime.datetime.now().isoformat(timespec='seconds'),
              'nom': str(nom or '')}
    if mod == 'MesMaillots':
        m = next((x for x in maillots.A.charger_projet()['maillots'] if str(x.get('id')) == str(code)), None) if maillots else None
        if not m:
            return {'ok': False, 'erreur': 'Maillot introuvable dans l’Atelier Maillots.'}
        paquet.update(genre='maillots', base=m.get('base'), nom=m.get('nom') or nom,
                      maillot={'prix': m.get('prix'), 'numero': m.get('numero') or {}, 'plis': m.get('plis') or 'simples',
                               'images': {k: _png(m.get(k)) for k in IMAGES_MAILLOT if _png(m.get(k))},
                               'icone': _png(m.get('icone')), 'embleme': _png(m.get('embleme')),
                               # planches des chiffres / du nom dessinées avec une police de l'ordinateur (pas forcément chez l'autre)
                               'lettres_png': {k: _png(os.path.join(maillots.A.dossier_travail(m), 'lettres_%s.png' % k)) for k in LETTRES
                                               if _png(os.path.join(maillots.A.dossier_travail(m), 'lettres_%s.png' % k))},
                               'accessoires': {k: {'png': _png(m[k].get('png')), 'bloc': m[k].get('bloc'), 'texture': m[k].get('texture'),
                                                   'modele': m[k].get('modele')}
                                               for k in ACCESSOIRES if isinstance(m.get(k), dict) and _png(m[k].get('png'))}})
    else:
        f = os.path.join(projets_dir, re.sub(r'[^\w.-]', '_', str(cle_projet or '')) + '.json')
        if not cle_projet or not os.path.isfile(f):
            return {'ok': False, 'erreur': 'Le projet de cette création est introuvable : ouvre-la avec « Modifier », change une couleur '
                                         '(le projet se refait tout seul), puis partage-la.'}
        e = json.load(open(f, encoding='utf-8'))
        p = {k: e[k] for k in CLES_PROJET if k in e}
        if champ:
            p.setdefault('champs', {})[champ] = paquet['nom']        # le nom de LA création dans le champ de son onglet
        paquet.update(genre=p.get('onglet') or 'techniques', base=p.get('code'), projet=p, champ=champ or None,
                      mod=mod, reglages=reglages or {})      # (27/11) stats, élément, bannière… (serveur.reglages_creation)
    os.makedirs(exports_dir, exist_ok=True)
    chemin = os.path.join(exports_dir, nom_fichier(paquet['nom']))
    with open(chemin, 'w', encoding='utf-8') as fo:
        json.dump(paquet, fo, ensure_ascii=False)
    return {'ok': True, 'chemin': chemin, 'taille': os.path.getsize(chemin)}


def _nettoyer_projet(p):
    """projet venu d'un autre ordinateur : seulement les clés connues, des types simples, des images PNG"""
    out = {k: p[k] for k in CLES_PROJET if k in p}
    out['textures'] = {str(k): v for k, v in (p.get('textures') or {}).items() if _est_png(v)} if isinstance(p.get('textures'), dict) else {}
    # (27/11, retour de muku : carte importée sans image) la vignette de l'aperçu est un JPEG (faireVignette) : gardée aussi
    if not (isinstance(out.get('vignette'), str) and re.match(r'data:image/(png|jpeg|webp);base64,', out['vignette'])):
        out['vignette'] = None
    ch = p.get('champs') if isinstance(p.get('champs'), dict) else {}
    out['champs'] = {k: v for k, v in ch.items() if re.fullmatch(r'[a-z0-9-]{1,40}', str(k)) and isinstance(v, (str, bool, int, float))
                     and len(str(v)) < 2000}
    for k in ('coulMat', 'teinteSom', 'teintePtl', 'lumK', 'auras', 'calques'):
        if not isinstance(out.get(k), dict):
            out[k] = {}
    for k in ('recette', 'apercu'):
        if not isinstance(out.get(k), list):
            out[k] = []
    return out


def lire(contenu):
    """texte du fichier -> paquet vérifié (ou exception ValueError avec un message pour l'utilisateur)"""
    if len(contenu) > TAILLE_MAX:
        raise ValueError('Fichier trop gros.')
    try:
        d = json.loads(contenu)
    except ValueError:
        raise ValueError('Ce fichier n’est pas une création de l’Atelier (.atelier).')
    if not isinstance(d, dict) or d.get('format') != FORMAT:
        raise ValueError('Ce fichier n’est pas une création de l’Atelier (.atelier).')
    if int(d.get('version') or 0) > VERSION:
        raise ValueError('Création faite avec un Atelier plus récent : mets ton Atelier à jour.')
    if d.get('genre') not in ONGLETS or not isinstance(d.get('base'), str):
        raise ValueError('Création incomplète.')
    return d


def _nom_libre(nom, pris):
    """(27/11) nom déjà pris par une création de celui qui importe : « nom (2) », sinon « Créer » referait SA création
    (un même nom garde son code)"""
    pris = {str(x).strip().lower() for x in pris or []}
    if nom.strip().lower() not in pris:
        return nom
    k = 2
    while ('%s (%d)' % (nom, k)).lower() in pris:
        k += 1
    return '%s (%d)' % (nom, k)


def importer(projets_dir, contenu, existe, maillots=None, cfg=None, noms_pris=()):
    """existe(onglet, code) -> bool (élément de départ présent chez celui qui importe) ; noms_pris = noms de ses créations ;
    -> {'ok', 'cle' | 'maillot', 'nom'}"""
    try:
        d = lire(contenu)
    except ValueError as ex:
        return {'ok': False, 'erreur': str(ex)}
    nom, base, genre = _nom_libre(str(d.get('nom') or '')[:120], noms_pris), d['base'], d['genre']
    if genre == 'maillots':
        m = d.get('maillot') if isinstance(d.get('maillot'), dict) else {}
        im = {k: v for k, v in (m.get('images') or {}).items() if k in IMAGES_MAILLOT and _est_png(v)}
        acc = {k: {'png': v.get('png'), 'bloc': v.get('bloc'), 'texture': v.get('texture'), 'modele': v.get('modele')}
               for k, v in (m.get('accessoires') or {}).items() if k in ACCESSOIRES and isinstance(v, dict) and _est_png(v.get('png'))}
        r = maillots.enregistrer(cfg, {'id': None, 'nom': nom or 'Maillot importé', 'prix': m.get('prix'), 'base': base,
                                      'numero': m.get('numero') if isinstance(m.get('numero'), dict) else {},
                                      'plis': m.get('plis') if m.get('plis') in ('simples', 'base', 'plat') else 'simples', 'images': im,
                                      'icone': m.get('icone') if _est_png(m.get('icone')) else None,
                                      'embleme': m.get('embleme') if _est_png(m.get('embleme')) else None, 'accessoires': acc,
                                      'lettres_png': {k: v for k, v in (m.get('lettres_png') or {}).items() if k in LETTRES and _est_png(v)}})
        if not r.get('ok'):
            return {'ok': False, 'erreur': 'Maillot de base absent de ton jeu (%s) : %s' % (base, r.get('erreur') or '')}
        return {'ok': True, 'genre': genre, 'maillot': r.get('id'), 'nom': nom}
    if not existe(genre, base):
        mod = base.split('~')[0] if '~' in base else None
        return {'ok': False, 'erreur': ('Cette création part de « %s », un élément du mod %s : installe ce mod, puis réessaie.' % (base, mod)) if mod
                else 'Cette création part de « %s », qui n’est pas dans ton jeu.' % base}
    p = _nettoyer_projet(d.get('projet') if isinstance(d.get('projet'), dict) else {})
    if re.fullmatch(r'[a-z0-9-]{1,40}', str(d.get('champ') or '')):
        p['champs'][d['champ']] = nom                          # nom (éventuellement « (2) ») dans le champ de son onglet
    rg = d.get('reglages') if isinstance(d.get('reglages'), dict) else {}
    if rg and str(d.get('mod') or '') in ('MesTechniques', 'MesEsprits', 'MesPersonnages', 'MesObjets', 'MesTenues'):
        p['reglages'] = {'mod': d['mod'], 'valeurs': json.loads(json.dumps(rg))}     # remis après « Créer » (app.js)
    p.update(version='1', code=base, onglet=genre, date=datetime.datetime.now().isoformat(timespec='seconds'), cree=None,
             importe={'nom': nom, 'atelier': str(d.get('atelier') or ''), 'date': str(d.get('date') or '')})
    t = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
    cle = re.sub(r'[^\w.-]', '_', '%s_%s_import_%s' % (genre, base, t))[:80]
    os.makedirs(projets_dir, exist_ok=True)
    with open(os.path.join(projets_dir, cle + '.json'), 'w', encoding='utf-8') as fo:
        json.dump(p, fo, ensure_ascii=False)
    return {'ok': True, 'genre': genre, 'cle': cle, 'nom': nom}
