"""Pure B8.8R3/v4 L-4 derivation from a normalized U8 container.

This module deliberately accepts no paths and no reporter-supplied portfolio
fields.  A caller supplies the already-bound normalized container and the
locked structural calendar; all targets, executions, costs, PnL and labels
below are derived here.
"""
from __future__ import annotations

import math
from collections import defaultdict
from datetime import date
from statistics import mean, pstdev
from typing import Any, Iterable, Sequence

from lib.l4_b88_scientific_contract_v1 import component_hhi, correlation_n_eff, top_dependency
from lib.l4_b88r_scientific_engine_v2 import actual_statistics
from lib.statistics import symmetric_eigenvalues
from lib.trend_baseline import ANNUALIZATION, CURRENT_EXPENSE_RATIOS, REGIONS, SLEEVES, _cap_and_redistribute

U8 = ("VTI", "VGK", "EWJ", "VWO", "IEF", "TIP", "GLD", "DBC")
U4 = ("VTI", "IEF", "GLD", "DBC")
METRICS = ("ex_ante_hhi_delta", "realized_hhi_delta", "top_dependency_delta", "n_eff_delta")
USEFUL = {"ex_ante_hhi_delta": .05, "realized_hhi_delta": .05, "top_dependency_delta": .10, "n_eff_delta": .5}
SEAL = {"status": "sealed_not_accessed", "accessed": False}

LOCKED_CONFIG = {
    "cutoff_inclusive": "2015-12-31", "span": 60, "gross_limit": .90,
    "weight_cap": .25, "target_volatility": .10, "trade_threshold": .02,
    "commission": .00107, "spread_bps": 25.0, "sell_surcharge_bps": 1.0,
    "borrow_annual": .03,
}


def _finite(value: object) -> bool:
    return type(value) in (int, float) and math.isfinite(value)


def _iso(value: object) -> bool:
    try:
        return isinstance(value, str) and date.fromisoformat(value).isoformat() == value
    except ValueError:
        return False


def _matrix(rows: Sequence[Sequence[float]]) -> bool:
    return bool(rows) and all(len(row) == len(rows[0]) and all(_finite(value) for value in row) for row in rows)


def _direction(value: float) -> int:
    return 1 if value > 0 else -1 if value < 0 else 0


def directional_q(history: Sequence[float]) -> float | None:
    if len(history) != 60 or not all(_finite(value) for value in history):
        return None
    return sum(_direction(value) for value in history) / 60.0


def ewma_covariance_pairwise_complete(rows: Sequence[Sequence[float]], *, span: int = 60) -> list[list[float]] | None:
    """L1's adjust=False EWMA recursion, requiring each pair to be complete."""
    if len(rows) != span or not _matrix(rows):
        return None
    width = len(rows[0]); alpha = 2.0 / (span + 1.0)
    # This initial observation convention is intentionally identical to
    # trend_baseline.load_market, rather than a zero-seeded approximation.
    means = list(rows[0]); second = [[rows[0][i] * rows[0][j] for j in range(width)] for i in range(width)]
    for row in rows[1:]:
        means = [(1.0 - alpha) * means[i] + alpha * row[i] for i in range(width)]
        second = [[(1.0 - alpha) * second[i][j] + alpha * row[i] * row[j] for j in range(width)] for i in range(width)]
    return [[second[i][j] - means[i] * means[j] for j in range(width)] for i in range(width)]


def l1_ewma_cross_check(rows: Sequence[Sequence[float]]) -> bool:
    """Cross-check the engine recursion against the locked L1 market loader."""
    if len(rows) != 60 or not _matrix(rows) or len(rows[0]) != len(U8):
        return False
    # `load_market` is the L1 implementation itself.  Build harmless pre-cutoff
    # levels solely in memory so comparison cannot touch a data container.
    from lib.trend_baseline import load_market
    sessions = [f"2015-10-{day:02d}" for day in range(1, 31)] + [f"2015-11-{day:02d}" for day in range(1, 31)] + ["2015-12-01"]
    levels = [1.0] * len(U8); symbols = []
    for asset, symbol in enumerate(U8):
        records = []
        for index, session in enumerate(sessions):
            if index:
                levels[asset] *= 1.0 + rows[index - 1][asset]
            records.append({"session_date": session, "total_return_close": levels[asset], "availability_timestamp": session + "T23:59:59Z"})
        symbols.append({"symbol": symbol, "records": records})
    try:
        reference = load_market({"cutoff_inclusive": "2015-12-31", "symbols": symbols})["risk_covariance"][60]
    except (KeyError, ValueError):
        return False
    local = ewma_covariance_pairwise_complete(rows)
    return local is not None and all(abs(local[i][j] - reference[i][j]) <= 1e-12 for i in range(8) for j in range(8))


