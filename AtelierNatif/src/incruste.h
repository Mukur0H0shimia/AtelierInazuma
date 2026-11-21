// LECTEUR INCRUSTÉ DANS L'ATELIER (14/11/2026) : au lieu d'une fenêtre à part, le lecteur dessine dans une fenêtre sans bordure
// rattachée à la fenêtre de l'Atelier (Edge en mode application) et posée exactement sur la vue 3D de la page.
// - fenêtre « possédée » par celle de l'Atelier : toujours juste au-dessus d'elle, cachée avec elle, ne prend jamais le clavier
//   (les touches restent à la page, qui envoie les commandes) ;
// - la page envoie, par le serveur, des commandes texte en UDP (127.0.0.1:<port>) : « rect x y l h » (zone de la vue en pixels
//   physiques depuis le coin de la page), « basculer », « pause 0|1 », « image n », « pas ±n », « debut », « ecran »,
//   « cacher », « montrer », « quitter », « etat » (réponse : « image f n pause p ips x ») ;
// - l'image du jeu (16:9) est centrée dans la zone ; la fenêtre suit la fenêtre de l'Atelier (déplacée, agrandie, réduite).
#pragma once
#include <winsock2.h>
#include <dwmapi.h>
#pragma comment(lib, "ws2_32.lib")
#pragma comment(lib, "dwmapi.lib")

struct Incruste {
    bool actif = false, cache = false, zoneOk = false; SOCKET s = INVALID_SOCKET;
    HWND proprio = nullptr, rendu = nullptr; RECT zone = {}; int ox = 0, oy = 0;   // ox, oy : largeur et hauteur de la page (pixels physiques)
    RECT pose = {}; bool visible = false; double ips = 0; int image = 0, n = 0;
    // (14/11/2026) filet de sécurité : un lecteur que plus personne ne commande se ferme (avant : fenêtre sans bordure
    // restée devant l'Atelier, impossible à fermer) — serveur disparu (--parent), ou page muette depuis 75 s (elle demande
    // « etat » toutes les 200 ms ; 75 s : au-delà du ralentissement des minuteurs d'une page cachée, 1 par minute)
    HANDLE parent = nullptr; ULONGLONG dernier = 0;
};
static Incruste INC;

