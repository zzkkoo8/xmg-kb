#!/usr/bin/env python3
"""Map raw-book documents onto the cleaned xmg-kb corpus (outline task 11).

Reuses the historical pipeline output instead of re-parsing 70GB:
  legacy/.pipeline/state.sqlite             existing source inventory
  .../extraction-results.jsonl              extracted text per file_id
  .../classification-primary.jsonl          product classification
  .../adjudication-final.jsonl              decision + normalized_body_sha256

Matching uses the SAME normalization the historical pipeline used, so raw
bodies can be compared to xmg-kb docs by fingerprint alone.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import unicodedata
from collections import Counter
from pathlib import Path

XMG = Path(os.environ.get("XMG_KB_ROOT", "/srv/xmg-kb"))
LEGACY = Path(os.environ.get("XMG_KB_LEGACY_ROOT", "/srv/xmg-kb/legacy"))
REPORTS = XMG / "reports"
CURATION = LEGACY / "reports/rawdocs-curation-v2"


def normalize(t: str) -> str:
    """Identical to the historical preprocess.normalize()."""
    t = unicodedata.normalize("NFKC", t).replace("\x00", "")
    t = re.sub(r"^---\s*\n.*?\n---\s*\n", "", t, 1, flags=re.S)
    t = re.sub(r"https?://\S+", " URL ", t)  # literal, as in the historical normalizer
    t = re.sub(r"\s+", "", t).lower()
    return t


def body_sha(text: str) -> str:
    return hashlib.sha256(normalize(text).encode()).hexdigest()


def main() -> int:
    REPORTS.mkdir(parents=True, exist_ok=True)

    # --- fingerprint the cleaned corpus -------------------------------------
    kb_index: dict[str, str] = {}
    for path in sorted((XMG / "docs").rglob("*.md")):
        text = path.read_text(errors="replace")
        kb_index.setdefault(body_sha(text), path.relative_to(XMG / "docs").as_posix())
    print(f"xmg-kb fingerprints: {len(kb_index)}")

    # --- load historical extraction + classification ------------------------
    extraction: dict[str, dict] = {}
    with (CURATION / "extraction-results.jsonl").open() as fh:
        for line in fh:
            rec = json.loads(line)
            extraction[rec["file_id"]] = rec

    classification: dict[str, dict] = {}
    with (CURATION / "classification-primary.jsonl").open() as fh:
        for line in fh:
            rec = json.loads(line)
            classification[rec["file_id"]] = rec

    # --- map ---------------------------------------------------------------
    rows = []
    counts: Counter = Counter()
    with (CURATION / "adjudication-final.jsonl").open() as fh:
        for line in fh:
            rec = json.loads(line)
            fid = rec["file_id"]
            body_hash = rec.get("normalized_body_sha256")
            matched = kb_index.get(body_hash) if body_hash else None
            hist = rec.get("decision")
            cls = classification.get(fid, {})
            ext = extraction.get(fid, {})
            products = cls.get("products") or rec.get("products") or []

            # The adjudicator's own normalization (it strips noise lines) does
            # not match preprocess.normalize, so its body hash cannot be
            # reproduced here.  best_kb_path is unambiguous -> map by path.
            kb_rel = None
            best = rec.get("best_kb_path")
            if best and "/docs/" in str(best):
                kb_rel = str(best).split("/docs/", 1)[1]

            if kb_rel and (XMG / "docs" / kb_rel).exists():
                status = "EXISTING_ACCEPTED"
            elif kb_rel:
                status = "EXISTING_DROPPED_BY_CLEANING"
            elif matched:
                status = "EXISTING_ACCEPTED"
            elif hist == "missing_ingest":
                status = "UNMAPPED_NEW_HIGH_CONF"
            elif hist == "supplement":
                status = "REVIEW_SUPPLEMENT"
            elif hist == "manual":
                status = "REVIEW_MANUAL"
            else:
                status = "SKIPPED"

            counts[status] += 1
            rows.append({
                "file_id": fid,
                "relative_path": rec.get("relative_path"),
                "status": status,
                "historical_decision": hist,
                "products": products,
                "matched_kb_path": matched,
                "text_path": ext.get("text_path"),
                "text_chars": ext.get("text_chars", 0),
                "normalized_body_chars": rec.get("normalized_body_chars", 0),
            })

    with (REPORTS / "rawbook-map.jsonl").open("w") as fh:
        for r in rows:
            fh.write(json.dumps(r, ensure_ascii=False) + "\n")

    summary = {
        "xmg_kb_docs_fingerprinted": len(kb_index),
        "adjudication_records": len(rows),
        "status_counts": dict(counts),
        "raw_inventory_total": 31908,
    }
    (REPORTS / "rawbook-map-summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2))
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
