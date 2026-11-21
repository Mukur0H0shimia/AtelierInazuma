"""Direct3D 11 depuis Python (ctypes), sans fenêtre : de quoi dessiner avec les VRAIS shaders du jeu (DXBC).

Prototype (13/11/2026). Seules les fonctions utiles sont exposées. Numéros des méthodes = ordre des tables de
d3d11.h (ID3D11Device, ID3D11DeviceContext).
"""
import ctypes
from ctypes import (POINTER, Structure, byref, c_char_p, c_float, c_int, c_size_t, c_ubyte, c_uint, c_void_p,
                    WINFUNCTYPE, cast)

HRESULT = c_int
_d3d = ctypes.WinDLL('d3d11.dll')
_comp = ctypes.WinDLL('d3dcompiler_47.dll')


_STABLES = set()          # adresses de l'appareil et du contexte : leurs méthodes sont gardées (14/11/2026, vitesse)
_cache_meth = {}


def _meth(obj, idx, restype, *argtypes):
    v = obj.value if isinstance(obj, c_void_p) else obj
    if v in _STABLES:
        k = (v, idx, restype, argtypes)
        f = _cache_meth.get(k)
        if f is None:
            vt = cast(obj, POINTER(POINTER(c_void_p)))[0]
            f = _cache_meth[k] = WINFUNCTYPE(restype, c_void_p, *argtypes)(vt[idx])
        return f
    vt = cast(obj, POINTER(POINTER(c_void_p)))[0]
    return WINFUNCTYPE(restype, c_void_p, *argtypes)(vt[idx])


def _ok(hr, quoi):
    if hr < 0:
        raise OSError('%s : échec 0x%08x' % (quoi, hr & 0xFFFFFFFF))


def liberer(obj):
    if obj:
        _meth(obj, 2, c_uint)(obj)


# ------------------------------------------------------------------ structures
class BUFFER_DESC(Structure):
    _fields_ = [('ByteWidth', c_uint), ('Usage', c_uint), ('BindFlags', c_uint), ('CPUAccessFlags', c_uint),
                ('MiscFlags', c_uint), ('StructureByteStride', c_uint)]


class SUBRESOURCE_DATA(Structure):
    _fields_ = [('pSysMem', c_void_p), ('SysMemPitch', c_uint), ('SysMemSlicePitch', c_uint)]


class TEXTURE2D_DESC(Structure):
    _fields_ = [('Width', c_uint), ('Height', c_uint), ('MipLevels', c_uint), ('ArraySize', c_uint), ('Format', c_uint),
                ('SampleCount', c_uint), ('SampleQuality', c_uint), ('Usage', c_uint), ('BindFlags', c_uint),
                ('CPUAccessFlags', c_uint), ('MiscFlags', c_uint)]


class INPUT_ELEMENT_DESC(Structure):
    _fields_ = [('SemanticName', c_char_p), ('SemanticIndex', c_uint), ('Format', c_uint), ('InputSlot', c_uint),
                ('AlignedByteOffset', c_uint), ('InputSlotClass', c_uint), ('InstanceDataStepRate', c_uint)]


class SAMPLER_DESC(Structure):
    _fields_ = [('Filter', c_uint), ('AddressU', c_uint), ('AddressV', c_uint), ('AddressW', c_uint),
                ('MipLODBias', c_float), ('MaxAnisotropy', c_uint), ('ComparisonFunc', c_uint),
                ('BorderColor', c_float * 4), ('MinLOD', c_float), ('MaxLOD', c_float)]


class RT_BLEND_DESC(Structure):
    _fields_ = [('BlendEnable', c_int), ('SrcBlend', c_uint), ('DestBlend', c_uint), ('BlendOp', c_uint),
                ('SrcBlendAlpha', c_uint), ('DestBlendAlpha', c_uint), ('BlendOpAlpha', c_uint), ('WriteMask', c_ubyte)]


class BLEND_DESC(Structure):
    _fields_ = [('AlphaToCoverageEnable', c_int), ('IndependentBlendEnable', c_int), ('RenderTarget', RT_BLEND_DESC * 8)]


class STENCILOP_DESC(Structure):
    _fields_ = [('Fail', c_uint), ('DepthFail', c_uint), ('Pass', c_uint), ('Func', c_uint)]


