#!/usr/bin/env python3
"""Phase 1 component ledger seed/update/render/gate CLI."""
from __future__ import annotations
import argparse, json, os, re, tempfile
from datetime import datetime, timezone
from pathlib import Path
import yaml
IDS=['outline','prefect','docling-serve','mineru','ragflow','langfuse','libreoffice','clamav','kag-poc']
GATE_SECTIONS=('Prerequisites','Required Components','Inputs','Preflight','Design','Execution','Evidence','Tests','Metrics','Acceptance','Risks','Rollback','Stop Conditions','Outputs','Next Gate')
SECRET_PATTERNS=(r"(?i)(password|token|secret|api[_-]?key)\s*[:=]\s*['\"]?[A-Za-z0-9_./~+-]{6,}",r"(?i)https?://[^/\s:@]+:[^/\s:@]+@")

def atomic(path:Path,obj):
    path.parent.mkdir(parents=True,exist_ok=True); fd,tmp=tempfile.mkstemp(dir=path.parent,prefix='.'+path.name+'.',text=True)
    with os.fdopen(fd,'w') as f: json.dump(obj,f,indent=2,ensure_ascii=False); f.write('\n'); f.flush(); os.fsync(f.fileno())
    os.replace(tmp,path)
def seed(lock:Path,out:Path):
    data=yaml.safe_load(lock.read_text()); rows=[]
    for cid,info in data.get('components',{}).items():
        digests=[a.get('digest_or_checksum') or a.get('checksum') or a.get('image_digest') for a in info.get('artifacts',[]) if isinstance(a,dict)]
        rows.append({'component':cid,'gate_role':info.get('gate_role'),'resolution':info.get('resolution_status'),'version':info.get('version'),'artifact_digests':[d for d in digests if d],'license':info.get('license',{}).get('id') if isinstance(info.get('license'),dict) else None,'port':(info.get('endpoint') or {}).get('host_port'),'installed':'NOT_RUN','smoke':'NOT_RUN','running_now':'NOT_RUN','status':'NOT_RUN','checks':{'health':'NOT_RUN','api':'NOT_RUN','restart':'NOT_RUN','persistence':'NOT_RUN'},'observed_resources':{},'captured_at':datetime.now(timezone.utc).isoformat(),'evidence_refs':info.get('evidence',[]),'blocker':info.get('blocker')})
    atomic(out,{'schema_version':'1','generated_at':datetime.now(timezone.utc).isoformat(),'components':rows})
def update(path:Path,cid:str,evidence:Path):
    doc=json.loads(path.read_text()); row=next((r for r in doc['components'] if r['component']==cid),None)
    if row is None: raise ValueError('unknown component')
    ev=json.loads(evidence.read_text())
    if not isinstance(ev,dict) or ev.get('component') not in (None,cid): raise ValueError('evidence component mismatch')
    caps=ev.get('capabilities')
    if not isinstance(caps,dict) or not caps: raise ValueError('evidence missing capabilities')
    for value in caps.values():
        if not isinstance(value,dict) or value.get('status') not in ('PASS','BLOCKED','N/A') or not str(value.get('reason','')).strip(): raise ValueError('invalid capability evidence')
    row.update({k:v for k,v in ev.items() if k not in ('component',)})
    row['component']=cid; row['captured_at']=datetime.now(timezone.utc).isoformat(); atomic(path,doc)
def render(src:Path,dst:Path):
    doc=json.loads(src.read_text());
    if not isinstance(doc,dict) or not isinstance(doc.get('components'),list): raise ValueError('invalid report input')
    lines=['# Phase 1 Components','',f"Generated: {doc.get('generated_at','')}",'','| Component | Resolution | Status | Installed | Smoke | Running | Blocker |','|---|---|---|---|---|---|---|']
    for r in doc.get('components',[]): lines.append('| {component} | {resolution} | {status} | {installed} | {smoke} | {running_now} | {blocker} |'.format(**{k:str(r.get(k,'')).replace('|','\\|') for k in ('component','resolution','status','installed','smoke','running_now','blocker')}))
    dst.parent.mkdir(parents=True,exist_ok=True)
    fd,tmp=tempfile.mkstemp(dir=dst.parent,prefix='.'+dst.name+'.',text=True)
    with os.fdopen(fd,'w') as f:
        f.write('\n'.join(lines)+'\n'); f.flush(); os.fsync(f.fileno())
    os.replace(tmp,dst)

def atomic_text(path: Path, text: str) -> None:
    """Write a report atomically and durably without exposing partial output."""
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix='.' + path.name + '.', text=True)
    with os.fdopen(fd, 'w') as f:
        f.write(text)
        f.flush(); os.fsync(f.fileno())
    os.replace(tmp, path)

