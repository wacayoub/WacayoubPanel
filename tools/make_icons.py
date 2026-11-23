#!/usr/bin/env python3
"""Draw the panel's UI images (FHD sizes) into src/WacayoubPanel/img/.

Glyphs: Lucide icons (ISC License, https://lucide.dev, Lucide Contributors).
Needs resvg-py + Pillow:  build/venv/Scripts/python tools/make_icons.py
"""
import io
import math
import os

import resvg_py
from PIL import Image, ImageDraw, ImageFilter

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "src", "WacayoubPanel", "img")

# Lucide glyph bodies (inside <svg viewBox="0 0 24 24">), stroke = currentColor
G = {
    "grid": '<rect width="7" height="7" x="3" y="3" rx="1"/><rect width="7" height="7" x="14" y="3" rx="1"/><rect width="7" height="7" x="14" y="14" rx="1"/><rect width="7" height="7" x="3" y="14" rx="1"/>',
    "satellite": '<path d="M18 12a6 6 0 0 0-6-6m-9.176 4.459a8 8 0 0 0 10.717 10.717c.558-.276.623-1.012.183-1.452l-9.448-9.448c-.44-.44-1.176-.375-1.452.183M22 12A10 10 0 0 0 12 2M9 15l4-4"/>',
    "calendar": '<path d="M16 14v2.2l1.6 1M16 2v3m5 2.338V5a2 2 0 0 0-2-2H5a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h2.338M3 9h5.859M8 2v3"/><circle cx="16" cy="16" r="6"/>',
    "headphones": '<path d="M3 14h3a2 2 0 0 1 2 2v3a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-7a9 9 0 0 1 18 0v7a2 2 0 0 1-2 2h-1a2 2 0 0 1-2-2v-3a2 2 0 0 1 2-2h3"/>',
    "wrench": '<path d="M14.7 6.3a1 1 0 0 0 0 1.4l1.6 1.6a1 1 0 0 0 1.4 0l3.106-3.105c.32-.322.863-.22.983.218a6 6 0 0 1-8.259 7.057l-7.91 7.91a1 1 0 0 1-2.999-3l7.91-7.91a6 6 0 0 1 7.057-8.259c.438.12.54.662.219.984z"/>',
    "palette": '<path d="M12 22a1 1 0 0 1 0-20a10 9 0 0 1 10 9a5 5 0 0 1-5 5h-2.25a1.75 1.75 0 0 0-1.4 2.8l.3.4a1.75 1.75 0 0 1-1.4 2.8z"/><circle cx="13.5" cy="6.5" r=".5" fill="currentColor"/><circle cx="17.5" cy="10.5" r=".5" fill="currentColor"/><circle cx="6.5" cy="12.5" r=".5" fill="currentColor"/><circle cx="8.5" cy="7.5" r=".5" fill="currentColor"/>',
    "terminal": '<path d="M12 19h8M4 17l6-6l-6-6"/>',
    "box": '<path d="M11 21.73a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73z"/><path d="M12 22V12M3.29 7L12 12l8.71-5M7.5 4.27l9 5.15"/>',
    "search": '<path d="m21 21l-4.34-4.34"/><circle cx="11" cy="11" r="8"/>',
    "puzzle": '<path d="M15.39 4.39a1 1 0 0 0 1.68-.474a2.5 2.5 0 1 1 3.014 3.015a1 1 0 0 0-.474 1.68l1.683 1.682a2.414 2.414 0 0 1 0 3.414L19.61 15.39a1 1 0 0 1-1.68-.474a2.5 2.5 0 1 0-3.014 3.015a1 1 0 0 1 .474 1.68l-1.683 1.682a2.414 2.414 0 0 1-3.414 0L8.61 19.61a1 1 0 0 0-1.68.474a2.5 2.5 0 1 1-3.014-3.015a1 1 0 0 0 .474-1.68l-1.683-1.682a2.414 2.414 0 0 1 0-3.414L4.39 8.61a1 1 0 0 1 1.68.474a2.5 2.5 0 1 0 3.014-3.015a1 1 0 0 1-.474-1.68l1.683-1.682a2.414 2.414 0 0 1 3.414 0z"/>',
    "cpu": '<path d="M12 20v2m0-20v2m5 16v2m0-20v2M2 12h2m-2 5h2M2 7h2m16 5h2m-2 5h2M20 7h2M7 20v2M7 2v2"/><rect width="16" height="16" x="4" y="4" rx="2"/><rect width="8" height="8" x="8" y="8" rx="1"/>',
    "list": '<path d="M11 5h10m-10 7h10m-10 7h10M4 4h1v5M4 9h2m.5 11H3.4c0-1 2.6-1.925 2.6-3.5a1.5 1.5 0 0 0-2.6-1.02"/>',
    "image": '<rect width="18" height="18" x="3" y="3" rx="2"/><circle cx="9" cy="9" r="2"/><path d="m21 15l-3.086-3.086a2 2 0 0 0-2.828 0L6 21"/>',
    "tv": '<path d="m17 2l-5 5l-5-5"/><rect width="20" height="15" x="2" y="7" rx="2"/>',
    "globe": '<circle cx="12" cy="12" r="10"/><path d="M12 2a14.5 14.5 0 0 0 0 20a14.5 14.5 0 0 0 0-20M2 12h20"/>',
    "moon": '<path d="M18 5h4m-2-2v4m.985 5.486a9 9 0 1 1-9.473-9.472c.405-.022.617.46.402.803a6 6 0 0 0 8.268 8.268c.344-.215.825-.004.803.401"/>',
    "cloudsun": '<path d="M12 2v2m-7.07.93l1.41 1.41M20 12h2m-2.93-7.07l-1.41 1.41m-1.713 6.31a4 4 0 0 0-5.925-4.128M13 22H7a5 5 0 1 1 4.9-6H13a3 3 0 0 1 0 6"/>',
    "arrows": '<path d="M8 3 4 7l4 4"/><path d="M4 7h16"/><path d="m16 21 4-4-4-4"/><path d="M20 17H4"/>',
    "cast": '<path d="M2 8V6a2 2 0 0 1 2-2h16a2 2 0 0 1 2 2v12a2 2 0 0 1-2 2h-6M2 12a9 9 0 0 1 8 8m-8-4a5 5 0 0 1 4 4m-4 0h.01"/>',
    "sliders": '<path d="M10 5H3m9 14H3M14 3v4m2 10v4m5-9h-9m9 7h-5m5-14h-7m-6 5v4m0-2H3"/>',
    "info": '<circle cx="12" cy="12" r="10"/><path d="M12 16v-4m0-4h.01"/>',
    "sparkles": '<path d="M11.017 2.814a1 1 0 0 1 1.966 0l1.051 5.558a2 2 0 0 0 1.594 1.594l5.558 1.051a1 1 0 0 1 0 1.966l-5.558 1.051a2 2 0 0 0-1.594 1.594l-1.051 5.558a1 1 0 0 1-1.966 0l-1.051-5.558a2 2 0 0 0-1.594-1.594l-5.558-1.051a1 1 0 0 1 0-1.966l5.558-1.051a2 2 0 0 0 1.594-1.594zM20 2v4m2-2h-4"/><circle cx="4" cy="20" r="2"/>',
    "badge": '<path d="M3.85 8.62a4 4 0 0 1 4.78-4.77a4 4 0 0 1 6.74 0a4 4 0 0 1 4.78 4.78a4 4 0 0 1 0 6.74a4 4 0 0 1-4.77 4.78a4 4 0 0 1-6.75 0a4 4 0 0 1-4.78-4.77a4 4 0 0 1 0-6.76z"/><path d="m9 12l2 2l4-4"/>',
    "rocket": '<path d="M12 15v5s3.03-.55 4-2c1.08-1.62 0-5 0-5M4.5 16.5c-1.5 1.26-2 5-2 5s3.74-.5 5-2c.71-.84.7-2.13-.09-2.91a2.18 2.18 0 0 0-2.91-.09"/><path d="M9 12a22 22 0 0 1 2-3.95A12.88 12.88 0 0 1 22 2c0 2.72-.78 7.5-6 11a22.4 22.4 0 0 1-4 2z"/><path d="M9 12H4s.55-3.03 2-4c1.62-1.08 5 .05 5 .05"/>',
    "drive": '<path d="M12 2v8m4-4l-4 4l-4-4"/><rect width="20" height="8" x="2" y="14" rx="2"/><path d="M6 18h.01M10 18h.01"/>',
    "key": '<path d="M2.586 17.414A2 2 0 0 0 2 18.828V21a1 1 0 0 0 1 1h3a1 1 0 0 0 1-1v-1a1 1 0 0 1 1-1h1a1 1 0 0 0 1-1v-1a1 1 0 0 1 1-1h.172a2 2 0 0 0 1.414-.586l.814-.814a6.5 6.5 0 1 0-4-4z"/><circle cx="16.5" cy="7.5" r=".5" fill="currentColor"/>',
    "rss": '<path d="M4 11a9 9 0 0 1 9 9M4 4a16 16 0 0 1 16 16"/><circle cx="5" cy="19" r="1"/>',
    "layers": '<path d="M12.83 2.18a2 2 0 0 0-1.66 0L2.6 6.08a1 1 0 0 0 0 1.83l8.58 3.91a2 2 0 0 0 .83.18a2 2 0 0 0 .83-.18l8.58-3.9a1 1 0 0 0 0-1.831zM16 17h6m-3-3v6M2 12a1 1 0 0 0 .58.91l8.6 3.91a2 2 0 0 0 .825.178M2 17a1 1 0 0 0 .58.91l8.6 3.91a2 2 0 0 0 1.65 0l2.116-.962"/>',
    "checkbig": '<path d="M21.801 10A10 10 0 1 1 17 3.335"/><path d="m9 11l3 3L22 4"/>',
    "check": '<path d="M20 6L9 17l-5-5"/>',
    "stethoscope": '<path d="M11 2v2M5 2v2M5 3H4a2 2 0 0 0-2 2v4a6 6 0 0 0 12 0V5a2 2 0 0 0-2-2h-1"/><path d="M8 15a6 6 0 0 0 12 0v-3"/><circle cx="20" cy="10" r="2"/>',
    "thermo": '<path d="M14 4v10.54a4 4 0 1 1-4 0V4a2 2 0 0 1 4 0Z"/>',
    "clock": '<circle cx="12" cy="12" r="10"/><path d="M12 6v6l4 2"/>',
    "chip": '<rect width="20" height="12" x="2" y="6" rx="2"/><path d="M6 10v4m4-4v4m4-4v4m4-4v4"/>',
    "up": '<path d="M12 19V5m-7 7l7-7l7 7"/>',
    "down": '<path d="M12 5v14m7-7l-7 7l-7-7"/>',
    "half": '<path d="M12 3v18"/><circle cx="12" cy="12" r="9"/>',
    "x": '<path d="M18 6L6 18M6 6l12 12"/>',
    "play": '<path d="M6 4l14 8l-14 8z"/>',
}

