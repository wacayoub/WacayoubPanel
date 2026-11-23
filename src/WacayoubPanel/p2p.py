# -*- coding: utf-8 -*-
"""Partage LAN: send channels, IPTV and softcam settings from one receiver to another on the same network.

Sender:   python3 p2p.py serve chaines,iptv,softcam      (code in WP2P_CODE; status in STATUS_FILE)
Receiver: python3 p2p.py find                             (one JSON line per receiver found)
          python3 p2p.py receive IP PORT                  (code in WP2P_CODE; backup, then apply)
          python3 p2p.py undo                             (puts back what the last exchange replaced)

Safety:
- the sender only serves while its screen is open (10 minutes at most) and stops after one transfer;
- only local network addresses (192.168.x, 10.x, 172.16-31.x) are answered;
- the receiver must prove it knows the 8-digit code shown on the sender before getting anything,
  3 wrong codes stop the sender; the archive is encrypted and authenticated with a key made from the code;
- the receiver only writes known file names in known folders, and saves what it replaces first.
No enigma2 imports here.
"""
import hashlib
import hmac
import io
import json
import os
import re
import shutil
import socket
import sys
import tarfile
import time

PORT = 47811
DISCO = 47812
LIFETIME = 600
E2 = "/etc/enigma2"
WORK = "/tmp/wacayoub-p2p"
STATUS_FILE = WORK + "/status.json"
BACKUPS = "/home/root/wacayoub-p2p"
KINDS = ("chaines", "iptv", "softcam")
KIND_NAMES = {"chaines": u"chaînes", "iptv": u"IPTV", "softcam": u"softcam"}
# IPTV plugins whose settings folder travels with the IPTV bouquets
IPTV_DIRS = ("iptvbouquetai", "bouquetmakerxtream", "xstreamity", "estalker", "e-stalker", "jediepgxtream")
SOFTCAM_DIRS = ("/etc/tuxbox/config", "/usr/keys")
SOFTCAM_FILES = ("/etc/CCcam.cfg",)
SKIP_RE = re.compile(r"(cache|logo|backup|\.log$|\.pid$|\.tmp$|\.bak$|\.before-)", re.I)
BOUQUET_RE = re.compile(r'FROM BOUQUET "([^"/]+)"')
NAME_OK = re.compile(r"^[\w.+@()\- ]+$")
STREAM_RE = re.compile(r"^#SERVICE (4097|5001|5002|5003|8193):|^#SERVICE [^\n]*%3a//", re.M)
MAX_FILE = 4 << 20


def say(msg):
    print(msg)
    sys.stdout.flush()


def private(ip):
    ip = ip.replace("::ffff:", "")
    try:
        a = [int(x) for x in ip.split(".")]
    except ValueError:
        return False
    return len(a) == 4 and (a[0] == 10 or (a[0] == 192 and a[1] == 168) or (a[0] == 172 and 16 <= a[1] <= 31)
                            or (a[0] == 169 and a[1] == 254))


def my_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("192.168.255.255", 9))
        return s.getsockname()[0]
    except OSError:
        return ""
    finally:
        s.close()


def box_name():
    for p in ("/proc/stb/info/vumodel", "/proc/stb/info/model", "/proc/stb/info/boxtype"):
        try:
            with open(p) as fh:
                v = fh.read().strip()
            if v:
                return ("Vu+ " + v.capitalize()) if "vumodel" in p else v.upper()
        except (IOError, OSError):
            pass
    return socket.gethostname()


# ------------------------------------------------------------------ what is sent
def _read(p):
    with open(p, encoding="utf-8", errors="replace") as fh:
        return fh.read()


def bouquet_tree(name, seen=None):
    """[name, children...] of a bouquet file (FROM BOUQUET references, recursive)."""
    seen = seen if seen is not None else []
    if name in seen or not NAME_OK.match(name) or not os.path.isfile(os.path.join(E2, name)):
        return seen
    seen.append(name)
    for child in BOUQUET_RE.findall(_read(os.path.join(E2, name))):
        bouquet_tree(child, seen)
    return seen


def is_iptv(tree):
    """A bouquet (with its sub-bouquets) is IPTV when most of its channels are streams."""
    total = streams = 0
    for n in tree:
        text = _read(os.path.join(E2, n))
        services = [l for l in text.splitlines() if l.startswith("#SERVICE ") and "FROM BOUQUET" not in l
                    and not l.startswith("#SERVICE 1:64:")]
        total += len(services)
        streams += len(STREAM_RE.findall("\n".join(services)))
    return total > 0 and streams * 2 >= total


