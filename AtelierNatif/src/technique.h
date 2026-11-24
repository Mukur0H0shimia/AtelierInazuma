// UNE IMAGE DE LA TECHNIQUE (14/11/2026) : ce que web/vue3d.js (_animer, _boucle, _carteOmbre) et web/app.js (rendreD3D
// pour le lecteur natif) calculaient pour chaque image, refait ici dans le même ordre -> structure Image du lecteur.
#pragma once

static void lignes_vers_d(const M4& m, double* o) { for (int i = 0; i < 16; i++) o[i] = m[i]; }
static std::vector<std::vector<double>> lire_vv(const JV& j) { std::vector<std::vector<double>> r; for (auto& x : j.a) { std::vector<double> v; for (auto& y : x.a) v.push_back(y.num()); r.push_back(v); } return r; }

struct PieceT {
    std::string cle, acteur; uint32_t elem = 0; bool opaque = false, ztest = true, zecrit = false, surEcran = false, cachee = false;
    int panneau = 0;     // (14/11/2026) octet +0x0D de la fiche de matériau G4MD : pièce tournée vers la caméra au dessin (LU)
    std::vector<std::vector<double>> params, texproj; std::vector<uint32_t> uvCrcs; double diffuse[4] = {1, 1, 1, 1}, ambient[4] = {0, 0, 0, 1}, alphaRepos = 1;
    bool aColonne = false; double colonne = 0;
    bool aAnim = false; int obj = -1, os = -1; uint32_t mat = 0; bool aPeau = false; std::vector<int> peau;
    // état (comme les champs de la pièce dans la vue)
    bool aModele = false; M4 modele; bool aOpacite = false; double opacite = 0; bool aJeuP = false; std::vector<std::vector<double>> jeuP;
    bool aJeuUV = false; double jeuUV[6][8]; bool ecran2D = false, animCachee = false; bool aPeauK = false; std::vector<M4> peauK;
    std::vector<std::array<double, 3>> jeuCol;          // couleurs animées (G4MA 16-19) : [n°, composante, valeur]
    bool aCoul = false; double coul[3] = {1, 1, 1};     // (14/11/2026) couleur de matériau choisie dans l'Atelier (options.json)
    bool aTeinteS = false; double tH = 0, tC = 0, tS = 1, tV = 1; // (14/11/2026) teinte des couleurs de sommets (options.json « sommets »)
};
struct EmetT {
    std::string cle, acteur; uint32_t elem = 0; int obj = -1; bool opaque = false, ztest = false, surEcran = false, monde = false, grd = false, cachee = false;
    std::vector<std::vector<double>> params; DefEm def; Emetteur ptl;
    bool aTeinte = false; double tH = 0, tC = 0, tS = 1, tV = 1;  // (14/11/2026) teinte des particules de l'objet (options.json « particules »)
    int ptlF = -1; bool aPtlClip = false; std::string ptlClip; bool ptlDemarre = false, ptlVisible = false, aN = false; double e[3] = {1, 1, 1}; bool animCachee = true;
};
struct RefL { uint32_t nameCrc, boneNameCrc; int setType, boneSpace, boneRefType; };
struct LumL { uint32_t pos, col; double type; };
struct ShL { uint32_t mat; int idx; uint32_t ref; int type; };
struct LumDefT { std::string acteur; int obj = -1; std::unordered_map<uint32_t, std::vector<double>> params; std::vector<RefL> refs; std::vector<LumL> lumieres; std::vector<ShL> shader; };
struct ParamSh { int idx, masque; std::vector<double> v; };
struct ActT { std::string acteur; int modele = -1, npieces = 0; std::vector<uint32_t> cles; std::vector<int> seaux; std::vector<int> ordre; };

// (21/11, LU nie.exe) ORDRE DE DESSIN DES PIÈCES D'UN MODÈLE (remplace la règle DÉDUITE « _s00 -> 1re version, _s80 -> 2e »).
// 0x140591fc0 ajoute les maillages dans l'ordre 0 -> n-1, chacun dans le seau « octet +8 de la fiche de son matériau », par
// 0x140591d60 (portée ici telle quelle) : clé = entier G4MD +0x72 du matériau (cles), valeur = profondeur du modèle, la même pour
// toutes ses pièces (donc « f <= f » toujours vrai entre elles). Liste doublement chaînée : un nouvel élément passe AVANT le 1er de
// même clé, ou avant le 1er d'une autre clé (puis la suite de même clé est ramenée derrière lui). La passe couleur des personnages
// teste la profondeur en EQUAL : de deux maillages superposés (dragon clair / sombre de Choc de la vouivre), le DERNIER dessiné reste.
// Seaux : dans l'ordre de leur 1re apparition (l'ordre de parcours des seaux par le moteur n'est pas encore lu ; il ne compte
// qu'entre pièces de seaux différents exactement superposées).
static std::vector<int> ordre_pieces(const std::vector<uint32_t>& cle, const std::vector<int>& seau, int n) {
    std::vector<int> out, seauxVus;
    for (int i = 0; i < n; i++) { const int s = i < (int)seau.size() ? seau[i] : 0; if (std::find(seauxVus.begin(), seauxVus.end(), s) == seauxVus.end()) seauxVus.push_back(s); }
    for (int s : seauxVus) {
        std::vector<int> prv(n, -1), nxt(n, -1); int tete = -1, queue = -1;
        auto K = [&](int i) { return i < (int)cle.size() ? cle[i] : 0u; };
        auto avant = [&](int c, int x) { const int p = prv[c]; prv[c] = x; nxt[x] = c; prv[x] = p; if (p >= 0) nxt[p] = x; else tete = x; };
        auto apres = [&](int c, int x) { const int q = nxt[c]; nxt[c] = x; prv[x] = c; nxt[x] = q; if (q >= 0) prv[q] = x; else queue = x; };
        auto retirer = [&](int c) { const int p = prv[c], q = nxt[c]; if (q >= 0) prv[q] = p; else queue = p; if (p >= 0) nxt[p] = q; else tete = q; prv[c] = nxt[c] = -1; };
        for (int x = 0; x < n; x++) {
            if ((x < (int)seau.size() ? seau[x] : 0) != s) continue;
            int cur = tete, deplace = -1; uint32_t k5 = 0; bool fait = false;
            while (cur >= 0) {
                const uint32_t k3 = K(cur);
                if (deplace < 0) {
                    if (k3 == K(x)) {                                   // même clé : valeur égale -> avant lui
                        avant(cur, x); fait = true; break;
                    } else if (k3 != k5) {                              // autre clé (valeur égale) : avant lui, puis on continue
                        avant(cur, x); deplace = x; cur = x;
                    }
                } else if (k3 == K(x)) {                                // la suite de même clé est ramenée derrière le nouveau
                    int c = cur;
                    while (c >= 0) { if (K(c) != K(x)) break; const int q = nxt[c]; retirer(c); apres(deplace, c); deplace = c; c = q; }
                    fait = true; break;
                }
                k5 = K(cur); cur = nxt[cur];
            }
            if (fait || deplace >= 0) continue;
            if (queue < 0) { tete = queue = x; prv[x] = nxt[x] = -1; } else apres(queue, x);
        }
        for (int c = tete; c >= 0; c = nxt[c]) out.push_back(c);
    }
    return out;
}
struct AuraT { std::string acteur; double debut, fin, duree = 1, entree = 0, sortie = 0; bool boucle = true, aCourbes = false; int prio = 3, genre = 0; std::vector<std::vector<std::vector<double>>> courbes; };

