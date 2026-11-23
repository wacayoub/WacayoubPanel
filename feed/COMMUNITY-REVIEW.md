# Sélection communauté — revue du 2026-11-23

Chaque paquet vient du feed officiel OpenATV 8.0.1 (vuzero4k). Vérifié : sha256 = liste du feed,
aucune commande à risque dans les scripts d'installation ni dans le code (téléchargement envoyé à un shell,
base64 exécuté, telnet/ssh, mots de passe, crontab, pare-feu), aucun marqueur du malware connu.

| Plugin | Version vérifiée | Taille | Fichiers | Binaires ELF | Résultat |
|---|---|---|---|---|---|
| [XStreamity](https://github.com/kiddac/XStreamity) | 5.75-20261108-git649+8353ba30+8353ba3c15-r1 | 8643 Ko | 615 | 0 | OK |
| [BouquetMakerXtream](https://github.com/kiddac/Bouquet_Maker_Xtream) | 1.82-20261108-git234+cad9baa0+cad9baaaf6-r4 | 4141 Ko | 288 | 0 | OK |
| [YouTube](https://github.com/Taapat/enigma2-plugin-youtube) | git1296+15a7fba0+15a7fba89b-r0 | 176 Ko | 75 | 0 | OK |
| [AJPanel](https://github.com/AMAJamry/AJPanel) | v10.8.6 | 528 Ko | 95 | 0 | REFUSÉ : changes passwords : ./usr/lib/enigma2/python/Plugins/Extensions/AJPan/plugin.py  (…bMa("echo root:NEW_PASSWORD | chpasswd\n", 0)    self.VVNDZz()   els…) |
| [WireGuard VPN](https://github.com/m4dhouse/Wireguard-Vpn) | 16.2 | 2833 Ko | 263 | 13 | REFUSÉ : code fermé (compilé), impossible à vérifier : usr/lib/enigma2/python/Plugins/Extensions/Wireguard/Nordvpn.so; code fermé (compilé), impossible à vérifier : usr/lib/enigma2/python/Plugins/Extensions/Wi |
| [OAWeather](https://github.com/oe-alliance/OAWeather) | 2.4-git165+273f3720+273f372e7f-r0 | 1283 Ko | 120 | 0 | OK |
| [SubsSupport](https://github.com/oe-mirrors/subssupport) | V2.0.0-git213+2ea6bd4-r0 | 764 Ko | 428 | 0 | OK |
| [IMDb](https://github.com/oe-alliance/enigma2-plugins) | V1.2-git367+aab57940+aab5794f1e-r0 | 74 Ko | 34 | 0 | OK |
| [TMDB](https://github.com/oe-alliance/enigma2-plugins) | V1.0.5-git150+d8d47330+d8d47335f9-r0 | 195 Ko | 48 | 0 | OK |
| [File Commander](https://github.com/openatv/enigma2) | 8.0.1+git36321+d31cb9a0+d31cb9aad3-r1 | 89 Ko | 7 | 0 | OK |
| [AutoTimer](https://github.com/oe-alliance/enigma2-plugins) | V1.0-git1138+8b7e54f0+8b7e54fd69-r0 | 379 Ko | 70 | 0 | OK |
| [EPGRefresh](https://github.com/oe-alliance/enigma2-plugins) | V1.0-git416+71911ad0+71911ad38e-r0 | 92 Ko | 40 | 0 | OK |
| [SeriesPlugin](https://github.com/betonme/e2openplugin-SeriesPlugin) | V5.9.8-git79+38e43950+38e43953de-r0 | 143 Ko | 49 | 0 | OK |
| [EnhancedMovieCenter](https://github.com/oe-alliance/enigma2-plugins) | 4.0.+git1804+a3769660+a376966b06-r0 | 687 Ko | 183 | 0 | OK |
| [CoolTVGuide](https://www.opena.tv) | Coolman_V8.0_py3 | 2263 Ko | 168 | 0 | OK |
| [xtraEvent](https://www.opena.tv) | 6.806 | 757 Ko | 70 | 0 | OK |
| [SetPicon](https://github.com/oe-alliance/enigma2-plugins) | V1.1-git139+0ce5e4f0+0ce5e4fa06-r0 | 42 Ko | 11 | 0 | OK |
| [BootlogoSwitcher](https://github.com/stein17) | 1.0+git1513+3ca5d510+3ca5d51a06-r0 | 63 Ko | 18 | 0 | OK |
