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

### B4.1 — L-1 Data-Quality Remediation

Without opening validation, reconcile corporate actions, acquire dated official fee evidence, replace zero cash with a lagged Treasury series, and classify Webull Thailand capability from public evidence. The completed order must retain E1, state every unresolved point-in-time or broker restriction, and write `research_log/003-lily-l1-data-quality-remediation.md`.

Exit: cash is resolved at E1; fee uncertainty is either reconstructed or decision-bounded; corporate-action and broker gaps are either resolved or explicitly scope-restricted; no E2, edge, or deployment claim is allowed.

### B4.2 — L-1 Validation Funding Capacity

Before any validation unlock, count the sealed window using calendar rules only and project effective observations with the dependence fields from the prior opened stage exactly as locked in B3. Do not request or load validation prices, returns, signals, regimes, positions, benchmarks, or PnL.

Exit: classify every validation null as statistically funded or underfunded, report the founding planning assumptions as a non-binding sensitivity, and retain all data-integrity and owner-approval blockers. Provider credentials may be used only for an explicitly authorized zero-spend metadata probe with true key provenance and no credential value stored.

### B4.3–B4.4 — Alpha Vantage Corporate-Action Audit

B4.3 locks the exact free 8-symbol by 2-endpoint acquisition, credential redaction, hashes, validation-return seal, and current-snapshot claim limit. B4.4 executes only that matrix and compares pre-2016 corporate-action events without loading validation prices or returns.

Exit: B4.4 completes 16/16 payloads at USD 0 and remains E1 scope-restricted because only 11/16 symbol-endpoint pairs reconcile exactly and Alpha Vantage has no point-in-time revision archive.

### B4.5 — Owner Scope Decision

The owner accepts the unresolved corporate-action history as an E1 limitation and pauses further free or paid provider search. This does not unlock validation, authorize paper trading, or promote L-1.

A later prospective comparison is allowed only through a separate hash-locked `E0` operational dry-run preregistration with `edge_claim: none`. It must lock the comparison streams, event/cash/unit/weight/order fields, materiality thresholds, insufficient-event rule, and stop conditions before the first observation. Complete the Webull Thailand read-only capability probe first; broker preview and order actions remain forbidden.

### B4.6 — Webull Thailand Read-only Capability Probe

B4.6 locks and executes a production read-only probe against the owner's Webull Thailand application. Authentication, account list, balance, positions, and one exact ten-symbol instrument query are allowed; private account values, preview, order, paper trade, validation access, and real money are forbidden.

Exit: all four read-only endpoints succeed, and VTI, VGK, EWJ, IPAC, VWO, IEF, SCHP, GLDM, PDBC, and VNQI return `status=OC` and `fractionable=true`. This is E0 operational evidence only. Minimum order, funding FX, execution quality, and realized costs remain outside the claim.

### B4.7 — Prospective Shadow-Accounting Preregistration

B4.7 locks an `E0` design before any prospective observation. It compares a Webull Thailand paper ledger, an Alpha Vantage current-snapshot shadow ledger, and Lily's Yahoo-event accounting on the frozen L-0 ten-sleeve portfolio. Materiality is account-scaled for cash, units, weight tracking, hypothetical order notional, and posting delay; opposite discrepancies cannot be netted.

Exit: gate `l_1_prospective_shadow_accounting_v1` is hash-bound with at least 180 days and three matched events across two symbols required, a 365-day hard stop, and explicit insufficient-evidence and claim rules. No API call, event observation, activation, preview, paper order, validation access, signal, PnL, E2, edge, or real-money action occurs in B4.7.

### B4.8 — Activation Contract (Complete: Activation Blocked)

Before the dry run begins, separately lock the paper environment and exact endpoints, broker fractional quantum, forward start/stop timestamps, immutable redacted containers, event-ledger implementation, hermetic fixtures, report validator, request/cost limits, and order attestation. If Webull cannot expose an auditable paper ledger, stop; do not substitute production or real money.

