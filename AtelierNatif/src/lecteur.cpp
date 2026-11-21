// LECTEUR NATIF de l'Atelier Inazuma (14/11/2026) — C++ / Direct3D 11, avec les VRAIS shaders du jeu.
//
// Dessine EN DIRECT (à la fréquence de l'écran), comme le jeu, une scène exportée par AtelierNatif/exporter.py :
//   scene.bin  : décor du stade — shaders DXBC du jeu, entrées, tampons (noms + décalages), géométrie, textures, matériaux,
//                réglages de lumière (CLightData + brouillard converti + réglages des passes d'écran), cubemap ;
//   effets.bin : ressources des effets de la technique, programmes des passes d'écran du jeu, modèles des personnages ;
//   images.bin : image par image, ce que l'animation de l'Atelier a calculé (caméra, effets, personnages, ombres…).
// Chaque passe reprend EXACTEMENT AtelierD3D/rendu_image.py et post.py (mêmes shaders, mêmes valeurs, même ordre).
//
// Ordre d'une image : profondeur du stade et des personnages -> cartes d'ombre (3 cascades) + shadow_ss -> couleur (4 images)
// -> SSAO + ombre des pieds -> 2e passe couleur -> ciel -> contours -> effets des couches < 25 -> tone mapping -> TAA ->
// profondeur de champ -> effets des couches 25-49 (40_Effect, LU) -> halo -> couches 55-63 (ordre du jeu, LU 14/11/2026).
// Touches : Espace = pause, flèches = image par image, Début = recommencer, E = effets d'écran oui / non, Échap = quitter.
#define WIN32_LEAN_AND_MEAN
#define NOMINMAX
#define _CRT_SECURE_NO_WARNINGS
#include <windows.h>
#include <shellapi.h>
#include <d3d11.h>
#include <d3dcompiler.h>
#include <cstdio>
#include <cstdint>
#include <cmath>
#include <cstring>
#include <string>
#include <vector>
#include <map>
#include <unordered_map>
#include <chrono>
#include <algorithm>
#include <array>

#pragma comment(lib, "d3d11.lib")
#pragma comment(lib, "d3dcompiler.lib")
#pragma comment(lib, "user32.lib")
#pragma comment(lib, "gdi32.lib")

typedef std::vector<uint8_t> Octets;

// ------------------------------------------------------------------ lecture du fichier
struct Lecteur {
    Octets d; size_t p = 0;
    bool ouvrir(const std::wstring& f) {
        FILE* x = _wfopen(f.c_str(), L"rb"); if (!x) return false;
        fseek(x, 0, SEEK_END); long long n = _ftelli64(x); fseek(x, 0, SEEK_SET);
        d.resize((size_t)n); fread(d.data(), 1, (size_t)n, x); fclose(x); return true;
    }
    uint32_t u32() { uint32_t v; memcpy(&v, &d[p], 4); p += 4; return v; }
    int32_t i32() { int32_t v; memcpy(&v, &d[p], 4); p += 4; return v; }
    float f32() { float v; memcpy(&v, &d[p], 4); p += 4; return v; }
    double f64() { double v; memcpy(&v, &d[p], 8); p += 8; return v; }
    void f32s(float* o, size_t n) { if (n) memcpy(o, &d[p], 4 * n); p += 4 * n; }
    void f64s(double* o, size_t n) { if (n) memcpy(o, &d[p], 8 * n); p += 8 * n; }
    std::vector<float> vf(size_t n) { std::vector<float> v(n); f32s(v.data(), n); return v; }
    Octets octets() { uint32_t n = u32(); Octets o(d.begin() + p, d.begin() + p + n); p += n + ((4 - n % 4) % 4); return o; }
    std::string texte() { Octets o = octets(); return std::string(o.begin(), o.end()); }
};

// ------------------------------------------------------------------ matrices (tableaux WebGL, colonne par colonne)
static const double GL_VERS_D3D[16] = {1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0.5, 0, 0, 0, 0.5, 1};
static const double ID[16] = {1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1};
static void mul(const double* a, const double* b, double* o) {
    double r[16];
    for (int c = 0; c < 4; c++) for (int l = 0; l < 4; l++)
        r[c * 4 + l] = a[l] * b[c * 4] + a[4 + l] * b[c * 4 + 1] + a[8 + l] * b[c * 4 + 2] + a[12 + l] * b[c * 4 + 3];
    memcpy(o, r, sizeof r);
}
static bool inv4(const double* m, double* o) {
    double inv[16];
    inv[0] = m[5]*m[10]*m[15]-m[5]*m[11]*m[14]-m[9]*m[6]*m[15]+m[9]*m[7]*m[14]+m[13]*m[6]*m[11]-m[13]*m[7]*m[10];
    inv[4] = -m[4]*m[10]*m[15]+m[4]*m[11]*m[14]+m[8]*m[6]*m[15]-m[8]*m[7]*m[14]-m[12]*m[6]*m[11]+m[12]*m[7]*m[10];
    inv[8] = m[4]*m[9]*m[15]-m[4]*m[11]*m[13]-m[8]*m[5]*m[15]+m[8]*m[7]*m[13]+m[12]*m[5]*m[11]-m[12]*m[7]*m[9];
    inv[12] = -m[4]*m[9]*m[14]+m[4]*m[10]*m[13]+m[8]*m[5]*m[14]-m[8]*m[6]*m[13]-m[12]*m[5]*m[10]+m[12]*m[6]*m[9];
    inv[1] = -m[1]*m[10]*m[15]+m[1]*m[11]*m[14]+m[9]*m[2]*m[15]-m[9]*m[3]*m[14]-m[13]*m[2]*m[11]+m[13]*m[3]*m[10];
    inv[5] = m[0]*m[10]*m[15]-m[0]*m[11]*m[14]-m[8]*m[2]*m[15]+m[8]*m[3]*m[14]+m[12]*m[2]*m[11]-m[12]*m[3]*m[10];
    inv[9] = -m[0]*m[9]*m[15]+m[0]*m[11]*m[13]+m[8]*m[1]*m[15]-m[8]*m[3]*m[13]-m[12]*m[1]*m[11]+m[12]*m[3]*m[9];
    inv[13] = m[0]*m[9]*m[14]-m[0]*m[10]*m[13]-m[8]*m[1]*m[14]+m[8]*m[2]*m[13]+m[12]*m[1]*m[10]-m[12]*m[2]*m[9];
    inv[2] = m[1]*m[6]*m[15]-m[1]*m[7]*m[14]-m[5]*m[2]*m[15]+m[5]*m[3]*m[14]+m[13]*m[2]*m[7]-m[13]*m[3]*m[6];
    inv[6] = -m[0]*m[6]*m[15]+m[0]*m[7]*m[14]+m[4]*m[2]*m[15]-m[4]*m[3]*m[14]-m[12]*m[2]*m[7]+m[12]*m[3]*m[6];
    inv[10] = m[0]*m[5]*m[15]-m[0]*m[7]*m[13]-m[4]*m[1]*m[15]+m[4]*m[3]*m[13]+m[12]*m[1]*m[7]-m[12]*m[3]*m[5];
    inv[14] = -m[0]*m[5]*m[14]+m[0]*m[6]*m[13]+m[4]*m[1]*m[14]-m[4]*m[2]*m[13]-m[12]*m[1]*m[6]+m[12]*m[2]*m[5];
    inv[3] = -m[1]*m[6]*m[11]+m[1]*m[7]*m[10]+m[5]*m[2]*m[11]-m[5]*m[3]*m[10]-m[9]*m[2]*m[7]+m[9]*m[3]*m[6];
    inv[7] = m[0]*m[6]*m[11]-m[0]*m[7]*m[10]-m[4]*m[2]*m[11]+m[4]*m[3]*m[10]+m[8]*m[2]*m[7]-m[8]*m[3]*m[6];
    inv[11] = -m[0]*m[5]*m[11]+m[0]*m[7]*m[9]+m[4]*m[1]*m[11]-m[4]*m[3]*m[9]-m[8]*m[1]*m[7]+m[8]*m[3]*m[5];
    inv[15] = m[0]*m[5]*m[10]-m[0]*m[6]*m[9]-m[4]*m[1]*m[10]+m[4]*m[2]*m[9]+m[8]*m[1]*m[6]-m[8]*m[2]*m[5];
    double det = m[0]*inv[0]+m[1]*inv[4]+m[2]*inv[8]+m[3]*inv[12];
    if (det == 0) { for (int i = 0; i < 16; i++) o[i] = 0; return false; }   // (comme rendu_image : zéros)
    for (int i = 0; i < 16; i++) o[i] = inv[i] / det;
    return true;
}
static void lignes(const double* m, float* o) { for (int r = 0; r < 4; r++) for (int c = 0; c < 4; c++) o[r * 4 + c] = (float)m[c * 4 + r]; }

// ------------------------------------------------------------------ ressources (décor ou effets : même format)
struct Var { uint32_t nom, off, taille; };
struct DefCb { uint32_t nom, slot, taille; std::vector<Var> vars; };
struct Prog {
    uint32_t vs, ps, gs, vs_tex, t11; std::vector<D3D11_INPUT_ELEMENT_DESC> el; std::vector<std::string> sem;
    std::vector<DefCb> etapes[3];                  // VS, PS, GS (geometry shader du jeu : FakeParticle)
    ID3D11VertexShader* vso = nullptr; ID3D11PixelShader* pso = nullptr; ID3D11GeometryShader* gso = nullptr; ID3D11InputLayout* disp = nullptr;
    int slotPL = -1, slotCube = -1;
};
struct Geo { std::vector<ID3D11Buffer*> vb; std::vector<UINT> pas; ID3D11Buffer* ib = nullptr; UINT n = 0;
             std::vector<std::vector<uint8_t>> cpu;      // (14/11/2026) copie des flux de 4 octets (couleurs) pour les teintes de l'Atelier
             bool teinte = false; double tH = 0, tC = 0; }; // (15/11/2026) teinte posée sur le flux COLOR (pour la retirer en direct)

enum VarId { V_AUTRE = -1, V_LW, V_LV, V_LP, V_LWOLD, V_LVOLD, V_UB, V_DIFF, V_AMB, V_SPEC, V_ATTACH, V_GRD, V_TEXPROJ, V_UVRANGE,
             V_SP0, V_SP1, V_SP2, V_SP3, V_SP4, V_SP5, V_SP6, V_SP7,
             V_VP, V_EYEVP, V_WV, V_WP, V_EYEWV, V_EYEWP, V_NFIA, V_EYEPV, V_EYEPOS, V_EYEDIR, V_EYEUP, V_VW, V_EYEVW, V_PV, V_PW, V_EYEPW,
             V_WVOLD, V_VPOLD, V_WPOLD, V_BONE,
             V_SKIN, V_HAIR, V_SUB1, V_SUB2, V_PLH0, V_PLH1, V_STCOL, V_STRIM, V_STPOW, V_LIGHTWP, V_CASCMM, V_SHSAMP, V_EYESPH, V_NB };
static const char* NOMS_VAR[] = {"u_mtxLW", "u_mtxLV", "u_mtxLP", "u_mtxLWOld", "u_mtxLVOld", "u_ubParam", "u_diffuse", "u_ambient",
    "u_speculer", "u_attachScale", "u_grdValue", "u_texProj", "u_uvRange", "u_shaderParam0", "u_shaderParam1", "u_shaderParam2",
    "u_shaderParam3", "u_shaderParam4", "u_shaderParam5", "u_shaderParam6", "u_shaderParam7", "u_mtxVP", "u_eyeMtxVP", "u_mtxWV",
    "u_mtxWP", "u_eyeMtxWV", "u_eyeMtxWP", "u_eyeNearFarInvAspect", "u_eyeMtxPV", "u_eyePos", "u_eyeDir", "u_eyeUpDir", "u_mtxVW",
    "u_eyeMtxVW", "u_mtxPV", "u_mtxPW", "u_eyeMtxPW", "u_mtxWVOld", "u_mtxVPOld", "u_mtxWPOld", "u_mtxBone",
    "u_skinColor", "u_hairColor", "u_subColor1", "u_subColor2", "u_pointLightHeader0", "u_pointLightHeader1", "u_charaStatusColor",
    "u_charaStatusRimColor", "u_charaStatusPowInOutDis", "u_mtxLightWP", "u_shadowCascadeMinMax", "u_shadowSampleParams", "u_mtxEyeSphere"};
static const char* BROUILLARD[] = {"u_RayleighColorP20", "u_RayleighColorP10", "u_RayleighColorO00", "u_RayleighColorM10",
    "u_RayleighColorM20", "u_HeightRayleighColor", "u_MieColorP20", "u_MieColorO00", "u_MieColorM20", "u_fogWorldParam0",
    "u_fogWorldParam1", "u_fogHeightParam0", "u_fogHeightParam1", "u_RayleighBandRatio"};

struct Base {
    std::vector<std::string> noms; std::vector<int> varDe; std::vector<char> estBrouillard;
    uint32_t nomCam = UINT32_MAX, nomLum = UINT32_MAX, nomChara = UINT32_MAX, nomMat = UINT32_MAX, nomPL = UINT32_MAX, nomCube = UINT32_MAX;
    std::vector<Octets> shaders; std::vector<Prog> progs; std::vector<ID3D11ShaderResourceView*> tex; std::vector<Geo> geos;
};

struct Dessin {      // décor (passe 0 profondeur, 1 couleur, 2 cartes d'ombre)
    uint32_t passe, prog, geo; int32_t tex[6]; uint32_t adr[6][2]; uint32_t faces, a_inst; int32_t lod; float lod_r;
    float params[32], diffuse[4], ambient[4], uv[48], ub[4]; double inst[16];
};
struct Element { uint32_t prog; int32_t geo; int32_t tex[6]; uint32_t adr[6][2]; uint32_t melange, part, seuil = 256; };
struct DessinEffet {
    uint32_t elem, flags; double mvp[16], modele[16], V[16], P[16]; float params[32], diffuse[4], ambient[4], uv[48], grd;
    std::vector<double> os; Geo geoP;
    int src = -1, srcE = -1;                 // (15/11/2026) n° de la pièce / de l'émetteur de la technique (caché, couleurs : au dessin)
    // particules : sommets de l'image (avant la carte graphique ; gardés pour les vérifications)
    uint32_t bNv = 0; std::vector<float> bPos, bCol, bUv[3], bNor, bTan; std::vector<uint16_t> bIdx; bool bANor = false, bATan = false;
};
// réglages des passes d'écran résolus par l'exporteur (reglages_resolus) : indices
enum { R_SUBLUM = 0, R_SUBLUMPRE = 4, R_INT = 8, R_ALPHA = 11, R_BLANC = 14, R_GRIS, R_ACTIF, R_ACTIFJ, R_SCR0, R_SCR1, R_TAUX, R_PAS = 21,
       R_SSAO = 24, R_PIEDS = 41, R_CIEL = 42, R_CIELR, R_DOF = 44, R_DOFCNT, R_NZ, R_FZ, R_FIN, R_FOUT, R_FRONT, R_BACK, R_GP0, R_GP1, R_TEXOFF, R_AUTO, R_SCAT };
struct Lum { Octets img, brouillard; float rg[64]; };
struct LumPonct { float v[7]; uint32_t masque; };
struct PieceA {      // pièce d'un personnage (acteurs.Acteur)
    uint32_t noir; int32_t prog, prog_st; uint32_t nv, faces;
    std::vector<float> pos, nor, tan; std::vector<uint32_t> os; std::vector<double> poids;
    int32_t tex[6]; uint32_t adr[6][2]; float params[32], diffuse[4], ambient[4], uv[48];
    ID3D11Buffer *vbPos = nullptr, *vbNor = nullptr, *vbTan = nullptr, *vbCol = nullptr, *vbZero = nullptr, *ib = nullptr;
    ID3D11Buffer* vbUv[6] = {}; UINT n = 0;
    // (14/11/2026) sommets après la peau : un jeu de tampons PAR PERSONNAGE de l'image (avant : un seul par modèle, donc
    // plusieurs joueurs du même modèle — les 3 joueurs de Big Bang — se retrouvaient tous à la place du dernier)
    std::vector<std::array<ID3D11Buffer*, 3>> inst;
};
struct ActeurImage { uint32_t modele; std::vector<uint32_t> pieces; std::vector<double> mats; uint32_t statut; float st[12]; float alpha = 1.0f; };
struct Ombres { uint32_t present = 0, T = 1024; double vp[3][16], tr[3][2], dir[3], biais[3]; };
struct Image {
    double V[16], P[16]; uint32_t lum, decor; std::vector<LumPonct> lumieres; std::vector<DessinEffet> effets;
    Ombres om; std::vector<ActeurImage> acteurs; std::vector<double> pieds; double foyer = 10;
};
struct PsSeul { ID3D11PixelShader* ps = nullptr; std::vector<DefCb> cbs; };
struct Cible { ID3D11Texture2D* t = nullptr; ID3D11RenderTargetView* rtv = nullptr; ID3D11ShaderResourceView* srv = nullptr; int w = 0, h = 0; };

struct Valeur { std::vector<float> v; bool ok = false; };

enum { SP_SSAO, SP_PIEDS, SP_CIEL, SP_EDGE, SP_TONE, SP_COMPOSI, SP_GAUSS, SP_DOF, SP_DEPTH, SP_SCDEP, SP_SCAT, SP_SCUP, SP_SNRM, SP_BILAT, SP_TDEP, SP_TUP, SP_NB };
enum { PS_SS, PS_SEUIL, PS_FLOU, PS_HALO, PS_TONEMAP, PS_TAA, PS_TAA1, PS_NB };

struct App {
    HWND fen = nullptr; int W = 1280, H = 720, Wf = 0, Hf = 0;     // W, H : image calculée ; Wf, Hf : fenêtre (incrustée)
    ID3D11Device* dev = nullptr; ID3D11DeviceContext* ctx = nullptr; IDXGISwapChain* sc = nullptr;
    ID3D11RenderTargetView* rtvEcran = nullptr;
    Cible hdr, copie, copieDemi, fond, mrt[3], t13, t13b, snrm, temp[2], dofMi[2], seuil, niv[3][2], ldr, masque, lumC, taaSortie, taaHist; bool taaOk = false;
    ID3D11Texture2D* prof = nullptr; ID3D11DepthStencilView* dsv = nullptr;
    ID3D11Texture2D* profCopieTex = nullptr; ID3D11ShaderResourceView* profScene = nullptr;
    ID3D11Texture2D* csmTex = nullptr; ID3D11DepthStencilView* csmDsv[3] = {}; ID3D11ShaderResourceView* csmSrv = nullptr; uint32_t csmT = 0;
    ID3D11Texture2D* csm0Tex = nullptr; ID3D11ShaderResourceView* csm0Srv = nullptr; double csm0vp[16];   // ombre des effets (t15)
    ID3D11Buffer* lumBuf = nullptr; ID3D11ShaderResourceView* lumSrv = nullptr; ID3D11UnorderedAccessView* lumUav = nullptr;
    ID3D11ComputeShader* csAdapt = nullptr; ID3D11ShaderResourceView* lumMip6 = nullptr;
    Base decor, eff;
    std::vector<Dessin> dessins; std::vector<Element> elems; std::vector<Lum> lums; std::vector<Image> images;
    std::vector<std::vector<PieceA>> modeles;
    int speciaux[SP_NB] = {}; PsSeul psSeuls[PS_NB]; int texSys[2] = {-1, -1};
    ID3D11BlendState* melFondu = nullptr;           // (15/11/2026) personnages en fondu
    ID3D11ShaderResourceView *blanc = nullptr, *noir = nullptr, *cube = nullptr, *t17 = nullptr, *t18 = nullptr;
    ID3D11Buffer *cb9 = nullptr, *cb8 = nullptr; Octets cb8Octets;
    std::unordered_map<uint64_t, ID3D11SamplerState*> ech;
    ID3D11SamplerState* s15 = nullptr;
    std::unordered_map<uint64_t, ID3D11Buffer*> cbPool;
    ID3D11BlendState* mel[5] = {};                   // 0 opaque, 1 profondeur, 2 alpha, 3 additif, 4 soustractif
    ID3D11BlendState *melMasqueA = nullptr, *melMasque0 = nullptr, *melTaa = nullptr, *melR_A = nullptr, *melG = nullptr, *melGAdd = nullptr, *melRGB = nullptr, *melMul = nullptr, *melEcran = nullptr, *melDof = nullptr;
    std::unordered_map<int, ID3D11DepthStencilState*> ds;
    ID3D11RasterizerState *rasDouble = nullptr, *rasArriere = nullptr;
    // shaders de l'Atelier (AtelierD3D : _HLSL_SS, post._HLSL) et du lecteur (mannequin noir, masque des joueurs)
    ID3D11VertexShader *vsSS = nullptr, *vs1 = nullptr, *vs2 = nullptr, *vsg = nullptr, *vsNoir = nullptr;
    ID3D11PixelShader *psCopie = nullptr, *psCopieBrut = nullptr, *psCopieV2 = nullptr, *psLum = nullptr, *psNoir = nullptr, *psMasque = nullptr, *psBan = nullptr;
    ID3D11VertexShader* vsBan = nullptr; ID3D11ShaderResourceView* telSrv = nullptr; int telW = 0, telH = 0;     // bannière
    ID3D11InputLayout* dispNoir = nullptr;
    ID3D11VertexShader* vsNoirSt = nullptr; ID3D11PixelShader* psNoirSt = nullptr; ID3D11InputLayout* dispNoirSt = nullptr;   // mannequin + aura
    ID3D11Buffer *quadPos = nullptr, *quadUv = nullptr, *quadCol = nullptr, *quadIb = nullptr, *cubeVb = nullptr, *cubeIb = nullptr;
    Valeur val[V_NB];
    double mvp[16], V[16];
    bool effetsEcran = true, premiere = true;
};
static App A;

static bool silencieux = false;      // mode capture (essais) : erreurs dans lecteur_erreur.txt, sans fenêtre
static void echec(const char* quoi, HRESULT hr) {
    char m[512]; sprintf_s(m, "%s : échec 0x%08x", quoi, (unsigned)hr);
    FILE* x = fopen("lecteur_erreur.txt", "a"); if (x) { fprintf(x, "%s\n", m); fclose(x); }
    if (!silencieux) MessageBoxA(nullptr, m, "Lecteur natif", MB_ICONERROR);
    ExitProcess(1);
}
#define OK(x, q) do { HRESULT _h = (x); if (FAILED(_h)) echec(q, _h); } while (0)

static ID3D11ShaderResourceView* texture_rgba(int w, int h, const uint8_t* px, bool mips, uint32_t niveaux = 0) {
    D3D11_TEXTURE2D_DESC d = {}; d.Width = w; d.Height = h; d.MipLevels = mips ? niveaux : 1; d.ArraySize = 1; d.Format = DXGI_FORMAT_R8G8B8A8_UNORM;
    d.SampleDesc.Count = 1; d.Usage = D3D11_USAGE_DEFAULT; d.BindFlags = D3D11_BIND_SHADER_RESOURCE | (mips ? D3D11_BIND_RENDER_TARGET : 0);
    d.MiscFlags = mips ? D3D11_RESOURCE_MISC_GENERATE_MIPS : 0;
    ID3D11Texture2D* t; ID3D11ShaderResourceView* v;
    if (mips) {
        OK(A.dev->CreateTexture2D(&d, nullptr, &t), "CreateTexture2D");
        A.ctx->UpdateSubresource(t, 0, nullptr, px, w * 4, 0);
        OK(A.dev->CreateShaderResourceView(t, nullptr, &v), "CreateSRV");
        A.ctx->GenerateMips(v);
    } else {
        D3D11_SUBRESOURCE_DATA s = {px, (UINT)w * 4, 0};
        OK(A.dev->CreateTexture2D(&d, &s, &t), "CreateTexture2D");
        OK(A.dev->CreateShaderResourceView(t, nullptr, &v), "CreateSRV");
    }
    return v;
}
static Cible cible(int w, int h, DXGI_FORMAT f) {
    Cible c; c.w = w; c.h = h;
    D3D11_TEXTURE2D_DESC d = {(UINT)w, (UINT)h, 1, 1, f, {1, 0}, D3D11_USAGE_DEFAULT, D3D11_BIND_RENDER_TARGET | D3D11_BIND_SHADER_RESOURCE, 0, 0};
    OK(A.dev->CreateTexture2D(&d, nullptr, &c.t), "cible");
    OK(A.dev->CreateRenderTargetView(c.t, nullptr, &c.rtv), "cible rtv"); OK(A.dev->CreateShaderResourceView(c.t, nullptr, &c.srv), "cible srv");
    return c;
}

// échantillonneurs : filtre 0x15 (linéaire) ou 0 (point), comme Rendu.ech / ech_point
static ID3D11SamplerState* echantillonneur(uint32_t u, uint32_t v, uint32_t w = 1, uint32_t filtre = 0x15) {
    uint64_t k = ((uint64_t)filtre << 32) | ((uint64_t)u << 16) | ((uint64_t)v << 8) | w;
    auto it = A.ech.find(k); if (it != A.ech.end()) return it->second;
    D3D11_SAMPLER_DESC d = {}; d.Filter = (D3D11_FILTER)filtre; d.AddressU = (D3D11_TEXTURE_ADDRESS_MODE)u; d.AddressV = (D3D11_TEXTURE_ADDRESS_MODE)v;
    d.AddressW = (D3D11_TEXTURE_ADDRESS_MODE)w; d.MaxAnisotropy = 1; d.ComparisonFunc = D3D11_COMPARISON_ALWAYS; d.MinLOD = 0; d.MaxLOD = 3.4e38f;
    ID3D11SamplerState* s; OK(A.dev->CreateSamplerState(&d, &s), "CreateSamplerState");
    A.ech[k] = s; return s;
}
static ID3D11SamplerState* ech_point(uint32_t u, uint32_t v) { return echantillonneur(u, v, 3, 0); }

static ID3D11Buffer* tampon(const void* data, size_t n, UINT bind) {
    if (!n) return nullptr;
    D3D11_BUFFER_DESC d = {(UINT)n, D3D11_USAGE_DEFAULT, bind, 0, 0, 0}; D3D11_SUBRESOURCE_DATA s = {data, 0, 0};
    ID3D11Buffer* b; OK(A.dev->CreateBuffer(&d, &s, &b), "CreateBuffer"); return b;
}
static ID3D11Buffer* tampon_dyn(size_t n, UINT bind) {
    D3D11_BUFFER_DESC d = {(UINT)n, D3D11_USAGE_DYNAMIC, bind, D3D11_CPU_ACCESS_WRITE, 0, 0};
    ID3D11Buffer* b; OK(A.dev->CreateBuffer(&d, nullptr, &b), "CreateBuffer (dyn)"); return b;
}
static void maj_dyn(ID3D11Buffer* b, const void* data, size_t n) {
    D3D11_MAPPED_SUBRESOURCE m; OK(A.ctx->Map(b, 0, D3D11_MAP_WRITE_DISCARD, 0, &m), "Map"); memcpy(m.pData, data, n); A.ctx->Unmap(b, 0);
}

// ------------------------------------------------------------------ chargement
static void lire_cbs(Lecteur& L, const Base& B, std::vector<DefCb>& out, Prog* P, int s) {
    uint32_t nc = L.u32();
    for (uint32_t c = 0; c < nc; c++) {
        DefCb d; d.nom = L.u32(); d.slot = L.u32(); d.taille = L.u32(); uint32_t nv = L.u32();
        for (uint32_t v = 0; v < nv; v++) { Var x; x.nom = L.u32(); x.off = L.u32(); x.taille = L.u32(); d.vars.push_back(x); }
        if (P && s == 1 && d.nom == B.nomPL) P->slotPL = d.slot;
        if (P && s == 1 && d.nom == B.nomCube) P->slotCube = d.slot;
        out.push_back(d);
    }
}

