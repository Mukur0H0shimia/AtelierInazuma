// Particules du jeu (.ptlb) recréées à l'identique (13/11/2026) : code lu dans nie.exe, vérifié en exécutant le vrai code
// du jeu dans un émulateur (nie_outils/emu_ptl.py, banc d'essai : nie_outils/test_particules.js).
// Détail des adresses et des formules : coffre Obsidian, note « Particules - code du moteur ».
//
// Une instance d'Emetteur = l'état d'un émetteur vivant (0x4E0 octets dans le jeu) + ses particules (0x120 octets chacune).
// Le hasard : le jeu prend la place 0 de sa table de générateurs = mt19937 semé par l'heure du lancement du jeu ;
// on reproduit l'ALGORITHME et la loi de hasard (un tirage précis d'une partie du jeu n'est pas reproductible, même en jeu).
"use strict";
(function (racine) {
  const F = Math.fround, PI = F(Math.PI), DEUXPI = F(6.2831854820251465), INV2PI = F(0.15915493667125702);
  // (14/11/2026) TEINTE choisie dans l'Atelier (sommets / particules) : opération « set » de VRFW (hue + colorize,
  // saturation = valeur = 1). (15/11/2026) LU dans VRFW (winmm.dll, FUN_1827bccd0, exécutée dans l'émulateur :
  // nie_outils/emu_vrfw.py, 2 000 couleurs, écart 4e-7) : s = (max - min) / max ; s < 0,08 (seuil des gris, constante
  // 0x3da3d70a) -> inchangé si colorize = 0, sinon s = max(s, colorize) ; teinte -> H ; valeur gardée (pas de plafond à 1).
  // Avant : saturation au moins C pour TOUTES les couleurs (les couleurs pâles sortaient trop vives).
  // Même formule : AtelierNatif/src/animation.h (teinter_hsv), AtelierD3D/rendu_image.py.
  function teinterHSV(c, H, C) {
    const v = Math.max(c[0], c[1], c[2]), mn = Math.min(c[0], c[1], c[2]);
    if (!(v > 0)) return c;
    let s = (v - mn) / v;
    if (s < 0.08) { if (!(C > 0)) return c; s = Math.max(s, C); }
    s = Math.min(1, s);
    let h = H % 360; if (h < 0) h += 360; h /= 60; const i = Math.floor(h) % 6, f = h - Math.floor(h);
    const p = v * (1 - s), q = v * (1 - s * f), t = v * (1 - s * (1 - f));
    const r = [[v, t, p], [q, v, p], [p, v, t], [p, q, v], [t, p, v], [v, p, q]][i];
    c[0] = r[0]; c[1] = r[1]; c[2] = r[2]; return c;
  }
  racine.teinterHSV = teinterHSV;

  // ------------------------------------------------------------------ hasard : mt19937 (CRand du jeu)
  class MT19937 {
    constructor(graine) { this.mt = new Uint32Array(624); this.i = 625; this.semer(graine >>> 0); }
    semer(s) { const mt = this.mt; mt[0] = s >>> 0;
      for (let i = 1; i < 624; i++) { const p = mt[i - 1] ^ (mt[i - 1] >>> 30); mt[i] = (Math.imul(1812433253, p) + i) >>> 0; } this.i = 624; }
    u32() { const mt = this.mt;
      if (this.i >= 624) { for (let k = 0; k < 624; k++) { const y = (mt[k] & 0x80000000) | (mt[(k + 1) % 624] & 0x7fffffff);
        mt[k] = mt[(k + 397) % 624] ^ (y >>> 1) ^ ((y & 1) ? 0x9908b0df : 0); } this.i = 0; }
      let y = mt[this.i++]; y ^= y >>> 11; y ^= (y << 7) & 0x9d2c5680; y ^= (y << 15) & 0xefc60000; y ^= y >>> 18; return y >>> 0; }
    f() { return F(this.u32() * 2.3283064365386963e-10); }       // tirage × 2^-32 (méthode +0x28)
    n(max) { return max ? this.u32() % max : 0; }                 // entier < max (méthode +0x20)
  }
  // hasard imposé (banc d'essai) : suite de nombres
  class Suite { constructor(v) { this.v = v; this.k = 0; } f() { const x = this.v[this.k % this.v.length]; this.k++; return F(x); }
    n(max) { const x = this.v[this.k % this.v.length]; this.k++; return max ? (Math.floor(x * max) % max) : 0; } }

  // ------------------------------------------------------------------ courbes (0x140549fa0 ; 3 composantes : 0x1402adda0)
  function courbe(c, t, defaut) {
    if (!c || !c.t || !c.t.length) return defaut;
    const T = c.t, V = c.v, n = T.length; let k = 0;
    while (k < n && !(t < T[k])) k++;
    if (k === 0) return V[0];
    if (k >= n) return V[n - 1];
    const a = T[k - 1], d = F(T[k] - a), u = d <= 0 ? 0 : F(F(t - a) / d);
    if (Array.isArray(V[0])) return V[k].map((x, j) => F(F(F(x - V[k - 1][j]) * u) + V[k - 1][j]));
    return F(F(F(V[k] - V[k - 1]) * u) + V[k - 1]);
  }

  // ------------------------------------------------------------------ outils 3D (quaternions x, y, z, w)
  // angles -> quaternion (0x140489ce0, vérifié dans l'émulateur) : q = qx(ax) ⊗ qy(ay) ⊗ qz(az)
  function qmul(a, b) { return [F(a[3] * b[0] + a[0] * b[3] + a[1] * b[2] - a[2] * b[1]), F(a[3] * b[1] - a[0] * b[2] + a[1] * b[3] + a[2] * b[0]),
    F(a[3] * b[2] + a[0] * b[1] - a[1] * b[0] + a[2] * b[3]), F(a[3] * b[3] - a[0] * b[0] - a[1] * b[1] - a[2] * b[2])]; }
  function qaxe(i, a) { const s = F(Math.sin(a / 2)), q = [0, 0, 0, F(Math.cos(a / 2))]; q[i] = s; return q; }
  function quatAngles(x, y, z) { return qmul(qmul(qaxe(0, x), qaxe(1, y)), qaxe(2, z)); }
  function quatMat(q) {   // matrice 3x3 (lignes) d'un quaternion
    const [x, y, z, w] = q, s = 2 / (x * x + y * y + z * z + w * w || 1);
    return [[1 - s * (y * y + z * z), s * (x * y - w * z), s * (x * z + w * y)], [s * (x * y + w * z), 1 - s * (x * x + z * z), s * (y * z - w * x)],
      [s * (x * z - w * y), s * (y * z + w * x), 1 - s * (x * x + y * y)]]; }
  function matQuat(m) {   // 3x3 (lignes) -> quaternion
    const t = m[0][0] + m[1][1] + m[2][2]; let x, y, z, w;
    if (t > 0) { const s = Math.sqrt(t + 1) * 2; w = s / 4; x = (m[2][1] - m[1][2]) / s; y = (m[0][2] - m[2][0]) / s; z = (m[1][0] - m[0][1]) / s; }
    else if (m[0][0] > m[1][1] && m[0][0] > m[2][2]) { const s = Math.sqrt(1 + m[0][0] - m[1][1] - m[2][2]) * 2; w = (m[2][1] - m[1][2]) / s; x = s / 4; y = (m[0][1] + m[1][0]) / s; z = (m[0][2] + m[2][0]) / s; }
    else if (m[1][1] > m[2][2]) { const s = Math.sqrt(1 + m[1][1] - m[0][0] - m[2][2]) * 2; w = (m[0][2] - m[2][0]) / s; x = (m[0][1] + m[1][0]) / s; y = s / 4; z = (m[1][2] + m[2][1]) / s; }
    else { const s = Math.sqrt(1 + m[2][2] - m[0][0] - m[1][1]) * 2; w = (m[1][0] - m[0][1]) / s; x = (m[0][2] + m[2][0]) / s; y = (m[1][2] + m[2][1]) / s; z = s / 4; }
    return [F(x), F(y), F(z), F(w)]; }
  const rx = (a, v) => { const c = Math.cos(a), s = Math.sin(a); return [v[0], c * v[1] - s * v[2], s * v[1] + c * v[2]]; };
  const ry = (a, v) => { const c = Math.cos(a), s = Math.sin(a); return [c * v[0] + s * v[2], v[1], -s * v[0] + c * v[2]]; };
  const rz = (a, v) => { const c = Math.cos(a), s = Math.sin(a); return [c * v[0] - s * v[1], s * v[0] + c * v[1], v[2]]; };
  // direction au hasard (0x1405ccc20, vérifié) : 3 angles dans [−π, π], v = Rz(c)·Ry(b)·Rx(a)·(0, 1, 0)
  function dirHasard(R) { const a = F(F(R.f() * DEUXPI) - PI), b = F(F(R.f() * DEUXPI) - PI), c = F(F(R.f() * DEUXPI) - PI);
    return rz(c, ry(b, rx(a, [0, 1, 0]))).map(F); }
  // angle ramené dans [−π, π] (comme le jeu : troncature vers zéro)
  function ramener(a) { const s = a < 0 ? -PI : PI, b = F(a + s); return F(b - F(F(Math.trunc(F(b * INV2PI)) * DEUXPI) + s)); }
  // M (3 lignes de 4 : rotation | translation) x (v, w)
  const app = (M, v, w) => [0, 1, 2].map(i => F(M[i][0] * v[0] + M[i][1] * v[1] + M[i][2] * v[2] + M[i][3] * w));
  const nrm = v => { const l = Math.hypot(v[0], v[1], v[2]); return l > 0 ? v.map(x => F(x / l)) : v.slice(); };

  // ------------------------------------------------------------------ courbe du trajet (mode d'émission 1)
  // normalisation du jeu : (0, 0, 0) si longueur² <= 0 ou infinie
  function nrmJ(v) { const s = F(F(F(v[0] * v[0]) + F(v[1] * v[1])) + F(v[2] * v[2]));
    if (!(s > 0) || !isFinite(s)) return [0, 0, 0]; const l = F(Math.sqrt(s)); return v.map(x => F(x / l)); }
  const sous = (a, b) => [F(a[0] - b[0]), F(a[1] - b[1]), F(a[2] - b[2])];
  const croixJ = (a, b) => [F(F(a[1] * b[2]) - F(a[2] * b[1])), F(F(a[2] * b[0]) - F(a[0] * b[2])), F(F(a[0] * b[1]) - F(a[1] * b[0]))];
  // tangente d'un point intérieur (0x1404cfe70) : a, b = directions vers le précédent et le suivant ;
  // si |a + b| > 0,001 : c = norm(a x b), tangente = c x norm(a + b) ; sinon tangente = b
  function tangenteInt(prec, cur, suiv) { const a = nrmJ(sous(prec, cur)), b = nrmJ(sous(suiv, cur)), s = [F(a[0] + b[0]), F(a[1] + b[1]), F(a[2] + b[2])];
    const l = F(Math.sqrt(F(F(F(s[0] * s[0]) + F(s[1] * s[1])) + F(s[2] * s[2]))));
    if (l !== 0 && F(0.001) < l) { const inv = F(1 / l), bi = s.map(x => F(inv * x)), c = nrmJ(croixJ(a, b)); return croixJ(c, bi); }
    return b; }
  // tangentes des N points (0x1404cffe0) rangées dans H[100 + 4i] ; extrémités : (3 t − t voisine) x 0,5
  function tangentes(H, P, N) { const T = [];
    for (let i = 0; i < N; i++) T.push(i === 0 ? nrmJ(sous(P[1], P[0])) : i === N - 1 ? nrmJ(sous(P[i], P[i - 1])) : tangenteInt(P[i - 1], P[i], P[i + 1]));
    T[0] = T[0].map((x, k) => F(F(F(x * 3) - T[1][k]) * F(0.5)));
    T[N - 1] = T[N - 1].map((x, k) => F(F(F(x * 3) - T[N - 2][k]) * F(0.5)));
    for (let i = 0; i < N; i++) for (let k = 0; k < 3; k++) H[100 + 4 * i + k] = T[i][k]; }
  // point du trajet (0x140549a80) : t = fraction de la longueur (depuis le point « départ » s) ; segment trouvé par longueurs
  // cumulées, puis Hermite cubique entre P[u] et P[u + 1], tangentes x longueur du segment ; hors trajet : (0, 0, 0)
  function hermite(H, P, s, n, reste, t) { let cum = 0, f = 0, fp = 0, u = 0;
    const inv = F(1 / reste);
    for (let k = 0; k < n; k++) { fp = f; cum = F(cum + H[132 + s + k]); f = F(inv * cum); if (t <= f) { u = k; break; } }
    if (!(u < n - 1 && F(f - fp) > 0)) return [0, 0, 0];
    const v = F(F(t - fp) / F(f - fp)), v2 = F(v * v), v3 = F(v * v2), L = H[132 + s + u], i0 = s + u, i1 = i0 + 1;
    return [0, 1, 2].map(k => { const p0 = P[i0][k], p1 = P[i1][k], a = F(H[100 + 4 * i0 + k] * L), b = F(H[100 + 4 * i1 + k] * L);
      const c2 = F(F(F(F(F(-3 * p0) - F(a + a)) + F(3 * p1)) - b)), c3 = F(F(F(F(2 * p0) + a) - F(2 * p1)) + b);
      return F(F(F(F(c2 * v2) + F(c3 * v3)) + F(v * a)) + p0); }); }

  // ------------------------------------------------------------------ une particule (0x120 octets dans le jeu)
  function nouvelleParticule() {
    return { q: [0, 0, 0, 1], w: [0, 0, 0], uv: [[0, 0, 0, 0], [0, 0, 0, 0], [0, 0, 0, 0]], col: [1, 1, 1, 1], pos: [0, 0, 0], monde: [0, 0, 0],
      vit: [0, 0, 0], t0: [1, 1, 1], taille: [0, 0, 0], tirT: [0, 0, 0], vitesse: 0, vyG: 0, tirC: 0, tirA: 0, vent: 0, ventK: 1, p104: 0,
      img0: [0, 0, 0], compteur: 0, age: 0, vie: 0, vivante: true, prec: null };
  }

  class Emetteur {
    // def : un émetteur lu par moteur/particules.py ; hasard : générateur (MT19937 par défaut)
    constructor(def, hasard) { this.d = def; this.R = hasard || new MT19937(0x1234567); this.max = this._maximum(); this.reset(); }
    // nombre maximal (CParticleController +0x68 = 0x14058f4e0)
    _maximum() { const E = this.d.emetteur, V = this.d.vie;
      if (E.mode !== 0) return E.max;
      let T = E.boucle ? Math.max(V.max, V.min) : F(E.fin + E.duree);
      if (V.k >= 1) T = F(T * V.k);
      return Math.min(E.max, Math.trunc(F(T * E.debit)) + 1); }
    // remise à zéro (0x1405b5ed0) : l'accumulateur est réglé pour émettre dès la 1re image
    reset() { this.t = 0; this.parts = []; this.fini = false; this.boucle = false; this.premier = false; this.arret = null;
      const c0 = F(courbe(this.d.emetteur.courbe, 0, 1) * this.d.emetteur.debit); this.acc = c0 > 0 ? F(1 / c0) : 0;
      // historique du mode « trajet » : dans le jeu, bloc de 0x250 octets (émetteur +0x268) mis à zéro à la création
      // (0x1405b538b) et PAS par la remise à zéro ; ici une remise à zéro = un émetteur neuf (une nouvelle lecture de l'effet)
      this.H = new Float32Array(148); this.hN = 0; this.hDep = 0; this.hImg = 0; this.hImgL = 0; this.hDrap = false; }

    // ---------------------------------------------------------------- mode d'émission 1 « trajet » (lu dans nie.exe le 13/11/2026)
    // Bloc d'historique H (index = octet / 4) : [4 + 12i] 8 matrices 3x4 (translation en 7 + 12i, 11 + 12i, 15 + 12i),
    // [100 + 4i] 8 tangentes, [132 + i] longueurs des segments, [140] longueur totale ; à part : nombre (+0x234), départ (+0x238),
    // corde (+0x23c = H[143]), image de la corde (+0x240), drapeau (+0x244), compteur d'images (+0).
    _hEcrire(i, M) { const H = this.H, b = 4 + 12 * i; for (let r = 0; r < 3; r++) for (let c = 0; c < 4; c++) H[b + 4 * r + c] = M[r][c]; }
    _hPoint(i) { const H = this.H; return [H[7 + 12 * i], H[11 + 12 * i], H[15 + 12 * i]]; }
    // mise à jour de l'historique (0x1405b5410, 0x1405b5850…58fa)
    _trajetMaj(M) { const H = this.H, n = this.hN;
      if (n > 0) {
        // le jeu compare la position à l'entrée n (pas n − 1) : encore à zéro tant que n < 8 ; à n = 8 il lit 3 octets plus loin
        // (composantes w des tangentes 0 à 2, des restes de pile dans le jeu : ici 0)
        const dx = F(H[12 * n + 7] - M[0][3]), dy = F(H[12 * n + 11] - M[1][3]), dz = F(H[12 * n + 15] - M[2][3]);
        if (!(F(F(F(dx * dx) + F(dy * dy)) + F(dz * dz)) > 0)) return;            // rien (et le compteur d'images ne bouge pas)
        if (n >= 8) {                                                               // plein : on décale (l'entrée 0 reste si départ = 0)
          for (let b = 0; b < 7; b++) if (b !== 0 || this.hDep !== 0) H.copyWithin(4 + 12 * b, 16 + 12 * b, 28 + 12 * b);
          this._hEcrire(7, M); if (this.hDep !== 0) this.hDep--;
        } else { this._hEcrire(n, M); this.hN++; }
      } else { this._hEcrire(0, M); this.hN = 1; }
      if (!this.hDrap) { this.hDep = 0; this.hDrap = true; }
      this.hImg++; }
    // corde (0x1405b6810) : distance entre le point de départ et le dernier point, recalculée une fois par image
    _corde() { const H = this.H, n = this.hN; if (n < 2) return 0;
      if (this.hImgL === this.hImg) return H[143];
      const a = this._hPoint(this.hDep), b = this._hPoint(n - 1), d = [0, 1, 2].map(k => F(b[k] - a[k]));
      this.hImgL = this.hImg; H[143] = F(Math.sqrt(F(F(F(d[0] * d[0]) + F(d[1] * d[1])) + F(d[2] * d[2])))); return H[143]; }
    // naissances le long du trajet (0x1405b60e0) puis l'entrée « départ » prend la matrice de la dernière née (0x1405b5ef0…)
    _naitreTrajet(n, M, q, vE, mult) { const H = this.H, E = this.d.emetteur, L = this._corde(), N = this.hN;
      if (!(L > 0)) return;
      if (N > 1) { H[140] = 0;                                                       // longueurs des segments
        for (let i = 0; i < N - 1; i++) { const a = this._hPoint(i), b = this._hPoint(i + 1), d = [0, 1, 2].map(k => F(b[k] - a[k]));
          H[132 + i] = F(Math.sqrt(F(F(F(d[0] * d[0]) + F(d[1] * d[1])) + F(d[2] * d[2])))); H[140] = F(H[132 + i] + H[140]); } }
      const P = []; for (let i = 0; i < 8; i++) P.push(this._hPoint(i));
      if (N > 2) tangentes(H, P, N);                                                // 0x1404cffe0
      const s = this.hDep, b0 = 4 + 12 * s, den = F(F(F(mult * E.debit)) * L); let Mi = null;
      for (let k = 0; k < n; k++) {
        const t = F((k + 1) / den);
        Mi = [0, 1, 2].map(r => [0, 1, 2, 3].map(c => F(F(t * F(M[r][c] - H[b0 + 4 * r + c])) + H[b0 + 4 * r + c])));
        let p = [0, 0, 0];                                                           // 0x1423afeb0 = (0, 0, 0, 0) (0x140024a00)
        if (N !== 0 && H[140] > 0 && 8 - s >= 2) {
          let somme = 0; for (let i = 0; i < s; i++) somme = F(somme + H[132 + i]);
          p = hermite(H, P, s, 8 - s, F(H[140] - somme), t); }                       // 0x140549a80
        Mi[0][3] = p[0]; Mi[1][3] = p[1]; Mi[2][3] = p[2];
        this.parts.push(this._naissance(Mi, q, vE, 0)); }
      if (N !== 0) { this.hDep = N - 1; this._hEcrire(N - 1, Mi); this.hImg++; } }
    get fin() { const E = this.d.emetteur; return F(F(E.fin + E.retard) + E.duree); }
    // arrêt demandé par un plan (MOTION_INFO, 2e liste) : délai puis le temps saute à la fin
    arreter(delai) { if (this.arret === null) this.arret = delai; }

    // ---------------------------------------------------------------- une image (0x1405b5410 puis 0x1405b5d0c)
    // M : matrice du nœud (3 lignes de 4, rotation sans échelle | translation), q : sa rotation, ech : son échelle [x, y, z]
    pas(dt, M, q, ech, actif, vitesseEffet) {
      dt = F(dt); const E = this.d.emetteur, vE = vitesseEffet === undefined ? 1 : vitesseEffet;
      if (this.fini || !(dt > 0)) return;
      if (this.arret !== null) { this.arret = F(this.arret - dt); if (this.arret <= 0 && this.t < this.fin) this.t = this.fin; }
      const fin = this.fin;
      if (fin <= this.t) { if (!this.parts.length) { this.fini = true; return; } }
      else { this.t = F(this.t + dt);
        if (fin <= this.t) { if (!E.boucle || !actif) this.t = fin; else { this.t = F(this.t - E.duree); this.boucle = true; } } }
      if (!actif && E.figer) return;
      const pret = E.retard <= this.t;
      let emettre = actif && this.t < fin && pret;
      if (!this.premier && actif && pret) { emettre = true; this.premier = true; }
      const mult = fin > 0 ? F(courbe(E.courbe, F(this.t / fin), 1) * vE) : 1;
      const echelle = E.sansEchelle ? [1, 1, 1] : ech;
      if (E.mode === 1) this._trajetMaj(M);          // historique du trajet, à chaque image (0x1405b5410, avant le comptage)
      if (emettre) { let n = this._nombre(dt, mult); n = Math.min(n, this.max - this.parts.length);
        if (E.mode === 1) { if (n > 0) this._naitreTrajet(n, M, q, vE, mult); }
        else for (let k = 0; k < n; k++) this.parts.push(this._naissance(M, q, vE, 0)); }
      // vent dirigé (0x14054c7b0, WIND_INFO force > 0) : force x (matrice de l'émetteur x (direction, 1)) ;
      // vent du monde (WIND_INFO[0]) : TOUJOURS NUL dans ce jeu (game::CParticleController +0x38 = 0x140f00460 renvoie 0)
      const W = this.d.vent; let vent = null;
      if (W.force > 0) { const dd = W.dir; vent = [0, 1, 2].map(i => F(W.force * F(F(F(F(M[i][0] * dd[0]) + F(M[i][1] * dd[1])) + F(M[i][2] * dd[2])) + M[i][3]))); }
      for (const p of this.parts) this._maj(p, dt, M, echelle, vent);
      this.parts = this.parts.filter(p => p.age < p.vie);
    }
    // nombre à émettre (0x1405b6020) : mode 0 = débit dans le temps ; mode 1 = « trajet » : (int)(corde x débit x mult)
    _nombre(dt, mult) { const E = this.d.emetteur, r = F(E.debit * mult);
      if (!(E.debit > 0) || !(mult > 0)) return 0;
      if (E.mode === 1) return Math.trunc(F(F(this._corde() * E.debit) * mult));
      if (E.mode !== 0) return 0;
      this.acc = F(this.acc + dt); const seuil = F(1 / r);
      if (seuil <= this.acc) { const n = Math.trunc(F(this.acc * r)); this.acc = seuil < this.acc ? F(this.acc % seuil) : 0; return n; }
      return 0; }

    // ---------------------------------------------------------------- naissance (0x1405cb1d0 + forme 0x1405cc4b0)
    _naissance(M, qEm, vE, p6) {
      const d = this.d, R = this.R, p = nouvelleParticule(), S = d.forme, loc = d.emetteur.local !== 0;
      // forme : position (p.pos) et direction (p.vit)
      let d1 = null, d2 = null, cs = [0, 0];
      if (S.type === 0 || S.type === 1) { d1 = dirHasard(R); if (S.type === 1 && d1[1] < 0) d1[1] = -d1[1];
        if (S.dirHasard) { d2 = dirHasard(R); if (S.type === 1 && d2[1] < 0) d2[1] = -d2[1]; } }
      else if (S.type === 2) { const a = F(F(R.f() * DEUXPI) - PI); cs = [F(Math.sin(a)), F(Math.cos(a))]; }
      let rr = 1;
      if (S.type === 0 || S.type === 1) { if (!S.coque) rr = R.f();
        const dp = S.dirHasard ? d2 : d1; p.pos = dp.map(x => F(F(S.rayon * x) * rr)); if (!loc) p.pos = app(M, p.pos, 1); }
      else if (S.type === 2) { let r = S.rayon; if (!S.coque) { rr = R.f(); r = F(r * rr); }
        p.pos = [F(r * cs[1]), 0, F(r * cs[0])]; if (!loc) p.pos = app(M, p.pos, 1); }
      else p.pos = [M[0][3], M[1][3], M[2][3]];
      if (S.type === 0 || S.type === 1) { if (S.dirHasard) p.vit = d1.slice(); else p.vit = loc ? d1.slice() : app(M, d1, 0); }
      else if (S.type === 2) {
        if (!S.dirHasard) { const ph = F(S.angle * rr), sp = F(Math.sin(ph)), cp = F(Math.cos(ph));   // cône d'angle S.angle (× le tirage du rayon)
          p.vit = [F(sp * cs[1]), cp, F(sp * cs[0])]; }
        else { const a = F(F(F(S.angle + S.angle) * R.f()) - S.angle), b = F(F(F(S.angle + S.angle) * R.f()) - S.angle);   // cône (vérifié)
          p.vit = rz(b, rx(a, [0, 1, 0])).map(F); }
        if (!loc) p.vit = app(M, p.vit, 0); }
      else p.vit = [0, 1, 0];
      p.vit = nrm(p.vit);
      p.vitesse = d.vitesse.min; if (d.vitesse.hasard) p.vitesse = F(F(F(d.vitesse.max - d.vitesse.min) * R.f()) + p.vitesse);
      if (!d.vitesse.courbe) p.vit = p.vit.map(x => F(x * p.vitesse));
      // durée de vie
      let vie = d.vie.min; if (d.vie.hasard) vie = F(F(F(d.vie.max - d.vie.min) * R.f()) + vie);
      p.vie = F(vie * vE); p.age = 0; p.col = [1, 1, 1, 1];
      if (d.couleur.hasardA) p.tirA = R.f();
      if (d.couleur.hasardC) p.tirC = R.f();
      const T = d.taille; p.t0 = T.min.slice();
      if (T.hasard) { if (!T.unTirage) for (let k = 0; k < 3; k++) p.t0[k] = F(F(F(T.max[k] - T.min[k]) * R.f()) + p.t0[k]);
        else { const r = R.f(); p.t0 = [0, 1, 2].map(k => F(F(r * F(T.max[k] - T.min[k])) + T.min[k])); } }
      if (T.deux) { if (!T.unTirage) p.tirT = [R.f(), R.f(), R.f()]; else { const r = R.f(); p.tirT = [r, r, r]; } }
      p.p104 = p6;
      const W = d.vent;
      if (W.actif || W.force > 0) { p.vent = W.min; if (W.hasard) p.vent = F(F(R.f() * F(W.max - W.min)) + p.vent);
        if (W.actif) p.ventK = F(F(R.f() * F(0.6)) + F(0.4)); }
      // rotation
      const Ro = d.rotation; let a = [0, 0, 0];
      if (!d.modele.suitVitesse) { a = Ro.a0.slice(); if (Ro.suitEmetteur) p.q = qEm ? qEm.slice() : matQuat(M); }
      else { const v = p.vit, l = Math.hypot(v[0], v[1], v[2]); p.q = l > 0 ? versDirection(v.map(x => x / l)) : [0, 0, 0, 1]; }
      if (Ro.hasardA) { const r = R.f(); a = [0, 1, 2].map(k => F(F(r * F(Ro.a1[k] - Ro.a0[k])) + a[k])); }
      a = a.map(ramener);
      let w = Ro.v0.slice();
      if (Ro.hasardV) { const r = R.f(); w = [0, 1, 2].map(k => F(F(r * F(Ro.v1[k] - Ro.v0[k])) + Ro.v0[k])); }
      if (Ro.signe) for (let k = 0; k < 3; k++) if ((a[k] > 0 && w[k] < 0) || (a[k] < 0 && w[k] > 0)) w[k] = -w[k];
      if (!d.modele.suitVitesse && !Ro.suitEmetteur) { p.q = quatAngles(a[0], a[1], a[2]); p.w = w; }
      // couches de texture
      d.uv.forEach((u, i) => { if (i > 2) return;
        let z = u.rep[0] === 0 ? 0 : F(1 / u.rep[0]), ww = u.rep[1] === 0 ? 0 : F(1 / u.rep[1]);
        if (u.defil) { z = F(z / u.facteur); ww = F(ww / u.facteur); }
        p.uv[i] = [u.dec[0], u.dec[1], z, ww];
        if (u.depHasard) { const tot = u.col * u.lig, n = R.n(tot);
          p.img0[i] = u.mode === 1 ? F(n / tot) : u.mode === 2 ? F(n / p.vie) : u.mode === 3 ? n : 0; } });
      p.prec = p.pos.slice();
      return p;
    }

    // ---------------------------------------------------------------- mise à jour d'une particule (0x1405cbb90)
    _maj(p, dt, M, ech, vent) {
      const d = this.d; let dtm = dt;
      p.age = F(p.age + dt); let t = F(p.age / p.vie);
      if (F(p.vie - p.age) < 0) { dtm = F(F(p.vie - p.age) + dt); p.age = p.vie; t = 1; }
      if (d.uv.some(u => u.mode === 3)) p.compteur = F(F(dt * 60) + p.compteur);
      if (p.vie !== 0) {
        const C = d.couleur; let c = courbe(C.rgb, t, [1, 1, 1]);
        if (C.hasardC && C.rgb2) { const c2 = courbe(C.rgb2, t, [1, 1, 1]); c = c.map((x, k) => F(F(F(c2[k] - x) * p.tirC) + x)); }
        let al = F(1 - courbe(C.alpha, t, 0));
        if (C.hasardA && C.alpha2) al = F(F(F(F(1 - courbe(C.alpha2, t, 0)) - al) * p.tirA) + al);
        p.col = [c[0], c[1], c[2], al];       // (× opacité générale de l'effet : appliquée au dessin)
        const T = d.taille; let s = courbe(T.courbe, t, [1, 1, 1]); const g = F(t * p.p104);
        s = s.map(x => F(F(g * x) + x));
        if (T.deux && T.courbe2) { const s2 = courbe(T.courbe2, t, [1, 1, 1]); s = s.map((x, k) => F(F(F(s2[k] - x) * p.tirT[k]) + x)); }
        if (T.parAxe === 0) s = [s[0], s[0], s[0]];
        p.taille = s;
      }
      // couches de texture : défilement et animation par cases
      d.uv.forEach((u, i) => { if (i > 2) return;
        if (u.defil) { const v = courbe(u.defil, t, [0, 0]); p.uv[i][0] = F(v[0] * u.facteur); p.uv[i][1] = F(v[1] * u.facteur); }
        if (u.mode) { let x = u.mode === 1 ? p.age : u.mode === 2 ? t : u.mode === 3 ? p.compteur : 0;
          if (u.depHasard) x = F(x + p.img0[i]);
          const tot = u.col * u.lig; let n;
          if (u.mode === 1 || u.mode === 2) n = Math.trunc(F(F(F(x % u.invVit) / u.invVit) * tot));
          else if (u.mode === 3) n = Math.trunc(x) % tot;
          else { p.uv[i] = [0, 0, 1, 1]; return; }
          const c1 = F(1 / u.col), l1 = F(1 / u.lig);
          p.uv[i] = [F((n % u.col) * c1), F(F(Math.floor(n / u.col) + 1) * l1), c1, l1]; } });
      // mouvement (r = échelle de l'émetteur, g = gravité)
      const g = d.force.gravite, V = d.vitesse, ancien = p.pos.slice();
      if (!V.courbe) { if (g !== 0) p.vit[1] = F(p.vit[1] - F(g * dtm));
        for (let k = 0; k < 3; k++) p.pos[k] = F(F(F(p.vit[k] * ech[k]) * dtm) + p.pos[k]); }
      else if (g !== 0) { const cv = F(courbe(V.courbe, t, 1) * p.vitesse); const v4 = p.vit.map(x => F(cv * x));
        p.vyG = F(p.vyG - F(dtm * g));
        for (let k = 0; k < 3; k++) p.pos[k] = F(F(F(v4[k] * ech[k]) * dtm) + p.pos[k]);
        p.pos[1] = F(F(F(p.vyG * ech[1]) * dtm) + p.pos[1]);
        p.vit = v4; const l = Math.hypot(v4[0], v4[1], v4[2]); if (l > 0) p.vit = v4.map(x => F(x / F(l))); }
      else { const cv = F(F(courbe(V.courbe, t, 1) * p.vitesse) * dtm);
        for (let k = 0; k < 3; k++) p.pos[k] = F(F(cv * F(p.vit[k] * ech[k])) + p.pos[k]); }
      // VENT (0x1405cbb90 après le mouvement) : émetteur dans le monde, particule.vent > 0 (« masse »), x courbe(t) ;
      // position += vent dirigé / masse x dtm (vérifié dans l'émulateur : 21 / 21 émetteurs à vent, et 8 / 8 avec une force imposée)
      { const W = d.vent; let s = p.vent;
        if (s > 0 && (W.actif || W.force > 0) && d.emetteur.local === 0) {
          if (W.courbe) s = F(courbe(W.courbe, t, 1) * s);
          if (s > 0 && vent) { const k = F(1 / s); for (let i = 0; i < 3; i++) p.pos[i] = F(F(F(k * vent[i]) * dtm) + p.pos[i]); } } }
      p.monde = d.emetteur.local !== 0 ? app(M, p.pos, 1) : p.pos.slice();
      if (d.modele.suitVitesse) { const pa = d.emetteur.local !== 0 ? app(M, ancien, 1) : ancien, dv = [0, 1, 2].map(k => p.monde[k] - pa[k]), l = Math.hypot(...dv);
        if (l > 0) p.q = versDirection(dv.map(x => x / l)); }
      else if (p.w[0] !== 0 || p.w[1] !== 0 || p.w[2] !== 0) p.q = qmul(p.q, quatAngles(F(p.w[0] * dtm), F(p.w[1] * dtm), F(p.w[2] * dtm)));
      p.prec = p.monde.slice();
    }

    // ---------------------------------------------------------------- dessin (0x1405b6720 puis 0x14059d900)
    // quadrilatères : {pos: Float32Array (x, y, z), col: Float32Array (r, g, b, a), uv: [Float32Array x3], n}
    // camRot : 3x3 (lignes) rotation caméra -> monde ; camPos : position de la caméra ; echObj : échelle de l'objet
    quads(camRot, camPos, echObj, opacite) {
      const d = this.d, Mo = d.modele, n = this.parts.length, pos = new Float32Array(n * 12), col = new Float32Array(n * 16);
      const uvs = [0, 1, 2].map(() => new Float32Array(n * 8)), nor = new Float32Array(n * 12), tan = new Float32Array(n * 12);
      const L = Mo.m0 === 0 ? Mo.larg : 1, H = Mo.m0 === 0 ? Mo.haut : 1;
      const COINS = [[-0.5, 0.5], [-0.5, -0.5], [0.5, 0.5], [0.5, -0.5]], TUV = [[0, 1], [0, 0], [1, 1], [1, 0]];
      let m = 0;
      // ORDRE DE DESSIN (0x14054d130, liste prête à la remise à zéro 0x1405b5ed0) : mélange additif / soustractif = ordre des
      // cases (sans effet visible) ; sinon liste chaînée, nouvelle particule en tête : MODEL_INFO[11] (+0x824) = 1 -> de la plus
      // ancienne à la plus récente (la plus récente dessinée par-dessus), 0 / 2 -> de la plus récente à la plus ancienne
      const liste = d.materiau.melange === 3 || d.materiau.melange === 4 || Mo.ordre === 1 ? this.parts : this.parts.slice().reverse();
      for (const p of liste) {
        const s = d.emetteur.sansEchelle ? p.taille.map((x, k) => F(p.t0[k] * x)) : p.taille.map((x, k) => F(F(p.t0[k] * x) * (echObj ? echObj[k] : 1)));
        const Rq = quatMat(p.q); let X, Y, Z;
        if (Mo.type === 1) { const A = [0, 1, 2].map(i => [0, 1, 2].map(j => camRot[i][0] * Rq[0][j] + camRot[i][1] * Rq[1][j] + camRot[i][2] * Rq[2][j]));
          X = [A[0][0], A[1][0], A[2][0]]; Y = [A[0][1], A[1][1], A[2][1]]; Z = [A[0][2], A[1][2], A[2][2]]; }
        else if (Mo.type === 2) { const y = [Rq[0][1], Rq[1][1], Rq[2][1]], vc = [camPos[0] - p.monde[0], camPos[1] - p.monde[1], camPos[2] - p.monde[2]];
          const x = [y[1] * vc[2] - y[2] * vc[1], y[2] * vc[0] - y[0] * vc[2], y[0] * vc[1] - y[1] * vc[0]], lx = Math.hypot(...x);
          if (lx > 0) { X = x.map(v => v / lx); Y = y; Z = [X[1] * Y[2] - X[2] * Y[1], X[2] * Y[0] - X[0] * Y[2], X[0] * Y[1] - X[1] * Y[0]]; }
          else { X = [1, 0, 0]; Y = [0, 1, 0]; Z = [0, 0, 1]; } }
        else { X = [Rq[0][0], Rq[1][0], Rq[2][0]]; Y = [Rq[0][1], Rq[1][1], Rq[2][1]]; Z = [Rq[0][2], Rq[1][2], Rq[2][2]]; }
        const sx = L * s[0], sy = H * s[1];
        const c = [p.col[0], p.col[1], p.col[2], p.col[3] * (opacite === undefined ? 1 : opacite)];
        if (this.teinte) teinterHSV(c, this.teinte[0], this.teinte[1]);      // (14/11/2026) teinte de l'Atelier
        for (let j = 0; j < 4; j++) { const [cx, cy] = COINS[j], o = (4 * m + j);
          for (let k = 0; k < 3; k++) pos[3 * o + k] = p.monde[k] + X[k] * cx * sx + Y[k] * cy * sy;
          // NORMAL (bit 0x20) = R x (0, 0, 1), TANGENT (bit 0x40) = R x (1, 0, 0), tables 0x141a7a5f0 / 0x141a7a5b0, R = repère du
          // quadrilatère sans la taille ; écrits seulement si la déclaration de sommets du shader les demande (0x140549c10)
          nor.set(Z, 3 * o); tan.set(X, 3 * o);
          col.set(c, 4 * o);
          for (let i = 0; i < 3; i++) { const u = i < d.uv.length ? p.uv[i] : [0, 0, 1, 1];   /* couche absente : (0, 0, 1, 1) au dessin (0x1405b6720) */ uvs[i][2 * o] = TUV[j][0] * u[2] + u[0]; uvs[i][2 * o + 1] = 1 - TUV[j][1] * u[3] + u[1]; } }
        m++;
      }
      return { pos, col, uv: uvs, nor, tan, n: m };
    }
  }
  // orientation qui amène l'axe (0, 1, 0) sur la direction v (0x1405cce60, vérifié : axe = (0,1,0) × v, angle = acos(v.y))
  function versDirection(v) { const ax = [v[2], 0, -v[0]], l = Math.hypot(ax[0], ax[1], ax[2]);
    if (l <= 0) return v[1] >= 0 ? [0, 0, 0, 1] : [1, 0, 0, 0];
    const a = Math.acos(Math.max(-1, Math.min(1, v[1]))), s = Math.sin(a / 2) / l;
    return [F(ax[0] * s), F(ax[1] * s), F(ax[2] * s), F(Math.cos(a / 2))]; }

  const api = { Emetteur, MT19937, Suite, courbe, quatAngles, quatMat, matQuat, dirHasard, ramener, tangentes, hermite };
  if (typeof module !== 'undefined' && module.exports) module.exports = api; else racine.Particules = api;
})(typeof window !== 'undefined' ? window : globalThis);