struct Technique {
    JV J; LecteurAnim L; std::vector<PieceT> pieces; std::vector<EmetT> ems; std::vector<LumDefT> lums; std::vector<ActT> acteurs; std::vector<AuraT> auras;
    // BANNIÈRE (14/11/2026) : modèle de menu soccer10_01 du jeu ; courbes LUES dans ses clips, placement et vitesses MESURÉS
    // sur les vidéos (1:1 dans 1920 x 1080, centre (960, 856), entrée à 30 images/s dès « montrée », sortie à 60 dès « cachée »)
    struct TelopT { bool ok = false; double debut = 0, fin = 1e9, vin = 0.5, vout = 1, cx = 960, cy = 856;
        std::vector<std::pair<double, double>> e_in, e_out, a_in, a_out;
        static double val(const std::vector<std::pair<double, double>>& c, double t, double d) {
            if (c.empty()) return d; if (t <= c[0].first) return c[0].second; if (t >= c.back().first) return c.back().second;
            for (size_t i = 1; i < c.size(); i++) if (t < c[i].first) { const double u = (t - c[i - 1].first) / (c[i].first - c[i - 1].first);
                return c[i - 1].second + (c[i].second - c[i - 1].second) * u; }
            return c.back().second; }
        // échelle et opacité à l'image f (opacité 0 : rien)
        void etat(double f, double& s, double& a) const {
            s = 1; a = 0; if (!ok || f < debut) return;
            if (f < fin) { const double t = (f - debut) * vin; s = val(e_in, t, 1); a = val(a_in, t, 1); }
            else { const double t = (f - fin) * vout; s = val(e_out, t, 1); a = (a_out.empty() || t > a_out.back().first) ? 0 : val(a_out, t, 0); } }
    } telop, telop2;                                 // (24/11) telop2 : 2e bannière (mise en armure : ARMED après celle de l'esprit)
    std::unordered_map<std::string, int> planLum; int lumBase = -1, lumCourant = 0;
    bool aVP = false; M4 Vc, Pc; bool sansActeurs = false;       // (essais : personnages cachés)
    int duree() const { return (int)L.duree; }

    bool charger(const std::wstring& dos) {
        if (!lire_json(dos + L"\\tech.json", J)) return false;
        L.init(J["anim"]);
        for (auto& x : J["pieces"].a) { PieceT p; p.cle = x["cle"].s; p.elem = (uint32_t)x["elem"].num(); p.opaque = x["opaque"].vrai(); p.ztest = x["ztest"].vrai(); p.zecrit = x["zecrit"].vrai();
            p.surEcran = x["surEcran"].vrai(); p.panneau = (int)ou(x["panneau"].num(), 0); p.params = lire_vv(x["params"]); p.texproj = lire_vv(x["texproj"]);
            for (auto& c : x["uvCrcs"].a) p.uvCrcs.push_back((uint32_t)(int64_t)c.num());
            for (int k = 0; k < 4; k++) { p.diffuse[k] = x["diffuse"][k].num(); p.ambient[k] = x["ambient"][k].num(); }
            p.alphaRepos = x["alphaRepos"].num(); p.aColonne = x["colonne"].t == JV::NUM; p.colonne = x["colonne"].num();
            const JV& a = x["anim"];
            if (a.vrai()) { p.aAnim = true; p.acteur = a["acteur"].s; auto it = L.objetDe.find(p.acteur); p.obj = it == L.objetDe.end() ? -1 : it->second;
                p.os = (int)a["os"].num(); p.mat = (uint32_t)(int64_t)a["mat"].num();
                if (a["peau"].vrai()) { p.aPeau = true; for (auto& i : a["peau"].a) p.peau.push_back((int)i.num()); } }
            pieces.push_back(std::move(p)); }
        for (auto& x : J["emetteurs"].a) { ems.emplace_back(); EmetT& e = ems.back(); e.cle = x["cle"].s; e.acteur = x["acteur"].s; e.elem = (uint32_t)x["elem"].num();
            auto it = L.objetDe.find(e.acteur); e.obj = it == L.objetDe.end() ? -1 : it->second;
            e.opaque = x["opaque"].vrai(); e.ztest = x["ztest"].vrai(); e.surEcran = x["surEcran"].vrai(); e.monde = x["monde"].vrai(); e.grd = x["grd"].vrai();
            e.params = lire_vv(x["params"]); e.def.lire(x["def"]); }
        // (après le remplissage : adresse de def stable)
        { size_t k = 0; for (auto& x : J["emetteurs"].a) { ems[k].ptl.init(&ems[k].def, (uint32_t)(int64_t)x["graine"].num()); k++; } }
        for (auto& x : J["lumieres"].a) { LumDefT l; l.acteur = x["acteur"].s; auto it = L.objetDe.find(l.acteur); l.obj = it == L.objetDe.end() ? -1 : it->second;
            const JV& d = x["def"];
            for (auto& p : d["params"].o) { std::vector<double> v; for (auto& y : p.second.a) v.push_back(y.num()); l.params[(uint32_t)strtoull(p.first.c_str(), nullptr, 10)] = v; }
            for (auto& r : d["refs"].a) l.refs.push_back({(uint32_t)(int64_t)r["nameCrc"].num(), (uint32_t)(int64_t)r["boneNameCrc"].num(), (int)r["setType"].num(), (int)r["boneSpace"].num(), (int)r["boneRefType"].num()});
            for (auto& r : d["lumieres"].a) l.lumieres.push_back({(uint32_t)(int64_t)r["posParamCrc"].num(), (uint32_t)(int64_t)r["colorParamCrc"].num(), r["type"].num()});
            for (auto& r : d["shader"].a) l.shader.push_back({(uint32_t)(int64_t)r["matNameCrc"].num(), (int)r["setShaderParamIdx"].num(), (uint32_t)(int64_t)r["refParamNameCrc"].num(), (int)r["refParamType"].num()});
            lums.push_back(std::move(l)); }
        for (auto& x : J["acteurs"].a) { ActT t{x["acteur"].s, (int)x["modele"].num(), (int)x["pieces"].num()};
            for (auto& v : x["cles"].a) t.cles.push_back((uint32_t)(int64_t)v.num());
            for (auto& v : x["seaux"].a) t.seaux.push_back((int)v.num());
            t.ordre = ordre_pieces(t.cles, t.seaux, t.npieces);
            acteurs.push_back(t); }
        for (auto& p : J["plan_lum"].o) { planLum[p.first] = (int)p.second.num(); if (p.first == "_base") lumBase = (int)p.second.num(); }
        for (auto& x : J["anim"]["aura_balle"].a) { AuraT a; a.acteur = x["acteur"].s; a.debut = x["debut"].num(); a.fin = x["fin"].num(); a.aCourbes = x["courbes"].vrai();
            if (x["duree"].existe()) a.duree = x["duree"].num(); if (x["entree"].existe()) a.entree = x["entree"].num();
            if (x["sortie"].existe()) a.sortie = x["sortie"].num(); if (x["boucle"].existe()) a.boucle = x["boucle"].vrai();
            if (x["priorite"].existe()) a.prio = (int)x["priorite"].num(); if (x["genre"].existe()) a.genre = (int)x["genre"].num();
            for (auto& c : x["courbes"].a) a.courbes.push_back(lire_vv(c)); auras.push_back(std::move(a)); }
        // pièces cachées dans l'Atelier (cases décochées) : options.json
        for (int it = 0; it < 2; it++) { const JV& t = J[it ? "telop2" : "telop"]; TelopT& tl = it ? telop2 : telop; tl = TelopT();
          if (t.t == JV::OBJ && t["courbes"].t == JV::OBJ) { tl.ok = true; tl.debut = t["debut"].num();
              if (t["fin"].t == JV::NUM) tl.fin = t["fin"].num();
              if (t["vitesse_in"].t == JV::NUM) tl.vin = t["vitesse_in"].num(); if (t["vitesse_out"].t == JV::NUM) tl.vout = t["vitesse_out"].num();
              if (t["centre"].taille() == 2) { tl.cx = t["centre"][0].num(); tl.cy = t["centre"][1].num(); }
              auto lire = [&](const char* k, std::vector<std::pair<double, double>>& v) { for (auto& p : t["courbes"][k].a) v.push_back({p[0].num(), p[1].num()}); };
              lire("echelle_in", tl.e_in); lire("echelle_out", tl.e_out); lire("fondu_in", tl.a_in); lire("fondu_out", tl.a_out); } }
        lire_options(dos);
        return true;
    }
    // (15/11/2026) options.json (pièces cachées, couleurs de matériau, teintes des sommets / particules) : lu au chargement
    // ET relu pendant la lecture (commande « options » de l'Atelier) : plus besoin de relancer le lecteur
    void lire_options(const std::wstring& dos) {
        for (auto& p : pieces) { p.cachee = false; p.aCoul = false; p.aTeinteS = false; }
        for (auto& e : ems) { e.cachee = false; e.aTeinte = false; }
        lumK.clear();
        JV opt; if (lire_json(dos + L"\\options.json", opt)) sansActeurs = opt["sans_acteurs"].vrai();
        if (opt.existe()) for (auto& c : opt["caches"].a) {
            for (auto& p : pieces) if (p.cle == c.s) p.cachee = true;
            for (auto& e : ems) if (e.cle == c.s) e.cachee = true; }
        if (opt.existe()) for (auto& kv : opt["couleurs"].o) for (auto& p : pieces)     // (14/11/2026) couleurs de matériau
            if (p.cle == kv.first && kv.second.taille() >= 3) { p.aCoul = true; for (int k = 0; k < 3; k++) p.coul[k] = kv.second[k].num(); }
        if (opt.existe()) for (auto& kv : opt["sommets"].o) for (auto& p : pieces)     // (14/11/2026) teinte des sommets [H, C]
            if (p.cle == kv.first && kv.second.taille() >= 2) { p.aTeinteS = true; p.tH = kv.second[0].num(); p.tC = kv.second[1].num(); p.tS = kv.second.taille() >= 3 ? kv.second[2].num() : 1.0; p.tV = kv.second.taille() >= 4 ? kv.second[3].num() : 1.0; }
        if (opt.existe()) for (auto& kv : opt["lumieres"].o) if (kv.second.t == JV::NUM) lumK[kv.first] = kv.second.num();
        if (opt.existe()) for (auto& kv : opt["particules"].o) for (auto& e : ems)     // (14/11/2026) teinte des particules d'un objet
            if (e.cle.rfind(kv.first + "/", 0) == 0 && kv.second.taille() >= 2) { e.aTeinte = true; e.tH = kv.second[0].num(); e.tC = kv.second[1].num(); e.tS = kv.second.taille() >= 3 ? kv.second[2].num() : 1.0; e.tV = kv.second.taille() >= 4 ? kv.second[3].num() : 1.0; }
    }

