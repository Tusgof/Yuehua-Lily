"""Pure, synthetic-only CORE-1E-A calculation machinery.

This module deliberately accepts an already materialized fixture mapping.  It
does not resolve a data root, open a container, call a provider, or know about
the sealed validation window.
"""

from __future__ import annotations

import math
from datetime import date
from decimal import Decimal
from statistics import mean, pstdev
from typing import Any, Callable, Sequence

from lib.statistics import (
    asymptotic_autocorrelation_inflation,
    deflated_sharpe_ratio,
    effective_independent_bets_from_eigenvalues,
    independent_bet_equivalent_count,
    newey_west_t_statistic,
    newey_west_variance_of_mean,
    probabilistic_sharpe_ratio,
    raw_kurtosis_population,
    sample_autocorrelation,
    sharpe_estimator_variance,
    skewness_population,
    symmetric_eigenvalues,
)


UNIVERSE = ("VTI", "VGK", "EWJ", "VWO", "IEF", "TIP", "GLD", "DBC")
CANDIDATES = ("CORE1_DC60", "CORE1_DC120", "CORE1_SMA200")
BENCHMARK_ID = "equal_weight_always_long_fixed_sleeves"
SLEEVE_WEIGHT = 0.125
NO_TRADE_BAND = 0.02
PRIMARY_COMMISSION = 0.00107
PRIMARY_SPREAD_SLIPPAGE = 0.0025
PRIMARY_SELL_SURCHARGE = 0.0001
TRADING_SESSIONS_PER_YEAR = 252
DEVELOPMENT_START = date(2007, 2, 5)
DEVELOPMENT_END = date(2015, 12, 31)
WARMUP_START = date(2006, 2, 3)
WARMUP_END = date(2007, 2, 2)
VALIDATION_START = date(2016, 1, 4)
VALIDATION_END = date(2026, 6, 30)
SUBPERIODS = {
    "2007_2009": (date(2007, 1, 1), date(2009, 12, 31)),
    "2010_2012": (date(2010, 1, 1), date(2012, 12, 31)),
    "2013_2015": (date(2013, 1, 1), date(2015, 12, 31)),
}

REPORT_SCHEMA_VERSION = "lily_core_1e_a_synthetic_report_v1"
FIXTURE_SCHEMA_VERSION = "lily_core_1e_a_synthetic_market_v1"
ATTRIBUTION_COMPONENTS = ("return", "etf_expense", "commission", "spread_slippage", "sell_surcharge", "primary_net")
ATTRIBUTION_TOLERANCE = 1e-12


def validate_fixture(fixture: Any) -> list[str]:
    """Return structural blockers before any calculation is attempted."""

    blockers: list[str] = []
    required = {"schema_version", "fixture_id", "session_dates", "closes", "expense_ratios"}
    if not isinstance(fixture, dict):
        return ["fixture_must_be_object"]
    if set(fixture) != required:
        blockers.append("fixture_closed_world_changed")
    if fixture.get("schema_version") != FIXTURE_SCHEMA_VERSION:
        blockers.append("fixture_schema_version_changed")
    if fixture.get("fixture_id") != "core1e_a_synthetic_market_v1":
        blockers.append("fixture_id_changed")

    raw_dates = fixture.get("session_dates")
    parsed_dates: list[date] = []
    if not isinstance(raw_dates, list) or not raw_dates:
        blockers.append("session_dates_must_be_nonempty_list")
    else:
        for index, value in enumerate(raw_dates):
            try:
                parsed = date.fromisoformat(value)
            except (TypeError, ValueError):
                blockers.append(f"invalid_session_date:{index}")
                continue
            if not isinstance(value, str) or parsed.isoformat() != value:
                blockers.append(f"noncanonical_session_date:{index}")
            if parsed.weekday() >= 5:
                blockers.append(f"weekend_session_date:{value}")
            parsed_dates.append(parsed)
        if parsed_dates != sorted(set(parsed_dates)):
            blockers.append("session_dates_must_be_strictly_sorted_unique")
        if parsed_dates and (parsed_dates[0] < WARMUP_START or parsed_dates[-1] > DEVELOPMENT_END):
            blockers.append("fixture_date_outside_warmup_or_development_boundary")
        if any(VALIDATION_START <= item <= VALIDATION_END for item in parsed_dates):
            blockers.append("validation_session_present")

    closes = fixture.get("closes")
    if not isinstance(closes, dict) or set(closes) != set(UNIVERSE):
        blockers.append("fixture_universe_changed")
    else:
        expected_length = len(raw_dates) if isinstance(raw_dates, list) else None
        for symbol in UNIVERSE:
            values = closes.get(symbol)
            if not isinstance(values, list) or expected_length is None or len(values) != expected_length:
                blockers.append(f"close_series_shape_changed:{symbol}")
                continue
            for index, value in enumerate(values):
                if not isinstance(value, (int, float)) or isinstance(value, bool) or not math.isfinite(value) or value <= 0.0:
                    blockers.append(f"invalid_close:{symbol}:{index}")

    expenses = fixture.get("expense_ratios")
    if not isinstance(expenses, dict) or set(expenses) != set(UNIVERSE):
        blockers.append("fixture_expense_universe_changed")
    else:
        for symbol in UNIVERSE:
            value = expenses.get(symbol)
            if not isinstance(value, (int, float)) or isinstance(value, bool) or not math.isfinite(value) or value < 0.0:
                blockers.append(f"invalid_expense_ratio:{symbol}")
    return sorted(set(blockers))


def directional_count(returns: list[float], lookback: int) -> int | None:
    """Count positive minus negative observations; zero returns contribute 0."""

    if lookback <= 0:
        raise ValueError("lookback must be positive")
    if len(returns) < lookback:
        return None
    window = returns[-lookback:]
    return sum((value > 0.0) - (value < 0.0) for value in window)


def directional_count_signal(returns: list[float], lookback: int) -> bool | None:
    count = directional_count(returns, lookback)
    return None if count is None else count > 0


def simple_moving_average_signal(closes: list[float], lookback: int = 200) -> bool | None:
    if lookback <= 0:
        raise ValueError("lookback must be positive")
    if len(closes) < lookback:
        return None
    current = closes[-1]
    average = sum(closes[-lookback:]) / lookback
    return current > average


