#!/bin/sh
# Wacayoub Panel - Écran noir (skin) : revient au skin par défaut de l'image. L'interface redémarre.
CUR=$(grep '^config.skin.primary_skin=' /etc/enigma2/settings | cut -d= -f2)
echo "Skin actuel : ${CUR:-par défaut}"
if [ -z "$CUR" ]; then echo "Déjà sur le skin par défaut."; exit 0; fi
echo "Retour au skin par défaut : l'interface va redémarrer dans 3 secondes..."
S=nohup; command -v setsid >/dev/null && S="setsid nohup"
$S sh -c 'sleep 3; init 4; sleep 4; sed -i "/^config.skin.primary_skin=/d" /etc/enigma2/settings; init 3' >/dev/null 2>&1 &
exit 0
