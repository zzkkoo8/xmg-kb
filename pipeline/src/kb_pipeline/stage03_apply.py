#!/usr/bin/env python3
"""Apply the audit decisions to xmg-kb/docs.

Excluded documents are QUARANTINED (moved into _archive/excluded-<ts>/), never
deleted, and every move is recorded with its sha256 so the step can be undone.
Documents marked REVIEW stay in the corpus; they are only listed in a queue.

  --dry-run   print what would happen, change nothing (default)
  --apply     actually move files
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from lib import write_manifest

ROOT = Path(os.environ.get("XMG_KB_ROOT", "/srv/xmg-kb"))
DOCS = ROOT / "docs"
REPORTS = ROOT / "reports"
AUDIT = REPORTS / "corpus-audit.jsonl"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true", help="perform the quarantine moves")
    args = ap.parse_args()
    mode = "APPLY" if args.apply else "DRY-RUN"

    records = [json.loads(line) for line in AUDIT.open()]
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    archive = ROOT / f"_archive/excluded-{stamp}"

    manifest: list[dict] = []
    review_queue: list[dict] = []

    for rec in records:
        path = DOCS / rec["path"]
        if rec["decision"] == "EXCLUDE":
            if not path.exists():
                continue
            target = archive / rec["path"]
            if args.apply:
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.move(str(path), str(target))
            manifest.append({
                "original_path": rec["path"],
                "archived_to": str(target.relative_to(ROOT)),
                "sha256": rec["sha256"],
                "reasons": rec["reasons"],
                "moved": bool(args.apply),
            })
        elif rec["decision"] == "REVIEW":
            review_queue.append({
                "path": rec["path"],
                "product": rec["product"],
                "module": rec["module"],
                "reasons": rec["reasons"],
            })

    REPORTS.mkdir(parents=True, exist_ok=True)
    # merge, never overwrite: earlier runs' archived files stay traceable
    n_records = write_manifest(REPORTS / "apply-manifest.jsonl", manifest)
    print(f"[{mode}] apply-manifest records={n_records} (this run {len(manifest)})")
    with (REPORTS / "review-queue.jsonl").open("w") as fh:
        for item in review_queue:
            fh.write(json.dumps(item, ensure_ascii=False) + "\n")

    remaining = sum(1 for r in records if r["decision"] != "EXCLUDE")
    print(f"[{mode}] total={len(records)} kept={remaining} "
          f"quarantined={len(manifest)} review={len(review_queue)}")
    print(f"[{mode}] archive={archive}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