def sma200_signal(closes: list[float]) -> bool | None:
    return simple_moving_average_signal(closes, 200)


def candidate_q(candidate_id: str, returns: list[float], closes: list[float]) -> int | None:
    """Return the signed signal quantity used by the inherited L-1 episode rule."""

    if candidate_id == "CORE1_DC60":
        return directional_count(returns, 60)
    if candidate_id == "CORE1_DC120":
        return directional_count(returns, 120)
    if candidate_id == "CORE1_SMA200":
        signal = sma200_signal(closes)
        return None if signal is None else (1 if signal else -1)
    raise ValueError(f"unknown candidate: {candidate_id}")


def candidate_signal(candidate_id: str, returns: list[float], closes: list[float]) -> bool | None:
    quantity = candidate_q(candidate_id, returns, closes)
    return None if quantity is None else quantity > 0


def weekly_next_session_schedule(
    session_dates: list[str],
    start: date = DEVELOPMENT_START,
    end: date = DEVELOPMENT_END,
) -> list[dict[str, Any]]:
    """Schedule each eligible ISO-week decision at the next supplied session.

    The caller supplies the session calendar.  No weekends, holidays, or
    synthetic dates are inserted by this function.
    """

    dates = [date.fromisoformat(item) for item in session_dates]
    weeks: dict[tuple[int, int], list[int]] = {}
    for index, session_date in enumerate(dates):
        weeks.setdefault((session_date.isocalendar().year, session_date.isocalendar().week), []).append(index)
    schedule: list[dict[str, Any]] = []
    for indices in weeks.values():
        decision_index = indices[-1]
        if dates[decision_index] > end:
            continue
        execution_index = decision_index + 1
        if execution_index >= len(dates) or not start <= dates[execution_index] <= end:
            continue
        schedule.append(
            {
                "decision_index": decision_index,
                "execution_index": execution_index,
                "decision_date": session_dates[decision_index],
                "execution_date": session_dates[execution_index],
            }
        )
    return sorted(schedule, key=lambda item: item["decision_index"])


def fixed_sleeve_target_weights(active_symbols: set[str] | frozenset[str]) -> dict[str, float]:
    unknown = set(active_symbols) - set(UNIVERSE)
    if unknown:
        raise ValueError(f"unknown active symbols: {sorted(unknown)}")
    weights = {symbol: (SLEEVE_WEIGHT if symbol in active_symbols else 0.0) for symbol in UNIVERSE}
    weights["cash"] = 1.0 - sum(weights.values())
    return weights


def drifted_pre_trade_weights(
    previous_weights: dict[str, float], asset_returns: dict[str, float]
) -> dict[str, float]:
    expected = set(UNIVERSE) | {"cash"}
    if set(previous_weights) != expected or set(asset_returns) != set(UNIVERSE):
        raise ValueError("portfolio keys changed")
    values = {
        symbol: previous_weights[symbol] * (1.0 + asset_returns[symbol]) for symbol in UNIVERSE
    }
    values["cash"] = previous_weights["cash"]
    nav = sum(values.values())
    if not math.isfinite(nav) or nav <= 0.0:
        raise ValueError("portfolio NAV must be positive")
    return {key: value / nav for key, value in values.items()}


def apply_no_trade_band(
    drifted_weights: dict[str, float], target_weights: dict[str, float], band: float = NO_TRADE_BAND
) -> dict[str, float]:
    expected = set(UNIVERSE) | {"cash"}
    if set(drifted_weights) != expected or set(target_weights) != expected:
        raise ValueError("portfolio keys changed")
    if band < 0.0:
        raise ValueError("band must be non-negative")
    executed = {}
    for symbol in UNIVERSE:
        difference = abs(target_weights[symbol] - drifted_weights[symbol])
        # Decimal(str(...)) makes the locked inclusive 0.02 boundary explicit
        # instead of depending on a binary floating-point representation.
        if Decimal(str(difference)) >= Decimal(str(band)):
            executed[symbol] = target_weights[symbol]
        else:
            executed[symbol] = drifted_weights[symbol]
    executed["cash"] = 1.0 - sum(executed.values())
    return executed


def execution_costs(
    drifted_weights: dict[str, float],
    executed_weights: dict[str, float],
    *,
    nav: float = 1.0,
    multiplier: float = 1.0,
) -> dict[str, float]:
    if nav <= 0.0 or multiplier <= 0.0:
        raise ValueError("nav and multiplier must be positive")
    by_asset = _asset_execution_costs(drifted_weights, executed_weights, nav=nav, multiplier=multiplier)
    return {
        key: sum(item[key] for item in by_asset.values())
        for key in ("traded_notional", "sold_notional", "commission", "spread_slippage", "sell_surcharge", "execution_cost")
    }


def _asset_execution_costs(
    drifted_weights: dict[str, float],
    executed_weights: dict[str, float],
    *,
    nav: float,
    multiplier: float,
) -> dict[str, dict[str, float]]:
    expected = set(UNIVERSE) | {"cash"}
    if set(drifted_weights) != expected or set(executed_weights) != expected:
        raise ValueError("portfolio keys changed")
    if nav <= 0.0 or multiplier <= 0.0:
        raise ValueError("nav and multiplier must be positive")
    result = {}
    for symbol in UNIVERSE:
        traded_notional = nav * abs(executed_weights[symbol] - drifted_weights[symbol])
        sold_notional = nav * max(drifted_weights[symbol] - executed_weights[symbol], 0.0)
        commission = multiplier * PRIMARY_COMMISSION * traded_notional
        spread_slippage = multiplier * PRIMARY_SPREAD_SLIPPAGE * traded_notional
        sell_surcharge = multiplier * PRIMARY_SELL_SURCHARGE * sold_notional
        result[symbol] = {
            "traded_notional": traded_notional,
            "sold_notional": sold_notional,
            "commission": commission,
            "spread_slippage": spread_slippage,
            "sell_surcharge": sell_surcharge,
            "execution_cost": commission + spread_slippage + sell_surcharge,
        }
    return result