def _report_status(rows:list[dict]) -> tuple[str,list[str]]:
    blocked=[r.get('component','?') for r in rows if r.get('gate_role')=='required' and (r.get('resolution')!='RESOLVED' or r.get('status')!='PASS')]
    return ('PASS' if not blocked else 'BLOCKED'), blocked

def _validate_report(path:Path,text:str,expected_status:str)->None:
    headings=re.findall(r"^## (.+)$",text,re.M)
    if headings!=list(GATE_SECTIONS): raise ValueError('invalid gate sections')
    status_tokens=re.findall(r"(?<![A-Z0-9_])STATUS:\s*(PASS|BLOCKED)\b",text)
    status_lines=re.findall(r"^STATUS: (PASS|BLOCKED)$",text,re.M)
    if status_tokens!=[expected_status] or status_lines!=[expected_status]: raise ValueError('gate status token mismatch')
    for pattern in SECRET_PATTERNS:
        if re.search(pattern,text): raise ValueError('gate secret leak detected')
    repo_reports=(Path(__file__).resolve().parents[2]/'reports').resolve()
    for link in re.findall(r"\[[^\]]+\]\(([^)]+)\)",text):
        if link.startswith('/') or '..' in Path(link).parts: raise ValueError(f'gate floating ref: {link}')
        if path.parent.resolve()==repo_reports:
            target=(path.parent/link).resolve()
            if not target.is_file() or target.parent != repo_reports: raise ValueError(f'gate missing ref: {link}')

def _validate_component_ledger(json_path: Path, rows: list[dict]) -> None:
    markdown = json_path.with_name('01-components.md')
    if not markdown.is_file():
        # Unit fixtures may exercise gate logic with an isolated JSON ledger;
        # the production reports directory must always have its sibling table.
        if json_path.name == '01-components.json':
            raise ValueError('component markdown ledger missing')
        return
    text = markdown.read_text()
    for row in rows:
        fields = [str(row.get(k, '')).replace('|', '\\|')
                  for k in ('component','resolution','status','installed','smoke','running_now','blocker')]
        expected = '| ' + ' | '.join(fields) + ' |'
        if expected not in text:
            raise ValueError(f'component markdown ledger drift: {row.get("component", "?")}')

def _component_table(rows:list[dict])->list[str]:
    lines=['| Component | Role | Resolution | Status | Installed | Smoke | Running | Blocker |','| --- | --- | --- | --- | --- | --- | --- | --- |']
    for row in rows:
        values={k:str(row.get(k,'')).replace('|','\\|') for k in ('component','gate_role','resolution','status','installed','smoke','running_now','blocker')}
        lines.append('| {component} | {gate_role} | {resolution} | {status} | {installed} | {smoke} | {running_now} | {blocker} |'.format(**values))
    return lines

