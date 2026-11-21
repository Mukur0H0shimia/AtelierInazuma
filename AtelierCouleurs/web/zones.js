// (15/11/2026) ATELIER DES ESPRITS GUERRIERS ET TOTEMS : un modèle 3D, une seule texture où toutes les pièces sont tassées.
// Outils : pièces de la texture trouvées toutes seules (« zones » = îles du patron UV), choix d'une pièce par clic sur la 3D
// ou sur la texture à plat, surbrillance croisée 3D <-> texture, recoloration de la pièce qui garde l'ombrage peint (et,
// au choix, les reflets du métal : carte « spm »), peinture directement sur le modèle.
// Données : app.js garde la géométrie de chaque pièce (piece.geo = {pos, uv, idx}) ; vue3d.js fournit la caméra (_mvp) et
// laisse les gestes de souris à l'outil (clicOutil / outil).
// Règles du jeu utilisées (LU) : couleur du modèle = texture x éclairage ; reflets du métal = carte spm (couleur) x carte sp
// (reflet selon la normale), shaders chr_toon*_metal (t5 = spm, t4 = sp). Le reste (découpage, recoloration) est un outil
// d'édition, pas une règle du jeu.
"use strict";
const Z = { tex: {}, zones: [], sel: new Set(), survol: -1, outil: 'choisir', pret: false, enCours: false, vue: null };

