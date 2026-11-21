"""(15/11/2026) Éditeur de textures de l'Atelier Couleurs = COPIE adaptée du studio de l'Atelier Maillots (lib/studio.html,
non modifié) : on garde le moteur de dessin (outils, formes, motifs, texte, image, seau, annuler, zoom) et on retire ce qui est
propre aux maillots (zones du patron, 3D, numéro, relief, portraits)."""
import os, re

_R = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SRC = os.path.join(_R, 'AtelierMaillots', 'lib', 'studio.html')
DST = os.path.join(_R, 'AtelierCouleurs', 'web', 'editeur.html')
s = open(SRC, encoding='utf-8').read()


def entre(a, b):
    i = s.index(a); j = s.index(b, i)
    return s[i:j]


css = entre('<style>', '</style>') + """
/* (15/11/2026) éditeur de textures d'effet */
main { grid-template-columns: 84px 1fr 340px; }
#scene { background-color: #2a2d34; background-image: linear-gradient(45deg, #3a3e47 25%, transparent 25%), linear-gradient(-45deg, #3a3e47 25%, transparent 25%), linear-gradient(45deg, transparent 75%, #3a3e47 75%), linear-gradient(-45deg, transparent 75%, #3a3e47 75%); }
#fond_choix .puce { padding: 4px 8px; }
#apercu { width: 100%; image-rendering: pixelated; border-radius: 8px; display: block; }
/* (15/11/2026) dans le panneau de droite de l'Atelier (la vue 3D reste visible) */
body.panneau header { height: 46px; gap: 8px; padding: 0 8px; }
body.panneau .logo span, body.panneau #nom { display: none; }
body.panneau .bt { padding: 5px 8px; }
body.panneau #etat { min-width: 0; max-width: 140px; overflow: hidden; white-space: nowrap; text-overflow: ellipsis; }
body.panneau main { grid-template-columns: 58px 1fr 250px; height: calc(100% - 46px); }
body.panneau .outil { font-size: 9px; padding: 5px 1px 4px; }
body.panneau .outil svg { width: 20px; height: 20px; }
body.panneau #cote { padding: 6px; gap: 6px; }
body.panneau .carte { padding: 9px; }
body.panneau .palette { grid-template-columns: repeat(8, 1fr); }
body.panneau #aideOutil { white-space: normal; max-width: 90%; text-align: center; font-size: 12px; }
body.panneau #zoombar { flex-wrap: wrap; max-width: calc(100% - 24px); }
body.panneau #survol { display: none; }
.regl .val { min-width: 48px; }
"""

