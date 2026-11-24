// ANIMATION DU LECTEUR NATIF (14/11/2026) — calculée ici, image par image, comme la page de l'Atelier la calculait :
// port EXACT de web/anim3d.js (squelettes, clips, accroches, caméra), web/particules.js (émetteurs du jeu, hasard
// mt19937, arrondis 32 bits de Math.fround) et des parties « animation » de web/vue3d.js (_animer, _calculerLumieres,
// _avancerEmetteur, _quadsEmetteur, _peauEffet, _carteOmbre / cascadesOmbre) et web/app.js (rendreD3D : dessins des
// effets, personnages, ombre des pieds). Même ordre des calculs et mêmes arrondis : les matrices de la page sont des
// Float32Array (arrondies en 32 bits à chaque écriture), les calculs intermédiaires en 64 bits (nombres de JavaScript).
// Math.hypot reprend l'algorithme de V8 (somme de Kahan, normalisée par le plus grand).
// Données : scenes/tech_<code>/tech.json (AtelierNatif/exporter.py, exporter_technique).
#pragma once
#include <array>
#include <map>

// ====================================================================== JSON (lecture seule, comme JSON.parse)
struct JV {
    enum Type : uint8_t { UNDEF, NUL, BOOL, NUM, STR, ARR, OBJ } t = UNDEF;
    bool b = false; double n = 0; std::string s;
    std::vector<JV> a; std::vector<std::pair<std::string, JV>> o;
    static const JV& vide() { static JV v; return v; }
    const JV& operator[](const char* k) const { if (t == OBJ) for (auto& p : o) if (p.first == k) return p.second; return vide(); }
    const JV& operator[](const std::string& k) const { return (*this)[k.c_str()]; }
    const JV& operator[](size_t i) const { if (t == ARR && i < a.size()) return a[i]; return vide(); }
    const JV& operator[](int i) const { return (*this)[(size_t)i]; }
    bool existe() const { return t != UNDEF; }
    bool vrai() const {                                  // vérité de JavaScript
        switch (t) { case BOOL: return b; case NUM: return n != 0 && n == n; case STR: return !s.empty(); case ARR: case OBJ: return true; default: return false; }
    }
    double num() const {                                 // Number(x) : undefined -> NaN, null -> 0
        switch (t) { case NUM: return n; case BOOL: return b ? 1 : 0; case NUL: return 0; case STR: return strtod(s.c_str(), nullptr); default: return NAN; }
    }
    size_t taille() const { return t == ARR ? a.size() : t == OBJ ? o.size() : 0; }
};
struct LecteurJSON {
    const char* p; const char* fin;
    void blancs() { while (p < fin && (*p == ' ' || *p == '\n' || *p == '\r' || *p == '\t')) p++; }
    static void utf8(std::string& s, uint32_t c) {
        if (c < 0x80) s += (char)c;
        else if (c < 0x800) { s += (char)(0xC0 | (c >> 6)); s += (char)(0x80 | (c & 63)); }
        else if (c < 0x10000) { s += (char)(0xE0 | (c >> 12)); s += (char)(0x80 | ((c >> 6) & 63)); s += (char)(0x80 | (c & 63)); }
        else { s += (char)(0xF0 | (c >> 18)); s += (char)(0x80 | ((c >> 12) & 63)); s += (char)(0x80 | ((c >> 6) & 63)); s += (char)(0x80 | (c & 63)); }
    }
    std::string chaine() {
        std::string s; p++;
        while (p < fin && *p != '"') {
            if (*p == '\\') { p++; char c = *p++;
                if (c == 'n') s += '\n'; else if (c == 't') s += '\t'; else if (c == 'r') s += '\r'; else if (c == 'b') s += '\b'; else if (c == 'f') s += '\f';
                else if (c == 'u') { uint32_t u = (uint32_t)strtoul(std::string(p, 4).c_str(), nullptr, 16); p += 4;
                    if (u >= 0xD800 && u < 0xDC00 && p + 6 <= fin && p[0] == '\\' && p[1] == 'u') {
                        uint32_t v = (uint32_t)strtoul(std::string(p + 2, 4).c_str(), nullptr, 16); p += 6; u = 0x10000 + ((u - 0xD800) << 10) + (v - 0xDC00); }
                    utf8(s, u); }
                else s += c; }
            else s += *p++;
        }
        p++; return s;
    }
    void valeur(JV& v) {
        blancs();
        char c = *p;
        if (c == '{') { v.t = JV::OBJ; p++; blancs();
            if (*p == '}') { p++; return; }
            for (;;) { blancs(); std::string k = chaine(); blancs(); p++; v.o.emplace_back(std::move(k), JV()); valeur(v.o.back().second); blancs();
                if (*p == ',') { p++; continue; } p++; return; } }
        if (c == '[') { v.t = JV::ARR; p++; blancs();
            if (*p == ']') { p++; return; }
            for (;;) { v.a.emplace_back(); valeur(v.a.back()); blancs(); if (*p == ',') { p++; continue; } p++; return; } }
        if (c == '"') { v.t = JV::STR; v.s = chaine(); return; }
        if (c == 't') { v.t = JV::BOOL; v.b = true; p += 4; return; }
        if (c == 'f') { v.t = JV::BOOL; v.b = false; p += 5; return; }
        if (c == 'n') { v.t = JV::NUL; p += 4; return; }
        if (c == 'N') { v.t = JV::NUM; v.n = NAN; p += 3; return; }
        if (c == 'I') { v.t = JV::NUM; v.n = INFINITY; p += 8; return; }
        if (c == '-' && p + 1 < fin && p[1] == 'I') { v.t = JV::NUM; v.n = -INFINITY; p += 9; return; }
        v.t = JV::NUM; char* e; v.n = strtod(p, &e); p = e;
    }
};
static bool lire_json(const std::wstring& f, JV& v) {
    Lecteur L; if (!L.ouvrir(f)) return false;
    LecteurJSON J{(const char*)L.d.data(), (const char*)L.d.data() + L.d.size()}; J.valeur(v); return true;
}

// ====================================================================== nombres de JavaScript
static inline double F(double x) { return (double)(float)x; }          // Math.fround
static inline double ou(double x, double d) { return (x != 0 && x == x) ? x : d; }   // x || d
static double hypotJS(const double* v, int n) {                        // Math.hypot de V8 (builtins/math.tq)
    double ab[8] = {}, mx = 0; bool nan = false;
    for (int i = 0; i < n; i++) { double x = v[i]; if (x != x) nan = true; else { ab[i] = fabs(x); if (ab[i] > mx) mx = ab[i]; } }
    if (mx == INFINITY) return INFINITY;
    if (nan) return NAN;
    if (mx == 0) return 0;
    double sum = 0, comp = 0;
    for (int i = 0; i < n; i++) { double q = ab[i] / mx; double summand = q * q - comp; double prel = sum + summand; comp = (prel - sum) - summand; sum = prel; }
    return sqrt(sum) * mx;
}
static inline double hyp3(double a, double b, double c) { double v[3] = {a, b, c}; return hypotJS(v, 3); }
static inline double hyp4(double a, double b, double c, double d) { double v[4] = {a, b, c, d}; return hypotJS(v, 4); }

typedef std::array<float, 16> M4;                                      // Float32Array(16), colonne par colonne
static M4 I4f() { M4 m{}; m[0] = m[5] = m[10] = m[15] = 1; return m; }
static M4 mulF(const M4& a, const M4& b) {
    M4 o; for (int i = 0; i < 4; i++) for (int j = 0; j < 4; j++) { double s = 0; for (int k = 0; k < 4; k++) s += (double)a[k * 4 + j] * (double)b[i * 4 + k]; o[i * 4 + j] = (float)s; }
    return o;
}
static M4 trs(const double* t, const double* q, const double* e) {    // anim3d.js trs : T x R x S
    double x = q[0], y = q[1], z = q[2], w = q[3]; const double n = ou(hyp4(x, y, z, w), 1); x /= n; y /= n; z /= n; w /= n;
    M4 m{};
    m[0] = (float)((1 - 2 * (y * y + z * z)) * e[0]); m[1] = (float)((2 * (x * y + z * w)) * e[0]); m[2] = (float)((2 * (x * z - y * w)) * e[0]);
    m[4] = (float)((2 * (x * y - z * w)) * e[1]); m[5] = (float)((1 - 2 * (x * x + z * z)) * e[1]); m[6] = (float)((2 * (y * z + x * w)) * e[1]);
    m[8] = (float)((2 * (x * z + y * w)) * e[2]); m[9] = (float)((2 * (y * z - x * w)) * e[2]); m[10] = (float)((1 - 2 * (x * x + y * y)) * e[2]);
    m[12] = (float)t[0]; m[13] = (float)t[1]; m[14] = (float)t[2]; m[15] = 1; return m;
}
static M4 inverseA(const M4& m) {                                      // anim3d.js inverse (affine)
    const double a = m[0], b = m[1], c = m[2], d = m[4], e = m[5], f = m[6], g = m[8], h = m[9], i = m[10];
    const double A_ = e * i - f * h, B_ = -(d * i - f * g), C_ = d * h - e * g, det = ou(a * A_ + b * B_ + c * C_, 1e-9);
    M4 o{};
    o[0] = (float)(A_ / det); o[1] = (float)(-(b * i - c * h) / det); o[2] = (float)((b * f - c * e) / det);
    o[4] = (float)(B_ / det); o[5] = (float)((a * i - c * g) / det); o[6] = (float)(-(a * f - c * d) / det);
    o[8] = (float)(C_ / det); o[9] = (float)(-(a * h - b * g) / det); o[10] = (float)((a * e - b * d) / det);
    o[12] = (float)(-((double)m[12] * o[0] + (double)m[13] * o[4] + (double)m[14] * o[8]));
    o[13] = (float)(-((double)m[12] * o[1] + (double)m[13] * o[5] + (double)m[14] * o[9]));
    o[14] = (float)(-((double)m[12] * o[2] + (double)m[13] * o[6] + (double)m[14] * o[10])); o[15] = 1; return o;
}
static M4 inv4GJ(const M4& m) {                                        // vue3d.js inv4 (Gauss-Jordan)
    double r[4][8];
    for (int i = 0; i < 4; i++) { r[i][0] = m[i]; r[i][1] = m[4 + i]; r[i][2] = m[8 + i]; r[i][3] = m[12 + i]; for (int j = 0; j < 4; j++) r[i][4 + j] = i == j ? 1 : 0; }
    for (int c = 0; c < 4; c++) {
        int p = c; for (int i = c + 1; i < 4; i++) if (fabs(r[i][c]) > fabs(r[p][c])) p = i;
        if (p != c) for (int j = 0; j < 8; j++) std::swap(r[c][j], r[p][j]);
        const double d = r[c][c]; for (int j = 0; j < 8; j++) r[c][j] /= d;
        for (int i = 0; i < 4; i++) if (i != c) { const double f = r[i][c]; for (int j = 0; j < 8; j++) r[i][j] -= f * r[c][j]; }
    }
    M4 o; for (int i = 0; i < 4; i++) for (int j = 0; j < 4; j++) o[j * 4 + i] = (float)r[i][4 + j]; return o;
}
static void versD(const M4& m, double* o) { for (int i = 0; i < 16; i++) o[i] = m[i]; }

