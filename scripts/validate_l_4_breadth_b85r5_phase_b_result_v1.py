"""Validate the single consumed E0 Phase-B result without touching data storage."""
from __future__ import annotations
import hashlib,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))
from lib.provenance import git_commit
from scripts.validate_l_4_breadth_b85r5_structural_preflight_report_v6 import validate as validate_report
PATH=ROOT/"experiments/l_4_breadth_b85r5_phase_b_result_v1.json"
def sha(path:Path)->str|None:
 try:return hashlib.sha256(path.read_bytes()).hexdigest()
 except OSError:return None
def validate(path=PATH):
 try:result=json.loads(path.read_text(encoding="ascii"));report_path=ROOT/result["report"]["path"];report=json.loads(report_path.read_text(encoding="ascii"))
 except (OSError,UnicodeDecodeError,ValueError,KeyError) as exc:return {"status":"blocked","blockers":[type(exc).__name__]}
 expected={"schema_version":"lily_l4_b85r5_phase_b_result_v1","order_id":"B8.5R5B","hypothesis_id":"L-4","evidence_tier":"E0","edge_claim":"none","command":"python scripts/run_l_4_breadth_b85r5_phase_b_preflight_v6.py --execute-one-shot","command_exit_code":1,"real_preflight_consumed":True,"outcome":"preflight_blocked","blocker":"data_root_unavailable","access_counters":{"manifest_attempted_read_count":0,"manifest_read_count":0,"payload_attempted_read_count":0,"payload_read_count":0,"return_value_decode_count":0,"validation_access_count":0},"validation_seal":{"status":"sealed_not_accessed","accessed":False},"producing_git_commit":"b1119873c25b1ce364133496614c36226345907f","phase_b_status":"consumed_blocked_no_data_root_no_retry"}
 if not isinstance(result,dict) or any(result.get(k)!=v for k,v in expected.items()):return {"status":"blocked","blockers":["result_content"]}
 marker=ROOT/result["marker"]["path"]
 if result.get("report",{}).get("sha256")!=sha(report_path) or result.get("marker",{}).get("sha256")!=sha(marker):return {"status":"blocked","blockers":["repo_artifact_hash"]}
 if validate_report(report).get("status")!="pass" or report.get("access_counters")!={"return_value_decode_count":0,"validation_access_count":0} or any(report["artifacts"][name]["attempted_read_count"]!=0 or report["artifacts"][name]["read_count"]!=0 for name in ("manifest","payload")):return {"status":"blocked","blockers":["report_binding"]}
 _=git_commit(ROOT);return {"status":"pass","blockers":[]}
if __name__=="__main__":
 output=validate();print(json.dumps(output));raise SystemExit(output["status"]!="pass")
