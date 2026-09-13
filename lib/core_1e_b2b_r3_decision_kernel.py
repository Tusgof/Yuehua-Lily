"""Closed-world CORE-1E-B2-B-R3 Decimal decision machinery."""
from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation, Overflow, localcontext
from typing import Any

CANDIDATE_ORDER = ("CORE1_DC60", "CORE1_DC120", "CORE1_SMA200")
UNIVERSE_ORDER = ("VTI", "VGK", "EWJ", "VWO", "IEF", "TIP", "GLD", "DBC")
SUBPERIOD_ORDER = ("2007-2009", "2010-2012", "2013-2015")
TRIAL_COUNT = 3
SELECTED_CANDIDATE = "selected_candidate"
STOP_NO_CANDIDATE = "stop_no_candidate_passes_all_gates"
EVIDENCE_TIER, EDGE_CLAIM = "E0", "none"
VALIDATION_STATUS = "sealed_not_accessed"
FUTURE_EMPIRICAL_CEILING = "E1_development_ceiling_only"
ZERO, ONE, TWO = Decimal("0"), Decimal("1"), Decimal("2")
MINUS_ONE = Decimal("-1")
PSR_THRESHOLD = Decimal("0.90")
DRAWDOWN_GAP = Decimal("0.05")
SHARE_LIMIT = Decimal("0.50")
SUBPERIOD_FLOOR = Decimal("-0.05")
NEAR_TIE = Decimal("0.02")
FINAL_TIE = Decimal("1e-12")
DECIMAL_FLOAT_MAX = Decimal("1.7976931348623157e308")

class EvidenceValidationError(ValueError):
    """Raised when closed-world primitive evidence is invalid."""

class ForgedDecisionError(EvidenceValidationError):
    """Raised when a reported decision differs from recomputation."""

_TOP_LEVEL_FIELDS = frozenset({"candidates"})
_CANDIDATE_FIELDS = frozenset("""
 candidate_id primary_net_annual_geometric_return primary_net_annual_sharpe
 stress_net_annual_geometric_return stress_net_annual_sharpe primary_max_drawdown
 benchmark_max_drawdown leave_one_asset_id leave_one_asset_net_annual_geometric_return
 asset_net_contributions subperiod_net_annual_geometric_return subperiod_net_sharpe
 one_way_turnover critical_blockers trials best_episode_concentration
""".split())
_TRIAL_FIELDS = frozenset("annual_sharpe psr_vs_zero hac_mean_return_p_value dsr_probability".split())
_DECISION_FIELDS = frozenset("""
 candidate_order outcome selected_candidate eligible_candidates ranking_order candidate_gates
 evidence_tier edge_claim validation_status future_provenance_bound_empirical_ceiling
""".split())

