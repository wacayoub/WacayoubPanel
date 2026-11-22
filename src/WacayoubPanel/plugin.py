# -*- coding: utf-8 -*-
# Wacayoub Panel - installe, met à jour et supprime mes plugins, skins et scripts
# + les paquets du feed OpenATV. Icônes : Lucide (ISC License, lucide.dev).
import json
import os
import time

from enigma import eListboxPythonMultiContent, eTimer, gFont, getDesktop, RT_HALIGN_LEFT, RT_HALIGN_RIGHT, RT_VALIGN_CENTER
from Components.ActionMap import ActionMap
from Components.Console import Console as AsyncConsole
from Components.Label import Label
from Components.MenuList import MenuList
from Components.MultiContent import MultiContentEntryPixmapAlphaBlend, MultiContentEntryText
from Components.Pixmap import Pixmap
from Plugins.Plugin import PluginDescriptor
from Screens.ChoiceBox import ChoiceBox
from Screens.Console import Console
from Screens.MessageBox import MessageBox
from Screens.Screen import Screen
from Screens.Standby import TryQuitMainloop
from Screens.VirtualKeyBoard import VirtualKeyBoard
from Tools.LoadPixmap import LoadPixmap

import sys

try:
    from enigma import BT_SCALE, BT_KEEP_ASPECT_RATIO
    PIX_FLAGS = BT_SCALE | BT_KEEP_ASPECT_RATIO  # icons are drawn for 1920 px: scale them on HD skins
except ImportError:
    PIX_FLAGS = 0

from . import feed as F
from . import images as IM
from .details import WacayoubDetails
from . import sysinfo as S

VERSION = "1.5.0"
PANEL_PKG = "enigma2-plugin-extensions-wacayoubpanel"
PLUGIN_DIR = os.path.dirname(os.path.abspath(__file__))
IMG = os.path.join(PLUGIN_DIR, "img")

_W = getDesktop(0).size().width() or 1920
SC = _W / 1920.0


def s(v):
    return int(round(v * SC))


C_TEXT = 0xF1F5F9
C_DIM = 0x8C9AB0
C_STATE = {F.ST_NONE: 0x8C9AB0, F.ST_OK: 0x4ADE80, F.ST_UPDATE: 0xFBBF24, F.ST_PARTIAL: 0xFBBF24, F.ST_NA: 0x64748B}
STATE_IMG = {F.ST_NONE: "none", F.ST_OK: "ok", F.ST_UPDATE: "update", F.ST_PARTIAL: "partial", F.ST_NA: "na"}
TYPE_LABEL = {"plugin": "Plugin", "skin": "Skin", "script": "Script", "panel": "Panel", "opkg": "OpenATV"}
SEARCH = "search"
LAUNCH = "launch"
# my plugin folders -> icon id (Mes outils)
LAUNCH_MAP = {
    "SatIPTVBridge": "iptosat", "IPTVBouquetAI": "iptvbouquetai", "EPGManager": "epgmanager", "BOP2": "bop2",
    "IPAudioPro": "ipaudio", "IPAudioSmartAI": "ipaudio", "SalaatNEO": "salaatneo", "NeoWeather": "neoweather",
    "NeoConnect": "neoconnect", "MetrixNEOHelper": "metrixneohelper", "MetrixNeoAI": "metrixneohelper",
    "MetrixNEOBoot": "metrixneohelper", "OSAppleTV": "osappletv", "OrbitAIColours": "orbitai", "NovaOrbit": "novaorbit",
}

_PIX = {}


def pix(name):
    """Cached PNG from img/ (None if missing, the row is drawn without it)."""
    if name not in _PIX:
        path = os.path.join(IMG, name)
        _PIX[name] = LoadPixmap(path, cached=True) if os.path.exists(path) else None
    return _PIX[name]


def item_tile(it):
    if it.get("type") == "launch":
        return pix("t-i-%s.png" % it.get("tile")) or pix("t-launch.png")
    if it.get("type") == "image":
        return pix("t-%s.png" % it.get("category")) or pix("t-img.png")
    if it.get("type") == "opkg":
        return pix("t-%s.png" % it.get("category", "atv-ext")) or pix("t-atv-ext.png")
    return pix("t-i-%s.png" % it.get("id")) or pix("t-%s.png" % it.get("category", "all"))


class _List(MenuList):
    def __init__(self, item_h, fonts):
        MenuList.__init__(self, [], False, eListboxPythonMultiContent)
        for i, (name, size) in enumerate(fonts):
            self.l.setFont(i, gFont(name, s(size)))
        self.l.setItemHeight(s(item_h))