haut = """<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="utf-8">
<title>Dessiner — Atelier Couleurs</title>
""" + css + """</style>
</head>
<body>
<header>
  <div class="logo"><svg viewBox="0 0 24 24"><path d="M13 2 4 14h6l-1 8 9-12h-6z" fill="#ffc83d"/></svg><span>Dessiner sur la texture</span></div>
  <div id="nom"></div>
  <div class="espace"></div>
  <button class="bt" id="b_annuler" title="Annuler (Ctrl+Z)"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M9 14 4 9l5-5"/><path d="M4 9h10a6 6 0 0 1 0 12h-3"/></svg></button>
  <button class="bt" id="b_retablir" title="Rétablir (Ctrl+Y)"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="m15 14 5-5-5-5"/><path d="M20 9H10a6 6 0 0 0 0 12h3"/></svg></button>
  <button class="bt" id="b_origine" title="Revenir à la texture du jeu">Texture du jeu</button>
  <label class="case" title="Chaque trait est envoyé tout de suite à l'aperçu et au lecteur natif"><input type="checkbox" id="direct" checked> En direct</label>
  <span id="etat"></span>
  <button class="bt principal" id="b_enreg" title="Garder ce dessin et fermer (Ctrl+S)"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2"><path d="M5 3h11l3 3v15H5z"/><path d="M8 3v6h8V3M8 21v-7h8v7"/></svg>Garder et fermer</button>
  <button class="bt" id="b_fermer" title="Fermer (Échap)">Fermer</button>
</header>
<main>
  <nav id="outils"></nav>
  <section id="scene">
    <div id="monde">
      <canvas id="c_img"></canvas><canvas id="c_trait"></canvas><canvas id="c_guide"></canvas><canvas id="c_calque"></canvas>
    </div>
    <div id="aideOutil"></div>
    <div id="zoombar">
      <button class="bt" id="z_moins">−</button><span id="zoomtxt">100 %</span><button class="bt" id="z_plus">+</button>
      <button class="bt" id="z_ajuster">Ajuster</button>
      <span class="petit" style="margin-left:6px">Fond :</span><div class="choix" id="fond_choix"></div>
    </div>
    <div id="survol"></div>
    <div id="chargement">Chargement…</div>
  </section>
  <aside id="cote">
    <div class="carte">
      <h3>Couleurs <span class="petit">clic droit sur l'image = pipette</span></h3>
      <div class="couleurs">
        <div class="duo"><div class="pastille" id="p1" title="Couleur principale"></div><div class="pastille" id="p2" title="2e couleur (contours, motifs à 2 couleurs)"></div></div>
        <div class="palette" id="palette"></div>
      </div>
      <div class="ligne"><span class="lib">Personnalisée</span><input type="color" id="perso1"><input type="color" id="perso2"><button class="bt" id="b_echange" title="Échanger les 2 couleurs (X)">⇄</button></div>
      <div class="ligne"><span class="lib">Récentes</span><div class="palette" id="recentes" style="grid-template-columns:repeat(10,1fr)"></div></div>
    </div>
    <div class="carte">
      <h3>Transparence</h3>
      <label class="case" title="Le pinceau, les formes, le texte… ne colorent que là où la texture est déjà visible"><input type="checkbox" id="verrou"> Garder la forme de la texture</label>
      <div class="petit">Les textures d'effet dessinent leur forme avec la transparence (flammes, étincelles…). Coché : tu recolores l'intérieur
        sans déborder. Décoché : tu peux ajouter de nouvelles formes (elles deviennent visibles).</div>
    </div>
    <div class="carte regl">
      <h3>Réglages de l'image</h3>
      <div class="ligne"><span class="lib">Saturation</span><input type="range" id="r_sat" min="0" max="300" value="100"><span class="val" id="v_sat">100 %</span></div>
      <div class="ligne"><span class="lib">Luminosité</span><input type="range" id="r_lum" min="0" max="300" value="100"><span class="val" id="v_lum">100 %</span></div>
      <div class="ligne"><span class="lib">Contraste</span><input type="range" id="r_con" min="0" max="300" value="100"><span class="val" id="v_con">100 %</span></div>
      <div class="ligne"><button class="bt principal" id="r_ok">Valider</button><button class="bt" id="r_non">Remettre à 100 %</button></div>
      <div class="petit">Sur toute la texture, transparence gardée. Aperçu en direct ; Ctrl+Z annule.</div>
    </div>
    <div class="carte" id="options"><h3 id="opt_titre">Outil</h3><div id="opt"></div></div>
    <div class="carte">
      <h3>Taille réelle</h3>
      <canvas id="apercu"></canvas>
      <div class="petit" id="info_tex"></div>
    </div>
  </aside>
</main>
<script>
"use strict";
"""

js_debut = entre('const PALETTE = [', "// =====================================================================================================  état")
js_debut = js_debut.replace("""  ['gomme', 'Gomme', 'E', 'Efface en remettant l\\'image de départ.'],""",
                            """  ['gomme', 'Gomme', 'E', 'Remet la texture du jeu, ou rend transparent (au choix à droite).'],""")
js_debut = js_debut.replace("Clique sur le maillot pour prendre une couleur.", "Clique sur l\\'image pour prendre une couleur.")
js_debut = js_debut.replace("Clique sur une partie du maillot pour la remplir.", "Clique pour remplir la couleur touchée.")
js_debut = js_debut.replace("Clique sur une partie du maillot pour y poser le motif.", "Clique pour poser le motif sur toute l\\'image.")
js_debut = js_debut.replace("Écris ton texte à droite, puis clique sur le maillot pour le poser.", "Écris ton texte à droite, puis clique sur l\\'image pour le poser.")

