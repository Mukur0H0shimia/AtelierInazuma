# Journal des mises à jour — Atelier Inazuma

*English below.*

## 3.0.2
- **⚙ Paramètres coupé** : avec la palette « Comme le jeu » (celle par défaut), la fenêtre ne défilait pas ; le bas (Dossier du jeu, Corbeille, Cache) était caché, même en plein écran à 100 %. Elle défile maintenant jusqu'en bas.
- **Mode dessin sur un petit écran** : la barre de lecture de la vue 3D passe à la ligne ; « Bannière », « Son » et le bouton vidéo ne sortent plus de l'écran.

## 3.0.1
- **Écrans plus petits que le full HD** (portable 1366 × 768, ou écran à 125-150 % dans Windows) : en cliquant sur l'élément, la bannière… d'une fiche (technique, esprit guerrier, totem, armure), la case de réglage était écrasée et on ne pouvait rien choisir. Elle garde maintenant sa taille et la fiche défile. Le nom de la technique n'est plus coupé (« S… »), et l'écran du joueur n'a plus de barre de défilement en travers.
- **◎ Voir seul** (onglet Techniques → Textures) : l'objet de la texture choisie, seul, au repos, pour le retoucher comme un esprit guerrier (les pingouins, le dragon…). Pour une pièce d'effet : seulement les pièces qui portent cette texture. Marche aussi en mode dessin ; « ✕ Tout revoir » ramène la technique entière.
- **Lettres accentuées dans les bannières** (style « Lettres du jeu ») : ñ, á, í, ó, ú, Á, Í, Ó, Ú, ¡, ü, ä, ö, ß, ã, õ… découpées dans les bannières du jeu en espagnol, portugais, allemand et italien (Cañón…). Une lettre qui n'existe que dans un autre élément prend maintenant les vraies couleurs de l'élément choisi ; une lettre qu'aucune bannière n'a (ì, ò…) s'écrit sans accent au lieu de disparaître.
- Au 1er lancement après la mise à jour, l'Atelier refait ses lettres du jeu (environ 5 minutes, en arrière-plan) : les bannières « Lettres du jeu » arrivent quand c'est fini.

## 3.0
### Joueurs : l'écran du Tableau des compétences
- **Stats** d'un joueur (Mes créations) s'ouvre maintenant sur un écran fait comme le **Tableau des compétences du jeu** :
  - à gauche : la carte, le poste, **la case de l'esprit guerrier ou du totem**, puis les **6 techniques** ;
  - au centre : le joueur en 3D ;
  - sous son nom : **les 8 stats à régler** (− / +, la barre, ↺), le 2e poste et l'élément ;
  - en bas à droite : la fiche de la case choisie (puissance, TENSION, niveau d'apprentissage) et la liste pour la remplir.
- Stats et techniques s'enregistrent ensemble. « Choisir ses techniques » ouvre le même écran.

### Esprits guerriers, totems et armures
- **Fiche faite comme la carte Keshin du jeu** : bandeau de l'élément, portrait, barre de sa technique avec sa puissance, élément, Niv. 1.
- **Apparition** : tu choisis l'invocation parmi tous les esprits du jeu (Pégase : 89 choix au lieu de 17), ceux qui ont les mêmes os en premier. « Selon l'élément » suit l'élément choisi, et l'aperçu change tout de suite.
- **Bonus et effet unique** : jusqu'à 6 bonus et 3 effets uniques, choisis parmi ceux du jeu (et des mods activés), comme les esprits du jeu.
- **Totems** : l'aperçu montre l'invocation du totem en match (ta copie, avec ses couleurs). Tu peux aussi lui donner les gestes d'un des 22 totems.
- **Fiche d'armure** : « Stats » sur une armure règle sa puissance, son élément, ses bonus, son effet unique et sa **mise en armure** (80 scènes, ou « Selon l'élément »). Avant : « création inconnue ».
- **Aperçus** : la bannière de ta copie s'affiche pendant l'invocation. La mise en armure montre ses deux bannières, et à la fin le joueur porte vraiment l'armure, avec tes couleurs.

### Bannières
- L'onglet Bannières fait aussi celles de tes **esprits guerriers**, **totems** (bannière de leur nom) et **armures** (bannière ARMED). Leur fiche a une case « Bannière » avec « ✎ Personnaliser la bannière ».
- **Styles d'écriture du jeu** dans les polices (groupe « Styles des esprits ») : Esprit guerrier (un par élément), Totem et Armure, refaits à partir des vraies bannières du jeu. Les bannières automatiques de tes copies prennent ces styles.

