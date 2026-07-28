"""Fail-closed validator for the append-only B8.4R2 hermetic remediation gate."""
from __future__ import annotations
import json, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path: sys.path.insert(0,str(ROOT))
from lib.l4_b84_preflight import canonical_fixture_sha256
GATE=ROOT/'experiments/l_4_breadth_b84r2_activation_contract_v3.json'
IMPLEMENT={'runner':'scripts/run_l_4_breadth_b84r2_preflight_v3.py','report_validator':'scripts/validate_l_4_breadth_b84r2_preflight_report_v3.py','report_schema':'schemas/l_4_breadth_b84r2_preflight_report_v3.schema.json','shared_preflight_library':'lib/l4_b84_preflight.py'}
AUTH={'data','container','market','return','signal','position','covariance','regime','cost','pnl','execution','report_decision','ledger','validation','provider','network','credentials','broker','paid','paper_trade','real_money','activation'}
SOURCE={'v4_active_science':{'gate_id':'l_4_breadth_v4','artifact_path':'experiments/l_4_breadth_preregistration_v4.json','artifact_sha256':'648b480aed523074e8c99646b313c70b074ca6bde95c2a30fb88a128d150ffcb','validator_path':'scripts/validate_l_4_breadth_preregistration_v4.py','validator_sha256':'78bd4553ca0145d78f2408b0a325fe630897cc717495c6a60766fd72b9a42a42'},'b84_v1_failed_history':{'path':'experiments/l_4_breadth_b84_activation_contract_v1.json','artifact_sha256':'65108e4eddc9aeaf0f8de98fe5c1e1bfe232d77e696af249655e394403974536','ci_run':'30363935144','root_cause':'clean hermetic CI lacks jsonschema; v1 import failed before report validation'},'b84r_v2_failed_history':{'path':'experiments/l_4_breadth_b84r_activation_contract_v2.json','artifact_sha256':'43bff523a204f15a81a2e355b4f4cb78613903bcbdda3d059b7287854edff9eb','ci_run':'30365332742','root_cause':'cross-platform CRLF worktree hashes differed from LF clean checkout'}}
def canonical_sha(path: Path) -> str:
 import hashlib
 return hashlib.sha256(path.read_bytes().replace(b'\r\n', b'\n')).hexdigest()
def validate(path:Path=GATE)->dict:
 try:p=json.loads(path.read_text(encoding='utf-8'))
 except Exception as e:return {'status':'blocked','blockers':[type(e).__name__]}
 b=[]
 top={'schema_version','order_id','gate_id','activation_for_gate_id','hypothesis_id','evidence_ceiling','edge_claim','source_binding','implementation','authorizations'}
 if set(p)!=top:b.append('top_shape')
 if p.get('gate_id')!='l_4_breadth_b84r2_activation_contract_v3' or p.get('order_id')!='B8.4R2' or p.get('activation_for_gate_id')!='l_4_breadth_v4' or p.get('evidence_ceiling')!='E0' or p.get('edge_claim')!='none':b.append('identity')
 if p.get('source_binding')!=SOURCE:b.append('exact_source_binding')
 impl=p.get('implementation',{})
 for name,relative in IMPLEMENT.items():
  row=impl.get(name,{}); b.extend([] if isinstance(row,dict) and row=={'path':relative,'sha256':canonical_sha(ROOT/relative)} else ['implementation:'+name])
 fixture=impl.get('synthetic_fixture',{}); fp=ROOT/'tests/fixtures/l4_b84/synthetic_preflight_report_v3.json'
 try:fixture_hash=canonical_fixture_sha256(json.loads(fp.read_text(encoding='utf-8')))
 except Exception:fixture_hash=None
 if fixture!={'path':'tests/fixtures/l4_b84/synthetic_preflight_report_v3.json','canonical_payload_sha256':fixture_hash}:b.append('fixture')
 if not isinstance(p.get('authorizations'),dict) or set(p['authorizations'])!=AUTH or any(v is not False for v in p['authorizations'].values()):b.append('authorizations')
 return {'status':'pass' if not b else 'blocked','blockers':sorted(set(b))}
if __name__=='__main__':
 r=validate();print(json.dumps(r));raise SystemExit(r['status']!='pass')
