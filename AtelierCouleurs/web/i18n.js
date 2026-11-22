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
    'En attente de stats': 'Waiting for stats', 'en attente de stats': 'waiting for stats', 'Régler les stats': 'Set the stats', 'Stats': 'Stats',
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
    '⚙ Paramètres': '⚙ Settings', 'Paramètres : couleurs, musique': 'Settings: colours, music', "Couleurs de l'écran": 'Screen colours',
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

  function trad(s) {
    if (langue !== 'en' || !s) { return s; }
    var brut = s.trim();
    if (!brut) { return s; }
    var t = brut.replace(/\s+/g, ' ');           // le dictionnaire a les espaces réduits
    var d = window.I18N_EN || {};
    var r = d[t] !== undefined ? d[t] : SUP[t];
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
      for (var m = 0; m < MOTIFS.length && r === undefined; m++) {
        if (MOTIFS[m][0].test(t)) { r = t.replace(MOTIFS[m][0], MOTIFS[m][1]); }
      }
    }
    if (r === undefined) {                       // bannières : police absente de ce PC
      var p0 = t.match(/^Police absente de ce PC : (\S+) \(Impact utilisée à la place\)\.$/);
      if (p0) { r = 'Font not on this PC: ' + p0[1] + ' (Impact used instead).'; }
    }
    if (r === undefined) {                       // « cinématique ev62_00010_1 » (titre d'une technique)
      var c0 = t.match(/^cinématique (\S+)$/);
      if (c0) { r = 'cutscene ' + c0[1]; }
    }
    if (r === undefined) {                       // « Éclaircir (O) » : texte + touche
      var k0 = t.match(/^([^·]*?)( \([^()]{1,8}\))$/);
      if (k0 && d[k0[1]] !== undefined) { r = d[k0[1]] + k0[2]; }
    }
    if (r === undefined && t.indexOf(' · ') > 0) {   // infobulles « Outil (touche) · explication »
      var i0 = t.indexOf(' · ');
      var tete = t.slice(0, i0), reste = t.slice(i0 + 3);
      var tt = trad(tete), tr = d[reste] !== undefined ? d[reste] : trad(reste);
      if (tt !== tete || tr !== reste) { r = tt + ' · ' + tr; }
    }
    if (r === undefined) {                       // dernier recours : les mots du jeu (Esprit guerrier -> Keshin)
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

  if (langue === 'en') {
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

  // bouton FR / EN dans l'en-tête
  function bouton() {
    var h = document.querySelector('header');
    if (!h || document.getElementById('bouton-langue')) { return; }
    var b = document.createElement('button');
    b.id = 'bouton-langue';
    b.setAttribute('data-pas-traduire', '');
    b.title = langue === 'en' ? 'Passer l’Atelier en français' : 'Switch the Atelier to English';
    b.textContent = langue === 'en' ? 'FR' : 'EN';
    b.style.cssText = 'margin-left:8px;padding:4px 10px;border-radius:6px;border:1px solid #fff6;background:#0003;color:inherit;' +
      'font-weight:700;cursor:pointer;flex:none';
    b.onclick = function () {
      var l = langue === 'en' ? 'fr' : 'en';
      b.disabled = true; b.textContent = '…';
      fetch('/api/langue', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ langue: l }) })
        .then(function () { try { localStorage.setItem(CLE, l); } catch (e) { } location.reload(); })
        .catch(function () { location.reload(); });
    };
    h.appendChild(b);
  }
  if (document.readyState === 'loading') { document.addEventListener('DOMContentLoaded', bouton); } else { bouton(); }
  window.I18N = { trad: trad, dico: dico };
}());
