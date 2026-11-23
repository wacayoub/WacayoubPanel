# -*- coding: utf-8 -*-
"""Fixo: reads the enigma2 crash logs, finds the plugin and the error, and proposes a fix.

Knowledge comes from three places:
- built-in rules below;
- online rules embedded in the panel's feed index ("doctor_rules", fetched fresh from GitHub at each analysis);
- the package feeds (opkg update + my feed): is there a newer version of the plugin that crashed?
Fix types are a fixed whitelist (install / update / reinstall / disable / restore / script / archive);
online rules can only choose among them. No enigma2 imports here, so it runs on its own for tests:
    python3 docteur.py
"""
import glob
import json
import os
import re
import time

try:
    from . import feed as F
    from . import garde as G
except ImportError:  # run directly for tests
    import feed as F
    import garde as G

LOG_GLOBS = ("/home/root/logs/*crash*.log", "/media/hdd/*crash*.log", "/media/usb/*crash*.log", "/media/hdd/logs/*crash*.log")
ARCHIVE = "/home/root/logs/wacayoub-archive"
QUARANTINE = "/home/root/wacayoub-quarantine"
PLUGIN_ROOT = "/usr/lib/enigma2/python/Plugins"
OPKG_INFO = "/var/lib/opkg/info"
OPKG_LISTS = ("/var/lib/opkg/lists", "/var/cache/opkg")
PKG_RE = re.compile(r"^[a-z0-9][a-z0-9.+-]*$")
TS_RE = re.compile(r"^\d\d:\d\d:\d\d\.\d+\s?")
FRAME_RE = re.compile(r'^\s*File "([^"]+)", line (\d+), in (\S+)')
EXC_RE = re.compile(r"^([A-Za-z_][\w.]*(?:Error|Exception|Exit|Interrupt|Warning|Iteration|error))(?::\s*(.*))?$")
PLUGIN_PATH_RE = re.compile(r"/Plugins/(Extensions|SystemPlugins)/([\w.-]+)")

# Python module -> OpenATV package (when the name differs from python3-<module>)
MODULE_MAP = {
    "PIL": "python3-pillow", "Crypto": "python3-pycryptodome", "Cryptodome": "python3-pycryptodomex",
    "bs4": "python3-beautifulsoup4", "yaml": "python3-pyyaml", "OpenSSL": "python3-pyopenssl", "dateutil": "python3-dateutil",
    "twisted": "python3-twisted", "serial": "python3-pyserial", "usb": "python3-pyusb", "magic": "python3-magic",
    "google": "python3-protobuf", "socks": "python3-pysocks", "Levenshtein": "python3-levenshtein", "cv2": "python3-opencv",
    "sqlite3": "python3-sqlite3", "lxml": "python3-lxml", "requests": "python3-requests", "six": "python3-six",
    "js2py": "python3-js2py", "mechanize": "python3-mechanize", "chardet": "python3-chardet", "certifi": "python3-certifi",
    "urllib3": "python3-urllib3", "treq": "python3-treq", "pyexecjs": "python3-pyexecjs", "execjs": "python3-pyexecjs",
    "rarfile": "python3-rarfile", "cryptography": "python3-cryptography", "pytz": "python3-pytz", "simplejson": "python3-simplejson",
    "future": "python3-future", "past": "python3-future", "html5lib": "python3-html5lib", "zope": "python3-zopeinterface",
    "yt_dlp": "python3-yt-dlp", "youtube_dl": "python3-youtube-dl", "streamlink": "streamlink", "netifaces": "python3-netifaces",
    "ntplib": "python3-ntplib", "pyotp": "python3-pyotp", "qrcode": "python3-qrcode", "json": "python3-json",
}