def _skin():
    d = {"W": s(1920), "H": s(1080), "img": IMG}
    for k, v in {
        "lx": 48, "ly": 38, "lw": 64, "tx": 132, "ty": 30, "tw": 900, "th": 54, "tf": 44,
        "stx": 132, "sty": 86, "stw": 1000, "sth": 34, "stf": 24,
        "subx": 1020, "subw": 852, "subf": 23,
        "cx": 62, "cy": 156, "cw": 412, "ch": 624,
        "ix": 520, "iy": 150, "iw": 1340, "ih": 640,
        "dx": 72, "dy": 832, "dw": 1240, "dh": 124, "df": 25,
        "r1": 1342, "r2": 1520, "r3": 1698, "ry": 828, "rs": 104,
        "pw": 104, "py": 864, "pf": 26, "ny": 936, "nw": 170, "nh": 28, "nf": 19,
        "fy": 996, "fd": 26, "fty": 988, "fth": 42, "ff": 25,
        "k1": 62, "k2": 392, "k3": 742, "k4": 1062, "k5": 1452,
    }.items():
        d[k] = s(v)
    d["n1"], d["n2"], d["n3"] = d["r1"] - s(33), d["r2"] - s(33), d["r3"] - s(33)
    for i in range(1, 6):
        d["l%d" % i] = d["k%d" % i] + s(38)
    d["kw"] = s(300)
    return """
    <screen name="WacayoubPanel" position="0,0" size="%(W)d,%(H)d" flags="wfNoBorder" backgroundColor="#00070B14" title="Wacayoub Panel">
      <ePixmap position="0,0" size="%(W)d,%(H)d" pixmap="%(img)s/bg.jpg" scale="1" zPosition="-2" />
      <ePixmap position="%(lx)d,%(ly)d" size="%(lw)d,%(lw)d" pixmap="%(img)s/logo.png" alphatest="blend" scale="1" />
      <widget name="title" position="%(tx)d,%(ty)d" size="%(tw)d,%(th)d" font="Regular;%(tf)d" foregroundColor="#00F1F5F9" backgroundColor="#00070B14" transparent="1" valign="center" />
      <widget name="status" position="%(stx)d,%(sty)d" size="%(stw)d,%(sth)d" font="Regular;%(stf)d" foregroundColor="#007DD3FC" backgroundColor="#00070B14" transparent="1" valign="center" />
      <widget name="sub" position="%(subx)d,%(ty)d" size="%(subw)d,%(th)d" font="Regular;%(subf)d" foregroundColor="#008C9AB0" backgroundColor="#00070B14" transparent="1" halign="right" valign="center" />
      <widget name="cats" position="%(cx)d,%(cy)d" size="%(cw)d,%(ch)d" backgroundColor="#00070B14" transparent="1" foregroundColor="#00F1F5F9" foregroundColorSelected="#00FFFFFF" selectionPixmap="%(img)s/sel-cat.png" scrollbarMode="showNever" enableWrapAround="1" />
      <widget name="items" position="%(ix)d,%(iy)d" size="%(iw)d,%(ih)d" backgroundColor="#00070B14" transparent="1" foregroundColor="#00F1F5F9" foregroundColorSelected="#00FFFFFF" selectionPixmap="%(img)s/sel-item.png" scrollbarMode="showOnDemand" scrollbarWidth="4" scrollbarForegroundColor="#003B82F6" enableWrapAround="1" />
      <widget name="desc" position="%(dx)d,%(dy)d" size="%(dw)d,%(dh)d" font="Regular;%(df)d" foregroundColor="#00CBD5E1" backgroundColor="#00070B14" transparent="1" />
      <widget name="ring_cpu" position="%(r1)d,%(ry)d" size="%(rs)d,%(rs)d" alphatest="blend" scale="1" />
      <widget name="ring_ram" position="%(r2)d,%(ry)d" size="%(rs)d,%(rs)d" alphatest="blend" scale="1" />
      <widget name="ring_disk" position="%(r3)d,%(ry)d" size="%(rs)d,%(rs)d" alphatest="blend" scale="1" />
      <widget name="pct_cpu" position="%(r1)d,%(py)d" size="%(pw)d,%(sth)d" font="Regular;%(pf)d" foregroundColor="#00FFFFFF" backgroundColor="#00070B14" transparent="1" halign="center" valign="center" zPosition="2" />
      <widget name="pct_ram" position="%(r2)d,%(py)d" size="%(pw)d,%(sth)d" font="Regular;%(pf)d" foregroundColor="#00FFFFFF" backgroundColor="#00070B14" transparent="1" halign="center" valign="center" zPosition="2" />
      <widget name="pct_disk" position="%(r3)d,%(py)d" size="%(pw)d,%(sth)d" font="Regular;%(pf)d" foregroundColor="#00FFFFFF" backgroundColor="#00070B14" transparent="1" halign="center" valign="center" zPosition="2" />
      <widget name="lab_cpu" position="%(n1)d,%(ny)d" size="%(nw)d,%(nh)d" font="Regular;%(nf)d" foregroundColor="#008C9AB0" backgroundColor="#00070B14" transparent="1" halign="center" />
      <widget name="lab_ram" position="%(n2)d,%(ny)d" size="%(nw)d,%(nh)d" font="Regular;%(nf)d" foregroundColor="#008C9AB0" backgroundColor="#00070B14" transparent="1" halign="center" />
      <widget name="lab_disk" position="%(n3)d,%(ny)d" size="%(nw)d,%(nh)d" font="Regular;%(nf)d" foregroundColor="#008C9AB0" backgroundColor="#00070B14" transparent="1" halign="center" />
      <ePixmap position="%(k1)d,%(fy)d" size="%(fd)d,%(fd)d" pixmap="%(img)s/k-red.png" alphatest="blend" scale="1" />
      <ePixmap position="%(k2)d,%(fy)d" size="%(fd)d,%(fd)d" pixmap="%(img)s/k-green.png" alphatest="blend" scale="1" />
      <ePixmap position="%(k3)d,%(fy)d" size="%(fd)d,%(fd)d" pixmap="%(img)s/k-yellow.png" alphatest="blend" scale="1" />
      <ePixmap position="%(k4)d,%(fy)d" size="%(fd)d,%(fd)d" pixmap="%(img)s/k-blue.png" alphatest="blend" scale="1" />
      <ePixmap position="%(k5)d,%(fy)d" size="%(fd)d,%(fd)d" pixmap="%(img)s/k-search.png" alphatest="blend" scale="1" />
      <widget name="key_red" position="%(l1)d,%(fty)d" size="%(kw)d,%(fth)d" font="Regular;%(ff)d" foregroundColor="#00E2E8F0" backgroundColor="#00070B14" transparent="1" valign="center" />
      <widget name="key_green" position="%(l2)d,%(fty)d" size="%(kw)d,%(fth)d" font="Regular;%(ff)d" foregroundColor="#00E2E8F0" backgroundColor="#00070B14" transparent="1" valign="center" />
      <widget name="key_yellow" position="%(l3)d,%(fty)d" size="%(kw)d,%(fth)d" font="Regular;%(ff)d" foregroundColor="#00E2E8F0" backgroundColor="#00070B14" transparent="1" valign="center" />
      <widget name="key_blue" position="%(l4)d,%(fty)d" size="%(kw)d,%(fth)d" font="Regular;%(ff)d" foregroundColor="#00E2E8F0" backgroundColor="#00070B14" transparent="1" valign="center" />
      <widget name="key_menu" position="%(l5)d,%(fty)d" size="%(kw)d,%(fth)d" font="Regular;%(ff)d" foregroundColor="#00E2E8F0" backgroundColor="#00070B14" transparent="1" valign="center" />
    </screen>""" % d


