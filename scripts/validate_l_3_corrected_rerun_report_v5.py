"""Validate the B7.9 prospective, synthetic-only L-3 report contract."""
from __future__ import annotations

import argparse
import json
import math
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from lib.provenance import file_sha256

GATE = ROOT / "experiments/l_3_corrected_rerun_activation_v5.json"
SCHEMA = ROOT / "schemas/l_3_corrected_rerun_report_v5.schema.json"
IMPLEMENTATION = {
    "gate": "experiments/l_3_corrected_rerun_activation_v5.json",
    "runner": "scripts/run_l_3_corrected_rerun_v5.py",
    "report_validator": "scripts/validate_l_3_corrected_rerun_report_v5.py",
    "report_schema": "schemas/l_3_corrected_rerun_report_v5.schema.json",
    "side_effect_library": "lib/l3_corrected_rerun_v5.py",
}
IDENTITIES = {
    "container_identity": "tests/fixtures/l3_corrected_rerun_v5/identities/synthetic_container.json",
    "schedule_identity": "tests/fixtures/l3_corrected_rerun_v5/identities/synthetic_schedule.json",
    "ledger_identity": "tests/fixtures/l3_corrected_rerun_v5/identities/synthetic_ledger.json",
}
TOP = {"schema_version", "order_id", "hypothesis_id", "report_mode", "decision", "evidence_tier", "edge_claim", "provenance", "counts", "primary", "realized", "side_effects", "regimes", "validation_seal", "autopsy"}
AUTOPSY = {"volatility_scaling_concentration", "common_constraints", "ex_ante_vs_realized_hhi", "turnover_cost", "implementation_data_alternatives"}
BRANCH = {"turnover", "commission", "spread_slippage", "sell_surcharge", "cap_events", "cash_events", "scale_down_events"}
REGIME_NAMES = ["low", "middle", "high"]


def _number(value: Any, *, nonnegative: bool = False) -> bool:
    return type(value) in (int, float) and math.isfinite(value) and (not nonnegative or value >= 0)


def _head() -> str | None:
    run = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True, capture_output=True, check=False)
    return run.stdout.strip() if run.returncode == 0 else None


def _identity(value: Any, expected: str) -> bool:
    return isinstance(value, dict) and value == {"path": expected, "sha256": file_sha256(ROOT / expected)}


def _bound_identity(value: Any, expected: str, present: bool) -> bool:
    if not isinstance(value, dict) or set(value) != {"present", "path", "sha256"}:
        return False
    if not present:
        return value == {"present": False, "path": None, "sha256": None}
    path = ROOT / expected
    return path.is_file() and value == {"present": True, "path": expected, "sha256": file_sha256(path)}


def _exact(value: Any, keys: set[str], name: str, blockers: list[str]) -> dict[str, Any] | None:
    if not isinstance(value, dict) or set(value) != keys:
        blockers.append(f"shape:{name}")
        return None
    return value


def _matrix(mode: Any, decision: Any, tier: Any, autopsy: Any, blockers: list[str]) -> None:
    allowed = {
        "synthetic_not_run": ("not_run", "E0"),
        "pre_return_failure": ("scope_restricted", "E1"),
    }
    if mode in allowed:
        if (decision, tier) != allowed[mode] or autopsy is not None:
            blockers.append("mode_decision_tier_autopsy_matrix")
    elif mode == "future_execution":
        if decision not in {"falsified", "not_falsified_not_validated"} or tier != "E1":
            blockers.append("mode_decision_tier_autopsy_matrix")
        if decision == "falsified":
            if not isinstance(autopsy, dict) or set(autopsy) != AUTOPSY or not all(isinstance(item, str) and item for item in autopsy.values()):
                blockers.append("five_part_autopsy_required")
        elif autopsy is not None:
            blockers.append("mode_decision_tier_autopsy_matrix")
    else:
        blockers.append("mode_decision_tier_autopsy_matrix")