// ------------------------------------------------------------------ préparation : îles du patron UV -> carte des zones
function zonesTexCle(o, p) { const x = texPrincipale(o, p); return x ? o.nom + '/' + x.nom : null; }
function zonesPreparer() {
  Z.tex = {}; Z.zones = []; Z.sel.clear(); Z.survol = -1; Z.pret = false;
  if (!E.tech || !E.tech.perso) { zonesDessiner(); if (window.atelierApresOuverture) atelierApresOuverture(); return; }
  for (const o of E.objets) { if (o.erreur) continue;
    for (const p of o.pieces || []) { if (!p.geo || !p.vue) continue;
      const cle = zonesTexCle(o, p), x = cle && E.textures[cle]; if (!x || !x.cur) continue;
      let T = Z.tex[cle];
      if (!T) { const W = x.cur.width, H = x.cur.height;
        T = Z.tex[cle] = { cle, x, W, H, label: new Int32Array(W * H).fill(-1), pieces: [] }; }
      zonesIles(T, o, p); } }
  for (const T of Object.values(Z.tex)) zonesFinir(T);
  Z.pret = true; zonesDessiner(); zonesAfficher3D();
  // (15/11/2026) un seul endroit pour peindre : l'atelier ouvert, les blocs de technique repliés
  if (window.atelierApresOuverture) atelierApresOuverture();
}
function zonesIles(T, o, p) {
  const { pos, uv, idx } = p.geo, nt = Math.floor(idx.length / 3), W = T.W, H = T.H;
  // sommets de même UV = même point du patron (les arêtes vives dédoublent les sommets) ; triangles reliés = une île
  const cle = new Map(), rac = new Int32Array(uv.length / 2);
  for (let v = 0; v < rac.length; v++) { const k = Math.round(uv[2 * v] * 4096) + ':' + Math.round(uv[2 * v + 1] * 4096);
    let r = cle.get(k); if (r === undefined) { r = v; cle.set(k, v); } rac[v] = r; }
  const par = new Int32Array(rac.length); for (let i = 0; i < par.length; i++) par[i] = i;
  const tr = i => { while (par[i] !== i) { par[i] = par[par[i]]; i = par[i]; } return i; };
  for (let t = 0; t < nt; t++) { const a = tr(rac[idx[3 * t]]), b = tr(rac[idx[3 * t + 1]]), c = tr(rac[idx[3 * t + 2]]); par[b] = a; par[tr(c)] = tr(a); }
  const ileDe = new Map(), triIle = new Int32Array(nt);
  for (let t = 0; t < nt; t++) { const r = tr(rac[idx[3 * t]]); let z = ileDe.get(r);
    if (z === undefined) { z = Z.zones.length; ileDe.set(r, z); Z.zones.push({ id: z, cle: T.cle, piece: p, n: 0, px: null }); }
    triIle[t] = z; }
  p.zonesTri = triIle; p.zonesTex = T.cle;
  // dessin des triangles dans la carte des zones (pixels de la texture)
  const L = T.label;
  for (let t = 0; t < nt; t++) {
    const i0 = idx[3 * t], i1 = idx[3 * t + 1], i2 = idx[3 * t + 2];
    let u0 = uv[2 * i0], v0 = uv[2 * i0 + 1], u1 = uv[2 * i1], v1 = uv[2 * i1 + 1], u2 = uv[2 * i2], v2 = uv[2 * i2 + 1];
    const du = Math.floor((u0 + u1 + u2) / 3), dv = Math.floor((v0 + v1 + v2) / 3);   // patron répété : ramené dans 0..1
    const x0 = (u0 - du) * W, y0 = (v0 - dv) * H, x1 = (u1 - du) * W, y1 = (v1 - dv) * H, x2 = (u2 - du) * W, y2 = (v2 - dv) * H;
    const ar = (x1 - x0) * (y2 - y0) - (x2 - x0) * (y1 - y0); if (Math.abs(ar) < 1e-9) continue;
    const xa = Math.max(0, Math.floor(Math.min(x0, x1, x2))), xb = Math.min(W - 1, Math.ceil(Math.max(x0, x1, x2)));
    const ya = Math.max(0, Math.floor(Math.min(y0, y1, y2))), yb = Math.min(H - 1, Math.ceil(Math.max(y0, y1, y2)));
    const z = triIle[t], e = -0.02 * Math.abs(ar);
    for (let y = ya; y <= yb; y++) for (let x = xa; x <= xb; x++) { const px = x + 0.5, py = y + 0.5;
      const w0 = ((x1 - px) * (y2 - py) - (x2 - px) * (y1 - py)) * Math.sign(ar), w1 = ((x2 - px) * (y0 - py) - (x0 - px) * (y2 - py)) * Math.sign(ar),
        w2 = ((x0 - px) * (y1 - py) - (x1 - px) * (y0 - py)) * Math.sign(ar);
      if (w0 >= e && w1 >= e && w2 >= e) L[y * W + x] = z; } }
}
function zonesFinir(T) {
  const W = T.W, H = T.H, L = T.label;
  // bords : 3 pixels autour de chaque pièce (la texture déborde du patron pour éviter les coutures)
  for (let k = 0; k < 3; k++) { const c = L.slice();
    for (let y = 0; y < H; y++) for (let x = 0; x < W; x++) { const i = y * W + x; if (c[i] >= 0) continue;
      const v = (x > 0 && c[i - 1] >= 0) ? c[i - 1] : (x < W - 1 && c[i + 1] >= 0) ? c[i + 1] : (y > 0 && c[i - W] >= 0) ? c[i - W] : (y < H - 1 && c[i + W] >= 0) ? c[i + W] : -1;
      if (v >= 0) L[i] = v; } }
  const n = new Int32Array(Z.zones.length); for (let i = 0; i < L.length; i++) if (L[i] >= 0) n[L[i]]++;
  const px = Z.zones.map((z, k) => z.cle === T.cle ? new Int32Array(n[k]) : null), f = new Int32Array(Z.zones.length);
  for (let i = 0; i < L.length; i++) { const z = L[i]; if (z >= 0 && px[z]) px[z][f[z]++] = i; }
  const a = T.x.cur.getContext('2d').getImageData(0, 0, W, H).data;
  for (const z of Z.zones) { if (z.cle !== T.cle) continue; z.px = px[z.id]; z.n = z.px.length; zonesCouleur(z, a);
    // (15/11/2026) couleur de la pièce dans la TEXTURE DU JEU : référence de « Garder l'ombrage » (l'ombrage vient du jeu)
    if (T.x.orig && T.x.orig.data.length === W * H * 4) { const o = { px: z.px, n: z.n }; zonesCouleur(o, T.x.orig.data); z.o = { h: o.h, s: o.s, v: o.v }; } }
}
function zonesCouleur(z, a) {
  let r = 0, g = 0, b = 0, m = 0; const pas = Math.max(1, Math.floor(z.n / 4000));
  for (let k = 0; k < z.n; k += pas) { const i = z.px[k] * 4; if (a[i + 3] < 10) continue; r += a[i]; g += a[i + 1]; b += a[i + 2]; m++; }
  z.rgb = m ? [r / m / 255, g / m / 255, b / m / 255] : [0.5, 0.5, 0.5];
  const [h, s, v] = rgb2hsv(...z.rgb); z.h = h; z.s = s; z.v = v;
}