etat_js = """// =====================================================================================================  état
const P = new URLSearchParams(location.search);
const cle = P.get('k') || '';
const PARENT = window.parent && window.parent !== window ? window.parent : null;
const S = {
  outil: 'pinceau', c1: '#3a7bff', c2: '#ffffff', taille: 8, opacite: 100, durete: 100, zone: 'tout',
  forme: 'etoile', remplissage: 'plein', epaisseur: 3, motif: 'rayures_d', largeur: 6, espacement: 6, angle: 45, rayon: 4,
  texte: 'INAZUMA', police: 'Arial Black', tTaille: 24, tContour: 0, rotation: 0, remplirMode: 'seau', tolerance: 40,
  imgTaille: 64, recentes: [], verrou: true, gommeMode: 'origine', fond: 'damier', pinceauMode: 'peindre',
};
try { Object.assign(S, JSON.parse(localStorage.getItem('editeur_tex_reglages') || '{}')); } catch (e) {}
S.outil = S.outil === 'main' ? 'pinceau' : S.outil; if (S.remplirMode === 'zone') S.remplirMode = 'teinte';
const memo = () => { try { localStorage.setItem('editeur_tex_reglages', JSON.stringify(S)); } catch (e) {} };

const cImg = document.getElementById('c_img'), cTrait = document.getElementById('c_trait'), cCalque = document.getElementById('c_calque'), cGuide = document.getElementById('c_guide');
const xImg = cImg.getContext('2d', { willReadFrequently: true }), xTrait = cTrait.getContext('2d'), xCalque = cCalque.getContext('2d'), xGuide = cGuide.getContext('2d');
const monde = document.getElementById('monde'), scene = document.getElementById('scene');
let W = 0, H = 0, orig = null, sale = false, logo = null;
let annuler = [], retablir = [];
let vue = { s: 1, x: 0, y: 0 };
const etatEl = document.getElementById('etat');
function etat(t, c) { etatEl.textContent = t; etatEl.className = c || ''; }

// pas de zones (patron de maillot) pour une texture d'effet : toute l'image
const masque = () => null, zoneSous = () => null, boiteZone = () => ({ x: 0, y: 0, w: W, h: H });
const choixZone = () => document.createElement('div'), dessinerGuide = () => {};

// =====================================================================================================  aperçu et lecteur en direct
const cApercu = document.getElementById('apercu'), xApercu = cApercu.getContext('2d');
let minuteurDirect = null;
function maj3d(pendantTrait) {
  xApercu.clearRect(0, 0, cApercu.width, cApercu.height); xApercu.drawImage(cImg, 0, 0, cApercu.width, cApercu.height);
  if (pendantTrait) xApercu.drawImage(cTrait, 0, 0, cApercu.width, cApercu.height);
  if (pendantTrait || !document.getElementById('direct').checked) return;    // envoi à l'Atelier : trait fini seulement
  clearTimeout(minuteurDirect); minuteurDirect = setTimeout(envoyer, 250);
}
function envoyer() {
  if (!PARENT || !PARENT.recevoirTextureEditee || !W) return false;
  PARENT.recevoirTextureEditee(cle, xImg.getImageData(0, 0, W, H)); return true;
}

// =====================================================================================================  chargement (texture prise dans l'Atelier)
function charger() {
  const T = PARENT && PARENT.texturePourEditeur ? PARENT.texturePourEditeur(cle) : null;
  if (!T || !T.cur) { document.getElementById('chargement').textContent = 'Texture introuvable : ouvre l\\'éditeur depuis l\\'Atelier.'; return; }
  document.getElementById('nom').textContent = T.nom + '  ·  ' + T.cur.width + ' × ' + T.cur.height;
  W = cImg.width = cTrait.width = cCalque.width = cGuide.width = T.cur.width;
  H = cImg.height = cTrait.height = cCalque.height = cGuide.height = T.cur.height;
  for (const c of [cImg, cTrait, cCalque, cGuide]) { c.style.width = W + 'px'; c.style.height = H + 'px'; }
  monde.style.width = W + 'px'; monde.style.height = H + 'px';
  xImg.clearRect(0, 0, W, H); xImg.drawImage(T.cur, 0, 0);
  orig = document.createElement('canvas'); orig.width = W; orig.height = H;
  if (T.orig) orig.getContext('2d').putImageData(T.orig, 0, 0); else orig.getContext('2d').drawImage(T.cur, 0, 0);
  const k = Math.min(1, 300 / Math.max(W, H)) * Math.max(1, Math.floor(300 / Math.max(W, H)));
  cApercu.width = Math.round(W * k); cApercu.height = Math.round(H * k);
  document.getElementById('info_tex').textContent = `${T.nom} : ${W} × ${H} pixels. Les changements partent dans l'aperçu et le lecteur natif ; le mod les reprend à « Créer le mod ».`;
  // tailles des outils à l'échelle de la texture (beaucoup font 64 ou 128 pixels)
  if (S.taille > W / 2) S.taille = Math.max(1, Math.round(W / 12));
  if (S.tTaille > H) S.tTaille = Math.max(6, Math.round(H / 4));
  if (S.imgTaille > W) S.imgTaille = Math.round(W / 2);
  annuler = []; retablir = []; sale = false; boutons();
  document.getElementById('chargement').style.display = 'none';
  ajuster(); panneauOptions(); maj3d();
}

"""

