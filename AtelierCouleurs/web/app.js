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
// (25/11, demande de danifdez) TYPE D'ÉVOLUTION d'une technique (skill_config growthType 0-7), LU dans le jeu
// (soccer_common GetSkillEvoCode) : 1-3 God, 4-6 Infinity, 7 GO, 0 aucun ; marques gaiji_wlvNNN des niveaux 2 à 5 de la
// planche gaiji_game2 de la langue (fr : 2 3 4 4X 5 / V2 V3 V4 A ∞ / N2 N3 N4 Nx GO ; en : +1… / L2…)
const EVOL_CODES = t => t >= 1 && t <= 3 ? ['101', '102', '103', ['104', '114', '124'][t - 1], '105']
  : t >= 4 && t <= 6 ? ['201', '202', '203', ['204', '214', '224'][t - 4], '205'] : t === 7 ? ['301', '302', '303', '304', '305'] : [];
const nomEvol = t => (+t >= 1 && +t <= 3 ? 'God' : +t >= 4 && +t <= 6 ? 'Infinity' : +t === 7 ? 'GO' : 'Aucune');
const marquesEvol = (t, h) => EVOL_CODES(+t).map(c => `<img class="evol-marque" src="/ui_jeu/zone/gaiji_game2/${['en', 'es'].includes(window.ATELIER_LANGUE) ? window.ATELIER_LANGUE : 'fr'}/gaiji_wlv${c}.png" alt="" style="height:${h}px" onerror="this.remove()">`).join('');
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
        acteurs: Object.values(acteursD3D), pieds, statut: V._statut || null, statuts: V._statuts || [],   // (25/11) une par personnage
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
                stade: st ? { ombres: st.ombres, acteurs: st.acteurs, pieds: st.pieds, statut: st.statut, statuts: st.statuts, foyer: st.foyer } : null });
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
  if (NATIF.hote && NATIF.hote.isConnected) {               // (23/11) aperçu d'invocation d'un esprit : la zone de l'aperçu
    const c = NATIF.hote.getBoundingClientRect(), d = devicePixelRatio || 1;
    return [c.left * d, c.top * d, c.width * d, c.height * d, innerWidth * d, innerHeight * d].map(Math.round);
  }
  if ($('centre').classList.contains('dans-stats')) {        // (23/11) aperçu de la fenêtre des stats : toute la vue, sans barres
    const c = $('vue').getBoundingClientRect(), d = devicePixelRatio || 1;
    return [c.left * d, c.top * d, c.width * d, c.height * d, innerWidth * d, innerHeight * d].map(Math.round);
  }
  const c = $('vue').getBoundingClientRect(), hb = document.querySelector('.barre-vue').getBoundingClientRect(), lb = $('lecteur').getBoundingClientRect();
  const haut = Math.max(c.top, hb.bottom + 2), bas = Math.min(c.bottom, lb.top - 2), d = devicePixelRatio || 1;
  // + taille de la page (le lecteur place la page en bas de la zone cliente de la fenêtre d'Edge)
  return [c.left * d, haut * d, c.width * d, Math.max(0, bas - haut) * d, innerWidth * d, innerHeight * d].map(Math.round);
}
function cmdNatif(cmd, attendre) { return api('/api/natif_cmd', { cmd, attendre: !!attendre }).catch(() => ({ actif: false })); }
function finNatif(envoyer) {
  // (14/11/2026) aussi pendant un lancement : le lecteur en chargement est arrêté par le serveur, et le lancement en cours
  // est annulé (numéro de lancement changé : sa réponse referme le lecteur au lieu de l'afficher)
  // (23/11, retour de muku : « changer l'apparition ne s'actualise pas ») « quitter » VISE le lecteur lancé (pid) : sans pid
  // le serveur arrêtait TOUS les lecteurs, y compris le suivant déjà lancé si la réponse arrivait après. Pendant un lancement
  // (pas encore de pid) rien n'est envoyé : le serveur arrête l'ancien avant d'en lancer un, et la réponse annulée referme le sien.
  if (envoyer && NATIF.pid) api('/api/natif_cmd', { cmd: 'quitter', pid: NATIF.pid }).catch(() => {});
  else if (envoyer && NATIF.actif) cmdNatif('quitter');
  if (envoyer) NATIF.pid = null;
  if (envoyer) { NATIF.numero = (NATIF.numero || 0) + 1; NATIF.lance = false; }
  NATIF.actif = false; NATIF.cle = null; clearInterval(NATIF.minuteur); NATIF.minuteur = null;
  if (envoyer) NATIF.imageVoulue = undefined;
  if (E.vue) E.vue.cv.style.visibility = ''; $('l-jouer').textContent = '▶';
}
// (22/11, retour de muku : « les paramètres vont derrière aussi ») ce qui s'ouvre PAR-DESSUS la vue cache le lecteur natif
// (une vraie fenêtre, toujours devant la page) : liste des résultats (17/11), fenêtre ⚙ Paramètres, fenêtres <dialog>
// (Tableau des compétences, technique liée)
function natifRecouvert() {
  const res = $('resultats');
  // (23/11) fenêtre qui CONTIENT la vue (aperçu de « En attente de stats / cosmétique ») : elle ne la recouvre pas
  const dlg = [...document.querySelectorAll('dialog[open]')].some(d => !d.contains($('centre')) && !(NATIF.hote && d.contains(NATIF.hote)));
  return (res && res.style.display === 'block') || !!document.querySelector('#parametres.ouvert') || dlg;
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
    // (23/11) + renvoyée toutes les 2 s même sans changement : un lecteur qui a reçu une autre zone (commande perdue, ou zone d'un
    // lancement précédent) se recale tout seul
    NATIF.tic = ((NATIF.tic || 0) + 1) % 10;
    if (r !== NATIF.rect || !NATIF.tic) { NATIF.rect = r; cmdNatif('rect ' + r); }
    optionsNatif();                              // (15/11/2026) pièces cachées / couleurs changées : envoyées sans relancer
    const numero = NATIF.numero, e = await cmdNatif('etat', true);
    // (23/11, retour de muku) réponse arrivée APRÈS la fermeture du lecteur (changement d'onglet…) : ignorée (elle réécrivait
    // « lecteur C++ » et ❚❚ sur une barre vide)
    if (!NATIF.actif || NATIF.numero !== numero) return;
    // (23/11) un « etat » sans réponse (page occupée) ne veut pas dire lecteur fermé : 5 de suite (1 s) avant de le croire
    if (!e.actif) { NATIF.rates = (NATIF.rates || 0) + 1; if (NATIF.rates >= 5) { NATIF.rates = 0; finNatif(false); } return; }
    NATIF.rates = 0;
    const ch = e.etat && e.etat.match(/choix (\d+) (\S+)/);      // (15/11/2026) clic sur la vidéo du lecteur natif
    if (ch && !NATIF.hote) { if (NATIF.choixN === undefined) NATIF.choixN = +ch[1]; else if (+ch[1] !== NATIF.choixN) { NATIF.choixN = +ch[1]; choisirDepuisVue(ch[2], false); } }
    const m = e.etat && e.etat.match(/image (\d+) (\d+) pause (\d)/);
    // (23/11) image demandée à l'ouverture : renvoyée tant que le lecteur n'est pas en pause dessus
    if (m && NATIF.imageVoulue !== undefined) { if (+m[1] === NATIF.imageVoulue && m[3] === '1') NATIF.imageVoulue = undefined; else cmdNatif('image ' + NATIF.imageVoulue); }
    if (m) { if (document.activeElement !== $('l-image')) $('l-image').value = +m[1];
      $('l-info').textContent = `${window.I18N ? I18N.trad('image') : 'image'} ${m[1]} / ${m[2]} · ${window.I18N ? I18N.trad('Lecteur natif') : 'Lecteur natif'}`; $('l-jouer').textContent = m[3] === '1' ? '▶' : '❚❚'; }
  }, 200);
}
// (15/11/2026) options du lecteur natif (pièces cachées, couleurs de matériau, teintes) : réécrites et relues par le lecteur
// ouvert (commande « options ») -> cacher / isoler / changer une couleur ne relance plus la vidéo
// (23/11) teinte de sommets / particules -> [H, C, S] (S = saturation de VRFW, multiplicateur ; 1 = gardée)
const tsc = t => [t.H, t.C, t.S === undefined ? 1 : t.S, t.V === undefined ? 1 : t.V];   // (23/11) + V = luminosité (value de VRFW)
function optionsActuelles() {
  const V = E.vue;
  return { caches: V.pieces.filter(p => p.cle && !p.visible && !p.cle.startsWith('stade/') && !p.peau && !p.terrain).map(p => p.cle),
    couleurs: couleursNatif(), sommets: E.avant ? {} : Object.fromEntries(Object.entries(E.teinteSom || {}).map(([k, t]) => [k, tsc(t)])),
    particules: E.avant ? {} : Object.fromEntries(Object.entries(E.teintePtl || {}).map(([k, t]) => [k, tsc(t)])),
    lumieres: E.avant ? {} : Object.assign({}, E.lumK || {}),   // (23/11) intensité des lumières de l'effet, par objet
    auras: E.avant ? {} : aurasChoisies(),
    // (25/11, retour d'enhanc3) « Fil de fer sélection » aussi dans le lecteur du jeu : pièces sélectionnées (pas les particules)
    fil: V.fil ? V.pieces.filter(p => p.sel && p.cle && !p.ptl && !p.peau && !p.cle.startsWith('stade/')).map(p => p.cle) : [] };   // (25/11) couleurs d'aura cochées : vues dans le lecteur du jeu (comme l'export)
}
// (25/11, muku : « montre les auras dans l'aperçu ») couleurs d'aura cochées {nom : [r, v, b] (0..1)} : lecteur du jeu (options.json
// « auras ») et aperçu WebGL (Vue3D.aurasCouleurs), même recoloration que l'export (_cles_aura : couleur du modèle + lueur)
function aurasChoisies() {
  const out = {};
  document.querySelectorAll('[data-aura]').forEach(cb => { if (!cb.checked || cb.disabled) return;
    const c = document.querySelector(`[data-aura-c="${CSS.escape(cb.dataset.aura)}"]`); if (c) out[cb.dataset.aura] = hex2rgb(c.value); });
  return out;
}
function majAurasVue() {                         // (25/11) aperçu WebGL tout de suite, lecteur du jeu par options.json (sans relancer)
  if (E.vue) { E.vue.aurasCouleurs = E.avant ? {} : aurasChoisies(); Vue3D.activite = performance.now(); }
  if (NATIF.actif) optionsNatif();
}
async function optionsNatif() {
  if (!NATIF.actif || NATIF.hote || !E.tech || !E.vue || NATIF.envoiOpt) return;
  const o = optionsActuelles(), j = JSON.stringify(o); if (j === NATIF.opt) return;
  NATIF.envoiOpt = true;
  try { const r = await api('/api/natif_options', Object.assign({ technique: E.tech.code }, o)).catch(() => ({ actif: false }));
    if (r.actif) { NATIF.opt = j; NATIF.cle = cleNatif().cle; } } finally { NATIF.envoiOpt = false; }
}
function cleNatif() {
  const V = E.vue;
  const caches = V.pieces.filter(p => p.cle && !p.visible && !p.cle.startsWith('stade/') && !p.peau && !p.terrain).map(p => p.cle);
  const versions = Object.entries(E.textures).filter(([, x]) => x.modif).map(([k, x]) => k + JSON.stringify(x.moyenne)).join('|');
  return { caches, cle: [E.tech.code, E.avant ? 'avant' : versions, caches.join(','), JSON.stringify(E.coulMat || {}), JSON.stringify(E.teinteSom || {}), JSON.stringify(E.teintePtl || {}), JSON.stringify(E.lumK || {})].join('#') };
}
// (14/11/2026) couleurs de matériau choisies -> par pièce (options.json du lecteur natif : « couleurs »)
function couleursNatif() {
  const out = {};
  for (const o of E.objets) for (const p of o.pieces || []) { const c = couleurMat(o, p); if (c) out[o.nom + '/' + p.index] = c.rgb; }
  return out;
}
async function modifsNatif() {                  // textures recolorées dans l'Atelier (RGBA en base64)
  const modifs = {}; if (E.avant) return modifs;          // (15/11/2026) « avant » : textures d'origine
  for (const [k, x] of Object.entries(E.textures)) if (x.modif && x.cur && x.cur.getContext && !k.startsWith('mm/')) {
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
// (24/11, demande d'enhanc3 : « comme les Keshin, isolés dans une pose par défaut pour retoucher leurs textures : et les éléments des
// techniques, comme les pingouins ? ») OBJET SEUL : l'objet de la texture choisie, montré seul dans l'aperçu de l'Atelier, au repos
// (son maillage tel qu'il est dans son fichier) ou à l'image courante, caméra libre. Ne change NI la visibilité des pièces, NI le
// projet, NI ce qui part au lecteur du jeu ou à l'export (Vue3D.isole / repos). Le lecteur du jeu (caméra du jeu) est fermé
// pendant ce temps ; « ✕ Tout revoir », ▶, une autre technique ou un autre onglet ramènent la technique entière.
function piecesObjet(o, nomTex) {
  const V = E.vue, s = new Set(); if (!V || !o) return s;
  // effet : seulement les pièces qui portent cette texture (la vrille, pas les flashs ni les dômes de tout l'objet)
  const avec = new Set((o.pieces || []).filter(q => nomTex && (q.textures || []).includes(nomTex)).map(q => o.nom + '/' + q.index));
  if (nomTex && !avec.size && (o.pieces || []).length) return s;      // texture des seules particules : rien à montrer seul
  for (const p of V.pieces) if (!p.ptl && !p.peau && !p.versionCachee && p.cle && (avec.size ? avec.has(p.cle) : p.cle.startsWith(o.nom + '/'))) s.add(p);
  if (!s.size) {     // modèle animé par os (pingouins…) : les maillages d'UN acteur (plusieurs pingouins = le même modèle)
    const pp = V.pieces.filter(p => p.peau && !p.versionCachee && p.texCle && p.texCle.replace(/^peau:/, '').startsWith(o.nom + '/'));
    const ac = pp.length ? pp[0].peau.acteur : null;
    // deux versions du modèle dans le même acteur (dragon clair _10 / sombre _20 de Choc de la vouivre) : celle de la texture choisie
    const ver = n => (/_(\d\d)[a-z]*$/.exec(n || '') || [])[1], v0 = ver(nomTex);
    if (ac !== null) for (const p of V.pieces) if (p.peau && p.peau.acteur === ac && !p.versionCachee && (!v0 || !ver(p.texCle) || ver(p.texCle) === v0)) s.add(p);
  }
  return s;
}
const avecTex = (o, n) => (o.pieces || []).some(q => (q.textures || []).includes(n)) && !(o.pieces || []).every(q => (q.textures || []).includes(n));
async function isolerObjet(cleTex) {
  const V = E.vue; if (!V || !E.tech || E.tech.perso) return majRapport('« Voir seul » sert aux techniques (onglet Techniques).');
  const x = cleTex && E.textures[cleTex], o = x && x.obj;
  if (!o) return majRapport('Choisis d’abord une texture de l’objet à voir seul (clic sur une vignette).');
  let s = piecesObjet(o, x.nom);
  // modèle animé (pingouins…) : chargé avec l'animation, quelques secondes après l'ouverture -> on l'attend
  if (!s.size && o.modeleActeur) { const t = E.tech; majRapport('Chargement du modèle…');
    for (let k = 0; k < 60 && !s.size && E.tech === t && E.vue === V; k++) { await new Promise(r => setTimeout(r, 250)); s = piecesObjet(o, x.nom); }
    if (E.tech !== t || E.vue !== V) return; }
  if (!s.size) return majRapport('Cet objet n’a pas de maillage à montrer seul (particules ou image).');
  if (!E.isole) E.isoleAvant = { cameraJeu: V.cameraJeu, centre: V.centre && V.centre.slice(), dist: V.dist, yaw: V.yaw, pitch: V.pitch };
  finNatif(true);
  E.isole = avecTex(o, x.nom) ? x.nom : o.nom; V.isole = s; V.repos = !$('iso-image') || !$('iso-image').checked; V.joue = false; V.cameraJeu = false;
  for (const p of s) if (p.peau) p.peau._repos = false;
  V.recadrer(true); V.dist *= 1.3; Vue3D.activite = performance.now(); majIsole();
  majRapport('« ' + (avecTex(o, x.nom) ? x.nom : o.nom) + ' » seul dans l’aperçu de l’Atelier : glisse pour tourner, molette pour zoomer. Tes retouches s’y voient tout de suite. « ✕ Tout revoir » pour revenir à la technique.');
}
function quitterIsolement(relancer) {
  const V = E.vue; if (!E.isole) return; E.isole = null;
  if (V) { V.isole = null; const a = E.isoleAvant || {}; if (a.cameraJeu !== undefined) V.cameraJeu = a.cameraJeu;
    if (a.centre) { V.centre = a.centre; V.dist = a.dist; V.yaw = a.yaw; V.pitch = a.pitch; }
    for (const p of V.pieces) if (p.peau) p.peau._repos = false; Vue3D.activite = performance.now(); }
  majIsole();
  if (relancer !== false && E.onglet === 'techniques' && V && V.lecteur) natifSurImage(Math.floor(V.image || 0));
}
function majIsole() {
  const c = $('centre'); if (!c) return;
  let d = $('iso-vue');
  if (!d) { d = document.createElement('div'); d.id = 'iso-vue';
    d.innerHTML = '<span class="iso-titre">Objet seul : <b></b></span><label title="Coché : la pose de l’image courante de l’animation ; décoché : au repos (maillage tel qu’il est dans son fichier)"><input type="checkbox" id="iso-image"> À l’image courante</label>'
      + '<button id="iso-quitter" title="Revenir à la technique entière (lecteur du jeu)">✕ Tout revoir</button>';
    c.appendChild(d);
    d.querySelector('#iso-quitter').onclick = () => quitterIsolement();
    d.querySelector('#iso-image').onchange = e => { const V = E.vue; if (!V) return; V.repos = !e.target.checked; for (const p of V.pieces) if (p.peau) p.peau._repos = false;
      if (V.repos) { V.recadrer(true); V.dist *= 1.3; } Vue3D.activite = performance.now(); };
  }
  d.hidden = !E.isole; if (E.isole) d.querySelector('b').textContent = E.isole;
  const b = $('tex-isoler'); if (b) b.classList.toggle('actif', !!E.isole);
}

// (23/11, muku : « fais tout ce que tu peux en natif ») l'image d'une technique = celle du LECTEUR DU JEU (vrais shaders) :
// à l'ouverture, au curseur, aux flèches, il s'ouvre en pause sur l'image voulue. L'aperçu WebGL (approché : pas les vraies
// couleurs du jeu) ne se voit plus que pendant son chargement, ou s'il est fermé / indisponible, avec une mention.
async function natifSurImage(f) {
  const V = E.vue; if (!V || !V.lecteur || !E.tech || E.tech.perso || NATIF.hote || E.isole) return;     // (24/11) pas pendant « objet seul »
  if (NATIF.actif && NATIF.cle === cleNatif().cle) { NATIF.imageVoulue = f; cmdNatif('image ' + f); return; }
  NATIF.imageVoulue = f;
  if (NATIF.lance) return;                       // lancement en cours : l'image sera posée à l'ouverture
  try { await lecteurNatif(); } catch (e) { /* l'aperçu approché reste */ }
}
async function natifAuto(t) {                   // ouverture d'une technique dans l'onglet Techniques : lecteur en pause sur l'image 0
  for (let k = 0; k < 240 && E.tech === t && !(E.lecteur && E.stadeCode); k++) await new Promise(r => setTimeout(r, 250));
  const stats = $('menu-stats') && $('menu-stats').open;
  if (E.tech !== t || !E.lecteur || !E.stadeCode || E.onglet !== 'techniques' || stats || $('centre').classList.contains('dans-stats')
    || NATIF.actif || NATIF.lance || NATIF.hote || E.isole) return;
  activerAnimation(true); E.vue.joue = false; E.vue.image = 0;
  natifSurImage(0);
}
function majApproche() {                        // mention sur l'aperçu WebGL quand c'est lui qu'on voit
  const tl = $('l-telop'); if (tl && tl.style.display !== 'none' && !telopWebVisible()) tl.style.display = 'none';   // (23/11) bannière WebGL
  const v = $('centre'); if (!v) return;          // (#vue est le canevas : la mention va dans #centre, par-dessus)
  let d = $('vue-approche');
  if (!d) { d = document.createElement('div'); d.id = 'vue-approche'; v.appendChild(d); }
  const tech = E.tech && !E.tech.perso && E.onglet === 'techniques';
  const voir = tech && !NATIF.actif && !(E.vue && E.vue.cv.style.visibility === 'hidden');
  d.style.display = voir ? '' : 'none';
  if (voir) d.textContent = NATIF.lance ? 'Aperçu approché · le lecteur du jeu se charge…'
    : 'Aperçu approché (pas les vraies couleurs du jeu) · ▶, ← → ou le curseur ouvrent le lecteur du jeu';
}
setInterval(majApproche, 300);
async function lecteurNatif() {
  if (E.isole) quitterIsolement(false);           // (24/11) ▶ pendant « objet seul » : la technique entière revient
  const V = E.vue; if (!V || !V.lecteur || !E.tech) return;
  const { caches, cle } = cleNatif();
  // déjà ouvert : lecture / pause. (23/11) ordre EXPLICITE d'après le bouton (« basculer » pendant le chargement, quand le lecteur
  // ne s'est pas encore mis en pause sur l'image demandée, le mettait en pause au lieu de lancer la lecture)
  if (NATIF.actif && NATIF.cle === cle) { NATIF.imageVoulue = undefined; const jouer = $('l-jouer').textContent !== '❚❚';
    const r = await cmdNatif(jouer ? 'pause 0' : 'pause 1'); if (r.actif) { $('l-jouer').textContent = jouer ? '❚❚' : '▶'; return; } finNatif(false); }
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
      particules: opt.particules, lumieres: opt.lumieres, auras: opt.auras, fil: opt.fil, largeur: w, hauteur: h, incruste: true, rect, jeton });
    if (r.erreur) { $('l-film-info').textContent = 'Lecteur natif : ' + r.erreur; return; }
    if (NATIF.numero !== numero || !E.tech || E.vue !== V) {     // annulé pendant le lancement : CE lecteur seulement
      api('/api/natif_cmd', { cmd: 'quitter', pid: r.pid }).catch(() => {}); return; }
    NATIF.actif = true; NATIF.pid = r.pid || null; NATIF.cle = cle; NATIF.rect = rect.join(' '); NATIF.choixN = undefined; NATIF.opt = JSON.stringify(optionsActuelles()); V.cv.style.visibility = 'hidden'; suivreNatif();
    // (23/11) ouvert pour une image précise (curseur, flèches, ouverture de la technique) : en pause sur elle (commande gardée
    // par le lecteur pendant son chargement)
    // (renvoyée par suivreNatif jusqu'à ce que le lecteur la confirme : au lancement, il n'écoute pas encore)
    if (NATIF.imageVoulue !== undefined) cmdNatif('image ' + NATIF.imageVoulue);
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
  quitterIsolement(false);                         // (24/11) « objet seul » : fini avec l'ancienne technique
  await sauverProjet();                            // (15/11/2026) dernier changement de la technique d'avant gardé
  finNatif(true);
  $('resultats').style.display = 'none';
  $('titre-tech').textContent = 'Chargement… (la 1re ouverture d\'un modèle lit ses textures : quelques secondes)';
  const perso = estPerso();
  const t = await api(perso ? '/api/personnage?code=' + encodeURIComponent(code) + (ONGLETS_JEU.includes(E.onglet) ? '&cat=' + E.onglet + (E.onglet === 'maillots' ? '&cote=' + (MM.cote || '10') : '') : '') : '/api/technique?code=' + code);
  E.tech = t; E.tech.perso = perso; E.tech.onglet = E.onglet; E.objets = t.objets_details; E.textures = {}; E.coulMat = {}; E.teinteSom = {}; E.teintePtl = {}; E.lumK = {}; E.selPieces.clear(); E.selTex.clear();
  { const inv = !!t.invocation_de;                  // (25/11) apparition d'un esprit guerrier : ses couleurs, pas une technique
    if ($('exporter')) $('exporter').textContent = inv ? 'Enregistrer les couleurs de l’apparition' : 'Créer le mod';
    document.querySelectorAll('#f-nom, #f-desc').forEach(x => { const l = x.closest('label'); if (l) l.hidden = inv; }); }
  retirerSuite();                                   // (22/11) les suites d'une création précédente ne concernent pas celle-ci
  // (28/11, banc d'essai) nouvel élément : noms / descriptions des copies vides (avant : ceux de l'élément d'avant restaient ->
  // « Créer » reprenait un ancien nom) ; « Modifier » et la reprise d'un projet les remplissent ensuite
  for (const id of ['ct-nom', 'ct-desc', 'cu-nom', 'cu-desc', 'co-nom', 'co-desc', 'ca-nom']) if ($(id)) $(id).value = '';
  if (!(E.repriseAuto && E.repriseAuto === E.projet)) E.cree = null;   // (22/11) même projet (côté du maillot) : lien gardé
  E.avant = false; majBoutonAvant(); E.recette = []; E.pileRc = []; E.rev = 0; E.reprise = false; E.sigProjet = null; E.chargement = true; E.projet = E.repriseAuto || nouvelleCleProjet(E.onglet, code); E.repriseCle = E.repriseAuto; E.repriseAuto = null; E.texturesCachees = new Set(); E.texturesMontrees = new Set(); E.vignette = null; E.vignetteT = 0; E.vignetteManque = false; if ($('reprise')) $('reprise').style.display = 'none';   // (15/11/2026) pas de sauvegarde pendant le chargement
  if (perso) { $('titre-tech').textContent = `${t.nom}  ·  ${t.code}  ·  ${t.genre}`;
    $('p-nom').value = t.nom + ' (couleurs)'; $('p-desc').value = ''; if ($('rt-nom')) $('rt-nom').value = t.nom + ' (couleurs)'; if ($('cp-nom')) { $('cp-nom').value = ''; $('cp-nom').placeholder = t.nom + ' bis'; }
    if (E.onglet === 'personnages' && typeof cpPeauOuvrir === 'function') cpPeauOuvrir(code);
    if (E.onglet === 'personnages' && typeof cpCorpsOuvrir === 'function') cpCorpsOuvrir(code); }
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
  const geantes = perso ? [] : E.vue.cacherGeantes(); E.vue.recadrer(true); teintesPieces(); dessinerPieces(); dessinerTextures(); dessinerAuras(); dessinerMateriaux(); dessinerTeintes(); appliquerLumieres(); dessinerLumieres(); majCompteurs();
  if (!perso) chargerAnimation(t).then(() => natifAuto(t)).catch(e => majRapport('Animation non lue : ' + e.message));
  majRapport(geantes.length ? geantes.length + ' pièce(s) géante(s) cachée(s) au départ (fonds, flashs) : coche-les à gauche pour les voir.' : '');
  dessinerRecette(); paletteTech(); E.sigProjet = signatureProjet(); E.chargement = false; verifierProjet();
  if (E.modifie) { const m = E.modifie; E.modifie = null; E.cree = { mod: m.mod, code: m.code };   // (22/11) « Modifier » d'une création
    if (m.champ && $(m.champ)) $(m.champ).value = m.nom;
    if (E.onglet === 'personnages' && m.mod === 'MesPersonnages' && typeof cpCorpsOuvrir === 'function') cpCorpsOuvrir(E.tech.code); }   // (27/11) sa morphologie
  else proposerReprise();
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
    const t = document.createElement('div'); t.className = 'objet-titre'; t.textContent = o.erreur ? `${o.acteur} (illisible : ${o.erreur})` : o.espritDuJoueur ? `${o.nom}  (totem / esprit du joueur : en jeu, c’est celui du joueur qui lance — pour le recolorer, fais une copie dans Totems ou Esprits)` : o.modeleActeur ? `${o.nom}  (modèle de personnage : textures seulement)` : `${o.nom}  (${o.pieces.length} pièces)`;
      // (28/11) mode simple : « Objet 1 · 3 pièces » / « Icône » au lieu des codes
      if (!o.erreur && !o.espritDuJoueur) { const k = E.objets.indexOf(o) + 1, av = t.textContent;
        t.innerHTML = `<span class="nom-simple">${echapper(o.role === 'icone' ? 'Icône' : o.modeleActeur ? 'Textures' : (E.objets.length > 1 ? 'Objet ' + k + ' · ' : '') + o.pieces.length + ' pièce' + (o.pieces.length > 1 ? 's' : ''))}</span><span class="nom-av">${echapper(av)}</span>`; }
      box.appendChild(t);
    if (o.erreur) continue;
    o.pieces.forEach((p, kp) => {
      const cle = o.nom + '/' + p.index, d = document.createElement('div'); d.className = 'piece' + (E.selPieces.has(cle) ? ' sel' : ''); d.dataset.cle = cle;
      const cb = document.createElement('input'); cb.type = 'checkbox'; cb.checked = p.vue ? p.vue.visible : true;
      cb.onclick = ev => { ev.stopPropagation(); if (p.vue) p.vue.visible = cb.checked; };
      const pa = document.createElement('span'); pa.className = 'pastille';
      if (p.pastille) pa.style.background = `rgb(${p.pastille.map(c => Math.round(c * 255)).join(',')})`;
      const n = document.createElement('span'); n.className = 'n'; n.title = p.textures.join(', ');
      n.innerHTML = `<span class="nom-simple">${echapper('Partie ' + (kp + 1))}</span><span class="nom-av">${echapper(p.nom)} (${echapper(String(p.materiau ?? '-'))})</span>`;
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
  if (E.vue && E.vue.fil && NATIF.actif) optionsNatif();     // (25/11) fil de fer de la sélection dans le lecteur du jeu
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
    // (25/11/2026, export_modele.js) PNG de cette texture / image à sa place
    .concat(peutDessiner && window.exporterPng ? [['⬇ Enregistrer en PNG', () => exporterPng([cle]).catch(e => majRapport('Échec : ' + e.message))],['⬆ Remplacer par une image', () => choisirImages(cle)]] : [])
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
  if (!$('filtre-sel').checked || !E.selPieces.size) return Object.keys(E.textures).filter(k => !k.startsWith('mm/'));   // (24/11) icône / emblème : mode dessin seul
  const s = new Set();
  for (const o of E.objets) for (const p of o.pieces || []) if (E.selPieces.has(o.nom + '/' + p.index)) for (const n of p.textures) s.add(o.nom + '/' + n);
  for (const [o, n] of texturesParticulesChoisies()) s.add(o.nom + '/' + n);
  // modèles de personnages (esprit guerrier…) : pas de pièce à sélectionner, leurs textures restent toujours visibles
  for (const o of E.objets) if (o.modeleActeur && !o.erreur) for (const t of o.textures) s.add(o.nom + '/' + t.nom);
  return [...s];
}
// (26/11, retour d'un joueur sur Parade fatale du dragon : « la gueule reste verte ») MESURÉ : 70 pièces du tourbillon ont des
// COULEURS DE SOMMETS cyan (128, 215, 255) que le jeu multiplie avec la texture -> texture orange × sommets cyan = vert-jaune.
// Les textures recolorées à la main laissent les sommets d'origine : avertissement + « Teinter leurs sommets comme la texture »
// (teinte du bloc « Sommets et particules », la même que la pipette ; VRFW vertex_colors à l'export)
function teinteTexture(x) {                  // teinte dominante d'une texture (pondérée par saturation × valeur), ou null
  const w = x.cur.width, h = x.cur.height, d = x.cur.getContext('2d').getImageData(0, 0, w, h).data; let sx = 0, sy = 0, sw = 0;
  for (let i = 0; i < d.length; i += 16) { if (!d[i + 3]) continue; const [hh, s, v] = rgb2hsv(d[i] / 255, d[i + 1] / 255, d[i + 2] / 255), wt = s * v;
    sx += Math.cos(hh * Math.PI / 180) * wt; sy += Math.sin(hh * Math.PI / 180) * wt; sw += wt; }
  return sw < 1e-3 ? null : (Math.atan2(sy, sx) * 180 / Math.PI + 360) % 360;
}
function piecesSommetsMelanges() {
  const out = [], hues = new Map(); if (!E.tech || E.tech.perso || E.avant) return out;
  const hue = x => { if (!hues.has(x)) hues.set(x, teinteTexture(x)); return hues.get(x); };
  // (26/11, muku : « il n'est pas censé y avoir de pièce qu'on ne peut pas teinter ») texture grise / blanche (pas de couleur à
  // suivre) : la teinte des AUTRES textures modifiées du même objet (moyenne circulaire), sinon de toutes les textures modifiées
  const moyH = L => { let sx = 0, sy = 0; for (const h of L) { sx += Math.cos(h * Math.PI / 180); sy += Math.sin(h * Math.PI / 180); }
    return L.length ? (Math.atan2(sy, sx) * 180 / Math.PI + 360) % 360 : null; };
  const modH = o => Object.values(E.textures).filter(y => (!o || y.obj === o) && y.modif && y.cur && y.cur.getContext && !y.info.donnees).map(hue).filter(h => h !== null);
  const parObjet = new Map(); let toutes;
  const repli = o => { if (!parObjet.has(o)) parObjet.set(o, moyH(modH(o))); const h = parObjet.get(o);
    if (h !== null) return h; if (toutes === undefined) toutes = moyH(modH(null)); return toutes; };
  for (const o of E.objets) { if (o.erreur || o.modeleActeur || o.aura_balle) continue;
    for (const p of o.pieces || []) { if (!p.vue || !p.vue.col0) continue; const cle = o.nom + '/' + p.index; if (E.teinteSom[cle]) continue;
      const x = (p.textures || []).map(n => E.textures[o.nom + '/' + n]).find(y => y && y.modif && y.cur && y.cur.getContext && !y.info.donnees);
      if (!x) continue;
      const m = moyenneSommets(p.vue.col0); if (m.colores < 0.3 || rgb2hsv(...m.c)[1] < 0.15) continue;
      let H = hue(x); if (H === null) H = repli(o);
      if (H === null) continue;                    // aucune texture modifiée n'a de couleur : rien à suivre (réglable à la main)
      out.push({ o, p, cle, x, m, H }); } }
  return out;
}
function conseilSommets() {
  const L = piecesSommetsMelanges(); if (!L.length) return null;
  const d = document.createElement('div'); d.className = 'conseil-sommets';
  d.innerHTML = `<span class="cs-pastille" style="background:${versHex(L[0].m.c)}"></span><span>⚠ Des pièces mélangent tes textures modifiées avec leurs couleurs de sommets : le jeu multiplie les deux (orange × cyan = vert).</span> <b>${L.length}</b> <button type="button">Teinter leurs sommets comme la texture</button>`;
  d.querySelector('button').onclick = () => { let n = 0;
    for (const { o, p, cle, H } of piecesSommetsMelanges()) {
      E.teinteSom[cle] = Object.assign(teinteDe(versHex(hsv2rgb(H, 0.85, 1))), { nom: p.nom, acteur: o.acteur }); n++; }
    appliquerTeintes(); dessinerTeintes(); dessinerTextures(); if (NATIF.actif) optionsNatif();
    majRapport(n ? 'Sommets teintés comme leur texture. Réglables dans « Sommets et particules ».' : 'Rien à teinter.'); };
  return d;
}
// (28/11, muku : « noms clairs à la place des codes ») en mode simple, des mots au lieu des noms de fichiers du jeu ; le nom
// technique reste en mode Avancé et dans l'infobulle
function nomTextureSimple(x) {
  if (x.obj && x.obj.role === 'icone') return 'Icône';
  const s = String(x.nom || '').toLowerCase().replace(String(x.obj && x.obj.nom || '').toLowerCase(), '');
  if (/line$/.test(s)) return 'Contours';
  if (/spm$/.test(s)) return 'Métal';
  if (/msk$|mask$/.test(s)) return 'Masque';
  if (/sp$|spc$/.test(s)) return 'Reflets';
  if (/bc$/.test(s)) return 'Ombres';
  if (/nrm$|nm$|norm/.test(s)) return 'Relief';
  return 'Couleurs';
}
function dessinerTextures() {
  const g = $('textures'); g.innerHTML = '';
  const vus_ = {}, compte_ = {}; for (const c of texturesVisibles()) { const x = E.textures[c]; if (x) { const k = nomTextureSimple(x); compte_[k] = (compte_[k] || 0) + 1; } }
  { const cs = conseilSommets(); if (cs) g.appendChild(cs); }   // (26/11) avant les vignettes
  for (const cle of texturesVisibles()) {
    const x = E.textures[cle]; if (!x) continue;
    const d = document.createElement('div'); d.className = 'tex' + (E.selTex.has(cle) ? ' sel' : '') + (x.modif ? ' modif' : '') + (!x.cur || x.info.donnees ? ' donnees' : '');
    const cv = document.createElement('canvas'); cv.width = 64; cv.height = 64;
    if (x.cur) cv.getContext('2d').drawImage(x.cur, 0, 0, 64, 64);
    const n = document.createElement('div'); n.className = 'nom';
    const ns_ = nomTextureSimple(x); vus_[ns_] = (vus_[ns_] || 0) + 1;
    n.innerHTML = `<span class="nom-simple">${echapper(compte_[ns_] > 1 ? ns_ + ' ' + vus_[ns_] : ns_)}</span><span class="nom-av">${echapper(x.nom.replace(x.obj.nom + '_', '#'))}</span>`;
    d.title = `${x.nom}${x.info.w ? ` (${x.info.w}×${x.info.h})` : ''}${x.info.donnees ? ' : carte de données, non modifiable' : !x.cur ? ' : format non lu' : ''}`;
    // (15/11/2026) texture d'une version de l'objet que le jeu ne montre pas dans cette technique
    if (texturePasMontree(cle)) { d.classList.add('cachee');
      d.title += '\nVersion de l’objet que le jeu ne montre PAS dans cette technique : tes changements ici ne se verront pas.'
        + '\nClic droit → « Copier cette image sur … » pour les mettre sur la version montrée.'; }
    // (22/11) texture empruntée à un autre objet : visible dans l'aperçu, mais le jeu ne la recolore pas dans la copie
    if (x.info.source && !x.obj.modeleActeur) { d.classList.add('cachee');
      d.title += `\nPrise dans un autre objet (${x.info.source.split('/').pop().split('.')[0]}) : le jeu ne la recolore pas dans ta copie (ignorée à la création).`; }
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
function apresRetouche() { if (window.__bqDessin) return; quitterAvant(); E.rev = (E.rev || 0) + 1; teintesPieces(); dessinerPieces(); dessinerTextures(); dessinerZone(); texturesNatif(); majCompteurs();
  if (E.onglet === 'objets' && window.ojIcone) ojIcone();
  if (E.onglet === 'personnages' && typeof cpPeauPlusTard === 'function') cpPeauPlusTard(); }   // (26/11) peau du corps : suit le visage
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
  // (27/11, essai profond EN) mot traduit à part (avant : « 3 changés » restait en français)
  const T = s => (window.I18N ? I18N.trad(s) : s), n = (x, mot) => x ? `${x} ${T(mot + (x > 1 ? 's' : ''))}` : '';
  const t = !!E.tech;                              // (23/11) rien d'ouvert : compteurs vides
  if ($('cpt-tex')) $('cpt-tex').textContent = t ? n(Object.values(E.textures || {}).filter(x => x.modif).length, 'changée') : '';
  if ($('cpt-mat')) $('cpt-mat').textContent = t ? n(Object.keys(E.coulMat || {}).length, 'changé') : '';
  if ($('cpt-teintes')) $('cpt-teintes').textContent = t ? n(Object.keys(E.teinteSom || {}).length + Object.keys(E.teintePtl || {}).length, 'changé') : '';
  if ($('cpt-lum')) $('cpt-lum').textContent = t ? n(Object.keys(E.lumK || {}).length, 'changée') : '';
  const i = $('info-sel'); if (i) i.innerHTML = !E.tech ? '' : E.selPieces.size
    ? `<b>${E.selPieces.size} ${T(E.selPieces.size > 1 ? 'pièces sélectionnées' : 'pièce sélectionnée')}</b> : ${T('les listes ne montrent que leurs couleurs (Ctrl + clic pour en ajouter).')}`
    : 'Clique une pièce à gauche (ou un nom ci-dessous) pour ne voir que ses couleurs.';
}
function dessinerMateriaux() {
  const b = $('materiaux'); if (!b) return; b.innerHTML = '';
  if (!E.tech || E.tech.perso) { b.innerHTML = '<p class="aide">Seulement pour les techniques.</p>'; return; }
  const lignes = [];
  for (const o of E.objets) { if (o.erreur || o.modeleActeur || o.aura_balle) continue;   // (23/11) effets communs (ega…) aussi
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
// (23/11) + S (saturation de VRFW, multiplicateur) : une couleur pâle choisie pâlit aussi les sommets colorés (blanc -> S = 0) ;
// avant, choisir du blanc ne changeait rien aux sommets colorés (teinte seule)
// (23/11, « je veux tout modifier ») + V : une couleur sombre choisie assombrit aussi (luminosité × v de la couleur)
function teinteDe(hex) { const [h, s, v] = rgb2hsv(...hex2rgb(hex)); return { hex, H: Math.round(h * 10) / 10, C: Math.round(s * 1000) / 1000, S: Math.round(Math.min(1, s / 0.85) * 1000) / 1000, V: Math.round(v * 1000) / 1000 }; }
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
    for (const p of o.pieces || []) if (p.vue) { const t = (!E.avant && E.teinteSom[o.nom + '/' + p.index]) || null, tt = t ? tsc(t) : null;
      const avant = p.vue.teinteSom; if (JSON.stringify(avant || null) !== JSON.stringify(tt)) E.vue.teinterSommets(p.vue, tt); }
    const tp = (!E.avant && E.teintePtl[o.nom]) || null;
    for (const v of o.emetteursVue || []) v.teintePtl = tp ? tsc(tp) : null; }
}
// (23/11, muku : « je veux tout modifier », choix « intensité seulement ») LUMIÈRES DE L'EFFET (CCustomPointLight : elles
// éclairent les joueurs et le stade). Leur couleur vient de l'échelle animée d'un os de l'objet ; VRFW n'a pas de réglage :
// l'Atelier change l'animation lui-même (moteur/lumieres_effet.py). Une intensité par objet : 0 = éteinte, 100 % = comme le jeu.
function objetsAvecLumieres() {
  return (E.objets || []).filter(o => !o.erreur && !o.modeleActeur && !o.commun && o.lumieres && (o.lumieres.lumieres || []).length);
}
function appliquerLumieres() { if (E.vue) E.vue.lumK = E.avant ? {} : Object.assign({}, E.lumK || {}); }
function dessinerLumieres() {
  const b = $('lumieres-effet'); if (!b) return; b.innerHTML = '';
  if (!E.tech || E.tech.perso) { b.innerHTML = '<p class="aide">Seulement pour les techniques.</p>'; return; }
  const L = objetsAvecLumieres();
  if (!L.length) { b.innerHTML = '<p class="aide">Aucune lumière dans cet effet.</p>'; return; }
  for (const o of L) {
    const k = (E.lumK || {})[o.acteur], v = Math.round((k === undefined ? 1 : k) * 100), n = o.lumieres.lumieres.length;
    const d = document.createElement('div'); d.className = 'lum-ligne';
    d.innerHTML = `<span class="lum-nom" title="Objet ${echapper(o.acteur)}">${echapper(o.acteur)} : ${n} lumière${n > 1 ? 's' : ''}</span>
      <input type="range" min="0" max="200" step="5" value="${v}"><b class="lum-v">${v} %</b><button class="lum-raz" title="Comme le jeu (100 %)">↺</button>`;
    const r = d.querySelector('input'), t = d.querySelector('.lum-v');
    const regler = x => { if (x === 100) delete E.lumK[o.acteur]; else E.lumK[o.acteur] = x / 100; t.textContent = x + ' %'; appliquerLumieres(); majCompteurs(); };
    r.oninput = () => regler(+r.value);
    d.querySelector('.lum-raz').onclick = () => { r.value = 100; regler(100); };
    b.appendChild(d); }
}
function dessinerTeintes() {
  const b = $('teintes'); if (!b) return; b.innerHTML = '';
  if (!E.tech || E.tech.perso) { b.innerHTML = '<p class="aide">Seulement pour les techniques.</p>'; return; }
  const S = filtreSel();
  // particules : une couleur par objet
  let titreP = false;
  for (const o of E.objets) { if (o.erreur || o.modeleActeur || o.aura_balle) continue;   // (23/11) effets communs (ega…) aussi
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
  for (const o of E.objets) { if (o.erreur || o.modeleActeur || o.aura_balle) continue;   // (23/11) effets communs (ega…) aussi
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
  E.avant = oui === undefined ? !E.avant : !!oui; majBoutonAvant(); majAurasVue();
  for (const x of Object.values(E.textures)) x.donneesCur = null;
  teintesPieces(); appliquerTeintes(); appliquerLumieres(); if (NATIF.actif) { texturesNatif(); optionsNatif(); }
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
  for (const o of E.objets) { if (o.erreur || o.modeleActeur || o.aura_balle) continue;   // (23/11) effets communs (ega…) aussi
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
    if (op.cibles.som) for (const o of E.objets) { if (o.erreur || o.modeleActeur || o.aura_balle) continue;   // (23/11) effets communs (ega…) aussi
      for (const p of o.pieces || []) { if (!p.vue || !p.vue.col0) continue; const cle = o.nom + '/' + p.index, t = E.teinteSom[cle];
        let h; if (t) h = t.H; else { const m = moyenneSommets(p.vue.col0); if (m.colores < 0.05) continue; const [hh, ss] = rgb2hsv(...m.c); if (ss < 0.08) continue; h = hh; }
        if (!(poidsTeinte(h, 1, op) > 0.5)) continue;
        const H = ((op.H1 + (h - op.h0)) % 360 + 360) % 360;
        // (23/11, retour d'un joueur : tigre blanc à l'aperçu, jaunâtre en lecture) la saturation suit aussi (op.k), comme les textures :
        // avant, seule la teinte changeait et « jaune -> blanc » laissait les sommets jaunes (le lecteur et le jeu les dessinent)
        const Sk = Math.round(Math.min(4, (t && t.S !== undefined ? t.S : 1) * op.k) * 1000) / 1000;
        E.teinteSom[cle] = { hex: versHex(hsv2rgb(H, Math.min(1, 0.85 * Sk), Math.min(1, t && t.V !== undefined ? t.V : 1))), H: Math.round(H * 10) / 10, C: t ? t.C : 0, S: Sk, V: t && t.V !== undefined ? t.V : 1, nom: p.nom, acteur: o.acteur }; n.som++; } }
    if (op.cibles.ptl) for (const o of E.objets) { if (o.erreur || o.modeleActeur || o.aura_balle) continue;   // (23/11) effets communs (ega…) aussi
      const t = E.teintePtl[o.nom]; let h;
      if (t) h = t.H; else { const m = couleurMoyenneSaturee(couleursParticules(o)); if (!m) continue; h = rgb2hsv(...m.c)[0]; }
      if (!(poidsTeinte(h, 1, op) > 0.5)) continue;
      const H = ((op.H1 + (h - op.h0)) % 360 + 360) % 360;
      const Sk = Math.round(Math.min(4, (t && t.S !== undefined ? t.S : 1) * op.k) * 1000) / 1000;      // (23/11) saturation aussi
      E.teintePtl[o.nom] = { hex: versHex(hsv2rgb(H, Math.min(1, 0.85 * Sk), Math.min(1, t && t.V !== undefined ? t.V : 1))), H: Math.round(H * 10) / 10, C: t ? t.C : 0, S: Sk, V: t && t.V !== undefined ? t.V : 1 }; n.ptl++; }
  }
  return n;
}
function apresTout() { apresRetouche(); appliquerTeintes(); appliquerLumieres(); dessinerMateriaux(); dessinerTeintes(); dessinerLumieres(); dessinerRecette(); paletteTech(); majCompteurs(); }
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
    for (const o of E.objets) { if (o.erreur || o.modeleActeur || o.aura_balle) continue;   // (23/11) effets communs (ega…) aussi
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
    b.title = `${hex} · ${Math.round(C.w / tot * 100)} % · ${[...C.src].map(s => (window.I18N ? I18N.trad(s) : s)).join(', ')}\n(clic : remplacer cette couleur)`;
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
  return JSON.stringify([E.rev || 0, E.coulMat, E.teinteSom, E.teintePtl, E.lumK || {}, E.recette, champsProjet()]);
}
async function sauverProjet() {
  // (15/11/2026) jamais pendant le chargement d'une technique : l'état à moitié chargé écrasait le projet (avant la question « Reprendre »)
  if (!E.tech || E.reprise || E.chargement || NATIF.sauveProjet) return;
  // (15/11/2026) projet repris sans image de l'aperçu : une sauvegarde de plus pour la faire, dès que l'animation est chargée
  const sig = signatureProjet(); if (sig === E.sigProjet && !(E.vignetteManque && E.lecteur)) return;
  const tex = {}; for (const [k, x] of Object.entries(E.textures)) if (x.modif && x.cur && x.cur.toDataURL && !k.startsWith('mm/')) tex[k] = x.cur.toDataURL('image/png');
  const { c, auras } = champsProjet();
  if (!E.vignette || !E.vignetteT || performance.now() - E.vignetteT > 20000) { NATIF.sauveProjet = true;
    try { const v = await faireVignette(); if (v) { E.vignette = v; E.vignetteT = performance.now(); } } finally { NATIF.sauveProjet = false; } }
  const etat = { version: 1, code: E.tech.code, onglet: E.tech.onglet, nom: E.tech.nom, date: new Date().toISOString(), textures: tex, apercu: couleursPrincipales(4), vignette: E.vignette || null,
    coulMat: E.coulMat, teinteSom: E.teinteSom, teintePtl: E.teintePtl, lumK: E.lumK || {}, recette: E.recette, champs: c, auras,
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
    nS = Object.keys(e.teinteSom || {}).length + Object.keys(e.teintePtl || {}).length + Object.keys(e.lumK || {}).length, nR = (e.recette || []).length;
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
  E.coulMat = e.coulMat || {}; E.teinteSom = e.teinteSom || {}; E.teintePtl = e.teintePtl || {}; E.lumK = e.lumK || {}; E.recette = e.recette || []; E.pileRc = [];
  appliquerLumieres(); dessinerLumieres();
  E.vignette = e.vignette || null; E.vignetteT = e.vignette ? performance.now() : 0; E.vignetteManque = !e.vignette;
  for (const [id, v] of Object.entries(e.champs || {})) { const el = $(id); if (!el) continue; if (el.type === 'checkbox') el.checked = v; else el.value = v; }
  for (const [n, [oui, hex]] of Object.entries(e.auras || {})) { const cb = document.querySelector(`[data-aura="${CSS.escape(n)}"]`), c = document.querySelector(`[data-aura-c="${CSS.escape(n)}"]`);
    if (cb) cb.checked = oui; if (c) c.value = hex; }
  majAurasVue();
  if ($('lueurs-h')) { $('lueurs-h').dispatchEvent(new Event('input')); $('lueurs-on').dispatchEvent(new Event('change')); }
  if ($('mode')) $('mode').dispatchEvent(new Event('change'));
  apresTout(); majRapport('Projet repris : tu continues là où tu t\'étais arrêté.');
  if (window.zonesPreparer) try { zonesPreparer(); } catch (e) { console.error('zones', e); }
  if (e.calques && window.atelierRestaurer) try { await atelierRestaurer(e.calques); } catch (er) { console.error('calques', er); }
  // (28/11, « Modifier » d'une copie d'Ogres : le champ Nom montrait « Ogres (copie) ») projet relié à une création : SON nom
  // dans le champ du nom de l'onglet (les noms des copies ne sont pas dans les champs gardés), et objets : ses réglages
  if (E.cree) { const c = (HUB.creations || []).find(x => x.mod === E.cree.mod && String(x.code) === String(E.cree.code));
    const id = c && champNomCreation(c); if (id && $(id) && c.nom) $(id).value = c.nom;
    if (E.onglet === 'objets' && window.ojPreparer && E.cree.mod === 'MesObjets') try { ojPreparer(); } catch (er) { console.error('objet', er); } }
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
  const V = E.vue; if (!V || !E.tech || E.avant || E.isole || !V.cv || !V.cv.width) return null;   // (24/11) pas d'image « objet seul »
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
  // (26/11, demande de muku : « le cosmétique, ce sera l'étape en attente de stats mais pour les objets ; à la fin tout va dans
  // Terminées ») objets, tenues et maillots qui attendent leur étape « Cosmétique » (prix, icône…), puis Terminées
  const estCosm = c => ['MesObjets', 'MesTenues', 'MesMaillots'].includes(c.mod) && !!c.attenteCosm;
  const nAttente = HUB.creations.filter(c => c.attente).length, nCosm = HUB.creations.filter(c => !c.attente && estCosm(c)).length,
    nFinies = HUB.creations.length - nAttente - nCosm;    // (22/11)
  const nProjets = HUB.projets.filter(p => !projetLieExistant(p)).length;   // (22/11) sans les projets des créations
  $('hub-stats').innerHTML = [[nProjets, 'à continuer'], [nAttente, 'en attente de stats'], [nCosm, 'cosmétique'], [nFinies, 'terminées'], [PREREG.length, 'préréglages']]
    .map(([n, t]) => `<div class="hub-stat"><b>${n}</b><span>${t}</span></div>`).join('');
  $('hub-n-projets').textContent = nProjets; $('hub-n-creations').textContent = nFinies; $('hub-n-prereglages').textContent = PREREG.length;
  // à continuer
  const g = $('hub-projets'); g.innerHTML = '';
  const pl = HUB.projets.filter(p => !projetLieExistant(p) && ok(p.titre, p.base, p.code) && (!HUB.filtre || p.onglet === HUB.filtre));
  if (!pl.length) g.innerHTML = `<div class="hub-vide"><b>${HUB.projets.length ? 'Aucun projet ne correspond' : 'Rien en cours'}</b>${HUB.projets.length ? 'Essaie un autre mot.' : 'Ouvre une technique et change ses couleurs : ton travail apparaîtra ici tout seul.'}</div>`;
  for (const p of pl) {
    const tags = [[p.textures, 'texture'], [p.materiaux, 'matériau'], [p.teintes, 'teinte'], [p.remplacements, 'remplacement']].filter(x => x[0])
      .map(([n, m]) => `<span>${n} ${m}${n > 1 ? (m === 'matériau' ? 'x' : 's') : ''}</span>`).join('');
    const d = carte({ onglet: p.onglet, vignette: p.vignette, estTexture: p.vignetteTexture, badge: 'En cours', badgeCl: 'encours', titre: tradNom(p.titre), couleurs: p.couleurs, lecture: true,
      sousImg: `${genre(p.onglet)} · d'après ${echapper(tradNom(p.base))}`, sous: `Modifié le ${dateCourte(p.date)}`, tags: tags || '<span>rien de changé</span>',
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
  const lc = $('hub-cosmetique'); lc.innerHTML = '';       // (26/11) cosmétique
  const cr = HUB.creations.filter(c => ok(c.nom, c.base, c.code, c.nom_base) && (!HUB.filtre || c.onglet === HUB.filtre));
  $('jm-s-cosmetique').style.display = lc.style.display = cr.some(c => !c.attente && estCosm(c)) ? '' : 'none';
  { const autres = HUB.creations.some(c => !c.attente && !estCosm(c));    // (26/11) cosmétiques à part : pas comptées ici
    if (!cr.some(c => !c.attente && !estCosm(c))) l.innerHTML = `<div class="hub-vide"><b>${autres ? 'Aucune création ne correspond' : 'Aucun mod créé pour l’instant'}</b>${autres ? 'Essaie un autre mot.' : 'Quand une technique te plaît : « Créer le mod » dans le panneau de droite.'}</div>`; }
  for (const c of cr) {
    const proj = projetDe(c);
    // (22/11) joueur sans projet à lui : son portrait recoloré (celui des cartes du jeu)
    const vign = c.vignette || (proj && !proj.vignetteTexture ? proj.vignette : null) || (proj && proj.vignette)
      || (c.mod === 'MesPersonnages' && c.code ? '/api/portrait?code=' + encodeURIComponent(c.code) : null);
    const st = c.jeuSeul ? ['Dans le jeu', 'oui'] : c.installe ? ['Installé', 'oui'] : ['Pas installé', 'non'];
    const d = carte({ onglet: c.onglet, vignette: vign, estTexture: !c.vignette && proj && proj.vignetteTexture, badge: st[0], badgeCl: st[1], titre: c.nom, couleurs: proj && proj.couleurs, lecture: true,
      sousImg: `${genre(c.genre)} · copie de ${echapper(tradNom(c.nom_base || c.base))}`,
      sous: `<span class="avance"><span>Code</span> ${echapper(c.code)} · </span>${dateCourte(c.date)}${c.jeuSeul ? '<br>Plus dans la sortie de l’Atelier, mais toujours dans le jeu.' : ''}`,
      boutons: (c.attente ? '<button class="primaire" data-a="stats" title="Puissance, PT, élément… (ou garder ceux de l’original)">Régler les stats</button>' : '')
        + (estCosm(c) ? '<button class="primaire" data-a="cosm" title="Prix en boutique, icône… (ou garder ceux de la création)">Régler la cosmétique</button>' : '')
        + `<button${c.attente || estCosm(c) ? '' : ' class="primaire"'} data-a="modifier" title="${proj ? 'Reprendre le projet qui a servi à la créer' : 'Projet d’origine introuvable : rouvre la technique de départ'}">Modifier</button>`
        + (!c.attente && aDesStats(c) ? '<button data-a="stats" title="Changer ses valeurs (puissance, PT, élément…)">Stats</button>' : '')
        + (c.mod === 'MesPersonnages' && c.cle ? `<button data-a="coups" title="Choisir ses techniques et son esprit guerrier">Techniques${c.nb_coups ? ' (' + c.nb_coups + ')' : ''}</button>` : '')
        + (c.mod === 'MesEsprits' && (c.genre === 'esprit' || c.genre === 'totem') ? `<button data-a="liee" title="${c.liee ? 'Technique liée : ' + echapper(c.liee) : 'Choisir la technique de cet esprit guerrier'}">Technique liée${c.liee ? ' ✓' : ''}</button>` : '')
        // (22/11, demande de muku) « Installer » seulement dans Terminées (pas en attente de stats) ; « Supprimer » dans Terminées
        + (['MesObjets', 'MesTenues', 'MesMaillots'].includes(c.mod) && !estCosm(c) ? '<button data-a="cosm" title="Prix en boutique, icône…">Cosmétique</button>' : '')
        + (c.installe || c.attente || estCosm(c) ? '' : '<button data-a="installer" title="Copier dans le mod du jeu (sauvegarde avant ; ce qui y est déjà reste)">Installer</button>')
        + (c.attente || estCosm(c) ? '' : '<button data-a="supprimer" class="supprimer" title="Retirer cette création (ses fichiers sont rangés à part, récupérables)">Supprimer</button>') });
    const bc = d.querySelector('[data-a="coups"]'); if (bc) bc.onclick = () => ouvrirStats(c);     // (24/11) un seul écran : stats + techniques
    const bs = d.querySelector('[data-a="stats"]'); if (bs) bs.onclick = () => ouvrirStats(c);
    const bk = d.querySelector('[data-a="cosm"]'); if (bk) bk.onclick = () => ouvrirCosmetique(c);     // (26/11)
    const bx = d.querySelector('[data-a="supprimer"]'); if (bx) bx.onclick = () => supprimerCreation(c);
    const bl = d.querySelector('[data-a="liee"]'); if (bl) bl.onclick = () => ouvrirTechniqueLiee(c);
    const ouvrirC = c.mod === 'MesMaillots' && c.maillot ? async () => { window.changerOnglet('maillots'); await mmOuvrir(c.maillot); }   // (15/11) un de mes maillots
      : () => modifierCreation(c);   // (22/11) rouvre LA création (voir modifierCreation)
    d.querySelector('.hub-image').onclick = ouvrirC; d.querySelector('[data-a="modifier"]').onclick = ouvrirC;
    const bi = d.querySelector('[data-a="installer"]');
    if (bi) bi.onclick = async () => {
      await installer(c.mod);              // (21/11) créations du jeu qui seraient retirées : demandé par installer()
      $('hub-etat').textContent = $('rapport').textContent.split('\n')[0]; chargerHub(); };
    (c.attente ? la : estCosm(c) ? lc : l).appendChild(d); }
  // préréglages
  const pr = $('hub-prereglages'); pr.innerHTML = '';
  if (!PREREG.length) pr.innerHTML = '<div class="hub-vide"><b>Aucun préréglage</b>Fais un remplacement de couleur dans une technique, puis « Garder ».</div>';
  for (const p of PREREG.filter(p => ok(p.nom))) { const r = p.recette || [], s = document.createElement('span'); s.className = 'hub-puce';
    s.innerHTML = r.slice(0, 3).map(x => `<i style="background:${echapper(x.de)}"></i>→<i style="background:${echapper(x.vers)}"></i>`).join('<span style="width:6px"></span>')
      + ` <b>${echapper(p.nom)}</b> <small>· ${r.length} remplacement${r.length > 1 ? 's' : ''}</small>`;
    pr.appendChild(s); }
}
// (27/11) nom d'origine (« Tenue · gris et bleu 2 », « Armure · Ogre ») placé DANS une phrase : traduit avant, sinon il reste en français
// (27/11, essai profond EN / ES) nom par couleurs gardé en français dans la création (« gris et bleu 2 ») : mots traduits
// comme moteur/jeu.py COULEURS_MOTS (le catalogue, lui, est déjà fait dans la langue)
const COUL_MOTS = { en: { noir: 'black', blanc: 'white', gris: 'grey', rouge: 'red', orange: 'orange', jaune: 'yellow', vert: 'green', turquoise: 'turquoise', bleu: 'blue', violet: 'purple', rose: 'pink', et: 'and' },
  es: { noir: 'negro', blanc: 'blanco', gris: 'gris', rouge: 'rojo', orange: 'naranja', jaune: 'amarillo', vert: 'verde', turquoise: 'turquesa', bleu: 'azul', violet: 'morado', rose: 'rosa', et: 'y' } };
const tradCouleurs = x => { const M = COUL_MOTS[document.documentElement.lang]; if (!M) return x;
  const m = /^([a-z]+(?: [a-z]+)*)( \d+)?$/.exec(x); if (!m || !m[1].split(' ').every(w => M[w])) return x;
  return m[1].split(' ').map(w => M[w]).join(' ') + (m[2] || ''); };
const tradNom = n => (window.I18N && n ? String(n).split(' · ').map(x => { const t = I18N.trad(x); return t === x ? tradCouleurs(x) : t; }).join(' · ') : n);
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
    // (22/11, LU dans nie.exe) nom avec balise (« ball_aura_out15_<BALL_AURA> », 405 cinématiques de techniques) : la commande
    // d'aura remplace BALL_AURA (crc 0x72a1ed8f) par la variante de l'aura du ballon que le MATCH a posée (fonction 0x140f57420,
    // service de mots 0x141605580 ; valeur posée par le code du ballon 0x1414b0ee1) -> pas de nom fixe : pas recolorable.
    // (Avant : le nom n'était pas échappé, « <BALL_AURA> » était pris pour une balise HTML et coupé à l'affichage.)
    const variable = /<[A-Z_0-9]+>/.test(a.aura);
    d.innerHTML = `<input type="checkbox" data-aura="${echapper(a.aura)}"${a.couleur && !variable ? ' checked' : ''}${variable ? ' disabled' : ''}><span class="n">${echapper(a.aura)}${a.origine && a.origine !== a.aura ? ' <small>(copie de ' + echapper(a.origine) + ')</small>' : ''}${variable ? ' <small>(choisie par le match : pas recolorable)</small>' : ''}</span><input type="color" value="${a.couleur || '#2a1f8c'}" data-aura-c="${echapper(a.aura)}"${variable ? ' disabled' : ''}>`;
    if (variable) d.title = 'Le jeu met ici l’aura du ballon du moment (sa variante change pendant le match) : aucun nom fixe à recolorer.';
    b.appendChild(d);
  }
  // (25/11) couleur choisie = vue dans l'aperçu (WebGL et lecteur du jeu) ; le bloc est gardé d'une technique à l'autre : un seul écouteur
  if (!b._ecoute) { b._ecoute = true; b.addEventListener('input', majAurasVue); b.addEventListener('change', majAurasVue); }
  majAurasVue();
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
    // (25/11, capture de Hibou : « [Errno 2] No such file or directory: ' ») dans une erreur, le NOM du fichier manquant reste
    // (sans le chemin, qui contient le nom de l'utilisateur) : sinon le message ne dit plus rien
    .replace(/^(Ça n’a pas marché|Pas mis dans le jeu) : .*$/, m => m.replace(/[A-Za-z]:\\[^\n'"]*/g, c => c.split(/\\+/).filter(Boolean).pop() || ''))
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
// (22/11, retour de muku : deux « What next » avec les suites d'un ESPRIT sous la création d'un nouveau joueur) deux appels
// en même temps ajoutaient chacun leur bloc (le retrait avant l'attente ne voyait pas l'autre), et le bloc restait en
// changeant d'élément : tous les blocs retirés, seul le dernier appel ajoute le sien, retiré à l'ouverture d'un élément
let SUITE_N = 0;
function retirerSuite() { document.querySelectorAll('#suite-creation').forEach(x => x.remove()); }
async function proposerSuite(mod, code) {
  const n = ++SUITE_N; retirerSuite();
  if (!code || !['MesPersonnages', 'MesEsprits'].includes(mod)) return;
  let L = []; try { L = (await api('/api/projets')).creations || []; } catch (e) { return; }
  if (n !== SUITE_N) return;
  retirerSuite();
  const c = L.find(x => x.mod === mod && String(x.code) === String(code)); if (!c) return;
  const d = document.createElement('div'); d.id = 'suite-creation'; d.className = 'ensuite';
  const ajout = (txt, f) => { const b = document.createElement('button'); b.textContent = txt; b.onclick = f; d.appendChild(b); };
  if (mod === 'MesPersonnages' && c.cle) ajout('Choisir ses techniques', () => ouvrirStats(c));
  if (mod === 'MesEsprits' && c.genre === 'esprit') { ajout('Choisir sa technique liée', () => ouvrirTechniqueLiee(c)); ajout('Lui faire une armure', () => window.changerOnglet('armures')); }
  if (mod === 'MesEsprits' && c.genre === 'totem') ajout('Choisir sa technique liée', () => ouvrirTechniqueLiee(c));   // (22/11) totems aussi
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
  objets: 'Choisis un objet en haut, donne-lui un nom, puis « Créer ». Le prix se règle ensuite dans Mes créations (Cosmétique).',
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
// (28/11) aussi les codes DANS un morceau (« Chaussures e000401_10 » -> « Chaussures »), les codes de mod (« Mod~nom ») et les
// morceaux répétés (« Tenue de Axel · InazumaFantasy · InazumaFantasy »)
function titreSimple(s) { const vus = new Set();
  return s.split('·').map(x => x.trim().replace(/\b[a-z][a-z_]{0,8}\d{4,}[a-z0-9_]*\b/gi, '').replace(/\S+~\S+/g, '').replace(/\s{2,}/g, ' ').trim())
    .filter(x => x && !/^(cinématique|cutscene)\b/i.test(x) && !vus.has(x) && vus.add(x)).join('  ·  '); }
// (28/11) bouton « Créer » fixe du bas RETIRÉ (muku : « il y a des Créer, ce serait mieux de supprimer celui en bas de page »)
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
    // (22/11) CACHÉ, pas retiré : d'autres blocs branchent encore $(idInst).onclick ; retiré = null -> erreur qui arrêtait le
    // bloc avant d'autres boutons (le « Créer » des totems ne faisait plus rien)
    if ($(idInst)) { $(idInst).hidden = true; $(idInst).style.display = 'none'; }
  }
});
async function exporter() {
  if (!E.tech) return majRapport('Ouvre d\'abord une technique.');
  const objets = {};
  // (23/11, « je veux tout modifier ») effets communs (ega…, traits de vitesse) exportés aussi : copie « egz… » chargée à la
  // place de l'original dans CETTE cinématique (moteur/export.py) ; les lueurs globales ne les touchent pas
  for (const o of E.objets) { if (o.erreur || o.aura_balle) continue;
    const imgs = {};
    for (const [cle, x] of Object.entries(E.textures)) if (x.obj === o && x.modif) imgs[x.nom] = x.cur.toDataURL('image/png');
    const lueurs = !o.modeleActeur && !o.commun && $('lueurs-on').checked ? { hue: +$('lueurs-h').value, saturation: 1.3, value: 1.0, garder_or: $('garder-or').checked } : null;
    const materiaux = {};                    // (14/11/2026) couleurs des matériaux -> VRFW [[recolor.tint]]
    if (!o.modeleActeur) for (const [k, c] of Object.entries(E.coulMat || {})) if (k.startsWith(o.nom + '/')) materiaux[c.nom] = c.rgb;
    const sommets = {};                      // (14/11/2026) teintes des sommets : {nom de pièce : [H, C]}
    if (!o.modeleActeur) for (const [k, t] of Object.entries(E.teinteSom || {})) if (k.startsWith(o.nom + '/')) sommets[t.nom] = tsc(t);
    const tp = !o.modeleActeur && (E.teintePtl || {})[o.nom], particules = tp ? tsc(tp) : null;
    const lumiere = !o.modeleActeur && !o.commun && (E.lumK || {})[o.acteur] !== undefined ? E.lumK[o.acteur] : null;   // (23/11) intensité des lumières
    if (Object.keys(imgs).length || lueurs || Object.keys(materiaux).length || Object.keys(sommets).length || particules || lumiere !== null)
      objets[o.acteur] = { textures: imgs, lueurs, materiaux, sommets, particules, lumiere };
  }
  const auras = {};
  document.querySelectorAll('[data-aura]').forEach(cb => { if (cb.checked) auras[cb.dataset.aura] = hex2rgb(document.querySelector(`[data-aura-c="${CSS.escape(cb.dataset.aura)}"]`).value); });
  // (25/11, demande de muku) APPARITION d'un esprit guerrier (« invoc_<copie> ») : les couleurs vont dans SA scène d'invocation
  // à part (serveur : couleurs_apparition), pas dans une technique ; son propre modèle n'est pas pris (couleurs de sa copie)
  if (E.tech.invocation_de) {
    for (const o of E.objets) if (o.modeleActeur) delete objets[o.acteur];
    if (!Object.keys(objets).length && !Object.keys(auras).length) return majRapport('Rien n\'est modifié : change d\'abord des couleurs.');
    majRapport('Enregistrement des couleurs de l’apparition…');
    try { const r = await api('/api/couleurs_apparition', { copie: E.tech.invocation_de, objets, auras });
      majRapport(r.ok ? 'Couleurs de l’apparition enregistrées (pas encore installées) : ' + r.dossier + '\n- ' + r.rapport.join('\n- ') : 'Erreur : ' + r.erreur);
      return r; } catch (e) { return majRapport('Erreur : ' + e.message); }
  }
  if (!Object.keys(objets).length && !Object.keys(auras).length) return majRapport('Rien n\'est modifié : change d\'abord des couleurs.');
  // (23/11, demande de muku) seulement le nom et la description ici : couleur du tir, traînée, prix et bannière se règlent
  // dans « En attente de stats / cosmétique » (gardés par le serveur quand la technique est refaite ; neuve : en vente à 18 jetons)
  const d = { code: E.tech.code, nom: $('f-nom').value.trim() || E.tech.nom + ' (couleurs)', description: $('f-desc').value.trim(),
    banniere: {}, objets, auras };
  if (E.banniereImage && E.banniereImage.projet === E.projet) d.banniere.image = E.banniereImage.image;   // (21/11) liée au projet
  majRapport('Création du mod…');
  d.cle = creeCode('MesTechniques');                 // (28/11) « Modifier » : LA création (même si le nom change)
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
  try { const r = await api('/api/exporter_personnage', { code: E.tech.code, cle: creeCode('MesEsprits'), textures, nom, description: $('p-desc').value.trim(),
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
  if ($('mm-icone-img')) { $('mm-icone-img').src = (m && m.icone) || ''; $('mm-embleme-img').src = (m && m.embleme) || ''; } MM.icone = MM.embleme = null; mmOublierDessins();
  $('mm-en-cours').textContent = m ? 'Maillot : ' + m.nom : 'Nouveau maillot' + (E.tech ? ' (coupe : ' + E.tech.nom + ')' : '');
}
function mmNouveau() { MM.id = null; MM.cote = '10'; MM.base = { '10': {}, '20': {} }; MM.edits = { '10': {}, '20': {} }; mmFormulaire(null); mmListe(); if (E.tech && E.tech.onglet === 'maillots') mmMajCotes(); }
async function mmOuvrir(m) {
  if (!m.code) return majRapport('Coupe introuvable pour ' + m.nom + ' : ' + m.base);
  MM.id = m.id; MM.cote = '10'; MM.edits = { '10': {}, '20': {} };
  const a = m.accessoires || {}, im = m.images || {};
  MM.base = { '10': { haut: im.haut_dom, short: im.short_dom, chaussures: a.chaussures_dom && a.chaussures_dom.png, gants: a.gants_dom && a.gants_dom.png },
              '20': { haut: im.haut_ext, short: im.short_ext, chaussures: a.chaussures_ext && a.chaussures_ext.png, gants: a.gants_ext && a.gants_ext.png } };
  await ouvrir(m.code);
  E.projet = ('cree_MesMaillots_' + m.id).replace(/[^\w.-]/g, '_'); E.repriseCle = null; E.cree = { mod: 'MesMaillots', code: m.id };   // (22/11) pas de nouveau projet
  await mmPoser(); mmFormulaire(m); mmListe(); mmMajCotes();
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
  mmCapturer(); mmDessinFini();
  const images = {}, accessoires = {};
  for (const [c, suf] of [['10', 'dom'], ['20', 'ext']]) { const ed = MM.edits[c] || {};
    if (ed.haut) images['haut_' + suf] = ed.haut.png; if (ed.short) images['short_' + suf] = ed.short.png;
    for (const r of ['chaussures', 'gants']) if (ed[r]) accessoires[r + '_' + suf] = ed[r]; }
  if (!MM.id && !images.haut_dom) { const r = mmRoles();
    if (MM.cote === '10' && r.haut) images.haut_dom = r.haut.x.cur.toDataURL('image/png');
    else return majRapport('Il faut au moins le haut domicile : repasse sur « Domicile » puis enregistre.'); }
  majRapport('Enregistrement du maillot…');
  const r = await api('/api/maillot', { action: 'enregistrer', id: MM.id, nom: $('mm-nom').value, prix: null, base,
    plis: $('mm-plis').value, numero: mmNumero(), images, accessoires, icone: MM.icone, embleme: MM.embleme, lettres_png: await mmLettresPng(mmNumero()) });
  if (!r.ok) return majRapport('Pas enregistré : ' + r.erreur);
  // ce qui vient d'être envoyé devient « enregistré » (plus renvoyé tant qu'on n'y touche pas)
  for (const c of ['10', '20']) { for (const [role, v] of Object.entries(MM.edits[c] || {})) MM.base[c][role] = v.png; MM.edits[c] = {}; }
  for (const v of Object.values(mmRoles())) v.x.mmCharge = v.x.moyenne.join();
  MM.id = r.id; MM.icone = MM.embleme = null; E.cree = { mod: 'MesMaillots', code: r.id };   // (22/11) projet lié au maillot
  await mmListe(); $('mm-en-cours').textContent = 'Maillot : ' + $('mm-nom').value;
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
  lr.onload = () => { MM[cle] = lr.result; $(img).src = lr.result; mmOublierDessins(cle); }; lr.readAsDataURL(f); }; }
// (24/11, muku : « sur l'atelier maillot on pouvait dessiner le logo en boutique ») ICÔNE DE LA BOUTIQUE et EMBLÈME DESSINABLES,
// comme l'onglet Icône du studio de l'Atelier Maillots : ✎ ouvre le mode dessin sur une image 256 × 256 (icône) ou 512 × 512
// (emblème) ; elle part de ton image, sinon de l'icône du maillot de base dans le jeu (/api/maillot_icone_base), sinon vide.
// Elle n'est dans E.textures que pendant le mode dessin (pas sur la 3D, pas dans les vignettes, pas au lecteur natif).
MM.tex = {};
function mmOublierDessins(cle) { for (const k of cle ? [cle] : ['icone', 'embleme']) { delete MM.tex[k]; delete E.textures['mm/' + k]; if (typeof A !== 'undefined' && A.docs) delete A.docs['mm/' + k]; } }
async function mmDessiner(cle) {
  if (!E.tech || E.tech.onglet !== 'maillots') return majRapport('Ouvre d’abord un maillot du jeu (il sert de coupe) ou un de tes maillots.');
  let x = MM.tex[cle];
  if (!x) { const taille = cle === 'icone' ? 256 : 512, cv = document.createElement('canvas'); cv.width = cv.height = taille; const g = cv.getContext('2d');
    const src = MM[cle] || $('mm-' + cle + '-img').getAttribute('src') || (cle === 'icone' && E.tech.cle_maillot ? '/api/maillot_icone_base?base=' + encodeURIComponent(E.tech.cle_maillot) : '');
    if (src) { try { g.drawImage(await chargerImage(src), 0, 0, taille, taille); } catch (e) { /* pas d'image : on part du vide */ } }
    const orig = g.getImageData(0, 0, taille, taille);
    x = MM.tex[cle] = { obj: { nom: 'mm' }, nom: cle === 'icone' ? 'Icône de la boutique' : 'Emblème d’équipe', info: { w: taille, h: taille }, orig, cur: cv, modif: false, moyenne: moyenne(orig) }; }
  E.textures['mm/' + cle] = x; atDessinOuvrir('mm/' + cle);
  majRapport(cle === 'icone' ? 'Icône de la boutique en mode dessin. Ferme le mode dessin, puis « Enregistrer sans construire » ou « Créer » pour la garder.'
    : 'Emblème d’équipe en mode dessin. Ferme le mode dessin, puis « Enregistrer sans construire » ou « Créer » pour le garder.');
}
function mmDessinFini() {      // fermeture du mode dessin (atelier.js) et enregistrement : le dessin devient l'image envoyée
  for (const [cle, x] of Object.entries(MM.tex)) { if (!document.body.classList.contains('dessin')) delete E.textures['mm/' + cle];
    if (!x.modif) continue; const u = x.cur.toDataURL('image/png'); $('mm-' + cle + '-img').src = u; if (u !== x.mmEnvoye) { MM[cle] = u; x.mmEnvoye = u; } }
}
window.addEventListener('load', () => { if (!$('mm-enregistrer')) return;
  $('mm-enregistrer').onclick = () => mmEnregistrer().catch(e => majRapport('Erreur : ' + e.message));
  $('mm-nouveau').onclick = mmNouveau; document.querySelectorAll('[data-mm-cote]').forEach(b => b.onclick = () => mmCote(b.dataset.mmCote).catch(e => majRapport('Erreur : ' + e.message))); $('mm-construire').onclick = () => mmConstruire().catch(e => majRapport('Erreur : ' + e.message));
  // (27/11, muku) icône et emblème : plus ici, dans Mes créations -> Cosmétique (écran de la boutique, ✎ Dessiner / Importer)
  if ($('mm-icone')) { mmFichier($('mm-icone'), 'icone', 'mm-icone-img'); mmFichier($('mm-embleme'), 'embleme', 'mm-embleme-img');
    $('mm-icone-dessin').onclick = () => mmDessiner('icone').catch(e => majRapport('Erreur : ' + e.message));
    $('mm-embleme-dessin').onclick = () => mmDessiner('embleme').catch(e => majRapport('Erreur : ' + e.message)); }
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
  if (CP_PEAU.auto) cpPeauAuto();
  const r = await api('/api/copie_personnage', { code: E.tech.code, cle: creeCode('MesPersonnages'), nom, description: $('cp-desc').value.trim(), textures, portrait: await photoIcone('visage'),
    // (26/11) automatique : la peau du visage recoloré ('' si le visage n'est pas recoloré) ; une couleur gardée à la main avant
    // (« Garder », champ) n'est pas remplacée par l'automatique (serveur : peau_main)
    peau: $('cp-peau') ? (CP_PEAU.auto && CP_PEAU.inchange ? '' : $('cp-peau').value) : undefined, peau_auto: CP_PEAU.auto,
    corps: $('cp-corps') && CP_CORPS.pret ? $('cp-corps').value : undefined });   // (27/11) morphologie ('' = l'original)
  majRapport(r.ok ? 'Copie créée (pas encore installée) : ' + r.dossier + '\n- ' + r.rapport.join('\n- ') + '\n« Installer dans le jeu », puis tirage Kizuna (ChronicleDeluxe).' : 'Erreur : ' + r.erreur);
  return r;                                   // (22/11) « Créer » crée seulement : on installe depuis la carte (Mes créations)
}
window.addEventListener('load', () => { if (!$('cp-exporter')) return;
  $('cp-exporter').onclick = () => cpExporter().catch(e => majRapport('Erreur : ' + e.message)); $('cp-installer').onclick = () => installer('MesPersonnages');
  if ($('cp-peau')) { $('cp-peau').oninput = () => { CP_PEAU.auto = false; cpPeauEtat(); };
    $('cp-peau-tete').onclick = () => { CP_PEAU.auto = true; cpPeauAuto(); };
    $('cp-peau-origine').onclick = () => { CP_PEAU.auto = false; if (CP_PEAU.origine) $('cp-peau').value = CP_PEAU.origine; cpPeauEtat(); }; } });
// (26/11, retour de jayden / WhiteRabbit : « la peau des bras et des jambes ne va pas avec la tête »). LU : la tête (Chr_ToonMetal)
// a sa peau peinte dans sa texture ; bras (_uniform/sk…), jambes et cou (c000N01_10) sont BLANCS et le shader Chr_EditToon les
// multiplie par u_skinColor = chara_model colonne 16 « skin_color » (le corps de l'original, même avec une tête recolorée).
// MESURÉ : cette couleur = la couleur dominante de l'atlas du visage (_10) -> par défaut, la peau du visage recoloré.
const CP_PEAU = { origine: null, auto: true, code: null, inchange: true };
function peauDeTete(o, c) {          // ImageData d'origine / recolorée -> '#RRGGBB' : pixels de la couleur dominante d'origine, lus dans la recolorée
  const d = o.data, e = (c || o).data, n = d.length / 4, pas = Math.max(1, Math.floor(n / 250000)), H = new Map();
  const cle = k => (d[k] >> 2) << 12 | (d[k + 1] >> 2) << 6 | (d[k + 2] >> 2);
  for (let i = 0; i < n; i += pas) { const k = i * 4; if (d[k + 3] < 200) continue; const q = cle(k); H.set(q, (H.get(q) || 0) + 1); }
  let m = -1, nb = 0; for (const [q, v] of H) if (v > nb) { nb = v; m = q; }
  if (m < 0) return null;
  const s = [0, 0, 0], s0 = [0, 0, 0]; let t = 0;
  for (let i = 0; i < n; i += pas) { const k = i * 4; if (d[k + 3] < 200 || cle(k) !== m) continue;
    for (let j = 0; j < 3; j++) { s[j] += e[k + j]; s0[j] += d[k + j]; } t++; }
  // change = la peau du visage a été recolorée (sinon : la peau de l'original reste la bonne, rien à écrire)
  return { couleur: '#' + s.map(v => Math.round(v / t).toString(16).padStart(2, '0')).join('').toUpperCase(),
           change: s.some((v, j) => Math.abs(v - s0[j]) / t > 1.5) };
}
function cpTextureVisage() {         // atlas du visage de la tête ouverte : <code>_10
  if (!E.tech || !E.objets || !E.objets[0]) return null;
  const L = Object.values(E.textures).filter(x => x.orig && x.obj && x.obj.nom === E.objets[0].nom);
  return L.find(x => x.nom === E.tech.code + '_10') || L.filter(x => /_10$/.test(x.nom)).sort((a, b) => b.orig.width * b.orig.height - a.orig.width * a.orig.height)[0] || null;
}
function cpPeauAuto() {
  const x = cpTextureVisage(); if (!x || !$('cp-peau')) return;
  const cur = x.modif && x.cur && x.cur.getContext ? x.cur.getContext('2d').getImageData(0, 0, x.orig.width, x.orig.height) : null;
  const p = peauDeTete(x.orig, cur);
  CP_PEAU.inchange = !p || !p.change;              // visage non recoloré : la peau de l'original (rien d'écrit dans le mod)
  const v = CP_PEAU.inchange ? (CP_PEAU.origine || (p && p.couleur)) : p.couleur; if (v) $('cp-peau').value = v;
  cpPeauEtat();
}
function cpPeauEtat() {
  const el = $('cp-peau-etat'); if (!el) return; const v = ($('cp-peau').value || '').toUpperCase();
  const o = CP_PEAU.origine || '—';
  el.textContent = CP_PEAU.auto ? `Automatique : comme la peau du visage (${v}). Original : ${o}.` : `Choisie à la main : ${v}. Original : ${o}.`;
}
async function cpPeauOuvrir(code) {
  CP_PEAU.auto = true; CP_PEAU.inchange = true; CP_PEAU.origine = null; CP_PEAU.code = code;
  try { const q = await api('/api/peau_perso?tete=' + encodeURIComponent(code)); if (CP_PEAU.code !== code) return; CP_PEAU.origine = q.ok ? q.origine : null; } catch (e) { /* serveur ancien */ }
  if (CP_PEAU.origine && $('cp-peau')) $('cp-peau').value = CP_PEAU.origine;
  cpPeauEtat();
}
// (27/11, muku : « ajouter une option pour choisir la morphologie quand on fait un joueur ») corps du nouveau joueur : un des
// corps communs du jeu (CHARA_BODY_INFO, moteur/copies_persos.morphologies), montré avec des joueurs qui l'ont ; « Modifier » le remet
const CP_CORPS = { jeton: 0, pret: false, origine: null };
async function cpCorpsOuvrir(code) {
  const sel = $('cp-corps'); if (!sel) return;
  const j = ++CP_CORPS.jeton; CP_CORPS.pret = false;
  const cree = creeCode('MesPersonnages') || '';
  let q = null;
  try { q = await api('/api/morphologie_perso?tete=' + encodeURIComponent(code) + '&cree=' + encodeURIComponent(cree)); } catch (e) { /* serveur ancien */ }
  if (j !== CP_CORPS.jeton) return;
  const T = s => (window.I18N ? I18N.trad(s) : s);
  const lib = b => T(b.libelle) + (b.exemples && b.exemples.length ? ' — ' + T('comme') + ' ' + b.exemples.join(', ') : '');
  const L = q && q.ok ? q.liste : [];
  CP_CORPS.origine = q && q.ok ? q.origine : null;
  const o = L.find(b => b.cle === CP_CORPS.origine);
  sel.innerHTML = `<option value="">${echapper(T("Comme l'original") + (o ? ' (' + T(o.libelle) + ')' : ''))}</option>`
    + L.map(b => `<option value="${b.cle}"${b.cle === CP_CORPS.origine ? ' disabled' : ''}>${echapper(lib(b))}</option>`).join('');
  sel.value = q && q.ok && q.copie && L.some(b => b.cle === q.copie) ? String(q.copie) : '';
  CP_CORPS.pret = !!(q && q.ok);
}
let cpPeauMinuteur = null;
function cpPeauPlusTard() { clearTimeout(cpPeauMinuteur); cpPeauMinuteur = setTimeout(() => { if (CP_PEAU.auto && E.tech && E.tech.onglet === 'personnages') cpPeauAuto(); }, 500); }
// ------------------------------------------------------------------ (15/11/2026) COPIE D'ARMURE (moteur/armures_copies.py)
async function caListe() {
  const sel = $('ca-esprit'); if (!sel) return;
  let r = { copies: [] }; try { r = await api('/api/copies_esprits'); } catch (e) { /* serveur absent */ }
  sel.innerHTML = r.copies.length ? r.copies.map(c => `<option value="${echapper(c.code)}">${echapper(c.nom)} (copie de ${echapper(tradNom(c.nom_base || c.base))})</option>`).join('')
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
  const dem = { code: E.tech.code, esprit: $('ca-esprit').value, nom: $('ca-nom').value.trim(), textures, cle: creeCode('MesEsprits') };
  let r = await api('/api/copie_armure', dem);
  // (28/11) une copie d'esprit n'a qu'UNE armure : en créer une 2e la remplaçait sans rien dire -> on demande
  if (!r.ok && r.deja) {
    if (!confirm(`Cette copie d'esprit a déjà une armure : « ${r.deja} ». La remplacer par celle-ci ?`)) return majRapport('Rien n’a changé : l’armure « ' + r.deja + ' » est gardée.');
    r = await api('/api/copie_armure', Object.assign(dem, { remplacer: true })); }
  majRapport(r.ok ? 'Armure créée (pas encore installée) : ' + r.dossier + '\n- ' + r.rapport.join('\n- ') + '\n« Installer dans le jeu » (mod MesEsprits).' : 'Erreur : ' + r.erreur);
  return r;                                   // (22/11) « Créer » crée seulement : on installe depuis la carte (Mes créations)
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
    // (27/11) gabarit (grand, petit…) et exemple dans des nœuds à part : le gabarit se traduit (EN / ES)
    const L = r.corps_tenue || [], nomCorps = c => c ? `<span class="cu-nom"><span>${echapper(c.gabarit || c.libelle)}</span>${c.exemple ? ' <span>(ex. ' + echapper(c.exemple) + ')</span>' : ''}</span>` : '';
    // (27/11, muku : « simple à comprendre ») seulement les corpulences possibles ; les autres en une ligne
    const non = L.filter(c => !c.propre && c.emprunt == null).length;
    $('cu-corps-non').textContent = non ? non + ' autres corpulences ne peuvent pas la mettre (squelette différent).' : '';
    $('cu-corps').innerHTML = L.filter(c => c.propre || c.emprunt != null).map(c => `<label class="${c.propre ? 'propre' : c.emprunt != null ? 'emprunt' : 'impossible'}" title="${c.nb} personnages">`
      + `<input type="checkbox" data-corps="${c.ligne}"${c.propre ? ' checked' : ''}${!c.propre && c.emprunt == null ? ' disabled' : ''}> ${nomCorps(c)}`
      + `<small>${c.propre ? '<span>sa version</span>' : c.emprunt != null ? '<span>à vérifier en jeu, prend :</span> ' + nomCorps(L.find(x => x.ligne === c.emprunt)) : '<span>pas de version (autre squelette)</span>'}</small></label>`).join('');
    // (27/11) choix automatiques montrés (règle « tout modifiable ») : chaussures du jeu pour ce vêtement, boutique
    if ($('cu-chaussures')) { $('cu-chaussures').options[0].textContent = r.chaussures ? 'Celles du jeu pour ce vêtement (' + r.chaussures + ')'
        : r.kit_jeu && r.kit_jeu.source ? 'Comme dans le jeu (pas de chaussures)' : 'Celles du jeu (aucune pour ce vêtement : crampons de Raimon)';
      E.cuJoueurs = []; cuJoueursPreparer().catch(() => {}); }
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
  const r = await api('/api/copie_tenue', { code: E.tech.code, cle: creeCode('MesPersonnages'), porteur: $('ct-porteur').value, nom: $('ct-nom').value.trim(), description: $('ct-desc').value.trim(), textures });
  majRapport(r.ok ? 'Copie créée (pas encore installée) : ' + r.dossier + '\n- ' + r.rapport.join('\n- ') + '\n« Installer dans le jeu », puis tirage Kizuna (ChronicleDeluxe).' : 'Erreur : ' + r.erreur);
  return r;                                   // (22/11) « Créer » crée seulement : on installe depuis la carte (Mes créations)
}
async function coExporter() {
  if (!E.tech || E.tech.genre !== 'Accessoire') return majRapport('Ouvre d’abord un accessoire (onglet Tenues, tri « Accessoire »).');
  const tete = ($('co-tete').value.split('·').pop() || '').trim(); if (!tete) return majRapport('Choisis le personnage qui portera l’objet.');
  const textures = texturesModifiees(); if (!Object.keys(textures).length) return majRapport('Rien n’est modifié : recolore d’abord l’objet.');
  majRapport('Création du nouveau joueur…');
  const r = await api('/api/copie_objet', { code: E.tech.code, cle: creeCode('MesPersonnages'), tete, nom: $('co-nom').value.trim(), description: $('co-desc').value.trim(), textures });
  majRapport(r.ok ? 'Copie créée (pas encore installée) : ' + r.dossier + '\n- ' + r.rapport.join('\n- ') + '\n« Installer dans le jeu », puis tirage Kizuna (ChronicleDeluxe).' : 'Erreur : ' + r.erreur);
  return r;                                   // (22/11) « Créer » crée seulement : on installe depuis la carte (Mes créations)
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
// (27/11) « Seulement ces joueurs » : noms du jeu (même liste que les conditions des synergies)
async function cuJoueursPreparer() {
  const lg = (window.I18N && I18N.langue) || 'fr';
  if (!OJ_SYN || OJ_SYN.lg !== lg) { const r = await api('/api/synergies_listes?langue=' + lg); OJ_SYN = { lg, effets: r.effets || [], joueurs: r.joueurs || [] }; }
  if (!$('cu-joueurs-liste').children.length) $('cu-joueurs-liste').innerHTML = OJ_SYN.joueurs.map(j => `<option value="${echapper(j.nom)} · ${echapper(j.code)}"></option>`).join('');
  cuJoueursDessiner();
}
function cuJoueursDessiner() {
  const l = E.cuJoueurs || (E.cuJoueurs = []);
  $('cu-joueurs-choisis').innerHTML = l.map((j, i) => `<span class="cu-joueur">${echapper(j.nom)} <button type="button" data-i="${i}" title="Retirer">✕</button></span>`).join('');
  $('cu-joueurs-choisis').querySelectorAll('button').forEach(b => b.onclick = () => { l.splice(+b.dataset.i, 1); cuJoueursDessiner(); });
}
function cuJoueurAjouter() {
  const v = $('cu-joueurs').value, code = (v.split('·').pop() || '').trim();
  const j = (OJ_SYN && OJ_SYN.joueurs || []).find(x => x.code === code) || (OJ_SYN && OJ_SYN.joueurs || []).find(x => x.nom.toLowerCase() === v.trim().toLowerCase());
  if (!j) return; const l = E.cuJoueurs || (E.cuJoueurs = []); if (!l.some(x => x.code === j.code)) l.push(j);
  $('cu-joueurs').value = ''; cuJoueursDessiner();
}
async function cuExporter() {
  if (!E.tech || E.tech.onglet !== 'tenues') return majRapport('Ouvre d’abord une tenue (onglet Tenues).');
  const textures = texturesModifiees(); if (!Object.keys(textures).length) return majRapport('Rien n’est modifié : recolore d’abord la tenue.');
  majRapport('Création de la tenue…');
  const corps = [...document.querySelectorAll('#cu-corps [data-corps]:checked')].map(c => +c.dataset.corps);
  if (!corps.length) return majRapport('Coche au moins une corpulence (« Qui peut la mettre ? »).');
  const r = await api('/api/copie_outfit', { code: E.tech.code, modele: E.cree && E.cree.mod === 'MesTenues' ? E.cree.code : undefined, nom: $('cu-nom').value.trim(), description: $('cu-desc').value.trim(), prix: null, textures, icone: null, corps,
    chaussures: $('cu-chaussures').value, rarete: +$('cu-rarete').value, max: +$('cu-max').value || 1, joueurs: (E.cuJoueurs || []).map(j => j.code) });
  // (27/11) icône faite tout de suite : le mannequin qui porte la tenue (comme les icônes du jeu), sauf si muku l'a dessinée
  if (r.ok && r.cle && !r.icone_perso) {
    try { const ic = await bqIconeTenueAuto(r.cle); const a = await api('/api/cosmetique', { mod: 'MesTenues', code: r.cle, icone: ic, icone_auto: true });
      r.rapport.push(...(a.rapport || [])); } catch (e) { r.rapport.push('icône automatique : ' + e.message + ' (la texture réduite reste)'); } }
  majRapport(r.ok ? 'Tenue créée (pas encore installée) : ' + r.dossier + '\n- ' + r.rapport.join('\n- ') + '\n« Installer dans le jeu » (mod MesTenues).' : 'Erreur : ' + r.erreur);
  return r;                                   // (22/11) « Créer » crée seulement : on installe depuis la carte (Mes créations)
}
window.addEventListener('load', () => { if (!$('cu-exporter')) return;
  $('cu-exporter').onclick = () => cuExporter().catch(e => majRapport('Erreur : ' + e.message)); $('cu-installer').onclick = () => installer('MesTenues');
  $('cu-joueurs').onchange = cuJoueurAjouter; $('cu-joueurs').onkeydown = ev => { if (ev.key === 'Enter') { ev.preventDefault(); cuJoueurAjouter(); } };
  $('corps-choix').onchange = () => changerCorpulence($('corps-choix').value).catch(e => majRapport('Erreur : ' + e.message));
  $('cu-icone').onchange = () => { const f = $('cu-icone').files[0]; if (!f) return; const lr = new FileReader(); lr.onload = () => { E.cuIcone = lr.result; $('cu-icone-img').src = lr.result; }; lr.readAsDataURL(f); }; });
// ------------------------------------------------------------------ (15/11/2026) OBJETS DU JEU (moteur/objets_jeu.py)
function ojTexture() { document.body.classList.toggle('objet-3d', E.onglet === 'objets' && E.objets.length > 1); const o = E.objets[0]; const t = o && o.textures && o.textures[0]; return t ? E.textures[o.nom + '/' + t.nom] : null; }
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
// (27/11) RÉGLAGES D'UN ÉQUIPEMENT (crampons, bracelets / gants, pendentifs, spéciaux) : les 7 bonus tels qu'en jeu (table construite
// par VRFW), réglables ; les POSTES ne se choisissent pas : le jeu les déduit des bonus (LU nie.exe 0x140e99e30, appelé par la Lua
// SetupItemPositionIcon) : pour chaque bonus > 0, dans cet ordre, il ajoute ses postes tant qu'il y a moins de 2 postes, puis les
// trie ATT, MIL, DÉF, GAR
const OJ_STATS = [['kick', 'Frappe'], ['control', 'Contrôle'], ['technique', 'Technique'], ['pressure', 'Pression'], ['physical', 'Physique'], ['intelligence', 'Intelligence'], ['agility', 'Agilité']];
const OJ_POSTES_ORDRE = [['kick', ['ATT']], ['technique', ['ATT', 'MIL']], ['intelligence', ['DÉF', 'MIL']], ['agility', ['GAR']], ['physical', ['GAR', 'DÉF']], ['pressure', ['GAR', 'DÉF']], ['control', ['ATT', 'MIL']]];
function ojPostes(st) { const l = [];
  for (const [k, ps] of OJ_POSTES_ORDRE) if ((+st[k] || 0) > 0) for (const p of ps) if (l.length < 2 && !l.includes(p)) l.push(p);
  return ['ATT', 'MIL', 'DÉF', 'GAR'].filter(p => l.includes(p)); }
// (27/11) RÉGLAGES D'UNE SYNERGIE (vraie nouvelle synergie : son code, ses effets, ses conditions ; moteur/synergies.py) :
// effets du jeu (30 blocs, textes du jeu), 3 au plus, lignes du panneau comme le jeu (2 principales + 1 secondaire) ; conditions =
// joueurs TITULAIRES (ou staff) nécessaires, tous obligatoires, 8 au plus (le panneau du jeu en montre 3)
let OJ_SYN = null;
async function ojReglagesSynergie(t, d) {
  const lg = ['en', 'es'].includes(window.ATELIER_LANGUE) ? window.ATELIER_LANGUE : 'fr';
  if (!OJ_SYN || OJ_SYN.lg !== lg) { const r = await api('/api/synergies_listes?langue=' + lg); OJ_SYN = { lg, effets: r.effets || [], joueurs: r.joueurs || [] }; }
  const sy = t.synergie, noms = new Map(OJ_SYN.joueurs.map(j => [j.id, j])), lib = e => (e.textes[lg] || e.textes.fr).replace(/X/g, '…');
  const effets = sy.effets.map(x => x.slice()), conds = sy.conditions.slice();
  const commun = d.querySelector('.oj-commun');
  d.innerHTML = `<h3>Synergie ${sy.offensive ? 'offensive' : 'défensive'}</h3>
    <p class="aide">Une vraie nouvelle synergie (son propre code) : ses effets et les joueurs qu’il faut dans l’équipe. Offensive ou défensive : comme l’original. On en équipe une de chaque genre par composition d’équipe.</p>
    <b>Effets (3 au plus)</b><div class="oj-syn-effets"></div><button class="oj-syn-plus-effet">+ Effet</button>
    <b>Joueurs nécessaires (titulaires ou staff, tous obligatoires, 8 au plus)</b><div class="oj-syn-joueurs"></div>
    <input class="oj-syn-cherche" list="oj-syn-liste" placeholder="Ajouter un joueur : tape son nom"><datalist id="oj-syn-liste">${OJ_SYN.joueurs.map(j => `<option value="${echapper(j.nom + ' · ' + j.code)}">`).join('')}</datalist>
    <p class="oj-apercu oj-syn-etat"></p>`;
  if (commun) d.prepend(commun);
  const dessiner = () => {
    d.querySelector('.oj-syn-effets').innerHTML = effets.map((x, i) => `<div class="ligne oj-syn-effet">
      <select data-i="${i}" data-k="0">${OJ_SYN.effets.map(e => `<option value="${e.id}"${e.id === x[0] ? ' selected' : ''}>${echapper(lib(e))}</option>`).join('')}</select>
      <label>% <input type="number" min="1" max="100" data-i="${i}" data-k="1" value="${x[1]}"></label>
      <select data-i="${i}" data-k="2"><option value="1"${x[2] ? ' selected' : ''}>ligne principale</option><option value="0"${x[2] ? '' : ' selected'}>ligne secondaire</option></select>
      <button data-suppr="${i}" title="Retirer cet effet">✕</button></div>`).join('');
    d.querySelector('.oj-syn-joueurs').innerHTML = conds.map((c, i) => { const j = noms.get(c);
      return `<span class="oj-puce">${echapper(j ? j.nom + ' · ' + j.code : 'personnage ' + c)}<button data-jsuppr="${i}" title="Retirer">✕</button></span>`; }).join('') || '<i>aucun</i>';
    d.querySelectorAll('.oj-syn-effet [data-i]').forEach(el => el.onchange = el.oninput = () => { effets[+el.dataset.i][+el.dataset.k] = +el.value; etat(); });
    d.querySelectorAll('[data-suppr]').forEach(b => b.onclick = () => { effets.splice(+b.dataset.suppr, 1); dessiner(); });
    d.querySelectorAll('[data-jsuppr]').forEach(b => b.onclick = () => { conds.splice(+b.dataset.jsuppr, 1); dessiner(); });
    d.querySelector('.oj-syn-plus-effet').disabled = effets.length >= 3; etat(); };
  const etat = () => { const p = effets.filter(x => x[2]).length, sc = effets.length - p, m = [];
    if (!effets.length) m.push('il faut au moins un effet'); if (p > 2) m.push('2 lignes principales au plus'); if (sc > 1) m.push('1 ligne secondaire au plus');
    if (!conds.length) m.push('il faut au moins un joueur'); if (effets.some(x => x[1] > 10)) m.push('au-dessus de 10 % : jamais vu dans le jeu');
    d.querySelector('.oj-syn-etat').textContent = m.length ? '⚠ ' + m.join(' · ') : 'Active quand ' + (conds.length > 1 ? 'tous ces joueurs sont' : 'ce joueur est') + ' dans l’équipe (titulaires ou staff).'; };
  d.querySelector('.oj-syn-plus-effet').onclick = () => { if (effets.length < 3) { effets.push([OJ_SYN.effets[0].id, 5, effets.filter(x => x[2]).length < 2 ? 1 : 0]); dessiner(); } };
  const ch = d.querySelector('.oj-syn-cherche');
  ch.onchange = () => { const v = ch.value, j = OJ_SYN.joueurs.find(x => x.nom + ' · ' + x.code === v);
    if (j && !conds.includes(j.id) && conds.length < 8) { conds.push(j.id); ch.value = ''; dessiner(); } };
  d.__valeurs = () => ({ synergie: { effets: effets.map(x => [x[0], x[1], x[2] ? 1 : 0]), conditions: conds.slice() } });
  dessiner();
}
// (27/11, recherche de tous les types) réglages COMMUNS à toute copie : rareté (1-2 : au-dessus, icône blanche d'après VRFW) et
// quantité max dans le sac ; description cachée quand le jeu n'en montre pas pour ce genre (titres, emblèmes, synergies…) ;
// « Créer » refusé, avec la raison, pour ce qu'une copie ne ferait pas marcher (boîtes, plaques, formations, tenues -> onglet Tenues)
function ojCommun(t) {                        // (27/11, muku : « comme les techniques ») création : nom + description seulement
  const c = t.commun || {}, lab = $('oj-desc-copie').closest('label');
  if (lab) lab.hidden = c.description === false;
  $('oj-exporter').disabled = !!c.refus;
  // (27/11, parcours EN) morceaux dans des nœuds à part : chacun se traduit (avant : la raison restait en français)
  if (c.refus) $('oj-etat').innerHTML = '<span>Pas de copie possible pour cet objet :</span> <span>' + echapper(c.refus) + '</span>.';
}
function ojCommunChamps(t) {
  const c = t.commun || {};
  const d = document.createElement('div'); d.className = 'oj-commun';
  // (27/11, vu en jeu) choix seulement là où le jeu en a deux : titres (argenté / doré), consommables (fond normal / brillant)
  const R = { titre: ['Type de titre', 'Argenté', 'Doré'], fond: ['Fond de l’objet', 'Normal', 'Brillant (rare)'] }[c.choix_rarete];
  d.innerHTML = (R ? `<label>${R[0]} <select class="oj-rarete"><option value="1">${R[1]}</option><option value="2">${R[2]}</option></select></label>` : '') + `
    ${c.unique ? '<p class="aide">Une seule : comme dans le jeu, on ne peut l’acheter qu’une fois.</p>'
      : `<label>Quantité max dans le sac <input type="number" class="oj-max" min="1" max="999999" value="${c.max || 1}"></label>`}`;
  if (R) d.querySelector('.oj-rarete').value = String(Math.min(2, Math.max(1, c.rarete || 1)));
  return d;
}
function ojReglages(t) {                      // création : plus de réglages ici (ils sont dans Mes créations -> Cosmétique)
  const d = $('oj-reglages'); d.innerHTML = ''; d.__valeurs = null; ojCommun(t);
}
// (27/11) panneau des réglages d'une copie (étape Cosmétique de la boutique) : t = { commun, equipement, synergie }
function ojReglagesDans(t, d) {
  d.innerHTML = ''; d.__valeurs = null;
  d.appendChild(ojCommunChamps(t));
  if (t.synergie) return ojReglagesSynergie(t, d).catch(e => { d.textContent = 'Réglages de la synergie indisponibles : ' + e.message; });
  if (!t.equipement) return;
  const S = t.equipement.S || 70, st = t.equipement.stats || {}, commun = d.querySelector('.oj-commun');
  d.innerHTML = `<h3>Bonus de l’équipement</h3><p class="aide">Les bonus tels qu’ils sont en jeu pour l’original. Les postes (ATT, MIL, DÉF, GAR) ne se choisissent pas : le jeu les déduit des bonus.</p>
    <div class="oj-stats">${OJ_STATS.map(([k, n]) => `<label>${n} <input type="number" data-stat="${k}" min="${-S}" max="${S}" value="${+st[k] || 0}"></label>`).join('')}</div>
    <p class="oj-apercu"></p>`;
  if (commun) d.prepend(commun);
  const maj = () => { const v = {}; d.querySelectorAll('[data-stat]').forEach(i => { v[i.dataset.stat] = Math.max(-S, Math.min(S, Math.round(+i.value || 0))); });
    const T = x => window.trad ? window.trad(x) : x;     // (27/11, parcours EN) noms des stats traduits
    const txt = OJ_STATS.filter(([k]) => v[k]).map(([k, n]) => `${T(n)} ${v[k] > 0 ? '+' : ''}${v[k]}`).join(' · ') || T('aucun bonus'), ps = ojPostes(v);
    d.querySelector('.oj-apercu').textContent = `${T('En jeu :')} ${txt}${ps.length ? '  —  ' + T('postes :') + ' ' + ps.map(T).join(' ') : ''} (${T('maximum')} ${S})`; };
  d.querySelectorAll('[data-stat]').forEach(i => { i.oninput = maj; }); maj();
}
function ojValeursReglages(d0) {
  const d = d0 || $('oj-reglages'), r = d && d.querySelector('.oj-rarete'), m = d && d.querySelector('.oj-max');
  const commun = Object.assign({}, r ? { rarete: +r.value } : {}, m ? { max: Math.max(1, Math.min(999999, Math.round(+m.value || 1))) } : {});
  return Object.assign(commun, ojValeursPropres(d));
}
function ojValeursPropres(d) {
  const v = {}; if (d && d.__valeurs) return d.__valeurs();
  if (!d || !d.querySelector('[data-stat]')) return {};
  d.querySelectorAll('[data-stat]').forEach(i => { v[i.dataset.stat] = Math.round(+i.value || 0); });
  return { stats: v };
}
function ojPreparer() {
  const t = E.tech; $('oj-nom').textContent = t.nom; $('oj-genre').textContent = t.genre + ' · ' + t.code; $('oj-desc').textContent = t.description || '(pas de description)';
  // (27/11) « Modifier » d'une copie (E.cree) : son nom, sa description et ses réglages ; sinon ceux de l'original (avant : le nom de
  // la copie était remplacé par « <original> (copie) » juste après avoir été posé)
  const copie = E.cree && E.cree.mod === 'MesObjets';
  if (!copie) { $('oj-nom-copie').value = t.nom + ' (copie)'; $('oj-desc-copie').value = t.description || ''; }
  $('oj-formulaire').style.display = '';                 // (15/11/2026) copie pour TOUS les objets (VRFW : la base suffit)
  const ic = t.icone, fichier = ic && /\/(01_icon_emblem|25_icon_nameplate)$/.test(ic.fichier.replace(/\/[^/]*$/, ''));
  // (27/11) ce que la copie garde : réglable (bonus, synergie) ou les effets de l'original (le reste : le jeu les prend dans sa ligne)
  const effets = t.synergie ? 'ses effets et ses joueurs : réglables ensuite dans Mes créations (Cosmétique)' : t.equipement ? 'ses bonus : réglables ensuite dans Mes créations (Cosmétique)'
    : /TACTICS/.test(t.famille || '') ? 'la même tactique que « ' + t.nom + ' » (une copie ne change pas la tactique)' : 'les mêmes effets que « ' + t.nom + ' »';
  const sp = x => '<span>' + echapper(x) + '</span>';     // (27/11, parcours EN) une phrase par nœud : chacune se traduit
  $('oj-etat').innerHTML = sp(t.commun && t.commun.description === false ? 'Un NOUVEL objet : ton nom.' : 'Un NOUVEL objet : ton nom et ta description.') + ' '
    + sp('Prix et réglages : ensuite, dans Mes créations (Cosmétique).') + ' '
    + (t.synergie ? sp('Ses effets et ses joueurs se règlent dans Cosmétique (une vraie nouvelle synergie).') : t.equipement ? sp('Ses bonus se règlent dans Cosmétique.')
      : /TACTICS/.test(t.famille || '') ? sp('Même tactique que l’original (une copie ne change pas la tactique).') : sp('Mêmes effets que l’original.')) + ' '
    + sp('L’original ne change pas.') + ' '
    + sp(!ic ? 'Pas d’image dans le jeu pour ce genre d’objet : la copie s’affiche en texte, comme l’original.'
      : (t.commun ? t.commun.icone : ic.nb > 1 || fichier) ? 'Son icône : celle que tu recolores (✎ Mode dessin).' : 'Son icône : celle de l’original (le jeu la prend ailleurs, elle ne se remplace pas).');
  ojIcone();
  if (String(t.code).includes('~')) {            // (27/11) objet d'un mod : aperçu seulement (le serveur refuse sa copie)
    ojReglages(t); $('oj-exporter').disabled = true;
    $('oj-etat').innerHTML = '<span>Objet du mod</span> ' + echapper(t.mod || String(t.code).split('~')[0]) + ' : <span>aperçu et recoloration seulement, sa copie n’est pas encore possible.</span>'; return; }
  if (!copie) return ojReglages(t);
  api('/api/cosmetique', { lire: true, mod: 'MesObjets', code: E.cree.code }).then(r => {
    if (r && r.ok) { if (r.description != null) $('oj-desc-copie').value = r.description;
      if (r.stats && t.equipement) t.equipement = Object.assign({}, t.equipement, { stats: r.stats });
      if (r.synergie && t.synergie) t.synergie = Object.assign({}, t.synergie, r.synergie);
      if (t.commun && (r.rarete || r.max)) t.commun = Object.assign({}, t.commun, r.rarete ? { rarete: r.rarete } : {}, r.max ? { max: r.max } : {}); }
    ojReglages(t); }).catch(() => ojReglages(t));
}
// (28/11) code de la création ouverte par « Modifier » (E.cree) pour ce mod, sinon rien : le moteur met à jour CELLE-LÀ
const creeCode = mod => E.cree && E.cree.mod === mod ? String(E.cree.code) : undefined;
async function ojExporter() {
  if (!E.tech || E.tech.onglet !== 'objets') return majRapport('Ouvre d’abord un objet du jeu (onglet Objets).');
  const x = ojTexture();
  majRapport('Création de la copie…');
  // (27/11, muku) crampons / gants : les textures recolorées de leur modèle 3D (2e objet de l'éditeur)
  const tm = {}; for (const t of Object.values(E.textures)) if (t.modif && t.cur && t.obj && E.objets[1] && t.obj.nom === E.objets[1].nom) tm[t.nom] = t.cur.toDataURL('image/png');
  // (28/11, muku : « quand on fait Modifier, ça refait des objets en double ») « Modifier » : la clé de LA création (même si le nom change)
  const cle = E.cree && E.cree.mod === 'MesObjets' ? E.cree.code : undefined;
  const r = await api('/api/copie_objet_jeu', Object.assign({ code: E.tech.code, cle, nom: $('oj-nom-copie').value.trim(), description: $('oj-desc-copie').value, prix: null,
    icone: x && x.cur ? x.cur.toDataURL('image/png') : null, textures_modele: tm }, ojValeursReglages()));
  majRapport(r.ok ? 'Objet créé (pas encore installé) : ' + r.dossier + '\n- ' + r.rapport.join('\n- ') + '\n« Installer dans le jeu » (mod MesObjets).' : 'Erreur : ' + r.erreur);
  return r;                                   // (22/11) « Créer » crée seulement : on installe depuis la carte (Mes créations)
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
    majRapport(r.ok ? (r.avertissement ? '⚠ ' + r.avertissement            // (22/11) 1re ligne = celle que montre Mes créations
                      : 'C’est dans le jeu ! ' + (OU_EN_JEU[mod || 'MesTechniques'] || '') + ' (Relance le jeu s’il était ouvert.)')
                      + (r.repares ? '\nRéparé :\n- ' + r.repares.join('\n- ') : '')   // (22/11) totems / esprits des cinématiques, cinématiques d'échec
                      + (r.controle ? '\n⚠ À vérifier (le jeu ignorera) :\n- ' + r.controle.join('\n- ') : '')   // (22/11) moteur/verifier_mods.py
                      + '\nInstallé dans ' + r.dossier + '\nSauvegarde : ' + r.sauvegarde + '\nLance le jeu, puis regarde le journal de VRFW (aucune ligne ERROR).'
                    : 'Pas installé : ' + r.erreur);
    // (22/11, journal d'un joueur : « Installed » mais rien en jeu, son jeu n'avait pas de dossier mods) l'avertissement restait
    // dans les détails, invisible depuis Mes créations (1re ligne seulement) : fenêtre, avec le réglage du dossier du jeu
    if (r.ok && r.avertissement) alert('⚠ ' + r.avertissement);
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
    { const tp = (!E.avant && (E.teintePtl || {})[o.nom]) || null; for (const v of o.emetteursVue) v.teintePtl = tp ? tsc(tp) : null; }
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
// (23/11, retour de muku : « la bannière du web reste par-dessus le natif, et nous suit dans tous les onglets ») la bannière de
// l'aperçu WebGL n'est cachée que par l'animation WebGL, qui ne tourne plus quand le lecteur du jeu (qui dessine SA bannière)
// est ouvert : cachée aussi quand il l'est, et hors d'une technique (vérifié aussi toutes les 300 ms par majApproche)
function telopWebVisible() {
  return !NATIF.actif && !!E.tech && !E.tech.perso && (E.onglet === 'techniques' || $('centre').classList.contains('dans-stats'));
}
function majTelop(f) {
  const el = $('l-telop'), t = E.lecteur && E.lecteur.d.telop;
  // (14/11/2026) courbes du modèle de menu du jeu (soccer10_01) comme le lecteur natif : entrée à 30 images/s dès « montrée »,
  // sortie à 60 images/s dès « cachée » (MESURÉ sur les vidéos) ; avant : zoom 1,35 -> 1 approché
  const C = t && t.courbes, fin = t && t.fin != null ? t.fin : Infinity;
  const val = (k, u, d) => { if (!k || !k.length) return d; if (u <= k[0][0]) return k[0][1]; if (u >= k[k.length - 1][0]) return k[k.length - 1][1];
    for (let i = 1; i < k.length; i++) if (u < k[i][0]) return k[i - 1][1] + (k[i][1] - k[i - 1][1]) * (u - k[i - 1][0]) / (k[i][0] - k[i - 1][0]); return d; };
  const sortie = C && f >= fin ? (f - fin) * (t.vitesse_out || 1) : null;
  if (!t || !E.vue.lecteur || !$('l-banniere').checked || f < t.debut || (f >= fin && (!C || sortie > 10)) || !telopWebVisible()) { el.style.display = 'none'; return; }
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
    if (B.ed.manquante) $('b-rapport').textContent = String(B.ed.p.police).startsWith('jeu:') ? B.ed.manquante   // (24/11) lettres du jeu : la police reste
      : `Police absente de ce PC : ${B.ed.manquante} (Impact utilisée à la place).`;
  } catch (e) { $('b-rapport').textContent = 'Police : ' + e.message; }
}
function reglagesBanniere() {
  const p = B.ed.p;
  for (const k of ['texte', 'haut', 'milieu', 'bas', 'c1', 'c2', 'ombre', 'lueur']) $('b-' + k).value = p[k];
  $('b-police').value = p.police;
  for (const k of ['taille', 'espacement', 'saute', 'tourne', 'x', 'y', 'e1', 'e2', 'ombreX', 'ombreY', 'lueurT']) $('b-' + k).value = p[k];
  $('b-penche').value = Math.round(p.penche * 100); $('b-ombreA').value = Math.round(p.ombreA * 100);
  banniereJeuReglages();
}
// (27/11, essai profond des boutons : Penché, contours, ombre… ne faisaient RIEN avec les lettres du jeu) les styles « jeu: »
// (Lettres du jeu, esprit guerrier, totem, armure) sont des images du jeu (banniere.js _dessinerJeu : texte, x, y seulement) :
// les autres réglages sont grisés, avec une phrase qui dit pourquoi
function banniereJeuReglages() {
  if (!B.ed || !$('b-reglages')) return;
  const jeu = String(B.ed.p.police || '').startsWith('jeu:');
  const garde = new Set(['b-texte', 'b-police', 'b-x', 'b-y']);
  for (const el of document.querySelectorAll('#b-reglages input, #b-reglages select, #b-reglages button, #b-styles button')) {
    if (garde.has(el.id)) continue;
    el.disabled = jeu; const l = el.closest('.ligne'); if (l) l.classList.toggle('b-inutile', jeu); }
  if ($('b-jeu-note')) $('b-jeu-note').hidden = !jeu;
}
async function ouvrirBannieres() {
  if (!B.ed) {
    B.ed = new EditeurBanniere($('b-vue'));
    let dispo = null;                                   // polices présentes sur ce PC : seules celles-là sont proposées
    try { dispo = new Set(await api('/api/polices')); } catch (e) { }
    // (23/11, demande de muku) les vraies lettres des bannières du jeu, une couleur par élément (en tête de liste)
    const tr_ = x => (window.trad ? window.trad(x) : x);         // (24/11) titres des groupes traduits (attribut label)
    const gJeu = document.createElement('optgroup'); gJeu.label = tr_('Lettres du jeu');
    for (const [el, n] of [['wind', 'Air'], ['fire', 'Feu'], ['forest', 'Forêt'], ['mountain', 'Montagne'], ['void', 'Néant']]) {
      const o = document.createElement('option'); o.value = 'jeu:' + el; o.textContent = 'Lettres du jeu — ' + n; gJeu.appendChild(o); }
    $('b-police').appendChild(gJeu);
    // (24/11, muku : « proposer le style d'écriture des Keshin, totem et armure dans les polices ») comme les bannières du jeu :
    // esprit guerrier (lettres plus étroites, « / » = 2e ligne : nom / titre), totem (le « Totem » du jeu au-dessus du nom,
    // lettres claires au contour bleu foncé), armure (ARMED : lettres violettes)
    const gSt = document.createElement('optgroup'); gSt.label = tr_('Styles des esprits');
    for (const [el, n] of [['wind', 'Air'], ['fire', 'Feu'], ['forest', 'Forêt'], ['mountain', 'Montagne'], ['void', 'Néant']]) {
      const o = document.createElement('option'); o.value = 'jeu:esprit:' + el; o.textContent = 'Esprit guerrier — ' + n; gSt.appendChild(o); }
    // (24/11, muku : « transforme-moi ça en police ») planches d'alphabet de muku : chaque lettre = ses pixels (moteur/police_image.py)
    for (const [v, n] of [['jeu:totem', 'Totem'], ['jeu:armure', 'Armure (lettres du jeu)'], ['jeu:image:armure2', 'Armure — planche 2']]) {
      const o = document.createElement('option'); o.value = v; o.textContent = n; gSt.appendChild(o); }
    $('b-police').appendChild(gSt);
    for (const [f, n] of EditeurBanniere.polices()) {
      if (dispo && !dispo.has(f.toLowerCase())) continue;
      const o = document.createElement('option'); o.value = f; o.textContent = n; $('b-police').appendChild(o); }
    if (window.brancherPolices) brancherPolices($('b-police'), p => p.fichier);       // (22/11) polices importées
    for (const [n, st] of Object.entries(EditeurBanniere.styles())) { const b = document.createElement('button'); b.textContent = n;
      b.onclick = () => { Object.assign(B.ed.p, st); reglagesBanniere(); dessinerBanniere(); }; $('b-styles').appendChild(b); }
    const num = { penche: v => v / 100, ombreA: v => v / 100 };
    document.querySelectorAll('#b-reglages input, #b-reglages select').forEach(el => el.addEventListener('input', () => {
      const k = el.id.slice(2); B.ed.p[k] = el.type === 'range' ? (num[k] ? num[k](+el.value) : +el.value) : el.value;
      if (k === 'police') banniereJeuReglages(); dessinerBanniere(); }));
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
      // (23/11) esprit / totem / armure : sortie MesEsprits (bannière du nom, ou ARMED de l'armure)
      try { const r = B.choix.genre ? await api('/api/banniere_esprit', { genre: B.choix.genre, id: B.choix.id, image: B.ed.image() })
          : await api('/api/banniere', { nom: B.choix.nom, base: B.choix.base, image: B.ed.image() }); E.telopV = Date.now();
        $('b-rapport').textContent = r.ok ? r.rapport.join('\n') : 'Erreur : ' + r.erreur; } catch (e) { $('b-rapport').textContent = 'Erreur : ' + e.message; } };
    reglagesBanniere();
  }
  // choix : la technique ouverte + les copies déjà créées
  const etat = await api('/api/etat');
  B.liste = [];
  if (E.tech && !E.tech.perso) B.liste.push({ ouverte: true, titre: 'Technique ouverte : ' + E.tech.nom, base: E.tech.code, texte: $('f-nom').value || E.tech.nom });
  for (const [nom, v] of Object.entries(etat.deja || {})) B.liste.push({ nom, titre: v.nom, sous: v.key + ' · copie de ' + v.base, base: v.base, texte: v.nom });
  // (23/11, muku : « tu n'as pas fait les bannières pour les totems et les armures ») + mes esprits guerriers et totems (la bannière
  // de leur nom, affichée à l'invocation) et mes armures (la bannière ARMED de la mise en armure, commune dans le jeu)
  try {
    const GENRES = { esprit: 'Esprit guerrier', totem: 'Totem', armure: 'Armure : bannière ARMED' };
    for (const x of await api('/api/bannieres_esprits'))
      B.liste.push({ genre: x.genre, id: x.id, titre: x.nom, sous: GENRES[x.genre], base: x.base, texte: x.genre === 'armure' ? ({ en: 'Armourfy!', es: '¡Armadura!' }[window.ATELIER_LANGUE] || 'Armure !') : x.nom, style: x.style });   // (24/11) texte du jeu dans la langue de l'Atelier
  } catch (e) { }
  const box = $('b-choix'); box.innerHTML = '';
  if (!B.liste.length) box.innerHTML = '<p class="aide">Ouvre une technique (onglet Techniques) ou crée d\'abord une copie.</p>';
  B.liste.forEach(c => { const d = document.createElement('div'); d.innerHTML = `${c.titre}${c.sous ? `<small>${c.sous}</small>` : ''}`;
    d.onclick = () => choisirBanniere(c, d); box.appendChild(d); });
  // (23/11) ouvert depuis « cosmétique » d'une technique créée : cette copie déjà choisie
  const pre = B.preselect ? B.liste.findIndex(c => c.id === B.preselect || (c.sous && c.sous.startsWith(B.preselect + ' ·'))) : -1; B.preselect = null;
  if (B.liste.length) choisirBanniere(B.liste[Math.max(0, pre)], box.children[Math.max(0, pre)]); else dessinerBanniere();
}
function choisirBanniere(c, el) {
  B.choix = c; document.querySelectorAll('#b-choix div').forEach(x => x.classList.toggle('sel', x === el));
  B.ed.p.texte = c.texte; $('b-texte').value = c.texte;
  if (c.style) { B.ed.p.police = 'jeu:' + c.style; $('b-police').value = B.ed.p.police; }   // (24/11) le style du jeu pour ce genre
  banniereJeuReglages();
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
    if (E.onglet !== o) { E.filtreSource = null; E.filtreSerie = null; if (o !== 'techniques') quitterIsolement(false); }   // (17/11/2026) filtres Jeu / Mods et série : par onglet
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
    // (23/11) le lecteur du jeu est ouvert dès qu'une technique l'est : en pause hors de l'onglet Techniques, fermé si elle est vidée
    if (o !== 'techniques' && NATIF.actif && !NATIF.hote) cmdNatif('pause 1');
    if (o !== 'bannieres' && o !== 'hub' && E.tech && E.tech.onglet !== o) { retirerSuite(); if (!NATIF.hote) finNatif(true); E.tech = null; E.objets = []; E.textures = {}; E.vue.vider(); E.vue.lecteur = null; E.lecteur = null;
      // (23/11, retour de muku : « ça fait comme si la technique était encore là ») barre de lecture, sélection, compteurs,
      // couleurs de la technique et listes remis à vide
      E.selPieces.clear(); E.selTex.clear();
      $('l-image').value = 0; $('l-info').textContent = ''; $('l-jouer').textContent = '▶'; if ($('l-film-info')) $('l-film-info').textContent = '';
      $('lecteur').classList.add('inactif'); if ($('l-telop')) $('l-telop').style.display = 'none';
      dessinerPieces(); dessinerTextures(); dessinerMateriaux(); dessinerTeintes(); paletteTech(); majCompteurs(); $('titre-tech').textContent = "Rien d'ouvert"; majRapport(''); }
  };
  document.querySelectorAll('.onglets button').forEach(b => b.onclick = () => changerOnglet(b.dataset.onglet));
  // (28/11, petits écrans) barre d'onglets qui défile : la molette la fait glisser ; l'onglet ouvert reste en vue
  { const nav = document.querySelector('header .onglets');
    if (nav) { nav.addEventListener('wheel', e => { if (nav.scrollWidth > nav.clientWidth + 2) { nav.scrollLeft += e.deltaY || e.deltaX; e.preventDefault(); } }, { passive: false });
      new MutationObserver(() => { const a = nav.querySelector('button.actif'); if (a && nav.scrollWidth > nav.clientWidth + 2) a.scrollIntoView({ block: 'nearest', inline: 'nearest' }); })
        .observe(nav, { subtree: true, attributes: true, attributeFilter: ['class'] }); } }
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
  $('fil').onchange = e => { E.vue.fil = e.target.checked; optionsNatif();   // (25/11) aussi le lecteur du jeu
    // (25/11, retour de muku : « le fil de fer ne marche pas » : options.json avait « fil » vide = aucune pièce choisie)
    if (e.target.checked && E.vue && !E.vue.pieces.some(p => p.sel && !p.ptl)) majRapport('Fil de fer : choisis une pièce (liste des pièces, ou clic sur l’aperçu) pour la voir en traits blancs.'); };
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
  if ($('tex-isoler')) $('tex-isoler').onclick = () => E.isole ? quitterIsolement() : isolerObjet([...E.selTex][0]);   // (24/11) objet seul
  if ($('tex-dessiner')) $('tex-dessiner').onclick = () => { const k = [...E.selTex][0]; if (!k) return majRapport('Choisis d\'abord une texture (clic sur une vignette), puis « Dessiner ».'); ouvrirEditeur(k); };
  cherche.addEventListener('focus', () => { if (estPerso() || E.onglet === 'techniques') cherche.dispatchEvent(new Event('input')); });
  document.addEventListener('click', ev => { if (!ev.target.closest('.recherche')) res.style.display = 'none'; });
  // lecteur
  E.vue.surImage = (f, res) => { majTelop(f); majSon(f); $('vue').classList.toggle('ciel', !!E.vue.lecteur && $('l-terrain').checked && res.decor !== false);
    if (NATIF.actif) return;                   // (14/11/2026) lecteur natif ouvert : barre et texte suivent SON image (suivreNatif)
    if (document.activeElement !== $('l-image')) $('l-image').value = f;
    const T_ = s => (window.I18N ? I18N.trad(s) : s);   // (27/11) traduit (avant : « image … · plan c0020 » en français)
    $('l-info').textContent = `${T_('image')} ${f} / ${E.lecteur ? E.lecteur.duree : 0}${res.plan ? ' · ' + T_('plan') + ' ' + res.plan.nom : ''}`; $('l-jouer').textContent = E.vue.joue ? '❚❚' : '▶'; };
  // (14/11/2026 : l'ancien lecteur, rendu Python à la pause et « Film Direct3D », est retiré : tout passe par le lecteur C++)
  if ($('l-natif-bouton')) $('l-natif-bouton').onclick = () => lecteurNatif();
  $('l-jouer').onclick = () => { if (!E.vue.lecteur) activerAnimation(true); E.vue.joue = false; lecteurNatif(); };   // lecture = lecteur C++
  // (23/11, muku : « tout ce que tu peux en natif ») image par image = lecteur du jeu (ouvert en pause sur l'image si besoin)
  $('l-image').oninput = () => { if (NATIF.actif) { NATIF.imageVoulue = undefined; cmdNatif('image ' + $('l-image').value); return; }
    if (!E.vue.lecteur) activerAnimation(true); E.vue.joue = false; E.vue.image = +$('l-image').value; natifSurImage(+$('l-image').value); };
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
    // (23/11) flèches / Début sans lecteur ouvert : il s'ouvre en pause sur l'image voulue
    if (!NATIF.actif) { const d = { ArrowRight: 1, ArrowLeft: -1, Home: 0 }[ev.code];
      if (d !== undefined && E.tech && !E.tech.perso && E.vue && E.lecteur) { ev.preventDefault();
        natifSurImage(d === 0 ? 0 : Math.max(0, Math.min(E.lecteur.duree - 1, Math.floor(E.vue.image) + d))); }
      return; }                                   // lecteur incrusté : ses touches
    const k = { ArrowRight: 'pas 1', ArrowLeft: 'pas -1', Home: 'debut', KeyE: 'ecran', Escape: 'quitter' }[ev.code];
    // (23/11) Échap : d'abord pause (on reste sur l'image du jeu), Échap encore : fermer (l'aperçu approché revient)
    if (k === 'quitter' && $('l-jouer').textContent === '❚❚') { ev.preventDefault(); cmdNatif('pause 1'); return; }
    if (k) { ev.preventDefault(); NATIF.imageVoulue = undefined; if (k === 'quitter') finNatif(true); else cmdNatif(k); } });
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
  // (22/11, muku : « le bouton créer marche pas avec mon loup ») les boutons « Installer » des panneaux sont RETIRÉS (un seul
  // bouton Créer) : $('installer') = null faisait planter ce bloc avant de brancher le « Créer » des esprits et totems
  $('exporter').onclick = exporter;
  $('exporter-perso').onclick = exporterPerso;
  if ($('installer')) $('installer').onclick = () => installer('MesTechniques');
  if ($('installer-perso')) $('installer-perso').onclick = () => installer('MesEsprits');
  if ($('ouvrir-maillots')) $('ouvrir-maillots').onclick = async () => { const r = await api('/api/ouvrir_maillots', {});
    $('rapport-maillots').textContent = r.ok ? "L'Atelier Maillots s'ouvre dans sa fenêtre." : r.erreur; };
});


// ------------------------------------------------------------------ (15/11/2026) techniques d'un nouveau joueur, technique liée d'un esprit
// Règles (moteur/coups.py) : une carte = 9 cases [technique, niveau] ; CharacterReforged (activé) : techniques en cases 1 à 6,
// cases 7-8 vides, UNE aura (esprit guerrier / totem…) en case 9 où VRFW la range toute seule, niveaux selon la puissance.
const libCoup = x => (x.mod ? '★ ' : '') + x.nom + ' — ' + x.genre + ' (' + x.code + ')';
const AURAS_COUPS = ['Esprit guerrier', 'Totem', 'Armure', 'Aura', 'Miximax', 'Lien', 'Éveil', 'Mode'];
// (26/11, demande de muku) ÉTAPE « COSMÉTIQUE » d'un objet, d'une tenue ou d'un maillot : prix en boutique et icônes (objet : son
// icône est son visuel, recolorée dans l'éditeur). « Enregistrer » ou « Garder » : la création passe dans Terminées.
// (26/11, muku : « pour l'interface on va faire comme dans la boutique du jeu », puis « fais tous les menus que je t'ai envoyés »)
// ÉCRANS DE LA BOUTIQUE DU JEU, un par catégorie des 7 captures de muku (Boutique générale : Maillots, Emblèmes, Tenues ; Boutique
// d'entraînement : Crampons, Bracelets, Pendentifs, Spéciaux), avec les images du jeu, places en 1920 × 1080 (1 px du jeu = --u) :
// - barre d'onglets = cmn06_01 list_tab_base02 (verte) en (-78, 156), case choisie cmn06_20 icon_base01, icônes LUES dans
//   shop_inc GetTabIconTypeByShopSlotType + listview SetupTabIcon -> 200_icon/16_icon_list_tab « icon_list_tab_* » (teintées
//   comme sur les captures), nom de l'onglet = menu_text du jeu (GetTabTextIdByShopSlotType) dans la langue de l'Atelier ;
// - lignes shop01_02 list_base_m02_off / list_base_m01_on (contenu 508 × 88 à (8, 8) dans 524 × 104), tous les 102 px dès y = 285,
//   compteurs base_have02 / base_equip02 / base_stock01, prix token_list_base01 + jeton tk_bb000001 ; la liste = MES créations de
//   la même catégorie (ce que notre mod mettra en vente), celle qu'on règle en bleu ;
// - carte shop01_05 (calques LUS dans le .g4pkm) : win_item01 (962, 338), bandeau base_item01 bleu (boutique générale) ou
//   base_item02 vert (équipements) en (982, 538), filigrane icon_cate_* (200_icon/17_icon_category) en (1565, 540), icône 240 en
//   (1099, 436) (emblème) ou 184 en (1127, 478) (équipement), « équipé » base_equip01 (1432, 554), « possédés » base_have01 (1626, 554) ;
// - maillot : les 4 joueurs habillés + DOMICILE / EXTÉRIEUR ; son EMBLÈME a son propre onglet « Emblèmes » (muku : « on fera des
//   menus séparés pour les emblèmes ») avec « Changer l'emblème ».
// PAS montré (non lu dans les fichiers) : bonus des équipements (« Pression +70 ») et postes (ATT / MIL…), jetons du joueur.
const BQ_ONGLETS = {
  general: [[1, 'ticket01'], [2, 'uniform01'], [3, 'emblem01'], [8, 'outfit01'], [11, 'kizuna04'], [12, 'town01'], [14, 'sixth01'], [18, 'battle01'], [19, 'nameplate01']],
  entrainement: [[4, 'equip01'], [5, 'equip02'], [6, 'equip03'], [7, 'equip04'], [13, 'tactics01'], [17, 'power01'], [20, 'synergy01']] };   // T, viseur, drapeau des captures
const BQ_NOMS = {      // menu_text du jeu (ids de GetTabTextIdByShopSlotType)
  fr: { 1: 'Tickets', 2: 'Maillots', 3: 'Emblèmes', 4: 'Crampons', 5: 'Bracelets', 6: 'Pendentifs', 7: 'Spéciaux', 8: 'Tenues', 11: 'Autocollant décoratif', 12: 'Objet de lien', 13: 'Tactiques spéciales', 14: 'Passif personnalisé', 15: 'Titres', 17: 'Hyper techniques', 18: 'Consommable', 19: 'Plaques nominatives', 20: 'Synergies' },
  en: { 1: 'Tickets', 2: 'Kits', 3: 'Emblems', 4: 'Boots', 5: 'Bracelets', 6: 'Pendants', 7: 'Misc.', 8: 'Costumes', 11: 'Deco Stickers', 12: 'Bond Objects', 13: 'Special Tactics', 14: 'Custom Passive', 15: 'Titles', 17: 'Hyper Moves', 18: 'Consumables', 19: 'Nameplates', 20: 'Synergies' },
  es: { 1: 'Tiques', 2: 'Equipaciones', 3: 'Emblemas', 4: 'Botas', 5: 'Brazaletes', 6: 'Colgantes', 7: 'Especiales', 8: 'Ropa', 11: 'Pegatinas decorativas', 12: 'Objeto de vinculación', 13: 'Tácticas especiales', 14: 'Pasiva personalizada', 15: 'Títulos', 17: 'Hipertécnicas', 18: 'Consumibles', 19: 'Placas', 20: 'Sinergias' } };
const BQ_CATE = { 1: 'ticket01', 2: 'uniform01', 3: 'emblem01', 4: 'equip01', 5: 'equip02', 6: 'equip03', 7: 'equip04', 8: 'outfit01' };    // filigrane icon_cate_*
const BQ_FAMILLE = { ITEM_SHOES_INFO: 4, ITEM_MISANGA_INFO: 5, ITEM_ACCESSORY_INFO: 6, ITEM_SPECIAL_INFO: 7, ITEM_EMBLEM_INFO: 3, ITEM_TITLE_INFO: 15, ITEM_CONSUME_INFO: 18,
  ITEM_SPECIAL_TACTICS_INFO: 13, ITEM_SYNERGY_FLAG_INFO: 20, ITEM_KIZUNA_LINK_INFO: 11, ITEM_NAME_PLATE_INFO: 19,
  ITEM_COSTUME_INFO: 8, ITEM_CRAFT_OBJ_INFO: 12, ITEM_IMPORTANT_INFO: 1 };      // (27/11, VU EN JEU par muku) objets importants : onglet Tickets          // le reste (animaux, célébrations…) : 31 « Autres »
// (27/11, essai de tous les types) catégories SANS onglet dans les barres du jeu (titres, objets importants, autres) : leur onglet est
// ajouté au bout de la barre quand on a une création de ce type (avant : on ne pouvait plus y revenir après avoir changé d'onglet)
const BQ_EXTRA = { 15: 'title01', 30: 'key01', 31: 'present01' };   // 31 : pas « ALL / TOUT » (lu comme « tout »)
Object.assign(BQ_NOMS.fr, { 30: 'Objets importants', 31: 'Autres' }); Object.assign(BQ_NOMS.en, { 30: 'Key items', 31: 'Other' }); Object.assign(BQ_NOMS.es, { 30: 'Objetos clave', 31: 'Otros' });
const bqCode = c => c.mod === 'MesMaillots' ? c.code : (c.cle || c.code);
const bqSlot = (c, r) => c.mod === 'MesMaillots' ? 2 : c.mod === 'MesTenues' ? 8 : BQ_FAMILLE[r.famille] || 31;
// (27/11, muku : « le mode automatique ne fait pas une bonne image de maillot ») ICÔNE AUTOMATIQUE d'un maillot = l'ICÔNE DU JEU
// du maillot de base (même dessin, même style que la boutique), RECOLORÉE avec les couleurs de ton maillot : la texture du haut
// du maillot de base et ta texture ont la même disposition (tu peins par-dessus) ; on range les couleurs de la texture de base
// en familles (k-moyennes, 10 familles), chaque famille prend la couleur moyenne de TA texture aux mêmes pixels, puis chaque pixel
// de l'icône prend la couleur de sa famille la plus proche, en gardant son ombre (rapport de luminosité) ; contours noirs gardés.
async function bqIconeMaillotAuto(m) {
  const base = m.base || ('uni_' + m.code), im = m.images || {};
  if (!im.haut_dom) throw new Error('pas d’image du haut domicile');
  const buf = await api('/api/modele?quoi=joueur&code=c01000100&maillot=' + encodeURIComponent(m.code) + '&cote=10');
  const lg = new DataView(buf).getUint32(0, true), meta = JSON.parse(new TextDecoder().decode(new Uint8Array(buf, 4, lg)));
  const t = (meta.find(x => x.texture && /(?:^|\/)u\d{6}_20$/.test(x.texture)) || {}).texture;
  if (!t) throw new Error('texture du maillot de base introuvable');
  const [I, B, T] = await Promise.all([chargerImage('/api/maillot_icone_base?base=' + encodeURIComponent(base)), chargerImage('/tex/' + t + '.png'), chargerImage(im.haut_dom)]);
  const W = Math.min(256, B.width), H = Math.min(256, B.height);
  const lire = (img, w, h) => { const c = document.createElement('canvas'); c.width = w; c.height = h; const g = c.getContext('2d'); g.drawImage(img, 0, 0, w, h); return g.getImageData(0, 0, w, h); };
  const b = lire(B, W, H).data, tt = lire(T, W, H).data;
  // familles de couleurs de la texture de base
  const pts = []; for (let i = 0; i < b.length; i += 4) if (b[i + 3] > 128) pts.push(i);
  const K = 6, cen = []; for (let k = 0; k < K; k++) { const i = pts[Math.floor((k + 0.5) * pts.length / K)]; cen.push([b[i], b[i + 1], b[i + 2]]); }
  const proche = (r, g, bl, C) => { let m_ = 0, d0 = 1e9; for (let k = 0; k < C.length; k++) { const d = (r - C[k][0]) ** 2 + (g - C[k][1]) ** 2 + (bl - C[k][2]) ** 2; if (d < d0) { d0 = d; m_ = k; } } return m_; };
  let fam = new Uint8Array(pts.length);
  for (let it = 0; it < 8; it++) {
    const s = cen.map(() => [0, 0, 0, 0]);
    pts.forEach((i, j) => { const k = fam[j] = proche(b[i], b[i + 1], b[i + 2], cen); s[k][0] += b[i]; s[k][1] += b[i + 1]; s[k][2] += b[i + 2]; s[k][3]++; });
    s.forEach((e, k) => { if (e[3]) cen[k] = [e[0] / e[3], e[1] / e[3], e[2] / e[3]]; });
  }
  // couleur DOMINANTE de ta texture dans chaque famille (la moyenne mélangeait les motifs en une couleur terne)
  const hist = cen.map(() => new Map());
  pts.forEach((i, j) => { const q = ((tt[i] >> 4) << 8) | ((tt[i + 1] >> 4) << 4) | (tt[i + 2] >> 4), h = hist[fam[j]], e = h.get(q) || [0, 0, 0, 0];
    e[0] += tt[i]; e[1] += tt[i + 1]; e[2] += tt[i + 2]; e[3]++; h.set(q, e); });
  const dest = hist.map((h, k) => { let m_ = null; for (const e of h.values()) if (!m_ || e[3] > m_[3]) m_ = e; return m_ ? [m_[0] / m_[3], m_[1] / m_[3], m_[2] / m_[3]] : cen[k]; });
  const lum = c => 0.3 * c[0] + 0.59 * c[1] + 0.11 * c[2];
  // l'icône du jeu, recolorée
  const out = document.createElement('canvas'); out.width = out.height = 256; const g = out.getContext('2d'); g.drawImage(I, 0, 0, 256, 256);
  const ic = g.getImageData(0, 0, 256, 256), d = ic.data;
  // famille de chaque pixel choisie sur l'icône un peu floutée (sinon des points parasites aux limites des couleurs)
  const fl = document.createElement('canvas'); fl.width = fl.height = 256; const gf = fl.getContext('2d'); gf.filter = 'blur(1.5px)'; gf.drawImage(I, 0, 0, 256, 256);
  const db = gf.getImageData(0, 0, 256, 256).data;
  // contours de l'icône gardés : traits très foncés, et bord extérieur (à 4 px du fond transparent) s'il est foncé
  const loinFond = new Uint8Array(256 * 256).fill(99);
  for (let y = 0; y < 256; y++) for (let x = 0; x < 256; x++) if (d[(y * 256 + x) * 4 + 3] < 8)
    for (let dy = -4; dy <= 4; dy++) for (let dx = -4; dx <= 4; dx++) { const X = x + dx, Y = y + dy; if (X >= 0 && Y >= 0 && X < 256 && Y < 256) { const o = Y * 256 + X; loinFond[o] = Math.min(loinFond[o], Math.max(Math.abs(dx), Math.abs(dy))); } }
  for (let i = 0; i < d.length; i += 4) {
    if (d[i + 3] < 8) continue; const p = [d[i], d[i + 1], d[i + 2]], l = lum(p);
    if (l < 40 || (loinFond[i / 4] <= 4 && l < 95 && Math.max(...p) - Math.min(...p) < 50)) continue;     // contours
    // ombres et reflets de l'icône gardés NETS : écart de luminosité au centre de la famille, ajouté à la nouvelle couleur
    const k = proche(db[i], db[i + 1], db[i + 2], cen), dl = (l - lum(cen[k])) * 0.9;
    for (let c = 0; c < 3; c++) d[i + c] = Math.max(0, Math.min(255, dest[k][c] + dl));
  }
  g.putImageData(ic, 0, 0);
  return out.toDataURL('image/png');
}
// ÉMBLÈME AUTOMATIQUE : blason (forme d'écusson) aux deux couleurs principales du haut domicile du maillot, bord doré,
// initiales du nom du maillot (sans « Maillot »), 512 × 512, fond transparent
async function bqEmblemeAuto(m, nom) {
  let cols = [[40, 60, 160], [240, 200, 40]];
  try { const i_ = await chargerImage((m.images || {}).haut_dom); const t = document.createElement('canvas'); t.width = t.height = 64;
    const g0 = t.getContext('2d'); g0.drawImage(i_, 0, 0, 64, 64); const d = g0.getImageData(0, 0, 64, 64).data, h = new Map();
    for (let k = 0; k < d.length; k += 4) { if (d[k + 3] < 128) continue; const q = ((d[k] >> 5) << 6) | ((d[k + 1] >> 5) << 3) | (d[k + 2] >> 5);
      const e = h.get(q) || [0, 0, 0, 0]; e[0] += d[k]; e[1] += d[k + 1]; e[2] += d[k + 2]; e[3]++; h.set(q, e); }
    const l = [...h.values()].sort((a, b) => b[3] - a[3]).map(e => [e[0] / e[3], e[1] / e[3], e[2] / e[3]]);
    const loin = (a, b) => Math.hypot(a[0] - b[0], a[1] - b[1], a[2] - b[2]) > 90;
    if (l[0]) { cols[0] = l[0]; cols[1] = l.find(x => loin(x, l[0])) || [255, 255, 255]; } } catch (e) { /* couleurs par défaut */ }
  const rgb = c => `rgb(${c.map(v => Math.round(v)).join(',')})`, clair = c => (c[0] * 0.3 + c[1] * 0.59 + c[2] * 0.11) > 150;
  const cv = document.createElement('canvas'); cv.width = cv.height = 512; const g = cv.getContext('2d');
  const ecusson = (marge) => { g.beginPath(); g.moveTo(256, 30 + marge); g.lineTo(440 - marge, 90 + marge * 0.6); g.lineTo(430 - marge, 270);
    g.quadraticCurveTo(400 - marge * 0.5, 410 - marge * 0.4, 256, 482 - marge); g.quadraticCurveTo(112 + marge * 0.5, 410 - marge * 0.4, 82 + marge, 270);
    g.lineTo(72 + marge, 90 + marge * 0.6); g.closePath(); };
  g.shadowColor = 'rgba(0,0,0,.35)'; g.shadowBlur = 14; g.shadowOffsetY = 6;
  ecusson(0); const or = g.createLinearGradient(0, 30, 0, 480); or.addColorStop(0, '#fff3b0'); or.addColorStop(.5, '#e0a82a'); or.addColorStop(1, '#a8701a'); g.fillStyle = or; g.fill();
  g.shadowColor = 'transparent';
  ecusson(22); g.fillStyle = rgb(cols[0]); g.fill();
  g.save(); ecusson(22); g.clip(); g.fillStyle = rgb(cols[1]); g.fillRect(256 - 34, 0, 68, 512); g.globalAlpha = .18; g.fillStyle = '#fff'; g.fillRect(0, 0, 512, 200); g.restore();
  const ini = String(nom || '').replace(/^(Maillot|Tenue|Kit)\s+/i, '').split(/\s+/).filter(Boolean).map(w => w[0]).join('').slice(0, 2).toUpperCase() || '★';
  g.font = `900 ${ini.length > 1 ? 170 : 210}px "Inazuma Jeu", "Arial Black", sans-serif`; g.textAlign = 'center'; g.textBaseline = 'middle';
  g.lineWidth = 16; g.strokeStyle = clair(cols[0]) ? '#1b1b1b' : '#ffffff'; g.lineJoin = 'round'; g.strokeText(ini, 256, 275);
  g.fillStyle = clair(cols[0]) ? rgb(cols[0].map(v => v * 0.35)) : rgb(cols[1]); g.fillText(ini, 256, 275);
  return cv.toDataURL('image/png');
}
// (27/11, muku : « très mal fait le menu, on ne peut cliquer sur rien et les boutons sont pas intuitifs ») TOUT ce qui a l'air
// cliquable l'est : onglets (mes créations de cette catégorie ; vide = « aucune création ici »), lignes (choisir une création),
// touches W / C et flèches (onglet précédent / suivant, ligne au-dessus / en dessous), « Changer de boutique » (générale <->
// entraînement, comme la touche E du jeu) ; en bas de VRAIS boutons (Fermer, Changer l'icône / l'emblème, Garder tel quel,
// Enregistrer) ; l'écran reste ouvert après « Enregistrer » (la ligne prend « ✓ Terminé ») pour régler les suivantes.
async function ouvrirCosmetique(c0) {
  const Z = (pl, z) => `/ui_jeu/zone/${pl}/${z}.png`;
  const lgJeu = ['en', 'es'].includes(window.ATELIER_LANGUE) ? window.ATELIER_LANGUE : 'fr';     // textes du jeu dans la langue de l'Atelier
  const defaut = c => c.mod === 'MesTenues' ? 28 : c.mod === 'MesMaillots' ? 1 : 10;
  const fiches = new Map(), cle = c => c.mod + '|' + bqCode(c);
  const charger = async c => {
    if (!fiches.has(cle(c))) {
      let r; try { r = await api('/api/cosmetique', { lire: true, mod: c.mod, code: bqCode(c) }); } catch (e) { r = { ok: false, erreur: e.message }; }
      const t = r.ok && r.reglages ? JSON.parse(JSON.stringify(r.reglages)) : null;     // (27/11) réglages : l'original + ceux de la copie
      if (t) { if (r.stats && t.equipement) t.equipement.stats = r.stats; if (r.synergie && t.synergie) Object.assign(t.synergie, r.synergie);
        if (t.commun) { if (r.rarete) t.commun.rarete = r.rarete; if (r.max) t.commun.max = r.max; } }
      fiches.set(cle(c), r.ok ? { c, r, t, img: {}, prix: r.prix || defaut(c), slot: bqSlot(c, r) } : null);
    }
    return fiches.get(cle(c)); };
  const premiere = await charger(c0);
  if (!premiere) return alert('création inconnue');
  await Promise.all((HUB.creations || []).filter(x => ['MesObjets', 'MesTenues', 'MesMaillots'].includes(x.mod)).map(charger));
  const toutes = () => [...fiches.values()].filter(Boolean);
  // (27/11, muku : « un maillot ne fait pas forcément un emblème ») emblème FACULTATIF : l'onglet Emblèmes ne montre que les
  // maillots qui en ont un (+ le maillot qu'on règle, pour lui en ajouter un) et les objets emblèmes ; « Retirer l'emblème »
  const embImg = x => x.sansEmb ? null : (x.img.embleme || x.r.embleme);
  // (27/11, initiative) maillot sans icône à toi : celle du maillot de base, que le mod met dans ce cas (avant : case vide)
  const iconeDe = x => x.img.icone || x.r.icone || (x.c.mod === 'MesMaillots' && x.c.maillot && x.c.maillot.base ? '/api/maillot_icone_base?base=' + encodeURIComponent(x.c.maillot.base) : null);
  // (27/11, muku : « arrête de faire des emblèmes à chaque maillot ») un maillot sans emblème n'a PAS de ligne ici ; on lui en
  // n'en ajoute pas (27/11, muku : plus de « Ajouter un emblème » ni « Importer une image » : le mode dessin sait importer)
  const dansOnglet = s => s === 3 ? toutes().filter(x => (x.c.mod === 'MesMaillots' && (embImg(x) || x.sansEmb)) || x.slot === 3) : toutes().filter(x => x.slot === s);
  const boutiqueDe = x => x.c.mod === 'MesObjets' && x.r.boutique === 'entrainement' ? 'entrainement' : 'general';
  const ongletsDe = b => { const l = BQ_ONGLETS[b].slice(), vus = new Set(l.map(([s]) => s));
    const ext = [];
    for (const x of toutes()) if (boutiqueDe(x) === b && !vus.has(x.slot) && BQ_EXTRA[x.slot] && !BQ_ONGLETS[b === 'general' ? 'entrainement' : 'general'].some(([s]) => s === x.slot)) { vus.add(x.slot); ext.push([x.slot, BQ_EXTRA[x.slot]]); }
    return l.concat(ext.sort((p_, q_) => p_[0] - q_[0])); };
  const bqBoutiqueDe = s => ongletsDe('entrainement').some(([x]) => x === s) ? 'entrainement' : 'general';
  let sel = premiere, memo = premiere, slot = premiere.slot, boutique = boutiqueDe(premiere), joueursDe = null;
  let f = $('boutique-cosm');
  if (!f) { f = document.createElement('dialog'); f.id = 'boutique-cosm'; document.body.appendChild(f); }
  const vueJ = document.createElement('div'); vueJ.className = 'bq-joueurs'; vueJ.innerHTML = '<canvas class="bq-vue"></canvas><span class="bq-vue-msg"></span>';
  const nomEmb = x => (x.r.nom_embleme && (x.r.nom_embleme[lgJeu] || x.r.nom_embleme.fr)) || x.c.nom;
  const compteur = (fond, ic, n, cls) => `<span class="${cls}"><img class="bq-cfond" src="${fond}" alt=""><img class="bq-cic" src="${ic}" alt=""><b>${n}</b></span>`;
  const ligne = (x, i) => {
    const on = x === sel, emb = slot === 3 && x.c.mod === 'MesMaillots', icone = emb ? embImg(x) : iconeDe(x);
    return `<div class="bq-ligne${on ? ' bq-on' : ''}" data-i="${i}" title="${on ? '' : echapper('Choisir « ' + x.c.nom + ' »')}">
      <img class="bq-lfond" src="${Z('shop01_02', on ? 'list_base_m01_on' : 'list_base_m02_off')}" alt="">${on ? '<i class="bq-fleche"></i>' : ''}
      <span class="bq-ic">${icone ? `<img src="${icone}" alt="">` : ''}</span>
      <span class="bq-nom">${echapper(emb ? nomEmb(x) : x.c.nom)}</span>${emb && !icone ? `<span class="bq-fait bq-sans-emb">${x.sansEmb ? 'Emblème retiré' : 'Nouvel emblème'}</span>` : x.r.fait ? '<span class="bq-fait">✓ Terminé</span>' : ''}
      ${boutique === 'entrainement' ? ([4, 5, 6, 7].includes(x.slot) ? compteur(Z('shop01_02', 'base_equip02'), Z('shop01_05', 'gtxt_equip01'), 0, 'bq-equipe') : '') + compteur(Z('shop01_02', 'base_have02'), Z('shop01_02', 'icon_have01'), 0, [4, 5, 6, 7].includes(x.slot) ? 'bq-avoir bq-avoir2' : 'bq-avoir')
        : compteur(Z('shop01_02', 'base_have02'), Z('shop01_02', 'icon_have01'), 0, 'bq-avoir') + compteur(Z('shop01_02', 'base_stock01'), Z('shop01_02', 'icon_stock01'), 1, 'bq-stock')}
      <label class="bq-prix"${on ? ' title="Prix en boutique (jetons) : clique pour le changer"' : ''}><img class="bq-pfond" src="${Z('shop01_02', 'token_list_base01')}" alt="">
        <img class="bq-jeton" src="${Z('icon_item10', 'tk_bb000001')}" alt="">${on ? `<input type="number" min="1" class="cosm-prix" value="${x.prix}"><i class="bq-crayon">✎</i>` : `<b>${x.prix}</b>`}</label></div>`; };
  const changerOnglet = s => { slot = s; boutique = bqBoutiqueDe(s); const l = dansOnglet(s); sel = l.includes(memo) ? memo : l.includes(sel) ? sel : l[0] || null; dessiner(); };   // un onglet vide n'oublie pas la création réglée
  const dessiner = () => {
    const emb = slot === 3 && !!sel && sel.c.mod === 'MesMaillots', liste = dansOnglet(slot), onglets = ongletsDe(boutique), n = onglets.length;
    const pas = n > 9 ? 640 / (n - 1) : 80, ech = Math.min(1, (pas - 4) / 76);   // (27/11) plus de 9 onglets : resserrés dans la zone verte
    const ia = onglets.findIndex(([s]) => s === slot), titre = boutique === 'entrainement' ? 'Boutique d’entraînement' : 'Boutique générale';
    const equip = boutique === 'entrainement', equipe = [4, 5, 6, 7].includes(slot), kit = sel && sel.c.mod === 'MesMaillots' && !emb, mannequin = sel && sel.c.mod === 'MesTenues';
    const ic = sel && (emb ? embImg(sel) : iconeDe(sel));
    const boutons = !sel ? [] : emb ? [['embleme', 'Changer l’emblème', "Emblème d'équipe (512 × 512, fond transparent ; vendu avec le maillot, même prix)"]]
      : sel.c.mod === 'MesTenues' || sel.c.mod === 'MesMaillots' || (sel.c.mod === 'MesObjets' && sel.r.icone && sel.r.dessin !== false) ? [['icone', 'Changer l’icône', 'Icône de la boutique (256 × 256, fond transparent)']] : [];   // (27/11) objets aussi
    const note = !sel ? (slot === 3 ? 'Aucun de tes maillots n’a d’emblème.' : 'Aucune de tes créations dans cette catégorie.')
      : emb ? 'L’emblème est vendu avec le maillot, au même prix.'
      : 'Clique le prix pour le changer.';   // (27/11, initiative) une ligne : les boutons parlent d'eux-mêmes
    f.style.backgroundImage = `url('${Z('shop01_00', 'bg01')}')`;      // (27/11) plein écran : le fond du jeu sur toute la fenêtre
    f.innerHTML = `<div class="bq-ecran" style="background-image:url('${Z('shop01_00', 'bg01')}')">
      <div class="bq-haut"><span class="bq-coin"><img src="${Z('shop01_00', 'bg_icon_shop01')}" alt=""></span><b>${titre}</b><small>Cosmétique${sel ? ' : ' + echapper(sel.c.nom) : ''}</small>
        <button class="bq-x cosm-fermer2" title="Fermer (Esc)">✕</button></div>
      <img class="bq-barre" src="${Z('cmn06_01', 'list_tab_base02')}" alt="">
      ${ia >= 0 ? `<img class="bq-case" src="${Z('cmn06_20', 'icon_base01')}" alt="" style="left:calc(var(--u) * ${440 + (ia - (n - 1) / 2) * pas - 46 * ech});width:calc(var(--u) * ${92 * ech})">` : ''}
      ${onglets.map(([s, ico], k) => `<button class="bq-onglet${s === slot ? ' bq-actif' : ''}${dansOnglet(s).length ? '' : ' bq-vide'}" data-slot="${s}"
        style="left:calc(var(--u) * ${440 + (k - (n - 1) / 2) * pas - pas / 2});width:calc(var(--u) * ${pas})${ech < 1 ? ';--ech:' + ech : ''}" title="${echapper(((BQ_NOMS[lgJeu] || BQ_NOMS.fr)[s] || '') + ' (' + dansOnglet(s).length + ')')}">
        <i style="-webkit-mask-image:url('${Z('icon_list_tab', 'icon_list_tab_' + ico)}');mask-image:url('${Z('icon_list_tab', 'icon_list_tab_' + ico)}')"></i></button>`).join('')}
      <img class="bq-tri" src="${Z('cmn06_01', 'icon_sort01')}" alt="">
      <button class="bq-touche-w" title="Onglet précédent (W)"><img src="${Z('gaiji_key', 'gaiji_w')}" alt="W"></button>
      <button class="bq-touche-c" title="Onglet suivant (C)"><img src="${Z('gaiji_key', 'gaiji_c')}" alt="C"></button>
      <div class="bq-categorie">${echapper((BQ_NOMS[lgJeu] || BQ_NOMS.fr)[slot] || '')}</div>
      <div class="bq-liste">${liste.length ? liste.map(ligne).join('') : `<p class="bq-vide-txt">${echapper('Aucune de tes créations dans cette catégorie.')}</p>`}</div>
      <img class="bq-tokens-trait" src="${Z('shop01_03', 'token_line01')}" alt=""><img class="bq-tokens" src="${Z('shop01_03', 'gtxt_token01')}" alt="TOKENS">
      ${kit ? `<div class="bq-cotes"><img src="/ui_jeu/zone/shop01_07/${lgJeu}/gtxt_home01.png" alt=""><img src="/ui_jeu/zone/shop01_07/${lgJeu}/gtxt_away01.png" alt=""></div>` : ''}
      ${sel && !kit && !mannequin ? `<img class="bq-win" src="${Z('shop01_05', 'win_item01')}" alt="">
        <img class="bq-bande" src="${Z('shop01_05', equip ? 'base_item02' : 'base_item01')}" alt="">
        ${BQ_CATE[slot] ? `<img class="bq-filigrane" src="${Z('icon_category', 'icon_cate_' + BQ_CATE[slot])}" alt="">` : ''}
        ${ic ? `<img class="${emb || !equip ? 'bq-grande-emb' : 'bq-grande-eq'}" src="${ic}" alt="">` : `<span class="bq-sans">${emb ? (sel.sansEmb ? 'Emblème retiré' : 'Nouvel emblème : à faire') : ''}</span>`}
        <span class="bq-carte-nom">${echapper(emb ? nomEmb(sel) : sel.c.nom)}</span>
        ${equipe ? compteur(Z('shop01_05', 'base_equip01'), Z('shop01_05', 'gtxt_equip01'), 0, 'bq-c-equipe') : ''}
        ${compteur(Z('shop01_05', 'base_have01'), Z('shop01_05', 'icon_have01'), 0, 'bq-c-avoir')}` : ''}
      <div class="bq-message"><span class="cosm-etat">${echapper(note)}</span></div>
      <div class="bq-bas">
        <button class="bq-btn cosm-boutique"${ongletsDe(boutique === 'entrainement' ? 'general' : 'entrainement').some(([x]) => dansOnglet(x).length) ? '' : ' hidden'} title="Passer à la ${boutique === 'entrainement' ? 'Boutique générale' : 'Boutique d’entraînement'}">⇄ ${boutique === 'entrainement' ? 'Boutique générale' : 'Boutique d’entraînement'}</button>
        ${boutons.map(([k, t, aide]) => `${sel.c.mod === 'MesMaillots' || sel.c.mod === 'MesTenues' ? `<button class="bq-btn bq-auto-btn" data-auto="${k}" title="${sel.c.mod === 'MesTenues' ? 'La tenue en croix sur le mannequin, comme les icônes du jeu' : k === 'embleme' ? 'Blason aux couleurs du maillot, avec ses initiales' : 'L’icône du jeu du maillot de base, aux couleurs de ton maillot'}">✨ Automatique</button>` : ''}
          <button class="bq-btn bq-dessin-btn" data-dessin="${k}" title="${echapper(aide)}">✎ ${k === 'embleme' ? 'Dessiner l’emblème' : 'Dessiner l’icône'}</button>`).join('')}
        ${sel && sel.c.mod === 'MesObjets' && reglable(sel) ? `<button class="bq-btn bq-regl-btn${sel.ouvert ? ' bq-actif' : ''}" title="Bonus, synergie, type de titre, quantité…">⚙ <span>Réglages</span></button>` : ''}
        <!-- (27/11, muku) plus de « Retirer l’emblème » -->
        ${sel ? `<button class="bq-btn bq-ok cosm-ok" title="Enregistrer le prix, les images et les réglages">✔ <span>Enregistrer</span></button>` : ''}</div>
    </div>`;
    const ecran = f.querySelector('.bq-ecran');
    // (27/11, muku : « les stats se choisissent dans Cosmétique ») réglages de la copie : panneau gardé par fiche (rien n'est perdu
    // en changeant de ligne), résumé façon jeu dans la carte (« Frappe +60 · Agilité +40 »)
    if (sel && sel.c.mod === 'MesObjets' && reglable(sel)) {
      if (!sel.panneau) { sel.panneau = document.createElement('div'); sel.panneau.className = 'bq-reglages-corps';
        ojReglagesDans(sel.t, sel.panneau); bqEmbellir(sel.panneau, sel.t);
        sel.panneau.addEventListener('input', () => { if (sel) resume(); }); sel.panneau.addEventListener('change', () => { if (sel) resume(); }); }
      const res = document.createElement('div'); res.className = 'bq-resume'; ecran.appendChild(res);
      if (sel.ouvert) { const w = document.createElement('div'); w.className = 'bq-reglages';
        w.innerHTML = `<div class="bq-reglages-titre"><b>Réglages : ${echapper(sel.c.nom)}</b><button class="bq-btn" title="Revenir à la carte">✕</button></div>`;
        w.appendChild(sel.panneau); w.querySelector('button').onclick = () => { sel.ouvert = false; dessiner(); }; ecran.appendChild(w); }
      resume(); }
    const rb = f.querySelector('.bq-regl-btn'); if (rb) rb.onclick = () => { sel.ouvert = !sel.ouvert; dessiner(); };
    if (mannequin) { ecran.appendChild(vueJ); if (joueursDe !== cle(sel.c)) { joueursDe = cle(sel.c); tenue3D(vueJ.querySelector('.bq-vue'), vueJ.querySelector('.bq-vue-msg'), bqCode(sel.c)); } }
    if (kit) { ecran.appendChild(vueJ); if (joueursDe !== cle(sel.c)) { joueursDe = cle(sel.c); joueursMaillot(vueJ.querySelector('.bq-vue'), vueJ.querySelector('.bq-vue-msg'), sel.c.maillot); } }
    const pr = f.querySelector('.cosm-prix'); if (pr) pr.oninput = () => { if (pr.value !== '') sel.prix = +pr.value; };
    f.querySelectorAll('.bq-onglet').forEach(o => o.onclick = () => changerOnglet(+o.dataset.slot));
    f.querySelectorAll('.bq-ligne').forEach(l => l.onclick = e => { const x = liste[+l.dataset.i]; if (x && x !== sel && !e.target.closest('.bq-prix')) { sel = memo = x; dessiner(); } });
    f.querySelector('.bq-touche-w').onclick = () => tourner(-1);
    f.querySelector('.bq-touche-c').onclick = () => tourner(1);
    f.querySelectorAll('input[type=file]').forEach(inp => inp.onchange = () => { const fi = inp.files[0]; if (!fi) return; const lr = new FileReader();
      lr.onload = () => { sel.img[inp.dataset.k] = lr.result; if (inp.dataset.k === 'embleme') sel.sansEmb = false; dessiner(); f.querySelector('.cosm-etat').textContent = 'Image prête : « Enregistrer » pour la garder.'; }; lr.readAsDataURL(fi); });
    f.querySelectorAll('.bq-auto-btn').forEach(b => b.onclick = () => imageAuto(b.dataset.auto));
    f.querySelectorAll('.bq-dessin-btn').forEach(b => b.onclick = () => dessinerImage(b.dataset.dessin).catch(e => { f.querySelector('.cosm-etat').textContent = 'Erreur : ' + e.message; }));
    f.querySelector('.cosm-fermer2').onclick = () => f.close();   // (27/11, initiative) plus de « Fermer » en double : la croix et Échap
    f.querySelector('.cosm-boutique').onclick = () => { const b = boutique === 'entrainement' ? 'general' : 'entrainement';
      const s = (ongletsDe(b).find(([x]) => dansOnglet(x).length) || ongletsDe(b)[0])[0]; changerOnglet(s); };
    const o = f.querySelector('.cosm-ok');      // (27/11, muku) plus de « Garder tel quel » (bouton inutile)
    if (o) o.onclick = () => envoyer(false);
  };
  // (27/11, muku : « on doit pouvoir changer l'image ici » puis « tu as mis le mode dessin de l'Atelier Maillots, moi je veux celui
  // de l'Atelier Inazuma ») DESSIN DE L'ICÔNE / DE L'EMBLÈME = le MODE DESSIN de l'Atelier (atelier.js : calques, outils façon
  // Photoshop) : son panneau #atelier-dessin est posé dans l'écran de la boutique le temps du dessin, sur une texture temporaire
  // 256 × 256 (icône) ou 512 × 512 (emblème) qui part de l'image actuelle (sinon de l'icône du maillot de base, sinon vide) ;
  // « Terminer » / Échap le remet à sa place et rend le dessin ici (à garder avec « ✔ Enregistrer »).
  const dessinerImage = async k => {
    const x = sel; if (!x || window.__bqDessin) return;
    const taille = k === 'embleme' ? 512 : 256, cv = document.createElement('canvas'); cv.width = cv.height = taille; const g = cv.getContext('2d');
    const srcs = [x.img[k], k === 'embleme' ? embImg(x) : x.r.icone,
      k === 'icone' && x.c.maillot && x.c.maillot.base ? '/api/maillot_icone_base?base=' + encodeURIComponent(x.c.maillot.base) : null].filter(Boolean);
    for (const src of srcs) { try { g.drawImage(await chargerImage(src), 0, 0, taille, taille); break; } catch (e) { /* image suivante */ } }
    const cleT = 'bq/' + k, orig = g.getImageData(0, 0, taille, taille);
    E.textures[cleT] = { obj: { nom: 'boutique' }, nom: (k === 'embleme' ? 'Emblème : ' : 'Icône : ') + x.c.nom, info: { w: taille, h: taille }, orig, cur: cv, modif: false, moyenne: moyenne(orig) };
    const pan = $('atelier-dessin'), place = [pan.parentNode, pan.nextSibling];
    const o = document.createElement('div'); o.className = 'bq-dessin'; f.querySelector('.bq-ecran').appendChild(o); o.appendChild(pan);
    window.__bqDessin = { cle: cleT, fini: () => {
      window.__bqDessin = null; place[0].insertBefore(pan, place[1]); o.remove();
      const t = E.textures[cleT]; if (t && t.modif) { x.img[k] = t.cur.toDataURL('image/png'); if (k === 'embleme') x.sansEmb = false; }
      delete E.textures[cleT]; if (typeof A !== 'undefined') { if (A.docs) delete A.docs[cleT]; if (A.doc && A.doc.cle === cleT) A.doc = null; }
      if (f.open && fiches.get(cle(x.c)) === x) { dessiner(); if (x.img[k]) f.querySelector('.cosm-etat').textContent = 'Dessin prêt : « ✔ Enregistrer » pour le garder.'; } } };
    const videAvant = $('at-vide') ? $('at-vide').checked : false; if ($('at-vide')) $('at-vide').checked = true;   // (27/11) icône : fond vide
    const finiBq = window.__bqDessin.fini; window.__bqDessin.fini = () => { if ($('at-vide')) $('at-vide').checked = videAvant; return finiBq(); };
    document.body.classList.add('dessin'); atActiver(cleT); atOutil(A.outil && A.outil !== 'choisir' ? A.outil : 'pinceau');
    setTimeout(() => { atPlat(); dispatchEvent(new Event('resize')); }, 80);
  };
  // (27/11) « ✨ Automatique » : l'image faite toute seule (bqIconeMaillotAuto / bqEmblemeAuto), à garder avec « ✔ Enregistrer »
  const imageAuto = async k => {
    const x = sel; if (!x || !(x.c.maillot || x.c.mod === 'MesTenues')) return; const et = f.querySelector('.cosm-etat'); et.textContent = 'Image automatique en cours…';
    try { x.img[k] = x.c.mod === 'MesTenues' ? await bqIconeTenueAuto(bqCode(x.c)) : k === 'embleme' ? await bqEmblemeAuto(x.c.maillot, x.c.nom) : await bqIconeMaillotAuto(x.c.maillot); if (k === 'embleme') x.sansEmb = false; }
    catch (e) { et.textContent = 'Image automatique impossible : ' + e.message; return; }
    if (sel === x) { dessiner(); f.querySelector('.cosm-etat').textContent = 'Image automatique prête : « ✔ Enregistrer » pour la garder, ou « ✎ Dessiner » pour la retoucher.'; } };
  // (27/11) ce qui se règle pour un objet : bonus (équipement), synergie, type de titre / fond, quantité (pas « une seule »)
  const reglable = x => { const t = x && x.t; if (!t) return false; const c = t.commun || {};
    return !!(t.equipement || t.synergie || c.choix_rarete || !c.unique); };
  const resume = () => { const res = f.querySelector('.bq-resume'); if (!res || !sel || !sel.panneau) return;
    const v = ojValeursReglages(sel.panneau), l = [], T = x => window.trad ? window.trad(x) : x;     // (27/11) traduit (EN / ES)
    if (v.stats) { const t = OJ_STATS.filter(([k]) => v.stats[k]).map(([k, n]) => `${T(n)} ${v.stats[k] > 0 ? '+' : ''}${v.stats[k]}`); l.push(t.join(' · ') || T('aucun bonus'));
      const ps = ojPostes(v.stats); if (ps.length) l.push(ps.map(T).join(' ')); }
    if (v.synergie) l.push(v.synergie.effets.length + ' ' + T('effet(s)') + ' · ' + v.synergie.conditions.length + ' ' + T('joueur(s)'));
    if (v.rarete && sel.t.commun && sel.t.commun.choix_rarete) l.push(T(sel.t.commun.choix_rarete === 'titre' ? (v.rarete === 2 ? 'Titre doré' : 'Titre argenté') : (v.rarete === 2 ? 'Fond brillant' : 'Fond normal')));
    if (v.max) l.push(T('max') + ' ' + v.max);
    res.textContent = l.join('  —  '); };
  // (27/11, muku : « fais un bel affichage dans l'esprit du shop ») bonus en lignes de boutique : nom, − valeur +, barre (0 au
  // centre, jusqu'au maximum du jeu S) ; les champs d'origine restent (mêmes valeurs lues à l'enregistrement)
  const bqEmbellir = (d, t) => {
    const S = (t.equipement && t.equipement.S) || 70;
    d.querySelectorAll('[data-stat]').forEach(inp => { const lab = inp.closest('label'); if (!lab || lab.classList.contains('bq-stat')) return;
      lab.classList.add('bq-stat'); const n = lab.firstChild && lab.firstChild.nodeType === 3 ? lab.firstChild.textContent.trim() : '';
      lab.innerHTML = ''; const nom = document.createElement('span'); nom.className = 'bq-stat-nom'; nom.textContent = n;
      const moins = document.createElement('button'); moins.type = 'button'; moins.className = 'bq-pm'; moins.textContent = '−'; moins.title = '−5';
      const plus = document.createElement('button'); plus.type = 'button'; plus.className = 'bq-pm'; plus.textContent = '+'; plus.title = '+5';
      const barre = document.createElement('span'); barre.className = 'bq-stat-barre'; barre.innerHTML = '<i></i>';
      lab.append(nom, moins, inp, plus, barre);
      const maj = () => { const v = Math.max(-S, Math.min(S, Math.round(+inp.value || 0))), i = barre.firstChild;
        i.style.left = (v >= 0 ? 50 : 50 + 50 * v / S) + '%'; i.style.width = (50 * Math.abs(v) / S) + '%'; i.className = v < 0 ? 'neg' : '';
        lab.classList.toggle('bq-stat-zero', !v); };
      const pas = k => { inp.value = Math.max(-S, Math.min(S, Math.round(+inp.value || 0) + k)); inp.dispatchEvent(new Event('input', { bubbles: true })); maj(); };
      moins.onclick = () => pas(-5); plus.onclick = () => pas(5); inp.addEventListener('input', maj); maj(); });
  };
  const tourner = d => { const l = ongletsDe(boutique), i = l.findIndex(([s]) => s === slot); changerOnglet(l[(i + d + l.length) % l.length][0]); };
  const envoyer = async garder => {
    const x = sel, et = f.querySelector('.cosm-etat'); et.textContent = 'Écriture…';
    let rep; try { rep = await api('/api/cosmetique', Object.assign({ mod: x.c.mod, code: bqCode(x.c), garder, prix: x.prix, icone: x.img.icone || null, embleme: x.sansEmb ? null : x.img.embleme || null, sans_embleme: !!x.sansEmb },
      x.panneau ? ojValeursReglages(x.panneau) : {})); }
    catch (e) { rep = { ok: false, erreur: e.message }; }
    if (!rep.ok) { et.textContent = 'Erreur : ' + rep.erreur; return; }
    majRapport(rep.rapport.join('\n')); chargerHub();
    fiches.delete(cle(x.c)); const y = await charger(x.c); if (sel === x) sel = y || x;
    dessiner(); f.querySelector('.cosm-etat').textContent = '✓ ' + rep.rapport[0]; };
  // clavier comme le jeu : W / C onglets, flèches lignes, Entrée enregistre (Esc ferme : boîte de dialogue)
  // (le focus se perd quand l'écran est redessiné : écoute sur toute la page, seulement quand la boutique est ouverte)
  if (!window.__bqClavier) { window.__bqClavier = true; document.addEventListener('keydown', e => { const g = $('boutique-cosm'); if (g && g.open && g.__clavier) g.__clavier(e); }); }
  f.__clavier = e => {
    if (window.__bqDessin) return;
    if (e.target.tagName === 'INPUT') { if (e.key === 'Enter' && !e.target.closest('.bq-reglages')) { e.preventDefault(); envoyer(false); } return; }
    if (e.target.closest && e.target.closest('.bq-reglages') && e.key !== 'Escape') return;     // (27/11) le panneau des réglages garde ses touches
    const k = e.key.toLowerCase(), l = dansOnglet(slot), i = l.indexOf(sel);
    if (k === 'w') tourner(-1); else if (k === 'c') tourner(1);
    else if ((k === 'arrowdown' || k === 'arrowup') && l.length) { e.preventDefault(); sel = memo = l[(i + (k === 'arrowdown' ? 1 : -1) + l.length) % l.length]; dessiner(); }
    else return;
  };
  f.oncancel = e => { if (window.__bqDessin) e.preventDefault(); };      // Esc pendant le dessin : ne ferme pas la boutique
  f.onclose = () => { if (window.__bqDessin) atDessinFermer(); };
  dessiner();
  if (!f.open) f.showModal();
}
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
            <button data-cote="10" title="Domicile">Dom.</button><button data-cote="20" title="Extérieur">Ext.</button></div>
          <div class="tc-maillot-choix tc-peau-choix"><span>Peau des bras et des jambes</span><input type="color" class="tc-peau">
            <button class="tc-peau-tete" title="La couleur de la peau du visage recoloré">Comme la tête</button>
            <button class="tc-peau-orig" title="La couleur de peau du personnage d'origine">Original</button>
            <button class="tc-peau-ok" title="Écrite dans le mod de la copie (skin_color)">Garder</button><span class="tc-peau-etat"></span></div></div>
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
    const tension = (F && F[1] ? `<div class="tc-tension"><span>TENSION</span><i style="--t:${Math.min(1, F[1] / 150)}"></i><b>${F[1]}<small>T</small></b></div>` : '') + (F && (F[4] || +F[5]) ? `<div class="tc-recharge">${F[4] ? `<span title="Recharge">⟳ ${F[4]} s</span>` : ''}${+F[5] ? `<span class="tc-evol" title="${echapper(nomEvol(F[5]))}">${marquesEvol(F[5], 18)}</span>` : ''}</div>` : '');   // (25/11) + recharge et marques d'évolution (danifdez)
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
  // (26/11, jayden / WhiteRabbit) peau des bras et des jambes de la copie (chara_model skin_color) : vue en direct, « Garder » l'écrit
  { const ip = f.querySelector('.tc-peau'), et = f.querySelector('.tc-peau-etat'), voir = v => { TC.peau = v; if (TC.vue) poserPeau(TC.vue, r.base, c.cle, v); };
    TC.peau = null; TC.peauOrig = null; et.textContent = '';
    api('/api/peau_perso?cle=' + encodeURIComponent(c.cle)).then(q => { if (!q.ok) return; TC.peauOrig = q.origine; ip.value = q.copie || q.origine || '#F0CFB0';
      et.textContent = q.copie ? '' : 'celle de l’original'; }).catch(() => {});
    ip.oninput = () => { voir(ip.value); et.textContent = 'pas encore gardée'; };
    f.querySelector('.tc-peau-orig').onclick = () => { if (TC.peauOrig) { ip.value = TC.peauOrig; voir(ip.value); et.textContent = 'pas encore gardée'; } };
    f.querySelector('.tc-peau-tete').onclick = async () => { const v = TC.visage ? await peauVisage(TC.visage) : null;
      if (v) { ip.value = v; voir(v); et.textContent = 'pas encore gardée'; } else et.textContent = 'tête non recolorée'; };
    f.querySelector('.tc-peau-ok').onclick = async () => { const q = await api('/api/peau_copie', { cle: c.cle, peau: ip.value.toUpperCase() === (TC.peauOrig || '').toUpperCase() ? '' : ip.value });
      if (!q.ok) { et.textContent = q.erreur; return; } et.textContent = 'gardée'; majRapport(q.rapport.join('\n'));
      $('hub-etat').textContent = 'Enregistré. Pour le mettre dans le jeu : « Installer » sur sa carte dans Mes créations.'; chargerHub(); }; }
  apercuJoueur(r, c.cle, f);
}
async function peauVisage(v) {      // (26/11) { o: url de l'atlas du visage d'origine, c: url de celui de la copie } -> '#RRGGBB'
  const lire = async u => { const im = await chargerImage(u), cv = document.createElement('canvas'); cv.width = im.width; cv.height = im.height;
    const cx = cv.getContext('2d'); cx.drawImage(im, 0, 0); return cx.getImageData(0, 0, im.width, im.height); };
  try { const o = await lire(v.o), c = v.c ? await lire(v.c) : null; if (c && (c.width !== o.width || c.height !== o.height)) return null;
    const p = peauDeTete(o, c); return p && p.change ? p.couleur : null; } catch (e) { return null; }   // visage non recoloré : « tête non recolorée »
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
      if (m.masque) { try { await tex('peau:' + m.masque, '/tex/' + m.masque + '.png'); v.masqueCle = 'peau:' + m.masque; } catch (e) { /* sans masque */ } }   // (26/11) peau du corps
    }
    await poserPeau(V, r.base, cle, TC.peau);
    { const mv = meta.find(m => m.texture && r.tete && m.texture.split('/').pop() === r.tete + '_10');     // atlas du visage (« Comme la tête »)
      TC.visage = mv ? { o: '/tex/' + mv.texture + '.png', c: copie[r.tete + '_10'] || null } : null; }
    // pose : un clip des mouvements de sa corpulence, en boucle (la tête n'est mise sur le cou que par l'animation)
    try { const P = await api('/api/pose_joueur?code=' + encodeURIComponent(r.base) + '&paquet=' + TC_POSE.paquet + '&clip=' + TC_POSE.clip);
      if (P.ok) { const sq = new Squelette(P.os, P), inv = sq.mondeRepos.map(Anim3D.inverse), c0 = P.clip, n = Math.max(1, c0.fin - c0.debut);
        V.lecteur = { d: {}, duree: n, calculer(f) { const m = sq.poser(c0, c0.debut + (f % n)); return { peaux: { joueur: m.map((w, b) => Anim3D.mul(w, inv[b])) }, objets: {} }; } };
        V.image = 0; V.joue = true; V.boucle = true; } } catch (e) { /* pose de liaison */ }
    V.recadrer(); V.dist *= 0.95; V.yaw = TC_POSE.yaw; V.pitch = 0.05;
    msg.textContent = r.vetement ? 'Aperçu : le joueur d’origine (la tenue recolorée n’est pas montrée ici)' : Object.keys(copie).length ? '' : 'Aperçu : couleurs d’origine';
  } catch (e) { msg.textContent = 'Aperçu indisponible : ' + e.message; }
}

// (26/11, jayden / WhiteRabbit : « la peau des bras et des jambes ne va pas avec la tête ») couleur de peau du corps dans la vue :
// celle de la copie, sinon celle de l'original (chara_model col. 16, LU) ; « couleur » = réglage en cours ('#RRGGBB')
async function poserPeau(V, base, cle, couleur) {
  let c = couleur;
  if (!c) { try { const q = await api('/api/peau_perso?cle=' + encodeURIComponent(cle || '') + '&code=' + encodeURIComponent(base || ''));
    c = q.ok ? (q.copie || q.origine) : null; } catch (e) { /* serveur ancien */ } }
  const x = /^#?([0-9a-f]{6})$/i.exec(c || ''), n = x ? parseInt(x[1], 16) : 0;
  V.peaux = x ? { joueur: [(n >> 16 & 255) / 255, (n >> 8 & 255) / 255, (n & 255) / 255] } : null;
  return x ? '#' + x[1].toUpperCase() : null;
}

// (26/11, muku : « ajoute les joueurs habillés ») BOUTIQUE, maillot : comme le jeu (capture de muku, onglet Maillots), quatre
// joueurs qui portent le maillot, deux à domicile et deux à l'extérieur, dans la pose du Tableau des compétences ; chacun = le
// joueur du jeu (/api/modele?quoi=joueur, coupe du maillot de base m.code, côté 10 / 20) avec les images du maillot (haut = texture
// « …_20 », short = « …_30 », LU dans les noms des textures du modèle) ; une seule vue, les joueurs décalés en x
// (26/11, muku : « regarde mieux mes photos ») comme la capture : domicile = un joueur de champ + un GARDIEN, extérieur pareil ; le
// maillot du gardien est celui du jeu (uniform_config m_UniformModelInfoList : uniformKeeperModelIdCrc, ex. u080101 -> u080151,
// serveur : /api/maillot_gardien) ; nos maillots ne changent que celui des joueurs de champ ; bras le long du corps (BQ_POSE)
const BQ_JOUEURS = [['c01000100', '10', false], ['c01000010', '10', true], ['c01000020', '20', false], ['c01000300', '20', true]];   // Axel Blaze, Mark Evans (gardien), Nathan Swift, Jude Sharp (gardien)
const BQ_POSE = { paquet: 'p010', clip: 4, tourne: 0.35 };   // tourne : chacun pivoté de face (comme la capture)   // debout, bras le long du corps (comme la boutique ; clip 0 = pose en T, 2 = mains sur les hanches)
async function joueursMaillot(cv, msg, m) {
  if (!cv || typeof Vue3D === 'undefined' || !m || !m.code) return;
  msg.textContent = 'Chargement des joueurs…';
  try {
    const V = cv.__vue || (cv.__vue = new Vue3D(cv)); V.cameraJeu = false; V.vider(); V.lecteur = null;
    const im = m.images || {}, poses = {};
    let gardien = null; try { const g = await api('/api/maillot_gardien?code=' + encodeURIComponent(m.code)); gardien = g.ok ? g.gardien : null; } catch (e) { /* sans gardien */ }
    const tex = async (cleT, url) => { if (V.textures[cleT]) return; const i_ = await chargerImage(url); const t = document.createElement('canvas');
      t.width = i_.width; t.height = i_.height; t.getContext('2d').drawImage(i_, 0, 0); V.texture(cleT, t); };
    const ecart = 1.04;                                  // distance entre deux joueurs (unités du jeu ; capture : 213 px)
    for (const [k, [code, cote, garde]] of BQ_JOUEURS.entries()) {
      const acteur = 'bq' + k, mien = garde && gardien ? {} : { '20': im[cote === '10' ? 'haut_dom' : 'haut_ext'], '30': im[cote === '10' ? 'short_dom' : 'short_ext'] };
      const buf = await api('/api/modele?quoi=joueur&code=' + code + '&maillot=' + encodeURIComponent(garde && gardien ? gardien : m.code) + '&cote=' + cote);
      const dv = new DataView(buf), lg = dv.getUint32(0, true), meta = JSON.parse(new TextDecoder().decode(new Uint8Array(buf, 4, lg))); let p = 4 + lg;
      for (const [i, x] of meta.entries()) {
        const pos = new Float32Array(buf.slice(p, p + x.nv * 12)); p += x.nv * 12;
        const normales = new Float32Array(buf.slice(p, p + x.nv * 12)); p += x.nv * 12;
        const uv = new Float32Array(buf.slice(p, p + x.nv * 8)); p += x.nv * 8;
        const os = new Uint16Array(buf.slice(p, p + x.nv * 8)); p += x.nv * 8;
        const poids = new Float32Array(buf.slice(p, p + x.nv * 16)); p += x.nv * 16;
        const idx = new Uint16Array(buf.slice(p, p + x.ni * 2)); p += x.ni * 2 + ((4 - (x.ni * 2) % 4) % 4);
        const v = V.ajouterPeau(acteur + '/' + i, { nv: x.nv, ni: x.ni, pos, uv, os, poids, idx, normales, contour: x.contour, ombreCle: x.ombre ? 'peau:' + x.ombre : null, noir: x.noir }, acteur);
        if (x.ombre) { try { await tex('peau:' + x.ombre, '/tex/' + x.ombre + '.png'); } catch (e) { /* sans carte d'ombres */ } }
        // (26/11, muku : « les cheveux prennent la couleur du maillot ») la tête a aussi des textures « …_20 » : seulement u<n>_20 / _30
        if (x.texture) { const suf = (/(?:^|\/)u\d{6}_(20|30)$/.exec(x.texture) || [])[1], url = (suf && mien[suf]) || '/tex/' + x.texture + '.png', cleT = 'peau:' + x.texture + (suf && mien[suf] ? ':' + m.id + cote : '');
          try { await tex(cleT, url); v.texCle = cleT; } catch (e) { /* sans texture */ } }
        if (x.masque) { try { await tex('peau:' + x.masque, '/tex/' + x.masque + '.png'); v.masqueCle = 'peau:' + x.masque; } catch (e) { /* sans masque */ } }
      }
      try { const P = await api('/api/pose_joueur?code=' + code + '&paquet=' + BQ_POSE.paquet + '&clip=' + BQ_POSE.clip);
        if (P.ok) { const sq = new Squelette(P.os, P); poses[acteur] = { sq, inv: sq.mondeRepos.map(Anim3D.inverse), clip: P.clip, dx: (k - 1.5) * ecart }; } } catch (e) { /* pose de liaison */ }
    }
    V.lecteur = { d: {}, duree: 1000, calculer(f) { const peaux = {};
      for (const [a_, q] of Object.entries(poses)) { const n = Math.max(1, q.clip.fin - q.clip.debut), co = Math.cos(BQ_POSE.tourne || 0), si = Math.sin(BQ_POSE.tourne || 0), T = new Float32Array([co, 0, -si, 0, 0, 1, 0, 0, si, 0, co, 0, q.dx, 0, 0, 1]);   // chacun tourné sur lui-même
        peaux[a_] = q.sq.poser(q.clip, q.clip.debut + (f % n)).map((w, b) => Anim3D.mul(T, Anim3D.mul(w, q.inv[b]))); }
      return { peaux, objets: {} }; } };
    V.image = 0; V.joue = true; V.boucle = true;
    // cadrage fixe (MESURÉ sur la capture de muku : têtes vers 40 % de la hauteur de l'écran, pieds vers 73 %)
    V.recadrer(); V.centre = [0, 0.8, 0]; V.dist = 2.72;   // (26/11) mesuré sur la capture : joueurs de y ≈ 425 à 795, centres x ≈ 1100 / 1310 / 1530 / 1740
    V.yaw = TC_POSE.yaw; V.pitch = 0.05; Vue3D.activite = performance.now();
    msg.textContent = '';
  } catch (e) { msg.textContent = 'Aperçu indisponible : ' + e.message; }
}

// (27/11, muku : « fais aussi les tenues en 3D comme sur le jeu ») BOUTIQUE, tenue : comme l'onglet Tenues de la boutique du jeu,
// le MANNEQUIN (tête grise c21000010) qui porte la tenue avec SA texture (/api/modele code « tenue:<copie> », serveur
// modele_binaire), debout comme les joueurs des maillots (BQ_POSE), seul et au centre ; squelette du corps normal (pose sans code)
async function tenue3D(cv, msg, cleTenue) {
  if (!cv || typeof Vue3D === 'undefined') return;
  msg.textContent = 'Chargement de la tenue…';
  try {
    const V = cv.__vue || (cv.__vue = new Vue3D(cv)); V.cameraJeu = false; V.vider(); V.lecteur = null;
    const tex = async (cleT, url) => { if (V.textures[cleT]) return; const i_ = await chargerImage(url); const t = document.createElement('canvas');
      t.width = i_.width; t.height = i_.height; t.getContext('2d').drawImage(i_, 0, 0); V.texture(cleT, t); };
    const buf = await api('/api/modele?quoi=joueur&code=' + encodeURIComponent('tenue:' + cleTenue));
    const dv = new DataView(buf), lg = dv.getUint32(0, true), meta = JSON.parse(new TextDecoder().decode(new Uint8Array(buf, 4, lg))); let p = 4 + lg;
    for (const [i, x] of meta.entries()) {
      const pos = new Float32Array(buf.slice(p, p + x.nv * 12)); p += x.nv * 12;
      const normales = new Float32Array(buf.slice(p, p + x.nv * 12)); p += x.nv * 12;
      const uv = new Float32Array(buf.slice(p, p + x.nv * 8)); p += x.nv * 8;
      const os = new Uint16Array(buf.slice(p, p + x.nv * 8)); p += x.nv * 8;
      const poids = new Float32Array(buf.slice(p, p + x.nv * 16)); p += x.nv * 16;
      const idx = new Uint16Array(buf.slice(p, p + x.ni * 2)); p += x.ni * 2 + ((4 - (x.ni * 2) % 4) % 4);
      const v = V.ajouterPeau('tn/' + i, { nv: x.nv, ni: x.ni, pos, uv, os, poids, idx, normales, contour: x.contour, ombreCle: x.ombre ? 'peau:' + x.ombre : null, noir: x.noir }, 'tn');
      if (x.ombre) { try { await tex('peau:' + x.ombre, '/tex/' + x.ombre + '.png'); } catch (e) { /* sans carte d'ombres */ } }
      if (x.texture) { try { await tex('peau:' + x.texture, '/tex/' + x.texture + '.png'); v.texCle = 'peau:' + x.texture; } catch (e) { /* sans texture */ } }
      if (x.masque) { try { await tex('peau:' + x.masque, '/tex/' + x.masque + '.png'); v.masqueCle = 'peau:' + x.masque; } catch (e) { /* sans masque */ } }
    }
    let pose = null;
    try { const P = await api('/api/pose_joueur?code=&paquet=' + BQ_POSE.paquet + '&clip=' + BQ_POSE.clip);
      if (P.ok) { const sq = new Squelette(P.os, P); pose = { sq, inv: sq.mondeRepos.map(Anim3D.inverse), clip: P.clip }; } } catch (e) { /* pose de liaison */ }
    V.lecteur = { d: {}, duree: 1000, calculer(f) { const peaux = {};
      if (pose) { const n = Math.max(1, pose.clip.fin - pose.clip.debut), co = Math.cos(BQ_POSE.tourne || 0), si = Math.sin(BQ_POSE.tourne || 0),
        T = new Float32Array([co, 0, -si, 0, 0, 1, 0, 0, si, 0, co, 0, 0, 0, 0, 1]);
        peaux.tn = pose.sq.poser(pose.clip, pose.clip.debut + (f % n)).map((w, b) => Anim3D.mul(T, Anim3D.mul(w, pose.inv[b]))); }
      return { peaux, objets: {} }; } };
    V.image = 0; V.joue = true; V.boucle = true;
    // cadrage MESURÉ sur la capture de muku (onglet Tenues) : mannequin de y ≈ 400 à 800, au milieu de la vue
    V.recadrer(); V.centre = [0, 0.82, 0]; V.dist = 2.15; V.yaw = TC_POSE.yaw; V.pitch = 0.05; Vue3D.activite = performance.now();
    msg.textContent = '';
  } catch (e) { msg.textContent = 'Aperçu indisponible : ' + e.message; }
}

// (27/11, initiative) ICÔNE AUTOMATIQUE d'une tenue : comme les icônes de tenue de la boutique du jeu (la tenue en croix), le
// mannequin qui porte TA tenue, au repos (bras en croix = pose de liaison), de face, sans la tête, fond transparent, 256 × 256
// (avant, sans icône dessinée : la texture réduite, illisible)
async function bqIconeTenueAuto(cleTenue) {
  let cv = window.__bqVueIcone;
  if (!cv) { cv = window.__bqVueIcone = document.createElement('canvas'); cv.width = cv.height = 512;
    cv.style.cssText = 'position:fixed;left:-9999px;top:0;width:512px;height:512px'; document.body.appendChild(cv); }
  const V = cv.__vue || (cv.__vue = new Vue3D(cv)); V.cameraJeu = false; V.vider(); V.lecteur = null;
  const tex = async (cleT, url) => { if (V.textures[cleT]) return; const i_ = await chargerImage(url); const t = document.createElement('canvas');
    t.width = i_.width; t.height = i_.height; t.getContext('2d').drawImage(i_, 0, 0); V.texture(cleT, t); };
  const buf = await api('/api/modele?quoi=joueur&code=' + encodeURIComponent('tenue:' + cleTenue));
  const dv = new DataView(buf), lg = dv.getUint32(0, true), meta = JSON.parse(new TextDecoder().decode(new Uint8Array(buf, 4, lg))); let p = 4 + lg;
  for (const [i, x] of meta.entries()) {
    const pos = new Float32Array(buf.slice(p, p + x.nv * 12)); p += x.nv * 12;
    const normales = new Float32Array(buf.slice(p, p + x.nv * 12)); p += x.nv * 12;
    const uv = new Float32Array(buf.slice(p, p + x.nv * 8)); p += x.nv * 8;
    const os = new Uint16Array(buf.slice(p, p + x.nv * 8)); p += x.nv * 8;
    const poids = new Float32Array(buf.slice(p, p + x.nv * 16)); p += x.nv * 16;
    const idx = new Uint16Array(buf.slice(p, p + x.ni * 2)); p += x.ni * 2 + ((4 - (x.ni * 2) % 4) % 4);
    if (x.texture && /c21000010_/.test(x.texture)) continue;            // pas la tête du mannequin
    const v = V.ajouterPeau('ti/' + i, { nv: x.nv, ni: x.ni, pos, uv, os, poids, idx, normales, contour: x.contour, ombreCle: x.ombre ? 'peau:' + x.ombre : null, noir: x.noir }, 'ti');
    if (x.ombre) { try { await tex('peau:' + x.ombre, '/tex/' + x.ombre + '.png'); } catch (e) { /* sans carte d'ombres */ } }
    if (x.texture) { try { await tex('peau:' + x.texture, '/tex/' + x.texture + '.png'); v.texCle = 'peau:' + x.texture; } catch (e) { /* sans texture */ } }
    if (x.masque) { try { await tex('peau:' + x.masque, '/tex/' + x.masque + '.png'); v.masqueCle = 'peau:' + x.masque; } catch (e) { /* sans masque */ } }
  }
  V.recadrer(true); V.dist *= 0.9; V.yaw = 0; V.pitch = 0.05;
  V._dessinerUne(0);
  const lu = document.createElement('canvas'); lu.width = lu.height = 512; const g_ = lu.getContext('2d'); g_.drawImage(cv, 0, 0);
  const d = g_.getImageData(0, 0, 512, 512).data; let x0 = 512, y0 = 512, x1 = -1, y1 = -1;
  for (let y = 0; y < 512; y++) for (let x = 0; x < 512; x++) if (d[(y * 512 + x) * 4 + 3] > 20) { if (x < x0) x0 = x; if (x > x1) x1 = x; if (y < y0) y0 = y; if (y > y1) y1 = y; }
  if (x1 < 0) throw new Error('rendu vide');
  const out = document.createElement('canvas'); out.width = out.height = 256; const c = Math.max(x1 - x0, y1 - y0) * 1.08;
  out.getContext('2d').drawImage(lu, (x0 + x1) / 2 - c / 2, (y0 + y1) / 2 - c / 2, c, c, 0, 0, 256, 256);
  return out.toDataURL('image/png');
}

// (23/11) joueur en 3D au centre de l'écran des stats (comme le jeu) : même chargement qu'apercuJoueur, sur SA propre vue
// (la vue du Tableau des compétences n'est pas prise).
async function joueur3D(cv, msg, base, cle) {
  if (!cv || typeof Vue3D === 'undefined' || !base) return;
  msg.textContent = 'Chargement du joueur…';
  try {
    const V = cv.__vue || (cv.__vue = new Vue3D(cv)); V.cameraJeu = false; V.vider(); V.lecteur = null;
    const [buf, copie] = await Promise.all([api('/api/modele?quoi=joueur&code=' + encodeURIComponent(base)),
      cle ? api('/api/copie_textures?cle=' + encodeURIComponent(cle)).catch(() => ({})) : Promise.resolve({})]);
    const dv = new DataView(buf), lg = dv.getUint32(0, true), meta = JSON.parse(new TextDecoder().decode(new Uint8Array(buf, 4, lg))); let p = 4 + lg;
    const tex = async (cleT, url) => { if (V.textures[cleT]) return; const im = await chargerImage(url); const t = document.createElement('canvas');
      t.width = im.width; t.height = im.height; t.getContext('2d').drawImage(im, 0, 0); V.texture(cleT, t); };
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
      if (m.masque) { try { await tex('peau:' + m.masque, '/tex/' + m.masque + '.png'); v.masqueCle = 'peau:' + m.masque; } catch (e) { /* sans masque */ } }   // (26/11) peau du corps
    }
    await poserPeau(V, base, cle);
    try { const P = await api('/api/pose_joueur?code=' + encodeURIComponent(base) + '&paquet=' + TC_POSE.paquet + '&clip=' + TC_POSE.clip);
      if (P.ok) { const sq = new Squelette(P.os, P), inv = sq.mondeRepos.map(Anim3D.inverse), c0 = P.clip, n = Math.max(1, c0.fin - c0.debut);
        V.lecteur = { d: {}, duree: n, calculer(f) { const m = sq.poser(c0, c0.debut + (f % n)); return { peaux: { joueur: m.map((w, b) => Anim3D.mul(w, inv[b])) }, objets: {} }; } };
        V.image = 0; V.joue = true; V.boucle = true; } } catch (e) { /* pose de liaison */ }
    V.recadrer(); V.dist *= 0.95; V.yaw = TC_POSE.yaw; V.pitch = 0.05;
    msg.textContent = '';
  } catch (e) { msg.textContent = 'Aperçu indisponible : ' + e.message; }
}

// (23/11, demande de muku) APERÇU d'une technique créée dans « En attente de stats / cosmétique » : son projet est rouvert
// dans l'éditeur (comme « Modifier » : tes couleurs), puis la zone de la vue 3D (#centre : vue, barre de lecture, ▶ lecteur
// natif) est posée dans la fenêtre ; à la fermeture elle revient à sa place et on retourne à Mes créations.
// (23/11, demande de muku : « la preview des Keshin = l'animation d'invocation en match ») le LECTEUR DU JEU joue
// « invoc_<copie> » (serveur : technique_invocation, scène d'invocation de la sortie MesEsprits, la copie à la place de
// l'esprit), posé sur la zone de l'aperçu (NATIF.hote) ; il boucle tout seul. Arrêté à la fermeture de la fenêtre.
async function apercuInvocation(hote, msg, code, f, choix) {
  NATIF.hote = hote; finNatif(true);
  msg.textContent = 'Chargement de l’invocation (la 1re fois : jusqu’à une minute)…'; msg.classList.add('bas');
  const numero = NATIF.numero = (NATIF.numero || 0) + 1; NATIF.lance = true;
  const arreter = () => { if (NATIF.hote === hote) NATIF.hote = null; finNatif(true); };   // finNatif vise le pid (23/11)
  f.__fin = arreter;
  const rect = rectNatif(); let w = rect[2], h = Math.round(w * 9 / 16); if (h > rect[3]) { h = rect[3]; w = Math.round(h * 16 / 9); }
  w = Math.max(640, Math.min(2560, w)); h = Math.round(w * 9 / 16);
  const jeton = 'L' + Math.random().toString(36).slice(2, 10), titre = document.title.replace(/ · L[a-z0-9]+$/, '');
  document.title = titre + ' · ' + jeton; setTimeout(() => { document.title = titre; }, 4000);
  const tcode = (code.startsWith('armure_') ? code : 'invoc_' + code) + (choix && choix.element ? '~@' + choix.element : choix ? '~' + choix.scene + '~' + choix.esprit : '');
  let r; try { r = await api('/api/natif', { stade: 's10g001', technique: tcode, modifs: {}, caches: [], couleurs: {}, sommets: {}, particules: {},
    largeur: w, hauteur: h, incruste: true, rect, jeton }); } catch (e) { r = { erreur: e.message }; }
  if (NATIF.numero === numero) NATIF.lance = false;
  if (!f.open || NATIF.numero !== numero || NATIF.hote !== hote) { if (r && r.pid) api('/api/natif_cmd', { cmd: 'quitter', pid: r.pid }).catch(() => {}); return; }
  if (!r || r.erreur) { msg.textContent = 'Aperçu indisponible : ' + ((r && r.erreur) || '?'); return; }
  NATIF.actif = true; NATIF.pid = r.pid || null; NATIF.cle = tcode; NATIF.rect = rect.join(' '); NATIF.choixN = undefined; suivreNatif(); msg.textContent = '';
}
function finApercuStats(f) { if (f && f.__fin) { const x = f.__fin; f.__fin = null; x(); } }
async function apercuTechnique(hote, msg, c, f) {
  const centre = $('centre'); if (!centre || !hote) return;
  msg.textContent = 'Chargement de l’aperçu…';
  const deja = E.tech && !E.tech.perso && E.cree && E.cree.mod === c.mod && String(E.cree.code) === String(c.code);
  const ongletAvant = E.onglet;
  if (deja && E.onglet !== 'techniques' && window.changerOnglet) window.changerOnglet('techniques');   // barre de lecture : onglet Techniques
  try { if (!deja) { await modifierCreation(c); for (let k = 0; k < 100 && E.chargement; k++) await new Promise(r => setTimeout(r, 100)); } }
  catch (e) { msg.textContent = 'Aperçu indisponible : ' + e.message; }
  if (!f.open || !hote.isConnected) { if (!f.open && ongletAvant === 'hub' && window.changerOnglet) window.changerOnglet('hub'); return; }   // fermée pendant le chargement
  if (!E.tech || E.tech.perso) { msg.textContent = 'Aperçu indisponible : technique introuvable.'; return; }
  const place = { parent: centre.parentNode, suivant: centre.nextSibling };
  hote.appendChild(centre); centre.classList.add('dans-stats');
  msg.textContent = projetDe(c) ? '' : 'Projet d’origine introuvable : couleurs de la technique de départ.';
  if (E.vue) E.vue.recadrer(true);
  // (23/11, muku : « la preview doit se jouer en boucle et sans paramètre, juste voir la technique ») animation du jeu en
  // boucle dans la vue (caméra du jeu, sans son), réglages de la vue cachés (CSS #centre.dans-stats)
  const avant = { son: $('l-son').checked };
  $('l-son').checked = false; finNatif(true);
  (async () => { for (let k = 0; k < 150 && !E.lecteur && f.open; k++) await new Promise(r => setTimeout(r, 100));
    if (!E.lecteur || !f.open || !centre.classList.contains('dans-stats')) return;
    activerAnimation(true); E.vue.cameraJeu = true; E.vue.boucle = true; E.vue.vitesse = 1; E.vue.image = 0; E.vue.joue = true;
    // (23/11, retour de muku : « problème avec la preview ») l'aperçu WebGL n'a pas les vrais joueurs (silhouettes) : le
    // LECTEUR DU JEU (AtelierNatif, Direct3D, vrais shaders, il boucle tout seul) est lancé dans la zone de l'aperçu
    msg.textContent = 'Chargement du lecteur du jeu…'; msg.classList.add('bas');
    try { await lecteurNatif(); } catch (e) { /* l'aperçu WebGL reste */ }
    if (!f.open || !centre.classList.contains('dans-stats')) { arreterNatifs(); return; }   // fermée pendant le lancement
    if (NATIF.actif) { E.vue.joue = false; msg.textContent = ''; }
    else msg.textContent = 'Lecteur du jeu indisponible : aperçu simplifié.'; })();
  // (23/11, retour de muku : « en fermant le menu la preview est restée ») le lecteur peut tourner alors que l'Atelier le
  // croit fermé (un « etat » sans réponse remet NATIF.actif à faux) : à la fermeture, TOUS les lecteurs sont arrêtés
  const arreterNatifs = () => { finNatif(true); api('/api/natif_cmd', { cmd: 'quitter' }).catch(() => {}); };
  f.__fin = () => {
    arreterNatifs();
    if (E.vue) { E.vue.joue = false; E.vue.boucle = $('l-boucle').checked; E.vue.cameraJeu = $('l-camera').checked; E.vue.vitesse = +$('l-vitesse').value; }
    $('l-son').checked = avant.son;
    centre.classList.remove('dans-stats');
    place.parent.insertBefore(centre, place.suivant && place.suivant.parentNode === place.parent ? place.suivant : null);
    if (E.vue) E.vue.recadrer(true);
    if (ongletAvant === 'hub' && window.changerOnglet) window.changerOnglet('hub');
  };
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
      r = await api('/api/maillot', { action: 'supprimer', id: c.maillot.id || c.code });   // (23/11) l'id, pas l'objet (rien n'était retiré)
      if (r.ok) r = await api('/api/maillot', { action: 'construire' });          // le mod « Mes maillots » refait sans lui
      r = r.ok ? { ok: true, rapport: ['maillot supprimé ; le mod « Mes maillots » est refait sans lui'] } : r;
    } else r = await api('/api/supprimer_creation', { mod: c.mod, code: c.mod === 'MesPersonnages' ? c.cle : c.code, genre: c.genre });
  } catch (e) { r = { ok: false, erreur: e.message }; }
  $('hub-etat').textContent = r.ok ? `« ${c.nom} » supprimé.` : 'Pas supprimé : ' + r.erreur;
  if (r.ok) majRapport(r.rapport.join('\n'));
  chargerHub();
}
function aDesStats(c) { return !c.jeuSeul && (c.mod === 'MesTechniques' || c.mod === 'MesEsprits' || (c.mod === 'MesPersonnages' && c.cle)); }   // (22/11) totems aussi (comme « En attente de stats »)
// (22/11, « fais un beau menu pour les stats ») MENU DES STATS façon menus du jeu, comme le Tableau des compétences :
// en-tête orange + plaque du nom, à gauche la carte et l'aperçu (barre de technique ou d'esprit comme en jeu, PT en jauge
// « TENSION »), à droite les réglages ; joueur : panneau de statistiques d'après references_menus/equipement.webp
// (étiquettes bleues en capitales, barre de couleur par statistique, gros chiffres bleus, pastilles ATT / MIL / DÉF / GAR).
const MS_EL = { wind: 'air', forest: 'foret', fire: 'feu', mountain: 'montagne', void: 'neant' };
const MS_POSTE = { fw: ['ATT', 'Attaquant'], mf: ['MIL', 'Milieu'], df: ['DÉF', 'Défenseur'], gk: ['GAR', 'Gardien'] };
const MS_GENRE = { whs: ['g-tir', 'Tir'], who: ['g-dri', 'Dribble'], whd: ['g-def', 'Défense'], whk: ['g-gar', 'Arrêt'] };
const MS_STAT = { kick: 'frappe', control: 'controle', technique: 'technique', pressure: 'pression', physical: 'physique',
  intelligence: 'intelligence', agility: 'agilite', freedom: 'liberte' };
function iconeNommee(nom, t) {          // (22/11) icône de icon_common par son nom (menus_jeu.ZONES_NOMMEES)
  const P = MJ && MJ.icones_communes, z = P && P.noms && P.noms[nom];
  if (!z) return '';
  const k = t / Math.max(z[2], z[3]);
  return `<i class="jm-icone ms2-ic" style="width:${Math.round(z[2] * k)}px;height:${Math.round(z[3] * k)}px;background-image:url('${P.url}');`
    + `background-size:${P.w * k}px ${P.h * k}px;background-position:${-z[0] * k}px ${-z[1] * k}px"></i>`;
}
const MS_EL_IC = { fire: 'feu', forest: 'foret', wind: 'vent' };
// (23/11, muku : « void n'a pas d'image ») TUILES D'ÉLÉMENT DU JEU : gaiji_cmd_type01-04 (dx11/font/gaiji_game) ; Néant =
// gaiji_cmd_type00, fabriquée par BetterQoL (content/images/font/gaiji_game.toml, cache de VRFW) et reprise par CharacterReforged
// (element_icon). Sans l'image (autre installation), le carré de couleur reste dessous.
const EL_GAIJI = { wind: '01', forest: '02', fire: '03', mountain: '04', void: '00' };
function elIcone(e, t) {
  if (EL_GAIJI[e]) return `<span class="ms2-carre el-${MS_EL[e] || 'neutre'} ms2-gaiji" style="width:${t}px;height:${t}px;background-image:url('/ui_jeu/zone/gaiji_game/gaiji_cmd_type${EL_GAIJI[e]}.png')"></span>`;
  return elIconeAncienne(e, t);
}
function elIconeAncienne(e, t) {        // carré d'élément du jeu ; montagne : son carré brun est redessiné (alpha nul dans la planche)
  if (e === 'mountain') return `<span class="ms2-carre mont" style="width:${t}px;height:${t}px">${iconeNommee('montagne', t * .8)}</span>`;
  const ic = MS_EL_IC[e] ? iconeNommee(MS_EL_IC[e], t) : '';
  return ic || `<span class="ms2-carre el-${MS_EL[e] || 'neutre'}" style="width:${t}px;height:${t}px"></span>`;
}
async function ouvrirStats(c) {
  const code = c.mod === 'MesPersonnages' ? c.cle : c.code;
  let f = $('menu-stats');
  if (!f) {
    f = document.createElement('dialog'); f.id = 'menu-stats'; document.body.appendChild(f);
    f.addEventListener('close', () => { if (!f.open) finApercuStats(f); if (typeof majCacheNatif === 'function') majCacheNatif(); });
    f.addEventListener('cancel', () => finApercuStats(f));     // (23/11) Échap : aperçu remis tout de suite (« close » arrive tard)
  }
  finApercuStats(f); f.classList.remove('ms-tech-mode'); f.onkeydown = null; f.__invocation = null; f.__effets = null; f.__coups = null; f.classList.remove('msp-mode');
  const tag = c.genre === 'totem' ? 'TOT' : c.genre === 'armures' ? 'ARM' : { MesTechniques: 'TECH', MesEsprits: 'ESP', MesPersonnages: 'PERSO' }[c.mod] || '';
  const motEsprit = c.genre === 'totem' ? 'TOTEM' : c.genre === 'armures' ? 'ARMURE' : 'ESPRIT';     // (23/11) + armures                // (22/11) les totems ne sont pas des esprits
  f.innerHTML = `<div class="tc-entete"><div class="jm-coin tc-coin">${iconeJeu('m2', 46)}<span>Stats</span></div>
      <div class="tc-plaque"><span class="tc-plaque-nom"></span><span class="tc-plaque-sous">Lecture…</span><span class="jm-tag tc-plaque-tag">${tag}</span></div>
      <button class="tc-fermer" title="Fermer sans rien changer (Échap)">✕</button></div>
    <div class="ms-corps"><div class="ms-gauche"></div><div class="ms-droite"></div></div>
    <div class="tc-aide"><span><i class="jm-touche">Échap</i> Fermer</span><span class="ms-aide-txt"></span>
      <button class="ms-original">Garder celles de l'original</button><button class="tc-enregistrer ms-garder">Enregistrer</button></div>`;
  f.querySelector('.tc-plaque-nom').textContent = c.nom;
  f.querySelector('.tc-fermer').onclick = () => { finApercuStats(f); f.close(); };
  if (!f.open) f.showModal();
  if (typeof majCacheNatif === 'function') majCacheNatif();
  let G = f.querySelector('.ms-gauche'), D = f.querySelector('.ms-droite');
  let r; try { r = await api('/api/stats?mod=' + encodeURIComponent(c.mod) + '&code=' + encodeURIComponent(code) + '&langue=' + encodeURIComponent(window.ATELIER_LANGUE || 'fr')); } catch (e) { D.textContent = e.message; return; }
  if (!r.ok) { D.textContent = r.erreur; return; }

  const jeu = r.jeu || {}, deja = r.stats || {}, champ = k => r.champs.find(x => x.cle === k);
  // valeurs de travail : réglées avant, sinon celles de l'original (joueur : vide = comme l'original)
  const V = {};
  const joueur = r.genre === 'personnages';
  for (const ch of r.champs) { const k = ch.cle, d = k.startsWith('stats.') ? (deja.stats || {})[k.slice(6)] : deja[k];
    V[k] = d !== undefined ? d : (jeu[k] !== undefined && (!joueur || k.startsWith('stats.')) ? jeu[k] : ''); }
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
    if (r.genre === 'technique' && f.querySelector('.msj-tech')) {
      // (23/11, demande de muku : « copie cette UI ») plaque du nom + fiche blanche du Tableau des compétences du jeu
      const g = MS_GENRE[(c.code || '').slice(0, 3)] || ['', ''], P = f.querySelector('.msj-tech .msj-plaque');
      P.innerHTML = `<i class="msj-rayures"></i><span class="msj-nom-j">${echapper(c.nom)}</span>${V.element ? elIcone(V.element, 30) : ''}
        <span class="msj-genre">${echapper(g[1].toUpperCase())}</span><span class="msj-pt"><small>PT</small>${V.tp !== '' ? V.tp : '—'}</span>`;
      G.innerHTML = `<div class="msj-fiche-tete"><span class="tc-orbe ${g[0]}"></span><span>${echapper(g[1])}</span><small>Comme en jeu</small></div>
        <div class="msj-fiche-ligne"><div class="tc-barre el-${el} ms-apercu"><span class="tc-orbe ${g[0]}"></span><span class="tc-nom">${echapper(c.nom)}</span><span class="tc-pw"><small>${g[1].toUpperCase()}</small>${pmax}</span></div>
          <div class="tc-tension" style="--t:${Math.min(1, (+V.tp || 0) / 150)}"><span>TENSION</span><i></i><b>${V.tp !== '' ? V.tp : '—'}<small>T</small></b></div></div>
        <div class="msj-fiche-puces"><span class="msj-ia">${V.users > 1 ? V.users + ' joueurs' : 'Solo'}</span>
          <span class="tc-puce el-${el} ms2-puce">${elIcone(V.element, 22)}${echapper(libEl(V.element) || 'Élément')}</span><span class="tc-niv"><span>Niv. 1</span>${V.power_min}</span>
          ${jeu.power_max !== undefined ? `<span class="msj-orig"><small>Original</small><span class="tc-barre petit el-${MS_EL[jeu.element] || 'neutre'}"><span class="tc-orbe ${g[0]}"></span><span class="tc-nom">${echapper(nomBase)}</span><span class="tc-pw"><small>${g[1].toUpperCase()}</small>${jeu.power_max}</span></span></span>` : ''}</div>`;
      return;
    }
    if (r.genre === 'technique') {
      const g = MS_GENRE[(c.code || '').slice(0, 3)] || ['', ''];
      h += `<div class="ms-titre">Comme en jeu</div>
        <div class="tc-barre el-${el} ms-apercu"><span class="tc-orbe ${g[0]}"></span><span class="tc-nom">${echapper(c.nom)}</span><span class="tc-pw"><small>${g[1].toUpperCase()}</small>${pmax}</span></div>
        <div class="tc-tension" style="--t:${Math.min(1, (+V.tp || 0) / 150)}"><span>TENSION</span><i></i><b>${V.tp !== '' ? V.tp : '—'}<small>T</small></b></div>
        <div class="ms-infos"><span class="tc-puce el-${el} ms2-puce">${elIcone(V.element, 22)}${echapper(libEl(V.element) || 'Élément')}</span><span class="tc-niv"><span>Niv. 1</span>${V.power_min}</span>
          <span class="tc-puce">${V.users > 1 ? V.users + ' joueurs' : 'Solo'}</span></div>`;
      if (jeu.power_max !== undefined) h += `<div class="ms-titre">Original</div><div class="tc-barre petit el-${MS_EL[jeu.element] || 'neutre'}"><span class="tc-orbe ${g[0]}"></span><span class="tc-nom">${echapper(nomBase)}</span><span class="tc-pw"><small>${g[1].toUpperCase()}</small>${jeu.power_max}</span></div>`;
    } else if (r.genre === 'esprit') {
      h += `<div class="ms-titre">Comme en jeu</div>
        <div class="tc-barre esprit ms-apercu"><span class="tc-nom">${echapper(c.nom)}</span><span class="tc-pw"><small>${motEsprit}</small>${pmax}</span></div>
        <div class="ms-infos"><span class="tc-puce el-${el} ms2-puce">${elIcone(V.element, 22)}${echapper(libEl(V.element) || 'Élément')}</span><span class="tc-niv"><span>Niv. 1</span>${V.power_min}</span></div>`;
      if (jeu.power_max !== undefined) h += `<div class="ms-titre">Original</div><div class="tc-barre petit esprit"><span class="tc-nom">${echapper(nomBase)}</span><span class="tc-pw"><small>${motEsprit}</small>${jeu.power_max}</span></div>`;
    } else {
      const pos = V.position || jeu.position, sub = V.sub_position || jeu.sub_position, ele = V.element || jeu.element;   // (22/11) vide = l'original
      const p = pos ? MS_POSTE[pos] : null, el2 = ele ? MS_EL[ele] : '';
      h += `<div class="ms-titre">Comme en jeu</div><div class="ms-joueur-tags">
        ${p ? `<span class="ms-poste p-${pos}">${p[0]}</span>` : '<span class="ms-poste vide">poste d’origine</span>'}
        ${sub && MS_POSTE[sub] ? `<span class="ms-poste petit p-${sub}">${MS_POSTE[sub][0]}</span>` : ''}
        ${el2 ? `<span class="tc-puce el-${el2} ms2-puce">${elIcone(ele, 22)}${echapper(libEl(ele))}</span>` : '<span class="tc-puce">élément d’origine</span>'}</div>`;
      if (r.source) h += `<p class="ms-note">Original : stats du mod ${echapper(r.source)} (activé), comme en jeu.</p>`;
    }
    G.innerHTML = h;
  };
  // ---- réglages (droite) — (22/11, « fais-moi encore un meilleur menu pour les stats ») façon fiche d'Équipement du jeu
  // (references_menus/equipement.webp) : panneau sombre à alvéoles, noms en capitales bleues, jauge avec l'ORIGINAL en
  // fantôme (ce qui est gagné en vert, perdu encadré de rouge), gros chiffres bleus avec « +25 / −10 » au-dessus, boutons
  // − / + (Maj : 10), ↺ par ligne ; en haut, les cases des changements comme le jeu (« −10 +25 +43 ») ; éléments avec les
  // icônes du jeu (icon_common, menus_jeu.ZONES_NOMMEES).
  const nombre = k => (champ(k) || {}).type === 'nombre';
  const libChoix = (k, v) => { const ch = champ(k) || {}; const x = (ch.choix || []).find(y => String(y[0]) === String(v));
    return x ? x[1] : (k === 'position' || k === 'sub_position') && MS_POSTE[v] ? MS_POSTE[v][0] : String(v); };
  const NOMS_COURTS = { power_min: 'Puiss. niv. 1', power_max: 'Puiss. max', tp: 'PT', users: 'Joueurs', element: 'Élément', growth: 'Évolution',
    position: 'Poste', sub_position: '2e poste' };
  const ligneNombre = (k, nom, max) => { const ch = champ(k); if (!ch) return '';
    return `<div class="ms2-ligne" data-k="${k}" data-max="${max}">
      <span class="ms2-nom">${echapper(nom)}</span>
      <div class="ms2-jauge"><i class="b"></i><i class="p"></i><i class="m"></i><b class="o"></b>
        <input type="range" data-k="${k}" min="${ch.min ?? 0}" max="${max}" step="1" value="${V[k] === '' ? 0 : V[k]}"></div>
      <button class="ms2-pas" data-d="-1" title="−1 (Maj : −10)">−</button>
      <span class="ms2-chiffre"><small class="ms2-delta"></small><input type="number" data-k="${k}" min="${ch.min}" max="${ch.max}" value="${V[k]}"></span>
      <button class="ms2-pas" data-d="1" title="+1 (Maj : +10)">+</button>
      <button class="ms2-raz" title="Remettre la valeur de l’original${jeu[k] !== undefined ? ' (' + jeu[k] + ')' : ''}">↺</button></div>`; };
  const ligneChoix = (k, items, vide, cls) => { const ch = champ(k); if (!ch) return '';
    return `<div class="ms2-ligne ms2-l-choix"><span class="ms2-nom">${echapper(ch.nom)}</span><div class="ms-choix ${cls || ''}" data-k="${k}">
      ${vide ? `<button data-v="" class="${V[k] === '' ? 'sel' : ''}">comme l’original</button>` : ''}
      ${items.map(([v, n, cl, ic]) => `<button data-v="${v}" class="${cl || ''}${String(V[k]) === String(v) ? ' sel' : ''}${jeu[k] !== undefined && String(jeu[k]) === String(v) ? ' orig' : ''}">${ic || ''}<span>${echapper(n)}</span></button>`).join('')}</div>
      <button class="ms2-raz" data-raz="${k}" title="Remettre celui de l’original">↺</button></div>`; };
  const elems = (champ('element') || { choix: [] }).choix.map(([v, n]) => [v, n, 'el el-' + MS_EL[v], elIcone(v, 26)]);
  const fond = '<div class="ms2-alveoles"></div>';
  // (23/11, demande de muku) COSMÉTIQUE d'une technique (plus dans « Créer la technique ») : couleur du tir, traînée du
  // ballon (tirs), prix en boutique, bannière ; gardée par le serveur (export.appliquer_cosmetique) avec « Enregistrer »
  const cos0 = r.cosmetique || {}, ban0 = cos0.banniere || {};
  const C = r.genre === 'technique' ? { couleur_tir: cos0.couleur_tir ?? '', prix: cos0.prix ?? '',
    trainee: (cos0.trainee || {}).famille || '', trainee_el: (cos0.trainee || {}).element || 'void',
    ban_texte: ban0.texte || '', ban_c: ban0.couleur || '#f5c842', ban_o: ban0.contour || '#0d1a4a', ban_style: ban0.style || 'jeu' } : null;
  const opts = (L, v) => L.map(([x, n]) => `<option value="${x}"${String(v) === String(x) ? ' selected' : ''}>${echapper(n)}</option>`).join('');
  const blocCosmetique = () => !C ? '' : `<div class="ms-section">Cosmétique</div><div class="ms-cosm">
      <label><span>Couleur du tir</span><select data-c="couleur_tir">${opts([['', "Garder celle d'origine"], [0, 'Montagne'], [1, 'Air'], [2, 'Feu'], [3, 'Forêt'], [4, 'Néant'], [6, 'Esprit (jaune)']], C.couleur_tir)}</select></label>
      ${r.tir ? `<label><span>Traînée du ballon (tirs)</span><span class="ms-cosm-2"><select data-c="trainee">${opts([['', 'Celle du jeu'], ['ega0075', 'Tir spécial'], ['ega0080', 'Tir enchaîné'], ['ega0085', 'Tir lointain']], C.trainee)}</select>
        <select data-c="trainee_el"${C.trainee ? '' : ' disabled'}>${opts([['void', 'Néant (violet)'], ['wind', 'Air'], ['fire', 'Feu'], ['forest', 'Forêt'], ['mountain', 'Montagne']], C.trainee_el)}</select></span></label>` : ''}
      <label><span>Prix en boutique (jetons, vide = pas de vente)</span><input type="number" min="1" data-c="prix" value="${C.prix}"></label>
      <label><span>Bannière (texte)</span><input data-c="ban_texte" value="${echapper(C.ban_texte)}" placeholder="${ban0.editeur ? 'bannière de l’éditeur gardée (écris un texte pour la remplacer)' : ban0.garder ? 'bannière actuelle gardée (écris un texte pour la remplacer)' : 'FRAPPE GALACTIQUE'}"></label>
      <div class="ms-cosm-2"><label><span>Lettres</span><input type="color" data-c="ban_c" value="${C.ban_c}"></label><label><span>Contour</span><input type="color" data-c="ban_o" value="${C.ban_o}"></label>
        <button type="button" class="ms-ban-perso" title="Ouvre l'éditeur de bannières avec cette copie choisie">✎ Personnaliser la bannière</button></div></div>`;
  const brancherCosmetique = () => {
    if (!C) return;
    D.querySelectorAll('[data-c]').forEach(el => { el.oninput = el.onchange = () => { C[el.dataset.c] = el.value;
      if (el.dataset.c === 'trainee') { const s = D.querySelector('[data-c="trainee_el"]'); if (s) s.disabled = !el.value; } }; });
    const b = D.querySelector('.ms-ban-perso');
    if (b) b.onclick = () => { B.preselect = c.code; f.close(); window.changerOnglet('bannieres'); };
  };
  const cosmetique = () => !C ? undefined : { couleur_tir: C.couleur_tir === '' ? null : +C.couleur_tir, prix: C.prix === '' ? null : +C.prix,
    trainee: C.trainee ? { famille: C.trainee, element: C.trainee_el } : null, banniere: { texte: C.ban_texte.trim(), couleur: C.ban_c, contour: C.ban_o, style: C.ban_style } };
  const panneau = () => {
    let h = `<div class="tc-detail ms-panneau ms2">${fond}<div class="ms2-deltas"></div>`;
    if (r.genre === 'technique') {
      h += '<div class="ms-section">Puissance</div>' + ligneNombre('power_min', 'Au niveau 1', 1000) + ligneNombre('power_max', 'Au niveau max', 1500)
        + '<div class="ms-section">Utilisation</div>' + ligneNombre('tp', 'Coût en PT (tension)', 150)
        + ligneChoix('users', [[1, 'Solo'], [2, '2 joueurs'], [3, '3 joueurs'], [4, '4 joueurs']])
        + '<div class="ms-section">Nature</div>' + ligneChoix('element', elems, false, 'ms2-els')
        + ligneChoix('growth', [0, 1, 2, 3, 4, 5, 6, 7].map(n => [n, String(n)])) + blocCosmetique();
    } else if (r.genre === 'esprit') {
      h += '<div class="ms-section">Puissance</div>' + ligneNombre('power_min', 'Au niveau 1', 300) + ligneNombre('power_max', 'Au niveau max', 300)
        + '<div class="ms-section">Nature</div>' + ligneChoix('element', elems, false, 'ms2-els');
    } else {
      const postes = Object.entries(MS_POSTE).map(([v, [a, n]]) => [v, a + ' · ' + n, 'poste p-' + v]);
      h += '<div class="ms-section">Poste et élément</div>' + ligneChoix('position', postes, true) + ligneChoix('sub_position', postes, true)
        + ligneChoix('element', elems, true, 'ms2-els')
        + `<div class="ms-section">Statistiques <label class="ms-bascule"><input type="checkbox" class="ms-stats-on"${statsOn ? ' checked' : ''}> les changer</label></div>`
        + `<div class="ms-stats${statsOn ? '' : ' eteint'}">` + Object.entries(MS_STAT).map(([k, cl]) => {
          const ch = champ('stats.' + k), v = V['stats.' + k] === '' ? 200 : V['stats.' + k], o = jeu['stats.' + k];
          return `<div class="ms-stat s-${cl}" data-st="${k}"><span class="ms-stat-nom">${echapper(ch.nom.toUpperCase())}</span>
            <span class="ms-stat-barre"><i style="--v:${Math.min(1, v / 300)}"></i>${o !== undefined ? `<b class="ms2-o" style="--o:${Math.min(1, o / 300)}" title="original : ${o}"></b>` : ''}<small class="ms2-delta"></small><input type="range" data-k="stats.${k}" min="0" max="300" value="${v}"${statsOn ? '' : ' disabled'}></span>
            <input type="number" class="ms-stat-val" data-k="stats.${k}" min="0" max="999" value="${v}"${statsOn ? '' : ' disabled'}></div>`; }).join('')
        + `</div><p class="ms-note">Sans « les changer » : les statistiques de l’original${Object.keys(jeu).some(k => k.startsWith('stats.')) ? ' (trait blanc)' : ''}. Les 8 vont ensemble.</p>`;
    }
    h += '<div class="ms-etat"></div></div>';
    D.innerHTML = h;
    brancherCosmetique();
    const regler = (k, v) => { V[k] = v; D.querySelectorAll(`input[data-k="${k}"]`).forEach(o => { if (+o.value !== +v || o.value === '') o.value = v; }); majTout(); apercu(); };
    D.querySelectorAll('input[data-k]').forEach(el => el.oninput = () => {
      const k = el.dataset.k, v = el.value === '' ? '' : +el.value; V[k] = v;
      D.querySelectorAll(`input[data-k="${k}"]`).forEach(o => { if (o !== el) o.value = v; });
      const bar = el.closest('.ms-stat'); if (bar) bar.querySelector('i').style.setProperty('--v', Math.min(1, (+v || 0) / 300));
      majTout(); apercu(); });
    D.querySelectorAll('.ms2-ligne[data-k]').forEach(L => {
      const k = L.dataset.k, ch = champ(k);
      L.querySelectorAll('.ms2-pas').forEach(b => b.onclick = ev => {
        const v = Math.max(ch.min ?? 0, Math.min(ch.max ?? 9999, (+V[k] || 0) + (+b.dataset.d) * (ev.shiftKey ? 10 : 1)));
        regler(k, v); });
      L.querySelector('.ms2-raz').onclick = () => { if (jeu[k] !== undefined) regler(k, jeu[k]); };
    });
    D.querySelectorAll('.ms-choix').forEach(b => b.querySelectorAll('button').forEach(x => x.onclick = () => {
      const k = b.dataset.k, v = x.dataset.v; V[k] = v === '' ? '' : (nombre(k) ? +v : v);
      b.querySelectorAll('button').forEach(y => y.classList.toggle('sel', y === x)); majTout(); apercu(); }));
    D.querySelectorAll('[data-raz]').forEach(b => b.onclick = () => {
      const k = b.dataset.raz, cible = jeu[k] !== undefined ? String(jeu[k]) : '';
      const x = D.querySelector(`.ms-choix[data-k="${k}"] button[data-v="${CSS.escape(cible)}"]`); if (x) x.click(); });
    const on = D.querySelector('.ms-stats-on');
    if (on) on.onchange = () => { statsOn = on.checked;
      if (statsOn) for (const k of Object.keys(MS_STAT)) if (V['stats.' + k] === '') V['stats.' + k] = 200;
      panneau(); };
    majTout();
  };
  // jauges, chiffres des écarts, cases des changements (en haut)
  const majTout = () => {
    D.querySelectorAll('.ms2-ligne[data-k]').forEach(L => {
      const k = L.dataset.k, max = +L.dataset.max || 1, v = V[k] === '' ? 0 : +V[k], o = jeu[k] !== undefined ? +jeu[k] : v;
      const J = L.querySelector('.ms2-jauge');
      J.style.setProperty('--v', Math.min(1, v / max)); J.style.setProperty('--o', Math.min(1, o / max));
      const d = v - o, e = L.querySelector('.ms2-delta');
      e.textContent = d ? (d > 0 ? '+' : '−') + Math.abs(d) : ''; e.className = 'ms2-delta' + (d > 0 ? ' plus' : d < 0 ? ' moins' : '');
      L.classList.toggle('change', !!d);
    });
    D.querySelectorAll('.ms-stat[data-st]').forEach(L => { const k = 'stats.' + L.dataset.st, o = jeu[k], e = L.querySelector('.ms2-delta');
      const d = o !== undefined && statsOn && V[k] !== '' ? +V[k] - o : 0;
      e.textContent = d ? (d > 0 ? '+' : '−') + Math.abs(d) : ''; e.className = 'ms2-delta' + (d > 0 ? ' plus' : d < 0 ? ' moins' : ''); });
    D.querySelectorAll('.ms2-l-choix').forEach(L => { const b = L.querySelector('.ms-choix'), k = b && b.dataset.k;
      L.classList.toggle('change', !!k && jeu[k] !== undefined && V[k] !== '' && String(V[k]) !== String(jeu[k])); });
    const cases = [];
    for (const ch of r.champs) { const k = ch.cle; if (k.startsWith('stats.') || V[k] === '' || V[k] === undefined || jeu[k] === undefined) continue;
      if (String(V[k]) === String(jeu[k])) continue;
      const nom = NOMS_COURTS[k] || ch.nom;
      if (nombre(k) && k !== 'users' && k !== 'growth') { const d = +V[k] - +jeu[k];
        cases.push(`<span class="ms2-case ${d > 0 ? 'plus' : 'moins'}"><small>${echapper(nom)}</small>${d > 0 ? '+' : '−'}${Math.abs(d)}</span>`); }
      else cases.push(`<span class="ms2-case chg"><small>${echapper(nom)}</small>${echapper(libChoix(k, jeu[k]))} → ${echapper(libChoix(k, V[k]))}</span>`); }
    if (joueur && statsOn) { let n = 0, tot = 0; for (const [k] of Object.entries(MS_STAT)) { const o = jeu['stats.' + k]; if (o === undefined || V['stats.' + k] === '') continue;
        if (+V['stats.' + k] !== o) n++; tot += +V['stats.' + k] - o; }
      if (n) cases.push(`<span class="ms2-case ${tot >= 0 ? 'plus' : 'moins'}"><small>${n} stat${n > 1 ? 's' : ''} · total</small>${tot >= 0 ? '+' : '−'}${Math.abs(tot)}</span>`); }
    const Z = D.querySelector('.ms2-deltas');
    if (Z) Z.innerHTML = cases.length ? cases.join('') + `<button class="ms2-tout-raz" title="Remettre toutes les valeurs de l’original (rien n’est écrit avant « Enregistrer »)">↺ Tout remettre</button>`
      : `<span class="ms2-rien">${jeu && Object.keys(jeu).length ? 'Comme l’original : change une valeur, l’écart s’affiche ici.' : 'Valeurs de l’original gardées tant que tu ne changes rien.'}</span>`;
    const T = D.querySelector('.ms2-tout-raz');
    if (T) T.onclick = () => { for (const ch of r.champs) if (jeu[ch.cle] !== undefined) V[ch.cle] = jeu[ch.cle]; panneau(); apercu(); };
  };
  // (23/11, demande de muku : « copier le jeu », écran validé sur maquette) JOUEUR : écran comme le Tableau des compétences
  // du jeu (capture de muku) : à gauche la carte, le poste et les lignes de stats (étiquette blanche, bout vert, gros chiffres
  // bleus, jauge) ; au centre le joueur en 3D ; à droite la plaque du nom et le détail de la stat choisie (− / +, barre, ↺).
  // Mêmes valeurs (V, statsOn) et même enregistrement qu'avant : changer une stat allume « les changer » (les 8 vont ensemble).
  const statsJeu = () => {
    const corps = f.querySelector('.ms-corps'); corps.classList.add('ms-jeu');
    corps.innerHTML = `<div class="msj-gauche"></div><div class="msj-centre"><canvas class="msj-vue"></canvas><div class="msj-vue-msg"></div></div><div class="msj-droite"></div>`;
    const Gc = corps.querySelector('.msj-gauche'), Dr = corps.querySelector('.msj-droite');
    const ST = Object.keys(MS_STAT), MAXJ = 300, POSTES = ['', 'fw', 'mf', 'df', 'gk'];
    let sel = 0;
    const brut = k => V['stats.' + k], orig = k => jeu['stats.' + k];
    const val = k => brut(k) === '' || brut(k) === undefined ? (orig(k) ?? 200) : +brut(k);
    const allumer = () => { if (statsOn) return; statsOn = true; for (const k of ST) if (brut(k) === '' || brut(k) === undefined) V['stats.' + k] = orig(k) ?? 200; };
    const regler = (k, v) => { allumer(); const ch = champ('stats.' + k) || {}; V['stats.' + k] = Math.max(ch.min ?? 0, Math.min(ch.max ?? 999, Math.round(v))); dessiner(); };
    const posteDe = () => V.position || jeu.position || '';
    const dessiner = () => {
      const pos = posteDe(), p = MS_POSTE[pos], ele = V.element || jeu.element, el2 = ele ? MS_EL[ele] : '';
      const port = c.code ? `<img src="/api/portrait?code=${encodeURIComponent(c.code)}" alt="">` : '';
      let h = `<div class="msj-carte el-${el2 || 'neutre'}">${port}${p ? `<span class="msj-poste p-${pos}">${p[0]}</span>` : ''}${ele ? `<span class="msj-el">${elIcone(ele, 26)}</span>` : ''}</div>
        <div class="msj-poste-ligne"><span>Poste :</span><button class="msj-fl" data-d="-1" title="Poste précédent">◀</button>
          <b class="msj-poste p-${pos || 'vide'}">${p ? p[0] : '—'}</b><button class="msj-fl" data-d="1" title="Poste suivant">▶</button>
          ${V.position === '' || V.position === undefined ? '<small>comme l’original</small>' : ''}</div><div class="msj-lignes">`;
      ST.forEach((k, n) => { const ch = champ('stats.' + k) || { nom: k }, v = val(k), o = orig(k), d = o !== undefined && statsOn ? v - o : 0;
        h += `<div class="msj-ligne${n === sel ? ' sel' : ''}${d ? ' change' : ''}" data-n="${n}"><span class="msj-etiq">${iconeNommee('st_' + k, 34)}<span class="msj-nom">${echapper(ch.nom)}</span></span>
          <span class="msj-tend ${d > 0 ? 'plus' : d < 0 ? 'moins' : ''}"></span>
          <span class="msj-val"><b>${v}</b><small>/${MAXJ}</small></span>
          <span class="msj-jauge" title="Clique pour régler"><i style="width:${Math.min(100, 100 * v / MAXJ)}%"></i>${o !== undefined ? `<u style="left:${Math.min(100, 100 * o / MAXJ)}%"></u>` : ''}</span></div>`; });
      h += `</div>`;
      Gc.innerHTML = h;
      // droite : plaque du nom + détail de la stat choisie + poste secondaire et élément
      const k = ST[sel], ch = champ('stats.' + k) || { nom: k }, v = val(k), o = orig(k);
      const sec = V.sub_position || '', secs = [['', 'comme l’original']].concat(Object.entries(MS_POSTE).map(([x, [a, nn]]) => [x, a + ' · ' + nn]));
      const els = [['', 'comme l’original']].concat((champ('element') || { choix: [] }).choix);
      Dr.innerHTML = `<div class="msj-plaque"><i class="msj-rayures"></i><span class="msj-nom-j">${echapper(c.nom)}</span>${p ? `<span class="msj-poste p-${pos}">${p[0]}</span>` : ''}
          ${ele ? elIcone(ele, 30) : ''}<small>${echapper(f.querySelector('.tc-plaque-sous').textContent)}</small></div>
        <div class="msj-detail"><div class="msj-tete">${iconeNommee('st_' + k, 44)}<span>${echapper(ch.nom)}</span></div>
          <div class="msj-corps-d"><div class="msj-col"><small>ORIGINAL</small><b>${o !== undefined ? o : '—'}</b></div>
            <div class="msj-col"><small>VALEUR</small><b class="msj-v">${v}</b></div>
            <div class="msj-regler"><button class="msj-pas" data-d="-1" title="−1 (Maj : −10)">−</button><input type="range" min="0" max="${MAXJ}" value="${Math.min(MAXJ, v)}">
              <button class="msj-pas" data-d="1" title="+1 (Maj : +10)">+</button><button class="msj-raz" title="Remettre la valeur de l’original">↺</button></div>
            ${statsOn ? '' : '<p class="msj-note">Les stats de l’original sont gardées tant que tu n’en changes aucune (les 8 vont ensemble).</p>'}</div></div>
        <div class="ms-etat"></div>
        <div class="msj-choix"><div class="msj-titre">2e poste</div><div class="msj-puces" data-k="sub_position">${secs.map(([x, nn]) => `<button data-v="${x}" class="${String(sec) === String(x) ? 'sel' : ''}">${echapper(nn)}</button>`).join('')}</div>
          <div class="msj-titre">Élément</div><div class="msj-puces" data-k="element">${els.map(([x, nn]) => `<button data-v="${x}" class="${String(V.element || '') === String(x) ? 'sel' : ''}">${x ? elIcone(x, 22) : ''}${echapper(nn)}</button>`).join('')}</div></div>`;
      // branchements
      Gc.querySelectorAll('.msj-ligne').forEach(L => L.onclick = e => { sel = +L.dataset.n; const J = e.target.closest('.msj-jauge');
        if (J) { const R = J.getBoundingClientRect(); regler(ST[sel], MAXJ * Math.max(0, Math.min(1, (e.clientX - R.left) / R.width))); } else dessiner(); });
      Gc.querySelectorAll('.msj-fl').forEach(b => b.onclick = () => { const i = POSTES.indexOf(V.position || ''); V.position = POSTES[(i + (+b.dataset.d) + POSTES.length) % POSTES.length]; dessiner(); });
      Dr.querySelectorAll('.msj-pas').forEach(b => b.onclick = e => regler(k, val(k) + (+b.dataset.d) * (e.shiftKey ? 10 : 1)));
      Dr.querySelector('.msj-regler input').oninput = e => regler(k, +e.target.value);
      Dr.querySelector('.msj-raz').onclick = () => { if (o !== undefined) regler(k, o); };
      Dr.querySelectorAll('.msj-puces').forEach(P => P.querySelectorAll('button').forEach(b => b.onclick = () => { V[P.dataset.k] = b.dataset.v; dessiner(); }));
    };
    f.onkeydown = e => { if (e.target.closest('input[type=number], select')) return; const k = ST[sel], pas = e.shiftKey ? 10 : 1;
      if (e.key === 'ArrowDown') { sel = (sel + 1) % ST.length; dessiner(); } else if (e.key === 'ArrowUp') { sel = (sel + ST.length - 1) % ST.length; dessiner(); }
      else if (e.key === 'ArrowRight') regler(k, val(k) + pas); else if (e.key === 'ArrowLeft') regler(k, val(k) - pas); else return;
      e.preventDefault(); };
    dessiner();
    joueur3D(corps.querySelector('.msj-vue'), corps.querySelector('.msj-vue-msg'), c.base || c.code, c.cle);
  };
  // (24/11, muku : « refais-moi le menu des stats d'un joueur pour pouvoir choisir ses techniques dedans ; à l'endroit vide sous
  // son nom, les stats qu'on peut modifier ; à l'endroit de « Catalyste… », la case de l'esprit guerrier ou du totem »)
  // JOUEUR = le Tableau des compétences du jeu (capture de muku) : à gauche la carte, le poste, la case esprit / totem (là où
  // le jeu met le catalyseur) puis les 6 techniques ; au centre le joueur en 3D ; à droite la plaque du nom, SOUS elle les 8
  // stats (clic, − / +, barre), puis la fiche blanche de la case choisie avec la liste pour la remplir. « Enregistrer » écrit
  // les techniques (/api/coups, seulement si elles ont changé) puis les stats (/api/stats), comme les deux anciens écrans.
  const joueurJeu = async () => {
    const corps = f.querySelector('.ms-corps'); corps.classList.add('ms-jeu', 'msp');
    corps.innerHTML = `<div class="msj-gauche"></div><div class="msj-centre"><canvas class="msj-vue"></canvas><div class="msj-vue-msg"></div></div><div class="msj-droite"><div class="msp-haut"></div><div class="ms-etat"></div><div class="msp-fiche"></div></div>`;
    const Gc = corps.querySelector('.msj-gauche'), Hd = corps.querySelector('.msp-haut'), Fi = corps.querySelector('.msp-fiche');
    const ST = Object.keys(MS_STAT), MAXJ = 300, POSTES = ['', 'fw', 'mf', 'df', 'gk'];
    let selSt = 0, sel = 0, filtreG = '', texte = '', touche = false;
    const brut = k => V['stats.' + k], orig = k => jeu['stats.' + k];
    const val = k => brut(k) === '' || brut(k) === undefined ? (orig(k) ?? 200) : +brut(k);
    const allumer = () => { if (statsOn) return; statsOn = true; for (const k of ST) if (brut(k) === '' || brut(k) === undefined) V['stats.' + k] = orig(k) ?? 200; };
    const regler = (k, v) => { allumer(); const ch = champ('stats.' + k) || {}; V['stats.' + k] = Math.max(ch.min ?? 0, Math.min(ch.max ?? 999, Math.round(v))); dessinerHaut(); };
    const posteDe = () => V.position || jeu.position || '';
    Gc.innerHTML = '<div class="tc-vide-txt">Lecture des techniques…</div>';
    // ---- techniques (même lecture que l'ancien Tableau des compétences)
    let R; try { R = await api('/api/coups?cle=' + encodeURIComponent(c.cle)); if (!R.ok) throw new Error(R.erreur); } catch (e) { R = { erreur: e.message, mes: [], catalogue: [], actuels: [], mods: [], origine: [], fiches: {}, modeles_esprits: {} }; }
    const tous = [...R.mes, ...R.catalogue], parId = new Map(tous.map(x => [x.id, x]));
    const estAura = x => AURAS_COUPS.includes(x.genre);
    const S = [null, null, null, null, null, null, null];          // 0-5 techniques, 6 = esprit / totem (case 9 du jeu)
    const poser = L => { S.fill(null); let k = 0; for (const m of L) { const x = parId.get(m.move); if (!x) continue;
        if (estAura(x)) S[6] = { move: m.move, level: m.level || 1 }; else if (k < 6) S[k++] = { move: m.move, level: m.level || 1 }; } };
    poser(R.actuels.length ? R.actuels : R.mods.length ? R.mods : R.origine);
    f.__coups = () => touche ? [...S.slice(0, 6), S[6]].filter(Boolean) : undefined;
    const fiche = x => R.fiches[x.code] || [0, 0, 0, 0];
    const iconeEsprit = x => { const m = R.modeles_esprits[String(fiche(x)[3])]; return m ? `<img class="tc-esp-ico" src="/api/icone_esprit?code=${encodeURIComponent(m)}" alt="" onerror="this.remove()">` : ''; };
    const barre = (x, i, petit) => {
      if (!x) return `<button class="tc-barre vide${i === 6 ? ' msp-vide-esprit' : ''}${petit ? ' petit' : ''}" data-i="${i}"><span class="tc-orbe"></span><span class="tc-nom">${i === 6 ? 'Esprit guerrier ou totem' : ''}</span></button>`;
      if (estAura(x)) return `<button class="tc-barre esprit${petit ? ' petit' : ''}" data-i="${i}" data-id="${x.id}"><span class="tc-nom">${x.mod ? '★ ' : ''}${echapper(x.nom)}</span><small>${echapper(x.genre)}</small>${iconeEsprit(x)}</button>`;
      const F = fiche(x), el = TC_EL[F[2]] || ['', 'neutre'], g = TC_GENRE[x.genre] || [x.genre.slice(0, 3).toUpperCase(), 'tir'];
      return `<button class="tc-barre el-${el[1]}${petit ? ' petit' : ''}" data-i="${i}" data-id="${x.id}" title="${echapper(x.nom)} — ${echapper(x.genre)}${el[0] ? ', ' + el[0] : ''} (${x.code})">
        <span class="tc-orbe g-${g[1]}"></span><span class="tc-nom">${x.mod ? '★ ' : ''}${echapper(x.nom)}</span><span class="tc-pw"><small>${g[0]}</small>${F[0] || ''}</span></button>`; };
    const changer = () => { touche = true; dessinerGauche(); dessinerFiche(); };
    // ---- gauche : carte, poste, case esprit / totem, 6 techniques
    const dessinerGauche = () => {
      const pos = posteDe(), p = MS_POSTE[pos], ele = V.element || jeu.element, el2 = ele ? MS_EL[ele] : '';
      const port = c.code ? `<img src="/api/portrait?code=${encodeURIComponent(c.code)}" alt="">` : '';
      Gc.innerHTML = `<div class="msj-carte el-${el2 || 'neutre'}">${port}${p ? `<span class="msj-poste p-${pos}">${p[0]}</span>` : ''}${ele ? `<span class="msj-el">${elIcone(ele, 26)}</span>` : ''}</div>
        <div class="msj-poste-ligne"><span>Poste :</span><button class="msj-fl" data-d="-1" title="Poste précédent">◀</button>
          <b class="msj-poste p-${pos || 'vide'}">${p ? p[0] : '—'}</b><button class="msj-fl" data-d="1" title="Poste suivant">▶</button>
          ${V.position === '' || V.position === undefined ? '<small>comme l’original</small>' : ''}</div>
        <div class="msp-cases">${barre(S[6] && parId.get(S[6].move), 6)}${[0, 1, 2, 3, 4, 5].map(i => barre(S[i] && parId.get(S[i].move), i)).join('')}</div>
        <div class="tc-boutons msp-boutons"><button data-f="origine" title="Les techniques de la carte d'origine (fichiers du jeu)">Celles du jeu</button>
          ${R.mods.length ? `<button data-f="mods" title="Ce que ${echapper(R.mod)} donne à l'original (ce que tu vois en jeu)">Celles de ${echapper(R.mod)}</button>` : ''}</div>
        ${R.erreur ? `<div class="tc-note">Techniques illisibles : ${echapper(R.erreur)}</div>` : R.plateau ? '<div class="tc-note">La carte d’origine a son propre plateau de compétences : une technique ajoutée n’y apparaît que si le plateau la contient (VRFW).</div>' : ''}`;
      Gc.querySelectorAll('.msp-cases .tc-barre').forEach(b => { b.classList.toggle('sel', +b.dataset.i === sel); b.onclick = () => { sel = +b.dataset.i; filtreG = ''; dessinerGauche(); dessinerFiche(); }; });
      Gc.querySelectorAll('.msj-fl').forEach(b => b.onclick = () => { const i = POSTES.indexOf(V.position || ''); V.position = POSTES[(i + (+b.dataset.d) + POSTES.length) % POSTES.length]; dessinerGauche(); dessinerHaut(); });
      Gc.querySelector('[data-f="origine"]').onclick = () => { poser(R.origine); changer(); };
      if (R.mods.length) Gc.querySelector('[data-f="mods"]').onclick = () => { poser(R.mods); changer(); };
    };
    // ---- droite, en haut : plaque du nom puis LES STATS (l'endroit vide du jeu sous le nom)
    const dessinerHaut = () => {
      const pos = posteDe(), p = MS_POSTE[pos], ele = V.element || jeu.element;
      const k = ST[selSt], ch = champ('stats.' + k) || { nom: k }, v = val(k), o = orig(k);
      const sec = V.sub_position || '', els = (champ('element') || { choix: [] }).choix;
      Hd.innerHTML = `<div class="msj-plaque"><i class="msj-rayures"></i><span class="msj-nom-j">${echapper(c.nom)}</span>${p ? `<span class="msj-poste p-${pos}">${p[0]}</span>` : ''}
          ${ele ? elIcone(ele, 30) : ''}<small>${echapper(f.querySelector('.tc-plaque-sous').textContent)}</small></div>
        <div class="msp-stats">${ST.map((s_, n) => { const c_ = champ('stats.' + s_) || { nom: s_ }, w = val(s_), o_ = orig(s_), d = o_ !== undefined && statsOn ? w - o_ : 0;
          return `<button class="msp-st${n === selSt ? ' sel' : ''}${d > 0 ? ' plus' : d < 0 ? ' moins' : ''}" data-n="${n}" title="${echapper(c_.nom)}${o_ !== undefined ? ' — original : ' + o_ : ''}">
            <span class="msp-st-nom">${iconeNommee('st_' + s_, 22)}<span>${echapper(c_.nom)}</span></span><b>${w}</b><i style="width:${Math.min(100, 100 * w / MAXJ)}%"></i></button>`; }).join('')}</div>
        <div class="msp-regler"><span class="msp-regler-nom">${iconeNommee('st_' + k, 26)}${echapper(ch.nom)}</span><small>Original</small><b>${o !== undefined ? o : '—'}</b>
          <button class="msj-pas" data-d="-1" title="−1 (Maj : −10)">−</button><input type="range" min="0" max="${MAXJ}" value="${Math.min(MAXJ, v)}">
          <button class="msj-pas" data-d="1" title="+1 (Maj : +10)">+</button><b class="msj-v">${v}</b><button class="msj-raz" title="Remettre la valeur de l’original">↺</button></div>
        <div class="msp-autres"><label>2e poste <select data-k="sub_position"><option value="">comme l’original</option>${Object.entries(MS_POSTE).map(([x, [a, nn]]) => `<option value="${x}"${String(sec) === x ? ' selected' : ''}>${a} · ${echapper(nn)}</option>`).join('')}</select></label>
          <label>Élément <select data-k="element"><option value="">comme l’original</option>${els.map(([x, nn]) => `<option value="${echapper(x)}"${String(V.element || '') === String(x) ? ' selected' : ''}>${echapper(nn)}</option>`).join('')}</select></label>
          ${statsOn ? '' : '<small class="msp-note">Stats de l’original gardées tant que tu n’en changes aucune (les 8 vont ensemble).</small>'}</div>`;
      Hd.querySelectorAll('.msp-st').forEach(b => b.onclick = () => { selSt = +b.dataset.n; dessinerHaut(); });
      Hd.querySelectorAll('.msj-pas').forEach(b => b.onclick = e => regler(k, val(k) + (+b.dataset.d) * (e.shiftKey ? 10 : 1)));
      Hd.querySelector('.msp-regler input').oninput = e => regler(k, +e.target.value);
      Hd.querySelector('.msj-raz').onclick = () => { if (o !== undefined) regler(k, o); };
      Hd.querySelectorAll('.msp-autres select').forEach(x => x.onchange = () => { V[x.dataset.k] = x.value; dessinerHaut(); dessinerGauche(); });
    };
    // ---- droite, en bas : fiche blanche de la case choisie + la liste pour la remplir
    const dessinerFiche = () => {
      const s_ = S[sel], x = s_ && parId.get(s_.move), F = x ? fiche(x) : null, aura = sel === 6;
      const liste = tous.filter(y => aura ? estAura(y) : !estAura(y)), genres = [...new Set(liste.map(y => y.genre))];
      const q = texte.toLowerCase().normalize('NFD').replace(/[̀-ͯ]/g, '');
      const L = liste.filter(y => (!filtreG || y.genre === filtreG) && (!q || (y.nom + ' ' + y.code).toLowerCase().normalize('NFD').replace(/[̀-ͯ]/g, '').includes(q)))
        .sort((a, b) => (b.mod ? 1 : 0) - (a.mod ? 1 : 0) || (fiche(b)[0] - fiche(a)[0]) || a.nom.localeCompare(b.nom)).slice(0, 150);
      const tension = (F && F[1] ? `<div class="tc-tension" style="--t:${Math.min(1, F[1] / 150)}"><span>TENSION</span><i></i><b>${F[1]}<small>T</small></b></div>` : '') + (F && (F[4] || +F[5]) ? `<div class="tc-recharge">${F[4] ? `<span title="Recharge">⟳ ${F[4]} s</span>` : ''}${+F[5] ? `<span class="tc-evol" title="${echapper(nomEvol(F[5]))}">${marquesEvol(F[5], 18)}</span>` : ''}</div>` : '');   // (25/11) + recharge et marques d'évolution (danifdez)
      Fi.innerHTML = `<div class="msp-detail">${x ? barre(x, sel, false) : `<div class="tc-vide-txt">${aura ? 'Case de l’esprit guerrier ou du totem : vide' : 'Case ' + (sel + 1) + ' vide'}</div>`}${tension}
          ${x ? `<div class="tc-infos"><label class="tc-niv"><span>Appris au</span> <i class="jm-touche">Lv.</i><input type="number" min="1" max="99" value="${s_.level}"></label>
            <span class="tc-puce">${echapper(x.genre)}</span>${F && TC_EL[F[2]] ? `<span class="tc-puce el-${TC_EL[F[2]][1]}">${TC_EL[F[2]][0]}</span>` : ''}
            ${x.mod ? `<span class="tc-puce mien">${x.mod}</span>` : ''}<button class="tc-vider">Vider la case</button></div>` : ''}</div>
        <div class="msp-choix"><div class="tc-choix-tete"><span>${aura ? 'Choisir un esprit guerrier ou un totem' : 'Choisir une technique'}</span>
            <div class="jm-recherche"><span class="jm-touche">X</span><input class="tc-cherche" placeholder="Chercher par nom" value="${echapper(texte)}"></div></div>
          <div class="tc-genres"><button data-g="" class="${filtreG ? '' : 'sel'}">Tout</button>${genres.map(g => `<button data-g="${echapper(g)}" class="${filtreG === g ? 'sel' : ''}">${echapper(g)}</button>`).join('')}</div>
          <div class="tc-liste">${L.map(y => barre(y, -1, true).replace('data-i="-1"', `data-choix="${y.id}"`)).join('') || '<div class="tc-vide-txt">Aucune</div>'}</div></div>`;
      const inp = Fi.querySelector('.tc-niv input'); if (inp) inp.oninput = () => { s_.level = Math.max(1, Math.min(99, +inp.value || 1)); touche = true; };
      const vd = Fi.querySelector('.tc-vider'); if (vd) vd.onclick = () => { S[sel] = null; changer(); };
      const ch = Fi.querySelector('.tc-cherche'); ch.oninput = () => { texte = ch.value; const p_ = ch.selectionStart; dessinerFiche(); const n = Fi.querySelector('.tc-cherche'); n.focus(); n.setSelectionRange(p_, p_); };
      Fi.querySelectorAll('.tc-genres button').forEach(b => b.onclick = () => { filtreG = b.dataset.g; dessinerFiche(); });
      Fi.querySelectorAll('[data-choix]').forEach(b => b.onclick = () => {
        const id = +b.dataset.choix, y = parId.get(id);
        const i0 = S.findIndex(m => m && m.move === id); if (i0 >= 0 && i0 !== sel) S[i0] = null;      // pas deux fois la même
        S[sel] = { move: id, level: (S[sel] && S[sel].level) || 1 };
        if (!estAura(y) && sel < 5) { const nx = S.findIndex((m, k_) => k_ < 6 && k_ > sel && !m); if (nx >= 0) sel = nx; }
        changer(); });
    };
    f.onkeydown = e => { if (e.target.closest('input, select')) return;
      if ((e.key === 'Delete' || e.key === 'Backspace') && S[sel]) { S[sel] = null; changer(); e.preventDefault(); } };
    dessinerGauche(); dessinerHaut(); dessinerFiche();
    joueur3D(corps.querySelector('.msj-vue'), corps.querySelector('.msj-vue-msg'), c.base || c.code, c.cle);
  };
  // (23/11, demandes de muku : « copie cette UI », « fais comme les joueurs : je clique sur Forest, ça me propose les autres »)
  // TECHNIQUE : écran du Tableau des compétences du jeu. À gauche l'APERÇU (la vue 3D de l'éditeur, tes couleurs, en boucle,
  // sans réglages) ; à droite la plaque du nom, la fiche blanche du jeu où CHAQUE élément se clique (barre = puissance max,
  // TENSION = PT, Solo, élément, Niv. 1, évolution, et la cosmétique), et entre les deux le détail de ce qui est choisi.
  const techJeu = () => {
    f.classList.add('ms-tech-mode'); f.querySelector('.tc-coin span').textContent = 'Tableau des compétences';
    const corps = f.querySelector('.ms-corps'); corps.classList.add('ms-jeu', 'msj-tech');
    corps.innerHTML = `<div class="msj-apercu"><div class="msj-apercu-hote"></div><div class="msj-apercu-msg"></div></div>
      <div class="msj-droite"><div class="msj-plaque"></div><div class="msjt-detail"></div><div class="msj-fiche"></div></div>`;
    const P = corps.querySelector('.msj-plaque'), Dt = corps.querySelector('.msjt-detail'), Fi = corps.querySelector('.msj-fiche');
    const GENRE_CAT = { shoot: ['g-tir', 'Tir'], dribble: ['g-dri', 'Dribble'], block: ['g-def', 'Défense'], catch: ['g-gar', 'Arrêt'] };
    const genre = () => GENRE_CAT[V.category] || MS_GENRE[(c.code || '').slice(0, 3)] || ['', ''];
    // (23/11, muku : « une meilleure image pour le type ») les ORBES DU JEU (icon_common, comme les barres du Tableau des compétences)
    const ORBE_CAT = { shoot: 'type_tir', dribble: 'type_dribble', block: 'type_bloc', catch: 'type_arret' };
    const CAT_PREF = { whs: 'shoot', who: 'dribble', whd: 'block', whk: 'catch' };
    const orbe = (cat, t) => iconeNommee(ORBE_CAT[cat] || '', t) || `<span class="tc-orbe ${(GENRE_CAT[cat] || [''])[0]}"></span>`;
    const catDe = () => V.category || CAT_PREF[(c.code || '').slice(0, 3)] || '';
    const ELS = (champ('element') || { choix: [] }).choix;
    const NOMS = { power_max: 'Puissance au niveau max', power_min: 'Puissance au niveau 1', tp: 'Coût en PT (tension)', users: 'Joueurs pour la lancer',
      element: 'Élément', growth: 'Type d’évolution', recast: 'Recharge (secondes)', category: 'Type de technique', specialite: 'Spécialité', couleur_tir: 'Couleur du tir', trainee: 'Traînée du ballon', prix: 'Prix en boutique', banniere: 'Bannière' };
    const MAXI = { power_max: 1500, power_min: 1000, tp: 150, recast: 180 };
    // (23/11) couleurs du tir LUES (skill_config m_skillColorInfoList) : 0 montagne (jaune-orange), 1 air (bleu), 2 feu
    // (orange-rouge), 3 forêt (vert), 4 néant (violet) ; 6 = bleu de la seule Inazuma Break (whs10180), autres effets de tir
    const COUL_TIR = [['', "Garder celle d'origine"], ['0', 'Montagne'], ['1', 'Air'], ['2', 'Feu'], ['3', 'Forêt'], ['4', 'Néant'], ['6', 'Inazuma Break (bleu)']];
    // (23/11, muku : « une photo au-dessus de ce que c'est ») IMAGE de chaque couleur : le ballon et son aura dessinés avec
    // la colonne de la texture du jeu BallAura0010 que cette couleur utilise (r.degrades_tir), du blanc au cœur au plus foncé
    const IMG_COUL = {};
    const imgCouleur = idx => {
      const d = (r.degrades_tir || {})[idx]; if (!d) return '';
      if (IMG_COUL[idx]) return IMG_COUL[idx];
      const W = 150, H = 84, cv = document.createElement('canvas'); cv.width = W; cv.height = H; const x = cv.getContext('2d');
      const rgb = (k, a) => `rgba(${d[Math.min(d.length - 1, k)].join(',')},${a})`, bx = 104, by = 44;
      x.fillStyle = '#0c1830'; x.fillRect(0, 0, W, H);
      x.globalCompositeOperation = 'lighter';
      const q = x.createLinearGradient(6, 0, bx, 0);                 // traînée
      q.addColorStop(0, rgb(31, 0)); q.addColorStop(.45, rgb(27, .55)); q.addColorStop(.85, rgb(14, .95)); q.addColorStop(1, rgb(6, 1));
      x.fillStyle = q; x.beginPath(); x.moveTo(6, by - 3); x.quadraticCurveTo(60, by - 24, bx, by - 22); x.lineTo(bx, by + 22); x.quadraticCurveTo(60, by + 24, 6, by + 3); x.closePath(); x.fill();
      const g2 = x.createRadialGradient(bx, by, 6, bx, by, 38);      // aura
      g2.addColorStop(0, rgb(2, 1)); g2.addColorStop(.4, rgb(12, .95)); g2.addColorStop(.72, rgb(26, .7)); g2.addColorStop(1, rgb(31, 0));
      x.fillStyle = g2; x.beginPath(); x.arc(bx, by, 38, 0, 7); x.fill();
      x.globalCompositeOperation = 'source-over';                     // ballon
      x.fillStyle = '#f4f6f8'; x.beginPath(); x.arc(bx, by, 13, 0, 7); x.fill();
      x.fillStyle = '#2b3440'; const pent = (cx, cy, rr) => { x.beginPath(); for (let i = 0; i < 5; i++) { const t = -Math.PI / 2 + i * 2 * Math.PI / 5; x.lineTo(cx + rr * Math.cos(t), cy + rr * Math.sin(t)); } x.fill(); };
      pent(bx, by, 4.6); pent(bx - 9, by - 6, 2.6); pent(bx + 9, by - 6, 2.6); pent(bx - 6, by + 9, 2.6); pent(bx + 6, by + 9, 2.6);
      return (IMG_COUL[idx] = cv.toDataURL());
    };
    const idxCouleur = v => v === '' || v === undefined ? jeu.couleur_tir_jeu : +v;
    // (23/11, muku : « des spécialités qu'on ne peut pas choisir, comme tir de loin ») SPÉCIALITÉ, LUE dans le jeu :
    // tir -> Tir lointain (bit 4) / Tir de contre (bit 16) ; défense -> Bloque-tir (bit 16) ; icônes icon_sp_sub01/03/02
    const SPEC = { long: ['Tir lointain', 'icon_sp_sub01'], contre: ['Tir de contre', 'icon_sp_sub03'], bloque: ['Bloque-tir', 'icon_sp_sub02'] };
    const specsDe = cat => cat === 'shoot' ? ['aucune', 'long', 'contre'] : cat === 'block' ? ['aucune', 'bloque'] : [];
    const icSpec = (k, t) => SPEC[k] ? `<img class="msjt-ic-spec" src="/ui_jeu/zone/icon_common/${SPEC[k][1]}.png" alt="" style="width:${t}px;height:${t}px">` : '';
    const TRAIN = [['', 'Celle du jeu'], ['ega0075', 'Tir spécial'], ['ega0080', 'Tir enchaîné'], ['ega0085', 'Tir lointain']];
    const TRAIN_EL = [['void', 'Néant (violet)'], ['wind', 'Air'], ['fire', 'Feu'], ['forest', 'Forêt'], ['mountain', 'Montagne']];
    const ordre = () => ['category'].concat(specsDe(catDe()).length ? ['specialite'] : [], ['power_max', 'tp', 'recast', 'users', 'element', 'power_min', 'growth', 'couleur_tir'], r.tir ? ['trainee'] : [], ['prix', 'banniere']);
    let sel = 'power_max';
    const lib = (L, v) => (L.find(x => String(x[0]) === String(v)) || ['', String(v)])[1];
    // (23/11, retour de muku : « la bannière ne change pas dans la preview ») bannière refaite (lettres du jeu / simple) et
    // envoyée à l'aperçu (vue 3D + lecteur du jeu ouvert) à chaque changement du texte, du style, des couleurs ou de l'élément
    let minBan = null;
    const banApercu = () => { clearTimeout(minBan); minBan = setTimeout(async () => {
      if (!E.tech || !E.projet) return;
      try { await api('/api/banniere_apercu', { code: E.tech.code, projet: E.projet, texte: C.ban_texte || c.nom, style: C.ban_style,
          couleur: C.ban_c, contour: C.ban_o, element: V.element || jeu.element });
        E.telopV = Date.now(); } catch (e) { /* aperçu seulement */ } }, 350); };
    const dessiner = () => {
      if (sel === 'specialite' && !specsDe(catDe()).length) sel = 'category';
      const el = MS_EL[V.element] || 'neutre', pmax = V.power_max !== '' ? V.power_max : '—', s_ = k => k === sel ? ' sel' : '', g = genre(), go = GENRE_CAT[jeu.category] || g;
      P.innerHTML = `<i class="msj-rayures"></i><span class="msj-nom-j">${echapper(c.nom)}</span>${V.element ? elIcone(V.element, 30) : ''}
        <span class="msj-genre">${echapper(g[1])}</span><span class="msj-pt"><small>PT</small>${V.tp !== '' ? V.tp : '—'}</span>`;
      Fi.innerHTML = `<div class="msj-fiche-tete"><span class="msjt-type msjt-clic${s_('category')}" data-k="category" title="Changer le type (tir, dribble, défense, arrêt)">${orbe(catDe(), 40)}<span>${echapper(g[1])}</span></span>
          ${specsDe(catDe()).length ? `<span class="msjt-spec msjt-clic${s_('specialite')}${V.specialite && V.specialite !== 'aucune' ? '' : ' vide'}" data-k="specialite" title="Spécialité">${V.specialite && SPEC[V.specialite] ? icSpec(V.specialite, 34) + '<span>' + echapper(SPEC[V.specialite][0]) + '</span>' : '<span>Spécialité : aucune</span>'}</span>` : ''}<small>Comme en jeu</small></div>
        <div class="msj-fiche-ligne"><div class="tc-barre el-${el} msjt-clic${s_('power_max')}" data-k="power_max"><span class="msjt-orbe">${orbe(catDe(), 46)}</span><span class="tc-nom">${echapper(c.nom)}</span><span class="tc-pw"><small>${g[1]}</small>${pmax}</span></div>
          <div class="tc-tension msjt-clic${s_('tp')}" data-k="tp" style="--t:${Math.min(1, (+V.tp || 0) / 150)}"><span>TENSION</span><i></i><b>${V.tp !== '' ? V.tp : '—'}<small>T</small></b></div></div>
        <div class="msj-fiche-puces"><span class="msj-ia msjt-clic${s_('users')}" data-k="users">${V.users > 1 ? V.users + ' joueurs' : 'Solo'}</span>
          <span class="tc-puce el-${el} ms2-puce msjt-clic${s_('element')}" data-k="element">${elIcone(V.element, 22)}${echapper(lib(ELS, V.element) || 'Élément')}</span>
          <span class="tc-niv msjt-clic${s_('power_min')}" data-k="power_min"><span>Niv. 1</span>${V.power_min}</span>
          <span class="tc-niv msjt-clic${s_('recast')}" data-k="recast"><span>Recharge</span>${V.recast !== '' && V.recast !== undefined ? V.recast + ' s' : '—'}</span>
          <span class="tc-niv msjt-evol msjt-clic${s_('growth')}" data-k="growth" title="${echapper(nomEvol(V.growth))}"><span>Évol.</span>${V.growth !== '' && +V.growth ? marquesEvol(V.growth, 20) : '—'}</span>
          ${jeu.power_max !== undefined ? `<span class="msj-orig"><small>Original</small><span class="tc-barre petit el-${MS_EL[jeu.element] || 'neutre'}"><span class="msjt-orbe">${orbe(jeu.category || catDe(), 32)}</span><span class="tc-nom">${echapper(nomBase)}</span><span class="tc-pw"><small>${go[1]}</small>${jeu.power_max}</span></span></span>` : ''}</div>
        <div class="msj-fiche-puces msjt-cosm"><span class="msjt-titre-c">Cosmétique</span>
          <span class="msjt-chip msjt-coul-chip msjt-clic${s_('couleur_tir')}" data-k="couleur_tir">${imgCouleur(idxCouleur(C.couleur_tir)) ? `<img src="${imgCouleur(idxCouleur(C.couleur_tir))}" alt="">` : ''}<span><small>Tir</small>${echapper(lib(COUL_TIR, C.couleur_tir))}</span></span>
          ${r.tir ? `<span class="msjt-chip msjt-clic${s_('trainee')}" data-k="trainee"><small>Traînée</small>${echapper(lib(TRAIN, C.trainee))}${C.trainee ? ' · ' + echapper(lib(TRAIN_EL, C.trainee_el)) : ''}</span>` : ''}
          <span class="msjt-chip msjt-clic${s_('prix')}" data-k="prix"><small>Boutique</small>${C.prix === '' ? 'Pas en vente' : C.prix + ' jetons'}</span>
          <span class="msjt-chip msjt-clic${s_('banniere')}" data-k="banniere"><small>Bannière</small>${echapper(C.ban_texte || (ban0.editeur ? 'de l’éditeur' : ban0.garder ? 'actuelle' : '—'))}</span></div>`;
      Fi.querySelectorAll('.msjt-clic').forEach(x => x.onclick = () => { sel = x.dataset.k; dessiner(); });
      detail();
    };
    // détail de ce qui est choisi (comme le détail d'une stat des joueurs)
    const detail = () => {
      const k = sel, nb = ['power_max', 'power_min', 'tp', 'recast'].includes(k);
      let corpsD = '';
      if (nb) {
        const v = V[k] === '' ? 0 : +V[k], o = jeu[k], mx = Math.max(MAXI[k], v, o || 0);
        corpsD = `<div class="msj-corps-d"><div class="msj-col"><small>ORIGINAL</small><b>${o !== undefined ? o : '—'}</b></div>
          <div class="msj-col"><small>VALEUR</small><input class="msjt-val" type="number" min="${(champ(k) || {}).min ?? 0}" max="${(champ(k) || {}).max ?? 9999}" value="${v}"></div>
          <div class="msj-regler"><button class="msj-pas" data-d="-1" title="−1 (Maj : −10)">−</button><input type="range" min="0" max="${mx}" value="${v}">
            <button class="msj-pas" data-d="1" title="+1 (Maj : +10)">+</button><button class="msj-raz" title="Remettre la valeur de l’original">↺</button></div></div>`;
      } else {
        const puces = (L, v, cle, ic) => `<div class="msj-puces" data-c="${cle}">${L.map(([x, n]) => `<button data-v="${x}" class="${String(v) === String(x) ? 'sel' : ''}${cle === k && jeu[k] !== undefined && String(jeu[k]) === String(x) ? ' orig' : ''}">${ic ? ic(x) : ''}${echapper(n)}</button>`).join('')}</div>`;
        if (k === 'users') corpsD = puces([[1, 'Solo'], [2, '2 joueurs'], [3, '3 joueurs'], [4, '4 joueurs']], V.users, 'users');
        else if (k === 'element') corpsD = puces(ELS, V.element, 'element', x => elIcone(x, 24));
        // (25/11) type d'évolution : nom du jeu + ses marques (niveaux 2 à 5), comme sur le nom de la technique en jeu
        else if (k === 'growth') corpsD = `<div class="msj-puces msjt-evols" data-c="growth">${[0, 1, 2, 3, 4, 5, 6, 7].map(n => `<button data-v="${n}" class="${String(V.growth) === String(n) ? 'sel' : ''}${jeu.growth !== undefined && String(jeu.growth) === String(n) ? ' orig' : ''}"><span>${echapper(nomEvol(n))}</span>${marquesEvol(n, 18)}</button>`).join('')}</div>
          <p class="msj-note msjt-note">La marque ajoutée au nom de la technique quand elle évolue (niveaux 2 à 5), comme en jeu.</p>`;
        else if (k === 'category') corpsD = puces((champ('category') || { choix: [] }).choix, V.category, 'category', x => orbe(x, 34))
          + '<p class="msj-note msjt-note">Le type décide où la technique est proposée en match (tir, dribble, défense, arrêt). La cinématique reste celle de l’original.</p>';
        else if (k === 'couleur_tir') corpsD = `<div class="msj-puces msjt-coul" data-c="couleur_tir">${COUL_TIR.map(([x, n]) => { const im = imgCouleur(idxCouleur(x));
            return `<button data-v="${x}" class="${String(C.couleur_tir) === String(x) ? 'sel' : ''}">${im ? `<img src="${im}" alt="">` : ''}<span>${echapper(n)}</span></button>`; }).join('')}</div>
          <p class="msj-note msjt-note">L’aura et la traînée du ballon pendant le tir, avec les couleurs du jeu (dégradé BallAura0010).</p>`;
        else if (k === 'specialite') corpsD = `<div class="msj-puces" data-c="specialite">${specsDe(catDe()).map(x => `<button data-v="${x}" class="${(V.specialite || 'aucune') === x ? 'sel' : ''}${jeu.specialite === x ? ' orig' : ''}">${icSpec(x, 28)}${echapper(SPEC[x] ? SPEC[x][0] : 'Aucune')}</button>`).join('')}</div>
          <p class="msj-note msjt-note">Comme dans le jeu : un tir lointain se tire de loin (et se propose dans tous les duels), un tir de contre reprend un ballon, un bloque-tir arrête les tirs.</p>`;
        else if (k === 'trainee') corpsD = puces(TRAIN, C.trainee, 'trainee') + (C.trainee ? '<div class="msj-titre">Couleur de la traînée</div>' + puces(TRAIN_EL, C.trainee_el, 'trainee_el') : '');
        else if (k === 'prix') corpsD = `<div class="msj-corps-d"><div class="msj-col"><small>JETONS</small><input class="msjt-val" type="number" min="1" value="${C.prix}" placeholder="—"></div>
          <div class="msj-regler"><button class="msj-pas" data-d="-1">−</button><button class="msj-pas" data-d="1">+</button><button class="msjt-pas-vente">Pas en vente</button></div></div>`;
        // (23/11, demande de muku) style : LETTRES DES BANNIÈRES DU JEU (découpées dans ses 861 bannières, couleur de l'élément)
        // ou simple (police Impact, couleurs des lettres et du contour)
        else if (k === 'banniere') corpsD = `<div class="msj-puces" data-c="ban_style">${[['jeu', 'Lettres du jeu'], ['simple', 'Simple (couleurs)']].map(([x, n]) => `<button data-v="${x}" class="${C.ban_style === x ? 'sel' : ''}">${echapper(n)}</button>`).join('')}</div>
          <div class="msjt-ban"><label>Texte <input class="msjt-ban-t" value="${echapper(C.ban_texte)}" placeholder="${ban0.editeur ? 'bannière de l’éditeur gardée (écris un texte pour la remplacer)' : ban0.garder ? 'bannière actuelle gardée (écris un texte pour la remplacer)' : 'FRAPPE GALACTIQUE'}"></label>
          <label>Lettres <input type="color" class="msjt-ban-c" value="${C.ban_c}"></label><label>Contour <input type="color" class="msjt-ban-o" value="${C.ban_o}"></label>
          <button type="button" class="ms-ban-perso" title="Ouvre l'éditeur de bannières avec cette copie choisie">✎ Personnaliser la bannière</button></div>`;
      }
      const raz = !nb && jeu[k] !== undefined ? `<button class="msj-raz msjt-raz" title="Remettre celui de l’original">↺</button>` : '';
      Dt.innerHTML = `<div class="msj-detail"><div class="msj-tete"><span>${echapper(NOMS[k] || k)}</span>${raz}</div>${corpsD}</div><div class="ms-etat"></div>`;
      Dt.firstElementChild.scrollIntoView({ block: 'nearest' });       // (24/11) petit écran : la case de réglage reste visible
      // branchements
      const regler = v => { const ch = champ(k) || {}; V[k] = Math.max(ch.min ?? 0, Math.min(ch.max ?? 99999, Math.round(v))); dessiner(); };
      if (nb) {
        Dt.querySelectorAll('.msj-pas').forEach(b => b.onclick = e => regler((V[k] === '' ? 0 : +V[k]) + (+b.dataset.d) * (e.shiftKey ? 10 : 1)));
        Dt.querySelector('input[type=range]').oninput = e => regler(+e.target.value);
        const n = Dt.querySelector('.msjt-val'); n.onchange = () => regler(+n.value || 0);
        Dt.querySelector('.msj-raz').onclick = () => { if (jeu[k] !== undefined) regler(jeu[k]); };
      }
      Dt.querySelectorAll('.msj-puces').forEach(L => L.querySelectorAll('button').forEach(b => b.onclick = () => {
        const cle = L.dataset.c, v = b.dataset.v;
        if (cle in C) C[cle] = v; else V[cle] = nombre(cle) ? +v : v;
        if (cle === 'category' && !specsDe(catDe()).includes(V.specialite)) { V.specialite = 'aucune'; }   // spécialité d'un autre type : retirée
        if (cle === 'ban_style' || cle === 'element') banApercu();
        dessiner(); }));
      const rz = Dt.querySelector('.msjt-raz'); if (rz) rz.onclick = () => { V[k] = jeu[k]; dessiner(); };
      if (k === 'prix') {
        const n = Dt.querySelector('.msjt-val'); n.onchange = () => { C.prix = n.value === '' || +n.value < 1 ? '' : Math.round(+n.value); dessiner(); };
        Dt.querySelectorAll('.msj-pas').forEach(b => b.onclick = e => { C.prix = Math.max(1, (+C.prix || 0) + (+b.dataset.d) * (e.shiftKey ? 10 : 1)); dessiner(); });
        Dt.querySelector('.msjt-pas-vente').onclick = () => { C.prix = ''; dessiner(); };
      }
      if (k === 'banniere') {
        const t = Dt.querySelector('.msjt-ban-t'); t.oninput = () => { C.ban_texte = t.value; banApercu(); };
        t.onchange = () => dessiner();
        Dt.querySelector('.msjt-ban-c').oninput = e => { C.ban_c = e.target.value; banApercu(); };
        Dt.querySelector('.msjt-ban-o').oninput = e => { C.ban_o = e.target.value; banApercu(); };
        Dt.querySelector('.ms-ban-perso').onclick = () => { B.preselect = c.code; finApercuStats(f); f.close(); window.changerOnglet('bannieres'); };
      }
    };
    // clavier : ↑ ↓ choisir, ← → changer (Maj : 10)
    f.onkeydown = e => {
      if (e.target.closest('input, select, textarea')) return;
      const ORDRE = ordre(), i = ORDRE.indexOf(sel), pas = e.shiftKey ? 10 : 1;
      if (e.key === 'ArrowDown' || e.key === 'ArrowUp') { sel = ORDRE[(i + (e.key === 'ArrowDown' ? 1 : ORDRE.length - 1)) % ORDRE.length]; dessiner(); }
      else if ((e.key === 'ArrowRight' || e.key === 'ArrowLeft') && ['power_max', 'power_min', 'tp'].includes(sel)) {
        const ch = champ(sel) || {}; V[sel] = Math.max(ch.min ?? 0, Math.min(ch.max ?? 99999, (V[sel] === '' ? 0 : +V[sel]) + (e.key === 'ArrowRight' ? pas : -pas))); dessiner(); }
      else return;
      e.preventDefault(); };
    dessiner();
    apercuTechnique(corps.querySelector('.msj-apercu-hote'), corps.querySelector('.msj-apercu-msg'), c, f);
  };
  // (23/11, demande de muku) ESPRIT GUERRIER / TOTEM : même écran que les techniques ; à gauche l'invocation en match
  // (lecteur du jeu), à droite la plaque, le détail de ce qui est choisi et la fiche (barre d'esprit, élément, Niv. 1)
  const espJeu = () => {
    f.classList.add('ms-tech-mode'); f.querySelector('.tc-coin span').textContent = 'Tableau des compétences';
    const corps = f.querySelector('.ms-corps'); corps.classList.add('ms-jeu', 'msj-tech');
    corps.innerHTML = `<div class="msj-apercu"><div class="msj-apercu-hote"></div><div class="msj-apercu-msg"></div></div>
      <div class="msj-droite"><div class="msj-plaque"></div><div class="msjt-detail"></div><div class="msj-fiche"></div></div>`;
    const P = corps.querySelector('.msj-plaque'), Dt = corps.querySelector('.msjt-detail'), Fi = corps.querySelector('.msj-fiche');
    const ELS = (champ('element') || { choix: [] }).choix, totem = c.genre === 'totem';
    // (23/11, demande de muku : « les armures maintenant ») ARMURE : même fiche (sa ligne AURA_CMD_INFO wao…/was… : puissance,
    // élément, bonus, effet unique) ; « Apparition » = sa MISE EN ARMURE (scènes ev81) ; bandeau fsa_base + icône Armed (area06) ;
    // ses techniques = celles de l'esprit (CharacterReforged keep_spirit) ; aperçu « armure_<ma copie d'esprit> »
    const armure = r.genre === 'armure', codeApercu = armure ? 'armure_' + r.esprit : c.code;
    const NOMS = { power_max: 'Puissance au niveau max', power_min: 'Puissance au niveau 1', element: 'Élément', invocation: armure ? 'Mise en armure (en match)' : 'Apparition (invocation en match)',
      bonus: armure ? 'Bonus (pour le joueur en armure)' : 'Bonus (pour le joueur qui l’invoque)', unique: 'Effet unique', banniere: 'Bannière' };
    // (24/11, muku : « ajoute un bouton comme les techniques pour faire sa bannière direct ici ») case Bannière : l'image actuelle
    // (son nom, automatique, ou celle de l'éditeur ; armure : ARMED) et « Personnaliser la bannière » -> éditeur, cette copie choisie
    const BAN = r.banniere || null;
    // (23/11, muku : « un autre truc qu'on ne peut pas modifier… tout sauf compatible ») BONUS et EFFET UNIQUE de l'esprit
    // (aura_skill_config AURA_CMD_EFFECT / AURA_CMD_UNIQUE_EFFECT, moteur/effets_esprits.py) : choisis parmi ceux que le jeu et
    // les mods utilisent, écrits tels quels (VRFW effects / unique_effects). null = ceux de l'original.
    const EO = r.effets_origine || { bonus: [], uniques: [] }, CAT = r.catalogue_effets || { bonus: [], uniques: [] };
    const nomEffet = l => ((CAT.bonus.concat(CAT.uniques)).find(x => x.ligne[0] === l[0]) || (EO.bonus.concat(EO.uniques)).find(x => x.ligne[0] === l[0]) || {}).nom || 'effet';
    const EF = { bonus: r.effets && r.effets.bonus ? r.effets.bonus.map(l => l.slice()) : null, uniques: r.effets && r.effets.uniques ? r.effets.uniques.map(l => l.slice()) : null };
    let efChange = false;
    const efListe = k => EF[k] || EO[k].map(x => x.ligne.slice());
    // (23/11, muku : « après un certain nombre de bonus, l'effet unique disparaît ») case courte : 2 noms puis « +n » (la liste
    // complète est dans la bulle et dans le panneau) ; avant, la case grandissait et poussait « Effet unique » hors de la fenêtre
    const efCourt = L => L.length ? L.slice(0, 2).map(nomEffet).join(' · ') + (L.length > 2 ? ' +' + (L.length - 2) : '') : 'aucun';
    // (23/11, demande de muku : « changer l'animation d'apparition », « c'est selon l'esprit guerrier ») chaque scène
    // d'invocation contient les gestes de plusieurs esprits : on choisit l'esprit (et sa scène) dont ta copie prend les gestes
    const INV = r.invocations || [], INV0 = r.invocation_origine || null;
    let invChoix = r.invocation && r.invocation.choisie ? { scene: r.invocation.scene, esprit: r.invocation.esprit } : null, invChange = false;
    const ORDRE = ['power_max', 'element', 'power_min'].concat(INV.length ? ['invocation'] : []).concat(['bonus', 'unique'], BAN ? ['banniere'] : []);
    const libInv = x => x ? ((INV.find(y => y.scene === x.scene && y.esprit === x.esprit) || {}).nom || x.esprit) : (totem ? 'Celle de l’original' : 'Selon l’élément');
    let sel = 'power_max';
    const lib = (L, v) => (L.find(x => String(x[0]) === String(v)) || ['', String(v)])[1];
    const PORTRAIT_V = Date.now();        // portrait relu à chaque ouverture (il change quand la copie est refaite)
    const dessiner = () => {
      const pmax = V.power_max !== '' ? V.power_max : '—', s_ = k => k === sel ? ' sel' : '', el = MS_EL[V.element] || 'neutre';
      P.innerHTML = `<i class="msj-rayures"></i><span class="msj-nom-j">${echapper(c.nom)}</span>${V.element ? elIcone(V.element, 30) : ''}
        <span class="msj-genre">${echapper(motEsprit)}</span>`;
      // (23/11, muku : « c'est ça », capture de la carte Keshin du Tableau des compétences) CARTE DU JEU (team00_30) :
      // bandeau de l'élément fs_base01-05 (totems : soul_base) avec l'icône du genre (icon_sp_area05 Keshin, 08 totem,
      // Lua ability_learning_report_menu : 100 + n -> area05 + n), le nom et le portrait (aura_fs / aura_soul) à droite ;
      // « Technique de Keshin » ; sa barre fsp_base (élément) avec sa puissance et ATT / DÉF (gtxt_cmd_at01 / df01) ; son type
      const T = r.technique || {}, gT = MS_GENRE[(T.code || '').slice(0, 3)] || ['', ''];
      const nEl = e => ({ wind: '01', forest: '02', fire: '03', mountain: '04', void: '05' })[e] || '05';
      const fond = (e, tot) => `/ui_jeu/zone/team00_30/${tot ? 'soul' : armure ? 'fsa' : 'fs'}_base${nEl(e)}.png`;
      const bandeau = (nom, e, cls, k, port) => `<div class="msjk-bandeau${cls}"${k ? ` data-k="${k}"` : ''} style="background-image:url('${fond(e, totem)}')">
          <img class="msjk-ic" src="/ui_jeu/zone/icon_common/icon_sp_area${totem ? '08' : armure ? '06' : '05'}.png" alt=""><span class="msjk-nom">${echapper(nom)}</span>
          ${port ? `<img class="msjk-portrait" src="/api/icone_esprit?code=${encodeURIComponent(port)}&v=${PORTRAIT_V}" alt="" onerror="this.remove()">` : ''}</div>`;
      const defense = ['g-def', 'g-gar'].includes(gT[0]);
      Fi.innerHTML = `<div class="msjk-carte">${bandeau(c.nom, V.element, ' msjt-clic' + s_('element'), 'element', armure ? r.esprit : c.code)}
        ${armure ? `<div class="msjk-sous"><span class="msjk-titre">Techniques : celles de l’esprit</span><small>Comme en jeu</small></div>
        <div class="msjk-tech msjt-clic${s_('power_max')}" data-k="power_max" style="background-image:url('/ui_jeu/zone/team00_30/fsp_base${nEl(V.element)}.png')"><span class="msjk-tnom">${echapper(motEsprit)}</span>
          <span class="msjk-pw"><img src="/ui_jeu/zone/team00_30/gtxt_cmd_at01.png" alt="">${pmax}</span></div>` : `<div class="msjk-sous"><span class="msjk-titre">Technique ${totem ? 'du totem' : 'de Keshin'}</span><small>Comme en jeu</small></div>
        <div class="msjk-tech msjt-clic${s_('power_max')}" data-k="power_max" style="background-image:url('/ui_jeu/zone/team00_30/fsp_base${nEl(V.element)}.png')">
          ${{ 'g-tir': '01', 'g-dri': '02', 'g-def': '03', 'g-gar': '04' }[gT[0]] ? `<img class="msjk-type" src="/ui_jeu/zone/icon_common/icon_sp_area${{ 'g-tir': '01', 'g-dri': '02', 'g-def': '03', 'g-gar': '04' }[gT[0]]}.png" alt="">` : ''}<span class="msjk-tnom">${echapper(T.nom || motEsprit)}</span>
          <span class="msjk-pw"><img src="/ui_jeu/zone/team00_30/gtxt_cmd_${defense ? 'df' : 'at'}01.png" alt="">${pmax}</span></div>`}
        <div class="msj-fiche-puces"><div class="msjk-ligne1">${gT[1] ? `<span class="msjk-genre ${gT[0]}">${echapper(gT[1])}</span>` : ''}
          <span class="tc-puce el-${el} ms2-puce msjt-clic${s_('element')}" data-k="element">${elIcone(V.element, 22)}${echapper(lib(ELS, V.element) || 'Élément')}</span>
          <span class="tc-niv msjt-clic${s_('power_min')}" data-k="power_min"><span>Niv. 1</span>${V.power_min}</span>
          ${INV.length ? `<span class="msjt-chip msjt-clic${s_('invocation')}" data-k="invocation" title="${echapper(libInv(invChoix))}"><small>${armure ? 'Mise en armure' : 'Apparition'}</small>${echapper(libInv(invChoix))}</span>` : ''}
          <span class="msjt-chip msjk-ef msjt-clic${s_('bonus')}" data-k="bonus" title="${echapper(efListe('bonus').map(nomEffet).join(' · '))}"><small>Bonus${EF.bonus ? ' ✎' : ''}</small>${echapper(efCourt(efListe('bonus')))}</span>
          <span class="msjt-chip msjk-ef msjt-clic${s_('unique')}" data-k="unique" title="${echapper(efListe('uniques').map(nomEffet).join(' · '))}"><small>Effet unique${EF.uniques ? ' ✎' : ''}</small>${echapper(efCourt(efListe('uniques')))}</span>
          ${BAN ? `<span class="msjt-chip msjt-clic${s_('banniere')}" data-k="banniere"><small>Bannière</small>${echapper(BAN.editeur ? 'de l’éditeur' : armure ? 'celle du jeu' : 'automatique')}</span>` : ''}</div>
          ${jeu.power_max !== undefined ? `<span class="msj-orig"><small>Original</small>${bandeau((armure ? r.nom_origine || nomBase : nomBase) + ' · ' + jeu.power_max, jeu.element, ' petit', '', armure ? r.esprit_origine : c.base)}</span>` : ''}</div></div>`;
      Fi.querySelectorAll('.msjt-clic').forEach(x => x.onclick = () => { sel = x.dataset.k; dessiner(); });
      detail();
    };
    const detail = () => {
      const k = sel, nb = k !== 'element' && k !== 'invocation' && k !== 'bonus' && k !== 'unique' && k !== 'banniere';
      let corpsD;
      if (k === 'banniere') {
        corpsD = `<div class="msjk-ban"><img src="/api/banniere_esprit_png?id=${encodeURIComponent(BAN.id)}&base=${encodeURIComponent(BAN.base || '')}&v=${Date.now()}" alt="" onerror="this.remove()"></div>
          <p class="msj-note msjt-note">${armure ? 'Bannière « ARMED » de la mise en armure : dans le jeu, la même pour toutes les armures. La tienne remplace celle du jeu pour cette armure seulement.'
            : 'Montrée à l’invocation en match : faite automatiquement avec son nom (lettres du jeu), ou la tienne faite dans l’éditeur de bannières.'}</p>
          <div class="msjt-ban"><button type="button" class="ms-ban-perso" title="Ouvre l'éditeur de bannières avec cette copie choisie">✎ Personnaliser la bannière</button></div>`;
      } else if (k === 'bonus' || k === 'unique') {
        const cle = k === 'bonus' ? 'bonus' : 'uniques', L = efListe(cle), max = k === 'bonus' ? 6 : 3;
        const choix = k === 'bonus' ? CAT.bonus : CAT.uniques.filter(x => x.texte || L.some(l => l[0] === x.ligne[0]));
        corpsD = `<div class="msjk-ef-liste">${L.map((l, i) => `<span class="msjk-ef-pastille">${echapper(nomEffet(l))}<button data-retirer="${i}" title="Retirer">✕</button></span>`).join('') || '<i>aucun</i>'}</div>
          ${L.length < max ? `<div class="msjk-ef-ajout"><select class="msjk-ef-choix"><option value="">+ Ajouter ${k === 'bonus' ? 'un bonus' : 'un effet unique'}…</option>
            ${choix.map((x, i) => `<option value="${i}">${echapper((x.type ? x.type + ' · ' : '') + x.nom)}${x.emplois > 1 ? ' (' + x.emplois + ' esprits)' : ''}</option>`).join('')}</select></div>` : `<p class="msj-note msjt-note">${max} au plus (comme dans le jeu).</p>`}
          <p class="msj-note msjt-note">${k === 'bonus' ? (armure ? 'Bonus que reçoit le joueur en armure. Choisis parmi ceux que le jeu utilise (écrits exactement comme le jeu).' : 'Bonus que reçoit le joueur qui invoque l’esprit. Choisis parmi ceux que le jeu utilise (écrits exactement comme le jeu).')
            : 'Effet en plus, comme une compétence passive. Choisis parmi ceux du jeu et des mods activés.'} Original : ${echapper(EO[cle].map(x => x.nom).join(' · ') || 'aucun')}.</p>`;
      } else if (k === 'invocation') {
        const EL_NOM = Object.fromEntries(ELS);
        const bouton = (x, n, ic, sl) => `<button data-inv="${x ? x.scene + '|' + x.esprit : ''}" class="${sl ? 'sel' : ''}${x && x.os_ok === false ? ' msjt-os' : ''}"${x && x.os_ok === false ? ' title="Pas tous ses os chez ta copie : regarde l’aperçu"' : ''}>${ic}${echapper(n)}</button>`;
        let h = '<div class="msj-puces msjt-inv">' + bouton(null, totem ? 'Celle de l’original' : 'Selon l’élément (automatique)', '', !invChoix) + '</div>';
        const parScene = {};
        for (const x of INV) (parScene[x.scene] = parScene[x.scene] || []).push(x);
        for (const [sc, L] of Object.entries(parScene)) {
          const el = L[0].element;
          h += `<div class="msj-titre">${el ? elIcone(el, 18) + ' ' + echapper(EL_NOM[el] || el) : sc.startsWith('ev83') ? 'Invocation des totems' : 'Scène de Pégase'} <small>(${sc})</small></div><div class="msj-puces msjt-inv">`
            + L.map(x => bouton(x, x.nom + (INV0 && x.esprit === INV0.esprit && x.scene === INV0.scene ? ' (original)' : ''), '',
                invChoix && invChoix.scene === x.scene && invChoix.esprit === x.esprit)).join('') + '</div>';
        }
        corpsD = h + '<p class="msj-note msjt-note">Ta copie prend les gestes de l’esprit choisi, dans la scène de son élément. Tous sont proposés : ceux en pointillés n’ont pas tous leurs os chez ta copie (des pièces peuvent rester figées), regarde l’aperçu à gauche avant de choisir. « Enregistrer » garde ton choix.</p>'
          // (25/11, demande de muku) COULEURS DE L'APPARITION : la scène d'invocation ouverte dans l'éditeur (« invoc_<copie> »)
          + (!totem && !armure ? `<div class="msjk-app"><button class="msjk-couleurs-app"${invChange ? ' disabled' : ''}>🎨 Couleurs de l’apparition</button>
            <p class="msj-note msjt-note">${invChange ? '« Enregistrer » d’abord ce choix : les couleurs se font sur l’apparition enregistrée.' : 'Ouvre l’apparition dans l’éditeur : recolore ses effets comme une technique, puis « Enregistrer les couleurs de l’apparition ». Seul ton esprit change, pas les autres de cet élément.'}</p>
            <p class="msj-note msjt-note">L’aperçu de cette fiche montre l’apparition du jeu : tes couleurs se voient dans l’éditeur, et en jeu après « Installer ».</p></div>` : '');
      } else if (nb) {
        const v = V[k] === '' ? 0 : +V[k], o = jeu[k], mx = Math.max(300, v, o || 0);
        corpsD = `<div class="msj-corps-d"><div class="msj-col"><small>ORIGINAL</small><b>${o !== undefined ? o : '—'}</b></div>
          <div class="msj-col"><small>VALEUR</small><input class="msjt-val" type="number" min="0" max="${(champ(k) || {}).max ?? 32767}" value="${v}"></div>
          <div class="msj-regler"><button class="msj-pas" data-d="-1" title="−1 (Maj : −10)">−</button><input type="range" min="0" max="${mx}" value="${v}">
            <button class="msj-pas" data-d="1" title="+1 (Maj : +10)">+</button><button class="msj-raz" title="Remettre la valeur de l’original">↺</button></div></div>`;
      } else {
        corpsD = `<div class="msj-puces" data-c="element">${ELS.map(([x, n]) => `<button data-v="${x}" class="${String(V.element) === String(x) ? 'sel' : ''}${jeu.element === x ? ' orig' : ''}">${elIcone(x, 24)}${echapper(n)}</button>`).join('')}</div>`
          + (totem ? '' : armure ? '<p class="msj-note msjt-note">La mise en armure suit l’élément (scène de mise en armure de cet élément, enregistrée avec « Enregistrer »).</p>'
            : '<p class="msj-note msjt-note">L’invocation en match suit l’élément (scène d’invocation de cet élément, enregistrée avec « Enregistrer »).</p>');
      }
      const raz = (k === 'bonus' || k === 'unique') ? `<button class="msj-raz msjk-ef-raz" title="Remettre ceux de l’original">↺</button>`
        : !nb && jeu[k] !== undefined ? `<button class="msj-raz msjt-raz" title="Remettre celui de l’original">↺</button>` : '';
      Dt.innerHTML = `<div class="msj-detail"><div class="msj-tete"><span>${echapper(NOMS[k] || k)}</span>${raz}</div>${corpsD}</div><div class="ms-etat"></div>`;
      Dt.firstElementChild.scrollIntoView({ block: 'nearest' });       // (24/11) petit écran : la case de réglage reste visible
      const regler = v => { const ch = champ(k) || {}; V[k] = Math.max(ch.min ?? 0, Math.min(ch.max ?? 99999, Math.round(v))); dessiner(); };
      if (nb) {
        Dt.querySelectorAll('.msj-pas').forEach(b => b.onclick = e => regler((V[k] === '' ? 0 : +V[k]) + (+b.dataset.d) * (e.shiftKey ? 10 : 1)));
        Dt.querySelector('input[type=range]').oninput = e => regler(+e.target.value);
        const n = Dt.querySelector('.msjt-val'); n.onchange = () => regler(+n.value || 0);
        Dt.querySelector('.msj-raz').onclick = () => { if (jeu[k] !== undefined) regler(jeu[k]); };
      }
      // aperçu du choix (le lecteur du jeu relancé sur cette apparition) ; (23/11, retour de muku : « quand je change l'élément
      // et que l'apparence est par élément ça ne recharge pas ») « Selon l'élément » : l'invocation de l'élément CHOISI ici
      // (« ~@<élément> », serveur : plan_invocation comme à l'enregistrement), pas celle enregistrée
      const relancerApercu = () => {
        const hote = f.querySelector('.msj-apercu-hote'), msg = f.querySelector('.msj-apercu-msg');
        if (hote) { finApercuStats(f); apercuInvocation(hote, msg, codeApercu, f, invChoix || (totem ? null : { element: V.element })); } };
      Dt.querySelectorAll('.msj-puces button[data-v]').forEach(b => b.onclick = () => {
        const avant = V.element; V.element = b.dataset.v; dessiner();
        if (!invChoix && !totem && String(avant) !== String(V.element)) relancerApercu(); });
      const bApp = Dt.querySelector('.msjk-couleurs-app');
      // (25/11) le projet déjà commencé de cette apparition est REPRIS (sinon un projet neuf repartirait des couleurs du jeu,
      // et l'enregistrer effacerait les couleurs faites avant)
      if (bApp) bApp.onclick = () => {
        const pj = ((window.HUB && HUB.projets) || []).filter(p => p.code === 'invoc_' + c.code && p.onglet === 'techniques')
          .sort((a, b) => String(b.cle).localeCompare(String(a.cle)))[0];
        finApercuStats(f); f.close(); pj ? reprendreDepuisHub(pj) : ouvrirDepuisHub('techniques', 'invoc_' + c.code); };
      Dt.querySelectorAll('.msj-puces button[data-inv]').forEach(b => b.onclick = () => {
        const [sc, es] = b.dataset.inv.split('|'); invChoix = sc ? { scene: sc, esprit: es } : null; invChange = true; dessiner();
        relancerApercu(); });
      const rz = Dt.querySelector('.msjt-raz'); if (rz) rz.onclick = () => { V[k] = jeu[k]; dessiner(); };
      if (k === 'banniere') Dt.querySelector('.ms-ban-perso').onclick = () => { B.preselect = BAN.id; finApercuStats(f); f.close(); window.changerOnglet('bannieres'); };
      if (k === 'bonus' || k === 'unique') {
        const cle = k === 'bonus' ? 'bonus' : 'uniques';
        const choix = k === 'bonus' ? CAT.bonus : CAT.uniques.filter(x => x.texte || efListe(cle).some(l => l[0] === x.ligne[0]));
        Dt.querySelectorAll('[data-retirer]').forEach(b => b.onclick = () => { const L = efListe(cle); L.splice(+b.dataset.retirer, 1); EF[cle] = L; efChange = true; dessiner(); });
        const se = Dt.querySelector('.msjk-ef-choix'); if (se) se.onchange = () => { const x = choix[+se.value]; if (!x) return; const L = efListe(cle); L.push(x.ligne.slice()); EF[cle] = L; efChange = true; dessiner(); };
        const zr = Dt.querySelector('.msjk-ef-raz'); if (zr) zr.onclick = () => { EF[cle] = null; efChange = true; dessiner(); };
      }
    };
    f.onkeydown = e => {
      if (e.target.closest('input, select, textarea')) return;
      const i = ORDRE.indexOf(sel), pas = e.shiftKey ? 10 : 1;
      if (e.key === 'ArrowDown' || e.key === 'ArrowUp') { sel = ORDRE[(i + (e.key === 'ArrowDown' ? 1 : ORDRE.length - 1)) % ORDRE.length]; dessiner(); }
      else if ((e.key === 'ArrowRight' || e.key === 'ArrowLeft') && sel !== 'element') {
        const ch = champ(sel) || {}; V[sel] = Math.max(ch.min ?? 0, Math.min(ch.max ?? 99999, (V[sel] === '' ? 0 : +V[sel]) + (e.key === 'ArrowRight' ? pas : -pas))); dessiner(); }
      else return;
      e.preventDefault(); };
    f.__invocation = () => invChange ? (invChoix || { auto: true }) : undefined;
    // (23/11) bonus / effet unique : envoyés seulement s'ils ont été touchés ({} = ceux de l'original)
    f.__effets = () => efChange || r.effets ? Object.fromEntries(Object.entries(EF).filter(([, v]) => v)) : undefined;
    dessiner();
    const hote = corps.querySelector('.msj-apercu-hote'), msg = corps.querySelector('.msj-apercu-msg');
    // (23/11, totems) un totem A une invocation en match : ev83_00010_1 (LU : colonne 12 de wss000020… = crc32 de ce nom ;
    // gestes de 20 totems, ceux de la copie livrés sous son code) -> joué par le lecteur du jeu, comme les Keshin
    apercuInvocation(hote, msg, codeApercu, f);
  };
  if (joueur && c.cle) { f.classList.add('msp-mode'); f.querySelector('.tc-coin span').textContent = 'Tableau des compétences'; joueurJeu(); } else if (joueur) statsJeu(); else if (r.genre === 'technique') techJeu(); else if (r.genre === 'esprit' || r.genre === 'armure') espJeu(); else { apercu(); panneau(); }
  f.querySelector('.ms-aide-txt').textContent = joueur && c.cle ? 'Clique une case pour choisir sa technique ; clique une stat pour la changer (− / +, la barre). Suppr : vider la case'
    : joueur ? 'Clique une statistique, puis change sa valeur (− / +, la barre, ou ← →)'
    : r.genre === 'technique' || r.genre === 'esprit' || r.genre === 'armure' ? 'Clique un élément de la fiche pour le changer (↑ ↓ choisir, ← → changer)' : 'Partie des valeurs de l’original : seules celles que tu changes sont écrites';
  const envoyer = async stats => {
    const e = f.querySelector('.ms-etat'); e.textContent = 'Écriture…';
    const bs = [f.querySelector('.ms-garder'), f.querySelector('.ms-original')].filter(Boolean);   // (22/11) pas de double clic
    if (bs.some(b => b.disabled)) return;
    bs.forEach(b => { b.disabled = true; });
    // (24/11) joueur : ses techniques d'abord (si elles ont changé), comme « Enregistrer » de l'ancien Tableau des compétences
    const coups = f.__coups ? f.__coups() : undefined; let rapCoups = [];
    if (coups !== undefined) { try { const qc = await api('/api/coups', { cle: c.cle, coups });
        if (!qc.ok) { bs.forEach(b => { b.disabled = false; }); e.textContent = qc.erreur; return; } rapCoups = qc.rapport || []; }
      catch (x) { bs.forEach(b => { b.disabled = false; }); e.textContent = x.message; return; } }
    try { const q = await api('/api/stats', { mod: c.mod, code, stats, cosmetique: cosmetique(), invocation: f.__invocation ? f.__invocation() : undefined, effets: f.__effets ? f.__effets() : undefined }).finally(() => bs.forEach(b => { b.disabled = false; }));
      if (!q.ok) { e.textContent = q.erreur; return; }
      finApercuStats(f); f.close(); majRapport(rapCoups.concat(q.rapport).join('\n'));
      $('hub-etat').textContent = (C ? 'Stats et cosmétique enregistrées. Pour le mettre dans le jeu : « Installer » sur sa carte dans Mes créations.' : 'Stats enregistrées. Pour le mettre dans le jeu : « Installer » sur sa carte dans Mes créations.'); chargerHub();
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
  window[nom] = async function (...a) { retirerSuite(); SUITE_N++;
    const r = await f0.apply(this, a); if (r && r.ok && (r.code || r.key)) { await lierProjetCreation(mod, r.code || r.key); await proposerSuite(mod, r.code); }
    if (r && r.ok && $('page-hub') && typeof chargerHub === 'function') chargerHub();
    return r; };
}
// (22/11, retour de muku : « Modifier crée un nouveau dans À continuer alors que ça devrait modifier celui qui existe »)
// « Modifier » rouvre LA création : son projet lié, sinon un projet lié à elle (clé fixe « cree_<mod>_<code> ») avec son
// nom dans le champ du nom -> « Créer » met à jour la même création (même nom = même code, partout dans l'Atelier).
// Un projet lié à une création qui existe n'est pas dans « À continuer ».
function champNomCreation(c) {
  return c.mod === 'MesTechniques' ? 'f-nom' : c.mod === 'MesEsprits' ? (c.genre === 'armures' ? 'ca-nom' : 'p-nom')
    : c.mod === 'MesPersonnages' ? (c.copie === 'objet' ? 'co-nom' : c.onglet === 'tenues' ? 'ct-nom' : 'cp-nom') : c.mod === 'MesTenues' ? 'cu-nom' : c.mod === 'MesObjets' ? 'oj-nom-copie' : null;
}
const cleCreation = c => ('cree_' + c.mod + '_' + c.code).replace(/[^\w.-]/g, '_');
async function modifierCreation(c) {
  const proj = projetDe(c);
  if (proj) return reprendreDepuisHub(proj);
  E.modifie = { mod: c.mod, code: String(c.code), nom: c.nom, champ: champNomCreation(c) };
  await ouvrirDepuisHub(c.onglet, c.base, cleCreation(c));
}
function projetLieExistant(p) {
  return !!(p.cree && HUB.creations.some(c => c.mod === p.cree.mod && String(c.code) === String(p.cree.code)));
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

// (22/11, 2.0.1) un fichier du jeu illisible (modifié par un autre outil de mod…) ne bloque plus le démarrage : on le dit une fois
(async () => { try {
  const e = await api('/api/etat');
  if (e.catalogues_en_erreur && e.catalogues_en_erreur.length)
    alert("Certains fichiers du jeu sont illisibles (sans doute modifiés par un autre outil de mod) : ces parties de l'Atelier restent vides.\n\n"
          + e.catalogues_en_erreur.join('\n') + '\n\nJournal / log : AtelierCouleurs\\cache\\serveur.log');
} catch (_) {} })();
