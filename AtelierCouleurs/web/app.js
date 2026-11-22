// Atelier Inazuma : recolorer une technique (copie -> mod MesTechniques), un esprit guerrier ou un totem
// (couleurs remplacées -> mod MesEsprits) ; onglet Maillots = ouvre l'Atelier Maillots.
"use strict";
const $ = id => document.getElementById(id);
const E = { onglet: 'techniques', index: [], persos: [], tech: null, objets: [], textures: {}, selPieces: new Set(), selTex: new Set(), vue: null };
const ONGLETS = {
  hub: { cherche: '', pieces: '', tout: '', note: '' },
  techniques: { cherche: 'Chercher une technique (nom ou code : Frappe stellaire, whs01430…)', pieces: "Pièces de l'effet", tout: "Tout l'effet",
    note: "Animation du jeu : effet, ballon et caméra (les joueurs et l'esprit ne sont pas encore affichés)." },
  esprits: { cherche: 'Chercher un esprit guerrier (Pégase, Reine blanche, k000010…)', pieces: 'Parties du modèle', tout: 'Tout le modèle',
    note: "Aperçu fixe du modèle (pose de repos), couleurs des textures seulement (sans ombrage du jeu)." },
  totems: { cherche: 'Chercher un totem (loup, lion, a000020…)', pieces: 'Parties du modèle', tout: 'Tout le modèle',
    note: "Aperçu fixe du modèle (pose de repos), couleurs des textures seulement (sans ombrage du jeu)." },
  // (15/11/2026) tout le jeu (moteur/jeu.py) : ouvert comme un esprit
  maillots: { cherche: 'Chercher un maillot du jeu (Zeus, Raimon, u080101…) : il sert de coupe', pieces: 'Parties du maillot', tout: 'Tout le maillot',
    note: 'Maillot du jeu (domicile). Dessine le haut (« _20 ») et le short + chaussettes (« _30 »).' },
  tenues: { cherche: 'Chercher une tenue (code : e000401, s000101…)', pieces: 'Parties de la tenue', tout: 'Toute la tenue', note: 'Aperçu fixe du modèle.' },
  armures: { cherche: 'Chercher une armure (ka000101…)', pieces: "Parties de l'armure", tout: "Toute l'armure", note: 'Aperçu fixe du modèle.' },
  personnages: { cherche: 'Chercher un personnage (Mark Evans, Axel Blaze, c01000010…)', pieces: 'Parties de la tête', tout: 'Toute la tête', note: 'Tête du personnage (le corps vient de sa tenue).' },
  objets: { cherche: 'Chercher un objet du jeu (Crampons, Pendentif, Boisson…)', pieces: 'Icône', tout: 'Icône', note: 'Objet du jeu : son icône (à recolorer en mode dessin).' },
  bannieres: { cherche: '', pieces: '', tout: '', note: '' },
};
// (21/11) éléments des techniques : le catalogue les donne en anglais (wind, fire…) -> noms du jeu en français
const EL_FR = { wind: 'Air', fire: 'Feu', forest: 'Forêt', mountain: 'Montagne', void: 'Néant' };
const libElement = e => (window.ATELIER_LANGUE === 'en' ? (e ? e.charAt(0).toUpperCase() + e.slice(1) : e) : EL_FR[e] || e);
const ONGLETS_JEU = ['maillots', 'tenues', 'armures', 'personnages', 'objets'];     // (15/11/2026) tout le jeu (moteur/jeu.py)
const estPerso = () => E.onglet === 'esprits' || E.onglet === 'totems' || ONGLETS_JEU.includes(E.onglet);
// E.textures[cle] = {obj, nom, info, orig: ImageData, cur: canvas, modif: bool, moyenne: [r,g,b]}

// ------------------------------------------------------------------ couleurs (HSV)
function rgb2hsv(r, g, b) { const mx = Math.max(r, g, b), mn = Math.min(r, g, b), d = mx - mn; let h = 0;
  if (d) { if (mx === r) h = ((g - b) / d) % 6; else if (mx === g) h = (b - r) / d + 2; else h = (r - g) / d + 4; h *= 60; if (h < 0) h += 360; }
  return [h, mx ? d / mx : 0, mx]; }
function hsv2rgb(h, s, v) { h = ((h % 360) + 360) % 360 / 60; const i = Math.floor(h), f = h - i, p = v * (1 - s), q = v * (1 - s * f), t = v * (1 - s * (1 - f));
  return [[v, t, p], [q, v, p], [p, v, t], [p, q, v], [t, p, v], [v, p, q]][i % 6]; }
function hex2rgb(x) { x = x.replace('#', ''); return [0, 2, 4].map(i => parseInt(x.substr(i, 2), 16) / 255); }

function poidsZone(h, s, v, z) {
  // z : {h, s, v, tol (0-1)} ; 1 = couleur visée, 0 = trop loin (dégradé doux entre les deux)
  let d;
  if (z.s > 0.18) { const dh = Math.min(Math.abs(h - z.h), 360 - Math.abs(h - z.h)) / 180; d = dh + (s < 0.12 ? 1 : 0) + Math.abs(v - z.v) * 0.3; }
  else d = Math.abs(v - z.v) + s;                   // couleur visée grise / blanche / noire : luminosité
  return Math.max(0, Math.min(1, 1.5 - d / z.tol * 1.5));
}
function recolorer(src, dst, r) {
  // r : {mode, c1:[r,g,b], c2, sat, lum, garderOr, garderBlanc, zone: {h, s, v, tol} | null}
  const a = src.data, o = dst.data, [h1, s1] = rgb2hsv(...r.c1), [h2, s2] = rgb2hsv(...r.c2);
  for (let i = 0; i < a.length; i += 4) {
    const R = a[i] / 255, G = a[i + 1] / 255, B = a[i + 2] / 255; let [h, s, v] = rgb2hsv(R, G, B);
    o[i + 3] = a[i + 3];
    const wz = r.zone ? poidsZone(h, s, v, r.zone) : 1;
    if (wz <= 0) { o[i] = a[i]; o[i + 1] = a[i + 1]; o[i + 2] = a[i + 2]; continue; }
    let garder = false;
    if (r.garderBlanc && s < 0.08 && v > 0.88) garder = true;
    if (r.garderOr && s > 0.15 && (h < 70)) garder = true;
    if (garder) { o[i] = a[i]; o[i + 1] = a[i + 1]; o[i + 2] = a[i + 2]; continue; }
    let out;
    if (r.mode === 'teinte') {
      if (s < 0.02) { out = [R, G, B]; }
      else out = hsv2rgb(h1, Math.min(1, s * r.sat), Math.min(1, v * r.lum));
    } else if (r.mode === 'coloriser') {
      out = hsv2rgb(h1, Math.min(1, s1 * r.sat * (r.garderBlanc ? Math.min(1, 1.15 - v * 0.6) : 1)), Math.min(1, v * r.lum));
    } else {   // dégradé : la luminosité choisit entre couleur 1 (sombre) et couleur 2 (clair)
      const l = v, c = [0, 1, 2].map(k => r.c1[k] * (1 - l) + r.c2[k] * l);
      const [hh, ss] = rgb2hsv(...c); out = hsv2rgb(hh, Math.min(1, ss * r.sat), Math.min(1, v * r.lum));
    }
    o[i] = a[i] * (1 - wz) + out[0] * 255 * wz; o[i + 1] = a[i + 1] * (1 - wz) + out[1] * 255 * wz; o[i + 2] = a[i + 2] * (1 - wz) + out[2] * 255 * wz;
  }
}
function moyenne(img) { let n = 0, s = [0, 0, 0]; const a = img.data; const pas = Math.max(4, Math.floor(a.length / 4 / 3000) * 4);
  for (let i = 0; i < a.length; i += pas) { if (a[i + 3] < 20) continue; const m = Math.max(a[i], a[i + 1], a[i + 2]); if (m < 20) continue;
    n++; s[0] += a[i]; s[1] += a[i + 1]; s[2] += a[i + 2]; }
  return n ? s.map(x => x / n / 255) : [0.8, 0.8, 0.8]; }

// ------------------------------------------------------------------ chargement
async function api(url, corps) {
  const r = await fetch(url, corps ? { method: 'POST', body: JSON.stringify(corps), headers: { 'Content-Type': 'application/json' } } : {});
  if (!r.ok && r.headers.get('content-type')?.includes('json')) { const e = await r.json(); throw new Error(e.erreur || r.status); }
  return r.headers.get('content-type')?.includes('json') ? r.json() : r.arrayBuffer();
}
function chargerImage(url) { return new Promise((ok, ko) => { const i = new Image(); i.onload = () => ok(i); i.onerror = ko; i.src = url; }); }

// carte d'ombre de la cascade 0 (ombre des effets, t15 du jeu) envoyée au rendu Direct3D : profondeur rangée en RVB + matrice
function carteOmbreD3D(V) {
  const O = V._ombreEffets; if (!O || !O.tex) return null;
  const gl = V.gl, T = O.taille, fb = gl.createFramebuffer(), px = new Uint8Array(T * T * 4);
  gl.bindFramebuffer(gl.FRAMEBUFFER, fb); gl.framebufferTexture2D(gl.FRAMEBUFFER, gl.COLOR_ATTACHMENT0, gl.TEXTURE_2D, O.tex, 0);
  const ok = gl.checkFramebufferStatus(gl.FRAMEBUFFER) === gl.FRAMEBUFFER_COMPLETE; if (ok) gl.readPixels(0, 0, T, T, gl.RGBA, gl.UNSIGNED_BYTE, px);
  gl.bindFramebuffer(gl.FRAMEBUFFER, null); gl.deleteFramebuffer(fb); if (!ok) return null;
  let b = ''; for (let i = 0; i < px.length; i += 0x8000) b += String.fromCharCode.apply(null, px.subarray(i, i + 0x8000));
  return { taille: T, vp: Array.from(O.vp), px: btoa(b) };
}
// ------------------------------------------------------------------ PROTOTYPE Direct3D (13/11/2026)
// À l'arrêt : la page dessine la scène SANS les effets du jeu, note pour chaque pièce d'effet ce qu'elle aurait dessiné
// (matrices, paramètres animés, textures, adressage, mélange), puis le serveur la fait dessiner par Direct3D 11 avec les
// vrais shaders du jeu (dossier AtelierD3D). Limite : les effets passent devant les joueurs (pas de profondeur partagée).
const D3D = { attente: false, cle: null };
const enBase64 = u8 => new Promise(r => { const fr = new FileReader(); fr.onload = () => r(fr.result.split(',')[1]); fr.readAsDataURL(new Blob([u8])); });
// opts (film Direct3D, 14/11/2026) : { film: true, lum } -> rend l'image courante et renvoie { px, w, h, lum, ms } sans
// l'afficher ; lum = luminosité adaptée de l'image d'avant (renvoyée par le serveur), à la place des 60 images WebGL
// couleurs animées d'une pièce (G4MA 16-19, 14/11/2026) : n° 0 = u_diffuse (rvb ; l'alpha reste l'opacité), 1 = u_ambient
function couleurJeu(p, n, c) {
  for (const [k, i, v] of p.jeuCol || []) if (k === n && !(n === 0 && i === 3)) c[i] = v;
  // (14/11/2026) couleur du matériau choisie dans l'Atelier : remplace la couleur fixe ET animée (VRFW [[recolor.tint]] op = "set")
  if (n === 0 && p.couleurMat) for (let i = 0; i < 3; i++) c[i] = p.couleurMat[i];
  return c;
}
async function rendreD3D(opts) {
  const V = E.vue, cv2 = $('vue-d3d');
  if (!opts && FILM.enCours) return;                 // (le film occupe Direct3D)
  if (!opts && filmVisible()) return;                // (image du film affichée par la boucle du film)
  if (!opts && (!V || !$('l-d3d').checked || !V.lecteur || V.joue)) { cv2.style.display = 'none'; D3D.cle = null; $('l-d3d-info').textContent = ''; return; }
  if (opts && (!V || !V.lecteur)) return null;
  if (D3D.attente && !opts) return;
  const f = Math.floor(V.image), w = V.cv.width, h = V.cv.height;
  const versions = Object.values(E.textures).map(x => x.modif ? JSON.stringify(x.moyenne) : 0).join(',');
  const post = $('l-d3d-post') ? $('l-d3d-post').checked : true;
  const cle = [f, w, h, V.yaw, V.pitch, V.dist, V.centre.join(), $('l-camera').checked, $('l-terrain').checked, versions, E.persoChoisi, post, JSON.stringify(E.coulMat || {}), JSON.stringify(E.teinteSom || {}), JSON.stringify(E.teintePtl || {})].join('|');
  if (!opts && cle === D3D.cle) return;
  D3D.attente = true; if (!opts) { D3D.cle = cle; $('l-d3d-info').textContent = '…'; }
  try {
    const objDe = {}; for (const o of E.objets) objDe[o.nom] = o;
    const appels = [], orig = V._dessinerJeu, gl = V.gl;
    V._dessinerJeu = function (p, mvp) {          // noter sans dessiner
      const J = p.jeu, [on, idx] = p.cle.split('/'); let P = (p.jeuP || J.params).map(v => v.slice());
      if (p.ptl) {                                // vraies particules : quadrilatères déjà calculés (repère caméra), dessinés
        // SmokePar1 : quadrilatères dans le repère du monde avec NORMAL / TANGENT du jeu (le shader calcule lumières et ombre au point du monde)
        const B = this._quadsEmetteur(p, J.mode === 28); if (!B || !B.cpu) return;     // par les shaders de leur matériau
        const I = [1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1];
        const Wd = B.cpu.monde;                   // SmokePar1 : sommets du monde (u_mtxLW = identité, u_mtxLP = P x V)
        appels.push({ cle: p.cle, geo: Wd ? Object.assign({}, B.cpu, { pos: B.cpu.posW }) : B.cpu, vs: p.def.shader_vs || J.ps, ps: J.ps,
          mvp: Wd ? B.cpu.mvpW : Array.from(this._P || I), modele: I, V: Wd ? B.cpu.V : I, P: Array.from(this._P || I),
          uv: [0, 1, 2, 3, 4, 5].map(() => [1, 0, 0, 0, 0, 1, 0, 0]), params: P, diffuse: J.diffuse, ambient: J.ambient, melange: p.melange, ztest: p.ztest,
          surEcran: !!p.surEcran, tex: J.tex, adressage: J.adressage, mode: J.mode, particules: false, colonne: J.colonne,
          prio: (p.def && p.def.materiau && p.def.materiau.priorite !== undefined) ? p.def.materiau.priorite : 25,   // couche de dessin (LU)
          depthTest: gl.isEnabled(gl.DEPTH_TEST), depthMask: gl.getParameter(gl.DEPTH_WRITEMASK) });
        return; }
      if (J.colonne !== null && J.colonne !== undefined) { let col = J.colonne; /* = couleur de tir (vérifié sur vidéos du jeu) */ if (P[2]) P[2][3] = (col + 0.5) / 128; }
      appels.push({ cle: p.cle, chemin: objDe[on] && objDe[on].chemin, piece: +idx, mvp: Array.from(mvp), modele: Array.from(p.modele || [1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1]),
        V: Array.from(this._V || []), P: Array.from(this._P || []), uv: p.jeuUV || [0, 1, 2, 3, 4, 5].map(k => J.texproj[k] || [1, 0, 0, 0, 0, 1, 0, 0]),
        params: P, diffuse: couleurJeu(p, 0, [J.diffuse[0], J.diffuse[1], J.diffuse[2], p.opacite !== undefined ? p.opacite : J.diffuse[3]]),
        ambient: couleurJeu(p, 1, J.ambient.slice()),
        melange: p.melange, ztest: p.ztest, surEcran: !!p.surEcran, tex: J.tex, adressage: J.adressage, mode: J.mode, particules: !!J.particules,
        // écriture de profondeur = clé 5 du matériau (LU nie.exe 0x140528eb0), comme AtelierNatif/src/technique.h
        faces: p.faces ? 1 : 0, biais: p.biais || 0, prio: p.prio !== undefined ? p.prio : 30, seuil: p.seuil !== undefined ? p.seuil : 256, colonne: J.colonne, depthTest: gl.isEnabled(gl.DEPTH_TEST), depthMask: !!(p.zecrit && !p.surEcran),
        // maillage à peau : matrices des os de la palette (repère de l'objet) -> u_mtxBone du shader « _vb » du jeu
        os_peau: p.peauK ? p.peauK.map(m => m ? Array.from(m) : [1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1]) : null,
        teinte_sommets: p.teinteSom || null });   // (14/11/2026) teinte des couleurs de sommets (rendu_image.geometrie)
    };
    // stade dessiné par Direct3D avec les vrais shaders du jeu (13/11/2026) : la page envoie la caméra et un fond SANS le stade
    const stadeD3D = !!E.stadeCode, cachees = [];
    if (stadeD3D) for (const p of V.pieces) if (p.cle && p.cle.startsWith('stade/') && p.visible) { p.visible = false; cachees.push(p); }
    // acteurs (esprits, totems…) dessinés par Direct3D avec chr_toon* du jeu : retirés du fond ; le joueur mannequin NOIR reste
    // dessiné par la vue (choix de l'utilisateur). La page n'envoie que les matrices des os, le serveur fait la peau.
    // (lecteur natif : le mannequin noir aussi, il n'y a pas de vue WebGL derrière ; le lecteur le dessine en noir)
    const acteursD3D = {}, estActeurD3D = p => stadeD3D && p.peau && (!p.noir || (opts && opts.natif)) && E.acteursSrc && E.acteursSrc[p.peau.acteur];
    if (stadeD3D) for (const p of V.pieces) if (estActeurD3D(p) && p.visible) { p.visible = false; cachees.push(p); p._d3d = true; }
    let camStade = null;
    try { V._ombresD3D = null; V._dessinerUne(f); const O = V._ombresD3D, PX = V._peauxD3D || {};
      for (const p of cachees) { if (!p._d3d) continue; delete p._d3d; const ac = p.peau.acteur, M = PX[ac]; if (!M || p.animCachee) continue;
        const A = acteursD3D[ac] || (acteursD3D[ac] = Object.assign({ acteur: ac, pieces: [], mats: [] }, E.acteursSrc[ac]));
        A.pieces.push(+p.cle.split('/').pop()); }
      // ombre sous les pieds du jeu (FootShadowAO) : ellipsoïdes CRenderCollision de chaque acteur (LU le 14/11/2026 :
      // render_collision.cfg.bin, profil de l'objbin ; vérifié dans la mémoire du jeu). Matrice = monde de l'os × T(décalage)
      // × échelle (largeur, profondeur, hauteur) ; envoyée en 3 lignes (12 nombres). Sans profil : pas d'ombre (comme le jeu).
      var pieds = [];
      for (const A of (E.lecteur ? E.lecteur.acteurs : [])) { const M = PX[A.d.acteur]; if (!M || !A.d.os || !A.d.collision) continue;
        for (const c of A.d.collision) { const i = A.d.os.findIndex(o => o.nom === c.os); if (i < 0) continue;
          const m = M[i], r = A.sq.mondeRepos[i]; if (!m || !r) continue;
          const W = new Array(16); for (let col = 0; col < 4; col++) for (let row = 0; row < 4; row++) {      // W = m × r (colonnes)
            let s = 0; for (let k = 0; k < 4; k++) s += m[k * 4 + row] * r[col * 4 + k]; W[col * 4 + row] = s; }
          const [dx, dy, dz] = c.decalage, [sx, sy, sz] = c.taille;
          const t = [0, 1, 2].map(row => W[row] * dx + W[4 + row] * dy + W[8 + row] * dz + W[12 + row]);
          for (let row = 0; row < 3; row++) pieds.push(W[row] * sx, W[4 + row] * sy, W[8 + row] * sz, t[row]); } }
      pieds = pieds.length ? Array.from({ length: pieds.length / 12 }, (_, k) => pieds.slice(12 * k, 12 * k + 12)) : [];
      for (const A of Object.values(acteursD3D)) { const M = PX[A.acteur], n = M.length;
        for (let k = 0; k < n; k++) A.mats.push(...(M[k] ? Array.from(M[k]) : [1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1])); }
      camStade = stadeD3D && V._V && V._P ? { code: E.stadeCode, V: Array.from(V._V), P: Array.from(V._P),
        // ombres du soleil (cascades calculées comme le jeu) : dessinées par Direct3D avec shadow_ss du jeu
        ombres: O ? { vp: O.vp.map(m => Array.from(m)), tranches: O.tranches, dir: O.dir, biais: O.biais, taille: O.taille } : null,
        acteurs: Object.values(acteursD3D), pieds, statut: V._statut || null,
        // décor caché par la cinématique (commande 0x3DB3FBEB [0], ex. galaxie de Big Bang) : stade ET ciel non dessinés
        decor: !cachees.some(p => p.cle && p.cle.startsWith('stade/') && p.animCachee),   // aura du ballon = effet de statut du jeu
        // mise au point automatique du jeu (scène +0x8CC) = distance œil -> point visé de la caméra
        foyer: V._camD3D ? Math.hypot(V._camD3D.cible[0] - V._camD3D.oeil[0], V._camD3D.cible[1] - V._camD3D.oeil[1], V._camD3D.cible[2] - V._camD3D.oeil[2]) : null,
        // lumières ponctuelles des effets (CCustomPointLight, calculées par la vue) : cb8 / t17 / t18 des shaders du jeu
        lumieres: (V.lumPL || []).map(l => ({ pos: Array.from(l.pos), att: l.att, col: Array.from(l.col), masque: l.masque })) } : null; }
    finally { V._dessinerJeu = orig; cachees.forEach(p => { p.visible = true; }); }
    // lecteur natif : seulement ce que l'animation a calculé (le lecteur a sa propre profondeur, pas de fond WebGL)
    if (opts && opts.natif) return { appels, stade: camStade, w, h };
    // fond = scène sans les effets, sur le fond de la page
    const c = document.createElement('canvas'); c.width = w; c.height = h; const x = c.getContext('2d');
    let g; if ($('vue').classList.contains('ciel')) { g = x.createLinearGradient(0, 0, 0, h); g.addColorStop(0, '#5d8fd0'); g.addColorStop(0.55, '#a9c9ee'); g.addColorStop(1, '#d9e8f6'); }
    else { g = x.createRadialGradient(w / 2, h / 2, 0, w / 2, h / 2, Math.hypot(w, h) / 2); g.addColorStop(0, '#1a1f2b'); g.addColorStop(1, '#07080b'); }
    x.fillStyle = g; x.fillRect(0, 0, w, h); x.drawImage(V.cv, 0, 0);
    const fond = await enBase64(new Uint8Array(x.getImageData(0, 0, w, h).data.buffer));
    // profondeur du décor et des joueurs (passe spéciale : chaque pixel = sa profondeur sur 3 octets), pour que les effets
    // passent derrière eux comme dans le jeu ; lignes de bas en haut
    const prof = await enBase64(V.pixelsProfondeur(f));
    // stade en Direct3D : profondeur des objets SEULS (ballon…) pour le tampon de profondeur de Direct3D, qui dessine le stade
    let profObjets = null;
    if (camStade) { const cach = []; for (const p of V.pieces) if (((p.cle && p.cle.startsWith('stade/')) || estActeurD3D(p)) && p.visible) { p.visible = false; cach.push(p); }
      try { profObjets = await enBase64(V.pixelsProfondeur(f)); } finally { cach.forEach(p => { p.visible = true; }); } }
    // effets d'écran : luminosité moyenne des 3 secondes d'avant, lissée comme le fait le jeu (cs_buffer_lerp), pour
    // l'adaptation du tone mapping. Mesure COMME LE JEU (cs_tex_reduction, lu dans nie.exe 0x141335cf0) : grille 64 x 64,
    // un pixel par point ((i x L) >> 6, (j x H) >> 6), luminance dot(max(rvb, 0), (0,29891 ; 0,58661 ; 0,11448)),
    // moyenne arithmétique ; u_rate = dt x tonemapFadeSpeed à chaque image (ici 1 image sur 3, taux composé).
    // APPROCHÉ : les images d'avant sont les images WebGL de l'Atelier (8 bits), pas l'image HDR du jeu.
    let lumAvant = null;
    if (opts) lumAvant = opts.lum === undefined ? null : opts.lum;      // film : valeur adaptée par le serveur, image après image
    else if (post && f > 0) { const p = document.createElement('canvas'); p.width = w; p.height = h; const px = p.getContext('2d');
      const vit = ((V.lumStade && V.lumStade.tonemapFadeSpeed) || [1])[0];
      for (let k = Math.max(0, f - 180); k < f; k += 3) { V._dessinerUne(k); px.fillStyle = g; px.fillRect(0, 0, w, h); px.drawImage(V.cv, 0, 0, w, h);
        const d = px.getImageData(0, 0, w, h).data; let s = 0;
        for (let j = 0; j < 64; j++) for (let i = 0; i < 64; i++) { const o = (((j * h) >> 6) * w + ((i * w) >> 6)) * 4;
          s += (0.29891 * d[o] + 0.58661 * d[o + 1] + 0.11448 * d[o + 2]) / 255; }
        const L = s / 4096; lumAvant = lumAvant === null ? L : lumAvant + (1 - Math.pow(1 - vit / 60, 3)) * (L - lumAvant); } }
    V._dessinerUne(f);                              // remettre la vue normale
    // textures recolorées dans l'Atelier
    const modifs = {};
    for (const a of appels) for (const k of a.tex || []) { const t = k && E.textures[k]; if (t && t.modif && t.cur && !modifs[k]) {
      const cc = t.cur.getContext ? t.cur : null; if (!cc) continue; const d = cc.getContext('2d').getImageData(0, 0, cc.width, cc.height);
      modifs[k] = [cc.width, cc.height, await enBase64(new Uint8Array(d.data.buffer))]; } }
    const corps = { etat: { image: f, largeur: w, hauteur: h, appels, stade: camStade }, fond, profondeur: prof, profondeur_objets: profObjets, modifs, effets_ecran: post, lum_avant: lumAvant,
      reglages_ecran: V.lumStade || null, ombre: carteOmbreD3D(V) };
    if (opts && opts.preparer) return { corps, w, h };   // film : envoyé plus tard (préparation de l'image suivante pendant le rendu)
    const r = await api('/api/rendu_d3d', corps);
    if (r.erreur) throw new Error(r.erreur);
    const px = new Uint8ClampedArray(await (await fetch('data:application/octet-stream;base64,' + r.image)).arrayBuffer());
    if (opts) return { px, w, h, lum: r.lum, ms: r.ms };
    if (D3D.cle === cle && $('l-d3d').checked && !V.joue) {
      cv2.width = w; cv2.height = h; cv2.getContext('2d').putImageData(new ImageData(px, w, h), 0, 0); cv2.style.display = 'block';
      $('l-d3d-info').textContent = `${r.ms} ms` + (r.notes && r.notes.length ? ' · ' + r.notes.join(' · ') : '');
    }
  } catch (e) { $('l-d3d-info').textContent = 'erreur : ' + e.message; console.error(e); if (opts) throw e; }
  finally { D3D.attente = false; }
}

// ------------------------------------------------------------------ FILM DIRECT3D (14/11/2026)
// Comme le jeu, chaque image de la cinématique est dessinée avec les vrais shaders, dans l'ordre : la luminosité adaptée
// (tone mapping) passe d'une image à la suivante comme dans le jeu (cs_buffer_lerp). Les images (JPEG) sont gardées puis
// rejouées à la vitesse de la lecture. Seulement avec la caméra du jeu (une caméra libre change l'image).
const FILM = { images: [], enCours: false, stop: false, cle: null, decod: new Map(), attente: new Set() };
function cleFilm() {
  const V = E.vue;
  return V && E.tech ? [E.tech.code, V.cv.width, V.cv.height, $('l-d3d-post').checked, $('l-terrain').checked, E.persoChoisi].join('|') : null;
}
function filmVisible() {
  const V = E.vue;
  return !!(V && $('l-film') && $('l-film').checked && $('l-camera').checked && FILM.cle === cleFilm() && FILM.images[Math.floor(V.image)]);
}
function versJpeg(px, w, h) {
  const c = document.createElement('canvas'); c.width = w; c.height = h; c.getContext('2d').putImageData(new ImageData(px, w, h), 0, 0);
  return new Promise(r => c.toBlob(r, 'image/jpeg', 0.92));
}
async function filmD3D() {
  const V = E.vue; if (!V || !V.lecteur) return;
  if (FILM.enCours) { FILM.stop = true; return; }                 // 2e clic : arrêter
  FILM.enCours = true; FILM.stop = false; FILM.images = []; FILM.decod.forEach(b => b.close()); FILM.decod.clear();
  FILM.cle = cleFilm(); $('l-camera').checked = true; V.joue = false; $('l-film-bouton').textContent = 'Arrêter le film';
  const n = V.lecteur.duree, t0 = performance.now(); let lum = null, f = 0;
  // l'image f+1 est préparée (animation, profondeurs, ombre des effets) PENDANT que le serveur dessine l'image f ;
  // la luminosité adaptée de f n'est connue qu'à la réponse : elle est mise dans la demande de f+1 juste avant l'envoi
  const preparer = async k => { V.image = k; V._dessinerUne(k); return rendreD3D({ film: true, preparer: true }); };
  try {
    let pret = await preparer(0);
    FILM.cle = cleFilm();                            // (après la 1re image : la vue a alors sa vraie taille)
    for (; f < n && !FILM.stop && pret; f++) {
      pret.corps.lum_avant = lum;
      const envoi = api('/api/rendu_d3d', pret.corps);
      const { w, h } = pret;
      pret = f + 1 < n ? await preparer(f + 1) : null;
      const r = await envoi;
      if (r.erreur) throw new Error(r.erreur);
      const px = new Uint8ClampedArray(await (await fetch('data:application/octet-stream;base64,' + r.image)).arrayBuffer());
      lum = r.lum === undefined ? null : r.lum;
      { const k = f, cleF = FILM.cle;                 // (compression en parallèle : ne bloque pas l'image suivante)
        versJpeg(px, w, h).then(b => { if (FILM.cle === cleF) FILM.images[k] = b; }); }
      const s = (performance.now() - t0) / 1000 / (f + 1);
      $('l-film-info').textContent = `${f + 1} / ${n} images · ${s.toFixed(2)} s par image · reste ${Math.round(s * (n - f - 1))} s`;
    }
    $('l-film-info').textContent = (f >= n ? 'Film prêt : ' : 'Film arrêté : ') + `${f} / ${n} images en ${Math.round((performance.now() - t0) / 1000)} s`;
  } catch (e) { $('l-film-info').textContent = 'erreur : ' + e.message; }
  finally { FILM.enCours = false; $('l-film-bouton').textContent = 'Film Direct3D'; }
}
// LECTEUR NATIF — VÉRIFICATION SEULEMENT (14/11/2026) : l'ancienne méthode, l'animation calculée ici pour toutes les images
// et envoyée au serveur (gardée dans AtelierNatif/scenes/tech_<code>/demande_page.json) : elle sert de référence pour vérifier
// l'animation calculée par le lecteur C++ (AtelierNatif/essai_anim.py). Appel : animationPage() dans la console.
async function animationPage() {
  const V = E.vue; if (!V || !V.lecteur) return;
  if (!E.stadeCode) { $('l-film-info').textContent = 'lecteur natif : pas de stade chargé'; return; }
  $('l-camera').checked = true; V.joue = false;
  const n = V.lecteur.duree, imgs = [], regl = [], idx = {}, modifs = {};
  $('l-film-info').textContent = 'Lecteur natif : calcul de l\'animation…';
  // animation calculée en 16:9 (1280 x 720), la forme du jeu et de la fenêtre du lecteur : caméra, effets collés à
  // l'écran (traits de vitesse) et particules tournées vers la caméra arrivent déjà à la bonne forme
  const st0 = [V.cv.style.width, V.cv.style.height];
  V.cv.style.width = '1280px'; V.cv.style.height = '720px';
  try {
  for (let f = 0; f < n; f++) {
    V.image = f;
    // (étape 2) dessins des effets de cette image : pièces (matrices, paramètres animés, opacité, os) et particules
    const r = await rendreD3D({ film: true, natif: true });
    const g = V.lumStade || {}, k = JSON.stringify(g);
    if (!(k in idx)) { idx[k] = regl.length; regl.push(g); }
    const st = r && r.stade;
    imgs.push({ V: Array.from(V._V), P: Array.from(V._P), reglages: idx[k], appels: r ? r.appels : [],
                lumieres: st ? st.lumieres : [], decor: st ? st.decor !== false : true,
                // (étape 3) personnages (matrices des os), cascades d'ombre, ombre des pieds, effet de statut, mise au point
                stade: st ? { ombres: st.ombres, acteurs: st.acteurs, pieds: st.pieds, statut: st.statut, foyer: st.foyer } : null });
    // textures recolorées dans l'Atelier : envoyées une fois
    for (const a of (r ? r.appels : [])) for (const t of a.tex || []) { const x = t && E.textures[t];
      if (x && x.modif && !E.avant && x.cur && x.cur.getContext && !modifs[t]) { const d = x.cur.getContext('2d').getImageData(0, 0, x.cur.width, x.cur.height);
        modifs[t] = [x.cur.width, x.cur.height, await enBase64(new Uint8Array(d.data.buffer))]; } }
    if (f % 10 === 0) { $('l-film-info').textContent = `Lecteur natif : animation ${f} / ${n}…`; await new Promise(r => setTimeout(r, 0)); }
  }
  } finally { V.cv.style.width = st0[0]; V.cv.style.height = st0[1]; V._dessinerUne(Math.floor(V.image)); }
  $('l-film-info').textContent = 'Lecteur natif : export (la 1re fois pour ce stade : ~1 min)…';
  try {
    const r = await api('/api/natif', { stade: E.stadeCode, technique: E.tech && E.tech.code, projet: E.projet, images: imgs, reglages: regl, modifs, largeur: 1280, hauteur: 720, verification: true });
    $('l-film-info').textContent = r.erreur ? 'Lecteur natif : ' + r.erreur : `Lecteur natif lancé (${r.images} images)`;
  } catch (e) { $('l-film-info').textContent = 'Lecteur natif : erreur ' + e.message; }
}

// colonne du dégradé BallAura (u_grdValue) : couleur de tir du joueur qui a TIRÉ (LU nie.exe 0x140f12490) ; gardien -> ballon
// adverse, jamais sa couleur ; vidéos officielles : 0 (jaune, MESURÉ). Même règle que AtelierNatif/exporter.py.
function couleurTirBalle() { const t = E.tech; if (!t) return 0; return /^whk/.test(t.code) ? 0 : (t.couleur_tir || 0); }