static void lire_base(Lecteur& L, Base& B) {
    uint32_t n = L.u32();
    for (uint32_t i = 0; i < n; i++) B.noms.push_back(L.texte());
    B.varDe.assign(B.noms.size(), V_AUTRE); B.estBrouillard.assign(B.noms.size(), 0);
    for (size_t i = 0; i < B.noms.size(); i++) {
        for (int k = 0; k < V_NB; k++) if (B.noms[i] == NOMS_VAR[k]) B.varDe[i] = k;
        for (const char* b : BROUILLARD) if (B.noms[i] == b) B.estBrouillard[i] = 1;
        if (B.noms[i] == "CBUSE_UB_CAMERA_IDX") B.nomCam = (uint32_t)i;
        if (B.noms[i] == "CBUSE_UB_LIGHT_IDX") B.nomLum = (uint32_t)i;
        if (B.noms[i] == "CBUSE_UB_CHARA_LIGHT_IDX") B.nomChara = (uint32_t)i;
        if (B.noms[i] == "CBUSE_UB_MODEL_MATERIAL_IDX") B.nomMat = (uint32_t)i;
        if (B.noms[i] == "CBUSE_UB_POINT_LIGHT_IDX") B.nomPL = (uint32_t)i;
        if (B.noms[i] == "CBUSE_UB_CUBEMAP_IDX") B.nomCube = (uint32_t)i;
    }
    n = L.u32();
    for (uint32_t i = 0; i < n; i++) { L.u32(); B.shaders.push_back(L.octets()); }
    n = L.u32();
    B.progs.resize(n);
    for (uint32_t i = 0; i < n; i++) {
        Prog& P = B.progs[i];
        P.vs = L.u32(); P.ps = L.u32(); P.gs = L.u32(); P.vs_tex = L.u32(); P.t11 = L.u32();
        uint32_t ne = L.u32(); P.sem.resize(ne);
        for (uint32_t e = 0; e < ne; e++) {
            uint32_t sem = L.u32(), idx = L.u32(), fmt = L.u32(), slot = L.u32();
            P.sem[e] = B.noms[sem];
            P.el.push_back({nullptr, idx, (DXGI_FORMAT)fmt, slot, 0, D3D11_INPUT_PER_VERTEX_DATA, 0});
        }
        for (uint32_t e = 0; e < ne; e++) P.el[e].SemanticName = P.sem[e].c_str();
        for (int s = 0; s < 3; s++) lire_cbs(L, B, P.etapes[s], &P, s);
        const Octets& cv = B.shaders[P.vs]; const Octets& cp = B.shaders[P.ps];
        OK(A.dev->CreateVertexShader(cv.data(), cv.size(), nullptr, &P.vso), "CreateVertexShader");
        OK(A.dev->CreatePixelShader(cp.data(), cp.size(), nullptr, &P.pso), "CreatePixelShader");
        if (P.gs != UINT32_MAX) { const Octets& cg = B.shaders[P.gs]; OK(A.dev->CreateGeometryShader(cg.data(), cg.size(), nullptr, &P.gso), "CreateGeometryShader"); }
        if (!P.el.empty()) OK(A.dev->CreateInputLayout(P.el.data(), (UINT)P.el.size(), cv.data(), cv.size(), &P.disp), "CreateInputLayout");
    }
    n = L.u32();
    // (14/11/2026) octet haut de la largeur = nombre de mips du .g4tx (LU) : 1 = pas de mips (34 048 des 34 130 textures
    // d'effets) ; 0 = inconnu (chaîne complète comme avant)
    for (uint32_t i = 0; i < n; i++) { uint32_t w = L.u32(), h = L.u32(); Octets px = L.octets(); const uint32_t mp = w >> 24; w &= 0xFFFFFF;
        B.tex.push_back(texture_rgba(w, h, px.data(), mp != 1, mp > 1 ? mp : 0)); }
    n = L.u32();
    B.geos.resize(n);
    for (uint32_t i = 0; i < n; i++) {
        Geo& G = B.geos[i]; uint32_t nf = L.u32();
        for (uint32_t f = 0; f < nf; f++) { uint32_t pas = L.u32(); Octets b = L.octets(); G.vb.push_back(tampon(b.data(), b.size(), D3D11_BIND_VERTEX_BUFFER)); G.pas.push_back(pas);
            G.cpu.push_back(pas == 4 ? std::vector<uint8_t>(b.begin(), b.end()) : std::vector<uint8_t>()); }
        Octets ib = L.octets(); G.n = (UINT)(ib.size() / 2); G.ib = tampon(ib.data(), ib.size(), D3D11_BIND_INDEX_BUFFER);
    }
}

static void lier_lumieres(const std::vector<LumPonct>& L) {
    // comme Rendu.lier_lumieres : cb8 = en-têtes + (pos, rayon), (couleur, masque) ; t17 = (nombre << 16) ; t18 = n° des lumières
    Octets cb(32, 0); uint32_t n = (uint32_t)L.size(); memcpy(&cb[0], &n, 4); float un[2] = {1, 1}; memcpy(&cb[16], un, 8);
    for (auto& l : L) { size_t o = cb.size(); cb.resize(o + 32); memcpy(&cb[o], l.v, 16); memcpy(&cb[o + 16], l.v + 4, 12); memcpy(&cb[o + 28], &l.masque, 4); }
    cb.resize(cb.size() + 32, 0);
    if (A.cb8 && cb == A.cb8Octets) return;
    A.cb8Octets = cb;
    Octets c2 = cb; c2.resize((c2.size() + 15) / 16 * 16, 0);
    A.cb8 = tampon(c2.data(), c2.size(), D3D11_BIND_CONSTANT_BUFFER);
    uint32_t g[4]; for (auto& x : g) x = n << 16;
    D3D11_BUFFER_DESC d = {16, D3D11_USAGE_DEFAULT, D3D11_BIND_SHADER_RESOURCE, 0, D3D11_RESOURCE_MISC_BUFFER_STRUCTURED, 4};
    D3D11_SUBRESOURCE_DATA s = {g, 0, 0}; ID3D11Buffer* b; OK(A.dev->CreateBuffer(&d, &s, &b), "t17");
    OK(A.dev->CreateShaderResourceView(b, nullptr, &A.t17), "t17");
    Octets r(4, 0); for (uint32_t i = 0; i < n; i++) r.push_back((uint8_t)i);
    size_t pad = n % 4 ? 4 - n % 4 : 4; for (size_t i = 0; i < pad; i++) r.push_back(255);
    r.resize((r.size() + 3) / 4 * 4, 0);
    D3D11_BUFFER_DESC d2 = {(UINT)r.size(), D3D11_USAGE_DEFAULT, D3D11_BIND_SHADER_RESOURCE, 0, D3D11_RESOURCE_MISC_BUFFER_ALLOW_RAW_VIEWS, 0};
    D3D11_SUBRESOURCE_DATA s2 = {r.data(), 0, 0}; OK(A.dev->CreateBuffer(&d2, &s2, &b), "t18");
    D3D11_SHADER_RESOURCE_VIEW_DESC sd = {}; sd.Format = DXGI_FORMAT_R32_TYPELESS; sd.ViewDimension = D3D11_SRV_DIMENSION_BUFFEREX;
    sd.BufferEx.NumElements = (UINT)r.size() / 4; sd.BufferEx.Flags = D3D11_BUFFEREX_SRV_FLAG_RAW;
    OK(A.dev->CreateShaderResourceView(b, &sd, &A.t18), "t18");
}

static void lire_particules(Lecteur& L, DessinEffet& D) {
    uint32_t nv = L.u32(); D.bNv = nv;
    D.bPos = L.vf(3 * nv); D.bCol = L.vf(4 * nv);
    for (int s = 0; s < 3; s++) D.bUv[s] = L.vf(2 * nv);
    D.bANor = L.u32() != 0; if (D.bANor) D.bNor = L.vf(3 * nv);
    D.bATan = L.u32() != 0; if (D.bATan) D.bTan = L.vf(3 * nv);
    Octets idx = L.octets(); D.bIdx.resize(idx.size() / 2); memcpy(D.bIdx.data(), idx.data(), idx.size());
}
static Geo geo_particules(const DessinEffet& D, const Prog& P) {
    // comme Rendu.geometrie_fournie : un flux par entrée du VS (couleur en flottants)
    const uint32_t nv = D.bNv; const std::vector<float>& pos = D.bPos; const std::vector<float>& col = D.bCol; const std::vector<float>* uv = D.bUv;
    const std::vector<float>& nor = D.bNor; const std::vector<float>& tan = D.bTan;
    Octets idx(D.bIdx.size() * 2); memcpy(idx.data(), D.bIdx.data(), idx.size());
    Geo G;
    for (size_t e = 0; e < P.el.size(); e++) {
        std::string n = P.sem[e]; std::vector<float> b; UINT pas = 12;
        if (n == "POSITION") { b = pos; pas = 12; }
        else if (n == "COLOR") { b = col; pas = 16; }
        else if (n == "TEXCOORD") { b = uv[std::min<UINT>(P.el[e].SemanticIndex, 2)]; pas = 8; }
        else if (n == "NORMAL") { if (!nor.empty()) b = nor; else for (uint32_t i = 0; i < nv; i++) { b.push_back(0); b.push_back(0); b.push_back(1); } pas = 12; }
        else if (n == "TANGENT") { for (uint32_t i = 0; i < nv; i++) { if (!tan.empty()) { b.push_back(tan[3 * i]); b.push_back(tan[3 * i + 1]); b.push_back(tan[3 * i + 2]); }
                                    else { b.push_back(1); b.push_back(0); b.push_back(0); } b.push_back(1); } pas = 16; }
        else { b.assign(3 * nv, 0.f); pas = 12; }
        G.vb.push_back(tampon(b.data(), b.size() * 4, D3D11_BIND_VERTEX_BUFFER)); G.pas.push_back(pas);
    }
    G.n = (UINT)(idx.size() / 2); G.ib = tampon(idx.data(), idx.size(), D3D11_BIND_INDEX_BUFFER);
    return G;
}

static void choisir_instance(PieceA& p, size_t j) {
    while (p.inst.size() <= j) p.inst.push_back({tampon_dyn(12 * p.nv, D3D11_BIND_VERTEX_BUFFER), tampon_dyn(12 * p.nv, D3D11_BIND_VERTEX_BUFFER), tampon_dyn(16 * p.nv, D3D11_BIND_VERTEX_BUFFER)});
    p.vbPos = p.inst[j][0]; p.vbNor = p.inst[j][1]; p.vbTan = p.inst[j][2];
}
static void lire_acteurs(Lecteur& E) {
    uint32_t nm = E.u32(); A.modeles.resize(nm);
    for (auto& M : A.modeles) {
        uint32_t np = E.u32(); M.resize(np);
        for (auto& p : M) {
            p.noir = E.u32(); p.prog = E.i32(); p.prog_st = E.i32(); p.nv = E.u32(); p.faces = E.u32();
            Octets b = E.octets(); p.pos.resize(3 * p.nv); memcpy(p.pos.data(), b.data(), b.size());
            b = E.octets(); p.nor.resize(3 * p.nv); memcpy(p.nor.data(), b.data(), b.size());
            b = E.octets(); p.tan.resize(4 * p.nv); memcpy(p.tan.data(), b.data(), b.size());
            b = E.octets(); p.os.resize(4 * p.nv); memcpy(p.os.data(), b.data(), b.size());
            b = E.octets(); p.poids.resize(4 * p.nv); memcpy(p.poids.data(), b.data(), b.size());
            Octets col = E.octets();
            for (int u = 0; u < 6; u++) { Octets uv = E.octets(); p.vbUv[u] = tampon(uv.data(), uv.size(), D3D11_BIND_VERTEX_BUFFER); }
            Octets idx = E.octets(); p.n = (UINT)(idx.size() / 2);
            for (int k = 0; k < 6; k++) p.tex[k] = E.i32();
            for (int k = 0; k < 6; k++) { p.adr[k][0] = E.u32(); p.adr[k][1] = E.u32(); }
            E.f32s(p.params, 32); E.f32s(p.diffuse, 4); E.f32s(p.ambient, 4); E.f32s(p.uv, 48);
            if (!p.nv || !p.n) continue;
            p.vbCol = tampon(col.data(), col.size(), D3D11_BIND_VERTEX_BUFFER);
            std::vector<uint8_t> z(12 * p.nv, 0); p.vbZero = tampon(z.data(), z.size(), D3D11_BIND_VERTEX_BUFFER);
            p.ib = tampon(idx.data(), idx.size(), D3D11_BIND_INDEX_BUFFER);
            choisir_instance(p, 0);
        }
    }
}

static bool charger_decor(const std::wstring& dos) {
    Lecteur L;
    if (!L.ouvrir(dos + L"\\scene.bin") || memcmp(L.d.data(), "INZ1", 4)) return false;
    L.p = 4;
    lire_base(L, A.decor);
    uint32_t n = L.u32();
    A.dessins.resize(n);
    for (uint32_t i = 0; i < n; i++) {
        Dessin& D = A.dessins[i];
        D.passe = L.u32(); D.prog = L.u32(); D.geo = L.u32();
        for (int k = 0; k < 6; k++) D.tex[k] = L.i32();
        for (int k = 0; k < 6; k++) { D.adr[k][0] = L.u32(); D.adr[k][1] = L.u32(); }
        D.faces = L.u32(); D.a_inst = L.u32(); D.lod = L.i32(); D.lod_r = L.f32();
        L.f32s(D.params, 32); L.f32s(D.diffuse, 4); L.f32s(D.ambient, 4); L.f32s(D.uv, 48); L.f32s(D.ub, 4);
        L.f64s(D.inst, 16);
    }
    n = L.u32();
    for (uint32_t i = 0; i < n; i++) { Lum l; l.img = L.octets(); l.brouillard = L.octets(); L.f32s(l.rg, 64); A.lums.push_back(l); }
    if (L.u32()) {                                    // cubemap BC6H (6 faces, chacune avec ses niveaux), vue TextureCubeArray
        uint32_t w = L.u32(), h = L.u32(), mips = L.u32(), fmt = L.u32(); Octets o = L.octets();
        std::vector<D3D11_SUBRESOURCE_DATA> init(6 * mips); size_t p = 0;
        for (int f = 0; f < 6; f++) { uint32_t lw = w, lh = h;
            for (uint32_t k = 0; k < mips; k++) { uint32_t bw = std::max(1u, (lw + 3) / 4), bh = std::max(1u, (lh + 3) / 4);
                init[f * mips + k] = {o.data() + p, bw * 16, bw * bh * 16}; p += bw * bh * 16; lw = std::max(1u, lw / 2); lh = std::max(1u, lh / 2); } }
        D3D11_TEXTURE2D_DESC d = {w, h, mips, 6, (DXGI_FORMAT)fmt, {1, 0}, D3D11_USAGE_DEFAULT, D3D11_BIND_SHADER_RESOURCE, 0, D3D11_RESOURCE_MISC_TEXTURECUBE};
        ID3D11Texture2D* t; OK(A.dev->CreateTexture2D(&d, init.data(), &t), "CreateTexture2D (cube)");
        D3D11_SHADER_RESOURCE_VIEW_DESC sd = {}; sd.Format = (DXGI_FORMAT)fmt; sd.ViewDimension = D3D11_SRV_DIMENSION_TEXTURECUBEARRAY;
        sd.TextureCubeArray.MipLevels = mips; sd.TextureCubeArray.NumCubes = 1;
        OK(A.dev->CreateShaderResourceView(t, &sd, &A.cube), "CreateSRV (cube)");
    }
    { Octets b = L.octets(); b.resize((b.size() + 15) / 16 * 16, 0); A.cb9 = tampon(b.data(), b.size(), D3D11_BIND_CONSTANT_BUFFER); }
    L.octets(); L.octets();
    lier_lumieres({});
    return true;
}

static bool charger_effets(const std::wstring& dos) {
    uint32_t n;
    for (int k = 0; k < SP_NB; k++) A.speciaux[k] = -1;
    Lecteur E;
    if (E.ouvrir(dos + L"\\effets.bin") && !memcmp(E.d.data(), "INZE", 4)) {
        E.p = 4; lire_base(E, A.eff);
        n = E.u32(); A.elems.resize(n);
        for (uint32_t i = 0; i < n; i++) { Element& x = A.elems[i]; x.prog = E.u32(); x.geo = E.i32();
            for (int k = 0; k < 6; k++) x.tex[k] = E.i32();
            for (int k = 0; k < 6; k++) { x.adr[k][0] = E.u32(); x.adr[k][1] = E.u32(); }
            x.melange = E.u32(); x.part = E.u32(); x.seuil = (x.part >> 8) & 0x1FF; x.part &= 1; }
        for (int k = 0; k < SP_NB; k++) A.speciaux[k] = E.i32();
        uint32_t nps = E.u32();
        for (uint32_t k = 0; k < nps; k++) {
            uint32_t sh = E.u32(); PsSeul& P = A.psSeuls[std::min<uint32_t>(k, PS_NB - 1)];
            const Octets& c = A.eff.shaders[sh]; OK(A.dev->CreatePixelShader(c.data(), c.size(), nullptr, &P.ps), "PS seul");
            lire_cbs(E, A.eff, P.cbs, nullptr, 1);
        }
        A.texSys[0] = E.i32(); A.texSys[1] = E.i32();
        lire_acteurs(E);
    }
    else return false;
    return true;
}

// images.bin (animation calculée par la page : ancien lecteur, ou référence des vérifications)
static bool lire_images(const std::wstring& fichier, std::vector<Image>& images, bool creerGeo) {
    uint32_t n;
    Lecteur I;
    if (!I.ouvrir(fichier) || memcmp(I.d.data(), "INZF", 4)) return false;
    I.p = 4; n = I.u32(); images.resize(n);
    for (uint32_t i = 0; i < n; i++) {
        Image& im = images[i]; I.f64s(im.V, 16); I.f64s(im.P, 16); im.lum = I.u32(); im.decor = I.u32();
        uint32_t nl = I.u32(); im.lumieres.resize(nl);
        for (auto& l : im.lumieres) { I.f32s(l.v, 7); l.masque = I.u32(); }
        uint32_t nd = I.u32(); im.effets.resize(nd);
        for (auto& d : im.effets) {
            d.elem = I.u32(); d.flags = I.u32();
            I.f64s(d.mvp, 16); I.f64s(d.modele, 16); I.f64s(d.V, 16); I.f64s(d.P, 16);
            I.f32s(d.params, 32); I.f32s(d.diffuse, 4); I.f32s(d.ambient, 4); I.f32s(d.uv, 48); d.grd = I.f32();
            uint32_t no = I.u32(); d.os.resize(16 * no); I.f64s(d.os.data(), 16 * no);
            if (d.elem < A.elems.size() && A.elems[d.elem].part) { lire_particules(I, d); if (creerGeo) d.geoP = geo_particules(d, A.eff.progs[A.elems[d.elem].prog]); }
        }
        im.om.present = I.u32();
        if (im.om.present) {
            im.om.T = I.u32();
            for (int k = 0; k < 3; k++) I.f64s(im.om.vp[k], 16);
            for (int k = 0; k < 3; k++) I.f64s(im.om.tr[k], 2);
            I.f64s(im.om.dir, 3); I.f64s(im.om.biais, 3);
        }
        uint32_t na = I.u32(); im.acteurs.resize(na);
        for (auto& a : im.acteurs) {
            a.modele = I.u32(); uint32_t np = I.u32(); a.pieces.resize(np); for (auto& x : a.pieces) x = I.u32();
            uint32_t nm = I.u32(); a.mats.resize(16 * nm); I.f64s(a.mats.data(), 16 * nm);
            a.statut = I.u32(); if (a.statut) I.f32s(a.st, 12);
        }
        uint32_t np = I.u32(); im.pieds.resize(12 * np); I.f64s(im.pieds.data(), 12 * np);
        im.foyer = I.f64();
    }
    return true;
}


// lums.bin de la technique : réglages de lumière des plans (CLightData, brouillard, passes d'écran)
static bool charger_lums(const std::wstring& f) {
    Lecteur L; if (!L.ouvrir(f) || memcmp(L.d.data(), "INZL", 4)) return false;
    L.p = 4; uint32_t n = L.u32(); A.lums.clear();
    for (uint32_t i = 0; i < n; i++) { Lum l; l.img = L.octets(); l.brouillard = L.octets(); L.f32s(l.rg, 64); A.lums.push_back(l); }
    return true;
}
// modifs.bin : textures recolorées dans l'Atelier (remplacent celles d'effets.bin)
// (14/11/2026) rechargées PENDANT la lecture (commande « textures » de la page, après une retouche) : chaque texture
// d'origine est gardée ; les retouches précédentes sont d'abord défaites (une texture remise d'origine le redevient)
static std::vector<ID3D11ShaderResourceView*> TEX_ORIG; static std::map<uint32_t, ID3D11ShaderResourceView*> TEX_MODIF;
static std::wstring F_MODIFS;
static void charger_modifs(const std::wstring& f) {
    F_MODIFS = f;
    if (TEX_ORIG.empty()) TEX_ORIG = A.eff.tex;
    for (auto& m : TEX_MODIF) { if (m.first < A.eff.tex.size()) A.eff.tex[m.first] = TEX_ORIG[m.first]; if (m.second) m.second->Release(); }
    TEX_MODIF.clear();
    Lecteur L; if (!L.ouvrir(f) || L.d.size() < 8 || memcmp(L.d.data(), "INZM", 4)) return;
    L.p = 4; uint32_t n = L.u32();
    for (uint32_t i = 0; i < n; i++) { uint32_t k = L.u32(), w = L.u32(), h = L.u32(); Octets px = L.octets();
        if (k < A.eff.tex.size() && px.size() >= (size_t)w * h * 4) {
            UINT nv = 0;                          // même nombre de mips que la texture d'origine (.g4tx, LU)
            if (TEX_ORIG[k]) { D3D11_SHADER_RESOURCE_VIEW_DESC sd; TEX_ORIG[k]->GetDesc(&sd); nv = sd.Texture2D.MipLevels; }
            A.eff.tex[k] = texture_rgba((int)w, (int)h, px.data(), nv != 1, nv > 1 ? nv : 0); TEX_MODIF[k] = A.eff.tex[k]; } }
}

