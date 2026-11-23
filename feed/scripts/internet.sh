#!/bin/sh
# Wacayoub Panel - Pas d'Internet : teste le réseau étape par étape (ne change rien).
echo "=== Test du réseau ==="
for i in $(ls /sys/class/net | grep -v lo); do
	echo "Interface $i : $(cat /sys/class/net/$i/operstate 2>/dev/null)  $(ip -4 addr show $i 2>/dev/null | awk '/inet /{print $2}')"
done
GW=$(ip route 2>/dev/null | awk '/^default/{print $3; exit}')
echo
if [ -z "$GW" ]; then
	echo "ÉCHEC : pas de passerelle. Vérifiez le câble ou le Wi-Fi (Menu > Réseau)."; exit 0
fi
ping -c2 -W3 "$GW" >/dev/null 2>&1 && echo "1. Box Internet ($GW) : OK" || { echo "1. Box Internet ($GW) : ÉCHEC -> redémarrez la box Internet / vérifiez le câble"; exit 0; }
ping -c2 -W3 1.1.1.1 >/dev/null 2>&1 && echo "2. Internet (1.1.1.1) : OK" || { echo "2. Internet : ÉCHEC -> la box Internet n'a pas de connexion"; exit 0; }
if nslookup github.com >/dev/null 2>&1; then echo "3. DNS : OK"; else echo "3. DNS : ÉCHEC -> catégorie DNS, choisissez Cloudflare ou Google"; exit 0; fi
if wget -q -T 10 -O /dev/null https://github.com 2>/dev/null; then echo "4. Sites sécurisés (HTTPS) : OK"; else echo "4. HTTPS : ÉCHEC -> vérifiez l'heure (outil « Heure fausse »)"; exit 0; fi
echo
echo "Tout fonctionne : Internet est disponible."
exit 0
