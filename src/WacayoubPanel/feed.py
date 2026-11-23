# -*- coding: utf-8 -*-
"""Feed index + opkg status helpers for Wacayoub Panel (no enigma2 imports here,
so this file can be tested on a PC)."""
import json
import os
import re
import sys

INDEX_URL = "https://raw.githubusercontent.com/wacayoub/WacayoubPanel/main/feed/index.json"
# GitHub API answers with the latest commit (raw.githubusercontent.com is cached ~5 min).
INDEX_API = "https://api.github.com/repos/wacayoub/WacayoubPanel/contents/feed/index.json"
CACHE_DIR = "/etc/enigma2/wacayoubpanel"
CACHE_FILE = CACHE_DIR + "/index.json"
DL_DIR = "/tmp/wacayoubpanel"
IPKCHECK = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ipkcheck.py")
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


def parse_depends(text):
    """'a (>= 1), b | c, d' -> ['a', 'b', 'd'] (first choice of alternatives)."""
    out = []
    for part in (text or "").split(","):
        name = part.split("|")[0].strip().split(" ")[0].split("(")[0].strip()
        if name:
            out.append(name)
    return out


def fold(text):
    """Lowercase without accents, for search."""
    import unicodedata
    t = unicodedata.normalize("NFKD", text or "")
    return "".join(c for c in t if not unicodedata.combining(c)).lower()


STATE_CHARS = 36  # what fits in the list's state column


def update_label(old, new, limit=STATE_CHARS):
    """'Mise à jour 1.0 → 1.1', shortened so it fits the list column (full versions are in the detail card)."""
    text = u"Mise à jour %s → %s" % (old, new)
    if len(text) <= limit:
        return text
    text = u"Mise à jour → %s" % new
    if len(text) <= limit:
        return text
    return text[:limit - 1] + u"…"


