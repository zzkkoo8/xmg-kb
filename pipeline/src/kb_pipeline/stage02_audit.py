#!/usr/bin/env python3
"""Audit the xmg-kb corpus against chaitin-kb's product/module taxonomy.

Read-only.  Produces:
  reports/corpus-audit.jsonl   one record per document
  reports/corpus-audit-summary.json
  reports/corpus-audit.md

Decision model (conservative: prefer REVIEW over EXCLUDE):
  KEEP     - product knowledge, usable as-is
  REVIEW   - ambiguous; needs a human call before it enters the KB
  EXCLUDE  - matches the outline's hard exclusion list, or fails P0 quality
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import sys
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from lib import CREDENTIAL_RE, MASK_TOKEN, PLACEHOLDER_VALUE

ROOT = Path(os.environ.get("XMG_KB_ROOT", "/srv/xmg-kb"))
DOCS = ROOT / "docs"
REPORTS = ROOT / "reports"

# --- chaitin-kb taxonomy: product from first path segment ---------------------
PRODUCTS = {
    "00-通用基础": "通用基础", "01-雷池-SafeLine": "SafeLine", "02-洞鉴-X-Ray": "X-Ray",
    "03-牧云-CloudWalker": "CloudWalker", "04-谛听-DSensor": "DSensor",
    "05-全悉-T-Answer": "T-Answer", "06-万象-Cosmos": "Cosmos", "07-ApiSec": "ApiSec",
    "09-主机安全-CSK": "HostSecurity-CSK", "10-硬件知识": "硬件知识",
    "12-FK01-网盾": "FK01", "13-云图": "Yuntu", "14-墨攻-Reversi": "Reversi",
    "15-CT-DA-数据库审计": "CT-DA", "16-CT-AC-上网行为管理": "CT-AC",
    "17-Matrix-纵横": "Matrix", "18-CT-LA-日志审计": "CT-LA",
    "19-CTDSG-E-防火墙": "CTDSG-E", "20-CT-OAM-堡垒机": "CT-OAM",
    "21-流量分析预警": "TrafficAnalysis", "22-CTDSG-深度安全网关": "CTDSG",
    "91-产品联动": "产品联动", "FDE": "FDE",
}

# Outline task 04 / README: content that must never enter the corpus.
EXCLUDE_PATTERNS = [
    ("专利资质", r"(专利|软著|软件著作权|商标|资质|CMMI|logo\s*申请|等保测评申请)"),
    ("人力行政", r"(招聘|应聘|考勤|薪资|薪酬|绩效|报销|差旅|入职|离职|述职|组织架构|人员编制)"),
    ("商务合同", r"(商机|投标|招标|中标|报价|合同|NDA|保密协议|维保政策|销售业绩|销售成绩|商务谈判|回款)"),
    ("资产管理", r"(资产申请|发货申请|出入库|领用|固定资产|设备借用)"),
    ("行政值班", r"(值班排班|排班表|工单模板|行政|会议室|团建|年会)"),
    ("会议汇报", r"(会议纪要|例会|周报|月报|季度汇报|述职汇报|访谈记录|汇报材料)"),
    ("客户信息", r"(客户清单|客户案例集|客户商机|客户信息表|联系人名单|交付客户)"),
    ("制度规范", r"(部门日常规范|公司制度|行为规范|管理办法|奖惩|考勤制度)"),
]
# Ambiguous: may still be technical -> REVIEW, not EXCLUDE.
REVIEW_PATTERNS = [
    ("竞品调研", r"(竞品|调研报告|产品对比|友商|对比分析)"),
    ("项目管理", r"(项目复盘|项目管理|需求拆解|任务追踪|项目计划|里程碑|风险评估)"),
    ("测试验收", r"(测试报告|验收报告|测试用例|压测报告|测试计划)"),
    ("内部培训", r"(培训日程|赋能培训|新人学习|学习计划|考核题)"),
    ("待补占位", r"(待补充|需补充|TODO|待完善|占位|暂缺)"),
]

SENSITIVE_PATTERNS = {
    "credential": CREDENTIAL_RE,
    # require an explicit customer marker; the generic "某公司" form matched ordinary prose
    "customer": r"(客户名称|客户环境|客户现场|客户地址|客户名称：|某某客户|某某(?:公司|集团|医院|银行|证券))",
    "internal_ip": r"\b(?:10\.\d+\.\d+\.\d+|192\.168\.\d+\.\d+|172\.(?:1[6-9]|2\d|3[01])\.\d+\.\d+)\b",
}

# Outline task 06: a pwd in a doc example is not a leak.  Only real-looking
# values found OUTSIDE code fences escalate to review.
CODE_FENCE_RE = re.compile(r"```.*?```", re.S)


def code_fence_spans(text: str) -> list[tuple[int, int]]:
    return [(m.start(), m.end()) for m in CODE_FENCE_RE.finditer(text)]


def in_spans(pos: int, spans: list[tuple[int, int]]) -> bool:
    return any(start <= pos < end for start, end in spans)


def sensitive_findings(text: str) -> list[str]:
    """Classify sensitive hits; return only the ones that justify review.

    Outline task 06 categories: TECHNICAL_EXAMPLE / PUBLIC_DEFAULT_CREDENTIAL
    are recorded as findings but must not block a document.
    """
    spans = code_fence_spans(text)
    findings: list[str] = []

    for m in re.finditer(CREDENTIAL_RE, text):
        value = (m.group(3) or "").strip().strip("\"'`,;，。、)）]】")
        if in_spans(m.start(), spans):
            continue  # documentation example inside a code block
        if PLACEHOLDER_VALUE.match(value) or not value:
            continue  # public default / placeholder credential
        if MASK_TOKEN in value:
            continue  # already desensitised by a previous run
        # a real secret is machine-readable, not Chinese prose ("密码：识别比较准确")
        if not re.fullmatch(r"[A-Za-z0-9!@#$%^&*_+\-./=]{6,}", value):
            continue
        findings.append("sensitive:real_credential")
        break

    if re.search(SENSITIVE_PATTERNS["customer"], text):
        findings.append("sensitive:customer")

    # RFC1918 in prose alone is not a leak; flag only when combined with
    # customer/credential context, otherwise record as a benign finding.
    ip_outside_code = [
        m for m in re.finditer(SENSITIVE_PATTERNS["internal_ip"], text)
        if not in_spans(m.start(), spans)
    ]
    if ip_outside_code and ("sensitive:customer" in findings or "sensitive:real_credential" in findings):
        findings.append("sensitive:internal_ip_with_context")

    return findings


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def normalize_text(text: str) -> str:
    text = unicodedata.normalize("NFKC", text)
    text = re.sub(r"^---\s*\n.*?\n---\s*\n", "", text, 1, flags=re.S)
    return re.sub(r"\s+", "", text)


def classify_path(rel: Path):
    """Derive product/module from the chaitin-kb directory taxonomy."""
    parts = rel.parts
    if len(parts) == 1:
        return "未分类", "根级文件"
    product_dir = parts[0]
    product = PRODUCTS.get(product_dir, "未分类")
    if len(parts) == 2:
        # loose file sitting directly in the product root -> uncategorized
        return product, "未归类"
    return product, parts[1]


def quality_issues(text: str) -> list[str]:
    issues: list[str] = []
    compact = normalize_text(text)
    if not compact:
        return ["empty"]
    if len(compact) < 80:
        issues.append("too_short")
    repl = text.count("\ufffd") / max(1, len(text))
    bad = sum(unicodedata.category(c) == "Cc" and c not in "\n\t\r" for c in text) / max(1, len(text))
    if repl > 0.01 or bad > 0.01:
        issues.append("garbled")
    lines = [x.strip() for x in text.splitlines() if x.strip()]
    if lines:
        repetition = 1 - len(set(lines)) / len(lines)
        if len(lines) > 20 and repetition > 0.45:
            issues.append("high_line_repetition")
    if len(compact) < 500 and sum(1 for x in lines if re.match(r"^(目录|第?\d+[.、])", x)) > 5:
        issues.append("toc_only")
    if text.count("```") % 2 == 1:
        issues.append("unclosed_code_fence")
    return issues


def main() -> int:
    REPORTS.mkdir(parents=True, exist_ok=True)
    records = []
    for path in sorted(DOCS.rglob("*.md")):
        rel = path.relative_to(DOCS)
        raw = path.read_bytes()
        try:
            text = raw.decode("utf-8")
        except UnicodeDecodeError:
            text = raw.decode("utf-8", "replace")
        product, module = classify_path(rel)
        issues = quality_issues(text)
        has_fm = text.startswith("---")

        reasons: list[str] = []
        decision = "KEEP"

        # sensitive -> review only for genuinely risky hits
        for finding in sensitive_findings(text):
            reasons.append(finding)
            decision = "REVIEW"

        # hard exclusion list
        for name, pattern in EXCLUDE_PATTERNS:
            if re.search(pattern, str(rel)) or re.search(pattern, text[:4000]):
                reasons.append(f"exclude:{name}")
                decision = "EXCLUDE"
                break

        if decision != "EXCLUDE":
            for name, pattern in REVIEW_PATTERNS:
                if re.search(pattern, str(rel)) or re.search(pattern, text[:4000]):
                    reasons.append(f"review:{name}")
                    decision = "REVIEW"
                    break

        # P0 quality failures override to EXCLUDE
        if "empty" in issues or "garbled" in issues:
            reasons.append("quality:P0")
            decision = "EXCLUDE"
        elif issues:
            reasons.append("quality:P1")
            if decision == "KEEP":
                decision = "REVIEW"

        records.append({
            "path": rel.as_posix(),
            "product": product,
            "module": module,
            "sha256": sha256_bytes(raw),
            "size": len(raw),
            "has_frontmatter": has_fm,
            "issues": issues,
            "reasons": reasons,
            "decision": decision,
        })

    # exact duplicate grouping by content hash
    by_hash: dict[str, list[dict]] = defaultdict(list)
    for r in records:
        by_hash[r["sha256"]].append(r)
    dup_groups = 0
    dup_extra = 0
    for digest, group in by_hash.items():
        if len(group) < 2:
            continue
        dup_groups += 1
        group.sort(key=lambda r: r["path"])
        for extra in group[1:]:
            dup_extra += 1
            extra["decision"] = "EXCLUDE"
            extra["reasons"].append("duplicate:exact")

    with (REPORTS / "corpus-audit.jsonl").open("w") as fh:
        for r in records:
            fh.write(json.dumps(r, ensure_ascii=False) + "\n")

    decisions = Counter(r["decision"] for r in records)
    products = Counter(r["product"] for r in records)
    modules = Counter(r["module"] for r in records)
    reason_counts: Counter = Counter()
    for r in records:
        for reason in r["reasons"]:
            reason_counts[reason] += 1

    summary = {
        "total_documents": len(records),
        "decisions": dict(decisions),
        "duplicate_groups": dup_groups,
        "duplicate_extra_files": dup_extra,
        "missing_frontmatter": sum(1 for r in records if not r["has_frontmatter"]),
        "products": dict(products.most_common()),
        "modules_top": dict(modules.most_common(25)),
        "uncategorized": modules.get("未归类", 0),
        "issues": dict(reason_counts.most_common()),
    }
    (REPORTS / "corpus-audit-summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2))

    lines = [
        "# xmg-kb 语料审计报告",
        "",
        f"- 文档总数：{len(records)}",
        f"- KEEP：{decisions['KEEP']} / REVIEW：{decisions['REVIEW']} / EXCLUDE：{decisions['EXCLUDE']}",
        f"- 精确重复组：{dup_groups}（额外文件 {dup_extra}）",
        f"- 缺 front matter：{summary['missing_frontmatter']}",
        f"- 未归类（散落在产品根目录）：{summary['uncategorized']}",
        "",
        "## 判定原因分布",
        "",
        "| 原因 | 数量 |",
        "|---|---|",
    ]
    for reason, count in reason_counts.most_common():
        lines.append(f"| {reason} | {count} |")
    lines += ["", "## 产品分布", "", "| 产品 | 数量 |", "|---|---|"]
    for product, count in products.most_common():
        lines.append(f"| {product} | {count} |")
    (REPORTS / "corpus-audit.md").write_text("\n".join(lines) + "\n")

    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