### Techniques
- **Le lecteur du jeu partout** : une technique s'ouvre directement dans le lecteur (les vraies couleurs du jeu), en pause sur l'image 0. Le curseur d'image l'ouvre aussi. L'aperçu approché ne se voit plus que pendant le chargement.
- **Couleurs plus fidèles** : « Remplacer une couleur partout » vers une couleur pâle (jaune → blanc) blanchit maintenant aussi les couleurs des sommets et des particules, comme VRFW. Nouveau réglage de **luminosité** pour les sommets et les particules.
- **Effets communs** (traits de vitesse…) : maintenant recolorables.
- **Tir lointain** : la copie d'un tir lointain s'utilise dans tous les duels.
- **Lumières de l'effet** (intensité) : réglage visible dans l'Atelier seulement pour l'instant (VRFW ne l'accepte pas encore en jeu).

### Maillots
- **Dessiner l'icône de la boutique et l'emblème** (✎ Dessiner), comme dans l'Atelier Maillots. L'icône part de celle du maillot de base dans le jeu.

### Corrections
- **Écran à 125 % (ou plus)** : le lecteur s'ouvrait décalé, trop petit et impossible à fermer. Corrigé.
- Changer d'apparition rapidement pouvait poser le lecteur au mauvais endroit, ou laisser l'aperçu vide jusqu'à sortir et revenir.
- La bannière de l'aperçu restait affichée par-dessus le lecteur et dans les autres onglets. Une technique restait « encore là » (barre de lecture, compteurs) après un changement d'onglet.
- Fiche d'esprit : les cases restent sur une ligne (Montagne…), et l'effet unique ne disparaît plus après plusieurs bonus.
- Tous les nouveaux textes en anglais et en espagnol.

## 2.0.6
- **Corbeille** (⚙ Paramètres) : tout ce que tu as supprimé (projets, créations, maillots) se voit dans une liste avec sa date et sa taille. « Restaurer » le remet comme avant ; « Supprimer définitivement » l'efface pour gagner de la place.
- **Vider le cache** (⚙ Paramètres) : libère la place prise par ce que l'Atelier a déjà lu du jeu et des mods. Tes créations ne sont pas touchées, et le terrain des cinématiques est gardé.
- **« Modifier » rouvrait une création avec les couleurs d'origine** quand elle avait été faite avec une ancienne version et que son projet avait été retiré de « À continuer ». Chaque création retrouve maintenant son projet toute seule, et ce projet ne s'affiche plus dans « À continuer » (il ne peut plus être jeté par erreur).
- **Supprimer un maillot dans Mes créations** ne le retirait pas : il revenait au rechargement. C'est corrigé.
- **Armures sur tous les joueurs** : une armure faite dans l'Atelier n'avait le modèle que pour un seul type de corps ; sur les autres joueurs, le jeu ne proposait pas l'armure. Elle a maintenant un modèle pour chaque corps (comme les armures du jeu). Pour une armure déjà faite : « Installer » sur la carte de ton esprit guerrier.
- **Invocation selon l'élément** : un esprit guerrier copié dont tu changes l'élément (« Régler les stats ») a maintenant l'invocation de cet élément, comme ceux du jeu (feu → invocation de feu…). Il prend les animations d'un esprit de cet élément qui a les mêmes os ; s'il n'y en a aucun, l'invocation d'origine reste et le rapport le dit.
- Refaire un esprit guerrier avec « Créer » garde maintenant ses stats (avant, elles étaient perdues).
- **Anglais et espagnol complets** : les phrases qui contiennent un nom ou un nombre (rapports, confirmations, menus : « Préréglage « Rouge » appliqué », « Sélection : 3 pièces »…) restaient en français. Elles sont maintenant traduites, et les noms des maillots du jeu suivent la langue choisie.

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

## 3.0.2
- **⚙ Settings cut off**: with the "Like the game" palette (the default one), the window didn't scroll; its bottom (Game folder, Trash, Cache) was hidden, even full screen at 100 %. It now scrolls all the way down.
- **Drawing mode on a small screen**: the 3D view's playback bar wraps onto a second line; "Banner", "Sound" and the video button no longer go off-screen.

## 3.0.1
- **Screens smaller than full HD** (1366 × 768 laptop, or a screen at 125-150 % in Windows): clicking the element, the banner… of a sheet (technique, Keshin, totem, armour) squashed its setting box and nothing could be chosen. It now keeps its size and the sheet scrolls. The technique name is no longer cut (“S…”), and the player screen no longer has a sideways scrollbar.
- **◎ View alone** (Techniques tab → Textures): the object of the chosen texture, alone, at rest, to retouch it like a Keshin (the penguins, the dragon…). For an effect part: only the pieces using that texture. Works in drawing mode too; “✕ Show everything” brings the whole technique back.
- **Accented letters in banners** (“Game lettering” style): ñ, á, í, ó, ú, Á, Í, Ó, Ú, ¡, ü, ä, ö, ß, ã, õ… cut from the game's Spanish, Portuguese, German and Italian banners (Cañón…). A letter that only exists in another element now takes the real colours of the chosen element; a letter no banner has (ì, ò…) is written without its accent instead of disappearing.
- On the first launch after the update, the Atelier rebuilds its game letters (about 5 minutes, in the background): “Game lettering” banners come once it's done.

