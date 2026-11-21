/* Lecture des paquets du jeu, partie rapide (même calcul que moteur/paquets_jeu.py, en C) :
 *   xor_cpk   : XOR des .cpk (clé = crc32 du nom de l'archive, dépend de la position dans le fichier) ;
 *   crilayla  : décompression CRILAYLA (format public de CRI).
 * Compilé par compiler.bat en paquets.dll ; si la DLL manque, paquets_jeu.py fait le même calcul en Python.
 * Fast part of the pack reader (XOR + CRILAYLA), same results as the Python code. */
#include <stdint.h>
#include <string.h>
#include <stdlib.h>
#include <math.h>

static uint32_t T[256];
static int T_pret = 0;

static void t_init(void)
{
    if (T_pret)
        return;
    for (uint32_t i = 0; i < 256; i++) {
        uint32_t c = i;
        for (int k = 0; k < 8; k++)
            c = (c & 1) ? (c >> 1) ^ 0xEDB88320u : c >> 1;
        T[i] = c;
    }
    T_pret = 1;
}

__declspec(dllexport) void xor_cpk(uint8_t *buf, int64_t n, int64_t pos, uint32_t cle)
{
    t_init();
    uint32_t K = 0;
    int64_t bloc = -1;
    for (int64_t i = 0; i < n; i++) {
        int64_t p = pos + i;
        int64_t b = p & ~(int64_t)3;
        if (b != bloc) {
            uint32_t v = ~(uint32_t)b;
            for (int k = 0; k < 4; k++)
                v = (v >> 8) ^ T[(v & 0xff) ^ ((cle >> (8 * k)) & 0xff)];
            K = ~v;
            bloc = b;
        }
        uint32_t s = (uint32_t)(2 * (p & 3));
        uint32_t x = (((((K >> (s + 8)) & 3) | (((K >> s) << 2) & 0xff)) << 2 | ((K >> (s + 16)) & 3)) << 2
                      | ((K >> (s + 24)) & 3));
        buf[i] ^= (uint8_t)(x & 0xff);
    }
}

typedef struct {
    const uint8_t *src;
    int64_t pos;      /* lu à l'envers */
    int bits;
    uint32_t octet;
    int erreur;
} Flux;

static uint32_t lire_bits(Flux *f, int n)
{
    uint32_t v = 0;
    while (n) {
        if (f->bits == 0) {
            if (f->pos < 0) {
                f->erreur = 1;
                return 0;
            }
            f->octet = f->src[f->pos--];
            f->bits = 8;
        }
        int k = n < f->bits ? n : f->bits;
        v = (v << k) | ((f->octet >> (f->bits - k)) & ((1u << k) - 1));
        f->bits -= k;
        n -= k;
    }
    return v;
}

/* ------------------------------------------------------------------ BC7 / BC1 (même calcul que AtelierMaillots/lib) */
static const uint16_t P2[64] = {0xCCCC,0x8888,0xEEEE,0xECC8,0xC880,0xFEEC,0xFEC8,0xEC80,0xC800,0xFFEC,0xFE80,0xE800,0xFFE8,0xFF00,0xFFF0,0xF000,
    0xF710,0x008E,0x7100,0x08CE,0x008C,0x7310,0x3100,0x8CCE,0x088C,0x3110,0x6666,0x366C,0x17E8,0x0FF0,0x718E,0x399C,
    0xAAAA,0xF0F0,0x5A5A,0x33CC,0x3C3C,0x55AA,0x9696,0xA55A,0x73CE,0x13C8,0x324C,0x3BDC,0x6996,0xC33C,0x9966,0x0660,
    0x0272,0x04E4,0x4E40,0x2720,0xC936,0x936C,0x39C6,0x639C,0x9336,0x9CC6,0x817E,0xE718,0xCCF0,0x0FCC,0x7744,0xEE22};