// ====================================================================== anim3d.js
struct Canal { int type = 0; bool interp = false; std::vector<double> im; int dim = 1; std::vector<double> v; double prm = 0; };
struct CibleClip { uint32_t crc; std::vector<Canal> canaux; };
struct Clip { double debut = 0, fin = 0, fps = 60; std::vector<CibleClip> cibles; };
static void lire_clip(const JV& j, Clip& c) {
    c.debut = j["debut"].num(); c.fin = j["fin"].num(); c.fps = ou(j["fps"].num(), 60);
    for (auto& x : j["cibles"].a) { CibleClip cc; cc.crc = (uint32_t)(int64_t)x["crc"].num();
        for (auto& k : x["canaux"].a) { Canal ch; ch.type = (int)k["type"].num(); ch.interp = k["interp"].vrai(); ch.prm = ou(k["prm"].num(), 0);
            for (auto& i : k["images"].a) ch.im.push_back(i.num());
            const JV& V = k["valeurs"]; ch.dim = V.taille() ? (int)std::max<size_t>(1, V[0].taille()) : 1;
            for (auto& vv : V.a) for (int d = 0; d < ch.dim; d++) ch.v.push_back(vv[d].num());
            cc.canaux.push_back(std::move(ch)); }
        c.cibles.push_back(std::move(cc)); }
}
static void lire_clips(const JV& j, std::map<std::string, Clip>& out) { if (j.t == JV::OBJ) for (auto& p : j.o) lire_clip(p.second, out[p.first]); }
struct Ech { double v[4]; int n; };
static Ech echantillon(const Canal& ch, double f) {
    const std::vector<double>& im = ch.im; const size_t n = im.size(); const int D = ch.dim; Ech r; r.n = D;
    auto val = [&](size_t i) { for (int d = 0; d < D && d < 4; d++) r.v[d] = ch.v[i * D + d]; return r; };
    if (n == 1 || f <= im[0]) return val(0);
    if (f >= im[n - 1]) return val(n - 1);
    size_t lo = 0, hi = n - 1;
    while (hi - lo > 1) { size_t m = (lo + hi) >> 1; if (im[m] <= f) lo = m; else hi = m; }
    if (!ch.interp) return val(lo);
    const double t = (f - im[lo]) / ou(im[hi] - im[lo], 1);
    const double* a = &ch.v[lo * D]; const double* b = &ch.v[hi * D];
    if (ch.type == 9) { const double d = a[0] * b[0] + a[1] * b[1] + a[2] * b[2] + a[3] * b[3], s = d < 0 ? -1 : 1;
        for (int k = 0; k < 4; k++) r.v[k] = a[k] * (1 - t) + s * b[k] * t; r.n = 4; return r; }
    for (int k = 0; k < D && k < 4; k++) r.v[k] = a[k] * (1 - t) + b[k] * t;
    return r;
}
struct OsJ { std::string nom; uint32_t crc; int parent; double e[3], r[4], t[3]; int drap = 0; bool aIb = false; float ib[12] = {}; };
// os « panneaux » (anim3d.js panneau ; LU dans nie.exe 0x14052a200)
static M4 panneau(const M4& m, int mode, const M4& c) {
    const double d[3] = {(double)c[12] - m[12], (double)c[13] - m[13], (double)c[14] - m[14]}, dd = d[0] * d[0] + d[1] * d[1] + d[2] * d[2];
    if (!(dd > 0) || !std::isfinite(dd)) return m;
    double s[3]; for (int k = 0; k < 3; k++) s[k] = sqrt((double)m[4 * k] * m[4 * k] + (double)m[4 * k + 1] * m[4 * k + 1] + (double)m[4 * k + 2] * m[4 * k + 2]);
    auto nz = [](const double* v, double* o) { const double l = sqrt(v[0] * v[0] + v[1] * v[1] + v[2] * v[2]); o[0] = v[0] / l; o[1] = v[1] / l; o[2] = v[2] / l; };
    auto cr = [](const double* a, const double* b, double* o) { o[0] = a[1] * b[2] - a[2] * b[1]; o[1] = a[2] * b[0] - a[0] * b[2]; o[2] = a[0] * b[1] - a[1] * b[0]; };
    auto ok = [](const double* v) { const double q = v[0] * v[0] + v[1] * v[1] + v[2] * v[2]; return q > 0 && std::isfinite(q); };
    double X[3], Y[3], Z[3], t[3];
    if (mode == 3) { double a[3] = {-(double)c[0], -(double)c[1], -(double)c[2]}, b[3] = {c[4], c[5], c[6]}, e[3] = {-(double)c[8], -(double)c[9], -(double)c[10]}; nz(a, X); nz(b, Y); nz(e, Z); }
    else if (mode == 2) { double y[3] = {m[4], m[5], m[6]}; nz(y, Y); cr(Y, d, t); if (!ok(t)) return m; nz(t, X); double z[3]; cr(X, Y, z); nz(z, Z); }
    else { nz(d, Z); double u[3] = {c[4], c[5], c[6]}, un[3]; nz(u, un); cr(un, Z, t); if (!ok(t)) return m; nz(t, X); double y[3]; cr(Z, X, y); nz(y, Y); }
    M4 o = m;
    for (int k = 0; k < 3; k++) { o[k] = (float)(X[k] * s[0]); o[4 + k] = (float)(Y[k] * s[1]); o[8 + k] = (float)(Z[k] * s[2]); }
    return o;
}
struct Loc { double t[3], r[4], e[3]; };
struct Squelette {
    std::vector<OsJ> os; int n = 0; std::unordered_map<uint32_t, int> parCrc; std::unordered_map<std::string, int> parNom;
    std::vector<Loc> repos, local; std::vector<M4> monde, mondeRepos; std::vector<char> cache;
    bool nus = false, panneaux = false; int g4sk = 0;
    void init(const JV& j, const JV* opts = nullptr) {
        if (opts) { nus = (*opts)["nus"].vrai(); g4sk = (int)ou((*opts)["g4sk"].num(), 0); }
        for (auto& x : j.a) { OsJ o; o.nom = x["nom"].s; o.crc = (uint32_t)(int64_t)x["crc"].num(); o.parent = (int)x["parent"].num(); o.drap = (int)ou(x["drap"].num(), 0);
            if ((g4sk & 2) && ((o.drap >> 1) & 15)) panneaux = true;
            for (int k = 0; k < 3; k++) { o.e[k] = x["e"][k].num(); o.t[k] = x["t"][k].num(); } for (int k = 0; k < 4; k++) o.r[k] = x["r"][k].num();
            if (x["ib"].a.size() == 12) { o.aIb = true; for (int k = 0; k < 12; k++) o.ib[k] = (float)x["ib"][k].num(); }   // liaison (G4SK table 0)
            os.push_back(o); }
        n = (int)os.size();
        for (int i = 0; i < n; i++) { parCrc[os[i].crc] = i; parNom[os[i].nom] = i; }
        repos.resize(n); for (int i = 0; i < n; i++) { memcpy(repos[i].t, os[i].t, 24); memcpy(repos[i].r, os[i].r, 32); memcpy(repos[i].e, os[i].e, 24); }
        poser(nullptr, 0, nullptr); mondeRepos = monde;
    }
    int nom(const std::string& s) const { auto i = parNom.find(s); return i == parNom.end() ? -1 : i->second; }
    void poser(const Clip* clip, double f, const Clip* vis, const M4* cam = nullptr) {
        std::vector<Loc> loc = repos;
        if (clip) for (auto& c : clip->cibles) { auto it = parCrc.find(c.crc); if (it == parCrc.end()) continue; Loc& L = loc[it->second];
            for (auto& ch : c.canaux) { Ech v = echantillon(ch, f); const int t = ch.type;
                if (t >= 1 && t <= 3) L.e[t - 1] = v.v[0]; else if (t == 9) { for (int k = 0; k < 4; k++) L.r[k] = v.v[k]; } else if (t >= 10 && t <= 12) L.t[t - 10] = v.v[0]; } }
        std::vector<char> cache_(n, 0);
        if (vis) for (auto& c : vis->cibles) { auto it = parCrc.find(c.crc); if (it == parCrc.end()) continue;
            for (auto& ch : c.canaux) if (ch.type == 15 && echantillon(ch, f).v[0] < 0.5) cache_[it->second] = 1; }
        std::vector<M4> m(n); std::vector<char> fait(n, 0); cache.assign(n, 0);
        for (int i = 0; i < n; i++) {
            const int p = os[i].parent; M4 x = trs(loc[i].t, loc[i].r, loc[i].e);
            if (p >= 0 && p < n && fait[p]) {
                const double* sp = loc[p].e;
                if (nus && (F(sp[0]) != 1 || F(sp[1]) != 1 || F(sp[2]) != 1)) {      // compensation d'échelle (0x140529aa0)
                    const M4& P = m[p]; M4 Aa = P;
                    for (int j = 0; j < 3; j++) { const double e = F(sp[j]), k = e != 0 ? F(1 / e) : 0; for (int r = 0; r < 3; r++) Aa[4 * j + r] = (float)F((double)P[4 * j + r] * k); }
                    M4 Mx = mulF(Aa, x);
                    for (int r = 0; r < 3; r++) Mx[12 + r] = (float)((double)P[r] * x[12] + (double)P[4 + r] * x[13] + (double)P[8 + r] * x[14] + P[12 + r]);
                    m[i] = Mx;
                } else m[i] = mulF(m[p], x);
            } else m[i] = x;
            fait[i] = 1;
            const int md = (os[i].drap >> 1) & 15;
            if (cam && md && (g4sk & 2)) m[i] = panneau(m[i], md, *cam);
            cache[i] = cache_[i] || (p >= 0 && p < n && p < i && cache[p]);
        }
        monde = std::move(m); local = std::move(loc);
    }
};
struct Ordre { double image; bool aJouer = false; std::string jouer; bool boucle = false; bool aVisible = false, visible = false; bool aAcc = false; std::string acc0, acc1;
                bool aFondu = false; double fondu = 1, fonduImages = 0; };   // (15/11/2026) fondu du modèle (anim3d.js)