// ------------------------------------------------------------------ animation calculée par le lecteur (14/11/2026)
#include "animation.h"
#include "technique.h"
static Technique T; static bool modeTech = false; static int calcules = 0;
// (14/11/2026) teintes des couleurs de sommets choisies dans l'Atelier : flux COLOR (n° 0) de la géométrie de la pièce refait
static void teintes_sommets() {
    for (const PieceT& p : T.pieces) { if (p.elem >= A.elems.size()) continue; const Element& X = A.elems[p.elem];
        if (X.part || X.geo < 0 || (size_t)X.geo >= A.eff.geos.size()) continue; Geo& G = A.eff.geos[X.geo]; const Prog& P = A.eff.progs[X.prog];
        // (15/11/2026) relu en direct : refait seulement si la teinte a changé (posée, changée ou retirée -> couleurs d'origine)
        if (G.teinte == p.aTeinteS && (!p.aTeinteS || (G.tH == p.tH && G.tC == p.tC))) continue;
        G.teinte = p.aTeinteS; G.tH = p.tH; G.tC = p.tC;
        for (size_t e = 0; e < P.sem.size() && e < G.vb.size(); e++) {
            if (P.sem[e] != "COLOR" || P.el[e].SemanticIndex != 0 || e >= G.cpu.size() || G.cpu[e].empty()) continue;
            std::vector<uint8_t> b = G.cpu[e];
            if (p.aTeinteS) for (size_t i = 0; i + 3 < b.size(); i += 4) { double c[3] = {b[i] / 255.0, b[i + 1] / 255.0, b[i + 2] / 255.0}; teinter_hsv(c, p.tH, p.tC);
                for (int k = 0; k < 3; k++) b[i + k] = (uint8_t)std::max(0.0, std::min(255.0, floor(c[k] * 255 + 0.5))); }
            if (G.vb[e]) G.vb[e]->Release(); G.vb[e] = tampon(b.data(), b.size(), D3D11_BIND_VERTEX_BUFFER); } }
}
static void particules_gpu(Image& im) {
    for (auto& D : im.effets) if (D.elem < A.elems.size() && A.elems[D.elem].part && D.bNv) {
        // (15/11/2026) teinte de l'Atelier posée sur une copie des couleurs (bCol garde celles d'origine : refaites en direct)
        const bool t = D.srcE >= 0 && D.srcE < (int)T.ems.size() && T.ems[D.srcE].aTeinte;
        std::vector<float> orig; if (t) { orig = D.bCol; const EmetT& e = T.ems[D.srcE];
            for (size_t i = 0; i + 3 < D.bCol.size(); i += 4) { double c[3] = {D.bCol[i], D.bCol[i + 1], D.bCol[i + 2]}; teinter_hsv(c, e.tH, e.tC);
                for (int k = 0; k < 3; k++) D.bCol[i + k] = (float)c[k]; } }
        for (auto* b : D.geoP.vb) if (b) b->Release(); if (D.geoP.ib) D.geoP.ib->Release(); D.geoP = Geo();
        D.geoP = geo_particules(D, A.eff.progs[A.elems[D.elem].prog]);
        if (t) D.bCol.swap(orig); }
}
// (15/11/2026) ÉCLAT (commande « surligner <ms> <clés> » de l'Atelier) : pièces / émetteurs localisés plus lumineux quelques
// instants (couleur × 1 à 2,8, pulsation 2,5 fois par seconde) ; même effet que l'aperçu (vue3d.facteurEclat)
static std::vector<char> ECLAT_P, ECLAT_E; static ULONGLONG ECLAT_DEBUT = 0, ECLAT_FIN = 0;
static float facteurEclat(const DessinEffet& D) {
    if (!ECLAT_FIN) return 1.0f;
    const ULONGLONG t = GetTickCount64(); if (t > ECLAT_FIN) { ECLAT_FIN = 0; return 1.0f; }
    const bool oui = (D.src >= 0 && D.src < (int)ECLAT_P.size() && ECLAT_P[D.src]) || (D.srcE >= 0 && D.srcE < (int)ECLAT_E.size() && ECLAT_E[D.srcE]);
    return oui ? (float)(1 + 1.8 * (0.5 - 0.5 * cos((t - ECLAT_DEBUT) / 1000.0 * 3.14159265358979 * 2 * 2.5))) : 1.0f;
}
static void surligner(const char* liste) {      // « <ms> clé clé … »
    int ms = 0, n = 0; if (sscanf(liste, "%d%n", &ms, &n) != 1) return;
    ECLAT_P.assign(T.pieces.size(), 0); ECLAT_E.assign(T.ems.size(), 0);
    std::string s(liste + n); size_t q = 0;
    while (q < s.size()) { while (q < s.size() && s[q] == ' ') q++; size_t r = s.find(' ', q); if (r == std::string::npos) r = s.size();
        const std::string k = s.substr(q, r - q); q = r;
        for (size_t i = 0; i < T.pieces.size(); i++) if (T.pieces[i].cle == k) ECLAT_P[i] = 1;
        for (size_t i = 0; i < T.ems.size(); i++) if (T.ems[i].cle == k) ECLAT_E[i] = 1; }
    ECLAT_DEBUT = GetTickCount64(); ECLAT_FIN = ECLAT_DEBUT + std::max(100, ms);
}
static bool dessinCache(const DessinEffet& D) {          // (15/11/2026) pièce / émetteur caché dans l'Atelier (options.json)
    if (!modeTech) return false;
    if (D.src >= 0 && D.src < (int)T.pieces.size()) return T.pieces[D.src].cachee;
    if (D.srcE >= 0 && D.srcE < (int)T.ems.size()) return T.ems[D.srcE].cachee;
    return false;
}
static bool sansGpu = false;                 // (vérification : pas de tampons de sommets)
static void assurer_image(int f) {           // images calculées dans l'ordre (les particules avancent d'une image à la suivante)
    if (!modeTech) return;
    while (calcules <= f && calcules < (int)A.images.size()) { T.image(calcules, A.images[calcules]); if (!sansGpu) particules_gpu(A.images[calcules]); calcules++; }
}
// --verifier : compare l'animation calculée ici à celle de la page (reference.bin écrit par essai_anim.py)
struct Ecart { double max = 0; long long n = 0, diff = 0; int premiere = -1; std::string ou; };
static std::map<std::string, Ecart> ECARTS; static std::vector<std::string> STRUCT;
template <class X, class Y> static void cmp(const char* cat, const X* a, const Y* b, size_t n, int f, const std::string& ou) {
    Ecart& E = ECARTS[cat];
    for (size_t i = 0; i < n; i++) { const double x = (double)a[i], y = (double)b[i]; E.n++;
        if (x == y || (x != x && y != y)) continue;
        const double d = (x != x || y != y) ? INFINITY : fabs(x - y); E.diff++;
        if (d > E.max || E.ou.empty()) { E.max = std::max(E.max, d); char t[300]; sprintf_s(t, "image %d %s [%zu] : lecteur %.9g / page %.9g", f, ou.c_str(), i, x, y); E.ou = t; }
        if (E.premiere < 0) E.premiere = f; }
}
static void verifier(const std::vector<Image>& ref, const std::wstring& rapport) {
    const int n = std::min((int)ref.size(), (int)A.images.size());
    for (int f = 0; f < n; f++) {
        assurer_image(f); const Image& a = A.images[f]; const Image& b = ref[f]; char t[512];
        cmp("camera V", a.V, b.V, 16, f, ""); cmp("camera P", a.P, b.P, 16, f, "");
        if (a.lum != b.lum || a.decor != b.decor) { sprintf_s(t, "image %d : reglages %u / %u, decor %u / %u", f, a.lum, b.lum, a.decor, b.decor); STRUCT.push_back(t); }
        if (a.lumieres.size() != b.lumieres.size()) { sprintf_s(t, "image %d : %zu lumieres / %zu", f, a.lumieres.size(), b.lumieres.size()); STRUCT.push_back(t); }
        else for (size_t i = 0; i < a.lumieres.size(); i++) { cmp("lumieres", a.lumieres[i].v, b.lumieres[i].v, 7, f, "lum " + std::to_string(i));
            if (a.lumieres[i].masque != b.lumieres[i].masque) { sprintf_s(t, "image %d : masque de lumiere %zu", f, i); STRUCT.push_back(t); } }
        bool memes = a.effets.size() == b.effets.size();
        if (memes) for (size_t i = 0; i < a.effets.size(); i++) if (a.effets[i].elem != b.effets[i].elem || a.effets[i].flags != b.effets[i].flags) memes = false;
        if (!memes) { std::string s = "image " + std::to_string(f) + " : dessins lecteur [";
            for (auto& d : a.effets) s += std::to_string(d.elem) + "/" + std::to_string(d.flags) + " "; s += "] page ["; for (auto& d : b.effets) s += std::to_string(d.elem) + "/" + std::to_string(d.flags) + " "; s += "]"; STRUCT.push_back(s); }
        else for (size_t i = 0; i < a.effets.size(); i++) { const DessinEffet& x = a.effets[i]; const DessinEffet& y = b.effets[i]; std::string ou = "dessin " + std::to_string(i) + " (element " + std::to_string(x.elem) + ")";
            cmp("effets mvp", x.mvp, y.mvp, 16, f, ou); cmp("effets modele", x.modele, y.modele, 16, f, ou); cmp("effets V", x.V, y.V, 16, f, ou); cmp("effets P", x.P, y.P, 16, f, ou);
            cmp("effets u_shaderParam", x.params, y.params, 32, f, ou); cmp("effets diffuse/ambient", x.diffuse, y.diffuse, 4, f, ou); cmp("effets diffuse/ambient", x.ambient, y.ambient, 4, f, ou);
            cmp("effets u_texProj", x.uv, y.uv, 48, f, ou); cmp("effets grd", &x.grd, &y.grd, 1, f, ou);
            if (x.os.size() != y.os.size()) { sprintf_s(t, "image %d %s : %zu os / %zu", f, ou.c_str(), x.os.size() / 16, y.os.size() / 16); STRUCT.push_back(t); } else cmp("effets os (peau)", x.os.data(), y.os.data(), x.os.size(), f, ou);
            if (x.bNv != y.bNv) { sprintf_s(t, "image %d %s : %u sommets de particules / %u", f, ou.c_str(), x.bNv, y.bNv); STRUCT.push_back(t); }
            else if (x.bNv) { cmp("particules position", x.bPos.data(), y.bPos.data(), x.bPos.size(), f, ou); cmp("particules couleur", x.bCol.data(), y.bCol.data(), x.bCol.size(), f, ou);
                for (int s = 0; s < 3; s++) cmp("particules uv", x.bUv[s].data(), y.bUv[s].data(), std::min(x.bUv[s].size(), y.bUv[s].size()), f, ou);
                if (x.bANor == y.bANor && x.bANor) { cmp("particules normale/tangente", x.bNor.data(), y.bNor.data(), x.bNor.size(), f, ou); cmp("particules normale/tangente", x.bTan.data(), y.bTan.data(), x.bTan.size(), f, ou); }
                else if (x.bANor != y.bANor) { sprintf_s(t, "image %d %s : normales %d / %d", f, ou.c_str(), (int)x.bANor, (int)y.bANor); STRUCT.push_back(t); }
                if (x.bIdx != y.bIdx) { sprintf_s(t, "image %d %s : indices", f, ou.c_str()); STRUCT.push_back(t); } } }
        if (a.om.present != b.om.present) { sprintf_s(t, "image %d : ombres %u / %u", f, a.om.present, b.om.present); STRUCT.push_back(t); }
        else if (a.om.present) { for (int k = 0; k < 3; k++) cmp("ombres cascades", a.om.vp[k], b.om.vp[k], 16, f, "cascade " + std::to_string(k));
            for (int k = 0; k < 3; k++) cmp("ombres tranches/dir/biais", a.om.tr[k], b.om.tr[k], 2, f, "tranche");
            cmp("ombres tranches/dir/biais", a.om.dir, b.om.dir, 3, f, "dir"); cmp("ombres tranches/dir/biais", a.om.biais, b.om.biais, 3, f, "biais"); }
        if (a.acteurs.size() != b.acteurs.size()) { sprintf_s(t, "image %d : %zu personnages / %zu", f, a.acteurs.size(), b.acteurs.size()); STRUCT.push_back(t); }
        else for (size_t i = 0; i < a.acteurs.size(); i++) { const ActeurImage& x = a.acteurs[i]; const ActeurImage& y = b.acteurs[i];
            if (x.modele != y.modele || x.pieces != y.pieces || x.mats.size() != y.mats.size() || x.statut != y.statut) {
                sprintf_s(t, "image %d : personnage %zu (modele %u/%u, %zu/%zu pieces, %zu/%zu os, statut %u/%u)", f, i, x.modele, y.modele, x.pieces.size(), y.pieces.size(), x.mats.size() / 16, y.mats.size() / 16, x.statut, y.statut); STRUCT.push_back(t); }
            else { cmp("personnages os", x.mats.data(), y.mats.data(), x.mats.size(), f, "personnage " + std::to_string(i)); if (x.statut) cmp("personnages statut", x.st, y.st, 12, f, ""); } }
        if (a.pieds.size() != b.pieds.size()) { sprintf_s(t, "image %d : %zu ombres de pieds / %zu", f, a.pieds.size() / 12, b.pieds.size() / 12); STRUCT.push_back(t); }
        else cmp("ombre des pieds", a.pieds.data(), b.pieds.data(), a.pieds.size(), f, "");
        cmp("mise au point", &a.foyer, &b.foyer, 1, f, "");
    }
    FILE* x = _wfopen(rapport.c_str(), L"w"); if (!x) return;
    fprintf(x, "Verification de l'animation calculee par le lecteur (C++) contre celle de la page : %d images\n\n", n);
    for (auto& p : ECARTS) fprintf(x, "%-30s : %lld valeurs, %lld differentes, ecart max %.3g%s%s\n", p.first.c_str(), p.second.n, p.second.diff, p.second.max, p.second.diff ? " -- " : "", p.second.ou.c_str());
    fprintf(x, "\nDifferences de structure : %zu\n", STRUCT.size());
    for (size_t i = 0; i < STRUCT.size() && i < 60; i++) fprintf(x, "  %s\n", STRUCT[i].c_str());
    fclose(x);
}

// ------------------------------------------------------------------ valeurs (comme rendu_image.tampons)
static void poser(int id, const float* v, size_t n) { A.val[id].v.assign(v, v + n); A.val[id].ok = true; }
static void poser_m(int id, const double* m) { float o[16]; lignes(m, o); poser(id, o, 16); }
static void effacer(int id) { A.val[id].ok = false; }

static double echelle_x(const double* P) { return (P[11] != 0 && P[0] != 0) ? (P[5] * (double)A.H / (double)A.W) / P[0] : 1.0; }
static void ligne0(double* m, double k) { m[0] *= k; m[4] *= k; m[8] *= k; m[12] *= k; }

// corriger : mvp = P x V de la page (mis à la forme de la fenêtre) ; non pour les cascades d'ombre et les mvp identité
static bool camPrecOk = false; static double camPrecV[16], camPrecVP[16], camPrecWP[16], camCourV[16], camCourVP[16], camCourWP[16];
static void valeurs_camera(const double* Vw, const double* Pin, const double* mvpgl_in, bool corriger = true, bool principale = false) {
    double P[16], mvpgl[16]; memcpy(P, Pin, sizeof P); memcpy(mvpgl, mvpgl_in, sizeof mvpgl);
    double k = echelle_x(Pin); ligne0(P, k); if (corriger) ligne0(mvpgl, k);
    memcpy(A.V, Vw, sizeof A.V);
    double vp[16], t[16];
    mul(GL_VERS_D3D, mvpgl, A.mvp); mul(GL_VERS_D3D, P, vp);
    poser_m(V_VP, vp); poser_m(V_EYEVP, vp); poser_m(V_WV, Vw); poser_m(V_WP, A.mvp); poser_m(V_EYEWV, Vw); poser_m(V_EYEWP, A.mvp);
    float nf[4] = {0.05f, 8000, 1, 1};
    if (fabs(P[11] + 1) <= 1e-6 && P[0] && P[5]) { nf[0] = (float)(P[14] / (P[10] - 1)); nf[1] = (float)(P[14] / (P[10] + 1)); nf[2] = (float)(1 / P[0]); nf[3] = (float)(1 / P[5]); }
    poser(V_NFIA, nf, 4);
    inv4(vp, t); poser_m(V_EYEPV, t); poser_m(V_PV, t);
    float eye[3]; for (int i = 0; i < 3; i++) eye[i] = (float)-(Vw[i * 4] * Vw[12] + Vw[i * 4 + 1] * Vw[13] + Vw[i * 4 + 2] * Vw[14]);
    poser(V_EYEPOS, eye, 3);
    float dir[4] = {(float)-Vw[2], (float)-Vw[6], (float)-Vw[10], 0}, up[4] = {(float)Vw[1], (float)Vw[5], (float)Vw[9], 0};
    poser(V_EYEDIR, dir, 4); poser(V_EYEUP, up, 4);
    // (14/11/2026) u_mtxEyeSphere (tampon caméra +0x1C0 = scène +0xA70), LU nie.exe 0x141348c27 (produit 0x140078820 vérifié à
    // l'émulateur) : diag(0,5 ; −0,5 ; 0,5) x rotation de la vue, 4e colonne 0,5. Sert au reflet de chr_toon_metal (t3 lue en
    // (ligne 0 · n, ligne 1 · n)). Avant : jamais posée (0) -> reflet lu dans un coin de la carte, armures trop blanches.
    { float es[12] = {(float)(0.5 * Vw[0]), (float)(0.5 * Vw[4]), (float)(0.5 * Vw[8]), 0.5f,
                      (float)(-0.5 * Vw[1]), (float)(-0.5 * Vw[5]), (float)(-0.5 * Vw[9]), 0.5f,
                      (float)(0.5 * Vw[2]), (float)(0.5 * Vw[6]), (float)(0.5 * Vw[10]), 0.5f};
      poser(V_EYESPH, es, 12); }
    inv4(Vw, t); poser_m(V_VW, t); poser_m(V_EYEVW, t);
    inv4(A.mvp, t); poser_m(V_PW, t); poser_m(V_EYEPW, t);
    poser_m(V_WVOLD, Vw); poser_m(V_VPOLD, vp); poser_m(V_WPOLD, A.mvp);
    if (principale) {     // TAA : matrices de l'image précédente (u_mtx…Old) -> vitesses écrites en o1 par les shaders du jeu
        memcpy(camCourV, Vw, sizeof camCourV); memcpy(camCourVP, vp, sizeof camCourVP); memcpy(camCourWP, A.mvp, sizeof camCourWP);
        if (camPrecOk) { poser_m(V_WVOLD, camPrecV); poser_m(V_VPOLD, camPrecVP); poser_m(V_WPOLD, camPrecWP); }
    }
}

static void valeurs_dessin(const double* modele, const float* ub, const float* diffuse, const float* ambient, const float* uv,
                           const float* params, float grd, const std::vector<double>* os) {
    double t[16];
    poser_m(V_LW, modele); poser_m(V_LWOLD, modele);
    mul(A.V, modele, t); poser_m(V_LV, t); poser_m(V_LVOLD, t);
    mul(A.mvp, modele, t); poser_m(V_LP, t);
    poser(V_UB, ub, 4); poser(V_DIFF, diffuse, 4); poser(V_AMB, ambient, 4);
    float z4[4] = {0, 0, 0, 0}, un3[3] = {1, 1, 1}, g4[4] = {grd, 0, 0, 0}; poser(V_SPEC, z4, 4); poser(V_ATTACH, un3, 3); poser(V_GRD, g4, 4);
    float tp[48]; for (int k = 0; k < 6; k++) { float r[8] = {1, 0, 0, 0, 0, 1, 0, 0};
        if (uv) { const float* m = uv + 8 * k; r[0] = m[0]; r[1] = m[1]; r[2] = m[2]; r[4] = m[4]; r[5] = m[5]; r[6] = m[6]; } memcpy(tp + 8 * k, r, 32); }
    poser(V_TEXPROJ, tp, 48);
    float uvr[24]; for (int k = 0; k < 6; k++) { uvr[4 * k] = 0; uvr[4 * k + 1] = 0; uvr[4 * k + 2] = 1; uvr[4 * k + 3] = 1; }
    poser(V_UVRANGE, uvr, 24);
    for (int i = 0; i < 8; i++) { if (params) poser(V_SP0 + i, params + 4 * i, 4); else poser(V_SP0 + i, z4, 4); }
    effacer(V_BONE);
    if (os && !os->empty()) {          // u_mtxBone[k] (float3x4 row_major) = 3 premières lignes de la matrice de l'os k
        std::vector<float> b; float l[16];
        for (size_t i = 0; i + 16 <= os->size(); i += 16) { lignes(os->data() + i, l); b.insert(b.end(), l, l + 12); }
        poser(V_BONE, b.data(), b.size());
    }
    for (int i = V_SKIN; i <= V_SHSAMP; i++) effacer(i);   // (valeurs des acteurs : posées par valeurs_acteur)
}

// passes d'écran : a = {modele I, mvp, V, P, uv [], params [], diffuse 1, ambient 0} comme rendu_image
static void valeurs_passe(const Image& im, bool mvpIdentite) {
    double mvpgl[16]; if (mvpIdentite) memcpy(mvpgl, ID, sizeof mvpgl); else mul(im.P, im.V, mvpgl);
    valeurs_camera(im.V, im.P, mvpgl, !mvpIdentite);
    float ub[4] = {1, 0, 0, 0}, un[4] = {1, 1, 1, 1}, z[4] = {0, 0, 0, 0};
    valeurs_dessin(ID, ub, un, z, nullptr, nullptr, 0, nullptr);
}

static ID3D11Buffer* cb_dynamique(uint32_t slot, uint32_t taille, const Octets& b) {
    uint64_t k = ((uint64_t)slot << 32) | taille;
    auto it = A.cbPool.find(k); ID3D11Buffer* x;
    if (it == A.cbPool.end()) { x = tampon_dyn(taille, D3D11_BIND_CONSTANT_BUFFER); A.cbPool[k] = x; } else x = it->second;
    D3D11_MAPPED_SUBRESOURCE m; OK(A.ctx->Map(x, 0, D3D11_MAP_WRITE_DISCARD, 0, &m), "Map");
    memcpy(m.pData, b.data(), std::min<size_t>(b.size(), taille)); A.ctx->Unmap(x, 0);
    return x;
}
// petit tampon de constantes ponctuel (cb0, cb2, cb6… des passes d'écran) : un tampon par appel dans une image
static std::vector<ID3D11Buffer*> cbJetables; static size_t cbJetablesN = 0;
static ID3D11Buffer* cb_valeurs(const float* v, size_t n) {
    size_t taille = (n * 4 + 15) / 16 * 16; Octets b(taille, 0); memcpy(b.data(), v, n * 4);
    if (cbJetablesN >= cbJetables.size()) cbJetables.push_back(tampon_dyn(4096, D3D11_BIND_CONSTANT_BUFFER));
    ID3D11Buffer* x = cbJetables[cbJetablesN++]; maj_dyn(x, b.data(), b.size()); return x;
}

static void tampons_cbs(const Base& B, const std::vector<DefCb>* etapes, int nEt, const Lum* lum, std::vector<std::pair<uint32_t, Octets>>& out,
                        std::vector<uint32_t>* noms = nullptr) {
    out.clear(); if (noms) noms->clear();
    for (int s = 0; s < nEt; s++) for (const DefCb& c : etapes[s]) {
        Octets* deja = nullptr; for (auto& o : out) if (o.first == c.slot) deja = &o.second;
        int bloc = -1;
        if (lum) { if (c.nom == B.nomLum) bloc = 0x140; else if (c.nom == B.nomChara) bloc = 0x6B0; }
        Octets buf;
        if (deja) buf = *deja;
        else if (bloc >= 0) buf.assign(lum->img.begin() + bloc, lum->img.begin() + std::min<size_t>(lum->img.size(), bloc + c.taille));
        if (buf.size() < c.taille) buf.resize(c.taille, 0);
        bool brl = lum && c.nom == B.nomCam && !deja;
        if (brl && buf.size() > 0x250) { size_t n = std::min<size_t>(0xE0, buf.size() - 0x250); memcpy(&buf[0x250], lum->brouillard.data(), std::min(n, lum->brouillard.size())); }
        for (const Var& v : c.vars) {
            int id = B.varDe[v.nom];
            bool connu = id >= 0 && A.val[id].ok;
            if (bloc >= 0 && !connu) continue;
            if (brl && B.estBrouillard[v.nom]) continue;
            if (connu) {
                size_t n = 4 * A.val[id].v.size();
                // (14/11/2026) u_mtxBone : TOUTE la palette. La réflexion dit u_mtxBone[4] (192 octets) mais le tableau du jeu
                // va jusqu'à u_mtxBoneEnd (+12240 : 255 os) ; coupé à 4 os, les sommets des os 4.. s'effondraient vers
                // l'origine de l'objet (Main oméga : rayons géants images 286-300)
                n = id == V_BONE ? std::min<size_t>(n, 12240 - v.off) : std::min<size_t>(v.taille, n);
                if (v.off + n > buf.size()) buf.resize(v.off + n, 0);
                memcpy(&buf[v.off], A.val[id].v.data(), n);
            }
        }
        if (deja) *deja = buf; else { out.push_back({c.slot, buf}); if (noms) noms->push_back(c.nom); }
    }
}

static bool visible_lod(const Dessin& D) {
    if (!D.a_inst) return D.lod != 2;
    double eye[3]; for (int i = 0; i < 3; i++) eye[i] = -(A.V[i * 4] * A.V[12] + A.V[i * 4 + 1] * A.V[13] + A.V[i * 4 + 2] * A.V[14]);
    double dx = D.inst[12] - eye[0], dy = D.inst[13] - eye[1], dz = D.inst[14] - eye[2], dist = sqrt(dx * dx + dy * dy + dz * dz);
    bool r = !std::isnan(D.lod_r);
    // (14/11/2026) LU (0x140527a80) : niveau = premier i avec d² < portée²[i] -> lv1 si d < portée, lv2 si d >= portée
    if (D.lod == 1) return !r || dist < D.lod_r;
    if (D.lod == 2) return r && dist >= D.lod_r;
    return true;
}

static ID3D11DepthStencilState* etat_profondeur(bool test, bool ecrire, int fonction = 4) {
    int k = (test ? 1 : 0) | (ecrire ? 2 : 0) | (fonction << 2);
    auto it = A.ds.find(k); if (it != A.ds.end()) return it->second;
    D3D11_DEPTH_STENCIL_DESC d = {}; d.DepthEnable = test; d.DepthWriteMask = ecrire ? D3D11_DEPTH_WRITE_MASK_ALL : D3D11_DEPTH_WRITE_MASK_ZERO;
    d.DepthFunc = (D3D11_COMPARISON_FUNC)fonction; d.StencilReadMask = d.StencilWriteMask = 0xFF;
    d.FrontFace = d.BackFace = {D3D11_STENCIL_OP_KEEP, D3D11_STENCIL_OP_KEEP, D3D11_STENCIL_OP_KEEP, D3D11_COMPARISON_ALWAYS};
    ID3D11DepthStencilState* s; OK(A.dev->CreateDepthStencilState(&d, &s), "depth"); A.ds[k] = s; return s;
}
static void etats(ID3D11BlendState* m, ID3D11DepthStencilState* d, ID3D11RasterizerState* r) {
    float zero[4] = {0, 0, 0, 0}; A.ctx->OMSetBlendState(m, zero, 0xFFFFFFFF); A.ctx->OMSetDepthStencilState(d, 0); A.ctx->RSSetState(r);
}
static void vider_srv() { ID3D11ShaderResourceView* nuls[20] = {}; A.ctx->PSSetShaderResources(0, 20, nuls); A.ctx->VSSetShaderResources(0, 20, nuls); }
static void sortie(ID3D11RenderTargetView* const* rtv, int n, ID3D11DepthStencilView* dsv, int w, int h) {
    A.ctx->OMSetRenderTargets(n, rtv, dsv); D3D11_VIEWPORT vp = {0, 0, (float)w, (float)h, 0, 1}; A.ctx->RSSetViewports(1, &vp);
}
static void sortie1(ID3D11RenderTargetView* rtv, ID3D11DepthStencilView* dsv, int w, int h) { sortie(&rtv, rtv ? 1 : 0, dsv, w, h); }
static bool t11Demi = false;                    // t11 = copie demi-taille (couches 40-49 de 40_Effect)
static void sortie_principale() { sortie1(A.hdr.rtv, A.dsv, A.W, A.H); }
static void sortie_mrt() { ID3D11RenderTargetView* r[4] = {A.hdr.rtv, A.mrt[0].rtv, A.mrt[1].rtv, A.mrt[2].rtv}; sortie(r, 4, A.dsv, A.W, A.H); }

// commun aux dessins du jeu : tampons, sommets, shaders, textures
static void lier_cbs(const Base& B, const Prog& P, const Lum* lum, bool stade) {
    static std::vector<std::pair<uint32_t, Octets>> cbs; tampons_cbs(B, P.etapes, 3, lum, cbs);
    for (auto& c : cbs) {
        if (stade && B.nomMat != UINT32_MAX)     // stade : u_ubParam.z = masque des cubemaps (entier) dans le tampon matériau
            for (int s = 0; s < 3; s++) for (const DefCb& d : P.etapes[s]) if (d.slot == c.first && d.nom == B.nomMat) { uint32_t m = 0xFFFFFFFF; memcpy(&c.second[8], &m, 4); }
        ID3D11Buffer* b = cb_dynamique(c.first, (uint32_t)((c.second.size() + 15) / 16 * 16), c.second);
        A.ctx->VSSetConstantBuffers(c.first, 1, &b); A.ctx->PSSetConstantBuffers(c.first, 1, &b);
        if (P.gso) A.ctx->GSSetConstantBuffers(c.first, 1, &b);
    }
}
static void lier_shaders(const Prog& P) { A.ctx->VSSetShader(P.vso, nullptr, 0); A.ctx->PSSetShader(P.pso, nullptr, 0); A.ctx->GSSetShader(P.gso, nullptr, 0); }
static void lier_textures(const Base& B, const Prog& P, const int32_t* tex, const uint32_t (*adr)[2]) {
    for (int k = 0; k < 6; k++) {
        ID3D11ShaderResourceView* v = tex[k] >= 0 ? B.tex[tex[k]] : A.blanc;
        ID3D11SamplerState* e = echantillonneur(adr[k][0], adr[k][1]);
        A.ctx->PSSetShaderResources(k, 1, &v); A.ctx->PSSetSamplers(k, 1, &e);
        if (P.vs_tex) { A.ctx->VSSetShaderResources(k, 1, &v); A.ctx->VSSetSamplers(k, 1, &e); }
        if (P.gso) { A.ctx->GSSetShaderResources(k, 1, &v); A.ctx->GSSetSamplers(k, 1, &e); }
    }
}
static void preparer(const Base& B, const Prog& P, const Geo& G, const Lum* lum, const int32_t* tex, const uint32_t (*adr)[2], bool stade) {
    lier_cbs(B, P, lum, stade);
    static const UINT zeros[16] = {};
    A.ctx->IASetInputLayout(P.disp);
    A.ctx->IASetVertexBuffers(0, (UINT)G.vb.size(), G.vb.data(), G.pas.data(), zeros);
    A.ctx->IASetIndexBuffer(G.ib, DXGI_FORMAT_R16_UINT, 0);
    A.ctx->IASetPrimitiveTopology(D3D11_PRIMITIVE_TOPOLOGY_TRIANGLELIST);
    lier_shaders(P);
    lier_textures(B, P, tex, adr);
    ID3D11SamplerState* e33 = echantillonneur(3, 3);
    A.ctx->PSSetShaderResources(11, 1, t11Demi ? &A.copieDemi.srv : &A.copie.srv); A.ctx->PSSetSamplers(11, 1, &e33);
    A.ctx->PSSetShaderResources(12, 1, &A.profScene); A.ctx->PSSetSamplers(12, 1, &e33);
}

// ------------------------------------------------------------------ décor
static bool csmActif = false; static ID3D11ShaderResourceView* t13Actif = nullptr;
static void dessiner_decor(const Dessin& D, const Lum* lum, const double* mvpCascade = nullptr) {
    const Prog& P = A.decor.progs[D.prog]; const Geo& G = A.decor.geos[D.geo];
    if (!G.ib || !G.n) return;
    valeurs_dessin(D.inst, D.ub, D.diffuse, D.ambient, D.uv, D.params, 0, nullptr);
    preparer(A.decor, P, G, lum, D.tex, D.adr, true);
    if (P.slotPL >= 0) A.ctx->PSSetConstantBuffers(P.slotPL, 1, &A.cb8);
    A.ctx->PSSetShaderResources(17, 1, &A.t17); A.ctx->PSSetShaderResources(18, 1, &A.t18);
    ID3D11SamplerState* e33 = echantillonneur(3, 3);
    if (A.cube) { A.ctx->PSSetShaderResources(14, 1, &A.cube); A.ctx->PSSetSamplers(14, 1, &e33);
        if (P.slotCube >= 0) A.ctx->PSSetConstantBuffers(P.slotCube, 1, &A.cb9); }
    ID3D11ShaderResourceView* t13 = t13Actif ? t13Actif : A.noir;
    A.ctx->PSSetShaderResources(13, 1, &t13); A.ctx->PSSetSamplers(13, 1, &e33);
    etats(D.passe == 1 ? A.mel[0] : A.mel[1], etat_profondeur(true, D.passe != 1), D.faces ? A.rasArriere : A.rasDouble);
    A.ctx->DrawIndexed(G.n, 0, 0);
    (void)mvpCascade;
}

