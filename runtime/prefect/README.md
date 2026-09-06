# prefect runtime

STATUS: BLOCKED

Component role: required orchestration and scheduled workflow control plane.
Published port: 17112 (reserved loopback only when a future resolved lock allows startup).

Commands:
- configure: `platform/bootstrap.sh --configure prefect`
- check: `platform/bootstrap.sh --check prefect`
- install: `platform/bootstrap.sh --install prefect`
- verify: `platform/bootstrap.sh --verify prefect`
- status: `platform/bootstrap.sh --status prefect`

Blocked behavior: the current lock is `BLOCKED`, so `configure` and `check` only write redacted evidence, while `install` and `verify` return `STATUS: BLOCKED` without Docker pull, start, or `up`.

Security boundary: no command may write to `/srv/xmg-kb/evidence` or `/srv/xmg-kb/legacy`; published listeners remain loopback-only; direct `docker compose up` is not allowed from this contract state.

Evidence path: `runtime/prefect/evidence/result.json`
