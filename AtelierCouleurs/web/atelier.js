// (15/11/2026) ATELIER DE RETOUCHE façon logiciel pro (Photoshop) pour les textures : esprits guerriers et totems (sur la 3D
// et la texture à plat) et textures des techniques (à plat). Outil d'édition (aucune règle du jeu ici) :
//  - un DOCUMENT par texture : un fond (la texture avec tes retouches d'avant) + des CALQUES (visible, opacité, mode de
//    fusion), le résultat aplati est écrit dans la texture de l'Atelier (x.cur) -> aperçu, lecteur natif, mod inchangés ;
//  - HISTORIQUE (40 pas) : clic sur un pas pour y revenir ; Ctrl+Z / Ctrl+Y ;
//  - SÉLECTION (masque 0..255) : baguette magique (tolérance, contiguë), lasso, rectangle, pièces du modèle, tout, inverser,
//    adoucir ; les pinceaux, le remplissage et les réglages restent dedans ;
//  - PINCEAUX : taille, dureté, opacité, flux ; pinceau, gomme, éclaircir, assombrir, tampon (Alt+clic = source), doigt,
//    dégradé (couleur 1 -> couleur 2), remplir, pipette ; symétrie gauche-droite sur le modèle 3D ;
//  - RÉGLAGES (aperçu en direct, sur la sélection) : teinte / saturation (coloriser), niveaux, courbes, balance des couleurs,
//    courbe de dégradé, remplacer la couleur.
"use strict";
const A = { docs: {}, doc: null, hist: [], pos: 0, sel: null, outil: 'choisir', mode: 'ombrage', recentes: [], tampon: null, trait: null,
  vue: { zoom: 1, ox: 0, oy: 0 }, lasso: null, rect: null, degrade: null, reglage: null, sym: false };
const MODES_FUSION = [['normal', 'Normal'], ['produit', 'Produit'], ['ecran', 'Écran'], ['incrustation', 'Incrustation'], ['ajout', 'Ajout (lumière)'],
  ['couleur', 'Couleur'], ['teinte', 'Teinte'], ['luminosite', 'Luminosité']];

// ====================================================================== documents
function atDoc(cle) {
  const x = E.textures[cle]; if (!x || !x.cur || !x.cur.getContext) return null;
  let d = A.docs[cle];
  const W = x.cur.width, H = x.cur.height;
  if (d && (d.W !== W || d.H !== H)) d = null;
  if (!d) { d = A.docs[cle] = { cle, x, W, H, fond: null, calques: [], actif: -1, n: 0, sig: null }; }
  // texture changée par un autre outil de l'Atelier (Changer la couleur, éditeur, remplacement global) : le fond la suit
  if (d.sig !== x.moyenne || !d.fond) {
    const px = x.cur.getContext('2d').getImageData(0, 0, W, H).data;
    if (d.calques.length && d.fond) { majRapport(`${x.nom} a été changée par un autre outil : les calques sont fusionnés dans le fond.`); d.calques = []; d.actif = -1; }
    d.fond = new Uint8ClampedArray(px); d.sig = x.moyenne; }
  return d;
}
function atActiver(cle) { const d = cle && atDoc(cle); A.doc = d || null; if (A.sel && (!d || A.sel.cle !== cle)) A.sel = null; A.vue = { zoom: 1, ox: 0, oy: 0 }; atPanneau(); atPlat(); atMajAffichage(); }
// barres sur la vue : seulement avec une texture en retouche, le bloc ouvert, dans un onglet de retouche
function atMajAffichage() { /* (les barres sur la vue n'existent plus : tout est dans le mode dessin) */ }
const atOuvert = () => document.body.classList.contains('dessin');
// (15/11/2026) MODE DESSIN : l'atelier prend la place des panneaux (la vue 3D reste à gauche). Esprits / totems : un clic sur
// une partie du modèle la choisit, et on ne colorie plus qu'elle (sélection = cette partie).
function atDessinOuvrir(cle) {
  if (!E.tech) return majRapport('Ouvre d’abord une technique, un esprit ou un totem.');
  if (E.tech.perso && !(cle && E.textures[cle] && E.textures[cle].cur && !E.textures[cle].info.donnees && Z.tex[cle])) cle = cle && E.textures[cle] && E.textures[cle].cur ? cle : Object.keys(Z.tex)[0];
  if (!cle) cle = atTexturePourTechnique();
  if (!cle) cle = Object.keys(E.textures).find(k => E.textures[k].cur && !(E.textures[k].info && E.textures[k].info.donnees));   // (objet du jeu : son icône)
  if (!cle) return majRapport('Choisis d’abord une texture (clic sur une vignette).');
  if (typeof fermerEditeur === 'function' && document.body.classList.contains('edition')) fermerEditeur();
  document.body.classList.add('dessin'); atActiver(cle); atOutil(A.outil && A.outil !== 'choisir' ? A.outil : 'pinceau');
  setTimeout(() => { atPlat(); dispatchEvent(new Event('resize')); atCadrer3D(); }, 80);
}
function atDessinFermer() {
  document.body.classList.remove('dessin'); if (A.reglage) atReglageFermer(false);
  if (E.vue) { E.vue.outil = null; E.vue.clicOutil = null; E.vue.cv.style.cursor = ''; }
  setTimeout(() => { dispatchEvent(new Event('resize')); atCadrer3D(); }, 60);
}
// la vue 3D est étroite en mode dessin : on recule la caméra pour voir le modèle en entier (champ vertical fixe)
function atCadrer3D() { const V = E.vue; if (!V || !V.recadrer(true)) return; const c = V.cv, a = c.clientWidth / Math.max(1, c.clientHeight);
  if (a < 1) V.dist *= Math.min(2.2, 0.85 / a); }
function atOnglet(n) { document.querySelectorAll('[data-at-onglet]').forEach(b => b.classList.toggle('actif', b.dataset.atOnglet === n));
  document.querySelectorAll('[data-at-volet]').forEach(v => { v.hidden = v.dataset.atVolet !== n; }); }
function atCalque(d) { return d.actif >= 0 ? d.calques[d.actif] : null; }
function atPixels(d) { const c = atCalque(d); return c ? c.px : d.fond; }
function atNouveauCalque(d, nom, mode) {
  const c = { id: ++d.n, nom: nom || 'Calque ' + (d.n), visible: true, opacite: 1, mode: mode || 'normal', px: new Uint8ClampedArray(d.W * d.H * 4) };
  d.calques.splice(d.actif + 1, 0, c); d.actif = d.actif + 1; return c;
}

// ---------------------------------------------------------------------- fusion des calques (formules usuelles, comme Photoshop)
const lumC = (r, g, b) => 0.3 * r + 0.59 * g + 0.11 * b;
function clipC(c) { const l = lumC(c[0], c[1], c[2]), n = Math.min(c[0], c[1], c[2]), x = Math.max(c[0], c[1], c[2]);
  if (n < 0) for (let k = 0; k < 3; k++) c[k] = l + (c[k] - l) * l / Math.max(1e-6, l - n);
  if (x > 1) for (let k = 0; k < 3; k++) c[k] = l + (c[k] - l) * (1 - l) / Math.max(1e-6, x - l); return c; }
function setLum(c, l) { const d = l - lumC(c[0], c[1], c[2]); return clipC([c[0] + d, c[1] + d, c[2] + d]); }
function setSat(c, s) { const x = Math.max(c[0], c[1], c[2]), n = Math.min(c[0], c[1], c[2]), o = [0, 0, 0];
  if (x - n < 1e-6) return o; for (let k = 0; k < 3; k++) o[k] = (c[k] - n) * s / (x - n); return o; }
function fusion(mode, b, s) {
  switch (mode) {
    case 'produit': return [b[0] * s[0], b[1] * s[1], b[2] * s[2]];
    case 'ecran': return b.map((v, k) => 1 - (1 - v) * (1 - s[k]));
    case 'incrustation': return b.map((v, k) => v < 0.5 ? 2 * v * s[k] : 1 - 2 * (1 - v) * (1 - s[k]));
    case 'ajout': return b.map((v, k) => Math.min(1, v + s[k]));
    case 'couleur': return setLum(s.slice(), lumC(b[0], b[1], b[2]));
    case 'teinte': { const sb = Math.max(...b) - Math.min(...b); return setLum(setSat(s, sb), lumC(b[0], b[1], b[2])); }
    case 'luminosite': return setLum(b.slice(), lumC(s[0], s[1], s[2]));
    default: return s;
  }
}
// aplatit le rectangle [x0,y0,x1,y1) du document dans la texture de l'Atelier
function atComposer(d, r) {
  r = r || [0, 0, d.W, d.H]; const [x0, y0, x1, y1] = [Math.max(0, r[0] | 0), Math.max(0, r[1] | 0), Math.min(d.W, Math.ceil(r[2])), Math.min(d.H, Math.ceil(r[3]))];
  if (x1 <= x0 || y1 <= y0) return;
  if (!d.comp) d.comp = new ImageData(d.W, d.H);
  const o = d.comp.data, f = d.fond, vis = d.calques.filter(c => c.visible && c.opacite > 0), b = [0, 0, 0], s = [0, 0, 0];
  for (let y = y0; y < y1; y++) for (let x = x0; x < x1; x++) { const i = (y * d.W + x) * 4;
    b[0] = f[i] / 255; b[1] = f[i + 1] / 255; b[2] = f[i + 2] / 255; let a = f[i + 3] / 255;
    for (const c of vis) { const ca = c.px[i + 3] / 255 * c.opacite; if (ca <= 0) continue;
      s[0] = c.px[i] / 255; s[1] = c.px[i + 1] / 255; s[2] = c.px[i + 2] / 255;
      const m = fusion(c.mode, b, s); for (let k = 0; k < 3; k++) b[k] = b[k] * (1 - ca) + m[k] * ca;
      if (c.mode === 'normal' || c.mode === 'ajout') a = a + ca * (1 - a); }
    o[i] = b[0] * 255; o[i + 1] = b[1] * 255; o[i + 2] = b[2] * 255; o[i + 3] = a * 255; }
  d.x.cur.getContext('2d').putImageData(d.comp, 0, 0, x0, y0, x1 - x0, y1 - y0);
}
let atAttenteGPU = false;
function atEnvoyerGPU(d) {     // pendant un geste : seulement la texture de la vue 3D (rapide)
  if (atAttenteGPU) return; atAttenteGPU = true;
  requestAnimationFrame(() => { atAttenteGPU = false; const c = texAffichee(d.x); E.vue.texture(d.cle, c); if (E.vue.textures['peau:' + d.cle]) E.vue.texture('peau:' + d.cle, c); atPlat(); });
}
function atFini(d) {           // fin d'une action : texture de l'Atelier à jour partout (aperçu, lecteur natif, projet, mod)
  const x = d.x; x.base = x.cur.getContext('2d').getImageData(0, 0, d.W, d.H); x.modif = true; x.moyenne = moyenne(x.base); x.donneesCur = null; d.sig = x.moyenne;
  if (Z.tex[d.cle]) { const a = x.base.data; for (const z of Z.zones) if (z.cle === d.cle) zonesCouleur(z, a); }
  apresRetouche(); atDessinerListes(); zonesAfficher3D(); atPlat();
}

