"""Validate the transparent B7.14 pre-check filesystem-metadata incident."""
from __future__ import annotations
import json
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from lib.io import load_json
PATH=ROOT/'experiments/l_3_b714_pre_checkpoint_filesystem_metadata_incident_v1.json'
TOP={'schema_version','order_id','classification','target','command','observed_metadata','counters','research_decision_count','ledger_row_count','edge_claim','authorization'}
COUNTS={'directory_listing_count':1,'filesystem_metadata_access_count':1,'container_content_read_count':0,'container_hash_count':0,'date_metadata_inspection_count':0,'return_values_decoded_count':0,'validation_access_count':0}
def validate(path:Path=PATH)->dict:
 try: value=load_json(path)
 except (OSError,json.JSONDecodeError) as exc:return {'status':'blocked','blockers':[type(exc).__name__]}
 ok=set(value)==TOP and value.get('schema_version')=='lily_l3_b714_pre_checkpoint_filesystem_metadata_incident_v1' and value.get('order_id')=='B7.14' and value.get('classification')=='procedural_scope_incident_no_scientific_data_opened' and value.get('target')=='data/normalized/l1_yahoo_daily_v1.json' and value.get('command')=='Get-ChildItem -Force data\\normalized | Select-Object Name,Length' and value.get('observed_metadata')=={'filename_observed':True,'byte_length_observed':True,'last_write_time_observed':False} and value.get('counters')==COUNTS and value.get('research_decision_count')==0 and value.get('ledger_row_count')==0 and value.get('edge_claim')=='none' and isinstance(value.get('authorization'),str) and bool(value['authorization'])
 return {'status':'pass' if ok else 'blocked','blockers':[] if ok else ['incident_contract']}
if __name__=='__main__':
 r=validate();print(json.dumps(r));raise SystemExit(r['status']!='pass')
