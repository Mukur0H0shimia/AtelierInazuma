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
  }
  // le lecteur natif (vraie fenêtre devant la page) se cache tant que la fenêtre est ouverte (app.js : majCacheNatif)
  function natif() { try { if (typeof majCacheNatif === 'function') { majCacheNatif(); } } catch (e) { } }
  window.ouvrirParametres = function () { majFenetre(); fenetre().classList.add('ouvert'); natif(); };

  window.addEventListener('load', function () {
    var h = document.querySelector('header');
    if (h && !document.getElementById('bouton-parametres')) {
      var b = document.createElement('button'); b.id = 'bouton-parametres'; b.textContent = '⚙'; b.title = 'Paramètres : couleurs, musique';
      b.onclick = window.ouvrirParametres; h.appendChild(b);
    }
    if (P.musique) { demarrer(); }        // la fenêtre de l'Atelier (WebView2) laisse souvent jouer sans geste
  });
})();