// ------------------------------------------------------------------ 3D : ce qui est sous la souris
function zonesSousSouris(ev) {
  const V = E.vue; if (!V || !V._mvp || !Number.isFinite(V._mvp[0])) return null;
  const r = V.cv.getBoundingClientRect(), mx = ev.clientX - r.left, my = ev.clientY - r.top, w = r.width, h = r.height, m = V._mvp;
  let best = null;
  for (const o of E.objets) for (const p of o.pieces || []) { if (!p.geo || !p.vue || !p.vue.visible || !p.zonesTri) continue;
    const { pos, uv, idx } = p.geo, nv = pos.length / 3;
    if (!p._ecran || p._ecran.length !== nv * 3) p._ecran = new Float32Array(nv * 3);
    const S = p._ecran;
    for (let v = 0; v < nv; v++) { const x = pos[3 * v], y = pos[3 * v + 1], z = pos[3 * v + 2];
      const cw = m[3] * x + m[7] * y + m[11] * z + m[15];
      if (cw <= 1e-6) { S[3 * v + 2] = 9; continue; }
      S[3 * v] = ((m[0] * x + m[4] * y + m[8] * z + m[12]) / cw * 0.5 + 0.5) * w;
      S[3 * v + 1] = (0.5 - (m[1] * x + m[5] * y + m[9] * z + m[13]) / cw * 0.5) * h;
      S[3 * v + 2] = (m[2] * x + m[6] * y + m[10] * z + m[14]) / cw; }
    for (let t = 0; t < idx.length / 3; t++) { const a = idx[3 * t], b = idx[3 * t + 1], c = idx[3 * t + 2];
      const ax = S[3 * a], ay = S[3 * a + 1], bx = S[3 * b], by = S[3 * b + 1], cx = S[3 * c], cy = S[3 * c + 1];
      if (S[3 * a + 2] > 1 || S[3 * b + 2] > 1 || S[3 * c + 2] > 1) continue;
      if (mx < Math.min(ax, bx, cx) || mx > Math.max(ax, bx, cx) || my < Math.min(ay, by, cy) || my > Math.max(ay, by, cy)) continue;
      const d = (by - cy) * (ax - cx) + (cx - bx) * (ay - cy); if (Math.abs(d) < 1e-9) continue;
      const l0 = ((by - cy) * (mx - cx) + (cx - bx) * (my - cy)) / d, l1 = ((cy - ay) * (mx - cx) + (ax - cx) * (my - cy)) / d, l2 = 1 - l0 - l1;
      if (!(l0 >= 0 && l1 >= 0 && l2 >= 0)) continue;          // (NaN compris : vue pas encore dessinée)
      const zz = l0 * S[3 * a + 2] + l1 * S[3 * b + 2] + l2 * S[3 * c + 2];
      if (!best || zz < best.z) best = { z: zz, piece: p, t, l: [l0, l1, l2], u: l0 * uv[2 * a] + l1 * uv[2 * b] + l2 * uv[2 * c], v: l0 * uv[2 * a + 1] + l1 * uv[2 * b + 1] + l2 * uv[2 * c + 1] }; } }
  if (!best) return null;
  best.zone = best.piece.zonesTri[best.t]; best.cle = best.piece.zonesTex; return best;
}