def top_bouquets():
    """{'tv'/'radio': [(top line, tree, iptv)]} in the order of bouquets.tv / bouquets.radio."""
    out = {}
    for kind in ("tv", "radio"):
        rows = []
        p = os.path.join(E2, "bouquets." + kind)
        if os.path.isfile(p):
            for line in _read(p).splitlines():
                m = BOUQUET_RE.search(line)
                if m and line.startswith("#SERVICE"):
                    tree = bouquet_tree(m.group(1))
                    if tree:
                        rows.append((line, tree, is_iptv(tree)))
        out[kind] = rows
    return out


def _walk(root):
    for dp, _dn, fns in os.walk(root):
        for fn in fns:
            p = os.path.join(dp, fn)
            if not os.path.islink(p) and not SKIP_RE.search(p) and os.path.getsize(p) <= MAX_FILE:
                yield p


def collect(kinds):
    """(manifest, {archive name: absolute path})."""
    files, man = {}, {"app": "wacayoub-p2p", "v": 1, "from": box_name(), "date": time.strftime("%d/%m/%Y %H:%M"),
                      "kinds": list(kinds), "tops": {}, "counts": {}}
    tops = top_bouquets() if ("chaines" in kinds or "iptv" in kinds) else {}
    for k in ("chaines", "iptv"):
        if k not in kinds:
            continue
        want_iptv = k == "iptv"
        n = 0
        man["tops"][k] = {}
        for kind, rows in tops.items():
            man["tops"][k][kind] = []
            for line, tree, iptv in rows:
                if iptv != want_iptv:
                    continue
                man["tops"][k][kind].append(line)
                n += 1
                for name in tree:
                    files["%s/%s" % (k, name)] = os.path.join(E2, name)
        if k == "chaines":
            for name in ("lamedb", "lamedb5"):
                if os.path.isfile(os.path.join(E2, name)):
                    files["chaines/" + name] = os.path.join(E2, name)
        else:
            for d in IPTV_DIRS:
                for p in _walk(os.path.join(E2, d)):
                    files["iptv-conf/" + os.path.relpath(p, E2)] = p
        man["counts"][k] = n
    if "softcam" in kinds:
        n = 0
        for root in SOFTCAM_DIRS:
            for p in _walk(root):
                files["softcam" + p] = p
                n += 1
        for p in SOFTCAM_FILES:
            if os.path.isfile(p):
                files["softcam" + p] = p
                n += 1
        try:
            man["cam"] = os.path.basename(os.readlink("/etc/init.d/softcam")).replace("softcam.", "")
        except OSError:
            man["cam"] = ""
        man["counts"]["softcam"] = n
    return man, files


def pack(man, files):
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w:gz") as tar:
        data = json.dumps(man, ensure_ascii=False).encode("utf-8")
        ti = tarfile.TarInfo("manifest.json")
        ti.size = len(data)
        tar.addfile(ti, io.BytesIO(data))
        for arc, path in sorted(files.items()):
            tar.add(path, arc, recursive=False)
    return buf.getvalue()


# ------------------------------------------------------------------ crypto (code -> keys)
def keys(code, salt):
    k = hashlib.pbkdf2_hmac("sha256", code.encode("ascii"), salt, 100000, 96)
    return k[:32], k[32:64], k[64:]  # proof, encryption, integrity


def _stream(key, nonce, n):
    return hashlib.shake_256(key + nonce).digest(n)


def _xor(a, b):
    return (int.from_bytes(a, "big") ^ int.from_bytes(b, "big")).to_bytes(len(a), "big")


def seal(blob, enc, mac):
    nonce = os.urandom(16)
    ct = _xor(blob, _stream(enc, nonce, len(blob)))
    return nonce + ct + hmac.new(mac, nonce + ct, hashlib.sha256).digest()


def unseal(data, enc, mac):
    nonce, ct, tag = data[:16], data[16:-32], data[-32:]
    if not hmac.compare_digest(tag, hmac.new(mac, nonce + ct, hashlib.sha256).digest()):
        raise ValueError("bad code or damaged transfer")
    return _xor(ct, _stream(enc, nonce, len(ct)))


# ------------------------------------------------------------------ sender
def status(**kw):
    os.makedirs(WORK, exist_ok=True)
    kw["time"] = int(time.time())
    with open(STATUS_FILE + ".tmp", "w", encoding="utf-8") as fh:
        json.dump(kw, fh, ensure_ascii=False)
    os.replace(STATUS_FILE + ".tmp", STATUS_FILE)


