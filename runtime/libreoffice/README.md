# libreoffice runtime

STATUS: BLOCKED

Component role: required native document conversion and office-format fallback tooling.
Published port: none (native package path only; no listener may be exposed in the blocked state).

Commands:
- configure: `platform/bootstrap.sh --configure libreoffice`
- check: `platform/bootstrap.sh --check libreoffice`
- install: `platform/bootstrap.sh --install libreoffice`
- verify: `platform/bootstrap.sh --verify libreoffice`
- status: `platform/bootstrap.sh --status libreoffice`

Blocked behavior: the current lock is `BLOCKED`, so `configure` and `check` only write redacted evidence, while `install` and `verify` return `STATUS: BLOCKED` without package install or process start.

Security boundary: no command may write to `/srv/xmg-kb/evidence` or `/srv/xmg-kb/legacy`; no service port may be published; direct package mutation is not allowed from this contract state.

Evidence path: `runtime/libreoffice/evidence/result.json`
