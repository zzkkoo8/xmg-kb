# ragflow runtime

STATUS: BLOCKED

Component role: required RAG orchestration and retrieval application stack.
Published port: 17115 (reserved loopback only when a future resolved lock allows startup).

Commands:
- configure: `platform/bootstrap.sh --configure ragflow`
- check: `platform/bootstrap.sh --check ragflow`
- install: `platform/bootstrap.sh --install ragflow`
- verify: `platform/bootstrap.sh --verify ragflow`
- status: `platform/bootstrap.sh --status ragflow`

Blocked behavior: the current lock is `BLOCKED`, so `configure` and `check` only write redacted evidence, while `install` and `verify` return `STATUS: BLOCKED` without Docker pull, start, or `up`.

Security boundary: no command may write to `/srv/xmg-kb/evidence` or `/srv/xmg-kb/legacy`; published listeners remain loopback-only; direct `docker compose up` is not allowed from this contract state.

Evidence path: `runtime/ragflow/evidence/result.json`
