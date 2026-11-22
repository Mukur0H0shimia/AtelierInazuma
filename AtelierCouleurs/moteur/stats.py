"""(22/11/2026, idée de muku : « d'abord le visuel, ensuite les stats dans un menu à part : En attente de stats »)
Valeurs des créations (techniques, esprits guerriers, joueurs), réglées APRÈS le visuel, gardées dans le registre de
chaque création (clé « stats » ; {} = « garder les valeurs de l'original ») et écrites dans le mod par son écrivain.

Clés VRFW (LUES dans des mods qui marchent, jamais devinées) :
- technique (`[[technique]]`, ChronicleDeluxe final_phoenix, IECross, InazumaFantasy) : power_min, power_max, tp,
  element ("fire" …), users (+ partners = [] : n'importe quel coéquipier), growth (0-7) ;
- esprit guerrier (`[[aura_command]] cells`, colonnes de AURA_CMD_INFO lues dans VRFW : power_min, power_max, element ;
  « cells » déjà utilisé par l'Atelier et le mod Mukuro) ; élément en nombre (1 Air … 5 Néant, comme skill_config) ;
- joueur (mod Mukuro, CONFIRMÉ en jeu ; CharacterReforged) : position / element sur `[[character]]`, sub_position et
  stats = { kick, control, technique, pressure, physical, intelligence, agility, freedom } sur `[[character.cards]]`.
Valeurs du jeu (pour partir de l'original) : skill_config (RDBN, colonnes trouvées par crc32 de leur nom) et
aura_skill_config (T2B : 4 power_min, 5 power_max, 8 element).
Seules les valeurs CHANGÉES par rapport à l'original sont écrites.
"""
import glob, os, struct, zlib

ELEMENTS = {1: 'wind', 2: 'forest', 3: 'fire', 4: 'mountain', 5: 'void'}
NUM_ELEMENT = {v: k for k, v in ELEMENTS.items()}
CHOIX_ELEMENT = [['wind', 'Air'], ['forest', 'Forêt'], ['fire', 'Feu'], ['mountain', 'Montagne'], ['void', 'Néant']]
CHOIX_POSTE = [['fw', 'Attaquant'], ['mf', 'Milieu'], ['df', 'Défenseur'], ['gk', 'Gardien']]
STATS_JOUEUR = [('kick', 'Frappe'), ('control', 'Contrôle'), ('technique', 'Technique'), ('pressure', 'Pression'),
                ('physical', 'Physique'), ('intelligence', 'Intelligence'), ('agility', 'Agilité'), ('freedom', 'Liberté')]

CHAMPS = {
    'technique': [
        {'cle': 'power_min', 'nom': 'Puissance au niveau 1', 'type': 'nombre', 'min': 0, 'max': 32767},
        {'cle': 'power_max', 'nom': 'Puissance au niveau max', 'type': 'nombre', 'min': 0, 'max': 32767},
        {'cle': 'tp', 'nom': 'Coût en PT', 'type': 'nombre', 'min': 0, 'max': 255},
        {'cle': 'element', 'nom': 'Élément', 'type': 'choix', 'choix': CHOIX_ELEMENT},
        {'cle': 'users', 'nom': 'Joueurs pour la lancer', 'type': 'nombre', 'min': 1, 'max': 4,
         'aide': 'Plus de 1 : n\'importe quels coéquipiers'},
        {'cle': 'growth', 'nom': 'Courbe de progression (0-7)', 'type': 'nombre', 'min': 0, 'max': 7}],
    'esprit': [
        {'cle': 'power_min', 'nom': 'Puissance au niveau 1', 'type': 'nombre', 'min': 0, 'max': 32767},
        {'cle': 'power_max', 'nom': 'Puissance au niveau max', 'type': 'nombre', 'min': 0, 'max': 32767},
        {'cle': 'element', 'nom': 'Élément', 'type': 'choix', 'choix': CHOIX_ELEMENT}],
    'personnages': [
        {'cle': 'position', 'nom': 'Poste', 'type': 'choix', 'choix': CHOIX_POSTE, 'vide': True},
        {'cle': 'sub_position', 'nom': 'Poste secondaire', 'type': 'choix', 'choix': CHOIX_POSTE, 'vide': True},
        {'cle': 'element', 'nom': 'Élément', 'type': 'choix', 'choix': CHOIX_ELEMENT, 'vide': True}]
    + [{'cle': 'stats.' + k, 'nom': n, 'type': 'nombre', 'min': 0, 'max': 999, 'vide': True, 'groupe': 'stats'} for k, n in STATS_JOUEUR],
}


# ------------------------------------------------------------------ valeurs du jeu
def _rdbn_lignes(b, nom_liste, colonnes):
    """table RDBN : {valeur de la 1re colonne demandée: {colonne: valeur}} (colonnes = noms ; trouvées par crc32)"""
    assert b[:4] == b'RDBN'
    h = struct.unpack_from('<13H', b, 0x26)
    fin_types, fin_cols, nlistes, debut = h[1], h[3], h[4], h[8]
    D = 0x50 + 4 * debut
    for i in range(nlistes):
        o = 0x50 + 4 * fin_cols + 0x20 * i
        typ, _, deb, lg, n, crc = struct.unpack_from('<HHIIII', b, o)
        if crc != zlib.crc32(nom_liste.encode()):
            continue
        ot = 0x50 + 0x20 * typ
        c0, nc = struct.unpack_from('<HH', b, ot + 8)
        cols = {}
        for k in range(c0, c0 + nc):
            ccrc, ty, _, taille, place = struct.unpack_from('<IHHII', b, 0x50 + 4 * fin_types + 0x20 * k)
            cols[ccrc] = (taille, place)
        out = {}
        for r in range(n):
            ligne = b[D + deb + r * lg: D + deb + (r + 1) * lg]
            v = {}
            for nom in colonnes:
                t, p = cols[zlib.crc32(nom.encode())]
                v[nom] = int.from_bytes(ligne[p:p + t], 'little', signed=t == 2)
            out[v[colonnes[0]]] = v
        return out
    return {}