// ====================================================================== historique
function atCopieRect(px, W, r) { const [x0, y0, x1, y1] = r, w = x1 - x0, h = y1 - y0, o = new Uint8ClampedArray(w * h * 4);
  for (let y = 0; y < h; y++) o.set(px.subarray(((y0 + y) * W + x0) * 4, ((y0 + y) * W + x1) * 4), y * w * 4); return o; }
function atPoserRect(px, W, r, src) { const [x0, y0, x1, y1] = r, w = x1 - x0, h = y1 - y0;
  for (let y = 0; y < h; y++) px.set(src.subarray(y * w * 4, (y + 1) * w * 4), ((y0 + y) * W + x0) * 4); }
function atStructure(d) { return { actif: d.actif, n: d.n, fond: new Uint8ClampedArray(d.fond), calques: d.calques.map(c => ({ ...c, px: new Uint8ClampedArray(c.px) })) }; }
function atRemettreStructure(d, s) { d.actif = s.actif; d.n = s.n; d.fond = new Uint8ClampedArray(s.fond); d.calques = s.calques.map(c => ({ ...c, px: new Uint8ClampedArray(c.px) })); }
function atPas(nom, pas) {      // pas = {cle, type:'pixels', cible (id calque ou 0 = fond), r, avant, apres} | {cle, type:'structure', avant, apres}
  A.hist.length = A.pos; A.hist.push({ nom, ...pas }); if (A.hist.length > 40) A.hist.shift(); A.pos = A.hist.length; atHistorique();
}
function atPixelsDe(d, cible) { if (!cible) return d.fond; const c = d.calques.find(c => c.id === cible); return c ? c.px : null; }
function atAppliquerPas(p, sens) {
  const d = A.docs[p.cle]; if (!d) return;
  if (p.type === 'structure') atRemettreStructure(d, sens > 0 ? p.apres : p.avant);
  else { const px = atPixelsDe(d, p.cible); if (px) atPoserRect(px, d.W, p.r, sens > 0 ? p.apres : p.avant); }
  atComposer(d); atFini(d);
}
function atAnnuler() { if (A.pos <= 0) return majRapport('Rien à annuler.'); A.pos--; atAppliquerPas(A.hist[A.pos], -1); atHistorique(); }
function atRetablir() { if (A.pos >= A.hist.length) return majRapport('Rien à rétablir.'); atAppliquerPas(A.hist[A.pos], 1); A.pos++; atHistorique(); }
function atAllerA(n) { while (A.pos > n) atAnnuler(); while (A.pos < n) atRetablir(); }
// une action sur les pixels du calque actif, dans le rectangle r : historique + fusion
function atAvantPixels(d) { return { cible: atCalque(d) ? atCalque(d).id : 0, avant: new Uint8ClampedArray(atPixels(d)) }; }
function atApresPixels(d, nom, av, r) {
  r = [Math.max(0, Math.floor(r[0])), Math.max(0, Math.floor(r[1])), Math.min(d.W, Math.ceil(r[2])), Math.min(d.H, Math.ceil(r[3]))];
  if (r[2] <= r[0] || r[3] <= r[1]) return;
  const px = atPixelsDe(d, av.cible);
  atPas(nom, { cle: d.cle, type: 'pixels', cible: av.cible, r, avant: atCopieRect(av.avant, d.W, r), apres: atCopieRect(px, d.W, r) });
  atComposer(d, r); atFini(d);
}
function atAvantStructure(d) { return atStructure(d); }
function atApresStructure(d, nom, avant) { atPas(nom, { cle: d.cle, type: 'structure', avant, apres: atStructure(d) }); atComposer(d); atFini(d); }

// ====================================================================== sélection (masque 0..255 de la taille du document)
function atMasque(d) { return A.sel && A.sel.cle === d.cle ? A.sel.m : null; }
function atSelDefinir(d, m, comment) {     // comment : 'nouveau' | 'ajouter' | 'retirer'
  if (!A.sel || A.sel.cle !== d.cle || comment === 'nouveau') A.sel = { cle: d.cle, m };
  else { const o = A.sel.m; for (let i = 0; i < o.length; i++) o[i] = comment === 'ajouter' ? Math.max(o[i], m[i]) : Math.min(o[i], 255 - m[i]); }
  if (!A.sel.m.some(v => v)) A.sel = null;
  atDessinerListes(); zonesAfficher3D(); atPlat();
}
function atCommentSel(ev) { return ev && ev.altKey ? 'retirer' : ev && (ev.shiftKey || ev.ctrlKey) ? 'ajouter' : 'nouveau'; }
function atBaguette(d, x, y, ev) {
  const W = d.W, H = d.H, c = d.comp ? d.comp.data : d.x.cur.getContext('2d').getImageData(0, 0, W, H).data, i0 = ((y | 0) * W + (x | 0)) * 4;
  const tol = +$('at-tol').value * 2.55, contigu = $('at-contigu').checked, m = new Uint8Array(W * H);
  const proche = i => Math.abs(c[i] - c[i0]) + Math.abs(c[i + 1] - c[i0 + 1]) + Math.abs(c[i + 2] - c[i0 + 2]) <= tol * 1.6 && Math.abs(c[i + 3] - c[i0 + 3]) <= tol;
  if (!contigu) { for (let p = 0; p < W * H; p++) if (proche(p * 4)) m[p] = 255; }
  else { const pile = [(y | 0) * W + (x | 0)]; m[pile[0]] = 255;
    while (pile.length) { const p = pile.pop(), px = p % W, py = (p - px) / W;
      for (const q of [px > 0 ? p - 1 : -1, px < W - 1 ? p + 1 : -1, py > 0 ? p - W : -1, py < H - 1 ? p + W : -1])
        if (q >= 0 && !m[q] && proche(q * 4)) { m[q] = 255; pile.push(q); } } }
  atSelDefinir(d, m, atCommentSel(ev));
}
function atPolygone(d, pts, ev) {        // lasso : polygone (pixels de la texture)
  const W = d.W, H = d.H, m = new Uint8Array(W * H);
  const ys = pts.map(p => p[1]), y0 = Math.max(0, Math.floor(Math.min(...ys))), y1 = Math.min(H - 1, Math.ceil(Math.max(...ys)));
  for (let y = y0; y <= y1; y++) { const xs = [], yc = y + 0.5;
    for (let k = 0; k < pts.length; k++) { const a = pts[k], b = pts[(k + 1) % pts.length];
      if ((a[1] <= yc && b[1] > yc) || (b[1] <= yc && a[1] > yc)) xs.push(a[0] + (yc - a[1]) / (b[1] - a[1]) * (b[0] - a[0])); }
    xs.sort((p, q) => p - q);
    for (let k = 0; k + 1 < xs.length; k += 2) for (let x = Math.max(0, Math.ceil(xs[k] - 0.5)); x <= Math.min(W - 1, Math.floor(xs[k + 1] - 0.5)); x++) m[y * W + x] = 255; }
  atSelDefinir(d, m, atCommentSel(ev));
}
function atSelPieces() {      // pièces choisies (outil Choisir) -> sélection
  const d = A.doc; if (!d || !Z.tex[d.cle]) return;
  if (!Z.sel.size) { if (A.sel && A.sel.pieces) A.sel = null; atDessinerListes(); atPlat(); return; }
  const m = new Uint8Array(d.W * d.H); for (const id of Z.sel) { const z = Z.zones[id]; if (z.cle === d.cle) for (let q = 0; q < z.n; q++) m[z.px[q]] = 255; }
  A.sel = { cle: d.cle, m, pieces: true }; atDessinerListes(); atPlat();
}
function atSelTout() { const d = A.doc; if (!d) return; atSelDefinir(d, new Uint8Array(d.W * d.H).fill(255), 'nouveau'); }
function atSelInverser() { const d = A.doc; if (!d) return; const m = new Uint8Array(d.W * d.H); const o = atMasque(d); for (let i = 0; i < m.length; i++) m[i] = 255 - (o ? o[i] : 0); atSelDefinir(d, m, 'nouveau'); }
function atSelRien() { A.sel = null; if (Z.sel.size) { Z.sel.clear(); zonesDessinerListe(); } atDessinerListes(); zonesAfficher3D(); atPlat(); }
function atSelAdoucir() {   // flou de la sélection (bord progressif), rayon en pixels
  const d = A.doc, o = d && atMasque(d); if (!o) return majRapport('Rien de sélectionné.');
  const r = Math.max(1, +$('at-adoucir').value | 0), W = d.W, H = d.H, t = new Float32Array(W * H), m = new Uint8Array(W * H);
  for (let y = 0; y < H; y++) { let s = 0; for (let x = -r; x < W; x++) { if (x + r < W) s += o[y * W + x + r]; if (x - r - 1 >= 0) s -= o[y * W + x - r - 1]; if (x >= 0) t[y * W + x] = s / (2 * r + 1); } }
  for (let x = 0; x < W; x++) { let s = 0; for (let y = -r; y < H; y++) { if (y + r < H) s += t[(y + r) * W + x]; if (y - r - 1 >= 0) s -= t[(y - r - 1) * W + x]; if (y >= 0) m[y * W + x] = s / (2 * r + 1); } }
  A.sel = { cle: d.cle, m }; atPlat(); zonesAfficher3D(); majRapport(`Bord de la sélection adouci (${r} px).`);
}