static const uint32_t P3[64] = {0xaa685050,0x6a5a5040,0x5a5a4200,0x5450a0a8,0xa5a50000,0xa0a05050,0x5555a0a0,0x5a5a5050,
    0xaa550000,0xaa555500,0xaaaa5500,0x90909090,0x94949494,0xa4a4a4a4,0xa9a59450,0x2a0a4250,
    0xa5945040,0x0a425054,0xa5a5a500,0x55a0a0a0,0xa8a85454,0x6a6a4040,0xa4a45000,0x1a1a0500,
    0x0050a4a4,0xaaa59090,0x14696914,0x69691400,0xa08585a0,0xaa821414,0x50a4a450,0x6a5a0200,
    0xa9a58000,0x5090a0a8,0xa8a09050,0x24242424,0x00aa5500,0x24924924,0x24499224,0x50a50a50,
    0x500aa550,0xaaaa4444,0x66660000,0xa5a0a5a0,0x50a050a0,0x69286928,0x44aaaa44,0x66666600,
    0xaa444444,0x54a854a8,0x95809580,0x96969600,0xa85454a8,0x80959580,0xaa141414,0x96960000,
    0xaaaa1414,0xa05050a0,0xa0a5a5a0,0x96000000,0x40804080,0xa9a8a9a8,0xaaaaaa44,0x2a4a5254};
static const uint8_t A2[64] = {15,15,15,15,15,15,15,15,15,15,15,15,15,15,15,15,15,2,8,2,2,8,8,15,2,8,2,2,8,8,2,2,
    15,15,6,8,2,8,15,15,2,8,2,2,2,15,15,6,6,2,6,8,15,15,2,2,15,15,15,15,15,2,2,15};
static const uint8_t A3a[64] = {3,3,15,15,8,3,15,15,8,8,6,6,6,5,3,3,3,3,8,15,3,3,6,10,5,8,8,6,8,5,15,15,
    8,15,3,5,6,10,8,15,15,3,15,5,15,15,15,15,3,15,5,5,5,8,5,10,5,10,8,13,15,12,3,3};
static const uint8_t A3b[64] = {15,8,8,3,15,15,3,8,15,15,15,15,15,15,15,8,15,8,15,3,15,8,15,8,3,15,6,10,15,15,10,8,
    15,3,15,10,10,8,9,10,6,15,8,15,3,6,6,8,15,3,15,15,15,15,15,15,15,15,15,15,3,15,15,8};
static const uint8_t W2[4] = {0,21,43,64}, W3[8] = {0,9,18,27,37,46,55,64},
    W4[16] = {0,4,9,13,17,21,26,30,34,38,43,47,51,55,60,64};
/* NS PB RB ISB CB AB EPB SPB IB IB2 */
static const uint8_t MODES[8][10] = {{3,4,0,0,4,0,1,0,3,0},{2,6,0,0,6,0,0,1,3,0},{3,6,0,0,5,0,0,0,2,0},{2,6,0,0,7,0,1,0,2,0},
    {1,0,2,1,5,6,0,0,2,3},{1,0,2,0,7,8,0,0,2,2},{1,0,0,0,7,7,1,0,4,0},{2,6,0,0,5,5,1,0,2,0}};

static const uint8_t *poids(int n) { return n == 2 ? W2 : n == 3 ? W3 : W4; }

typedef struct { uint64_t lo, hi; int pos; } Bits;
static uint32_t rd(Bits *b, int n)
{
    uint32_t v = 0;
    for (int k = 0; k < n; k++, b->pos++) {
        int p = b->pos;
        uint64_t bit = p < 64 ? (b->lo >> p) & 1 : p < 128 ? (b->hi >> (p - 64)) & 1 : 0;
        v |= (uint32_t)bit << k;
    }
    return v;
}
static int etendre(int v, int n) { v <<= (8 - n); return v | (v >> n); }

