#!/usr/bin/env python3
"""Build the Wacayoub Panel .ipk and write feed/index.json.

- .ipk files live in packages/ and are published as assets of the GitHub release
  RELEASE_TAG of wacayoub/WacayoubPanel (files over 100 MB cannot go in git).
- EPG Manager is not re-hosted: its entry points at its own GitHub release.
- Scripts live in git under feed/scripts/ and are served from raw.githubusercontent.com.

Usage: python tools/build_feed.py
"""
import datetime
import hashlib
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import ipk  # noqa: E402

REPO = "wacayoub/WacayoubPanel"
RELEASE_TAG = "packages"
ASSET_URL = "https://github.com/%s/releases/download/%s/" % (REPO, RELEASE_TAG)
RAW_URL = "https://raw.githubusercontent.com/%s/main/" % REPO
EXTERNAL = {
    # package -> url (published by the plugin's own project)
    "enigma2-plugin-extensions-epgmanager":
        "https://github.com/wacayoub/EPGManager/releases/download/v2026.11.14-rc88/"
        "enigma2-plugin-extensions-epgmanager_2026.11.14-rc88_all.ipk",
}

PANEL = {
    "Package": "enigma2-plugin-extensions-wacayoubpanel",
    "Version": "1.0.3",
    "Description": "Wacayoub Panel: install, update and remove wacayoub's plugins, skins and scripts",
    "Section": "extra",
    "Priority": "optional",
    "Maintainer": "wacayoub",
    "Architecture": "all",
    "Depends": "enigma2, python3-core, python3-json",
}
PANEL_POSTINST = """#!/bin/sh
find /usr/lib/enigma2/python/Plugins/Extensions/WacayoubPanel -name '*.pyc' -delete 2>/dev/null
exit 0
"""
PANEL_POSTRM = """#!/bin/sh
rm -rf /usr/lib/enigma2/python/Plugins/Extensions/WacayoubPanel /tmp/wacayoubpanel 2>/dev/null
exit 0
"""

CATEGORIES = [
    {"id": "iptv", "title": "IPTV & Satellite"},
    {"id": "epg", "title": "EPG & Bouquets"},
    {"id": "audio", "title": "Audio"},
    {"id": "tools", "title": "Outils & Infos"},
    {"id": "skins", "title": "Skins"},
    {"id": "scripts", "title": "Scripts"},
    {"id": "panel", "title": "Panel"},
]