def serve(kinds):
    import threading
    from http.server import BaseHTTPRequestHandler, HTTPServer
    code = os.environ.get("WP2P_CODE", "")
    if not re.match(r"^\d{8}$", code):
        status(state="error", text=u"code invalide")
        return 2
    status(state="prepare", text=u"Préparation…")
    man, files = collect(kinds)
    blob = pack(man, files)
    salt, challenge = os.urandom(16), os.urandom(16)
    k_proof, k_enc, k_mac = keys(code, salt)
    sealed = seal(blob, k_enc, k_mac)
    info = {"app": "wacayoub-p2p", "v": 1, "name": man["from"], "ip": my_ip(), "port": PORT, "kinds": man["kinds"],
            "counts": man["counts"], "size": len(sealed)}
    hello = dict(info, salt=salt.hex(), challenge=challenge.hex())
    st = {"wrong": 0, "done": False}

    class H(BaseHTTPRequestHandler):
        def log_message(self, *a):
            pass

        def _send(self, code_, body, ctype="application/json"):
            self.send_response(code_)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self):
            if not private(self.client_address[0]) or st["done"]:
                return self._send(403, b"{}")
            if self.path == "/hello":
                return self._send(200, json.dumps(hello).encode("utf-8"))
            m = re.match(r"^/data\?proof=([0-9a-f]{64})$", self.path)
            if not m:
                return self._send(404, b"{}")
            good = hmac.new(k_proof, challenge, hashlib.sha256).hexdigest()
            if not hmac.compare_digest(m.group(1), good):
                st["wrong"] += 1
                status(state="waiting" if st["wrong"] < 3 else "locked", wrong=st["wrong"], text=u"Code faux reçu de %s" % self.client_address[0], **info)
                if st["wrong"] >= 3:
                    st["done"] = True
                return self._send(403, b'{"error":"code"}')
            status(state="sending", text=u"Envoi vers %s…" % self.client_address[0], **info)
            self._send(200, sealed, "application/octet-stream")
            st["done"] = True
            status(state="sent", text=u"Envoyé à %s" % self.client_address[0], **info)

    srv = HTTPServer(("0.0.0.0", PORT), H)
    srv.timeout = 1

    def disco():
        u = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        u.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        u.bind(("0.0.0.0", DISCO))
        u.settimeout(1)
        while not st["done"]:
            try:
                data, addr = u.recvfrom(256)
            except socket.timeout:
                continue
            except OSError:
                break
            if data.startswith(b"WACAYOUB-P2P?") and private(addr[0]):
                u.sendto(json.dumps(info).encode("utf-8"), addr)
        u.close()

    threading.Thread(target=disco, daemon=True).start()
    status(state="waiting", wrong=0, text=u"En attente de l'autre récepteur", **info)
    end = time.time() + LIFETIME
    while not st["done"] and time.time() < end:
        srv.handle_request()
    if not st["done"]:
        status(state="expired", text=u"Temps écoulé (10 min)", **info)
    time.sleep(1)
    srv.server_close()
    return 0


# ------------------------------------------------------------------ receiver
def find(wait=2.5):
    u = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    u.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    u.settimeout(0.3)
    me = my_ip()
    targets = ["255.255.255.255"]
    if me.count(".") == 3:
        targets.append(me.rsplit(".", 1)[0] + ".255")
    seen = {}
    end = time.time() + wait
    nxt = 0
    while time.time() < end:
        if time.time() >= nxt:
            for t in targets:
                try:
                    u.sendto(b"WACAYOUB-P2P?", (t, DISCO))
                except OSError:
                    pass
            nxt = time.time() + 0.8
        try:
            data, addr = u.recvfrom(4096)
        except (socket.timeout, OSError):
            continue
        try:
            d = json.loads(data.decode("utf-8"))
        except ValueError:
            continue
        if d.get("app") == "wacayoub-p2p" and addr[0] != me and private(addr[0]) and addr[0] not in seen:
            d["ip"] = addr[0]
            seen[addr[0]] = d
            print(json.dumps(d, ensure_ascii=False))
            sys.stdout.flush()
    u.close()
    return 0


def _get(url, timeout=30):
    import urllib.request
    with urllib.request.urlopen(url, timeout=timeout) as r:
        return r.read()