def _gate_markdown(rows:list[dict], verdict:str, blocked:list[str], phase_report:Path, health_report:Path)->tuple[str,str]:
    blockers='none' if not blocked else ', '.join(blocked)
    optional_note='optional `kag-poc` remains non-gating'
    phase_lines=[
        '# Phase 1 Bootstrap','',f'STATUS: {verdict}','',
        '## Prerequisites','',
        'Phase 0 gate remains the only startup prerequisite for this aggregate closure.',
        '[Phase 0 Gate](phase-00-baseline.md) records `PHASE_0: PASS`; this task does not authorize any component startup.','',
        '## Required Components','',
        'The required gate set is `outline`, `prefect`, `docling-serve`, `mineru`, `ragflow`, `langfuse`, `libreoffice`, and `clamav`.',
        f'Required components still blocking closure: {blockers}.',
        f'The {optional_note}.','',
        '## Inputs','',
        '[Phase 0 Gate](phase-00-baseline.md)',
        '[Component Ledger](01-components.json)',
        '[Rendered Component Ledger](01-components.md)','',
        '## Preflight','',
        'The aggregate gate is read-only with respect to component runtime state: it evaluates existing Phase 1 ledger evidence and leaves every component stopped.',
        'No Docker pull, compose up, native package install, or source-directory mutation is permitted in this closure step.','',
        '## Design','',
        'BOOTSTRAP_MODE: STAGED',
        'gate_capture_state=ALL_STOPPED',
        'handoff_state=ALL_STOPPED',
        'A required component must be both `RESOLVED` and `PASS`; any weaker state keeps the aggregate gate blocked.','',
        '## Execution','',
        'This gate rerenders the aggregate Markdown from `reports/01-components.json` and does not invoke component `--install`, `--verify`, or startup commands.',
        'The conclusion is derived only from the JSON ledger plus the Phase 0 prerequisite state.','',
        '## Evidence','',
        f'AGGREGATE_GATE_VERDICT: {verdict}',
        f'REQUIRED_BLOCKERS: {len(blocked)}',
        f'REQUIRED_BLOCKER_LIST: {blockers}',
        f'{optional_note}.',
        '[Component Health](component-health.md) is regenerated from the same ledger input.','',
        '## Tests','',
        'FOCUSED_GATE_COMMAND: python3 -m pytest platform/tests/phase1/test_phase1_gate.py -q',
        'FULL_PHASE1_COMMAND: python3 -m pytest platform/tests/phase1 -q',
        'FULL_PLATFORM_COMMAND: python3 -m pytest platform/tests -q','',
        '## Metrics','',
        f'REQUIRED_COMPONENT_COUNT: {sum(1 for r in rows if r.get("gate_role")=="required")}',
        f'OPTIONAL_COMPONENT_COUNT: {sum(1 for r in rows if r.get("gate_role")=="optional")}',
        f'REQUIRED_BLOCKED_COUNT: {len(blocked)}',
        f'ALL_STOPPED_COMPONENT_COUNT: {sum(1 for r in rows if str(r.get("running_now"))!="PASS")}','',
        '## Acceptance','',
        f'- [{" " if verdict=="BLOCKED" else "x"}] Every required component is `RESOLVED` and `PASS`.',
        '- [x] The gate output is derived without starting components.',
        '- [x] The aggregate closure keeps `handoff_state=ALL_STOPPED`.','',
        '## Risks','',
        'Any future component-resolution change can alter this gate outcome, so the ledger must be regenerated before re-attempting closure.',
        'As of 2026-09-01, required blockers remain evidence-closure failures rather than runtime health failures.','',
        '## Rollback','',
        'Rollback is limited to replacing the generated Markdown reports; this step makes no runtime, Docker, Raw, Legacy, or curated-doc changes.','',
        '## Stop Conditions','',
        '| Gate Stop Condition | State | Decision | Evidence |',
        '| --- | --- | --- | --- |',
        f'| required component unresolved or not PASS | {"ACTIVE" if blocked else "INACTIVE"} | {"STOP" if blocked else "CLEAR"} | required blockers: {blockers} |',
        '| component startup requested by gate step | INACTIVE | CLEAR | aggregate closure does not invoke startup commands |',
        '| handoff state differs from ALL_STOPPED | INACTIVE | CLEAR | gate_capture_state=ALL_STOPPED; handoff_state=ALL_STOPPED |','',
        '## Outputs','',
        f'This command atomically writes `reports/{phase_report.name}` and `reports/{health_report.name}`.',
        'The ledger inputs remain `reports/01-components.json` and `reports/01-components.md`.','',
        '## Next Gate','',
        'Phase 1 remains blocked until every required component becomes both `RESOLVED` and `PASS`.',
        'Any later PASS handoff may explicitly move to `handoff_state=OUTLINE_RUNNING`; this closure does not.',''
    ]
    health_lines=[
        '# Component Health','',f'STATUS: {verdict}','',
        '## Prerequisites','',
        'This report is generated from the Phase 1 component ledger after the Phase 0 gate stayed `PASS`.',
        '[Phase 0 Gate](phase-00-baseline.md) remains the upstream prerequisite.','',
        '## Required Components','',
        'The table below reflects every required gate participant and the optional `kag-poc` row.',
        f'Blocking required components: {blockers}.',
        f'The {optional_note}.','',
        '## Inputs','',
        '[Component Ledger](01-components.json)',
        '[Rendered Component Ledger](01-components.md)','',
        '## Preflight','',
        'No component is started to generate this report. The health view summarizes already-captured ledger state only.','',
        '## Design','',
        'The health report mirrors the JSON ledger and must keep the same aggregate verdict as the phase gate.',
        'gate_capture_state=ALL_STOPPED',
        'handoff_state=ALL_STOPPED','',
        '## Execution','',
        'The health summary is rendered from the same JSON input as the phase report, so any mismatch is a gate-generation defect.','',
        '## Evidence','',
        f'HEALTH_REPORT_VERDICT: {verdict}',
        f'REQUIRED_BLOCKER_LIST: {blockers}',''
    ] + _component_table(rows) + [
        '',
        '## Tests','',
        'FOCUSED_GATE_COMMAND: python3 -m pytest platform/tests/phase1/test_phase1_gate.py -q','',
        '## Metrics','',
        f'TOTAL_COMPONENTS: {len(rows)}',
        f'REQUIRED_BLOCKED_COUNT: {len(blocked)}','',
        '## Acceptance','',
        '- [x] Markdown rows mirror the JSON ledger.',
        f'- [{" " if verdict=="BLOCKED" else "x"}] Required rows are all `RESOLVED` and `PASS`.','',
        '## Risks','',
        'The ledger can become stale if component evidence changes without rerendering this report.','',
        '## Rollback','',
        'Rollback is limited to regenerating the Markdown from the JSON ledger.','',
        '## Stop Conditions','',
        '| Gate Stop Condition | State | Decision | Evidence |',
        '| --- | --- | --- | --- |',
        f'| required component unresolved or not PASS | {"ACTIVE" if blocked else "INACTIVE"} | {"STOP" if blocked else "CLEAR"} | required blockers: {blockers} |',
        '| handoff state differs from ALL_STOPPED | INACTIVE | CLEAR | gate_capture_state=ALL_STOPPED; handoff_state=ALL_STOPPED |','',
        '## Outputs','',
        f'Generated outputs: `reports/{phase_report.name}` and `reports/{health_report.name}` with source rows from `reports/01-components.json`.','',
        '## Next Gate','',
        'Resolve required blockers before attempting a Phase 1 PASS closure.',''
    ]
    return '\n'.join(phase_lines), '\n'.join(health_lines)

