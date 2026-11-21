// Lecteur de cinématique de l'Atelier Inazuma : rejoue les mouvements du jeu (squelettes G4SK + clips G4MT / G4VS / G4CM)
// pour les objets d'effet, le ballon et la caméra. Données : /api/anim (moteur/anim.py).
// Repère : chaque pièce d'effet est collée à l'os du même nom ; l'objet est accroché à point_eff/evp_eff01.
"use strict";
(function () {
  // ---------------------------------------------------------------- matrices 4x4 (colonnes, comme WebGL)
  const I = () => new Float32Array([1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1]);
  function mul(a, b) { const o = new Float32Array(16);
    for (let i = 0; i < 4; i++) for (let j = 0; j < 4; j++) { let s = 0; for (let k = 0; k < 4; k++) s += a[k * 4 + j] * b[i * 4 + k]; o[i * 4 + j] = s; } return o; }
  function trs(t, q, e) {   // position, quaternion xyzw, échelle -> T * R * S
    let [x, y, z, w] = q; const n = Math.hypot(x, y, z, w) || 1; x /= n; y /= n; z /= n; w /= n;
    const m = new Float32Array(16);
    m[0] = (1 - 2 * (y * y + z * z)) * e[0]; m[1] = (2 * (x * y + z * w)) * e[0]; m[2] = (2 * (x * z - y * w)) * e[0];
    m[4] = (2 * (x * y - z * w)) * e[1]; m[5] = (1 - 2 * (x * x + z * z)) * e[1]; m[6] = (2 * (y * z + x * w)) * e[1];
    m[8] = (2 * (x * z + y * w)) * e[2]; m[9] = (2 * (y * z - x * w)) * e[2]; m[10] = (1 - 2 * (x * x + y * y)) * e[2];
    m[12] = t[0]; m[13] = t[1]; m[14] = t[2]; m[15] = 1; return m;
  }
  function inverse(m) {     // inverse d'une matrice affine
    const a = m[0], b = m[1], c = m[2], d = m[4], e = m[5], f = m[6], g = m[8], h = m[9], i = m[10];
    const A = e * i - f * h, B = -(d * i - f * g), C = d * h - e * g, det = a * A + b * B + c * C || 1e-9;
    const o = new Float32Array(16);
    o[0] = A / det; o[1] = -(b * i - c * h) / det; o[2] = (b * f - c * e) / det;
    o[4] = B / det; o[5] = (a * i - c * g) / det; o[6] = -(a * f - c * d) / det;
    o[8] = C / det; o[9] = -(a * h - b * g) / det; o[10] = (a * e - b * d) / det;
    o[12] = -(m[12] * o[0] + m[13] * o[4] + m[14] * o[8]); o[13] = -(m[12] * o[1] + m[13] * o[5] + m[14] * o[9]);
    o[14] = -(m[12] * o[2] + m[13] * o[6] + m[14] * o[10]); o[15] = 1; return o;
  }

  // ---------------------------------------------------------------- échantillonnage d'un canal à l'image f (absolue dans le clip)
  function echantillon(ch, f) {
    const im = ch.images, v = ch.valeurs, n = im.length;
    if (n === 1 || f <= im[0]) return v[0];
    if (f >= im[n - 1]) return v[n - 1];
    let lo = 0, hi = n - 1;
    while (hi - lo > 1) { const m = (lo + hi) >> 1; if (im[m] <= f) lo = m; else hi = m; }
    if (!ch.interp) return v[lo];
    const t = (f - im[lo]) / (im[hi] - im[lo] || 1), a = v[lo], b = v[hi];
    if (ch.type === 9) {    // quaternion : chemin le plus court puis normalisation (nlerp)
      const d = a[0] * b[0] + a[1] * b[1] + a[2] * b[2] + a[3] * b[3], s = d < 0 ? -1 : 1;
      return [0, 1, 2, 3].map(k => a[k] * (1 - t) + s * b[k] * t);
    }
    return a.map((x, k) => x * (1 - t) + b[k] * t);
  }

  // ---------------------------------------------------------------- os « panneaux » (LU dans nie.exe 0x14052a200, 14/11/2026)
  // m : matrice monde de l'os (repère de l'objet) ; c : caméra dans le repère de l'objet (inverse(objet) x caméra -> monde).
  // Position et échelles (longueurs des colonnes) gardées ; orientation : 1 = axe Z vers la caméra (X = haut caméra x Z),
  // 2 = axe Y de l'os gardé (X = Y x direction), 3 = axes de la caméra (X et Z retournés). Vérifié dans l'émulateur.
  const F = Math.fround;
  function panneau(m, mode, c) {
    const d = [c[12] - m[12], c[13] - m[13], c[14] - m[14]], dd = d[0] * d[0] + d[1] * d[1] + d[2] * d[2];
    if (!(dd > 0) || !isFinite(dd)) return m;
    const s = [0, 1, 2].map(k => Math.sqrt(m[4 * k] * m[4 * k] + m[4 * k + 1] * m[4 * k + 1] + m[4 * k + 2] * m[4 * k + 2]));
    const nz = v => { const l = Math.sqrt(v[0] * v[0] + v[1] * v[1] + v[2] * v[2]); return [v[0] / l, v[1] / l, v[2] / l]; };
    const cr = (a, b) => [a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0]];
    const ok = v => { const q = v[0] * v[0] + v[1] * v[1] + v[2] * v[2]; return q > 0 && isFinite(q); };
    let X, Y, Z;
    if (mode === 3) { X = nz([-c[0], -c[1], -c[2]]); Y = nz([c[4], c[5], c[6]]); Z = nz([-c[8], -c[9], -c[10]]); }
    else if (mode === 2) { Y = nz([m[4], m[5], m[6]]); const x = cr(Y, d); if (!ok(x)) return m; X = nz(x); Z = nz(cr(X, Y)); }
    else { Z = nz(d); const x = cr(nz([c[4], c[5], c[6]]), Z); if (!ok(x)) return m; X = nz(x); Y = nz(cr(Z, X)); }
    const o = new Float32Array(m);
    for (let k = 0; k < 3; k++) { o[k] = X[k] * s[0]; o[4 + k] = Y[k] * s[1]; o[8 + k] = Z[k] * s[2]; }
    return o;
  }

  // ---------------------------------------------------------------- un squelette animé
  // opts : {nus : propriété NonUniformScale du modèle (objbin), g4sk : octet d'en-tête +0x22 du squelette}
  class Squelette {
    constructor(os, opts) {
      this.os = os; this.n = os.length; this.parCrc = {}; this.parNom = {};
      this.nus = !!(opts && opts.nus); this.g4sk = (opts && opts.g4sk) || 0;
      this.panneaux = (this.g4sk & 2) !== 0 && os.some(o => ((o.drap || 0) >> 1) & 15);
      os.forEach((o, i) => { this.parCrc[o.crc >>> 0] = i; this.parNom[o.nom] = i; });
      this.repos = os.map(o => ({ t: o.t.slice(), r: o.r.slice(), e: o.e.slice() }));
      this.monde = this.poser(null, 0);
      this.mondeRepos = this.monde.map(m => m.slice());
    }
    // clip : {debut, cibles:[{crc, canaux}]}, f = image absolue dans le clip ; vis : clip G4VS (type 15)
    // cam (os panneaux) : caméra dans le repère de l'objet, ou rien
    poser(clip, f, vis, cam) {
      const loc = this.repos.map(r => ({ t: r.t.slice(), r: r.r.slice(), e: r.e.slice() }));
      if (clip) for (const c of clip.cibles) {
        const i = this.parCrc[c.crc >>> 0]; if (i === undefined) continue; const L = loc[i];
        for (const ch of c.canaux) { const v = echantillon(ch, f), t = ch.type;
          if (t >= 1 && t <= 3) L.e[t - 1] = v[0]; else if (t === 9) L.r = v.slice(0, 4); else if (t >= 10 && t <= 12) L.t[t - 10] = v[0]; }
      }
      const cache = new Array(this.n).fill(false);
      if (vis) for (const c of vis.cibles) { const i = this.parCrc[c.crc >>> 0]; if (i === undefined) continue;
        for (const ch of c.canaux) if (ch.type === 15 && echantillon(ch, f)[0] < 0.5) cache[i] = true; }
      const monde = new Array(this.n); this.cache = new Array(this.n);
      for (let i = 0; i < this.n; i++) {
        const p = this.os[i].parent, m = trs(loc[i].t, loc[i].r, loc[i].e);
        if (p >= 0 && monde[p]) {
          // COMPENSATION D'ÉCHELLE (LU dans nie.exe 0x14052b100 -> 0x140529aa0, 14/11/2026) : modèle NonUniformScale et
          // échelle locale du parent différente de (1, 1, 1) -> l'enfant prend l'orientation du parent SANS son échelle
          // (colonnes du parent / échelle du parent), mais sa position passe par la matrice complète du parent
          const sp = loc[p].e;
          if (this.nus && (F(sp[0]) !== 1 || F(sp[1]) !== 1 || F(sp[2]) !== 1)) {
            const P = monde[p], A = new Float32Array(P);
            for (let j = 0; j < 3; j++) { const e = F(sp[j]), k = e !== 0 ? F(1 / e) : 0; for (let r = 0; r < 3; r++) A[4 * j + r] = F(P[4 * j + r] * k); }
            const M = mul(A, m);
            for (let r = 0; r < 3; r++) M[12 + r] = P[r] * m[12] + P[4 + r] * m[13] + P[8 + r] * m[14] + P[12 + r];
            monde[i] = M;
          } else monde[i] = mul(monde[p], m);
        } else monde[i] = m;
        // OS PANNEAUX : seulement avec le calcul 0x14052bfd0 (en-tête +0x22 bit 2), après la composition de l'os
        const md = ((this.os[i].drap || 0) >> 1) & 15;
        if (cam && md && (this.g4sk & 2)) monde[i] = panneau(monde[i], md, cam);
        this.cache[i] = cache[i] || (p >= 0 && this.cache[p]);
      }
      this.monde = monde; this.local = loc; return monde;
    }
  }

  // ---------------------------------------------------------------- le lecteur
  class Lecteur {
    constructor(donnees) {
      this.d = donnees; this.image = 0; this.joue = false; this.vitesse = 1;
      this.objets = {};
      for (const [act, o] of Object.entries(donnees.objets || {})) if (o.os && o.os.length) this.objets[act] = { sq: new Squelette(o.os, o), d: o };
      this.pe = donnees.point_eff ? new Squelette(donnees.point_eff.os) : null;
      this.balle = donnees.balle ? new Squelette(donnees.balle.os) : null;
      this.ps = donnees.point_s00 ? new Squelette(donnees.point_s00.os) : null;
      // joueurs (peau) : inverse du monde au repos de chaque os, calculé une fois
      this.joueurs = [];
      // squelettes « point » (accroches) et acteurs (joueur, esprit, objets, ballon) : tous avec os
      this.points = {};
      for (const [nom, pt] of Object.entries(donnees.points || {})) this.points[nom] = { sq: new Squelette(pt.os), d: pt };
      this.acteurs = (donnees.acteurs || []).map(a => { const sq = new Squelette(a.os, a); return { d: a, sq, invRepos: sq.mondeRepos.map(inverse) }; });
    }
    get duree() { return this.d.duree || 1; }
    // caméra du jeu -> matrice caméra vers monde (comme la vue de vue3d._boucle : X, Y avec le roulis, Z vers l'arrière)
    _cameraMonde(p, dans) {
      if (!this.d.camera || !p || !this.d.camera[p.nom]) return null;
      const cl = this.d.camera[p.nom], ch = {};
      for (const c of cl.cibles) for (const k of c.canaux) ch[k.type] = echantillon(k, cl.debut + dans)[0];
      if (!(22 in ch && 26 in ch)) return null;
      const oe = [ch[22], ch[23], ch[24]], ci = [ch[26], ch[27], ch[28]], r = -(ch[30] || 0); /* (14/11/2026) roulis du canal 30 de SENS OPPOSÉ à notre vue : LU nie.exe 0x1404c7420 (quaternion de la caméra, émulé) */
      const nm = v => { const l = Math.hypot(v[0], v[1], v[2]) || 1; return [v[0] / l, v[1] / l, v[2] / l]; };
      const cr = (a, b) => [a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0]];
      const z = nm([oe[0] - ci[0], oe[1] - ci[1], oe[2] - ci[2]]), x = nm(cr([0, 1, 0], z)), y = cr(z, x);
      const c = Math.cos(r), s = Math.sin(r), x2 = [0, 1, 2].map(k => x[k] * c + y[k] * s), y2 = [0, 1, 2].map(k => y[k] * c - x[k] * s);
      return new Float32Array([x2[0], x2[1], x2[2], 0, y2[0], y2[1], y2[2], 0, z[0], z[1], z[2], 0, oe[0], oe[1], oe[2], 1]);
    }
    plan(f) { const ps = this.d.plans; for (const p of ps) if (f >= p.debut && f < p.fin) return p; return ps[ps.length - 1] || null; }
    // l'ordre en cours d'un objet à l'image f : clip joué (et depuis quand), visible, accroche
    _etat(o, f) {
      // (21/11) SANS commande d'accroche (0xA2D1F942) : PAS d'accroche, l'objet reste dans le repère de la cinématique. LU nie.exe :
      // seul le gestionnaire de cette commande (0x140f3afd0) rattache un objet à un parent (0x1418161a0), aucun code ne nomme
      // point_eff. Avant : accroché d'office à point_eff/evp_eff01 (déduit le 13/11) -> 38 cinématiques décalées (Bouclier royal :
      // cercle 5 m devant le gardien, os point_eff_Ex = +5 au plan c0400). 4 650 effets du jeu ont, eux, la commande explicite.
      let jouer = null, depuis = 0, visible = false, acc = ['', ''], boucle = false;
      for (const x of o.d.ordres) { if (x.image > f) break;
        if (x.jouer) { jouer = x.jouer; depuis = x.image; boucle = !!x.boucle; } if ('visible' in x) visible = x.visible; if (x.accroche) acc = x.accroche; }
      return { jouer, depuis, visible, acc, boucle };
    }
    // calcule tout pour l'image f ; renvoie {camera, objets: {acteur: {monde, cache, visible, racine}}, balle}
    calculer(f) {
      const p = this.plan(f), dans = p ? f - p.debut : f, res = { plan: p, objets: {} };
      // gardiens (ev63) : caméra dans le repère du terrain -> points d'accroche posés au but (anim.decalage_gardien)
      const D = this.d.decalage_points, TD = D ? new Float32Array([1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, D[0], D[1], D[2], 1]) : null;
      const dep = m => TD ? mul(TD, m) : m;
      const DE = this.d.decalage_eff, TE = DE ? new Float32Array([1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, DE[0], DE[1], DE[2], 1]) : null;
      const depE = m => TE ? mul(TE, dep(m)) : dep(m);
      // point d'accroche
      let racine = { evp_eff01: depE(I()) };
      if (this.pe && p && this.d.point_eff.clips[p.nom]) { const cl = this.d.point_eff.clips[p.nom];
        const m = this.pe.poser(cl, cl.debut + dans); racine = {};
        for (const [nom, i] of Object.entries(this.pe.parNom)) racine[nom] = depE(m[i]); }
      for (const [act, o] of Object.entries(this.objets)) {
        const e = this._etat(o, f); const cl = e.jouer && o.d.clips[e.jouer];
        // temps du clip à SA vitesse (le plus souvent 60 images/s ; 30 pour quelques effets communs comme les traits ega0001)
        const ec = cl ? (f - e.depuis) * (cl.fps || 60) / 60 : 0;
        const t = cl ? cl.debut + (e.boucle ? ec % (cl.fin - cl.debut + 1) : ec) : 0;
        const monde = o.sq.poser(cl || null, t, cl && o.d.vis[e.jouer]);
        o._pose = [cl || null, t, cl && o.d.vis[e.jouer]];
        // opacité de chaque matériau (crc32 de son nom) à cet instant
        // + paramètres des shaders : G4MA 32-35 = u_shaderParam[octet 7].xyzw -> prm[crc] = [[n°, composante, valeur], …]
        // + couleurs (14/11/2026) : G4MA 16-19 = couleur[octet 7].rgba (0 = u_diffuse, 1 = u_ambient) -> col[crc] = [[n°, composante, valeur], …]
        const opa = {}, prm = {}, col = {}, co = cl && o.d.opa && o.d.opa[e.jouer];
        if (co) for (const c of co.cibles) for (const ch of c.canaux) { const v = echantillon(ch, t)[0];
          if (ch.type === 19 && !(ch.prm || 0)) opa[c.crc >>> 0] = Math.max(0, Math.min(1, v));
          else if (ch.type >= 16 && ch.type <= 19) (col[c.crc >>> 0] = col[c.crc >>> 0] || []).push([ch.prm || 0, ch.type - 16, v]);
          else if (ch.type >= 32 && ch.type <= 35) (prm[c.crc >>> 0] = prm[c.crc >>> 0] || []).push([ch.prm || 0, ch.type - 32, v]); }
        // défilement des textures : [échelle u, échelle v, décalage u, décalage v] par crc32('<matériau>_tex<n>')
        const uv = {}, uvc = {}, cu = cl && o.d.uv && o.d.uv[e.jouer];
        if (cu) for (const c of cu.cibles) { const x = [1, 1, 0, 0], brut = {};
          for (const ch of c.canaux) { const v = echantillon(ch, t)[0]; brut[ch.type] = v;
            if (ch.type === 1) x[0] = v; else if (ch.type === 2) x[1] = v; else if (ch.type === 10) x[2] = v; else if (ch.type === 11) x[3] = v; }
          // même règle que le jeu : décalage u compté à l'envers, v depuis le bas (voir vue3d, matrices u_texProj)
          uv[c.crc >>> 0] = [x[0], x[1], -x[0] * x[2], 1 - x[1] + x[1] * x[3]]; uvc[c.crc >>> 0] = brut; }
        res.objets[act] = { monde, cache: o.sq.cache, visible: e.visible && !!cl, racine: racine[e.acc[1]] || I(), sq: o.sq, opa, prm, col, uv, uvc,
          clip: e.jouer, depuis: e.depuis, local: o.sq.local };   // (plan joué : émetteurs de particules, MOTION_INFO ; local = t, r, e des os : lumières ponctuelles)
      }
      // point d'accroche des personnages et du ballon
      let rps = {};
      if (this.ps && p && this.d.point_s00.clips[p.nom]) { const cl = this.d.point_s00.clips[p.nom];
        const m = this.ps.poser(cl, cl.debut + dans); for (const [nom, i] of Object.entries(this.ps.parNom)) rps[nom] = dep(m[i]); }
      if (this.balle && p && this.d.balle.clips[p.nom]) { const cl = this.d.balle.clips[p.nom];
        const m = this.balle.poser(cl, cl.debut + dans), i = this.balle.parNom[this.d.balle.os_balle];
        const rac = rps[this.d.balle.accroche] || I();
        res.balle = i !== undefined ? mul(rac, mul(m[i], inverse(this.balle.mondeRepos[i]))) : null; }
      // caméra -> matrice « caméra vers monde » (pour les effets collés à la caméra)
      if (this.d.camera && p && this.d.camera[p.nom]) { const cl = this.d.camera[p.nom], ch = {};
        for (const c of cl.cibles) for (const k of c.canaux) ch[k.type] = echantillon(k, cl.debut + dans)[0];
        if (22 in ch && 26 in ch) { const o = [ch[22], ch[23], ch[24]], c = [ch[26], ch[27], ch[28]], r = -(ch[30] || 0); /* (14/11/2026) roulis du canal 30 de SENS OPPOSÉ à notre vue : LU nie.exe 0x1404c7420 (quaternion de la caméra, émulé) */
          const nz = (v => { const l = Math.hypot(...v) || 1; return v.map(x => x / l); });
          const z = nz([o[0] - c[0], o[1] - c[1], o[2] - c[2]]); let x = nz([z[2], 0, -z[0]]);
          let y = [z[1] * x[2] - z[2] * x[1], z[2] * x[0] - z[0] * x[2], z[0] * x[1] - z[1] * x[0]];
          const cr = Math.cos(r), sr = Math.sin(r), x2 = [0, 1, 2].map(k => x[k] * cr + y[k] * sr), y2 = [0, 1, 2].map(k => y[k] * cr - x[k] * sr);
          res.cameraMonde = new Float32Array([x2[0], x2[1], x2[2], 0, y2[0], y2[1], y2[2], 0, z[0], z[1], z[2], 0, o[0], o[1], o[2], 1]); } }
      // accroches de tous les squelettes « point » à cette image
      const rac = {};
      for (const [nom, pt] of Object.entries(this.points)) { const cl = p && pt.d.clips[p.nom]; const m = pt.sq.poser(cl || null, cl ? cl.debut + dans : 0);
        rac[nom] = {}; for (const [n, i] of Object.entries(pt.sq.parNom)) rac[nom][n] = nom === 'point_eff' ? depE(m[i]) : dep(m[i]); }
      res.racines = rac;
      // acteurs d'abord (un effet peut être accroché à un de leurs os : l'épée de Lancelot dans sa main)
      res.peaux = {}; res.fondus = {};
      const mondeActeur = {};
      for (const a of this.acteurs) {
        let jouer = null, depuis = 0, visible = false, acc = null;
        // (15/11/2026) FONDU D'UN MODÈLE (15/11/2026, LU nie.exe) : commande 0x48A58CDC [acteur, valeur, images, …] (gestionnaire 0x140f39730) ->
        //   0x141817db0 : couche « event » (crc 0x3bae0aa7) du contrôleur de fondu du modèle (+0x790) ; valeur bornée à 0..1, atteinte
        //   en images x 1/60 s, en ligne droite depuis la valeur du moment (0x140baa840) ; valeur de départ 1 (+0xA8 = 1,0).
        //   Modèle pas dessiné du tout si la valeur <= 0,001 (0x1417de6cf, constante 0x141a7cad4).
        let fde = 1, fvers = 1, f0 = 0, fd = 0;
        const fval = t => fd > 0 ? fde + (fvers - fde) * Math.min(1, Math.max(0, (t - f0) / fd)) : fvers;
        for (const x of a.d.ordres) { if (x.image > f) break; if (x.jouer) { jouer = x.jouer; depuis = x.image; } if ('visible' in x) visible = x.visible; if (x.accroche) acc = x.accroche;
          if (x.fondu) { fde = fval(x.image); fvers = x.fondu[0]; fd = x.fondu[1]; f0 = x.image; } }
        const fondu = fval(f); res.fondus[a.d.acteur] = fondu; if (fondu <= 0.001) visible = false;
        const cl = jouer && a.d.clips[jouer]; if (!cl) continue;
        const m = a.sq.poser(cl, cl.debut + (f - depuis)), r = (acc && rac[acc[0]] && rac[acc[0]][acc[1]]) || I();
        const mondes = {}; for (const [n, i] of Object.entries(a.sq.parNom)) mondes[n] = mul(r, m[i]);
        mondeActeur[a.d.acteur] = mondes;
        if (visible) res.peaux[a.d.acteur] = m.map((w, b) => mul(r, mul(w, a.invRepos[b])));
      }
      for (const [act, o] of Object.entries(res.objets)) { const e = this._etat(this.objets[act], f);
        if (e.acc[0] === 'camera') {
          // (avant le 13/11/2026 : posé devant la caméra avec une distance corrigée au jugé ; traits 2 à 4 fois trop grands)
          // LU DANS nie.exe (commande 0x36E5B708 -> 0x140f584f0 -> 0x140f587f0, 13/11/2026) : l'effet est posé EN PIXELS au centre
          // de l'écran (largeur / 2 + x, −hauteur / 2 − y) : c'est un effet 2D, pas un objet devant la caméra. Ses os (dont
          // « scale » x 19 000) donnent directement des pixels. Projection : voir vue3d.js (ecran2D).
          o.racine = I(); o.ecran2D = true;
        }
        else if (rac[e.acc[0]] && rac[e.acc[0]][e.acc[1]]) o.racine = rac[e.acc[0]][e.acc[1]];
        else if (mondeActeur[e.acc[0]] && mondeActeur[e.acc[0]][e.acc[1]]) {
          o.racine = mondeActeur[e.acc[0]][e.acc[1]];
          // aura du ballon (ega0020…) : l'os « BallAura » (x 10) est prévu pour l'échelle des combats ; sans lui, les couches
          // de l'aura (rayon 0,136 à 0,16) épousent le ballon (rayon 0,14). On l'annule quand l'aura est sur le ballon.
          const sq = this.objets[act].sq, i = sq.parNom['BallAura'];
          if (i !== undefined) { const k = 1 / (sq.os[i].e[0] || 1); o.racine = mul(o.racine, new Float32Array([k, 0, 0, 0, 0, k, 0, 0, 0, 0, k, 0, 0, 0, 0, 1])); }
        } }
      // OS PANNEAUX (14/11/2026) : une fois l'accroche connue, les os sont recalculés avec la caméra du jeu dans le repère de
      // l'objet (le jeu : inverse(monde de l'objet) x caméra, 0x140526420)
      const camM = this._cameraMonde(p, dans);
      res.camM = camM || null;     // (14/11/2026) pièces panneaux par matériau (vue3d._animer)
      if (camM) for (const [act, o] of Object.entries(res.objets)) { const ob = this.objets[act]; if (!ob.sq.panneaux || !ob._pose) continue;
        const c = mul(inverse(o.racine), camM), [cl, t, vis] = ob._pose;
        o.monde = ob.sq.poser(cl, t, vis, c); o.cache = ob.sq.cache; o.local = ob.sq.local; }
      // peau des acteurs : matrice de chaque os = accroche x monde animé x inverse du repos

      for (const j of this.joueurs) { const cl = p && j.d.clips[p.nom]; if (!cl) continue;
        const m = j.sq.poser(cl, cl.debut + dans), rac = rps[j.d.accroche] || I();
        res.peaux[j.d.acteur] = m.map((w, b) => mul(rac, mul(w, j.invRepos[b]))); }
      if (this.d.camera && p && this.d.camera[p.nom]) { const cl = this.d.camera[p.nom], ch = {};
        for (const c of cl.cibles) for (const k of c.canaux) ch[k.type] = echantillon(k, cl.debut + dans)[0];
        if (22 in ch && 26 in ch) res.camera = { oeil: [ch[22], ch[23], ch[24]], cible: [ch[26], ch[27], ch[28]], roulis: -(ch[30] || 0), champ: ch[31] || Math.PI / 4 }; }   // sans canal 31 : 45°, défaut du constructeur de caméra (0x140b7a4d0, vu aussi en mémoire)
      res.decor = true;
      for (const x of this.d.decor || []) { if (x.image > f) break; res.decor = x.visible; }
      return res;
    }
  }
  window.Lecteur = Lecteur; window.Squelette = Squelette; window.Anim3D = { mul, trs, inverse, I, panneau };
})();
