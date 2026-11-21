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

  // (21/11) textes avec des données : [modèle sur le texte aux espaces réduits, remplacement]
  var MOTIFS = [
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
    [/^Texture déjà colorée \((.+?)\) : la couleur du matériau la MULTIPLIE \(orange × bleu = presque noir\)\. Pour changer la teinte, recolore plutôt la texture \(bloc Textures\) et laisse le matériau blanc\.$/,
     'Already coloured texture ($1): the material colour MULTIPLIES it (orange × blue = almost black). To change the hue, recolour the texture instead (Textures block) and leave the material white.']
  ];

  function trad(s) {
    if (langue !== 'en' || !s) { return s; }
    var brut = s.trim();
    if (!brut) { return s; }
    var t = brut.replace(/\s+/g, ' ');           // le dictionnaire a les espaces réduits
    var d = window.I18N_EN || {};
    var r = d[t];
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
