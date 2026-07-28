"""Fail-closed hermetic validator for the L-4 B8 breadth preregistration."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
GATE = PROJECT_ROOT / "experiments/l_4_breadth_preregistration_v1.json"

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from lib.statistics import paired_mean_minimum_observations


LAGS = [0.25, 0.125, 0.0625, 0.03125, 0.015625]
SOURCES = {
    "l1_preregistration": ("experiments/l_1_baseline_preregistration.json", "91527c2f4ec00134767df86849f36b9876b00eb44cd56dc01650d33bf938fe29"),
    "l3_preregistration": ("experiments/l_3_inverse_volatility_sizing_preregistration_v2.json", "83a68792614ee0def3ddb96349d6d95c7f0aeb0ac8b1c984c1e3d29ed74e709e"),
    "b715_closure": ("research_log/010-lily-l3-corrected-rerun.md", "4ab215690aefbab3e30434326ee9554d280f353363803c73e552317eb62d939d"),
}
SNAPSHOTS = [
    ("wiki/concepts/global-trend-regime-diversification.md", "6f1bf76c6730f1dfdde19809608f6533e7bf371830f58c132c3f47870ab4f0fb"),
    ("wiki/concepts/covariance-and-correlation.md", "27e28cb04ac1939acc6f4a1fc59e0a8208d365ee3e59872ffea9e4bb934c8828"),
    ("wiki/concepts/minimum-track-record-length.md", "ca65225740673bd363be7461b8022281da08ae32e6ff42f8887f1072eb51ad81"),
    ("wiki/concepts/newey-west-validation.md", "355b37f5f64d938d254337663b5df635ce008e47f8197eac041c03790643fcc5"),
    ("wiki/concepts/deflated-sharpe-ratio.md", "90663b67e49dcec90bd641e801f9464e593ff8fe9091b2d70e9f4645381af556"),
    ("wiki/concepts/backtest-validation-protocol.md", "c7f843310706d902120651e677429e66cbde9ce96ee526544de5419ee99aefa0"),
]
TOP_LEVEL = {"schema_version", "order_id", "gate_id", "hypothesis_id", "status", "evidence_ceiling", "edge_claim", "owner_authorization", "source_binding", "research_question", "universes", "sizing_isolation", "primary_observation", "realized_confirmation", "non_tautology_gates", "side_effects", "timing_and_seal", "statistics", "static_capacity", "data_integrity", "search_inventory", "decision_limits", "authorizations", "hard_stops"}


def validate_gate(gate_path: Path = GATE, *, project_root: Path = PROJECT_ROOT) -> dict[str, Any]:
    blockers: list[str] = []
    try:
        gate = json.loads(gate_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return _result([f"gate_unreadable:{exc.__class__.__name__}"])
    if not isinstance(gate, dict):
        return _result(["gate_not_object"])
    _exact_keys(gate, TOP_LEVEL, "top_level", blockers)
    _governance(gate, blockers)
    _sources(gate, project_root, blockers)
    _universes_and_sizing(gate, blockers)
    _scientific_contract(gate, blockers)
    _statistics(gate, blockers)
    _seals_and_authorizations(gate, blockers)
    return _result(blockers)


def _governance(gate: dict[str, Any], blockers: list[str]) -> None:
    expected = {"schema_version": "lily_l4_breadth_preregistration_v1", "order_id": "B8", "gate_id": "l_4_breadth_v1", "hypothesis_id": "L-4", "status": "locked_E0_planning_only", "evidence_ceiling": "E0", "edge_claim": "none", "owner_authorization": "Owner standing authorization to begin L-4 planning only; this B8 preregistration authorizes no data access, activation, execution, report, or research decision."}
    for key, value in expected.items():
        if gate.get(key) != value:
            blockers.append(f"governance_mismatch:{key}")


def _sources(gate: dict[str, Any], root: Path, blockers: list[str]) -> None:
    binding = gate.get("source_binding")
    _exact_keys(binding, {"l1_preregistration", "l3_preregistration", "b715_closure", "methodology_snapshots"}, "source_binding", blockers)
    if not isinstance(binding, dict):
        return
    for name, (path, digest) in SOURCES.items():
        expected = {"path": path, "sha256": digest}
        if name == "b715_closure":
            expected["commit"] = "a30fb4425a3abac5ecb03051c8677618f34c03c8"
        if binding.get(name) != expected:
            blockers.append(f"source_declaration_mismatch:{name}")
        if _sha256(root / path) != digest:
            blockers.append(f"source_hash_mismatch:{name}")
    declared = binding.get("methodology_snapshots")
    expected_snapshots = [{"wiki_relative_path": path, "snapshot_path": f"methodology_snapshots/l4_breadth_v1/{path}", "sha256": digest} for path, digest in SNAPSHOTS]
    if declared != expected_snapshots:
        blockers.append("methodology_snapshot_declarations_mismatch")
        return
    for item in expected_snapshots:
        if _sha256(root / item["snapshot_path"]) != item["sha256"]:
            blockers.append(f"methodology_snapshot_hash_mismatch:{item['wiki_relative_path']}")


def _universes_and_sizing(gate: dict[str, Any], blockers: list[str]) -> None:
    universes = gate.get("universes")
    _exact_keys(universes, {"inherited_l1_order", "U1", "U4", "U8", "eligible_date_rule"}, "universes", blockers)
    expected_order = ["VTI", "VGK", "EWJ", "VWO", "IEF", "TIP", "GLD", "DBC"]
    if not isinstance(universes, dict) or universes.get("inherited_l1_order") != expected_order or universes.get("U4", {}).get("members") != ["VTI", "IEF", "GLD", "DBC"] or universes.get("U8", {}).get("members") != expected_order:
        blockers.append("universe_order_or_nesting_mismatch")
    if not isinstance(universes, dict) or universes.get("U1") != {"members": ["VTI"], "role": "descriptive_only", "claim_eligible": False, "primary_effect_eligible": False, "reason": "The inherited 25% asset cap/cash constraint makes a portfolio-return comparison mechanically incomparable."}:
        blockers.append("u1_descriptive_only_mismatch")
    sizing = gate.get("sizing_isolation")
    _exact_keys(sizing, {"primary_raw_score", "primary_rule", "inverse_volatility", "l3_claim_limit"}, "sizing_isolation", blockers)
    if not isinstance(sizing, dict) or sizing.get("primary_raw_score") != "q[i,t]" or "non-claim-eligible" not in str(sizing.get("inverse_volatility")) or "No L-3 result may be carried forward" not in str(sizing.get("l3_claim_limit")):
        blockers.append("sizing_isolation_mismatch")


def _scientific_contract(gate: dict[str, Any], blockers: list[str]) -> None:
    primary = gate.get("primary_observation")
    _exact_keys(primary, {"unit", "anti_pseudoreplication", "ex_ante_hhi", "minimum_useful_reduction", "missingness"}, "primary_observation", blockers)
    if not isinstance(primary, dict) or primary.get("unit") != "one weekly paired U4-versus-U8 portfolio dependency observation" or primary.get("minimum_useful_reduction") != 0.05 or "Never multiply" not in str(primary.get("anti_pseudoreplication")):
        blockers.append("primary_observation_mismatch")
    realized = gate.get("realized_confirmation")
    _exact_keys(realized, {"timing", "measure", "minimum_useful_reduction", "overlap_rule"}, "realized_confirmation", blockers)
    if not isinstance(realized, dict) or "t+1 through t+20" not in str(realized.get("timing")) or realized.get("minimum_useful_reduction") != 0.05:
        blockers.append("realized_confirmation_mismatch")
    gates = gate.get("non_tautology_gates")
    _exact_keys(gates, {"effective_opportunity", "top_dependency", "trend_state", "best_market_removal", "best_trend_episode_removal", "anti_tautology"}, "non_tautology_gates", blockers)
    if not isinstance(gates, dict) or gates.get("effective_opportunity", {}).get("useful_increase_minimum") != 0.5 or gates.get("top_dependency", {}).get("useful_reduction_minimum") != 0.1 or gates.get("best_market_removal", {}).get("retained_hhi_benefit_minimum_fraction") != 0.5 or gates.get("best_trend_episode_removal", {}).get("retained_hhi_benefit_minimum_fraction") != 0.5 or "cannot pass L-4" not in str(gates.get("anti_tautology")):
        blockers.append("non_tautology_gate_mismatch")
    side_effects = gate.get("side_effects")
    if not isinstance(side_effects, dict) or side_effects.get("turnover_cost_relative_increase_maximum") != 0.2 or side_effects.get("cap_cash_scale_down_frequency_increase_maximum_percentage_points") != 10.0 or "comparable average gross exposure" not in str(side_effects.get("comparable_exposure")):
        blockers.append("side_effect_contract_mismatch")
    integrity = gate.get("data_integrity")
    if not isinstance(integrity, dict) or "survivorship-free" not in str(integrity.get("survivorship")) or set(integrity.get("kill_zones", [])) != {"synchronization and duplicate exposure", "correlated equity regions", "marginal cost", "backfill", "best-episode dependence"}:
        blockers.append("data_integrity_or_kill_zone_mismatch")
    search = gate.get("search_inventory")
    if not isinstance(search, dict) or "q / volatility" not in str(search.get("sensitivity")) or set(search.get("forbidden", [])) != {"post-result universe selection", "post-result date selection", "unlogged parameter/filter search", "U1 primary inference"}:
        blockers.append("search_inventory_mismatch")


def _statistics(gate: dict[str, Any], blockers: list[str]) -> None:
    stats = gate.get("statistics")
    if not isinstance(stats, dict) or stats.get("planning_standard_deviation_delta") != 0.1 or stats.get("one_sided_alpha") != 0.05 or stats.get("power") != 0.8 or stats.get("planning_autocorrelations_lags_1_to_5") != LAGS or stats.get("inflation") != 1.96875:
        blockers.append("statistics_parameters_mismatch")
        return
    plans = (stats.get("falsify_plan"), stats.get("validation_plans", {}).get("portfolio_zero"), stats.get("validation_plans", {}).get("minimum_useful"))
    actual = [paired_mean_minimum_observations(alternative_mean=a, null_mean=n, planning_standard_deviation=0.1, autocorrelations=LAGS, significance=0.05, power=0.8) for a, n in ((0.0, 0.05), (0.05, 0.0), (0.1, 0.05))]
    if actual != [49, 49, 49] or any(not isinstance(plan, dict) or plan.get("required_weekly_paired_observations") != 49 for plan in plans) or stats.get("validation_plans", {}).get("binding_required_weekly_paired_observations") != 49:
        blockers.append("statistics_mintrl_mismatch")
    capacity = gate.get("static_capacity")
    if not isinstance(capacity, dict) or capacity.get("maximum_weekly_slots_before_warmup_missingness_or_evaluable_pair_reductions") != 465 or capacity.get("regime_pooling") != "forbidden":
        blockers.append("static_capacity_mismatch")


def _seals_and_authorizations(gate: dict[str, Any], blockers: list[str]) -> None:
    seal = gate.get("timing_and_seal")
    if not isinstance(seal, dict) or seal.get("falsification_end") != "2015-12-31" or seal.get("validation_start") != "2016-01-04" or seal.get("validation_end") != "2026-06-30" or seal.get("validation_opened") is not False or seal.get("falsification_validation_pooling") is not False or "separate owner-approved" not in str(seal.get("activation_requirement")):
        blockers.append("timing_or_validation_seal_mismatch")
    authorizations = gate.get("authorizations")
    if not isinstance(authorizations, dict) or not authorizations or any(value is not False for value in authorizations.values()):
        blockers.append("authorizations_not_all_false")
    required_stops = {"No data/container/path discovery or inspection beyond named methodology sources and committed control artifacts.", "No market price, return, signal, position, covariance, regime, cost, or PnL computation or backtest.", "No validation access, provider/network acquisition, credentials/environment variables, broker, paid action, paper trade, or real money.", "No L-4 activation, execution runner, report, ledger, or B8.1.", "No L-3 closure weakening or inverse-volatility pass claim."}
    if set(gate.get("hard_stops", [])) != required_stops:
        blockers.append("hard_stops_mismatch")


def _exact_keys(value: Any, expected: set[str], label: str, blockers: list[str]) -> None:
    if not isinstance(value, dict):
        blockers.append(f"{label}_not_object")
        return
    extras = set(value) - expected
    missing = expected - set(value)
    blockers.extend(f"unknown_{label}_field:{key}" for key in sorted(extras))
    blockers.extend(f"missing_{label}_field:{key}" for key in sorted(missing))


def _sha256(path: Path) -> str | None:
    try:
        return hashlib.sha256(path.read_bytes()).hexdigest()
    except OSError:
        return None


def _result(blockers: list[str]) -> dict[str, Any]:
    return {"status": "pass" if not blockers else "blocked", "blockers": blockers, "gate_path": "experiments/l_4_breadth_preregistration_v1.json"}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--gate", type=Path, default=GATE)
    args = parser.parse_args()
    result = validate_gate(args.gate)
    print(json.dumps(result, indent=2, sort_keys=True))
    raise SystemExit(0 if result["status"] == "pass" else 1)
