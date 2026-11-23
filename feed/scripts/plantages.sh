#!/bin/sh
# Wacayoub Panel - Plantages : résume les derniers rapports de plantage (ne change rien).
echo "=== Plantages ==="
L=$(ls -t /home/root/logs/*crash*.log /media/hdd/*crash*.log /media/usb/*crash*.log 2>/dev/null)
if [ -z "$L" ]; then echo "Aucun rapport de plantage. Tout va bien."; exit 0; fi
echo "$(echo "$L" | wc -l) rapport(s). Les 3 derniers :"
for f in $(echo "$L" | head -3); do
	echo
	echo "--- $(basename $f)"
	P=$(grep -o '/Plugins/[A-Za-z]*/[A-Za-z0-9_]*' "$f" | tail -1)
	[ -n "$P" ] && echo "Plugin en cause : $P"
	grep -E "Error|Exception" "$f" | grep -v "^\s*$" | tail -2 | cut -c1-150
done
echo
echo "Si c'est toujours le même plugin : supprimez-le (ROUGE) ou mettez-le à jour."
exit 0
