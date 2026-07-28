"""Hermetic B7.14R8 historical snapshot and duplicate-recovery validator."""
from __future__ import annotations
import base64, hashlib, json, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))
from lib.provenance import file_sha256
INDEX=ROOT/'experiments/l_3_b714r8_snapshot_index_v1.json'
def _digest(path:Path, encoded:bool=False)->str:
    raw=path.read_bytes()
    return hashlib.sha256(base64.b64decode(raw) if encoded else raw).hexdigest()
def validate():
 try: index=json.loads(INDEX.read_text(encoding='utf-8'))
 except (OSError,json.JSONDecodeError) as exc:return {'status':'blocked','blockers':[type(exc).__name__]}
 blockers=[]; snapshots=index.get('snapshots',{})
 if index.get('schema_version')!='lily_l3_b714r8_snapshot_index_v1' or index.get('access')!={'data':False,'container':False,'provider':False,'research_log':False}:blockers.append('index')
 for name in ('v5','v6','v7','v8'):
  item=snapshots.get(name,{}); path=ROOT/str(item.get('snapshot',''))
  try: payload=json.loads(base64.b64decode(path.read_bytes()) if item.get('encoding')=='base64' else path.read_bytes())
  except (OSError,ValueError,json.JSONDecodeError): blockers.append(name);continue
  if _digest(path,item.get('encoding')=='base64')!=item.get('sha256') or payload.get('gate_id')!=f'l_3_b714_date_only_preflight_remediation_{name}':blockers.append(name)
 try:
  duplicate=(ROOT/snapshots['duplicated_manifest']['snapshot']).read_text(encoding='utf-8').splitlines(); recovered=(ROOT/snapshots['recovered_manifest']['snapshot']).read_text(encoding='utf-8').splitlines()
  if len(duplicate)!=2 or duplicate[0]!=duplicate[1] or recovered!=duplicate[:1] or json.loads(recovered[0]).get('gate_id')!='l_3_b714_date_only_preflight_remediation_v7':blockers.append('recovery')
 except (OSError,json.JSONDecodeError):blockers.append('recovery')
 try:
  proof=json.loads((ROOT/'methodology_snapshots/b714r8/manifest_states/history_proof.json').read_text(encoding='utf-8')); current=(ROOT/'experiments/locked_gates.jsonl').read_bytes().splitlines()
  dup,rec=proof['duplicated'],proof['recovered']; indices=proof['duplicate']['indices']; vector=lambda rows:[hashlib.sha256(row).hexdigest() for row in rows]
  expected=dup['line_sha256'][:indices[1]]+dup['line_sha256'][indices[1]+1:]
  if indices!=[indices[0],indices[0]+1] or dup['line_sha256'][indices[0]]!=proof['duplicate']['row_sha256'] or rec['line_sha256']!=expected or vector(current)[:rec['line_count']]!=expected: blockers.append('history_proof')
 except (OSError,KeyError,TypeError,json.JSONDecodeError): blockers.append('history_proof')
 return {'status':'pass' if not blockers else 'blocked','blockers':sorted(set(blockers))}
if __name__=='__main__':
 r=validate();print(json.dumps(r,sort_keys=True));raise SystemExit(r['status']!='pass')
