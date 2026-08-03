"""B8.8R5/v6 synthetic-only correction layer for the L-4 future engine.

The v5 bytes remain immutable.  This module reuses v5's already-derived
portfolio state and replaces only the rejected side-effect and breakdown
machinery before returning a report.  No path or container access is added
here; the committed bootstrap owns that boundary.
"""
from __future__ import annotations

import math
from collections import defaultdict
from statistics import mean
from typing import Any, Sequence

from lib.l4_b88r4_scientific_engine_v5 import (
    CURRENT_EXPENSE_RATIOS,
    LOCKED_CONFIG,
    METRICS,
    SEAL,
    U4,
    U8,
    USEFUL,
    derive as _derive_v5,
    _costs,
    directional_q,
    drift_weights,
    ewma_covariance_pairwise_complete,
    l1_ewma_cross_check,
    psd_clip,
    threshold_changes,
)
from lib.trend_baseline import REGIONS

MACRO_SLEEVES = {
    "equity": ("VTI", "VGK", "EWJ", "VWO"),
    "nominal_bonds": ("IEF",),
    "inflation_linked_bonds": ("TIP",),
    "gold": ("GLD",),
    "broad_commodities": ("DBC",),
}
MACRO_SLEEVE_ORDER = tuple(MACRO_SLEEVES)
REGION_ORDER = ("United_States", "Europe", "Japan", "Emerging_markets", "Global")


def _finite(value: object) -> bool:
    return type(value) in (int, float) and math.isfinite(value)


def _component_shares(weights: Sequence[float], covariance: Sequence[Sequence[float]]) -> list[float] | None:
    if len(weights) != len(covariance) or not weights:
        return None
    if any(len(row) != len(weights) for row in covariance):
        return None
    if not all(_finite(value) for value in weights):
        return None
    if not all(_finite(value) for row in covariance for value in row):
        return None
    contributions = [
        weights[index] * sum(covariance[index][other] * weights[other] for other in range(len(weights)))
        for index in range(len(weights))
    ]
    denominator = sum(abs(value) for value in contributions)
    return None if not _finite(denominator) or denominator <= 0.0 else [abs(value) / denominator for value in contributions]


def _dominant(shares: Sequence[float], groups: dict[str, Sequence[str]], order: Sequence[str]) -> tuple[str, float] | None:
    if len(shares) != len(U8) or not all(_finite(value) for value in shares):
        return None
    indices = {symbol: index for index, symbol in enumerate(U8)}
    totals = {
        name: sum(shares[indices[symbol]] for symbol in members)
        for name, members in groups.items()
    }
    if any(not _finite(value) for value in totals.values()):
        return None
    selected = max(order, key=lambda name: (totals[name], -order.index(name)))
    return selected, totals[selected]


def _breakdown_assignment(row: dict[str, Any]) -> dict[str, Any] | None:
    state = row.get("state", {}).get("u8", {})
    shares = _component_shares(state.get("weights", []), state.get("covariance", []))
    if shares is None:
        return None
    asset, asset_share = _dominant(shares, {symbol: (symbol,) for symbol in U8}, U8) or (None, None)
    macro_sleeve, macro_share = _dominant(shares, MACRO_SLEEVES, MACRO_SLEEVE_ORDER) or (None, None)
    region_groups: dict[str, list[str]] = defaultdict(list)
    for symbol in U8:
        region_groups[REGIONS[symbol]].append(symbol)
    region, region_share = _dominant(shares, region_groups, REGION_ORDER) or (None, None)
    if None in (asset, macro_sleeve, region):
        return None
    return {
        "asset": asset,
        "asset_component_share": asset_share,
        "macro_sleeve": macro_sleeve,
        "macro_sleeve_component_share": macro_share,
        "country_or_region": region,
        "country_or_region_component_share": region_share,
        "rule": "one dominant U8 component-risk bucket per dimension; ties use locked order",
    }


def _side_effects(rows: list[dict[str, Any]]) -> dict[str, Any]:
    """Use the preregistered aggregate denominator, not per-row gross values."""
    if not rows:
        return {"evaluable": False, "pass": False}
    turnover_u4 = sum(sum(abs(value) for value in row["changes_u4"]) for row in rows)
    turnover_u8 = sum(sum(abs(value) for value in row["changes_u8"]) for row in rows)
    cost_u4 = sum(row["costs_u4"]["total"] for row in rows)
    cost_u8 = sum(row["costs_u8"]["total"] for row in rows)
    gross_u4 = sum(row["gross_u4"] for row in rows)
    gross_u8 = sum(row["gross_u8"] for row in rows)
    turnover_intensity_u4 = turnover_u4 / gross_u4 if gross_u4 else None
    turnover_intensity_u8 = turnover_u8 / gross_u8 if gross_u8 else None
    cost_intensity_u4 = cost_u4 / gross_u4 if gross_u4 else None
    cost_intensity_u8 = cost_u8 / gross_u8 if gross_u8 else None
    finite_inputs = all(
        _finite(value)
        for value in (turnover_u4, turnover_u8, cost_u4, cost_u8, gross_u4, gross_u8)
    )
    evaluable = bool(
        finite_inputs
        and gross_u4 > 0.0
        and gross_u8 > 0.0
        and turnover_intensity_u4 not in (None, 0.0)
        and cost_intensity_u4 not in (None, 0.0)
        and _finite(turnover_intensity_u4)
        and _finite(turnover_intensity_u8)
        and _finite(cost_intensity_u4)
        and _finite(cost_intensity_u8)
    )
    turnover_relative = turnover_intensity_u8 / turnover_intensity_u4 - 1.0 if evaluable else None
    cost_relative = cost_intensity_u8 / cost_intensity_u4 - 1.0 if evaluable else None
    flags = {
        flag: 100.0 * (sum(row["flags_u8"][flag] for row in rows) - sum(row["flags_u4"][flag] for row in rows)) / len(rows)
        for flag in ("cap", "cash", "scale_down")
    }
    result = {
        "evaluable": evaluable,
        "turnover_u4": turnover_u4,
        "turnover_u8": turnover_u8,
        "pre_trade_gross_u4": gross_u4,
        "pre_trade_gross_u8": gross_u8,
        "turnover_intensity_u4": turnover_intensity_u4,
        "turnover_intensity_u8": turnover_intensity_u8,
        "turnover_relative_increase": turnover_relative,
        "cost_u4": cost_u4,
        "cost_u8": cost_u8,
        "cost_intensity_u4": cost_intensity_u4,
        "cost_intensity_u8": cost_intensity_u8,
        "cost_relative_increase": cost_relative,
        "flag_frequency_delta_percentage_points": flags,
    }
    result["pass"] = bool(
        evaluable
        and turnover_relative <= 0.20
        and cost_relative <= 0.20
        and all(value <= 10.0 for value in flags.values())
    )
    return result


