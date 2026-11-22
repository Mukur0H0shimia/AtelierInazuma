# Journal des mises à jour — Atelier Inazuma

*English below.*

## 2.0.5
- **Español** : l'Atelier existe maintenant en espagnol, avec le vocabulaire du jeu (Keshin, Supertécnicas, Tiro, Regate, Parada…). Les noms du jeu suivent aussi la langue.
- **Choix de la langue** : un menu en haut à droite, et trois boutons dans ⚙ Paramètres (Français, English, Español).
- **« Installer » ne bloque plus** : les créations supprimées (dossier `_retires`) ne partent plus dans le jeu ; les chemins très longs (OneDrive…) sont acceptés ; si un fichier est utilisé par un autre programme, rien n'est changé et un message le dit. Avant, une installation pouvait s'arrêter au milieu et laisser le mod à moitié effacé (armure absente en jeu).
- **Tout l'Atelier en anglais** : environ 150 textes traduits en plus. Ils couvrent les rapports détaillés (esprits, totems, joueurs, tenues, objets, armures, maillots, cinématique d'échec), les messages d'erreur, l'éditeur de dessin complet, les calques, le texte de l'onglet Objets et la musique.
- Raccourcis : « Maj » s'affiche « Shift » en anglais.
- **Noms de tes mods dans le gestionnaire de mods** (Mes techniques, Mes esprits et totems, Mes personnages, Mes tenues, Mes objets, Mes maillots) : en anglais par défaut, avec leur traduction française et espagnole, comme les autres mods. Ils sont mis à jour au prochain « Installer ».
- L'avertissement « fichiers du jeu illisibles » est traduit lui aussi.

## 2.0.4
- **Aucun mod ne se charge, « requires `VRFW`, which is not enabled » dans le journal de VRFW** : si VRFW est installé mais absent de la liste des mods activés (ton gestionnaire a pu rallumer tes mods sans lui après le bug de la 2.0.2), l'Atelier le remet au démarrage.
- Installer un **maillot** ne crée plus non plus le fichier des mods activés du jeu (même bug que la 2.0.3).
- **Jeu sans fichier des mods activés** (VRFW active alors tous les mods) : l'Atelier croyait tous les mods éteints. Il lit maintenant les mods activés comme VRFW : stats d'origine (CharacterReforged), puissances (HissatsuReforged), techniques données par les mods.

## 2.0.3
- **Important si tous tes mods se sont éteints après « Installer »** : quand le jeu n'avait pas de fichier `mods\enabled.toml`, l'Atelier en créait un qui ne listait que ses propres mods. VRFW éteignait alors tous les autres, VRFW compris. L'Atelier ne crée plus ce fichier, et retire au démarrage celui qu'une version précédente avait créé : tes mods se rechargent tous.

