# Wacayoub Panel

Panel Enigma2 (OpenATV 8, Python 3) qui installe, met à jour et supprime mes plugins, skins et scripts,
par catégorie, depuis la télécommande — dans l'esprit d'Emil's panel / AJPanel.

## Installation sur le récepteur

```sh
wget -O /tmp/wp.ipk https://github.com/wacayoub/WacayoubPanel/releases/download/packages/enigma2-plugin-extensions-wacayoubpanel_1.4.0_all.ipk
opkg install /tmp/wp.ipk && init 4; sleep 2; init 3
```

Ensuite : **Menu > Plugins > Wacayoub Panel**.

## Touches

| Touche | Action |
|---|---|
| Haut / Bas | catégorie ou élément |
| Droite / OK | entrer dans la liste ; OK = installer / mettre à jour (déjà à jour : réinstaller ou supprimer) |
| Gauche / Exit | revenir aux catégories |
| Rouge | supprimer |
| Vert | installer / mettre à jour |
| Jaune | relire le feed + mettre à jour les listes OpenATV (`opkg update`) |
| Bleu | tout mettre à jour |
| MENU | rechercher (nom, paquet ou description ; accents ignorés) — EXIT efface la recherche |

## Interface

Icônes par catégorie et par plugin, badges d'état (installé, mise à jour, non installé) et trois jauges rondes
en direct : **CPU** (avec la température), **RAM** et **stockage**, rafraîchies toutes les 2 secondes.
Les images sont générées par `tools/make_icons.py` (glyphes [Lucide](https://lucide.dev), licence ISC, Lucide Contributors).

## Mes outils

Première catégorie : tous mes plugins installés (IPToSat Pro, EPG Manager, BOP 2, IPAudio, Salaat NEO…)
réunis au même endroit. **OK** les ouvre directement ; on revient au panel en les fermant.

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