def _regimes(rows: list[dict[str, Any]]) -> dict[str, Any]:
    names = (
        "global_state:broad_uptrend", "global_state:broad_downtrend", "global_state:whipsaw", "global_state:mixed",
        "volatility_tercile:warmup_unclassified", "volatility_tercile:low", "volatility_tercile:middle", "volatility_tercile:high",
        "equity_synchronization:all_four_equity_signs_same_nonzero", "equity_synchronization:mixed_signs", "equity_synchronization:neutral_present",
        "subperiod:2007-02-05_to_2011-06-30", "subperiod:2011-07-01_to_2015-12-31", "crisis:GFC", "crisis:COVID_sealed", "crisis:inflation_2022_sealed",
    )
    buckets: dict[str, list[dict[str, Any]]] = {name: [] for name in names}
    for symbol in U8:
        buckets[f"asset:{symbol}"] = []
    for sleeve in MACRO_SLEEVE_ORDER:
        buckets[f"macro_sleeve:{sleeve}"] = []
    for region in REGION_ORDER:
        buckets[f"country_or_region:{region}"] = []
    for row in rows:
        regime = row["regime"]
        buckets[f"global_state:{regime['global_state']}"].append(row)
        buckets[f"volatility_tercile:{regime['volatility_tercile']}"].append(row)
        buckets[f"equity_synchronization:{regime['equity_synchronization']}"].append(row)
        buckets[f"subperiod:{'2007-02-05_to_2011-06-30' if row['date'] <= '2011-06-30' else '2011-07-01_to_2015-12-31'}"].append(row)
        if "2007-07-01" <= row["date"] <= "2009-06-30":
            buckets["crisis:GFC"].append(row)
        assignment = row.get("breakdown") or _breakdown_assignment(row)
        if assignment is not None:
            buckets[f"asset:{assignment['asset']}"].append(row)
            buckets[f"macro_sleeve:{assignment['macro_sleeve']}"].append(row)
            buckets[f"country_or_region:{assignment['country_or_region']}"].append(row)

    def summarize(items: list[dict[str, Any]]) -> dict[str, Any]:
        statistics = {
            metric: _statistics(items)[metric]
            for metric in METRICS
            if metric in _statistics(items)
        }
        return {
            "weekly_observations": len(items),
            "metric_statistics": statistics,
            "funded_by_metric": {
                metric: bool(statistics.get(metric) and len(items) >= statistics[metric]["mintrl"]["falsify"])
                for metric in METRICS
            },
            "underfunded": len(items) < 6,
        }

    result = {name: summarize(items) for name, items in sorted(buckets.items())}
    result["breakdown_contract"] = {
        "asset": "dominant U8 component-risk share; ties use U8 order",
        "macro_sleeve": "dominant U8 grouped macro-sleeve component-risk share; ties use fixed sleeve order",
        "country_or_region": "dominant U8 region component-risk share; ties use fixed region order",
        "assignment": "each paired week belongs to exactly one bucket in each breakdown dimension; no full-sample duplication",
    }
    return result


def classify_outcome(statistics: dict[str, Any], *, constraints_pass: bool) -> str:
    """Expose the locked three-outcome E1 decision boundary in the v6 namespace."""
    if set(statistics) != set(METRICS) or not constraints_pass or any(
        value is None or len(value["values"]) < value["mintrl"]["falsify"] for value in statistics.values()
    ):
        return "scope_restricted"
    if any(statistics[metric]["falsify_ucb"] < USEFUL[metric] for metric in METRICS):
        return "falsified_E1_only"
    return "not_falsified_not_validated_E1"


def _statistics(rows: list[dict[str, Any]]) -> dict[str, Any]:
    from lib.l4_b88r4_scientific_engine_v5 import _statistics as statistics_v5

    return statistics_v5(rows)


def derive(container: dict[str, Any], *, config: dict[str, Any]) -> dict[str, Any] | None:
    """Derive v5 state, then replace the rejected v5 decisions and breakdowns."""
    result = _derive_v5(container, config=config)
    if result is None:
        return None
    rows = result["weekly_observations"]
    for row in rows:
        row["breakdown"] = _breakdown_assignment(row)
    side_effects = _side_effects(rows)
    regimes = _regimes(rows)
    constraints_pass = side_effects.get("pass", False) and all(
        value.get("pass", False) for value in result["robustness"].values()
    )
    result["side_effects"] = side_effects
    result["regimes"] = regimes
    result["outcome"] = classify_outcome(result["statistics"], constraints_pass=constraints_pass)
    return result
