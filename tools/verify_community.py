#!/usr/bin/env python3
"""Review the curated community plugins one by one before they go into the panel.

For each package (taken from the official OpenATV feed, the receiver's own lists in build/lists):
 1. download the exact .ipk named in the feed list,
 2. check its sha256 against the feed list,
 3. scan every file (tools/scan.py patterns) and the install scripts for risky commands
    (piping downloads into a shell, opening telnet/ssh, touching passwords, crontab, base64 exec),
 4. list ELF binaries.
Writes feed/community.json (used by build_feed.py) and feed/COMMUNITY-REVIEW.md.

Usage: python tools/verify_community.py
"""
import datetime
import hashlib
import json
import os
import re
import sys
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import ipk  # noqa: E402
import scan  # noqa: E402
sys.path.insert(0, os.path.join(ROOT, "src"))
from WacayoubPanel.feed import compare_versions  # noqa: E402

LISTS = os.path.join(ROOT, "build", "lists")
CACHE = os.path.join(ROOT, "build", "community")

# name, title, summary, project page (author)
PICKS = [
    ("enigma2-plugin-extensions-xstreamity", "XStreamity", "Lecteur IPTV Xtream Codes (KiddaC)", "https://github.com/kiddac/XStreamity"),
    ("enigma2-plugin-extensions-bouquetmakerxtream", "BouquetMakerXtream", "Bouquets IPTV depuis Xtream / M3U (KiddaC)", "https://github.com/kiddac/Bouquet_Maker_Xtream"),
    ("enigma2-plugin-extensions-youtube", "YouTube", "Regarder YouTube sur le récepteur (Taapat)", "https://github.com/Taapat/enigma2-plugin-youtube"),
    ("enigma2-plugin-extensions-ajpanel", "AJPanel", "Boîte à outils Enigma2 (AMAJamry)", "https://github.com/AMAJamry/AJPanel"),
    ("enigma2-plugin-extensions-wireguard-vpn", "WireGuard VPN", "Client VPN WireGuard", "https://github.com/m4dhouse/Wireguard-Vpn"),
    ("enigma2-plugin-extensions-oaweather", "OAWeather", "Météo (oe-alliance)", "https://github.com/oe-alliance/OAWeather"),
    ("enigma2-plugin-extensions-subssupport", "SubsSupport", "Sous-titres pour films et enregistrements", "https://github.com/oe-mirrors/subssupport"),
    ("enigma2-plugin-extensions-imdb", "IMDb", "Fiches films IMDb depuis l'EPG", "https://github.com/oe-alliance/enigma2-plugins"),
    ("enigma2-plugin-extensions-tmdb", "TMDB", "Fiches films/séries The Movie Database", "https://github.com/oe-alliance/enigma2-plugins"),
    ("enigma2-plugin-extensions-filecommander", "File Commander", "Gestionnaire de fichiers", "https://github.com/openatv/enigma2"),
    ("enigma2-plugin-extensions-autotimer", "AutoTimer", "Enregistrements automatiques par mots-clés", "https://github.com/oe-alliance/enigma2-plugins"),
    ("enigma2-plugin-extensions-epgrefresh", "EPGRefresh", "Rafraîchit l'EPG la nuit", "https://github.com/oe-alliance/enigma2-plugins"),
    ("enigma2-plugin-extensions-seriesplugin", "SeriesPlugin", "Saison/épisode dans les titres d'enregistrement", "https://github.com/betonme/e2openplugin-SeriesPlugin"),
    ("enigma2-plugin-extensions-enhancedmoviecenter", "EnhancedMovieCenter", "Liste d'enregistrements avancée", "https://github.com/oe-alliance/enigma2-plugins"),
    ("enigma2-plugin-extensions-cooltvguide", "CoolTVGuide", "Guide TV 3D en grille (Coolman)", "https://www.opena.tv"),
    ("enigma2-plugin-extensions-xtraevent", "xtraEvent", "Affiches et infos des programmes (kitte888)", "https://www.opena.tv"),
    ("enigma2-plugin-extensions-setpicon", "SetPicon", "Attribuer et gérer les picons", "https://github.com/oe-alliance/enigma2-plugins"),
    ("enigma2-plugin-extensions-bootlogoswitcher", "BootlogoSwitcher", "Choisir le logo de démarrage", "https://github.com/stein17"),
    ("enigma2-plugin-extensions-e2iplayer", "E2iPlayer", "Vidéos et replays de nombreux sites", "https://github.com/oe-mirrors/e2iplayer"),
    ("enigma2-plugin-extensions-estalker", "EStalker", "Lecteur IPTV Stalker / MAG (KiddaC)", "https://github.com/kiddac/E-Stalker"),
    ("enigma2-plugin-extensions-jediepgxtream", "JediEPGXtream", "EPG pour les listes Xtream (KiddaC)", "https://github.com/kiddac/Jedi_EPG_Xtream"),
    ("enigma2-plugin-extensions-xcplugin-forever", "XCplugin Forever", "Lecteur IPTV Xtream (Lululla)", "https://github.com/Belfagor2005/xc_plugin_forever"),
    ("enigma2-plugin-extensions-internet-speedtest", "Internet Speedtest", "Mesure du débit Internet", "https://www.opena.tv"),
    ("enigma2-plugin-extensions-weatherplugin", "WeatherPlugin", "Météo MSN", "https://github.com/oe-alliance/enigma2-plugins"),
    ("enigma2-plugin-extensions-worldcam", "WorldCam", "Webcams du monde entier (Lululla)", "https://github.com/Belfagor2005/WorldCam"),
    ("enigma2-plugin-extensions-apsattv", "ApSatTV", "Chaînes et listes ApSatTV (Lululla)", "https://github.com/Belfagor2005"),
    ("enigma2-plugin-extensions-mmpicons", "mmPicons", "Picons et skins (Lululla & MMark)", "https://github.com/Belfagor2005"),
    ("enigma2-plugin-extensions-chocholousek-picons", "Chocholousek Picons", "Téléchargement de picons satellite", "https://github.com/s3n0/e2plugins"),
    ("enigma2-plugin-extensions-horoscope", "Horoscope", "Horoscope du jour (Lululla)", "https://github.com/Belfagor2005"),
    ("enigma2-plugin-skins-aglare-fhd", "AGlare FHD", "Skin Full HD AGlare (Lululla)", "https://github.com/Belfagor2005"),
    ("enigma2-plugin-skins-maxy-fhd", "Maxy FHD", "Skin Full HD Maxy", "https://www.opena.tv"),
]

