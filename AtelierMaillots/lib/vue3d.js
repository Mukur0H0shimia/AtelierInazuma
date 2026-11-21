// Moteur 3D de l'Atelier Maillots (WebGL, sans bibliothèque) : maillot (haut, col, short) + numéro dans le dos.
"use strict";
(function () {
  const VS = `attribute vec3 p; attribute vec3 n; attribute vec2 t; uniform mat4 mvp;
    varying vec3 vn; varying vec2 vt; void main(){ gl_Position = mvp * vec4(p, 1.0); vn = n; vt = t; }`;
  const FS = `precision mediump float; varying vec3 vn; varying vec2 vt; uniform sampler2D tex; uniform vec3 lum; uniform float aTex;
    uniform sampler2D ocTex; uniform float aOc; uniform float force;
    void main(){ vec3 c = aTex > 0.5 ? texture2D(tex, vt).rgb : vec3(0.62);
      if (aOc > 0.5) {
        // relief du tissu : ombre des plis + léger effet de bosse éclairée (comme dans le jeu)
        float v = dot(texture2D(ocTex, vt).rg, vec2(0.5));
        float e = 1.5 / 512.0;
        float gx = dot(texture2D(ocTex, vt + vec2(e, 0.0)).rg - texture2D(ocTex, vt - vec2(e, 0.0)).rg, vec2(0.5));
        float gy = dot(texture2D(ocTex, vt + vec2(0.0, e)).rg - texture2D(ocTex, vt - vec2(0.0, e)).rg, vec2(0.5));
        c *= clamp(mix(0.18, 1.0, pow(v, 1.4)) * force + (1.0 - force), 0.0, 1.0);
        c += force * vec3(clamp(-gx * 1.2 - gy * 1.6, -0.25, 0.25));
      }
      float d = abs(dot(normalize(vn), normalize(lum)));
      gl_FragColor = vec4(c * (0.42 + 0.62 * d), 1.0); }`;
  const FS_NUM = `precision mediump float; varying vec3 vn; varying vec2 vt; uniform sampler2D tex; uniform vec3 lum;
    uniform vec2 dec; uniform vec3 rempl; uniform vec3 cont;
    void main(){ vec4 c = texture2D(tex, vt + dec); if (c.a < 0.4) discard;
      vec3 col = mix(cont, rempl, step(0.5, c.r));
      float d = abs(dot(normalize(vn), normalize(lum)));
      gl_FragColor = vec4(col * (0.5 + 0.55 * d), 1.0); }`;

  function hex(c) { c = (c || '000000').replace('#', ''); return [0, 2, 4].map(i => parseInt(c.substr(i, 2), 16) / 255); }

  class Vue3D {
    constructor(canvas) {
      this.cv = canvas;
      const gl = this.gl = canvas.getContext('webgl2', { antialias: true, preserveDrawingBuffer: true }) ||
        canvas.getContext('webgl', { antialias: true, preserveDrawingBuffer: true });
      if (!gl) throw new Error('WebGL indisponible');
      this.gl2 = typeof WebGL2RenderingContext !== 'undefined' && gl instanceof WebGL2RenderingContext;
      this.prog = this._programme(VS, FS, ['mvp', 'lum', 'aTex', 'tex', 'ocTex', 'aOc', 'force']);
      this.forceRelief = 1;
      this.progN = this._programme(VS, FS_NUM, ['mvp', 'lum', 'tex', 'dec', 'rempl', 'cont']);
      this.parties = {}; this.textures = {};
      this.yaw = 0; this.pitch = 0.08; this.dist = 2.3; this.hauteur = 0.72; this.auto = false;
      this.col = 'col10';
      this.relief = true;
      this.numero = { visible: false, valeur: 10, rempl: 'FFFFFF', cont: '1A1A1A', taille: 1, hauteur: 0, base: null, buf: null, planche: null };
      this._demande = false;
      this._souris();
      const boucle = () => { if (this.auto) { this.yaw += 0.012; this._dessiner(); } requestAnimationFrame(boucle); };
      requestAnimationFrame(boucle);
      addEventListener('resize', () => this.dessiner());
    }
    _programme(vs, fs, unis) {
      const gl = this.gl;
      const sh = (type, src) => { const s = gl.createShader(type); gl.shaderSource(s, src); gl.compileShader(s);
        if (!gl.getShaderParameter(s, gl.COMPILE_STATUS)) throw new Error(gl.getShaderInfoLog(s)); return s; };
      const p = gl.createProgram(); gl.attachShader(p, sh(gl.VERTEX_SHADER, vs)); gl.attachShader(p, sh(gl.FRAGMENT_SHADER, fs));
      gl.linkProgram(p);
      const L = { prog: p, p: gl.getAttribLocation(p, 'p'), n: gl.getAttribLocation(p, 'n'), t: gl.getAttribLocation(p, 't') };
      for (const u of unis) L[u] = gl.getUniformLocation(p, u);
      return L;
    }
    _tampon(data, cible) { const gl = this.gl, b = gl.createBuffer(); gl.bindBuffer(cible || gl.ARRAY_BUFFER, b);
      gl.bufferData(cible || gl.ARRAY_BUFFER, data, gl.STATIC_DRAW); return b; }
    static normales(p, idx) {
      const n = new Float32Array(p.length);
      for (let i = 0; i < idx.length; i += 3) {
        const a = idx[i] * 3, b = idx[i + 1] * 3, c = idx[i + 2] * 3;
        const ux = p[b] - p[a], uy = p[b + 1] - p[a + 1], uz = p[b + 2] - p[a + 2];
        const vx = p[c] - p[a], vy = p[c + 1] - p[a + 1], vz = p[c + 2] - p[a + 2];
        const nx = uy * vz - uz * vy, ny = uz * vx - ux * vz, nz = ux * vy - uy * vx;
        for (const k of [a, b, c]) { n[k] += nx; n[k + 1] += ny; n[k + 2] += nz; }
      }
      return n;
    }
    _maillage(s) {
      const p = new Float32Array(s.p);
      return { bp: this._tampon(p), bn: this._tampon(Vue3D.normales(p, s.i)), bt: this._tampon(new Float32Array(s.t)),
        bi: this._tampon(new Uint16Array(s.i), this.gl.ELEMENT_ARRAY_BUFFER), n: s.i.length };
    }
    chargerModele(m, cadrer) {
      this.parties = {};
      for (const k in m.parties) this.parties[k] = this._maillage(m.parties[k]);
      if (cadrer !== false && m.haut) { this.hauteur = (m.bas + m.haut) / 2; this.dist = Math.max(1.2, (m.haut - m.bas) * 1.95); }
      this.dessiner();
    }
    texture(nom, source) {
      const gl = this.gl;
      let t = this.textures[nom];
      if (!t) t = this.textures[nom] = gl.createTexture();
      gl.activeTexture(gl.TEXTURE0);
      gl.bindTexture(gl.TEXTURE_2D, t);
      gl.pixelStorei(gl.UNPACK_FLIP_Y_WEBGL, false);
      gl.texImage2D(gl.TEXTURE_2D, 0, gl.RGBA, gl.RGBA, gl.UNSIGNED_BYTE, source);
      const w = source.width, h = source.height, pot = (w & (w - 1)) === 0 && (h & (h - 1)) === 0;
      if (this.gl2 || pot) { gl.generateMipmap(gl.TEXTURE_2D); gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MIN_FILTER, gl.LINEAR_MIPMAP_LINEAR); }
      else gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MIN_FILTER, gl.LINEAR);
      gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MAG_FILTER, gl.LINEAR);
      gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_S, gl.CLAMP_TO_EDGE);
      gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_T, gl.CLAMP_TO_EDGE);
      this.dessiner();
    }
    chargerTexture(nom, url) {
      return new Promise((ok, ko) => { const img = new Image(); img.onload = () => { this.texture(nom, img); ok(img); }; img.onerror = ko; img.src = url; });
    }
    // ------------------------------------------------------------------ numéro
    numeroModele(m) { this.numero.base = m; this._numeroTampon(); }
    numeroPlanche(img) { this.texture('_planche', img); this.numero.planche = true; }
    reglerNumero(r) { Object.assign(this.numero, r); this._numeroTampon(); }
    _numeroTampon() {
      const N = this.numero, m = N.base; if (!m) return;
      const p = m.p.slice(); let ymin = 1e9, ymax = -1e9, zf = 1e9;
      for (let i = 0; i < p.length; i += 3) { ymin = Math.min(ymin, p[i + 1]); ymax = Math.max(ymax, p[i + 1]); zf = Math.min(zf, p[i + 2]); }
      const cy = (ymin + ymax) / 2, s = N.taille, dy = N.hauteur / 100;
      for (let i = 0; i < p.length; i += 3) {
        p[i] = p[i] * s; p[i + 1] = cy + (p[i + 1] - cy) * s + dy; p[i + 2] = zf + (p[i + 2] - zf) * s - 0.002 * Math.abs(s - 1) - 0.0015;
      }
      N.buf = this._maillage({ p: p, t: m.t, i: m.i });
      this.dessiner();
    }
    // ------------------------------------------------------------------ dessin
    dessiner() { if (this._demande) return; this._demande = true; requestAnimationFrame(() => { this._demande = false; this._dessiner(); }); }
    _attribs(L, x) {
      const gl = this.gl;
      gl.bindBuffer(gl.ARRAY_BUFFER, x.bp); gl.enableVertexAttribArray(L.p); gl.vertexAttribPointer(L.p, 3, gl.FLOAT, false, 0, 0);
      if (L.n >= 0) { gl.bindBuffer(gl.ARRAY_BUFFER, x.bn); gl.enableVertexAttribArray(L.n); gl.vertexAttribPointer(L.n, 3, gl.FLOAT, false, 0, 0); }
      gl.bindBuffer(gl.ARRAY_BUFFER, x.bt); gl.enableVertexAttribArray(L.t); gl.vertexAttribPointer(L.t, 2, gl.FLOAT, false, 0, 0);
      gl.bindBuffer(gl.ELEMENT_ARRAY_BUFFER, x.bi);
    }
    _dessiner() {
      const gl = this.gl, cv = this.cv;
      const w = Math.max(1, cv.clientWidth * devicePixelRatio | 0), h = Math.max(1, cv.clientHeight * devicePixelRatio | 0);
      if (cv.width !== w || cv.height !== h) { cv.width = w; cv.height = h; }
      gl.viewport(0, 0, w, h);
      gl.clearColor(0, 0, 0, 0); gl.clear(gl.COLOR_BUFFER_BIT | gl.DEPTH_BUFFER_BIT);
      gl.enable(gl.DEPTH_TEST); gl.disable(gl.CULL_FACE);
      const e = [Math.sin(this.yaw) * Math.cos(this.pitch) * this.dist, this.hauteur + Math.sin(this.pitch) * this.dist,
        Math.cos(this.yaw) * Math.cos(this.pitch) * this.dist];
      const mvp = new Float32Array(mul(perspective(0.6, w / h, 0.05, 20), regarder(e, [0, this.hauteur, 0])));
      const lum = [e[0] + 0.6, e[1] + 1.2 - this.hauteur, e[2]];
      let L = this.prog; gl.useProgram(L.prog);
      gl.uniformMatrix4fv(L.mvp, false, mvp); gl.uniform3f(L.lum, lum[0], lum[1], lum[2]);
      gl.uniform1i(L.tex, 0); gl.uniform1i(L.ocTex, 1); gl.uniform1f(L.force, this.forceRelief);
      for (const k in this.parties) {
        if (k.startsWith('col') && k !== this.col) continue;
        const extra = k.startsWith('x');
        if (extra && !this.textures[k]) continue;      // pièce en plus : seulement quand son image est là
        const oc = this.relief && !extra ? this.textures[k === 'short' ? 'oc_short' : 'oc_haut'] : null;
        gl.activeTexture(gl.TEXTURE1); gl.bindTexture(gl.TEXTURE_2D, oc || null); gl.uniform1f(L.aOc, oc ? 1 : 0);
        gl.activeTexture(gl.TEXTURE0);
        const t = this.textures[extra ? k : (k === 'short' ? 'short' : 'haut')];
        gl.uniform1f(L.aTex, t ? 1 : 0); gl.bindTexture(gl.TEXTURE_2D, t || null);
        this._attribs(L, this.parties[k]);
        gl.drawElements(gl.TRIANGLES, this.parties[k].n, gl.UNSIGNED_SHORT, 0);
      }
      const N = this.numero;
      if (N.visible && N.buf && this.textures._planche) {
        L = this.progN; gl.useProgram(L.prog);
        gl.uniformMatrix4fv(L.mvp, false, mvp); gl.uniform3f(L.lum, lum[0], lum[1], lum[2]);
        gl.uniform1i(L.tex, 0); gl.bindTexture(gl.TEXTURE_2D, this.textures._planche);
        const v = Math.max(0, Math.min(99, N.valeur | 0));
        gl.uniform2f(L.dec, (v % 10) * 0.1, Math.floor(v / 10) * 0.1);
        gl.uniform3fv(L.rempl, hex(N.rempl)); gl.uniform3fv(L.cont, hex(N.cont));
        gl.enable(gl.POLYGON_OFFSET_FILL); gl.polygonOffset(-2, -4);
        this._attribs(L, N.buf);
        gl.drawElements(gl.TRIANGLES, N.buf.n, gl.UNSIGNED_SHORT, 0);
        gl.disable(gl.POLYGON_OFFSET_FILL);
      }
    }
    vue(yaw) { this.yaw = yaw; this.pitch = 0.08; this.dessiner(); }
    _souris() {
      const cv = this.cv; let g = null;
      cv.addEventListener('mousedown', ev => { g = { x: ev.clientX, y: ev.clientY, b: ev.button }; ev.preventDefault(); });
      cv.addEventListener('contextmenu', ev => ev.preventDefault());
      addEventListener('mouseup', () => g = null);
      addEventListener('mousemove', ev => {
        if (!g) return;
        const dx = ev.clientX - g.x, dy = ev.clientY - g.y; g.x = ev.clientX; g.y = ev.clientY;
        if (g.b === 2) this.hauteur = Math.max(0, Math.min(1.8, this.hauteur + dy * 0.003));
        else { this.yaw -= dx * 0.01; this.pitch = Math.max(-1.3, Math.min(1.3, this.pitch + dy * 0.01)); }
        this.dessiner();
      });
      cv.addEventListener('wheel', ev => { this.dist = Math.max(0.4, Math.min(6, this.dist * (ev.deltaY > 0 ? 1.1 : 0.9))); this.dessiner(); ev.preventDefault(); }, { passive: false });
    }
  }
  function perspective(f, a, n, l) { const t = 1 / Math.tan(f / 2);
    return [t / a, 0, 0, 0, 0, t, 0, 0, 0, 0, (l + n) / (n - l), -1, 0, 0, 2 * l * n / (n - l), 0]; }
  function mul(a, b) { const r = new Array(16);
    for (let i = 0; i < 4; i++) for (let j = 0; j < 4; j++) { let s = 0; for (let k = 0; k < 4; k++) s += a[k * 4 + j] * b[i * 4 + k]; r[i * 4 + j] = s; }
    return r; }
  function regarder(e, c) {
    let zx = e[0] - c[0], zy = e[1] - c[1], zz = e[2] - c[2]; let l = Math.hypot(zx, zy, zz); zx /= l; zy /= l; zz /= l;
    let xx = zz, xy = 0, xz = -zx; l = Math.hypot(xx, xy, xz) || 1; xx /= l; xz /= l;
    const yx = zy * xz - zz * xy, yy = zz * xx - zx * xz, yz = zx * xy - zy * xx;
    return [xx, yx, zx, 0, xy, yy, zy, 0, xz, yz, zz, 0,
      -(xx * e[0] + xy * e[1] + xz * e[2]), -(yx * e[0] + yy * e[1] + yz * e[2]), -(zx * e[0] + zy * e[1] + zz * e[2]), 1];
  }
  window.Vue3D = Vue3D;
})();
