#!/bin/sh
# Wacayoub Panel - Info système (lecture seule, ne change rien)
echo "=== Récepteur ==="
echo "Modèle : $(cat /etc/hostname 2>/dev/null)"
grep -E "^(distro|version|imageversion|imagebuild)=" /etc/image-version 2>/dev/null
echo "Allumé depuis : $(uptime | sed 's/.*up \([^,]*\),.*/\1/')"
echo
echo "=== Mémoire et place ==="
free | awk 'NR==2{printf "RAM : %d Mo utilisés / %d Mo\n",$3/1024,$2/1024}'
python3 -c "import os;s=os.statvfs('/');print('Flash libre : %d Mo / %d Mo'%(s.f_bavail*s.f_frsize//1048576,s.f_blocks*s.f_frsize//1048576))"
echo
echo "=== Skin actif ==="
grep "^config.skin.primary_skin=" /etc/enigma2/settings 2>/dev/null | cut -d= -f2
echo
echo "=== Mes paquets installés ==="
opkg list-installed | grep -E "satiptvbridge|epgmanager|bop2|iptvbouquetai|ipaudio|salaatneo|metrixneo|neoweather|neoconnect|orbitai|novaorbit|osappletv|wacayoubpanel"
exit 0
