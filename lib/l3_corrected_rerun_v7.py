"""B7.11 closed-world synthetic paired-observation derivation; no data I/O."""
from __future__ import annotations

import math
from typing import Any

Z_ONE_SIDED_95 = 1.6448536269514722
Z_POWER_80 = 0.8416212335729143
NULL_DELTA = 0.05
ADVERSE_DELTA = 0.0
MINTRL_FLOOR = 49
REGIMES = ("low", "middle", "high")
SIDE_KEYS = ("turnover", "commission", "spread_slippage", "sell_surcharge")
EVENT_KEYS = ("cap_event", "cash_event", "scale_down_event")


def finite(value: Any, *, nonnegative: bool = False) -> bool:
    return type(value) in (int, float) and math.isfinite(value) and (not nonnegative or value >= 0)


def _statistics(deltas: list[float]) -> dict[str, Any] | None:
    n = len(deltas)
    if n <= 5:
        return None
    mean = sum(deltas) / n
    denominator = sum((value - mean) ** 2 for value in deltas)
    if denominator <= 0 or not math.isfinite(denominator):
        return None
    sd = math.sqrt(denominator / (n - 1))
    lags = [sum((deltas[index] - mean) * (deltas[index - lag] - mean) for index in range(lag, n)) / denominator for lag in range(1, 6)]
    inflation = 1.0 + 2.0 * sum(lags)
    if not all(math.isfinite(value) for value in lags) or inflation <= 0:
        return None
    se = sd * math.sqrt(inflation / n)
    mintrl = max(MINTRL_FLOOR, math.ceil((Z_ONE_SIDED_95 + Z_POWER_80) ** 2 * sd ** 2 * inflation / (NULL_DELTA - ADVERSE_DELTA) ** 2))
    return {"raw_weekly_paired_observations": n, "paired_delta_mean": mean, "paired_delta_standard_deviation": sd, "lag_1_to_5_sample_autocorrelations": lags, "locked_asymptotic_autocorrelation_inflation": inflation, "standard_error": se, "one_sided_95_ucb": mean + Z_ONE_SIDED_95 * se, "actual_raw_observation_mintrl_falsify": mintrl, "raw_n_meets_actual_mintrl": n >= mintrl}


def derive(observations: Any) -> tuple[dict[str, Any] | None, list[str]]:
    """Derive every decision input from ordered synthetic observations, or fail closed."""
    if not isinstance(observations, list) or not observations or len(observations) > 465:
        return None, ["weekly_observations_cardinality"]
    blockers: list[str] = []
    deltas: list[float] = []
    realized_deltas: list[float] = []
    regime_deltas: dict[str, list[float]] = {name: [] for name in REGIMES}
    totals = {branch: {key: 0.0 for key in SIDE_KEYS} | {key: 0 for key in EVENT_KEYS} for branch in ("candidate", "comparator")}
    required = {"observation_index", "observation_id", "regime", "primary_candidate_hhi", "primary_comparator_hhi", "realized_candidate_hhi", "realized_comparator_hhi", "side_effects"}
    for expected, observation in enumerate(observations, start=1):
        if not isinstance(observation, dict) or set(observation) != required:
            blockers.append("observation_shape"); continue
        if observation.get("observation_index") != expected or observation.get("observation_id") != f"synthetic-week-{expected:03d}" or observation.get("regime") not in REGIMES:
            blockers.append("observation_identity_or_order"); continue
        hhis = [observation.get(key) for key in ("primary_candidate_hhi", "primary_comparator_hhi", "realized_candidate_hhi", "realized_comparator_hhi")]
        if not all(finite(value) and .125 <= value <= 1.0 for value in hhis):
            blockers.append("hhi_domain"); continue
        side = observation.get("side_effects")
        if not isinstance(side, dict) or set(side) != {"candidate", "comparator"}:
            blockers.append("side_effect_shape"); continue
        valid_side = True
        for branch in ("candidate", "comparator"):
            row = side.get(branch)
            if not isinstance(row, dict) or set(row) != set(SIDE_KEYS) | set(EVENT_KEYS): valid_side = False; break
            if not all(finite(row.get(key), nonnegative=True) for key in SIDE_KEYS) or not all(type(row.get(key)) is bool for key in EVENT_KEYS): valid_side = False; break
        if not valid_side:
            blockers.append("side_effect_inputs"); continue
        delta = observation["primary_comparator_hhi"] - observation["primary_candidate_hhi"]
        deltas.append(delta); realized_deltas.append(observation["realized_comparator_hhi"] - observation["realized_candidate_hhi"]); regime_deltas[observation["regime"]].append(delta)
        for branch in ("candidate", "comparator"):
            for key in SIDE_KEYS: totals[branch][key] += side[branch][key]
            for key in EVENT_KEYS: totals[branch][key] += int(side[branch][key])
    if blockers:
        return None, sorted(set(blockers))
    primary = _statistics(deltas)
    if primary is None:
        return None, ["primary_statistics_undefined"]
    regimes: dict[str, Any] = {}
    for name in REGIMES:
        stats = _statistics(regime_deltas[name])
        if stats is None:
            return None, [f"regime_statistics_undefined:{name}"]
        regimes[name] = stats
    comparator_cost = sum(totals["comparator"][key] for key in SIDE_KEYS[1:])
    if totals["comparator"]["turnover"] == 0 or comparator_cost == 0:
        return None, ["side_effect_zero_denominator"]
    side = {"candidate": totals["candidate"], "comparator": totals["comparator"], "turnover_increase": (totals["candidate"]["turnover"] - totals["comparator"]["turnover"]) / totals["comparator"]["turnover"], "cost_increase": (sum(totals["candidate"][key] for key in SIDE_KEYS[1:]) - comparator_cost) / comparator_cost}
    for key in EVENT_KEYS:
        side[f"{key}_increase_percentage_points"] = 100.0 * (totals["candidate"][key] - totals["comparator"][key]) / len(observations)
    limits_met = side["turnover_increase"] <= .20 and side["cost_increase"] <= .20 and all(side[f"{key}_increase_percentage_points"] <= 10.0 for key in EVENT_KEYS)
    return {"primary": primary, "realized": {"paired_delta_mean": sum(realized_deltas) / len(realized_deltas)}, "regimes": regimes, "two_of_three_regimes_funded": sum(item["raw_n_meets_actual_mintrl"] for item in regimes.values()) >= 2, "side_effects": side, "side_effect_limits_met": limits_met}, []
