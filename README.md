# Wacayoub Panel

Panel Enigma2 (OpenATV 8, Python 3) qui installe, met à jour et supprime mes plugins, skins et scripts,
par catégorie, depuis la télécommande — dans l'esprit d'Emil's panel / AJPanel.

## Installation sur le récepteur

```sh
wget -O /tmp/wp.ipk https://github.com/wacayoub/WacayoubPanel/releases/download/packages/enigma2-plugin-extensions-wacayoubpanel_2.4.2_all.ipk
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

**Packs** (un bouton = plusieurs plugins, tous du feed officiel OpenATV) : IPTV (XStreamity, BouquetMakerXtream, EStalker,
JediEPGXtream, XCplugin Forever), EPG & Picons (xtraEvent, SetPicon, EPGRefresh, AutoTimer), Films & Séries (SubsSupport, IMDb,
TMDB, YouTube), Outils (BootlogoSwitcher, Internet Speedtest, WeatherPlugin, File Commander).
Les installateurs « wget … | sh » de sites tiers ne sont jamais utilisés.

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
