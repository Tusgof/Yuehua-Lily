# PROJECT_BRAIN.md

## 1. Project Definition

Lily is a systematic trend-following research program. Its purpose is to determine, with reproducible and implementable evidence, whether trend continuation can support a globally diversified strategy and what capital is required to trade it honestly.

The research program is the product. A dashboard, backtest, paper account, or broker integration is only a supporting artifact.

## 2. Current Research Thesis

The owner-authored mechanism and predictions were promoted during refounding into `docs/DECISION_RECORD_001_PROJECT_REFOUNDING.md` and `experiments/hypothesis_registry.json`. Legacy `Note/` files were retired by Decision Record 002.

The proposed mechanism is slow information diffusion followed by herding, which can create continuation rather than immediate reversal. The intended payoff is divergent: many small losses are accepted in exchange for occasional large trends. The mechanism depends on system architecture, especially trend duration, breadth, volatility-aware sizing, and cost control.

The pre-refounding design inputs from the archived `IMPLEMENT_PLAN.md` are:

- baseline: 60-day directional count;
- candidate: multi-lookback t-stat / delta-straddle interpretation;
- sizing direction: `signal × risk weight / volatility`;
- leverage: portfolio target volatility and caps, never ad hoc per-asset leverage;
- trust rule: include realistic costs before judging results;
- honesty rule: unknowns remain explicit and are never guessed.

These are prior design inputs, not validated findings.

## 3. Research Standards

### Evidence Tiers

| Tier | Meaning | Allowed claim |
|:--|:--|:--|
| E0 | Infrastructure, fixtures, synthetic evidence, or operational dry run | The machinery works. No edge claim. |
| E1 | Real-data diagnostic that is under-sampled, underpowered, or blocked | Hypothesis-generating only. |
| E2 | Preregistered validation passes statistics, regimes, robustness, costs, and adversarial review | Edge exists only in the tested scope. |
| E3 | E2 plus operational validation, account feasibility, and launch checklist | Eligible for a separate owner decision about real money. |

Any acceptance language below E2 is a blocker. Paper trading is allowed only after E2 or as a labeled E0 dry run with `edge_claim: none`.

### Preregistration And Falsification

- Hypotheses own experiments; experiment IDs are foreign keys.
- Each run locks the observation unit, benchmark null, costs, regimes, search space, validation rule, falsification rule, and outputs before results are observed.
- Fund `MinTRL_falsify` before `MinTRL_validate`.
- A kill needs both preregistered statistical evidence and a mechanism autopsy.
- Resurrection uses a new ID and at least one new prediction.
- Scope restriction is a first-class result.

### Trend-Specific Statistics

Trend positions persist and overlap. Do not treat raw trade counts as independent observations.

Before any real backtest, the statistics kernel must:

- use autocorrelation-adjusted Sharpe variance and report lag choices;
- report effective independent-bet-equivalent counts alongside calendar and trade counts;
- use PSR for Sharpe inference and DSR when signals, parameters, universes, or filters were searched;
- use HAC/Newey-West-style inference for mean return or alpha where appropriate;
- pin skewness, kurtosis, annualization, excess-return, and missing-data conventions;
- pass golden-number tests anchored to published worked examples and an offline reference implementation.

Primary local methodology pages include:

- `wiki/questions/trend-following-research-track-synthesis.md`
- `wiki/concepts/directional-count-trend-signal.md`
- `wiki/concepts/multi-lookback-trend-following.md`
- `wiki/concepts/inverse-volatility-weighting.md`
- `wiki/concepts/target-volatility.md`
- `wiki/concepts/trend-following-transaction-cost-control.md`
- `wiki/concepts/minimum-track-record-length.md`
- `wiki/concepts/probabilistic-sharpe-ratio.md`
- `wiki/concepts/deflated-sharpe-ratio.md`
- `wiki/concepts/newey-west-validation.md`
- `wiki/concepts/global-trend-regime-diversification.md`

Preregistrations must record wiki-relative paths and SHA-256 values so later wiki edits cannot rewrite the historical basis.

## 4. Hypothesis Registry

Authoritative files:

- human view: `docs/HYPOTHESIS_REGISTRY.md`
- machine view: `experiments/hypothesis_registry.json`

Seed order:

1. L-0 — capital and broker sizing feasibility;
2. L-1 — 60-day baseline continuation after costs;
3. L-2 — multi-lookback candidate versus matched-horizon baseline;
4. L-3 — inverse-volatility sizing versus equal notional;
5. L-4 — breadth versus single-market dependency.

Current machine status is authoritative in `experiments/hypothesis_registry.json`: L-0 is scope-restricted after E0 sizing evidence; L-1 is scope-restricted after E1 falsification-window, data-quality remediation, and validation-capacity evidence, while its validation window remains sealed; L-2 through L-4 remain proposed.

The family review triggers after three consecutive adequately powered falsifications of distinct edge/mechanism hypotheses. L-0 and engineering failures do not count.

