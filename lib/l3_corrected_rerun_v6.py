"""B7.10 synthetic-only L-3 decision arithmetic; no data I/O."""
from __future__ import annotations

import math
from typing import Any

Z_ONE_SIDED_95 = 1.6448536269514722
Z_POWER_80 = 0.8416212335729143
NULL_DELTA = 0.05
ADVERSE_DELTA = 0.0
MINTRL_FLOOR = 49


def finite(value: Any, *, nonnegative: bool = False) -> bool:
    return type(value) in (int, float) and math.isfinite(value) and (not nonnegative or value >= 0)


def recompute_statistics(observations: Any, standard_deviation: Any, lags: Any) -> dict[str, float | int] | None:
    """Locked weekly-paired L-3 inference arithmetic, independent of returns."""
    if type(observations) is not int or observations <= 0 or not finite(standard_deviation, nonnegative=True) or not isinstance(lags, list) or len(lags) != 5 or not all(finite(value) for value in lags):
        return None
    inflation = 1.0 + 2.0 * sum(lags)
    if inflation <= 0:
        return None
    standard_error = standard_deviation * math.sqrt(inflation / observations)
    raw_mintrl = math.ceil((Z_ONE_SIDED_95 + Z_POWER_80) ** 2 * standard_deviation ** 2 / abs(ADVERSE_DELTA - NULL_DELTA) ** 2 * inflation)
    return {"autocorrelation_inflation": inflation, "standard_error": standard_error, "actual_mintrl_falsify": max(MINTRL_FLOOR, raw_mintrl)}
