#!/bin/sh
# Wacayoub Panel - Pas d'image / écran noir sur une chaîne : vérifie tuners, signal et softcam (ne change rien).
echo "=== Pas d'image ==="
echo "Tuners :"
grep -E "NIM Socket|Type|Name" /proc/bus/nim_sockets 2>/dev/null | sed 's/^/  /'
echo
ls /dev/dvb/adapter0/frontend* >/dev/null 2>&1 && echo "Pilotes DVB : chargés" || echo "Pilotes DVB : ABSENTS -> redémarrez le récepteur"
for f in /proc/stb/frontend/*/lock /proc/stb/frontend/*/snr; do [ -r "$f" ] && echo "  $f : $(cat $f)"; done 2>/dev/null
echo
CAM=$(readlink -f /etc/init.d/softcam 2>/dev/null); CAM=${CAM##*/softcam.}
echo "Softcam : ${CAM:-None}"
if [ -n "$CAM" ] && [ "$CAM" != "None" ]; then
	pidof "$CAM" >/dev/null && echo "  il tourne" || echo "  ARRÊTÉ -> lancez le script « Softcam Fix »"
	[ -s /tmp/ecm.info ] && { echo "  Dernier ECM :"; head -6 /tmp/ecm.info | sed 's/^/    /'; } || echo "  pas d'ECM (chaîne en clair ou non décodée)"
fi
echo
echo "À essayer :"
echo "  - chaîne en clair (ex. France 24) : si elle marche, le problème vient du softcam ou de l'abonnement"
echo "  - aucune chaîne : vérifiez le câble de la parabole et Menu > Réglages > Tuner"
echo "  - écran noir partout : outil « Écran noir (skin) » ou vérifiez la sortie HDMI (Menu > Système > Vidéo)"
exit 0
