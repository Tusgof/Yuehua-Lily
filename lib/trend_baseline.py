"""Locked L-1 directional-count baseline and diagnostic reporting kernel."""

from __future__ import annotations

import math
from collections import defaultdict
from dataclasses import dataclass
from datetime import date
from statistics import mean, pstdev
from typing import Any

from lib.statistics import (
    deflated_sharpe_ratio,
    effective_independent_bets_from_eigenvalues,
    effective_sample_length,
    newey_west_t_statistic,
    probabilistic_sharpe_ratio,
    raw_kurtosis_population,
    sample_autocorrelation,
    sharpe_ratio,
    skewness_population,
    symmetric_eigenvalues,
)


ANNUALIZATION = 252
ASSETS = ("VTI", "VGK", "EWJ", "VWO", "IEF", "TIP", "GLD", "DBC")
SLEEVES = {
    "VTI": "US_equity", "VGK": "Europe_equity", "EWJ": "Japan_equity",
    "VWO": "emerging_markets_equity", "IEF": "intermediate_US_Treasuries",
    "TIP": "US_inflation_linked_bonds", "GLD": "gold", "DBC": "broad_commodities",
}
REGIONS = {
    "VTI": "United_States", "VGK": "Europe", "EWJ": "Japan", "VWO": "Emerging_markets",
    "IEF": "United_States", "TIP": "United_States", "GLD": "Global", "DBC": "Global",
}
CURRENT_EXPENSE_RATIOS = {
    "VTI": 0.0003, "VGK": 0.0006, "EWJ": 0.0050, "VWO": 0.0007,
    "IEF": 0.0015, "TIP": 0.0018, "GLD": 0.0040, "DBC": 0.0085,
}


@dataclass(frozen=True)
class CostModel:
    spread_bps: float
    borrow_annual: float
    commission: float = 0.00107
    sell_surcharge_bps: float = 1.0


@dataclass
class Trial:
    trial_id: str
    lookback: int
    returns_gross: list[float]
    returns_net: list[float]
    benchmark_net: list[float]
    dates: list[str]
    asset_contributions: dict[str, list[float]]
    asset_returns: dict[str, list[float]]
    signals: dict[str, dict[str, float]]
    weights: list[dict[str, float]]
    trades: int
    turnover: float
    costs: dict[str, float]
    covariance_clipped_mass: float


def load_market(payload: dict[str, Any]) -> dict[str, Any]:
    if payload.get("cutoff_inclusive") != "2015-12-31":
        raise ValueError("dataset cutoff does not match the locked falsification boundary")
    by_symbol = {item["symbol"]: item for item in payload.get("symbols", [])}
    if tuple(by_symbol) != ASSETS:
        raise ValueError("dataset symbol order does not match the locked universe")
    series: dict[str, dict[str, float]] = {}
    availability: dict[str, dict[str, str]] = {}
    for symbol in ASSETS:
        records = by_symbol[symbol]["records"]
        if any(row["session_date"] > "2015-12-31" for row in records):
            raise ValueError("validation data must remain sealed")
        series[symbol] = {row["session_date"]: float(row["total_return_close"]) for row in records}
        availability[symbol] = {row["session_date"]: row["availability_timestamp"] for row in records}
    dates = sorted(set.intersection(*(set(series[symbol]) for symbol in ASSETS)))
    returns = {symbol: {} for symbol in ASSETS}
    for symbol in ASSETS:
        previous: float | None = None
        for session in dates:
            level = series[symbol][session]
            if previous is not None:
                returns[symbol][session] = level / previous - 1.0
            previous = level
    risk_covariance: dict[int, list[list[float]]] = {}
    alpha = 2.0 / 61.0
    means = [0.0] * len(ASSETS)
    second = [[0.0] * len(ASSETS) for _ in ASSETS]
    for index in range(1, len(dates)):
        row = [returns[symbol][dates[index]] for symbol in ASSETS]
        if index == 1:
            means = list(row)
            second = [[row[i] * row[j] for j in range(len(row))] for i in range(len(row))]
        else:
            means = [(1.0 - alpha) * means[i] + alpha * row[i] for i in range(len(row))]
            second = [
                [(1.0 - alpha) * second[i][j] + alpha * row[i] * row[j] for j in range(len(row))]
                for i in range(len(row))
            ]
        if index >= 60:
            risk_covariance[index] = [
                [second[i][j] - means[i] * means[j] for j in range(len(ASSETS))]
                for i in range(len(ASSETS))
            ]
    return {"dates": dates, "returns": returns, "availability": availability, "risk_covariance": risk_covariance}