def _dernier(motif):
    f = sorted(glob.glob(motif))
    return f[-1] if f else None


def jeu_technique(data_dir, code):
    f = _dernier(os.path.join(data_dir, 'common', 'gamedata', 'skill', 'skill_config_*.cfg.bin'))
    if not f:
        return {}
    t = _rdbn_lignes(open(f, 'rb').read(), 'm_skillInfoList',
                     ['skillID', 'power_min', 'power_max', 'element', 'growthType', 'consumeTp', 'partnerType'])
    r = t.get(zlib.crc32(str(code).encode()))
    if not r:
        return {}
    return {'power_min': r['power_min'], 'power_max': r['power_max'], 'tp': r['consumeTp'],
            'element': ELEMENTS.get(r['element'], ''), 'users': max(1, r['partnerType']), 'growth': r['growthType']}


def jeu_esprit(data_dir, technique):
    """technique d'invocation de l'esprit d'origine (wko00010…) -> sa ligne AURA_CMD_INFO"""
    from . import cfgbin
    f = _dernier(os.path.join(data_dir, 'common', 'gamedata', 'skill', 'aura_skill_config_*.cfg.bin'))
    if not f:
        return {}
    for _, v in cfgbin.lire(open(f, 'rb').read()):
        if len(v) >= 9 and v[1] == technique:
            return {'power_min': v[4], 'power_max': v[5], 'element': ELEMENTS.get(v[8], '')}
    return {}


# ------------------------------------------------------------------ écriture (seulement ce qui change)
def _changes(stats, jeu):
    return {k: v for k, v in (stats or {}).items() if v not in (None, '') and (k not in jeu or jeu[k] != v)}


def lignes_technique(stats, jeu):
    c = _changes(stats, jeu)
    out = []
    for k in ('power_min', 'power_max', 'tp', 'growth'):
        if k in c:
            out.append('%s = %d' % (k, int(c[k])))
    if c.get('element') in NUM_ELEMENT:
        out.append('element = "%s"' % c['element'])
    if 'users' in c:
        out += ['users = %d' % int(c['users']), 'partners = []']
    return out


def cellules_esprit(stats, jeu):
    c = _changes(stats, jeu)
    out = ''
    for k in ('power_min', 'power_max'):
        if k in c:
            out += ', %s = %d' % (k, int(c[k]))
    if c.get('element') in NUM_ELEMENT:
        out += ', element = %d' % NUM_ELEMENT[c['element']]
    return out


def lignes_joueur(stats):
    """-> (lignes du [[character]], lignes de sa carte) ; vide = comme l'original. Les 8 stats vont ensemble."""
    s = stats or {}
    perso, carte = [], []
    if s.get('position') in dict(CHOIX_POSTE):
        perso.append('position = "%s"' % s['position'])
    if s.get('element') in NUM_ELEMENT:
        perso.append('element = "%s"' % s['element'])
    if s.get('sub_position') in dict(CHOIX_POSTE):
        carte.append('  sub_position = "%s"' % s['sub_position'])
    st = s.get('stats') or {}
    if all(isinstance(st.get(k), int) for k, _ in STATS_JOUEUR):
        carte.append('  stats = { %s }' % ', '.join('%s = %d' % (k, st[k]) for k, _ in STATS_JOUEUR))
    return perso, carte


def nettoyer(genre, brut):
    """valeurs reçues de la page -> valeurs sûres (bornes, choix connus) ; joueur : les 8 stats ensemble ou aucune"""
    out = {}
    for ch in CHAMPS.get(genre, []):
        cle = ch['cle']
        v = (brut.get('stats') or {}).get(cle[6:]) if cle.startswith('stats.') else brut.get(cle)
        if v in (None, ''):
            continue
        if ch['type'] == 'nombre':
            try:
                v = max(ch['min'], min(ch['max'], int(v)))
            except (TypeError, ValueError):
                continue
        elif v not in dict(ch['choix']):
            continue
        if cle.startswith('stats.'):
            out.setdefault('stats', {})[cle[6:]] = v
        else:
            out[cle] = v
    if 'stats' in out and len(out['stats']) != len(STATS_JOUEUR):
        raise ValueError('les 8 statistiques vont ensemble : remplis-les toutes, ou aucune (= celles de l\'original)')
    return out


# ------------------------------------------------------------------ réglage d'une création déjà faite
CLES_TECHNIQUE = ('power_min', 'power_max', 'tp', 'element', 'users', 'partners', 'growth')


def appliquer_technique(fichier_toml, lignes):
    """remplace les valeurs dans le bloc [[technique]] (avant ses sous-tables) du .toml écrit par l'Atelier"""
    L = open(fichier_toml, encoding='utf-8').read().split('\n')
    i = L.index('[[technique]]')
    j = i + 1
    while j < len(L) and L[j].strip() and not L[j].startswith((' ', '[')):
        j += 1
    bloc = [l for l in L[i + 1:j] if l.split('=')[0].strip() not in CLES_TECHNIQUE]
    L[i + 1:j] = bloc + lignes
    open(fichier_toml, 'w', encoding='utf-8').write('\n'.join(L))