def daily_asset_attribution(
    *,
    start_nav: float,
    start_weights: dict[str, float],
    asset_returns: dict[str, float],
    executed_weights: dict[str, float],
    expense_ratios: dict[str, float],
    drifted_weights: dict[str, float] | None = None,
    execution_multiplier: float = 1.0,
    execution_nav: float | None = None,
) -> dict[str, dict[str, float]]:
    """Attribute one period in fractions of its starting NAV.

    Return, expense, and each execution charge are assigned to the asset that
    generated or incurred them.  The component sum is therefore an additive
    primary-net return reconciliation, independent of the portfolio simulator.
    """

    expected = set(UNIVERSE) | {"cash"}
    if set(start_weights) != expected or set(executed_weights) != expected:
        raise ValueError("portfolio keys changed")
    if set(asset_returns) != set(UNIVERSE) or set(expense_ratios) != set(UNIVERSE):
        raise ValueError("asset keys changed")
    if not math.isfinite(start_nav) or start_nav <= 0.0:
        raise ValueError("start NAV must be positive")
    drifted = start_weights if drifted_weights is None else drifted_weights
    costs_nav = start_nav if execution_nav is None else execution_nav
    if not math.isfinite(costs_nav) or costs_nav <= 0.0:
        raise ValueError("execution NAV must be positive")
    costs = _asset_execution_costs(drifted, executed_weights, nav=costs_nav, multiplier=execution_multiplier)
    result: dict[str, dict[str, float]] = {}
    for symbol in UNIVERSE:
        values = {
            "return": start_weights[symbol] * asset_returns[symbol],
            "etf_expense": -start_weights[symbol] * expense_ratios[symbol] / TRADING_SESSIONS_PER_YEAR,
            "commission": -costs[symbol]["commission"] / start_nav,
            "spread_slippage": -costs[symbol]["spread_slippage"] / start_nav,
            "sell_surcharge": -costs[symbol]["sell_surcharge"] / start_nav,
        }
        values["primary_net"] = sum(values[key] for key in ATTRIBUTION_COMPONENTS[:-1])
        result[symbol] = values
    return result


def _daily_returns(closes: dict[str, list[float]], index: int) -> dict[str, float]:
    return {
        symbol: closes[symbol][index] / closes[symbol][index - 1] - 1.0 for symbol in UNIVERSE
    }


def _autocorrelation_values(values: list[float]) -> tuple[list[float | None], list[float]]:
    reported: list[float | None] = []
    usable: list[float] = []
    for lag in range(1, 6):
        coefficient = sample_autocorrelation(values, lag) if len(values) > lag + 1 else None
        reported.append(coefficient)
        usable.append(0.0 if coefficient is None else coefficient)
    return reported, usable


def _maximum_drawdown(returns: list[float]) -> float | None:
    if not returns:
        return None
    equity = 1.0
    peak = equity
    drawdown = 0.0
    for value in returns:
        equity *= 1.0 + value
        peak = max(peak, equity)
        drawdown = min(drawdown, equity / peak - 1.0)
    return drawdown


def _annual_geometric_return(returns: list[float]) -> float | None:
    if not returns or any(1.0 + value <= 0.0 for value in returns):
        return None
    return math.prod(1.0 + value for value in returns) ** (TRADING_SESSIONS_PER_YEAR / len(returns)) - 1.0


def cross_sectional_correlation_eigenvalues(
    asset_net_contribution_series: dict[str, Sequence[float]],
) -> list[float]:
    """Derive correlation eigenvalues from the supplied per-asset series."""

    if set(asset_net_contribution_series) != set(UNIVERSE):
        raise ValueError("cross-sectional asset set changed")
    series = [list(asset_net_contribution_series[symbol]) for symbol in UNIVERSE]
    if not series or any(len(values) < 2 for values in series) or len({len(values) for values in series}) != 1:
        raise ValueError("cross-sectional series are not evaluable")
    if any(not math.isfinite(value) for values in series for value in values):
        raise ValueError("cross-sectional series contain nonfinite values")
    means = [mean(values) for values in series]
    centered = [[value - average for value in values] for values, average in zip(series, means, strict=True)]
    variances = [sum(value * value for value in values) for values in centered]
    if any(value <= 0.0 for value in variances):
        raise ValueError("cross-sectional correlation requires nonconstant asset series")
    matrix = []
    for left in range(len(UNIVERSE)):
        row = []
        for right in range(len(UNIVERSE)):
            denominator = math.sqrt(variances[left] * variances[right])
            row.append(sum(a * b for a, b in zip(centered[left], centered[right], strict=True)) / denominator)
        matrix.append(row)
    eigenvalues = symmetric_eigenvalues(matrix)
    if any(not math.isfinite(value) or value < -1e-9 for value in eigenvalues):
        raise ValueError("cross-sectional correlation eigenvalues are invalid")
    return [max(0.0, value) for value in eigenvalues]


def cross_sectional_effective_dimension(asset_net_contribution_series: dict[str, Sequence[float]]) -> float:
    return effective_independent_bets_from_eigenvalues(
        cross_sectional_correlation_eigenvalues(asset_net_contribution_series)
    )


