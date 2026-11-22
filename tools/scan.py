#!/usr/bin/env python3
"""Scan .ipk files before publishing: secrets, personal data, IPTV credentials, malware markers.

Usage: python tools/scan.py packages/*.ipk
Prints every hit with the file and a short context. Exit code 1 if a hard hit is found.
The email to look for is read from the environment (PANEL_PRIVATE_WORDS, comma separated),
so it is never written in this public file.
"""
import os
import re
import sys

sys.path.insert(0, os.path.dirname(__file__))
import ipk  # noqa: E402

HARD = [
    (r"185\.53\.179\.136|system\.mark|netstat\.cfg|libgdi\.so\.0\.8\.2|/\.mod\b", "malware marker"),
    (r"(gh[pousr]_[A-Za-z0-9]{30,}|sk-[A-Za-z0-9_-]{30,}|AKIA[0-9A-Z]{16}|xox[bp]-[0-9A-Za-z-]{20,})", "API token"),
    (r"-----BEGIN [A-Z ]*PRIVATE KEY-----", "private key"),
    (r"(get\.php|player_api\.php)\?username=(?!\{|%|\"|'|<|\$|USER|user\b|xxx|test)[^&\s\"']{3,}&password=(?!\{|%|\"|'|<|\$|PASS|pass\b|xxx|test)[^&\s\"']{3,}", "IPTV credential URL"),
    (r"https?://[^/\s\"':@]{3,}:[^/\s\"'@]{3,}@[^\s\"']+", "URL with user:password"),
]
SOFT = [
    (r"\"(password|passwd|pass)\"\s*:\s*\"[^\"]{3,}\"", "password field with value"),
    (r"192\.168\.\d+\.\d+", "LAN address"),
]


def main(paths):
    private = [w.strip().lower() for w in os.environ.get("PANEL_PRIVATE_WORDS", "").split(",") if w.strip()]
    hard_hits = 0
    for p in paths:
        n = 0
        for name, blob in ipk.iter_files(p):
            n += 1
            low = blob.lower()
            for w in private:
                if w.encode() in low:
                    print("HARD  %s  %s  private word #%d" % (os.path.basename(p), name, private.index(w)))
                    hard_hits += 1
            try:
                text = blob.decode("utf-8")
            except UnicodeDecodeError:
                text = blob.decode("latin-1")
            for rx, label in HARD:
                for m in re.finditer(rx, text):
                    ctx = text[max(0, m.start() - 40):m.end() + 20].replace("\n", " ")
                    print("HARD  %s  %s  %s  ...%s..." % (os.path.basename(p), name, label, ctx[:140]))
                    hard_hits += 1
            for rx, label in SOFT:
                for m in list(re.finditer(rx, text))[:2]:
                    ctx = text[max(0, m.start() - 30):m.end() + 10].replace("\n", " ")
                    print("soft  %s  %s  %s  ...%s..." % (os.path.basename(p), name, label, ctx[:120]))
        print("ok    %s  (%d files)" % (os.path.basename(p), n))
    print("HARD HITS: %d" % hard_hits)
    return 1 if hard_hits else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
