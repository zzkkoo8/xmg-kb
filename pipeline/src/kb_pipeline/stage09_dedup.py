"""Link raw-book files to the xmg-kb corpus (outline task 11 + 12).

Exact hashing alone fails because curation rewrote the documents (it prepends a
`# <title>` H1 and adds front matter), so raw bodies never hash equal to KB
bodies.  This stage resolves that in three cheap passes:

  pass A  historical hash fast path - reuse the 9,620 normalized_text_sha256
          values already in state.sqlite; no file is read.
  pass B  read text-like files and match against the same index.
  pass C  bottom-k shingle sketch + LSH voting for the remainder.

Binary files (docx/pdf/pptx/xlsx) are left for stage10 to parse first.
"""
from __future__ import annotations

import hashlib
import json
import re
import sqlite3
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from lib import (  # noqa: E402
    DOCS, HTML_EXT, LEGACY, PARSED, RAW, REPORTS, TEXT_EXT, connect,
    normalize, normalized_sha, _now,
)

K = 96                 # sketch size
NEAR_ACCEPT = 0.80     # estimated Jaccard -> treat as already in KB
NEAR_REVIEW = 0.55
SHINGLE = 5
MIN_SHARED = 6         # LSH vote threshold before computing a real Jaccard


def select_targets(con) -> list[dict]:
    """Select files that dedup can evaluate, including stage10 PARSED output."""
    return [dict(r) for r in con.execute(
        "SELECT source_path, status, ext, sha256 FROM raw_files "
        "WHERE status IN ('CANDIDATE_PARSED','PARSED','NEEDS_PARSE') ORDER BY source_path")]


def strip_fm(text: str) -> str:
    return re.sub(r"^---\s*\n.*?\n---\s*\n", "", text, 1, flags=re.S)


def norm_body(text: str) -> str:
    return normalize(strip_fm(text))


def drop_leading_title(t: str, title: str) -> str:
    if not title:
        return t
    for head in (normalize("# " + title), normalize("#" + title)):
        if head and t.startswith(head):
            return t[len(head):]
    return t


def build_kb_index():
    """hash -> kb_rel, using several normalization variants."""
    index: dict[str, str] = {}
    sketches: list[tuple[str, list[int]]] = []
    for path in sorted(DOCS.rglob("*.md")):
        if path.name == "_sidebar.md":
            continue
        rel = path.relative_to(DOCS).as_posix()
        text = path.read_text(errors="replace")
        base = norm_body(text)
        titles = {path.stem}
        m = re.search(r"^title:\s*(.+)$", text.split("\n---", 1)[0], re.M) if text.startswith("---") else None
        if m:
            titles.add(m.group(1).strip().strip('"'))
        for h in {base} | {drop_leading_title(base, t) for t in titles if t}:
            index.setdefault(h, rel)
            # Historical state stores normalized_text_sha256, so index the
            # canonical hash alongside the raw normalized body for a cheap
            # exact-match fast path.
            index.setdefault(normalized_sha(h), rel)
        sketches.append((rel, bottom_k(base)))
    return index, sketches


def bottom_k(norm_text: str, k: int = K) -> list[int]:
    if len(norm_text) < SHINGLE:
        norm_text = (norm_text + " " * SHINGLE)[:SHINGLE]
    seen = set()
    step = 1 if len(norm_text) < 4000 else 2
    for i in range(0, len(norm_text) - SHINGLE + 1, step):
        seen.add(hashlib.blake2b(norm_text[i:i + SHINGLE].encode(), digest_size=8).digest())
        if len(seen) >= 8000:
            break
    return sorted(int.from_bytes(h, "big") for h in seen)[:k]


def jaccard(a: list[int], b: list[int]) -> float:
    if not a or not b:
        return 0.0
    k = min(len(a), len(b))
    sa, sb = set(a[:k]), set(b[:k])
    inter = len(sa & sb)
    union = len(sa | sb)
    return inter / union if union else 0.0


def build_lsh(sketches):
    inv: dict[int, list[int]] = {}
    for i, (_rel, sk) in enumerate(sketches):
        for v in sk:
            inv.setdefault(v, []).append(i)
    return inv


