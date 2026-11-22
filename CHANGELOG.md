# Journal des mises à jour — Atelier Inazuma

*English below.*

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
