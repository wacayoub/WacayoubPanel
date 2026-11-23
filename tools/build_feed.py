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
    "Version": "2.3.0",
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
# Only clean up on a real removal: during an upgrade opkg runs the OLD postrm with
# "upgrade" after unpacking the new files (1.0.0-1.0.3 deleted them here).
PANEL_POSTRM = """#!/bin/sh
case "$1" in
  remove|purge)
    find /usr/lib/enigma2/python/Plugins/Extensions/WacayoubPanel -name '*.pyc' -delete 2>/dev/null
    rmdir /usr/lib/enigma2/python/Plugins/Extensions/WacayoubPanel/__pycache__ 2>/dev/null
    rmdir /usr/lib/enigma2/python/Plugins/Extensions/WacayoubPanel 2>/dev/null
    ;;
esac
exit 0
"""

CATEGORIES = [
    {"id": "iptv", "title": "IPTV & Satellite"},
    {"id": "epg", "title": "EPG & Bouquets"},
    {"id": "audio", "title": "Audio"},
    {"id": "tools", "title": "Outils & Infos"},
    {"id": "skins", "title": "Skins"},
    {"id": "scripts", "title": "Scripts"},
    {"id": "fix", "title": "Réparer"},
    {"id": "dns", "title": "DNS"},
    {"id": "deps", "title": "Dépendances"},
    {"id": "disk", "title": "Disque"},
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
    {"id": "softcamfix", "name": "Softcam Fix", "category": "scripts", "type": "script",
     "summary": "Arrête le softcam, vide caches et PID, répare droits et lien, puis le relance",
     "description": "Softcam Fix : arrête le softcam actif, supprime les caches (/tmp/.oscam, /tmp/.ncam, ecm.info) et les fichiers PID restés, "
                    "remet les droits de /usr/softcams et le lien /etc/init.d/softcam, puis relance le softcam. Les configurations ne sont pas modifiées.",
     "packages": ["script-softcam-fix"]},
    {"id": "infosysteme", "name": "Info système", "category": "scripts", "type": "script",
     "summary": "Affiche modèle, image, mémoire, place libre et mes paquets (ne change rien)",
     "description": "Script en lecture seule : modèle, version de l'image, RAM, place libre, skin actif et liste de vos paquets installés.",
     "packages": ["script-info-systeme"]},
    {"id": "panel", "name": "Wacayoub Panel", "category": "panel", "type": "panel",
     "summary": "Ce panel (mise à jour du panel lui-même)",
     "description": "Wacayoub Panel : installe, met à jour et supprime mes plugins, skins et scripts.",
     "packages": [PANEL["Package"]]},
]

SCRIPTS = {"script-info-systeme": ("feed/scripts/info-systeme.sh", "1.0"),
           "script-softcam-fix": ("feed/scripts/softcam-fix.sh", "1.0")}