def short_version(v, limit=22):
    """'V1.07-git10+0141d090+0141d0911b-r0' -> 'V1.07-git10' (display only)."""
    v = (v or "").split("+")[0].rstrip(".-_~") or (v or "")
    return v if len(v) <= limit else v[:limit - 1] + "…"


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
        # copies: OpenATV entries are added on top without touching the cached index
        self.categories = list(self.data.get("categories", []))
        self.packages = dict(self.data.get("packages", {}))
        self.items = list(self.data.get("items", []))
        self.atv_count = 0
        self.ext_count = 0
        self.ext_sources = []
        self.common = {}
        self.env = {}  # set by the panel: python, model, model_name, width, installed

    def attach_atv(self, atv):
        """Add the image's own feed (OpenATV opkg lists) as extra categories."""
        if not atv or not atv.items:
            return
        # my own packages win over the image feed; curated community picks ("opkg" items
        # in my index) take their package data from the image feed and also stay in the ATV lists
        own = set()
        for it in self.items:
            if it.get("type") != "opkg":
                own.update(it.get("packages", []))
        for c in ATV_CATEGORIES:
            if any(i["category"] == c["id"] for i in atv.items):
                self.categories.append(dict(c))
        for name, meta in atv.packages.items():
            if name not in own:
                self.packages[name] = meta
        for it in atv.items:
            if it["packages"][0] not in own:
                self.items.append(it)
                self.atv_count += 1

    def attach_ext(self, ext):
        """Add other images' feeds (extfeeds.load result), after my items and the image feed."""
        if not ext or self.ext_count:
            return
        cats, packages, items, common = ext
        self.ext_sources = cats  # merged into the ATV categories, kept for the header
        self.common = common  # package -> images that ship it (2 or more)
        for name, meta in packages.items():
            self.packages.setdefault(name, meta)
        for it in items:
            if self.packages.get(it["packages"][0], {}).get("ext") == it.get("ext"):
                self.items.append(it)
                self.ext_count += 1

    @classmethod
    def load(cls, path=CACHE_FILE):
        with open(path, "r", encoding="utf-8") as fh:
            data = json.load(fh)
        if not isinstance(data, dict) or "items" not in data or "packages" not in data:
            raise ValueError("index.json invalide")
        return cls(data)

    # merged lists also show my own plugins / skins (source "Wacayoub")
    MERGE_OWN = {"atv-ext": ("plugin", "panel"), "atv-skins": ("skin",)}

    def items_in(self, cat_id):
        if cat_id in GROUP_IDS:
            out = [i for i in self.items if group_of(i) == cat_id]
            return sorted(out, key=lambda i: fold(i.get("name", "")))
        if cat_id in (None, "all"):
            return [i for i in self.items if i.get("type") not in ("opkg", "ext")]
        if cat_id in self.MERGE_OWN:
            own_types = self.MERGE_OWN[cat_id]
            out = [i for i in self.items if i.get("category") == cat_id or
                   (i.get("type") in own_types and i.get("category") not in ("communaute",))]
            return sorted(out, key=lambda i: fold(i.get("name", "")))
        out = [i for i in self.items if i.get("category") == cat_id]
        if cat_id in ("atv-sys",):  # merged across sources: one alphabetical list
            out.sort(key=lambda i: fold(i.get("name", "")))
        return out

    def search(self, query):
        """Items (mine first, then OpenATV) whose name, package or text contains every word of query.
        Case and accents are ignored."""
        words = [w for w in fold(query).split() if w]
        if not words:
            return []
        hits = []
        for it in self.items:
            hay = fold(" ".join([it.get("name", ""), " ".join(it.get("packages", [])),
                                 it.get("summary", ""), it.get("description", "")]))
            if all(w in hay for w in words):
                score = 0 if fold(it.get("name", "")).startswith(words[0]) else 1
                hits.append(({"opkg": 1, "ext": 2}.get(it.get("type"), 0), score, it.get("name", "").lower(), it))
        hits.sort(key=lambda h: h[:3])
        return [h[3] for h in hits]

    # -- compatibility ---------------------------------------------------
    def compat(self, item, archs=None):
        """[(ok, label)] checks for this receiver: Python, model, screen, package architecture."""
        env = self.env or {}
        req = item.get("requires") or {}
        out = []
        py = env.get("python")
        need_py = req.get("python")
        if py and need_py:
            want = tuple(int(x) for x in str(need_py).split(".")[:2])
            out.append((tuple(py[:len(want)]) >= want, "Python %s (requis %s+)" % (".".join(str(x) for x in py[:2]), need_py)))
        elif py:
            dep = " ".join(self.packages.get(p, {}).get("depends", "") for p in item.get("packages", []))
            if re.search(r"(^|[\s,])python-(?!3)", dep):
                out.append((False, "Python 2 seulement (récepteur en Python %d)" % py[0]))
            elif item.get("type") not in ("image", "launch"):
                out.append((True, "Python %s" % ".".join(str(x) for x in py[:2])))
        model = env.get("model")
        machines = req.get("machines")
        if machines and model:
            out.append((model in machines, "Appareil %s (prévu pour %s)" % (env.get("model_name") or model, ", ".join(machines))))
        elif model and item.get("type") != "launch":
            out.append((True, "Appareil %s" % (env.get("model_name") or model)))
        width = env.get("width")
        if req.get("min_width") and width:
            out.append((width >= req["min_width"], "Écran %d px (skin Full HD, %d px requis)" % (width, req["min_width"])))
        if item.get("type") == "ext":
            meta = self.packages.get(item["packages"][0], {})
            installed = env.get("installed") or {}
            missing = [d for d in meta.get("missing", []) if d not in installed]
            if missing:
                out.append((False, u"Dépendances absentes de cette image : %s" % ", ".join(missing[:4])))
            else:
                out.append((True, u"Dépendances disponibles dans cette image"))
            out.append((True, u"Vient du feed %s (autre image, non testé ici)" % item.get("ext", "?")))
        if archs:
            for p in item.get("packages", []):
                meta = self.packages.get(p)
                if meta and meta.get("arch", "all") not in archs:
                    out.append((False, "Architecture %s non supportée" % meta.get("arch")))
        return out

    # -- per item state ------------------------------------------------
    def item_state(self, item, installed, archs):
        """Return (state, text) for an item."""
        pkgs = item.get("packages", [])
        for p in pkgs:
            meta = self.packages.get(p)
            if not meta:
                return ST_NA, "absent du feed"
        bad = [label for ok, label in self.compat(item, archs) if not ok]
        if bad:
            first = bad[0]
            short = ("Python 2" if first.startswith("Python 2") else "Python" if first.startswith("Python")
                     else u"dépendances" if first.startswith(u"Dépendances")
                     else "autre appareil" if first.startswith("Appareil") else "écran HD" if first.startswith("Écran")
                     else "architecture")
            return ST_NA, "Incompatible : " + short
        main = item.get("main") or (pkgs[0] if pkgs else "")
        if item.get("type") == "script":
            return ST_NONE, "script"
        if main not in installed:
            return ST_NONE, "Non installé"
        upd = self.outdated(item, installed)
        missing = [p for p in pkgs if p not in installed and p not in item.get("optional", [])]
        if upd:
            if main in upd:
                old, new = short_version(installed[main]), short_version(self.packages[main]["version"])
                if old == new:  # same base, different git build: show one more '+' part
                    old = "+".join(installed[main].split("+")[:2])[:24]
                    new = "+".join(self.packages[main]["version"].split("+")[:2])[:24]
                return ST_UPDATE, update_label(old, new)
            return ST_UPDATE, "Mise à jour disponible"
        if missing:
            return ST_PARTIAL, "Incomplet (%d manquant)" % len(missing)
        return ST_OK, "Installé %s" % short_version(installed[main], STATE_CHARS - 9)

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
        # add my own feed packages they depend on (opkg cannot find those in the image feed)
        queue = list(res)
        while queue:
            for dep in parse_depends(self.packages.get(queue.pop(), {}).get("depends", "")):
                meta = self.packages.get(dep)
                if meta and meta.get("url") and not meta.get("ext") and dep not in installed and dep not in res:
                    res.append(dep)
                    queue.append(dep)
        return res

    def install_size(self, names):
        total = 0
        for n in names:
            meta = self.packages.get(n, {})
            isize = int(meta.get("installed_size", 0) or 0) * 1024
            total += isize or int(meta.get("size", 0) or 0)  # feed lists without Installed-Size: use the download size
        return total