// ------------------------------------------------------------------ surbrillance (3D et texture à plat)
let zonesAttente = false;
function zonesAfficher3D() {
  if (zonesAttente) return; zonesAttente = true;
  requestAnimationFrame(() => { zonesAttente = false;
    // (15/11/2026) plus de pulsation : la partie choisie est teintée un court instant (flash), puis on voit ses vraies couleurs
    // (sinon on ne voyait pas ce qu'on peignait). Le survol reste marqué (en bleu clair, sans clignoter).
    const sig = [...Z.sel].sort().join(',') + '|' + (window.A && A.sel ? A.sel.cle + ':' + (A.sel.pieces || A.sel.m.length) : '');
    const maintenant = performance.now();
    if (window.A && A.sel && zonesAfficher3D.m !== A.sel.m) { zonesAfficher3D.m = A.sel.m; Z.flashFin = maintenant + 650; }
    if (sig !== Z.sigSel) { Z.sigSel = sig; if (Z.sel.size || (window.A && A.sel)) Z.flashFin = maintenant + 650; }
    const flash = maintenant < (Z.flashFin || 0);
    for (const T of Object.values(Z.tex)) {
      const masque = window.A && A.sel && A.sel.cle === T.cle && !A.sel.pieces ? A.sel.m : null;
      const base = texAffichee(T.x), marquer = (flash && (!!masque || Z.zones.some(z => z.cle === T.cle && Z.sel.has(z.id)))) || Z.zones.some(z => z.cle === T.cle && z.id === Z.survol);
      const cles = [T.cle].concat(E.vue.textures['peau:' + T.cle] ? ['peau:' + T.cle] : []);
      if (!marquer) { for (const c of cles) E.vue.texture(c, base); continue; }
      if (!T.cv) { T.cv = document.createElement('canvas'); T.cv.width = T.W; T.cv.height = T.H; }
      const cx = T.cv.getContext('2d'); cx.clearRect(0, 0, T.W, T.H); cx.drawImage(base, 0, 0);
      const im = cx.getImageData(0, 0, T.W, T.H), a = im.data, k = 0.4;
      for (const z of Z.zones) { if (z.cle !== T.cle) continue; const sel = Z.sel.has(z.id) && flash, sv = z.id === Z.survol; if (!sel && !sv) continue;
        const c = sel ? [255, 205, 60] : [70, 200, 255], kk = sel && sv ? k + 0.15 : k;
        for (let q = 0; q < z.n; q++) { const i = z.px[q] * 4; a[i] = a[i] * (1 - kk) + c[0] * kk; a[i + 1] = a[i + 1] * (1 - kk) + c[1] * kk; a[i + 2] = a[i + 2] * (1 - kk) + c[2] * kk; } }
      if (masque && flash) for (let p = 0; p < masque.length; p++) { const w = masque[p] / 255 * k; if (!w) continue; const i = p * 4; a[i] = a[i] * (1 - w) + 70 * w; a[i + 1] = a[i + 1] * (1 - w) + 200 * w; a[i + 2] = a[i + 2] * (1 - w) + 255 * w; }
      cx.putImageData(im, 0, 0); for (const c of cles) E.vue.texture(c, T.cv); }
    zonesPlat();
    if (flash) setTimeout(zonesAfficher3D, Z.flashFin - maintenant + 20);     // fin du flash : vraies couleurs
  });
}
// ------------------------------------------------------------------ choix
function zonesChoisir(z, ajout) {
  if (z === undefined || z === null || z < 0) { if (!ajout) Z.sel.clear(); }
  else if (ajout) { if (Z.sel.has(z)) Z.sel.delete(z); else Z.sel.add(z); }
  else { Z.sel.clear(); Z.sel.add(z); }
  if (window.atSelPieces) atSelPieces();          // pièces choisies = sélection de l'atelier
  zonesDessiner(); zonesAfficher3D();
}
function zonesPareilles() {      // toute la couleur pareille sur le modèle : même teinte (±18°), ou gris de même clarté
  const ref = [...Z.sel].map(i => Z.zones[i]); if (!ref.length) return;
  for (const z of Z.zones) { if (!z.n) continue;
    if (ref.some(r => (r.s < 0.15 && z.s < 0.15 && Math.abs(r.v - z.v) < 0.12) || (r.s >= 0.15 && z.s >= 0.15 && distTeinte(r.h, z.h) < 18 && Math.abs(r.v - z.v) < 0.3))) Z.sel.add(z.id); }
  if (window.atSelPieces) atSelPieces();
  zonesDessiner(); zonesAfficher3D();
}