## 3.0
### Players: the Skill board screen
- A player's **Stats** (My creations) now opens a screen made like the **game's Skill board**:
  - left: the card, the position, **the Keshin or totem slot**, then the **6 techniques**;
  - centre: the player in 3D;
  - under the name: **the 8 stats to set** (− / +, the bar, ↺), the 2nd position and the element;
  - bottom right: the selected slot's sheet (power, TENSION, level learnt) and the list to fill it.
- Stats and techniques are saved together. The techniques button on a player opens the same screen too.

### Keshin, totems and armours
- **Sheet made like the game's Keshin card**: element banner, portrait, its technique bar with its power, element, Lv. 1.
- **Appearance**: choose the summon among every Keshin in the game (Pegasus: 89 choices instead of 17), the ones with the same bones first. "By element" follows the chosen element, and the preview changes straight away.
- **Bonuses and unique effect**: up to 6 bonuses and 3 unique effects, picked from the game's own (and enabled mods'), like the game's Keshin.
- **Totems**: the preview shows the totem's in-match summon (your copy, in its colours). You can also give it the moves of one of 22 totems.
- **Armour sheet**: "Stats" on an armour sets its power, element, bonuses, unique effect and its **Armour transformation** (80 scenes, or "By element"). Before: "unknown creation".
- **Previews**: your copy's banner shows during the summon. The armour transformation shows both its banners, and at the end the player really wears the armour, in your colours.

### Banners
- The Banners tab also makes those of your **Keshin**, **totems** (their name banner) and **armours** (ARMED banner). Their sheet has a "Banner" box with "✎ Customise the banner".
- **The game's lettering styles** in the fonts ("Keshin styles" group): Keshin (one per element), Totem and Armour, rebuilt from the game's real banners. Your copies' automatic banners use these styles.

### Techniques
- **The game's player everywhere**: a technique opens straight in the player (the game's real colours), paused on frame 0. The frame slider opens it too. The approximate preview only shows while loading.
- **Truer colours**: "Replace a colour everywhere" towards a pale colour (yellow → white) now also whitens the vertex and particle colours, like VRFW. New **brightness** setting for vertices and particles.
- **Shared effects** (speed lines…): can now be recoloured.
- **Long shot**: a copy of a long shot can be used in every duel.
- **Effect lights** (intensity): shown in the Atelier only for now (VRFW doesn't accept it in game yet).

### Kits
- **Draw the shop icon and the crest** (✎ Draw), like in the Atelier Maillots. The icon starts from the base kit's icon in the game.

### Fixes
- **Screen at 125 % (or more)**: the player opened offset, too small and impossible to close. Fixed.
- Switching appearance quickly could put the player in the wrong place, or leave the preview empty until you left and came back.
- The preview banner stayed on top of the player and in the other tabs. A technique stayed "still there" (playback bar, counters) after changing tab.
- Keshin sheet: the boxes stay on one line (Mountain…), and the unique effect no longer disappears after several bonuses.
- All new texts in English and Spanish.

## 2.0.6
- **Trash** (⚙ Settings): everything you deleted (projects, creations, kits) shows in a list with its date and size. "Restore" puts it back as before; "Delete permanently" erases it to free up space.
- **Empty the cache** (⚙ Settings): frees the space taken by what the Atelier has already read from the game and the mods. Your creations are not touched, and the cutscene pitch is kept.
- **"Edit" reopened a creation with the original colours** when it was made with an older version and its project had been removed from "To continue". Each creation now finds its project by itself, and that project no longer shows in "To continue" (it can no longer be thrown away by mistake).
- **Deleting a kit in My creations** did not remove it: it came back on reload. Fixed.
- **Armours on every player**: an armour made in the Atelier only had the model for one body type; on other players, the game didn't offer the armour. It now has a model for every body (like the game's armours). For an armour you already made: “Install” on your Keshin's card.
- **Summon by element**: a copied Keshin whose element you change (“Set the stats”) now has the summon of that element, like the game's own (fire → fire summon…). It uses the animations of a Keshin of that element with the same bones; if there is none, the original summon stays and the report says so.
- Re-making a Keshin with “Create” now keeps its stats (they used to be lost).
- **Complete English and Spanish**: sentences containing a name or a number (reports, confirmations, menus: “Preset “Red” applied”, “Selection: 3 parts”…) stayed in French. They are now translated, and the game's kit names follow the chosen language.

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
