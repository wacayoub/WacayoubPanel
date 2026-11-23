#!/bin/sh
# Wacayoub Panel - DNS Google : utilise les serveurs DNS Google (8.8.8.8 8.8.4.4).
# Méthode OpenATV : /etc/enigma2/nameserversdns.conf (prioritaire sur les DNS de la box Internet).
echo "=== DNS : Google ==="
echo "Avant : $(awk '/^nameserver/{printf "%s ", $2}' /etc/resolv.conf)"
[ -f /etc/enigma2/nameserversdns.conf ] && [ ! -f /etc/enigma2/nameserversdns.conf.wp-backup ] && cp /etc/enigma2/nameserversdns.conf /etc/enigma2/nameserversdns.conf.wp-backup
printf 'nameserver %s\nnameserver %s\n' 8.8.8.8 8.8.4.4 > /etc/enigma2/nameserversdns.conf
{ grep -v '^nameserver' /etc/resolv.conf; printf 'nameserver %s\nnameserver %s\n' 8.8.8.8 8.8.4.4; } > /tmp/resolv.wp && cat /tmp/resolv.wp > /etc/resolv.conf
rm -f /tmp/resolv.wp
echo "Après : $(awk '/^nameserver/{printf "%s ", $2}' /etc/resolv.conf)"
if nslookup github.com >/dev/null 2>&1; then echo "Test : OK, les noms de sites sont trouvés."; else echo "Test : ÉCHEC. Revenez en arrière avec « DNS automatique »."; fi
exit 0
