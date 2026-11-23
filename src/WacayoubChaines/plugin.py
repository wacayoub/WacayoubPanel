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

VERSION = "1.1.0"
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
        self.bmarked = set()      # files of the marked bouquets
        self.sweep = False        # continuous selection: moving marks every channel passed
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
                                     "ChannelSelectBaseActions", "InfoActions", "NumberActions"], {
            "0": self.keyZero,
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
        self.bmarked &= set(b.file for b in self.bqs)
        self["bouquets"].setList([self._brow(b) for b in self.bqs])
        if keep is not None and keep in self.bqs:
            self["bouquets"].moveToIndex(self.bqs.index(keep))
        self._build_right()

    def _brow(self, b):
        mk = b.file in self.bmarked
        name = (u"   " * b.depth) + clean(b.name) + (u"  •" if b.dirty else u"")
        row = [b, MultiContentEntryText(pos=(s(16), 0), size=(s(290 if mk else 300), s(52)), font=0, flags=RT_HALIGN_LEFT | RT_VALIGN_CENTER,
                                        text=name, color=C_MARK if mk else C_DIRTY if b.dirty else C_TEXT, color_sel=0xFFFFFF),
               MultiContentEntryText(pos=(s(300), 0), size=(s(66 if mk else 98), s(52)), font=1, flags=RT_HALIGN_RIGHT | RT_VALIGN_CENTER,
                                     text=u"%d" % b.count(), color=C_DIM, color_sel=0xE2E8F0)]
        if mk and img("sel.png"):
            row.append(MultiContentEntryPixmapAlphaBlend(pos=(s(372), s(13)), size=(s(26), s(26)), png=img("sel.png"), flags=PIX_FLAGS))
        return row

    def _brefresh(self, b):
        if b in self.bqs:
            i = self.bqs.index(b)
            self["bouquets"].list[i] = self._brow(b)
            try:
                self["bouquets"].l.invalidateEntry(i)
            except Exception:
                self["bouquets"].setList(self["bouquets"].list)

    def _bsel(self):
        """Marked bouquets, or the current one."""
        if self.bmarked:
            return [b for b in self.bqs if b.file in self.bmarked]
        b = self._cur_bouquet()
        return [b] if b else []

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
            st = u"%s  ·  %d chaînes%s%s" % (clean(b.name), b.count(), (u"  ·  %d marquée(s)" % len(self.marked)) if self.marked else u"",
                                             (u"  ·  %d bouquet(s) marqué(s)" % len(self.bmarked)) if self.bmarked else u"")
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
        elif self.sweep:
            self["desc"].setText(u"Sélection continue : HAUT / BAS (et CH+ / CH-) marquent chaque chaîne au passage. 0 ou OK : arrêter.")
        elif self.focus == "left" and self.bmarked:
            n = len(self.bmarked)
            keys.update(red=u"Supprimer (%d)" % n, yellow=u"Déplacer (%d)" % n, blue=u"Fusionner (%d)" % n)
            self["desc"].setText(u"%d bouquet(s) marqué(s).  0 : marquer / démarquer.  ROUGE : les supprimer.  JAUNE : les déplacer ensemble.  "
                                 u"BLEU : les fusionner en un seul.  MENU : trier / nettoyer tous les bouquets marqués." % n)
        elif self.focus == "left":
            keys.update(red=u"Suppr. bouquet", yellow=u"Déplacer bouquet", blue=u"Renommer")
            self["desc"].setText(u"OK / DROITE : ouvrir.  0 : marquer plusieurs bouquets (supprimer, déplacer, fusionner ensemble).  "
                                 u"MENU : outils intelligents.  INFO : rechercher une chaîne.")
        else:
            e = self._cur_entry()
            self["desc"].setText(u"OK : marquer.  0 : sélection continue (HAUT / BAS marquent en passant).  MENU : sélection intelligente "
                                 u"(par nom, HD, SD, IPTV, tout, inverser).  JAUNE : déplacer.  BLEU : vers un autre bouquet.  GAUCHE : bouquets.")
        for k, v in keys.items():
            self["key_" + k].setText(v)

    def _cur_entry(self):
        b, i = self._cur_bouquet(), self._cur_index()
        return b.entries[i] if b and 0 <= i < len(b.entries) else None

    def keyZero(self):
        if not self.lib or self.move:
            return
        if self.focus == "left":
            b = self._cur_bouquet()
            if b:
                self.bmarked.symmetric_difference_update([b.file])
                self._brefresh(b)
                self["bouquets"].down()
                self.rtimer.start(250, True)
                self._update()
            return
        self.sweep = not self.sweep
        if self.sweep:
            self._mark_range(self._cur_index(), self._cur_index())
        self._update()

    def _mark_range(self, a, b):
        if a < 0 or b < 0:
            return
        lo, hi = min(a, b), max(a, b)
        bq = self._cur_bouquet()
        new = [i for i in range(lo, hi + 1) if i < len(bq.entries) and bq.entries[i].kind in ("service", "stream", "marker")]
        if new:
            self.marked.update(new)
            self._refresh_rows(lo, hi)

    def keyLeft(self):
        if self.move == "chan":
            return self._move_block(-8)
        if self.move:
            return
        self.sweep = False
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
            files = [x.file for x in self._bsel()]
            if b and self.lib.move_tops(self.kind, files, 1 if d > 0 else -1):
                self._build_left(b)
            return
        lst = self["bouquets"] if self.focus == "left" else self["chans"]
        before = self._cur_index()
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
            if self.sweep:
                self._mark_range(before, self._cur_index())
            self._update()

    def _right_now(self):
        if self.rtimer.isActive():
            self.rtimer.stop()
            self._build_right(0)

    def keyOk(self):
        if self.move:
            return self.keyYellow()
        if self.sweep:
            self.sweep = False
            return self._update()
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
        if self.sweep:
            self.sweep = False
            return self._update()
        if self.focus == "left" and self.bmarked:
            marked = [b for b in self.bqs if b.file in self.bmarked]
            self.bmarked = set()
            for b in marked:
                self._brefresh(b)
            return self._update()
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
            self.bmarked = set()
            if self.focus == "right":
                self._build_right(self.block[0] if self.block else None)
            self._build_left(self._cur_bouquet()) if self.focus == "left" else self._update()
            return
        if self.focus == "left":
            sel = [b for b in self._bsel() if b.depth == 0]
            if sel:
                self.bmarked = set(b.file for b in sel) if self.bmarked else set()
                self.lib.move_tops(self.kind, [b.file for b in sel], 0)
                self._build_left(sel[0])
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
            self._brefresh(b)
        self._update()

    def keyRed(self):
        if not self.lib or self.move:
            return
        b = self._cur_bouquet()
        if not b:
            return
        if self.focus == "left" and self.bmarked:
            sel = self._bsel()
            return self.session.openWithCallback(lambda ok: ok and self._del_bouquets(sel), MessageBox,
                                                 u"Supprimer %d bouquets (%d chaînes) ?\n%s\nRien n'est perdu avant VERT, et MENU → Annuler remet l'ancien."
                                                 % (len(sel), sum(x.count() for x in sel), u", ".join(clean(x.name) for x in sel[:6]) +
                                                    (u"…" if len(sel) > 6 else u"")), MessageBox.TYPE_YESNO)
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

    def _del_bouquets(self, sel):
        i = self.bqs.index(sel[0]) if sel[0] in self.bqs else 0
        for b in sel:
            if b.file in self.lib.bouquets:
                self.lib.delete_bouquet(b)
        self.bmarked = set()
        self._build_left()
        self["bouquets"].moveToIndex(max(0, min(i, len(self.bqs) - 1)))
        self._build_right(0)

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
        if self.focus == "left" and len(self.bmarked) >= 2:
            sel = self._bsel()

            def keep(c):
                if c:
                    self.session.openWithCallback(lambda t: t and self._merge(sel, t, c[1]), VirtualKeyBoard,
                                                  title=u"Nom du bouquet fusionné", text=clean(sel[0].name))
            return self.session.openWithCallback(keep, ChoiceBox, title=u"Fusionner %d bouquets (%d chaînes, sans doublons)" % (
                len(sel), sum(x.count() for x in sel)), list=[(u"Fusionner et supprimer les anciens bouquets", False),
                                                              (u"Fusionner et garder les anciens bouquets", True)])
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

    def _merge(self, sel, name, keep):
        target = self.lib.merge(sel, name.strip() or clean(sel[0].name), keep=keep)
        self.bmarked = set()
        self._build_left(target)
        self._set_focus("left")
        self.session.open(MessageBox, u"« %s » : %d chaînes (VERT pour enregistrer)." % (clean(target.name), target.count()),
                          MessageBox.TYPE_INFO, timeout=4)

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
        if self.focus == "left" and self.bmarked:
            n = len(self.bmarked)
            menu += [(u"Trier les %d bouquets marqués de A à Z (chaînes)" % n, "msort"),
                     (u"Trier les %d bouquets marqués : 4K et HD d'abord" % n, "msorthd"),
                     (u"Supprimer les doublons des %d bouquets marqués" % n, "mdups"),
                     (u"Supprimer les chaînes mortes des %d bouquets marqués" % n, "mdead"),
                     (u"Démarquer les bouquets", "bunmark")]
        elif self.focus == "left":
            menu.append((u"Marquer tous les bouquets", "ball"))
        if b and self.focus == "right":
            menu += [(u"Sélection : par nom…", "s:name"), (u"Sélection : chaînes HD / 4K", "s:hd"), (u"Sélection : chaînes SD", "s:sd"),
                     (u"Sélection : chaînes IPTV", "s:iptv"), (u"Sélection : chaînes satellite", "s:sat"),
                     (u"Sélection : inverser", "s:invert")]
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
        if a.startswith("s:"):
            return self._smart_select(b, a[2:])
        if a in ("msort", "msorthd", "mdups", "mdead"):
            total = 0
            for x in self._bsel():
                if a == "msort" or a == "msorthd":
                    self.lib.sort(x, "hd" if a == "msorthd" else "name")
                else:
                    idx = self.lib.duplicates(x) if a == "mdups" else self.lib.dead(x)
                    total += len(idx)
                    if idx:
                        self.lib.delete(x, idx)
            self._build_left(b)
            if a in ("mdups", "mdead"):
                self.session.open(MessageBox, u"%d chaîne(s) supprimée(s) (VERT pour enregistrer)." % total, MessageBox.TYPE_INFO, timeout=4)
            return
        if a == "bunmark":
            self.bmarked = set()
            return self._build_left(b)
        if a == "ball":
            self.bmarked = set(x.file for x in self.bqs)
            return self._build_left(b)
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

    def _smart_select(self, b, how):
        if how == "name":
            return self.session.openWithCallback(lambda t: t and self._smart_select_name(b, t), VirtualKeyBoard,
                                                 title=u"Marquer les chaînes dont le nom contient…", text=u"")
        if how == "invert":
            self.marked = set(i for i, e in enumerate(b.entries) if e.kind in ("service", "stream")) - self.marked
        else:
            self.marked |= set(self.lib.select(b, how))
        self._build_right(self._cur_index())

    def _smart_select_name(self, b, text):
        found = self.lib.select(b, "name", text)
        self.marked |= set(found)
        self._build_right(found[0] if found else self._cur_index())
        if not found:
            self.session.open(MessageBox, u"Aucune chaîne « %s » dans ce bouquet." % text, MessageBox.TYPE_INFO, timeout=3)

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