# ---------------------------------------------------------------- OpenATV feed
OPKG_LISTS = "/var/lib/opkg/lists"
ATV_CATEGORIES = [
    {"id": "atv-ext", "title": "Toutes · Extensions", "prefixes": ("enigma2-plugin-extensions-",)},
    {"id": "atv-sys", "title": "Toutes · Système", "prefixes": ("enigma2-plugin-systemplugins-",)},
    {"id": "atv-skins", "title": "Toutes · Skins", "prefixes": ("enigma2-plugin-skins-", "enigma2-plugin-skinpacks-")},
    {"id": "atv-settings", "title": "Listes de chaînes", "prefixes": ("enigma2-plugin-settings-",)},
    {"id": "atv-picons", "title": "Picons", "prefixes": ("enigma2-plugin-picons-",)},
    {"id": "atv-softcam", "title": "Softcam", "prefixes": ("enigma2-plugin-softcams-",)},
]

# v2 categories: every source merged (mine = "Wacayoub"), one list per kind of package
GROUPS = [("addons", "Addons"), ("system", "Système"), ("skins", "Skins"), ("softcam", "Softcam"), ("picons", "Picons"),
          ("settings", "Settings"), ("panels", "Panels"), ("multiboot", "Multiboot")]
GROUP_IDS = set(g for g, _t in GROUPS)
MULTIBOOT_WORDS = ("multiboot", "neoboot", "egamiboot", "openmultiboot", "multi-boot")


def group_of(it):
    """Category of an item in the merged lists (None = not listed there)."""
    t = it.get("type")
    if t in ("image", "launch", "script", "feedsrc"):
        return None
    if it.get("category") == "communaute":
        return None  # curated picks: listed in their own category, the same package is in the merged list
    name = (it.get("packages") or [""])[0].lower()
    short = name[len("enigma2-plugin-"):] if name.startswith("enigma2-plugin-") else name
    if any(w in short for w in MULTIBOOT_WORDS):
        return "multiboot"
    if name.startswith("enigma2-plugin-softcams-") or "softcam" in short:
        return "softcam"
    if name.startswith("enigma2-plugin-picons-"):
        return "picons"
    if name.startswith("enigma2-plugin-settings-"):
        return "settings"
    if t == "skin" or name.startswith(("enigma2-plugin-skins-", "enigma2-plugin-skinpacks-")):
        return "skins"
    if "panel" in short.split("-", 1)[-1]:
        return "panels"
    if name.startswith("enigma2-plugin-systemplugins-"):
        return "system"
    return "addons"
ATV_SKIP_SUFFIX = ("-dev", "-dbg", "-src", "-staticdev", "-meta", "-doc", "-po", "-locale", "-common")
ATV_SKIP_NAMES = ("piconmanager", "iptvquickzapguard", "vudoctorpro")


def _pretty(name, prefix):
    short = name[len(prefix):]
    return short.replace("-", " ").strip().title() if short.islower() else short