def gate(j:Path, phase:Path, health:Path) -> int:
    doc=json.loads(j.read_text())
    rows=doc.get('components') if isinstance(doc,dict) else None
    if not isinstance(rows,list): raise ValueError('invalid gate input')
    _validate_component_ledger(j, rows)
    verdict, blocked = _report_status(rows)
    phase_text, health_text = _gate_markdown(rows, verdict, blocked, phase, health)
    _validate_report(phase, phase_text, verdict)
    _validate_report(health, health_text, verdict)
    if phase.suffix.lower() in {'.md', '.markdown'} and health.suffix.lower() in {'.md', '.markdown'}:
        # Prepare both outputs before publication and roll back the first
        # replacement if the second one fails, avoiding a mixed report pair.
        old = {p: p.read_bytes() for p in (phase, health) if p.exists()}
        temps = []
        try:
            for path, content in ((phase, phase_text), (health, health_text)):
                path.parent.mkdir(parents=True, exist_ok=True)
                fd, tmp = tempfile.mkstemp(dir=path.parent, prefix='.' + path.name + '.', text=True)
                with os.fdopen(fd, 'w') as f:
                    f.write(content); f.flush(); os.fsync(f.fileno())
                temps.append((path, Path(tmp)))
            for path, tmp in temps: os.replace(tmp, path)
        except Exception:
            for path, content in old.items(): atomic_text(path, content.decode())
            for path, _ in temps:
                if path not in old and path.exists(): path.unlink()
            raise
        finally:
            for _, tmp in temps:
                if tmp.exists(): tmp.unlink()
    elif phase.suffix.lower() in {'.md', '.markdown'}: atomic_text(phase, phase_text)
    elif health.suffix.lower() in {'.md', '.markdown'}: atomic_text(health, health_text)
    blockers='required components ' + ', '.join(blocked) if blocked else 'none'
    print(f'STATUS: {verdict}')
    if blocked: print(f'BLOCKER: {blockers}')
    return 0 if verdict == 'PASS' else 10
def main():
    p=argparse.ArgumentParser(); sub=p.add_subparsers(dest='cmd',required=True)
    s=sub.add_parser('seed'); s.add_argument('--lock',type=Path,required=True); s.add_argument('--json',type=Path,required=True)
    u=sub.add_parser('update'); u.add_argument('--json',type=Path,required=True); u.add_argument('--component',required=True); u.add_argument('--evidence',type=Path,required=True)
    r=sub.add_parser('render'); r.add_argument('--json',type=Path,required=True); r.add_argument('--markdown',type=Path,required=True)
    g=sub.add_parser('gate'); g.add_argument('--json',type=Path,required=True); g.add_argument('--phase-report',type=Path,required=True); g.add_argument('--health-report',type=Path,required=True)
    a=p.parse_args()
    try:
        if a.cmd=='seed': seed(a.lock,a.json)
        elif a.cmd=='update': update(a.json,a.component,a.evidence)
        elif a.cmd=='render': render(a.json,a.markdown)
        else: raise SystemExit(gate(a.json,a.phase_report,a.health_report))
    except Exception as e: print(f'ERROR: {e}',file=__import__('sys').stderr); raise SystemExit(2)
if __name__=='__main__': main()
