# IMPLEMENT_PLAN.md

## 1. Plan Definition

- **Program**: Lily systematic trend-following research
- **Plan version**: Refounding v2
- **Date**: 2026-07-15
- **Operating model**: parallel hypothesis tracks plus standing governance programs
- **End state**: Lily can honestly classify hypotheses as proposed, active, parked, falsified, scope-restricted, E2-validated, or E3 deployment-grade.

This plan does not authorize strategy code, a backtest, paper trading, broker requests, or real-money trading by itself.

## 2. Accepted Design Inputs

Pre-refounding, owner-authored inputs carried forward:

- baseline: 60-day directional count;
- candidate: multi-lookback t-stat / delta-straddle interpretation;
- sizing: `signal × risk weight / volatility`;
- portfolio leverage: target volatility plus caps;
- costs before trust;
- unknowns remain explicit.

Founding decisions are in `docs/DECISION_RECORD_001_PROJECT_REFOUNDING.md`.

## 3. Standing Programs

### P0 — Governance And Audit

Maintain evidence tiers, hypothesis registry, preregistration, locked-gate hashes, adversarial E2 review, anti-overstatement checks, and machine-checkable trackers.

### P1 — Reproducibility And Environment

Maintain pinned Python, dependency manifests, hermetic/state-audit tiers, CI, environment resolution, commit provenance, and zero tracked absolute paths.

### P2 — Statistics Kernel

Maintain one `lib/` implementation for autocorrelation-adjusted Sharpe variance, PSR, DSR, dual MinTRL, HAC sensitivity, independent-bet-equivalent counts, and golden-number anchors.

### P3 — Data Integrity And Cost

Maintain acquisition decisions, provider schemas, survivorship/roll policy, dataset registry, dual hashes, true-provenance per-key cost ledger, and budget guards.

### P4 — Backup, Restore, And Retention

Maintain `BACKUP_AND_RESTORE.md`, restore rehearsals, durable evidence indices, and later retention policy. A backup is not trusted until restored successfully.

## 4. Hypothesis Tracks

### T0 / L-0 — Sizing Feasibility First

Question: can a globally diversified trend implementation be sized honestly at USD 1,000 and USD 2,000, and what capital is required for broader futures variants?

Required branches:

1. US-listed fractional ETF portfolio with global country and asset-class exposure;
2. micro-futures feasibility at 4, 8, and 12 markets;
3. full-size futures as a documented out-of-current-scope comparator.

Include whole/fractional granularity, margin, cash buffer, target risk, volatility, cost, turnover, concentration, currency, and broker capability. No return backtest is needed to resolve L-0.

Exit: classify each branch as current-capital feasible, scope-restricted, minimum-capital-only, or infeasible under the preregistered constraints.

### T1 / L-1 — Baseline Continuation

Test the 60-day directional-count baseline on the chosen research universe after implementable costs. Evaluate convex/right-tail behavior, whipsaw regimes, concentration, and scope restrictions.

Exit: falsified with mechanism autopsy, parked as underpowered, or E2-eligible after all gates and adversarial review.

### T2 / L-2 — Candidate Versus Baseline

Compare the multi-lookback t-stat candidate with a matched-horizon baseline on the same universe, dates, sizing, cost model, and search accounting.

Exit: candidate improves a preregistered utility criterion without relying on unlogged search, or is falsified/parked.

### T3 / L-3 — Sizing Architecture

Compare inverse-volatility sizing with equal notional using ex-ante and realized risk contribution, concentration, turnover, leverage, drawdown, and regime stability.

Exit: inverse-vol sizing materially reduces preregistered concentration measures without unacceptable cost or leverage side effects, or the claim is falsified.

### T4 / L-4 — Breadth

Test whether additional countries, sleeves, and independent markets reduce single-market trend dependency after accounting for trend-state correlation and costs.

Exit: breadth reduces preregistered dependency/concentration measures, produces an explicit scope restriction, or is falsified.

## 5. Execution Orders

### B0 — Governance Bootstrap

Source of truth: `HANDOFF_FOR_CODEX_BOOTSTRAP.md` and `experiments/bootstrap_tracker.json`.

Deliver the self-verifying repository contract before research code. The tracker validator must reject false `done` claims. CI must run the hermetic tier on every push.

Forbidden: data acquisition, broker contact, strategy rules, backtests, and performance claims.

### B1 — Data Layer Design And Fixtures

After B0 passes:

- write the data acquisition decision tree;
- define dataset registry and dual-hash rules;
- define ETF survivorship/inception/delisting policy;
- define futures contract/roll and adjusted-series policy;
- add provider-boundary schemas and committed synthetic fixtures;
- keep paid spend at USD 0.