def run_trial(
    market: dict[str, Any],
    *,
    trial_id: str,
    lookback: int,
    cost_model: CostModel,
) -> Trial:
    strategy = _run_branch(market, lookback=lookback, cost_model=cost_model, always_long=False)
    benchmark = _run_branch(market, lookback=lookback, cost_model=cost_model, always_long=True)
    return Trial(
        trial_id=trial_id,
        lookback=lookback,
        benchmark_net=benchmark["net"],
        **strategy,
    )


def _run_branch(
    market: dict[str, Any],
    *,
    lookback: int,
    cost_model: CostModel,
    always_long: bool,
) -> dict[str, Any]:
    dates: list[str] = market["dates"]
    returns: dict[str, dict[str, float]] = market["returns"]
    weekly_decisions = _weekly_last_sessions(dates)
    signals: dict[str, dict[str, float]] = {}
    scheduled_targets: dict[int, dict[str, float]] = {}
    covariance_clipped_mass = 0.0
    for index in weekly_decisions:
        if index + 1 >= len(dates):
            continue
        target, signal, clipped = _target_at(
            dates, returns, covariance=market["risk_covariance"].get(index),
            index=index, lookback=lookback, always_long=always_long
        )
        if target is None:
            continue
        decision_date = dates[index]
        if any(market["availability"][symbol][decision_date][:10] > decision_date for symbol in ASSETS):
            raise ValueError("availability timestamp is after the decision session")
        signals[decision_date] = signal
        scheduled_targets[index + 1] = target
        covariance_clipped_mass += clipped

    start = dates.index("2007-02-05")
    end = dates.index("2015-12-31")
    weights = {symbol: 0.0 for symbol in ASSETS}
    gross_rows: list[float] = []
    net_rows: list[float] = []
    row_dates: list[str] = []
    weight_rows: list[dict[str, float]] = []
    contributions = {symbol: [] for symbol in ASSETS}
    opened_asset_returns = {symbol: [] for symbol in ASSETS}
    costs = {"commission": 0.0, "spread_slippage": 0.0, "sell_surcharge": 0.0,
             "short_borrow": 0.0, "expense_ratio": 0.0, "cash_yield": 0.0}
    turnover = 0.0
    trades = 0
    for index in range(1, end + 1):
        session = dates[index]
        asset_returns = {symbol: returns[symbol][session] for symbol in ASSETS}
        gross_return = sum(weights[symbol] * asset_returns[symbol] for symbol in ASSETS)
        expense = sum(abs(weights[symbol]) * CURRENT_EXPENSE_RATIOS[symbol] / ANNUALIZATION for symbol in ASSETS)
        borrow = sum(max(-weights[symbol], 0.0) * cost_model.borrow_annual / ANNUALIZATION for symbol in ASSETS)
        net_return = gross_return - expense - borrow
        per_asset = {
            symbol: weights[symbol] * asset_returns[symbol]
            - abs(weights[symbol]) * CURRENT_EXPENSE_RATIOS[symbol] / ANNUALIZATION
            - max(-weights[symbol], 0.0) * cost_model.borrow_annual / ANNUALIZATION
            for symbol in ASSETS
        }
        if index >= start:
            costs["expense_ratio"] += expense
            costs["short_borrow"] += borrow

        denominator = 1.0 + gross_return
        drifted = {
            symbol: weights[symbol] * (1.0 + asset_returns[symbol]) / denominator
            for symbol in ASSETS
        } if denominator > 0.0 else dict(weights)
        if index in scheduled_targets:
            target = scheduled_targets[index]
            executed: dict[str, float] = {}
            for symbol in ASSETS:
                delta = target[symbol] - drifted[symbol]
                threshold = 0.02 * abs(drifted[symbol])
                executed[symbol] = delta if abs(delta) >= threshold else 0.0
            for symbol, delta in executed.items():
                if delta == 0.0:
                    continue
                if index >= start:
                    trades += 1
                    turnover += abs(delta)
                commission = abs(delta) * cost_model.commission
                spread = abs(delta) * cost_model.spread_bps / 10_000.0
                surcharge = max(-delta, 0.0) * cost_model.sell_surcharge_bps / 10_000.0
                total = commission + spread + surcharge
                if index >= start:
                    costs["commission"] += commission
                    costs["spread_slippage"] += spread
                    costs["sell_surcharge"] += surcharge
                net_return -= total
                per_asset[symbol] -= total
            weights = {symbol: drifted[symbol] + executed[symbol] for symbol in ASSETS}
        else:
            weights = drifted

        if index >= start:
            row_dates.append(session)
            gross_rows.append(gross_return)
            net_rows.append(net_return)
            weight_rows.append(dict(weights))
            for symbol in ASSETS:
                contributions[symbol].append(per_asset[symbol])
                opened_asset_returns[symbol].append(asset_returns[symbol])
    return {
        "returns_gross": gross_rows,
        "returns_net": net_rows,
        "dates": row_dates,
        "asset_contributions": contributions,
        "asset_returns": opened_asset_returns,
        "signals": signals,
        "weights": weight_rows,
        "trades": trades,
        "turnover": turnover,
        "costs": costs,
        "covariance_clipped_mass": covariance_clipped_mass,
    }