P = "enigma2-plugin-extensions-"
ITEMS = [
    {"id": "iptosat", "name": "IPToSat Pro", "category": "iptv", "type": "plugin",
     "summary": "Remplace les chaînes satellite par la meilleure source IPTV",
     "description": "IPToSat Pro (SatIPTVBridge) : associe chaque chaîne satellite à ses flux IPTV, classe les sources et verrouille la meilleure.",
     "packages": [P + "satiptvbridge"]},
    {"id": "iptvbouquetai", "name": "IPTV Bouquet AI", "category": "iptv", "type": "plugin",
     "summary": "Crée des bouquets IPTV propres et triés automatiquement",
     "description": "IPTV Bouquet AI : construit des bouquets IPTV classés à partir de votre liste, sans doublons.",
     "packages": [P + "iptvbouquetai"]},
    {"id": "epgmanager", "name": "EPG Manager", "category": "epg", "type": "plugin",
     "summary": "Guide TV : sources, correspondances et mise à jour automatique",
     "description": "EPG Manager : télécharge et associe l'EPG à vos chaînes satellite et IPTV, avec mise à jour programmée.",
     "packages": [P + "epgmanager"]},
    {"id": "bop2", "name": "BOP 2 – Bouquets par pays", "category": "epg", "type": "plugin",
     "summary": "Bouquets par pays et par langue, satellite d'abord",
     "description": "BOP 2 « Bouquets par pays » : range vos chaînes par pays et par langue, satellite en premier, avec logos.",
     "packages": [P + "bop2"]},
    {"id": "ipaudio", "name": "IPAudio Pro + SMART AI Pilote", "category": "audio", "type": "plugin",
     "summary": "Autre commentaire audio sur l'image, synchronisé",
     "description": "IPAudio Pro : écoute une autre source audio (radio, IPTV) sur l'image en direct. SMART AI Pilote : Chronos, Auto protégé et calage direct.",
     "packages": [P + "ipaudiopro", P + "ipaudiosmartai"],
     "main": P + "ipaudiopro",
     "remove": [P + "ipaudiosmartai", P + "ipaudiopro"]},
    {"id": "salaatneo", "name": "Salaat NEO", "category": "tools", "type": "plugin",
     "summary": "Horaires de prière, rappels et adhan",
     "description": "Salaat NEO : calendrier des prières et rappels visuels, avec les sons d'adhan.",
     "packages": [P + "salaatneo", P + "salaatneo-sounds", P + "salaatneo-sounds-salaatfirst"],
     "main": P + "salaatneo",
     "remove": [P + "salaatneo-sounds-salaatfirst", P + "salaatneo-sounds", P + "salaatneo"]},
    {"id": "neoweather", "name": "Neo Weather", "category": "tools", "type": "plugin",
     "summary": "Météo pour les skins NEO",
     "description": "Neo Weather : météo actuelle et prévisions affichées par les skins MetrixNEO / Orbit.",
     "packages": [P + "neoweather"]},
    {"id": "neoconnect", "name": "Neo Connect", "category": "tools", "type": "plugin",
     "summary": "Relie le récepteur à l'application Neo (Google TV)",
     "description": "Neo Connect : service récepteur pour piloter le Vu+ depuis l'application Neo sur Google TV.",
     "packages": [P + "neoconnect"]},
    {"id": "metrixneohelper", "name": "MetrixNEO Helper", "category": "tools", "type": "plugin",
     "summary": "Réglages et assistant du skin MetrixNEO",
     "description": "MetrixNEO Helper : réglages, thèmes et outils du skin MetrixNEO.",
     "packages": [P + "metrixneohelper"]},
    {"id": "metrixneo", "name": "MetrixNEO", "category": "skins", "type": "skin",
     "summary": "Skin FHD MetrixNEO (avec composants et Helper)",
     "description": "Skin MetrixNEO en Full HD. Installe aussi ses composants (runtime) et MetrixNEO Helper.",
     "packages": ["enigma2-plugin-skins-metrixneo", "enigma2-plugin-skincomponents-metrixneo-runtime", P + "metrixneohelper"],
     "main": "enigma2-plugin-skins-metrixneo",
     "remove": ["enigma2-plugin-skins-metrixneo"]},
    {"id": "orbitai", "name": "Orbit AI", "category": "skins", "type": "skin",
     "summary": "Skin FHD Orbit AI, 6 thèmes couleur, écran de démarrage DEEP BLUE",
     "description": "Skin Orbit AI en Full HD avec 6 thèmes de couleurs (OrbitAIColours) et l'écran de démarrage DEEP BLUE. Utilise les composants MetrixNEO.",
     "packages": ["enigma2-plugin-skins-orbitai", "enigma2-plugin-skincomponents-metrixneo-runtime"],
     "main": "enigma2-plugin-skins-orbitai",
     "remove": ["enigma2-plugin-skins-orbitai"]},
    {"id": "novaorbit", "name": "Nova Orbit", "category": "skins", "type": "skin",
     "summary": "Skin FHD Nova Orbit avec écran Briefing",
     "description": "Skin Nova Orbit en Full HD avec l'écran Nova Briefing. Utilise les composants MetrixNEO.",
     "packages": ["enigma2-plugin-skins-novaorbit", "enigma2-plugin-skincomponents-metrixneo-runtime"],
     "main": "enigma2-plugin-skins-novaorbit",
     "remove": ["enigma2-plugin-skins-novaorbit"]},
    {"id": "osappletv", "name": "OS Apple TV", "category": "skins", "type": "skin",
     "summary": "Skin FHD style Apple TV, accueil et météo",
     "description": "Skin OS APPLE TV en Full HD : écran d'accueil, météo et préférences du skin.",
     "packages": ["enigma2-plugin-skins-osappletv"]},
    {"id": "infosysteme", "name": "Info système", "category": "scripts", "type": "script",
     "summary": "Affiche modèle, image, mémoire, place libre et mes paquets (ne change rien)",
     "description": "Script en lecture seule : modèle, version de l'image, RAM, place libre, skin actif et liste de vos paquets installés.",
     "packages": ["script-info-systeme"]},
    {"id": "panel", "name": "Wacayoub Panel", "category": "panel", "type": "panel",
     "summary": "Ce panel (mise à jour du panel lui-même)",
     "description": "Wacayoub Panel : installe, met à jour et supprime mes plugins, skins et scripts.",
     "packages": [PANEL["Package"]]},
]

