# -*- coding: utf-8 -*-
"""Plugins from other images' feeds (OpenPLi, EGAMI, OpenViX, OpenBH).

Safety rules:
- only the architecture-independent "all" feeds (Python plugins, skins): no binaries built for another image;
- these feeds are never added to opkg: the panel downloads one .ipk, checks its SHA256 against the feed's
  Packages file and installs it with `opkg install <file>`, so dependencies only come from this image;
- a package is offered only if all its dependencies exist in this image's feed or are already installed,
  it is not Python 2, and the same package is not already offered by this image's own feed.
"""
import gzip
import os
import re
import sys
import time

WORK = "/tmp/wacayoubpanel/ext"

# name, category id, list of base URLs tried in order ({m} = machine build, e.g. vuzero4k)
FEEDS = [
    ("OpenPLi", "ext-openpli", ["http://downloads.openpli.org/feeds/openpli-9-release/all"]),
    ("EGAMI", "ext-egami", ["http://egami-feed.com/feeds/egami/11.0/{m}/all"]),
    ("OpenViX", "ext-openvix", ["https://www.openvix.co.uk/feeds/openvix/release/6.9/{m}/all"]),
    ("OpenBH", "ext-openbh", ["http://feeds2.openbh.net/openbh/6.0/{m}/all", "http://feeds2.openbh.net/openbh/5.6/{m}/all",
                              "http://feeds.openbh.net/6.0/{m}/all", "http://feeds.openbh.net/5.6/{m}/all"]),
]
PREFIXES = ("enigma2-plugin-extensions-", "enigma2-plugin-systemplugins-", "enigma2-plugin-skins-")
SKIP_SUFFIX = ("-dev", "-dbg", "-src", "-staticdev", "-meta", "-doc", "-po", "-locale")


def fetch_script(model):
    """Shell script downloading each feed's Packages.gz (first URL that answers)."""
    lines = ["mkdir -p %s" % WORK]
    for name, _cat, urls in FEEDS:
        # first URL that answers wins; its base is remembered for the download links
        tries = " || ".join("(wget -q -T 20 -U opkg -O %s/%s.gz '%s/Packages.gz' && echo '%s' > %s/%s.base)"
                            % (WORK, name, u.format(m=model), u.format(m=model), WORK, name) for u in urls)
        lines.append("%s || rm -f %s/%s.gz %s/%s.base" % (tries, WORK, name, WORK, name))
    lines.append("exit 0")
    return "\n".join(lines) + "\n"


def _pretty(name):
    for pre in PREFIXES:
        if name.startswith(pre):
            short = name[len(pre):]
            return short.replace("-", " ").strip().title() if short.islower() else short
    return name


def load(own_names, available, compare_versions):
    """Return (categories, packages, items) for the feeds downloaded in WORK.
    own_names: packages already offered by this image's feed or mine (skipped);
    available: every package name this image can install or has installed (dependency check)."""
    cats, packages, items, seen = [], {}, [], set(own_names)
    for name, cat, _urls in FEEDS:
        gz = os.path.join(WORK, name + ".gz")
        base_file = os.path.join(WORK, name + ".base")
        if not os.path.exists(gz) or not os.path.exists(base_file):
            continue
        try:
            with open(base_file) as fh:
                base = fh.read().strip()
            with gzip.open(gz, "rt", encoding="utf-8", errors="replace") as fh:
                text = fh.read()
        except (IOError, OSError, EOFError):
            continue
        mtime = int(os.path.getmtime(gz))
        best = {}
        for block in text.split("\n\n"):
            f = {}
            for line in block.split("\n"):
                if line[:1] in (" ", "\t") or ":" not in line:
                    continue
                k, v = line.split(":", 1)
                f[k.strip()] = v.strip()
            pkg = f.get("Package", "")
            if not pkg.startswith(PREFIXES) or pkg.endswith(SKIP_SUFFIX) or f.get("Architecture") != "all":
                continue
            if pkg in seen or not f.get("Filename") or not (f.get("SHA256sum") or f.get("MD5Sum")):
                continue
            if sys.version_info[0] >= 3 and re.search(r"(^|[\s,])python-(?!3)", f.get("Depends", "")):
                continue
            old = best.get(pkg)
            if old and compare_versions(old.get("Version", ""), f.get("Version", "")) >= 0:
                continue
            best[pkg] = f
        n = 0
        for pkg, f in sorted(best.items()):
            deps = [d.split("|")[0].strip().split(" ")[0] for d in f.get("Depends", "").split(",") if d.strip()]
            missing = [d for d in deps if d and d not in available]
            try:
                size = int(f.get("Size", "0") or 0)
                isize = int(f.get("Installed-Size", "0") or 0)
            except ValueError:
                size, isize = 0, 0
            packages[pkg] = {"version": f.get("Version", ""), "arch": "all", "file": os.path.basename(f["Filename"]),
                             "url": "%s/%s" % (base, f["Filename"]), "sha256": f.get("SHA256sum", ""), "md5": f.get("MD5Sum", ""), "size": size,
                             "installed_size": isize // 1024 if isize > 100000 else isize, "depends": f.get("Depends", ""),
                             "ext": name, "missing": missing}
            desc = (f.get("Description", "") or "").strip()
            if not desc or desc.startswith(pkg):
                desc = "Paquet du feed %s" % name
            items.append({"id": "ext:%s:%s" % (name, pkg), "type": "ext", "category": cat, "name": _pretty(pkg),
                          "summary": desc[:110], "packages": [pkg], "ext": name,
                          "description": u"%s\nPaquet du feed %s (image différente) : installé tel quel, dépendances prises dans OpenATV uniquement. "
                                         u"Non testé sur OpenATV." % (desc, name)})
            seen.add(pkg)
            n += 1
        if n:
            cats.append({"id": cat, "title": u"Autres · %s" % name, "time": mtime})
    items.sort(key=lambda i: (i["category"], i["name"].lower()))
    return cats, packages, items


def age_hours():
    try:
        ts = [os.path.getmtime(os.path.join(WORK, f)) for f in os.listdir(WORK) if f.endswith(".gz")]
        return (time.time() - max(ts)) / 3600.0 if ts else 1e9
    except OSError:
        return 1e9
