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
from . import extfeeds as X
from . import images as IM
from .details import WacayoubDetails
from . import sysinfo as S
from . import docteur as D
from . import garde as G

VERSION = "2.5.0"
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
TYPE_LABEL = {"plugin": "Plugin", "skin": "Skin", "script": "Script", "panel": "Panel", "opkg": "", "ext": "", "image": "Image"}
SEARCH = "search"
FEEDSRC = "feedsrc"
RECV = "recv"  # 'Mon récepteur' info rows (nothing to install)
DOCTOR = "doctor"  # row that opens the Fixo screen
TOOL_CATS = ('communaute', 'scripts', 'fix', 'dns', 'deps', 'disk')  # categories of the index shown as they are
# where an item comes from, shown on every row (lists are merged across sources)
SOURCE_COLOR = {"Wacayoub": 0x60A5FA, "Universel": 0xE2E8F0, u"Installé": 0x4ADE80, "OpenATV": 0x34D399, "OpenPLi": 0xFB923C, "OpenViX": 0x4ADE80,
                "EGAMI": 0xFACC15, "OpenBH": 0xA78BFA, "OpenHDF": 0xF472B6, "OpenSPA": 0xF87171}


SOURCE_ORDER = ["Wacayoub", "OpenATV", "Universel", "OpenPLi", "OpenViX", "OpenBH", "EGAMI", "OpenHDF", "OpenSPA"]


def sources_of(it, common=None):
    """Every source an item belongs to (for the filter): its own feed plus the images that share it."""
    s = set([source_of(it, None)])
    if it.get("type") in ("opkg", "ext") and common and it.get("packages") and it["packages"][0] in common:
        s |= set(common[it["packages"][0]]) | set(["Universel"])
    return s


def source_of(it, common=None):
    t = it.get("type")
    if t == LAUNCH:
        return it.get("src", "Wacayoub")
    if t == FEEDSRC:
        return it.get("src", "")
    if t in (RECV, DOCTOR):
        return "Wacayoub" if t == DOCTOR else ""
    if t in ("opkg", "ext") and common and it.get("packages") and it["packages"][0] in common:
        return "Universel"  # same tool in several images: no image name
    if t == "opkg":
        return "OpenATV"
    if t == "ext":
        return it.get("ext", "")
    if t == "image":
        return it.get("distro", "")
    return "Wacayoub"
