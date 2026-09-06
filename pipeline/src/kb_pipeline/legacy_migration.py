"""Evidence-based Legacy -> xmg mapping primitives.

The module deliberately has no write side effects.  Callers provide the
already-trusted target hashes (normally from ``data/existing-docs-manifest``)
and governance manifests, then decide whether to persist the returned rows.
"""

from __future__ import annotations

from dataclasses import dataclass
import json
import os
from pathlib import Path, PurePosixPath
import sqlite3
import subprocess
from typing import Iterable


ALLOWED_FINAL_STATES = {
    "MIGRATED_REUSED",
    "MIGRATED_TRANSFORMED",
    "MERGED_CANONICAL",
    "DUPLICATE_CONFIRMED",
    "ARCHIVE_ONLY",
    "REJECTED_INVALID",
    "NEEDS_REPAIR",
    "UNMAPPED",
}


@dataclass(frozen=True)
class MigrationResult:
    rows: list[dict]

    @property
    def unmapped(self) -> int:
        return sum(row["final_state"] == "UNMAPPED" for row in self.rows)

    @property
    def counts(self) -> dict[str, int]:
        return {state: sum(row["final_state"] == state for row in self.rows)
                for state in sorted(ALLOWED_FINAL_STATES)}


def _read_jsonl(path: Path | None) -> list[dict]:
    if path is None:
        return []
    rows: list[dict] = []
    with path.open(encoding="utf-8") as handle:
        for line_no, line in enumerate(handle, 1):
            if not line.strip():
                continue
            try:
                value = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(f"invalid JSONL at {path}:{line_no}") from exc
            if not isinstance(value, dict):
                raise ValueError(f"JSONL row is not an object at {path}:{line_no}")
            rows.append(value)
    return rows


def _relative(value: object) -> str:
    if not isinstance(value, str) or not value:
        raise ValueError("mapping path must be a non-empty string")
    raw = value.replace("\\", "/")
    if raw.startswith("/"):
        raise ValueError(f"absolute mapping path rejected: {value}")
    if raw == "docs":
        raise ValueError("docs directory is not a knowledge file")
    if raw.startswith("docs/"):
        raw = raw[5:]
    if raw.startswith("/"):
        raise ValueError(f"absolute mapping path rejected: {value}")
    path = PurePosixPath(raw)
    if not path.parts or any(part in {"", ".", ".."} for part in path.parts):
        raise ValueError(f"unsafe mapping path rejected: {value}")
    return path.as_posix()


def _governance(paths: Iterable[Path]) -> dict[str, tuple[str, dict]]:
    result: dict[str, tuple[str, dict]] = {}
    for manifest in paths:
        for row in _read_jsonl(manifest):
            raw_path = row.get("original_path", row.get("original", row.get("path")))
            if raw_path is None:
                continue
            rel = _relative(raw_path)
            if manifest.name.startswith("review-exclusion"):
                decision = "ARCHIVE_ONLY"
                evidence = {"code": row.get("code"), "archive_target": row.get("archived_to")}
            elif manifest.name.startswith("junk"):
                decision = "REJECTED_INVALID"
                evidence = {"reason": row.get("reason", "invalid")}
            else:
                decision = "ARCHIVE_ONLY"
                evidence = {"reasons": row.get("reasons", [])}
            previous = result.get(rel)
            if previous and previous[0] != decision:
                raise ValueError(f"conflicting governance evidence for {rel}")
            result[rel] = (decision, evidence)
    return result


