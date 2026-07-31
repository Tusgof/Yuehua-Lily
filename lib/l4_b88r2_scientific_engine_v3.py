"""Pure, in-memory B8.8R2 weekly evidence derivation; it never opens a path."""
from __future__ import annotations

import math
from statistics import mean
from typing import Any, Sequence

from lib.l4_b88_scientific_contract_v1 import METRICS, U4, U8, USEFUL, component_hhi, correlation_n_eff, top_dependency
from lib.l4_b88r_scientific_engine_v2 import Z95, actual_statistics, daily_costs, directional_q, ewma_covariance, timing_is_matched


def _finite(value: object) -> bool:
    return type(value) in (int, float) and math.isfinite(value)


def _vector(value: object, width: int) -> bool:
    return isinstance(value, list) and len(value) == width and all(_finite(x) for x in value)


def _matrix(value: object, rows: int, width: int) -> bool:
    return isinstance(value, list) and len(value) == rows and all(_vector(row, width) for row in value)


def _same(left: Sequence[float], right: Sequence[float], tolerance: float = 1e-12) -> bool:
    return len(left) == len(right) and all(abs(x-y) <= tolerance for x, y in zip(left, right))


def _same_matrix(left: Sequence[Sequence[float]], right: Sequence[Sequence[float]]) -> bool:
    return len(left) == len(right) and all(_same(a, b) for a, b in zip(left, right))


def _sample_covariance(rows: Sequence[Sequence[float]]) -> list[list[float]] | None:
    if len(rows) < 2 or not rows or any(not _vector(row, len(rows[0])) for row in rows): return None
    width = len(rows[0]); centres = [mean(row[i] for row in rows) for i in range(width)]
    return [[sum((row[i]-centres[i])*(row[j]-centres[j]) for row in rows)/(len(rows)-1) for j in range(width)] for i in range(width)]


def _jacobi_psd(matrix: Sequence[Sequence[float]]) -> list[list[float]] | None:
    """Deterministically clip a symmetric covariance matrix without third-party code."""
    n = len(matrix)
    if not n or any(len(row) != n or not all(_finite(x) for x in row) for row in matrix): return None
    work = [list(row) for row in matrix]
    if any(abs(work[i][j]-work[j][i]) > 1e-10 for i in range(n) for j in range(n)): return None
    vectors = [[1.0 if i == j else 0.0 for j in range(n)] for i in range(n)]
    for _ in range(100*n*n):
        p, q, largest = 0, 0, 0.0
        for i in range(n):
            for j in range(i+1, n):
                if abs(work[i][j]) > largest: p, q, largest = i, j, abs(work[i][j])
        if largest <= 1e-14: break
        angle = .5*math.atan2(2*work[p][q], work[q][q]-work[p][p]); c, s = math.cos(angle), math.sin(angle)
        app, aqq, apq = work[p][p], work[q][q], work[p][q]
        work[p][p], work[q][q], work[p][q], work[q][p] = c*c*app-2*s*c*apq+s*s*aqq, s*s*app+2*s*c*apq+c*c*aqq, 0.0, 0.0
        for k in range(n):
            if k not in (p, q):
                aik, akq = work[k][p], work[k][q]
                work[k][p] = work[p][k] = c*aik-s*akq; work[k][q] = work[q][k] = s*aik+c*akq
            vip, viq = vectors[k][p], vectors[k][q]
            vectors[k][p], vectors[k][q] = c*vip-s*viq, s*vip+c*viq
    values = [max(0.0, work[i][i]) for i in range(n)]
    return [[sum(vectors[i][k]*values[k]*vectors[j][k] for k in range(n)) for j in range(n)] for i in range(n)]


def _realized_hhi(returns: Sequence[Sequence[float]], weights: Sequence[float]) -> float | None:
    covariance = _sample_covariance(returns)
    clipped = _jacobi_psd(covariance) if covariance is not None else None
    return component_hhi(weights, clipped) if clipped is not None else None


RAW_FIELDS = frozenset(("timing", "returns_history_u4", "returns_history_u8", "q_u4", "q_u8", "covariance_u4", "covariance_u8", "q_history_u4", "q_history_u8", "weights_u4", "weights_u8", "changes_u4", "changes_u8", "cash_return", "realized_returns_u4", "realized_returns_u8", "net_pnl_contribution_u4", "net_pnl_contribution_u8", "regime"))