def psd_clip(matrix: Sequence[Sequence[float]]) -> tuple[list[list[float]], float] | None:
    """Deterministic Jacobi eigendecomposition and ex-ante zero clipping."""
    n = len(matrix)
    if not n or any(len(row) != n or not all(_finite(value) for value in row) for row in matrix):
        return None
    if any(abs(matrix[i][j] - matrix[j][i]) > 1e-10 for i in range(n) for j in range(n)):
        return None
    work = [list(row) for row in matrix]; vectors = [[float(i == j) for j in range(n)] for i in range(n)]
    for _ in range(100 * n * n):
        p, q, largest = 0, 0, 0.0
        for i in range(n):
            for j in range(i + 1, n):
                if abs(work[i][j]) > largest:
                    p, q, largest = i, j, abs(work[i][j])
        if largest <= 1e-14:
            break
        angle = .5 * math.atan2(2 * work[p][q], work[q][q] - work[p][p]); c, s = math.cos(angle), math.sin(angle)
        app, aqq, apq = work[p][p], work[q][q], work[p][q]
        work[p][p], work[q][q], work[p][q], work[q][p] = c*c*app - 2*s*c*apq + s*s*aqq, s*s*app + 2*s*c*apq + c*c*aqq, 0.0, 0.0
        for k in range(n):
            if k not in (p, q):
                akp, akq = work[k][p], work[k][q]
                work[k][p] = work[p][k] = c*akp - s*akq; work[k][q] = work[q][k] = s*akp + c*akq
            vkp, vkq = vectors[k][p], vectors[k][q]
            vectors[k][p], vectors[k][q] = c*vkp - s*vkq, s*vkp + c*vkq
    eigenvalues = [work[i][i] for i in range(n)]; clipped_mass = sum(-value for value in eigenvalues if value < 0.0)
    eigenvalues = [max(0.0, value) for value in eigenvalues]
    return ([[sum(vectors[i][k] * eigenvalues[k] * vectors[j][k] for k in range(n)) for j in range(n)] for i in range(n)], clipped_mass)


def _target(q: Sequence[float], covariance: Sequence[Sequence[float]], symbols: Sequence[str]) -> tuple[list[float], dict[str, bool]] | None:
    if not q or len(q) != len(covariance) or len(q) != len(symbols) or sum(abs(value) for value in q) == 0.0:
        return None
    raw = {symbol: LOCKED_CONFIG["gross_limit"] * value / sum(abs(item) for item in q) for symbol, value in zip(symbols, q, strict=True)}
    capped = _cap_and_redistribute(raw | {symbol: 0.0 for symbol in U8 if symbol not in raw}, cap=LOCKED_CONFIG["weight_cap"], gross_limit=LOCKED_CONFIG["gross_limit"])
    weights = [capped[symbol] for symbol in symbols]
    gross = sum(abs(value) for value in weights)
    if gross > LOCKED_CONFIG["gross_limit"]:
        weights = [value * LOCKED_CONFIG["gross_limit"] / gross for value in weights]
    variance = sum(weights[i] * covariance[i][j] * weights[j] for i in range(len(weights)) for j in range(len(weights))) * ANNUALIZATION
    scale = min(1.0, LOCKED_CONFIG["target_volatility"] / math.sqrt(max(variance, 0.0))) if variance > 0 else 1.0
    scaled = [value * scale for value in weights]
    return scaled, {"cap": any(abs(value) >= .25 - 1e-12 for value in weights), "cash": sum(abs(value) for value in scaled) < .9 - 1e-12, "scale_down": scale < 1.0 - 1e-12}


