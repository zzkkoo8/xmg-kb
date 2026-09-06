"""Ingest genuinely-new raw-book documents into xmg-kb (outline tasks 17/19).

Applies the SAME gates used to clean the legacy corpus, so raw material cannot
re-pollute it.  Also de-duplicates within the batch by normalized body hash,
because raw-book contains many copies of the same document.

  --dry-run   report only (default)
  --apply     write into docs/
  --limit N   stop after N documents
"""
from __future__ import annotations

import argparse
import json
import re
import sqlite3
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from lib import (  # noqa: E402
    DATA, DOCS, INGEST_MODULE, LEGACY, PARSED, PRODUCT_DIR, RAW, REPORTS,
    TEXT_EXT, HTML_EXT,
    connect, norm_body, classify_product, _now,
)
from stage02_audit import (  # noqa: E402
    EXCLUDE_PATTERNS, REVIEW_PATTERNS, sensitive_findings, quality_issues,
)
from stage05_review import EXCLUDE_RULES, EXPLICIT_EMPTY, KEEP_GUARD  # noqa: E402
from stage07_ingest import (  # noqa: E402
    looks_like_base64, ERROR_PAGE, COMPETITOR_BRAND,
)

MIN_COMPACT = 400


def read_text(rel: str, ext: str, text_path: str | None) -> str:
    if text_path and Path(text_path).exists():
        return Path(text_path).read_text(errors="replace")
    if ext in (TEXT_EXT | HTML_EXT):
        p = RAW / rel
        if p.exists():
            return p.read_text(errors="replace")
    return ""