static void lire_ordres(const JV& j, std::vector<Ordre>& out) {
    for (auto& x : j.a) { Ordre o; o.image = x["image"].num();
        if (x["jouer"].vrai()) { o.aJouer = true; o.jouer = x["jouer"].s; o.boucle = x["boucle"].vrai(); }
        if (x["visible"].existe()) { o.aVisible = true; o.visible = x["visible"].vrai(); }
        if (x["accroche"].vrai()) { o.aAcc = true; o.acc0 = x["accroche"][0].s; o.acc1 = x["accroche"][1].s; }
        if (x["fondu"].vrai()) { o.aFondu = true; o.fondu = x["fondu"][0].num(); o.fonduImages = x["fondu"][1].num(); }
        out.push_back(o); }
}
struct ObjetA { std::string acteur; Squelette sq; std::map<std::string, Clip> clips, vis, opa, uv; std::vector<Ordre> ordres;
               const Clip* pCl = nullptr; double pT = 0; const Clip* pVis = nullptr; };
struct PointA { std::string nom; Squelette sq; std::map<std::string, Clip> clips; };
struct ActeurA { std::string acteur; Squelette sq; std::vector<M4> invRepos; std::map<std::string, Clip> clips; std::vector<Ordre> ordres;
                 struct Col { std::string os; double dec[3], taille[3]; }; std::vector<Col> collision; bool aCollision = false; };
struct Plan { std::string nom; double debut, fin; };
struct ObjRes {
    std::vector<M4> monde; std::vector<char> cache; std::vector<Loc> local; bool visible = false; M4 racine; bool ecran2D = false;
    std::unordered_map<uint32_t, double> opa; std::unordered_map<uint32_t, std::vector<std::array<double, 3>>> prm, col;
    std::unordered_map<uint32_t, std::map<int, double>> uvc; bool aClip = false; std::string clip;
};
struct Res {
    int plan = -1; std::vector<ObjRes> objets; std::unordered_map<std::string, std::vector<M4>> peaux; std::unordered_map<std::string, double> fondus;
    bool aCamera = false; double oeil[3], cible[3], roulis = 0, champ = 0; bool decorFaux = false;
    bool aCamM = false; M4 camM{};      // (14/11/2026) caméra -> monde (pièces panneaux par matériau)
};
// (21/11) sans commande d'accroche 0xA2D1F942 : AUCUNE accroche (repère de la cinématique), LU nie.exe 0x140f3afd0 -> 0x1418161a0 ;
// avant : point_eff/evp_eff01 d'office (déduit), 38 cinématiques décalées (Bouclier royal). Comme anim3d.js _etat.
struct EtatO { const std::string* jouer = nullptr; double depuis = 0; bool visible = false; std::string acc0, acc1; bool boucle = false; };
static EtatO etat_ordres(const std::vector<Ordre>& ordres, double f) {
    EtatO e;
    for (auto& x : ordres) { if (x.image > f) break;
        if (x.aJouer) { e.jouer = &x.jouer; e.depuis = x.image; e.boucle = x.boucle; } if (x.aVisible) e.visible = x.visible; if (x.aAcc) { e.acc0 = x.acc0; e.acc1 = x.acc1; } }
    return e;
}
static const Clip* clip_de(const std::map<std::string, Clip>& m, const std::string* nom) { if (!nom) return nullptr; auto i = m.find(*nom); return i == m.end() ? nullptr : &i->second; }
static const Clip* clip_de(const std::map<std::string, Clip>& m, const std::string& nom) { auto i = m.find(nom); return i == m.end() ? nullptr : &i->second; }

