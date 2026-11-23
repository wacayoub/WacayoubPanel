# -*- coding: utf-8 -*-
# Wacayoub Chaînes - organise les chaînes : déplacer, supprimer, trier, ranger par thème. Icônes : Lucide (ISC).
import os
import re

from enigma import eListboxPythonMultiContent, eTimer, gFont, getDesktop, RT_HALIGN_LEFT, RT_HALIGN_RIGHT, RT_VALIGN_CENTER
from Components.ActionMap import ActionMap
from Components.Label import Label
from Components.MenuList import MenuList
from Components.MultiContent import MultiContentEntryPixmapAlphaBlend, MultiContentEntryText
from Plugins.Plugin import PluginDescriptor
from Screens.ChoiceBox import ChoiceBox
from Screens.MessageBox import MessageBox
from Screens.Screen import Screen
from Screens.VirtualKeyBoard import VirtualKeyBoard
from Tools.LoadPixmap import LoadPixmap

try:
    from enigma import BT_SCALE, BT_KEEP_ASPECT_RATIO
    PIX_FLAGS = BT_SCALE | BT_KEEP_ASPECT_RATIO
except ImportError:
    PIX_FLAGS = 0

from . import bouquets as B

VERSION = "1.0.0"
HERE = os.path.dirname(os.path.abspath(__file__))
IMG = os.path.join(HERE, "img")
SC = (getDesktop(0).size().width() or 1920) / 1920.0
PICON_MAX = 400      # bouquets bigger than this are shown without picons (speed)
C_TEXT, C_DIM, C_MARK, C_HEAD, C_DIRTY = 0xF1F5F9, 0x8C9AB0, 0xFBBF24, 0x7DD3FC, 0xFBBF24
CTRL = re.compile(u"[\u0080-\u009f]")


def s(v):
    return int(round(v * SC))


_PIX = {}


def pix(path):
    if path not in _PIX:
        _PIX[path] = LoadPixmap(path, cached=True) if path and os.path.exists(path) else None
    return _PIX[path]


def img(name):
    return pix(os.path.join(IMG, name))


class _List(MenuList):
    def __init__(self, item_h, fonts):
        MenuList.__init__(self, [], False, eListboxPythonMultiContent)
        for i, (name, size) in enumerate(fonts):
            self.l.setFont(i, gFont(name, s(size)))
        self.l.setItemHeight(s(item_h))


class Picons(object):
    """name -> path, from the usual picon folders (only mounted disks, never waking up a network share)."""

    def __init__(self):
        self.index = None

    def _build(self):
        self.index = {}
        dirs = ["/usr/share/enigma2/picon", "/picon", "/data/picon"]
        try:
            with open("/proc/mounts") as fh:
                for line in fh:
                    mp = line.split()[1]
                    if mp.startswith("/media/") and mp not in ("/media/autofs", "/media/net"):
                        dirs.append(mp + "/picon")
        except (IOError, OSError):
            pass
        for d in reversed(dirs):
            try:
                for fn in os.listdir(d):
                    if fn.endswith(".png"):
                        self.index[fn[:-4].upper()] = os.path.join(d, fn)
            except OSError:
                pass

    def get(self, entry):
        if self.index is None:
            self._build()
        if not self.index:
            return None
        for n in entry.picon_names():
            if n in self.index:
                return pix(self.index[n])
        return None


def clean(text):
    return CTRL.sub(u"", text or u"")


