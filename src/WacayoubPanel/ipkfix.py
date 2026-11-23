# -*- coding: utf-8 -*-
"""Adapt an OSCam/NCam package built by another image (OpenViX, OpenPLi...) to OpenATV, in place.

Only the control file's Depends line changes (the binary, init script and configs stay as they are):
- "softcam-support" is removed: it is the other image's softcam framework, OpenATV has its own
  (/etc/init.d/softcam + Softcam Setup) and its initscripts package conflicts with it;
- "libusb1" becomes "libusb-1.0-0": same library, OpenATV's package name.
The checksum of the original file is verified by the panel before this runs.
Usage: python3 ipkfix.py file.ipk
"""
import io
import sys
import tarfile
import time

DROP = ("softcam-support",)
RENAME = {"libusb1": "libusb-1.0-0"}


def ar_read(raw):
    pos, out = 8, []
    while pos + 60 <= len(raw):
        head = raw[pos:pos + 60]
        name = head[:16].decode("ascii", "replace").strip().rstrip("/")
        size = int(head[48:58].decode("ascii").strip() or 0)
        out.append((name, raw[pos + 60:pos + 60 + size]))
        pos += 60 + size + (size % 2)
    return out


def ar_member(name, data):
    head = "%-16s%-12d%-6d%-6d%-8s%-10d`\n" % (name, int(time.time()), 0, 0, "100644", len(data))
    return head.encode("ascii") + data + (b"\n" if len(data) % 2 else b"")


def open_tar(blob):
    if blob[:4] == bytes([0x28, 0xB5, 0x2F, 0xFD]):
        from compression import zstd  # Python 3.14+
        blob = zstd.decompress(blob)
    return tarfile.open(fileobj=io.BytesIO(blob), mode="r:*")


def fix_depends(line):
    out = []
    for part in line.split(","):
        alts = []
        for alt in part.split("|"):
            name = alt.strip().split(" ")[0]
            if not name or name in DROP:
                continue
            alts.append(alt.strip().replace(name, RENAME.get(name, name), 1))
        if alts:
            out.append(" | ".join(alts))
    return ", ".join(out)


def main(path):
    with open(path, "rb") as fh:
        raw = fh.read()
    if raw[:8] != b"!<arch>\n":
        raise ValueError("format ipk inattendu")
    members = ar_read(raw)
    ctl_name = [n for n, _b in members if n.startswith("control.tar")][0]
    files = []
    with open_tar(dict(members)[ctl_name]) as tar:
        for m in tar.getmembers():
            data = tar.extractfile(m).read() if m.isfile() else None
            files.append((m, data))
    changed = False
    new_files = []
    for m, data in files:
        if m.isfile() and m.name.lstrip("./") == "control":
            lines = data.decode("utf-8").split("\n")
            for i, line in enumerate(lines):
                if line.startswith("Depends:"):
                    fixed = "Depends: " + fix_depends(line[len("Depends:"):])
                    if fixed != line:
                        lines[i], changed = fixed, True
            data = "\n".join(lines).encode("utf-8")
            m.size = len(data)
        new_files.append((m, data))
    if not changed:
        print(">>> Paquet déjà compatible OpenATV")
        return
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w:gz", format=tarfile.GNU_FORMAT) as tar:
        for m, data in new_files:
            tar.addfile(m, io.BytesIO(data) if data is not None else None)
    out = [b"!<arch>\n"]
    for name, blob in members:
        if name == ctl_name:
            out.append(ar_member("control.tar.gz", buf.getvalue()))
        else:
            out.append(ar_member(name, blob))
    with open(path, "wb") as fh:
        fh.write(b"".join(out))
    print(">>> Paquet adapté à OpenATV (dépendances softcam-support/libusb1 corrigées)")


if __name__ == "__main__":
    try:
        main(sys.argv[1])
    except Exception as e:
        print("ERREUR: adaptation impossible (%s)" % e)
        sys.exit(1)
