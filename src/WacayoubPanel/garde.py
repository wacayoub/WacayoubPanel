# -*- coding: utf-8 -*-
"""Garde: watches what a malware or a third-party installer changes, and the Enigma2 freezes.

1. Package sources: every src line of /etc/opkg/*.conf must point to OpenATV or oe-alliance,
   or have been kept by the user. Anything else is reported (opkg would trust that site).
2. System files: startup scripts, cron, passwords, ssh keys, profile... are compared with a reference
   taken the first time (STATE). A change made by a package (opkg) at install time is accepted on its own;
   any other change is reported until the user accepts it.
3. Freezes: garde-gel.sh (started by the panel) writes /home/root/logs/wacayoub-gel-*.log when Enigma2 is stuck
   in a driver (kernel "blocked for more than" report) and restarts the receiver.
No enigma2 imports: python3 garde.py on the box prints the findings.
"""
import glob
import hashlib
import json
import os
import re
import time

STATE = "/home/root/wacayoub-garde.json"
GEL_GLOB = "/home/root/logs/wacayoub-gel-*.log"
GEL_OFF = "/home/root/wacayoub-gel-off"
OPKG_CONF = "/etc/opkg"
TRUSTED = ("https://feeds2.mynonpublic.com/", "http://feeds2.mynonpublic.com/",
           "https://raw.githubusercontent.com/oe-alliance/")
FILES = ("/etc/passwd", "/etc/shadow", "/etc/group", "/etc/profile", "/etc/inittab", "/etc/rc.local", "/etc/crontab",
         "/etc/inetd.conf", "/etc/hosts", "/etc/ld.so.preload", "/etc/dropbear/authorized_keys",
         "/home/root/.ssh/authorized_keys", "/home/root/.profile")
EXTRA = "/home/root/wacayoub-garde-extra.txt"  # more files to watch on this receiver, one path per line
DIRS = ("/etc/init.d", "/etc/rcS.d", "/etc/rc0.d", "/etc/rc3.d", "/etc/rc5.d", "/etc/rc6.d", "/etc/profile.d",
        "/etc/cron.d", "/etc/cron.hourly", "/etc/cron.daily", "/etc/cron.weekly", "/etc/cron.monthly",
        "/var/spool/cron/crontabs")
SKIP = ("/etc/init.d/softcam", "/etc/init.d/cardserver")  # switched by Softcam Setup
NAMES = {"/etc/passwd": u"comptes", "/etc/shadow": u"mots de passe", "/etc/group": u"groupes",
         "/etc/profile": u"démarrage du shell", "/etc/inittab": u"démarrage du système", "/etc/rc.local": u"démarrage du système",
         "/etc/crontab": u"tâches planifiées", "/etc/inetd.conf": u"services réseau (telnet, ftp)", "/etc/hosts": u"noms de sites",
         "/etc/ld.so.preload": u"bibliothèques forcées", "/etc/dropbear/authorized_keys": u"clés SSH",
         "/home/root/.ssh/authorized_keys": u"clés SSH", "/home/root/.profile": u"démarrage du shell"}


def extra():
    """Files listed in EXTRA (for example neutralised copies of an old malware that must not change)."""
    try:
        with open(EXTRA, encoding="utf-8", errors="replace") as fh:
            return tuple(l.strip() for l in fh if l.strip().startswith("/"))
    except (IOError, OSError):
        return ()


def _sig(path):
    try:
        if os.path.islink(path):
            return "->" + os.readlink(path)
        if not os.path.isfile(path):
            return None
        h = hashlib.sha256()
        with open(path, "rb") as fh:
            for chunk in iter(lambda: fh.read(1 << 16), b""):
                h.update(chunk)
        return h.hexdigest()[:32]
    except (IOError, OSError):
        return None


def snapshot():
    out = {}
    for p in FILES + extra():
        sig = _sig(p)
        if sig:
            out[p] = sig
    for d in DIRS:
        try:
            names = os.listdir(d)
        except OSError:
            continue
        for n in names:
            p = os.path.join(d, n)
            if p in SKIP:
                continue
            sig = _sig(p)
            if sig:
                out[p] = sig
    return out


def sources():
    """[(conf file, name, url)] of the opkg package sources that are switched on."""
    out = []
    for conf in sorted(glob.glob(OPKG_CONF + "/*.conf")):
        try:
            with open(conf, encoding="utf-8", errors="replace") as fh:
                lines = fh.read().splitlines()
        except (IOError, OSError):
            continue
        for line in lines:
            p = line.split()
            if len(p) >= 3 and p[0] in ("src", "src/gz"):
                out.append((conf, p[1], p[2]))
    return out


def trusted(url):
    return url.startswith(TRUSTED)