class WacayoubChaines(Screen):
    def __init__(self, session):
        Screen.__init__(self, session)
        self.skin = self._skin()
        self.setTitle(u"Wacayoub Chaînes")
        self.lib = None
        self.kind = "tv"
        self.focus = "left"
        self.marked = set()
        self.move = None          # None, "chan" (block of indexes) or "bouquet"
        self.block = []
        self.bqs = []
        self.rows = []
        self.picons = Picons()
        self["title"] = Label(u"Wacayoub Chaînes")
        self["status"] = Label(u"Chargement des chaînes…")
        self["sub"] = Label(u"v%s" % VERSION)
        self["bouquets"] = _List(52, [("Regular", 24), ("Regular", 20)])
        self["chans"] = _List(80, [("Regular", 28), ("Regular", 21), ("Regular", 24)])
        self["desc"] = Label(u"")
        for k in ("red", "green", "yellow", "blue", "menu"):
            self["key_" + k] = Label(u"")
        self["actions"] = ActionMap(["OkCancelActions", "ColorActions", "DirectionActions", "MenuActions",
                                     "ChannelSelectBaseActions", "InfoActions"], {
            "ok": self.keyOk, "cancel": self.keyCancel, "red": self.keyRed, "green": self.keyGreen,
            "yellow": self.keyYellow, "blue": self.keyBlue, "menu": self.keyMenu, "info": self.search,
            "up": lambda: self.keyMove(-1), "down": lambda: self.keyMove(1),
            "left": self.keyLeft, "right": self.keyRight,
            "nextBouquet": lambda: self.keyMove(-8), "prevBouquet": lambda: self.keyMove(8),
        }, -1)
        self.loader = eTimer()
        self.loader.callback.append(self._load)
        self.rtimer = eTimer()   # the channel list follows the bouquet list a moment later (fast scrolling)
        self.rtimer.callback.append(lambda: self._build_right(0))
        self.onLayoutFinish.append(self._start)  # OpenATV runs non-method entries with exec(): methods only

    def _start(self):
        self.loader.start(30, True)

    @staticmethod
    def _skin():
        d = {"W": s(1920), "H": s(1080), "img": IMG}
        for k, v in {"lx": 48, "ly": 38, "lw": 64, "tx": 132, "ty": 30, "tw": 1100, "th": 54, "tf": 44, "sty": 86, "sth": 34, "stf": 24,
                     "subx": 1220, "subw": 652, "subf": 23,
                     "bx": 64, "by": 156, "bw": 412, "bh": 624,
                     "cx": 520, "cy": 150, "cw": 1340, "ch": 640,
                     "dx": 72, "dy": 832, "dw": 1776, "dh": 124, "df": 24,
                     "fy": 996, "fd": 26, "fty": 988, "fth": 42, "ff": 25, "k1": 62, "k2": 392, "k3": 742, "k4": 1092, "k5": 1452}.items():
            d[k] = s(v)
        for i in range(1, 6):
            d["l%d" % i] = d["k%d" % i] + s(38)
        d["kw"] = s(320)
        return """
        <screen name="WacayoubChaines" position="0,0" size="%(W)d,%(H)d" flags="wfNoBorder" backgroundColor="#00070B14" title="Wacayoub Chaînes">
          <ePixmap position="0,0" size="%(W)d,%(H)d" pixmap="%(img)s/bg.jpg" scale="1" zPosition="-2" />
          <ePixmap position="%(lx)d,%(ly)d" size="%(lw)d,%(lw)d" pixmap="%(img)s/logo.png" alphatest="blend" scale="1" />
          <widget name="title" position="%(tx)d,%(ty)d" size="%(tw)d,%(th)d" font="Regular;%(tf)d" foregroundColor="#00F1F5F9" backgroundColor="#00070B14" transparent="1" valign="center" />
          <widget name="status" position="%(tx)d,%(sty)d" size="%(tw)d,%(sth)d" font="Regular;%(stf)d" foregroundColor="#007DD3FC" backgroundColor="#00070B14" transparent="1" valign="center" />
          <widget name="sub" position="%(subx)d,%(ty)d" size="%(subw)d,%(th)d" font="Regular;%(subf)d" foregroundColor="#008C9AB0" backgroundColor="#00070B14" transparent="1" halign="right" valign="center" />
          <widget name="bouquets" position="%(bx)d,%(by)d" size="%(bw)d,%(bh)d" backgroundColor="#00070B14" transparent="1" selectionPixmap="%(img)s/sel-cat.png" scrollbarMode="showOnDemand" scrollbarWidth="4" scrollbarForegroundColor="#003B82F6" enableWrapAround="1" />
          <widget name="chans" position="%(cx)d,%(cy)d" size="%(cw)d,%(ch)d" backgroundColor="#00070B14" transparent="1" selectionPixmap="%(img)s/sel-item.png" scrollbarMode="showOnDemand" scrollbarWidth="4" scrollbarForegroundColor="#003B82F6" />
          <widget name="desc" position="%(dx)d,%(dy)d" size="%(dw)d,%(dh)d" font="Regular;%(df)d" foregroundColor="#00CBD5E1" backgroundColor="#00070B14" transparent="1" />
          <ePixmap position="%(k1)d,%(fy)d" size="%(fd)d,%(fd)d" pixmap="%(img)s/k-red.png" alphatest="blend" scale="1" />
          <ePixmap position="%(k2)d,%(fy)d" size="%(fd)d,%(fd)d" pixmap="%(img)s/k-green.png" alphatest="blend" scale="1" />
          <ePixmap position="%(k3)d,%(fy)d" size="%(fd)d,%(fd)d" pixmap="%(img)s/k-yellow.png" alphatest="blend" scale="1" />
          <ePixmap position="%(k4)d,%(fy)d" size="%(fd)d,%(fd)d" pixmap="%(img)s/k-blue.png" alphatest="blend" scale="1" />
          <ePixmap position="%(k5)d,%(fy)d" size="%(fd)d,%(fd)d" pixmap="%(img)s/k-menu.png" alphatest="blend" scale="1" />
          <widget name="key_red" position="%(l1)d,%(fty)d" size="%(kw)d,%(fth)d" font="Regular;%(ff)d" foregroundColor="#00E2E8F0" backgroundColor="#00070B14" transparent="1" valign="center" />
          <widget name="key_green" position="%(l2)d,%(fty)d" size="%(kw)d,%(fth)d" font="Regular;%(ff)d" foregroundColor="#00E2E8F0" backgroundColor="#00070B14" transparent="1" valign="center" />
          <widget name="key_yellow" position="%(l3)d,%(fty)d" size="%(kw)d,%(fth)d" font="Regular;%(ff)d" foregroundColor="#00E2E8F0" backgroundColor="#00070B14" transparent="1" valign="center" />
          <widget name="key_blue" position="%(l4)d,%(fty)d" size="%(kw)d,%(fth)d" font="Regular;%(ff)d" foregroundColor="#00E2E8F0" backgroundColor="#00070B14" transparent="1" valign="center" />
          <widget name="key_menu" position="%(l5)d,%(fty)d" size="%(kw)d,%(fth)d" font="Regular;%(ff)d" foregroundColor="#00E2E8F0" backgroundColor="#00070B14" transparent="1" valign="center" />
        </screen>""" % d

    # ------------------------------------------------------------ loading
    def _load(self, keep=None):
        try:
            self.lib = B.Library()
        except Exception as e:
            self["status"].setText(u"Erreur de lecture : %s" % e)
            return
        self.marked = set()
        self._build_left(keep)
        self._set_focus("left")

    def _cur_bouquet(self):
        i = self["bouquets"].getSelectionIndex()
        return self.bqs[i] if 0 <= i < len(self.bqs) else None

    def _build_left(self, keep=None):
        self.bqs = self.lib.ordered(self.kind)
        rows = []
        for b in self.bqs:
            n = b.count()
            name = (u"   " * b.depth) + clean(b.name) + (u"  •" if b.dirty else u"")
            rows.append([b,
                         MultiContentEntryText(pos=(s(16), 0), size=(s(300), s(52)), font=0, flags=RT_HALIGN_LEFT | RT_VALIGN_CENTER,
                                               text=name, color=C_DIRTY if b.dirty else C_TEXT, color_sel=0xFFFFFF),
                         MultiContentEntryText(pos=(s(312), 0), size=(s(86), s(52)), font=1, flags=RT_HALIGN_RIGHT | RT_VALIGN_CENTER,
                                               text=u"%d" % n, color=C_DIM, color_sel=0xE2E8F0)])
        self["bouquets"].setList(rows)
        if keep is not None and keep in self.bqs:
            self["bouquets"].moveToIndex(self.bqs.index(keep))
        self._build_right()

    def _left_row_refresh(self):
        b = self._cur_bouquet()
        if b:
            i = self.bqs.index(b)
            self._build_left(b)
            self["bouquets"].moveToIndex(i)

    def _row(self, b, i, e, num, picons):
        mk = i in self.marked
        col = C_MARK if mk else C_TEXT
        name = clean(e.name(self.lib.services))
        if e.kind == "marker":
            return [i, MultiContentEntryText(pos=(s(24), 0), size=(s(1290), s(80)), font=2, flags=RT_HALIGN_LEFT | RT_VALIGN_CENTER,
                                             text=u"—  %s  —" % name, color=C_MARK if mk else C_HEAD, color_sel=0xFFFFFF)]
        row = [i, MultiContentEntryText(pos=(s(10), 0), size=(s(70), s(80)), font=2, flags=RT_HALIGN_RIGHT | RT_VALIGN_CENTER,
                                        text=u"%d" % num if num else u"", color=C_DIM, color_sel=0xDBEAFE)]
        p = self.picons.get(e) if picons else None
        if p:
            row.append(MultiContentEntryPixmapAlphaBlend(pos=(s(96), s(8)), size=(s(110), s(64)), png=p, flags=PIX_FLAGS))
        else:
            t = img("t-iptv.png" if e.kind == "stream" else "t-bouquet.png" if e.kind == "bouquet" else
                    "t-radio.png" if b.kind == "radio" else "t-tv.png")
            if t:
                row.append(MultiContentEntryPixmapAlphaBlend(pos=(s(121), s(10)), size=(s(60), s(60)), png=t, flags=PIX_FLAGS))
        row.append(MultiContentEntryText(pos=(s(226), s(6)), size=(s(1000), s(40)), font=0, flags=RT_HALIGN_LEFT | RT_VALIGN_CENTER,
                                         text=name, color=col, color_sel=0xFFFFFF))
        row.append(MultiContentEntryText(pos=(s(226), s(44)), size=(s(1000), s(30)), font=1, flags=RT_HALIGN_LEFT | RT_VALIGN_CENTER,
                                         text=clean(e.info(self.lib.services)), color=C_DIM, color_sel=0xDBEAFE))
        if mk and img("sel.png"):
            row.append(MultiContentEntryPixmapAlphaBlend(pos=(s(1270), s(25)), size=(s(30), s(30)), png=img("sel.png"), flags=PIX_FLAGS))
        return row

    def _build_right(self, index=None):
        b = self._cur_bouquet()
        self.rows = []
        if b:
            picons = len(b.entries) <= PICON_MAX
            num = 0
            for i, e in enumerate(b.entries):
                if e.kind in ("service", "stream"):
                    num += 1
                self.rows.append(self._row(b, i, e, num if e.kind in ("service", "stream") else 0, picons))
        self["chans"].setList(self.rows)
        if index is not None and self.rows:
            self["chans"].moveToIndex(max(0, min(index, len(self.rows) - 1)))
        self._update()

    def _cur_index(self):
        return self["chans"].getSelectionIndex() if self.rows else -1

    # ------------------------------------------------------------ texts and keys
    def _set_focus(self, where):
        self.focus = where
        self["bouquets"].selectionEnabled(where == "left")
        self["chans"].selectionEnabled(where == "right")
        self._update()

    def _update(self):
        if not self.lib:
            return
        b = self._cur_bouquet()
        dirty = self.lib.dirty()
        tail = u"  ·  modifié : VERT pour enregistrer" if dirty else u""
        if b:
            st = u"%s  ·  %d chaînes%s" % (clean(b.name), b.count(), (u"  ·  %d marquée(s)" % len(self.marked)) if self.marked else u"")
        else:
            st = u"Aucun bouquet"
        self["status"].setText(st + tail)
        self["sub"].setText(u"%s  ·  %d bouquets  ·  v%s" % (u"TV" if self.kind == "tv" else u"Radio", len(self.bqs), VERSION))
        keys = {"red": u"Supprimer", "green": u"Enregistrer", "yellow": u"Déplacer", "blue": u"Vers un bouquet", "menu": u"Outils"}
        if self.move == "chan":
            keys = {"red": u"", "green": u"", "yellow": u"Poser ici", "blue": u"", "menu": u""}
            self["desc"].setText(u"Déplacement : HAUT / BAS d'une ligne, GAUCHE / DROITE d'une page. OK ou JAUNE pour poser.")
        elif self.move == "bouquet":
            keys = {"red": u"", "green": u"", "yellow": u"Poser ici", "blue": u"", "menu": u""}
            self["desc"].setText(u"Déplacement du bouquet : HAUT / BAS. OK ou JAUNE pour poser.")
        elif self.focus == "left":
            keys.update(red=u"Suppr. bouquet", yellow=u"Déplacer bouquet", blue=u"Renommer")
            self["desc"].setText(u"OK / DROITE : ouvrir le bouquet.  MENU : outils intelligents (trier, doublons, chaînes mortes, "
                                 u"bouquets par thème, nouveau bouquet, TV / Radio, annuler).  INFO : rechercher une chaîne.")
        else:
            e = self._cur_entry()
            self["desc"].setText(u"OK : marquer plusieurs chaînes.  JAUNE : déplacer.  BLEU : déplacer ou copier vers un autre bouquet.  "
                                 u"GAUCHE : bouquets.  CH+/CH- : page." + (u"\n%s" % clean(e.ref) if e and e.kind == "service" else u""))
        for k, v in keys.items():
            self["key_" + k].setText(v)

    def _cur_entry(self):
        b, i = self._cur_bouquet(), self._cur_index()
        return b.entries[i] if b and 0 <= i < len(b.entries) else None

    def keyLeft(self):
        if self.move == "chan":
            return self._move_block(-8)
        if self.move:
            return
        if self.focus == "right":
            self._set_focus("left")
        else:
            self["bouquets"].pageUp()
            self.rtimer.start(250, True)

    def keyRight(self):
        if self.move == "chan":
            return self._move_block(8)
        if self.move:
            return
        if self.focus == "left":
            self._right_now()
            if self.rows:
                self._set_focus("right")
        else:
            self["chans"].pageDown()
            self._update()

    def keyMove(self, d):
        if self.move == "chan":
            return self._move_block(d)
        if self.move == "bouquet":
            b = self._cur_bouquet()
            if b and self.lib.move_top(b, 1 if d > 0 else -1):
                self._build_left(b)
            return
        lst = self["bouquets"] if self.focus == "left" else self["chans"]
        if d == -1:
            lst.up()
        elif d == 1:
            lst.down()
        elif d < 0:
            lst.pageUp()
        else:
            lst.pageDown()
        if self.focus == "left":
            self.marked = set()
            self.rtimer.start(250, True)
            self._update()
        else:
            self._update()

    def _right_now(self):
        if self.rtimer.isActive():
            self.rtimer.stop()
            self._build_right(0)

    def keyOk(self):
        if self.move:
            return self.keyYellow()
        if self.focus == "left":
            self._right_now()
            if self.rows:
                self._set_focus("right")
            return
        i = self._cur_index()
        if i < 0:
            return
        self.marked.symmetric_difference_update([i])
        self._refresh_rows(i, i)
        self["chans"].down()
        self._update()

    def _refresh_rows(self, lo, hi):
        b = self._cur_bouquet()
        if not b:
            return
        picons = len(b.entries) <= PICON_MAX
        num = sum(1 for e in b.entries[:lo] if e.kind in ("service", "stream"))
        for i in range(lo, min(hi, len(b.entries) - 1) + 1):
            e = b.entries[i]
            if e.kind in ("service", "stream"):
                num += 1
            self.rows[i] = self._row(b, i, e, num if e.kind in ("service", "stream") else 0, picons)
            try:
                self["chans"].l.invalidateEntry(i)
            except Exception:
                self["chans"].setList(self.rows)
                break

    def keyCancel(self):
        if self.move:
            return self.keyYellow()
        if self.focus == "right":
            if self.marked:
                old = sorted(self.marked)
                self.marked = set()
                self._refresh_rows(old[0], old[-1])
                return self._update()
            return self._set_focus("left")
        if self.lib and self.lib.dirty():
            return self.session.openWithCallback(self._quit_answer, ChoiceBox, title=u"Enregistrer les changements ?",
                                                 list=[(u"Oui, enregistrer et quitter", "save"), (u"Non, quitter sans enregistrer", "quit"),
                                                       (u"Rester", None)])
        self.close()

    def _quit_answer(self, c):
        if not c or not c[1]:
            return
        if c[1] == "save" and not self._save():
            return
        self.close()

    # ------------------------------------------------------------ move / delete / copy
    def _selection(self):
        if self.marked:
            return sorted(self.marked)
        i = self._cur_index()
        return [i] if i >= 0 else []

    def keyYellow(self):
        if not self.lib:
            return
        if self.move:
            self.move = None
            self.marked = set()
            if self.focus == "right":
                self._build_right(self.block[0] if self.block else None)
            self._build_left(self._cur_bouquet()) if self.focus == "left" else self._update()
            return
        if self.focus == "left":
            b = self._cur_bouquet()
            if b and b.depth == 0:
                self.move = "bouquet"
                self._update()
            return
        sel = self._selection()
        if not sel:
            return
        b = self._cur_bouquet()
        self.block = self.lib.gather(b, sel)
        self.marked = set(self.block)
        self.move = "chan"
        self._build_right(self.block[0])
        self._left_mark()

    def _move_block(self, d):
        b = self._cur_bouquet()
        old = self.block
        self.block = self.lib.move_block(b, old, d)
        self.marked = set(self.block)
        lo, hi = min(old[0], self.block[0]), max(old[-1], self.block[-1])
        self._refresh_rows(lo, hi)
        self["chans"].moveToIndex(self.block[0])
        self._update()

    def _left_mark(self):
        """Shows the '•' (modified) on the current bouquet without rebuilding the right list."""
        b = self._cur_bouquet()
        if b and b.dirty:
            i = self.bqs.index(b)
            rows = self["bouquets"].list
            rows[i] = [b] + rows[i][1:]
            rows[i][1] = MultiContentEntryText(pos=(s(16), 0), size=(s(300), s(52)), font=0, flags=RT_HALIGN_LEFT | RT_VALIGN_CENTER,
                                               text=(u"   " * b.depth) + clean(b.name) + u"  •", color=C_DIRTY, color_sel=0xFFFFFF)
            try:
                self["bouquets"].l.invalidateEntry(i)
            except Exception:
                pass
        self._update()

    def keyRed(self):
        if not self.lib or self.move:
            return
        b = self._cur_bouquet()
        if not b:
            return
        if self.focus == "left":
            n = b.count()
            return self.session.openWithCallback(lambda ok: ok and self._del_bouquet(b), MessageBox,
                                                 u"Supprimer le bouquet « %s » (%d chaînes) ?\nRien n'est perdu avant VERT (enregistrer), "
                                                 u"et MENU → Annuler remet l'ancien." % (clean(b.name), n), MessageBox.TYPE_YESNO)
        sel = self._selection()
        if not sel:
            return
        what = clean(b.entries[sel[0]].name(self.lib.services)) if len(sel) == 1 else u"%d chaînes" % len(sel)

        def go(ok):
            if ok:
                self.lib.delete(b, sel)
                self.marked = set()
                self._build_right(sel[0])
                self._left_mark()
        self.session.openWithCallback(go, MessageBox, u"Supprimer %s de « %s » ?" % (what, clean(b.name)), MessageBox.TYPE_YESNO,
                                      default=True)

    def _del_bouquet(self, b):
        i = self.bqs.index(b)
        self.lib.delete_bouquet(b)
        self._build_left()
        self["bouquets"].moveToIndex(max(0, min(i, len(self.bqs) - 1)))
        self._build_right(0)

    def _bouquet_choices(self, exclude=None):
        out = [(u"＋ Nouveau bouquet…", "new")]
        for b in self.lib.ordered(self.kind):
            if b is not exclude:
                out.append(((u"   " * b.depth) + clean(b.name) + u"  (%d)" % b.count(), b))
        return out

    def keyBlue(self):
        if not self.lib or self.move:
            return
        b = self._cur_bouquet()
        if not b:
            return
        if self.focus == "left":
            return self.session.openWithCallback(lambda t: t and self._rename_bouquet(b, t), VirtualKeyBoard,
                                                 title=u"Nouveau nom du bouquet", text=b.name)
        sel = self._selection()
        if not sel:
            return
        n = len(sel)

        def how(c):
            if c:
                self.session.openWithCallback(lambda t: t and self._to_bouquet(b, sel, t[1], c[1]), ChoiceBox,
                                              title=u"%s %d chaîne(s) vers…" % (u"Déplacer" if c[1] else u"Copier", n),
                                              list=self._bouquet_choices(b))
        self.session.openWithCallback(how, ChoiceBox, title=u"%d chaîne(s) sélectionnée(s)" % n,
                                      list=[(u"Déplacer vers un autre bouquet", True), (u"Copier vers un autre bouquet", False)])

    def _to_bouquet(self, b, sel, target, move):
        if target == "new":
            return self.session.openWithCallback(lambda t: t and self._to_bouquet(b, sel, self.lib.new_bouquet(t, self.kind), move),
                                                 VirtualKeyBoard, title=u"Nom du nouveau bouquet", text=u"")
        added = self.lib.copy_to(b, sel, target, move=move)
        self.marked = set()
        self._build_left(b)
        self._build_right(sel[0])
        self.session.open(MessageBox, u"%d chaîne(s) %s dans « %s »%s." % (
            added, u"déplacée(s)" if move else u"copiée(s)", clean(target.name),
            u" (les doublons ne sont pas ajoutés)" if added < len(sel) else u""), MessageBox.TYPE_INFO, timeout=4)

    def _rename_bouquet(self, b, name):
        self.lib.rename(b, name.strip() or b.name)
        self._build_left(b)

    # ------------------------------------------------------------ save / undo
    def keyGreen(self):
        if self.lib and not self.move:
            self._save()

    def _save(self):
        try:
            n, d = self.lib.save()
        except Exception as e:
            self.session.open(MessageBox, u"Enregistrement impossible : %s" % e, MessageBox.TYPE_ERROR)
            return False
        if n:
            self._reload_enigma()
            self.session.open(MessageBox, u"%d fichier(s) enregistré(s). Liste des chaînes mise à jour.\n"
                                          u"MENU → Annuler le dernier enregistrement remet l'ancienne version." % n,
                              MessageBox.TYPE_INFO, timeout=4)
        self._build_left(self._cur_bouquet())
        return True

    @staticmethod
    def _reload_enigma():
        try:
            from enigma import eDVBDB
            eDVBDB.getInstance().reloadBouquets()
        except Exception as e:
            print("[WacayoubChaines] reload: %s" % e)

    def _undo(self):
        d, info = self.lib.last_backup()
        if not d:
            return self.session.open(MessageBox, u"Aucun enregistrement à annuler.", MessageBox.TYPE_INFO, timeout=4)

        def go(ok):
            if ok:
                n = self.lib.undo()
                self._reload_enigma()
                self._load()
                self.session.open(MessageBox, u"%d fichier(s) remis comme avant." % n, MessageBox.TYPE_INFO, timeout=4)
        self.session.openWithCallback(go, MessageBox, u"Remettre les bouquets comme avant l'enregistrement du %s ?%s" % (
            info.get("date", ""), u"\nLes changements non enregistrés seront perdus." if self.lib.dirty() else u""), MessageBox.TYPE_YESNO)

    # ------------------------------------------------------------ smart tools
    def keyMenu(self):
        if not self.lib or self.move:
            return
        b = self._cur_bouquet()
        menu = []
        if b:
            dups, dead = self.lib.duplicates(b), self.lib.dead(b)
            menu += [(u"Trier « %s » de A à Z" % clean(b.name), "sort"),
                     (u"Trier « %s » : 4K et HD d'abord" % clean(b.name), "sorthd"),
                     (u"Supprimer les doublons de ce bouquet (%d)" % len(dups), "dups"),
                     (u"Supprimer les chaînes mortes de ce bouquet (%d)" % len(dead), "dead")]
        menu.append((u"★ Créer les bouquets par thème (Sport, Info, Enfants, Cinéma…)", "themes"))
        empty = self.lib.empty_bouquets()
        if empty:
            menu.append((u"Supprimer les bouquets vides (%d)" % len(empty), "empty"))
        menu += [(u"Nouveau bouquet…", "new"), (u"Rechercher une chaîne…  (INFO)", "search")]
        if b and self.focus == "right":
            menu += [(u"Ajouter un séparateur ici…", "marker"), (u"Renommer cette chaîne…", "renchan")]
        if self.marked:
            menu.append((u"Tout démarquer (%d)" % len(self.marked), "unmark"))
        elif b and self.focus == "right":
            menu.append((u"Tout marquer dans ce bouquet", "markall"))
        menu.append((u"Passer aux bouquets Radio" if self.kind == "tv" else u"Passer aux bouquets TV", "kind"))
        d, info = self.lib.last_backup()
        if d:
            menu.append((u"Annuler le dernier enregistrement (%s)" % info.get("date", ""), "undo"))
        self.session.openWithCallback(self._menu_done, ChoiceBox, title=u"Outils intelligents", list=menu)

    def _menu_done(self, c):
        if not c:
            return
        a = c[1]
        b = self._cur_bouquet()
        if a in ("sort", "sorthd"):
            self.lib.sort(b, "hd" if a == "sorthd" else "name")
            self.marked = set()
            self._build_right(0)
            self._left_mark()
        elif a in ("dups", "dead"):
            idx = self.lib.duplicates(b) if a == "dups" else self.lib.dead(b)
            if not idx:
                return self.session.open(MessageBox, u"Rien à supprimer.", MessageBox.TYPE_INFO, timeout=3)
            self.lib.delete(b, idx)
            self.marked = set()
            self._build_right(0)
            self._left_mark()
            self.session.open(MessageBox, u"%d chaîne(s) supprimée(s) (VERT pour enregistrer)." % len(idx), MessageBox.TYPE_INFO, timeout=4)
        elif a == "themes":
            res = self.lib.themes(self.kind)
            self._build_left()
            self["bouquets"].moveToIndex(0)
            self._build_right(0)
            self.session.open(MessageBox, u"Bouquets par thème créés en haut de la liste :\n" +
                              u"\n".join(u"%s : %d" % (k, v) for k, v in res.items()) +
                              u"\n\nTes autres bouquets ne changent pas. VERT pour enregistrer.", MessageBox.TYPE_INFO)
        elif a == "empty":
            for x in self.lib.empty_bouquets():
                self.lib.delete_bouquet(x)
            self._build_left()
        elif a == "new":
            self.session.openWithCallback(self._new_bouquet, VirtualKeyBoard, title=u"Nom du nouveau bouquet", text=u"")
        elif a == "search":
            self.search()
        elif a == "marker":
            self.session.openWithCallback(lambda t: t and self._add_marker(b, t), VirtualKeyBoard, title=u"Texte du séparateur", text=u"")
        elif a == "renchan":
            e = self._cur_entry()
            if e:
                self.session.openWithCallback(lambda t: t and self._rename_chan(b, e, t), VirtualKeyBoard,
                                              title=u"Nom affiché de la chaîne", text=e.name(self.lib.services))
        elif a == "unmark":
            self.marked = set()
            self._build_right(self._cur_index())
        elif a == "markall":
            self.marked = set(i for i, e in enumerate(b.entries) if e.kind in ("service", "stream"))
            self._build_right(self._cur_index())
        elif a == "kind":
            self.kind = "radio" if self.kind == "tv" else "tv"
            self.marked = set()
            self._build_left()
            self["bouquets"].moveToIndex(0)
            self._build_right(0)
            self._set_focus("left")
        elif a == "undo":
            self._undo()

    def _new_bouquet(self, name):
        if name:
            b = self.lib.new_bouquet(name.strip(), self.kind)
            self._build_left(b)
            self._set_focus("left")

    def _add_marker(self, b, text):
        i = max(0, self._cur_index())
        self.lib.add_marker(b, i, text.strip())
        self.marked = set()
        self._build_right(i)
        self._left_mark()

    def _rename_chan(self, b, e, text):
        e.desc = text.strip() or None
        b.dirty = True
        i = self._cur_index()
        self._refresh_rows(i, i)
        self._left_mark()

    def search(self):
        if self.lib and not self.move:
            self.session.openWithCallback(self._search_text, VirtualKeyBoard, title=u"Rechercher une chaîne (dans tous les bouquets)", text=u"")

    def _search_text(self, text):
        if not text:
            return
        res = self.lib.search(text, self.kind)
        if not res:
            return self.session.open(MessageBox, u"Aucune chaîne « %s »." % text, MessageBox.TYPE_INFO, timeout=4)
        lst = [(u"%s   ·   %s" % (clean(b.entries[i].name(self.lib.services)), clean(b.name)), (b, i)) for b, i in res[:300]]
        self.session.openWithCallback(self._jump, ChoiceBox, title=u"%d résultat(s) pour « %s »" % (len(res), text), list=lst)

    def _jump(self, c):
        if not c:
            return
        b, i = c[1]
        if b in self.bqs:
            self.marked = set()
            self["bouquets"].moveToIndex(self.bqs.index(b))
            self._build_right(i)
            self._set_focus("right")


def main(session, **kwargs):
    session.open(WacayoubChaines)


def Plugins(**kwargs):
    return [
        PluginDescriptor(name=u"Wacayoub Chaînes", description=u"Organiser les chaînes : déplacer, supprimer, trier, ranger par thème",
                         where=PluginDescriptor.WHERE_PLUGINMENU, icon="plugin.png", fnc=main),
        PluginDescriptor(name=u"Wacayoub Chaînes", description=u"Organiser les chaînes",
                         where=PluginDescriptor.WHERE_EXTENSIONSMENU, fnc=main),
    ]