// (14/11/2026, 2e version) la fenêtre de l'Atelier est cherchée dans N'IMPORTE QUEL navigateur (Edge en mode application,
// Opera, Chrome, Firefox…) : 1) titre contenant le JETON que la page vient de mettre dans son titre (unique : jamais la
// fenêtre d'un autre Atelier) ; 2) titre contenant « Atelier Inazuma » ; 3) fenêtre de navigateur au premier plan (on vient
// d'y cliquer « lecture »).
static std::wstring JETON;
struct ChercheF { const wchar_t* motif; HWND h; };
static bool classe_navigateur(HWND h) {
    wchar_t c[64]; GetClassNameW(h, c, 64);
    // (14/11/2026) + « Atelier Inazuma.exe » (AtelierCouleurs/lanceur : WinForms + WebView2) : classe WindowsForms10.*, titre
    // toujours « Atelier Inazuma » (le jeton de la page n'y apparaît pas) ; la page est dans un Chrome_RenderWidgetHostHWND enfant
    return !wcscmp(c, L"Chrome_WidgetWin_1") || !wcscmp(c, L"MozillaWindowClass") || !wcsncmp(c, L"WindowsForms10.", 15);
}
static BOOL CALLBACK chercher_titre(HWND h, LPARAM l) {
    ChercheF* c = (ChercheF*)l;
    if (!IsWindowVisible(h) || GetWindow(h, GW_OWNER)) return TRUE;
    wchar_t t[512]; GetWindowTextW(h, t, 512);
    if (wcsstr(t, c->motif) && classe_navigateur(h)) { c->h = h; return FALSE; }
    return TRUE;
}
static HWND trouver_atelier() {
    for (int k = 0; k < 40 && !JETON.empty(); k++) {          // (la page change son titre juste avant : jusqu'à 2 s)
        ChercheF c{JETON.c_str(), nullptr}; EnumWindows(chercher_titre, (LPARAM)&c); if (c.h) return c.h;
        ChercheF w{L"Atelier Inazuma", nullptr}; EnumWindows(chercher_titre, (LPARAM)&w);      // lanceur WebView2 : pas de jeton
        if (w.h) { wchar_t cl[64]; GetClassNameW(w.h, cl, 64); if (!wcsncmp(cl, L"WindowsForms10.", 15)) return w.h; }
        Sleep(50); }
    HWND f = GetForegroundWindow();
    if (f) { wchar_t t[512]; GetWindowTextW(f, t, 512); if (wcsstr(t, L"Atelier Inazuma") && classe_navigateur(f)) return f; }
    ChercheF c{L"Atelier Inazuma", nullptr}; EnumWindows(chercher_titre, (LPARAM)&c); if (c.h) return c.h;
    if (f && classe_navigateur(f)) { wchar_t t[512]; GetWindowTextW(f, t, 512); if (wcscmp(t, L"Claude")) return f; }
    return nullptr;
}
// zone de la page : sous-fenêtre de rendu (Chrome, Edge, Opera) dont la taille est celle de la page (ox × oy) ; à défaut la plus grande
struct ChercheR { int ox, oy; HWND h; long score; };
static BOOL CALLBACK chercher_rendu(HWND h, LPARAM l) {
    ChercheR* c = (ChercheR*)l; wchar_t cl[64]; GetClassNameW(h, cl, 64);
    if (wcscmp(cl, L"Chrome_RenderWidgetHostHWND") || !IsWindowVisible(h)) return TRUE;
    RECT r; GetClientRect(h, &r);
    const long sc = (c->ox > 0) ? -(labs(r.right - c->ox) + labs(r.bottom - c->oy)) : r.right * r.bottom;
    if (!c->h || sc > c->score) { c->h = h; c->score = sc; }
    return TRUE;
}
static HWND trouver_rendu() {
    ChercheR c{INC.ox, INC.oy, nullptr, 0}; if (INC.proprio) EnumChildWindows(INC.proprio, chercher_rendu, (LPARAM)&c);
    if (c.h && INC.ox > 0 && c.score < -8) return nullptr;    // aucune ne fait la taille de la page : calcul par la zone cliente
    return c.h;
}
static bool incruste_init(int port) {
    WSADATA w; if (WSAStartup(MAKEWORD(2, 2), &w)) return false;
    INC.s = socket(AF_INET, SOCK_DGRAM, IPPROTO_UDP); if (INC.s == INVALID_SOCKET) return false;
    sockaddr_in a = {}; a.sin_family = AF_INET; a.sin_port = htons((u_short)port); a.sin_addr.s_addr = htonl(INADDR_LOOPBACK);
    if (bind(INC.s, (sockaddr*)&a, sizeof a)) return false;
    u_long nb = 1; ioctlsocket(INC.s, FIONBIO, &nb);
    INC.proprio = trouver_atelier();
    INC.rendu = trouver_rendu();
    INC.actif = true;
    { FILE* x = fopen("lecteur_incruste.txt", "w"); if (x) { RECT r = {}; if (INC.proprio) GetWindowRect(INC.proprio, &r);
        POINT p = {0, 0}; if (INC.rendu) ClientToScreen(INC.rendu, &p); RECT rc = {}; if (INC.rendu) GetClientRect(INC.rendu, &rc);
        wchar_t t[256] = L"", cl[64] = L""; if (INC.proprio) { GetWindowTextW(INC.proprio, t, 256); GetClassNameW(INC.proprio, cl, 64); }
        fprintf(x, "jeton '%ls' -> titre '%ls' classe %ls\n", JETON.c_str(), t, cl);
        fprintf(x, "atelier %p fenetre %ld,%ld-%ld,%ld ; page %p origine %ld,%ld taille %ldx%ld\n", (void*)INC.proprio, r.left, r.top, r.right, r.bottom, (void*)INC.rendu, p.x, p.y, rc.right, rc.bottom); fclose(x); } }
    return INC.proprio != nullptr;
}
// origine de la page (pixels physiques, écran)
static POINT origine_page() {
    POINT p = {0, 0};
    if (INC.rendu && IsWindow(INC.rendu)) { ClientToScreen(INC.rendu, &p); return p; }
    // Edge (mode application) : une seule sous-fenêtre « Intermediate D3D Window » sur toute la zone cliente, barre de titre
    // comprise ; la page en occupe le BAS : origine = coin de la zone cliente + (largeur − page, hauteur − page)
    RECT c; GetClientRect(INC.proprio, &c); ClientToScreen(INC.proprio, &p);
    if (INC.ox > 0 && INC.oy > 0) { p.x += std::max(0L, c.right - INC.ox); p.y += std::max(0L, c.bottom - INC.oy); }
    return p;
}
static void redimensionner(int w, int h);       // (lecteur.cpp)
static void charger_modifs_rel();               // (lecteur.cpp)
static void charger_telop_rel();                // (lecteur.cpp) (22/11) bannière relue
static void options_rel();                      // (lecteur.cpp) pièces cachées / couleurs relues
static void surligner(const char* liste);       // (lecteur.cpp) pièces localisées plus lumineuses
static void incruste_commandes(int n, int image, bool& pause_, double& temps_, int& pas_) {
    char b[512]; sockaddr_in de; int lg = sizeof de;
    for (;;) {
        const int k = recvfrom(INC.s, b, sizeof b - 1, 0, (sockaddr*)&de, &lg); if (k <= 0) break; b[k] = 0;
        INC.dernier = GetTickCount64();
        int x, y, w, h, ox, oy, v;
        if (sscanf(b, "rect %d %d %d %d %d %d", &x, &y, &w, &h, &ox, &oy) >= 4) {
            INC.zone = {x, y, x + w, y + h}; INC.zoneOk = w > 8 && h > 8;
            if (sscanf(b, "rect %d %d %d %d %d %d", &x, &y, &w, &h, &ox, &oy) == 6 && (ox != INC.ox || oy != INC.oy)) {
                INC.ox = ox; INC.oy = oy; INC.rendu = trouver_rendu(); } }
        else if (!strcmp(b, "basculer")) pause_ = !pause_;
        else if (sscanf(b, "pause %d", &v) == 1) pause_ = v != 0;
        else if (sscanf(b, "image %d", &v) == 1) { temps_ = std::max(0, v) / 60.0 + 0.5 / 60; pause_ = true; A.premiere = true; }
        else if (sscanf(b, "pas %d", &v) == 1) { pause_ = true; pas_ += v; }
        else if (!strcmp(b, "debut")) { temps_ = 0; A.premiere = true; }
        else if (!strcmp(b, "ecran")) { A.effetsEcran = !A.effetsEcran; A.premiere = true; }
        else if (!strcmp(b, "cacher")) INC.cache = true;
        else if (!strcmp(b, "montrer")) INC.cache = false;
        else if (!strcmp(b, "quitter")) PostQuitMessage(0);
        else if (!strcmp(b, "textures")) charger_modifs_rel();         // retouche de couleur dans l'Atelier : modifs.bin relu
        else if (!strcmp(b, "telop")) charger_telop_rel();             // (22/11) bannière changée dans l'Atelier : telop.bin relu
        else if (!strcmp(b, "options")) options_rel();                 // (15/11/2026) pièces cachées / couleurs : options.json relu
        else if (!strncmp(b, "surligner ", 10)) surligner(b + 10);       // (15/11/2026) « Localiser la texture » : éclat
        else if (!strcmp(b, "etat")) { char r[400]; const int m = sprintf_s(r, "image %d %d pause %d ips %.0f ecran %d choix %d %s", image, n, pause_ ? 1 : 0, INC.ips,
                                                     A.effetsEcran ? 1 : 0, CHOIX_N, CHOIX.empty() ? "-" : CHOIX.substr(0, 200).c_str());
            sendto(INC.s, r, m, 0, (sockaddr*)&de, lg); }
        lg = sizeof de;
    }
}
// plus personne ne commande ce lecteur ? (serveur fermé, ou page muette depuis 75 s)
static bool incruste_abandonne() {
    if (INC.parent && WaitForSingleObject(INC.parent, 0) == WAIT_OBJECT_0) return true;
    if (!INC.dernier) INC.dernier = GetTickCount64();
    return GetTickCount64() - INC.dernier > 75000;
}
// place la fenêtre sur la vue (16:9 centré) ; à appeler à chaque image
static void incruste_placer() {
    if (!IsWindow(INC.proprio)) { PostQuitMessage(0); return; }
    const bool vis = !INC.cache && INC.zoneOk && !IsIconic(INC.proprio) && IsWindowVisible(INC.proprio);
    if (!vis) { if (INC.visible) { ShowWindow(A.fen, SW_HIDE); INC.visible = false; } return; }
    const POINT o = origine_page();
    const int zw = INC.zone.right - INC.zone.left, zh = INC.zone.bottom - INC.zone.top;
    int w = zw, h = zw * 9 / 16; if (h > zh) { h = zh; w = zh * 16 / 9; }
    RECT r = {o.x + INC.zone.left + (zw - w) / 2, o.y + INC.zone.top + (zh - h) / 2, 0, 0}; r.right = r.left + w; r.bottom = r.top + h;
    if (!INC.visible || memcmp(&r, &INC.pose, sizeof r)) {
        const bool taille = (r.right - r.left) != (INC.pose.right - INC.pose.left) || (r.bottom - r.top) != (INC.pose.bottom - INC.pose.top);
        SetWindowPos(A.fen, nullptr, r.left, r.top, w, h, SWP_NOACTIVATE | SWP_NOZORDER | SWP_SHOWWINDOW);
        if (taille) redimensionner(w, h);
        INC.pose = r; INC.visible = true;
        FILE* x = fopen("lecteur_incruste.txt", "a"); if (x) { fprintf(x, "zone %ld,%ld %ldx%ld -> image %ld,%ld %dx%d (origine page %ld,%ld)\n", INC.zone.left, INC.zone.top, zw, zh, r.left, r.top, w, h, o.x, o.y); fclose(x); }
    }
}
