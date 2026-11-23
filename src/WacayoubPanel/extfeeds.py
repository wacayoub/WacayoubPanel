# -*- coding: utf-8 -*-
"""Plugins from other images' feeds (OpenPLi, EGAMI, OpenViX, OpenBH, OpenHDF, OpenSPA).

Safety rules:
- these feeds are never added to opkg: the panel downloads one .ipk, checks its SHA256 (or MD5) against the
  feed's Packages file and installs it with `opkg install <file>`, so dependencies only come from this image;
- "all" feeds (Python plugins, skins) are offered as they are;
- CPU feeds (same processor as this receiver) are offered too, but each package is opened before install
  (ipkcheck.py) and refused if it holds compiled code (ELF) or Python bytecode without its source:
  bytecode built for another image's Python does not load here;
- system components (network, software manager, boot/multiboot, CI) are never offered;
- a package is blocked if a dependency is missing in this image, it is Python 2, or this image already ships it.
"""
import gzip
import os
import re
import sys
import time

WORK = "/tmp/wacayoubpanel/ext"

# name, category id, "all" feed URLs tried in order, CPU feed URL templates ({m} machine, {a} architecture)
FEEDS = [
    ("OpenPLi", "ext-openpli", ["http://downloads.openpli.org/feeds/openpli-9-release/all"],
     ["http://downloads.openpli.org/feeds/openpli-9-release/{a}"]),
    ("EGAMI", "ext-egami", ["http://egami-feed.com/feeds/egami/11.0/{m}/all"],
     ["http://egami-feed.com/feeds/egami/11.0/{m}/{a}"]),
    ("OpenViX", "ext-openvix", ["https://www.openvix.co.uk/feeds/openvix/release/6.9/{m}/all"],
     ["https://www.openvix.co.uk/feeds/openvix/release/6.9/{m}/{a}"]),
    ("OpenHDF", "ext-openhdf", ["https://feed.hdfreaks.cc/V8.0/{m}/all", "https://feed.hdfreaks.cc/V7.5/{m}/all"],
     ["https://feed.hdfreaks.cc/V8.0/{m}/{a}"]),
    ("OpenSPA", "ext-openspa", ["https://openspa.webhop.info/feeds/oea/8.7/{m}/all"],
     ["https://openspa.webhop.info/feeds/oea/8.7/{m}/{a}"]),
    ("OpenBH", "ext-openbh", ["http://feeds2.openbh.net/openbh/6.0/{m}/all", "http://feeds2.openbh.net/openbh/5.6/{m}/all",
                              "http://feeds.openbh.net/6.0/{m}/all", "http://feeds.openbh.net/5.6/{m}/all"],
     ["http://feeds2.openbh.net/openbh/5.6/{m}/{a}", "http://feeds.openbh.net/5.6/{m}/{a}"]),
]
PREFIXES = ("enigma2-plugin-extensions-", "enigma2-plugin-systemplugins-", "enigma2-plugin-skins-")
# open-source softcams only (OSCam, NCam), official builds of the image feeds; closed binaries (CCcam, mgcamd) are left out
SOFTCAM_RE = re.compile(r"^enigma2-plugin-softcams-(oscam|ncam)(-[a-z0-9]+)*$")
SOFTCAM_FIXED_DEPS = ("softcam-support", "libusb1")  # rewritten by ipkfix.py before install
# merged lists: other images' packages go into the same categories as the image's own feed
MERGED_CAT = {"enigma2-plugin-extensions-": "atv-ext", "enigma2-plugin-systemplugins-": "atv-sys", "enigma2-plugin-skins-": "atv-skins"}
SKIP_SUFFIX = ("-dev", "-dbg", "-src", "-staticdev", "-meta", "-doc", "-po", "-locale")
# never offered from another image: they replace parts of this image's system
SYSTEM_WORDS = ("softcamsetup", "softwaremanager", "networkwizard", "wirelesslan", "networkbrowser", "inifansetup", "boot", "socketmmi",
                "ciplushelper", "fastboot", "flashexpander", "imagemanager", "recoverymanager", "videomode", "hdmicec")