class DEPTH_STENCIL_DESC(Structure):
    _fields_ = [('DepthEnable', c_int), ('DepthWriteMask', c_uint), ('DepthFunc', c_uint), ('StencilEnable', c_int),
                ('StencilReadMask', c_ubyte), ('StencilWriteMask', c_ubyte), ('FrontFace', STENCILOP_DESC),
                ('BackFace', STENCILOP_DESC)]


class RASTERIZER_DESC(Structure):
    _fields_ = [('FillMode', c_uint), ('CullMode', c_uint), ('FrontCounterClockwise', c_int), ('DepthBias', c_int),
                ('DepthBiasClamp', c_float), ('SlopeScaledDepthBias', c_float), ('DepthClipEnable', c_int),
                ('ScissorEnable', c_int), ('MultisampleEnable', c_int), ('AntialiasedLineEnable', c_int)]


class VIEWPORT(Structure):
    _fields_ = [('TopLeftX', c_float), ('TopLeftY', c_float), ('Width', c_float), ('Height', c_float),
                ('MinDepth', c_float), ('MaxDepth', c_float)]


class MAPPED(Structure):
    _fields_ = [('pData', c_void_p), ('RowPitch', c_uint), ('DepthPitch', c_uint)]


# formats / constantes
RGBA8 = 28; R32F = 41; D32F = 40; RG32F = 16; RGB32F = 6; RGBA32F = 2; RGBA16F = 10
BIND_VB, BIND_IB, BIND_CB, BIND_SRV, BIND_RTV, BIND_DSV = 1, 2, 4, 8, 32, 64
USAGE_DEFAULT, USAGE_DYNAMIC, USAGE_STAGING = 0, 2, 3
CPU_WRITE, CPU_READ = 0x10000, 0x20000
MISC_GENERATE_MIPS = 1
# adressage Direct3D 11 : 1 répété, 2 miroir, 3 bloqué au bord, 4 bordure, 5 miroir une fois
BLEND_ZERO, BLEND_ONE, BLEND_SRC_ALPHA, BLEND_INV_SRC_ALPHA = 1, 2, 5, 6
BLEND_SRC_COLOR, BLEND_DEST_COLOR = 3, 9