# Repair / DNS / dependency / disk tools: (file, category, name, summary, description). All are my own shell
# scripts in feed/scripts/, checked with sha256 before they run. "lecture seule" ones change nothing.
TOOLS = [
    ("bilan-sante", "fix", "Bilan santé", "Vérifie tout le récepteur en une fois (ne change rien)",
     "Température, RAM, place libre, disques, réseau, Internet, DNS, heure, opkg, plantages, softcam et EPG. "
     "Chaque problème trouvé indique l'outil à utiliser. Lecture seule."),
    ("internet", "fix", "Pas d'Internet", "Teste box, Internet, DNS et HTTPS étape par étape",
     "Cherche où la connexion casse : câble/Wi-Fi, box Internet, accès Internet, DNS, sites HTTPS. Lecture seule."),
    ("pas-image", "fix", "Pas d'image", "Vérifie tuners, pilotes DVB et softcam",
     "Liste les tuners, vérifie les pilotes DVB, le softcam et le dernier ECM, puis donne les vérifications à faire. Lecture seule."),
    ("lent", "fix", "Récepteur lent", "Libère la RAM et montre ce qui consomme",
     "Vide le cache mémoire du noyau et les fichiers temporaires du panel, puis affiche les processus qui utilisent le plus de mémoire."),
    ("heure", "fix", "Heure fausse", "Remet l'heure à jour depuis Internet (NTP)",
     "Synchronise l'horloge avec pool.ntp.org (ou Google / Cloudflare). Une heure fausse casse l'EPG, les timers et les sites HTTPS."),
    ("epg-vide", "fix", "EPG vide", "Vérifie le fichier et le dossier de l'EPG",
     "Contrôle l'emplacement du fichier EPG, les droits d'écriture et l'heure. Supprime seulement un fichier EPG vide (moins de 1 Ko)."),
    ("flash-pleine", "fix", "Flash pleine", "Vide caches et vieux journaux, montre ce qui prend de la place",
     "Supprime le cache opkg, les journaux archivés et les rapports de plantage anciens (garde les 3 derniers), puis liste les "
     "dossiers les plus gros. Vos plugins, skins et réglages ne sont pas touchés."),
    ("opkg-bloque", "fix", "opkg bloqué", "Retire un verrou resté, finit les installations, met à jour les listes",
     "Si aucune installation ne tourne : retire le verrou opkg resté après une coupure, termine les paquets à moitié installés "
     "(opkg configure) puis relance opkg update."),
    ("skin-defaut", "fix", "Écran noir (skin)", "Revient au skin par défaut de l'image",
     "Remet le skin par défaut quand un skin affiche un écran noir ou plante. L'interface redémarre ; vos autres réglages restent."),
    ("plantages", "fix", "Plantages", "Résume les derniers rapports de plantage",
     "Lit les 3 derniers rapports de plantage d'Enigma2 et indique le plugin en cause et l'erreur. Lecture seule."),
    ("dns-test", "dns", "DNS actuels et vitesse", "Affiche les DNS utilisés et compare leur vitesse (ne change rien)",
     "Montre les DNS actuels et le temps de réponse de Cloudflare, Google, Quad9 et AdGuard. Lecture seule."),
    ("dns-cloudflare", "dns", "DNS Cloudflare", "1.1.1.1  ·  1.0.0.1  ·  rapide",
     "Utilise les DNS Cloudflare (méthode OpenATV : /etc/enigma2/nameserversdns.conf). Retour arrière : « DNS automatique »."),
    ("dns-google", "dns", "DNS Google", "8.8.8.8  ·  8.8.4.4",
     "Utilise les DNS Google (méthode OpenATV : /etc/enigma2/nameserversdns.conf). Retour arrière : « DNS automatique »."),
    ("dns-quad9", "dns", "DNS Quad9", "9.9.9.9  ·  bloque les sites malveillants",
     "Utilise les DNS Quad9, qui bloquent les domaines malveillants connus. Retour arrière : « DNS automatique »."),
    ("dns-adguard", "dns", "DNS AdGuard", "94.140.14.14  ·  bloque pubs et pisteurs",
     "Utilise les DNS AdGuard, qui bloquent publicités et pisteurs. Retour arrière : « DNS automatique »."),
    ("dns-auto", "dns", "DNS automatique", "Revient aux DNS de votre box Internet",
     "Annule un DNS choisi ici et revient aux DNS donnés par la box Internet (DHCP), ou à vos anciens DNS personnalisés."),
    ("dep-tout", "deps", "Tout installer", "Toutes les dépendances ci-dessous en une fois",
     "Installe depuis le feed officiel OpenATV ce qui manque parmi GStreamer, lecteurs, modules Python, audio, IPTV et archives. "
     "Les paquets déjà présents ou absents du feed sont sautés."),
    ("dep-gstreamer", "deps", "GStreamer", "Lecture vidéo et audio (plugins base, good, bad, ugly, libav)",
     "Plugins GStreamer du feed OpenATV, utiles pour lire IPTV, vidéos et radios."),
    ("dep-lecteurs", "deps", "Lecteurs vidéo", "ServiceApp, exteplayer3, gstplayer, sous-titres, ffmpeg",
     "Lecteurs alternatifs utilisés par les plugins IPTV (ServiceApp, exteplayer3, gstplayer), SubsSupport et ffmpeg."),
    ("dep-python", "deps", "Modules Python", "requests, lxml, pillow, beautifulsoup4, cryptodome…",
     "Modules Python 3 souvent demandés par les plugins (requests, six, pillow, lxml, beautifulsoup4, pycryptodome, js2py…)."),
    ("dep-audio", "deps", "Audio", "alsa-utils, mpg123, libmad",
     "Outils et bibliothèques audio du feed OpenATV."),
    ("dep-iptv", "deps", "IPTV", "streamlink, yt-dlp, rtmpdump, curl",
     "Outils de flux utilisés par les plugins IPTV et YouTube."),
    ("dep-archives", "deps", "Archives", "unrar, 7zip, zip",
     "Pour ouvrir les fichiers rar, 7z et zip."),
    ("disque-info", "disk", "Info disques", "Place, format et santé SMART des disques (ne change rien)",
     "Pour chaque disque ou clé USB : taille, place libre, format, santé SMART, température et secteurs défectueux. Lecture seule."),
    ("disque-vitesse", "disk", "Vitesse du disque", "Écrit puis relit 64 Mo pour mesurer la vitesse",
     "Mesure la vitesse d'écriture et de lecture du disque (fichier de test supprimé ensuite) et dit s'il suffit pour enregistrer en HD."),
    ("disque-dossiers", "disk", "Préparer le disque", "Crée movie, picon, epg, backup, images, timeshift",
     "Crée les dossiers habituels sur /media/hdd (ou la clé USB) s'ils n'existent pas. Rien n'est supprimé."),
    ("swap-creer", "disk", "Créer un swap", "Fichier d'échange de 256 Mo sur le disque (peu de RAM)",
     "Crée wacayoub.swap (256 Mo) sur un disque ext4 et l'active à chaque démarrage. Rien n'est fait si un swap existe déjà."),
    ("swap-supprimer", "disk", "Supprimer le swap", "Retire le swap créé par le panel",
     "Désactive et supprime seulement le fichier wacayoub.swap créé par le panel."),
]
for _f, _cat, _name, _sum, _desc in TOOLS:
    SCRIPTS["script-" + _f] = ("feed/scripts/%s.sh" % _f, "1.0")
    ITEMS.append({"id": "t-" + _f, "name": _name, "category": _cat, "type": "script",
                  "summary": _sum, "description": _desc, "packages": ["script-" + _f]})