def load():
    try:
        with open(STATE, encoding="utf-8") as fh:
            st = json.load(fh)
        return st if isinstance(st.get("files"), dict) else None
    except (IOError, OSError, ValueError):
        return None


def save(st):
    tmp = STATE + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(st, fh, ensure_ascii=False, indent=0, sort_keys=True)
    os.replace(tmp, STATE)


def owners(paths, info="/var/lib/opkg/info"):
    """{path: package} for the paths that an installed package put there."""
    want, out = set(paths), {}
    for lst in glob.glob(info + "/*.list"):
        try:
            with open(lst, errors="replace") as fh:
                for line in fh:
                    p = line.split("\t")[0].rstrip("\n")
                    if p in want:
                        out[p] = os.path.basename(lst)[:-5]
        except (IOError, OSError):
            pass
    return out


def installed_times(path="/var/lib/opkg/status"):
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


def _mtime(p):
    try:
        return os.lstat(p).st_mtime
    except OSError:
        return 0


def check():
    """(changed files, unknown sources). The first call only records the reference.
    changed file = {"path", "what": added/changed/removed, "package"}; source = (conf, name, url)."""
    st, cur = load(), snapshot()
    if not st:
        try:
            save({"time": int(time.time()), "files": cur, "sources_ok": []})
        except (IOError, OSError):
            pass
        return [], []
    old = st["files"]
    new = [p for p in extra() if p in cur and p not in old]  # just added to the list: start watching from now
    if new:
        accept(new, st, cur)
    changes = [(p, "added") for p in cur if p not in old] + [(p, "changed") for p in cur if p in old and old[p] != cur[p]]
    changes += [(p, "removed") for p in old if p not in cur]
    bad, quiet = [], []
    if changes:
        own, times = owners([c[0] for c in changes]), installed_times()
        for p, what in changes:
            pkg = own.get(p)
            # written by opkg: the package was installed after the reference, and the file not touched afterwards
            if pkg and times.get(pkg, 0) >= st.get("time", 0) - 60 and _mtime(p) <= times[pkg] + 300:
                quiet.append(p)
            elif what == "removed" and p not in FILES + extra():
                quiet.append(p)  # a startup script that left with its package
            else:
                bad.append({"path": p, "what": what, "package": pkg})
    if quiet:
        accept(quiet, st, cur)
    ok = set(st.get("sources_ok", []))
    srcs = [s for s in sources() if not trusted(s[2]) and s[2] not in ok]
    return bad, srcs


def accept(paths, st=None, cur=None):
    """The user (or a package) made these changes: they become the new reference."""
    st = st or load()
    if not st:
        return
    cur = cur or snapshot()
    for p in paths:
        if p in cur:
            st["files"][p] = cur[p]
        else:
            st["files"].pop(p, None)
    try:
        save(st)
    except (IOError, OSError):
        pass


def keep_source(url):
    st = load()
    if st is not None:
        st.setdefault("sources_ok", [])
        if url not in st["sources_ok"]:
            st["sources_ok"].append(url)
        save(st)


def source_off(conf, url):
    """Switch a source off by commenting its line (put '#' back to switch it on again)."""
    with open(conf, encoding="utf-8", errors="replace") as fh:
        lines = fh.read().splitlines()
    out = []
    for line in lines:
        p = line.split()
        out.append("#" + line if len(p) >= 3 and p[0] in ("src", "src/gz") and p[2] == url else line)
    with open(conf, "w", encoding="utf-8") as fh:
        fh.write("\n".join(out) + "\n")


def gel_events(days=30):
    """Freeze reports of the last days, oldest first: [(path, time, driver, rebooted)]."""
    out = []
    now = time.time()
    for p in glob.glob(GEL_GLOB):
        t = _mtime(p)
        if now - t > days * 86400:
            continue
        drv, rebooted = "", False
        try:
            with open(p, errors="replace") as fh:
                text = fh.read()
            rebooted = "reboot=oui" in text
            m = re.search(r"^wchan=(\S+)", text, re.M)
            drv = m.group(1) if m and m.group(1) not in ("0", "") else ""
            if not drv:
                m = re.search(r"\b(\w*(?:demux|dmx|dvb|frontend|tuner)\w*)\+0x", text)
                drv = m.group(1) if m else ""
        except (IOError, OSError):
            pass
        out.append((p, t, drv, rebooted))
    return sorted(out, key=lambda e: e[1])


def _host(url):
    return url.split("//", 1)[-1].split("/", 1)[0]


_ALERTS = {}


def alerts():
    """Home screen lines: [(level, text, action)] (system files checked at most every 30 s)."""
    if _ALERTS and time.time() - _ALERTS["t"] < 30:
        return list(_ALERTS["v"])
    v = _alerts()
    _ALERTS.update(t=time.time(), v=v)
    return list(v)


