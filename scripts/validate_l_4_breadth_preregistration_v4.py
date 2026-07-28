"""Fail-closed B8.3 E0/no-data exact-preservation validator."""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from itertools import product
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from lib.statistics import paired_mean_minimum_observations

GATE = ROOT / "experiments/l_4_breadth_preregistration_v4.json"
EXPECTED_SHA = "648b480aed523074e8c99646b313c70b074ca6bde95c2a30fb88a128d150ffcb"
LAGS = [0.25, 0.125, 0.0625, 0.03125, 0.015625]
METRICS = {"ex_ante_hhi_delta": (0.05, 0.1), "realized_hhi_delta": (0.05, 0.1), "top_dependency_delta": (0.1, 0.2), "n_eff_delta": (0.5, 1.0)}
SNAPSHOTS = (
    ("wiki/concepts/global-trend-regime-diversification.md", "6f1bf76c6730f1dfdde19809608f6533e7bf371830f58c132c3f47870ab4f0fb"),
    ("wiki/concepts/covariance-and-correlation.md", "27e28cb04ac1939acc6f4a1fc59e0a8208d365ee3e59872ffea9e4bb934c8828"),
    ("wiki/concepts/minimum-track-record-length.md", "ca65225740673bd363be7461b8022281da08ae32e6ff42f8887f1072eb51ad81"),
    ("wiki/concepts/newey-west-validation.md", "355b37f5f64d938d254337663b5df635ce008e47f8197eac041c03790643fcc5"),
    ("wiki/concepts/deflated-sharpe-ratio.md", "90663b67e49dcec90bd641e801f9464e593ff8fe9091b2d70e9f4645381af556"),
    ("wiki/concepts/backtest-validation-protocol.md", "c7f843310706d902120651e677429e66cbde9ce96ee526544de5419ee99aefa0"),
)
TOP = {"schema_version", "order_id", "gate_id", "supersedes_gate_id", "hypothesis_id", "status", "evidence_ceiling", "edge_claim", "owner_authorization", "v3_binding", "source_binding", "research_question", "universes", "primary_sizing", "macro_sleeves", "static_capacity", "inherited_controls", "component_risk", "mandatory_metrics", "statistics", "robustness_and_side_effects", "regime_matrix", "decision_contract", "timing_and_seal", "authorizations", "hard_stops"}


def classify_e1(*, non_evaluable_or_underfunded: bool, breach: bool) -> str:
    if non_evaluable_or_underfunded:
        return "scope_restricted"
    if breach:
        return "falsified_E1_only"
    return "not_falsified_not_validated_E1"


def classify_validation(*, non_evaluable_or_underfunded: bool, breach: bool, all_lcb_strictly_above: bool, constraints_pass: bool, integrity_pass: bool) -> str:
    if non_evaluable_or_underfunded:
        return "validation_scope_restricted"
    if breach:
        return "validation_falsified_E1_only"
    if all_lcb_strictly_above and constraints_pass and integrity_pass:
        return "validation_candidate"
    return "not_validated_E1"


def validate_gate(gate_path: Path = GATE, *, project_root: Path = ROOT) -> dict[str, Any]:
    try:
        raw = gate_path.read_bytes()
        gate = json.loads(raw)
    except (OSError, json.JSONDecodeError) as exc:
        return _result([f"gate_unreadable:{exc.__class__.__name__}"])
    blockers: list[str] = []
    _closed_schema(gate, blockers)
    if hashlib.sha256(raw).hexdigest() != EXPECTED_SHA:
        blockers.append("gate_bytes_or_semantics_mismatch")
    _sources(gate, project_root, blockers)
    _semantics(gate, blockers)
    _planning(gate, blockers)
    _truth_tables(blockers)
    return _result(blockers)


