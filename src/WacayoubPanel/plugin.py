# -*- coding: utf-8 -*-
# Wacayoub Panel - installe, met à jour et supprime les plugins, skins et scripts de wacayoub.
import json
import os

from enigma import eListboxPythonMultiContent, gFont, getDesktop, RT_HALIGN_LEFT, RT_HALIGN_RIGHT, RT_VALIGN_CENTER
from Components.ActionMap import ActionMap
from Components.Console import Console as AsyncConsole
from Components.Label import Label
from Components.MenuList import MenuList
from Components.MultiContent import MultiContentEntryText
from Plugins.Plugin import PluginDescriptor
from Screens.ChoiceBox import ChoiceBox
from Screens.Console import Console
from Screens.MessageBox import MessageBox
from Screens.Screen import Screen
from Screens.Standby import TryQuitMainloop

from . import feed as F

VERSION = "1.0.2"
PANEL_PKG = "enigma2-plugin-extensions-wacayoubpanel"
PLUGIN_DIR = os.path.dirname(os.path.abspath(__file__))

_W = getDesktop(0).size().width() or 1920
SC = _W / 1920.0


def s(v):
    return int(round(v * SC))


C_TEXT = 0xFFFFFF
C_DIM = 0x9AA7B8
C_STATE = {
    F.ST_NONE: 0x9AA7B8,
    F.ST_OK: 0x46D17D,
    F.ST_UPDATE: 0xFFB020,
    F.ST_PARTIAL: 0xFFB020,
    F.ST_NA: 0x6B7380,
}
ICON = {F.ST_NONE: u"○", F.ST_OK: u"●", F.ST_UPDATE: u"▲", F.ST_PARTIAL: u"◐", F.ST_NA: u"×"}
TYPE_LABEL = {"plugin": "Plugin", "skin": "Skin", "script": "Script", "panel": "Panel"}


class _List(MenuList):
    def __init__(self, item_h, fonts):
        MenuList.__init__(self, [], False, eListboxPythonMultiContent)
        for i, (name, size) in enumerate(fonts):
            self.l.setFont(i, gFont(name, s(size)))
        self.l.setItemHeight(s(item_h))


def _human(n):
    n = float(n or 0)
    for unit in ("o", "Ko", "Mo", "Go"):
        if n < 1024 or unit == "Go":
            return ("%.0f %s" if unit in ("o", "Ko") else "%.1f %s") % (n, unit)
        n /= 1024.0