def _alerts():
    out = []
    try:
        bad, srcs = check()
    except Exception as e:  # never break the home screen
        print("[WacayoubPanel] garde: %s" % e)
        bad, srcs = [], []
    if srcs:
        out.append(("red", u"Source de paquets inconnue : %s  ·  OK : Fixo" % _host(srcs[0][2]), "doctor"))
    if len(bad) == 1:
        out.append(("red", u"Fichier système modifié : %s  ·  OK : Fixo" % bad[0]["path"], "doctor"))
    elif bad:
        out.append(("red", u"%d fichiers système modifiés  ·  OK : Fixo" % len(bad), "doctor"))
    ev = gel_events(7)
    if ev:
        out.append(("amber", u"Récepteur bloqué le %s%s  ·  OK : Fixo" % (time.strftime("%d/%m %H:%M", time.localtime(ev[-1][1])),
                                                                     u", redémarré" if ev[-1][3] else u""), "doctor"))
    return out


def _f(fid, level, title, explain, fix, label, date="", logs=None, show=None):
    return {"id": fid, "plugin": None, "kind": "", "package": None, "count": len(logs or []), "logs": logs or [],
            "exception": "", "where": "", "sure": True, "date": date, "level": level, "title": title,
            "explain": explain, "fix": fix, "fix_label": label, "show": show, "garde": True}


def findings():
    """Fixo rows for the sources, the system files and the freezes."""
    out = []
    try:
        bad, srcs = check()
    except Exception as e:
        print("[WacayoubPanel] garde: %s" % e)
        bad, srcs = [], []
    for conf, name, url in srcs:
        out.append(_f("src|" + url, "red", u"Source de paquets inconnue : %s" % _host(url),
                      u"%s ajoute la source « %s » (%s). opkg peut installer et mettre à jour des paquets depuis ce site, "
                      u"sans contrôle. Typique d'un panel tiers ou d'un malware. VERT : la désactiver (ou la garder si c'est toi)."
                      % (conf, name, url), {"type": "source", "conf": conf, "url": url}, u"Désactiver la source", show=conf))
    more = extra()
    for b in bad:
        p, what = b["path"], b["what"]
        role = NAMES.get(p) or (u"fichier surveillé en plus" if p in more else
                                u"démarrage automatique" if "/rc" in p or "/init.d" in p else
                                u"tâche planifiée" if "cron" in p else u"démarrage du shell")
        title = {"added": u"Nouveau fichier système : %s", "changed": u"Fichier système modifié : %s",
                 "removed": u"Fichier système supprimé : %s"}[what] % p
        why = (u"Aucun paquet ne l'a installé." if not b["package"] else
               u"Il appartient au paquet %s mais a été modifié après son installation." % b["package"])
        warn = (u"Il est dans ta liste à surveiller : il ne doit pas changer. " if p in more else "")
        out.append(_f("sys|" + p, "red", title,
                      u"%s (%s). %s %sSi ce n'est pas toi, ne l'accepte pas : c'est peut-être un malware. "
                      u"VERT : accepter si c'est toi. BLEU : voir le fichier." % (p, role, why, warn),
                      {"type": "accept", "paths": [p]}, u"C'est moi : accepter",
                      date=time.strftime("%d/%m %H:%M", time.localtime(_mtime(p))) if what != "removed" else "", show=p))
    ev = gel_events(30)
    if ev:
        drv = ev[-1][2]
        auto = ev[-1][3]
        out.append(_f("gel", "amber", u"Récepteur bloqué%s" % (u" (pilote du démodulateur)" if re.search("demux|dmx", drv) else u""),
                      u"Enigma2 était figé dans un pilote%s : télécommande et image ne répondaient plus. Garde l'a vu %s. "
                      u"Panne connue du pilote : si ça revient souvent, mets l'image à jour et vérifie le câble d'antenne. "
                      u"VERT : archiver. BLEU : voir le rapport."
                      % ((u" (%s)" % drv) if drv else u"",
                         u"et a redémarré le récepteur tout seul" if auto else u"mais ne l'a pas redémarré (redémarrage automatique coupé ou test)"),
                      {"type": "archive"}, u"Archiver (déjà redémarré)" if auto else u"Archiver",
                      date=time.strftime("%d/%m %H:%M", time.localtime(ev[-1][1])), logs=[e[0] for e in ev], show=ev[-1][0]))
    return out


if __name__ == "__main__":
    for x in findings():
        print("[%s] %s\n    %s\n    -> %s" % (x["level"], x["title"], x["explain"], x["fix_label"]))
    print("sources: %d, reference: %s" % (len(sources()), STATE))