def _target_at(
    dates: list[str],
    returns: dict[str, dict[str, float]],
    *,
    covariance: list[list[float]] | None,
    index: int,
    lookback: int,
    always_long: bool,
) -> tuple[dict[str, float] | None, dict[str, float], float]:
    if covariance is None or index < lookback:
        return None, {}, 0.0
    histories = {
        symbol: [returns[symbol][dates[pos]] for pos in range(index - lookback + 1, index + 1)]
        for symbol in ASSETS
    }
    signals = {
        symbol: (1.0 if always_long else sum(_direction(value) for value in histories[symbol][-lookback:]) / lookback)
        for symbol in ASSETS
    }
    annual_vol = {
        symbol: max(math.sqrt(max(covariance[i][i], 0.0) * ANNUALIZATION), 0.05)
        for i, symbol in enumerate(ASSETS)
    }
    scores = {symbol: signals[symbol] / annual_vol[symbol] for symbol in ASSETS}
    gross = sum(abs(value) for value in scores.values())
    if gross == 0.0:
        return {symbol: 0.0 for symbol in ASSETS}, signals, 0.0
    normalized = {symbol: 0.90 * scores[symbol] / gross for symbol in ASSETS}
    capped = _cap_and_redistribute(normalized, cap=0.25, gross_limit=0.90)
    portfolio_variance = sum(
        capped[a] * capped[b] * covariance[i][j] * ANNUALIZATION
        for i, a in enumerate(ASSETS) for j, b in enumerate(ASSETS)
    )
    predicted_vol = math.sqrt(max(portfolio_variance, 0.0))
    scale = min(1.0, 0.10 / predicted_vol) if predicted_vol > 0.0 else 1.0
    target = {symbol: capped[symbol] * scale for symbol in ASSETS}
    eigenvalues = symmetric_eigenvalues(covariance)
    clipped_mass = sum(-value for value in eigenvalues if value < 0.0)
    return target, signals, clipped_mass


