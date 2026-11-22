'use strict';
// (15/11/2026) OUTILS DE L'ANCIEN ÉDITEUR, maintenant DANS LE MODE DESSIN (un seul endroit pour tout dessiner) :
// trait droit, formes, motifs, texte, image, déplacer + palette, fond damier / noir / blanc, « garder la forme » (transparence).
// Ils posent sur le calque actif (ou le fond), seulement dans la sélection / la partie choisie, avec l'historique commun.
// Formes et motifs repris de editeur.html (gardé tel quel). Ce sont des outils d'édition : aucune règle du jeu ici.

const ED = { forme: 'etoile', remplissage: 'plein', contour: 8, trait: 12, opacite: 100, motif: 'rayures_d', largeur: 40, espacement: 40, angle: 45, rayon: 16,
  texte: 'INAZUMA', police: 'Arial Black', tTaille: 160, tContour: 0, rotation: 0, imgTaille: 400, fond: 'damier', logo: null, glisse: null };
try { Object.assign(ED, JSON.parse(localStorage.getItem('atelier_outils') || '{}')); } catch (e) {}
ED.logo = null; ED.glisse = null;
const edMemo = () => { try { const { logo, glisse, ...r } = ED; localStorage.setItem('atelier_outils', JSON.stringify(r)); } catch (e) {} };
const ED_OUTILS = ['ligne', 'formes', 'motifs', 'texte', 'image'];
OUTILS.push(['ligne', '╱', 'Trait droit', 'U', 'Glisser · Maj : angles de 15°'], ['formes', '⬟', 'Formes', 'F', 'Glisser pour dessiner la forme · Maj : proportions gardées'],
  ['motifs', '▦', 'Motifs', 'N', 'Clic : poser le motif sur la partie / la sélection (sinon toute la texture)'], ['texte', 'T', 'Texte', 'T', 'Écris le texte à droite, puis clique pour le poser'],
  ['image', '🖼', 'Image', 'P', 'Choisis une image à droite, puis clique pour la poser'], ['main', '✋', 'Déplacer', 'H', 'Glisser : déplacer la vue · molette : zoom']);
const PALETTE_ED = ['#ffffff', '#d9dde4', '#9aa0aa', '#4a4f58', '#1a1a1a', '#000000', '#e3262e', '#a3101c', '#ff7a1a', '#ffc800', '#ffe66b', '#c9a227',
  '#1fa34a', '#0b6e3a', '#7ed957', '#00a3a3', '#3ab7ff', '#1d6fe0', '#14388f', '#0b1f4d', '#7a3fd1', '#c43fa6', '#ff8fc1', '#7a4a26'];
const edC1 = () => $('at-c1').value, edC2 = () => $('at-c2').value;