    // ---------------------------------------------------------------- vue3d._calculerLumieres
    std::vector<LumPonct> lumPL; std::unordered_map<std::string, std::unordered_map<uint32_t, std::vector<ParamSh>>> PS;
    std::unordered_map<std::string, double> lumK;     // (23/11) intensité des lumières de l'effet par objet (options.json « lumieres »)
    void calculerLumieres(const Res& res) {
        lumPL.clear(); PS.clear();
        for (auto& D : lums) {
            if (D.obj < 0) continue; const ObjRes& o = res.objets[D.obj]; const Squelette& sq = L.objets[D.obj].sq;
            if (!o.visible) continue;
            std::unordered_map<uint32_t, std::vector<double>> P = D.params;
            for (auto& r : D.refs) {
                auto ii = sq.parCrc.find(r.boneNameCrc); auto dd = P.find(r.nameCrc); if (ii == sq.parCrc.end() || dd == P.end()) continue;
                const int i = ii->second, genre = r.boneRefType >> 4, masque = r.boneRefType & 15; double src[4]; bool a = false;
                if (r.boneSpace == 0) { if (i >= (int)o.local.size()) continue; const Loc& l = o.local[i];
                    if (genre == 1) { src[0] = l.t[0]; src[1] = l.t[1]; src[2] = l.t[2]; src[3] = 1; a = true; }
                    else if (genre == 2) { src[0] = l.e[0]; src[1] = l.e[1]; src[2] = l.e[2]; src[3] = 1; a = true; }
                    else if (genre == 4 || genre == 5) { const double x = l.r[0], y = l.r[1], z = l.r[2], w = l.r[3], s = genre == 4 ? l.e[2] : l.e[1]; a = true;
                        if (genre == 4) { src[0] = 2 * (x * z + w * y) * s; src[1] = 2 * (y * z - w * x) * s; src[2] = (1 - 2 * (x * x + y * y)) * s; src[3] = 0; }
                        else { src[0] = 2 * (x * y - w * z) * s; src[1] = (1 - 2 * (x * x + z * z)) * s; src[2] = 2 * (y * z + w * x) * s; src[3] = 0; } } }
                else { const M4 N = mulF(o.racine, o.monde[i]);
                    if (genre == 1) { src[0] = N[12]; src[1] = N[13]; src[2] = N[14]; src[3] = 1; a = true; }
                    else if (genre == 2) { for (int c = 0; c < 3; c++) src[c] = hyp3(N[4 * c], N[4 * c + 1], N[4 * c + 2]); src[3] = 1; a = true; }
                    else if (genre == 4) { src[0] = N[8]; src[1] = N[9]; src[2] = N[10]; src[3] = 0; a = true; }
                    else if (genre == 5) { src[0] = N[4]; src[1] = N[5]; src[2] = N[6]; src[3] = 0; a = true; } }
                if (!a) continue;
                std::vector<double>& dst = dd->second;
                int j = r.setType; for (int c = 0; c < 4 && j < 4; c++) if ((masque >> c) & 1) { if ((int)dst.size() <= j) dst.resize(j + 1, NAN); dst[j++] = src[c]; }
            }
            for (auto& s : D.shader) { auto v = P.find(s.ref); if (v == P.end()) continue; PS[D.acteur][s.mat].push_back({s.idx, s.type & 15, v->second}); }
            for (auto& l : D.lumieres) { auto p = P.find(l.pos), c = P.find(l.col); if (p == P.end() || c == P.end()) continue;
                LumPonct x; for (int k = 0; k < 3; k++) x.v[k] = (float)(k < (int)p->second.size() ? p->second[k] : 0);       // (exporteur : + [0, 0, 0])
                x.v[3] = (float)(p->second.size() > 3 ? p->second[3] : NAN); for (int k = 0; k < 3; k++) x.v[4 + k] = (float)(k < (int)c->second.size() ? c->second[k] : 0);
                { auto kk = lumK.find(D.acteur); if (kk != lumK.end()) for (int k = 0; k < 3; k++) x.v[4 + k] *= (float)kk->second; }   // (23/11) intensité de l'Atelier
                x.masque = (uint32_t)(int64_t)ou(l.type, 0xF7);
                if (x.v[3] != 0 && x.v[3] == x.v[3] && lumPL.size() < 255) lumPL.push_back(x); }      // (exporteur : lumières sans atténuation retirées)
        }
    }