def trial_summary(trial: Trial) -> dict[str, Any]:
    net = performance_metrics(trial.returns_net)
    gross = performance_metrics(trial.returns_gross)
    active = [value - benchmark for value, benchmark in zip(trial.returns_net, trial.benchmark_net, strict=True)]
    autocorrelations = [sample_autocorrelation(trial.returns_net, lag) or 0.0 for lag in range(1, 6)]
    correlation = _correlation_matrix(
        [[trial.asset_contributions[symbol][index] for index in range(len(trial.dates))] for symbol in ASSETS]
    )
    eigenvalues = [max(value, 0.0) for value in symmetric_eigenvalues(correlation)]
    dimensions = effective_independent_bets_from_eigenvalues(eigenvalues)
    time_effective = effective_sample_length(len(trial.returns_net), autocorrelations)
    joint = time_effective * dimensions
    net_daily_sharpe = sharpe_ratio(trial.returns_net) or 0.0
    skewness = skewness_population(trial.returns_net) or 0.0
    kurtosis = raw_kurtosis_population(trial.returns_net) or 3.0
    psr_025 = probabilistic_sharpe_ratio(
        observed_sharpe=net_daily_sharpe,
        sample_length=len(trial.returns_net),
        skewness=skewness,
        raw_kurtosis=kurtosis,
        null_sharpe=0.25 / math.sqrt(ANNUALIZATION),
        autocorrelations=autocorrelations,
    )
    payoff = _payoff_tests(trial, active)
    concentration = _concentration_tests(trial)
    return {
        "trial_id": trial.trial_id,
        "lookback_sessions": trial.lookback,
        "gross": gross,
        "net": net,
        "active_vs_matched_benchmark": performance_metrics(active),
        "turnover_one_way_notional": trial.turnover,
        "executed_asset_trades": trial.trades,
        "cost_decomposition_return_units": trial.costs,
        "exposure": _exposure_summary(trial.weights),
        "holding_overlap": _holding_overlap(trial.weights),
        "autocorrelations_lags_1_to_5": autocorrelations,
        "time_effective_observations": time_effective,
        "cross_sectional_effective_dimensions": dimensions,
        "joint_independent_bet_equivalents": joint,
        "PSR_vs_annual_Sharpe_0_25": psr_025,
        "MinTRL_falsify_required": 3850,
        "MinTRL_falsify_funded": joint >= 3850,
        "payoff_tests": payoff,
        "concentration_tests": concentration,
        "regime_matrix": _regime_matrix(trial),
        "asset_and_region_matrix": _asset_matrix(trial),
        "removals": _removal_tests(trial, concentration),
        "covariance_negative_eigenvalue_clipped_mass": trial.covariance_clipped_mass,
    }


def add_dsr(primary: dict[str, Any], trials: list[Trial]) -> dict[str, Any]:
    sharpes = [sharpe_ratio(trial.returns_net) or 0.0 for trial in trials]
    correlations = _correlation_matrix([trial.returns_net for trial in trials])
    eigenvalues = [max(value, 0.0) for value in symmetric_eigenvalues(correlations)]
    effective_rank = effective_independent_bets_from_eigenvalues(eigenvalues)
    effective_trials = max(5.0, effective_rank)
    trial_std = pstdev(sharpes)
    returns = trials[0].returns_net
    autocorrelations = [sample_autocorrelation(returns, lag) or 0.0 for lag in range(1, 6)]
    primary["DSR"] = {
        "probability": deflated_sharpe_ratio(
            observed_sharpe=sharpes[0],
            sample_length=len(returns),
            skewness=skewness_population(returns) or 0.0,
            raw_kurtosis=raw_kurtosis_population(returns) or 3.0,
            trial_sharpe_std=trial_std,
            effective_trials=effective_trials,
            autocorrelations=autocorrelations,
        ),
        "locked_trials": 5,
        "correlation_effective_rank": effective_rank,
        "effective_trials_used": effective_trials,
        "trial_daily_sharpe_standard_deviation": trial_std,
    }
    return primary