def _blank_evidence(counts: dict[str, Any], primary: dict[str, Any], realized: dict[str, Any], side: dict[str, Any], regimes: dict[str, Any]) -> bool:
    return (counts == {"paired_observations": 0, "effective_independent_bets": 0.0, "mintrl_falsify": 49, "asset_multiplier": 1, "day_multiplier": 1, "trade_multiplier": 1, "t20_multiplier": 1}
        and primary == {"candidate_mean_hhi": None, "comparator_mean_hhi": None, "mean_delta": None, "threshold": None, "autocorrelation_ucb_trace": [], "ucb": None}
        and realized == {"candidate_mean_hhi": None, "comparator_mean_hhi": None, "mean_delta": None, "threshold": None, "complete_t_plus_20_observations": 0}
        and side == {"paired_observations": 0, "candidate": None, "comparator": None}
        and regimes == {"claims": [], "pooled": False})


def _future_evidence(counts: dict[str, Any], primary: dict[str, Any], realized: dict[str, Any], side: dict[str, Any], regimes: dict[str, Any], decision: str, blockers: list[str]) -> None:
    if not (type(counts.get("paired_observations")) is int and 49 <= counts["paired_observations"] <= 465 and _number(counts.get("effective_independent_bets"), nonnegative=True) and counts["effective_independent_bets"] >= 49 and counts.get("mintrl_falsify") == 49 and all(counts.get(key) == 1 for key in ("asset_multiplier", "day_multiplier", "trade_multiplier", "t20_multiplier"))):
        blockers.append("effective_funding_not_met")
    numeric_primary = all(_number(primary.get(key)) for key in ("candidate_mean_hhi", "comparator_mean_hhi", "mean_delta", "ucb"))
    trace = primary.get("autocorrelation_ucb_trace")
    if not numeric_primary or primary.get("threshold") != 0.05 or not isinstance(trace, list) or len(trace) != 5 or not all(_number(item) for item in trace) or abs(primary["mean_delta"] - (primary["comparator_mean_hhi"] - primary["candidate_mean_hhi"])) > 1e-12 or abs(primary["ucb"] - max(trace)) > 1e-12:
        blockers.append("primary_numeric_evidence_invalid")
    numeric_realized = all(_number(realized.get(key)) for key in ("candidate_mean_hhi", "comparator_mean_hhi", "mean_delta"))
    if not numeric_realized or realized.get("threshold") != 0.05 or realized.get("complete_t_plus_20_observations") != counts.get("paired_observations") or abs(realized["mean_delta"] - (realized["comparator_mean_hhi"] - realized["candidate_mean_hhi"])) > 1e-12:
        blockers.append("realized_confirmation_not_recomputable")
    if side.get("paired_observations") != counts.get("paired_observations") or not isinstance(side.get("candidate"), dict) or not isinstance(side.get("comparator"), dict) or set(side["candidate"]) != BRANCH or set(side["comparator"]) != BRANCH:
        blockers.append("side_effect_evidence_shape")
        side_metrics = None
    else:
        candidate, comparator = side["candidate"], side["comparator"]
        branch_ok = all(_number(branch.get(key), nonnegative=True) for branch in (candidate, comparator) for key in ("turnover", "commission", "spread_slippage", "sell_surcharge")) and all(type(branch.get(key)) is int and branch[key] >= 0 for branch in (candidate, comparator) for key in ("cap_events", "cash_events", "scale_down_events"))
        if not branch_ok or comparator["turnover"] == 0 or sum(comparator[key] for key in ("commission", "spread_slippage", "sell_surcharge")) == 0:
            blockers.append("side_effect_evidence_not_evaluable")
            side_metrics = None
        else:
            c_cost = sum(candidate[key] for key in ("commission", "spread_slippage", "sell_surcharge"))
            b_cost = sum(comparator[key] for key in ("commission", "spread_slippage", "sell_surcharge"))
            side_metrics = [(candidate["turnover"] - comparator["turnover"]) / comparator["turnover"], (c_cost - b_cost) / b_cost, *[(candidate[key] - comparator[key]) / counts["paired_observations"] for key in ("cap_events", "cash_events", "scale_down_events")]]
    claims = regimes.get("claims") if isinstance(regimes, dict) else None
    regime_ok = regimes.get("pooled") is False and isinstance(claims, list) and [claim.get("name") for claim in claims if isinstance(claim, dict)] == REGIME_NAMES and len(claims) == 3
    if regime_ok:
        for claim in claims:
            regime_ok = regime_ok and type(claim.get("paired_observations")) is int and 49 <= claim["paired_observations"] <= 465 and _number(claim.get("effective_independent_bets"), nonnegative=True) and claim["effective_independent_bets"] >= 49 and claim.get("mintrl_falsify") == 49 and all(claim.get(key) == 1 for key in ("asset_multiplier", "day_multiplier", "trade_multiplier", "t20_multiplier"))
    if not regime_ok:
        blockers.append("exact_regime_inventory_not_separately_funded")
    side_breach = side_metrics is not None and any(value > limit for value, limit in zip(side_metrics, (.20, .20, .10, .10, .10), strict=True))
    if decision == "not_falsified_not_validated" and (side_metrics is None or any(value > limit for value, limit in zip(side_metrics, (.20, .20, .10, .10, .10), strict=True))):
        blockers.append("not_falsified_requires_numeric_side_effect_limits")
    if decision == "falsified" and not (primary.get("ucb") is not None and _number(primary["ucb"]) and primary["ucb"] < .05 or side_breach):
        blockers.append("falsified_requires_ucb_or_numeric_side_breach")


