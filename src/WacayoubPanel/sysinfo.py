# -*- coding: utf-8 -*-
"""CPU / RAM / storage readings for the gauges (no enigma2 imports, testable on a PC)."""
import os
import re
import time

_prev = [None]


def cpu_percent():
    """Busy % since the previous call (first call: since boot)."""
    try:
        with open("/proc/stat") as fh:
            parts = fh.readline().split()[1:]
        vals = [int(x) for x in parts]
    except (IOError, OSError, ValueError):
        return 0
    idle = vals[3] + (vals[4] if len(vals) > 4 else 0)
    total = sum(vals)
    prev = _prev[0]
    _prev[0] = (idle, total)
    if not prev:
        return int(round(100.0 * (total - idle) / total)) if total else 0
    d_total, d_idle = total - prev[1], idle - prev[0]
    if d_total <= 0:
        return 0
    return max(0, min(100, int(round(100.0 * (d_total - d_idle) / d_total))))


def cpu_temp():
    for path, div in (("/proc/stb/sensors/temp0/value", 1), ("/proc/stb/fp/temp_sensor", 1),
                      ("/sys/devices/virtual/thermal/thermal_zone0/temp", 1000),
                      ("/sys/class/thermal/thermal_zone0/temp", 1000)):
        try:
            with open(path) as fh:
                v = int(fh.read().strip().split()[0]) // div
            if 0 < v < 150:
                return v
        except (IOError, OSError, ValueError, IndexError):
            continue
    try:  # HiSilicon boxes (Octagon, Zgemma H7...): "Tsensor: temperature = 67 degree"
        with open("/proc/hisi/msp/pm_cpu") as fh:
            m = re.search(r"temperature\s*=\s*(\d+)", fh.read())
        if m and 0 < int(m.group(1)) < 150:
            return int(m.group(1))
    except (IOError, OSError):
        pass
    return None


def temp_step(t):
    """Temperature -> ring percentage, so the colour means: blue < 70°C, yellow 70-84°C, red >= 85°C."""
    if not t:
        return 0
    if t < 70:
        return int(t * 55 / 70)
    if t < 85:
        return 60 + int((t - 70) * 24 / 15)
    return min(100, 85 + (t - 85))


def _read(path, default=""):
    try:
        with open(path) as fh:
            return fh.read().strip()
    except (IOError, OSError):
        return default


def uptime_text():
    try:
        sec = int(float(_read("/proc/uptime", "0").split()[0]))
    except (ValueError, IndexError):
        return "?"
    d, h, m = sec // 86400, sec % 86400 // 3600, sec % 3600 // 60
    return ("%d j %d h %02d min" % (d, h, m)) if d else ("%d h %02d min" % (h, m))


def image_version():
    info = {}
    for line in _read("/etc/image-version").splitlines():
        if "=" in line:
            k, v = line.split("=", 1)
            info[k.strip()] = v.strip()
    distro = info.get("distro", "") or info.get("creator", "")
    ver = info.get("imageversion", "") or info.get("version", "")
    build = info.get("imagebuild", "")
    return ("%s %s%s" % (distro, ver, (" (build %s)" % build) if build else "")).strip() or "?"