vue_js = entre("// =====================================================================================================  vue (zoom, déplacement)",
               "// =====================================================================================================  historique")
vue_js = re.sub(r"document.getElementById\('b_guide'\).*?\n", "", vue_js)
vue_js = re.sub(r"document.getElementById\('b_col'\).onclick = \(\) => \{.*?\n\};\n", "", vue_js, flags=re.S)
vue_js = vue_js.replace("vue.s = Math.max(0.05, Math.min((r.width - 40) / W, (r.height - 90) / H));",
                        "vue.s = Math.max(0.05, Math.min(32, (r.width - 40) / W, (r.height - 90) / H));")
vue_js = vue_js.replace("const s2 = Math.max(0.05, Math.min(16, vue.s * f));", "const s2 = Math.max(0.05, Math.min(64, vue.s * f));")
vue_js += """// fond derrière l'image (les parties transparentes) : damier, noir (comme les effets additifs), blanc
const FONDS = [['damier', 'Damier'], ['noir', 'Noir'], ['blanc', 'Blanc']];
function majFond() {
  scene.style.backgroundImage = S.fond === 'damier' ? '' : 'none';
  scene.style.backgroundColor = S.fond === 'noir' ? '#000' : S.fond === 'blanc' ? '#fff' : '';
  document.querySelectorAll('#fond_choix .puce').forEach(b => b.classList.toggle('actif', b.dataset.f === S.fond));
}
(function () { const c = document.getElementById('fond_choix');
  for (const [f, l] of FONDS) { const b = document.createElement('button'); b.className = 'puce'; b.dataset.f = f; b.textContent = l;
    b.onclick = () => { S.fond = f; memo(); majFond(); }; c.appendChild(b); } majFond(); })();

"""

histo_js = entre("// =====================================================================================================  historique",
                 "// =====================================================================================================  couleurs")
histo_js = histo_js.replace("document.title = (sale ? '• ' : '') + 'Studio — Atelier Maillots';", "document.title = (sale ? '• ' : '') + 'Dessiner — Atelier Couleurs';")
histo_js = histo_js.replace("if (!confirm('Revenir à l\\'image de départ ? (Annuler reste possible)')) return;", "if (!confirm('Revenir à la texture du jeu ? (Annuler reste possible)')) return;")
histo_js = histo_js.replace("""  xImg.globalAlpha = (opacite === undefined ? S.opacite : opacite) / 100; xImg.drawImage(t, 0, 0); xImg.globalAlpha = 1;""",
                            """  // (15/11/2026) « garder la forme » : source-atop = ne colore que là où la texture est déjà visible (sa transparence reste)
  xImg.globalCompositeOperation = S.verrou ? 'source-atop' : 'source-over';
  xImg.globalAlpha = (opacite === undefined ? S.opacite : opacite) / 100; xImg.drawImage(t, 0, 0); xImg.globalAlpha = 1;
  xImg.globalCompositeOperation = 'source-over';""")

coul_js = entre("// =====================================================================================================  couleurs",
                "// =====================================================================================================  panneau d'options")

opt_js = entre("// =====================================================================================================  panneau d'options",
               "// =====================================================================================================  souris sur le patron")
opt_js = re.sub(r"function choixZone\(\) \{.*?\n\}\n", "", opt_js, count=1, flags=re.S)
opt_js = opt_js.replace("""    case 'gomme': ajout(curseur('Taille', 'taille', 2, 400, 1, ' px')); ajout(choixZone()); break;""",
                        """    case 'gomme': ajout(curseur('Taille', 'taille', 1, 400, 1, ' px'));
      ajout(puces('La gomme…', 'gommeMode', [['origine', 'remet la texture du jeu'], ['transparent', 'rend transparent']])); break;""")
opt_js = opt_js.replace("case 'pinceau': ajout(curseur('Taille', 'taille', 2, 400, 1, ' px'));",
    "case 'pinceau': ajout(puces('Effet', 'pinceauMode', [['peindre', 'Peindre (couvre)'], ['recolorer', 'Recolorer (garde les nuances)']])); ajout(curseur('Taille', 'taille', 1, 400, 1, ' px'));")
opt_js = opt_js.replace("""      ajout(Object.assign(document.createElement('div'), { className: 'petit', innerHTML: 'Avec une partie choisie, le pinceau ne déborde pas dessus. <kbd>[</kbd> <kbd>]</kbd> = taille.' })); break;""",
                        """      ajout(Object.assign(document.createElement('div'), { className: 'petit', innerHTML: '<kbd>[</kbd> <kbd>]</kbd> = taille. Maj = trait droit depuis le dernier point.' })); break;""")