// LECTEUR NATIF (14/11/2026) : la lecture se fait dans AtelierNatif/lecteur.exe (C++ / Direct3D 11, vrais shaders du jeu),
// qui calcule lui-même l'animation (caméra, effets, particules, personnages, ombres), comme le jeu : la page envoie seulement
// les textures recolorées et les pièces décochées. La technique est préparée par le serveur dès son ouverture.
// (14/11/2026) le lecteur est INCRUSTÉ dans la vue 3D : sa fenêtre (sans bordure, rattachée à celle de l'Atelier) est posée
// sur la zone entre la barre du haut et la barre de lecture ; la page lui envoie les commandes (lecture / pause, image…).
const NATIF = { actif: false, cle: null, rect: '', minuteur: null };
function rectNatif() {
  const c = $('vue').getBoundingClientRect(), hb = document.querySelector('.barre-vue').getBoundingClientRect(), lb = $('lecteur').getBoundingClientRect();
  const haut = Math.max(c.top, hb.bottom + 2), bas = Math.min(c.bottom, lb.top - 2), d = devicePixelRatio || 1;
  // + taille de la page (le lecteur place la page en bas de la zone cliente de la fenêtre d'Edge)
  return [c.left * d, haut * d, c.width * d, Math.max(0, bas - haut) * d, innerWidth * d, innerHeight * d].map(Math.round);
}
function cmdNatif(cmd, attendre) { return api('/api/natif_cmd', { cmd, attendre: !!attendre }).catch(() => ({ actif: false })); }
function finNatif(envoyer) {
  // (14/11/2026) aussi pendant un lancement : le lecteur en chargement est arrêté par le serveur, et le lancement en cours
  // est annulé (numéro de lancement changé : sa réponse referme le lecteur au lieu de l'afficher)
  if (envoyer && (NATIF.actif || NATIF.lance)) cmdNatif('quitter');
  if (envoyer) { NATIF.numero = (NATIF.numero || 0) + 1; NATIF.lance = false; }
  NATIF.actif = false; NATIF.cle = null; clearInterval(NATIF.minuteur); NATIF.minuteur = null;
  if (E.vue) E.vue.cv.style.visibility = ''; $('l-jouer').textContent = '▶';
}
// (22/11, retour de muku : « les paramètres vont derrière aussi ») ce qui s'ouvre PAR-DESSUS la vue cache le lecteur natif
// (une vraie fenêtre, toujours devant la page) : liste des résultats (17/11), fenêtre ⚙ Paramètres, fenêtres <dialog>
// (Tableau des compétences, technique liée)
function natifRecouvert() {
  const res = $('resultats');
  return (res && res.style.display === 'block') || !!document.querySelector('#parametres.ouvert, dialog[open]');
}
function majCacheNatif() {
  if (!NATIF.actif) { NATIF.cacheListe = false; return; }
  const c = natifRecouvert();
  if (c !== !!NATIF.cacheListe) { NATIF.cacheListe = c; cmdNatif(c ? 'cacher' : 'montrer'); }
}
function suivreNatif() {                        // zone de la vue (la fenêtre la suit) + image en cours (curseur)
  clearInterval(NATIF.minuteur);
  NATIF.minuteur = setInterval(async () => {
    if (!NATIF.actif) return;
    majCacheNatif();
    const r = rectNatif().join(' ');
    if (r !== NATIF.rect) { NATIF.rect = r; cmdNatif('rect ' + r); }
    optionsNatif();                              // (15/11/2026) pièces cachées / couleurs changées : envoyées sans relancer
    const e = await cmdNatif('etat', true);
    if (!e.actif) { finNatif(false); return; }
    const ch = e.etat && e.etat.match(/choix (\d+) (\S+)/);      // (15/11/2026) clic sur la vidéo du lecteur natif
    if (ch) { if (NATIF.choixN === undefined) NATIF.choixN = +ch[1]; else if (+ch[1] !== NATIF.choixN) { NATIF.choixN = +ch[1]; choisirDepuisVue(ch[2], false); } }
    const m = e.etat && e.etat.match(/image (\d+) (\d+) pause (\d)/);
    if (m) { if (document.activeElement !== $('l-image')) $('l-image').value = +m[1];
      $('l-info').textContent = `image ${m[1]} / ${m[2]} · lecteur C++`; $('l-jouer').textContent = m[3] === '1' ? '▶' : '❚❚'; }
  }, 200);
}
// (15/11/2026) options du lecteur natif (pièces cachées, couleurs de matériau, teintes) : réécrites et relues par le lecteur
// ouvert (commande « options ») -> cacher / isoler / changer une couleur ne relance plus la vidéo
function optionsActuelles() {
  const V = E.vue;
  return { caches: V.pieces.filter(p => p.cle && !p.visible && !p.cle.startsWith('stade/') && !p.peau && !p.terrain).map(p => p.cle),
    couleurs: couleursNatif(), sommets: E.avant ? {} : Object.fromEntries(Object.entries(E.teinteSom || {}).map(([k, t]) => [k, [t.H, t.C]])),
    particules: E.avant ? {} : Object.fromEntries(Object.entries(E.teintePtl || {}).map(([k, t]) => [k, [t.H, t.C]])) };
}
async function optionsNatif() {
  if (!NATIF.actif || !E.tech || !E.vue || NATIF.envoiOpt) return;
  const o = optionsActuelles(), j = JSON.stringify(o); if (j === NATIF.opt) return;
  NATIF.envoiOpt = true;
  try { const r = await api('/api/natif_options', Object.assign({ technique: E.tech.code }, o)).catch(() => ({ actif: false }));
    if (r.actif) { NATIF.opt = j; NATIF.cle = cleNatif().cle; } } finally { NATIF.envoiOpt = false; }
}
function cleNatif() {
  const V = E.vue;
  const caches = V.pieces.filter(p => p.cle && !p.visible && !p.cle.startsWith('stade/') && !p.peau && !p.terrain).map(p => p.cle);
  const versions = Object.entries(E.textures).filter(([, x]) => x.modif).map(([k, x]) => k + JSON.stringify(x.moyenne)).join('|');
  return { caches, cle: [E.tech.code, E.avant ? 'avant' : versions, caches.join(','), JSON.stringify(E.coulMat || {}), JSON.stringify(E.teinteSom || {}), JSON.stringify(E.teintePtl || {})].join('#') };
}
// (14/11/2026) couleurs de matériau choisies -> par pièce (options.json du lecteur natif : « couleurs »)
function couleursNatif() {
  const out = {};
  for (const o of E.objets) for (const p of o.pieces || []) { const c = couleurMat(o, p); if (c) out[o.nom + '/' + p.index] = c.rgb; }
  return out;
}
async function modifsNatif() {                  // textures recolorées dans l'Atelier (RGBA en base64)
  const modifs = {}; if (E.avant) return modifs;          // (15/11/2026) « avant » : textures d'origine
  for (const [k, x] of Object.entries(E.textures)) if (x.modif && x.cur && x.cur.getContext) {
    const d = x.cur.getContext('2d').getImageData(0, 0, x.cur.width, x.cur.height);
    modifs[k] = [x.cur.width, x.cur.height, await enBase64(new Uint8Array(d.data.buffer))]; }
  return modifs;
}
// (14/11/2026) retouche de couleur PENDANT la lecture : le lecteur ouvert relit les textures (sans redémarrer)
function texturesNatif() {
  if (!NATIF.actif || !E.tech) return;
  clearTimeout(NATIF.minTex);
  NATIF.minTex = setTimeout(async () => {
    if (!NATIF.actif) return;
    const r = await api('/api/natif_textures', { technique: E.tech.code, modifs: await modifsNatif() }).catch(() => ({ actif: false }));
    if (r.actif) NATIF.cle = cleNatif().cle;
  }, 250);
}
async function lecteurNatif() {
  const V = E.vue; if (!V || !V.lecteur || !E.tech) return;
  const { caches, cle } = cleNatif();
  if (NATIF.actif && NATIF.cle === cle) { const r = await cmdNatif('basculer'); if (r.actif) return; finNatif(false); }   // déjà ouvert : lecture / pause
  // (14/11/2026) lancement déjà en cours (Espace / ▶ pendant le chargement) : rien. Avant : un 2e lecteur, et le 1er restait
  // devant l'Atelier (fenêtre sans bordure impossible à fermer)
  if (NATIF.lance) return;
  NATIF.lance = true; const numero = NATIF.numero = (NATIF.numero || 0) + 1;
  try { await lancerNatif(V, caches, cle, numero); } finally { if (NATIF.numero === numero) NATIF.lance = false; }
}
async function lancerNatif(V, caches, cle, numero) {
  const t0 = performance.now();
  $('l-film-info').textContent = 'Lecteur natif : lancement…';
  const modifs = await modifsNatif();
  // taille de l'image calculée : 16:9 dans la zone (pixels physiques)
  const rect = rectNatif(); let w = rect[2], h = Math.round(w * 9 / 16); if (h > rect[3]) { h = rect[3]; w = Math.round(h * 16 / 9); }
  w = Math.max(640, Math.min(2560, w)); h = Math.round(w * 9 / 16);
  try {
    // jeton dans le titre de la page : le lecteur retrouve CETTE fenêtre (Edge, Opera, Chrome, Firefox…), puis le titre revient
    const jeton = 'L' + Math.random().toString(36).slice(2, 10), titre = document.title.replace(/ · L[a-z0-9]+$/, '');
    document.title = titre + ' · ' + jeton; setTimeout(() => { document.title = titre; }, 4000);
    const opt = optionsActuelles();
    const r = await api('/api/natif', { stade: E.stadeCode || 's10g001', technique: E.tech.code, projet: E.projet, modifs, caches, couleurs: opt.couleurs, sommets: opt.sommets,
      particules: opt.particules, largeur: w, hauteur: h, incruste: true, rect, jeton });
    if (r.erreur) { $('l-film-info').textContent = 'Lecteur natif : ' + r.erreur; return; }
    if (NATIF.numero !== numero || !E.tech || E.vue !== V) {     // annulé pendant le lancement : CE lecteur seulement
      api('/api/natif_cmd', { cmd: 'quitter', pid: r.pid }).catch(() => {}); return; }
    NATIF.actif = true; NATIF.cle = cle; NATIF.rect = rect.join(' '); NATIF.choixN = undefined; NATIF.opt = JSON.stringify(optionsActuelles()); V.cv.style.visibility = 'hidden'; suivreNatif();
    $('l-film-info').textContent = `Lecteur natif (C++) ouvert en ${((performance.now() - t0) / 1000).toFixed(1).replace('.', ',')} s · Espace : pause · flèches : image par image · Échap : fermer`;
  } catch (e) { $('l-film-info').textContent = 'Lecteur natif : erreur ' + e.message; }
}

// boucle d'affichage : l'image du film qui correspond à l'image jouée ; décodage à l'avance des 12 suivantes
function boucleFilm() {
  requestAnimationFrame(boucleFilm);
  const V = E.vue, cv2 = $('vue-d3d');
  if (!filmVisible()) { if (FILM.montre) { FILM.montre = false; if (V && V.joue) cv2.style.display = 'none'; } return; }
  const f = Math.floor(V.image);
  for (let k = f; k < f + 12 && k < FILM.images.length; k++)
    if (FILM.images[k] && !FILM.decod.has(k) && !FILM.attente.has(k)) { FILM.attente.add(k);
      createImageBitmap(FILM.images[k]).then(b => { FILM.attente.delete(k); FILM.decod.set(k, b); }); }
  for (const [k, b] of FILM.decod) if (k < f - 2 || k > f + 14) { b.close(); FILM.decod.delete(k); }
  const b = FILM.decod.get(f);
  if (b && FILM.montre !== f) { if (cv2.width !== b.width || cv2.height !== b.height) { cv2.width = b.width; cv2.height = b.height; }
    cv2.getContext('2d').drawImage(b, 0, 0); cv2.style.display = 'block'; FILM.montre = f; }
}

// (15/11/2026) géométrie des objets ouverts (extrait de ouvrir_ : aussi pour changer de corpulence)
async function chargerGeometries(perso) {
  E.vue.vider();
  for (const o of E.objets) {
    if (o.erreur || o.modeleActeur) continue;     // modèle de personnage (esprit…) : textures seulement, dessiné par le lecteur
    const buf = await api('/api/geometrie?chemin=' + encodeURIComponent(o.chemin));
    const dv = new DataView(buf); const lg = dv.getUint32(0, true);
    const meta = JSON.parse(new TextDecoder().decode(new Uint8Array(buf, 4, lg))); let p = 4 + lg;
    meta.forEach((m, i) => {
      const pos = new Float32Array(buf.slice(p, p + m.nv * 12)); p += m.nv * 12;
      const col = new Uint8Array(buf.slice(p, p + m.nv * 4)); p += m.nv * 4;
      const uv = new Float32Array(buf.slice(p, p + m.nv * 8)); p += m.nv * 8;
      const idx = new Uint16Array(buf.slice(p, p + m.ni * 2)); p += m.ni * 2 + ((4 - (m.ni * 2) % 4) % 4);
      const uvs = [uv];                                            // TEXCOORD0..4 (shaders du jeu)
      for (let k = 0; k < (m.uvs || 0); k++) { uvs.push(new Float32Array(buf.slice(p, p + m.nv * 8))); p += m.nv * 8; }
      const col1 = m.col1 ? new Uint8Array(buf.slice(p, p + m.nv * 4)) : null; if (m.col1) p += m.nv * 4;
      const nor = m.nor ? new Float32Array(buf.slice(p, p + m.nv * 12)) : null; if (m.nor) p += m.nv * 12;
      const tan = m.tan ? new Float32Array(buf.slice(p, p + m.nv * 12)) : null; if (m.tan) p += m.nv * 12;
      // maillage à peau (14/11/2026) : 4 poids + 4 n° d'os (dans la palette) par sommet
      let peau = null; if (m.peau) { peau = { poids: new Float32Array(buf.slice(p, p + m.nv * 16)), os: new Uint8Array(buf.slice(p + m.nv * 16, p + m.nv * 20)) }; p += m.nv * 20; }
      const piece = o.pieces[i]; piece.vue = E.vue.ajouter(o.nom + '/' + i, { nv: m.nv, ni: m.ni, pos, col, idx, uv, uvs, col1, nor, tan, peau });
      if (perso) piece.geo = { pos, uv, idx };          // (15/11/2026) zones.js : pièces du modèle, clic et peinture sur la 3D
      piece.cleObj = o.nom;
    });
  }
}
async function ouvrir(code) {
  try { return await ouvrir_(code); } catch (e) { E.chargement = false; throw e; }
}
async function ouvrir_(code) {
  await sauverProjet();                            // (15/11/2026) dernier changement de la technique d'avant gardé
  finNatif(true);
  $('resultats').style.display = 'none';
  $('titre-tech').textContent = 'Chargement… (la 1re ouverture d\'un modèle lit ses textures : quelques secondes)';
  const perso = estPerso();
  const t = await api(perso ? '/api/personnage?code=' + encodeURIComponent(code) + (ONGLETS_JEU.includes(E.onglet) ? '&cat=' + E.onglet + (E.onglet === 'maillots' ? '&cote=' + (MM.cote || '10') : '') : '') : '/api/technique?code=' + code);
  E.tech = t; E.tech.perso = perso; E.tech.onglet = E.onglet; E.objets = t.objets_details; E.textures = {}; E.coulMat = {}; E.teinteSom = {}; E.teintePtl = {}; E.selPieces.clear(); E.selTex.clear();
  E.cree = null; E.avant = false; majBoutonAvant(); E.recette = []; E.pileRc = []; E.rev = 0; E.reprise = false; E.sigProjet = null; E.chargement = true; E.projet = E.repriseAuto || nouvelleCleProjet(E.onglet, code); E.repriseCle = E.repriseAuto; E.repriseAuto = null; E.texturesCachees = new Set(); E.texturesMontrees = new Set(); E.vignette = null; E.vignetteT = 0; E.vignetteManque = false; if ($('reprise')) $('reprise').style.display = 'none';   // (15/11/2026) pas de sauvegarde pendant le chargement
  if (perso) { $('titre-tech').textContent = `${t.nom}  ·  ${t.code}  ·  ${t.genre}`;
    $('p-nom').value = t.nom + ' (couleurs)'; $('p-desc').value = ''; if ($('rt-nom')) $('rt-nom').value = t.nom + ' (couleurs)'; if ($('cp-nom')) { $('cp-nom').value = ''; $('cp-nom').placeholder = t.nom + ' bis'; } }
  else { $('titre-tech').textContent = `${t.nom}  ·  ${t.code}  ·  ${t.genre}${t.element ? ' · ' + libElement(t.element) : ''}  ·  cinématique ${t.cinematique}`;
    $('f-nom').value = t.nom + ' (couleurs)'; $('f-ban').value = E.banAuto = (t.nom + ' couleurs').toUpperCase();
    // (22/11, retour de muku) traînée du ballon : tirs seulement (dribble, défense, arrêt : rien à régler)
    if ($('bloc-trainee')) { const tir = /^whs/.test(t.code); $('bloc-trainee').style.display = tir ? '' : 'none'; if (!tir) $('f-trainee').value = ''; } }
  // textures
  for (const o of E.objets) {
    if (o.erreur) continue;
    for (const ti of o.textures) {
      const cle = o.nom + '/' + ti.nom, x = { obj: o, nom: ti.nom, info: ti, modif: false, moyenne: ti.moyenne ? ti.moyenne.map(c => c / 255) : [0.8, 0.8, 0.8] };
      E.textures[cle] = x;
      if (ti.lisible) {
        const img = await chargerImage('/tex/' + o.nom + '/' + encodeURIComponent(ti.nom) + '.png');
        const cv = document.createElement('canvas'); cv.width = img.width; cv.height = img.height;
        const cx = cv.getContext('2d'); cx.drawImage(img, 0, 0);
        x.orig = cx.getImageData(0, 0, cv.width, cv.height); x.cur = cv;
      }
    }
  }
  // 3D
  await chargerGeometries(perso);
  // modèle de personnage : opaque (pas d'additif) et rien de caché ; effet : additif, pièces géantes cachées
  E.vue.additif = !perso; $('additif').checked = !perso;
  E.vue.lecteur = null; E.lecteur = null;
  const geantes = perso ? [] : E.vue.cacherGeantes(); E.vue.recadrer(true); teintesPieces(); dessinerPieces(); dessinerTextures(); dessinerAuras(); dessinerMateriaux(); dessinerTeintes(); majCompteurs();
  if (!perso) chargerAnimation(t).catch(e => majRapport('Animation non lue : ' + e.message));
  majRapport(geantes.length ? geantes.length + ' pièce(s) géante(s) cachée(s) au départ (fonds, flashs) : coche-les à gauche pour les voir.' : '');
  dessinerRecette(); paletteTech(); E.sigProjet = signatureProjet(); E.chargement = false; verifierProjet(); proposerReprise();
  if (window.zonesPreparer) try { zonesPreparer(); } catch (e) { console.error('zones', e); }   // (15/11/2026) esprits / totems
  if (E.onglet === 'tenues' && window.ctPreparer) ctPreparer().catch(() => {});   // (15/11/2026) copies
  if (E.onglet === 'objets' && window.ojPreparer) ojPreparer();
}

// pixel shader du jeu -> branche du shader traduit (vue3d.js, FS_J)
function modeDuShader(ps) {
  return /^Effect_ThresholdGrd/.test(ps) ? 1 : ps === 'Effect_TestThreshold' ? 2
    : /^Effect_T1M1(_low)?$/.test(ps) ? 4 : ps === 'Effect_T1M1Rim' ? 5 : ps === 'Effect_T3ThresholdF' ? 3
    : ps === 'Effect_T2' ? 6 : ps === 'Effect_T2M1' ? 10 : ps === 'Effect_T1Flow2' ? 11 : ps === 'Effect_T1M1Flow' ? 12
    : ps === 'Effect_T1PatternFade' ? 7 : ps === 'Effect_VDispRim' ? 8 : ps === 'Effect_Solid' ? 14 : /^Effect_Solid/.test(ps) ? 13
    // distorsion (déforme l'image derrière) et masque de flou : pas de couleur propre -> pas dessinés
    : ps === 'Effect_Aura1' ? 20 : ps === 'Effect_T1M1Morph' ? 21 : ps === 'Effect_T1M1Fog' ? 22 : ps === 'Effect_BorderLight' ? 23 : ps === 'Effect_Water1' ? 24 : ps === 'Effect_Smoke2' ? 25 : ps === 'Effect_T1L' ? 26 : ps === 'Effect_T1L2PatternFadePar' ? 27 : ps === 'Effect_SmokePar1' ? 28 : ps === 'Effect_BallAura1' ? 17 : ps === 'Effect_DifferenceFlow' ? 18 : ps === 'Effect_DifferenceFlowM' ? 19
    : /^Effect_BallAura/.test(ps) ? 1          // BallAura = ThresholdGrd ; colonne du dégradé donnée par le moteur
    : ps === 'Effect_DistortionBlur' ? 16 : /^Effect_Distortion/.test(ps) ? 15     // distorsions (DistortionSolid : comme Distortion, APPROCHÉ)
    : /^Effect_DofMask/.test(ps) ? -1 : 0;
}
// VRAIES PARTICULES (.ptlb) d'un objet : un émetteur par PARTICLE_INFO, dessiné avec le shader de son MATERIAL_INFO
function ajouterEmetteurs(o) {
  const defs = (o.particules && o.particules.emetteurs) || []; o.emetteursVue = [];
  defs.forEach((d, k) => {
    const v = E.vue.ajouterEmetteur(o.nom + '/ptl' + k, d, 0x9E3779B9 ^ (k * 2654435761));
    v.anim = { acteur: o.acteur, noeud: d.noeud };
    const M = d.materiau, ps = d.shader_ps || M.shader || 'Effect_T1';
    // mélange (MATERIAL_INFO[9], lu dans 0x14059f540) : 2 normal, 3 additif, 4 soustractif, 0 / 1 sans mélange
    v.melange = M.melange === 3 ? 'add' : M.melange === 4 ? 'sous' : M.melange === 2 ? 'normal' : 'opaque';
    v.ztest = !!M.b102; v.surEcran = !!o.commun;
    const tex = (d.textures || []).map(n => { const x = n && E.textures[o.nom + '/' + n]; return x && x.cur && !x.info.donnees ? o.nom + '/' + n : null; });
    const donnees = (d.textures || []).map(n => donneesTexture(n && E.textures[o.nom + '/' + n]));
    const params = [0, 1, 2, 3, 4, 5, 6, 7].map(i => d.shader.slice(4 * i, 4 * i + 4));   // SHADER_INFO = u_shaderParam0..7
    v.jeu = { ps, mode: modeDuShader(ps), donnees, adressage: M.adressage.concat([[1, 1], [1, 1], [1, 1]]), particules: false,
      approx: !/^Effect_(T1|T1_low|ThresholdGrd|BallAura1)$/.test(ps), diffuse: [1, 1, 1, 1], ambient: [0, 0, 0, 1], params, texproj: [],
      tex: tex.length ? tex : [null], uvCrcs: [], alphaRepos: 1, colonne: /^Effect_BallAura/.test(ps) ? couleurTirBalle() : null };
    o.emetteursVue.push(v);
  });
}

// (15/11/2026) pixels lus par le code des fausses particules (_parColor = couleur au fil du temps) : la version RETOUCHÉE si
// la texture a été recolorée dans l'Atelier (avant : toujours l'originale -> la retouche ne se voyait pas)
function donneesTexture(x) {
  if (!x || !x.orig) return null;
  if (E.avant || !x.modif || !x.cur || !x.cur.getContext) return x.orig;
  if (!x.donneesCur || x.donneesV !== x.moyenne) { x.donneesCur = x.cur.getContext('2d').getImageData(0, 0, x.cur.width, x.cur.height); x.donneesV = x.moyenne; }
  return x.donneesCur;
}
function texPrincipale(o, piece) {
  for (const n of piece.textures) { const x = E.textures[o.nom + '/' + n]; if (x && x.cur && !x.info.donnees) return x; }
  return null;
}
function teintesPieces() {
  // la 3D affiche la texture principale de chaque pièce (mise à jour après chaque retouche) x la couleur de ses sommets ;
  // la pastille de la liste montre la couleur moyenne de cette texture
  for (const [cle, x] of Object.entries(E.textures)) if (x.cur && !x.info.donnees) { E.vue.texture(cle, texAffichee(x));
    if (E.vue.textures['peau:' + cle]) E.vue.texture('peau:' + cle, texAffichee(x)); }   // (15/11/2026) modèles d'acteurs
  for (const o of E.objets) { if (o.erreur) continue;
    for (const p of o.pieces) { if (!p.vue) continue; const x = texPrincipale(o, p);
      // couleur du matériau (table des couleurs du G4MD) x son intensité (gain additif)
      const cm = couleurMat(o, p); p.vue.couleurMat = cm ? cm.rgb : null;
      const c = cm ? cm.rgb : (p.couleur || [1, 1, 1, 1]), g = Math.min(p.gain || 1, 3);
      p.vue.texCle = x ? o.nom + '/' + x.nom : null; p.vue.teinte = [c[0] * g, c[1] * g, c[2] * g, 1];
      p.vue.melange = p.melange; p.vue.ztest = p.ztest !== false; p.vue.zecrit = !!p.zecrit; p.vue.faces = p.faces ? 1 : 0; p.vue.biais = p.biais || 0; p.vue.panneau = p.panneau || 0; p.vue.prio = p.prio !== undefined ? p.prio : 30;   // couche de dessin (LU)   // mode de mélange du jeu (additif / normal)
      // RENDU DU JEU : le pixel shader du matériau (lu dans les fichiers du jeu) et ses données
      p.vue.jeu = null;
      if (p.jeu && p.jeu.shader_ps && p.jeu.diffuse) {
        const ps = p.jeu.shader_ps;
        const mode = modeDuShader(ps);
        const tex = p.textures.map(n => { const x = E.textures[o.nom + '/' + n]; return x && x.cur && !x.info.donnees ? o.nom + '/' + n : null; });
        // nom de matériau sûr (sinon les animations G4MA ne le retrouvent pas : on n'applique pas son alpha de repos)
        const nomSur = !/^(partie[ _]|materiau_)/.test(p.shader || '');
        const donnees = p.textures.map(n => donneesTexture(E.textures[o.nom + '/' + n]));
        p.vue.jeu = { ps, mode, donnees, adressage: p.jeu.adressage || null, particules: /^Effect_FakeParticle(RotZ|RotZPat|Line1|Line2|Line2F)?$/.test(ps), ligne2: /^Effect_FakeParticleLine2F?$/.test(ps), ligne2F: ps === 'Effect_FakeParticleLine2F', ligne1: ps === 'Effect_FakeParticleLine1', soft: /^Effect_(T1|T1M1|T1M1Rim|ThresholdGrd|TestThreshold|T3ThresholdF|BallAura1|T1M1Flow|DistortionBlur|T1PatternFade|DifferenceFlow|DifferenceFlowM|VDispRim|Aura1|T1M1Morph|T1M1Fog|BorderLight|Water1|Smoke2|T1L|T1L2PatternFadePar|SmokePar1)$/.test(ps), ombreFx: /^Effect_(T1L|T1L2PatternFadePar|SmokePar1)$/.test(ps),
          rotz: /^Effect_FakeParticleRotZ/.test(ps), pat: ps === 'Effect_FakeParticleRotZPat',
          approx: !/^Effect_(T1|T1_low|ThresholdGrd|ThresholdGrd_low|TestThreshold|FakeParticle|T1M1|T1M1_low|T1M1Rim|T3ThresholdF|T2|T2M1|T1Flow2|T1M1Flow|T1PatternFade|FakeParticleRotZ|FakeParticleRotZPat|Solid|SolidToon1|VDispRim|FakeParticleLine1|FakeParticleLine2|FakeParticleLine2F|Aura1|T1M1Morph|T1M1Fog|BorderLight|Water1|Smoke2|T1L|T1L2PatternFadePar|SmokePar1|BallAura1|DifferenceFlow|DifferenceFlowM|Distortion|DistortionBlur)$/.test(ps),
          diffuse: cm ? [cm.rgb[0], cm.rgb[1], cm.rgb[2], p.jeu.diffuse[3]] : p.jeu.diffuse, ambient: p.jeu.ambient || [0, 0, 0, 1], params: p.jeu.params || [], texproj: p.jeu.texproj || [],
          tex, uvCrcs: (p.uv_crcs || []).map(c => c >>> 0), alphaRepos: nomSur ? p.jeu.diffuse[3] : 1,
          // aura du ballon : colonne de la palette BallAura0010 = « couleur de tir » de la technique (0 montagne, 1 vent,
          // 2 feu, 3 forêt, 4 vide), vérifié sur les couleurs de la palette
          colonne: /^Effect_BallAura/.test(ps) ? couleurTirBalle() : null };
      }
      // nuages / fumées (matériaux « T3Threshold », 5 textures) : [0] couleur d'ombre, [1] couleur de lumière,
      // [3] forme (niveaux de gris -> transparence), [4] détail (passage ombre -> lumière)
      p.vue.nuage = null;
      if (/Threshold/.test(p.shader || '') && p.textures.length >= 5) {
        const t = k => E.textures[o.nom + '/' + p.textures[k]];
        const a = t(0), b = t(1), f = t(3), d = t(4);
        if (a && b && f && f.cur && d && d.cur)
          p.vue.nuage = { ombre: a.moyenne, lum: b.moyenne, forme: o.nom + '/' + f.nom, detail: o.nom + '/' + d.nom };
      }
      const m = x ? x.moyenne : [0.75, 0.75, 0.75]; p.pastille = m; } }
}

// ------------------------------------------------------------------ pièces
function dessinerPieces() {
  const box = $('pieces'); box.innerHTML = '';
  for (const o of E.objets) {
    const t = document.createElement('div'); t.className = 'objet-titre'; t.textContent = o.erreur ? `${o.acteur} (illisible : ${o.erreur})` : o.modeleActeur ? `${o.nom}  (modèle de personnage : textures seulement)` : `${o.nom}  (${o.pieces.length} pièces)`; box.appendChild(t);
    if (o.erreur) continue;
    o.pieces.forEach(p => {
      const cle = o.nom + '/' + p.index, d = document.createElement('div'); d.className = 'piece' + (E.selPieces.has(cle) ? ' sel' : ''); d.dataset.cle = cle;
      const cb = document.createElement('input'); cb.type = 'checkbox'; cb.checked = p.vue ? p.vue.visible : true;
      cb.onclick = ev => { ev.stopPropagation(); if (p.vue) p.vue.visible = cb.checked; };
      const pa = document.createElement('span'); pa.className = 'pastille';
      if (p.pastille) pa.style.background = `rgb(${p.pastille.map(c => Math.round(c * 255)).join(',')})`;
      const n = document.createElement('span'); n.className = 'n'; n.textContent = `${p.nom} (${p.materiau ?? '-'})`; n.title = p.textures.join(', ');
      const iso = document.createElement('button'); iso.textContent = 'Isoler';
      iso.onclick = ev => { ev.stopPropagation(); for (const oo of E.objets) for (const pp of oo.pieces || []) if (pp.vue) pp.vue.visible = pp === p; E.vue.recadrer(true); dessinerPieces(); };
      const cac = document.createElement('button'); cac.textContent = 'Cacher';
      cac.onclick = ev => { ev.stopPropagation(); if (p.vue) p.vue.visible = false; dessinerPieces(); };
      d.append(cb, pa, n, iso, cac);
      d.onclick = ev => { if (!ev.ctrlKey) E.selPieces.clear(); if (E.selPieces.has(cle) && ev.ctrlKey) E.selPieces.delete(cle); else E.selPieces.add(cle); majSelection(); };
      box.appendChild(d);
    });
  }
}
// (15/11/2026) particules choisies (clé « objet/ptlK ») : textures de leur émetteur
function texturesParticulesChoisies() {
  const out = [];
  for (const k of E.selPieces) { const m = /^(.*)\/ptl(\d+)$/.exec(k); if (!m) continue;
    const o = E.objets.find(x => x.nom === m[1]); const d = o && o.particules && (o.particules.emetteurs || [])[+m[2]];
    for (const n of (d && d.textures) || []) if (n) out.push([o, n]); }
  return out;
}
// (15/11/2026) CLIC SUR LA VUE (aperçu WebGL ou lecteur natif) : la pièce / les particules sous la souris deviennent la sélection
// (Ctrl ou Maj : ajoutées) ; la ligne de la pièce est montrée dans la liste et le bloc Textures s'ouvre.
function choisirDepuisVue(cle, ajout) {
  if (!E.tech) return;
  if (!cle || cle === '-') { if (!ajout) { E.selPieces.clear(); majSelection(); } majRapport('Clic : aucune pièce d\'effet à cet endroit.'); return; }
  if (!ajout) E.selPieces.clear();
  if (ajout && E.selPieces.has(cle)) E.selPieces.delete(cle); else E.selPieces.add(cle);
  majSelection();
  const ligne = document.querySelector(`.piece[data-cle="${CSS.escape(cle)}"]`); if (ligne) ligne.scrollIntoView({ block: 'nearest' });
  const bt = document.querySelector('#panneau-couleurs details.bloc'); if (bt) bt.open = true;
  const m = /^(.*)\/ptl(\d+)$/.exec(cle), o = E.objets.find(x => x.nom === cle.split('/')[0]);
  const p = !m && o && (o.pieces || [])[+cle.split('/')[1]];
  majRapport(m ? `Clic : particules de ${m[1]} (émetteur ${+m[2] + 1}).` : p ? `Clic : pièce ${p.nom}.` : `Clic : ${cle}.`);
}
function majSelection() {
  for (const o of E.objets) for (const p of o.pieces || []) if (p.vue) p.vue.sel = E.selPieces.has(o.nom + '/' + p.index);
  for (const o of E.objets) (o.emetteursVue || []).forEach((v, k) => { v.sel = E.selPieces.has(o.nom + '/ptl' + k); });
  // textures des pièces choisies -> sélection de textures
  if (E.selPieces.size) { E.selTex.clear();
    for (const o of E.objets) for (const p of o.pieces || []) if (E.selPieces.has(o.nom + '/' + p.index)) for (const n of p.textures) { const x = E.textures[o.nom + '/' + n]; if (x && x.cur && !x.info.donnees) E.selTex.add(o.nom + '/' + n); }
    for (const [o, n] of texturesParticulesChoisies()) { const x = E.textures[o.nom + '/' + n]; if (x && x.cur && !x.info.donnees) E.selTex.add(o.nom + '/' + n); } }
  dessinerPieces(); dessinerTextures(); dessinerMateriaux(); dessinerTeintes(); majCompteurs();
}

// ------------------------------------------------------------------ textures
// ------------------------------------------------------------------ clic sur une texture : aller où elle se voit (15/11/2026)
// L'animation est parcourue une fois (toutes les 2 images, L.calculer) : pour chaque pièce, sa présence à l'écran avec la MÊME
// règle que l'aperçu (vue3d._animer : objet visible, os pas caché, opacité >= 0,005 ; particules : objet visible, nœud pas caché).
// Pour une texture : somme sur les pièces / émetteurs qui l'utilisent ; on va au plus fort de la plus longue période visible.
let CHRONO = null;
async function chronologie() {
  const L = E.lecteur; if (!L || !E.vue) return null;
  if (CHRONO && CHRONO.L === L) return CHRONO.pret;
  const pas = 2, n = Math.max(1, Math.ceil(L.duree / pas)), vis = new Map();
  const pieces = E.vue.pieces.filter(p => p.anim && p.cle && !p.terrain && !p.peau && !p.balle);
  for (const p of pieces) vis.set(p.cle, new Float32Array(n));
  CHRONO = { L, pas, n, vis, pret: null };
  CHRONO.pret = (async () => {
    for (let k = 0; k < n; k++) {
      let res = null; try { res = L.calculer(k * pas); } catch (e) { continue; }
      for (const p of pieces) { const o = res.objets[p.anim.acteur]; let v = 0;
        if (o && o.visible) {
          if (p.ptl) { const i = o.sq && o.sq.parNom ? o.sq.parNom[p.anim.noeud] : undefined; v = i !== undefined && o.cache && o.cache[i] ? 0 : 1; }
          else if (p.anim.os === undefined) v = 1;
          else { const op = o.opa && p.anim.mat in o.opa ? o.opa[p.anim.mat] : (p.jeu ? p.jeu.alphaRepos : 1);
            v = o.cache && o.cache[p.anim.os] ? 0 : op >= 0.005 ? Math.min(1, op) : 0; } }
        vis.get(p.cle)[k] = v; }
      if (k % 15 === 14) await new Promise(r => setTimeout(r, 0));
    }
    return CHRONO;
  })();
  return CHRONO.pret;
}
function piecesDeTexture(cle) {         // clés des pièces / émetteurs (vue) qui utilisent cette texture
  const [on, ...r] = cle.split('/'), nom = r.join('/'), o = E.objets.find(x => x.nom === on), out = [];
  if (!o) return out;
  (o.pieces || []).forEach((p, i) => { if ((p.textures || []).includes(nom)) out.push(on + '/' + i); });
  ((o.particules && o.particules.emetteurs) || []).forEach((d, k) => { if ((d.textures || []).includes(nom)) out.push(on + '/ptl' + k); });
  return out;
}
// (15/11/2026) faire briller des pièces / émetteurs quelques instants (aperçu WebGL + lecteur natif : commande « surligner »)
function surligner(cles, ms) {
  ms = ms || 2600; const t = performance.now();
  if (E.vue) E.vue.eclat = { cles: new Set(cles), debut: t, fin: t + ms };
  if (NATIF.actif) { let c = 'surligner ' + ms; for (const k of cles) { if (c.length + k.length + 1 > 480) break; c += ' ' + k; } cmdNatif(c); }
}
// (15/11/2026) menu du clic droit (vignettes de textures, lignes de couleurs) : actions = [[libellé, fonction], …]
function menuContexte(ev, titre, actions) {
  let m = $('menu-tex');
  if (!m) { m = document.createElement('div'); m.id = 'menu-tex'; document.body.appendChild(m);
    document.addEventListener('mousedown', e => { if (!e.target.closest('#menu-tex')) m.style.display = 'none'; });
    document.addEventListener('keydown', e => { if (e.key === 'Escape') m.style.display = 'none'; }); }
  m.innerHTML = '<div class="titre"></div>' + actions.map((a, i) => `<button data-i="${i}"></button>`).join('');
  m.querySelector('.titre').textContent = titre;
  m.querySelectorAll('button').forEach((b, i) => { b.textContent = actions[i][0]; });
  m.style.display = 'block';
  const w = m.offsetWidth, h = m.offsetHeight;
  m.style.left = Math.min(ev.clientX, innerWidth - w - 4) + 'px'; m.style.top = Math.min(ev.clientY, innerHeight - h - 4) + 'px';
  m.onclick = e => { const b = e.target.closest('button'); if (!b) return; m.style.display = 'none'; actions[+b.dataset.i][1](); };
}
function menuTexture(ev, cle) {
  const x = E.textures[cle], peutDessiner = x && x.cur && !x.info.donnees;
  // (15/11/2026) « Copier sur » : textures de même taille du même objet (ex. versions _10 / _20 d'un objet de technique,
  // même patron) ; la version montrée par le jeu en premier
  const carteTech = n => /(nml|oc|sp|spm|line|msk)$/.test(n);      // relief, ombre, reflets, contour, masque : pas des couleurs
  const cibles = peutDessiner && !carteTech(x.nom) ? Object.entries(E.textures).filter(([k, y]) => k !== cle && y.obj === x.obj && y.cur && !y.info.donnees && !carteTech(y.nom)
      && y.cur.width === x.cur.width && y.cur.height === x.cur.height)
    .sort((a, b) => (texturePasMontree(a[0]) ? 1 : 0) - (texturePasMontree(b[0]) ? 1 : 0)).slice(0, 8) : [];
  // (22/11, demande d'un joueur : « mettre des textures de Kabuki Smash sur le Triangle ZZ ») presse-papiers de l'Atelier :
  // il garde l'image quand on ouvre une autre technique
  const presse = peutDessiner ? [['📄 Copier l’image (pour une autre technique)', () => copierPresse(cle)]]
    .concat(PRESSE.img ? [[`📋 Coller ici : ${PRESSE.nom}${PRESSE.tech ? ' (' + PRESSE.tech + ')' : ''}`, () => collerPresse(cle)]] : []) : [];
  menuContexte(ev, x ? x.nom : cle, [['◎ Localiser la texture', () => allerVersTexture(cle, true)]].concat(peutDessiner ? [['✎ Dessiner', () => ouvrirEditeur(cle)]] : [])
    .concat(cibles.map(([k, y]) => [`⧉ Copier cette image sur ${y.nom}${!texturePasMontree(k) && texturePasMontree(cle) ? ' (version montrée)' : ''}`, () => copierTexture(cle, k)]))
    .concat(presse));
}
const PRESSE = { img: null, nom: '', tech: '' };
function copierPresse(cle) {
  const a = E.textures[cle]; if (!a || !a.cur) return;
  const c = document.createElement('canvas'); c.width = a.cur.width; c.height = a.cur.height; c.getContext('2d').drawImage(a.cur, 0, 0);
  PRESSE.img = c; PRESSE.nom = a.nom; PRESSE.tech = E.tech ? E.tech.nom : '';
  majRapport(`Image de ${a.nom} copiée (${c.width} × ${c.height}). Ouvre une autre technique, clic droit sur une texture : « Coller ici ».`);
}
function collerPresse(vers) {
  const a = PRESSE.img, b = E.textures[vers]; if (!a || !b || !b.cur) return;
  quitterAvant(); E.pileRc.push(photoEtat()); if (E.pileRc.length > 8) E.pileRc.shift();
  const w = b.cur.width, h = b.cur.height, cx = b.cur.getContext('2d');
  cx.clearRect(0, 0, w, h); cx.imageSmoothingQuality = 'high'; cx.drawImage(a, 0, 0, w, h);
  b.base = cx.getImageData(0, 0, w, h); b.modif = true; b.moyenne = moyenne(b.base); b.donneesCur = null;
  apresRetouche(); paletteTech();
  majRapport(`Image de ${PRESSE.nom} collée sur ${b.nom}` + (a.width !== w || a.height !== h ? ` (mise à sa taille : ${a.width} × ${a.height} → ${w} × ${h})` : '')
    + '. La forme des pièces reste celle de cette technique : une image faite pour une autre forme peut tomber autrement.'
    + ' Pour revenir en arrière : « Annuler le dernier » (bloc Remplacer une couleur partout).');
}
// (15/11/2026) texture d'une version d'objet qu'AUCUN acteur de la cinématique ne montre (voir chargerPeau)
function texturePasMontree(cle) { return !!(E.texturesCachees && E.texturesCachees.has(cle) && !(E.texturesMontrees && E.texturesMontrees.has(cle))); }
// (15/11/2026) copie l'image (avec tes retouches) d'une texture sur une autre de même taille ; « Annuler le dernier » la défait
function copierTexture(de, vers) {
  const a = E.textures[de], b = E.textures[vers]; if (!a || !b || !a.cur || !b.cur) return;
  quitterAvant(); E.pileRc.push(photoEtat()); if (E.pileRc.length > 8) E.pileRc.shift();
  const cx = b.cur.getContext('2d'); cx.clearRect(0, 0, b.cur.width, b.cur.height); cx.drawImage(a.cur, 0, 0);
  b.base = cx.getImageData(0, 0, b.cur.width, b.cur.height); b.modif = true; b.moyenne = moyenne(b.base); b.donneesCur = null;
  apresRetouche(); paletteTech();
  majRapport(`Image de ${a.nom} copiée sur ${b.nom}. Pour revenir en arrière : « Annuler le dernier » (bloc Remplacer une couleur partout).`);
}
async function allerVersTexture(cle, demande) {
  const x = E.textures[cle], nom = 'Texture ' + (x ? x.nom : cle);
  const cles = piecesDeTexture(cle); if (!cles.length) { majRapport(`${nom} : aucune pièce ne l'utilise.`); return; }
  return allerVersPieces(cles, nom, demande);
}
// (15/11/2026) aller à l'image où ces pièces / émetteurs se voient le plus (textures, matériaux, sommets, particules), puis
// les faire briller : plus longue période visible, image la plus forte au milieu (règle de vue3d._animer, voir chronologie)
async function allerVersPieces(cles, nom, demande) {
  if (!E.tech || E.tech.perso) return;
  if (!E.lecteur) { if (demande) majRapport('L’animation n’est pas encore chargée : attends un instant puis réessaie.'); return; }
  if (!cles.length) { majRapport(`${nom} : aucune pièce.`); return; }
  if (demande) majRapport(`${nom} : recherche des images où ça se voit…`);
  const C = await chronologie(); if (!C) return;
  const sc = new Float32Array(C.n), visibles = [];
  for (const k of cles) { const v = C.vis.get(k); if (!v) continue; for (let i = 0; i < C.n; i++) sc[i] += v[i]; }
  // plus longue suite d'images où la texture se voit (somme des scores) ; dedans, l'image la plus forte (milieu des égalités)
  let best = null;
  for (let i = 0; i < C.n;) { if (sc[i] <= 0) { i++; continue; }
    let j = i, somme = 0; while (j < C.n && sc[j] > 0) { somme += sc[j]; j++; }
    if (!best || somme > best.somme) best = { a: i, b: j - 1, somme };
    i = j; }
  if (!best) { majRapport(`${nom} : jamais visible pendant l'animation (pièces cachées ou transparentes).`); return; }
  let mx = 0; for (let i = best.a; i <= best.b; i++) mx = Math.max(mx, sc[i]);
  const forts = []; for (let i = best.a; i <= best.b; i++) if (sc[i] >= mx * 0.999) forts.push(i);
  const f = forts[Math.floor(forts.length / 2)] * C.pas;
  const li = $('l-image'); if (li) { li.value = f; li.dispatchEvent(new Event('input')); }
  surligner(cles);
  majRapport(`${nom} : image ${f} (visible des images ${best.a * C.pas} à ${best.b * C.pas}).`);
}