static void bloc_bc7(const uint8_t *src, uint8_t px[16][4])
{
    memset(px, 0, 64);
    if (src[0] == 0)
        return;                                   /* bloc nul ou mode > 7 : transparent noir (comme le Python) */
    int mode = 0;
    while (!((src[0] >> mode) & 1))
        mode++;
    Bits b;
    memcpy(&b.lo, src, 8); memcpy(&b.hi, src + 8, 8); b.pos = mode + 1;
    const uint8_t *M = MODES[mode];
    int NS = M[0], PB = M[1], RB = M[2], ISB = M[3], CB = M[4], AB = M[5], EPB = M[6], SPB = M[7], IB = M[8], IB2 = M[9];
    int part = rd(&b, PB), rot = rd(&b, RB), isel = rd(&b, ISB);
    int ne = NS * 2, ep[6][4];
    for (int i = 0; i < ne; i++) { ep[i][0] = ep[i][1] = ep[i][2] = 0; ep[i][3] = 255; }
    for (int c = 0; c < 3; c++)
        for (int i = 0; i < ne; i++) ep[i][c] = rd(&b, CB);
    if (AB)
        for (int i = 0; i < ne; i++) ep[i][3] = rd(&b, AB);
    int cb = CB, ab = AB, nc = AB ? 4 : 3;
    if (EPB) {
        for (int i = 0; i < ne; i++) {
            int p = rd(&b, 1);
            for (int c = 0; c < nc; c++) ep[i][c] = (ep[i][c] << 1) | p;
        }
        cb += 1; ab += AB ? 1 : 0;
    } else if (SPB) {
        for (int s = 0; s < NS; s++) {
            int p = rd(&b, 1);
            for (int i = 2 * s; i <= 2 * s + 1; i++)
                for (int c = 0; c < nc; c++) ep[i][c] = (ep[i][c] << 1) | p;
        }
        cb += 1; ab += AB ? 1 : 0;
    }
    for (int i = 0; i < ne; i++) {
        for (int c = 0; c < 3; c++) ep[i][c] = etendre(ep[i][c], cb);
        ep[i][3] = AB ? etendre(ep[i][3], ab) : 255;
    }
    int sub[16], anc[3] = {0, -1, -1};
    for (int i = 0; i < 16; i++)
        sub[i] = NS == 1 ? 0 : NS == 2 ? (P2[part] >> i) & 1 : (P3[part] >> (2 * i)) & 3;
    if (NS == 2) anc[1] = A2[part];
    if (NS == 3) { anc[1] = A3a[part]; anc[2] = A3b[part]; }
    int idx[16], idx2[16];
    for (int i = 0; i < 16; i++) {
        int a = (i == anc[0] || i == anc[1] || i == anc[2]);
        idx[i] = rd(&b, a ? IB - 1 : IB);
    }
    if (IB2)
        for (int i = 0; i < 16; i++) idx2[i] = rd(&b, i == 0 ? IB2 - 1 : IB2);
    for (int i = 0; i < 16; i++) {
        int *e0 = ep[2 * sub[i]], *e1 = ep[2 * sub[i] + 1], w, wa;
        if (!IB2) { w = poids(IB)[idx[i]]; wa = w; }
        else if (isel) { w = poids(IB2)[idx2[i]]; wa = poids(IB)[idx[i]]; }
        else { w = poids(IB)[idx[i]]; wa = poids(IB2)[idx2[i]]; }
        int r = ((64 - w) * e0[0] + w * e1[0] + 32) >> 6;
        int g = ((64 - w) * e0[1] + w * e1[1] + 32) >> 6;
        int bb = ((64 - w) * e0[2] + w * e1[2] + 32) >> 6;
        int a = ((64 - wa) * e0[3] + wa * e1[3] + 32) >> 6, t;
        if (rot == 1) { t = r; r = a; a = t; }
        else if (rot == 2) { t = g; g = a; a = t; }
        else if (rot == 3) { t = bb; bb = a; a = t; }
        px[i][0] = (uint8_t)r; px[i][1] = (uint8_t)g; px[i][2] = (uint8_t)bb; px[i][3] = (uint8_t)a;
    }
}

static void c565(uint16_t v, int o[3])
{
    int r = (v >> 11) & 31, g = (v >> 5) & 63, b = v & 31;
    o[0] = r << 3 | r >> 2; o[1] = g << 2 | g >> 4; o[2] = b << 3 | b >> 2;
}

static void bloc_bc1(const uint8_t *src, uint8_t px[16][4])
{
    uint16_t c0, c1; uint32_t idx;
    memcpy(&c0, src, 2); memcpy(&c1, src + 2, 2); memcpy(&idx, src + 4, 4);
    int a[3], b[3], cs[4][4];
    c565(c0, a); c565(c1, b);
    for (int k = 0; k < 3; k++) {
        cs[0][k] = a[k]; cs[1][k] = b[k];
        if (c0 > c1) { cs[2][k] = (2 * a[k] + b[k]) / 3; cs[3][k] = (a[k] + 2 * b[k]) / 3; }
        else { cs[2][k] = (a[k] + b[k]) / 2; cs[3][k] = 0; }
    }
    cs[0][3] = cs[1][3] = cs[2][3] = 255; cs[3][3] = c0 > c1 ? 255 : 0;
    for (int i = 0; i < 16; i++) {
        int *c = cs[(idx >> (2 * i)) & 3];
        px[i][0] = (uint8_t)c[0]; px[i][1] = (uint8_t)c[1]; px[i][2] = (uint8_t)c[2]; px[i][3] = (uint8_t)c[3];
    }
}

