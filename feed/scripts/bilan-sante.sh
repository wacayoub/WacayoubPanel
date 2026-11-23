#!/bin/sh
# Wacayoub Panel - Bilan santé : vérifie le récepteur sans rien changer.
sizemb() { set -- $(stat -f -c "%b %S" "$1" 2>/dev/null); echo $(( ${1:-0} * ${2:-0} / 1048576 )); }
freemb() { set -- $(stat -f -c "%a %S" "$1" 2>/dev/null); echo $(( ${1:-0} * ${2:-0} / 1048576 )); }
OK=0; WARN=0
ok()   { echo "  [OK]  $1"; OK=$((OK+1)); }
warn() { echo "  [!!]  $1"; WARN=$((WARN+1)); }
echo "=== Bilan santé du récepteur ==="
echo "Modèle : $(cat /etc/hostname 2>/dev/null)  ·  $(grep -E '^(distro|imageversion)=' /etc/image-version 2>/dev/null | cut -d= -f2 | tr '\n' ' ')"
echo
T=""
for f in /proc/stb/sensors/temp0/value /proc/stb/fp/temp_sensor; do [ -r $f ] && T=$(cat $f) && break; done
[ -z "$T" ] && [ -r /sys/class/thermal/thermal_zone0/temp ] && T=$(( $(cat /sys/class/thermal/thermal_zone0/temp) / 1000 ))
[ -z "$T" ] && [ -r /proc/hisi/msp/pm_cpu ] && T=$(sed -n 's/.*temperature = \([0-9]*\).*/\1/p' /proc/hisi/msp/pm_cpu)
if [ -n "$T" ]; then
	if [ "$T" -ge 85 ]; then warn "Température $T °C : trop chaude, aérez le récepteur"
	elif [ "$T" -ge 75 ]; then warn "Température $T °C : chaude"
	else ok "Température $T °C"; fi
fi
FREE=$(awk '/MemAvailable/{print int($2/1024)}' /proc/meminfo)
[ "${FREE:-0}" -lt 60 ] && warn "RAM libre faible : $FREE Mo (outil « Récepteur lent »)" || ok "RAM libre : $FREE Mo"
FL=$(freemb /)
[ "${FL:-0}" -lt 50 ] && warn "Système presque plein : $FL Mo libres (outil « Flash pleine »)" || ok "Système : $FL Mo libres"
for m in /media/hdd /media/usb; do
	grep -q " $m " /proc/mounts && ok "Disque $m : $(freemb $m) Mo libres / $(sizemb $m) Mo"
done
LOAD=$(cut -d' ' -f1 /proc/loadavg)
ok "Charge du processeur : $LOAD"
GW=$(awk '$2=="00000000"{print $3}' /proc/net/route | head -1)
[ -n "$GW" ] && ok "Réseau connecté" || warn "Pas de passerelle réseau (câble / Wi-Fi ?)"
if ping -c1 -W3 1.1.1.1 >/dev/null 2>&1; then ok "Internet joignable"; else warn "Internet injoignable (outil « Pas d'Internet »)"; fi
if nslookup github.com >/dev/null 2>&1; then ok "DNS fonctionne"; else warn "DNS en panne (catégorie DNS)"; fi
Y=$(date +%Y)
[ "$Y" -lt 2024 ] && warn "Heure fausse : $(date) (outil « Heure fausse »)" || ok "Heure : $(date '+%d/%m/%Y %H:%M')"
if [ -e /run/opkg.lock ] || [ -e /var/lib/opkg/lock ]; then
	pidof opkg >/dev/null && ok "opkg travaille" || warn "Verrou opkg bloqué (outil « opkg bloqué »)"
else ok "opkg libre"; fi
N=$(ls /home/root/logs/*crash*.log /media/hdd/*crash*.log 2>/dev/null | wc -l)
[ "$N" -gt 0 ] && warn "$N rapport(s) de plantage (outil « Plantages »)" || ok "Aucun plantage enregistré"
CAM=$(readlink -f /etc/init.d/softcam 2>/dev/null); CAM=${CAM##*/softcam.}
if [ -n "$CAM" ] && [ "$CAM" != "None" ]; then
	pidof "$CAM" >/dev/null && ok "Softcam $CAM actif" || warn "Softcam $CAM arrêté (script « Softcam Fix »)"
fi
EPG=$(grep '^config.misc.epgcache_filename=' /etc/enigma2/settings | cut -d= -f2); EPG=${EPG:-/etc/enigma2/epg.dat}
[ -s "$EPG" ] && ok "EPG : $(du -h "$EPG" | cut -f1) ($EPG)" || warn "EPG vide (outil « EPG vide »)"
echo
echo "Résultat : $OK OK, $WARN à vérifier."
exit 0