Exit: B4.8 locks `activation_blocked_before_observation`. Public Webull Thailand evidence does not establish a dedicated owner-controlled test ledger, account-level corporate-action cash/unit paths, or the minimum fractional-share quantum. Runtime allowlists and request caps remain empty/zero, no activation marker exists, and no broker/provider call or prospective observation occurred. Activation requires written Webull Thailand confirmation and a new owner-approved gate that supersedes B4.8.

### B4.9 — Webull API Scope And Fractional-preview Preregistration (Complete)

B4.9 accepts the published Webull Thailand API inventory as the current boundary. Account-level corporate-action event, cash, unit, dividend, and split ledgers are classified as unavailable; the B4.7 three-stream dry run is closed without observation. Alpha Vantage and Lily Yahoo accounting remain limited research streams and neither is promoted to ground truth.

Exit: gate `l_1_shadow_accounting_activation_v2` supersedes the B4.8 gate and preregisters, but does not execute, a UAT-only VTI preview grid of eight fixed quantities from 1 through 0.0000001. Only `POST /openapi/trade/order/preview` may be considered by the later machinery and activation orders. Production, balance, positions, AMOUNT mode, retries, order mutation/query endpoints, validation access, paper trading, and real money remain forbidden.

### B4.10 — UAT Fractional-preview Machinery Gate (Complete, Not Executed)

B4.10 implements and hash-locks the fail-closed runner, exact Thailand UAT request path, eight-value VTI QTY grid, request caps, report schema/validator, and three hermetic fixtures. The runner requires both `--execute` and a future active `l_0_webull_th_fractional_preview_activation_v1` gate before it reads credentials or imports the SDK.

Exit: gate `l_0_webull_th_fractional_preview_probe_v1` is active with machinery status `locked_machinery_ready_execution_not_authorized`. B4.10 makes zero Webull, provider, authentication, preview, order, or validation requests and creates no experiment report or research log. The next possible order is a separately owner-approved B4.11 activation gate; it may not authorize production, balance, positions, order mutation/query, validation access, paper trading, or real money.

### B4.11 — UAT Fractional-preview Activation And Execution (Complete: Blocked Before Preview)

The owner approves one bounded execution of the exact B4.10 matrix. Gate `l_0_webull_th_fractional_preview_activation_v1` must be committed and pushed before the runner may read the three `WEBULL_UAT_*` variables, import the SDK, authenticate, or preview.

Exit: the activation gate was committed and pushed before execution. The one guarded run used the official shared UAT row in process memory, made one token-create and two token-check requests, and stopped when the guard blocked authentication request four. Preview requests, orders, production calls, provider calls, validation access, and paid spend are all zero. Report and Thai research log 007 classify the result as `blocked_before_preview`; no fractional minimum is known and rerun requires a new superseding gate.

### B4.12 — UAT Authentication-budget Remediation (Complete: Blocked Before Preview)

B4.12 preserves every locked B4.10/B4.11 file and creates a new superseding activation artifact, runner, report schema, validator, and tests. It funds a fixed 30-second SDK polling window with one token-create request and at most seven token checks, while retaining the exact eight-value VTI preview grid and a sixteen-request total cap. Automatic retry, token persistence, production, orders, balance, positions, providers, validation access, paper trading, and real money remain forbidden.

Exit: gate commit `152c8e1e8ecc946b889472707b4b3280e63d4e02` was pushed and passed Hermetic CI before execution. The one authorized run made one token-create and seven token-check requests over 30 seconds, but authentication remained non-NORMAL. The run stopped with zero previews, orders, production calls, provider calls, validation access, or paid spend. The redacted v2 report and Thai research log 008 record `blocked_before_preview`; the evidence ceiling remains E0 and no rerun is authorized.

### B4.13 — UAT Documentation Scope Decision (Complete)

B4.13 records that the SDK markdown reference to `th-api.uat.webullbroker.com` does not establish a publicly available UAT service or an access entitlement for Lily. The inspected public pages are the Trade API and Market Data API getting-started pages; they do not document owner-controlled UAT provisioning or non-interactive authentication.