// ====================================================================== pinceaux
function atCouleur(id) { const hex = $(id || 'at-c1').value, rgb = hex2rgb(hex), [H, S, V] = rgb2hsv(...rgb); return { hex, rgb, H, S, V }; }
function atRetenir(hex) {
  A.recentes = [hex].concat(A.recentes.filter(x => x !== hex)).slice(0, 12);
  try { localStorage.setItem('atelier_couleurs_recentes', JSON.stringify(A.recentes)); } catch (e) { /* pas de stockage */ }
  atRecentes();
}
const PINCEAUX = ['pinceau', 'gomme', 'eclaircir', 'assombrir', 'tampon', 'doigt'];
function atTraitDebut(d, px, py, zone, ev) {
  const o = A.outil;
  if (o === 'tampon' && ev && ev.altKey) { A.tampon = { src: [px, py], decal: null }; majRapport('Source du tampon posée : peins ailleurs pour copier.'); return false; }
  if (o === 'tampon' && !A.tampon) { majRapport('Tampon : Alt + clic d’abord pour choisir la source.'); return false; }
  const av = atAvantPixels(d), C = atCouleur();
  A.trait = { d, av, src: av.avant, comp0: d.comp ? new Uint8ClampedArray(d.comp.data) : null, cov: new Float32Array(d.W * d.H), dernier: null, dernierM: null,
    zone: $('at-limiter') && $('at-limiter').checked && zone !== undefined ? zone : -1, C, r: [1e9, 1e9, -1e9, -1e9], doigt: null, calque: !!atCalque(d),
    libre: !!($('at-verrou') && !$('at-verrou').checked && !(E.tech && E.tech.perso)), ombre: atOmbreJeu(d) };
  if (o === 'tampon') { if (!A.tampon.decal) A.tampon.decal = [A.tampon.src[0] - px, A.tampon.src[1] - py]; }
  return true;
}
function atTraitPoint(px, py, miroir) {
  const t = A.trait; if (!t) return; const d = t.d, W = d.W, H = d.H, o = A.outil;
  const rr = +$('at-taille').value, dur = +$('at-durete').value / 100, opa = +$('at-opacite').value / 100, flux = +$('at-flux').value / 100;
  const px0 = atPixels(d), src = t.src, cov = t.cov, m = atMasque(d), T = Z.tex[d.cle], C = t.C;
  const cle = miroir ? 'dernierM' : 'dernier', pts = [];
  if (t[cle]) { const dd = Math.hypot(px - t[cle][0], py - t[cle][1]), n = Math.min(80, Math.ceil(dd / Math.max(1, rr * 0.25)));
    if (dd < W * 0.25) for (let k = 1; k <= n; k++) pts.push([t[cle][0] + (px - t[cle][0]) * k / n, t[cle][1] + (py - t[cle][1]) * k / n]); else pts.push([px, py]); } else pts.push([px, py]);
  t[cle] = [px, py];
  for (const [qx, qy] of pts) {
    t.r[0] = Math.min(t.r[0], qx - rr - 1); t.r[1] = Math.min(t.r[1], qy - rr - 1); t.r[2] = Math.max(t.r[2], qx + rr + 2); t.r[3] = Math.max(t.r[3], qy + rr + 2);
    if (o === 'doigt' && !t.doigt) { const i = ((Math.min(H - 1, Math.max(0, qy | 0))) * W + Math.min(W - 1, Math.max(0, qx | 0))) * 4; t.doigt = [px0[i], px0[i + 1], px0[i + 2], px0[i + 3]]; }
    for (let y = Math.max(0, Math.floor(qy - rr)); y <= Math.min(H - 1, Math.ceil(qy + rr)); y++)
      for (let x = Math.max(0, Math.floor(qx - rr)); x <= Math.min(W - 1, Math.ceil(qx + rr)); x++) {
        const dist = Math.hypot(x + 0.5 - qx, y + 0.5 - qy) / rr; if (dist > 1) continue;
        const p = y * W + x; if (t.zone >= 0 && T && T.label[p] !== t.zone && !miroir) continue;
        let f = dist <= dur ? 1 : 1 - (dist - dur) / Math.max(1e-3, 1 - dur); f *= flux; if (m) f *= m[p] / 255; if (f <= 0) continue;
        const i = p * 4;
        if (o === 'doigt') { const k = f * 0.6; for (let j = 0; j < 4; j++) { const v = px0[i + j] * (1 - k) + t.doigt[j] * k; t.doigt[j] = t.doigt[j] * 0.85 + px0[i + j] * 0.15; px0[i + j] = v; } continue; }
        const c0 = cov[p]; cov[p] = Math.min(opa, c0 + f * (1 - c0)); const w = cov[p]; if (w <= c0) continue;
        if (o === 'gomme') {
          if (t.calque) px0[i + 3] = src[i + 3] * (1 - w);
          else if ($('at-gomme-transp') && $('at-gomme-transp').checked) px0[i + 3] = src[i + 3] * (1 - w);
          else { const g = d.x.orig.data; for (let j = 0; j < 4; j++) px0[i + j] = src[i + j] * (1 - w) + g[i + j] * w; } }
        else if (o === 'eclaircir' || o === 'assombrir') { const k = o === 'eclaircir' ? 1 + 0.6 * w : 1 - 0.5 * w; for (let j = 0; j < 3; j++) px0[i + j] = src[i + j] * k; }
        else if (o === 'tampon') { const sx = Math.round(x + A.tampon.decal[0]), sy = Math.round(y + A.tampon.decal[1]);
          if (sx < 0 || sy < 0 || sx >= W || sy >= H) continue; const si = (sy * W + sx) * 4, s2 = t.comp0 || src;
          for (let j = 0; j < 4; j++) px0[i + j] = src[i + j] * (1 - w) + s2[si + j] * w; }
        else if (t.calque) {          // calque : peinture « normale » (le mode du calque fait le reste)
          const a0 = src[i + 3] / 255, a1 = a0 + w * (1 - a0);
          for (let j = 0; j < 3; j++) px0[i + j] = a1 > 0 ? (src[i + j] * a0 * (1 - w) + C.rgb[j] * 255 * w) / a1 : 0; px0[i + 3] = a1 * 255; }
        else if (A.mode === 'couvrir' || (t.libre && src[i + 3] < 250)) { for (let j = 0; j < 3; j++) px0[i + j] = src[i + j] * (1 - w) + C.rgb[j] * 255 * w; if (t.libre) px0[i + 3] = src[i + 3] + w * (255 - src[i + 3]); }
        else { const og = t.ombre, z0 = T && Z.zones[T.label[p]], z = z0 ? (og && z0.o ? z0.o : z0) : zoneVoisinage(og || src, i); zonesTeindre(px0, i, C.H, C.S, C.V, z, 1, w, src, og); } } }
  atComposer(d, t.r); atEnvoyerGPU(d);
}
// (15/11/2026) « Garder l'ombrage » prend l'ombrage dans la TEXTURE DU JEU (pas dans ce qui est déjà peint) : on peut
// repeindre n'importe quelle couleur par-dessus, même par-dessus du noir
function atOmbreJeu(d) { const o = d.x.orig; return o && o.data && o.data.length === d.W * d.H * 4 ? o.data : null; }
function zoneVoisinage(src, i) { const [h, s, v] = rgb2hsv(src[i] / 255, src[i + 1] / 255, src[i + 2] / 255); return { h, s, v: Math.max(0.2, v) }; }
function atTraitFin() {
  const t = A.trait; if (!t) return; A.trait = null;
  const noms = { pinceau: 'Pinceau', gomme: 'Gomme', eclaircir: 'Éclaircir', assombrir: 'Assombrir', tampon: 'Tampon', doigt: 'Doigt' };
  atApresPixels(t.d, noms[A.outil] || 'Pinceau', t.av, t.r);
  if (['pinceau'].includes(A.outil)) atRetenir(t.C.hex);
}
// remplir : une pièce du modèle (esprits / totems) ou la zone de couleur proche (pot de peinture), ou la sélection
function atRemplirMasque(d, m, nom) {
  const av = atAvantPixels(d), px = atPixels(d), C = atCouleur(), cal = !!atCalque(d), T = Z.tex[d.cle], lum = +$('zn-lum').value / 100;
  const spmM = $('zn-metal') && $('zn-metal').checked && T ? zonesCarte(d.cle, 'spm') : null;     // seulement le métal
  let r = [1e9, 1e9, -1e9, -1e9], n = 0;
  for (let p = 0; p < m.length; p++) { const w = m[p] / 255; if (!w) continue; if (spmM && zonesValeurCarte(spmM, p, T) < 0.2) continue;
    const i = p * 4, x = p % d.W, y = (p - x) / d.W; n++;
    r[0] = Math.min(r[0], x); r[1] = Math.min(r[1], y); r[2] = Math.max(r[2], x + 1); r[3] = Math.max(r[3], y + 1);
    if (cal) { const a0 = px[i + 3] / 255, a1 = a0 + w * (1 - a0); for (let j = 0; j < 3; j++) px[i + j] = a1 > 0 ? (px[i + j] * a0 * (1 - w) + C.rgb[j] * 255 * w) / a1 : 0; px[i + 3] = a1 * 255; }
    else if (A.mode === 'couvrir') { for (let j = 0; j < 3; j++) px[i + j] = px[i + j] * (1 - w) + Math.min(255, C.rgb[j] * 255 * lum) * w; }
    else { const og = atOmbreJeu(d), z0 = T && Z.zones[T.label[p]], z = z0 ? (og && z0.o ? z0.o : z0) : zoneVoisinage(og || av.avant, i); zonesTeindre(px, i, C.H, C.S, C.V, z, lum, w, av.avant, og); } }
  if (!n) return majRapport('Rien à remplir ici.');
  atRetenir(C.hex); atApresPixels(d, nom || 'Remplir', av, r);
  // reflets du métal (esprits / totems) : la carte spm sous les mêmes pixels
  if ($('zn-reflets') && $('zn-reflets').checked && T && !cal) { const spm = zonesCarte(d.cle, 'spm'); if (spm) atReflets(d, m, spm, C); }
}
function atReflets(d, m, spm, C) {
  const ds = atDoc(d.cle + 'spm'); if (!ds) return; const av = atAvantPixels(ds), px = atPixels(ds), T = Z.tex[d.cle]; let n = 0;
  for (let y = 0; y < ds.H; y++) for (let x = 0; x < ds.W; x++) { const p = Math.floor(y * d.H / ds.H) * d.W + Math.floor(x * d.W / ds.W), w = m[p] / 255; if (!w) continue;
    const i = (y * ds.W + x) * 4; if (Math.max(px[i], px[i + 1], px[i + 2]) < 12) continue; const z = T && Z.zones[T.label[p]];
    zonesTeindre(px, i, C.H, C.S, C.V, { h: z ? z.h : 0, s: z ? z.s : 0, v: C.V }, 1, w, av.avant); n++; }
  if (n) atApresPixels(ds, 'Reflets du métal (spm)', av, [0, 0, ds.W, ds.H]);
}
function atRemplirClic(d, px, py, zone, ev) {
  const m = atMasque(d);
  if (m && m[(py | 0) * d.W + (px | 0)]) return atRemplirMasque(d, m, 'Remplir la sélection');
  const T = Z.tex[d.cle];
  if (T && zone >= 0) { const z = Z.zones[zone], mm = new Uint8Array(d.W * d.H); for (let q = 0; q < z.n; q++) mm[z.px[q]] = 255; return atRemplirMasque(d, mm, 'Remplir · pièce ' + (zone + 1)); }
  // pot de peinture : couleur proche contiguë (même tolérance que la baguette)
  const garde = A.sel; atBaguette(d, px, py, null); const mm = A.sel ? A.sel.m : null; A.sel = garde;
  if (mm) atRemplirMasque(d, mm, 'Pot de peinture');
}
function atDegrade(d, a, b) {          // dégradé linéaire couleur 1 -> couleur 2, dans la sélection (sinon tout le calque)
  const av = atAvantPixels(d), px = atPixels(d), m = atMasque(d), c1 = atCouleur('at-c1').rgb, c2 = atCouleur('at-c2').rgb, cal = !!atCalque(d);
  const dx = b[0] - a[0], dy = b[1] - a[1], L = dx * dx + dy * dy || 1, opa = +$('at-opacite').value / 100;
  for (let p = 0; p < d.W * d.H; p++) { const w = (m ? m[p] / 255 : 1) * opa; if (!w) continue; const x = p % d.W, y = (p - x) / d.W, i = p * 4;
    const t = Math.max(0, Math.min(1, ((x + 0.5 - a[0]) * dx + (y + 0.5 - a[1]) * dy) / L)), c = [0, 1, 2].map(k => (c1[k] * (1 - t) + c2[k] * t) * 255);
    if (cal) { const a0 = px[i + 3] / 255, a1 = a0 + w * (1 - a0); for (let j = 0; j < 3; j++) px[i + j] = a1 > 0 ? (px[i + j] * a0 * (1 - w) + c[j] * w) / a1 : 0; px[i + 3] = a1 * 255; }
    else for (let j = 0; j < 3; j++) px[i + j] = px[i + j] * (1 - w) + c[j] * w; }
  atApresPixels(d, 'Dégradé', av, [0, 0, d.W, d.H]);
}
function atPipette(d, px, py) {
  const c = d.comp ? d.comp.data : d.x.cur.getContext('2d').getImageData(0, 0, d.W, d.H).data, i = ((py | 0) * d.W + (px | 0)) * 4;
  $('at-c1').value = '#' + [c[i], c[i + 1], c[i + 2]].map(v => v.toString(16).padStart(2, '0')).join(''); atMajCouleurs();
  atOutil(A.avantPipette || 'pinceau'); majRapport('Couleur prise : ' + $('at-c1').value + '.');
}

