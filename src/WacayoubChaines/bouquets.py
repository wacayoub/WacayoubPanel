# -*- coding: utf-8 -*-
"""Wacayoub Chaînes - bouquet engine (no enigma2 imports: testable on a PC with a copy of /etc/enigma2).

Reads bouquets.tv / bouquets.radio, every userbouquet / subbouquet file and lamedb (names, providers),
edits them in memory, and saves only what changed, after a backup (undo = put the last backup back).
"""
import json
import os
import re
import shutil
import time
import unicodedata

E2 = "/etc/enigma2"
BACKUP_DIR = "/home/root/wacayoub-chaines"
KEEP_BACKUPS = 5
BOUQUET_RE = re.compile(r'FROM BOUQUET "([^"/]+)"')
SAFE_FILE = re.compile(r"^(userbouquet|subbouquet)\.[\w.+@()\- ]+\.(tv|radio)$")


def fold(s):
    s = unicodedata.normalize("NFKD", s or u"")
    return u"".join(c for c in s if not unicodedata.combining(c)).lower()


# ------------------------------------------------------------------ lamedb
class Services(object):
    """key (sid, tsid, onid, ns) -> (name, provider, service type)."""

    def __init__(self, root=E2):
        self.db = {}
        p5, p4 = os.path.join(root, "lamedb5"), os.path.join(root, "lamedb")
        try:
            if os.path.isfile(p5):
                self._v5(p5)
            if not self.db and os.path.isfile(p4):
                self._v4(p4)
        except (IOError, OSError, ValueError) as e:
            print("[WacayoubChaines] lamedb: %s" % e)

    def _v5(self, path):
        with open(path, encoding="utf-8", errors="replace") as fh:
            for line in fh:
                if not line.startswith("s:"):
                    continue
                head, _, rest = line.partition(",")
                f = head.split(":")
                if len(f) < 6:
                    continue
                m = re.match(r'"((?:[^"\\]|\\.)*)"(.*)', rest)
                name = m.group(1) if m else ""
                prov = re.search(r",p:([^,\n]*)", "," + (m.group(2) if m else rest))
                key = (int(f[1], 16), int(f[3], 16), int(f[4], 16), int(f[2], 16))
                self.db[key] = (name, prov.group(1) if prov else "", int(f[5]))

    def _v4(self, path):
        with open(path, encoding="utf-8", errors="replace") as fh:
            lines = fh.read().split("\n")
        try:
            i = lines.index("services") + 1
        except ValueError:
            return
        while i + 2 < len(lines) and lines[i] != "end":
            f = lines[i].split(":")
            if len(f) >= 5:
                prov = re.search(r"(?:^|,)p:([^,]*)", lines[i + 2])
                key = (int(f[0], 16), int(f[2], 16), int(f[3], 16), int(f[1], 16))
                self.db[key] = (lines[i + 1], prov.group(1) if prov else "", int(f[4]))
            i += 3

    def get(self, key):
        return self.db.get(key)


def sat_label(ns):
    pos = (ns >> 16) & 0xFFFF
    if pos == 0xEEEE:
        return u"Terrestre"
    if pos == 0xFFFF:
        return u"Câble"
    if pos > 3600 or pos == 0:
        return u""
    return (u"%.1f°E" % (pos / 10.0)) if pos <= 1800 else (u"%.1f°W" % ((3600 - pos) / 10.0))