function texturesVisibles() {
  if (!$('filtre-sel').checked || !E.selPieces.size) return Object.keys(E.textures);
  const s = new Set();
  for (const o of E.objets) for (const p of o.pieces || []) if (E.selPieces.has(o.nom + '/' + p.index)) for (const n of p.textures) s.add(o.nom + '/' + n);
  for (const [o, n] of texturesParticulesChoisies()) s.add(o.nom + '/' + n);
  // modèles de personnages (esprit guerrier…) : pas de pièce à sélectionner, leurs textures restent toujours visibles
  for (const o of E.objets) if (o.modeleActeur && !o.erreur) for (const t of o.textures) s.add(o.nom + '/' + t.nom);
  return [...s];
}
function dessinerTextures() {
  const g = $('textures'); g.innerHTML = '';
  for (const cle of texturesVisibles()) {
    const x = E.textures[cle]; if (!x) continue;
    const d = document.createElement('div'); d.className = 'tex' + (E.selTex.has(cle) ? ' sel' : '') + (x.modif ? ' modif' : '') + (!x.cur || x.info.donnees ? ' donnees' : '');
    const cv = document.createElement('canvas'); cv.width = 64; cv.height = 64;
    if (x.cur) cv.getContext('2d').drawImage(x.cur, 0, 0, 64, 64);
    const n = document.createElement('div'); n.className = 'nom'; n.textContent = x.nom.replace(x.obj.nom + '_', '#');
    d.title = `${x.nom}${x.info.w ? ` (${x.info.w}×${x.info.h})` : ''}${x.info.donnees ? ' : carte de données, non modifiable' : !x.cur ? ' : format non lu' : ''}`;
    // (15/11/2026) texture d'une version de l'objet que le jeu ne montre pas dans cette technique
    if (texturePasMontree(cle)) { d.classList.add('cachee');
      d.title += '\nVersion de l’objet que le jeu ne montre PAS dans cette technique : tes changements ici ne se verront pas.'
        + '\nClic droit → « Copier cette image sur … » pour les mettre sur la version montrée.'; }
    d.append(cv, n);
    d.ondblclick = () => { if (x.cur && !x.info.donnees) ouvrirEditeur(cle); };      // (15/11/2026) éditeur en grand
    d.oncontextmenu = ev => { ev.preventDefault(); menuTexture(ev, cle); };      // (15/11/2026) clic droit : Localiser / Dessiner
    d.onclick = ev => { if (!x.cur || x.info.donnees) return; if (!ev.ctrlKey && !ev.shiftKey) E.selTex.clear();
      if (E.selTex.has(cle) && (ev.ctrlKey || ev.shiftKey)) E.selTex.delete(cle); else E.selTex.add(cle); dessinerTextures(); dessinerZone();
      if (window.atActiver && E.tech && !E.tech.perso) atActiver(cle); };     // (15/11/2026) atelier de retouche : cette texture
    g.appendChild(d);
  }
}
function reglage(mode) {
  return { mode: mode || $('mode').value, c1: hex2rgb($('c1').value), c2: hex2rgb($('c2').value), sat: $('sat').value / 100, lum: $('lum').value / 100,
    garderOr: $('garder-or').checked, garderBlanc: $('garder-blanc').checked,
    zone: $('zone-on').checked ? (() => { const [h, s, v] = rgb2hsv(...hex2rgb($('zone-c').value)); return { h, s, v, tol: $('zone-t').value / 100 }; })() : null };
}
function appliquerA(cle, r) {
  const x = E.textures[cle]; if (!x || !x.cur || x.info.donnees) return;
  const cx = x.cur.getContext('2d'), dst = cx.createImageData(x.orig.width, x.orig.height);
  // (15/11/2026) x.base = dessin fait dans l'éditeur (sinon il serait effacé)
  recolorer(x.base || x.orig, dst, r); cx.putImageData(dst, 0, 0); x.modif = true; x.moyenne = moyenne(dst);
}
// (15/11/2026) ÉDITEUR DE TEXTURE (web/editeur.html, copie adaptée du studio de l'Atelier Maillots) : ouvert en grand par-dessus
// l'Atelier ; il lit la texture ici (E.textures[cle].cur / .orig) et renvoie son dessin (recevoirTextureEditee, en direct).
// Le lecteur natif (fenêtre posée sur la vue) est caché pendant l'édition, puis remontré.
// (15/11/2026) l'éditeur prend la place du panneau de droite (la colonne des pièces se replie) : la vue 3D / le lecteur natif
// restent visibles au milieu pendant qu'on dessine (le lecteur suit la nouvelle taille de la vue)
// (15/11/2026) « Dessiner » (double-clic, menu, bouton) ouvre le MODE DESSIN (atelier.js) : TOUT y est (outils façon Photoshop
// + trait droit, formes, motifs, texte, image de l'ancien éditeur : atelier_outils.js). ouvrirEditeurComplet n'est plus appelé.
function ouvrirEditeur(cle) { if (window.atDessinOuvrir) return atDessinOuvrir(cle); return ouvrirEditeurComplet(cle); }
function ouvrirEditeurComplet(cle) {
  const x = E.textures[cle]; if (!x || !x.cur || x.info.donnees) return;
  quitterAvant();
  let o = $('editeur-tex'); if (!o) { o = document.createElement('section'); o.id = 'editeur-tex'; document.querySelector('main').appendChild(o); }
  o.innerHTML = `<iframe src="/web/editeur.html?panneau=1&k=${encodeURIComponent(cle)}" title="Dessiner sur la texture"></iframe>`;
  document.body.classList.add('edition');
  setTimeout(() => { const f = o.querySelector('iframe'); if (f) f.focus(); }, 200);
}
function fermerEditeur() {
  const o = $('editeur-tex'); if (o) o.innerHTML = '';
  document.body.classList.remove('edition');
}
function recevoirTextureEditee(cle, img) {
  const x = E.textures[cle]; if (!x || !x.cur) return;
  const cx = x.cur.getContext('2d'); cx.clearRect(0, 0, x.cur.width, x.cur.height); cx.putImageData(img, 0, 0);
  x.base = img; x.modif = true; x.moyenne = moyenne(img); x.donneesCur = null;
  apresRetouche();
}
window.ouvrirEditeur = ouvrirEditeur; window.fermerEditeur = fermerEditeur; window.recevoirTextureEditee = recevoirTextureEditee; window.texturePourEditeur = cle => E.textures[cle] || null;
function apresRetouche() { quitterAvant(); E.rev = (E.rev || 0) + 1; teintesPieces(); dessinerPieces(); dessinerTextures(); dessinerZone(); texturesNatif(); majCompteurs();
  if (E.onglet === 'objets' && window.ojIcone) ojIcone(); }
// grande vignette de la 1re texture choisie : on y prend la couleur à changer ; la zone visée est surlignée
function dessinerZone() {
  const cv = $('zone-apercu'); if (!$('zone-on').checked) return;
  const cle = [...E.selTex][0] || Object.keys(E.textures).find(k => E.textures[k].cur && !E.textures[k].info.donnees);
  const x = cle && E.textures[cle]; const c = cv.getContext('2d');
  cv.width = 512; cv.height = 512; c.clearRect(0, 0, 512, 512); if (!x || !x.cur) return;
  c.drawImage(x.cur, 0, 0, 512, 512); cv.dataset.cle = cle;
  const img = c.getImageData(0, 0, 512, 512), d = img.data, r = reglage();
  for (let i = 0; i < d.length; i += 4) { const [h, s, v] = rgb2hsv(d[i] / 255, d[i + 1] / 255, d[i + 2] / 255);
    if (poidsZone(h, s, v, r.zone) <= 0.01) { d[i] *= 0.3; d[i + 1] *= 0.3; d[i + 2] *= 0.3; } }   // hors zone : assombri
  c.putImageData(img, 0, 0);
}

// ------------------------------------------------------------------ couleurs des matériaux (14/11/2026)
// u_diffuse du matériau (table des couleurs du G4MD, + pistes G4MA 16-19) : multiplie les textures. Une texture blanche
// sous un matériau jaune (anneaux de Frappe cosmique) ne se recolore pas par la texture : on change ici la couleur du matériau.
// Clé : objet/n° de matériau (plusieurs pièces peuvent partager un matériau). La luminosité d'origine est gardée : la
// couleur choisie (0..1) est multipliée par max(1, plus grande composante d'origine) (couleurs HDR > 1 du jeu).
const versHex = c => '#' + c.slice(0, 3).map(v => Math.round(Math.max(0, Math.min(1, v)) * 255).toString(16).padStart(2, '0')).join('');
function couleurMat(o, p) { return E.avant ? null : (E.coulMat || {})[o.nom + '/' + p.materiau] || null; }
function nomMateriau(p) {             // nom donné à VRFW : le nom du matériau, sinon son crc (« e97d9762 »)
  return p.shader && !/^(partie[ _]|materiau_)/.test(p.shader) ? p.shader : (p.mat_crc >>> 0).toString(16).padStart(8, '0');
}
// (15/11/2026) LISIBILITÉ : une ligne = pastille, nom (une ligne), couleur, ↺. Avec des pièces sélectionnées (et « seulement
// celles des pièces sélectionnées »), seules leurs lignes ; sinon les colorées, les autres repliées.
function filtreSel() { return $('filtre-sel') && $('filtre-sel').checked && E.selPieces.size ? E.selPieces : null; }
function ligneCouleur({ pastille, nom, titre, valeur, modif, choisir, remettre, surNom, cles }) {
  const d = document.createElement('div'); d.className = 'lc' + (modif ? ' modif' : '');
  const pa = document.createElement('span'); pa.className = 'pastille'; pa.style.background = pastille;
  const n = document.createElement('span'); n.className = 'n'; n.textContent = nom;
  n.title = titre + (surNom ? '\n(cliquer : choisir ces pièces)' : '') + (cles && cles.length ? '\n(clic droit : localiser)' : '');
  if (surNom) n.onclick = surNom;
  const ent = document.createElement('input'); ent.type = 'color'; ent.value = valeur; ent.title = 'Choisir la couleur';
  ent.oninput = () => { quitterAvant(); choisir(ent.value); d.classList.add('modif'); majCompteurs(); };
  const rz = document.createElement('button'); rz.textContent = '↺'; rz.title = 'Remettre la couleur du jeu';
  rz.onclick = () => { quitterAvant(); ent.value = remettre(); d.classList.remove('modif'); majCompteurs(); };
  // (15/11/2026) clic droit : aller où ces pièces se voient (elles brillent un instant)
  if (cles && cles.length) d.oncontextmenu = ev => { ev.preventDefault();
    menuContexte(ev, nom, [['◎ Localiser', () => allerVersPieces(cles, nom, true)]]
      .concat(surNom ? [['☐ Choisir ces pièces', surNom]] : []).concat([['↺ Remettre la couleur du jeu', () => rz.click()]])); };
  d.append(pa, n, ent, rz); return d;
}
function blocReplie(titre, lignes) {
  const dd = document.createElement('details'); dd.className = 'replie'; const s = document.createElement('summary');
  s.textContent = `${titre} (${lignes.length})`; dd.appendChild(s); for (const l of lignes) dd.appendChild(l); return dd;
}
function majCompteurs() {
  const n = (x, mot) => x ? `${x} ${mot}${x > 1 ? 's' : ''}` : '';
  if ($('cpt-tex')) $('cpt-tex').textContent = n(Object.values(E.textures || {}).filter(x => x.modif).length, 'changée');
  if ($('cpt-mat')) $('cpt-mat').textContent = n(Object.keys(E.coulMat || {}).length, 'changé');
  if ($('cpt-teintes')) $('cpt-teintes').textContent = n(Object.keys(E.teinteSom || {}).length + Object.keys(E.teintePtl || {}).length, 'changé');
  const i = $('info-sel'); if (i) i.innerHTML = !E.tech ? '' : E.selPieces.size
    ? `<b>${E.selPieces.size} pièce${E.selPieces.size > 1 ? 's' : ''} sélectionnée${E.selPieces.size > 1 ? 's' : ''}</b> : les listes ne montrent que leurs couleurs (Ctrl + clic pour en ajouter).`
    : 'Clique une pièce à gauche (ou un nom ci-dessous) pour ne voir que ses couleurs.';
}
function dessinerMateriaux() {
  const b = $('materiaux'); if (!b) return; b.innerHTML = '';
  if (!E.tech || E.tech.perso) { b.innerHTML = '<p class="aide">Seulement pour les techniques.</p>'; return; }
  const lignes = [];
  for (const o of E.objets) { if (o.erreur || o.modeleActeur || o.commun) continue;
    const parMat = new Map();
    for (const p of o.pieces || []) { if (p.materiau === null || p.materiau === undefined) continue;
      if (!parMat.has(p.materiau)) parMat.set(p.materiau, []); parMat.get(p.materiau).push(p); }
    for (const [m, ps] of parMat) { const p0 = ps[0], d0 = (p0.jeu && p0.jeu.diffuse) || p0.couleur || [1, 1, 1, 1];
      const blanc = d0[0] > 0.98 && d0[1] > 0.98 && d0[2] > 0.98;
      lignes.push({ o, m, ps, d0, blanc }); } }
  lignes.sort((a, b) => (a.blanc - b.blanc));            // matériaux colorés d'abord
  const S = filtreSel(), vus = [], autres = [];
  for (const L of lignes) {
    const cle = L.o.nom + '/' + L.m, ch = E.coulMat[cle];
    if (S && !L.ps.some(p => S.has(L.o.nom + '/' + p.index))) continue;
    const mx = Math.max(1, L.d0[0], L.d0[1], L.d0[2]), orig = versHex(L.d0.map(v => v / mx));
    // (15/11/2026) la couleur du matériau MULTIPLIE les textures : sur une texture déjà colorée (orange…), une autre couleur
    // donne du noir (orange x bleu). On le signale : mieux vaut alors recolorer la texture.
    const colorees = [...new Set(L.ps.flatMap(p => p.textures || []))].map(n => E.textures[L.o.nom + '/' + n])
      .filter(x => x && !x.info.donnees && (x.info.colores || 0) > 0.3);
    const el = ligneCouleur({ pastille: versHex(L.d0), nom: L.ps.map(p => p.nom).join(', '),
      titre: `matériau ${nomMateriau(L.ps[0])} (${L.o.nom})\npièces : ${L.ps.map(p => p.nom).join(', ')}\ncouleur du jeu : ${L.d0.slice(0, 3).map(v => v.toFixed(2)).join(' / ')}`,
      valeur: ch ? ch.hex : orig, modif: !!ch,
      choisir: hex => { E.coulMat[cle] = { hex, rgb: hex2rgb(hex).map(v => v * mx), nom: nomMateriau(L.ps[0]), acteur: L.o.acteur }; apresMateriau(); },
      remettre: () => { delete E.coulMat[cle]; apresMateriau(); return orig; },
      surNom: () => { E.selPieces.clear(); for (const p of L.ps) E.selPieces.add(L.o.nom + '/' + p.index); majSelection(); },
      cles: L.ps.map(p => L.o.nom + '/' + p.index) });
    if (colorees.length) { const a = document.createElement('span'); a.className = 'alerte'; a.textContent = '⚠';
      a.title = `Texture déjà colorée (${colorees.map(x => x.nom.replace(L.o.nom + '_', '#').replace(/^.*?_(ef_)/, '#')).join(', ')}) : la couleur du `
        + `matériau la MULTIPLIE (orange × bleu = presque noir). Pour changer la teinte, recolore plutôt la texture (bloc Textures) `
        + `et laisse le matériau blanc.`;
      el.insertBefore(a, el.querySelector('input')); }
    (S || !L.blanc || ch ? vus : autres).push(el);
  }
  for (const el of vus) b.appendChild(el);
  if (autres.length) b.appendChild(blocReplie('Matériaux blancs', autres));
  if (!vus.length && !autres.length) b.innerHTML = `<p class="aide">${S ? 'Aucun matériau pour les pièces sélectionnées.' : 'Aucun matériau.'}</p>`;
}
function apresMateriau() { teintesPieces(); dessinerPieces(); }

// ------------------------------------------------------------------ couleurs des sommets et des particules (14/11/2026)
// VRFW : [[recolor]] hue / colorize / mode = "set" avec vertex_colors = [pièces] (G4MG) et particles = true (COLOR_INFO de
// tous les émetteurs de l'objet : VRFW ne choisit pas un émetteur seul). On choisit une couleur : sa teinte H et sa
// saturation C (minimum) ; la luminosité d'origine de chaque sommet / particule est gardée (formule : teinterHSV).
function teinteDe(hex) { const [h, s] = rgb2hsv(...hex2rgb(hex)); return { hex, H: Math.round(h * 10) / 10, C: Math.round(s * 1000) / 1000 }; }
function moyenneSommets(col) {         // couleur moyenne (0..1) et part de sommets colorés
  let n = 0, s = [0, 0, 0], col_ = 0; const pas = Math.max(4, Math.floor(col.length / 4 / 4000) * 4);
  for (let i = 0; i + 3 < col.length; i += pas) { const r = col[i] / 255, g = col[i + 1] / 255, b = col[i + 2] / 255; s[0] += r; s[1] += g; s[2] += b; n++;
    const mx = Math.max(r, g, b); if (mx > 0.05 && (mx - Math.min(r, g, b)) / mx > 0.12) col_++; }
  return { c: n ? s.map(x => x / n) : [1, 1, 1], colores: n ? col_ / n : 0 };
}
function ligneTeinte(nom, titre, pastille, ch, choisir, remettre, surNom, cles) {
  return ligneCouleur({ pastille, nom, titre, valeur: ch ? ch.hex : '#ffffff', modif: !!ch, choisir, remettre: () => { remettre(); return '#ffffff'; }, surNom, cles });
}
function appliquerTeintes() {
  for (const o of E.objets) { if (o.erreur || o.modeleActeur) continue;
    for (const p of o.pieces || []) if (p.vue) { const t = (!E.avant && E.teinteSom[o.nom + '/' + p.index]) || null, tt = t ? [t.H, t.C] : null;
      const avant = p.vue.teinteSom; if (JSON.stringify(avant || null) !== JSON.stringify(tt)) E.vue.teinterSommets(p.vue, tt); }
    const tp = (!E.avant && E.teintePtl[o.nom]) || null;
    for (const v of o.emetteursVue || []) v.teintePtl = tp ? [tp.H, tp.C] : null; }
}
function dessinerTeintes() {
  const b = $('teintes'); if (!b) return; b.innerHTML = '';
  if (!E.tech || E.tech.perso) { b.innerHTML = '<p class="aide">Seulement pour les techniques.</p>'; return; }
  const S = filtreSel();
  // particules : une couleur par objet
  let titreP = false;
  for (const o of E.objets) { if (o.erreur || o.modeleActeur || o.commun) continue;
    const nem = ((o.particules && o.particules.emetteurs) || []).length; if (!nem) continue;
    if (S && ![...S].some(k => k.startsWith(o.nom + '/'))) continue;
    if (!titreP) { const t = document.createElement('div'); t.className = 'sous'; t.textContent = 'Particules'; b.appendChild(t); titreP = true; }
    b.appendChild(ligneTeinte(`${o.nom} : ${nem} émetteur${nem > 1 ? 's' : ''}`, 'Toutes les particules de cet objet (VRFW ne sépare pas les émetteurs)',
      'linear-gradient(45deg,#fff,#888)', E.teintePtl[o.nom],
      hex => { E.teintePtl[o.nom] = teinteDe(hex); appliquerTeintes(); },
      () => { delete E.teintePtl[o.nom]; appliquerTeintes(); },
      () => { E.selPieces.clear(); for (let k = 0; k < nem; k++) E.selPieces.add(o.nom + '/ptl' + k); majSelection(); },
      Array.from({ length: nem }, (_, k) => o.nom + '/ptl' + k))); }
  // sommets : une couleur par pièce (colorées en premier, les blanches repliées)
  const lignes = [];
  for (const o of E.objets) { if (o.erreur || o.modeleActeur || o.commun) continue;
    for (const p of o.pieces || []) { if (!p.vue || !p.vue.col0) continue; const m = moyenneSommets(p.vue.col0); lignes.push({ o, p, m }); } }
  lignes.sort((a, b) => b.m.colores - a.m.colores);
  const vus = [], autres = [];
  for (const L of lignes) {
    const cle = L.o.nom + '/' + L.p.index;
    if (S && !S.has(cle)) continue;
    const el = ligneTeinte(L.p.nom, `${L.o.nom} / pièce ${L.p.index} : ${Math.round(L.m.colores * 100)} % de sommets colorés`,
      versHex(L.m.c), E.teinteSom[cle],
      hex => { E.teinteSom[cle] = Object.assign(teinteDe(hex), { nom: L.p.nom, acteur: L.o.acteur }); appliquerTeintes(); },
      () => { delete E.teinteSom[cle]; appliquerTeintes(); },
      () => { E.selPieces.clear(); E.selPieces.add(cle); majSelection(); }, [cle]);
    (S || L.m.colores > 0.05 || E.teinteSom[cle] ? vus : autres).push(el); }
  if (vus.length || autres.length) { const t = document.createElement('div'); t.className = 'sous'; t.textContent = 'Sommets des pièces'; b.appendChild(t); }
  for (const el of vus) b.appendChild(el);
  if (autres.length) b.appendChild(blocReplie('Sommets blancs ou gris', autres));
  if (!b.children.length) b.innerHTML = `<p class="aide">${S ? 'Rien pour les pièces sélectionnées.' : 'Aucune.'}</p>`;
}



// ------------------------------------------------------------------ AVANT / APRÈS (15/11/2026)
// Montre la technique d'origine (textures, matériaux, sommets, particules ; aperçu et lecteur natif) sans rien perdre :
// E.avant est lu par texAffichee / couleurMat / donneesTexture / appliquerTeintes / optionsActuelles / modifsNatif.
// Un changement de couleur fait revenir à « après ».
function origCanvas(x) {
  if (!x.origCv) { const c = document.createElement('canvas'); c.width = x.orig.width; c.height = x.orig.height; c.getContext('2d').putImageData(x.orig, 0, 0); x.origCv = c; }
  return x.origCv;
}
function texAffichee(x) { return E.avant && x.orig ? origCanvas(x) : x.cur; }
function majBoutonAvant() { const b = $('avant-apres'); if (!b) return; b.classList.toggle('actif', !!E.avant); b.textContent = E.avant ? '◐ Original du jeu' : '◐ Avant / après'; }
function basculerAvant(oui) {
  if (!E.tech) return;
  E.avant = oui === undefined ? !E.avant : !!oui; majBoutonAvant();
  for (const x of Object.values(E.textures)) x.donneesCur = null;
  teintesPieces(); appliquerTeintes(); if (NATIF.actif) { texturesNatif(); optionsNatif(); }
  majRapport(E.avant ? 'Original du jeu affiché (tes changements sont gardés) : « Avant / après » ou la touche A pour les revoir.' : 'Tes couleurs sont revenues.');
}
function quitterAvant() { if (E.avant) basculerAvant(false); }

// ------------------------------------------------------------------ REMPLACER UNE COULEUR PARTOUT (15/11/2026)
// Une teinte (« de », ± tolérance en degrés) devient une autre (« par ») dans toute la technique. Même règle que l'éditeur
// (recolorerPixels, remplir « toute cette teinte ») : nouvelle teinte = teinte cible + écart à la teinte de départ (les nuances
// restent), saturation x min(1,5 ; saturation cible / 0,85), luminosité gardée ; gris / blancs (saturation < 8 %) jamais
// touchés ; bord de la tolérance adouci (70 % plein, puis fondu).
//  - textures (sauf cartes de données) : chaque pixel ;
//  - matériaux : leur couleur (luminosité HDR gardée, comme la liste) ;
//  - sommets : pièces dont la couleur moyenne des sommets a cette teinte -> teinte VRFW (hue « set », colorize 0 : gris gardés) ;
//  - particules : objets dont les couleurs d'émetteurs ont cette teinte -> teinte VRFW de l'objet (tous ses émetteurs).
// Sur les sommets / particules VRFW ne règle que la teinte : la saturation d'origine reste.
// Chaque remplacement est noté dans la « recette » (réutilisable : préréglages) ; « Annuler le dernier » remet l'état d'avant.
const distTeinte = (a, b) => { let d = Math.abs(a - b) % 360; return Math.min(d, 360 - d); };
function opRemplacement(de, vers, tol, cibles) {
  const [h0] = rgb2hsv(...hex2rgb(de)), [H1, S1] = rgb2hsv(...hex2rgb(vers));
  return { de, vers, tol, cibles, h0, H1, k: Math.min(1.5, S1 / 0.85) };
}
function poidsTeinte(h, s, op) {
  if (s < 0.08) return 0; const d = distTeinte(h, op.h0), t = op.tol;
  return d <= t * 0.7 ? 1 : d >= t ? 0 : 1 - (d - t * 0.7) / (t * 0.3);
}
function teinteRemplacee(h, s, v, op) { return hsv2rgb(op.H1 + (h - op.h0), Math.min(1, s * op.k), v); }
function couleursParticules(o) {        // couleurs (0..1) des courbes COLOR_INFO de tous les émetteurs de l'objet
  const out = [];
  for (const d of (o.particules && o.particules.emetteurs) || []) { const C = d.couleur || {};
    for (const c of [C.rgb, C.rgb2]) if (c && c.v) for (const v of c.v) if (Array.isArray(v)) out.push(v); }
  return out;
}
function couleurMoyenneSaturee(cols) {    // moyenne des couleurs colorées (chacune ramenée à luminosité 1)
  let n = 0; const s = [0, 0, 0];
  for (const c of cols) { const mx = Math.max(c[0], c[1], c[2]); if (!(mx > 0)) continue; const [, sa] = rgb2hsv(c[0] / mx, c[1] / mx, c[2] / mx);
    if (sa < 0.12) continue; for (let k = 0; k < 3; k++) s[k] += c[k] / mx; n++; }
  return n ? { c: s.map(x => x / n), part: n / Math.max(1, cols.length) } : null;
}
function listeMateriaux() {             // une entrée par (objet, n° de matériau), comme la liste « Couleurs des matériaux »
  const out = [];
  for (const o of E.objets) { if (o.erreur || o.modeleActeur || o.commun) continue;
    const parMat = new Map();
    for (const p of o.pieces || []) { if (p.materiau === null || p.materiau === undefined) continue;
      if (!parMat.has(p.materiau)) parMat.set(p.materiau, []); parMat.get(p.materiau).push(p); }
    for (const [m, ps] of parMat) { const d0 = (ps[0].jeu && ps[0].jeu.diffuse) || ps[0].couleur || [1, 1, 1, 1];
      out.push({ o, m, ps, d0, cle: o.nom + '/' + m, mx: Math.max(1, d0[0], d0[1], d0[2]) }); } }
  return out;
}
function photoEtat() {                  // pour « Annuler le dernier »
  const tex = {};
  for (const [k, x] of Object.entries(E.textures)) if (x.cur && !x.info.donnees && x.cur.getContext)
    tex[k] = { img: x.cur.getContext('2d').getImageData(0, 0, x.cur.width, x.cur.height), base: x.base, modif: x.modif, moyenne: x.moyenne };
  return { tex, coulMat: JSON.parse(JSON.stringify(E.coulMat)), teinteSom: JSON.parse(JSON.stringify(E.teinteSom)),
    teintePtl: JSON.parse(JSON.stringify(E.teintePtl)), recette: E.recette.length };
}
function remettrePhoto(ph) {
  for (const [k, t] of Object.entries(ph.tex)) { const x = E.textures[k]; if (!x || !x.cur) continue;
    x.cur.getContext('2d').putImageData(t.img, 0, 0); x.base = t.base; x.modif = t.modif; x.moyenne = t.moyenne; x.donneesCur = null; }
  E.coulMat = ph.coulMat; E.teinteSom = ph.teinteSom; E.teintePtl = ph.teintePtl; E.recette.length = ph.recette;
}
function remplacer(op) {                // -> {tex, mat, som, ptl} : nombres d'éléments changés
  const n = { tex: 0, mat: 0, som: 0, ptl: 0 };
  if (op.cibles.tex) for (const x of Object.values(E.textures)) { if (!x.cur || x.info.donnees || !x.cur.getContext) continue;
    const cx = x.cur.getContext('2d'), im = cx.getImageData(0, 0, x.cur.width, x.cur.height), a = im.data; let ch = 0;
    for (let i = 0; i < a.length; i += 4) { if (!a[i + 3]) continue;
      const [h, s, v] = rgb2hsv(a[i] / 255, a[i + 1] / 255, a[i + 2] / 255), w = poidsTeinte(h, s, op); if (!(w > 0)) continue;
      const c = teinteRemplacee(h, s, v, op); for (let j = 0; j < 3; j++) a[i + j] = a[i + j] * (1 - w) + c[j] * 255 * w; ch++; }
    if (ch) { cx.putImageData(im, 0, 0); x.base = im; x.modif = true; x.moyenne = moyenne(im); x.donneesCur = null; n.tex++; } }
  if (E.tech && !E.tech.perso) {
    if (op.cibles.mat) for (const L of listeMateriaux()) {
      const ch = E.coulMat[L.cle], c = ch ? hex2rgb(ch.hex) : L.d0.slice(0, 3).map(v => v / L.mx);
      const [h, s, v] = rgb2hsv(c[0], c[1], c[2]), w = poidsTeinte(h, s, op); if (!(w > 0.5)) continue;
      const nv = teinteRemplacee(h, s, v, op), hex = versHex(nv);
      E.coulMat[L.cle] = { hex, rgb: hex2rgb(hex).map(x => x * L.mx), nom: nomMateriau(L.ps[0]), acteur: L.o.acteur }; n.mat++; }
    if (op.cibles.som) for (const o of E.objets) { if (o.erreur || o.modeleActeur || o.commun) continue;
      for (const p of o.pieces || []) { if (!p.vue || !p.vue.col0) continue; const cle = o.nom + '/' + p.index, t = E.teinteSom[cle];
        let h; if (t) h = t.H; else { const m = moyenneSommets(p.vue.col0); if (m.colores < 0.05) continue; const [hh, ss] = rgb2hsv(...m.c); if (ss < 0.08) continue; h = hh; }
        if (!(poidsTeinte(h, 1, op) > 0.5)) continue;
        const H = ((op.H1 + (h - op.h0)) % 360 + 360) % 360;
        E.teinteSom[cle] = { hex: versHex(hsv2rgb(H, 0.85, 1)), H: Math.round(H * 10) / 10, C: 0, nom: p.nom, acteur: o.acteur }; n.som++; } }
    if (op.cibles.ptl) for (const o of E.objets) { if (o.erreur || o.modeleActeur || o.commun) continue;
      const t = E.teintePtl[o.nom]; let h;
      if (t) h = t.H; else { const m = couleurMoyenneSaturee(couleursParticules(o)); if (!m) continue; h = rgb2hsv(...m.c)[0]; }
      if (!(poidsTeinte(h, 1, op) > 0.5)) continue;
      const H = ((op.H1 + (h - op.h0)) % 360 + 360) % 360;
      E.teintePtl[o.nom] = { hex: versHex(hsv2rgb(H, 0.85, 1)), H: Math.round(H * 10) / 10, C: 0 }; n.ptl++; }
  }
  return n;
}
function apresTout() { apresRetouche(); appliquerTeintes(); dessinerMateriaux(); dessinerTeintes(); dessinerRecette(); paletteTech(); majCompteurs(); }
function ciblesChoisies() { return { tex: $('rc-tex').checked, mat: $('rc-mat').checked, som: $('rc-som').checked, ptl: $('rc-ptl').checked }; }
function texteCompte(n) {
  const l = [[n.tex, 'texture'], [n.mat, 'matériau'], [n.som, 'pièce (sommets)', 'pièces (sommets)'], [n.ptl, 'objet (particules)', 'objets (particules)']]
    .filter(a => a[0]).map(([k, s, p]) => `${k} ${k > 1 ? (p || s + 's') : s}`);
  return l.length ? l.join(', ') : 'rien (aucune couleur proche : augmente la tolérance ou choisis une couleur dans la palette)';
}
function lancerRemplacement() {
  if (!E.tech) return majRapport('Ouvre d\'abord une technique.');
  quitterAvant();
  const op = opRemplacement($('rc-de').value, $('rc-vers').value, +$('rc-tol').value, ciblesChoisies());
  const ph = photoEtat(), n = remplacer(op);
  if (!n.tex && !n.mat && !n.som && !n.ptl) { majRapport('Remplacement : ' + texteCompte(n) + '.'); return; }
  E.pileRc.push(ph); if (E.pileRc.length > 8) E.pileRc.shift();
  E.recette.push({ de: op.de, vers: op.vers, tol: op.tol, cibles: op.cibles });
  apresTout(); majRapport('Remplacé : ' + texteCompte(n) + '.');
}
function annulerRemplacement() {
  const ph = E.pileRc.pop(); if (!ph) return majRapport('Rien à annuler.');
  quitterAvant(); remettrePhoto(ph); apresTout(); majRapport('Dernier remplacement annulé.');
}
function dessinerRecette() {
  const b = $('rc-recette'); if (!b) return; b.innerHTML = '';
  if ($('cpt-rc')) $('cpt-rc').textContent = E.recette && E.recette.length ? E.recette.length + ' fait' + (E.recette.length > 1 ? 's' : '') : '';
  for (const r of E.recette || []) { const d = document.createElement('div'); d.className = 'rc-op';
    d.innerHTML = `<span class="pastille" style="background:${r.de}"></span>→<span class="pastille" style="background:${r.vers}"></span><span class="aide">± ${r.tol}°</span>`;
    b.appendChild(d); }
}
// couleurs principales de la technique (état actuel) : 24 cases de 15° de teinte, pondérées (textures réduites à 32 x 32,
// matériaux colorés, sommets colorés, particules) ; clic -> couleur « de »
function couleursPrincipales(n) {        // (15/11/2026) les n premières couleurs de la palette (hub : bandes de la carte)
  const b = document.createElement('div'); paletteTech(b); return [...b.querySelectorAll('.rc-case')].slice(0, n).map(x => x.dataset.hex);
}
function paletteTech(cible) {
  const box = cible || $('rc-palette'); if (!box) return; box.innerHTML = ''; if (!E.tech) return;
  const cases = Array.from({ length: 24 }, () => ({ w: 0, c: [0, 0, 0], src: new Set() }));
  const ajout = (r, g, b, w, src) => { const [h, s, v] = rgb2hsv(r, g, b); if (s < 0.15 || v < 0.08 || !(w > 0)) return;
    const C = cases[Math.floor(h / 15) % 24], ww = w * s; C.w += ww; C.c[0] += r / v * ww; C.c[1] += g / v * ww; C.c[2] += b / v * ww; C.src.add(src); };
  const pt = document.createElement('canvas'); pt.width = pt.height = 32; const px = pt.getContext('2d', { willReadFrequently: true });
  for (const x of Object.values(E.textures)) { if (!x.cur || x.info.donnees) continue;
    px.clearRect(0, 0, 32, 32); px.drawImage(x.cur, 0, 0, 32, 32); const a = px.getImageData(0, 0, 32, 32).data;
    for (let i = 0; i < a.length; i += 4) ajout(a[i] / 255, a[i + 1] / 255, a[i + 2] / 255, a[i + 3] / 255 / 1024 * 3, 'textures'); }
  if (!E.tech.perso) {
    for (const L of listeMateriaux()) { const ch = E.coulMat[L.cle], c = ch ? hex2rgb(ch.hex) : L.d0.slice(0, 3).map(v => v / L.mx); ajout(c[0], c[1], c[2], 1, 'matériaux'); }
    for (const o of E.objets) { if (o.erreur || o.modeleActeur || o.commun) continue;
      for (const p of o.pieces || []) { if (!p.vue || !p.vue.col0) continue; const t = E.teinteSom[o.nom + '/' + p.index];
        if (t) { const c = hsv2rgb(t.H, 0.85, 1); ajout(c[0], c[1], c[2], 0.6, 'sommets'); continue; }
        const m = moyenneSommets(p.vue.col0); if (m.colores > 0.05) ajout(m.c[0], m.c[1], m.c[2], 0.6 * m.colores, 'sommets'); }
      const t = E.teintePtl[o.nom];
      if (t) { const c = hsv2rgb(t.H, 0.85, 1); ajout(c[0], c[1], c[2], 1, 'particules'); }
      else { const m = couleurMoyenneSaturee(couleursParticules(o)); if (m) ajout(m.c[0], m.c[1], m.c[2], 1, 'particules'); } } }
  const tot = cases.reduce((s, C) => s + C.w, 0) || 1;
  const garder = cases.map((C, i) => ({ C, i })).filter(e => e.C.w / tot > 0.025).sort((a, b) => b.C.w - a.C.w).slice(0, 10);
  if (!garder.length) { box.innerHTML = '<span class="aide">Aucune couleur vive.</span>'; return; }
  for (const { C } of garder) { const c = C.c.map(v => v / C.w), mx = Math.max(...c, 1e-6), hex = versHex(c.map(v => v / mx));
    const b = document.createElement('button'); b.className = 'rc-case'; b.style.background = hex; b.dataset.hex = hex;
    b.title = `${hex} · ${Math.round(C.w / tot * 100)} % · ${[...C.src].join(', ')}\n(clic : remplacer cette couleur)`;
    b.onclick = () => { $('rc-de').value = hex; };
    box.appendChild(b); }
}

