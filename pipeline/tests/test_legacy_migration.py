import json
from pathlib import Path

import pytest

from kb_pipeline.legacy_migration import (
    ALLOWED_FINAL_STATES,
    build_mapping,
    validate_mapping,
    write_outputs,
)


def _write_jsonl(path: Path, rows: list[dict]) -> Path:
    path.write_text("".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows), encoding="utf-8")
    return path


def _legacy_row(path: str, sha: str, normalized: str = "n") -> dict:
    return {
        "path": f"docs/{path}",
        "file_sha256": sha,
        "normalized_text_sha256": normalized,
        "title": Path(path).stem,
        "product": "Product",
        "version": "1.0",
        "source_path": path,
        "content_length": 12,
    }


def test_build_mapping_classifies_reused_transformed_archive_and_rejected(tmp_path: Path):
    legacy = _write_jsonl(
        tmp_path / "legacy.jsonl",
        [
            _legacy_row("reuse.md", "a" * 64),
            _legacy_row("transform.md", "b" * 64),
            _legacy_row("excluded.md", "c" * 64),
            _legacy_row("junk.md", "d" * 64),
        ],
    )
    xmg_docs = tmp_path / "xmg" / "docs"
    xmg_docs.mkdir(parents=True)
    (xmg_docs / "reuse.md").write_text("same", encoding="utf-8")
    (xmg_docs / "transform.md").write_text("changed", encoding="utf-8")
    excluded = _write_jsonl(tmp_path / "review-exclusion-manifest.jsonl", [{"original_path": "excluded.md"}])
    junk = _write_jsonl(tmp_path / "junk-removal.jsonl", [{"original": "junk.md", "reason": "error_page"}])

    # The fixture uses manifest hashes as the source of truth; target hashes are
    # supplied explicitly so this test does not depend on a production hash pass.
    result = build_mapping(
        legacy_manifest=legacy,
        xmg_docs=xmg_docs,
        xmg_hashes={"reuse.md": "a" * 64, "transform.md": "e" * 64},
        excluded_manifests=[excluded],
        junk_manifest=junk,
        archive_root=tmp_path / "archive",
    )

    assert [row["final_state"] for row in result.rows] == [
        "MIGRATED_REUSED",
        "MIGRATED_TRANSFORMED",
        "ARCHIVE_ONLY",
        "REJECTED_INVALID",
    ]
    assert result.unmapped == 0
    assert all(row["final_state"] in ALLOWED_FINAL_STATES for row in result.rows)
    assert result.rows[2]["archive_target"].endswith("excluded.md")
    assert result.rows[3]["reason"] == "error_page"


def test_build_mapping_fails_closed_on_conflicting_governance(tmp_path: Path):
    legacy = _write_jsonl(tmp_path / "legacy.jsonl", [_legacy_row("conflict.md", "a" * 64)])
    xmg_docs = tmp_path / "xmg" / "docs"
    xmg_docs.mkdir(parents=True)
    first = _write_jsonl(tmp_path / "review-exclusion-one.jsonl", [{"original_path": "conflict.md"}])
    second = _write_jsonl(tmp_path / "junk-removal.jsonl", [{"original": "conflict.md", "reason": "invalid"}])
    with pytest.raises(ValueError, match="conflicting governance"):
        build_mapping(
            legacy_manifest=legacy,
            xmg_docs=xmg_docs,
            xmg_hashes={},
            excluded_manifests=[first, second],
            junk_manifest=None,
            archive_root=tmp_path / "archive",
        )


def test_build_mapping_reports_unmapped_when_no_evidence(tmp_path: Path):
    legacy = _write_jsonl(tmp_path / "legacy.jsonl", [_legacy_row("missing.md", "a" * 64)])
    xmg_docs = tmp_path / "xmg" / "docs"
    xmg_docs.mkdir(parents=True)
    result = build_mapping(
        legacy_manifest=legacy,
        xmg_docs=xmg_docs,
        xmg_hashes={},
        excluded_manifests=[],
        junk_manifest=None,
        archive_root=tmp_path / "archive",
    )
    assert result.unmapped == 1
    assert result.rows[0]["final_state"] == "UNMAPPED"


@pytest.mark.parametrize("bad_path", ["/absolute.md", "../escape.md", "docs/../escape.md"])
def test_build_mapping_rejects_unsafe_source_path(tmp_path: Path, bad_path: str):
    legacy = _write_jsonl(tmp_path / "legacy.jsonl", [_legacy_row(bad_path, "a" * 64)])
    with pytest.raises(ValueError, match="unsafe|absolute"):
        build_mapping(
            legacy_manifest=legacy,
            xmg_docs=tmp_path / "docs",
            xmg_hashes={},
            excluded_manifests=[],
            junk_manifest=None,
            archive_root=tmp_path / "archive",
        )


