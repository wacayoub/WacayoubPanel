# -*- coding: utf-8 -*-
"""Firmware images for the detected receiver (download only; flashing is done by the user
with the image's own Flash Manager). Same sources as OpenATV's Flash Manager."""
import json
import os
import time

OPENATV_JSON = "https://images.mynonpublic.com/openatv/json/%s"
DISTROS_JSON = "https://raw.githubusercontent.com/OpenATV/FlashImage/gh-pages/%s.json"
WORK = "/tmp/wacayoubpanel/images"
IMAGE_DIRS = ("/media/hdd", "/media/usb", "/media/mmc", "/media/usb2")


def box_model():
    """(machinebuild, display name) e.g. ('vuzero4k', 'Vu+ Zero 4K')."""
    build, name = "", ""
    try:
        from Components.SystemInfo import BoxInfo
        build = BoxInfo.getItem("machinebuild") or BoxInfo.getItem("model") or ""
        name = ("%s %s" % (BoxInfo.getItem("displaybrand") or "", BoxInfo.getItem("displaymodel") or "")).strip()
    except Exception:
        pass
    if not build:
        try:
            with open("/etc/hostname") as fh:
                build = fh.read().strip()
        except (IOError, OSError):
            build = ""
    return build, name or build


def image_dir():
    """Folder where Flash Manager looks for downloaded images, or None."""
    for base in IMAGE_DIRS:
        if os.path.ismount(base):
            return os.path.join(base, "images")
    return None


def fetch_script(model):
    """Shell script that downloads the distribution list then each distribution's JSON."""
    lines = [
        "mkdir -p %s && rm -f %s/*.json" % (WORK, WORK),
        "wget -q -T 20 -O %s/0-OpenATV.json '%s'" % (WORK, OPENATV_JSON % model),
        "wget -q -T 20 -O %s/distros.json '%s' || exit 0" % (WORK, DISTROS_JSON % model),
        "python3 - <<'EOF'",
        "import json, subprocess",
        "try:",
        "    d = json.load(open('%s/distros.json'))" % WORK,
        "except Exception:",
        "    d = []",
        "for n, (name, url) in enumerate(d, 1):",
        "    safe = ''.join(c for c in name if c.isalnum()) or 'img'",
        "    subprocess.call(['wget', '-q', '-T', '20', '-O', '%s/%%d-%%s.json' %% (n, safe), url])" % WORK,
        "EOF",
        "exit 0",
    ]
    return "\n".join(lines) + "\n"


def _human(n):
    n = float(n or 0)
    for unit in ("o", "Ko", "Mo", "Go"):
        if n < 1024 or unit == "Go":
            return ("%.0f %s" if unit in ("o", "Ko", "Mo") else "%.1f %s") % (n, unit)
        n /= 1024.0


def load_catalog(work=WORK):
    """[(distro, [image items])] from the downloaded JSON files, newest first in each distro."""
    out = []
    try:
        files = sorted(f for f in os.listdir(work) if f.endswith(".json") and f != "distros.json")
    except OSError:
        return out
    for fn in files:
        distro = fn.split("-", 1)[1][:-5] if "-" in fn else fn[:-5]
        try:
            with open(os.path.join(work, fn), "rb") as fh:
                data = json.loads(fh.read().decode("utf-8-sig"))
        except Exception:
            continue
        items = []
        if not isinstance(data, dict):
            continue
        for group, imgs in data.items():
            if not isinstance(imgs, dict):
                continue
            for key, meta in imgs.items():
                if not isinstance(meta, dict) or not meta.get("link"):
                    continue
                name = meta.get("name") or os.path.basename(meta["link"])
                try:
                    size = int(meta.get("size") or 0)
                    date = int(meta.get("date") or 0)
                except ValueError:
                    size, date = 0, 0
                day = time.strftime("%d/%m/%Y", time.localtime(date)) if date else ""
                items.append({
                    "id": "img:" + name, "type": "image", "category": "img-" + distro.lower(),
                    "name": "%s %s" % (distro, group) if not group.lower().startswith(distro.lower()) else group,
                    "summary": "%s  ·  %s  ·  %s" % (name, _human(size), day),
                    "description": "Image %s (%s) pour ce récepteur.\nTéléchargée dans le dossier images, à flasher ensuite avec Menu > Flash Manager (Images téléchargées)." % (distro, group),
                    "file": name, "url": meta["link"], "size": size, "date": date, "distro": distro,
                    "packages": [],
                })
        items.sort(key=lambda i: -i["date"])
        if items:
            out.append((distro, items))
    return out


def download_commands(item, dest_dir):
    dest = os.path.join(dest_dir, item["file"])
    q = lambda s: "'" + str(s).replace("'", "'\"'\"'") + "'"
    return "\n".join([
        "mkdir -p %s" % q(dest_dir),
        "echo '>>> Téléchargement de %s (%s)'" % (item["file"].replace("'", ""), _human(item["size"])),
        "wget -T 30 --progress=dot:giga -O %s %s 2>&1 | grep -E '%%|saved|ERROR' || true" % (q(dest + ".part"), q(item["url"])),
        "[ -s %s ] || { echo 'ERREUR: téléchargement'; rm -f %s; exit 1; }" % (q(dest + ".part"), q(dest + ".part")),
        "python3 -c \"import zipfile,sys; sys.exit(0 if zipfile.is_zipfile(sys.argv[1]) else 1)\" %s || { echo 'ERREUR: fichier zip invalide'; rm -f %s; exit 1; }" % (q(dest + ".part"), q(dest + ".part")),
        "mv %s %s" % (q(dest + ".part"), q(dest)),
        "echo '>>> Image enregistrée : %s'" % dest.replace("'", ""),
        "echo '>>> Pour flasher : Menu > Flash Manager > Images téléchargées.'",
    ]) + "\n"
