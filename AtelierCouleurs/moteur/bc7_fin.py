"""(16/11/2026) ENCODEUR BC7 PLUS FIN (numpy) pour les images très dessinées (portraits des copies).

Pourquoi : l'encodeur de l'Atelier Maillots (lib/bustes.encoder_bc7_bande) n'écrit que le mode 6 : UNE ligne de couleurs
par bloc de 4 x 4. Un bloc qui contient trois couleurs (sangle bleue, peau rouge, trait noir) prend alors des couleurs
intermédiaires sur la ligne -> « pixels bizarres un peu partout » sur le portrait recoloré (muku, en jeu).
Ici chaque bloc essaie aussi les modes à DEUX groupes (64 découpages du bloc) et garde le moins faux :
- mode 1 : 2 groupes, RVB 6 bits + bit P partagé par groupe, index 3 bits (blocs opaques) ;
- mode 7 : 2 groupes, RVBA 5 bits + bit P par extrémité, index 2 bits (blocs avec transparence) ;
- mode 6 : 1 groupe, RVBA 7 bits + bit P par extrémité, index 4 bits.
LU (format BC7, Microsoft / Khronos) ; mêmes tables que lib/bc7.py (décodeur de l'Atelier), vérifié en relisant les blocs
avec texture2ddecoder et lib/bc7.
"""
import numpy as np
from . import g4                                # noqa: F401 (met l'Atelier Maillots dans le chemin)
from lib import bc7 as _t                      # noqa: E402 (tables P2 / A2 / W de l'Atelier Maillots)

_W = {k: np.array(v, np.int32) for k, v in _t.W.items()}
_SUB2 = np.array([[(m >> i) & 1 for i in range(16)] for m in _t.P2], np.int8)      # (64, 16)
_ANC2 = np.array(_t.A2, np.int32)
# mode : (groupes, bits couleur, bits alpha, bits P : 'u' par extrémité / 's' par groupe, bits d'index)
_MODES = {1: (2, 6, 0, 's', 3), 7: (2, 5, 5, 'u', 2), 6: (1, 7, 7, 'u', 4)}


def _expand(v, n):
    v = v << (8 - n)
    return v | (v >> n)


def _axe(Y, m):
    """extrémités : moyenne ± axe principal (itération de puissance), bornées par les projections extrêmes"""
    n = np.maximum(m.sum(1, keepdims=True), 1)[..., None]                       # (N, 1, 1)
    mu = (Y * m[..., None]).sum(1, keepdims=True) / n
    D = (Y - mu) * m[..., None]
    cov = np.einsum('nki,nkj->nij', D, D)
    a = np.ones((Y.shape[0], Y.shape[2])) / np.sqrt(Y.shape[2])
    for _ in range(6):
        a = np.einsum('nij,nj->ni', cov, a)
        a /= np.maximum(np.linalg.norm(a, axis=1, keepdims=True), 1e-9)
    pr = np.einsum('nkc,nc->nk', Y - mu, a)
    lo = np.where(m, pr, np.inf).min(1); hi = np.where(m, pr, -np.inf).max(1)
    lo = np.where(np.isfinite(lo), lo, 0); hi = np.where(np.isfinite(hi), hi, 0)
    e0 = np.clip(mu[:, 0] + a * lo[:, None], 0, 255); e1 = np.clip(mu[:, 0] + a * hi[:, None], 0, 255)
    return e0, e1


def _quant(e0, e1, cb, pmode):
    """extrémités (N, C) -> (valeurs à cb bits (N, 2, C), bits P (N, 2), extrémités relues sur 8 bits (N, 2, C))"""
    B = cb + 1
    best = None
    E = np.stack([e0, e1], 1)                                                   # (N, 2, C)
    res = []
    for p in (0, 1):
        q = np.clip(np.round((E * ((1 << B) - 1) / 255 - p) / 2), 0, (1 << cb) - 1).astype(np.int32)
        r = _expand((q << 1) | p, B)
        res.append((q, r, ((r - E) ** 2).sum(2)))                               # erreur par extrémité (N, 2)
    if pmode == 'u':
        ch = res[1][2] < res[0][2]                                              # (N, 2)
        q = np.where(ch[..., None], res[1][0], res[0][0]); r = np.where(ch[..., None], res[1][1], res[0][1])
        return q, ch.astype(np.int32), r
    ch = res[1][2].sum(1) < res[0][2].sum(1)                                    # (N,) bit partagé
    q = np.where(ch[:, None, None], res[1][0], res[0][0]); r = np.where(ch[:, None, None], res[1][1], res[0][1])
    return q, np.repeat(ch[:, None], 2, 1).astype(np.int32), r


