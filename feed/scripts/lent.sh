#!/bin/sh
# Wacayoub Panel - Récepteur lent : libère la mémoire et montre ce qui consomme.
echo "=== Récepteur lent ==="
before=$(awk '/MemAvailable/{print int($2/1024)}' /proc/meminfo)
sync; echo 3 > /proc/sys/vm/drop_caches 2>/dev/null
rm -rf /tmp/wacayoubpanel/prev /tmp/wacayoubpanel/*.ipk 2>/dev/null
after=$(awk '/MemAvailable/{print int($2/1024)}' /proc/meminfo)
echo "RAM libre : $before Mo -> $after Mo"
echo "Charge : $(cut -d' ' -f1-3 /proc/loadavg)"
echo
echo "Processus qui utilisent le plus de mémoire :"
for p in /proc/[0-9]*; do
	n=$(cat $p/comm 2>/dev/null); r=$(awk '/VmRSS/{print $2}' $p/status 2>/dev/null)
	[ -n "$r" ] && echo "$r $n"
done | sort -rn | head -6 | awk '{printf "  %-20s %d Mo\n", $2, $1/1024}'
grep -q "^/" /proc/swaps 2>/dev/null && echo "Swap actif." || echo "Pas de swap : sur un petit récepteur, voir catégorie Disque > Créer un swap."
exit 0
