#!/bin/sh
# Wacayoub Panel - Créer un swap : fichier d'échange de 256 Mo sur le disque, utile aux récepteurs qui ont peu de RAM.
freemb() { set -- $(stat -f -c "%a %S" "$1" 2>/dev/null); echo $(( ${1:-0} * ${2:-0} / 1048576 )); }
grep -q "^/" /proc/swaps && { echo "Un swap est déjà actif :"; cat /proc/swaps; exit 0; }
for m in /media/hdd /media/usb; do grep -q " $m " /proc/mounts && D=$m && break; done
[ -z "$D" ] && { echo "Aucun disque monté : branchez un disque ou une clé USB."; exit 0; }
FS=$(awk -v m="$D" '$2==m{print $3}' /proc/mounts)
case "$FS" in vfat|exfat|ntfs*|fuseblk) echo "Le disque est en $FS : le swap demande ext4. Rien n'est fait."; exit 0;; esac
F="$D/wacayoub.swap"
FREE=$(freemb "$D")
[ "$FREE" -lt 600 ] && { echo "Pas assez de place sur $D ($FREE Mo)."; exit 0; }
echo ">>> Création de $F (256 Mo)"
dd if=/dev/zero of="$F" bs=1M count=256 2>/dev/null && chmod 600 "$F" && mkswap "$F" >/dev/null && swapon "$F" || { echo "ERREUR : création impossible"; rm -f "$F"; exit 1; }
grep -q "$F" /etc/fstab || echo "$F swap swap defaults 0 0" >> /etc/fstab
echo "Swap actif et gardé au redémarrage :"
cat /proc/swaps
exit 0
