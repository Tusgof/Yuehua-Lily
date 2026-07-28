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

Current machine status is authoritative in `experiments/hypothesis_registry.json`: L-0 is scope-restricted after E0 sizing evidence; L-1 is scope-restricted after E1 falsification-window, data-quality remediation, and validation-capacity evidence, while its validation window remains sealed; L-2 is E1 underfunded/scope-restricted; L-3 is E1 scope-restricted after its invalidated B7.3 run, with B7.5 as E0 corrected no-data governance; L-4 is active planning E0 only.

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

- **Verified date**: 2026-07-28
- **Bootstrap**: B0 through B4.16 complete; B5.2 and B6.4 L-2 remediation complete; B7 L-3 governance lock, B7.2 hermetic source-provenance remediation, and B7.1 locked E0 gate-only preflight complete
- **Legacy Note status**: retired and deleted by `docs/DECISION_RECORD_002_RESEARCH_LOG_CONTRACT.md` after its research content was promoted
- **Human research logs**: contract active; L-0 sizing and Webull capability are logs 001 and 006; L-1 baseline, remediation, validation-capacity, and Alpha Vantage corporate-action audits are logs 002 through 005 under `research_log/`
- **Dashboard**: retained under `Dashboard/`, demoted from product/state owner
- **Founding decisions**: `docs/DECISION_RECORD_001_PROJECT_REFOUNDING.md`
- **Registry**: L-0 scope-restricted E0; L-1 scope-restricted E1; L-2 E1 underfunded_scope_restricted; L-3 E1 scope-restricted after its one-run invalidation; L-4 active planning E0 with edge_claim none
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
- **UAT documentation scope**: B4.13 confirms that the SDK markdown reference to a Thailand UAT hostname is not evidence of public UAT availability or Lily access entitlement. The inspected public pages are the Trade API and Market Data API getting-started pages; no owner-controlled UAT provisioning or non-interactive authentication path is documented there
- **Project-memory synchronization**: B4.14 records the UAT branch as closed with no planned UAT work; it changes no locked artifact, evidence tier, hypothesis status, or validation boundary
- **CI runtime maintenance**: B4.15 updates the Hermetic CI checkout action from v4 to v5 to remove the observed Node.js 20 deprecation path; the pinned Python, hermetic test, and tracker-validation steps remain unchanged
- **Governance content validation**: B4.16 makes tracker completion for B4.13–B4.15 validate the UAT decision sources and limits, synchronized project-memory statements, and the exact checkout v5 requirement
- **L-2 candidate preregistration**: B5.2 supersedes B5.1 without altering v1/v2; it locks shared decision index t and return window r[t-k], k=0..h-1, for the 32/64/126/252 t-stat candidate and matched-horizon comparator, executes both at t+1 close, retains L-1 60-day only as secondary reference, and keeps validation sealed
- **L-2 falsification machinery**: B6 locks the v2/v3 overlay, synthetic report contract, and fail-closed runner; it makes zero market-data, validation, broker, provider, paid, paper-trading, or real-money request. B6.1 requires a new owner-approved activation gate before any falsification-only container may be inspected
- **L-2 report-contract remediation**: B6.2 supersedes B6 only for report validation. The closed-world v2 report validator binds active-contract/v2/v3/git provenance and requires all locked decision evidence before it can accept a falsified or not-falsified result; B6.1 remains unauthorized
- **L-2 capacity gate**: B6.3 establishes a no-return upper bound of 26,016 joint independent-bet equivalents, below the locked 54,048 `MinTRL_falsify`; L-2 is E1 underfunded_scope_restricted and B6.1/container inspection is forbidden unless a separately approved preregistration redesign changes the statistical capacity
- **L-3 inverse-volatility sizing gate**: B7 locks L1 research_signed eight ETFs; q/volatility versus q under identical weekly inherited constraints; weekly paired component-risk HHI delta with a 0.05 useful reduction; ex-ante plus fixed-weight realized confirmation; side-effect limits; `MinTRL_falsify` 49 and binding `MinTRL_validate` 49; independently funded regimes with an optimistic 366-slot ceiling; E0/edge none and validation sealed. B7.2 makes v2 active by superseding only v1 external-Wiki source verification with hermetic source-provenance snapshots; research semantics remain unchanged. B7.1 locked E0 gate-only preflight source-binds v2/v1/L1 and the seal; all six authorization flags false, so it authorizes neither data/container inspection nor execution.
- **L-3 B7.3 one-run result**: the one authorized falsification run used only the sealed falsification container but included 500 weekly observations, exceeding the locked 465 ceiling. The provisional result is invalidated; L-3 is E1 scope_restricted, edge_claim none, validation sealed, and no rerun is authorized.
- **L-3 B7.4 ledger remediation**: preserves the original ledger row and adds one hash-bound invalidation event. The original ledger decision and every provisional metric are invalid; `scope_restricted` is the sole authoritative state. B7.4 read zero market returns and opened no validation.
- **L-3 B7.5 corrected rerun schedule gate**: E0 no-data governance only. It source-binds B7.1/B7.3/B7.4 history and preserves all L-3 research semantics while locking decisions no earlier than 2007-02-05, complete t+20 confirmation by 2015-12-31, the 465 weekly-pair ceiling, a date-only hash-bound pre-return schedule attestation, and fresh report/ledger paths. All authorizations are false; B7.3 remains invalidated E1 scope_restricted, validation sealed, and edge_claim none. The owner authorization wording remains an exact B7.5 control mirror.
- **L-3 B7.6 corrected attempt**: hard-stopped at `date_only_schema_metadata_missing` before return parsing. It produced an E1 scope-restricted preflight report with zero market-return reads and no fresh schedule attestation or ledger row; validation remains sealed and edge_claim none.
- **L-3 B7.7 remediation**: E0 synthetic-only v2 machinery supersedes the defective B7.6 execution contract, with field-aware per-symbol common-session design, explicit side-effect diagnostics, and a closed-world future report contract. It opens no data or execution path.
- **L-3 B7.8 remediation**: E0 synthetic-only supersession of B7.7’s defective execution-contract machinery. The hash-bound v3 gate leaves all authorizations false and verification is hermetic; no container, return, schedule attestation, execution, ledger, or validation access occurs. L-3 remains E1 scope-restricted, validation sealed, edge_claim none.
- **L-3 B7.9 remediation**: E0 synthetic-only adversarial supersession of B7.8/v4 machinery. The v5 gate binds B7.7/v2, locked science, exact implementation hashes, and committed synthetic identity fixtures; it rejects individual post-end sessions before intersection, recomputes decision evidence, leaves all fourteen authorizations false, and opens no container, return, schedule attestation, execution, report decision, ledger, or validation path. L-3 remains E1 scope-restricted, validation sealed, edge_claim none; no rerun is authorized.
- **L-3 B7.10 remediation**: E0 synthetic-only decision-integrity supersession of B7.9/v5. The v6 gate preserves v5 and recomputes locked five-lag UCB/MinTRL arithmetic, HHI/event/regime constraints, and mutually exclusive decisions using synthetic fixtures only; all fourteen authorizations remain false, validation sealed, and edge_claim none. No rerun is authorized.
- **L-3 B7.11 remediation**: B7.10 Inspector rejection is recorded: v6 trusted reporter-authored summaries, accepted MinTRL/effective-bet mismatches, and permitted synthetic E1 decisions. B7.11 supersedes only that machinery with an E0 synthetic-only, hash-bound closed-world weekly-observation vector. v7 derives HHI deltas, sample dependence statistics, raw-observation MinTRL, regime funding, and side-effect limits itself; all fourteen authorizations remain false, validation sealed, edge_claim none, and no rerun is authorized.
- **L-3 B7.12 remediation**: v8 preserves immutable v7 and fixes its inclusive-boundary float error, absent runner fixture, and incomplete golden coverage. It binds a committed E0-only synthetic report by actual file and observation hash; deterministic decimal comparisons accept exact 20% and 10-point limits and reject attainable breaches. All fourteen authorizations remain false, validation sealed, edge_claim none, and no rerun is authorized.
- **L-3 B7.13 v3 contract**: restores the v2 manifest row byte-for-byte, then adds the only allowed direct correction for its missing `human_approval`. The immutable v3 E0 gate preserves B7.6 artifact/validator lineage and the approved synthetic metadata identity. No container is exposed or opened; B7.14 remains unauthorized.
- **L-3 B7.14 v3, B7.14R/v4, and B7.14R3/v5 rejected**: v3 decoded a skipped timestamp; v4 lacked complete bindings/contracts; v5's inert runner failed the shared-lib script audit. B7.14R4/v6 is E0 synthetic-only remediation with the runner fixed; no further container access is authorized.
- **L-3 B7.14R7/v9 rejected; B7.14R8/v10 complete E0**: v9 failed Phase A. v10 commits snapshot-only predecessor/recovery proof at `d2a9001`, passed CI 30351502467, and closed at `cf0fa3d` with CI 30351716462. All fourteen authorizations are false; validation is sealed; L-3 remains E1 scope_restricted and unresolved, with no rerun or edge claim.
- **L-3 B7.15 current-preregistration closure**: L-3 remains E1 scope_restricted and unresolved, not falsified or validated; no rerun is planned under the current preregistration; validation is sealed; edge_claim none; no L-3 result may be carried forward as proof that inverse-volatility sizing passed.
- **L-4 B8/B8.1/B8.2/B8.3 preregistration**: B8.3 v4 supersedes prior gates without changing v1/v2/v3. The E0/no-data contract keeps U1 descriptive-only, fixes `u=q` (no volatility division), matched U4/U8, exact 465 weekly-paired capacity, macro sleeves, component-risk HHI/`N_eff` missingness, three-plan MinTRL, exact robustness/side-effect and regime controls, and exhaustive four-outcome validation precedence. It creates no breadth evidence; `edge_claim none`, validation sealed, and all authorizations are false.
- **L-4 B8.4 preflight machinery**: Inspector accepted B8.4R2/v3 at commit `bb9f4c1527aade97cc7ede1b19048cfa93a3cc16` after Exact-SHA CI run `30367686488` passed. B8.4 v1 and B8.4R v2 remain immutable CI-defective history; v3 source-binds v4 without superseding its science and permits only synthetic structural preflight fixtures. Any future real container must be structurally checked before return parsing and fail closed on date/schema/path/hash/membership ambiguity or a post-2015-12-31 session. E0 only, `edge_claim none`, validation sealed.
- **Operating roles**: Lily's persistent GPT-5.6 Terra high subagent is the primary implementation Worker for sequential bounded orders. The root agent is Inspector, owns inspection and `research_log` authorship/decision, and the Worker must hand off and wait for Inspector acceptance before a next order.
- **Databento**: `DATABENTO_API_02` passes metadata access with USD 0 spend, but relevant US-equity coverage begins in 2018 or later and no dedicated corporate-actions history was exposed; owner-reported USD 50 credit has unverified real-payment provenance

## 11. Next Safe Action

Keep validation returns sealed and do not rerun B4.11, B4.12, B7.3, B7.6, or B7.14. L-3 is E1 scope_restricted and unresolved; no L-3 result may be carried forward as proof that inverse-volatility sizing passed. B8.4R2/v3 is Inspector-accepted. The next safe action is an owner decision on whether to authorize a separately locked B8.5 real-container preflight; until then, no real-container discovery/read/hash/scan, data, execution, report decision, or validation access is authorized. No UAT work is planned: a hostname reference is not a public UAT entitlement.

Historical control compatibility: B4.14 records no UAT work and requires a new locked gate for any future broker probe. The next safe action, for a later order, is L-4 preregistration/planning only; B7.15 authorizes no L-4 work. B8.3 was accepted after Inspector review of B8.3 only. These are historical statements, not the current next action. B8 E0/edge_claim none validation controls retain U1, U4, U8, and B8.1 N_eff; B8.3's 465 weekly-paired, macro sleeves, four-outcome, and all-authorizations-false controls remain intact through accepted B8.4R2/v3.

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