Exit: UAT is closed as an unsupported path for Lily. This static E0 decision makes no broker or provider call, changes no locked gate, and does not establish a broker defect, preview result, production capability, execution result, or strategy evidence.

### B4.14 — Project-memory Synchronization (Complete)

B4.14 aligns project memory with B4.13. No UAT work is planned, and the UAT hostname is not treated as a public test-environment entitlement. L-0 remains scope-restricted E0, L-1 remains scope-restricted E1, and validation stays sealed.

### B4.16 — Governance Content-validation Remediation (Complete)

B4.16 responds to the independent review finding that B4.13–B4.15 completion checks were too weak. The tracker now validates the inspected source list and claim limits in Decision Record 004, the UAT-closure statements in project memory, and the exact `actions/checkout@v5` requirement in CI.

### B5 — L-2 Multi-Lookback t-stat Candidate Preregistration (Complete)

B5 locks the 32/64/126/252 equal-weight t-stat candidate against the 60-day baseline. Candidate and baseline inherit the same L-1 universe, timing, sizing, costs, return accounting, benchmarks, sample order, and data-integrity rules. The primary utility is paired annualized net-Sharpe improvement of at least 0.10; the complete DSR log contains the primary candidate and four leave-one-horizon-out sensitivities.

Exit: gate `l_2_multi_lookback_tstat_v1` is hash-bound before execution. Dual MinTRL is locked on paired portfolio-return differences, and the 2016-01-04 through 2026-06-30 validation window remains sealed. B5 makes no market-data, broker, provider, paid, paper-trading, or real-money request and creates no L-2 performance result.

### B5.1 — L-2 Preregistration Inference Remediation (Complete)

B5.1 preserves B5 v1 and appends superseding gate `l_2_multi_lookback_tstat_v2`. Its primary comparator is the equal-weight 32/64/126/252 directional-count signal, so candidate and comparator share horizons as well as all inherited L-1 portfolio plumbing. The L-1 60-day baseline is a secondary descriptive reference only.

The primary utility, MinTRL, PSR, and DSR input is the same paired daily net active-return series. Annualized planning Sharpes are divided by `sqrt(252)` before calling the per-period MinTRL kernel; locked requirements are 54,048 for falsification, 54,056 for no-improvement validation, and 216,218 for minimum-useful-improvement validation. The unambiguous decision matrix and DSR active-return trial inventory remain pre-execution only; validation remains sealed.

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

- Webull Thailand: preferred current-capital ETF candidate; B4.6 verifies production read-only access plus `status=OC` and `fractionable=true` for all ten current candidates, while minimum order, funding FX, execution quality, and realized costs remain unverified.
- IBKR: micro-futures/reference API candidate; actual permissions remain unverified.
- Databento: metadata access through `DATABENTO_API_02` is verified with zero spend; relevant equity coverage begins in 2018 or later and does not expose the required corporate-actions history. The owner-reported USD 50 credit is ineligible for paid use until real-payment provenance is confirmed.
- No shared Higanbana credentials or cost state.
- No tracked credentials, account identifiers, or absolute local paths.
- Broker order transmission is outside this plan until E3 and separate owner approval.

## 10. Current Status

| Program/track | Status | Next gate |
|:--|:--|:--|
| Founding decisions | Complete | pushed founding pack |
| P0–P4 | Active after bootstrap | Maintain governance, reproducibility, statistics, data, and restore controls |
| L-0 | Scope-restricted E0; B4.6 verifies production read-only and fractional metadata; B4.11/B4.12 stop before preview; B4.13 confirms the UAT hostname is not a public access entitlement | No UAT work planned; fractional minimum, funding FX, execution quality, and realized-cost evidence remain open |
| L-1 | Scope-restricted E1; B4.9 closes the unavailable Webull-ledger dry run without observation; B4.10 adds no L-1 evidence | Validation remains sealed; no broker-ledger or historical-correctness claim |
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