struct LecteurAnim {
    double duree = 1; std::vector<Plan> plans; std::vector<ObjetA> objets; std::unordered_map<std::string, int> objetDe;
    bool aPe = false; Squelette pe; std::map<std::string, Clip> peClips;
    std::vector<PointA> points; std::vector<ActeurA> acteurs;
    std::map<std::string, Clip> camera;
    bool aD = false, aDE = false; M4 TD, TE;
    struct Decor { double image; bool faux; }; std::vector<Decor> decor;
    void init(const JV& d) {
        duree = ou(d["duree"].num(), 1);
        for (auto& p : d["plans"].a) plans.push_back({p["nom"].s, p["debut"].num(), p["fin"].num()});
        for (auto& p : d["objets"].o) { const JV& o = p.second; if (!o["os"].taille()) continue;
            ObjetA x; x.acteur = p.first; x.sq.init(o["os"], &o); lire_clips(o["clips"], x.clips); lire_clips(o["vis"], x.vis); lire_clips(o["opa"], x.opa); lire_clips(o["uv"], x.uv);
            lire_ordres(o["ordres"], x.ordres); objetDe[x.acteur] = (int)objets.size(); objets.push_back(std::move(x)); }
        if (d["point_eff"].vrai()) { aPe = true; pe.init(d["point_eff"]["os"]); lire_clips(d["point_eff"]["clips"], peClips); }
        if (d["points"].t == JV::OBJ) for (auto& p : d["points"].o) { PointA x; x.nom = p.first; x.sq.init(p.second["os"]); lire_clips(p.second["clips"], x.clips); points.push_back(std::move(x)); }
        for (auto& a : d["acteurs"].a) { ActeurA x; x.acteur = a["acteur"].s; x.sq.init(a["os"], &a); for (auto& m : x.sq.mondeRepos) x.invRepos.push_back(inverseA(m));
            lire_clips(a["clips"], x.clips); lire_ordres(a["ordres"], x.ordres);
            if (a["collision"].vrai()) { x.aCollision = true;
                for (auto& c : a["collision"].a) { ActeurA::Col k; k.os = c["os"].s; for (int i = 0; i < 3; i++) { k.dec[i] = c["decalage"][i].num(); k.taille[i] = c["taille"][i].num(); } x.collision.push_back(k); } }
            acteurs.push_back(std::move(x)); }
        lire_clips(d["camera"], camera);
        const JV& D = d["decalage_points"]; if (D.vrai()) { aD = true; TD = I4f(); TD[12] = (float)D[0].num(); TD[13] = (float)D[1].num(); TD[14] = (float)D[2].num(); }
        const JV& DE = d["decalage_eff"]; if (DE.vrai()) { aDE = true; TE = I4f(); TE[12] = (float)DE[0].num(); TE[13] = (float)DE[1].num(); TE[14] = (float)DE[2].num(); }
        for (auto& x : d["decor"].a) decor.push_back({x["image"].num(), x["visible"].t == JV::BOOL && !x["visible"].b});
    }
    bool cameraMonde(const Plan* p, double dans, M4& out) const {     // anim3d.js _cameraMonde
        if (!p) return false; const Clip* cl = clip_de(camera, p->nom); if (!cl) return false;
        std::map<int, double> ch; for (auto& c : cl->cibles) for (auto& k : c.canaux) ch[k.type] = echantillon(k, cl->debut + dans).v[0];
        if (!ch.count(22) || !ch.count(26)) return false;
        const double oe[3] = {ch[22], ch[23], ch[24]}, ci[3] = {ch[26], ch[27], ch[28]}, r = -ou(ch.count(30) ? ch[30] : NAN, 0); /* (14/11/2026) roulis du canal 30 de SENS OPPOSÉ à notre vue : LU nie.exe 0x1404c7420 (quaternion de la caméra, émulé) */
        auto nm = [](double* v) { const double l = ou(hyp3(v[0], v[1], v[2]), 1); v[0] /= l; v[1] /= l; v[2] /= l; };
        double z[3] = {oe[0] - ci[0], oe[1] - ci[1], oe[2] - ci[2]}; nm(z);
        const double a0 = 0, a1 = 1, a2 = 0; double x[3] = {a1 * z[2] - a2 * z[1], a2 * z[0] - a0 * z[2], a0 * z[1] - a1 * z[0]}; nm(x);
        const double y[3] = {z[1] * x[2] - z[2] * x[1], z[2] * x[0] - z[0] * x[2], z[0] * x[1] - z[1] * x[0]};
        const double c = cos(r), s = sin(r); double x2[3], y2[3];
        for (int k = 0; k < 3; k++) { x2[k] = x[k] * c + y[k] * s; y2[k] = y[k] * c - x[k] * s; }
        const double v[16] = {x2[0], x2[1], x2[2], 0, y2[0], y2[1], y2[2], 0, z[0], z[1], z[2], 0, oe[0], oe[1], oe[2], 1};
        for (int i = 0; i < 16; i++) out[i] = (float)v[i];
        return true;
    }
    int plan(double f) const { for (size_t i = 0; i < plans.size(); i++) if (f >= plans[i].debut && f < plans[i].fin) return (int)i; return plans.empty() ? -1 : (int)plans.size() - 1; }
    M4 dep(const M4& m) const { return aD ? mulF(TD, m) : m; }
    M4 depE(const M4& m) const { return aDE ? mulF(TE, dep(m)) : dep(m); }
    void calculer(double f, Res& res) {
        const int pi = plan(f); const Plan* p = pi >= 0 ? &plans[pi] : nullptr; const double dans = p ? f - p->debut : f;
        res = Res(); res.plan = pi; res.objets.resize(objets.size());
        std::unordered_map<std::string, M4> racine; racine["evp_eff01"] = depE(I4f());
        if (aPe && p) { const Clip* cl = clip_de(peClips, p->nom);
            if (cl) { pe.poser(cl, cl->debut + dans, nullptr); racine.clear(); for (auto& x : pe.parNom) racine[x.first] = depE(pe.monde[x.second]); } }
        for (size_t k = 0; k < objets.size(); k++) { ObjetA& o = objets[k]; ObjRes& R = res.objets[k];
            EtatO e = etat_ordres(o.ordres, f); const Clip* cl = clip_de(o.clips, e.jouer);
            const double ec = cl ? (f - e.depuis) * cl->fps / 60 : 0;
            const double t = cl ? cl->debut + (e.boucle ? fmod(ec, cl->fin - cl->debut + 1) : ec) : 0;
            o.sq.poser(cl, t, cl ? clip_de(o.vis, e.jouer) : nullptr);
            o.pCl = cl; o.pT = t; o.pVis = cl ? clip_de(o.vis, e.jouer) : nullptr;
            const Clip* co = cl ? clip_de(o.opa, e.jouer) : nullptr;
            if (co) for (auto& c : co->cibles) for (auto& ch : c.canaux) { const double v = echantillon(ch, t).v[0];
                if (ch.type == 19 && ch.prm == 0) R.opa[c.crc] = std::max(0.0, std::min(1.0, v));
                else if (ch.type >= 16 && ch.type <= 19) R.col[c.crc].push_back({ch.prm, (double)(ch.type - 16), v});     // couleurs (G4MA 16-19)
                else if (ch.type >= 32 && ch.type <= 35) R.prm[c.crc].push_back({ch.prm, (double)(ch.type - 32), v}); }
            const Clip* cu = cl ? clip_de(o.uv, e.jouer) : nullptr;
            if (cu) for (auto& c : cu->cibles) { std::map<int, double> brut; for (auto& ch : c.canaux) brut[ch.type] = echantillon(ch, t).v[0]; R.uvc[c.crc] = brut; }
            R.monde = o.sq.monde; R.cache = o.sq.cache; R.local = o.sq.local; R.visible = e.visible && cl;
            auto it = racine.find(e.acc1); R.racine = it != racine.end() ? it->second : I4f();
            R.aClip = e.jouer != nullptr; if (e.jouer) R.clip = *e.jouer;
        }
        std::unordered_map<std::string, std::unordered_map<std::string, M4>> rac;
        for (auto& pt : points) { const Clip* cl = p ? clip_de(pt.clips, p->nom) : nullptr; pt.sq.poser(cl, cl ? cl->debut + dans : 0, nullptr);
            auto& r = rac[pt.nom]; for (auto& x : pt.sq.parNom) r[x.first] = pt.nom == "point_eff" ? depE(pt.sq.monde[x.second]) : dep(pt.sq.monde[x.second]); }
        std::unordered_map<std::string, std::unordered_map<std::string, M4>> mondeActeur;
        for (auto& a : acteurs) {
            const std::string* jouer = nullptr; double depuis = 0; bool visible = false; bool aAcc = false; std::string acc0, acc1;
            // (15/11/2026) fondu du modèle (commande 0x48A58CDC, LU) : comme anim3d.js
            double fde = 1, fvers = 1, f0 = 0, fd = 0;
            auto fval = [&](double t) { return fd > 0 ? fde + (fvers - fde) * std::min(1.0, std::max(0.0, (t - f0) / fd)) : fvers; };
            for (auto& x : a.ordres) { if (x.image > f) break; if (x.aJouer) { jouer = &x.jouer; depuis = x.image; } if (x.aVisible) visible = x.visible; if (x.aAcc) { aAcc = true; acc0 = x.acc0; acc1 = x.acc1; }
                if (x.aFondu) { fde = fval(x.image); fvers = x.fondu; fd = x.fonduImages; f0 = x.image; } }
            { const double fv = fval(f); res.fondus[a.acteur] = fv; if (fv <= 0.001) visible = false; }
            const Clip* cl = clip_de(a.clips, jouer); if (!cl) continue;
            a.sq.poser(cl, cl->debut + (f - depuis), nullptr);
            M4 r = I4f(); if (aAcc) { auto i = rac.find(acc0); if (i != rac.end()) { auto j = i->second.find(acc1); if (j != i->second.end()) r = j->second; } }
            auto& mondes = mondeActeur[a.acteur]; for (auto& x : a.sq.parNom) mondes[x.first] = mulF(r, a.sq.monde[x.second]);
            if (visible) { auto& P = res.peaux[a.acteur]; P.resize(a.sq.n); for (int b = 0; b < a.sq.n; b++) P[b] = mulF(r, mulF(a.sq.monde[b], a.invRepos[b])); }
        }
        for (size_t k = 0; k < objets.size(); k++) { ObjRes& o = res.objets[k]; EtatO e = etat_ordres(objets[k].ordres, f);
            if (e.acc0 == "camera") { o.racine = I4f(); o.ecran2D = true; continue; }
            auto i = rac.find(e.acc0); if (i != rac.end()) { auto j = i->second.find(e.acc1); if (j != i->second.end()) { o.racine = j->second; continue; } }
            auto a = mondeActeur.find(e.acc0);
            if (a != mondeActeur.end()) { auto j = a->second.find(e.acc1);
                if (j != a->second.end()) { o.racine = j->second;
                    const Squelette& sq = objets[k].sq; const int b = sq.nom("BallAura");
                    if (b >= 0) { const float kk = (float)(1 / ou(sq.os[b].e[0], 1)); M4 S{}; S[0] = S[5] = S[10] = kk; S[15] = 1; o.racine = mulF(o.racine, S); } } }
        }
        // os panneaux : 2e calcul avec la caméra dans le repère de l'objet (anim3d.js)
        { M4 camM; if (cameraMonde(p, dans, camM)) { res.aCamM = true; res.camM = camM; }
          if (res.aCamM) for (size_t k = 0; k < objets.size(); k++) { ObjetA& ob = objets[k]; if (!ob.sq.panneaux) continue;
              ObjRes& o = res.objets[k]; const M4 c = mulF(inverseA(o.racine), camM);
              ob.sq.poser(ob.pCl, ob.pT, ob.pVis, &c); o.monde = ob.sq.monde; o.cache = ob.sq.cache; o.local = ob.sq.local; } }
        if (p) { const Clip* cl = clip_de(camera, p->nom);
            if (cl) { std::map<int, double> ch; for (auto& c : cl->cibles) for (auto& k : c.canaux) ch[k.type] = echantillon(k, cl->debut + dans).v[0];
                if (ch.count(22) && ch.count(26)) { res.aCamera = true;
                    res.oeil[0] = ch[22]; res.oeil[1] = ch[23]; res.oeil[2] = ch[24]; res.cible[0] = ch[26]; res.cible[1] = ch[27]; res.cible[2] = ch[28];
                    res.roulis = -ou(ch.count(30) ? ch[30] : NAN, 0); /* sens opposé (LU 0x1404c7420) */ res.champ = ou(ch.count(31) ? ch[31] : NAN, 3.141592653589793 / 4); } } }
        res.decorFaux = false;
        for (auto& x : decor) { if (x.image > f) break; res.decorFaux = x.faux; }
    }
};

