#!/bin/sh
# Wacayoub Panel - EPG vide : vérifie le fichier EPG et le dossier.
echo "=== EPG ==="
EPG=$(grep '^config.misc.epgcache_filename=' /etc/enigma2/settings | cut -d= -f2); EPG=${EPG:-/etc/enigma2/epg.dat}
D=$(dirname "$EPG")
echo "Fichier EPG : $EPG"
if [ ! -d "$D" ]; then echo "ERREUR : le dossier $D n'existe pas (disque débranché ?). Menu > Système > EPG pour changer."; exit 0; fi
touch "$D/.wp_test" 2>/dev/null && rm -f "$D/.wp_test" && echo "Dossier accessible en écriture : OK" || echo "ERREUR : dossier $D en lecture seule"
if [ -f "$EPG" ]; then
	S=$(wc -c < "$EPG")
	echo "Taille : $((S/1024)) Ko  ·  modifié le $(date -r "$EPG" '+%d/%m %H:%M' 2>/dev/null)"
	if [ "$S" -lt 1024 ]; then rm -f "$EPG"; echo "Fichier vide supprimé : il sera recréé."; fi
else
	echo "Pas encore de fichier EPG."
fi
[ "$(date +%Y)" -lt 2024 ] && echo "ATTENTION : l'heure est fausse, l'EPG ne s'affiche pas (outil « Heure fausse »)."
echo
echo "Pour remplir l'EPG : restez 1 minute sur une chaîne de chaque bouquet, ou utilisez EPG Manager."
exit 0
