# -*- coding: utf-8 -*-
"""Feed index + opkg status helpers for Wacayoub Panel (no enigma2 imports here,
so this file can be tested on a PC)."""
import json
import os
import re

INDEX_URL = "https://raw.githubusercontent.com/wacayoub/WacayoubPanel/main/feed/index.json"
# GitHub API answers with the latest commit (raw.githubusercontent.com is cached ~5 min).
INDEX_API = "https://api.github.com/repos/wacayoub/WacayoubPanel/contents/feed/index.json"
CACHE_DIR = "/etc/enigma2/wacayoubpanel"
CACHE_FILE = CACHE_DIR + "/index.json"
DL_DIR = "/tmp/wacayoubpanel"
OPKG_STATUS = "/var/lib/opkg/status"
ARCH_CONF = "/etc/opkg/arch.conf"

ST_NONE, ST_OK, ST_UPDATE, ST_PARTIAL, ST_NA = range(5)


# ---------------------------------------------------------------- versions
def _split_version(v):
    """Debian-like version -> (epoch, upstream, revision)."""
    v = (v or "").strip()
    epoch = 0
    if ":" in v:
        e, v = v.split(":", 1)
        try:
            epoch = int(e)
        except ValueError:
            epoch = 0
    if "-" in v:
        up, rev = v.rsplit("-", 1)
    else:
        up, rev = v, ""
    return epoch, up, rev


def _order(c):
    if c == "~":
        return -1
    if c.isalpha():
        return ord(c)
    return ord(c) + 256 if c else 0


def _cmp_part(a, b):
    # dpkg's verrevcmp
    while a or b:
        na = re.match(r"[^0-9]*", a).group(0)
        nb = re.match(r"[^0-9]*", b).group(0)
        for i in range(max(len(na), len(nb))):
            ca = _order(na[i]) if i < len(na) else 0
            cb = _order(nb[i]) if i < len(nb) else 0
            if ca != cb:
                return -1 if ca < cb else 1
        a, b = a[len(na):], b[len(nb):]
        da = re.match(r"[0-9]*", a).group(0)
        db = re.match(r"[0-9]*", b).group(0)
        ia, ib = int(da or 0), int(db or 0)
        if ia != ib:
            return -1 if ia < ib else 1
        a, b = a[len(da):], b[len(db):]
    return 0


def compare_versions(a, b):
    """-1 if a<b, 0 if equal, 1 if a>b (dpkg/opkg rules)."""
    ea, ua, ra = _split_version(a)
    eb, ub, rb = _split_version(b)
    if ea != eb:
        return -1 if ea < eb else 1
    return _cmp_part(ua, ub) or _cmp_part(ra, rb)


# ---------------------------------------------------------------- receiver state
def installed_packages(path=OPKG_STATUS):
    """{package: version} for packages whose status is 'install ... installed'."""
    out = {}
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as fh:
            block = {}
            for line in fh.read().split("\n") + [""]:
                if not line.strip():
                    if block.get("Package") and "installed" in block.get("Status", "") \
                            and "not-installed" not in block.get("Status", ""):
                        out[block["Package"]] = block.get("Version", "")
                    block = {}
                    continue
                if ":" in line and line[0] not in " \t":
                    k, v = line.split(":", 1)
                    block[k.strip()] = v.strip()
    except (IOError, OSError):
        pass
    return out


def supported_archs(path=ARCH_CONF):
    archs = {"all", "noarch", "any"}
    try:
        with open(path) as fh:
            for line in fh:
                parts = line.split()
                if len(parts) >= 2 and parts[0] == "arch":
                    archs.add(parts[1])
    except (IOError, OSError):
        pass
    return archs


def free_bytes(path="/"):
    try:
        st = os.statvfs(path)
        return st.f_bavail * st.f_frsize
    except OSError:
        return -1


