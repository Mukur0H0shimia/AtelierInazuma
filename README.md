# Atelier Inazuma

*English below.*

Outil pour créer des mods d'**Inazuma Eleven : Victory Road** (PC) : recolorer les techniques, les Keshin (esprits guerriers), les totems, les maillots, les tenues, les armures, les têtes et les objets, puis en faire des mods prêts à installer (format VRFW / Inazuma Fantasy).

## ⬇️ Télécharger

**[Télécharger AtelierInazuma.zip](https://github.com/Mukur0H0shimia/AtelierInazuma/releases/latest/download/AtelierInazuma.zip)** : un seul fichier, tout est dedans (Python et ffmpeg compris), **rien d'autre à installer**.

1. Téléchargez le zip, puis **clic droit → Extraire tout…** (n'importe où : Bureau, Documents…).
2. Ouvrez le dossier `AtelierInazuma` et double-cliquez sur **`Atelier Inazuma.exe`**.
   Windows demande peut-être une confirmation la première fois (programme non signé) : cliquez **Exécuter**, ou **Informations complémentaires → Exécuter quand même**. Ensuite il ne redemande plus.
3. Au premier lancement, un raccourci **Atelier Inazuma** apparaît sur votre bureau. Les fois suivantes, lancez l'Atelier depuis ce raccourci.

Le **premier lancement** prépare l'Atelier pendant quelques minutes, avec une barre de progression. Ensuite, il s'ouvre en quelques secondes.

## Ce qu'il fait

- Aperçu 3D des techniques avec les vrais shaders du jeu (Direct3D 11), animation, particules, lumières.
- Recoloration : remplacer une couleur partout, calques, pinceaux, dessin sur les textures.
- Copies à code neuf : nouveaux joueurs, nouvelles tenues, nouveaux objets, copies de Keshin, techniques. **Les fichiers d'origine du jeu ne sont jamais modifiés.**
- Le contenu de tous vos mods (même désactivés) est rangé dans les onglets habituels.
- Interface en **français ou en anglais** (bouton FR / EN en haut à droite) ; les noms du jeu suivent la langue choisie.

## Ce qu'il faut

- **Windows 10 ou 11** avec le jeu installé par **Steam**.
- **Rien à extraire** : l'Atelier lit les fichiers du jeu directement dans ses paquets (`data\packs\*.cpk`). Chaque fichier utilisé est rangé dans `AtelierCouleurs\cache\data_jeu` la première fois.
- L'Atelier trouve tout seul le jeu dans vos bibliothèques Steam et choisit **le dossier qui contient vos mods** : jeu de base (`steamapps\common\INAZUMA ELEVEN  Victory Road\mods`) ou copie de dépôt (`steamapps\content\app_2799860\depot_…\mods`).

**Conseil :** jouez hors ligne avec des mods, et gardez une sauvegarde de vos parties.

## Réglages (facultatif)

L'Atelier écrit tout seul `AtelierCouleurs\config.json`. Changez-le seulement si son choix ne vous va pas :

| Réglage | Rôle |
|---|---|
| `jeu_dir` | dossier du jeu qui contient le dossier `mods` |
| `data_dir` | dossier des fichiers du jeu déjà extraits (`common\`, `dx11\`) ; sans lui, lecture directe des paquets |
| `sauvegardes_dir` | où l'Atelier range ses sauvegardes avant d'installer un mod |
| `langue` | `fr` ou `en` (aussi réglable avec le bouton FR / EN) |
| `port` | port local de l'interface (8765 par défaut) |

## Pour les développeurs

- `AtelierCouleurs\` : l'Atelier (serveur Python + interface web). `AtelierMaillots\` : l'atelier des maillots. `AtelierD3D\`, `AtelierNatif\` : rendu Direct3D avec les shaders du jeu.
- Depuis les sources de ce dépôt (sans le zip) : Python 3.12+ avec `numpy`, et ffmpeg dans le PATH pour les sons et les bannières.
- Parties natives (fournies déjà compilées) : `AtelierNatif\compiler.bat`, `AtelierCouleurs\moteur\natif\compiler.bat` (Visual Studio Build Tools).

Ce dépôt ne contient **aucun fichier du jeu** : l'Atelier lit les fichiers de votre propre copie.

---

# Atelier Inazuma (English)

A modding tool for **Inazuma Eleven: Victory Road** (PC): recolour techniques, **Keshin**, totems, kits, outfits, armours, heads and items, then turn them into ready-to-install mods (VRFW / Inazuma Fantasy format).

## ⬇️ Download

**[Download AtelierInazuma.zip](https://github.com/Mukur0H0shimia/AtelierInazuma/releases/latest/download/AtelierInazuma.zip)**: one file with everything inside (Python and ffmpeg included), **nothing else to install**.

1. Download the zip, then **right-click → Extract All…** (anywhere: Desktop, Documents…).
2. Open the `AtelierInazuma` folder and double-click **`Atelier Inazuma.exe`**.
   Windows may ask for confirmation the first time (unsigned program): click **Run**, or **More info → Run anyway**. It won't ask again.
3. On the first run, an **Atelier Inazuma** shortcut appears on your desktop. Use it to start the Atelier from then on.

The **first run** gets the Atelier ready for a few minutes, with a progress bar. After that it opens in a few seconds.

## What it does

- 3D preview of techniques with the game's real shaders (Direct3D 11), animation, particles, lights.
- Recolouring: replace a colour everywhere, layers, brushes, drawing on textures.
- Copies with new codes: new players, outfits, items, Keshin copies, techniques. **The game's original files are never modified.**
- The content of all your mods (even disabled ones) shows up in the usual tabs.
- **French or English** interface (FR / EN button, top right); game names follow the chosen language.

## Requirements

- **Windows 10 or 11** with the game installed through **Steam**.
- **Nothing to extract**: the Atelier reads the game files straight from its packs (`data\packs\*.cpk`). Each file it uses is stored in `AtelierCouleurs\cache\data_jeu` the first time.
- The Atelier finds the game in your Steam libraries by itself and picks **the folder that holds your mods**: base game (`steamapps\common\INAZUMA ELEVEN  Victory Road\mods`) or depot copy (`steamapps\content\app_2799860\depot_…\mods`).

**Tip:** play offline with mods, and keep a backup of your saves.

## Settings (optional)

The Atelier writes `AtelierCouleurs\config.json` by itself. Only change it if its choice is wrong:

| Setting | Purpose |
|---|---|
| `jeu_dir` | game folder that contains the `mods` folder |
| `data_dir` | folder of already-extracted game files (`common\`, `dx11\`); without it, the packs are read directly |
| `sauvegardes_dir` | where the Atelier stores backups before installing a mod |
| `langue` | `fr` or `en` (also set with the FR / EN button) |
| `port` | local port of the interface (8765 by default) |

## For developers

- `AtelierCouleurs\`: the Atelier (Python server + web interface). `AtelierMaillots\`: the kit workshop. `AtelierD3D\`, `AtelierNatif\`: Direct3D rendering with the game's shaders.
- From this repository's sources (without the zip): Python 3.12+ with `numpy`, and ffmpeg on PATH for sounds and banners.
- Native parts (included prebuilt): `AtelierNatif\compiler.bat`, `AtelierCouleurs\moteur\natif\compiler.bat` (Visual Studio Build Tools).

This repository contains **no game files**: the Atelier reads the files of your own copy of the game.
