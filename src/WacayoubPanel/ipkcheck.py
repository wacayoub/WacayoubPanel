# -*- coding: utf-8 -*-
"""Check a package from another image before installing it (run by the panel's install script).

Exit 0: only portable content (Python source, images, skins, translations...).
Exit 1 (message printed): compiled code (ELF binary / .so) or Python bytecode without its .py source:
those are built for another image's system or Python version and would not work here.
Usage: python3 ipkcheck.py file.ipk
"""
import io
import os
import sys
import tarfile


def ar_members(raw):
    pos, out = 8, {}
    while pos + 60 <= len(raw):
        head = raw[pos:pos + 60]
        name = head[:16].decode("ascii", "replace").strip().rstrip("/")
        size = int(head[48:58].decode("ascii").strip() or 0)
        out[name] = raw[pos + 60:pos + 60 + size]
        pos += 60 + size + (size % 2)
    return out


def open_tar(blob):
    if blob[:4] == bytes([0x28, 0xB5, 0x2F, 0xFD]):  # zstd
        try:
            from compression import zstd  # Python 3.14+
            blob = zstd.decompress(blob)
        except ImportError:
            import zstandard  # optional module on older images
            blob = zstandard.ZstdDecompressor().stream_reader(io.BytesIO(blob)).read()
    return tarfile.open(fileobj=io.BytesIO(blob), mode="r:*")


def check(path):
    with open(path, "rb") as fh:
        raw = fh.read()
    if raw[:8] == b"!<arch>\n":
        members = ar_members(raw)
    else:  # old tar.gz container
        with tarfile.open(path, "r:*") as tar:
            members = dict((m.name.lstrip("./"), tar.extractfile(m).read()) for m in tar.getmembers() if m.isfile())
    data = [v for k, v in members.items() if k.startswith("data.tar")]
    if not data:
        return "contenu illisible"
    py, pyc, problems = set(), [], []
    with open_tar(data[0]) as tar:
        for m in tar.getmembers():
            if not m.isfile():
                continue
            name = m.name.lstrip("./")
            head = tar.extractfile(m).read(4)
            if head == b"\x7fELF" or name.endswith(".so") or ".so." in os.path.basename(name):
                problems.append("code binaire : " + name)
            elif name.endswith(".py"):
                py.add(name[:-3])
            elif name.endswith(".pyc"):
                pyc.append(name)
    for name in pyc:
        base = name[:-4]
        if "/__pycache__/" in name:  # __pycache__/x.cpython-312.pyc -> x
            d, f = name.split("/__pycache__/", 1)
            base = d + "/" + f.split(".")[0]
        if base not in py:
            problems.append("Python compilé sans source : " + name)
    return "; ".join(problems[:3]) + (" …" if len(problems) > 3 else "") if problems else ""


if __name__ == "__main__":
    try:
        why = check(sys.argv[1])
    except Exception as e:
        why = "paquet illisible (%s)" % e
    if why:
        print("REFUSÉ : " + why)
        print("Ce paquet est fait pour une autre image et ne marcherait pas sur ce récepteur.")
        sys.exit(1)
    print(">>> Contrôle OK : pas de code binaire, Python avec source")
    sys.exit(0)
