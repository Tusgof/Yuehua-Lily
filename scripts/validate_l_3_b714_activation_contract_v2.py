import json, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path: sys.path.insert(0,str(ROOT))
from lib.provenance import file_sha256
GATE=ROOT/'experiments/l_3_b714_activation_contract_v2.json'
def validate():
 p=json.loads(GATE.read_text()); b=[]; s=p.get('source_binding',{}); rows=[json.loads(x) for x in (ROOT/'experiments/locked_gates.jsonl').read_text().splitlines() if x]
 for key,path,digest in [('b7_13_v1','experiments/l_3_b714_activation_contract_v1.json','3c7b620aa36423f1cb94804cdffcd4454256eedb205741ad3ca44a4d2f2cbc01'),('b7_6_addendum','experiments/l_3_b76_preflight_provenance_addendum_v1.json','69eea0f80cb303872c83e32ba940f96b11d05fe9a67df3891cfd8ada59036400')]:
  x=s.get(key,{});
  if x.get('path')!=path or x.get('sha256')!=digest or file_sha256(ROOT/path)!=digest:b.append(key)
 x=s.get('b7_13_v1',{}); m=next((r for r in rows if r.get('gate_id')=='l_3_b714_activation_contract_v1'),{});
 if x.get('manifest_identity',{}).get('validator_sha256')!=m.get('validator_sha256') or m.get('artifact_sha256')!=x.get('sha256'):b.append('v1_manifest')
 x=s.get('b7_6_addendum',{});
 if x.get('validator_path')!='scripts/validate_l_3_b76_preflight_provenance_addendum_v1.py' or x.get('validator_sha256')!=file_sha256(ROOT/x.get('validator_path','')):b.append('b76_lineage')
 x=p.get('approved_synthetic_metadata',{});
 if x.get('sha256')!=file_sha256(ROOT/x.get('path','')):b.append('fixture')
 if p.get('gate_id')!='l_3_b714_activation_contract_v2' or any(p.get('authorizations',{}).values()):b.append('identity')
 return {'status':'pass' if not b else 'blocked','blockers':b}
if __name__=='__main__':
 r=validate();print(json.dumps(r));raise SystemExit(r['status']!='pass')
