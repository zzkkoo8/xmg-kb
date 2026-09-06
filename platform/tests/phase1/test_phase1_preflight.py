"""Phase 1 preflight stays read-only and validates the rendered Compose contract."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import yaml

from tools import phase1_preflight


def _resolved_lock(path: Path, *, ram: int = 1, disk: int = 1, vm: int | None = 1) -> Path:
    path.write_text(yaml.safe_dump({"components": {"outline": {
        "resolution_status": "RESOLVED", "deployment_mode": "compose",
        "resources": {"min_available_ram_gib": ram, "min_free_disk_gib": disk, "vm_max_map_count": vm},
        "persistent_paths": [{"path": "runtime/outline/data", "owner_uid": os.getuid(), "owner_gid": os.getgid(), "mode": "0700"}],
    }}}))
    return path


def _runtime(tmp_path: Path) -> Path:
    runtime = tmp_path / "runtime"; component = runtime / "outline"
    component.mkdir(parents=True); (component / ".env").write_text("EXAMPLE=value\n")
    data = component / "data"; data.mkdir(); data.chmod(0o700)
    return runtime


def _fake_docker(tmp_path: Path, transcript: Path) -> None:
    fake = tmp_path / "docker"
    fake.write_text("#!/usr/bin/env python3\nimport os,sys\nfrom pathlib import Path\nPath(os.environ['XMG_DOCKER_TRANSCRIPT']).write_text(' '.join(sys.argv[1:]))\nif sys.argv[-3:] == ['config','--format','json']: print(os.environ['XMG_COMPOSE_JSON'])\n")
    fake.chmod(0o755)


def test_preflight_import():
    assert "outline" in phase1_preflight.IDS


def test_resolved_preflight_enforces_thresholds_and_safe_compose_argv(tmp_path, monkeypatch):
    runtime = _runtime(tmp_path); lock = _resolved_lock(tmp_path / "lock.yaml")
    source = tmp_path / "source"; source.mkdir(); (source / "one.md").write_text("fixture")
    transcript = tmp_path / "docker.argv"
    config = {"services": {
        "outline": {"image": "registry.example/outline@sha256:" + "a" * 64, "ports": [{"host_ip": "127.0.0.1", "published": "3000"}]},
        "postgres": {"image": "postgres@sha256:" + "b" * 64},
    }}
    _fake_docker(tmp_path, transcript)
    monkeypatch.setenv("PATH", f"{tmp_path}:{os.environ['PATH']}")
    monkeypatch.setenv("XMG_DOCKER_TRANSCRIPT", str(transcript)); monkeypatch.setenv("XMG_COMPOSE_JSON", json.dumps(config))
    monkeypatch.setattr(phase1_preflight, "registry_reachable", lambda _url: (True, "fixture"))
    status, payload = phase1_preflight.preflight("outline", lock, runtime, source_roots=[source], registry_url="https://registry.example/v2/")
    assert status == "PASS"
    assert payload["checks"]["ram_threshold"] and payload["checks"]["disk_threshold"]
    assert payload["checks"]["compose_digest_only"] and payload["checks"]["compose_loopback"]
    assert payload["checks"]["compose_dependencies_unpublished"]
    assert "compose --project-name xmg-kb-outline --env-file" in transcript.read_text()
    assert payload["observations"]["source_roots"][str(source)]["file_count"] == 1
    assert payload["observations"]["source_roots"][str(source)]["uid"] == os.getuid()


def test_preflight_blocks_unsafe_dependency_port_and_unpinned_image(tmp_path, monkeypatch):
    runtime = _runtime(tmp_path); lock = _resolved_lock(tmp_path / "lock.yaml")
    source = tmp_path / "source"; source.mkdir(); transcript = tmp_path / "docker.argv"
    config = {"services": {
        "outline": {"image": "outline:latest", "ports": [{"host_ip": "0.0.0.0", "published": 3000}]},
        "postgres": {"image": "postgres@sha256:" + "b" * 64, "ports": [{"host_ip": "127.0.0.1", "published": 5432}]},
    }}
    _fake_docker(tmp_path, transcript)
    monkeypatch.setenv("PATH", f"{tmp_path}:{os.environ['PATH']}")
    monkeypatch.setenv("XMG_DOCKER_TRANSCRIPT", str(transcript)); monkeypatch.setenv("XMG_COMPOSE_JSON", json.dumps(config))
    monkeypatch.setattr(phase1_preflight, "registry_reachable", lambda _url: (True, "fixture"))
    status, payload = phase1_preflight.preflight("outline", lock, runtime, source_roots=[source])
    assert status == "BLOCKED"
    assert not payload["checks"]["compose_digest_only"]
    assert not payload["checks"]["compose_loopback"]
    assert not payload["checks"]["compose_dependencies_unpublished"]


def test_preflight_blocks_when_resource_threshold_is_not_met(tmp_path, monkeypatch):
    runtime = _runtime(tmp_path); lock = _resolved_lock(tmp_path / "lock.yaml", ram=10**9, disk=10**9, vm=10**9)
    source = tmp_path / "source"; source.mkdir()
    monkeypatch.setattr(phase1_preflight, "registry_reachable", lambda _url: (True, "fixture"))
    status, payload = phase1_preflight.preflight("outline", lock, runtime, source_roots=[source])
    assert status == "BLOCKED"
    assert not payload["checks"]["ram_threshold"] and not payload["checks"]["disk_threshold"]
    assert not payload["checks"]["vm_max_map_count"]


def test_preflight_rejects_published_port_without_explicit_loopback_host(tmp_path, monkeypatch):
    runtime = _runtime(tmp_path); lock = _resolved_lock(tmp_path / "lock.yaml")
    source = tmp_path / "source"; source.mkdir(); transcript = tmp_path / "docker.argv"
    config = {"services": {"outline": {
        "image": "outline@sha256:" + "a" * 64, "ports": [{"published": 3000}],
    }}}
    _fake_docker(tmp_path, transcript)
    monkeypatch.setenv("PATH", f"{tmp_path}:{os.environ['PATH']}")
    monkeypatch.setenv("XMG_DOCKER_TRANSCRIPT", str(transcript)); monkeypatch.setenv("XMG_COMPOSE_JSON", json.dumps(config))
    monkeypatch.setattr(phase1_preflight, "registry_reachable", lambda _url: (True, "fixture"))
    status, payload = phase1_preflight.preflight("outline", lock, runtime, source_roots=[source])
    assert status == "BLOCKED"
    assert not payload["checks"]["compose_loopback"]


def test_generated_fixtures_have_required_pdf_shapes_and_markers(tmp_path):
    script = Path(__file__).resolve().parents[2] / "tools/generate_phase1_fixtures.py"
    result = subprocess.run([sys.executable, str(script), "--output", str(tmp_path)], text=True, capture_output=True)
    assert result.returncode == 0, result.stderr
    complex_pdf, scan_pdf = (tmp_path / "complex.pdf").read_bytes(), (tmp_path / "scan.pdf").read_bytes()
    assert complex_pdf.startswith(b"%PDF-") and complex_pdf.count(b"/Type /Page") >= 2
    assert b"XMG_PHASE1_COMPLEX_20260831" in complex_pdf
    assert scan_pdf.startswith(b"%PDF-") and b"XMG_PHASE1_SCAN_20260831" in scan_pdf
    assert (tmp_path / "corrupt.pdf").read_bytes() == b"%PDF-corrupt"
    assert {"complex.pdf", "scan.pdf", "corrupt.pdf", "rag-sample.md"} <= set(json.loads((tmp_path / "manifest.json").read_text()))
