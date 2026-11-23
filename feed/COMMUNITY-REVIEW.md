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
| [IMDb](https://github.com/oe-alliance/enigma2-plugins) | V1.3-git369+f0df8e70+f0df8e7f8e-r0 | 74 Ko | 34 | 0 | OK |
| [TMDB](https://github.com/oe-alliance/enigma2-plugins) | V1.0.5-git150+d8d47330+d8d47335f9-r0 | 195 Ko | 48 | 0 | OK |
| [File Commander](https://github.com/openatv/enigma2) | 8.0.1+git36322+b4ac3bd0+b4ac3bd50a-r1 | 89 Ko | 7 | 0 | OK |
| [AutoTimer](https://github.com/oe-alliance/enigma2-plugins) | V1.0-git1140+077bc9d0+077bc9d4db-r0 | 379 Ko | 70 | 0 | OK |
| [EPGRefresh](https://github.com/oe-alliance/enigma2-plugins) | V1.0-git416+71911ad0+71911ad38e-r0 | 92 Ko | 40 | 0 | OK |
| [SeriesPlugin](https://github.com/betonme/e2openplugin-SeriesPlugin) | V5.9.8-git79+38e43950+38e43953de-r0 | 143 Ko | 49 | 0 | OK |
| [EnhancedMovieCenter](https://github.com/oe-alliance/enigma2-plugins) | 4.0.+git1804+a3769660+a376966b06-r0 | 687 Ko | 183 | 0 | OK |
| [CoolTVGuide](https://www.opena.tv) | Coolman_V8.0_py3 | 2263 Ko | 168 | 0 | OK |
| [xtraEvent](https://www.opena.tv) | 6.806 | 757 Ko | 70 | 0 | OK |
| [SetPicon](https://github.com/oe-alliance/enigma2-plugins) | V1.1-git139+0ce5e4f0+0ce5e4fa06-r0 | 42 Ko | 11 | 0 | OK |
| [BootlogoSwitcher](https://github.com/stein17) | 1.0+git1513+3ca5d510+3ca5d51a06-r0 | 63 Ko | 18 | 0 | OK |
| [E2iPlayer](https://github.com/oe-mirrors/e2iplayer) | 2026.11.23.01-git6436+646ebdf0+646ebdff6e-r0 | 21908 Ko | 3121 | 0 | REFUSÉ : URL with user:password : data:./usr/lib/enigma2/python/Plugins/Extensions/IPTVPlayer/components/iptvconfig.pyc; URL with user:password : data:./usr/lib/enigma2/python/Plugins/Extensions/IPTVPlayer/hos |
| [EStalker](https://github.com/kiddac/E-Stalker) | 1.55-20261024-git72+f5bc2040+f5bc204b9e-r0 | 3321 Ko | 498 | 0 | OK |
| [JediEPGXtream](https://github.com/kiddac/Jedi_EPG_Xtream) | 2.13-20240805-git25+7cf0d7d0+7cf0d7db6c-r3 | 265 Ko | 169 | 0 | OK |
| [XCplugin Forever](https://github.com/Belfagor2005/xc_plugin_forever) | 2.2 | 994 Ko | 155 | 0 | OK |
| [Internet Speedtest](https://www.opena.tv) | 1.8 | 701 Ko | 33 | 0 | OK |
| [WeatherPlugin](https://github.com/oe-alliance/enigma2-plugins) | V1.0-git131+cb2a2ea0+cb2a2eafd4-r0 | 73 Ko | 42 | 0 | OK |
| [WorldCam](https://github.com/Belfagor2005/WorldCam) | V7.4-git567+0a0532f0+0a0532fd24-r0 | 6416 Ko | 498 | 0 | OK |
| [ApSatTV](https://github.com/Belfagor2005) | 1.5 | 761 Ko | 235 | 0 | OK |
| [mmPicons](https://github.com/Belfagor2005) | 1.6 | 1355 Ko | 241 | 0 | OK |
| [Chocholousek Picons](https://github.com/s3n0/e2plugins) | - | 0 Ko | - | 0 | REFUSÉ : absent du feed OpenATV |
| [Horoscope](https://github.com/Belfagor2005) | 1.2 | 2877 Ko | 198 | 0 | OK |
| [AGlare FHD](https://github.com/Belfagor2005) | 8.6 | 13262 Ko | 1346 | 0 | OK |
| [Maxy FHD](https://www.opena.tv) | 1.2 | 5705 Ko | 744 | 0 | OK |
