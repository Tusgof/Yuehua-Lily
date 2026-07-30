from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import scripts.run_l_4_breadth_b86r9_committed_bootstrap_v11 as bootstrap


class CommittedBootstrapTests(unittest.TestCase):
    def prepared(self):
        temporary = tempfile.TemporaryDirectory(); root = Path(temporary.name); commit = "a" * 40
        raws = {path: (path + "-committed").encode("ascii") for path in bootstrap.DEPENDENCIES}
        sources = {path: {"path": path, "sha256": hashlib.sha256(raws[path]).hexdigest()} for path in bootstrap.DEPENDENCIES if path != bootstrap.GATE}
        raws[bootstrap.GATE] = json.dumps({"gate_id": bootstrap.GATE_ID, "execution_dependencies": list(bootstrap.DEPENDENCIES), "source_binding": sources}, sort_keys=True, separators=(",", ":")).encode("ascii")
        for path, raw in raws.items():
            target = root / path; target.parent.mkdir(parents=True, exist_ok=True); target.write_bytes(raw)
        activation = {"schema_version": "lily_l4_b86r9_provisioning_activation_v11", "gate_id": bootstrap.GATE_ID, "gate_sha256": hashlib.sha256(raws[bootstrap.GATE]).hexdigest(), "accepted_gate_head_sha": "b" * 40, "hermetic_ci_head_sha": "b" * 40, "hermetic_ci_run_id": 1, "inspector_decision": "ACCEPTED", "owner_authorization_reference": "B8.6R9 one-shot owner authorization", "scope": "one_repo_relative_falsification_container_provisioning_only", "validation_seal": bootstrap.SEAL}
        raws[bootstrap.ACTIVATION] = json.dumps(activation, sort_keys=True, separators=(",", ":")).encode("ascii")
        return temporary, root, commit, raws

    def test_committed_precheck_reaches_only_injected_synthetic_executor(self):
        temporary, root, commit, raws = self.prepared()
        with temporary:
            calls = []
            saved_blob, saved_runpy = bootstrap.blob, bootstrap.runpy.run_path
            bootstrap.blob = lambda _root, candidate, path: raws.get(path) if candidate == commit else None
            bootstrap.runpy.run_path = lambda *_args, **_kwargs: {"run_one_shot": lambda **kwargs: calls.append(kwargs) or {"outcome": "synthetic_only"}}
            try:
                result = bootstrap.run(root, commit)
            finally:
                bootstrap.blob, bootstrap.runpy.run_path = saved_blob, saved_runpy
            self.assertEqual({"outcome": "synthetic_only"}, result)
            self.assertEqual(1, len(calls))

    def test_dirty_scanner_or_contract_cannot_import_or_reach_executor(self):
        for path in ("lib/l4_b86r2_provisioning_scanner_v3.py", "lib/l4_b86r9_contract_v11.py"):
            temporary, root, commit, raws = self.prepared()
            with temporary:
                (root / path).write_text("raise RuntimeError('import side effect')", encoding="ascii")
                reached = []
                saved_blob, saved_runpy = bootstrap.blob, bootstrap.runpy.run_path
                bootstrap.blob = lambda _root, candidate, item: raws.get(item) if candidate == commit else None
                bootstrap.runpy.run_path = lambda *_args, **_kwargs: reached.append(True)
                try:
                    result = bootstrap.run(root, commit)
                finally:
                    bootstrap.blob, bootstrap.runpy.run_path = saved_blob, saved_runpy
                self.assertEqual({"outcome": "refused_execution_provenance", "dataset_read_count": 0}, result)
                self.assertEqual([], reached)

    def test_direct_worktree_cli_refuses_before_runtime_import(self):
        root = Path(__file__).resolve().parents[1]
        result = subprocess.run([sys.executable, str(root / bootstrap.RUNTIME), "--execute-one-shot"], capture_output=True, check=False)
        self.assertEqual(2, result.returncode)
        result = subprocess.run([sys.executable, str(root / "scripts/run_l_4_breadth_b86r9_committed_bootstrap_v11.py")], capture_output=True, check=False)
        self.assertEqual(2, result.returncode)


if __name__ == "__main__":
    unittest.main()