def _costs(weights: Sequence[float], changes: Sequence[float], symbols: Sequence[str], cash_return: float) -> dict[str, float]:
    commission = sum(abs(change) * LOCKED_CONFIG["commission"] for change in changes)
    spread = sum(abs(change) * LOCKED_CONFIG["spread_bps"] / 10_000.0 for change in changes)
    sell = sum(max(-change, 0.0) * LOCKED_CONFIG["sell_surcharge_bps"] / 10_000.0 for change in changes)
    expense = sum(abs(weight) * CURRENT_EXPENSE_RATIOS[symbol] / ANNUALIZATION for weight, symbol in zip(weights, symbols, strict=True))
    borrow = sum(max(-weight, 0.0) * LOCKED_CONFIG["borrow_annual"] / ANNUALIZATION for weight in weights)
    cash = max(0.0, 1.0 - sum(abs(weight) for weight in weights)) * cash_return
    return {"commission": commission, "spread_slippage": spread, "sell_surcharge": sell, "expense_ratio": expense, "short_borrow": borrow, "cash_yield": cash, "total": commission + spread + sell + expense + borrow - cash}


def threshold_changes(target: Sequence[float], current: Sequence[float]) -> list[float]:
    """The locked inclusive 2% threshold, including zero opens/closes."""
    if len(target) != len(current):
        raise ValueError("weight_shape")
    return [wanted - held if abs(wanted - held) + 1e-15 >= LOCKED_CONFIG["trade_threshold"] * abs(held) else 0.0 for wanted, held in zip(target, current, strict=True)]


def _validate_container(container: dict[str, Any], config: dict[str, Any]) -> tuple[list[str], dict[str, list[float]], list[float]] | None:
    if not isinstance(container, dict) or set(container) != {"schema_version", "cutoff_inclusive", "universe", "sessions", "returns", "cash_returns"}:
        return None
    sessions, returns, cash = container["sessions"], container["returns"], container["cash_returns"]
    structural = config.get("u8_sessions")
    if container["schema_version"] != "lily_l4_normalized_container_v1" or container["cutoff_inclusive"] != LOCKED_CONFIG["cutoff_inclusive"] or tuple(container["universe"]) != U8:
        return None
    if not isinstance(sessions, list) or sessions != structural or sessions != sorted(set(sessions)) or not sessions or any(not _iso(value) or date.fromisoformat(value).weekday() >= 5 or value > LOCKED_CONFIG["cutoff_inclusive"] for value in sessions):
        return None
    if not isinstance(returns, dict) or set(returns) != set(U8) or not isinstance(cash, list) or len(cash) != len(sessions) or not all(_finite(value) for value in cash):
        return None
    if any(not isinstance(returns[symbol], list) or len(returns[symbol]) != len(sessions) or not all(_finite(value) for value in returns[symbol]) for symbol in U8):
        return None
    return sessions, returns, cash


def _weekly_decisions(sessions: Sequence[str]) -> list[int]:
    latest: dict[tuple[int, int], int] = {}
    for index, value in enumerate(sessions):
        parsed = date.fromisoformat(value); week = parsed.isocalendar()
        latest[(week.year, week.week)] = index
    return list(latest.values())