// ---------------------------------------------------------------------- formes et motifs (repris de editeur.html)
function edPoly(x, b, pts) { x.beginPath(); pts.forEach(([u, v], i) => (i ? x.lineTo : x.moveTo).call(x, b.x + u * b.w, b.y + v * b.h)); x.closePath(); }
const ED_FORMES = {
  rectangle: (x, b) => x.rect(b.x, b.y, b.w, b.h),
  arrondi: (x, b) => { const r = Math.min(Math.abs(b.w), Math.abs(b.h)) * 0.22; x.roundRect ? x.roundRect(b.x, b.y, b.w, b.h, r) : x.rect(b.x, b.y, b.w, b.h); },
  rond: (x, b) => x.ellipse(b.x + b.w / 2, b.y + b.h / 2, Math.abs(b.w / 2), Math.abs(b.h / 2), 0, 0, Math.PI * 2),
  etoile: (x, b) => edPoly(x, b, Array.from({ length: 10 }, (_, i) => { const a = -Math.PI / 2 + i * Math.PI / 5, r = i % 2 ? 0.4 : 1; return [0.5 + Math.cos(a) * r * 0.5, 0.53 + Math.sin(a) * r * 0.5]; })),
  eclair: (x, b) => edPoly(x, b, [[0.62, 0], [0.12, 0.56], [0.45, 0.56], [0.3, 1], [0.88, 0.38], [0.54, 0.38], [0.74, 0]]),
  coeur: (x, b) => { const X = v => b.x + v * b.w, Y = v => b.y + v * b.h; x.moveTo(X(0.5), Y(0.95));
    x.bezierCurveTo(X(-0.15), Y(0.5), X(0.1), Y(-0.05), X(0.5), Y(0.25)); x.bezierCurveTo(X(0.9), Y(-0.05), X(1.15), Y(0.5), X(0.5), Y(0.95)); x.closePath(); },
  triangle: (x, b) => edPoly(x, b, [[0.5, 0], [1, 1], [0, 1]]),
  losange: (x, b) => edPoly(x, b, [[0.5, 0], [1, 0.5], [0.5, 1], [0, 0.5]]),
  chevron: (x, b) => edPoly(x, b, [[0, 0], [0.5, 0.55], [1, 0], [1, 0.45], [0.5, 1], [0, 0.45]]),
  fleche: (x, b) => edPoly(x, b, [[0, 0.35], [0.6, 0.35], [0.6, 0.1], [1, 0.5], [0.6, 0.9], [0.6, 0.65], [0, 0.65]]),
  bouclier: (x, b) => { const X = v => b.x + v * b.w, Y = v => b.y + v * b.h;
    x.moveTo(X(0.06), Y(0.04)); x.lineTo(X(0.94), Y(0.04)); x.lineTo(X(0.94), Y(0.45)); x.quadraticCurveTo(X(0.9), Y(0.85), X(0.5), Y(1));
    x.quadraticCurveTo(X(0.1), Y(0.85), X(0.06), Y(0.45)); x.closePath(); },
  croix: (x, b) => edPoly(x, b, [[0.35, 0], [0.65, 0], [0.65, 0.35], [1, 0.35], [1, 0.65], [0.65, 0.65], [0.65, 1], [0.35, 1], [0.35, 0.65], [0, 0.65], [0, 0.35], [0.35, 0.35]]),
};
const ED_NOMS_FORMES = { rectangle: 'Carré', arrondi: 'Arrondi', rond: 'Rond', etoile: 'Étoile', eclair: 'Éclair', coeur: 'Cœur', triangle: 'Triangle', losange: 'Losange', chevron: 'Chevron', fleche: 'Flèche', bouclier: 'Blason', croix: 'Croix' };
function edForme(x, nom, b) {
  x.beginPath(); ED_FORMES[nom](x, b);
  if (ED.remplissage !== 'contour') { x.fillStyle = edC1(); x.fill(); }
  if (ED.remplissage !== 'plein') { x.lineWidth = ED.contour; x.lineJoin = 'round'; x.strokeStyle = ED.remplissage === 'contour' ? edC1() : edC2(); x.stroke(); }
}
const ED_MOTIFS = { rayures_v: 'Rayures', rayures_h: 'Cerceaux', rayures_d: 'Diagonales', damier: 'Damier', pois: 'Pois', chevrons: 'Chevrons',
  bande_v: 'Bande', bande_h: 'Bande ventre', echarpe: 'Écharpe', moitie: 'Moitié', degrade: 'Dégradé', zigzag: 'Zigzag', carreaux: 'Carreaux', eclairs: 'Éclairs', etoiles: 'Étoiles', fines: 'Fines rayures' };