# tile gradients (top-left -> bottom-right)
TILES = {
    # categories / items
    "iptv": ("satellite", "#2F8CFF", "#22D3EE"),
    "epg": ("calendar", "#7C5CFF", "#C084FC"),
    "audio": ("headphones", "#FF4D8D", "#FF8A5B"),
    "tools": ("wrench", "#10B981", "#34D399"),
    "skins": ("palette", "#F59E0B", "#F97316"),
    "scripts": ("terminal", "#475569", "#64748B"),
    "panel": ("box", "#2563EB", "#7C3AED"),
    "all": ("grid", "#0EA5E9", "#6366F1"),
    "search": ("search", "#22C55E", "#0EA5E9"),
    "launch": ("rocket", "#F43F5E", "#8B5CF6"),
    "img-openatv": ("drive", "#1E40AF", "#0EA5E9"),
    "img-openpli": ("drive", "#9A3412", "#F97316"),
    "img-openvix": ("drive", "#065F46", "#10B981"),
    "img-openbh": ("drive", "#111827", "#6B7280"),
    "img-openspa": ("drive", "#7F1D1D", "#EF4444"),
    "img": ("drive", "#334155", "#64748B"),
    "communaute": ("badge", "#0891B2", "#22C55E"),
    "installed": ("checkbig", "#059669", "#22C55E"),
    "addons": ("puzzle", "#2563EB", "#06B6D4"),
    "system": ("cpu", "#334155", "#1D4ED8"),
    "skins": ("palette", "#F59E0B", "#F97316"),
    "softcam": ("key", "#7C2D12", "#EA580C"),
    "picons": ("image", "#9D174D", "#EC4899"),
    "settings": ("list", "#5B21B6", "#8B5CF6"),
    "panels": ("grid", "#0F766E", "#14B8A6"),
    "multiboot": ("layers", "#1E3A8A", "#6366F1"),
    "feeds": ("rss", "#C2410C", "#FBBF24"),
    "recv": ("tv", "#0369A1", "#22D3EE"),
    "doctor": ("stethoscope", "#0E7490", "#22C55E"),
    "p2p": ("arrows", "#0F766E", "#3B82F6"),
    "i-p2p": ("arrows", "#0F766E", "#3B82F6"),
    "fix": ("wrench", "#B45309", "#FBBF24"),
    "dns": ("globe", "#1D4ED8", "#60A5FA"),
    "deps": ("box", "#B45309", "#F59E0B"),
    "disk": ("drive", "#6D28D9", "#A78BFA"),
    # 'Mon récepteur' rows
    "r-model": ("tv", "#0369A1", "#22D3EE"),
    "r-temp": ("thermo", "#DC2626", "#F97316"),
    "r-cpu": ("cpu", "#1D4ED8", "#06B6D4"),
    "r-ram": ("chip", "#7C3AED", "#A78BFA"),
    "r-flash": ("drive", "#0F766E", "#2DD4BF"),
    "r-disk": ("drive", "#6D28D9", "#A78BFA"),
    "r-net": ("globe", "#1D4ED8", "#60A5FA"),
    "r-up": ("clock", "#059669", "#34D399"),
    "r-tuner": ("satellite", "#2F8CFF", "#22D3EE"),
    "r-cam": ("key", "#7C2D12", "#EA580C"),
    "r-skin": ("palette", "#F59E0B", "#F97316"),
    "r-soft": ("terminal", "#475569", "#64748B"),
    "ext": ("puzzle", "#4C1D95", "#DB2777"),
    "atv-ext": ("puzzle", "#334155", "#0F766E"),
    "atv-sys": ("cpu", "#334155", "#1D4ED8"),
    "atv-skins": ("palette", "#334155", "#B45309"),
    "atv-settings": ("list", "#334155", "#7C3AED"),
    "atv-picons": ("image", "#334155", "#BE185D"),
    # own items
    "i-iptosat": ("satellite", "#1D4ED8", "#06B6D4"),
    "i-iptvbouquetai": ("sparkles", "#4F46E5", "#22D3EE"),
    "i-epgmanager": ("calendar", "#6D28D9", "#A855F7"),
    "i-bop2": ("globe", "#7C3AED", "#EC4899"),
    "i-ipaudio": ("headphones", "#E11D48", "#FB923C"),
    "i-salaatneo": ("moon", "#047857", "#10B981"),
    "i-neoweather": ("cloudsun", "#0284C7", "#38BDF8"),
    "i-neoconnect": ("cast", "#0F766E", "#2DD4BF"),
    "i-metrixneohelper": ("sliders", "#0E7490", "#22D3EE"),
    "i-metrixneo": ("palette", "#0EA5E9", "#2563EB"),
    "i-orbitai": ("palette", "#1E3A8A", "#3B82F6"),
    "i-novaorbit": ("palette", "#6D28D9", "#DB2777"),
    "i-osappletv": ("tv", "#374151", "#9CA3AF"),
    "i-infosysteme": ("info", "#475569", "#94A3B8"),
    "i-panel": ("box", "#2563EB", "#7C3AED"),
    "i-chaines": ("list", "#0EA5E9", "#22C55E"),
    "i-wmultiboot": ("drive", "#0F172A", "#2563EB"),
}