## 5. Capital, Broker, And Universe Decisions

- Capital is separate from Higanbana: USD 1,000–2,000.
- Research is primary; implementation studies report both current-capital feasibility and minimum capital.
- Current-capital implementation candidate: 8–12 US-listed fractional ETFs whose underlying exposures are globally diversified across countries and asset classes.
- Webull Thailand is the preferred ETF operational candidate because of usability and fractional execution.
- IBKR is the reference broker for micro-futures feasibility and broader API capability.
- Webull Thailand production read-only and fractional metadata support for the current ten-ETF set passed B4.6; minimum order, funding FX, execution quality, and actual IBKR permissions remain unverified.
- Full-size futures are outside current-capital scope.
- Futures feasibility reports minimum capital for 4, 8, and 12 markets using one-contract granularity, margin, volatility, cash buffer, costs, and concentration limits.

The ETF branch is long/cash by default. It must not be represented as equivalent to a symmetric long/short futures CTA.

## 6. Data Standards

Daily bars are the initial frequency. Free or already-accessible data must be evaluated before purchase.

Every dataset plan must define:

- source and true provenance;
- field and timestamp semantics;
- instrument identifiers and corporate actions;
- inception and delisting treatment;
- survivorship and backfill controls;
- futures contract selection, roll rule, and adjusted/unadjusted series purpose;
- missing sessions, holidays, currencies, and FX conversion;
- raw, normalized, and derived boundaries;
- schema validation at ingest;
- cost and re-downloadability.

Hard-to-reproduce data uses raw/container and canonical/content hashes. Free re-downloadable daily data may use documented container hashes until the first hard-to-reproduce artifact arrives.

## 7. Cost Policy

- Paid-data guard is USD 0 through L-0 and cumulative USD 50 through L-1.
- Lily uses one real funded provider account and records true per-key provenance.
- No shared Higanbana budget, keys, ledger, or credentials.
- A purchase must serve a named registry gap, exhaust cached/free alternatives, fund falsification before validation, fit remaining room, and use the smallest recoverable block.
- If validation sample cost exceeds remaining room or MinTRL is undefined against the benchmark null, validation purchase is forbidden; revise, narrow, or falsify instead.

## 8. Repository Architecture Before Research Code

The bootstrap order must create:

- pinned Python and a dependency manifest;
- hermetic and state-audit test tiers;
- CI on every push;
- environment-variable/untracked-manifest resolution with zero absolute paths in active project artifacts; immutable `Backup_/` history is excluded from the check;
- `lib/` for hypothesis-independent IO, timestamps, statistics, guardrails, provenance, and reporting;
- golden-number statistics tests;
- hypothesis-registry and evidence-tier validators;
- append-only locked-gate hashes and validator;
- machine-checkable tracker and done-claim validator;
- data integrity registry and provider-boundary schemas;
- `docs/BACKUP_AND_RESTORE.md` plus one restore rehearsal.

Past reports are reproduced by checking out their recorded commit hash. Do not create one copied helper set per experiment.

## 9. Project Memory And Interfaces

- Git-tracked machine-readable files own state.
- `research_log/` contains numbered Thai explanations of completed experiments for human readers; `RESEARCH_LOG_FORMAT.md` and its audit define the contract.
- Exact values and state remain in reports, registries, locked gates, trackers, and Git; prose logs cannot override them.
- `Dashboard/` is optional visualization only. Its `localStorage` is non-authoritative and disposable.
- Decision history belongs in `docs/DECISION_RECORD_*.md`, registry decision logs, reports, and git.
- `PROJECT_BRAIN.md` remains concise and points to those stores.

## 10. Current Verified State