// ====================================================================== particules.js
static const double PI_F = F(3.141592653589793), DEUXPI = F(6.2831854820251465), INV2PI = F(0.15915493667125702);
struct MT19937 {
    uint32_t mt[624]; int i = 625;
    explicit MT19937(uint32_t g = 0x1234567) { semer(g); }
    void semer(uint32_t s) { mt[0] = s; for (int k = 1; k < 624; k++) { uint32_t p = mt[k - 1] ^ (mt[k - 1] >> 30); mt[k] = 1812433253u * p + (uint32_t)k; } i = 624; }
    uint32_t u32() {
        if (i >= 624) { for (int k = 0; k < 624; k++) { uint32_t y = (mt[k] & 0x80000000u) | (mt[(k + 1) % 624] & 0x7fffffffu);
            mt[k] = mt[(k + 397) % 624] ^ (y >> 1) ^ ((y & 1) ? 0x9908b0dfu : 0); } i = 0; }
        uint32_t y = mt[i++]; y ^= y >> 11; y ^= (y << 7) & 0x9d2c5680u; y ^= (y << 15) & 0xefc60000u; y ^= y >> 18; return y;
    }
    double f() { return F((double)u32() * 2.3283064365386963e-10); }
    double n(double mx) { return (mx != 0 && mx == mx) ? fmod((double)u32(), mx) : 0; }
};
struct Courbe { bool present = false; std::vector<double> t; int dim = 0; std::vector<double> v; };
static void lire_courbe(const JV& j, Courbe& c) {
    c.present = j.vrai(); if (!c.present) return;
    for (auto& x : j["t"].a) c.t.push_back(x.num());
    const JV& V = j["v"]; c.dim = (V.taille() && V[0].t == JV::ARR) ? (int)V[0].taille() : 0;
    for (auto& x : V.a) { if (c.dim) for (int d = 0; d < c.dim; d++) c.v.push_back(x[d].num()); else c.v.push_back(x.num()); }
}
struct V4 { double v[4] = {0, 0, 0, 0}; int n = 0; double operator[](int i) const { return v[i]; } };
static V4 v4(std::initializer_list<double> l) { V4 r; for (double x : l) r.v[r.n++] = x; return r; }
static int courbe_k(const Courbe& c, double t) { const size_t n = c.t.size(); size_t k = 0; while (k < n && !(t < c.t[k])) k++; return (int)k; }
static double courbe1(const Courbe& c, double t, double dft) {           // courbe(c, t, nombre)
    if (!c.present || c.t.empty()) return dft;
    const int n = (int)c.t.size(), k = courbe_k(c, t);
    if (k == 0) return c.v[0];
    if (k >= n) return c.v[n - 1];
    const double a = c.t[k - 1], d = F(c.t[k] - a), u = d <= 0 ? 0 : F(F(t - a) / d);
    return F(F(F(c.v[k] - c.v[k - 1]) * u) + c.v[k - 1]);
}
static V4 courbeN(const Courbe& c, double t, V4 dft) {                     // courbe(c, t, [..])
    if (!c.present || c.t.empty()) return dft;
    const int n = (int)c.t.size(), k = courbe_k(c, t), D = std::max(1, c.dim); V4 r; r.n = D;
    if (k == 0) { for (int j = 0; j < D; j++) r.v[j] = c.v[j]; return r; }
    if (k >= n) { for (int j = 0; j < D; j++) r.v[j] = c.v[(n - 1) * D + j]; return r; }
    const double a = c.t[k - 1], d = F(c.t[k] - a), u = d <= 0 ? 0 : F(F(t - a) / d);
    for (int j = 0; j < D; j++) { const double p = c.v[(k - 1) * D + j], x = c.v[k * D + j]; r.v[j] = F(F(F(x - p) * u) + p); }
    return r;
}
typedef std::array<double, 4> Q4;
typedef std::array<double, 3> D3;
static Q4 qmul(const Q4& a, const Q4& b) {
    return {F(a[3] * b[0] + a[0] * b[3] + a[1] * b[2] - a[2] * b[1]), F(a[3] * b[1] - a[0] * b[2] + a[1] * b[3] + a[2] * b[0]),
            F(a[3] * b[2] + a[0] * b[1] - a[1] * b[0] + a[2] * b[3]), F(a[3] * b[3] - a[0] * b[0] - a[1] * b[1] - a[2] * b[2])};
}
static Q4 qaxe(int i, double a) { Q4 q = {0, 0, 0, F(cos(a / 2))}; q[i] = F(sin(a / 2)); return q; }
static Q4 quatAngles(double x, double y, double z) { return qmul(qmul(qaxe(0, x), qaxe(1, y)), qaxe(2, z)); }
typedef std::array<std::array<double, 3>, 3> M3;
static M3 quatMat(const Q4& q) {
    const double x = q[0], y = q[1], z = q[2], w = q[3], s = 2 / ou(x * x + y * y + z * z + w * w, 1);
    return {{{1 - s * (y * y + z * z), s * (x * y - w * z), s * (x * z + w * y)}, {s * (x * y + w * z), 1 - s * (x * x + z * z), s * (y * z - w * x)},
             {s * (x * z - w * y), s * (y * z + w * x), 1 - s * (x * x + y * y)}}};
}
static Q4 matQuat(const M3& m) {
    const double t = m[0][0] + m[1][1] + m[2][2]; double x, y, z, w;
    if (t > 0) { const double s = sqrt(t + 1) * 2; w = s / 4; x = (m[2][1] - m[1][2]) / s; y = (m[0][2] - m[2][0]) / s; z = (m[1][0] - m[0][1]) / s; }
    else if (m[0][0] > m[1][1] && m[0][0] > m[2][2]) { const double s = sqrt(1 + m[0][0] - m[1][1] - m[2][2]) * 2; w = (m[2][1] - m[1][2]) / s; x = s / 4; y = (m[0][1] + m[1][0]) / s; z = (m[0][2] + m[2][0]) / s; }
    else if (m[1][1] > m[2][2]) { const double s = sqrt(1 + m[1][1] - m[0][0] - m[2][2]) * 2; w = (m[0][2] - m[2][0]) / s; x = (m[0][1] + m[1][0]) / s; y = s / 4; z = (m[1][2] + m[2][1]) / s; }
    else { const double s = sqrt(1 + m[2][2] - m[0][0] - m[1][1]) * 2; w = (m[1][0] - m[0][1]) / s; x = (m[0][2] + m[2][0]) / s; y = (m[1][2] + m[2][1]) / s; z = s / 4; }
    return {F(x), F(y), F(z), F(w)};
}
static D3 rx(double a, const D3& v) { const double c = cos(a), s = sin(a); return {v[0], c * v[1] - s * v[2], s * v[1] + c * v[2]}; }
static D3 ry(double a, const D3& v) { const double c = cos(a), s = sin(a); return {c * v[0] + s * v[2], v[1], -s * v[0] + c * v[2]}; }
static D3 rz(double a, const D3& v) { const double c = cos(a), s = sin(a); return {c * v[0] - s * v[1], s * v[0] + c * v[1], v[2]}; }
static D3 mapF(const D3& v) { return {F(v[0]), F(v[1]), F(v[2])}; }
static D3 dirHasard(MT19937& R) { const double a = F(F(R.f() * DEUXPI) - PI_F), b = F(F(R.f() * DEUXPI) - PI_F), c = F(F(R.f() * DEUXPI) - PI_F);
    return mapF(rz(c, ry(b, rx(a, {0, 1, 0})))); }
static double ramener(double a) { const double s = a < 0 ? -PI_F : PI_F, b = F(a + s); return F(b - F(F(trunc(F(b * INV2PI)) * DEUXPI) + s)); }
typedef std::array<std::array<double, 4>, 3> M34;
static D3 app(const M34& M, const D3& v, double w) { D3 r; for (int i = 0; i < 3; i++) r[i] = F(M[i][0] * v[0] + M[i][1] * v[1] + M[i][2] * v[2] + M[i][3] * w); return r; }
static D3 nrm(const D3& v) { const double l = hyp3(v[0], v[1], v[2]); return l > 0 ? D3{F(v[0] / l), F(v[1] / l), F(v[2] / l)} : v; }
static D3 nrmJ(const D3& v) { const double s = F(F(F(v[0] * v[0]) + F(v[1] * v[1])) + F(v[2] * v[2]));
    if (!(s > 0) || !std::isfinite(s)) return {0, 0, 0}; const double l = F(sqrt(s)); return {F(v[0] / l), F(v[1] / l), F(v[2] / l)}; }