def validate(payload: Any) -> dict[str, Any]:
    if not isinstance(payload, dict):
        return {"status": "blocked", "blockers": ["report_not_object"]}
    blockers: list[str] = []
    try:
        json.loads(SCHEMA.read_text(encoding="utf-8"))
    except Exception as exc:
        return {"status": "blocked", "blockers": [f"schema_unreadable:{type(exc).__name__}"]}
    if set(payload) != TOP:
        blockers.append("shape:top_level")
    if {key: payload.get(key) for key in ("schema_version", "order_id", "hypothesis_id", "edge_claim")} != {"schema_version": "lily_l3_corrected_rerun_report_v5", "order_id": "B7.9", "hypothesis_id": "L-3", "edge_claim": "none"}:
        blockers.append("identity")
    provenance = _exact(payload.get("provenance"), {"producing_git_commit", *IMPLEMENTATION, *IDENTITIES}, "provenance", blockers)
    counts = _exact(payload.get("counts"), {"paired_observations", "effective_independent_bets", "mintrl_falsify", "asset_multiplier", "day_multiplier", "trade_multiplier", "t20_multiplier"}, "counts", blockers)
    primary = _exact(payload.get("primary"), {"candidate_mean_hhi", "comparator_mean_hhi", "mean_delta", "threshold", "autocorrelation_ucb_trace", "ucb"}, "primary", blockers)
    realized = _exact(payload.get("realized"), {"candidate_mean_hhi", "comparator_mean_hhi", "mean_delta", "threshold", "complete_t_plus_20_observations"}, "realized", blockers)
    side = _exact(payload.get("side_effects"), {"paired_observations", "candidate", "comparator"}, "side_effects", blockers)
    regimes = _exact(payload.get("regimes"), {"claims", "pooled"}, "regimes", blockers)
    mode, decision = payload.get("report_mode"), payload.get("decision")
    _matrix(mode, decision, payload.get("evidence_tier"), payload.get("autopsy"), blockers)
    if provenance is not None:
        if provenance.get("producing_git_commit") != _head():
            blockers.append("producing_checkout_head_mismatch")
        for name, path in IMPLEMENTATION.items():
            if not _identity(provenance.get(name), path):
                blockers.append(f"implementation_identity_mismatch:{name}")
        for name, path in IDENTITIES.items():
            if not _bound_identity(provenance.get(name), path, mode == "future_execution"):
                blockers.append(f"synthetic_identity_binding_invalid:{name}")
    if payload.get("validation_seal") != {"status": "sealed_not_accessed", "accessed": False}:
        blockers.append("validation_seal_broken")
    if all(value is not None for value in (counts, primary, realized, side, regimes)):
        if mode == "future_execution":
            _future_evidence(counts, primary, realized, side, regimes, decision, blockers)
        elif not _blank_evidence(counts, primary, realized, side, regimes):
            blockers.append("nonexecution_evidence_must_be_blank")
    return {"status": "pass" if not blockers else "blocked", "blockers": sorted(set(blockers))}


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate a prospective B7.9 synthetic-only L-3 report.")
    parser.add_argument("report", type=Path)
    args = parser.parse_args()
    try:
        payload = json.loads(args.report.read_text(encoding="utf-8"))
    except Exception as exc:
        print(json.dumps({"status": "blocked", "blockers": [f"unreadable:{type(exc).__name__}"]}, sort_keys=True))
        return 1
    result = validate(payload)
    print(json.dumps(result, sort_keys=True))
    return 0 if result["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