def summarize_path(
    returns: list[float],
    rows: list[dict[str, Any]],
    *,
    trial_sharpes_daily: list[float | None] | None = None,
    asset_net_contribution_series: dict[str, Sequence[float]] | None = None,
) -> dict[str, Any]:
    calendar_count = len(returns)
    turnover = sum(row["turnover"] for row in rows)
    trades = sum(row["trades"] for row in rows)
    exposures = [row["exposure"] for row in rows]
    autocorrelation, usable_autocorrelation = _autocorrelation_values(returns)
    if calendar_count >= 1:
        arithmetic_daily = mean(returns)
        arithmetic_annual = arithmetic_daily * TRADING_SESSIONS_PER_YEAR
        geometric_annual = _annual_geometric_return(returns)
        annualized_volatility = pstdev(returns) * math.sqrt(TRADING_SESSIONS_PER_YEAR) if calendar_count >= 2 else None
    else:
        arithmetic_daily = None
        arithmetic_annual = None
        geometric_annual = None
        annualized_volatility = None
    daily_sharpe = None
    annualized_sharpe = None
    skewness = skewness_population(returns)
    raw_kurtosis = raw_kurtosis_population(returns)
    if calendar_count >= 2 and pstdev(returns) != 0.0:
        daily_sharpe = mean(returns) / pstdev(returns)
        annualized_sharpe = daily_sharpe * math.sqrt(TRADING_SESSIONS_PER_YEAR)
    psr = None
    sharpe_variance = None
    hac_variance = None
    hac_t = None
    if (
        daily_sharpe is not None
        and skewness is not None
        and raw_kurtosis is not None
        and calendar_count >= 2
    ):
        try:
            sharpe_variance = sharpe_estimator_variance(
                observed_sharpe=daily_sharpe,
                sample_length=calendar_count,
                skewness=skewness,
                raw_kurtosis=raw_kurtosis,
                autocorrelations=usable_autocorrelation,
            )
            psr = probabilistic_sharpe_ratio(
                observed_sharpe=daily_sharpe,
                sample_length=calendar_count,
                skewness=skewness,
                raw_kurtosis=raw_kurtosis,
                null_sharpe=0.0,
                autocorrelations=usable_autocorrelation,
            )
        except ValueError:
            psr = None
            sharpe_variance = None
    if calendar_count >= 2:
        lags = min(5, calendar_count - 1)
        hac_variance = newey_west_variance_of_mean(returns, lags)
        hac_t = newey_west_t_statistic(returns, lags)
    independent_bets = None
    effective_time = None
    cross_section_bets = None
    cross_section_eigenvalues = None
    if calendar_count >= 2:
        try:
            inflation = asymptotic_autocorrelation_inflation(usable_autocorrelation)
            effective_time = calendar_count / inflation
            if asset_net_contribution_series is not None:
                cross_section_eigenvalues = cross_sectional_correlation_eigenvalues(asset_net_contribution_series)
                cross_section_bets = effective_independent_bets_from_eigenvalues(cross_section_eigenvalues)
                independent_bets = independent_bet_equivalent_count(
                    sample_length=calendar_count,
                    autocorrelations=usable_autocorrelation,
                    cross_section_eigenvalues=cross_section_eigenvalues,
                )
        except ValueError:
            pass
    trial_std = None
    dsr = None
    if (
        trial_sharpes_daily is not None
        and len(trial_sharpes_daily) == 3
        and all(value is not None and math.isfinite(value) for value in trial_sharpes_daily)
        and daily_sharpe is not None
        and calendar_count >= 2
        and skewness is not None
        and raw_kurtosis is not None
    ):
        trial_std = pstdev([value for value in trial_sharpes_daily if value is not None])
        try:
            dsr = deflated_sharpe_ratio(
                observed_sharpe=daily_sharpe,
                sample_length=calendar_count,
                skewness=skewness,
                raw_kurtosis=raw_kurtosis,
                trial_sharpe_std=trial_std,
                effective_trials=3.0,
                autocorrelations=usable_autocorrelation,
            )
        except ValueError:
            dsr = None
    return {
        "calendar_count": calendar_count,
        "annual_arithmetic_return": arithmetic_annual,
        "annual_geometric_return": geometric_annual,
        "annualized_volatility": annualized_volatility,
        "annualized_sharpe": annualized_sharpe,
        "maximum_drawdown": _maximum_drawdown(returns),
        "one_way_turnover": turnover,
        "annualized_one_way_turnover": turnover * TRADING_SESSIONS_PER_YEAR / calendar_count if calendar_count else None,
        "trade_count": trades,
        "average_exposure": mean(exposures) if exposures else None,
        "minimum_exposure": min(exposures) if exposures else None,
        "maximum_exposure": max(exposures) if exposures else None,
        "psr": psr,
        "dsr": dsr,
        "autocorrelation_adjusted_sharpe_variance": sharpe_variance,
        "autocorrelation_lags": {"lags": [1, 2, 3, 4, 5], "values": autocorrelation},
        "hac_newey_west": {
            "lags": min(5, calendar_count - 1) if calendar_count >= 2 else None,
            "variance_of_mean": hac_variance,
            "t_statistic": hac_t,
        },
        "independent_bet_equivalents": {
            "effective_time_count": effective_time,
            "cross_section_count": cross_section_bets,
            "joint_count": independent_bets,
            "cross_section_eigenvalues": cross_section_eigenvalues,
        },
        "daily_sharpe_for_inference": daily_sharpe,
        "skewness_population": skewness,
        "raw_kurtosis_population": raw_kurtosis,
    }


def _signal_target(
    candidate_id: str,
    fixture: dict[str, Any],
    decision_index: int,
    *,
    excluded_asset: str | None = None,
) -> dict[str, float]:
    closes = fixture["closes"]
    active: set[str] = set()
    for symbol in UNIVERSE:
        returns = [closes[symbol][index] / closes[symbol][index - 1] - 1.0 for index in range(1, decision_index + 1)]
        if candidate_signal(candidate_id, returns, closes[symbol][: decision_index + 1]):
            active.add(symbol)
    if excluded_asset is not None:
        active.discard(excluded_asset)
    return fixed_sleeve_target_weights(active)


def _signal_q_by_asset(candidate_id: str, fixture: dict[str, Any], decision_index: int) -> dict[str, int | None]:
    closes = fixture["closes"]
    return {
        symbol: candidate_q(
            candidate_id,
            [closes[symbol][index] / closes[symbol][index - 1] - 1.0 for index in range(1, decision_index + 1)],
            closes[symbol][: decision_index + 1],
        )
        for symbol in UNIVERSE
    }


def _benchmark_target(*, excluded_asset: str | None = None) -> dict[str, float]:
    active = set(UNIVERSE)
    if excluded_asset is not None:
        active.discard(excluded_asset)
    return fixed_sleeve_target_weights(active)