// ------------------------------------------------------------------ PRÉRÉGLAGES (15/11/2026)
// Un préréglage = la recette (remplacements dans l'ordre) + aura du ballon, couleur du tir, traînée, lueurs. Gardé par le
// serveur (prereglages.json) ; s'applique à n'importe quelle technique (les remplacements cherchent les teintes, pas les pièces).
let PREREG = [];
async function chargerPrereglages() {
  try { PREREG = (await api('/api/prereglages')).liste || []; } catch (e) { PREREG = []; }
  const s = $('pr-liste'); if (!s) return; s.innerHTML = '';
  if (!PREREG.length) { const o = document.createElement('option'); o.value = ''; o.textContent = '(aucun préréglage)'; s.appendChild(o); return; }
  for (const p of PREREG) { const o = document.createElement('option'); o.value = p.nom; o.textContent = `${p.nom} (${(p.recette || []).length} remplacement${(p.recette || []).length > 1 ? 's' : ''})`; s.appendChild(o); }
}
function premiereAura() {
  for (const cb of document.querySelectorAll('[data-aura]')) if (cb.checked) return document.querySelector(`[data-aura-c="${CSS.escape(cb.dataset.aura)}"]`).value;
  return null;
}
async function garderPrereglage() {
  const nom = $('pr-nom').value.trim(); if (!nom) return majRapport('Donne un nom au préréglage.');
  if (!E.tech) return majRapport('Ouvre d’abord une technique.');
  if (!E.recette.length && !premiereAura() && $('f-couleur').value === '' && !$('f-trainee').value && !$('lueurs-on').checked)
    return majRapport('Rien à garder : fais d\'abord un remplacement (ou choisis une aura, une couleur de tir, une traînée).');
  const p = { nom, recette: E.recette, aura: premiereAura(), couleur_tir: $('f-couleur').value, trainee: $('f-trainee').value, trainee_el: $('f-trainee-el').value,
    lueurs: $('lueurs-on').checked ? +$('lueurs-h').value : null };
  const r = await api('/api/prereglages', { action: 'garder', prereglage: p });
  if (!r.ok) return majRapport('Préréglage non gardé : ' + (r.erreur || '?'));
  await chargerPrereglages(); $('pr-liste').value = nom; majRapport(`Préréglage « ${nom} » gardé.`);
}
async function supprimerPrereglage() {
  const nom = $('pr-liste').value; if (!nom) return;
  if (!confirm(`Supprimer le préréglage « ${nom} » ?`)) return;
  await api('/api/prereglages', { action: 'supprimer', nom }); await chargerPrereglages(); majRapport(`Préréglage « ${nom} » supprimé.`);
}
function appliquerPrereglage() {
  const p = PREREG.find(x => x.nom === $('pr-liste').value); if (!p) return majRapport('Choisis un préréglage.');
  if (!E.tech) return majRapport('Ouvre d\'abord une technique.');
  quitterAvant();
  const ph = photoEtat(), tot = { tex: 0, mat: 0, som: 0, ptl: 0 };
  for (const r of p.recette || []) { const n = remplacer(opRemplacement(r.de, r.vers, r.tol, r.cibles)); for (const k in tot) tot[k] += n[k]; E.recette.push(r); }
  E.pileRc.push(ph); if (E.pileRc.length > 8) E.pileRc.shift();
  if (!E.tech.perso) {
    if (p.aura) document.querySelectorAll('[data-aura]').forEach(cb => { cb.checked = true; document.querySelector(`[data-aura-c="${CSS.escape(cb.dataset.aura)}"]`).value = p.aura; });
    if (p.couleur_tir !== undefined) $('f-couleur').value = p.couleur_tir;
    if (p.trainee !== undefined) $('f-trainee').value = p.trainee;
    if (p.trainee_el) $('f-trainee-el').value = p.trainee_el;
    if (p.lueurs !== null && p.lueurs !== undefined) { $('lueurs-on').checked = true; $('lueurs-h').value = p.lueurs; $('lueurs-h').dispatchEvent(new Event('input')); $('lueurs-on').dispatchEvent(new Event('change')); }
  }
  apresTout(); majRapport(`Préréglage « ${p.nom} » appliqué : ${texteCompte(tot)}.`);
}

// ------------------------------------------------------------------ PROJET : sauvegarde automatique et reprise (15/11/2026)
// Toutes les 2 s, si quelque chose a changé : textures retouchées (PNG), couleurs de matériaux, teintes, recette, auras et
// champs du formulaire -> serveur (projets/<onglet>_<code>.json). À la réouverture de la technique : « Reprendre » ou
// (plus de question « Reprendre / Repartir de zéro » depuis le 15/11 au soir : chaque création a son projet, « Continuer » au hub).
const CHAMPS_PROJET = ['f-nom', 'f-desc', 'f-couleur', 'f-trainee', 'f-trainee-el', 'f-prix', 'f-ban', 'f-ban-c', 'f-ban-o', 'lueurs-on', 'lueurs-h', 'garder-or', 'garder-blanc', 'p-nom', 'p-desc', 'p-prix'];
// (15/11/2026) UN PROJET PAR CRÉATION (avant : un par esprit / technique de départ, et une nouvelle version remplaçait l'ancienne).
// Ouvrir depuis un onglet = nouvelle création (fichier neuf, créé au 1er changement) ; « Continuer » (hub) = ce projet-là.
function nouvelleCleProjet(onglet, code) { const d = new Date(), z = n => String(n).padStart(2, '0');
  return `${onglet || 'techniques'}_${code}_${d.getFullYear()}${z(d.getMonth() + 1)}${z(d.getDate())}_${z(d.getHours())}${z(d.getMinutes())}${z(d.getSeconds())}`; }
const cleProjet = () => E.tech ? (E.projet || (E.tech.onglet || 'techniques') + '_' + E.tech.code) : null;
function champsProjet() {
  const c = {}; for (const id of CHAMPS_PROJET) { const el = $(id); if (el) c[id] = el.type === 'checkbox' ? el.checked : el.value; }
  const auras = {}; document.querySelectorAll('[data-aura]').forEach(cb => { auras[cb.dataset.aura] = [cb.checked, document.querySelector(`[data-aura-c="${CSS.escape(cb.dataset.aura)}"]`).value]; });
  return { c, auras };
}
function signatureProjet() {
  if (!E.tech) return null;
  return JSON.stringify([E.rev || 0, E.coulMat, E.teinteSom, E.teintePtl, E.recette, champsProjet()]);
}
async function sauverProjet() {
  // (15/11/2026) jamais pendant le chargement d'une technique : l'état à moitié chargé écrasait le projet (avant la question « Reprendre »)
  if (!E.tech || E.reprise || E.chargement || NATIF.sauveProjet) return;
  // (15/11/2026) projet repris sans image de l'aperçu : une sauvegarde de plus pour la faire, dès que l'animation est chargée
  const sig = signatureProjet(); if (sig === E.sigProjet && !(E.vignetteManque && E.lecteur)) return;
  const tex = {}; for (const [k, x] of Object.entries(E.textures)) if (x.modif && x.cur && x.cur.toDataURL) tex[k] = x.cur.toDataURL('image/png');
  const { c, auras } = champsProjet();
  if (!E.vignette || !E.vignetteT || performance.now() - E.vignetteT > 20000) { NATIF.sauveProjet = true;
    try { const v = await faireVignette(); if (v) { E.vignette = v; E.vignetteT = performance.now(); } } finally { NATIF.sauveProjet = false; } }
  const etat = { version: 1, code: E.tech.code, onglet: E.tech.onglet, nom: E.tech.nom, date: new Date().toISOString(), textures: tex, apercu: couleursPrincipales(4), vignette: E.vignette || null,
    coulMat: E.coulMat, teinteSom: E.teinteSom, teintePtl: E.teintePtl, recette: E.recette, champs: c, auras,
    calques: window.atelierEtat ? atelierEtat() : {},           // (15/11/2026) calques de l'atelier de retouche
    cree: E.cree || null };                                     // (22/11) la création faite depuis ce projet (Mes créations)
  NATIF.sauveProjet = true;
  try { const r = await api('/api/projet', { action: 'garder', cle: cleProjet(), etat }); if (r.ok) { E.sigProjet = sig; if (etat.vignette) E.vignetteManque = false; } }
  catch (e) { /* serveur absent : on réessaiera */ } finally { NATIF.sauveProjet = false; }
}
async function verifierProjet() {
  const cle = cleProjet(); if (!cle) return;
  let r = null; try { r = await api('/api/projet?cle=' + encodeURIComponent(cle)); } catch (e) { return; }
  if (!r || !r.existe || cleProjet() !== cle) return;
  const e = r.etat, nT = Object.keys(e.textures || {}).length, nM = Object.keys(e.coulMat || {}).length,
    nS = Object.keys(e.teinteSom || {}).length + Object.keys(e.teintePtl || {}).length, nR = (e.recette || []).length;
  if (!nT && !nM && !nS && !nR) return;
  if (E.repriseCle === cle) { E.repriseCle = null; E.chargement = true; try { await reprendreProjet(e); } finally { E.sigProjet = signatureProjet(); E.chargement = false; } return; }
  // (15/11/2026) plus de question « Reprendre / Repartir de zéro » : elle bloquait la sauvegarde tant qu'on n'y répondait pas
  // (cachée par le mode dessin : un Pégase noir n'a jamais été gardé). Nouvelle création = nouveau projet ; les autres restent au hub.
}
async function reprendreProjet(e) {
  E.cree = e.cree || null;                        // (22/11) lien projet -> création gardé
  majRapport('Reprise du projet…');
  for (const [k, url] of Object.entries(e.textures || {})) { const x = E.textures[k]; if (!x || !x.cur) continue;
    try { const im = await chargerImage(url), cx = x.cur.getContext('2d');
      cx.clearRect(0, 0, x.cur.width, x.cur.height); cx.drawImage(im, 0, 0, x.cur.width, x.cur.height);
      x.base = cx.getImageData(0, 0, x.cur.width, x.cur.height); x.modif = true; x.moyenne = moyenne(x.base); x.donneesCur = null; } catch (er) { /* texture illisible */ } }
  E.coulMat = e.coulMat || {}; E.teinteSom = e.teinteSom || {}; E.teintePtl = e.teintePtl || {}; E.recette = e.recette || []; E.pileRc = [];
  E.vignette = e.vignette || null; E.vignetteT = e.vignette ? performance.now() : 0; E.vignetteManque = !e.vignette;
  for (const [id, v] of Object.entries(e.champs || {})) { const el = $(id); if (!el) continue; if (el.type === 'checkbox') el.checked = v; else el.value = v; }
  for (const [n, [oui, hex]] of Object.entries(e.auras || {})) { const cb = document.querySelector(`[data-aura="${CSS.escape(n)}"]`), c = document.querySelector(`[data-aura-c="${CSS.escape(n)}"]`);
    if (cb) cb.checked = oui; if (c) c.value = hex; }
  if ($('lueurs-h')) { $('lueurs-h').dispatchEvent(new Event('input')); $('lueurs-on').dispatchEvent(new Event('change')); }
  if ($('mode')) $('mode').dispatchEvent(new Event('change'));
  apresTout(); majRapport('Projet repris : tu continues là où tu t\'étais arrêté.');
  if (window.zonesPreparer) try { zonesPreparer(); } catch (e) { console.error('zones', e); }
  if (e.calques && window.atelierRestaurer) try { await atelierRestaurer(e.calques); } catch (er) { console.error('calques', er); }
}