def cpu_archs(archs):
    """Architectures that can have their own feed folder (all/any/noarch are the 'all' feed)."""
    return sorted(a for a in archs if a not in ("all", "any", "noarch", "private", "ocram") and not a.startswith("static"))


def fetch_script(model, archs=()):
    """Shell script downloading each feed's Packages.gz: the 'all' feed (first URL that answers) and the CPU feeds."""
    lines = ["mkdir -p %s && rm -f %s/*.gz %s/*.base" % (WORK, WORK, WORK)]
    for name, _cat, urls, cpu in FEEDS:
        tries = " || ".join("(wget -q -T 20 -U opkg -O %s/%s.gz '%s/Packages.gz' && echo '%s' > %s/%s.base)"
                            % (WORK, name, u.format(m=model), u.format(m=model), WORK, name) for u in urls)
        lines.append("%s || rm -f %s/%s.gz %s/%s.base" % (tries, WORK, name, WORK, name))
        for a in cpu_archs(archs):
            key = "%s@%s" % (name, a)
            tries = " || ".join("(wget -q -T 20 -U opkg -O %s/%s.gz '%s/Packages.gz' && echo '%s' > %s/%s.base)"
                                % (WORK, key, u.format(m=model, a=a), u.format(m=model, a=a), WORK, key) for u in cpu)
            lines.append("%s || rm -f %s/%s.gz %s/%s.base" % (tries, WORK, key, WORK, key))
    lines.append("exit 0")
    return "\n".join(lines) + "\n"


def _pretty(name):
    if name.startswith("enigma2-plugin-softcams-"):
        short = name[len("enigma2-plugin-softcams-"):].replace("-", " ").title()
        return short.replace("Oscam", "OSCam").replace("Ncam", "NCam").replace("Emu", "EMU").replace("Pcscd", "PCSCD")
    for pre in PREFIXES:
        if name.startswith(pre):
            short = name[len(pre):]
            return short.replace("-", " ").strip().title() if short.islower() else short
    return name


def _read(name):
    """[(base_url, packages_text, is_cpu_feed)] for one image."""
    out = []
    try:
        files = sorted(f for f in os.listdir(WORK) if f.endswith(".gz") and (f == name + ".gz" or f.startswith(name + "@")))
    except OSError:
        return out
    for fn in files:
        try:
            with open(os.path.join(WORK, fn[:-3] + ".base")) as fh:
                base = fh.read().strip()
            with gzip.open(os.path.join(WORK, fn), "rt", encoding="utf-8", errors="replace") as fh:
                out.append((base, fh.read(), "@" in fn))
        except (IOError, OSError, EOFError):
            continue
    return out


_LOADED = {}


def _work_sig():
    try:
        return tuple((f, int(os.path.getmtime(os.path.join(WORK, f)))) for f in sorted(os.listdir(WORK)))
    except OSError:
        return ()


def load(own_names, available, compare_versions, image_names=(), archs=()):
    """Cached _load(): parsed again only when the downloaded feeds or the inputs changed."""
    key = (_work_sig(), hash(frozenset(own_names)), hash(frozenset(available)), hash(frozenset(image_names)),
           tuple(sorted(archs)))
    if _LOADED.get("key") != key:
        _LOADED.update(key=key, value=_load(own_names, available, compare_versions, image_names, archs))
    return _LOADED["value"]