def main() -> int:
    REPORTS.mkdir(parents=True, exist_ok=True)
    con = connect("raw-manifest.sqlite")
    print("building KB index ...", flush=True)
    index, sketches = build_kb_index()
    inv = build_lsh(sketches)
    print(f"  KB variants indexed: {len(index)}  sketches: {len(sketches)}", flush=True)

    legacy = sqlite3.connect(f"file:{LEGACY/'.pipeline/state.sqlite'}?mode=ro", uri=True)
    legacy.row_factory = sqlite3.Row
    hist = {r["source_path"]: r["normalized_text_sha256"]
            for r in legacy.execute(
                "SELECT source_path, normalized_text_sha256 FROM sources "
                "WHERE normalized_text_sha256 IS NOT NULL")}
    print(f"  historical hashes available: {len(hist)}", flush=True)

    targets = select_targets(con)
    print(f"  candidates: {len(targets)}", flush=True)

    counts: Counter = Counter()
    rows = []
    for i, row in enumerate(targets):
        rel, ext = row["source_path"], (row["ext"] or "").lower()
        status, how = None, ""

        # pass A - reuse historical hash, no I/O
        h = hist.get(rel)
        if h and h in index:
            status, how = "EXISTING_ACCEPTED", "hist_exact"

        # pass B - read text-like files, or extracted output from stage10.
        src = RAW / rel
        if row["status"] == "PARSED" and row.get("sha256"):
            parsed = PARSED / row["sha256"][:2] / row["sha256"] / "document.md"
            if parsed.exists():
                src = parsed
        if status is None and (ext in (TEXT_EXT | HTML_EXT) or row["status"] == "PARSED"):
            if src.exists():
                try:
                    text = src.read_text(errors="replace")
                except Exception:
                    text = ""
                if text:
                    base = norm_body(text)
                    if base in index or normalized_sha(base) in index:
                        status, how = "EXISTING_ACCEPTED", "read_exact"
                    else:
                        stripped = drop_leading_title(base, Path(rel).stem)
                        if stripped in index or normalized_sha(stripped) in index:
                            status, how = "EXISTING_ACCEPTED", "read_notitle"

        # pass C - LSH voting
        if status is None and (ext in (TEXT_EXT | HTML_EXT) or row["status"] == "PARSED"):
            if src.exists():
                try:
                    sk = bottom_k(norm_body(src.read_text(errors="replace")))
                except Exception:
                    sk = []
                if sk:
                    votes: Counter = Counter()
                    for v in sk:
                        for idx in inv.get(v, ())[:40]:
                            votes[idx] += 1
                    best, bestv = None, 0.0
                    for idx, c in votes.most_common(8):
                        if c < MIN_SHARED:
                            break
                        v = jaccard(sk, sketches[idx][1])
                        if v > bestv:
                            best, bestv = sketches[idx][0], v
                    if bestv >= NEAR_ACCEPT:
                        status, how = "EXISTING_ACCEPTED", f"near:{bestv:.2f}"
                    elif bestv >= NEAR_REVIEW:
                        status, how = "NEAR_DUP_REVIEW", f"near:{bestv:.2f}"

        if status is None:
            # binary documents still need parsing before they can be judged
            status = ("CANDIDATE_NEW" if row["status"] == "PARSED"
                      or ext in (TEXT_EXT | HTML_EXT) else "NEEDS_PARSE")
            how = "no_match"

        counts[status] += 1
        rows.append({"source_path": rel, "status": status, "match": how})
        con.execute("UPDATE raw_files SET status=?, reason=?, updated_at=? WHERE source_path=?",
                    (status, how, _now(), rel))
        if (i + 1) % 1000 == 0:
            con.commit()
            print(f"  ...{i+1}/{len(targets)} {dict(counts)}", flush=True)
    con.commit()

    with (REPORTS / "rawbook-dedup.jsonl").open("w") as fh:
        for r in rows:
            fh.write(json.dumps(r, ensure_ascii=False) + "\n")
    summary = {"candidates": len(targets), "result": dict(counts),
               "kb_variants": len(index)}
    (REPORTS / "rawbook-dedup-summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2))
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    con.close()
    legacy.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
