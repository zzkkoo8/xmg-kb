#!/usr/bin/env python3
"""Acceptance test: run one product line through the REAL pipeline and verify.

The pipeline stages are executed unmodified - only their module-level path
constants are redirected at a sandbox, so this exercises the same code paths as
production.  Each check maps to an acceptance criterion in
KB-PIPELINE-OUTLINE-RAGFLOW.md / the chaitin-kb README.

  python3 acceptance_test.py --product 07-ApiSec
  python3 acceptance_test.py --product 07-ApiSec --promote   # on all-PASS only
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import sqlite3
import sys
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import stage02_audit  # noqa: E402
import stage03_apply  # noqa: E402
import stage04_taxonomy  # noqa: E402
import stage05_review  # noqa: E402
from lib import (  # noqa: E402
    CREDENTIAL_RE, CUSTOMER_ID_RE, DOCS as XMG_DOCS, MASK_TOKEN,
    PLACEHOLDER_VALUE, PRODUCT_DIR, REAL_SECRET, ROOT as XMG_ROOT, norm_body,
)

CHAI = Path(os.environ.get("XMG_KB_LEGACY_ROOT", "/srv/xmg-kb/legacy")) / "docs"
SANDBOX = Path("/tmp/kb-acceptance")


def sha_tree(root: Path) -> dict[str, str]:
    out = {}
    for p in sorted(root.rglob("*.md")):
        out[str(p.relative_to(root))] = hashlib.sha256(p.read_bytes()).hexdigest()
    return out


class Runner:
    """Run the real stages against a redirected root."""

    def __init__(self, root: Path):
        self.root = root
        for mod in (stage02_audit, stage03_apply, stage04_taxonomy, stage05_review):
            mod.ROOT = root
            mod.DOCS = root / "docs"
            mod.REPORTS = root / "reports"
        stage03_apply.AUDIT = root / "reports" / "corpus-audit.jsonl"
        stage04_taxonomy.REPORTS = root / "reports"

    def run(self, apply_: bool) -> None:
        sys.argv = ["x"]
        stage02_audit.main()                       # audit (always read-only)
        sys.argv = ["x"] + (["--apply"] if apply_ else [])
        stage03_apply.main()                       # quarantine exclusions
        sys.argv = ["x"] + (["--apply"] if apply_ else [])
        stage04_taxonomy.main()                    # front matter + sidebar
        sys.argv = ["x"] + (["--apply"] if apply_ else [])
        stage05_review.main()                      # resolve review queue
        sys.argv = ["x"] + (["--apply"] if apply_ else [])
        stage04_taxonomy.main()                    # rebuild nav after moves



def unmasked_secret(text: str) -> bool:
    """True only for leaks the pipeline is meant to remove.

    Generic customer-context mentions (客户环境/客户现场) are deliberately
    retained, and documented defaults are not secrets (outline task 06), so
    this checks for real credentials and explicit customer identities that are
    still present after masking.
    """
    for m in CREDENTIAL_RE.finditer(text):
        value = m.group(3).strip().strip("\"'`,;，。、)）]】")
        if MASK_TOKEN in value or PLACEHOLDER_VALUE.match(value):
            continue
        if REAL_SECRET.fullmatch(value):
            return True
    for m in CUSTOMER_ID_RE.finditer(text):
        if MASK_TOKEN not in m.group(2):
            return True
    return False


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--product", default="07-ApiSec")
    ap.add_argument("--promote", action="store_true",
                    help="copy sandbox result into xmg-kb (only if all checks pass)")
    args = ap.parse_args()

    product = args.product
    src = CHAI / product
    if not src.is_dir():
        print(f"product not found: {src}")
        return 1
    source_files = sorted(p for p in src.rglob("*.md"))
    n_source = len(source_files)

    if SANDBOX.exists():
        shutil.rmtree(SANDBOX)
    sb_docs = SANDBOX / "docs" / product
    sb_docs.mkdir(parents=True)
    prod_root = sb_docs  # scope all accounting to the product under test
    (SANDBOX / "reports").mkdir(parents=True)
    # mirror production: docs/README.md exists at the corpus root, so the
    # sidebar home link resolves (its absence was a sandbox artefact, not a bug)
    prod_readme = XMG_DOCS / "README.md"
    if prod_readme.exists():
        shutil.copy2(prod_readme, SANDBOX / "docs" / "README.md")
    else:
        (SANDBOX / "docs" / "README.md").write_text(
            "# xmg-kb 知识语料\n\n本目录按产品线组织，为 xmg-kb 的可检索正文。\n")
    for p in source_files:
        rel = p.relative_to(src)
        (sb_docs / rel).parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(p, sb_docs / rel)

    # ---- C1: baseline of the read-only source -------------------------------
    before = sha_tree(src)

    runner = Runner(SANDBOX)

    # ---- C3: dry-run must not move anything --------------------------------
    runner.run(apply_=False)
    dry_snapshot = sha_tree(prod_root)
    c3_files_untouched = len(dry_snapshot) == n_source

    # ---- real run ----------------------------------------------------------
    runner.run(apply_=True)
    out_docs = sorted(prod_root.rglob("*.md"))
    out_docs = [p for p in out_docs if p.name != "_sidebar.md"]
    after = sha_tree(src)
    c1 = before == after

    # ---- C2: idempotency ---------------------------------------------------
    first = sha_tree(SANDBOX / "docs")
    first_arch = sha_tree(SANDBOX / "_archive") if (SANDBOX / "_archive").exists() else {}
    runner.run(apply_=True)
    second = sha_tree(SANDBOX / "docs")
    second_arch = sha_tree(SANDBOX / "_archive") if (SANDBOX / "_archive").exists() else {}
    c2 = (first == second) and (first_arch == second_arch)

    # ---- content checks ----------------------------------------------------
    n_out = len(out_docs)
    fm_ok = p0 = 0
    bad_product = no_source = secrets = unknown_product = 0
    bodies: dict[str, str] = {}
    dupes = 0
    for p in out_docs:
        text = p.read_text(errors="replace")
        m = re.match(r"^---\s*\n(.*?)\n---", text, re.S)
        if m:
            head = m.group(1)
            if re.search(r"^product:", head, re.M) and re.search(r"^category:", head, re.M):
                fm_ok += 1
            pm = re.search(r"^product:\s*(.+)$", head, re.M)
            if pm:
                val = pm.group(1).strip().strip('"')
                if val == "unknown":
                    unknown_product += 1
                elif val not in PRODUCT_DIR:
                    bad_product += 1
            if re.search(r"^source:", head, re.M):
                pass
            else:
                no_source += 1
        else:
            no_source += 1
        if unmasked_secret(text):
            secrets += 1
        issues = stage02_audit.quality_issues(text)
        if "empty" in issues or "garbled" in issues:
            p0 += 1
        h = norm_body(text)
        if h in bodies:
            dupes += 1
        else:
            bodies[h] = str(p)

    c4 = fm_ok / max(1, n_out) >= 0.99
    c5 = p0 == 0
    c6 = dupes == 0
    c7 = no_source == 0
    c8 = secrets == 0
    c11 = bad_product == 0

    # ---- C9: exclusion traceability + conservation -------------------------
    manifest = SANDBOX / "reports" / "apply-manifest.jsonl"
    review_manifest = SANDBOX / "reports" / "review-exclusion-manifest.jsonl"
    moved = set()
    for mf in (manifest, review_manifest):
        if mf.exists():
            for line in mf.open():
                rec = json.loads(line)
                moved.add(rec.get("original_path") or rec.get("path"))
    archived = sorted((SANDBOX / "_archive").rglob("*.md")) if (SANDBOX / "_archive").exists() else []
    archived = [a for a in archived if a.name != "README.md"]
    n_arch = len(archived)
    c9_count = (n_out + n_arch) == n_source
    c9_trace = all(
        any(str(Path(m).name) == Path(str(a)).name for m in moved) for a in archived
    ) if archived else True

    # ---- C10: navigation integrity ----------------------------------------
    from urllib.parse import unquote
    sb_sidebar = SANDBOX / "docs" / "_sidebar.md"
    dangling = 0
    n_links = 0
    if sb_sidebar.exists():
        links = re.findall(r"\]\(([^)]+\.md)\)", sb_sidebar.read_text(errors="replace"))
        n_links = len(links)
        for l in links:
            if not (SANDBOX / "docs" / unquote(l).lstrip("/")).exists():
                dangling += 1
    c10 = dangling == 0

    checks = [
        ("C1  Raw 0 修改（源库只读）", c1, f"{len(before)} 篇源文档哈希前后一致"),
        ("C2  幂等（重复执行不重复产出）", c2, f"两次运行输出 {len(first)} == {len(second)}，隔离区一致"),
        ("C3  dry-run 不写文件", c3_files_untouched, f"dry-run 后仍为 {n_source} 篇"),
        ("C4  Metadata 完整率 ≥99%", c4, f"{fm_ok}/{n_out} = {fm_ok/max(1,n_out)*100:.1f}%"),
        ("C5  P0 质量未解决 = 0", c5, f"乱码/空文档 {p0} 篇"),
        ("C6  精确重复已聚组", c6, f"重复正文 {dupes} 篇"),
        ("C7  每篇可回溯来源", c7, f"缺 source 字段 {no_source} 篇"),
        ("C8  高风险秘密未进入", c8, f"残留真实凭据 {secrets} 篇"),
        ("C9  排除可追溯 + 数量守恒", c9_count and c9_trace,
         f"入库 {n_out} + 隔离 {n_arch} = {n_out+n_arch}（源 {n_source}），清单可追溯={c9_trace}"),
        ("C10 导航 0 死链", c10, f"{n_links} 条链接，死链 {dangling}"),
        ("C11 禁止编造（产品值合法）", c11, f"非法产品值 {bad_product} 篇；unknown {unknown_product} 篇"),
    ]
    all_pass = all(ok for _n, ok, _d in checks)

    print(f"\n{'='*74}\n验收测试：{product}   源 {n_source} 篇 → 管线输出 {n_out} 篇，隔离 {n_arch} 篇\n{'='*74}")
    for name, ok, detail in checks:
        print(f"  [{'PASS' if ok else 'FAIL'}] {name:<32} {detail}")
    print(f"\n  总体：{'PASS' if all_pass else 'FAIL'}")

    # ---- promote -----------------------------------------------------------
    if args.promote:
        if not all_pass:
            print("\n  存在 FAIL，拒绝写入 xmg-kb（保持原状）")
        else:
            stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
            target = XMG_DOCS / product
            if target.exists():
                arch = XMG_ROOT / f"_archive/acceptance-{stamp}" / product
                arch.parent.mkdir(parents=True, exist_ok=True)
                shutil.move(str(target), str(arch))
                print(f"\n  原 {product} 已隔离至 {arch}")
            shutil.copytree(SANDBOX / "docs" / product, target)
            print(f"  已写入 xmg-kb：{len(list(target.rglob('*.md')))} 篇")

    report = {
        "product": product,
        "source_docs": n_source,
        "pipeline_output": n_out,
        "quarantined": n_arch,
        "checks": [{"check": n, "pass": ok, "detail": d} for n, ok, d in checks],
        "all_pass": all_pass,
    }
    (XMG_ROOT / "reports").mkdir(parents=True, exist_ok=True)
    (XMG_ROOT / "reports" / "acceptance-test.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2))
    print(f"\n  报告：reports/acceptance-test.json   沙箱：{SANDBOX}")
    return 0 if all_pass else 1


if __name__ == "__main__":
    raise SystemExit(main())
