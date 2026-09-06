#!/usr/bin/env python3
"""Resolve the REVIEW queue produced by stage02/stage03.

Per-document outcome, in priority order:
  EXCLUDE  quarantine (reversible) - stubs, generated nav, internal process/QA/PM, competitor research
  REPAIR   fix in place (recorded before/after) - duplicated title lines, unclosed code fences
  MASK     desensitize in place (recorded before/after) - real credentials, explicit customer identity
  KEEP     release into the corpus unchanged

Outline task 06: desensitize only the canonical copy (xmg-kb), never raw.
Outline task 17: every automatic fix must keep before/after/diff/reason/source.

  --dry-run   report only (default)
  --apply     execute
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
from collections import Counter
from datetime import datetime
from pathlib import Path

ROOT = Path(os.environ.get("XMG_KB_ROOT", "/srv/xmg-kb"))
DOCS = ROOT / "docs"
REPORTS = ROOT / "reports"

FM_RE = re.compile(r"^---\s*\n.*?\n---\s*\n?", re.S)

# Product documentation must never be dropped by a keyword rule.
KEEP_GUARD = re.compile(
    r"(白皮书|产品介绍|产品概述|使用手册|用户手册|配置手册|安装手册|部署指南|配置指南"
    r"|运维手册|快速入门|最佳实践|FAQ|常见问题|API参考|接口文档)"
)

PLACEHOLDER_MARK = re.compile(r"(需补充|待补充|内容为空|暂无正文|待完善|TODO)")

# Only an explicit "this page is empty" statement makes a stub.  A short doc
# that merely contains the word 需补充 is still real content (e.g. a 438-char
# tuning note), so mere keyword presence must not trigger exclusion.
EXPLICIT_EMPTY = re.compile(
    r"(内容为空|暂无正文|仅保留标题|内容待补充|此文档待补充|当前无内容|页面暂无|暂无内容)")

# --- exclusion rules: (code, regex over path+head, guardable) -----------------
EXCLUDE_RULES = [
    ("internal_qa_report", re.compile(r"(测试报告|验收报告|测试计划|压测报告|测试方案)"), True),
    ("internal_pm", re.compile(r"(排期规划|排期|里程碑|项目计划|任务追踪|需求拆解|执行规范|项目管理规范|项目管理执行)"), True),
    ("internal_process", re.compile(r"(售后体系|工单模板|参会人统计|过程记录|述职|CRM\s*地址|邮件形式|周报|月报)"), True),
    ("competitor_research", re.compile(r"(竞品|友商|调研报告|产品对比|RSAC)"), True),
    ("training_schedule", re.compile(r"(培训日程|赋能培训日程|学习计划)"), True),
]

from lib import (CREDENTIAL_RE, CUSTOMER_ID_RE, MASK_TOKEN, write_manifest,
                 PLACEHOLDER_VALUE, REAL_SECRET)  # shared with the detector (no \\b)
PLACEHOLDER_VALUE = re.compile(
    r"(?i)^(?:admin|root|test|demo|example|changeme|password|passwd|123456|1234|111111"
    r"|x{3,}|\*{3,}|xxx|your[_-]?password|<[^>]*>|\{\{[^}]*\}\})$")

# only explicit identity assignments are masked; generic "客户现场" is not a leak
CODE_FENCE_RE = re.compile(r"```.*?```", re.S)


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def compact_len(text: str) -> int:
    return len(re.sub(r"\s+", "", text))


HEADING_RE = re.compile(r"^#{1,6}\s+(.*\S)\s*$")


def dedupe_title_block(text: str) -> tuple[str, int]:
    """Drop a heading that immediately repeats the previous heading.

    Only consecutive headings (blank lines allowed between) are collapsed, so
    the conversion artifact "# title / # title" is fixed without touching
    repeated log lines or list bullets, which can be real evidence.
    """
    lines = text.split("\n")
    out: list[str] = []
    removed = 0
    last_heading: str | None = None
    content_since = False
    for line in lines[:40]:
        m = HEADING_RE.match(line)
        if m:
            key = m.group(1)
            if key == last_heading and not content_since:
                removed += 1
                continue
            last_heading = key
            content_since = False
            out.append(line)
            continue
        if line.strip():
            content_since = True
        out.append(line)
    return "\n".join(out + lines[40:]), removed


def close_code_fences(text: str) -> tuple[str, int]:
    if text.count("```") % 2 == 0:
        return text, 0
    return text.rstrip("\n") + "\n```\n", 1


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args()
    mode = "APPLY" if args.apply else "DRY-RUN"

    audit = [json.loads(l) for l in (REPORTS / "corpus-audit.jsonl").open()]
    targets = [r for r in audit if r["decision"] == "REVIEW"]

    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    archive = ROOT / f"_archive/review-excluded-{stamp}"
    resolutions: list[dict] = []
    counts: Counter = Counter()

    for rec in targets:
        path = DOCS / rec["path"]
        if not path.exists():
            continue
        text = path.read_text(errors="replace")
        body = FM_RE.sub("", text, count=1)
        head = (rec["path"] + "\n" + body[:1500])
        guard_hit = bool(KEEP_GUARD.search(rec["path"]))

        action, detail = "KEEP", {}

        # ---- EXCLUDE -------------------------------------------------------
        if EXPLICIT_EMPTY.search(body[:1200]) or compact_len(body) < 200:
            action, detail = "EXCLUDE", {"code": "stub_placeholder"}
        elif rec["path"].startswith("_nav/"):
            action, detail = "EXCLUDE", {"code": "nav_generated"}
        elif "toc_only" in rec["issues"] or "too_short" in rec["issues"]:
            action, detail = "EXCLUDE", {"code": "quality_stub"}
        else:
            for code, rx, guardable in EXCLUDE_RULES:
                if rx.search(head) and not (guardable and guard_hit):
                    action, detail = "EXCLUDE", {"code": code}
                    break

        # ---- REPAIR / MASK -------------------------------------------------
        new_text = text
        if action == "KEEP":
            before = sha256_text(text)
            repaired, removed = dedupe_title_block(text)
            repaired, fences = close_code_fences(repaired)
            if removed or fences:
                new_text = repaired
                action = "REPAIR"
                detail = {"dupe_lines_removed": removed, "fences_closed": fences}

            masked = 0
            spans = [(m.start(), m.end()) for m in CODE_FENCE_RE.finditer(new_text)]

            def mask_cred(m):
                nonlocal masked
                value = m.group(3).strip().strip("\"'`,;，。、)）]】")
                if any(s <= m.start() < e for s, e in spans):
                    return m.group(0)
                if PLACEHOLDER_VALUE.match(value) or not REAL_SECRET.fullmatch(value):
                    return m.group(0)
                masked += 1
                return f"{m.group(1)}{m.group(2)}{MASK_TOKEN}"

            new_text = CREDENTIAL_RE.sub(mask_cred, new_text)

            def mask_customer(m):
                nonlocal masked
                masked += 1
                return f"{m.group(1)}：{MASK_TOKEN}"

            new_text = CUSTOMER_ID_RE.sub(mask_customer, new_text)

            if masked:
                action = "MASK" if action != "REPAIR" else "REPAIR_MASK"
                detail["masked"] = masked
            if action in {"REPAIR", "MASK", "REPAIR_MASK"}:
                detail["sha256_before"] = before
                detail["sha256_after"] = sha256_text(new_text)

        # ---- execute -------------------------------------------------------
        if action == "EXCLUDE":
            if args.apply:
                target = archive / rec["path"]
                target.parent.mkdir(parents=True, exist_ok=True)
                path.replace(target)
        elif action != "KEEP" and args.apply:
            path.write_text(new_text)

        counts[action] += 1
        resolutions.append({"path": rec["path"], "product": rec["product"],
                            "action": action, "detail": detail,
                            "reasons": rec["reasons"]})

    REPORTS.mkdir(parents=True, exist_ok=True)
    with (REPORTS / "review-resolution.jsonl").open("w") as fh:
        for r in resolutions:
            fh.write(json.dumps(r, ensure_ascii=False) + "\n")
    exclusion_rows = [
        {"original_path": r["path"],
         "archived_to": str(archive.relative_to(ROOT) / r["path"]),
         "code": r["detail"]["code"], "moved": bool(args.apply)}
        for r in resolutions if r["action"] == "EXCLUDE"
    ]
    n_records = write_manifest(REPORTS / "review-exclusion-manifest.jsonl", exclusion_rows)
    print(f"[{mode}] review-exclusion-manifest records={n_records} (this run {len(exclusion_rows)})")

    print(f"[{mode}] review_queue={len(targets)}")
    for action, n in counts.most_common():
        print(f"[{mode}]   {action:<12} {n}")
    codes = Counter(r["detail"].get("code") for r in resolutions if r["action"] == "EXCLUDE")
    for code, n in codes.most_common():
        print(f"[{mode}]     exclude:{code:<22} {n}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
