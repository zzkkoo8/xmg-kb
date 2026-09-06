import hashlib
import sqlite3
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parents[1] / "src" / "kb_pipeline"
sys.path.insert(0, str(HERE))

import stage10_parse  # noqa: E402
import stage09_dedup  # noqa: E402
import kbctl  # noqa: E402
from lib import normalized_sha  # noqa: E402


def test_stage10_work_stores_normalized_hash_and_honors_dry_run(tmp_path, monkeypatch):
    raw = tmp_path / "raw"
    parsed = tmp_path / "parsed"
    raw.mkdir()
    source = raw / "sample.pdf"
    source.write_bytes(b"fixture-pdf")
    monkeypatch.setattr(stage10_parse, "RAW", raw)
    monkeypatch.setattr(stage10_parse, "PARSED", parsed)
    monkeypatch.setattr(stage10_parse, "extract", lambda _src: ("A useful extracted document " * 10, "fixture"))

    result = stage10_parse.work("sample.pdf", write_output=False)
    assert result["status"] == "PARSED"
    assert result["norm"] == normalized_sha("A useful extracted document " * 10)
    assert not parsed.exists()

    result = stage10_parse.work("sample.pdf", write_output=True)
    digest = hashlib.sha256(source.read_bytes()).hexdigest()
    output = parsed / digest[:2] / digest / "document.md"
    assert result["text_path"] == str(output)
    assert output.read_text() == "A useful extracted document " * 10


def test_only_failed_selects_retryable_states(tmp_path):
    db = sqlite3.connect(tmp_path / "raw.sqlite")
    db.execute("CREATE TABLE raw_files(source_path TEXT, status TEXT, ext TEXT)")
    rows = [
        ("new.pdf", "NEEDS_PARSE", ".pdf"),
        ("failed.pdf", "PARSE_FAILED", ".pdf"),
        ("empty.pdf", "PARSE_EMPTY", ".pdf"),
        ("garbage.pdf", "PARSE_GARBAGE", ".pdf"),
        ("done.pdf", "PARSED", ".pdf"),
        ("failed.txt", "PARSE_FAILED", ".txt"),
    ]
    db.executemany("INSERT INTO raw_files VALUES(?,?,?)", rows)
    assert stage10_parse.select_todo(db) == ["new.pdf"]
    assert stage10_parse.select_todo(db, only_failed=True) == ["empty.pdf", "failed.pdf", "garbage.pdf"]


def test_dedup_consumes_stage10_parsed_state(tmp_path):
    db = sqlite3.connect(tmp_path / "raw.sqlite")
    db.row_factory = sqlite3.Row
    db.execute("CREATE TABLE raw_files(source_path TEXT, status TEXT, ext TEXT, sha256 TEXT)")
    db.executemany("INSERT INTO raw_files VALUES(?,?,?,?)", [
        ("parsed.pdf", "PARSED", ".pdf", "a" * 64),
        ("candidate.pdf", "CANDIDATE_PARSED", ".pdf", "b" * 64),
        ("pending.pdf", "NEEDS_PARSE", ".pdf", "c" * 64),
        ("done.pdf", "EXISTING_ACCEPTED", ".pdf", "d" * 64),
    ])
    targets = stage09_dedup.select_targets(db)
    assert [r["source_path"] for r in targets] == ["candidate.pdf", "parsed.pdf", "pending.pdf"]


def test_kbctl_parse_uses_dry_run_flag_instead_of_apply(monkeypatch):
    calls = []
    monkeypatch.setattr(kbctl, "sh", lambda script, extra: calls.append((script, extra)) or 0)
    monkeypatch.setattr(sys, "argv", ["kbctl", "--dry-run", "--limit", "2", "parse"])
    assert kbctl.main() == 0
    assert calls == [("stage10_parse.py", ["--workers", "8", "--dry-run", "--limit", "2"])]


def test_kbctl_dry_run_parse_is_read_only(tmp_path, monkeypatch):
    """The real parse entry point must not mutate state through kbctl dry-run."""
    data = tmp_path / "data"
    parsed = tmp_path / "parsed"
    reports = tmp_path / "reports"
    data.mkdir()
    parsed.mkdir()
    reports.mkdir()
    db_path = data / "raw-manifest.sqlite"
    db = sqlite3.connect(db_path)
    db.execute("CREATE TABLE raw_files(source_path TEXT, status TEXT, ext TEXT)")
    db.commit()
    db.close()
    parsed_marker = parsed / "keep.txt"
    reports_marker = reports / "keep.txt"
    parsed_marker.write_text("parsed sentinel")
    reports_marker.write_text("reports sentinel")
    before = {
        "db": db_path.read_bytes(),
        "parsed": parsed_marker.read_bytes(),
        "reports": reports_marker.read_bytes(),
    }

    monkeypatch.setattr(stage10_parse, "DATA", data)
    monkeypatch.setattr(stage10_parse, "PARSED", parsed)
    monkeypatch.setattr(stage10_parse, "REPORTS", reports)

    def run_stage10(script, extra):
        assert script == "stage10_parse.py"
        monkeypatch.setattr(sys, "argv", [script, *extra])
        return stage10_parse.main()

    monkeypatch.setattr(kbctl, "sh", run_stage10)
    monkeypatch.setattr(sys, "argv", ["kbctl", "--dry-run", "--workers", "1", "parse"])

    assert kbctl.main() == 0
    assert db_path.read_bytes() == before["db"]
    assert parsed_marker.read_bytes() == before["parsed"]
    assert reports_marker.read_bytes() == before["reports"]
