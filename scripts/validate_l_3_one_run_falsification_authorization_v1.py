"""Fail-closed validator for the separately authorized one L-3 falsification run."""
from __future__ import annotations
import argparse, hashlib, json, sys
from pathlib import Path
from typing import Any
PROJECT_ROOT=Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path: sys.path.insert(0,str(PROJECT_ROOT))
from lib.io import relative_to_root
GATE=PROJECT_ROOT/'experiments/l_3_one_run_falsification_authorization_v1.json'
EXPECTED={
'b7_1':('experiments/l_3_falsification_activation_preflight_v1.json','b27827ba15b2f7cbd89d10f771da1639d26d54087195ad275df4a72cf39ab5c3'),
'l3_v2':('experiments/l_3_inverse_volatility_sizing_preregistration_v2.json','83a68792614ee0def3ddb96349d6d95c7f0aeb0ac8b1c984c1e3d29ed74e709e'),
'l3_v1':('experiments/l_3_inverse_volatility_sizing_preregistration_v1.json','0e0aaf281c75a450bbdf1015c1f400fc7ce8a398952ea25ddbb0ba2f4557c2b0'),
'l1':('experiments/l_1_baseline_preregistration.json','91527c2f4ec00134767df86849f36b9876b00eb44cd56dc01650d33bf938fe29')}
ROOT={'schema_version':'lily_l3_one_run_falsification_authorization_v1','order_id':'B7.3','gate_id':'l_3_one_run_falsification_authorization_v1','hypothesis_id':'L-3','status':'locked_one_run_falsification_authorized','evidence_ceiling':'E1','edge_claim':'none'}
AUTH={'data_access_authorized':True,'container_inspection_authorized':True,'return_parsing_authorized':True,'execution_authorized':True,'report_decision_authorized':True,'validation_access_authorized':False,'provider_network_acquisition_authorized':False,'credentials_authorized':False,'paid_action_authorized':False,'broker_authorized':False,'paper_trade_authorized':False,'real_money_authorized':False}
KEYS=set(ROOT)|{'owner_authorization','source_binding','approved_container','one_run','authorizations','hard_stops'}
def validate_authorization(path:Path=GATE)->dict[str,Any]:
 b=[]
 try: p=json.loads(path.read_text(encoding='utf-8'))
 except Exception as e:return {'status':'blocked','blockers':[f'authorization_unreadable:{type(e).__name__}']}
 if not isinstance(p,dict): return {'status':'blocked','blockers':['authorization_not_object']}
 for k in set(p)-KEYS:b.append(f'unknown_top_level_field:{k}')
 for k in KEYS-set(p):b.append(f'missing_top_level_field:{k}')
 for k,v in ROOT.items():
  if p.get(k)!=v:b.append(f'root_mismatch:{k}')
 if p.get('authorizations')!=AUTH:b.append('authorization_drift')
 if p.get('approved_container')!={'path':'data/normalized/l1_yahoo_daily_v1.json','falsification_end':'2015-12-31','validation_start':'2016-01-04'}:b.append('container_scope_drift')
 if p.get('one_run')!={'maximum_real_return_decision_runs':1,'ledger_path':'reports/experiments/l_3_falsification_execution_ledger.jsonl','report_path':'reports/experiments/l_3_falsification_report.json'}:b.append('one_run_contract_drift')
 sb=p.get('source_binding')
 if not isinstance(sb,dict) or set(sb)!=set(EXPECTED):b.append('source_binding_shape_mismatch')
 else:
  for name,(rel,digest) in EXPECTED.items():
   if sb.get(name)!={'path':rel,'sha256':digest}:b.append(f'source_binding_declaration_mismatch:{name}')
   source=PROJECT_ROOT/rel
   if not source.is_file() or hashlib.sha256(source.read_bytes()).hexdigest()!=digest:b.append(f'source_binding_hash_mismatch:{name}')
 if not isinstance(p.get('hard_stops'),list) or len(p['hard_stops'])!=4:b.append('hard_stops_incomplete')
 return {'status':'pass' if not b else 'blocked','blockers':b,'gate_path':relative_to_root(path,PROJECT_ROOT)}
def main()->int:
 r=validate_authorization();print(json.dumps(r,indent=2,sort_keys=True));return 0 if r['status']=='pass' else 1
if __name__=='__main__':raise SystemExit(main())
