# IMPLEMENT_PLAN.md

- **Plan version**: Refounding v4 — outcome-first execution
- **Date**: 2026-09-13
- **Scope**: one CORE-1 development decision; validation and operations remain outside this plan.

## 1. Objective and fixed CORE-1 question

Obtain one reproducible development decision for the stable baseline, or stop honestly, without changing locked science.

On the locked U8 daily total-return universe through 2015-12-31, does any of `CORE1_DC60`, `CORE1_DC120`, or `CORE1_SMA200` pass all locked A-H gates after locked costs?

## 2. Accepted locked inputs

- CORE-1 direction, candidates, U8 order, sleeves, timing, band, costs, benchmark, A-H gates, ranking, selection, stop rule, claim ceiling, and sealed validation boundary: `docs/DECISION_RECORD_007_STABLE_BASELINE_DIRECTION.md` and `experiments/core_1_stable_baseline_preregistration_v1.json`.
- Gate hashes and append-only lineage: `experiments/locked_gates_v2.jsonl`, `experiments/locked_gate_segments.json`, and `scripts/validate_locked_gates.py`.
- Hypothesis/evidence state: `experiments/hypothesis_registry.json` and `docs/HYPOTHESIS_REGISTRY.md`.
- Current execution state: `experiments/bootstrap_tracker.json`, `PROJECT_BRAIN.md`, and Decision Record 008.
- Methodology context: the named local LLM Wiki pages for directional count, horizons, volatility, costs, MinTRL, PSR, DSR, HAC/Newey-West, and global regimes. Wiki context cannot override locked artifacts.
- Validation remains sealed for 2016-01-04 through 2026-06-30; no input substitution, parameter rescue, fourth candidate, or search expansion is accepted.

## 3. Single active execution queue

1. **OF-0 — integrate GOV-2.** Owner integrates the governance decision before this plan governs main.
2. **OF-1 — close the smallest missing R3 decision/lifecycle/report binding.** Reuse existing artifacts where safe; add no new schema or validator unless the existing contract cannot represent the decision.
3. **OF-2 — CP-A clean-commit/full-audit/data-boundary review.** Inspector reviews the clean commit, static tracker, full-audit status where required, locked gates, cutoff, and data boundary before opening development inputs.
4. **OF-3 — exactly one pre-2016 development execution.** Run the three fixed candidates once on the locked pre-2016 window, with no validation access, no parameter search, and no rescue.
5. **OF-4 — CP-B independent report review and Thai research log.** Inspector independently reviews the report and writes the Thai research log after the genuine empirical result.
6. **OF-5 — lock one winner or stop CORE-1.** Select exactly one candidate only if the locked rule allows it; otherwise stop. Only then decide whether L-2/L-3/L-4 resumes.
7. **OF-6 — CP-C validation.** Validation is a separate future owner decision and remains unauthorized here.

## 4. Development milestone definition of done

One provenance-bound report, generated at one commit, contains return; Sharpe, PSR, DSR, and HAC evidence; drawdown; turnover and cost; subperiods; concentration; all A-H results; ranking; and the locked stop/selection trace. It records the evidence tier, claim ceiling, environment, inputs, and blockers. Validation remains sealed. A Thai research log exists before the scientific outcome closes.

## 5. Verification ladder

Use focused tests during implementation, then the static tracker check locally, then fast exact-SHA CI on every push. Run the full runtime audit only for control/tracker/locked-gate changes, named CP-A/CP-B/CP-C or closure points, main integration, or weekly/manual review—not after every small edit. Never run a full tracker from a dirty checkout.

## 6. Work-order rule

Every order names the scientific decision it unlocks. If a proposed task has no direct link to that decision within two steps, backlog it.

## 7. Complexity and version budget

Reuse before adding. Fix uncommitted work in place. Do not add a fourth candidate, parameter search, or rescue path. Create a new locked version only when a locked/published artifact is materially superseded for semantic or integrity reasons. A second rejection at the same critical point requires simplification and a smaller Inspector-reviewed design, not another layer.

## 8. Paused backlog

L-2, L-3, and L-4 execution; Webull options capability; broker, paper, live, paid, and provider work.

## 9. Owner decisions still required

Owner integration of GOV-2; CP-A data opening; any development activation; CP-C validation; and all paid, provider-mutating, broker, paper, or live actions.

## 10. Current status and next safe action

CORE-1 is active E0 machinery with no empirical result and no edge claim. L-2/L-3/L-4 are paused at their existing statuses, and validation is sealed. Next safe action: owner integration of GOV-2, then the smallest missing binding for one CP-A-reviewed development-only run. Historical execution detail belongs in `Backup_/2026-09-13/`, decision records, reports, the tracker, and Git.
