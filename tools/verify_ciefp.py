#!/usr/bin/env python3
"""Review Ciefp plugins (github.com/ciefp) before the panel offers them.

Ciefp publishes no .ipk and no licence, so nothing of his code is copied into this repository.
For each plugin this tool:
 1. takes the current commit of the repository and downloads its archive (codeload.github.com),
 2. records the archive sha256 (the receiver refuses any other file),
 3. scans every file that will be installed (.pyc files are never installed) for risky commands
    and refuses compiled code (ELF / .so),
 4. reads the Python 3 dependencies from Ciefp's installer.sh.
Writes feed/ciefp.json (used by build_feed.py) and feed/CIEFP-REVIEW.md.

Usage: python tools/verify_ciefp.py
"""
import datetime
import hashlib
import io
import json
import os
import re
import subprocess
import sys
import tarfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import scan  # noqa: E402
from verify_community import RISKY  # noqa: E402

CACHE = os.path.join(ROOT, "build", "ciefp")

# repository, title, summary
PICKS = [
    ("CiefpE2editor", "Ciefp E2 Editor", "Éditeur avancé de chaînes et de bouquets"),
    ("CiefpSatelliteXmlEditor", "Ciefp Satellite XML Editor", "Modifier le fichier satellites.xml"),
    ("CiefpSignalInfo", "Ciefp Signal Info", "Infos signal et chaîne"),
    ("CiefpPiconManager", "Ciefp Picon Manager", "Gestion avancée des picons"),
    ("CiefpScreenGrab", "Ciefp ScreenGrab", "Captures d'écran de l'interface"),
    ("CiefpBootlogo", "Ciefp Bootlogo", "Créer un logo de démarrage depuis une image"),
    ("CiefpOscamEditor", "Ciefp OSCam Editor", "Modifier oscam.server et oscam.dvbapi"),
    ("CiefpEPGinfo", "Ciefp EPG Info", "Fiche EPG Full HD enrichie (TMDB/OMDb)"),
    ("CiefpSettingsDownloader", "Ciefp Settings Downloader", "Télécharger les listes de chaînes Ciefp"),
    ("CiefpVibes", "Ciefp Vibes", "Juke-box musique locale et en ligne"),
]

# what a plugin may also do over the network or on disk, shown in the review (not a refusal)
NOTES = [
    (r"os\.system\(|subprocess\.", "lance des commandes"),
    (r"requests\.(get|post)|urlopen\(", "télécharge des données"),
]
SAFE_DEP = re.compile(r"^(python3-[a-z0-9.+-]+|ffmpeg|wget|curl|unzip|p7zip|gstreamer1\.0-[a-z0-9.+-]+)$")


def gh(*args):
    return subprocess.check_output(["gh", "api"] + list(args), text=True).strip()


def deps_of(installer):
    out = []
    for m in re.finditer(r"opkg install ([^\n;&|]+)", installer):
        for w in m.group(1).split():
            w = w.strip("'\"")
            if w.startswith("$") or w.startswith("-"):
                continue
            if w.startswith("python-") and not w.startswith("python3"):
                continue  # Python 2 branch
            if SAFE_DEP.match(w) and w not in out:
                out.append(w)
    for var, val in re.findall(r"^\s*(Package\w+)=(python3-[a-z0-9.+-]+)", installer, re.M):
        if val not in out:
            out.append(val)
    return out


