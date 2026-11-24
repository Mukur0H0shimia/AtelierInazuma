// Éditeur de bannières de l'Atelier Inazuma : image 1728 x 352, fond transparent, dans le style des bannières du jeu
// (lettres qui sautillent et penchent, dégradé vertical, contour clair puis contour foncé, ombre portée, lueur).
"use strict";
(function () {
  const L = 1728, H = 352;
  const POLICES = [
    ['impact.ttf', 'Impact'], ['COOPBL.TTF', 'Cooper Black'], ['HATTEN.TTF', 'Haettenschweiler'], ['SNAP____.TTF', 'Snap ITC'],
    ['JOKERMAN.TTF', 'Jokerman'], ['GILSANUB.TTF', 'Gill Sans Ultra'], ['BRLNSB.TTF', 'Berlin Sans gras'], ['FRAHV.TTF', 'Franklin lourd'],
    ['ERASBD.TTF', 'Eras gras'], ['BAUHS93.TTF', 'Bauhaus 93'], ['RAVIE.TTF', 'Ravie'], ['FORTE.TTF', 'Forte'], ['CHILLER.TTF', 'Chiller'],
    ['BROADW.TTF', 'Broadway'], ['ALGER.TTF', 'Algerian'], ['STENCIL.TTF', 'Stencil'], ['ELEPHNT.TTF', 'Elephant'], ['comicbd.ttf', 'Comic gras'],
    ['ITCKRIST.TTF', 'Kristen'], ['Inkfree.ttf', 'Ink Free'], ['MAGNETOB.TTF', 'Magneto'], ['JUICE___.TTF', 'Juice'],
  ];
  // styles tout prêts (couleurs du dégradé haut / milieu / bas, contours, ombre, lueur)
  const STYLES = {
    'Feu (comme le jeu)': { haut: '#8a1204', milieu: '#e5420c', bas: '#ffb21a', c1: '#ffe9a8', e1: 7, c2: '#3a0a02', e2: 5, ombre: '#000000', ombreA: 0.55, lueur: '#ffb000', lueurT: 0 },
    'Néant (violet)': { haut: '#1c0b4a', milieu: '#6a2cf0', bas: '#e0a8ff', c1: '#f3e6ff', e1: 7, c2: '#120428', e2: 5, ombre: '#000000', ombreA: 0.55, lueur: '#a060ff', lueurT: 18 },
    'Galaxie': { haut: '#0d1a4a', milieu: '#5a3df0', bas: '#ff8ae6', c1: '#fff6d0', e1: 7, c2: '#05081c', e2: 6, ombre: '#000000', ombreA: 0.55, lueur: '#7a6bff', lueurT: 22 },
    'Glace': { haut: '#0a3c78', milieu: '#3fa9f5', bas: '#e8fbff', c1: '#ffffff', e1: 7, c2: '#06213f', e2: 5, ombre: '#000000', ombreA: 0.5, lueur: '#9ae6ff', lueurT: 16 },
    'Or': { haut: '#6b3a00', milieu: '#e0a21c', bas: '#fff2a8', c1: '#fff8de', e1: 7, c2: '#2a1500', e2: 5, ombre: '#000000', ombreA: 0.55, lueur: '#ffd34a', lueurT: 12 },
    'Forêt': { haut: '#0b3d12', milieu: '#2fae3a', bas: '#d2ff8a', c1: '#f4ffe0', e1: 7, c2: '#062008', e2: 5, ombre: '#000000', ombreA: 0.55, lueur: '#8aff6a', lueurT: 0 },
    'Air': { haut: '#0a4a3c', milieu: '#20c9a8', bas: '#d8fff4', c1: '#ffffff', e1: 7, c2: '#05261f', e2: 5, ombre: '#000000', ombreA: 0.5, lueur: '#8affe0', lueurT: 0 },
    'Montagne': { haut: '#4a2a0a', milieu: '#b0702a', bas: '#ffd79a', c1: '#fff0d8', e1: 7, c2: '#241205', e2: 5, ombre: '#000000', ombreA: 0.55, lueur: '#ffb060', lueurT: 0 },
  };
  const DEFAUT = Object.assign({ texte: 'Frappe galactique', police: 'impact.ttf', taille: 0, espacement: 2, penche: 0.18, saute: 18,
    tourne: 5, graine: 7, x: 0, y: 0, ombreX: 10, ombreY: 12, ombreFlou: 6 }, STYLES['Galaxie']);

  // (24/11) réglages du style armure (police couleur) : ajustés en comparant à la bannière du jeu (scratchpad comparer)
  const ArmureReglages = {
    taille: 297, espace: -5, base: 0.30, contour: [255, 249, 172], contourPlus: 7, texY0: 73, texY1: 292,
    ombre: [40, 33, 30], ombreA: 0.55, ombreX: 9, ombreY: 10, ombreFlou: 1,
    lueur: 'rgb(240,222,196)', lueurFlou: 4, lueurA: 0.9, lueurN: 2,     // profil mesuré = celui du jeu à partir de 11 px (24/11)
    textes: ['armure!', 'armourfy!', '¡armadura!', 'rüstung!', 'armatura!', 'armadura!'],
    texteDuJeu(t) { return this.textes.includes(String(t || '').split(/\s+/).join('').toLowerCase()); },
  };
  window.ArmureReglages = ArmureReglages;

  function aleat(graine) { let s = graine * 9301 + 49297; return () => { s = (s * 9301 + 49297) % 233280; return s / 233280; }; }

  class EditeurBanniere {
    constructor(canvas) {
      this.cv = canvas; this.cv.width = L; this.cv.height = H; this.p = Object.assign({}, DEFAUT); this.charge = {};
    }
    static polices() { return POLICES; }
    static styles() { return STYLES; }
    async police(f) {
      if (this.charge[f]) return this.charge[f];
      const nom = 'pol_' + f.replace(/\W/g, '_');
      const ff = new FontFace(nom, `url(/police/${encodeURIComponent(f)})`);
      try { await ff.load(); }
      catch (e) {                                     // police absente de ce PC (polices d'Office…) : Impact à la place
        if (f === 'impact.ttf') throw e;
        this.manquante = f; return this.police('impact.ttf');
      }
      document.fonts.add(ff); this.charge[f] = nom; return nom;
    }
    // dessine les lettres (sans couleur) : renvoie [{ch, x, y, a}] et la taille utilisée
    _placer(cx, famille) {
      const p = this.p, txt = p.texte || ' ', r = aleat(p.graine);
      let taille = p.taille || 210;
      const mesure = t => { cx.font = `${t}px "${famille}"`; let w = 0; for (const ch of txt) w += cx.measureText(ch).width + p.espacement; return w - p.espacement; };
      if (!p.taille) { const w = mesure(taille), max = L - 260; if (w > max) taille = Math.max(60, Math.floor(taille * max / w)); }
      const largeur = mesure(taille);
      let x = (L - largeur) / 2 + p.x;
      const lettres = [];
      let i = 0;
      for (const ch of txt) {
        const w = cx.measureText(ch).width;
        const dy = (r() - 0.5) * 2 * p.saute, a = (r() - 0.5) * 2 * p.tourne * Math.PI / 180;
        lettres.push({ ch, x: x + w / 2, y: H / 2 + p.y + dy, a, w });
        x += w + p.espacement; i++;
      }
      return { lettres, taille };
    }
    _passe(cx, lettres, taille, famille, faire) {
      cx.save(); cx.font = `${taille}px "${famille}"`; cx.textAlign = 'center'; cx.textBaseline = 'middle';
      cx.lineJoin = 'round'; cx.miterLimit = 2;
      for (const l of lettres) {
        cx.save(); cx.translate(l.x, l.y); cx.transform(1, 0, -this.p.penche, 1, 0, 0); cx.rotate(l.a);
        faire(cx, l); cx.restore();
      }
      cx.restore();
    }
    // (23/11, demande de muku) « Lettres du jeu » : la bannière est écrite avec les LETTRES DÉCOUPÉES DANS LES BANNIÈRES DU
    // JEU (serveur : moteur/lettres_jeu.py, alphabet de l'élément choisi), puis posée telle quelle (décalage x / y gardé)
    async _dessinerJeu() {
      const p = this.p, el = p.police.slice(4), cle = el + '|' + p.texte, cx = this.cv.getContext('2d');
      if (this._jeu && this._jeu.cle === cle) { cx.clearRect(0, 0, L, H); cx.drawImage(this._jeu.im, p.x, p.y); return this.cv; }
      const im = new Image();
      im.src = '/api/banniere_jeu?texte=' + encodeURIComponent(p.texte || ' ') + '&element=' + encodeURIComponent(el);
      // (24/11) une 2e tentative avant de passer à une police ordinaire (une image ratée laissait Impact pour de bon)
      try { await im.decode(); } catch (e) {
        const im2 = new Image(); im2.src = im.src + '&r=' + Date.now();
        try { await im2.decode(); this._jeu = { cle, im: im2 }; cx.clearRect(0, 0, L, H); cx.drawImage(im2, p.x, p.y); return this.cv; }
        // (24/11, muku : « test » sorti en Impact) on GARDE la police choisie : un échec (texte vide pendant la frappe, serveur
        // occupé) laissait Impact pour de bon ; la bannière est vidée et le message dit pourquoi
        catch (e2) { this.manquante = 'Lettres du jeu (pas encore prêtes : environ 3 min au 1er lancement)'; cx.clearRect(0, 0, L, H); return this.cv; } }
      this._jeu = { cle, im };
      cx.clearRect(0, 0, L, H); cx.drawImage(im, p.x, p.y);
      return this.cv;
    }
    // (24/11, muku : polices « Armure Style Color ») STYLE ARMURE avec la police couleur de muku (COLR : 3 couches par lettre,
    // ombre (56,51,46), contour (255,204,61), remplissage (140,10,102)) : dessinée par le navigateur, puis chaque couche reprend
    // les couleurs MESURÉES sur la bannière du jeu : remplissage = texture du jeu (dégradé rose -> violet + facettes,
    // /api/texture_armure), contour = jaune pâle (255,249,172), ombre = sombre ; lueur crème autour. Le texte exact du jeu
    // (« Armure ! »…) reste la bannière du jeu (serveur).
    async _dessinerArmure() {
      const p = this.p, cx = this.cv.getContext('2d'), R = ArmureReglages;
      const famille = await this.police('Armure_Style_Color.ttf');
      if (!this._texArm) { const t = new Image(); t.src = '/api/texture_armure'; try { await t.decode(); this._texArm = t; } catch (e) { } }
      const calque = () => { const c = document.createElement('canvas'); c.width = L; c.height = H; return c; };
      // 1. la police telle quelle (ses 3 couches)
      const brut = calque(), cb = brut.getContext('2d');
      const txt = p.texte || ' ';
      let taille = p.taille || R.taille;
      cb.font = `${taille}px "${famille}"`;
      let w = cb.measureText(txt).width + R.espace * (txt.length - 1);
      if (w > L - 120) { taille = Math.floor(taille * (L - 120) / w); cb.font = `${taille}px "${famille}"`; w = cb.measureText(txt).width + R.espace * (txt.length - 1) * taille / R.taille; }
      cb.textBaseline = 'alphabetic';
      let x = (L - w) / 2 + p.x;
      const base = H / 2 + taille * R.base + p.y;
      if (cb.letterSpacing !== undefined) { cb.letterSpacing = (R.espace * taille / R.taille) + 'px'; cb.fillText(txt, x, base); }
      else for (const ch of txt) { cb.fillText(ch, x, base); x += cb.measureText(ch).width + R.espace * taille / R.taille; }
      // 2. chaque pixel : sa couche (couleur la plus proche des 3 de la police) ; remplissage -> texture du jeu
      const d = cb.getImageData(0, 0, L, H), px = d.data;
      // texture étirée sur la hauteur de NOS lettres : leurs lignes du haut et du bas = celles du remplissage du jeu (73 et 292),
      // le dégradé tombe au même endroit de la lettre (avant : bas des lettres dans une zone plus sombre)
      let y0 = H, y1 = 0;
      for (let y = 0; y < H; y++) for (let x = 0; x < L; x += 3) { const i = (y * L + x) * 4; if (px[i + 3] > 128 && px[i] < 200 && px[i + 2] > 60 && px[i + 1] < 60) { if (y < y0) y0 = y; if (y > y1) y1 = y; break; } }
      let tex = null;
      if (this._texArm && y1 > y0) { const tc = calque(), tt = tc.getContext('2d'), k = (y1 - y0) / (R.texY1 - R.texY0);
        tt.drawImage(this._texArm, 0, y0 - R.texY0 * k, L, H * k); tex = tt.getImageData(0, 0, L, H).data; }
      const sil = calque(), cs = sil.getContext('2d'), ds = cs.createImageData(L, H), sp = ds.data;   // lettre + son contour
      const rem = calque(), cr = rem.getContext('2d'), dr = cr.createImageData(L, H), rp = dr.data;   // remplissage seul
      const COUCHES = [[56, 51, 46], [255, 204, 61], [140, 10, 102]];
      for (let i = 0; i < px.length; i += 4) {
        const a = px[i + 3]; if (!a) continue;
        let k = 0, best = 1e9;
        for (let j = 0; j < 3; j++) { const c = COUCHES[j], e = (px[i] - c[0]) ** 2 + (px[i + 1] - c[1]) ** 2 + (px[i + 2] - c[2]) ** 2; if (e < best) { best = e; k = j; } }
        if (k === 0) continue;                       // l'ombre de la police : remplacée par celle du jeu (plus bas)
        sp[i] = 255; sp[i + 1] = 255; sp[i + 2] = 255; sp[i + 3] = a;
        if (k === 2) { rp[i] = tex ? tex[i] : 160; rp[i + 1] = tex ? tex[i + 1] : 70; rp[i + 2] = tex ? tex[i + 2] : 150; rp[i + 3] = a; }
      }
      cs.putImageData(ds, 0, 0); cr.putImageData(dr, 0, 0);
      // 3. contour élargi à l'épaisseur du jeu : la silhouette posée en cercle autour d'elle-même (dilatation)
      const k_ = taille / R.taille, ep = R.contourPlus * k_;
      const dil = calque(), cd = dil.getContext('2d');
      const pas = Math.max(16, Math.ceil(ep * 4));
      for (let n = 0; n < pas; n++) { const t = 2 * Math.PI * n / pas; cd.drawImage(sil, Math.cos(t) * ep, Math.sin(t) * ep); }
      cd.drawImage(sil, 0, 0);
      const teinte = (src, couleur) => { const c = calque(), t = c.getContext('2d'); t.drawImage(src, 0, 0); t.globalCompositeOperation = 'source-in'; t.fillStyle = couleur; t.fillRect(0, 0, L, H); return c; };
      // 4. ordre du jeu : lueur crème, ombre sombre décalée PAR-DESSUS la lueur, contour jaune pâle, remplissage
      cx.clearRect(0, 0, L, H);
      const lu = calque(), cl = lu.getContext('2d');
      cl.filter = `blur(${R.lueurFlou * k_}px)`; cl.drawImage(teinte(dil, R.lueur), 0, 0); cl.filter = 'none';
      cx.save(); cx.globalAlpha = R.lueurA; for (let n = 0; n < R.lueurN; n++) cx.drawImage(lu, 0, 0); cx.restore();
      cx.save(); cx.globalAlpha = R.ombreA; cx.filter = `blur(${R.ombreFlou * k_}px)`;
      cx.drawImage(teinte(dil, `rgb(${R.ombre.join(',')})`), R.ombreX * k_, R.ombreY * k_); cx.restore();
      cx.drawImage(teinte(dil, `rgb(${R.contour.join(',')})`), 0, 0);
      cx.drawImage(rem, 0, 0);
      return this.cv;
    }
    async dessiner() {
      // (24/11, muku : « regarde les deux à côté ») le style armure = LETTRES DU JEU (serveur) : la police couleur avait d'autres formes
      if (String(this.p.police).startsWith('jeu:')) return this._dessinerJeu();
      const p = this.p, famille = await this.police(p.police), cx = this.cv.getContext('2d');
      cx.clearRect(0, 0, L, H);
      const { lettres, taille } = this._placer(cx, famille);
      const calque = () => { const c = document.createElement('canvas'); c.width = L; c.height = H; return c; };
      // 1. ombre portée (forme complète avec le contour foncé), floue
      const om = calque(), co = om.getContext('2d');
      this._passe(co, lettres, taille, famille, (c, l) => { c.fillStyle = p.ombre; c.strokeStyle = p.ombre; c.lineWidth = 2 * (p.e1 + p.e2);
        c.strokeText(l.ch, 0, 0); c.fillText(l.ch, 0, 0); });
      cx.save(); cx.globalAlpha = p.ombreA; cx.filter = `blur(${p.ombreFlou}px)`; cx.drawImage(om, p.ombreX, p.ombreY); cx.restore();
      // 2. lueur
      if (p.lueurT > 0) { cx.save(); cx.filter = `blur(${p.lueurT}px)`;
        this._passe(cx, lettres, taille, famille, (c, l) => { c.strokeStyle = p.lueur; c.lineWidth = 2 * (p.e1 + p.e2) + p.lueurT; c.strokeText(l.ch, 0, 0); });
        cx.restore(); }
      // 3. contour foncé (extérieur), 4. contour clair (intérieur)
      this._passe(cx, lettres, taille, famille, (c, l) => { c.strokeStyle = p.c2; c.lineWidth = 2 * (p.e1 + p.e2); c.strokeText(l.ch, 0, 0); });
      this._passe(cx, lettres, taille, famille, (c, l) => { c.strokeStyle = p.c1; c.lineWidth = 2 * p.e1; c.strokeText(l.ch, 0, 0); });
      // 5. remplissage en dégradé vertical (haut -> milieu -> bas) dans chaque lettre
      this._passe(cx, lettres, taille, famille, (c, l) => {
        const g = c.createLinearGradient(0, -taille * 0.42, 0, taille * 0.42);
        g.addColorStop(0, p.haut); g.addColorStop(0.55, p.milieu); g.addColorStop(1, p.bas);
        c.fillStyle = g; c.fillText(l.ch, 0, 0);
      });
      // 6. reflet léger en haut des lettres
      this._passe(cx, lettres, taille, famille, (c, l) => {
        const g = c.createLinearGradient(0, -taille * 0.42, 0, 0);
        g.addColorStop(0, 'rgba(255,255,255,0.35)'); g.addColorStop(1, 'rgba(255,255,255,0)');
        c.fillStyle = g; c.fillText(l.ch, 0, 0);
      });
      return this.cv;
    }
    image() { return this.cv.toDataURL('image/png'); }
  }
  window.EditeurBanniere = EditeurBanniere;
})();