# Compatibility shim for OSCam/NCam builds of other images (OpenViX, OpenPLi): they depend on
# "softcam-support" (their softcam framework; OpenATV has its own /etc/init.d/softcam system) and
# "libusb1" (OpenATV names the same library libusb-1.0-0). No files: it only satisfies those names.
COMPAT = {
    "Package": "wacayoub-softcam-compat",
    "Version": "1.0",
    "Description": "Softcam compatibility for OSCam/NCam builds of other images on OpenATV (no files)",
    "Section": "misc",
    "Priority": "optional",
    "Maintainer": "wacayoub",
    "Architecture": "all",
    "Depends": "libusb-1.0-0",
    "Provides": "softcam-support, libusb1",
}


def build_compat():
    import shutil
    stage = os.path.join(ROOT, "build", "compat")
    if os.path.isdir(stage):
        shutil.rmtree(stage)
    doc = os.path.join(stage, "usr", "share", "doc", "wacayoub-softcam-compat")
    os.makedirs(doc)
    with open(os.path.join(doc, "README"), "w", newline="\n") as fh:
        fh.write("Installed by Wacayoub Panel so that OSCam/NCam packages from OpenViX/OpenPLi feeds\n"
                 "can be installed on OpenATV. OpenATV's own softcam system (/etc/init.d/softcam) is used.\n")
    ctl = dict(COMPAT)
    ctl["Installed-Size"] = "1"
    out = os.path.join(ROOT, "packages", "%s_%s_all.ipk" % (ctl["Package"], ctl["Version"]))
    ipk.build_ipk(out, ctl, stage)


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
    if os.path.isdir(os.path.join(src, "img")):
        shutil.copytree(os.path.join(src, "img"), os.path.join(dest, "img"))
    ctl = dict(PANEL)
    ctl["Installed-Size"] = str(sum(os.path.getsize(os.path.join(dp, f)) for dp, _d, fs in os.walk(dest) for f in fs) // 1024 + 1)
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
            "provides": [x.strip().split(" ")[0] for x in c.get("Provides", "").split(",") if x.strip()],
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
    # curated community picks reviewed by tools/verify_community.py (installed from the OpenATV feed)
    categories, items = list(CATEGORIES), [dict(i) for i in ITEMS]
    for it in items:
        # what the receiver must have; the panel refuses to install otherwise
        if it["type"] in ("plugin", "skin", "panel"):
            it["requires"] = {"python": "3.9"}
        if it["type"] == "skin":
            it["requires"]["min_width"] = 1920
        arches = {packages[p]["arch"] for p in it["packages"] if p in packages} - {"all"}
        if arches:
            it["requires"]["machines"] = sorted(a for a in arches if not a.startswith("cortex"))
            if not it["requires"]["machines"]:
                del it["requires"]["machines"]
        prev = os.path.join(ROOT, "feed", "previews", it["id"] + ".jpg")
        if os.path.exists(prev):
            it["preview"] = RAW_URL + "feed/previews/%s.jpg?v=%s" % (it["id"], sha256(prev)[:8])
    cpath = os.path.join(ROOT, "feed", "community.json")
    if os.path.exists(cpath):
        with open(cpath, encoding="utf-8") as fh:
            picks = json.load(fh)
        if picks:
            categories.insert(len(categories) - 2, {"id": "communaute", "title": "Communauté"})
            for c in picks:
                items.append({
                    "id": "c-" + c["package"].split("-")[-1], "name": c["title"], "category": "communaute",
                    "type": "opkg", "summary": c["summary"],
                    "description": "%s  ·  %s\nVérifié par Wacayoub le %s : version %s (feed officiel OpenATV)."
                                   % (c["summary"], c["page"], c["reviewed"], c["reviewed_version"].split("+")[0]),
                    "packages": [c["package"]], "reviewed_version": c["reviewed_version"],
                    "reviewed_sha256": c["reviewed_sha256"], "reviewed": c["reviewed"], "page": c["page"]})
    index = {
        "name": "Wacayoub Panel",
        "format": 1,
        "updated": datetime.date.today().isoformat(),
        "repo": "https://github.com/" + REPO,
        "categories": categories,
        "packages": packages,
        "items": items,
    }
    out = os.path.join(ROOT, "feed", "index.json")
    with open(out, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(index, fh, ensure_ascii=False, indent=1)
        fh.write("\n")
    print("wrote", out, len(packages), "packages,", len(items), "items")


def ipk_newer(a, b):
    sys.path.insert(0, os.path.join(ROOT, "src"))
    from WacayoubPanel.feed import compare_versions
    return compare_versions(a, b)


if __name__ == "__main__":
    main()
