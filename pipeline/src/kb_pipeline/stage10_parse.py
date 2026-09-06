"""Parse binary documents that still lack extracted text (outline task 13).

Only files in NEEDS_PARSE are touched - anything already covered by the
historical parse or matched to the KB is skipped.

Router: PDF -> pdftotext; legacy Office (.doc/.xls/.ppt) and OOXML ->
LibreOffice --convert-to txt.  Results are written under parsed/<sha2>/
and the normalized hash is stored so stage09 can link them.

Reads the configured Raw Evidence root read-only. Parallel, resumable.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import multiprocessing as mp
import re
import sqlite3
import subprocess
import sys
import tempfile
import zipfile
from collections import Counter
from html import unescape
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from lib import (  # noqa: E402
    DATA, OFFICE_EXT, PARSED, PDF_EXT, RAW, REPORTS, connect, normalized_sha, _now,
)


INLINE_RE = re.compile(r"<(?:w:t|a:t|t)\b[^>]*>(.*?)</(?:w:t|a:t|t)>", re.S)
OOXML_EXT = {".docx", ".pptx", ".xlsx"}


def select_todo(con, only_failed: bool = False) -> list[str]:
    """Return parse candidates for the requested retry mode."""
    statuses = ("'PARSE_FAILED','PARSE_EMPTY','PARSE_GARBAGE'" if only_failed
                else "'NEEDS_PARSE'")
    exts = "','".join(sorted(OFFICE_EXT | PDF_EXT | OOXML_EXT | {'.log', '.xml'}))
    q = (f"SELECT source_path FROM raw_files WHERE status IN ({statuses}) "
         f"AND ext IN ('{exts}') ORDER BY source_path")
    return [r[0] for r in con.execute(q)]


def ooxml_text(src: Path) -> str:
    """Extract text from OOXML without spawning LibreOffice (ZIP + XML)."""
    ext = src.suffix.lower()
    out: list[str] = []
    with zipfile.ZipFile(src) as z:
        names = z.namelist()
        if ext == ".docx":
            targets = [n for n in names if n == "word/document.xml"]
        elif ext == ".pptx":
            targets = sorted(n for n in names if re.match(r"ppt/slides/slide\d+\.xml$", n))
        else:
            targets = [n for n in names if n == "xl/sharedStrings.xml"] + \
                      sorted(n for n in names if re.match(r"xl/worksheets/sheet\d+\.xml$", n))
        for n in targets:
            try:
                data = z.read(n).decode("utf-8", "replace")
            except Exception:
                continue
            data = re.sub(r"</(?:w:p|a:p)>", "\n", data)
            parts = INLINE_RE.findall(data)
            chunk = "".join(re.sub(r"<[^>]+>", "", p) for p in parts)
            out.append(unescape(chunk))
    return "\n".join(out)


def extract(src: Path) -> tuple[str, str]:
    ext = src.suffix.lower()
    if ext in PDF_EXT:
        out = subprocess.run(["pdftotext", "-enc", "UTF-8", str(src), "-"],
                             capture_output=True, timeout=240)
        if out.returncode != 0:
            raise RuntimeError("pdftotext failed")
        return out.stdout.decode("utf-8", "replace"), "pdftotext"
    if ext in OOXML_EXT:
        text = ooxml_text(src)
        if len(re.sub(r"\s+", "", text)) < 120:
            raise RuntimeError("ooxml yielded no text")
        return text, "ooxml-inline"
    if ext in OFFICE_EXT:
        with tempfile.TemporaryDirectory() as td, tempfile.TemporaryDirectory() as profile:
            # parallel soffice instances collide on the default user profile
            subprocess.run(
                ["soffice", f"-env:UserInstallation=file://{profile}", "--headless",
                 "--convert-to", "txt:Text", "--outdir", td, str(src)],
                capture_output=True, timeout=300, check=False)
            produced = sorted(Path(td).glob("*.txt"))
            if not produced:
                raise RuntimeError("soffice produced no output")
            return produced[0].read_text(errors="replace"), "libreoffice"
    raise RuntimeError(f"unsupported {ext}")


BASE64_RUN = re.compile(r"[A-Za-z0-9+/]{60,}={0,2}")
MIME_HDR = re.compile(r"(?im)^\s*(MIME-Version|Content-Transfer-Encoding|Content-Type:\s*multipart)")


def looks_like_base64(text: str) -> bool:
    if MIME_HDR.search(text[:2000]):
        return True
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    if not lines:
        return False
    b64 = sum(1 for l in lines if BASE64_RUN.fullmatch(l))
    return b64 > 20 or (b64 / len(lines)) > 0.3


def work(rel: str, write_output: bool = True) -> dict:
    src = RAW / rel
    try:
        if not src.exists():
            return {"rel": rel, "status": "MISSING"}
        text, parser = extract(src)
        compact = re.sub(r"\s+", "", text)
        if len(compact) < 120:
            return {"rel": rel, "status": "PARSE_EMPTY", "chars": len(compact)}
        if looks_like_base64(text):
            return {"rel": rel, "status": "PARSE_GARBAGE", "chars": len(compact)}
        if text.count("\ufffd") / max(1, len(text)) > 0.02:
            return {"rel": rel, "status": "PARSE_GARBAGE", "chars": len(compact)}
        digest = hashlib.sha256(src.read_bytes()).hexdigest()
        text_path = None
        if write_output:
            outdir = PARSED / digest[:2] / digest
            outdir.mkdir(parents=True, exist_ok=True)
            text_path = str(outdir / "document.md")
            Path(text_path).write_text(text)
        return {"rel": rel, "status": "PARSED", "parser": parser,
                "chars": len(text), "norm": normalized_sha(text), "text_path": text_path}
    except Exception as exc:
        return {"rel": rel, "status": "PARSE_FAILED", "error": f"{type(exc).__name__}: {exc}"[:200]}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--workers", type=int, default=6)
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--only-failed", action="store_true")
    ap.add_argument("--dry-run", action="store_true",
                    help="parse and report without writing parsed files or database state")
    args = ap.parse_args()

    if args.dry_run:
        # Open SQLite read-only so even WAL/journal metadata cannot be changed.
        con = sqlite3.connect(f"file:{DATA / 'raw-manifest.sqlite'}?mode=ro", uri=True)
        con.row_factory = sqlite3.Row
    else:
        con = connect("raw-manifest.sqlite")
    todo = select_todo(con, args.only_failed)
    if args.limit:
        todo = todo[:args.limit]
    print(f"to parse: {len(todo)}", flush=True)

    counts: Counter = Counter()
    results = []
    # A top-level partial remains picklable under multiprocessing spawn.
    from functools import partial
    worker = partial(work, write_output=not args.dry_run)
    with mp.Pool(args.workers) as pool:
        for i, res in enumerate(pool.imap_unordered(worker, todo, chunksize=4)):
            counts[res["status"]] += 1
            results.append(res)
            if not args.dry_run:
                con.execute(
                    "UPDATE raw_files SET status=?, parser=?, text_chars=?, normalized_sha=?,"
                    " needs_parse=0, updated_at=?, error=? WHERE source_path=?",
                    (res["status"], res.get("parser"), res.get("chars"), res.get("norm"),
                     _now(), res.get("error"), res["rel"]))
            if (i + 1) % 200 == 0:
                if not args.dry_run:
                    con.commit()
                print(f"  ...{i+1}/{len(todo)} {dict(counts)}", flush=True)
    if not args.dry_run:
        con.commit()

    if not args.dry_run:
        REPORTS.mkdir(parents=True, exist_ok=True)
    if not args.dry_run:
        with (REPORTS / "parse-results.jsonl").open("w") as fh:
            for r in results:
                fh.write(json.dumps(r, ensure_ascii=False) + "\n")
    summary = {"parsed_attempted": len(todo), "result": dict(counts)}
    if not args.dry_run:
        (REPORTS / "parse-summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2))
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    con.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
