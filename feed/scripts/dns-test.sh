#!/bin/sh
# Wacayoub Panel - Tester les DNS : affiche les DNS actuels et compare leur vitesse (ne change rien).
echo "=== DNS actuels ==="
awk '/^nameserver/{print "  " $2}' /etc/resolv.conf
[ -f /etc/enigma2/nameserversdns.conf ] && echo "(choisis manuellement)" || echo "(donnés par la box Internet)"
echo
echo "=== Vitesse de réponse ==="
for d in 1.1.1.1:Cloudflare 8.8.8.8:Google 9.9.9.9:Quad9 94.140.14.14:AdGuard; do
	ip=${d%%:*}; n=${d##*:}
	t1=$(date +%s%N 2>/dev/null)
	if nslookup github.com $ip >/dev/null 2>&1; then
		t2=$(date +%s%N 2>/dev/null)
		case "$t1" in *N|"") echo "  $n ($ip) : OK";; *) echo "  $n ($ip) : $(( (t2-t1)/1000000 )) ms";; esac
	else
		echo "  $n ($ip) : pas de réponse"
	fi
done
exit 0