// ------------------------------------------------------------------ personnages (acteurs.Acteur.peau + dessiner_acteur)
static void peau(PieceA& p, const std::vector<double>& mats) {
    // positions, normales, tangentes avec les matrices des os (monde animé x inverse du repos), en 64 bits comme numpy
    size_t nM = mats.size() / 16; if (!nM) return;
    std::vector<float> P(3 * p.nv), N(3 * p.nv), T(4 * p.nv);
    for (uint32_t v = 0; v < p.nv; v++) {
        double M[3][4] = {};                              // somme des poids x matrices (lignes)
        for (int k = 0; k < 4; k++) {
            double w = p.poids[4 * v + k]; size_t j = std::min<size_t>(p.os[4 * v + k], nM - 1); const double* m = &mats[16 * j];
            for (int r = 0; r < 3; r++) for (int c = 0; c < 4; c++) M[r][c] += w * m[c * 4 + r];
        }
        const float* x = &p.pos[3 * v]; const float* n = &p.nor[3 * v]; const float* t = &p.tan[4 * v];
        double nn[3], tt[3];
        for (int r = 0; r < 3; r++) {
            P[3 * v + r] = (float)(M[r][0] * x[0] + M[r][1] * x[1] + M[r][2] * x[2] + M[r][3]);
            nn[r] = M[r][0] * n[0] + M[r][1] * n[1] + M[r][2] * n[2];
            tt[r] = M[r][0] * t[0] + M[r][1] * t[1] + M[r][2] * t[2];
        }
        double ln = std::max(sqrt(nn[0] * nn[0] + nn[1] * nn[1] + nn[2] * nn[2]), 1e-9), lt = std::max(sqrt(tt[0] * tt[0] + tt[1] * tt[1] + tt[2] * tt[2]), 1e-9);
        for (int r = 0; r < 3; r++) { N[3 * v + r] = (float)(nn[r] / ln); T[4 * v + r] = (float)(tt[r] / lt); }
        T[4 * v + 3] = t[3];
    }
    maj_dyn(p.vbPos, P.data(), P.size() * 4); maj_dyn(p.vbNor, N.data(), N.size() * 4); maj_dyn(p.vbTan, T.data(), T.size() * 4);
}

static void sommets_acteur(const PieceA& p, const Prog& P) {
    std::vector<ID3D11Buffer*> vb; std::vector<UINT> pas;
    for (size_t e = 0; e < P.el.size(); e++) {
        const std::string& n = P.sem[e];
        if (n == "POSITION") { vb.push_back(p.vbPos); pas.push_back(12); }
        else if (n == "NORMAL") { vb.push_back(p.vbNor); pas.push_back(12); }
        else if (n == "TANGENT") { vb.push_back(p.vbTan); pas.push_back(16); }
        else if (n == "COLOR") { vb.push_back(p.vbCol); pas.push_back(4); }
        else if (n == "TEXCOORD") { vb.push_back(p.vbUv[std::min<UINT>(P.el[e].SemanticIndex, 5)]); pas.push_back(8); }
        else { vb.push_back(p.vbZero); pas.push_back(12); }
    }
    static const UINT zeros[16] = {};
    A.ctx->IASetInputLayout(P.disp);
    A.ctx->IASetVertexBuffers(0, (UINT)vb.size(), vb.data(), pas.data(), zeros);
    A.ctx->IASetIndexBuffer(p.ib, DXGI_FORMAT_R16_UINT, 0);
    A.ctx->IASetPrimitiveTopology(D3D11_PRIMITIVE_TOPOLOGY_TRIANGLELIST);
}

static void valeurs_acteur(const Image& im, const ActeurImage* a, bool cascade) {
    float blanc0[4] = {1, 1, 1, 0}, z4[4] = {0, 0, 0, 0};
    poser(V_SKIN, blanc0, 4); poser(V_HAIR, blanc0, 4); poser(V_SUB1, z4, 4); poser(V_SUB2, z4, 4); poser(V_PLH0, z4, 4); poser(V_PLH1, z4, 4);
    if (a && a->statut && !cascade) { poser(V_STCOL, a->st, 4); poser(V_STRIM, a->st + 4, 4); poser(V_STPOW, a->st + 8, 4); }
    if (csmActif) {
        const Ombres& o = im.om; std::vector<float> m; float l[16]; double t[16];
        for (int k = 0; k < 3; k++) { mul(GL_VERS_D3D, o.vp[k], t); lignes(t, l); m.insert(m.end(), l, l + 16); }
        poser(V_LIGHTWP, m.data(), m.size());
        float mm[12]; for (int k = 0; k < 3; k++) { mm[4 * k] = (float)o.tr[k][0]; mm[4 * k + 1] = (float)o.tr[k][1]; mm[4 * k + 2] = 0; mm[4 * k + 3] = 0; }
        poser(V_CASCMM, mm, 12);
        float T = (float)o.T, sp[4] = {T, T, 1.0f / T, 1.0f / T}; poser(V_SHSAMP, sp, 4);
    }
}

static void dessiner_acteur(const Image& im, const ActeurImage& a, PieceA& p, const Lum* lum, int cascade) {
    // cascade >= 0 : carte d'ombre (depth du jeu) ; sinon couleur (shader du matériau, 4 images écrites)
    int ip = cascade >= 0 ? A.speciaux[SP_DEPTH] : (a.statut && p.prog_st >= 0 ? p.prog_st : p.prog);
    if (ip < 0 || !p.ib) return;
    const Prog& P = A.eff.progs[ip];
    double mvpgl[16]; if (cascade >= 0) memcpy(mvpgl, im.om.vp[cascade], sizeof mvpgl); else mul(im.P, im.V, mvpgl);
    valeurs_camera(im.V, im.P, mvpgl, cascade < 0);
    float ub[4] = {1, 0, 0, 0};
    valeurs_dessin(ID, ub, p.diffuse, p.ambient, p.uv, p.params, 0, nullptr);
    valeurs_acteur(im, &a, cascade >= 0);
    std::vector<std::pair<uint32_t, Octets>> cbs; std::vector<uint32_t> nomsCb; tampons_cbs(A.eff, P.etapes, 3, lum, cbs, &nomsCb);
    // (15/11/2026) FONDU DU MODÈLE (commande 0x48A58CDC, valeur LUE) : le PS chr_toon* sort o0.w = alpha texture x sat(u_charaAmbient.w)
    // (cb7[0].w) ; on y met la valeur du fondu et la couleur (cible 0) est mélangée SRC_ALPHA / INV_SRC_ALPHA. APPROCHÉ : la façon
    // dont le jeu applique la valeur au dessin n'est pas encore lue (seul le seuil « pas dessiné si <= 0,001 » est LU).
    const bool fondu = cascade < 0 && a.alpha < 0.999f;
    if (fondu) for (size_t i = 0; i < cbs.size() && i < nomsCb.size(); i++) if (nomsCb[i] == A.eff.nomChara && cbs[i].second.size() >= 16) {
        float w; memcpy(&w, &cbs[i].second[12], 4); w *= a.alpha; memcpy(&cbs[i].second[12], &w, 4); }
    for (auto& c : cbs) { ID3D11Buffer* b = cb_dynamique(c.first, (uint32_t)((c.second.size() + 15) / 16 * 16), c.second);
        A.ctx->VSSetConstantBuffers(c.first, 1, &b); A.ctx->PSSetConstantBuffers(c.first, 1, &b); }
    sommets_acteur(p, P); lier_shaders(P);
    if (cascade < 0) {
        if (P.slotPL >= 0) A.ctx->PSSetConstantBuffers(P.slotPL, 1, &A.cb8);
        A.ctx->PSSetShaderResources(17, 1, &A.t17); A.ctx->PSSetShaderResources(18, 1, &A.t18);
        for (int k = 0; k < 6; k++) {
            ID3D11ShaderResourceView* v = p.tex[k] >= 0 ? A.eff.tex[p.tex[k]] : A.blanc; ID3D11SamplerState* e = echantillonneur(p.adr[k][0], p.adr[k][1]);
            A.ctx->VSSetShaderResources(k, 1, &v); A.ctx->VSSetSamplers(k, 1, &e); A.ctx->PSSetShaderResources(k, 1, &v); A.ctx->PSSetSamplers(k, 1, &e);
        }
        ID3D11SamplerState* e33 = echantillonneur(3, 3);
        ID3D11ShaderResourceView* grd = A.texSys[0] >= 0 ? A.eff.tex[A.texSys[0]] : A.blanc;
        A.ctx->PSSetShaderResources(7, 1, &grd); A.ctx->PSSetSamplers(7, 1, &e33);
        A.ctx->PSSetShaderResources(12, 1, &A.profScene); A.ctx->PSSetSamplers(12, 1, &e33);
        ID3D11ShaderResourceView* t13 = t13Actif ? t13Actif : A.noir; A.ctx->PSSetShaderResources(13, 1, &t13); A.ctx->PSSetSamplers(13, 1, &e33);
        if (csmActif) { A.ctx->PSSetShaderResources(15, 1, &A.csmSrv); A.ctx->PSSetSamplers(15, 1, &A.s15); }
        if (fondu && !A.melFondu) {           // cible 0 mélangée, les 3 autres (vitesse, masque, normale) écrites telles quelles
            D3D11_BLEND_DESC b = {}; b.IndependentBlendEnable = TRUE;
            for (int k = 0; k < 8; k++) b.RenderTarget[k].RenderTargetWriteMask = 0x0F;
            auto& r = b.RenderTarget[0]; r.BlendEnable = TRUE; r.SrcBlend = D3D11_BLEND_SRC_ALPHA; r.DestBlend = D3D11_BLEND_INV_SRC_ALPHA; r.BlendOp = D3D11_BLEND_OP_ADD;
            r.SrcBlendAlpha = D3D11_BLEND_ONE; r.DestBlendAlpha = D3D11_BLEND_INV_SRC_ALPHA; r.BlendOpAlpha = D3D11_BLEND_OP_ADD;
            OK(A.dev->CreateBlendState(&b, &A.melFondu), "fondu"); }
        etats(fondu ? A.melFondu : A.mel[0], etat_profondeur(true, true), p.faces ? A.rasArriere : A.rasDouble);
    } else {
        etats(A.mel[1], etat_profondeur(true, true), A.rasDouble);
    }
    A.ctx->DrawIndexed(p.n, 0, 0);
}

static ID3D11Buffer* cbNoir = nullptr;
// mode : 0 couleur noire, 1 profondeur seule, 2 masque des joueurs
static ID3D11Buffer* cbNoirSt = nullptr;
static void dessiner_noir(const Image& im, PieceA& p, int cascade, int mode, const ActeurImage* a = nullptr) {
    bool masque = mode == 2;
    // mannequin noir (choix de l'utilisateur dans l'Atelier) : sommets déjà placés, couleur noire ; ou profondeur seule
    if (!p.ib) return;
    double mvpgl[16], m[16]; if (cascade >= 0) memcpy(mvpgl, im.om.vp[cascade], sizeof mvpgl); else { mul(im.P, im.V, mvpgl); ligne0(mvpgl, echelle_x(im.P)); }
    mul(GL_VERS_D3D, mvpgl, m); float l[16]; lignes(m, l);
    maj_dyn(cbNoir, l, 64);
    static const UINT zeros[1] = {}; UINT pas = 12;
    A.ctx->IASetInputLayout(A.dispNoir); A.ctx->IASetVertexBuffers(0, 1, &p.vbPos, &pas, zeros);
    A.ctx->IASetIndexBuffer(p.ib, DXGI_FORMAT_R16_UINT, 0); A.ctx->IASetPrimitiveTopology(D3D11_PRIMITIVE_TOPOLOGY_TRIANGLELIST);
    A.ctx->VSSetShader(A.vsNoir, nullptr, 0); A.ctx->PSSetShader(masque ? A.psMasque : A.psNoir, nullptr, 0); A.ctx->GSSetShader(nullptr, nullptr, 0);
    A.ctx->VSSetConstantBuffers(0, 1, &cbNoir);
    if (mode == 0 && cascade < 0 && a && a->statut && A.psNoirSt) {   // (14/11/2026) aura du personnage sur le mannequin
        const double* Vw = im.V; float c[12] = {};
        for (int i = 0; i < 3; i++) c[i] = (float)-(Vw[i * 4] * Vw[12] + Vw[i * 4 + 1] * Vw[13] + Vw[i * 4 + 2] * Vw[14]);
        memcpy(c + 4, a->st + 4, 4 * sizeof(float)); memcpy(c + 8, a->st + 8, 4 * sizeof(float));
        maj_dyn(cbNoirSt, c, sizeof c);
        ID3D11Buffer* vb2[2] = {p.vbPos, p.vbNor}; UINT pas2[2] = {12, 12}, z2[2] = {0, 0};
        A.ctx->IASetInputLayout(A.dispNoirSt); A.ctx->IASetVertexBuffers(0, 2, vb2, pas2, z2);
        A.ctx->VSSetShader(A.vsNoirSt, nullptr, 0); A.ctx->PSSetShader(A.psNoirSt, nullptr, 0); A.ctx->PSSetConstantBuffers(1, 1, &cbNoirSt);
    }
    if (masque) etats(A.mel[0], etat_profondeur(true, false), A.rasDouble);
    else etats(cascade >= 0 || mode == 1 ? A.mel[1] : A.mel[0], etat_profondeur(true, true), A.rasDouble);
    A.ctx->DrawIndexed(p.n, 0, 0);
}

static void acteurs_passe(const Image& im, const Lum* lum, int cascade, bool profondeurSeule) {
    for (size_t j = 0; j < im.acteurs.size(); j++) { const ActeurImage& a = im.acteurs[j];
        if (a.modele >= A.modeles.size()) continue;
        auto& M = A.modeles[a.modele];
        for (uint32_t i : a.pieces) {
            if (i >= M.size() || !M[i].ib) continue; PieceA& p = M[i]; choisir_instance(p, j);
            if (p.noir || p.prog < 0 || profondeurSeule) dessiner_noir(im, p, cascade, profondeurSeule ? 1 : 0, &a);
            else dessiner_acteur(im, a, p, lum, cascade);
        }
    }
}

// ------------------------------------------------------------------ passes d'écran du jeu
static void quad_jeu(const Prog& P) {   // quadrilatère des passes (Python : quad / _ssao_c / _ct / _ciel)
    std::vector<ID3D11Buffer*> vb; std::vector<UINT> pas;
    for (size_t e = 0; e < P.el.size(); e++) {
        const std::string& n = P.sem[e];
        if (n == "POSITION") { vb.push_back(A.quadPos); pas.push_back(16); }
        else if (n == "TEXCOORD") { vb.push_back(A.quadUv); pas.push_back(8); }
        else { vb.push_back(A.quadCol); pas.push_back(4); }
    }
    static const UINT zeros[16] = {};
    A.ctx->IASetInputLayout(P.disp); A.ctx->IASetVertexBuffers(0, (UINT)vb.size(), vb.data(), pas.data(), zeros);
    A.ctx->IASetIndexBuffer(A.quadIb, DXGI_FORMAT_R16_UINT, 0); A.ctx->IASetPrimitiveTopology(D3D11_PRIMITIVE_TOPOLOGY_TRIANGLELIST);
}
// tampons calculés d'une passe (comme self.tampons(a, prog)) ; filtre : seulement CAMERA, ou tous sauf un slot
static void lier_cbs_passe(const Prog& P, const Lum* lum, bool vs, bool ps, bool seulementCam, int sauf = -1) {
    std::vector<std::pair<uint32_t, Octets>> cbs; std::vector<uint32_t> noms; tampons_cbs(A.eff, P.etapes, 3, lum, cbs, &noms);
    for (size_t i = 0; i < cbs.size(); i++) {
        if (seulementCam && noms[i] != A.eff.nomCam) continue;
        if ((int)cbs[i].first == sauf) continue;
        ID3D11Buffer* b = cb_dynamique(cbs[i].first, (uint32_t)((cbs[i].second.size() + 15) / 16 * 16), cbs[i].second);
        if (vs) A.ctx->VSSetConstantBuffers(cbs[i].first, 1, &b);
        if (ps) A.ctx->PSSetConstantBuffers(cbs[i].first, 1, &b);
    }
}

static void copier_profondeur() {   // (Rendu._copie_profondeur) -> A.profScene
    vider_srv(); sortie1(nullptr, nullptr, A.W, A.H); A.ctx->CopyResource(A.profCopieTex, A.prof);
}

static void scatter_jeu(const Image& im, const Lum* lum);
static ID3D11BlendState* melange(bool actif, D3D11_BLEND src, D3D11_BLEND dst, D3D11_BLEND_OP op, D3D11_BLEND sa, D3D11_BLEND da, UINT8 masque);
static void ombres_stade(const Image& im, const Lum* lum) {
    const Ombres& o = im.om; uint32_t T = o.T;
    if (!A.csmTex || A.csmT != T) {
        D3D11_TEXTURE2D_DESC d = {T, T, 1, 3, DXGI_FORMAT_R32_TYPELESS, {1, 0}, D3D11_USAGE_DEFAULT, D3D11_BIND_DEPTH_STENCIL | D3D11_BIND_SHADER_RESOURCE, 0, 0};
        OK(A.dev->CreateTexture2D(&d, nullptr, &A.csmTex), "cascades");
        for (int i = 0; i < 3; i++) { D3D11_DEPTH_STENCIL_VIEW_DESC v = {}; v.Format = DXGI_FORMAT_D32_FLOAT; v.ViewDimension = D3D11_DSV_DIMENSION_TEXTURE2DARRAY;
            v.Texture2DArray.FirstArraySlice = i; v.Texture2DArray.ArraySize = 1; OK(A.dev->CreateDepthStencilView(A.csmTex, &v, &A.csmDsv[i]), "cascade dsv"); }
        D3D11_SHADER_RESOURCE_VIEW_DESC s = {}; s.Format = DXGI_FORMAT_R32_FLOAT; s.ViewDimension = D3D11_SRV_DIMENSION_TEXTURE2DARRAY;
        s.Texture2DArray.MipLevels = 1; s.Texture2DArray.ArraySize = 3; OK(A.dev->CreateShaderResourceView(A.csmTex, &s, &A.csmSrv), "cascades srv");
        A.csmT = T;
    }
    csmActif = true;
    for (int k = 0; k < 3; k++) {
        vider_srv();
        A.ctx->ClearDepthStencilView(A.csmDsv[k], D3D11_CLEAR_DEPTH, 1.0f, 0);
        sortie1(nullptr, A.csmDsv[k], T, T);
        if (im.decor) {
            valeurs_camera(im.V, im.P, o.vp[k], false);
            for (const Dessin& D : A.dessins) if (D.passe == 2) dessiner_decor(D, lum);
        }
        acteurs_passe(im, lum, k, false);
    }
    // OMBRE DES EFFETS (t15 + u_mtxLightWP des shaders d'effets, Texture2D) : la cascade 0 (LU dans nie.exe 0x1413486d0)
    if (!A.csm0Tex) { D3D11_TEXTURE2D_DESC d = {T, T, 1, 1, DXGI_FORMAT_R32_TYPELESS, {1, 0}, D3D11_USAGE_DEFAULT, D3D11_BIND_SHADER_RESOURCE, 0, 0};
        OK(A.dev->CreateTexture2D(&d, nullptr, &A.csm0Tex), "cascade 0");
        D3D11_SHADER_RESOURCE_VIEW_DESC s = {}; s.Format = DXGI_FORMAT_R32_FLOAT; s.ViewDimension = D3D11_SRV_DIMENSION_TEXTURE2D; s.Texture2D.MipLevels = 1;
        OK(A.dev->CreateShaderResourceView(A.csm0Tex, &s, &A.csm0Srv), "cascade 0 srv"); }
    vider_srv(); sortie1(nullptr, nullptr, A.W, A.H);
    A.ctx->CopySubresourceRegion(A.csm0Tex, 0, 0, 0, 0, A.csmTex, 0, nullptr);
    memcpy(A.csm0vp, o.vp[0], sizeof A.csm0vp);
    // tampon cb12 (CBUSE_UB_USER_DATA02_IDX), disposition lue dans nie.exe 0x14133c9a0
    const double* V = im.V; double Vi[16]; inv4(V, Vi);
    double dv[3] = {V[0] * o.dir[0] + V[4] * o.dir[1] + V[8] * o.dir[2], V[1] * o.dir[0] + V[5] * o.dir[1] + V[9] * o.dir[2], V[2] * o.dir[0] + V[6] * o.dir[1] + V[10] * o.dir[2]};
    double near_ = o.tr[0][0], far2 = o.tr[2][1];
    std::vector<float> cb = {(float)dv[0], (float)dv[1], (float)dv[2], 0, (float)T, (float)T, 1.0f / T, 1.0f / T, (float)o.biais[0], (float)o.biais[1], (float)o.biais[2], 0,
                             (float)near_, (float)far2, (float)(1.0 / (far2 - near_)), 0, (float)A.W, (float)A.H, 1.0f / A.W, 1.0f / A.H};
    for (int k = 0; k < 3; k++) { cb.push_back((float)o.tr[k][0]); cb.push_back((float)o.tr[k][1]); cb.push_back(0); cb.push_back(0); }
    double mats[3][16]; for (int k = 0; k < 3; k++) { double t[16]; mul(GL_VERS_D3D, o.vp[k], t); mul(t, Vi, mats[k]); }
    float l[16];
    for (int k = 0; k < 3; k++) { lignes(mats[k], l); cb.insert(cb.end(), l, l + 16); }
    for (int k = 0; k < 3; k++) { double t[16]; inv4(mats[k], t); lignes(t, l); cb.insert(cb.end(), l, l + 16); }
    cb.resize((cb.size() + 3) / 4 * 4, 0.f);
    ID3D11Buffer* b12 = tampon(cb.data(), cb.size() * 4, D3D11_BIND_CONSTANT_BUFFER);
    // passe shadow_ss du jeu -> t13 (R et A)
    vider_srv();
    float zero[4] = {0, 0, 0, 0}; A.ctx->ClearRenderTargetView(A.t13.rtv, zero);
    sortie1(A.t13.rtv, nullptr, A.t13.w, A.t13.h);
    valeurs_passe(im, true);
    std::vector<std::pair<uint32_t, Octets>> cbs; std::vector<uint32_t> noms;
    tampons_cbs(A.eff, &A.psSeuls[PS_SS].cbs, 1, lum, cbs, &noms);
    for (size_t i = 0; i < cbs.size(); i++) if (noms[i] == A.eff.nomCam) {
        ID3D11Buffer* bb = cb_dynamique(cbs[i].first, (uint32_t)((cbs[i].second.size() + 15) / 16 * 16), cbs[i].second); A.ctx->PSSetConstantBuffers(cbs[i].first, 1, &bb); }
    A.ctx->PSSetConstantBuffers(12, 1, &b12);
    A.ctx->IASetInputLayout(nullptr); A.ctx->IASetPrimitiveTopology(D3D11_PRIMITIVE_TOPOLOGY_TRIANGLELIST);
    A.ctx->VSSetShader(A.vsSS, nullptr, 0); A.ctx->PSSetShader(A.psSeuls[PS_SS].ps, nullptr, 0); A.ctx->GSSetShader(nullptr, nullptr, 0);
    ID3D11SamplerState* e33 = echantillonneur(3, 3); ID3D11SamplerState* p33 = ech_point(3, 3);
    A.ctx->PSSetShaderResources(0, 1, &A.profScene); A.ctx->PSSetSamplers(0, 1, &e33);
    // (14/11/2026) LU (0x14133c9a0, r13 = 1) : cases 0 et 1 linéaires, case 1 bloquée au bord. Avant : point (DÉDUIT)
    { ID3D11SamplerState* l33 = echantillonneur(3, 3, 3); A.ctx->PSSetShaderResources(1, 1, &A.csmSrv); A.ctx->PSSetSamplers(1, 1, &l33); }
    etats(A.melR_A, etat_profondeur(false, false), A.rasDouble);
    A.ctx->Draw(3, 0);
    vider_srv(); b12->Release();
    t13Actif = A.t13.srv;
    scatter_jeu(im, lum);              // (14/11/2026) t13.z (LU 0x14133e290)
}

