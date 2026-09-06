# kag-poc runtime

STATUS: BLOCKED

Component role: optional KAG proof-of-concept integration for graph-assisted retrieval experiments.
Published port: 17117 (reserved loopback only when a future resolved lock allows startup).

Commands:
- configure: `platform/bootstrap.sh --configure kag-poc`
- check: `platform/bootstrap.sh --check kag-poc`
- install: `platform/bootstrap.sh --install kag-poc`
- verify: `platform/bootstrap.sh --verify kag-poc`
- status: `platform/bootstrap.sh --status kag-poc`

Blocked behavior: the current lock is `BLOCKED`, so `configure` and `check` only write redacted evidence, while `install` and `verify` return `STATUS: BLOCKED` without Docker pull, start, or `up`.

Security boundary: no command may write to `/srv/xmg-kb/evidence` or `/srv/xmg-kb/legacy`; published listeners remain loopback-only; because this component is optional, its blocked state cannot justify bypassing required component gates.

Evidence path: `runtime/kag-poc/evidence/result.json`
