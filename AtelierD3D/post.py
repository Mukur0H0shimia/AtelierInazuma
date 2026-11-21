"""Effets d'écran du jeu (13/11/2026) : halo (bloom) et tone mapping, avec les shaders du jeu.

Shaders du jeu utilisés tels quels (data/dx11/shader/1.00.41) :
- bloom_sublum_composi.pfxo : seuil du halo, couleur x u_subLum.xyz - u_subLum.w ;
- bloom_gauss.pfxo : flou (8 lectures, poids u_weight1 / u_weight2) ;
- bloom_composi.pfxo : 3 flous mélangés en « écran » : 1 - produit(1 - sat(flou_i x intensité_i)) ;
- tonemap.pfxo : Reinhard (blanc fLumWhite, gris fLumGray, luminosité moyenne de l'image), joueurs exclus si
  fEnableRateForChara = 0.
Réglages : common/property/light/light_data.cfg.bin (bloomSubLumMap/Post 1,1,1,1.25 ; bloomIntensity 0.5 0.7 1.0 ;
bloomAlphaBlendRate 0.2 ; tonemapLumMax 1.25 ; tonemapLumMiddle 0.5 ; tonemapEnable 1 ; tonemapEnableChara 0).

LU DANS nie.exe (0x14132fd90, techniques Sublum / Gauss / Composite de bloom.fxbin) :
- flou : 7 lectures (centre, ±1, ±2, ±3 pas ; u_offs = (bloomTexStepSize / largeur, 0) puis (0, pas / hauteur), zw = 0),
  poids u_weight1 = exp(−x²) pour x = 0,1 / 0,3 / 0,5 / 0,7 (exp vectorielle 0x14184ebe0, vérifiée à l'émulateur) / (2 x somme),
  u_weight2 = 0 ; la réduction d'un niveau au suivant se fait PENDANT le flou horizontal (lecture de l'image du niveau d'avant) ;
- halo posé sur l'image en ONE / INV_SRC_ALPHA (pas « écran ») : couleur du halo + image x (1 − alpha du halo),
  intensités = bloomIntensity x 1,0 (réglage global +0x2A4, 1 au démarrage).
TAILLES (lues le 13/11/2026, app_config_6.00.23.00.cfg.bin) : seuil 1/2, flous 1/4, 1/8, 1/16 de l'écran.
Luminosité moyenne : comme le jeu (grille 64 x 64, moyenne arithmétique). APPROCHÉ : ordre halo puis mesure / tone mapping. Pas encore : vignettage (texture), reflets d'objectif, profondeur de champ.
"""
import os, struct, math
import d3d11 as D

REGLAGES = {'subLum': (1.0, 1.0, 1.0, 1.25), 'subLumPre': (1.0, 1.0, 1.0, 1.25), 'intensite': (0.5, 0.7, 1.0),
            'alpha': (0.2, 0.2, 0.2), 'blanc': 1.25, 'gris': 0.5, 'actif': 0.0, 'actif_joueurs': 0.0}
# Tone mapping : le shader du jeu est branché, mais COUPÉ (actif = 0 ; le jeu met tonemapEnable = 1). La luminosité
# moyenne que le moteur lui donne n'est pas encore connue (sur quelle image elle est mesurée, vitesse d'adaptation) ;
# avec une valeur approchée, l'image devenait grise et délavée, loin de la vidéo officielle (13/11/2026).