STATES = {"open": ("play", "#8B5CF6"), "ok": ("check", "#22C55E"), "update": ("up", "#F59E0B"), "none": ("down", "#64748B"),
          "partial": ("half", "#F59E0B"), "na": ("x", "#475569"), "script": ("play", "#38BDF8")}


def glyph(name, px, color="#FFFFFF", width=2.0):
    svg = ('<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" color="%s">'
           '<g fill="none" stroke="currentColor" stroke-linecap="round" stroke-linejoin="round" stroke-width="%s">%s</g></svg>'
           % (color, width, G[name]))
    png = resvg_py.svg_to_bytes(svg_string=svg, width=px, height=px)
    return Image.open(io.BytesIO(bytes(png))).convert("RGBA")


def hexrgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def gradient(w, h, c1, c2):
    a, b = hexrgb(c1), hexrgb(c2)
    im = Image.new("RGBA", (w, h))
    px = im.load()
    for y in range(h):
        for x in range(w):
            t = (x / max(1, w - 1) + y / max(1, h - 1)) / 2.0
            px[x, y] = tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3)) + (255,)
    return im


def rounded_mask(w, h, r, ss=4):
    m = Image.new("L", (w * ss, h * ss), 0)
    ImageDraw.Draw(m).rounded_rectangle([0, 0, w * ss - 1, h * ss - 1], r * ss, fill=255)
    return m.resize((w, h), Image.LANCZOS)


