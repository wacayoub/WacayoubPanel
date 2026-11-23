# Wacayoub Panel

Panel Enigma2 (OpenATV 8, Python 3) qui installe, met à jour et supprime mes plugins, skins et scripts,
par catégorie, depuis la télécommande — dans l'esprit d'Emil's panel / AJPanel.

## Installation sur le récepteur

```sh
wget -O /tmp/wp.ipk https://github.com/wacayoub/WacayoubPanel/releases/download/packages/enigma2-plugin-extensions-wacayoubpanel_2.5.3_all.ipk
opkg install /tmp/wp.ipk && init 4; sleep 2; init 3
```

Ensuite : **Menu > Plugins > Wacayoub Panel**.

## Touches

| Touche | Action |
|---|---|
| Haut / Bas | catégorie ou élément |
| Droite / OK | entrer dans la liste ; **OK = cocher / décocher** (sélection pour installer plusieurs éléments) ; dans Mes outils, OK ouvre le plugin |
| INFO | fiche de l'élément (aperçu, compatibilité, versions, description) |
| Gauche / Exit | revenir aux catégories |
| Rouge | supprimer (ou vider la sélection s'il y en a une) |
| Vert | installer / mettre à jour (ou installer toute la sélection, dépendances comprises) |
| Jaune | relire le feed + mettre à jour les listes OpenATV (`opkg update`) |
| Bleu | tout mettre à jour |
| 0 | filtrer par source : Wacayoub, OpenATV, Universel, OpenPLi, OpenViX, OpenBH, EGAMI, OpenHDF (puis tout) |
| MENU | rechercher (nom, paquet ou description ; accents ignorés) — EXIT efface la recherche |

## Accueil (v2.3)

Le panel s'ouvre sur un tableau de bord : bonjour, modèle, image, durée allumé, réseau, tuners et softcam ; quatre jauges
(température, CPU, RAM, stockage) ; une bande d'**alertes** classées par importance (température, plantages récents, système plein,
heure fausse, opkg bloqué, EPG vide, softcam arrêté, Internet / DNS, mises à jour) ; trois badges d'état ; huit tuiles
(Réparer, Addons, Softcam, Skins, Mes outils, Mon récepteur, DNS, Images).
OK sur une alerte ouvre le bon outil, OK sur une tuile ouvre la catégorie. ROUGE Fixo, VERT Bilan santé, JAUNE actualiser,
BLEU tout mettre à jour (mes paquets, OpenATV et autres images), MENU rechercher, EXIT quitter.

## Fixo (v2.4)

ROUGE sur l'accueil, une alerte « plantage », ou la première ligne de **Réparer**. Fixo :

1. met à jour les listes de paquets et relit le feed du panel **sur Internet** (avec les règles en ligne `feed/doctor-rules.json`) ;
2. lit les rapports de plantage d'Enigma2 (`/home/root/logs`, disques), trouve l'erreur Python et le plugin en cause
   (dans la trace, sinon les plugins installés ou modifiés juste avant le plantage) ;
3. propose une réparation, confirmée avant de s'exécuter : installer le module Python manquant, mettre à jour le plugin si le feed
   a une version plus récente, le réinstaller si ses fichiers sont abîmés, lancer l'outil adapté (Flash pleine, Heure fausse…),
   ou le désactiver (mis de côté dans `/home/root/wacayoub-quarantine`, réactivable) s'il plante encore et encore ;
