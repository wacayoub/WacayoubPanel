# -*- coding: utf-8 -*-
"""Detail card of one item: preview image, compatibility checks, versions, description.
OK/GREEN = main action, RED = remove, EXIT = back. Returns the chosen action to the panel."""
import hashlib
import os

from enigma import getDesktop
from Components.ActionMap import ActionMap
from Components.Console import Console as AsyncConsole
from Components.Label import Label
from Components.Pixmap import Pixmap
from Screens.Screen import Screen
from Tools.LoadPixmap import LoadPixmap

PREV_DIR = "/tmp/wacayoubpanel/prev"
_W = getDesktop(0).size().width() or 1920
SC = _W / 1920.0


def s(v):
    return int(round(v * SC))


def _skin(img):
    d = {"W": s(1920), "H": s(1080), "img": img}
    for k, v in {"px": 60, "py": 150, "pw": 1080, "ph": 608, "tx": 1180, "tw": 680, "ty": 150, "th": 60, "tf": 40,
                 "ky": 214, "kh": 34, "kf": 24, "sy": 256, "sh": 40, "sf": 28, "cy": 310, "ch": 190, "cf": 24,
                 "vy": 510, "vh": 120, "vf": 23, "dx": 60, "dy": 780, "dw": 1800, "dh": 190, "df": 25,
                 "fy": 996, "fd": 26, "fty": 988, "fth": 42, "ff": 25, "k1": 62, "k2": 392, "k3": 742,
                 "ix": 520, "iy": 334, "is": 160, "lx": 48, "ly": 38, "lw": 64, "hx": 132, "hy": 30, "hw": 1700, "hh": 54, "hf": 30}.items():
        d[k] = s(v)
    d["l1"], d["l2"], d["l3"] = d["k1"] + s(38), d["k2"] + s(38), d["k3"] + s(38)
    d["kw"] = s(300)
    return """
    <screen name="WacayoubDetails" position="0,0" size="%(W)d,%(H)d" flags="wfNoBorder" backgroundColor="#00070B14" title="Wacayoub Panel">
      <ePixmap position="0,0" size="%(W)d,%(H)d" pixmap="%(img)s/bg-detail.jpg" scale="1" zPosition="-2" />
      <ePixmap position="%(lx)d,%(ly)d" size="%(lw)d,%(lw)d" pixmap="%(img)s/logo.png" alphatest="blend" scale="1" />
      <widget name="crumb" position="%(hx)d,%(hy)d" size="%(hw)d,%(hh)d" font="Regular;%(hf)d" foregroundColor="#008C9AB0" backgroundColor="#00070B14" transparent="1" valign="center" />
      <widget name="preview" position="%(px)d,%(py)d" size="%(pw)d,%(ph)d" alphatest="on" scale="1" zPosition="1" />
      <widget name="bigicon" position="%(ix)d,%(iy)d" size="%(is)d,%(is)d" alphatest="blend" scale="1" zPosition="2" />
      <widget name="noprev" position="%(px)d,%(vy)d" size="%(pw)d,%(kh)d" font="Regular;%(kf)d" foregroundColor="#008C9AB0" backgroundColor="#00070B14" transparent="1" halign="center" zPosition="2" />
      <widget name="name" position="%(tx)d,%(ty)d" size="%(tw)d,%(th)d" font="Regular;%(tf)d" foregroundColor="#00F1F5F9" backgroundColor="#00070B14" transparent="1" valign="center" />
      <widget name="kind" position="%(tx)d,%(ky)d" size="%(tw)d,%(kh)d" font="Regular;%(kf)d" foregroundColor="#007DD3FC" backgroundColor="#00070B14" transparent="1" />
      <widget name="state" position="%(tx)d,%(sy)d" size="%(tw)d,%(sh)d" font="Regular;%(sf)d" foregroundColor="#004ADE80" backgroundColor="#00070B14" transparent="1" />
      <widget name="compat" position="%(tx)d,%(cy)d" size="%(tw)d,%(ch)d" font="Regular;%(cf)d" foregroundColor="#00CBD5E1" backgroundColor="#00070B14" transparent="1" />
      <widget name="versions" position="%(tx)d,%(vy)d" size="%(tw)d,%(vh)d" font="Regular;%(vf)d" foregroundColor="#008C9AB0" backgroundColor="#00070B14" transparent="1" />
      <widget name="desc" position="%(dx)d,%(dy)d" size="%(dw)d,%(dh)d" font="Regular;%(df)d" foregroundColor="#00E2E8F0" backgroundColor="#00070B14" transparent="1" />
      <ePixmap position="%(k1)d,%(fy)d" size="%(fd)d,%(fd)d" pixmap="%(img)s/k-green.png" alphatest="blend" scale="1" />
      <ePixmap position="%(k2)d,%(fy)d" size="%(fd)d,%(fd)d" pixmap="%(img)s/k-red.png" alphatest="blend" scale="1" />
      <ePixmap position="%(k3)d,%(fy)d" size="%(fd)d,%(fd)d" pixmap="%(img)s/k-menu.png" alphatest="blend" scale="1" />
      <widget name="key_green" position="%(l1)d,%(fty)d" size="%(kw)d,%(fth)d" font="Regular;%(ff)d" foregroundColor="#00E2E8F0" backgroundColor="#00070B14" transparent="1" valign="center" />
      <widget name="key_red" position="%(l2)d,%(fty)d" size="%(kw)d,%(fth)d" font="Regular;%(ff)d" foregroundColor="#00E2E8F0" backgroundColor="#00070B14" transparent="1" valign="center" />
      <widget name="key_exit" position="%(l3)d,%(fty)d" size="%(kw)d,%(fth)d" font="Regular;%(ff)d" foregroundColor="#00E2E8F0" backgroundColor="#00070B14" transparent="1" valign="center" />
    </screen>""" % d