def _run_universe(sessions: list[str], returns: dict[str, list[float]], cash: list[float], symbols: tuple[str, ...]) -> dict[int, dict[str, Any]] | None:
    state = [0.0] * len(symbols); output: dict[int, dict[str, Any]] = {}; daily: list[dict[str, float]] = []; scheduled: dict[int, tuple[list[float], dict[str, bool], list[float], list[list[float]], float]] = {}
    decisions = _weekly_decisions(sessions)
    q_history: list[tuple[int, list[float]]] = []
    for decision in decisions:
        if decision < 60 or decision + 21 >= len(sessions):
            continue
        history = [[returns[symbol][index] for symbol in symbols] for index in range(decision - 59, decision + 1)]
        q = [directional_q([row[index] for row in history]) for index in range(len(symbols))]
        covariance = ewma_covariance_pairwise_complete(history)
        if any(value is None for value in q) or covariance is None:
            continue
        clipped = psd_clip(covariance)
        if clipped is None:
            continue
        target = _target(q, clipped[0], symbols)
        if target is None:
            continue
        q_history.append((decision, [float(value) for value in q]))
        if len(q_history) < 52:
            continue
        scheduled[decision + 1] = (target[0], target[1], [float(value) for value in q], clipped[0], clipped[1])
    for index in range(len(sessions)):
        asset_returns = [returns[symbol][index] for symbol in symbols]
        pre_state = list(state)
        gross = sum(weight * asset_return for weight, asset_return in zip(state, asset_returns, strict=True))
        denominator = 1.0 + gross
        drift = [weight * (1.0 + asset_return) / denominator for weight, asset_return in zip(state, asset_returns, strict=True)] if denominator > 0 else list(state)
        changes = [0.0] * len(symbols); flags = {"cap": False, "cash": sum(abs(value) for value in drift) < .9 - 1e-12, "scale_down": False}
        if index in scheduled:
            target, flags, q, covariance, mass = scheduled[index]
            changes = threshold_changes(target, drift)
            # The 2% turnover threshold never overrides a hard portfolio
            # constraint.  A drifted holding above a cap (or a drifted gross
            # exposure above its limit) is therefore fully repaired here.
            # The same rule applies where partial threshold trades themselves
            # would create a hard-limit breach.
            proposed = [held + change for held, change in zip(drift, changes, strict=True)]
            if any(abs(value) > LOCKED_CONFIG["weight_cap"] + 1e-12 for value in proposed) or sum(abs(value) for value in proposed) > LOCKED_CONFIG["gross_limit"] + 1e-12:
                changes = [wanted - held for wanted, held in zip(target, drift, strict=True)]
            state = [current + change for current, change in zip(drift, changes, strict=True)]
            decision = index - 1
            past_q = [values for decision_index, values in q_history if decision_index <= decision][-52:]
            realized = [[returns[symbol][future] for symbol in symbols] for future in range(index + 1, index + 21)]
            output[decision] = {"decision_date": sessions[decision], "execution_date": sessions[index], "execution_index": index, "realized_dates": sessions[index + 1:index + 21], "q": q, "q_history": past_q, "covariance": covariance, "covariance_clipped_mass": mass, "weights": list(state), "changes": changes, "costs": _costs(state, changes, symbols, cash[index]), "realized_returns": realized, "flags": flags, "gross": sum(abs(value) for value in drift)}
        else:
            state = drift
        daily_cost = _costs(state, changes, symbols, cash[index])
        contribution = {symbol: pre_state[position] * asset_returns[position] - abs(pre_state[position]) * CURRENT_EXPENSE_RATIOS[symbol] / ANNUALIZATION - max(-pre_state[position], 0.0) * LOCKED_CONFIG["borrow_annual"] / ANNUALIZATION for position, symbol in enumerate(symbols)}
        contribution[symbols[0]] += -daily_cost["commission"] - daily_cost["spread_slippage"] - daily_cost["sell_surcharge"] + daily_cost["cash_yield"]
        daily.append(contribution)
    return {"weekly": output, "daily": daily}


def _realized_hhi(rows: Sequence[Sequence[float]], weights: Sequence[float]) -> float | None:
    if len(rows) != 20:
        return None
    width = len(weights); centres = [mean(row[i] for row in rows) for i in range(width)]
    covariance = [[sum((row[i] - centres[i]) * (row[j] - centres[j]) for row in rows) / (len(rows) - 1) for j in range(width)] for i in range(width)]
    clipped = psd_clip(covariance)
    return component_hhi(weights, clipped[0]) if clipped else None