4. archive ensuite les rapports réparés dans `/home/root/logs/wacayoub-archive` (rien n'est effacé).

Un plantage plus ancien que la dernière mise à jour du plugin est marqué « sans doute corrigé ». Les règles en ligne ne peuvent
choisir qu'entre ces réparations (liste fixe) et sont vérifiées par `tools/build_feed.py`.

### Garde (v2.4.3)

Fixo et l'accueil surveillent aussi ce qu'un malware ou un installateur tiers change :

- **Sources de paquets** : chaque ligne `src` de `/etc/opkg/*.conf` doit pointer vers OpenATV (feeds2.mynonpublic.com)
  ou oe-alliance. Une autre source donne une alerte rouge ; VERT propose de la désactiver (la ligne est mise en commentaire)
  ou de la garder.
- **Fichiers système** : scripts de démarrage (`/etc/init.d`, `/etc/rc*.d`, `/etc/profile.d`), tâches planifiées (cron),
  comptes et mots de passe, clés SSH, `inetd.conf`, `hosts`, `ld.so.preload`… sont comparés à une photo prise la première fois
  (`/home/root/wacayoub-garde.json`). Un changement fait par opkg pendant l'installation d'un paquet est accepté tout seul ;
  tout autre changement reste en rouge jusqu'à ce que tu l'acceptes (VERT), BLEU montre le fichier.
  `/home/root/wacayoub-garde-extra.txt` (un chemin par ligne) ajoute des fichiers à surveiller sur ce récepteur.
- **Blocages** : `garde-gel.sh`, lancé au démarrage de l'interface, repère Enigma2 figé dans un pilote (rapport du noyau
  « blocked for more than 120 seconds », ou Enigma2 bloqué 4 minutes sans réponse de l'interface web). Il écrit un rapport
  `/home/root/logs/wacayoub-gel-*.log` et redémarre le récepteur. Le fichier `/home/root/wacayoub-gel-off` coupe le
  redémarrage automatique (rapport seulement). Au retour, l'accueil et Fixo affichent le blocage.

## Wacayoub Chaînes (plugin à part, v1.2)

Organiser les chaînes : **Outils & Infos → Wacayoub Chaînes** dans le panel, puis Extensions → Wacayoub Chaînes.
Bouquets à gauche, chaînes à droite (numéro, picon, fournisseur, satellite, HD), **20 lignes par page**. Code : `src/WacayoubChaines`.

| Touche | Bouquets (gauche) | Chaînes (droite) |
|---|---|---|
| OK | ouvrir | marquer / démarquer (plusieurs) |
| ROUGE | supprimer le bouquet | supprimer les chaînes marquées |
| VERT | enregistrer | enregistrer |
| JAUNE | déplacer le bouquet (HAUT / BAS) | déplacer les chaînes marquées en bloc (HAUT / BAS, GAUCHE / DROITE = page) |
| BLEU | renommer | déplacer ou copier vers un autre bouquet (ou un nouveau) |
| MENU | outils intelligents | outils intelligents |
| 0 | marquer plusieurs bouquets | sélection continue : HAUT / BAS marquent en passant |
| INFO | rechercher une chaîne dans tous les bouquets | |

**Déplacer facilement** :
- JAUNE = mode déplacement (barre orange) : HAUT / BAS = 1 ligne, GAUCHE / DROITE ou CH+ / CH- = 1 page (20),
  chiffres = aller directement à la position n°, VERT = tout en haut, BLEU = tout en bas, MENU = juste après un séparateur,
  OK / JAUNE = poser, ROUGE = annuler le déplacement. Marche aussi pour les bouquets (gauche).
- MENU → Déplacer… : tout en haut, tout en bas, position n°…, après un séparateur…, vers un autre bouquet (au début ou à la fin,
  déplacer ou copier), **couper / copier puis coller** n'importe où (même dans un autre bouquet), échanger 2 chaînes,
  inverser l'ordre des chaînes marquées.
- Chiffres hors déplacement : aller à la chaîne n° (droite) ou au bouquet n° (gauche).
- MENU → Annuler la dernière action : retour arrière pas à pas (30 actions) avant d'enregistrer.

**Sélection multiple** : bouquets marqués (touche 0) → ROUGE les supprime, JAUNE les déplace ensemble, BLEU les **fusionne**
(sans doublons, en gardant ou supprimant les anciens), MENU les trie ou les nettoie tous. Chaînes : OK, sélection continue (0),
ou MENU → sélection par nom, HD / 4K, SD, IPTV, satellite, inverser.

Outils intelligents : trier de A à Z ou 4K / HD d'abord (dans chaque section entre séparateurs), supprimer les doublons, supprimer
les chaînes mortes (absentes de la liste des chaînes), **bouquets par thème** (★ Sport, ★ Info, ★ Enfants, ★ Documentaires,
★ Musique, ★ Cinéma & Séries, ★ Religion, créés en haut sans toucher aux autres bouquets), supprimer les bouquets vides,
nouveau bouquet, séparateur, renommer une chaîne, TV / Radio.

Rapide : un bouquet n'est lu qu'à son ouverture (965 bouquets en 1,4 s sur l'Octagon), picons jusqu'à 400 chaînes par bouquet.
Rien n'est écrit avant VERT ; chaque enregistrement garde l'ancienne version dans `/home/root/wacayoub-chaines`
(5 dernières) et **MENU → Annuler le dernier enregistrement** la remet. La liste des chaînes d'Enigma2 est rechargée aussitôt.

## Mises à jour rapides (v2.5.1)

- La sortie d'opkg n'arrive plus en entier dans la console : seulement « [3] Mise a jour : paquet » (journal complet dans
  `/tmp/wacayoubpanel/opkg.log`). Avant, la barre de progression des gros téléchargements noyait Enigma2, qui restait figé
  plusieurs minutes. 21 paquets : 33 s au lieu de plus de 13 min bloquées.
- **Tout mettre à jour** ne prend plus les listes de chaînes (`enigma2-plugin-settings-*`, elles remplaceraient tes chaînes)
  ni les picons (60-80 Mo chacun, à mettre à jour à part dans Picons).
- Si des plugins OpenATV sont mis à jour et que le cœur `enigma2` du récepteur est plus ancien que le feed, il est mis à jour
  avec eux (sinon ServiceApp, PositionerSetup… ne se chargent plus).
- La console du panel a son propre écran, lisible sur tous les skins (texte clair sur fond opaque).
- v2.5.2 : un paquet « half-installed » (installation ratée) n'est plus proposé en mise à jour, et les milliers de
  conflits de fichiers entre paquets de picons tiennent en une ligne au lieu de noyer la console.

## Panel plus rapide (v2.5.3)

- Catalogue OpenATV gardé en mémoire et dans `/tmp/wacayoubpanel/atv-cache.json` : relu seulement après un `opkg update`
  (Octagon : 1,1 s → 0,001 s, 0,08 s après un redémarrage de l'interface). Pareil pour les feeds des autres images et les
  versions du feed (Fixo, mises à jour).
- Liste des paquets installés relue seulement quand opkg a changé quelque chose ; état de chaque paquet calculé une fois.
- Dans les catégories, la liste suit les touches un instant après (plus d'attente à chaque touche).
- Fixo ne lance `opkg update` que si les listes ont plus de 6 h ; Garde vérifie les fichiers système au plus toutes les 30 s.

## Partage LAN (v2.5)

**Mon récepteur → Partage LAN** copie les chaînes, l'IPTV et la softcam d'un récepteur à l'autre sur le même réseau :

1. sur le premier : **Envoyer**, choisir quoi (tout, chaînes + IPTV, chaînes, IPTV, softcam) ; un code à 8 chiffres s'affiche ;
2. sur le second : **Recevoir** ; il trouve le premier tout seul (diffusion sur le réseau local), choisir puis taper le code.

- **Chaînes** : `lamedb`, `lamedb5` et les bouquets satellite (avec leurs sous-bouquets). Les bouquets satellite du receveur
  sont remplacés, ses bouquets IPTV restent.
- **IPTV** : les bouquets dont la plupart des chaînes sont des flux, ajoutés à la liste, plus les réglages des plugins IPTV
  (IPTV Bouquet AI, BouquetMakerXtream, XStreamity, EStalker, JediEPGXtream).
- **Softcam** : `/etc/tuxbox/config`, `/usr/keys`, `/etc/CCcam.cfg` (pas les programmes : la même softcam doit être installée),
  puis la softcam est redémarrée.

Sécurité : l'envoi ne tourne que tant que l'écran est ouvert (10 minutes au plus) et pour un seul transfert ; seules les adresses
du réseau local (192.168.x, 10.x, 172.16-31.x) sont servies ; le receveur doit prouver qu'il connaît le code avant de recevoir
quoi que ce soit, 3 codes faux arrêtent l'envoi ; le transfert est chiffré et contrôlé avec une clé tirée du code. Le receveur
n'écrit que des noms de fichiers connus dans ces dossiers et garde ce qu'il remplace dans `/home/root/wacayoub-p2p`
(3 derniers échanges) : **Annuler le dernier échange reçu** remet tout comme avant.

## Catégories (v2)

Tout est fusionné, mes plugins compris (source **Wacayoub**) :

| Catégorie | Contenu |
|---|---|
| **Installés** | tous les plugins installés qui ont une entrée de menu ; OK les ouvre |
| **Mon récepteur** | modèle, image, température, processeur, RAM, place, disques, réseau, DNS, durée allumé, tuners, softcam, skin |
| **Addons** | extensions (OpenATV, autres images, Wacayoub) |
| **Système** | plugins système |
| **Skins** | skins et packs de skins |
| **Softcam** | softcams du feed de l'image (vide si le feed n'en propose pas) |
| **Picons** | paquets de picons |
| **Settings** | listes de chaînes |
| **Panels** | panels (AJPanel, Wacayoub Panel…) |
| **Multiboot** | gestionnaires multiboot |
| **Feeds** | une ligne par source (Wacayoub, OpenATV, Universel, OpenPLi, OpenViX…) ; OK n'affiche que cette source |
| Communauté, Scripts | sélection vérifiée, scripts |
| **Réparer** | Bilan santé, Pas d'Internet, Pas d'image, Récepteur lent, Heure fausse, EPG vide, Flash pleine, opkg bloqué, Écran noir (skin), Plantages |
| **DNS** | DNS actuels et vitesse, Cloudflare, Google, Quad9, AdGuard, DNS automatique (retour arrière) |
| **Dépendances** | Tout, GStreamer, lecteurs vidéo, modules Python, audio, IPTV, archives (feed officiel OpenATV) |
| **Disque** | Info disques (SMART), vitesse, préparer les dossiers, créer / supprimer un swap |
| Images | images firmware (téléchargement seulement) |

Les outils Réparer / DNS / Dépendances / Disque sont mes scripts shell (`feed/scripts/`), vérifiés par sha256 avant de tourner.
Ceux marqués « lecture seule » ne changent rien. Les DNS passent par le fichier prévu par OpenATV (`/etc/enigma2/nameserversdns.conf`) ;
« DNS automatique » revient aux DNS de la box Internet. Le swap ne touche que son propre fichier `wacayoub.swap`.

## Softcams (OSCam, NCam)

La catégorie **Softcam** propose les builds officiels open source **OSCam** (latest, emu, pcscd) et **NCam** des feeds OpenViX/OpenPLi,
compilés pour le même processeur (les binaires fermés CCcam/mgcamd ne sont pas proposés). À l'installation, le panel :

1. vérifie l'empreinte du paquet ;
2. **adapte ses dépendances à OpenATV** (`ipkfix.py`) : retire `softcam-support` (cadre softcam d'OpenViX/OpenPLi, en conflit avec
   `initscripts` d'OpenATV qui a son propre système) et remplace `libusb1` par `libusb-1.0-0` ; le binaire, le script et les configs ne changent pas ;
3. sauvegarde `/etc/tuxbox/config` dans `/tmp/wacayoubpanel/softcam-config-backup.tgz` ;
4. installe (les bibliothèques manquantes, ex. `libdvbcsa1`, viennent du feed OpenATV) puis **lance le binaire** (`-V`) :
   s'il ne démarre pas sur cette image, il est désinstallé aussitôt.

Le softcam reste sur « None » : on l'active dans **Menu > Configuration > Softcam**. Script **Softcam Fix** (catégorie Scripts) :
arrête le softcam, vide les caches (`/tmp/.oscam`, `/tmp/.ncam`, `ecm.info`) et les PID restés, répare droits et lien
`/etc/init.d/softcam`, puis le relance. Les configurations ne sont jamais modifiées.

## Fiche détail et compatibilité

**INFO ouvre la fiche du plugin** (OK sert à cocher), avec un aperçu en image (`feed/previews/`),
la description, les versions (feed et installée) et les vérifications de compatibilité :

- **Python** : version du récepteur comparée au minimum du plugin ; les paquets Python 2 du feed ne sont jamais proposés.
- **Appareil** : modèle détecté (ex. Vu+ Zero 4K) ; un paquet construit pour un autre modèle est bloqué.
- **Écran** : les skins Full HD sont bloqués sur une interface HD.

Dans la fiche : **Vert** installe / met à jour, **Rouge** supprime, **EXIT** revient à la liste.
Un élément incompatible affiche « Incompatible : … » et ne peut pas être installé.

## Interface

Icônes par catégorie et par plugin, badges d'état (installé, mise à jour, non installé) et quatre jauges rondes
en direct : **température** (bleu < 70 °C, jaune 70-84 °C, rouge ≥ 85 °C), **CPU**, **RAM** et **stockage**, rafraîchies toutes les 2 secondes.
Les images sont générées par `tools/make_icons.py` (glyphes [Lucide](https://lucide.dev), licence ISC, Lucide Contributors).

## Mes outils

Première catégorie : tous mes plugins installés (IPToSat Pro, EPG Manager, BOP 2, IPAudio, Salaat NEO…)
réunis au même endroit. **OK** les ouvre directement ; on revient au panel en les fermant.

## Autres images (OpenPLi, OpenViX, OpenBH, OpenHDF, OpenSPA, EGAMI)

Les plugins et skins des feeds d'autres images sont **fusionnés** avec ceux d'OpenATV et les miens dans les listes **Toutes · Extensions / Système / Skins** ; chaque ligne affiche sa source en couleur (Wacayoub, OpenATV, OpenPLi, OpenViX, OpenBH, OpenHDF, EGAMI, OpenSPA). Un outil présent dans plusieurs images est marqué **Universel** (sans nom d'image) ; sa fiche liste les images qui le proposent. Feeds lus en direct
(`extfeeds.py`, rafraîchis une fois par jour ou avec Jaune). EGAMI est lu aussi, mais presque tout y est déjà dans le feed OpenATV. OpenHDF ne publie pas tous les modèles (rien pour le Vu+ Zero 4K) ; le feed OpenSPA refuse actuellement l'accès extérieur (il apparaîtra s'il s'ouvre).
Règles de sécurité :

- paquets « all » (Python, skins) et paquets du même processeur ; ces derniers sont ouverts avant l'installation (`ipkcheck.py`) et **refusés s'ils contiennent du code binaire ou du Python compilé sans source** (ex. EGAMI Permanent Clock) ; les composants système (réseau, gestion logiciels, boot, CI) ne sont jamais proposés ;
- ces feeds ne sont **jamais ajoutés à opkg** : le panel télécharge le fichier, vérifie son empreinte (SHA256, ou MD5 pour OpenPLi)
  puis fait `opkg install <fichier>` ; les dépendances viennent uniquement du feed de l'image ;
- un paquet est bloqué si une dépendance manque dans l'image, s'il est en Python 2, ou s'il existe déjà dans le feed OpenATV ;
- la fiche et la confirmation affichent « non testé sur OpenATV ».

## Images

Le panel détecte le récepteur (ici Vu+ Zero 4K) et liste toutes les images disponibles pour lui :
**OpenATV, OpenPLi, OpenViX, OpenBH, OpenSPA** (mêmes sources que le Flash Manager d'OpenATV).
**OK** télécharge le `.zip` (vérifié) dans `/media/hdd/images` ; **Rouge** supprime le fichier.
Le panel ne flashe jamais : le flash se fait ensuite avec **Menu > Flash Manager > Images téléchargées**.

## Communauté (sélection vérifiée)

Plugins communautaires connus, installés depuis le **feed officiel OpenATV** (versions plus récentes que les releases GitHub).
Chaque paquet est revu par `tools/verify_community.py` : téléchargement, sha256 = liste du feed, recherche de commandes à risque
(téléchargement envoyé à un shell, base64 exécuté, telnet/ssh, mots de passe, crontab, pare-feu, code obfusqué) et refus du code fermé (compilé).
Résultat détaillé : [feed/COMMUNITY-REVIEW.md](feed/COMMUNITY-REVIEW.md). Refusés : AJPanel (change le mot de passe root, code obfusqué)
WireGuard VPN (code compilé, impossible à vérifier) et E2iPlayer (code compilé contenant des adresses avec mot de passe).

Les installateurs « wget … | sh » de sites tiers ne sont jamais utilisés.

### Plugins Ciefp

Six plugins de [Ciefp](https://github.com/ciefp) sont aussi dans Communauté : Satellite XML Editor, Signal Info, Picon Manager,
ScreenGrab, Bootlogo et Settings Downloader. Ciefp ne publie ni paquet ni licence, donc son code n'est pas copié ici :
chaque petit paquet du feed télécharge l'archive du plugin chez Ciefp, à la version revue (commit), la refuse si son
sha256 a changé, et installe le dossier du plugin sans fichiers `.pyc`. Revue : `tools/verify_ciefp.py`,
résultat dans [feed/CIEFP-REVIEW.md](feed/CIEFP-REVIEW.md). Refusés : E2 Editor, OSCam Editor, EPG Info et Vibes
(ils se mettent à jour eux-mêmes avec un script téléchargé et lancé, « wget … | /bin/sh »).

### LinuxsatPanel (non vérifié)

[LinuxsatPanel](https://github.com/Belfagor2005/LinuxsatPanel) (Lululla, licence GPL-3) est ajouté à la demande, marqué
**non vérifié** : le panel lui-même est revu de la même façon (version figée, sha256, pas de code compilé, rien hors de son
dossier), mais les addons qu'il propose s'installent avec les scripts d'autres sites (« wget … | sh ») que Wacayoub
ne vérifie pas. EliesatPanel n'est pas ajouté : son installateur remplace AJPanel par une copie modifiée et ajoute un
feed opkg permanent (`/etc/opkg/eliesat-feed.conf`).

## Paquets OpenATV

En plus de mes plugins, le panel montre les paquets du feed de l'image (lus dans `/var/lib/opkg/lists`)
dans 5 catégories : **ATV · Extensions**, **ATV · Système**, **ATV · Skins**, **ATV · Listes chaînes** (settings)
et **ATV · Picons**. Ils s'installent avec `opkg install`. Les listes sont mises à jour à l'ouverture si elles
ont plus d'un jour, ou avec la touche Jaune. « Tout mettre à jour » (Bleu) ne touche que mes paquets.

## Le feed

- `feed/index.json` : catégories, éléments, et pour chaque paquet sa version, son URL de téléchargement,
  sa taille et son **sha256** (le panel refuse un fichier dont le sha256 ne correspond pas).
- Les `.ipk` sont des fichiers de la release GitHub [`packages`](https://github.com/wacayoub/WacayoubPanel/releases/tag/packages)
  (le skin Orbit AI dépasse la limite de 100 Mo de git). EPG Manager pointe vers sa propre release.
- Les scripts sont dans `feed/scripts/`.

## Publier une nouvelle version

1. Mettre le nouveau `.ipk` dans `packages/` (dossier local, non suivi par git).
2. `python tools/scan.py packages/*.ipk` (secrets, identifiants IPTV, marqueurs de malware).
3. `python tools/build_feed.py` (reconstruit le panel et `feed/index.json`).
4. `gh release upload packages packages/<fichier>.ipk` puis commit + push de `feed/index.json`.