// SCATTER OCCLUSION DU JEU (14/11/2026, LU nie.exe 0x14133e290 + shaders scatter_occlusion*) -> t13.z (masque 4) :
// occlusion des rayons du brouillard par les ombres du soleil (map_pbrt1 : brouillard x sat(t13.z + u_fogWorldParam1.y)).
// A) profondeur reduite : RT_OneEighth (1/8, profondeur D32_FLOAT), 2d_direct + 2d_depth_nt, t1 = profondeur (lineaire),
//    profondeur ALWAYS ecrite, sans melange ;
// B) 128 tranches (0x1413444d0 : quad (-1..1) copie 128 fois, z = n / 128) dans l'attachement 2 de RT_OneEighth
//    (R16_UNORM, efface a 0), melange ONE / ONE (ADD), profondeur LESS_EQUAL sans ecriture ; cb0 = u_param (-Near, -Far,
//    Scale, 1/128) (CLightData +0xB70 / +0xB74 / +0xB68), u_upsampling (l, h, 0,5/l, 0,5/h), u_cascadeMinMax[3],
//    u_mtxVWtoShadowWP[3] ; t15 = cascades (comparaison, comme le jeu) ;
// C) 2d_direct + scatter_occlusion_upsampling -> t13 (masque 4 = B), t0 = occlusion, t1 = profondeur reduite,
//    t2 = profondeur ; echantillonneurs des cases 0-2 lineaires, sans profondeur.
static ID3D11Texture2D* scDepT = nullptr; static ID3D11DepthStencilView* scDepDsv = nullptr; static ID3D11ShaderResourceView* scDepSrv = nullptr;
static Cible scOcc; static ID3D11Buffer *scPos = nullptr, *scUv = nullptr, *scCol = nullptr, *scIb = nullptr;
static ID3D11BlendState *melAddOO = nullptr, *melB = nullptr;
static void scatter_jeu(const Image& im, const Lum* lum) {
    const float* r = lum->rg; const Ombres& o = im.om;
    if (r[R_SCAT] == 0 || !csmActif || !t13Actif || A.speciaux[SP_SCDEP] < 0 || A.speciaux[SP_SCAT] < 0 || A.speciaux[SP_SCUP] < 0) return;
    const int w8 = std::max(1, (int)(A.W * 0.125f)), h8 = std::max(1, (int)(A.H * 0.125f));
    if (!scDepT || scOcc.w != w8 || scOcc.h != h8) {
        if (scDepT) { scDepT->Release(); scDepDsv->Release(); scDepSrv->Release(); }
        D3D11_TEXTURE2D_DESC d = {(UINT)w8, (UINT)h8, 1, 1, DXGI_FORMAT_R32_TYPELESS, {1, 0}, D3D11_USAGE_DEFAULT, D3D11_BIND_DEPTH_STENCIL | D3D11_BIND_SHADER_RESOURCE, 0, 0};
        OK(A.dev->CreateTexture2D(&d, nullptr, &scDepT), "scatter profondeur");
        D3D11_DEPTH_STENCIL_VIEW_DESC v = {}; v.Format = DXGI_FORMAT_D32_FLOAT; v.ViewDimension = D3D11_DSV_DIMENSION_TEXTURE2D;
        OK(A.dev->CreateDepthStencilView(scDepT, &v, &scDepDsv), "scatter dsv");
        D3D11_SHADER_RESOURCE_VIEW_DESC sv = {}; sv.Format = DXGI_FORMAT_R32_FLOAT; sv.ViewDimension = D3D11_SRV_DIMENSION_TEXTURE2D; sv.Texture2D.MipLevels = 1;
        OK(A.dev->CreateShaderResourceView(scDepT, &sv, &scDepSrv), "scatter srv");
        scOcc = cible(w8, h8, DXGI_FORMAT_R16_UNORM);
    }
    if (!scPos) {                                   // 128 tranches, sommets du modele 0x141a420a0 (position, UV, couleur blanche)
        std::vector<float> pos, uv; std::vector<uint8_t> col; std::vector<uint16_t> ix;
        const float qx[4] = {-1, -1, 1, 1}, qy[4] = {1, -1, 1, -1}, qu[4] = {0, 0, 1, 1}, qv[4] = {0, 1, 0, 1};
        for (int t = 0; t < 128; t++) {
            for (int k = 0; k < 4; k++) { pos.insert(pos.end(), {qx[k], qy[k], t * 0.0078125f, 1.0f}); uv.insert(uv.end(), {qu[k], qv[k]});
                col.insert(col.end(), {(uint8_t)255, (uint8_t)255, (uint8_t)255, (uint8_t)255}); }
            const uint16_t b = (uint16_t)(4 * t);
            ix.insert(ix.end(), {b, (uint16_t)(b + 1), (uint16_t)(b + 2), (uint16_t)(b + 2), (uint16_t)(b + 1), (uint16_t)(b + 3)});
        }
        scPos = tampon(pos.data(), (UINT)(pos.size() * 4), D3D11_BIND_VERTEX_BUFFER); scUv = tampon(uv.data(), (UINT)(uv.size() * 4), D3D11_BIND_VERTEX_BUFFER);
        scCol = tampon(col.data(), (UINT)col.size(), D3D11_BIND_VERTEX_BUFFER); scIb = tampon(ix.data(), (UINT)(ix.size() * 2), D3D11_BIND_INDEX_BUFFER);
        melAddOO = melange(true, D3D11_BLEND_ONE, D3D11_BLEND_ONE, D3D11_BLEND_OP_ADD, D3D11_BLEND_ONE, D3D11_BLEND_ONE, 0x0F);
        melB = melange(false, D3D11_BLEND_ONE, D3D11_BLEND_ZERO, D3D11_BLEND_OP_ADD, D3D11_BLEND_ONE, D3D11_BLEND_ZERO, 4);
    }
    ID3D11SamplerState* l33 = echantillonneur(3, 3, 3);
    // A) profondeur reduite
    vider_srv();
    A.ctx->ClearDepthStencilView(scDepDsv, D3D11_CLEAR_DEPTH, 1.0f, 0);
    sortie1(nullptr, scDepDsv, w8, h8);
    { const Prog& P = A.eff.progs[A.speciaux[SP_SCDEP]]; lier_shaders(P); quad_jeu(P);
      A.ctx->PSSetShaderResources(1, 1, &A.profScene); A.ctx->PSSetSamplers(1, 1, &l33);
      etats(A.mel[1], etat_profondeur(true, true, 8), A.rasDouble); A.ctx->DrawIndexed(6, 0, 0); }
    // B) tranches
    vider_srv();
    const float z4[4] = {0, 0, 0, 0}; A.ctx->ClearRenderTargetView(scOcc.rtv, z4);
    sortie1(scOcc.rtv, scDepDsv, w8, h8);
    { const Prog& P = A.eff.progs[A.speciaux[SP_SCAT]]; lier_shaders(P);
      std::vector<ID3D11Buffer*> vb; std::vector<UINT> pas;
      for (size_t e = 0; e < P.el.size(); e++) { const std::string& n = P.sem[e];
          if (n == "POSITION") { vb.push_back(scPos); pas.push_back(16); } else if (n == "TEXCOORD") { vb.push_back(scUv); pas.push_back(8); }
          else { vb.push_back(scCol); pas.push_back(4); } }
      static const UINT zeros[16] = {};
      A.ctx->IASetInputLayout(P.disp); A.ctx->IASetVertexBuffers(0, (UINT)vb.size(), vb.data(), pas.data(), zeros);
      A.ctx->IASetIndexBuffer(scIb, DXGI_FORMAT_R16_UINT, 0); A.ctx->IASetPrimitiveTopology(D3D11_PRIMITIVE_TOPOLOGY_TRIANGLELIST);
      valeurs_passe(im, false); lier_cbs_passe(P, lum, true, true, true);
      const double* V = im.V; double Vi[16]; inv4(V, Vi);
      std::vector<float> cb = {-r[R_SCAT + 1], -r[R_SCAT + 2], r[R_SCAT], 0.0078125f, (float)w8, (float)h8, 0.5f / w8, 0.5f / h8};
      for (int k = 0; k < 3; k++) { cb.push_back((float)o.tr[k][0]); cb.push_back((float)o.tr[k][1]); cb.push_back(0); cb.push_back(0); }
      float l[16];
      for (int k = 0; k < 3; k++) { double t[16], m[16]; mul(GL_VERS_D3D, o.vp[k], t); mul(t, Vi, m); lignes(m, l); cb.insert(cb.end(), l, l + 16); }
      ID3D11Buffer* b0 = cb_valeurs(cb.data(), cb.size()); A.ctx->VSSetConstantBuffers(0, 1, &b0); A.ctx->PSSetConstantBuffers(0, 1, &b0);
      A.ctx->PSSetShaderResources(15, 1, &A.csmSrv); A.ctx->PSSetSamplers(15, 1, &A.s15);
      etats(melAddOO, etat_profondeur(true, false, 4), A.rasDouble); A.ctx->DrawIndexed(6 * 128, 0, 0); }
    // C) suréchantillonnage -> t13.z
    vider_srv();
    sortie1(A.t13.rtv, nullptr, A.t13.w, A.t13.h);
    { const Prog& P = A.eff.progs[A.speciaux[SP_SCUP]]; lier_shaders(P); quad_jeu(P);
      valeurs_passe(im, false); lier_cbs_passe(P, lum, false, true, true);
      float cb[8] = {-r[R_SCAT + 1], -r[R_SCAT + 2], r[R_SCAT], 0.0078125f, (float)w8, (float)h8, 0.5f / w8, 0.5f / h8};
      ID3D11Buffer* b0 = cb_valeurs(cb, 8); A.ctx->PSSetConstantBuffers(0, 1, &b0);
      ID3D11ShaderResourceView* t[3] = {scOcc.srv, scDepSrv, A.profScene};
      for (int k = 0; k < 3; k++) { A.ctx->PSSetShaderResources(k, 1, &t[k]); A.ctx->PSSetSamplers(k, 1, &l33); }
      etats(melB, etat_profondeur(false, false), A.rasDouble); A.ctx->DrawIndexed(6, 0, 0); }
    vider_srv(); sortie1(nullptr, nullptr, A.W, A.H);
    if (getenv("LECTEUR_CONTROLE_T13")) {           // contrôle (essais) : min / moyenne / max de t13.z -> controle_t13.txt
        ID3D11Resource* res; A.t13.srv->GetResource(&res); ID3D11Texture2D* tx = (ID3D11Texture2D*)res; D3D11_TEXTURE2D_DESC d; tx->GetDesc(&d);
        d.Usage = D3D11_USAGE_STAGING; d.BindFlags = 0; d.CPUAccessFlags = D3D11_CPU_ACCESS_READ; d.MiscFlags = 0; ID3D11Texture2D* st;
        if (SUCCEEDED(A.dev->CreateTexture2D(&d, nullptr, &st))) { A.ctx->CopyResource(st, tx); D3D11_MAPPED_SUBRESOURCE m;
            if (SUCCEEDED(A.ctx->Map(st, 0, D3D11_MAP_READ, 0, &m))) { double mn = 1e9, mx = -1e9, sm = 0; size_t n = 0;
                for (UINT y = 0; y < d.Height; y++) { const uint16_t* row = (const uint16_t*)((const uint8_t*)m.pData + y * m.RowPitch);
                    for (UINT x = 0; x < d.Width; x++) { const uint16_t hz = row[4 * x + 2]; const int e = (hz >> 10) & 31, f = hz & 1023;
                        const double z = e == 0 ? f / 16777216.0 : ldexp(1.0 + f / 1024.0, e - 15); mn = std::min(mn, z); mx = std::max(mx, z); sm += z; n++; } }
                A.ctx->Unmap(st, 0); FILE* x = fopen("controle_t13.txt", "a");
                if (x) { fprintf(x, "t13.z min %.4f moy %.4f max %.4f (Scale %.3g Near %.3g Far %.3g)\n", mn, sm / std::max<size_t>(n, 1), mx, r[R_SCAT], r[R_SCAT + 1], r[R_SCAT + 2]); fclose(x); } }
            st->Release(); }
        res->Release(); }
}

// NORMALE SIMPLE DU SSAO (14/11/2026, LU 0x14133c510) : RT_Half att5 (RGBA8, demi-taille), VS 2d_direct + PS simple_nrm_from_dep,
// t0 = profondeur (case 0 linéaire, bloquée), cb0 = u_screenSizeParam (l, h, 1/l, 1/h) de RT_Half, sans mélange (masque 0x0F).
static bool snrm_jeu(const Image& im, const Lum* lum) {
    if (A.speciaux[SP_SNRM] < 0) return false;
    if (!A.snrm.t || A.snrm.w != A.t13.w || A.snrm.h != A.t13.h) A.snrm = cible(A.t13.w, A.t13.h, DXGI_FORMAT_R8G8B8A8_UNORM);
    const Prog& P = A.eff.progs[A.speciaux[SP_SNRM]];
    vider_srv(); sortie1(A.snrm.rtv, nullptr, A.snrm.w, A.snrm.h);
    lier_shaders(P); quad_jeu(P);
    valeurs_passe(im, false); lier_cbs_passe(P, lum, false, true, true);
    float c[4] = {(float)A.snrm.w, (float)A.snrm.h, 1.0f / A.snrm.w, 1.0f / A.snrm.h};
    ID3D11Buffer* b = cb_valeurs(c, 4); A.ctx->PSSetConstantBuffers(0, 1, &b);
    ID3D11SamplerState* l33 = echantillonneur(3, 3, 3); A.ctx->PSSetShaderResources(0, 1, &A.profScene); A.ctx->PSSetSamplers(0, 1, &l33);
    etats(A.mel[0], etat_profondeur(false, false), A.rasDouble); A.ctx->DrawIndexed(6, 0, 0);
    vider_srv();
    return true;
}

// FLOU BILATÉRAL DE PRESHADING (14/11/2026, LU 0x14133b950, technique « bilateral » de pre_shading_composite :
// VS gauss_l + PS pre_shading_bilateral). Réglages CLightData : shadingBlurOffset +0x1D28 (2), shadingBlurParam +0x1D30
// (sigma, p, q), shadingBlurCount +0x1D40 (min 32), octet +0x1D44 (autre chemin, non fait : 0 par défaut).
// Par itération : att0 -> att1 avec u_offs (dx, 0, dx/2, 0), puis att1 -> att0 avec (0, dy, 0, dy/2) ; dx = offset.x / largeur
// de RT_PreShading ; u_color = 1 ; u_weight0 = exp(-(k+0,5)^2 / (2 sigma^2)), k = 0..3 (constantes -0,125 / -1,125 / -3,125 /
// -6,125, expf 0x140a07cd0) ; u_weight1 = 0 ; u_bilateral = ((-0,5 / p) x p, q, 0, 0) si q > 0 (sinon tampon de 0x40 octets).
// cb0 (PS) = u_shardingNearFar (scène +0x8E0, +0xAF4, 1 / (loin - près)), comme l'ombre à l'écran. Sans mélange ni profondeur.
static void flou_preshading(const Image& im, const Lum* lum) {
    if (!t13Actif || A.speciaux[SP_BILAT] < 0 || lum->img.size() < 0x1D48) return;
    const uint8_t* c = lum->img.data(); float off[2], prm[3]; uint32_t n; memcpy(off, c + 0x1D28, 8); memcpy(prm, c + 0x1D30, 12); memcpy(&n, c + 0x1D40, 4);
    if (!n || c[0x1D44]) return;
    n = std::min<uint32_t>(n, 32);
    if (!A.t13b.t || A.t13b.w != A.t13.w || A.t13b.h != A.t13.h) A.t13b = cible(A.t13.w, A.t13.h, DXGI_FORMAT_R16G16B16A16_FLOAT);
    const float s2 = 1.0f / (prm[0] * prm[0]);
    const float w[4] = {expf(s2 * -0.125f), expf(s2 * -1.125f), expf(s2 * -3.125f), expf(s2 * -6.125f)};
    const float bx = prm[2] > 0 ? (-0.5f / prm[1]) * prm[1] : 0.0f, by = prm[2] > 0 ? prm[2] : 0.0f;
    const float dx = off[0] / A.t13.w, dy = off[1] / A.t13.h;
    float cbH[20] = {dx, 0, dx * 0.5f, 0, 1, 1, 1, 1, w[0], w[1], w[2], w[3], 0, 0, 0, 0, bx, by, 0, 0};
    float cbV[20] = {0, dy, 0, dy * 0.5f, 1, 1, 1, 1, w[0], w[1], w[2], w[3], 0, 0, 0, 0, bx, by, 0, 0};
    const Ombres& o = im.om; const double near_ = o.tr[0][0], far2 = o.tr[2][1];
    float nf[4] = {(float)near_, (float)far2, (float)(1.0 / (far2 - near_)), prm[2]};
    const Prog& P = A.eff.progs[A.speciaux[SP_BILAT]];
    ID3D11SamplerState* l33 = echantillonneur(3, 3, 3);
    for (uint32_t it = 0; it < n; it++)
        for (int sens = 0; sens < 2; sens++) {
            vider_srv();
            Cible& dst = sens == 0 ? A.t13b : A.t13; Cible& src = sens == 0 ? A.t13 : A.t13b;
            sortie1(dst.rtv, nullptr, dst.w, dst.h); lier_shaders(P); quad_jeu(P);
            ID3D11Buffer* b6 = cb_valeurs(sens == 0 ? cbH : cbV, 20); A.ctx->VSSetConstantBuffers(6, 1, &b6); A.ctx->PSSetConstantBuffers(6, 1, &b6);
            ID3D11Buffer* b0 = cb_valeurs(nf, 4); A.ctx->PSSetConstantBuffers(0, 1, &b0);
            A.ctx->PSSetShaderResources(0, 1, &src.srv); A.ctx->PSSetSamplers(0, 1, &l33);
            etats(A.mel[0], etat_profondeur(false, false), A.rasDouble); A.ctx->DrawIndexed(6, 0, 0);
        }
    vider_srv(); sortie1(nullptr, nullptr, A.W, A.H);
}

static bool ssao_jeu(const Image& im, const Lum* lum) {
    const float* r = lum->rg;
    if (!r[R_SSAO] || !t13Actif || A.speciaux[SP_SSAO] < 0) return false;
    copier_profondeur();
    const Prog& P = A.eff.progs[A.speciaux[SP_SSAO]];
    float cb0[20]; memcpy(cb0, r + R_SSAO + 1, 16 * 4);
    cb0[16] = (float)A.t13.w; cb0[17] = (float)A.t13.h; cb0[18] = 1.0f / A.t13.w; cb0[19] = 1.0f / A.t13.h;
    sortie1(A.t13.rtv, nullptr, A.t13.w, A.t13.h);
    lier_shaders(P); quad_jeu(P);
    valeurs_passe(im, false); lier_cbs_passe(P, lum, false, true, false);
    ID3D11Buffer* b0 = cb_valeurs(cb0, 20); A.ctx->PSSetConstantBuffers(0, 1, &b0);
    ID3D11SamplerState* p33 = ech_point(3, 3); ID3D11SamplerState* e33 = echantillonneur(3, 3);
    // (14/11/2026) LU (SSAO 0x14133d6a0 : case 0 bloquée au bord, filtre r12 = 1 linéaire ; case 2 bloquée). Avant : point (DÉDUIT)
    { ID3D11SamplerState* l33 = echantillonneur(3, 3, 3); A.ctx->PSSetShaderResources(0, 1, &A.profScene); A.ctx->PSSetSamplers(0, 1, &l33); }
    // (14/11/2026) LU : la case 2 du SSAO = RT_Half att5 (+0x39B0), « normale simple » écrite juste avant par 0x14133c510
    // (simple_nrm_from_dep : normale de facette reconstruite depuis la profondeur, tournée vers la caméra, x 0,5 + 0,5).
    // Avant : normale du G-buffer (mrt[2], avec cartes de normales), DÉDUIT. Repli sur mrt[2] si le programme manque.
    ID3D11ShaderResourceView* nrm = snrm_jeu(im, lum) ? A.snrm.srv : A.mrt[2].srv;
    sortie1(A.t13.rtv, nullptr, A.t13.w, A.t13.h); lier_shaders(P); quad_jeu(P);
    valeurs_passe(im, false); lier_cbs_passe(P, lum, false, true, false); A.ctx->PSSetConstantBuffers(0, 1, &b0);
    { ID3D11SamplerState* l33 = echantillonneur(3, 3, 3); A.ctx->PSSetShaderResources(0, 1, &A.profScene); A.ctx->PSSetSamplers(0, 1, &l33); }
    A.ctx->PSSetShaderResources(2, 1, &nrm); A.ctx->PSSetSamplers(2, 1, &e33);
    etats(A.melG, etat_profondeur(false, false), A.rasDouble);
    A.ctx->DrawIndexed(6, 0, 0);
    vider_srv();
    return true;
}

static bool pieds_jeu(const Image& im, const Lum* lum) {
    float rate = lum->rg[R_PIEDS];
    if (im.pieds.empty() || rate <= 0 || !t13Actif || A.speciaux[SP_PIEDS] < 0) return false;
    copier_profondeur();
    const Prog& P = A.eff.progs[A.speciaux[SP_PIEDS]];
    sortie1(A.t13.rtv, nullptr, A.t13.w, A.t13.h);
    lier_shaders(P);
    static const UINT z[1] = {}; UINT pas = 12;
    A.ctx->IASetInputLayout(P.disp); A.ctx->IASetVertexBuffers(0, 1, &A.cubeVb, &pas, z);
    A.ctx->IASetIndexBuffer(A.cubeIb, DXGI_FORMAT_R16_UINT, 0); A.ctx->IASetPrimitiveTopology(D3D11_PRIMITIVE_TOPOLOGY_TRIANGLELIST);
    valeurs_passe(im, false); lier_cbs_passe(P, lum, true, true, true);
    float r4[4] = {rate, rate, rate, rate}; ID3D11Buffer* b1 = cb_valeurs(r4, 4); A.ctx->PSSetConstantBuffers(1, 1, &b1);
    // (14/11/2026) LU : l'ombre des pieds est dessinée dans la fonction du SSAO (0x14133d6a0, instances +0x3000 / +0x3008),
    // après lui, avec ses échantillonneurs : case 0 bloquée au bord, linéaire. Avant : point (DÉDUIT)
    ID3D11SamplerState* p33 = echantillonneur(3, 3, 3);
    A.ctx->PSSetShaderResources(0, 1, &A.profScene); A.ctx->PSSetSamplers(0, 1, &p33);
    etats(A.melGAdd, etat_profondeur(false, false), A.rasDouble);
    for (size_t i = 0; i + 12 <= im.pieds.size(); i += 12) {
        // A4 = 3 lignes + (0 0 0 1) ; inverse (lu comme colonnes : inverse de la transposée = transposée de l'inverse)
        double a4[16]; for (int k = 0; k < 12; k++) a4[k] = im.pieds[i + k]; a4[12] = a4[13] = a4[14] = 0; a4[15] = 1;
        double ai[16]; if (!inv4(a4, ai)) continue;
        float cb[24]; for (int k = 0; k < 12; k++) { cb[k] = (float)a4[k]; cb[12 + k] = (float)ai[k]; }
        ID3D11Buffer* b0 = cb_valeurs(cb, 24); A.ctx->VSSetConstantBuffers(0, 1, &b0); A.ctx->PSSetConstantBuffers(0, 1, &b0);
        A.ctx->DrawIndexed(36, 0, 0);
    }
    vider_srv();
    return true;
}

static void ciel_jeu(const Image& im, const Lum* lum) {
    if (!lum->rg[R_CIEL] || A.speciaux[SP_CIEL] < 0) return;
    const Prog& P = A.eff.progs[A.speciaux[SP_CIEL]];
    sortie_principale();
    lier_shaders(P); quad_jeu(P);
    valeurs_passe(im, false); lier_cbs_passe(P, lum, true, true, false);
    float c0[4] = {0, 0, lum->rg[R_CIELR], 0}; ID3D11Buffer* b0 = cb_valeurs(c0, 4); A.ctx->VSSetConstantBuffers(0, 1, &b0); A.ctx->PSSetConstantBuffers(0, 1, &b0);
    ID3D11SamplerState* p33 = ech_point(3, 3); ID3D11SamplerState* e33 = echantillonneur(3, 3);
    // (14/11/2026) LU : la passe du ciel (0x141338920, shader rangé en +0x515C) ne change aucun échantillonneur -> état par
    // défaut, linéaire et bloqué au bord. Avant : point (DÉDUIT)
    A.ctx->PSSetShaderResources(12, 1, &A.profScene); A.ctx->PSSetSamplers(12, 1, &e33);
    ID3D11ShaderResourceView* t13 = t13Actif ? t13Actif : A.noir; A.ctx->PSSetShaderResources(13, 1, &t13); A.ctx->PSSetSamplers(13, 1, &e33);
    // (14/11/2026) LU (0x141338920, état courant = +0xEC3 + clé) : test de profondeur 1 (clé 4), écriture 0 (clé 5), faces
    // arrière retirées (clé 0x1B = 3, comme le défaut +0xEBB : le quad du ciel est de face), clé 0x10 = 0 ; mélange et masque
    // non changés -> état par défaut (sans mélange, masque 0x0F = RVBA). Avant : RVB seulement (DÉDUIT)
    etats(A.mel[0], etat_profondeur(true, false), A.rasDouble);
    A.ctx->DrawIndexed(6, 0, 0);
    vider_srv();
}

static void contour_jeu(const Image& im, const Lum* lum) {
    if (A.speciaux[SP_EDGE] < 0 || A.speciaux[SP_TONE] < 0 || A.speciaux[SP_COMPOSI] < 0) return;
    const Octets& L = lum->img;
    auto f4 = [&](size_t o, float* v) { memcpy(v, &L[o], 16); };
    float ec[4], w0[4], w1[4], x9[4]; f4(0x9A0, ec); f4(0x9B0, w0); f4(0x9C0, w1); f4(0x9D0, x9);
    float fb = x9[0], fe = x9[1], x9dc = x9[3];
    copier_profondeur();
    float w = (float)A.W, h = (float)A.H, k = 4.0f * (1 + std::min(std::max(h / 540.0f - 1, 0.0f), 1.0f));
    float taille[4] = {w, h, 1 / w, 1 / h};
    ID3D11ShaderResourceView* tone = A.texSys[1] >= 0 ? A.eff.tex[A.texSys[1]] : A.blanc;
    // (14/11/2026) échantillonneurs LUS (0x141337285) : état par défaut du moteur = linéaire, bloqué au bord (modèle +0x1140
    // posé par 0x14049fa80, chaque passe le sauve / le rend : 0x1404a1370) ; le contour ne change que la case 2 (profondeur) :
    // linéaire à la 1re passe (0x140093bd0(ctx, 2, 4/5, 1)), POINT à la 3e (… 0). Avant : point partout (DÉDUIT).
    ID3D11SamplerState* p33 = ech_point(3, 3); ID3D11SamplerState* e33 = echantillonneur(3, 3, 3);
    float zero[4] = {0, 0, 0, 0};
    for (int pass = 0; pass < 3; pass++) {
        const Prog& P = A.eff.progs[A.speciaux[SP_EDGE + pass]];
        if (pass < 2) { A.ctx->ClearRenderTargetView(A.temp[pass].rtv, zero); sortie1(A.temp[pass].rtv, nullptr, A.W, A.H); }
        else sortie_principale();
        lier_shaders(P); quad_jeu(P);
        valeurs_passe(im, true); lier_cbs_passe(P, lum, false, true, false);
        std::vector<float> c0;
        if (pass == 0) { c0.insert(c0.end(), taille, taille + 4); c0.insert(c0.end(), w0, w0 + 4); c0.insert(c0.end(), w1, w1 + 3); c0.push_back(0); }
        else if (pass == 1) c0.insert(c0.end(), taille, taille + 4);
        else { c0.insert(c0.end(), ec, ec + 4); float t2[4] = {1 / w, 1 / h, 0.5f / w, 0.5f / h}; c0.insert(c0.end(), t2, t2 + 4); }
        ID3D11Buffer* b0 = cb_valeurs(c0.data(), c0.size()); A.ctx->PSSetConstantBuffers(0, 1, &b0);
        if (pass == 2) { float c2[12] = {1 / w, 1 / h, 0.5f / w, 0.5f / h, fb, (fe - fb) > 0 ? 1 / (fe - fb) : 0.0f, k * 0.25f, 1 / k, x9dc, 0, 0, 0};
            ID3D11Buffer* b2 = cb_valeurs(c2, 12); A.ctx->PSSetConstantBuffers(2, 1, &b2); }
        if (pass == 0) { ID3D11ShaderResourceView* s[3] = {A.mrt[1].srv, A.mrt[2].srv, A.profScene}; for (int i = 0; i < 3; i++) { A.ctx->PSSetShaderResources(i, 1, &s[i]); A.ctx->PSSetSamplers(i, 1, &e33); } }
        if (pass == 1) { A.ctx->PSSetShaderResources(3, 1, &A.temp[0].srv); A.ctx->PSSetSamplers(3, 1, &e33); A.ctx->PSSetShaderResources(4, 1, &tone); A.ctx->PSSetSamplers(4, 1, &e33); }
        if (pass == 2) { A.ctx->PSSetShaderResources(2, 1, &A.profScene); A.ctx->PSSetSamplers(2, 1, &p33); A.ctx->PSSetShaderResources(3, 1, &A.temp[1].srv); A.ctx->PSSetSamplers(3, 1, &e33); }
        if (pass < 2) etats(A.mel[0], etat_profondeur(false, false), A.rasDouble);
        else etats(A.melMul, etat_profondeur(true, true, 8), A.rasDouble);
        A.ctx->DrawIndexed(6, 0, 0);
        vider_srv();
    }
}