opt_js = opt_js.replace("'Clic gauche = couleur principale, clic droit = 2e couleur. Dans tous les outils, le clic droit sur le maillot prend la couleur.'",
                        "'Clic gauche = couleur principale, clic droit = 2e couleur. Dans tous les outils, le clic droit sur l\\'image prend la couleur.'")
opt_js = opt_js.replace("""      ajout(puces('Mode', 'remplirMode', [['zone', 'Toute la partie cliquée'], ['seau', 'Même couleur (seau)'], ['partout', 'Remplacer cette couleur partout']]));""",
                        """      ajout(puces('Mode', 'remplirMode', [['teinte', 'Toute cette teinte (garde les nuances)'], ['seau', 'Même couleur (seau)'], ['partout', 'Remplacer cette couleur partout (garde les ombres)']]));""")
opt_js = re.sub(r"      ajout\(Object.assign\(document.createElement\('div'\), \{ className: 'petit', innerHTML: '« Toute la partie ».*?\}\)\); break;",
                "      ajout(Object.assign(document.createElement('div'), { className: 'petit', innerHTML: 'La transparence de la texture est toujours gardée.' })); break;", opt_js, flags=re.S)
opt_js = opt_js.replace("b.textContent = 'Poser sur la partie choisie';", "b.textContent = 'Poser sur toute l\\'image';")
opt_js = opt_js.replace("ajout(curseur('Largeur', 'largeur', 4, 400, 1, ' px')); ajout(curseur('Espacement', 'espacement', 2, 400, 1, ' px'));",
                        "ajout(curseur('Largeur', 'largeur', 1, 400, 1, ' px')); ajout(curseur('Espacement', 'espacement', 1, 400, 1, ' px'));")
opt_js = opt_js.replace("ajout(curseur('Angle', 'angle', -90, 90, 1, '°')); ajout(curseur('Taille (pois)', 'rayon', 3, 150, 1, ' px'));",
                        "ajout(curseur('Angle', 'angle', -90, 90, 1, '°')); ajout(curseur('Taille (pois)', 'rayon', 1, 150, 1, ' px'));")
opt_js = opt_js.replace("ajout(curseur('Taille', 'tTaille', 10, 600, 1, ' px'));", "ajout(curseur('Taille', 'tTaille', 4, 600, 1, ' px'));")
opt_js = opt_js.replace("ajout(curseur('Taille', 'imgTaille', 16, 1500, 1, ' px'));", "ajout(curseur('Taille', 'imgTaille', 4, 1500, 1, ' px'));")
opt_js = opt_js.replace("ajout(curseur('Épaisseur', 'taille', 2, 400, 1, ' px'));", "ajout(curseur('Épaisseur', 'taille', 1, 400, 1, ' px'));")
opt_js = opt_js.replace("'PNG avec fond transparent de préférence (écusson, logo de marque…).'", "'PNG avec fond transparent de préférence.'")
opt_js = opt_js.replace("etat('Image prête : clique sur le maillot pour la poser', 'ok')", "etat('Image prête : clique sur la texture pour la poser', 'ok')")

souris_js = entre("// =====================================================================================================  souris sur le patron",
                  "// =====================================================================================================  clavier, enregistrement")