class AtvCatalog(object):
    """Packages of the image feed read from opkg's downloaded lists (refreshed by 'opkg update')."""

    def __init__(self, lists_dir=OPKG_LISTS, archs=None):
        self.packages, self.items, self.lists_time = {}, [], 0
        self.all_names = set()  # every package (and Provides) this image's feed can install
        try:
            names = sorted(os.listdir(lists_dir))
        except OSError:
            return
        for fn in names:
            path = os.path.join(lists_dir, fn)
            try:
                self.lists_time = max(self.lists_time, int(os.path.getmtime(path)))
                with open(path, "r", encoding="utf-8", errors="replace") as fh:
                    text = fh.read()
            except (IOError, OSError):
                continue
            for m in re.finditer(r"^(Package|Provides): (.+)$", text, re.M):
                for n in m.group(2).split(","):
                    self.all_names.add(n.strip().split(" ")[0])
            for block in text.split("\n\n"):
                if "Package: enigma2-plugin-" not in block:
                    continue
                self._add(block, fn, archs)
        self.items.sort(key=lambda i: (i["category"], i["name"].lower()))

    def _add(self, block, feed_name, archs):
        f = {}
        last = None
        for line in block.split("\n"):
            if line[:1] in (" ", "\t"):
                continue
            if ":" in line:
                last, v = line.split(":", 1)
                f[last.strip()] = v.strip()
        name = f.get("Package", "")
        if not name or name.endswith(ATV_SKIP_SUFFIX) or any(s in name for s in ATV_SKIP_NAMES):
            return
        cat = None
        for c in ATV_CATEGORIES:
            for pre in c["prefixes"]:
                if name.startswith(pre):
                    cat, prefix = c["id"], pre
        if not cat:
            return
        arch = f.get("Architecture", "all")
        if archs and arch not in archs:
            return  # other receiver / CPU: never offered
        if sys.version_info[0] >= 3 and re.search(r"(^|[\s,])python-(?!3)", f.get("Depends", "")):
            return  # Python 2 plugin on a Python 3 image: never offered
        version = f.get("Version", "")
        old = self.packages.get(name)
        if old and compare_versions(old["version"], version) >= 0:
            return
        try:
            size = int(f.get("Size", "0") or 0)
            isize = int(f.get("Installed-Size", "0") or 0)
        except ValueError:
            size, isize = 0, 0
        if isize > 100000:  # some feeds give bytes instead of KiB
            isize //= 1024
        self.packages[name] = {"version": version, "arch": arch, "file": name, "url": "", "sha256": "",
                               "size": size, "installed_size": isize, "depends": f.get("Depends", ""),
                               "source": feed_name}
        desc = f.get("Description", "").strip()
        if not desc or desc.startswith(name) or desc.lower().startswith(name[len(prefix):].lower() + " version"):
            desc = u"Pas de description"
        if not old:
            self.items.append({"id": "opkg:" + name, "name": _pretty(name, prefix), "category": cat,
                               "type": "opkg", "summary": desc[:110],
                               "description": "%s  (feed %s)" % (desc, feed_name), "packages": [name]})
        else:
            for it in self.items:
                if it["packages"][0] == name:
                    it["description"] = "%s  (feed %s)" % (desc, feed_name)


def opkg_install_commands(names, reinstall=False):
    flags = "--force-reinstall " if reinstall else ""
    return ("echo '>>> Installation depuis le feed OpenATV'\n"
            "opkg install %s%s || { echo 'ERREUR: opkg (essayez JAUNE pour mettre les listes à jour)'; exit 1; }\n"
            "echo '>>> Terminé avec succès'\n" % (flags, " ".join(sh_quote(n) for n in names)))


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
        algo, digest = ("sha256", meta.get("sha256")) if meta.get("sha256") else ("md5", meta.get("md5"))
        cmds.append("echo %s | %ssum -c - >/dev/null || { echo 'ERREUR: fichier corrompu (%s)'; rm -f %s; exit 1; }"
                    % (sh_quote("%s  %s" % (digest, dest)), algo, algo, sh_quote(dest)))
        if meta.get("native"):  # CPU-feed package from another image: open it and refuse compiled code
            cmds.append("python3 %s %s || { rm -f %s; exit 1; }"
                        % (sh_quote(IPKCHECK), sh_quote(dest), sh_quote(dest)))
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


def write_run_script(body, name="run.sh"):
    """Write the job to a file; the Console then shows only 'sh run.sh' and its output."""
    if not os.path.isdir(DL_DIR):
        os.makedirs(DL_DIR)
    path = os.path.join(DL_DIR, name)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write("#!/bin/sh\n" + body)
    return ["sh " + path]