// ---------------------------------------------------------------------- symétrie gauche-droite (modèle 3D, axe X du modèle)
function atMiroir(h) {       // point du modèle touché -> point symétrique -> UV du sommet le plus proche
  const p = h.piece, g = p.geo, idx = g.idx, t = h.t, P = [0, 0, 0];
  if (!p._grille) { const n = g.pos.length / 3, mn = [1e9, 1e9, 1e9], mx = [-1e9, -1e9, -1e9];
    for (let v = 0; v < n; v++) for (let k = 0; k < 3; k++) { mn[k] = Math.min(mn[k], g.pos[3 * v + k]); mx[k] = Math.max(mx[k], g.pos[3 * v + k]); }
    const c = Math.max(mx[0] - mn[0], mx[1] - mn[1], mx[2] - mn[2]) / 48 || 1, G = new Map();
    for (let v = 0; v < n; v++) { const k = Math.floor(g.pos[3 * v] / c) + ',' + Math.floor(g.pos[3 * v + 1] / c) + ',' + Math.floor(g.pos[3 * v + 2] / c); (G.get(k) || G.set(k, []).get(k)).push(v); }
    p._grille = { c, G }; p._zoneSommet = new Int32Array(n).fill(-1); for (let k = 0; k < idx.length; k++) p._zoneSommet[idx[k]] = p.zonesTri[(k / 3) | 0]; }
  for (let k = 0; k < 3; k++) P[k] = h.l[0] * g.pos[3 * idx[3 * t] + k] + h.l[1] * g.pos[3 * idx[3 * t + 1] + k] + h.l[2] * g.pos[3 * idx[3 * t + 2] + k];
  P[0] = -P[0];
  const { c, G } = p._grille, cx = Math.floor(P[0] / c), cy = Math.floor(P[1] / c), cz = Math.floor(P[2] / c); let best = -1, bd = 1e18;
  for (let a = -1; a <= 1; a++) for (let b = -1; b <= 1; b++) for (let e = -1; e <= 1; e++) for (const v of G.get((cx + a) + ',' + (cy + b) + ',' + (cz + e)) || []) {
    const dd = (g.pos[3 * v] - P[0]) ** 2 + (g.pos[3 * v + 1] - P[1]) ** 2 + (g.pos[3 * v + 2] - P[2]) ** 2; if (dd < bd) { bd = dd; best = v; } }
  if (best < 0) return null; const u = g.uv[2 * best], w = g.uv[2 * best + 1];
  return { u: u - Math.floor(u), v: w - Math.floor(w), zone: p._zoneSommet[best] };
}

// ====================================================================== gestes : 3D et texture à plat
function atGeste(type, d, px, py, zone, ev, h) {
  if (type === 'fin') { if (A.trait) atTraitFin(); return true; }
  if (!d) return false; const o = A.outil;
  if (PINCEAUX.includes(o)) {
    if (type === 'debut') { if (!atTraitDebut(d, px, py, zone, ev)) return true; atTraitPoint(px, py);
      if (A.sym && h) { const mi = atMiroir(h); if (mi) atTraitPoint(mi.u * d.W, mi.v * d.H, true); } }
    else if (type === 'bouger' && A.trait && A.trait.d === d) { atTraitPoint(px, py); if (A.sym && h) { const mi = atMiroir(h); if (mi) atTraitPoint(mi.u * d.W, mi.v * d.H, true); } }
    return true; }
  if (type !== 'clic') return false;
  if (o === 'choisir') { if (Z.tex[d.cle]) zonesChoisir(zone >= 0 ? zone : -1, ev && (ev.shiftKey || ev.ctrlKey)); return true; }
  if (o === 'remplir') { atRemplirClic(d, px, py, zone, ev); if (A.sym && h) { const mi = atMiroir(h); if (mi && mi.zone >= 0 && mi.zone !== zone) atRemplirClic(d, mi.u * d.W, mi.v * d.H, mi.zone, ev); } return true; }
  if (o === 'pipette') { atPipette(d, px, py); return true; }
  if (o === 'baguette') { atBaguette(d, px, py, ev); return true; }
  return false;
}
function at3D(ev) { const h = zonesSousSouris(ev); if (!h) return null; const d = atDoc(h.cle); if (!d) return null; if (A.doc !== d) atActiver(h.cle);
  return { d, px: (h.u - Math.floor(h.u)) * d.W, py: (h.v - Math.floor(h.v)) * d.H, zone: h.zone, h }; }