def _prior_volatility_tercile(returns: dict[str, list[float]], decision: int) -> str:
    """L1's daily median-volatility tercile using only earlier daily medians."""
    medians=[]
    for index in range(59, decision + 1):
        vols=[pstdev(returns[symbol][index-59:index+1]) * math.sqrt(ANNUALIZATION) for symbol in U8]
        medians.append(sorted(vols)[len(vols)//2])
    if len(medians) <= 756:
        return "warmup_unclassified"
    prior=sorted(medians[:-1]); current=medians[-1]
    def percentile(probability: float) -> float:
        position=(len(prior)-1)*probability; low=math.floor(position); high=math.ceil(position)
        return prior[low] if low == high else prior[low]*(high-position)+prior[high]*(position-low)
    low, high=percentile(1/3), percentile(2/3)
    return "low" if current <= low else "high" if current >= high else "middle"


def derive(container: dict[str, Any], *, config: dict[str, Any]) -> dict[str, Any] | None:
    """Return the complete derived result, or fail closed for malformed input."""
    validated = _validate_container(container, config)
    if validated is None:
        return None
    sessions, returns, cash = validated; run4 = _run_universe(sessions, returns, cash, U4); run8 = _run_universe(sessions, returns, cash, U8)
    if run4 is None or run8 is None:
        return None
    u4, u8 = run4["weekly"], run8["weekly"]
    common = sorted(set(u4) & set(u8)); observations = []
    for common_index, decision in enumerate(common):
        left, right = u4[decision], u8[decision]
        if left["execution_date"] != right["execution_date"] or left["realized_dates"] != right["realized_dates"] or len(left["realized_dates"]) != 20:
            return None
        h4, h8 = component_hhi(left["weights"], left["covariance"]), component_hhi(right["weights"], right["covariance"])
        r4, r8 = _realized_hhi(left["realized_returns"], left["weights"]), _realized_hhi(right["realized_returns"], right["weights"])
        n4, n8 = correlation_n_eff(left["q_history"]), correlation_n_eff(right["q_history"])
        d4, d8 = top_dependency(left["weights"], left["covariance"], U4), top_dependency(right["weights"], right["covariance"], U8)
        if None in (h4, h8, r4, r8, n4, n8, d4, d8):
            return None
        signs = right["q"][:4]; history=[entry["q_u8"] for entry in observations] + [right["q"]]
        states=["up" if value >= .20 else "down" if value <= -.20 else "neutral" for value in right["q"]]
        whipsaw=sum(sum(a != b for a,b in zip([_direction(item[asset]) for item in history[-20:] if _direction(item[asset])], [_direction(item[asset]) for item in history[-20:] if _direction(item[asset])][1:])) >= 4 and abs(right["q"][asset]) < .20 for asset in range(8))
        up, down = states.count("up"), states.count("down")
        global_state = "broad_uptrend" if up >= 4 and down < 2 else "broad_downtrend" if down >= 4 and up < 2 else "whipsaw" if whipsaw >= 4 else "mixed"
        equity = "neutral_present" if any(value == 0 for value in signs) else "all_four_equity_signs_same_nonzero" if len({_direction(value) for value in signs}) == 1 else "mixed_signs"
        end = u8[common[common_index + 1]]["execution_index"] if common_index + 1 < len(common) else len(sessions)
        pnl4 = {symbol: sum(run4["daily"][day][symbol] for day in range(left["execution_index"], end)) for symbol in U4}; pnl8 = {symbol: sum(run8["daily"][day][symbol] for day in range(right["execution_index"], end)) for symbol in U8}
        observations.append({"date": left["decision_date"], "timing": {"decision_date": left["decision_date"], "execution_date": left["execution_date"], "realized_dates": left["realized_dates"]}, "ex_ante_hhi_delta": h4-h8, "realized_hhi_delta": r4-r8, "top_dependency_delta": d4-d8, "n_eff_delta": n8[0]-n4[0], "costs_u4": left["costs"], "costs_u8": right["costs"], "changes_u4": left["changes"], "changes_u8": right["changes"], "gross_u4": left["gross"], "gross_u8": right["gross"], "flags_u4": left["flags"], "flags_u8": right["flags"], "q_u8": right["q"], "net_pnl_contribution_u4": pnl4, "net_pnl_contribution_u8": pnl8, "state":{"u4":{"weights":left["weights"],"covariance":left["covariance"],"hhi":h4},"u8":{"weights":right["weights"],"covariance":right["covariance"],"hhi":h8}}, "regime": {"global_state": global_state, "volatility_tercile":_prior_volatility_tercile(returns, decision), "equity_synchronization": equity}})
    statistics = _statistics(observations); side_effects = _side_effects(observations); robustness = _robustness(observations)
    return {"weekly_observations": observations, "statistics": statistics, "robustness": robustness, "side_effects": side_effects, "regimes": _regimes(observations), "outcome": classify_outcome(statistics, constraints_pass=side_effects.get("evaluable", False))}


def _statistics(rows: list[dict[str, Any]]) -> dict[str, Any]:
    return {metric: actual_statistics([row[metric] for row in rows], metric) for metric in METRICS} if len(rows) >= 6 else {}


def classify_outcome(statistics: dict[str, Any], *, constraints_pass: bool) -> str:
    """The locked E1 ordering: scope restriction precedes falsification."""
    if set(statistics) != set(METRICS) or not constraints_pass or any(value is None or len(value["values"]) < value["mintrl"]["falsify"] for value in statistics.values()):
        return "scope_restricted"
    if any(statistics[metric]["falsify_ucb"] < USEFUL[metric] for metric in METRICS):
        return "falsified_E1_only"
    return "not_falsified_not_validated_E1"


def _side_effects(rows: list[dict[str, Any]]) -> dict[str, Any]:
    if not rows or any(row["gross_u4"] <= 0 or row["gross_u8"] <= 0 for row in rows):
        return {"evaluable": False}
    turnover = [sum(abs(value) for row in rows for value in row["changes_u4"]), sum(abs(value) for row in rows for value in row["changes_u8"])]
    cost4, cost8 = sum(row["costs_u4"]["total"] for row in rows), sum(row["costs_u8"]["total"] for row in rows)
    gross4, gross8 = sum(row["gross_u4"] for row in rows), sum(row["gross_u8"] for row in rows)
    return {"evaluable": cost4 != 0 and gross4 != 0 and gross8 != 0 and turnover[0] != 0, "turnover_relative_increase": (turnover[1]/gross8)/(turnover[0]/gross4)-1 if turnover[0] else None, "cost_relative_increase": (cost8/gross8)/(cost4/gross4)-1 if cost4 else None, "flag_frequency_delta_percentage_points": {flag: 100*(sum(row["flags_u8"][flag] for row in rows)-sum(row["flags_u4"][flag] for row in rows))/len(rows) for flag in ("cap", "cash", "scale_down")}}


def _robustness(rows: list[dict[str, Any]]) -> dict[str, Any]:
    totals = {symbol: sum(row["net_pnl_contribution_u8"][symbol] for row in rows) for symbol in U8} if rows else {}
    best = min(U8, key=lambda symbol: (-totals[symbol], U8.index(symbol))) if totals else None
    original = mean(row["ex_ante_hhi_delta"] for row in rows) if rows else None
    def removed(row, symbols, removed):
        keep=[index for index,symbol in enumerate(symbols) if symbol != removed]
        if not keep: return None
        weights=[row["weights_" + ("u4" if symbols == U4 else "u8")][index] for index in keep] if "weights_u4" in row else None
        return keep, weights
    # The weekly output carries no reporter-owned weights; retain derivable
    # component-risk removals from precomputed deltas only when not available.
    # The run attaches weight/covariance evidence below for this calculation.
    def hhi_after(row, universe, removed_symbol):
        prefix="u4" if universe == U4 else "u8"; keep=[i for i,s in enumerate(universe) if s != removed_symbol]
        if not keep: return None
        weights=[row["state"][prefix]["weights"][i] for i in keep]; gross=sum(abs(x) for x in weights)
        if gross == 0: return None
        weights=[.9*x/gross for x in weights]; covariance=[[row["state"][prefix]["covariance"][i][j] for j in keep] for i in keep]
        return component_hhi(weights,covariance)
    market_values=[]
    if best:
        for row in rows:
            h8=hhi_after(row,U8,best); h4=hhi_after(row,U4,best) if best in U4 else row["state"]["u4"]["hhi"]
            if h4 is None or h8 is None: market_values=[]; break
            market_values.append(h4-h8)
    market_mean=mean(market_values) if market_values else None
    episodes=[]
    for asset,symbol in enumerate(U8):
        current=None; neutral=0
        for index,row in enumerate(rows):
            sign=_direction(row["q_u8"][asset])
            if sign == 0:
                neutral += 1
                if current is not None and neutral >= 2:
                    current["end"]=index; episodes.append(current); current=None
                continue
            neutral=0
            if current is None or current["sign"] != sign:
                if current is not None: current["end"]=index-1; episodes.append(current)
                current={"symbol":symbol,"asset":asset,"sign":sign,"start":index,"end":len(rows)-1}
        if current is not None: episodes.append(current)
    for item in episodes:
        item["net_pnl"]=sum(rows[index]["net_pnl_contribution_u8"][item["symbol"]] for index in range(item["start"],item["end"]+1))
    episode=min(episodes,key=lambda item:(-item["net_pnl"],item["asset"],item["start"])) if episodes else None
    retained=[row["ex_ante_hhi_delta"] for index,row in enumerate(rows) if episode is None or not episode["start"] <= index <= episode["end"]]
    required=49
    return {"best_market":{"selected_symbol":best,"selected_net_pnl":totals.get(best) if best else None,"mean_after_removal":market_mean,"threshold":.025,"retained_fraction":None if original in (None,0) else market_mean/original if market_mean is not None else None,"pass":bool(original and market_mean is not None and market_mean >= .025 and market_mean >= .5*original)},"best_trend_episode":{"selected_symbol":None if episode is None else episode["symbol"],"start_date":None if episode is None else rows[episode["start"]]["date"],"end_date":None if episode is None else rows[episode["end"]]["date"],"selected_net_pnl":None if episode is None else episode["net_pnl"],"remaining_observations":len(retained),"mean_after_removal":mean(retained) if retained else None,"minimum_required":required,"pass":bool(original and retained and len(retained)>=required and mean(retained)>=.025 and mean(retained)>=.5*original)}}


def _regimes(rows: list[dict[str, Any]]) -> dict[str, Any]:
    buckets: dict[str, list[dict[str, Any]]] = {name:[] for name in ("global_state:broad_uptrend","global_state:broad_downtrend","global_state:whipsaw","global_state:mixed","volatility_tercile:warmup_unclassified","volatility_tercile:low","volatility_tercile:middle","volatility_tercile:high","equity_synchronization:all_four_equity_signs_same_nonzero","equity_synchronization:mixed_signs","equity_synchronization:neutral_present","subperiod:2007-02-05_to_2011-06-30","subperiod:2011-07-01_to_2015-12-31","crisis:GFC","crisis:COVID_sealed","crisis:inflation_2022_sealed")}
    for symbol in U8:
        buckets.setdefault("asset:" + symbol, []); buckets.setdefault("macro_sleeve:" + SLEEVES[symbol], []); buckets.setdefault("country_or_region:" + REGIONS[symbol], [])
    for row in rows:
        buckets["global_state:" + row["regime"]["global_state"]].append(row); buckets["volatility_tercile:" + row["regime"]["volatility_tercile"]].append(row); buckets["equity_synchronization:" + row["regime"]["equity_synchronization"]].append(row)
        buckets["subperiod:" + ("2007-02-05_to_2011-06-30" if row["date"] <= "2011-06-30" else "2011-07-01_to_2015-12-31")].append(row)
        for symbol in U8:
            buckets["asset:" + symbol].append(row); buckets["macro_sleeve:" + SLEEVES[symbol]].append(row); buckets["country_or_region:" + REGIONS[symbol]].append(row)
        if "2007-07-01" <= row["date"] <= "2009-06-30": buckets["crisis:GFC"].append(row)
    return {name: {"weekly_observations": len(items), "metric_statistics": _statistics(items), "funded_by_metric": {metric: bool(_statistics(items).get(metric) and len(items) >= _statistics(items)[metric]["mintrl"]["falsify"]) for metric in METRICS}, "underfunded": len(items) < 6} for name, items in sorted(buckets.items())}
