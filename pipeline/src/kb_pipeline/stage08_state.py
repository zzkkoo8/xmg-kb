"""Build the pipeline databases and assign a definitive state to every raw file.

Outline tasks 02/10/11.  Idempotent and resumable: re-running only touches rows
whose size/mtime changed.

Reads the configured Raw Evidence root strictly read-only. The historical
state database already holds SHA-256 coverage for the inventoried files and
normalized text hashes for parsed files, so those files need no re-hashing or
re-parsing.
"""
from __future__ import annotations

import json
import sqlite3
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from lib import (  # noqa: E402
    ARCHIVE_EXT, DATA, DOC_EXT, DOCS, EXEC_EXT, LEGACY, MEDIA_EXT, RAW,
    REPORTS, connect, ensure_dirs, normalized_sha, sha256_file, _now,
)

RAW_SCHEMA = """
CREATE TABLE IF NOT EXISTS raw_files(
  source_path TEXT PRIMARY KEY, ext TEXT, size INTEGER, mtime_ns INTEGER,
  sha256 TEXT, status TEXT, reason TEXT, normalized_sha TEXT,
  text_chars INTEGER, product TEXT, product_conf REAL, parser TEXT,
  needs_parse INTEGER DEFAULT 0, updated_at TEXT, error TEXT);
CREATE INDEX IF NOT EXISTS idx_raw_status ON raw_files(status);
CREATE INDEX IF NOT EXISTS idx_raw_norm ON raw_files(normalized_sha);
CREATE INDEX IF NOT EXISTS idx_raw_sha ON raw_files(sha256);
"""

EXISTING_SCHEMA = """
CREATE TABLE IF NOT EXISTS existing_docs(
  path TEXT PRIMARY KEY, sha256 TEXT, normalized_sha TEXT,
  product TEXT, category TEXT, chars INTEGER);
CREATE INDEX IF NOT EXISTS idx_ex_norm ON existing_docs(normalized_sha);
"""

GOV_SCHEMA = """
CREATE TABLE IF NOT EXISTS events(
  id INTEGER PRIMARY KEY AUTOINCREMENT, stage TEXT, file_id TEXT,
  status TEXT, message TEXT, created_at TEXT);
"""


def build_existing(con: sqlite3.Connection) -> int:
    """Fingerprint the cleaned corpus (outline 'existing-docs-manifest')."""
    econ = connect("existing-docs-manifest.sqlite")
    econ.executescript(EXISTING_SCHEMA)
    n = 0
    for path in sorted(DOCS.rglob("*.md")):
        if path.name == "_sidebar.md":
            continue
        text = path.read_text(errors="replace")
        rel = path.relative_to(DOCS).as_posix()
        product = category = "unknown"
        if text.startswith("---"):
            head = text.split("\n---", 1)[0]
            for line in head.splitlines():
                if line.startswith("product:"):
                    product = line.split(":", 1)[1].strip().strip('"')
                elif line.startswith("category:"):
                    category = line.split(":", 1)[1].strip().strip('"')
        econ.execute(
            "INSERT OR REPLACE INTO existing_docs VALUES(?,?,?,?,?,?)",
            (rel, sha256_file(path), normalized_sha(text), product, category,
             len(text)))
        n += 1
    econ.commit()
    econ.close()
    return n


def main() -> int:
    ensure_dirs()
    con = connect("raw-manifest.sqlite")
    con.executescript(RAW_SCHEMA)
    gov = connect("governance.sqlite")
    gov.executescript(GOV_SCHEMA)

    print("fingerprinting existing corpus ...", flush=True)
    n_existing = build_existing(con)
    econ = connect("existing-docs-manifest.sqlite")
    kb_norm = {r[0] for r in econ.execute("SELECT normalized_sha FROM existing_docs")}
    econ.close()
    print(f"  existing docs: {n_existing} ({len(kb_norm)} unique bodies)", flush=True)

    # ---- load historical inventory -----------------------------------------
    legacy = sqlite3.connect(f"file:{LEGACY/'.pipeline/state.sqlite'}?mode=ro", uri=True)
    legacy.row_factory = sqlite3.Row
    rows = legacy.execute(
        "SELECT source_path, source_size, source_mtime_ns, source_sha256, extension,"
        " normalized_text_sha256, state, source_alias_of, product,"
        " classification_confidence, parser, error FROM sources").fetchall()
    print(f"  historical inventory rows: {len(rows)}", flush=True)

    known = {r["source_path"]: dict(r) for r in con.execute(
        "SELECT source_path,size,mtime_ns,sha256,status FROM raw_files")}

    counts: Counter = Counter()
    batch = []
    for i, r in enumerate(rows):
        rel = r["source_path"]
        ext = (r["extension"] or "").lower()
        prior = known.get(rel)
        if prior and prior["status"] and prior["size"] == r["source_size"] \
                and prior["mtime_ns"] == r["source_mtime_ns"]:
            counts[prior["status"]] += 1
            continue  # unchanged -> resumable skip

        src = RAW / rel
        status, reason, needs_parse = None, "", 0

        if r["source_alias_of"]:
            status, reason = "EXACT_DUPLICATE", "content-identical to another raw file"
        elif ext in MEDIA_EXT:
            status, reason = "UNSUPPORTED", "image/audio/video; needs OCR to be useful"
        elif ext in ARCHIVE_EXT:
            status, reason = "UNSUPPORTED", "archive; only if no expanded equivalent"
        elif ext in EXEC_EXT:
            status, reason = "UNSUPPORTED", "binary program or library"
        elif ext == ".http" or rel.lower().endswith(".http"):
            status, reason = "UNSUPPORTED", "single HTTP test sample"
        elif Path(rel).name.lower() in {"cookies.json"} or "_download_log" in rel:
            status, reason = "UNSUPPORTED", "scrape/control artifact"
        elif ext not in DOC_EXT:
            status, reason = "UNSUPPORTED", f"no extractable text ({ext or 'no ext'})"
        elif not src.exists():
            status, reason = "MISSING", "raw file not present on disk"
        else:
            norm = r["normalized_text_sha256"]
            if norm and norm in kb_norm:
                status, reason = "EXISTING_ACCEPTED", "body already in xmg-kb"
            elif norm:
                status, reason = "CANDIDATE_PARSED", "parsed body not in KB"
            else:
                status, reason, needs_parse = "NEEDS_PARSE", "not yet parsed", 1

        counts[status] += 1
        batch.append((rel, ext, r["source_size"], r["source_mtime_ns"], r["source_sha256"],
                      status, reason, r["normalized_text_sha256"], None,
                      r["product"], r["classification_confidence"], r["parser"],
                      needs_parse, _now(), r["error"]))
        if len(batch) >= 2000:
            con.executemany("INSERT OR REPLACE INTO raw_files VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", batch)
            con.commit()
            batch.clear()
            print(f"  ...{i+1}", flush=True)
    if batch:
        con.executemany("INSERT OR REPLACE INTO raw_files VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", batch)
        con.commit()

    summary = {"total": len(rows), "status_counts": dict(counts),
               "existing_docs": n_existing, "unique_kb_bodies": len(kb_norm)}
    REPORTS.mkdir(parents=True, exist_ok=True)
    (REPORTS / "rawbook-state-summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2))
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    con.close()
    gov.close()
    legacy.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
