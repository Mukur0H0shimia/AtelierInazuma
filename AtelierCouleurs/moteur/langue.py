"""Langue des textes du jeu montrés par l'Atelier (noms des techniques, Keshin, personnages, objets…) : 'fr', 'en' ou 'es'.
Réglée par le bouton FR / EN de l'interface (config.json « langue »). Les textes de l'interface elle-même sont traduits
dans le navigateur (web/i18n.js).

Language of the game texts shown by the Atelier (technique, Keshin, character and item names): 'fr' or 'en'. Set by the
FR / EN button (config.json "langue"). The interface itself is translated in the browser (web/i18n.js)."""

LANGUES = ('fr', 'en', 'es')                # (22/11) + espagnol
_langue = 'fr'


def code():
    """langue des textes du jeu ('fr', 'en' ou 'es')"""
    return _langue


def regler(l):
    global _langue
    _langue = l if l in LANGUES else 'fr'
    return _langue
