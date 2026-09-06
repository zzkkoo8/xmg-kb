#!/usr/bin/env python3
"""Encode chaitin-kb's directory taxonomy into document front matter.

Only fills MISSING keys, never overwrites values that are already present.
Unverifiable fields are written as `unknown` (outline task 16: no fabrication).
Also regenerates docs/_sidebar.md from the cleaned corpus.

  --dry-run   report what would change (default)
  --apply     write front matter and sidebar
"""
from __future__ import annotations

import argparse
import json
import os
import re
from pathlib import Path

from stage02_audit import PRODUCTS, REPORTS, classify_path
from lib import canonical_product

ROOT = Path(os.environ.get("XMG_KB_ROOT", "/srv/xmg-kb"))
DOCS = ROOT / "docs"

FM_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n?", re.S)


def yaml_quote(value: str) -> str:
    if value == "" or re.search(r"[:#\[\]{}&*!|>'\"%@`\n]", value) or value.strip() != value:
        return '"' + value.replace("\\", "\\\\").replace('"', '\\"') + '"'
    return value


def extract_title(text: str, path: Path) -> str:
    body = FM_RE.sub("", text, count=1)
    for line in body.splitlines():
        if line.lstrip().startswith("# "):
            return re.sub(r"^#\s+", "", line.strip()).strip("* ")
    return path.stem


def build_frontmatter(fields: dict) -> str:
    lines = ["---"]
    for key, value in fields.items():
        lines.append(f"{key}: {yaml_quote(str(value))}")
    lines.append("---")
    return "\n".join(lines) + "\n"


def parse_frontmatter(block: str) -> dict:
    fields: dict[str, str] = {}
    for line in block.splitlines():
        m = re.match(r"^([A-Za-z_][A-Za-z0-9_-]*)\s*:\s*(.*)$", line)
        if m:
            fields[m.group(1)] = m.group(2).strip().strip('"\'')
    return fields


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args()
    mode = "APPLY" if args.apply else "DRY-RUN"

    added_fm = 0
    filled_keys = 0
    skipped = 0
    taxonomy_rows = []

    for path in sorted(DOCS.rglob("*.md")):
        if path.name in {"_sidebar.md"} or path.parts[1:2] == ("_nav",):
            continue
        rel = path.relative_to(DOCS)
        text = path.read_text(errors="replace")
        product, module = classify_path(rel)
        product = "unknown" if product == "未分类" else product
        module = "unknown" if module in {"未归类", "根级文件"} else module
        title = extract_title(text, path)

        m = FM_RE.match(text)
        if m:
            fields = parse_frontmatter(m.group(1))
            missing = {k: v for k, v in
                       (("title", title), ("product", product), ("category", module),
                        ("source", "chaitin-kb"))
                       if k not in fields or not fields[k]}
            # normalise a legacy free-form product value onto the taxonomy,
            # keeping the original for traceability
            current = fields.get("product", "")
            canonical, changed = canonical_product(current)
            if changed:
                fields["product_original"] = current
                fields["product"] = canonical
                missing.pop("product", None)
            if not missing and not changed:
                skipped += 1
                taxonomy_rows.append({"path": rel.as_posix(), "product": product,
                                      "category": module, "action": "complete"})
                continue
            fields.update(missing)
            new_block = build_frontmatter(fields)
            new_text = new_block + text[m.end():]
            filled_keys += 1
            action = "filled_keys"
        else:
            fields = {"title": title, "product": product, "category": module,
                      "source": "chaitin-kb"}
            new_text = build_frontmatter(fields) + text
            added_fm += 1
            action = "added_frontmatter"

        if args.apply:
            path.write_text(new_text)
        taxonomy_rows.append({"path": rel.as_posix(), "product": product,
                              "category": module, "action": action})

    # regenerate sidebar over the cleaned corpus
    groups: dict[str, dict[str, list[Path]]] = {}
    for path in sorted(DOCS.rglob("*.md")):
        rel = path.relative_to(DOCS)
        if rel.parts[0] == "_nav" or rel.name in {"_sidebar.md", "index.html"}:
            continue
        product, module = classify_path(rel)
        groups.setdefault(product, {}).setdefault(module, []).append(rel)

    lines = ["- [首页](README.md)", ""]
    for product in sorted(groups):
        lines.append(f"- **{product}**")
        for module in sorted(groups[product]):
            lines.append(f"  - **{module}**")
            for rel in sorted(groups[product][module])[:400]:
                from urllib.parse import quote
                lines.append(f"    - [{rel.stem}]({quote(rel.as_posix())})")
    lines.append("")
    sidebar = "\n".join(lines)
    if args.apply:
        (DOCS / "_sidebar.md").write_text(sidebar)

    REPORTS.mkdir(parents=True, exist_ok=True)
    with (REPORTS / "taxonomy.jsonl").open("w") as fh:
        for row in taxonomy_rows:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")

    actions = {}
    for row in taxonomy_rows:
        actions[row["action"]] = actions.get(row["action"], 0) + 1
    print(f"[{mode}] added_frontmatter={added_fm} filled_keys={filled_keys} "
          f"already_complete={skipped} sidebar_links={sum(1 for l in sidebar.splitlines() if l.strip().startswith('- ['))}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
