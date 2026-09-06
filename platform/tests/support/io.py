"""Small, explicit loaders used by platform contract tests."""

import json
from pathlib import Path

import yaml


def load_yaml(path: Path) -> dict:
    """Load a YAML mapping from *path*."""
    payload = yaml.safe_load(path.read_text())
    if not isinstance(payload, dict):
        raise ValueError(f"expected YAML object in {path}")
    return payload


def load_json(path: Path) -> dict:
    """Load a JSON object from *path*."""
    payload = json.loads(path.read_text())
    if not isinstance(payload, dict):
        raise ValueError(f"expected JSON object in {path}")
    return payload