# Built-in rules. Online rules (index "doctor_rules") use the same keys and come first.
# match: regex on the exception line; where: optional regex on the traceback text; fix: see FIX_TYPES.
BUILTIN_RULES = [
    {"id": "nospace", "match": r"No space left on device|Errno 28", "level": "red",
     "title": u"Mémoire flash pleine", "explain": u"Le système n'a plus de place : Enigma2 ne peut plus écrire ses fichiers.",
     "fix": "script:t-flash-pleine"},
    {"id": "memory", "match": r"MemoryError|Cannot allocate memory|Errno 12", "level": "red",
     "title": u"Mémoire RAM épuisée", "explain": u"Le récepteur a manqué de RAM. Libérer la mémoire ou créer un swap aide.",
     "fix": "script:t-lent"},
    {"id": "readonly", "match": r"Read-only file system|Errno 30", "level": "red",
     "title": u"Disque en lecture seule", "explain": u"Un disque ou la flash est passé en lecture seule (erreur disque).",
     "fix": "script:t-disque-info"},
    {"id": "marshal", "match": r"bad marshal data|unknown magic number|EOFError: marshal|ImportError: bad magic", "level": "amber",
     "title": u"Fichiers du plugin abîmés", "explain": u"Des fichiers compilés du plugin sont corrompus (coupure, flash pleine). Une réinstallation les remplace.",
     "fix": "reinstall"},
    {"id": "py2", "match": r"^SyntaxError", "where": r"print |Missing parentheses|invalid syntax", "level": "amber",
     "title": u"Plugin écrit pour Python 2", "explain": u"Ce plugin utilise une syntaxe Python 2 : il ne marche pas sur Python 3.",
     "fix": "update_or_disable"},
    {"id": "skin", "match": r"SkinError|skin\.xml|in applySkin|SkinException", "level": "amber",
     "title": u"Erreur du skin", "explain": u"Le skin actif a un écran ou une police manquante pour un plugin.",
     "fix": "update_or_script:t-skin-defaut"},
    {"id": "ssl", "match": r"CERTIFICATE_VERIFY_FAILED|SSLError|certificate verify failed", "level": "amber",
     "title": u"Connexion sécurisée refusée", "explain": u"Souvent l'heure du récepteur est fausse, donc les certificats HTTPS semblent invalides.",
     "fix": "script:t-heure"},
    {"id": "dns", "match": r"Temporary failure in name resolution|Name or service not known|Errno -[23]|getaddrinfo failed", "level": "amber",
     "title": u"Internet ou DNS en panne", "explain": u"Le plugin n'a pas pu joindre son serveur (Internet coupé ou DNS en panne).",
     "fix": "script:t-internet"},
    {"id": "badcallback", "match": r"'bool' object is not callable|'NoneType' object is not callable", "where": r"execBegin|onShown|onLayoutFinish|onExecBegin",
     "level": "amber", "title": u"Plugin incompatible avec les écrans OpenATV",
     "explain": u"Un plugin a mis une valeur au lieu d'une fonction dans les événements d'un écran (onShown, onLayoutFinish).", "fix": "update_or_disable"},
    {"id": "importname", "match": r"cannot import name|module '[\w.]+' has no attribute|ModuleNotFoundError: No module named '(Components|Screens|Tools|enigma)",
     "level": "amber", "title": u"Plugin prévu pour une autre image",
     "explain": u"Le plugin appelle une fonction qui n'existe pas dans cette version d'OpenATV.", "fix": "update_or_disable"},
    {"id": "xmlparse", "match": r"ParseError|ExpatError", "level": "amber", "title": u"Fichier XML illisible",
     "explain": u"Un fichier XML (source EPG, liste, réglage) est incomplet ou abîmé ; souvent un téléchargement coupé.",
     "fix": "update_or_none"},
]
SCRIPT_NAMES = {"t-flash-pleine": u"Flash pleine", "t-lent": u"Récepteur lent", "t-disque-info": u"Info disques",
                "t-skin-defaut": u"Écran noir (skin)", "t-heure": u"Heure fausse", "t-internet": u"Pas d'Internet",
                "t-opkg-bloque": u"opkg bloqué", "t-epg-vide": u"EPG vide", "softcamfix": u"Softcam Fix"}
FIX_TYPES = ("install", "update", "reinstall", "disable", "restore", "script", "archive", "none")

FIX_LABEL = {"install": u"Installer %s", "update": u"Mettre à jour %s", "reinstall": u"Réinstaller %s",
             "disable": u"Désactiver %s", "restore": u"Réactiver %s", "script": u"Lancer « %s »", "archive": u"Archiver les rapports",
             "none": u"Pas de réparation sûre"}


def strip_ts(line):
    return TS_RE.sub("", line.rstrip("\n"))


def find_logs(limit=20):
    files = []
    for pat in LOG_GLOBS:
        files += glob.glob(pat)
    files = sorted(set(files), key=os.path.getmtime, reverse=True)
    return files[:limit]


