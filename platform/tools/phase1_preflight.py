#!/usr/bin/env python3
"""Read-only host/component preflight checks for Phase 1 bootstrap."""
from __future__ import annotations
import argparse, json, os, shutil, socket, subprocess, tempfile, urllib.request
from pathlib import Path
import yaml
ROOT=Path(__file__).resolve().parents[2]
IDS={"outline","prefect","docling-serve","mineru","ragflow","langfuse","libreoffice","clamav","kag-poc"}

def run(cmd:list[str], timeout=8):
    try:
        p=subprocess.run(cmd,text=True,capture_output=True,timeout=timeout)
        return p.returncode,p.stdout,p.stderr
    except Exception as e: return 127,"",str(e)

def registry_reachable(url: str = "https://registry-1.docker.io/v2/") -> bool:
    """Bounded HTTPS reachability probe; kept as a seam for offline tests."""
    try:
        req=urllib.request.Request(url, method='HEAD', headers={'User-Agent':'xmg-kb-preflight/1'})
        with urllib.request.urlopen(req, timeout=5) as response:
            return response.status in (200,401,403)
    except Exception:
        return False

def preflight(component:str, lock_path:Path, runtime_root:Path, source_roots=None, registry_url="https://registry-1.docker.io/v2/")->tuple[str,dict]:
    lock=yaml.safe_load(lock_path.read_text()); info=lock.get('components',{}).get(component)
    if not info: return 'FAIL', {'component':component,'status':'FAIL','blocker':'unknown component'}
    if info.get('resolution_status')!='RESOLVED':
        reason=info.get('blocker','lock BLOCKED')
        return 'BLOCKED', {'component':component,'status':'BLOCKED','blocker':reason,'capabilities':{'preflight':{'status':'BLOCKED','reason':reason}}}
    checks={}
    # Collect host observations with bounded, read-only probes. Failures are
    # represented as false checks rather than raising or mutating the host.
    probes = {
        'disk': ['df','-Pk'],
        'vmstat': ['vmstat','1','5'],
        'sockets': ['ss','-H','-lntup'],
        'sysctl': ['sysctl','vm.max_map_count'],
    }
    outputs={name:run(cmd, timeout=12) for name,cmd in probes.items()}
    for name,(rc,_,_) in outputs.items(): checks[name] = rc == 0
    resources=info.get('resources') or {}
    try:
      mem_kib=next(int(line.split()[1]) for line in Path('/proc/meminfo').read_text().splitlines() if line.startswith('MemAvailable:'))
    except Exception: mem_kib=0
    checks['ram_threshold'] = mem_kib >= float(resources.get('min_available_ram_gib',0))*1024*1024
    try:
      df_lines=outputs['disk'][1].splitlines(); avail_kib=int(df_lines[-1].split()[3]) if len(df_lines)>1 else 0
    except Exception: avail_kib=0
    checks['disk_threshold'] = avail_kib >= float(resources.get('min_free_disk_gib',0))*1024*1024
    try:
      vm=int(Path('/proc/sys/vm/max_map_count').read_text().strip()); req=resources.get('vm_max_map_count')
      checks['vm_max_map_count'] = req is None or vm >= int(req)
    except Exception: checks['vm_max_map_count']=resources.get('vm_max_map_count') is None
    for path in ('/proc/meminfo','/proc/sys/vm/max_map_count'):
        checks[path] = Path(path).is_file()
    checks['docker']=shutil.which('docker') is not None
    checks['ca_readable']=Path('/etc/ssl/certs/ca-certificates.crt').is_file() or Path('/etc/ssl/cert.pem').is_file()
    reg=registry_reachable(registry_url)
    checks['registry_reachable']=reg[0] if isinstance(reg,tuple) else bool(reg)
    root=(runtime_root/component).resolve(); checks['runtime']=root.is_dir()
    roots=[Path(x) for x in (source_roots or [
        os.environ.get('XMG_KB_RAW_EVIDENCE', '/srv/xmg-kb/evidence'),
        os.environ.get('XMG_KB_LEGACY_ROOT', '/srv/xmg-kb/legacy'),
    ])]
    source_obs={}
    for src in roots:
      try:
        source_stat=src.stat()
        source_obs[str(src)]={'exists':src.is_dir(),'file_count':sum(1 for p in src.rglob('*') if p.is_file()),'uid':source_stat.st_uid,'gid':source_stat.st_gid,'mode':oct(source_stat.st_mode & 0o777)}
      except OSError: source_obs[str(src)]={'exists':False,'file_count':0}
    checks['source_root']=all(v['exists'] for v in source_obs.values())
    persistent_ok=True
    for item in info.get('persistent_paths') or []:
      rel=Path(item.get('path',''))
      target=(runtime_root.parent / rel if rel.parts and rel.parts[0]=='runtime' else runtime_root / rel)
      try:
        st=target.stat(); mode=item.get('mode')
        persistent_ok &= st.st_uid == int(item.get('owner_uid',st.st_uid)) and st.st_gid == int(item.get('owner_gid',st.st_gid)) and (mode is None or (st.st_mode & 0o777)==int(str(mode),8))
      except (OSError,ValueError): persistent_ok=False
    checks['persistent_paths']=persistent_ok
    if info.get('deployment_mode')=='compose' and checks['docker']:
        for sub in (['ps'], ['network','ls'], ['volume','ls']):
            checks['docker_' + sub[0]] = run(['docker', *sub])[0] == 0
        argv=['docker','compose','--project-name',f'xmg-kb-{component}','--env-file',str(root/'.env'),'-f',str(root/'compose.upstream.yaml'),'-f',str(root/'compose.xmg.yaml'),'config','--format','json']
        rc,out,err=run(argv); checks['compose_config']=rc==0
        if rc==0:
            try:
                cfg=json.loads(out); images=[]; ports=[]
                for svc in cfg.get('services',{}).values():
                    images.append(svc.get('image','')); ports += svc.get('ports',[]) or []
                import re
                checks['compose_digest_only']=bool(images) and all(re.fullmatch(r'[^\s@]+(?:/[^\s@]+)*@sha256:[0-9a-f]{64}', i) for i in images)
                checks['compose_loopback']=all((p.get('host_ip')=='127.0.0.1') if isinstance(p,dict) else str(p).startswith('127.0.0.1:') for p in ports)
                checks['compose_dependencies_unpublished']=all(not (svc.get('ports') or []) for svc_name,svc in cfg.get('services',{}).items() if svc_name != component)
            except Exception:
                checks['compose_digest_only']=checks['compose_loopback']=checks['compose_dependencies_unpublished']=False
    status='PASS' if all(checks.values()) else 'BLOCKED'
    reason=None if status=='PASS' else 'preflight checks incomplete'
    return status, {'component':component,'status':status,'checks':checks,'observations':{'source_roots':source_obs},'blocker':reason,'capabilities':{'preflight':{'status':status,'reason':reason or 'all checks passed'}}}

def main():
    p=argparse.ArgumentParser(); p.add_argument('--lock',required=True); p.add_argument('--component',required=True); p.add_argument('--runtime-root',default='runtime'); p.add_argument('--output')
    a=p.parse_args()
    if a.component not in IDS: raise SystemExit(2)
    status,payload=preflight(a.component,Path(a.lock),Path(a.runtime_root))
    if a.output:
        out=Path(a.output); out.parent.mkdir(parents=True,exist_ok=True); fd,tmp=tempfile.mkstemp(dir=out.parent,prefix='.preflight.',text=True)
        with os.fdopen(fd,'w') as f: json.dump(payload,f,indent=2); f.write('\n'); f.flush(); os.fsync(f.fileno())
        os.replace(tmp,out)
    print(f'STATUS: {status}')
    raise SystemExit(0 if status=='PASS' else 10 if status=='BLOCKED' else 30)
if __name__=='__main__': main()