class WacayoubPanel(Screen):
    skin = _skin()

    def __init__(self, session):
        Screen.__init__(self, session)
        self.setTitle("Wacayoub Panel")
        self.feed = None
        self.atv = None
        self.installed = {}
        self.archs = F.supported_archs()
        self.focus_items = False
        self.cat_ids = []
        self.query = ""
        self.closed = False
        self.opkg_busy = False
        self.launch_items = []
        self.image_groups = []
        self.images_busy = False
        self.model, self.model_name = IM.box_model()
        self.img_console = AsyncConsole()
        self.async_console = AsyncConsole()
        self.atv_console = AsyncConsole()
        self.stat_timer = eTimer()
        self.stat_timer.callback.append(self._tick)

        self["title"] = Label("Wacayoub Panel")
        self["status"] = Label("")
        self["sub"] = Label("")
        self["cats"] = _List(52, [("Regular", 26), ("Regular", 22)])
        self["items"] = _List(80, [("Regular", 30), ("Regular", 22)])
        self["desc"] = Label("")
        for k in ("cpu", "ram", "disk"):
            self["ring_" + k] = Pixmap()
            self["pct_" + k] = Label("")
            self["lab_" + k] = Label("")
        self["key_red"] = Label("Supprimer")
        self["key_green"] = Label("Installer / MAJ")
        self["key_yellow"] = Label("Actualiser")
        self["key_blue"] = Label("Tout mettre à jour")
        self["key_menu"] = Label("MENU  Rechercher")

        self["actions"] = ActionMap(["OkCancelActions", "ColorActions", "DirectionActions", "MenuActions"], {
            "ok": self.keyOk,
            "cancel": self.keyExit,
            "red": self.keyRemove,
            "green": self.keyInstall,
            "yellow": self.refreshFeed,
            "blue": self.keyUpdateAll,
            "menu": self.keySearch,
            "left": self.keyLeft,
            "right": self.keyRight,
            "up": self.keyUp,
            "down": self.keyDown,
        }, -1)
        self.onLayoutFinish.append(self._start)
        self.onClose.append(self._on_close)

    # ------------------------------------------------------------ start / data
    def _start(self):
        self["cats"].selectionEnabled(True)
        self["items"].selectionEnabled(False)
        S.cpu_percent()
        self._tick()
        self.stat_timer.start(2000, False)
        self._load_cache()
        self._load_atv()
        self._build_launch()
        self._refresh_all()
        self.refreshFeed(auto=True)
        self._fetch_images()

    def _on_close(self):
        self.closed = True
        self.stat_timer.stop()

    def _load_cache(self):
        try:
            self.feed = F.Feed.load(F.CACHE_FILE)
        except Exception:
            self.feed = None

    def _load_atv(self):
        try:
            self.atv = F.AtvCatalog(archs=self.archs)
        except Exception as e:
            self.atv = None
            print("[WacayoubPanel] OpenATV lists: %s" % e)
        if self.feed:
            self.feed = F.Feed(self.feed.data)  # fresh copy, OpenATV part attached in _refresh_all

    def refreshFeed(self, auto=False):
        """JAUNE: my feed + 'opkg update'. On open: opkg update only if the lists are over a day old."""
        self["status"].setText("Lecture du feed en ligne…")
        stale = not self.atv or not self.atv.lists_time or time.time() - self.atv.lists_time > 86400
        if (not auto or stale) and not self.opkg_busy:
            self.opkg_busy = True
            self.atv_console.ePopen("opkg update", self._opkg_done)
        tmp = "/tmp/wacayoubpanel-index.json"
        self.async_console.ePopen(F.index_fetch_command(tmp), self._feed_done, tmp)

    def _opkg_done(self, data, retval, extra=None):
        self.opkg_busy = False
        if self.closed:
            return
        self._load_atv()
        self._refresh_all()
        if retval != 0:
            self["status"].setText("Listes OpenATV : mise à jour impossible, listes en cache.")

    def _feed_done(self, data, retval, tmp):
        if self.closed:
            return
        try:
            if retval != 0:
                raise IOError("wget %s" % retval)
            fresh = F.Feed.load(tmp)
            if not os.path.isdir(F.CACHE_DIR):
                os.makedirs(F.CACHE_DIR)
            with open(F.CACHE_FILE, "w", encoding="utf-8") as fh:
                json.dump(fresh.data, fh, ensure_ascii=False)
            self.feed = fresh
            self["status"].setText("Mes plugins, skins et scripts  ·  paquets OpenATV")
        except Exception as e:
            if self.feed:
                self["status"].setText("Hors ligne : liste en cache (%s)" % (self.feed.updated or "?"))
            else:
                self["status"].setText("Feed inaccessible (%s). Vérifiez Internet puis JAUNE." % e)
        try:
            os.remove(tmp)
        except OSError:
            pass
        self._refresh_all()

    # ------------------------------------------------------------ Mes outils / Images
    def _build_launch(self):
        items = []
        try:
            from Components.PluginComponent import plugins
            for p in plugins.getPlugins(PluginDescriptor.WHERE_PLUGINMENU):
                d = os.path.basename(os.path.normpath(p.path or ""))
                if d in LAUNCH_MAP:
                    items.append({"id": "run:%s:%s" % (d, p.name), "type": LAUNCH, "category": LAUNCH,
                                  "name": p.name, "summary": p.description or d, "tile": LAUNCH_MAP[d],
                                  "description": "%s\nOK : ouvrir  (dossier %s)" % (p.description or p.name, d),
                                  "descriptor": p, "packages": []})
        except Exception as e:
            print("[WacayoubPanel] Mes outils: %s" % e)
        items.sort(key=lambda i: i["name"].lower())
        self.launch_items = items

    def _fetch_images(self):
        if self.images_busy or not self.model:
            return
        self.images_busy = True
        try:
            cmd = F.write_run_script(IM.fetch_script(self.model), "images.sh")[0]
        except Exception as e:
            self.images_busy = False
            print("[WacayoubPanel] images: %s" % e)
            return
        self.img_console.ePopen(cmd, self._images_done)

    def _images_done(self, data, retval, extra=None):
        self.images_busy = False
        if self.closed:
            return
        self.image_groups = IM.load_catalog()
        self._refresh_all()

    def _state(self, it):
        t = it.get("type")
        if t == LAUNCH:
            return F.ST_OK, "Ouvrir"
        if t == "image":
            d = IM.image_dir()
            if d and os.path.exists(os.path.join(d, it["file"])):
                return F.ST_OK, "Téléchargée"
            return F.ST_NONE, "Télécharger"
        return self.feed.item_state(it, self.installed, self.archs)

    def _refresh_all(self):
        self.installed = F.installed_packages()
        if self.feed and self.atv and not self.feed.atv_count:
            self.feed.attach_atv(self.atv)
        if self.feed:
            self.feed.env = {"python": tuple(sys.version_info[:3]), "model": self.model,
                             "model_name": self.model_name, "width": _W}
        sub = "%s  ·  v%s" % (self.model_name or "?", VERSION)
        if self.feed and self.feed.updated:
            sub += "  ·  feed %s" % self.feed.updated
        if self.opkg_busy:
            sub += "  ·  OpenATV : mise à jour…"
        elif self.atv and self.atv.lists_time:
            sub += "  ·  OpenATV %s" % time.strftime("%d/%m %H:%M", time.localtime(self.atv.lists_time))
        self["sub"].setText(sub)
        self._build_cats()
        self._build_items()

    # ------------------------------------------------------------ gauges
    def _tick(self):
        if self.closed:
            return
        cpu = S.cpu_percent()
        temp = S.cpu_temp()
        rp, rused, rtotal = S.ram()
        dp, dused, dtotal = S.storage("/")
        for key, pct, label in (("cpu", cpu, "CPU" + ("  %d°C" % temp if temp else "")),
                                ("ram", rp, "RAM  %d/%d Mo" % (rused, rtotal)),
                                ("disk", dp, "Stockage  %s" % S.human(dtotal))):
            png = pix(S.ring_step(pct))
            if png and self["ring_" + key].instance:
                self["ring_" + key].instance.setPixmap(png)
            self["pct_" + key].setText("%d%%" % pct)
            self["lab_" + key].setText(label)

    # ------------------------------------------------------------ lists
    def _cat_list(self):
        cats = []
        if self.query:
            cats.append({"id": SEARCH, "title": u"« %s »" % self.query})
        cats.append({"id": LAUNCH, "title": "Mes outils"})
        cats.append({"id": "all", "title": "Tout"})
        if self.feed:
            cats += self.feed.categories
        if self.image_groups:
            for distro, items in self.image_groups:
                cats.append({"id": items[0]["category"], "title": "Images · %s" % distro})
        else:
            cats.append({"id": "img-wait", "title": "Images"})
        return cats

    def _items_for(self, cat_id):
        if cat_id == LAUNCH:
            return list(self.launch_items)
        if cat_id.startswith("img-"):
            for _d, items in self.image_groups:
                if items[0]["category"] == cat_id:
                    return list(items)
            return []
        if cat_id == SEARCH:
            q = [w for w in F.fold(self.query).split() if w]
            mine = [i for i in self.launch_items if all(w in F.fold(i["name"] + " " + i["summary"]) for w in q)]
            return mine + (self.feed.search(self.query) if self.feed else [])
        if not self.feed:
            return []
        return self.feed.items_in(cat_id)

    def _build_cats(self, select=None):
        old = self["cats"].getSelectionIndex() if self.cat_ids else 0
        old_id = self.cat_ids[old] if 0 <= old < len(self.cat_ids) else None
        rows, self.cat_ids = [], []
        for c in self._cat_list():
            items = self._items_for(c["id"])
            n_upd = 0
            if self.feed and c["id"] != SEARCH and c["id"] != LAUNCH and not c["id"].startswith("img-"):
                for it in items:
                    if self.feed.item_state(it, self.installed, self.archs)[0] == F.ST_UPDATE:
                        n_upd += 1
            right = (u"%d ↑" % n_upd) if n_upd else (u"…" if c["id"] == "img-wait" else str(len(items)))
            self.cat_ids.append(c["id"])
            row = [c["id"]]
            icon = pix("c-%s.png" % c["id"]) or (pix("c-img.png") if c["id"].startswith("img-") else None)
            if icon:
                row.append(MultiContentEntryPixmapAlphaBlend(pos=(s(18), s(11)), size=(s(30), s(30)), png=icon, flags=PIX_FLAGS))
            row.append(MultiContentEntryText(pos=(s(62), 0), size=(s(260), s(52)), font=0,
                                             flags=RT_HALIGN_LEFT | RT_VALIGN_CENTER, text=c.get("title", c["id"]),
                                             color=C_TEXT, color_sel=0xFFFFFF))
            row.append(MultiContentEntryText(pos=(s(318), 0), size=(s(78), s(52)), font=1,
                                             flags=RT_HALIGN_RIGHT | RT_VALIGN_CENTER, text=right,
                                             color=0xFBBF24 if n_upd else C_DIM, color_sel=0xFFFFFF))
            rows.append(row)
        self["cats"].setList(rows)
        if select in self.cat_ids:
            self["cats"].moveToIndex(self.cat_ids.index(select))
        elif old_id in self.cat_ids:
            self["cats"].moveToIndex(self.cat_ids.index(old_id))
        elif rows:
            self["cats"].moveToIndex(min(old, len(rows) - 1))

    def _current_cat(self):
        i = self["cats"].getSelectionIndex()
        return self.cat_ids[i] if 0 <= i < len(self.cat_ids) else "all"

    def _build_items(self, keep=True):
        old = self["items"].getSelectionIndex() if (keep and self["items"].list) else 0
        rows = []
        for it in self._items_for(self._current_cat()):
            st, txt = self._state(it)
            if it.get("type") == "script":
                badge = pix("s-script.png")
                txt = "Script"
            elif it.get("type") == LAUNCH:
                badge = pix("s-open.png")
            else:
                badge = pix("s-%s.png" % STATE_IMG[st])
            kind = TYPE_LABEL.get(it.get("type"), "")
            row = [it]
            tile = item_tile(it)
            if tile:
                row.append(MultiContentEntryPixmapAlphaBlend(pos=(s(16), s(10)), size=(s(60), s(60)), png=tile, flags=PIX_FLAGS))
            row.append(MultiContentEntryText(pos=(s(94), s(8)), size=(s(820), s(38)), font=0,
                                             flags=RT_HALIGN_LEFT | RT_VALIGN_CENTER, text=it.get("name", it["id"]),
                                             color=C_TEXT, color_sel=0xFFFFFF))
            row.append(MultiContentEntryText(pos=(s(94), s(44)), size=(s(1180), s(28)), font=1,
                                             flags=RT_HALIGN_LEFT | RT_VALIGN_CENTER,
                                             text=(kind + "  ·  " if kind else "") + it.get("summary", ""),
                                             color=C_DIM, color_sel=0xDBEAFE))
            row.append(MultiContentEntryText(pos=(s(900), s(8)), size=(s(370), s(38)), font=1,
                                             flags=RT_HALIGN_RIGHT | RT_VALIGN_CENTER, text=txt,
                                             color=C_STATE[st], color_sel=C_STATE[st]))
            if badge:
                row.append(MultiContentEntryPixmapAlphaBlend(pos=(s(1286), s(14)), size=(s(26), s(26)), png=badge, flags=PIX_FLAGS))
            rows.append(row)
        self["items"].setList(rows)
        if rows:
            self["items"].moveToIndex(min(old, len(rows) - 1))
        self._update_desc()

    def _current_item(self):
        cur = self["items"].getCurrent()
        return cur[0] if cur else None

    def _update_desc(self):
        it = self._current_item()
        cat = self._current_cat()
        if not it and cat == "img-wait":
            self["desc"].setText("Recherche des images pour %s (OpenATV, OpenPLi, OpenViX, OpenBH, OpenSPA)…" % (self.model_name or self.model))
            return
        if it and it.get("type") in (LAUNCH, "image"):
            extra = ""
            if it.get("type") == "image":
                d = IM.image_dir()
                extra = "\nDossier : %s" % (d or "aucun disque ou clé USB monté")
            self["desc"].setText(it.get("description", "") + extra)
            return
        if not self.feed:
            self["desc"].setText("Aucune liste. Appuyez sur JAUNE pour lire le feed.")
            return
        if not it:
            if cat == SEARCH:
                self["desc"].setText(u"Aucun résultat pour « %s ».  MENU : nouvelle recherche  ·  EXIT : effacer" % self.query)
            else:
                self["desc"].setText("")
            return
        parts = [it.get("description", it.get("summary", ""))]
        names = [p for p in it.get("packages", []) if p in self.feed.packages]
        rv = it.get("reviewed_version")
        if rv and names and self.feed.packages[names[0]].get("version") != rv:
            parts[0] += u"\nLe feed propose maintenant %s, plus récent que la version vérifiée." % F.short_version(self.feed.packages[names[0]]["version"], 30)
        size = sum(int(self.feed.packages[p].get("size", 0) or 0) for p in names)
        vers = ", ".join("%s %s" % (p.replace("enigma2-plugin-", ""), F.short_version(self.feed.packages[p]["version"], 30)) for p in names)
        parts.append(u"Paquets : %s  ·  téléchargement %s" % (vers, S.human(size)))
        self["desc"].setText("\n".join(parts))

    # ------------------------------------------------------------ keys
    def _set_focus(self, items):
        self.focus_items = items
        self["cats"].selectionEnabled(not items)
        self["items"].selectionEnabled(items)

    def keyLeft(self):
        if self.focus_items:
            self._set_focus(False)
        else:
            self["cats"].pageUp()
            self._build_items(keep=False)

    def keyRight(self):
        if not self.focus_items and self["items"].list:
            self._set_focus(True)
        elif self.focus_items:
            self["items"].pageDown()
            self._update_desc()

    def keyUp(self):
        if self.focus_items:
            self["items"].up()
            self._update_desc()
        else:
            self["cats"].up()
            self._build_items(keep=False)

    def keyDown(self):
        if self.focus_items:
            self["items"].down()
            self._update_desc()
        else:
            self["cats"].down()
            self._build_items(keep=False)

    def keySearch(self):
        self.session.openWithCallback(self._search_done, VirtualKeyBoard,
                                      title="Rechercher un plugin, un skin, une liste de chaînes…", text=self.query)

    def _search_done(self, text):
        if text is None:
            return
        self.query = text.strip()
        self._build_cats(select=SEARCH if self.query else "all")
        self._build_items(keep=False)
        self._set_focus(bool(self.query and self["items"].list))

    def keyOk(self):
        if not self.focus_items:
            if self["items"].list:
                self._set_focus(True)
            return
        it = self._current_item()
        if not it:
            return
        if it.get("type") == LAUNCH:
            return self._launch(it)
        # OK only selects: open the detail card (preview, compatibility, description)
        self._open_details(it)

    def _big_icon(self, it):
        t = it.get("type")
        for name in (("B-i-%s.png" % it.get("tile", it.get("id"))) if t == LAUNCH else "B-i-%s.png" % it.get("id"),
                     "B-%s.png" % it.get("category", ""), "B-img.png" if t == "image" else "B-all.png"):
            path = os.path.join(IMG, name)
            if os.path.exists(path):
                return path
        return None

    def _open_details(self, it):
        st, txt = self._state(it)
        t = it.get("type")
        cat_title = dict((c["id"], c.get("title", "")) for c in self._cat_list()).get(it.get("category"), "")
        kind = {"image": "Image firmware", "script": "Script"}.get(t, TYPE_LABEL.get(t, "Paquet"))
        if t == "opkg":
            kind = "Paquet du feed OpenATV" + ("  ·  sélection vérifiée" if it.get("reviewed") else "")
        green, red = "", ""
        if t == "image":
            compat = [(True, "Image prévue pour %s" % (self.model_name or self.model))]
            d = IM.image_dir()
            compat.append((bool(d), "Dossier %s" % (d or "aucun disque/USB monté")))
            versions = u"%s\nTaille %s" % (it["file"], S.human(it.get("size")))
            if st == F.ST_OK:
                red = "Supprimer le fichier"
            else:
                green = "Télécharger"
        else:
            compat = self.feed.compat(it, self.archs) if self.feed else []
            names = [p for p in it.get("packages", []) if self.feed and p in self.feed.packages]
            vl = []
            for p in names:
                meta = self.feed.packages[p]
                cur = self.installed.get(p)
                vl.append(u"%s : %s%s" % (p.replace("enigma2-plugin-", ""), F.short_version(meta.get("version"), 26),
                                          (u"  (installé %s)" % F.short_version(cur, 20)) if cur else ""))
            size = sum(int(self.feed.packages[p].get("size", 0) or 0) for p in names)
            vl.append(u"Téléchargement %s" % S.human(size))
            versions = "\n".join(vl)
            if t == "script":
                green = "Lancer le script"
            elif st != F.ST_NA:
                green = {F.ST_NONE: "Installer", F.ST_UPDATE: "Mettre à jour", F.ST_PARTIAL: "Compléter",
                         F.ST_OK: "Réinstaller"}.get(st, "Installer")
            main = it.get("main") or (it["packages"][0] if it.get("packages") else "")
            if t != "script" and main in self.installed and main != PANEL_PKG:
                red = "Supprimer"
        info = {
            "img": IMG, "name": it.get("name", ""), "crumb": u"Wacayoub Panel  ›  %s" % cat_title,
            "kind": kind, "state_text": txt, "state_color": C_STATE.get(st), "compat": compat,
            "versions": versions, "description": it.get("description", it.get("summary", "")),
            "preview": it.get("preview", ""), "icon": self._big_icon(it), "green": green, "red": red,
        }
        self.session.openWithCallback(lambda act: self._details_done(it, act), WacayoubDetails, info)

    def _details_done(self, it, act):
        if not act:
            return
        t = it.get("type")
        if t == "image":
            return self._image_action(it) if act == "green" else self._image_delete(it)
        if act == "green":
            st = self._state(it)[0]
            return self._install(it, reinstall=(st == F.ST_OK))
        if act == "red":
            return self._ask_remove(it)

    def _choice(self, it, choice):
        if not choice or not choice[1]:
            return
        if choice[1] == "reinstall":
            self._install(it, reinstall=True)
        elif choice[1] == "remove":
            self._ask_remove(it)

    def keyInstall(self):
        it = self._current_item()
        if it and self.focus_items:
            if it.get("type") == LAUNCH:
                return self._launch(it)
            if it.get("type") == "image":
                return self._image_action(it)
            self._install(it)

    def keyRemove(self):
        it = self._current_item()
        if it and self.focus_items:
            if it.get("type") == "image":
                return self._image_delete(it)
            if it.get("type") == LAUNCH:
                return
            self._ask_remove(it)

    def _launch(self, it):
        try:
            it["descriptor"](session=self.session)
        except Exception as e:
            self.session.open(MessageBox, "Impossible d'ouvrir %s :\n%s" % (it["name"], e), MessageBox.TYPE_ERROR)

    def _image_action(self, it):
        d = IM.image_dir()
        if not d:
            self.session.open(MessageBox, "Aucun disque dur ou clé USB monté pour enregistrer l'image.", MessageBox.TYPE_ERROR)
            return
        if self._state(it)[0] == F.ST_OK:
            self.session.open(MessageBox, "%s est déjà téléchargée.\nPour flasher : Menu > Flash Manager > Images téléchargées.\nROUGE : supprimer le fichier." % it["file"],
                              MessageBox.TYPE_INFO)
            return
        free = F.free_bytes(os.path.dirname(d))
        if free >= 0 and it["size"] and it["size"] + 50 * 1024 * 1024 > free:
            self.session.open(MessageBox, "Pas assez de place sur %s : il faut %s, libre %s." % (os.path.dirname(d), S.human(it["size"]), S.human(free)),
                              MessageBox.TYPE_ERROR)
            return
        self._confirm_run("Télécharger l'image %s ?\n%s  ·  %s\nDossier : %s\n\nRien n'est flashé : vous flasherez vous-même avec Menu > Flash Manager."
                          % (it["name"], it["file"], S.human(it["size"]), d),
                          IM.download_commands(it, d), "Image %s" % it["name"], restart=False)

    def _image_delete(self, it):
        d = IM.image_dir()
        path = os.path.join(d, it["file"]) if d else None
        if not path or not os.path.exists(path):
            return

        def go(yes):
            if yes:
                try:
                    os.remove(path)
                except OSError as e:
                    self.session.open(MessageBox, "Erreur : %s" % e, MessageBox.TYPE_ERROR)
                self._build_items()
        self.session.openWithCallback(go, MessageBox, "Supprimer le fichier %s ?" % path, MessageBox.TYPE_YESNO)

    def keyUpdateAll(self):
        if not self.feed:
            return
        names = []
        for it in self.feed.items:
            if it.get("type") in ("script", "opkg"):
                continue
            for p in self.feed.outdated(it, self.installed):
                if p not in names:
                    names.append(p)
        if not names:
            self.session.open(MessageBox, "Tous mes plugins sont à jour.", MessageBox.TYPE_INFO, timeout=4)
            return
        self._confirm_run("Mettre à jour %d paquet(s) ?\n%s" % (len(names), "\n".join(names)),
                          F.install_commands(self.feed, names), "Mise à jour")

    # ------------------------------------------------------------ actions
    def _install(self, it, reinstall=False):
        st, txt = self._state(it)
        if st == F.ST_NA:
            self.session.open(MessageBox, "%s : %s." % (it["name"], txt), MessageBox.TYPE_ERROR, timeout=6)
            return
        if it.get("type") == "script":
            self._confirm_run(u"Lancer le script « %s » ?\n%s" % (it["name"], it.get("summary", "")),
                              F.script_commands(self.feed, it), it["name"], restart=False)
            return
        names = list(it["packages"]) if reinstall else self.feed.to_fetch(it, self.installed)
        if not names:
            self.session.open(MessageBox, "%s est déjà à jour." % it["name"], MessageBox.TYPE_INFO, timeout=4)
            return
        need = self.feed.install_size(names)
        free = F.free_bytes("/")
        if free >= 0 and need and need + 8 * 1024 * 1024 > free:
            self.session.open(MessageBox, "Pas assez de place : il faut %s, libre %s." % (S.human(need), S.human(free)),
                              MessageBox.TYPE_ERROR)
            return
        if it.get("type") == "opkg":
            cmds = F.opkg_install_commands(names, reinstall=reinstall)
        else:
            cmds = F.install_commands(self.feed, names, reinstall=reinstall)
        verb = "Réinstaller" if reinstall else ("Mettre à jour" if st == F.ST_UPDATE else "Installer")
        self._confirm_run("%s %s ?\n%s\nPlace utilisée : %s" % (verb, it["name"], "\n".join(names), S.human(need)),
                          cmds, "%s %s" % (verb, it["name"]))

    def _ask_remove(self, it):
        if it.get("type") == "script":
            return
        names = [p for p in it.get("remove", [it.get("main") or it["packages"][0]]) if p in self.installed]
        if not names:
            self.session.open(MessageBox, "%s n'est pas installé." % it["name"], MessageBox.TYPE_INFO, timeout=4)
            return
        if PANEL_PKG in names:
            self.session.open(MessageBox, "Le panel ne peut pas se supprimer lui-même ici.\nUtilisez Menu > Paramètres > Logiciels.",
                              MessageBox.TYPE_INFO)
            return
        self._confirm_run("Supprimer %s ?\n%s" % (it["name"], "\n".join(names)),
                          F.remove_commands(names), "Supprimer %s" % it["name"])

    def _confirm_run(self, question, cmds, title, restart=True):
        def go(yes):
            if yes:
                try:
                    cmdlist = F.write_run_script(cmds)
                except Exception as e:
                    self.session.open(MessageBox, "Erreur : %s" % e, MessageBox.TYPE_ERROR)
                    return
                self.session.openWithCallback(lambda *a: self._after_run(restart), Console,
                                              title=title, cmdlist=cmdlist, closeOnSuccess=False)
        self.session.openWithCallback(go, MessageBox, question, MessageBox.TYPE_YESNO)

    def _after_run(self, restart):
        before = dict(self.installed)
        self._refresh_all()
        self._build_launch()
        self._build_items()
        if restart and before != self.installed:
            self.session.openWithCallback(self._restart_answer, MessageBox,
                                          "Changement effectué.\nRedémarrer l'interface maintenant pour l'appliquer ?",
                                          MessageBox.TYPE_YESNO)

    def _restart_answer(self, yes):
        if yes:
            self.session.open(TryQuitMainloop, 3)

    def keyExit(self):
        if self.focus_items:
            self._set_focus(False)
            return
        if self.query:
            self.query = ""
            self._build_cats(select="all")
            self._build_items(keep=False)
            return
        self.async_console.killAll()
        # 'opkg update' keeps running if needed; never kill opkg half-way
        self.closed = True
        self.close()


def main(session, **kwargs):
    session.open(WacayoubPanel)


def Plugins(**kwargs):
    return [
        PluginDescriptor(name="Wacayoub Panel", description="Installer et mettre à jour mes plugins, skins et scripts",
                         where=PluginDescriptor.WHERE_PLUGINMENU, icon="plugin.png", fnc=main),
        PluginDescriptor(name="Wacayoub Panel", description="Installer et mettre à jour mes plugins, skins et scripts",
                         where=PluginDescriptor.WHERE_EXTENSIONSMENU, fnc=main),
    ]