def parse_log(path):
    """Last traceback of a crash log: {frames, exception, text, before}."""
    try:
        with open(path, errors="replace") as fh:
            lines = [strip_ts(l) for l in fh]
    except (IOError, OSError):
        return None
    tbs, i = [], 0
    while i < len(lines):
        if lines[i].startswith("Traceback (most recent call last)"):
            start, frames, exc = i, [], ""
            i += 1
            while i < len(lines):
                m = FRAME_RE.match(lines[i])
                if m:
                    frames.append((m.group(1), int(m.group(2)), m.group(3)))
                elif EXC_RE.match(lines[i].strip()) and not lines[i].startswith(" "):
                    exc = lines[i].strip()
                    i += 1
                    break
                elif lines[i] and not lines[i].startswith(" ") and not lines[i].startswith("\t") and frames:
                    break
                i += 1
            tbs.append({"start": start, "frames": frames, "exception": exc, "text": "\n".join(lines[start:i])})
            continue
        i += 1
    whole = "\n".join(lines)
    info = {"path": path, "mtime": os.path.getmtime(path), "whole": whole}
    for key in ("crashdate", "skin", "imageversion"):
        m = re.search(r"^%s=(.*)$" % key, whole, re.M)
        info[key] = m.group(1).strip() if m else ""
    if tbs:
        tb = [t for t in tbs if t["exception"]] or tbs
        tb = tb[-1]
        info.update(tb)
        info["before"] = "\n".join(lines[max(0, tb["start"] - 400):tb["start"]])
    else:  # no python traceback (crash in C++ code): keep the signal line if any
        m = re.search(r"(Segmentation fault|SIGSEGV|SIGABRT|signal \d+|Aborted).*", whole)
        info.update({"frames": [], "exception": m.group(0) if m else u"Plantage sans trace Python", "text": "", "before": whole[-6000:]})
    return info


def installed_plugins():
    out = {}
    for kind in ("Extensions", "SystemPlugins"):
        try:
            for d in os.listdir(os.path.join(PLUGIN_ROOT, kind)):
                if os.path.isdir(os.path.join(PLUGIN_ROOT, kind, d)) and not d.startswith("__"):
                    out[d] = kind
        except OSError:
            pass
    return out


def culprit(info, plugins):
    """(plugin, kind, file, sure): the plugin in the traceback, else the last one named before the crash."""
    for path, line, func in reversed(info.get("frames", [])):
        m = PLUGIN_PATH_RE.search(path)
        if m:
            return m.group(2), m.group(1), "%s:%d" % (os.path.basename(path), line), True
    text = info.get("before", "")
    best, pos = None, -1
    for name, kind in plugins.items():
        if name in ("WacayoubPanel",) or len(name) < 4:
            continue
        for pat in ("/%s/%s" % (kind, name), "[%s]" % name):
            p = text.rfind(pat)
            if p > pos:
                best, pos = (name, kind), p
    if best:
        return best[0], best[1], "", False
    return None, None, "", False


_OWNER = {}


def package_of(plugin, kind):
    """opkg package that installed /usr/lib/enigma2/python/Plugins/<kind>/<plugin> (None if copied by hand)."""
    key = (plugin, kind)
    if key in _OWNER:
        return _OWNER[key]
    target = "%s/%s/%s/" % (PLUGIN_ROOT, kind, plugin)
    found = None
    try:
        names = sorted(os.listdir(OPKG_INFO))
    except OSError:
        names = []
    for fn in names:
        if not fn.endswith(".list"):
            continue
        try:
            with open(os.path.join(OPKG_INFO, fn), errors="replace") as fh:
                if target in fh.read():
                    found = fn[:-5]
                    break
        except (IOError, OSError):
            continue
    _OWNER[key] = found
    return found


def installed_times(path="/var/lib/opkg/status"):
    """{package: Installed-Time} (when opkg last installed or upgraded it)."""
    out, name = {}, None
    try:
        with open(path, errors="replace") as fh:
            for line in fh:
                if line.startswith("Package: "):
                    name = line[9:].strip()
                elif line.startswith("Installed-Time: ") and name:
                    try:
                        out[name] = int(line[16:].strip())
                    except ValueError:
                        pass
    except (IOError, OSError):
        pass
    return out


def changed_before(when, plugins, hours=48):
    """Plugins whose folder changed in the hours before a crash (newest first): likely suspects."""
    out = []
    for name, kind in plugins.items():
        if name == "WacayoubPanel":
            continue
        try:
            m = os.path.getmtime(os.path.join(PLUGIN_ROOT, kind, name))
        except OSError:
            continue
        if when - hours * 3600 <= m <= when:
            out.append((m, name))
    return [(n, time.strftime("%d/%m %H:%M", time.localtime(m))) for m, n in sorted(out, reverse=True)[:3]]