/* image BC7 (format 7) ou BC1 (format 1) de w x h pixels -> RGBA (w*h*4, rangées de haut en bas) ; 0 si tout va bien */
__declspec(dllexport) int decoder_bc(const uint8_t *src, int64_t nsrc, int w, int h, int format, uint8_t *rgba)
{
    int taille = format == 7 ? 16 : 8, bw = (w + 3) / 4, bh = (h + 3) / 4;
    if ((int64_t)bw * bh * taille > nsrc)
        return -1;
    uint8_t px[16][4];
    for (int by = 0; by < bh; by++)
        for (int bx = 0; bx < bw; bx++) {
            const uint8_t *s = src + ((int64_t)by * bw + bx) * taille;
            if (format == 7) bloc_bc7(s, px); else bloc_bc1(s, px);
            for (int i = 0; i < 16; i++) {
                int y = by * 4 + i / 4, x = bx * 4 + i % 4;
                if (y < h && x < w)
                    memcpy(rgba + ((int64_t)y * w + x) * 4, px[i], 4);
            }
        }
    return 0;
}

/* ------------------------------------------------------------------ ENCODAGE (même calcul que AtelierMaillots/lib) */
/* BC7 mode 6 de bustes.bc7_mode6 : extrémités = pixels de luminance min / max (1re occurrence), 7 bits + bit 0 */
static void enc_bc7_mode6(const uint8_t px[16][4], uint8_t *dst)
{
    int imin = 0, imax = 0, lmin = 0, lmax = 0;
    for (int i = 0; i < 16; i++) {
        int l = px[i][0] * 299 + px[i][1] * 587 + px[i][2] * 114 + px[i][3] * 50;
        if (i == 0 || l < lmin) { lmin = l; imin = i; }
        if (i == 0 || l > lmax) { lmax = l; imax = i; }
    }
    int q0[4], q1[4], pal[16][4], ind[16];
    for (int k = 0; k < 4; k++) {
        q0[k] = (px[imin][k] + 1) >> 1; if (q0[k] > 127) q0[k] = 127;
        q1[k] = (px[imax][k] + 1) >> 1; if (q1[k] > 127) q1[k] = 127;
    }
    for (int j = 0; j < 16; j++)
        for (int k = 0; k < 4; k++)
            pal[j][k] = ((q0[k] << 1) * (64 - W4[j]) + (q1[k] << 1) * W4[j] + 32) >> 6;
    for (int i = 0; i < 16; i++) {
        int best = 1 << 30, bi = 0;
        for (int j = 0; j < 16; j++) {
            int d0 = px[i][0] - pal[j][0], d1 = px[i][1] - pal[j][1], d2 = px[i][2] - pal[j][2], d3 = px[i][3] - pal[j][3];
            int d = d0 * d0 + d1 * d1 + d2 * d2 + d3 * d3;
            if (d < best) { best = d; bi = j; }
        }
        ind[i] = bi;
    }
    if (ind[0] >= 8) {
        for (int k = 0; k < 4; k++) { int t = q0[k]; q0[k] = q1[k]; q1[k] = t; }
        for (int i = 0; i < 16; i++) ind[i] = 15 - ind[i];
    }
    uint64_t b[2] = {0, 0};
    int n = 0;
#define METTRE(v, k) do { uint64_t _v = (uint64_t)(v) & ((1ull << (k)) - 1); int _k = (k); \
        for (int _i = 0; _i < _k; _i++, n++) if ((_v >> _i) & 1) b[n >> 6] |= 1ull << (n & 63); } while (0)
    METTRE(1 << 6, 7);
    for (int k = 0; k < 4; k++) { METTRE(q0[k], 7); METTRE(q1[k], 7); }
    METTRE(0, 1); METTRE(0, 1);
    METTRE(ind[0], 3);
    for (int i = 1; i < 16; i++) METTRE(ind[i], 4);
#undef METTRE
    memcpy(dst, b, 16);
}

static int vers565(int r, int g, int b)
{
    return ((r * 31 + 127) / 255) << 11 | ((g * 63 + 127) / 255) << 5 | ((b * 31 + 127) / 255);
}