def tile(key, size):
    gname, c1, c2 = TILES[key]
    im = gradient(size, size, c1, c2)
    # soft top highlight
    hl = Image.new("RGBA", (size, size), (255, 255, 255, 0))
    d = ImageDraw.Draw(hl)
    d.ellipse([-size * 0.3, -size * 0.9, size * 1.3, size * 0.45], fill=(255, 255, 255, 40))
    im = Image.alpha_composite(im, hl.filter(ImageFilter.GaussianBlur(size / 10)))
    g = glyph(gname, int(size * 0.56), "#FFFFFF", 2.0)
    off = (size - g.width) // 2
    im.alpha_composite(g, (off, off))
    im.putalpha(Image.composite(im.getchannel("A"), Image.new("L", im.size, 0), rounded_mask(size, size, int(size * 0.26))))
    return im


def state_badge(key, size):
    gname, col = STATES[key]
    ss = 4
    im = Image.new("RGBA", (size * ss, size * ss), (0, 0, 0, 0))
    r, g, b = hexrgb(col)
    ImageDraw.Draw(im).ellipse([0, 0, size * ss - 1, size * ss - 1], fill=(r, g, b, 255))
    im = im.resize((size, size), Image.LANCZOS)
    gl = glyph(gname, int(size * 0.62), "#FFFFFF", 3.0)
    o = (size - gl.width) // 2
    im.alpha_composite(gl, (o, o))
    return im


