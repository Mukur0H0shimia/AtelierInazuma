"""Décodage BC6H (textures HDR du jeu : cubemaps des stades) PAR LA CARTE GRAPHIQUE (décodeur matériel Direct3D 11, donc
exact). Créé le 13/11/2026 pour le vrai shader du stade (map_pbrt1 : reflets et lumière diffuse prises dans la cubemap).

decoder(blocs, w, h, mips, signe) -> liste de niveaux [(w, h, flottants RGBA ligne par ligne)]
  blocs : données DDS d'UNE face (tous ses niveaux à la suite), w, h : taille du niveau 0, signe : BC6H_SF16 (96) sinon UF16 (95).
"""
import ctypes, struct
from ctypes import byref, c_void_p, c_uint, POINTER, cast
import d3d11 as D

_HLSL = """
Texture2D<float4> t0 : register(t0);
cbuffer CB0 : register(b0) { uint niveau; uint3 rien; };
float4 vs(uint id : SV_VertexID) : SV_Position { float2 p = float2((id << 1) & 2, id & 2); return float4(p * float2(2, -2) + float2(-1, 1), 0, 1); }
float4 ps(float4 pos : SV_Position) : SV_Target { return t0.Load(int3(int(pos.x), int(pos.y), int(niveau))); }
"""
_app = None


def _appareil():
    global _app
    if _app is None:
        d = D.Appareil()
        vs = d.shader('vs', D.compiler(_HLSL, 'vs', 'vs_5_0'))
        ps = d.shader('ps', D.compiler(_HLSL, 'ps', 'ps_5_0'))
        _app = (d, vs, ps, d.raster(), d.melange(D.BLEND_ONE, D.BLEND_ZERO, False), d.etat_profondeur(False, False))
    return _app


def _texture_bc(d, w, h, mips, fmt, donnees):
    desc = D.TEXTURE2D_DESC(w, h, mips, 1, fmt, 1, 0, D.USAGE_DEFAULT, D.BIND_SRV, 0, 0)
    init = (D.SUBRESOURCE_DATA * mips)()
    garde, o, lw, lh = [], 0, w, h
    for k in range(mips):
        bw, bh = max(1, (lw + 3) // 4), max(1, (lh + 3) // 4)
        t = bw * bh * 16
        buf = ctypes.create_string_buffer(bytes(donnees[o:o + t]), t); garde.append(buf)
        init[k] = D.SUBRESOURCE_DATA(cast(buf, c_void_p), bw * 16, 0)
        o += t; lw, lh = max(1, lw // 2), max(1, lh // 2)
    out = c_void_p()
    D._ok(D._meth(d.dev, 5, D.HRESULT, POINTER(D.TEXTURE2D_DESC), POINTER(D.SUBRESOURCE_DATA), POINTER(c_void_p))(
        d.dev, byref(desc), init, byref(out)), 'CreateTexture2D BC6H')
    return out, o


def _lire_rgba32f(d, tex, w, h):
    st = d.texture(w, h, D.RGBA32F, bind=0, usage=D.USAGE_STAGING, cpu=D.CPU_READ)
    d.copier(st, tex)
    m = D.MAPPED()
    D._ok(D._meth(d.ctx, 14, D.HRESULT, c_void_p, c_uint, c_uint, c_uint, POINTER(D.MAPPED))(d.ctx, st, 0, 1, 0, byref(m)), 'Map')
    data = b''.join(ctypes.string_at(m.pData + y * m.RowPitch, w * 16) for y in range(h))
    D._meth(d.ctx, 15, None, c_void_p, c_uint)(d.ctx, st, 0)
    D.liberer(st)
    return struct.unpack('<%df' % (w * h * 4), data)


def decoder(blocs, w, h, mips, signe=True):
    """-> ([(lw, lh, valeurs RGBA flottantes)], octets consommés)"""
    d, vs, ps, rs, bl, dp = _appareil()
    tex, lu = _texture_bc(d, w, h, mips, 96 if signe else 95, blocs)
    srv = d.image_shader(tex)
    out, lw, lh = [], w, h
    for k in range(mips):
        rt = d.texture(lw, lh, D.RGBA32F, bind=D.BIND_RTV)
        rtv = d.cible(rt)
        cb = d.tampon(struct.pack('<4I', k, 0, 0, 0), D.BIND_CB)
        d.sortie(rtv, None, lw, lh)
        d.etats(bl, dp, rs)
        d.shaders(vs, ps)
        d.cb('ps', 0, cb); d.srv('ps', 0, srv)
        d.dessiner_sans_sommets(3)
        out.append((lw, lh, _lire_rgba32f(d, rt, lw, lh)))
        d.vider_srv()
        for x in (rtv, rt, cb):
            D.liberer(x)
        lw, lh = max(1, lw // 2), max(1, lh // 2)
    D.liberer(srv); D.liberer(tex)
    return out, lu
