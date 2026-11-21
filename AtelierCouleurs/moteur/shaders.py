"""Shaders du jeu : quel programme dessine un matériau d'effet (lecture des fichiers du jeu, 13/11/2026).

Chaîne (vérifiée sur ev60014300 Frappe stellaire, ev60017800 Botte de Lancelot) :
- G4MD : table de l'en-tête +0x78 (jusqu'à +0x7A) = crc32 des NOMS de shaders utilisés par le fichier
  (ex. Effect_T1_low, Effect_FakeParticle, Effect_T3Threshold, Effect_ThresholdGrd) ;
- matériau : octet haut de v4 = n° dans cette liste (le nom du matériau, « Effect_T1_07 », n'est qu'une étiquette) ;
- dx11/shader/<version>/shader_list.cfg.bin : lignes [nom du shader, '#/shader/<SHADER_VERSION>/<fichier>.fxbin'] ;
- .fxbin : techniques ; la 1re « main » donne (vertex shader, pixel shader), ex. Effect_T3Threshold ->
  effect_test_threshold.fxbin -> Effect_TestThreshold.vfxo / .pfxo (DXBC lisible avec D3DDisassemble).
"""
import os, re, zlib

_cache = {}


def _dossier(data_dir):
    d = os.path.join(data_dir, 'dx11', 'shader')
    vs = sorted(x for x in os.listdir(d) if os.path.isdir(os.path.join(d, x))) if os.path.isdir(d) else []
    return os.path.join(d, vs[-1]) if vs else None


def table(data_dir):
    """crc32(nom du shader) -> {'nom', 'vs', 'ps'}"""
    if data_dir in _cache:
        return _cache[data_dir]
    from . import cfgbin
    out = {}
    d = _dossier(data_dir)
    f = d and os.path.join(d, 'shader_list.cfg.bin')
    if f and os.path.exists(f):
        for c, v in cfgbin.lire(open(f, 'rb').read()):
            if (c & 0xFFFFFFFF) != 0xA0795486 or len(v) < 2 or not isinstance(v[0], str) or not isinstance(v[1], str):
                continue
            nom, fx = v[0], os.path.join(d, os.path.basename(v[1]))
            vs = ps = nom
            if os.path.exists(fx):
                mots = [m.decode() for m in re.findall(rb'[A-Za-z_][A-Za-z0-9_]{2,}', open(fx, 'rb').read())]
                if 'main' in mots:
                    i = mots.index('main')
                    vs, ps = (mots[i + 1:i + 3] + [nom, nom])[:2]
            out[zlib.crc32(nom.encode())] = {'nom': nom, 'vs': vs, 'ps': ps}
    _cache[data_dir] = out
    return out