def bar(w, h, c1, c2, radius, alpha=255, accent=None):
    im = gradient(w, h, c1, c2)
    im.putalpha(Image.eval(rounded_mask(w, h, radius), lambda v: v * alpha // 255))
    if accent:
        r, g, b = hexrgb(accent)
        a = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        ImageDraw.Draw(a).rounded_rectangle([6, h * 0.22, 12, h * 0.78], 3, fill=(r, g, b, 255))
        im = Image.alpha_composite(im, a)
    return im


def background_detail(w, h):
    im = gradient(w, h, "#070B14", "#0B1424")
    glow = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(glow)
    d.ellipse([-300, -420, 900, 420], fill=(47, 140, 255, 55))
    d.ellipse([1300, 650, 2300, 1450], fill=(124, 92, 255, 40))
    im = Image.alpha_composite(im, glow.filter(ImageFilter.GaussianBlur(160)))
    card = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(card)
    d.rounded_rectangle([48, 138, 1152, 770], 22, fill=(0, 0, 0, 90), outline=(255, 255, 255, 26), width=1)
    d.rounded_rectangle([1164, 138, 1872, 770], 22, fill=(255, 255, 255, 12), outline=(255, 255, 255, 22), width=1)
    d.rounded_rectangle([48, 776, 1872, 976], 22, fill=(255, 255, 255, 10), outline=(255, 255, 255, 18), width=1)
    im = Image.alpha_composite(im, card)
    return im.convert("RGB")


def background(w, h):
    im = gradient(w, h, "#070B14", "#0B1424")
    glow = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(glow)
    d.ellipse([-300, -420, 900, 420], fill=(47, 140, 255, 60))
    d.ellipse([1300, 650, 2300, 1450], fill=(124, 92, 255, 45))
    glow = glow.filter(ImageFilter.GaussianBlur(160))
    im = Image.alpha_composite(im, glow)
    # panels: categories card + list card (subtle glass)
    card = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(card)
    d.rounded_rectangle([48, 140, 48 + 440, 140 + 660], 22, fill=(255, 255, 255, 14), outline=(255, 255, 255, 22), width=1)
    d.rounded_rectangle([508, 140, 1872, 140 + 660], 22, fill=(255, 255, 255, 9), outline=(255, 255, 255, 18), width=1)
    d.rounded_rectangle([48, 818, 1872, 818 + 150], 22, fill=(255, 255, 255, 10), outline=(255, 255, 255, 18), width=1)
    im = Image.alpha_composite(im, card)
    return im.convert("RGB")


# Home screen (FHD coordinates, plugin.py HOME_* uses the same numbers)
HOME_TILES = [("fix", "Réparer"), ("addons", "Addons"), ("softcam", "Softcam"), ("skins", "Skins"),
              ("launch", "Mes outils"), ("recv", "Mon récepteur"), ("dns", "DNS"), ("img", "Images")]
HOME_ALERT = (897, 78)
HOME_STATUS = (582, 78)
HOME_TILE = (438, 138)
HOME_COLORS = {"red": (239, 68, 68), "amber": (245, 158, 11), "blue": (59, 130, 246), "green": (34, 197, 94), "gray": (100, 116, 139)}


def home_tile_box(i):
    x0, y0 = 48 + (i % 4) * 462, 675 + (i // 4) * 162
    return [x0, y0, x0 + HOME_TILE[0], y0 + HOME_TILE[1]]


def home_background(w=1920, h=1080):
    from PIL import ImageFont
    im = gradient(w, h, "#070B14", "#0B1424")
    glow = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(glow)
    d.ellipse([-300, -420, 900, 420], fill=(47, 140, 255, 60))
    d.ellipse([1300, 650, 2300, 1450], fill=(124, 92, 255, 45))
    im = Image.alpha_composite(im, glow.filter(ImageFilter.GaussianBlur(160)))
    lay = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(lay)
    card = dict(fill=(15, 23, 42, 170), outline=(148, 163, 184, 55), width=1)
    d.rounded_rectangle([48, 150, 1872, 450], 24, **card)
    fr = ImageFont.truetype("C:/Windows/Fonts/segoeui.ttf", 31)
    fk = ImageFont.truetype("C:/Windows/Fonts/segoeui.ttf", 25)
    ft = ImageFont.truetype("C:/Windows/Fonts/segoeui.ttf", 45)
    for i, (key, label) in enumerate(HOME_TILES):
        x0, y0, x1, y1 = home_tile_box(i)
        d.rounded_rectangle([x0, y0, x1, y1], 24, **card)
        icon = tile(key, 96)
        lay.alpha_composite(icon, (x0 + 24, y0 + 21))
        d.text((x0 + 144, (y0 + y1) // 2), label, font=fr, fill=(241, 245, 249, 255), anchor="lm")
    lay.alpha_composite(logo(66), (48, 36))
    d.text((132, 30), "Wacayoub Panel", font=ft, fill=(241, 245, 249, 255))
    x = 60
    for col, lab in (("#EF4444", "Fixo"), ("#22C55E", "Bilan santé"), ("#F59E0B", "Actualiser"), ("#3B82F6", "Mises à jour")):
        lay.alpha_composite(key_dot(col), (x, 1010))
        d.text((x + 38, 1023), lab, font=fk, fill=(226, 232, 240, 255), anchor="lm")
        x += 330
    d.text((1860, 1023), "OK  ouvrir   ·   MENU  rechercher   ·   EXIT  quitter", font=fk, fill=(226, 232, 240, 255), anchor="rm")
    return Image.alpha_composite(im, lay).convert("RGB")


def home_bar(size, col):
    w, h = size
    r, g, b = HOME_COLORS[col]
    im = Image.new("RGBA", (w * 2, h * 2), (0, 0, 0, 0))
    ImageDraw.Draw(im).rounded_rectangle([1, 1, w * 2 - 2, h * 2 - 2], 32, fill=(r, g, b, 60), outline=(r, g, b, 175), width=3)
    return im.resize(size, Image.LANCZOS)


def home_select(size):
    w, h = size
    im = Image.new("RGBA", (w * 2, h * 2), (0, 0, 0, 0))
    ImageDraw.Draw(im).rounded_rectangle([3, 3, w * 2 - 4, h * 2 - 4], 48, outline=(125, 211, 252, 255), width=8)
    return im.resize(size, Image.LANCZOS)


def key_dot(color, size=26):
    ss = 4
    im = Image.new("RGBA", (size * ss, size * ss), (0, 0, 0, 0))
    r, g, b = hexrgb(color)
    ImageDraw.Draw(im).rounded_rectangle([0, 0, size * ss - 1, size * ss - 1], 8 * ss, fill=(r, g, b, 255))
    return im.resize((size, size), Image.LANCZOS)


def ring(pct, size=104, width=10):
    """Circular gauge frame for pct (0..100); colour follows the load."""
    ss = 4
    S = size * ss
    im = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    pad = width * ss // 2 + ss
    box = [pad, pad, S - pad, S - pad]
    d.ellipse(box, outline=(255, 255, 255, 34), width=width * ss)
    if pct >= 85:
        c1, c2 = "#F97316", "#EF4444"
    elif pct >= 60:
        c1, c2 = "#FACC15", "#F59E0B"
    else:
        c1, c2 = "#22D3EE", "#3B82F6"
    if pct > 0:
        a, b = hexrgb(c1), hexrgb(c2)
        steps = max(2, int(pct * 3.6))
        for i in range(steps):
            t = i / float(steps)
            col = tuple(int(a[k] + (b[k] - a[k]) * t) for k in range(3)) + (255,)
            start = -90 + 360.0 * pct / 100.0 * i / steps
            end = -90 + 360.0 * pct / 100.0 * (i + 1) / steps + 0.6
            d.arc(box, start, end, fill=col, width=width * ss)
        # round caps
        r = width * ss / 2.0
        cx = cy = S / 2.0
        rad = (S - 2 * pad) / 2.0 - r + r
        for ang, col in ((-90, a), (-90 + 3.6 * pct, b)):
            x = cx + (rad - r) * math.cos(math.radians(ang))
            y = cy + (rad - r) * math.sin(math.radians(ang))
            d.ellipse([x - r, y - r, x + r, y + r], fill=tuple(col) + (255,))
    return im.resize((size, size), Image.LANCZOS)


def logo(size=64):
    im = tile("panel", size)
    return im


def chaines_images(font):
    """Images of the Wacayoub Chaînes plugin (same style as the panel)."""
    import shutil
    ch = os.path.join(ROOT, "src", "WacayoubChaines", "img")
    os.makedirs(ch, exist_ok=True)
    for fn in ("sel.png", "k-red.png", "k-green.png", "k-yellow.png", "k-blue.png", "k-menu.png"):
        shutil.copy2(os.path.join(OUT, fn), ch)
    tile("i-chaines", 64).save(os.path.join(ch, "logo.png"), optimize=True)
    # compact layout (20 rows per page): own background and thinner selection bars
    im = gradient(1920, 1080, "#070B14", "#0B1424")
    glow = Image.new("RGBA", (1920, 1080), (0, 0, 0, 0))
    d = ImageDraw.Draw(glow)
    d.ellipse([-300, -420, 900, 420], fill=(47, 140, 255, 60))
    d.ellipse([1300, 650, 2300, 1450], fill=(124, 92, 255, 45))
    im = Image.alpha_composite(im, glow.filter(ImageFilter.GaussianBlur(160)))
    card = Image.new("RGBA", (1920, 1080), (0, 0, 0, 0))
    d = ImageDraw.Draw(card)
    d.rounded_rectangle([48, 128, 488, 930], 20, fill=(255, 255, 255, 14), outline=(255, 255, 255, 22), width=1)
    d.rounded_rectangle([508, 128, 1872, 930], 20, fill=(255, 255, 255, 9), outline=(255, 255, 255, 18), width=1)
    im = Image.alpha_composite(im, card).convert("RGB")
    im.save(os.path.join(ch, "bg-ch.jpg"), quality=88, optimize=True)
    bar(1340, 39, "#1E3A8A", "#1D4ED8", 10, 235, accent="#7DD3FC").save(os.path.join(ch, "sel-row.png"), optimize=True)
    bar(416, 39, "#2563EB", "#7C3AED", 10, 255).save(os.path.join(ch, "sel-bq.png"), optimize=True)
    bar(1340, 39, "#92400E", "#B45309", 10, 235, accent="#FBBF24").save(os.path.join(ch, "sel-move.png"), optimize=True)
    for name, key in (("tv", "recv"), ("iptv", "dns"), ("radio", "audio"), ("bouquet", "settings")):
        tile(key, 60).save(os.path.join(ch, "t-%s.png" % name), optimize=True)
    pb = Image.new("RGBA", (220, 132), (0, 0, 0, 0))
    pb.alpha_composite(bar(220, 132, "#0B1B3A", "#1E1B4B", 22, 255))
    pb.alpha_composite(tile("i-chaines", 84), (68, 10))
    ImageDraw.Draw(pb).text((110, 114), u"CHAÎNES", font=font, fill=(226, 232, 240, 255), anchor="mm")
    pb.save(os.path.join(ROOT, "src", "WacayoubChaines", "plugin.png"), optimize=True)


def main():
    os.makedirs(OUT, exist_ok=True)
    for k in TILES:
        tile(k, 60).save(os.path.join(OUT, "t-%s.png" % k), optimize=True)
        tile(k, 160).save(os.path.join(OUT, "B-%s.png" % k), optimize=True)
        if not k.startswith(("i-", "r-")):
            # small category glyph, white and dim versions
            glyph(TILES[k][0], 30, "#FFFFFF", 2.0).save(os.path.join(OUT, "c-%s.png" % k), optimize=True)
    for k in STATES:
        state_badge(k, 26).save(os.path.join(OUT, "s-%s.png" % k), optimize=True)
    # selection tick shown on the tile corner of ticked items
    sel = Image.new("RGBA", (30, 30), (0, 0, 0, 0))
    selbox = Image.new("RGBA", (120, 120), (0, 0, 0, 0))
    ImageDraw.Draw(selbox).rounded_rectangle([0, 0, 119, 119], 30, fill=(37, 99, 235, 255), outline=(255, 255, 255, 255), width=10)
    sel = selbox.resize((30, 30), Image.LANCZOS)
    gl = glyph("check", 20, "#FFFFFF", 3.2)
    sel.alpha_composite(gl, (5, 5))
    sel.save(os.path.join(OUT, "sel.png"), optimize=True)
    bar(1340, 80, "#1E3A8A", "#1D4ED8", 16, 235, accent="#7DD3FC").save(os.path.join(OUT, "sel-item.png"), optimize=True)
    bar(412, 52, "#2563EB", "#7C3AED", 14, 255).save(os.path.join(OUT, "sel-cat.png"), optimize=True)
    background(1920, 1080).save(os.path.join(OUT, "bg.jpg"), quality=88, optimize=True)
    home_background().save(os.path.join(OUT, "bg-home.jpg"), quality=88, optimize=True)
    for col in HOME_COLORS:
        home_bar(HOME_ALERT, col).save(os.path.join(OUT, "ha-%s.png" % col), optimize=True)
        home_bar(HOME_STATUS, col).save(os.path.join(OUT, "hs-%s.png" % col), optimize=True)
    home_select(HOME_TILE).save(os.path.join(OUT, "hsel-tile.png"), optimize=True)
    home_select(HOME_ALERT).save(os.path.join(OUT, "hsel-alert.png"), optimize=True)
    background_detail(1920, 1080).save(os.path.join(OUT, "bg-detail.jpg"), quality=88, optimize=True)
    for name, col in (("red", "#EF4444"), ("green", "#22C55E"), ("yellow", "#F59E0B"), ("blue", "#3B82F6"), ("menu", "#94A3B8")):
        key_dot(col).save(os.path.join(OUT, "k-%s.png" % name), optimize=True)
    glyph("search", 30, "#CBD5E1", 2.2).save(os.path.join(OUT, "k-search.png"), optimize=True)
    logo(64).save(os.path.join(OUT, "logo.png"), optimize=True)
    for p in range(0, 101, 5):
        ring(p).save(os.path.join(OUT, "ring-%03d.png" % p), optimize=True)
    # plugin browser icon (220x132) in the same style
    pb = Image.new("RGBA", (220, 132), (0, 0, 0, 0))
    pb.alpha_composite(bar(220, 132, "#0B1B3A", "#1E1B4B", 22, 255))
    pb.alpha_composite(tile("panel", 84), (68, 10))
    from PIL import ImageFont
    try:
        f = ImageFont.truetype("C:/Windows/Fonts/segoeuib.ttf", 22)
    except Exception:
        f = ImageFont.load_default()
    ImageDraw.Draw(pb).text((110, 114), "WACAYOUB", font=f, fill=(226, 232, 240, 255), anchor="mm")
    pb.save(os.path.join(ROOT, "src", "WacayoubPanel", "plugin.png"), optimize=True)
    chaines_images(f)
    total = sum(os.path.getsize(os.path.join(OUT, f)) for f in os.listdir(OUT))
    print("images:", len(os.listdir(OUT)), "total KB:", total // 1024)


if __name__ == "__main__":
    main()
