"""Dependency-free statistical primitives with explicit Lily conventions.

The kernel uses population moments, raw Pearson kurtosis, unannualized Sharpe,
finite-sample Bartlett autocorrelation weights for observed inference, and an
asymptotic autocorrelation inflation for prospective sample-size planning.
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from statistics import NormalDist, mean, pstdev


NORMAL = NormalDist()
ONE_SIDED_95_Z = NORMAL.inv_cdf(0.95)
EULER_MASCHERONI = 0.5772156649015329


def normal_cdf(value: float) -> float:
    return NORMAL.cdf(value)


def normal_ppf(probability: float) -> float:
    if not 0.0 < probability < 1.0:
        raise ValueError("probability must be between zero and one")
    return NORMAL.inv_cdf(probability)


def sharpe_ratio(returns: Sequence[float]) -> float | None:
    if len(returns) < 2:
        return None
    sigma = pstdev(returns)
    return None if sigma == 0.0 else mean(returns) / sigma


def skewness_population(returns: Sequence[float]) -> float | None:
    if len(returns) < 2:
        return None
    mu = mean(returns)
    sigma = pstdev(returns)
    if sigma == 0.0:
        return None
    return sum(((value - mu) / sigma) ** 3 for value in returns) / len(returns)


def raw_kurtosis_population(returns: Sequence[float]) -> float | None:
    if len(returns) < 2:
        return None
    mu = mean(returns)
    sigma = pstdev(returns)
    if sigma == 0.0:
        return None
    return sum(((value - mu) / sigma) ** 4 for value in returns) / len(returns)


def sample_autocorrelation(values: Sequence[float], lag: int) -> float | None:
    if lag < 1:
        raise ValueError("lag must be positive")
    if len(values) <= lag + 1:
        return None
    left = values[:-lag]
    right = values[lag:]
    left_mean = mean(left)
    right_mean = mean(right)
    denominator = math.sqrt(
        sum((value - left_mean) ** 2 for value in left)
        * sum((value - right_mean) ** 2 for value in right)
    )
    if denominator == 0.0:
        return None
    return sum((a - left_mean) * (b - right_mean) for a, b in zip(left, right)) / denominator


def generalized_sharpe_variance_term(
    observed_sharpe: float,
    skewness: float,
    raw_kurtosis: float,
) -> float:
    value = 1.0 - skewness * observed_sharpe
    value += ((raw_kurtosis - 1.0) / 4.0) * observed_sharpe * observed_sharpe
    if value <= 0.0:
        raise ValueError("generalized Sharpe variance term must be positive")
    return value


def autocorrelation_inflation(sample_length: int, autocorrelations: Sequence[float]) -> float:
    if sample_length < 2:
        raise ValueError("sample_length must be at least two")
    if len(autocorrelations) >= sample_length:
        raise ValueError("autocorrelation lags must be shorter than the sample")
    inflation = 1.0
    for lag, coefficient in enumerate(autocorrelations, start=1):
        if not -1.0 < coefficient < 1.0:
            raise ValueError("autocorrelation must lie strictly between minus one and one")
        inflation += 2.0 * (1.0 - lag / sample_length) * coefficient
    if inflation <= 0.0:
        raise ValueError("autocorrelation inflation must be positive")
    return inflation


def asymptotic_autocorrelation_inflation(autocorrelations: Sequence[float]) -> float:
    for coefficient in autocorrelations:
        if not -1.0 < coefficient < 1.0:
            raise ValueError("autocorrelation must lie strictly between minus one and one")
    inflation = 1.0 + 2.0 * sum(autocorrelations)
    if inflation <= 0.0:
        raise ValueError("asymptotic autocorrelation inflation must be positive")
    return inflation


def effective_sample_length(sample_length: int, autocorrelations: Sequence[float]) -> float:
    return sample_length / autocorrelation_inflation(sample_length, autocorrelations)


def sharpe_estimator_variance(
    *,
    observed_sharpe: float,
    sample_length: int,
    skewness: float,
    raw_kurtosis: float,
    autocorrelations: Sequence[float] = (),
) -> float:
    effective_n = effective_sample_length(sample_length, autocorrelations)
    if effective_n <= 1.0:
        raise ValueError("effective sample length must exceed one")
    return generalized_sharpe_variance_term(observed_sharpe, skewness, raw_kurtosis) / (effective_n - 1.0)


def probabilistic_sharpe_ratio(
    *,
    observed_sharpe: float,
    sample_length: int,
    skewness: float,
    raw_kurtosis: float,
    null_sharpe: float,
    autocorrelations: Sequence[float] = (),
) -> float:
    variance = sharpe_estimator_variance(
        observed_sharpe=observed_sharpe,
        sample_length=sample_length,
        skewness=skewness,
        raw_kurtosis=raw_kurtosis,
        autocorrelations=autocorrelations,
    )
    return normal_cdf((observed_sharpe - null_sharpe) / math.sqrt(variance))


def minimum_track_record_length(
    *,
    observed_sharpe: float,
    skewness: float,
    raw_kurtosis: float,
    null_sharpe: float,
    autocorrelations: Sequence[float] = (),
    significance: float = 0.05,
) -> int | None:
    """Observed-significance MinTRL anchor; does not include prospective power."""
    if observed_sharpe <= null_sharpe:
        return None
    z_alpha = normal_ppf(1.0 - significance)
    variance_term = generalized_sharpe_variance_term(observed_sharpe, skewness, raw_kurtosis)
    raw_length = 1.0 + variance_term * (z_alpha / (observed_sharpe - null_sharpe)) ** 2
    return math.ceil(raw_length * asymptotic_autocorrelation_inflation(autocorrelations))


def minimum_track_record_length_validate(
    *,
    expected_sharpe: float,
    null_sharpe: float,
    skewness: float,
    raw_kurtosis: float,
    autocorrelations: Sequence[float] = (),
    significance: float = 0.05,
    power: float = 0.80,
) -> int | None:
    if expected_sharpe <= null_sharpe:
        return None
    return _powered_track_record_length(
        difference=expected_sharpe - null_sharpe,
        reference_sharpe=expected_sharpe,
        skewness=skewness,
        raw_kurtosis=raw_kurtosis,
        autocorrelations=autocorrelations,
        significance=significance,
        power=power,
    )


def minimum_track_record_length_falsify(
    *,
    claimed_minimum_sharpe: float,
    adverse_true_sharpe: float,
    skewness: float,
    raw_kurtosis: float,
    autocorrelations: Sequence[float] = (),
    significance: float = 0.05,
    power: float = 0.80,
) -> int | None:
    if adverse_true_sharpe >= claimed_minimum_sharpe:
        return None
    return _powered_track_record_length(
        difference=claimed_minimum_sharpe - adverse_true_sharpe,
        reference_sharpe=adverse_true_sharpe,
        skewness=skewness,
        raw_kurtosis=raw_kurtosis,
        autocorrelations=autocorrelations,
        significance=significance,
        power=power,
    )


def paired_mean_minimum_observations(
    *,
    alternative_mean: float,
    null_mean: float,
    planning_standard_deviation: float,
    autocorrelations: Sequence[float] = (),
    significance: float = 0.05,
    power: float = 0.80,
) -> int | None:
    """One-sided paired-mean planning length with asymptotic lag inflation.

    This is a normal-mean power calculation for a paired portfolio metric.  It
    deliberately does not use Sharpe moments, annualization, or asset counts.
    """
    if planning_standard_deviation <= 0.0:
        raise ValueError("planning standard deviation must be positive")
    if not 0.0 < significance < 1.0 or not 0.0 < power < 1.0:
        raise ValueError("significance and power must be between zero and one")
    difference = abs(alternative_mean - null_mean)
    if difference == 0.0:
        return None
    z_total = normal_ppf(1.0 - significance) + normal_ppf(power)
    independent_observations = (z_total * planning_standard_deviation / difference) ** 2
    return math.ceil(
        independent_observations * asymptotic_autocorrelation_inflation(autocorrelations)
    )


def _powered_track_record_length(
    *,
    difference: float,
    reference_sharpe: float,
    skewness: float,
    raw_kurtosis: float,
    autocorrelations: Sequence[float],
    significance: float,
    power: float,
) -> int:
    if not 0.0 < significance < 1.0 or not 0.0 < power < 1.0:
        raise ValueError("significance and power must be between zero and one")
    variance_term = generalized_sharpe_variance_term(reference_sharpe, skewness, raw_kurtosis)
    z_total = normal_ppf(1.0 - significance) + normal_ppf(power)
    raw_length = 1.0 + variance_term * (z_total / difference) ** 2
    return math.ceil(raw_length * asymptotic_autocorrelation_inflation(autocorrelations))


def expected_maximum_sharpe(*, trial_sharpe_std: float, effective_trials: float) -> float:
    if trial_sharpe_std < 0.0:
        raise ValueError("trial_sharpe_std must be non-negative")
    if effective_trials <= 1.0:
        raise ValueError("effective_trials must exceed one")
    first = normal_ppf(1.0 - 1.0 / effective_trials)
    second = normal_ppf(1.0 - 1.0 / (effective_trials * math.e))
    return trial_sharpe_std * ((1.0 - EULER_MASCHERONI) * first + EULER_MASCHERONI * second)


def deflated_sharpe_ratio(
    *,
    observed_sharpe: float,
    sample_length: int,
    skewness: float,
    raw_kurtosis: float,
    trial_sharpe_std: float,
    effective_trials: float,
    autocorrelations: Sequence[float] = (),
) -> float:
    search_hurdle = expected_maximum_sharpe(
        trial_sharpe_std=trial_sharpe_std,
        effective_trials=effective_trials,
    )
    return probabilistic_sharpe_ratio(
        observed_sharpe=observed_sharpe,
        sample_length=sample_length,
        skewness=skewness,
        raw_kurtosis=raw_kurtosis,
        null_sharpe=search_hurdle,
        autocorrelations=autocorrelations,
    )


def newey_west_variance_of_mean(values: Sequence[float], lags: int) -> float:
    if len(values) < 2:
        raise ValueError("at least two observations are required")
    if lags < 0 or lags >= len(values):
        raise ValueError("lags must be between zero and sample_length minus one")
    mu = mean(values)
    centered = [value - mu for value in values]
    sample_length = len(values)
    long_run_variance = sum(value * value for value in centered) / sample_length
    for lag in range(1, lags + 1):
        covariance = sum(centered[index] * centered[index - lag] for index in range(lag, sample_length))
        covariance /= sample_length
        weight = 1.0 - lag / (lags + 1.0)
        long_run_variance += 2.0 * weight * covariance
    return max(long_run_variance, 0.0) / sample_length


def newey_west_t_statistic(values: Sequence[float], lags: int, *, null_mean: float = 0.0) -> float | None:
    variance = newey_west_variance_of_mean(values, lags)
    if variance == 0.0:
        return None
    return (mean(values) - null_mean) / math.sqrt(variance)


def effective_independent_bets_from_eigenvalues(eigenvalues: Sequence[float]) -> float:
    if not eigenvalues or any(value < 0.0 for value in eigenvalues):
        raise ValueError("eigenvalues must be a non-empty non-negative sequence")
    total = sum(eigenvalues)
    squared_total = sum(value * value for value in eigenvalues)
    if total <= 0.0 or squared_total == 0.0:
        raise ValueError("eigenvalues must contain positive mass")
    return total * total / squared_total


def independent_bet_equivalent_count(
    *,
    sample_length: int,
    autocorrelations: Sequence[float],
    cross_section_eigenvalues: Sequence[float],
) -> float:
    time_equivalents = effective_sample_length(sample_length, autocorrelations)
    cross_section_equivalents = effective_independent_bets_from_eigenvalues(cross_section_eigenvalues)
    return time_equivalents * cross_section_equivalents


def symmetric_eigenvalues(matrix: Sequence[Sequence[float]], *, tolerance: float = 1e-12) -> list[float]:
    """Return eigenvalues of a small real symmetric matrix via Jacobi rotations."""
    size = len(matrix)
    if size == 0 or any(len(row) != size for row in matrix):
        raise ValueError("matrix must be non-empty and square")
    work = [[float(value) for value in row] for row in matrix]
    for row in range(size):
        for column in range(size):
            if abs(work[row][column] - work[column][row]) > tolerance:
                raise ValueError("matrix must be symmetric")
    for _ in range(max(1, 50 * size * size)):
        p, q = max(
            ((row, column) for row in range(size) for column in range(row + 1, size)),
            key=lambda pair: abs(work[pair[0]][pair[1]]),
            default=(0, 0),
        )
        if p == q or abs(work[p][q]) <= tolerance:
            break
        angle = 0.5 * math.atan2(2.0 * work[p][q], work[q][q] - work[p][p])
        cosine, sine = math.cos(angle), math.sin(angle)
        app, aqq, apq = work[p][p], work[q][q], work[p][q]
        work[p][p] = cosine * cosine * app - 2.0 * sine * cosine * apq + sine * sine * aqq
        work[q][q] = sine * sine * app + 2.0 * sine * cosine * apq + cosine * cosine * aqq
        work[p][q] = work[q][p] = 0.0
        for index in range(size):
            if index in (p, q):
                continue
            aip, aiq = work[index][p], work[index][q]
            work[index][p] = work[p][index] = cosine * aip - sine * aiq
            work[index][q] = work[q][index] = sine * aip + cosine * aiq
    return sorted((work[index][index] for index in range(size)), reverse=True)
