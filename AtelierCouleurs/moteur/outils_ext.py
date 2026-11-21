"""Programmes extérieurs : ffmpeg (sons des cinématiques, bannières des techniques).
Celui fourni avec l'Atelier (outils\\ffmpeg.exe, à côté des dossiers Atelier…) s'il est là, sinon celui du PATH.
External programs: the bundled ffmpeg if present, else the one on PATH."""
import os

_RACINE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def ffmpeg():
    p = os.path.join(_RACINE, 'outils', 'ffmpeg.exe')
    return p if os.path.isfile(p) else 'ffmpeg'
