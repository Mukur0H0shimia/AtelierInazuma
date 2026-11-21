// Terrain de l'aperçu des cinématiques : pelouse rayée avec les lignes, buts, tribunes et ciel, aux dimensions du terrain
// du jeu (134 x 90, mesurées sur le stade s01g001). Le vrai stade n'est pas chargé (textures de 4096 x 4096).
"use strict";
(function () {
  const L = 134, l = 90;                       // longueur (x), largeur (z) ; échelle des terrains du jeu
  const K = L / 105;                           // facteur par rapport à un terrain réel de 105 m

  function texturePelouse() {
    const W = 2048, H = Math.round(2048 * l / L), cv = document.createElement('canvas'); cv.width = W; cv.height = H;
    const c = cv.getContext('2d'), sx = W / L, sz = H / l, X = x => (x + L / 2) * sx, Z = z => (z + l / 2) * sz;
    for (let i = 0; i < 20; i++) { c.fillStyle = i % 2 ? '#3f8f3a' : '#4aa043'; c.fillRect(i * W / 20, 0, W / 20 + 1, H); }
    // grain de l'herbe
    const img = c.getImageData(0, 0, W, H), d = img.data;
    for (let i = 0; i < d.length; i += 4) { const n = (Math.random() - 0.5) * 18; d[i] += n; d[i + 1] += n; d[i + 2] += n * 0.5; }
    c.putImageData(img, 0, 0);
    c.strokeStyle = 'rgba(255,255,255,0.92)'; c.lineWidth = 0.12 * K * sx * 1.6;
    const rect = (x0, z0, x1, z1) => c.strokeRect(X(x0), Z(z0), X(x1) - X(x0), Z(z1) - Z(z0));
    rect(-L / 2 + 1, -l / 2 + 1, L / 2 - 1, l / 2 - 1);
    c.beginPath(); c.moveTo(X(0), Z(-l / 2 + 1)); c.lineTo(X(0), Z(l / 2 - 1)); c.stroke();
    c.beginPath(); c.ellipse(X(0), Z(0), 9.15 * K * sx, 9.15 * K * sz, 0, 0, 2 * Math.PI); c.stroke();
    c.fillStyle = '#fff'; c.beginPath(); c.ellipse(X(0), Z(0), 0.4 * K * sx, 0.4 * K * sz, 0, 0, 2 * Math.PI); c.fill();
    for (const s of [-1, 1]) {
      const b = s * (L / 2 - 1);
      rect(Math.min(b, b - s * 16.5 * K), -20.15 * K, Math.max(b, b - s * 16.5 * K), 20.15 * K);     // surface de réparation
      rect(Math.min(b, b - s * 5.5 * K), -9.15 * K, Math.max(b, b - s * 5.5 * K), 9.15 * K);         // surface de but
      c.beginPath(); c.ellipse(X(b - s * 11 * K), Z(0), 0.35 * K * sx, 0.35 * K * sz, 0, 0, 2 * Math.PI); c.fill();
      c.beginPath(); c.ellipse(X(b - s * 11 * K), Z(0), 9.15 * K * sx, 9.15 * K * sz, 0, s > 0 ? Math.PI * 0.705 : -Math.PI * 0.295, s > 0 ? Math.PI * 1.295 : Math.PI * 0.295); c.stroke();
    }
    return cv;
  }

  function textureTribune() {
    const W = 1024, H = 256, cv = document.createElement('canvas'); cv.width = W; cv.height = H;
    const c = cv.getContext('2d'); c.fillStyle = '#2a2f3d'; c.fillRect(0, 0, W, H);
    for (let y = 0; y < H; y += 8) { c.fillStyle = y % 16 ? '#323848' : '#262b38'; c.fillRect(0, y, W, 4); }
    const coul = ['#d8d8e0', '#e94b3c', '#2f6fd8', '#f2c230', '#3fb35a', '#202020', '#f08a2c'];
    for (let i = 0; i < 5000; i++) { c.fillStyle = coul[(Math.random() * coul.length) | 0]; c.globalAlpha = 0.55 + Math.random() * 0.4;
      c.fillRect(Math.random() * W, Math.random() * H, 3, 4); }
    c.globalAlpha = 1; return cv;
  }

  // géométrie : pelouse, buts, quatre tribunes inclinées autour
  function geometries() {
    const out = [];
    const quad = (p, uv) => ({ pos: new Float32Array(p), uv: new Float32Array(uv), idx: new Uint16Array([0, 1, 2, 0, 2, 3]) });
    const m = 12;   // bord d'herbe autour des lignes
    out.push(Object.assign(quad([-L / 2 - m, 0, -l / 2 - m, L / 2 + m, 0, -l / 2 - m, L / 2 + m, 0, l / 2 + m, -L / 2 - m, 0, l / 2 + m],
      [-m / L, -m / l, 1 + m / L, -m / l, 1 + m / L, 1 + m / l, -m / L, 1 + m / l]), { tex: 'pelouse' }));
    const T = (x0, z0, x1, z1, h, rec) => {      // tribune : rampe qui monte vers l'extérieur
      const dx = x1 - x0, dz = z1 - z0, n = Math.hypot(dx, dz), ox = dz / n * rec, oz = -dx / n * rec;
      return Object.assign(quad([x0, 1, z0, x1, 1, z1, x1 + ox, h, z1 + oz, x0 + ox, h, z0 + oz], [0, 1, n / 40, 1, n / 40, 0, 0, 0]), { tex: 'tribune' });
    };
    const A = L / 2 + m + 6, B = l / 2 + m + 6;
    out.push(T(-A, -B, A, -B, 34, 40), T(A, B, -A, B, 34, 40), T(A, -B, A, B, 30, 34), T(-A, B, -A, -B, 30, 34));
    // buts : poteaux et barre (boîtes fines blanches)
    const boite = (x0, y0, z0, x1, y1, z1) => {
      const P = [[x0, y0, z0], [x1, y0, z0], [x1, y1, z0], [x0, y1, z0], [x0, y0, z1], [x1, y0, z1], [x1, y1, z1], [x0, y1, z1]];
      const F = [[0, 1, 2, 3], [5, 4, 7, 6], [4, 0, 3, 7], [1, 5, 6, 2], [3, 2, 6, 7], [4, 5, 1, 0]];
      const pos = [], idx = [], uv = [];
      for (const f of F) { const b = pos.length / 3; for (const k of f) { pos.push(...P[k]); uv.push(0.5, 0.5); } idx.push(b, b + 1, b + 2, b, b + 2, b + 3); }
      return { pos: new Float32Array(pos), uv: new Float32Array(uv), idx: new Uint16Array(idx), tex: null };
    };
    const g = 7.32 * K / 2, h = 2.44 * K, e = 0.15;
    for (const s of [-1, 1]) { const x = s * (L / 2 - 1);
      out.push(boite(x - e, 0, -g - e, x + e, h, -g + e), boite(x - e, 0, g - e, x + e, h, g + e), boite(x - e, h - e, -g, x + e, h + e, g)); }
    return out;
  }

  window.Terrain = {
    // ajoute le terrain à la vue (pièces opaques, montrées seulement pendant l'animation)
    ajouter(vue) {
      vue.texture('terrain:pelouse', texturePelouse()); vue.texture('terrain:tribune', textureTribune());
      const ps = [];
      geometries().forEach((g, i) => {
        const nv = g.pos.length / 3, p = vue.ajouter('terrain/' + i, { nv, ni: g.idx.length, pos: g.pos, uv: g.uv, idx: g.idx, col: new Uint8Array(nv * 4).fill(255) });
        p.terrain = true; p.opaque = true; p.teinte = [1, 1, 1, 1]; p.texCle = g.tex ? 'terrain:' + g.tex : null; ps.push(p);
      });
      return ps;
    },
  };
})();