/* BC1 de images.encoder_bc1_lignes : bloc uni, sinon extrémités = luminance max / min (1re occurrence) */
static void enc_bc1(const uint8_t px[16][4], uint8_t *dst)
{
    int uni = 1;
    for (int i = 1; i < 16; i++)
        if (px[i][0] != px[0][0] || px[i][1] != px[0][1] || px[i][2] != px[0][2]) { uni = 0; break; }
    uint16_t c0, c1; uint32_t idx = 0;
    if (uni) {
        c0 = c1 = (uint16_t)vers565(px[0][0], px[0][1], px[0][2]);
    } else {
        int imin = 0, imax = 0, lmin = 0, lmax = 0;
        for (int i = 0; i < 16; i++) {
            int l = px[i][0] * 299 + px[i][1] * 587 + px[i][2] * 114;
            if (i == 0 || l > lmax) { lmax = l; imax = i; }
            if (i == 0 || l < lmin) { lmin = l; imin = i; }
        }
        c0 = (uint16_t)vers565(px[imax][0], px[imax][1], px[imax][2]);
        c1 = (uint16_t)vers565(px[imin][0], px[imin][1], px[imin][2]);
        if (c0 != c1) {
            if (c0 < c1) { uint16_t t = c0; c0 = c1; c1 = t; }
            int a[3], bb[3], pal[4][3];
            c565(c0, a); c565(c1, bb);
            for (int k = 0; k < 3; k++) {
                pal[0][k] = a[k]; pal[1][k] = bb[k];
                pal[2][k] = (2 * a[k] + bb[k]) / 3; pal[3][k] = (a[k] + 2 * bb[k]) / 3;
            }
            for (int i = 0; i < 16; i++) {
                int best = 1 << 30, bi = 0;
                for (int j = 0; j < 4; j++) {
                    int d0 = px[i][0] - pal[j][0], d1 = px[i][1] - pal[j][1], d2 = px[i][2] - pal[j][2];
                    int d = d0 * d0 + d1 * d1 + d2 * d2;
                    if (d < best) { best = d; bi = j; }
                }
                idx |= (uint32_t)bi << (2 * i);
            }
        }
    }
    memcpy(dst, &c0, 2); memcpy(dst + 2, &c1, 2); memcpy(dst + 4, &idx, 4);
}

/* images.moitie : moyenne 2x2 arrondie, bords répétés */
static uint8_t *moitie(const uint8_t *src, int w, int h, int *nw_, int *nh_)
{
    int nw = w / 2 > 1 ? w / 2 : 1, nh = h / 2 > 1 ? h / 2 : 1;
    uint8_t *o = (uint8_t *)malloc((size_t)nw * nh * 4);
    if (!o) return NULL;
    for (int y = 0; y < nh; y++) {
        const uint8_t *r0 = src + (size_t)(2 * y < h - 1 ? 2 * y : h - 1) * w * 4;
        const uint8_t *r1 = src + (size_t)(2 * y + 1 < h - 1 ? 2 * y + 1 : h - 1) * w * 4;
        for (int x = 0; x < nw; x++) {
            int a = (2 * x < w - 1 ? 2 * x : w - 1) * 4, b = (2 * x + 1 < w - 1 ? 2 * x + 1 : w - 1) * 4;
            for (int k = 0; k < 4; k++)
                o[((size_t)y * nw + x) * 4 + k] = (uint8_t)((r0[a + k] + r0[b + k] + r1[a + k] + r1[b + k] + 2) >> 2);
        }
    }
    *nw_ = nw; *nh_ = nh;
    return o;
}

/* ---- BC7 « fin » de moteur/bc7_fin.py (portraits) : modes 6, 7 et 1 (64 découpages), le moins faux par bloc ---- */
typedef struct { int ns, cb, ab, pu, ib, mode; } ModeFin;          /* pu : bit P par extrémité (1) ou par groupe (0) */
static const ModeFin MF6 = {1, 7, 7, 1, 4, 6}, MF7 = {2, 5, 5, 1, 2, 7}, MF1 = {2, 6, 0, 0, 3, 1};

