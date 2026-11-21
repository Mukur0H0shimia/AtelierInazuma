# Atelier Inazuma

*English below.*

Outil pour créer des mods d'**Inazuma Eleven : Victory Road** (PC) : recolorer les techniques, les Keshin (esprits guerriers), les totems, les maillots, les tenues, les armures, les têtes et les objets, puis en faire des mods prêts à installer (format VRFW / Inazuma Fantasy).

- Aperçu 3D des techniques avec les vrais shaders du jeu (Direct3D 11), animation, particules, lumières.
- Recoloration : remplacer une couleur partout, calques, pinceaux, dessin sur les textures.
- Copies à code neuf : nouveaux joueurs, nouvelles tenues, nouveaux objets, copies de Keshin, techniques. **Les fichiers d'origine du jeu ne sont jamais modifiés.**
- Le contenu de tous vos mods (même désactivés) est rangé dans les onglets habituels.
- Interface en **français ou en anglais** (bouton FR / EN en haut à droite) ; les noms du jeu suivent la langue choisie.

## Ce qu'il faut

1. **Windows** avec le jeu (Steam).
2. **Python 3.12 ou plus récent** ([python.org](https://www.python.org/downloads/)) avec `numpy` : `pip install numpy`.
3. **Rien à extraire** : l'Atelier lit les fichiers du jeu **directement dans ses paquets** (`data\packs\*.cpk`). Le premier lancement prépare un index (quelques minutes) ; ensuite chaque fichier utilisé est rangé dans `AtelierCouleurs\cache\data_jeu`, la première fois seulement. *(Si vous avez déjà extrait le jeu dans un dossier `data` avec `common\` et `dx11\`, mettez-le à côté de `AtelierCouleurs` ou indiquez-le dans `config.json` : il sera utilisé à la place.)*
4. *(Facultatif)* Pour recompiler les parties natives : Visual Studio Build Tools, puis `AtelierNatif\compiler.bat` (lecteur Direct3D) et `AtelierCouleurs\moteur\natif\compiler.bat` (lecture rapide des paquets). Les deux sont fournis déjà compilés.

## Lancer

Double-cliquez sur **`AtelierCouleurs\Atelier Inazuma.exe`** (ou `Atelier Inazuma.bat`).

Au premier lancement, l'Atelier écrit tout seul `AtelierCouleurs\config.json`. Il cherche le jeu dans toutes vos bibliothèques Steam et choisit **le dossier qui contient vos mods**. Ça marche que vos mods soient dans le jeu de base (`steamapps\common\INAZUMA ELEVEN  Victory Road\mods`) ou dans une copie de dépôt (`steamapps\content\app_2799860\depot_…\mods`). Si le choix ne vous va pas, changez `jeu_dir` dans `config.json`.

| Réglage (`config.json`) | Rôle |
|---|---|
| `data_dir` | *(facultatif)* dossier des fichiers extraits du jeu (`common\`, `dx11\`) ; sans lui, lecture directe des paquets |
| `jeu_dir` | dossier du jeu qui contient le dossier `mods` |
| `sauvegardes_dir` | où l'Atelier range ses sauvegardes avant d'installer un mod |
| `langue` | `fr` ou `en` (aussi réglable avec le bouton FR / EN) |
| `port` | port local de l'interface (8765 par défaut) |

## Dossiers

- `AtelierCouleurs\` : l'Atelier (serveur Python + interface web).
- `AtelierMaillots\` : l'atelier des maillots (patron, numéros, emblème).
- `AtelierD3D\`, `AtelierNatif\` : rendu Direct3D avec les shaders du jeu (aperçus fidèles).

Ce dépôt ne contient **aucun fichier du jeu** : l'Atelier lit les fichiers de votre propre copie.

**Conseil :** jouez hors ligne avec des mods, et gardez une sauvegarde de vos parties.

---

# Atelier Inazuma (English)

A modding tool for **Inazuma Eleven: Victory Road** (PC): recolour techniques, **Keshin**, totems, kits, outfits, armours, heads and items, then turn them into ready-to-install mods (VRFW / Inazuma Fantasy format).

- 3D preview of techniques with the game's real shaders (Direct3D 11), animation, particles, lights.
- Recolouring: replace a colour everywhere, layers, brushes, drawing on textures.
- Copies with new codes: new players, outfits, items, Keshin copies, techniques. **The game's original files are never modified.**
- The content of all your mods (even disabled ones) shows up in the usual tabs.
- **French or English** interface (FR / EN button, top right); game names follow the chosen language.

## Requirements

1. **Windows** with the game (Steam).
2. **Python 3.12 or newer** ([python.org](https://www.python.org/downloads/)) with `numpy`: `pip install numpy`.
3. **Nothing to extract**: the Atelier reads the game files **straight from its packs** (`data\packs\*.cpk`). The first run builds an index (a few minutes); after that each file it uses is stored in `AtelierCouleurs\cache\data_jeu`, the first time only. *(If you have already extracted the game into a `data` folder with `common\` and `dx11\`, put it next to `AtelierCouleurs` or set it in `config.json`: it will be used instead.)*
4. *(Optional)* To rebuild the native parts: Visual Studio Build Tools, then `AtelierNatif\compiler.bat` (Direct3D player) and `AtelierCouleurs\moteur\natif\compiler.bat` (fast pack reading). Both are included prebuilt.

## Running

Double-click **`AtelierCouleurs\Atelier Inazuma.exe`** (or `Atelier Inazuma.bat`).

On the first run the Atelier writes `AtelierCouleurs\config.json` by itself. It searches every Steam library for the game and picks **the folder that holds your mods**. That works whether your mods are in the base game (`steamapps\common\INAZUMA ELEVEN  Victory Road\mods`) or in a depot copy (`steamapps\content\app_2799860\depot_…\mods`). If its choice is wrong, change `jeu_dir` in `config.json`.

| Setting (`config.json`) | Purpose |
|---|---|
| `data_dir` | *(optional)* folder of the extracted game files (`common\`, `dx11\`); without it, the packs are read directly |
| `jeu_dir` | game folder that contains the `mods` folder |
| `sauvegardes_dir` | where the Atelier stores backups before installing a mod |
| `langue` | `fr` or `en` (also set with the FR / EN button) |
| `port` | local port of the interface (8765 by default) |

This repository contains **no game files**: the Atelier reads the files of your own copy of the game.

**Tip:** play offline with mods, and keep a backup of your saves.
