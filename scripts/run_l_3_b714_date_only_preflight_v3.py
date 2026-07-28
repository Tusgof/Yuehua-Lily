"""One-shot B7.14 v3 runner; no path, provider, or environment fallback exists."""
from __future__ import annotations
import argparse,json,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))
from lib.l3_b714_date_only_scanner_v3 import scan_date_only
from lib.provenance import file_sha256
GATE=ROOT/'experiments/l_3_b714_date_only_preflight_activation_v3.json';INC=ROOT/'experiments/l_3_b714_pre_checkpoint_filesystem_metadata_incident_v1.json'
CONTAINER=ROOT/'data/normalized/l1_yahoo_daily_v1.json';REPORT=ROOT/'reports/experiments/l_3_b714_date_only_preflight_report_v3.json';ATT=ROOT/'reports/experiments/l_3_b714_date_only_schedule_attestation_v3.json'
EXPECTED='6608c0ef88f4b7edaef7523738d7a172215aa4f97c8c403adeba884d6582a4dd'
def _manifest(gate_id:str)->dict:
 return next(x for x in (json.loads(line) for line in (ROOT/'experiments/locked_gates.jsonl').read_text(encoding='utf-8').splitlines() if line) if x.get('gate_id')==gate_id)
def run_once(container:Path,report:Path,attestation:Path,checkpoint:str)->int:
 g=json.loads(GATE.read_text(encoding='utf-8'));result=scan_date_only(container,EXPECTED);att_path='reports/experiments/l_3_b714_date_only_schedule_attestation_v3.json'
 provenance={'active_b713':{'gate_id':'l_3_b714_activation_contract_v3','path':'experiments/l_3_b714_activation_contract_v3.json','sha256':file_sha256(ROOT/'experiments/l_3_b714_activation_contract_v3.json'),'manifest_row':_manifest('l_3_b714_activation_contract_v3')},'activation':{'gate_id':g['gate_id'],'path':'experiments/l_3_b714_date_only_preflight_activation_v3.json','sha256':file_sha256(GATE),'manifest_row':_manifest(g['gate_id'])},'incident':{'id':'l_3_b714_pre_checkpoint_filesystem_metadata_incident_v1','path':'experiments/l_3_b714_pre_checkpoint_filesystem_metadata_incident_v1.json','sha256':file_sha256(INC)},'checkpoint_git_commit':checkpoint,'storage_reference':'data/normalized/l1_yahoo_daily_v1.json','expected_historical_container_sha256':EXPECTED,'actual_container_sha256':result['container_sha256'],'attestation_path':None,'attestation_sha256':None}
 pre={'blocker':result.get('blocker')} if result['outcome']=='scope_restricted' else result['attestation']
 if result['outcome']=='preflight_pass':
  att={'schema_version':'lily_l3_b714_date_only_schedule_attestation_v3','order_id':'B7.14','hypothesis_id':'L-3','checkpoint_git_commit':checkpoint,'container_sha256':result['container_sha256'],'validation_seal':{'status':'sealed_not_accessed','accessed':False},'pre_checkpoint_incident_counts':json.loads(INC.read_text(encoding='utf-8'))['counters'],**result['attestation']}
  attestation.parent.mkdir(parents=True,exist_ok=True);attestation.write_text(json.dumps(att,sort_keys=True,separators=(',',':'))+'\n',encoding='utf-8');provenance['attestation_path']=att_path;provenance['attestation_sha256']=file_sha256(attestation)
 payload={'schema_version':'lily_l3_b714_date_only_preflight_report_v3','order_id':'B7.14','hypothesis_id':'L-3','outcome':result['outcome'],'evidence_tier':'E1','edge_claim':'none','provenance':provenance,'validation_seal':{'status':'sealed_not_accessed','accessed':False},'pre_checkpoint_incident_counts':json.loads(INC.read_text(encoding='utf-8'))['counters'],'access_counters':result['counters'],'preflight':pre}
 report.parent.mkdir(parents=True,exist_ok=True);report.write_text(json.dumps(payload,sort_keys=True,separators=(',',':'))+'\n',encoding='utf-8');return 0
def main()->int:
 p=argparse.ArgumentParser();p.add_argument('--execute',action='store_true');a=p.parse_args()
 if not a.execute:return 2
 if REPORT.exists() or ATT.exists():return 3
 if subprocess.run([sys.executable,'scripts/validate_l_3_b714_date_only_preflight_activation_v3.py'],cwd=ROOT).returncode:return 5
 head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip();remote=subprocess.check_output(['git','rev-parse','origin/main'],cwd=ROOT,text=True).strip()
 if head!=remote or subprocess.run(['git','diff','--quiet'],cwd=ROOT).returncode or subprocess.run(['git','diff','--cached','--quiet'],cwd=ROOT).returncode:return 4
 return run_once(CONTAINER,REPORT,ATT,head)
if __name__=='__main__':raise SystemExit(main())