_HLSL = """
Texture2D t0 : register(t0); SamplerState s0 : register(s0);
struct V1 { float4 pos : SV_Position; float4 uv : TEXCOORD0; };
struct V2 { float4 pos : SV_Position; float4 col : COLOR0; float2 uv : TEXCOORD0; };
struct VG { float4 pos : SV_Position; float4 a : TEXCOORD0; float4 b : TEXCOORD1; float4 c : TEXCOORD2; float4 d : TEXCOORD3; };
cbuffer CB6 : register(b6) { float4 u_offs; };
float2 coin(uint id) { return float2((id << 1) & 2, id & 2); }
float4 place(float2 p) { return float4(p * float2(2, -2) + float2(-1, 1), 0, 1); }
V1 vs1(uint id : SV_VertexID) { V1 o; float2 p = coin(id); o.pos = place(p); o.uv = p.xyxy; return o; }
V2 vs2(uint id : SV_VertexID) { V2 o; float2 p = coin(id); o.pos = place(p); o.col = 1; o.uv = p; return o; }
// même calcul que le vertex shader du jeu bloom_gauss.vfxo (positions des 8 lectures)
VG vsg(uint id : SV_VertexID) { VG o; float2 p = coin(id); o.pos = place(p);
  o.a = float4(p + u_offs.zw, p - u_offs.zw); float2 r = u_offs.xy + u_offs.zw;
  o.b = float4(p + r, p - r); r += u_offs.xy; o.c = float4(p + r, p - r); r += u_offs.xy; o.d = float4(p + r, p - r); return o; }
float4 copie(V1 i) : SV_Target { return t0.Sample(s0, i.uv.xy); }
// luminance comme cs_tex_reduction.cfxo du jeu : grille 64 x 64, lecture ponctuelle du texel ((i x L) >> 6, (j x H) >> 6)
float lum(V1 i) : SV_Target { uint w, h; t0.GetDimensions(w, h); uint2 c = (uint2(i.pos.xy) * uint2(w, h)) >> 6;
  return dot(max(t0.Load(int3(c, 0)).rgb, 0), float3(0.29891, 0.58661, 0.11448)); }
// masque des joueurs pour tonemap.pfxo : bit 0 du canal bleu ; passe de profondeur de l'Atelier : alpha 0.5 = joueur
float4 masque(V1 i) : SV_Target { uint w, h; t0.GetDimensions(w, h);
  float4 c = t0.Load(int3(int(i.pos.x), int(h) - 1 - int(i.pos.y), 0)); return float4(0, 0, (c.a > 0.25 && c.a < 0.75) ? 1.0 / 255.0 : 0, 1); }
"""


def _code(nom, ext):
    from rendu_image import code_shader
    return code_shader(nom, ext)