def simulate(
    fixture: dict[str, Any],
    target_for_decision: Callable[[int], dict[str, float]],
) -> dict[str, Any]:
    blockers = validate_fixture(fixture)
    if blockers:
        raise ValueError("invalid synthetic fixture: " + ",".join(blockers))
    dates = fixture["session_dates"]
    parsed_dates = [date.fromisoformat(item) for item in dates]
    closes = fixture["closes"]
    expenses = fixture["expense_ratios"]
    schedule = weekly_next_session_schedule(dates)
    executions = {item["execution_index"]: item for item in schedule}
    weights = {symbol: 0.0 for symbol in UNIVERSE} | {"cash": 1.0}
    nav = 1.0
    rows: list[dict[str, Any]] = []
    path_returns = {"gross": [], "primary_net": [], "two_x_execution_cost_net": []}
    full_attribution = {
        symbol: {component: 0.0 for component in ATTRIBUTION_COMPONENTS}
        for symbol in UNIVERSE
    }
    path_asset_series = {
        path: {symbol: [] for symbol in UNIVERSE}
        for path in path_returns
    }
    daily_attribution: list[dict[str, Any]] = []
    cost_totals = {
        "commission": 0.0,
        "spread_slippage": 0.0,
        "sell_surcharge": 0.0,
        "execution_cost_primary": 0.0,
        "execution_cost_two_x": 0.0,
        "etf_expense_accrual": 0.0,
        "primary_total_cost_drag": 0.0,
        "two_x_total_cost_drag": 0.0,
    }
    for index in range(1, len(dates)):
        period_returns = _daily_returns(closes, index)
        start_weights = dict(weights)
        start_values = {symbol: nav * weights[symbol] for symbol in UNIVERSE}
        start_values["cash"] = nav * weights["cash"]
        start_nav = sum(start_values.values())
        gross_nav = start_values["cash"] + sum(
            start_values[symbol] * (1.0 + period_returns[symbol]) for symbol in UNIVERSE
        )
        expense = sum(
            start_values[symbol] * expenses[symbol] / TRADING_SESSIONS_PER_YEAR for symbol in UNIVERSE
        )
        post_expense_nav = gross_nav - expense
        if post_expense_nav <= 0.0:
            raise ValueError("synthetic portfolio NAV became non-positive")
        drifted_values = {
            symbol: start_values[symbol] * (1.0 + period_returns[symbol]) for symbol in UNIVERSE
        }
        drifted_values["cash"] = start_values["cash"]
        drifted_values = {
            key: value * post_expense_nav / gross_nav for key, value in drifted_values.items()
        }
        drifted = {key: value / post_expense_nav for key, value in drifted_values.items()}
        execution = executions.get(index)
        executed = drifted
        costs_primary = {key: 0.0 for key in ("traded_notional", "sold_notional", "commission", "spread_slippage", "sell_surcharge", "execution_cost")}
        costs_two_x = dict(costs_primary)
        target = None
        if execution is not None:
            target = target_for_decision(execution["decision_index"])
            executed = apply_no_trade_band(drifted, target)
            costs_primary = execution_costs(drifted, executed, nav=post_expense_nav, multiplier=1.0)
            costs_two_x = execution_costs(drifted, executed, nav=post_expense_nav, multiplier=2.0)
            nav_after_cost = post_expense_nav - costs_primary["execution_cost"]
            if nav_after_cost <= 0.0:
                raise ValueError("synthetic execution costs exhausted NAV")
            weights = dict(executed)
            nav = nav_after_cost
        else:
            weights = drifted
            nav = post_expense_nav
        gross_return = gross_nav / (sum(start_values.values())) - 1.0
        primary_return = (post_expense_nav - costs_primary["execution_cost"]) / sum(start_values.values()) - 1.0
        two_x_return = (post_expense_nav - costs_two_x["execution_cost"]) / sum(start_values.values()) - 1.0
        if parsed_dates[index] < DEVELOPMENT_START or parsed_dates[index] > DEVELOPMENT_END:
            continue
        cost_totals["commission"] += costs_primary["commission"]
        cost_totals["spread_slippage"] += costs_primary["spread_slippage"]
        cost_totals["sell_surcharge"] += costs_primary["sell_surcharge"]
        cost_totals["execution_cost_primary"] += costs_primary["execution_cost"]
        cost_totals["execution_cost_two_x"] += costs_two_x["execution_cost"]
        cost_totals["etf_expense_accrual"] += expense
        cost_totals["primary_total_cost_drag"] += expense + costs_primary["execution_cost"]
        cost_totals["two_x_total_cost_drag"] += expense + costs_two_x["execution_cost"]
        rows.append(
            {
                "date": dates[index],
                "gross_return": gross_return,
                "primary_net_return": primary_return,
                "two_x_execution_cost_net_return": two_x_return,
                "exposure": sum(executed[symbol] for symbol in UNIVERSE) if execution is not None else sum(weights[symbol] for symbol in UNIVERSE),
                "turnover": costs_primary["traded_notional"] / sum(start_values.values()),
                "trades": sum(
                    abs(executed[symbol] - drifted[symbol]) >= 1e-15 for symbol in UNIVERSE
                ) if execution is not None else 0,
                "execution": execution is not None,
                "decision_date": execution["decision_date"] if execution is not None else None,
                "execution_date": execution["execution_date"] if execution is not None else None,
                "expense_accrual": expense,
                "primary_execution_cost": costs_primary["execution_cost"],
                "two_x_execution_cost": costs_two_x["execution_cost"],
            }
        )
        path_returns["gross"].append(gross_return)
        path_returns["primary_net"].append(primary_return)
        path_returns["two_x_execution_cost_net"].append(two_x_return)
        primary_attribution = daily_asset_attribution(
            start_nav=start_nav,
            start_weights=start_weights,
            asset_returns=period_returns,
            executed_weights=executed,
            drifted_weights=drifted,
            expense_ratios=expenses,
            execution_nav=post_expense_nav,
        )
        two_x_attribution = daily_asset_attribution(
            start_nav=start_nav,
            start_weights=start_weights,
            asset_returns=period_returns,
            executed_weights=executed,
            drifted_weights=drifted,
            expense_ratios=expenses,
            execution_multiplier=2.0,
            execution_nav=post_expense_nav,
        )
        for symbol in UNIVERSE:
            for component in ATTRIBUTION_COMPONENTS:
                full_attribution[symbol][component] += primary_attribution[symbol][component]
            path_asset_series["gross"][symbol].append(primary_attribution[symbol]["return"])
            path_asset_series["primary_net"][symbol].append(primary_attribution[symbol]["primary_net"])
            path_asset_series["two_x_execution_cost_net"][symbol].append(two_x_attribution[symbol]["primary_net"])
        daily_attribution.append(
            {
                "date": dates[index],
                "primary_net_return": primary_return,
                "asset_components": primary_attribution,
                "asset_total": sum(item["primary_net"] for item in primary_attribution.values()),
            }
        )
    path_rows = {
        name: [
            {
                "turnover": row["turnover"],
                "trades": row["trades"],
                "exposure": row["exposure"],
            }
            for row in rows
        ]
        for name in path_returns
    }
    return {
        "rows": rows,
        "path_returns": path_returns,
        "path_rows": path_rows,
        "asset_contributions": {
            symbol: full_attribution[symbol]["primary_net"] for symbol in UNIVERSE
        },
        "full_window_attribution": full_attribution,
        "daily_attribution": daily_attribution,
        "asset_net_contribution_series": path_asset_series,
        "cost_totals": cost_totals,
        "schedule": schedule,
    }