static D3 sous(const D3& a, const D3& b) { return {F(a[0] - b[0]), F(a[1] - b[1]), F(a[2] - b[2])}; }
static D3 croixJ(const D3& a, const D3& b) { return {F(F(a[1] * b[2]) - F(a[2] * b[1])), F(F(a[2] * b[0]) - F(a[0] * b[2])), F(F(a[0] * b[1]) - F(a[1] * b[0]))}; }
static D3 tangenteInt(const D3& prec, const D3& cur, const D3& suiv) {
    const D3 a = nrmJ(sous(prec, cur)), b = nrmJ(sous(suiv, cur)), s = {F(a[0] + b[0]), F(a[1] + b[1]), F(a[2] + b[2])};
    const double l = F(sqrt(F(F(F(s[0] * s[0]) + F(s[1] * s[1])) + F(s[2] * s[2]))));
    if (l != 0 && F(0.001) < l) { const double inv = F(1 / l); const D3 bi = {F(inv * s[0]), F(inv * s[1]), F(inv * s[2])}, c = nrmJ(croixJ(a, b)); return croixJ(c, bi); }
    return b;
}
static void tangentes(float* H, const std::vector<D3>& P, int N) {
    std::vector<D3> T;
    for (int i = 0; i < N; i++) T.push_back(i == 0 ? nrmJ(sous(P[1], P[0])) : i == N - 1 ? nrmJ(sous(P[i], P[i - 1])) : tangenteInt(P[i - 1], P[i], P[i + 1]));
    for (int k = 0; k < 3; k++) T[0][k] = F(F(F(T[0][k] * 3) - T[1][k]) * F(0.5));
    for (int k = 0; k < 3; k++) T[N - 1][k] = F(F(F(T[N - 1][k] * 3) - T[N - 2][k]) * F(0.5));
    for (int i = 0; i < N; i++) for (int k = 0; k < 3; k++) H[100 + 4 * i + k] = (float)T[i][k];
}
static D3 hermite(const float* H, const std::vector<D3>& P, int s, int n, double reste, double t) {
    double cum = 0, f = 0, fp = 0; int u = 0; const double inv = F(1 / reste);
    for (int k = 0; k < n; k++) { fp = f; cum = F(cum + H[132 + s + k]); f = F(inv * cum); if (t <= f) { u = k; break; } }
    if (!(u < n - 1 && F(f - fp) > 0)) return {0, 0, 0};
    const double v = F(F(t - fp) / F(f - fp)), v2 = F(v * v), v3 = F(v * v2), L = H[132 + s + u]; const int i0 = s + u, i1 = i0 + 1;
    D3 r;
    for (int k = 0; k < 3; k++) { const double p0 = P[i0][k], p1 = P[i1][k], a = F(H[100 + 4 * i0 + k] * L), b = F(H[100 + 4 * i1 + k] * L);
        const double c2 = F(F(F(F(F(-3 * p0) - F(a + a)) + F(3 * p1)) - b)), c3 = F(F(F(F(2 * p0) + a) - F(2 * p1)) + b);
        r[k] = F(F(F(F(c2 * v2) + F(c3 * v3)) + F(v * a)) + p0); }
    return r;
}
static Q4 versDirection(const D3& v) {
    const double ax[3] = {v[2], 0, -v[0]}, l = hyp3(ax[0], ax[1], ax[2]);
    if (l <= 0) return v[1] >= 0 ? Q4{0, 0, 0, 1} : Q4{1, 0, 0, 0};
    const double a = acos(std::max(-1.0, std::min(1.0, v[1]))), s = sin(a / 2) / l;
    return {F(ax[0] * s), F(ax[1] * s), F(ax[2] * s), F(cos(a / 2))};
}
struct DefEm {
    double Emode, Emax, Efin, Eduree, Edebit, Eretard, Elocal; bool Eboucle, Efiger, EsansEchelle; Courbe Ecourbe;
    double vieMin, vieMax, vieK; bool vieHasard;
    double Ftype, Frayon, Fangle; bool FdirHasard, Fcoque;
    double vMin, vMax; bool vHasard; Courbe vCourbe;
    bool cHasardA, cHasardC; Courbe cRgb, cRgb2, cAlpha, cAlpha2;
    double tMin[3], tMax[3], tParAxe; bool tHasard, tUnTirage, tDeux; Courbe tCourbe, tCourbe2;
    double wForce, wDir[3], wMin, wMax; bool wActif, wHasard; Courbe wCourbe;
    double ra0[3], ra1[3], rv0[3], rv1[3]; bool rHasardA, rHasardV, rSigne, rSuitEmetteur;
    bool mSuitVitesse; double mM0, mLarg, mHaut, mType, mOrdre;
    struct UV { double rep[2], facteur, dec[2], col, lig, mode, invVit; bool depHasard; Courbe defil; }; std::vector<UV> uv;
    double gravite, melange; std::vector<std::string> mDebut; std::vector<std::pair<std::string, double>> mFin; std::string noeud; bool uvMode3 = false;
    void lire(const JV& d) {
        const JV& E = d["emetteur"]; Emode = E["mode"].num(); Emax = E["max"].num(); Efin = E["fin"].num(); Eduree = E["duree"].num(); Edebit = E["debit"].num();
        Eretard = E["retard"].num(); Elocal = E["local"].num(); Eboucle = E["boucle"].vrai(); Efiger = E["figer"].vrai(); EsansEchelle = E["sansEchelle"].vrai(); lire_courbe(E["courbe"], Ecourbe);
        const JV& V = d["vie"]; vieMin = V["min"].num(); vieMax = V["max"].num(); vieK = V["k"].num(); vieHasard = V["hasard"].vrai();
        const JV& S = d["forme"]; Ftype = S["type"].num(); Frayon = S["rayon"].num(); Fangle = S["angle"].num(); FdirHasard = S["dirHasard"].vrai(); Fcoque = S["coque"].vrai();
        const JV& Vi = d["vitesse"]; vMin = Vi["min"].num(); vMax = Vi["max"].num(); vHasard = Vi["hasard"].vrai(); lire_courbe(Vi["courbe"], vCourbe);
        const JV& C = d["couleur"]; cHasardA = C["hasardA"].vrai(); cHasardC = C["hasardC"].vrai(); lire_courbe(C["rgb"], cRgb); lire_courbe(C["rgb2"], cRgb2); lire_courbe(C["alpha"], cAlpha); lire_courbe(C["alpha2"], cAlpha2);
        const JV& T = d["taille"]; for (int k = 0; k < 3; k++) { tMin[k] = T["min"][k].num(); tMax[k] = T["max"][k].num(); }
        tParAxe = T["parAxe"].num(); tHasard = T["hasard"].vrai(); tUnTirage = T["unTirage"].vrai(); tDeux = T["deux"].vrai(); lire_courbe(T["courbe"], tCourbe); lire_courbe(T["courbe2"], tCourbe2);
        const JV& W = d["vent"]; wForce = W["force"].num(); for (int k = 0; k < 3; k++) wDir[k] = W["dir"][k].num(); wMin = W["min"].num(); wMax = W["max"].num();
        wActif = W["actif"].vrai(); wHasard = W["hasard"].vrai(); lire_courbe(W["courbe"], wCourbe);
        const JV& R = d["rotation"]; for (int k = 0; k < 3; k++) { ra0[k] = R["a0"][k].num(); ra1[k] = R["a1"][k].num(); rv0[k] = R["v0"][k].num(); rv1[k] = R["v1"][k].num(); }
        rHasardA = R["hasardA"].vrai(); rHasardV = R["hasardV"].vrai(); rSigne = R["signe"].vrai(); rSuitEmetteur = R["suitEmetteur"].vrai();
        const JV& M = d["modele"]; mSuitVitesse = M["suitVitesse"].vrai(); mM0 = M["m0"].num(); mLarg = M["larg"].num(); mHaut = M["haut"].num(); mType = M["type"].num(); mOrdre = M["ordre"].num();
        for (auto& u : d["uv"].a) { UV x; for (int k = 0; k < 2; k++) { x.rep[k] = u["rep"][k].num(); x.dec[k] = u["dec"][k].num(); }
            x.facteur = u["facteur"].num(); x.col = u["col"].num(); x.lig = u["lig"].num(); x.mode = u["mode"].num(); x.invVit = u["invVit"].num(); x.depHasard = u["depHasard"].vrai();
            lire_courbe(u["defil"], x.defil); if (x.mode == 3) uvMode3 = true; uv.push_back(x); }
        gravite = d["force"]["gravite"].num(); melange = d["materiau"]["melange"].num();
        for (auto& x : d["motion"]["debut"].a) mDebut.push_back(x.s);
        for (auto& x : d["motion"]["fin"].a) mFin.push_back({x[0].s, x[1].num()});
        noeud = d["noeud"].s;
    }
};
struct Part {
    Q4 q = {0, 0, 0, 1}; D3 w = {0, 0, 0}; double uv[3][4] = {}; double col[4] = {1, 1, 1, 1}; D3 pos = {0, 0, 0}, monde = {0, 0, 0}, vit = {0, 0, 0};
    D3 t0 = {1, 1, 1}, taille = {0, 0, 0}, tirT = {0, 0, 0}; double vitesse = 0, vyG = 0, tirC = 0, tirA = 0, vent = 0, ventK = 1, p104 = 0;
    double img0[3] = {0, 0, 0}, compteur = 0, age = 0, vie = 0;
};
// (14/11/2026) TEINTE choisie dans l'Atelier pour les couleurs de sommets / de particules : opération « set » de VRFW
// ([[recolor]] hue + colorize, saturation = valeur = 1) : teinte remplacée par H (degrés), saturation au moins C, valeur gardée.
// Même formule dans app.js / particules.js (teinterHSV) et AtelierD3D/rendu_image.py (teinter_hsv). APPROCHÉ : formule de VRFW non lue.
// (23/11) S = `saturation` de VRFW : multiplicateur après colorize (émulé, nie_outils/emu_vrfw.py) ; 1 = gardée
static inline void teinter_hsv(double* c, double H, double C, double S = 1.0, double Vl = 1.0) {   // (23/11) Vl = `value` de VRFW (luminosité ×, gris compris)
    const double v0 = std::max(c[0], std::max(c[1], c[2])), mn = std::min(c[0], std::min(c[1], c[2]));
    if (!(v0 > 0)) return;
    const double v = v0 * Vl;
    // (15/11/2026) LU dans VRFW (FUN_1827bccd0, émulée : nie_outils/emu_vrfw.py) : seuil des gris 0,08 ; colorize pour eux seuls
    double s = (v0 - mn) / v0;
    if (s < 0.08) { if (!(C > 0)) { for (int k = 0; k < 3; k++) c[k] *= Vl; return; } s = std::max(s, C); }
    s = std::min(1.0, s * S);
    double h = fmod(H, 360.0); if (h < 0) h += 360; h /= 60; const int i = (int)floor(h) % 6; const double f = h - floor(h);
    const double p = v * (1 - s), q = v * (1 - s * f), t = v * (1 - s * (1 - f));
    switch (i) { case 0: c[0] = v; c[1] = t; c[2] = p; break; case 1: c[0] = q; c[1] = v; c[2] = p; break; case 2: c[0] = p; c[1] = v; c[2] = t; break;
                 case 3: c[0] = p; c[1] = q; c[2] = v; break; case 4: c[0] = t; c[1] = p; c[2] = v; break; default: c[0] = v; c[1] = p; c[2] = q; }
}
struct Quads { std::vector<float> pos, col, uv[3], nor, tan; int n = 0; };
struct Emetteur {
    const DefEm* d = nullptr; MT19937 R; double max = 0;
    double t = 0; std::vector<Part> parts; bool fini = false, boucle = false, premier = false; bool aArret = false; double arret = 0; double acc = 0;
    float H[148]; int hN = 0, hDep = 0, hImg = 0, hImgL = 0; bool hDrap = false;
    bool aTeinte = false; double tH = 0, tC = 0, tS = 1, tV = 1;   // (14/11/2026) teinte de l'Atelier (options.json « particules ») ; 23/11 + saturation, luminosité
    void init(const DefEm* def, uint32_t graine) { d = def; R = MT19937(graine); max = maximum(); reset(); }
    double maximum() const { const DefEm& D = *d;
        if (D.Emode != 0) return D.Emax;
        double T = D.Eboucle ? std::max(D.vieMax, D.vieMin) : F(D.Efin + D.Eduree);
        if (D.vieK >= 1) T = F(T * D.vieK);
        return std::min(D.Emax, trunc(F(T * D.Edebit)) + 1); }
    void reset() { t = 0; parts.clear(); fini = false; boucle = false; premier = false; aArret = false;
        const double c0 = F(courbe1(d->Ecourbe, 0, 1) * d->Edebit); acc = c0 > 0 ? F(1 / c0) : 0;
        memset(H, 0, sizeof H); hN = 0; hDep = 0; hImg = 0; hImgL = 0; hDrap = false; }
    void hEcrire(int i, const M34& M) { const int b = 4 + 12 * i; for (int r = 0; r < 3; r++) for (int c = 0; c < 4; c++) H[b + 4 * r + c] = (float)M[r][c]; }
    D3 hPoint(int i) const { return {(double)H[7 + 12 * i], (double)H[11 + 12 * i], (double)H[15 + 12 * i]}; }
    void trajetMaj(const M34& M) { const int n = hN;
        if (n > 0) {
            const double dx = F(H[12 * n + 7] - M[0][3]), dy = F(H[12 * n + 11] - M[1][3]), dz = F(H[12 * n + 15] - M[2][3]);
            if (!(F(F(F(dx * dx) + F(dy * dy)) + F(dz * dz)) > 0)) return;
            if (n >= 8) { for (int b = 0; b < 7; b++) if (b != 0 || hDep != 0) memmove(&H[4 + 12 * b], &H[16 + 12 * b], 12 * sizeof(float));
                hEcrire(7, M); if (hDep != 0) hDep--; }
            else { hEcrire(n, M); hN++; }
        } else { hEcrire(0, M); hN = 1; }
        if (!hDrap) { hDep = 0; hDrap = true; }
        hImg++; }
    double corde() { const int n = hN; if (n < 2) return 0;
        if (hImgL == hImg) return H[143];
        const D3 a = hPoint(hDep), b = hPoint(n - 1); const double dd[3] = {F(b[0] - a[0]), F(b[1] - a[1]), F(b[2] - a[2])};
        hImgL = hImg; H[143] = (float)F(sqrt(F(F(F(dd[0] * dd[0]) + F(dd[1] * dd[1])) + F(dd[2] * dd[2])))); return H[143]; }
    void naitreTrajet(int n, const M34& M, const Q4& q, double vE, double mult) { const double L = corde(); const int N = hN;
        if (!(L > 0)) return;
        if (N > 1) { H[140] = 0;
            for (int i = 0; i < N - 1; i++) { const D3 a = hPoint(i), b = hPoint(i + 1); const double dd[3] = {F(b[0] - a[0]), F(b[1] - a[1]), F(b[2] - a[2])};
                H[132 + i] = (float)F(sqrt(F(F(F(dd[0] * dd[0]) + F(dd[1] * dd[1])) + F(dd[2] * dd[2])))); H[140] = (float)F((double)H[132 + i] + H[140]); } }
        std::vector<D3> P; for (int i = 0; i < 8; i++) P.push_back(hPoint(i));
        if (N > 2) tangentes(H, P, N);
        const int s = hDep, b0 = 4 + 12 * s; const double den = F(F(F(mult * d->Edebit)) * L); M34 Mi{};
        for (int k = 0; k < n; k++) {
            const double tt = F((k + 1) / den);
            for (int r = 0; r < 3; r++) for (int c = 0; c < 4; c++) Mi[r][c] = F(F(tt * F(M[r][c] - H[b0 + 4 * r + c])) + H[b0 + 4 * r + c]);
            D3 p = {0, 0, 0};
            if (N != 0 && H[140] > 0 && 8 - s >= 2) { double somme = 0; for (int i = 0; i < s; i++) somme = F(somme + H[132 + i]);
                p = hermite(H, P, s, 8 - s, F(H[140] - somme), tt); }
            Mi[0][3] = p[0]; Mi[1][3] = p[1]; Mi[2][3] = p[2];
            parts.push_back(naissance(Mi, &q, vE, 0)); }
        if (N != 0) { hDep = N - 1; hEcrire(N - 1, Mi); hImg++; } }
    double fin() const { return F(F(d->Efin + d->Eretard) + d->Eduree); }
    void arreter(double delai) { if (!aArret) { aArret = true; arret = delai; } }
    void pas(double dt, const M34& M, const Q4& q, const D3& ech, bool actif, double vE) {
        dt = F(dt); const DefEm& E = *d;
        if (fini || !(dt > 0)) return;
        if (aArret) { arret = F(arret - dt); if (arret <= 0 && t < fin()) t = fin(); }
        const double fn = fin();
        if (fn <= t) { if (parts.empty()) { fini = true; return; } }
        else { t = F(t + dt); if (fn <= t) { if (!E.Eboucle || !actif) t = fn; else { t = F(t - E.Eduree); boucle = true; } } }
        if (!actif && E.Efiger) return;
        const bool pret = E.Eretard <= t;
        bool emettre = actif && t < fn && pret;
        if (!premier && actif && pret) { emettre = true; premier = true; }
        const double mult = fn > 0 ? F(courbe1(E.Ecourbe, F(t / fn), 1) * vE) : 1;
        const D3 echelle = E.EsansEchelle ? D3{1, 1, 1} : ech;
        if (E.Emode == 1) trajetMaj(M);
        if (emettre) { double n = nombre(dt, mult); n = std::min(n, max - (double)parts.size());
            if (E.Emode == 1) { if (n > 0) naitreTrajet((int)n, M, q, vE, mult); }
            else for (int k = 0; k < n; k++) parts.push_back(naissance(M, &q, vE, 0)); }
        bool aVent = false; D3 vent{};
        if (E.wForce > 0) { aVent = true; const double* dd = E.wDir;
            for (int i = 0; i < 3; i++) vent[i] = F(E.wForce * F(F(F(F(M[i][0] * dd[0]) + F(M[i][1] * dd[1])) + F(M[i][2] * dd[2])) + M[i][3])); }
        for (auto& p : parts) maj(p, dt, M, echelle, aVent ? &vent : nullptr);
        std::vector<Part> garde; garde.reserve(parts.size()); for (auto& p : parts) if (p.age < p.vie) garde.push_back(p); parts.swap(garde);
    }
    double nombre(double dt, double mult) { const DefEm& E = *d; const double r = F(E.Edebit * mult);
        if (!(E.Edebit > 0) || !(mult > 0)) return 0;
        if (E.Emode == 1) return trunc(F(F(corde() * E.Edebit) * mult));
        if (E.Emode != 0) return 0;
        acc = F(acc + dt); const double seuil = F(1 / r);
        if (seuil <= acc) { const double n = trunc(F(acc * r)); acc = seuil < acc ? F(fmod(acc, seuil)) : 0; return n; }
        return 0; }
    Part naissance(const M34& M, const Q4* qEm, double vE, double p6) {
        const DefEm& D = *d; Part p; const bool loc = D.Elocal != 0;
        D3 d1{}, d2{}; double cs[2] = {0, 0};
        if (D.Ftype == 0 || D.Ftype == 1) { d1 = dirHasard(R); if (D.Ftype == 1 && d1[1] < 0) d1[1] = -d1[1];
            if (D.FdirHasard) { d2 = dirHasard(R); if (D.Ftype == 1 && d2[1] < 0) d2[1] = -d2[1]; } }
        else if (D.Ftype == 2) { const double a = F(F(R.f() * DEUXPI) - PI_F); cs[0] = F(sin(a)); cs[1] = F(cos(a)); }
        double rr = 1;
        if (D.Ftype == 0 || D.Ftype == 1) { if (!D.Fcoque) rr = R.f();
            const D3& dp = D.FdirHasard ? d2 : d1; for (int k = 0; k < 3; k++) p.pos[k] = F(F(D.Frayon * dp[k]) * rr); if (!loc) p.pos = app(M, p.pos, 1); }
        else if (D.Ftype == 2) { double r = D.Frayon; if (!D.Fcoque) { rr = R.f(); r = F(r * rr); }
            p.pos = {F(r * cs[1]), 0, F(r * cs[0])}; if (!loc) p.pos = app(M, p.pos, 1); }
        else p.pos = {M[0][3], M[1][3], M[2][3]};
        if (D.Ftype == 0 || D.Ftype == 1) { if (D.FdirHasard) p.vit = d1; else p.vit = loc ? d1 : app(M, d1, 0); }
        else if (D.Ftype == 2) {
            if (!D.FdirHasard) { const double ph = F(D.Fangle * rr), sp = F(sin(ph)), cp = F(cos(ph)); p.vit = {F(sp * cs[1]), cp, F(sp * cs[0])}; }
            else { const double a = F(F(F(D.Fangle + D.Fangle) * R.f()) - D.Fangle), b = F(F(F(D.Fangle + D.Fangle) * R.f()) - D.Fangle); p.vit = mapF(rz(b, rx(a, {0, 1, 0}))); }
            if (!loc) p.vit = app(M, p.vit, 0); }
        else p.vit = {0, 1, 0};
        p.vit = nrm(p.vit);
        p.vitesse = D.vMin; if (D.vHasard) p.vitesse = F(F(F(D.vMax - D.vMin) * R.f()) + p.vitesse);
        if (!D.vCourbe.present) for (int k = 0; k < 3; k++) p.vit[k] = F(p.vit[k] * p.vitesse);
        double vie = D.vieMin; if (D.vieHasard) vie = F(F(F(D.vieMax - D.vieMin) * R.f()) + vie);
        p.vie = F(vie * vE); p.age = 0;
        if (D.cHasardA) p.tirA = R.f();
        if (D.cHasardC) p.tirC = R.f();
        for (int k = 0; k < 3; k++) p.t0[k] = D.tMin[k];
        if (D.tHasard) { if (!D.tUnTirage) for (int k = 0; k < 3; k++) p.t0[k] = F(F(F(D.tMax[k] - D.tMin[k]) * R.f()) + p.t0[k]);
            else { const double r = R.f(); for (int k = 0; k < 3; k++) p.t0[k] = F(F(r * F(D.tMax[k] - D.tMin[k])) + D.tMin[k]); } }
        if (D.tDeux) { if (!D.tUnTirage) { const double a = R.f(), b = R.f(), c = R.f(); p.tirT = {a, b, c}; } else { const double r = R.f(); p.tirT = {r, r, r}; } }
        p.p104 = p6;
        if (D.wActif || D.wForce > 0) { p.vent = D.wMin; if (D.wHasard) p.vent = F(F(R.f() * F(D.wMax - D.wMin)) + p.vent);
            if (D.wActif) p.ventK = F(F(R.f() * F(0.6)) + F(0.4)); }
        D3 a = {0, 0, 0};
        if (!D.mSuitVitesse) { a = {D.ra0[0], D.ra0[1], D.ra0[2]};
            if (D.rSuitEmetteur) { if (qEm) p.q = *qEm; else { M3 R3; for (int r = 0; r < 3; r++) for (int c = 0; c < 3; c++) R3[r][c] = M[r][c]; p.q = matQuat(R3); } } }
        else { const D3& v = p.vit; const double l = hyp3(v[0], v[1], v[2]); p.q = l > 0 ? versDirection({v[0] / l, v[1] / l, v[2] / l}) : Q4{0, 0, 0, 1}; }
        if (D.rHasardA) { const double r = R.f(); for (int k = 0; k < 3; k++) a[k] = F(F(r * F(D.ra1[k] - D.ra0[k])) + a[k]); }
        for (int k = 0; k < 3; k++) a[k] = ramener(a[k]);
        D3 w = {D.rv0[0], D.rv0[1], D.rv0[2]};
        if (D.rHasardV) { const double r = R.f(); for (int k = 0; k < 3; k++) w[k] = F(F(r * F(D.rv1[k] - D.rv0[k])) + D.rv0[k]); }
        if (D.rSigne) for (int k = 0; k < 3; k++) if ((a[k] > 0 && w[k] < 0) || (a[k] < 0 && w[k] > 0)) w[k] = -w[k];
        if (!D.mSuitVitesse && !D.rSuitEmetteur) { p.q = quatAngles(a[0], a[1], a[2]); p.w = w; }
        for (size_t i = 0; i < D.uv.size() && i <= 2; i++) { const DefEm::UV& u = D.uv[i];
            double z = u.rep[0] == 0 ? 0 : F(1 / u.rep[0]), ww = u.rep[1] == 0 ? 0 : F(1 / u.rep[1]);
            if (u.defil.present) { z = F(z / u.facteur); ww = F(ww / u.facteur); }
            p.uv[i][0] = u.dec[0]; p.uv[i][1] = u.dec[1]; p.uv[i][2] = z; p.uv[i][3] = ww;
            if (u.depHasard) { const double tot = u.col * u.lig, n = R.n(tot);
                p.img0[i] = u.mode == 1 ? F(n / tot) : u.mode == 2 ? F(n / p.vie) : u.mode == 3 ? n : 0; } }
        return p;
    }
    void maj(Part& p, double dt, const M34& M, const D3& ech, const D3* vent) {
        const DefEm& D = *d; double dtm = dt;
        p.age = F(p.age + dt); double t = F(p.age / p.vie);
        if (F(p.vie - p.age) < 0) { dtm = F(F(p.vie - p.age) + dt); p.age = p.vie; t = 1; }
        if (D.uvMode3) p.compteur = F(F(dt * 60) + p.compteur);
        if (p.vie != 0) {
            V4 c = courbeN(D.cRgb, t, v4({1, 1, 1}));
            if (D.cHasardC && D.cRgb2.present) { const V4 c2 = courbeN(D.cRgb2, t, v4({1, 1, 1})); for (int k = 0; k < c.n; k++) c.v[k] = F(F(F(c2[k] - c.v[k]) * p.tirC) + c.v[k]); }
            double al = F(1 - courbe1(D.cAlpha, t, 0));
            if (D.cHasardA && D.cAlpha2.present) al = F(F(F(F(1 - courbe1(D.cAlpha2, t, 0)) - al) * p.tirA) + al);
            p.col[0] = c[0]; p.col[1] = c[1]; p.col[2] = c[2]; p.col[3] = al;
            V4 s = courbeN(D.tCourbe, t, v4({1, 1, 1})); const double g = F(t * p.p104);
            for (int k = 0; k < s.n; k++) s.v[k] = F(F(g * s.v[k]) + s.v[k]);
            if (D.tDeux && D.tCourbe2.present) { const V4 s2 = courbeN(D.tCourbe2, t, v4({1, 1, 1})); for (int k = 0; k < s.n; k++) s.v[k] = F(F(F(s2[k] - s.v[k]) * p.tirT[k]) + s.v[k]); }
            if (D.tParAxe == 0) { s.v[1] = s.v[0]; s.v[2] = s.v[0]; }
            p.taille = {s[0], s[1], s[2]};
        }
        for (size_t i = 0; i < D.uv.size() && i <= 2; i++) { const DefEm::UV& u = D.uv[i];
            if (u.defil.present) { const V4 v = courbeN(u.defil, t, v4({0, 0})); p.uv[i][0] = F(v[0] * u.facteur); p.uv[i][1] = F(v[1] * u.facteur); }
            if (u.mode != 0 && u.mode == u.mode) { double x = u.mode == 1 ? p.age : u.mode == 2 ? t : u.mode == 3 ? p.compteur : 0;
                if (u.depHasard) x = F(x + p.img0[i]);
                const double tot = u.col * u.lig; double n;
                if (u.mode == 1 || u.mode == 2) n = trunc(F(F(F(fmod(x, u.invVit)) / u.invVit) * tot));
                else if (u.mode == 3) n = fmod(trunc(x), tot);
                else { p.uv[i][0] = 0; p.uv[i][1] = 0; p.uv[i][2] = 1; p.uv[i][3] = 1; continue; }
                const double c1 = F(1 / u.col), l1 = F(1 / u.lig);
                p.uv[i][0] = F(fmod(n, u.col) * c1); p.uv[i][1] = F(F(floor(n / u.col) + 1) * l1); p.uv[i][2] = c1; p.uv[i][3] = l1; } }
        const double g = D.gravite; const D3 ancien = p.pos;
        if (!D.vCourbe.present) { if (g != 0) p.vit[1] = F(p.vit[1] - F(g * dtm)); for (int k = 0; k < 3; k++) p.pos[k] = F(F(F(p.vit[k] * ech[k]) * dtm) + p.pos[k]); }
        else if (g != 0) { const double cv = F(courbe1(D.vCourbe, t, 1) * p.vitesse); D3 v4_ = {F(cv * p.vit[0]), F(cv * p.vit[1]), F(cv * p.vit[2])};
            p.vyG = F(p.vyG - F(dtm * g));
            for (int k = 0; k < 3; k++) p.pos[k] = F(F(F(v4_[k] * ech[k]) * dtm) + p.pos[k]);
            p.pos[1] = F(F(F(p.vyG * ech[1]) * dtm) + p.pos[1]);
            p.vit = v4_; const double l = hyp3(v4_[0], v4_[1], v4_[2]); if (l > 0) for (int k = 0; k < 3; k++) p.vit[k] = F(v4_[k] / F(l)); }
        else { const double cv = F(F(courbe1(D.vCourbe, t, 1) * p.vitesse) * dtm); for (int k = 0; k < 3; k++) p.pos[k] = F(F(cv * F(p.vit[k] * ech[k])) + p.pos[k]); }
        { double s = p.vent;
            if (s > 0 && (D.wActif || D.wForce > 0) && D.Elocal == 0) {
                if (D.wCourbe.present) s = F(courbe1(D.wCourbe, t, 1) * s);
                if (s > 0 && vent) { const double k = F(1 / s); for (int i = 0; i < 3; i++) p.pos[i] = F(F(F(k * (*vent)[i]) * dtm) + p.pos[i]); } } }
        p.monde = D.Elocal != 0 ? app(M, p.pos, 1) : p.pos;
        if (D.mSuitVitesse) { const D3 pa = D.Elocal != 0 ? app(M, ancien, 1) : ancien; const double dv[3] = {p.monde[0] - pa[0], p.monde[1] - pa[1], p.monde[2] - pa[2]};
            const double l = hyp3(dv[0], dv[1], dv[2]); if (l > 0) p.q = versDirection({dv[0] / l, dv[1] / l, dv[2] / l}); }
        else if (p.w[0] != 0 || p.w[1] != 0 || p.w[2] != 0) p.q = qmul(p.q, quatAngles(F(p.w[0] * dtm), F(p.w[1] * dtm), F(p.w[2] * dtm)));
    }
    void quads(const M3& camRot, const double* camPos, const double* echObj, double opacite, Quads& Q) const {
        const DefEm& D = *d; const size_t n = parts.size();
        Q.pos.assign(n * 12, 0); Q.col.assign(n * 16, 0); for (auto& u : Q.uv) u.assign(n * 8, 0); Q.nor.assign(n * 12, 0); Q.tan.assign(n * 12, 0);
        const double L = D.mM0 == 0 ? D.mLarg : 1, Hh = D.mM0 == 0 ? D.mHaut : 1;
        static const double COINS[4][2] = {{-0.5, 0.5}, {-0.5, -0.5}, {0.5, 0.5}, {0.5, -0.5}}, TUV[4][2] = {{0, 1}, {0, 0}, {1, 1}, {1, 0}};
        int m = 0;
        const bool ordre = D.melange == 3 || D.melange == 4 || D.mOrdre == 1;
        for (size_t ii = 0; ii < n; ii++) { const Part& p = parts[ordre ? ii : n - 1 - ii];
            double s[3]; for (int k = 0; k < 3; k++) s[k] = D.EsansEchelle ? F(p.t0[k] * p.taille[k]) : F(F(p.t0[k] * p.taille[k]) * (echObj ? echObj[k] : 1));
            const M3 Rq = quatMat(p.q); double X[3], Y[3], Z[3];
            if (D.mType == 1) { double Am[3][3]; for (int i = 0; i < 3; i++) for (int j = 0; j < 3; j++) Am[i][j] = camRot[i][0] * Rq[0][j] + camRot[i][1] * Rq[1][j] + camRot[i][2] * Rq[2][j];
                for (int i = 0; i < 3; i++) { X[i] = Am[i][0]; Y[i] = Am[i][1]; Z[i] = Am[i][2]; } }
            else if (D.mType == 2) { const double y[3] = {Rq[0][1], Rq[1][1], Rq[2][1]}, vc[3] = {camPos[0] - p.monde[0], camPos[1] - p.monde[1], camPos[2] - p.monde[2]};
                const double x[3] = {y[1] * vc[2] - y[2] * vc[1], y[2] * vc[0] - y[0] * vc[2], y[0] * vc[1] - y[1] * vc[0]}, lx = hyp3(x[0], x[1], x[2]);
                if (lx > 0) { for (int k = 0; k < 3; k++) { X[k] = x[k] / lx; Y[k] = y[k]; }
                    Z[0] = X[1] * Y[2] - X[2] * Y[1]; Z[1] = X[2] * Y[0] - X[0] * Y[2]; Z[2] = X[0] * Y[1] - X[1] * Y[0]; }
                else { X[0] = 1; X[1] = 0; X[2] = 0; Y[0] = 0; Y[1] = 1; Y[2] = 0; Z[0] = 0; Z[1] = 0; Z[2] = 1; } }
            else for (int i = 0; i < 3; i++) { X[i] = Rq[i][0]; Y[i] = Rq[i][1]; Z[i] = Rq[i][2]; }
            const double sx = L * s[0], sy = Hh * s[1];
            double c[4] = {p.col[0], p.col[1], p.col[2], p.col[3] * opacite};
            if (aTeinte) teinter_hsv(c, tH, tC, tS, tV);
            for (int j = 0; j < 4; j++) { const double cx = COINS[j][0], cy = COINS[j][1]; const int o = 4 * m + j;
                for (int k = 0; k < 3; k++) Q.pos[3 * o + k] = (float)(p.monde[k] + X[k] * cx * sx + Y[k] * cy * sy);
                for (int k = 0; k < 3; k++) { Q.nor[3 * o + k] = (float)Z[k]; Q.tan[3 * o + k] = (float)X[k]; }
                for (int k = 0; k < 4; k++) Q.col[4 * o + k] = (float)c[k];
                for (int i = 0; i < 3; i++) { double u[4] = {0, 0, 1, 1}; if (i < (int)D.uv.size()) memcpy(u, p.uv[i], sizeof u);
                    Q.uv[i][2 * o] = (float)(TUV[j][0] * u[2] + u[0]); Q.uv[i][2 * o + 1] = (float)(1 - TUV[j][1] * u[3] + u[1]); } }
            m++; }
        Q.n = m;
    }
};