# ------------------------------------------------------------------ entries
class Entry(object):
    __slots__ = ("ref", "desc", "extra", "kind")

    def __init__(self, ref, desc=None, extra=None):
        self.ref, self.desc, self.extra = ref, desc, extra or []
        self.kind = self._kind()

    def fields(self):
        return self.ref.split(":")

    def _kind(self):
        f = self.fields()
        if "FROM BOUQUET" in self.ref:
            return "bouquet"
        if len(f) > 1 and f[1] in ("64", "320"):
            return "marker"
        if len(f) > 10 and f[10] or "%3a" in self.ref.lower() or (f and f[0] in ("4097", "5001", "5002", "5003", "8193")):
            return "stream"
        return "service"

    def key(self):
        f = self.fields()
        try:
            return (int(f[3], 16), int(f[4], 16), int(f[5], 16), int(f[6], 16))
        except (IndexError, ValueError):
            return None

    def norm(self):
        return ":".join(self.fields()[:11]).upper().rstrip(":")

    def name(self, services):
        if self.desc:
            return self.desc
        k = self.kind
        if k == "stream":
            f = self.fields()
            return f[11] if len(f) > 11 and f[11] else u"Flux IPTV"
        if k == "bouquet":
            m = BOUQUET_RE.search(self.ref)
            return m.group(1) if m else u"?"
        if k == "marker":
            return u"—"
        s = services.get(self.key())
        return s[0] if s else u"(chaîne inconnue)"

    def info(self, services):
        k = self.kind
        if k == "stream":
            return u"IPTV"
        if k == "marker":
            return u"Séparateur"
        if k == "bouquet":
            return u"Sous-bouquet"
        key = self.key()
        s = services.get(key)
        if not s:
            return u"absente de la liste des chaînes"
        parts = [p for p in (s[1], sat_label(key[3]) if key else "", "HD" if s[2] in (17, 22, 25, 31, 32) else "") if p]
        return u"  ·  ".join(parts)

    def picon_names(self):
        f = self.fields()[:10]
        if len(f) < 10:
            return []
        if f[0] != "1":
            f[0] = "1"
        out = ["_".join(f).upper()]
        if f[2] != "1":
            g = list(f)
            g[2] = "1"
            out.append("_".join(g).upper())
        return out

    def text(self):
        out = "#SERVICE %s\n" % self.ref
        if self.desc is not None:
            out += "#DESCRIPTION %s\n" % self.desc
        for x in self.extra:
            out += x + "\n"
        return out


def marker(name, n):
    return Entry("1:64:%d:0:0:0:0:0:0:0::%s" % (n, name), name)


# ------------------------------------------------------------------ bouquets
STREAM_LINE = re.compile(r"^#SERVICE (?:4097|5001|5002|5003|8193):|^#SERVICE [^\n]*%3a//", re.M | re.I)
MARK_LINE = re.compile(r"^#SERVICE \d+:(?:64|320):", re.M)


class Bouquet(object):
    """Channels are parsed only when the bouquet is opened (fast start with hundreds of bouquets)."""

    def __init__(self, file, kind, name=u"", entries=None, header=None, depth=0):
        self.file, self.kind, self.name = file, kind, name
        self._entries = entries if entries is not None else []
        self._raw = None
        self.header = header or []
        self.depth = depth
        self.dirty = False

    @property
    def entries(self):
        if self._raw is not None:
            self._parse(self._raw)
        return self._entries

    @entries.setter
    def entries(self, value):
        self._raw = None
        self._entries = value

    def count(self):
        """Channels (no separators / sub-bouquets), without parsing."""
        if self._raw is not None:
            return self._raw.count("#SERVICE ") - len(MARK_LINE.findall(self._raw)) - self._raw.count("FROM BOUQUET")
        return len(self.channels())

    def children(self):
        if self._raw is not None:
            return BOUQUET_RE.findall(self._raw)
        return [m.group(1) for m in (BOUQUET_RE.search(e.ref) for e in self._entries if e.kind == "bouquet") if m]

    @classmethod
    def load(cls, root, file, kind, depth=0):
        b = cls(file, kind, depth=depth)
        with open(os.path.join(root, file), encoding="utf-8", errors="replace") as fh:
            raw = fh.read()
        m = re.match(r"#NAME ([^\r\n]*)", raw)
        b.name = m.group(1) if m else file
        b._raw = raw
        return b

    def _parse(self, raw):
        self._raw = None
        self._entries = []
        self.header = []
        name = None
        lines = raw.splitlines()
        b = self
        cur = None
        for line in lines:
            if line.startswith("#NAME ") and name is None and cur is None:
                name = line[6:]
            elif line.startswith("#SERVICE "):
                cur = Entry(line[9:])
                b._entries.append(cur)
            elif line.startswith("#DESCRIPTION ") and cur is not None and cur.desc is None:
                cur.desc = line[13:]
            elif line.strip():
                (cur.extra if cur is not None else b.header).append(line)

    def text(self):
        return "#NAME %s\n" % self.name + "".join(h + "\n" for h in self.header) + "".join(e.text() for e in self.entries)

    def channels(self):
        return [e for e in self.entries if e.kind in ("service", "stream")]

    def is_iptv(self):
        if self._raw is not None:
            n = self.count()
            return n > 0 and len(STREAM_LINE.findall(self._raw)) * 2 >= n
        ch = self.channels()
        return bool(ch) and sum(1 for e in ch if e.kind == "stream") * 2 >= len(ch)