    // ---------------------------------------------------------------- vue3d._avancerEmetteur
    void avancerEmetteur(EmetT& p, int f, const Res& courant) {
        if (f < p.ptlF || f - p.ptlF > 900) { p.ptl.reset(); p.ptlF = -1; p.aPtlClip = false; p.ptlClip.clear(); p.ptlDemarre = false; }
        Res tmp;
        for (int k = p.ptlF + 1; k <= f; k++) {
            const Res* r = &courant; if (k != f) { L.calculer(k, tmp); r = &tmp; }
            if (p.obj < 0) { p.ptlF = k; continue; }
            const ObjRes& o = r->objets[p.obj];
            const bool clipNul = !o.aClip;
            if (clipNul != !p.aPtlClip || (!clipNul && o.clip != p.ptlClip)) {
                bool dem;
                if (!p.def.mDebut.empty()) { dem = false; if (!clipNul) for (auto& x : p.def.mDebut) if (x == o.clip) dem = true; }
                else dem = !p.ptlDemarre || p.ptl.fini;
                if (dem) { p.ptl.reset(); p.ptlDemarre = true; }
                if (!clipNul) for (auto& x : p.def.mFin) if (x.first == o.clip) { if (p.ptlDemarre) p.ptl.arreter(x.second); break; }
                p.aPtlClip = !clipNul; p.ptlClip = o.clip; }
            const int i = L.objets[p.obj].sq.nom(p.def.noeud);
            const M4 N = i >= 0 ? mulF(o.racine, o.monde[i]) : o.racine;
            double e[3]; for (int c = 0; c < 3; c++) e[c] = ou(hyp3(N[4 * c], N[4 * c + 1], N[4 * c + 2]), 1);
            M3 R3; for (int r_ = 0; r_ < 3; r_++) for (int c = 0; c < 3; c++) R3[r_][c] = N[4 * c + r_] / e[c];
            M34 M; for (int r_ = 0; r_ < 3; r_++) { for (int c = 0; c < 3; c++) M[r_][c] = R3[r_][c]; M[r_][3] = N[12 + r_]; }
            // ÉCHELLE DE L'ÉMETTEUR (LU 14/11/2026, nie.exe 0x14054c501) : longueurs des colonnes de la matrice de l'OBJET d'effet
            // (méthode +0x48 du propriétaire), pas celles du nœud (avant : DÉDUIT, nœud -> étincelles x 23 de Main oméga)
            for (int c = 0; c < 3; c++) e[c] = ou(hyp3(o.racine[4 * c], o.racine[4 * c + 1], o.racine[4 * c + 2]), 1);
            const Q4 q = matQuat(R3); p.aN = true; memcpy(p.e, e, sizeof e);
            if (p.ptlDemarre) p.ptl.pas(1.0 / 60, M, q, {e[0], e[1], e[2]}, o.visible, 1);
            p.ptlVisible = o.visible; p.ptlF = k;
        }
    }