def build_mapping(
    *,
    legacy_manifest: Path,
    xmg_docs: Path,
    xmg_hashes: dict[str, str],
    excluded_manifests: Iterable[Path],
    junk_manifest: Path | None,
    archive_root: Path,
) -> MigrationResult:
    """Build one deterministic final-state row for every Legacy docs candidate."""

    governance_paths = list(excluded_manifests)
    if junk_manifest is not None:
        governance_paths.append(junk_manifest)
    decisions = _governance(governance_paths)
    rows: list[dict] = []
    seen: set[str] = set()

    for source in _read_jsonl(legacy_manifest):
        source_path = source.get("path")
        # The historical manifest also contains repository-level metadata and
        # scripts.  Knowledge migration is deliberately limited to docs/*.md;
        # the other assets remain covered by the Legacy archive itself.
        if not isinstance(source_path, str) or not source_path.replace("\\", "/").startswith("docs/"):
            continue
        if not source_path.replace("\\", "/").lower().endswith(".md"):
            continue
        rel = _relative(source_path)
        if rel in seen:
            raise ValueError(f"duplicate Legacy path: {rel}")
        seen.add(rel)
        target = xmg_docs / rel
        target_hash = xmg_hashes.get(rel)
        source_hash = source.get("file_sha256")
        if not isinstance(source_hash, str) or len(source_hash) != 64:
            raise ValueError(f"missing Legacy SHA-256 for {rel}")
        row = {
            "legacy_path": rel,
            "legacy_sha256": source_hash,
            "legacy_normalized_sha256": source.get("normalized_text_sha256"),
            "title": source.get("title"),
            "product": source.get("product"),
            "version": source.get("version"),
            "target": None,
            "target_sha256": None,
            "archive_target": None,
            "raw_source": source.get("source_path") or None,
            "reason": None,
        }
        if target.exists() and not target.is_file():
            raise ValueError(f"xmg target is not a file: {rel}")
        if rel == "_sidebar.md":
            # Generated navigation is an archiveable artifact, never a
            # knowledge target.  It is intentionally absent from the xmg
            # knowledge manifest.
            row["final_state"] = "ARCHIVE_ONLY"
            row["archive_target"] = str(archive_root / rel)
            row["reason"] = "generated_navigation"
        elif target.exists() and target_hash is None:
            row["final_state"] = "NEEDS_REPAIR"
            row["reason"] = "target hash missing from xmg manifest"
        elif target.exists():
            row["final_state"] = (
                "MIGRATED_REUSED" if target_hash == source_hash else "MIGRATED_TRANSFORMED"
            )
            row["target"] = f"docs/{rel}"
            row["target_sha256"] = target_hash
        elif rel in decisions:
            decision, evidence = decisions[rel]
            row["final_state"] = decision
            row["archive_target"] = str(archive_root / rel)
            row["reason"] = evidence.get("reason") or evidence.get("code") or evidence.get("reasons")
        else:
            row["final_state"] = "UNMAPPED"
            row["reason"] = "no xmg target or governance evidence"
        rows.append(row)

    return MigrationResult(rows=rows)


def validate_mapping(rows: list[dict], *, xmg_root: Path,
                     expected_total: int | None = None) -> dict:
    """Validate durable mapping invariants without mutating any source."""
    blockers: list[str] = []
    seen: set[str] = set()
    for index, row in enumerate(rows, 1):
        try:
            rel = _relative(row.get("legacy_path"))
        except ValueError as exc:
            blockers.append(f"row {index}: {exc}")
            continue
        if rel in seen:
            blockers.append(f"duplicate legacy path: {rel}")
        seen.add(rel)
        state = row.get("final_state")
        if state not in ALLOWED_FINAL_STATES:
            blockers.append(f"{rel}: invalid final_state {state!r}")
            continue
        if state in {"MIGRATED_REUSED", "MIGRATED_TRANSFORMED", "MERGED_CANONICAL", "DUPLICATE_CONFIRMED"}:
            target = row.get("target")
            if not isinstance(target, str):
                blockers.append(f"{rel}: migrated state missing target")
            else:
                try:
                    target_rel = _relative(target)
                    target_path = xmg_root / "docs" / target_rel
                    if not target_path.is_file():
                        blockers.append(f"{rel}: target missing {target}")
                except ValueError as exc:
                    blockers.append(f"{rel}: {exc}")
            if state == "MIGRATED_REUSED" and row.get("legacy_sha256") != row.get("target_sha256"):
                blockers.append(f"{rel}: reused hash mismatch")
            if state == "MIGRATED_TRANSFORMED" and row.get("legacy_sha256") == row.get("target_sha256"):
                blockers.append(f"{rel}: transformed hash is unchanged")
        if state == "ARCHIVE_ONLY" and not isinstance(row.get("archive_target"), str):
            blockers.append(f"{rel}: archive-only row missing archive_target")
        if state in {"REJECTED_INVALID", "NEEDS_REPAIR"} and not row.get("reason"):
            blockers.append(f"{rel}: {state} row missing reason")
    if expected_total is not None and len(rows) != expected_total:
        blockers.append(f"mapping total {len(rows)} != expected {expected_total}")
    unmapped = sum(row.get("final_state") == "UNMAPPED" for row in rows)
    if unmapped:
        blockers.append(f"UNMAPPED={unmapped}")
    counts = {state: sum(row.get("final_state") == state for row in rows)
              for state in sorted(ALLOWED_FINAL_STATES)}
    return {"gate": "PASS" if not blockers else "BLOCKED",
            "total": len(rows), "counts": counts, "unmapped": unmapped,
            "blockers": blockers}


def load_xmg_hashes(sqlite_path: Path) -> dict[str, str]:
    """Read xmg's existing-doc manifest without opening it in write mode."""
    uri = f"file:{sqlite_path.resolve()}?mode=ro"
    with sqlite3.connect(uri, uri=True) as con:
        rows = con.execute("SELECT path, sha256 FROM existing_docs").fetchall()
    return {_relative(path): sha for path, sha in rows if isinstance(sha, str)}