RISKY = [
    (r"(wget|curl)[^\n|;]*\|\s*(/usr)?(/bin/)?(ba)?sh\b", "download piped into a shell"),
    (r"base64\s+-d[^\n]*\|\s*(ba)?sh|exec\(\s*base64|eval\(\s*base64", "base64 decoded and executed"),
    (r"telnetd|dropbear\s+-|/etc/init\.d/(telnet|dropbear)\s+start", "starts telnet/ssh server"),
    (r"/etc/shadow|passwd\s+root|chpasswd", "changes passwords"),
    (r"crontab|/etc/cron", "adds a scheduled job"),
    (r"iptables\s+-F|ufw\s+disable", "opens the firewall"),
    (r"marshal\.loads\(|exec\(\s*(zlib|bz2|lzma)\.decompress|exec\(\s*compile\(\s*(base64|codecs)", "obfuscated code executed"),
]


def sources():
    out = {}
    with open(os.path.join(LISTS, "_sources.txt")) as fh:
        for line in fh:
            p = line.split()
            if len(p) >= 3:
                out[p[1]] = p[2].rstrip("/")
    return out


def find(name):
    best = None
    for fn in os.listdir(LISTS):
        if fn.startswith("_"):
            continue
        text = open(os.path.join(LISTS, fn), encoding="utf-8", errors="replace").read()
        for block in text.split("\n\n"):
            if ("Package: %s\n" % name) in block + "\n":
                f = dict(l.split(": ", 1) for l in block.splitlines() if ": " in l and not l.startswith(" "))
                if f.get("Package") == name and (not best or compare_versions(f.get("Version", ""), best[1].get("Version", "")) > 0):
                    best = (fn, f)
    return best


