"""Fail-closed validator for the append-only B8.4R hermetic remediation gate."""
from __future__ import annotations
import json, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path: sys.path.insert(0,str(ROOT))
from lib.provenance import file_sha256
from lib.l4_b84_preflight import canonical_fixture_sha256
GATE=ROOT/'experiments/l_4_breadth_b84r_activation_contract_v2.json'
IMPLEMENT={'runner':'scripts/run_l_4_breadth_b84r_preflight_v2.py','report_validator':'scripts/validate_l_4_breadth_b84r_preflight_report_v2.py','report_schema':'schemas/l_4_breadth_b84r_preflight_report_v2.schema.json','shared_preflight_library':'lib/l4_b84_preflight.py'}
AUTH={'data','container','market','return','signal','position','covariance','regime','cost','pnl','execution','report_decision','ledger','validation','provider','network','credentials','broker','paid','paper_trade','real_money','activation'}
def validate(path:Path=GATE)->dict:
 try:p=json.loads(path.read_text(encoding='utf-8'))
 except Exception as e:return {'status':'blocked','blockers':[type(e).__name__]}
 b=[]
 if p.get('gate_id')!='l_4_breadth_b84r_activation_contract_v2' or p.get('order_id')!='B8.4R' or p.get('activation_for_gate_id')!='l_4_breadth_v4' or p.get('evidence_ceiling')!='E0' or p.get('edge_claim')!='none':b.append('identity')
 v1=p.get('source_binding',{}).get('b84_v1_failed_history',{})
 if v1.get('path')!='experiments/l_4_breadth_b84_activation_contract_v1.json' or v1.get('ci_run')!='30363935144' or 'jsonschema' not in str(v1):b.append('v1_ci_history')
 impl=p.get('implementation',{})
 for name,relative in IMPLEMENT.items():
  row=impl.get(name,{}); b.extend([] if isinstance(row,dict) and row=={'path':relative,'sha256':file_sha256(ROOT/relative)} else ['implementation:'+name])
 fixture=impl.get('synthetic_fixture',{}); fp=ROOT/'tests/fixtures/l4_b84/synthetic_preflight_report_v2.json'
 try:fixture_hash=canonical_fixture_sha256(json.loads(fp.read_text(encoding='utf-8')))
 except Exception:fixture_hash=None
 if fixture!={'path':'tests/fixtures/l4_b84/synthetic_preflight_report_v2.json','canonical_payload_sha256':fixture_hash}:b.append('fixture')
 if not isinstance(p.get('authorizations'),dict) or set(p['authorizations'])!=AUTH or any(v is not False for v in p['authorizations'].values()):b.append('authorizations')
 return {'status':'pass' if not b else 'blocked','blockers':sorted(set(b))}
if __name__=='__main__':
 r=validate();print(json.dumps(r));raise SystemExit(r['status']!='pass')
