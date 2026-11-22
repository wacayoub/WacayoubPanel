# Wacayoub Panel

Panel Enigma2 (OpenATV 8, Python 3) qui installe, met à jour et supprime mes plugins, skins et scripts,
par catégorie, depuis la télécommande — dans l'esprit d'Emil's panel / AJPanel.

## Installation sur le récepteur

```sh
wget -O /tmp/wp.ipk https://github.com/wacayoub/WacayoubPanel/releases/download/packages/enigma2-plugin-extensions-wacayoubpanel_1.0.4_all.ipk
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
| Jaune | relire le feed |
| Bleu | tout mettre à jour |

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