def performance_metrics(values: list[float]) -> dict[str, Any]:
    if not values:
        return {"observations": 0}
    nav = 1.0
    peak = 1.0
    maximum_drawdown = 0.0
    for value in values:
        nav *= 1.0 + value
        peak = max(peak, nav)
        maximum_drawdown = min(maximum_drawdown, nav / peak - 1.0)
    daily_sharpe = sharpe_ratio(values)
    return {
        "observations": len(values),
        "cumulative_return": nav - 1.0,
        "annual_arithmetic_return": mean(values) * ANNUALIZATION,
        "annual_geometric_return": nav ** (ANNUALIZATION / len(values)) - 1.0,
        "annual_volatility": pstdev(values) * math.sqrt(ANNUALIZATION),
        "annual_sharpe": None if daily_sharpe is None else daily_sharpe * math.sqrt(ANNUALIZATION),
        "maximum_drawdown": maximum_drawdown,
    }


def _weekly_last_sessions(dates: list[str]) -> list[int]:
    groups: dict[tuple[int, int], int] = {}
    for index, value in enumerate(dates):
        parsed = date.fromisoformat(value)
        iso = parsed.isocalendar()
        groups[(iso.year, iso.week)] = index
    return sorted(groups.values())


def _direction(value: float) -> int:
    return 1 if value > 0.0 else -1 if value < 0.0 else 0


def _cap_and_redistribute(weights: dict[str, float], *, cap: float, gross_limit: float) -> dict[str, float]:
    output = dict(weights)
    capped: set[str] = set()
    while True:
        newly_capped = {symbol for symbol, value in output.items() if abs(value) > cap + 1e-15}
        if not newly_capped:
            break
        capped |= newly_capped
        for symbol in newly_capped:
            output[symbol] = math.copysign(cap, output[symbol])
        remaining = gross_limit - sum(abs(output[symbol]) for symbol in capped)
        uncapped = [symbol for symbol in ASSETS if symbol not in capped and weights[symbol] != 0.0]
        base = sum(abs(weights[symbol]) for symbol in uncapped)
        if remaining <= 0.0 or base == 0.0:
            for symbol in uncapped:
                output[symbol] = 0.0
            break
        for symbol in uncapped:
            output[symbol] = math.copysign(remaining * abs(weights[symbol]) / base, weights[symbol])
    return output


def _payoff_tests(trial: Trial, benchmark_active: list[float]) -> dict[str, Any]:
    ordered = sorted(trial.returns_net)
    lower = _percentile(ordered, 0.05)
    upper = _percentile(ordered, 0.95)
    ratio = upper / abs(lower) if lower != 0.0 else None
    convexity = _quadratic_convexity(trial.benchmark_net, trial.returns_net)
    skew = skewness_population(trial.returns_net)
    passes = [ratio is not None and ratio > 1.0, skew is not None and skew > 0.0, convexity["coefficient"] > 0.0 and convexity["newey_west_t"] is not None and convexity["newey_west_t"] >= 1.645]
    return {
        "right_tail_ratio": ratio,
        "right_tail_pass": passes[0],
        "population_skewness": skew,
        "positive_skew_pass": passes[1],
        "quadratic_convexity": convexity,
        "quadratic_convexity_pass": passes[2],
        "convex_payoff_gate_pass": sum(passes) >= 2,
        "explicit_convexity_claim_allowed": sum(passes) >= 2 and passes[2],
    }


