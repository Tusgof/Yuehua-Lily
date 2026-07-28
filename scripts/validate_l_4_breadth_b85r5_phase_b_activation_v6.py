"""Validate the bounded B8.5R5 Phase-B activation checkpoint without running it."""
from __future__ import annotations
import json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))
from lib.provenance import git_commit
from scripts.run_l_4_breadth_b85r5_phase_b_preflight_v6 import ACTIVATION_RECORD_RELATIVE,activation
PATH=ROOT/ACTIVATION_RECORD_RELATIVE
ACCEPTED="c8d358ee23b68e11ee02bb00eec17ee7f08128dd";RUN_ID=30384415559
def validate(path=PATH):
 try:raw=path.read_bytes();record=json.loads(raw.decode("ascii"))
 except (OSError,UnicodeDecodeError,ValueError) as exc:return {"status":"blocked","blockers":[type(exc).__name__]}
 expected={"accepted_gate_head_sha":ACCEPTED,"hermetic_ci_head_sha":ACCEPTED,"hermetic_ci_run_id":RUN_ID,"inspector_decision":"ACCEPTED","owner_authorization_reference":"B8.5R5 Phase B owner authorization","scope":"one_structural_u8_preflight_only","validation_seal":{"status":"sealed_not_accessed","accessed":False}}
 if not isinstance(record,dict) or any(record.get(k)!=v for k,v in expected.items()):return {"status":"blocked","blockers":["checkpoint_content"]}
 proof=activation(raw,activation_head=ACCEPTED); _=git_commit(ROOT)
 return {"status":"pass" if proof is not None else "blocked","blockers":[] if proof is not None else ["activation_proof"]}
if __name__=="__main__":
 result=validate();print(json.dumps(result));raise SystemExit(result["status"]!="pass")