function edMotif(x, nom, b, opts) {
  const o = Object.assign({ c1: edC1(), c2: edC2(), l: ED.largeur, e: ED.espacement, a: ED.angle, r: ED.rayon }, opts || {}), pas = o.l + o.e;
  x.save(); x.fillStyle = o.c1; x.strokeStyle = o.c1; x.beginPath(); x.rect(b.x, b.y, b.w, b.h); x.clip();
  const cx = b.x + b.w / 2, cy = b.y + b.h / 2, R = Math.hypot(b.w, b.h);
  switch (nom) {
    case 'rayures_v': for (let X = cx - o.l / 2 - Math.ceil(b.w / pas) * pas; X < b.x + b.w; X += pas) x.fillRect(X, b.y, o.l, b.h); break;
    case 'fines': for (let X = b.x; X < b.x + b.w; X += Math.max(4, o.e / 2)) x.fillRect(X, b.y, Math.max(2, o.l / 6), b.h); break;
    case 'rayures_h': for (let Y = cy - o.l / 2 - Math.ceil(b.h / pas) * pas; Y < b.y + b.h; Y += pas) x.fillRect(b.x, Y, b.w, o.l); break;
    case 'rayures_d': x.translate(cx, cy); x.rotate(o.a * Math.PI / 180); for (let X = -R; X < R; X += pas) x.fillRect(X, -R, o.l, 2 * R); break;
    case 'damier': { const c = Math.max(4, o.l); for (let Y = b.y, j = 0; Y < b.y + b.h; Y += c, j++) for (let X = b.x, i = 0; X < b.x + b.w; X += c, i++) if ((i + j) % 2 === 0) x.fillRect(X, Y, c, c); break; }
    case 'carreaux': x.globalAlpha = 0.55; for (let X = b.x; X < b.x + b.w; X += pas) x.fillRect(X, b.y, o.l / 2, b.h); for (let Y = b.y; Y < b.y + b.h; Y += pas) x.fillRect(b.x, Y, b.w, o.l / 2); break;
    case 'pois': { const p = o.r * 2 + o.e; for (let Y = b.y + p / 2, j = 0; Y < b.y + b.h + p; Y += p, j++) for (let X = b.x + (j % 2) * p / 2; X < b.x + b.w + p; X += p) { x.beginPath(); x.arc(X, Y, o.r, 0, Math.PI * 2); x.fill(); } break; }
    case 'etoiles': { const p = o.r * 3 + o.e; for (let Y = b.y + p / 2, j = 0; Y < b.y + b.h + p; Y += p, j++) for (let X = b.x + (j % 2) * p / 2; X < b.x + b.w + p; X += p) { x.beginPath(); ED_FORMES.etoile(x, { x: X - o.r * 1.4, y: Y - o.r * 1.4, w: o.r * 2.8, h: o.r * 2.8 }); x.fill(); } break; }
    case 'eclairs': { const p = o.r * 3 + o.e; for (let Y = b.y + p / 2, j = 0; Y < b.y + b.h + p; Y += p, j++) for (let X = b.x + (j % 2) * p / 2; X < b.x + b.w + p; X += p) { x.beginPath(); ED_FORMES.eclair(x, { x: X - o.r, y: Y - o.r * 1.5, w: o.r * 2, h: o.r * 3 }); x.fill(); } break; }
    case 'chevrons': x.lineWidth = o.l; x.lineJoin = 'miter'; for (let Y = b.y - b.w / 2; Y < b.y + b.h + pas; Y += pas) { x.beginPath(); x.moveTo(b.x - 10, Y); x.lineTo(cx, Y + b.w * 0.35); x.lineTo(b.x + b.w + 10, Y); x.stroke(); } break;
    case 'zigzag': x.lineWidth = Math.max(4, o.l / 2); for (let Y = b.y; Y < b.y + b.h + pas; Y += pas) { x.beginPath(); for (let X = b.x - pas, i = 0; X < b.x + b.w + pas; X += pas / 2, i++) x.lineTo(X, Y + (i % 2 ? pas / 3 : 0)); x.stroke(); } break;
    case 'bande_v': x.fillRect(cx - o.l, b.y, o.l * 2, b.h); break;
    case 'bande_h': x.fillRect(b.x, b.y + b.h * 0.3, b.w, o.l * 2); break;
    case 'echarpe': x.translate(cx, cy); x.rotate(o.a * Math.PI / 180); x.fillRect(-o.l, -R, o.l * 2, 2 * R); break;
    case 'moitie': x.fillRect(b.x, b.y, b.w / 2, b.h); break;
    case 'degrade': { const g = x.createLinearGradient(0, b.y, 0, b.y + b.h); g.addColorStop(0, o.c1); g.addColorStop(1, o.c2); x.fillStyle = g; x.fillRect(b.x, b.y, b.w, b.h); break; }
  }
  x.restore();
}
function edTexte(x, p) {
  x.save(); x.translate(p[0], p[1]); x.rotate(ED.rotation * Math.PI / 180);
  x.font = `bold ${ED.tTaille}px "${ED.police}", sans-serif`; x.textAlign = 'center'; x.textBaseline = 'middle';
  if (ED.tContour > 0) { x.lineWidth = ED.tContour * 2; x.lineJoin = 'round'; x.strokeStyle = edC2(); x.strokeText(ED.texte, 0, 0); }
  x.fillStyle = edC1(); x.fillText(ED.texte, 0, 0); x.restore();
}
function edLogo(x, p) {
  const L = ED.logo, k = ED.imgTaille / Math.max(L.width, L.height);
  x.save(); x.translate(p[0], p[1]); x.rotate(ED.rotation * Math.PI / 180); x.drawImage(L, -L.width * k / 2, -L.height * k / 2, L.width * k, L.height * k); x.restore();
}
function edBoite(a, b, carre) {
  let w = b[0] - a[0], h = b[1] - a[1];
  if (carre) { const m = Math.max(Math.abs(w), Math.abs(h)); w = Math.sign(w || 1) * m; h = Math.sign(h || 1) * m; }
  return { x: Math.min(a[0], a[0] + w), y: Math.min(a[1], a[1] + h), w: Math.abs(w), h: Math.abs(h) };
}
function edDroit(a, b) { const ang = Math.atan2(b[1] - a[1], b[0] - a[0]), pas = Math.PI / 12, r = Math.hypot(b[0] - a[0], b[1] - a[1]), q = Math.round(ang / pas) * pas;
  return [a[0] + Math.cos(q) * r, a[1] + Math.sin(q) * r]; }