## 2.0.2
- **⚙ Paramètres > Dossier du jeu** : montre le dossier du jeu où « Installer » met tes créations, et toutes les installations trouvées (avec ou sans VRFW, tes mods déjà dedans). On peut en choisir une autre ou en taper le chemin. Utile si ton gestionnaire de mods utilise une autre installation du jeu (créations « installées » mais absentes en jeu).
- Au premier lancement, l'Atelier choisit d'abord l'installation du jeu qui a VRFW.
- Si VRFW n'est pas dans le jeu choisi, « Installer » le dit dans une fenêtre, avec le dossier. Avant, l'avertissement restait caché dans les détails.
- Ouvrir une technique ne plante plus quand le jeu n'a pas de dossier mods.
- **Anglais** : une vingtaine de textes récents restaient en français (portrait des cartes, stats, suppression, auras choisies par le match, polices, copier-coller de textures…). Ils sont traduits.
- **« Et maintenant »** : ce bloc n'apparaît plus en double, et il disparaît quand on ouvre un autre élément ou qu'on change d'onglet. Avant, les suites d'un esprit restaient affichées sous un nouveau joueur.
- **Rapports de création en anglais** : lignes des techniques (objets, auras, bannière, cinématique d'échec, totem…), contrôle des mods, suppressions, menus Techniques du joueur et Technique liée.
- Une ligne d'aura n'est plus répétée plusieurs fois dans le rapport.
- « Le jeu est-il ouvert ? » ne peut plus planter sur un Windows dont la liste des programmes contient des caractères spéciaux (il bloquait l'onglet Bannières et « Installer »).

## 2.0.1
- **L'Atelier démarre même si un fichier du jeu est illisible** (par exemple modifié par un autre outil de mod). Avant, il s'arrêtait sur « Le serveur de l'atelier n'a pas démarré ». Maintenant, seule la partie concernée reste vide, et un message dit laquelle.
- Esprits et totems : toujours listés avec leur nom, même si la table des personnages ne se lit pas.
- Les fichiers « libres » compressés posés dans le dossier du jeu sont lus correctement.

## 2.0

### Créer et installer, plus simple
- **Un seul bouton « Créer »** dans chaque panneau (techniques, esprits, totems, joueurs, maillots…). Il crée la copie **sans toucher au jeu** ; on l'installe ensuite depuis sa carte dans **Mes créations**.
- **Mes créations** :
  - chaque création garde son propre projet : deux copies du même personnage ne partagent plus les mêmes textures ;
  - **« Modifier »** rouvre la création elle-même au lieu d'ouvrir un nouveau projet ;
  - **« Supprimer »** range les fichiers à part, donc ils restent récupérables. La suppression est refusée si la création sert encore ailleurs ;
  - « Installer » n'apparaît que dans **Terminées**.
- Rouvrir un élément déjà commencé propose de **continuer le projet** au lieu d'en créer un doublon.
- Après une création, des boutons **« Et maintenant »** proposent la suite ; l'onglet Armures a un guide quand aucun esprit n'est encore copié.

### Stats
- **« En attente de stats »** : on fait d'abord le visuel, puis on règle les valeurs (ou on garde celles de l'original).
- **Nouveau menu des stats** inspiré de la fiche d'équipement du jeu, en plein écran :
  - carte et aperçu comme en jeu, avec les icônes d'éléments du jeu ;
  - l'original et l'écart affichés sur chaque ligne ;
  - réglage avec les boutons ± (Maj = par 10), ↺ pour remettre une ligne, « Tout remettre » pour tout remettre.
- **Joueurs** : le poste, le 2e poste et l'élément d'origine viennent du jeu. Les stats d'origine viennent d'un mod activé qui les redéfinit (CharacterReforged…).
- **Techniques** : l'original affiché tient compte des mods (HissatsuReforged…).
- « Enregistrer » prend 0,3 s au lieu de 10 s. Le bouton Stats est aussi sur les totems.

### Totems et esprits
- **Technique liée** pour les copies de totems.
- Copies de techniques à totem (Frappe du loup…) :
  - le totem apparaît bien dans la cinématique ;
  - le son de l'invocation est revenu ;
  - la bannière s'affiche pour chaque lanceur.
- « Créer » des esprits et des totems remarche.

### Techniques plus fidèles au jeu
- **Cinématique d'échec** : les arrêts et défenses qui ont une 2e cinématique (227 techniques) livrent maintenant aussi la leur, avec les mêmes couleurs. Avant, un arrêt raté montrait les couleurs de l'original. Les copies déjà faites sont réparées au prochain « Installer ».
- **Auras recolorées** : la cinématique copiée garde la bonne forme. Avant, 45 techniques testées sur 138 retombaient dans une copie qui faisait perdre son visage à l'adversaire.
- Les auras **choisies par le match** (aura du ballon) ne sont plus proposées à la recoloration, puisque le jeu les choisit lui-même.
- Une texture **empruntée à un autre objet** est signalée et ignorée : le jeu ne la recolore pas dans la copie.
- **Contrôle avant le jeu** : à chaque « Installer », l'Atelier vérifie les règles du chargeur de mods VRFW et signale ce qui serait refusé.

### Confort
- ⚙ **Paramètres** :
  - 4 palettes de couleurs ;
  - **musique de fond** (le thème de l'écran titre du jeu) ;
  - **Mes polices** pour importer ses polices .ttf / .otf (bannières, maillots, outil Texte).
- **Tablette graphique** : la pression du stylet règle la taille du pinceau, et le stylet ne fait plus glisser l'écran.
- **Copier une texture** d'une technique et la coller sur une autre (clic droit).
- **Sons** : décodeur à nous, donc plus de son saturé ni écrêté.
- La bannière se fait depuis la technique ouverte et se voit tout de suite dans le lecteur.
- **Mode simple** : barre de lecture réduite aux réglages utiles.
- L'Atelier s'ouvre toujours dans sa propre fenêtre, plus jamais dans Edge.

## 1.9
- **Plus aucune création perdue** : un Atelier neuf reprend les créations déjà dans le jeu, et « Installer » prévient avant de retirer quoi que ce soit.
- **Fenêtre toujours à jour** : l'Atelier ne réutilise plus un ancien serveur resté ouvert, et le serveur s'arrête quand on ferme la fenêtre.
- **Techniques plus fidèles** : les effets sans accroche sont à leur bonne place (Bouclier royal, Tempête du tigre et 36 autres), et la bonne version des objets est utilisée (Choc de la vouivre, Cris d'Eden).
- **Bannières perso** visibles dans les aperçus. Le texte suit le nom de la technique.
- **Mes créations** : tenues, objets et armures y apparaissent, et les armures se créent depuis l'accueil.
- Mode dessin des maillots : la pièce choisie est bien celle cliquée.
- Corrections :
  - son (erreur 500) ;
  - vidéos officielles pour tous ;
  - éléments affichés en français ;
  - rapports en anglais ;
  - dossiers avec accents et espaces.

## 1.8
- **Mise à jour sans rien perdre** : une nouvelle version décompressée ailleurs reprend les données de la précédente (cache, projets, créations, maillots, réglages), donc le long 1er démarrage n'est pas refait.

## 1.7
- Le raccourci du bureau mène toujours à la version la plus récente.
- Numéro de version dans le titre de la fenêtre.

## 1.6
- Encodage des textures en C : une copie de personnage prend environ 5 s au lieu de 32 s.

## 1.5
- Les copies de personnages, tenues et armures ne restent plus bloquées sur « Création de la copie… ».

## 1.4
- Aperçu 3D beaucoup plus léger : environ 2 % du processeur au repos au lieu d'environ 50 %.

## 1.3
- Bannières : seules les polices présentes sur le PC sont proposées. Une police absente est remplacée par Impact, avec un message clair.

## 1.2
- L'Atelier démarre même si le jeu a quelques fichiers « libres » posés par un mod.
- Recherche du jeu plus large : toutes les bibliothèques Steam. Si le jeu est introuvable, l'Atelier demande où il est.

---

# Update log — Atelier Inazuma

## 2.0.5
- **Español**: the Atelier is now in Spanish too, with the game's own words (Keshin, Supertécnicas, Tiro, Regate, Parada…). Game names follow the language as well.
- **Choosing the language**: a menu at the top right, and three buttons in ⚙ Settings (Français, English, Español).
- **"Install" no longer gets stuck**: deleted creations (`_retires` folder) no longer go into the game; very long paths (OneDrive…) are accepted; if a file is used by another program, nothing is changed and a message says so. Before, an install could stop halfway and leave the mod half deleted (armour missing in game).
- **The whole Atelier in English**: about 150 more texts translated. They cover the detailed reports (Keshin, totems, players, outfits, items, armours, kits, failure cutscene), error messages, the full drawing editor, layers, the Items tab text and the music.
- Shortcuts: "Maj" now shows as "Shift" in English.
- **Your mods' names in the mod manager** (My techniques, My Keshin and totems, My characters, My outfits, My items, My kits): English by default, with their French and Spanish translations, like the other mods. They are updated at the next "Install".
- The "unreadable game files" warning is translated too.

## 2.0.4
- **No mod loads, "requires `VRFW`, which is not enabled" in the VRFW log**: if VRFW is installed but missing from the enabled-mods list (your mod manager may have switched your mods back on without it after the 2.0.2 bug), the Atelier puts it back on start.
- Installing a **kit** no longer creates the game's enabled-mods file either (same bug as 2.0.3).
- **Game without an enabled-mods file** (VRFW then enables every mod): the Atelier thought every mod was off. It now reads the enabled mods like VRFW does: original stats (CharacterReforged), powers (HissatsuReforged), moves given by mods.

## 2.0.3
- **Important if all your mods were switched off after "Install"**: when the game had no `mods\enabled.toml` file, the Atelier created one listing only its own mods. VRFW then switched every other mod off, VRFW included. The Atelier no longer creates this file, and on start it removes the one an older version made: all your mods load again.

## 2.0.2
- **⚙ Settings > Game folder**: shows the game folder where "Install" puts your creations, and every installation found (with or without VRFW, your mods already in it). You can pick another one or type its path. Useful if your mod manager uses another installation of the game (creations "installed" but missing in game).
- On first run, the Atelier picks the game installation that has VRFW first.
- If VRFW is not in the chosen game, "Install" says so in a window, with the folder. Before, the warning stayed hidden in the details.
- Opening a technique no longer crashes when the game has no mods folder.
- **English**: about twenty recent texts were still in French (card portrait, stats, delete, auras picked by the match, fonts, texture copy-paste…). They are now translated.
- **"What next"**: this block no longer shows twice, and it goes away when another item is opened or the tab changes. Before, a spirit's next steps stayed under a new player.
- **Creation reports in English**: technique lines (objects, auras, banner, failure cutscene, totem…), mod check, deletions, the player's Techniques and Linked technique menus.
- An aura line is no longer repeated in the report.
- "Is the game open?" can no longer crash on a Windows whose process list has special characters (it blocked the Banners tab and "Install").

## 2.0.1
- **The Atelier starts even if a game file can't be read** (for example changed by another mod tool). Before, it stopped on "The Atelier server did not start". Now only that part stays empty, and a message says which one.
- Spirits and totems: still listed with their names even if the character table can't be read.
- Compressed loose files placed in the game folder are read correctly.

## 2.0

### Creating and installing, simpler
- **A single "Create" button** in every panel. It makes the copy **without touching the game**; install it afterwards from its card in **My creations**.
- **My creations**:
  - each creation keeps its own project;
  - **"Edit"** reopens the creation itself;
  - **"Delete"** puts the files aside, so they can still be recovered;
  - "Install" only appears under **Finished**.
- Reopening something already started offers to **continue the project** instead of making a duplicate.
- After a creation, **"What next"** buttons suggest the next step.

### Stats
- **"Waiting for stats"**: make the look first, set the values later (or keep the original's).
- **New stats menu** inspired by the game's equipment screen:
  - in-game look, with the game's element icons;
  - the original and the difference on every line;
  - ± buttons (Shift = by 10), ↺ per line, "Reset all".
- **Players**: original position, second position and element are read from the game. Original stats come from an enabled mod that redefines them (CharacterReforged…).
- **Techniques**: the original shown includes mod changes (HissatsuReforged…).
- "Save" takes 0.3 s instead of 10 s. The Stats button is on totems too.

### Totems and spirits
- **Linked technique** for totem copies.
- Copies of totem techniques (Frappe du loup…): the totem shows in the cutscene, the summon sound is back, and the banner shows for every user.
- "Create" works again for spirits and totems.

### Techniques closer to the game
- **Failure cutscene**: blocks and saves with a second cutscene (227 techniques) now ship theirs too, with the same colours. Copies made before are repaired at the next "Install".
- **Recoloured auras**: the copied cutscene keeps the right shape. Before, 45 of the 138 techniques tested fell back to a copy that made the opponent lose their face.
- Auras **picked by the match** (ball aura) are no longer offered for recolouring.
- A texture **borrowed from another object** is flagged and skipped.
- **Check before playing**: every "Install" checks the rules of the VRFW mod loader and reports what it would refuse.

### Comfort
- ⚙ **Settings**: 4 colour palettes, **background music** (the game's title theme), **My fonts** to import .ttf / .otf files.
- **Graphics tablet**: pen pressure sets the brush size.
- **Copy a texture** from one technique and paste it on another (right-click).
- **Sounds**: our own decoder, so no more saturated or clipped sound.
- The banner is made from the open technique and shows straight away in the player.
- **Simple mode**, and the Atelier always opens in its own window (never Edge).

## 1.9
- **No more lost creations**: a fresh Atelier takes back the creations already in the game, and "Install" warns before removing anything.
- **Window always up to date**, and the server stops when the window is closed.
- **Techniques closer to the game**: unattached effects in the right place (Royal Shield, Tiger Storm and 36 more), and the right object version (Wyvern Crash, Scream of Eden).
- **Custom banners** in the previews.
- My creations lists outfits, items and armours.
- Kit drawing mode picks the right part.
- Fixes: sound, official videos, English reports, folders with accents.

## 1.8
- **Update without losing anything**: a new version takes back the previous version's data.

## 1.7
- The desktop shortcut follows the newest version.
- Version number in the window title.

## 1.6
- Textures encoded in C: a character copy takes about 5 s instead of 32 s.

## 1.5
- Character, outfit and armour copies no longer hang.

## 1.4
- Much lighter 3D preview: about 2 % CPU when idle instead of about 50 %.

## 1.3
- Banners: only fonts installed on the PC are offered. A missing font is replaced by Impact, with a clear message.

## 1.2
- The Atelier starts even with loose game files left by a mod.
- Wider game search: if the game can't be found, the Atelier asks where it is.