_VERSIONS = {}


def feed_versions():
    """{package: newest version} from the opkg lists (read again only when 'opkg update' changed them)."""
    sig = [F._lists_sig(d) for d in OPKG_LISTS]
    if _VERSIONS.get("sig") != sig:
        _VERSIONS.update(sig=sig, data=_feed_versions())
    return _VERSIONS["data"]


def _feed_versions():
    out = {}
    for d in OPKG_LISTS:
        for fn in glob.glob(os.path.join(d, "*")):
            if not os.path.isfile(fn):
                continue
            try:
                with open(fn, errors="replace") as fh:
                    name = None
                    for line in fh:
                        if line.startswith("Package: "):
                            name = line[9:].strip()
                        elif line.startswith("Version: ") and name:
                            v = line[9:].strip()
                            if name not in out or F.compare_versions(out[name], v) < 0:
                                out[name] = v
            except (IOError, OSError):
                continue
    return out


def load_rules(index):
    rules = []
    for r in (index or {}).get("doctor_rules", []) + BUILTIN_RULES:
        try:
            re.compile(r["match"])
            if r.get("where"):
                re.compile(r["where"])
        except (KeyError, re.error):
            continue
        rules.append(r)
    return rules


def module_package(exc, available):
    m = re.search(r"No module named '([\w.]+)'", exc)
    if not m:
        return None, None
    mod = m.group(1).split(".")[0]
    if mod in ("Components", "Screens", "Tools", "enigma", "Plugins"):
        return mod, None
    for cand in (MODULE_MAP.get(mod), "python3-" + mod.lower(), "python3-" + mod.lower().replace("_", "-")):
        if cand and cand in available:
            return mod, cand
    return mod, ""


def analyse(index=None, own_packages=None):
    """List of findings, most serious first. own_packages: {name: version} from my feed (updates via the panel)."""
    plugins = installed_plugins()
    installed = F.installed_packages()
    available = feed_versions()
    own_packages = own_packages or {}
    rules = load_rules(index)
    times = installed_times()
    groups = {}
    for path in find_logs():
        info = parse_log(path)
        if not info:
            continue
        name, kind, where, sure = culprit(info, plugins)
        exc = info.get("exception", "")
        key = (name or "core", re.sub(r"\d+", "#", exc)[:120])
        g = groups.get(key)
        if g:
            g["logs"].append(path)
            continue
        groups[key] = {"plugin": name, "kind": kind, "where": where, "sure": sure, "exception": exc, "info": info, "logs": [path]}
    findings = []
    for g in groups.values():
        findings.append(_diagnose(g, rules, installed, available, own_packages, times, plugins))
    findings += _quarantined()
    findings += G.findings()
    order = {"red": 0, "amber": 1, "blue": 2, "green": 3}
    findings.sort(key=lambda f: (order.get(f["level"], 4), -f["count"]))
    return findings


