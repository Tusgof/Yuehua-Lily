"""One-shot B7.14 v2 runner; main accepts only the locked exact path."""
from __future__ import annotations
import argparse, json, subprocess, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path: sys.path.insert(0,str(ROOT))
from lib.l3_b714_date_only_scanner_v2 import scan_date_only
from lib.provenance import file_sha256
GATE=ROOT/'experiments/l_3_b714_date_only_preflight_activation_v2.json'; CONTAINER=ROOT/'data/normalized/l1_yahoo_daily_v1.json'
REPORT=ROOT/'reports/experiments/l_3_b714_date_only_preflight_report_v2.json'; ATTESTATION=ROOT/'reports/experiments/l_3_b714_date_only_schedule_attestation_v2.json'
INCIDENT=ROOT/'experiments/l_3_b714_pre_checkpoint_filesystem_metadata_incident_v1.json'
def run_once(container:Path,report:Path,attestation:Path,checkpoint:str)->int:
 result=scan_date_only(container); gate=json.loads(GATE.read_text(encoding='utf-8'))
 provenance={'active_b713_v3_sha256':file_sha256(ROOT/'experiments/l_3_b714_activation_contract_v3.json'),'activation_v2_sha256':file_sha256(GATE),'storage_reference':'data/normalized/l1_yahoo_daily_v1.json','checkpoint_git_commit':checkpoint,'incident_sha256':file_sha256(INCIDENT),'container_sha256':result.get('container_sha256')}
 payload={'schema_version':'lily_l3_b714_date_only_preflight_report_v2','order_id':'B7.14','hypothesis_id':'L-3','outcome':result['outcome'],'evidence_tier':'E1','edge_claim':'none','provenance':provenance,'validation_seal':{'status':'sealed_not_accessed','accessed':False},'pre_checkpoint_incident_counts':json.loads(INCIDENT.read_text(encoding='utf-8'))['counters'],'access_counters':result['counters'],'preflight':{'blocker':result.get('blocker')} if result['outcome']=='scope_restricted' else result['attestation']}
 report.parent.mkdir(parents=True,exist_ok=True);report.write_text(json.dumps(payload,sort_keys=True,separators=(',',':'))+'\n',encoding='utf-8')
 if result['outcome']=='preflight_pass':
  att={'schema_version':'lily_l3_b714_date_only_schedule_attestation_v2','report_sha256':file_sha256(report),'container_sha256':result['container_sha256'],'checkpoint_git_commit':checkpoint,'validation_seal':{'status':'sealed_not_accessed','accessed':False},'pre_checkpoint_incident_counts':payload['pre_checkpoint_incident_counts'],**result['attestation']}
  attestation.write_text(json.dumps(att,sort_keys=True,separators=(',',':'))+'\n',encoding='utf-8')
 return 0
def main()->int:
 parser=argparse.ArgumentParser();parser.add_argument('--execute',action='store_true');args=parser.parse_args()
 if not args.execute:return 2
 if REPORT.exists() or ATTESTATION.exists():return 3
 if subprocess.run([sys.executable,'scripts/validate_l_3_b714_date_only_preflight_activation_v2.py'],cwd=ROOT).returncode:return 5
 head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip();remote=subprocess.check_output(['git','rev-parse','origin/main'],cwd=ROOT,text=True).strip()
 if head!=remote or subprocess.run(['git','diff','--quiet'],cwd=ROOT).returncode or subprocess.run(['git','diff','--cached','--quiet'],cwd=ROOT).returncode:return 4
 return run_once(CONTAINER,REPORT,ATTESTATION,head)
if __name__=='__main__':raise SystemExit(main())
