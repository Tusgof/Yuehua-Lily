from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from lib.io import load_json, load_jsonl

CONTRACT = PROJECT_ROOT / "experiments" / "l_2_falsification_execution_contract.json"
MANIFEST = PROJECT_ROOT / "experiments" / "locked_gates.jsonl"
V2 = PROJECT_ROOT / "experiments" / "l_2_multi_lookback_tstat_preregistration_v2.json"
V3 = PROJECT_ROOT / "experiments" / "l_2_multi_lookback_tstat_preregistration_v3.json"
V2_SHA256 = "84a7bb45070b54846a709573506c8213a3bc62d28cfa25f4982415d40d94e1f3"
V3_SHA256 = "507bf40a0a6ac1690ff0c6898bf20dc79c3b8dee78d18251c5835e45d7b60afc"


class ExecutionBlocked(RuntimeError):
    pass


def load_execution_spec() -> dict[str, Any]:
    from scripts.validate_l_2_multi_lookback_tstat_preregistration_v2 import validate_preregistration as validate_v2
    from scripts.validate_l_2_multi_lookback_tstat_preregistration_v3 import validate_preregistration as validate_v3

    if validate_v2()["status"] != "pass" or validate_v3()["status"] != "pass":
        raise ExecutionBlocked("l2_preregistration_validator_failed")
    if _sha256(V2) != V2_SHA256 or _sha256(V3) != V3_SHA256:
        raise ExecutionBlocked("l2_preregistration_hash_mismatch")
    rows = load_jsonl(MANIFEST)
    matching = [row for row in rows if row.get("gate_id") == "l_2_multi_lookback_tstat_v3"]
    if len(matching) != 1 or matching[0].get("artifact_sha256") != V3_SHA256:
        raise ExecutionBlocked("l2_v3_manifest_gate_mismatch")
    v2, v3 = load_json(V2), load_json(V3)
    return {
        "inference_source": "v2",
        "time_index_source": "v3",
        "primary_utility_and_inference": v2["primary_utility_and_inference"],
        "search_accounting_and_DSR": v2["search_accounting_and_DSR"],
        "dual_MinTRL": v2["dual_MinTRL"],
        "falsification_decision_matrix": v2["falsification_decision_matrix"],
        "time_index_contract": v3["time_index_contract"],
        "overlay_rule": "v3 overrides only time-index wording; v2 owns every inference field.",
    }


def run_falsification() -> None:
    from scripts.validate_l_2_falsification_execution_contract import validate_contract

    if validate_contract()["status"] != "pass":
        raise ExecutionBlocked("b6_contract_invalid")
    load_execution_spec()
    raise ExecutionBlocked("b6_1_activation_gate_required")


def _sha256(path: Path) -> str | None:
    return hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else None


def main() -> int:
    parser = argparse.ArgumentParser(description="Fail-closed L-2 falsification runner; B6.1 activation is required for execution.")
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args()
    if not args.execute:
        print(json.dumps({"status": "blocked", "blocker": "explicit_execute_flag_missing"}, sort_keys=True))
        return 1
    try:
        run_falsification()
    except ExecutionBlocked as exc:
        print(json.dumps({"status": "blocked", "blocker": str(exc)}, sort_keys=True))
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
