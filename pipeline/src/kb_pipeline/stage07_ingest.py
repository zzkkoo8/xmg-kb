#!/usr/bin/env python3
"""Ingest the high-confidence raw-book delta into xmg-kb (outline task 13/19).

Reads the configured Raw Evidence root strictly read-only. Historical manifests reference the
pre-2026-08-20 flat layout, so each file is located by remapping its sha256
through the post-reorg state.sqlite inventory.

  --dry-run   report only (default)
  --apply     write into xmg-kb/docs
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sqlite3
import subprocess
import sys
import tempfile
import unicodedata
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from stage02_audit import (  # reuse the exact gates used on the legacy corpus
    EXCLUDE_PATTERNS, REVIEW_PATTERNS, sensitive_findings, quality_issues,
)
from stage05_review import EXCLUDE_RULES, EXPLICIT_EMPTY, KEEP_GUARD

XMG = Path(os.environ.get("XMG_KB_ROOT", "/srv/xmg-kb"))
RAW = Path(os.environ.get("XMG_KB_RAW_EVIDENCE", "/srv/xmg-kb/evidence"))
LEGACY = Path(os.environ.get("XMG_KB_LEGACY_ROOT", "/srv/xmg-kb/legacy"))
REPORTS = XMG / "reports"
CURATION = LEGACY / "reports/rawdocs-curation-v2"

PRODUCT_DIR = {
    "SafeLine": "01-雷池-SafeLine", "X-Ray": "02-洞鉴-X-Ray",
    "CloudWalker": "03-牧云-CloudWalker", "DSensor": "04-谛听-DSensor",
    "T-Answer": "05-全悉-T-Answer", "Cosmos": "06-万象-Cosmos",
    "ApiSec": "07-ApiSec", "HostSecurity-CSK": "09-主机安全-CSK",
    "硬件知识": "10-硬件知识", "FK01": "12-FK01-网盾", "Yuntu": "13-云图",
    "Reversi": "14-墨攻-Reversi", "CT-DA": "15-CT-DA-数据库审计",
    "CT-AC": "16-CT-AC-上网行为管理", "Matrix": "17-Matrix-纵横",
    "CT-LA": "18-CT-LA-日志审计", "CTDSG-E": "19-CTDSG-E-防火墙",
    "CT-OAM": "20-CT-OAM-堡垒机", "TrafficAnalysis": "21-流量分析预警",
    "CTDSG": "22-CTDSG-深度安全网关", "产品联动": "91-产品联动",
    "FDE": "FDE", "通用基础": "00-通用基础",
}
INGEST_MODULE = "90-原始文档增量"
TEXT_EXT = {".md", ".txt", ".json", ".jsonl", ".yaml", ".yml", ".csv"}
MIN_CHARS = 300


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def strip_html(text: str) -> str:
    text = re.sub(r"(?is)<(script|style).*?</\1>", " ", text)
    text = re.sub(r"(?s)<[^>]+>", " ", text)
    text = re.sub(r"&nbsp;?", " ", text)
    return re.sub(r"\n{3,}", "\n\n", text).strip()


def extract_text(path: Path) -> tuple[str, str]:
    """Return (text, parser). Raises RuntimeError when not extractable."""
    ext = path.suffix.lower()
    if ext in TEXT_EXT:
        return path.read_text(errors="replace"), "direct"
    if ext == ".html" or ext == ".htm":
        return strip_html(path.read_text(errors="replace")), "html-strip"
    if ext == ".pdf":
        out = subprocess.run(["pdftotext", "-enc", "UTF-8", str(path), "-"],
                             capture_output=True, timeout=180)
        if out.returncode != 0:
            raise RuntimeError(f"pdftotext failed: {out.stderr[:120]}")
        return out.stdout.decode("utf-8", "replace"), "pdftotext"
    if ext in {".doc", ".docx", ".xlsx", ".xls", ".ppt", ".pptx"}:
        with tempfile.TemporaryDirectory() as td:
            subprocess.run(["soffice", "--headless", "--convert-to", "txt:Text",
                            "--outdir", td, str(path)],
                           capture_output=True, timeout=300, check=False)
            produced = sorted(Path(td).glob("*.txt"))
            if not produced:
                raise RuntimeError("soffice produced no text")
            return produced[0].read_text(errors="replace"), "libreoffice"
    raise RuntimeError(f"unsupported extension {ext}")


BASE64_RUN = re.compile(r"[A-Za-z0-9+/]{60,}={0,2}")
MIME_HDR = re.compile(r"(?im)^\s*(MIME-Version|Content-Transfer-Encoding|Content-Type:\s*multipart)")
ERROR_PAGE = re.compile(
    r"(?i)(HTTP Error \d|Internet Server Error|Internal Server Error|Server Error in|"
    r"<title>\s*404|页面不存在)")
# competitor brands, consistent with the legacy project's COMPETITOR_RE
COMPETITOR_BRAND = re.compile(r"(?i)(imperva|奇安信|深信服|绿盟|安恒|天融信)")


def looks_like_base64(text: str) -> bool:
    """MHTML/base64 exports convert to clean-looking ASCII that fools garbled checks."""
    if MIME_HDR.search(text[:2000]):
        return True
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    if not lines:
        return False
    b64 = sum(1 for l in lines if BASE64_RUN.fullmatch(l))
    return b64 > 20 or (b64 / len(lines)) > 0.3


def is_garbled(text: str) -> bool:
    if not text.strip():
        return True
    repl = text.count("\ufffd") / max(1, len(text))
    bad = sum(unicodedata.category(c) == "Cc" and c not in "\n\t\r" for c in text) / max(1, len(text))
    return repl > 0.01 or bad > 0.01


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args()
    mode = "APPLY" if args.apply else "DRY-RUN"

    # sha256 -> current (post-reorg) raw path
    con = sqlite3.connect(LEGACY / ".pipeline/state.sqlite")
    sha2path = {r[0]: r[1] for r in con.execute("SELECT source_sha256, source_path FROM sources")}
    con.close()

    extraction = {}
    with (CURATION / "extraction-results.jsonl").open() as fh:
        for line in fh:
            d = json.loads(line)
            extraction[d["file_id"]] = d

    candidates = [json.loads(l) for l in (REPORTS / "rawbook-map.jsonl").open()
                  if json.loads(l)["status"] == "UNMAPPED_NEW_HIGH_CONF"]

    ingested, skipped = [], []
    for cand in candidates:
        fid = cand["file_id"]
        ext = extraction.get(fid, {})
        cur_rel = sha2path.get(ext.get("source_sha256"))
        src = RAW / cur_rel if cur_rel else None
        if not src or not src.exists():
            skipped.append({"file_id": fid, "reason": "raw_path_unresolved"})
            continue
        try:
            text, parser = extract_text(src)
        except Exception as exc:
            skipped.append({"file_id": fid, "reason": f"extract_failed:{type(exc).__name__}",
                            "detail": str(exc)[:120]})
            continue
        if len(re.sub(r"\s+", "", text)) < MIN_CHARS or is_garbled(text):
            skipped.append({"file_id": fid, "reason": "quality_too_short_or_garbled",
                            "chars": len(text)})
            continue

        # --- same gates as the legacy corpus, so ingestion cannot re-pollute --
        gate = None
        if looks_like_base64(text):
            gate = "exclude:base64_or_mhtml_garbage"
        elif ERROR_PAGE.search(text[:2000]) or ERROR_PAGE.search(cur_rel):
            gate = "exclude:error_page_boilerplate"
        elif COMPETITOR_BRAND.search(cur_rel) or COMPETITOR_BRAND.search(text[:4000]):
            gate = "exclude:competitor_brand"
        elif "_待归属附件" in cur_rel:
            gate = "exclude:unattributed_attachment"   # AGENTS.md rule 4: never guess attribution
        if gate is None:
            for name, pattern in EXCLUDE_PATTERNS:
                if re.search(pattern, cur_rel) or re.search(pattern, text[:4000]):
                    gate = f"exclude:{name}"
                    break
        if gate is None:
            for name, pattern in REVIEW_PATTERNS:
                if re.search(pattern, cur_rel) or re.search(pattern, text[:4000]):
                    gate = f"review:{name}"
                    break
        if gate is None:
            for code, rx, _guardable in EXCLUDE_RULES:
                if rx.search(cur_rel + "\n" + text[:1500]) and not KEEP_GUARD.search(cur_rel):
                    gate = f"exclude:{code}"
                    break
        if gate is None:
            sens = sensitive_findings(text)
            if sens:
                gate = f"sensitive:{sens[0]}"
        if gate is None and EXPLICIT_EMPTY.search(text[:1200]):
            gate = "exclude:stub_placeholder"
        if gate is None:
            issues = quality_issues(text)
            if "empty" in issues or "garbled" in issues:
                gate = "quality:P0"
        if gate:
            skipped.append({"file_id": fid, "reason": "gated", "code": gate,
                            "path": cur_rel[:70]})
            continue

        products = cand.get("products") or []
        product = products[0] if products else "unknown"
        dest_dir = XMG / "docs" / PRODUCT_DIR.get(product, "00-通用基础") / INGEST_MODULE
        dest = dest_dir / (Path(cand["relative_path"]).stem[:80] + ".md")

        body = (f"---\n"
                f"title: {json.dumps(Path(cand['relative_path']).stem, ensure_ascii=False)}\n"
                f"product: {product}\n"
                f"category: {INGEST_MODULE}\n"
                f"source: raw-book\n"
                f"raw_path: {cur_rel}\n"
                f"raw_sha256: {ext.get('source_sha256')}\n"
                f"parser: {parser}\n"
                f"review_status: ingested_auto\n"
                f"---\n\n{text.strip()}\n")
        if args.apply:
            dest_dir.mkdir(parents=True, exist_ok=True)
            dest.write_text(body)
        ingested.append({"file_id": fid, "product": product, "parser": parser,
                         "relative_path": cand["relative_path"],
                         "dest": str(dest.relative_to(XMG / "docs")) if dest.parent.exists() else str(dest),
                         "chars": len(text), "written": bool(args.apply)})

    with (REPORTS / "rawbook-ingest.jsonl").open("w") as fh:
        for r in ingested:
            fh.write(json.dumps(r, ensure_ascii=False) + "\n")
    with (REPORTS / "rawbook-ingest-skipped.jsonl").open("w") as fh:
        for r in skipped:
            fh.write(json.dumps(r, ensure_ascii=False) + "\n")

    print(f"[{mode}] candidates={len(candidates)} ingested={len(ingested)} skipped={len(skipped)}")
    for r in skipped:
        print(f"[{mode}]   skip {r['file_id']}: {r['reason']}")
    for r in ingested:
        print(f"[{mode}]   + {r['product']:<12} {r['parser']:<12} {r['chars']:>7}c  {r['dest'][:60]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
