#!/usr/bin/env bash
set -u
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
LOCK="$ROOT/platform/config/components.lock.yaml"
RUNTIME="$ROOT/runtime"
IDS='outline prefect docling-serve mineru ragflow langfuse libreoffice clamav kag-poc'
valid(){ case " $IDS " in *" $1 "*) return 0;; esac; return 1; }
bad(){ echo 'invalid arguments' >&2; exit 2; }
lock_status(){ python3 - "$LOCK" "$1" <<'PY'
import sys, yaml
doc = yaml.safe_load(open(sys.argv[1])) or {}
row = (doc.get("components") or {}).get(sys.argv[2]) or {}
print(row.get("resolution_status", "BLOCKED"))
PY
}
[ "$#" -eq 2 ] || bad
ACTION=$1; ID=$2; valid "$ID" || bad
case "$ACTION" in --configure|--check|--install|--verify|--status) ;; *) bad ;; esac
echo "BOOTSTRAP_ACTION: ${ACTION#--}"; echo "COMPONENT: $ID"
case "$ACTION" in
 --configure) python3 "$ROOT/platform/tools/configure_component.py" --lock "$LOCK" --component "$ID" --runtime-root "$RUNTIME"; rc=$?; emit=0 ;;
 --check) python3 "$ROOT/platform/tools/phase1_preflight.py" --lock "$LOCK" --component "$ID" --runtime-root "$RUNTIME" --output "$RUNTIME/$ID/evidence/result.json"; rc=$?; emit=0 ;;
 --install)
   status=$(lock_status "$ID")
   if [ "$status" != RESOLVED ]; then echo 'STATUS: BLOCKED'; exit 20; fi
   # Validate the immutable deployment provenance before any pull.  This is a
   # read-only check; a mismatch fails closed and never invokes Docker pull.
   if ! python3 - "$LOCK" "$RUNTIME" "$ID" <<'PY'
import hashlib, json, pathlib, subprocess, sys, yaml
lock = (yaml.safe_load(pathlib.Path(sys.argv[1]).read_text()) or {}).get("components", {}).get(sys.argv[3], {})
root = pathlib.Path(sys.argv[2]) / sys.argv[3]
dep = lock.get("deployment") or {}
rel = dep.get("path")
expected = dep.get("upstream_sha256")
if not isinstance(rel, str) or not rel.startswith(f"runtime/{sys.argv[3]}/"):
    raise SystemExit(1)
if not isinstance(expected, str) or len(expected) != 64 or any(c not in "0123456789abcdef" for c in expected.lower()):
    raise SystemExit(1)
path = pathlib.Path(sys.argv[2]).parent / rel
try: path.relative_to(root)
except ValueError: raise SystemExit(1)
if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != expected:
    raise SystemExit(1)
if lock.get("deployment_mode") == "compose":
    argv = ["docker", "compose", "--project-name", f"xmg-kb-{sys.argv[3]}",
            "--env-file", str(root/".env"), "-f", str(root/"compose.upstream.yaml"),
            "-f", str(root/"compose.xmg.yaml"), "config", "--format", "json"]
    try: rendered = subprocess.run(argv, check=True, capture_output=True, text=True, timeout=30)
    except Exception: raise SystemExit(1)
    try: services = (json.loads(rendered.stdout) or {}).get("services", {})
    except Exception: raise SystemExit(1)
    actual = {svc.get("image") for svc in services.values() if svc.get("image")}
    expected = {a.get("name") + "@" + a.get("digest_or_checksum") for a in lock.get("artifacts", [])
                if a.get("kind") == "image" and a.get("name") and str(a.get("digest_or_checksum", "")).startswith("sha256:")}
    if not actual or actual != expected: raise SystemExit(1)
PY
   then echo 'STATUS: BLOCKED'; exit 20; fi
   images=$(python3 - "$LOCK" "$ID" <<'PY'
import sys, yaml
row=(yaml.safe_load(open(sys.argv[1])) or {}).get("components",{}).get(sys.argv[2],{})
for a in row.get("artifacts",[]):
    if a.get("kind") == "image" and a.get("name") and a.get("digest_or_checksum", "").startswith("sha256:"):
        print(a["name"] + "@" + a["digest_or_checksum"])
PY
)
   # Native package components have no image pull; resolved artifact closure is
   # checked by the lock resolver and install remains side-effect free here.
   if [ -z "$images" ]; then
     [ "$ID" = libreoffice ] || { echo 'STATUS: BLOCKED'; exit 20; }
   fi
   rc=0
   if [ -n "$images" ]; then
    while IFS= read -r image; do
      [ -n "$image" ] || continue
      docker pull "$image" >/dev/null || { rc=20; break; }
    done <<EOF
$images
EOF
   fi
   ;;
 --verify)
   status=$(lock_status "$ID")
   [ "$status" = RESOLVED ] || { echo 'STATUS: BLOCKED'; exit 30; }
   test -x "$RUNTIME/$ID/smoke-test.sh" || { echo 'STATUS: FAIL'; exit 30; }
   "$RUNTIME/$ID/smoke-test.sh"; rc=$?; ;;
 --status)
   status=$(lock_status "$ID")
   if [ "$status" != RESOLVED ]; then echo 'STATUS: UNAVAILABLE'; exit 40; fi
   if [ -f "$RUNTIME/$ID/compose.xmg.yaml" ]; then
     docker compose --project-name "xmg-kb-$ID" --env-file "$RUNTIME/$ID/.env" -f "$RUNTIME/$ID/compose.upstream.yaml" -f "$RUNTIME/$ID/compose.xmg.yaml" ps --status running --services >/dev/null 2>&1 || { echo 'STATUS: UNAVAILABLE'; exit 40; }
   elif [ "$ID" = libreoffice ]; then command -v soffice >/dev/null 2>&1 || { echo 'STATUS: UNAVAILABLE'; exit 40; }
   else docker ps --format '{{.Names}}' | grep -q "xmg-kb-$ID" || { echo 'STATUS: UNAVAILABLE'; exit 40; }
   fi
   echo 'STATUS: PASS'; rc=0 ;;
 *) bad;;
esac
[ "${emit:-1}" -eq 0 ] || echo "STATUS: $([ "$rc" -eq 0 ] && echo PASS || echo BLOCKED)"
exit "$rc"