def _load(own_names, available, compare_versions, image_names=(), archs=()):
    """Return (categories, packages, items, common) for the feeds downloaded in WORK.
    own_names: packages already offered by this image's feed or mine (skipped);
    available: every package name this image can install or has installed (dependency check);
    image_names: this image's plugin packages (to find tools shared with other images);
    archs: this receiver's architectures (CPU feed packages must match one)."""
    cats, packages, items, seen = [], {}, [], set(own_names)
    archs = set(archs)
    where = {}  # package -> images shipping it: 2+ images = "Universel"
    for n in image_names:
        where.setdefault(n, set()).add("OpenATV")
    for name, cat, _urls, _cpu in FEEDS:
        best = {}
        for base, text, is_cpu in _read(name):
            for block in text.split("\n\n"):
                f = {}
                for line in block.split("\n"):
                    if line[:1] in (" ", "\t") or ":" not in line:
                        continue
                    k, v = line.split(":", 1)
                    f[k.strip()] = v.strip()
                pkg = f.get("Package", "")
                arch = f.get("Architecture", "")
                softcam = bool(SOFTCAM_RE.match(pkg))
                if not (pkg.startswith(PREFIXES) or softcam) or pkg.endswith(SKIP_SUFFIX):
                    continue
                if arch != "all" and arch not in archs:
                    continue
                if any(w in pkg[len("enigma2-plugin-"):] for w in SYSTEM_WORDS):
                    continue
                where.setdefault(pkg, set()).add(name)
                if pkg in seen or not f.get("Filename") or not (f.get("SHA256sum") or f.get("MD5Sum")):
                    continue
                if sys.version_info[0] >= 3 and re.search(r"(^|[\s,])python-(?!3)", f.get("Depends", "")):
                    continue
                if softcam and [d for d in _deps(f) if d not in available and d not in SOFTCAM_FIXED_DEPS]:
                    continue  # binary built against libraries this image does not have: try the next image
                old = best.get(pkg)
                if old and compare_versions(old[0].get("Version", ""), f.get("Version", "")) >= 0:
                    continue
                best[pkg] = (f, base, arch != "all")
        n = 0
        for pkg, (f, base, native) in sorted(best.items()):
            softcam = bool(SOFTCAM_RE.match(pkg))
            missing = [d for d in _deps(f) if d not in available and not (softcam and d in SOFTCAM_FIXED_DEPS)]
            try:
                size = int(f.get("Size", "0") or 0)
                isize = int(f.get("Installed-Size", "0") or 0)
            except ValueError:
                size, isize = 0, 0
            packages[pkg] = {"version": f.get("Version", ""), "arch": f.get("Architecture", "all"),
                             "file": os.path.basename(f["Filename"]), "url": "%s/%s" % (base, f["Filename"]),
                             "sha256": f.get("SHA256sum", ""), "md5": f.get("MD5Sum", ""), "size": size,
                             "installed_size": isize // 1024 if isize > 100000 else isize, "depends": f.get("Depends", ""),
                             "ext": name, "missing": missing, "native": native, "softcam": softcam}
            desc = (f.get("Description", "") or "").strip()
            if not desc or desc.startswith(pkg):
                desc = u"Pas de description"
            if softcam:
                cam = pkg[len("enigma2-plugin-softcams-"):]
                note = (u"Binaire officiel open source du feed %s, compilé pour ce processeur : lancé après l'installation "
                        u"et désinstallé s'il ne démarre pas. Config : /etc/tuxbox/config/%s/ (gardée aux mises à jour). "
                        u"Ensuite : Menu > Configuration > Softcam pour l'activer." % (name, cam))
            else:
                note = None
            note = note or (u"Paquet compilé pour le processeur, vérifié à l'installation : refusé s'il contient du code binaire "
                    u"ou du Python sans source (il ne marcherait pas ici)." if native else
                    u"Installé tel quel, dépendances prises dans OpenATV uniquement.")
            merged = [c for pre, c in MERGED_CAT.items() if pkg.startswith(pre)]
            items.append({"id": "ext:%s:%s" % (name, pkg), "type": "ext", "category": merged[0] if merged else cat,
                          "name": _pretty(pkg), "summary": desc[:110], "packages": [pkg], "ext": name,
                          "description": u"%s\nPaquet du feed %s (image différente). %s Non testé sur OpenATV." % (desc, name, note)})
            seen.add(pkg)
            n += 1
        if n:
            cats.append({"id": cat, "title": name, "count": n})  # info only: lists are merged
    items.sort(key=lambda i: (i["category"], i["name"].lower()))
    common = dict((p, sorted(s)) for p, s in where.items() if len(s) >= 2)
    return cats, packages, items, common


def _deps(f):
    return [d.split("|")[0].strip().split(" ")[0] for d in f.get("Depends", "").split(",") if d.strip()]


def age_hours():
    try:
        ts = [os.path.getmtime(os.path.join(WORK, f)) for f in os.listdir(WORK) if f.endswith(".gz")]
        return (time.time() - max(ts)) / 3600.0 if ts else 1e9
    except OSError:
        return 1e9
