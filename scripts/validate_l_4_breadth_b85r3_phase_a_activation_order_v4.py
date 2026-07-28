"""Fail-closed B8.5R3/v4 gate validator."""
from __future__ import annotations
import hashlib, json, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path: sys.path.insert(0,str(ROOT))
from lib.l4_b85r3_structural_scanner_v4 import MAX_BYTES, canonical_payload_capacity_bytes
GATE=ROOT/"experiments/l_4_breadth_b85r3_phase_a_activation_order_v4.json"
PATHS={"scanner":"lib/l4_b85r3_structural_scanner_v4.py","runner":"scripts/run_l_4_breadth_b85r3_phase_b_preflight_v4.py","report_schema":"schemas/l_4_breadth_b85r3_structural_preflight_report_v4.schema.json","activation_schema":"schemas/l_4_breadth_b85r3_phase_b_activation_v4.schema.json","report_validator":"scripts/validate_l_4_breadth_b85r3_structural_preflight_report_v4.py","synthetic_manifest":"tests/fixtures/l4_b85r3/structural_manifest_v4.json","synthetic_payload":"tests/fixtures/l4_b85r3/u8_symbol_session_dates_v4.json"}
AUTH={"data","container","path_inspection","environment","market","return","value","signal","position","covariance","regime","cost","pnl","execution","report_decision","ledger","validation","provider","network","credentials","broker","paid","paper_trade","real_money"}
def sha(path:Path)->str|None:
 try:
  with path.open("rb") as handle: raw=handle.read(MAX_BYTES+1)
  return hashlib.sha256(raw).hexdigest() if len(raw)<=MAX_BYTES else None
 except OSError:return None
def validate(path:Path=GATE)->dict:
 try: gate=json.loads(path.read_text(encoding="utf-8"))
 except Exception as exc:return {"status":"blocked","blockers":[type(exc).__name__]}
 blockers=[]; identity={"schema_version":"lily_l4_b85r3_phase_a_activation_order_v4","order_id":"B8.5R3","phase":"A","gate_id":"l_4_breadth_b85r3_phase_a_activation_order_v4","supersedes_gate_id":"l_4_breadth_b85r2_phase_a_activation_order_v3","hypothesis_id":"L-4","status":"published_E0_phase_a_remediation_awaiting_inspector_acceptance_and_activation","evidence_ceiling":"E0","edge_claim":"none"}
 if any(gate.get(k)!=v for k,v in identity.items()): blockers.append("identity")
 if gate.get("source_binding",{}).get("rejected_v3",{}).get("rejection","").count("Inspector-required")!=1: blockers.append("rejected_v3")
 for name,relative in PATHS.items():
  row=gate.get("implementation",{}).get(name,{})
  if row.get("path")!=relative or row.get("sha256")!=sha(ROOT/relative): blockers.append("implementation:"+name)
 contract=gate.get("future_phase_b_contract",{})
 if contract.get("max_payload_bytes")!=MAX_BYTES or contract.get("max_payload_bytes")!=canonical_payload_capacity_bytes() or contract.get("max_session_dates_per_symbol")!=4096 or contract.get("repo_relative_activation_record_path")!="experiments/activation_records/l_4_breadth_b85r3_phase_b_activation_v4.json" or "Acceptance record must validate before atomic marker creation" not in contract.get("one_shot_rule",""): blockers.append("capacity_or_activation_contract")
 authorizations=gate.get("phase_a_authorizations",{})
 if set(authorizations)!=AUTH or any(value is not False for value in authorizations.values()): blockers.append("authorizations")
 if any(value!=0 for value in gate.get("phase_a_access_counts",{}).values()) or gate.get("validation_seal")!={"status":"sealed_not_accessed","accessed":False}: blockers.append("seals")
 return {"status":"pass" if not blockers else "blocked","blockers":sorted(set(blockers))}
if __name__=="__main__":
 result=validate(); print(json.dumps(result)); raise SystemExit(result["status"]!="pass")