SCRIPTS = {"script-info-systeme": ("feed/scripts/info-systeme.sh", "1.0")}


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def build_panel():
    stage = os.path.join(ROOT, "build", "panel")
    dest = os.path.join(stage, "usr/lib/enigma2/python/Plugins/Extensions/WacayoubPanel")
    if os.path.isdir(stage):
        import shutil
        shutil.rmtree(stage)
    os.makedirs(dest)
    src = os.path.join(ROOT, "src", "WacayoubPanel")
    import shutil
    for fn in sorted(os.listdir(src)):
        if fn.endswith((".py", ".png")):
            shutil.copy2(os.path.join(src, fn), dest)
    ctl = dict(PANEL)
    ctl["Installed-Size"] = str(sum(os.path.getsize(os.path.join(dest, f)) for f in os.listdir(dest)) // 1024 + 1)
    out = os.path.join(ROOT, "packages", "%s_%s_all.ipk" % (ctl["Package"], ctl["Version"]))
    ipk.build_ipk(out, ctl, stage, {"postinst": PANEL_POSTINST, "postrm": PANEL_POSTRM})
    return out


def main():
    build_panel()
    pkg_dir = os.path.join(ROOT, "packages")
    packages = {}
    for fn in sorted(os.listdir(pkg_dir)):
        if not fn.endswith(".ipk"):
            continue
        path = os.path.join(pkg_dir, fn)
        c = ipk.control_fields(path)
        name = c["Package"]
        if name in packages and ipk_newer(packages[name]["version"], c["Version"]) >= 0:
            continue
        packages[name] = {
            "version": c["Version"],
            "arch": c.get("Architecture", "all"),
            "file": fn,
            "url": EXTERNAL.get(name, ASSET_URL + fn),
            "sha256": sha256(path),
            "size": os.path.getsize(path),
            "installed_size": int(c.get("Installed-Size", "0") or 0),
            "depends": c.get("Depends", ""),
        }
    for name, (rel, ver) in SCRIPTS.items():
        path = os.path.join(ROOT, rel)
        packages[name] = {"version": ver, "arch": "all", "file": os.path.basename(rel),
                          "url": RAW_URL + rel, "sha256": sha256(path),
                          "size": os.path.getsize(path), "installed_size": 0, "depends": ""}
    for it in ITEMS:
        for p in it["packages"]:
            if p not in packages:
                raise SystemExit("missing package for %s: %s" % (it["id"], p))
    index = {
        "name": "Wacayoub Panel",
        "format": 1,
        "updated": datetime.date.today().isoformat(),
        "repo": "https://github.com/" + REPO,
        "categories": CATEGORIES,
        "packages": packages,
        "items": ITEMS,
    }
    out = os.path.join(ROOT, "feed", "index.json")
    with open(out, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(index, fh, ensure_ascii=False, indent=1)
        fh.write("\n")
    print("wrote", out, len(packages), "packages,", len(ITEMS), "items")


def ipk_newer(a, b):
    sys.path.insert(0, os.path.join(ROOT, "src"))
    from WacayoubPanel.feed import compare_versions
    return compare_versions(a, b)


if __name__ == "__main__":
    main()
