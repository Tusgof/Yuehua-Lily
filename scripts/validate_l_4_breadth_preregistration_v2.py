"""Fail-closed, byte-locked validator for the B8.1 L-4 breadth contract."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
GATE = PROJECT_ROOT / "experiments/l_4_breadth_preregistration_v2.json"
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from lib.statistics import paired_mean_minimum_observations
EXPECTED_GATE_SHA256 = "5eeb602cdf06e0cb1dfcda1e535d023cc3a125458ed32d811559b7fbd0d710b1"
V1_GATE_SHA256 = "52b7333118cfcd77bd423ae3ca87dd1bdff0c24e1de1a19dbe3066016af97bd6"
V1_VALIDATOR_SHA256 = "5a43551741abc6d92e0ec7f68ba08c6901ae85565dd4199cc510bc4ce232cb20"
SNAPSHOTS = [
    ("wiki/concepts/global-trend-regime-diversification.md", "6f1bf76c6730f1dfdde19809608f6533e7bf371830f58c132c3f47870ab4f0fb"),
    ("wiki/concepts/covariance-and-correlation.md", "27e28cb04ac1939acc6f4a1fc59e0a8208d365ee3e59872ffea9e4bb934c8828"),
    ("wiki/concepts/minimum-track-record-length.md", "ca65225740673bd363be7461b8022281da08ae32e6ff42f8887f1072eb51ad81"),
    ("wiki/concepts/newey-west-validation.md", "355b37f5f64d938d254337663b5df635ce008e47f8197eac041c03790643fcc5"),
    ("wiki/concepts/deflated-sharpe-ratio.md", "90663b67e49dcec90bd641e801f9464e593ff8fe9091b2d70e9f4645381af556"),
    ("wiki/concepts/backtest-validation-protocol.md", "c7f843310706d902120651e677429e66cbde9ce96ee526544de5419ee99aefa0"),
]

SCHEMA: dict[str, Any] = {
    "schema_version": str, "order_id": str, "gate_id": str, "supersedes_gate_id": str, "hypothesis_id": str, "status": str, "evidence_ceiling": str, "edge_claim": str, "owner_authorization": str,
    "source_binding": {"v1_predecessor": {"gate_path": str, "gate_sha256": str, "validator_path": str, "validator_sha256": str, "manifest_gate_id": str}, "l1_preregistration": {"path": str, "sha256": str}, "l3_preregistration": {"path": str, "sha256": str}, "b715_closure": {"path": str, "sha256": str, "commit": str, "git_blob_sha1": str}, "methodology_snapshots_root": str, "methodology_snapshot_hashes": [str]},
    "universes": {"inherited_l1_order": [str], "U1": {"members": [str], "role": str, "claim_eligible": bool}, "U4": [str], "U8": [str], "common_dates": str},
    "sizing": {"primary_raw_score": str, "primary": str, "inverse_volatility_sensitivity": str},
    "component_risk": {"covariance": str, "formula": str, "cash": str, "missingness": str},
    "macro_sleeves": {"equity": [str], "nominal_bonds": [str], "inflation_linked_bonds": [str], "gold": [str], "broad_commodities": [str]},
    "primary_metrics": {"ex_ante_hhi_delta": {"formula": str, "useful_threshold": float, "planning_sd": float, "planning_effect": float}, "realized_hhi_delta": {"formula": str, "useful_threshold": float, "planning_sd": float, "planning_effect": float, "missingness": str}, "top_dependency_delta": {"formula": str, "useful_threshold": float, "planning_sd": float, "planning_effect": float, "ties": str}, "n_eff_delta": {"formula": str, "useful_threshold": float, "planning_sd": float, "planning_effect": float, "diagnostic": str, "missingness": str}},
    "robustness": {"best_market": {"selection": str, "recalculation": str, "threshold": float, "retained_fraction": float, "failure": str}, "best_trend_episode": {"episode_rule": str, "selection": str, "recalculation": str, "threshold": float, "retained_fraction": float, "minimum_sample": str}},
    "side_effects": {"turnover_intensity": str, "cost_intensity": str, "relative_increase": str, "maximum_relative_increase": float, "cap_cash_scale_down": str, "maximum_frequency_delta_percentage_points": float},
    "statistics": {"one_sided_alpha": float, "power": float, "lags_1_to_5": [float], "inflation": float, "planning_mintrl": {"ex_ante_hhi_delta": int, "realized_hhi_delta": int, "top_dependency_delta": int, "n_eff_delta": int}, "actual_recalculation": str},
    "regime_matrix": {"global_state": str, "volatility": str, "equity_synchronization": [str], "major_subperiods": [{"start": str, "end": str}], "crisis_windows": str, "breakdowns": [str], "no_pooling": str},
    "timing_and_decisions": {"falsification_end": str, "validation_start": str, "validation_end": str, "validation_opened": bool, "pooling": bool, "scope_restricted": str, "falsified_E1_only": str, "not_falsified_not_validated_E1": str, "validation_candidate_future_only": str, "equality": str},
    "static_capacity": {"maximum_weekly_slots": int, "observation_unit": str},
    "authorizations": {"data": bool, "container": bool, "market": bool, "return": bool, "signal": bool, "position": bool, "covariance": bool, "regime": bool, "cost": bool, "pnl": bool, "validation": bool, "provider": bool, "network": bool, "credentials": bool, "broker": bool, "paid": bool, "paper_trade": bool, "real_money": bool, "activation": bool, "execution": bool, "report": bool, "research_decision": bool},
    "hard_stops": [str],
}


def validate_gate(gate_path: Path = GATE, *, project_root: Path = PROJECT_ROOT) -> dict[str, Any]:
    blockers: list[str] = []
    try:
        raw = gate_path.read_bytes()
        gate = json.loads(raw)
    except (OSError, json.JSONDecodeError) as exc:
        return _result([f"gate_unreadable:{exc.__class__.__name__}"])
    _closed_world(gate, SCHEMA, "gate", blockers)
    if hashlib.sha256(raw).hexdigest() != EXPECTED_GATE_SHA256:
        blockers.append("gate_bytes_or_semantics_mismatch")
    _binding(gate, project_root, blockers)
    _semantic_assertions(gate, blockers)
    return _result(blockers)


def _closed_world(value: Any, shape: Any, label: str, blockers: list[str]) -> None:
    if isinstance(shape, dict):
        if not isinstance(value, dict):
            blockers.append(f"{label}_not_object")
            return
        for key in sorted(set(value) - set(shape)):
            blockers.append(f"unknown_{label}_field:{key}")
        for key in sorted(set(shape) - set(value)):
            blockers.append(f"missing_{label}_field:{key}")
        for key, nested in shape.items():
            if key in value:
                _closed_world(value[key], nested, f"{label}.{key}", blockers)
    elif isinstance(shape, list):
        if not isinstance(value, list):
            blockers.append(f"{label}_not_list")
        else:
            for index, item in enumerate(value):
                _closed_world(item, shape[0], f"{label}[{index}]", blockers)
    elif not isinstance(value, shape) or (shape is int and isinstance(value, bool)):
        blockers.append(f"{label}_wrong_type")


def _binding(gate: dict[str, Any], root: Path, blockers: list[str]) -> None:
    binding = gate.get("source_binding", {})
    expected = {
        "v1_predecessor": {"gate_path": "experiments/l_4_breadth_preregistration_v1.json", "gate_sha256": V1_GATE_SHA256, "validator_path": "scripts/validate_l_4_breadth_preregistration_v1.py", "validator_sha256": V1_VALIDATOR_SHA256, "manifest_gate_id": "l_4_breadth_v1"},
        "l1_preregistration": {"path": "experiments/l_1_baseline_preregistration.json", "sha256": "91527c2f4ec00134767df86849f36b9876b00eb44cd56dc01650d33bf938fe29"},
        "l3_preregistration": {"path": "experiments/l_3_inverse_volatility_sizing_preregistration_v2.json", "sha256": "83a68792614ee0def3ddb96349d6d95c7f0aeb0ac8b1c984c1e3d29ed74e709e"},
        "b715_closure": {"path": "research_log/010-lily-l3-corrected-rerun.md", "sha256": "4ab215690aefbab3e30434326ee9554d280f353363803c73e552317eb62d939d", "commit": "62557cc7d02f81fafbed57ef7bcd8cc836193fe1", "git_blob_sha1": "978483b9daefe9e5c93933aaee476b6ff6e2cbec"},
        "methodology_snapshots_root": "methodology_snapshots/l4_breadth_v1", "methodology_snapshot_hashes": [digest for _, digest in SNAPSHOTS],
    }
    if binding != expected:
        blockers.append("source_declarations_mismatch")
        return
    for item in (expected["v1_predecessor"], expected["l1_preregistration"], expected["l3_preregistration"], expected["b715_closure"]):
        path = item.get("gate_path", item.get("path"))
        digest = item.get("gate_sha256", item.get("sha256"))
        if _sha256(root / str(path)) != digest:
            blockers.append(f"source_hash_mismatch:{path}")
    for relative, digest in SNAPSHOTS:
        if _sha256(root / "methodology_snapshots/l4_breadth_v1" / relative) != digest:
            blockers.append(f"snapshot_hash_mismatch:{relative}")
    commit = expected["b715_closure"]["commit"]
    path = expected["b715_closure"]["path"]
    completed = subprocess.run(["git", "rev-parse", f"{commit}:{path}"], cwd=root, text=True, capture_output=True, check=False)
    if completed.returncode != 0 or completed.stdout.strip() != expected["b715_closure"]["git_blob_sha1"]:
        blockers.append("b715_closure_commit_blob_mismatch")
    try:
        rows = [json.loads(line) for line in (root / "experiments/locked_gates.jsonl").read_text(encoding="utf-8").splitlines() if line]
    except (OSError, json.JSONDecodeError):
        blockers.append("v1_manifest_unreadable")
        return
    v1 = [row for row in rows if row.get("gate_id") == "l_4_breadth_v1"]
    if len(v1) != 1 or v1[0].get("artifact_sha256") != V1_GATE_SHA256 or v1[0].get("validator_sha256") != V1_VALIDATOR_SHA256:
        blockers.append("v1_manifest_identity_mismatch")


def _semantic_assertions(gate: dict[str, Any], blockers: list[str]) -> None:
    if gate.get("universes", {}).get("U1", {}).get("role") != "descriptive_only" or gate.get("sizing", {}).get("primary_raw_score") != "q[i,t]":
        blockers.append("u1_or_q_primary_mismatch")
    if gate.get("universes", {}).get("U4") != ["VTI", "IEF", "GLD", "DBC"] or gate.get("universes", {}).get("U8") != ["VTI", "VGK", "EWJ", "VWO", "IEF", "TIP", "GLD", "DBC"]:
        blockers.append("universe_mismatch")
    if gate.get("statistics", {}).get("planning_mintrl") != {"ex_ante_hhi_delta": 49, "realized_hhi_delta": 49, "top_dependency_delta": 49, "n_eff_delta": 49}:
        blockers.append("per_metric_mintrl_mismatch")
    mintrl = paired_mean_minimum_observations(alternative_mean=0.0, null_mean=0.05, planning_standard_deviation=0.1, autocorrelations=[0.25, 0.125, 0.0625, 0.03125, 0.015625], significance=0.05, power=0.8)
    if mintrl != 49:
        blockers.append("planning_mintrl_recomputation_mismatch")
    if gate.get("timing_and_decisions", {}).get("validation_opened") is not False or gate.get("timing_and_decisions", {}).get("pooling") is not False:
        blockers.append("validation_or_pooling_opened")
    if any(value is not False for value in gate.get("authorizations", {}).values()):
        blockers.append("authorizations_not_all_false")


def _sha256(path: Path) -> str | None:
    try:
        return hashlib.sha256(path.read_bytes()).hexdigest()
    except OSError:
        return None


def _result(blockers: list[str]) -> dict[str, Any]:
    return {"status": "pass" if not blockers else "blocked", "blockers": blockers, "gate_path": "experiments/l_4_breadth_preregistration_v2.json"}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--gate", type=Path, default=GATE)
    args = parser.parse_args()
    result = validate_gate(args.gate)
    print(json.dumps(result, indent=2, sort_keys=True))
    raise SystemExit(0 if result["status"] == "pass" else 1)
