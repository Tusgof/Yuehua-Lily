"""Stdlib-only, commit-sourced production bootstrap for B8.6R10/v12."""
from __future__ import annotations
import hashlib,json,runpy,subprocess,sys
from pathlib import Path

GATE="experiments/l_4_breadth_b86r10_provisioning_gate_v12.json"; ACTIVATION="experiments/activation_records/l_4_breadth_b86r10_provisioning_activation_v12.json"; RUNTIME="scripts/run_l_4_breadth_b86r10_provisioning_v12.py"; GATE_ID="l_4_breadth_b86r10_provisioning_gate_v12"; SEAL={"status":"sealed_not_accessed","accessed":False}
DEPENDENCIES=(GATE,"scripts/run_l_4_breadth_b86r10_committed_bootstrap_v12.py",RUNTIME,"lib/l4_b86r10_contract_v12.py","lib/l4_b86r2_provisioning_scanner_v3.py","lib/draft202012_subset.py","scripts/validate_l_4_breadth_b86r10_provisioning_gate_v12.py","scripts/validate_l_4_breadth_b86r10_provisioning_report_v12.py","schemas/l_4_breadth_b86r10_provisioning_activation_v12.schema.json","schemas/l_4_breadth_b86r10_provisioning_report_v12.schema.json","schemas/l_4_breadth_b86r10_falsification_manifest_v12.schema.json","schemas/l_4_breadth_b86r10_u8_session_dates_v12.schema.json")
def sha256(raw): return hashlib.sha256(raw).hexdigest()
def h40(value): return isinstance(value,str) and len(value)==40 and all(x in "0123456789abcdef" for x in value)
def h64(value): return isinstance(value,str) and len(value)==64 and all(x in "0123456789abcdef" for x in value)
def canonical(value): return json.dumps(value,sort_keys=True,separators=(",",":"),ensure_ascii=True).encode("ascii")
def blob(root,commit,path):
    result=subprocess.run(["git","show",f"{commit}:{path}"],cwd=root,capture_output=True,check=False)
    return result.stdout if result.returncode==0 else None
def identities(root,commit):
    if not h40(commit): return None
    output={}
    for path in DEPENDENCIES:
        try: current=(root/path).read_bytes()
        except OSError: return None
        committed=blob(root,commit,path)
        if committed is None or current!=committed: return None
        output[path]={"path":path,"sha256":sha256(current)}
    return output
def gate_ok(root,commit,current):
    raw=blob(root,commit,GATE)
    if raw is None: return None
    try: gate=json.loads(raw.decode("ascii"))
    except (UnicodeDecodeError,ValueError): return None
    expected={path:current[path] for path in DEPENDENCIES if path!=GATE}
    if gate.get("gate_id")!=GATE_ID or gate.get("execution_dependencies")!=list(DEPENDENCIES) or gate.get("execution_binding")!=expected: return None
    return raw,gate
def activation_ok(root,commit,gate_raw):
    raw=blob(root,commit,ACTIVATION)
    if raw is None: return None
    try: value=json.loads(raw.decode("ascii"))
    except (UnicodeDecodeError,ValueError): return None
    keys={"schema_version","gate_id","gate_sha256","accepted_gate_head_sha","hermetic_ci_head_sha","hermetic_ci_run_id","inspector_decision","owner_authorization_reference","scope","validation_seal"}
    accepted=value.get("accepted_gate_head_sha")
    if raw!=canonical(value) or set(value)!=keys or value.get("schema_version")!="lily_l4_b86r10_provisioning_activation_v12" or value.get("gate_id")!=GATE_ID or value.get("gate_sha256")!=sha256(gate_raw) or not h64(value.get("gate_sha256")) or not h40(accepted) or value.get("hermetic_ci_head_sha")!=accepted or not isinstance(value.get("hermetic_ci_run_id"),int) or isinstance(value.get("hermetic_ci_run_id"),bool) or value["hermetic_ci_run_id"]<=0 or value.get("inspector_decision")!="ACCEPTED" or value.get("owner_authorization_reference")!="B8.6R10 one-shot owner authorization" or value.get("scope")!="one_repo_relative_falsification_container_provisioning_only" or value.get("validation_seal")!=SEAL: return None
    ancestor=subprocess.run(["git","merge-base","--is-ancestor",accepted,commit],cwd=root,capture_output=True,check=False)
    accepted_blob=blob(root,accepted,GATE)
    if ancestor.returncode!=0 or accepted_blob!=gate_raw: return None
    return {"path":ACTIVATION,"raw_sha256":sha256(raw),"content":value,"activation_checkpoint_head":commit,"accepted_gate_blob_sha256":sha256(gate_raw)}
def run(root,commit):
    current=identities(root,commit)
    if current is None:return {"outcome":"refused_execution_provenance","dataset_read_count":0}
    gate=gate_ok(root,commit,current)
    if gate is None:return {"outcome":"refused_execution_provenance","dataset_read_count":0}
    activation=activation_ok(root,commit,gate[0])
    if activation is None:return {"outcome":"refused_activation","dataset_read_count":0}
    namespace=runpy.run_path(str(root/RUNTIME),run_name="lily_committed_after_provenance")
    return namespace["run_one_shot"](root=root,commit=commit,dependency_identities=current,activation=activation)
def main(argv):
    if len(argv)!=5 or argv[:2]!=["--committed-bootstrap","--repo-root"] or argv[3]!="--producing-commit" or Path(sys.argv[0]).name!="-":return 2
    return 0 if run(Path(argv[2]).resolve(),argv[4]).get("outcome")=="structural_provisioned" else 1
if __name__=="__main__":raise SystemExit(main(sys.argv[1:]))
