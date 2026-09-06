# docling-serve runtime

STATUS: BLOCKED

Component role: required HTTP document parsing service for structured extraction.
Published port: 17113 (reserved loopback only when a future resolved lock allows startup).

Commands:
- configure: `platform/bootstrap.sh --configure docling-serve`
- check: `platform/bootstrap.sh --check docling-serve`
- install: `platform/bootstrap.sh --install docling-serve`
- verify: `platform/bootstrap.sh --verify docling-serve`
- status: `platform/bootstrap.sh --status docling-serve`

Blocked behavior: the current lock is `BLOCKED`, so `configure` and `check` only write redacted evidence, while `install` and `verify` return `STATUS: BLOCKED` without Docker pull, start, or `up`.

Security boundary: no command may write to `/srv/xmg-kb/evidence` or `/srv/xmg-kb/legacy`; published listeners remain loopback-only; direct `docker compose up` is not allowed from this contract state.

Evidence path: `runtime/docling-serve/evidence/result.json`
