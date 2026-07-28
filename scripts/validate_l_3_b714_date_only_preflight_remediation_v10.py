"""Hermetic B7.14R8/v10 validator; historical proof is committed snapshots only."""
from __future__ import annotations
import hashlib,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; GATE=ROOT/'experiments/l_3_b714_date_only_preflight_remediation_v10.json'; MANIFEST=ROOT/'experiments/locked_gates.jsonl'
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))
from lib.provenance import file_sha256
from scripts.validate_l_3_b714r8_snapshots_v1 import validate as validate_snapshots
AUTH={'real_container_access':False,'container_hashing':False,'date_inspection':False,'return_parsing':False,'execution':False,'research_decision':False,'ledger_write':False,'validation':False,'provider':False,'credentials':False,'broker':False,'paid':False,'paper_trade':False,'real_money':False}
def digest(path):return hashlib.sha256((ROOT/path).read_bytes()).hexdigest()
def validate():
 try:gate=json.loads(GATE.read_text(encoding='utf-8')); rows=[json.loads(x) for x in MANIFEST.read_text(encoding='utf-8').splitlines() if x]
 except (OSError,json.JSONDecodeError) as exc:return {'status':'blocked','blockers':[type(exc).__name__]}
 blockers=[]
 if {k:gate.get(k) for k in ('schema_version','order_id','gate_id','supersedes_gate_id','hypothesis_id','status','evidence_ceiling','edge_claim')}!={'schema_version':'lily_l3_b714_date_only_preflight_remediation_v10','order_id':'B7.14R8','gate_id':'l_3_b714_date_only_preflight_remediation_v10','supersedes_gate_id':'l_3_b714_date_only_preflight_remediation_v9','hypothesis_id':'L-3','status':'locked_E0_snapshot_only_remediation','evidence_ceiling':'E0','edge_claim':'none'}:blockers.append('identity')
 if gate.get('authorizations')!=AUTH or gate.get('validation_seal')!={'status':'sealed_not_accessed','accessed':False}:blockers.append('scope')
 for section in ('source_binding','artifact_identities'):
  for item in gate.get(section,{}).values():
   if not isinstance(item,dict) or digest(item['path'])!=item['sha256']:blockers.append(section)
 if validate_snapshots().get('status')!='pass':blockers.append('snapshots')
 matches=[r for r in rows if r.get('gate_id')==gate['gate_id']]
 if len(matches)!=1 or matches[0].get('artifact_sha256')!=digest('experiments/l_3_b714_date_only_preflight_remediation_v10.json') or matches[0].get('validator_sha256')!=digest('scripts/validate_l_3_b714_date_only_preflight_remediation_v10.py'):blockers.append('manifest')
 return {'status':'pass' if not blockers else 'blocked','blockers':sorted(set(blockers))}
if __name__=='__main__':
 r=validate();print(json.dumps(r,sort_keys=True));raise SystemExit(r['status']!='pass')
