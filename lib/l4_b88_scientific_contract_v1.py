"""Pure in-memory L-4 B8.8 science contract; it never opens a data path."""
from __future__ import annotations

import math
from statistics import mean, stdev
from typing import Sequence

from lib.statistics import newey_west_variance_of_mean, paired_mean_minimum_observations, symmetric_eigenvalues

U8 = ("VTI", "VGK", "EWJ", "VWO", "IEF", "TIP", "GLD", "DBC")
U4 = ("VTI", "IEF", "GLD", "DBC")
METRICS = ("ex_ante_hhi_delta", "realized_hhi_delta", "top_dependency_delta", "n_eff_delta")
USEFUL = {"ex_ante_hhi_delta": .05, "realized_hhi_delta": .05, "top_dependency_delta": .1, "n_eff_delta": .5}
Z95 = 1.6448536269514722
AUTHORIZATIONS = {key: False for key in ("data", "container", "market", "return", "signal", "position", "covariance", "regime", "cost", "pnl", "validation", "provider", "network", "credentials", "broker", "paid", "paper_trade", "real_money", "activation", "execution", "report", "research_decision", "ledger")}
SEAL = {"status": "sealed_not_accessed", "accessed": False}


def _finite(value: object) -> bool:
    return type(value) in (int, float) and math.isfinite(value)


def _matrix(matrix: Sequence[Sequence[float]]) -> bool:
    return bool(matrix) and all(len(row) == len(matrix) and all(_finite(x) for x in row) for row in matrix) and all(abs(matrix[i][j] - matrix[j][i]) <= 1e-10 for i in range(len(matrix)) for j in range(len(matrix)))


def _shares(weights: Sequence[float], covariance: Sequence[Sequence[float]]) -> list[float] | None:
    if len(weights) != len(covariance) or not all(_finite(x) for x in weights) or not _matrix(covariance): return None
    rc = [weights[i] * sum(covariance[i][j] * weights[j] for j in range(len(weights))) for i in range(len(weights))]
    total = sum(abs(x) for x in rc)
    return None if not _finite(total) or total <= 0 else [abs(x) / total for x in rc]


def component_hhi(weights: Sequence[float], covariance: Sequence[Sequence[float]]) -> float | None:
    shares = _shares(weights, covariance)
    return None if shares is None else sum(x * x for x in shares)


def top_dependency(weights: Sequence[float], covariance: Sequence[Sequence[float]], symbols: Sequence[str]) -> float | None:
    shares = _shares(weights, covariance)
    if shares is None or tuple(symbols) not in (U4, U8): return None
    lookup = dict(zip(symbols, shares)); sleeves = (("VTI", "VGK", "EWJ", "VWO"), ("IEF",), ("TIP",), ("GLD",), ("DBC",))
    return max(max(shares), *(sum(lookup.get(symbol, 0.0) for symbol in sleeve) for sleeve in sleeves))


def correlation_n_eff(q_history: Sequence[Sequence[float]]) -> tuple[float, float] | None:
    """Participation ratio of PSD-clipped Pearson correlation, plus clipped mass."""
    if len(q_history) != 52 or not q_history or len(q_history[0]) not in (4, 8): return None
    width = len(q_history[0])
    if any(len(row) != width or not all(_finite(x) for x in row) for row in q_history): return None
    columns = [[row[j] for row in q_history] for j in range(width)]
    if any(max(col) == min(col) for col in columns): return None
    centers = [mean(col) for col in columns]; scales = [math.sqrt(sum((x-center)**2 for x in col)) for col, center in zip(columns, centers)]
    corr = [[sum((x-centers[i])*(y-centers[j]) for x,y in zip(columns[i],columns[j]))/(scales[i]*scales[j]) for j in range(width)] for i in range(width)]
    try: values = symmetric_eigenvalues(corr)
    except ValueError: return None
    mass = sum(-x for x in values if x < 0); clipped = [max(0.0, x) for x in values]; denominator = sum(x*x for x in clipped)
    return None if denominator <= 0 else ((sum(clipped)**2)/denominator, mass)


def gross_cap_scale(q: Sequence[float], covariance: Sequence[Sequence[float]]) -> tuple[list[float], dict[str, bool]] | None:
    """L1 mechanics after L4's locked primary u=q override; cash is implicit."""
    if not q or not all(_finite(x) for x in q) or not _matrix(covariance) or len(q) != len(covariance): return None
    gross = sum(abs(x) for x in q)
    if gross == 0: return [0.0 for _ in q], {"cap": False, "cash": True, "scale_down": False}
    target = [.9*x/gross for x in q]; cap = False
    while any(abs(x) > .25+1e-12 for x in target):
        cap = True; excess = 0.0; free = []
        for i,value in enumerate(target):
            if abs(value) > .25: excess += abs(value)-.25; target[i] = math.copysign(.25,value)
            elif value != 0: free.append(i)
        denominator = sum(abs(target[i]) for i in free)
        if denominator == 0: break
        for i in free: target[i] += math.copysign(excess*abs(target[i])/denominator,target[i])
    predicted = math.sqrt(max(0.0,sum(target[i]*covariance[i][j]*target[j] for i in range(len(target)) for j in range(len(target)))))
    scale = min(1.0,.10/predicted) if predicted > 0 else 1.0
    return [x*scale for x in target], {"cap":cap,"cash":sum(abs(x) for x in target)<.9-1e-12,"scale_down":scale<1.0-1e-12}


