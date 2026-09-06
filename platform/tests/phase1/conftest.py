"""Shared Phase 1 test configuration."""

import sys
from pathlib import Path
import re
import yaml


PLATFORM = Path(__file__).resolve().parents[2]

if str(PLATFORM) not in sys.path:
    sys.path.insert(0, str(PLATFORM))

ROOT = PLATFORM.parent

def compose_command(component: str, verb: str) -> list[str]:
    allowed = {"outline", "prefect", "docling-serve", "ragflow", "langfuse", "clamav", "kag-poc"}
    assert component in allowed and verb in {"up", "stop", "restart"}
    root = ROOT / "runtime" / component
    return ["docker", "compose", "--project-name", f"xmg-kb-{component}", "--env-file", str(root / ".env"), "-f", str(root / "compose.upstream.yaml"), "-f", str(root / "compose.xmg.yaml"), verb] + (["-d"] if verb == "up" else [])

def assert_component_contract(component: str, port: int | None, checks: set[str]) -> None:
    lock = yaml.safe_load((ROOT / "platform/config/components.lock.yaml").read_text())["components"][component]
    assert lock["resolution_status"] == "RESOLVED"
    runtime = ROOT / "runtime" / component
    for name in ("README.md", ".env.example", "smoke-test.sh", "backup-notes.md"):
        assert (runtime / name).is_file()
    entries = dict(line.split("=",1) for line in runtime.joinpath(".env.example").read_text().splitlines() if line and not line.startswith("#"))
    assert {k for k,v in entries.items() if v == "__GENERATE__"} == set(lock.get("configuration",{}).get("secret_keys",[]))
    smoke = runtime.joinpath("smoke-test.sh").read_text()
    assert checks <= set(re.findall(r"CHECK:([a-z_]+)", smoke))
    assert "/srv/xmg-kb/evidence" not in smoke and "/srv/xmg-kb/legacy" not in smoke
