import os
import subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
def test_blocked_check():
 p=subprocess.run([str(ROOT/'platform/bootstrap.sh'),'--check','outline'],capture_output=True,text=True)
 assert p.returncode==10 and 'STATUS: BLOCKED' in p.stdout

def test_bad_action_and_shell_text_are_rejected():
 p=subprocess.run([str(ROOT/'platform/bootstrap.sh'),'--status','outline;id'],capture_output=True,text=True)
 assert p.returncode==2

def test_blocked_install_never_invokes_docker():
 p=subprocess.run([str(ROOT/'platform/bootstrap.sh'),'--install','outline'],capture_output=True,text=True)
 assert p.returncode==20 and 'STATUS: BLOCKED' in p.stdout

def test_status_returns_40_when_docker_is_unavailable(tmp_path):
 fake=tmp_path/'docker'
 fake.write_text('#!/bin/sh\nexit 127\n')
 fake.chmod(0o755)
 env=os.environ.copy()
 env['PATH']=f"{tmp_path}:/usr/bin:/bin"
 p=subprocess.run([str(ROOT/'platform/bootstrap.sh'),'--status','outline'],capture_output=True,text=True,env=env)
 assert p.returncode==40 and 'STATUS: UNAVAILABLE' in p.stdout

def test_unknown_option_is_rejected():
 p=subprocess.run([str(ROOT/'platform/bootstrap.sh'),'--install','outline','extra'],capture_output=True,text=True)
 assert p.returncode==2

def test_install_source_contains_fail_closed_deployment_guards():
 script=(ROOT/'platform/bootstrap.sh').read_text()
 assert 'dep.get("path")' in script and 'upstream_sha256' in script
 assert 'relative_to(root)' in script
 assert 'actual != expected' in script