static void dof_jeu(const Image& im, const Lum* lum, ID3D11ShaderResourceView* src, ID3D11RenderTargetView* dst) {
    const float* r = lum->rg;
    int cnt = (int)r[R_DOFCNT];
    if (cnt <= 0 || A.speciaux[SP_GAUSS] < 0 || A.speciaux[SP_DOF] < 0) return;
    double nz = r[R_NZ], fz = r[R_FZ], fin = r[R_FIN], fout = r[R_FOUT], front = r[R_FRONT], back = r[R_BACK];
    double n = 0.05, f = 8000; const double* P = im.P;
    if (fabs(P[11] + 1) <= 1e-6 && P[0] && P[5]) { n = P[14] / (P[10] - 1); f = P[14] / (P[10] + 1); }
    double a_, b_, p, q;
    if (!r[R_AUTO]) { b_ = fout + fz; a_ = nz - fin; q = b_ - a_; if (q) { p = fin / q; q = fout / q; } else { p = 0; q = 0; } }
    else { double F = im.foyer; double f12 = F * nz; p = F * fin; double f13 = f12 * fz; q = p * fout;
           a_ = (F - f12) - p; b_ = f13 + F + q; double s = q + p + f13 + f12; if (s) { p /= s; q /= s; } else { p = 0; q = 0; } }
    float cbps[12] = {(float)(n * f), (float)(n - f), (float)(n - a_), (float)(b_ != a_ ? 1 / (b_ - a_) : 0.0), (float)p, (float)(1 - q),
                      (float)(p ? 1 / p : 0.0), (float)(q ? 1 / q : 0.0), (float)front, (float)back, 0, 0};
    copier_profondeur();
    int hw = A.dofMi[0].w, hh = A.dofMi[0].h;
    ID3D11SamplerState* e33 = echantillonneur(3, 3); ID3D11SamplerState* p33 = ech_point(3, 3);
    // 1. copie à mi-taille
    sortie1(A.dofMi[0].rtv, nullptr, hw, hh);
    A.ctx->IASetInputLayout(nullptr); A.ctx->VSSetShader(A.vsSS, nullptr, 0); A.ctx->PSSetShader(A.psCopieV2, nullptr, 0); A.ctx->GSSetShader(nullptr, nullptr, 0);
    A.ctx->PSSetShaderResources(0, 1, &src); A.ctx->PSSetSamplers(0, 1, &e33);
    etats(A.mel[0], etat_profondeur(false, false), A.rasDouble); A.ctx->Draw(3, 0);
    // 2. flou gaussien du jeu
    double sig = r[R_GP1] ? r[R_GP1] : 2.0, ws[8]; ws[0] = 1; double tot = 1;
    for (int i = 1; i < 8; i++) { ws[i] = exp(-0.5 * i * i / (sig * sig)); tot += ws[i]; }
    tot *= 2;
    const Prog& G = A.eff.progs[A.speciaux[SP_GAUSS]];
    for (int c = 0; c < cnt; c++) for (int d = 0; d < 2; d++) {
        Cible& s = d == 0 ? A.dofMi[0] : A.dofMi[1]; Cible& t = d == 0 ? A.dofMi[1] : A.dofMi[0];
        vider_srv(); sortie1(t.rtv, nullptr, hw, hh);
        lier_shaders(G); quad_jeu(G);
        float cb[16] = {d == 0 ? (float)(r[R_GP0] / hw) : 0, d == 1 ? (float)(r[R_GP0] / hh) : 0, 0, 0, 1, 1, 1, 1};
        for (int i = 0; i < 8; i++) cb[8 + i] = (float)(ws[i] / tot);
        ID3D11Buffer* b = cb_valeurs(cb, 16); A.ctx->VSSetConstantBuffers(6, 1, &b); A.ctx->PSSetConstantBuffers(6, 1, &b);
        A.ctx->PSSetShaderResources(0, 1, &s.srv); A.ctx->PSSetSamplers(0, 1, &e33);
        etats(A.mel[0], etat_profondeur(false, false), A.rasDouble); A.ctx->DrawIndexed(6, 0, 0);
    }
    // 3. composite depth_of_field
    vider_srv(); sortie1(dst, nullptr, A.W, A.H);
    const Prog& Df = A.eff.progs[A.speciaux[SP_DOF]];
    lier_shaders(Df); quad_jeu(Df);
    valeurs_passe(im, false); lier_cbs_passe(Df, lum, false, true, false, 6);
    float vo[4] = {(float)(r[R_TEXOFF] / A.W), (float)(r[R_TEXOFF] / A.H), 0, 0};
    ID3D11Buffer* bv = cb_valeurs(vo, 4); A.ctx->VSSetConstantBuffers(6, 1, &bv);
    ID3D11Buffer* bp = cb_valeurs(cbps, 12); A.ctx->PSSetConstantBuffers(6, 1, &bp);
    A.ctx->PSSetShaderResources(0, 1, &A.dofMi[0].srv); A.ctx->PSSetSamplers(0, 1, &e33);
    // (14/11/2026) LU : profondeur de champ sans réglage propre (0x141331ba0) = état par défaut linéaire ; 0x141332b73 met la
    // case 1 en linéaire. Avant : point (DÉDUIT)
    A.ctx->PSSetShaderResources(1, 1, &A.profScene); A.ctx->PSSetSamplers(1, 1, &e33);
    etats(A.melDof, etat_profondeur(false, false), A.rasDouble); A.ctx->DrawIndexed(6, 0, 0);
    vider_srv();
}

// effets d'écran (post.py) : passe plein écran avec un VS de l'Atelier
static void passe(ID3D11RenderTargetView* rtv, int w, int h, ID3D11VertexShader* vs, ID3D11PixelShader* ps, std::vector<ID3D11ShaderResourceView*> srvs,
                  const float* cb6, size_t n6, const float* cb0, size_t n0, ID3D11BlendState* m = nullptr) {
    vider_srv(); sortie1(rtv, nullptr, w, h);
    A.ctx->IASetInputLayout(nullptr); A.ctx->IASetPrimitiveTopology(D3D11_PRIMITIVE_TOPOLOGY_TRIANGLELIST);
    A.ctx->VSSetShader(vs, nullptr, 0); A.ctx->PSSetShader(ps, nullptr, 0); A.ctx->GSSetShader(nullptr, nullptr, 0);
    ID3D11SamplerState* lin = echantillonneur(3, 3, 3);
    for (size_t k = 0; k < srvs.size(); k++) { A.ctx->PSSetShaderResources((UINT)k, 1, &srvs[k]); A.ctx->PSSetSamplers((UINT)k, 1, &lin); }
    if (cb6) { ID3D11Buffer* b = cb_valeurs(cb6, n6); A.ctx->VSSetConstantBuffers(6, 1, &b); A.ctx->PSSetConstantBuffers(6, 1, &b); }
    if (cb0) { ID3D11Buffer* b = cb_valeurs(cb0, n0); A.ctx->PSSetConstantBuffers(0, 1, &b); }
    etats(m ? m : A.mel[0], etat_profondeur(false, false), A.rasDouble);
    if (m && m == A.melTaa) { float f[4] = {0.3f, 0.3f, 0.3f, 0.3f}; A.ctx->OMSetBlendState(m, f, 0xFFFFFFFF); }
    A.ctx->Draw(3, 0);
}

static void effets_ecran(const Image& im, const Lum* lum) {
    const float* r = lum->rg;
    // 1. luminosité moyenne (grille 64 x 64, comme cs_tex_reduction) puis adaptation dans le temps (cs_buffer_lerp)
    passe(A.lumC.rtv, 64, 64, A.vs1, A.psLum, {A.hdr.srv}, nullptr, 0, nullptr, 0);
    vider_srv(); A.ctx->GenerateMips(A.lumC.srv);
    float cs[4] = {r[R_TAUX], A.premiere ? 1.0f : 0.0f, 0, 0}; A.premiere = false;
    ID3D11Buffer* bcs = cb_valeurs(cs, 4);
    A.ctx->CSSetShader(A.csAdapt, nullptr, 0); A.ctx->CSSetConstantBuffers(0, 1, &bcs);
    A.ctx->CSSetShaderResources(0, 1, &A.lumMip6); A.ctx->CSSetUnorderedAccessViews(0, 1, &A.lumUav, nullptr);
    A.ctx->Dispatch(1, 1, 1);
    ID3D11UnorderedAccessView* nulU = nullptr; ID3D11ShaderResourceView* nulS = nullptr;
    A.ctx->CSSetUnorderedAccessViews(0, 1, &nulU, nullptr); A.ctx->CSSetShaderResources(0, 1, &nulS);
    // 2. tone mapping du jeu -> +0x3400 en 16 bits flottants (t1 = masque o2 des shaders du jeu, LU)
    float cb0[8] = {r[R_BLANC], r[R_GRIS], r[R_ACTIF], r[R_ACTIFJ], r[R_SCR0], r[R_SCR1], 0, 0};
    vider_srv(); sortie1(A.ldr.rtv, nullptr, A.W, A.H);
    A.ctx->IASetInputLayout(nullptr); A.ctx->VSSetShader(A.vs2, nullptr, 0); A.ctx->PSSetShader(A.psSeuls[PS_TONEMAP].ps, nullptr, 0);
    ID3D11SamplerState* lin = echantillonneur(3, 3, 3); ID3D11SamplerState* pt = ech_point(3, 3);
    A.ctx->PSSetShaderResources(0, 1, &A.hdr.srv); A.ctx->PSSetSamplers(0, 1, &lin);
    A.ctx->PSSetShaderResources(1, 1, &A.mrt[1].srv); A.ctx->PSSetSamplers(1, 1, &pt);   // masque o2 des shaders du jeu (LU)
    A.ctx->PSSetShaderResources(2, 1, &A.lumSrv);
    ID3D11Buffer* b0 = cb_valeurs(cb0, 8); A.ctx->PSSetConstantBuffers(0, 1, &b0);
    etats(A.mel[0], etat_profondeur(false, false), A.rasDouble); A.ctx->Draw(3, 0);
    vider_srv();
    // 2a. (LU 14/11/2026) Sublum du halo (0x141330db0, 30_MapAfter) : bloom_sublum.pfxo = max(t0, 0), image tonemappée
    //     (+0x3400) copiée dans RT_Half n° 2 (groupe 5 masque 4), AVANT l'anticrénelage et les effets
    passe(A.fond.rtv, A.fond.w, A.fond.h, A.vs1, A.psCopieBrut, {A.ldr.srv}, nullptr, 0, nullptr, 0);
    // 2b. ANTICRÉNELAGE TAA du jeu (LU dans nie.exe 0x141334190, 14/11/2026), avant la profondeur de champ :
    //   passe 1 « taa » (taa.pfxo) : t0 image tonemappée, t1 image précédente, t2 vitesses (sortie o1 des shaders, MRT 1) ;
    //     cb0 = u_uvoffs (taaUvOffset 0,5 / taille), u_uvoffsHalton (taaJitterSize = 0 : pas de tremblement), u_rate
    //     (taaBlendRate 0,5), u_neiborRate (taaNeiborBlendRate 0,5) — posteffect_data.cfg.bin ;
    //   passe 2 « 2d_direct_uvoffset » : résultat posé sur l'image en mélange alpha, alpha = taaTemporalBlendRate 0,3.
    //   Sans image précédente (début, saut) : « taa_oneframe ». LU (0x141334768..0x1413347de) : à la fin du TAA, l'image +0x3398 (résultat
    //   final) est copiée par un quad dans l'historique (groupe 1, +0x4510) = image après la passe 2.
    if (A.psSeuls[PS_TAA].ps && A.psSeuls[PS_TAA1].ps) {
        float ct[8] = {0.5f / A.W, 0.5f / A.H, 0, 0, 0.5f, 0.5f, 0, 0};
        if (A.taaOk) passe(A.taaSortie.rtv, A.W, A.H, A.vs1, A.psSeuls[PS_TAA].ps, {A.ldr.srv, A.taaHist.srv, A.mrt[0].srv}, nullptr, 0, ct, 8);
        else passe(A.taaSortie.rtv, A.W, A.H, A.vs1, A.psSeuls[PS_TAA1].ps, {A.ldr.srv}, nullptr, 0, ct, 8);
        passe(A.ldr.rtv, A.W, A.H, A.vs1, A.psCopieBrut, {A.taaSortie.srv}, nullptr, 0, nullptr, 0, A.melTaa);
        float f3[4] = {0.3f, 0.3f, 0.3f, 0.3f}; (void)f3;
        vider_srv(); A.ctx->CopyResource(A.taaHist.t, A.ldr.t); A.taaOk = true;
    }
    // 3. (LU 14/11/2026) TAA écrit dans l'attachement 0 du groupe 2 (+0x3398, 0x1413342b5) : l'image tonemappée et lissée
    //    remplace l'image HDR ; la profondeur de champ (0x141331ba0, groupe 2 masque 0x8001) la modifie sur place.
    passe(A.hdr.rtv, A.W, A.H, A.vs1, A.psCopieBrut, {A.ldr.srv}, nullptr, 0, nullptr, 0);
    if (r[R_DOF]) dof_jeu(im, lum, A.ldr.srv, A.hdr.rtv);
    vider_srv();
}

// halo (0x14132fd90, étape 50_Post) : APRÈS les effets. t0 = +0x3398 (image tonemappée + TAA + profondeur de champ + effets),
// t1 = _SublumTex (copie demi-taille de l'image tonemappée sans effets) ; 3 flous ; posé sur +0x3398 en ONE / INV_SRC_ALPHA
static void halo_jeu(const Lum* lum) {
    const float* r = lum->rg;
    float sl[8]; memcpy(sl, r + R_SUBLUM, 32);
    passe(A.seuil.rtv, A.seuil.w, A.seuil.h, A.vs1, A.psSeuls[PS_SEUIL].ps, {A.hdr.srv, A.fond.srv}, sl, 8, nullptr, 0);
    double g[4] = {exp(-0.01), exp(-0.09), exp(-0.25), exp(-0.49)}; double s = 2 * (g[0] + g[1] + g[2] + g[3]);
    ID3D11ShaderResourceView* src = A.seuil.srv;
    for (int k = 0; k < 3; k++) {
        Cible& a = A.niv[k][0]; Cible& b = A.niv[k][1];
        for (int d = 0; d < 2; d++) {
            float cb[16] = {d == 0 ? r[R_PAS + k] / a.w : 0.0f, d == 1 ? r[R_PAS + k] / a.h : 0.0f, 0, 0, 1, 1, 1, 1,
                            (float)(g[0] / s), (float)(g[1] / s), (float)(g[2] / s), (float)(g[3] / s), 0, 0, 0, 0};
            if (d == 0) passe(b.rtv, a.w, a.h, A.vsg, A.psSeuls[PS_FLOU].ps, {src}, cb, 16, nullptr, 0);
            else passe(a.rtv, a.w, a.h, A.vsg, A.psSeuls[PS_FLOU].ps, {b.srv}, cb, 16, nullptr, 0);
        }
        src = a.srv;
    }
    float hc[8] = {r[R_INT], r[R_ALPHA], r[R_INT + 1], r[R_ALPHA + 1], r[R_INT + 2], r[R_ALPHA + 2], 0, 0};
    passe(A.hdr.rtv, A.W, A.H, A.vs1, A.psSeuls[PS_HALO].ps, {A.niv[0][0].srv, A.niv[1][0].srv, A.niv[2][0].srv}, hc, 8, nullptr, 0, A.melEcran);
    vider_srv();
}

// ------------------------------------------------------------------ effets de la technique
// COUCHES 37-38 (14/11/2026, LU nie.exe 0x14132d760 / 0x14132d1b0 + shaders 2d_direct_depth, neighborhood_similarity_upsampling) :
// ces couches de 40_Effect sont dessinées au TIERS de l'écran (RT_OneThird, groupe 6) puis remontées dans l'image :
// A) RT_OneThird effacé (couleur + profondeur), quad 2d_direct + 2d_direct_depth : couleur = t0 x v1 avec t0 = texture 1x1
//    à 0x00000000 (+0x4ac0, créée en 0x141345d8c) -> (0, 0, 0, 0) ; profondeur = t1 = profondeur principale (+0x4720),
//    profondeur ALWAYS écrite, sans mélange ; B) effets des couches 37 puis 38 dans cette cible (test sur cette profondeur) ;
// C) retour à la cible d'avant (attachement 0), quad 2d_direct + neighborhood_similarity_upsampling : t0 = couleur 1/3
//    (+0x3a88), t1 = profondeur 1/3 (+0x4858), t2 = profondeur principale, cb0 u_param = (1/l, 1/h) du tiers,
//    mélange ONE / INV_SRC_ALPHA (couleur et alpha), sans profondeur ; échantillonneurs comme la remontée du scatter.
static Cible tiersC; static ID3D11Texture2D* tiersPT = nullptr; static ID3D11DepthStencilView* tiersDsv = nullptr; static ID3D11ShaderResourceView* tiersPSrv = nullptr;
static ID3D11BlendState *melTiersA = nullptr, *melTiersC = nullptr;
static bool tiers_debut() {
    if (A.speciaux[SP_TDEP] < 0 || A.speciaux[SP_TUP] < 0) return false;
    static const bool sans = getenv("LECTEUR_SANS_TIERS") != nullptr; if (sans) return false;   // essais : comme avant
    const int w3 = std::max(1, A.W / 3), h3 = std::max(1, A.H / 3);
    if (!tiersPT || tiersC.w != w3 || tiersC.h != h3) {
        if (tiersPT) { tiersPT->Release(); tiersDsv->Release(); tiersPSrv->Release(); }
        D3D11_TEXTURE2D_DESC d = {(UINT)w3, (UINT)h3, 1, 1, DXGI_FORMAT_R32_TYPELESS, {1, 0}, D3D11_USAGE_DEFAULT, D3D11_BIND_DEPTH_STENCIL | D3D11_BIND_SHADER_RESOURCE, 0, 0};
        OK(A.dev->CreateTexture2D(&d, nullptr, &tiersPT), "tiers profondeur");
        D3D11_DEPTH_STENCIL_VIEW_DESC v = {}; v.Format = DXGI_FORMAT_D32_FLOAT; v.ViewDimension = D3D11_DSV_DIMENSION_TEXTURE2D;
        OK(A.dev->CreateDepthStencilView(tiersPT, &v, &tiersDsv), "tiers dsv");
        D3D11_SHADER_RESOURCE_VIEW_DESC sv = {}; sv.Format = DXGI_FORMAT_R32_FLOAT; sv.ViewDimension = D3D11_SRV_DIMENSION_TEXTURE2D; sv.Texture2D.MipLevels = 1;
        OK(A.dev->CreateShaderResourceView(tiersPT, &sv, &tiersPSrv), "tiers srv");
        tiersC = cible(w3, h3, DXGI_FORMAT_R16G16B16A16_FLOAT);
    }
    if (!melTiersA) { melTiersA = melange(false, D3D11_BLEND_ONE, D3D11_BLEND_ZERO, D3D11_BLEND_OP_ADD, D3D11_BLEND_ONE, D3D11_BLEND_ZERO, 0x0F);
        melTiersC = melange(true, D3D11_BLEND_ONE, D3D11_BLEND_INV_SRC_ALPHA, D3D11_BLEND_OP_ADD, D3D11_BLEND_ONE, D3D11_BLEND_INV_SRC_ALPHA, 0x0F); }
    ID3D11SamplerState* l33 = echantillonneur(3, 3, 3);
    vider_srv(); copier_profondeur();
    const float z4[4] = {0, 0, 0, 0}; A.ctx->ClearRenderTargetView(tiersC.rtv, z4); A.ctx->ClearDepthStencilView(tiersDsv, D3D11_CLEAR_DEPTH, 1.0f, 0);
    sortie1(tiersC.rtv, tiersDsv, tiersC.w, tiersC.h);
    { const Prog& P = A.eff.progs[A.speciaux[SP_TDEP]]; lier_shaders(P); quad_jeu(P);
      ID3D11ShaderResourceView* t[2] = {nullptr, A.profScene};   // t0 : vue nulle = (0, 0, 0, 0), comme la texture 1x1 du jeu
      for (int k = 0; k < 2; k++) { A.ctx->PSSetShaderResources(k, 1, &t[k]); A.ctx->PSSetSamplers(k, 1, &l33); }
      etats(melTiersA, etat_profondeur(true, true, 8), A.rasDouble); A.ctx->DrawIndexed(6, 0, 0); }
    vider_srv(); sortie1(tiersC.rtv, tiersDsv, tiersC.w, tiersC.h);
    return true;
}
static void tiers_fin() {
    vider_srv(); sortie1(A.hdr.rtv, nullptr, A.W, A.H);
    ID3D11SamplerState* l33 = echantillonneur(3, 3, 3);
    { const Prog& P = A.eff.progs[A.speciaux[SP_TUP]]; lier_shaders(P); quad_jeu(P);
      float cb[4] = {1.0f / tiersC.w, 1.0f / tiersC.h, 0, 0}; ID3D11Buffer* b0 = cb_valeurs(cb, 4); A.ctx->PSSetConstantBuffers(0, 1, &b0);
      ID3D11ShaderResourceView* t[3] = {tiersC.srv, tiersPSrv, A.profScene};
      for (int k = 0; k < 3; k++) { A.ctx->PSSetShaderResources(k, 1, &t[k]); A.ctx->PSSetSamplers(k, 1, &l33); }
      etats(melTiersC, etat_profondeur(false, false), A.rasDouble); A.ctx->DrawIndexed(6, 0, 0); }
    vider_srv(); sortie_principale();
}

static void dessiner_effet(const DessinEffet& D, const Lum* lum) {
    if (D.elem >= A.elems.size()) return;
    const Element& X = A.elems[D.elem];
    const Prog& P = A.eff.progs[X.prog];
    const Geo& G = X.part ? D.geoP : A.eff.geos[X.geo];
    if (!G.ib || !G.n) return;
    valeurs_camera(D.V, D.P, D.mvp);
    // u_ubParam.w = seuil d'alpha (LU 0x1405948f8) : case 3 / 255 + 0,1 / 255 si le test est actif, sinon -1
    // (14/11/2026) particules : LU (0x14059ff50) u_ubParam = (1, 0, 0, 0) -> seuil 0, quel que soit le mode ; avant : -1
    float ub[4] = {1, 0, 0, X.part ? 0.0f : X.seuil >= 256 ? -1.0f : X.seuil / 255.0f + 0.1f / 255.0f};
    float dif[4] = {D.diffuse[0], D.diffuse[1], D.diffuse[2], D.diffuse[3]};
    // (15/11/2026) couleur de matériau choisie dans l'Atelier : fixe ET animée remplacées (app.js couleurJeu), posée au dessin
    if (modeTech && D.src >= 0 && D.src < (int)T.pieces.size() && T.pieces[D.src].aCoul) for (int k = 0; k < 3; k++) dif[k] = (float)T.pieces[D.src].coul[k];
    { const float ke = facteurEclat(D); if (ke != 1.0f) for (int k = 0; k < 3; k++) dif[k] *= ke; }
    valeurs_dessin(D.modele, ub, dif, D.ambient, D.uv, D.params, D.grd, &D.os);
    if (csmActif && A.csm0Srv) { double t[16]; float l[16]; mul(GL_VERS_D3D, A.csm0vp, t); lignes(t, l); poser(V_LIGHTWP, l, 16); }
    if (P.t11 && !t11Demi) {                          // distorsions hors couches 40-49 : copie de la scène (comme Rendu.dessiner)
        ID3D11ShaderResourceView* nul = nullptr; A.ctx->PSSetShaderResources(11, 1, &nul);
        A.ctx->CopyResource(A.copie.t, A.hdr.t);
    }
    preparer(A.eff, P, G, lum, X.tex, X.adr, false);
    if (csmActif && A.csm0Srv) { A.ctx->PSSetShaderResources(15, 1, &A.csm0Srv); A.ctx->PSSetSamplers(15, 1, &A.s15);
        A.ctx->VSSetShaderResources(15, 1, &A.csm0Srv); A.ctx->VSSetSamplers(15, 1, &A.s15); }
    bool ecran = D.flags & 4;
    const uint32_t mi = std::min<uint32_t>(X.melange & 0xFF, 4);
    // (14/11/2026) bit 8 : faces arrière éliminées (matériau clé 0x0E -> CullMode BACK, FrontCounterClockwise = 1 : LU nie.exe)
    ID3D11RasterizerState* ras = (X.melange & 0x100) ? A.rasArriere : A.rasDouble;
    if ((X.melange >> 16) & 0xFF) {        // biais de profondeur du matériau (0x1404b83d0 : DepthBias = −case 0x1C, plafond 15, pente 0)
        static std::map<uint32_t, ID3D11RasterizerState*> rb; const uint32_t k = X.melange & 0xFF0100; auto it = rb.find(k);
        if (it == rb.end()) { D3D11_RASTERIZER_DESC r = {}; r.FillMode = D3D11_FILL_SOLID; r.CullMode = (X.melange & 0x100) ? D3D11_CULL_BACK : D3D11_CULL_NONE;
            r.FrontCounterClockwise = TRUE; r.DepthClipEnable = TRUE; r.DepthBias = -(INT)((X.melange >> 16) & 0xFF); r.DepthBiasClamp = 15.0f;
            ID3D11RasterizerState* s = nullptr; OK(A.dev->CreateRasterizerState(&r, &s), "raster biais"); it = rb.emplace(k, s).first; }
        ras = it->second; }
    etats(A.mel[mi], etat_profondeur((D.flags & 1) && !ecran, (D.flags & 2) != 0), ras);
    A.ctx->DrawIndexed(G.n, 0, 0);
    // (14/11/2026) l'ancien effacement DÉDUIT du masque des personnages sous les effets est retiré : LU, les effets sont
    // dessinés après le tone mapping (étape 40_Effect), dans l'attachement 0 + profondeur seulement (masque 0x8001).
}

// ------------------------------------------------------------------ fenêtre, appareil
static const char* HLSL_ATELIER =
    // AtelierD3D : _HLSL_SS (VS plein écran), _HLSL_COPIE ; post._HLSL (vs1, vs2, vsg, copie, lum)
    "Texture2D t0 : register(t0); SamplerState s0 : register(s0);\n"
    "struct V1 { float4 pos : SV_Position; float4 uv : TEXCOORD0; };\n"
    "struct V2 { float4 pos : SV_Position; float4 col : COLOR0; float2 uv : TEXCOORD0; };\n"
    "struct VG { float4 pos : SV_Position; float4 a : TEXCOORD0; float4 b : TEXCOORD1; float4 c : TEXCOORD2; float4 d : TEXCOORD3; };\n"
    "cbuffer CB6 : register(b6) { float4 u_offs; };\n"
    "float2 coin(uint id) { return float2((id << 1) & 2, id & 2); }\n"
    "float4 place(float2 p) { return float4(p * float2(2, -2) + float2(-1, 1), 0, 1); }\n"
    "V2 vs_ss(uint id : SV_VertexID) { V2 o; float2 p = float2((id << 1) & 2, id & 2); o.pos = float4(p * float2(2, -2) + float2(-1, 1), 0, 1); o.col = float4(1, 1, 1, 1); o.uv = p; return o; }\n"
    "V1 vs1(uint id : SV_VertexID) { V1 o; float2 p = coin(id); o.pos = place(p); o.uv = p.xyxy; return o; }\n"
    "V2 vs2(uint id : SV_VertexID) { V2 o; float2 p = coin(id); o.pos = place(p); o.col = 1; o.uv = p; return o; }\n"
    "VG vsg(uint id : SV_VertexID) { VG o; float2 p = coin(id); o.pos = place(p);\n"
    "  o.a = float4(p + u_offs.zw, p - u_offs.zw); float2 r = u_offs.xy + u_offs.zw;\n"
    "  o.b = float4(p + r, p - r); r += u_offs.xy; o.c = float4(p + r, p - r); r += u_offs.xy; o.d = float4(p + r, p - r); return o; }\n"
    "float4 copie(V1 i) : SV_Target { return t0.Sample(s0, i.uv.xy); }\n"
    "float4 copie_v2(V2 i) : SV_Target { return t0.Sample(s0, i.uv); }\n"
    "float4 ecran(V1 i) : SV_Target { return float4(saturate(t0.Sample(s0, i.uv.xy).rgb), 1); }\n"
    "float lum(V1 i) : SV_Target { uint w, h; t0.GetDimensions(w, h); uint2 c = (uint2(i.pos.xy) * uint2(w, h)) >> 6;\n"
    "  return dot(max(t0.Load(int3(c, 0)).rgb, 0), float3(0.29891, 0.58661, 0.11448)); }\n"
    // lecteur : mannequin noir (sommets déjà placés) et masque des joueurs pour tonemap.pfxo (bit 0 du canal bleu)
    "cbuffer CBN : register(b0) { row_major float4x4 u_mvp; };\n"
    "float4 vs_noir(float3 p : POSITION) : SV_Position { return mul(u_mvp, float4(p, 1)); }\n"
    "float4 ps_noir() : SV_Target { return float4(0, 0, 0, 1); }\n"
    "float4 ps_masque() : SV_Target { return float4(0, 0, 7.0 / 255.0, 1); }\n"
    // (14/11/2026) mannequin noir AVEC effet de statut (aura du personnage) : terme R de chr_toon_effstatus.pfxo (LU) sur un
    // corps noir : x = 1 - sat(N.V), p = x^Pow, Rim = RimColor.rgb x RimColor.w, s = 0,3 sat(Rim p),
    // R = min(5 N.V, 1) (Rim p - s) + s ; couleur = 0 x StatusColor + R
    "cbuffer CBNS : register(b1) { float4 u_oeil; float4 u_stRim; float4 u_stPow; };\n"
    "struct VNS { float4 p : SV_Position; float3 w : TEXCOORD0; float3 n : TEXCOORD1; };\n"
    "VNS vs_noir_st(float3 p : POSITION, float3 n : NORMAL) { VNS o; o.p = mul(u_mvp, float4(p, 1)); o.w = p; o.n = n; return o; }\n"
    "float4 ps_noir_st(VNS i) : SV_Target { float3 N = normalize(i.n), V = normalize(u_oeil.xyz - i.w); float nv = saturate(dot(N, V));\n"
    "  float x = 1 - nv; float p = exp(log(x) * u_stPow.x); float3 rim = u_stRim.rgb * u_stRim.w;\n"
    "  float3 s = saturate(rim * p) * 0.3; return float4(min(nv * 5, 1) * (rim * p - s) + s, 1); }\n"
    // bannière : quadrilatère (6 sommets) ; u_ban = centre et demi-taille en coordonnées d'écran (-1..1), u_ban2.x = opacité
    "cbuffer CBB : register(b1) { float4 u_ban; float4 u_ban2; };\n"
    "V2 vs_ban(uint id : SV_VertexID) { V2 o; float2 q = float2((id == 1 || id == 4 || id == 5) ? 1 : 0, (id == 2 || id == 3 || id == 5) ? 1 : 0);\n"
    "  o.pos = float4(u_ban.xy + (q * 2 - 1) * u_ban.zw * float2(1, -1), 0, 1); o.col = float4(1, 1, 1, u_ban2.x); o.uv = q; return o; }\n"
    "float4 ps_ban(V2 i) : SV_Target { float4 c = t0.Sample(s0, i.uv); return float4(c.rgb, c.a * i.col.a); }\n"
    // adaptation de la luminosité (cs_buffer_lerp du jeu) : adaptée += taux x (mesure − adaptée)
    "Texture2D<float> tl : register(t0); RWStructuredBuffer<float> ul : register(u0);\n"
    "cbuffer CBA : register(b0) { float4 u_adapt; };\n"
    "[numthreads(1, 1, 1)] void cs_adapt() { float m = tl.Load(int3(0, 0, 0)); ul[0] = u_adapt.y > 0.5 ? m : ul[0] + (m - ul[0]) * u_adapt.x; }\n";