class Appareil:
    def __init__(self):
        dev, ctx, niv = c_void_p(), c_void_p(), c_uint()
        niveaux = (c_uint * 1)(0xb000)
        _ok(_d3d.D3D11CreateDevice(None, 1, None, 0, niveaux, 1, 7, byref(dev), byref(niv), byref(ctx)), 'D3D11CreateDevice')
        self.dev, self.ctx = dev, ctx
        _STABLES.add(dev.value); _STABLES.add(ctx.value)
        self._garde = []          # tampons Python à garder en vie
        self._lie = {}            # ce qui est déjà lié (textures, échantillonneurs, tampons, shaders, états) : appels sautés

    # ---------------------------------------------------------- création
    def tampon(self, donnees, bind, dynamique=False, taille=None, structure=0):
        # TAMPONS DE CONSTANTES (14/11/2026, vitesse) : jamais modifiés sur place -> un seul tampon par contenu, gardé
        # (avant : ~12 000 créés par image et jamais libérés). Au-delà de 8 000, les plus anciens sont libérés.
        if bind == BIND_CB and not dynamique and donnees is not None and taille is None and not structure:
            cle = bytes(donnees)
            c = self.__dict__.setdefault('_cb_cache', {})
            b = c.pop(cle, None)
            if b is None:
                b = self._tampon(cle, bind)
                if len(c) >= 8000:
                    for k in list(c)[:2000]:
                        v = c.pop(k)
                        if v.value not in self._lie.values():
                            liberer(v)
            c[cle] = b                                   # (remis à la fin : ordre = du plus ancien au plus récent)
            return b
        return self._tampon(donnees, bind, dynamique, taille, structure)

    def _tampon(self, donnees, bind, dynamique=False, taille=None, structure=0):
        n = taille if taille is not None else len(donnees)
        n = (n + 15) // 16 * 16 if bind == BIND_CB else n
        d = BUFFER_DESC(n, USAGE_DYNAMIC if dynamique else USAGE_DEFAULT, bind, CPU_WRITE if dynamique else 0,
                        0x40 if structure else 0, structure)     # 0x40 = tampon structuré (StructuredBuffer)
        out = c_void_p()
        if donnees is not None:
            buf = ctypes.create_string_buffer(bytes(donnees) + b'\0' * (n - len(donnees)), n)
            init = SUBRESOURCE_DATA(cast(buf, c_void_p), 0, 0)
            _ok(_meth(self.dev, 3, HRESULT, POINTER(BUFFER_DESC), POINTER(SUBRESOURCE_DATA), POINTER(c_void_p))(
                self.dev, byref(d), byref(init), byref(out)), 'CreateBuffer')
        else:
            _ok(_meth(self.dev, 3, HRESULT, POINTER(BUFFER_DESC), c_void_p, POINTER(c_void_p))(
                self.dev, byref(d), None, byref(out)), 'CreateBuffer')
        return out

    def cube_bc(self, w, h, mips, fmt, octets):
        """cubemap compressée (BC6H : fmt 95 / 96) telle que dans le DDS : 6 faces, chacune avec tous ses niveaux.
        -> vue TextureCubeArray (1 cube), comme t14 « in_texCubeAry » des shaders du jeu"""
        n = 6 * mips
        init = (SUBRESOURCE_DATA * n)()
        garde = ctypes.create_string_buffer(bytes(octets), len(octets))
        o = 0
        for face in range(6):
            lw, lh = w, h
            for k in range(mips):
                bw, bh = max(1, (lw + 3) // 4), max(1, (lh + 3) // 4)
                init[face * mips + k] = SUBRESOURCE_DATA(ctypes.addressof(garde) + o, bw * 16, bw * bh * 16)
                o += bw * bh * 16
                lw, lh = max(1, lw // 2), max(1, lh // 2)
        d = TEXTURE2D_DESC(w, h, mips, 6, fmt, 1, 0, USAGE_DEFAULT, BIND_SRV, 0, 0x4)     # 0x4 = TEXTURECUBE
        tex = c_void_p()
        _ok(_meth(self.dev, 5, HRESULT, POINTER(TEXTURE2D_DESC), POINTER(SUBRESOURCE_DATA), POINTER(c_void_p))(
            self.dev, byref(d), init, byref(tex)), 'CreateTexture2D (cube)')
        sd = (c_uint * 6)(fmt, 10, 0, mips, 0, 1)          # TEXTURECUBEARRAY : niveau 0, mips, 1re face 0, 1 cube
        srv = c_void_p()
        _ok(_meth(self.dev, 7, HRESULT, c_void_p, c_void_p, POINTER(c_void_p))(self.dev, tex, cast(sd, c_void_p), byref(srv)), 'CreateSRV (cube)')
        self._garde += [sd, tex]
        return srv, o

    def tampon_brut(self, donnees):
        """ByteAddressBuffer (lecture ld_raw) : tampon « raw » + vue BUFFEREX R32 sans type"""
        n = (len(donnees) + 3) // 4 * 4
        d = BUFFER_DESC(n, USAGE_DEFAULT, BIND_SRV, 0, 0x20, 0)     # 0x20 = vues « raw » permises
        buf = ctypes.create_string_buffer(bytes(donnees) + b'\0' * (n - len(donnees)), n)
        init = SUBRESOURCE_DATA(cast(buf, c_void_p), 0, 0)
        out = c_void_p()
        _ok(_meth(self.dev, 3, HRESULT, POINTER(BUFFER_DESC), POINTER(SUBRESOURCE_DATA), POINTER(c_void_p))(
            self.dev, byref(d), byref(init), byref(out)), 'CreateBuffer (raw)')
        sd = (c_uint * 6)(39, 11, 0, n // 4, 1, 0)
        srv = c_void_p()
        _ok(_meth(self.dev, 7, HRESULT, c_void_p, c_void_p, POINTER(c_void_p))(self.dev, out, cast(sd, c_void_p), byref(srv)), 'CreateSRV (raw)')
        self._garde += [sd, out]
        return srv

    def texture(self, w, h, fmt=RGBA8, donnees=None, pas=None, bind=BIND_SRV, mips=1, misc=0, usage=USAGE_DEFAULT, cpu=0):
        d = TEXTURE2D_DESC(w, h, mips, 1, fmt, 1, 0, usage, bind, cpu, misc)
        out = c_void_p()
        if donnees is not None and mips == 1:
            buf = ctypes.create_string_buffer(bytes(donnees), len(donnees))
            init = SUBRESOURCE_DATA(cast(buf, c_void_p), pas, 0)
            _ok(_meth(self.dev, 5, HRESULT, POINTER(TEXTURE2D_DESC), POINTER(SUBRESOURCE_DATA), POINTER(c_void_p))(
                self.dev, byref(d), byref(init), byref(out)), 'CreateTexture2D')
        else:
            _ok(_meth(self.dev, 5, HRESULT, POINTER(TEXTURE2D_DESC), c_void_p, POINTER(c_void_p))(
                self.dev, byref(d), None, byref(out)), 'CreateTexture2D')
            if donnees is not None:
                buf = ctypes.create_string_buffer(bytes(donnees), len(donnees))
                _meth(self.ctx, 48, None, c_void_p, c_uint, c_void_p, c_void_p, c_uint, c_uint)(
                    self.ctx, out, 0, None, cast(buf, c_void_p), pas, 0)
        return out

    def profondeur_tableau(self, w, h, n):
        """tableau de n tampons de profondeur LISIBLES (R32 sans type) : n vues de profondeur (une par tranche, D32_FLOAT)
        et une vue de shader Texture2DArray (R32_FLOAT) — comme les cartes d'ombre en cascade du jeu"""
        d = TEXTURE2D_DESC(w, h, 1, n, 39, 1, 0, USAGE_DEFAULT, BIND_DSV | BIND_SRV, 0, 0)
        tex = c_void_p()
        _ok(_meth(self.dev, 5, HRESULT, POINTER(TEXTURE2D_DESC), c_void_p, POINTER(c_void_p))(self.dev, byref(d), None, byref(tex)), 'CreateTexture2D (tableau)')
        dsvs = []
        for i in range(n):
            vd = (c_uint * 6)(40, 4, 0, 0, i, 1)          # D32_FLOAT, TEXTURE2DARRAY, drapeaux, mip, 1re tranche, nombre
            out = c_void_p()
            _ok(_meth(self.dev, 10, HRESULT, c_void_p, c_void_p, POINTER(c_void_p))(self.dev, tex, cast(vd, c_void_p), byref(out)), 'CreateDSV (tranche)')
            dsvs.append(out); self._garde.append(vd)
        sd = (c_uint * 6)(41, 5, 0, 1, 0, n)               # R32_FLOAT, TEXTURE2DARRAY, mip 0, 1 mip, 1re tranche 0, n
        srv = c_void_p()
        _ok(_meth(self.dev, 7, HRESULT, c_void_p, c_void_p, POINTER(c_void_p))(self.dev, tex, cast(sd, c_void_p), byref(srv)), 'CreateSRV (tableau)')
        self._garde.append(sd)
        return tex, dsvs, srv

    def profondeur_lisible(self, w, h):
        """tampon de profondeur que les shaders peuvent aussi lire (R32 sans type : vue D32_FLOAT + vue R32_FLOAT)"""
        d = TEXTURE2D_DESC(w, h, 1, 1, 39, 1, 0, USAGE_DEFAULT, BIND_DSV | BIND_SRV, 0, 0)
        tex = c_void_p()
        _ok(_meth(self.dev, 5, HRESULT, POINTER(TEXTURE2D_DESC), c_void_p, POINTER(c_void_p))(self.dev, byref(d), None, byref(tex)), 'CreateTexture2D (profondeur)')
        vd = (c_uint * 4)(40, 3, 0, 0)
        dsv = c_void_p()
        _ok(_meth(self.dev, 10, HRESULT, c_void_p, c_void_p, POINTER(c_void_p))(self.dev, tex, cast(vd, c_void_p), byref(dsv)), 'CreateDSV')
        self._garde.append(vd)
        return tex, dsv, self.vue_r32(tex)

    def copie_r32(self, w, h):
        """texture R32 sans type (copie d'un tampon de profondeur) + vue R32_FLOAT"""
        d = TEXTURE2D_DESC(w, h, 1, 1, 39, 1, 0, USAGE_DEFAULT, BIND_SRV, 0, 0)
        tex = c_void_p()
        _ok(_meth(self.dev, 5, HRESULT, POINTER(TEXTURE2D_DESC), c_void_p, POINTER(c_void_p))(self.dev, byref(d), None, byref(tex)), 'CreateTexture2D (copie)')
        return tex, self.vue_r32(tex)

    def vue_r32(self, tex):
        sd = (c_uint * 6)(41, 4, 0, 1, 0, 0)
        srv = c_void_p()
        _ok(_meth(self.dev, 7, HRESULT, c_void_p, c_void_p, POINTER(c_void_p))(self.dev, tex, cast(sd, c_void_p), byref(srv)), 'CreateSRV (R32)')
        self._garde.append(sd)
        return srv

    def image_shader(self, tex):
        out = c_void_p()
        _ok(_meth(self.dev, 7, HRESULT, c_void_p, c_void_p, POINTER(c_void_p))(self.dev, tex, None, byref(out)), 'CreateSRV')
        return out

    def cible(self, tex):
        out = c_void_p()
        _ok(_meth(self.dev, 9, HRESULT, c_void_p, c_void_p, POINTER(c_void_p))(self.dev, tex, None, byref(out)), 'CreateRTV')
        return out

    def profondeur(self, tex):
        out = c_void_p()
        _ok(_meth(self.dev, 10, HRESULT, c_void_p, c_void_p, POINTER(c_void_p))(self.dev, tex, None, byref(out)), 'CreateDSV')
        return out

    def disposition(self, elements, vs_code):
        arr = (INPUT_ELEMENT_DESC * len(elements))(*[INPUT_ELEMENT_DESC(n.encode(), i, f, s, 0, 0, 0) for n, i, f, s in elements])
        self._garde.append(arr)
        out = c_void_p()
        _ok(_meth(self.dev, 11, HRESULT, POINTER(INPUT_ELEMENT_DESC), c_uint, c_char_p, c_size_t, POINTER(c_void_p))(
            self.dev, arr, len(elements), vs_code, len(vs_code), byref(out)), 'CreateInputLayout')
        return out

    def shader(self, genre, code):
        idx = {'vs': 12, 'gs': 13, 'ps': 15}[genre]
        out = c_void_p()
        _ok(_meth(self.dev, idx, HRESULT, c_char_p, c_size_t, c_void_p, POINTER(c_void_p))(
            self.dev, code, len(code), None, byref(out)), 'Create%s' % genre)
        return out

    def melange(self, src, dst, actif=True, src_a=None, dst_a=None, masque=0x0F, op=1):
        d = BLEND_DESC()
        rt = d.RenderTarget[0]
        rt.BlendEnable, rt.SrcBlend, rt.DestBlend, rt.BlendOp = int(actif), src, dst, op       # op : 1 ajout, 3 soustraction inversée
        rt.SrcBlendAlpha, rt.DestBlendAlpha, rt.BlendOpAlpha = (src_a or BLEND_ONE), (dst_a or BLEND_INV_SRC_ALPHA), 1
        rt.WriteMask = masque
        out = c_void_p()
        _ok(_meth(self.dev, 20, HRESULT, POINTER(BLEND_DESC), POINTER(c_void_p))(self.dev, byref(d), byref(out)), 'CreateBlendState')
        return out

    def etat_profondeur(self, test, ecrire, fonction=4):
        op = STENCILOP_DESC(1, 1, 1, 8)
        d = DEPTH_STENCIL_DESC(int(test), int(ecrire), fonction, 0, 0xFF, 0xFF, op, op)   # 4 = LESS_EQUAL, 8 = ALWAYS
        out = c_void_p()
        _ok(_meth(self.dev, 21, HRESULT, POINTER(DEPTH_STENCIL_DESC), POINTER(c_void_p))(self.dev, byref(d), byref(out)), 'CreateDepthStencilState')
        return out

    def raster(self, cull=1, ccw=0):
        """cull : 1 aucune, 2 faces avant, 3 faces arrière ; ccw : 1 = faces avant dans le sens inverse des aiguilles"""
        d = RASTERIZER_DESC(3, cull, ccw, 0, 0.0, 0.0, 1, 0, 0, 0)        # plein
        out = c_void_p()
        _ok(_meth(self.dev, 22, HRESULT, POINTER(RASTERIZER_DESC), POINTER(c_void_p))(self.dev, byref(d), byref(out)), 'CreateRasterizerState')
        return out

    def echantillonneur(self, u, v, w=1, filtre=0x15, comparaison=8, bord=(0, 0, 0, 0)):
        d = SAMPLER_DESC(filtre, u, v, w, 0.0, 1, comparaison, (c_float * 4)(*bord), 0.0, 3.4e38)
        out = c_void_p()
        _ok(_meth(self.dev, 23, HRESULT, POINTER(SAMPLER_DESC), POINTER(c_void_p))(self.dev, byref(d), byref(out)), 'CreateSamplerState')
        return out

    # ---------------------------------------------------------- contexte
    def maj_tampon(self, buf, donnees):
        m = MAPPED()
        _ok(_meth(self.ctx, 14, HRESULT, c_void_p, c_uint, c_uint, c_uint, POINTER(MAPPED))(self.ctx, buf, 0, 4, 0, byref(m)), 'Map')
        ctypes.memmove(m.pData, bytes(donnees), len(donnees))
        _meth(self.ctx, 15, None, c_void_p, c_uint)(self.ctx, buf, 0)

    def _tab(self, objs):
        return (c_void_p * len(objs))(*[o.value if isinstance(o, c_void_p) else o for o in objs])

    @staticmethod
    def _v(o):
        return o.value if isinstance(o, c_void_p) else o

    def _lier(self, cle, idx, slot, obj):
        """liaison d'une case ; sautée si la même chose y est déjà (gain de temps : ~5 000 dessins par image)"""
        v = self._v(obj)
        if self._lie.get(cle, -1) == v:
            return
        self._lie[cle] = v
        _meth(self.ctx, idx, None, c_uint, c_uint, c_void_p)(self.ctx, slot, 1, (c_void_p * 1)(v))

    def cb(self, etape, slot, buf):
        self._lier(('cb', etape, slot), {'vs': 7, 'ps': 16, 'gs': 22}[etape], slot, buf)

    def srv(self, etape, slot, vue):
        self._lier(('srv', etape, slot), {'vs': 25, 'ps': 8, 'gs': 31}[etape], slot, vue)

    def ech(self, etape, slot, s):
        self._lier(('ech', etape, slot), {'vs': 26, 'ps': 10, 'gs': 32}[etape], slot, s)

    def _oublier_srv(self):
        """une image liée en sortie est retirée des entrées par Direct3D : on oublie ce qu'on croyait lié"""
        for k in [k for k in self._lie if k[0] == 'srv']:
            del self._lie[k]

    def shaders(self, vs, ps, gs=None):
        k = (self._v(vs), self._v(ps), self._v(gs))
        if self._lie.get('shaders') == k:
            return
        self._lie['shaders'] = k
        _meth(self.ctx, 11, None, c_void_p, c_void_p, c_uint)(self.ctx, vs, None, 0)
        _meth(self.ctx, 9, None, c_void_p, c_void_p, c_uint)(self.ctx, ps, None, 0)
        _meth(self.ctx, 23, None, c_void_p, c_void_p, c_uint)(self.ctx, gs, None, 0)

    def sommets(self, disposition, tampons, pas, ib):
        _meth(self.ctx, 17, None, c_void_p)(self.ctx, disposition)
        n = len(tampons)
        _meth(self.ctx, 18, None, c_uint, c_uint, c_void_p, c_void_p, c_void_p)(
            self.ctx, 0, n, self._tab(tampons), (c_uint * n)(*pas), (c_uint * n)(*([0] * n)))
        _meth(self.ctx, 19, None, c_void_p, c_uint, c_uint)(self.ctx, ib, 57, 0)     # R16_UINT
        _meth(self.ctx, 24, None, c_uint)(self.ctx, 4)                               # liste de triangles

    def dessiner_sans_sommets(self, n):
        _meth(self.ctx, 17, None, c_void_p)(self.ctx, None)
        _meth(self.ctx, 24, None, c_uint)(self.ctx, 4)
        _meth(self.ctx, 13, None, c_uint, c_uint)(self.ctx, n, 0)

    def dessiner(self, n):
        _meth(self.ctx, 12, None, c_uint, c_uint, c_int)(self.ctx, n, 0, 0)

    def sortie(self, rtv, dsv, w, h):
        """cible(s) de rendu : une vue, ou une liste (plusieurs images écrites par le même PS, comme les shaders chr_toon du jeu)"""
        L = list(rtv) if isinstance(rtv, (list, tuple)) else [rtv]
        self._oublier_srv()
        _meth(self.ctx, 33, None, c_uint, c_void_p, c_void_p)(self.ctx, len(L), self._tab(L), dsv)
        vp = VIEWPORT(0, 0, w, h, 0, 1)
        _meth(self.ctx, 44, None, c_uint, POINTER(VIEWPORT))(self.ctx, 1, byref(vp))

    def etats(self, melange, prof, raster):
        k = (self._v(melange), self._v(prof), self._v(raster))
        if self._lie.get('etats') == k:
            return
        self._lie['etats'] = k
        _meth(self.ctx, 35, None, c_void_p, POINTER(c_float * 4), c_uint)(self.ctx, melange, byref((c_float * 4)(0, 0, 0, 0)), 0xFFFFFFFF)
        _meth(self.ctx, 36, None, c_void_p, c_uint)(self.ctx, prof, 0)
        _meth(self.ctx, 43, None, c_void_p)(self.ctx, raster)

    def effacer(self, rtv, dsv, couleur=(0, 0, 0, 0)):
        _meth(self.ctx, 50, None, c_void_p, POINTER(c_float * 4))(self.ctx, rtv, byref((c_float * 4)(*couleur)))
        _meth(self.ctx, 53, None, c_void_p, c_uint, c_float, c_ubyte)(self.ctx, dsv, 1, 1.0, 0)

    def copier(self, dst, src):
        _meth(self.ctx, 47, None, c_void_p, c_void_p)(self.ctx, dst, src)

    def mips(self, srv):
        _meth(self.ctx, 54, None, c_void_p)(self.ctx, srv)

    def lire_float(self, tex):
        """un seul texel R32F -> flottant"""
        st = self.texture(1, 1, R32F, bind=0, usage=USAGE_STAGING, cpu=CPU_READ)
        self.copier(st, tex)
        m = MAPPED()
        _ok(_meth(self.ctx, 14, HRESULT, c_void_p, c_uint, c_uint, c_uint, POINTER(MAPPED))(self.ctx, st, 0, 1, 0, byref(m)), 'Map lecture')
        v = ctypes.c_float.from_address(m.pData).value
        _meth(self.ctx, 15, None, c_void_p, c_uint)(self.ctx, st, 0)
        liberer(st)
        return v

    def maj(self, res, donnees, pas=0):
        buf = ctypes.create_string_buffer(bytes(donnees), len(donnees))
        _meth(self.ctx, 48, None, c_void_p, c_uint, c_void_p, c_void_p, c_uint, c_uint)(self.ctx, res, 0, None, cast(buf, c_void_p), pas, 0)

    def vider_srv(self):
        for k in [k for k in self._lie if k[:2] == ('srv', 'ps')]:
            del self._lie[k]
        _meth(self.ctx, 8, None, c_uint, c_uint, c_void_p)(self.ctx, 0, 16, self._tab([None] * 16))

    def lire(self, tex, w, h):
        """pixels RGBA (lignes de haut en bas)"""
        st = self.texture(w, h, RGBA8, bind=0, usage=USAGE_STAGING, cpu=CPU_READ)
        self.copier(st, tex)
        m = MAPPED()
        _ok(_meth(self.ctx, 14, HRESULT, c_void_p, c_uint, c_uint, c_uint, POINTER(MAPPED))(self.ctx, st, 0, 1, 0, byref(m)), 'Map lecture')
        lignes = [ctypes.string_at(m.pData + y * m.RowPitch, w * 4) for y in range(h)]
        _meth(self.ctx, 15, None, c_void_p, c_uint)(self.ctx, st, 0)
        liberer(st)
        return lignes


# ------------------------------------------------------------------ shaders du jeu
class _Blob(Structure):
    pass


def compiler(source, entree, cible):
    """HLSL -> DXBC (d3dcompiler_47) ; seulement pour les petits shaders de l'outil, pas pour ceux du jeu"""
    code, err = c_void_p(), c_void_p()
    src = source.encode()
    hr = _comp.D3DCompile(c_char_p(src), c_size_t(len(src)), None, None, None, c_char_p(entree.encode()), c_char_p(cible.encode()),
                          c_uint(0), c_uint(0), byref(code), byref(err))
    if hr != 0:
        msg = ctypes.string_at(_meth(err, 3, c_void_p)(err), _meth(err, 4, c_size_t)(err)).decode('latin-1') if err else ''
        raise OSError('D3DCompile : ' + msg)
    out = ctypes.string_at(_meth(code, 3, c_void_p)(code), _meth(code, 4, c_size_t)(code))
    liberer(code)
    return out


def desassembler(code):
    blob = c_void_p()
    hr = _comp.D3DDisassemble(c_char_p(code), c_size_t(len(code)), c_uint(0), None, byref(blob))
    if hr != 0:
        return ''
    p = _meth(blob, 3, c_void_p)(blob)
    n = _meth(blob, 4, c_size_t)(blob)
    txt = ctypes.string_at(p, n).decode('latin-1').rstrip('\0')
    liberer(blob)
    return txt
