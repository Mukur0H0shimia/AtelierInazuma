"""(15/11/2026) L'ATELIER MAILLOTS DANS L'ATELIER INAZUMA.

Le code de l'Atelier Maillots est COPIÉ dans moteur/maillots/ (l'original, AtelierMaillots/, n'est pas modifié) ; ses
données aussi, dans AtelierCouleurs/maillots/ (mes_maillots.json, travail/, cache_textures/, catalogue.json).
On dessine le maillot dans l'Atelier (onglet Maillots : coupe du jeu + mode dessin) ; ici :
- enregistrer : images du haut (« _20 ») et du short (« _30 ») -> travail/<id>/haut_dom_modifie.png… + réglages du maillot ;
- construire : atelier_mod.construire_mod (la même construction que l'Atelier Maillots : remplace mods/MesMaillots,
  l'ancien est gardé dans maillots/ancien_mod, active le mod dans enabled.toml).
"""
import os, json, base64, threading, time, traceback, multiprocessing
from .maillots import atelier_mod as A

ICI = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DOSSIER = os.path.join(ICI, 'maillots')
A.ICI = DOSSIER
A.REGLAGES = os.path.join(DOSSIER, 'reglages.json')
A.PROJET = os.path.join(DOSSIER, 'mes_maillots.json')
A.CATALOGUE = os.path.join(DOSSIER, 'catalogue.json')
A.TRAVAIL = os.path.join(DOSSIER, 'travail')
ORIGINE = os.path.join(os.path.dirname(ICI), 'AtelierMaillots', 'reglages.json')

_etat = {'en_cours': False, 'journal': [], 'fini': None, 'erreur': None}
_verrou = threading.Lock()


def reglages(cfg):
    """dossiers : données du jeu de l'Atelier Inazuma ; dossier mods et auteur repris de l'Atelier Maillots"""
    r = dict(A.DEFAUT)
    try:
        r.update(json.load(open(ORIGINE, encoding='utf-8')))
    except (OSError, ValueError):
        pass
    if os.path.exists(A.REGLAGES):
        r.update(json.load(open(A.REGLAGES, encoding='utf-8')))
    r['donnees'] = cfg['data_dir']
    if cfg.get('jeu_dir'):                             # (21/11) le jeu de l'Atelier (avant : chemin écrit en dur)
        r['mods'] = os.path.join(cfg['jeu_dir'], 'mods')
    return r


def catalogue(cfg):
    return A.catalogue(cfg['data_dir'], lambda *_: None)


def _png(chemin):
    return 'data:image/png;base64,' + base64.b64encode(open(chemin, 'rb').read()).decode() if chemin and os.path.exists(chemin) else None


def liste(cfg):
    cat = {k['cle']: k for k in catalogue(cfg)}
    out = []
    for m in A.charger_projet()['maillots']:
        b = cat.get(m.get('base'))
        out.append({'id': m['id'], 'nom': m['nom'], 'prix': m.get('prix'), 'base': m.get('base'), 'code': b['code'] if b else None,
                    'nom_base': b['nom'] if b else m.get('base'), 'numero': m.get('numero') or {}, 'plis': m.get('plis', 'simples'),
                    'icone': _png(m.get('icone')), 'embleme': _png(m.get('embleme')),
                    'images': {k: '/maillot_img/%s/%s' % (m['id'], os.path.basename(m[k])) for k in ('haut_dom', 'short_dom', 'haut_ext', 'short_ext')
                               if m.get(k) and os.path.exists(m[k])},
                    'accessoires': {k: dict(m[k], png='/maillot_img/%s/%s' % (m['id'], os.path.basename(m[k]['png'])))
                                    for k in ('chaussures_dom', 'gants_dom', 'chaussures_ext', 'gants_ext')
                                    if isinstance(m.get(k), dict) and os.path.exists(m[k].get('png') or '')}})
    return out


def image(id_, nom):
    f = os.path.join(A.TRAVAIL, os.path.basename(id_), os.path.basename(nom))
    return f if os.path.isfile(f) else None


def _ecrire(m, cle, data_url):
    d = os.path.join(A.TRAVAIL, m['id']); os.makedirs(d, exist_ok=True)
    f = os.path.join(d, cle + '_modifie.png')
    if os.path.exists(f):                       # version d'avant gardée (rien n'est effacé)
        os.replace(f, f[:-4] + '.avant.png')
    open(f, 'wb').write(base64.b64decode(data_url.split(',', 1)[1]))
    m[cle] = f


