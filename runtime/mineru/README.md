# mineru runtime

STATUS: BLOCKED

Component role: required OCR and PDF extraction fallback worker.
Published port: none (container-cli path only; no listener may be exposed in the blocked state).

Commands:
- configure: `platform/bootstrap.sh --configure mineru`
- check: `platform/bootstrap.sh --check mineru`
- install: `platform/bootstrap.sh --install mineru`
- verify: `platform/bootstrap.sh --verify mineru`
- status: `platform/bootstrap.sh --status mineru`

Blocked behavior: the current lock is `BLOCKED`, so `configure` and `check` only write redacted evidence, while `install` and `verify` return `STATUS: BLOCKED` without Docker pull, start, or `up`.

Security boundary: no command may write to `/srv/xmg-kb/evidence` or `/srv/xmg-kb/legacy`; no service port may be published; direct runtime execution is not allowed from this contract state.

Evidence path: `runtime/mineru/evidence/result.json`