souris_js = '''// (15/11/2026) RECOLORER EN GARDANT LES NUANCES : la teinte devient celle de la couleur principale, saturation et
// luminosité de chaque pixel gardées (les blancs / gris, saturation < 8 %, restent tels quels) ; la saturation est mise à
// l'échelle de la couleur choisie (une couleur pâle donne un résultat pâle). Transparence toujours gardée.
function hsvE(r, g, b) { const mx = Math.max(r, g, b), mn = Math.min(r, g, b), d = mx - mn; let h = 0;
  if (d) { if (mx === r) h = ((g - b) / d) % 6; else if (mx === g) h = (b - r) / d + 2; else h = (r - g) / d + 4; h *= 60; if (h < 0) h += 360; }
  return [h, mx ? d / mx : 0, mx]; }
function rgbE(h, s, v) { h = ((h % 360) + 360) % 360 / 60; const i = Math.floor(h), f = h - i, p = v * (1 - s), q = v * (1 - s * f), t = v * (1 - s * (1 - f));
  return [[v, t, p], [q, v, p], [p, v, t], [p, q, v], [t, p, v], [v, p, q]][i % 6]; }
// a : pixels de départ ; o : sortie ; poids(i) 0..1 pour le pixel i ; dh0 : décalage de teinte de référence (garde les écarts de teinte)
function recolorerPixels(a, o, poids, h0) {
  const [H1, S1] = hsvE(...hexRGB(S.c1).map(v => v / 255));
  for (let i = 0, n = a.length / 4; i < n; i++) { const k = i * 4, w = poids(i);
    if (!(w > 0)) continue;
    const [h, s, v] = hsvE(a[k] / 255, a[k + 1] / 255, a[k + 2] / 255);
    if (s < 0.08) continue;                                     // blancs / gris gardés
    const hn = h0 === null ? H1 : H1 + (h - h0), sn = Math.min(1, s * Math.min(1.5, S1 / 0.85));
    const c = rgbE(hn, sn, v);
    for (let j = 0; j < 3; j++) o[k + j] = a[k + j] * (1 - w) + c[j] * 255 * w;
  }
}
''' + souris_js
souris_js = souris_js.replace("""  document.getElementById('survol').innerHTML = z ? `Tu es sur : <b>${NOMS_ZONES[z] || z}</b>` : (dedans ? 'Partie pas visible sur le maillot' : 'Survole le maillot');""",
                              """  if (dedans) { const d = xImg.getImageData(p.x | 0, p.y | 0, 1, 1).data;
    document.getElementById('survol').innerHTML = `x ${p.x | 0}, y ${p.y | 0} · <b>#${[d[0], d[1], d[2]].map(v => v.toString(16).padStart(2, '0')).join('')}</b> · opacité ${Math.round(d[3] / 2.55)} %`; }
  else document.getElementById('survol').textContent = '';""")
souris_js = souris_js.replace("""  if (g.type === 'pinceau') { poser(x => x.drawImage(cTrait, 0, 0)); xTrait.clearRect(0, 0, W, H); }""",
"""  if (g.type === 'pinceau' && S.pinceauMode === 'recolorer') {     // (15/11/2026) recolore sous le trait, nuances gardées
    memoriser(); const tr = xTrait.getImageData(0, 0, W, H).data, im = xImg.getImageData(0, 0, W, H), a = new Uint8ClampedArray(im.data);
    recolorerPixels(a, im.data, i => tr[i * 4 + 3] / 255 * S.opacite / 100, null);
    xImg.putImageData(im, 0, 0); xTrait.clearRect(0, 0, W, H); changer();
  } else if (g.type === 'pinceau') { poser(x => x.drawImage(cTrait, 0, 0)); xTrait.clearRect(0, 0, W, H); }""")
souris_js = souris_js.replace("""  else if (g.type === 'gomme') {
    poser(x => { x.drawImage(cTrait, 0, 0); x.globalCompositeOperation = 'source-in'; x.drawImage(orig, 0, 0); }, undefined, 100);
    xTrait.clearRect(0, 0, W, H);""",
                              """  else if (g.type === 'gomme') {
    if (S.gommeMode === 'transparent') {          // (15/11/2026) gomme vers la transparence
      memoriser(); xImg.globalCompositeOperation = 'destination-out'; xImg.drawImage(cTrait, 0, 0); xImg.globalCompositeOperation = 'source-over'; changer();
    } else {                                      // remet la texture du jeu (transparence comprise)
      memoriser(); const t = document.createElement('canvas'); t.width = W; t.height = H; const x = t.getContext('2d');
      x.drawImage(cTrait, 0, 0); x.globalCompositeOperation = 'source-in'; x.drawImage(orig, 0, 0);
      xImg.globalCompositeOperation = 'destination-out'; xImg.drawImage(cTrait, 0, 0); xImg.globalCompositeOperation = 'source-over'; xImg.drawImage(t, 0, 0); changer();
    }
    xTrait.clearRect(0, 0, W, H);""")
souris_js = souris_js.replace("""  etat('Motif posé' + (z !== 'tout' ? ' sur : ' + (NOMS_ZONES[z] || z) : ''), 'ok');""", """  etat('Motif posé', 'ok');""")
souris_js = souris_js.replace("""    etat((NOMS_ZONES[z] || z) + ' remplie', 'ok'); return;""", """    etat('Rempli', 'ok'); return;""")
souris_js = souris_js.replace("""  if (!geste) { apercuOutil(); if (S.outil === 'motifs' || S.outil === 'remplir') dessinerGuide(z); return; }""",
                              """  if (!geste) { apercuOutil(); return; }""")
