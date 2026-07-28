"""Validate only B7.12 E0 synthetic closed-world report payloads."""
from __future__ import annotations
import argparse, hashlib, json, sys
from pathlib import Path
from typing import Any
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))
from lib.l3_corrected_rerun_v8 import derive
TOP={"schema_version","order_id","hypothesis_id","report_mode","decision","evidence_tier","edge_claim","weekly_observations","closed_world_observations_sha256","synthetic_expected_classification","validation_seal"}
IDENTITY={"schema_version":"lily_l3_corrected_rerun_report_v8","order_id":"B7.12","hypothesis_id":"L-3","report_mode":"synthetic_evaluation","decision":"not_run","evidence_tier":"E0","edge_claim":"none"}
def observation_hash(observations:Any)->str:return hashlib.sha256(json.dumps(observations,sort_keys=True,separators=(',',':')).encode()).hexdigest()
def validate(payload:Any)->dict[str,Any]:
 if not isinstance(payload,dict):return {"status":"blocked","blockers":["report_not_object"]}
 blockers=[]
 if set(payload)!=TOP:blockers.append("top_shape")
 if any(payload.get(key)!=value for key,value in IDENTITY.items()):blockers.append("e0_only_identity_matrix")
 if payload.get("closed_world_observations_sha256")!=observation_hash(payload.get("weekly_observations")):blockers.append("closed_world_observation_identity")
 if payload.get("validation_seal")!={"status":"sealed_not_accessed","accessed":False}:blockers.append("validation_seal_broken")
 if payload.get("synthetic_expected_classification") not in {None,"non_authoritative_synthetic_only"}:blockers.append("synthetic_expected_classification")
 derived,errors=derive(payload.get("weekly_observations"));blockers.extend(errors)
 return {"status":"pass" if not blockers else "blocked","blockers":sorted(set(blockers)),"derived":derived if not blockers else None}
def main()->int:
 parser=argparse.ArgumentParser(description="Validate B7.12 E0 synthetic observations only.");parser.add_argument("report",type=Path);args=parser.parse_args()
 try:payload=json.loads(args.report.read_text(encoding="utf-8"))
 except Exception as exc:print(json.dumps({"status":"blocked","blockers":[f"unreadable:{type(exc).__name__}"]}));return 1
 result=validate(payload);print(json.dumps(result,sort_keys=True));return result["status"]!="pass"
if __name__=="__main__":raise SystemExit(main())
