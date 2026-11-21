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
