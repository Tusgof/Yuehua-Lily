"""Validate the B7.6 no-return hard-stop report without reopening the container."""
from __future__ import annotations
import argparse,hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
import sys
if str(ROOT) not in sys.path: sys.path.insert(0,str(ROOT))
from lib.io import relative_to_root
REPORT=ROOT/'reports/experiments/l_3_corrected_rerun_falsification_report.json'
ACTIVATION=ROOT/'experiments/l_3_corrected_rerun_activation_v1.json'
REQUIRED={'schema_version','order_id','hypothesis_id','rerun_id','evidence_tier','edge_claim','producing_git_commit','activation_sha256','container_sha256','schedule_attestation_sha256','validation_seal','report_mode','decision','market_returns_read','preflight_failure','pre_return_schedule_attestation','observation_counts','primary_statistics','realized_confirmation','side_effects','regimes','mechanism_autopsy','claim_limits'}
def validate(path:Path=REPORT)->dict:
 try:r=json.loads(path.read_text(encoding='utf-8'))
 except Exception as e:return {'status':'blocked','blockers':[f'report_unreadable:{type(e).__name__}']}
 required={'schema_version':'lily_l3_corrected_rerun_falsification_report_v1','order_id':'B7.6','hypothesis_id':'L-3','rerun_id':'L-3-B7.5-CORRECTED-RERUN-ONE','evidence_tier':'E1','edge_claim':'none','report_mode':'preflight_failure','decision':'scope_restricted','market_returns_read':False,'container_sha256':None,'schedule_attestation_sha256':None,'pre_return_schedule_attestation':None,'observation_counts':None,'primary_statistics':None,'realized_confirmation':None,'side_effects':None,'mechanism_autopsy':None}
 b=[f'unknown_field:{k}' for k in sorted(set(r)-REQUIRED)]+[f'missing_field:{k}' for k in sorted(REQUIRED-set(r))]
 b += [f'mismatch:{k}' for k,v in required.items() if r.get(k)!=v]
 if r.get('activation_sha256')!=hashlib.sha256(ACTIVATION.read_bytes()).hexdigest():b.append('activation_hash_mismatch')
 if not isinstance(r.get('producing_git_commit'),str) or len(r['producing_git_commit'])!=40:b.append('producing_commit_mismatch')
 if r.get('preflight_failure')!='date_only_schema_metadata_missing':b.append('preflight_reason_mismatch')
 if r.get('claim_limits')!=['E1 only','edge_claim none','validation sealed','no deployment or profitability claim']:b.append('claim_limits_mismatch')
 if r.get('validation_seal')!={'start':'2016-01-04','end':'2026-06-30','status':'sealed_not_accessed','validation_access_authorized':False}:b.append('validation_seal_mismatch')
 if r.get('regimes')!={'claims':[],'rule':'no regime pooling'}:b.append('regime_claim_mismatch')
 return {'status':'pass' if not b else 'blocked','blockers':b,'report_path':relative_to_root(path,ROOT),'market_returns_read_count':0,'fresh_real_return_decision_run_count':0,'authoritative_outcome':'scope_restricted','validation_status':'sealed_not_accessed'}
def main()->int:
 r=validate();print(json.dumps(r,indent=2,sort_keys=True));return 0 if r['status']=='pass' else 1
if __name__=='__main__':raise SystemExit(main())