Exit: hermetic ingestion/normalization fixtures pass and no real strategy is executed.

### B2 — L-0 Feasibility Study

After B1 passes, preregister L-0 and run only the sizing/capability study. Use read-only public terms, sandbox, or account-reported permissions; never store credentials.

Exit: current-capital and minimum-capital classifications are reproducible and costed.

### B3 — L-1 Baseline Specification

After L-0 decision:

- lock research universe and observation unit;
- lock 60-day formula, timing, neutral handling, volatility estimate, rebalance rule, cost model, benchmarks, regimes, and untouched test;
- compute/fund `MinTRL_falsify` before `MinTRL_validate`;
- create locked manifest entry and adversarial-review plan.

No real backtest may run in the same session that first writes or revises this preregistration.

### B4 — L-1 Baseline Execution

Only after B3's hashes and validators pass may a separate session run the bounded baseline. Report E1 unless every E2 criterion, including adversarial review, passes.

The completed run must also write the audited Thai narrative `research_log/002-lily-l1-baseline.md`. It must state the scoped question, hypothesis, method, results, discussion and limitations, conclusion, and next research direction in language that can be understood without opening JSON first.

## 6. Acceptance Gate

E2 requires all of the following:

1. preregistration and locked-gate integrity;
2. implementable net PnL with spread, commission, slippage, roll/currency costs, and turnover;
3. sample adequacy against zero, matched benchmark, and minimum acceptable nulls using autocorrelation-adjusted effective observations;
4. PSR threshold and DSR/search-log handling;
5. regime matrix including trend/whipsaw, volatility, asset sleeve, country/region, major subperiod, and crisis behavior, or explicit scope restrictions;
6. big-trend/outlier dependency and concentration analysis;
7. survivorship, inception, backfill, and futures-roll controls;
8. an independent adversarial review with no unresolved critical blocker.

Paper trading after E2 validates operations, not edge. An earlier E0 dry run must contain `edge_claim: none`.

## 7. Family Stop And Resurrection

After three consecutive adequately powered falsifications of distinct edge/mechanism hypotheses, stop new family expansion and run a Lily family review. L-0 and engineering/data failures are excluded.

Each kill needs a mechanism autopsy. Resurrection requires a new registry entry and a new testable prediction.

## 8. Data Purchase Rule

No paid data through L-0. Cumulative guard through L-1 is USD 50.

A purchase is rejected unless it:

1. serves a named hypothesis and gap;
2. cannot be filled from cache/free sources;
3. funds falsification first or an affordable validation plan;
4. fits remaining guard room using a live estimate;
5. is the smallest recoverable block;
6. records the selected key environment name and true provenance without recording its value.

If MinTRL validation cost is unaffordable or undefined against the benchmark null, revise or falsify; do not buy completionist data.

## 9. Broker And Credential Rule

- Webull Thailand: preferred current-capital ETF candidate; fractional API capability remains unverified.
- IBKR: micro-futures/reference API candidate; actual permissions remain unverified.
- No shared Higanbana credentials or cost state.
- No tracked credentials, account identifiers, or absolute local paths.
- Broker order transmission is outside this plan until E3 and separate owner approval.

## 10. Current Status

| Program/track | Status | Next gate |
|:--|:--|:--|
| Founding decisions | Complete | pushed founding pack |
| P0–P4 | Not started | B0 bootstrap |
| L-0 | Scope-restricted E0 feasibility complete | Broker capability remains unverified |
| L-1 | Active; preregistration locked | B4 falsification window |
| L-2 | Proposed | L-1 evidence |
| L-3 | Proposed | baseline infrastructure and preregistration |
| L-4 | Proposed | universe/data integrity and preregistration |

## 11. Source Lineage

- Lily `docs/DECISION_RECORD_001_PROJECT_REFOUNDING.md` and `experiments/hypothesis_registry.json`: promoted L-1 through L-4 rationale and predictions.
- Archived Lily `Backup_/2026-07-15/IMPLEMENT_PLAN.md`: baseline/candidate/sizing/cost inputs.
- Higanbana `docs/FABLE5_UPGRADE_PROPOSAL.md`: registry, tiers, dual MinTRL, data decisions, tracks, and acceptance gate.
- Higanbana `docs/HIGANBANA_TECHNICAL_DUE_DILIGENCE.md`: B0/P1/P2/P4 requirements.
- Higanbana `experiments/dd_remediation_tracker.json`: evidence-backed order completion.

Lily changes the statistical observation model for persistent trend positions and adds country/asset breadth, survivorship, futures-roll, and small-account sizing gates.
