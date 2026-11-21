/* Lecture des paquets du jeu, partie rapide (même calcul que moteur/paquets_jeu.py, en C) :
 *   xor_cpk   : XOR des .cpk (clé = crc32 du nom de l'archive, dépend de la position dans le fichier) ;
 *   crilayla  : décompression CRILAYLA (format public de CRI).
 * Compilé par compiler.bat en paquets.dll ; si la DLL manque, paquets_jeu.py fait le même calcul en Python.
 * Fast part of the pack reader (XOR + CRILAYLA), same results as the Python code. */
#include <stdint.h>
#include <string.h>

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