def safe_target(arc, kinds):
    """Where an archive member may be written on this receiver, or None."""
    parts = arc.split("/")
    if any(p in ("", ".", "..") for p in parts):
        return None
    head = parts[0]
    if head in ("chaines", "iptv") and head in kinds and len(parts) == 2:
        n = parts[1]
        if NAME_OK.match(n) and (n in ("lamedb", "lamedb5") and head == "chaines" or
                                 re.match(r"^(userbouquet|subbouquet|alternatives)\..+\.(tv|radio)$", n)):
            return os.path.join(E2, n)
        return None
    if head == "iptv-conf" and "iptv" in kinds and len(parts) >= 3 and parts[1] in IPTV_DIRS:
        return os.path.join(E2, *parts[1:])
    if head == "softcam" and "softcam" in kinds:
        p = "/" + "/".join(parts[1:])
        if p in SOFTCAM_FILES or any(p.startswith(d + "/") for d in SOFTCAM_DIRS):
            return p
    return None


class Backup(object):
    def __init__(self):
        self.dir = os.path.join(BACKUPS, time.strftime("echange-%Y%m%d-%H%M%S"))
        os.makedirs(os.path.join(self.dir, "files"))
        self.saved, self.added = [], []

    def touch(self, path):
        """Call before writing or deleting path."""
        if path in self.saved or path in self.added:
            return
        if os.path.isfile(path):
            dst = os.path.join(self.dir, "files", path.lstrip("/"))
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            shutil.copy2(path, dst)
            self.saved.append(path)
        else:
            self.added.append(path)

    def close(self, info):
        with open(os.path.join(self.dir, "backup.json"), "w", encoding="utf-8") as fh:
            json.dump(dict(info, saved=self.saved, added=self.added), fh, ensure_ascii=False, indent=0)
        old = sorted(d for d in os.listdir(BACKUPS) if d.startswith("echange-"))
        for d in old[:-3]:
            shutil.rmtree(os.path.join(BACKUPS, d), ignore_errors=True)


def _write(bk, path, data):
    bk.touch(path)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path + ".wp2p", "wb") as fh:
        fh.write(data)
    os.replace(path + ".wp2p", path)


def _top_file(kind_file, lines, header):
    return "\n".join([header] + lines) + "\n"


