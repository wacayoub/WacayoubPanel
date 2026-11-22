#!/usr/bin/env python3
"""Build .ipk packages for the items that were installed by hand on the receiver
(no opkg package existed). Payload folders under payload/<id>/ mirror '/'.

Usage: python tools/build_payloads.py
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import ipk  # noqa: E402

VER = "2026.11.22"
MAINT = "wacayoub"
PLUG = "/usr/lib/enigma2/python/Plugins/Extensions"

# Remove .pyc caches left by older manual installs so the new .py is used.
CLEAN_PYC = """#!/bin/sh
find "%s" -name '*.pyc' -delete 2>/dev/null
exit 0
"""

SKIN_LINK = """#!/bin/sh
# mySkin is the skin's personal-parts switch; default is off.
D=/usr/share/enigma2/%(skin)s
[ -e "$D/mySkin" ] || ln -s mySkin_off "$D/mySkin"
%(extra)s
exit 0
"""

SKIN_PRERM = """#!/bin/sh
# Refuse to remove the skin that is active right now (the GUI would fall back badly).
if grep -q "^config.skin.primary_skin=%(skin)s/" /etc/enigma2/settings 2>/dev/null; then
  echo "%(skin)s is the active skin: choose another skin first."
  exit 1
fi
exit 0
"""

SKIN_POSTRM = """#!/bin/sh
rm -f /usr/share/enigma2/%(skin)s/mySkin 2>/dev/null
exit 0
"""

PACKAGES = [
    {
        "id": "ipaudiopro",
        "control": {
            "Package": "enigma2-plugin-extensions-ipaudiopro",
            "Version": VER,
            "Description": "IPAudio Pro: listen to another audio source (radio, IPTV) over the live picture, with sync and scoreboard tools",
            "Section": "extra",
            "Priority": "optional",
            "Maintainer": MAINT,
            "Architecture": "all",
            "Depends": "enigma2, python3-core, gstreamer1.0",
        },
        "scripts": {"postinst": CLEAN_PYC % (PLUG + "/IPAudioPro")},
        "exec": ["usr/lib/enigma2/python/Plugins/Extensions/IPAudioPro/ocr_runtime/tesseract"],
    },
    {
        "id": "ipaudiosmartai",
        "control": {
            "Package": "enigma2-plugin-extensions-ipaudiosmartai",
            "Version": VER,
            "Description": "IPAudio SMART AI Pilote: Chronos, protected Auto and live audio alignment for IPAudio Pro",
            "Section": "extra",
            "Priority": "optional",
            "Maintainer": MAINT,
            "Architecture": "all",
            "Depends": "enigma2, python3-core, enigma2-plugin-extensions-ipaudiopro",
        },
        "scripts": {"postinst": CLEAN_PYC % (PLUG + "/IPAudioSmartAI")},
    },
    {
        "id": "orbitai",
        "skin": "OrbitAI",
        "control": {
            "Package": "enigma2-plugin-skins-orbitai",
            "Version": VER,
            "Description": "Orbit AI skin (FHD) with colour themes (OrbitAIColours) and DEEP BLUE boot screens",
            "Section": "skins",
            "Priority": "optional",
            "Maintainer": MAINT,
            "Architecture": "all",
            "Depends": "enigma2, enigma2-plugin-skincomponents-metrixneo-runtime",
        },
    },
    {
        "id": "novaorbit",
        "skin": "NovaOrbit",
        "control": {
            "Package": "enigma2-plugin-skins-novaorbit",
            "Version": VER,
            "Description": "Nova Orbit skin (FHD) with the Nova briefing screen",
            "Section": "skins",
            "Priority": "optional",
            "Maintainer": MAINT,
            "Architecture": "all",
            "Depends": "enigma2, enigma2-plugin-skincomponents-metrixneo-runtime",
        },
    },
    {
        "id": "osappletv",
        "skin": "OSAppleTV",
        "control": {
            "Package": "enigma2-plugin-skins-osappletv",
            "Version": VER,
            "Description": "OS APPLE TV skin (FHD) with home screen, weather and preferences",
            "Section": "skins",
            "Priority": "optional",
            "Maintainer": MAINT,
            "Architecture": "all",
            "Depends": "enigma2",
        },
    },
]


def main():
    out_dir = os.path.join(ROOT, "packages")
    for p in PACKAGES:
        root = os.path.join(ROOT, "payload", p["id"])
        scripts = dict(p.get("scripts", {}))
        symlinks = {}
        if "skin" in p:
            skin = p["skin"]
            extra = ""
            plug_dirs = [d for d in os.listdir(os.path.join(root, PLUG.lstrip("/"))) ] if os.path.isdir(os.path.join(root, PLUG.lstrip("/"))) else []
            for d in plug_dirs:
                extra += "find %s/%s -name '*.pyc' -delete 2>/dev/null\n" % (PLUG, d)
            scripts["postinst"] = SKIN_LINK % {"skin": skin, "extra": extra}
            scripts["prerm"] = SKIN_PRERM % {"skin": skin}
            scripts["postrm"] = SKIN_POSTRM % {"skin": skin}
            os.makedirs(os.path.join(root, "usr/share/enigma2", skin, "mySkin_off"), exist_ok=True)
        ctl = dict(p["control"])
        size = 0
        for dp, _dn, fns in os.walk(root):
            for fn in fns:
                size += os.path.getsize(os.path.join(dp, fn))
        ctl["Installed-Size"] = str(size // 1024)
        name = "%s_%s_%s.ipk" % (ctl["Package"], ctl["Version"], ctl["Architecture"])
        ipk.build_ipk(os.path.join(out_dir, name), ctl, root, scripts, symlinks, p.get("exec", ()))
        print("built", name, os.path.getsize(os.path.join(out_dir, name)) // 1024, "KB")


if __name__ == "__main__":
    main()
