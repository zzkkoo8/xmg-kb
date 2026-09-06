# outline runtime

STATUS: BLOCKED

Component role: required team knowledge wiki and canonical document workspace.
Published port: 17111 (reserved loopback only when a future resolved lock allows startup).

Commands:
- configure: `platform/bootstrap.sh --configure outline`
- check: `platform/bootstrap.sh --check outline`
- install: `platform/bootstrap.sh --install outline`
- verify: `platform/bootstrap.sh --verify outline`
- status: `platform/bootstrap.sh --status outline`

Blocked behavior: the current lock is `BLOCKED`, so `configure` and `check` only write redacted evidence, while `install` and `verify` return `STATUS: BLOCKED` without Docker pull, start, or `up`.

Security boundary: no command may write to `/srv/xmg-kb/evidence` or `/srv/xmg-kb/legacy`; published listeners remain loopback-only; direct `docker compose up` is not allowed from this contract state.

Evidence path: `runtime/outline/evidence/result.json`