// ====================================================================== réglages (aperçu en direct, sur la sélection)
const REGLAGES = {
  tsl: { nom: 'Teinte / saturation', champs: [['Teinte', 'h', -180, 180, 0], ['Saturation', 's', -100, 100, 0], ['Luminosité', 'l', -100, 100, 0]], cases: [['Coloriser', 'col']] },
  niveaux: { nom: 'Niveaux', champs: [['Noir', 'n', 0, 250, 0], ['Gamma ×100', 'g', 10, 300, 100], ['Blanc', 'b', 5, 255, 255]] },
  courbes: { nom: 'Courbes', champs: [['Ombres', 'c0', 0, 255, 0], ['Quart', 'c1', 0, 255, 64], ['Milieu', 'c2', 0, 255, 128], ['Trois-quarts', 'c3', 0, 255, 192], ['Clairs', 'c4', 0, 255, 255]], canal: true },
  balance: { nom: 'Balance des couleurs', champs: [['Cyan ↔ Rouge', 'r', -100, 100, 0], ['Magenta ↔ Vert', 'v', -100, 100, 0], ['Jaune ↔ Bleu', 'b', -100, 100, 0]], tons: true },
  degrade: { nom: 'Courbe de dégradé', couleurs: [['Ombres', 'd0', '#101030'], ['Milieu', 'd1', '#2a6cff'], ['Clairs', 'd2', '#e8f2ff']], champs: [['Mélange %', 'm', 0, 100, 100]] },
  remplacer: { nom: 'Remplacer la couleur', couleurs: [['Couleur visée', 'cible', '#ff0000']], champs: [['Tolérance', 't', 1, 120, 40], ['Teinte', 'h', -180, 180, 0], ['Saturation', 's', -100, 100, 0], ['Luminosité', 'l', -100, 100, 0]] },
};
function atReglageOuvrir(k) {
  const d = A.doc; if (!d) return majRapport('Choisis d’abord une texture.');
  if (A.reglage) atReglageFermer(false);
  atOnglet('reglages'); const R = REGLAGES[k], b = $('at-reglage'); A.reglage = { k, d, av: atAvantPixels(d), v: {} };
  let h = `<div class="at-reg-titre">${R.nom}${atMasque(d) ? ' <small>(dans la sélection)</small>' : ''}</div>`;
  if (R.canal) h += `<div class="ligne"><label>Canal <select data-reg="canal"><option value="rvb">RVB</option><option value="r">Rouge</option><option value="v">Vert</option><option value="b">Bleu</option></select></label></div>`;
  if (R.tons) h += `<div class="ligne"><label>Tons <select data-reg="tons"><option value="m">Moyens</option><option value="o">Ombres</option><option value="c">Clairs</option></select></label></div>`;
  for (const [n, id, def] of R.couleurs || []) h += `<div class="ligne"><label>${n} <input type="color" data-reg="${id}" value="${def}"></label></div>`;
  for (const [n, id, mn, mx, def] of R.champs || []) h += `<div class="ligne at-reg-champ"><label>${n}</label><input type="range" data-reg="${id}" min="${mn}" max="${mx}" value="${def}"><span>${def}</span></div>`;
  for (const [n, id] of R.cases || []) h += `<label class="aide"><input type="checkbox" data-reg="${id}"> ${n}</label>`;
  h += `<div class="ligne"><button class="primaire" id="at-reg-ok">OK</button><button id="at-reg-non">Annuler</button></div>`;
  b.innerHTML = h; b.style.display = '';
  b.querySelectorAll('[data-reg]').forEach(e => { e.oninput = () => { if (e.type === 'range') e.nextElementSibling.textContent = e.value; atReglageApercu(); }; e.onchange = e.oninput; });
  $('at-reg-ok').onclick = () => atReglageFermer(true); $('at-reg-non').onclick = () => atReglageFermer(false);
  atReglageApercu();
}
function atReglageValeurs() { const v = {}; $('at-reglage').querySelectorAll('[data-reg]').forEach(e => { v[e.dataset.reg] = e.type === 'checkbox' ? e.checked : e.type === 'color' || e.tagName === 'SELECT' ? e.value : +e.value; }); return v; }
let atRegAttente = false;
function atReglageCalculer() {
  const R = A.reglage; if (!R) return;
  const d = R.d, src = R.av.avant, px = atPixels(d), m = atMasque(d), v = atReglageValeurs(), f = atFonctionReglage(R.k, v);
  for (let p = 0; p < d.W * d.H; p++) { const i = p * 4, w = m ? m[p] / 255 : 1;
    if (!w || !src[i + 3]) { px[i] = src[i]; px[i + 1] = src[i + 1]; px[i + 2] = src[i + 2]; continue; }
    const c = f(src[i] / 255, src[i + 1] / 255, src[i + 2] / 255);
    for (let j = 0; j < 3; j++) px[i + j] = src[i + j] * (1 - w) + Math.max(0, Math.min(1, c[j])) * 255 * w; }
  atComposer(d); atEnvoyerGPU(d);
}
function atReglageApercu() {
  if (atRegAttente) return; atRegAttente = true;
  requestAnimationFrame(() => { atRegAttente = false; atReglageCalculer(); });
}
function atFonctionReglage(k, v) {
  if (k === 'tsl') return (r, g, b) => { let [h, s, l] = rgb2hsv(r, g, b); if (v.col) { h = (v.h + 360) % 360; s = Math.max(0, Math.min(1, 0.5 + v.s / 200)); } else { h += v.h; s = Math.max(0, Math.min(1, s * (1 + v.s / 100))); }
    l = v.l >= 0 ? l + (1 - l) * v.l / 100 : l * (1 + v.l / 100); return hsv2rgb(h, s, l); };
  if (k === 'niveaux') { const n = v.n / 255, bl = Math.max(n + 0.01, v.b / 255), gm = v.g / 100; const L = x => Math.pow(Math.max(0, Math.min(1, (x - n) / (bl - n))), 1 / gm); return (r, g, b) => [L(r), L(g), L(b)]; }
  if (k === 'courbes') { const pts = [v.c0, v.c1, v.c2, v.c3, v.c4].map(x => x / 255), lut = new Float32Array(256);
    for (let i = 0; i < 256; i++) { const x = i / 255 * 4, k0 = Math.min(3, Math.floor(x)), t = x - k0, p0 = pts[Math.max(0, k0 - 1)], p1 = pts[k0], p2 = pts[k0 + 1], p3 = pts[Math.min(4, k0 + 2)];
      lut[i] = 0.5 * (2 * p1 + (-p0 + p2) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t * t + (-p0 + 3 * p1 - 3 * p2 + p3) * t * t * t); }
    const L = x => lut[Math.max(0, Math.min(255, Math.round(x * 255)))];
    return (r, g, b) => v.canal === 'r' ? [L(r), g, b] : v.canal === 'v' ? [r, L(g), b] : v.canal === 'b' ? [r, g, L(b)] : [L(r), L(g), L(b)]; }
  if (k === 'balance') return (r, g, b) => { const l = lumC(r, g, b), w = v.tons === 'o' ? Math.max(0, 1 - l * 2.5) : v.tons === 'c' ? Math.max(0, (l - 0.6) * 2.5) : 1 - Math.abs(l - 0.5) * 2, s = 0.3 * w;
    return [r + v.r / 100 * s, g + v.v / 100 * s, b + v.b / 100 * s]; };
  if (k === 'degrade') { const c = [v.d0, v.d1, v.d2].map(hex2rgb), mel = v.m / 100;
    return (r, g, b) => { const l = Math.max(0, Math.min(1, lumC(r, g, b))), t = l * 2, k0 = t < 1 ? 0 : 1, u = t - k0, o = [0, 1, 2].map(j => c[k0][j] * (1 - u) + c[k0 + 1][j] * u);
      return [r * (1 - mel) + o[0] * mel, g * (1 - mel) + o[1] * mel, b * (1 - mel) + o[2] * mel]; }; }
  if (k === 'remplacer') { const [hc, sc, vc] = rgb2hsv(...hex2rgb(v.cible)), tol = v.t;
    return (r, g, b) => { let [h, s, l] = rgb2hsv(r, g, b); const dd = (distTeinte(h, hc) + Math.abs(s - sc) * 120 + Math.abs(l - vc) * 60), w = dd <= tol * 0.6 ? 1 : dd >= tol ? 0 : 1 - (dd - tol * 0.6) / (tol * 0.4);
      if (!w) return [r, g, b]; const o = hsv2rgb(h + v.h * w, Math.max(0, Math.min(1, s * (1 + v.s / 100 * w))), Math.max(0, Math.min(1, l * (1 + v.l / 100 * w)))); return o; }; }
  return (r, g, b) => [r, g, b];
}
function atReglageFermer(ok) {
  const R = A.reglage; if (!R) return; if (ok) atReglageCalculer();     // valeurs finales, même sans aperçu encore dessiné
  A.reglage = null; $('at-reglage').style.display = 'none'; $('at-reglage').innerHTML = '';
  const d = R.d;
  if (!ok) { atPixels(d).set(R.av.avant); atComposer(d); atEnvoyerGPU(d); return; }
  atApresPixels(d, REGLAGES[R.k].nom, R.av, [0, 0, d.W, d.H]);
}

// ====================================================================== calques
function atCalqueAjouter(mode) { const d = A.doc; if (!d) return; const av = atAvantStructure(d); const c = atNouveauCalque(d, null, mode); if (mode === 'couleur') c.nom = 'Couleur ' + d.n; atApresStructure(d, 'Nouveau calque', av); }
function atCalqueDupliquer() { const d = A.doc; if (!d) return; const av = atAvantStructure(d), s = atCalque(d);
  const c = atNouveauCalque(d, (s ? s.nom : 'Fond') + ' copie', s ? s.mode : 'normal'); c.px.set(s ? s.px : d.fond); if (s) c.opacite = s.opacite; atApresStructure(d, 'Dupliquer le calque', av); }
