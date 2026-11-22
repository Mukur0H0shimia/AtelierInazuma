// Écran de chargement du 1er lancement — first-run loading screen.
// Au 1er lancement, le serveur prépare l'index des textures du jeu (lu dans ses paquets : quelques minutes, une seule
// fois). Pendant ce temps l'interface ne répond pas encore : cet écran le dit, avec l'avancement (/api/chargement).
(function () {
  'use strict';
  var LG = window.ATELIER_LANGUE || document.documentElement.lang;
  var EN = LG === 'en';
  var T = LG === 'es' ? {                      // (22/11) espagnol
    titre: 'Preparando el Atelier',
    lecture: 'Leyendo los archivos del juego…',
    textures: 'Índice de las texturas del juego',
    mods: 'Leyendo tus mods…',
    une_fois: 'Solo la primera vez: la próxima vez el Atelier se abre en unos segundos.',
    reste: function (m) { return m <= 1 ? 'queda 1 minuto aprox.' : 'quedan unos ' + m + ' minutos'; },
    fichiers: function (a, b) { return a.toLocaleString('es') + ' / ' + b.toLocaleString('es') + ' archivos'; },
    astuces: [
      'No hay nada que extraer: el Atelier lee el juego directamente en sus paquetes.',
      'Los archivos originales del juego nunca se modifican: cada creación es una copia con un código nuevo.',
      'Tus mods aparecen en las pestañas de siempre, incluso los desactivados.',
      'Idioma arriba a la derecha o en ⚙ Ajustes: los nombres del juego siguen el idioma elegido.'
    ]
  } : EN ? {
    titre: 'Getting the Atelier ready',
    lecture: 'Reading the game files…',
    textures: 'Indexing the game textures',
    mods: 'Reading your mods…',
    une_fois: 'First run only: next time the Atelier opens in a few seconds.',
    reste: function (m) { return m <= 1 ? 'about 1 minute left' : 'about ' + m + ' minutes left'; },
    fichiers: function (a, b) { return a.toLocaleString('en') + ' / ' + b.toLocaleString('en') + ' files'; },
    astuces: [
      'Nothing is extracted: the Atelier reads the game straight from its packs.',
      'The game’s original files are never modified: every creation is a copy with a new code.',
      'Your mods show up in the usual tabs, even the disabled ones.',
      'Language at the top right or in ⚙ Settings: game names follow the chosen language.'
    ]
  } : {
    titre: 'Préparation de l’Atelier',
    lecture: 'Lecture des fichiers du jeu…',
    textures: 'Index des textures du jeu',
    mods: 'Lecture de tes mods…',
    une_fois: 'Seulement au 1er lancement : la prochaine fois, l’Atelier s’ouvre en quelques secondes.',
    reste: function (m) { return m <= 1 ? 'environ 1 minute restante' : 'environ ' + m + ' minutes restantes'; },
    fichiers: function (a, b) { return a.toLocaleString('fr') + ' / ' + b.toLocaleString('fr') + ' fichiers'; },
    astuces: [
      'Rien à extraire : l’Atelier lit le jeu directement dans ses paquets.',
      'Les fichiers d’origine du jeu ne sont jamais modifiés : chaque création est une copie à code neuf.',
      'Tes mods apparaissent dans les onglets habituels, même ceux qui sont désactivés.',
      'Langue en haut à droite ou dans ⚙ Paramètres : les noms du jeu suivent la langue choisie.'
    ]
  };

  var CSS =
    '#chargement{position:fixed;inset:0;z-index:100000;display:flex;align-items:center;justify-content:center;' +
    'background:radial-gradient(ellipse at 50% 35%,#1a1f2b 0%,#0f1117 60%,#0b0d12 100%);color:#e6e8ee;' +
    'font:14px/1.5 "Bahnschrift","Segoe UI",system-ui,sans-serif;opacity:1;transition:opacity .45s ease}' +
    '#chargement.fini{opacity:0;pointer-events:none}' +
    '#chargement .boite{width:min(520px,calc(100vw - 32px));text-align:center}' +
    '#chargement .marque{letter-spacing:4px;font-weight:300;color:#9aa1b2;font-size:15px}' +
    '#chargement .marque b{color:#f0b429;font-weight:700}' +
    '#chargement .eclair{width:46px;height:46px;margin:0 auto 18px;animation:ch-pulse 1.6s ease-in-out infinite}' +
    '#chargement h1{font-size:24px;font-weight:600;margin:6px 0 22px;letter-spacing:.5px}' +
    '#chargement .etape{color:#e6e8ee;margin-bottom:10px;min-height:21px}' +
    '#chargement .barre{height:8px;border-radius:4px;background:#232836;overflow:hidden;position:relative}' +
    '#chargement .plein{height:100%;width:0;background:linear-gradient(90deg,#f0b429,#ffd36b);border-radius:4px;transition:width .4s ease}' +
    '#chargement .barre.vague .plein{width:35%;position:absolute;animation:ch-vague 1.3s ease-in-out infinite}' +
    '#chargement .chiffres{display:flex;justify-content:space-between;color:#9aa1b2;font-size:12.5px;margin-top:8px;min-height:19px;font-variant-numeric:tabular-nums}' +
    '#chargement .une-fois{color:#9aa1b2;font-size:12.5px;margin-top:22px}' +
    '#chargement .astuce{margin-top:26px;padding:12px 16px;border-left:3px solid #f0b429;background:#171a22;text-align:left;' +
    'color:#c9cdd8;font-size:13px;min-height:44px;transition:opacity .35s ease}' +
    '@keyframes ch-vague{0%{left:-35%}100%{left:100%}}' +
    '@keyframes ch-pulse{0%,100%{transform:scale(1);filter:drop-shadow(0 0 0 rgba(240,180,41,0))}50%{transform:scale(1.06);filter:drop-shadow(0 0 10px rgba(240,180,41,.55))}}' +
    '@media (prefers-reduced-motion:reduce){#chargement .eclair,#chargement .barre.vague .plein{animation:none}}';

  var ecran = null, el = {}, debut = null, astuce = 0, minuteur = null;

  function creer() {
    var st = document.createElement('style'); st.textContent = CSS; document.head.appendChild(st);
    ecran = document.createElement('div');
    ecran.id = 'chargement';
    ecran.setAttribute('data-pas-traduire', '');
    ecran.setAttribute('role', 'status');
    ecran.innerHTML =
      '<div class="boite">' +
      '<svg class="eclair" viewBox="0 0 24 24" aria-hidden="true"><path fill="#f0b429" d="M13.5 2 4 13.6h6.2L9 22l10-12.2h-6.3z"/></svg>' +
      '<div class="marque">ATELIER <b>INAZUMA</b></div>' +
      '<h1></h1><div class="etape"></div>' +
      '<div class="barre vague"><div class="plein"></div></div>' +
      '<div class="chiffres"><span class="n"></span><span class="reste"></span></div>' +
      '<div class="une-fois"></div><div class="astuce"></div></div>';
    (document.body || document.documentElement).appendChild(ecran);
    ['h1', '.etape', '.barre', '.plein', '.n', '.reste', '.une-fois', '.astuce'].forEach(function (s) { el[s] = ecran.querySelector(s); });
    el.h1.textContent = T.titre;
    el['.une-fois'].textContent = T.une_fois;
    el['.astuce'].textContent = T.astuces[0];
    minuteur = setInterval(function () {
      astuce = (astuce + 1) % T.astuces.length;
      el['.astuce'].style.opacity = 0;
      setTimeout(function () { el['.astuce'].textContent = T.astuces[astuce]; el['.astuce'].style.opacity = 1; }, 350);
    }, 7000);
  }

  function montrer(e) {
    if (!ecran) { creer(); }
    var fait = e.fait || 0, total = e.total || 0;
    if (total > 0 && fait < total) {
      el['.etape'].textContent = T.textures;
      el['.barre'].classList.remove('vague');
      el['.plein'].style.width = (100 * fait / total).toFixed(1) + '%';
      el['.n'].textContent = T.fichiers(fait, total);
      if (!debut || fait < debut.fait) { debut = { t: Date.now(), fait: fait }; }
      var dt = (Date.now() - debut.t) / 1000, df = fait - debut.fait;
      el['.reste'].textContent = (dt > 8 && df > 0) ? T.reste(Math.ceil((total - fait) / (df / dt) / 60)) : '';
    } else {
      el['.etape'].textContent = total > 0 ? T.mods : T.lecture;
      el['.barre'].classList.add('vague');
      el['.plein'].style.width = '';
      el['.n'].textContent = total > 0 ? T.fichiers(total, total) : '';
      el['.reste'].textContent = '';
    }
  }

  function finir() {
    if (!ecran) { return; }
    clearInterval(minuteur);
    ecran.classList.add('fini');
    setTimeout(function () { if (ecran && ecran.parentNode) { ecran.parentNode.removeChild(ecran); } }, 500);
  }

  function suivre() {
    fetch('/api/chargement').then(function (r) { return r.json(); }).then(function (e) {
      if (e.pret) { finir(); return; }
      montrer(e);
      setTimeout(suivre, 500);
    }).catch(function () { setTimeout(suivre, 1500); });
  }

  if (document.body) { suivre(); } else { document.addEventListener('DOMContentLoaded', suivre); }
})();
