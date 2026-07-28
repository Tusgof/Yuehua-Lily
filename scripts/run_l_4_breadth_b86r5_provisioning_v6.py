"""Runnable but activation-gated B8.6R5 orchestration; tests inject a temporary root."""
from __future__ import annotations
import hashlib,json,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))
from lib.io import load_json
import scripts.run_l_4_breadth_b86r4_provisioning_v5 as core
GATE_RELATIVE="experiments/l_4_breadth_b86r5_provisioning_gate_v6.json";ACTIVATION_RELATIVE=Path("experiments/activation_records/l_4_breadth_b86r5_provisioning_activation_v6.json");REPORT_RELATIVE=Path("reports/experiments/l_4_breadth_b86r5_provisioning_report_v6.json");MARKER_RELATIVE=Path("reports/experiments/l_4_breadth_b86r5_provisioning_attempt_v6.json");MANIFEST_RELATIVE=Path("experiments/provisioned/l_4_breadth_b86r5_falsification_manifest_v6.json");PAYLOAD_RELATIVE=Path("experiments/provisioned/l_4_breadth_b86r5_u8_session_dates_v6.json")
def canonical(value):return core.canonical(value)
def git_blob(commit,path):
 p=subprocess.run(["git","show",f"{commit}:{path}"],cwd=ROOT,capture_output=True,check=False);return p.stdout if p.returncode==0 else None
def gate_sha(root):return hashlib.sha256((root/GATE_RELATIVE).read_bytes()).hexdigest()
def valid_activation(raw,*,head,root=ROOT,blob_loader=git_blob,gate_check=core.accepted_gate):
 try:value=json.loads(raw.decode("ascii"));sha=gate_sha(root)
 except (OSError,UnicodeDecodeError,ValueError):return None
 expected={"schema_version":"lily_l4_b86r5_provisioning_activation_v6","gate_id":"l_4_breadth_b86r5_provisioning_gate_v6","gate_sha256":sha,"hermetic_ci_head_sha":value.get("accepted_gate_head_sha"),"inspector_decision":"ACCEPTED","owner_authorization_reference":"B8.6R5 one-shot owner authorization","scope":"one_repo_relative_falsification_container_provisioning_only","validation_seal":{"status":"sealed_not_accessed","accessed":False}}
 if raw!=canonical(value) or set(value)!=set(expected)|{"accepted_gate_head_sha","hermetic_ci_run_id"} or any(value.get(k)!=v for k,v in expected.items()) or value.get("accepted_gate_head_sha")!=value.get("hermetic_ci_head_sha") or not isinstance(value.get("hermetic_ci_run_id"),int) or value["hermetic_ci_run_id"]<1 or blob_loader(head,ACTIVATION_RELATIVE.as_posix())!=raw or not gate_check(value["accepted_gate_head_sha"],head,sha):return None
 return {"path":ACTIVATION_RELATIVE.as_posix(),"raw_sha256":hashlib.sha256(raw).hexdigest(),"content":value,"activation_checkpoint_head":head}
def run_phase_b(*,root=ROOT,head=None,blob_loader=git_blob,gate_check=core.accepted_gate):
 head=head or core.git_commit(ROOT)
 try:raw=(root/ACTIVATION_RELATIVE).read_bytes()
 except OSError:return {"outcome":"refused_activation","dataset_read_count":0}
 proof=valid_activation(raw,head=head,root=root,blob_loader=blob_loader,gate_check=gate_check)
 if proof is None:return {"outcome":"refused_activation","dataset_read_count":0}
 marker=root/MARKER_RELATIVE
 if not core.claim(marker):return {"outcome":"refused_already_consumed","dataset_read_count":0}
 row=core.artifact();data,error=core.read(root/core.DATASET_RELATIVE,row)
 report=core.base("real_one_shot",row,proof) if error else core.structural(data,mode="real_one_shot",row=row,provenance=proof,output_paths=(root/MANIFEST_RELATIVE,root/PAYLOAD_RELATIVE))
 if error:report.update({"outcome":"provisioning_blocked","blocker":error})
 if report["outcome"]=="structural_provisioned":core.write_raw(root/MANIFEST_RELATIVE,canonical(report["manifest"]));core.write_raw(root/PAYLOAD_RELATIVE,canonical(report["payload"]))
 core.write_raw(root/REPORT_RELATIVE,canonical(report));return report
def main(argv):
 if argv!=["--execute-one-shot"]:return 2
 return 0 if run_phase_b().get("outcome")=="structural_provisioned" else 1
if __name__=="__main__":raise SystemExit(main(sys.argv[1:]))
