#!/usr/bin/env python3
"""
build_manifest.py — regenerate MANIFEST.csv with real byte sizes and SHA-256
checksums for every release file.

Scope (same as the original manifest): README.md plus everything under
data/, documents/, and pipeline/. The website (docs/) and the manifest itself
are excluded.

Usage:
    python3 scripts/build_manifest.py
"""
import os
import csv
import hashlib

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT  = os.path.join(REPO, "MANIFEST.csv")
ROOTS = ["data", "documents", "pipeline"]
EXTRA_FILES = ["README.md"]


def sha256(path, chunk=1 << 20):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for block in iter(lambda: fh.read(chunk), b""):
            h.update(block)
    return h.hexdigest()


def main():
    rows = []
    for f in EXTRA_FILES:
        p = os.path.join(REPO, f)
        if os.path.isfile(p):
            rows.append((f, os.path.getsize(p), sha256(p)))

    for root in ROOTS:
        base = os.path.join(REPO, root)
        for dirpath, _, files in os.walk(base):
            for fn in files:
                p = os.path.join(dirpath, fn)
                rel = os.path.relpath(p, REPO)
                rows.append((rel, os.path.getsize(p), sha256(p)))

    rows.sort(key=lambda r: r[0])

    with open(OUT, "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["path", "size_bytes", "sha256"])
        for r in rows:
            w.writerow(r)

    print(f"Wrote {os.path.relpath(OUT, REPO)} with {len(rows)} files")


if __name__ == "__main__":
    main()