LAUNCH = "launch"
# my plugin folders -> icon id (Mes outils)
LAUNCH_MAP = {
    "SatIPTVBridge": "iptosat", "IPTVBouquetAI": "iptvbouquetai", "EPGManager": "epgmanager", "BOP2": "bop2",
    "IPAudioPro": "ipaudio", "IPAudioSmartAI": "ipaudio", "SalaatNEO": "salaatneo", "NeoWeather": "neoweather",
    "NeoConnect": "neoconnect", "MetrixNEOHelper": "metrixneohelper", "MetrixNeoAI": "metrixneohelper",
    "MetrixNEOBoot": "metrixneohelper", "OSAppleTV": "osappletv", "OrbitAIColours": "orbitai", "NovaOrbit": "novaorbit",
    "WMultiBoot": "wmultiboot",
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
        return pix("t-i-%s.png" % it.get("tile")) or pix("t-%s.png" % it.get("tile")) or pix("t-launch.png")
    if it.get("type") == FEEDSRC:
        return pix("t-feeds.png")
    if it.get("type") == RECV:
        return pix("t-r-%s.png" % it.get("tile")) or pix("t-recv.png")
    if it.get("type") == DOCTOR:
        return pix("t-p2p.png" if it.get("id") == "p2p" else "t-doctor.png")
    g = F.group_of(it)
    if g and it.get("type") in ("opkg", "ext") and pix("t-%s.png" % g):
        return pix("t-%s.png" % g)
    if it.get("type") == "image":
        return pix("t-%s.png" % it.get("category")) or pix("t-img.png")
    if it.get("type") == "ext":
        return pix("t-ext.png")
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
        "dx": 72, "dy": 832, "dw": 1068, "dh": 124, "df": 25,
        "r0": 1164, "r1": 1342, "r2": 1520, "r3": 1698, "ry": 828, "rs": 104,
        "pw": 104, "py": 864, "pf": 26, "ny": 936, "nw": 170, "nh": 28, "nf": 19,
        "fy": 996, "fd": 26, "fty": 988, "fth": 42, "ff": 25,
        "k1": 62, "k2": 392, "k3": 742, "k4": 1062, "k5": 1452,
    }.items():
        d[k] = s(v)
    d["n0"], d["n1"], d["n2"], d["n3"] = d["r0"] - s(33), d["r1"] - s(33), d["r2"] - s(33), d["r3"] - s(33)
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
      <widget name="ring_temp" position="%(r0)d,%(ry)d" size="%(rs)d,%(rs)d" alphatest="blend" scale="1" />
      <widget name="pct_temp" position="%(r0)d,%(py)d" size="%(pw)d,%(sth)d" font="Regular;%(pf)d" foregroundColor="#00FFFFFF" backgroundColor="#00070B14" transparent="1" halign="center" valign="center" zPosition="2" />
      <widget name="lab_temp" position="%(n0)d,%(ny)d" size="%(nw)d,%(nh)d" font="Regular;%(nf)d" foregroundColor="#008C9AB0" backgroundColor="#00070B14" transparent="1" halign="center" />
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

    def __init__(self, session, start_cat=None, start_action=None):
        Screen.__init__(self, session)
        self.setTitle("Wacayoub Panel")
        self.start_cat, self.start_action = start_cat, start_action
        self.start_timer = eTimer()
        self.start_timer.callback.append(self._apply_start_action)
        self.feed = None
        self.atv = None
        self.installed = {}
        self.archs = F.supported_archs()
        self.focus_items = False
        self.cat_ids = []
        self.query = ""
        self.marked = []  # item ids ticked with OK for a grouped install
        self.src_filter = None  # key 0: show one source only
        self._batch = False
        self.closed = False
        self.opkg_busy = False
        self.launch_items = []
        self.image_groups = []
        self.images_busy = False
        self.ext = None
        self.ext_busy = False
        self.ext_console = AsyncConsole()
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
        for k in ("temp", "cpu", "ram", "disk"):
            self["ring_" + k] = Pixmap()
            self["pct_" + k] = Label("")
            self["lab_" + k] = Label("")
        self["key_red"] = Label("Supprimer")
        self["key_green"] = Label("Installer / MAJ")
        self["key_yellow"] = Label("Actualiser")
        self["key_blue"] = Label("Tout mettre à jour")
        self["key_menu"] = Label("MENU  Rechercher")

        self["actions"] = ActionMap(["OkCancelActions", "ColorActions", "DirectionActions", "MenuActions", "InfoActions", "NumberActions"], {
            "ok": self.keyOk,
            "cancel": self.keyExit,
            "red": self.keyRemove,
            "green": self.keyInstall,
            "yellow": self.refreshFeed,
            "blue": self.keyUpdateAll,
            "menu": self.keySearch,
            "info": self.keyInfo,
            "0": self.keyFilter,
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
        self._apply_start()

    def _apply_start(self):
        """Opened from the home screen: show the chosen category, then run the action once drawn."""
        cat = self.start_cat
        if cat == "images":
            cat = ([c for c in self.cat_ids if c.startswith("img-")] or [None])[0]
        if cat in self.cat_ids:
            self["cats"].moveToIndex(self.cat_ids.index(cat))
            self._build_items(keep=False)
            if self["items"].list and not self.start_action:
                self._set_focus(True)
        if self.start_action:
            self.start_timer.start(300, True)

    def _apply_start_action(self):
        if getattr(self, "closed", True):  # enigma2 clears attributes of closed screens
            return
        act, self.start_action = self.start_action, None
        if act == "update":
            self.keyUpdateAll()
        elif act == "search":
            self.keySearch()
        elif act and act.startswith("run:") and self.feed:
            it = [i for i in self.feed.items if i["id"] == act[4:]]
            if it:
                self._set_focus(True)
                if it[0] in [r[0] for r in self["items"].list]:
                    self["items"].moveToIndex([r[0] for r in self["items"].list].index(it[0]))
                self._install(it[0])

    def _on_close(self):
        self.closed = True
        self.stat_timer.stop()
        self.start_timer.stop()

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
        self._load_ext()

    def _load_ext(self):
        """Other images' feeds (already downloaded in /tmp): offered only when their deps exist here."""
        try:
            installed = F.installed_packages()
            own = set(installed)
            avail = set(installed)
            if self.atv:
                own |= set(self.atv.packages)
                avail |= self.atv.all_names
            if self.feed:
                own |= set(self.feed.data.get("packages", {}))
            self.ext = X.load(own, avail, F.compare_versions, set(self.atv.packages), self.archs) if self.atv else None
        except Exception as e:
            self.ext = None
            print("[WacayoubPanel] other feeds: %s" % e)
        if self.feed:
            self.feed = F.Feed(self.feed.data)  # fresh copy, OpenATV + other feeds attached in _refresh_all

    def _fetch_ext(self):
        if self.ext_busy or not self.model:
            return
        self.ext_busy = True
        try:
            cmd = F.write_run_script(X.fetch_script(self.model, self.archs), "ext.sh")[0]
        except Exception as e:
            self.ext_busy = False
            print("[WacayoubPanel] other feeds: %s" % e)
            return
        self.ext_console.ePopen(cmd, self._ext_done)

    def _ext_done(self, data, retval, extra=None):
        self.ext_busy = False
        if getattr(self, "closed", True):  # enigma2 clears attributes of closed screens
            return
        self._load_ext()
        self._refresh_all()

    def refreshFeed(self, auto=False):
        """JAUNE: my feed + 'opkg update'. On open: opkg update only if the lists are over a day old."""
        self["status"].setText("Lecture du feed en ligne…")
        stale = not self.atv or not self.atv.lists_time or time.time() - self.atv.lists_time > 86400
        if (not auto or stale) and not self.opkg_busy:
            self.opkg_busy = True
            self.atv_console.ePopen("opkg update", self._opkg_done)
        if not auto or X.age_hours() > 24:
            self._fetch_ext()
        tmp = "/tmp/wacayoubpanel-index.json"
        self.async_console.ePopen(F.index_fetch_command(tmp), self._feed_done, tmp)

    def _opkg_done(self, data, retval, extra=None):
        self.opkg_busy = False
        if getattr(self, "closed", True):  # enigma2 clears attributes of closed screens
            return
        self._load_atv()
        self._refresh_all()
        if retval != 0:
            self["status"].setText("Listes OpenATV : mise à jour impossible, listes en cache.")

    def _feed_done(self, data, retval, tmp):
        if getattr(self, "closed", True):  # enigma2 clears attributes of closed screens
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
            self._update_keys()
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
                if d == "WacayoubPanel":
                    continue
                mine = d in LAUNCH_MAP
                items.append({"id": "run:%s:%s" % (d, p.name), "type": LAUNCH, "category": LAUNCH,
                              "name": p.name, "summary": p.description or d, "tile": LAUNCH_MAP.get(d, "installed"),
                              "src": "Wacayoub" if mine else u"Installé",
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
        if getattr(self, "closed", True):  # enigma2 clears attributes of closed screens
            return
        self.image_groups = IM.load_catalog()
        self._refresh_all()

    def _state(self, it):
        t = it.get("type")
        if t == LAUNCH:
            return F.ST_OK, "Ouvrir"
        if t == RECV:
            return F.ST_OK, ""
        if t == DOCTOR:
            return F.ST_OK, u"Ouvrir"
        if t == FEEDSRC:
            return F.ST_OK, (u"Filtre actif" if self.src_filter == it.get("src") else u"Afficher")
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
        if self.feed and self.ext and not self.feed.ext_count:
            self.feed.attach_ext(self.ext)
        if self.feed:
            self.feed.env = {"python": tuple(sys.version_info[:3]), "model": self.model,
                             "model_name": self.model_name, "width": _W, "installed": self.installed}
        sub = "%s  ·  v%s" % (self.model_name or "?", VERSION)
        if self.src_filter:  # short header: the feed dates do not fit next to the filter
            self["sub"].setText(u"Filtre : %s  ·  %s  ·  v%s" % (self.src_filter, self.model_name or "?", VERSION))
            self._build_cats()
            self._build_items()
            return
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
        if getattr(self, "closed", True):  # enigma2 clears attributes of closed screens
            return
        cpu = S.cpu_percent()
        temp = S.cpu_temp()
        rp, rused, rtotal = S.ram()
        dp, dused, dtotal = S.storage("/")
        if temp:
            png = pix(S.ring_step(S.temp_step(temp)))
            if png and self["ring_temp"].instance:
                self["ring_temp"].instance.setPixmap(png)
            self["pct_temp"].setText(u"%d°" % temp)
            self["lab_temp"].setText(u"Température")
        for key, pct, label in (("cpu", cpu, "CPU"),
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
        cats.append({"id": LAUNCH, "title": u"Installés"})
        cats.append({"id": RECV, "title": u"Mon récepteur"})
        for gid, title in F.GROUPS:
            cats.append({"id": gid, "title": title})
        cats.append({"id": "feeds", "title": "Feeds"})
        if self.feed:
            cats += sorted([c for c in self.feed.data.get("categories", []) if c["id"] in TOOL_CATS],
                           key=lambda c: TOOL_CATS.index(c["id"]))
        if self.image_groups:
            for distro, items in self.image_groups:
                cats.append({"id": items[0]["category"], "title": "Images · %s" % distro})
        else:
            cats.append({"id": "img-wait", "title": "Images"})
        return cats

    def _items_for(self, cat_id):
        if cat_id == LAUNCH:
            return list(self.launch_items)
        if cat_id == "feeds":
            return self._feed_sources()
        if cat_id == RECV:
            p2p = {"id": "p2p", "type": DOCTOR, "category": RECV, "name": u"Partage LAN (entre deux récepteurs)",
                   "summary": u"Envoyer ou recevoir les chaînes, l'IPTV et la softcam sur le réseau de la maison",
                   "description": u"Copie les chaînes, l'IPTV et la softcam d'un récepteur à l'autre sur le même réseau, "
                                  u"avec un code à 8 chiffres. Ce qui est remplacé est gardé (annulable).\nOK : ouvrir",
                   "packages": []}
            return [p2p] + self._recv_rows()
        if cat_id == "fix":
            doc = {"id": "doctor", "type": DOCTOR, "category": "fix", "name": u"Fixo (réparation intelligente)",
                   "summary": u"Analyse les plantages et propose la réparation (feeds et règles en ligne)",
                   "description": u"Fixo : lit les rapports de plantage, trouve le plugin et l'erreur, cherche une version "
                                  u"corrigée sur Internet et propose la réparation (installer, mettre à jour, réinstaller, désactiver).\nOK : ouvrir",
                   "packages": []}
            return [doc] + (self.feed.items_in(cat_id) if self.feed else [])
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
        items = self.feed.items_in(cat_id)
        if self.src_filter:
            items = [i for i in items if self.src_filter in sources_of(i, self.feed.common)]
        return items

    def _recv_rows(self):
        try:
            rows = S.receiver_info(self.model_name)
        except Exception as e:
            print("[WacayoubPanel] receiver info: %s" % e)
            return []
        tiles = {"model": "model", "temp": "temp", "cpu": "cpu", "ram": "ram", "flash": "flash", "net": "net", "dns": "net",
                 "up": "up", "cam": "cam", "skin": "skin", "soft": "soft"}
        out = []
        for rid, title, value, detail in rows:
            key = "disk" if rid.startswith("disk") else "tuner" if rid.startswith("tuner") else rid
            out.append({"id": "recv:" + rid, "type": RECV, "category": RECV, "name": title, "value": value,
                        "summary": value + ((u"  ·  " + detail) if detail else ""), "tile": tiles.get(key, key),
                        "description": u"%s : %s%s" % (title, value, ("\n" + detail) if detail else ""), "packages": []})
        return out

    def _feed_sources(self):
        """One row per source; OK shows only that source in every list."""
        if not self.feed:
            return []
        count = {}
        for i in self.feed.items:
            if F.group_of(i):
                for s in sources_of(i, self.feed.common):
                    count[s] = count.get(s, 0) + 1
        about = {"Wacayoub": u"Mes plugins et skins", "OpenATV": u"Feed officiel de cette image",
                 "Universel": u"Outils présents dans plusieurs images"}
        rows = []
        for s in SOURCE_ORDER:
            if s in count:
                rows.append({"id": "src:" + s, "type": FEEDSRC, "category": "feeds", "src": s, "name": s,
                             "summary": u"%d paquets  ·  %s" % (count[s], about.get(s, u"Feed de l'image %s" % s)),
                             "description": u"OK : n'afficher que %s dans Addons, Système, Skins…  (0 : changer de source)" % s,
                             "packages": []})
        return rows

    def keyFilter(self):
        """0: show only one source (Wacayoub, OpenATV, Universel, OpenPLi, OpenViX, ...), then all again."""
        present = set()
        if self.feed:
            for i in self.feed.items:
                present |= sources_of(i, self.feed.common)
        order = [None] + [x for x in SOURCE_ORDER if x in present]
        cur = order.index(self.src_filter) if self.src_filter in order else 0
        self.src_filter = order[(cur + 1) % len(order)]
        self._refresh_all()
        self._update_keys()

    def _build_cats(self, select=None):
        old = self["cats"].getSelectionIndex() if self.cat_ids else 0
        old_id = self.cat_ids[old] if 0 <= old < len(self.cat_ids) else None
        rows, self.cat_ids = [], []
        for c in self._cat_list():
            items = self._items_for(c["id"])
            n_upd = 0
            if self.feed and c["id"] not in (SEARCH, LAUNCH, RECV, "feeds") and not c["id"].startswith("img-"):
                for it in items:
                    if it.get("type") != DOCTOR and self.feed.item_state(it, self.installed, self.archs)[0] == F.ST_UPDATE:
                        n_upd += 1
            right = (u"%d ↑" % n_upd) if n_upd else (u"…" if c["id"] == "img-wait" else str(len(items)))
            self.cat_ids.append(c["id"])
            row = [c["id"]]
            icon = pix("c-%s.png" % c["id"]) or (pix("c-img.png") if c["id"].startswith("img-") else
                                                 pix("c-ext.png") if c["id"].startswith("ext-") else None)
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
            elif it.get("type") == RECV:
                badge, txt = None, ""
            elif it.get("type") == DOCTOR:
                badge, txt = pix("s-open.png"), u"Ouvrir"
            else:
                badge = pix("s-%s.png" % STATE_IMG[st])
            kind = TYPE_LABEL.get(it.get("type"), "")
            row = [it]
            tile = item_tile(it)
            if tile:
                row.append(MultiContentEntryPixmapAlphaBlend(pos=(s(16), s(10)), size=(s(60), s(60)), png=tile, flags=PIX_FLAGS))
            if it["id"] in self.marked and pix("sel.png"):
                row.append(MultiContentEntryPixmapAlphaBlend(pos=(s(54), s(46)), size=(s(30), s(30)), png=pix("sel.png"), flags=PIX_FLAGS))
                txt = u"Sélectionné pour installation"
            row.append(MultiContentEntryText(pos=(s(94), s(8)), size=(s(820), s(38)), font=0,
                                             flags=RT_HALIGN_LEFT | RT_VALIGN_CENTER, text=it.get("name", it["id"]),
                                             color=C_TEXT, color_sel=0xFFFFFF))
            src = source_of(it, self.feed.common if self.feed else None)
            row.append(MultiContentEntryText(pos=(s(94), s(44)), size=(s(132), s(28)), font=1,
                                             flags=RT_HALIGN_LEFT | RT_VALIGN_CENTER, text=src,
                                             color=SOURCE_COLOR.get(src, C_DIM), color_sel=0xFFFFFF))
            row.append(MultiContentEntryText(pos=(s(232), s(44)), size=(s(1042), s(28)), font=1,
                                             flags=RT_HALIGN_LEFT | RT_VALIGN_CENTER,
                                             text=(kind + "  ·  " if kind and kind != src else "") + it.get("summary", ""),
                                             color=C_DIM, color_sel=0xDBEAFE))
            row.append(MultiContentEntryText(pos=(s(900), s(8)), size=(s(370), s(38)), font=1,
                                             flags=RT_HALIGN_RIGHT | RT_VALIGN_CENTER, text=txt,
                                             color=0x60A5FA if it["id"] in self.marked else C_STATE[st],
                                             color_sel=0xBFDBFE if it["id"] in self.marked else C_STATE[st]))
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
        if it and it.get("type") in (LAUNCH, "image", FEEDSRC, RECV, DOCTOR):
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
            if cat in F.GROUP_IDS:
                self["desc"].setText(u"Aucun paquet dans cette catégorie pour ce récepteur" +
                                     (u" avec le filtre %s (0 : changer)." % self.src_filter if self.src_filter else u"."))
                return
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
        if len(names) > 2:  # pack: the list would not fit
            vers = u"%d paquets" % len(names)
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
        if it.get("type") == RECV:
            return
        if it.get("type") == DOCTOR:
            return self.session.open(WacayoubP2P if it.get("id") == "p2p" else WacayoubDoctor)
        if it.get("type") == FEEDSRC:
            self.src_filter = it["src"]
            self._refresh_all()
            self._update_keys()
            self._set_focus(False)
            self._build_cats(select="addons")
            return self._build_items(keep=False)
        if it.get("type") in ("image", "script"):
            return self._open_details(it)  # not batch-installable: show the card
        # OK ticks / unticks the item to prepare a grouped install (INFO opens the card)
        self._toggle_mark(it)

    def keyInfo(self):
        it = self._current_item() if self.focus_items else None
        if it and it.get("type") not in (LAUNCH, FEEDSRC, RECV, DOCTOR):
            self._open_details(it)

    # ------------------------------------------------------------ selection (grouped install)
    def _toggle_mark(self, it):
        iid = it["id"]
        if iid in self.marked:
            self.marked.remove(iid)
        else:
            st, txt = self._state(it)
            if st == F.ST_NA:
                self.session.open(MessageBox, "%s : %s." % (it["name"], txt), MessageBox.TYPE_INFO, timeout=4)
                return
            if st == F.ST_OK:
                self.session.open(MessageBox, "%s est déjà installé et à jour.\nINFO : fiche (réinstaller / supprimer)." % it["name"],
                                  MessageBox.TYPE_INFO, timeout=4)
                return
            self.marked.append(iid)
        self._build_items()
        self["items"].down()  # next item, like ticking a list
        self._update_desc()
        self._update_keys()

    def _update_keys(self):
        n = len(self.marked)
        self["key_green"].setText("Installer la sélection (%d)" % n if n else "Installer / MAJ")
        self["key_red"].setText("Vider la sélection" if n else "Supprimer")
        if n:
            self["status"].setText(u"%d sélectionné(s)  ·  VERT : installer  ·  ROUGE : vider" % n)
        elif self.src_filter:
            self["status"].setText(u"Source : %s  ·  0 : source suivante" % self.src_filter)
        else:
            self["status"].setText(u"OK : cocher  ·  INFO : fiche  ·  0 : filtrer par source")

    def _marked_items(self):
        if not self.feed:
            return []
        by_id = dict((i["id"], i) for i in self.feed.items)
        return [by_id[i] for i in self.marked if i in by_id]

    def _install_marked(self):
        own, opkg, names, skipped = [], [], [], []
        for it in self._marked_items():
            st, txt = self._state(it)
            if st in (F.ST_NA, F.ST_OK):
                skipped.append("%s (%s)" % (it["name"], txt))
                continue
            names.append(it["name"])
            target = opkg if it.get("type") == "opkg" else own
            for p in self.feed.to_fetch(it, self.installed):
                if p not in own and p not in opkg:
                    target.append(p)
        if not own and not opkg:
            self.session.open(MessageBox, "Rien à installer dans la sélection.", MessageBox.TYPE_INFO, timeout=4)
            return
        need = self.feed.install_size(own + opkg)
        free = F.free_bytes("/")
        if free >= 0 and need and need + 8 * 1024 * 1024 > free:
            self.session.open(MessageBox, "Pas assez de place : il faut %s, libre %s." % (S.human(need), S.human(free)),
                              MessageBox.TYPE_ERROR)
            return
        body = (F.install_commands(self.feed, own) if own else "") + (F.opkg_install_commands(opkg) if opkg else "")
        q = u"Installer %d élément(s) ?\n%s\n%d paquet(s)  ·  place utilisée : %s" % (
            len(names), u"\n".join(u"•  " + n for n in names), len(own) + len(opkg), S.human(need))
        if skipped:
            q += u"\nIgnorés : " + ", ".join(skipped)
        exts = sorted(set(i.get("ext") for i in self._marked_items() if i.get("type") == "ext"))
        if exts:
            q += u"\nAttention : paquets d'autres images (%s), non testés sur OpenATV." % ", ".join(exts)
        self._batch = True
        self._confirm_run(q, body, u"Installer la sélection (%d)" % len(names))

    def _big_icon(self, it):
        t = it.get("type")
        for name in (("B-i-%s.png" % it.get("tile", it.get("id"))) if t == LAUNCH else "B-i-%s.png" % it.get("id"),
                     "B-%s.png" % (F.group_of(it) or ""), "B-%s.png" % it.get("category", ""), "B-ext.png" if t == "ext" else "B-img.png" if t == "image" else "B-all.png"):
            path = os.path.join(IMG, name)
            if os.path.exists(path):
                return path
        return None

    def _open_details(self, it):
        st, txt = self._state(it)
        t = it.get("type")
        titles = dict((c["id"], c.get("title", "")) for c in self._cat_list())
        cat_title = titles.get(F.group_of(it) or it.get("category"), "") or titles.get(it.get("category"), "")
        kind = {"image": "Image firmware", "script": "Script"}.get(t, TYPE_LABEL.get(t, "Paquet"))
        if t == "opkg":
            kind = "Paquet du feed OpenATV" + ("  ·  sélection vérifiée" if it.get("reviewed") else "")
        elif t == "ext":
            kind = u"Paquet de l'image %s  ·  non testé sur OpenATV" % it.get("ext", "?")
        if t in ("opkg", "ext") and self.feed and it.get("packages") and it["packages"][0] in self.feed.common:
            kind = u"Universel  ·  présent dans %s" % ", ".join(self.feed.common[it["packages"][0]])
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
        if self.marked:
            return self._install_marked()
        it = self._current_item()
        if it and self.focus_items:
            if it.get("type") in (RECV, FEEDSRC):
                return
            if it.get("type") == DOCTOR:
                return self.session.open(WacayoubP2P if it.get("id") == "p2p" else WacayoubDoctor)
            if it.get("type") == LAUNCH:
                return self._launch(it)
            if it.get("type") == "image":
                return self._image_action(it)
            self._install(it)

    def keyRemove(self):
        if self.marked:
            self.marked = []
            self._build_items()
            self._update_keys()
            return
        it = self._current_item()
        if it and self.focus_items:
            if it.get("type") == "image":
                return self._image_delete(it)
            if it.get("type") in (LAUNCH, RECV, FEEDSRC, DOCTOR):
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
        own, opkg = [], []
        for it in self.feed.items:
            if it.get("type") == "script":
                continue
            target = opkg if it.get("type") == "opkg" else own
            for p in self.feed.outdated(it, self.installed):
                if p not in own and p not in opkg:
                    target.append(p)
        names = own + opkg
        if not names:
            self.session.open(MessageBox, "Tout est à jour.", MessageBox.TYPE_INFO, timeout=4)
            return
        shown = names[:14] + ([u"… et %d autre(s)" % (len(names) - 14)] if len(names) > 14 else [])
        body = (F.install_commands(self.feed, own) if own else "") + (F.opkg_install_commands(opkg) if opkg else "")
        self._confirm_run("Mettre à jour %d paquet(s) ?\n%s" % (len(names), "\n".join(shown)), body, "Mise à jour")

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
        warn = (u"\nAttention : paquet de l'image %s, non testé sur OpenATV." % it.get("ext")) if it.get("type") == "ext" else ""
        self._confirm_run("%s %s ?\n%s\nPlace utilisée : %s%s" % (verb, it["name"], "\n".join(names), S.human(need), warn),
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
        if getattr(self, "_batch", False):
            self._batch = False
            self.marked = []
            self._update_keys()
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


# ---------------------------------------------------------------- home screen (dashboard + alerts)
HOME_TILES = [("fix", "fix"), ("addons", "addons"), ("softcam", "softcam"), ("skins", "skins"),
              ("launch", LAUNCH), ("recv", RECV), ("dns", "dns"), ("img", "images")]
LEVEL_ORDER = {"red": 0, "amber": 1, "blue": 2, "green": 3, "gray": 4}


def count_updates(model, archs):
    """Same list as BLUE 'Tout mettre à jour' in the panel (mine, OpenATV and other images' packages)."""
    feed = F.Feed.load(F.CACHE_FILE)
    installed = F.installed_packages()
    atv = F.AtvCatalog(archs=archs)
    own = set(installed) | set(atv.packages) | set(feed.data.get("packages", {}))
    avail = set(installed) | atv.all_names
    ext = X.load(own, avail, F.compare_versions, set(atv.packages), archs)
    feed = F.Feed(feed.data)
    feed.attach_atv(atv)
    if ext:
        feed.attach_ext(ext)
    names = set()
    for it in feed.items:
        if it.get("type") != "script":
            names |= set(feed.outdated(it, installed))
    return len(names)


def recent_crashes(days=7):
    """(count, last plugin name) of enigma2 crash logs from the last days."""
    import glob
    import re
    files = []
    for pat in ("/home/root/logs/*crash*.log", "/media/hdd/*crash*.log", "/media/usb/*crash*.log"):
        files += glob.glob(pat)
    now = time.time()
    files = sorted([f for f in files if now - os.path.getmtime(f) < days * 86400], key=os.path.getmtime)
    plugin = ""
    if files:
        try:
            with open(files[-1], errors="replace") as fh:
                found = re.findall(r"/Plugins/(?:Extensions|SystemPlugins)/(\w+)", fh.read())
            plugin = found[-1] if found else ""
        except (IOError, OSError):
            pass
    return len(files), plugin


def local_checks():
    """Quick checks without network: [(level, text, action)]."""
    out = []
    t = S.cpu_temp()
    if t and t >= 85:
        out.append(("red", u"Température %d °C : trop chaude" % t, "fix"))
    elif t and t >= 75:
        out.append(("amber", u"Température %d °C : chaude" % t, "fix"))
    n, plug = recent_crashes()
    if n:
        out.append(("amber", u"%d plantage(s) récent(s)%s  ·  OK : Fixo" % (n, (u" (%s)" % plug) if plug else ""), "doctor"))
    free = F.free_bytes("/")
    if 0 <= free < 50 * 1024 * 1024:
        out.append(("red", u"Système presque plein : %s libres" % S.human(free), "fix"))
    if time.localtime().tm_year < 2024:
        out.append(("red", u"Heure fausse  ·  OK pour corriger", "fix"))
    if (os.path.exists("/run/opkg.lock") or os.path.exists("/var/lib/opkg/lock")) and not os.system("pidof opkg >/dev/null 2>&1") == 0:
        out.append(("amber", u"opkg bloqué  ·  OK pour réparer", "fix"))
    epg = S.setting("config.misc.epgcache_filename") or "/etc/enigma2/epg.dat"
    if not os.path.exists(epg) or os.path.getsize(epg) < 1024:
        out.append(("amber", u"EPG vide  ·  OK pour vérifier", "fix"))
    cam = S.softcam()
    if cam.endswith(u"(arrêté)"):
        out.append(("amber", u"Softcam %s arrêté  ·  OK pour Softcam Fix" % cam.split()[0], "run:softcamfix"))
    out += G.alerts()
    return out


class WacayoubHome(Screen):
    def __init__(self, session):
        Screen.__init__(self, session)
        self.skin = self._skin()
        self.setTitle("Wacayoub Panel")
        self.closed = False
        self.model, self.model_name = IM.box_model()
        self.archs = F.supported_archs()
        self.updates = None
        self.net = None  # None = test running, else (internet ok, dns ok)
        self.alerts = []
        self.row, self.col = 0, 0  # row -1 = alerts, 0..1 = tiles
        self.console = AsyncConsole()
        self.timer = eTimer()
        self.timer.callback.append(self._tick)
        self.slow = eTimer()
        self.slow.callback.append(self._slow_checks)
        for k in ("clock", "sub", "hello", "line2", "line3"):
            self[k] = Label("")
        for k in ("temp", "cpu", "ram", "disk"):
            self["ring_" + k] = Pixmap()
            self["pct_" + k] = Label("")
            self["lab_" + k] = Label({"temp": u"Température", "cpu": "CPU", "ram": "RAM", "disk": "Stockage"}[k])
        for i in range(2):
            self["a%d_bg" % i] = Pixmap()
            self["a%d" % i] = Label("")
        for i in range(3):
            self["s%d_bg" % i] = Pixmap()
            self["s%d" % i] = Label("")
        self["sel_tile"] = Pixmap()
        self["sel_alert"] = Pixmap()
        self["actions"] = ActionMap(["OkCancelActions", "ColorActions", "DirectionActions", "MenuActions"], {
            "ok": self.keyOk, "cancel": self.close, "red": self.keyRed, "green": self.keyGreen,
            "yellow": self.refresh, "blue": self.keyBlue, "menu": self.keyMenu,
            "left": self.keyLeft, "right": self.keyRight, "up": self.keyUp, "down": self.keyDown,
        }, -1)
        self.onLayoutFinish.append(self._start)
        self.onClose.append(self._on_close)

    @staticmethod
    def _skin():
        d = {"W": s(1920), "H": s(1080), "img": IMG}
        widgets = []

        def lab(name, x, y, w, h, f, col="#00F1F5F9", extra=""):
            widgets.append('<widget name="%s" position="%d,%d" size="%d,%d" font="Regular;%d" foregroundColor="%s" '
                           'backgroundColor="#00070B14" transparent="1" valign="center" %s/>' % (name, s(x), s(y), s(w), s(h), s(f), col, extra))

        def pixw(name, x, y, w, h, z=1):
            widgets.append('<widget name="%s" position="%d,%d" size="%d,%d" alphatest="blend" scale="1" zPosition="%d" />'
                           % (name, s(x), s(y), s(w), s(h), z))

        lab("clock", 1100, 36, 772, 50, 30, "#008C9AB0", 'halign="right"')
        lab("sub", 134, 92, 1200, 38, 24, "#007DD3FC")
        lab("hello", 90, 172, 860, 70, 48)
        lab("line2", 90, 250, 880, 42, 26, "#008C9AB0")
        lab("line3", 90, 300, 880, 42, 26, "#008C9AB0")
        for i, k in enumerate(("temp", "cpu", "ram", "disk")):
            cx = 1035 + i * 225
            pixw("ring_" + k, cx - 75, 205, 150, 150)
            lab("pct_" + k, cx - 75, 255, 150, 50, 34, "#00FFFFFF", 'halign="center" zPosition="2"')
            lab("lab_" + k, cx - 100, 368, 200, 36, 22, "#008C9AB0", 'halign="center"')
        for i in range(2):
            x = 48 + i * 927
            pixw("a%d_bg" % i, x, 474, 897, 78)
            lab("a%d" % i, x + 28, 474, 850, 78, 27, "#00F8FAFC", 'zPosition="2"')
        for i in range(3):
            x = 48 + i * 621
            pixw("s%d_bg" % i, x, 573, 582, 78)
            lab("s%d" % i, x + 28, 573, 540, 78, 26, "#00F8FAFC", 'zPosition="2"')
        pixw("sel_tile", 48, 675, 438, 138, 3)
        pixw("sel_alert", 48, 474, 897, 78, 3)
        return ('<screen name="WacayoubHome" position="0,0" size="%(W)d,%(H)d" flags="wfNoBorder" backgroundColor="#00070B14" title="Wacayoub Panel">'
                '<ePixmap position="0,0" size="%(W)d,%(H)d" pixmap="%(img)s/bg-home.jpg" scale="1" zPosition="-2" />' % d
                + "".join(widgets) + "</screen>")

    def _start(self):
        S.cpu_percent()
        for k in ("sel_tile", "sel_alert"):
            png = pix("hsel-tile.png" if k == "sel_tile" else "hsel-alert.png")
            if png and self[k].instance:
                self[k].instance.setPixmap(png)
        self.refresh()
        self.timer.start(2000, False)

    def _on_close(self):
        self.closed = True
        self.timer.stop()
        self.slow.stop()
        self.console.killAll()

    # ------------------------------------------------------------ data
    def refresh(self):
        h = time.localtime().tm_hour
        self["hello"].setText(u"Bonjour" if 5 <= h < 18 else u"Bonsoir")
        self["line2"].setText(u"%s  ·  %s  ·  allumé depuis %s" % (self.model_name or self.model or "?", S.image_version().split(" (build")[0], S.uptime_text()))
        net = S.network()
        tn = len(S.tuners())
        self["line3"].setText(u"%s  ·  %d tuner%s  ·  Softcam : %s" % (
            "  ".join("%s %s" % n for n in net[:1]) or u"pas de réseau", tn, "s" if tn > 1 else "", S.softcam()))
        self["sub"].setText(u"Accueil  ·  v%s  ·  vérification…" % VERSION)
        self.net = None
        self._render()
        self._tick()
        self.console.ePopen("ping -c1 -W3 1.1.1.1 >/dev/null 2>&1 && echo NET; nslookup github.com >/dev/null 2>&1 && echo DNS",
                            self._net_done)
        self.slow.start(300, True)  # after the screen is drawn: reading the package lists takes a moment

    def _slow_checks(self):
        if getattr(self, "closed", True):  # enigma2 clears attributes of closed screens
            return
        try:
            self.updates = count_updates(self.model, self.archs)
        except Exception as e:
            print("[WacayoubPanel] home updates: %s" % e)
            self.updates = None
        self._render()

    def _net_done(self, data, retval, extra=None):
        if getattr(self, "closed", True):
            return
        out = data.decode("utf-8", "replace") if isinstance(data, bytes) else (data or "")
        self.net = ("NET" in out, "DNS" in out)
        self._render()

    def _render(self):
        alerts = local_checks()
        if self.net is not None:
            if not self.net[0]:
                alerts.append(("red", u"Pas d'Internet  ·  OK pour tester", "fix"))
            elif not self.net[1]:
                alerts.append(("amber", u"DNS en panne  ·  OK pour changer", "dns"))
        if self.updates:
            alerts.append(("blue", u"%d mise(s) à jour  ·  BLEU pour tout" % self.updates, "update"))
        alerts.sort(key=lambda a: LEVEL_ORDER[a[0]])
        problems = [a for a in alerts if a[0] in ("red", "amber")]
        if not alerts:
            alerts = [("green", u"Tout va bien", None), ("green", u"Aucune mise à jour" if self.updates == 0 else u"Mises à jour : calcul…", None)]
        elif len(alerts) == 1:
            alerts.append(("green", u"Aucune mise à jour" if self.updates == 0 else u"Rien d'autre à signaler", None))
        self.alerts = alerts[:2]
        for i, (lvl, text, _a) in enumerate(self.alerts):
            png = pix("ha-%s.png" % lvl)
            if png and self["a%d_bg" % i].instance:
                self["a%d_bg" % i].instance.setPixmap(png)
            self["a%d" % i].setText(text)
        extra = len(alerts) - 2
        if extra > 0:
            self["a1"].setText(self.alerts[1][1] + u"   (+%d)" % extra)
        # status row
        if self.net is None:
            net = ("gray", u"Internet : test…")
        elif self.net[0] and self.net[1]:
            net = ("green", u"Internet et DNS OK")
        else:
            net = ("red", u"Internet : problème")
        cam = S.softcam()
        status = [("green", u"Santé : tout va bien") if not problems else ("amber", u"Santé : %d à vérifier" % len(problems)),
                  net, ("amber" if cam.endswith(u"(arrêté)") else "green", u"Softcam : %s" % cam)]
        for i, (lvl, text) in enumerate(status):
            png = pix("hs-%s.png" % lvl)
            if png and self["s%d_bg" % i].instance:
                self["s%d_bg" % i].instance.setPixmap(png)
            self["s%d" % i].setText(text)
        if self.net is not None and self.updates is not None:
            self["sub"].setText(u"Accueil  ·  v%s  ·  vérifié à %s" % (VERSION, time.strftime("%H:%M")))
        if self.row == -1 and not self._alert_actionable():
            self.row = 0
        self._move_sel()

    def _alert_actionable(self):
        return [i for i, a in enumerate(self.alerts) if a[2]]

    def _tick(self):
        if getattr(self, "closed", True):
            return
        self["clock"].setText(time.strftime(u"%d/%m/%Y   %H:%M"))
        temp = S.cpu_temp()
        rp = S.ram()[0]
        dp = S.storage("/")[0]
        for key, pct, txt in (("temp", S.temp_step(temp), (u"%d°" % temp) if temp else u"–"), ("cpu", S.cpu_percent(), None),
                              ("ram", rp, None), ("disk", dp, None)):
            png = pix(S.ring_step(pct))
            if png and self["ring_" + key].instance:
                self["ring_" + key].instance.setPixmap(png)
            self["pct_" + key].setText(txt if txt else "%d%%" % pct)

    # ------------------------------------------------------------ keys
    def _move_sel(self):
        from enigma import ePoint
        if self.row == -1:
            self["sel_tile"].hide()
            self["sel_alert"].show()
            if self["sel_alert"].instance:
                self["sel_alert"].instance.move(ePoint(s(48 + self.col * 927), s(474)))
        else:
            self["sel_alert"].hide()
            self["sel_tile"].show()
            if self["sel_tile"].instance:
                self["sel_tile"].instance.move(ePoint(s(48 + self.col * 462), s(675 + self.row * 162)))

    def keyLeft(self):
        cols = 2 if self.row == -1 else 4
        self.col = (self.col - 1) % cols
        if self.row == -1 and self.col not in self._alert_actionable():
            self.col = self._alert_actionable()[0]
        self._move_sel()

    def keyRight(self):
        cols = 2 if self.row == -1 else 4
        self.col = (self.col + 1) % cols
        if self.row == -1 and self.col not in self._alert_actionable():
            self.col = self._alert_actionable()[0]
        self._move_sel()

    def keyUp(self):
        if self.row == 1:
            self.row = 0
        elif self.row == 0 and self._alert_actionable():
            self.row = -1
            ok = self._alert_actionable()
            self.col = (1 if self.col >= 2 else 0) if (1 if self.col >= 2 else 0) in ok else ok[0]
        self._move_sel()

    def keyDown(self):
        if self.row == -1:
            self.row, self.col = 0, self.col * 2
        elif self.row == 0:
            self.row = 1
        self._move_sel()

    def keyOk(self):
        if self.row == -1:
            act = self.alerts[self.col][2] if self.col < len(self.alerts) else None
            if act == "update":
                return self._open(None, "update")
            if act == "doctor":
                return self.session.openWithCallback(self._back, WacayoubDoctor)
            if act and act.startswith("run:"):
                return self._open("scripts", act)
            if act:
                return self._open(act)
            return
        self._open(HOME_TILES[self.row * 4 + self.col][1])

    def keyRed(self):
        self.session.openWithCallback(self._back, WacayoubDoctor)

    def keyGreen(self):
        self._open("fix", "run:t-bilan-sante")

    def keyBlue(self):
        self._open(None, "update")

    def keyMenu(self):
        self._open(None, "search")

    def _open(self, cat, action=None):
        self.session.openWithCallback(self._back, WacayoubPanel, cat, action)

    def _back(self, *args):
        if not getattr(self, "closed", True):
            self.refresh()


# ---------------------------------------------------------------- Fixo (crash logs -> fixes)
class WacayoubDoctor(Screen):
    def __init__(self, session):
        Screen.__init__(self, session)
        self.skin = self._skin()
        self.setTitle("Fixo")
        self.closed = False
        self.feed = None
        self.findings = []
        self.busy = False
        self.console = AsyncConsole()
        self.later = eTimer()
        self.later.callback.append(self._analyse)
        self["title"] = Label(u"Fixo  ·  réparation intelligente")
        self["status"] = Label("")
        self["sub"] = Label("")
        self["summary"] = Label("")
        self["items"] = _List(80, [("Regular", 28), ("Regular", 22)])
        self["desc"] = Label("")
        self["key_red"] = Label(u"Archiver tout")
        self["key_green"] = Label(u"Réparer")
        self["key_yellow"] = Label(u"Analyser")
        self["key_blue"] = Label(u"Voir le rapport")
        self["actions"] = ActionMap(["OkCancelActions", "ColorActions", "DirectionActions"], {
            "ok": self.keyFix, "green": self.keyFix, "cancel": self.close, "red": self.keyArchiveAll,
            "yellow": self.start, "blue": self.keyShow,
            "up": self.keyUp, "down": self.keyDown, "left": self.keyPageUp, "right": self.keyPageDown,
        }, -1)
        self.onLayoutFinish.append(self._first)
        self.onClose.append(self._on_close)

    @staticmethod
    def _skin():
        d = {"W": s(1920), "H": s(1080), "img": IMG}
        for k, v in {"lx": 48, "ly": 38, "lw": 64, "tx": 132, "ty": 30, "tw": 900, "th": 54, "tf": 44, "sty": 86, "sth": 34, "stf": 24,
                     "subx": 1020, "subw": 852, "subf": 23, "bx": 188, "by": 170, "bw": 160, "mx": 70, "my": 350, "mw": 400, "mh": 430, "mf": 25,
                     "ix": 520, "iy": 150, "iw": 1340, "ih": 640, "dx": 72, "dy": 832, "dw": 1776, "dh": 124, "df": 24,
                     "fy": 996, "fd": 26, "fty": 988, "fth": 42, "ff": 25, "k1": 62, "k2": 392, "k3": 742, "k4": 1062}.items():
            d[k] = s(v)
        for i in range(1, 5):
            d["l%d" % i] = d["k%d" % i] + s(38)
        d["kw"] = s(300)
        return """
        <screen name="WacayoubDoctor" position="0,0" size="%(W)d,%(H)d" flags="wfNoBorder" backgroundColor="#00070B14" title="Fixo">
          <ePixmap position="0,0" size="%(W)d,%(H)d" pixmap="%(img)s/bg.jpg" scale="1" zPosition="-2" />
          <ePixmap position="%(lx)d,%(ly)d" size="%(lw)d,%(lw)d" pixmap="%(img)s/logo.png" alphatest="blend" scale="1" />
          <ePixmap position="%(bx)d,%(by)d" size="%(bw)d,%(bw)d" pixmap="%(img)s/B-doctor.png" alphatest="blend" scale="1" />
          <widget name="title" position="%(tx)d,%(ty)d" size="%(tw)d,%(th)d" font="Regular;%(tf)d" foregroundColor="#00F1F5F9" backgroundColor="#00070B14" transparent="1" valign="center" />
          <widget name="status" position="%(tx)d,%(sty)d" size="%(tw)d,%(sth)d" font="Regular;%(stf)d" foregroundColor="#007DD3FC" backgroundColor="#00070B14" transparent="1" valign="center" />
          <widget name="sub" position="%(subx)d,%(ty)d" size="%(subw)d,%(th)d" font="Regular;%(subf)d" foregroundColor="#008C9AB0" backgroundColor="#00070B14" transparent="1" halign="right" valign="center" />
          <widget name="summary" position="%(mx)d,%(my)d" size="%(mw)d,%(mh)d" font="Regular;%(mf)d" foregroundColor="#00CBD5E1" backgroundColor="#00070B14" transparent="1" halign="center" />
          <widget name="items" position="%(ix)d,%(iy)d" size="%(iw)d,%(ih)d" backgroundColor="#00070B14" transparent="1" foregroundColor="#00F1F5F9" foregroundColorSelected="#00FFFFFF" selectionPixmap="%(img)s/sel-item.png" scrollbarMode="showOnDemand" scrollbarWidth="4" scrollbarForegroundColor="#003B82F6" enableWrapAround="1" />
          <widget name="desc" position="%(dx)d,%(dy)d" size="%(dw)d,%(dh)d" font="Regular;%(df)d" foregroundColor="#00CBD5E1" backgroundColor="#00070B14" transparent="1" />
          <ePixmap position="%(k1)d,%(fy)d" size="%(fd)d,%(fd)d" pixmap="%(img)s/k-red.png" alphatest="blend" scale="1" />
          <ePixmap position="%(k2)d,%(fy)d" size="%(fd)d,%(fd)d" pixmap="%(img)s/k-green.png" alphatest="blend" scale="1" />
          <ePixmap position="%(k3)d,%(fy)d" size="%(fd)d,%(fd)d" pixmap="%(img)s/k-yellow.png" alphatest="blend" scale="1" />
          <ePixmap position="%(k4)d,%(fy)d" size="%(fd)d,%(fd)d" pixmap="%(img)s/k-blue.png" alphatest="blend" scale="1" />
          <widget name="key_red" position="%(l1)d,%(fty)d" size="%(kw)d,%(fth)d" font="Regular;%(ff)d" foregroundColor="#00E2E8F0" backgroundColor="#00070B14" transparent="1" valign="center" />
          <widget name="key_green" position="%(l2)d,%(fty)d" size="%(kw)d,%(fth)d" font="Regular;%(ff)d" foregroundColor="#00E2E8F0" backgroundColor="#00070B14" transparent="1" valign="center" />
          <widget name="key_yellow" position="%(l3)d,%(fty)d" size="%(kw)d,%(fth)d" font="Regular;%(ff)d" foregroundColor="#00E2E8F0" backgroundColor="#00070B14" transparent="1" valign="center" />
          <widget name="key_blue" position="%(l4)d,%(fty)d" size="%(kw)d,%(fth)d" font="Regular;%(ff)d" foregroundColor="#00E2E8F0" backgroundColor="#00070B14" transparent="1" valign="center" />
        </screen>""" % d

    def _first(self):
        self["items"].selectionEnabled(True)
        model, name = IM.box_model()
        self["sub"].setText(u"%s  ·  v%s" % (name or model or "?", VERSION))
        self.start()

    def _on_close(self):
        self.closed = True
        self.later.stop()
        self.console.killAll()

    def start(self):
        """Internet first: package lists (newer versions) and the panel feed (online rules), then the analysis."""
        if self.busy:
            return
        self.busy = True
        self["status"].setText(u"Connexion aux feeds (Internet)…")
        self["summary"].setText(u"Analyse en cours…")
        tmp = "/tmp/wacayoubpanel-doctor-index.json"
        self.console.ePopen("opkg update >/dev/null 2>&1; " + F.index_fetch_command(tmp), self._online_done, tmp)

    def _online_done(self, data, retval, tmp):
        if getattr(self, "closed", True):  # enigma2 clears attributes of closed screens
            return
        self.online = False
        try:
            if retval != 0:
                raise IOError("wget %s" % retval)
            fresh = F.Feed.load(tmp)
            if not os.path.isdir(F.CACHE_DIR):
                os.makedirs(F.CACHE_DIR)
            with open(F.CACHE_FILE, "w", encoding="utf-8") as fh:
                json.dump(fresh.data, fh, ensure_ascii=False)
            self.online = True
        except Exception as e:
            print("[WacayoubPanel] doctor online: %s" % e)
        try:
            os.remove(tmp)
        except OSError:
            pass
        self["status"].setText(u"Analyse des rapports de plantage…")
        self.later.start(50, True)

    def _analyse(self):
        if getattr(self, "closed", True):
            return
        try:
            self.feed = F.Feed.load(F.CACHE_FILE)
        except Exception:
            self.feed = None
        data = self.feed.data if self.feed else {}
        own = dict((k, v.get("version", "")) for k, v in data.get("packages", {}).items())
        try:
            self.findings = D.analyse(data, own)
        except Exception as e:
            print("[WacayoubPanel] doctor: %s" % e)
            self.findings = []
        self.busy = False
        nlogs = sum(f["count"] for f in self.findings)
        todo = [f for f in self.findings if f["level"] in ("red", "amber")]
        rules = len(data.get("doctor_rules", []))
        self["status"].setText((u"Feeds et règles en ligne à jour (%d règles Internet)" % rules) if self.online
                               else u"Hors ligne : listes et règles en cache")
        if not self.findings:
            self["summary"].setText(u"Aucun plantage enregistré.\n\nEnigma2 va bien.")
        else:
            self["summary"].setText(u"%d rapport(s) analysé(s)\n%d problème(s) trouvé(s)\n%d à réparer\n\nVERT : réparer la ligne choisie\n"
                                    u"Chaque réparation est confirmée avant de s'exécuter." % (nlogs, len(self.findings), len(todo)))
        self._build()

    def _build(self):
        rows = []
        dot = {"red": "k-red.png", "amber": "k-yellow.png", "blue": "k-blue.png", "green": "k-green.png"}
        col = {"red": 0xF87171, "amber": 0xFBBF24, "blue": 0x60A5FA, "green": 0x4ADE80}
        for f in self.findings:
            row = [f]
            tile = pix("t-i-%s.png" % (f.get("plugin") or "").lower()) or pix("t-doctor.png")
            if tile:
                row.append(MultiContentEntryPixmapAlphaBlend(pos=(s(16), s(10)), size=(s(60), s(60)), png=tile, flags=PIX_FLAGS))
            row.append(MultiContentEntryText(pos=(s(94), s(6)), size=(s(780), s(40)), font=0, flags=RT_HALIGN_LEFT | RT_VALIGN_CENTER,
                                             text=f["title"], color=C_TEXT, color_sel=0xFFFFFF))
            meta = [x for x in ((u"%d %s(s)" % (f["count"], u"blocage" if f["id"] == "gel" else u"plantage")) if f["count"] else "", f.get("date", ""), f.get("plugin") or "") if x]
            row.append(MultiContentEntryText(pos=(s(94), s(44)), size=(s(780), s(30)), font=1, flags=RT_HALIGN_LEFT | RT_VALIGN_CENTER,
                                             text=u"  ·  ".join(meta), color=C_DIM, color_sel=0xDBEAFE))
            row.append(MultiContentEntryText(pos=(s(880), s(8)), size=(s(400), s(64)), font=1, flags=RT_HALIGN_RIGHT | RT_VALIGN_CENTER,
                                             text=f["fix_label"], color=col.get(f["level"], C_DIM), color_sel=0xFFFFFF))
            if pix(dot.get(f["level"], "k-menu.png")):
                row.append(MultiContentEntryPixmapAlphaBlend(pos=(s(1290), s(27)), size=(s(26), s(26)), png=pix(dot[f["level"]]), flags=PIX_FLAGS))
            rows.append(row)
        self["items"].setList(rows)
        self._desc()

    def _cur(self):
        c = self["items"].getCurrent()
        return c[0] if c else None

    def _desc(self):
        f = self._cur()
        if not f:
            self["desc"].setText(u"Fixo lit les rapports de plantage d'Enigma2, cherche la cause et propose une réparation "
                                 u"(feeds OpenATV et Wacayoub, règles en ligne). JAUNE : analyser à nouveau.")
            return
        txt = f.get("explain", "")
        if f.get("exception"):
            txt += u"\nErreur : %s%s" % (f["exception"][:150], (u"  (%s)" % f["where"]) if f.get("where") else "")
        self["desc"].setText(txt)

    def keyUp(self):
        self["items"].up()
        self._desc()

    def keyDown(self):
        self["items"].down()
        self._desc()

    def keyPageUp(self):
        self["items"].pageUp()
        self._desc()

    def keyPageDown(self):
        self["items"].pageDown()
        self._desc()

    # ------------------------------------------------------------ actions
    def keyFix(self):
        f = self._cur()
        if not f or self.busy:
            return
        if f["fix"]["type"] in ("accept", "source"):
            return self._garde_fix(f)
        if f["fix"]["type"] == "archive":
            body = self._archive_body(f["logs"])
            q = u"%s\n\nArchiver %d rapport(s) ? (déplacés dans %s)" % (f["title"], len(f["logs"]), D.ARCHIVE)
        else:
            body = D.fix_commands(f, F.Feed(self.feed.data) if self.feed else None)
            q = u"%s\n\nRéparation : %s\n%s" % (f["title"], f["fix_label"],
                                                 u"L'interface redémarrera ensuite." if D.needs_restart(f) else u"")
        if not body:
            self.session.open(MessageBox, u"Réparation indisponible hors ligne. JAUNE pour réessayer.", MessageBox.TYPE_ERROR, timeout=6)
            return

        def go(ok):
            if ok:
                cmd = F.write_run_script(body, "doctor.sh")
                self.session.openWithCallback(lambda *a: self._done(f), Console, title=u"Fixo : %s" % f["fix_label"], cmdlist=cmd)
        self.session.openWithCallback(go, MessageBox, q, MessageBox.TYPE_YESNO)

    def _garde_fix(self, f):
        fx = f["fix"]
        if fx["type"] == "accept":
            choices = [(u"Oui, c'est moi : accepter ce changement", "accept"), (u"Non, laisser l'alerte", None)]
        else:
            choices = [(u"Désactiver cette source (conseillé)", "off"), (u"La garder : je lui fais confiance", "keep"), (u"Annuler", None)]

        def go(c):
            if not c or not c[1] or getattr(self, "closed", True):
                return
            try:
                if c[1] == "accept":
                    G.accept(fx["paths"])
                elif c[1] == "off":
                    G.source_off(fx["conf"], fx["url"])
                else:
                    G.keep_source(fx["url"])
            except Exception as e:
                self.session.open(MessageBox, u"Impossible : %s" % e, MessageBox.TYPE_ERROR, timeout=8)
            self.start()
        self.session.openWithCallback(go, ChoiceBox, title=f["title"], list=choices)

    def _done(self, f):
        if getattr(self, "closed", True):
            return
        if f["fix"]["type"] != "archive" and D.needs_restart(f):
            def restart(ok):
                if ok:
                    self.session.open(TryQuitMainloop, 3)
                else:
                    self.start()
            self.session.openWithCallback(restart, MessageBox, u"Redémarrer l'interface maintenant pour appliquer la réparation ?",
                                          MessageBox.TYPE_YESNO)
            return
        self.start()

    @staticmethod
    def _archive_body(paths):
        q = " ".join(D.sh(p) for p in paths)
        return ("mkdir -p %s && mv -f %s %s/ && echo '>>> %d rapport(s) archivé(s) dans %s'\n"
                % (D.sh(D.ARCHIVE), q, D.sh(D.ARCHIVE), len(paths), D.ARCHIVE))

    def keyArchiveAll(self):
        paths = [p for f in self.findings for p in f.get("logs", [])]
        if not paths or self.busy:
            return

        def go(ok):
            if ok:
                self.session.openWithCallback(lambda *a: self.start(), Console, title=u"Archiver les rapports",
                                              cmdlist=F.write_run_script(self._archive_body(paths), "doctor.sh"))
        self.session.openWithCallback(go, MessageBox, u"Archiver les %d rapports de plantage ?\nIls sont gardés dans %s." % (len(paths), D.ARCHIVE),
                                      MessageBox.TYPE_YESNO)

    def keyShow(self):
        f = self._cur()
        if f and f.get("garde") and f.get("show"):
            p = D.sh(f["show"])
            body = "ls -l %s 2>&1; echo; head -c 4000 %s 2>/dev/null | head -60 | cut -c1-160\n" % (p, p)
            return self.session.open(Console, title=f["title"][:60], cmdlist=F.write_run_script(body, "doctor-show.sh"))
        if not f or not f.get("logs"):
            return
        path = f["logs"][0]
        body = ("echo %s; grep -E '^(crashdate|skin|imageversion)=' %s; echo; sed -n '/Traceback/,$p' %s | grep -v '^<' | head -60\n"
                % (D.sh(os.path.basename(path)), D.sh(path), D.sh(path)))
        self.session.open(Console, title=u"Rapport de plantage", cmdlist=F.write_run_script(body, "doctor-show.sh"))


# ---------------------------------------------------------------- Partage LAN (P2P between two receivers)
P2P_PY = os.path.join(PLUGIN_DIR, "p2p.py")
P2P_WHAT = [(u"Tout : chaînes, IPTV et softcam", "chaines,iptv,softcam"), (u"Chaînes satellite + IPTV", "chaines,iptv"),
            (u"Chaînes satellite seulement", "chaines"), (u"IPTV seulement (bouquets + réglages des plugins IPTV)", "iptv"),
            (u"Softcam seulement (configs et clés)", "softcam")]
P2P_KIND = {"chaines": u"chaînes", "iptv": u"IPTV", "softcam": u"softcam"}


def p2p_what(counts, kinds):
    unit = {"chaines": u"bouquets de chaînes", "iptv": u"bouquets IPTV", "softcam": u"fichiers softcam"}
    return u", ".join(u"%d %s" % (counts.get(k, 0), unit.get(k, k)) for k in kinds)


def reload_channels():
    try:
        from enigma import eDVBDB
        db = eDVBDB.getInstance()
        db.reloadServicelist()
        db.reloadBouquets()
    except Exception as e:
        print("[WacayoubPanel] p2p reload: %s" % e)


class WacayoubP2P(Screen):
    def __init__(self, session):
        Screen.__init__(self, session)
        self.skin = WacayoubDoctor._skin().replace('name="WacayoubDoctor"', 'name="WacayoubP2P"').replace(
            'B-doctor.png', 'B-p2p.png').replace('title="Fixo"', 'title="Partage LAN"').replace(
            '<widget name="desc"', '<widget name="code" position="%d,%d" size="%d,%d" font="Regular;%d" foregroundColor="#00FBBF24" '
            'backgroundColor="#00070B14" transparent="1" halign="center" valign="center" />\n          <widget name="desc"'
            % (s(520), s(260), s(1340), s(200), s(120)))
        self.setTitle(u"Partage LAN")
        self.closed = False
        self.mode = "menu"
        self.rows = []
        self.proc = None
        self.peers = []
        self.console = AsyncConsole()
        self.poll = eTimer()
        self.poll.callback.append(self._poll)
        self["title"] = Label(u"Partage LAN  ·  entre deux récepteurs")
        self["status"] = Label(u"Même réseau (box Internet), aucun réglage à faire")
        self["sub"] = Label("")
        self["summary"] = Label("")
        self["items"] = _List(80, [("Regular", 28), ("Regular", 22)])
        self["code"] = Label("")
        self["desc"] = Label("")
        self["key_red"] = Label(u"Fermer")
        self["key_green"] = Label(u"Choisir")
        self["key_yellow"] = Label(u"Chercher")
        self["key_blue"] = Label("")
        self["actions"] = ActionMap(["OkCancelActions", "ColorActions", "DirectionActions"], {
            "ok": self.keyOk, "green": self.keyOk, "cancel": self.keyBack, "red": self.keyBack, "yellow": self.keyFind,
            "up": self.keyUp, "down": self.keyDown,
        }, -1)
        self.onLayoutFinish.append(self._first)
        self.onClose.append(self._on_close)

    def _first(self):
        self["items"].selectionEnabled(True)
        model, name = IM.box_model()
        self["sub"].setText(u"%s  ·  v%s" % (name or model or "?", VERSION))
        self._menu()

    def _on_close(self):
        self.closed = True
        self.poll.stop()
        self._stop_server()
        self.console.killAll()

    def _stop_server(self):
        if self.proc:
            try:
                self.proc.terminate()
            except Exception:
                pass
            self.proc = None

    # ------------------------------------------------------------ list
    def _set_rows(self, rows):
        """rows: [(key, title, subtitle, tile)]"""
        self.rows = rows
        out = []
        for r in rows:
            row = [r]
            if pix(r[3]):
                row.append(MultiContentEntryPixmapAlphaBlend(pos=(s(16), s(10)), size=(s(60), s(60)), png=pix(r[3]), flags=PIX_FLAGS))
            row.append(MultiContentEntryText(pos=(s(94), s(6)), size=(s(1220), s(40)), font=0, flags=RT_HALIGN_LEFT | RT_VALIGN_CENTER,
                                             text=r[1], color=C_TEXT, color_sel=0xFFFFFF))
            row.append(MultiContentEntryText(pos=(s(94), s(44)), size=(s(1220), s(30)), font=1, flags=RT_HALIGN_LEFT | RT_VALIGN_CENTER,
                                             text=r[2], color=C_DIM, color_sel=0xDBEAFE))
            out.append(row)
        self["items"].setList(out)

    def _cur(self):
        c = self["items"].getCurrent()
        return c[0] if c else None

    def keyUp(self):
        self["items"].up()

    def keyDown(self):
        self["items"].down()

    def _last_backup(self):
        try:
            names = sorted(d for d in os.listdir("/home/root/wacayoub-p2p") if d.startswith("echange-"))
            with open(os.path.join("/home/root/wacayoub-p2p", names[-1], "backup.json"), encoding="utf-8") as fh:
                return json.load(fh)
        except Exception:
            return None

    def _menu(self):
        self.mode = "menu"
        self._stop_server()
        self.poll.stop()
        self["code"].setText("")
        self["key_yellow"].setText(u"")
        self["key_green"].setText(u"Choisir")
        self["status"].setText(u"Même réseau (box Internet), aucun réglage à faire")
        rows = [("send", u"Envoyer depuis ce récepteur", u"Chaînes, IPTV, softcam : l'autre récepteur reçoit avec un code", "t-p2p.png"),
                ("recv", u"Recevoir sur ce récepteur", u"Cherche l'autre récepteur sur le réseau, puis demande son code", "t-p2p.png")]
        last = self._last_backup()
        if last:
            rows.append(("undo", u"Annuler le dernier échange reçu",
                         u"Reçu de %s le %s : %s" % (last.get("from", "?"), last.get("date", ""),
                                                      ", ".join(P2P_KIND.get(k, k) for k in last.get("kinds", []))), "t-fix.png"))
        self._set_rows(rows)
        self["summary"].setText(u"Copie les chaînes, l'IPTV et la softcam d'un récepteur à l'autre.\n\n"
                                u"1. Sur le premier : Envoyer\n2. Sur le second : Recevoir\n3. Taper le code affiché\n\n"
                                u"Ce qui est remplacé est gardé : on peut annuler.")
        self["desc"].setText(u"Fonctionne seulement sur le réseau de la maison. Transfert chiffré avec un code à 8 chiffres, "
                             u"valable 10 minutes, pour un seul envoi. 3 codes faux arrêtent l'envoi.")

    def keyBack(self):
        if self.mode == "menu":
            return self.close()
        self._menu()

    def keyOk(self):
        r = self._cur()
        if not r:
            return
        if self.mode == "menu":
            if r[0] == "send":
                self.session.openWithCallback(self._send_what, ChoiceBox, title=u"Quoi envoyer ?", list=P2P_WHAT)
            elif r[0] == "recv":
                self._receive()
            elif r[0] == "undo":
                self._undo()
        elif self.mode == "recv" and r[0] == "peer":
            self._ask_code(r[4])

    # ------------------------------------------------------------ send
    def _send_what(self, choice):
        if not choice or getattr(self, "closed", True):
            return
        import random
        import subprocess
        code = "%08d" % random.SystemRandom().randrange(10 ** 8)
        try:
            os.remove("/tmp/wacayoub-p2p/status.json")
        except OSError:
            pass
        env = dict(os.environ, WP2P_CODE=code)
        try:
            with open(os.devnull, "wb") as null:
                self.proc = subprocess.Popen(["python3", "-I", P2P_PY, "serve", choice[1]], env=env, stdin=null, stdout=null,
                                             stderr=null, close_fds=True)
        except Exception as e:
            self.session.open(MessageBox, u"Impossible de lancer l'envoi : %s" % e, MessageBox.TYPE_ERROR)
            return
        self.mode = "send"
        self.sent_what = choice[0]
        self["key_yellow"].setText("")
        self["key_green"].setText("")
        self._set_rows([])
        self["code"].setText(u"%s %s" % (code[:4], code[4:]))
        self["summary"].setText(u"Sur l'autre récepteur :\nWacayoub Panel\n→ Mon récepteur\n→ Partage LAN\n→ Recevoir\n\npuis taper ce code.")
        self["desc"].setText(u"Envoi : %s. Le code est valable 10 minutes et pour un seul envoi. EXIT : arrêter." % choice[0])
        self["status"].setText(u"Préparation…")
        self.poll.start(1000, False)

    def _poll(self):
        if getattr(self, "closed", True) or self.mode != "send":
            return
        try:
            with open("/tmp/wacayoub-p2p/status.json", encoding="utf-8") as fh:
                st = json.load(fh)
        except Exception:
            return
        state = st.get("state")
        counts = st.get("counts", {})
        what = p2p_what(counts, counts.keys())
        if state == "waiting":
            self["status"].setText(u"Prêt : %s  ·  en attente" % what)
            if st.get("wrong"):
                self["desc"].setText(u"Code faux reçu (%d/3). Vérifie le code tapé sur l'autre récepteur." % st["wrong"])
        elif state == "sending":
            self["status"].setText(st.get("text", ""))
        elif state in ("sent", "locked", "expired", "error"):
            self.poll.stop()
            self.proc = None
            self["code"].setText({"sent": u"Envoyé ✓", "locked": u"Arrêté", "expired": u"Expiré", "error": u"Erreur"}[state])
            self["status"].setText(st.get("text", ""))
            self["desc"].setText({"sent": u"L'autre récepteur a reçu %s. EXIT : retour." % what,
                                  "locked": u"3 codes faux : l'envoi est arrêté par sécurité. EXIT puis Envoyer pour un nouveau code.",
                                  "expired": u"Personne n'a reçu en 10 minutes. EXIT puis Envoyer pour un nouveau code.",
                                  "error": st.get("text", "")}[state])

    # ------------------------------------------------------------ receive
    def keyFind(self):
        if self.mode == "recv":
            self._receive()

    def _receive(self):
        self.mode = "recv"
        self.peers = []
        self["key_yellow"].setText(u"Chercher")
        self["code"].setText("")
        self._set_rows([])
        self["status"].setText(u"Recherche des récepteurs sur le réseau…")
        self["summary"].setText(u"Sur l'autre récepteur :\nPartage LAN → Envoyer\n\nIl apparaît ici, choisis-le puis tape son code.")
        self["desc"].setText(u"JAUNE : chercher à nouveau. EXIT : retour.")
        self.console.ePopen(["python3", "python3", "-I", P2P_PY, "find"], self._found)

    def _found(self, data, retval, extra=None):
        if getattr(self, "closed", True) or self.mode != "recv":
            return
        out = data.decode("utf-8", "replace") if isinstance(data, bytes) else (data or "")
        rows = []
        for line in out.splitlines():
            try:
                d = json.loads(line)
            except ValueError:
                continue
            counts = d.get("counts", {})
            what = p2p_what(counts, d.get("kinds", []))
            rows.append(("peer", u"%s  ·  %s" % (d.get("name", "?"), d.get("ip", "")), u"Envoie : %s" % what, "t-p2p.png", d))
        self._set_rows(rows)
        self["status"].setText(u"%d récepteur(s) prêt(s) à envoyer" % len(rows) if rows else
                               u"Aucun récepteur trouvé : sur l'autre, Partage LAN → Envoyer, puis JAUNE")

    def _ask_code(self, peer):
        from Screens.InputBox import InputBox
        from Components.Input import Input

        def got(code):
            code = (code or "").replace(" ", "")
            if not code or getattr(self, "closed", True):
                return
            if len(code) != 8 or not code.isdigit():
                self.session.open(MessageBox, u"Le code a 8 chiffres.", MessageBox.TYPE_ERROR, timeout=5)
                return
            kinds = u", ".join(P2P_KIND.get(k, k) for k in peer.get("kinds", []))
            q = (u"Recevoir %s depuis %s ?\n\n" % (kinds, peer.get("name", "?")) +
                 (u"Les chaînes satellite d'ici sont remplacées (tes bouquets IPTV restent).\n" if "chaines" in peer.get("kinds", []) else u"") +
                 u"Tout ce qui est remplacé est gardé : « Annuler le dernier échange » le remet.")

            def go(ok):
                if ok and not getattr(self, "closed", True):
                    body = ("export WP2P_CODE=%s\nrm -f \"$0\"\npython3 -I %s receive %s %d\n"
                            % (code, D.sh(P2P_PY), D.sh(peer["ip"]), int(peer.get("port", 47811))))
                    self.session.openWithCallback(self._after, Console, title=u"Partage LAN : réception",
                                                  cmdlist=F.write_run_script(body, "p2p-recv.sh"))
            self.session.openWithCallback(go, MessageBox, q, MessageBox.TYPE_YESNO)
        self.session.openWithCallback(got, InputBox, title=u"Code affiché sur %s (8 chiffres)" % peer.get("name", "?"),
                                      text=" " * 8, maxSize=True, type=Input.NUMBER)

    def _undo(self):
        def go(ok):
            if ok and not getattr(self, "closed", True):
                self.session.openWithCallback(self._after, Console, title=u"Partage LAN : annulation",
                                              cmdlist=F.write_run_script("python3 -I %s undo\n" % D.sh(P2P_PY), "p2p-undo.sh"))
        self.session.openWithCallback(go, MessageBox, u"Remettre les chaînes, l'IPTV et la softcam d'avant le dernier échange ?",
                                      MessageBox.TYPE_YESNO)

    def _after(self, *args):
        if getattr(self, "closed", True):
            return
        reload_channels()
        self._menu()


def main(session, **kwargs):
    session.open(WacayoubHome)


def start_garde(reason, **kwargs):
    """Starts garde-gel.sh (freeze watchdog) once per boot; it keeps itself to one copy."""
    if reason != 0:
        return
    try:
        import subprocess
        with open(os.devnull, "wb") as null:
            subprocess.Popen(["/bin/sh", os.path.join(PLUGIN_DIR, "garde-gel.sh")], stdin=null, stdout=null, stderr=null,
                             close_fds=True, start_new_session=True)
    except Exception as e:
        print("[WacayoubPanel] garde-gel: %s" % e)


def Plugins(**kwargs):
    return [
        PluginDescriptor(name="Wacayoub Panel", description="Installer et mettre à jour mes plugins, skins et scripts",
                         where=PluginDescriptor.WHERE_PLUGINMENU, icon="plugin.png", fnc=main),
        PluginDescriptor(name="Wacayoub Panel", description="Installer et mettre à jour mes plugins, skins et scripts",
                         where=PluginDescriptor.WHERE_EXTENSIONSMENU, fnc=main),
        PluginDescriptor(where=PluginDescriptor.WHERE_SESSIONSTART, fnc=start_garde),
    ]