function atCalqueSupprimer() { const d = A.doc; if (!d || d.actif < 0) return majRapport('Le fond ne se supprime pas.'); const av = atAvantStructure(d); d.calques.splice(d.actif, 1); d.actif = Math.min(d.actif, d.calques.length - 1); atApresStructure(d, 'Supprimer le calque', av); }
function atCalqueFusionner() {     // fusionner le calque actif dans celui du dessous (ou le fond)
  const d = A.doc; if (!d || d.actif < 0) return; const av = atAvantStructure(d), c = d.calques[d.actif];
  const tmp = { ...d, calques: d.actif > 0 ? [d.calques[d.actif - 1], c] : [c], fond: d.actif > 0 ? null : d.fond };
  if (d.actif > 0) { const dessous = d.calques[d.actif - 1], o = dessous.px; for (let p = 0; p < d.W * d.H; p++) { const i = p * 4, ca = c.px[i + 3] / 255 * (c.visible ? c.opacite : 0); if (!ca) continue;
      const b = [o[i] / 255, o[i + 1] / 255, o[i + 2] / 255], s = [c.px[i] / 255, c.px[i + 1] / 255, c.px[i + 2] / 255], f = fusion(c.mode, b, s), a0 = o[i + 3] / 255, a1 = a0 + ca * (1 - a0);
      for (let j = 0; j < 3; j++) o[i + j] = (b[j] * a0 * (1 - ca) + f[j] * ca) / Math.max(1e-6, a1) * 255; o[i + 3] = a1 * 255; } }
  else { const garde = d.calques; d.calques = [c]; atComposer(d); d.fond = new Uint8ClampedArray(d.comp.data); d.calques = garde; }
  d.calques.splice(d.actif, 1); d.actif--; atApresStructure(d, 'Fusionner vers le bas', av); void tmp;
}
function atCalqueDeplacer(k) { const d = A.doc; if (!d || d.actif < 0) return; const j = d.actif + k; if (j < 0 || j >= d.calques.length) return;
  const av = atAvantStructure(d); [d.calques[d.actif], d.calques[j]] = [d.calques[j], d.calques[d.actif]]; d.actif = j; atApresStructure(d, k > 0 ? 'Monter le calque' : 'Descendre le calque', av); }
function atCalqueProp(c, prop, val) { const d = A.doc; const av = atAvantStructure(d); c[prop] = val; atApresStructure(d, prop === 'visible' ? (val ? 'Afficher le calque' : 'Masquer le calque') : prop === 'mode' ? 'Mode du calque' : prop === 'nom' ? 'Renommer le calque' : 'Opacité du calque', av); }

// ====================================================================== sauvegarde dans le projet
function atelierEtat() {        // seulement les documents qui ont des calques
  const out = {};
  for (const d of Object.values(A.docs)) { if (!d.calques.length) continue;
    const enPng = px => { const c = document.createElement('canvas'); c.width = d.W; c.height = d.H; c.getContext('2d').putImageData(new ImageData(new Uint8ClampedArray(px), d.W, d.H), 0, 0); return c.toDataURL('image/png'); };
    out[d.cle] = { fond: enPng(d.fond), actif: d.actif, calques: d.calques.map(c => ({ nom: c.nom, visible: c.visible, opacite: c.opacite, mode: c.mode, png: enPng(c.px) })) }; }
  return out;
}
async function atelierRestaurer(e) {
  for (const [cle, s] of Object.entries(e || {})) { const d = atDoc(cle); if (!d) continue;
    const lire = async url => { const im = await chargerImage(url), c = document.createElement('canvas'); c.width = d.W; c.height = d.H; const x = c.getContext('2d'); x.drawImage(im, 0, 0, d.W, d.H); return new Uint8ClampedArray(x.getImageData(0, 0, d.W, d.H).data); };
    try { d.fond = await lire(s.fond); d.calques = [];
      for (const c of s.calques) d.calques.push({ id: ++d.n, nom: c.nom, visible: c.visible, opacite: c.opacite, mode: c.mode, px: await lire(c.png) });
      d.actif = Math.min(s.actif, d.calques.length - 1); atComposer(d); const x = d.x; x.base = x.cur.getContext('2d').getImageData(0, 0, d.W, d.H); x.moyenne = moyenne(x.base); d.sig = x.moyenne; x.modif = true; }
    catch (er) { console.error('calques', er); } }
  atPanneau(); atPlat();
}
function atelierApresOuverture() {
  if (atOuvert()) atDessinFermer();
  A.docs = {}; A.hist = []; A.pos = 0; A.sel = null; A.tampon = null; A.reglage = null; if ($('at-reglage')) { $('at-reglage').style.display = 'none'; }
  const T = Object.values(Z.tex)[0]; atActiver(T ? T.cle : atTexturePourTechnique());
  atHistorique();
}
function atTexturePourTechnique() { const k = [...E.selTex][0]; return k && E.textures[k] && !E.textures[k].info.donnees ? k : null; }

// ====================================================================== panneau
const OUTILS = [['choisir', '☝', 'Choisir', 'C', 'Choisir des pièces du modèle'], ['pinceau', '🖌', 'Pinceau', 'B', ''], ['gomme', '⌫', 'Gomme', 'E', 'Sur le fond : remet la texture du jeu ; sur un calque : efface'],
  ['remplir', '🪣', 'Remplir', 'G', 'Pièce (esprits) · sélection · couleur proche'], ['pipette', '💧', 'Pipette', 'I', ''], ['baguette', '🪄', 'Baguette', 'W', 'Sélection par couleur · Maj : ajouter · Alt : retirer'],
  ['lasso', '➰', 'Lasso', 'L', 'Sur la texture à plat'], ['rectangle', '⬚', 'Rectangle', 'M', 'Sur la texture à plat'], ['degrade', '◐', 'Dégradé', 'D', 'Glisser sur la texture à plat : couleur 1 → couleur 2'],
  ['eclaircir', '☀', 'Éclaircir', 'O', ''], ['assombrir', '☾', 'Assombrir', 'Maj+O', ''], ['tampon', '⎘', 'Tampon', 'S', 'Alt + clic : source, puis peindre'], ['doigt', '☝︎', 'Doigt', 'R', 'Estomper']];
function atOutil(o) {
  if (o === 'pipette' && A.outil !== 'pipette') A.avantPipette = A.outil;
  A.outil = o; Z.outil = o; const V = E.vue; if (!V) return;
  const perso = !!(E.tech && E.tech.perso);
  V.outil = null;
  V.clicOutil = perso && atOuvert() ? (ev => { if (!Z.pret) return false; const g = at3D(ev);
    zonesChoisir(g ? g.zone : -1, ev.shiftKey || ev.ctrlKey);
    if (g) { const z = Z.zones[g.zone]; majRapport(`Partie ${g.zone + 1} choisie : seule elle se colorie (Maj + clic pour en ajouter, clic dans le vide pour tout).`); void z; }
    return true; }) : null;
  const cur = PINCEAUX.includes(o) ? 'crosshair' : o === 'pipette' ? 'copy' : o === 'remplir' ? 'cell' : o === 'choisir' ? 'pointer' : 'crosshair';
  if (V.cv) V.cv.style.cursor = perso && atOuvert() ? 'pointer' : ''; if ($('zn-plat')) $('zn-plat').style.cursor = cur;
  document.querySelectorAll('[data-at-outil]').forEach(b => b.classList.toggle('actif', b.dataset.atOutil === o));
  const def = OUTILS.find(x => x[0] === o);
  if ($('at-aide')) $('at-aide').textContent = def ? `${def[2]} (${def[3]})${def[4] ? ' · ' + def[4] : ''}` : '';
  if ($('at-opt-pinceau')) $('at-opt-pinceau').style.display = PINCEAUX.includes(o) || o === 'degrade' ? '' : 'none';
  if ($('at-opt-baguette')) $('at-opt-baguette').style.display = o === 'baguette' || o === 'remplir' ? '' : 'none';
  if ($('at-opt-mode')) $('at-opt-mode').style.display = ['pinceau', 'remplir'].includes(o) ? '' : 'none';
  if ($('at-nom-outil')) $('at-nom-outil').textContent = def ? def[2] : '';
  if (window.edOutilChange) edOutilChange(o);
  atMajAffichage();
}
function zonesOutil(o) { atOutil(o === 'aucun' ? 'choisir' : o); }       // (appelé par zones.js)
function zonesPlat() { atPlat(); }
function atMajCouleurs() { if ($('at-ap1')) $('at-ap1').style.background = $('at-c1').value; if ($('at-ap2')) $('at-ap2').style.background = $('at-c2').value; }
function atRecentes() { const b = $('at-recentes'); if (!b) return; b.innerHTML = '';
  for (const c of A.recentes) { const s = document.createElement('button'); s.className = 'zn-pastille'; s.style.background = c; s.title = c + ' (clic droit : couleur 2)';
    s.onclick = () => { $('at-c1').value = c; atMajCouleurs(); }; s.oncontextmenu = ev => { ev.preventDefault(); $('at-c2').value = c; atMajCouleurs(); }; b.appendChild(s); } }