def receive(ip, port):
    code = os.environ.get("WP2P_CODE", "")
    if not private(ip) or not re.match(r"^\d{8}$", code):
        say(u"ERREUR : adresse ou code invalide")
        return 2
    base = "http://%s:%d" % (ip, int(port))
    say(u">>> Connexion à %s" % ip)
    try:
        hello = json.loads(_get(base + "/hello", 10).decode("utf-8"))
    except Exception as e:
        say(u"ERREUR : l'autre récepteur ne répond pas (%s). Sur lui : Partage LAN → Envoyer." % e)
        return 1
    k_proof, k_enc, k_mac = keys(code, bytes.fromhex(hello["salt"]))
    proof = hmac.new(k_proof, bytes.fromhex(hello["challenge"]), hashlib.sha256).hexdigest()
    say(u">>> Réception depuis %s (%d Ko)" % (hello.get("name", ip), hello.get("size", 0) // 1024))
    try:
        data = _get(base + "/data?proof=" + proof, 120)
    except Exception as e:
        if "403" in str(e):
            say(u"ERREUR : code faux. Après 3 codes faux, l'envoi s'arrête sur l'autre récepteur.")
        else:
            say(u"ERREUR : transfert interrompu (%s)" % e)
        return 1
    try:
        blob = unseal(data, k_enc, k_mac)
    except ValueError:
        say(u"ERREUR : transfert abîmé, rien n'a été changé")
        return 1
    return apply(blob)


def apply(blob):
    tar = tarfile.open(fileobj=io.BytesIO(blob), mode="r:gz")
    members = {m.name: m for m in tar.getmembers() if m.isfile()}
    man = json.loads(tar.extractfile(members.pop("manifest.json")).read().decode("utf-8"))
    kinds = [k for k in man.get("kinds", []) if k in KINDS]
    say(u">>> Reçu de %s (%s) : %s" % (man.get("from", "?"), man.get("date", ""), ", ".join(KIND_NAMES[k] for k in kinds)))
    content = {}
    refused = 0
    for name, m in members.items():
        target = safe_target(name, kinds)
        if not target:
            refused += 1
            continue
        content[name] = (target, tar.extractfile(m).read())
    if refused:
        say(u"    %d fichier(s) inattendu(s) ignoré(s)" % refused)
    bk = Backup()
    mine = top_bouquets() if ("chaines" in kinds or "iptv" in kinds) else {}
    incoming = set(t for t, _d in content.values())
    if "chaines" in kinds:
        # my satellite bouquets leave (saved), the sender's come in; my IPTV bouquets stay
        keep = set(n for rows in mine.values() for _l, tree, iptv in rows if iptv for n in tree)
        for kind, rows in mine.items():
            for _line, tree, iptv in rows:
                if not iptv:
                    for n in tree:
                        p = os.path.join(E2, n)
                        if p not in incoming and n not in keep and os.path.isfile(p):
                            bk.touch(p)
                            os.remove(p)
    for name, (target, data) in sorted(content.items()):
        _write(bk, target, data)
    n_files = len(content)
    for kind in ("tv", "radio"):
        p = os.path.join(E2, "bouquets." + kind)
        header = "#NAME User - Bouquets (%s)" % ("TV" if kind == "tv" else "Radio")
        if os.path.isfile(p):
            first = _read(p).splitlines()[:1]
            if first and first[0].startswith("#NAME"):
                header = first[0]
        cur = [line for line, _t, _i in mine.get(kind, [])]
        if "chaines" in kinds:
            sat = man["tops"].get("chaines", {}).get(kind, [])
            cur = sat + [line for line, _t, iptv in mine.get(kind, []) if iptv and line not in sat]
        if "iptv" in kinds:
            cur += [l for l in man["tops"].get("iptv", {}).get(kind, []) if l not in cur]
        if "chaines" in kinds or "iptv" in kinds:
            _write(bk, p, (_top_file(kind, cur, header)).encode("utf-8"))
    for k in kinds:
        say(u"    %s : %d %s" % (KIND_NAMES[k], man["counts"].get(k, 0), u"fichier(s)" if k == "softcam" else u"bouquet(s)"))
    bk.close({"from": man.get("from"), "date": man.get("date"), "kinds": kinds})
    say(u">>> %d fichier(s) écrit(s). Ancienne version gardée dans %s" % (n_files, bk.dir))
    if "softcam" in kinds:
        cam = man.get("cam", "")
        if cam and cam != "None" and not os.path.exists("/etc/init.d/softcam." + cam):
            say(u"ATTENTION : la softcam « %s » de l'autre récepteur n'est pas installée ici (Softcam du panel)." % cam)
        if os.path.exists("/etc/init.d/softcam"):
            os.system("/etc/init.d/softcam restart >/dev/null 2>&1")
            say(u">>> Softcam redémarrée")
    say(u">>> Terminé")
    return 0


def undo():
    try:
        last = sorted(d for d in os.listdir(BACKUPS) if d.startswith("echange-"))[-1]
    except (OSError, IndexError):
        say(u"Aucun échange à annuler.")
        return 1
    d = os.path.join(BACKUPS, last)
    with open(os.path.join(d, "backup.json"), encoding="utf-8") as fh:
        info = json.load(fh)
    say(u">>> Annulation de l'échange reçu de %s (%s)" % (info.get("from", "?"), info.get("date", "")))
    for p in info.get("added", []):
        if os.path.isfile(p):
            os.remove(p)
    for p in info.get("saved", []):
        src = os.path.join(d, "files", p.lstrip("/"))
        os.makedirs(os.path.dirname(p), exist_ok=True)
        shutil.copy2(src, p)
    shutil.rmtree(d, ignore_errors=True)
    if "softcam" in info.get("kinds", []) and os.path.exists("/etc/init.d/softcam"):
        os.system("/etc/init.d/softcam restart >/dev/null 2>&1")
    say(u">>> %d fichier(s) remis, %d retiré(s). Terminé" % (len(info.get("saved", [])), len(info.get("added", []))))
    return 0


def main(argv):
    if len(argv) >= 2 and argv[1] == "serve":
        kinds = [k for k in (argv[2] if len(argv) > 2 else "").split(",") if k in KINDS]
        return serve(kinds or list(KINDS))
    if len(argv) >= 2 and argv[1] == "find":
        return find()
    if len(argv) >= 4 and argv[1] == "receive":
        return receive(argv[2], argv[3])
    if len(argv) >= 2 and argv[1] == "undo":
        return undo()
    if len(argv) >= 2 and argv[1] == "list":
        man, files = collect(list(KINDS))
        print(json.dumps(man["counts"]), len(files), "fichiers", man.get("cam"))
        return 0
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv))