def derive_weekly_observation(row: dict[str, Any]) -> dict[str, Any] | None:
    """Recompute every weekly metric from closed-world, in-memory raw evidence."""
    if not isinstance(row, dict) or set(row) != RAW_FIELDS or not timing_is_matched(row["timing"]): return None
    if not _matrix(row["returns_history_u4"], 60, len(U4)) or not _matrix(row["returns_history_u8"], 60, len(U8)): return None
    if not _vector(row["q_u4"], len(U4)) or not _vector(row["q_u8"], len(U8)) or not _matrix(row["covariance_u4"], len(U4), len(U4)) or not _matrix(row["covariance_u8"], len(U8), len(U8)): return None
    if not _matrix(row["q_history_u4"], 52, len(U4)) or not _matrix(row["q_history_u8"], 52, len(U8)) or not _vector(row["weights_u4"], len(U4)) or not _vector(row["weights_u8"], len(U8)) or not _vector(row["changes_u4"], len(U4)) or not _vector(row["changes_u8"], len(U8)) or not _finite(row["cash_return"]): return None
    if not _matrix(row["realized_returns_u4"], 20, len(U4)) or not _matrix(row["realized_returns_u8"], 20, len(U8)): return None
    if not isinstance(row["net_pnl_contribution_u4"], dict) or not isinstance(row["net_pnl_contribution_u8"], dict) or set(row["net_pnl_contribution_u4"]) != set(U4) or set(row["net_pnl_contribution_u8"]) != set(U8) or not all(_finite(x) for x in tuple(row["net_pnl_contribution_u4"].values())+tuple(row["net_pnl_contribution_u8"].values())): return None
    if not isinstance(row["regime"], dict) or set(row["regime"]) != {"global_state", "volatility_tercile", "equity_synchronization"} or not all(isinstance(x, str) and x for x in row["regime"].values()): return None
    expected_q4 = [directional_q([item[i] for item in row["returns_history_u4"]]) for i in range(len(U4))]
    expected_q8 = [directional_q([item[i] for item in row["returns_history_u8"]]) for i in range(len(U8))]
    expected_cov4 = ewma_covariance(row["returns_history_u4"]); expected_cov8 = ewma_covariance(row["returns_history_u8"])
    if None in expected_q4+expected_q8 or expected_cov4 is None or expected_cov8 is None or not _same(row["q_u4"], expected_q4) or not _same(row["q_u8"], expected_q8) or not _same_matrix(row["covariance_u4"], expected_cov4[0]) or not _same_matrix(row["covariance_u8"], expected_cov8[0]): return None
    h4, h8 = component_hhi(row["weights_u4"], row["covariance_u4"]), component_hhi(row["weights_u8"], row["covariance_u8"])
    realized4, realized8 = _realized_hhi(row["realized_returns_u4"], row["weights_u4"]), _realized_hhi(row["realized_returns_u8"], row["weights_u8"])
    n4, n8 = correlation_n_eff(row["q_history_u4"]), correlation_n_eff(row["q_history_u8"])
    d4, d8 = top_dependency(row["weights_u4"], row["covariance_u4"], U4), top_dependency(row["weights_u8"], row["covariance_u8"], U8)
    if None in (h4, h8, realized4, realized8, n4, n8, d4, d8): return None
    return {"date": row["timing"]["decision_date"], "ex_ante_hhi_delta": h4-h8, "realized_hhi_delta": realized4-realized8, "top_dependency_delta": d4-d8, "n_eff_delta": n8[0]-n4[0], "costs_u4": daily_costs(row["weights_u4"], row["changes_u4"], row["cash_return"]), "costs_u8": daily_costs(row["weights_u8"], row["changes_u8"], row["cash_return"]), "gross_u4": sum(abs(x-y) for x, y in zip(row["weights_u4"], row["changes_u4"])), "gross_u8": sum(abs(x-y) for x, y in zip(row["weights_u8"], row["changes_u8"])), "flags_u4": {"cap": any(abs(x) >= .25-1e-12 for x in row["weights_u4"]), "cash": sum(abs(x) for x in row["weights_u4"]) < .9-1e-12, "scale_down": sum(abs(x) for x in row["weights_u4"]) < .9-1e-12}, "flags_u8": {"cap": any(abs(x) >= .25-1e-12 for x in row["weights_u8"]), "cash": sum(abs(x) for x in row["weights_u8"]) < .9-1e-12, "scale_down": sum(abs(x) for x in row["weights_u8"]) < .9-1e-12}, "covariance_clipped_mass": n4[1]+n8[1], "net_pnl_contribution_u4": row["net_pnl_contribution_u4"], "net_pnl_contribution_u8": row["net_pnl_contribution_u8"], "regime": row["regime"]}


