#!/bin/sh
# Wacayoub Panel - Heure fausse : remet l'heure à jour depuis Internet (NTP).
echo "=== Heure ==="
echo "Avant : $(date '+%d/%m/%Y %H:%M:%S')"
done=0
for s in pool.ntp.org time.google.com time.cloudflare.com; do
	if ntpd -q -n -p "$s" >/dev/null 2>&1; then echo "Synchronisé avec $s"; done=1; break; fi
done
[ $done = 0 ] && command -v rdate >/dev/null && rdate -s time.nist.gov 2>/dev/null && done=1 && echo "Synchronisé (rdate)"
echo "Après : $(date '+%d/%m/%Y %H:%M:%S')"
[ $done = 0 ] && echo "ÉCHEC : pas d'accès Internet (outil « Pas d'Internet »)."
command -v hwclock >/dev/null && hwclock -w 2>/dev/null
echo "Fuseau horaire : Menu > Système > Heure."
exit 0
