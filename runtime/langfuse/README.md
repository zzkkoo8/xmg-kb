# langfuse runtime

STATUS: BLOCKED

Component role: required tracing, telemetry, and evaluation workspace for LLM pipelines.
Published port: 17116 (reserved loopback only when a future resolved lock allows startup).

Commands:
- configure: `platform/bootstrap.sh --configure langfuse`
- check: `platform/bootstrap.sh --check langfuse`
- install: `platform/bootstrap.sh --install langfuse`
- verify: `platform/bootstrap.sh --verify langfuse`
- status: `platform/bootstrap.sh --status langfuse`

Blocked behavior: the current lock is `BLOCKED`, so `configure` and `check` only write redacted evidence, while `install` and `verify` return `STATUS: BLOCKED` without Docker pull, start, or `up`.

Security boundary: no command may write to `/srv/xmg-kb/evidence` or `/srv/xmg-kb/legacy`; published listeners remain loopback-only; memory-admission and registry evidence must be resolved before any startup.

Evidence path: `runtime/langfuse/evidence/result.json`
