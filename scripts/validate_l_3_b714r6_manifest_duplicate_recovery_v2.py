from __future__ import annotations
import json, subprocess, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path: sys.path.insert(0,str(ROOT))
from lib.provenance import file_sha256
RECOVERY=ROOT/'experiments/l_3_b714r6_manifest_duplicate_recovery_v2.json'
MARKER='"gate_id":"l_3_b714_date_only_preflight_remediation_v7"'
def _lines(commit):
 r=subprocess.run(['git','show',f'{commit}:experiments/locked_gates.jsonl'],cwd=ROOT,text=True,capture_output=True,check=False)
 return r.returncode,[x for x in r.stdout.splitlines() if x]
def validate():
 try:o=json.loads(RECOVERY.read_text(encoding='utf-8'))
 except (OSError,json.JSONDecodeError) as exc:return {'status':'blocked','blockers':[type(exc).__name__]}
 expected={'schema_version':'lily_l3_b714r6_manifest_duplicate_recovery_v2','duplicated_commit':'b2d349d4ce3fcfb5e275664f20e69844fba4823a','recovery_commit':'5fb2f36969d20ad41df85efe60fec1faaefafd4e','gate_id':'l_3_b714_date_only_preflight_remediation_v7','access':{'data':False,'container':False,'provider':False,'research_log':False}}
 a,old=_lines(o.get('duplicated_commit','')); b,new=_lines(o.get('recovery_commit','')); positions=[i for i,x in enumerate(old) if MARKER in x]; oldv=[old[i] for i in positions]; newv=[x for x in new if MARKER in x]
 ok=o==expected and not a and not b and len(oldv)==2 and oldv[0]==oldv[1] and len(newv)==1 and newv[0]==oldv[0] and new==old[:positions[1]]+old[positions[1]+1:] and bool(file_sha256(RECOVERY))
 return {'status':'pass' if ok else 'blocked','blockers':[] if ok else ['portable_recovery_mismatch']}
if __name__=='__main__':
 r=validate();print(json.dumps(r,sort_keys=True));raise SystemExit(r['status']!='pass')