def _diagnose(g, rules, installed, available, own, times, plugins):
    name, kind, exc, info = g["plugin"], g["kind"], g["exception"], g["info"]
    pkg = package_of(name, kind) if name else None
    newest = own.get(pkg) or available.get(pkg) if pkg else None
    has_update = bool(pkg and newest and pkg in installed and F.compare_versions(installed[pkg], newest) < 0)
    who = name or u"Enigma2"
    f = {"id": "%s|%s" % (name or "core", exc[:60]), "plugin": name, "kind": kind, "package": pkg, "count": len(g["logs"]),
         "logs": g["logs"], "exception": exc, "where": g["where"], "sure": g["sure"],
         "date": time.strftime("%d/%m %H:%M", time.localtime(info["mtime"])), "level": "amber", "fix": None}
    # 1) missing Python module: install it from the feed
    mod, mpkg = module_package(exc, available)
    if mod and mpkg:
        f.update(level="red", title=u"Module Python manquant : %s" % mod,
                 explain=u"%s a besoin du module « %s ». Il est disponible dans le feed OpenATV : %s." % (who, mod, mpkg))
        f["fix"] = {"type": "install", "packages": [mpkg]}
        return _finish(f)
    rule = None
    for r in rules:
        if re.search(r["match"], exc) and (not r.get("where") or re.search(r["where"], info.get("text", "") + "\n" + exc)):
            rule = r
            break
    if mod and mpkg == "" and not rule:
        f.update(level="amber", title=u"Module Python introuvable : %s" % mod,
                 explain=u"%s demande « %s », absent du feed de cette image : le plugin n'est pas fait pour elle." % (who, mod))
        rule = {"fix": "update_or_disable"}
    if rule and "title" in rule:
        f.update(level=rule.get("level", "amber"), title=rule["title"], explain=rule.get("explain", ""), rule=rule.get("id", ""))
    elif "title" not in f:
        f.update(title=u"Plantage dans %s" % who if name else u"Plantage d'Enigma2",
                 explain=u"%s a planté (erreur dans son code)." % who if name else u"Enigma2 a planté.")
    when = max(os.path.getmtime(x) for x in g["logs"])
    if not (name and g["sure"]) and (not rule or rule.get("id") in ("badcallback", "importname")):
        sus = changed_before(when, plugins)
        if sus:
            f["explain"] += u"\nInstallés ou modifiés juste avant : %s." % ", ".join(u"%s (%s)" % s for s in sus)
    if pkg and times.get(pkg, 0) > when:
        f.update(level="green", title=f["title"] + u" (sans doute corrigé)")
        f["explain"] += u"\n%s a été mis à jour le %s, après ce plantage : la nouvelle version corrige probablement le problème." % (
            who, time.strftime("%d/%m %H:%M", time.localtime(times[pkg])))
        f["fix"] = None
        f["fixed"] = True
        return _finish(f)
    plan = (rule or {}).get("fix")
    if not plan:  # plain bug in a plugin: newer version, else disable only if it keeps crashing
        plan = "update_or_disable" if (name and len(g["logs"]) >= 2) else "update_or_none"
    f["fix"] = _plan(plan, f, pkg, has_update, newest, name, kind)
    if not f["fix"] and name and len(g["logs"]) < 2:
        f["explain"] += u"\nUn seul plantage : rien n'est changé. S'il revient, Fixo proposera de désactiver %s." % who
    return _finish(f)


def _plan(plan, f, pkg, has_update, newest, name, kind):
    """Turn a rule's fix word into a concrete fix; 'update_or_X' prefers a newer version when the feeds have one."""
    if plan.startswith("update_or_"):
        if has_update:
            return {"type": "update", "packages": [pkg], "version": newest}
        plan = plan[len("update_or_"):]
    if plan == "update":
        return {"type": "update", "packages": [pkg], "version": newest} if has_update else None
    if plan == "reinstall":
        return {"type": "reinstall", "packages": [pkg]} if pkg else ({"type": "disable", "plugin": name, "kind": kind} if name else None)
    if plan == "disable":
        if not name or name == "WacayoubPanel":
            return None
        return {"type": "disable", "plugin": name, "kind": kind, "sure": f["sure"]}
    if plan.startswith("script:"):
        return {"type": "script", "item": plan[7:]}
    if plan.startswith("install:"):
        pk = [p for p in plan[8:].split() if PKG_RE.match(p)]
        return {"type": "install", "packages": pk} if pk else None
    return None


def _finish(f):
    fx = f.get("fix")
    if fx and fx.get("type") not in FIX_TYPES:
        f["fix"] = fx = None
    who = f.get("plugin") or "Enigma2"
    if f.get("plugin") and not f.get("sure"):
        f["explain"] += u"\nPlugin suspect (utilisé juste avant le plantage) : %s." % who
    if fx:
        t = fx["type"]
        if t == "update":
            f["fix_label"] = u"Mettre à jour %s → %s" % (f.get("plugin") or fx["packages"][0], F.short_version(fx.get("version", ""), 20))
        elif t in ("install", "reinstall"):
            f["fix_label"] = FIX_LABEL[t] % ", ".join(fx["packages"])
        elif t in ("disable", "restore"):
            f["fix_label"] = FIX_LABEL[t] % fx["plugin"]
        elif t == "script":
            f["fix_label"] = FIX_LABEL[t] % SCRIPT_NAMES.get(fx["item"], fx["item"])
    else:
        f["fix"] = {"type": "archive"}
        if f.get("fixed"):
            f["fix_label"] = u"Archiver ce rapport"
        else:
            f["fix_label"] = u"Pas de réparation sûre : archiver"
    return f


def _quarantined():
    out = []
    try:
        names = sorted(os.listdir(QUARANTINE))
    except OSError:
        return out
    for d in names:
        kind = "SystemPlugins" if os.path.exists(os.path.join(QUARANTINE, d, ".systemplugin")) else "Extensions"
        out.append({"id": "q|" + d, "plugin": d, "kind": kind, "package": None, "count": 0, "logs": [], "exception": "",
                    "where": "", "sure": True, "date": "", "level": "blue", "title": u"%s est désactivé" % d,
                    "explain": u"Mis de côté par Fixo dans %s. VERT le remet à sa place (redémarrage de l'interface)." % QUARANTINE,
                    "fix": {"type": "restore", "plugin": d, "kind": kind}, "fix_label": FIX_LABEL["restore"] % d})
    return out