// ------------------------------------------------------------------ HUB « MES CRÉATIONS » (15/11/2026)
// Premier onglet : projets en cours (sauvegarde automatique, projets/*.json), mods créés (sortie/MesTechniques,
// sortie/MesEsprits ; installé = même fichier dans <jeu>/mods) et préréglages. « Reprendre » ouvre la technique / l'esprit
// et recharge le travail sans poser la question ; « Modifier » (mod créé) reprend le projet de la même technique de départ.
const HUB = { projets: [], creations: [] };
const echapper = s => String(s ?? '').replace(/[&<>"]/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
function dateCourte(d) { if (!d) return ''; const x = typeof d === 'number' ? new Date(d * 1000) : new Date(d);
  return x.toLocaleString('fr-FR', { day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit' }).replace(' ', ' · '); }
function bandes(c) { const l = (c || []).length ? c : ['#3a3f4b', '#2c313b', '#232730'];
  return l.map(x => `<span style="background:${echapper(x)}"></span>`).join(''); }
async function chargerHub() {
  $('hub-etat').textContent = 'Lecture…';
  try { const r = await api('/api/projets'); HUB.projets = r.projets || []; HUB.creations = r.creations || []; $('hub-etat').textContent = ''; }
  catch (e) { $('hub-etat').textContent = 'Lecture impossible : ' + e.message; }
  await chargerPrereglages(); await chargerMenusJeu(); dessinerHub();
}
// VIGNETTE (15/11/2026) : une image de l'aperçu (vue3d._dessinerUne, lue dans la même tâche que le dessin) à l'image où
// l'effet est le plus présent (somme des visibilités de chronologie(), même règle que « Localiser »), caméra du jeu, en
// 16:9, JPEG 640 px. Refaite au plus toutes les 20 s quand le projet change ; gardée avec le projet (etat.vignette).
async function faireVignette() {
  const V = E.vue; if (!V || !E.tech || E.avant || !V.cv || !V.cv.width) return null;
  let f = null;
  // animation pas lancée : posée le temps de la vignette (mêmes visibilités qu'activerAnimation(true)), puis tout est remis
  const anim0 = V.lecteur, vis0 = V.pieces.map(p => p.visible);
  if (!V.lecteur && E.lecteur) { V.lecteur = E.lecteur;
    for (const p of V.pieces) p.visible = p.terrain ? $('l-terrain').checked : !p.versionCachee; }
  let candidats = [];
  if (E.lecteur) { try { const C = await chronologie(); if (C) {
    const sc = []; for (let i = 0; i < C.n; i++) { let t = 0; for (const v of C.vis.values()) t += v[i]; sc.push([t, i * C.pas]); }
    sc.sort((a, b) => b[0] - a[0]);
    for (const [, fr] of sc) { if (candidats.every(c => Math.abs(c - fr) > 20)) candidats.push(fr); if (candidats.length >= 8) break; }
    f = candidats[0] ?? null; } } catch (e) { f = null; } }
  const f0 = V.image, fil = V.fil, sel = V.pieces.map(p => p.sel), ec = V.eclat;
  V.fil = false; V.pieces.forEach(p => { p.sel = false; }); V.eclat = null;
  try {
    // (15/11/2026) parmi les 8 images les plus chargées (écartées de 20), la plus colorée et la moins « flash » (pixels presque
    // blancs ou noirs comptés à part) : petit rendu 64 x 36 de chacune
    if (candidats.length > 1) { const p = document.createElement('canvas'); p.width = 64; p.height = 36; const px = p.getContext('2d', { willReadFrequently: true });
      let best = -1;
      for (const fr of candidats) { V._dessinerUne(fr); px.clearRect(0, 0, 64, 36); px.drawImage(V.cv, 0, 0, 64, 36);
        const a = px.getImageData(0, 0, 64, 36).data; let s = 0, blanc = 0, noir = 0;
        for (let i = 0; i < a.length; i += 4) { const mx = Math.max(a[i], a[i + 1], a[i + 2]), mn = Math.min(a[i], a[i + 1], a[i + 2]);
          if (mn > 225) blanc++; else if (mx < 25) noir++; else s += (mx - mn) / 255; }
        const n = a.length / 4, note = s / n - 1.5 * blanc / n - 0.5 * noir / n;
        if (note > best) { best = note; f = fr; } } }
    V._dessinerUne(f !== null ? f : V.image);
    const W = 640, H = 360, c = document.createElement('canvas'); c.width = W; c.height = H; const x = c.getContext('2d');
    x.fillStyle = '#0b0d12'; x.fillRect(0, 0, W, H);
    const sw = V.cv.width, sh = V.cv.height, r = Math.min(sw / W, sh / H), cw = W * r, ch = H * r;
    x.drawImage(V.cv, (sw - cw) / 2, (sh - ch) / 2, cw, ch, 0, 0, W, H);
    return c.toDataURL('image/jpeg', 0.82);
  } catch (e) { return null; }
  finally { V.fil = fil; V.pieces.forEach((p, k) => { p.sel = sel[k]; p.visible = vis0[k]; }); V.eclat = ec; V.image = f0; V.lecteur = anim0; }
}
function dessinerHub() {
  const q = ($('hub-cherche').value || '').toLowerCase().normalize('NFD').replace(/[\u0300-\u036f]/g, '');
  const ok = (...t) => !q || t.join(' ').toLowerCase().normalize('NFD').replace(/[\u0300-\u036f]/g, '').includes(q);
  const genre = o => o === 'esprits' || o === 'esprit' ? 'Esprit guerrier' : o === 'totems' || o === 'totem' ? 'Totem' : o === 'maillots' ? 'Maillot'
    : o === 'tenues' ? 'Tenue' : o === 'armures' ? 'Armure' : o === 'personnages' ? 'Personnage' : o === 'objets' ? 'Objet' : 'Technique';
  const couleursBande = c => (c && c.length ? c : ['#3a3f4b', '#2c313b']).map(x => `<span style="background:${echapper(x)}"></span>`).join('');
  const image = (v, titre, couleurs, estTexture) => v
    ? `<img src="${echapper(v)}" alt="" loading="lazy">`
    : `<div class="hub-couv" style="background:linear-gradient(135deg, ${echapper((couleurs || [])[0] || '#2a3040')}, ${echapper((couleurs || [])[1] || (couleurs || [])[0] || '#151821')} 70%, #0e1016)">${echapper((titre || '?').trim().charAt(0).toUpperCase())}</div>`;
  const carte = ({ onglet, vignette, estTexture, badge, badgeCl, titre, sousImg, couleurs, sous, tags, boutons, lecture }) => {
    const d = document.createElement('div'); d.className = 'hub-carte g-' + (onglet || 'techniques');
    const G = ONGLETS_HUB.find(x => x.o === (onglet || 'techniques')) || ONGLETS_HUB[0];     // (15/11) carte de joueur du jeu
    d.innerHTML = `<div class="hub-image${estTexture ? ' texture' : ''}">${image(vignette, titre, couleurs, estTexture)}
        <span class="hub-badge ${badgeCl}">${badge}</span>${lecture ? '<span class="hub-lecture">▶</span>' : ''}
        <span class="jm-carte-ico">${iconeJeu(G.ic, 28)}</span><span class="jm-tag">${G.tag}</span>
        <div class="hub-sur-img"><div class="hub-titre">${echapper(titre)}</div><div class="hub-genre">${sousImg}</div></div></div>
      <div class="hub-couleurs">${couleursBande(couleurs)}</div>
      <div class="hub-corps"><div class="hub-sous">${sous}</div>${tags ? `<div class="hub-tags">${tags}</div>` : ''}<div class="hub-boutons">${boutons}</div></div>`;
    return d;
  };
  dessinerMenuJeu();                // (15/11/2026) en-tête, bannières, tuiles et filtres façon menus du jeu
  // chiffres
  const nAttente = HUB.creations.filter(c => c.attente).length, nFinies = HUB.creations.length - nAttente;    // (22/11)
  $('hub-stats').innerHTML = [[HUB.projets.length, 'à continuer'], [nAttente, 'en attente de stats'], [nFinies, 'terminées'], [PREREG.length, 'préréglages']]
    .map(([n, t]) => `<div class="hub-stat"><b>${n}</b><span>${t}</span></div>`).join('');
  $('hub-n-projets').textContent = HUB.projets.length; $('hub-n-creations').textContent = nFinies; $('hub-n-prereglages').textContent = PREREG.length;
  // à continuer
  const g = $('hub-projets'); g.innerHTML = '';
  const pl = HUB.projets.filter(p => ok(p.titre, p.base, p.code) && (!HUB.filtre || p.onglet === HUB.filtre));
  if (!pl.length) g.innerHTML = `<div class="hub-vide"><b>${HUB.projets.length ? 'Aucun projet ne correspond' : 'Rien en cours'}</b>${HUB.projets.length ? 'Essaie un autre mot.' : 'Ouvre une technique et change ses couleurs : ton travail apparaîtra ici tout seul.'}</div>`;
  for (const p of pl) {
    const tags = [[p.textures, 'texture'], [p.materiaux, 'matériau'], [p.teintes, 'teinte'], [p.remplacements, 'remplacement']].filter(x => x[0])
      .map(([n, m]) => `<span>${n} ${m}${n > 1 ? (m === 'matériau' ? 'x' : 's') : ''}</span>`).join('');
    const d = carte({ onglet: p.onglet, vignette: p.vignette, estTexture: p.vignetteTexture, badge: 'En cours', badgeCl: 'encours', titre: p.titre, couleurs: p.couleurs, lecture: true,
      sousImg: `${genre(p.onglet)} · d'après ${echapper(p.base)}`, sous: `Modifié le ${dateCourte(p.date)}`, tags: tags || '<span>rien de changé</span>',
      boutons: '<button class="primaire" data-a="reprendre">Continuer</button><button data-a="renommer" title="Renommer">✎</button><button data-a="supprimer" title="Retirer de la liste (rangé dans projets/corbeille)">🗑</button>' });
    d.querySelector('.hub-image').onclick = () => reprendreDepuisHub(p);
    d.querySelector('[data-a="reprendre"]').onclick = () => reprendreDepuisHub(p);
    d.querySelector('[data-a="renommer"]').onclick = async () => { const t = prompt('Nouveau nom :', p.titre); if (!t || !t.trim()) return;
      await api('/api/projet', { action: 'renommer', cle: p.cle, titre: t.trim() }); chargerHub(); };
    d.querySelector('[data-a="supprimer"]').onclick = async () => {
      if (!confirm(`Retirer « ${p.titre} » de la liste ?\nRien n'est effacé : le projet est rangé dans AtelierCouleurs/projets/corbeille.`)) return;
      await api('/api/projet', { action: 'supprimer', cle: p.cle }); chargerHub(); };
    g.appendChild(d); }
  // terminées
  const l = $('hub-creations'); l.innerHTML = '';
  const la = $('hub-attente'); la.innerHTML = '';          // (22/11) en attente de stats
  $('jm-s-attente').style.display = la.style.display = HUB.creations.some(c => c.attente) ? '' : 'none';
  const cr = HUB.creations.filter(c => ok(c.nom, c.base, c.code, c.nom_base) && (!HUB.filtre || c.onglet === HUB.filtre));
  if (!cr.length) l.innerHTML = `<div class="hub-vide"><b>${HUB.creations.length ? 'Aucune création ne correspond' : 'Aucun mod créé pour l’instant'}</b>${HUB.creations.length ? 'Essaie un autre mot.' : 'Quand une technique te plaît : « Créer le mod » dans le panneau de droite.'}</div>`;
  for (const c of cr) {
    const proj = projetDe(c);
    // (22/11) joueur sans projet à lui : son portrait recoloré (celui des cartes du jeu)
    const vign = c.vignette || (proj && !proj.vignetteTexture ? proj.vignette : null) || (proj && proj.vignette)
      || (c.mod === 'MesPersonnages' && c.code ? '/api/portrait?code=' + encodeURIComponent(c.code) : null);
    const st = c.jeuSeul ? ['Dans le jeu', 'oui'] : c.installe ? ['Installé', 'oui'] : ['Pas installé', 'non'];
    const d = carte({ onglet: c.onglet, vignette: vign, estTexture: !c.vignette && proj && proj.vignetteTexture, badge: st[0], badgeCl: st[1], titre: c.nom, couleurs: proj && proj.couleurs, lecture: true,
      sousImg: `${genre(c.genre)} · copie de ${echapper(c.nom_base || c.base)}`,
      sous: `<span class="avance">Code ${echapper(c.code)} · </span>${dateCourte(c.date)}${c.jeuSeul ? '<br>Plus dans la sortie de l’Atelier, mais toujours dans le jeu.' : ''}`,
      boutons: (c.attente ? '<button class="primaire" data-a="stats" title="Puissance, PT, élément… (ou garder ceux de l’original)">Régler les stats</button>' : '')
        + `<button${c.attente ? '' : ' class="primaire"'} data-a="modifier" title="${proj ? 'Reprendre le projet qui a servi à la créer' : 'Projet d’origine introuvable : rouvre la technique de départ'}">Modifier</button>`
        + (!c.attente && aDesStats(c) ? '<button data-a="stats" title="Changer ses valeurs (puissance, PT, élément…)">Stats</button>' : '')
        + (c.mod === 'MesPersonnages' && c.cle ? `<button data-a="coups" title="Choisir ses techniques et son esprit guerrier">Techniques${c.nb_coups ? ' (' + c.nb_coups + ')' : ''}</button>` : '')
        + (c.mod === 'MesEsprits' && c.genre === 'esprit' ? `<button data-a="liee" title="${c.liee ? 'Technique liée : ' + echapper(c.liee) : 'Choisir la technique de cet esprit guerrier'}">Technique liée${c.liee ? ' ✓' : ''}</button>` : '')
        // (22/11, demande de muku) « Installer » seulement dans Terminées (pas en attente de stats) ; « Supprimer » dans Terminées
        + (c.installe || c.attente ? '' : '<button data-a="installer" title="Copier dans le mod du jeu (sauvegarde avant ; ce qui y est déjà reste)">Installer</button>')
        + (c.attente ? '' : '<button data-a="supprimer" class="supprimer" title="Retirer cette création (ses fichiers sont rangés à part, récupérables)">Supprimer</button>') });
    const bc = d.querySelector('[data-a="coups"]'); if (bc) bc.onclick = () => ouvrirCoups(c);
    const bs = d.querySelector('[data-a="stats"]'); if (bs) bs.onclick = () => ouvrirStats(c);
    const bx = d.querySelector('[data-a="supprimer"]'); if (bx) bx.onclick = () => supprimerCreation(c);
    const bl = d.querySelector('[data-a="liee"]'); if (bl) bl.onclick = () => ouvrirTechniqueLiee(c);
    const ouvrirC = c.mod === 'MesMaillots' && c.maillot ? async () => { window.changerOnglet('maillots'); await mmOuvrir(c.maillot); }   // (15/11) un de mes maillots
      : () => proj ? reprendreDepuisHub(proj) : ouvrirDepuisHub(c.onglet, c.base, false);
    d.querySelector('.hub-image').onclick = ouvrirC; d.querySelector('[data-a="modifier"]').onclick = ouvrirC;
    const bi = d.querySelector('[data-a="installer"]');
    if (bi) bi.onclick = async () => {
      await installer(c.mod);              // (21/11) créations du jeu qui seraient retirées : demandé par installer()
      $('hub-etat').textContent = $('rapport').textContent.split('\n')[0]; chargerHub(); };
    (c.attente ? la : l).appendChild(d); }
  // préréglages
  const pr = $('hub-prereglages'); pr.innerHTML = '';
  if (!PREREG.length) pr.innerHTML = '<div class="hub-vide"><b>Aucun préréglage</b>Fais un remplacement de couleur dans une technique, puis « Garder ».</div>';
  for (const p of PREREG.filter(p => ok(p.nom))) { const r = p.recette || [], s = document.createElement('span'); s.className = 'hub-puce';
    s.innerHTML = r.slice(0, 3).map(x => `<i style="background:${echapper(x.de)}"></i>→<i style="background:${echapper(x.vers)}"></i>`).join('<span style="width:6px"></span>')
      + ` <b>${echapper(p.nom)}</b> <small>· ${r.length} remplacement${r.length > 1 ? 's' : ''}</small>`;
    pr.appendChild(s); }
}
async function ouvrirDepuisHub(onglet, code, reprise) {
  window.changerOnglet(onglet || 'techniques');
  if (reprise) E.repriseAuto = reprise;
  try { await ouvrir(code); } catch (e) { $('titre-tech').textContent = 'Erreur : ' + e.message; }
}
function reprendreDepuisHub(p) { return ouvrirDepuisHub(p.onglet, p.code, p.cle); }

// ------------------------------------------------------------------ auras
function dessinerAuras() {
  const b = $('auras'); b.innerHTML = '';
  if (!E.tech.auras || !E.tech.auras.length) { b.innerHTML = '<p class="aide">Aucune aura dans cette cinématique.</p>'; return; }
  for (const a of E.tech.auras) {
    const d = document.createElement('div'); d.className = 'aura';
    // (17/11/2026) aura recolorée par un mod (VRFW [[recolor]] aura / copy / color) : cochée, avec la couleur du mod
    d.innerHTML = `<input type="checkbox" data-aura="${a.aura}"${a.couleur ? ' checked' : ''}><span class="n">${a.aura}${a.origine && a.origine !== a.aura ? ' <small>(copie de ' + echapper(a.origine) + ')</small>' : ''}</span><input type="color" value="${a.couleur || '#2a1f8c'}" data-aura-c="${a.aura}">`;
    b.appendChild(d);
  }
}

// ------------------------------------------------------------------ export
// (21/11, avis demandé par muku : « que ça ne prenne pas la tête ») RAPPORT EN LANGAGE NORMAL : en mode simple, une phrase claire
// (sans chemins de fichiers ni codes), et le texte complet replié dans « Détails » ; en mode avancé, tout le texte comme avant.
const CHEMIN_RE = /\s*:?\s*[A-Za-z]:\\[^\n]*/g;
function phraseSimple(l) {
  return l.replace(/^Mod créé \(pas encore installé\).*$/, 'C’est créé ! Pour le mettre dans le jeu : « Installer » sur sa carte dans Mes créations.')
    .replace(/^(Copie|Tenue|Armure) créée \(pas encore installée\).*$/, (_, q) => q + ' créée ! Pour la mettre dans le jeu : « Installer » sur sa carte dans Mes créations.')
    .replace(/^Objet créé \(pas encore installé\).*$/, 'Objet créé ! Pour le mettre dans le jeu : « Installer » sur sa carte dans Mes créations.')
    .replace(/^Erreur : /, 'Ça n’a pas marché : ').replace(/^Pas installé : /, 'Pas mis dans le jeu : ')
    .replace(CHEMIN_RE, '').trim();
}
function majRapport(t) {
  const el = $('rapport'); t = String(t == null ? '' : t);
  if (!document.body.classList.contains('mode-simple')) { el.textContent = t; return; }
  const lignes = t.split('\n'), tete = phraseSimple(lignes[0]), reste = t !== tete;
  el.textContent = tete;
  if (reste && t.trim()) { const d = document.createElement('details'); d.className = 'rapport-details';
    const s = document.createElement('summary'); s.textContent = 'Détails'; const p = document.createElement('div'); p.textContent = t;
    d.append(s, p); el.append('\n', d); }
}
function modeAvance() { try { return localStorage.getItem('atelier_avance') === '1'; } catch (e) { return false; } }
function appliquerMode(avance) {
  document.body.classList.toggle('mode-simple', !avance);
  const b = $('bouton-avance'); if (b) { b.classList.toggle('actif', avance); b.title = avance ? 'Revenir au mode simple' : 'Montrer les réglages avancés (codes, matériaux, boutons séparés…)'; }
  const t = $('titre-tech'); if (t && t.dataset.complet) { const v = avance ? t.dataset.complet : titreSimple(t.dataset.complet); t.dataset.affiche = v; t.textContent = v; }
}
// (22/11, retour de muku : parcours pas intuitifs) APRÈS UNE CRÉATION, LA SUITE LOGIQUE en boutons, sous le rapport (avant : cachée
// dans « Mes créations ») : nouveau joueur -> ses techniques ; esprit -> sa technique liée, une armure
async function proposerSuite(mod, code) {
  if ($('suite-creation')) $('suite-creation').remove();
  if (!code || !['MesPersonnages', 'MesEsprits'].includes(mod)) return;
  let L = []; try { L = (await api('/api/projets')).creations || []; } catch (e) { return; }
  const c = L.find(x => x.mod === mod && String(x.code) === String(code)); if (!c) return;
  const d = document.createElement('div'); d.id = 'suite-creation'; d.className = 'ensuite';
  const ajout = (txt, f) => { const b = document.createElement('button'); b.textContent = txt; b.onclick = f; d.appendChild(b); };
  if (mod === 'MesPersonnages' && c.cle) ajout('Choisir ses techniques', () => ouvrirCoups(c));
  if (mod === 'MesEsprits' && c.genre === 'esprit') { ajout('Choisir sa technique liée', () => ouvrirTechniqueLiee(c)); ajout('Lui faire une armure', () => window.changerOnglet('armures')); }
  if (!d.children.length) return;
  const t = document.createElement('span'); t.className = 'aide'; t.textContent = 'Et maintenant :'; d.prepend(t);
  $('rapport').after(d);
}
// (22/11, « Les autres parcours ») rouvrir un élément déjà commencé créait un 2e projet sans rien dire (deux whk10060 à une heure d'écart
// dans projets/) : on propose de continuer le dernier. « Nouveau » garde le comportement d'avant (un projet neuf).
async function proposerReprise() {
  if ($('reprise-proposee')) $('reprise-proposee').remove();
  if (!E.tech || E.repriseCle) return;
  const cle = E.projet, code = String(E.tech.code), onglet = E.tech.onglet || 'techniques';
  let L = []; try { L = (await api('/api/projets')).projets || []; } catch (e) { return; }
  if (!E.tech || E.projet !== cle) return;
  const memes = L.filter(x => String(x.code) === code && (x.onglet || 'techniques') === onglet && x.cle !== cle); if (!memes.length) return;
  const p = memes[0];                                  // liste du plus récent au plus ancien
  const d = document.createElement('div'); d.id = 'reprise-proposee';
  d.innerHTML = `<span>Tu as déjà commencé <b>${echapper(p.titre || p.base || code)}</b> (${echapper(dateCourte(p.date))})`
    + (memes.length > 1 ? ` et ${memes.length - 1} autre${memes.length > 2 ? 's' : ''} (accueil)` : '') + '.</span>';
  const b1 = document.createElement('button'); b1.className = 'primaire'; b1.textContent = 'Continuer ce projet';
  b1.onclick = () => { d.remove(); reprendreDepuisHub(p); };
  const b2 = document.createElement('button'); b2.textContent = 'Non, en commencer un nouveau'; b2.onclick = () => d.remove();
  d.append(b1, b2); $('centre').appendChild(d);
}
// (22/11, « les interfaces ne sont pas assez graphiques ») HABILLAGE MENUS DU JEU (style.css, fin) : coin orange avec l'icône et le nom de
// l'écran, bande d'aide du bas (ce qu'on fait ici + touches), images du jeu (fond, orange) pour toute la page ; suit l'onglet ouvert.
const AIDE_ONGLET = {
  techniques: 'Choisis une technique en haut, change ses couleurs, puis « Créer ».',
  esprits: 'Choisis un esprit guerrier en haut, recolore-le, puis « Créer ».',
  totems: 'Choisis un totem en haut, recolore-le, puis « Créer ».',
  bannieres: 'Choisis un style, écris ton texte, puis utilise la bannière pour ta technique.',
  maillots: 'Choisis un maillot du jeu comme coupe, dessine le haut et le short, puis « Créer ».',
  tenues: 'Choisis une tenue en haut, recolore-la, puis « Créer ».',
  armures: 'Choisis une armure en haut, recolore-la pour un de tes esprits, puis « Créer ».',
  personnages: 'Choisis un personnage en haut, recolore sa tête, donne-lui un nom, puis « Créer ».',
  objets: 'Choisis un objet en haut, donne-lui un nom et un prix, puis « Créer ».',
};
function habillageJeu() {
  const h = document.querySelector('header'), nav = document.querySelector('header .onglets');
  if (h && !$('jeu-coin')) { const c = document.createElement('div'); c.id = 'jeu-coin'; c.className = 'jeu-coin';
    c.innerHTML = '<span class="jc-ico"></span><span class="jc-nom"></span>'; h.insertBefore(c, h.firstChild); }
  const m = document.querySelector('main');
  if (m && !$('aide-jeu')) { const f = document.createElement('footer'); f.id = 'aide-jeu';
    f.innerHTML = '<span class="aj-texte"></span><span class="aj-touches"><span><i class="jm-touche">🖱</i>Choisir une pièce</span>'
      + '<span><i class="jm-touche">Glisser</i>Tourner</span><span><i class="jm-touche">Molette</i>Zoom</span><span><i class="jm-touche">Clic droit</i>Déplacer</span></span>';
    m.parentNode.insertBefore(f, m.nextSibling); }
  const maj = () => {
    const o = (document.body.className.match(/onglet-(\w+)/) || [])[1] || 'hub';
    const b = nav && nav.querySelector(`button[data-onglet="${o}"]`), g = ONGLETS_HUB.find(x => x.o === o);
    const c = $('jeu-coin'); if (c) { c.querySelector('.jc-nom').textContent = b ? b.textContent : 'Mes créations';
      c.querySelector('.jc-ico').innerHTML = iconeJeu(g ? g.ic : 'm3', 34); }
    const a = $('aide-jeu'); if (a) { a.querySelector('.aj-texte').textContent = AIDE_ONGLET[o] || '';
      a.querySelector('.aj-touches').style.display = o === 'bannieres' ? 'none' : ''; }
  };
  new MutationObserver(maj).observe(document.body, { attributes: true, attributeFilter: ['class'] });
  chargerMenusJeu().then(J => { const r = document.documentElement;
    if (J && J.fond) r.style.setProperty('--jm-fond', `url("${J.fond.url}")`);
    if (J && J.fond_orange) r.style.setProperty('--jm-fond-orange', `url("${J.fond_orange.url}")`); maj(); }).catch(() => {});
  maj();
}
// titre de l'élément ouvert : en mode simple, sans les codes du jeu (whs00830, c01000300…) ni la cinématique
function titreSimple(s) { return s.split('·').map(x => x.trim()).filter(x => x && !/^(cinématique|cutscene)\s|^[a-z]{1,4}\d{4,}[a-z0-9_]*$/i.test(x)).join('  ·  '); }
window.addEventListener('load', () => {
  // bouton « Avancé » dans l'en-tête (mode simple par défaut)
  const h = document.querySelector('header');
  if (h && !$('bouton-avance')) { const b = document.createElement('button'); b.id = 'bouton-avance'; b.textContent = 'Avancé';
    b.onclick = () => { const a = !document.body.classList.contains('mode-simple'); try { localStorage.setItem('atelier_avance', a ? '0' : '1'); } catch (e) { }
      appliquerMode(!a); };
    h.appendChild(b); }
  const t = $('titre-tech');
  if (t) new MutationObserver(() => {
    if (t.textContent === t.dataset.affiche) return;
    t.dataset.complet = t.textContent;
    const v = document.body.classList.contains('mode-simple') ? titreSimple(t.textContent) : t.textContent;
    t.dataset.affiche = v; if (v !== t.textContent) t.textContent = v;
  }).observe(t, { childList: true, characterData: true, subtree: true });
  appliquerMode(modeAvance());
  habillageJeu();
  // (22/11, demande de muku : « supprime "Créer et mettre dans le jeu", mets juste "Créer", on n'a besoin que de créer »)
  // UN SEUL BOUTON par panneau : « Créer » (la création, sans toucher au jeu). Plus de bouton « Installer dans le jeu » dans
  // les panneaux : on installe depuis la carte de la création dans Mes créations. (L'installation automatique remplaçait le
  // mod du jeu et demandait de retirer des créations faites ailleurs.)
  for (const [id, idInst] of [['exporter', 'installer'], ['exporter-perso', 'installer-perso'], ['cp-exporter', 'cp-installer'], ['ct-exporter', 'ct-installer'],
    ['co-exporter', 'co-installer'], ['cu-exporter', 'cu-installer'], ['oj-exporter', 'oj-installer'], ['ca-exporter', 'ca-installer']]) {
    const b = $(id); if (!b) continue;
    // onglet Tenues : deux créations différentes (tenue de boutique / nouveau joueur qui la porte) -> nommées
    b.textContent = { 'cu-exporter': 'Créer la tenue', 'ct-exporter': 'Créer le joueur' }[id] || 'Créer'; b.title = 'Crée ta copie, sans toucher au jeu. Pour la mettre dans le jeu : « Installer » sur sa carte dans Mes créations.';
    b.classList.add('primaire', 'creer-jeu'); b.classList.remove('avance');
    if ($(idInst)) $(idInst).remove();
  }
});
async function exporter() {
  if (!E.tech) return majRapport('Ouvre d\'abord une technique.');
  const objets = {};
  for (const o of E.objets) { if (o.erreur || o.commun) continue;            // effets communs (ega…) : jamais exportés
    const imgs = {};
    for (const [cle, x] of Object.entries(E.textures)) if (x.obj === o && x.modif) imgs[x.nom] = x.cur.toDataURL('image/png');
    const lueurs = !o.modeleActeur && $('lueurs-on').checked ? { hue: +$('lueurs-h').value, saturation: 1.3, value: 1.0, garder_or: $('garder-or').checked } : null;
    const materiaux = {};                    // (14/11/2026) couleurs des matériaux -> VRFW [[recolor.tint]]
    if (!o.modeleActeur) for (const [k, c] of Object.entries(E.coulMat || {})) if (k.startsWith(o.nom + '/')) materiaux[c.nom] = c.rgb;
    const sommets = {};                      // (14/11/2026) teintes des sommets : {nom de pièce : [H, C]}
    if (!o.modeleActeur) for (const [k, t] of Object.entries(E.teinteSom || {})) if (k.startsWith(o.nom + '/')) sommets[t.nom] = [t.H, t.C];
    const tp = !o.modeleActeur && (E.teintePtl || {})[o.nom], particules = tp ? [tp.H, tp.C] : null;
    if (Object.keys(imgs).length || lueurs || Object.keys(materiaux).length || Object.keys(sommets).length || particules)
      objets[o.acteur] = { textures: imgs, lueurs, materiaux, sommets, particules };
  }
  const auras = {};
  document.querySelectorAll('[data-aura]').forEach(cb => { if (cb.checked) auras[cb.dataset.aura] = hex2rgb(document.querySelector(`[data-aura-c="${CSS.escape(cb.dataset.aura)}"]`).value); });
  if (!Object.keys(objets).length && !Object.keys(auras).length) return majRapport('Rien n\'est modifié : change d\'abord des couleurs.');
  const d = { code: E.tech.code, nom: $('f-nom').value.trim() || E.tech.nom + ' (couleurs)', description: $('f-desc').value.trim(),
    couleur_tir: $('f-couleur').value === '' ? null : +$('f-couleur').value, prix: $('f-prix').value ? +$('f-prix').value : null,
    banniere: { texte: $('f-ban').value.trim(), couleur: $('f-ban-c').value, contour: $('f-ban-o').value },
    trainee: $('f-trainee').value ? { famille: $('f-trainee').value, element: $('f-trainee-el').value } : null, objets, auras };
  if (E.banniereImage && E.banniereImage.projet === E.projet) d.banniere.image = E.banniereImage.image;   // (21/11) liée au projet
  majRapport('Création du mod…');
  try { const r = await api('/api/exporter', d);
    majRapport(r.ok ? 'Mod créé (pas encore installé) : ' + r.dossier + '\n- ' + r.rapport.join('\n- ') : 'Erreur : ' + r.erreur);
    if (r.ok) { const m = /code (\w+)/.exec(r.rapport[0] || ''), v = await faireVignette() || E.vignette;     // (15/11/2026) image pour le hub
      if (m && v) api('/api/vignette', { code: m[1], image: v }).catch(() => {}); }
    return r;
  } catch (e) { majRapport('Erreur : ' + e.message); }
}
// (16/11/2026) PHOTO POUR LE PORTRAIT D'UNE COPIE (moteur/icones_copies.py) : le modèle recoloré de la vue, de face, fond
// transparent, 256 x 256 ; cadre « visage » = toute la tête (nouveau joueur), « buste » = le haut du modèle (esprit, totem).
// Les recolorations sont peintes librement : seule une photo du modèle les montre toutes dans le portrait.
async function photoIcone(cadre) {
  const V = E.vue; if (!V || !V.cv || !V.cv.width) return null;
  const ps = V.pieces.filter(p => p.visible && !p.terrain && p.boite && p.boite[0][0] < 1e8 && !String(p.cle || '').startsWith('stade/'));
  if (!ps.length) return null;
  const mn = [1e9, 1e9, 1e9], mx = [-1e9, -1e9, -1e9];
  for (const p of ps) for (let k = 0; k < 3; k++) { mn[k] = Math.min(mn[k], p.boite[0][k]); mx[k] = Math.max(mx[k], p.boite[1][k]); }
  const H = mx[1] - mn[1], cx = (mn[0] + mx[0]) / 2;
  // buste : la tête = le plus haut point PRÈS DE L'AXE du modèle (les ailes et les bras écartés ne comptent pas)
  let tete = mx[1];
  if (cadre === 'buste') { let t = -1e9;
    for (const o of E.objets || []) for (const pc of o.pieces || []) { const P = pc.geo && pc.geo.pos; if (!P || (pc.vue && !pc.vue.visible)) continue;
      for (let i = 0; i < P.length; i += 3) if (Math.abs(P[i] - cx) < 0.12 * (mx[0] - mn[0]) && P[i + 1] > t) t = P[i + 1]; }
    if (t > -1e9) tete = Math.min(mx[1], t + 0.04 * H); }
  const haut = tete, bas = cadre === 'buste' ? tete - 0.36 * H : mn[1];
  const larg = Math.max(mx[0] - mn[0], mx[2] - mn[2]) * (cadre === 'buste' ? 0.75 : 1), cote = cadre === 'buste' ? (haut - bas) * 1.05 : Math.max(haut - bas, larg) * 1.42;   // buste : gros plan (ailes larges coupées, comme le jeu)   // marge des portraits du jeu (tête ~70 % de la hauteur)
  const sv = { yaw: V.yaw, pitch: V.pitch, dist: V.dist, centre: V.centre.slice(), cam: V.cameraJeu, fil: V.fil, ec: V.eclat, sel: V.pieces.map(p => p.sel) };
  try {
    V.cameraJeu = false; V.fil = false; V.eclat = null; V.pieces.forEach(p => { p.sel = false; });
    V.yaw = 0; V.pitch = 0.04; V.centre = [(mn[0] + mx[0]) / 2, (haut + bas) / 2, (mn[2] + mx[2]) / 2];
    V.dist = cote / (2 * Math.tan(0.45)) + (mx[2] - mn[2]) / 2;           // champ vertical 0,9 rad (vue3d persp)
    V._dessinerUne(V.image);
    const w = V.cv.width, h = V.cv.height, c = Math.min(w, h), o = document.createElement('canvas'); o.width = o.height = 256;
    o.getContext('2d').drawImage(V.cv, (w - c) / 2, (h - c) / 2, c, c, 0, 0, 256, 256);
    return o.toDataURL('image/png');
  } catch (e) { return null; }
  finally { Object.assign(V, { yaw: sv.yaw, pitch: sv.pitch, dist: sv.dist, centre: sv.centre, cameraJeu: sv.cam, fil: sv.fil, eclat: sv.ec });
    V.pieces.forEach((p, k) => { p.sel = sv.sel[k]; }); }
}
async function exporterPerso() {
  if (!E.tech || !E.tech.perso || ONGLETS_JEU.includes(E.tech.onglet)) return majRapport('Ouvre d\'abord un esprit guerrier ou un totem.');
  const textures = {};
  for (const x of Object.values(E.textures)) if (x.modif) textures[x.nom] = x.cur.toDataURL('image/png');
  if (!Object.keys(textures).length) return majRapport('Rien n\'est modifié : change d\'abord des couleurs.');
  majRapport('Création de la copie (réencodage des textures, environ 45 s)…');
  const nom = $('p-nom').value.trim(); if (!nom) return majRapport('Donne un nom à la copie.');
  try { const r = await api('/api/exporter_personnage', { code: E.tech.code, textures, nom, description: $('p-desc').value.trim(),
      prix: $('p-prix').value ? +$('p-prix').value : null, icone: await photoIcone('buste') });
    majRapport(r.ok ? 'Mod créé (pas encore installé) : ' + r.dossier + '\n- ' + r.rapport.join('\n- ') : 'Erreur : ' + r.erreur);
    return r;
  } catch (e) { majRapport('Erreur : ' + e.message); }
}
// ------------------------------------------------------------------ (15/11/2026) ATELIER MAILLOTS (moteur/mes_maillots.py)
// Un maillot = une coupe du jeu (ouverte dans l'onglet) + mes images : haut = texture « …_20 », short + chaussettes = « …_30 ».
// (15/11/2026) CÔTÉS (domicile 10 / extérieur 20) et ACCESSOIRES (chaussures, gants des gardiens) : chaque côté garde ses
// retouches ; « base » = images enregistrées (posées à l'ouverture, renvoyées seulement si on les change), « edits » = changées.
const MM = { liste: [], id: null, icone: null, embleme: null, cote: '10', base: { '10': {}, '20': {} }, edits: { '10': {}, '20': {} } };
const MM_ROLES = { haut: 'haut', short: 'short', chaussures: 'chaussures', gants: 'gants' };
function mmRoles() {          // rôle -> {cle, x, o, bloc} pour le côté ouvert
  const out = {};
  for (const o of E.objets) { if (!o.role) continue;
    for (const t of o.textures || []) { const cle = o.nom + '/' + t.nom, x = E.textures[cle]; if (!x || !x.cur || (x.info && x.info.donnees)) continue;
      if (o.role === 'maillot') { if (/_20$/.test(t.nom)) out.haut = out.haut || { cle, x, o, bloc: t.nom }; else if (/_30$/.test(t.nom)) out.short = out.short || { cle, x, o, bloc: t.nom }; }
      else if (!out[o.role] && !/(line|msk|oc|sp|spm)$/.test(t.nom)) out[o.role] = { cle, x, o, bloc: t.nom }; } }
  return out;
}
function mmTexture(suf) { const r = mmRoles(); return ((suf === '20' ? r.haut : r.short) || {}).cle; }
function mmCapturer() {       // retouches du côté ouvert -> MM.edits
  const ed = MM.edits[MM.cote] = MM.edits[MM.cote] || {};
  for (const [role, v] of Object.entries(mmRoles())) { const x = v.x;
    if (x.modif && x.moyenne.join() !== x.mmCharge) ed[role] = { png: x.cur.toDataURL('image/png'), bloc: v.bloc, texture: v.o.texture_jeu, modele: v.o.modele_jeu }; }
}
async function mmPoser() {    // images du côté ouvert (changées, sinon enregistrées) sur la coupe
  const ed = MM.edits[MM.cote] || {}, ba = MM.base[MM.cote] || {};
  for (const [role, v] of Object.entries(mmRoles())) { const src = (ed[role] && ed[role].png) || ba[role]; if (!src) continue;
    try { const im = await chargerImage(src.startsWith('data:') ? src : src + '?v=' + Date.now()), x = v.x, cx = x.cur.getContext('2d');
      cx.clearRect(0, 0, x.cur.width, x.cur.height); cx.drawImage(im, 0, 0, x.cur.width, x.cur.height);
      x.base = cx.getImageData(0, 0, x.cur.width, x.cur.height); x.modif = true; x.moyenne = moyenne(x.base); x.donneesCur = null;
      x.mmCharge = ed[role] ? null : x.moyenne.join(); } catch (e) { /* image illisible */ } }
  apresRetouche(); if (window.zonesPreparer) zonesPreparer();
}
async function mmCote(c) {
  if (!E.tech || E.tech.onglet !== 'maillots' || c === MM.cote) return;
  mmCapturer(); MM.cote = c; E.repriseAuto = E.projet;            // même projet pour les deux côtés
  await ouvrir(E.tech.code); await mmPoser(); mmMajCotes();
  majRapport((c === '20' ? 'Côté extérieur' : 'Côté domicile') + (c === '20' && E.tech.tex20_existe === false ? ' (ce maillot du jeu n’en a pas : on part du domicile)' : '') + '. Chaque côté garde ses retouches.');
}
function mmMajCotes() { document.querySelectorAll('[data-mm-cote]').forEach(b => b.classList.toggle('actif', b.dataset.mmCote === MM.cote));
  const r = mmRoles(); $('mm-parties').textContent = 'Sur ce côté : ' + ['haut', 'short', 'chaussures', 'gants'].filter(k => r[k]).map(k => ({ haut: 'haut (« _20 »)', short: 'short + chaussettes (« _30 »)', chaussures: 'chaussures', gants: 'gants des gardiens' })[k]).join(', ') + '.'; }
async function mmListe() {
  try { MM.liste = await api('/api/mes_maillots'); } catch (e) { MM.liste = []; }
  const b = $('mm-liste'); if (!b) return; b.innerHTML = MM.liste.length ? '' : '<p class="aide">Aucun maillot pour l’instant.</p>';
  for (const m of MM.liste) { const d = document.createElement('div'); d.className = 'mm-item' + (m.id === MM.id ? ' actif' : '');
    d.innerHTML = `<img src="${echapper(m.icone || m.images.haut_dom || '')}" alt=""><div><b>${echapper(m.nom)}</b><small>coupe : ${echapper(m.nom_base || '')} · ${m.prix || 1} jeton(s)</small></div>`
      + '<button class="mm-sup" title="Retirer de la liste (ses images restent dans maillots/travail)">🗑</button>';
    d.onclick = ev => { if (ev.target.closest('.mm-sup')) return; mmOuvrir(m); };
    d.querySelector('.mm-sup').onclick = async () => { if (!confirm(`Retirer « ${m.nom} » de tes maillots ?\nSes images restent dans AtelierCouleurs/maillots/travail.`)) return;
      await api('/api/maillot', { action: 'supprimer', id: m.id }); if (MM.id === m.id) mmNouveau(); mmListe(); };
    b.appendChild(d); }
}
function mmFormulaire(m) {
  const n = (m && m.numero) || {};
  $('mm-nom').value = m ? m.nom : (E.tech ? E.tech.nom + ' (perso)' : ''); $('mm-prix').value = m ? m.prix || 1 : 1; $('mm-plis').value = (m && m.plis) || 'simples';
  $('mm-num-perso').checked = !!n.perso; $('mm-num-c1').value = '#' + (n.remplissage || 'FFFFFF'); $('mm-num-c2').value = '#' + (n.contour || '000000');
  $('mm-num-police').value = n.chiffres ? 'f:' + n.chiffres : String(n.police || 1); $('mm-num-taille').value = Math.round((n.taille || 1) * 100); $('mm-num-hauteur').value = n.hauteur || 0;
  $('mm-num-nom').checked = !!n.nom; $('mm-num-lettres').value = n.lettres || '';
  // (22/11) police importée pas encore chargée : choisie dès qu'elle arrive (parametres.js : brancherPolices)
  for (const [id, v] of [['mm-num-police', n.chiffres ? 'f:' + n.chiffres : null], ['mm-num-lettres', n.lettres || null]]) if (v && $(id).value !== v) $(id).dataset.voulue = v;
  mmApercuNumero();
  $('mm-icone-img').src = (m && m.icone) || ''; $('mm-embleme-img').src = (m && m.embleme) || ''; MM.icone = MM.embleme = null;
  $('mm-en-cours').textContent = m ? 'Maillot : ' + m.nom : 'Nouveau maillot' + (E.tech ? ' (coupe : ' + E.tech.nom + ')' : '');
}
function mmNouveau() { MM.id = null; MM.cote = '10'; MM.base = { '10': {}, '20': {} }; MM.edits = { '10': {}, '20': {} }; mmFormulaire(null); mmListe(); if (E.tech && E.tech.onglet === 'maillots') mmMajCotes(); }
async function mmOuvrir(m) {
  if (!m.code) return majRapport('Coupe introuvable pour ' + m.nom + ' : ' + m.base);
  MM.id = m.id; MM.cote = '10'; MM.edits = { '10': {}, '20': {} };
  const a = m.accessoires || {}, im = m.images || {};
  MM.base = { '10': { haut: im.haut_dom, short: im.short_dom, chaussures: a.chaussures_dom && a.chaussures_dom.png, gants: a.gants_dom && a.gants_dom.png },
              '20': { haut: im.haut_ext, short: im.short_ext, chaussures: a.chaussures_ext && a.chaussures_ext.png, gants: a.gants_ext && a.gants_ext.png } };
  await ouvrir(m.code); await mmPoser(); mmFormulaire(m); mmListe(); mmMajCotes();
  majRapport('Maillot « ' + m.nom + ' » repris : ses images sont sur la coupe (domicile). Bouton « Extérieur » pour l’autre côté.');
}
function mmNumero() { const h = id => $(id).value.replace('#', '').toUpperCase(), v = $('mm-num-police').value, ordi = v.startsWith('f:');
  return { perso: $('mm-num-perso').checked, remplissage: h('mm-num-c1'), contour: h('mm-num-c2'), police: ordi ? 1 : +v, chiffres: ordi ? v.slice(2) : undefined,
    taille: +$('mm-num-taille').value / 100, hauteur: +$('mm-num-hauteur').value, nom: $('mm-num-nom').checked, lettres: $('mm-num-lettres').value || undefined }; }
// (16/11/2026) NUMÉRO DANS LE DOS : police de l'ordinateur et aperçu.
// Planches au format du jeu (LU sur n000101_10.g4tx / n000201_10.g4tx) : chiffres 2048 x 2048, 10 x 10 cases de 204,8 px
// (0 à 99, ligne de base à 154 px dans la case, chiffres ~116 px de haut comme ceux du jeu) ; lettres du nom 512 x 1024,
// cases de 64 px (même grille que l'Atelier Maillots). Image blanche (alpha = forme avec contour) + masque (vert =
// remplissage, bleu = contour) ; moteur/maillots/numeros.texture_perso les met dans une copie de la texture du numéro.
const MM_CARS_NOMS = ['ABCDEFGH', 'IJKLMNOP', 'QRSTUVWX', 'YZ', 'abcdefgh', 'ijklmnop', 'qrstuvwx', 'yz', 'ÁÄĂÃÇÉÈÊ', 'ÍÑÓÔÕÖÚÙ', 'Ü', '01234567', '89'];
function mmEcrire(c, txt, cx, by, taille, police, maxw, trait, contour) {
  const x = c.getContext('2d'); x.save(); x.font = 'bold ' + taille + 'px "' + police + '", sans-serif'; x.textAlign = 'center'; x.textBaseline = 'alphabetic';
  const w = x.measureText(txt).width + trait; x.translate(cx, by); if (w > maxw) x.scale(maxw / w, 1);
  x.fillStyle = x.strokeStyle = '#fff'; x.lineJoin = 'round';
  if (contour) { x.lineWidth = trait; x.strokeText(txt, 0, 0); }
  x.fillText(txt, 0, 0); x.restore();
}
function mmPlanche(w, h, dessiner) {          // forme (avec contour) + remplissage seul -> [image, masque] (canevas)
  const fab = () => { const c = document.createElement('canvas'); c.width = w; c.height = h; return c; };
  const cf = fab(), cr = fab(); dessiner(cf, true); dessiner(cr, false);
  const a = cf.getContext('2d').getImageData(0, 0, w, h).data, r = cr.getContext('2d').getImageData(0, 0, w, h).data;
  const img = new ImageData(w, h), msk = new ImageData(w, h);
  for (let i = 0; i < w * h * 4; i += 4) { img.data[i] = img.data[i + 1] = img.data[i + 2] = 255; img.data[i + 3] = a[i + 3];
    msk.data[i + 1] = r[i + 3]; msk.data[i + 2] = 255 - r[i + 3]; msk.data[i + 3] = 255; }
  const ci = fab(), cm = fab(); ci.getContext('2d').putImageData(img, 0, 0); cm.getContext('2d').putImageData(msk, 0, 0);
  return [ci, cm];
}
// chiffres à la hauteur de ceux du jeu (LU n000101_10 : forme avec contour de y 38 à 154 dans la case de 204,8) : taille de
// police calculée pour que les chiffres (sans contour) fassent 104 px, ligne de base à 148, contour de 12 px
function mmTailleChiffres(p) { const c = document.createElement('canvas').getContext('2d'); c.font = 'bold 100px "' + p + '", sans-serif';
  const m = c.measureText('0123456789'), h = (m.actualBoundingBoxAscent || 72) + Math.max(0, m.actualBoundingBoxDescent || 0);
  return Math.max(40, Math.min(400, 100 * 104 / Math.max(h, 1))); }
const mmPlancheChiffres = p => { const t = mmTailleChiffres(p);
  return mmPlanche(2048, 2048, (c, ct) => { for (let n = 0; n < 100; n++) mmEcrire(c, String(n), (n % 10) * 204.8 + 102.4, Math.floor(n / 10) * 204.8 + 148, t, p, 184, 12, ct); }); };
const mmPlancheNoms = p => mmPlanche(512, 1024, (c, ct) => MM_CARS_NOMS.forEach((l, row) => [...l].forEach((ch, col) => mmEcrire(c, ch, col * 64 + 32, row * 64 + 53, 58, p, 56, 5, ct))));
async function mmChargerPolice(p) { try { await document.fonts.load('bold 64px "' + p + '"', '0123456789AZ'); } catch (e) { /* police système : déjà là */ } }
async function mmLettresPng(n) {              // planches à envoyer à l'enregistrement ({} = celles du jeu)
  const out = {}; if (!n.perso) return out;
  if (n.chiffres) { await mmChargerPolice(n.chiffres); const [a, b] = mmPlancheChiffres(n.chiffres); out.num = a.toDataURL('image/png'); out.num_msk = b.toDataURL('image/png'); }
  if (n.nom && n.lettres) { await mmChargerPolice(n.lettres); const [a, b] = mmPlancheNoms(n.lettres); out.noms = a.toDataURL('image/png'); out.noms_msk = b.toDataURL('image/png'); }
  return out;
}
const MM_PLANCHES_JEU = {};
function mmPlancheJeu(p) {                    // planche du jeu (serveur : R = remplissage, A = forme ; 1024 x 1024)
  if (!MM_PLANCHES_JEU[p]) MM_PLANCHES_JEU[p] = new Promise((ok, ko) => { const i = new Image(); i.onload = () => ok(i); i.onerror = ko; i.src = '/api/planche_numero?p=' + p; });
  return MM_PLANCHES_JEU[p];
}
function mmCouleurMaillot() {                 // couleur moyenne du haut ouvert : fond de l'aperçu
  try { const r = mmRoles(); const m = r.haut && r.haut.x && r.haut.x.moyenne; if (m && m.length >= 3) return 'rgb(' + m.slice(0, 3).map(v => Math.round(v)).join(',') + ')'; } catch (e) { /* pas de maillot */ }
  return '#34507f';
}
let mmApercuJeton = 0;
async function mmApercuNumero() {
  const cv = $('mm-num-apercu'); if (!cv) return;
  const jeton = ++mmApercuJeton, n = mmNumero(), x = cv.getContext('2d'), W = cv.width, H = cv.height;
  const val = Math.max(0, Math.min(99, Math.round(+$('mm-num-essai').value || 0))), fill = '#' + n.remplissage, cont = '#' + n.contour;
  const fond = () => { x.clearRect(0, 0, W, H); x.fillStyle = mmCouleurMaillot(); x.fillRect(0, 0, W, H);
    x.fillStyle = 'rgba(255,255,255,0.06)'; for (let i = 0; i < W; i += 6) x.fillRect(i, 0, 1, H); };
  const k = n.taille || 1, cy = n.nom ? 128 : 112, taille = 150 * k;            // la case du numéro, à l'échelle de l'aperçu
  // un numéro : case (val) de la planche -> remplissage / contour aux couleurs choisies
  const dessinerCase = (src, cell, dx, dy, s) => { const t = document.createElement('canvas'); t.width = t.height = Math.ceil(s);
    const tx = t.getContext('2d'); tx.drawImage(src, cell.x, cell.y, cell.w, cell.h, 0, 0, s, s);
    const d = tx.getImageData(0, 0, t.width, t.height), a = d.data, cf = mmHex(fill), cc = mmHex(cont);
    for (let i = 0; i < a.length; i += 4) { const f = a[i] / 255, al = a[i + 3]; a[i] = cc[0] + (cf[0] - cc[0]) * f; a[i + 1] = cc[1] + (cf[1] - cc[1]) * f; a[i + 2] = cc[2] + (cf[2] - cc[2]) * f; a[i + 3] = al; }
    tx.putImageData(d, 0, 0); x.drawImage(t, dx, dy); };
  let info = '';
  if (n.chiffres) {                           // police de l'ordinateur : dessinée comme la planche qui ira dans le jeu
    await mmChargerPolice(n.chiffres); if (jeton !== mmApercuJeton) return;
    const tc = mmTailleChiffres(n.chiffres), [ci, cm] = mmPlanche(205, 205, (c, ct) => mmEcrire(c, String(val), 102.4, 148, tc, n.chiffres, 184, 12, ct));
    const t = document.createElement('canvas'); t.width = t.height = 205; const tx = t.getContext('2d'), d = tx.createImageData(205, 205);
    const A = ci.getContext('2d').getImageData(0, 0, 205, 205).data, M = cm.getContext('2d').getImageData(0, 0, 205, 205).data;
    for (let i = 0; i < d.data.length; i += 4) { d.data[i] = M[i + 1]; d.data[i + 3] = A[i + 3]; }
    tx.putImageData(d, 0, 0); fond(); dessinerCase(t, { x: 0, y: 0, w: 205, h: 205 }, W / 2 - taille / 2, cy - taille / 2, taille);
  } else {                                    // police du jeu : la case de la planche du jeu
    const p = n.perso && n.nom ? 0 : (n.perso ? n.police : 1);
    let img = null; try { img = await mmPlancheJeu(p); } catch (e) { info = 'Planche du jeu introuvable.'; }
    if (jeton !== mmApercuJeton) return;
    fond();
    if (img) { const c = img.width / 10; dessinerCase(img, { x: (val % 10) * c, y: Math.floor(val / 10) * c, w: c, h: c }, W / 2 - taille / 2, cy - taille / 2, taille); }
  }
  if (n.perso && n.nom) {                     // nom au-dessus (lettres du jeu : police proche, seulement pour l'idée)
    const nomEx = (($('mm-nom').value || 'JOUEUR').replace(/^(Maillot|Tenue)\s+/i, '').split(' ')[0] || 'JOUEUR').toUpperCase().slice(0, 10);
    x.save(); x.font = 'bold ' + Math.round(30 * k) + 'px "' + (n.lettres || 'Arial Black') + '", sans-serif'; x.textAlign = 'center'; x.lineJoin = 'round';
    x.lineWidth = 5 * k; x.strokeStyle = cont; x.strokeText(nomEx, W / 2, cy - taille / 2 + 22 * k); x.fillStyle = fill; x.fillText(nomEx, W / 2, cy - taille / 2 + 22 * k); x.restore();
  }
  if (!n.perso) info = 'Numéro du jeu (coche « Personnaliser » pour le changer)';
  else if (!n.chiffres && !n.nom && [2, 3, 5].includes(n.police)) info = 'Police du jeu ' + n.police + ' : sans contour (LU sur sa planche)';
  if (info) { x.fillStyle = 'rgba(0,0,0,0.55)'; x.fillRect(0, H - 22, W, 22); x.fillStyle = '#fff'; x.font = '12px sans-serif'; x.textAlign = 'center'; x.fillText(info, W / 2, H - 7); }
}
function mmHex(h) { h = String(h).replace('#', ''); return [0, 2, 4].map(i => parseInt(h.slice(i, i + 2), 16) || 0); }   // 0..255
async function mmEnregistrer() {
  if (!E.tech || E.tech.onglet !== 'maillots') return majRapport('Ouvre d’abord un maillot du jeu (il sert de coupe) ou un de tes maillots.');
  const base = E.tech.cle_maillot; if (!base) return majRapport('Ce maillot du jeu ne peut pas servir de coupe.');
  mmCapturer();
  const images = {}, accessoires = {};
  for (const [c, suf] of [['10', 'dom'], ['20', 'ext']]) { const ed = MM.edits[c] || {};
    if (ed.haut) images['haut_' + suf] = ed.haut.png; if (ed.short) images['short_' + suf] = ed.short.png;
    for (const r of ['chaussures', 'gants']) if (ed[r]) accessoires[r + '_' + suf] = ed[r]; }
  if (!MM.id && !images.haut_dom) { const r = mmRoles();
    if (MM.cote === '10' && r.haut) images.haut_dom = r.haut.x.cur.toDataURL('image/png');
    else return majRapport('Il faut au moins le haut domicile : repasse sur « Domicile » puis enregistre.'); }
  majRapport('Enregistrement du maillot…');
  const r = await api('/api/maillot', { action: 'enregistrer', id: MM.id, nom: $('mm-nom').value, prix: +$('mm-prix').value || 1, base,
    plis: $('mm-plis').value, numero: mmNumero(), images, accessoires, icone: MM.icone, embleme: MM.embleme, lettres_png: await mmLettresPng(mmNumero()) });
  if (!r.ok) return majRapport('Pas enregistré : ' + r.erreur);
  // ce qui vient d'être envoyé devient « enregistré » (plus renvoyé tant qu'on n'y touche pas)
  for (const c of ['10', '20']) { for (const [role, v] of Object.entries(MM.edits[c] || {})) MM.base[c][role] = v.png; MM.edits[c] = {}; }
  for (const v of Object.values(mmRoles())) v.x.mmCharge = v.x.moyenne.join();
  MM.id = r.id; MM.icone = MM.embleme = null; await mmListe(); $('mm-en-cours').textContent = 'Maillot : ' + $('mm-nom').value;
  majRapport('Maillot enregistré (domicile, extérieur, chaussures et gants changés). « Ajouter au mod » pour le mettre dans le mod.');
}
// (15/11/2026) « Ajouter au mod » : comme les autres créations, le maillot est enregistré puis le mod MesMaillots est écrit
// dans AtelierCouleurs/sortie (sans toucher au jeu) ; « Installer » dans Mes créations le met dans le jeu
async function mmConstruire() {
  if (E.tech && E.tech.onglet === 'maillots' && (MM.id || Object.keys(MM.edits['10'] || {}).length || Object.keys(MM.edits['20'] || {}).length || mmRoles().haut)) {
    await mmEnregistrer(); if (!MM.id) return; }
  const r = await api('/api/maillot', { action: 'construire' }); if (!r.ok) return majRapport('Pas ajouté : ' + r.erreur);
  majRapport('Ajout au mod « Mes maillots »… (de quelques secondes à quelques minutes)');
  // (21/11) la promesse se termine avec la construction : « Créer et mettre dans le jeu » enchaîne alors l'installation
  return await new Promise(fini => {
    const suivre = async () => { let e; try { e = await api('/api/maillot_etat'); } catch (x) { return fini({ ok: false, erreur: x.message }); }
      majRapport((e.en_cours ? 'Construction…\n' : e.erreur ? 'Erreur : ' + e.erreur + '\n'
        : 'Maillot créé (mod « Mes maillots » refait, sans toucher au jeu). Pour le mettre dans le jeu : « Installer » dans Mes créations.\n') + e.journal.join('\n'));
      if (e.en_cours) setTimeout(suivre, 1000); else fini({ ok: !e.erreur, erreur: e.erreur }); };
    suivre(); });
}
function mmFichier(input, cle, img) { input.onchange = () => { const f = input.files[0]; if (!f) return; const lr = new FileReader();
  lr.onload = () => { MM[cle] = lr.result; $(img).src = lr.result; }; lr.readAsDataURL(f); }; }
window.addEventListener('load', () => { if (!$('mm-enregistrer')) return;
  $('mm-enregistrer').onclick = () => mmEnregistrer().catch(e => majRapport('Erreur : ' + e.message));
  $('mm-nouveau').onclick = mmNouveau; document.querySelectorAll('[data-mm-cote]').forEach(b => b.onclick = () => mmCote(b.dataset.mmCote).catch(e => majRapport('Erreur : ' + e.message))); $('mm-construire').onclick = () => mmConstruire().catch(e => majRapport('Erreur : ' + e.message));
  mmFichier($('mm-icone'), 'icone', 'mm-icone-img'); mmFichier($('mm-embleme'), 'embleme', 'mm-embleme-img');
  // (16/11/2026) aperçu du numéro : redessiné à chaque réglage
  // (22/11) polices importées (⚙ Paramètres) dans les deux listes, + « Importer une police… »
  if (window.brancherPolices) { brancherPolices($('mm-num-police'), p => 'f:' + p.nom); brancherPolices($('mm-num-lettres'), p => p.nom); }
  for (const id of ['mm-num-perso', 'mm-num-c1', 'mm-num-c2', 'mm-num-police', 'mm-num-taille', 'mm-num-hauteur', 'mm-num-nom', 'mm-num-lettres', 'mm-num-essai', 'mm-nom'])
    if ($(id)) { $(id).addEventListener('input', () => mmApercuNumero()); $(id).addEventListener('change', () => mmApercuNumero()); }
  mmApercuNumero(); });
// ------------------------------------------------------------------ (15/11/2026) REMPLACEMENTS (moteur/retouches.py)
async function rtExporter() {
  if (!E.tech || !['tenues', 'armures', 'personnages', 'objets'].includes(E.tech.onglet)) return majRapport('Ouvre d’abord une tenue, une armure, un personnage ou un objet.');
  const textures = {};
  for (const x of Object.values(E.textures)) if (x.modif && x.cur && x.obj && x.obj.nom === E.objets[0].nom) textures[x.nom] = x.cur.toDataURL('image/png');
  if (!Object.keys(textures).length) return majRapport('Rien n’est modifié : change d’abord des couleurs.');
  majRapport('Création du mod MesRetouches (réencodage de ' + Object.keys(textures).length + ' texture(s))…');
  const r = await api('/api/retouche', { action: 'exporter', cat: E.tech.onglet, code: E.tech.code, nom: $('rt-nom').value.trim() || E.tech.nom, textures });
  majRapport(r.ok ? 'Mod créé (pas encore installé) : ' + r.dossier + '\n' + r.fichier + '\n- ' + r.rapport.join('\n- ') : 'Erreur : ' + r.erreur);
}
async function rtRetirer() {
  if (!E.tech) return;
  if (!confirm(`Remettre « ${E.tech.nom} » comme dans le jeu ?\nSa texture sort du mod MesRetouches (gardée dans sortie/MesRetouches/_retires). Réinstalle ensuite.`)) return;
  const r = await api('/api/retouche', { action: 'retirer', cat: E.tech.onglet, code: E.tech.code });
  majRapport(r.ok ? 'Retiré de MesRetouches. « Installer dans le jeu » pour que le jeu reprenne l’original.' : 'Rien à retirer : ' + r.erreur);
}
window.addEventListener('load', () => { if (!$('rt-exporter')) return;
  $('rt-exporter').onclick = () => rtExporter().catch(e => majRapport('Erreur : ' + e.message));
  $('rt-installer').onclick = () => installer('MesRetouches'); $('rt-retirer').onclick = () => rtRetirer().catch(e => majRapport('Erreur : ' + e.message)); });
// ------------------------------------------------------------------ (15/11/2026) COPIE D'UN PERSONNAGE (moteur/copies_persos.py)
async function cpExporter() {
  if (!E.tech || E.tech.onglet !== 'personnages') return majRapport('Ouvre d’abord un personnage (onglet Personnages).');
  const nom = $('cp-nom').value.trim(); if (!nom) return majRapport('Donne un nom au nouveau joueur.');
  const textures = {};
  for (const x of Object.values(E.textures)) if (x.modif && x.cur && x.obj && x.obj.nom === E.objets[0].nom) textures[x.nom] = x.cur.toDataURL('image/png');
  if (!Object.keys(textures).length) return majRapport('Rien n’est modifié : recolore d’abord la tête.');
  majRapport('Création de la copie « ' + nom + ' » (réencodage de ' + Object.keys(textures).length + ' texture(s))…');
  const r = await api('/api/copie_personnage', { code: E.tech.code, nom, description: $('cp-desc').value.trim(), textures, portrait: await photoIcone('visage') });
  majRapport(r.ok ? 'Copie créée (pas encore installée) : ' + r.dossier + '\n- ' + r.rapport.join('\n- ') + '\n« Installer dans le jeu », puis tirage Kizuna (ChronicleDeluxe).' : 'Erreur : ' + r.erreur);
  return r;                                   // (21/11) « Créer » enchaîne l'installation
}
window.addEventListener('load', () => { if (!$('cp-exporter')) return;
  $('cp-exporter').onclick = () => cpExporter().catch(e => majRapport('Erreur : ' + e.message)); $('cp-installer').onclick = () => installer('MesPersonnages'); });
// ------------------------------------------------------------------ (15/11/2026) COPIE D'ARMURE (moteur/armures_copies.py)
async function caListe() {
  const sel = $('ca-esprit'); if (!sel) return;
  let r = { copies: [] }; try { r = await api('/api/copies_esprits'); } catch (e) { /* serveur absent */ }
  sel.innerHTML = r.copies.length ? r.copies.map(c => `<option value="${echapper(c.code)}">${echapper(c.nom)} (copie de ${echapper(c.nom_base || c.base)})</option>`).join('')
    : '<option value="">Aucune copie d’esprit : crée-en une dans l’onglet Esprits guerriers</option>';
  if ($('ca-aucune')) { $('ca-aucune').style.display = r.copies.length ? 'none' : ''; $('ca-formulaire').style.display = r.copies.length ? '' : 'none'; }
}
window.addEventListener('load', () => { if ($('ca-vers-esprits')) $('ca-vers-esprits').onclick = () => {
  window.changerOnglet('esprits'); majRapport('Choisis un esprit guerrier en haut, recolore-le et crée-le : tu pourras ensuite lui faire une armure.'); }; });
async function caExporter() {
  if (!E.tech || E.tech.onglet !== 'armures') return majRapport('Ouvre d’abord une armure (onglet Armures).');
  if (!$('ca-esprit').value) return majRapport('Aucune copie d’esprit : crée-en d’abord une (onglet Esprits guerriers, « Créer le mod »).');
  const textures = {};
  for (const x of Object.values(E.textures)) if (x.modif && x.cur && x.obj && x.obj.nom === E.objets[0].nom) textures[x.nom] = x.cur.toDataURL('image/png');
  if (!Object.keys(textures).length) return majRapport('Rien n’est modifié : recolore d’abord l’armure.');
  majRapport('Création de l’armure (réencodage de ' + Object.keys(textures).length + ' texture(s))…');
  const r = await api('/api/copie_armure', { code: E.tech.code, esprit: $('ca-esprit').value, nom: $('ca-nom').value.trim(), textures });
  majRapport(r.ok ? 'Armure créée (pas encore installée) : ' + r.dossier + '\n- ' + r.rapport.join('\n- ') + '\n« Installer dans le jeu » (mod MesEsprits).' : 'Erreur : ' + r.erreur);
  return r;                                   // (21/11) « Créer » enchaîne l'installation
}
window.addEventListener('load', () => { if (!$('ca-exporter')) return;
  $('ca-exporter').onclick = () => caExporter().catch(e => majRapport('Erreur : ' + e.message)); $('ca-installer').onclick = () => installer('MesEsprits');
  });
// ------------------------------------------------------------------ (15/11/2026) COPIES DE TENUES ET D'OBJETS (moteur/copies_tenues.py)
function texturesModifiees() { const t = {};
  for (const x of Object.values(E.textures)) if (x.modif && x.cur && x.obj && x.obj.nom === E.objets[0].nom) t[x.nom] = x.cur.toDataURL('image/png'); return t; }
async function ctPreparer() {
  if (!E.tech) return;
  if (E.tech.onglet === 'tenues') { const sel = $('ct-porteur'); sel.innerHTML = '<option value="">Recherche de qui la porte…</option>';
    const r = await api('/api/porteurs?cat=tenues&code=' + encodeURIComponent(E.tech.code));
    // (15/11/2026) vêtement : copie = tenue à équiper ; chaussures, gants… : nouveau joueur ; corpulences : choix du maillage
    $('bloc-outfit').style.display = r.vetement ? '' : 'none'; $('bloc-nouveau-joueur').style.display = r.vetement ? 'none' : '';
    const C = r.corps || []; $('corps-bloc').style.display = C.length > 1 ? '' : 'none';
    $('corps-choix').innerHTML = C.map(c => `<option value="${echapper(c.modele)}"${c.modele === E.objets[0].chemin.split('|')[0] ? ' selected' : ''}>${echapper(c.libelle)}</option>`).join('');
    $('co-corps').textContent = C.length ? 'Corpulences : ' + C.map(c => c.libelle).join(' · ') : 'Une seule corpulence (celle du maillage du jeu).';
    // (15/11/2026) choix des corps qui peuvent la mettre
    const L = r.corps_tenue || [], lib = i => (L.find(c => c.ligne === i) || {}).libelle || 'corps ' + i;
    $('cu-corps').innerHTML = L.map(c => `<label class="${c.propre ? 'propre' : c.emprunt != null ? 'emprunt' : 'impossible'}" title="${c.nb} personnages">`
      + `<input type="checkbox" data-corps="${c.ligne}"${c.propre ? ' checked' : ''}${!c.propre && c.emprunt == null ? ' disabled' : ''}> ${echapper(c.libelle)}`
      + `<small>${c.propre ? 'sa version' : c.emprunt != null ? 'emprunte : ' + echapper(lib(c.emprunt)) : 'pas de version (autre squelette)'}</small></label>`).join('');
    sel.innerHTML = r.porteurs.length ? r.porteurs.map(p => `<option value="${echapper(p.code)}">${echapper(p.nom)} (${echapper(p.code)})</option>`).join('')
      : '<option value="">Aucun joueur ne porte cette tenue dans le jeu : pas de copie possible</option>'; }
  const acc = E.tech.onglet === 'tenues' && E.tech.genre === 'Accessoire';
  if (E.tech.onglet === 'tenues') { $('bloc-objet').style.display = acc ? 'block' : 'none'; if (acc) { $('bloc-outfit').style.display = 'none'; $('bloc-nouveau-joueur').style.display = 'none'; } }
  if (acc) { const r = await api('/api/porteurs?cat=tenues&code=' + encodeURIComponent(E.tech.code));
    $('co-etat').textContent = r.accessoire ? 'Cet objet est un accessoire : il peut être porté par un nouveau joueur.' : 'Cet objet n’est pas un accessoire porté par les personnages (véhicule, décor…) : pas de copie possible.';
    $('co-exporter').disabled = !r.accessoire;
    if (!$('co-tetes').children.length) { const l = E.jeu.personnages || (E.jeu.personnages = await api('/api/jeu?cat=personnages'));
      $('co-tetes').innerHTML = l.filter(p => p.nom !== p.code).map(p => `<option value="${echapper(p.nom)} · ${echapper(p.code)}"></option>`).join(''); } }
}
async function ctExporter() {
  if (!E.tech || E.tech.onglet !== 'tenues') return majRapport('Ouvre d’abord une tenue (onglet Tenues).');
  if (!$('ct-porteur').value) return majRapport('Aucun joueur ne porte cette tenue dans le jeu : pas de copie possible.');
  const textures = texturesModifiees(); if (!Object.keys(textures).length) return majRapport('Rien n’est modifié : recolore d’abord la tenue.');
  majRapport('Création du nouveau joueur…');
  const r = await api('/api/copie_tenue', { code: E.tech.code, porteur: $('ct-porteur').value, nom: $('ct-nom').value.trim(), description: $('ct-desc').value.trim(), textures });
  majRapport(r.ok ? 'Copie créée (pas encore installée) : ' + r.dossier + '\n- ' + r.rapport.join('\n- ') + '\n« Installer dans le jeu », puis tirage Kizuna (ChronicleDeluxe).' : 'Erreur : ' + r.erreur);
  return r;                                   // (21/11) « Créer » enchaîne l'installation
}
async function coExporter() {
  if (!E.tech || E.tech.genre !== 'Accessoire') return majRapport('Ouvre d’abord un accessoire (onglet Tenues, tri « Accessoire »).');
  const tete = ($('co-tete').value.split('·').pop() || '').trim(); if (!tete) return majRapport('Choisis le personnage qui portera l’objet.');
  const textures = texturesModifiees(); if (!Object.keys(textures).length) return majRapport('Rien n’est modifié : recolore d’abord l’objet.');
  majRapport('Création du nouveau joueur…');
  const r = await api('/api/copie_objet', { code: E.tech.code, tete, nom: $('co-nom').value.trim(), description: $('co-desc').value.trim(), textures });
  majRapport(r.ok ? 'Copie créée (pas encore installée) : ' + r.dossier + '\n- ' + r.rapport.join('\n- ') + '\n« Installer dans le jeu », puis tirage Kizuna (ChronicleDeluxe).' : 'Erreur : ' + r.erreur);
  return r;                                   // (21/11) « Créer » enchaîne l'installation
}
window.addEventListener('load', () => { if (!$('ct-exporter')) return;
  $('ct-exporter').onclick = () => ctExporter().catch(e => majRapport('Erreur : ' + e.message)); $('ct-installer').onclick = () => installer('MesPersonnages');
  $('co-exporter').onclick = () => coExporter().catch(e => majRapport('Erreur : ' + e.message)); $('co-installer').onclick = () => installer('MesPersonnages'); });
// (15/11/2026) CORPULENCE : autre maillage du même dossier, mêmes textures (les retouches restent)
async function changerCorpulence(md) {
  if (!E.tech) return; const t = await api('/api/personnage?code=' + encodeURIComponent(E.tech.code) + '&cat=' + E.tech.onglet + '&modele=' + encodeURIComponent(md));
  const o = E.objets[0], o2 = t.objets_details[0]; o.pieces = o2.pieces; o.chemin = o2.chemin;
  await chargerGeometries(true); E.vue.recadrer(true); teintesPieces(); dessinerPieces(); apresRetouche(); if (window.zonesPreparer) zonesPreparer();
  majRapport('Corpulence : ' + $('corps-choix').selectedOptions[0].textContent + ' (mêmes textures).');
}
async function cuExporter() {
  if (!E.tech || E.tech.onglet !== 'tenues') return majRapport('Ouvre d’abord une tenue (onglet Tenues).');
  const textures = texturesModifiees(); if (!Object.keys(textures).length) return majRapport('Rien n’est modifié : recolore d’abord la tenue.');
  majRapport('Création de la tenue…');
  const corps = [...document.querySelectorAll('#cu-corps [data-corps]:checked')].map(c => +c.dataset.corps);
  if (!corps.length) return majRapport('Coche au moins une corpulence (« Qui peut la mettre ? »).');
  const r = await api('/api/copie_outfit', { code: E.tech.code, nom: $('cu-nom').value.trim(), description: $('cu-desc').value.trim(), prix: +$('cu-prix').value || 28, textures, icone: E.cuIcone || null, corps });
  majRapport(r.ok ? 'Tenue créée (pas encore installée) : ' + r.dossier + '\n- ' + r.rapport.join('\n- ') + '\n« Installer dans le jeu » (mod MesTenues).' : 'Erreur : ' + r.erreur);
  return r;                                   // (21/11) « Créer » enchaîne l'installation
}
window.addEventListener('load', () => { if (!$('cu-exporter')) return;
  $('cu-exporter').onclick = () => cuExporter().catch(e => majRapport('Erreur : ' + e.message)); $('cu-installer').onclick = () => installer('MesTenues');
  $('corps-choix').onchange = () => changerCorpulence($('corps-choix').value).catch(e => majRapport('Erreur : ' + e.message));
  $('cu-icone').onchange = () => { const f = $('cu-icone').files[0]; if (!f) return; const lr = new FileReader(); lr.onload = () => { E.cuIcone = lr.result; $('cu-icone-img').src = lr.result; }; lr.readAsDataURL(f); }; });
// ------------------------------------------------------------------ (15/11/2026) OBJETS DU JEU (moteur/objets_jeu.py)
function ojTexture() { const o = E.objets[0]; const t = o && o.textures && o.textures[0]; return t ? E.textures[o.nom + '/' + t.nom] : null; }
function ojIcone() { const x = ojTexture(), img = $('objet-grand-img');
  if (x && x.cur) { img.src = x.cur.toDataURL('image/png'); $('objet-grand-txt').textContent = ''; return; }
  // (15/11/2026) pas d'image dans les fichiers du jeu (titres, autocollants, synergies…) : une carte avec son nom
  const c = document.createElement('canvas'); c.width = 512; c.height = 256; const g = c.getContext('2d');
  const d = g.createLinearGradient(0, 0, 512, 256); d.addColorStop(0, '#2b3350'); d.addColorStop(1, '#151a28'); g.fillStyle = d; g.fillRect(0, 0, 512, 256);
  g.strokeStyle = '#ffc83d'; g.lineWidth = 6; g.strokeRect(8, 8, 496, 240); g.fillStyle = '#f2f4f8'; g.font = 'bold 30px Segoe UI'; g.textAlign = 'center';
  const mots = (E.tech ? E.tech.nom : '').split(' '); let l = '', y = 110; const lignes = [];
  for (const m of mots) { if (g.measureText(l + ' ' + m).width > 440 && l) { lignes.push(l); l = m; } else l = (l ? l + ' ' : '') + m; } lignes.push(l);
  lignes.slice(0, 3).forEach((t, k) => g.fillText(t, 256, y + k * 38 - (lignes.length - 1) * 19));
  g.fillStyle = '#9aa3b5'; g.font = '18px Segoe UI'; g.fillText(E.tech ? E.tech.genre : '', 256, 225);
  img.src = c.toDataURL('image/png'); $('objet-grand-txt').textContent = 'Pas d’image dans les fichiers du jeu : le jeu l’affiche en texte.';
}
function ojPreparer() {
  const t = E.tech; $('oj-nom').textContent = t.nom; $('oj-genre').textContent = t.genre + ' · ' + t.code; $('oj-desc').textContent = t.description || '(pas de description)';
  $('oj-nom-copie').value = t.nom + ' (copie)'; $('oj-desc-copie').value = t.description || '';
  $('oj-formulaire').style.display = '';                 // (15/11/2026) copie pour TOUS les objets (VRFW : la base suffit)
  const ic = t.icone, fichier = ic && /\/(01_icon_emblem|25_icon_nameplate)$/.test(ic.fichier.replace(/\/[^/]*$/, ''));
  $('oj-etat').textContent = 'Un NOUVEL objet : ton nom, ta description, ton prix ; les mêmes effets que « ' + t.nom + ' ». L’original ne change pas. '
    + (!ic ? 'Pas d’image dans le jeu pour ce genre d’objet : la copie s’affiche en texte, comme l’original.'
      : ic.nb > 1 || fichier ? 'Son icône : celle que tu recolores (✎ Mode dessin).' : 'Son icône : celle de l’original (ce genre d’icône ne se remplace pas encore).');
  ojIcone();
}
async function ojExporter() {
  if (!E.tech || E.tech.onglet !== 'objets') return majRapport('Ouvre d’abord un objet du jeu (onglet Objets).');
  const x = ojTexture();
  majRapport('Création de la copie…');
  const r = await api('/api/copie_objet_jeu', { code: E.tech.code, nom: $('oj-nom-copie').value.trim(), description: $('oj-desc-copie').value, prix: +$('oj-prix').value || 10, icone: x && x.cur ? x.cur.toDataURL('image/png') : null });
  majRapport(r.ok ? 'Objet créé (pas encore installé) : ' + r.dossier + '\n- ' + r.rapport.join('\n- ') + '\n« Installer dans le jeu » (mod MesObjets).' : 'Erreur : ' + r.erreur);
  return r;                                   // (21/11) « Créer » enchaîne l'installation
}
window.addEventListener('load', () => { if (!$('oj-exporter')) return;
  $('oj-exporter').onclick = () => ojExporter().catch(e => majRapport('Erreur : ' + e.message)); $('oj-installer').onclick = () => installer('MesObjets'); });
async function installer(mod) {
  majRapport('Installation…');
  try { let r = await api('/api/installer', { mod: mod || 'MesTechniques' });
    // (21/11) le mod du jeu a des créations absentes de cet Atelier (autre dossier, autre PC) : installer les retirerait
    if (!r.ok && r.perdus && r.perdus.length) {
      if (!confirm(`Installer remplace le mod ${mod} du jeu. Ces créations n'existent pas dans cet Atelier et seront retirées du jeu :\n`
        + r.perdus.map(n => '- ' + n).join('\n') + '\n\n(une sauvegarde est faite avant ; « Annuler » pour ne rien changer)\nContinuer ?')) return majRapport('Installation annulée : rien n’a changé.');
      r = await api('/api/installer', { mod: mod || 'MesTechniques', forcer: true }); }
    // (21/11) 1re ligne : où la trouver en jeu (textes de l'Atelier : OU_EN_JEU) ; le reste = détails (repliés en mode simple)
    majRapport(r.ok ? 'C’est dans le jeu ! ' + (OU_EN_JEU[mod || 'MesTechniques'] || '') + ' (Relance le jeu s’il était ouvert.)'
                      + (r.avertissement ? '\n⚠ ' + r.avertissement : '')
                      + '\nInstallé dans ' + r.dossier + '\nSauvegarde : ' + r.sauvegarde + '\nLance le jeu, puis regarde le journal de VRFW (aucune ligne ERROR).'
                    : 'Pas installé : ' + r.erreur);
    return r;
  } catch (e) { majRapport('Erreur : ' + e.message); }
}
// (21/11) où trouver chaque création en jeu : repris des textes de l'Atelier et de ses mods (export.py : boutique des supertechniques
// d'Inazuma Fantasy ; esprits.py : boutique d'entraînement ; copies_persos.py : tirage Kizuna de ChronicleDeluxe ; objets_jeu.py et
// atelier_mod.py : boutique générale ; copies_outfits.py : tenue en boutique, à équiper ; armures_copies.py : forme en armure de l'esprit)
const OU_EN_JEU = {
  MesTechniques: 'Ta technique est en vente à la boutique des supertechniques d’Inazuma Fantasy.',
  MesEsprits: 'Ton esprit guerrier / totem est en vente à la boutique d’entraînement d’Inazuma Fantasy (une armure devient la forme en armure de son esprit).',
  MesPersonnages: 'Ton nouveau joueur t’attend au tirage Kizuna (ChronicleDeluxe).',
  MesTenues: 'Ta tenue est en vente en boutique : équipe-la à un joueur comme les tenues du jeu.',
  MesObjets: 'Ton objet est en vente à la boutique générale d’Inazuma Fantasy.',
  MesMaillots: 'Ton maillot est en vente à la boutique générale d’Inazuma Fantasy.',
};

// ------------------------------------------------------------------ animation de la cinématique
async function chargerAnimation(t) {
  $('l-info').textContent = 'Lecture de l\'animation…';
  const d = await api('/api/anim?code=' + t.code);
  if (E.tech !== t) return;                                       // une autre technique a été ouverte entre-temps
  try { E.telopV = (await api('/api/telop_apercu_version?tech=' + encodeURIComponent(t.code) + '&projet=' + encodeURIComponent(E.projet || ''))).v; } catch (e) { }   // bannière perso à jour
  const L = new Lecteur(d);
  E.vue.lumieresDefs = [];                                          // lumières ponctuelles (CCustomPointLight) des objets de l'effet
  for (const o of E.objets) { if (o.erreur || !L.objets[o.acteur]) continue;
    const sq = L.objets[o.acteur].sq;
    for (const p of o.pieces) if (p.vue) { p.vue.anim = { acteur: o.acteur, os: sq.parNom[p.nom], mat: p.mat_crc >>> 0, uv: p.uv_crc >>> 0 };
      if (p.peau && p.vue.peauCPU) p.vue.anim.peau = p.peau.map(n => sq.parNom[n]);    // os de la palette -> n° dans le squelette
      if (o.commun) p.vue.surEcran = true; }
    ajouterEmetteurs(o); for (const v of o.emetteursVue) v.visible = !$('l-particules') || $('l-particules').checked;
    { const tp = (!E.avant && (E.teintePtl || {})[o.nom]) || null; for (const v of o.emetteursVue) v.teintePtl = tp ? [tp.H, tp.C] : null; }
    // (+ CCustomShaderParam : valeurs prises sur les os recopiées dans les u_shaderParam des matériaux)
    if (o.lumieres && ((o.lumieres.lumieres || []).length || (o.lumieres.shader || []).length)) E.vue.lumieresDefs.push({ acteur: o.acteur, def: o.lumieres }); }
  // (ancien ballon rigide : remplacé par les acteurs avec os)
  if (false && d.balle) { try { const buf = await api('/api/geometrie?chemin=' + encodeURIComponent('common/chr/b000001/b000001.objbin'));
    const dv = new DataView(buf), lg = dv.getUint32(0, true), meta = JSON.parse(new TextDecoder().decode(new Uint8Array(buf, 4, lg))); let p = 4 + lg;
    meta.forEach((m, i) => { const pos = new Float32Array(buf.slice(p, p + m.nv * 12)); p += m.nv * 12; const col = new Uint8Array(buf.slice(p, p + m.nv * 4)); p += m.nv * 4;
      const uv = new Float32Array(buf.slice(p, p + m.nv * 8)); p += m.nv * 8; const idx = new Uint16Array(buf.slice(p, p + m.ni * 2)); p += m.ni * 2 + ((4 - (m.ni * 2) % 4) % 4);
      const v = E.vue.ajouter('balle/' + i, { nv: m.nv, ni: m.ni, pos, col, idx, uv }); v.balle = true; v.opaque = true; v.teinte = [1, 1, 1, 1]; }); } catch (e) { /* pas de ballon */ } }
  // acteurs avec os : le joueur (modèle générique), l'esprit / le totem, les objets, le ballon
  const deja = {};
  // personnage : le 1er qui a la technique (choix dans la barre) ; sa corpulence choisit squelette + gestes
  const sel = $('l-perso'); sel.innerHTML = '';
  // un seul joueur : mannequin entièrement noir (choix de l'utilisateur, 13/11/2026 : plus de choix du personnage)
  const o0 = document.createElement('option'); o0.value = ''; o0.textContent = 'Joueur noir'; o0.dataset.corps = 1; sel.appendChild(o0); sel.value = '';
  sel.style.display = 'none';
  const corps = +(sel.selectedOptions[0] ? sel.selectedOptions[0].dataset.corps : 1) || 1;
  for (const a of d.acteurs || []) if (a.modele === 'joueur' && a.corps && a.corps[corps]) { a.os = a.corps[corps].os; a.clips = a.corps[corps].clips; if (a.corps[corps].collision) a.collision = a.corps[corps].collision; a.nus = a.corps[corps].nus; a.g4sk = a.corps[corps].g4sk; }
  L.acteurs = (d.acteurs || []).map(a => { const sq = new Squelette(a.os, a); return { d: a, sq, invRepos: sq.mondeRepos.map(Anim3D.inverse) }; });
  E.acteursSrc = {};          // acteur -> modèle chargé (rendu Direct3D : le serveur retrouve ses matériaux et sommets)
  for (const a of d.acteurs || []) { E.acteursSrc[a.acteur] = a.modele === 'joueur' ? { quoi: 'joueur', code: sel.value } : { quoi: 'chr', code: a.code };
    const url = a.modele === 'joueur' ? '/api/modele?quoi=joueur&code=' + encodeURIComponent(sel.value) : '/api/modele?quoi=chr&code=' + a.code;
    try { await chargerPeau(url, a.acteur); } catch (e) { majRapport(a.code + ' non chargé : ' + e.message); } }
  if (E.tech !== t) return;
  // décor : le vrai stade (Raimon, s10g001), sinon le terrain dessiné
  try { await chargerStade('s10g001'); } catch (e) { majRapport('Stade non chargé (' + e.message + ') : terrain dessiné à la place.'); Terrain.ajouter(E.vue); }
  E.lecteur = L; E.vue.image = 0; E.vue.joue = false; chargerSons(d); E.vue.vitesse = +$('l-vitesse').value; E.vue.boucle = $('l-boucle').checked;
  E.vue.cameraJeu = $('l-camera').checked;
  if ($('l-anim').checked) activerAnimation(true);
  $('l-image').max = L.duree - 1;
  majRapport(`Animation : ${d.plans.length} plan(s), ${L.duree} images (${(L.duree / 60).toFixed(1).replace('.', ',')} s). ▶ pour lancer.`);
}
async function chargerPeau(url, acteur) {
  const buf = await api(url), dv = new DataView(buf), lg = dv.getUint32(0, true);
  const meta = JSON.parse(new TextDecoder().decode(new Uint8Array(buf, 4, lg))); let p = 4 + lg;
  // (21/11, LU nie.exe — remplace la règle DÉDUITE du 15/11 « _s00 -> 1re version, _s80 -> 2e ») toutes les pièces sont
  // dessinées ; leur ORDRE est celui du jeu (ordrePieces, même tri que le lecteur natif) : de deux maillages superposés (dragon
  // clair / sombre de Choc de la vouivre), le jeu garde le DERNIER dessiné (passe couleur en profondeur EQUAL). La vue WebGL n'a
  // pas de passe de profondeur préalable (test LESS : le PREMIER dessiné l'emporte) : elle dessine donc ces pièces en ordre INVERSE.
  const cacher = new Set();
  for (const [i, m] of meta.entries()) {
    const pos = new Float32Array(buf.slice(p, p + m.nv * 12)); p += m.nv * 12;
    const normales = new Float32Array(buf.slice(p, p + m.nv * 12)); p += m.nv * 12;
    const uv = new Float32Array(buf.slice(p, p + m.nv * 8)); p += m.nv * 8;
    const os = new Uint16Array(buf.slice(p, p + m.nv * 8)); p += m.nv * 8;
    const poids = new Float32Array(buf.slice(p, p + m.nv * 16)); p += m.nv * 16;
    const idx = new Uint16Array(buf.slice(p, p + m.ni * 2)); p += m.ni * 2 + ((4 - (m.ni * 2) % 4) % 4);
    const v = E.vue.ajouterPeau(acteur + '/' + i, { nv: m.nv, ni: m.ni, pos, uv, os, poids, idx, normales, contour: m.contour,
      ombreCle: m.ombre ? 'peau:' + m.ombre : null, noir: m.noir }, acteur);
    if (cacher.has(i)) { v.visible = false; v.versionCachee = true; }
    if (m.texture) { (cacher.has(i) ? (E.texturesCachees = E.texturesCachees || new Set()) : (E.texturesMontrees = E.texturesMontrees || new Set())).add(m.texture);
      if (cacher.size) dessinerTextures(); }
    if (m.ombre && !E.vue.textures['peau:' + m.ombre]) { try { const im = await chargerImage('/tex/' + m.ombre + '.png'); const c2 = document.createElement('canvas');
      c2.width = im.width; c2.height = im.height; c2.getContext('2d').drawImage(im, 0, 0); E.vue.texture('peau:' + m.ombre, c2); } catch (e) { /* pas de carte d'ombres */ } }
    // (15/11/2026) texture retouchée dans l'Atelier (même clé « objet/nom ») : c'est elle qu'on montre (avant : toujours l'originale)
    if (m.texture && E.textures[m.texture] && E.textures[m.texture].cur) { E.vue.texture('peau:' + m.texture, texAffichee(E.textures[m.texture])); v.texCle = 'peau:' + m.texture; }
    else if (m.texture) { try { const img = await chargerImage('/tex/' + m.texture + '.png'); const cv = document.createElement('canvas');
      cv.width = img.width; cv.height = img.height; cv.getContext('2d').drawImage(img, 0, 0); E.vue.texture('peau:' + m.texture, cv); v.texCle = 'peau:' + m.texture; } catch (e) { /* sans texture */ } }
  }
  // ordre de dessin (voir plus haut) : les pièces de cet acteur reprennent leurs places dans E.vue.pieces, en ordre jeu inversé
  if (meta.some(m => m.cle != null)) {
    const voulu = ordrePieces(meta.map(m => m.cle >>> 0), meta.map(m => m.seau | 0), meta.length).reverse().map(i => acteur + '/' + i);
    const P = E.vue.pieces, places = [], parCle = new Map();
    P.forEach((q, k) => { if (q.cle && voulu.includes(q.cle)) { places.push(k); parCle.set(q.cle, q); } });
    if (places.length === voulu.length) voulu.forEach((c, j) => { P[places[j]] = parCle.get(c); });
  }
}
// (21/11, LU nie.exe) ordre de dessin des pièces d'un modèle : 0x140591fc0 les ajoute de 0 à n-1, chacune dans le seau « octet +8 de
// la fiche de son matériau », triée par 0x140591d60 (portée telle quelle, comme AtelierNatif/src/technique.h ordre_pieces) : clé = entier
// G4MD +0x72 du matériau, valeur = profondeur du modèle (la même pour toutes ses pièces). Seaux dans l'ordre de leur 1re apparition.
function ordrePieces(cle, seau, n) {
  const out = [], seaux = [];
  for (let i = 0; i < n; i++) if (!seaux.includes(seau[i] || 0)) seaux.push(seau[i] || 0);
  for (const s of seaux) {
    const prv = new Array(n).fill(-1), nxt = new Array(n).fill(-1); let tete = -1, queue = -1;
    const K = i => cle[i] >>> 0;
    const avant = (c, x) => { const p = prv[c]; prv[c] = x; nxt[x] = c; prv[x] = p; if (p >= 0) nxt[p] = x; else tete = x; };
    const apres = (c, x) => { const q = nxt[c]; nxt[c] = x; prv[x] = c; nxt[x] = q; if (q >= 0) prv[q] = x; else queue = x; };
    const retirer = c => { const p = prv[c], q = nxt[c]; if (q >= 0) prv[q] = p; else queue = p; if (p >= 0) nxt[p] = q; else tete = q; prv[c] = nxt[c] = -1; };
    for (let x = 0; x < n; x++) {
      if ((seau[x] || 0) !== s) continue;
      let cur = tete, deplace = -1, k5 = 0, fait = false;
      while (cur >= 0) {
        const k3 = K(cur);
        if (deplace < 0) {
          if (k3 === K(x)) { avant(cur, x); fait = true; break; }
          else if (k3 !== k5) { avant(cur, x); deplace = x; cur = x; }
        } else if (k3 === K(x)) {
          let c = cur; while (c >= 0) { if (K(c) !== K(x)) break; const q = nxt[c]; retirer(c); apres(deplace, c); deplace = c; c = q; }
          fait = true; break;
        }
        k5 = K(cur); cur = nxt[cur];
      }
      if (fait || deplace >= 0) continue;
      if (queue < 0) { tete = queue = x; prv[x] = nxt[x] = -1; } else apres(queue, x);
    }
    for (let c = tete; c >= 0; c = nxt[c]) out.push(c);
  }
  return out;
}
// bannière par-dessus la cinématique : entrée en grossissant, sortie en fondu (celle de l'éditeur si tu en as fait une)
function majTelop(f) {
  const el = $('l-telop'), t = E.lecteur && E.lecteur.d.telop;
  // (14/11/2026) courbes du modèle de menu du jeu (soccer10_01) comme le lecteur natif : entrée à 30 images/s dès « montrée »,
  // sortie à 60 images/s dès « cachée » (MESURÉ sur les vidéos) ; avant : zoom 1,35 -> 1 approché
  const C = t && t.courbes, fin = t && t.fin != null ? t.fin : Infinity;
  const val = (k, u, d) => { if (!k || !k.length) return d; if (u <= k[0][0]) return k[0][1]; if (u >= k[k.length - 1][0]) return k[k.length - 1][1];
    for (let i = 1; i < k.length; i++) if (u < k[i][0]) return k[i - 1][1] + (k[i][1] - k[i - 1][1]) * (u - k[i - 1][0]) / (k[i][0] - k[i - 1][0]); return d; };
  const sortie = C && f >= fin ? (f - fin) * (t.vitesse_out || 1) : null;
  if (!t || !E.vue.lecteur || !$('l-banniere').checked || f < t.debut || (f >= fin && (!C || sortie > 10))) { el.style.display = 'none'; return; }
  // (21/11) bannière perso (onglet Bannières ou copie déjà créée) si elle existe, sinon celle du jeu ; v : date de la perso
  // (21/11, retour de muku) la bannière perso est celle du PROJET ouvert : la technique du jeu ouverte sans lui montre la vraie
  const src = E.banniereImage && E.tech && E.banniereImage.projet === E.projet ? E.banniereImage.image
    : '/api/telop_apercu?tech=' + encodeURIComponent(E.tech ? E.tech.code : '') + '&telop=' + encodeURIComponent(t.code) + '&projet=' + encodeURIComponent(E.projet || '') + '&v=' + (E.telopV || 0);
  if (el.dataset.src !== src) { el.src = src; el.dataset.src = src; }
  let s, op;
  if (C) { if (sortie === null) { const u = (f - t.debut) * (t.vitesse_in || 0.5); s = val(C.echelle_in, u, 1); op = val(C.fondu_in, u, 1); }
           else { s = val(C.echelle_out, sortie, 1); op = val(C.fondu_out, sortie, 0); } }
  else { const d = f - t.debut, r = t.fin != null ? t.fin - f : 99, e = Math.min(1, d / 8); s = 1.35 - 0.35 * (1 - Math.pow(1 - e, 3)); op = Math.min(e * 1.5, r / 10, 1); }
  el.style.display = 'block'; el.style.opacity = Math.max(0, Math.min(op, 1));
  el.style.transform = `translateX(-50%) scale(${s.toFixed(3)})`;
}
async function chargerStade(code) {
  E.stadeCode = code;
  $('l-info').textContent = 'Chargement du stade…';
  const buf = await api('/api/carte?code=' + code), dv = new DataView(buf), lg = dv.getUint32(0, true);
  const meta = JSON.parse(new TextDecoder().decode(new Uint8Array(buf, 4, lg))); let p = 4 + lg;
  const vues = {};
  for (const [i, m] of meta.entries()) {
    const pos = new Float32Array(buf.slice(p, p + m.nv * 12)); p += m.nv * 12;
    const col = new Uint8Array(buf.slice(p, p + m.nv * 4)); p += m.nv * 4;
    const uv = new Float32Array(buf.slice(p, p + m.nv * 8)); p += m.nv * 8;
    const idx = new Uint16Array(buf.slice(p, p + m.ni * 2)); p += m.ni * 2 + ((4 - (m.ni * 2) % 4) % 4);
    let nor = null; if (m.n) { nor = new Float32Array(buf.slice(p, p + m.nv * 12)); p += m.nv * 12; }   // normales (lumières ponctuelles)
    let tan4 = null; if (m.t) { tan4 = new Float32Array(buf.slice(p, p + m.nv * 16)); p += m.nv * 16; }  // tangentes (vrai shader du stade)
    if (!m.texture) continue;                 // maillages sans texture : volumes cachés du jeu (ombres, collisions) -> pas affichés
    const v = E.vue.ajouter('stade/' + i, { nv: m.nv, ni: m.ni, pos, col, uv, idx, nor, tan4 });
    if (m.jeu) { v.jeuStade = m.jeu; for (const k of m.jeu.tex) if (k && !vues[k]) vues[k] = []; }
    v.terrain = true; v.opaque = true; v.teinte = [1.25, 1.25, 1.25, 1];
    if (m.texture) { v.texCle = 'stade:' + m.texture; (vues[m.texture] = vues[m.texture] || []).push(v); }
  }
  // textures du stade (chargées en parallèle)
  await Promise.all(Object.keys(vues).map(async t => { try { const img = await chargerImage('/tex/' + t + '.png'); const cv = document.createElement('canvas');
    E.vue.texture('stade:' + t, img); } catch (e) { /* sans texture */ } }));   // image directe : pas de pré-multiplication (alpha = métal des cartes de relief)
  // cubemap HDR du stade (reflets du vrai shader)
  try { const b = await api('/api/cubemap?code=' + code), dv2 = new DataView(b), lg2 = dv2.getUint32(0, true);
    const me = JSON.parse(new TextDecoder().decode(new Uint8Array(b, 4, lg2))); E.vue.cubemap(me, new Uint8Array(b, 4 + lg2)); } catch (e) { console.warn('cubemap', e); }
}
// son : bruitages de la technique + voix du personnage choisi, calés sur les images
const SON = { pistes: [], joue: false, image: 0 };
function chargerSons(d) {
  for (const s of SON.pistes) s.audio.pause();
  SON.pistes = [];
  const perso = $('l-perso').value;
  for (const s of d.sons || []) {
    if (s.voix && !perso) continue;
    const a = new Audio('/api/son?nom=' + encodeURIComponent(s.nom) + (s.voix ? '&perso=' + encodeURIComponent(perso) : ''));
    a.preload = 'auto'; a.onerror = () => { s.absent = true; };
    SON.pistes.push({ s, audio: a });
  }
}
function majSon(f) {
  const marche = E.vue.lecteur && E.vue.joue && $('l-son').checked;
  for (const p of SON.pistes) {
    if (p.s.absent) continue;
    const t = (f - p.s.image) / 60, a = p.audio;
    const doitJouer = marche && t >= 0 && (!a.duration || t < a.duration);
    if (doitJouer) {
      a.playbackRate = E.vue.vitesse || 1;
      if (a.paused) { try { a.currentTime = Math.max(0, t); } catch (e) { /* pas encore chargé */ } a.play().catch(() => {}); }
      else if (Math.abs(a.currentTime - t) > 0.25) a.currentTime = Math.max(0, t);     // recalage (saut, boucle)
    } else if (!a.paused) a.pause();
  }
}
function activerAnimation(oui) {
  if (!E.lecteur) return;
  E.vue.lecteur = oui ? E.lecteur : null;
  // pendant l'animation, la caméra du jeu cadre tout : on remet les pièces géantes (fonds, flashs)
  for (const p of E.vue.pieces) if (oui && !p.balle) p.visible = !p.versionCachee;
  for (const p of E.vue.pieces) if (p.balle || p.peau) p.visible = oui && !p.versionCachee;   // (15/11/2026) une version par objet
  for (const p of E.vue.pieces) if (p.terrain) p.visible = oui && $('l-terrain').checked;
  $('vue').classList.toggle('ciel', oui && $('l-terrain').checked);
  $('lecteur').classList.toggle('inactif', !oui); dessinerPieces();
}

// ------------------------------------------------------------------ bannières
const B = { ed: null, choix: null, liste: [] };
async function dessinerBanniere() {
  try {
    B.ed.manquante = null; await B.ed.dessiner();
    if (B.ed.manquante) $('b-rapport').textContent = `Police absente de ce PC : ${B.ed.manquante} (Impact utilisée à la place).`;
  } catch (e) { $('b-rapport').textContent = 'Police : ' + e.message; }
}
function reglagesBanniere() {
  const p = B.ed.p;
  for (const k of ['texte', 'haut', 'milieu', 'bas', 'c1', 'c2', 'ombre', 'lueur']) $('b-' + k).value = p[k];
  $('b-police').value = p.police;
  for (const k of ['taille', 'espacement', 'saute', 'tourne', 'x', 'y', 'e1', 'e2', 'ombreX', 'ombreY', 'lueurT']) $('b-' + k).value = p[k];
  $('b-penche').value = Math.round(p.penche * 100); $('b-ombreA').value = Math.round(p.ombreA * 100);
}
async function ouvrirBannieres() {
  if (!B.ed) {
    B.ed = new EditeurBanniere($('b-vue'));
    let dispo = null;                                   // polices présentes sur ce PC : seules celles-là sont proposées
    try { dispo = new Set(await api('/api/polices')); } catch (e) { }
    for (const [f, n] of EditeurBanniere.polices()) {
      if (dispo && !dispo.has(f.toLowerCase())) continue;
      const o = document.createElement('option'); o.value = f; o.textContent = n; $('b-police').appendChild(o); }
    if (window.brancherPolices) brancherPolices($('b-police'), p => p.fichier);       // (22/11) polices importées
    for (const [n, st] of Object.entries(EditeurBanniere.styles())) { const b = document.createElement('button'); b.textContent = n;
      b.onclick = () => { Object.assign(B.ed.p, st); reglagesBanniere(); dessinerBanniere(); }; $('b-styles').appendChild(b); }
    const num = { penche: v => v / 100, ombreA: v => v / 100 };
    document.querySelectorAll('#b-reglages input, #b-reglages select').forEach(el => el.addEventListener('input', () => {
      const k = el.id.slice(2); B.ed.p[k] = el.type === 'range' ? (num[k] ? num[k](+el.value) : +el.value) : el.value; dessinerBanniere(); }));
    $('b-graine').onclick = () => { B.ed.p.graine = Math.floor(Math.random() * 1e6); dessinerBanniere(); };
    $('b-utiliser').onclick = () => {
      if (!E.tech || E.tech.perso) return $('b-rapport').textContent = "Ouvre d'abord une technique dans l'onglet Techniques.";
      E.banniereImage = { code: E.tech.code, projet: E.projet, image: B.ed.image() };
      // (22/11) appliquée tout de suite (aperçu web ET lecteur natif ouvert, sans recharger), puis retour à la technique
      $('b-rapport').textContent = 'Application…';
      api('/api/banniere_apercu', { code: E.tech.code, projet: E.projet, image: E.banniereImage.image })
        .then(() => { E.telopV = Date.now(); window.changerOnglet('techniques');
          majRapport('Bannière appliquée : tu la vois dans l’aperçu de la technique. Elle partira avec « Créer ».'); })
        .catch(e => { $('b-rapport').textContent = 'Erreur : ' + e.message; }); };
    $('b-enregistrer').onclick = async () => {
      if (!B.choix || B.choix.ouverte) return $('b-rapport').textContent = 'Choisis à gauche une copie déjà créée.';
      $('b-rapport').textContent = 'Enregistrement…';
      try { const r = await api('/api/banniere', { nom: B.choix.nom, base: B.choix.base, image: B.ed.image() }); E.telopV = Date.now();
        $('b-rapport').textContent = r.ok ? r.rapport.join('\n') : 'Erreur : ' + r.erreur; } catch (e) { $('b-rapport').textContent = 'Erreur : ' + e.message; } };
    reglagesBanniere();
  }
  // choix : la technique ouverte + les copies déjà créées
  const etat = await api('/api/etat');
  B.liste = [];
  if (E.tech && !E.tech.perso) B.liste.push({ ouverte: true, titre: 'Technique ouverte : ' + E.tech.nom, base: E.tech.code, texte: $('f-nom').value || E.tech.nom });
  for (const [nom, v] of Object.entries(etat.deja || {})) B.liste.push({ nom, titre: v.nom, sous: v.key + ' · copie de ' + v.base, base: v.base, texte: v.nom });
  const box = $('b-choix'); box.innerHTML = '';
  if (!B.liste.length) box.innerHTML = '<p class="aide">Ouvre une technique (onglet Techniques) ou crée d\'abord une copie.</p>';
  B.liste.forEach(c => { const d = document.createElement('div'); d.innerHTML = `${c.titre}${c.sous ? `<small>${c.sous}</small>` : ''}`;
    d.onclick = () => choisirBanniere(c, d); box.appendChild(d); });
  if (B.liste.length) choisirBanniere(B.liste[0], box.firstChild); else dessinerBanniere();
}
function choisirBanniere(c, el) {
  B.choix = c; document.querySelectorAll('#b-choix div').forEach(x => x.classList.toggle('sel', x === el));
  B.ed.p.texte = c.texte; $('b-texte').value = c.texte;
  $('b-modele').src = '/api/telop_png?code=' + encodeURIComponent(c.base);
  // (22/11, retour de muku : « pas intuitif ») UN seul bouton, selon ce qui est choisi à gauche, avec le nom écrit dessus
  // (avant : « Utiliser pour la technique ouverte » et « Enregistrer dans la copie choisie » côte à côte, faciles à confondre)
  const u = $('b-utiliser'), en = $('b-enregistrer');
  u.style.display = c.ouverte ? '' : 'none'; en.style.display = c.ouverte ? 'none' : '';
  en.classList.add('primaire');
  if (c.ouverte && E.tech) u.textContent = 'Utiliser pour « ' + E.tech.nom + ' » et revenir à la technique';
  else en.textContent = 'Enregistrer dans ma copie « ' + c.titre + ' »';
  dessinerBanniere();
}

// (21/11) le texte de la bannière suit le nom de la technique tant qu'on ne l'a pas changé soi-même (avant : on renommait
// « Tornade Éloïse » et la bannière restait « TORNADE DE FEU COULEURS »)
window.addEventListener('load', () => { if ($('f-ban-perso')) $('f-ban-perso').onclick = () => window.changerOnglet('bannieres'); });   // (22/11) bannière depuis la technique
window.addEventListener('load', () => { const n = $('f-nom'), b = $('f-ban'); if (!n || !b) return; let prec = n.value;
  n.addEventListener('focus', () => { prec = n.value; });
  n.addEventListener('input', () => { const v = b.value.trim();
    if (!v || v === E.banAuto || v === prec.trim().toUpperCase()) { b.value = E.banAuto = n.value.trim().toUpperCase(); b.dispatchEvent(new Event('input')); }
    prec = n.value; }); });
// ------------------------------------------------------------------ démarrage
window.addEventListener('load', async () => {
  E.vue = new Vue3D($('vue')); E.vue.surChoix = (cle, ajout) => choisirDepuisVue(cle, ajout);   // (15/11/2026) clic sur l'aperçu
  E.index = await api('/api/techniques');
  E.persos = await api('/api/personnages'); E.jeu = {};
  const cherche = $('cherche'), res = $('resultats');
  // (17/11/2026, retour de muku : « quand il y a une technique devant on voit plus rien ») le lecteur natif est une vraie
  // fenêtre posée sur la vue : elle passe devant la liste des résultats -> cachée tant que la liste est ouverte
  // (commandes « cacher » / « montrer » du lecteur, AtelierNatif/src/incruste.h)
  new MutationObserver(majCacheNatif).observe(res, { attributes: true, attributeFilter: ['style'] });
  const changerOnglet = o => {
    if (E.onglet !== o) { E.filtreSource = null; E.filtreSerie = null; }   // (17/11/2026) filtres Jeu / Mods et série : par onglet
    E.onglet = o; const simple_ = document.body.classList.contains('mode-simple'); document.body.className = 'onglet-' + o + (simple_ ? ' mode-simple' : '');   // (21/11) garde le mode simple
    document.querySelectorAll('.onglets button').forEach(b => b.classList.toggle('actif', b.dataset.onglet === o));
    const c = ONGLETS[o]; cherche.placeholder = c.cherche; cherche.value = ''; res.style.display = 'none';
    $('titre-pieces').textContent = c.pieces; $('titre-tout').textContent = c.tout; $('note-vue').textContent = c.note;
    // chaque onglet montre seulement ce qu'on y a ouvert (Maillots ne ferme rien)
    if (o === 'bannieres') ouvrirBannieres();
    if (o === 'hub') chargerHub();                 // (15/11/2026) hub « Mes créations »
    if (ONGLETS_JEU.includes(o) && !E.jeu[o]) api('/api/jeu?cat=' + o).then(l => { E.jeu[o] = l; if (E.onglet === o && document.activeElement === cherche) cherche.dispatchEvent(new Event('input')); });
    if (o === 'maillots') mmListe();
    // (21/11) liste des copies d'esprit de l'onglet Armures : remplie à CHAQUE arrivée sur l'onglet (avant : seulement au clic
    // sur l'onglet ; par l'accueil, « Continuer » / « Modifier », elle restait vide -> « Aucune copie d'esprit »)
    if (o === 'armures') caListe();
    if (o !== 'bannieres' && o !== 'hub' && E.tech && E.tech.onglet !== o) { E.tech = null; E.objets = []; E.textures = {}; E.vue.vider(); E.vue.lecteur = null; E.lecteur = null;
      dessinerPieces(); dessinerTextures(); $('titre-tech').textContent = "Rien d'ouvert"; majRapport(''); }
  };
  document.querySelectorAll('.onglets button').forEach(b => b.onclick = () => changerOnglet(b.dataset.onglet));
  window.changerOnglet = changerOnglet;
  if ($('hub-cherche')) $('hub-cherche').oninput = dessinerHub;
  if ($('hub-nouveau')) $('hub-nouveau').onclick = () => { changerOnglet('techniques'); $('cherche').focus(); };
  changerOnglet(new URLSearchParams(location.search).get('essai_natif') ? 'techniques' : 'hub');
  const source = () => E.onglet === 'esprits' ? E.persos.filter(p => p.genre === 'Esprit guerrier')
    : E.onglet === 'totems' ? E.persos.filter(p => p.genre === 'Totem') : ONGLETS_JEU.includes(E.onglet) ? (E.jeu[E.onglet] || []) : E.index;
  const sansAccent = s => s.normalize('NFD').replace(/[̀-ͯ]/g, '').toLowerCase();
  cherche.addEventListener('input', () => {
    const q = sansAccent(cherche.value.trim()); res.innerHTML = '';
    // (17/11/2026, retour de muku) Techniques aussi : toute la liste au clic, même sans rien taper (comme les autres onglets)
    if (!q && !estPerso() && E.onglet !== 'techniques') { res.style.display = 'none'; return; }
    // (15/11/2026) TOUTE la liste (avant : les 60 premiers seulement) ; construite d'un coup, un seul clic écouté
    // (15/11/2026) boutons de tri par genre (onglet Tenues : Tenue, Chaussures, Gants, Manches, Peau, Numéro)
    const tous = source().filter(t => sansAccent(t.nom).includes(q) || t.code.includes(q));
    const ORDRE = ['Tenue', 'Chaussures', 'Gants', 'Manches', 'Peau (bras, mains)', 'Numéro'];
    // (17/11/2026, demandes de muku) TROIS rangées de filtres, qui se combinent :
    // - provenance : Jeu / Mods (modèles de TOUS les mods, activés ou non, rangés dans l'onglet de leur type : moteur/mods_jeu.py) ;
    // - série : IE1 … Victory Road (moteur/series.py ; un élément peut être de plusieurs séries) ;
    // - genre (Tenues, Objets : Tenue, Chaussures, Gants…).
    const SERIES = ['IE1', 'IE2', 'IE3', 'GO 1', 'GO 2', 'GO 3', 'Ares', 'Orion', 'Victory Road'];
    const genreDe = t => t.mod ? (t.sorte || t.genre) : t.genre;
    const avecMods = ['techniques', 'esprits', 'totems', 'maillots', 'tenues', 'armures', 'personnages', 'objets'].includes(E.onglet), avecSeries = tous.some(t => t.series && t.series.length);
    const GENRES = ['tenues', 'objets'].includes(E.onglet);
    const fSource = avecMods && ['jeu', 'mods'].includes(E.filtreSource) ? E.filtreSource : null;
    const fSerie = avecSeries && SERIES.includes(E.filtreSerie) ? E.filtreSerie : null;
    const parSource = t => !fSource || (fSource === 'mods') === !!t.mod;
    const parSerie = t => !fSerie || (t.series || []).includes(fSerie);
    const nbG = {}; for (const t of tous) if (parSource(t) && parSerie(t)) nbG[genreDe(t)] = (nbG[genreDe(t)] || 0) + 1;
    const genres = Object.keys(nbG).sort((a, b) => E.onglet === 'tenues' ? (ORDRE.indexOf(a) + 99) % 99 - (ORDRE.indexOf(b) + 99) % 99 : nbG[b] - nbG[a]);
    const fGenre = GENRES && genres.length > 1 && genres.includes(E.filtreGenre) ? E.filtreGenre : null;
    const parGenre = t => !fGenre || genreDe(t) === fGenre;
    const l = tous.filter(t => parSource(t) && parSerie(t) && parGenre(t));
    const rangee = (attr, actif, choix) => '<div class="tri-genres">' + choix.map(([v, lib, n]) =>
      `<button data-${attr}="${echapper(v)}" class="${(actif || '') === v ? 'actif' : ''}">${echapper(lib)} <small>${n}</small></button>`).join('') + '</div>';
    let puces = '';
    if (avecMods) puces += rangee('source', fSource, [['', 'Tout', tous.filter(t => parSerie(t) && parGenre(t)).length],
      ['jeu', 'Jeu', tous.filter(t => !t.mod && parSerie(t) && parGenre(t)).length], ['mods', 'Mods', tous.filter(t => t.mod && parSerie(t) && parGenre(t)).length]]);
    if (avecSeries) puces += rangee('serie', fSerie, [['', 'Toutes séries', tous.filter(t => parSource(t) && parGenre(t)).length]]
      .concat(SERIES.map(s => [s, s, tous.filter(t => (t.series || []).includes(s) && parSource(t) && parGenre(t)).length]).filter(x => x[2])));
    if (GENRES && genres.length > 1) puces += rangee('genre', fGenre, [['', 'Tout', Object.values(nbG).reduce((a, b) => a + b, 0)]].concat(genres.map(g => [g, g, nbG[g]])));
    res.innerHTML = `<div class="compte-liste">${puces}${l.length} résultat${l.length > 1 ? 's' : ''}</div>` + l.map((t, i) =>
      `<div data-i="${i}"><span>${echapper(t.nom)}</span><small>${echapper(t.code)} · ${echapper(t.genre)}${t.element ? ' · ' + echapper(libElement(t.element)) : ''}</small></div>`).join('');
    res.onclick = ev => { const bg = ev.target.closest('[data-genre],[data-source],[data-serie]');
      if (bg) { ev.stopPropagation();                         // tri : la liste reste ouverte
        if ('genre' in bg.dataset) E.filtreGenre = bg.dataset.genre || null;
        if ('source' in bg.dataset) E.filtreSource = bg.dataset.source || null;
        if ('serie' in bg.dataset) E.filtreSerie = bg.dataset.serie || null;
        cherche.dispatchEvent(new Event('input')); return; }
      const d = ev.target.closest('[data-i]'); if (!d) return; const t = l[+d.dataset.i];
      cherche.value = t.nom; res.style.display = 'none'; const onglet = E.onglet; if (onglet === 'maillots') MM.cote = '10';
      ouvrir(t.code).then(() => { if (onglet === 'maillots') mmNouveau(); })   // maillot du jeu = nouvelle coupe
        .catch(e => { $('titre-tech').textContent = 'Erreur : ' + e.message; }); };
    res.style.display = l.length ? 'block' : 'none';
  });
  $('tout-sel').onclick = () => { for (const o of E.objets) for (const p of o.pieces || []) E.selPieces.add(o.nom + '/' + p.index); majSelection(); };
  $('rien-sel').onclick = () => { E.selPieces.clear(); E.selTex.clear(); majSelection(); };
  $('isoler').onclick = () => { for (const o of E.objets) for (const p of o.pieces || []) if (p.vue) p.vue.visible = E.selPieces.has(o.nom + '/' + p.index); E.vue.recadrer(true); dessinerPieces(); };
  $('tout-voir').onclick = () => { for (const o of E.objets) for (const p of o.pieces || []) if (p.vue) p.vue.visible = true; E.vue.recadrer(); dessinerPieces(); };
  $('recadrer').onclick = () => E.vue.recadrer(true);
  $('additif').onchange = e => E.vue.additif = e.target.checked;
  $('fil').onchange = e => E.vue.fil = e.target.checked;
  $('filtre-sel').onchange = () => { dessinerTextures(); dessinerMateriaux(); dessinerTeintes(); };
  $('tex-tout').onclick = () => { for (const c of texturesVisibles()) { const x = E.textures[c]; if (x && x.cur && !x.info.donnees) E.selTex.add(c); } dessinerTextures(); };
  $('tex-rien').onclick = () => { E.selTex.clear(); dessinerTextures(); };
  $('mode').onchange = () => $('lab-c2').style.display = $('mode').value === 'degrade' ? '' : 'none'; $('mode').onchange();
  $('sat').oninput = () => $('v-sat').textContent = ($('sat').value / 100).toFixed(1).replace('.', ',');
  $('lum').oninput = () => $('v-lum').textContent = ($('lum').value / 100).toFixed(1).replace('.', ',');
  const lh = () => { const c = hsv2rgb(+$('lueurs-h').value, 0.8, 1); $('v-lh').style.background = `rgb(${c.map(x => x * 255).join(',')})`; };
  const majLueurs = () => { E.vue.lueur = $('lueurs-on').checked; E.vue.lueurH = +$('lueurs-h').value; E.vue.garderOr = $('garder-or').checked; };
  $('lueurs-h').oninput = () => { lh(); majLueurs(); }; lh();
  $('lueurs-on').onchange = majLueurs; $('garder-or').addEventListener('change', majLueurs);
  $('appliquer').onclick = () => { if (!E.selTex.size) return majRapport('Choisis d\'abord des textures (clic sur une vignette, ou sélectionne des pièces).');
    const r = reglage(); for (const c of E.selTex) appliquerA(c, r); apresRetouche(); };
  $('aleatoire').onclick = () => { for (const c of Object.keys(E.textures)) { const r = reglage('teinte'); r.c1 = hsv2rgb(Math.random() * 360, 1, 1); appliquerA(c, r); } apresRetouche(); };
  $('degrade-tout').onclick = () => { for (const c of Object.keys(E.textures)) appliquerA(c, reglage('degrade')); apresRetouche(); };
  $('remettre').onclick = () => { for (const x of Object.values(E.textures)) if (x.cur && x.orig) { x.cur.getContext('2d').putImageData(x.orig, 0, 0); x.modif = false; x.base = null; x.moyenne = moyenne(x.orig); } apresRetouche(); };
  if ($('tex-dessiner')) $('tex-dessiner').onclick = () => { const k = [...E.selTex][0]; if (!k) return majRapport('Choisis d\'abord une texture (clic sur une vignette), puis « Dessiner ».'); ouvrirEditeur(k); };
  cherche.addEventListener('focus', () => { if (estPerso() || E.onglet === 'techniques') cherche.dispatchEvent(new Event('input')); });
  document.addEventListener('click', ev => { if (!ev.target.closest('.recherche')) res.style.display = 'none'; });
  // lecteur
  E.vue.surImage = (f, res) => { majTelop(f); majSon(f); $('vue').classList.toggle('ciel', !!E.vue.lecteur && $('l-terrain').checked && res.decor !== false);
    if (NATIF.actif) return;                   // (14/11/2026) lecteur natif ouvert : barre et texte suivent SON image (suivreNatif)
    if (document.activeElement !== $('l-image')) $('l-image').value = f;
    $('l-info').textContent = `image ${f} / ${E.lecteur ? E.lecteur.duree : 0}${res.plan ? ' · plan ' + res.plan.nom : ''}`; $('l-jouer').textContent = E.vue.joue ? '❚❚' : '▶'; };
  // (14/11/2026 : l'ancien lecteur, rendu Python à la pause et « Film Direct3D », est retiré : tout passe par le lecteur C++)
  if ($('l-natif-bouton')) $('l-natif-bouton').onclick = () => lecteurNatif();
  $('l-jouer').onclick = () => { if (!E.vue.lecteur) activerAnimation(true); E.vue.joue = false; lecteurNatif(); };   // lecture = lecteur C++
  $('l-image').oninput = () => { if (NATIF.actif) { cmdNatif('image ' + $('l-image').value); return; }
    if (!E.vue.lecteur) activerAnimation(true); E.vue.joue = false; E.vue.image = +$('l-image').value; };
  $('l-vitesse').onchange = () => E.vue.vitesse = +$('l-vitesse').value;
  $('l-camera').onchange = () => E.vue.cameraJeu = $('l-camera').checked;
  $('l-boucle').onchange = () => E.vue.boucle = $('l-boucle').checked;
  $('l-anim').onchange = () => activerAnimation($('l-anim').checked);
// vraies particules : afficher / cacher (la simulation continue)
if ($('l-vraistade')) $('l-vraistade').onchange = () => { E.vue.vraiStade = $('l-vraistade').checked; };
if ($('l-lumieres')) $('l-lumieres').onchange = () => { E.vue.lumieresActives = $('l-lumieres').checked; };
if ($('l-particules')) $('l-particules').onchange = () => { for (const p of E.vue.pieces) if (p.ptl) p.visible = $('l-particules').checked; };
  $('l-terrain').onchange = () => activerAnimation(!!E.vue.lecteur);
  // vidéo officielle (site zukan.inazuma.jp) à côté de l'aperçu
  $('l-video').onclick = () => { const v = E.tech && E.tech.video; if (!v) { majRapport('Pas de vidéo officielle pour cette technique.'); return; }
    const el = $('video-jeu-v'); if (el.dataset.src !== v) { el.src = v; el.dataset.src = v; } $('video-jeu').style.display = 'block'; el.currentTime = 0; el.play().catch(() => {}); };
  $('video-jeu-x').onclick = () => { $('video-jeu-v').pause(); $('video-jeu').style.display = 'none'; };
  $('l-perso').onchange = () => { E.persoChoisi = $('l-perso').value; if (E.tech && !E.tech.perso) ouvrir(E.tech.code); };
  document.addEventListener('keydown', ev => {
    if (/INPUT|TEXTAREA|SELECT/.test(document.activeElement.tagName) && document.activeElement !== $('l-image')) return;
    if (ev.code === 'Space' && E.vue.lecteur) { ev.preventDefault(); E.vue.joue = false; lecteurNatif(); return; }
    if (ev.code === 'Escape' && NATIF.lance && !NATIF.actif) { finNatif(true); $('l-film-info').textContent = 'Lecteur natif : lancement annulé'; return; }
    if (ev.code === 'KeyA' && !ev.ctrlKey && !ev.altKey && E.tech) { ev.preventDefault(); basculerAvant(); return; }      // (15/11/2026) avant / après
    if (!NATIF.actif) return;                     // lecteur incrusté : ses touches
    const k = { ArrowRight: 'pas 1', ArrowLeft: 'pas -1', Home: 'debut', KeyE: 'ecran', Escape: 'quitter' }[ev.code];
    if (k) { ev.preventDefault(); if (k === 'quitter') finNatif(true); else cmdNatif(k); } });
  addEventListener('resize', () => { if (NATIF.actif) { NATIF.rect = rectNatif().join(' '); cmdNatif('rect ' + NATIF.rect); } });
  // essais : ?essai_natif=<code> ouvre la technique puis le lecteur incrusté (vérifications sans clic)
  { const q = new URLSearchParams(location.search).get('essai_natif');
    if (q) setTimeout(async () => { await ouvrir(q); for (let i = 0; i < 240 && !(E.lecteur && E.stadeCode); i++) await new Promise(r => setTimeout(r, 500));
      activerAnimation(true); lecteurNatif(); }, 500); }
  addEventListener('beforeunload', () => { if (NATIF.actif || NATIF.lance) navigator.sendBeacon && navigator.sendBeacon('/api/natif_cmd', JSON.stringify({ cmd: 'quitter' })); });
  $('zone-on').onchange = () => { $('zone').classList.toggle('on', $('zone-on').checked); dessinerZone(); };
  $('zone-c').oninput = dessinerZone; $('zone-t').oninput = dessinerZone;
  $('zone-apercu').onclick = ev => { const x = E.textures[$('zone-apercu').dataset.cle]; if (!x) return;
    const b = $('zone-apercu').getBoundingClientRect(), px = Math.floor((ev.clientX - b.left) / b.width * x.orig.width), py = Math.floor((ev.clientY - b.top) / b.height * x.orig.height);
    const k = (py * x.orig.width + px) * 4, d = x.orig.data, hx = v => v.toString(16).padStart(2, '0');
    $('zone-c').value = '#' + hx(d[k]) + hx(d[k + 1]) + hx(d[k + 2]); dessinerZone(); };
  // (15/11/2026) avant / après, remplacer partout, préréglages, sauvegarde du projet
  if ($('avant-apres')) $('avant-apres').onclick = () => basculerAvant();
  if ($('rc-ok')) { $('rc-ok').onclick = lancerRemplacement; $('rc-annuler').onclick = annulerRemplacement;
    $('rc-tol').oninput = () => { $('v-rc-tol').textContent = $('rc-tol').value + '°'; }; $('rc-tol').oninput();
    $('rc-inverser').onclick = () => { const a = $('rc-de').value; $('rc-de').value = $('rc-vers').value; $('rc-vers').value = a; };
    $('bloc-remplacer').addEventListener('toggle', () => { if ($('bloc-remplacer').open) paletteTech(); }); }
  if ($('pr-garder')) { $('pr-garder').onclick = garderPrereglage; $('pr-appliquer').onclick = appliquerPrereglage; $('pr-suppr').onclick = supprimerPrereglage; chargerPrereglages(); }
  setInterval(sauverProjet, 2000);
  $('exporter').onclick = exporter;
  $('installer').onclick = () => installer('MesTechniques');
  $('exporter-perso').onclick = exporterPerso;
  $('installer-perso').onclick = () => installer('MesEsprits');
  $('ouvrir-maillots').onclick = async () => { const r = await api('/api/ouvrir_maillots', {});
    $('rapport-maillots').textContent = r.ok ? "L'Atelier Maillots s'ouvre dans sa fenêtre." : r.erreur; };
});


// ------------------------------------------------------------------ (15/11/2026) techniques d'un nouveau joueur, technique liée d'un esprit
// Règles (moteur/coups.py) : une carte = 9 cases [technique, niveau] ; CharacterReforged (activé) : techniques en cases 1 à 6,
// cases 7-8 vides, UNE aura (esprit guerrier / totem…) en case 9 où VRFW la range toute seule, niveaux selon la puissance.
const libCoup = x => (x.mod ? '★ ' : '') + x.nom + ' — ' + x.genre + ' (' + x.code + ')';
const AURAS_COUPS = ['Esprit guerrier', 'Totem', 'Armure', 'Aura', 'Miximax', 'Lien', 'Éveil', 'Mode'];
function fenetreCoups(titre, html) {
  let f = $('fenetre-coups');
  if (!f) { f = document.createElement('dialog'); f.id = 'fenetre-coups'; document.body.appendChild(f); }
  f.innerHTML = `<div class="fc-tete"><b>${echapper(titre)}</b><button data-f="fermer" title="Fermer sans rien changer">✕</button></div>${html}`;
  f.querySelector('[data-f="fermer"]').onclick = () => f.close();
  if (!f.open) f.showModal();
  return f;
}
function listeCoups(id, liste) {           // <datalist> : mes créations d'abord
  return `<datalist id="${id}">${[...liste].sort((a, b) => (b.mod ? 1 : 0) - (a.mod ? 1 : 0)).map(x => `<option value="${echapper(libCoup(x))}">`).join('')}</datalist>`;
}

// (15/11/2026) TECHNIQUES D'UN NOUVEAU JOUEUR, façon « Tableau des compétences » du jeu (capture de muku :
// references_menus/tableau_competences.webp) : à gauche la carte du joueur, la barre de l'esprit (violette) et les barres des
// techniques (couleur = élément, boule = genre, puissance à droite) ; au milieu le joueur en 3D ; à droite la fiche de la case
// choisie (puissance, tension, niveau) et la liste pour la remplir. LU : puissance = power_max, tension = tp (skill_config,
// changés par les mods : HissatsuReforged donne Tir solaire 580 / 90T comme la capture) ; couleur des barres = élément (Tir
// chaotique Forêt = vert, Icare Feu = rouge sur la capture) ; boule : tirs rouges, dribbles verts (capture), défense / gardien DÉDUIT.
// Règles CharacterReforged (moteur/coups.py) : 6 techniques (cases 1-6), UN esprit / totem (case 9).
const TC_EL = { 1: ['Air', 'air'], 2: ['Forêt', 'foret'], 3: ['Feu', 'feu'], 4: ['Montagne', 'montagne'], 5: ['Néant', 'neant'] };
const TC_GENRE = { Tir: ['TIR', 'tir'], 'Tir simple': ['TIR', 'tir'], Dribble: ['DRI', 'dri'], 'Dribble simple': ['DRI', 'dri'],
  Défense: ['DÉF', 'def'], 'Défense simple': ['DÉF', 'def'], Gardien: ['GAR', 'gar'], 'Arrêt simple': ['GAR', 'gar'] };
const TC = { vue: null, maillot: 'u010101', cote: '10' };
const TC_POSE = { paquet: 'p010', clip: 1, yaw: 0 };     // clip 1 de p010 = mains sur les hanches (choisi à l'œil) ; yaw 0 = de face
async function ouvrirCoups(c) {
  let f = $('tableau-coups');
  if (!f) {
    f = document.createElement('dialog'); f.id = 'tableau-coups'; document.body.appendChild(f);
    f.innerHTML = `<div class="tc-entete"><div class="jm-coin tc-coin">${iconeJeu('m4', 46)}<span>Tableau des compétences</span></div>
        <div class="tc-plaque"><span class="tc-plaque-nom"></span><span class="tc-plaque-sous"></span><span class="jm-tag tc-plaque-tag">PERSO</span></div>
        <button class="tc-fermer" title="Fermer sans rien changer (Échap)">✕</button></div>
      <div class="tc-corps"><div class="tc-gauche"></div>
        <div class="tc-milieu"><canvas id="tc-vue"></canvas><div class="tc-vue-msg"></div><div class="tc-curseur"></div>
          <div class="tc-maillot-choix"><span>Maillot</span><select class="tc-maillot"></select>
            <button data-cote="10" title="Domicile">Dom.</button><button data-cote="20" title="Extérieur">Ext.</button></div></div>
        <div class="tc-droite"></div></div>
      <div class="tc-aide"><span><i class="jm-touche">Échap</i> Fermer</span><span><i class="jm-touche">🖱</i> Choisir</span><span><i class="jm-touche">Suppr</i> Vider la case</span><span class="tc-aide-note"></span></div>`;
    f.querySelector('.tc-fermer').onclick = () => f.close();
    f.addEventListener('keydown', ev => { if ((ev.key === 'Delete' || ev.key === 'Backspace') && !/INPUT/.test(document.activeElement.tagName) && TC.vider) { ev.preventDefault(); TC.vider(); } });
  }
  if (!f.open) f.showModal();
  const G = f.querySelector('.tc-gauche'), D = f.querySelector('.tc-droite');
  f.querySelector('.tc-plaque-nom').textContent = c.nom; f.querySelector('.tc-plaque-sous').textContent = 'Lecture…'; G.innerHTML = ''; D.innerHTML = '';
  let r; try { r = await api('/api/coups?cle=' + encodeURIComponent(c.cle)); } catch (e) { D.textContent = e.message; return; }
  if (!r.ok) { D.textContent = r.erreur; return; }
  f.querySelector('.tc-plaque-sous').textContent = `Copie de ${r.nom_origine || r.base} · code ${r.code}`;
  f.querySelector('.tc-aide-note').textContent = r.reforged ? 'CharacterReforged : 6 techniques + 1 esprit (case 9) ; les niveaux peuvent être recalculés' : '';
  const tous = [...r.mes, ...r.catalogue], parId = new Map(tous.map(x => [x.id, x]));
  const estAura = x => AURAS_COUPS.includes(x.genre);
  // les 7 cases : 0-5 techniques, 6 = esprit (case 9 du jeu)
  const S = [null, null, null, null, null, null, null];
  const poser = L => { S.fill(null); let k = 0; for (const m of L) { const x = parId.get(m.move); if (!x) continue;
      if (estAura(x)) S[6] = { move: m.move, level: m.level || 1 }; else if (k < 6) S[k++] = { move: m.move, level: m.level || 1 }; } };
  poser(r.actuels.length ? r.actuels : r.mods.length ? r.mods : r.origine);
  let sel = 0, filtreG = '', texte = '';
  const fiche = x => r.fiches[x.code] || [0, 0, 0, 0];
  const iconeEsprit = x => { const m = r.modeles_esprits[String(fiche(x)[3])]; return m ? `<img class="tc-esp-ico" src="/api/icone_esprit?code=${encodeURIComponent(m)}" alt="" onerror="this.remove()">` : ''; };
  const barre = (x, lv, i, petit) => {
    if (!x) return `<button class="tc-barre vide${petit ? ' petit' : ''}" data-i="${i}"><span class="tc-orbe"></span><span class="tc-nom">${i === 6 ? 'Esprit guerrier ou totem' : ''}</span></button>`;
    if (estAura(x)) return `<button class="tc-barre esprit${petit ? ' petit' : ''}" data-i="${i}" data-id="${x.id}"><span class="tc-nom">${x.mod ? '★ ' : ''}${echapper(x.nom)}</span><small>${echapper(x.genre)}</small>${iconeEsprit(x)}</button>`;
    const F = fiche(x), el = TC_EL[F[2]] || ['', 'neutre'], g = TC_GENRE[x.genre] || [x.genre.slice(0, 3).toUpperCase(), 'tir'];
    return `<button class="tc-barre el-${el[1]}${petit ? ' petit' : ''}" data-i="${i}" data-id="${x.id}" title="${echapper(x.nom)} — ${echapper(x.genre)}${el[0] ? ', ' + el[0] : ''} (${x.code})">
      <span class="tc-orbe g-${g[1]}"></span><span class="tc-nom">${x.mod ? '★ ' : ''}${echapper(x.nom)}</span>
      <span class="tc-pw"><small>${g[0]}</small>${F[0] || ''}</span></button>`; };
  const dessiner = () => {
    G.innerHTML = `<div class="tc-carte g-personnages"><img src="/api/portrait?code=${encodeURIComponent(r.code)}" onerror="this.src='/api/portrait?code=${encodeURIComponent(r.tete || r.base)}';this.onerror=null" alt="">
        <span class="jm-tag">PERSO</span></div>
      ${barre(S[6] && parId.get(S[6].move), S[6] && S[6].level, 6)}
      ${[0, 1, 2, 3, 4, 5].map(i => barre(S[i] && parId.get(S[i].move), S[i] && S[i].level, i)).join('')}
      <div class="tc-boutons"><button data-f="origine" title="Les techniques de la carte d'origine (fichiers du jeu)">Celles du jeu</button>
        ${r.mods.length ? `<button data-f="mods" title="Ce que ${echapper(r.mod)} donne à l'original (ce que tu vois en jeu)">Celles de ${echapper(r.mod)}</button>` : ''}
        <button data-f="aucun" title="Ne rien écrire : la copie garde la liste de la carte d'origine">Ne rien changer</button></div>
      <button class="tc-enregistrer" data-f="garder">Enregistrer</button><div class="tc-etat"></div>
      ${r.plateau ? '<div class="tc-note">La carte d’origine a son propre plateau de compétences : une technique ajoutée n’y apparaît que si le plateau la contient (VRFW).</div>' : ''}`;
    G.querySelectorAll('.tc-barre').forEach(b => { if (+b.dataset.i === sel) b.classList.add('sel'); b.onclick = () => { sel = +b.dataset.i; filtreG = ''; dessiner(); }; });
    G.querySelector('[data-f="origine"]').onclick = () => { poser(r.origine); dessiner(); };
    if (r.mods.length) G.querySelector('[data-f="mods"]').onclick = () => { poser(r.mods); dessiner(); };
    G.querySelector('[data-f="aucun"]').onclick = () => envoyer([]);
    G.querySelector('[data-f="garder"]').onclick = () => envoyer([...S.slice(0, 6), S[6]].filter(Boolean));
    dessinerDroite();
    const b = G.querySelector('.tc-barre.sel'); f.querySelector('.tc-curseur').style.top = b ? (b.offsetTop + b.offsetHeight / 2 - 10) + 'px' : '-99px';
  };
  const dessinerDroite = () => {
    const s = S[sel], x = s && parId.get(s.move), F = x ? fiche(x) : null, aura = sel === 6;
    const liste = tous.filter(y => aura ? estAura(y) : !estAura(y));
    const genres = [...new Set(liste.map(y => y.genre))];
    const q = texte.toLowerCase().normalize('NFD').replace(/[̀-ͯ]/g, '');
    const L = liste.filter(y => (!filtreG || y.genre === filtreG) && (!q || (y.nom + ' ' + y.code).toLowerCase().normalize('NFD').replace(/[̀-ͯ]/g, '').includes(q)))
      .sort((a, b) => (b.mod ? 1 : 0) - (a.mod ? 1 : 0) || (fiche(b)[0] - fiche(a)[0]) || a.nom.localeCompare(b.nom)).slice(0, 150);
    const tension = F && F[1] ? `<div class="tc-tension"><span>TENSION</span><i style="--t:${Math.min(1, F[1] / 150)}"></i><b>${F[1]}<small>T</small></b></div>` : '';
    D.innerHTML = `<div class="tc-detail">${x ? barre(x, s.level, sel, false) : `<div class="tc-vide-txt">${aura ? 'Case 9 : esprit guerrier ou totem' : 'Case ' + (sel + 1) + ' vide'}</div>`}
        ${x ? `<div class="tc-infos">${tension}
          <label class="tc-niv"><span>Appris au</span> <i class="jm-touche">Lv.</i><input type="number" min="1" max="99" value="${s.level}"></label>
          <span class="tc-puce">${echapper(x.genre)}</span>${F && TC_EL[F[2]] ? `<span class="tc-puce el-${TC_EL[F[2]][1]}">${TC_EL[F[2]][0]}</span>` : ''}
          ${x.mod ? `<span class="tc-puce mien">${x.mod}</span>` : ''}<button class="tc-vider">Vider la case</button></div>` : ''}</div>
      <div class="tc-choix"><div class="tc-choix-tete"><span>${aura ? 'Choisir un esprit' : 'Choisir une technique'}</span>
          <div class="jm-recherche"><span class="jm-touche">X</span><input class="tc-cherche" placeholder="Chercher par nom" value="${echapper(texte)}"></div></div>
        <div class="tc-genres"><button data-g="" class="${filtreG ? '' : 'sel'}">Tout</button>${genres.map(g => `<button data-g="${echapper(g)}" class="${filtreG === g ? 'sel' : ''}">${echapper(g)}</button>`).join('')}</div>
        <div class="tc-liste">${L.map(y => barre(y, 1, -1, true).replace('data-i="-1"', `data-choix="${y.id}"`)).join('') || '<div class="tc-vide-txt">Aucune</div>'}</div></div>`;
    const inp = D.querySelector('.tc-niv input'); if (inp) inp.oninput = () => { s.level = Math.max(1, Math.min(99, +inp.value || 1)); };
    const v = D.querySelector('.tc-vider'); if (v) v.onclick = () => { S[sel] = null; dessiner(); };
    const ch = D.querySelector('.tc-cherche'); ch.oninput = () => { texte = ch.value; const p = ch.selectionStart; dessinerDroite(); const n = D.querySelector('.tc-cherche'); n.focus(); n.setSelectionRange(p, p); };
    D.querySelectorAll('.tc-genres button').forEach(b => b.onclick = () => { filtreG = b.dataset.g; dessinerDroite(); });
    D.querySelectorAll('[data-choix]').forEach(b => b.onclick = () => {
      const id = +b.dataset.choix, y = parId.get(id);
      const i0 = S.findIndex(m => m && m.move === id); if (i0 >= 0 && i0 !== sel) S[i0] = null;      // pas deux fois la même
      S[sel] = { move: id, level: (S[sel] && S[sel].level) || 1 };
      if (!estAura(y) && sel < 5 && S.slice(0, 6).every(Boolean) === false) { const nx = S.findIndex((m, k) => k < 6 && k > sel && !m); if (nx >= 0) sel = nx; }
      dessiner(); });
  };
  TC.vider = () => { S[sel] = null; dessiner(); };
  const envoyer = async L => {
    const e = G.querySelector('.tc-etat'); e.textContent = 'Écriture…';
    try { const q = await api('/api/coups', { cle: c.cle, coups: L });
      if (!q.ok) { e.textContent = q.erreur; return; }
      f.close();
      // (22/11, « on n'a besoin que de créer ») enregistré dans la création ; « Installer » sur sa carte pour le jeu
      e.textContent = ''; majRapport(q.rapport.join('\n')); $('hub-etat').textContent = 'Enregistré. Pour le mettre dans le jeu : « Installer » sur sa carte dans Mes créations.'; chargerHub();
    } catch (x) { e.textContent = x.message; } };
  dessiner();
  // (15/11/2026) maillot porté dans l'aperçu : un maillot du jeu (Raimon par défaut), gardé pour la prochaine fois
  try { TC.maillot = localStorage.getItem('tc_maillot') || TC.maillot; TC.cote = localStorage.getItem('tc_cote') || TC.cote; } catch (e) { /* sans mémoire */ }
  const sm = f.querySelector('.tc-maillot');
  if (!sm.options.length) { try { const L = (E.jeu && E.jeu.maillots) || await api('/api/jeu?cat=maillots');
      [...L].sort((a, b) => a.nom.localeCompare(b.nom)).forEach(m => { const o = document.createElement('option'); o.value = m.code; o.textContent = m.nom.replace(/^Maillot /, ''); sm.appendChild(o); }); } catch (e) { /* liste indisponible */ } }
  sm.value = TC.maillot;
  const majCote = () => f.querySelectorAll('[data-cote]').forEach(b => b.classList.toggle('sel', b.dataset.cote === TC.cote));
  const garder = () => { try { localStorage.setItem('tc_maillot', TC.maillot); localStorage.setItem('tc_cote', TC.cote); } catch (e) { /* sans mémoire */ } };
  sm.onchange = () => { TC.maillot = sm.value; garder(); apercuJoueur(r, c.cle, f); };
  f.querySelectorAll('[data-cote]').forEach(b => b.onclick = () => { TC.cote = b.dataset.cote; majCote(); garder(); apercuJoueur(r, c.cle, f); });
  majCote();
  apercuJoueur(r, c.cle, f);
}

// aperçu 3D du joueur : modèle complet du personnage d'origine (/api/modele?quoi=joueur : tête, maillot, chaussures, peau,
// squelette de sa corpulence), pose de liaison (sans animation), tête recolorée de la copie (/api/copie_textures)
async function apercuJoueur(r, cle, f) {
  const msg = f.querySelector('.tc-vue-msg'); msg.textContent = 'Chargement du joueur…';
  try {
    if (!TC.vue) { TC.vue = new Vue3D(f.querySelector('#tc-vue')); TC.vue.cameraJeu = false; }
    const V = TC.vue; V.vider(); V.lecteur = null;
    const jeton = TC.jeton = (TC.jeton || 0) + 1;          // un autre maillot choisi pendant le chargement : celui-ci est oublié
    const [buf, copie] = await Promise.all([api('/api/modele?quoi=joueur&code=' + encodeURIComponent(r.base) + '&maillot=' + encodeURIComponent(TC.maillot || '') + '&cote=' + (TC.cote || '10')),
      api('/api/copie_textures?cle=' + encodeURIComponent(cle)).catch(() => ({}))]);
    if (jeton !== TC.jeton) return;
    V.vider(); V.lecteur = null;
    const dv = new DataView(buf), lg = dv.getUint32(0, true), meta = JSON.parse(new TextDecoder().decode(new Uint8Array(buf, 4, lg))); let p = 4 + lg;
    const tex = async (cleT, url) => { if (V.textures[cleT]) return; const im = await chargerImage(url); const cv = document.createElement('canvas');
      cv.width = im.width; cv.height = im.height; cv.getContext('2d').drawImage(im, 0, 0); V.texture(cleT, cv); };
    for (const [i, m] of meta.entries()) {
      const pos = new Float32Array(buf.slice(p, p + m.nv * 12)); p += m.nv * 12;
      const normales = new Float32Array(buf.slice(p, p + m.nv * 12)); p += m.nv * 12;
      const uv = new Float32Array(buf.slice(p, p + m.nv * 8)); p += m.nv * 8;
      const os = new Uint16Array(buf.slice(p, p + m.nv * 8)); p += m.nv * 8;
      const poids = new Float32Array(buf.slice(p, p + m.nv * 16)); p += m.nv * 16;
      const idx = new Uint16Array(buf.slice(p, p + m.ni * 2)); p += m.ni * 2 + ((4 - (m.ni * 2) % 4) % 4);
      const v = V.ajouterPeau('joueur/' + i, { nv: m.nv, ni: m.ni, pos, uv, os, poids, idx, normales, contour: m.contour, ombreCle: m.ombre ? 'peau:' + m.ombre : null, noir: m.noir }, 'joueur');
      if (m.ombre) { try { await tex('peau:' + m.ombre, '/tex/' + m.ombre + '.png'); } catch (e) { /* sans carte d'ombres */ } }
      if (m.texture) { const nom = m.texture.split('/').pop(), url = copie[nom] || '/tex/' + m.texture + '.png';
        try { await tex('peau:' + m.texture + (copie[nom] ? ':copie' : ''), url); v.texCle = 'peau:' + m.texture + (copie[nom] ? ':copie' : ''); } catch (e) { /* sans texture */ } }
    }
    // pose : un clip des mouvements de sa corpulence, en boucle (la tête n'est mise sur le cou que par l'animation)
    try { const P = await api('/api/pose_joueur?code=' + encodeURIComponent(r.base) + '&paquet=' + TC_POSE.paquet + '&clip=' + TC_POSE.clip);
      if (P.ok) { const sq = new Squelette(P.os, P), inv = sq.mondeRepos.map(Anim3D.inverse), c0 = P.clip, n = Math.max(1, c0.fin - c0.debut);
        V.lecteur = { d: {}, duree: n, calculer(f) { const m = sq.poser(c0, c0.debut + (f % n)); return { peaux: { joueur: m.map((w, b) => Anim3D.mul(w, inv[b])) }, objets: {} }; } };
        V.image = 0; V.joue = true; V.boucle = true; } } catch (e) { /* pose de liaison */ }
    V.recadrer(); V.dist *= 0.95; V.yaw = TC_POSE.yaw; V.pitch = 0.05;
    msg.textContent = r.vetement ? 'Aperçu : le joueur d’origine (la tenue recolorée n’est pas montrée ici)' : Object.keys(copie).length ? '' : 'Aperçu : couleurs d’origine';
  } catch (e) { msg.textContent = 'Aperçu indisponible : ' + e.message; }
}

// (22/11, idée de muku : « d'abord le visuel, ensuite les stats dans un menu à part ») fenêtre des valeurs d'une création :
// champs donnés par le serveur (moteur/stats.py : clés VRFW lues dans des mods qui marchent), partis des valeurs de l'original
// (22/11, demande de muku) SUPPRIMER une création de Terminées : ses fichiers sont rangés dans sortie/<mod>/_retires
// (récupérables) ; refusé si elle sert encore (techniques d'un joueur, technique liée d'un esprit…)
async function supprimerCreation(c) {
  const dansJeu = c.installe || c.jeuSeul;
  const suite = c.mod === 'MesTechniques' ? (dansJeu ? '\nElle est aussi retirée du jeu (le jeu doit être fermé).' : '')
    : dansJeu ? '\nElle reste dans le jeu jusqu’au prochain « Installer » de ce genre de créations.' : '';
  if (!confirm(`Supprimer « ${c.nom} » ?\nSes fichiers sont rangés à part dans l’Atelier (sortie/${c.mod}/_retires), pas effacés.${suite}`)) return;
  let r;
  try {
    if (c.mod === 'MesMaillots' && c.maillot) {
      await api('/api/maillot', { action: 'supprimer', id: c.maillot });
      r = await api('/api/maillot', { action: 'construire' });          // le mod « Mes maillots » refait sans lui
      r = r.ok ? { ok: true, rapport: ['maillot supprimé ; le mod « Mes maillots » est refait sans lui'] } : r;
    } else r = await api('/api/supprimer_creation', { mod: c.mod, code: c.mod === 'MesPersonnages' ? c.cle : c.code, genre: c.genre });
  } catch (e) { r = { ok: false, erreur: e.message }; }
  $('hub-etat').textContent = r.ok ? `« ${c.nom} » supprimé.` : 'Pas supprimé : ' + r.erreur;
  if (r.ok) majRapport(r.rapport.join('\n'));
  chargerHub();
}
function aDesStats(c) { return !c.jeuSeul && (c.mod === 'MesTechniques' || (c.mod === 'MesEsprits' && c.genre === 'esprit') || (c.mod === 'MesPersonnages' && c.cle)); }
// (22/11, « fais un beau menu pour les stats ») MENU DES STATS façon menus du jeu, comme le Tableau des compétences :
// en-tête orange + plaque du nom, à gauche la carte et l'aperçu (barre de technique ou d'esprit comme en jeu, PT en jauge
// « TENSION »), à droite les réglages ; joueur : panneau de statistiques d'après references_menus/equipement.webp
// (étiquettes bleues en capitales, barre de couleur par statistique, gros chiffres bleus, pastilles ATT / MIL / DÉF / GAR).
const MS_EL = { wind: 'air', forest: 'foret', fire: 'feu', mountain: 'montagne', void: 'neant' };
const MS_POSTE = { fw: ['ATT', 'Attaquant'], mf: ['MIL', 'Milieu'], df: ['DÉF', 'Défenseur'], gk: ['GAR', 'Gardien'] };
const MS_GENRE = { whs: ['g-tir', 'Tir'], who: ['g-dri', 'Dribble'], whd: ['g-def', 'Défense'], whk: ['g-gar', 'Arrêt'] };
const MS_STAT = { kick: 'frappe', control: 'controle', technique: 'technique', pressure: 'pression', physical: 'physique',
  intelligence: 'intelligence', agility: 'agilite', freedom: 'liberte' };
async function ouvrirStats(c) {
  const code = c.mod === 'MesPersonnages' ? c.cle : c.code;
  let f = $('menu-stats');
  if (!f) {
    f = document.createElement('dialog'); f.id = 'menu-stats'; document.body.appendChild(f);
    f.addEventListener('close', () => { if (typeof majCacheNatif === 'function') majCacheNatif(); });
  }
  const tag = { MesTechniques: 'TECH', MesEsprits: 'ESP', MesPersonnages: 'PERSO' }[c.mod] || '';
  f.innerHTML = `<div class="tc-entete"><div class="jm-coin tc-coin">${iconeJeu('m2', 46)}<span>Stats</span></div>
      <div class="tc-plaque"><span class="tc-plaque-nom"></span><span class="tc-plaque-sous">Lecture…</span><span class="jm-tag tc-plaque-tag">${tag}</span></div>
      <button class="tc-fermer" title="Fermer sans rien changer (Échap)">✕</button></div>
    <div class="ms-corps"><div class="ms-gauche"></div><div class="ms-droite"></div></div>
    <div class="tc-aide"><span><i class="jm-touche">Échap</i> Fermer</span><span class="ms-aide-txt"></span>
      <button class="ms-original">Garder celles de l'original</button><button class="tc-enregistrer ms-garder">Enregistrer</button></div>`;
  f.querySelector('.tc-plaque-nom').textContent = c.nom;
  f.querySelector('.tc-fermer').onclick = () => f.close();
  if (!f.open) f.showModal();
  if (typeof majCacheNatif === 'function') majCacheNatif();
  const G = f.querySelector('.ms-gauche'), D = f.querySelector('.ms-droite');
  let r; try { r = await api('/api/stats?mod=' + encodeURIComponent(c.mod) + '&code=' + encodeURIComponent(code)); } catch (e) { D.textContent = e.message; return; }
  if (!r.ok) { D.textContent = r.erreur; return; }

  const jeu = r.jeu || {}, deja = r.stats || {}, champ = k => r.champs.find(x => x.cle === k);
  // valeurs de travail : réglées avant, sinon celles de l'original (joueur : vide = comme l'original)
  const V = {};
  for (const ch of r.champs) { const k = ch.cle, d = k.startsWith('stats.') ? (deja.stats || {})[k.slice(6)] : deja[k];
    V[k] = d !== undefined ? d : (jeu[k] !== undefined ? jeu[k] : ''); }
  const joueur = r.genre === 'personnages';
  let statsOn = joueur && !!deja.stats;
  // ---- carte + aperçu (gauche)
  const proj = projetDe(c);
  const vign = c.vignette || (proj && proj.vignette) || '';
  const nomBase = c.nom_base || ((E.index || []).find(t => t.code === c.base) || {}).nom || c.base || '';   // nom de l'original (techniques : index)
  f.querySelector('.tc-plaque-sous').textContent = `Copie de ${nomBase}${c.code ? ' · code ' + c.code : ''}`;
  const libEl = e => ((champ('element') || { choix: [] }).choix.find(x => x[0] === e) || [e, ''])[1];
  const apercu = () => {
    const pmax = V.power_max !== '' ? V.power_max : '—', el = MS_EL[V.element] || 'neutre';
    let h = `<div class="tc-carte ms-carte g-${c.onglet}">${joueur && c.code ? `<img src="/api/portrait?code=${encodeURIComponent(c.code)}" alt="">` : vign ? `<img src="${vign}" alt="">` : ''}<span class="jm-tag">${tag}</span></div>`;
    if (r.genre === 'technique') {
      const g = MS_GENRE[(c.code || '').slice(0, 3)] || ['', ''];
      h += `<div class="ms-titre">Comme en jeu</div>
        <div class="tc-barre el-${el} ms-apercu"><span class="tc-orbe ${g[0]}"></span><span class="tc-nom">${echapper(c.nom)}</span><span class="tc-pw"><small>${g[1].toUpperCase()}</small>${pmax}</span></div>
        <div class="tc-tension" style="--t:${Math.min(1, (+V.tp || 0) / 150)}"><span>TENSION</span><i></i><b>${V.tp !== '' ? V.tp : '—'}<small>T</small></b></div>
        <div class="ms-infos"><span class="tc-puce el-${el}">${echapper(libEl(V.element) || 'Élément')}</span><span class="tc-niv"><span>Niv. 1</span>${V.power_min}</span>
          <span class="tc-puce">${V.users > 1 ? V.users + ' joueurs' : 'Solo'}</span></div>`;
      if (jeu.power_max !== undefined) h += `<div class="ms-titre">Original</div><div class="tc-barre petit el-${MS_EL[jeu.element] || 'neutre'}"><span class="tc-orbe ${g[0]}"></span><span class="tc-nom">${echapper(nomBase)}</span><span class="tc-pw"><small>${g[1].toUpperCase()}</small>${jeu.power_max}</span></div>`;
    } else if (r.genre === 'esprit') {
      h += `<div class="ms-titre">Comme en jeu</div>
        <div class="tc-barre esprit ms-apercu"><span class="tc-nom">${echapper(c.nom)}</span><span class="tc-pw"><small>ESPRIT</small>${pmax}</span></div>
        <div class="ms-infos"><span class="tc-puce el-${el}">${echapper(libEl(V.element) || 'Élément')}</span><span class="tc-niv"><span>Niv. 1</span>${V.power_min}</span></div>`;
      if (jeu.power_max !== undefined) h += `<div class="ms-titre">Original</div><div class="tc-barre petit esprit"><span class="tc-nom">${echapper(nomBase)}</span><span class="tc-pw"><small>ESPRIT</small>${jeu.power_max}</span></div>`;
    } else {
      const p = V.position ? MS_POSTE[V.position] : null, el2 = V.element ? MS_EL[V.element] : '';
      h += `<div class="ms-titre">Comme en jeu</div><div class="ms-joueur-tags">
        ${p ? `<span class="ms-poste p-${V.position}">${p[0]}</span>` : '<span class="ms-poste vide">poste d’origine</span>'}
        ${V.sub_position ? `<span class="ms-poste petit p-${V.sub_position}">${MS_POSTE[V.sub_position][0]}</span>` : ''}
        ${el2 ? `<span class="tc-puce el-${el2}">${echapper(libEl(V.element))}</span>` : '<span class="tc-puce">élément d’origine</span>'}</div>`;
    }
    G.innerHTML = h;
  };
  // ---- réglages (droite)
  const curseur = (k, nom, min, max, pas) => { const ch = champ(k); if (!ch) return '';
    const orig = jeu[k] !== undefined ? `<small>original : ${jeu[k]}</small>` : '';
    return `<div class="ms-ligne"><label>${echapper(nom || ch.nom)}${orig}</label><div class="ms-reglage">
      <input type="range" data-k="${k}" min="${min ?? ch.min}" max="${max ?? ch.max}" step="${pas || 1}" value="${V[k] === '' ? 0 : V[k]}">
      <input type="number" data-k="${k}" min="${ch.min}" max="${ch.max}" value="${V[k]}"></div></div>`; };
  const boutonsChoix = (k, items, vide) => { const ch = champ(k); if (!ch) return '';
    const orig = jeu[k] !== undefined && jeu[k] !== '' ? `<small>original : ${echapper(String(items.find(x => x[0] === jeu[k])?.[1] || jeu[k]))}</small>` : '';
    return `<div class="ms-ligne"><label>${echapper(ch.nom)}${orig}</label><div class="ms-choix" data-k="${k}">
      ${vide ? `<button data-v="" class="${V[k] === '' ? 'sel' : ''}">comme l’original</button>` : ''}
      ${items.map(([v, n, cl]) => `<button data-v="${v}" class="${cl || ''}${String(V[k]) === String(v) ? ' sel' : ''}">${echapper(n)}</button>`).join('')}</div></div>`; };
  const elems = (champ('element') || { choix: [] }).choix.map(([v, n]) => [v, n, 'el el-' + MS_EL[v]]);
  const panneau = () => {
    let h = '<div class="tc-detail ms-panneau">';
    if (r.genre === 'technique') {
      h += '<div class="ms-section">Puissance</div>' + curseur('power_min', 'Au niveau 1', 0, 1000) + curseur('power_max', 'Au niveau max', 0, 1500)
        + '<div class="ms-section">Utilisation</div>' + curseur('tp', 'Coût en PT (tension)', 0, 150)
        + boutonsChoix('users', [[1, 'Solo'], [2, '2 joueurs'], [3, '3 joueurs'], [4, '4 joueurs']])
        + '<div class="ms-section">Nature</div>' + boutonsChoix('element', elems)
        + boutonsChoix('growth', [0, 1, 2, 3, 4, 5, 6, 7].map(n => [n, String(n)]));
    } else if (r.genre === 'esprit') {
      h += '<div class="ms-section">Puissance</div>' + curseur('power_min', 'Au niveau 1', 0, 300) + curseur('power_max', 'Au niveau max', 0, 300)
        + '<div class="ms-section">Nature</div>' + boutonsChoix('element', elems);
    } else {
      const postes = Object.entries(MS_POSTE).map(([v, [a, n]]) => [v, a + ' · ' + n, 'poste p-' + v]);
      h += '<div class="ms-section">Poste et élément</div>' + boutonsChoix('position', postes, true) + boutonsChoix('sub_position', postes, true) + boutonsChoix('element', elems, true)
        + `<div class="ms-section">Statistiques <label class="ms-bascule"><input type="checkbox" class="ms-stats-on"${statsOn ? ' checked' : ''}> les changer</label></div>`
        + `<div class="ms-stats${statsOn ? '' : ' eteint'}">` + Object.entries(MS_STAT).map(([k, cl]) => {
          const ch = champ('stats.' + k), v = V['stats.' + k] === '' ? 200 : V['stats.' + k];
          return `<div class="ms-stat s-${cl}"><span class="ms-stat-nom">${echapper(ch.nom.toUpperCase())}</span>
            <span class="ms-stat-barre"><i style="--v:${Math.min(1, v / 300)}"></i><input type="range" data-k="stats.${k}" min="0" max="300" value="${v}"${statsOn ? '' : ' disabled'}></span>
            <input type="number" class="ms-stat-val" data-k="stats.${k}" min="0" max="999" value="${v}"${statsOn ? '' : ' disabled'}></div>`; }).join('')
        + '</div><p class="ms-note">Sans « les changer » : les statistiques de l’original. Les 8 vont ensemble.</p>';
    }
    h += '<div class="ms-etat"></div></div>';
    D.innerHTML = h;
    D.querySelectorAll('input[data-k]').forEach(el => el.oninput = () => {
      const k = el.dataset.k, v = el.value === '' ? '' : +el.value; V[k] = v;
      D.querySelectorAll(`input[data-k="${k}"]`).forEach(o => { if (o !== el) o.value = v; });
      const bar = el.closest('.ms-stat'); if (bar) bar.querySelector('i').style.setProperty('--v', Math.min(1, (+v || 0) / 300));
      apercu(); });
    D.querySelectorAll('.ms-choix').forEach(b => b.querySelectorAll('button').forEach(x => x.onclick = () => {
      const k = b.dataset.k, v = x.dataset.v; V[k] = v === '' ? '' : (champ(k).type === 'nombre' ? +v : v);
      b.querySelectorAll('button').forEach(y => y.classList.toggle('sel', y === x)); apercu(); }));
    const on = D.querySelector('.ms-stats-on');
    if (on) on.onchange = () => { statsOn = on.checked;
      if (statsOn) for (const k of Object.keys(MS_STAT)) if (V['stats.' + k] === '') V['stats.' + k] = 200;
      panneau(); };
  };
  apercu(); panneau();
  f.querySelector('.ms-aide-txt').textContent = joueur ? 'Vide ou « comme l’original » : rien ne change' : 'Partie des valeurs de l’original : seules celles que tu changes sont écrites';
  const envoyer = async stats => {
    const e = f.querySelector('.ms-etat'); e.textContent = 'Écriture…';
    try { const q = await api('/api/stats', { mod: c.mod, code, stats });
      if (!q.ok) { e.textContent = q.erreur; return; }
      f.close(); majRapport(q.rapport.join('\n'));
      $('hub-etat').textContent = 'Stats enregistrées. Pour le mettre dans le jeu : « Installer » sur sa carte dans Mes créations.'; chargerHub();
    } catch (x) { e.textContent = x.message; } };
  f.querySelector('.ms-original').onclick = () => envoyer({});
  f.querySelector('.ms-garder').onclick = () => {
    const out = {};
    for (const ch of r.champs) { const k = ch.cle, v = V[k]; if (v === '' || v === undefined) continue;
      if (k.startsWith('stats.')) { if (statsOn) (out.stats = out.stats || {})[k.slice(6)] = +v; } else out[k] = v; }
    envoyer(out); };
}
// (22/11, retour de muku : « j'ai fait 2 Mark et les deux ont pris les mêmes textures ») les cartes de Mes créations
// trouvaient leur projet par le seul code de l'ORIGINAL : deux copies de Mark montraient le même projet (image, « Modifier »).
// Chaque création garde maintenant SON projet ; sans lien, on ne devine que s'il n'y a qu'une création de cet original.
async function lierProjetCreation(mod, code) {
  if (!E.tech || !code) return;
  E.cree = { mod, code: String(code) }; E.sigProjet = null;
  try { await sauverProjet(); } catch (e) { /* le lien manquera, rien de plus */ }
}
for (const [nom, mod] of [['exporter', 'MesTechniques'], ['exporterPerso', 'MesEsprits'], ['cpExporter', 'MesPersonnages'], ['ctExporter', 'MesPersonnages'],
  ['coExporter', 'MesPersonnages'], ['cuExporter', 'MesTenues'], ['ojExporter', 'MesObjets'], ['caExporter', 'MesEsprits']]) {
  const f0 = window[nom]; if (typeof f0 !== 'function') continue;
  window[nom] = async function (...a) { if ($('suite-creation')) $('suite-creation').remove();
    const r = await f0.apply(this, a); if (r && r.ok && (r.code || r.key)) { await lierProjetCreation(mod, r.code || r.key); await proposerSuite(mod, r.code); }
    if (r && r.ok && $('page-hub') && typeof chargerHub === 'function') chargerHub();
    return r; };
}
function projetDe(c) {
  const lie = HUB.projets.find(p => p.cree && p.cree.mod === c.mod && p.cree.code === String(c.code));
  if (lie) return lie;
  const memes = HUB.creations.filter(x => x.base === c.base && x.onglet === c.onglet).length;
  return memes === 1 ? HUB.projets.find(p => p.code === c.base && p.onglet === c.onglet && !p.cree) || null : null;
}
async function ouvrirTechniqueLiee(c) {
  const f = fenetreCoups('Technique de ' + c.nom, '<div class="fc-corps">Lecture…</div>');
  let r; try { r = await api('/api/technique_liee?code=' + encodeURIComponent(c.code)); } catch (e) { f.querySelector('.fc-corps').textContent = e.message; return; }
  if (!r.ok) { f.querySelector('.fc-corps').textContent = r.erreur; return; }
  // (15/11/2026) ✦ = ton esprit apparaît dans la cinématique (la sienne, ou un autre esprit aux mêmes os) ; sinon il y est caché
  const esp = x => r.esprits[x.code], lib = x => libCoup(x) + (esp(x) ? (esp(x)[1] ? ' ✦' : ' · esprit ' + esp(x)[0]) : '');
  const tous = [...r.mes, ...r.catalogue], parLib = new Map(tous.map(x => [lib(x), x]));
  const act = r.actuelle ? tous.find(x => x.id === r.actuelle.id) : null;
  const etat = x => !x ? '' : !esp(x) ? 'Cinématique sans esprit guerrier : rien à changer dedans.'
    : esp(x)[2] === r.base ? `✦ ${c.nom} apparaît dans la cinématique (c'est celle de son esprit d'origine).`
    : esp(x)[1] ? `✦ ${c.nom} apparaît dans la cinématique avec les animations de l'esprit ${esp(x)[0]} (tous ses os existent dans ${c.nom}).`
    : `Cinématique faite pour l'esprit ${esp(x)[0]} : ses os ne sont pas tous dans ${c.nom}, il y sera caché.`;
  f.querySelector('.fc-corps').outerHTML = `<div class="fc-corps">${[...tous].sort((a, b) => (b.mod ? 2 : 0) + (esp(b) && esp(b)[1] ? 1 : 0) - (a.mod ? 2 : 0) - (esp(a) && esp(a)[1] ? 1 : 0))
      .reduce((h, x) => h + `<option value="${echapper(lib(x))}">`, '<datalist id="fc-liees">') + '</datalist>'}
    <p class="fc-note">La technique que ${echapper(c.nom)} donne en jeu (comme Michael et sa Lumière de Michael). ★ = tes techniques.
      <br>Sans choix : celle de ${echapper(r.nom_base)}${r.origine ? ' — <b>' + echapper(r.origine.nom) + '</b>' : ''}.</p>
    <p class="fc-note">✦ = ${echapper(c.nom)} apparaît dans la cinématique de la technique (en haut de la liste).</p>
    <div class="fc-ligne"><span class="fc-case">Technique</span><input class="fc-nom" list="fc-liees" placeholder="Tape pour chercher" value="${echapper(act ? lib(act) : '')}"></div>
    <div class="fc-repris fc-scene">${echapper(etat(act))}</div>
    <div class="fc-boutons"><button data-f="origine">Remettre celle d’origine</button><button class="primaire" data-f="garder">Enregistrer</button></div><div class="fc-etat"></div></div>`;
  f.querySelector('.fc-nom').oninput = e => { f.querySelector('.fc-scene').textContent = etat(parLib.get(e.target.value.trim())); };
  const envoyer = async t => {
    const e = f.querySelector('.fc-etat'); e.textContent = 'Écriture…';
    try { const q = await api('/api/technique_liee', { code: c.code, technique: t });
      if (!q.ok) { e.textContent = q.erreur; return; }
      f.close();
      // (22/11, « on n'a besoin que de créer ») enregistrée dans la création ; « Installer » sur sa carte pour le jeu
      $('hub-etat').textContent = 'Technique liée enregistrée. Pour le mettre dans le jeu : « Installer » sur sa carte dans Mes créations.'; chargerHub();
    } catch (x) { e.textContent = x.message; } };
  f.querySelector('[data-f="origine"]').onclick = () => envoyer(null);
  f.querySelector('[data-f="garder"]').onclick = () => {
    const v = f.querySelector('.fc-nom').value.trim(), x = parLib.get(v);
    if (!x) { f.querySelector('.fc-etat').textContent = v ? `« ${v} » : choisis-la dans la liste qui s’ouvre quand tu tapes.` : 'Choisis une technique, ou « Remettre celle d’origine ».'; return; }
    envoyer(x.id); };
}


// ------------------------------------------------------------------ (15/11/2026) hub façon menus du jeu
// Images des menus du jeu (moteur/menus_jeu.py, /api/menus_jeu) : grandes icônes en couleur (planche 3 x 3 : 0 joueur, 1 sac,
// 2 fiche, 3 cartes, 4 livre Y, 5 cadeau, 6 réglages, 7 enveloppe, 8 Y) et petites (6 x 5 : 16 esprit, 9 orbe, 25 veste,
// 27 épée et bouclier, 2 livre à la loupe…), fond à empreintes, fond orange au « Y ».
const ONGLETS_HUB = [
  { o: 'techniques', nom: 'Techniques', ic: 'm4', tag: 'TECH' }, { o: 'esprits', nom: 'Esprits guerriers', ic: 'p16', tag: 'ESP' },
  { o: 'totems', nom: 'Totems', ic: 'p9', tag: 'TOT' }, { o: 'bannieres', nom: 'Bannières', ic: 'm2', tag: 'BAN' },
  { o: 'maillots', nom: 'Maillots', ic: 'm1', tag: 'MAIL' }, { o: 'tenues', nom: 'Tenues', ic: 'p25', tag: 'TEN' },
  { o: 'armures', nom: 'Armures', ic: 'p27', tag: 'ARM' }, { o: 'personnages', nom: 'Personnages', ic: 'm0', tag: 'PERSO' },
  { o: 'objets', nom: 'Objets', ic: 'm5', tag: 'OBJ' }];
let MJ = null;
async function chargerMenusJeu() {
  if (MJ) return MJ;
  try { MJ = await api('/api/menus_jeu'); } catch (e) { MJ = {}; }
  const p = $('page-hub');
  if (MJ.fond) p.style.setProperty('--jm-fond', `url("${MJ.fond.url}")`);
  if (MJ.fond_orange) p.style.setProperty('--jm-fond-orange', `url("${MJ.fond_orange.url}")`);
  return MJ;
}
function iconeJeu(ic, t) {             // ic = 'm4' (grandes icônes) ou 'p16' (petites) ; t = taille en pixels
  const P = MJ && MJ[ic[0] === 'm' ? 'icones_menu' : 'petites_icones'], z = P && P.zones[+ic.slice(1)];
  if (!z) return `<i class="jm-icone" style="width:${t}px;height:${t}px"></i>`;
  const k = t / Math.max(z[2], z[3]);
  return `<i class="jm-icone" style="width:${t}px;height:${t}px;background-image:url('${P.url}');background-size:${P.w * k}px ${P.h * k}px;`
    + `background-position:${-z[0] * k}px ${-z[1] * k}px"></i>`;
}
function dessinerMenuJeu() {
  document.querySelectorAll('#page-hub [data-ic]').forEach(e => { e.outerHTML = iconeJeu(e.dataset.ic, +e.dataset.t || 40); });
  const n = (L, o) => L.filter(x => x.onglet === o).length;
  $('hub-n-tout').textContent = HUB.projets.length + HUB.creations.length;
  $('hub-n-installees').textContent = HUB.creations.filter(c => c.installe || c.jeuSeul).length;
  const img = (b, v) => { const e = $(b).querySelector('.jm-b-img'); if (v) e.style.setProperty('--img', `url("${v}")`); else e.style.removeProperty('--img'); };
  img('jm-b-continuer', (HUB.projets.find(p => p.vignette && !p.vignetteTexture) || HUB.projets.find(p => p.vignette) || {}).vignette);
  img('jm-b-terminees', (HUB.creations.find(c => c.vignette) || {}).vignette);
  $('jm-b-continuer').onclick = () => $('jm-s-continuer').scrollIntoView({ behavior: 'smooth' });
  $('jm-b-terminees').onclick = () => $('jm-s-terminees').scrollIntoView({ behavior: 'smooth' });
  // tuiles : un onglet chacune, + préréglages et nouvelle création
  const T = $('jm-tuiles'); T.innerHTML = '';
  const tuiles = [...ONGLETS_HUB.map(x => ({ ...x, act: () => window.changerOnglet(x.o) })),
    { nom: 'Préréglages', ic: 'm6', act: () => $('jm-s-prereglages').scrollIntoView({ behavior: 'smooth' }) },
    { nom: 'Nouvelle création', ic: 'p2', act: () => { window.changerOnglet('techniques'); $('cherche').focus(); } }];
  for (const x of tuiles) {
    const b = document.createElement('button'); b.className = 'jm-tuile'; b.title = x.nom;
    b.innerHTML = `<span class="jm-tuile-fond"></span>${iconeJeu(x.ic, 78)}`;
    b.onmouseenter = b.onfocus = () => { $('jm-etiquette').textContent = x.nom; T.querySelectorAll('.sel').forEach(e => e.classList.remove('sel')); b.classList.add('sel'); };
    b.onclick = x.act; T.appendChild(b); }
  // filtres par genre (onglets de la Banque)
  const O = $('jm-onglets'); O.innerHTML = '';
  const L = [...HUB.projets, ...HUB.creations];
  for (const x of [{ o: '', nom: 'TOUT' }, ...ONGLETS_HUB.filter(g => n(L, g.o))]) {
    const b = document.createElement('button'); b.className = 'jm-onglet' + ((HUB.filtre || '') === x.o ? ' sel' : ''); b.title = x.nom;
    b.innerHTML = x.o ? `${iconeJeu(x.ic, 30)}<b>${n(L, x.o)}</b>` : 'TOUT';
    b.onclick = () => { HUB.filtre = x.o; dessinerHub(); }; O.appendChild(b); }
}
document.addEventListener('keydown', ev => {        // X : chercher par nom (comme la Banque), seulement au hub et hors d'un champ
  if ((ev.key === 'x' || ev.key === 'X') && $('page-hub') && $('page-hub').offsetParent !== null && !/INPUT|TEXTAREA|SELECT/.test(document.activeElement.tagName)) {
    ev.preventDefault(); $('hub-cherche').focus(); } });
