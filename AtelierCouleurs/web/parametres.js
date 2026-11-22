// (22/11/2026, idée de muku : « des paramètres, les gens pourront choisir » + « une petite musique de fond »)
// ⚙ Paramètres : palette de l'écran d'édition (html[data-theme], style.css fin) et musique de fond (thème de l'écran titre
// du jeu, lu dans le jeu de la personne : moteur/musique.py). Gardés par le serveur dans config.json : la mémoire du
// navigateur change avec le port, le choix se serait perdu.
// Chargé dans <head> : la palette est posée avant le premier affichage (pas d'éclair de l'ancienne couleur).
(function () {
  'use strict';
  var P = { theme: 'or', musique: false, volume: 0.35 };
  try {
    var x = new XMLHttpRequest();
    x.open('GET', '/api/parametres', false); x.send();
    if (x.status === 200) { P = JSON.parse(x.responseText); }
  } catch (e) { /* serveur absent : palette d'origine */ }
  function poserTheme() { document.documentElement.setAttribute('data-theme', P.theme || 'or'); }
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
    { id: 'or', nom: "Doré (d'origine)", c: ['#f26a17', '#b8903f', '#2cc35c', '#2f86ff'] },
    { id: 'sobre', nom: 'Sobre, comme le jeu', c: ['#1c2226', '#2a353b', '#e9eef0', '#b8903f'] },
    { id: 'bleu', nom: 'Bleu Inazuma', c: ['#1c2226', '#1561c9', '#2aa6f2', '#b8903f'] },
    { id: 'turquoise', nom: 'Ardoise et turquoise', c: ['#1c2226', '#17534d', '#23a08f', '#3fe3c6'] }];

  function fenetre() {
    var f = document.getElementById('parametres');
    if (f) { return f; }
    f = document.createElement('div'); f.id = 'parametres';
    f.innerHTML = '<div class="p-boite" role="dialog" aria-label="Paramètres">'
      + '<div class="p-titre"><span>⚙ Paramètres</span><button id="p-fermer" title="Fermer">×</button></div>'
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
    f.querySelector('#p-police-importer').onclick = function () { window.importerPolice().then(majFenetre); };
    f.querySelector('#p-jeu-utiliser').onclick = function () { choisirJeu(f.querySelector('#p-jeu-autre').value); };
    var fermer = function () { f.classList.remove('ouvert'); natif(); };
    f.querySelector('#p-fermer').onclick = fermer; f.querySelector('#p-ok').onclick = fermer;
    f.addEventListener('pointerdown', function (ev) { if (ev.target === f) { fermer(); } });
    document.addEventListener('keydown', function (ev) { if (ev.key === 'Escape' && f.classList.contains('ouvert')) { fermer(); } });
    return f;
  }
  function majFenetre() {
    var f = fenetre();
    f.querySelectorAll('.p-palette').forEach(function (b) { b.classList.toggle('sel', b.dataset.theme === (P.theme || 'or')); });
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
    chargerJeux();
  }

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
      var g = document.createElement('optgroup'); g.label = 'Mes polices'; g.className = 'mes-polices';
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
      var b = document.createElement('button'); b.id = 'bouton-parametres'; b.textContent = '⚙'; b.title = 'Paramètres : couleurs, musique, polices, dossier du jeu';
      b.onclick = window.ouvrirParametres; h.appendChild(b);
    }
    if (P.musique) { demarrer(); }        // la fenêtre de l'Atelier (WebView2) laisse souvent jouer sans geste
  });
})();