def metric_statistics(rows: Sequence[dict[str, Any]]) -> dict[str, dict[str, Any]] | None:
    observed = [derive_weekly_observation(row) for row in rows]
    if not observed or any(row is None for row in observed): return None
    result = {metric: actual_statistics([row[metric] for row in observed], metric) for metric in METRICS}
    return None if any(value is None for value in result.values()) else result


def funded(statistics: dict[str, dict[str, Any]]) -> bool:
    return set(statistics) == set(METRICS) and all(len(value["values"]) >= value["mintrl"]["falsify"] for value in statistics.values())


def classify_outcome(statistics: dict[str, dict[str, Any]], *, constraints_evaluable: bool, constraints_pass: bool) -> str:
    if not constraints_evaluable or not funded(statistics): return "scope_restricted"
    if not constraints_pass or any(statistics[metric]["falsify_ucb"] < USEFUL[metric] for metric in METRICS): return "falsified_E1_only"
    return "not_falsified_not_validated_E1"


def side_effects(rows: Sequence[dict[str, Any]]) -> dict[str, Any] | None:
    observed = [derive_weekly_observation(row) for row in rows]
    if not observed or any(row is None or row["gross_u4"] <= 0 or row["gross_u8"] <= 0 for row in observed): return None
    def relative(numerator: float, denominator: float) -> float | None: return None if denominator == 0 else (numerator-denominator)/denominator
    cost4, cost8 = sum(row["costs_u4"]["total"] for row in observed), sum(row["costs_u8"]["total"] for row in observed)
    gross4, gross8 = sum(row["gross_u4"] for row in observed), sum(row["gross_u8"] for row in observed)
    turnover4, turnover8 = sum(sum(abs(x) for x in raw["changes_u4"]) for raw in rows), sum(sum(abs(x) for x in raw["changes_u8"]) for raw in rows)
    values = {"turnover_relative_increase": relative(turnover8/gross8, turnover4/gross4), "cost_relative_increase": relative(cost8/gross8, cost4/gross4), "flag_frequency_delta_percentage_points": {name: 100*(sum(row["flags_u8"][name] for row in observed)-sum(row["flags_u4"][name] for row in observed))/len(observed) for name in ("cap", "cash", "scale_down")}}
    if values["turnover_relative_increase"] is None or values["cost_relative_increase"] is None: return None
    values["pass"] = values["turnover_relative_increase"] <= .2 and values["cost_relative_increase"] <= .2 and all(value <= 10 for value in values["flag_frequency_delta_percentage_points"].values())
    return values


def constraints(rows: Sequence[dict[str, Any]]) -> dict[str, Any] | None:
    observed = [derive_weekly_observation(row) for row in rows]
    if not observed or any(row is None for row in observed): return None
    dates = [row["date"] for row in observed]
    cap = all(all(abs(weight) <= .25+1e-12 for weight in raw[weights]) for raw in rows for weights in ("weights_u4", "weights_u8"))
    gross = all(sum(abs(weight) for weight in raw[weights]) <= .9+1e-12 for raw in rows for weights in ("weights_u4", "weights_u8"))
    return {"evaluable": True, "unique_sorted_dates": dates == sorted(set(dates)), "weight_cap": cap, "gross_cap": gross, "pass": dates == sorted(set(dates)) and cap and gross}