def gate(rel: str, text: str) -> str | None:
    if looks_like_base64(text):
        return "exclude:base64_or_mhtml"
    if ERROR_PAGE.search(text[:2000]) or ERROR_PAGE.search(rel):
        return "exclude:error_page"
    if COMPETITOR_BRAND.search(rel) or COMPETITOR_BRAND.search(text[:4000]):
        return "exclude:competitor_brand"
    if "_待归属附件" in rel:
        return "exclude:unattributed_attachment"
    for name, pattern in EXCLUDE_PATTERNS:
        if re.search(pattern, rel) or re.search(pattern, text[:4000]):
            return f"exclude:{name}"
    for name, pattern in REVIEW_PATTERNS:
        if re.search(pattern, rel) or re.search(pattern, text[:4000]):
            return f"review:{name}"
    for code, rx, _g in EXCLUDE_RULES:
        if rx.search(rel + "\n" + text[:1500]) and not KEEP_GUARD.search(rel):
            return f"exclude:{code}"
    sens = sensitive_findings(text)
    if sens:
        return f"sensitive:{sens[0]}"
    if EXPLICIT_EMPTY.search(text[:1200]):
        return "exclude:stub_placeholder"
    issues = quality_issues(text)
    if "empty" in issues or "garbled" in issues:
        return "quality:P0"
    return None


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--limit", type=int, default=0)
    args = ap.parse_args()
    mode = "APPLY" if args.apply else "DRY-RUN"

    con = connect("raw-manifest.sqlite")
    rows = [dict(r) for r in con.execute(
        "SELECT source_path, ext, sha256, normalized_sha, text_chars, product, parser, error "
        "FROM raw_files WHERE status='CANDIDATE_NEW' ORDER BY source_path")]
    print(f"candidates: {len(rows)}", flush=True)

    legacy_state = (LEGACY / ".pipeline/state.sqlite").resolve()
    legacy = sqlite3.connect(f"file:{legacy_state}?mode=ro", uri=True)
    legacy.row_factory = sqlite3.Row
    tp = {r["source_path"]: None for r in legacy.execute("SELECT source_path FROM sources")}

    counts: Counter = Counter()
    seen_hash: dict[str, str] = {}
    ingested, skipped = [], []

    for i, row in enumerate(rows):
        rel, ext = row["source_path"], (row["ext"] or "").lower()
        # locate parsed output for binaries
        tpath = None
        sha = None
        lrow = legacy.execute(
            "SELECT source_sha256, output_path FROM sources WHERE source_path=?", (rel,)).fetchone()
        if lrow:
            sha = lrow["source_sha256"]
            if lrow["output_path"] and Path(lrow["output_path"]).exists():
                tpath = lrow["output_path"]
            elif sha:
                cand = PARSED / sha[:2] / sha / "document.md"
                if cand.exists():
                    tpath = str(cand)
        if tpath is None and row.get("sha256"):
            # stage10 writes extracted text under parsed/<sha256>/document.md;
            # use the raw manifest hash when legacy state has no output_path.
            raw_sha = row["sha256"]
            cand = PARSED / raw_sha[:2] / raw_sha / "document.md"
            if cand.exists():
                tpath = str(cand)
        text = read_text(rel, ext, tpath)
        if not text.strip():
            skipped.append({"source_path": rel, "reason": "no_text"})
            counts["no_text"] += 1
            continue
        if len(re.sub(r"\s+", "", text)) < MIN_COMPACT:
            skipped.append({"source_path": rel, "reason": "too_short"})
            counts["too_short"] += 1
            continue

        h = norm_body(text)
        if h in seen_hash:
            skipped.append({"source_path": rel, "reason": "batch_duplicate_of",
                            "dup_of": seen_hash[h]})
            counts["batch_duplicate"] += 1
            continue

        g = gate(rel, text)
        if g:
            skipped.append({"source_path": rel, "reason": g})
            counts[g.split(":")[0]] += 1
            continue

        product, conf = classify_product(text, rel)
        if product == "unknown":
            counts["unknown_product"] += 1
        dest_dir = DOCS / PRODUCT_DIR.get(product, "00-通用基础") / INGEST_MODULE
        stem = Path(rel).stem[:80]
        dest = dest_dir / f"{stem}.md"
        n = 1
        while dest.exists():
            dest = dest_dir / f"{stem}-{n}.md"
            n += 1

        body = (f"---\n"
                f"title: {json.dumps(Path(rel).stem, ensure_ascii=False)}\n"
                f"product: \"{product}\"\n"
                f"category: \"{INGEST_MODULE}\"\n"
                f"source: raw-book\n"
                f"raw_path: \"{rel}\"\n"
                f"raw_sha256: \"{sha or ''}\"\n"
                f"parser: \"{row['parser'] or ('direct' if ext in (TEXT_EXT|HTML_EXT) else 'legacy')}\"\n"
                f"product_confidence: {conf}\n"
                f"review_status: ingested_auto\n"
                f"---\n\n{text.strip()}\n")
        if args.apply:
            dest_dir.mkdir(parents=True, exist_ok=True)
            dest.write_text(body)
        seen_hash[h] = dest.relative_to(DOCS).as_posix() if args.apply else rel
        ingested.append({"source_path": rel, "product": product, "conf": conf,
                         "dest": str(dest.relative_to(DOCS)), "chars": len(text)})
        counts["INGESTED"] += 1
        if args.apply:
            # only record the transition once the file really exists
            con.execute("UPDATE raw_files SET status='INGESTED', updated_at=? WHERE source_path=?",
                        (_now(), rel))
        if (i + 1) % 500 == 0:
            con.commit()
            print(f"  ...{i+1}/{len(rows)} {dict(counts)}", flush=True)
        if args.limit and counts["INGESTED"] >= args.limit:
            break
    con.commit()

    REPORTS.mkdir(parents=True, exist_ok=True)
    with (REPORTS / "ingest-manifest.jsonl").open("w") as fh:
        for r in ingested:
            fh.write(json.dumps(r, ensure_ascii=False) + "\n")
    with (REPORTS / "ingest-skipped.jsonl").open("w") as fh:
        for r in skipped:
            fh.write(json.dumps(r, ensure_ascii=False) + "\n")
    summary = {"candidates": len(rows), "result": dict(counts)}
    (REPORTS / "ingest-summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2))
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    con.close()
    legacy.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