def _essai(X, mode):
    """X (N, 16, 4) -> erreur (N,) et de quoi écrire le bloc pour le meilleur découpage"""
    ns, cb, ab, pm, ib = _MODES[mode]
    C = 4 if ab else 3
    N = X.shape[0]
    Y = X[..., :C].astype(np.float64)
    pds = np.ones(Y.shape)                                                      # poids des canaux par pixel
    if C == 4:
        pds[..., :3] = (X[..., 3:4] > 0)                                        # couleur d'un pixel transparent : sans importance
    w = _W[ib]
    parts = range(64) if ns == 2 else [None]
    meil = None
    for pa in parts:
        sub = _SUB2[pa] if pa is not None else np.zeros(16, np.int8)
        err = np.zeros(N); Q = np.zeros((N, ns, 2, C), np.int32); P = np.zeros((N, ns, 2), np.int32)
        I = np.zeros((N, 16), np.int32)
        for s in range(ns):
            m = np.broadcast_to(sub == s, (N, 16))
            e0, e1 = _axe(Y, m)
            q, p, r = _quant(e0, e1, cb, pm)
            pal = ((64 - w)[None, :, None] * r[:, 0:1] + w[None, :, None] * r[:, 1:2] + 32) >> 6   # (N, nI, C)
            d = (((Y[:, :, None, :] - pal[:, None]) ** 2) * pds[:, :, None, :]).sum(3)
            idx = d.argmin(2); dm = d.min(2)
            sel = sub == s
            err += dm[:, sel].sum(1)
            Q[:, s] = q; P[:, s] = p; I[:, sel] = idx[:, sel]
        if meil is None:
            meil = [err, np.zeros(N, np.int32) + (pa or 0), Q, P, I]
        else:
            b = err < meil[0]
            meil[0] = np.where(b, err, meil[0]); meil[1] = np.where(b, pa, meil[1])
            for k, v in ((2, Q), (3, P), (4, I)):
                meil[k] = np.where(b.reshape((N,) + (1,) * (v.ndim - 1)), v, meil[k])
    return meil


def _ecrire(mode, pa, Q, P, I):
    """un bloc -> 16 octets"""
    ns, cb, ab, pm, ib = _MODES[mode]
    Q = Q.copy(); P = P.copy(); I = I.copy()
    sub = _SUB2[pa] if ns == 2 else np.zeros(16, np.int8)
    anc = [0] + ([int(_ANC2[pa])] if ns == 2 else [])
    hautbit = 1 << (ib - 1)
    for s, a in enumerate(anc):                     # l'index d'ancre doit avoir son bit fort à 0 : sinon extrémités échangées
        if I[a] & hautbit:
            Q[s] = Q[s][::-1].copy(); P[s] = P[s][::-1].copy()
            sel = sub == s
            I[sel] = (1 << ib) - 1 - I[sel]
    x, pos = 1 << mode, mode + 1
    def ec(v, n):
        nonlocal x, pos
        x |= (int(v) & ((1 << n) - 1)) << pos; pos += n
    if ns == 2:
        ec(pa, 6)
    for c in range(3):
        for s in range(ns):
            for e in range(2):
                ec(Q[s, e, c], cb)
    if ab:
        for s in range(ns):
            for e in range(2):
                ec(Q[s, e, 3], ab)
    if pm == 'u':
        for s in range(ns):
            for e in range(2):
                ec(P[s, e], 1)
    else:
        for s in range(ns):
            ec(P[s, 0], 1)
    for i in range(16):
        ec(I[i], ib - 1 if i in anc else ib)
    assert pos == 128, (mode, pos)
    return x.to_bytes(16, 'little')


def encoder(w, h, rows):
    """image RGBA (rangées) -> blocs BC7 (octets), de gauche à droite puis de haut en bas"""
    a = np.frombuffer(b''.join(bytes(r) for r in rows), np.uint8)[:w * h * 4].reshape(h, w, 4)
    H4, W4 = (h + 3) // 4 * 4, (w + 3) // 4 * 4
    a = np.pad(a, ((0, H4 - h), (0, W4 - w), (0, 0)), mode='edge')
    X = a.reshape(H4 // 4, 4, W4 // 4, 4, 4).transpose(0, 2, 1, 3, 4).reshape(-1, 16, 4).astype(np.int32)
    out = []
    for d in range(0, len(X), 512):
        Xc = X[d:d + 512]
        opaque = (Xc[..., 3] == 255).all(1)
        r6 = _essai(Xc, 6)
        r7 = _essai(Xc, 7)
        r1 = _essai(Xc, 1)
        e1 = np.where(opaque, r1[0], np.inf)
        choix = np.argmin(np.stack([r6[0], r7[0], e1], 1), 1)
        for n in range(len(Xc)):
            mode, r = [(6, r6), (7, r7), (1, r1)][choix[n]]
            out.append(_ecrire(mode, int(r[1][n]), r[2][n], r[3][n], r[4][n]))
    return b''.join(out)


def dds_bc7(w, h, rows, entete, mips):
    """comme lib.images.dds_bc7 (en-tête DX10 d'une texture du jeu de même taille, `mips` niveaux), encodage plus fin"""
    from lib import images
    rapide = images.encoder_rapide(w, h, rows, mips, 17)   # (21/11) paquets.dll : même méthode en C (~25 fois plus vite)
    if rapide is not None:
        return bytes(entete) + rapide
    niveaux = [(w, h, rows)]
    while len(niveaux) < mips:
        niveaux.append(images.moitie(*niveaux[-1]))
    return bytes(entete) + b''.join(encoder(*n) for n in niveaux)