class WacayoubDetails(Screen):
    def __init__(self, session, info):
        """info: name, crumb, kind, state_text, state_color, compat [(ok,label)], versions text,
        description, preview (url or ''), icon (path), green (label or ''), red (label or ''), img (dir)."""
        self.skin = _skin(info["img"])
        Screen.__init__(self, session)
        self.info = info
        self.console = AsyncConsole()
        self.closed = False
        self["crumb"] = Label(info.get("crumb", ""))
        self["name"] = Label(info.get("name", ""))
        self["kind"] = Label(info.get("kind", ""))
        self["state"] = Label(info.get("state_text", ""))
        lines = []
        for ok, label in info.get("compat", []):
            lines.append((u"✓  " if ok else u"✗  ") + label)
        self["compat"] = Label("\n".join(lines) or "")
        self["versions"] = Label(info.get("versions", ""))
        self["desc"] = Label(info.get("description", ""))
        self["preview"] = Pixmap()
        self["bigicon"] = Pixmap()
        self["noprev"] = Label("")
        self["key_green"] = Label(info.get("green", ""))
        self["key_red"] = Label(info.get("red", ""))
        self["key_exit"] = Label("EXIT  Retour")
        self["actions"] = ActionMap(["OkCancelActions", "ColorActions"], {
            "ok": self.keyGreen, "green": self.keyGreen, "red": self.keyRed, "cancel": self.keyExit,
        }, -1)
        self.onLayoutFinish.append(self._start)
        self.onClose.append(self._on_close)

    def _on_close(self):
        self.closed = True

    def _start(self):
        col = self.info.get("state_color")
        if col is not None:
            try:
                from enigma import gRGB
                self["state"].instance.setForegroundColor(gRGB(col))
            except Exception:
                pass
        url = self.info.get("preview")
        if url:
            name = hashlib.md5(url.encode("utf-8")).hexdigest() + ".jpg"
            path = os.path.join(PREV_DIR, name)
            if os.path.exists(path) and os.path.getsize(path) > 0:
                self._show(path)
            else:
                self["noprev"].setText(u"Chargement de l'aperçu…")
                self._icon()
                if not os.path.isdir(PREV_DIR):
                    os.makedirs(PREV_DIR)
                cmd = "wget -q -T 20 -O '%s.part' '%s' && mv '%s.part' '%s'" % (path, url.replace("'", ""), path, path)
                self.console.ePopen(cmd, self._got, path)
        else:
            self._icon()
            self["noprev"].setText(u"Pas d'aperçu pour ce paquet")

    def _icon(self):
        png = self.info.get("icon")
        if png and os.path.exists(png) and self["bigicon"].instance:
            self["bigicon"].instance.setPixmap(LoadPixmap(png, cached=True))
            self["bigicon"].show()

    def _got(self, data, retval, path):
        if self.closed:
            return
        if retval == 0 and os.path.exists(path):
            self._show(path)
        else:
            self["noprev"].setText(u"Aperçu indisponible (hors ligne ?)")

    def _show(self, path):
        pm = LoadPixmap(path)
        if pm and self["preview"].instance:
            self["bigicon"].hide()
            self["noprev"].setText("")
            self["preview"].instance.setPixmap(pm)

    def keyGreen(self):
        if self.info.get("green"):
            self.close("green")

    def keyRed(self):
        if self.info.get("red"):
            self.close("red")

    def keyExit(self):
        self.close(None)
