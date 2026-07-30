"""Validate the hash-bound B8.6R11/v13 gate without data access."""
from __future__ import annotations
import hashlib, json
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
GATE = ROOT / "experiments/l_4_breadth_b86r11_provisioning_gate_v13.json"
def validate():
    try:
        value = json.loads(GATE.read_text("ascii")); dependencies = value["execution_dependencies"]
        expected = {path:{"path":path,"sha256":hashlib.sha256((ROOT / path).read_bytes()).hexdigest()} for path in dependencies if path != GATE.relative_to(ROOT).as_posix()}
        sources = value["source_binding"]
        ok = value["gate_id"] == "l_4_breadth_b86r11_provisioning_gate_v13" and value["supersedes_gate_id"] == "l_4_breadth_b86r10_provisioning_gate_v12" and value["execution_binding"] == expected and set(sources) == {"active_l4_v4", "consumed_b85r5_result", "superseded_v12"} and all(hashlib.sha256((ROOT / source["path"]).read_bytes()).hexdigest() == source["sha256"] for source in sources.values())
    except Exception: ok = False
    return {"status":"pass" if ok else "blocked"}
if __name__ == "__main__":
    result = validate(); print(json.dumps(result)); raise SystemExit(result["status"] != "pass")
