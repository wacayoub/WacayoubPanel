#!/bin/sh
# Wacayoub Panel - Dépendances Python (modules des plugins) : installe depuis le feed officiel OpenATV ce qui manque.
freemb() { set -- $(stat -f -c "%a %S" "$1" 2>/dev/null); echo $(( ${1:-0} * ${2:-0} / 1048576 )); }
PKGS="python3-requests python3-six python3-pillow python3-lxml python3-beautifulsoup4 python3-pycryptodome python3-cryptography python3-pyopenssl python3-certifi python3-urllib3 python3-chardet python3-treq python3-twisted-web python3-sqlite3 python3-json python3-futures3 python3-js2py python3-mechanize python3-rarfile python3-pyexecjs"
echo "=== Dépendances : Python (modules des plugins) ==="
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
