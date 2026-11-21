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
      await ff.load(); document.fonts.add(ff); this.charge[f] = nom; return nom;
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
    async dessiner() {
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