def review(name):
    found = find(name)
    if not found:
        return {"ok": False, "why": "absent du feed OpenATV"}
    feed, f = found
    url = "%s/%s" % (sources()[feed], f["Filename"])
    os.makedirs(CACHE, exist_ok=True)
    path = os.path.join(CACHE, f["Filename"])
    if not os.path.exists(path):
        # curl (system certificate store, TLS verified); sha256 is checked against the feed list below
        import subprocess
        subprocess.check_call(["curl", "-sSfL", "--retry", "2", "-o", path + ".part", url])
        os.replace(path + ".part", path)
    sha = hashlib.sha256(open(path, "rb").read()).hexdigest()
    res = {"version": f["Version"], "feed": feed, "url": url, "sha256": sha, "size": os.path.getsize(path),
           "maintainer": f.get("Maintainer", ""), "depends": f.get("Depends", ""), "issues": [], "elf": []}
    if sha != f.get("SHA256sum", sha):
        res["issues"].append("sha256 différent de la liste du feed")
    n_files = 0
    for arcname, blob in ipk.iter_files(path):
        n_files += 1
        text = blob.decode("utf-8", "replace")
        if blob[:4] == b"\x7fELF":
            res["elf"].append(arcname.split(":", 1)[1])
            if "/Plugins/" in arcname:
                res["issues"].append("code fermé (compilé), impossible à vérifier : %s" % arcname.split(":", 1)[1])
            continue
        for rx, label in scan.HARD:
            if re.search(rx, text):
                res["issues"].append("%s : %s" % (label, arcname))
        is_script = arcname.startswith("control:") or arcname.endswith((".sh", ".py"))
        if is_script:
            for rx, label in RISKY:
                for m in re.finditer(rx, text):
                    ctx = text[max(0, m.start() - 30):m.end() + 30].replace("\n", " ")
                    res["issues"].append("%s : %s  (…%s…)" % (label, arcname.split(":", 1)[1], ctx[:90]))
    res["files"] = n_files
    res["ok"] = not res["issues"]
    return res


def main():
    today = datetime.date.today().isoformat()
    out, lines = [], ["# Sélection communauté — revue du %s" % today, "",
                      "Chaque paquet vient du feed officiel OpenATV 8.0.1 (vuzero4k). Vérifié : sha256 = liste du feed,",
                      "aucune commande à risque dans les scripts d'installation ni dans le code (téléchargement envoyé à un shell,",
                      "base64 exécuté, telnet/ssh, mots de passe, crontab, pare-feu), aucun marqueur du malware connu.", "",
                      "| Plugin | Version vérifiée | Taille | Fichiers | Binaires ELF | Résultat |", "|---|---|---|---|---|---|"]
    for name, title, summary, page in PICKS:
        r = review(name)
        verdict = "OK" if r.get("ok") else "REFUSÉ : " + "; ".join(r.get("issues", [r.get("why", "?")]))[:200]
        print("%-46s %s" % (name, verdict))
        lines.append("| [%s](%s) | %s | %d Ko | %s | %s | %s |" % (
            title, page, r.get("version", "-"), r.get("size", 0) // 1024, r.get("files", "-"),
            len(r.get("elf", [])), verdict))
        if r.get("ok"):
            out.append({"package": name, "title": title, "summary": summary, "page": page,
                        "reviewed_version": r["version"], "reviewed_sha256": r["sha256"], "reviewed": today})
    with open(os.path.join(ROOT, "feed", "community.json"), "w", encoding="utf-8", newline="\n") as fh:
        json.dump(out, fh, ensure_ascii=False, indent=1)
        fh.write("\n")
    with open(os.path.join(ROOT, "feed", "COMMUNITY-REVIEW.md"), "w", encoding="utf-8", newline="\n") as fh:
        fh.write("\n".join(lines) + "\n")
    print("accepted %d / %d" % (len(out), len(PICKS)))


if __name__ == "__main__":
    main()
