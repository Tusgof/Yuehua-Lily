"""Closed-world validation for synthetic B8.8 reports; never opens market data."""
from __future__ import annotations
import json, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path: sys.path.insert(0,str(ROOT))
from lib.l4_b88_scientific_contract_v1 import AUTHORIZATIONS, METRICS, SEAL, classify_e1
from scripts.validate_l_4_breadth_b88_phase_a_execution_contract_v1 import GATE, sha, validate as validate_gate
def validate(path: Path)->dict:
 blockers=[]
 try: report=json.loads(path.read_text("ascii")); gate=json.loads(GATE.read_text("ascii"))
 except Exception: return {"status":"blocked","blockers":["unreadable"]}
 required={"schema_version","order_id","hypothesis_id","mode","evidence_tier","edge_claim","source_binding","validation_seal","authorizations","access_counts","lifecycle","outcome","metric_statistics"}
 if set(report)!=required: blockers.append("closed_world")
 if {k:report.get(k) for k in ("schema_version","order_id","hypothesis_id","edge_claim")}!={"schema_version":"lily_l4_b88_scientific_report_v1","order_id":"B8.8","hypothesis_id":"L-4","edge_claim":"none"}: blockers.append("identity")
 if report.get("source_binding")!={"gate_path":"experiments/l_4_breadth_b88_phase_a_execution_contract_v1.json","gate_sha256":sha(GATE)}: blockers.append("source_binding")
 if report.get("validation_seal")!=SEAL or report.get("authorizations")!=AUTHORIZATIONS: blockers.append("seals")
 if report.get("mode")!="synthetic_fixture" or report.get("evidence_tier")!="E0" or report.get("outcome")!="blocked_before_activation" or report.get("metric_statistics")!={}: blockers.append("phase_a_only")
 if report.get("access_counts")!={key:0 for key in gate["phase_a_access_counts"]}: blockers.append("access_counts")
 if report.get("lifecycle")!={"activation_schema_version":gate["activation"]["schema_version"],"owner_reference":gate["activation"]["owner_reference"],"committed_bootstrap_required":True,"one_shot_required":True,"activation_present":False}: blockers.append("lifecycle")
 if validate_gate().get("status")!="pass": blockers.append("gate")
 return {"status":"pass" if not blockers else "blocked","blockers":sorted(set(blockers))}
if __name__=="__main__":
 import argparse; parser=argparse.ArgumentParser(); parser.add_argument("report",type=Path); args=parser.parse_args(); result=validate(args.report); print(json.dumps(result,sort_keys=True)); raise SystemExit(result["status"]!="pass")