static void fin_axe(const double Y[16][4], int C, const int m[16], double e0[4], double e1[4])
{
    int n = 0;
    for (int k = 0; k < 16; k++) n += m[k];
    double nn = n > 0 ? n : 1, mu[4], D[16][4], cov[4][4], a[4], b[4];
    for (int c = 0; c < C; c++) {
        double s = 0;
        for (int k = 0; k < 16; k++) s += Y[k][c] * m[k];
        mu[c] = s / nn;
    }
    for (int k = 0; k < 16; k++)
        for (int c = 0; c < C; c++) D[k][c] = (Y[k][c] - mu[c]) * m[k];
    for (int i = 0; i < C; i++)
        for (int j = 0; j < C; j++) {
            double s = 0;
            for (int k = 0; k < 16; k++) s += D[k][i] * D[k][j];
            cov[i][j] = s;
        }
    for (int c = 0; c < C; c++) a[c] = 1.0 / sqrt((double)C);
    for (int it = 0; it < 6; it++) {
        double nr = 0;
        for (int i = 0; i < C; i++) {
            double s = 0;
            for (int j = 0; j < C; j++) s += cov[i][j] * a[j];
            b[i] = s;
        }
        for (int i = 0; i < C; i++) nr += b[i] * b[i];
        nr = sqrt(nr);
        if (nr < 1e-9) nr = 1e-9;
        for (int i = 0; i < C; i++) a[i] = b[i] / nr;
    }
    double lo = INFINITY, hi = -INFINITY;
    for (int k = 0; k < 16; k++) {
        if (!m[k]) continue;
        double s = 0;
        for (int c = 0; c < C; c++) s += (Y[k][c] - mu[c]) * a[c];
        if (s < lo) lo = s;
        if (s > hi) hi = s;
    }
    if (!isfinite(lo)) lo = 0;
    if (!isfinite(hi)) hi = 0;
    for (int c = 0; c < C; c++) {
        double v0 = mu[c] + a[c] * lo, v1 = mu[c] + a[c] * hi;
        e0[c] = v0 < 0 ? 0 : v0 > 255 ? 255 : v0;
        e1[c] = v1 < 0 ? 0 : v1 > 255 ? 255 : v1;
    }
}

static void fin_quant(const double e0[4], const double e1[4], int C, int cb, int pu, int q[2][4], int p[2], int r[2][4])
{
    int B = cb + 1, qq[2][2][4], rr[2][2][4];
    double err[2][2] = {{0, 0}, {0, 0}};
    const double *E[2] = {e0, e1};
    for (int pp = 0; pp < 2; pp++)
        for (int e = 0; e < 2; e++)
            for (int c = 0; c < C; c++) {
                double x = (E[e][c] * ((1 << B) - 1) / 255 - pp) / 2;
                double ro = nearbyint(x);                                     /* np.round : moitié vers le pair */
                int v = ro < 0 ? 0 : ro > (1 << cb) - 1 ? (1 << cb) - 1 : (int)ro;
                int z = ((v << 1) | pp) << (8 - B);
                z |= z >> B;
                qq[pp][e][c] = v; rr[pp][e][c] = z;
                err[pp][e] += (z - E[e][c]) * (z - E[e][c]);
            }
    if (pu) {
        for (int e = 0; e < 2; e++) {
            int ch = err[1][e] < err[0][e];
            p[e] = ch;
            for (int c = 0; c < C; c++) { q[e][c] = qq[ch][e][c]; r[e][c] = rr[ch][e][c]; }
        }
    } else {
        int ch = err[1][0] + err[1][1] < err[0][0] + err[0][1];
        p[0] = p[1] = ch;
        for (int e = 0; e < 2; e++)
            for (int c = 0; c < C; c++) { q[e][c] = qq[ch][e][c]; r[e][c] = rr[ch][e][c]; }
    }
}

typedef struct { double err; int pa; int Q[2][2][4]; int P[2][2]; int I[16]; } EssaiFin;

