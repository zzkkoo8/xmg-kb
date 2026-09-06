#!/usr/bin/env python3
"""Close the raw-file state semantics (outline task 13) and emit provenance.

Problem: `needs_parse` was set by stage08 (inventory) but never cleared by the
stages that later reclassify a file.  A file marked EXISTING_ACCEPTED - which
must never be re-parsed - could still carry needs_parse=1, so any consumer that
selects on that flag would re-parse content already in the corpus.

Rule enforced here:
    needs_parse == 1  <=>  status == 'NEEDS_PARSE'
and never for EXISTING_ACCEPTED / EXACT_DUPLICATE / UNSUPPORTED / any PARSED*.

Also emits parsed/<sha2>/<sha>/provenance.json (outline task 14) alongside each
extracted document, recording raw path/sha, parser, parser version and time.

  --dry-run   report the drift, change nothing (default)
  --apply     reconcile the flag and write provenance files
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sqlite3
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from lib import PARSED, connect, _now  # noqa: E402

# statuses that must never be queued for parsing
NEVER_PARSE = {
    "EXISTING_ACCEPTED", "EXACT_DUPLICATE", "UNSUPPORTED",
    "PARSED", "PARSE_FAILED", "PARSE_EMPTY", "PARSE_GARBAGE",
}


def tool_version(parser: str) -> str:
    """Best-effort parser version; 'unknown' when it cannot be determined."""
    try:
        if parser == "pdftotext":
            out = subprocess.run(["pdftotext", "-v"], capture_output=True,
                                 text=True, timeout=30)
            return (out.stderr or out.stdout).strip().splitlines()[0][:80]
        if parser == "libreoffice":
            out = subprocess.run(["soffice", "--version"], capture_output=True,
                                 text=True, timeout=60)
            return out.stdout.strip().splitlines()[0][:80]
        if parser == "tesseract":
            out = subprocess.run(["tesseract", "--version"], capture_output=True,
                                 text=True, timeout=30)
            return (out.stdout or out.stderr).strip().splitlines()[0][:80]
    except Exception:
        pass
    return "unknown"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args()
    mode = "APPLY" if args.apply else "DRY-RUN"

    con = connect("raw-manifest.sqlite")
    total = con.execute("SELECT COUNT(*) FROM raw_files").fetchone()[0]

    drift = con.execute(
        "SELECT COUNT(*) FROM raw_files WHERE needs_parse=1 AND status!='NEEDS_PARSE'"
    ).fetchone()[0]
    stale_in_never = con.execute(
        "SELECT COUNT(*) FROM raw_files WHERE needs_parse=1 AND status IN ({})".format(
            ",".join("?" * len(NEVER_PARSE))), tuple(NEVER_PARSE)).fetchone()[0]

    print(f"[{mode}] rows={total}")
    print(f"[{mode}] needs_parse=1 but status!='NEEDS_PARSE' : {drift}")
    print(f"[{mode}]   of which in never-parse statuses      : {stale_in_never}")

    if args.apply:
        cur = con.execute(
            "UPDATE raw_files SET needs_parse=0 WHERE needs_parse=1 "
            "AND status!='NEEDS_PARSE'")
        print(f"[{mode}] cleared {cur.rowcount} stale flags")
        # make the invariant explicit for anything still queued
        cur2 = con.execute(
            "UPDATE raw_files SET needs_parse=1 WHERE status='NEEDS_PARSE' "
            "AND needs_parse=0")
        print(f"[{mode}] re-armed {cur2.rowcount} genuine NEEDS_PARSE rows")
        con.commit()

    # --- normalized_sha must hold a hash, not the normalized body -----------
    # An earlier revision of stage10 stored the whole normalized text in this
    # column (~4.8k rows, inflating the DB to hundreds of MB).  The stored value
    # IS the normalized body, so hashing it recovers the intended digest without
    # re-reading any source file.
    polluted = con.execute(
        "SELECT COUNT(*) FROM raw_files WHERE normalized_sha IS NOT NULL "
        "AND length(normalized_sha) > 64").fetchone()[0]
    print(f"[{mode}] normalized_sha holding text instead of hash: {polluted}")
    if args.apply and polluted:
        rows = con.execute(
            "SELECT rowid, normalized_sha FROM raw_files WHERE normalized_sha IS NOT NULL "
            "AND length(normalized_sha) > 64").fetchall()
        con.executemany(
            "UPDATE raw_files SET normalized_sha=? WHERE rowid=?",
            [(hashlib.sha256(v.encode("utf-8")).hexdigest(), rid) for rid, v in rows])
        con.commit()
        print(f"[{mode}] converted {len(rows)} rows to sha256")
        con.execute("VACUUM")
        print(f"[{mode}] vacuumed database")

    # --- provenance for parsed outputs (outline task 14) --------------------
    versions: dict[str, str] = {}
    prov_written = 0
    rows = con.execute(
        "SELECT source_path, sha256, parser, normalized_sha, text_chars, updated_at "
        "FROM raw_files WHERE status='PARSED' AND sha256 IS NOT NULL").fetchall()
    for r in rows:
        parser = r["parser"] or "unknown"
        if parser not in versions:
            versions[parser] = tool_version(parser)
        digest = r["sha256"]
        outdir = PARSED / digest[:2] / digest
        doc = outdir / "document.md"
        if not doc.exists():
            continue
        rec = {
            "raw_path": r["source_path"],
            "raw_sha256": digest,
            "parser": parser,
            "parser_version": versions[parser],
            "parser_version_source": "environment_probe" if versions[parser] != "unknown"
                                     else "unavailable",
            "parse_time": r["updated_at"],
            "normalized_sha256": r["normalized_sha"],
            "text_chars": r["text_chars"],
            "document": str(doc),
            "recorded_at": datetime.now(timezone.utc).isoformat(),
        }
        if args.apply:
            (outdir / "provenance.json").write_text(
                json.dumps(rec, ensure_ascii=False, indent=2) + "\n")
        prov_written += 1

    print(f"[{mode}] provenance records for PARSED rows: {prov_written}")

    # --- post-condition ------------------------------------------------------
    remaining = con.execute(
        "SELECT COUNT(*) FROM raw_files WHERE needs_parse=1 AND status!='NEEDS_PARSE'"
    ).fetchone()[0]
    ok = remaining == 0 if args.apply else True
    print(f"[{mode}] post-check needs_parse drift: {remaining}  "
          f"({'PASS' if remaining == 0 else 'FAIL' if args.apply else 'n/a'})")
    con.close()
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
