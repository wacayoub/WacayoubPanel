#!/bin/sh
# Wacayoub Panel - Supprimer le swap créé par le panel.
echo "=== Supprimer le swap ==="
N=0
for F in /media/hdd/wacayoub.swap /media/usb/wacayoub.swap; do
	[ -f "$F" ] || continue
	swapoff "$F" 2>/dev/null
	rm -f "$F"
	sed -i "\#^$F #d" /etc/fstab
	echo "Supprimé : $F"; N=1
done
[ $N = 0 ] && echo "Aucun swap créé par le panel."
exit 0