def _closed_schema(gate: Any, blockers: list[str]) -> None:
    schema = {
        "$": TOP, "$.v3_binding": {"gate_path", "gate_sha256", "validator_path", "validator_sha256", "manifest_gate_id"}, "$.source_binding": {"v3", "l1", "l3", "b715", "snapshots"}, "$.source_binding.v3": {"gate_path", "gate_sha256", "validator_path", "validator_sha256"}, "$.source_binding.l1": {"path", "sha256"}, "$.source_binding.l3": {"path", "sha256"}, "$.source_binding.b715": {"path", "sha256", "commit", "git_blob_sha1"}, "$.source_binding.snapshots": {"root", "files"}, "$.source_binding.snapshots.files[]": {"path", "sha256"},
        "$.universes": {"order", "U1", "U4", "U8", "dates"}, "$.universes.U1": {"members", "role", "claim_eligible"}, "$.primary_sizing": {"step_1", "stages", "sensitivity"}, "$.macro_sleeves": {"equity", "nominal_bonds", "inflation_linked_bonds", "gold", "broad_commodities"}, "$.static_capacity": {"maximum_weekly_slots_before_warmup_missingness_or_evaluable_pair_reductions", "observation_unit"}, "$.inherited_controls": {"primary_sizing", "matched_dates", "l3_status"}, "$.component_risk": {"formula", "covariance", "cash", "non_evaluable"},
        "$.mandatory_metrics": set(METRICS), "$.statistics": {"one_sided_alpha", "power", "autocorrelations_lags_1_to_5", "inflation", "actual_recalculation"}, "$.robustness_and_side_effects": {"classification", "best_market", "best_trend_episode", "side_effects"}, "$.robustness_and_side_effects.best_market": {"selection", "recalculation", "threshold", "retained_fraction", "failure"}, "$.robustness_and_side_effects.best_trend_episode": {"episode_rule", "selection", "recalculation", "threshold", "retained_fraction", "minimum_sample"}, "$.robustness_and_side_effects.side_effects": {"turnover_intensity", "cost_intensity", "relative_increase", "maximum_relative_increase", "cap_cash_scale_down", "maximum_frequency_delta_percentage_points"},
        "$.regime_matrix": {"global_state", "volatility", "equity_synchronization", "major_subperiods", "crisis_windows", "breakdowns", "funding"}, "$.regime_matrix.major_subperiods[]": {"start", "end"}, "$.decision_contract": {"e1", "validation", "precedence", "equality", "scope_restricted", "falsified_E1_only", "not_falsified_not_validated_E1", "validation_scope_restricted", "validation_falsified_E1_only", "validation_candidate", "not_validated_E1"}, "$.timing_and_seal": {"falsification_end", "validation_start", "validation_end", "validation_opened", "pooling"}, "$.authorizations": {"data", "container", "market", "return", "signal", "position", "covariance", "regime", "cost", "pnl", "validation", "provider", "network", "credentials", "broker", "paid", "paper_trade", "real_money", "activation", "execution", "report", "research_decision"},
    }
    def walk(value: Any, path: str) -> None:
        allowed = schema.get(path)
        if path.startswith("$.mandatory_metrics.") and path.count(".") == 2:
            allowed = {"formula", "useful_threshold", "falsify", "validation_zero", "validation_minimum_useful"}
        elif path.startswith("$.mandatory_metrics.") and path.count(".") == 3:
            allowed = {"tail", "null", "alternative", "planning_sd", "expected_mintrl"}
        if isinstance(value, dict):
            if allowed is None or set(value) != allowed:
                blockers.append(f"closed_schema_mismatch:{path}")
            for key, item in value.items():
                walk(item, f"{path}.{key}")
        elif isinstance(value, list):
            for item in value:
                walk(item, f"{path}[]")
    walk(gate, "$")