def _concentration_tests(trial: Trial) -> dict[str, Any]:
    totals = {symbol: sum(values) for symbol, values in trial.asset_contributions.items()}
    positive = {symbol: max(value, 0.0) for symbol, value in totals.items()}
    total_positive = sum(positive.values())
    shares = {symbol: value / total_positive if total_positive else 0.0 for symbol, value in positive.items()}
    best_market = max(totals, key=totals.get)
    episodes = _episode_contributions(trial)
    positive_episodes = [row for row in episodes if row["contribution"] > 0.0]
    episode_total = sum(row["contribution"] for row in positive_episodes)
    best_episode = max(positive_episodes, key=lambda row: row["contribution"], default=None)
    return {
        "asset_net_contributions": totals,
        "largest_positive_asset": best_market,
        "largest_positive_asset_share": shares[best_market],
        "asset_concentration_pass": shares[best_market] <= 0.35,
        "positive_asset_Herfindahl": sum(value * value for value in shares.values()),
        "episode_count": len(episodes),
        "largest_positive_episode": best_episode,
        "largest_positive_episode_share": None if best_episode is None or episode_total == 0.0 else best_episode["contribution"] / episode_total,
    }


def _episode_contributions(trial: Trial) -> list[dict[str, Any]]:
    decisions = sorted((date_value, signal) for date_value, signal in trial.signals.items() if date_value >= "2007-02-05")
    output: list[dict[str, Any]] = []
    for symbol in ASSETS:
        current: dict[str, Any] | None = None
        neutral_count = 0
        for decision_date, signal_row in decisions:
            sign = _direction(signal_row[symbol])
            if sign == 0:
                neutral_count += 1
                if current is not None and neutral_count >= 2:
                    current["end"] = decision_date
                    output.append(current)
                    current = None
                continue
            neutral_count = 0
            if current is None or current["sign"] != sign:
                if current is not None:
                    current["end"] = decision_date
                    output.append(current)
                current = {"symbol": symbol, "sign": sign, "start": decision_date, "end": trial.dates[-1]}
        if current is not None:
            output.append(current)
    for episode in output:
        episode["contribution"] = sum(
            trial.asset_contributions[episode["symbol"]][index]
            for index, session in enumerate(trial.dates)
            if episode["start"] <= session <= episode["end"]
        )
    return output


def _removal_tests(trial: Trial, concentration: dict[str, Any]) -> dict[str, Any]:
    best_market = concentration["largest_positive_asset"]
    removed_market = [
        trial.returns_net[index] - trial.asset_contributions[best_market][index]
        for index in range(len(trial.dates))
    ]
    episode = concentration["largest_positive_episode"]
    removed_episode = list(trial.returns_net)
    if episode is not None:
        for index, session in enumerate(trial.dates):
            if episode["start"] <= session <= episode["end"]:
                removed_episode[index] -= trial.asset_contributions[episode["symbol"]][index]
    return {
        "best_market_removed": _removal_result(removed_market, best_market),
        "best_trend_removed": _removal_result(removed_episode, None if episode is None else f"{episode['symbol']}:{episode['start']}:{episode['end']}"),
        "method": "Original asset contribution is replaced by zero/cash without re-optimizing other weights.",
    }


def _removal_result(values: list[float], removed: str | None) -> dict[str, Any]:
    metrics = performance_metrics(values)
    sharp = sharpe_ratio(values) or 0.0
    autocorrelations = [sample_autocorrelation(values, lag) or 0.0 for lag in range(1, 6)]
    psr = probabilistic_sharpe_ratio(
        observed_sharpe=sharp, sample_length=len(values), skewness=skewness_population(values) or 0.0,
        raw_kurtosis=raw_kurtosis_population(values) or 3.0, null_sharpe=0.0,
        autocorrelations=autocorrelations,
    )
    return {"removed": removed, "metrics": metrics, "PSR_vs_zero": psr,
            "pass": metrics["annual_geometric_return"] > 0.0 and psr >= 0.90}


