#!/bin/sh
# Wacayoub Panel - opkg bloqué : retire un verrou resté, termine les installations interrompues, met à jour les listes.
echo "=== Réparer opkg ==="
if pidof opkg >/dev/null; then echo "opkg travaille déjà (PID $(pidof opkg)) : attendez la fin puis relancez."; exit 0; fi
for l in /run/opkg.lock /var/lib/opkg/lock /var/run/opkg.lock; do [ -e $l ] && rm -f $l && echo "Verrou retiré : $l"; done
echo ">>> Fin des installations interrompues"
opkg configure 2>&1 | tail -5
echo ">>> Mise à jour des listes"
if opkg update >/tmp/opkg-update.log 2>&1; then echo "Listes à jour."; else echo "ERREUR :"; tail -5 /tmp/opkg-update.log; fi
rm -f /tmp/opkg-update.log
B=$(opkg list-installed 2>/dev/null | wc -l)
echo "$B paquets installés."
exit 0