def _mapping(value: Any, label: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise EvidenceValidationError(f"{label} must be an object")
    return value

def _exact(value: Mapping[str, Any], expected: frozenset[str], label: str) -> None:
    actual = set(value)
    if missing := expected - actual:
        raise EvidenceValidationError(f"{label} missing fields: {sorted(missing)}")
    if unknown := actual - expected:
        raise EvidenceValidationError(f"{label} unknown fields: {sorted(unknown)}")

def _number(value: Any, label: str) -> Decimal:
    if type(value) not in (int, float):
        raise EvidenceValidationError(f"{label} must be an int or float primitive")
    try:
        result = Decimal(str(value))
    except (InvalidOperation, OverflowError, ValueError) as exc:
        raise EvidenceValidationError(f"{label} cannot be normalized to Decimal") from exc
    if not result.is_finite() or result.copy_abs() > DECIMAL_FLOAT_MAX:
        raise EvidenceValidationError(f"{label} must be finite and within numeric bounds")
    return result

def _bounded(value: Any, label: str, *, minimum: Decimal | None = None, maximum: Decimal | None = None) -> Decimal:
    result = _number(value, label)
    if minimum is not None and result < minimum:
        raise EvidenceValidationError(f"{label} is below {minimum}")
    if maximum is not None and result > maximum:
        raise EvidenceValidationError(f"{label} is above {maximum}")
    return result

def _ordered(value: Any, expected: tuple[str, ...], label: str, *, minimum: Decimal | None = None, maximum: Decimal | None = None) -> dict[str, Decimal]:
    mapping = _mapping(value, label)
    if set(mapping) != set(expected):
        raise EvidenceValidationError(f"{label} must contain exactly {expected}")
    return {key: _bounded(mapping[key], f"{label}.{key}", minimum=minimum, maximum=maximum) for key in expected}

def _trial(value: Any, index: int, primary_sharpe: Decimal) -> dict[str, Decimal]:
    item = _mapping(value, f"trials[{index}]")
    _exact(item, _TRIAL_FIELDS, f"trials[{index}]")
    result = {
        "annual_sharpe": _number(item["annual_sharpe"], f"trials[{index}].annual_sharpe"),
        "psr_vs_zero": _bounded(item["psr_vs_zero"], f"trials[{index}].psr_vs_zero", minimum=ZERO, maximum=ONE),
        "hac_mean_return_p_value": _bounded(item["hac_mean_return_p_value"], f"trials[{index}].hac_mean_return_p_value", minimum=ZERO, maximum=ONE),
        "dsr_probability": _bounded(item["dsr_probability"], f"trials[{index}].dsr_probability", minimum=ZERO, maximum=ONE),
    }
    if index == 0 and result["annual_sharpe"] != primary_sharpe:
        raise EvidenceValidationError("trials[0].annual_sharpe must equal primary_net_annual_sharpe")
    return result

def _candidate(value: Any, index: int) -> dict[str, Any]:
    item = _mapping(value, f"candidates[{index}]")
    _exact(item, _CANDIDATE_FIELDS, f"candidates[{index}]")
    candidate_id, expected_id = item["candidate_id"], CANDIDATE_ORDER[index]
    if not isinstance(candidate_id, str) or candidate_id != expected_id:
        raise EvidenceValidationError(f"candidates must use locked order; index {index} is {expected_id}")
    primary_sharpe = _number(item["primary_net_annual_sharpe"], f"{candidate_id}.primary_net_annual_sharpe")
    result: dict[str, Any] = {
        "candidate_id": candidate_id,
        "primary_net_annual_geometric_return": _bounded(item["primary_net_annual_geometric_return"], f"{candidate_id}.primary_net_annual_geometric_return", minimum=MINUS_ONE),
        "primary_net_annual_sharpe": primary_sharpe,
        "stress_net_annual_geometric_return": _bounded(item["stress_net_annual_geometric_return"], f"{candidate_id}.stress_net_annual_geometric_return", minimum=MINUS_ONE),
        "stress_net_annual_sharpe": _number(item["stress_net_annual_sharpe"], f"{candidate_id}.stress_net_annual_sharpe"),
        "primary_max_drawdown": _bounded(item["primary_max_drawdown"], f"{candidate_id}.primary_max_drawdown", minimum=MINUS_ONE, maximum=ZERO),
        "benchmark_max_drawdown": _bounded(item["benchmark_max_drawdown"], f"{candidate_id}.benchmark_max_drawdown", minimum=MINUS_ONE, maximum=ZERO),
        "leave_one_asset_id": item["leave_one_asset_id"],
        "leave_one_asset_net_annual_geometric_return": _bounded(item["leave_one_asset_net_annual_geometric_return"], f"{candidate_id}.leave_one_asset_net_annual_geometric_return", minimum=MINUS_ONE),
        "asset_net_contributions": _ordered(item["asset_net_contributions"], UNIVERSE_ORDER, f"{candidate_id}.asset_net_contributions"),
        "subperiod_net_annual_geometric_return": _ordered(item["subperiod_net_annual_geometric_return"], SUBPERIOD_ORDER, f"{candidate_id}.subperiod_net_annual_geometric_return", minimum=MINUS_ONE),
        "subperiod_net_sharpe": _ordered(item["subperiod_net_sharpe"], SUBPERIOD_ORDER, f"{candidate_id}.subperiod_net_sharpe"),
        "one_way_turnover": _bounded(item["one_way_turnover"], f"{candidate_id}.one_way_turnover", minimum=ZERO),
        "best_episode_concentration": _bounded(item["best_episode_concentration"], f"{candidate_id}.best_episode_concentration", minimum=ZERO, maximum=ONE),
    }
    leave_one = result["leave_one_asset_id"]
    if leave_one is not None and (not isinstance(leave_one, str) or leave_one not in UNIVERSE_ORDER):
        raise EvidenceValidationError(f"{candidate_id}.leave_one_asset_id must be a universe symbol or null")
    blockers = item["critical_blockers"]
    if type(blockers) is not list or any(not isinstance(blocker, str) or not blocker for blocker in blockers):
        raise EvidenceValidationError(f"{candidate_id}.critical_blockers must be a list of non-empty strings")
    if len(set(blockers)) != len(blockers):
        raise EvidenceValidationError(f"{candidate_id}.critical_blockers must not contain duplicates")
    result["critical_blockers"] = tuple(blockers)
    trials = item["trials"]
    if type(trials) is not list or len(trials) != TRIAL_COUNT:
        raise EvidenceValidationError(f"{candidate_id}.trials must contain exactly {TRIAL_COUNT} entries")
    result["trials"] = tuple(_trial(trial, trial_index, primary_sharpe) for trial_index, trial in enumerate(trials))
    return result

def validate_primitive_evidence(evidence: Mapping[str, Any]) -> tuple[dict[str, Any], ...]:
    payload = _mapping(evidence, "evidence")
    _exact(payload, _TOP_LEVEL_FIELDS, "evidence")
    candidates = payload["candidates"]
    if type(candidates) is not list or len(candidates) != len(CANDIDATE_ORDER):
        raise EvidenceValidationError("candidates must contain exactly the three locked candidates")
    return tuple(_candidate(item, index) for index, item in enumerate(candidates))

def _checked_sum(values: tuple[Decimal, ...], label: str) -> Decimal:
    try:
        with localcontext() as context:
            context.prec = 1000
            total = sum(values, ZERO)
    except (InvalidOperation, Overflow) as exc:
        raise EvidenceValidationError(f"{label} aggregate overflow") from exc
    if not total.is_finite() or total.copy_abs() > DECIMAL_FLOAT_MAX:
        raise EvidenceValidationError(f"{label} aggregate overflow")
    return total

def _metrics(candidate: Mapping[str, Any]) -> dict[str, Any]:
    contributions = candidate["asset_net_contributions"]
    _checked_sum(tuple(contributions.values()), f"{candidate['candidate_id']}.asset_net_contributions")
    positive = {symbol: value for symbol, value in contributions.items() if value > ZERO}
    positive_total = _checked_sum(tuple(positive.values()), f"{candidate['candidate_id']}.positive_contributions")
    if not positive:
        return {"removed": None, "share": ZERO, "hhi": ZERO, "share_ok": False, "worst": min(candidate["subperiod_net_sharpe"].values())}
    removed = None
    for symbol in UNIVERSE_ORDER:
        if symbol in positive and (removed is None or positive[symbol] > positive[removed]):
            removed = symbol
    largest = positive[removed]
    with localcontext() as context:
        context.prec = 1000
        share, hhi = largest / positive_total, sum(((value / positive_total) ** 2 for value in positive.values()), ZERO)
    return {"removed": removed, "share": share, "hhi": hhi, "share_ok": largest * TWO <= positive_total, "worst": min(candidate["subperiod_net_sharpe"].values())}

@dataclass(frozen=True)
class CandidateEvaluation:
    candidate_id: str
    gates: Mapping[str, bool]
    eligible: bool
    worst_subperiod_net_sharpe: Decimal
    one_way_turnover: Decimal
    removed_asset: str | None
    largest_positive_contribution_share: Decimal
    positive_contribution_hhi: Decimal

    def as_mapping(self) -> dict[str, Any]:
        return {"candidate_id": self.candidate_id, "gates": dict(self.gates), "eligible": self.eligible, "worst_subperiod_net_sharpe": self.worst_subperiod_net_sharpe, "one_way_turnover": self.one_way_turnover, "removed_asset": self.removed_asset, "largest_positive_contribution_share": self.largest_positive_contribution_share, "positive_contribution_hhi": self.positive_contribution_hhi}

def _evaluate(candidate: Mapping[str, Any]) -> CandidateEvaluation:
    metrics = _metrics(candidate)
    primary_trial, returns = candidate["trials"][0], candidate["subperiod_net_annual_geometric_return"]
    gates = {
        "A": candidate["primary_net_annual_geometric_return"] > ZERO and candidate["primary_net_annual_sharpe"] > ZERO,
        "B": primary_trial["psr_vs_zero"] >= PSR_THRESHOLD,
        "C": candidate["stress_net_annual_geometric_return"] > ZERO and candidate["stress_net_annual_sharpe"] > ZERO,
        "D": candidate["primary_max_drawdown"] - candidate["benchmark_max_drawdown"] >= DRAWDOWN_GAP,
        "E": metrics["removed"] is not None and candidate["leave_one_asset_id"] == metrics["removed"] and candidate["leave_one_asset_net_annual_geometric_return"] > ZERO,
        "F": metrics["share_ok"],
        "G": sum(value > ZERO for value in returns.values()) >= 2 and all(value >= SUBPERIOD_FLOOR for value in returns.values()),
        "H": not candidate["critical_blockers"],
    }
    return CandidateEvaluation(candidate["candidate_id"], gates, all(gates.values()), metrics["worst"], candidate["one_way_turnover"], metrics["removed"], metrics["share"], metrics["hhi"])

@dataclass(frozen=True)
class Decision:
    candidate_order: tuple[str, ...]
    outcome: str
    selected_candidate: str | None
    eligible_candidates: tuple[str, ...]
    ranking_order: tuple[str, ...]
    candidate_evaluations: tuple[CandidateEvaluation, ...]
    evidence_tier: str = EVIDENCE_TIER
    edge_claim: str = EDGE_CLAIM
    validation_status: str = VALIDATION_STATUS
    future_provenance_bound_empirical_ceiling: str = FUTURE_EMPIRICAL_CEILING

    def as_mapping(self) -> dict[str, Any]:
        return {"candidate_order": list(self.candidate_order), "outcome": self.outcome, "selected_candidate": self.selected_candidate, "eligible_candidates": list(self.eligible_candidates), "ranking_order": list(self.ranking_order), "candidate_gates": {item.candidate_id: dict(item.gates) for item in self.candidate_evaluations}, "evidence_tier": self.evidence_tier, "edge_claim": self.edge_claim, "validation_status": self.validation_status, "future_provenance_bound_empirical_ceiling": self.future_provenance_bound_empirical_ceiling}

def _ranking(evaluations: tuple[CandidateEvaluation, ...]) -> tuple[CandidateEvaluation, ...]:
    order = {candidate_id: index for index, candidate_id in enumerate(CANDIDATE_ORDER)}
    return tuple(sorted((item for item in evaluations if item.eligible), key=lambda item: (-item.worst_subperiod_net_sharpe, order[item.candidate_id])))

def _select(ranked: tuple[CandidateEvaluation, ...]) -> CandidateEvaluation | None:
    if not ranked:
        return None
    if len(ranked) == 1:
        return ranked[0]
    first, second = ranked[:2]
    if first.worst_subperiod_net_sharpe - second.worst_subperiod_net_sharpe <= NEAR_TIE:
        delta = first.one_way_turnover - second.one_way_turnover
        if abs(delta) <= FINAL_TIE:
            return min((first, second), key=lambda item: CANDIDATE_ORDER.index(item.candidate_id))
        return first if delta < ZERO else second
    return first

def _check_reported(decision: Decision, reported: Mapping[str, Any]) -> None:
    payload = _mapping(reported, "reported_decision")
    _exact(payload, _DECISION_FIELDS, "reported_decision")
    if dict(payload) != decision.as_mapping():
        raise ForgedDecisionError("reported decision does not exactly equal recomputation")

def derive_decision(evidence: Mapping[str, Any], *, reported_decision: Mapping[str, Any] | None = None) -> Decision:
    primitives = validate_primitive_evidence(evidence)
    with localcontext() as context:
        context.prec = 1000
        evaluations = tuple(_evaluate(candidate) for candidate in primitives)
        eligible = tuple(item.candidate_id for item in evaluations if item.eligible)
        ranked = _ranking(evaluations)
        selected = _select(ranked)
        decision = Decision(CANDIDATE_ORDER, SELECTED_CANDIDATE if selected else STOP_NO_CANDIDATE, selected.candidate_id if selected else None, eligible, tuple(item.candidate_id for item in ranked), evaluations)
    if reported_decision is not None:
        _check_reported(decision, reported_decision)
    return decision

def validate_reported_decision(decision: Decision, reported: Mapping[str, Any]) -> None:
    if not isinstance(decision, Decision):
        raise TypeError("decision must be a Decision")
    _check_reported(decision, reported)

__all__ = ["CANDIDATE_ORDER", "UNIVERSE_ORDER", "SUBPERIOD_ORDER", "CandidateEvaluation", "Decision", "EvidenceValidationError", "ForgedDecisionError", "STOP_NO_CANDIDATE", "SELECTED_CANDIDATE", "derive_decision", "validate_primitive_evidence", "validate_reported_decision"]