static void fin_essai(const uint8_t X[16][4], const ModeFin *M, EssaiFin *best)
{
    int C = M->ab ? 4 : 3, nI = 1 << M->ib, premier = 1;
    const uint8_t *w = poids(M->ib);
    double Y[16][4], pds[16][4];
    for (int k = 0; k < 16; k++)
        for (int c = 0; c < 4; c++) {
            Y[k][c] = X[k][c];
            pds[k][c] = (C == 4 && c < 3) ? (X[k][3] > 0) : 1;
        }
    for (int pa = 0; pa < (M->ns == 2 ? 64 : 1); pa++) {
        int sub[16];
        for (int k = 0; k < 16; k++) sub[k] = M->ns == 2 ? (P2[pa] >> k) & 1 : 0;
        EssaiFin cur;
        cur.err = 0; cur.pa = pa;
        for (int s = 0; s < M->ns; s++) {
            int m[16];
            double e0[4], e1[4];
            int q[2][4], p[2], r[2][4], pal[16][4];
            for (int k = 0; k < 16; k++) m[k] = sub[k] == s;
            fin_axe(Y, C, m, e0, e1);
            fin_quant(e0, e1, C, M->cb, M->pu, q, p, r);
            for (int j = 0; j < nI; j++)
                for (int c = 0; c < C; c++) pal[j][c] = ((64 - w[j]) * r[0][c] + w[j] * r[1][c] + 32) >> 6;
            for (int k = 0; k < 16; k++) {
                if (!m[k]) continue;
                double dm = 0; int bi = 0;
                for (int j = 0; j < nI; j++) {
                    double d = 0;
                    for (int c = 0; c < C; c++) { double t = Y[k][c] - pal[j][c]; d += t * t * pds[k][c]; }
                    if (j == 0 || d < dm) { dm = d; bi = j; }
                }
                cur.err += dm; cur.I[k] = bi;
            }
            for (int e = 0; e < 2; e++) {
                cur.P[s][e] = p[e];
                for (int c = 0; c < 4; c++) cur.Q[s][e][c] = c < C ? q[e][c] : 0;
            }
        }
        if (premier || cur.err < best->err) { *best = cur; premier = 0; }
    }
}

static void fin_ecrire(const ModeFin *M, EssaiFin *R, uint8_t *dst)
{
    int sub[16], anc[2] = {0, -1}, nanc = M->ns == 2 ? 2 : 1, haut = 1 << (M->ib - 1);
    for (int k = 0; k < 16; k++) sub[k] = M->ns == 2 ? (P2[R->pa] >> k) & 1 : 0;
    if (M->ns == 2) anc[1] = A2[R->pa];
    for (int s = 0; s < nanc; s++)
        if (R->I[anc[s]] & haut) {                  /* l'index d'ancre doit avoir son bit fort à 0 : extrémités échangées */
            for (int c = 0; c < 4; c++) { int t = R->Q[s][0][c]; R->Q[s][0][c] = R->Q[s][1][c]; R->Q[s][1][c] = t; }
            { int t = R->P[s][0]; R->P[s][0] = R->P[s][1]; R->P[s][1] = t; }
            for (int k = 0; k < 16; k++) if (sub[k] == s) R->I[k] = (1 << M->ib) - 1 - R->I[k];
        }
    uint64_t b[2] = {0, 0};
    int n = 0;
#define METTRE(v, k) do { uint64_t _v = (uint64_t)(v) & ((1ull << (k)) - 1); int _k = (k); \
        for (int _i = 0; _i < _k; _i++, n++) if ((_v >> _i) & 1) b[n >> 6] |= 1ull << (n & 63); } while (0)
    METTRE(1u << M->mode, M->mode + 1);
    if (M->ns == 2) METTRE(R->pa, 6);
    for (int c = 0; c < 3; c++)
        for (int s = 0; s < M->ns; s++)
            for (int e = 0; e < 2; e++) METTRE(R->Q[s][e][c], M->cb);
    if (M->ab)
        for (int s = 0; s < M->ns; s++)
            for (int e = 0; e < 2; e++) METTRE(R->Q[s][e][3], M->ab);
    if (M->pu) {
        for (int s = 0; s < M->ns; s++)
            for (int e = 0; e < 2; e++) METTRE(R->P[s][e], 1);
    } else {
        for (int s = 0; s < M->ns; s++) METTRE(R->P[s][0], 1);
    }
    for (int i = 0; i < 16; i++) {
        int a = (i == anc[0]) || (nanc == 2 && i == anc[1]);
        METTRE(R->I[i], a ? M->ib - 1 : M->ib);
    }
#undef METTRE
    memcpy(dst, b, 16);
}