def _sources(gate: dict[str, Any], root: Path, blockers: list[str]) -> None:
    binding = gate["v3_binding"]
    expected_v3 = {"gate_path": "experiments/l_4_breadth_preregistration_v3.json", "gate_sha256": "59010f1486ff891172b9b71a51dca3b770206bebf44ecc28fb17a4df871eb238", "validator_path": "scripts/validate_l_4_breadth_preregistration_v3.py", "validator_sha256": "ecaea56625cd4f42810bec7c8281d5d5bbc53874c8b3e4610ddeffa30f722ced", "manifest_gate_id": "l_4_breadth_v3"}
    if binding != expected_v3:
        blockers.append("v3_binding_declaration_mismatch")
    for path, digest in ((binding.get("gate_path"), binding.get("gate_sha256")), (binding.get("validator_path"), binding.get("validator_sha256")), ("experiments/l_1_baseline_preregistration.json", gate["source_binding"]["l1"].get("sha256")), ("experiments/l_3_inverse_volatility_sizing_preregistration_v2.json", gate["source_binding"]["l3"].get("sha256")), ("research_log/010-lily-l3-corrected-rerun.md", gate["source_binding"]["b715"].get("sha256"))):
        if not isinstance(path, str) or _sha(root / path) != digest:
            blockers.append(f"source_hash_mismatch:{path}")
    snapshots = gate["source_binding"].get("snapshots", {})
    declared = [(item.get("path"), item.get("sha256")) for item in snapshots.get("files", []) if isinstance(item, dict)]
    if snapshots.get("root") != "methodology_snapshots/l4_breadth_v1" or declared != list(SNAPSHOTS):
        blockers.append("snapshot_declaration_mismatch")
    for path, digest in SNAPSHOTS:
        if _sha(root / "methodology_snapshots/l4_breadth_v1" / path) != digest:
            blockers.append(f"snapshot_hash_mismatch:{path}")
    try:
        rows = [json.loads(line) for line in (root / "experiments/locked_gates.jsonl").read_text(encoding="utf-8").splitlines() if line]
        rows = [row for row in rows if row.get("gate_id") == "l_4_breadth_v3"]
    except (OSError, json.JSONDecodeError):
        rows = []
    if len(rows) != 1 or rows[0].get("artifact_sha256") != binding["gate_sha256"] or rows[0].get("validator_sha256") != binding["validator_sha256"]:
        blockers.append("v3_manifest_identity_mismatch")
    run = subprocess.run(["git", "rev-parse", "62557cc7d02f81fafbed57ef7bcd8cc836193fe1:research_log/010-lily-l3-corrected-rerun.md"], cwd=root, text=True, capture_output=True, check=False)
    if run.returncode or run.stdout.strip() != gate["source_binding"]["b715"].get("git_blob_sha1"):
        blockers.append("b715_commit_blob_mismatch")


def _semantics(gate: dict[str, Any], blockers: list[str]) -> None:
    if gate["macro_sleeves"] != {"equity": ["VTI", "VGK", "EWJ", "VWO"], "nominal_bonds": ["IEF"], "inflation_linked_bonds": ["TIP"], "gold": ["GLD"], "broad_commodities": ["DBC"]}:
        blockers.append("macro_sleeves_mismatch")
    if gate["static_capacity"].get("maximum_weekly_slots_before_warmup_missingness_or_evaluable_pair_reductions") != 465 or "one weekly paired portfolio observation" not in gate["static_capacity"].get("observation_unit", ""):
        blockers.append("static_capacity_or_unit_mismatch")
    robustness = gate["robustness_and_side_effects"]
    episode = robustness.get("best_trend_episode", {})
    if not all(term in episode.get("episode_rule", "") for term in ("consecutive weekly nonzero q", "at most one neutral bridge", "opposite sign or two neutrals")) or episode.get("threshold") != .025 or episode.get("retained_fraction") != .5 or "actual primary HHI MinTRL" not in episode.get("minimum_sample", ""):
        blockers.append("best_episode_rule_mismatch")
    market = robustness.get("best_market", {})
    if market.get("threshold") != .025 or market.get("retained_fraction") != .5 or "ties use inherited ETF order" not in market.get("selection", "") or "without rerunning or reselecting" not in market.get("recalculation", ""):
        blockers.append("best_market_rule_mismatch")
    side = robustness.get("side_effects", {})
    if side.get("maximum_relative_increase") != .2 or side.get("maximum_frequency_delta_percentage_points") != 10.0 or "zero or nonfinite" not in side.get("relative_increase", ""):
        blockers.append("side_effect_limits_mismatch")
    regimes = gate["regime_matrix"]
    if regimes.get("equity_synchronization") != ["all four equity q signs same nonzero", "mixed signs", "neutral present"] or regimes.get("major_subperiods") != [{"start": "2007-02-05", "end": "2011-06-30"}, {"start": "2011-07-01", "end": "2015-12-31"}] or regimes.get("breakdowns") != ["asset", "macro_sleeve", "country_or_region"] or "no pooling" not in regimes.get("funding", ""):
        blockers.append("regime_matrix_mismatch")
    if "Missing/nonfinite" not in gate["component_risk"].get("non_evaluable", "") or "missing/constant/nonfinite q" not in gate["component_risk"].get("non_evaluable", ""):
        blockers.append("missingness_mismatch")
    if gate["decision_contract"].get("validation") != ["validation_scope_restricted", "validation_falsified_E1_only", "validation_candidate", "not_validated_E1"]:
        blockers.append("validation_outcomes_mismatch")
    if gate["timing_and_seal"].get("validation_opened") is not False or set(gate["authorizations"]) != {"data", "container", "market", "return", "signal", "position", "covariance", "regime", "cost", "pnl", "validation", "provider", "network", "credentials", "broker", "paid", "paper_trade", "real_money", "activation", "execution", "report", "research_decision"} or any(value is not False for value in gate["authorizations"].values()):
        blockers.append("seal_or_authorization_opened")


