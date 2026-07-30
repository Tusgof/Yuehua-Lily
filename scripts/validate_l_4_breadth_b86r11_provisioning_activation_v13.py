"""Validate the B8.6R11A activation checkpoint without execution."""
from __future__ import annotations
import hashlib, json, subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GATE = "experiments/l_4_breadth_b86r11_provisioning_gate_v13.json"
ACTIVATION = "experiments/activation_records/l_4_breadth_b86r11_provisioning_activation_v13.json"
ACCEPTED = "4387081407b92f50df6003f9435b19b885135daf"
CI_RUN = 30523998233
SEAL = {"status":"sealed_not_accessed","accessed":False}
KEYS = {"schema_version","gate_id","gate_sha256","accepted_gate_head_sha","hermetic_ci_head_sha","hermetic_ci_run_id","inspector_decision","owner_authorization_reference","scope","validation_seal"}
def canonical(value): return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("ascii")
def activation_ok(raw, value, gate, accepted_gate):
    return raw == canonical(value) and set(value) == KEYS and value == {"schema_version":"lily_l4_breadth_b86r11_provisioning_activation_v13","gate_id":"l_4_breadth_b86r11_provisioning_gate_v13","gate_sha256":hashlib.sha256(gate).hexdigest(),"accepted_gate_head_sha":ACCEPTED,"hermetic_ci_head_sha":ACCEPTED,"hermetic_ci_run_id":CI_RUN,"inspector_decision":"ACCEPTED","owner_authorization_reference":"B8.6R11 one-shot owner authorization","scope":"one_repo_relative_falsification_container_provisioning_only","validation_seal":SEAL} and accepted_gate == gate
def validate(root=ROOT):
    try:
        raw = (Path(root) / ACTIVATION).read_bytes(); value = json.loads(raw.decode("ascii")); gate = (Path(root) / GATE).read_bytes()
        accepted_gate = subprocess.run(["git","show",f"{ACCEPTED}:{GATE}"], cwd=root, capture_output=True, check=False).stdout
        ok = activation_ok(raw, value, gate, accepted_gate)
    except Exception: ok = False
    return {"status":"pass" if ok else "blocked"}
if __name__ == "__main__":
    result = validate(); print(json.dumps(result)); raise SystemExit(result["status"] != "pass")
