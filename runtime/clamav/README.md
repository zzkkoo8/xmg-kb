# clamav runtime

STATUS: BLOCKED

Component role: required malware scanning and attachment hygiene gate.
Published port: none (daemon integration only; no listener may be exposed in the blocked state).

Commands:
- configure: `platform/bootstrap.sh --configure clamav`
- check: `platform/bootstrap.sh --check clamav`
- install: `platform/bootstrap.sh --install clamav`
- verify: `platform/bootstrap.sh --verify clamav`
- status: `platform/bootstrap.sh --status clamav`

Blocked behavior: the current lock is `BLOCKED`, so `configure` and `check` only write redacted evidence, while `install` and `verify` return `STATUS: BLOCKED` without Docker pull, start, or `up`.

Security boundary: no command may write to `/srv/xmg-kb/evidence` or `/srv/xmg-kb/legacy`; published listeners remain loopback-only; signature updates and daemon start remain disabled until the lock is resolved.

Evidence path: `runtime/clamav/evidence/result.json`