def booked_cost(previous: Sequence[float], target: Sequence[float], *, commission: float=.00107, spread_bps: float=25.0, sell_bps: float=1.0) -> float | None:
    if len(previous) != len(target) or not all(_finite(x) for x in tuple(previous)+tuple(target)): return None
    return sum(abs(new-old)*(commission+spread_bps/10000.0)+(abs(new-old)*sell_bps/10000.0 if new-old < 0 else 0.0) for old,new in zip(previous,target))


def timing_is_matched(rows: Sequence[dict[str, object]]) -> bool:
    for row in rows:
        if set(row) != {"decision_date","execution_date","realized_dates","u4_date","u8_date"}: return False
        decision, execution, realized = row["decision_date"],row["execution_date"],row["realized_dates"]
        if not all(isinstance(x,str) for x in (decision,execution,row["u4_date"],row["u8_date"])) or decision >= execution or decision > "2015-12-31" or row["u4_date"] != decision or row["u8_date"] != decision: return False
        if not isinstance(realized,list) or len(realized) != 20 or any(not isinstance(x,str) for x in realized) or realized != sorted(realized) or realized[0] < execution or realized[-1] > "2015-12-31": return False
    return bool(rows)


def _lags(values: Sequence[float]) -> list[float] | None:
    if len(values) <= 5 or not all(_finite(x) for x in values): return None
    centre=mean(values); denominator=sum((x-centre)**2 for x in values)
    return None if denominator <= 0 else [sum((values[i]-centre)*(values[i-lag]-centre) for i in range(lag,len(values)))/denominator for lag in range(1,6)]


def actual_statistics(values: Sequence[float], metric: str) -> dict[str, object] | None:
    if metric not in METRICS or len(values) < 6: return None
    lags=_lags(values)
    if lags is None: return None
    sd=stdev(values); useful=USEFUL[metric]
    plans=(("falsify",0.0,useful),("validation_zero",useful,0.0),("validation_minimum_useful",2*useful,useful))
    required={name:paired_mean_minimum_observations(alternative_mean=alternative,null_mean=null,planning_standard_deviation=sd,autocorrelations=lags,significance=.05,power=.8) for name,alternative,null in plans}
    if any(value is None for value in required.values()): return None
    hac=math.sqrt(newey_west_variance_of_mean(values,5))
    return {"observation_unit":"one weekly paired portfolio observation","weekly_paired_observations":len(values),"mean":mean(values),"sample_sd":sd,"lags_1_to_5":lags,"dependence_inflation":1+2*sum(lags),"hac_standard_error_lags_5":hac,"falsify_mintrl":required["falsify"],"validation_zero_mintrl":required["validation_zero"],"validation_minimum_useful_mintrl":required["validation_minimum_useful"],"falsify_ucb":mean(values)+Z95*hac,"validation_lcb":mean(values)-Z95*hac}


def classify_e1(statistics: dict[str, dict[str, object]], *, constraints_evaluable: bool, constraints_pass: bool) -> str:
    if set(statistics) != set(METRICS) or not constraints_evaluable: return "scope_restricted"
    if any(not isinstance(statistics[name].get("falsify_mintrl"),int) or statistics[name]["weekly_paired_observations"] < statistics[name]["falsify_mintrl"] for name in METRICS): return "scope_restricted"
    if not constraints_pass or any(statistics[name]["falsify_ucb"] < USEFUL[name] for name in METRICS): return "falsified_E1_only"
    return "not_falsified_not_validated_E1"


def classify_validation(statistics: dict[str, dict[str, object]], *, regimes_funded: bool, constraints_evaluable: bool, constraints_pass: bool, integrity_pass: bool) -> str:
    if set(statistics) != set(METRICS) or not regimes_funded or not constraints_evaluable: return "validation_scope_restricted"
    if any(statistics[name]["weekly_paired_observations"] < max(statistics[name]["validation_zero_mintrl"],statistics[name]["validation_minimum_useful_mintrl"]) for name in METRICS): return "validation_scope_restricted"
    if not constraints_pass or any(statistics[name]["validation_lcb"] <= USEFUL[name] for name in METRICS): return "validation_falsified_E1_only"
    return "validation_candidate" if integrity_pass else "not_validated_E1"
