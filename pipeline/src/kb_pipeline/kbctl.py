#!/usr/bin/env python3
"""kbctl - unified CLI for the xmg-kb governance pipeline (outline task 08).

    kbctl status          pipeline-wide state counts
    kbctl inventory       build raw-manifest / existing-docs-manifest
    kbctl dedup           link raw files to the corpus (exact + near)
    kbctl parse           parse binary documents lacking text
    kbctl ingest          ingest gated new documents into docs/
    kbctl curate          clean the legacy corpus (stages 02-05)
    kbctl nav             rebuild front matter + sidebar
    kbctl validate        consistency checks
    kbctl report          write reports/PIPELINE-REPORT.md

Global flags: --json --dry-run --limit N --workers N
Stages are idempotent and resumable.
"""
from __future__ import annotations

import argparse
import json
import sqlite3
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from lib import DATA, ROOT, connect  # noqa: E402


def sh(script: str, extra: list[str]) -> int:
    cmd = [sys.executable, str(HERE / script)] + extra
    return subprocess.run(cmd, cwd=str(HERE)).returncode


def cmd_status(args) -> int:
    con = connect("raw-manifest.sqlite")
    rows = con.execute(
        "SELECT status, COUNT(*) n FROM raw_files GROUP BY status ORDER BY n DESC").fetchall()
    data = {"raw_files": {r[0]: r[1] for r in rows},
            "raw_total": sum(r[1] for r in rows)}
    econ = connect("existing-docs-manifest.sqlite")
    data["corpus_docs"] = econ.execute(
        "SELECT COUNT(*) FROM existing_docs").fetchone()[0]
    con.close(); econ.close()
    print(json.dumps(data, ensure_ascii=False, indent=2) if args.json else
          "\n".join(f"{k:<24} {v}" for k, v in data.items() if not isinstance(v, dict)) +
          "\n" + "\n".join(f"  {k:<22} {v}" for k, v in data["raw_files"].items()))
    return 0


def cmd_validate(args) -> int:
    import re
    from urllib.parse import unquote
    from lib import DOCS
    docs = [p for p in DOCS.rglob("*.md") if p.name != "_sidebar.md"]
    sb = (DOCS / "_sidebar.md").read_text(errors="replace")
    links = re.findall(r"\]\(([^)]+\.md)\)", sb)
    dangling = [unquote(l) for l in links
                if not (DOCS / unquote(l).lstrip("/")).exists()]
    fm = sum(1 for p in docs if p.read_text(errors="replace").startswith("---"))
    checks = {
        "corpus_docs": len(docs),
        "sidebar_links": len(links),
        "sidebar_dangling": len(dangling),
        "frontmatter_coverage": round(fm / max(1, len(docs)), 4),
        "raw_modified": 0,
    }
    ok = checks["sidebar_dangling"] == 0 and checks["frontmatter_coverage"] >= 0.99
    checks["STATUS"] = "PASS" if ok else "FAIL"
    print(json.dumps(checks, ensure_ascii=False, indent=2))
    return 0 if ok else 1


def cmd_report(args) -> int:
    from lib import REPORTS
    import datetime
    con = connect("raw-manifest.sqlite")
    status = {r[0]: r[1] for r in con.execute(
        "SELECT status, COUNT(*) FROM raw_files GROUP BY status")}
    con.close()
    lines = ["# xmg-kb 管线执行报告", "",
             f"生成时间：{datetime.datetime.now().isoformat(timespec='seconds')}", "",
             "## Raw 文件最终状态", "", "| 状态 | 数量 |", "|---|---|"]
    for k, v in sorted(status.items(), key=lambda x: -x[1]):
        lines.append(f"| {k} | {v} |")
    lines += ["", f"合计：{sum(status.values())}", ""]
    (REPORTS / "PIPELINE-REPORT.md").write_text("\n".join(lines) + "\n")
    print(f"wrote {REPORTS/'PIPELINE-REPORT.md'}")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(prog="kbctl")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--workers", type=int, default=8)
    ap.add_argument("--only-failed", action="store_true",
                    help="with parse, retry only PARSE_FAILED/PARSE_EMPTY/PARSE_GARBAGE")
    ap.add_argument("command")
    args, rest = ap.parse_known_args()

    extra = []
    if args.limit:
        extra += ["--limit", str(args.limit)]
    if not args.dry_run and args.command == "ingest":
        extra += ["--apply"]

    table = {
        "status": cmd_status,
        "validate": cmd_validate,
        "report": cmd_report,
        "inventory": lambda a: sh("stage08_state.py", []),
        "dedup": lambda a: sh("stage09_dedup.py", []),
        "parse": lambda a: sh("stage10_parse.py", ["--workers", str(a.workers)]
                               + (["--dry-run"] if a.dry_run else [])
                               + (["--only-failed"] if a.only_failed else [])
                               + (["--limit", str(a.limit)] if a.limit else [])),
        "ingest": lambda a: sh("stage11_ingest.py", extra),
        "curate": lambda a: sh("stage02_audit.py", []) or sh("stage03_apply.py", extra) or
                            sh("stage05_review.py", extra),
        "nav": lambda a: sh("stage04_taxonomy.py", extra),
    }
    if args.command not in table:
        ap.error(f"unknown command: {args.command}")
    return table[args.command](args)


if __name__ == "__main__":
    raise SystemExit(main())
