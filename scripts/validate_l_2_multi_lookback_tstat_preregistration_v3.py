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

from lib.io import load_json, relative_to_root

DEFAULT_PREREGISTRATION = PROJECT_ROOT / "experiments" / "l_2_multi_lookback_tstat_preregistration_v3.json"
V2_PREREGISTRATION = PROJECT_ROOT / "experiments" / "l_2_multi_lookback_tstat_preregistration_v2.json"
V2_SHA256 = "84a7bb45070b54846a709573506c8213a3bc62d28cfa25f4982415d40d94e1f3"
HORIZONS = [32, 64, 126, 252]
TIME_INDEX_CONTRACT = {
    "decision_index": "t is the last actual NYSE trading session selected for rebalance, immediately after its official close.",
    "shared_signal_information_set": "Candidate and primary matched comparator both use the same available return observations r[t-k] for k=0..h-1 at decision close t, separately for every locked horizon h.",
    "future_return_prohibition": "No candidate or comparator signal, weight, volatility, covariance, cost, or decision input may use r[t+1] or any return after t.",
    "weight_index": "Both portfolios compute their target weights at decision index t from their respective signals and the identical inherited non-signal inputs available at t.",
    "execution_index": "Both portfolios execute their t-index targets at the official close of the next actual NYSE trading session t+1; same-close execution at t is forbidden.",
    "shared_portfolio_return_window": "For each decision t, candidate and primary comparator net returns use the identical effective interval beginning immediately after their shared execution close at t+1 and ending immediately before the next shared executable rebalance close; the paired active return subtracts those two identical-window net returns.",
    "holiday_rule": "If the next calendar day is not a NYSE session, t+1 means the next actual NYSE trading session; never manufacture a session.",
}
CANDIDATE_WINDOW = "At decision close t, for every horizon h use exactly r[t-k] for k=0..h-1; r[t] is the latest admissible return and r[t+1] or later is forbidden."
COMPARATOR_WINDOW = "At the same decision close t and for each same horizon h, use exactly r[t-k] for k=0..h-1; the set must equal the candidate component's set and cannot contain r[t+1] or later."


def validate_preregistration(path: Path = DEFAULT_PREREGISTRATION) -> dict[str, Any]:
    try:
        payload = load_json(path)
    except (FileNotFoundError, json.JSONDecodeError) as exc:
        return _result(path, [f"preregistration_unreadable:{exc.__class__.__name__}"])
    if not isinstance(payload, dict):
        return _result(path, ["preregistration_must_be_object"])
    blockers: list[str] = []
    for field, expected in {
        "schema_version": "lily_l2_multi_lookback_tstat_preregistration_v3",
        "hypothesis_id": "L-2",
        "status": "locked_before_execution",
        "supersedes_gate_id": "l_2_multi_lookback_tstat_v2",
        "evidence_ceiling_without_adversarial_review": "E1",
        "edge_claim_before_execution": "none",
    }.items():
        if payload.get(field) != expected:
            blockers.append(f"invalid_locked_field:{field}")
    blockers.extend(_validate_v2_lineage(payload))
    blockers.extend(_validate_pre_measurement_state(payload))
    blockers.extend(_validate_shared_indexing(payload))
    blockers.extend(_validate_primary_inference(payload))
    blockers.extend(_validate_validation_seal(payload))
    hard_stops = " ".join(payload.get("hard_stops", []))
    for phrase in ("backtest execution", "2016-01-04 through 2026-06-30", "broker or provider request", "edge, E2"):
        if phrase not in hard_stops:
            blockers.append(f"hard_stop_missing:{phrase}")
    return _result(path, blockers)


