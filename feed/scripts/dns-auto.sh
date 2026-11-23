#!/bin/sh
# Wacayoub Panel - DNS automatique : revient aux DNS donnés par la box Internet.
echo "=== DNS automatique ==="
if [ -f /etc/enigma2/nameserversdns.conf.wp-backup ]; then
	mv -f /etc/enigma2/nameserversdns.conf.wp-backup /etc/enigma2/nameserversdns.conf
	echo "Vos anciens DNS personnalisés sont remis."
else
	rm -f /etc/enigma2/nameserversdns.conf
fi
GW=$(ip route 2>/dev/null | awk '/^default/{print $3; exit}')
# ask the DHCP client for a new lease: it rewrites /etc/resolv.conf
killall -USR1 udhcpc 2>/dev/null
sleep 3
if ! grep -q '^nameserver' /etc/resolv.conf && [ -n "$GW" ]; then
	echo "nameserver $GW" >> /etc/resolv.conf
fi
echo "DNS actuels : $(awk '/^nameserver/{printf "%s ", $2}' /etc/resolv.conf)"
if nslookup github.com >/dev/null 2>&1; then echo "Test : OK"; else echo "Test : ÉCHEC (outil « Pas d'Internet »)"; fi
exit 0
