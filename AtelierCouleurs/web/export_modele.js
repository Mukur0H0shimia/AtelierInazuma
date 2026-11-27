// (25/11/2026, demande d'un joueur, Ryu : « any way to extract/import models and textures from the tool itself ? I'd prefer to
// texture my stuff using Substance Painter ») EXPORT / IMPORT DE L'ATELIER, panneau Textures :
//  - « ⬇ PNG » : la texture choisie telle qu'elle est (retouches comprises : x.cur, jamais l'original de « Avant / après ») ;
//  - « ⬆ Remplacer par une image » : même chemin qu'une retouche du mode dessin (x.base / modif / moyenne, apresRetouche) :
//    l'aperçu, le lecteur du jeu et « Créer » la prennent ; « Annuler le dernier » la défait. Plusieurs images à la fois :
//    chacune va à la texture dont le NOM est dans le nom du fichier (export de Substance Painter : $mesh_$textureSet_BaseColor) ;
//  - « ⬇ Modèle (.glb) » : les pièces VISIBLES du modèle ouvert, au repos (positions lues du jeu), UV, normales, et un
//    matériau par texture principale, NOMMÉ comme la texture, avec son PNG (Substance Painter en fait un « texture set »).
// Fichiers enregistrés dans AtelierCouleurs\exports (serveur.py, /api/enregistrer_export ; l'Explorateur s'ouvre dessus),
// sinon téléchargés par le navigateur.
// Convention des sommets (LU, moteur/glb_vrfw.convertir : VRFW écrit positions, normales, UV et indices du .glb tels quels
// dans le jeu) : rien à retourner, ni axes, ni V des UV, ni sens des triangles.
(function () {
  const carteDonnees = x => !x || !x.cur || !x.cur.getContext || (x.info && x.info.donnees);
  const nomSur = s => String(s || '').replace(/[\\/:*?"<>|\x00-\x1f]+/g, '_').replace(/\s+/g, ' ').trim().slice(0, 100) || 'atelier';
  const blobPng = cv => new Promise((ok, ko) => cv.toBlob(b => b ? ok(b) : ko(new Error('PNG')), 'image/png'));

  async function enregistrer(nom, blob, ouvrir = true) {
    try {
      const r = await api('/api/enregistrer_export', { nom, donnees: await enBase64(new Uint8Array(await blob.arrayBuffer())), ouvrir: ouvrir && !window.EXPORT_SANS_DOSSIER });
      if (r && r.ok) return r.chemin;
    } catch (e) { /* serveur d'une ancienne version : téléchargement */ }
    const a = document.createElement('a'); a.href = URL.createObjectURL(blob); a.download = nom;
    document.body.appendChild(a); a.click(); a.remove(); setTimeout(() => URL.revokeObjectURL(a.href), 60000);
    return null;
  }

  function choisies() {
    return [...E.selTex].filter(k => !k.startsWith('mm/') && !carteDonnees(E.textures[k]));
  }

  // ------------------------------------------------------------------ ⬇ PNG
  async function exporterPng(cles) {
    cles = cles || choisies();
    if (!E.tech) return majRapport('Ouvre d’abord une technique ou un personnage.');
    if (!cles.length) return majRapport('Choisis d’abord une texture (clic sur une vignette).');
    const faits = [];
    let dossier = null;
    for (const k of cles) { const x = E.textures[k]; const c = await enregistrer(nomSur(x.nom) + '.png', await blobPng(x.cur), k === cles[cles.length - 1]);   // Explorateur : une fois
      faits.push(x.nom); if (c) dossier = c.replace(/[\\/][^\\/]*$/, ''); }
    // 1re ligne sans chemin (le mode simple ne montre qu'elle et retire les chemins), chemin complet dessous
    // (traduction : une phrase = UN modèle ; les morceaux variables sont des données, traduites par le dictionnaire)
    const lieu = dossier ? 'Texture enregistrée dans le dossier « exports » de l’Atelier' : 'Texture enregistrée dans les téléchargements du navigateur';
    majRapport(`${lieu} : ${faits.join(', ')} (PNG, retouches comprises). Une fois peinte, « ⬆ Remplacer par une image » la remet ici.` + (dossier ? '\n' + dossier : ''));
  }

  // ------------------------------------------------------------------ ⬆ Remplacer par une image
  // l'image va à la taille de la texture ; si elle n'a AUCUNE transparence et que la texture en a (Substance Painter exporte
  // souvent le Base Color sans alpha), la transparence de la texture est gardée (sinon les découpes deviendraient pleines)
  function poserImage(x, src) {
    const w = x.cur.width, h = x.cur.height, cx = x.cur.getContext('2d');
    const avant = cx.getImageData(0, 0, w, h);
    cx.clearRect(0, 0, w, h); cx.imageSmoothingEnabled = true; cx.imageSmoothingQuality = 'high'; cx.drawImage(src, 0, 0, w, h);
    let img = cx.getImageData(0, 0, w, h), d = img.data, opaque = true, alphaGarde = false;
    for (let i = 3; i < d.length; i += 4) if (d[i] < 255) { opaque = false; break; }
    if (opaque) { const a = avant.data; for (let i = 3; i < a.length; i += 4) if (a[i] < 250) { alphaGarde = true; break; }
      if (alphaGarde) { for (let i = 3; i < d.length; i += 4) d[i] = avant.data[i]; cx.putImageData(img, 0, 0); img = cx.getImageData(0, 0, w, h); } }
    x.base = img; x.modif = true; x.moyenne = moyenne(img); x.donneesCur = null;
    return { taille: src.width !== w || src.height !== h, alphaGarde };
  }

  // texture visée par un fichier : le plus long nom de texture contenu dans le nom du fichier (sans .png)
  function textureDuFichier(nomF) {
    const s = nomF.replace(/\.[^.]*$/, '').toLowerCase(); let best = null;
    for (const [k, x] of Object.entries(E.textures)) { if (k.startsWith('mm/') || carteDonnees(x)) continue;
      const n = x.nom.toLowerCase(); if (s.includes(n) && (!best || n.length > best[1].nom.length)) best = [k, x]; }
    return best && best[0];
  }

  async function importer(fichiers, cle) {
    fichiers = [...(fichiers || [])]; if (!fichiers.length) return;
    if (!E.tech) return majRapport('Ouvre d’abord une technique ou un personnage.');
    const sel = choisies(), lignes = [], poses = [];
    // UNE image par texture : l'export de Substance Painter donne aussi …_Normal, …_Roughness, …_Metallic pour le même
    // texture set -> la couleur (BaseColor / Diffuse / Albedo / Color) est prise, les autres cartes ignorées (dit dans le rapport)
    const couleur = n => /base_?colou?r|diffuse|albedo|colou?r/i.test(n.replace(/\.[^.]*$/, ''));
    const groupes = new Map(), choix = new Map();
    for (const f of fichiers) {
      const k = cle || (fichiers.length === 1 && sel.length === 1 ? sel[0] : textureDuFichier(f.name || ''));
      if (!k) { lignes.push(`${f.name} : aucune texture de ce nom ici (choisis la texture, puis une seule image).`); continue; }
      if (!groupes.has(k)) groupes.set(k, []); groupes.get(k).push(f);
    }
    for (const [k, fs] of groupes) { const garde = fs.find(f => couleur(f.name)) || fs[0]; choix.set(k, garde);
      for (const f of fs) if (f !== garde) lignes.push(`${f.name} : ignorée (une seule image par texture : ${garde.name} est prise).`); }
    for (const [k, f] of choix) {
      let im; try { im = await createImageBitmap(f, { colorSpaceConversion: 'none' }); } catch (e) { lignes.push(`${f.name} : image illisible.`); continue; }
      poses.push([k, im, f.name]);
    }
    if (poses.length) { quitterAvant(); E.pileRc.push(photoEtat()); if (E.pileRc.length > 8) E.pileRc.shift(); }
    // 1re ligne = résumé (seule montrée en mode simple : l'avertissement de taille y est), puis une ligne par image
    let redim = 0;
    for (const [k, im, nomF] of poses) {
      const x = E.textures[k], r = poserImage(x, im);
      lignes.push(`${nomF} → ${x.nom}`);
      if (r.taille) { redim++; lignes.push(`${x.nom} : image de ${im.width} × ${im.height} mise à la taille de la texture (${x.cur.width} × ${x.cur.height}).`); }
      if (r.alphaGarde) lignes.push(`${x.nom} : image sans transparence, celle de la texture est gardée.`);
      if (im.close) im.close();
    }
    if (poses.length) { apresRetouche(); paletteTech(); }
    const att = redim ? ' (attention : image d’une autre taille, mise à la taille de la texture)' : '';
    majRapport((poses.length ? `Image posée sur ${poses.length} texture(s)${att}. Pour revenir en arrière : « Annuler le dernier » (bloc Remplacer une couleur partout).`
      : 'Rien n’a été posé.') + lignes.map(l => '\n- ' + l).join(''));   // « - » hors des phrases : i18n.js le garde, traduit le reste
  }

  function choisirImages(cle) {
    const f = document.createElement('input'); f.type = 'file'; f.accept = 'image/png,image/*'; f.multiple = !cle; f.style.display = 'none';
    document.body.appendChild(f);
    f.onchange = () => { importer(f.files, cle).catch(e => majRapport('Image non posée : ' + e.message)); f.remove(); };
    f.click();
  }

  // ------------------------------------------------------------------ ⬇ Modèle (.glb)
  // normales lissées (sommets à la même place = une normale) quand le jeu n'en donne pas (personnages)
  function normalesLissees(P, I) {
    const n = P.length / 3, N = new Float32Array(P.length), cle = new Array(n), somme = new Map();
    for (let i = 0; i < n; i++) cle[i] = Math.round(P[3 * i] * 1e4) + ',' + Math.round(P[3 * i + 1] * 1e4) + ',' + Math.round(P[3 * i + 2] * 1e4);
    for (let t = 0; t + 2 < I.length; t += 3) {
      const a = I[t] * 3, b = I[t + 1] * 3, c = I[t + 2] * 3;
      const ux = P[b] - P[a], uy = P[b + 1] - P[a + 1], uz = P[b + 2] - P[a + 2], vx = P[c] - P[a], vy = P[c + 1] - P[a + 1], vz = P[c + 2] - P[a + 2];
      const f = [uy * vz - uz * vy, uz * vx - ux * vz, ux * vy - uy * vx];
      for (const s of [I[t], I[t + 1], I[t + 2]]) { const m = somme.get(cle[s]) || [0, 0, 0]; m[0] += f[0]; m[1] += f[1]; m[2] += f[2]; somme.set(cle[s], m); }
    }
    for (let i = 0; i < n; i++) { const m = somme.get(cle[i]) || [0, 1, 0], l = Math.hypot(m[0], m[1], m[2]) || 1; N[3 * i] = m[0] / l; N[3 * i + 1] = m[1] / l; N[3 * i + 2] = m[2] / l; }
    return N;
  }

  // pièces à mettre dans le .glb : celles des objets ouverts + modèles d'acteurs (esprit guerrier…) dont la texture est ouverte
  function piecesModele() {
    const L = [], vues = new Set(); let cachees = 0;
    // « ◎ Voir seul » : seulement l'objet montré (E.vue.isole = pièces de la vue), le reste compte comme caché
    const iso = E.vue && E.vue.isole && E.vue.isole.size ? E.vue.isole : null, montre = v => v.visible !== false && (!iso || iso.has(v));
    for (const o of E.objets || []) { if (o.erreur) continue;
      for (const pc of o.pieces || []) { const v = pc.vue; if (!v || !v.cpu || !v.cpu.idx || v.cpu.idx.length < 3) continue; vues.add(v);
        if (!montre(v)) { cachees++; continue; }
        const x = texPrincipale(o, pc); L.push({ nom: o.nom + '_' + pc.index, groupe: o.nom, v, tex: x ? o.nom + '/' + x.nom : null }); } }
    for (const v of (E.vue && E.vue.pieces) || []) {
      if (vues.has(v) || !v.peau || !v.cpu || !v.cpu.idx || v.cpu.idx.length < 3 || v.peau.acteur === 'joueur') continue;
      const k = v.texCle && v.texCle.startsWith('peau:') ? v.texCle.slice(5) : null; if (!k || !E.textures[k]) continue;
      if (!montre(v)) { cachees++; continue; }
      L.push({ nom: v.cle.replace(/\//g, '_'), groupe: k.split('/')[0], v, tex: k });
    }
    return { L, cachees };
  }

  async function construireGlb() {
    const { L, cachees } = piecesModele();
    if (!L.length) throw new Error('aucune pièce visible à exporter');
    const perso = !!(E.tech && E.tech.perso);
    const j = { asset: { version: '2.0', generator: 'Atelier Inazuma (export_modele.js)' }, scene: 0, scenes: [{ name: E.tech.code, nodes: [0] }],
      nodes: [{ name: String(E.tech.code), children: [] }], meshes: [], materials: [], textures: [], images: [], samplers: [{ magFilter: 9729, minFilter: 9987, wrapS: 10497, wrapT: 10497 }],
      accessors: [], bufferViews: [], buffers: [] };
    const morceaux = []; let taille = 0;
    const vue = (u8, cible) => { const pad = (4 - taille % 4) % 4; if (pad) { morceaux.push(new Uint8Array(pad)); taille += pad; }
      j.bufferViews.push(Object.assign({ buffer: 0, byteOffset: taille, byteLength: u8.byteLength }, cible ? { target: cible } : {}));
      morceaux.push(u8); taille += u8.byteLength; return j.bufferViews.length - 1; };
    const octets = a => new Uint8Array(a.buffer, a.byteOffset, a.byteLength);
    const mats = new Map(), groupes = new Map(), nomsMat = new Set();
    async function materiau(k) {
      if (!k) k = '';
      if (mats.has(k)) return mats.get(k);
      const x = k && E.textures[k];
      let nom = x ? x.nom : 'sans_texture'; if (nomsMat.has(nom)) nom = k.replace(/\//g, '_'); nomsMat.add(nom);
      const m = { name: nom, pbrMetallicRoughness: { baseColorFactor: [1, 1, 1, 1], metallicFactor: 0, roughnessFactor: 1 } };
      if (x && !carteDonnees(x)) {
        const png = new Uint8Array(await (await blobPng(x.cur)).arrayBuffer());
        j.images.push({ name: x.nom, mimeType: 'image/png', bufferView: vue(png) });
        j.textures.push({ source: j.images.length - 1, sampler: 0, name: x.nom });
        m.pbrMetallicRoughness.baseColorTexture = { index: j.textures.length - 1 };
        if (!perso) { const d = x.cur.getContext('2d').getImageData(0, 0, x.cur.width, x.cur.height).data;
          for (let i = 3; i < d.length; i += 4) if (d[i] < 250) { m.alphaMode = 'BLEND'; break; } }
      }
      j.materials.push(m); mats.set(k, j.materials.length - 1); return j.materials.length - 1;
    }
    for (const p of L) {
      const c = p.v.cpu, P = c.pos, I = c.idx, nv = P.length / 3;
      let mn = [Infinity, Infinity, Infinity], mx = [-Infinity, -Infinity, -Infinity];
      for (let i = 0; i < nv; i++) for (let a = 0; a < 3; a++) { const z = P[3 * i + a]; if (z < mn[a]) mn[a] = z; if (z > mx[a]) mx[a] = z; }
      const N = c.nor && c.nor.length === P.length ? c.nor : normalesLissees(P, I);
      const aP = j.accessors.length;
      j.accessors.push({ bufferView: vue(octets(new Float32Array(P)), 34962), componentType: 5126, count: nv, type: 'VEC3', min: mn, max: mx });
      j.accessors.push({ bufferView: vue(octets(new Float32Array(N)), 34962), componentType: 5126, count: nv, type: 'VEC3' });
      j.accessors.push({ bufferView: vue(octets(new Float32Array(c.uv)), 34962), componentType: 5126, count: nv, type: 'VEC2' });
      const ni = I.length - I.length % 3;
      j.accessors.push({ bufferView: vue(octets(new Uint16Array(I.subarray(0, ni))), 34963), componentType: 5123, count: ni, type: 'SCALAR' });
      j.meshes.push({ name: p.nom, primitives: [{ attributes: { POSITION: aP, NORMAL: aP + 1, TEXCOORD_0: aP + 2 }, indices: aP + 3, material: await materiau(p.tex) }] });
      if (!groupes.has(p.groupe)) { j.nodes.push({ name: p.groupe, children: [] }); groupes.set(p.groupe, j.nodes.length - 1); j.nodes[0].children.push(j.nodes.length - 1); }
      j.nodes.push({ name: p.nom, mesh: j.meshes.length - 1 }); j.nodes[groupes.get(p.groupe)].children.push(j.nodes.length - 1);
    }
    while (taille % 4) { morceaux.push(new Uint8Array(1)); taille++; }
    j.buffers.push({ byteLength: taille });
    let js = new TextEncoder().encode(JSON.stringify(j)); const pj = (4 - js.length % 4) % 4;
    if (pj) { const t = new Uint8Array(js.length + pj); t.set(js); t.fill(32, js.length); js = t; }
    const ent = new DataView(new ArrayBuffer(20));
    ent.setUint32(0, 0x46546C67, true); ent.setUint32(4, 2, true); ent.setUint32(8, 12 + 8 + js.length + 8 + taille, true);
    ent.setUint32(12, js.length, true); ent.setUint32(16, 0x4E4F534A, true);
    const eb = new DataView(new ArrayBuffer(8)); eb.setUint32(0, taille, true); eb.setUint32(4, 0x004E4942, true);
    return { blob: new Blob([ent.buffer, js, eb.buffer, ...morceaux], { type: 'model/gltf-binary' }), pieces: L.length, textures: j.images.length, cachees };
  }

  async function exporterModele() {
    if (!E.tech) return majRapport('Ouvre d’abord une technique ou un personnage.');
    if (E.chargement) return majRapport('Attends la fin du chargement.');
    majRapport('Modèle (.glb) en préparation…');
    const r = await construireGlb();
    const nom = nomSur(E.tech.code + ' ' + (E.tech.nom || '')) + '.glb', c = await enregistrer(nom, r.blob);
    const lieu = c ? 'Modèle enregistré dans le dossier « exports » de l’Atelier' : 'Modèle enregistré dans les téléchargements du navigateur';
    majRapport(`${lieu} : ${nom} (${r.pieces} pièce(s), ${r.textures} texture(s), au repos). Dans Substance Painter : un « texture set » par texture, du même nom ; exporte-les en PNG puis « ⬆ Remplacer par une image » (plusieurs à la fois : reconnues par leur nom).`
      + (r.cachees ? `\n${r.cachees} pièce(s) cachée(s) non comprises (cases décochées à gauche ou « Voir seul »).` : '') + (c ? '\n' + c : ''));
  }

  window.exporterPng = exporterPng; window.importerImages = importer; window.choisirImages = choisirImages;
  window.construireGlb = construireGlb; window.exporterModele = exporterModele;
  const lier = (id, f) => { const b = document.getElementById(id); if (b) b.onclick = () => Promise.resolve(f()).catch(e => majRapport('Échec : ' + e.message)); };
  lier('tex-png', () => exporterPng()); lier('tex-importer', () => choisirImages()); lier('tex-glb', () => exporterModele());
})();
