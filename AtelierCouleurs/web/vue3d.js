// Vue 3D de l'Atelier Couleurs (WebGL pur, sans bibliothèque) : les pièces d'un effet de technique, fixes.
// Couleur d'une pièce = couleur de ses sommets x couleur moyenne de sa texture principale (recalculée après chaque retouche).
"use strict";
(function () {
  const VS = `attribute vec3 p; attribute vec4 c; attribute vec2 t; attribute vec3 nrm; uniform mat4 mvp; uniform mat4 modele; uniform vec4 uvx;
    varying vec4 vc; varying vec2 vt; varying vec3 vw; varying vec3 vnw;
    void main(){ vec4 w = modele * vec4(p, 1.0); gl_Position = mvp * w; vc = c; vt = t * uvx.xy + uvx.zw; vw = w.xyz; vnw = (modele * vec4(nrm, 0.0)).xyz; }`;
  const ID = new Float32Array([1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1]);
  // RENDU DU JEU (13/11/2026) : traduction des shaders DXBC du jeu (dx11/shader/<version>/Effect_*.pfxo / .vfxo).
  // u_texProj[k] (2 lignes) -> coordonnées de la case k ; couleur = sommet x u_diffuse, RVB x (1 + u_ambient.x).
  // BROUILLARD (diffusion Rayleigh / Mie + brouillard de hauteur) : traduit ligne à ligne de map_pbrt1.vfxo (même code dans
  // map_basic / map_pbrt2 / map_t1_cutout) ; registres cb5[37…50] remplis par nie.exe 0x140f7f050 (voir brouillardCB).
  // Seulement si u_ambient.w > 0 (matériau). Résultat : vF.rgb = lumière diffusée, vF.a = transmission.
  const FOG_GLSL = `uniform float aFog; uniform vec3 fR[5]; uniform vec3 fHC; uniform vec3 fM[3]; uniform vec4 fW0; uniform vec4 fW1; uniform vec4 fH0; uniform vec4 fH1; uniform vec4 fB;
    vec4 brouillard(vec3 p, vec3 oeil, vec3 lDir) {
      vec3 D = p - oeil; float dist = length(D); vec3 Dn = D / dist;
      float cs = dot(Dn, normalize(lDir));
      float rayP = min((cs * cs * 0.059683 + 0.059683) * 12.0, 1.0);
      float g = fW1.x, g2 = g * g;
      float mieP = (1.0 - g2) / (g2 + 2.0) * (cs * cs + 1.0) / pow(abs(g2 + 1.0 - 2.0 * cs * g), 1.5) * 0.119366;
      float b1 = (1.0 + fB.y) * 0.116, b2 = (1.0 + fB.x) * 0.216, b0 = b2 - b1;
      float s = min(dist * 0.004, 1.0) * Dn.y;
      vec4 k = clamp(vec4(1.0 / b0, 1.0 / b1, 1.0 / b1, 1.0 / b0) * vec4(s - b1, s, s + b1, s + b2), 0.0, 1.0);
      vec3 A = mix(fR[1], fR[0], k.x), B = mix(fR[2], fR[1], k.y), C = mix(fR[3], fR[2], k.z), E = mix(fR[4], fR[3], k.w);
      vec3 rayC = s >= b1 ? A : (s >= 0.0 ? B : (s >= -b1 ? C : E));
      vec2 m = clamp(vec2(s, s + b2) / b2, 0.0, 1.0);
      vec3 M1 = mix(fM[1], fM[0], m.x), M2 = mix(fM[2], fM[1], m.y), mieC = mix(M2, M1, s >= 0.0 ? 1.0 : 0.0);
      float hF = exp(-(p.y - fH0.x) * fH0.y);
      float dW = max(dist + fW0.x, 0.0), dH = max(dist + fH0.z, 0.0);
      vec4 f = 1.0 - exp(vec4(dW * fW0.y, dW * fW0.z, dH * fH0.w, dH * fH1.x));
      vec4 r7 = vec4(rayP, mieP, hF, mieP * hF) * f;
      const vec3 Y = vec3(0.29891, 0.58661, 0.11448);
      float lR = dot(rayC, Y); rayC = mix(vec3(lR), rayC, clamp(dW * fW0.w, 0.0, 1.0));
      float lH = dot(fHC, Y); vec3 hC = mix(vec3(lH), fHC, clamp(dH * fH1.y, 0.0, 1.0));
      vec3 ins = rayC * r7.x + hC * clamp(r7.z, 0.0, 1.0) + mieC * r7.y + mieC * clamp(r7.w, 0.0, 1.0);
      return vec4(ins, max(1.0 - (r7.x + r7.z), 0.0) * max(1.0 - f.y * mieP, 0.0));
    }`;
  const VS_J = `attribute vec3 p; attribute vec4 c; attribute vec2 t; attribute vec2 ta; attribute vec2 tb; attribute vec2 tc; attribute vec2 td;
    attribute vec3 n; uniform mat4 mv; varying vec3 vN; varying vec3 vV; attribute vec3 tg; varying vec3 vT;
    attribute vec2 te; attribute vec4 k1; varying vec2 t5; varying vec2 t0r; varying vec2 t3r; varying vec2 t4r; varying vec4 vk1; varying vec2 t1r;
    uniform mat4 mvp; uniform mat4 modele; uniform float vdisp; uniform vec4 Q0; uniform vec4 Q1; uniform sampler2D s3; uniform sampler2D s4;
    varying vec2 vDa; varying vec2 vDb; varying float vBord;
    uniform float aura; uniform vec4 Q2; uniform vec3 oeilW; uniform mat4 vueV; varying vec2 vAu; varying float vAf;
    uniform float morph; uniform sampler2D s2;
    uniform float fogFx; uniform float bordFx; uniform vec3 lDir; varying vec4 vF; varying float vRimA;
    uniform float eau; varying vec3 vB;
    uniform float fumee; uniform vec4 Q4; uniform vec4 Q5; varying vec4 vCel; varying vec3 vL;
    uniform mat4 ombVP; uniform float ombFx; varying vec4 vLS; uniform float patL; uniform vec4 Q3;
    uniform float smp; varying vec4 vL2;
    ` + FOG_GLSL + `
    float fm(float x, float y){ float q = x / y; return x - y * (q < 0.0 ? ceil(q) : floor(q)); }
    vec2 celUV(vec2 uv, float nc, float nl, float n) { float c0 = fm(n, nc), l0 = fm(n / nc < 0.0 ? ceil(n / nc) : floor(n / nc), nl);
      return uv / vec2(nc, nl) + vec2(c0 / nc, l0 / nl); }
    uniform vec4 uA[6]; uniform vec4 uB[6]; varying vec4 vc; varying vec2 t0; varying vec2 t1; varying vec2 t2; varying vec2 t3; varying vec2 t4;
    vec2 tp(vec4 a, vec4 b, vec2 uv){ vec3 u = vec3(uv, 1.0); return vec2(dot(a.xyz, u), dot(b.xyz, u)); }
    void main(){ vec3 pp = p, nn = n;
      // Effect_VDispRim.vfxo : sommets poussés par _VectorDispTex (case 3, TEXCOORD3) dans le repère (T, B, N signé par COLOR0.w),
      // amplitude = P0.w x (1 + P1.z x (attachScale - 1), attachScale pris à 1) / échelle de l'objet x COLOR0.x x P0.z ;
      // normale refaite avec _NormalTex (case 4)
      if (vdisp > 0.5) { vec3 e = vec3(length(modele[0].xyz), length(modele[1].xyz), length(modele[2].xyz));
        vec3 k = Q0.w / e * (c.x * Q0.z); float sg = c.w * 2.0 - 1.0; vec3 Ns = sg * n, B = cross(Ns, tg);
        vec2 ud = tp(uA[3], uB[3], tc); vec3 d = texture2DLod(s3, ud, 0.0).xyz * 2.0 - 1.0; vec3 nt = texture2DLod(s4, ud, 0.0).xyz;
        pp = p + (B * d.y + tg * d.x + Ns * d.z) * k;
        float w = Q0.z * c.x; vec3 q = vec3(sg * (nt.xy * 2.0 - 1.0), nt.z + nt.z - 2.0) * w + vec3(0.0, 0.0, 1.0);
        nn = tg * q.x + cross(n, tg) * q.y + n * q.z; }
      // Effect_Aura1.vfxo (traduit le 13/11/2026) : gonflement le long de la normale (P0.z x COLOR0.x), puis encore sur les bords
      // (P0.w x (1 − N.V)) ; point repoussé loin de l'œil (P1.x, repère monde) ; décalage vertical à l'écran sur les bords (P1.y) ;
      // texture lue dans un plan face à la caméra centré sur P2.xyz ; fondu de profondeur (P2.zw) sur la profondeur Direct3D
      // (near / far de la caméra du jeu : 0,1 / 5000)
      vAu = vec2(0.0); vAf = 1.0; vB = vec3(0.0); vec3 pFog = p; vCel = vec4(0.0); vL = vec3(0.0, 0.0, 1.0);
      // Effect_Smoke2.vfxo (traduit le 13/11/2026) : planche de silhouettes (TEXCOORD1 x u_texProj[1], P5.x colonnes, P5.y lignes,
      // image P5.z et suivante) ; lumière = P2.xyz (direction si P4.x = 0, sinon point) ; repère T, B, N de l'objet
      if (fumee > 0.5) { float nc = Q5.x, nl = Q5.y, n0 = Q5.z < 0.0 ? ceil(Q5.z) : floor(Q5.z), n1 = n0 + 1.0;
        vec2 uv = tp(uA[1], uB[1], ta) / vec2(nc, nl);
        float c0 = fm(n0, nc), l0 = fm(n0 / nc < 0.0 ? ceil(n0 / nc) : floor(n0 / nc), nl);
        float c1 = fm(n1, nc), l1 = fm(n1 / nc < 0.0 ? ceil(n1 / nc) : floor(n1 / nc), nl);
        vCel = vec4(uv + vec2(c0 / nc, l0 / nl), uv + vec2(c1 / nc, l1 / nl));
        vec3 e = vec3(length(modele[0].xyz), length(modele[1].xyz), length(modele[2].xyz));
        vec3 pw = (modele * vec4(p, 1.0)).xyz; vec3 Lw = Q4.x == 0.0 ? Q2.xyz : Q2.xyz - pw;
        vL = (vueV * vec4(Lw, 0.0)).xyz; vB = (mv * vec4(normalize(cross(n, tg)) / e, 0.0)).xyz; }
      // Effect_Water1.vfxo (traduit le 13/11/2026) : sommets poussés par _VectorDispTex (case 2) dans le repère (T, B, N signé par
      // COLOR0.w), normale refaite avec la case 3 ; amplitude P0.w / échelle x COLOR0.x x P0.z (attachScale pris à 1)
      if (eau > 0.5) { vec3 e = vec3(length(modele[0].xyz), length(modele[1].xyz), length(modele[2].xyz));
        vec3 k = Q0.w / e * (c.x * Q0.z); float sg = c.w * 2.0 - 1.0; vec3 Ns = sg * n, B = normalize(cross(Ns, tg));
        vec2 ud = tp(uA[2], uB[2], tb); vec3 d = texture2DLod(s2, ud, 0.0).xyz * 2.0 - 1.0; vec3 nt = texture2DLod(s3, ud, 0.0).xyz;
        pp = p + (B * d.y + tg * d.x + Ns * d.z) * k;
        float w = Q0.z * c.x; vec3 q = vec3(nt.xy * 2.0 - 1.0, nt.z + nt.z - 2.0) * w + vec3(0.0, 0.0, 1.0);
        nn = (tg * q.x + B * q.y + Ns * q.z) / e; vB = (mv * vec4(B / e, 0.0)).xyz; }
      // Effect_T1M1Morph.vfxo (traduit le 13/11/2026) : poses rangées en planche dans _MorphTex (case 2, TEXCOORD2), P0.z colonnes,
      // P0.w lignes ; pose n = partie entière de P1.x et pose n + 1, fondu = partie décimale ; déplacement local
      // (couleur x 2 − 1) x COLOR0.rgb x P1.y
      if (morph > 0.5) { float nc = Q0.z, nl = Q0.w, n0 = Q1.x < 0.0 ? ceil(Q1.x) : floor(Q1.x), n1 = n0 + 1.0;
        vec2 uv = tp(uA[2], uB[2], tb) / vec2(nc, nl);
        float c0 = fm(n0, nc), l0 = fm(n0 / nc < 0.0 ? ceil(n0 / nc) : floor(n0 / nc), nl);
        float c1 = fm(n1, nc), l1 = fm(n1 / nc < 0.0 ? ceil(n1 / nc) : floor(n1 / nc), nl);
        vec3 A = texture2DLod(s2, uv + vec2(c0 / nc, l0 / nl), 0.0).xyz, B = texture2DLod(s2, uv + vec2(c1 / nc, l1 / nl), 0.0).xyz;
        pp = p + (mix(A, B, fm(Q1.x, 1.0)) * 2.0 - 1.0) * (c.xyz * Q1.y); }
      if (aura > 0.5) {
        pp = p + n * (Q0.z * c.x);
        vec3 nv0 = normalize((mv * vec4(n, 0.0)).xyz);
        pp += n * (Q0.w * (1.0 - dot(nv0, -normalize((mv * vec4(pp, 1.0)).xyz))));
        vec3 e2 = normalize((mv * vec4(pp, 1.0)).xyz); float rb = 1.0 - clamp(dot(nv0, -e2), 0.0, 1.0);
        vec3 pw = (modele * vec4(pp, 1.0)).xyz, pw2 = pw - Q1.x * normalize(oeilW - pw);
        vec4 cl = mvp * vec4(pw2, 1.0); cl.y += Q1.y * rb; gl_Position = cl;
        float zc = (cl.w * 5000.0 - 0.1 * 5000.0) / (5000.0 - 0.1);
        vAf = clamp((zc - Q2.w) / (Q2.z - Q2.w), 0.0, 1.0);
        vec3 dv = (vueV * vec4(pw - Q2.xyz, 0.0)).xyz;
        vAu = tp(uA[0], uB[0], vec2(dv.x * 0.5 + 0.5, 1.0 - (dv.y * 0.5 + 0.5)));
      } else gl_Position = mvp * modele * vec4(pp, 1.0);
      vc = c;     // case k : u_texProj[k] x TEXCOORDk
      vLS = ombFx > 0.5 ? ombVP * (modele * vec4(pp, 1.0)) : vec4(0.0, 0.0, 0.0, 1.0);   // u_mtxLightWP x point du monde
      // Effect_T1L2PatternFadePar.vfxo (traduit le 13/11/2026) : image (P3.x x P3.y − 1) x COLOR0.x de la planche (P3.x colonnes,
      // P3.y lignes) et la suivante, fondu mix(fraction, fraction > 0,5, P3.w) ; lumière P1.xyz (direction si P2.x = 0, sinon point,
      // atténuation 1 + P2.w (1 / distance − 1)) ; ombre lue au point décalé de 0,05 x normale du monde
      if (patL > 0.5) { float f = (Q3.x * Q3.y - 1.0) * c.x, n0 = f < 0.0 ? ceil(f) : floor(f), fr = f - n0;
        vec2 u0 = tp(uA[0], uB[0], t); vCel = vec4(celUV(u0, Q3.x, Q3.y, n0), celUV(u0, Q3.x, Q3.y, n0 + 1.0));
        vec3 e = vec3(length(modele[0].xyz), length(modele[1].xyz), length(modele[2].xyz));
        vec3 pw = (modele * vec4(p, 1.0)).xyz, nw = (modele * vec4(n / e, 0.0)).xyz;
        vec3 Lw = Q2.x == 0.0 ? Q1.xyz : Q1.xyz - pw;
        vAu = vec2(1.0 + Q2.w * (1.0 / length(Lw) - 1.0), mix(fr, abs(fr) > 0.5 ? 1.0 : 0.0, Q3.w));
        vL = (vueV * vec4(Lw, 0.0)).xyz; vB = (mv * vec4(normalize(cross(n, tg)) / e, 0.0)).xyz;
        if (ombFx > 0.5) vLS = ombVP * vec4(pw + 0.05 * nw, 1.0); }
      // Effect_T1M1Fog.vfxo (traduit le 13/11/2026) : brouillard du stade (même calcul et mêmes registres cb5[37…50] que map_pbrt1,
      // toujours actif) au point du monde ; alpha x fondu de bord min(|N.V| / sat(P1.x + P1.y), 1) remis entre P1.y et 1
      vF = vec4(0.0, 0.0, 0.0, 1.0); vRimA = 1.0;
      if (eau > 0.5 && aFog > 0.5) vF = brouillard((modele * vec4(pFog, 1.0)).xyz, oeilW, lDir);   // brouillard au point non déplacé
      if (fogFx > 0.5 || bordFx > 0.5) { if (fogFx > 0.5 && aFog > 0.5) vF = brouillard((modele * vec4(pp, 1.0)).xyz, oeilW, lDir);
        // Effect_BorderLight.vfxo : même fondu de bord, avec P1.z / P1.w
        vec2 rq = bordFx > 0.5 ? Q1.zw : Q1.xy;
        vec3 e = vec3(length(modele[0].xyz), length(modele[1].xyz), length(modele[2].xyz));
        vec3 nv = (mv * vec4(n / e, 0.0)).xyz, vv = normalize((mv * vec4(pp, 1.0)).xyz);
        float a = min(abs(dot(nv, -vv)) / clamp(rq.y + rq.x, 0.0, 1.0), 1.0);
        vRimA = max((a - rq.y) / (1.0 - rq.y), 0.0); }
      { vec3 ax = normalize(mv[0].xyz), by = normalize(mv[1].xyz); vDa = vec2(ax.x, by.x); vDb = vec2(ax.y, by.y); }   // distorsions
      { vec3 e = vec3(length(modele[0].xyz), length(modele[1].xyz), length(modele[2].xyz)); vec3 nv = (mv * vec4(nn / e, 0.0)).xyz;
        float b = abs(dot(nv, -normalize((mv * vec4(pp, 1.0)).xyz))) / clamp(Q1.w + Q1.z, 0.0, 1.0);      // BallAura1 : |N.V| / sat(P1.w + P1.z)
        vBord = max((min(b, 1.0) - Q1.w) / (1.0 - Q1.w), 0.0); }
      vN = (mv * vec4(nn, 0.0)).xyz; vV = -(mv * vec4(pp, 1.0)).xyz;      // repère caméra (reflets T1M1Rim)
      vT = (mv * vec4(tg, 0.0)).xyz;
      t5 = tp(uA[5], uB[5], te); t0r = t; t4r = td; vk1 = k1; t1r = ta;  // T3ThresholdF, flux
      t0 = tp(uA[0], uB[0], t); t1 = tp(uA[1], uB[1], ta); t2 = tp(uA[2], uB[2], tb); t3 = tp(uA[3], uB[3], tc); t4 = tp(uA[4], uB[4], td);
      t3r = t3; /* après le calcul de t3 (jeu : o3 = texProj[3] x TEXCOORD3, puis cases) */ 
      // Effect_SmokePar1.vfxo (traduit le 13/11/2026) — comme dans le jeu, lumières et ombre en repère LOCAL de l'objet :
      // image (P5.x x P5.y − 1) x COLOR0.x de la planche (TEXCOORD1), fraction ; lumière 1 = P2 (direction si P4.x = 0, sinon point),
      // U du dégradé COLOR0.y x P2.w ; lumière 2 = point P3, U = COLOR0.z x P3.w, atténuation sat(1 + P4.w (P4.z / distance − 1)) ;
      // normale = mix(normale du monde, direction depuis P1, sat(N.dir + 1) x P1.w) ; ombre au point local + 0,05 x normale
      vL2 = vec4(0.0);
      if (smp > 0.5) { float f = (Q5.x * Q5.y - 1.0) * c.x, n0 = f < 0.0 ? ceil(f) : floor(f);
        vec2 u1 = tp(uA[1], uB[1], ta); vCel = vec4(celUV(u1, Q5.x, Q5.y, n0), celUV(u1, Q5.x, Q5.y, n0 + 1.0));
        vec3 l2 = Q3.xyz - p; vAu = vec2(f - n0, clamp(1.0 + Q4.w * (Q4.z / length(l2) - 1.0), 0.0, 1.0));
        vL = Q4.x == 0.0 ? Q2.xyz : Q2.xyz - p; vAf = c.y * Q2.w; vL2 = vec4(l2, c.z * Q3.w);
        vec3 nw = (modele * vec4(n, 0.0)).xyz, rd = normalize(p - Q1.xyz);
        vec3 n8 = mix(nw, rd, clamp(dot(nw, rd) + 1.0, 0.0, 1.0) * Q1.w);
        vN = n8; vT = (modele * vec4(tg, 0.0)).xyz; vB = (modele * vec4(normalize(cross(n, tg)), 0.0)).xyz;
        if (ombFx > 0.5) vLS = ombVP * vec4(p + 0.05 * n8, 1.0); }
    }`;
  const FS_J = `precision highp float; varying vec4 vc; varying vec2 t0; varying vec2 t1; varying vec2 t2; varying vec2 t3; varying vec2 t4;
    varying vec3 vT; uniform vec3 L1; uniform vec3 L2; uniform float L1dir;
    varying vec3 vN; varying vec3 vV; varying vec2 t5; varying vec2 t0r; varying vec2 t3r; varying vec2 t4r; varying vec4 vk1; varying vec2 t1r;
    vec2 tpf(vec4 a, vec4 b, vec2 uv){ vec3 u = vec3(uv, 1.0); return vec2(dot(a.xyz, u), dot(b.xyz, u)); }
    uniform sampler2D s5; uniform vec4 P4; uniform vec4 P5; uniform vec4 P6; uniform vec4 fbA; uniform vec4 fbB; uniform float fbT;
    uniform vec4 uA[6]; uniform vec4 uB[6];
    uniform sampler2D s0; uniform sampler2D s1; uniform sampler2D s2; uniform sampler2D s3; uniform sampler2D s4;
    uniform float mode; uniform vec4 dif; uniform vec4 amb; uniform vec4 P0; uniform vec4 P1; uniform vec4 P2; uniform vec4 P3; uniform float ubw;
    varying vec2 vDa; varying vec2 vDb; uniform sampler2D sc; uniform vec2 ecranT; uniform float projY; uniform float asp;
    varying float vBord; uniform float grdU; varying vec2 vAu; varying float vAf; varying vec4 vF; varying float vRimA; varying vec3 vB; varying vec4 vCel; varying vec3 vL;
    uniform vec3 ambC; uniform vec2 cAL; uniform float effA; varying vec4 vLS;
    uniform sampler2D sOmbE; uniform float aOmbE; uniform float ombT; uniform vec4 csP; uniform float effS; uniform vec3 ombC;
    varying vec4 vL2; uniform float effP;
    // OMBRE DES EFFETS (T1L / T1L2PatternFadePar / SmokePar1) : carte de la cascade 0 (t15), 5 lectures (centre, ±(t, t), ±(t, −t))
    // comparées à la profondeur − 0,0005 ; s = sat(somme x charaShadowParam.x x 0,2) x effectShadowRate ;
    // couleur x (1 + s z (c − 1)) x (1 + s w (c − 1)), c = shadowColor grisée à effectShadowGrayScale, (z, w) = charaShadowParam.zw
    // échantillonneur s15 du jeu (LU dans nie.exe : clé de la case 15 réglée par 0x14132c360 et 0x14133c9a0) : comparaison
    // GREATER (1 = point derrière la carte = dans l'ombre), adressage BORDER à 1,0 (hors carte : pas d'ombre), filtre
    // linéaire avec comparaison (0x95, réglé par la passe d'ombre d'écran et gardé) = moyenne bilinéaire de 4 comparaisons
    float cmpOE(vec2 ij, float z) { float T = 1.0 / ombT; if (ij.x < 0.0 || ij.y < 0.0 || ij.x >= T || ij.y >= T) return 0.0;
      float d = dot(texture2D(sOmbE, (ij + 0.5) * ombT).rgb, vec3(1.0, 1.0 / 255.0, 1.0 / 65025.0)) * 2.0 - 1.0; return z > d ? 1.0 : 0.0; }
    float lireOE(vec2 uv, float z) { vec2 p = uv / ombT - 0.5, i = floor(p), f = p - i;
      return mix(mix(cmpOE(i, z), cmpOE(i + vec2(1.0, 0.0), z), f.x), mix(cmpOE(i + vec2(0.0, 1.0), z), cmpOE(i + vec2(1.0, 1.0), z), f.x), f.y); }
    vec3 ombreEffetC(float fondu, vec3 oc);
    vec3 ombreEffet(float fondu) { return ombreEffetC(fondu, ombC); }
    vec3 ombreEffetC(float fondu, vec3 oc) {
      if (aOmbE < 0.5 || vLS.w <= 0.0) return vec3(1.0);
      vec3 q = vLS.xyz / vLS.w; vec2 uv = q.xy * 0.5 + 0.5; float z = min(q.z - 0.0005, 1.0);
      float sm = lireOE(uv + vec2(ombT, ombT), z) + lireOE(uv, z) + lireOE(uv - vec2(ombT, ombT), z) + lireOE(uv + vec2(ombT, -ombT), z) + lireOE(uv - vec2(ombT, -ombT), z);
      float sh = clamp(sm * csP.x * 0.2, 0.0, 1.0) * effS * fondu;
      return (1.0 + sh * csP.z * (oc - 1.0)) * (1.0 + sh * csP.w * (oc - 1.0)); }
    // PARTICULES DOUCES (« soft particles », t12 du jeu) : d = distance de la scène − distance du fragment (profondeur de la scène
    // vue de la caméra, passe _profScene) ; plage R1 = softParticleDistance x (1 − min(y², 1)), R2 = mix(R1, sd, z),
    // R = mix(R2, R1, alpha) ; adoucissement = mix(1, sat(d / R), k) — paramètres propres à chaque shader (lus dans le jeu)
    uniform sampler2D sProf; uniform float aProf; uniform vec2 pz; uniform float spD; uniform vec2 ecranP;
    float distProf() { if (aProf < 0.5) return 1e6; vec2 uv = gl_FragCoord.xy / ecranP;
      float dw = dot(texture2D(sProf, uv).rgb, vec3(1.0, 1.0 / 255.0, 1.0 / 65025.0));
      if (dw > 0.9999) return 1e6;                                  // rien derrière (ciel) : valeur d'effacement
      float Ds = pz.y / ((dw * 2.0 - 1.0) + pz.x); return max(Ds - 1.0 / gl_FragCoord.w, 0.0); }
    float R1f(float y) { return spD * (1.0 - min(y * y, 1.0)); }
    float RMIX(float y, float z, float a) { float r = R1f(y); return mix(mix(r, spD, z), r, a); }
    float SOFT(float R, float k) { if (aProf < 0.5) return 1.0; return mix(1.0, clamp(distProf() / max(R, 1e-6), 0.0, 1.0), k); }

    uniform vec2 adr[6];
    float AX(float u, float m){ if (m > 4.5) return clamp(abs(u), 0.0, 1.0); if (m > 1.5 && m < 2.5) return 1.0 - abs(mod(u, 2.0) - 1.0);
      if (m > 0.5 && m < 1.5) return fract(u); return u; }
    vec2 AD(vec2 uv, vec2 m){ return vec2(AX(uv.x, m.x), AX(uv.y, m.y)); }
    bool HB(vec2 uv, vec2 m){ return (m.x > 3.5 && m.x < 4.5 && (uv.x < 0.0 || uv.x > 1.0)) || (m.y > 3.5 && m.y < 4.5 && (uv.y < 0.0 || uv.y > 1.0)); }
    vec4 TX0(vec2 uv){ vec2 m = adr[0]; if (HB(uv, m)) return vec4(0.0); return texture2D(s0, AD(uv, m)); }
    vec4 TX1(vec2 uv){ vec2 m = adr[1]; if (HB(uv, m)) return vec4(0.0); return texture2D(s1, AD(uv, m)); }
    vec4 TX2(vec2 uv){ vec2 m = adr[2]; if (HB(uv, m)) return vec4(0.0); return texture2D(s2, AD(uv, m)); }
    vec4 TX3(vec2 uv){ vec2 m = adr[3]; if (HB(uv, m)) return vec4(0.0); return texture2D(s3, AD(uv, m)); }
    vec4 TX4(vec2 uv){ vec2 m = adr[4]; if (HB(uv, m)) return vec4(0.0); return texture2D(s4, AD(uv, m)); }
    vec4 TX5(vec2 uv){ vec2 m = adr[5]; if (HB(uv, m)) return vec4(0.0); return texture2D(s5, AD(uv, m)); }
    void main(){
      if (mode > 27.5 && mode < 28.5) {     // Effect_SmokePar1.pfxo (traduit) : Smoke2 + 2 lumières + ombre des effets
        float a = SOFT(R1f(P6.y), P6.x) * vc.a * dif.a;
        vec4 sil = mix(TX1(vCel.xy), TX1(vCel.zw), vAu.x); a *= sil.w; vec3 sv = sil.xyz * 2.0 - 1.0;
        vec4 rg = TX0(tpf(uA[0], uB[0], t0r + P0.y * vec2(-sv.x, sv.y)));
        float al = TX2(clamp(vec2(a, 1.0 - rg.w), 0.015625, 0.984375)).w; if (al - ubw < 0.0) discard;
        vec2 nt = 2.0 * rg.xy + sv.xy - 1.0;
        vec3 N = normalize(normalize(vT) * nt.x + normalize(vB) * nt.y + normalize(vN) * sv.z);
        float o = sil.w * rg.w * vAu.y;
        float x = (dot(N, normalize(vL)) * 0.5 + 0.5) * mix(1.0, o, P0.w); x = mix(x, o, P0.z);
        float d2 = length(vL2.xyz);
        vec3 t2c = TX2(vec2(vL2.w, 1.0 - (dot(N, vL2.xyz / d2) * 0.5 + 0.5))).rgb / d2;           // lumière 2 (point)
        x += dot(t2c, vec3(0.29891, 0.58661, 0.11448)) * P4.y;
        vec3 t1c = TX2(clamp(vec2(vAf, 1.0 - x), 0.015625, 0.984375)).rgb * ombreEffetC(1.0, mix(ombC, vec3(1.0), P5.w));
        float kk = 1.0 - max(max(t2c.r, t2c.g), t2c.b) * min(1.0, P4.y) * effP;
        vec3 col = (t1c * kk + t2c * P4.y) * dif.rgb * (1.0 + amb.x) * vAu.y;
        vec3 v11 = mix(ambC, vec3(1.0), P5.w); float k = mix(effA, 1.0, P6.z);
        col += k * cAL.x * (v11 - col); col *= 1.0 + k * cAL.y * (v11 - 1.0);
        gl_FragColor = vec4(col, al); return;
      }
      if (mode > 26.5 && mode < 27.5) {     // Effect_T1L2PatternFadePar.pfxo (traduit) : planche animée, éclairage toon, ombre, ambiance
        vec4 tx = mix(TX0(vCel.xy), TX0(vCel.zw), vAu.y);
        float a = tx.a * SOFT(RMIX(P0.y, P0.z, tx.a), P0.x); if (a * vc.a * dif.a - ubw < 0.0) discard;
        vec3 nm = TX1(t1).xyz * 2.0 - 1.0;                              // _NormalTex (case 1, TEXCOORD1)
        vec3 N = normalize(normalize(vT) * nm.x + normalize(vB) * nm.y + normalize(vN) * nm.z);
        float h = dot(N, normalize(vL)) * 0.5 + 0.5;
        vec3 lt = TX2(clamp(vec2(P1.w, 1.0 - h), 0.015625, 0.984375)).rgb * vAu.x * P2.y + P2.z;      // _ToonTex
        lt *= ombreEffet(1.0);
        vec3 col = tx.rgb * lt; col += effA * cAL.x * (ambC - col); col *= 1.0 + effA * cAL.y * (ambC - 1.0);
        gl_FragColor = vec4(col * dif.rgb * (1.0 + amb.x), a * vc.a * dif.a); return;
      }
      if (mode > 25.5 && mode < 26.5) {     // Effect_T1L.pfxo (traduit) : T1 + ambiance des personnages + ombre des effets
        vec4 tx = TX0(t0); float a = tx.a * SOFT(RMIX(P0.y, P0.z, tx.a), P0.x);
        if (a * vc.a * dif.a - ubw < 0.0) discard;
        vec3 col = tx.rgb * vc.rgb * dif.rgb * (1.0 + amb.x); float k = mix(effA, 1.0, P1.z);
        col += k * cAL.x * (ambC - col); col *= 1.0 + k * cAL.y * (ambC - 1.0);
        gl_FragColor = vec4(col * ombreEffet(1.0), a * vc.a * dif.a); return;      // o9.w = 0 : pas de fondu de cascade
      }
      if (mode > 24.5 && mode < 25.5) {     // Effect_Smoke2.pfxo (traduit) : fumée éclairée en dégradé « toon »
        float a = SOFT(R1f(P6.y), P6.x) * vc.a * dif.a;
        float fr = P5.z - (P5.z < 0.0 ? ceil(P5.z) : floor(P5.z));
        vec4 sil = mix(TX1(vCel.xy), TX1(vCel.zw), fr); a *= sil.w;          // _SilhouetteTex (2 images de la planche)
        vec3 sv = sil.xyz * 2.0 - 1.0;
        vec4 rg = TX0(tpf(uA[0], uB[0], t0r + P0.y * vec2(-sv.x, sv.y)));    // _RoughnessTex0
        float al = TX2(vec2(a, 1.0 - rg.w)).w; if (al - ubw < 0.0) discard;   // _ToonCPTex : alpha
        vec2 nt = 2.0 * rg.xy + sv.xy - 1.0;
        vec3 N = normalize(normalize(vT) * nt.x + normalize(vB) * nt.y + normalize(vN) * sv.z);
        float x = (dot(N, normalize(vL)) * 0.5 + 0.5) * mix(1.0, sil.w * rg.w, P0.w); x = mix(x, rg.w * sil.w, P0.z);
        vec3 col = TX2(vec2(P2.w, 1.0 - x)).rgb * vc.rgb * dif.rgb * (1.0 + amb.x);
        vec3 v10 = mix(ambC, vec3(1.0), P5.w); float k = mix(effA, 1.0, P6.z);           // ambiance des personnages
        col += k * cAL.x * (v10 - col); col *= 1.0 + k * cAL.y * (v10 - 1.0);
        gl_FragColor = vec4(col, al); return;
      }
      if (mode > 23.5 && mode < 24.5) {     // Effect_Water1.pfxo (traduit) : eau = couleur + reflet de sphère, brouillard x P1.z
        vec3 sn = TX4(t4).xyz * 2.0 - 1.0;                             // _SubNormalTex (case 4, TEXCOORD4)
        vec3 N = normalize(normalize(vT) * sn.x + normalize(vB) * sn.y + normalize(vN) * sn.z);
        vec4 tx = TX0(t0 + sn.xy * P0.x);                              // _ColorTex0 décalée par la sous-normale
        vec3 V = normalize(vV), Rr = normalize(cross(vec3(0.0, 1.0, 0.0), V)), Uu = normalize(cross(V, Rr));
        vec4 sph = TX1(vec2(0.5 + 0.5 * dot(N, Rr), 0.5 - 0.5 * dot(N, Uu)));       // _SphereTex
        vec3 col = tx.rgb * vk1.rgb * dif.rgb * (1.0 + amb.x) + sph.rgb;
        float a = sph.w * tx.w * vk1.a * dif.a * SOFT(R1f(P1.y), P1.x);
        if (a - ubw < 0.0) discard;
        gl_FragColor = vec4(col * (1.0 + P1.z * (vF.a - 1.0)) + vF.rgb * P1.z, a); return;
      }
      if (mode > 22.5 && mode < 23.5) {     // Effect_BorderLight.pfxo (traduit) : lueur là où le maillage touche le décor
        // d = profondeur de la scène − celle du fragment ; L = P0.y x alpha de _FlowTex0 ; bande = sat(d / (P0.x L)) x (1 − sat((d − P0.x L) / ((1 − P0.x) L)))
        vec4 fl = TX2(t2); float L = P0.y * fl.w, d = distProf();
        float band = clamp(d / (P0.x * L), 0.0, 1.0) * (1.0 - clamp((d - P0.x * L) / max(L * (1.0 - P0.x), 1e-6), 0.0, 1.0));
        vec4 g = TX1(vec2(P0.z, band));                               // _GrdTex
        vec2 dfl = vec2(fl.x * 2.0 - 1.0, -(fl.y * 2.0 - 1.0)) * P1.x * mix(1.0, g.w, P1.y);
        g *= vec4(vc.rgb * dif.rgb * (1.0 + amb.x), vc.a * dif.a * vRimA);
        vec4 tx = TX0(tpf(uA[0], uB[0], t0r + dfl));                  // _ColorTex0 : TEXCOORD0 brut + flux, puis u_texProj[0]
        if (g.w * tx.w - ubw < 0.0) discard;
        gl_FragColor = g * tx; return;
      }
      if (mode > 21.5 && mode < 22.5) {     // Effect_T1M1Fog.pfxo : T1M1 puis brouillard (couleur x transmission + lumière diffusée)
        vec4 tx = TX0(t0); float m_ = TX1(t1).x * tx.a; float a = m_ * SOFT(RMIX(P0.y, P0.z, m_), P0.x) * vc.a * dif.a * vRimA;
        if (a - ubw < 0.0) discard;
        vec3 col = tx.rgb * vc.rgb * dif.rgb * (1.0 + amb.x);
        gl_FragColor = vec4(col * vF.a + vF.rgb, a); return;
      }
      if (mode > 20.5 && mode < 21.5) {     // Effect_T1M1Morph.pfxo : T1M1 ; couleur = COLOR1 (COLOR0.rgb sert au déplacement)
        vec4 col = TX0(t0) * vec4(vk1.rgb * dif.rgb * (1.0 + amb.x), vk1.a * vc.a * dif.a);
        col = max(col, 0.0); float a = TX1(t1).x * col.a * SOFT(R1f(P0.y), P0.x); if (a - ubw < 0.0) discard;
        gl_FragColor = vec4(col.rgb, a); return;
      }
      if (mode > 19.5 && mode < 20.5) {     // Effect_Aura1.pfxo (traduit)
        float rim = dot(normalize(vN), normalize(vV));
        float a = max((clamp(rim / clamp(P1.w + P1.z, 0.0, 1.0), 0.0, 1.0) - P1.w) / (1.0 - P1.w), 0.0) * P3.y;
        float mk = TX2(t2).x;                                    // _MaskTex (case 2, TEXCOORD2)
        float so = SOFT(R1f(P0.y), P0.x); a *= mix(1.0, so, P2.w);
        vec4 col = TX1(vec2(a * mix(1.0, mk, P3.x), 1.0 - TX0(vAu).w));      // _ColorPlateTex[rim x masque, 1 − alpha de _ResourceTex]
        col *= vec4(dif.rgb * (1.0 + amb.x), mix(mk, 1.0, P3.x) * vAf * vc.w * dif.w); col.a *= mix(so, 1.0, P2.w);
        col = max(col, 0.0); if (col.a - ubw < 0.0) discard;
        gl_FragColor = col; return;
      }
      vec3 rgb = vc.rgb * dif.rgb * (1.0 + amb.x); float va = vc.a;
      if (mode > 98.5) { gl_FragColor = vec4(TX1(t1).x, TX2(t2).x, va, 1.0); return; }   // contrôle (masques, alpha sommet) : mode 99
      if (mode > 5.5 && mode < 6.5 || mode > 9.5 && mode < 10.5) {   // Effect_T2 / Effect_T2M1 : 2 couleurs (+ masque case 2)
        vec4 a0 = TX0(t0), a1 = TX1(t1); float a = clamp(a0.a + a1.a, 0.0, 1.0);
        if (mode > 9.5) a *= TX2(t2).x;
        vec3 cc = clamp(a0.rgb * (1.0 - a1.a * P0.w) + a1.rgb * a1.a, 0.0, 1.0);
        vec4 o = vec4(cc, a) * vec4(rgb, va * dif.a); if (o.a - ubw < 0.0) discard; gl_FragColor = o; return;
      }
      if (mode > 10.5 && mode < 12.5) {     // Effect_T1Flow2 / Effect_T1M1Flow : coordonnées déformées par une carte de flux
        float kf = mix(1.0, vc.r, P1.z); vec3 rgbF = mix(vc.rgb, vec3(1.0), P1.z) * dif.rgb * (1.0 + amb.x);
        vec4 c0; float m = 1.0;
        if (mode < 11.5) { vec2 v = TX1(t1).xy * 2.0 - 1.0 + (TX2(t2).xy * 2.0 - 1.0) * P0.w;
          c0 = TX0(tpf(uA[0], uB[0], t0r + P0.x * kf * vec2(v.x, -v.y))); }
        else { vec2 v = TX2(t2).xy * 2.0 - 1.0; vec2 d = vec2(v.x, -v.y) * kf;
          c0 = TX0(tpf(uA[0], uB[0], t0r + d * P0.x)); m = TX1(tpf(uA[1], uB[1], t1r + d * P0.y)).x; }
        c0.a *= m; if (mode > 11.5) c0.a *= SOFT(R1f(P1.y), P1.x);
        c0 *= vec4(rgbF, va * dif.a); if (c0.a - ubw < 0.0) discard; gl_FragColor = c0; return;
      }
      if (mode > 6.5 && mode < 7.5) {       // Effect_T1PatternFade : animation par cases (P0.x n°, P0.y colonnes, P0.z lignes) + fondu
        vec4 c0 = mix(TX0(t0 * fbA.zw + fbA.xy), TX0(t0 * fbB.zw + fbB.xy), fbT); c0.a *= SOFT(RMIX(P1.y, P1.z, c0.a), P1.x);
        c0 *= vec4(rgb, va * dif.a); if (c0.a - ubw < 0.0) discard; gl_FragColor = c0; return;
      }
      if (mode > 7.5 && mode < 8.5) {       // Effect_VDispRim (sans le déplacement des sommets) : couleur = COLOR1, reflet de bord
        vec2 ruv = vec2(P0.x, dot(normalize(vV), normalize(vN)));
        float rm = TX2(ruv).x; vec4 rc = TX1(ruv);
        vec4 cc = TX0(t0) * vec4(vk1.rgb * dif.rgb * (1.0 + amb.x), vk1.a * dif.a);
        float a = rm * cc.a * SOFT(R1f(P1.y), P1.x); if (a - ubw < 0.0) discard;
        gl_FragColor = vec4((1.0 - rc.a * P0.y) * cc.rgb + rc.rgb * (1.0 + P1.w) * rc.a, a); return;
      }
      if (mode > 16.5 && mode < 17.5) {     // Effect_BallAura1 (traduit)
        bool f = (P2.z >= 2.0 && P2.z < 3.0) || P2.z < 1.0;               // vertex shader : r0.xy = f ? (1, a) : (a, 1)
        float a = vc.a; vec2 r = f ? vec2(1.0, a) : vec2(a, 1.0);
        float sq_ = SOFT(R1f(P2.y), P2.x); vec2 q = P2.z < 2.0 ? vec2(1.0, sq_) : vec2(sq_, 1.0);   // pixel shader : (alpha, seuil)
        float a1 = q.x * r.x * dif.a, a2 = q.y * r.y * vBord;
        float v = TX2(t2).x - (1.0 - TX1(t1).x * P1.y * a2);
        float th = max(1.0 - P1.x, 0.005), al = clamp(min(th, v) / th, 0.0, 1.0) * a1;
        float t1_ = max(1.0 - P0.x, 0.005), t2_ = max(1.0 - P0.z, 0.005);
        float g1 = clamp(min(v - (1.0 - P0.y), t1_) / t1_, 0.0, 1.0), g2 = clamp(min(v - (1.0 - P0.w), t2_) / t2_, 0.0, 1.0);
        vec4 gc = texture2D(s0, vec2(grdU, 1.0 + g2 * (-0.5 - 0.5 * g1)));
        if (al * gc.a - ubw < 0.0) discard;
        gl_FragColor = vec4(gc.rgb * vc.rgb * dif.rgb * (1.0 + amb.x), gc.a * al); return;
      }
      if (mode > 17.5 && mode < 19.5) {     // Effect_DifferenceFlow (18) / DifferenceFlowM (19) (traduits)
        vec4 fl = TX3(t3); vec2 f = vec2(fl.x * 2.0 - 1.0, -(fl.y * 2.0 - 1.0));
        vec4 A = TX0(tpf(uA[0], uB[0], f * P0.w + t0r)); float B = TX1(tpf(uA[1], uB[1], f * P1.x + t1r)).x;
        float d = A.x - B; d = d + P0.z * (abs(d) - d);
        float ca = vc.a; float u = P0.y + P0.x * P0.y * (ca - 1.0);
        vec4 c = texture2D(s2, vec2(u, 1.0 - d)); c.a *= A.w;
        if (mode > 18.5) c.a *= TX4(t4).x;
        c.a *= SOFT(RMIX(P1.z, P2.x, c.a), P1.y);
        float va = mix(ca, 1.0, P1.w) * dif.a;
        if (c.a * va - ubw < 0.0) discard;
        gl_FragColor = vec4(c.rgb * vc.rgb * dif.rgb * (1.0 + amb.x), c.a * va); return;
      }
      if (mode > 14.5 && mode < 16.5) {     // Effect_Distortion (15) / Effect_DistortionBlur (16) : l'image derrière, décalée
        vec2 mk = TX1(t1).xw; if (mode > 15.5) mk.y *= SOFT(RMIX(P2.y, P2.z, mk.y), P2.x); if (mk.y * vc.a * dif.a - ubw < 0.0) discard;
        vec2 d = TX0(t0).xy * 2.0 - 1.0; vec2 o = (d.x * vDa + d.y * vDb) * mk.x;      // jeu : t.x x (ax, bx) + t.y x (ay, by)
        float pp = projY * projY, k = mix(0.17 * pp, 0.0085, P1.w) * gl_FragCoord.z;
        // o3.zw = k2 x u_eyeNearFarInvAspect.zw ; zw = (tan(fov/2) x aspect, tan(fov/2)) : lu dans nie.exe (0x1413486d0 remplit
        // cb5[3] : near, far, tan(caméra +0x2E4 x 0,5) x (+0x2E8 = largeur / hauteur), tan(+0x2E4 x 0,5) ; tan vérifiée à l'émulateur)
        vec2 zw = vec2(asp, 1.0) / projY, nz = normalize(zw); float k2 = nz.y / nz.x * 2.97 + 0.03;
        o *= k * vec2(k2 * zw.y, k2 * zw.x);
        vec2 uv = vec2(gl_FragCoord.x / ecranT.x, 1.0 - gl_FragCoord.y / ecranT.y);     // repère Direct3D (y vers le bas)
        uv -= (uv - 0.5) * clamp(P2.w, 0.0, 1.0);
        vec3 c;
        if (mode < 15.5) { vec2 u = o * P0.x + uv; c = texture2D(sc, vec2(u.x, 1.0 - u.y)).rgb; }
        else { vec3 S[6]; float W[6]; W[0] = 0.285714; W[1] = 0.238095; W[2] = 0.190476; W[3] = 0.142857; W[4] = 0.095238; W[5] = 0.047619;
          vec3 A = vec3(0.0), Wt = vec3(0.0);
          for (int i = 0; i < 6; i++) { vec2 u = o * (P0.x + float(i) * P0.y) + uv; vec3 x = texture2D(sc, vec2(u.x, 1.0 - u.y)).rgb; A += x; Wt += x * W[i]; }
          A /= 6.0; c = mix(A, Wt, P0.z) + P0.w; c = pow(max(c, 0.0), vec3(P1.x)); c = c + P1.y * (1.0 - 2.0 * c);
          float y = dot(c, vec3(0.29891, 0.58661, 0.11448)); c = y + P1.z * (c - y); }
        gl_FragColor = vec4(c * vc.rgb * dif.rgb * (1.0 + amb.x), mk.y * vc.a * dif.a); return;
      }
      if (mode > 13.5 && mode < 14.5) {     // Effect_Solid (traduit, sans ombre portée ni brouillard) — tout en repère caméra
        vec3 N0 = normalize(vN), T0 = normalize(vT - N0 * dot(vT, N0)), B0 = cross(N0, T0);
        vec3 nm = TX1(t1).xyz * 2.0 - 1.0; vec3 N = normalize(T0 * nm.x + B0 * nm.y + N0 * nm.z);
        vec3 V = normalize(vV); vec4 c0 = TX0(t0); vec4 st = TX3(t2);
        vec3 Rr = normalize(cross(vec3(0.0, 1.0, 0.0), V)), Uu = cross(V, Rr);
        vec3 sq = vec3(dot(N, Rr) * 0.5, dot(N, Uu) * 0.5, 1.0);
        vec3 sph = TX4(vec2(dot(uA[4].xyz, sq) + 0.5, -dot(uB[4].xyz, sq) + 0.5)).rgb;
        vec3 l1 = normalize(L1dir > 0.5 ? L1 : L1 + vV);                       // lumière 1 : direction, ou point (P0.xyz)
        vec3 toon1 = TX2(vec2(P0.w, 1.0 - (dot(N, l1) * 0.5 + 0.5))).rgb;
        float nv = dot(V, N), fres = P4.y + (P4.z - P4.y) * (1.0 - nv) * (1.0 - nv);
        vec3 t1c = toon1 * fres; vec3 spec = pow(clamp(dot(N, normalize(l1 + V)), 0.0, 1.0), P3.w) * t1c;
        vec3 v10 = L2 + vV; float invd = 1.0 / max(length(v10), 1e-4); vec3 l2 = v10 * invd;  // lumière 2 : point (P1.xyz)
        vec3 toon2 = TX2(vec2(P1.w, 1.0 - (dot(N, l2) * 0.5 + 0.5))).rgb * invd * fres;
        spec += toon2 * pow(clamp(dot(N, normalize(l2 + V)), 0.0, 1.0), P3.w) * P2.y;
        vec3 specOut = st.rgb * (sph + spec * P4.x); float sw = st.a * P2.y * invd;
        float tr = pow(clamp(dot(V, -(N * P2.w + l2)), 0.0, 1.0), P3.x) + P3.y;
        vec4 cc = c0 * vec4(rgb, va * dif.a); if (cc.a - ubw < 0.0) discard;
        vec3 o = cc.rgb * (t1c + toon2 * P2.y) + specOut;
        vec3 ramp = TX2(vec2(P3.z, 1.0 - tr * sw)).rgb; o += max(tr * sw - (1.0 - ramp), 0.0);
        o = mix(c0.rgb * 0.75, o, clamp(nv * 5.0, 0.0, 1.0));
        gl_FragColor = vec4(o, cc.a); return;
      }
      if (mode > 12.5 && mode < 13.5) {     // Effect_SolidToon1 (traduit, sans ombre portée ni brouillard)
        vec3 N0 = normalize(vN), T0 = normalize(vT - N0 * dot(vT, N0)), B0 = cross(N0, T0);
        vec3 nm = TX1(t1).xyz * 2.0 - 1.0; vec3 N = normalize(T0 * nm.x + B0 * nm.y + N0 * nm.z);
        vec3 V = normalize(vV); vec3 Rr = normalize(cross(vec3(0.0, 1.0, 0.0), V)), Uu = cross(V, Rr);
        vec3 sq = vec3(dot(N, Rr) * 0.5, dot(N, Uu) * 0.5, 1.0);
        vec4 sph = TX4(vec2(dot(uA[4].xyz, sq) + 0.5, -dot(uB[4].xyz, sq) + 0.5));
        vec4 c0 = TX0(t0); vec4 cc = c0 * dif; float lum = dot(c0.rgb, vec3(0.29891, 0.58661, 0.11448));
        float a = cc.a * va; if (a * sph.a - ubw < 0.0) discard;
        vec3 l1 = normalize(L1dir > 0.5 ? L1 : L1 + vV); float nl1 = dot(N, l1);
        vec4 so = TX3(t2); float h = nl1 * 0.5 + 0.5; h += P0.z * (so.w - h);      // occlusion (alpha case 3)
        vec3 r1 = TX2(vec2(P1.w, 1.0 - h)).rgb; r1 += P0.y * lum * (1.0 - r1);
        vec3 v10 = L2 + vV; float invd = 1.0 / max(length(v10), 1e-4);
        vec3 r2 = TX2(vec2(P3.w, 1.0 - (dot(N, v10 * invd) * 0.5 + 0.5))).rgb * invd * P0.w;
        float th = P2.w - 0.01; float rim = clamp((clamp(nl1 * (1.0 - dot(V, N)), 0.0, 1.0) - th) / max(P2.w - th, 1e-4), 0.0, 1.0);
        vec3 col = cc.rgb * (r1 + r2) + sph.rgb * so.rgb + rim * P2.xyz; float g = 1.0 + amb.x;
        gl_FragColor = mix(vec4(col * g, a * sph.a), vec4(cc.rgb * g, sph.a * cc.a * va), P4.x); return;
      }
      if (mode > 2.5 && mode < 3.5) {       // Effect_T3ThresholdF : nuages avec carte de flux (case 5), masque animé par cases
        vec2 fl = TX5(t5).xy * 2.0 - 1.0; vec2 f = vec2(fl.x, -fl.y);
        vec2 ua = t3r * fbA.zw + fbA.xy + f * (vk1.a * P5.x), ub = t3r * fbB.zw + fbB.xy + f * (vk1.a * P5.x);
        vec4 qa = TX3(ua), qb = TX3(ub); vec3 m0 = mix(vec3(qa.x, qa.y, qa.w), vec3(qb.x, qb.y, qb.w), fbT);
        vec2 g = vec2(m0.x * 2.0 - 1.0, -(m0.y * 2.0 - 1.0));
        vec3 q = vec3(t4r + g * P4.z + f * (vk1.a * P5.y), 1.0); float m1 = TX4(vec2(dot(uA[4].xyz, q), dot(uB[4].xyz, q))).x;
        vec3 q0 = vec3(t0r + f * (vk1.a * P4.w) + g * P4.y, 1.0); vec2 cu = vec2(dot(uA[0].xyz, q0), dot(uB[0].xyz, q0));
        float sf = clamp(P5.w + P6.x, 0.0, 1.0);
        float fres = sf > 0.0 ? max((min(abs(dot(normalize(vV), normalize(vN))) / sf, 1.0) - P6.x) / max(1.0 - P6.x, 1e-4), 0.0) : 1.0;
        float s3_ = SOFT(R1f(P3.y), P3.x), thF = mix(1.0, s3_, P2.w), alF = mix(s3_, 1.0, P2.w);
        vec3 o6 = fres * mix(1.0, va, P2.z) * P2.y * vk1.rgb * thF;
        vec3 inv = 1.0 / clamp(1.0 - vec3(P0.x, P1.x, P2.x), 0.01, 1.0);
        vec3 r2 = vec3(2.0 - P0.y - m0.z * o6.x, 2.0 - P1.y - m0.z * o6.y, 1.0 - m0.z * o6.z);
        vec3 k = clamp((max(vec3(m1), r2) - r2) * inv, 0.0, 1.0);
        vec4 col = mix(TX1(cu), TX0(cu), k.x); col = mix(TX2(cu), col, k.y); col.a *= k.z;
        col *= vec4(rgb, mix(va, 1.0, P2.z) * dif.a); col.a *= alF; if (col.a - ubw < 0.0) discard; gl_FragColor = col; return;
      }
      if (mode > 3.5 && mode < 4.5) {       // Effect_T1M1(_low) : T1 dont l'alpha est multiplié par un masque (case 1)
        vec4 tx = TX0(t0); float m_ = TX1(t1).x * tx.a; float a = m_ * SOFT(RMIX(P0.y, P0.z, m_), P0.x) * min(va * dif.a, 1.0);
        if (a - ubw < 0.0) discard; gl_FragColor = vec4(tx.rgb * rgb, a); return;
      }
      if (mode > 4.5 && mode < 5.5) {       // Effect_T1M1Rim : reflet de bord = rampe (case 1) et masque (case 3) lus à (P0.x, N.V)
        vec2 ruv = vec2(P0.x, dot(normalize(vV), normalize(vN)));
        float rm = TX3(ruv).x; vec4 rc = TX1(ruv);
        vec4 cc = TX0(t0); cc.a *= TX2(t2).x; cc *= vec4(rgb, va * dif.a);
        float a = rm * cc.a * SOFT(R1f(P0.w), P0.z); if (a - ubw < 0.0) discard;
        gl_FragColor = vec4((1.0 - rc.a * P0.y) * cc.rgb + rc.rgb * (1.0 + P1.x) * rc.a, a); return;
      }
      if (mode < 0.5) {                     // Effect_T1 / Effect_T1_low
        vec4 tx = TX0(t0); float a = tx.a * SOFT(RMIX(P0.y, P0.z, tx.a), P0.x) * min(va * dif.a, 1.0);
        if (a - ubw < 0.0) discard; gl_FragColor = vec4(tx.rgb * rgb, a);
      } else if (mode < 1.5) {              // Effect_ThresholdGrd(_low) : 2 bruits -> seuils -> couleur dans le dégradé
        bool fl = (P2.z >= 2.0 && P2.z < 3.0) || P2.z < 1.0; float v1w = fl ? 1.0 : va; float o3x = fl ? va : 1.0;
        { float sg_ = SOFT(R1f(P2.y), P2.x); if (P2.z < 2.0) o3x *= sg_; else v1w *= sg_; }
        float r = TX2(t2).x - (1.0 - TX1(t1).x * P1.y * o3x);
        float dy = max(1.0 - P0.x, 0.005), dz = max(1.0 - P0.z, 0.005);
        float ty = clamp(min(r - (1.0 - P0.y), dy) / dy, 0.0, 1.0), tz = clamp(min(r - (1.0 - P0.w), dz) / dz, 0.0, 1.0);
        vec4 g = TX0(vec2(P2.w, 1.0 + tz * (ty * -0.5 - 0.5)));
        float da = max(1.0 - P1.x, 0.005); float a = clamp(min(r, da) / da, 0.0, 1.0) * v1w * dif.a;
        if (a * g.a - ubw < 0.0) discard; gl_FragColor = vec4(g.rgb * rgb, g.a * a);
      } else {                              // Effect_TestThreshold (matériaux « T3Threshold » : nuages, fumées)
        float s2_ = SOFT(R1f(P3.y), P3.x);
        float o4w = mix(1.0, va, P2.z) * P2.y * mix(1.0, s2_, P2.w); float aV = mix(va, 1.0, P2.z) * dif.a * mix(s2_, 1.0, P2.w);
        vec3 inv = 1.0 / clamp(1.0 - vec3(P0.x, P1.x, P2.x), 0.01, 1.0);
        float ma = TX3(t3).x, mb = TX3(t3 + P0.zw).x, mc = TX3(t3 + P1.zw).x;
        float na = TX4(t4).x, nb = TX4(t4 + P0.zw).x, nc = TX4(t4 + P1.zw).x;
        float rx = (2.0 - P0.y) - mb * o4w, ry = (2.0 - P1.y) - mc * o4w, rz = 1.0 - ma * o4w;
        float k0 = clamp((max(rx, nb) - rx) * inv.x, 0.0, 1.0), k1 = clamp((max(ry, nc) - ry) * inv.y, 0.0, 1.0), k2 = clamp((max(rz, na) - rz) * inv.z, 0.0, 1.0);
        vec4 col = mix(TX1(t0), TX0(t0), k0); col = mix(TX2(t0), col, k1); col.a *= k2;
        col *= vec4(rgb, aV); if (col.a - ubw < 0.0) discard; gl_FragColor = col;
      }
    }`;

  // rendu « dessin animé » des personnages (style du jeu) : lumière en 2 tons modulée par la carte d'ombres <tex>oc
  // (jaune = éclairé, rouge foncé = ombre), contour par coque inversée d'épaisseur constante à l'écran (couleur <tex>line)
  const VS_TOON = `attribute vec3 p; attribute vec3 n; attribute vec2 t; uniform mat4 mvp; uniform float contour; uniform float largeur;
    uniform vec2 ecran; varying vec3 vn; varying vec2 vt; varying vec3 vw; varying vec4 vF; uniform vec3 oeil; uniform vec3 lDir;
    ` + FOG_GLSL + `
    void main(){ vec4 c = mvp * vec4(p, 1.0);
      if (contour > 0.5) { vec4 c2 = mvp * vec4(p + n * 0.02, 1.0); vec2 d = c2.xy / c2.w - c.xy / c.w; float l = length(d);
        if (l > 1e-6) d /= l; c.xy += d * largeur * c.w * 2.0 / ecran; }
      gl_Position = c; vn = n; vt = t; vw = p; vF = aFog > 0.5 ? brouillard(p, oeil, lDir) : vec4(0.0, 0.0, 0.0, 1.0); }`;
  const FS_TOON = `precision highp float; varying vec3 vn; varying vec2 vt; uniform sampler2D tex; uniform sampler2D ombre;
    uniform float aTex; uniform float aOmbre; uniform vec3 lum; uniform vec3 couleurContour; uniform float contour; uniform float noir; uniform float profPack;
    varying vec3 vw; uniform float nPL; uniform vec4 plPos[4]; uniform vec4 plCol[4]; uniform vec4 plToon; uniform vec4 plBlend; uniform vec2 plRim; uniform vec4 plRate; uniform vec3 oeil;
    varying vec4 vF; uniform float fOcc; uniform float fChara; uniform float stOn; uniform vec3 stCol; uniform vec4 stRim; uniform float stPow;
    void main(){ if (profPack > 0.5) { vec3 e = fract(gl_FragCoord.z * vec3(1.0, 255.0, 65025.0)); e -= e.yzz * vec3(1.0 / 255.0, 1.0 / 255.0, 0.0); gl_FragColor = vec4(e, 0.5); return; }   /* passe de profondeur (Direct3D) ; alpha 0.5 = joueur */
      vec4 a = aTex > 0.5 ? texture2D(tex, vt) : vec4(0.85, 0.85, 0.85, 1.0);
      if (noir > 0.5) a = vec4(0.07, 0.07, 0.08, 1.0);                  // silhouette noire (joueur mannequin)
      if (contour > 0.5) { gl_FragColor = vec4(a.rgb * 0.28 + couleurContour * 0.02, 1.0); return; }   // contour = couleur de l'objet assombrie
      if (a.a < 0.35) discard;
      vec3 N = normalize(vn); float ndl = dot(N, normalize(lum));
      float eclaire = smoothstep(-0.02, 0.06, ndl);
      vec4 oc = aOmbre > 0.5 ? texture2D(ombre, vt) : vec4(1.0, 1.0, 0.0, 1.0);
      eclaire *= smoothstep(0.35, 0.65, oc.g);
      vec3 teinteOmbre = vec3(0.70, 0.64, 0.80) * mix(0.82, 1.0, oc.r);
      vec3 col = mix(a.rgb * teinteOmbre, a.rgb, eclaire);
      col += vec3(0.06) * pow(max(N.y, 0.0), 4.0) * eclaire;            // léger reflet du ciel en haut
      // LUMIÈRES PONCTUELLES (traduit de chr_toon.pfxo, boucle sur u_pointLights, masque & 1) : par lumière,
      // q = sat(1 - d / att)² x toon.y, nd = N.(pos - P) - toon.x, w = sat(q² x sat(nd) + sat(nd + 1) x sat(q) x toon.w) ;
      // S = somme(clr x blend.x x w), W = somme(w) ; Y = luminance de la texture ; C = S x Y x rate.z ;
      // couleur += W x toon.z x blend.y x (C - couleur), puis ajout « écran » : A = C + sat(C x rim.y) x [sat((1 - N.V)² x rim.x) x W > 0,3],
      // couleur += A - couleur x A x rate.x
      if (nPL > 0.5) { vec4 S = vec4(0.0);
        for (int i = 0; i < 4; i++) { if (float(i) >= nPL) break; vec3 d = plPos[i].xyz - vw; float l = max(length(d), 1e-5);
          float q = clamp((l - plPos[i].w) / -plPos[i].w, 0.0, 1.0); q = q * q * plToon.y;
          float nd = dot(N, d) - plToon.x;
          float w = clamp(q * q * clamp(nd, 0.0, 1.0) + clamp(nd + 1.0, 0.0, 1.0) * clamp(q, 0.0, 1.0) * plToon.w, 0.0, 1.0);
          S += vec4(plCol[i].rgb * plBlend.x * w, w); }
        float Y = dot(a.rgb, vec3(0.29891, 0.58661, 0.11448));
        vec3 C = S.rgb * Y * plRate.z;
        col += S.a * plToon.z * plBlend.y * (C - col);
        float nv = 1.0 - clamp(dot(N, normalize(oeil - vw)), 0.0, 1.0);
        vec3 A = C + clamp(C * plRim.y, 0.0, 1.0) * (clamp(nv * nv * plRim.x, 0.0, 1.0) * S.a > 0.3 ? 1.0 : 0.0);
        col += A - col * A * plRate.x; }
      // brouillard (chr_toon.pfxo) : f = mix((0,0,0,1), brouillard du sommet, charaGrTParam.w) ; couleur x f.a + sat(t13 + occl) x f.rgb (t13 pris = 0)
      vec4 fz = mix(vec4(0.0, 0.0, 0.0, 1.0), vF, fChara); col = col * fz.a + fOcc * fz.rgb;
      // EFFET DE STATUT (aura du ballon en cinématique, chr_toon_effstatus.pfxo) : couleur x StatusColor + contour lumineux
      if (stOn > 0.5) { float fr = 1.0 - clamp(dot(N, normalize(oeil - vw)), 0.0, 1.0); vec3 R = stRim.rgb * stRim.w * pow(max(fr, 1e-6), stPow);
        vec3 s3 = clamp(R, 0.0, 1.0) * 0.3; col = col * stCol + min(a.a * 5.0, 1.0) * (R - s3) + s3; }
      gl_FragColor = vec4(col, 1.0); }`;
  const FS = `precision highp float; varying vec4 vc; varying vec2 vt; uniform vec4 teinte; uniform float force; uniform float profPack;
    uniform sampler2D tex; uniform float aTex; uniform float aLueur; uniform float lueurH; uniform float garderOr;
    uniform sampler2D forme; uniform sampler2D detail; uniform float aNuage; uniform vec3 cOmbre; uniform vec3 cLum;
    varying vec3 vw; varying vec3 vnw; uniform float aPL; uniform float nPL; uniform vec4 plPos[4]; uniform vec4 plCol[4]; uniform vec3 plK;
    vec3 hsv(vec3 c){ vec4 K = vec4(0.0, -1.0/3.0, 2.0/3.0, -1.0); vec4 p = mix(vec4(c.bg, K.wz), vec4(c.gb, K.xy), step(c.b, c.g));
      vec4 q = mix(vec4(p.xyw, c.r), vec4(c.r, p.yzx), step(p.x, c.r)); float d = q.x - min(q.w, q.y);
      return vec3(abs(q.z + (q.w - q.y) / (6.0 * d + 1e-10)), d / (q.x + 1e-10), q.x); }
    vec3 rgb(vec3 c){ vec3 p = abs(fract(c.xxx + vec3(1.0, 2.0/3.0, 1.0/3.0)) * 6.0 - 3.0); return c.z * mix(vec3(1.0), clamp(p - 1.0, 0.0, 1.0), c.y); }
    void main(){ if (profPack > 0.5) { vec3 e = fract(gl_FragCoord.z * vec3(1.0, 255.0, 65025.0)); e -= e.yzz * vec3(1.0 / 255.0, 1.0 / 255.0, 0.0); gl_FragColor = vec4(e, 1.0); return; }   /* passe de profondeur (Direct3D) */
      vec4 tx = aTex > 0.5 ? texture2D(tex, vt) : vec4(1.0); vec4 v = vc;
      if (aNuage > 0.5) tx = vec4(mix(cOmbre, cLum, texture2D(detail, vt).r), smoothstep(0.08, 0.45, texture2D(forme, vt).r));   // nuage : forme (bord durci, comme le seuil du jeu) + ombrage
      if (aLueur > 0.5) { vec3 h = hsv(v.rgb); bool or_ = garderOr > 0.5 && h.x * 360.0 < 70.0 && h.y > 0.15;
        if (h.y > 0.02 && !or_) v.rgb = rgb(vec3(lueurH / 360.0, min(1.0, h.y * 1.3), h.z)); }
      vec4 k = v * teinte * tx;
      // LUMIÈRES PONCTUELLES (shader du stade map_basic.pfxo, boucle sur u_pointLights) : par lumière (masque & 2),
      // clr x sat((1 - d / atténuation)² x N.L) ; somme x mapPointLightPow ; puis x texture x couleur du sommet x mapAmbient
      if (aPL > 0.5) { vec3 N = normalize(vnw), s = vec3(0.0);
        for (int i = 0; i < 4; i++) { if (float(i) >= nPL) break; vec3 d = plPos[i].xyz - vw; float l = max(length(d), 1e-5);
          float a = clamp((l - plPos[i].w) / -plPos[i].w, 0.0, 1.0); s += plCol[i].rgb * clamp(a * a * dot(N, d) / l, 0.0, 1.0); }
        k.rgb += v.rgb * tx.rgb * s * plK; }
      gl_FragColor = vec4(k.rgb * force, k.a * force); }`;


  // VRAI SHADER DU STADE (13/11/2026) : traduction de dx11/shader/1.00.41/map_pbrt1.pfxo (+ variantes cutout, pbrt1l, pbrt2,
  // map_t1_cutout, map_basic). Registres : cb6 = réglages de lumière du stade (CLightData +0x140), cb4 = matériau.
  // Pas reproduit (APPROCHÉ) : ombres portées et occlusion à l'écran (in_texPreShading = 0 ; pour le brouillard t13.z pris = 0),
  // réglages des cubemaps globales (cb9 : une seule cubemap, poids 1), seuil des « cutout » (0,5), map_pbrt1w traité comme pbrt1.
  const VS_MAP = `attribute vec3 p; attribute vec4 c; attribute vec2 t; attribute vec3 nrm; attribute vec4 tg;
    uniform mat4 mvp; uniform vec4 tpA; uniform vec4 tpB; uniform vec4 diff; uniform vec4 amb; uniform vec3 oeil; uniform vec3 lDir;
    ` + FOG_GLSL + `
    varying vec4 vc; varying vec2 vt; varying vec3 vw; varying vec3 vn; varying vec4 vtg; varying vec4 vF;
    void main(){ gl_Position = mvp * vec4(p, 1.0); vw = p; vn = nrm; vtg = tg; vc = c * diff;
      vec3 u = vec3(t, 1.0); vt = vec2(dot(tpA.xyz, u), dot(tpB.xyz, u));
      vF = vec4(0.0, 0.0, 0.0, 1.0);
      if (aFog > 0.5 && amb.w > 0.0) vF = brouillard(p, oeil, lDir); }`;
  const FS_MAP = `#extension GL_EXT_shader_texture_lod : enable
    #extension GL_OES_standard_derivatives : enable
    precision highp float;
    varying vec4 vc; varying vec2 vt; varying vec3 vw; varying vec3 vn; varying vec4 vtg; varying vec4 vF; uniform float fOcc;
    uniform sampler2D t0; uniform sampler2D t1; uniform sampler2D t2; uniform sampler2D t3; uniform samplerCube cube; uniform float aCube;
    uniform float genre; uniform float aNrm; uniform float couches; uniform float coupe; uniform float lodMax;
    uniform vec4 sp0; uniform vec4 sp1; uniform vec4 sp2; uniform vec4 sp3; uniform vec4 sp6; uniform vec4 amb;
    uniform vec3 oeil; uniform vec3 mapAmb; uniform vec3 lDir; uniform vec3 lCol; uniform vec3 lAmb; uniform vec4 LI; uniform vec4 IBL; uniform vec4 PS;
    uniform float plPow; uniform float nPL; uniform vec4 plPos[4]; uniform vec4 plCol[4];
    uniform sampler2D omb; uniform sampler2D omb1; uniform sampler2D omb2; uniform mat4 sunVP; uniform mat4 sunVP1; uniform mat4 sunVP2; uniform float aOmb; uniform vec2 ombT;
    uniform vec3 ombLoin; uniform vec3 camAv; uniform mat4 invVP; uniform mat4 invVP1; uniform mat4 invVP2;
    uniform vec3 ombB; uniform vec3 ombDir; uniform float ombN0; uniform float ombS;
    // OMBRE PORTÉE (shadow_ss.pfxo du jeu : point décalé de 0,1 le long de la normale puis de mapShadowBias.x (0,12 m) vers
    // le soleil, comparé à la carte de profondeur vue du soleil ; 1 = dans l'ombre). APPROCHÉ : une seule carte (le jeu en a 3).
    // OMBRE PORTÉE : traduit de shadow_ss.pfxo (registres cb12 remplis par nie.exe 0x14133c9a0), en repère monde :
    //  1. P décalé de 0,1 le long de la normale de la FACE (dérivées d'écran), cascade = première tranche qui dépasse la profondeur de vue ;
    //  2. trois lectures de la carte (centre, + 1 texel en v, + 1 texel en u) remises en 3D -> pente de la surface vue du soleil (Ns) ;
    //  3. d = distance jusqu'au point du centre du texel (au moins 0,1 texel) à la profondeur de P ;
    //     biais = clamp(d / cos x sin x B.y, 0, B.z) + B.x, B = shadowBiasParam ; P poussé du biais vers le soleil, puis comparé.
    // DÉDUIT : orientation des normales (vers la caméra pour la face, vers le soleil pour Ns) ; 1 = dans l'ombre.
    vec4 lireO(float k, vec2 uv) { if (k < 0.5) return texture2D(omb, uv); if (k < 1.5) return texture2D(omb1, uv); return texture2D(omb2, uv); }
    float profO(float k, vec2 uv) { return dot(lireO(k, uv).rgb, vec3(1.0, 1.0 / 255.0, 1.0 / 65025.0)) * 2.0 - 1.0; }   // profondeur Direct3D (0..1)
    vec3 versMonde(float k, vec2 uv, float z) { vec4 c = vec4(uv * 2.0 - 1.0, z, 1.0);
      vec4 w = k < 0.5 ? invVP * c : (k < 1.5 ? invVP1 * c : invVP2 * c); return w.xyz / w.w; }
    vec4 versOmbre(float k, vec3 P) { return k < 0.5 ? sunVP * vec4(P, 1.0) : (k < 1.5 ? sunVP1 * vec4(P, 1.0) : sunVP2 * vec4(P, 1.0)); }
    float ombre(vec3 P0, vec3 Nv, vec3 L) {
      if (aOmb < 0.5) return 0.0;
    #ifdef GL_OES_standard_derivatives
      vec3 Nf = normalize(cross(dFdx(P0), dFdy(P0)));
    #else
      vec3 Nf = Nv;
    #endif
      if (dot(Nf, oeil - P0) < 0.0) Nf = -Nf;
      vec3 P = P0 + Nf * 0.1;
      float pv = dot(P - oeil, camAv);
      if (pv > ombLoin.z) return 0.0;
      float k = pv <= ombLoin.x ? 0.0 : (pv <= ombLoin.y ? 1.0 : 2.0);
      vec4 q = versOmbre(k, P); if (q.w <= 0.0) return 0.0;
      vec2 uv = q.xy / q.w * 0.5 + 0.5; float zP = q.z / q.w;
      if (uv.x < 0.0 || uv.x > 1.0 || uv.y < 0.0 || uv.y > 1.0 || zP > 1.0) return 0.0;
      float t = 1.0 / ombS;
      float d0 = profO(k, uv), d1 = profO(k, uv + vec2(0.0, t)), d2 = profO(k, uv + vec2(t, 0.0));
      vec3 W0 = versMonde(k, uv, d0), W1 = versMonde(k, uv + vec2(0.0, t), d1), W2 = versMonde(k, uv + vec2(t, 0.0), d2);
      vec3 Ns = normalize(cross(W1 - W0, W2 - W0)); if (dot(Ns, ombDir) < 0.0) Ns = -Ns;
      vec2 o = (floor(uv * ombS) + 0.5) * t - uv; o = max(abs(o), vec2(0.1 * t));
      float dist = length(versMonde(k, uv + o, zP) - P);
      float cs = dot(ombDir, Ns); vec3 pe = Ns - ombDir * cs; float sn = dot(Ns, pe * inversesqrt(max(dot(pe, pe), 1e-12)));
      float b = clamp(dist / max(cs, 1e-4) * sn * ombB.y, 0.0, ombB.z) + ombB.x;
      vec4 q2 = versOmbre(k, P + ombDir * b);
      return d0 - q2.z / q2.w >= 0.0 ? 0.0 : 1.0; }
    // fondu des ombres (map_pbrt1 / basic / t1_cutout / pbrt2) : 1 − t⁴, t = sat((profondeur de vue − near₀) / (far₂ − near₀))
    float fonduO() { float t = clamp((dot(vw - oeil, camAv) - ombN0) / (ombLoin.z - ombN0), 0.0, 1.0); t *= t; return 1.0 - t * t; }
    vec3 cubeL(vec3 d, float l) {
    #ifdef GL_EXT_shader_texture_lod
      return textureCubeLodEXT(cube, d, l).rgb;
    #else
      return textureCube(cube, d).rgb;
    #endif
    }
    vec3 relief(vec2 xy) { vec2 r = (xy - 0.5) * sp6.y; vec3 q = normalize(vec3(r + r, 1.0)); return vec3(q.xy * sp6.y, q.z); }
    void main(){
      vec3 V = normalize(oeil - vw), N0 = normalize(vn);
      vec4 a = texture2D(t0, vt); vec4 nm = texture2D(t1, vt);
      if (coupe > 0.5 && a.a < 0.5) discard;
      // lumières ponctuelles (masque & 2) : clr x sat((1 - d / att)² x N.L)
      vec3 N = N0;
      if (genre < 1.5) {                       // PBR
        float w = 0.0;
        if (couches > 0.5) { vec2 uA = vt * sp0.x, uB = vt * sp0.y; vec4 a2 = texture2D(t2, uB);
          w = pow(clamp(vc.a * 2.0 + a2.a - 1.0, 0.0, 1.0), sp3.x);
          vec4 a1 = texture2D(t0, uA); nm = texture2D(t1, uA); vec4 nm2 = texture2D(t3, uB);
          a = mix(a1, a2, w);
          vec3 r1 = relief(nm.xy), r2 = relief(nm2.xy); vec3 r = mix(r1, r2, w);
          vec4 T = vtg / length(vtg); vec3 B = cross(N0, T.xyz) * T.w;
          N = normalize(N0 * r.z + T.xyz * r.x + B * r.y); nm.zw = mix(nm.zw, nm2.zw, w); }
        else if (aNrm > 0.5) { vec3 r = relief(nm.xy); vec4 T = vtg / length(vtg); vec3 B = cross(N0, T.xyz) * T.w;
          N = normalize(N0 * r.z + T.xyz * r.x + B * r.y); }
        else nm.zw = nm.xy;                    // pbrt1l : t1.zw lus en xy
        float rgh = nm.z * LI.w, inv = 1.0 - rgh, al = max(rgh * rgh, 1e-4), al2 = al * al;
        vec3 dc = (1.0 - nm.w) * a.rgb, F0 = max(nm.w * a.rgb, vec3(sp2.y));
        float lod = (1.0 - inv * inv * inv * inv) * 7.0;
        float NV = dot(V, N); vec3 R = 2.0 * NV * N - V;
        vec3 spI = aCube > 0.5 ? cubeL(R, min(lod, lodMax)) : vec3(0.5), dfI = aCube > 0.5 ? cubeL(N, min(lod, lodMax)) : vec3(0.5);
        spI *= IBL.xyz * PS.w; dfI *= IBL.w * IBL.xyz;
        vec3 L = normalize(lDir); float NL = dot(N, L);
        float fr = pow(1.0 - clamp(NV, 0.0, 1.0), 4.0); fr = fr * (1.0 - sp2.y) + sp2.y;
        float kF = sp2.z * PS.y * fr * inv;
        vec3 H = L + V; H *= inversesqrt(max(dot(H, H), 0.001));
        float NH = clamp(dot(N, H), 0.0, 1.0), LH = clamp(dot(L, H), 0.0, 1.0);
        float d = pow(NH, sp1.y) * (al2 - 1.0) + 1.00001;
        float sp = sqrt(max(al2 / (d * d * (al + 0.5) * max(LH * LH, 0.1) * 4.0), 1e-4)) * sp1.x * PS.x;
        float om = 1.0 - max(clamp((NL - 0.2) * -10.0, 0.0, 1.0), ombre(vw, N0, L)) * fonduO();   // face à l'envers du soleil, ou ombre portée
        vec3 S = vec3(0.0);
        for (int i = 0; i < 4; i++) { if (float(i) >= nPL) break; vec3 dd = plPos[i].xyz - vw; float l = max(length(dd), 1e-5);
          float q = clamp((l - plPos[i].w) / -plPos[i].w, 0.0, 1.0); S += plCol[i].rgb * clamp(q * q * dot(N, dd) / l, 0.0, 1.0); }
        vec3 lum = max(clamp(NL, 0.0, 1.0) * lCol * om + S * plPow, LI.xyz);
        vec3 col = (sp * lCol * om * F0 + dc) * lum * 0.666 + dc * dfI;
        col += spI * mix(F0, vec3(1.0), kF);
        float em = couches > 0.5 || coupe > 0.5 ? 0.0 : mix(clamp(a.a, 0.0, 1.0), 1.0, sp0.z);
        if (coupe > 0.5 && couches < 0.5) em = texture2D(t2, vt).x;
        col = col * mapAmb + a.rgb * amb.x * PS.z * em;
        gl_FragColor = vec4(col * vc.rgb * vF.a + fOcc * vF.rgb, 1.0); return;
      }
      if (genre > 3.5) { gl_FragColor = vec4(a.rgb * vc.rgb, 1.0); return; }   // map_nolight
      // map_t1_cutout (genre 2) et map_basic (genre 3)
      vec3 L = normalize(lDir); float NL = dot(N, L);
      float om = 1.0 - max(clamp((NL - 0.2) * -10.0, 0.0, 1.0), ombre(vw, N, L)) * fonduO();
      vec3 S = vec3(0.0);
      for (int i = 0; i < 4; i++) { if (float(i) >= nPL) break; vec3 dd = plPos[i].xyz - vw; float l = max(length(dd), 1e-5);
        float q = clamp((l - plPos[i].w) / -plPos[i].w, 0.0, 1.0); S += plCol[i].rgb * clamp(q * q * dot(N, dd) / l, 0.0, 1.0); }
      vec3 lum = clamp(NL, 0.0, 1.0) * lCol * om + S * plPow + lAmb;
      float rim = genre < 2.5 ? clamp(1.0 - clamp(dot(N, V), 0.0, 1.0) - sp2.y, 0.0, 1.0) * sp2.z * PS.y : 0.0;
      float em = mix(clamp(a.a, 0.0, 1.0), 1.0, sp0.z);
      vec3 col = (rim + lum) * a.rgb * mapAmb + a.rgb * amb.x * PS.z * em;
      gl_FragColor = vec4(col * vc.rgb * vF.a + fOcc * vF.rgb, 1.0); }`;

  // Matrices des cascades d'ombre (nie.exe 0x1405aa8a0, LiSPSM) — reconstruit puis comparé au vrai code exécuté dans l'émulateur
  // (nie_outils/test_lispsm.py : 60 cascades au hasard, écart relatif max 0,0002). V, P : vue et projection (colonne par colonne, WebGL).
  // Base : z = direction de l'ombre, y = direction de vue rendue perpendiculaire à z, x = y × z ; coins de la tranche -> y relatif ;
  // n = étendue / (ref_scale − 1) (si ref_scale <= 1 : n = 1000), f = n + étendue ; perspective le long de y ; recadrage de x / y et z / y
  // sur les coins -> la tranche remplit exactement [−1, 1]² × [0, 1] (profondeur Direct3D).
  // inverse d'une matrice 4 x 4 (colonne par colonne)
  function inv4(m) { const a = Array.from(m), o = new Float32Array(16), r = [];
    for (let i = 0; i < 4; i++) r.push([a[i], a[4 + i], a[8 + i], a[12 + i], i === 0 ? 1 : 0, i === 1 ? 1 : 0, i === 2 ? 1 : 0, i === 3 ? 1 : 0]);
    for (let c = 0; c < 4; c++) { let p = c; for (let i = c + 1; i < 4; i++) if (Math.abs(r[i][c]) > Math.abs(r[p][c])) p = i;
      [r[c], r[p]] = [r[p], r[c]]; const d = r[c][c]; for (let j = 0; j < 8; j++) r[c][j] /= d;
      for (let i = 0; i < 4; i++) if (i !== c) { const f = r[i][c]; for (let j = 0; j < 8; j++) r[i][j] -= f * r[c][j]; } }
    for (let i = 0; i < 4; i++) for (let j = 0; j < 4; j++) o[j * 4 + i] = r[i][4 + j]; return o; }
  function cascadesOmbre(V, P, dir, ref, tranches) {
    const r0 = [V[0], V[4], V[8]], r1 = [V[1], V[5], V[9]], r2 = [V[2], V[6], V[10]], t = [V[12], V[13], V[14]];
    const eye = [0, 1, 2].map(i => -(r0[i] * t[0] + r1[i] * t[1] + r2[i] * t[2]));
    const tX = 1 / P[0], tY = 1 / P[5], v = r2.map(c => -c);
    const z = norm(dir.slice(0, 3)), vz = dot(v, z), y = norm([v[0] - vz * z[0], v[1] - vz * z[1], v[2] - vz * z[2]]), x = croix(y, z);
    const vp = [];
    for (const [n0, f0] of tranches) {
      const C = [];
      for (const d of [n0, f0]) for (const sx of [-1, 1]) for (const sy of [-1, 1]) {
        const X = sx * d * tX, Y = sy * d * tY, Z = -d; C.push([0, 1, 2].map(i => r0[i] * X + r1[i] * Y + r2[i] * Z)); }   // relatif à l'œil
      const Ys = C.map(c => dot(c, y)), mn = Math.min(...Ys), e = Math.max(...Ys) - mn;
      const n = ref > 1 ? e / (ref - 1) : 1000, f = n + e;
      const Lp = C.map((c, k) => [dot(c, x), Ys[k] - mn + n, dot(c, z)]);
      const rx = Lp.map(q => q[0] / q[1]), rz = Lp.map(q => q[2] / q[1]);
      const xa = Math.min(...rx), xb = Math.max(...rx), za = Math.min(...rz), zb = Math.max(...rz);
      const A = [x.concat([-dot(x, eye)]), y.concat([-dot(y, eye) - mn + n]), z.concat([-dot(z, eye)]), [0, 0, 0, 1]];
      const B = [[2 / (xb - xa), -(xb + xa) / (xb - xa), 0, 0], [0, (f + n) / (f - n), 0, -2 * f * n / (f - n)], [0, zb / (zb - za), -1 / (zb - za), 0], [0, 1, 0, 0]];
      const M = new Float32Array(16);                       // B·A, rangée en colonnes pour WebGL
      for (let i = 0; i < 4; i++) for (let j = 0; j < 4; j++) { let sm = 0; for (let k = 0; k < 4; k++) sm += B[i][k] * A[k][j]; M[j * 4 + i] = sm; }
      vp.push(M);
    }
    return { vp, avant: v };
  }
  // Conversion des réglages bruts du brouillard (CLightData +0x540…+0x620) en registres cb5[37…50] : nie.exe 0x140f7f050
  // (lu le 13/11/2026). Couleurs × leur intensité (w) ; une couleur dont w < 0,01 est ignorée (Rayleigh : interpolée entre
  // ses voisines valides, sinon copie de la précédente ; Mie O00 : moyenne de P20 et M20) ; « push » : signe inversé ;
  // densités × −0,00001 ; « …DistanceRcp » : 1 / x ; fogOcclRate : 1 − max(x − 1/255, 0) × 1,003937.
  function brouillardCB(R) {
    const g = (k, d) => (R && R[k]) || d, n = k => g(k, [0])[0];
    if (!R || !R.fogWorldRayleighDensity) return null;
    const c4 = k => g(k, [0, 0, 0, 0]).concat([0, 0, 0, 0]).slice(0, 4), S = 0.01;
    const ray = ['P20', 'P10', 'O00', 'M10', 'M20'].map(x => c4('fogRayleighColor' + x)), kR = ray[0][3], out = [];
    out[0] = [ray[0][0] * kR, ray[0][1] * kR, ray[0][2] * kR, kR * kR];
    let der = 0;
    for (let i = 1; i < 5; i++) {
      const c = ray[i];
      if (c[3] < S) { out[i] = out[der].slice(); continue; }
      out[i] = [c[0] * kR, c[1] * kR, c[2] * kR, c[3] * kR];
      for (let j = 1; j < i - der; j++) { const t = j / (i - der); out[der + j] = out[der].map((v, q) => v + (out[i][q] - v) * t); }
      der = i;
    }
    const hc = c4('fogHeightRayleighColor'), mie = ['P20', 'O00', 'M20'].map(x => c4('fogMieColor' + x)), kM = mie[0][3];
    const m0 = [mie[0][0] * kM, mie[0][1] * kM, mie[0][2] * kM];
    let m1 = mie[1][3] < S ? m0.slice() : [mie[1][0] * kM, mie[1][1] * kM, mie[1][2] * kM];
    let m2 = mie[2][3] < S ? m1.slice() : [mie[2][0] * kM, mie[2][1] * kM, mie[2][2] * kM];
    if (mie[2][3] >= S && mie[1][3] < S) m1 = m0.map((v, q) => (v + m2[q]) * 0.5);
    const K = -9.999999747378752e-06, inv = x => 1 / x;
    return { R: new Float32Array(out.flatMap(v => v.slice(0, 3))), HC: [hc[0] * hc[3], hc[1] * hc[3], hc[2] * hc[3]],
      M: new Float32Array([...m0, ...m1, ...m2]),
      W0: [-n('fogWorldNearScatterPush'), n('fogWorldRayleighDensity') * K, n('fogWorldMieDensity') * K, inv(n('fogWorldNormalDistanceRcp'))],
      W1: [n('fogMiePhaseAnisotropy'), 1 - Math.max(n('fogOcclRate') - 1 / 255, 0) * 1.003937, 0, 0],
      H0: [n('fogHeightSeaLevel'), inv(n('fogHeightDistanceRcp')), -n('fogHeightNearScatterPush'), n('fogHeightRayleighDensity') * K],
      H1: [n('fogHeightMieDensity') * K, inv(n('fogHeightNormalDistanceRcp')), 0, 0],
      B: g('fogRayleighBandRatio', [0, 0, 0, 0]).concat([0, 0, 0, 0]).slice(0, 4),
      occ: Math.min(Math.max(1 - Math.max(n('fogOcclRate') - 1 / 255, 0) * 1.003937, 0), 1) };
  }
  function mul(a, b) { const o = new Float32Array(16);
    for (let i = 0; i < 4; i++) for (let j = 0; j < 4; j++) { let s = 0; for (let k = 0; k < 4; k++) s += a[k * 4 + j] * b[i * 4 + k]; o[i * 4 + j] = s; } return o; }
  function persp(f, a, n, l) { const t = 1 / Math.tan(f / 2); return new Float32Array([t / a, 0, 0, 0, 0, t, 0, 0, 0, 0, (l + n) / (n - l), -1, 0, 0, 2 * l * n / (n - l), 0]); }
  function regard(e, c) {
    const z = norm([e[0] - c[0], e[1] - c[1], e[2] - c[2]]), x = norm(croix([0, 1, 0], z)), y = croix(z, x);
    return new Float32Array([x[0], y[0], z[0], 0, x[1], y[1], z[1], 0, x[2], y[2], z[2], 0, -dot(x, e), -dot(y, e), -dot(z, e), 1]);
  }
  function croix(a, b) { return [a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0]]; }
  function dot(a, b) { return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]; }
  function norm(a) { const l = Math.hypot(a[0], a[1], a[2]) || 1; return [a[0] / l, a[1] / l, a[2] / l]; }

  class Vue3D {
    constructor(cv) {
      this.cv = cv;
      const gl = this.gl = cv.getContext('webgl', { antialias: true, premultipliedAlpha: true, alpha: true });
      if (!gl) throw new Error('WebGL indisponible');
      gl.getExtension('OES_element_index_uint');
      const prog = this.prog = gl.createProgram();
      for (const [t, s] of [[gl.VERTEX_SHADER, VS], [gl.FRAGMENT_SHADER, FS]]) {
        const sh = gl.createShader(t); gl.shaderSource(sh, s); gl.compileShader(sh);
        if (!gl.getShaderParameter(sh, gl.COMPILE_STATUS)) throw new Error(gl.getShaderInfoLog(sh));
        gl.attachShader(prog, sh);
      }
      gl.linkProgram(prog);
      this.loc = { p: gl.getAttribLocation(prog, 'p'), c: gl.getAttribLocation(prog, 'c'), t: gl.getAttribLocation(prog, 't'), nrm: gl.getAttribLocation(prog, 'nrm'),
        aPL: gl.getUniformLocation(prog, 'aPL'), nPL: gl.getUniformLocation(prog, 'nPL'), plPos: gl.getUniformLocation(prog, 'plPos'), plCol: gl.getUniformLocation(prog, 'plCol'), plK: gl.getUniformLocation(prog, 'plK'),
        profPack: gl.getUniformLocation(prog, 'profPack'), tex: gl.getUniformLocation(prog, 'tex'), aTex: gl.getUniformLocation(prog, 'aTex'), aLueur: gl.getUniformLocation(prog, 'aLueur'),
        lueurH: gl.getUniformLocation(prog, 'lueurH'), garderOr: gl.getUniformLocation(prog, 'garderOr'),
        forme: gl.getUniformLocation(prog, 'forme'), detail: gl.getUniformLocation(prog, 'detail'), aNuage: gl.getUniformLocation(prog, 'aNuage'),
        cOmbre: gl.getUniformLocation(prog, 'cOmbre'), cLum: gl.getUniformLocation(prog, 'cLum'),
        mvp: gl.getUniformLocation(prog, 'mvp'), modele: gl.getUniformLocation(prog, 'modele'), uvx: gl.getUniformLocation(prog, 'uvx'), teinte: gl.getUniformLocation(prog, 'teinte'), force: gl.getUniformLocation(prog, 'force') };
      // programme « dessin animé »
      const toon = this.toon = gl.createProgram();
      for (const [t, s] of [[gl.VERTEX_SHADER, VS_TOON], [gl.FRAGMENT_SHADER, FS_TOON]]) {
        const sh = gl.createShader(t); gl.shaderSource(sh, s); gl.compileShader(sh);
        if (!gl.getShaderParameter(sh, gl.COMPILE_STATUS)) throw new Error(gl.getShaderInfoLog(sh));
        gl.attachShader(toon, sh);
      }
      gl.linkProgram(toon);
      this.lt = {}; for (const a of ['p', 'n', 't']) this.lt[a] = gl.getAttribLocation(toon, a);
      for (const u of ['mvp', 'contour', 'largeur', 'ecran', 'tex', 'ombre', 'aTex', 'aOmbre', 'lum', 'couleurContour', 'noir', 'profPack',
        'nPL', 'plPos', 'plCol', 'plToon', 'plBlend', 'plRim', 'plRate', 'oeil',
        'lDir', 'aFog', 'fR', 'fHC', 'fM', 'fW0', 'fW1', 'fH0', 'fH1', 'fB', 'fOcc', 'fChara', 'stOn', 'stCol', 'stRim', 'stPow']) this.lt[u] = gl.getUniformLocation(toon, u);
      // programme « vrai shader du stade »
      this.extLod = gl.getExtension('EXT_shader_texture_lod'); gl.getExtension('OES_standard_derivatives');
      try { const pm = gl.createProgram();
        for (const [t, s] of [[gl.VERTEX_SHADER, VS_MAP], [gl.FRAGMENT_SHADER, FS_MAP]]) { const sh = gl.createShader(t); gl.shaderSource(sh, s); gl.compileShader(sh);
          if (!gl.getShaderParameter(sh, gl.COMPILE_STATUS)) throw new Error(gl.getShaderInfoLog(sh)); gl.attachShader(pm, sh); }
        gl.linkProgram(pm); if (!gl.getProgramParameter(pm, gl.LINK_STATUS)) throw new Error(gl.getProgramInfoLog(pm));
        this.pm = pm; this.lm = {};
        for (const a of ['p', 'c', 't', 'nrm', 'tg']) this.lm[a] = gl.getAttribLocation(pm, a);
        for (const u of ['mvp', 'tpA', 'tpB', 'diff', 't0', 't1', 't2', 't3', 'cube', 'aCube', 'genre', 'aNrm', 'couches', 'coupe', 'lodMax', 'sp0', 'sp1', 'sp2', 'sp3', 'sp6', 'amb',
          'oeil', 'mapAmb', 'lDir', 'lCol', 'lAmb', 'LI', 'IBL', 'PS', 'plPow', 'nPL', 'plPos', 'plCol', 'omb', 'sunVP', 'aOmb', 'ombT', 'omb1', 'omb2', 'sunVP1', 'sunVP2', 'ombLoin', 'camAv', 'invVP', 'invVP1', 'invVP2', 'ombB', 'ombDir', 'ombN0', 'ombS',
          'aFog', 'fR', 'fHC', 'fM', 'fW0', 'fW1', 'fH0', 'fH1', 'fB', 'fOcc']) this.lm[u] = gl.getUniformLocation(pm, u);
      } catch (e) { console.error('shader du stade', e); this.pm = null; }
      // programme « jeu » (shaders du jeu traduits)
      const pj = this.pj = gl.createProgram();
      for (const [t, s] of [[gl.VERTEX_SHADER, VS_J], [gl.FRAGMENT_SHADER, FS_J]]) {
        const sh = gl.createShader(t); gl.shaderSource(sh, s); gl.compileShader(sh);
        if (!gl.getShaderParameter(sh, gl.COMPILE_STATUS)) throw new Error(gl.getShaderInfoLog(sh));
        gl.attachShader(pj, sh);
      }
      gl.linkProgram(pj);
      if (!gl.getProgramParameter(pj, gl.LINK_STATUS)) throw new Error(gl.getProgramInfoLog(pj));
      this.lj = {}; for (const a of ['p', 'c', 't', 'ta', 'tb', 'tc', 'td', 'te', 'k1', 'n', 'tg']) this.lj[a] = gl.getAttribLocation(pj, a);
      for (const u of ['adr', 'smp', 'effP', 'patL', 'Q3', 'ombVP', 'ombFx', 'sOmbE', 'aOmbE', 'ombT', 'csP', 'effS', 'ombC', 'fumee', 'Q4', 'Q5', 'ambC', 'cAL', 'effA', 'eau', 'bordFx', 'sProf', 'aProf', 'pz', 'spD', 'ecranP', 'aura', 'morph', 'fogFx', 'lDir', 'aFog', 'fR', 'fHC', 'fM', 'fW0', 'fW1', 'fH0', 'fH1', 'fB', 'Q2', 'oeilW', 'vueV', 'L1', 'L2', 'L1dir', 's5', 'P4', 'P5', 'P6', 'fbA', 'fbB', 'fbT', 'mv', 'mvp', 'modele', 'uA', 'uB', 's0', 's1', 's2', 's3', 's4', 'mode', 'dif', 'amb', 'P0', 'P1', 'P2', 'P3', 'ubw', 'vdisp', 'Q0', 'Q1', 'sc', 'ecranT', 'projY', 'asp', 'grdU']) this.lj[u] = gl.getUniformLocation(pj, u);
      this.style = true;          // rendu du jeu (ombre + contour) ; false = couleurs plates
      this.pieces = []; this.textures = {}; this.additif = true; this.fil = false;
      this.yaw = 0.6; this.pitch = 0.25; this.dist = 30; this.centre = [0, 0, 0];
      // animation : this.lecteur (Lecteur de anim3d.js), this.image, this.joue, this.cameraJeu, this.surImage(image, res)
      this.lecteur = null; this.image = 0; this.joue = false; this.cameraJeu = true; this.surImage = null; this._t = 0;
      // (24/11, demande d'enhanc3) « objet seul » : this.isole = pièces montrées (Set), à la place de leur visibilité ; this.repos =
      // pose de repos (maillage tel qu'il est dans son fichier) au lieu de l'image de l'animation. p.visible n'est JAMAIS touché
      // (pièces cachées, projet, lecteur du jeu et export restent comme avant).
      this.isole = null; this.repos = true;
      this._souris(); this._boucle();
    }
    // texture (canvas) partagée par les pièces : créée ou mise à jour
    texture(cle, canvas) {
      Vue3D.activite = performance.now();
      const gl = this.gl; let t = this.textures[cle];
      if (!t) { t = this.textures[cle] = gl.createTexture(); }
      gl.bindTexture(gl.TEXTURE_2D, t); gl.pixelStorei(gl.UNPACK_FLIP_Y_WEBGL, false);
      gl.pixelStorei(gl.UNPACK_PREMULTIPLY_ALPHA_WEBGL, false); gl.pixelStorei(gl.UNPACK_COLORSPACE_CONVERSION_WEBGL, gl.NONE);
      gl.texImage2D(gl.TEXTURE_2D, 0, gl.RGBA, gl.RGBA, gl.UNSIGNED_BYTE, canvas);
      const p2 = n => (n & (n - 1)) === 0, rep = p2(canvas.width) && p2(canvas.height);
      (this.texPot || (this.texPot = {}))[cle] = rep;
      gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_S, rep ? gl.REPEAT : gl.CLAMP_TO_EDGE);
      gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_T, rep ? gl.REPEAT : gl.CLAMP_TO_EDGE);
      // mipmaps (comme le jeu : les DDS en contiennent) : une texture vue en petit (traits fins, lointains) est lue réduite,
      // plus douce et moins opaque ; sans elles, les traits de vitesse paraissaient 2 fois trop épais
      if (rep) { gl.generateMipmap(gl.TEXTURE_2D); gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MIN_FILTER, gl.LINEAR_MIPMAP_LINEAR); }
      else gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MIN_FILTER, gl.LINEAR);
      gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MAG_FILTER, gl.LINEAR);
    }
    // maillage avec os (joueur) : sommets recalculés à chaque image depuis les matrices des os
    ajouterPeau(cle, geo, acteur) {
      const p = this.ajouter(cle, Object.assign({}, geo, { col: new Uint8Array(geo.nv * 4).fill(255) }));
      const gl = this.gl; gl.bindBuffer(gl.ARRAY_BUFFER, p.bp); gl.bufferData(gl.ARRAY_BUFFER, geo.pos, gl.DYNAMIC_DRAW);
      p.peau = { acteur, pos0: geo.pos, os: geo.os, poids: geo.poids, sortie: new Float32Array(geo.pos.length),
        nor0: geo.normales || new Float32Array(geo.pos.length), sortieN: new Float32Array(geo.pos.length) };
      p.bn = gl.createBuffer(); gl.bindBuffer(gl.ARRAY_BUFFER, p.bn); gl.bufferData(gl.ARRAY_BUFFER, p.peau.nor0, gl.DYNAMIC_DRAW);
      p.contour = geo.contour || null; p.ombreCle = geo.ombreCle || null; p.noir = !!geo.noir;
      p.opaque = true; p.teinte = [1, 1, 1, 1];
      return p;
    }
    // une pièce d'effet avec le shader du jeu
    _dessinerJeu(p, mvp, avecOpaques) {
      const gl = this.gl, L = this.lj, J = p.jeu; gl.useProgram(this.pj);
      if (J.mode === 15 || J.mode === 16) {   // distorsion : copie de l'image déjà dessinée (in_rtTexColor du jeu)
        const w = gl.drawingBufferWidth, h = gl.drawingBufferHeight;
        if (!this._texScene) { this._texScene = gl.createTexture(); }
        gl.activeTexture(gl.TEXTURE7); gl.bindTexture(gl.TEXTURE_2D, this._texScene);
        gl.copyTexImage2D(gl.TEXTURE_2D, 0, gl.RGBA, 0, 0, w, h, 0);
        gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MIN_FILTER, gl.LINEAR); gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MAG_FILTER, gl.LINEAR);
        gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_S, gl.CLAMP_TO_EDGE); gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_T, gl.CLAMP_TO_EDGE);
        gl.uniform1i(L.sc, 7); gl.uniform2f(L.ecranT, w, h); gl.uniform1f(L.projY, this._P ? this._P[5] : 1); gl.uniform1f(L.asp, w / Math.max(h, 1));
        gl.activeTexture(gl.TEXTURE0); }
      let uv = p.jeuUV || [0, 1, 2, 3, 4, 5].map(k => J.texproj[k] || [1, 0, 0, 0, 0, 1, 0, 0]);
      const part = p.ptl ? this._quadsEmetteur(p, J.mode === 28) : J.particules && p.geoCPU && this._P ? (J.ligne2 ? this._ligne2(p, uv) : J.ligne1 ? this._ligne1(p, uv) : this._particules(p, uv)) : null;
      if ((J.particules || p.ptl) && !part) { gl.useProgram(this.prog); return; }
      if (part) { gl.uniformMatrix4fv(L.mvp, false, part.monde ? mul(this._P, this._V) : this._P); gl.uniformMatrix4fv(L.modele, false, ID); uv = uv.map(() => [1, 0, 0, 0, 0, 1, 0, 0]); }
      else { gl.uniformMatrix4fv(L.mvp, false, mvp); gl.uniformMatrix4fv(L.modele, false, p.modele || ID); }
      if (L.mv) gl.uniformMatrix4fv(L.mv, false, this._V ? mul(this._V, (part ? null : p.modele) || ID) : ID);
      if (L.tg >= 0) { const bt = part ? (part.monde ? part.btg : null) : p.btan; if (bt) { gl.bindBuffer(gl.ARRAY_BUFFER, bt); gl.enableVertexAttribArray(L.tg); gl.vertexAttribPointer(L.tg, 3, gl.FLOAT, false, 0, 0); }
        else { gl.disableVertexAttribArray(L.tg); gl.vertexAttrib3f(L.tg, 1, 0, 0); } }
      // Solid : lumières (P0.xyz, P1.xyz, en coordonnées du monde) passées en repère caméra ; P2.x = 0 -> lumière 1 = direction
      // SolidToon1 (mode 13) : lumière 1 = P1.xyz (direction si P0.x = 0), lumière 2 = P3.xyz
      if ((J.mode === 14 || J.mode === 13) && this._V) { const Pm = p.jeuP || J.params, V = this._V, t13 = J.mode === 13;
        const a = Pm[t13 ? 1 : 0] || [0, 0, 0, 0], b = Pm[t13 ? 3 : 1] || [0, 0, 0, 0];
        const dir = (Pm[t13 ? 0 : 2] || [1])[0] === 0, pt = (q, w) => [V[0] * q[0] + V[4] * q[1] + V[8] * q[2] + w * V[12], V[1] * q[0] + V[5] * q[1] + V[9] * q[2] + w * V[13], V[2] * q[0] + V[6] * q[1] + V[10] * q[2] + w * V[14]];
        gl.uniform3fv(L.L1, pt(a, dir ? 0 : 1)); gl.uniform3fv(L.L2, pt(b, 1)); gl.uniform1f(L.L1dir, dir ? 1 : 0); }
      if (L.n >= 0) { const bn = part ? (part.monde ? part.bn : null) : p.bnor; if (bn) { gl.bindBuffer(gl.ARRAY_BUFFER, bn); gl.enableVertexAttribArray(L.n); gl.vertexAttribPointer(L.n, 3, gl.FLOAT, false, 0, 0); }
        else { gl.disableVertexAttribArray(L.n); gl.vertexAttrib3f(L.n, 0, 0, 1); } }
      gl.uniform4fv(L.uA, new Float32Array(uv.flatMap(m => m.slice(0, 4)))); gl.uniform4fv(L.uB, new Float32Array(uv.flatMap(m => m.slice(4, 8))));
      const adrK = new Float32Array(12);
      for (let k = 0; k < 6; k++) { gl.activeTexture(gl.TEXTURE0 + k);
        const tk = k < J.tex.length ? J.tex[k] : J.tex[0]; /* case présente mais texture introuvable (« ?crc ») -> blanc */ gl.bindTexture(gl.TEXTURE_2D, (tk && this.textures[tk]) || this._blanc()); gl.uniform1i(L['s' + k], k);
        // ADRESSAGE DU JEU (13/11/2026, lu dans nie.exe) : par case et par axe, 1 répété, 2 miroir, 3 bloqué au bord
        // (4 bordure, 5 miroir une fois : jamais utilisés par les effets). WebGL 1 ne répète / ne reflète que les tailles
        // en puissance de 2 : sinon, bloqué côté matériel et calcul dans le shader (adr = mode à appliquer par axe).
        const ad = (J.adressage && J.adressage[k]) || [1, 1];
        // (cases vides : même texture que la case 0, ne pas écraser son réglage ; WebGL règle la texture, pas la case)
        if (k < J.tex.length && tk && this.textures[tk]) { const pot = this.texPot && this.texPot[tk];
          const m = v => v === 2 ? gl.MIRRORED_REPEAT : v === 1 ? gl.REPEAT : gl.CLAMP_TO_EDGE;
          adrK[2 * k] = pot && ad[0] <= 3 ? 0 : ad[0]; adrK[2 * k + 1] = pot && ad[1] <= 3 ? 0 : ad[1];
          gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_S, pot ? m(ad[0]) : gl.CLAMP_TO_EDGE);
          gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_T, pot ? m(ad[1]) : gl.CLAMP_TO_EDGE); } }
      gl.activeTexture(gl.TEXTURE0); if (L.adr) gl.uniform2fv(L.adr, adrK);
      let P = p.jeuP || J.params;
      if (J.colonne !== null && J.colonne !== undefined) {   // BallAura : colonne du dégradé (128 colonnes)
        let col = J.colonne;
        // colonne = « couleur de tir » de la technique (0 montagne jaune, 1 vent bleu, 2 feu orange, 3 forêt vert, 4 néant violet) :
        // VÉRIFIÉ le 13/11/2026 sur 5 vidéos du jeu (un tir par élément). L'ancien remplacement par la teinte de l'aura est retiré.
        P = P.map(v => v.slice()); if (P[2] && J.mode !== 17) P[2][3] = (col + 0.5) / 128;
        gl.uniform1f(L.grdU, (col + 0.5) / 128);           // BallAura1 : u_grdValue.x (cb11[5].x) = colonne du dégradé = n° de couleur du tir (vérifié)
      }
      { const k = this.facteurEclat(p);      // (15/11/2026) pièce localisée : plus lumineuse quelques instants
        gl.uniform1f(L.mode, J.mode); gl.uniform4fv(L.dif, [J.diffuse[0] * k, J.diffuse[1] * k, J.diffuse[2] * k, p.opacite !== undefined ? p.opacite : J.diffuse[3]]); }
      gl.uniform4fv(L.amb, J.ambient); for (let i = 0; i < 7; i++) if (L['P' + i]) gl.uniform4fv(L['P' + i], P[i] || [0, 0, 0, 0]);
      { const O = this._profS, on = !!(O && J.soft && !p.ecran2D);       // particules douces
        gl.activeTexture(gl.TEXTURE6); gl.bindTexture(gl.TEXTURE_2D, on ? O.tex : null); gl.uniform1i(L.sProf, 6); gl.uniform1f(L.aProf, on ? 1 : 0);
        if (O) { gl.uniform2f(L.pz, this._P[10], this._P[14]); gl.uniform2f(L.ecranP, O.w, O.h); }
        gl.uniform1f(L.spD, ((this.lumStade || {}).softParticleDistance || [1])[0]); gl.activeTexture(gl.TEXTURE0); }
      gl.uniform1f(L.fogFx, J.mode === 22 && !part ? 1 : 0); gl.uniform1f(L.bordFx, J.mode === 23 && !part ? 1 : 0); gl.uniform1f(L.eau, J.mode === 24 && !part ? 1 : 0);
      { const O = this._ombreEffets, on = !!(O && J.ombreFx && (!part || part.monde)), R = this.lumStade || {};      // ombre des effets
        gl.uniform1f(L.ombFx, on ? 1 : 0); gl.uniform1f(L.aOmbE, on ? 1 : 0);
        if (on) { gl.uniformMatrix4fv(L.ombVP, false, O.vp); gl.activeTexture(gl.TEXTURE7); gl.bindTexture(gl.TEXTURE_2D, O.tex); gl.uniform1i(L.sOmbE, 7);
          gl.uniform1f(L.ombT, 1 / O.taille); gl.activeTexture(gl.TEXTURE0); }
        const sc = (R.shadowColor || [0.7, 0.7, 0.7]).slice(0, 3), y = sc[0] * 0.29891 + sc[1] * 0.58661 + sc[2] * 0.11448, g = (R.effectShadowGrayScale || [0.5])[0];
        gl.uniform4fv(L.csP, (R.charaShadowParam || [1, 1, 0, 1]).concat([0, 0, 0, 0]).slice(0, 4)); gl.uniform1f(L.effS, (R.effectShadowRate || [1.0])[0]);
        gl.uniform3fv(L.ombC, sc.map(x => y + g * (x - y))); }
      gl.uniform1f(L.smp, J.mode === 28 && (!part || part.monde) ? 1 : 0); gl.uniform1f(L.effP, ((this.lumStade || {}).effectPLightRate || [0.5])[0]);   // 0,5 : constructeur de CLightData
      gl.uniform1f(L.patL, J.mode === 27 && !part ? 1 : 0); gl.uniform4fv(L.Q3, P[3] || [1, 1, 0, 0]);
      gl.uniform1f(L.fumee, J.mode === 25 && !part ? 1 : 0); gl.uniform4fv(L.Q4, P[4] || [0, 0, 0, 0]); gl.uniform4fv(L.Q5, P[5] || [1, 1, 0, 0]);
      { const R = this.lumStade || {}, ca = (R.charaAmbient || [1, 1, 1]).slice(0, 3), al = (R.charaAmbLightParam || [0, 1, 0]).concat([0, 0, 0]);
        // ambiance des effets (Smoke2 / T1L) : mix(charaAmbient, 1, charaAmbLightParam.z) rendue grise à effectShadowGrayScale ;
        // effectAmbientRate pas dans les données -> valeur du constructeur de CLightData (0x140f821c0) : 0,4
        const b = ca.map(x => x + al[2] * (1 - x)), y = b[0] * 0.29891 + b[1] * 0.58661 + b[2] * 0.11448, g = (R.effectShadowGrayScale || [0.5])[0];
        gl.uniform3fv(L.ambC, b.map(x => y + g * (x - y))); gl.uniform2f(L.cAL, al[0], al[1]); gl.uniform1f(L.effA, (R.effectAmbientRate || [0.4])[0]); }
      if (J.mode === 24) this._uniformsBrouillard(L, this.lecteur ? this.lumStade : null); if (J.mode === 22) this._uniformsBrouillard(L, this.lecteur ? this.lumStade : null);
      gl.uniform1f(L.aura, J.mode === 20 && !part ? 1 : 0); gl.uniform1f(L.morph, J.mode === 21 && !part ? 1 : 0); gl.uniform4fv(L.Q2, P[2] || [0, 0, 0, 0]);
      gl.uniform3fv(L.oeilW, this._oeil || [0, 0, 0]); gl.uniformMatrix4fv(L.vueV, false, this._V || ID);
      gl.uniform1f(L.vdisp, J.mode === 8 && !part ? 1 : 0); gl.uniform4fv(L.Q0, P[0] || [0, 0, 0, 0]); gl.uniform4fv(L.Q1, P[1] || [0, 0, 0, 0]);   // VDispRim : déplacement
      // animation par cases (T3ThresholdF, vertex shader du jeu) : n° = partie entière de P4.x, colonnes P3.z, lignes P3.w ;
      // case (n mod colonnes, (n / colonnes) mod lignes) ; fondu avec la case suivante = partie décimale de P4.x
      if (J.mode === 3) { const P3 = P[3] || [0, 0, 1, 1], P4 = P[4] || [0, 0, 0, 0], nc = P3[2] || 1, nl = P3[3] || 1;
        const cas = i => { const c = ((i % nc) + nc) % nc, l = ((Math.trunc(i / nc) % nl) + nl) % nl; return [c / nc, l / nl, 1 / nc, 1 / nl]; };
        const i0 = Math.trunc(P4[0]); gl.uniform4fv(L.fbA, cas(i0)); gl.uniform4fv(L.fbB, cas(i0 + 1)); gl.uniform1f(L.fbT, Math.abs(P4[0] - i0)); }
      // T1PatternFade (vertex shader du jeu) : n° = partie entière de P0.x, colonnes P0.y, lignes P0.z ;
      // fondu = partie décimale, ou en marche (0 / 1 à 0,5) quand P0.w = 1 : fondu = d + P0.w x (marche(0,5 < d) - d)
      if (J.mode === 7) { const P0 = P[0] || [0, 1, 1, 0], nc = P0[1] || 1, nl = P0[2] || 1;
        const cas = i => { const c = ((i % nc) + nc) % nc, l = ((Math.trunc(i / nc) % nl) + nl) % nl; return [c / nc, l / nl, 1 / nc, 1 / nl]; };
        const i0 = Math.trunc(P0[0]), d = Math.abs(P0[0] - i0);
        gl.uniform4fv(L.fbA, cas(i0)); gl.uniform4fv(L.fbB, cas(i0 + 1)); gl.uniform1f(L.fbT, d + P0[3] * ((d > 0.5 ? 1 : 0) - d)); }
      gl.uniform1f(L.ubw, 0);
      const opq = p.melange === 'opaque', dm = gl.getParameter(gl.DEPTH_WRITEMASK);
      if (opq) { gl.blendFuncSeparate(gl.ONE, gl.ZERO, gl.CONSTANT_ALPHA, gl.ZERO); gl.blendColor(0, 0, 0, 1); gl.depthMask(true); }  // opaque : alpha 1
      // (14/11/2026) écriture de profondeur = clé 5 du matériau, avec ou sans mélange (LU nie.exe 0x140528eb0) ; pas pour les particules
      const ze = !part && !opq && !p.surEcran && p.zecrit !== undefined; if (ze) gl.depthMask(!!p.zecrit);
      else this._bf(p.melange === 'add' ? gl.ONE : gl.ONE_MINUS_SRC_ALPHA);
      const ecran = p.surEcran || !p.ztest; if (ecran) gl.disable(gl.DEPTH_TEST); else if (avecOpaques || opq) gl.enable(gl.DEPTH_TEST);
      const B = part || p;
      gl.bindBuffer(gl.ARRAY_BUFFER, B.bp); gl.enableVertexAttribArray(L.p); gl.vertexAttribPointer(L.p, 3, gl.FLOAT, false, 0, 0);
      // (vraies particules : couleur en flottants, elle dépasse souvent 1 — sommets du jeu en float4)
      gl.bindBuffer(gl.ARRAY_BUFFER, B.bc); gl.enableVertexAttribArray(L.c); gl.vertexAttribPointer(L.c, 4, B.cf ? gl.FLOAT : gl.UNSIGNED_BYTE, !B.cf, 0, 0);
      gl.bindBuffer(gl.ARRAY_BUFFER, B.bt); gl.enableVertexAttribArray(L.t); gl.vertexAttribPointer(L.t, 2, gl.FLOAT, false, 0, 0);
      if (part) {   // particules : déjà en repère caméra ; vraies particules : couches de texture 1 et 2 (UV_INFO) en TEXCOORD1 / 2
        ['ta', 'tb', 'tc', 'td', 'te'].forEach((a, k) => { if (L[a] < 0) return; const b = k === 0 ? B.bta : k === 1 ? B.btb : null;
          if (b) { gl.bindBuffer(gl.ARRAY_BUFFER, b); gl.enableVertexAttribArray(L[a]); gl.vertexAttribPointer(L[a], 2, gl.FLOAT, false, 0, 0); }
          else { gl.disableVertexAttribArray(L[a]); gl.vertexAttrib2f(L[a], 0, 0); } });
        if (L.k1 >= 0) { gl.disableVertexAttribArray(L.k1); gl.vertexAttrib4f(L.k1, 1, 1, 1, 1); }
        // mélange soustractif du jeu (MATERIAL_INFO[9] = 4 : destination − source × alpha)
        if (p.melange === 'sous') { gl.blendEquation(gl.FUNC_REVERSE_SUBTRACT); gl.blendFunc(gl.SRC_ALPHA, gl.ONE); }
        gl.bindBuffer(gl.ELEMENT_ARRAY_BUFFER, part.bi); gl.drawElements(gl.TRIANGLES, part.ni, gl.UNSIGNED_SHORT, 0);
        if (p.melange === 'sous') gl.blendEquation(gl.FUNC_ADD);
        ['ta', 'tb'].forEach(a => { if (L[a] >= 0) gl.disableVertexAttribArray(L[a]); });
        if (ecran && avecOpaques) gl.enable(gl.DEPTH_TEST);
        this._bf(this.additif ? gl.ONE : gl.ONE_MINUS_SRC_ALPHA); gl.useProgram(this.prog); return;
      }
      if (L.k1 >= 0) { if (p.bc1) { gl.bindBuffer(gl.ARRAY_BUFFER, p.bc1); gl.enableVertexAttribArray(L.k1); gl.vertexAttribPointer(L.k1, 4, gl.UNSIGNED_BYTE, true, 0, 0); }
        else { gl.disableVertexAttribArray(L.k1); gl.vertexAttrib4f(L.k1, 1, 1, 1, 1); } }
      const sup = ['ta', 'tb', 'tc', 'td', 'te'];
      sup.forEach((a, k) => { if (L[a] < 0) return; gl.bindBuffer(gl.ARRAY_BUFFER, (p.btx && p.btx[k]) || p.bt);
        gl.enableVertexAttribArray(L[a]); gl.vertexAttribPointer(L[a], 2, gl.FLOAT, false, 0, 0); });
      gl.bindBuffer(gl.ELEMENT_ARRAY_BUFFER, p.bi); gl.drawElements(gl.TRIANGLES, p.ni, gl.UNSIGNED_SHORT, 0);
      sup.forEach(a => { if (L[a] >= 0) gl.disableVertexAttribArray(L[a]); });
      if (opq || ze) gl.depthMask(dm);
      if (L.n >= 0) gl.disableVertexAttribArray(L.n);
      if (L.k1 >= 0) gl.disableVertexAttribArray(L.k1);
      if (L.tg >= 0) gl.disableVertexAttribArray(L.tg);
      if (ecran && avecOpaques) gl.enable(gl.DEPTH_TEST);
      this._bf(this.additif ? gl.ONE : gl.ONE_MINUS_SRC_ALPHA);
      gl.useProgram(this.prog);
    }
    // mélange : couleur comme dans le jeu ; alpha du canevas (prémultiplié) = couverture : additif -> ne change pas l'alpha
    // (la lumière s'ajoute à ce qui est derrière la page), normal -> recouvre. Avant : canevas non prémultiplié, une lumière
    // additive sur du vide gardait un alpha ~0 et disparaissait à l'affichage.
    _bf(dst) { const gl = this.gl; gl.blendFuncSeparate(gl.SRC_ALPHA, dst, dst === gl.ONE ? gl.ZERO : gl.ONE, dst === gl.ONE ? gl.ONE : gl.ONE_MINUS_SRC_ALPHA); }
    // FakeParticle (traduction du geometry shader Effect_FakeParticle.gfxo) : chaque triangle = une particule.
    // Repère caméra : centre c, normale N du triangle, r2 = direction du 1er sommet, r3 = N x r2.
    // _TranslateTex (case 2, coordonnées TEXCOORD2 x u_texProj[2]) : décalage (rgb x 2 - 1) x COLOR0.rgb x P0.y x échelle,
    // alpha = taille ; demi-côté = |s0 - s1| x P0.x / 2 x alpha. _ColorAnimeTex (case 1, TEXCOORD1) x COLOR1 = couleur.
    // Carré face à la caméra, coordonnées (1,0) (0,0) (1,1) (0,1) par u_texProj[0].
    _particules(p, uv) {
      const J = p.jeu, G = p.geoCPU, V = this._V, M = p.modele || ID, P = (p.jeuP || J.params), P0 = P[0] || [1, 1, 0, 0];
      const LV = mul(V, M), tPos = J.donnees[2], tCol = J.donnees[1], tRot = J.rotz ? J.donnees[3] : null;
      // RotZ / RotZPat (Effect_FakeParticleRotZ(Pat).gfxo) : angle = (rouge de _RotZ(Pat)Tex x 2 - 1) x P0.z degrés ;
      // RotZPat : image de la planche n° = partie entière((P1.x x P1.y x P1.z - 1) x alpha), P1.x colonnes, P1.y lignes
      const P1 = P[1] || [1, 1, 1, 0], uv3 = G.uvs[3] || G.uvs[0];
      if (!tPos) return null;
      const ech = 1 + P0[3] * ((Math.hypot(M[0], M[1], M[2]) + Math.hypot(M[4], M[5], M[6]) + Math.hypot(M[8], M[9], M[10])) / 3 - 1);
      // coordonnées des textures de données (formule du vertex shader : décalages comptés à l'envers)
      const tp = (m, u, v) => [m[0] * u + m[1] * v - m[2] - 2 * m[1], m[4] * u + m[5] * v + 2 - 2 * m[5] - m[6]];
      const lire = (t, u, v) => { if (!t) return [1, 1, 1, 1]; const W = t.width, H = t.height, d = t.data;
        const x = Math.min(W - 1, Math.max(0, u * W - 0.5)), y = Math.min(H - 1, Math.max(0, v * H - 0.5));
        const x0 = Math.floor(x), y0 = Math.floor(y), x1 = Math.min(W - 1, x0 + 1), y1 = Math.min(H - 1, y0 + 1), fx = x - x0, fy = y - y0;
        const o = [0, 0, 0, 0];
        for (const [xx, yy, f] of [[x0, y0, (1 - fx) * (1 - fy)], [x1, y0, fx * (1 - fy)], [x0, y1, (1 - fx) * fy], [x1, y1, fx * fy]]) {
          const i = (yy * W + xx) * 4; for (let k = 0; k < 4; k++) o[k] += d[i + k] / 255 * f; }
        return o; };
      const vue = k => { const x = G.pos[3 * k], y = G.pos[3 * k + 1], z = G.pos[3 * k + 2];
        return [LV[0] * x + LV[4] * y + LV[8] * z + LV[12], LV[1] * x + LV[5] * y + LV[9] * z + LV[13], LV[2] * x + LV[6] * y + LV[10] * z + LV[14]]; };
      const sub = (a, b) => [a[0] - b[0], a[1] - b[1], a[2] - b[2]], nrm = a => { const l = Math.hypot(a[0], a[1], a[2]) || 1; return [a[0] / l, a[1] / l, a[2] / l]; };
      const cr = (a, b) => [a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0]];
      const n = Math.floor(G.idx.length / 3), pos = new Float32Array(n * 12), col = new Uint8Array(n * 16), tex = new Float32Array(n * 8), ind = new Uint16Array(n * 6);
      const u0 = uv[0], coin = (u, v) => [u0[0] * u + u0[1] * v + u0[2], u0[4] * u + u0[5] * v + u0[6]];
      const UV = [coin(1, 0), coin(0, 0), coin(1, 1), coin(0, 1)], uv1 = G.uvs[1] || G.uvs[0], uv2 = G.uvs[2] || G.uvs[0];
      let m = 0;
      for (let t = 0; t < n && m < 16000; t++) {
        const i0 = G.idx[3 * t], s0 = vue(i0), s1 = vue(G.idx[3 * t + 1]), s2 = vue(G.idx[3 * t + 2]);
        const N = nrm(cr(nrm(sub(s1, s0)), nrm(sub(s2, s0)))), c = [(s0[0] + s1[0] + s2[0]) / 3, (s0[1] + s1[1] + s2[1]) / 3, (s0[2] + s1[2] + s2[2]) / 3];
        const r2 = nrm(sub(s0, c)), r3 = cr(N, r2);
        const [pu, pv] = tp(uv[2], uv2[2 * i0], uv2[2 * i0 + 1]), T = lire(tPos, pu, pv);
        const k0 = [G.col[4 * i0] / 255, G.col[4 * i0 + 1] / 255, G.col[4 * i0 + 2] / 255, G.col[4 * i0 + 3] / 255];
        const o3 = [k0[0] * P0[1] * ech, k0[1] * P0[1] * ech, k0[2] * P0[1] * ech];
        const d = [(T[0] * 2 - 1) * o3[0], (T[1] * 2 - 1) * o3[1], (T[2] * 2 - 1) * o3[2]];
        const q = [c[0] + d[0] * r3[0] + d[1] * N[0] + d[2] * r2[0], c[1] + d[0] * r3[1] + d[1] * N[1] + d[2] * r2[1], c[2] + d[0] * r3[2] + d[1] * N[2] + d[2] * r2[2]];
        const h = T[3] * Math.abs(Math.hypot(...sub(s0, s1)) * P0[0] * 0.5);
        if (!(h > 1e-6)) continue;
        let ca = 1, sa = 0, cel = [0, 0, 1, 1];
        if (tRot) { const [ru, rv] = tp(uv[3], uv3[2 * i0], uv3[2 * i0 + 1]), Rt = lire(tRot, ru, rv);
          const ang = -(Rt[0] * 2 - 1) * P0[2] * 0.017453; ca = Math.cos(ang); sa = Math.sin(ang);
          if (J.pat) { const nc = P1[0] || 1, nl = P1[1] || 1, n = Math.trunc((nc * nl * P1[2] - 1) * Rt[3]);
            const c2 = ((n % nc) + nc) % nc, l2 = ((Math.trunc(n / nc) % nl) + nl) % nl; cel = [c2 / nc, l2 / nl, 1 / nc, 1 / nl]; } }
        const [cu, cv] = tp(uv[1], uv1[2 * i0], uv1[2 * i0 + 1]), C = lire(tCol, cu, cv);
        const k1 = [G.col1[4 * i0] / 255, G.col1[4 * i0 + 1] / 255, G.col1[4 * i0 + 2] / 255, G.col1[4 * i0 + 3] / 255];
        const rgba = [C[0] * k1[0], C[1] * k1[1], C[2] * k1[2], C[3] * k1[3] * k0[3]].map(x => Math.max(0, Math.min(255, Math.round(x * 255))));
        [[h, h], [-h, h], [h, -h], [-h, -h]].forEach(([dx, dy], j) => {
          pos.set([q[0] + dx * ca + dy * sa, q[1] - dx * sa + dy * ca, q[2]], (4 * m + j) * 3);
          col.set(rgba, (4 * m + j) * 4); tex.set([UV[j][0] * cel[2] + cel[0], UV[j][1] * cel[3] + cel[1]], (4 * m + j) * 2); });
        ind.set([4 * m, 4 * m + 1, 4 * m + 2, 4 * m + 1, 4 * m + 2, 4 * m + 3], 6 * m); m++;
      }
      if (!m) return null;
      const gl = this.gl, B = p.partBuf || (p.partBuf = { bp: gl.createBuffer(), bc: gl.createBuffer(), bt: gl.createBuffer(), bi: gl.createBuffer() });
      gl.bindBuffer(gl.ARRAY_BUFFER, B.bp); gl.bufferData(gl.ARRAY_BUFFER, pos.subarray(0, m * 12), gl.DYNAMIC_DRAW);
      gl.bindBuffer(gl.ARRAY_BUFFER, B.bc); gl.bufferData(gl.ARRAY_BUFFER, col.subarray(0, m * 16), gl.DYNAMIC_DRAW);
      gl.bindBuffer(gl.ARRAY_BUFFER, B.bt); gl.bufferData(gl.ARRAY_BUFFER, tex.subarray(0, m * 8), gl.DYNAMIC_DRAW);
      gl.bindBuffer(gl.ELEMENT_ARRAY_BUFFER, B.bi); gl.bufferData(gl.ELEMENT_ARRAY_BUFFER, ind.subarray(0, m * 6), gl.DYNAMIC_DRAW);
      B.ni = m * 6; return B;
    }
    // Effect_FakeParticleLine1.gfxo (traduit le 13/11/2026) : comme FakeParticle (repère du triangle, décalage lu dans
    // _TranslateTex), mais la particule est un carré ALIGNÉ SUR SON MOUVEMENT : 2e lecture de _TranslateTex à
    // uv + (P0.w, P1.x) / échelle x demi-taille x P0.y x alpha -> direction d = normalize(point 2 − point 1) ;
    // côté = normalize(d x (vers l'œil)) ; coins C ± w(côté ± d), w = |s0 − s1| x P0.x / 2.
    // Taille du décalage (vertex shader) : COLOR0.rgb x P0.z x (1 + P1.w x (échelle moyenne − 1)).
    _ligne1(p, uv) {
      const J = p.jeu, G = p.geoCPU, V = this._V, M = p.modele || ID, P = (p.jeuP || J.params), P0 = P[0] || [1, 1, 1, 0], P1 = P[1] || [0, 0, 0, 0];
      const LV = mul(V, M), tPos = J.donnees[2], tCol = J.donnees[1];
      if (!tPos) return null;
      const em = (Math.hypot(M[0], M[1], M[2]) + Math.hypot(M[4], M[5], M[6]) + Math.hypot(M[8], M[9], M[10])) / 3;
      const ech = 1 + P1[3] * (em - 1);
      const tp = (m, u, v) => [m[0] * u + m[1] * v - m[2] - 2 * m[1], m[4] * u + m[5] * v + 2 - 2 * m[5] - m[6]];
      const lire = (t, u, v) => { if (!t) return [1, 1, 1, 1]; const W = t.width, H = t.height, d = t.data;
        const x = Math.min(W - 1, Math.max(0, u * W - 0.5)), y = Math.min(H - 1, Math.max(0, v * H - 0.5));
        const x0 = Math.floor(x), y0 = Math.floor(y), x1 = Math.min(W - 1, x0 + 1), y1 = Math.min(H - 1, y0 + 1), fx = x - x0, fy = y - y0;
        const o = [0, 0, 0, 0];
        for (const [xx, yy, f] of [[x0, y0, (1 - fx) * (1 - fy)], [x1, y0, fx * (1 - fy)], [x0, y1, (1 - fx) * fy], [x1, y1, fx * fy]]) {
          const i = (yy * W + xx) * 4; for (let k = 0; k < 4; k++) o[k] += d[i + k] / 255 * f; }
        return o; };
      const vue = k => { const x = G.pos[3 * k], y = G.pos[3 * k + 1], z = G.pos[3 * k + 2];
        return [LV[0] * x + LV[4] * y + LV[8] * z + LV[12], LV[1] * x + LV[5] * y + LV[9] * z + LV[13], LV[2] * x + LV[6] * y + LV[10] * z + LV[14]]; };
      const sub = (a, b) => [a[0] - b[0], a[1] - b[1], a[2] - b[2]], nrm = a => { const l = Math.hypot(a[0], a[1], a[2]) || 1; return [a[0] / l, a[1] / l, a[2] / l]; };
      const cr = (a, b) => [a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0]];
      const n = Math.floor(G.idx.length / 3), pos = new Float32Array(n * 12), col = new Uint8Array(n * 16), tex = new Float32Array(n * 8), ind = new Uint16Array(n * 6);
      const u0 = uv[0], coin = (u, v) => [u0[0] * u + u0[1] * v + u0[2], u0[4] * u + u0[5] * v + u0[6]];
      const UV = [coin(1, 0), coin(0, 0), coin(1, 1), coin(0, 1)], uv1 = G.uvs[1] || G.uvs[0], uv2 = G.uvs[2] || G.uvs[0];
      let m = 0;
      for (let t = 0; t < n && m < 16000; t++) {
        const i0 = G.idx[3 * t], s0 = vue(i0), s1 = vue(G.idx[3 * t + 1]), s2 = vue(G.idx[3 * t + 2]);
        const N = nrm(cr(nrm(sub(s1, s0)), nrm(sub(s2, s0)))), c = [(s0[0] + s1[0] + s2[0]) / 3, (s0[1] + s1[1] + s2[1]) / 3, (s0[2] + s1[2] + s2[2]) / 3];
        const U = nrm(sub(s0, c)), W3 = cr(N, U);
        const k0 = [0, 1, 2, 3].map(k => G.col[4 * i0 + k] / 255), o3 = [k0[0] * P0[2] * ech, k0[1] * P0[2] * ech, k0[2] * P0[2] * ech];
        const dep = T => { const d = [(T[0] * 2 - 1) * o3[0], (T[1] * 2 - 1) * o3[1], (T[2] * 2 - 1) * o3[2]];
          return [0, 1, 2].map(i => d[0] * W3[i] + d[1] * N[i] + d[2] * U[i]); };
        const [pu, pv] = tp(uv[2], uv2[2 * i0], uv2[2 * i0 + 1]), T = lire(tPos, pu, pv), O = dep(T);
        const w = Math.abs(Math.hypot(...sub(s0, s1)) * P0[0] * 0.5), L = w * P0[1] * T[3];
        const O2 = dep(lire(tPos, pu + P0[3] / em * L, pv + P1[0] / em * L));
        const C = [c[0] + O[0], c[1] + O[1], c[2] + O[2]];
        const d = nrm(sub(O2, O)), cote = nrm(cr(d, nrm([-C[0], -C[1], -C[2]])));
        if (!(w > 1e-6)) continue;
        const [cu, cv] = tp(uv[1], uv1[2 * i0], uv1[2 * i0 + 1]), Cc = lire(tCol, cu, cv);
        const k1 = [0, 1, 2, 3].map(k => G.col1[4 * i0 + k] / 255);
        const rgba = [Cc[0] * k1[0], Cc[1] * k1[1], Cc[2] * k1[2], Cc[3] * k1[3] * k0[3]].map(x => Math.max(0, Math.min(255, Math.round(x * 255))));
        [[1, 1], [-1, 1], [1, -1], [-1, -1]].forEach(([a, b], j) => {      // (côté, d) : (+,+) (−,+) (+,−) (−,−) comme le jeu
          pos.set([0, 1, 2].map(i => C[i] + w * (a * cote[i] + b * d[i])), (4 * m + j) * 3);
          col.set(rgba, (4 * m + j) * 4); tex.set(UV[j], (4 * m + j) * 2); });
        ind.set([4 * m, 4 * m + 1, 4 * m + 2, 4 * m + 1, 4 * m + 2, 4 * m + 3], 6 * m); m++;
      }
      if (!m) return null;
      const gl = this.gl, B = p.partBuf || (p.partBuf = { bp: gl.createBuffer(), bc: gl.createBuffer(), bt: gl.createBuffer(), bi: gl.createBuffer() });
      gl.bindBuffer(gl.ARRAY_BUFFER, B.bp); gl.bufferData(gl.ARRAY_BUFFER, pos.subarray(0, m * 12), gl.DYNAMIC_DRAW);
      gl.bindBuffer(gl.ARRAY_BUFFER, B.bc); gl.bufferData(gl.ARRAY_BUFFER, col.subarray(0, m * 16), gl.DYNAMIC_DRAW);
      gl.bindBuffer(gl.ARRAY_BUFFER, B.bt); gl.bufferData(gl.ARRAY_BUFFER, tex.subarray(0, m * 8), gl.DYNAMIC_DRAW);
      gl.bindBuffer(gl.ELEMENT_ARRAY_BUFFER, B.bi); gl.bufferData(gl.ELEMENT_ARRAY_BUFFER, ind.subarray(0, m * 6), gl.DYNAMIC_DRAW);
      B.ni = m * 6; return B;
    }
    // Effect_FakeParticleLine2.gfxo (traduit le 13/11/2026) : pour chaque triangle, 4 points lus dans _TranslateTex (case 2) à
    // uv, uv + D, uv + 2D, uv + 3D (D = alpha du 1er point x (P0.w, P1.x)), placés dans le repère du triangle (normale, centre,
    // sommet 0) x échelle (|colonnes de l'objet| x COLOR0.xyz x P0.z) ; ruban face à la caméra de demi-largeur |s0 - s1| x P0.x / 2 ;
    // courbe de Bézier (points du milieu corrigés par P1.y), 12 paires de sommets à t = k / 12 (k = 0..11), v = k / 11.
    // Couleur = _ColorAnimeTex (case 1) x COLOR1 ; alpha x COLOR0.w.
    _ligne2(p, uv) {
      const J = p.jeu, G = p.geoCPU, V = this._V, M = p.modele || ID, P = (p.jeuP || J.params), P0 = P[0] || [1, 1, 1, 0], P1 = P[1] || [0, 0, 0, 0];
      const LV = mul(V, M), tTr = J.donnees[2], tCol = J.donnees[1];
      if (!tTr) return null;
      const tp = (m, u, v) => [m[0] * u + m[1] * v - m[2] - 2 * m[1], m[4] * u + m[5] * v + 2 - 2 * m[5] - m[6]];
      const lire = (t, u, v) => { if (!t) return [1, 1, 1, 1]; const W = t.width, H = t.height, d = t.data;
        const x = Math.min(W - 1, Math.max(0, u * W - 0.5)), y = Math.min(H - 1, Math.max(0, v * H - 0.5));
        const x0 = Math.floor(x), y0 = Math.floor(y), x1 = Math.min(W - 1, x0 + 1), y1 = Math.min(H - 1, y0 + 1), fx = x - x0, fy = y - y0;
        const o = [0, 0, 0, 0];
        for (const [xx, yy, f] of [[x0, y0, (1 - fx) * (1 - fy)], [x1, y0, fx * (1 - fy)], [x0, y1, (1 - fx) * fy], [x1, y1, fx * fy]]) {
          const i = (yy * W + xx) * 4; for (let k = 0; k < 4; k++) o[k] += d[i + k] / 255 * f; }
        return o; };
      const vue = k => { const x = G.pos[3 * k], y = G.pos[3 * k + 1], z = G.pos[3 * k + 2];
        return [LV[0] * x + LV[4] * y + LV[8] * z + LV[12], LV[1] * x + LV[5] * y + LV[9] * z + LV[13], LV[2] * x + LV[6] * y + LV[10] * z + LV[14]]; };
      const sub = (a, b) => [a[0] - b[0], a[1] - b[1], a[2] - b[2]], add = (a, b) => [a[0] + b[0], a[1] + b[1], a[2] + b[2]];
      const sc = (a, k) => [a[0] * k, a[1] * k, a[2] * k], nrm = a => { const l = Math.hypot(a[0], a[1], a[2]) || 1; return [a[0] / l, a[1] / l, a[2] / l]; };
      const cr = (a, b) => [a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0]];
      const comb = (w, Q) => [0, 1, 2].map(i => w[0] * Q[0][i] + w[1] * Q[1][i] + w[2] * Q[2][i] + w[3] * Q[3][i]);
      const eM = [Math.hypot(M[0], M[1], M[2]), Math.hypot(M[4], M[5], M[6]), Math.hypot(M[8], M[9], M[10])];
      const uv1 = G.uvs[1] || G.uvs[0], uv2 = G.uvs[2] || G.uvs[0], P2 = P[2] || [0, 0, 0, 0];
      let F = null;
      if (J.ligne2F) { const k = P2[1] * (eM[0] + eM[1] + eM[2]) / 3, Fw = [P1[2] * k, P1[3] * k, P2[0] * k];
        F = [0, 1, 2].map(i => V[i] * Fw[0] + V[4 + i] * Fw[1] + V[8 + i] * Fw[2]); }
      const n = Math.min(Math.floor(G.idx.length / 3), 2600), pos = new Float32Array(n * 72), col = new Uint8Array(n * 96), tex = new Float32Array(n * 48), ind = new Uint16Array(n * 66);
      let m = 0;
      for (let t = 0; t < n; t++) {
        const i0 = G.idx[3 * t], s0 = vue(i0), s1 = vue(G.idx[3 * t + 1]), s2 = vue(G.idx[3 * t + 2]);
        const N = nrm(cr(nrm(sub(s1, s0)), nrm(sub(s2, s0)))), c = sc(add(add(s0, s1), s2), 1 / 3);
        const u = nrm(sub(s0, c)), Wv = cr(N, u);
        const k0 = [0, 1, 2, 3].map(k => G.col[4 * i0 + k] / 255);
        const o3 = [eM[0] * k0[0] * P0[2], eM[1] * k0[1] * P0[2], eM[2] * k0[2] * P0[2]];
        const [pu, pv] = tp(uv[2], uv2[2 * i0], uv2[2 * i0 + 1]);
        const T0 = lire(tTr, pu, pv), du = T0[3] * P0[3], dv = T0[3] * P1[0];
        const pt = T => { const d = [(T[0] * 2 - 1) * o3[0], (T[1] * 2 - 1) * o3[1], (T[2] * 2 - 1) * o3[2]];
          return add(add(add(sc(N, d[1]), sc(Wv, d[0])), sc(u, d[2])), c); };
        const q = [pt(T0), pt(lire(tTr, pu + du, pv + dv)), pt(lire(tTr, pu + 2 * du, pv + 2 * dv)), pt(lire(tTr, pu + 3 * du, pv + 3 * dv))];
        // Line2F (Effect_FakeParticleLine2F.gfxo) : chaque point est poussé par une force fixe du MONDE :
        // q_i += min(max(sat(1 − v_i) − P2.w, 0)^P2.z, 1) x échelle moyenne x P2.y x (P1.z, P1.w, P2.x) (repère caméra via u_mtxVW)
        if (F) for (let i = 0; i < 4; i++) { const b = Math.max(Math.min(Math.max(1 - (pv + i * dv), 0), 1) - P2[3], 0);
          const f = Math.min(b > 0 ? Math.pow(b, P2[2]) : 0, 1); q[i] = add(q[i], sc(F, f)); }
        const w = Math.abs(Math.hypot(...sub(s0, s1)) * P0[0] * 0.5);
        const neg = a => [-a[0], -a[1], -a[2]];
        const sd = [nrm(cr(sub(q[0], q[1]), neg(q[0]))),
          nrm(cr(sc(add(nrm(sub(q[0], q[1])), nrm(sub(q[1], q[2]))), 0.5), neg(q[1]))),
          nrm(cr(sc(add(nrm(sub(q[1], q[2])), nrm(sub(q[2], q[3]))), 0.5), neg(q[2]))),
          nrm(cr(sub(q[2], q[3]), neg(q[3])))];
        const cA = [0, 1, 2, 3].map(i => add(q[i], sc(sd[i], w))), cB = [0, 1, 2, 3].map(i => sub(q[i], sc(sd[i], w)));
        const corr = C => { const a1 = comb([0.296741, 0.444444, 0.221889, 0.036926], C), a2 = comb([0.036926, 0.221889, 0.444444, 0.296741], C);
          return [C[0], add(C[1], sc(sub(C[1], a1), P1[1])), add(C[2], sc(sub(C[2], a2), P1[1])), C[3]]; };
        const QA = corr(cA), QB = corr(cB);
        const [cu, cv] = tp(uv[1], uv1[2 * i0], uv1[2 * i0 + 1]), Cc = lire(tCol, cu, cv);
        const k1 = [0, 1, 2, 3].map(k => G.col1[4 * i0 + k] / 255);
        const rgba = [Cc[0] * k1[0], Cc[1] * k1[1], Cc[2] * k1[2], Cc[3] * k1[3] * k0[3]].map(x => Math.max(0, Math.min(255, Math.round(x * 255))));
        for (let k = 0; k < 12; k++) { const tt = k / 12, b = [(1 - tt) ** 3, 3 * tt * (1 - tt) ** 2, 3 * tt * tt * (1 - tt), tt ** 3];
          const A = k ? comb(b, QA) : QA[0], B = k ? comb(b, QB) : QB[0], o = 24 * m + 2 * k;
          pos.set(A, 3 * o); pos.set(B, 3 * o + 3); col.set(rgba, 4 * o); col.set(rgba, 4 * o + 4);
          tex.set([1, k / 11, 0, k / 11], 2 * o); }
        for (let k = 0; k < 11; k++) { const o = 24 * m + 2 * k; ind.set([o, o + 1, o + 2, o + 2, o + 1, o + 3], 66 * m + 6 * k); }
        m++;
      }
      if (!m) return null;
      const gl = this.gl, B = p.partBuf || (p.partBuf = { bp: gl.createBuffer(), bc: gl.createBuffer(), bt: gl.createBuffer(), bi: gl.createBuffer() });
      gl.bindBuffer(gl.ARRAY_BUFFER, B.bp); gl.bufferData(gl.ARRAY_BUFFER, pos.subarray(0, m * 72), gl.DYNAMIC_DRAW);
      gl.bindBuffer(gl.ARRAY_BUFFER, B.bc); gl.bufferData(gl.ARRAY_BUFFER, col.subarray(0, m * 96), gl.DYNAMIC_DRAW);
      gl.bindBuffer(gl.ARRAY_BUFFER, B.bt); gl.bufferData(gl.ARRAY_BUFFER, tex.subarray(0, m * 48), gl.DYNAMIC_DRAW);
      gl.bindBuffer(gl.ELEMENT_ARRAY_BUFFER, B.bi); gl.bufferData(gl.ELEMENT_ARRAY_BUFFER, ind.subarray(0, m * 66), gl.DYNAMIC_DRAW);
      B.ni = m * 66; return B;
    }
    // vraies particules : quadrilatères de l'image (calcul du jeu, web/particules.js), passés en repère caméra
    _quadsEmetteur(p, monde) {
      const V = this._V; if (!V || !p.ptl.parts.length) return null;
      const camRot = [0, 1, 2].map(i => [0, 1, 2].map(j => V[i * 4 + j]));           // caméra -> monde (transposée de la vue)
      const t = [V[12], V[13], V[14]], camPos = [0, 1, 2].map(i => -(camRot[i][0] * t[0] + camRot[i][1] * t[1] + camRot[i][2] * t[2]));
      p.ptl.teinte = p.teintePtl || null;                 // (14/11/2026) teinte des particules choisie dans l'Atelier
      const Q = p.ptl.quads(camRot, camPos, p.ptlN ? p.ptlN.e : [1, 1, 1], 1), n = Math.min(Q.n, 16000);
      if (!n) return null;
      const pos = Q.pos;
      // SmokePar1 (monde) : sommets, NORMAL et TANGENT du jeu en repère du monde (u_mtxLW = identité : le shader passe
      // POSITION par u_mtxLP, donc les sommets des particules sont déjà dans le monde) ; sinon : repère caméra
      if (!monde) for (let i = 0; i < n * 4; i++) { const x = pos[3 * i], y = pos[3 * i + 1], z = pos[3 * i + 2];
        pos[3 * i] = V[0] * x + V[4] * y + V[8] * z + V[12]; pos[3 * i + 1] = V[1] * x + V[5] * y + V[9] * z + V[13]; pos[3 * i + 2] = V[2] * x + V[6] * y + V[10] * z + V[14]; }
      const ind = new Uint16Array(n * 6);
      for (let m = 0; m < n; m++) ind.set([4 * m, 4 * m + 1, 4 * m + 2, 4 * m + 3, 4 * m + 2, 4 * m + 1], 6 * m);   // (0,1,2) (3,2,1) comme le jeu
      const gl = this.gl, B = p.partBuf || (p.partBuf = { bp: gl.createBuffer(), bc: gl.createBuffer(), bt: gl.createBuffer(), bta: gl.createBuffer(), btb: gl.createBuffer(), bi: gl.createBuffer(), cf: true });
      B.monde = !!monde;
      if (monde) { if (!B.bn) { B.bn = gl.createBuffer(); B.btg = gl.createBuffer(); }
        gl.bindBuffer(gl.ARRAY_BUFFER, B.bn); gl.bufferData(gl.ARRAY_BUFFER, Q.nor.subarray(0, n * 12), gl.DYNAMIC_DRAW);
        gl.bindBuffer(gl.ARRAY_BUFFER, B.btg); gl.bufferData(gl.ARRAY_BUFFER, Q.tan.subarray(0, n * 12), gl.DYNAMIC_DRAW); }
      gl.bindBuffer(gl.ARRAY_BUFFER, B.bp); gl.bufferData(gl.ARRAY_BUFFER, pos.subarray(0, n * 12), gl.DYNAMIC_DRAW);
      gl.bindBuffer(gl.ARRAY_BUFFER, B.bc); gl.bufferData(gl.ARRAY_BUFFER, Q.col.subarray(0, n * 16), gl.DYNAMIC_DRAW);
      gl.bindBuffer(gl.ARRAY_BUFFER, B.bt); gl.bufferData(gl.ARRAY_BUFFER, Q.uv[0].subarray(0, n * 8), gl.DYNAMIC_DRAW);
      gl.bindBuffer(gl.ARRAY_BUFFER, B.bta); gl.bufferData(gl.ARRAY_BUFFER, Q.uv[1].subarray(0, n * 8), gl.DYNAMIC_DRAW);
      gl.bindBuffer(gl.ARRAY_BUFFER, B.btb); gl.bufferData(gl.ARRAY_BUFFER, Q.uv[2].subarray(0, n * 8), gl.DYNAMIC_DRAW);
      gl.bindBuffer(gl.ELEMENT_ARRAY_BUFFER, B.bi); gl.bufferData(gl.ELEMENT_ARRAY_BUFFER, ind, gl.DYNAMIC_DRAW);
      B.ni = n * 6;
      const posC = monde ? Array.from(pos.subarray(0, n * 12), (x, i) => { const j = i - (i % 3), k = i % 3;   // rendu Direct3D : repère caméra
        return V[k] * pos[j] + V[4 + k] * pos[j + 1] + V[8 + k] * pos[j + 2] + V[12 + k]; }) : Array.from(pos.subarray(0, n * 12));
      B.cpu = { n, pos: posC, col: Array.from(Q.col.subarray(0, n * 16)),
        uv: [0, 1, 2].map(k => Array.from(Q.uv[k].subarray(0, n * 8))), idx: Array.from(ind) };     // (rendu Direct3D)
      // SmokePar1 : le rendu Direct3D reçoit aussi les sommets du monde, NORMAL et TANGENT du jeu, et u_mtxLP = P x V
      if (monde) Object.assign(B.cpu, { monde: true, posW: Array.from(pos.subarray(0, n * 12)), nor: Array.from(Q.nor.subarray(0, n * 12)),
        tan: Array.from(Q.tan.subarray(0, n * 12)), mvpW: Array.from(mul(this._P, this._V)), V: Array.from(this._V) });
      return B;
    }
    // colonne de la palette BallAura0010 dont la couleur (bas du dégradé) est la plus proche de la teinte demandée
    _colonneProche(c) {
      const x = typeof E !== 'undefined' && Object.entries(E.textures || {}).find(([k]) => /BallAura0010$/.test(k));
      const im = x && x[1].orig; if (!im) return null;
      const n = Math.hypot(c[0], c[1], c[2]) || 1, cn = c.map(v => v / n); let best = null, bd = 1e9;
      for (let col = 0; col < 8; col++) { const i = ((im.height - 1) * im.width + col) * 4, r = im.data[i], g = im.data[i + 1], b = im.data[i + 2];
        const m = Math.hypot(r, g, b); if (m < 10) continue; const d = Math.hypot(r / m - cn[0], g / m - cn[1], b / m - cn[2]); if (d < bd) { bd = d; best = col; } }
      return best;
    }
    _blanc() {
      if (this._texBlanc) return this._texBlanc;
      const gl = this.gl, t = this._texBlanc = gl.createTexture(); gl.bindTexture(gl.TEXTURE_2D, t);
      gl.texImage2D(gl.TEXTURE_2D, 0, gl.RGBA, 1, 1, 0, gl.RGBA, gl.UNSIGNED_BYTE, new Uint8Array([255, 255, 255, 255])); return t;
    }
    _peau(p, mats) {
      const s = p.peau, P = s.pos0, O = s.os, W = s.poids, out = s.sortie, N = s.nor0, on = s.sortieN, n = P.length / 3;
      for (let v = 0; v < n; v++) {
        const x = P[3 * v], y = P[3 * v + 1], z = P[3 * v + 2], nx = N[3 * v], ny = N[3 * v + 1], nz = N[3 * v + 2];
        let a = 0, b = 0, c = 0, d = 0, e = 0, f = 0;
        for (let k = 0; k < 4; k++) { const w = W[4 * v + k]; if (!w) continue; const m = mats[O[4 * v + k]]; if (!m) continue;
          a += w * (m[0] * x + m[4] * y + m[8] * z + m[12]); b += w * (m[1] * x + m[5] * y + m[9] * z + m[13]); c += w * (m[2] * x + m[6] * y + m[10] * z + m[14]);
          d += w * (m[0] * nx + m[4] * ny + m[8] * nz); e += w * (m[1] * nx + m[5] * ny + m[9] * nz); f += w * (m[2] * nx + m[6] * ny + m[10] * nz); }
        out[3 * v] = a; out[3 * v + 1] = b; out[3 * v + 2] = c;
        const l = Math.hypot(d, e, f) || 1; on[3 * v] = d / l; on[3 * v + 1] = e / l; on[3 * v + 2] = f / l;
      }
      const gl = this.gl; gl.bindBuffer(gl.ARRAY_BUFFER, p.bp); gl.bufferSubData(gl.ARRAY_BUFFER, 0, out);
      gl.bindBuffer(gl.ARRAY_BUFFER, p.bn); gl.bufferSubData(gl.ARRAY_BUFFER, 0, on);
    }
    _dessinerToon(liste, mvp, w, h) {
      const gl = this.gl, L = this.lt; gl.useProgram(this.toon); gl.uniform1f(L.profPack, this._passeProf ? 1 : 0);
      gl.uniformMatrix4fv(L.mvp, false, mvp); gl.uniform2f(L.ecran, w, h); gl.uniform3f(L.lum, 0.45, 0.8, 0.4);
      // lumières ponctuelles des joueurs (masque & 1) ; réglages du stade Raimon (s10g001_g1.objbin, CLightData)
      const PL = (this.lecteur ? this.lumPL || [] : []).filter(l => (l.masque & 1) && l.att > 0).slice(0, 4), R = this.reglagesJoueurs || {};
      const pp = new Float32Array(16), pc = new Float32Array(16);
      PL.forEach((l, i) => { pp.set([l.pos[0], l.pos[1], l.pos[2], l.att], 4 * i); pc.set([l.col[0], l.col[1], l.col[2], 1], 4 * i); });
      gl.uniform1f(L.nPL, PL.length); gl.uniform4fv(L.plPos, pp); gl.uniform4fv(L.plCol, pc);
      gl.uniform4fv(L.plToon, R.toon || [0, 0.5, -0.5, 1]); gl.uniform4fv(L.plBlend, R.blend || [1, 0.2, 0.5, 0.85]);
      gl.uniform2fv(L.plRim, R.rim || [2, 2]); gl.uniform4fv(L.plRate, R.rate || [0.5, 300, 0.2, 0.1]); gl.uniform3fv(L.oeil, this._oeil || [0, 0, 0]);
      this._uniformsBrouillard(L, this.lecteur ? this.lumStade : null);
      gl.uniform1f(L.fChara, ((this.lumStade || {}).charaGrTParam || [0, 1, 1, 0.5])[3]);
      gl.enableVertexAttribArray(L.p); gl.enableVertexAttribArray(L.n); gl.enableVertexAttribArray(L.t);
      gl.disable(gl.BLEND); gl.enable(gl.DEPTH_TEST); gl.depthMask(true); gl.enable(gl.CULL_FACE);
      for (const passe of [1, 0]) {                     // 1 = contour (faces arrière agrandies), 0 = couleur
        gl.cullFace(passe ? gl.FRONT : gl.BACK);
        if (!passe) gl.disable(gl.CULL_FACE);
        for (const p of liste) {
          if (!this._vis(p) || !p.ni || (this.lecteur && p.animCachee)) continue;
          if (p.ptl && (!this.lecteur || !p.jeu)) continue;          // particules : seulement pendant l'animation
          if (passe && !p.contour) continue;
          { const S = this._statut, on = !passe && S && p.peau && (p.peau.acteur === S.acteur || (p.peau.acteur.startsWith('b000001') && String(S.acteur).startsWith('b000001')));
            gl.uniform1f(L.stOn, on ? 1 : 0); if (on) { gl.uniform3fv(L.stCol, S.col); gl.uniform4f(L.stRim, S.rim[0], S.rim[1], S.rim[2], S.rim_w === undefined ? 1 : S.rim_w); gl.uniform1f(L.stPow, S.pow || 1); } }
          gl.bindBuffer(gl.ARRAY_BUFFER, p.bp); gl.vertexAttribPointer(L.p, 3, gl.FLOAT, false, 0, 0);
          gl.bindBuffer(gl.ARRAY_BUFFER, p.bn); gl.vertexAttribPointer(L.n, 3, gl.FLOAT, false, 0, 0);
          gl.bindBuffer(gl.ARRAY_BUFFER, p.bt); gl.vertexAttribPointer(L.t, 2, gl.FLOAT, false, 0, 0);
          gl.uniform1f(L.contour, passe); gl.uniform1f(L.largeur, Math.max(1.2, h / 520)); gl.uniform1f(L.noir, p.noir ? 1 : 0);
          if (p.contour) gl.uniform3f(L.couleurContour, p.contour[0] * 0.55, p.contour[1] * 0.55, p.contour[2] * 0.55);
          const tx = p.texCle && this.textures[p.texCle], oc = p.ombreCle && this.textures[p.ombreCle];
          gl.activeTexture(gl.TEXTURE0); gl.bindTexture(gl.TEXTURE_2D, tx || null); gl.uniform1i(L.tex, 0); gl.uniform1f(L.aTex, tx ? 1 : 0);
          gl.activeTexture(gl.TEXTURE1); gl.bindTexture(gl.TEXTURE_2D, oc || null); gl.uniform1i(L.ombre, 1); gl.uniform1f(L.aOmbre, oc ? 1 : 0);
          gl.activeTexture(gl.TEXTURE0);
          gl.bindBuffer(gl.ELEMENT_ARRAY_BUFFER, p.bi); gl.drawElements(gl.TRIANGLES, p.ni, gl.UNSIGNED_SHORT, 0);
        }
      }
      gl.disable(gl.CULL_FACE); gl.disableVertexAttribArray(L.n); gl.enable(gl.BLEND);
    }
    vider() { for (const t of Object.values(this.textures)) this.gl.deleteTexture(t); this.textures = {}; const gl = this.gl; for (const p of this.pieces) { if (p.ptl) continue; gl.deleteBuffer(p.bp); gl.deleteBuffer(p.bc); gl.deleteBuffer(p.bi); gl.deleteBuffer(p.bt); if (p.bl) gl.deleteBuffer(p.bl); } this.pieces = []; }
    // VRAIES PARTICULES (.ptlb, 13/11/2026) : un émetteur simulé comme dans le jeu (web/particules.js), dessiné chaque image
    // avec le shader de son matériau ; p.anim = {acteur, noeud} (os de l'effet qui porte l'émetteur)
    ajouterEmetteur(cle, def, graine) {
      const p = { cle, ni: 6, visible: true, sel: false, teinte: [1, 1, 1, 1], def, ptl: new Particules.Emetteur(def, new Particules.MT19937(graine >>> 0)),
        ptlF: -1, ptlClip: null, ptlDemarre: false, boite: [[1e9, 1e9, 1e9], [-1e9, -1e9, -1e9]] };
      this.pieces.push(p); return p;
    }
    // matrice du nœud (colonnes, WebGL) -> rotation sans échelle | translation (3 lignes de 4), quaternion, échelle
    static _decomposer(N) {
      const e = [0, 1, 2].map(c => Math.hypot(N[4 * c], N[4 * c + 1], N[4 * c + 2]) || 1);
      const R = [0, 1, 2].map(r => [0, 1, 2].map(c => N[4 * c + r] / e[c]));
      const M = R.map((l, r) => [l[0], l[1], l[2], N[12 + r]]);
      return { M, q: Particules.matQuat(R), R, e };
    }
    // fait avancer un émetteur jusqu'à l'image f (1/60 s par image) ; en arrière ou trop loin : on recommence depuis 0
    _avancerEmetteur(p, f, L) {
      if (f < p.ptlF || f - p.ptlF > 900) { p.ptl.reset(); p.ptlF = -1; p.ptlClip = null; p.ptlDemarre = false; }
      for (let k = p.ptlF + 1; k <= f; k++) {
        const r = k === f && this._resCourant ? this._resCourant : L.calculer(k), o = r.objets[p.anim.acteur];
        if (!o) { p.ptlF = k; continue; }
        const mo = p.def.motion, clip = o.clip || null;
        if (clip !== p.ptlClip) {           // changement de plan de l'objet (0x14054c270 / 0x14054c110)
          if (mo.debut.length ? mo.debut.includes(clip) : !p.ptlDemarre || p.ptl.fini) { p.ptl.reset(); p.ptlDemarre = true; }
          const a = mo.fin.find(x => x[0] === clip); if (a && p.ptlDemarre) p.ptl.arreter(a[1]);
          p.ptlClip = clip; }
        const i = o.sq && o.sq.parNom[p.anim.noeud], N = i !== undefined ? mul(o.racine, o.monde[i]) : o.racine;
        const D = Vue3D._decomposer(N); p.ptlN = D;
        // ÉCHELLE DE L'ÉMETTEUR (LU 14/11/2026, nie.exe 0x14054c501) : colonnes de la matrice de l'OBJET (pas du nœud)
        D.e = Vue3D._decomposer(o.racine).e;
        if (p.ptlDemarre) p.ptl.pas(1 / 60, D.M, D.q, D.e, !!o.visible, 1);
        p.ptlVisible = !!o.visible; p.ptlF = k;
      }
    }
    // LUMIÈRES PONCTUELLES (lu dans nie.exe, 13/11/2026) : CCustomParamRefBone (0x14057be20) écrit dans des valeurs nommées
    // (CCustomParamProperty) des grandeurs prises sur des os ; CCustomPointLight (0x140f77df0) en fait une lumière :
    // valeur posParam = (x, y, z, atténuation), valeur colorParam = (r, v, b, a). boneRefType : genre = >> 4 (1 position,
    // 2 échelle, 4 / 5 direction), masque = & 15 (composantes recopiées), setType = 1re composante écrite ; boneSpace 0 = valeurs
    // locales de l'os, 1 = matrice monde (objet x os). Masque de la lumière : « type » ou 0xF7 (bit 0 joueurs, bit 1 stade).
    // DIRECTIONS (lu dans nie.exe 0x14057c3af, 14/11/2026) : genre 4 = matrice de l'os x (0, 0, 1, 0) (axe Z, constante
    // 0x14264e710), genre 5 = matrice x (0, 1, 0, 0) (axe Y, 0x14264e700), non normalisées, 4e composante 0.
    // CCustomShaderParam (0x14057a7f0) : valeur nommée -> u_shaderParam[idx] du matériau (crc du nom), masque 1 x 2 y 4 z 8 w
    // -> this.paramsShader[acteur][crc du matériau] = [[idx, masque, valeur], ...] (appliqué après les paramètres animés G4MA)
    _calculerLumieres(res) {
      const out = []; this.lumPL = out; const PS = {}; this.paramsShader = PS;
      for (const { acteur, def } of this.lumieresDefs || []) {
        const o = res.objets[acteur];
        if (!o || !o.visible || !o.sq) continue;             // (APPROCHÉ : allumée quand l'objet de l'effet est actif)
        const P = {}; for (const [k, v] of Object.entries(def.params || {})) P[k] = v.slice();
        for (const r of def.refs || []) {
          const i = o.sq.parCrc[r.boneNameCrc >>> 0], dst = P[r.nameCrc >>> 0]; if (i === undefined || !dst) continue;
          const genre = r.boneRefType >> 4, masque = r.boneRefType & 15; let src = null;
          if (r.boneSpace === 0) { const l = o.local && o.local[i]; if (!l) continue;
            if (genre === 1) src = [l.t[0], l.t[1], l.t[2], 1]; else if (genre === 2) src = [l.e[0], l.e[1], l.e[2], 1];
            else if (genre === 4 || genre === 5) { const [x, y, z, w] = l.r, s = genre === 4 ? l.e[2] : l.e[1];   // quaternion xyzw
              src = genre === 4 ? [2 * (x * z + w * y) * s, 2 * (y * z - w * x) * s, (1 - 2 * (x * x + y * y)) * s, 0]
                                : [2 * (x * y - w * z) * s, (1 - 2 * (x * x + z * z)) * s, 2 * (y * z + w * x) * s, 0]; } }
          else { const N = mul(o.racine, o.monde[i]);
            if (genre === 1) src = [N[12], N[13], N[14], 1];
            else if (genre === 2) src = [0, 1, 2].map(c => Math.hypot(N[4 * c], N[4 * c + 1], N[4 * c + 2])).concat([1]);
            else if (genre === 4) src = [N[8], N[9], N[10], 0];
            else if (genre === 5) src = [N[4], N[5], N[6], 0]; }
          if (!src) continue;
          let j = r.setType; for (let c = 0; c < 4 && j < 4; c++) if ((masque >> c) & 1) dst[j++] = src[c];
        }
        for (const s of def.shader || []) { const v = P[s.refParamNameCrc >>> 0]; if (!v) continue;
          const A = PS[acteur] || (PS[acteur] = {}), m = s.matNameCrc >>> 0;
          (A[m] || (A[m] = [])).push([s.setShaderParamIdx, s.refParamType & 15, v.slice()]); }
        if (this.lumieresActives === false) continue;
        for (const l of def.lumieres || []) { const p = P[l.posParamCrc >>> 0], c = P[l.colorParamCrc >>> 0]; if (!p || !c) continue;
          // (23/11) intensité réglée dans l'Atelier (Lumières de l'effet) : couleur × k, comme l'animation que l'export écrit
          const kL = this.lumK && this.lumK[acteur] !== undefined ? this.lumK[acteur] : 1;
          out.push({ pos: p.slice(0, 3), att: p[3], col: [c[0] * kL, c[1] * kL, c[2] * kL, c[3]], masque: l.type || 0xF7 }); }
      }
    }
    // cubemap du stade : {taille, niveaux} + octets RGBA (6 faces x niveaux)
    cubemap(meta, octets) {
      const gl = this.gl, t = gl.createTexture(); gl.bindTexture(gl.TEXTURE_CUBE_MAP, t); let o = 0;
      for (let f = 0; f < 6; f++) { let s = meta.taille;
        for (let k = 0; k < meta.niveaux; k++) { const n = s * s * 4;
          gl.texImage2D(gl.TEXTURE_CUBE_MAP_POSITIVE_X + f, k, gl.RGBA, s, s, 0, gl.RGBA, gl.UNSIGNED_BYTE, octets.subarray(o, o + n)); o += n; s = Math.max(1, s >> 1); } }
      gl.texParameteri(gl.TEXTURE_CUBE_MAP, gl.TEXTURE_MIN_FILTER, gl.LINEAR_MIPMAP_LINEAR); gl.texParameteri(gl.TEXTURE_CUBE_MAP, gl.TEXTURE_MAG_FILTER, gl.LINEAR);
      gl.texParameteri(gl.TEXTURE_CUBE_MAP, gl.TEXTURE_WRAP_S, gl.CLAMP_TO_EDGE); gl.texParameteri(gl.TEXTURE_CUBE_MAP, gl.TEXTURE_WRAP_T, gl.CLAMP_TO_EDGE);
      this.cubeStade = t; this.cubeNiveaux = meta.niveaux;
    }
    // carte de profondeur vue du soleil (ombres portées) : stade + joueurs, projection orthographique centrée sur la cible
    // de la caméra, 70 m de côté (APPROCHÉ : le jeu a 3 cascades dont les réglages sont calculés par le moteur)
    // OMBRES EN 3 CASCADES, comme le moteur : tranches de la vue [near, near + L/3, near + 2L/3, autoCascadeFarMax] (0x14133b1a0,
    // cas de repli : le drapeau d'optimisation +0x16B n'est jamais mis), puis une matrice LiSPSM par tranche (0x141340de0 / 0x1405aa8a0,
    // reconstruite et vérifiée à l'émulateur : cascadesOmbre). Une carte de 2048² par cascade (taille du jeu : non lue).
    _carteOmbre(cible) {
      // 1024 x 1024 comme le jeu : RT_ShadowCs0..2 (cases 11 à 13) dans common/system/app_config_6.00.23.00.cfg.bin (COMMON)
      const gl = this.gl, R = this.lumStade || {}, T = 1024;
      if (!this._fbO) { this._fbO = [];
        for (let k = 0; k < 3; k++) { const t = gl.createTexture(); gl.bindTexture(gl.TEXTURE_2D, t); gl.texImage2D(gl.TEXTURE_2D, 0, gl.RGBA, T, T, 0, gl.RGBA, gl.UNSIGNED_BYTE, null);
          for (const [k2, v] of [[gl.TEXTURE_MIN_FILTER, gl.NEAREST], [gl.TEXTURE_MAG_FILTER, gl.NEAREST], [gl.TEXTURE_WRAP_S, gl.CLAMP_TO_EDGE], [gl.TEXTURE_WRAP_T, gl.CLAMP_TO_EDGE]]) gl.texParameteri(gl.TEXTURE_2D, k2, v);
          const rb = gl.createRenderbuffer(); gl.bindRenderbuffer(gl.RENDERBUFFER, rb); gl.renderbufferStorage(gl.RENDERBUFFER, gl.DEPTH_COMPONENT16, T, T);
          const fb = gl.createFramebuffer(); gl.bindFramebuffer(gl.FRAMEBUFFER, fb);
          gl.framebufferTexture2D(gl.FRAMEBUFFER, gl.COLOR_ATTACHMENT0, gl.TEXTURE_2D, t, 0); gl.framebufferRenderbuffer(gl.FRAMEBUFFER, gl.DEPTH_ATTACHMENT, gl.RENDERBUFFER, rb);
          this._fbO.push({ fb, tex: t }); }
        gl.bindFramebuffer(gl.FRAMEBUFFER, null); }
      if (!this._V || !this._P) { this._ombreSoleil = null; return; }
      const dir = ((R.useShadowDir || [0])[0] && R.shadowDir) ? R.shadowDir : (R.lightDir || [0, 0.77, 0.64]);
      const auto = (R.isAutoCascadeRange || [0])[0], nC = 0.1;                     // near de la caméra du jeu (constructeur 0x140b7a4d0 : 0,1)
      let tr;
      if (auto) { const fm = (R.autoCascadeFarMax || [100])[0], L = fm - nC; tr = [[nC, nC + L / 3], [nC + L / 3, nC + 2 * L / 3], [nC + 2 * L / 3, fm]]; }
      else { const N = R.shadowCascadeNear || [0.1, 20, 50], F = R.shadowCascadeFar || [20, 50, 150]; tr = [0, 1, 2].map(i => [N[i], F[i]]); }
      const C = cascadesOmbre(this._V, this._P, dir, (R.ref_scale || [4])[0], tr);
      // les cartes de l'image précédente ne doivent plus être liées à une case de texture (sinon WebGL refuse les dessins : « feedback loop »)
      const texs = this._fbO.map(o => o.tex);
      for (let u = 0; u < 8; u++) { gl.activeTexture(gl.TEXTURE0 + u); if (texs.includes(gl.getParameter(gl.TEXTURE_BINDING_2D))) gl.bindTexture(gl.TEXTURE_2D, null); }
      gl.activeTexture(gl.TEXTURE0);
      gl.useProgram(this.prog); gl.uniformMatrix4fv(this.loc.modele, false, ID); gl.uniform1f(this.loc.profPack, 1);
      gl.uniform4fv(this.loc.uvx, [1, 1, 0, 0]); gl.uniform1f(this.loc.aTex, 0); gl.uniform1f(this.loc.aNuage, 0); if (this.loc.aPL) gl.uniform1f(this.loc.aPL, 0);
      gl.disable(gl.BLEND); gl.enable(gl.DEPTH_TEST); gl.depthMask(true); gl.disable(gl.CULL_FACE);
      for (let k = 0; k < 3; k++) {
        gl.bindFramebuffer(gl.FRAMEBUFFER, this._fbO[k].fb); gl.viewport(0, 0, T, T); gl.clearColor(1, 1, 1, 1); gl.clear(gl.COLOR_BUFFER_BIT | gl.DEPTH_BUFFER_BIT);
        gl.uniformMatrix4fv(this.loc.mvp, false, C.vp[k]);
        for (const p of this.pieces) { if (!(p.terrain || p.peau) || !this._vis(p) || !p.ni || p.animCachee) continue;
          gl.bindBuffer(gl.ARRAY_BUFFER, p.bp); gl.enableVertexAttribArray(this.loc.p); gl.vertexAttribPointer(this.loc.p, 3, gl.FLOAT, false, 0, 0);
          if (this.loc.c >= 0) { gl.disableVertexAttribArray(this.loc.c); gl.vertexAttrib4f(this.loc.c, 1, 1, 1, 1); }
          if (this.loc.t >= 0) { gl.disableVertexAttribArray(this.loc.t); gl.vertexAttrib2f(this.loc.t, 0, 0); }
          if (this.loc.nrm >= 0) gl.disableVertexAttribArray(this.loc.nrm);
          gl.bindBuffer(gl.ELEMENT_ARRAY_BUFFER, p.bi); gl.drawElements(gl.TRIANGLES, p.ni, gl.UNSIGNED_SHORT, 0); } }
      gl.uniform1f(this.loc.profPack, 0); gl.bindFramebuffer(gl.FRAMEBUFFER, this._fbCible || null); gl.clearColor(0, 0, 0, 0);
      gl.enable(gl.BLEND);
      this._ombreEffets = { tex: texs[0], vp: C.vp[0], taille: T };
      this._ombreSoleil = { tex: texs, vp: C.vp, loin: tr.map(t => t[1]), avant: C.avant, pres: tr[0][0], taille: T, tranches: tr,
        dir: norm(dir.slice(0, 3)), biais: (R.shadowBiasParam || [0.01, 1, 0.1]).slice(0, 3) };
      this._ombresD3D = this._ombreSoleil;            // copie gardée pour le rendu Direct3D (la passe transparente remet _ombreSoleil à null)
    }
    // dessin du stade avec le vrai shader (pièces p.jeuStade = {shader, tex, params, diffuse, ambient, texproj})
    _dessinerStade(liste, mvp) {
      const gl = this.gl, L = this.lm, R = this.lumStade || {}; gl.useProgram(this.pm);
      gl.uniformMatrix4fv(L.mvp, false, mvp); gl.uniform3fv(L.oeil, this._oeil || [0, 0, 0]);
      const v3 = (x, d) => (x || d).slice(0, 3), v4 = (x, d) => (x || d).concat([0, 0, 0, 0]).slice(0, 4);
      gl.uniform3fv(L.mapAmb, v3(R.mapAmbient, [1, 1, 1])); gl.uniform3fv(L.lDir, v3(R.lightDir, [0, 0.77, 0.64])); gl.uniform3fv(L.lCol, v3(R.lightColor, [1.5, 1.45, 1.45]));
      gl.uniform3fv(L.lAmb, v3(R.lightAmbient, [0.25, 0.3, 0.35])); gl.uniform4fv(L.LI, v4(R.mapPbrLightInfo, [0.25, 0.3, 0.35, 1])); gl.uniform4fv(L.IBL, v4(R.mapPbrIBLInfo, [1, 1, 1, 0.2]));
      gl.uniform4fv(L.PS, v4(R.mapPbrParamScaleInfo, [1.5, 1.2, 0, 0.8])); gl.uniform1f(L.plPow, (R.mapPointLightPow || [0.2])[0]);
      const pl = this._lumieresStade(); gl.uniform1f(L.nPL, pl.n); gl.uniform4fv(L.plPos, pl.pos); gl.uniform4fv(L.plCol, pl.col);
      this._uniformsBrouillard(L, R);
      gl.activeTexture(gl.TEXTURE4); gl.bindTexture(gl.TEXTURE_CUBE_MAP, this.cubeStade || null); gl.uniform1i(L.cube, 4);
      gl.uniform1f(L.aCube, this.cubeStade ? 1 : 0); gl.uniform1f(L.lodMax, (this.cubeNiveaux || 1) - 1);
      const O = this._ombreSoleil; gl.uniform1f(L.aOmb, O ? 1 : 0);
      if (O) { ['omb', 'omb1', 'omb2'].forEach((u, k) => { gl.activeTexture(gl.TEXTURE5 + k); gl.bindTexture(gl.TEXTURE_2D, O.tex[k]); gl.uniform1i(L[u], 5 + k); });
        ['sunVP', 'sunVP1', 'sunVP2'].forEach((u, k) => gl.uniformMatrix4fv(L[u], false, O.vp[k]));
        gl.uniform3fv(L.ombLoin, O.loin); gl.uniform3fv(L.camAv, O.avant);
        ['invVP', 'invVP1', 'invVP2'].forEach((u, k) => gl.uniformMatrix4fv(L[u], false, inv4(O.vp[k])));
        gl.uniform3fv(L.ombB, O.biais); gl.uniform3fv(L.ombDir, O.dir); gl.uniform1f(L.ombN0, O.pres); gl.uniform1f(L.ombS, O.taille); }
      gl.disable(gl.BLEND); gl.enable(gl.DEPTH_TEST); gl.depthMask(true);
      for (const p of liste) { const J = p.jeuStade, sh = J.shader || '';
        const genre = /^Map_Pbr/.test(sh) ? 1 : /^Map_T1/.test(sh) ? 2 : /^Map_Basic/.test(sh) ? 3 : 4;
        gl.uniform1f(L.genre, genre); gl.uniform1f(L.aNrm, /^Map_PbrT1L/.test(sh) ? 0 : 1); gl.uniform1f(L.couches, /^Map_PbrT2/.test(sh) ? 1 : 0);
        gl.uniform1f(L.coupe, /Cutout/.test(sh) ? 1 : 0);
        const P = k => (J.params[k] || [0, 0, 0, 0]);
        gl.uniform4fv(L.sp0, P(0)); gl.uniform4fv(L.sp1, P(1)); gl.uniform4fv(L.sp2, P(2)); gl.uniform4fv(L.sp3, P(3)); gl.uniform4fv(L.sp6, P(6));
        gl.uniform4fv(L.amb, v4(J.ambient, [0, 0, 0, 1])); gl.uniform4fv(L.diff, v4(J.diffuse, [1, 1, 1, 1]));
        const tp = J.texproj[0] || [1, 0, 0, 0, 0, 1, 0, 0]; gl.uniform4fv(L.tpA, tp.slice(0, 4)); gl.uniform4fv(L.tpB, tp.slice(4, 8));
        for (let k = 0; k < 4; k++) { gl.activeTexture(gl.TEXTURE0 + k); const tx = J.tex[k] && this.textures['stade:' + J.tex[k]];
          gl.bindTexture(gl.TEXTURE_2D, tx || this._blanc()); gl.uniform1i(L['t' + k], k); }
        gl.bindBuffer(gl.ARRAY_BUFFER, p.bp); gl.enableVertexAttribArray(L.p); gl.vertexAttribPointer(L.p, 3, gl.FLOAT, false, 0, 0);
        gl.bindBuffer(gl.ARRAY_BUFFER, p.bc); gl.enableVertexAttribArray(L.c); gl.vertexAttribPointer(L.c, 4, gl.UNSIGNED_BYTE, true, 0, 0);
        gl.bindBuffer(gl.ARRAY_BUFFER, p.bt); gl.enableVertexAttribArray(L.t); gl.vertexAttribPointer(L.t, 2, gl.FLOAT, false, 0, 0);
        if (p.bnor && L.nrm >= 0) { gl.bindBuffer(gl.ARRAY_BUFFER, p.bnor); gl.enableVertexAttribArray(L.nrm); gl.vertexAttribPointer(L.nrm, 3, gl.FLOAT, false, 0, 0); }
        if (p.btg4 && L.tg >= 0) { gl.bindBuffer(gl.ARRAY_BUFFER, p.btg4); gl.enableVertexAttribArray(L.tg); gl.vertexAttribPointer(L.tg, 4, gl.FLOAT, false, 0, 0); }
        else if (L.tg >= 0) { gl.disableVertexAttribArray(L.tg); gl.vertexAttrib4f(L.tg, 1, 0, 0, 1); }
        gl.bindBuffer(gl.ELEMENT_ARRAY_BUFFER, p.bi); gl.drawElements(gl.TRIANGLES, p.ni, gl.UNSIGNED_SHORT, 0); }
      for (const a of ['nrm', 'tg']) if (L[a] >= 0) gl.disableVertexAttribArray(L[a]);
      gl.activeTexture(gl.TEXTURE0); gl.enable(gl.BLEND);
    }
    // PROFONDEUR DE LA SCÈNE (t12 du jeu) pour les particules douces : décor et joueurs vus de la caméra, profondeur rangée
    // dans les couleurs (comme les cartes d'ombre), juste avant les effets transparents
    _profScene(opaques, mvp, w, h) {
      const gl = this.gl;
      if (!(w > 0 && h > 0)) return;                                 // canevas invisible (taille nulle)
      if (!this._fbS || this._fbS.w !== w || this._fbS.h !== h) {
        if (this._fbS) { gl.deleteTexture(this._fbS.tex); gl.deleteRenderbuffer(this._fbS.rb); gl.deleteFramebuffer(this._fbS.fb); }
        const t = gl.createTexture(); gl.bindTexture(gl.TEXTURE_2D, t); gl.texImage2D(gl.TEXTURE_2D, 0, gl.RGBA, w, h, 0, gl.RGBA, gl.UNSIGNED_BYTE, null);
        for (const [k, v] of [[gl.TEXTURE_MIN_FILTER, gl.NEAREST], [gl.TEXTURE_MAG_FILTER, gl.NEAREST], [gl.TEXTURE_WRAP_S, gl.CLAMP_TO_EDGE], [gl.TEXTURE_WRAP_T, gl.CLAMP_TO_EDGE]]) gl.texParameteri(gl.TEXTURE_2D, k, v);
        const rb = gl.createRenderbuffer(); gl.bindRenderbuffer(gl.RENDERBUFFER, rb); gl.renderbufferStorage(gl.RENDERBUFFER, gl.DEPTH_COMPONENT16, w, h);
        const fb = gl.createFramebuffer(); gl.bindFramebuffer(gl.FRAMEBUFFER, fb);
        gl.framebufferTexture2D(gl.FRAMEBUFFER, gl.COLOR_ATTACHMENT0, gl.TEXTURE_2D, t, 0); gl.framebufferRenderbuffer(gl.FRAMEBUFFER, gl.DEPTH_ATTACHMENT, gl.RENDERBUFFER, rb);
        this._fbS = { fb, tex: t, rb, w, h }; }
      for (let u = 0; u < 8; u++) { gl.activeTexture(gl.TEXTURE0 + u); if (gl.getParameter(gl.TEXTURE_BINDING_2D) === this._fbS.tex) gl.bindTexture(gl.TEXTURE_2D, null); }
      gl.activeTexture(gl.TEXTURE0);
      gl.bindFramebuffer(gl.FRAMEBUFFER, this._fbS.fb); gl.viewport(0, 0, w, h); gl.clearColor(1, 1, 1, 1); gl.clear(gl.COLOR_BUFFER_BIT | gl.DEPTH_BUFFER_BIT);
      gl.useProgram(this.prog); gl.uniformMatrix4fv(this.loc.mvp, false, mvp); gl.uniform1f(this.loc.profPack, 1);
      gl.uniform4fv(this.loc.uvx, [1, 1, 0, 0]); gl.uniform1f(this.loc.aTex, 0); gl.uniform1f(this.loc.aNuage, 0); if (this.loc.aPL) gl.uniform1f(this.loc.aPL, 0);
      gl.disable(gl.BLEND); gl.enable(gl.DEPTH_TEST); gl.depthMask(true); gl.disable(gl.CULL_FACE);
      for (const p of opaques) { if (!(p.terrain || p.peau) || !this._vis(p) || !p.ni || p.animCachee) continue;
        gl.uniformMatrix4fv(this.loc.modele, false, (this.lecteur && p.modele) || ID);
        gl.bindBuffer(gl.ARRAY_BUFFER, p.bp); gl.enableVertexAttribArray(this.loc.p); gl.vertexAttribPointer(this.loc.p, 3, gl.FLOAT, false, 0, 0);
        if (this.loc.c >= 0) { gl.disableVertexAttribArray(this.loc.c); gl.vertexAttrib4f(this.loc.c, 1, 1, 1, 1); }
        if (this.loc.t >= 0) { gl.disableVertexAttribArray(this.loc.t); gl.vertexAttrib2f(this.loc.t, 0, 0); }
        if (this.loc.nrm >= 0) gl.disableVertexAttribArray(this.loc.nrm);
        gl.bindBuffer(gl.ELEMENT_ARRAY_BUFFER, p.bi); gl.drawElements(gl.TRIANGLES, p.ni, gl.UNSIGNED_SHORT, 0); }
      gl.uniform1f(this.loc.profPack, 0); gl.bindFramebuffer(gl.FRAMEBUFFER, this._fbCible || null); gl.viewport(0, 0, w, h); gl.clearColor(0, 0, 0, 0);
      gl.enable(gl.BLEND);
      this._profS = { tex: this._fbS.tex, w, h };
    }
    // registres du brouillard (cb5[37…50], conversion de nie.exe 0x140f7f050 : brouillardCB) ; this.brouillard = false pour le couper
    _uniformsBrouillard(L, R) {
      const gl = this.gl, F = brouillardCB(R); gl.uniform1f(L.aFog, F && this.brouillard !== false ? 1 : 0);
      if (L.lDir) gl.uniform3fv(L.lDir, ((R && R.lightDir) || [0, 0.77, 0.64]).slice(0, 3));
      if (F) { gl.uniform3fv(L.fR, F.R); gl.uniform3fv(L.fHC, F.HC); gl.uniform3fv(L.fM, F.M); gl.uniform4fv(L.fW0, F.W0); gl.uniform4fv(L.fW1, F.W1);
        gl.uniform4fv(L.fH0, F.H0); gl.uniform4fv(L.fH1, F.H1); gl.uniform4fv(L.fB, F.B); gl.uniform1f(L.fOcc, F.occ); }
    }
    // lumières du stade (masque & 2), 4 au plus ; k = mapPointLightPow x mapAmbient du stade Raimon (s10g001_g1 : 0,2 et 1, 1, 1)
    _lumieresStade() {
      const L = (this.lumPL || []).filter(l => (l.masque & 2) && l.att > 0).slice(0, 4), pos = new Float32Array(16), col = new Float32Array(16);
      L.forEach((l, i) => { pos.set([l.pos[0], l.pos[1], l.pos[2], l.att], 4 * i); col.set([l.col[0], l.col[1], l.col[2], 1], 4 * i); });
      return { n: L.length, pos, col, k: this.plK || [0.2, 0.2, 0.2] };
    }
    // (15/11/2026) ÉCLAT d'une pièce localisée (this.eclat = {cles: Set, debut, fin} en ms) : couleur multipliée par 1 à 2,8,
    // en pulsation (2,5 fois par seconde), puis retour normal
    facteurEclat(p) {
      const e = this.eclat; if (!e || !p || !e.cles.has(p.cle)) return 1;
      const t = performance.now(); if (t > e.fin) { this.eclat = null; return 1; }
      return 1 + 1.8 * (0.5 - 0.5 * Math.cos((t - e.debut) / 1000 * Math.PI * 2 * 2.5));
    }
    // (14/11/2026) teinte des couleurs de sommets choisie dans l'Atelier ([H, C] ou null) : tampon des couleurs refait
    teinterSommets(p, t) {
      if (!p || !p.col0 || !p.bc) return; const gl = this.gl;
      let c = p.col0;
      if (t) { c = new Uint8Array(p.col0); const x = [0, 0, 0];
        for (let i = 0; i + 3 < c.length; i += 4) { x[0] = c[i] / 255; x[1] = c[i + 1] / 255; x[2] = c[i + 2] / 255; teinterHSV(x, t[0], t[1], t[2], t[3]);   // (23/11) t[2] = saturation (multiplicateur)
          for (let k = 0; k < 3; k++) c[i + k] = Math.max(0, Math.min(255, Math.floor(x[k] * 255 + 0.5))); } }
      gl.bindBuffer(gl.ARRAY_BUFFER, p.bc); gl.bufferData(gl.ARRAY_BUFFER, c, gl.STATIC_DRAW); p.teinteSom = t || null;
    }
    // geo : {nv, ni, pos: Float32Array, col: Uint8Array, idx: Uint16Array}, cle : identifiant (objet/index)
    ajouter(cle, geo) {
      Vue3D.activite = performance.now();
      const gl = this.gl, p = { cle, ni: geo.ni, visible: true, sel: false, teinte: [0.8, 0.8, 0.8, 1] };
      p.bp = gl.createBuffer(); gl.bindBuffer(gl.ARRAY_BUFFER, p.bp); gl.bufferData(gl.ARRAY_BUFFER, geo.pos, gl.STATIC_DRAW);
      p.bc = gl.createBuffer(); gl.bindBuffer(gl.ARRAY_BUFFER, p.bc); gl.bufferData(gl.ARRAY_BUFFER, geo.col, gl.STATIC_DRAW); p.col0 = geo.col;
      p.bt = gl.createBuffer(); gl.bindBuffer(gl.ARRAY_BUFFER, p.bt); gl.bufferData(gl.ARRAY_BUFFER, geo.uv, gl.STATIC_DRAW); p.texCle = null;
      if (geo.tan) { p.btan = gl.createBuffer(); gl.bindBuffer(gl.ARRAY_BUFFER, p.btan); gl.bufferData(gl.ARRAY_BUFFER, geo.tan, gl.STATIC_DRAW); }
      if (geo.nor) { p.bnor = gl.createBuffer(); gl.bindBuffer(gl.ARRAY_BUFFER, p.bnor); gl.bufferData(gl.ARRAY_BUFFER, geo.nor, gl.STATIC_DRAW); }
      if (geo.tan4) { p.btg4 = gl.createBuffer(); gl.bindBuffer(gl.ARRAY_BUFFER, p.btg4); gl.bufferData(gl.ARRAY_BUFFER, geo.tan4, gl.STATIC_DRAW); }
      if (geo.col1) { p.bc1 = gl.createBuffer(); gl.bindBuffer(gl.ARRAY_BUFFER, p.bc1); gl.bufferData(gl.ARRAY_BUFFER, geo.col1, gl.STATIC_DRAW); }
      if (geo.col1) p.geoCPU = { pos: geo.pos, col: geo.col, col1: geo.col1, idx: geo.idx, uvs: geo.uvs || [geo.uv] };
      if (geo.peau) p.peauCPU = { pos: geo.pos, nor: geo.nor, tan: geo.tan, poids: geo.peau.poids, os: geo.peau.os };   // maillage à peau
      p.btx = (geo.uvs || []).slice(1).map(u => { const b = gl.createBuffer(); gl.bindBuffer(gl.ARRAY_BUFFER, b); gl.bufferData(gl.ARRAY_BUFFER, u, gl.STATIC_DRAW); return b; });
      p.bi = gl.createBuffer(); gl.bindBuffer(gl.ELEMENT_ARRAY_BUFFER, p.bi); gl.bufferData(gl.ELEMENT_ARRAY_BUFFER, geo.idx, gl.STATIC_DRAW);
      // arêtes pour le fil de fer
      const l = new Uint16Array(geo.ni * 2);
      for (let t = 0; t + 2 < geo.ni; t += 3) { const a = geo.idx[t], b = geo.idx[t + 1], c = geo.idx[t + 2]; l.set([a, b, b, c, c, a], t * 2); }
      p.bl = gl.createBuffer(); gl.bindBuffer(gl.ELEMENT_ARRAY_BUFFER, p.bl); gl.bufferData(gl.ELEMENT_ARRAY_BUFFER, l, gl.STATIC_DRAW); p.nl = l.length;
      p.boite = this._boite(geo.pos);
      this.pieces.push(p); return p;
    }
    // PEAU DES MAILLAGES D'EFFETS (14/11/2026) : comme le shader « _vb » du jeu (4 os par sommet, u_mtxBone = cb8) ;
    // matrice de l'os k de la palette = monde animé x inverse du monde au repos (repère de l'objet ; u_mtxLW = racine).
    // p.peauK (matrices) sert aussi au rendu Direct3D. Aperçu WebGL : positions et normales recalculées sur le processeur
    // (tangentes non tournées : APPROCHÉ pour l'aperçu seulement).
    _peauEffet(p, o) {
      // (14/11/2026) inverse du monde de LIAISON lu dans le G4SK (table 0, 3 lignes de 4) quand il est là, comme le jeu
      const ib = b => new Float32Array([b[0], b[4], b[8], 0, b[1], b[5], b[9], 0, b[2], b[6], b[10], 0, b[3], b[7], b[11], 1]);
      const gl = this.gl, P = p.peauCPU, sq = o.sq, IR = sq._invRepos || (sq._invRepos = sq.mondeRepos.map((m, i) => sq.os[i] && sq.os[i].ib ? ib(sq.os[i].ib) : inv4(m)));
      const K = p.anim.peau.map(i => i === undefined || !o.monde[i] ? null : mul(o.monde[i], IR[i])); p.peauK = K;
      const n = P.pos.length / 3, X = P.pos, N = P.nor, W = P.poids, J = P.os;
      const out = P.out || (P.out = new Float32Array(X.length)), outN = N ? (P.outN || (P.outN = new Float32Array(N.length))) : null;
      for (let v = 0; v < n; v++) {
        const a = 3 * v, px = X[a], py = X[a + 1], pz = X[a + 2]; let x = 0, y = 0, z = 0, nx = 0, ny = 0, nz = 0;
        for (let k = 0; k < 4; k++) { const w = W[4 * v + k]; if (!w) continue; const M = K[J[4 * v + k]]; if (!M) continue;
          x += w * (M[0] * px + M[4] * py + M[8] * pz + M[12]); y += w * (M[1] * px + M[5] * py + M[9] * pz + M[13]); z += w * (M[2] * px + M[6] * py + M[10] * pz + M[14]);
          if (N) { const qx = N[a], qy = N[a + 1], qz = N[a + 2];
            nx += w * (M[0] * qx + M[4] * qy + M[8] * qz); ny += w * (M[1] * qx + M[5] * qy + M[9] * qz); nz += w * (M[2] * qx + M[6] * qy + M[10] * qz); } }
        out[a] = x; out[a + 1] = y; out[a + 2] = z;
        if (N) { const l = Math.hypot(nx, ny, nz) || 1; outN[a] = nx / l; outN[a + 1] = ny / l; outN[a + 2] = nz / l; }
      }
      gl.bindBuffer(gl.ARRAY_BUFFER, p.bp); gl.bufferData(gl.ARRAY_BUFFER, out, gl.DYNAMIC_DRAW);
      if (N && p.bnor) { gl.bindBuffer(gl.ARRAY_BUFFER, p.bnor); gl.bufferData(gl.ARRAY_BUFFER, outN, gl.DYNAMIC_DRAW); }
    }
    _boite(pos) { const mn = [1e9, 1e9, 1e9], mx = [-1e9, -1e9, -1e9];
      for (let i = 0; i < pos.length; i += 3) for (let k = 0; k < 3; k++) { mn[k] = Math.min(mn[k], pos[i + k]); mx[k] = Math.max(mx[k], pos[i + k]); } return [mn, mx]; }
    _rayon(p) { return Math.hypot(p.boite[1][0] - p.boite[0][0], p.boite[1][1] - p.boite[0][1], p.boite[1][2] - p.boite[0][2]) / 2; }
    _vis(p) { return this.isole ? this.isole.has(p) : p.visible; }
    // (24/11) pièce animée par os, au repos : son maillage tel quel (envoyé une fois, jusqu'à la prochaine image animée)
    _peauRepos(p) {
      if (p.peau._repos) return; p.peau._repos = true;
      const gl = this.gl; gl.bindBuffer(gl.ARRAY_BUFFER, p.bp); gl.bufferSubData(gl.ARRAY_BUFFER, 0, p.peau.pos0);
      gl.bindBuffer(gl.ARRAY_BUFFER, p.bn); gl.bufferSubData(gl.ARRAY_BUFFER, 0, p.peau.nor0);
    }
    recadrer(seulementVisibles) {
      // les pièces d'un effet sont posées autour de l'origine (le squelette de la cinématique les place en jeu) :
      // centre = milieu des boîtes visibles, caméra à l'extérieur de la plus grande pièce visible
      const ps = this.pieces.filter(p => (!seulementVisibles || this._vis(p)) && p.boite[0][0] < 1e8);
      if (!ps.length) return 0;
      const mn = [1e9, 1e9, 1e9], mx = [-1e9, -1e9, -1e9];
      for (const p of ps) for (let k = 0; k < 3; k++) { mn[k] = Math.min(mn[k], p.boite[0][k]); mx[k] = Math.max(mx[k], p.boite[1][k]); }
      this.centre = [(mn[0] + mx[0]) / 2, (mn[1] + mx[1]) / 2, (mn[2] + mx[2]) / 2];
      this.dist = Math.max(0.5, Math.hypot(mx[0] - mn[0], mx[1] - mn[1], mx[2] - mn[2]) * 0.85);
      return this.dist;
    }
    // cache les pièces géantes (dômes, fonds, flashs plein écran) : plus de 4 fois la taille de la pièce médiane
    cacherGeantes() {
      const ps = this.pieces.filter(p => p.boite[0][0] < 1e8); if (!ps.length) return [];
      const r = ps.map(p => this._rayon(p)).sort((a, b) => a - b), med = Math.max(r[Math.floor(r.length / 2)], 0.05);
      const cachees = [];
      for (const p of ps) if (this._rayon(p) > 4 * med) { p.visible = false; cachees.push(p.cle); }
      return cachees;
    }
    _souris() {
      let bouton = -1, x0 = 0, y0 = 0;
      this.cv.addEventListener('contextmenu', e => e.preventDefault());
      let cx0 = 0, cy0 = 0, t0 = 0;
      // (15/11/2026) OUTIL de l'Atelier (zones.js : peindre sur le modèle) : il prend le bouton gauche ; Alt + glisser tourne toujours
      this.cv.addEventListener('mousedown', e => { if (e.button === 0 && this.outil && this.outil.down(e)) { bouton = 99; return; }
        bouton = e.button; x0 = e.clientX; y0 = e.clientY; cx0 = e.clientX; cy0 = e.clientY; t0 = performance.now(); });
      window.addEventListener('mouseup', e => {
        if (bouton === 99) { bouton = -1; if (this.outil) this.outil.up(e); return; }
        // (15/11/2026) CLIC sans glisser (bouton gauche) : choisir la pièce / les particules sous la souris (_boucle)
        if (bouton === 0 && Math.hypot(e.clientX - cx0, e.clientY - cy0) < 4 && performance.now() - t0 < 600) {
          if (this.clicOutil && this.clicOutil(e)) { bouton = -1; return; }      // (15/11/2026) zones.js : choisir une pièce
          const r = this.cv.getBoundingClientRect();
          this._pick = { x: Math.floor((e.clientX - r.left) * this.cv.width / r.width), y: Math.floor((r.bottom - e.clientY) * this.cv.height / r.height), ajout: e.ctrlKey || e.shiftKey, res: [] }; }
        bouton = -1; });
      window.addEventListener('mousemove', e => {
        if (bouton === 99) { if (this.outil) this.outil.move(e); return; }
        if (bouton < 0) return; const dx = e.clientX - x0, dy = e.clientY - y0; x0 = e.clientX; y0 = e.clientY;
        if (bouton === 0) { this.yaw -= dx * 0.008; this.pitch = Math.max(-1.5, Math.min(1.5, this.pitch + dy * 0.008)); }
        else { const s = this.dist * 0.0015, cy = Math.cos(this.yaw), sy = Math.sin(this.yaw);
          this.centre[0] -= (dx * cy) * s; this.centre[2] += (dx * sy) * s; this.centre[1] += dy * s; }
      });
      this.cv.addEventListener('wheel', e => { e.preventDefault(); this.dist *= Math.exp(e.deltaY * 0.001); }, { passive: false });
    }
    // pose de chaque pièce à l'image courante (animation) : p.modele, p.animCachee
    _animer(ms) {
      const L = this.lecteur; if (!L) return null;
      if (this.joue) { const dt = this._t ? Math.min(0.1, (ms - this._t) / 1000) : 0; this.image += dt * 60 * (this.vitesse || 1);
        if (this.image >= L.duree) this.image = this.boucle ? 0 : (this.joue = false, L.duree - 1); }
      this._t = ms;
      const f = Math.floor(this.image), res = L.calculer(f);
      this._resCourant = res;
      try { this._calculerLumieres(res); } catch (e) { console.error('lumières', e); this.lumPL = []; }
      // réglages de lumière du plan (stade Raimon + fichier du plan : anim.reglages_lumiere) -> registres des shaders
      { const LP = L.d.lumiere_plans, g = LP && ((res.plan && LP[res.plan.nom]) || LP._base);
        if (g) this.lumStade = g;
        if (g) { const pw = (g.mapPointLightPow || [0.2])[0], am = g.mapAmbient || [1, 1, 1];
          this.plK = [pw * am[0], pw * am[1], pw * am[2]];
          this.reglagesJoueurs = { toon: g.pointLightToonParam, blend: (g.pointLightBlendParam || [1, 0.2, 0.5, 0.85]).concat([0]).slice(0, 4),
            rim: (g.pointLightRimParam || [2, 2]).slice(0, 2), rate: g.charaBlendRateParam }; } }
      this._peauxD3D = res.peaux || null; this._camD3D = res.camera || null;   // + caméra du jeu (mise au point de la profondeur de champ)        // matrices des os de chaque acteur : envoyées au rendu Direct3D (peau faite par le serveur)
      for (const p of this.pieces) {
        if (p.ptl) { if (!p.anim) { p.animCachee = true; continue; }
          try { this._avancerEmetteur(p, f, L); } catch (e) { console.error('particules', p.cle, e); }
          p.animCachee = !p.ptlVisible || !p.ptl.parts.length; continue; }
        if (p.terrain) { p.animCachee = res.decor === false; continue; }
        if (p.balle) { p.modele = res.balle || null; p.animCachee = !res.balle; continue; }
        if (p.peau && this.isole && this.repos && this.isole.has(p)) { p.animCachee = false; p.modele = null; this._peauRepos(p); continue; }
        if (p.peau) { const mats = res.peaux && res.peaux[p.peau.acteur]; p.animCachee = !mats; p.modele = null; if (mats) { p.peau._repos = false; this._peau(p, mats); } continue; }
        if (!p.anim) continue;
        const o = res.objets[p.anim.acteur];
        if (!o || p.anim.os === undefined) { p.animCachee = !o || !o.visible; p.modele = o ? o.racine : null; continue; }
        p.modele = mul(o.racine, o.monde[p.anim.os]);
        // (14/11/2026) PIÈCE PANNEAU PAR MATÉRIAU (LU nie.exe 0x140593632 -> 0x140598bd0) : monde de la pièce tourné vers la caméra
        if (p.panneau && res.camM && !o.ecran2D && !p.anim.peau) p.modele = Anim3D.panneau(p.modele, p.panneau, res.camM);
        if (p.anim.peau && p.peauCPU && o.sq) { p.modele = o.racine; try { this._peauEffet(p, o); } catch (e) { console.error('peau', p.cle, e); } }
        p.ecran2D = !!o.ecran2D;
        const op = p.anim.mat in o.opa ? o.opa[p.anim.mat] : (p.jeu ? p.jeu.alphaRepos : 1); p.opacite = op;
        p.jeuCol = (o.col && o.col[p.anim.mat]) || null;    // couleurs animées (G4MA 16-19)
        if (p.jeu) {   // paramètres animés (G4MA 32-35) et matrices de texture animées (G4TP) de chaque case
          const P = p.jeu.params.map(v => v.slice()); for (const [i, k, v] of (o.prm && o.prm[p.anim.mat]) || []) { if (P[i]) P[i][k] = v; }
          const SP = this.paramsShader && this.paramsShader[p.anim.acteur];   // CCustomShaderParam (valeurs prises sur les os)
          for (const [i, m, v] of (SP && SP[p.anim.mat]) || []) if (P[i]) for (let c = 0; c < 4; c++) if ((m >> c) & 1) P[i][c] = v[c];
          p.jeuP = P;
          p.jeuUV = [0, 1, 2, 3, 4, 5].map(k => { const m = (p.jeu.texproj[k] || [1, 0, 0, 0, 0, 1, 0, 0]).slice(), b = o.uvc && o.uvc[p.jeu.uvCrcs[k]];
            // G4TP -> matrice (règle retrouvée sur la table +0x88, 13/11/2026) : ligne 1 = (su, 0, -su x ou),
            // ligne 2 = (0, sv, 1 - sv + sv x ov)  (v compté depuis le bas)
            // CORRIGÉ 14/11/2026 : l'échelle de la matrice = 1 / valeur G4TP (vérifié sur 4 techniques : 0,1 <-> 10,
            // 0,5901 <-> 1,6947, 0,6 <-> 1,6667, 0,1228 <-> 8,1403 au début de chaque plan) ; un décalage non animé est
            // repris de la matrice fixe (ou = -m2 / su0, ov = (m6 - 1 + sv0) / sv0) puis recalculé avec la nouvelle échelle.
            // ROTATION (G4TP type 8, radians ; 14/11/2026) : en v retourné (w = 1 - v), p' = S R(-θ) (p - o) ; forme vue dans les
            // matrices fixes (ev63012300 : rotation finale 6,3716 = 2π + 0,0884 <-> matrice fixe à 0,0884 rad, échelle 1/2).
            // ordre échelle x rotation : LU DANS LES DONNÉES (14/11/2026) : les 22 matrices fixes du jeu à rotation et échelle non uniforme
            // ont des LIGNES orthogonales (S·R), aucune des colonnes (R·S) ; pivot au coin (0, 0) (seule forme compatible).
            if (b && (8 in b || m[1] !== 0 || m[4] !== 0)) {
              const det = m[0] * m[5] - m[1] * m[4], A0 = [m[0], -m[1], -m[4], m[5]], b0 = [m[1] + m[2], 1 - m[5] - m[6]];
              const o0 = det !== 0 ? [-(A0[3] * b0[0] - A0[1] * b0[1]) / det, -(-A0[2] * b0[0] + A0[0] * b0[1]) / det] : [0, 0];
              const su = (1 in b && b[1]) ? 1 / b[1] : Math.sqrt(m[0] * m[0] + m[1] * m[1]), sv = (2 in b && b[2]) ? 1 / b[2] : Math.sqrt(m[4] * m[4] + m[5] * m[5]);
              const th = 8 in b ? b[8] : Math.atan2(-m[1], m[0]), c = Math.cos(th), s = Math.sin(th);
              const ou = 10 in b ? b[10] : o0[0], ov = 11 in b ? b[11] : o0[1];
              const a00 = su * c, a01 = su * s, a10 = -sv * s, a11 = sv * c, bb0 = -(a00 * ou + a01 * ov), bb1 = -(a10 * ou + a11 * ov);
              m[0] = a00; m[1] = -a01; m[4] = -a10; m[5] = a11; m[2] = bb0 - m[1]; m[6] = 1 - m[5] - bb1;
            } else if (b) { const u0 = m[0], v0 = m[5];
              const su = (1 in b && b[1]) ? 1 / b[1] : u0, sv = (2 in b && b[2]) ? 1 / b[2] : v0;
              const ou = 10 in b ? b[10] : (u0 ? -m[2] / u0 : 0), ov = 11 in b ? b[11] : (v0 ? (m[6] - 1 + v0) / v0 : 0);
              if (1 in b || 10 in b) { m[0] = su; m[2] = -su * ou; }
              if (2 in b || 11 in b) { m[5] = sv; m[6] = 1 - sv + sv * ov; } }
            return m; });
        }
        p.uvx = (o.uv && p.anim.uv && o.uv[p.anim.uv]) || null;
        // (14/11/2026) aperçu WebGL : même matrice que Direct3D (échelle = 1 / valeur G4TP), rotation non montrée dans l'aperçu
        if (p.uvx && p.jeuUV && p.jeuUV[0]) { const m = p.jeuUV[0]; p.uvx = [m[0], m[5], m[2], m[6]]; }
        p.animCachee = !o.visible || o.cache[p.anim.os] || op < 0.005;
      }
      // aura du ballon en cours (APPROCHÉ) : la 2e courbe de sa définition sert de teinte -> colonne de la palette la plus proche
      this._auraActive = null;
      const IV = L.d.aura_balle || [];
      const iv = IV.find(x => f >= x.debut && f < x.fin);
      if (iv && iv.courbes && iv.courbes[1] && iv.courbes[1].length) {
        const ks = iv.courbes[1], t = (f - iv.debut) / 60; let c = ks[0].slice(1, 4);
        for (let k = 0; k + 1 < ks.length; k++) if (t >= ks[k][0]) { const a = ks[k], b = ks[k + 1], u = Math.min(1, (t - a[0]) / Math.max(1e-6, b[0] - a[0]));
          c = [1, 2, 3].map(j => a[j] * (1 - u) + b[j] * u); }
        this._auraActive = this._colonneProche(c);
      }
      // effet de statut du jeu sur le ballon : courbes 1, 2, 3 de la définition -> StatusColor, RimColor, PowInOutDis
      // CORRIGÉ 14/11/2026, LU dans nie.exe (CStatusEffComponent : 0x140f0a390 temps / fondus, 0x140f0aa40 valeurs,
      // 0x1402a44d0 courbes) : temps des courbes = temps / durée (en boucle si mode 0) ; poids w = fondu d'entrée puis 1,
      // fondu de sortie après la fin ; couleur = (c - 1) w + 1, contour = (c - (1,1,1,0)) w + (1,1,1,0), puissance = (c - 10) w + 10.
      // DÉDUIT : temps = (image - début) / 60, poids 1 si le fondu d'entrée vaut 0.
      this._statut = null;
      const ivS = iv || IV.find(x => x.sortie > 0 && x.fin < 1e6 && f >= x.fin && f < x.fin + x.sortie * 60);
      if (ivS && ivS.courbes) {
        const T = (f - ivS.debut) / 60, D = ivS.duree > 0 ? ivS.duree : 1, Ee = ivS.entree || 0, Ss = ivS.sortie || 0, boucle = ivS.boucle !== false;
        let w = 1;
        if (f >= ivS.fin) w = Ss > 0 ? 1 - ((f - ivS.fin) / 60) / Ss : 0;
        else if (Ee > 0 && T <= Ee) w = T / Ee;
        else if (!boucle) { const T2 = T - Ee, lim = D - Ee - Ss; if (T2 > lim) w = Ss > 0 ? 1 - (T2 - lim) / Ss : 0; }
        if (w > 0) {
          const tn = (boucle ? (T > D ? T % D : T) : Math.min(T, D)) / D;
          const val = ks => { if (!ks || !ks.length) return null; let i = 0; while (i < ks.length && tn >= ks[i][0]) i++;
            const g = (k, j) => (ks[k][j] === undefined ? 0 : ks[k][j]);
            if (i === 0) return [g(0, 1), g(0, 2), g(0, 3), g(0, 4)];
            if (i >= ks.length) { const k = ks.length - 1; return [g(k, 1), g(k, 2), g(k, 3), g(k, 4)]; }
            const dt = ks[i][0] - ks[i - 1][0], u = dt > 0 ? (tn - ks[i - 1][0]) / dt : 0;
            return [1, 2, 3, 4].map(j => (g(i, j) - g(i - 1, j)) * u + g(i - 1, j)); };
          const c0 = val(ivS.courbes[0]), c1 = val(ivS.courbes[1]), c2 = val(ivS.courbes[2]);
          this._statut = { acteur: ivS.acteur, col: c0 ? [0, 1, 2].map(j => (c0[j] - 1) * w + 1) : [1, 1, 1],
            rim: c1 ? [0, 1, 2].map(j => (c1[j] - 1) * w + 1) : [0, 0, 0], rim_w: c1 ? c1[3] * w : 0,
            pow: c2 ? (c2[0] - 10) * w + 10 : 1 }; } }
      if (this.surImage) this.surImage(f, res);
      if (this.isole) for (const p of this.isole) { p.animCachee = false; if (this.repos && !p.peau) { p.modele = null; p.opacite = 1; } }   // (24/11) objet seul
      return res;
    }
    _boucle() {
      const gl = this.gl, cv = this.cv;
      const dessiner = (ms) => {
        // au repos (aucune action depuis 1,5 s, rien qui joue) : 4 images par seconde au lieu de 60, l'image affichée reste
        // la même -> le processeur ne recalcule plus sans arrêt une vue qui ne bouge pas (~50 % d'un cœur avant)
        // et jamais plus de 60 images par seconde (écrans 144 Hz : l'animation du jeu est en 60 i/s)
        const pause = !this.joue && performance.now() - Vue3D.activite > 1500 ? 250 : 12;
        if (!this._unique && (ms || 0) - (this._dernier || 0) < pause
            && cv.width === cv.clientWidth && cv.height === cv.clientHeight) { requestAnimationFrame(dessiner); return; }
        this._dernier = ms || 0;
        const w = cv.clientWidth, h = cv.clientHeight;
        if (cv.width !== w || cv.height !== h) { cv.width = w; cv.height = h; }
        gl.viewport(0, 0, w, h); gl.clearColor(0, 0, 0, 0); gl.clear(gl.COLOR_BUFFER_BIT | gl.DEPTH_BUFFER_BIT);
        const res = this._animer(ms || 0);
        let mvp;
        if (res && res.camera && this.cameraJeu) {        // caméra du jeu : position, cible, roulis, champ de vision
          const c = res.camera, z = norm([c.oeil[0] - c.cible[0], c.oeil[1] - c.cible[1], c.oeil[2] - c.cible[2]]);
          let x = norm(croix([0, 1, 0], z)), y = croix(z, x);
          const cr = Math.cos(c.roulis), sr = Math.sin(c.roulis);
          const x2 = [0, 1, 2].map(k => x[k] * cr + y[k] * sr), y2 = [0, 1, 2].map(k => y[k] * cr - x[k] * sr); x = x2; y = y2;
          const vue = new Float32Array([x[0], y[0], z[0], 0, x[1], y[1], z[1], 0, x[2], y[2], z[2], 0, -dot(x, c.oeil), -dot(y, c.oeil), -dot(z, c.oeil), 1]);
          // champ de vision : la valeur du canal 31 du .g4cm est l'angle vertical ENTIER, en radians. LU dans le jeu en marche
          // (14/11/2026, Big Bang) : caméra +0x2E4 = canal 31, et la matrice de projection de la caméra (+0x1C0) a
          // m11 = 1 / tan(fov / 2) (0x1404c7090 -> 0x1402c5530). L'ancien « × 2 », déduit d'une vidéo, était faux.
          this._P = persp(c.champ, w / Math.max(h, 1), 0.05, 8000); this._V = vue; this._oeil = c.oeil;
          mvp = mul(this._P, vue);
        } else {
          const e = [this.centre[0] + this.dist * Math.cos(this.pitch) * Math.sin(this.yaw), this.centre[1] + this.dist * Math.sin(this.pitch),
            this.centre[2] + this.dist * Math.cos(this.pitch) * Math.cos(this.yaw)];
          this._P = persp(0.9, w / Math.max(h, 1), this.dist * 0.01, this.dist * 20); this._V = regard(e, this.centre); this._oeil = e;
          mvp = mul(this._P, this._V);
        }
        this._mvp = mvp;                                   // (15/11/2026) zones.js : ce qui est sous la souris
        gl.useProgram(this.prog); gl.uniformMatrix4fv(this.loc.mvp, false, mvp); gl.uniform1f(this.loc.profPack, this._passeProf ? 1 : 0);
        gl.uniform1f(this.loc.aLueur, this.lueur ? 1 : 0); gl.uniform1f(this.loc.lueurH, this.lueurH || 0); gl.uniform1f(this.loc.garderOr, this.garderOr ? 1 : 0);
        gl.enable(gl.BLEND); gl.disable(gl.CULL_FACE);
        const plStade = this._lumieresStade();
        // (15/11/2026) CHOIX AU CLIC : avant chaque pièce d'effet, le pixel cliqué est effacé en noir ; après son dessin (vrai shader,
        // vrai mélange), sa couleur = ce que la pièce y apporte (transparent = 0). Choisie : la dernière dessinée (le dessus) qui
        // apporte au moins 30 % du plus fort. Comme le lecteur natif (choisir_sous_clic). Le pixel est faux pendant UNE image.
        const pk = this._pick && !this._passeProf ? this._pick : null, pkBuf = pk ? new Uint8Array(4) : null;
        const pkCand = p => pk && p.cle && !p.cle.startsWith('stade/') && !p.terrain && !p.peau;
        const pkAvant = p => { if (!pkCand(p)) return; gl.enable(gl.SCISSOR_TEST); gl.scissor(pk.x, pk.y, 1, 1); gl.clearColor(0, 0, 0, 0); gl.clear(gl.COLOR_BUFFER_BIT); gl.disable(gl.SCISSOR_TEST); };
        const pkApres = p => { if (!pkCand(p)) return; gl.readPixels(pk.x, pk.y, 1, 1, gl.RGBA, gl.UNSIGNED_BYTE, pkBuf);
          const s = Math.max(pkBuf[0], pkBuf[1], pkBuf[2]) / 255; if (s > 0.004) pk.res.push([p.cle, s]); };
        const opaques = this.pieces.filter(p => p.opaque);
        // effets : les pièces OPAQUES du jeu (mélange désactivé dans leur état de rendu) d'abord, puis les transparentes
        const effets = this.pieces.filter(p => !p.opaque && this.lecteur && p.jeu && p.melange === 'opaque').concat(
          this.pieces.filter(p => !p.opaque && !(this.lecteur && p.jeu && p.melange === 'opaque')));
        for (const [liste, opaque] of [[opaques, true], [effets, false]]) {
        if (this._passeProf && !opaque) continue;      // passe de profondeur pour Direct3D : décor et joueurs seulement
        if (!opaque) { this._profS = null; if (this.lecteur && this.douces !== false) try { this._profScene(opaques, mvp, w, h); } catch (e) { console.error('profondeur', e); this._profS = null; } }
        if (opaque) { this._bf(gl.ONE_MINUS_SRC_ALPHA); gl.enable(gl.DEPTH_TEST); gl.depthMask(true); }
        else if (this.additif) { this._bf(gl.ONE); gl.depthMask(false); if (opaques.length && this.lecteur) gl.enable(gl.DEPTH_TEST); else gl.disable(gl.DEPTH_TEST); }
        else { this._bf(gl.ONE_MINUS_SRC_ALPHA); gl.enable(gl.DEPTH_TEST); gl.depthMask(true); }
        if (opaque && this.style) this._dessinerToon(liste.filter(p => p.peau), mvp, w, h);
        const vraiStade = opaque && this.lecteur && this.pm && this.vraiStade !== false && !this._passeProf;
        if (vraiStade && this.ombres !== false) { const cib = res && res.camera ? res.camera.cible : this.centre;
          try { this._carteOmbre(cib); } catch (e) { console.error('ombres', e); this._ombreSoleil = null; }
          gl.viewport(0, 0, w, h); gl.useProgram(this.prog); gl.uniformMatrix4fv(this.loc.mvp, false, mvp); }
        else this._ombreSoleil = null;
        if (vraiStade) this._dessinerStade(liste.filter(p => p.terrain && p.jeuStade && this._vis(p) && p.ni && !p.animCachee), mvp);
        gl.useProgram(this.prog);
        for (const p of liste) {
          if (opaque && this.style && p.peau) continue;
          if (vraiStade && p.terrain && p.jeuStade) continue;
          if (!this._vis(p) || !p.ni || (this.lecteur && p.animCachee)) continue;
          if (p.ptl && (!this.lecteur || !p.jeu)) continue;          // particules : seulement pendant l'animation
          if (this.lecteur && p.jeu && p.jeu.mode < 0) continue;
          if (this.lecteur && p.jeu && !opaque && p.melange) { let m = mvp;
            // effet 2D en pixels (traits de vitesse ega0001…) : projection orthographique sur une image de 1920 x 1080
            // (taille de référence DÉDUITE de la vidéo officielle en 1080p ; en jeu c'est la taille réelle de l'image)
            if (p.ecran2D) m = new Float32Array([2 / 1920, 0, 0, 0, 0, 2 / 1080, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1]);
            pkAvant(p); this._dessinerJeu(p, m, opaques.length > 0); pkApres(p); continue; }
          gl.uniformMatrix4fv(this.loc.modele, false, (this.lecteur && p.modele) || ID);
          gl.uniform4fv(this.loc.uvx, (this.lecteur && p.uvx) || [1, 1, 0, 0]);
          gl.bindBuffer(gl.ARRAY_BUFFER, p.bp); gl.enableVertexAttribArray(this.loc.p); gl.vertexAttribPointer(this.loc.p, 3, gl.FLOAT, false, 0, 0);
          gl.bindBuffer(gl.ARRAY_BUFFER, p.bc); gl.enableVertexAttribArray(this.loc.c); gl.vertexAttribPointer(this.loc.c, 4, gl.UNSIGNED_BYTE, true, 0, 0);
          gl.bindBuffer(gl.ARRAY_BUFFER, p.bt); gl.enableVertexAttribArray(this.loc.t); gl.vertexAttribPointer(this.loc.t, 2, gl.FLOAT, false, 0, 0);
          const pl = this.lecteur && p.terrain && p.bnor && this.loc.nrm >= 0 && plStade.n > 0;      // lumières ponctuelles sur le stade
          if (pl) { gl.bindBuffer(gl.ARRAY_BUFFER, p.bnor); gl.enableVertexAttribArray(this.loc.nrm); gl.vertexAttribPointer(this.loc.nrm, 3, gl.FLOAT, false, 0, 0); }
          else if (this.loc.nrm >= 0) gl.disableVertexAttribArray(this.loc.nrm);
          gl.uniform1f(this.loc.aPL, pl ? 1 : 0);
          if (pl) { gl.uniform1f(this.loc.nPL, plStade.n); gl.uniform4fv(this.loc.plPos, plStade.pos); gl.uniform4fv(this.loc.plCol, plStade.col); gl.uniform3fv(this.loc.plK, plStade.k); }
          const tx = p.texCle && this.textures[p.texCle];
          gl.activeTexture(gl.TEXTURE0); gl.bindTexture(gl.TEXTURE_2D, tx || null); gl.uniform1i(this.loc.tex, 0); gl.uniform1f(this.loc.aTex, tx ? 1 : 0);
          const nu = this.lecteur && p.nuage, tf = nu && this.textures[nu.forme], td = nu && this.textures[nu.detail];
          gl.uniform1f(this.loc.aNuage, tf && td ? 1 : 0);
          if (tf && td) { gl.activeTexture(gl.TEXTURE1); gl.bindTexture(gl.TEXTURE_2D, tf); gl.uniform1i(this.loc.forme, 1);
            gl.activeTexture(gl.TEXTURE2); gl.bindTexture(gl.TEXTURE_2D, td); gl.uniform1i(this.loc.detail, 2); gl.activeTexture(gl.TEXTURE0);
            gl.uniform3fv(this.loc.cOmbre, nu.ombre.slice(0, 3)); gl.uniform3fv(this.loc.cLum, nu.lum.slice(0, 3)); }
          { const k = this.facteurEclat(p);
            gl.uniform4fv(this.loc.teinte, this.lecteur && p.opacite !== undefined ? [p.teinte[0] * k, p.teinte[1] * k, p.teinte[2] * k, p.teinte[3] * p.opacite] : [p.teinte[0] * k, p.teinte[1] * k, p.teinte[2] * k, p.teinte[3]]); }
          // lecteur : mode de mélange réel du matériau (états de rendu du G4MD) ; sinon le réglage de l'aperçu
          const jeu = this.lecteur && !opaque && p.melange;
          if (jeu) this._bf(p.melange === 'add' ? gl.ONE : gl.ONE_MINUS_SRC_ALPHA);
          gl.uniform1f(this.loc.force, p.opaque || jeu ? 1.0 : this.additif ? (p.sel ? 0.9 : 0.45) : (p.sel ? 1.15 : 1.0));   // opaque : couleurs telles quelles
          const ecran = (p.surEcran || (jeu && !p.ztest)) && this.lecteur;   // collé à la caméra, ou sans test de profondeur : par-dessus le décor
          if (ecran) gl.disable(gl.DEPTH_TEST);
          pkAvant(p); gl.bindBuffer(gl.ELEMENT_ARRAY_BUFFER, p.bi); gl.drawElements(gl.TRIANGLES, p.ni, gl.UNSIGNED_SHORT, 0); pkApres(p);
          if (ecran && opaques.length) gl.enable(gl.DEPTH_TEST);
          if (jeu) this._bf(this.additif ? gl.ONE : gl.ONE_MINUS_SRC_ALPHA);
          if (p.sel && this.fil) { gl.uniform4fv(this.loc.teinte, [1, 1, 1, 1]); gl.uniform1f(this.loc.force, 0.6);
            gl.bindBuffer(gl.ELEMENT_ARRAY_BUFFER, p.bl); gl.drawElements(gl.LINES, p.nl, gl.UNSIGNED_SHORT, 0); }
        }
        }
        gl.depthMask(true);
        if (pk) { this._pick = null; let mx = 0, cle = null; for (const [, s] of pk.res) mx = Math.max(mx, s);
          for (let i = pk.res.length - 1; i >= 0; i--) if (pk.res[i][1] >= 0.3 * mx) { cle = pk.res[i][0]; break; }
          if (this.surChoix) try { this.surChoix(cle, pk.ajout); } catch (e) { console.error('choix', e); } }
        if (!this._unique) requestAnimationFrame(dessiner);
      };
      // une seule image à la demande (vérifications, captures) : vue._dessinerUne(image)
      this._dessinerUne = f => { this._unique = true; this.image = f; try { dessiner(performance.now()); } finally { this._unique = false; } };
      // profondeur pour Direct3D : passe dessinée dans une image À PART, sans lissage des bords (le lissage du canevas
      // mélangeait les valeurs codées aux contours) ; renvoie les pixels (lignes de bas en haut)
      this.pixelsProfondeur = f => {
        const w = cv.width, h = cv.height;
        if (!this._fbP || this._fbP.w !== w || this._fbP.h !== h) {
          const t = gl.createTexture(); gl.bindTexture(gl.TEXTURE_2D, t); gl.texImage2D(gl.TEXTURE_2D, 0, gl.RGBA, w, h, 0, gl.RGBA, gl.UNSIGNED_BYTE, null);
          gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MIN_FILTER, gl.NEAREST); gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MAG_FILTER, gl.NEAREST);
          gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_S, gl.CLAMP_TO_EDGE); gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_T, gl.CLAMP_TO_EDGE);
          const rb = gl.createRenderbuffer(); gl.bindRenderbuffer(gl.RENDERBUFFER, rb); gl.renderbufferStorage(gl.RENDERBUFFER, gl.DEPTH_COMPONENT16, w, h);
          const fb = gl.createFramebuffer(); gl.bindFramebuffer(gl.FRAMEBUFFER, fb);
          gl.framebufferTexture2D(gl.FRAMEBUFFER, gl.COLOR_ATTACHMENT0, gl.TEXTURE_2D, t, 0); gl.framebufferRenderbuffer(gl.FRAMEBUFFER, gl.DEPTH_ATTACHMENT, gl.RENDERBUFFER, rb);
          gl.bindFramebuffer(gl.FRAMEBUFFER, null); this._fbP = { fb, w, h };
        }
        const u = new Uint8Array(w * h * 4);
        gl.bindFramebuffer(gl.FRAMEBUFFER, this._fbP.fb); this._passeProf = true;
        try { this._dessinerUne(f); gl.readPixels(0, 0, w, h, gl.RGBA, gl.UNSIGNED_BYTE, u); }
        finally { this._passeProf = false; gl.bindFramebuffer(gl.FRAMEBUFFER, null); }
        return u;
      };
      requestAnimationFrame(dessiner);
    }
  }
  // dernière action (souris, clavier, réglage, texture ou modèle changé) : la vue redessine à pleine vitesse 1,5 s après
  Vue3D.activite = performance.now();
  for (const ev of ['pointerdown', 'pointermove', 'pointerup', 'wheel', 'keydown', 'keyup', 'input', 'change', 'resize'])
    addEventListener(ev, () => { Vue3D.activite = performance.now(); }, { capture: true, passive: true });
  window.Vue3D = Vue3D;
})();
