# -*- coding: utf-8 -*-
"""CPU / RAM / storage readings for the gauges (no enigma2 imports, testable on a PC)."""
import os

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
    return None


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