    // ---------------------------------------------------------------- une image
    void image(int f, Image& im) {
        Res res; L.calculer(f, res);
        calculerLumieres(res);
        // réglages de lumière du plan (lumiere_plans) -> n° du jeu de réglages
        { int g = -1; if (res.plan >= 0) { auto it = planLum.find(L.plans[res.plan].nom); if (it != planLum.end()) g = it->second; }
          if (g < 0) g = lumBase; if (g >= 0) lumCourant = g; }
        // pièces de maillage (vue3d._animer)
        for (auto& p : pieces) {
            if (!p.aAnim) continue;
            if (p.obj < 0) { p.animCachee = true; p.aModele = false; continue; }
            const ObjRes& o = res.objets[p.obj];
            if (p.os < 0) { p.animCachee = !o.visible; p.aModele = true; p.modele = o.racine; continue; }
            p.aModele = true; p.modele = mulF(o.racine, o.monde[p.os]);
            // (14/11/2026) PIÈCE PANNEAU PAR MATÉRIAU (LU nie.exe 0x140593632 -> 0x140598bd0, modes = os panneaux 0x14052a200,
            // vérifié dans l'émulateur) : le monde de la pièce est tourné vers la caméra du jeu au dessin (vue3d._animer)
            if (p.panneau && res.aCamM && !o.ecran2D && !p.aPeau) p.modele = panneau(p.modele, p.panneau, res.camM);
            if (p.aPeau) { p.modele = o.racine; const Squelette& sq = L.objets[p.obj].sq;   // vue3d._peauEffet (u_mtxBone)
                if (sqInv.size() <= (size_t)p.obj) sqInv.resize(p.obj + 1);
                auto& IR = sqInv[p.obj];
                if (IR.empty()) for (size_t i = 0; i < sq.mondeRepos.size(); i++) {   // (14/11/2026) liaison du G4SK si présente (vue3d.js)
                    const OsJ& b = sq.os[i];
                    if (b.aIb) { M4 m{}; const float* q = b.ib; m = {q[0], q[4], q[8], 0, q[1], q[5], q[9], 0, q[2], q[6], q[10], 0, q[3], q[7], q[11], 1}; IR.push_back(m); }
                    else IR.push_back(inv4GJ(sq.mondeRepos[i])); }
                p.peauK.clear(); for (int i : p.peau) p.peauK.push_back(i < 0 || i >= (int)o.monde.size() ? I4f() : mulF(o.monde[i], IR[i])); p.aPeauK = true; }
            p.ecran2D = o.ecran2D;
            auto io = o.opa.find(p.mat); const double op = io != o.opa.end() ? io->second : p.alphaRepos; p.aOpacite = true; p.opacite = op;
            { auto ic = o.col.find(p.mat); if (ic != o.col.end()) p.jeuCol = ic->second; else p.jeuCol.clear(); }
            p.jeuP = p.params;
            auto ip = o.prm.find(p.mat); if (ip != o.prm.end()) for (auto& x : ip->second) { const int i = (int)x[0], k = (int)x[1];
                if (i >= 0 && i < (int)p.jeuP.size()) { if ((int)p.jeuP[i].size() <= k) p.jeuP[i].resize(k + 1, NAN); p.jeuP[i][k] = x[2]; } }
            auto ia = PS.find(p.acteur);
            if (ia != PS.end()) { auto im2 = ia->second.find(p.mat); if (im2 != ia->second.end()) for (auto& s : im2->second)
                if (s.idx >= 0 && s.idx < (int)p.jeuP.size()) for (int c = 0; c < 4; c++) if ((s.masque >> c) & 1) {
                    if ((int)p.jeuP[s.idx].size() <= c) p.jeuP[s.idx].resize(c + 1, NAN); p.jeuP[s.idx][c] = c < (int)s.v.size() ? s.v[c] : NAN; } }
            p.aJeuP = true;
            for (int k = 0; k < 6; k++) { static const double D8[8] = {1, 0, 0, 0, 0, 1, 0, 0}; double* m = p.jeuUV[k];
                if (k < (int)p.texproj.size()) { for (int j = 0; j < 8; j++) m[j] = j < (int)p.texproj[k].size() ? p.texproj[k][j] : 0; } else memcpy(m, D8, sizeof D8);
                if (k < (int)p.uvCrcs.size()) { auto ib = o.uvc.find(p.uvCrcs[k]);
                    if (ib != o.uvc.end() && (ib->second.count(8) || m[1] != 0 || m[4] != 0)) {   // ROTATION G4TP type 8 (comme vue3d.js ; S R(-θ) (p - o), ordre S·R LU dans les données : 22 matrices fixes du jeu, 0 contre)
                        const auto& b = ib->second; auto has = [&](int t) { return b.count(t) > 0; };
                        const double det = m[0] * m[5] - m[1] * m[4], A0[4] = {m[0], -m[1], -m[4], m[5]}, b0[2] = {m[1] + m[2], 1 - m[5] - m[6]};
                        double o0[2] = {0, 0}; if (det != 0) { o0[0] = -(A0[3] * b0[0] - A0[1] * b0[1]) / det; o0[1] = -(-A0[2] * b0[0] + A0[0] * b0[1]) / det; }
                        const double su = (has(1) && b.at(1) != 0) ? 1 / b.at(1) : sqrt(m[0] * m[0] + m[1] * m[1]), sv = (has(2) && b.at(2) != 0) ? 1 / b.at(2) : sqrt(m[4] * m[4] + m[5] * m[5]);
                        const double th = has(8) ? b.at(8) : atan2(-m[1], m[0]), c = cos(th), s = sin(th);
                        const double ou = has(10) ? b.at(10) : o0[0], ov = has(11) ? b.at(11) : o0[1];
                        const double a00 = su * c, a01 = su * s, a10 = -sv * s, a11 = sv * c, bb0 = -(a00 * ou + a01 * ov), bb1 = -(a10 * ou + a11 * ov);
                        m[0] = a00; m[1] = -a01; m[4] = -a10; m[5] = a11; m[2] = bb0 - m[1]; m[6] = 1 - m[5] - bb1;
                    } else if (ib != o.uvc.end()) { const auto& b = ib->second; auto has = [&](int t) { return b.count(t) > 0; };
                        // CORRIGÉ 14/11/2026 (comme vue3d.js) : échelle de la matrice = 1 / valeur G4TP ; décalage non animé repris
                        // de la matrice fixe puis recalculé avec la nouvelle échelle
                        const double u0 = m[0], v0 = m[5];
                        const double su = (has(1) && b.at(1) != 0) ? 1 / b.at(1) : u0, sv = (has(2) && b.at(2) != 0) ? 1 / b.at(2) : v0;
                        const double ou = has(10) ? b.at(10) : (u0 != 0 ? -m[2] / u0 : 0), ov = has(11) ? b.at(11) : (v0 != 0 ? (m[6] - 1 + v0) / v0 : 0);
                        if (has(1) || has(10)) { m[0] = su; m[2] = -su * ou; }
                        if (has(2) || has(11)) { m[5] = sv; m[6] = 1 - sv + sv * ov; } } } }
            p.aJeuUV = true;
            p.animCachee = !o.visible || (p.os < (int)o.cache.size() && o.cache[p.os]) || op < 0.005;
        }
        for (auto& e : ems) { avancerEmetteur(e, f, res); e.animCachee = !e.ptlVisible || e.ptl.parts.empty(); }
        // effet de statut (aura du ballon) : courbes 1, 2, 3 -> StatusColor, RimColor, PowInOutDis
        // CORRIGÉ 14/11/2026 (comme vue3d.js), LU dans nie.exe (0x140f0a390, 0x140f0aa40, 0x1402a44d0) : temps des courbes =
        // temps / durée (boucle si mode 0), poids w des fondus, couleur = (c-1)w+1, contour = (c-(1,1,1,0))w+(1,1,1,0), puissance = (c-10)w+10
        bool aStatut = false; std::string stActeur; double stCol[3] = {1, 1, 1}, stRim[3] = {0, 0, 0}, stRimW = 0, stPow = 1;
        // (14/11/2026) DEUX AURAS PRÉSENTES (LU 0x140f07d50 / 0x140f0a7e9) : chaque aura reçoit la fonction table[genre]
        // (0x141918a50 ; genre = octet +0x5A de la définition) qui combine (ancienne, nouvelle) :
        //  0 (0x140f0b870) : la nouvelle seule, poids 1 ; 1 (0x140f0b5e0) : mélange linéaire des deux (poids 1 chacune) au taux f ;
        //  2 (0x140f0b530) : f <= 0,5 -> ancienne au poids 1 - 2f, sinon nouvelle au poids 2f - 1.
        //  f = poids de la nouvelle, ou 1 - poids de l'ancienne si celle-ci a une priorité plus haute (octet +0x58) et sort.
        //  Une seule aura : son propre poids (0x140f0aa40).
        { struct Etat { const AuraT* a; double w, T; bool sort; };
          auto etat = [&](const AuraT& x, Etat& e) -> bool {
              if (!x.aCourbes) return false;
              const bool dedans = f >= x.debut && f < x.fin, sortie = !dedans && x.sortie > 0 && x.fin < 1e6 && f >= x.fin && f < x.fin + x.sortie * 60;
              if (!dedans && !sortie) return false;
              const double T = (f - x.debut) / 60, D = x.duree > 0 ? x.duree : 1, Ee = x.entree, Ss = x.sortie; double w = 1;
              if (f >= x.fin) w = Ss > 0 ? 1 - ((f - x.fin) / 60) / Ss : 0;
              else if (Ee > 0 && T <= Ee) w = T / Ee;
              else if (!x.boucle) { const double T2 = T - Ee, lim = D - Ee - Ss; if (T2 > lim) w = Ss > 0 ? 1 - (T2 - lim) / Ss : 0; }
              e = {&x, w, T, f >= x.fin}; return true; };
          // valeurs d'une aura au poids w : couleur = (c-1)w+1, contour = (c-(1,1,1,0))w+(1,1,1,0), puissance = (c-10)w+10
          auto evaluer = [&](const Etat& e, double w, double* col, double* rim, double& rimw, double& pw) {
              const AuraT& x = *e.a; const double D = x.duree > 0 ? x.duree : 1, T = e.T;
              const double tn = (x.boucle ? (T > D ? fmod(T, D) : T) : std::min(T, D)) / D;
              auto val = [&](size_t k, double* out) -> bool { if (k >= x.courbes.size() || x.courbes[k].empty()) return false; const auto& ks = x.courbes[k];
                  auto g = [&](size_t a, int j) { return j < (int)ks[a].size() ? ks[a][j] : 0.0; };
                  size_t i = 0; while (i < ks.size() && tn >= ks[i][0]) i++;
                  if (i == 0) { for (int j = 0; j < 4; j++) out[j] = g(0, j + 1); return true; }
                  if (i >= ks.size()) { for (int j = 0; j < 4; j++) out[j] = g(ks.size() - 1, j + 1); return true; }
                  const double dt = ks[i][0] - ks[i - 1][0], u = dt > 0 ? (tn - ks[i - 1][0]) / dt : 0;
                  for (int j = 0; j < 4; j++) out[j] = (g(i, j + 1) - g(i - 1, j + 1)) * u + g(i - 1, j + 1);
                  return true; };
              double c[4];
              for (int j = 0; j < 3; j++) { col[j] = 1; rim[j] = 0; } rimw = 0; pw = 1;   // (valeurs de départ d'avant, sans courbe)
              if (val(0, c)) for (int j = 0; j < 3; j++) col[j] = (c[j] - 1) * w + 1;
              if (val(1, c)) { for (int j = 0; j < 3; j++) rim[j] = (c[j] - 1) * w + 1; rimw = c[3] * w; }
              if (val(2, c)) pw = (c[0] - 10) * w + 10; };
          std::vector<Etat> pres; for (auto& x : auras) { Etat e; if (etat(x, e) && (pres.empty() || x.acteur == pres[0].a->acteur)) pres.push_back(e); }
          const Etat* nv = nullptr; const Etat* an = nullptr;
          for (auto& e : pres) if (!nv || e.a->debut > nv->a->debut) nv = &e;
          for (auto& e : pres) if (&e != nv && (!an || e.a->debut > an->a->debut)) an = &e;
          if (nv) {
              double c1[3], r1[3], rw1, p1;
              if (!an) { if (nv->w > 0) { evaluer(*nv, nv->w, c1, r1, rw1, p1); aStatut = true; } }
              else {
                  const double fb = (nv->a->prio < an->a->prio && an->sort) ? 1 - an->w : nv->w;
                  if (nv->a->genre == 1) { double c0[3], r0[3], rw0, p0; evaluer(*an, 1, c0, r0, rw0, p0); evaluer(*nv, 1, c1, r1, rw1, p1);
                      for (int j = 0; j < 3; j++) { c1[j] = (c1[j] - c0[j]) * fb + c0[j]; r1[j] = (r1[j] - r0[j]) * fb + r0[j]; }
                      rw1 = (rw1 - rw0) * fb + rw0; p1 = (p1 - p0) * fb + p0; }
                  else if (nv->a->genre == 2) { if (fb <= 0.5) evaluer(*an, 1 - 2 * fb, c1, r1, rw1, p1); else evaluer(*nv, 2 * fb - 1, c1, r1, rw1, p1); }
                  else evaluer(*nv, 1, c1, r1, rw1, p1);
                  aStatut = true; }
              if (aStatut) { stActeur = nv->a->acteur; for (int j = 0; j < 3; j++) { stCol[j] = c1[j]; stRim[j] = r1[j]; } stRimW = rw1; stPow = p1; }
          } }
        // caméra du jeu (vue3d._boucle) : vue + projection en 32 bits ; image 16:9 de la fenêtre
        if (res.aCamera) {
            const double* oe = res.oeil; double z[3] = {oe[0] - res.cible[0], oe[1] - res.cible[1], oe[2] - res.cible[2]};
            auto norm = [](double* v) { const double l = ou(hyp3(v[0], v[1], v[2]), 1); v[0] /= l; v[1] /= l; v[2] /= l; };
            norm(z); const double a0 = 0, a1 = 1, a2 = 0;
            double x[3] = {a1 * z[2] - a2 * z[1], a2 * z[0] - a0 * z[2], a0 * z[1] - a1 * z[0]}; norm(x);
            double y[3] = {z[1] * x[2] - z[2] * x[1], z[2] * x[0] - z[0] * x[2], z[0] * x[1] - z[1] * x[0]};
            const double cr = cos(res.roulis), sr = sin(res.roulis); double x2[3], y2[3];
            for (int k = 0; k < 3; k++) { x2[k] = x[k] * cr + y[k] * sr; y2[k] = y[k] * cr - x[k] * sr; }
            auto dot = [](const double* a, const double* b) { return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]; };
            const double v[16] = {x2[0], y2[0], z[0], 0, x2[1], y2[1], z[1], 0, x2[2], y2[2], z[2], 0, -dot(x2, oe), -dot(y2, oe), -dot(z, oe), 1};
            for (int i = 0; i < 16; i++) Vc[i] = (float)v[i];
            const double t = 1 / tan(res.champ / 2), asp = (double)A.W / (double)std::max(A.H, 1), n = 0.05, l = 8000;
            const double P[16] = {t / asp, 0, 0, 0, 0, t, 0, 0, 0, 0, (l + n) / (n - l), -1, 0, 0, 2 * l * n / (n - l), 0};
            for (int i = 0; i < 16; i++) Pc[i] = (float)P[i];
            aVP = true;
        }
        if (!aVP) { Vc = I4f(); Pc = I4f(); }
        lignes_vers_d(Vc, im.V); lignes_vers_d(Pc, im.P);
        im.lum = (uint32_t)lumCourant; im.decor = res.decorFaux ? 0 : 1; im.lumieres = lumPL;
        const M4 mvp = mulF(Pc, Vc);
        // dessins des effets (app.js rendreD3D, ordre de vue3d._boucle) : opaques du jeu d'abord, puis les autres
        im.effets.clear();
        for (int passe = 0; passe < 2; passe++) {
            for (auto& p : pieces) { if (p.opaque != (passe == 0)) continue;
                // (15/11/2026) une pièce cachée dans l'Atelier est calculée quand même : « caché » et la couleur choisie sont
                // appliqués au dessin (lecteur.cpp), pour qu'un changement se voie aussi sur une image déjà calculée (pause)
                if (p.aAnim && p.animCachee) continue;
                im.effets.emplace_back(); DessinEffet& D = im.effets.back(); D.src = (int)(&p - pieces.data());
                // (14/11/2026) bit 2 : écriture de profondeur = clé 5 du matériau, copiée telle quelle dans l'état du jeu (LU 0x140528eb0)
                D.elem = p.elem; D.flags = 1 | ((p.surEcran || !p.ztest) ? 4 : 0) | (p.zecrit && !p.surEcran ? 2 : 0);
                M4 m = mvp;
                if (p.ecran2D) { m = M4{}; m[0] = (float)(2.0 / 1920); m[5] = (float)(2.0 / 1080); m[15] = 1; }
                lignes_vers_d(m, D.mvp); lignes_vers_d(p.aModele ? p.modele : I4f(), D.modele); lignes_vers_d(Vc, D.V); lignes_vers_d(Pc, D.P);
                std::vector<std::vector<double>> Pm = p.aJeuP ? p.jeuP : p.params;
                // (14/11/2026) LU : valeur lue par le moteur (0x141605810) dans SkillConfig (skill_config_5.00.07.00.cfg.bin, liste de 10
                // enregistrements de 0x18 octets, flottant à +4) : n° 0-9 -> ((n mod 5) + 0,5) / 128 ; hors table : 0
                if (p.aColonne && Pm.size() > 2) { if (Pm[2].size() < 4) Pm[2].resize(4, NAN); const int c = (int)p.colonne;
                    Pm[2][3] = (c >= 0 && c < 10) ? (c % 5 + 0.5) / 128 : 0.0; }
                for (int i = 0; i < 8; i++) for (int k = 0; k < 4; k++) D.params[4 * i + k] = (float)(i < (int)Pm.size() && k < (int)Pm[i].size() ? Pm[i][k] : 0);
                for (int k = 0; k < 3; k++) D.diffuse[k] = (float)p.diffuse[k]; D.diffuse[3] = (float)(p.aOpacite ? p.opacite : p.diffuse[3]);
                for (int k = 0; k < 4; k++) D.ambient[k] = (float)p.ambient[k];
                for (auto& c : p.jeuCol) { const int k = (int)c[0], i = (int)c[1];          // app.js couleurJeu
                    if (k == 0 && i < 3) D.diffuse[i] = (float)c[2]; else if (k == 1 && i >= 0 && i < 4) D.ambient[i] = (float)c[2]; }
                for (int k = 0; k < 6; k++) for (int j = 0; j < 8; j++) {
                    double v; if (p.aJeuUV) v = p.jeuUV[k][j]; else if (k < (int)p.texproj.size()) v = j < (int)p.texproj[k].size() ? p.texproj[k][j] : 0; else v = (j == 0 || j == 5) ? 1 : 0;
                    D.uv[8 * k + j] = (float)v; }
                D.grd = p.aColonne ? D.params[11] : 0;
                if (p.aPeauK) { D.os.resize(16 * p.peauK.size()); for (size_t b = 0; b < p.peauK.size(); b++) for (int i = 0; i < 16; i++) D.os[16 * b + i] = p.peauK[b][i]; }
            }
            for (auto& e : ems) { if (e.opaque != (passe == 0)) continue;
                if (e.animCachee) continue;                       // (15/11/2026) caché par l'Atelier : au dessin
                // vue3d._quadsEmetteur : quadrilatères (repère de la caméra ; SmokePar1 : repère du monde)
                M3 camRot; for (int i = 0; i < 3; i++) for (int j = 0; j < 3; j++) camRot[i][j] = Vc[i * 4 + j];
                const double t[3] = {Vc[12], Vc[13], Vc[14]}; double camPos[3];
                for (int i = 0; i < 3; i++) camPos[i] = -(camRot[i][0] * t[0] + camRot[i][1] * t[1] + camRot[i][2] * t[2]);
                e.ptl.aTeinte = false;                            // (15/11/2026) teinte posée au passage sur la carte graphique
                Quads Q; const double un[3] = {1, 1, 1}; e.ptl.quads(camRot, camPos, e.aN ? e.e : un, 1, Q);
                const int n = std::min(Q.n, 16000); if (!n) continue;
                im.effets.emplace_back(); DessinEffet& D = im.effets.back(); D.srcE = (int)(&e - ems.data());
                D.elem = e.elem; D.flags = 1 | ((e.surEcran || !e.ztest) ? 4 : 0);
                if (!e.monde) for (int i = 0; i < n * 4; i++) { const double x = Q.pos[3 * i], y = Q.pos[3 * i + 1], z = Q.pos[3 * i + 2];
                    Q.pos[3 * i] = (float)((double)Vc[0] * x + (double)Vc[4] * y + (double)Vc[8] * z + Vc[12]); Q.pos[3 * i + 1] = (float)((double)Vc[1] * x + (double)Vc[5] * y + (double)Vc[9] * z + Vc[13]);
                    Q.pos[3 * i + 2] = (float)((double)Vc[2] * x + (double)Vc[6] * y + (double)Vc[10] * z + Vc[14]); }
                D.bNv = 4 * n; D.bPos.assign(Q.pos.begin(), Q.pos.begin() + 12 * n); D.bCol.assign(Q.col.begin(), Q.col.begin() + 16 * n);
                for (int s = 0; s < 3; s++) D.bUv[s].assign(Q.uv[s].begin(), Q.uv[s].begin() + 8 * n);
                D.bANor = D.bATan = e.monde; if (e.monde) { D.bNor.assign(Q.nor.begin(), Q.nor.begin() + 12 * n); D.bTan.assign(Q.tan.begin(), Q.tan.begin() + 12 * n); }
                D.bIdx.resize(6 * n); for (int m = 0; m < n; m++) { uint16_t* q = &D.bIdx[6 * m]; q[0] = 4 * m; q[1] = 4 * m + 1; q[2] = 4 * m + 2; q[3] = 4 * m + 3; q[4] = 4 * m + 2; q[5] = 4 * m + 1; }
                if (e.monde) { lignes_vers_d(mvp, D.mvp); lignes_vers_d(Vc, D.V); } else { lignes_vers_d(Pc, D.mvp); lignes_vers_d(I4f(), D.V); }
                lignes_vers_d(I4f(), D.modele); lignes_vers_d(Pc, D.P);
                for (int i = 0; i < 8; i++) for (int k = 0; k < 4; k++) D.params[4 * i + k] = (float)(i < (int)e.params.size() && k < (int)e.params[i].size() ? e.params[i][k] : 0);
                for (int k = 0; k < 4; k++) { D.diffuse[k] = 1; D.ambient[k] = k == 3 ? 1.f : 0.f; }
                for (int k = 0; k < 6; k++) for (int j = 0; j < 8; j++) D.uv[8 * k + j] = (j == 0 || j == 5) ? 1.f : 0.f;
                D.grd = e.grd ? D.params[11] : 0;
            }
        }
        // ombres du soleil (vue3d._carteOmbre / cascadesOmbre), avec les réglages du plan
        im.om = Ombres();
        if (lumCourant < (int)J["reglages"].taille()) cascades(J["reglages"][lumCourant], im.om);
        // personnages (matrices des os), ombre des pieds, mise au point
        im.acteurs.clear(); im.pieds.clear();
        for (size_t k = 0; k < acteurs.size(); k++) { const ActT& a = acteurs[k]; auto it = res.peaux.find(a.acteur);
            if (it == res.peaux.end() || a.modele < 0 || a.npieces <= 0 || sansActeurs) continue;
            ActeurImage x; x.modele = (uint32_t)a.modele;
            { auto fi = res.fondus.find(a.acteur); x.alpha = fi != res.fondus.end() ? (float)std::min(1.0, fi->second) : 1.0f; }   // (15/11/2026) fondu
            for (int i : a.ordre) x.pieces.push_back(i);   // (21/11) toutes les pièces, dans l'ordre de dessin du jeu (ordre_pieces, LU)
            x.mats.resize(16 * it->second.size()); for (size_t b = 0; b < it->second.size(); b++) for (int i = 0; i < 16; i++) x.mats[16 * b + i] = it->second[b][i];
            x.statut = aStatut && (stActeur == a.acteur || (stActeur.rfind("b000001", 0) == 0 && a.acteur.rfind("b000001", 0) == 0)) ? 1 : 0;
            if (x.statut) { const float st[12] = {(float)stCol[0], (float)stCol[1], (float)stCol[2], 1, (float)stRim[0], (float)stRim[1], (float)stRim[2], (float)stRimW, (float)ou(stPow, 1), 0, 0, 0}; memcpy(x.st, st, sizeof st); }
            im.acteurs.push_back(std::move(x)); }
        for (auto& A_ : L.acteurs) { auto it = res.peaux.find(A_.acteur); if (it == res.peaux.end() || !A_.aCollision) continue; const auto& Mm = it->second;
            for (auto& c : A_.collision) { int i = -1; for (size_t b = 0; b < A_.sq.os.size(); b++) if (A_.sq.os[b].nom == c.os) { i = (int)b; break; }
                if (i < 0 || i >= (int)Mm.size()) continue; const M4& m = Mm[i]; const M4& r = A_.sq.mondeRepos[i];
                double W[16]; for (int col = 0; col < 4; col++) for (int row = 0; row < 4; row++) { double s = 0; for (int q = 0; q < 4; q++) s += (double)m[q * 4 + row] * (double)r[col * 4 + q]; W[col * 4 + row] = s; }
                double tt[3]; for (int row = 0; row < 3; row++) tt[row] = W[row] * c.dec[0] + W[4 + row] * c.dec[1] + W[8 + row] * c.dec[2] + W[12 + row];
                for (int row = 0; row < 3; row++) { im.pieds.push_back(W[row] * c.taille[0]); im.pieds.push_back(W[4 + row] * c.taille[1]); im.pieds.push_back(W[8 + row] * c.taille[2]); im.pieds.push_back(tt[row]); } } }
        im.foyer = res.aCamera ? ou(hyp3(res.cible[0] - res.oeil[0], res.cible[1] - res.oeil[1], res.cible[2] - res.oeil[2]), 10) : 10;
    }
    std::vector<std::vector<M4>> sqInv;

    // vue3d._carteOmbre + cascadesOmbre (LiSPSM, 3 tranches)
    void cascades(const JV& R, Ombres& om) {
        // (R.x || défaut) puis [i] : une liste vide est « vraie » en JavaScript et son [0] vaut undefined (NaN)
        auto arr = [&](const char* k, std::initializer_list<double> d) { std::vector<double> v; const JV& x = R[k]; if (x.vrai()) for (auto& y : x.a) v.push_back(y.num()); else v.assign(d); return v; };
        auto prem = [&](const char* k, double d) { return R[k].vrai() ? R[k][0].num() : d; };
        const double uSD = prem("useShadowDir", 0);
        std::vector<double> dir = (uSD != 0 && uSD == uSD && R["shadowDir"].vrai()) ? arr("shadowDir", {}) : arr("lightDir", {0, 0.77, 0.64});
        while (dir.size() < 3) dir.push_back(NAN);
        const double aut = prem("isAutoCascadeRange", 0), nC = 0.1; double tr[3][2];
        if (aut != 0 && aut == aut) { const double fm = prem("autoCascadeFarMax", 100), Lr = fm - nC;
            tr[0][0] = nC; tr[0][1] = nC + Lr / 3; tr[1][0] = nC + Lr / 3; tr[1][1] = nC + 2 * Lr / 3; tr[2][0] = nC + 2 * Lr / 3; tr[2][1] = fm; }
        else { auto N = arr("shadowCascadeNear", {0.1, 20, 50}), Fa = arr("shadowCascadeFar", {20, 50, 150}); for (int i = 0; i < 3; i++) { tr[i][0] = i < (int)N.size() ? N[i] : NAN; tr[i][1] = i < (int)Fa.size() ? Fa[i] : NAN; } }
        const double ref = prem("ref_scale", 4);
        const M4& V = Vc; const M4& P = Pc;
        const double r0[3] = {V[0], V[4], V[8]}, r1[3] = {V[1], V[5], V[9]}, r2[3] = {V[2], V[6], V[10]}, t[3] = {V[12], V[13], V[14]};
        double eye[3]; for (int i = 0; i < 3; i++) eye[i] = -(r0[i] * t[0] + r1[i] * t[1] + r2[i] * t[2]);
        const double tX = 1 / (double)P[0], tY = 1 / (double)P[5]; const double v[3] = {-r2[0], -r2[1], -r2[2]};
        auto dot = [](const double* a, const double* b) { return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]; };
        auto norm = [](double* a) { const double l = ou(hyp3(a[0], a[1], a[2]), 1); a[0] /= l; a[1] /= l; a[2] /= l; };
        double z[3] = {dir[0], dir[1], dir[2]}; norm(z); const double vz = dot(v, z);
        double y[3] = {v[0] - vz * z[0], v[1] - vz * z[1], v[2] - vz * z[2]}; norm(y);
        const double x[3] = {y[1] * z[2] - y[2] * z[1], y[2] * z[0] - y[0] * z[2], y[0] * z[1] - y[1] * z[0]};
        for (int s = 0; s < 3; s++) {
            double C[8][3]; int nC_ = 0;
            for (double d : {tr[s][0], tr[s][1]}) for (double sx : {-1.0, 1.0}) for (double sy : {-1.0, 1.0}) {
                const double X = sx * d * tX, Y = sy * d * tY, Z = -d; for (int i = 0; i < 3; i++) C[nC_][i] = r0[i] * X + r1[i] * Y + r2[i] * Z; nC_++; }
            double Ys[8], mn = INFINITY, mxY = -INFINITY; for (int k = 0; k < 8; k++) { Ys[k] = dot(C[k], y); mn = std::min(mn, Ys[k]); mxY = std::max(mxY, Ys[k]); }
            const double e = mxY - mn, n = ref > 1 ? e / (ref - 1) : 1000, fz = n + e;
            double xa = INFINITY, xb = -INFINITY, za = INFINITY, zb = -INFINITY;
            for (int k = 0; k < 8; k++) { const double q0 = dot(C[k], x), q1 = Ys[k] - mn + n, q2 = dot(C[k], z); const double rxv = q0 / q1, rzv = q2 / q1;
                xa = std::min(xa, rxv); xb = std::max(xb, rxv); za = std::min(za, rzv); zb = std::max(zb, rzv); }
            const double Am[4][4] = {{x[0], x[1], x[2], -dot(x, eye)}, {y[0], y[1], y[2], -dot(y, eye) - mn + n}, {z[0], z[1], z[2], -dot(z, eye)}, {0, 0, 0, 1}};
            const double B[4][4] = {{2 / (xb - xa), -(xb + xa) / (xb - xa), 0, 0}, {0, (fz + n) / (fz - n), 0, -2 * fz * n / (fz - n)}, {0, zb / (zb - za), -1 / (zb - za), 0}, {0, 1, 0, 0}};
            for (int i = 0; i < 4; i++) for (int j = 0; j < 4; j++) { double sm = 0; for (int k = 0; k < 4; k++) sm += B[i][k] * Am[k][j]; om.vp[s][j * 4 + i] = (float)sm; }
            om.tr[s][0] = tr[s][0]; om.tr[s][1] = tr[s][1];
        }
        double dn[3] = {dir[0], dir[1], dir[2]}; norm(dn); for (int k = 0; k < 3; k++) om.dir[k] = dn[k];
        auto bi = arr("shadowBiasParam", {0.01, 1, 0.1}); for (int k = 0; k < 3; k++) om.biais[k] = k < (int)bi.size() ? bi[k] : 0;
        om.present = 1; om.T = 1024;
    }
};