def test_build_mapping_marks_existing_target_without_manifest_hash_for_repair(tmp_path: Path):
    legacy = _write_jsonl(tmp_path / "legacy.jsonl", [_legacy_row("target.md", "a" * 64)])
    xmg_docs = tmp_path / "docs"
    xmg_docs.mkdir()
    (xmg_docs / "target.md").write_text("target", encoding="utf-8")
    result = build_mapping(
        legacy_manifest=legacy,
        xmg_docs=xmg_docs,
        xmg_hashes={},
        excluded_manifests=[],
        junk_manifest=None,
        archive_root=tmp_path / "archive",
    )
    assert result.rows[0]["final_state"] == "NEEDS_REPAIR"
    assert "hash" in result.rows[0]["reason"]


def test_build_mapping_rejects_duplicate_legacy_paths(tmp_path: Path):
    row = _legacy_row("same.md", "a" * 64)
    legacy = _write_jsonl(tmp_path / "legacy.jsonl", [row, row])
    with pytest.raises(ValueError, match="duplicate Legacy path"):
        build_mapping(
            legacy_manifest=legacy,
            xmg_docs=tmp_path / "docs",
            xmg_hashes={},
            excluded_manifests=[],
            junk_manifest=None,
            archive_root=tmp_path / "archive",
        )


def test_write_outputs_publishes_only_under_xmg_state(tmp_path: Path):
    legacy = _write_jsonl(tmp_path / "legacy.jsonl", [_legacy_row("reuse.md", "a" * 64)])
    docs = tmp_path / "docs"
    docs.mkdir()
    (docs / "reuse.md").write_text("same", encoding="utf-8")
    result = build_mapping(
        legacy_manifest=legacy,
        xmg_docs=docs,
        xmg_hashes={"reuse.md": "a" * 64},
        excluded_manifests=[],
        junk_manifest=None,
        archive_root=tmp_path / "archive",
    )
    write_outputs(result, xmg_root=tmp_path, migration_time="2026-09-02T00:00:00+00:00", migration_commit="abc")
    assert (tmp_path / "state/mappings/legacy-to-xmg.jsonl").exists()
    assert (tmp_path / "state/manifests/legacy-chaitin-kb/legacy-knowledge-manifest.jsonl").exists()
    assert not (tmp_path / "archive").exists()
    mapping = json.loads((tmp_path / "state/mappings/legacy-to-xmg.jsonl").read_text(encoding="utf-8"))
    assert mapping["target_sha256"] == "a" * 64


def test_build_mapping_ignores_non_docs_legacy_assets(tmp_path: Path):
    legacy = _write_jsonl(tmp_path / "legacy.jsonl", [
        {"path": "README.md", "file_sha256": "a" * 64},
        _legacy_row("knowledge.md", "b" * 64),
    ])
    result = build_mapping(
        legacy_manifest=legacy,
        xmg_docs=tmp_path / "docs",
        xmg_hashes={},
        excluded_manifests=[],
        junk_manifest=None,
        archive_root=tmp_path / "archive",
    )
    assert [row["legacy_path"] for row in result.rows] == ["knowledge.md"]


def test_validate_mapping_requires_targets_reasons_and_zero_unmapped(tmp_path: Path):
    docs = tmp_path / "docs"
    docs.mkdir()
    (docs / "ok.md").write_text("ok", encoding="utf-8")
    rows = [
        {"legacy_path": "ok.md", "legacy_sha256": "a" * 64,
         "final_state": "MIGRATED_TRANSFORMED", "target": "docs/ok.md",
         "target_sha256": "b" * 64},
        {"legacy_path": "old.md", "legacy_sha256": "c" * 64,
         "final_state": "ARCHIVE_ONLY", "archive_target": "/srv/xmg-kb/archive/x/old.md"},
        {"legacy_path": "bad.md", "legacy_sha256": "d" * 64,
         "final_state": "REJECTED_INVALID", "reason": "error_page"},
    ]
    result = validate_mapping(rows, xmg_root=tmp_path, expected_total=3)
    assert result["gate"] == "PASS"
    assert result["unmapped"] == 0


def test_validate_mapping_blocks_missing_target_and_unmapped(tmp_path: Path):
    rows = [{"legacy_path": "missing.md", "legacy_sha256": "a" * 64,
             "final_state": "UNMAPPED"}]
    result = validate_mapping(rows, xmg_root=tmp_path, expected_total=1)
    assert result["gate"] == "BLOCKED"
    assert result["unmapped"] == 1
    assert result["blockers"]
