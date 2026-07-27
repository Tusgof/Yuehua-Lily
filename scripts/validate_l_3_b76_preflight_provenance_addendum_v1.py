"""Validate the B7.6 provenance correction without reopening any market container."""
from __future__ import annotations
import hashlib,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))
from lib.io import relative_to_root
ADD=ROOT/'experiments/l_3_b76_preflight_provenance_addendum_v1.json'; REPORT=ROOT/'reports/experiments/l_3_corrected_rerun_falsification_report.json'
EXPECTED={'schema_version':'lily_l3_b76_preflight_provenance_addendum_v1','order_id':'B7.7','hypothesis_id':'L-3','b76_report_path':'reports/experiments/l_3_corrected_rerun_falsification_report.json','raw_container_bytes_read_and_scanned':True,'market_return_values_decoded_or_used':False,'attempted_container_hash_status':'discarded_by_b76_exception_path_retrospectively_unavailable','b73_container_hash_contextual_lineage_only':True,'preflight_failure_cause':'schema_schema_version_implementation_mismatch','authoritative_outcome':'scope_restricted','l3_result_claim':'none','validation_status':'sealed_not_accessed'}
def validate(path:Path=ADD)->dict:
 try:p=json.loads(path.read_text(encoding='utf-8'))
 except Exception as e:return {'status':'blocked','blockers':[f'unreadable:{type(e).__name__}']}
 b=[f'unknown:{x}' for x in set(p)-set(EXPECTED)-{'b76_report_sha256'}]+[f'missing:{x}' for x in set(EXPECTED)-set(p)]
 b += [f'mismatch:{k}' for k,v in EXPECTED.items() if p.get(k)!=v]
 if p.get('b76_report_sha256')!=hashlib.sha256(REPORT.read_bytes()).hexdigest():b.append('b76_report_hash_mismatch')
 return {'status':'pass' if not b else 'blocked','blockers':sorted(b),'real_container_read_or_hash_count':0,'market_returns_read_count':0}
if __name__=='__main__':
 r=validate();print(json.dumps(r,sort_keys=True));raise SystemExit(0 if r['status']=='pass' else 1)