def inherited_l1_episodes(
    decision_dates: list[str],
    q_by_asset: dict[str, Sequence[float | int | None]],
    *,
    final_date: str | None = None,
) -> list[dict[str, Any]]:
    """Return episodes using the inherited L-1 one-neutral-bridge rule."""

    if set(q_by_asset) != set(UNIVERSE) or any(len(q_by_asset[symbol]) != len(decision_dates) for symbol in UNIVERSE):
        raise ValueError("episode q series shape changed")
    if decision_dates != sorted(decision_dates) or len(set(decision_dates)) != len(decision_dates):
        raise ValueError("episode decision dates must be sorted and unique")
    if final_date is not None and decision_dates and final_date < decision_dates[-1]:
        raise ValueError("episode final date precedes final decision")
    episodes: list[dict[str, Any]] = []
    for asset_index, symbol in enumerate(UNIVERSE):
        current: dict[str, Any] | None = None
        neutral_count = 0
        for index, decision_date in enumerate(decision_dates):
            quantity = q_by_asset[symbol][index]
            if quantity is None or not math.isfinite(float(quantity)):
                raise ValueError("episode q is not evaluable")
            sign = 1 if quantity > 0 else -1 if quantity < 0 else 0
            if sign == 0:
                neutral_count += 1
                if current is not None and neutral_count >= 2:
                    current["end_date"] = decision_date
                    current["end_index"] = index
                    episodes.append(current)
                    current = None
                continue
            neutral_count = 0
            if current is None or current["sign"] != sign:
                if current is not None:
                    current["end_date"] = decision_date
                    current["end_index"] = index
                    episodes.append(current)
                current = {
                    "symbol": symbol,
                    "asset_index": asset_index,
                    "sign": sign,
                    "start_date": decision_date,
                    "start_index": index,
                    "end_date": decision_date,
                    "end_index": index,
                }
            else:
                current["end_date"] = decision_date
                current["end_index"] = index
        if current is not None:
            if final_date is not None:
                current["end_date"] = final_date
            episodes.append(current)
    return episodes


def best_episode_concentration(
    decision_dates: list[str],
    q_by_asset: dict[str, Sequence[float | int | None]],
    daily_dates: list[str],
    asset_net_contribution_series: dict[str, Sequence[float]],
) -> tuple[float | None, list[dict[str, Any]]]:
    """Calculate positive episode concentration from primary-net contributions."""

    if set(asset_net_contribution_series) != set(UNIVERSE) or any(
        len(asset_net_contribution_series[symbol]) != len(daily_dates) for symbol in UNIVERSE
    ):
        raise ValueError("episode contribution series shape changed")
    if daily_dates != sorted(daily_dates):
        raise ValueError("episode contribution dates must be sorted")
    episodes = inherited_l1_episodes(
        decision_dates,
        q_by_asset,
        final_date=daily_dates[-1] if daily_dates else None,
    )
    for episode in episodes:
        episode["primary_net_contribution"] = sum(
            value
            for session, value in zip(
                daily_dates,
                asset_net_contribution_series[episode["symbol"]],
                strict=True,
            )
            if episode["start_date"] <= session <= episode["end_date"]
        )
    positive = [item for item in episodes if item["primary_net_contribution"] > 0.0]
    total = sum(item["primary_net_contribution"] for item in positive)
    if total <= 0.0:
        return None, episodes
    best = max(
        positive,
        key=lambda item: (
            item["primary_net_contribution"],
            -item["asset_index"],
            -item["start_index"],
        ),
    )
    return best["primary_net_contribution"] / total, episodes


def _positive_contribution_summary(contribution: dict[str, float]) -> tuple[float | None, float, float]:
    positive = {key: value for key, value in contribution.items() if value > 0.0}
    total = sum(positive.values())
    if total <= 0.0:
        return None, 0.0, 0.0
    shares = [value / total for value in positive.values()]
    return max(shares), sum(value * value for value in shares), max(shares)


def _subperiods(result: dict[str, Any]) -> dict[str, dict[str, Any]]:
    rows = result["rows"]
    output: dict[str, dict[str, Any]] = {}
    for name, (start, end) in SUBPERIODS.items():
        selected = [row for row in rows if start <= date.fromisoformat(row["date"]) <= end]
        values = [row["primary_net_return"] for row in selected]
        output[name] = {
            "observations": len(values),
            "annual_geometric_return": _annual_geometric_return(values),
            "annualized_sharpe": summarize_path(values, selected)["annualized_sharpe"] if values else None,
        }
    return output


def _worst_subperiod_sharpe(subperiods: dict[str, dict[str, Any]]) -> float | None:
    values = [item["annualized_sharpe"] for item in subperiods.values() if item["annualized_sharpe"] is not None]
    return min(values) if values else None


