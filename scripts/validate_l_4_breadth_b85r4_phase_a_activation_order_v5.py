from __future__ import annotations
import hashlib,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))
from lib.l4_b85r4_structural_scanner_v5 import MAX_BYTES
GATE=ROOT/'experiments/l_4_breadth_b85r4_phase_a_activation_order_v5.json'
PATHS={"scanner":"lib/l4_b85r4_structural_scanner_v5.py","runner":"scripts/run_l_4_breadth_b85r4_phase_b_preflight_v5.py","report_schema":"schemas/l_4_breadth_b85r4_structural_preflight_report_v5.schema.json","activation_schema":"schemas/l_4_breadth_b85r4_phase_b_activation_v5.schema.json","report_validator":"scripts/validate_l_4_breadth_b85r4_structural_preflight_report_v5.py","synthetic_manifest":"tests/fixtures/l4_b85r4/structural_manifest_v5.json","synthetic_payload":"tests/fixtures/l4_b85r4/u8_symbol_session_dates_v5.json"}
def sha(p):
 try:
  with p.open('rb') as h:r=h.read(MAX_BYTES+1)
  return hashlib.sha256(r).hexdigest() if len(r)<=MAX_BYTES else None
 except OSError:return None
def validate(path=GATE):
 try:g=json.loads(path.read_text(encoding='utf-8'))
 except Exception as e:return {'status':'blocked','blockers':[type(e).__name__]}
 b=[]
 if not isinstance(g,dict) or any(g.get(k)!=v for k,v in {"schema_version":"lily_l4_b85r4_phase_a_activation_order_v5","order_id":"B8.5R4","phase":"A","gate_id":"l_4_breadth_b85r4_phase_a_activation_order_v5","supersedes_gate_id":"l_4_breadth_b85r3_phase_a_activation_order_v4","activation_for_gate_id":"l_4_breadth_b84r2_activation_contract_v3","hypothesis_id":"L-4","status":"published_E0_phase_a_remediation_awaiting_inspector_acceptance_and_activation","evidence_ceiling":"E0","edge_claim":"none","validation_seal":{"status":"sealed_not_accessed","accessed":False}}.items()):b.append('identity')
 for n,p in PATHS.items():
  if g.get('implementation',{}).get(n,{}).get('path')!=p or g.get('implementation',{}).get(n,{}).get('sha256')!=sha(ROOT/p):b.append(n)
 if set(g.get('implementation',{}))!=set(PATHS):b.append('implementation_shape')
 if g.get('future_phase_b_contract')!={"status":"not_executed","activation_lifecycle":"v5 Phase-A gate commit and CI precede a later tracked activation checkpoint; activation references accepted_gate_head_sha and CI head, never its own checkpoint. Reports bind that activation blob and producing activation commit; later report commits validate it as an ancestor blob provenance.","repo_relative_activation_record_path":"experiments/activation_records/l_4_breadth_b85r4_phase_b_activation_v5.json","exact_execution_flag":"--execute-one-shot"}:b.append('lifecycle')
 if not isinstance(g.get('phase_a_authorizations'),dict) or not g['phase_a_authorizations'] or any(value is not False for value in g['phase_a_authorizations'].values()) or g.get('phase_a_access_counts')!={"real_container_read":0,"environment_read":0,"market_or_return_value_decode":0,"execution":0,"validation_access":0}:b.append('sealed')
 return {'status':'pass' if not b else 'blocked','blockers':b}
if __name__=='__main__':
 r=validate();print(json.dumps(r));raise SystemExit(r['status']!='pass')
