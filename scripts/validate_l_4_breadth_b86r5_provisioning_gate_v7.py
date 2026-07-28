import hashlib,json
from pathlib import Path
R=Path(__file__).resolve().parents[1];P=R/'experiments/l_4_breadth_b86r5_provisioning_gate_v7.json'
g=json.loads(P.read_text());ok=g['gate_id']=='l_4_breadth_b86r5_provisioning_gate_v7' and hashlib.sha256((R/g['runner_path']).read_bytes()).hexdigest()==g['runner_sha256'];print(json.dumps({'status':'pass' if ok else 'blocked'}));raise SystemExit(not ok)