class WacayoubPanel(Screen):
    skin = """
    <screen name="WacayoubPanel" position="0,0" size="%(W)d,%(H)d" flags="wfNoBorder" backgroundColor="#00080C14" title="Wacayoub Panel">
      <eLabel position="0,0" size="%(W)d,%(hh)d" backgroundColor="#000F1826" zPosition="-1" />
      <eLabel position="%(x0)d,%(hl)d" size="%(wl)d,%(two)d" backgroundColor="#002F8CFF" />
      <widget name="title" position="%(x0)d,%(ty)d" size="%(tw)d,%(th)d" font="Regular;%(tf)d" foregroundColor="#00FFFFFF" backgroundColor="#000F1826" transparent="1" valign="center" />
      <widget name="sub" position="%(sx)d,%(ty)d" size="%(sw)d,%(th)d" font="Regular;%(sf)d" foregroundColor="#009AA7B8" backgroundColor="#000F1826" transparent="1" halign="right" valign="center" />
      <eLabel position="%(x0)d,%(ly)d" size="%(cw)d,%(lh)d" backgroundColor="#00101A2A" zPosition="-1" />
      <widget name="cats" position="%(x0)d,%(ly)d" size="%(cw)d,%(lh)d" backgroundColor="#00101A2A" foregroundColor="#00FFFFFF" backgroundColorSelected="#002F8CFF" foregroundColorSelected="#00FFFFFF" scrollbarMode="showNever" transparent="0" />
      <widget name="items" position="%(ix)d,%(ly)d" size="%(iw)d,%(lh)d" backgroundColor="#00080C14" foregroundColor="#00FFFFFF" backgroundColorSelected="#00203A5C" foregroundColorSelected="#00FFFFFF" scrollbarMode="showOnDemand" transparent="0" />
      <eLabel position="%(x0)d,%(dy0)d" size="%(wl)d,%(one)d" backgroundColor="#00203040" />
      <widget name="desc" position="%(x0)d,%(dy)d" size="%(wl)d,%(dh)d" font="Regular;%(df)d" foregroundColor="#00C9D4E3" backgroundColor="#00080C14" transparent="1" />
      <widget name="status" position="%(x0)d,%(sty)d" size="%(wl)d,%(sth)d" font="Regular;%(df)d" foregroundColor="#00FFB020" backgroundColor="#00080C14" transparent="1" />
      <eLabel position="%(b0)d,%(by)d" size="%(bw)d,%(bh)d" backgroundColor="#00E5484D" />
      <eLabel position="%(b1)d,%(by)d" size="%(bw)d,%(bh)d" backgroundColor="#0046D17D" />
      <eLabel position="%(b2)d,%(by)d" size="%(bw)d,%(bh)d" backgroundColor="#00FFB020" />
      <eLabel position="%(b3)d,%(by)d" size="%(bw)d,%(bh)d" backgroundColor="#002F8CFF" />
      <widget name="key_red" position="%(t0)d,%(bty)d" size="%(btw)d,%(bth)d" font="Regular;%(bf)d" foregroundColor="#00FFFFFF" backgroundColor="#00080C14" transparent="1" valign="center" />
      <widget name="key_green" position="%(t1)d,%(bty)d" size="%(btw)d,%(bth)d" font="Regular;%(bf)d" foregroundColor="#00FFFFFF" backgroundColor="#00080C14" transparent="1" valign="center" />
      <widget name="key_yellow" position="%(t2)d,%(bty)d" size="%(btw)d,%(bth)d" font="Regular;%(bf)d" foregroundColor="#00FFFFFF" backgroundColor="#00080C14" transparent="1" valign="center" />
      <widget name="key_blue" position="%(t3)d,%(bty)d" size="%(btw)d,%(bth)d" font="Regular;%(bf)d" foregroundColor="#00FFFFFF" backgroundColor="#00080C14" transparent="1" valign="center" />
    </screen>""" % {
        "W": s(1920), "H": s(1080), "hh": s(120), "x0": s(60), "wl": s(1800), "hl": s(118), "two": max(1, s(2)), "one": max(1, s(1)),
        "ty": s(28), "tw": s(900), "th": s(64), "tf": s(46), "sx": s(960), "sw": s(900), "sf": s(26),
        "ly": s(150), "cw": s(420), "lh": s(640), "ix": s(500), "iw": s(1360),
        "dy0": s(808), "dy": s(822), "dh": s(130), "df": s(27), "sty": s(955), "sth": s(40),
        "by": s(1012), "bw": s(12), "bh": s(40),
        "b0": s(60), "b1": s(510), "b2": s(960), "b3": s(1410),
        "t0": s(84), "t1": s(534), "t2": s(984), "t3": s(1434), "bty": s(1004), "btw": s(420), "bth": s(56), "bf": s(28),
    }

    def __init__(self, session):
        Screen.__init__(self, session)
        self.setTitle("Wacayoub Panel")
        self.feed = None
        self.installed = {}
        self.archs = F.supported_archs()
        self.changed = False
        self.focus_items = False
        self.cat_ids = []
        self.async_console = AsyncConsole()

        self["title"] = Label("Wacayoub Panel")
        self["sub"] = Label("")
        self["cats"] = _List(64, [("Regular", 30)])
        self["items"] = _List(80, [("Regular", 31), ("Regular", 23)])
        self["desc"] = Label("")
        self["status"] = Label("")
        self["key_red"] = Label("Supprimer")
        self["key_green"] = Label("Installer / MAJ")
        self["key_yellow"] = Label("Actualiser")
        self["key_blue"] = Label("Tout mettre à jour")

        self["actions"] = ActionMap(["OkCancelActions", "ColorActions", "DirectionActions"], {
            "ok": self.keyOk,
            "cancel": self.keyExit,
            "red": self.keyRemove,
            "green": self.keyInstall,
            "yellow": self.refreshFeed,
            "blue": self.keyUpdateAll,
            "left": self.keyLeft,
            "right": self.keyRight,
            "up": self.keyUp,
            "down": self.keyDown,
        }, -1)
        self.onLayoutFinish.append(self._start)

    # ------------------------------------------------------------ data
    def _start(self):
        self["cats"].selectionEnabled(True)
        self["items"].selectionEnabled(False)
        self._load_cache()
        self.refreshFeed()

    def _load_cache(self):
        try:
            self.feed = F.Feed.load(F.CACHE_FILE)
        except Exception:
            try:
                self.feed = F.Feed.load(os.path.join(PLUGIN_DIR, "index.json"))
            except Exception:
                self.feed = None
        self._refresh_all()

    def refreshFeed(self):
        self["status"].setText("Lecture du feed en ligne…")
        tmp = "/tmp/wacayoubpanel-index.json"
        cmd = "wget -q -T 20 -O %s %s" % (tmp, F.sh_quote(F.INDEX_URL + "?t=%d" % int(__import__("time").time())))
        self.async_console.ePopen(cmd, self._feed_done, tmp)

    def _feed_done(self, data, retval, tmp):
        try:
            if retval != 0:
                raise IOError("wget %s" % retval)
            fresh = F.Feed.load(tmp)
            if not os.path.isdir(F.CACHE_DIR):
                os.makedirs(F.CACHE_DIR)
            with open(F.CACHE_FILE, "w", encoding="utf-8") as fh:
                json.dump(fresh.data, fh, ensure_ascii=False)
            self.feed = fresh
            self["status"].setText("")
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

    def _refresh_all(self):
        self.installed = F.installed_packages()
        free = F.free_bytes("/")
        sub = "v%s" % VERSION
        if self.feed and self.feed.updated:
            sub += "  ·  feed %s" % self.feed.updated
        if free >= 0:
            sub += "  ·  libre %s" % _human(free)
        self["sub"].setText(sub)
        self._build_cats()
        self._build_items()

    def _build_cats(self):
        old = self["cats"].getSelectionIndex() if self.cat_ids else 0
        rows, self.cat_ids = [], []
        cats = [{"id": "all", "title": "Tout"}]
        if self.feed:
            cats += self.feed.categories
        for c in cats:
            items = self.feed.items_in(c["id"]) if self.feed else []
            n_upd = 0
            for it in items:
                if self.feed.item_state(it, self.installed, self.archs)[0] == F.ST_UPDATE:
                    n_upd += 1
            right = ("%d ▲" % n_upd) if n_upd else str(len(items))
            self.cat_ids.append(c["id"])
            rows.append([c["id"],
                         MultiContentEntryText(pos=(s(20), 0), size=(s(300), s(64)), font=0,
                                               flags=RT_HALIGN_LEFT | RT_VALIGN_CENTER, text=c.get("title", c["id"])),
                         MultiContentEntryText(pos=(s(300), 0), size=(s(100), s(64)), font=0,
                                               flags=RT_HALIGN_RIGHT | RT_VALIGN_CENTER, text=right,
                                               color=0xFFB020 if n_upd else C_DIM, color_sel=0xFFFFFF)])
        self["cats"].setList(rows)
        if rows:
            self["cats"].moveToIndex(min(old, len(rows) - 1))

    def _current_cat(self):
        i = self["cats"].getSelectionIndex()
        return self.cat_ids[i] if 0 <= i < len(self.cat_ids) else "all"

    def _build_items(self):
        old = self["items"].getSelectionIndex() if self["items"].list else 0
        rows = []
        if self.feed:
            for it in self.feed.items_in(self._current_cat()):
                st, txt = self.feed.item_state(it, self.installed, self.archs)
                kind = TYPE_LABEL.get(it.get("type"), "")
                rows.append([it,
                             MultiContentEntryText(pos=(s(20), s(4)), size=(s(50), s(44)), font=0,
                                                   flags=RT_HALIGN_LEFT | RT_VALIGN_CENTER, text=ICON[st], color=C_STATE[st], color_sel=C_STATE[st]),
                             MultiContentEntryText(pos=(s(70), s(4)), size=(s(820), s(44)), font=0,
                                                   flags=RT_HALIGN_LEFT | RT_VALIGN_CENTER, text=it.get("name", it["id"])),
                             MultiContentEntryText(pos=(s(900), s(4)), size=(s(440), s(44)), font=1,
                                                   flags=RT_HALIGN_RIGHT | RT_VALIGN_CENTER, text=txt, color=C_STATE[st], color_sel=C_STATE[st]),
                             MultiContentEntryText(pos=(s(70), s(46)), size=(s(1270), s(30)), font=1,
                                                   flags=RT_HALIGN_LEFT | RT_VALIGN_CENTER,
                                                   text=(kind + "  ·  " if kind else "") + it.get("summary", ""), color=C_DIM, color_sel=0xC9D4E3)])
        self["items"].setList(rows)
        if rows:
            self["items"].moveToIndex(min(old, len(rows) - 1))
        self._update_desc()

    def _current_item(self):
        cur = self["items"].getCurrent()
        return cur[0] if cur else None

    def _update_desc(self):
        it = self._current_item()
        if not it or not self.feed:
            self["desc"].setText("" if self.feed else "Aucune liste. Appuyez sur JAUNE pour lire le feed.")
            return
        parts = [it.get("description", it.get("summary", ""))]
        names = [p for p in it.get("packages", []) if p in self.feed.packages]
        size = sum(int(self.feed.packages[p].get("size", 0) or 0) for p in names)
        vers = ", ".join("%s %s" % (p.replace("enigma2-plugin-", ""), self.feed.packages[p]["version"]) for p in names)
        parts.append("Paquets : %s  ·  téléchargement %s" % (vers, _human(size)))
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
            self._build_items()

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
            self["items"].moveToIndex(0)
            self._build_items()

    def keyDown(self):
        if self.focus_items:
            self["items"].down()
            self._update_desc()
        else:
            self["cats"].down()
            self["items"].moveToIndex(0)
            self._build_items()

    def keyOk(self):
        if not self.focus_items:
            if self["items"].list:
                self._set_focus(True)
            return
        it = self._current_item()
        if not it:
            return
        st, _txt = self.feed.item_state(it, self.installed, self.archs)
        if st == F.ST_OK:
            choices = [("Réinstaller", "reinstall"), ("Supprimer", "remove"), ("Annuler", None)]
            self.session.openWithCallback(lambda c: self._choice(it, c), ChoiceBox,
                                          title="%s est déjà à jour." % it["name"], list=choices)
        else:
            self.keyInstall()

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
            self._install(it)

    def keyRemove(self):
        it = self._current_item()
        if it and self.focus_items:
            self._ask_remove(it)

    def keyUpdateAll(self):
        if not self.feed:
            return
        names = []
        for it in self.feed.items:
            if it.get("type") == "script":
                continue
            for p in self.feed.outdated(it, self.installed):
                if p not in names:
                    names.append(p)
        if not names:
            self.session.open(MessageBox, "Tout est à jour.", MessageBox.TYPE_INFO, timeout=4)
            return
        self._confirm_run("Mettre à jour %d paquet(s) ?\n%s" % (len(names), "\n".join(names)),
                          F.install_commands(self.feed, names), "Mise à jour")

    # ------------------------------------------------------------ actions
    def _install(self, it, reinstall=False):
        st, txt = self.feed.item_state(it, self.installed, self.archs)
        if st == F.ST_NA:
            self.session.open(MessageBox, "%s : %s." % (it["name"], txt), MessageBox.TYPE_ERROR, timeout=6)
            return
        if it.get("type") == "script":
            self._confirm_run("Lancer le script « %s » ?\n%s" % (it["name"], it.get("summary", "")),
                              F.script_commands(self.feed, it), it["name"], restart=False)
            return
        names = list(it["packages"]) if reinstall else self.feed.to_fetch(it, self.installed)
        if not names:
            self.session.open(MessageBox, "%s est déjà à jour." % it["name"], MessageBox.TYPE_INFO, timeout=4)
            return
        need = self.feed.install_size(names)
        free = F.free_bytes("/")
        if free >= 0 and need and need + 8 * 1024 * 1024 > free:
            self.session.open(MessageBox, "Pas assez de place : il faut %s, libre %s." % (_human(need), _human(free)),
                              MessageBox.TYPE_ERROR)
            return
        verb = "Réinstaller" if reinstall else ("Mettre à jour" if st == F.ST_UPDATE else "Installer")
        self._confirm_run("%s %s ?\n%s\nPlace utilisée : %s" % (verb, it["name"], "\n".join(names), _human(need)),
                          F.install_commands(self.feed, names, reinstall=reinstall), "%s %s" % (verb, it["name"]))

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
        if restart and before != self.installed:
            self.changed = True
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
        self.async_console.killAll()
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