souris_js = souris_js.replace("""  if (S.remplirMode === 'zone') {""", """  if (S.remplirMode === 'teinte') {            // (15/11/2026) toute la teinte cliquée, nuances gardées
    const im = xImg.getImageData(0, 0, W, H), a = new Uint8ClampedArray(im.data), i0 = (Y * W + X) * 4;
    const [h0, s0] = hsvE(a[i0] / 255, a[i0 + 1] / 255, a[i0 + 2] / 255);
    if (s0 < 0.08) { etat('Couleur cliquée trop proche du blanc / gris : clique sur une partie colorée', 'err'); return; }
    const tol = 8 + S.tolerance * 0.6;           // degrés de teinte (tolérance 40 -> 32°)
    memoriser();
    recolorerPixels(a, im.data, i => { const k = i * 4; const [h, s] = hsvE(a[k] / 255, a[k + 1] / 255, a[k + 2] / 255);
      if (s < 0.08) return 0; let d = Math.abs(h - h0); d = Math.min(d, 360 - d);
      return d <= tol * 0.7 ? 1 : d >= tol ? 0 : 1 - (d - tol * 0.7) / (tol * 0.3); }, h0);
    if (S.opacite < 100) { const f = S.opacite / 100; for (let k = 0; k < a.length; k++) im.data[k] = a[k] * (1 - f) + im.data[k] * f; }
    xImg.putImageData(im, 0, 0); changer(); etat('Teinte remplacée', 'ok'); return;
  }
  if (S.remplirMode === 'zone') {""")
souris_js = souris_js.replace("""    if (!z) { etat('Clique sur une partie visible du maillot', 'err'); return; }""", """    if (!z) { etat('Mode de remplissage inconnu', 'err'); return; }""")
souris_js = souris_js.replace("""  const t = document.createElement('canvas'); t.width = W; t.height = H; t.getContext('2d').putImageData(out, 0, 0);
  poser(x => x.drawImage(t, 0, 0), 'tout');""",
                              """  // (15/11/2026) remplissage : pixels remplacés tels quels (transparence de la texture gardée), pas de « garder la forme »
  memoriser(); const ok = xImg.getImageData(0, 0, W, H);
  for (let i = 0; i < W * H; i++) if (masq[i]) { const k = i * 4, a = S.opacite / 100;
    for (let c = 0; c < 3; c++) ok.data[k + c] = ok.data[k + c] * (1 - a) + o[k + c] * a; }
  xImg.putImageData(ok, 0, 0); changer();""")

