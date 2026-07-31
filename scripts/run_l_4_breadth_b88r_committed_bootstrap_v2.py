"""Future-only provenance bootstrap. This Phase-A build intentionally denies runtime."""
from __future__ import annotations
import json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))
from scripts.validate_l_4_breadth_b88r_phase_a_execution_contract_v2 import validate
def preflight():
 r=validate();return {'status':'blocked','reason':'canonical_activation_absent','gate_valid':r['status']=='pass','git_show_required':True,'pre_import_blob_checks_required':True,'dirty_dependency_rejected':True,'one_shot_marker_created':False,'real_accessed':False}
if __name__=='__main__':print(json.dumps(preflight(),sort_keys=True));raise SystemExit(1)
