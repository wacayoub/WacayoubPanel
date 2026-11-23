#!/bin/sh
# Wacayoub Panel - Info disques : place, système de fichiers et santé SMART (ne change rien).
freemb() { set -- $(stat -f -c "%a %S" "$1" 2>/dev/null); echo $(( ${1:-0} * ${2:-0} / 1048576 )); }
sizemb() { set -- $(stat -f -c "%b %S" "$1" 2>/dev/null); echo $(( ${1:-0} * ${2:-0} / 1048576 )); }
echo "=== Disques ==="
grep -E " /media/" /proc/mounts | grep -vE "tmpfs|autofs|^/dev/root" | while read dev mnt fs rest; do
	echo
	echo "$mnt  ($dev, $fs)"
	T=$(sizemb "$mnt"); L=$(freemb "$mnt")
	[ "$T" -gt 0 ] && echo "  Taille $T Mo  ·  libre $L Mo ($(( L * 100 / T ))% libre)"
	d=$(echo "$dev" | sed 's/[0-9]*$//')
	case "$d" in /dev/sd*)
		if command -v smartctl >/dev/null; then
			H=$(smartctl -H "$d" 2>/dev/null | grep -iE "overall-health|Health Status" | head -1 | cut -d: -f2 | tr -d ' ')
			[ -n "$H" ] && echo "  Santé SMART : $H"
			T=$(smartctl -A "$d" 2>/dev/null | awk '/Temperature_Celsius/{print $10}')
			[ -n "$T" ] && echo "  Température disque : $T °C"
			R=$(smartctl -A "$d" 2>/dev/null | awk '/Reallocated_Sector_Ct/{print $10}')
			[ -n "$R" ] && { [ "$R" -gt 0 ] && echo "  ATTENTION : $R secteurs réalloués, sauvegardez vos fichiers" || echo "  Secteurs défectueux : 0"; }
		fi;;
	esac
done
grep -q " /media/" /proc/mounts || echo "Aucun disque ni clé USB monté."
exit 0
