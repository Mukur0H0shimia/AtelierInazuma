// Langue de l'Atelier (FR / EN) — Atelier language switch.
// L'interface est écrite en français ; en anglais, chaque texte affiché (nœuds texte, title, placeholder, boîtes
// alert/confirm/prompt) est remplacé par sa traduction (web/i18n_en.js : window.I18N_EN). Les nombres sont gardés :
// « 12 techniques » cherche « {n} techniques ». Les noms venant du jeu sont donnés par le serveur dans la langue choisie.
// Esprits guerriers = Keshin.
(function () {
  'use strict';
  var CLE = 'atelier_langue';
  var langue = 'fr';
  try { langue = localStorage.getItem(CLE) || 'fr'; } catch (e) { }
  // la langue du serveur fait foi (noms du jeu) : demandée sans attendre, recharge si elle diffère
  try {
    var x = new XMLHttpRequest();
    x.open('GET', '/api/langue', false); x.send();
    if (x.status === 200) { langue = JSON.parse(x.responseText).langue || langue; }
  } catch (e) { }
  try { localStorage.setItem(CLE, langue); } catch (e) { }
  window.ATELIER_LANGUE = langue;
  document.documentElement.lang = langue;

  var D = {};
  function dico() { return D; }

  // (21/11) textes du mode simple, du bouton unique et des rapports en langage normal
  var SUP = {
    'Créer et mettre dans le jeu': 'Create and put in the game',
    'Crée ta copie puis la met dans le jeu (le jeu doit être fermé)': 'Creates your copy then puts it in the game (the game must be closed)',
    'Avancé': 'Advanced', 'Revenir au mode simple': 'Back to simple mode',
    'Enregistrer sans construire': 'Save without building', 'Supprimer': 'Delete', 'Retirer cette création (ses fichiers sont rangés à part, récupérables)': 'Remove this creation (its files are put aside, recoverable)', 'Créer la tenue': 'Create the outfit', 'Créer le joueur': 'Create the player', 'faites avec « Créer »': 'made with “Create”', 'Créer': 'Create',
    '« Créer » enregistre le maillot et refait le mod « Mes maillots » avec tous tes maillots, sans toucher au jeu. Pour le mettre dans le jeu : « Installer » dans Mes créations.': '“Create” saves the kit and rebuilds the “My kits” mod with all your kits, without touching the game. To put it in the game: “Install” in My creations.',
    // (22/11) nouveau menu des stats
    'Comme l’original : change une valeur, l’écart s’affiche ici.': 'Same as the original: change a value and the difference shows here.',
    'Valeurs de l’original gardées tant que tu ne changes rien.': 'The original’s values are kept until you change something.',
    '↺ Tout remettre': '↺ Reset all', 'Puiss. niv. 1': 'Power lv. 1', 'Puiss. max': 'Max power', 'PT': 'TP', 'Joueurs': 'Players',
    'Évolution': 'Growth', '2e poste': '2nd position',
    'Comme en jeu': 'As in the game', 'Original': 'Original', 'Puissance': 'Power', 'Au niveau 1': 'At level 1', 'Au niveau max': 'At max level',
    'Utilisation': 'Use', 'Coût en PT (tension)': 'TP cost (tension)', 'Nature': 'Nature', 'Solo': 'Solo', '2 joueurs': '2 players', '3 joueurs': '3 players',
    '4 joueurs': '4 players', 'Poste et élément': 'Position and element', 'Statistiques': 'Stats', 'les changer': 'change them',
    'poste d’origine': 'original position', 'élément d’origine': 'original element', 'Fermer': 'Close',
    'Sans « les changer » : les statistiques de l’original. Les 8 vont ensemble.': 'Without “change them”: the original’s stats. The 8 go together.',
    'Vide ou « comme l’original » : rien ne change': 'Empty or “like the original”: nothing changes',
    'Partie des valeurs de l’original : seules celles que tu changes sont écrites': 'Starts from the original’s values: only what you change is written',
    'ATT · Attaquant': 'FW · Forward', 'MIL · Milieu': 'MF · Midfielder', 'DÉF · Défenseur': 'DF · Defender', 'GAR · Gardien': 'GK · Goalkeeper',
    'FRAPPE': 'KICK', 'CONTRÔLE': 'CONTROL', 'TECHNIQUE': 'TECHNIQUE', 'PRESSION': 'PRESSURE', 'PHYSIQUE': 'PHYSICAL', 'INTELLIGENCE': 'INTELLIGENCE',
    'AGILITÉ': 'AGILITY', 'LIBERTÉ': 'FREEDOM',
    'En attente de stats': 'Waiting for stats', 'en attente de stats': 'waiting for stats', 'Régler les stats': 'Set the stats', 'Remettre celui de l’original': 'Back to the original’s', '−1 (Maj : −10)': '−1 (Shift: −10)', '+1 (Maj : +10)': '+1 (Shift: +10)', 'Remettre toutes les valeurs de l’original (rien n’est écrit avant « Enregistrer »)': 'Reset every value to the original’s (nothing is written before “Save”)', 'TOTEM': 'TOTEM', 'Remettre la valeur de l’original': 'Back to the original’s value', 'Technique liée': 'Linked move', 'Technique liée ✓': 'Linked move ✓', 'Stats': 'Stats',
    "le visuel est fait : règle ses valeurs (puissance, PT, élément…) ou garde celles de l'original": "the look is done: set its values (power, TP, element…) or keep the original's",
    "Garder celles de l'original": "Keep the original's", 'comme l’original': 'like the original',
    'Puissance au niveau 1': 'Power at level 1', 'Puissance au niveau max': 'Power at max level', 'Coût en PT': 'TP cost', 'Élément': 'Element',
    'Joueurs pour la lancer': 'Players needed', "Plus de 1 : n'importe quels coéquipiers": 'More than 1: any team mates', 'Courbe de progression (0-7)': 'Growth curve (0-7)',
    'Poste': 'Position', 'Poste secondaire': 'Secondary position', 'Attaquant': 'Forward', 'Milieu': 'Midfielder', 'Défenseur': 'Defender', 'Gardien': 'Goalkeeper',
    'Frappe': 'Kick', 'Contrôle': 'Control', 'Pression': 'Pressure', 'Physique': 'Physical', 'Agilité': 'Agility', 'Liberté': 'Freedom',
    "Les 8 statistiques vont ensemble : toutes remplies, ou toutes vides (= celles de l'original).": "The 8 stats go together: all filled, or all empty (= the original's).",
    'Mes polices': 'My fonts', '➕ Importer une police (.ttf / .otf)': '➕ Import a font (.ttf / .otf)', '➕ Importer une police…': '➕ Import a font…',
    "Proposées dans les bannières, les numéros et noms des maillots et l'outil Texte du mode dessin.": 'Offered in banners, kit numbers and names, and the drawing mode Text tool.',
    "Aucune pour l'instant.": 'None yet.', 'Retirer cette police': 'Remove this font',
    '📄 Copier l’image (pour une autre technique)': '📄 Copy the image (for another technique)',
    '⚙ Paramètres': '⚙ Settings', 'Paramètres : couleurs, musique': 'Settings: colours, music', 'Paramètres : couleurs, musique, polices, dossier du jeu': 'Settings: colours, music, fonts, game folder', "Couleurs de l'écran": 'Screen colours',
    "L'accueil (Mes créations) garde les couleurs du menu du jeu.": 'The home screen (My creations) keeps the game menu colours.',
    'Musique de fond': 'Background music', "Thème de l'écran titre du jeu": "The game's title screen theme", 'Volume': 'Volume',
    "Elle se coupe toute seule pendant la lecture d'une technique. Lue dans ton jeu, rien n'est copié.": 'It mutes itself while a technique plays. Read from your game, nothing is copied.',
    "Doré (d'origine)": 'Gold (original)', 'Sobre, comme le jeu': 'Plain, like the game', 'Bleu Inazuma': 'Inazuma blue', 'Ardoise et turquoise': 'Slate and turquoise',
    'Préparation de la musique…': 'Preparing the music…',
    'Tu as déjà commencé': 'You already started', 'Continuer ce projet': 'Continue this project', 'Non, en commencer un nouveau': 'No, start a new one',
    'Garde le maillot sans refaire le mod (pour le finir plus tard)': 'Keeps the kit without rebuilding the mod (to finish it later)',
    "« Créer » enregistre le maillot, refait le mod avec tous tes maillots et le met dans le jeu (le jeu doit être fermé). Il sera à la boutique générale d'Inazuma Fantasy.": "“Create” saves the kit, rebuilds the mod with all your kits and puts it in the game (the game must be closed). It will be in the Inazuma Fantasy general shop.",
    'Montrer les réglages avancés (codes, matériaux, boutons séparés…)': 'Show the advanced settings (codes, materials, separate buttons…)',
    'Détails': 'Details',
    'C’est créé ! Il reste à le mettre dans le jeu.': 'Created! It still has to be put in the game.',
    'Copie créée ! Il reste à la mettre dans le jeu.': 'Copy created! It still has to be put in the game.',
    'Tenue créée ! Il reste à la mettre dans le jeu.': 'Outfit created! It still has to be put in the game.',
    'Armure créée ! Il reste à la mettre dans le jeu.': 'Armour created! It still has to be put in the game.',
    'Objet créé ! Il reste à le mettre dans le jeu.': 'Item created! It still has to be put in the game.',
    'Ta technique est en vente à la boutique des supertechniques d’Inazuma Fantasy.': 'Your technique is on sale at the Inazuma Fantasy technique shop.',
    'Ton esprit guerrier / totem est en vente à la boutique d’entraînement d’Inazuma Fantasy (une armure devient la forme en armure de son esprit).': 'Your Keshin / totem is on sale at the Inazuma Fantasy training shop (an armour becomes the armoured form of its Keshin).',
    'Ton nouveau joueur t’attend au tirage Kizuna (ChronicleDeluxe).': 'Your new player is waiting in the Kizuna draw (ChronicleDeluxe).',
    'Ta tenue est en vente en boutique : équipe-la à un joueur comme les tenues du jeu.': 'Your outfit is on sale in the shop: equip it on a player like the game outfits.',
    'Ton objet est en vente à la boutique générale d’Inazuma Fantasy.': 'Your item is on sale at the Inazuma Fantasy general store.',
    'Ton maillot est en vente à la boutique générale d’Inazuma Fantasy.': 'Your kit is on sale at the Inazuma Fantasy general store.',
    'faites avec « Créer »': 'made with “Create” (or “Create” in advanced mode)',
    'Choisis une technique en haut, change ses couleurs, puis « Créer ».': 'Pick a technique at the top, change its colours, then “Create”.',
    'Choisis un esprit guerrier en haut, recolore-le, puis « Créer ».': 'Pick a Keshin at the top, recolour it, then “Create”.',
    'Choisis un totem en haut, recolore-le, puis « Créer ».': 'Pick a totem at the top, recolour it, then “Create”.',
    'Choisis un style, écris ton texte, puis utilise la bannière pour ta technique.': 'Pick a style, write your text, then use the banner for your technique.',
    'Choisis un maillot du jeu comme coupe, dessine le haut et le short, puis « Créer ».': 'Pick a game kit as a cut, draw the top and the shorts, then “Create”.',
    'Choisis une tenue en haut, recolore-la, puis « Créer ».': 'Pick an outfit at the top, recolour it, then “Create”.',
    'Choisis une armure en haut, recolore-la pour un de tes esprits, puis « Créer ».': 'Pick an armour at the top, recolour it for one of your Keshin, then “Create”.',
    'Choisis un personnage en haut, recolore sa tête, donne-lui un nom, puis « Créer ».': 'Pick a character at the top, recolour their head, give them a name, then “Create”.',
    'Choisis un objet en haut, donne-lui un nom et un prix, puis « Créer ».': 'Pick an item at the top, give it a name and a price, then “Create”.',
    'Choisir une pièce': 'Pick a part', 'Glisser': 'Drag', 'Tourner': 'Rotate', 'Molette': 'Wheel', 'Zoom': 'Zoom', 'Clic droit': 'Right click', 'Déplacer': 'Pan',
    'Appris au': 'Learnt at',
    'Enregistrer et mettre dans le jeu': 'Save and put in the game', 'Et maintenant :': 'What next:', 'Choisir ses techniques': 'Choose their techniques',
    'Choisir sa technique liée': 'Choose its linked technique', 'Lui faire une armure': 'Make it an armour', "Créer d'abord une copie d'esprit guerrier": 'First create a Keshin copy',
    'Choisis un esprit guerrier en haut, recolore-le et crée-le : tu pourras ensuite lui faire une armure.': 'Pick a Keshin at the top, recolour it and create it: you can then make it an armour.',
    '✎ Personnaliser la bannière': '✎ Customise the banner', 'Application…': 'Applying…',
    "Ouvre l'éditeur de bannière pour cette technique ; « Utiliser » te ramène ici avec l'aperçu à jour": 'Opens the banner editor for this technique; “Use” brings you back here with the preview up to date',
    'Bannière appliquée : tu la vois dans l’aperçu de la technique. Elle partira avec « Créer ».': 'Banner applied: you can see it in the technique preview. It will go with “Create”.', 'Choisir une technique': 'Choose a technique', 'Choisir un esprit': 'Choose a Keshin', 'Autre': 'Other',
    'CharacterReforged : 6 techniques + 1 esprit (case 9) ; les niveaux peuvent être recalculés': 'CharacterReforged: 6 techniques + 1 Keshin (slot 9); levels may be recomputed'
  };

  // (21/11) textes avec des données : [modèle sur le texte aux espaces réduits, remplacement]
  var MOTIFS = [
    // (22/11, 2.0.2) textes ajoutés après la traduction : copier / coller une texture, polices importées, Mes créations
    [/^Image de (.+) collée sur (\S+)(?: \(mise à sa taille : (.+?)\))?\. La forme des pièces reste celle de cette technique : une image faite pour une autre forme peut tomber autrement\. Pour revenir en arrière : « Annuler le dernier » \(bloc Remplacer une couleur partout\)\.$/,
     function (_, a, b, taille) { return 'Picture of ' + a + ' pasted on ' + b + (taille ? ' (resized: ' + taille + ')' : '')
       + '. The shape of the parts stays that of this technique: a picture made for another shape may land differently. To go back: “Undo last” (Replace a colour everywhere block).'; }],
    [/^Image de (.+) copiée sur (\S+)\. Pour revenir en arrière : « Annuler le dernier » \(bloc Remplacer une couleur partout\)\.$/,
     'Picture of $1 copied on $2. To go back: “Undo last” (Replace a colour everywhere block).'],
    [/^Retirer la police « (.+) » de l'Atelier \? \(ce qui est déjà fait avec ne change pas\)$/,
     'Remove the font “$1” from the Atelier? (what was already made with it does not change)'],
    [/^Police refusée : (.+)$/, function (_, e) { return 'Font refused: ' + trad(e); }],
    [/^Pas supprimé : (.+)$/, function (_, e) { return 'Not deleted: ' + trad(e); }],
    [/^« (.+) » supprimé\.$/, '“$1” deleted.'],
    [/^Technique liée : (.+)$/, 'Linked technique: $1'],
    // rapports de création des techniques (moteur/export.py) et contrôle des mods (moteur/verifier_mods.py), ligne par ligne
    [/^technique « (.+) » : code (\S+), cinématique (\S+) \(copie de (\S+)\)$/, 'technique “$1”: code $2, cutscene $3 (copy of $4)'],
    [/^(objet|modèle) (\S+) -> (\S+) : (\d+) texture\(s\) remplacée\(s\)(, lueurs recolorées)?(?:, (\d+) couleur\(s\) de matériau)?(?:, (\d+) teinte\(s\) de sommets \/ particules)?$/,
     function (_, q, a, b, n, l, m, t) { return (q === 'objet' ? 'object ' : 'model ') + a + ' -> ' + b + ': ' + n + ' texture(s) replaced' + (l ? ', glows recoloured' : '')
       + (m ? ', ' + m + ' material colour(s)' : '') + (t ? ', ' + t + ' vertex / particle tint(s)' : ''); }],
    [/^bannière « (.+?) »(?: \(aussi sous ses variantes (.+)\))?$/, function (_, t, v) { return 'banner “' + t + '”' + (v ? ' (also under its variants ' + v + ')' : ''); }],
    [/^bannière de l'éditeur(?: \(aussi sous ses variantes (.+)\))?$/, function (_, v) { return 'banner from the editor' + (v ? ' (also under its variants ' + v + ')' : ''); }],
    [/^bannière : celle d'origine$/, 'banner: the original one'],
    [/^bannière : (\S+)$/, 'banner: $1'],
    [/^(\S+) : cinématique (\S+) livrée en fichiers \(copie de (\S+)\)$/, '$1: cutscene $2 delivered as files (copy of $3)'],
    [/^cinématique d'échec (\S+) livrée en fichiers \(copie de (\S+), (\d+) changement\(s\) repris\)(?: ; absents de l'échec : (.+))?$/,
     function (_, a, b, n, x) { return 'failure cutscene ' + a + ' delivered as files (copy of ' + b + ', ' + n + ' change(s) carried over)' + (x ? '; not in the failure cutscene: ' + x : ''); }],
    [/^cinématique d'échec : celle d'origine(?: \((.+)\))?$/, function (_, x) { return 'failure cutscene: the original one' + (x ? ' (' + x + ')' : ''); }],
    [/^cinématique d'échec : première partie illisible \((.+)\), échec d'origine gardé$/, 'failure cutscene: first part unreadable ($1), original failure cutscene kept'],
    [/^(.+?) : cinématique d'échec (.+)$/, function (_, n, r) { return n + ': ' + trad("cinématique d'échec " + r); }],
    [/^cinématique d'échec de (.+) non livrée \((.+)\)$/, 'failure cutscene of $1 not delivered ($2)'],
    [/^esprit dans la cinématique : animations de (.+) livrées sous (\S+)$/, 'Keshin in the cutscene: animations of $1 delivered under $2'],
    [/^modèle (\S+) : c’est le totem \/ l’esprit du joueur qui lance \(le jeu le choisit\) -> pas copié ; pour le recolorer, fais une copie dans l’onglet Totems ou Esprits$/,
     'model $1: it is the totem / Keshin of the player who uses the move (the game picks it) -> not copied; to recolour it, make a copy in the Totems or Keshin tab'],
    [/^aura (.+) : choisie par le match \(balise\), pas recolorable -> ignorée$/, 'aura $1: picked by the match (tag), cannot be recoloured -> skipped'],
    [/^traînée : (\S+) en (\S+)$/, 'ball trail: $1 in $2'],
    [/^texture (\S+) : prise dans un autre objet \((.+)\), le jeu ne la recolore pas dans cette copie -> ignorée$/,
     'texture $1: taken from another object ($2), the game does not recolour it in this copy -> skipped'],
    [/^cinématique : copie automatique de VRFW gardée \((.+)\)$/, 'cutscene: VRFW’s automatic copy kept ($1)'],
    [/^boutique : (\d+) jetons$/, 'shop: $1 tokens'],
    [/^boutique d'entraînement : pas de vente$/, 'training shop: not for sale'],
    [/^\[\[event_env\]\] (\S+) : pas de ligne dans le jeu ni de `from` \(VRFW l'ignore\)$/, '[[event_env]] $1: no row in the game and no `from` (VRFW ignores it)'],
    [/^\[\[recolor\]\] (\S+) : image (\S+) absente de la planche de l'objet \(le jeu l'ignore\)$/, '[[recolor]] $1: picture $2 is not in the object’s texture sheet (the game ignores it)'],
    [/^cinématique (\S+) copiée par VRFW alors que (\S+) la livre déjà en fichiers$/, 'cutscene $1 copied by VRFW while $2 already delivers it as files'],
    [/^bannière (\S+) sans image \(celle du jeu sera montrée\)$/, 'banner $1 without a picture (the game’s one will be shown)'],
    [/^technique (\S+) : (event|fail_event) = (\S+) introuvable \(ni scène livrée, ni copie active, ni scène du jeu\)$/,
     'technique $1: $2 = $3 not found (no delivered scene, no active copy, no game scene)'],
    [/^TOML illisible : (.+)$/, 'unreadable TOML: $1'],
    // (22/11, avant l'espagnol : tout en anglais) rapports et erreurs des esprits, joueurs, tenues, objets, armures, maillots
    [/^copie (\S+) → code neuf (\S+) \(l'original ne change pas\)$/, 'copy $1 → new code $2 (the original does not change)'],
    [/^texture (\S+) \((\d+)x(\d+)\)$/, 'texture $1 ($2x$3)'],
    [/^texture textures recolorées gardées \(noms d'origine remis\)$/, 'texture: recoloured textures kept (original names restored)'],
    [/^scènes copiées : (.+)$/, function (_, x) { return 'cutscenes copied: ' + (x === 'aucune' ? 'none' : x); }],
    [/^icône : (dessin d'origine recoloré comme la copie|photo du modèle recoloré|copiée|aucune)$/, function (_, x) {
      return 'icon: ' + { "dessin d'origine recoloré comme la copie": 'original drawing recoloured like the copy', 'photo du modèle recoloré': 'photo of the recoloured model', 'copiée': 'copied', 'aucune': 'none' }[x]; }],
    [/^boutique d'entraînement : (\d+) points$/, 'training shop: $1 points'],
    [/^(.+) : technique liée « (.+) » \((\S+)\)$/, '$1: linked technique “$2” ($3)'],
    [/^(.+) : technique liée d'origine \(celle de (.+)\)$/, '$1: original linked technique (the one of $2)'],
    [/^cinématique : (.+) y apparaît \(animations de son esprit d'origine\)$/, 'cutscene: $1 appears in it (animations of its original Keshin)'],
    [/^cinématique : (.+) y apparaît avec les animations de (.+) \(mêmes os\)$/, 'cutscene: $1 appears in it with the animations of $2 (same bones)'],
    [/^cinématique : faite pour l'esprit (.+), dont les os ne sont pas tous dans (.+) : il y sera caché$/, 'cutscene: made for the Keshin $1, whose bones are not all in $2: it will be hidden there'],
    [/^cinématique : aucun esprit dedans \(rien à faire\)$/, 'cutscene: no Keshin in it (nothing to do)'],
    [/^MesTechniques : animations de (.+) livrées sous (\S+) \(à réinstaller aussi\)$/, 'MesTechniques: animations of $1 delivered under $2 (install it again too)'],
    [/^(.+) : pas de texture, copie laissée$/, '$1: no texture, copy left as it is'],
    [/^(.+) \((\S+)\) : modèle et (\d+) scène\(s\) refaits, textures gardées$/, '$1 ($2): model and $3 cutscene(s) redone, textures kept'],
    [/^sauvegarde : (.+)$/, 'backup: $1'],
    [/^armure (\S+) recolorée → forme en armure de « (.+) » \((\S+)\), modèle (\S+), technique (\S+) \(copiée de (\S+)\)$/,
     'armour $1 recoloured → armoured form of “$2” ($3), model $4, technique $5 (copied from $6)'],
    [/^id déjà utilisé \((.+)\) : réessaie$/, 'id already used ($1): try again'],
    [/^(\S+) n’est pas dans (\S+)$/, '$1 is not in $2'],
    [/^(\S+) : format pas encore pris en charge$/, '$1: format not supported yet'],
    [/^Le corps « (.+) » n’a pas de version de cette tenue, ni de corps au même squelette à emprunter\.$/, 'The build “$1” has no version of this outfit, and no build with the same skeleton to borrow from.'],
    [/^Le nom « (.+) » est déjà pris par une autre tenue : choisis-en un autre\.$/, 'The name “$1” is already used by another outfit: pick another one.'],
    [/^Le nom « (.+) » est déjà pris par une autre copie : choisis-en un autre\.$/, 'The name “$1” is already used by another copy: pick another one.'],
    [/^tenue « (.+) » : copie de (.+) \(vêtement (\S+)\), à équiper par les corps (.+), (\d+) jetons$/, 'outfit “$1”: copy of $2 (clothes $3), for the builds $4, $5 tokens'],
    [/^portrait : (dessin d’origine recoloré comme la tête|photo de la tête recolorée)$/, function (_, x) {
      return 'portrait: ' + (x === 'photo de la tête recolorée' ? 'photo of the recoloured head' : 'original drawing recoloured like the head'); }],
    [/^portrait de (\S+) refait : (dessin d'origine recoloré|photo du modèle recoloré)$/, function (_, c, x) {
      return 'portrait of ' + c + ' redone: ' + (x === "dessin d'origine recoloré" ? 'original drawing recoloured' : 'photo of the recoloured model'); }],
    [/^(.+) : (\d+) techniques choisies$/, '$1: $2 techniques chosen'],
    [/^(.+) : techniques de la carte d'origine \((.*)\)$/, '$1: techniques of the original card ($2)'],
    [/^niv\. (\d+) : (.+)$/, 'lv. $1: $2'],
    [/^(\S+) n’a pas de carte de joueur à copier\.$/, '$1 has no player card to copy.'],
    [/^cette texture n’est pas dans une colonne connue du vêtement (\S+)$/, 'this texture is not in a known column of the clothes $1'],
    [/^(.+) : copie de (.+) \((\S+)\) qui porte la tenue recolorée \((vêtement|chaussures|gants) (\S+), copie de (\S+)\), code (\S+)$/, function (_, n, p, c, g, m, b, k) {
      return n + ': copy of ' + p + ' (' + c + ') wearing the recoloured outfit (' + { 'vêtement': 'clothes', chaussures: 'shoes', gants: 'gloves' }[g] + ' ' + m + ', copy of ' + b + '), code ' + k; }],
    [/^ATTENTION : (\d+) ligne\(s\) où la texture est en colonne 7 \(nom de clé pas encore lu\) : gardées comme dans le jeu$/, 'WARNING: $1 row(s) where the texture is in column 7 (key name not read yet): kept as in the game'],
    [/^la texture (\S+) n’est pas celle de l’accessoire$/, 'the texture $1 is not the accessory’s'],
    [/^(.+) : copie de (.+) \((\S+)\) qui porte l’objet (\S+) recoloré \(accessoire (\S+)\), code (\S+)$/, '$1: copy of $2 ($3) wearing the recoloured item $4 (accessory $5), code $6'],
    [/^technique 0x([0-9A-F]{8}) inconnue \(ni du jeu, ni de mes créations\)$/, 'unknown technique 0x$1 (neither from the game nor from my creations)'],
    [/^(\d+) techniques : 6 au plus \(CharacterReforged : positions 1 à 6, cases 7 et 8 vides\)$/, '$1 techniques: 6 at most (CharacterReforged: positions 1 to 6, slots 7 and 8 empty)'],
    [/^icône recolorée \(planche (\S+)\)$/, 'icon recoloured (sheet $1)'],
    [/^icône recolorée \(fichier neuf (\S+), comme les emblèmes de ChronicleDeluxe et MesMaillots\)$/, 'icon recoloured (new file $1, like the emblems of ChronicleDeluxe and MesMaillots)'],
    [/^« (.+) » : copie de « (.+) » \((\S+), (catégorie .+|catégorie prise par VRFW sur l’original)\), (\d+) jetons à la boutique générale d’Inazuma Fantasy$/, function (_, n, o, c, k, p) {
      return '“' + n + '”: copy of “' + o + '” (' + c + ', ' + (k === 'catégorie prise par VRFW sur l’original' ? 'category taken by VRFW from the original' : 'category ' + k.slice(10)) + '), '
        + p + ' tokens at the Inazuma Fantasy general store'; }],
    [/^copie du modèle (\S+) : (.+)$/, 'copy of the model $1: $2'],
    [/^bannière de (\d+)x(\d+) au lieu de 1728x352$/, 'banner of $1x$2 instead of 1728x352'],
    [/^Technique « (.+) » introuvable dans MesTechniques\.$/, 'Technique “$1” not found in MesTechniques.'],
    [/^bannière de (.+) \((\S+)\) remplacée$/, 'banner of $1 ($2) replaced'],
    [/^(\S+) : modèle refait sous (\S+) \(au lieu de (\S+)\)$/, '$1: model redone under $2 (instead of $3)'],
    [/^déjà livrée en fichiers \(pas de content\/anims\/(.+)\)$/, 'already delivered as files (no content/anims/$1)'],
    [/^texte (.+) partagé par une autre commande$/, 'text $1 shared by another command'],
    [/^modèle de mod introuvable : (.+)$/, 'mod model not found: $1'],
    [/^modèle introuvable : (.+)$/, 'model not found: $1'],
    [/^le jeu n'a pas de portrait pour (.+)$/, 'the game has no portrait for $1'],
    [/^décodage impossible : (.+)$/, 'cannot decode: $1'],
    [/^Musique indisponible : (.+)$/, function (_, e) { return 'Music unavailable: ' + trad(e); }],
    [/^(.+) · (.+) \(désactivé\)$/, function (_, t, m) { return trad(t) + ' · ' + m + ' (disabled)'; }],
    [/^il manque le haut domicile pour : (.+)$/, 'the home top is missing for: $1'],
    [/^Un NOUVEL objet : ton nom, ta description, ton prix ; les mêmes effets que « (.+) »\. L’original ne change pas\. (.+)$/, function (_, n, f) {
      return 'A NEW item: your name, your description, your price; the same effects as “' + n + '”. The original does not change. '
        + ({ 'Pas d’image dans le jeu pour ce genre d’objet : la copie s’affiche en texte, comme l’original.': 'No picture in the game for this kind of item: the copy is shown as text, like the original.',
             'Son icône : celle que tu recolores (✎ Mode dessin).': 'Its icon: the one you recolour (✎ Drawing mode).',
             'Son icône : celle de l’original (ce genre d’icône ne se remplace pas encore).': 'Its icon: the original’s (this kind of icon cannot be replaced yet).' }[f] || f); }],
    [/^Calque (\d+)$/, 'Layer $1'],
    [/^Un fichier du mod est utilisé par un autre programme \(le jeu, le gestionnaire de mods, un antivirus, OneDrive…\) : ferme-le puis clique à nouveau sur « Installer »\. Rien n’a été changé dans le jeu\. \((.+)\)$/,
     'A file of the mod is used by another program (the game, the mod manager, an antivirus, OneDrive…): close it then click “Install” again. Nothing was changed in the game. ($1)'],
    // avertissement « fichiers du jeu illisibles » (serveur.py, CATALOGUES_EN_ERREUR : « partie : erreur »)
    [/^(techniques|esprits \/ totems \(chara_base\)|tout le jeu \(maillots, tenues, armures, têtes\)|accessoires \(chara_parts\)|objets) : (.+)$/,
     function (_, p, e) { return { techniques: 'techniques', 'esprits / totems (chara_base)': 'Keshin / totems (chara_base)',
       'tout le jeu (maillots, tenues, armures, têtes)': 'the whole game (kits, outfits, armours, heads)', 'accessoires (chara_parts)': 'accessories (chara_parts)',
       objets: 'items' }[p] + ': ' + e; }],
    [/^(\S+) : (\d+) × (\d+) pixels\. Les changements partent dans l'aperçu et le lecteur natif ; le mod les reprend à « Créer le mod »\.$/,
     '$1: $2 × $3 pixels. The changes go to the preview and the native player; the mod takes them when you click “Create”.'],
    [/^la technique liée doit être un tir, un dribble, une défense ou un arrêt \((.+)\)$/, 'the linked technique must be a shot, a dribble, a block or a save ($1)'],
    [/^numéro : (.+) \((\d+)x(\d+)\)…$/, 'number: $1 ($2x$3)…'],
    [/^relief : recherche du maillot le plus uni de cette coupe \((\d+) maillots, une seule fois\)…$/, 'relief: looking for the plainest kit of this cut ($1 kits, only once)…'],
    // Atelier Maillots (journal du mod « Mes maillots », moteur/maillots/atelier_mod.py)
    [/^(\d+) maillots du jeu utilisables comme base$/, '$1 game kits usable as a base'],
    [/^images exportées dans (.+)$/, 'pictures exported to $1'],
    [/^(.+) : relief du tissu \((.+)\) : (.+)$/, '$1: fabric relief ($2): $3'],
    [/^pas de « (.+) » dans (.+)$/, 'no “$1” in $2'],
    [/^(.+) : (.+) agrandi de (\d+)x(\d+) à (\d+)x(\d+)$/, '$1: $2 enlarged from $3x$4 to $5x$6'],
    [/^(.+) : (.+) redimensionné de (\d+)x(\d+) à (\d+)x(\d+)$/, '$1: $2 resized from $3x$4 to $5x$6'],
    [/^(.+) : encodage du (.+) (\d+) %$/, '$1: encoding the $2 $3 %'],
    [/^(.+) : (.+) encodé en ([\d.,]+) s$/, '$1: $2 encoded in $3 s'],
    [/^(.+) : emblème (.+)$/, '$1: emblem $2'],
    [/^(.+) : il manque l'image du haut \(domicile\)$/, '$1: the top picture (home) is missing'],
    [/^(.+) : bords non traités \((.+)\)$/, '$1: edges not processed ($2)'],
    [/^(.+) : bustes des portraits \(domicile (.+), extérieur (.+)\)…$/, '$1: portrait busts (home $2, away $3)…'],
    [/^(.+) : motif du maillot sur les portraits$/, '$1: kit pattern on the portraits'],
    [/^(.+) : pas d'icône \(ni la tienne, ni celle du maillot de base\)$/, '$1: no icon (neither yours nor the base kit’s)'],
    [/^mod écrit \(pas installé\) : (\d+) maillot\(s\) dans (.+)$/, 'mod written (not installed): $1 kit(s) in $2'],
    [/^mod installé : (\d+) maillot\(s\) dans (.+)$/, 'mod installed: $1 kit(s) in $2'],
    [/^modèle 3D introuvable pour (.+)$/, '3D model not found for $1'],
    [/^aperçu 3D : (.+)$/, function (_, e) { return '3D preview: ' + trad(e); }],
    [/^ce n'est pas un fichier PNG : (.+)$/, 'this is not a PNG file: $1'],
    [/^PNG non pris en charge \(profondeur (\d+) bits, type (\d+)\) : réenregistre en PNG 24 ou 32 bits$/, 'PNG not supported (depth $1 bits, type $2): save it again as a 24 or 32 bit PNG'],
    [/^VRFW remis dans enabled\.toml \(il en manquait : aucun mod ne se chargeait\)$/, 'VRFW put back in enabled.toml (it was missing: no mod was loading)'],
    [/^enabled\.toml \(créé par une version précédente de l’Atelier, il éteignait VRFW et tes autres mods\) retiré$/,
     'enabled.toml (made by an older version of the Atelier, it switched VRFW and your other mods off) removed'],
    [/^⚠ VRFW n’est pas dans le dossier mods de ce jeu \((.+)\) : le mod ne se chargera pas\. Si ton gestionnaire de mods utilise une autre installation du jeu, choisis-la dans ⚙ Paramètres > Dossier du jeu, puis installe à nouveau\. Sinon, installe VRFW \(avec Inazuma Fantasy\)\.$/,
     '⚠ VRFW is not in this game’s mods folder ($1): the mod will not load. If your mod manager uses another installation of the game, pick it in ⚙ Settings > Game folder, then install again. Otherwise, install VRFW (with Inazuma Fantasy).'],
    [/^VRFW n’est pas dans le dossier mods de ce jeu \((.+)\) : le mod ne se chargera pas\. Si ton gestionnaire de mods utilise une autre installation du jeu, choisis-la dans ⚙ Paramètres > Dossier du jeu, puis installe à nouveau\. Sinon, installe VRFW \(avec Inazuma Fantasy\)\.$/,
     'VRFW is not in this game’s mods folder ($1): the mod will not load. If your mod manager uses another installation of the game, pick it in ⚙ Settings > Game folder, then install again. Otherwise, install VRFW (with Inazuma Fantasy).'],
    [/^(VRFW ✓|sans VRFW) ·(\d+) mod\(s\)(?: · tes mods : (.+))?$/, function (_, v, n, m) {
      return (v === 'sans VRFW' ? 'no VRFW' : v) + ' · ' + n + ' mod(s)' + (m ? ' · your mods: ' + m : ''); }],
    [/^« (.+) » introuvable dans le jeu et les mods activés \(il venait peut-être d’un mod retiré ou désactivé\)\.$/,
     '“$1” not found in the game and the enabled mods (it may come from a removed or disabled mod).'],
    // « Supprimer » (serveur.py, supprimer_creation)
    [/^technique supprimée : (\d+) fichiers de l'Atelier et (\d+) du jeu rangés dans (.+)$/, 'technique deleted: $1 files of the Atelier and $2 of the game put aside in $3'],
    [/^(armure|esprit guerrier|tenue|objet) supprimée? \((\d+) fichiers rangés dans (.+)\)$/, function (_, q, n, d) {
      return { armure: 'armour', 'esprit guerrier': 'Keshin', tenue: 'outfit', objet: 'item' }[q] + ' deleted (' + n + ' files put aside in ' + d + ')'; }],
    [/^personnage supprimé \(fichiers rangés dans (.+)\)$/, 'character deleted (files put aside in $1)'],
    [/^Utilisée? par : (.+)\. Change-l[ae] d'abord là-bas\.$/, function (_, u) {
      return 'Used by: ' + u.replace(/ \(techniques du joueur\)/g, ' (player’s techniques)').replace(/ \(technique liée\)/g, ' (linked technique)')
        .replace(/ \(armure\)/g, ' (armour)') + '. Change it there first.'; }],
    [/^Le jeu est ouvert : ferme-le d'abord \(la technique est aussi retirée du jeu\)\.$/, 'The game is open: close it first (the technique is also removed from the game).'],
    [/^(armure|esprit|tenue|objet) inconnue?$/, function (_, q) { return 'unknown ' + { armure: 'armour', esprit: 'Keshin', tenue: 'outfit', objet: 'item' }[q]; }],
    [/^suppression pas prévue pour ce genre$/, 'deleting is not available for this kind'],
    // menus Techniques du joueur / Technique liée (genre et élément viennent du serveur en français)
    [/^(.+) — (Tir|Dribble|Défense|Gardien|Arrêt|Tir simple|Dribble simple|Défense simple|Arrêt simple)(?:, (Air|Feu|Forêt|Montagne|Néant))? \((\w+)\)$/,
     function (_, n, g, el, code) { return n + ' — ' + trad(g) + (el ? ', ' + trad(el) : '') + ' (' + code + ')'; }],
    [/^La technique que (.+) donne en jeu \(comme Michael et sa Lumière de Michael\)\. ★ = tes techniques\.$/,
     'The technique $1 gives in game (like Michael and his own technique). ★ = your techniques.'],
    [/^Sans choix : celle de (.+?)( —|\.)$/, 'Without a choice: that of $1$2'],
    [/^✦ = (.+) apparaît dans la cinématique de la technique \(en haut de la liste\)\.$/, '✦ = $1 appears in the technique’s cutscene (at the top of the list).'],
    [/^✦ (.+) apparaît dans la cinématique \(c'est celle de son esprit d'origine\)\.$/, '✦ $1 appears in the cutscene (it is the one of its original Keshin).'],
    [/^✦ (.+) apparaît dans la cinématique avec les animations de l'esprit (.+) \(tous ses os existent dans (.+)\)\.$/,
     '✦ $1 appears in the cutscene with the animations of the Keshin $2 (all its bones exist in $3).'],
    [/^Cinématique faite pour l'esprit (.+) : ses os ne sont pas tous dans (.+), il y sera caché\.$/,
     'Cutscene made for the Keshin $1: not all its bones are in $2, it will be hidden there.'],
    [/^Prise dans un autre objet \((.+)\) : le jeu ne la recolore pas dans ta copie \(ignorée à la création\)\.$/,
     'Taken from another object ($1): the game does not recolour it in your copy (skipped when creating).'],
    [/^\((\d\d\/\d\d · \d\d:\d\d)\)(?: et (\d+) autres? \(accueil\))?\.$/, function (_, d, n) {
      return '(' + d + ')' + (n ? ' and ' + n + ' more (home page)' : '') + '.'; }],
    [/^Copie de (.+?)( · code (\S+))?$/, function (_, n, x, c) { return 'Copy of ' + n + (c ? ' · code ' + c : ''); }],
    [/^Stats de (.+)$/, 'Stats of $1'], [/^original : (.+)$/, 'original: $1'],
    [/^📋 Coller ici : (.+)$/, '📋 Paste here: $1'],
    [/^Image de (\S+) copiée \((\d+) × (\d+)\)\. Ouvre une autre technique, clic droit sur une texture : « Coller ici »\.$/, 'Image of $1 copied ($2 × $3). Open another technique, right-click a texture: “Paste here”.'],
    [/^(\S+) \((\d+) pièces?\)$/, '$1  ($2 parts)'],
    [/^(\S+) \(modèle de personnage : textures seulement\)$/, '$1  (character model: textures only)'],
    [/^(#[0-9a-f]{6}) · (\d+) % · ([a-zé, ]+) \(clic : remplacer cette couleur\)$/i, function (_, c, p, src) {
      return c + ' · ' + p + ' % · ' + src.replace(/matériaux/g, 'materials').replace(/sommets/g, 'vertices') + '\n(click: replace this colour)'; }],
    [/^(\S+) \((\d+)×(\d+)\) : carte de données, non modifiable$/, '$1 ($2×$3): data map, not editable'],
    [/^matériau (\S+) \((\S+)\) pièces : (.+?) couleur du jeu : (\S+ \/ \S+ \/ \S+) \(cliquer : choisir ces pièces\) \(clic droit : localiser\)$/,
     'material $1 ($2)\nparts: $3\ngame colour: $4\n(click: select these parts)\n(right-click: locate)'],
    [/^(\S+) \/ pièce (\d+) : (\d+) % de sommets colorés \(cliquer : choisir ces pièces\) \(clic droit : localiser\)$/,
     '$1 / part $2: $3 % coloured vertices\n(click: select these parts)\n(right-click: locate)'],
    [/^(.+?) · d'après (.+)$/, function (_, tete, base) { return trad(tete) + ' · based on ' + base; }],
    [/^(.+?) · copie de (.+)$/, function (_, tete, base) { return trad(tete) + ' · copy of ' + base; }],
    [/^Modifié le (\S+) · (\S+)$/, 'Modified on $1 · $2'],
    [/^Créé le (\S+) · (\S+)$/, 'Created on $1 · $2'],
    [/^(\S+) : (\d+) émetteurs?$/, function (_, o, n) { return o + ': ' + n + (n === '1' ? ' emitter' : ' emitters'); }],
    [/^Toutes les particules de cet objet \(VRFW ne sépare pas les émetteurs\)$/, 'All the particles of this object (VRFW does not separate emitters)'],
    // toute infobulle de pièce qui finit par l'aide « cliquer / clic droit » : le début traduit à part, puis l'aide
    [/^(.+) \(cliquer : choisir ces pièces\) \(clic droit : localiser\)$/, function (_, tete) {
      return trad(tete) + '\n(click: select these parts)\n(right-click: locate)'; }],
    // (21/11) compte de la liste de recherche, rapports de création et d'installation (bloc sous le panneau de droite)
    [/^(\d+) résultats?$/, function (_, n) { return n + (n === '1' ? ' result' : ' results'); }],
    [/^(Copie|Tenue|Armure) créée \(pas encore installée\) : (.+)$/, function (_, q, d) {
      return { Copie: 'Copy', Tenue: 'Outfit', Armure: 'Armour' }[q] + ' created (not installed yet): ' + d; }],
    [/^(Mod|Objet) créé \(pas encore installé\) : (.+)$/, function (_, q, d) { return (q === 'Mod' ? 'Mod' : 'Item') + ' created (not installed yet): ' + d; }],
    [/^Installé dans (.+)$/, 'Installed in $1'],
    [/^Sauvegarde : (.+)$/, 'Backup: $1'],
    [/^⚠ À vérifier \(le jeu ignorera\) :$/, '⚠ To check (the game will ignore it):'],
    [/^Remettre la valeur de l’original \((.+)\)$/, 'Back to the original’s value ($1)'],
    [/^Original : stats du mod (.+) \(activé\), comme en jeu\.$/, 'Original: stats from the $1 mod (enabled), as in the game.'],
    [/^(\d+) stats? · total$/, '$1 stat(s) · total'],
    [/^Réparé \(totem \/ esprit qui n’apparaissait pas dans la cinématique\) : (.+)$/, 'Repaired (totem / Keshin missing from the cutscene): $1'],
    [/^Pas installé : (.+)$/, function (_, e) { return 'Not installed: ' + trad(e); }],
    [/^Erreur : (.+)$/, function (_, e) { return 'Error: ' + trad(e); }],
    [/^Lance le jeu, puis regarde le journal de VRFW \(aucune ligne ERROR\)\.$/, 'Start the game, then check the VRFW log (no ERROR line).'],
    [/^« Installer dans le jeu », puis tirage Kizuna \(ChronicleDeluxe\)\.$/, '“Install in the game”, then the Kizuna draw (ChronicleDeluxe).'],
    [/^« Installer dans le jeu » \(mod (\S+)\)\.$/, '“Install in the game” (mod $1).'],
    [/^(.+?) : copie de (.+?) \((\S+)\), code (\S+), carte (\S+) copiée de (\S+)$/, '$1: copy of $2 ($3), code $4, card $5 copied from $6'],
    [/^portrait : dessin d’origine recoloré comme la tête$/, 'portrait: original drawing recoloured like the head'],
    [/^portrait : photo de la tête recolorée$/, 'portrait: photo of the recoloured head'],
    [/^portrait : celui de (.+) \(couleurs d’origine\)$/, 'portrait: the one of $1 (original colours)'],
    [/^copie (\S+) → code neuf (\S+) \(l'original ne change pas\)$/, 'copy $1 → new code $2 (the original does not change)'],
    [/^texture (\S+) \((\d+x\d+)\)$/, 'texture $1 ($2)'],
    [/^scènes copiées : (.+)$/, 'copied scenes: $1'],
    [/^icône : dessin d'origine recoloré comme la copie$/, 'icon: original drawing recoloured like the copy'],
    [/^boutique d'entraînement : (\d+) points$/, 'training shop: $1 points'],
    [/^Création de la copie « (.+) » \(réencodage de (\d+) texture\(s\)\)…$/, 'Creating the copy “$1” (re-encoding $2 texture(s))…'],
    [/^Création de la copie \(réencodage des textures, environ 45 s\)…$/, 'Creating the copy (re-encoding the textures, about 45 s)…'],
    [/^Création (de la tenue|de l’armure|du nouveau joueur|de la copie)…$/, function (_, q) {
      return 'Creating ' + { 'de la tenue': 'the outfit', 'de l’armure': 'the armour', 'du nouveau joueur': 'the new player', 'de la copie': 'the copy' }[q] + '…'; }],
    [/^Installation…$/, 'Installing…'],
    [/^Utiliser pour « (.+) » et revenir à la technique$/, 'Use for “$1” and go back to the technique'],
    [/^Enregistrer dans ma copie « (.+) »$/, 'Save into my copy “$1”'],
    [/^Copie de (.+) · code (\S+)$/, 'Copy of $1 · code $2'],
    [/^Celles de (\S+)$/, '$1’s'],
    [/^C’est dans le jeu ! (.+?) \(Relance le jeu s’il était ouvert\.\)$/, function (_, ou) { return 'It’s in the game! ' + trad(ou) + ' (Restart the game if it was open.)'; }],
    [/^Ça n’a pas marché : (.+)$/, function (_, e) { return 'It did not work: ' + trad(e); }],
    [/^Pas mis dans le jeu : (.+)$/, function (_, e) { return 'Not put in the game: ' + trad(e); }],
    [/^Installer remplace le mod (\S+) du jeu\. Ces créations n'existent pas dans cet Atelier et seront retirées du jeu :$/,
     '“Install” replaces the $1 mod of the game. These creations are not in this Atelier and will be removed from the game:'],
    [/^\(une sauvegarde est faite avant ; « Annuler » pour ne rien changer\)$/, '(a backup is made first; “Cancel” to change nothing)'],
    [/^Continuer \?$/, 'Continue?'],
    [/^Installation annulée : rien n’a changé\.$/, 'Installation cancelled: nothing changed.'],
    [/^Installer retirerait du jeu : (.+) \(absents de cet Atelier\)\.$/, '“Install” would remove from the game: $1 (not in this Atelier).'],
    [/^Texture déjà colorée \((.+?)\) : la couleur du matériau la MULTIPLIE \(orange × bleu = presque noir\)\. Pour changer la teinte, recolore plutôt la texture \(bloc Textures\) et laisse le matériau blanc\.$/,
     'Already coloured texture ($1): the material colour MULTIPLIES it (orange × blue = almost black). To change the hue, recolour the texture instead (Textures block) and leave the material white.']
  ];

  // (22/11) ESPAGNOL : dictionnaire web/i18n_es.js (window.I18N_ES, phrases fixes) et modèles window.MOTIFS_ES (textes avec
  // données). Une phrase pas encore traduite en espagnol s'affiche en ANGLAIS (plus proche pour un hispanophone que le français).
  function trad(s) {
    if (langue === 'fr' || !s) { return s; }
    if (langue === 'es') {                       // null = rien trouvé en espagnol (une traduction identique au français compte)
      var e = tradL(s, 'es');
      return e !== null ? e : tradL(s, 'en');
    }
    return tradL(s, 'en');
  }
  function tradL(s, lg) {
    var brut = s.trim();
    if (!brut) { return s; }
    var t = brut.replace(/\s+/g, ' ');           // le dictionnaire a les espaces réduits
    var es = lg === 'es';
    var d = (es ? window.I18N_ES : window.I18N_EN) || {};
    var SUPL = es ? (window.SUP_ES || {}) : SUP, MOTIFSL = es ? (window.MOTIFS_ES || []) : MOTIFS;
    var r = d[t] !== undefined ? d[t] : SUPL[t];
    if (r === undefined) {                       // avec des nombres : « {n} »
      var nb = [];
      var modele = t.replace(/\d+(?:[.,]\d+)?/g, function (m) { nb.push(m); return '{n}'; });
      if (nb.length && d[modele] !== undefined) {
        var i = 0;
        r = d[modele].replace(/\{n\}/g, function () { return nb[i++]; });
      }
    }
    if (r === undefined && /\n/.test(brut)) {    // (21/11) bloc de plusieurs lignes (rapports) : ligne par ligne, « - » gardé
      var lignes = brut.split('\n'), chg = false;
      for (var j = 0; j < lignes.length; j++) {
        var lg = lignes[j], tiret = (lg.match(/^\s*-\s+/) || [''])[0], corps = lg.slice(tiret.length);
        if (!corps.trim()) { continue; }
        var tl = trad(corps);
        if (tl !== corps) { lignes[j] = tiret + tl; chg = true; }
      }
      if (chg) { return s.replace(brut, lignes.join('\n')); }
    }
    if (r === undefined) {                       // textes fabriqués avec des données (noms, nombres, couleurs)
      for (var m = 0; m < MOTIFSL.length && r === undefined; m++) {
        if (MOTIFSL[m][0].test(t)) { r = t.replace(MOTIFSL[m][0], MOTIFSL[m][1]); }
      }
    }
    if (r === undefined) {                       // bannières : police absente de ce PC
      var p0 = t.match(/^Police absente de ce PC : (\S+) \(Impact utilisée à la place\)\.$/);
      if (p0) { r = es ? 'Fuente no instalada en este PC: ' + p0[1] + ' (se usa Impact).' : 'Font not on this PC: ' + p0[1] + ' (Impact used instead).'; }
    }
    if (r === undefined) {                       // « cinématique ev62_00010_1 » (titre d'une technique)
      var c0 = t.match(/^cinématique (\S+)$/);
      if (c0) { r = (es ? 'cinemática ' : 'cutscene ') + c0[1]; }
    }
    if (r === undefined) {                       // « Éclaircir (O) » : texte + touche
      var k0 = t.match(/^([^·]*?)( \([^()]{1,8}\))$/);
      if (k0 && d[k0[1]] !== undefined) { r = d[k0[1]] + k0[2].replace(/\bMaj\b/g, es ? 'Mayús' : 'Shift'); }   // (22/11) « Maj+O » -> « Shift+O »
    }
    if (r === undefined && t.indexOf(' · ') > 0) {   // infobulles « Outil (touche) · explication »
      var i0 = t.indexOf(' · ');
      var tete = t.slice(0, i0), reste = t.slice(i0 + 3);
      var tt = trad(tete), tr = d[reste] !== undefined ? d[reste] : trad(reste);
      if (tt !== tete || tr !== reste) { r = tt + ' · ' + tr; }
    }
    if (r === undefined) {                       // dernier recours : les mots du jeu (Esprit guerrier -> Keshin)
      if (es) { return null; }                   // espagnol : l'anglais prend le relais (trad)
      r = t.replace(/[Ee]sprits? guerriers?|\b[Ee]sprits?\b/g, 'Keshin');
      if (r === t) { return s; }
    }
    return s.replace(brut, r);
  }
  window.t = window.trad = trad;

  var ATTRS = ['title', 'placeholder', 'aria-label', 'alt'];
  var FAIT = new WeakMap();                       // nœud -> dernier texte posé (évite de retraduire en boucle)

  function texte(n) {
    if (FAIT.get(n) === n.nodeValue) { return; }
    var p = n.parentNode;
    if (p && (p.nodeName === 'SCRIPT' || p.nodeName === 'STYLE' || p.isContentEditable || p.closest && p.closest('[data-pas-traduire]'))) { return; }
    var v = trad(n.nodeValue);
    if (v !== n.nodeValue) { n.nodeValue = v; }
    FAIT.set(n, n.nodeValue);
  }

  function element(e) {
    for (var i = 0; i < ATTRS.length; i++) {
      var a = e.getAttribute && e.getAttribute(ATTRS[i]);
      if (a) { var v = trad(a); if (v !== a) { e.setAttribute(ATTRS[i], v); } }
    }
    if (e.nodeName === 'INPUT' && (e.type === 'button' || e.type === 'submit') && e.value) {
      var w = trad(e.value); if (w !== e.value) { e.value = w; }
    }
  }

  function parcourir(racine) {
    if (!racine) { return; }
    if (racine.nodeType === 3) { texte(racine); return; }
    if (racine.nodeType !== 1 && racine.nodeType !== 9 && racine.nodeType !== 11) { return; }
    if (racine.nodeType === 1) { element(racine); }
    var w = document.createTreeWalker(racine, NodeFilter.SHOW_ELEMENT | NodeFilter.SHOW_TEXT);
    var n;
    while ((n = w.nextNode())) {
      if (n.nodeType === 3) { texte(n); } else { element(n); }
    }
  }

  if (langue !== 'fr') {
    var obs = new MutationObserver(function (liste) {
      for (var i = 0; i < liste.length; i++) {
        var m = liste[i];
        if (m.type === 'characterData') { texte(m.target); }
        else if (m.type === 'attributes') { element(m.target); }
        else { for (var j = 0; j < m.addedNodes.length; j++) { parcourir(m.addedNodes[j]); } }
      }
    });
    var lancer = function () {
      document.title = trad(document.title);
      parcourir(document.body);
      obs.observe(document.body, { childList: true, subtree: true, characterData: true, attributes: true, attributeFilter: ATTRS });
    };
    if (document.body) { lancer(); } else { document.addEventListener('DOMContentLoaded', lancer); }
    var A = window.alert, C = window.confirm, P = window.prompt;
    window.alert = function (m) { return A.call(window, trad(String(m))); };
    window.confirm = function (m) { return C.call(window, trad(String(m))); };
    window.prompt = function (m, v) { return P.call(window, trad(String(m)), v); };
  }

  // (22/11) LANGUES : français, anglais, espagnol. Choix dans l'en-tête (menu) et dans ⚙ Paramètres (window.LANGUES_ATELIER /
  // window.choisirLangue). Chaque langue écrite dans sa propre langue, pour la retrouver sans comprendre la langue actuelle.
  var LANGUES = [{ code: 'fr', nom: 'Français' }, { code: 'en', nom: 'English' }, { code: 'es', nom: 'Español' }];
  window.LANGUES_ATELIER = LANGUES;
  window.choisirLangue = function (l) {
    if (l === langue || !LANGUES.some(function (x) { return x.code === l; })) { return; }
    fetch('/api/langue', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ langue: l }) })
      .then(function () { try { localStorage.setItem(CLE, l); } catch (e) { } location.reload(); })
      .catch(function () { location.reload(); });
  };
  function bouton() {
    var h = document.querySelector('header');
    if (!h || document.getElementById('bouton-langue')) { return; }
    var b = document.createElement('select');
    b.id = 'bouton-langue';
    b.setAttribute('data-pas-traduire', '');
    b.title = 'Langue · Language · Idioma';
    LANGUES.forEach(function (x) { var o = new Option(x.code.toUpperCase() + ' · ' + x.nom, x.code); b.appendChild(o); });
    b.value = langue;
    b.style.cssText = 'margin-left:8px;padding:4px 6px;border-radius:6px;border:1px solid #fff6;background:#0003;color:inherit;' +
      'font-weight:700;cursor:pointer;flex:none;font:inherit';
    b.onchange = function () { b.disabled = true; window.choisirLangue(b.value); };
    h.appendChild(b);
  }
  if (document.readyState === 'loading') { document.addEventListener('DOMContentLoaded', bouton); } else { bouton(); }
  window.I18N = { trad: trad, dico: dico };
}());
