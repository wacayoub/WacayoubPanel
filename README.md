# Wacayoub Panel

Panel Enigma2 (OpenATV 8, Python 3) qui installe, met à jour et supprime mes plugins, skins et scripts,
par catégorie, depuis la télécommande — dans l'esprit d'Emil's panel / AJPanel.

## Installation sur le récepteur

```sh
wget -O /tmp/wp.ipk https://github.com/wacayoub/WacayoubPanel/releases/download/packages/enigma2-plugin-extensions-wacayoubpanel_1.10.0_all.ipk
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

## Fiche détail et compatibilité

**INFO ouvre la fiche du plugin** (OK sert à cocher), avec un aperçu en image (`feed/previews/`),
la description, les versions (feed et installée) et les vérifications de compatibilité :

- **Python** : version du récepteur comparée au minimum du plugin ; les paquets Python 2 du feed ne sont jamais proposés.
- **Appareil** : modèle détecté (ex. Vu+ Zero 4K) ; un paquet construit pour un autre modèle est bloqué.
- **Écran** : les skins Full HD sont bloqués sur une interface HD.

Dans la fiche : **Vert** installe / met à jour, **Rouge** supprime, **EXIT** revient à la liste.
Un élément incompatible affiche « Incompatible : … » et ne peut pas être installé.

## Interface

Icônes par catégorie et par plugin, badges d'état (installé, mise à jour, non installé) et trois jauges rondes
en direct : **CPU** (avec la température), **RAM** et **stockage**, rafraîchies toutes les 2 secondes.
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
et WireGuard VPN (code compilé, impossible à vérifier).

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
