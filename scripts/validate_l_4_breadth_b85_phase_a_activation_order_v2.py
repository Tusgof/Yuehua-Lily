"""Fail-closed validator for the B8.5R Phase-A runnable structural contract."""
from __future__ import annotations
import hashlib,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))
from lib.provenance import file_sha256
GATE=ROOT/'experiments/l_4_breadth_b85_phase_a_activation_order_v2.json'
PATHS={"scanner":"lib/l4_b85_structural_scanner_v1.py","runner":"scripts/run_l_4_breadth_b85_phase_b_preflight_v1.py","report_schema":"schemas/l_4_breadth_b85_structural_preflight_report_v1.schema.json","report_validator":"scripts/validate_l_4_breadth_b85_structural_preflight_report_v1.py","synthetic_manifest":"tests/fixtures/l4_b85/structural_manifest_v1.json","synthetic_payload":"tests/fixtures/l4_b85/u8_symbol_session_dates_v1.json"}
AUTH={"data","container","path_inspection","environment","market","return","value","signal","position","covariance","regime","cost","pnl","execution","report_decision","ledger","validation","provider","network","credentials","broker","paid","paper_trade","real_money"}
def sha(path:Path)->str|None:
 try:file_sha256(path);return hashlib.sha256(path.read_bytes().replace(b'\r\n',b'\n')).hexdigest()
 except OSError:return None
def identity(gate_id:str)->dict|None:
 try:
  row=next(json.loads(x) for x in (ROOT/'experiments/locked_gates.jsonl').read_text(encoding='utf-8').splitlines() if json.loads(x).get('gate_id')==gate_id)
  return {k:row.get(k) for k in ('gate_id','artifact_path','artifact_sha256','validator_path','validator_sha256')}
 except Exception:return None
def validate(path:Path=GATE)->dict:
 try:p=json.loads(path.read_text(encoding='utf-8'))
 except Exception as e:return {'status':'blocked','blockers':[type(e).__name__]}
 b=[]; ident={"schema_version":"lily_l4_b85_phase_a_activation_order_v2","order_id":"B8.5R","phase":"A","gate_id":"l_4_breadth_b85_phase_a_activation_order_v2","supersedes_gate_id":"l_4_breadth_b85_phase_a_activation_order_v1","activation_for_gate_id":"l_4_breadth_b84r2_activation_contract_v3","hypothesis_id":"L-4","status":"published_E0_phase_a_remediation_awaiting_inspector_acceptance","evidence_ceiling":"E0","edge_claim":"none"}
 if any(p.get(k)!=v for k,v in ident.items()):b.append('identity')
 v1={"gate_id":"l_4_breadth_b85_phase_a_activation_order_v1","artifact_path":"experiments/l_4_breadth_b85_phase_a_activation_order_v1.json","artifact_sha256":"d8887c5851a06605895ac287676d7912bedca4869bae73ccabf57317936ba962","validator_path":"scripts/validate_l_4_breadth_b85_phase_a_activation_order_v1.py","validator_sha256":"6e6e3b65c82b02ffdc51727ef52124667ec3235f80d1aba5f8e2538f5d72d1bd"}; v1['manifest_identity']=dict(v1)
 if p.get('source_binding',{}).get('rejected_v1')!=v1 or sha(ROOT/v1['artifact_path'])!=v1['artifact_sha256'] or sha(ROOT/v1['validator_path'])!=v1['validator_sha256'] or identity(v1['gate_id'])!=v1['manifest_identity']:b.append('rejected_v1_binding')
 impl=p.get('implementation',{})
 for name,relative in PATHS.items():
  row=impl.get(name,{})
  if row.get('path')!=relative or row.get('sha256')!=sha(ROOT/relative):b.append('implementation:'+name)
 c=p.get('future_phase_b_contract',{}); req={"status":"not_executed","one_shot_real_preflight_maximum":1,"storage_root_variable":"LILY_DATA_ROOT","manifest_storage_reference":"${LILY_DATA_ROOT}/sealed/l4_b85/l4_b85_structural_manifest_v1.json","payload_storage_reference":"${LILY_DATA_ROOT}/sealed/l4_b85/l4_b85_u8_symbol_session_dates_v1.json","container_identity":"lily-l4-falsification-pre2016-v1"}
 if any(c.get(k)!=v for k,v in req.items()) or c.get('preconditions')!=['inspector_acceptance_recorded','exact_sha_hermetic_ci_success'] or 'No unavailable pre-known manifest hash is claimed.' not in c.get('manifest_hash_semantics','') or 'no fallback, glob, directory listing' not in c.get('resolution_rule','') or 'Raw bytes first.' not in c.get('scanner_rule',''):b.append('future_phase_b_contract')
 a=p.get('phase_a_authorizations',{}); counts=p.get('phase_a_access_counts',{})
 if set(a)!=AUTH or any(x is not False for x in a.values()):b.append('phase_a_authorizations')
 if not isinstance(counts,dict) or any(x!=0 for x in counts.values()):b.append('phase_a_access_counts')
 if p.get('validation_seal')!={'status':'sealed_not_accessed','accessed':False}:b.append('validation_seal')
 return {'status':'pass' if not b else 'blocked','blockers':sorted(set(b))}
if __name__=='__main__':
 r=validate();print(json.dumps(r));raise SystemExit(r['status']!='pass')