static ID3DBlob* compiler(const char* entree, const char* cible_) {
    ID3DBlob *b = nullptr, *err = nullptr;
    HRESULT h = D3DCompile(HLSL_ATELIER, strlen(HLSL_ATELIER), nullptr, nullptr, nullptr, entree, cible_, 0, 0, &b, &err);
    if (FAILED(h)) { if (err) { FILE* x = fopen("lecteur_erreur.txt", "a"); if (x) { fprintf(x, "%s\n", (char*)err->GetBufferPointer()); fclose(x); } } echec(entree, h); }
    return b;
}
static ID3D11VertexShader* vs_de(const char* e, ID3DBlob** garde = nullptr) { ID3DBlob* b = compiler(e, "vs_5_0"); ID3D11VertexShader* s; OK(A.dev->CreateVertexShader(b->GetBufferPointer(), b->GetBufferSize(), nullptr, &s), e); if (garde) *garde = b; return s; }
static ID3D11PixelShader* ps_de(const char* e) { ID3DBlob* b = compiler(e, "ps_5_0"); ID3D11PixelShader* s; OK(A.dev->CreatePixelShader(b->GetBufferPointer(), b->GetBufferSize(), nullptr, &s), e); return s; }

static void cibles() {
    ID3D11Texture2D* bb; OK(A.sc->GetBuffer(0, __uuidof(ID3D11Texture2D), (void**)&bb), "GetBuffer");
    OK(A.dev->CreateRenderTargetView(bb, nullptr, &A.rtvEcran), "CreateRTV"); bb->Release();
    int W = A.W, H = A.H, hw = std::max(1, (int)(W * 0.5)), hh = std::max(1, (int)(H * 0.5));
    A.hdr = cible(W, H, DXGI_FORMAT_R16G16B16A16_FLOAT); A.copie = cible(W, H, DXGI_FORMAT_R16G16B16A16_FLOAT); A.fond = cible(hw, hh, DXGI_FORMAT_R16G16B16A16_FLOAT);   // RT_Half n° 2 du jeu (_SublumTex)
    A.copieDemi = cible(hw, hh, DXGI_FORMAT_R16G16B16A16_FLOAT);   // RT_Half n° 1 : t11 des couches 40-49 (0x14132dd50)
    A.mrt[0] = cible(W, H, DXGI_FORMAT_R16G16B16A16_FLOAT); A.mrt[1] = cible(W, H, DXGI_FORMAT_R8G8B8A8_UNORM); A.mrt[2] = cible(W, H, DXGI_FORMAT_R8G8B8A8_UNORM);
    A.t13 = cible(hw, hh, DXGI_FORMAT_R16G16B16A16_FLOAT);
    A.temp[0] = cible(W, H, DXGI_FORMAT_R8G8B8A8_UNORM); A.temp[1] = cible(W, H, DXGI_FORMAT_R8G8B8A8_UNORM);
    A.dofMi[0] = cible(hw, hh, DXGI_FORMAT_R16G16B16A16_FLOAT); A.dofMi[1] = cible(hw, hh, DXGI_FORMAT_R16G16B16A16_FLOAT);
    A.seuil = cible(hw, hh, DXGI_FORMAT_R16G16B16A16_FLOAT);
    const double ech_[3] = {0.25, 0.125, 0.0625};
    for (int k = 0; k < 3; k++) { int lw = std::max(1, (int)(W * ech_[k])), lh = std::max(1, (int)(H * ech_[k]));
        A.niv[k][0] = cible(lw, lh, DXGI_FORMAT_R16G16B16A16_FLOAT); A.niv[k][1] = cible(lw, lh, DXGI_FORMAT_R16G16B16A16_FLOAT); }
    // (LU 14/11/2026) formats de RT_Main dans app_config (crc -> n° DXGI, table nie.exe 0x141cc9f00) : attachements 0 (+0x3398)
    // et 1 (+0x3400 = sortie du tone mapping) R16G16B16A16_FLOAT, 2 R16G16_FLOAT, 3 et 4 R8G8B8A8_UNORM. Avant : 8 bits (DÉDUIT à
    // tort) -> tout ce qui dépasse 1 était coupé avant le halo (ballon de Big Bang sans sa lueur). TAA : sortie = attachement 0.
    A.ldr = cible(W, H, DXGI_FORMAT_R16G16B16A16_FLOAT); A.masque = cible(W, H, DXGI_FORMAT_R8G8B8A8_UNORM);
    A.taaSortie = cible(W, H, DXGI_FORMAT_R16G16B16A16_FLOAT); A.taaHist = cible(W, H, DXGI_FORMAT_R16G16B16A16_FLOAT);   // (LU app_config : RT_Prev = groupe 1 = historique +0x4510, 1 attachement R16G16B16A16_FLOAT)
    {   // luminosité : 64 x 64 R32F avec niveaux ; niveau 6 = 1 x 1
        D3D11_TEXTURE2D_DESC d = {64, 64, 0, 1, DXGI_FORMAT_R32_FLOAT, {1, 0}, D3D11_USAGE_DEFAULT, D3D11_BIND_RENDER_TARGET | D3D11_BIND_SHADER_RESOURCE, 0, D3D11_RESOURCE_MISC_GENERATE_MIPS};
        OK(A.dev->CreateTexture2D(&d, nullptr, &A.lumC.t), "lum"); A.lumC.w = A.lumC.h = 64;
        D3D11_RENDER_TARGET_VIEW_DESC rv = {}; rv.Format = DXGI_FORMAT_R32_FLOAT; rv.ViewDimension = D3D11_RTV_DIMENSION_TEXTURE2D;
        OK(A.dev->CreateRenderTargetView(A.lumC.t, &rv, &A.lumC.rtv), "lum rtv"); OK(A.dev->CreateShaderResourceView(A.lumC.t, nullptr, &A.lumC.srv), "lum srv");
        D3D11_SHADER_RESOURCE_VIEW_DESC sv = {}; sv.Format = DXGI_FORMAT_R32_FLOAT; sv.ViewDimension = D3D11_SRV_DIMENSION_TEXTURE2D; sv.Texture2D.MostDetailedMip = 6; sv.Texture2D.MipLevels = 1;
        OK(A.dev->CreateShaderResourceView(A.lumC.t, &sv, &A.lumMip6), "lum mip 6");
        float un = 0.5f; D3D11_BUFFER_DESC bd = {4, D3D11_USAGE_DEFAULT, D3D11_BIND_SHADER_RESOURCE | D3D11_BIND_UNORDERED_ACCESS, 0, D3D11_RESOURCE_MISC_BUFFER_STRUCTURED, 4};
        D3D11_SUBRESOURCE_DATA s = {&un, 0, 0}; OK(A.dev->CreateBuffer(&bd, &s, &A.lumBuf), "lum buf");
        OK(A.dev->CreateShaderResourceView(A.lumBuf, nullptr, &A.lumSrv), "lum buf srv"); OK(A.dev->CreateUnorderedAccessView(A.lumBuf, nullptr, &A.lumUav), "lum buf uav");
    }
    D3D11_TEXTURE2D_DESC z = {(UINT)W, (UINT)H, 1, 1, DXGI_FORMAT_R32_TYPELESS, {1, 0}, D3D11_USAGE_DEFAULT, D3D11_BIND_DEPTH_STENCIL | D3D11_BIND_SHADER_RESOURCE, 0, 0};
    OK(A.dev->CreateTexture2D(&z, nullptr, &A.prof), "profondeur");
    D3D11_DEPTH_STENCIL_VIEW_DESC dd = {}; dd.Format = DXGI_FORMAT_D32_FLOAT; dd.ViewDimension = D3D11_DSV_DIMENSION_TEXTURE2D;
    OK(A.dev->CreateDepthStencilView(A.prof, &dd, &A.dsv), "DSV");
    z.BindFlags = D3D11_BIND_SHADER_RESOURCE;          // copie de la profondeur (t12, shadow_ss, SSAO, contours, DOF)
    OK(A.dev->CreateTexture2D(&z, nullptr, &A.profCopieTex), "t12");
    D3D11_SHADER_RESOURCE_VIEW_DESC sd = {}; sd.Format = DXGI_FORMAT_R32_FLOAT; sd.ViewDimension = D3D11_SRV_DIMENSION_TEXTURE2D; sd.Texture2D.MipLevels = 1;
    OK(A.dev->CreateShaderResourceView(A.profCopieTex, &sd, &A.profScene), "t12");
}

static ID3D11BlendState* melange(bool actif, D3D11_BLEND src, D3D11_BLEND dst, D3D11_BLEND_OP op, D3D11_BLEND sa, D3D11_BLEND da, UINT8 masque) {
    D3D11_BLEND_DESC b = {}; auto& r = b.RenderTarget[0];
    r.BlendEnable = actif; r.SrcBlend = src; r.DestBlend = dst; r.BlendOp = op; r.SrcBlendAlpha = sa; r.DestBlendAlpha = da; r.BlendOpAlpha = D3D11_BLEND_OP_ADD;
    r.RenderTargetWriteMask = masque;
    ID3D11BlendState* s; OK(A.dev->CreateBlendState(&b, &s), "blend"); return s;
}

static void etats_init() {
    // comme Rendu.melange / Post : opaque, profondeur (rien écrit), alpha, additif, soustractif ; masques des passes
    auto ONE = D3D11_BLEND_ONE, ZERO = D3D11_BLEND_ZERO, ISA = D3D11_BLEND_INV_SRC_ALPHA, SA = D3D11_BLEND_SRC_ALPHA;
    A.mel[0] = melange(false, ONE, ZERO, D3D11_BLEND_OP_ADD, ONE, ISA, 0x0F);
    A.mel[1] = melange(false, ONE, ZERO, D3D11_BLEND_OP_ADD, ONE, ISA, 0);
    A.mel[2] = melange(true, SA, ISA, D3D11_BLEND_OP_ADD, ONE, ISA, 0x0F);
    A.mel[3] = melange(true, SA, ONE, D3D11_BLEND_OP_ADD, ZERO, ONE, 0x0F);
    A.mel[4] = melange(true, SA, ONE, D3D11_BLEND_OP_REV_SUBTRACT, ZERO, ONE, 0x0F);
    A.melR_A = melange(false, ONE, ZERO, D3D11_BLEND_OP_ADD, ONE, ISA, 9);          // shadow_ss : R et A
    A.melG = melange(false, ONE, ZERO, D3D11_BLEND_OP_ADD, ONE, ISA, 2);            // SSAO : G
    A.melGAdd = melange(true, ONE, ONE, D3D11_BLEND_OP_ADD, ONE, ONE, 2);           // ombre des pieds : G ajouté
    A.melRGB = melange(false, ONE, ZERO, D3D11_BLEND_OP_ADD, ONE, ISA, 7);          // ciel
    A.melMul = melange(true, ZERO, D3D11_BLEND_SRC_COLOR, D3D11_BLEND_OP_ADD, ZERO, ONE, 0x0F);   // composite des contours
    A.melEcran = melange(true, ONE, ISA, D3D11_BLEND_OP_ADD, ONE, ISA, 0x0F);       // halo
    A.melMasqueA = melange(true, ZERO, ISA, D3D11_BLEND_OP_ADD, ZERO, ISA, 0x0F);   // masque des personnages sous un effet alpha
    A.melMasque0 = melange(true, ZERO, ZERO, D3D11_BLEND_OP_ADD, ZERO, ZERO, 0x0F);  // ... sous un effet opaque
    A.melTaa = melange(true, D3D11_BLEND_BLEND_FACTOR, D3D11_BLEND_INV_BLEND_FACTOR, D3D11_BLEND_OP_ADD, D3D11_BLEND_BLEND_FACTOR, D3D11_BLEND_INV_BLEND_FACTOR, 0x0F);
    A.melDof = melange(true, SA, ISA, D3D11_BLEND_OP_ADD, ONE, ZERO, 7);            // profondeur de champ
    D3D11_RASTERIZER_DESC r = {}; r.FillMode = D3D11_FILL_SOLID; r.CullMode = D3D11_CULL_NONE; r.DepthClipEnable = TRUE;
    OK(A.dev->CreateRasterizerState(&r, &A.rasDouble), "raster");
    r.CullMode = D3D11_CULL_BACK; r.FrontCounterClockwise = TRUE; OK(A.dev->CreateRasterizerState(&r, &A.rasArriere), "raster");
    uint8_t b1[4] = {255, 255, 255, 255}, b0[4] = {0, 0, 0, 0}; A.blanc = texture_rgba(1, 1, b1, false); A.noir = texture_rgba(1, 1, b0, false);
    D3D11_SAMPLER_DESC s = {}; s.Filter = (D3D11_FILTER)0x95; s.AddressU = s.AddressV = s.AddressW = D3D11_TEXTURE_ADDRESS_BORDER; s.MaxAnisotropy = 1;
    s.ComparisonFunc = D3D11_COMPARISON_GREATER; s.BorderColor[0] = s.BorderColor[1] = s.BorderColor[2] = s.BorderColor[3] = 1; s.MaxLOD = 3.4e38f;
    OK(A.dev->CreateSamplerState(&s, &A.s15), "s15");
    ID3DBlob* bn = nullptr;
    A.vsSS = vs_de("vs_ss"); A.vs1 = vs_de("vs1"); A.vs2 = vs_de("vs2"); A.vsg = vs_de("vsg"); A.vsNoir = vs_de("vs_noir", &bn);
    A.psCopie = ps_de("ecran"); A.psCopieBrut = ps_de("copie"); A.psCopieV2 = ps_de("copie_v2"); A.psLum = ps_de("lum"); A.psNoir = ps_de("ps_noir"); A.psMasque = ps_de("ps_masque");
    // (psCopieBrut : copie SANS saturate, pour les copies internes en 16 bits flottants)
    A.vsBan = vs_de("vs_ban"); A.psBan = ps_de("ps_ban");
    D3D11_INPUT_ELEMENT_DESC el = {"POSITION", 0, DXGI_FORMAT_R32G32B32_FLOAT, 0, 0, D3D11_INPUT_PER_VERTEX_DATA, 0};
    OK(A.dev->CreateInputLayout(&el, 1, bn->GetBufferPointer(), bn->GetBufferSize(), &A.dispNoir), "noir");
    { ID3DBlob* bs = nullptr; A.vsNoirSt = vs_de("vs_noir_st", &bs); A.psNoirSt = ps_de("ps_noir_st");
      D3D11_INPUT_ELEMENT_DESC e2[2] = {{"POSITION", 0, DXGI_FORMAT_R32G32B32_FLOAT, 0, 0, D3D11_INPUT_PER_VERTEX_DATA, 0},
                                        {"NORMAL", 0, DXGI_FORMAT_R32G32B32_FLOAT, 1, 0, D3D11_INPUT_PER_VERTEX_DATA, 0}};
      OK(A.dev->CreateInputLayout(e2, 2, bs->GetBufferPointer(), bs->GetBufferSize(), &A.dispNoirSt), "noir statut"); }
    { ID3DBlob* c = compiler("cs_adapt", "cs_5_0"); OK(A.dev->CreateComputeShader(c->GetBufferPointer(), c->GetBufferSize(), nullptr, &A.csAdapt), "cs"); }
    cbNoir = tampon_dyn(64, D3D11_BIND_CONSTANT_BUFFER); cbNoirSt = tampon_dyn(48, D3D11_BIND_CONSTANT_BUFFER);
    float q[16] = {-1, 1, 0, 1, 1, 1, 0, 1, -1, -1, 0, 1, 1, -1, 0, 1}, uv[8] = {0, 0, 1, 0, 0, 1, 1, 1}; uint8_t col[16]; memset(col, 255, 16);
    uint16_t qi[6] = {0, 1, 2, 2, 1, 3};
    A.quadPos = tampon(q, 64, D3D11_BIND_VERTEX_BUFFER); A.quadUv = tampon(uv, 32, D3D11_BIND_VERTEX_BUFFER); A.quadCol = tampon(col, 16, D3D11_BIND_VERTEX_BUFFER);
    A.quadIb = tampon(qi, 12, D3D11_BIND_INDEX_BUFFER);
    float cv[24]; int i = 0; for (int x = -1; x <= 1; x += 2) for (int y = -1; y <= 1; y += 2) for (int zz = -1; zz <= 1; zz += 2) { cv[i++] = (float)x; cv[i++] = (float)y; cv[i++] = (float)zz; }
    uint16_t ci[36] = {0, 1, 2, 2, 1, 3, 4, 6, 5, 5, 6, 7, 0, 4, 1, 1, 4, 5, 2, 3, 6, 6, 3, 7, 0, 2, 4, 4, 2, 6, 1, 5, 3, 3, 5, 7};
    A.cubeVb = tampon(cv, 96, D3D11_BIND_VERTEX_BUFFER); A.cubeIb = tampon(ci, 72, D3D11_BIND_INDEX_BUFFER);
}

static void passe_couleur(const Image& im, const Lum* lum) {
    float zero[4] = {0, 0, 0, 0};
    for (int k = 0; k < 3; k++) A.ctx->ClearRenderTargetView(A.mrt[k].rtv, zero);      // (Rendu.vider_mrt)
    vider_srv(); sortie_mrt();
    if (im.decor) { double mvpgl[16]; mul(im.P, im.V, mvpgl); valeurs_camera(im.V, im.P, mvpgl, true, true);
        for (const Dessin& D : A.dessins) if (D.passe == 1 && visible_lod(D)) dessiner_decor(D, lum); }
    acteurs_passe(im, lum, -1, false);
    vider_srv(); sortie_principale();
}

// BANNIÈRE (14/11/2026) : telop.bin (u32 largeur, hauteur + RVBA), dessinée par-dessus l'image finale (couche du menu)
static std::wstring F_TELOP;                   // (22/11) relu sur la commande « telop » (bannière changée dans l'Atelier, sans relancer)
static void charger_telop(const std::wstring& f) {
    F_TELOP = f;
    if (A.telSrv) { A.telSrv->Release(); A.telSrv = nullptr; } A.telW = A.telH = 0;
    FILE* x = _wfopen(f.c_str(), L"rb"); if (!x) return;
    uint32_t wh[2] = {0, 0}; if (fread(wh, 4, 2, x) != 2 || !wh[0] || !wh[1] || wh[0] > 8192 || wh[1] > 8192) { fclose(x); return; }
    std::vector<uint8_t> px((size_t)wh[0] * wh[1] * 4); const size_t lu = fread(px.data(), 1, px.size(), x); fclose(x);
    if (lu != px.size()) return;
    D3D11_TEXTURE2D_DESC d = {wh[0], wh[1], 1, 1, DXGI_FORMAT_R8G8B8A8_UNORM, {1, 0}, D3D11_USAGE_IMMUTABLE, D3D11_BIND_SHADER_RESOURCE, 0, 0};
    D3D11_SUBRESOURCE_DATA s = {px.data(), wh[0] * 4, 0}; ID3D11Texture2D* t = nullptr;
    if (FAILED(A.dev->CreateTexture2D(&d, &s, &t))) return;
    A.dev->CreateShaderResourceView(t, nullptr, &A.telSrv); t->Release(); A.telW = (int)wh[0]; A.telH = (int)wh[1];
}
static void dessiner_telop(int f) {
    if (!modeTech || !A.telSrv || !A.vsBan || !A.psBan) return;
    double s, a; T.telop.etat(f, s, a); if (a <= 0.001) return;
    static ID3D11BlendState* mel = nullptr;
    if (!mel) mel = melange(true, D3D11_BLEND_SRC_ALPHA, D3D11_BLEND_INV_SRC_ALPHA, D3D11_BLEND_OP_ADD, D3D11_BLEND_ONE, D3D11_BLEND_INV_SRC_ALPHA, 0x0F);
    const int W = A.Wf ? A.Wf : A.W, H = A.Hf ? A.Hf : A.H;
    vider_srv(); sortie1(A.rtvEcran, nullptr, W, H);
    // espace du menu 1920 x 1080 -> écran (16:9) ; image 1:1 à l'échelle s, centrée en (cx, cy)
    float cb[8] = {(float)(T.telop.cx / 960.0 - 1), (float)(1 - T.telop.cy / 540.0), (float)(A.telW * 0.5 * s / 960.0), (float)(A.telH * 0.5 * s / 540.0),
                   (float)std::min(1.0, a), 0, 0, 0};
    ID3D11Buffer* b = cb_valeurs(cb, 8);
    A.ctx->IASetInputLayout(nullptr); A.ctx->IASetPrimitiveTopology(D3D11_PRIMITIVE_TOPOLOGY_TRIANGLELIST);
    A.ctx->VSSetShader(A.vsBan, nullptr, 0); A.ctx->VSSetConstantBuffers(1, 1, &b);
    A.ctx->PSSetShader(A.psBan, nullptr, 0); A.ctx->GSSetShader(nullptr, nullptr, 0);
    ID3D11SamplerState* lin = echantillonneur(3, 3, 3);
    A.ctx->PSSetShaderResources(0, 1, &A.telSrv); A.ctx->PSSetSamplers(0, 1, &lin);
    etats(mel, etat_profondeur(false, false), A.rasDouble);
    A.ctx->Draw(6, 0);
    vider_srv();
}