function atPanneau() {
  const d = A.doc, sel = $('at-texture');
  if (sel) { const cles = E.tech ? (E.tech.perso ? Object.keys(Z.tex).concat(Object.keys(Z.tex).map(k => k + 'spm').filter(k => E.textures[k])) :
      Object.keys(E.textures).filter(k => E.textures[k].cur && !E.textures[k].info.donnees)) : [];
    sel.innerHTML = cles.map(k => `<option value="${echapper(k)}"${d && d.cle === k ? ' selected' : ''}>${echapper(E.textures[k].nom)}${E.textures[k].modif ? ' •' : ''}</option>`).join('') || '<option>(aucune texture)</option>'; }
  atCalques(); atHistorique(); atDessinerListes();
}
function atCalques() {
  const b = $('at-calques'); if (!b) return; b.innerHTML = ''; const d = A.doc; if (!d) return;
  const ligne = (c, i) => { const l = document.createElement('div'); l.className = 'at-calque' + (d.actif === i ? ' actif' : '');
    l.innerHTML = c ? `<button class="at-oeil" title="Afficher / masquer">${c.visible ? '👁' : '·'}</button><span class="at-nom">${echapper(c.nom)}</span>
        <select title="Mode de fusion">${MODES_FUSION.map(([k, n]) => `<option value="${k}"${c.mode === k ? ' selected' : ''}>${n}</option>`).join('')}</select>
        <input type="range" min="0" max="100" value="${Math.round(c.opacite * 100)}" title="Opacité">`
      : `<span class="at-oeil">🔒</span><span class="at-nom">Fond (texture${d.x.modif ? ' retouchée' : ' du jeu'})</span>`;
    l.onclick = ev => { if (ev.target.closest('select,input,button')) return; d.actif = i; atCalques(); };
    if (c) { l.querySelector('.at-oeil').onclick = () => atCalqueProp(c, 'visible', !c.visible);
      l.querySelector('select').onchange = e => atCalqueProp(c, 'mode', e.target.value);
      const r = l.querySelector('input'); r.oninput = () => { c.opacite = r.value / 100; atComposer(d); atEnvoyerGPU(d); }; r.onchange = () => { const v = r.value / 100; c.opacite = v; atCalqueProp(c, 'opacite', v); };
      l.querySelector('.at-nom').ondblclick = () => { const n = prompt('Nom du calque :', c.nom); if (n && n.trim()) atCalqueProp(c, 'nom', n.trim()); }; }
    return l; };
  for (let i = d.calques.length - 1; i >= 0; i--) b.appendChild(ligne(d.calques[i], i));
  b.appendChild(ligne(null, -1));
}
function atHistorique() {
  const b = $('at-historique'); if (!b) return; b.innerHTML = '';
  const l0 = document.createElement('div'); l0.className = 'at-pas' + (A.pos === 0 ? ' actif' : ''); l0.textContent = 'Ouverture'; l0.onclick = () => atAllerA(0); b.appendChild(l0);
  A.hist.forEach((p, k) => { const l = document.createElement('div'); l.className = 'at-pas' + (k + 1 === A.pos ? ' actif' : '') + (k + 1 > A.pos ? ' futur' : '');
    l.textContent = p.nom; l.onclick = () => atAllerA(k + 1); b.appendChild(l); });
  b.scrollTop = b.scrollHeight;
}
function atDessinerListes() {
  const s = $('zn-selection'), d = A.doc;
  if (s) { const m = d && atMasque(d); s.style.display = m || Z.sel.size ? '' : 'none';
    let n = 0; if (m) for (let i = 0; i < m.length; i += 7) if (m[i]) n++;
    $('zn-n-sel').textContent = Z.sel.size ? `Sélection : ${Z.sel.size} pièce${Z.sel.size > 1 ? 's' : ''}` : m ? `Sélection : ${Math.max(1, Math.round(n * 7 / m.length * 100))} % de la texture` : ''; }
  zonesDessinerListe();
}
function zonesDessiner() { atDessinerListes(); }
function zonesDessinerListe() {
  const l = $('zn-liste'); if (!l) return;
  const T0 = Object.values(Z.tex)[0], nb = Z.zones.filter(z => z.n > 30).length;
  if ($('zn-info')) $('zn-info').textContent = !E.tech ? '' : E.tech.perso ? (!Z.pret ? 'découpage…' : `${nb} pièces`) : (A.doc ? A.doc.x.nom : 'choisis une texture');
  if ($('zn-n-liste')) $('zn-n-liste').textContent = nb; l.innerHTML = '';
  const tot = T0 ? T0.W * T0.H : 1, liste = Z.zones.filter(z => z.n > 30).sort((a, b) => (Z.sel.has(b.id) - Z.sel.has(a.id)) || b.n - a.n);
  for (const z of liste.slice(0, 80)) { const d = document.createElement('div'); d.className = 'zn-ligne' + (Z.sel.has(z.id) ? ' sel' : '');
    d.innerHTML = `<i style="background:${versHex(z.rgb)}"></i><span>Pièce ${z.id + 1}</span><small>${Math.round(z.n / tot * 1000) / 10} %</small>`;
    d.onclick = ev => zonesChoisir(z.id, ev.shiftKey || ev.ctrlKey);
    d.onmouseenter = () => { Z.survol = z.id; zonesAfficher3D(); }; d.onmouseleave = () => { Z.survol = -1; zonesAfficher3D(); };
    l.appendChild(d); }
}

// ---------------------------------------------------------------------- texture à plat : zoom, déplacement, superpositions
function atVersTexture(cv, ev) { const r = cv.getBoundingClientRect(), d = A.doc; if (!d) return null;
  const sx = (ev.clientX - r.left) * cv.width / r.width, sy = (ev.clientY - r.top) * cv.height / r.height, s = A.vue.zoom * cv.width / d.W;
  return [(sx - A.vue.ox) / s, (sy - A.vue.oy) / s]; }
let atAttentePlat = false, atFourmis = 0;
function atPlat() {
  if (atAttentePlat) return; atAttentePlat = true;
  requestAnimationFrame(() => { atAttentePlat = false;
    const cv = $('zn-plat'); if (!cv) return; const boite = cv.parentElement;
    if (boite && boite.clientWidth > 40) { const c = Math.max(120, Math.min(boite.clientWidth, boite.clientHeight) - 20) + 'px';   // toile carrée, la plus grande possible
      if (cv.style.width !== c) { cv.style.width = c; cv.style.height = c; } }
    const r = cv.getBoundingClientRect();
    if (r.width > 10 && Math.abs(cv.width - Math.round(r.width)) > 2) { cv.width = Math.round(r.width); cv.height = Math.round(r.width); }
    const x = cv.getContext('2d'), d = A.doc; x.setTransform(1, 0, 0, 1, 0, 0);
    if (window.edFond) edFond(x, cv); else for (let yy = 0; yy < cv.height; yy += 16) for (let xx = 0; xx < cv.width; xx += 16) { x.fillStyle = ((xx + yy) / 16) % 2 ? '#1b1e26' : '#14161c'; x.fillRect(xx, yy, 16, 16); }
    if (!d) return; const s = A.vue.zoom * cv.width / d.W;
    x.imageSmoothingEnabled = A.vue.zoom < 2; x.setTransform(s, 0, 0, s, A.vue.ox, A.vue.oy); x.drawImage(texAffichee(d.x), 0, 0);
    x.setTransform(1, 0, 0, 1, 0, 0);
    const T = Z.tex[d.cle], m = atMasque(d), surv = T && (Z.sel.size || Z.survol >= 0);
    if (m || surv) { const o = x.getImageData(0, 0, cv.width, cv.height), a = o.data, Wc = cv.width; atFourmis = (atFourmis + 1) % 8;
      const tex = (px, py) => { const tx = Math.floor((px - A.vue.ox) / s), ty = Math.floor((py - A.vue.oy) / s); return tx < 0 || ty < 0 || tx >= d.W || ty >= d.H ? -1 : ty * d.W + tx; };
      for (let py = 0; py < cv.height; py++) for (let px = 0; px < Wc; px++) { const p = tex(px, py), i = (py * Wc + px) * 4; if (p < 0) continue;
        if (surv && !m) { const z = T.label[p], dedans = z >= 0 && (Z.sel.has(z) || z === Z.survol); if (!dedans) { a[i] *= 0.35; a[i + 1] *= 0.35; a[i + 2] *= 0.35; } continue; }
        if (m) { const dedans = m[p] > 127; if (!dedans) { a[i] *= 0.55; a[i + 1] *= 0.55; a[i + 2] *= 0.6; continue; }
          const pv = [tex(px - 1, py), tex(px + 1, py), tex(px, py - 1), tex(px, py + 1)];
          if (pv.some(q => q < 0 || m[q] <= 127)) { const c = ((px + py) >> 2) % 2 ? 255 : 20; a[i] = a[i + 1] = a[i + 2] = c; } } }
      x.putImageData(o, 0, 0); }
    // lasso / rectangle / dégradé en cours, rond du pinceau
    x.setTransform(s, 0, 0, s, A.vue.ox, A.vue.oy); x.lineWidth = 1.5 / s;
    if (A.lasso && A.lasso.length > 1) { x.strokeStyle = '#ffd34d'; x.beginPath(); A.lasso.forEach((p, k) => k ? x.lineTo(p[0], p[1]) : x.moveTo(p[0], p[1])); x.stroke(); }
    if (A.rect) { x.strokeStyle = '#ffd34d'; x.strokeRect(A.rect[0], A.rect[1], A.rect[2] - A.rect[0], A.rect[3] - A.rect[1]); }
    if (A.degrade) { x.strokeStyle = '#ffffff'; x.beginPath(); x.moveTo(A.degrade[0][0], A.degrade[0][1]); x.lineTo(A.degrade[1][0], A.degrade[1][1]); x.stroke(); }
    if (A.curseur && PINCEAUX.includes(A.outil)) { x.strokeStyle = 'rgba(255,255,255,.8)'; x.beginPath(); x.arc(A.curseur[0], A.curseur[1], +$('at-taille').value, 0, Math.PI * 2); x.stroke(); }
    if (A.tampon && A.outil === 'tampon') { x.strokeStyle = '#4ad0ff'; x.beginPath(); x.arc(A.tampon.src[0], A.tampon.src[1], 4 / s, 0, Math.PI * 2); x.stroke(); }
    if (window.edApercu) edApercu(x, s);
    x.setTransform(1, 0, 0, 1, 0, 0);
  });
}
function atBrancherPlat() {
  const cv = $('zn-plat'); if (!cv) return; let geste = null, pan = null;
  cv.addEventListener('contextmenu', e => e.preventDefault());
  cv.addEventListener('wheel', ev => { ev.preventDefault(); const r = cv.getBoundingClientRect(), sx = (ev.clientX - r.left) * cv.width / r.width, sy = (ev.clientY - r.top) * cv.height / r.height;
    const z0 = A.vue.zoom, z1 = Math.max(1, Math.min(16, z0 * Math.exp(-ev.deltaY * 0.0015))); A.vue.ox = sx - (sx - A.vue.ox) * z1 / z0; A.vue.oy = sy - (sy - A.vue.oy) * z1 / z0; A.vue.zoom = z1;
    if (z1 === 1) { A.vue.ox = 0; A.vue.oy = 0; } atPlat(); }, { passive: false });
  cv.addEventListener('mousedown', ev => {
    const d = A.doc; if (!d) return; ev.preventDefault();
    if (ev.button === 1 || ev.button === 2 || (ev.button === 0 && (A.espace || A.outil === 'main'))) { pan = [ev.clientX, ev.clientY, A.vue.ox, A.vue.oy]; return; }
    if (ev.button !== 0) return; const [tx, ty] = atVersTexture(cv, ev), T = Z.tex[d.cle], zone = T ? T.label[Math.max(0, Math.min(d.H - 1, ty | 0)) * d.W + Math.max(0, Math.min(d.W - 1, tx | 0))] : -1;
    if (window.edSouris && edSouris('debut', d, tx, ty, ev)) { geste = 'ed'; return; }
    if (A.outil === 'lasso') { A.lasso = [[tx, ty]]; geste = 'lasso'; return; }
    if (A.outil === 'rectangle') { A.rect = [tx, ty, tx, ty]; geste = 'rect'; return; }
    if (A.outil === 'degrade') { A.degrade = [[tx, ty], [tx, ty]]; geste = 'degrade'; return; }
    if (PINCEAUX.includes(A.outil)) { geste = 'pinceau'; atGeste('debut', d, tx, ty, zone, ev); return; }
    atGeste('clic', d, tx, ty, zone, ev); });
  window.addEventListener('mousemove', ev => {
    if (pan) { const r = cv.getBoundingClientRect(), k = cv.width / r.width; A.vue.ox = pan[2] + (ev.clientX - pan[0]) * k; A.vue.oy = pan[3] + (ev.clientY - pan[1]) * k; atPlat(); return; }
    const d = A.doc; if (!d) return;
    if (ev.target === cv || geste) { const t = atVersTexture(cv, ev); A.curseur = t; if (!geste) atPlat(); }
    if (!geste) return; const [tx, ty] = atVersTexture(cv, ev);
    if (geste === 'lasso') { A.lasso.push([tx, ty]); atPlat(); } else if (geste === 'rect') { A.rect[2] = tx; A.rect[3] = ty; atPlat(); }
    else if (geste === 'degrade') { A.degrade[1] = [tx, ty]; atPlat(); } else if (geste === 'pinceau') atGeste('bouger', d, tx, ty, undefined, ev);
    else if (geste === 'ed') edSouris('bouger', d, tx, ty, ev); });
  window.addEventListener('mouseup', ev => {
    if (pan) { pan = null; return; } if (!geste) return; const g = geste, d = A.doc; geste = null;
    if (g === 'lasso') { const pts = A.lasso; A.lasso = null; if (pts.length > 2) atPolygone(d, pts, ev); else atSelRien(); }
    else if (g === 'rect') { const [a, b, c, e] = A.rect; A.rect = null; if (Math.abs(c - a) > 1 && Math.abs(e - b) > 1) atPolygone(d, [[a, b], [c, b], [c, e], [a, e]], ev); else atSelRien(); }
    else if (g === 'degrade') { const [a, b] = A.degrade; A.degrade = null; if (Math.hypot(b[0] - a[0], b[1] - a[1]) > 2) atDegrade(d, a, b); else atPlat(); }
    else if (g === 'pinceau') atGeste('fin');
    else if (g === 'ed') edSouris('fin', d, 0, 0, ev);
    atPlat(); });
  cv.addEventListener('mouseleave', () => { A.curseur = null; atPlat(); });
}

