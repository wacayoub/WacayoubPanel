#!/bin/sh
# Wacayoub Panel - Vitesse du disque : écrit puis relit un fichier de test de 64 Mo (supprimé ensuite).
freemb() { set -- $(stat -f -c "%a %S" "$1" 2>/dev/null); echo $(( ${1:-0} * ${2:-0} / 1048576 )); }
for m in /media/hdd /media/usb /media/mmc; do grep -q " $m " /proc/mounts && D=$m && break; done
[ -z "$D" ] && { echo "Aucun disque monté sur /media/hdd ou /media/usb."; exit 0; }
F="$D/.wacayoub-speedtest"
echo "=== Vitesse de $D ==="
FREE=$(freemb "$D")
[ "$FREE" -lt 100 ] && { echo "Pas assez de place ($FREE Mo)."; exit 0; }
t1=$(date +%s); dd if=/dev/zero of="$F" bs=1M count=64 conv=fsync 2>/dev/null; t2=$(date +%s)
w=$((t2-t1)); [ $w -lt 1 ] && w=1
echo "Écriture : environ $((64/w)) Mo/s"
sync; echo 3 > /proc/sys/vm/drop_caches 2>/dev/null
t1=$(date +%s); dd if="$F" of=/dev/null bs=1M 2>/dev/null; t2=$(date +%s)
r=$((t2-t1)); [ $r -lt 1 ] && r=1
echo "Lecture  : environ $((64/r)) Mo/s"
rm -f "$F"
[ $((64/w)) -lt 5 ] && echo "Lent : enregistrer une chaîne HD peut saccader." || echo "OK pour enregistrer et lire en HD."
exit 0