static void enc_bc7_fin(const uint8_t px[16][4], uint8_t *dst)
{
    int opaque = 1;
    for (int k = 0; k < 16; k++) if (px[k][3] != 255) { opaque = 0; break; }
    EssaiFin r6, r7, r1;
    fin_essai(px, &MF6, &r6);
    fin_essai(px, &MF7, &r7);
    const ModeFin *M = &MF6; EssaiFin *R = &r6;
    if (r7.err < R->err) { M = &MF7; R = &r7; }
    if (opaque) { fin_essai(px, &MF1, &r1); if (r1.err < R->err) { M = &MF1; R = &r1; } }
    fin_ecrire(M, R, dst);
}

/* image RGBA w x h -> blocs BC7 (format 7, mode 6 ; format 17 : BC7 « fin ») ou BC1 (format 1) de `mips` niveaux, comme images.dds_bc7 /
 * images.dds_bc1 (BC1 : on s'arrête à 1 x 1). out == NULL : renvoie seulement la taille nécessaire ; < 0 : erreur. */
__declspec(dllexport) int64_t encoder_dds(const uint8_t *rgba, int w, int h, int mips, int format, uint8_t *out, int64_t nout)
{
    int taille = format == 1 ? 8 : 16;
    int64_t total = 0;
    { int lw = w, lh = h, n = 0;
      while (1) {
          total += (int64_t)((lw + 3) / 4) * ((lh + 3) / 4) * taille; n++;
          if (!(n < mips && (format != 1 || lw > 1 || lh > 1))) break;
          lw = lw / 2 > 1 ? lw / 2 : 1; lh = lh / 2 > 1 ? lh / 2 : 1;
      } }
    if (!out) return total;
    if (nout < total) return -1;
    const uint8_t *niv = rgba; uint8_t *libre = NULL;
    int lw = w, lh = h, n = 0; int64_t p = 0;
    uint8_t px[16][4];
    while (1) {
        for (int by = 0; by < lh; by += 4)
            for (int bx = 0; bx < lw; bx += 4) {
                for (int i = 0; i < 16; i++) {
                    int y = by + i / 4, x = bx + i % 4;
                    if (y > lh - 1) y = lh - 1;
                    if (x > lw - 1) x = lw - 1;
                    memcpy(px[i], niv + ((size_t)y * lw + x) * 4, 4);
                }
                if (format == 7) enc_bc7_mode6(px, out + p); else if (format == 17) enc_bc7_fin(px, out + p); else enc_bc1(px, out + p);
                p += taille;
            }
        n++;
        if (!(n < mips && (format != 1 || lw > 1 || lh > 1))) break;
        int nw, nh; uint8_t *s = moitie(niv, lw, lh, &nw, &nh);
        if (libre) free(libre);
        if (!s) return -2;
        niv = libre = s; lw = nw; lh = nh;
    }
    if (libre) free(libre);
    return p;
}

/* out doit faire au moins taille + 0x100 octets (taille = uint32 à src+8) ; renvoie 0 si tout va bien */
__declspec(dllexport) int crilayla(const uint8_t *src, int64_t nsrc, uint8_t *out, int64_t nout)
{
    if (nsrc < 16)
        return -1;
    uint32_t taille, eoff;
    memcpy(&taille, src + 8, 4);
    memcpy(&eoff, src + 12, 4);
    if (nout < (int64_t)taille + 0x100 || (int64_t)eoff + 0x110 > nsrc)
        return -1;
    memcpy(out, src + eoff + 0x10, 0x100);
    Flux f = {src, (int64_t)eoff + 0x10 - 1, 0, 0, 0};
    static const int T5[4] = {2, 3, 5, 8};
    int64_t ecrits = 0, fin = taille;
    while (ecrits < fin) {
        if (lire_bits(&f, 1)) {
            int64_t recul = (int64_t)lire_bits(&f, 13) + 3;
            int64_t lg = 3;
            for (int i = 0;; i++) {
                int n = T5[i < 3 ? i : 3];
                uint32_t v = lire_bits(&f, n);
                lg += v;
                if (f.erreur)
                    return -2;
                if (v != (1u << n) - 1)
                    break;
            }
            int64_t a = 0x100 + fin - 1 - ecrits;
            if (a + recul >= nout || a - lg + 1 < 0)
                return -3;
            for (int64_t j = 0; j < lg; j++, a--)
                out[a] = out[a + recul];
            ecrits += lg;
        } else {
            uint32_t v = lire_bits(&f, 8);
            out[0x100 + fin - 1 - ecrits] = (uint8_t)v;
            ecrits += 1;
        }
        if (f.erreur)
            return -2;
    }
    return 0;
}