def _regime_matrix(trial: Trial) -> dict[str, Any]:
    latest_signal: dict[str, float] = {symbol: 0.0 for symbol in ASSETS}
    decision_rows = sorted(trial.signals.items())
    decision_index = 0
    global_labels: list[str] = []
    median_vols: list[float] = []
    volatility_labels: list[str] = []
    rolling_returns = {symbol: [] for symbol in ASSETS}
    prior_medians: list[float] = []
    sign_histories = {symbol: [] for symbol in ASSETS}
    for row_index, session in enumerate(trial.dates):
        while decision_index < len(decision_rows) and decision_rows[decision_index][0] <= session:
            latest_signal = decision_rows[decision_index][1]
            for symbol in ASSETS:
                sign_histories[symbol].append(_direction(latest_signal[symbol]))
            decision_index += 1
        states = {symbol: "up" if value >= 0.20 else "down" if value <= -0.20 else "neutral" for symbol, value in latest_signal.items()}
        whipsaw_assets = 0
        for symbol in ASSETS:
            recent = [value for value in sign_histories[symbol][-20:] if value != 0]
            changes = sum(a != b for a, b in zip(recent, recent[1:]))
            if changes >= 4 and abs(latest_signal[symbol]) < 0.20:
                whipsaw_assets += 1
        up = sum(value == "up" for value in states.values())
        down = sum(value == "down" for value in states.values())
        if up >= 4 and down < 2:
            label = "broad_uptrend"
        elif down >= 4 and up < 2:
            label = "broad_downtrend"
        elif whipsaw_assets >= 4:
            label = "whipsaw"
        else:
            label = "mixed"
        global_labels.append(label)
        vols = []
        for symbol in ASSETS:
            rolling_returns[symbol].append(trial.asset_returns[symbol][row_index])
            window = rolling_returns[symbol][-60:]
            if len(window) == 60:
                vols.append(pstdev(window) * math.sqrt(ANNUALIZATION))
        median_vol = _percentile(sorted(vols), 0.5) if vols else 0.0
        median_vols.append(median_vol)
        if len(prior_medians) < 756:
            volatility_labels.append("warmup_unclassified")
        else:
            low = _percentile(sorted(prior_medians), 1.0 / 3.0)
            high = _percentile(sorted(prior_medians), 2.0 / 3.0)
            volatility_labels.append("low" if median_vol <= low else "high" if median_vol >= high else "middle")
        prior_medians.append(median_vol)
    return {
        "global_state": _breakdown(trial.returns_net, global_labels),
        "volatility_state": _breakdown(trial.returns_net, volatility_labels),
        "calendar_subperiod": {
            "2007-2009": _date_metrics(trial, "2007-02-05", "2009-12-31"),
            "2010-2012": _date_metrics(trial, "2010-01-01", "2012-12-31"),
            "2013-2015": _date_metrics(trial, "2013-01-01", "2015-12-31"),
        },
        "fixed_crisis_window": {
            "GFC": {"status": "opened_diagnostic", "metrics": _date_metrics(trial, "2007-07-01", "2009-06-30")},
            "COVID": {"status": "sealed_not_accessed"},
            "inflation_2022": {"status": "sealed_not_accessed"},
        },
    }


def _asset_matrix(trial: Trial) -> dict[str, Any]:
    asset = {symbol: performance_metrics(values) for symbol, values in trial.asset_contributions.items()}
    sleeve = {SLEEVES[symbol]: asset[symbol] for symbol in ASSETS}
    region_values: dict[str, list[list[float]]] = defaultdict(list)
    for symbol in ASSETS:
        region_values[REGIONS[symbol]].append(trial.asset_contributions[symbol])
    region = {
        key: performance_metrics([sum(row) for row in zip(*values, strict=True)])
        for key, values in region_values.items()
    }
    return {"asset": asset, "sleeve": sleeve, "country_or_region": region}


def _date_metrics(trial: Trial, start: str, end: str) -> dict[str, Any]:
    return performance_metrics([value for session, value in zip(trial.dates, trial.returns_net, strict=True) if start <= session <= end])


