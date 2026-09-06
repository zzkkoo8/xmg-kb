#!/usr/bin/env python3
"""Safely materialize a component environment from its allow-listed example."""
from __future__ import annotations
import argparse, json, os, re, secrets, stat, tempfile, sys
from pathlib import Path
import yaml

COMPONENTS = {"outline","prefect","docling-serve","mineru","ragflow","langfuse","libreoffice","clamav","kag-poc"}
KEY_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
INTERP_RE = re.compile(r"\$\(|\$\{|`|;|&&|\|\|")
DEFAULT_SECRET_RE = re.compile(r"^(?:changeme|change[_-]?me|password|secret|token|example|default|__generate__)?$", re.I)

def load_lock(path: Path) -> dict:
    with path.open() as f: return yaml.safe_load(f)

def parse_example(path: Path) -> list[tuple[str,str]]:
    rows=[]
    for n,line in enumerate(path.read_text().splitlines(),1):
        line=line.strip()
        if not line or line.startswith('#'): continue
        if '=' not in line: raise ValueError(f"invalid env example line {n}")
        k,v=line.split('=',1)
        if not KEY_RE.fullmatch(k): raise ValueError(f"invalid key {k}")
        if INTERP_RE.search(v): raise ValueError("shell interpolation rejected")
        rows.append((k,v))
    if len({k for k,_ in rows}) != len(rows): raise ValueError("duplicate env key")
    return rows

def validate_env(rows:list[tuple[str,str]], secret_keys:set[str], expected_keys:set[str]|None=None):
    keys={k for k,_ in rows}
    if expected_keys is not None and keys != expected_keys: raise ValueError('environment key allowlist mismatch')
    if {k for k,v in rows if v == '__GENERATE__'} != secret_keys: raise ValueError('secret allowlist mismatch')
    for k,v in rows:
        if k in secret_keys and DEFAULT_SECRET_RE.fullmatch(v.strip()): raise ValueError('default or empty secret')

def result(runtime: Path, component: str, status: str, blocker: str|None=None):
    ev=runtime/'evidence'; ev.mkdir(parents=True, exist_ok=True)
    payload={"component":component,"status":status,"blocker":blocker or "","captured_at":"2026-09-01T00:00:00Z","capabilities":{"bootstrap":{"status":status,"reason":blocker or status}}}
    fd,tmp=tempfile.mkstemp(dir=ev,prefix='.result.',text=True)
    with os.fdopen(fd,'w') as f: json.dump(payload,f,indent=2); f.write('\n'); f.flush(); os.fsync(f.fileno())
    os.replace(tmp,ev/'result.json')

def configure(lock_path: Path, component: str, runtime_root: Path) -> int:
    if component not in COMPONENTS: return 2
    lock=load_lock(lock_path); info=lock.get('components',{}).get(component)
    if not info: return 2
    runtime=(runtime_root/component).resolve()
    root=runtime_root.resolve()
    if root not in runtime.parents: return 2
    if info.get('resolution_status') != 'RESOLVED':
        result(runtime,component,'BLOCKED',info.get('blocker','component lock is BLOCKED'))
        print('STATUS: BLOCKED'); return 10
    example=runtime/'.env.example'
    if not example.is_file(): print('STATUS: CONFIGURATION_FAILED', file=__import__('sys').stderr); return 21
    try: rows=parse_example(example)
    except Exception as e: print('STATUS: CONFIGURATION_FAILED', file=__import__('sys').stderr); return 21
    secret_keys=set(info.get('configuration',{}).get('secret_keys',[]))
    generated={k for k,v in rows if v=='__GENERATE__'}
    if generated != secret_keys: print('STATUS: CONFIGURATION_FAILED', file=sys.stderr); return 21
    env=runtime/'.env'
    if env.exists():
        if stat.S_IMODE(env.stat().st_mode)!=0o600: return 21
        try: existing_rows=parse_example(env); existing=dict(existing_rows)
        except Exception: return 21
        try: validate_env(existing_rows,secret_keys,{k for k,_ in rows})
        except Exception: return 21
        print('STATUS: PASS'); return 0
    runtime.mkdir(parents=True,exist_ok=True)
    old=os.umask(0o077)
    try:
        fd,tmp=tempfile.mkstemp(dir=runtime,prefix='.env.',text=True)
        with os.fdopen(fd,'w') as f:
            for k,v in rows: f.write(f"{k}={secrets.token_hex(32) if k in secret_keys else v}\n")
            f.flush(); os.fsync(f.fileno())
        os.chmod(tmp,0o600); os.replace(tmp,env)
    finally: os.umask(old)
    print('STATUS: PASS'); return 0

def main():
    p=argparse.ArgumentParser(); p.add_argument('--lock',required=True); p.add_argument('--component',required=True); p.add_argument('--runtime-root',required=True)
    try: raise SystemExit(configure(Path(p.parse_args().lock),p.parse_args().component,Path(p.parse_args().runtime_root)))
    except SystemExit: raise
    except Exception: print('STATUS: CONFIGURATION_FAILED',file=__import__('sys').stderr); raise SystemExit(21)
if __name__=='__main__': main()