// zone visée par un motif : la boîte de la sélection (ou de la partie choisie), sinon toute la texture
function edBoiteCible(d) { const m = atMasque(d); if (!m) return { x: 0, y: 0, w: d.W, h: d.H };
  let x0 = d.W, y0 = d.H, x1 = -1, y1 = -1;
  for (let p = 0; p < m.length; p++) if (m[p]) { const x = p % d.W, y = (p - x) / d.W; if (x < x0) x0 = x; if (x > x1) x1 = x; if (y < y0) y0 = y; if (y > y1) y1 = y; }
  return x1 < 0 ? { x: 0, y: 0, w: d.W, h: d.H } : { x: x0, y: y0, w: x1 - x0 + 1, h: y1 - y0 + 1 }; }

// ---------------------------------------------------------------------- pose : dessin -> calque actif (ou fond), dans la sélection
function edVerrou() { return !$('at-verrou') || $('at-verrou').checked; }
function edPoser(nom, dessin) {
  const d = A.doc; if (!d) return;
  const t = document.createElement('canvas'); t.width = d.W; t.height = d.H; const x = t.getContext('2d', { willReadFrequently: true }); dessin(x);
  const s = x.getImageData(0, 0, d.W, d.H).data, m = atMasque(d), opa = ED.opacite / 100, verrou = edVerrou(), cal = !!atCalque(d);
  const forme = d.comp ? d.comp.data : d.fond, av = atAvantPixels(d), px = atPixels(d), r = [1e9, 1e9, -1e9, -1e9]; let n = 0;
  for (let p = 0, N = d.W * d.H; p < N; p++) { const i = p * 4; if (!s[i + 3]) continue;
    let w = s[i + 3] / 255 * opa; if (m) w *= m[p] / 255; if (verrou) w *= forme[i + 3] / 255; if (w <= 0) continue;
    const xx = p % d.W, yy = (p - xx) / d.W; n++;
    if (xx < r[0]) r[0] = xx; if (yy < r[1]) r[1] = yy; if (xx + 1 > r[2]) r[2] = xx + 1; if (yy + 1 > r[3]) r[3] = yy + 1;
    if (cal) { const a0 = px[i + 3] / 255, a1 = a0 + w * (1 - a0); for (let j = 0; j < 3; j++) px[i + j] = a1 > 0 ? (px[i + j] * a0 * (1 - w) + s[i + j] * w) / a1 : 0; px[i + 3] = a1 * 255; }
    else { for (let j = 0; j < 3; j++) px[i + j] = px[i + j] * (1 - w) + s[i + j] * w; if (!verrou) px[i + 3] = px[i + 3] + w * (255 - px[i + 3]); } }
  if (!n) return majRapport(m ? 'Rien à poser : c’est en dehors de la partie / la sélection.' : 'Rien à poser ici (texture transparente : décoche « Garder la forme »).');
  atRetenir(edC1()); atApresPixels(d, nom, av, r);
}
function edSouris(type, d, tx, ty, ev) {
  const o = A.outil;
  if (type === 'debut') {
    if (o === 'ligne' || o === 'formes') { ED.glisse = { a: [tx, ty], b: [tx, ty], maj: ev.shiftKey }; return true; }
    if (o === 'texte') { if (!ED.texte.trim()) majRapport('Écris d’abord le texte (panneau de droite).'); else edPoser('Texte', x => edTexte(x, [tx, ty])); return true; }
    if (o === 'image') { if (!ED.logo) majRapport('Choisis d’abord une image (panneau de droite).'); else edPoser('Image', x => edLogo(x, [tx, ty])); return true; }
    if (o === 'motifs') { const b = edBoiteCible(d); edPoser('Motif · ' + ED_MOTIFS[ED.motif], x => edMotif(x, ED.motif, b)); return true; }
    return false; }
  if (!ED.glisse) return false;
  if (type === 'bouger') { ED.glisse.b = [tx, ty]; ED.glisse.maj = ev.shiftKey; atPlat(); return true; }
  const g = ED.glisse; ED.glisse = null;
  if (o === 'ligne') { const b = g.maj ? edDroit(g.a, g.b) : g.b; if (Math.hypot(b[0] - g.a[0], b[1] - g.a[1]) > 1)
    edPoser('Trait droit', x => { x.strokeStyle = edC1(); x.lineWidth = ED.trait; x.lineCap = 'round'; x.beginPath(); x.moveTo(g.a[0], g.a[1]); x.lineTo(b[0], b[1]); x.stroke(); }); }
  else if (o === 'formes') { const b = edBoite(g.a, g.b, g.maj); if (b.w > 2 && b.h > 2) edPoser('Forme · ' + ED_NOMS_FORMES[ED.forme], x => edForme(x, ED.forme, b)); }
  atPlat(); return true;
}
// aperçu sur la texture à plat (x est déjà à l'échelle de la texture, s = pixels écran par pixel de texture)
function edApercu(x, s) {
  const o = A.outil, d = A.doc; if (!d || !ED_OUTILS.includes(o)) return;
  x.save(); x.globalAlpha = 0.75 * ED.opacite / 100;
  if (ED.glisse && o === 'ligne') { const b = ED.glisse.maj ? edDroit(ED.glisse.a, ED.glisse.b) : ED.glisse.b;
    x.strokeStyle = edC1(); x.lineWidth = ED.trait; x.lineCap = 'round'; x.beginPath(); x.moveTo(ED.glisse.a[0], ED.glisse.a[1]); x.lineTo(b[0], b[1]); x.stroke(); }
  else if (ED.glisse && o === 'formes') { const b = edBoite(ED.glisse.a, ED.glisse.b, ED.glisse.maj); edForme(x, ED.forme, b);
    x.globalAlpha = 1; x.setLineDash([8 / s, 6 / s]); x.lineWidth = 1.5 / s; x.strokeStyle = '#fff'; x.strokeRect(b.x, b.y, b.w, b.h); x.setLineDash([]); }
  else if (o === 'motifs' && A.curseur) { x.globalAlpha = 0.5; edMotif(x, ED.motif, edBoiteCible(d)); }
  else if (o === 'texte' && A.curseur && ED.texte.trim()) edTexte(x, A.curseur);
  else if (o === 'image' && A.curseur && ED.logo) edLogo(x, A.curseur);
  x.restore();
}
// fond derrière la texture à plat (parties transparentes) : damier, noir (comme les effets additifs), blanc
function edFond(x, cv) {
  if (ED.fond === 'noir' || ED.fond === 'blanc') { x.fillStyle = ED.fond === 'noir' ? '#000' : '#fff'; x.fillRect(0, 0, cv.width, cv.height); return; }
  for (let yy = 0; yy < cv.height; yy += 16) for (let xx = 0; xx < cv.width; xx += 16) { x.fillStyle = ((xx + yy) / 16) % 2 ? '#1b1e26' : '#14161c'; x.fillRect(xx, yy, 16, 16); }
}

