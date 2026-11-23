"""Small opkg packages for the reviewed Ciefp plugins (feed/ciefp.json, written by verify_ciefp.py).

No Ciefp code is copied: each package holds only an info file. Its postinst downloads Ciefp's archive
at the reviewed commit, refuses it if the sha256 differs, and copies the plugin folder without .pyc files.
"""
import json
import os
import shutil

import ipk

POSTINST = r"""#!/bin/sh
# Wacayoub Panel - installe %(repo)s (github.com/%(owner)s, commit %(short)s)
URL='%(url)s'
SHA='%(sha256)s'
NAME='%(repo)s'
TOP="$NAME-%(commit)s"
D="/usr/lib/enigma2/python/Plugins/Extensions/$NAME"
T="/tmp/wp-ciefp-$NAME"
rm -rf "$T"; mkdir -p "$T" || exit 1
echo ">>> Téléchargement de $NAME (github.com/%(owner)s/$NAME)"
if ! wget -q -T 60 -O "$T/a.tgz" "$URL"; then
	echo "ERREUR : téléchargement impossible"; rm -rf "$T"; exit 1
fi
if [ "$(sha256sum "$T/a.tgz" | cut -d' ' -f1)" != "$SHA" ]; then
	echo "ERREUR : le fichier ne correspond pas à la version vérifiée, installation refusée"; rm -rf "$T"; exit 1
fi
tar -xzf "$T/a.tgz" -C "$T" "$TOP/usr/lib/enigma2/python/Plugins/Extensions/$NAME" || { echo "ERREUR : archive illisible"; rm -rf "$T"; exit 1; }
rm -rf "$D"; mkdir -p "$D"
cp -r "$T/$TOP/usr/lib/enigma2/python/Plugins/Extensions/$NAME/." "$D/"
find "$D" -name '*.pyc' -delete
rm -rf "$T"
echo ">>> $NAME installé (version vérifiée par Wacayoub Panel)"
exit 0
"""

POSTRM = r"""#!/bin/sh
case "$1" in
  remove|purge) rm -rf "/usr/lib/enigma2/python/Plugins/Extensions/%(repo)s" ;;
esac
exit 0
"""


def package_name(repo):
    return "enigma2-plugin-extensions-" + repo.lower()


def build_all(root):
    """Build the packages; return the panel items (category communaute)."""
    path = os.path.join(root, "feed", "ciefp.json")
    if not os.path.exists(path):
        return []
    picks = json.load(open(path, encoding="utf-8"))
    items = []
    for c in picks:
        c.setdefault("owner", "ciefp")
        who = "Ciefp" if c["owner"] == "ciefp" else c["owner"]
        page = "https://github.com/%s/%s" % (c["owner"], c["repo"])
        name = package_name(c["repo"])
        # Ciefp's installer.sh version is often behind his plugin: the commit date is the version
        version = "%s+%s" % (c["date"].replace("-", "."), c["commit"][:7])
        day = "/".join(reversed(c["date"].split("-")))
        stage = os.path.join(root, "build", "ciefp-pkg", c["repo"])
        if os.path.isdir(stage):
            shutil.rmtree(stage)
        info_dir = os.path.join(stage, "usr", "share", "wacayoubpanel", "ciefp")
        os.makedirs(info_dir)
        with open(os.path.join(info_dir, c["repo"] + ".txt"), "w", encoding="utf-8", newline="\n") as fh:
            fh.write("%s de %s - %s\ncommit %s (%s)\nsha256 %s\nvérifié le %s\n"
                     % (c["title"], who, page, c["commit"], c["date"], c["sha256"], c["reviewed"]))
        deps = ["enigma2", "python3-core"] + [d for d in c.get("depends", []) if d not in ("python3-core",)]
        ctl = {
            "Package": name,
            "Version": version,
            "Description": "%s (%s) - downloaded from %s at a reviewed commit" % (c["title"], who, page),
            "Section": "extra",
            "Priority": "optional",
            "Maintainer": "wacayoub",
            "Architecture": "all",
            "Depends": ", ".join(deps),
            "Installed-Size": str((c.get("installed") or c.get("size", 0) * 3) // 1024 + 1),
        }
        fill = dict(c, short=c["commit"][:7])
        out = os.path.join(root, "packages", "%s_%s_all.ipk" % (name, version))
        if not os.path.exists(out):
            ipk.build_ipk(out, ctl, stage, {"postinst": POSTINST % fill, "postrm": POSTRM % fill})
        if c.get("launcher"):
            shown = "%s (non vérifié)" % c["title"]
            summary = "%s  ·  ATTENTION : non vérifié" % c["summary"]
            desc = ("%s  ·  %s\nATTENTION : ce panel lance les installateurs d'autres sites (wget | sh). "
                    "Wacayoub a vérifié le panel (version du %s), PAS ce qu'il installe." % (c["summary"], page, day))
        else:
            shown = c["title"]
            summary = "%s  ·  %s" % (c["summary"], who)
            desc = ("%s  ·  %s\nPlugin de %s, téléchargé chez lui. Version du %s vérifiée par Wacayoub le %s "
                    "(sans fichiers compilés, empreinte contrôlée)." % (c["summary"], page, who, day, c["reviewed"]))
        items.append({"id": "cf-" + c["repo"].lower(), "name": shown, "category": "communaute", "type": "plugin",
                      "summary": summary, "description": desc, "packages": [name], "page": page})
    return items
