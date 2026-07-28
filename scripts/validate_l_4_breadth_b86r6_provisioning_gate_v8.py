from __future__ import annotations
import hashlib,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];PATH=ROOT/'experiments/l_4_breadth_b86r6_provisioning_gate_v8.json'
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))
from lib.io import load_json
KEYS={"schema_version","order_id","phase","gate_id","supersedes_gate_id","hypothesis_id","evidence_ceiling","edge_claim","source_binding","activation_path","dataset_path","expected_dataset_sha256","marker_path","report_path","manifest_path","payload_path","execution_flag","lifecycle","blocker_matrix","validation_seal","authorizations","access_counts"}
def validate():
 try:
  value=load_json(PATH);sources=value['source_binding'];ok=set(value)==KEYS and value['gate_id']=='l_4_breadth_b86r6_provisioning_gate_v8' and value['supersedes_gate_id']=='l_4_breadth_b86r5_provisioning_gate_v7' and value['schema_version']=='lily_l4_b86r6_provisioning_gate_v8' and value['execution_flag']=='--execute-one-shot' and value['expected_dataset_sha256']=='6608c0ef88f4b7edaef7523738d7a172215aa4f97c8c403adeba884d6582a4dd' and value['validation_seal']=={'status':'sealed_not_accessed','accessed':False} and not any(value['authorizations'].values()) and value['access_counts']=={'dataset':0,'return_value':0,'validation':0} and isinstance(sources,dict) and len(sources)>=10 and all(set(row)=={'path','sha256'} and hashlib.sha256((ROOT/row['path']).read_bytes()).hexdigest()==row['sha256'] for row in sources.values())
 except Exception:ok=False
 return {'status':'pass' if ok else 'blocked'}
if __name__=='__main__':
 result=validate();print(json.dumps(result));raise SystemExit(result['status']!='pass')