- **Verified date**: 2026-07-20
- **Bootstrap**: B0 through B4.12 complete
- **Legacy Note status**: retired and deleted by `docs/DECISION_RECORD_002_RESEARCH_LOG_CONTRACT.md` after its research content was promoted
- **Human research logs**: contract active; L-0 sizing and Webull capability are logs 001 and 006; L-1 baseline, remediation, validation-capacity, and Alpha Vantage corporate-action audits are logs 002 through 005 under `research_log/`
- **Dashboard**: retained under `Dashboard/`, demoted from product/state owner
- **Founding decisions**: `docs/DECISION_RECORD_001_PROJECT_REFOUNDING.md`
- **Registry**: L-0 scope-restricted E0; L-1 scope-restricted E1; L-2 through L-4 proposed
- **L-1 falsification execution**: complete through 2015-12-31; not falsified, not validated; validation sealed
- **L-1 data-quality remediation**: cash resolved at E1; historical fees decision-bounded; corporate actions pass the locked daily tolerance for 6/8 symbols; the later B4.6 probe resolves Webull candidate-ticker and fractional OpenAPI capability for the current ten-ETF set
- **L-1 validation capacity**: 2,637 calendar-only sessions project to 20,376 joint independent-bet equivalents versus the binding 8,673 under locked actual dependence; planning sensitivity projects 7,604; validation remains sealed
- **Alpha Vantage corporate actions**: B4.4 completed 16/16 free payloads in 16 attempts and stored 772 rows; 11/16 pre-2016 symbol-endpoint pairs reconcile exactly while five dividend pairs do not; the source is a current snapshot without point-in-time revisions, so the result remains E1 scope-restricted and validation stays sealed
- **Owner scope decision**: B4.5 accepts the unresolved corporate-action history as an E1 limitation and pauses additional source search; a future comparison is allowed only through a separately locked E0 shadow-accounting dry run that tests operations, not edge or historical correctness
- **Webull Thailand capability**: B4.6 production read-only authentication, account list, balance, and positions succeeded; all ten current ETF candidates returned `status=OC` and `fractionable=true`; no private account values, preview, order, paper trade, paid spend, or validation data were exposed
- **Shadow-accounting gate**: B4.7 locks the three streams, fixed L-0 ten-sleeve accounting portfolio, account-scaled materiality thresholds, no-netting rule, minimum evidence, 365-day stop, and claim limits
- **Shadow-accounting activation**: B4.8 stopped before observation because Webull Thailand does not publish the required account-level corporate-action ledger; its v1 activation gate is preserved as superseded history
- **Webull API scope decision**: B4.9 accepts the published Thailand API as the current capability boundary, closes the B4.7 three-stream dry run as not started, retains Alpha Vantage and Lily Yahoo accounting as limited non-ground-truth research streams, and locks but does not execute an eight-request VTI UAT fractional-preview design
- **Fractional-preview machinery**: B4.10 hash-locks the fail-closed runner, exact Thailand UAT path and VTI QTY grid, report schema/validator, and three hermetic fixtures; it performs zero API calls and cannot execute without a separate B4.11 activation gate
- **Fractional-preview execution**: B4.11 completed with `blocked_before_preview`; token create plus two token checks consumed the three-request authentication cap and the guard blocked the fourth attempt, leaving zero previews, orders, production calls, paid spend, or validation access
- **Authentication-budget remediation**: B4.12 preserved the locked B4.10/B4.11 files and executed only after the v2 gate commit passed CI. One token create plus seven checks used the full 30-second window without reaching NORMAL, so the result is `blocked_before_preview` with zero previews, orders, production calls, provider calls, validation access, or paid spend
- **Databento**: `DATABENTO_API_02` passes metadata access with USD 0 spend, but relevant US-equity coverage begins in 2018 or later and no dedicated corporate-actions history was exposed; owner-reported USD 50 credit has unverified real-payment provenance

## 11. Next Safe Action

Keep validation returns sealed, leave L-0 scope-restricted E0 and L-1 scope-restricted E1, and do not rerun B4.11 or B4.12. A further Webull UAT attempt requires new evidence such as a documented verification step or a dedicated test account, plus a new owner-approved gate; merely lengthening the polling window is insufficient justification. The next research order should be planned separately and must not open validation returns, production access, paper trading, or real-money actions.

## 12. Invariants

Never:

- claim edge from E0/E1 evidence;
- use browser state as project state;
- spend outside Lily's guard;
- infer a broker permission or fractional API feature;
- ignore survivorship, futures rolls, costs, serial correlation, or search history;
- weaken a locked gate and its validator in place;
- begin real-money execution without a separate E3 launch decision.

Always:

- compare the candidate against the matched-horizon baseline;
- report gross and implementable net results separately;
- report calendar observations, trade counts, and effective independent bets;
- record provenance, commit hash, environment, evidence tier, blockers, and scope;
- write the audited Thai research log required for every completed experiment;
- finish modifying sessions by pushing and reporting `origin/main` hash.

## 13. Source Lineage

### Lily Sources Kept

- `docs/DECISION_RECORD_001_PROJECT_REFOUNDING.md` and `experiments/hypothesis_registry.json`: promoted economic rationale, asymmetric payoff, architecture prerequisites, and predictions.
- `docs/DECISION_RECORD_002_RESEARCH_LOG_CONTRACT.md`: retirement of legacy notes and adoption of audited Thai experiment narratives.
- archived `Backup_/2026-07-15/IMPLEMENT_PLAN.md`: baseline, candidate, sizing, target-volatility, cost, and honest-unknown design inputs.

### Higanbana Sources Adapted

- `docs/FABLE5_UPGRADE_PROPOSAL.md`: evidence tiers, registry, dual MinTRL, data tree, kill/resurrection, and acceptance boundary.
- `docs/HIGANBANA_TECHNICAL_DUE_DILIGENCE.md`: self-verification, `lib/`, statistical anchors, locked gates, and control-plane limits.
- `AGENTS.md`: session closure, trailer, test tiers, and locked-gate rules.
- `experiments/dd_remediation_tracker.json`: evidence-backed required-artifact completion.

Lily excludes all 0DTE-specific logic and replaces per-trade assumptions with persistent-position trend inference.