def _validate_v2_lineage(payload: dict[str, Any]) -> list[str]:
    superseded = payload.get("superseded_artifact", {})
    inherited = payload.get("inherits_v2", {})
    blockers: list[str] = []
    if superseded.get("path") != "experiments/l_2_multi_lookback_tstat_preregistration_v2.json" or inherited.get("source_path") != superseded.get("path"):
        blockers.append("superseded_v2_path_changed")
    if superseded.get("sha256") != V2_SHA256 or inherited.get("source_sha256") != V2_SHA256 or _sha256(V2_PREREGISTRATION) != V2_SHA256:
        blockers.append("superseded_v2_hash_mismatch")
    return blockers


def _validate_pre_measurement_state(payload: dict[str, Any]) -> list[str]:
    state = payload.get("pre_measurement_state")
    if not isinstance(state, dict) or not state:
        return ["pre_measurement_state_missing"]
    return [] if all(value is False for value in state.values()) else ["pre_measurement_state_must_be_all_false"]


def _validate_shared_indexing(payload: dict[str, Any]) -> list[str]:
    blockers: list[str] = []
    candidate = payload.get("candidate_signal", {})
    if candidate.get("name") != "equal_weight_multi_lookback_t_stat" or candidate.get("lookback_sessions_in_order") != HORIZONS:
        blockers.append("candidate_horizons_or_name_changed")
    if candidate.get("shared_decision_return_window") != CANDIDATE_WINDOW or "r[t-k] for k=0..h-1" not in str(candidate.get("component_formula", "")):
        blockers.append("candidate_time_window_changed")
    comparator = payload.get("comparators", {}).get("primary", {})
    if comparator.get("id") != "matched_32_64_126_252_directional_count" or comparator.get("lookback_sessions_in_order") != HORIZONS:
        blockers.append("primary_comparator_not_matched_horizon")
    component_formula = str(comparator.get("component_formula", ""))
    if comparator.get("shared_decision_return_window") != COMPARATOR_WINDOW or "r[t-k]" not in component_formula or "k=0..h-1" not in component_formula:
        blockers.append("comparator_time_window_changed")
    if payload.get("time_index_contract") != TIME_INDEX_CONTRACT:
        blockers.append("time_index_contract_changed")
    return blockers


def _validate_primary_inference(payload: dict[str, Any]) -> list[str]:
    utility = payload.get("primary_utility_and_inference", {})
    search = payload.get("search_accounting_and_DSR", {})
    blockers: list[str] = []
    if utility.get("primary_utility") != "annualized Sharpe of the paired daily net active-return series":
        blockers.append("primary_utility_definition_changed")
    if "identical shared_portfolio_return_window" not in str(utility.get("observation_unit", "")):
        blockers.append("primary_return_window_changed")
    if "same paired active-return observations" not in str(utility.get("inference_input_rule", "")):
        blockers.append("inference_input_rule_changed")
    if "identical shared_portfolio_return_window" not in str(search.get("DSR_input_series", "")):
        blockers.append("DSR_return_window_changed")
    if "identical candidate and comparator horizon lists" not in str(search.get("trial_horizon_rule", "")):
        blockers.append("DSR_trial_horizon_rule_changed")
    return blockers


def _validate_validation_seal(payload: dict[str, Any]) -> list[str]:
    seal = payload.get("validation_seal", {})
    if seal.get("window") != {"start": "2016-01-04", "end": "2026-06-30"} or seal.get("status") != "sealed_not_accessed":
        return ["validation_seal_changed"]
    if seal.get("forbidden_fields") != ["prices", "returns", "signals", "positions", "regimes", "benchmarks", "PnL"]:
        return ["validation_forbidden_fields_changed"]
    return []


def _sha256(path: Path) -> str | None:
    return hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else None


def _result(path: Path, blockers: list[str]) -> dict[str, Any]:
    return {"status": "fail" if blockers else "pass", "path": relative_to_root(path, PROJECT_ROOT), "blockers": blockers}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--path", type=Path, default=DEFAULT_PREREGISTRATION)
    args = parser.parse_args()
    result = validate_preregistration(args.path)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