def sh(s):
    return "'" + str(s).replace("'", "'\\''") + "'"


def fix_commands(f, feed=None):
    """Shell body for a finding's fix; the crash logs are archived once the fix worked."""
    fx = f["fix"]
    t = fx["type"]
    lines = []
    if t == "install":
        lines.append("echo '>>> Installation depuis le feed OpenATV : %s'" % " ".join(fx["packages"]))
        lines.append("opkg install %s || { echo 'ERREUR: installation impossible'; exit 1; }" % " ".join(sh(p) for p in fx["packages"]))
    elif t in ("update", "reinstall"):
        names = fx["packages"]
        if feed and all(p in feed.packages and not feed.packages[p].get("ext") for p in names) and \
                all(feed.packages[p].get("url", "").startswith("https://github.com/") for p in names):
            lines.append(F.install_commands(feed, names, reinstall=(t == "reinstall")).rstrip("\n"))
        else:
            flags = "--force-reinstall " if t == "reinstall" else ""
            lines.append("echo '>>> %s depuis le feed : %s'" % ("Réinstallation" if t == "reinstall" else "Mise à jour", " ".join(names)))
            lines.append("opkg install %s%s || { echo 'ERREUR: opkg'; exit 1; }" % (flags, " ".join(sh(p) for p in names)))
    elif t == "disable":
        src = "%s/%s/%s" % (PLUGIN_ROOT, fx["kind"], fx["plugin"])
        dst = "%s/%s" % (QUARANTINE, fx["plugin"])
        lines.append("mkdir -p %s" % sh(QUARANTINE))
        lines.append("[ -d %s ] || { echo 'Plugin introuvable'; exit 1; }" % sh(src))
        lines.append("rm -rf %s; mv %s %s || exit 1" % (sh(dst), sh(src), sh(dst)))
        if fx["kind"] == "SystemPlugins":
            lines.append("touch %s/.systemplugin" % sh(dst))
        lines.append("echo '>>> %s désactivé (gardé dans %s, réactivable par Fixo)'" % (fx["plugin"], QUARANTINE))
    elif t == "restore":
        src = "%s/%s" % (QUARANTINE, fx["plugin"])
        dst = "%s/%s/%s" % (PLUGIN_ROOT, fx["kind"], fx["plugin"])
        lines.append("[ -e %s ] && { echo 'Un plugin du même nom existe déjà'; exit 1; }" % sh(dst))
        lines.append("rm -f %s/.systemplugin; mv %s %s || exit 1" % (sh(src), sh(src), sh(dst)))
        lines.append("echo '>>> %s réactivé'" % fx["plugin"])
    elif t == "script":
        if not feed:
            return None
        it = [i for i in feed.items if i["id"] == fx["item"] and i.get("type") == "script"]
        if not it:
            return None
        lines.append(F.script_commands(feed, it[0]).rstrip("\n").replace("exit $rc", "[ $rc = 0 ] || exit $rc"))
    if f.get("logs"):
        lines.append("mkdir -p %s && mv -f %s %s/ 2>/dev/null" % (sh(ARCHIVE), " ".join(sh(p) for p in f["logs"]), sh(ARCHIVE)))
        lines.append("echo '>>> %d rapport(s) de plantage archivé(s) dans %s'" % (len(f["logs"]), ARCHIVE))
    lines.append("echo '>>> Terminé'")
    return "\n".join(lines) + "\n"


def needs_restart(f):
    return f["fix"]["type"] in ("install", "update", "reinstall", "disable", "restore")


if __name__ == "__main__":
    idx = None
    try:
        with open(F.CACHE_FILE, encoding="utf-8") as fh:
            idx = json.load(fh)
    except Exception:
        pass
    for x in analyse(idx, dict((k, v.get("version", "")) for k, v in (idx or {}).get("packages", {}).items())):
        print("[%s] %s  (x%d, %s)  plugin=%s pkg=%s sure=%s" % (x["level"], x["title"], x["count"], x["date"], x["plugin"], x["package"], x["sure"]))
        print("    %s" % x["exception"])
        print("    %s" % x["explain"].replace("\n", "\n    "))
        print("    -> %s" % x["fix_label"])
