"""Recompute every accepted E1 metric from raw synthetic weekly observations."""
from __future__ import annotations
import json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))
from lib.l4_b88r_scientific_engine_v2 import AUTHORIZATIONS,METRICS,SEAL,actual_statistics,derive_weekly_observation
from scripts.validate_l_4_breadth_b88r_phase_a_execution_contract_v2 import GATE,sha,validate as gate_validate
def validate(path:Path):
 b=[]
 try:r=json.loads(path.read_text('ascii'))
 except Exception:return {'status':'blocked','blockers':['unreadable']}
 required={'schema_version','order_id','hypothesis_id','mode','evidence_tier','edge_claim','source_binding','validation_seal','authorizations','access_counts','observations','metric_statistics','constraints','robustness','side_effects','regimes','outcome','autopsy'}
 if set(r)!=required:b+=['closed_world']
 if r.get('mode')=='synthetic_fixture':
  if r.get('evidence_tier')!='E0' or r.get('outcome')!='blocked_before_activation' or r.get('observations')!=[] or r.get('metric_statistics')!={}:b+=['synthetic_mode']
 elif r.get('mode')=='future_falsification_only':
  if r.get('evidence_tier')!='E1' or r.get('outcome') not in {'scope_restricted','falsified_E1_only','not_falsified_not_validated_E1'}:b+=['mode']
  observed=[derive_weekly_observation(x) for x in r.get('observations',[])]
  if not observed or any(x is None for x in observed):b+=['observation_derivation']
  else:
   stats={m:actual_statistics([x[m] for x in observed],m) for m in METRICS}
   if any(x is None for x in stats.values()) or stats!=r.get('metric_statistics'):b+=['metric_derivation']
  if r.get('outcome')=='falsified_E1_only' and not r.get('autopsy'):b+=['autopsy']
 else:b+=['mode']
 if r.get('edge_claim')!='none' or r.get('validation_seal')!=SEAL or r.get('authorizations')!=AUTHORIZATIONS or any(r.get('access_counts',{}).values()):b+=['seals']
 if r.get('source_binding')!={'gate_path':'experiments/l_4_breadth_b88r_phase_a_execution_contract_v2.json','gate_sha256':sha(GATE)}:b+=['source']
 if gate_validate().get('status')!='pass':b+=['gate']
 return {'status':'pass' if not b else 'blocked','blockers':sorted(set(b))}
if __name__=='__main__':
 import argparse;p=argparse.ArgumentParser();p.add_argument('report',type=Path);a=p.parse_args();x=validate(a.report);print(json.dumps(x,sort_keys=True));raise SystemExit(x['status']!='pass')
