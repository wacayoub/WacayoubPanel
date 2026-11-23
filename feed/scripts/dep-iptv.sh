#!/bin/sh
# Wacayoub Panel - Dépendances IPTV (streamlink, yt-dlp) : installe depuis le feed officiel OpenATV ce qui manque.
freemb() { set -- $(stat -f -c "%a %S" "$1" 2>/dev/null); echo $(( ${1:-0} * ${2:-0} / 1048576 )); }
PKGS="streamlink python3-yt-dlp python3-youtube-dl rtmpdump curl wget"
echo "=== Dépendances : IPTV (streamlink, yt-dlp) ==="
opkg update >/dev/null 2>&1 || echo "Attention : listes non mises à jour, listes en cache utilisées."
TODO=""; HAVE=0; NONE=""
for p in $PKGS; do
	if opkg status "$p" 2>/dev/null | grep -q "install ok installed"; then HAVE=$((HAVE+1))
	elif opkg info "$p" 2>/dev/null | grep -q "^Package:"; then TODO="$TODO $p"
	else NONE="$NONE $p"; fi
done
echo "Déjà installés : $HAVE"
[ -n "$NONE" ] && echo "Absents du feed de cette image (ignorés) :$NONE"
if [ -z "$TODO" ]; then echo "Rien à installer : tout est déjà là."; exit 0; fi
echo ">>> Installation :$TODO"
FREE=$(freemb /)
echo "Place libre : $FREE Mo"
opkg install $TODO 2>&1 | grep -vE "^(Downloading|Configuring|Collected errors|Installing .* to root)" | tail -15
FAIL=""
for p in $TODO; do opkg status "$p" 2>/dev/null | grep -q "install ok installed" || FAIL="$FAIL $p"; done
[ -n "$FAIL" ] && echo "Non installés :$FAIL" || echo ">>> Terminé avec succès"
exit 0
