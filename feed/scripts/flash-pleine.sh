#!/bin/sh
# Wacayoub Panel - Flash pleine : vide les caches et vieux journaux, puis montre ce qui prend de la place.
freemb() { set -- $(stat -f -c "%a %S" "$1" 2>/dev/null); echo $(( ${1:-0} * ${2:-0} / 1048576 )); }
echo "=== Libérer de la place ==="
b=$(freemb /)
rm -rf /var/cache/opkg/* /tmp/wacayoubpanel/*.ipk /tmp/wacayoubpanel/prev 2>/dev/null
rm -f /home/root/logs/messages.[1-9] /var/log/*.gz /var/log/*.[1-9] 2>/dev/null
# keep the 3 newest crash logs
ls -t /home/root/logs/*crash*.log 2>/dev/null | tail -n +4 | while read f; do rm -f "$f"; done
a=$(freemb /)
echo "Libéré : $((a-b)) Mo  ·  libre maintenant : $a Mo"
echo
echo "Ce qui prend le plus de place :"
du -sk /usr/share/enigma2/* /usr/lib/enigma2/python/Plugins/Extensions/* /usr/share/enigma2/picon /picon 2>/dev/null | sort -rn | head -8 | awk '{printf "  %5d Mo  %s\n", $1/1024, $2}'
echo
echo "Conseil : supprimez les skins et plugins inutiles avec ROUGE, mettez les picons sur le disque."
exit 0
