from __future__ import annotations
import hashlib,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; GATE=ROOT/'experiments/l_4_breadth_b88r_phase_a_execution_contract_v2.json'; LOCKED=ROOT/'experiments/locked_gates_v2.jsonl'
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))
from lib.l4_b88r_scientific_engine_v2 import AUTHORIZATIONS,SEAL
def sha(p:Path):return hashlib.sha256(p.read_bytes()).hexdigest()
def validate(path:Path=GATE,*,require_manifest=True):
 b=[]
 try:g=json.loads(path.read_text('ascii'))
 except Exception:return {'status':'blocked','blockers':['unreadable']}
 required={'schema_version','order_id','gate_id','supersedes_gate_id','hypothesis_id','status','evidence_ceiling','edge_claim','v1_rejection','science','activation','validation_seal','authorizations','access_counts','no_force_push_closure_rule','hard_stops'}
 if set(g)!=required:b+=['closed_world']
 if {k:g.get(k) for k in ('schema_version','order_id','gate_id','supersedes_gate_id','hypothesis_id','status','evidence_ceiling','edge_claim')}!={'schema_version':'lily_l4_b88r_phase_a_execution_contract_v2','order_id':'B8.8R','gate_id':'l_4_breadth_b88r_phase_a_execution_contract_v2','supersedes_gate_id':'l_4_breadth_b88_phase_a_execution_contract_v1','hypothesis_id':'L-4','status':'locked_E0_synthetic_machinery_v2','evidence_ceiling':'E0','edge_claim':'none'}:b+=['identity']
 if g.get('validation_seal')!=SEAL or g.get('authorizations')!=AUTHORIZATIONS or any(g.get('access_counts',{}).values()):b+=['seals']
 if g.get('science',{}).get('u_primary')!='q' or g.get('science',{}).get('cutoff')!='2015-12-31':b+=['science']
 if g.get('activation',{}).get('caller_may_not_supply_schema_or_owner') is not True or g.get('activation',{}).get('committed_git_show_bootstrap_required') is not True or g.get('activation',{}).get('pre_import_blob_checks_required') is not True or g.get('activation',{}).get('dirty_dependency_rejected') is not True:b+=['activation']
 if require_manifest:
  try:
   rows=[json.loads(x) for x in LOCKED.read_text('ascii').splitlines() if x]; found=[x for x in rows if x.get('gate_id')==g['gate_id']]
   if len(found)!=1 or found[0].get('artifact_sha256')!=sha(path) or found[0].get('validator_sha256')!=sha(Path(__file__)):b+=['locked_manifest']
  except Exception:b+=['locked_manifest']
 return {'status':'pass' if not b else 'blocked','blockers':sorted(set(b))}
if __name__=='__main__':
 r=validate();print(json.dumps(r,sort_keys=True));raise SystemExit(r['status']!='pass')