def _candidate_summary(
    candidate_id: str,
    fixture: dict[str, Any],
    result: dict[str, Any],
    trial_sharpes_daily: list[float | None],
) -> dict[str, Any]:
    metrics = {
        path: summarize_path(
            result["path_returns"][path],
            result["path_rows"][path],
            trial_sharpes_daily=trial_sharpes_daily,
            asset_net_contribution_series=result["asset_net_contribution_series"][path],
        )
        for path in ("gross", "primary_net", "two_x_execution_cost_net")
    }
    contribution = result["asset_contributions"]
    largest_share, hhi, _ = _positive_contribution_summary(contribution)
    decision_dates = [item["decision_date"] for item in result["schedule"]]
    q_by_asset = {
        symbol: []
        for symbol in UNIVERSE
    }
    for item in result["schedule"]:
        q_values = _signal_q_by_asset(candidate_id, fixture, item["decision_index"])
        for symbol in UNIVERSE:
            q_by_asset[symbol].append(q_values[symbol])
    episode_concentration = None
    critical_blockers = []
    try:
        episode_concentration, _ = best_episode_concentration(
            decision_dates,
            q_by_asset,
            [item["date"] for item in result["rows"]],
            result["asset_net_contribution_series"]["primary_net"],
        )
    except ValueError:
        critical_blockers.append("best_episode_concentration_non_evaluable")
    if metrics["primary_net"]["independent_bet_equivalents"]["joint_count"] is None:
        critical_blockers.append("independent_bet_equivalents_non_evaluable")
    positive_asset = None
    positive_values = {key: value for key, value in contribution.items() if value > 0.0}
    if positive_values:
        positive_asset = max(
            positive_values,
            key=lambda symbol: (positive_values[symbol], -UNIVERSE.index(symbol)),
        )
    leave_one_out = None
    if positive_asset is not None:
        removed = simulate(
            fixture,
            lambda decision_index: _signal_target(
                candidate_id, fixture, decision_index, excluded_asset=positive_asset
            ),
        )
        removed_metrics = summarize_path(
            removed["path_returns"]["primary_net"],
            removed["path_rows"]["primary_net"],
            trial_sharpes_daily=trial_sharpes_daily,
            asset_net_contribution_series=removed["asset_net_contribution_series"]["primary_net"],
        )
        leave_one_out = {
            "removed_asset": positive_asset,
            "annual_geometric_return": removed_metrics["annual_geometric_return"],
        }
    subperiods = _subperiods(result)
    return {
        "id": candidate_id,
        "metrics": metrics,
        "costs": result["cost_totals"],
        "asset_contributions": contribution,
        "attribution": {
            "units": "fraction_of_starting_nav",
            "tolerance": ATTRIBUTION_TOLERANCE,
            "daily": result["daily_attribution"],
            "full_window": {
                "asset_components": result["full_window_attribution"],
                "primary_net_return_sum": sum(item["primary_net_return"] for item in result["daily_attribution"]),
                "asset_total": sum(item["primary_net"] for item in result["full_window_attribution"].values()),
            },
        },
        "largest_positive_contribution_share": largest_share,
        "positive_contribution_hhi": hhi,
        "best_episode_concentration": episode_concentration,
        "leave_one_out": leave_one_out,
        "subperiods": subperiods,
        "regime_diagnostics": {
            "gfc": {"status": "diagnostic_only", "funded": False, "claim": "none"},
            "prior_only_global_state_whipsaw": {
                "status": "not_funded",
                "lookahead_free": True,
                "claim": "none",
            },
        },
        "critical_blockers": critical_blockers,
        "gates": {},
        "all_gates_pass": False,
    }


def evaluate_gates(candidate: dict[str, Any], benchmark: dict[str, Any], trial_statistics: list[dict[str, Any]]) -> dict[str, bool]:
    primary = candidate["metrics"]["primary_net"]
    stress = candidate["metrics"]["two_x_execution_cost_net"]
    benchmark_primary = benchmark["metrics"]["primary_net"]
    subperiods = candidate["subperiods"]
    observed_subperiods = [item for item in subperiods.values() if item["observations"] > 0]
    gate_a = primary["annual_geometric_return"] is not None and primary["annual_geometric_return"] > 0.0 and primary["annualized_sharpe"] is not None and primary["annualized_sharpe"] > 0.0
    trial_ids = [item.get("candidate_id") for item in trial_statistics]
    trial_inventory_evaluable = (
        len(trial_statistics) == 3
        and trial_ids == list(CANDIDATES)
        and all(item.get("dsr") is not None for item in trial_statistics)
    )
    gate_b = primary["psr"] is not None and primary["psr"] >= 0.90 and primary["hac_newey_west"]["t_statistic"] is not None and trial_inventory_evaluable
    gate_c = stress["annual_geometric_return"] is not None and stress["annual_geometric_return"] > 0.0 and stress["annualized_sharpe"] is not None and stress["annualized_sharpe"] > 0.0
    gate_d = primary["maximum_drawdown"] is not None and benchmark_primary["maximum_drawdown"] is not None and primary["maximum_drawdown"] - benchmark_primary["maximum_drawdown"] >= 0.05
    leave_one_out = candidate["leave_one_out"]
    gate_e = leave_one_out is not None and leave_one_out["annual_geometric_return"] is not None and leave_one_out["annual_geometric_return"] > 0.0
    gate_f = candidate["largest_positive_contribution_share"] is not None and candidate["largest_positive_contribution_share"] <= 0.50 and candidate["positive_contribution_hhi"] is not None and candidate["best_episode_concentration"] is not None
    positive_subperiods = sum(item["annual_geometric_return"] is not None and item["annual_geometric_return"] > 0.0 for item in observed_subperiods)
    no_bad_subperiod = all(item["annual_geometric_return"] is not None and item["annual_geometric_return"] >= -0.05 for item in observed_subperiods)
    gate_g = len(observed_subperiods) == 3 and positive_subperiods >= 2 and no_bad_subperiod
    gate_h = not candidate["critical_blockers"]
    return {"A": gate_a, "B": gate_b, "C": gate_c, "D": gate_d, "E": gate_e, "F": gate_f, "G": gate_g, "H": gate_h}


