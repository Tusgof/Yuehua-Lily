"""Run the single authorized B7.14 byte-hash/date-only preflight."""
from __future__ import annotations
import argparse, json, subprocess, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path: sys.path.insert(0,str(ROOT))
from lib.l3_b714_date_only_scanner_v1 import scan_date_metadata
from lib.provenance import file_sha256

GATE=ROOT/'experiments/l_3_b714_date_only_preflight_activation_v1.json'
CONTAINER=ROOT/'data/normalized/l1_yahoo_daily_v1.json'
REPORT=ROOT/'reports/experiments/l_3_b714_date_only_preflight_report_v1.json'
ATTESTATION=ROOT/'reports/experiments/l_3_b714_date_only_schedule_attestation_v1.json'

def main() -> int:
 p=argparse.ArgumentParser(); p.add_argument('--execute',action='store_true'); args=p.parse_args()
 if not args.execute: return 2
 if REPORT.exists() or ATTESTATION.exists(): return 3
 if subprocess.run([sys.executable,'scripts/validate_l_3_b714_date_only_preflight_activation_v1.py'],cwd=ROOT).returncode: return 5
 head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(); remote=subprocess.check_output(['git','rev-parse','origin/main'],cwd=ROOT,text=True).strip()
 if head!=remote or subprocess.run(['git','diff','--quiet'],cwd=ROOT).returncode: return 4
 gate=json.loads(GATE.read_text(encoding='utf-8'))
 result=scan_date_metadata(CONTAINER)
 report={'schema_version':'lily_l3_b714_date_only_preflight_report_v1','order_id':'B7.14','hypothesis_id':'L-3','outcome':result['status'],'evidence_tier':'E1','edge_claim':'none','provenance':{'active_b713_gate_id':'l_3_b714_activation_contract_v3','active_b713_gate_sha256':file_sha256(ROOT/'experiments/l_3_b714_activation_contract_v3.json'),'activation_gate_id':gate['gate_id'],'activation_gate_sha256':file_sha256(GATE),'checkpoint_git_commit':head,'storage_reference':'data/normalized/l1_yahoo_daily_v1.json','container_sha256':result['container_sha256']},'validation_seal':{'status':'sealed_not_accessed','accessed':False},'access_counters':{'raw_container_hash_count':1,'date_metadata_inspection_count':1,'market_returns_read_count':0,'return_values_decoded_count':0,'research_decision_count':0,'ledger_row_count':0},'preflight':result}
 REPORT.parent.mkdir(parents=True,exist_ok=True); REPORT.write_text(json.dumps(report,sort_keys=True,separators=(',',':'))+'\n',encoding='utf-8')
 if result['status']=='preflight_pass':
  attestation={'schema_version':'lily_l3_b714_date_only_schedule_attestation_v1','report_sha256':file_sha256(REPORT),'container_sha256':result['container_sha256'],'canonical_schedule_sha256':result['canonical_schedule_sha256'],'selected_decision_dates':result['selected_decision_dates'],'execution_dates':result['execution_dates'],'t_plus_20_dates':result['t_plus_20_dates'],'return_values_decoded_count':0,'validation_seal_status':'sealed_not_accessed'}
  ATTESTATION.write_text(json.dumps(attestation,sort_keys=True,separators=(',',':'))+'\n',encoding='utf-8')
 print(json.dumps({'outcome':result['status'],'return_values_decoded_count':0})); return 0
if __name__=='__main__': raise SystemExit(main())
