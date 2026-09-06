#!/usr/bin/env python3
"""Break hardlinks shared with the legacy KB.

xmg-kb/docs was seeded via `cp -al`, so its files share inodes with
chaitin-kb/docs.  Any in-place edit would silently mutate the legacy KB.
This stage replaces each linked file with an independent copy (new inode),
leaving chaitin-kb untouched.  Idempotent: files already at nlink==1 are skipped.
"""
from __future__ import annotations

import os
import shutil
from pathlib import Path

DOCS = Path(os.environ.get("XMG_KB_ROOT", "/srv/xmg-kb")) / "docs"


def main() -> int:
    if not DOCS.is_dir():
        print(f"missing docs dir: {DOCS}", file=__import__("sys").stderr)
        return 1

    broken = 0
    already = 0
    for path in DOCS.rglob("*"):
        if not path.is_file():
            continue
        if path.stat().st_nlink <= 1:
            already += 1
            continue
        tmp = path.with_name(path.name + ".materialize.tmp")
        shutil.copy2(path, tmp)
        os.replace(tmp, path)  # atomic; new inode, legacy link stays on old inode
        broken += 1

    print(f"materialized={broken} already_independent={already}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