def select_candidate(candidates: list[dict[str, Any]], stop_rule: str) -> dict[str, Any]:
    if set(item["id"] for item in candidates) != set(CANDIDATES) or len(candidates) != len(CANDIDATES):
        raise ValueError("selection requires exactly the three locked candidates")
    discarded = [item["id"] for item in candidates if not item["all_gates_pass"]]
    eligible = [item for item in candidates if item["all_gates_pass"]]
    ranking = []
    for item in candidates:
        ranking.append(
            {
                "candidate_id": item["id"],
                "eligible": item["all_gates_pass"],
                "worst_subperiod_annualized_sharpe": _worst_subperiod_sharpe(item["subperiods"]),
                "one_way_turnover": item["metrics"]["primary_net"]["one_way_turnover"],
            }
        )
    if not eligible:
        return {
            "outcome": "no_winner_stop",
            "winner": None,
            "eligible_candidates": [],
            "discarded_candidates": discarded,
            "ranking": ranking,
            "stop_rule": stop_rule,
            "tie_break": "not_applied",
        }
    ranked_by_primary = sorted(
        eligible,
        key=lambda item: (
            -(_worst_subperiod_sharpe(item["subperiods"]) if _worst_subperiod_sharpe(item["subperiods"]) is not None else -math.inf),
            CANDIDATES.index(item["id"]),
        ),
    )
    ranked = ranked_by_primary
    winner = ranked[0]
    tie_break = "none"
    if len(ranked) >= 2:
        first_score = _worst_subperiod_sharpe(ranked[0]["subperiods"])
        second_score = _worst_subperiod_sharpe(ranked[1]["subperiods"])
        if first_score is not None and second_score is not None and abs(first_score - second_score) <= 0.02:
            tie_break = "lower_one_way_turnover_then_locked_candidate_order"
            near_tied = ranked[:2]
            near_tied.sort(
                key=lambda item: (
                    item["metrics"]["primary_net"]["one_way_turnover"] if item["metrics"]["primary_net"]["one_way_turnover"] is not None else math.inf,
                    CANDIDATES.index(item["id"]),
                )
            )
            winner = near_tied[0]
    return {
        "outcome": "single_winner",
        "winner": winner["id"],
        "eligible_candidates": [item["id"] for item in eligible],
        "discarded_candidates": discarded,
        "ranking": ranking,
        "stop_rule": stop_rule,
        "tie_break": tie_break,
    }


def build_report(
    fixture: dict[str, Any],
    *,
    contract_sha256: str,
    fixture_sha256: str,
    producing_commit: str,
    engine_sha256: str,
    stop_rule: str,
) -> dict[str, Any]:
    blockers = validate_fixture(fixture)
    if blockers:
        raise ValueError("invalid synthetic fixture: " + ",".join(blockers))
    results = {
        candidate_id: simulate(
            fixture,
            lambda decision_index, candidate_id=candidate_id: _signal_target(candidate_id, fixture, decision_index),
        )
        for candidate_id in CANDIDATES
    }
    benchmark_result = simulate(fixture, lambda _decision_index: _benchmark_target())
    trial_daily_sharpes = [
        summarize_path(
            result["path_returns"]["primary_net"],
            result["path_rows"]["primary_net"],
            asset_net_contribution_series=result["asset_net_contribution_series"]["primary_net"],
        )["daily_sharpe_for_inference"]
        for result in results.values()
    ]
    candidates = [
        _candidate_summary(candidate_id, fixture, results[candidate_id], trial_daily_sharpes)
        for candidate_id in CANDIDATES
    ]
    benchmark = {
        "id": BENCHMARK_ID,
        "metrics": {
            path: summarize_path(
                benchmark_result["path_returns"][path],
                benchmark_result["path_rows"][path],
                trial_sharpes_daily=trial_daily_sharpes,
                asset_net_contribution_series=benchmark_result["asset_net_contribution_series"][path],
            )
            for path in ("gross", "primary_net", "two_x_execution_cost_net")
        },
        "costs": benchmark_result["cost_totals"],
    }
    trial_statistics = []
    for candidate in candidates:
        primary_metrics = candidate["metrics"]["primary_net"]
        trial_statistics.append(
            {
                "candidate_id": candidate["id"],
                "annualized_sharpe": primary_metrics["annualized_sharpe"],
                "dsr": primary_metrics["dsr"],
                "effective_trial_count": 3,
            }
        )
    for candidate in candidates:
        candidate["gates"] = evaluate_gates(candidate, benchmark, trial_statistics)
        candidate["all_gates_pass"] = all(candidate["gates"].values())
    selection = select_candidate(candidates, stop_rule)
    schedule = results[CANDIDATES[0]]["schedule"]
    return {
        "schema_version": REPORT_SCHEMA_VERSION,
        "report_type": "synthetic_calculation_only",
        "outcome": "synthetic_evaluation",
        "evidence_tier": "E0",
        "edge_claim": "none",
        "contract_sha256": contract_sha256,
        "fixture": {
            "path": "tests/fixtures/core1e_a/synthetic_market_v1.json",
            "sha256": fixture_sha256,
            "fixture_id": fixture["fixture_id"],
        },
        "windows": {
            "warmup_qa": {"start": WARMUP_START.isoformat(), "end": WARMUP_END.isoformat(), "performance_claim": False},
            "development": {"start": DEVELOPMENT_START.isoformat(), "end": DEVELOPMENT_END.isoformat()},
            "validation": {"start": VALIDATION_START.isoformat(), "end": VALIDATION_END.isoformat(), "status": "sealed_not_accessed", "accessed": False},
        },
        "timing_attestation": {
            "weekly_decisions": len(schedule),
            "all_execution_dates_after_decisions": all(item["execution_index"] > item["decision_index"] for item in schedule),
            "same_close_execution": False,
            "manufactured_sessions": False,
            "lookahead_detected": False,
        },
        "calculation_attestation": {
            "fixed_sleeve_weight": SLEEVE_WEIGHT,
            "no_trade_band": NO_TRADE_BAND,
            "expense_accrual_basis": "annual_ratio_divided_by_252_on_held_notional",
            "primary_execution_cost_multiplier": 1.0,
            "two_x_execution_cost_multiplier": 2.0,
            "two_x_expense_multiplier": 1.0,
        },
        "trial_inventory": {
            "count": 3,
            "candidate_ids": list(CANDIDATES),
            "effective_rank_convention": "all_three_locked_trials",
        },
        "trial_statistics": trial_statistics,
        "candidates": candidates,
        "benchmark": benchmark,
        "selection": selection,
        "access_counts": {
            "real_dataset_access": 0,
            "real_container_access": 0,
            "real_return_decode": 0,
            "validation_access": 0,
            "provider_calls": 0,
            "credential_reads": 0,
            "broker_actions": 0,
            "paid_actions": 0,
        },
        "validation_seal": {"status": "sealed_not_accessed", "accessed": False},
        "provenance": {
            "producing_commit": producing_commit,
            "engine_sha256": engine_sha256,
            "source_kind": "committed_synthetic_fixture_only",
        },
    }
