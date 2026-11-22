#!/usr/bin/env python3
"""Small helpers to build and read opkg .ipk files on Windows (no ar/dpkg needed).

An .ipk is an `ar` archive with: debian-binary, control.tar.gz, data.tar.gz.
"""
import io
import os
import tarfile
import time

AR_MAGIC = b"!<arch>\n"


def _ar_member(name, data, mtime):
    head = "%-16s%-12d%-6d%-6d%-8s%-10d`\n" % (name, mtime, 0, 0, "100644", len(data))
    out = head.encode("ascii") + data
    if len(data) % 2:
        out += b"\n"
    return out


def _filter(ti):
    ti.uid = ti.gid = 0
    ti.uname = ti.gname = "root"
    if ti.isdir():
        ti.mode = 0o755
    elif ti.isfile():
        # keep exec bit for scripts/binaries, else 644
        ti.mode = 0o755 if (ti.mode & 0o111 or ti.name.endswith((".sh",))) else 0o644
    return ti


def _tar_gz(add_fn):
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w:gz", format=tarfile.GNU_FORMAT) as tar:
        add_fn(tar)
    return buf.getvalue()


def build_ipk(out_path, control, data_root, scripts=None, symlinks=None, exec_paths=()):
    """control: dict of control fields (ordered). data_root: folder whose content is '/'.
    scripts: {'postinst': '...', ...}. symlinks: {'./usr/x/link': 'target'}.
    exec_paths: relative paths (posix, without leading ./) that must be 0755."""
    scripts = scripts or {}
    symlinks = symlinks or {}
    mtime = int(time.time())
    exec_paths = set(exec_paths)

    def add_control(tar):
        text = "".join("%s: %s\n" % (k, v) for k, v in control.items())
        for name, body in [("control", text)] + sorted(scripts.items()):
            raw = body.replace("\r\n", "\n").encode("utf-8")
            ti = tarfile.TarInfo("./" + name)
            ti.size = len(raw)
            ti.mtime = mtime
            ti.mode = 0o644 if name == "control" else 0o755
            tar.addfile(ti, io.BytesIO(raw))

    def add_data(tar):
        for dirpath, dirnames, filenames in os.walk(data_root):
            dirnames.sort()
            rel = os.path.relpath(dirpath, data_root).replace(os.sep, "/")
            arc = "." if rel == "." else "./" + rel
            ti = tarfile.TarInfo(arc)
            ti.type = tarfile.DIRTYPE
            ti.mode = 0o755
            ti.mtime = mtime
            tar.addfile(_filter(ti))
            for fn in sorted(filenames):
                full = os.path.join(dirpath, fn)
                relf = (fn if rel == "." else rel + "/" + fn)
                ti = tar.gettarinfo(full, "./" + relf)
                ti = _filter(ti)
                if relf in exec_paths:
                    ti.mode = 0o755
                with open(full, "rb") as fh:
                    tar.addfile(ti, fh)
        for link, target in sorted(symlinks.items()):
            ti = tarfile.TarInfo(link)
            ti.type = tarfile.SYMTYPE
            ti.linkname = target
            ti.mtime = mtime
            tar.addfile(_filter(ti))

    control_tgz = _tar_gz(add_control)
    data_tgz = _tar_gz(add_data)
    with open(out_path, "wb") as fh:
        fh.write(AR_MAGIC)
        fh.write(_ar_member("debian-binary", b"2.0\n", mtime))
        fh.write(_ar_member("control.tar.gz", control_tgz, mtime))
        fh.write(_ar_member("data.tar.gz", data_tgz, mtime))
    return out_path


def read_ipk(path):
    """Return {member_name: bytes} for an ipk (ar or the older tar.gz flavour)."""
    with open(path, "rb") as fh:
        raw = fh.read()
    members = {}
    if raw.startswith(AR_MAGIC):
        pos = len(AR_MAGIC)
        while pos < len(raw):
            head = raw[pos:pos + 60]
            name = head[:16].decode().strip().rstrip("/")
            size = int(head[48:58].decode().strip())
            members[name] = raw[pos + 60:pos + 60 + size]
            pos += 60 + size + (size % 2)
    else:  # tar.gz container
        with tarfile.open(fileobj=io.BytesIO(raw), mode="r:*") as tar:
            for m in tar.getmembers():
                if m.isfile():
                    members[m.name.lstrip("./")] = tar.extractfile(m).read()
    return members


def _open_inner(blob):
    if blob[:4] == bytes([0x28, 0xB5, 0x2F, 0xFD]):  # zstd (OpenATV 8 feed packages)
        import zstandard
        blob = zstandard.ZstdDecompressor().stream_reader(io.BytesIO(blob)).read()
    return tarfile.open(fileobj=io.BytesIO(blob), mode="r:*")


def control_fields(path):
    m = read_ipk(path)
    key = [k for k in m if k.startswith("control.tar")][0]
    with _open_inner(m[key]) as tar:
        for ti in tar.getmembers():
            if ti.name.lstrip("./") == "control":
                text = tar.extractfile(ti).read().decode("utf-8", "replace")
                break
    fields, last = {}, None
    for line in text.splitlines():
        if line[:1] in (" ", "\t") and last:
            fields[last] += "\n" + line
        elif ":" in line:
            last, v = line.split(":", 1)
            fields[last.strip()] = v.strip()
    return fields


def iter_files(path):
    """Yield (archive_name, bytes) for every file in control and data parts."""
    m = read_ipk(path)
    for key in m:
        if key.startswith(("control.tar", "data.tar")):
            with _open_inner(m[key]) as tar:
                for ti in tar.getmembers():
                    if ti.isfile():
                        yield key.split(".")[0] + ":" + ti.name, tar.extractfile(ti).read()
