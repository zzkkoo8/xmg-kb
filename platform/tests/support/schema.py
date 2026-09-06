"""JSON Schema validation helpers for platform contract tests."""

from datetime import datetime
from pathlib import Path
import re

from jsonschema import Draft202012Validator, FormatChecker

from tests.support.io import load_json


SCHEMA_DIRECTORY = Path(__file__).resolve().parents[2] / "schemas"
FORMAT_CHECKER = FormatChecker()
RFC3339_RE = re.compile(
    r"^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}"
    r"(?:\.[0-9]+)?(?:Z|[+-][0-9]{2}:[0-9]{2})$"
)


@FORMAT_CHECKER.checks("date-time", raises=(TypeError, ValueError))
def is_rfc3339_datetime(value: object) -> bool:
    """Validate the timezone-bearing RFC3339 subset used by lock evidence."""
    if not isinstance(value, str) or RFC3339_RE.fullmatch(value) is None:
        return False
    normalized = value[:-1] + "+00:00" if value.endswith("Z") else value
    parsed = datetime.fromisoformat(normalized)
    return parsed.tzinfo is not None


def validate(instance: dict, schema_name: str) -> None:
    """Validate an object against a named schema in ``platform/schemas``."""
    schema = load_json(SCHEMA_DIRECTORY / f"{schema_name}.schema.json")
    validator = Draft202012Validator(schema, format_checker=FORMAT_CHECKER)
    validator.validate(instance)
