"""Fail-closed B8.4 synthetic-only future-preflight contract validator."""
from __future__ import annotations
import json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))
from lib.provenance import file_sha256
from lib.l4_b84_preflight import canonical_fixture_sha256
GATE=ROOT/'experiments/l_4_breadth_b84_activation_contract_v1.json'
AUTH={"data","container","market","return","signal","position","covariance","regime","cost","pnl","execution","report_decision","ledger","validation","provider","network","credentials","broker","paid","paper_trade","real_money","activation"}
IMPLEMENT={"runner":"scripts/run_l_4_breadth_b84_preflight_v1.py","report_validator":"scripts/validate_l_4_breadth_b84_preflight_report_v1.py","report_schema":"schemas/l_4_breadth_b84_preflight_report_v1.schema.json","shared_preflight_library":"lib/l4_b84_preflight.py"}
def manifest():
 for line in (ROOT/'experiments/locked_gates.jsonl').read_text(encoding='utf-8').splitlines():
  row=json.loads(line)
  if row.get('gate_id')=='l_4_breadth_v4':return {k:row.get(k) for k in ('gate_id','artifact_path','artifact_sha256','validator_path','validator_sha256')}
 return None
def validate(path:Path=GATE)->dict:
 try:p=json.loads(path.read_text(encoding='utf-8'))
 except Exception as exc:return {'status':'blocked','blockers':[type(exc).__name__]}
 b=[]; top={'schema_version','order_id','gate_id','activation_for_gate_id','hypothesis_id','status','evidence_ceiling','edge_claim','source_binding','future_falsification_only_contract','implementation','authorizations','attestation','hard_stops'}
 if set(p)!=top:b.append('top_shape')
 if {k:p.get(k) for k in ('schema_version','order_id','gate_id','activation_for_gate_id','hypothesis_id','status','evidence_ceiling','edge_claim')}!={'schema_version':'lily_l4_b84_activation_contract_v1','order_id':'B8.4','gate_id':'l_4_breadth_b84_activation_contract_v1','activation_for_gate_id':'l_4_breadth_v4','hypothesis_id':'L-4','status':'locked_E0_synthetic_only_future_falsification_preflight','evidence_ceiling':'E0','edge_claim':'none'}:b.append('identity')
 source=p.get('source_binding',{}).get('v4',{}); expected=manifest()
 if not isinstance(source,dict) or source.get('manifest_identity')!=expected or not (ROOT/source.get('path','')).is_file() or file_sha256(ROOT/source.get('path',''))!=source.get('sha256') or not (ROOT/source.get('validator_path','')).is_file() or file_sha256(ROOT/source.get('validator_path',''))!=source.get('validator_sha256'):b.append('v4_source_or_manifest')
 contract=p.get('future_falsification_only_contract',{}); text=str(contract)
 if not all(term in text for term in ('Before any return decoding or parsing','<= 2015-12-31','date ambiguity','schema ambiguity','path ambiguity','hash ambiguity','membership ambiguity','2016-01-04','2026-06-30','B8.5')):b.append('preflight_contract')
 impl=p.get('implementation',{})
 if set(impl)!=set(IMPLEMENT)|{'synthetic_fixture'}:b.append('implementation_shape')
 else:
  for name,relative in IMPLEMENT.items():
   row=impl.get(name,{});ok=isinstance(row,dict) and set(row)=={'path','sha256'} and row.get('path')==relative and file_sha256(ROOT/relative)==row.get('sha256')
   if not ok:b.append('implementation:'+name)
  fixture=impl.get('synthetic_fixture',{});fixture_path=ROOT/'tests/fixtures/l4_b84/synthetic_preflight_report.json'
  try: fixture_payload=json.loads(fixture_path.read_text(encoding='utf-8'))
  except (OSError,json.JSONDecodeError): fixture_payload=None
  if not isinstance(fixture,dict) or fixture!={'path':'tests/fixtures/l4_b84/synthetic_preflight_report.json','canonical_payload_sha256':canonical_fixture_sha256(fixture_payload)}:b.append('implementation:synthetic_fixture')
 if not isinstance(p.get('authorizations'),dict) or set(p['authorizations'])!=AUTH or any(v is not False for v in p['authorizations'].values()):b.append('authorizations')
 if p.get('attestation')!={'real_container_discovery_read_hash_scan_count':0,'return_decode_parse_count':0,'market_observation_count':0,'execution_decision_ledger_count':0,'validation_status':'sealed_not_accessed'}:b.append('attestation')
 return {'status':'pass' if not b else 'blocked','blockers':sorted(set(b))}
if __name__=='__main__':
 r=validate();print(json.dumps(r));raise SystemExit(r['status']!='pass')