def robustness(rows: Sequence[dict[str, Any],], statistics: dict[str, dict[str, Any]]) -> dict[str, Any] | None:
    observed = [derive_weekly_observation(row) for row in rows]
    if not observed or any(row is None for row in observed) or "ex_ante_hhi_delta" not in statistics: return None
    market_totals = {symbol: sum(row["net_pnl_contribution_u8"][symbol] for row in observed) for symbol in U8}
    market = min(U8, key=lambda symbol: (-market_totals[symbol], U8.index(symbol)))
    original = mean(row["ex_ante_hhi_delta"] for row in observed)
    def removed_hhi(raw: dict[str, Any], symbols: Sequence[str], weights: str, covariance: str, remove: str) -> float | None:
        keep = [i for i, symbol in enumerate(symbols) if symbol != remove]
        if not keep: return None
        vector = [raw[weights][i] for i in keep]; total = sum(abs(value) for value in vector)
        if total == 0: return None
        vector = [value*.9/total for value in vector]
        matrix = [[raw[covariance][i][j] for j in keep] for i in keep]
        return component_hhi(vector, matrix)
    market_values = []
    for raw in rows:
        h8 = removed_hhi(raw, U8, "weights_u8", "covariance_u8", market)
        h4 = removed_hhi(raw, U4, "weights_u4", "covariance_u4", market) if market in U4 else component_hhi(raw["weights_u4"], raw["covariance_u4"])
        if h4 is None or h8 is None: return None
        market_values.append(h4-h8)
    market_mean = mean(market_values)
    # The selected episode is a contiguous non-zero signed-q run, with one neutral bridge.
    episodes = []
    for index, symbol in enumerate(U8):
        start = None; sign = None; neutral = 0; contribution = 0.0
        for row_index, raw in enumerate(rows):
            value = raw["q_u8"][index]; current = 1 if value > 0 else -1 if value < 0 else 0
            if current and (sign is None or current == sign or (neutral <= 1 and sign == current)):
                if start is None: start = row_index; sign = current
                neutral = 0; contribution += raw["net_pnl_contribution_u8"][symbol]; continue
            if current == 0 and start is not None and neutral == 0:
                neutral = 1; contribution += raw["net_pnl_contribution_u8"][symbol]; continue
            if start is not None: episodes.append((contribution, index, start, row_index-1))
            start, sign, neutral, contribution = (row_index, current, 0, raw["net_pnl_contribution_u8"][symbol]) if current else (None, None, 0, 0.0)
        if start is not None: episodes.append((contribution, index, start, len(rows)-1))
    if not episodes: return None
    contribution, asset_index, start, end = min(episodes, key=lambda item: (-item[0], item[1], item[2]))
    retained = [row["ex_ante_hhi_delta"] for i, row in enumerate(observed) if not start <= i <= end]
    required = statistics["ex_ante_hhi_delta"]["mintrl"]["falsify"]
    episode_mean = mean(retained) if retained else None
    return {"best_market": {"selected_symbol": market, "selected_net_pnl": market_totals[market], "mean_after_removal": market_mean, "pass": original > 0 and market_mean >= .025 and market_mean >= .5*original}, "best_trend_episode": {"selected_symbol": U8[asset_index], "start_date": observed[start]["date"], "end_date": observed[end]["date"], "selected_net_pnl": contribution, "remaining_observations": len(retained), "mean_after_removal": episode_mean, "pass": episode_mean is not None and len(retained) >= required and original > 0 and episode_mean >= .025 and episode_mean >= .5*original}}


def regime_funding(rows: Sequence[dict[str, Any]], statistics: dict[str, dict[str, Any]]) -> dict[str, Any] | None:
    observed = [derive_weekly_observation(row) for row in rows]
    if not observed or any(row is None for row in observed) or set(statistics) != set(METRICS): return None
    buckets: dict[str, list[int]] = {}
    for index, row in enumerate(observed):
        for name, value in row["regime"].items(): buckets.setdefault(f"{name}:{value}", []).append(index)
        buckets.setdefault("subperiod:2007-02-05_to_2011-06-30" if row["date"] <= "2011-06-30" else "subperiod:2011-07-01_to_2015-12-31", []).append(index)
    return {name: {"weekly_observations": len(indices), "funded_by_metric": {metric: len(indices) >= statistics[metric]["mintrl"]["falsify"] for metric in METRICS}} for name, indices in sorted(buckets.items())}
