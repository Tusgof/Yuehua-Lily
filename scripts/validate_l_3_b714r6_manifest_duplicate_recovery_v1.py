from __future__ import annotations
import hashlib
import json
import subprocess
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path: sys.path.insert(0,str(ROOT))
from lib.provenance import file_sha256
RECOVERY=ROOT/'experiments/l_3_b714r6_manifest_duplicate_recovery_v1.json'
MANIFEST=ROOT/'experiments/locked_gates.jsonl'
GATE='l_3_b714_date_only_preflight_remediation_v7'
def validate():
 try: recovery=json.loads(RECOVERY.read_text(encoding='utf-8')); current=MANIFEST.read_text(encoding='utf-8').splitlines()
 except (OSError,json.JSONDecodeError) as exc:return {'status':'blocked','blockers':[type(exc).__name__]}
 prior=subprocess.run(['git','show',f"{recovery.get('prior_commit')}:experiments/locked_gates.jsonl"],cwd=ROOT,text=True,capture_output=True,check=False)
 old=[line for line in prior.stdout.splitlines() if f'"gate_id":"{GATE}"' in line]
 now=[line for line in current if f'"gate_id":"{GATE}"' in line]
 bad=[]
 if recovery.get('prior_commit')!='b2d349d4ce3fcfb5e275664f20e69844fba4823a' or recovery.get('access')!={'data':False,'container':False,'provider':False,'research_log':False}:bad.append('identity')
 if len(old)!=2 or old[0]!=old[1] or len(now)!=1 or now[0]!=old[0]:bad.append('exact_duplicate_recovery')
 if not file_sha256(RECOVERY):bad.append('recovery_missing')
 return {'status':'pass' if not bad else 'blocked','blockers':bad}
if __name__=='__main__':
 result=validate();print(json.dumps(result,sort_keys=True));raise SystemExit(result['status']!='pass')
