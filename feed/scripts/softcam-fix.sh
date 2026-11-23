#!/bin/sh
# Wacayoub Panel - Softcam Fix: stop the softcam, clear caches and stale PID files,
# fix permissions and the softcam link, then restart it. Configs are not touched.
echo "=== Softcam Fix ==="
CUR=$(readlink -f /etc/init.d/softcam 2>/dev/null)
CAM=${CUR##*/softcam.}
[ -n "$CAM" ] || CAM=None
echo "Softcam actif : $CAM"

echo ">>> Arrêt"
[ -x /etc/init.d/softcam ] && /etc/init.d/softcam stop >/dev/null 2>&1
sleep 1
for c in /usr/softcams/*; do
	[ -f "$c" ] && killall -9 "$(basename "$c")" 2>/dev/null
done

echo ">>> Nettoyage des caches et fichiers PID"
rm -rf /tmp/.oscam /tmp/.ncam /tmp/.emu 2>/dev/null
rm -f /tmp/ecm.info /tmp/ecm0.info /tmp/ecm1.info /tmp/pid.info /var/tmp/*.pid 2>/dev/null

echo ">>> Droits et lien"
chmod 755 /usr/softcams/* /etc/init.d/softcam.* 2>/dev/null
if [ ! -e /etc/init.d/softcam ]; then
	ln -sf softcam.None /etc/init.d/softcam
	echo "Lien /etc/init.d/softcam réparé (None)"
	CAM=None
fi

if [ "$CAM" != "None" ]; then
	echo ">>> Redémarrage de $CAM"
	/etc/init.d/softcam start >/dev/null 2>&1
	sleep 3
	if pidof "$CAM" >/dev/null 2>&1; then
		echo "OK : $CAM tourne (PID $(pidof "$CAM"))"
	else
		echo "ATTENTION : $CAM ne tourne pas. Vérifiez sa configuration dans /etc/tuxbox/config/$CAM/"
	fi
else
	echo "Aucun softcam actif : choisissez-en un dans Menu > Configuration > Softcam."
fi
echo "Configurations (/etc/tuxbox/config) : non modifiées."
exit 0