// ---------------------------------------------------------------------- panneau « Options de l'outil » (à droite) et palette
function edCurseur(lib, cle, min, max, unite) {
  const d = document.createElement('label'); d.className = 'ed-ligne';
  d.innerHTML = `<span>${lib}</span><input type="range" min="${min}" max="${max}" value="${Math.min(max, ED[cle])}"><span class="val">${Math.min(max, ED[cle])}${unite || ''}</span>`;
  const i = d.querySelector('input'), v = d.querySelector('.val'); i.oninput = () => { ED[cle] = +i.value; v.textContent = i.value + (unite || ''); edMemo(); atPlat(); };
  return d;
}
function edPuces(cle, liste) {
  const c = document.createElement('div'); c.className = 'ed-puces';
  for (const [v, l] of liste) { const b = document.createElement('button'); b.textContent = l; b.classList.toggle('actif', ED[cle] === v);
    b.onclick = () => { ED[cle] = v; edMemo(); c.querySelectorAll('button').forEach(x => x.classList.toggle('actif', x === b)); atPlat(); }; c.appendChild(b); }
  return c;
}
function edGalerie(liste, cle, vignette) {
  const g = document.createElement('div'); g.className = 'ed-galerie';
  for (const [k, nom] of Object.entries(liste)) { const v = document.createElement('button'); v.className = 'ed-vignette' + (ED[cle] === k ? ' actif' : ''); v.title = nom;
    v.innerHTML = `<canvas width="48" height="48"></canvas><span>${nom}</span>`; vignette(v.querySelector('canvas'), k);
    v.onclick = () => { ED[cle] = k; edMemo(); g.querySelectorAll('.ed-vignette').forEach(e => e.classList.toggle('actif', e === v)); atPlat(); }; g.appendChild(v); }
  return g;
}
function edVignetteForme(c, k) { const x = c.getContext('2d'); x.clearRect(0, 0, 48, 48); x.beginPath(); ED_FORMES[k](x, { x: 7, y: 7, w: 34, h: 34 }); x.fillStyle = edC1(); x.fill(); x.lineWidth = 2; x.strokeStyle = 'rgba(0,0,0,.4)'; x.stroke(); }
function edVignetteMotif(c, k) { const x = c.getContext('2d'); x.fillStyle = k === 'degrade' ? '#2a2f3d' : edC2(); x.fillRect(0, 0, 48, 48); edMotif(x, k, { x: 0, y: 0, w: 48, h: 48 }, { l: 6, e: 6, r: 4, a: 45 }); }
function edCarte() {
  const o = A.outil, carte = $('at-carte-outil'); if (!carte) return;
  const def = OUTILS.find(x => x[0] === o); carte.style.display = ED_OUTILS.includes(o) ? '' : 'none'; if (!ED_OUTILS.includes(o)) return;
  $('at-carte-titre').textContent = def[2]; const c = $('at-carte-contenu'); c.innerHTML = ''; const aj = e => c.appendChild(e);
  const W = A.doc ? A.doc.W : 1024, aide = t => Object.assign(document.createElement('p'), { className: 'aide', textContent: t });
  if (o === 'ligne') { aj(edCurseur('Épaisseur', 'trait', 1, Math.round(W / 4), ' px')); }
  else if (o === 'formes') { aj(edGalerie(ED_NOMS_FORMES, 'forme', edVignetteForme)); aj(edPuces('remplissage', [['plein', 'Plein'], ['contour', 'Contour'], ['deux', 'Plein + contour (couleur 2)']]));
    aj(edCurseur('Contour', 'contour', 1, Math.round(W / 8), ' px')); }
  else if (o === 'motifs') { aj(edGalerie(ED_MOTIFS, 'motif', edVignetteMotif)); aj(aide('Couleur 1 = le motif ; couleur 2 = fin du dégradé. Clic sur la texture : posé sur la partie / la sélection.'));
    aj(edCurseur('Largeur', 'largeur', 1, Math.round(W / 3), ' px')); aj(edCurseur('Espacement', 'espacement', 1, Math.round(W / 3), ' px'));
    aj(edCurseur('Angle', 'angle', -90, 90, '°')); aj(edCurseur('Taille (pois…)', 'rayon', 1, Math.round(W / 6), ' px'));
    const b = document.createElement('button'); b.className = 'primaire'; b.textContent = 'Poser le motif'; b.onclick = () => { const d = A.doc; if (d) edPoser('Motif · ' + ED_MOTIFS[ED.motif], x => edMotif(x, ED.motif, edBoiteCible(d))); }; aj(b); }
  else if (o === 'texte') {
    const t = document.createElement('label'); t.className = 'ed-ligne'; t.innerHTML = '<span>Texte</span><input type="text">'; const i = t.querySelector('input'); i.value = ED.texte;
    i.oninput = () => { ED.texte = i.value; edMemo(); }; aj(t);
    const p = document.createElement('label'); p.className = 'ed-ligne'; p.innerHTML = '<span>Police</span><select></select>'; const s = p.querySelector('select');
    for (const f of ['Arial Black', 'Impact', 'Bahnschrift', 'Segoe UI Black', 'Georgia', 'Trebuchet MS', 'Verdana', 'Courier New', 'Comic Sans MS', 'Times New Roman']) s.add(new Option(f, f, false, f === ED.police));
    if (window.brancherPolices) brancherPolices(s, q => q.nom);                    // (22/11) polices importées
    s.onchange = () => { ED.police = s.value; edMemo(); }; aj(p);
    aj(edCurseur('Taille', 'tTaille', 4, W, ' px')); aj(edCurseur('Contour', 'tContour', 0, Math.round(W / 20), ' px')); aj(edCurseur('Rotation', 'rotation', -180, 180, '°'));
    aj(aide('Couleur 1 = lettres, couleur 2 = contour.')); }
  else if (o === 'image') {
    const f = document.createElement('input'); f.type = 'file'; f.accept = 'image/*'; f.style.display = 'none';
    const b = document.createElement('button'); b.textContent = ED.logo ? 'Changer d’image…' : 'Choisir une image…'; b.onclick = () => f.click();
    f.onchange = () => { const fi = f.files[0]; if (!fi) return; const im = new Image(); im.onload = () => { ED.logo = im; edCarte(); majRapport('Image prête : clique sur la texture pour la poser.'); }; im.src = URL.createObjectURL(fi); };
    aj(b); aj(f);
    if (ED.logo) { const cv = document.createElement('canvas'); cv.width = cv.height = 96; cv.className = 'ed-logo'; const x = cv.getContext('2d'), L = ED.logo, k = Math.min(88 / L.width, 88 / L.height);
      x.drawImage(L, 48 - L.width * k / 2, 48 - L.height * k / 2, L.width * k, L.height * k); aj(cv); }
    aj(edCurseur('Taille', 'imgTaille', 4, W * 2, ' px')); aj(edCurseur('Rotation', 'rotation', -180, 180, '°')); aj(aide('PNG avec fond transparent de préférence.')); }
  aj(edCurseur('Opacité', 'opacite', 5, 100, ' %'));
}
function edOutilChange(o) {
  edCarte(); ED.glisse = null;
  if ($('at-opt-gomme')) $('at-opt-gomme').style.display = o === 'gomme' ? '' : 'none';
  if ($('zn-plat') && o === 'main') $('zn-plat').style.cursor = 'grab';
}
function edPalette() {
  const p = $('at-palette'); if (!p) return; p.innerHTML = '';
  for (const c of PALETTE_ED) { const s = document.createElement('button'); s.style.background = c; s.title = c + ' (clic droit : couleur 2)';
    s.onclick = () => { $('at-c1').value = c; atMajCouleurs(); edCarte(); }; s.oncontextmenu = ev => { ev.preventDefault(); $('at-c2').value = c; atMajCouleurs(); edCarte(); }; p.appendChild(s); }
}
// « Texture du jeu » : le fond redevient la texture d'origine (les calques restent ; Annuler possible)
function edTextureDuJeu() {
  const d = A.doc; if (!d || !d.x.orig) return; if (!confirm('Remettre la texture du jeu sous les calques ? (Ctrl+Z pour revenir)')) return;
  const av = atAvantStructure(d); d.fond = new Uint8ClampedArray(d.x.orig.data); atApresStructure(d, 'Texture du jeu', av);
}
addEventListener('DOMContentLoaded', () => {
  edPalette();
  document.querySelectorAll('[data-ed-fond]').forEach(b => { b.classList.toggle('actif', b.dataset.edFond === ED.fond);
    b.onclick = () => { ED.fond = b.dataset.edFond; edMemo(); document.querySelectorAll('[data-ed-fond]').forEach(x => x.classList.toggle('actif', x === b)); atPlat(); }; });
  if ($('at-jeu')) $('at-jeu').onclick = edTextureDuJeu;
  if ($('at-c1')) { $('at-c1').addEventListener('input', edCarte); $('at-c2').addEventListener('input', edCarte); }
});
