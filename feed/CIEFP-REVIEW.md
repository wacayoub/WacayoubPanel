# Plugins Ciefp — revue du 2026-11-23

Code de [Ciefp](https://github.com/ciefp), téléchargé chez lui à une version figée (commit) et vérifié par empreinte sha256.
Rien de son code n'est copié dans ce dépôt. Installé : le dossier du plugin, sans les fichiers .pyc.
Vérifié : aucun code compilé, aucune commande à risque (téléchargement envoyé à un shell, base64 exécuté,
telnet/ssh, mots de passe, crontab, pare-feu, code obfusqué), rien installé hors du dossier du plugin.

| Plugin | Version | Commit | Fichiers | Ce qu'il fait aussi | Résultat |
|---|---|---|---|---|---|
| [Ciefp E2 Editor](https://github.com/ciefp/CiefpE2editor) | 1.9.1 | 7bf3b7a (2026-10-28) | 31 | lance des commandes, télécharge des données | REFUSÉ : download piped into a shell : usr/lib/enigma2/python/Plugins/Extensions/CiefpE2editor/plugin_select_satellite.py  (…ng plugin...")         cmd = "wget -q --no-check-certificate https://raw.githubusercontent…) |
| [Ciefp Satellite XML Editor](https://github.com/ciefp/CiefpSatelliteXmlEditor) | 1.0 | 8ddad90 (2026-07-21) | 5 | - | OK |
| [Ciefp Signal Info](https://github.com/ciefp/CiefpSignalInfo) | 1.5 | 49c30dc (2026-09-21) | 13 | - | OK |
| [Ciefp Picon Manager](https://github.com/ciefp/CiefpPiconManager) | 1.0 | f9c0fd2 (2026-11-01) | 13 | lance des commandes | OK |
| [Ciefp ScreenGrab](https://github.com/ciefp/CiefpScreenGrab) | 1.5 | d8bc64d (2026-07-26) | 5 | - | OK |
| [Ciefp Bootlogo](https://github.com/ciefp/CiefpBootlogo) | 1.0 | 7ae3f96 (2026-08-15) | 4 | télécharge des données | OK |
| [Ciefp OSCam Editor](https://github.com/ciefp/CiefpOscamEditor) | 2.0.1 | 5bfcfca (2026-09-20) | 36 | lance des commandes, télécharge des données | REFUSÉ : download piped into a shell : usr/lib/enigma2/python/Plugins/Extensions/CiefpOscamEditor/plugin.py  (…ersion.txt" UPDATE_COMMAND = 'wget -q --no-check-certificate https://raw.githubusercontent…) |
| [Ciefp EPG Info](https://github.com/ciefp/CiefpEPGinfo) | 1.1 | f81a6e1 (2026-11-18) | 15 | lance des commandes, télécharge des données | REFUSÉ : download piped into a shell : usr/lib/enigma2/python/Plugins/Extensions/CiefpEPGinfo/plugin.py  (…ersion.txt" UPDATE_COMMAND = "wget -q --no-check-certificate https://raw.githubusercontent…) |
| [Ciefp Settings Downloader](https://github.com/ciefp/CiefpSettingsDownloader) | 1.0 | 79d3409 (2026-09-21) | 5 | télécharge des données | OK |
| [Ciefp Vibes](https://github.com/ciefp/CiefpVibes) | 1.1 | d8988b5 (2026-10-16) | 47 | lance des commandes, télécharge des données | REFUSÉ : download piped into a shell : usr/lib/enigma2/python/Plugins/Extensions/CiefpVibes/plugin.py  (…ersion.txt" UPDATE_COMMAND = "wget -q --no-check-certificate https://raw.githubusercontent…) |