fin_js = """// =====================================================================================================  clavier, fermeture
addEventListener('keydown', ev => {
  if (ev.target.tagName === 'INPUT' && ev.target.type !== 'range' && ev.target.type !== 'checkbox') return;
  const k = ev.key.toLowerCase();
  if (ev.ctrlKey && k === 'z') { defaire(); ev.preventDefault(); return; }
  if (ev.ctrlKey && (k === 'y' || (ev.shiftKey && k === 'z'))) { refaire(); ev.preventDefault(); return; }
  if (ev.ctrlKey && k === 's') { garder(); ev.preventDefault(); return; }
  if (ev.ctrlKey) return;
  if (k === 'escape') { fermer(); return; }
  if (k === ' ') { espace = true; scene.style.cursor = 'grab'; ev.preventDefault(); return; }
  if (k === '[') { S.taille = Math.max(1, Math.round(S.taille / 1.2)); panneauOptions(); return; }
  if (k === ']') { S.taille = Math.min(400, Math.max(S.taille + 1, Math.round(S.taille * 1.2))); panneauOptions(); return; }
  if (k === 'x') { echanger(); return; }
  if (k === '0') { ajuster(); return; }
  if (k === '+' || k === '=') { zoomer(1.25); return; }
  if (k === '-') { zoomer(1 / 1.25); return; }
  const t = OUTILS.find(o => o && o[2].toLowerCase() === k); if (t) choisirOutil(t[0]);
});
addEventListener('keyup', ev => { if (ev.key === ' ') { espace = false; scene.style.cursor = S.outil === 'main' ? 'grab' : 'crosshair'; } });
function garder() { if (envoyer()) { sale = false; boutons(); } if (PARENT && PARENT.fermerEditeur) PARENT.fermerEditeur(); }
function fermer() {
  // en direct : tout est déjà dans l'Atelier ; sinon, proposer de garder
  if (sale && !document.getElementById('direct').checked && confirm('Garder ce dessin dans l\\'Atelier ?')) envoyer();
  if (PARENT && PARENT.fermerEditeur) PARENT.fermerEditeur();
}
document.getElementById('b_enreg').onclick = garder;
document.getElementById('b_fermer').onclick = fermer;
document.getElementById('verrou').checked = S.verrou;
document.getElementById('verrou').onchange = ev => { S.verrou = ev.target.checked; memo(); };
document.getElementById('direct').onchange = ev => { if (ev.target.checked) maj3d(); };

// =====================================================================================================  réglages de l'image (15/11/2026)
// saturation : écart à la luminance × s ; luminosité : × l ; contraste : autour du gris moyen.
// La 1re retouche garde l'image de départ (annulable) ; chaque mouvement de curseur repart de cette image.
let reglBase = null;
const RS = document.getElementById('r_sat'), RL = document.getElementById('r_lum'), RC = document.getElementById('r_con');
function hsvR(r, g, b) { const mx = Math.max(r, g, b), mn = Math.min(r, g, b), d = mx - mn; let h = 0;
  if (d) { if (mx === r) h = ((g - b) / d) % 6; else if (mx === g) h = (b - r) / d + 2; else h = (r - g) / d + 4; h *= 60; if (h < 0) h += 360; }
  return [h, mx ? d / mx : 0, mx]; }
function rgbH(h, s, v) { h = ((h % 360) + 360) % 360 / 60; const i = Math.floor(h), f = h - i, p = v * (1 - s), q = v * (1 - s * f), t = v * (1 - s * (1 - f));
  return [[v, t, p], [q, v, p], [p, v, t], [p, q, v], [t, p, v], [v, p, q]][i % 6]; }
function majReglages() {
  const sa = RS.value / 100, lu = RL.value / 100, co = RC.value / 100;
  document.getElementById('v_sat').textContent = RS.value + ' %'; document.getElementById('v_lum').textContent = RL.value + ' %'; document.getElementById('v_con').textContent = RC.value + ' %';
  if (!W) return;
  if (!reglBase) { _memoriserAvant(); reglBase = xImg.getImageData(0, 0, W, H); }
  const a = reglBase.data, out = new ImageData(W, H), o = out.data;
  for (let i = 0; i < a.length; i += 4) {
    // saturation : vers le gris de même luminance (0 % = gris, pas blanc) ; luminosité : multiplie
    const R = a[i] / 255, G = a[i + 1] / 255, B = a[i + 2] / 255, L = 0.299 * R + 0.587 * G + 0.114 * B;
    let r = (L + (R - L) * sa) * lu, g = (L + (G - L) * sa) * lu, b = (L + (B - L) * sa) * lu;
    r = (r - 0.5) * co + 0.5; g = (g - 0.5) * co + 0.5; b = (b - 0.5) * co + 0.5;
    o[i] = Math.max(0, Math.min(255, r * 255)); o[i + 1] = Math.max(0, Math.min(255, g * 255)); o[i + 2] = Math.max(0, Math.min(255, b * 255)); o[i + 3] = a[i + 3];
  }
  xImg.putImageData(out, 0, 0); changer();
}
function finReglages() { reglBase = null; RS.value = RL.value = RC.value = 100; for (const k of ['v_sat', 'v_lum', 'v_con']) document.getElementById(k).textContent = '100 %'; }
for (const r of [RS, RL, RC]) r.oninput = majReglages;
document.getElementById('r_ok').onclick = () => { finReglages(); etat('Réglages appliqués', 'ok'); };
document.getElementById('r_non').onclick = () => { if (reglBase) { xImg.putImageData(reglBase, 0, 0); changer(); } finReglages(); };
// un autre geste (dessin, outil) valide les réglages en cours
const _memoriserAvant = memoriser;
memoriser = function () { if (reglBase && !majReglages._dedans) finReglages(); return _memoriserAvant.apply(this, arguments); };
majReglages._dedans = false;
{ const f = majReglages; }   // (garde le nom)

if (P.get('panneau')) document.body.classList.add('panneau');

// =====================================================================================================  départ
majCouleurs();
choisirOutil(S.outil);
charger();
</script>
</body>
</html>
"""

out = haut + js_debut + etat_js + vue_js + histo_js + coul_js + opt_js + souris_js + fin_js
# restes propres aux maillots
for mot in ('suivre()', 'Vue3D', 'zonesUV', 'NOMS_ZONES[', 'partie ===', 'imgEncolure'):
    if mot in out:
        print('reste :', mot, [m.start() for m in re.finditer(re.escape(mot), out)][:5])
open(DST, 'w', encoding='utf-8').write(out)
print('ok', len(out.splitlines()), 'lignes')
