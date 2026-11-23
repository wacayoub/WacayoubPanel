#!/bin/sh
# Wacayoub Panel - Préparer le disque : crée les dossiers habituels (movie, picon, epg, backup, images...).
for m in /media/hdd /media/usb; do grep -q " $m " /proc/mounts && D=$m && break; done
[ -z "$D" ] && { echo "Aucun disque monté sur /media/hdd ou /media/usb."; exit 0; }
echo "=== Dossiers sur $D ==="
for d in movie picon epg backup images timeshift logs; do
	if [ -d "$D/$d" ]; then echo "  $d : existe"; else mkdir -p "$D/$d" && echo "  $d : créé"; fi
done
echo "Pour mettre l'EPG sur le disque : Menu > Système > EPG > emplacement."
exit 0
