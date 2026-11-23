#!/bin/sh
# Wacayoub Panel - Garde : détecte Enigma2 figé dans un pilote (télécommande et image bloquées)
# et redémarre le récepteur. Lancé par le panel au démarrage de l'interface (un seul à la fois).
# Rapport : /home/root/logs/wacayoub-gel-*.log (lu par Fixo).
# Pas de redémarrage automatique si /home/root/wacayoub-gel-off existe (rapport seulement).
# Test sans redémarrer : WG_TEST=1 sh garde-gel.sh
SELF="$0"
PIDF=/var/run/wacayoub-gel.pid
LOGDIR=/home/root/logs
OFF=/home/root/wacayoub-gel-off
TEST=${WG_TEST:-0}
if [ "$TEST" != 1 ] && [ -f $PIDF ] && [ "$(cat $PIDF)" != "$$" ] && kill -0 "$(cat $PIDF)" 2>/dev/null; then
	exit 0
fi
[ "$TEST" = 1 ] || echo $$ > $PIDF
STAMP=$(stat -c %Y "$SELF" 2>/dev/null)
STUCK=0
DONE=""

state() { sed 's/^.*) //' "$1" 2>/dev/null | cut -c1; }

while :; do
	[ "$TEST" = 1 ] || sleep 15
	[ -f "$SELF" ] || { rm -f $PIDF; exit 0; }             # panel removed
	NOW=$(stat -c %Y "$SELF" 2>/dev/null)
	[ "$NOW" = "$STAMP" ] || exec /bin/sh "$SELF"           # panel updated: run the new version
	E2=$(pidof enigma2 | cut -d' ' -f1)
	if [ -z "$E2" ] || pidof opkg >/dev/null; then STUCK=0; continue; fi
	# 1) kernel report "task X:TID blocked for more than N seconds" for a thread of this enigma2, still stuck
	HUNG=""
	for t in $(dmesg | sed -n 's/.*task .*:\([0-9][0-9]*\) blocked for more than.*/\1/p'); do
		[ -d /proc/$E2/task/$t ] && [ "$(state /proc/$E2/task/$t/stat)" = D ] && HUNG=$t
	done
	# 2) or the main thread stuck in a driver (state D) for 4 minutes while the web interface does not answer
	ST=$(state /proc/$E2/stat)
	if [ "$ST" = D ] && ! wget -q -T 8 -O /dev/null http://127.0.0.1/api/statusinfo 2>/dev/null; then
		STUCK=$((STUCK + 1))
	else
		STUCK=0
	fi
	if [ "$TEST" = 1 ]; then HUNG=${HUNG:-$E2}; fi
	if [ -z "$HUNG" ] && [ $STUCK -lt 12 ]; then continue; fi
	KEY="$E2:${HUNG:-main}"
	[ "$KEY" = "$DONE" ] && continue
	DONE=$KEY
	T=${HUNG:-$E2}
	mkdir -p $LOGDIR
	F=$LOGDIR/wacayoub-gel-$(date +%Y%m%d-%H%M%S).log
	{
		echo "date=$(date '+%d/%m/%Y %H:%M:%S')"
		echo "enigma2=$E2 thread=$T state=$(state /proc/$E2/task/$T/stat)"
		echo "wchan=$(cat /proc/$E2/task/$T/wchan 2>/dev/null)"
		echo "test=$TEST"
		echo
		dmesg | grep -A30 "blocked for more than" | tail -80
	} > $F
	if [ "$TEST" = 1 ]; then echo "reboot=non (test)" >> $F; echo "$F"; exit 0; fi
	if [ -f $OFF ]; then echo "reboot=non (coupé)" >> $F; sync; continue; fi
	echo "reboot=oui" >> $F
	sync
	reboot
	sleep 90
	sync
	reboot -f
done