static void dessiner_image(int f) {
    const Image& im = A.images[f];
    const Lum* lum = im.lum < A.lums.size() ? &A.lums[im.lum] : &A.lums[0];
    cbJetablesN = 0; csmActif = false; t13Actif = nullptr;
    if (A.premiere) { A.taaOk = false; camPrecOk = false; }   // (début, saut d'image : pas d'image précédente)
    double mvpgl[16]; mul(im.P, im.V, mvpgl);
    valeurs_camera(im.V, im.P, mvpgl);
    lier_lumieres(im.lumieres);
    float noir[4] = {0, 0, 0, 0};
    vider_srv();
    A.ctx->ClearRenderTargetView(A.hdr.rtv, noir); A.ctx->ClearDepthStencilView(A.dsv, D3D11_CLEAR_DEPTH, 1.0f, 0);
    // peau des personnages (une fois par image)
    for (const ActeurImage& a : im.acteurs) if (a.modele < A.modeles.size())
        for (uint32_t i : a.pieces) if (i < A.modeles[a.modele].size() && A.modeles[a.modele][i].ib) { choisir_instance(A.modeles[a.modele][i], &a - im.acteurs.data()); peau(A.modeles[a.modele][i], a.mats); }
    // 1. profondeur du stade (depth du jeu) et des personnages
    sortie_principale();
    if (im.decor) for (const Dessin& D : A.dessins) if (D.passe == 0 && visible_lod(D)) dessiner_decor(D, lum);
    acteurs_passe(im, lum, -1, true);
    copier_profondeur();
    // 2. ombres du soleil : 3 cascades + shadow_ss -> t13
    if (im.om.present) ombres_stade(im, lum);
    sortie_principale();
    A.ctx->ClearDepthStencilView(A.dsv, D3D11_CLEAR_DEPTH, 1.0f, 0);
    if (im.decor) { valeurs_camera(im.V, im.P, mvpgl, true, true); for (const Dessin& D : A.dessins) if (D.passe == 0 && visible_lod(D)) dessiner_decor(D, lum); }
    // 3. couleur (4 images) ; SSAO + ombre des pieds ; 2e passe
    // (14/11/2026) ORDRE DU JEU (LU 0x140fa2083 -> 0x140fa22e9) : PreShading composé AVANT la couleur : normale simple, SSAO
    // (+ ombre des pieds), ombre à l'écran (déjà faite, elle efface t13), flou bilatéral ; puis UNE passe couleur.
    // Avant : couleur, SSAO, 2e passe couleur (la 1re servait aux normales du G-buffer pour le SSAO, DÉDUIT).
    ssao_jeu(im, lum);
    pieds_jeu(im, lum);
    flou_preshading(im, lum);
    passe_couleur(im, lum);
    // 4. ciel, contours
    if (im.decor) ciel_jeu(im, lum);
    bool personnages = false; for (auto& a : im.acteurs) if (!a.pieces.empty()) personnages = true;
    if (personnages) contour_jeu(im, lum);
    // masque des joueurs (tone mapping) et image sans les effets (halo)
    // (14/11/2026, LU) masque « personnage » du tone mapping = sortie o2 des shaders du jeu (attachement 3 du groupe 2,
    // chr_toon* : o2.z = 7/255), donc mrt[1] tel que la passe couleur l'a écrit (le ballon, les esprits…). Le lecteur
    // ne l'ajoute que pour les mannequins noirs (pièces dessinées sans le shader du jeu). Avant : masque redessiné
    // pour tous les acteurs (ancienne règle, devinée), incomplet sur le ballon de Big Bang -> exposition appliquée au ballon.
    if (personnages) { sortie1(A.mrt[1].rtv, A.dsv, A.W, A.H); for (auto& a : im.acteurs) if (a.modele < A.modeles.size())
        for (uint32_t i : a.pieces) if (i < A.modeles[a.modele].size() && A.modeles[a.modele][i].ib && (A.modeles[a.modele][i].noir || A.modeles[a.modele][i].prog < 0)) {
            choisir_instance(A.modeles[a.modele][i], &a - im.acteurs.data()); dessiner_noir(im, A.modeles[a.modele][i], -1, 2); } }
    // 5. ORDRE DU JEU (LU 14/11/2026, étapes gmdCDrawObjModelPriority de 0x140fa0c20) : 30_MapAfter = mesure, tone mapping,
    //    Sublum, TAA, profondeur de champ (isBlurBeforeEffectModel = 1 dans posteffect_data.cfg.bin : 0x140f9cbbf) ;
    //    40_Effect = effets (couches 0x19..0x32 : 53 000 des 57 000 matériaux d'effets ont la couche 30) dessinés sur
    //    l'image TONEMAPPÉE, attachement 0 + profondeur (groupe 2, masque 0x8001) ; 50_Post = halo.
    //    COUCHES (LU 14/11/2026) : octet +8 du matériau / priorité des particules ; plages des étapes (0x140591cc0, bornes
    //    [bas, haut[) : 10_MapBefore 2-9, 15_ProjEffect 21 et 39, 20_CharaBefore 10-19, 25_CharaAfter 16-19, 30_MapAfter
    //    20-24 (avant le tone mapping) ; 40_Effect : 25-29, puis 37-38, puis 30-36, puis 40-49 ; 60_UI 55-59, puis 60-63
    //    (après le halo). 50-54 : dans aucune plage (jamais dessinées). Dans une plage, couche par couche croissante.
    std::vector<std::pair<int, size_t>> ordre; ordre.reserve(im.effets.size());
    static int avecCouches = -1;                         // export d'avant VERSION_TECH 13 : aucune couche -> 30 partout
    if (avecCouches < 0) { avecCouches = 0; for (const Element& X : A.elems) if (X.melange >> 24) { avecCouches = 1; break; } }
    for (size_t i = 0; i < im.effets.size(); i++) {
        const DessinEffet& D = im.effets[i]; if (D.elem >= A.elems.size() || dessinCache(D)) continue;
        const int c = avecCouches ? (int)(A.elems[D.elem].melange >> 24) : 30, b = c >= 64 ? 63 : c;
        int etape;                                       // rang de l'étape puis de la sous-passe
        if (b < 2) etape = 0; else if (b < 10) etape = 1; else if (b == 21 || b == 39) etape = 2; else if (b < 20) etape = 3;
        else if (b < 25) etape = 4; else if (b < 30) etape = 10; else if (b == 37 || b == 38) etape = 11; else if (b < 37) etape = 12;
        else if (b >= 40 && b < 50) etape = 13; else if (b < 55) continue; else if (b < 60) etape = 20; else etape = 21;
        ordre.push_back({etape * 64 + b, i});
    }
    std::stable_sort(ordre.begin(), ordre.end(), [](const std::pair<int, size_t>& a, const std::pair<int, size_t>& b) { return a.first < b.first; });
    auto dessiner_rangs = [&](int de, int a) {
        int tiers = 0;                                   // 0 pas encore, 1 en cours, 2 impossible (export ancien), 3 fini
        for (auto& o : ordre) if (o.first >= de * 64 && o.first < a * 64) {
            // (LU 0x14132dd50) avant les couches 40-49 : l'image courante (+0x3398, isBlurBeforeEffectModel = 1) est copiée
            // UNE fois en demi-taille (RT_Half n° 1, quad plein écran) et devient t11 des distorsions de ces couches
            if (o.first >= 13 * 64 && o.first < 14 * 64 && !t11Demi) {
                passe(A.copieDemi.rtv, A.copieDemi.w, A.copieDemi.h, A.vs1, A.psCopieBrut, {A.hdr.srv}, nullptr, 0, nullptr, 0);
                vider_srv(); copier_profondeur(); sortie_principale(); t11Demi = true;
            }
            // (14/11/2026) couches 37-38 : au tiers de l'écran puis remontées (tiers_debut / tiers_fin, LU)
            const bool t37 = o.first >= 11 * 64 && o.first < 12 * 64;
            if (t37 && !tiers) tiers = tiers_debut() ? 1 : 2;
            if (!t37 && tiers == 1) { tiers_fin(); tiers = 3; }
            dessiner_effet(im.effets[o.second], lum);
        }
        if (tiers == 1) tiers_fin();
        t11Demi = false;
    };
    copier_profondeur(); sortie_principale();
    dessiner_rangs(0, 10);                               // couches des étapes avant le tone mapping
    ID3D11ShaderResourceView* finale = A.hdr.srv;
    if (A.effetsEcran) {
        effets_ecran(im, lum);
        copier_profondeur(); sortie_principale();
        dessiner_rangs(10, 20);                          // 40_Effect
        halo_jeu(lum);
        sortie_principale(); dessiner_rangs(20, 30);     // 60_UI et suivantes
    } else {
        if (lum->rg[R_DOF]) dof_jeu(im, lum, A.hdr.srv, A.hdr.rtv);
        copier_profondeur(); sortie_principale();
        dessiner_rangs(10, 30);
    }
    passe(A.rtvEcran, A.Wf ? A.Wf : A.W, A.Hf ? A.Hf : A.H, A.vs1, A.psCopie, {finale}, nullptr, 0, nullptr, 0);
    dessiner_telop(f);
    vider_srv();
    memcpy(camPrecV, camCourV, sizeof camPrecV); memcpy(camPrecVP, camCourVP, sizeof camPrecVP); memcpy(camPrecWP, camCourWP, sizeof camPrecWP); camPrecOk = true;
}

// (15/11/2026) CHOIX AU CLIC : la pièce / l'émetteur visible sous le clic. Chaque dessin d'effet de l'image affichée est refait
// SEUL dans une cible effacée en noir, avec ses vrais shaders et son mélange (même profondeur que l'image) : la couleur lue au
// pixel = ce qu'il y apporte (zones transparentes = 0). Choisi : le dernier dessiné (le dessus) qui apporte au moins 30 % du
// plus fort. Réponse à la page dans « etat » : « choix <n> <clé> ».
static int PICK_X = -1, PICK_Y = -1, CHOIX_N = 0; static std::string CHOIX;
static Cible pickC; static ID3D11Texture2D* pickSt = nullptr;
static float demi_vers_f(uint16_t h) { const int e = (h >> 10) & 31, m = h & 1023; const float v = e == 0 ? m / 16777216.0f : e == 31 ? 65504.0f : ldexpf(1.0f + m / 1024.0f, e - 15); return (h & 0x8000) ? -v : v; }
static void choisir_sous_clic(int f) {
    if (PICK_X < 0) return; const int x = PICK_X, y = PICK_Y; PICK_X = PICK_Y = -1;
    if (!modeTech || f < 0 || f >= (int)A.images.size() || x < 0 || y < 0 || x >= A.W || y >= A.H) return;
    if (!pickC.t || pickC.w != A.W || pickC.h != A.H) {
        pickC = cible(A.W, A.H, DXGI_FORMAT_R16G16B16A16_FLOAT);
        if (!pickSt) { D3D11_TEXTURE2D_DESC d = {1, 1, 1, 1, DXGI_FORMAT_R16G16B16A16_FLOAT, {1, 0}, D3D11_USAGE_STAGING, 0, D3D11_CPU_ACCESS_READ, 0};
            OK(A.dev->CreateTexture2D(&d, nullptr, &pickSt), "choix"); } }
    const Image& im = A.images[f]; const Lum* lum = im.lum < A.lums.size() ? &A.lums[im.lum] : &A.lums[0];
    std::vector<std::pair<int, size_t>> ordre;           // même ordre que dessiner_image (étapes puis couches)
    for (size_t i = 0; i < im.effets.size(); i++) { const DessinEffet& D = im.effets[i];
        if (D.elem >= A.elems.size() || dessinCache(D) || (D.src < 0 && D.srcE < 0)) continue;
        const int c = (int)(A.elems[D.elem].melange >> 24), b = c >= 64 ? 63 : c; int etape;
        if (b < 2) etape = 0; else if (b < 10) etape = 1; else if (b == 21 || b == 39) etape = 2; else if (b < 20) etape = 3;
        else if (b < 25) etape = 4; else if (b < 30) etape = 10; else if (b == 37 || b == 38) etape = 11; else if (b < 37) etape = 12;
        else if (b >= 40 && b < 50) etape = 13; else if (b < 55) continue; else if (b < 60) etape = 20; else etape = 21;
        ordre.push_back({etape * 64 + b, i}); }
    std::stable_sort(ordre.begin(), ordre.end(), [](const std::pair<int, size_t>& a, const std::pair<int, size_t>& b) { return a.first < b.first; });
    const float noir[4] = {0, 0, 0, 0}; std::vector<std::pair<size_t, float>> res; float mx = 0;
    for (auto& o : ordre) { const DessinEffet& D = im.effets[o.second];
        vider_srv(); A.ctx->ClearRenderTargetView(pickC.rtv, noir); sortie1(pickC.rtv, A.dsv, A.W, A.H);
        dessiner_effet(D, lum);
        D3D11_BOX bx = {(UINT)x, (UINT)y, 0, (UINT)x + 1, (UINT)y + 1, 1}; A.ctx->CopySubresourceRegion(pickSt, 0, 0, 0, 0, pickC.t, 0, &bx);
        D3D11_MAPPED_SUBRESOURCE m; if (FAILED(A.ctx->Map(pickSt, 0, D3D11_MAP_READ, 0, &m))) continue;
        uint16_t h[4]; memcpy(h, m.pData, 8); A.ctx->Unmap(pickSt, 0);
        float s = 0; for (int k = 0; k < 3; k++) { const float v = demi_vers_f(h[k]); if (v == v) s = std::max(s, std::min(v, 4.0f)); }
        if (s > 0.004f) { res.push_back({o.second, s}); mx = std::max(mx, s); } }
    vider_srv(); sortie_principale();
    std::string cle;
    for (auto it = res.rbegin(); it != res.rend(); ++it) if (it->second >= 0.3f * mx) { const DessinEffet& D = im.effets[it->first];
        cle = D.src >= 0 ? T.pieces[D.src].cle : T.ems[D.srcE].cle; break; }
    CHOIX = cle.empty() ? "-" : cle; CHOIX_N++;
    FILE* fx = fopen("lecteur_incruste.txt", "a"); if (fx) { fprintf(fx, "clic %d %d : %zu dessins touchés -> %s\n", x, y, res.size(), CHOIX.c_str()); fclose(fx); }
}
static bool pause = false; static double temps = 0; static int pasManuel = 0;
#include "incruste.h"
// (15/11/2026) commande « options » : pièces cachées et couleurs relues sans relancer le lecteur (dossier de modifs.bin)
static void options_rel() {
    if (F_MODIFS.empty()) return;
    const size_t k = F_MODIFS.find_last_of(L"\\/"); if (k == std::wstring::npos) return;
    std::string avant; for (auto& e : T.ems) { char t[64]; sprintf_s(t, "%d %.4f %.4f;", e.aTeinte ? 1 : 0, e.tH, e.tC); avant += t; }
    T.lire_options(F_MODIFS.substr(0, k)); teintes_sommets();
    std::string apres; for (auto& e : T.ems) { char t[64]; sprintf_s(t, "%d %.4f %.4f;", e.aTeinte ? 1 : 0, e.tH, e.tC); apres += t; }
    if (avant != apres) for (int i = 0; i < calcules && i < (int)A.images.size(); i++) particules_gpu(A.images[i]);   // (15/11/2026) aussi en pause
    FILE* x = fopen("lecteur_incruste.txt", "a"); if (x) { fprintf(x, "options relues\n"); fclose(x); }
}
static void charger_telop_rel() {
    if (F_TELOP.empty()) return;
    charger_telop(F_TELOP);
    FILE* x = fopen("lecteur_incruste.txt", "a"); if (x) { fprintf(x, "banniere relue : %dx%d\n", A.telW, A.telH); fclose(x); }
}
static void charger_modifs_rel() {
    if (F_MODIFS.empty()) return;
    charger_modifs(F_MODIFS);
    FILE* x = fopen("lecteur_incruste.txt", "a"); if (x) { fprintf(x, "textures relues : %zu retouchees\n", TEX_MODIF.size()); fclose(x); }
}
static void redimensionner(int w, int h) {          // fenêtre incrustée : nouvelle taille du tampon d'écran (image mise à l'échelle)
    if (w < 8 || h < 8) return;
    A.ctx->OMSetRenderTargets(0, nullptr, nullptr); if (A.rtvEcran) { A.rtvEcran->Release(); A.rtvEcran = nullptr; }
    A.ctx->Flush();
    OK(A.sc->ResizeBuffers(0, (UINT)w, (UINT)h, DXGI_FORMAT_UNKNOWN, 0), "ResizeBuffers");
    ID3D11Texture2D* bb; OK(A.sc->GetBuffer(0, __uuidof(ID3D11Texture2D), (void**)&bb), "GetBuffer");
    OK(A.dev->CreateRenderTargetView(bb, nullptr, &A.rtvEcran), "CreateRTV"); bb->Release();
    A.Wf = w; A.Hf = h;
}
static LRESULT CALLBACK proc(HWND h, UINT m, WPARAM w, LPARAM l) {
    if (m == WM_DESTROY) { PostQuitMessage(0); return 0; }
    if (INC.actif && m == WM_MOUSEACTIVATE) return MA_NOACTIVATE;            // (incrusté : ne prend jamais le clavier)
    // (15/11/2026) clic sur l'image : choisit la pièce / les particules sous la souris (avant : lecture / pause ; la pause reste
    // sur Espace et le bouton ▶ de l'Atelier). Coordonnées de la fenêtre -> pixels de l'image calculée (mise à l'échelle).
    if (INC.actif && m == WM_LBUTTONDOWN) { RECT rc; GetClientRect(h, &rc); const int cw = std::max<int>(1, rc.right), ch = std::max<int>(1, rc.bottom);
        PICK_X = (int)((short)LOWORD(l)) * A.W / cw; PICK_Y = (int)((short)HIWORD(l)) * A.H / ch; return 0; }
    if (m == WM_KEYDOWN) {
        if (w == VK_ESCAPE) DestroyWindow(h);
        if (w == VK_SPACE) pause = !pause;
        if (w == VK_HOME) { temps = 0; A.premiere = true; }
        if (w == VK_RIGHT) { pause = true; pasManuel++; }
        if (w == VK_LEFT) { pause = true; pasManuel--; }
        if (w == 'E') { A.effetsEcran = !A.effetsEcran; A.premiere = true; }
    }
    return DefWindowProcW(h, m, w, l);
}

int WINAPI wWinMain(HINSTANCE inst, HINSTANCE, PWSTR, int) {
    int argc; wchar_t** argv = CommandLineToArgvW(GetCommandLineW(), &argc);
    // lecteur.exe <stade> <technique> <L> <H> : l'animation est calculée ici (14/11/2026)
    // (ancien : lecteur.exe <dossier> <L> <H>, animation de la page dans <dossier>\images.bin)
    std::wstring dos = argc > 1 ? argv[1] : L"scenes\\essai", dosTech;
    if (argc > 2 && (argv[2][0] < L'0' || argv[2][0] > L'9')) { modeTech = true; dosTech = argv[2]; if (argc > 4) { A.W = _wtoi(argv[3]); A.H = _wtoi(argv[4]); } }
    else if (argc > 3) { A.W = _wtoi(argv[2]); A.H = _wtoi(argv[3]); }
    // essai : ... --capture <image> <fichier> [--sans-ecran] [--depuis <image>] -> pixels RGBA puis fin
    //         ... --verifier <reference.bin> <rapport.txt> -> comparaison de l'animation à celle de la page, puis fin
    int capture = -1, depuis = -1, portInc = 0; std::wstring fcap, fref, frap, dosPlanche; std::vector<int> planche;
    for (int i = 1; i < argc; i++) {
        std::wstring a = argv[i];
        if (a == L"--capture" && i + 2 < argc) { capture = _wtoi(argv[i + 1]); fcap = argv[i + 2]; silencieux = true; }
        if (a == L"--planche" && i + 1 < argc) { dosPlanche = argv[i + 1]; silencieux = true; for (int j = i + 2; j < argc && argv[j][0] >= L'0' && argv[j][0] <= L'9'; j++) planche.push_back(_wtoi(argv[j])); }
        if (a == L"--verifier" && i + 2 < argc) { fref = argv[i + 1]; frap = argv[i + 2]; silencieux = true; sansGpu = true; }
        if (a == L"--sans-ecran") A.effetsEcran = false;
        if (a == L"--incruste" && i + 1 < argc) portInc = _wtoi(argv[i + 1]);
        if (a == L"--fenetre" && i + 1 < argc) JETON = argv[i + 1];      // jeton mis par la page dans son titre
        if (a == L"--parent" && i + 1 < argc) INC.parent = OpenProcess(SYNCHRONIZE, FALSE, (DWORD)_wtoi(argv[i + 1]));   // serveur
        if (a == L"--depuis" && i + 1 < argc) depuis = _wtoi(argv[i + 1]);
    }
    WNDCLASSW wc = {}; wc.lpfnWndProc = proc; wc.hInstance = inst; wc.lpszClassName = L"LecteurNatif"; wc.hCursor = LoadCursor(nullptr, IDC_ARROW);
    wc.hbrBackground = (HBRUSH)GetStockObject(BLACK_BRUSH);
    RegisterClassW(&wc);
    bool trouve = false;
    if (portInc) {                                          // incrusté dans l'Atelier : fenêtre sans bordure, possédée par la sienne
        SetProcessDpiAwarenessContext(DPI_AWARENESS_CONTEXT_PER_MONITOR_AWARE_V2);   // (pixels physiques, comme la page x devicePixelRatio)
        trouve = incruste_init(portInc);
        if (trouve) A.fen = CreateWindowExW(WS_EX_NOACTIVATE | WS_EX_TOOLWINDOW, L"LecteurNatif", L"Lecteur natif", WS_POPUP, 0, 0, A.W, A.H,
                                            INC.proprio, nullptr, inst, nullptr);
        else INC.actif = false;                             // (fenêtre de l'Atelier introuvable : fenêtre à part ; les commandes restent lues)
    }
    if (!trouve) {
        RECT r = {0, 0, A.W, A.H}; DWORD st = WS_OVERLAPPEDWINDOW & ~WS_THICKFRAME & ~WS_MAXIMIZEBOX; AdjustWindowRect(&r, st, FALSE);
        A.fen = CreateWindowW(L"LecteurNatif", L"Lecteur natif — chargement…", st, CW_USEDEFAULT, CW_USEDEFAULT, r.right - r.left, r.bottom - r.top, nullptr, nullptr, inst, nullptr);
        if (capture < 0 && fref.empty() && planche.empty()) ShowWindow(A.fen, SW_SHOW);
    }
    DXGI_SWAP_CHAIN_DESC sd = {}; sd.BufferCount = 2; sd.BufferDesc.Width = A.W; sd.BufferDesc.Height = A.H; sd.BufferDesc.Format = DXGI_FORMAT_R8G8B8A8_UNORM;
    sd.BufferUsage = DXGI_USAGE_RENDER_TARGET_OUTPUT; sd.OutputWindow = A.fen; sd.SampleDesc.Count = 1; sd.Windowed = TRUE; sd.SwapEffect = DXGI_SWAP_EFFECT_FLIP_DISCARD;
    D3D_FEATURE_LEVEL nv = D3D_FEATURE_LEVEL_11_0;
    OK(D3D11CreateDeviceAndSwapChain(nullptr, D3D_DRIVER_TYPE_HARDWARE, nullptr, 0, &nv, 1, D3D11_SDK_VERSION, &sd, &A.sc, &A.dev, nullptr, &A.ctx), "D3D11CreateDeviceAndSwapChain");
    cibles(); etats_init();
    auto t0 = std::chrono::steady_clock::now();
    bool ok = charger_decor(dos);
    if (ok && modeTech) {
        ok = charger_effets(dosTech) && charger_lums(dosTech + L"\\lums.bin") && T.charger(dosTech);
        if (ok) teintes_sommets();
        if (ok) charger_telop(dosTech + L"\\telop.bin");
        if (ok) { charger_modifs(dosTech + L"\\modifs.bin"); A.images.resize(std::max(1, T.duree())); }
    }
    else if (ok) ok = charger_effets(dos) || true, ok = lire_images(dos + L"\\images.bin", A.images, true);
    if (!ok) { if (!silencieux) MessageBoxW(A.fen, (L"Scène illisible : " + dos + L" " + dosTech).c_str(), L"Lecteur natif", MB_ICONERROR); else echec("scène illisible", 0); return 1; }
    double tc = std::chrono::duration<double>(std::chrono::steady_clock::now() - t0).count();
    int n = (int)A.images.size(); if (!n) return 1;
    if (!fref.empty()) {                                  // vérification de l'animation (sans dessiner)
        std::vector<Image> ref; if (!lire_images(fref, ref, false)) { echec("référence illisible", 0); return 1; }
        auto t1 = std::chrono::steady_clock::now(); verifier(ref, frap);
        FILE* x = _wfopen(frap.c_str(), L"a"); if (x) { fprintf(x, "\nchargement %.2f s, calcul de %d images %.2f s\n", tc, n, std::chrono::duration<double>(std::chrono::steady_clock::now() - t1).count()); fclose(x); }
        return 0;
    }
    if (!planche.empty()) {                               // planche : images dessinées dans l'ordre depuis 0, celles demandées -> BMP
        int fmax = 0; for (int x : planche) fmax = std::max(fmax, x);
        ID3D11Texture2D* bb; A.sc->GetBuffer(0, __uuidof(ID3D11Texture2D), (void**)&bb);
        D3D11_TEXTURE2D_DESC d; bb->GetDesc(&d); d.Usage = D3D11_USAGE_STAGING; d.BindFlags = 0; d.CPUAccessFlags = D3D11_CPU_ACCESS_READ; d.MiscFlags = 0;
        ID3D11Texture2D* stg; OK(A.dev->CreateTexture2D(&d, nullptr, &stg), "staging");
        for (int k = 0; k <= fmax && k < n; k++) {
            assurer_image(k); dessiner_image(k);
            if (std::find(planche.begin(), planche.end(), k) == planche.end()) continue;
            A.ctx->CopyResource(stg, bb); D3D11_MAPPED_SUBRESOURCE m; OK(A.ctx->Map(stg, 0, D3D11_MAP_READ, 0, &m), "Map lecture");
            wchar_t nom[64]; swprintf_s(nom, L"/planche_%d.bmp", k); FILE* x = _wfopen((dosPlanche + nom).c_str(), L"wb");
            if (x) { BITMAPFILEHEADER fh = {}; BITMAPINFOHEADER ih = {}; ih.biSize = sizeof ih; ih.biWidth = A.W; ih.biHeight = -A.H; ih.biPlanes = 1; ih.biBitCount = 32;
                fh.bfType = 0x4D42; fh.bfOffBits = sizeof fh + sizeof ih; fh.bfSize = fh.bfOffBits + A.W * A.H * 4;
                fwrite(&fh, sizeof fh, 1, x); fwrite(&ih, sizeof ih, 1, x); std::vector<uint8_t> ligne(A.W * 4);
                for (int y = 0; y < A.H; y++) { const uint8_t* p = (uint8_t*)m.pData + y * m.RowPitch;
                    for (int i = 0; i < A.W; i++) { ligne[4 * i] = p[4 * i + 2]; ligne[4 * i + 1] = p[4 * i + 1]; ligne[4 * i + 2] = p[4 * i]; ligne[4 * i + 3] = 255; }
                    fwrite(ligne.data(), 1, ligne.size(), x); }
                fclose(x); }
            A.ctx->Unmap(stg, 0);
            // (15/11/2026) essai du choix au clic : LECTEUR_CLICS="x,y;x,y" -> lecteur_incruste.txt
            if (const char* cl = getenv("LECTEUR_CLICS")) { std::string t = cl; size_t q = 0;
                while (q < t.size()) { int cx, cy; if (sscanf(t.c_str() + q, "%d,%d", &cx, &cy) == 2) { PICK_X = cx; PICK_Y = cy; choisir_sous_clic(k); }
                    const size_t r = t.find(';', q); if (r == std::string::npos) break; q = r + 1; } }
        }
        return 0;
    }
    if (capture >= 0) {                                   // (avec --depuis : les images d'avant sont dessinées pour l'adaptation)
        assurer_image(capture % n);
        for (int k = std::max(0, depuis); depuis >= 0 && k < capture % n; k++) dessiner_image(k);
        dessiner_image(capture % n);
        ID3D11Texture2D* bb; A.sc->GetBuffer(0, __uuidof(ID3D11Texture2D), (void**)&bb);
        D3D11_TEXTURE2D_DESC d; bb->GetDesc(&d); d.Usage = D3D11_USAGE_STAGING; d.BindFlags = 0; d.CPUAccessFlags = D3D11_CPU_ACCESS_READ; d.MiscFlags = 0;
        ID3D11Texture2D* stg; OK(A.dev->CreateTexture2D(&d, nullptr, &stg), "staging"); A.ctx->CopyResource(stg, bb);
        D3D11_MAPPED_SUBRESOURCE m; OK(A.ctx->Map(stg, 0, D3D11_MAP_READ, 0, &m), "Map lecture");
        FILE* x = _wfopen(fcap.c_str(), L"wb");
        for (int y = 0; y < A.H; y++) fwrite((uint8_t*)m.pData + y * m.RowPitch, 1, A.W * 4, x);
        fclose(x); A.ctx->Unmap(stg, 0); return 0;
    }
    auto avant = std::chrono::steady_clock::now(); double ips = 0, acc = 0; int cpt = 0, prec = -1;
    MSG msg = {}; INC.dernier = GetTickCount64();       // (délai de la page compté depuis la fin du chargement)
    while (msg.message != WM_QUIT) {
        if (PeekMessageW(&msg, nullptr, 0, 0, PM_REMOVE)) { TranslateMessage(&msg); DispatchMessageW(&msg); continue; }
        // commandes de la page (barre de lecture, pause, image, textures) : aussi quand la fenêtre de l'Atelier n'a pas été trouvée
        if (INC.s != INVALID_SOCKET) incruste_commandes(n, prec < 0 ? 0 : prec, pause, temps, pasManuel);
        if (portInc && incruste_abandonne()) break;      // (14/11/2026) lecteur orphelin : fermé
        if (INC.actif) {                                   // incrusté : place sur la vue
            if (!INC.proprio) break;
            incruste_placer();
            if (!INC.visible) { Sleep(15); avant = std::chrono::steady_clock::now(); continue; } }
        auto maint = std::chrono::steady_clock::now(); double dt = std::chrono::duration<double>(maint - avant).count(); avant = maint;
        if (!pause) temps += dt;
        temps += pasManuel / 60.0; pasManuel = 0; if (temps < 0) temps = 0;
        int f = (int)(temps * 60) % n;
        if (f < prec) A.premiere = true;                 // (retour au début : la luminosité repart de la 1re image)
        prec = f;
        assurer_image(f);
        dessiner_image(f);
        A.sc->Present(1, 0);
        choisir_sous_clic(f);                            // (15/11/2026) clic sur l'image -> pièce choisie
        acc += dt; cpt++;
        if (acc >= 0.5) { ips = cpt / acc; acc = 0; cpt = 0; INC.ips = ips;
            wchar_t t[256]; swprintf_s(t, L"Lecteur natif — image %d / %d — %.0f images/s — %zu + %zu dessins — effets d'écran %s (E) — chargé en %.1f s%s", f, n, ips,
                                       A.dessins.size(), A.images[f].effets.size(), A.effetsEcran ? L"oui" : L"non", tc, pause ? L" — PAUSE" : L"");
            SetWindowTextW(A.fen, t); }
    }
    return 0;
}