def review(repo):
    sha = gh("repos/ciefp/%s/commits/HEAD" % repo, "-q", ".sha")
    date = gh("repos/ciefp/%s/commits/HEAD" % repo, "-q", ".commit.committer.date")[:10]
    os.makedirs(CACHE, exist_ok=True)
    path = os.path.join(CACHE, "%s-%s.tar.gz" % (repo, sha[:12]))
    url = "https://codeload.github.com/ciefp/%s/tar.gz/%s" % (repo, sha)
    if not os.path.exists(path):
        subprocess.check_call(["curl", "-sSfL", "--retry", "2", "-o", path + ".part", url])
        os.replace(path + ".part", path)
    blob = open(path, "rb").read()
    res = {"repo": repo, "commit": sha, "date": date, "url": url, "sha256": hashlib.sha256(blob).hexdigest(),
           "size": len(blob), "issues": [], "notes": set(), "files": 0, "paths": set(), "version": "",
           "depends": []}
    top = "%s-%s/" % (repo, sha)
    with tarfile.open(fileobj=io.BytesIO(blob), mode="r:gz") as tar:
        for ti in tar.getmembers():
            name = ti.name
            if name in (top, top.rstrip("/")) or name == "pax_global_header":
                continue
            if not name.startswith(top):
                res["issues"].append("chemin inattendu : %s" % name)
                continue
            rel = name[len(top):]
            if ti.issym() or ti.islnk():
                if rel.startswith("usr/"):
                    res["issues"].append("lien symbolique : %s" % rel)
                continue
            if not ti.isfile():
                continue
            data = tar.extractfile(ti).read()
            text = data.decode("utf-8", "replace")
            if rel == "installer.sh":
                v = re.search(r"^version='?([\w.\-]+)'?", text, re.M)
                res["version"] = v.group(1) if v else ""
                res["depends"] = deps_of(text)
                continue
            if not rel.startswith("usr/") or rel.endswith(".pyc"):
                continue  # only usr/ is installed, never the .pyc files
            res["files"] += 1
            parts = rel.split("/")
            res["paths"].add("/".join(parts[:7]) if rel.startswith("usr/lib/enigma2/python/Plugins/") else "/".join(parts[:3]))
            if data[:4] == b"\x7fELF" or rel.endswith(".so"):
                res["issues"].append("code compilé : %s" % rel)
                continue
            for rx, label in scan.HARD:
                if re.search(rx, text):
                    res["issues"].append("%s : %s" % (label, rel))
            if rel.endswith((".py", ".sh")):
                for rx, label in RISKY:
                    for m in re.finditer(rx, text):
                        ctx = text[max(0, m.start() - 30):m.end() + 30].replace("\n", " ")
                        res["issues"].append("%s : %s  (…%s…)" % (label, rel, ctx[:90]))
                for rx, label in NOTES:
                    if re.search(rx, text):
                        res["notes"].add(label)
    plug = "usr/lib/enigma2/python/Plugins/Extensions/%s" % repo
    if plug not in res["paths"]:
        res["issues"].append("dossier du plugin absent (%s)" % plug)
    others = sorted(p for p in res["paths"] if p != plug)
    if others:
        res["issues"].append("installe aussi hors de son dossier : %s" % ", ".join(others))
    res["ok"] = not res["issues"]
    return res


def main():
    today = datetime.date.today().isoformat()
    out = []
    lines = ["# Plugins Ciefp — revue du %s" % today, "",
             "Code de [Ciefp](https://github.com/ciefp), téléchargé chez lui à une version figée (commit) et vérifié par empreinte sha256.",
             "Rien de son code n'est copié dans ce dépôt. Installé : le dossier du plugin, sans les fichiers .pyc.",
             "Vérifié : aucun code compilé, aucune commande à risque (téléchargement envoyé à un shell, base64 exécuté,",
             "telnet/ssh, mots de passe, crontab, pare-feu, code obfusqué), rien installé hors du dossier du plugin.", "",
             "| Plugin | Version | Commit | Fichiers | Ce qu'il fait aussi | Résultat |", "|---|---|---|---|---|---|"]
    for repo, title, summary in PICKS:
        r = review(repo)
        verdict = "OK" if r["ok"] else "REFUSÉ : " + "; ".join(r["issues"])[:220]
        print("%-26s %s" % (repo, verdict))
        lines.append("| [%s](https://github.com/ciefp/%s) | %s | %s (%s) | %d | %s | %s |" % (
            title, repo, r["version"] or "-", r["commit"][:7], r["date"], r["files"],
            ", ".join(sorted(r["notes"])) or "-", verdict))
        if r["ok"]:
            out.append({"repo": repo, "title": title, "summary": summary, "version": r["version"] or "0",
                        "commit": r["commit"], "date": r["date"], "url": r["url"], "sha256": r["sha256"],
                        "size": r["size"], "files": r["files"], "depends": r["depends"],
                        "notes": sorted(r["notes"]), "reviewed": today})
    with open(os.path.join(ROOT, "feed", "ciefp.json"), "w", encoding="utf-8", newline="\n") as fh:
        json.dump(out, fh, ensure_ascii=False, indent=1)
        fh.write("\n")
    with open(os.path.join(ROOT, "feed", "CIEFP-REVIEW.md"), "w", encoding="utf-8", newline="\n") as fh:
        fh.write("\n".join(lines) + "\n")
    print("accepted %d / %d" % (len(out), len(PICKS)))


if __name__ == "__main__":
    main()