// ---------------------------------------------------------------------- branchements, raccourcis
function atBrancher() {
  if (!$('atelier-dessin')) return;
  try { A.recentes = JSON.parse(localStorage.getItem('atelier_couleurs_recentes') || '[]'); } catch (e) { A.recentes = []; }
  // barre verticale (comme Photoshop) : groupes séparés ; le nom est dans l'infobulle et dans la barre d'options
  const ordre = ['choisir', 'pipette', '|', 'pinceau', 'gomme', 'doigt', 'tampon', 'eclaircir', 'assombrir', '|', 'remplir', 'degrade', '|', 'baguette', 'lasso', 'rectangle', '|',
    'ligne', 'formes', 'motifs', 'texte', 'image', 'main'];   // (outils de l'ancien éditeur : atelier_outils.js)
  const bar = $('at-outils'); bar.innerHTML = ordre.map(k => { if (k === '|') return '<hr>'; const [, ic, n, t, a] = OUTILS.find(x => x[0] === k);
    return `<button data-at-outil="${k}" title="${n} (${t})${a ? ' · ' + a : ''}"><b>${ic}</b><span>${n}</span></button>`; }).join('');
  bar.querySelectorAll('[data-at-outil]').forEach(b => b.onclick = () => atOutil(b.dataset.atOutil));
  document.querySelectorAll('[data-at-mode]').forEach(b => b.onclick = () => { A.mode = b.dataset.atMode; document.querySelectorAll('[data-at-mode]').forEach(x => x.classList.toggle('actif', x === b)); });
  document.querySelector('[data-at-mode="ombrage"]').classList.add('actif');
  $('at-c1').oninput = atMajCouleurs; $('at-c2').oninput = atMajCouleurs; $('at-echanger').onclick = () => { const a = $('at-c1').value; $('at-c1').value = $('at-c2').value; $('at-c2').value = a; atMajCouleurs(); };
  for (const [id, suf] of [['at-taille', ' px'], ['at-durete', ' %'], ['at-opacite', ' %'], ['at-flux', ' %'], ['at-tol', ''], ['at-adoucir', ' px'], ['zn-lum', ' %']]) {
    const e = $(id); if (!e) continue; const v = e.parentElement.querySelector('.val') || e.nextElementSibling; e.addEventListener('input', () => { if (v) v.textContent = e.value + suf; }); }
  if ($('at-entrer')) $('at-entrer').onclick = () => atDessinOuvrir();
  $('at-terminer').onclick = atDessinFermer; addEventListener('resize', () => { if (atOuvert()) atPlat(); });
  $('zn-annuler').onclick = atAnnuler; $('zn-retablir').onclick = atRetablir;
  $('zn-appliquer').onclick = () => { const d = A.doc, m = d && atMasque(d); if (m) atRemplirMasque(d, m, 'Remplir la sélection'); else majRapport('Rien de sélectionné.'); };
  $('zn-pareil').onclick = () => { zonesPareilles(); };
  $('zn-rien').onclick = atSelRien; $('at-sel-tout').onclick = atSelTout; $('at-sel-inv').onclick = atSelInverser; $('at-sel-adoucir').onclick = atSelAdoucir;
  document.querySelectorAll('[data-at-reglage]').forEach(b => b.onclick = () => atReglageOuvrir(b.dataset.atReglage));
  $('at-c-plus').onclick = () => atCalqueAjouter('normal'); $('at-c-couleur').onclick = () => atCalqueAjouter('couleur'); $('at-c-dup').onclick = atCalqueDupliquer;
  $('at-c-sup').onclick = atCalqueSupprimer; $('at-c-fus').onclick = atCalqueFusionner; $('at-c-haut').onclick = () => atCalqueDeplacer(1); $('at-c-bas').onclick = () => atCalqueDeplacer(-1);
  $('at-texture').onchange = e => atActiver(e.target.value);
  document.querySelectorAll('[data-at-onglet]').forEach(b => b.onclick = () => atOnglet(b.dataset.atOnglet));
  $('at-zoom-plus').onclick = () => { A.vue.zoom = Math.min(16, A.vue.zoom * 1.5); atPlat(); }; $('at-zoom-moins').onclick = () => { A.vue.zoom = Math.max(1, A.vue.zoom / 1.5); if (A.vue.zoom === 1) A.vue.ox = A.vue.oy = 0; atPlat(); };
  $('at-zoom-ajuster').onclick = () => { A.vue = { zoom: 1, ox: 0, oy: 0 }; atPlat(); };
  atRecentes(); atMajCouleurs(); atBrancherPlat();
  document.addEventListener('keydown', ev => {
    if (ev.code === 'Space' && document.activeElement === document.body && document.body.classList.contains('onglet-esprits') + document.body.classList.contains('onglet-totems')) A.espace = true;
    if (!E.tech || !atOuvert() || document.body.classList.contains('edition')) return;
    if (/INPUT|TEXTAREA|SELECT/.test(document.activeElement.tagName) && !['range', 'checkbox', 'color'].includes(document.activeElement.type)) return;
    const k = ev.key.toLowerCase(), ctrl = ev.ctrlKey || ev.metaKey; let fait = true;
    if (ctrl && k === 'z' && !ev.shiftKey) atAnnuler(); else if (ctrl && (k === 'y' || (k === 'z' && ev.shiftKey))) atRetablir();
    else if (ctrl && k === 'd') atSelRien(); else if (ctrl && ev.shiftKey && k === 'i') atSelInverser(); else if (ctrl && k === 'a') atSelTout(); else if (ctrl && k === 'j') atCalqueDupliquer();
    else if (ctrl) fait = false;
    else if (k === 'escape') { if (A.reglage) atReglageFermer(false); else atDessinFermer(); }
    else if (k === 'x') $('at-echanger').onclick();
    else if (k === '[' || k === ']') { const t = $('at-taille'); t.value = Math.max(1, Math.min(120, +t.value + (k === ']' ? 3 : -3))); t.dispatchEvent(new Event('input')); atPlat(); }
    else { const def = OUTILS.find(x => x[3].toLowerCase() === (ev.shiftKey ? 'maj+' + k : k)); if (def) atOutil(def[0]); else fait = false; }
    if (fait) { ev.preventDefault(); ev.stopImmediatePropagation(); } }, true);
  document.addEventListener('keyup', ev => { if (ev.code === 'Space') A.espace = false; });
  // changement d'onglet (app.js réécrit la classe du corps) : le mode dessin se ferme, la vue 3D retrouve ses gestes
  new MutationObserver(() => { if (!atOuvert() && E.vue && E.vue.clicOutil) { E.vue.clicOutil = null; E.vue.cv.style.cursor = ''; } }).observe(document.body, { attributes: true, attributeFilter: ['class'] });
  atOutil('choisir');
}
addEventListener('DOMContentLoaded', atBrancher);