def _atomic_write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(f".{path.name}.tmp-{os.getpid()}")
    try:
        temp.write_text(content, encoding="utf-8")
        os.replace(temp, path)
    finally:
        if temp.exists():
            temp.unlink()


def write_outputs(result: MigrationResult, *, xmg_root: Path, migration_time: str,
                  migration_commit: str) -> None:
    """Publish mapping/manifests atomically under xmg state only."""
    state = xmg_root / "state"
    legacy_manifest = state / "manifests/legacy-chaitin-kb/legacy-knowledge-manifest.jsonl"
    xmg_manifest = state / "manifests/xmg-kb-knowledge-manifest.jsonl"
    mapping = state / "mappings/legacy-to-xmg.jsonl"
    summary = state / "provenance/legacy-migration-summary.json"
    legacy_rows = []
    xmg_rows = []
    mapping_rows = []
    for row in result.rows:
        base = {"legacy_path": row["legacy_path"], "legacy_sha256": row["legacy_sha256"],
                "legacy_normalized_sha256": row.get("legacy_normalized_sha256"),
                "title": row.get("title"), "product": row.get("product"),
                "version": row.get("version"), "migration_time": migration_time,
                "migration_commit": migration_commit}
        legacy_rows.append(base)
        if row.get("target"):
            xmg_rows.append({"target": row["target"], "legacy_path": row["legacy_path"],
                             "legacy_sha256": row["legacy_sha256"],
                             "final_state": row["final_state"],
                             "migration_time": migration_time,
                             "migration_commit": migration_commit})
        mapping_rows.append({**row, "migration_time": migration_time,
                             "migration_commit": migration_commit})
    _atomic_write(legacy_manifest, "".join(json.dumps(v, ensure_ascii=False, sort_keys=True) + "\n" for v in legacy_rows))
    _atomic_write(xmg_manifest, "".join(json.dumps(v, ensure_ascii=False, sort_keys=True) + "\n" for v in xmg_rows))
    _atomic_write(mapping, "".join(json.dumps(v, ensure_ascii=False, sort_keys=True) + "\n" for v in mapping_rows))
    _atomic_write(summary, json.dumps({"migration_time": migration_time,
                                       "migration_commit": migration_commit,
                                       "counts": result.counts,
                                       "total": len(result.rows),
                                       "unmapped": result.unmapped},
                                      ensure_ascii=False, indent=2) + "\n")


def _git_commit(root: Path) -> str:
    try:
        return subprocess.run(
            ["git", "--git-dir=.xmg-git", "--work-tree=.", "rev-parse", "HEAD"],
            cwd=root, check=True, capture_output=True, text=True,
        ).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return "unknown"


def run_live(*, root: Path, apply: bool = False, archive_root: Path | None = None) -> MigrationResult:
    """Run the live xmg mapping using existing read-only evidence files."""
    now = __import__("datetime").datetime.now(__import__("datetime").timezone.utc).isoformat()
    result = build_mapping(
        legacy_manifest=Path(os.environ.get(
            "XMG_KB_LEGACY_MANIFEST",
            "/srv/xmg-kb/legacy/.pipeline/existing-kb-manifest.jsonl",
        )),
        xmg_docs=root / "docs",
        xmg_hashes=load_xmg_hashes(root / "data/existing-docs-manifest.sqlite"),
        excluded_manifests=[root / "reports/apply-manifest.jsonl",
                            root / "reports/review-exclusion-manifest.jsonl"],
        junk_manifest=root / "reports/junk-removal.jsonl",
        archive_root=archive_root or Path(os.environ.get(
            "XMG_KB_LEGACY_ARCHIVE", "/srv/xmg-kb/archive/legacy-PENDING"
        )),
    )
    if apply:
        write_outputs(result, xmg_root=root, migration_time=now,
                      migration_commit=_git_commit(root))
    return result


def main(argv: list[str] | None = None) -> int:
    import argparse
    parser = argparse.ArgumentParser(description="Build Legacy to xmg evidence mapping")
    parser.add_argument("--apply", action="store_true", help="publish under xmg state/")
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[3])
    parser.add_argument(
        "--archive-root",
        type=Path,
        default=Path(os.environ.get(
            "XMG_KB_LEGACY_ARCHIVE", "/srv/xmg-kb/archive/legacy-PENDING"
        )),
    )
    args = parser.parse_args(argv)
    result = run_live(root=args.root, apply=args.apply, archive_root=args.archive_root)
    print(json.dumps({"mode": "APPLY" if args.apply else "DRY-RUN",
                      "total": len(result.rows), "counts": result.counts,
                      "unmapped": result.unmapped}, ensure_ascii=False, indent=2))
    return 0 if result.unmapped == 0 else 2


if __name__ == "__main__":
    raise SystemExit(main())
