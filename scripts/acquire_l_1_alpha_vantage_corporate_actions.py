from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from lib.alpha_vantage_corporate_actions import AcquisitionBlocked, acquire_corporate_actions
from lib.environment import require_configured_path
from lib.io import load_json, write_json
from lib.provenance import file_sha256
from scripts.validate_l_1_alpha_vantage_corporate_actions_acquisition import validate_contract


CONTRACT = PROJECT_ROOT / "experiments" / "l_1_alpha_vantage_corporate_actions_acquisition.json"
EXPECTED_CONTRACT_SHA256 = "562e06914be4e651c73017009f51c26cab83cb4ff6bb26d1c28c2be32c441c96"


def main() -> int:
    parser = argparse.ArgumentParser(description="Execute the locked Lily B4.4 acquisition only.")
    parser.add_argument("--data-root", type=Path)
    args = parser.parse_args()
    if file_sha256(CONTRACT) != EXPECTED_CONTRACT_SHA256:
        print(json.dumps({"status": "blocked", "blocker": "locked_contract_hash_mismatch"}))
        return 1
    contract_validation = validate_contract(CONTRACT)
    if contract_validation["status"] != "pass":
        print(json.dumps({"status": "blocked", "blocker": "locked_contract_invalid"}))
        return 1
    data_root = args.data_root.resolve() if args.data_root else require_configured_path("LILY_DATA_ROOT")
    key_name = load_json(CONTRACT)["source"]["key_environment_name"]
    credential = os.environ.get(key_name, "")
    if not credential:
        print(json.dumps({"status": "blocked", "blocker": f"missing_environment:{key_name}"}))
        return 1
    try:
        result = acquire_corporate_actions(
            load_json(CONTRACT), data_root=data_root, credential=credential
        )
    except AcquisitionBlocked as exc:
        print(json.dumps({"status": "blocked", "blocker": str(exc)}, sort_keys=True))
        return 1
    summary_path = data_root / "derived" / "l_1_alpha_vantage_corporate_actions_b4_4_summary.json"
    write_json(summary_path, result)
    print(json.dumps({"status": "pass", **result}, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
