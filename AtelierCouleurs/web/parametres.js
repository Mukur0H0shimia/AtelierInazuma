// (22/11/2026, idée de muku : « des paramètres, les gens pourront choisir » + « une petite musique de fond »)
// ⚙ Paramètres : palette de l'écran d'édition (html[data-theme], style.css fin) et musique de fond (thème de l'écran titre
// du jeu, lu dans le jeu de la personne : moteur/musique.py). Gardés par le serveur dans config.json : la mémoire du
// navigateur change avec le port, le choix se serait perdu.
// Chargé dans <head> : la palette est posée avant le premier affichage (pas d'éclair de l'ancienne couleur).
(function () {
  'use strict';
  var P = { theme: 'jeu', musique: false, volume: 0.35 };
  try {
    var x = new XMLHttpRequest();
    x.open('GET', '/api/parametres', false); x.send();
    if (x.status === 200) { P = JSON.parse(x.responseText); }
  } catch (e) { /* serveur absent : palette d'origine */ }
  function poserTheme() { document.documentElement.setAttribute('data-theme', P.theme || 'jeu'); }
  poserTheme();

  function garder(changes) {
    for (var k in changes) { P[k] = changes[k]; }
    try {
      fetch('/api/parametres', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(changes) });
    } catch (e) { /* gardé pour cette séance seulement */ }
  }

  // ------------------------------------------------------------------ musique (Web Audio : boucle exacte du jeu)
  var M = { ctx: null, gain: null, src: null, buf: null, info: null, charge: null, etat: '' };
  var JOUENT = new Set();                 // sons et vidéos de l'Atelier en train de jouer (la musique se tait)
  var jouer0 = HTMLMediaElement.prototype.play;
  HTMLMediaElement.prototype.play = function () {
    var el = this;
    if (!el.__suiviMusique) {
      el.__suiviMusique = true;
      ['pause', 'ended', 'emptied', 'error'].forEach(function (ev) { el.addEventListener(ev, function () { JOUENT.delete(el); }); });
    }
    JOUENT.add(el);
    return jouer0.apply(el, arguments);
  };
  function occupe() {
    var natif = false;
    try { natif = typeof NATIF !== 'undefined' && !!(NATIF.actif || NATIF.lance); } catch (e) { }
    return natif || JOUENT.size > 0;
  }
  function etatMusique(t) { M.etat = t; var e = document.getElementById('p-musique-etat'); if (e) { e.textContent = t; } }
  function charger() {
    if (M.charge) { return M.charge; }
    etatMusique('Préparation de la musique…');
    M.charge = fetch('/api/musique').then(function (r) { return r.json(); }).then(function (info) {
      if (!info.ok) { throw new Error(info.erreur || 'musique indisponible'); }
      M.info = info;
      return fetch('/api/musique.ogg');
    }).then(function (r) { return r.arrayBuffer(); }).then(function (ab) {
      return new Promise(function (ok, ko) { M.ctx.decodeAudioData(ab, ok, ko); });
    }).then(function (buf) { M.buf = buf; etatMusique(''); return buf; })
      .catch(function (e) { M.charge = null; etatMusique('Musique indisponible : ' + (e && e.message || e)); throw e; });
    return M.charge;
  }
  function demarrer() {
    if (!P.musique || M.src) { return; }
    if (!M.ctx) {
      var C = window.AudioContext || window.webkitAudioContext; if (!C) { return; }
      M.ctx = new C(); M.gain = M.ctx.createGain(); M.gain.gain.value = 0; M.gain.connect(M.ctx.destination);
    }
    if (M.ctx.state === 'suspended') { M.ctx.resume().catch(function () { }); }
    charger().then(function (buf) {
      if (!P.musique || M.src) { return; }
      var s = M.ctx.createBufferSource(); s.buffer = buf; s.loop = true;
      var i = M.info || {};
      if (i.debut != null && i.fin > i.debut && i.debut < buf.duration) { s.loopStart = i.debut; s.loopEnd = Math.min(i.fin, buf.duration); }
      s.connect(M.gain); s.start(); M.src = s;
    }).catch(function () { });
  }
  function arreter() {
    if (M.src) { try { M.src.stop(); } catch (e) { } M.src.disconnect(); M.src = null; }
  }
  // volume voulu : coupé pendant la lecture d'une technique (son du lecteur, voix, vidéo du jeu), fondu doux
  setInterval(function () {
    if (!M.gain) { return; }
    var cible = P.musique ? (occupe() ? 0 : P.volume) : 0;
    M.gain.gain.setTargetAtTime(cible, M.ctx.currentTime, 0.25);
  }, 250);
  // le navigateur ne laisse jouer un son qu'après un geste : premier clic / touche
  function geste() { if (P.musique) { demarrer(); } }
  window.addEventListener('pointerdown', geste, true);
  window.addEventListener('keydown', geste, true);

  // ------------------------------------------------------------------ fenêtre ⚙ Paramètres
  var PALETTES = [
    { id: 'jeu', nom: 'Comme le jeu', c: ['#9fd2ee', '#1d6fd6', '#2fe6dc', '#f26a17'] },     // (23/11) refonte : menus du jeu
    { id: 'or', nom: "Doré (ancien)", c: ['#f26a17', '#b8903f', '#2cc35c', '#2f86ff'] },
    { id: 'sobre', nom: 'Sobre, comme le jeu', c: ['#1c2226', '#2a353b', '#e9eef0', '#b8903f'] },
    { id: 'bleu', nom: 'Bleu Inazuma', c: ['#1c2226', '#1561c9', '#2aa6f2', '#b8903f'] },
    { id: 'turquoise', nom: 'Ardoise et turquoise', c: ['#1c2226', '#17534d', '#23a08f', '#3fe3c6'] }];

  function fenetre() {
    var f = document.getElementById('parametres');
    if (f) { return f; }
    f = document.createElement('div'); f.id = 'parametres';
    f.innerHTML = '<div class="p-boite" role="dialog" aria-label="Paramètres">'
      + '<div class="p-titre"><span>⚙ Paramètres</span><button id="p-fermer" title="Fermer">×</button></div>'
      + '<h3 data-pas-traduire>Langue · Language · Idioma</h3><div class="p-langues" id="p-langues" data-pas-traduire></div>'
      + '<h3>Couleurs de l\'écran</h3><div class="p-palettes" id="p-palettes"></div>'
      + '<p class="p-note">L\'accueil (Mes créations) garde les couleurs du menu du jeu.</p>'
      + '<h3>Musique de fond</h3>'
      + '<div class="p-ligne"><label><input type="checkbox" id="p-musique"> Thème de l\'écran titre du jeu</label></div>'
      + '<div class="p-ligne"><label>Volume <input type="range" id="p-volume" min="0" max="1" step="0.05"></label></div>'
      + '<p class="p-note">Elle se coupe toute seule pendant la lecture d\'une technique. Lue dans ton jeu, rien n\'est copié.</p>'
      + '<p class="p-note" id="p-musique-etat"></p>'
      + '<h3>Mes polices</h3>'
      + '<div class="p-ligne"><button id="p-police-importer">➕ Importer une police (.ttf / .otf)</button></div>'
      + '<div id="p-polices"></div>'
      + '<p class="p-note">Proposées dans les bannières, les numéros et noms des maillots et l\'outil Texte du mode dessin.</p>'
      + '<h3>Dossier du jeu</h3>'
      + '<p class="p-note">« Installer » met tes créations dans le dossier mods de ce jeu. Choisis celui où se trouve VRFW (celui de ton gestionnaire de mods).</p>'
      + '<div id="p-jeux"></div>'
      + '<div class="p-ligne"><input id="p-jeu-autre" placeholder="Autre dossier (celui de nie.exe)…"><button id="p-jeu-utiliser">Utiliser</button></div>'
      + '<p class="p-note" id="p-jeu-etat"></p>'
      + '<h3>Corbeille</h3>'
      + '<p class="p-note">Ce que tu supprimes (projets, créations, maillots) est rangé à part, jamais effacé : tu peux le remettre, ou l\'effacer pour de bon pour gagner de la place.</p>'
      + '<div class="p-ligne"><button id="p-corb-ouvrir">🗑 Ouvrir la corbeille</button><span class="p-taille" id="p-corb-taille" data-pas-traduire></span></div>'
      + '<h3>Cache</h3>'
      + '<p class="p-note">Ce que l\'Atelier a déjà lu du jeu et des mods, pour aller plus vite. Le vider libère de la place ; il est refait au besoin (un peu plus lent la première fois). Le terrain des cinématiques est gardé.</p>'
      + '<div class="p-ligne"><button id="p-cache-vider">Vider le cache (sauf le terrain)</button><span class="p-taille" id="p-cache-taille" data-pas-traduire></span></div>'
      + '<p class="p-note" id="p-cache-etat"></p>'
      + '<div class="p-bas"><button id="p-ok" class="primaire">OK</button></div></div>';
    document.body.appendChild(f);
    var L = f.querySelector('#p-palettes');
    PALETTES.forEach(function (p) {
      var b = document.createElement('button'); b.className = 'p-palette'; b.dataset.theme = p.id;
      b.innerHTML = '<div class="p-nuancier">' + p.c.map(function (c) { return '<i style="background:' + c + '"></i>'; }).join('') + '</div><span></span>';
      b.querySelector('span').textContent = p.nom;
      b.onclick = function () { garder({ theme: p.id }); poserTheme(); majFenetre(); };
      L.appendChild(b);
    });
    f.querySelector('#p-musique').onchange = function () {
      garder({ musique: this.checked });
      if (this.checked) { demarrer(); } else { arreter(); }
    };
    f.querySelector('#p-volume').oninput = function () { garder({ volume: +this.value }); };
    // (22/11, demande de muku) choix de la langue : un bouton par langue, écrit dans sa langue, la langue actuelle en surbrillance
    var LL = f.querySelector('#p-langues');
    (window.LANGUES_ATELIER || []).forEach(function (x) {
      var b = document.createElement('button'); b.className = 'p-langue'; b.dataset.langue = x.code;
      b.innerHTML = '<b>' + x.code.toUpperCase() + '</b><span></span>'; b.querySelector('span').textContent = x.nom;
      b.onclick = function () { if (window.choisirLangue) { b.classList.add('attente'); window.choisirLangue(x.code); } };
      LL.appendChild(b);
    });
    f.querySelector('#p-police-importer').onclick = function () { window.importerPolice().then(majFenetre); };
    f.querySelector('#p-jeu-utiliser').onclick = function () { choisirJeu(f.querySelector('#p-jeu-autre').value); };
    f.querySelector('#p-corb-ouvrir').onclick = ouvrirCorbeille;
    f.querySelector('#p-cache-vider').onclick = viderCache;
    var fermer = function () { f.classList.remove('ouvert'); natif(); };
    f.querySelector('#p-fermer').onclick = fermer; f.querySelector('#p-ok').onclick = fermer;
    f.addEventListener('pointerdown', function (ev) { if (ev.target === f) { fermer(); } });
    document.addEventListener('keydown', function (ev) { if (ev.key === 'Escape' && f.classList.contains('ouvert')) { fermer(); } });
    return f;
  }
  function majFenetre() {
    var f = fenetre();
    f.querySelectorAll('.p-langue').forEach(function (b) { b.classList.toggle('sel', b.dataset.langue === (window.ATELIER_LANGUE || 'fr')); });
    f.querySelectorAll('.p-palette').forEach(function (b) { b.classList.toggle('sel', b.dataset.theme === (P.theme || 'jeu')); });
    f.querySelector('#p-musique').checked = !!P.musique;
    f.querySelector('#p-volume').value = P.volume;
    etatMusique(M.etat);
    var L = f.querySelector('#p-polices'); L.innerHTML = '';
    if (!PP.length) { L.innerHTML = '<p class="p-note">Aucune pour l\'instant.</p>'; }
    PP.forEach(function (p) {
      var d = document.createElement('div'); d.className = 'p-ligne p-police';
      var n = document.createElement('span'); n.textContent = p.nom; n.style.fontFamily = '"' + p.nom + '", sans-serif'; n.style.fontSize = '20px';
      var x = document.createElement('button'); x.textContent = '🗑'; x.title = 'Retirer cette police';
      x.onclick = function () {
        if (!confirm('Retirer la police « ' + p.nom + ' » de l\'Atelier ? (ce qui est déjà fait avec ne change pas)')) { return; }
        fetch('/api/police_retirer', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ fichier: p.fichier }) })
          .then(function () { return chargerPolicesPerso(); }).then(majFenetre);
      };
      d.appendChild(n); d.appendChild(x); L.appendChild(d);
    });
    chargerJeux(); chargerTailles();
  }

  // ------------------------------------------------------------------ (23/11, demande de muku) CORBEILLE et CACHE
  // voir et remettre ce qui a été supprimé (projets/corbeille, sortie/<mod>/_retires, maillots retirés), l'effacer pour de bon ;
  // vider le cache sauf le terrain (moteur/corbeille.py)
  function api(u, corps) {
    return fetch(u, corps ? { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(corps) } : undefined)
      .then(function (r) { return r.json(); });
  }
  function enOctets(n) {
    var fr = (window.ATELIER_LANGUE || 'fr') === 'fr';
    if (n >= 1073741824) { return (n / 1073741824).toFixed(1).replace('.', fr ? ',' : '.') + (fr ? ' Go' : ' GB'); }
    if (n >= 1048576) { return Math.round(n / 1048576) + (fr ? ' Mo' : ' MB'); }
    return Math.max(1, Math.round(n / 1024)) + (fr ? ' Ko' : ' KB');
  }
  function enDate(t) {
    if (!t) { return ''; }
    var d = new Date(t); if (isNaN(d)) { return t; }
    return d.toLocaleString(window.ATELIER_LANGUE || 'fr', { day: '2-digit', month: '2-digit', year: 'numeric', hour: '2-digit', minute: '2-digit' });
  }
  function chargerTailles() {
    var c = document.getElementById('p-cache-taille'), t = document.getElementById('p-corb-taille');
    if (c) { c.textContent = '…'; }
    api('/api/cache_taille').then(function (r) { if (c) { c.textContent = enOctets(r.videable || 0); } }).catch(function () { if (c) { c.textContent = ''; } });
    api('/api/corbeille').then(function (r) { if (t) { t.textContent = r.elements.length + ' · ' + enOctets(r.taille || 0); } }).catch(function () { });
  }
  function viderCache() {
    var e = document.getElementById('p-cache-etat');
    if (!confirm('Vider le cache de l\'Atelier (sauf le terrain) ?\nRien de ce que tu as créé n\'est touché. Ce qui est effacé sera relu du jeu au besoin.')) { return; }
    e.textContent = 'Vidage du cache…';
    api('/api/cache_vider', {}).then(function (r) {
      e.textContent = 'Libéré : ' + enOctets(r.libere || 0) + '. Relance l\'Atelier pour repartir proprement.'
        + (r.bloques && r.bloques.length ? ' Utilisé en ce moment, gardé : ' + r.bloques.join(', ') + '.' : '');
      chargerTailles();
    }).catch(function (x) { e.textContent = String(x && x.message || x); });
  }
  var CORB = { filtre: '', liste: [] };
  var GENRES_CORB = { projet: 'Projet', creation: 'Création', maillot: 'Maillot' };
  function boiteCorbeille() {
    var d = document.getElementById('corbeille');
    if (d) { return d; }
    d = document.createElement('div'); d.id = 'corbeille';
    d.innerHTML = '<div class="p-boite c-boite" role="dialog" aria-label="Corbeille">'
      + '<div class="p-titre"><span>🗑 Corbeille</span><button class="c-fermer" title="Fermer">×</button></div>'
      + '<div class="c-filtres"><button data-f="" class="sel">Tout</button><button data-f="projet">Projets</button><button data-f="creation">Créations</button><button data-f="maillot">Maillots</button>'
      + '<span class="c-total" data-pas-traduire></span><button class="c-vider">Tout supprimer définitivement</button></div>'
      + '<p class="p-note">« Restaurer » remet l\'élément là où il était. « Supprimer définitivement » l\'efface pour de bon (place libérée).</p>'
      + '<div class="c-liste"></div><p class="p-note c-etat"></p>'
      + '<div class="p-bas"><button class="primaire c-ok">OK</button></div></div>';
    document.body.appendChild(d);
    var fermer = function () { d.classList.remove('ouvert'); chargerTailles(); };
    d.querySelector('.c-fermer').onclick = fermer; d.querySelector('.c-ok').onclick = fermer;
    d.addEventListener('pointerdown', function (ev) { if (ev.target === d) { fermer(); } });
    document.addEventListener('keydown', function (ev) { if (ev.key === 'Escape' && d.classList.contains('ouvert')) { ev.stopPropagation(); fermer(); } }, true);
    d.querySelectorAll('.c-filtres [data-f]').forEach(function (b) {
      b.onclick = function () { CORB.filtre = b.dataset.f; d.querySelectorAll('.c-filtres [data-f]').forEach(function (x) { x.classList.toggle('sel', x === b); }); dessinerCorbeille(); };
    });
    d.querySelector('.c-vider').onclick = function () {
      var l = CORB.liste.filter(function (x) { return !CORB.filtre || x.genre === CORB.filtre; });
      if (!l.length) { return; }
      var tot = l.reduce(function (a, x) { return a + (x.taille || 0); }, 0);
      if (!confirm('Supprimer définitivement ' + l.length + ' élément(s) (' + enOctets(tot) + ') ?\nOn ne pourra plus les restaurer.')) { return; }
      etatCorbeille('Suppression…');
      api('/api/corbeille', { action: 'vider', ids: l.map(function (x) { return x.id; }) }).then(function (r) {
        etatCorbeille('Libéré : ' + enOctets(r.libere || 0) + (r.erreurs && r.erreurs.length ? ' — pas supprimé : ' + r.erreurs.join(' ; ') : ''));
        chargerCorbeille();
      });
    };
    return d;
  }
  function etatCorbeille(t) { var e = document.querySelector('#corbeille .c-etat'); if (e) { e.textContent = t; } }
  function dessinerCorbeille() {
    var d = boiteCorbeille(), L = d.querySelector('.c-liste'); L.innerHTML = '';
    var l = CORB.liste.filter(function (x) { return !CORB.filtre || x.genre === CORB.filtre; });
    d.querySelector('.c-total').textContent = l.length + ' · ' + enOctets(l.reduce(function (a, x) { return a + (x.taille || 0); }, 0));
    if (!l.length) { L.innerHTML = '<p class="p-note c-vide">La corbeille est vide.</p>'; return; }
    l.forEach(function (x) {
      var r = document.createElement('div'); r.className = 'c-ligne';
      var im = document.createElement('div'); im.className = 'c-image';
      if (x.vignette) { im.style.backgroundImage = 'url("' + x.vignette + '")'; } else { im.textContent = x.genre === 'maillot' ? '👕' : x.genre === 'projet' ? '✎' : '★'; }
      var t = document.createElement('div'); t.className = 'c-texte';
      var b = document.createElement('b'); b.textContent = x.titre; b.setAttribute('data-pas-traduire', '');
      var g = document.createElement('span'); g.className = 'c-genre'; g.textContent = GENRES_CORB[x.genre] || x.genre;
      var s = document.createElement('small'); s.setAttribute('data-pas-traduire', '');
      s.textContent = [x.mod, x.onglet, enDate(x.supprime), enOctets(x.taille || 0)].filter(Boolean).join(' · ');
      t.appendChild(g); t.appendChild(b); t.appendChild(s);
      if (x.images_seules) {
        var n2 = document.createElement('small'); n2.className = 'c-alerte'; n2.textContent = 'Ancien maillot : seules ses images restent, on ne peut que les effacer.';
        t.appendChild(n2);
      } else if (x.genre === 'creation' && !x.restaurable) {
        var n = document.createElement('small'); n.className = 'c-alerte'; n.textContent = 'Suppression ancienne : sa fiche manque, on ne peut que l\'effacer.';
        t.appendChild(n);
      }
      var bt = document.createElement('div'); bt.className = 'c-boutons';
      var re = document.createElement('button'); re.className = 'primaire'; re.textContent = 'Restaurer';
      re.disabled = x.genre !== 'projet' && !x.restaurable;
      re.onclick = function () {
        re.disabled = true; etatCorbeille('Restauration…');
        api('/api/corbeille', { action: 'restaurer', id: x.id }).then(function (q) {
          etatCorbeille(q.ok ? (q.message || 'Restauré.') : 'Pas restauré : ' + q.erreur);
          chargerCorbeille();
          if (q.ok && typeof chargerHub === 'function' && document.getElementById('page-hub')) { chargerHub(); }
        });
      };
      var su = document.createElement('button'); su.textContent = 'Supprimer définitivement';
      su.onclick = function () {
        if (!confirm('Supprimer définitivement « ' + x.titre + ' » (' + enOctets(x.taille || 0) + ') ?\nOn ne pourra plus le restaurer.')) { return; }
        api('/api/corbeille', { action: 'supprimer', id: x.id }).then(function (q) {
          etatCorbeille(q.ok ? 'Libéré : ' + enOctets(q.libere || 0) : 'Pas supprimé : ' + q.erreur); chargerCorbeille();
        });
      };
      bt.appendChild(re); bt.appendChild(su);
      r.appendChild(im); r.appendChild(t); r.appendChild(bt); L.appendChild(r);
    });
  }
  function chargerCorbeille() {
    var L = boiteCorbeille().querySelector('.c-liste'); if (!CORB.liste.length) { L.innerHTML = '<p class="p-note">Lecture…</p>'; }
    return api('/api/corbeille').then(function (r) { CORB.liste = r.elements || []; dessinerCorbeille(); })
      .catch(function (e) { etatCorbeille(String(e && e.message || e)); });
  }
  function ouvrirCorbeille() { boiteCorbeille().classList.add('ouvert'); etatCorbeille(''); chargerCorbeille(); }
  window.ouvrirCorbeille = ouvrirCorbeille;

  // ------------------------------------------------------------------ (22/11, retour d'un joueur : créations « Installed » mais
  // absentes de son gestionnaire de mods) le dossier du jeu où « Installer » met les mods, et les autres installations trouvées
  function etatJeu(t) { var e = document.getElementById('p-jeu-etat'); if (e) { e.textContent = t; } }
  function afficherJeux(r) {
    var L = document.getElementById('p-jeux'); if (!L) { return; }
    L.innerHTML = '';
    (r.liste || []).forEach(function (j) {
      var d = document.createElement('label'); d.className = 'p-ligne p-jeu' + (j.dossier === r.actuel ? ' sel' : '');
      var c = document.createElement('input'); c.type = 'radio'; c.name = 'p-jeu'; c.checked = j.dossier === r.actuel;
      c.onchange = function () { choisirJeu(j.dossier); };
      var t = document.createElement('span'); t.className = 'p-jeu-texte';
      var ch = document.createElement('b'); ch.textContent = j.dossier;
      var s = document.createElement('small');
      s.textContent = (j.vrfw ? 'VRFW ✓' : 'sans VRFW') + ' · ' + j.nb_mods + ' mod(s)'
        + (j.mes_mods.length ? ' · tes mods : ' + j.mes_mods.join(', ') : '');
      if (!j.vrfw) { s.className = 'p-jeu-alerte'; }
      t.appendChild(ch); t.appendChild(s); d.appendChild(c); d.appendChild(t); L.appendChild(d);
    });
    if (!(r.liste || []).length) { L.innerHTML = '<p class="p-note">Aucune installation du jeu trouvée.</p>'; }
    etatJeu(r.actuel && r.demarrage && r.actuel !== r.demarrage
      ? '« Installer » utilise déjà ce dossier. Relance l\'Atelier pour que ses onglets lisent aussi les mods de ce jeu.' : '');
  }
  function chargerJeux() {
    fetch('/api/dossier_jeu').then(function (r) { return r.json(); }).then(afficherJeux).catch(function () { });
  }
  function choisirJeu(d) {
    if (!d || !String(d).trim()) { return; }
    fetch('/api/dossier_jeu', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ dossier: String(d).trim() }) })
      .then(function (r) { return r.json(); })
      .then(function (r) { if (!r.ok) { etatJeu(r.erreur); return; } afficherJeux(r); })
      .catch(function (e) { etatJeu(String(e && e.message || e)); });
  }

  // ------------------------------------------------------------------ (22/11, demande d'un joueur) polices importées
  // fichier .ttf / .otf -> AtelierCouleurs/polices (serveur), chargé ici sous son nom (FontFace) : utilisable partout dans la page
  var PP = [];
  function enregistrerPolice(p) {
    try {
      var ff = new FontFace(p.nom, 'url(/police/' + encodeURIComponent(p.fichier) + ')');
      document.fonts.add(ff); return ff.load().catch(function () { });
    } catch (e) { return Promise.resolve(); }
  }
  function chargerPolicesPerso() {
    return fetch('/api/polices_perso').then(function (r) { return r.json(); }).then(function (L) {
      var neuves = (L || []).filter(function (p) { return !PP.some(function (q) { return q.fichier === p.fichier; }); });
      PP = L || [];
      return Promise.all(neuves.map(enregistrerPolice));
    }).catch(function () { }).then(function () { document.dispatchEvent(new Event('polices-perso')); return PP; });
  }
  window.policesPerso = function () { return PP; };
  window.importerPolice = function () {
    return new Promise(function (fini) {
      var i = document.createElement('input'); i.type = 'file'; i.accept = '.ttf,.otf';
      i.onchange = function () {
        var f = i.files && i.files[0]; if (!f) { return fini(null); }
        var rd = new FileReader();
        rd.onload = function () {
          fetch('/api/police_importer', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ nom: f.name, data: rd.result }) })
            .then(function (r) { return r.json(); }).then(function (r) {
              if (!r.ok) { alert('Police refusée : ' + r.erreur); return fini(null); }
              chargerPolicesPerso().then(function () { fini(PP.filter(function (p) { return p.fichier === r.fichier; })[0] || null); });
            }).catch(function () { fini(null); });
        };
        rd.readAsDataURL(f);
      };
      i.click();
    });
  };
  // une liste de polices de la page : groupe « Mes polices » + « ➕ Importer une police… » (choisie tout de suite après)
  // valeur(p) : ce que la liste attend (nom de fichier pour les bannières, nom de la police ailleurs)
  window.brancherPolices = function (sel, valeur) {
    if (!sel) { return; }
    var remplir = function () {
      var garde = sel.value;
      Array.prototype.slice.call(sel.querySelectorAll('.mes-polices')).forEach(function (o) { o.remove(); });
      var g = document.createElement('optgroup'); g.label = window.trad ? window.trad('Mes polices') : 'Mes polices'; g.className = 'mes-polices';
      PP.forEach(function (p) { g.appendChild(new Option(p.nom, valeur(p))); });
      g.appendChild(new Option('➕ Importer une police…', '__importer__'));
      sel.appendChild(g);
      if (garde && garde !== '__importer__') { sel.value = garde; }
      if (sel.dataset.voulue && Array.prototype.some.call(sel.options, function (o) { return o.value === sel.dataset.voulue; })) { sel.value = sel.dataset.voulue; delete sel.dataset.voulue; }
    };
    remplir();
    if (sel.__polices) { return; }
    sel.__polices = true;
    var avant = sel.value;
    sel.addEventListener('focus', function () { avant = sel.value; });
    sel.addEventListener('pointerdown', function () { if (sel.value !== '__importer__') { avant = sel.value; } });
    // une liste envoie « input » puis « change » : l'import part au premier, le second est tu
    var enCours = false, taire = false;
    var choix = function (ev) {
      if (taire) { ev.stopImmediatePropagation(); return; }
      if (sel.value !== '__importer__') { avant = sel.value; return; }
      ev.stopImmediatePropagation(); sel.value = avant;
      taire = true; setTimeout(function () { taire = false; }, 0);
      if (enCours) { return; }
      enCours = true;
      window.importerPolice().then(function (p) {
        enCours = false; taire = false;            // (réponse rapide : le « silence » du 2e événement ne doit pas taire le choix)
        if (!p) { return; }
        sel.value = valeur(p);
        sel.dispatchEvent(new Event('input', { bubbles: true })); sel.dispatchEvent(new Event('change', { bubbles: true }));
      });
    };
    sel.addEventListener('input', choix, true); sel.addEventListener('change', choix, true);
    document.addEventListener('polices-perso', remplir);
  };
  chargerPolicesPerso();
  // le lecteur natif (vraie fenêtre devant la page) se cache tant que la fenêtre est ouverte (app.js : majCacheNatif)
  function natif() { try { if (typeof majCacheNatif === 'function') { majCacheNatif(); } } catch (e) { } }
  window.ouvrirParametres = function () { majFenetre(); fenetre().classList.add('ouvert'); natif(); };

  window.addEventListener('load', function () {
    var h = document.querySelector('header');
    if (h && !document.getElementById('bouton-parametres')) {
      var b = document.createElement('button'); b.id = 'bouton-parametres'; b.textContent = '⚙'; b.title = 'Paramètres : couleurs, musique, polices, dossier du jeu, corbeille, cache';
      b.onclick = window.ouvrirParametres; h.appendChild(b);
    }
    // (27/11, demande de muku) « Rejoins mon serveur » : le Discord de muku. La fenêtre de l'Atelier (WebView2) n'ouvre pas de
    // lien : le serveur l'ouvre dans le navigateur (/api/ouvrir_discord, adresse fixe) ; dans un navigateur, nouvel onglet.
    if (h && !document.getElementById('bouton-discord')) {
      var d = document.createElement('button'); d.id = 'bouton-discord'; d.title = 'Rejoins mon serveur Discord';
      d.innerHTML = '<svg viewBox="0 0 24 24" width="16" height="16" aria-hidden="true"><path fill="currentColor" d="M20.3 4.4A19.6 19.6 0 0 0 15.4 3l-.6 1.3a18 18 0 0 0-5.6 0L8.6 3a19.5 19.5 0 0 0-4.9 1.4C.6 9 0 13.6.3 18.1a19.7 19.7 0 0 0 6 3l1.3-2.1c-.7-.3-1.4-.6-2-1l.5-.4a14 14 0 0 0 11.8 0l.5.4c-.6.4-1.3.7-2 1l1.3 2.1a19.6 19.6 0 0 0 6-3c.5-5.2-.8-9.7-3.4-13.7ZM8.5 15.4c-1.2 0-2.1-1.1-2.1-2.4s.9-2.4 2.1-2.4 2.2 1.1 2.1 2.4c0 1.3-.9 2.4-2.1 2.4Zm7 0c-1.2 0-2.1-1.1-2.1-2.4s.9-2.4 2.1-2.4 2.2 1.1 2.1 2.4c0 1.3-.9 2.4-2.1 2.4Z"/></svg><span>Rejoins mon serveur</span>';
      d.onclick = function () {
        fetch('/api/ouvrir_discord', { method: 'POST' }).then(function (r) { return r.json(); })
          .then(function (j) { if (!j || !j.ok) { window.open('https://discord.gg/D9DvjdnFVE', '_blank'); } })
          .catch(function () { window.open('https://discord.gg/D9DvjdnFVE', '_blank'); });
      };
      h.insertBefore(d, document.getElementById('bouton-parametres'));
    }
    if (P.musique) { demarrer(); }        // la fenêtre de l'Atelier (WebView2) laisse souvent jouer sans geste
  });
})();