def _planning(gate: dict[str, Any], blockers: list[str]) -> None:
    for name, (threshold, sd) in METRICS.items():
        metric = gate["mandatory_metrics"].get(name, {})
        expected = (("falsify", "lower", threshold, 0.0), ("validation_zero", "upper", 0.0, threshold), ("validation_minimum_useful", "upper", threshold, 2 * threshold))
        for plan_name, tail, null, alternative in expected:
            actual = paired_mean_minimum_observations(alternative_mean=alternative, null_mean=null, planning_standard_deviation=sd, autocorrelations=LAGS, significance=.05, power=.8)
            if metric.get("useful_threshold") != threshold or metric.get(plan_name) != {"tail": tail, "null": null, "alternative": alternative, "planning_sd": sd, "expected_mintrl": 49} or actual != 49:
                blockers.append(f"mintrl_plan_mismatch:{name}:{plan_name}")


def _truth_tables(blockers: list[str]) -> None:
    for non_evaluable, breach in product((False, True), repeat=2):
        expected = "scope_restricted" if non_evaluable else "falsified_E1_only" if breach else "not_falsified_not_validated_E1"
        if classify_e1(non_evaluable_or_underfunded=non_evaluable, breach=breach) != expected:
            blockers.append("e1_truth_table_mismatch")
    outcomes = set()
    for values in product((False, True), repeat=5):
        result = classify_validation(non_evaluable_or_underfunded=values[0], breach=values[1], all_lcb_strictly_above=values[2], constraints_pass=values[3], integrity_pass=values[4])
        outcomes.add(result)
        if values[0] and result != "validation_scope_restricted": blockers.append("validation_scope_precedence_mismatch")
        if not values[0] and values[1] and result != "validation_falsified_E1_only": blockers.append("validation_falsification_precedence_mismatch")
    if outcomes != {"validation_scope_restricted", "validation_falsified_E1_only", "validation_candidate", "not_validated_E1"}:
        blockers.append("validation_truth_table_not_exhaustive")
    if classify_validation(non_evaluable_or_underfunded=False, breach=False, all_lcb_strictly_above=False, constraints_pass=True, integrity_pass=True) != "not_validated_E1":
        blockers.append("validation_equality_boundary_mismatch")


def _sha(path: Path) -> str | None:
    try:
        return hashlib.sha256(path.read_bytes()).hexdigest()
    except OSError:
        return None


def _result(blockers: list[str]) -> dict[str, Any]:
    return {"status": "pass" if not blockers else "blocked", "blockers": blockers, "gate_path": "experiments/l_4_breadth_preregistration_v4.json"}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--gate", type=Path, default=GATE)
    args = parser.parse_args()
    result = validate_gate(args.gate)
    print(json.dumps(result, indent=2, sort_keys=True))
    raise SystemExit(result["status"] != "pass")