def enregistrer(cfg, d):
    """d = {id (vide = nouveau), nom, prix, base (clé « uni_… »), numero, plis, images {haut_dom, short_dom…: data URL},
    icone, embleme (data URL ou None = garder)}"""
    cat = {k['cle']: k for k in catalogue(cfg)}
    if d.get('base') not in cat:
        return {'ok': False, 'erreur': 'maillot de base inconnu : %s' % d.get('base')}
    nom = str(d.get('nom') or '').strip()
    if not nom:
        return {'ok': False, 'erreur': 'donne un nom au maillot'}
    p = A.charger_projet()
    ids = {m['id'] for m in p['maillots']}
    m = next((x for x in p['maillots'] if x['id'] == d.get('id')), None)
    if m is None:
        m = {'id': A.identifiant(nom, ids), 'haut_dom': None, 'short_dom': None, 'haut_ext': None, 'short_ext': None, 'icone': None, 'embleme': None}
        p['maillots'].append(m)
    m.update({'nom': nom, 'prix': int(d.get('prix') or 1), 'base': d['base'], 'plis': d.get('plis') or 'simples'})
    if isinstance(d.get('numero'), dict):
        m['numero'] = d['numero']
    for k, v in (d.get('images') or {}).items():
        if k in ('haut_dom', 'short_dom', 'haut_ext', 'short_ext') and v:
            _ecrire(m, k, v)
    for k in ('icone', 'embleme'):
        if d.get(k):
            _ecrire(m, k, d[k])
    # (15/11/2026) chaussures et gants (gardiens), domicile / extérieur : image + d'où elle vient (pour la construction)
    from . import copies_tenues as _T
    P = _T._parties(cfg['data_dir'])
    for k, v in (d.get('accessoires') or {}).items():
        if k not in ('chaussures_dom', 'gants_dom', 'chaussures_ext', 'gants_ext') or not isinstance(v, dict) or not v.get('png'):
            continue
        g = 'shoes' if k.startswith('chaussures') else 'gloves'
        if v.get('modele') not in P[g]:
            continue
        tmp = {'id': m['id']}
        _ecrire(tmp, k, v['png'])
        m[k] = {'png': tmp[k], 'bloc': v.get('bloc'), 'texture': v.get('texture'), 'modele': v['modele'], 'lignes': len(P[g][v['modele']])}
    # (16/11/2026) planches des chiffres / du nom dessinées dans l'Atelier avec une police de l'ordinateur
    # (lettres_num.png, lettres_num_msk.png, lettres_noms.png, lettres_noms_msk.png) ; une planche plus utilisée est mise
    # de côté (.avant.png), pour que la construction reprenne celle du jeu
    if isinstance(d.get('lettres_png'), dict):
        dt = A.dossier_travail(m)
        for k in ('noms', 'noms_msk', 'num', 'num_msk'):
            f = os.path.join(dt, 'lettres_%s.png' % k)
            v = d['lettres_png'].get(k)
            if isinstance(v, str) and v.startswith('data:image/png'):
                open(f, 'wb').write(base64.b64decode(v.split(',', 1)[1]))
            elif os.path.exists(f):
                os.replace(f, f[:-4] + '.avant.png')
    A.dossier_travail(m)
    A.sauver_projet(p)
    return {'ok': True, 'id': m['id']}


def supprimer(id_):
    """retiré de la liste (ses images restent dans travail/<id>)"""
    p = A.charger_projet()
    avant = len(p['maillots'])
    p['maillots'] = [m for m in p['maillots'] if m['id'] != id_]
    if len(p['maillots']) != avant:
        json.dump(p, open(A.PROJET + '.avant_suppression_%d.json' % int(time.time()), 'w', encoding='utf-8'), ensure_ascii=False, indent=2)
        A.sauver_projet(p)
    return {'ok': True}


def construire(cfg, installer=False):
    """(15/11/2026) par défaut : écrit le mod dans AtelierCouleurs/sortie/MesMaillots (« Ajouter au mod »), sans toucher au
    jeu ; « Installer » dans Mes créations le copie ensuite dans le jeu (export.installer, sauvegarde avant). installer=True :
    l'ancienne façon (remplace directement mods/MesMaillots et l'active)."""
    with _verrou:
        if _etat['en_cours']:
            return {'ok': False, 'erreur': 'construction déjà en cours'}
        _etat.update(en_cours=True, journal=[], fini=None, erreur=None)
    p = A.charger_projet()
    manque = [m['nom'] for m in p['maillots'] if not m.get('haut_dom')]
    if manque:
        _etat.update(en_cours=False, erreur='il manque le haut domicile pour : ' + ', '.join(manque))
        return {'ok': False, 'erreur': _etat['erreur']}
    rgl, cat = reglages(cfg), {k['cle']: k for k in catalogue(cfg)}

    def journal(t, *_):
        _etat['journal'].append(str(t))

    def run():
        try:
            with multiprocessing.Pool(max(1, (os.cpu_count() or 2) - 1)) as pool:
                A.construire_mod({'maillots': [dict(m) for m in p['maillots']]}, cat, rgl, pool, journal,
                                 cible=None if installer else os.path.join(cfg['outil_dir'], 'sortie', A.MOD_ID), activer=installer)
            _etat['fini'] = time.time()
        except Exception as e:
            _etat['erreur'] = str(e); journal(traceback.format_exc())
        finally:
            _etat['en_cours'] = False
    threading.Thread(target=run, daemon=True).start()
    return {'ok': True}


def etat():
    return dict(_etat, journal=_etat['journal'][-40:])