def _breakdown(values: list[float], labels: list[str]) -> dict[str, Any]:
    groups: dict[str, list[float]] = defaultdict(list)
    for value, label in zip(values, labels, strict=True):
        groups[label].append(value)
    return {key: performance_metrics(rows) for key, rows in sorted(groups.items())}


def _exposure_summary(weights: list[dict[str, float]]) -> dict[str, Any]:
    gross = [sum(abs(value) for value in row.values()) for row in weights]
    net = [sum(row.values()) for row in weights]
    return {
        "average_gross": mean(gross), "maximum_gross": max(gross), "average_net": mean(net),
        "minimum_cash_fraction": 1.0 - max(gross), "maximum_absolute_asset_weight": max(abs(value) for row in weights for value in row.values()),
        "leverage_above_one_observations": sum(value > 1.0 + 1e-12 for value in gross),
    }


def _holding_overlap(weights: list[dict[str, float]]) -> dict[str, Any]:
    if len(weights) < 2:
        return {"mean_same_sign_fraction": None, "mean_active_assets": 0.0}
    overlaps = []
    for previous, current in zip(weights, weights[1:]):
        overlaps.append(sum(_direction(previous[s]) == _direction(current[s]) for s in ASSETS) / len(ASSETS))
    return {"mean_same_sign_fraction": mean(overlaps), "mean_active_assets": mean(sum(value != 0.0 for value in row.values()) for row in weights)}


def _quadratic_convexity(x: list[float], y: list[float]) -> dict[str, Any]:
    design = [[1.0, value, value * value] for value in x]
    xtx = [[sum(row[i] * row[j] for row in design) for j in range(3)] for i in range(3)]
    inverse = _inverse_3x3(xtx)
    xty = [sum(row[i] * value for row, value in zip(design, y, strict=True)) for i in range(3)]
    beta = [sum(inverse[i][j] * xty[j] for j in range(3)) for i in range(3)]
    residuals = [value - sum(beta[j] * row[j] for j in range(3)) for row, value in zip(design, y, strict=True)]
    score = [row[2] * residual for row, residual in zip(design, residuals, strict=True)]
    approximate_t = newey_west_t_statistic(score, 5)
    return {"coefficient": beta[2], "newey_west_t": approximate_t, "lags": 5,
            "note": "HAC diagnostic uses the quadratic normal-equation score; E1 only."}


def _inverse_3x3(matrix: list[list[float]]) -> list[list[float]]:
    a, b, c = matrix[0]
    d, e, f = matrix[1]
    g, h, i = matrix[2]
    determinant = a * (e * i - f * h) - b * (d * i - f * g) + c * (d * h - e * g)
    if abs(determinant) < 1e-24:
        raise ValueError("singular quadratic design")
    return [
        [(e * i - f * h) / determinant, (c * h - b * i) / determinant, (b * f - c * e) / determinant],
        [(f * g - d * i) / determinant, (a * i - c * g) / determinant, (c * d - a * f) / determinant],
        [(d * h - e * g) / determinant, (b * g - a * h) / determinant, (a * e - b * d) / determinant],
    ]


def _correlation_matrix(rows: list[list[float]]) -> list[list[float]]:
    means = [mean(row) for row in rows]
    deviations = [[value - means[index] for value in row] for index, row in enumerate(rows)]
    result = []
    for i, left in enumerate(deviations):
        row = []
        for j, right in enumerate(deviations):
            denominator = math.sqrt(sum(value * value for value in left) * sum(value * value for value in right))
            row.append(sum(a * b for a, b in zip(left, right, strict=True)) / denominator if denominator else (1.0 if i == j else 0.0))
        result.append(row)
    return result


def _percentile(ordered: list[float], probability: float) -> float:
    if not ordered:
        return 0.0
    position = (len(ordered) - 1) * probability
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return ordered[lower]
    return ordered[lower] * (upper - position) + ordered[upper] * (position - lower)