class Library(object):
    def __init__(self, root=E2, backup_dir=BACKUP_DIR):
        self.root, self.backup_dir = root, backup_dir
        self.services = Services(root)
        self.tops = {"tv": [], "radio": []}     # [Entry] lines of bouquets.tv / .radio
        self.headers = {"tv": "#NAME User - Bouquets (TV)", "radio": "#NAME User - Bouquets (Radio)"}
        self.bouquets = {}                      # file -> Bouquet
        self.removed = set()
        self.tops_dirty = set()
        for kind in ("tv", "radio"):
            self._load_kind(kind)

    def _load_kind(self, kind):
        p = os.path.join(self.root, "bouquets." + kind)
        if not os.path.isfile(p):
            return
        with open(p, encoding="utf-8", errors="replace") as fh:
            lines = fh.read().splitlines()
        for line in lines:
            if line.startswith("#NAME"):
                self.headers[kind] = line
            elif line.startswith("#SERVICE "):
                e = Entry(line[9:])
                m = BOUQUET_RE.search(e.ref)
                if m and os.path.isfile(os.path.join(self.root, m.group(1))):
                    self.tops[kind].append(e)
                    self._load_tree(m.group(1), kind, 0)

    def _load_tree(self, file, kind, depth):
        if file in self.bouquets or depth > 4:
            return
        try:
            b = Bouquet.load(self.root, file, kind, depth)
        except (IOError, OSError):
            return
        self.bouquets[file] = b
        for child in b.children():
            if os.path.isfile(os.path.join(self.root, child)):
                self._load_tree(child, kind, depth + 1)

    # -------------------------------------------------------------- views
    def ordered(self, kind):
        """[Bouquet] top bouquets in order, each followed by its sub-bouquets."""
        out, seen = [], set()

        def walk(file):
            b = self.bouquets.get(file)
            if not b or file in seen:
                return
            seen.add(file)
            out.append(b)
            for child in b.children():
                walk(child)
        for e in self.tops[kind]:
            walk(BOUQUET_RE.search(e.ref).group(1))
        return out

    def parent_of(self, b):
        for p in self.bouquets.values():
            if b.file in p.children():
                return p
        return None

    def dirty(self):
        return bool(self.removed or self.tops_dirty or any(b.dirty for b in self.bouquets.values()))

    # -------------------------------------------------------------- edits
    @staticmethod
    def move_block(b, idx, delta):
        """Move entries idx (sorted list) by delta positions as one block; returns the new indexes."""
        block = [b.entries[i] for i in idx]
        rest = [e for i, e in enumerate(b.entries) if i not in set(idx)]
        pos = max(0, min(len(rest), idx[0] + delta))
        b.entries = rest[:pos] + block + rest[pos:]
        b.dirty = True
        return list(range(pos, pos + len(block)))

    @staticmethod
    def gather(b, idx):
        """Bring marked entries together at the first one; returns their new indexes."""
        return Library.move_block(b, sorted(idx), 0)

    def delete(self, b, idx):
        s = set(idx)
        b.entries = [e for i, e in enumerate(b.entries) if i not in s]
        b.dirty = True

    def copy_to(self, b, idx, target, move=False, at_start=False):
        have = set(e.norm() for e in target.entries)
        new = []
        for i in sorted(idx):
            e = b.entries[i]
            if e.kind in ("service", "stream") and e.norm() not in have:
                new.append(Entry(e.ref, e.desc, list(e.extra)))
                have.add(e.norm())
        added = len(new)
        target.entries = (new + target.entries) if at_start else (target.entries + new)
        target.dirty = True
        if move:
            self.delete(b, idx)
        return added

    def new_bouquet(self, name, kind="tv", prefix="wch"):
        slug = re.sub(r"[^a-z0-9]+", "_", fold(name)).strip("_")[:24] or "bouquet"
        file, n = "userbouquet.%s_%s.%s" % (prefix, slug, kind), 1
        while file in self.bouquets or os.path.exists(os.path.join(self.root, file)) and file not in self.removed:
            n += 1
            file = "userbouquet.%s_%s%d.%s" % (prefix, slug, n, kind)
        b = Bouquet(file, kind, name)
        b.dirty = True
        self.bouquets[file] = b
        self.removed.discard(file)
        self.tops[kind].append(Entry('1:7:%d:0:0:0:0:0:0:0:FROM BOUQUET "%s" ORDER BY bouquet' % (1 if kind == "tv" else 2, file)))
        self.tops_dirty.add(kind)
        return b

    def delete_bouquet(self, b):
        for sub in [x for x in self.ordered(b.kind) if self.parent_of(x) is b]:
            self.delete_bouquet(sub)
        tag = '"%s"' % b.file
        before = len(self.tops[b.kind])
        self.tops[b.kind] = [e for e in self.tops[b.kind] if tag not in e.ref]
        if len(self.tops[b.kind]) != before:
            self.tops_dirty.add(b.kind)
        p = self.parent_of(b)
        if p:
            p.entries = [e for e in p.entries if tag not in e.ref]
            p.dirty = True
        self.bouquets.pop(b.file, None)
        if os.path.exists(os.path.join(self.root, b.file)):
            self.removed.add(b.file)

    def move_top(self, b, delta):
        """Reorder a top bouquet in bouquets.tv; False when it is a sub-bouquet."""
        tops = self.tops[b.kind]
        i = [n for n, e in enumerate(tops) if ('"%s"' % b.file) in e.ref]
        if not i:
            return False
        i = i[0]
        j = max(0, min(len(tops) - 1, i + delta))
        tops.insert(j, tops.pop(i))
        self.tops_dirty.add(b.kind)
        return True

    # -------------------------------------------------------------- precise moves
    @staticmethod
    def rest_pos_of_number(b, idx, n):
        """Position (in the list without the block idx) where the block lands to become channel number n."""
        s = set(idx)
        rest = [e for i, e in enumerate(b.entries) if i not in s]
        count = 0
        for p, e in enumerate(rest):
            if e.kind in ("service", "stream"):
                count += 1
                if count == n:
                    return p
        return len(rest)

    @staticmethod
    def rest_pos_after(b, idx, marker_index):
        """Position (in the list without the block) just after the entry marker_index."""
        s = set(idx)
        return sum(1 for i in range(marker_index + 1) if i not in s)

    def move_to(self, b, idx, pos):
        """Block idx to position pos of the list without the block; returns the new indexes."""
        idx = sorted(idx)
        return self.move_block(b, idx, pos - idx[0])

    @staticmethod
    def swap(b, i, j):
        b.entries[i], b.entries[j] = b.entries[j], b.entries[i]
        b.dirty = True

    @staticmethod
    def reverse(b, idx):
        idx = sorted(idx)
        items = [b.entries[i] for i in idx][::-1]
        for i, e in zip(idx, items):
            b.entries[i] = e
        b.dirty = True

    def paste(self, target, pos, entries, src=None):
        """Insert entries at pos in target (duplicates already there are skipped). src: bouquet to take them out of (cut).
        Returns (number inserted, index of the first one)."""
        ids = set(id(e) for e in entries) if src is not None else set()
        later = [x for x in target.entries[max(0, pos):] if id(x) not in ids]
        anchor = later[0] if later else None
        if src is not None:
            src.entries = [e for e in src.entries if id(e) not in ids]
            src.dirty = True
        have = set(e.norm() for e in target.entries)
        new = [e if src is not None else Entry(e.ref, e.desc, list(e.extra)) for e in entries
               if e.kind == "marker" or e.norm() not in have]
        if anchor is not None and any(x is anchor for x in target.entries):
            pos = [i for i, x in enumerate(target.entries) if x is anchor][0]
        else:
            pos = len(target.entries)
        target.entries = target.entries[:pos] + new + target.entries[pos:]
        target.dirty = True
        return len(new), pos

    @staticmethod
    def snapshot(bouquets):
        return dict((b.file, (b, list(b.entries), b.dirty)) for b in bouquets if b is not None)

    @staticmethod
    def restore(snap):
        for _f, (b, entries, dirty) in snap.items():
            b.entries = list(entries)
            b.dirty = dirty

    def move_tops(self, kind, files, delta):
        """Move several top bouquets as one block (kept in their order). Returns False if none is a top bouquet."""
        tops = self.tops[kind]
        tags = ['"%s"' % f for f in files]
        idx = [i for i, e in enumerate(tops) if any(t in e.ref for t in tags)]
        if not idx:
            return False
        block = [tops[i] for i in idx]
        rest = [e for i, e in enumerate(tops) if i not in set(idx)]
        pos = max(0, min(len(rest), idx[0] + delta))
        self.tops[kind] = rest[:pos] + block + rest[pos:]
        self.tops_dirty.add(kind)
        return True

    def merge(self, sources, name, keep=True):
        """New bouquet with every channel of sources (in order, without duplicates). keep=False deletes the sources."""
        kind = sources[0].kind
        tag = '"%s"' % sources[0].file
        pos = [i for i, e in enumerate(self.tops[kind]) if tag in e.ref]
        target = self.new_bouquet(name, kind)
        if pos:  # the merged bouquet takes the place of the first one
            self.tops[kind].insert(pos[0], self.tops[kind].pop())
        for b in sources:
            self.copy_to(b, range(len(b.entries)), target)
        if not keep:
            for b in sources:
                if b.file in self.bouquets:
                    self.delete_bouquet(b)
        return target

    def select(self, b, how, text=u""):
        """Indexes of the entries of b matching a smart selection."""
        out = []
        q = [w for w in fold(text).split() if w]
        for i, e in enumerate(b.entries):
            if e.kind not in ("service", "stream"):
                continue
            if how == "name":
                n = fold(e.name(self.services))
                ok = bool(q) and all(w in n for w in q)
            elif how == "hd":
                n = fold(e.name(self.services))
                ok = bool(re.search(r"\b(4k|uhd|fhd|hd)\b", n)) or e.info(self.services).endswith("HD")
            elif how == "sd":
                n = fold(e.name(self.services))
                ok = not (re.search(r"\b(4k|uhd|fhd|hd)\b", n) or e.info(self.services).endswith("HD"))
            elif how == "iptv":
                ok = e.kind == "stream"
            elif how == "sat":
                ok = e.kind == "service"
            elif how == "dead":
                ok = e.kind == "service" and bool(self.services.db) and not self.services.get(e.key())
            else:
                ok = False
            if ok:
                out.append(i)
        return out

    def rename(self, b, name):
        b.name = name
        b.dirty = True

    def add_marker(self, b, at, name):
        n = 1 + max([int(e.fields()[2]) for e in b.entries if e.kind == "marker" and e.fields()[2].isdigit()] or [0])
        b.entries.insert(at, marker(name, n))
        b.dirty = True

    # -------------------------------------------------------------- smart tools
    def sort(self, b, how="name"):
        """Sort inside each section (between separators): by name, or HD / 4K first then name."""
        def k(e):
            n = fold(e.name(self.services))
            if how == "hd":
                hd = 0 if re.search(r"\b(4k|uhd)\b", n) else 1 if re.search(r"\b(fhd|hd)\b", n) or "hd" in e.info(self.services) else 2
                return (hd, n)
            return n
        out, sec = [], []
        for e in b.entries + [None]:
            if e is None or e.kind == "marker":
                out += sorted(sec, key=k)
                sec = []
                if e is not None:
                    out.append(e)
            else:
                sec.append(e)
        b.entries = out
        b.dirty = True

    def duplicates(self, b):
        seen, out = set(), []
        for i, e in enumerate(b.entries):
            if e.kind in ("service", "stream"):
                n = e.norm()
                if n in seen:
                    out.append(i)
                seen.add(n)
        return out

    def dead(self, b):
        if not self.services.db:
            return []
        return [i for i, e in enumerate(b.entries) if e.kind == "service" and not self.services.get(e.key())]

    def empty_bouquets(self):
        return [b for b in self.bouquets.values() if not b.entries]

    def search(self, text, kind=None):
        q = [w for w in fold(text).split() if w]
        out = []
        for b in (self.ordered(kind) if kind else self.ordered("tv") + self.ordered("radio")):
            for i, e in enumerate(b.entries):
                if e.kind in ("service", "stream") and all(w in fold(e.name(self.services)) for w in q):
                    out.append((b, i))
        return out

    THEMES = [
        ("sport", u"★ Sport", r"sport|bein|espn|eurosport|dazn|arena|ssc|al ?kass|ad sports|setanta|golf|\bf1\b|foot|racing|motor|nba|ufc"),
        ("enfants", u"★ Enfants", r"kids|junior|cartoon|disney|nick|baby|gulli|tiji|boomerang|spacetoon|jeem|majid|piwi|toon|cbeebies|canal ?j\b"),
        ("info", u"★ Info", r"news|\binfo|jazeera|cnn|euronews|arabiya|alarabiya|\blci\b|bfm|cnews|i24|medi ?1|france ?24|al hadath|skynews|sky news"),
        ("docs", u"★ Documentaires", r"discovery|national geographic|nat ?geo|history|animal|plan[eè]te|science|ushuaia|\bdoc"),
        ("musique", u"★ Musique", r"music|musique|\bmtv\b|mezzo|rotana clip|trace|melody|mazzika|nrj hits|\bhits?\b"),
        ("cinema", u"★ Cinéma & Séries", r"movie|cin[eé]ma|\bcine|film|series|s[eé]ries|action|drama|\bhbo\b|\bosn\b|\btcm\b|paramount|syfy|\bocs\b|mbc ?(2|max|action|drama)"),
        ("religion", u"★ Religion", r"quran|coran|iqraa|islam|sunna|majd|makkah|mecca|azhari|\bkto\b"),
    ]

    def themes(self, kind="tv", include_iptv=False):
        """Builds (or rebuilds) the '★ theme' bouquets from every channel, without touching the others.
        Returns {theme name: number of channels}."""
        found = dict((t[0], []) for t in self.THEMES)
        seen = set()
        for b in self.ordered(kind):
            if b.file.startswith("userbouquet.wch_theme_") or (b.is_iptv() and not include_iptv):
                continue
            for e in b.entries:
                if e.kind not in ("service", "stream") or e.norm() in seen:
                    continue
                n = fold(e.name(self.services))
                for tid, _name, rx in self.THEMES:
                    if re.search(rx, n):
                        found[tid].append(Entry(e.ref, e.desc, list(e.extra)))
                        seen.add(e.norm())
                        break
        out = {}
        for tid, name, _rx in self.THEMES:
            file = "userbouquet.wch_theme_%s.%s" % (tid, kind)
            b = self.bouquets.get(file)
            if not found[tid]:
                if b:
                    self.delete_bouquet(b)
                continue
            if not b:
                b = Bouquet(file, kind, name)
                self.bouquets[file] = b
                self.removed.discard(file)
                line = Entry('1:7:%d:0:0:0:0:0:0:0:FROM BOUQUET "%s" ORDER BY bouquet' % (1 if kind == "tv" else 2, file))
                # themes go first, in their order
                n = sum(1 for e in self.tops[kind] if "userbouquet.wch_theme_" in e.ref)
                self.tops[kind].insert(n, line)
                self.tops_dirty.add(kind)
            b.entries = found[tid]
            b.dirty = True
            self.sort(b, "hd")
            out[name] = len(found[tid])
        return out

    # -------------------------------------------------------------- save / undo
    def save(self):
        """Writes what changed; the previous files go to a new backup folder. Returns (files written, backup dir)."""
        files = [b.file for b in self.bouquets.values() if b.dirty]
        files += ["bouquets.%s" % k for k in self.tops_dirty]
        if not files and not self.removed:
            return 0, None
        stamp = time.strftime("%Y%m%d-%H%M%S")
        bdir = os.path.join(self.backup_dir, "sauvegarde-" + stamp)
        os.makedirs(bdir)
        saved, added = [], []
        for f in files + sorted(self.removed):
            p = os.path.join(self.root, f)
            if os.path.isfile(p):
                shutil.copy2(p, os.path.join(bdir, f))
                saved.append(f)
            else:
                added.append(f)
        for b in self.bouquets.values():
            if b.dirty:
                self._write(b.file, b.text())
                b.dirty = False
        for k in sorted(self.tops_dirty):
            self._write("bouquets." + k, "\n".join([self.headers[k]] + ["#SERVICE " + e.ref for e in self.tops[k]]) + "\n")
        for f in self.removed:
            if SAFE_FILE.match(f):
                try:
                    os.remove(os.path.join(self.root, f))
                except OSError:
                    pass
        with open(os.path.join(bdir, "sauvegarde.json"), "w", encoding="utf-8") as fh:
            json.dump({"date": time.strftime("%d/%m/%Y %H:%M"), "saved": saved, "added": added}, fh, ensure_ascii=False)
        n = len(files) + len(self.removed)
        self.tops_dirty, self.removed = set(), set()
        old = sorted(d for d in os.listdir(self.backup_dir) if d.startswith("sauvegarde-"))
        for d in old[:-KEEP_BACKUPS]:
            shutil.rmtree(os.path.join(self.backup_dir, d), ignore_errors=True)
        return n, bdir

    def _write(self, file, text):
        p = os.path.join(self.root, file)
        with open(p + ".wch", "w", encoding="utf-8") as fh:
            fh.write(text)
        os.replace(p + ".wch", p)

    def last_backup(self):
        try:
            d = sorted(x for x in os.listdir(self.backup_dir) if x.startswith("sauvegarde-"))[-1]
            with open(os.path.join(self.backup_dir, d, "sauvegarde.json"), encoding="utf-8") as fh:
                return os.path.join(self.backup_dir, d), json.load(fh)
        except (OSError, IndexError, ValueError):
            return None, None

    def undo(self):
        """Puts back the files of the last save. Returns the number of files, or -1 if there is none."""
        d, info = self.last_backup()
        if not d:
            return -1
        for f in info.get("added", []):
            if SAFE_FILE.match(f):
                try:
                    os.remove(os.path.join(self.root, f))
                except OSError:
                    pass
        for f in info.get("saved", []):
            shutil.copy2(os.path.join(d, f), os.path.join(self.root, f))
        shutil.rmtree(d, ignore_errors=True)
        return len(info.get("saved", [])) + len(info.get("added", []))