class Post:
    def __init__(self, d, w, h):
        self.d, self.w, self.h = d, w, h
        c = lambda e, t: D.compiler(_HLSL, e, t)
        self.vs1, self.vs2, self.vsg = d.shader('vs', c('vs1', 'vs_5_0')), d.shader('vs', c('vs2', 'vs_5_0')), d.shader('vs', c('vsg', 'vs_5_0'))
        self.ps_copie, self.ps_lum, self.ps_masque = d.shader('ps', c('copie', 'ps_5_0')), d.shader('ps', c('lum', 'ps_5_0')), d.shader('ps', c('masque', 'ps_5_0'))
        # shaders du jeu
        self.ps_seuil = d.shader('ps', _code('bloom_sublum_composi', 'pfxo'))
        self.ps_flou = d.shader('ps', _code('bloom_gauss', 'pfxo'))
        self.ps_halo = d.shader('ps', _code('bloom_composi', 'pfxo'))
        self.ps_tone = d.shader('ps', _code('tonemap', 'pfxo'))
        self.lin = d.echantillonneur(3, 3, 3, 0x15)
        self.ech_point = d.echantillonneur(3, 3, 3, 0)
        self.sans = d.melange(D.BLEND_ONE, D.BLEND_ZERO, False)
        self.ecran = d.melange(D.BLEND_ONE, 6, True)       # 6 = INV_SRC_ALPHA : Composite du jeu (ONE, INV_SRC_ALPHA, ADD)
        self.prof = d.etat_profondeur(False, False)
        # TAILLES DU JEU (lues le 13/11/2026) : common/system/app_config_6.00.23.00.cfg.bin, commande 0xD82236E4 lue par
        # 0x140055550 (entrées COMMON / DX11 sur PC) ; case = nom -> numéro (table 0x141cca0c0) ; taille = (int)(écran x échelle)
        # (0x14134d2b0, même échelle pour largeur et hauteur). Halo (0x14132fd90) : seuil -> case 5 RT_Half (0,5) ;
        # flous -> cases 7 RT_Quarter (0,25), 8 RT_OneEighth (0,125), 9 RT_OneSixteenth (0,0625)
        t = lambda e: (max(1, int(w * e)), max(1, int(h * e)))
        self.seuil_wh = t(0.5); self.seuil = self._rt(*self.seuil_wh)
        self.niveaux = []
        for e in (0.25, 0.125, 0.0625):
            lw, lh = t(e)
            a, b = self._rt(lw, lh), self._rt(lw, lh)
            self.niveaux.append((lw, lh, a, b))
        self.l_tex = d.texture(64, 64, D.R32F, bind=D.BIND_SRV | D.BIND_RTV, mips=0, misc=D.MISC_GENERATE_MIPS)
        self.l_rtv, self.l_srv = d.cible(self.l_tex), d.image_shader(self.l_tex)
        self.l_1 = d.texture(1, 1, D.R32F, bind=D.BIND_SRV)
        self.lum_buf = d.tampon(struct.pack('<f', 0.5), D.BIND_SRV, taille=4, structure=4)
        self.lum_srv = d.image_shader(self.lum_buf)
        self.m_tex = d.texture(w, h, D.RGBA8, bind=D.BIND_SRV | D.BIND_RTV)
        self.m_rtv, self.m_srv = d.cible(self.m_tex), d.image_shader(self.m_tex)
        self.prof_srv = None
        # image APRÈS tone mapping (le jeu continue dessus : anticrénelage, profondeur de champ, rayons de soleil, reflets
        # d'objectif, halo, vignettage — ordre lu dans nie.exe 0x140f9c7a0 / 0x140f9bdb0). 8 bits : DÉDUIT (format non lu)
        self.ldr = d.texture(w, h, D.RGBA8, bind=D.BIND_SRV | D.BIND_RTV)
        self.ldr_rtv, self.ldr_srv = d.cible(self.ldr), d.image_shader(self.ldr)

    def _rt(self, w, h, fmt=D.RGBA16F):
        t = self.d.texture(w, h, fmt, bind=D.BIND_SRV | D.BIND_RTV)
        return (t, self.d.cible(t), self.d.image_shader(t))

    def _passe(self, rtv, w, h, vs, ps, srvs, cb6=None, cb0=None, melange=None):
        d = self.d
        d.vider_srv()
        d.sortie(rtv, None, w, h)
        d.shaders(vs, ps)
        for k, v in enumerate(srvs):
            d.srv('ps', k, v); d.ech('ps', k, self.lin)
        if cb6 is not None:
            b = d.tampon(cb6, D.BIND_CB); d.cb('vs', 6, b); d.cb('ps', 6, b)
        if cb0 is not None:
            b = d.tampon(cb0, D.BIND_CB); d.cb('ps', 0, b)
        d.etats(melange or self.sans, self.prof, None)
        d.dessiner_sans_sommets(3)

    def copier_vers(self, rtv, srv):
        self._passe(rtv, self.w, self.h, self.vs1, self.ps_copie, [srv])

    def _poids(self):
        # nie.exe 0x14132fd90 : exp(−(0,1² ; 0,3² ; 0,5² ; 0,7²)) / (2 x somme) -> centre (compté 2 fois), ±1, ±2, ±3 pas
        g = [math.exp(-x * x) for x in (0.1, 0.3, 0.5, 0.7)]
        s = 2 * sum(g)
        return [x / s for x in g]

    def appliquer(self, scene_rtv, scene_srv, sortie_rtv, profondeur_rgba=None, lum_avant=None, reglages=None, fond_srv=None,
                  apres_tonemap=None):
        """ORDRE DU JEU (LU le 14/11/2026, nie.exe 0x140f9c7a0 puis 0x140f9bdb0) :
        1. luminosité moyenne sur l'image HDR (0x141335cf0), 2. tone mapping HDR -> image finale (0x1413355f0 ; l'étalonnage
        0x141334870 ne sert que si CColorGradingManager a des étalonnages actifs), 3. sur l'image tonemappée : anticrénelage,
        flou de mouvement, profondeur de champ, rayons de soleil, reflets d'objectif (apres_tonemap(rtv, srv) : fait par
        rendu_image), 4. HALO : calculé sur l'image HDR (+0x3398, 0x14132fd90) mais POSÉ sur l'image tonemappée (ONE /
        INV_SRC_ALPHA) — avant le 14/11/2026 l'Atelier le posait avant le tone mapping, qui l'écrasait.
        reglages : réglages de lumière du plan ; fond_srv : image du décor SANS les effets (_SublumTex du jeu)."""
        moy = self.tonemap(scene_srv, self.ldr_rtv, profondeur_rgba, lum_avant, reglages)
        if apres_tonemap:
            apres_tonemap(self.ldr_rtv, self.ldr_srv)
        self.halo(scene_srv, fond_srv, self.ldr_rtv, reglages)
        self._passe(sortie_rtv, self.w, self.h, self.vs1, self.ps_copie, [self.ldr_srv])
        self.d.vider_srv()
        return moy

    def _reglages(self, reglages):
        R = dict(REGLAGES)
        g = reglages or {}
        v = lambda k, n, dft: (list(g[k]) + list(dft))[:n] if k in g else list(dft)
        if g:
            R['subLum'] = tuple(v('bloomSubLumPost', 4, R['subLum'])); R['subLumPre'] = tuple(v('bloomSubLumMap', 4, R['subLumPre']))
            R['intensite'] = tuple(v('bloomIntensity', 3, R['intensite'])); R['alpha'] = tuple(v('bloomAlphaBlendRate', 3, R['alpha']))
            R['blanc'] = v('tonemapLumMax', 1, [R['blanc']])[0]; R['gris'] = v('tonemapLumMiddle', 1, [R['gris']])[0]
            R['actif'] = v('tonemapEnable', 1, [R['actif']])[0]; R['actif_joueurs'] = v('tonemapEnableChara', 1, [R['actif_joueurs']])[0]
        return R, v

    def halo(self, scene_srv, fond_srv, cible_rtv, reglages):
        """halo du jeu (0x14132fd90) : seuil sur l'image HDR, 3 flous, posé sur cible_rtv en ONE / INV_SRC_ALPHA"""
        R, v = self._reglages(reglages)
        self._passe(self.seuil[1], *self.seuil_wh, self.vs1, self.ps_seuil, [scene_srv, fond_srv or scene_srv], cb6=struct.pack('<8f', *R['subLum'], *R['subLumPre']))
        w4 = self._poids()
        pas = list(v('bloomTexStepSize', 3, [1.0, 1.0, 1.0]))
        src = self.seuil[2]
        for k, (lw, lh, a, b) in enumerate(self.niveaux):
            for (ox, oy), de, vers in (((pas[k] / lw, 0.0), src, b), ((0.0, pas[k] / lh), b[2], a)):
                cb = struct.pack('<4f', ox, oy, 0.0, 0.0) + struct.pack('<4f', 1, 1, 1, 1) + struct.pack('<8f', *w4, 0, 0, 0, 0)
                self._passe(vers[1], lw, lh, self.vsg, self.ps_flou, [de], cb6=cb)
            src = a[2]
        I, A = R['intensite'], R['alpha']
        self._passe(cible_rtv, self.w, self.h, self.vs1, self.ps_halo, [n[2][2] for n in self.niveaux],
                    cb6=struct.pack('<8f', I[0], A[0], I[1], A[1], I[2], A[2], 0, 0), melange=self.ecran)
        self.d.vider_srv()

    def tonemap(self, scene_srv, cible_rtv, profondeur_rgba=None, lum_avant=None, reglages=None):
        """luminosité moyenne (comme le jeu) puis tone mapping du jeu : scène HDR -> cible_rtv ; renvoie la luminosité"""
        d = self.d
        R, v = self._reglages(reglages)
        scr = (v('tonemapScrLumEnable', 1, [0.0])[0], v('tonemapScrLum', 1, [1.0])[0])
        taux = v('tonemapFadeSpeed', 1, [1.0])[0] / 60.0
        self._passe(self.l_rtv, 64, 64, self.vs1, self.ps_lum, [scene_srv])
        d.vider_srv()
        d.mips(self.l_srv)
        D._meth(d.ctx, 46, None, D.c_void_p, D.c_uint, D.c_uint, D.c_uint, D.c_uint, D.c_void_p, D.c_uint, D.c_void_p)(
            d.ctx, self.l_1, 0, 0, 0, 0, self.l_tex, 6, None)
        moy = d.lire_float(self.l_1)
        if lum_avant is not None:
            moy = lum_avant + (moy - lum_avant) * taux
        d.maj(self.lum_buf, struct.pack('<f', moy))
        if profondeur_rgba:
            if self.prof_srv is None:
                self.prof_tex = d.texture(self.w, self.h, D.RGBA8, bind=D.BIND_SRV)
                self.prof_srv = d.image_shader(self.prof_tex)
            d.maj(self.prof_tex, profondeur_rgba, self.w * 4)
            self._passe(self.m_rtv, self.w, self.h, self.vs1, self.ps_masque, [self.prof_srv])
        cb0 = struct.pack('<8f', R['blanc'], R['gris'], R['actif'], R['actif_joueurs'], scr[0], scr[1], 0, 0)
        d.vider_srv()
        d.sortie(cible_rtv, None, self.w, self.h)
        d.shaders(self.vs2, self.ps_tone)
        d.srv('ps', 0, scene_srv); d.ech('ps', 0, self.lin)
        d.srv('ps', 1, self.m_srv); d.ech('ps', 1, self.ech_point)
        d.srv('ps', 2, self.lum_srv)
        b = d.tampon(cb0, D.BIND_CB); d.cb('ps', 0, b)
        d.etats(self.sans, self.prof, None)
        d.dessiner_sans_sommets(3)
        d.vider_srv()
        return moy

    def appliquer_ancien(self, scene_rtv, scene_srv, sortie_rtv, profondeur_rgba=None, lum_avant=None, reglages=None, fond_srv=None):
        """ANCIEN ORDRE (avant le 14/11/2026, gardé pour comparer) : halo posé sur l'image HDR, puis tone mapping."""
        d, R = self.d, dict(REGLAGES)
        g = reglages or {}
        v = lambda k, n, dft: (list(g[k]) + list(dft))[:n] if k in g else list(dft)
        if g:
            R['subLum'] = tuple(v('bloomSubLumPost', 4, R['subLum'])); R['subLumPre'] = tuple(v('bloomSubLumMap', 4, R['subLumPre']))
            R['intensite'] = tuple(v('bloomIntensity', 3, R['intensite'])); R['alpha'] = tuple(v('bloomAlphaBlendRate', 3, R['alpha']))
            R['blanc'] = v('tonemapLumMax', 1, [R['blanc']])[0]; R['gris'] = v('tonemapLumMiddle', 1, [R['gris']])[0]
            R['actif'] = v('tonemapEnable', 1, [R['actif']])[0]; R['actif_joueurs'] = v('tonemapEnableChara', 1, [R['actif_joueurs']])[0]
        scr = (v('tonemapScrLumEnable', 1, [0.0])[0], v('tonemapScrLum', 1, [1.0])[0])
        taux = v('tonemapFadeSpeed', 1, [1.0])[0] / 60.0      # u_rate = dt x tonemapFadeSpeed (0x140f7d450 -> CLightData +0xA98)
        # 1. seuil (bloom_sublum_composi du jeu) dans RT_Half (moitié de l'écran)
        self._passe(self.seuil[1], *self.seuil_wh, self.vs1, self.ps_seuil, [scene_srv, fond_srv or scene_srv], cb6=struct.pack('<8f', *R['subLum'], *R['subLumPre']))
        w4 = self._poids()
        pas = list(v('bloomTexStepSize', 3, [1.0, 1.0, 1.0]))
        src = self.seuil[2]                                 # niveau 0 : réduit l'image seuillée (1/2 -> 1/4) pendant le flou horizontal
        for k, (lw, lh, a, b) in enumerate(self.niveaux):
            # flou horizontal : lit le niveau d'avant (réduction incluse) -> b ; vertical : b -> a (bloom_gauss du jeu)
            for (ox, oy), de, vers in (((pas[k] / lw, 0.0), src, b), ((0.0, pas[k] / lh), b[2], a)):
                cb = struct.pack('<4f', ox, oy, 0.0, 0.0) + struct.pack('<4f', 1, 1, 1, 1) + struct.pack('<8f', *w4, 0, 0, 0, 0)
                self._passe(vers[1], lw, lh, self.vsg, self.ps_flou, [de], cb6=cb)
            src = a[2]
        # 2. halo posé sur la scène : bloom_composi du jeu, mélange ONE / INV_SRC_ALPHA
        I, A = R['intensite'], R['alpha']
        self._passe(scene_rtv, self.w, self.h, self.vs1, self.ps_halo, [n[2][2] for n in self.niveaux],
                    cb6=struct.pack('<8f', I[0], A[0], I[1], A[1], I[2], A[2], 0, 0), melange=self.ecran)
        # 3. luminosité moyenne COMME LE JEU (lu dans nie.exe 0x141335cf0) : cs_tex_reduction lancé en 8 x 8 groupes de 8 x 8,
        # u_param = (8, 8, largeur, hauteur) de l'image de la scène (+0x3398, celle que lit le tone mapping) -> 64 x 64
        # lectures ; puis moyenne arithmétique (cs_buffer_reduction : groupes de 64 x 1/64). Ici : image 64 x 64 + mips
        # (moyenne 2 x 2 exacte jusqu'au niveau 6 = 1 x 1 ; seul l'ordre des additions diffère)
        self._passe(self.l_rtv, 64, 64, self.vs1, self.ps_lum, [scene_srv])
        d.vider_srv()
        d.mips(self.l_srv)
        D._meth(d.ctx, 46, None, D.c_void_p, D.c_uint, D.c_uint, D.c_uint, D.c_uint, D.c_void_p, D.c_uint, D.c_void_p)(
            d.ctx, self.l_1, 0, 0, 0, 0, self.l_tex, 6, None)          # dernier niveau (1 x 1) : 7e niveau de 64
        moy = d.lire_float(self.l_1)
        # adaptation dans le temps (cs_buffer_lerp du jeu : adaptée += taux x (mesure - adaptée)) ; lum_avant = valeur
        # adaptée à l'image précédente, calculée par la page sur les images d'avant (APPROCHÉ : taux 1/60 par image)
        if lum_avant is not None:
            moy = lum_avant + (moy - lum_avant) * taux
        d.maj(self.lum_buf, struct.pack('<f', moy))
        # 4. masque des joueurs (exclus du tone mapping, comme dans le jeu)
        if profondeur_rgba:
            if self.prof_srv is None:
                self.prof_tex = d.texture(self.w, self.h, D.RGBA8, bind=D.BIND_SRV)
                self.prof_srv = d.image_shader(self.prof_tex)
            d.maj(self.prof_tex, profondeur_rgba, self.w * 4)
            self._passe(self.m_rtv, self.w, self.h, self.vs1, self.ps_masque, [self.prof_srv])
        # 5. tone mapping (tonemap du jeu) -> sortie
        cb0 = struct.pack('<8f', R['blanc'], R['gris'], R['actif'], R['actif_joueurs'], scr[0], scr[1], 0, 0)
        d.vider_srv()
        d.sortie(sortie_rtv, None, self.w, self.h)
        d.shaders(self.vs2, self.ps_tone)
        d.srv('ps', 0, scene_srv); d.ech('ps', 0, self.lin)
        d.srv('ps', 1, self.m_srv); d.ech('ps', 1, self.ech_point)
        d.srv('ps', 2, self.lum_srv)
        b = d.tampon(cb0, D.BIND_CB); d.cb('ps', 0, b)
        d.etats(self.sans, self.prof, None)
        d.dessiner_sans_sommets(3)
        d.vider_srv()
        return moy