def cpu_text():
    cores, model = 0, ""
    for line in _read("/proc/cpuinfo").splitlines():
        if line.lower().startswith("processor"):
            cores += 1
        k = line.split(":", 1)[0].strip().lower()
        if k in ("model name", "hardware", "cpu model") and ":" in line and not model:
            model = line.split(":", 1)[1].strip()
    mhz = ""
    f = _read("/sys/devices/system/cpu/cpu0/cpufreq/scaling_cur_freq")
    m = re.search(r"freq\s*=\s*(\d+)", _read("/proc/hisi/msp/pm_cpu"))
    if f.isdigit():
        mhz = "%d MHz" % (int(f) // 1000)
    elif m:
        mhz = "%d MHz" % (int(m.group(1)) // 1000)
    load = " ".join(_read("/proc/loadavg", "? ? ?").split()[:3])
    parts = [p for p in ("%d cœurs" % cores if cores else "", mhz, model[:28]) if p]
    return u"  ·  ".join(parts), u"charge %s" % load


def network():
    """[(iface, ip)] of the interfaces that are up (SIOCGIFADDR, Linux only)."""
    out = []
    try:
        import socket
        import fcntl
        import struct
        for iface in sorted(os.listdir("/sys/class/net")):
            if iface == "lo" or _read("/sys/class/net/%s/operstate" % iface) not in ("up", "unknown"):
                continue
            sk = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            try:
                raw = fcntl.ioctl(sk.fileno(), 0x8915, struct.pack("256s", iface[:15].encode()))  # SIOCGIFADDR
                out.append((iface, socket.inet_ntoa(raw[20:24])))
            except (IOError, OSError):
                pass
            finally:
                sk.close()
    except Exception:
        pass
    return out


def gateway():
    for line in _read("/proc/net/route").splitlines()[1:]:
        p = line.split()
        if len(p) > 2 and p[1] == "00000000":
            try:
                g = int(p[2], 16)
                return "%d.%d.%d.%d" % (g & 255, g >> 8 & 255, g >> 16 & 255, g >> 24 & 255)
            except ValueError:
                pass
    return ""


def dns_servers():
    return [l.split()[1] for l in _read("/etc/resolv.conf").splitlines()
            if l.startswith("nameserver") and len(l.split()) > 1]


def tuners():
    out, cur = [], None
    for line in _read("/proc/bus/nim_sockets").splitlines():
        line = line.strip()
        if line.startswith("NIM Socket"):
            cur = {"slot": chr(65 + len(out))}
            out.append(cur)
        elif cur is not None and ":" in line:
            k, v = line.split(":", 1)
            if k.strip() in ("Type", "Name"):
                cur[k.strip()] = v.strip()
    return ["%s: %s %s" % (t["slot"], t.get("Type", ""), t.get("Name", "")) for t in out if t.get("Name")]


def softcam():
    try:
        link = os.path.realpath("/etc/init.d/softcam")
    except OSError:
        return "?"
    name = os.path.basename(link)
    name = name[len("softcam."):] if name.startswith("softcam.") else ""
    if not name or name == "None":
        return "Aucun"
    running = False
    for pid in os.listdir("/proc"):
        if pid.isdigit() and _read("/proc/%s/comm" % pid).lower().startswith(name.lower()[:15]):
            running = True
            break
    return "%s  (%s)" % (name, "actif" if running else "arrêté")


def setting(key):
    for line in _read("/etc/enigma2/settings").splitlines():
        if line.startswith(key + "="):
            return line.split("=", 1)[1]
    return ""


def disks():
    out = []
    seen = set()
    for line in _read("/proc/mounts").splitlines():
        p = line.split()
        if len(p) < 3 or not p[1].startswith("/media/") or p[0] in seen or p[2] in ("tmpfs", "autofs"):
            continue
        seen.add(p[0])
        pct, used, total = storage(p[1])
        if total:
            out.append((p[1], pct, total - used, total, p[2]))
    return out


def receiver_info(model_name=""):
    """Rows for 'Mon récepteur': (id, title, value, detail)."""
    import platform
    t = cpu_temp()
    rp, rused, rtotal = ram()
    fp, fused, ftotal = storage("/")
    cpu, load = cpu_text()
    rows = [
        ("model", u"Récepteur", model_name or _read("/etc/hostname", "?"), image_version()),
        ("temp", u"Température", ("%d °C" % t) if t else u"pas de capteur",
         (u"Normale" if t < 70 else u"Chaude : aérez le récepteur" if t < 85 else u"Trop chaude ! Vérifiez la ventilation") if t else ""),
        ("cpu", u"Processeur", cpu or "?", load),
        ("ram", u"Mémoire RAM", "%d / %d Mo  (%d%%)" % (rused, rtotal, rp), u"libre : %d Mo" % max(0, rtotal - rused)),
        ("flash", u"Système (/)", "%s / %s  (%d%%)" % (human(fused), human(ftotal), fp), u"libre : %s" % human(max(0, ftotal - fused))),
    ]
    for mnt, pct, free, total, fs in disks():
        if (total, total - free) == (ftotal, fused):  # system runs from this disk (multiboot): shown once
            continue
        rows.append(("disk" + mnt, u"Disque %s" % mnt, u"%s libres / %s  (%d%%)" % (human(free), human(total), pct), fs))
    net = network()
    rows.append(("net", u"Réseau", u"  ·  ".join("%s %s" % (i, ip) for i, ip in net) or u"non connecté",
                 u"passerelle %s" % (gateway() or "?")))
    rows.append(("dns", u"DNS", u"  ·  ".join(dns_servers()[:3]) or "?", u"Catégorie DNS pour changer"))
    rows.append(("up", u"Allumé depuis", uptime_text(), time.strftime(u"heure : %d/%m/%Y %H:%M")))
    for i, tn in enumerate(tuners()):
        rows.append(("tuner%d" % i, u"Tuner %s" % tn[0], tn[3:], ""))
    rows.append(("cam", u"Softcam", softcam(), u"Menu > Configuration > Softcam"))
    skin = setting("config.skin.primary_skin").split("/")[0]
    rows.append(("skin", u"Skin", skin or u"par défaut", ""))
    rows.append(("soft", u"Système", "Python %s  ·  noyau %s" % (platform.python_version(), platform.release()),
                 ""))
    return rows


def ram():
    """(percent used, used MB, total MB)."""
    info = {}
    try:
        with open("/proc/meminfo") as fh:
            for line in fh:
                k, v = line.split(":", 1)
                info[k] = int(v.split()[0])
    except (IOError, OSError, ValueError):
        return 0, 0, 0
    total = info.get("MemTotal", 0)
    avail = info.get("MemAvailable", info.get("MemFree", 0) + info.get("Cached", 0))
    used = max(0, total - avail)
    pct = int(round(100.0 * used / total)) if total else 0
    return pct, used // 1024, total // 1024


def storage(path="/"):
    """(percent used, used bytes, total bytes)."""
    try:
        st = os.statvfs(path)
    except OSError:
        return 0, 0, 0
    total = st.f_blocks * st.f_frsize
    free = st.f_bavail * st.f_frsize
    used = max(0, total - st.f_bfree * st.f_frsize)
    pct = int(round(100.0 * used / (used + free))) if (used + free) else 0
    return pct, used, total


def ring_step(pct):
    """Nearest 5% frame: ring-000.png .. ring-100.png."""
    return "ring-%03d.png" % (max(0, min(100, int(round(pct / 5.0)) * 5)))


def human(n):
    n = float(n or 0)
    for unit in ("o", "Ko", "Mo", "Go", "To"):
        if n < 1024 or unit == "To":
            return ("%.0f %s" if unit in ("o", "Ko", "Mo") else "%.1f %s") % (n, unit)
        n /= 1024.0