# ---------------------------------------------------------------- index
class Feed(object):
    def __init__(self, data):
        self.data = data or {}
        self.name = self.data.get("name", "Wacayoub Panel")
        self.updated = self.data.get("updated", "")
        self.categories = self.data.get("categories", [])
        self.packages = self.data.get("packages", {})
        self.items = self.data.get("items", [])

    @classmethod
    def load(cls, path=CACHE_FILE):
        with open(path, "r", encoding="utf-8") as fh:
            data = json.load(fh)
        if not isinstance(data, dict) or "items" not in data or "packages" not in data:
            raise ValueError("index.json invalide")
        return cls(data)

    def items_in(self, cat_id):
        if cat_id in (None, "all"):
            return list(self.items)
        return [i for i in self.items if i.get("category") == cat_id]

    # -- per item state ------------------------------------------------
    def item_state(self, item, installed, archs):
        """Return (state, text) for an item."""
        pkgs = item.get("packages", [])
        for p in pkgs:
            meta = self.packages.get(p)
            if not meta:
                return ST_NA, "absent du feed"
            if meta.get("arch", "all") not in archs:
                return ST_NA, "non compatible"
        main = item.get("main") or (pkgs[0] if pkgs else "")
        if item.get("type") == "script":
            return ST_NONE, "script"
        if main not in installed:
            return ST_NONE, "Non installé"
        upd = self.outdated(item, installed)
        missing = [p for p in pkgs if p not in installed and p not in item.get("optional", [])]
        if upd:
            if main in upd:
                return ST_UPDATE, "Mise à jour %s → %s" % (installed[main], self.packages[main]["version"])
            return ST_UPDATE, "Mise à jour disponible"
        if missing:
            return ST_PARTIAL, "Incomplet (%d manquant)" % len(missing)
        return ST_OK, "Installé %s" % installed[main]

    def outdated(self, item, installed):
        out = []
        for p in item.get("packages", []):
            if p in installed and p in self.packages:
                if compare_versions(installed[p], self.packages[p].get("version", "")) < 0:
                    out.append(p)
        return out

    def to_fetch(self, item, installed):
        """Packages to download for install/update: missing or older ones."""
        res = []
        for p in item.get("packages", []):
            meta = self.packages.get(p)
            if not meta:
                continue
            if p not in installed or compare_versions(installed[p], meta.get("version", "")) < 0:
                res.append(p)
        return res

    def install_size(self, names):
        return sum(int(self.packages[n].get("installed_size", 0) or 0) * 1024 for n in names)


def index_fetch_command(dest):
    """API first (fresh), raw URL as fallback (rate limit or API down)."""
    return ("wget -q -T 20 --header=%s -O %s %s || wget -q -T 20 -O %s %s"
            % (sh_quote("Accept: application/vnd.github.raw"), sh_quote(dest), sh_quote(INDEX_API),
               sh_quote(dest), sh_quote(INDEX_URL)))


def sh_quote(s):
    return "'" + str(s).replace("'", "'\"'\"'") + "'"


def install_commands(feed, names, reinstall=False):
    """Shell lines that download, check sha256 and install the given packages."""
    cmds = ["mkdir -p %s && rm -f %s/*.ipk" % (DL_DIR, DL_DIR)]
    files = []
    for n in names:
        meta = feed.packages[n]
        fname = os.path.basename(meta["file"])
        dest = "%s/%s" % (DL_DIR, fname)
        files.append(dest)
        cmds.append("echo '>>> Téléchargement %s %s'" % (n, meta["version"]))
        cmds.append("wget -q -T 30 -O %s %s || { echo 'ERREUR: téléchargement'; exit 1; }"
                    % (sh_quote(dest), sh_quote(meta["url"])))
        cmds.append("echo %s | sha256sum -c - >/dev/null || { echo 'ERREUR: fichier corrompu (sha256)'; rm -f %s; exit 1; }"
                    % (sh_quote("%s  %s" % (meta["sha256"], dest)), sh_quote(dest)))
    flags = "--force-reinstall " if reinstall else ""
    cmds.append("echo '>>> Installation'")
    cmds.append("opkg install %s%s || { echo 'ERREUR: opkg'; exit 1; }" % (flags, " ".join(sh_quote(f) for f in files)))
    cmds.append("rm -f %s/*.ipk; echo '>>> Terminé avec succès'" % DL_DIR)
    # one script so 'exit 1' stops the whole sequence
    return "\n".join(cmds) + "\n"


def script_commands(feed, item):
    meta = feed.packages[item["packages"][0]]
    dest = "%s/%s" % (DL_DIR, os.path.basename(meta["file"]))
    lines = [
        "mkdir -p %s" % DL_DIR,
        "wget -q -T 30 -O %s %s || { echo 'ERREUR: téléchargement'; exit 1; }" % (sh_quote(dest), sh_quote(meta["url"])),
        "echo %s | sha256sum -c - >/dev/null || { echo 'ERREUR: fichier corrompu (sha256)'; exit 1; }"
        % sh_quote("%s  %s" % (meta["sha256"], dest)),
        "sh %s; rc=$?; rm -f %s; exit $rc" % (sh_quote(dest), sh_quote(dest)),
    ]
    return "\n".join(lines) + "\n"


def remove_commands(names):
    return "opkg remove %s && echo '>>> Supprimé'\n" % " ".join(sh_quote(n) for n in names)


RUN_SCRIPT = DL_DIR + "/run.sh"


def write_run_script(body):
    """Write the job to a file; the Console then shows only 'sh run.sh' and its output."""
    if not os.path.isdir(DL_DIR):
        os.makedirs(DL_DIR)
    with open(RUN_SCRIPT, "w", encoding="utf-8") as fh:
        fh.write("#!/bin/sh\n" + body)
    return ["sh " + RUN_SCRIPT]