// ------------------------------------------------------------------ couleur (ombrage peint gardé)
// (15/11/2026, refait) la pièce PREND la couleur choisie, ombrage peint gardé en relatif :
//  - clarté : v x (clarté choisie / clarté moyenne de la pièce), bornée x0,3..x3 ; x réglage « Luminosité » ;
//  - teinte : celle choisie ; petit écart d'origine gardé (±40°) seulement si le pixel ET la pièce sont vraiment colorés ;
//  - saturation : celle choisie, à l'échelle de la pièce pour les pixels colorés ; les éclats les plus clairs pâlissent un peu.
function zonesCouleurTeinte(r, g, b, H1, S1, V1, z, lum) {
  const [h, s, v] = rgb2hsv(r, g, b), vRef = Math.max(0.04, z.v || 0.5), sRef = z.s || 0;
  // (15/11/2026) plus de plancher à 0,3 : avec lui, le noir ne descendait qu'à 30 % de la clarté par passage (il fallait 3-4 passages)
  const vn = Math.min(1, v * Math.min(3, V1 / vRef) * lum);
  let dh = 0; if (s >= 0.25 && sRef >= 0.25) { dh = ((h - z.h) % 360 + 540) % 360 - 180; dh = Math.max(-40, Math.min(40, dh)); }
  let sn = sRef >= 0.25 && s >= 0.12 ? Math.min(1, s * S1 / sRef) : S1;
  if (vn > 0.85) sn *= 1 - 0.6 * (vn - 0.85) / 0.15;
  return hsv2rgb(H1 + dh, sn, vn);
}
// ombre : pixels d'où vient l'ombrage (la texture du jeu) ; sinon le pixel actuel
function zonesTeindre(a, i, H1, S1, V1, z, lum, w, src, ombre) {
  const b = src || a, o = ombre || b, c = zonesCouleurTeinte(o[i] / 255, o[i + 1] / 255, o[i + 2] / 255, H1, S1, V1, z, lum);
  for (let j = 0; j < 3; j++) a[i + j] = b[i + j] * (1 - w) + c[j] * 255 * w;
}
function zonesCarte(cle, suffixe) { const x = E.textures[cle + suffixe]; return x && x.cur ? x : null; }
function zonesValeurCarte(c, p, T) {
  if (!c._donnees || c._donneesV !== c.moyenne) { c._donnees = c.cur.getContext('2d').getImageData(0, 0, c.cur.width, c.cur.height).data; c._donneesV = c.moyenne; }
  const W = c.cur.width, H = c.cur.height, x = Math.floor((p % T.W) * W / T.W), y = Math.floor(Math.floor(p / T.W) * H / T.H), i = (y * W + x) * 4;
  return Math.max(c._donnees[i], c._donnees[i + 1], c._donnees[i + 2]) / 255;
}

// (15/11/2026) la peinture, les outils et le panneau sont dans atelier.js (moteur de retouche : calques, historique, sélection)
