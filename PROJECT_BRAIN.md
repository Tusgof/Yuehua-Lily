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
- **L-4 B8.5 Phase A activation/order lock**: source-binds B8.4R2/v3, v4, the B8.4R2 report/runner/schema/fixture, and the sealed validation boundary. Phase A performs no environment or container access: all 24 authorizations are false and all access counts are zero. Phase B is not executed; only after Inspector acceptance and exact-SHA CI success may one preflight inspect structural U8 symbol/session-date metadata, rejecting missing/ambiguous U8, schema/path/hash mismatch, or each post-2015-12-31 session before return/value decoding.
- **L-4 B8.5R Phase A remediation**: Inspector rejected immutable v1 for unlocked future machinery and storage resolution. v2 hash-binds the scanner, runner, schema/validator, and synthetic envelope; future Phase B may resolve only `LILY_DATA_ROOT` plus literal paths and reports observed raw manifest/payload hashes. It remains E0 with all Phase-A seals false; Phase B is not executed and awaits Inspector acceptance.
- **L-4 B8.5R2 Phase A remediation v3**: v1/v2 remain immutable Inspector-rejected history. v3 hash-binds bounded read-attempt counters, multiple strictly ordered calendar-valid session dates for every exact U8 member, atomic durable consumption before environment access, fixed repo-relative report/attempt-marker paths, and real-report validation. It remains E0 with all Phase-A seals false; Phase B is not executed and awaits Inspector acceptance.
- **L-4 B8.5R3 Phase A remediation v4**: v1/v2/v3 remain immutable Inspector-rejected history. v4 locks capacity-derived bounded reads, accurate prefix-versus-complete provenance, first-report preservation on a second invocation, a later machine-readable Inspector/CI activation record, and an explicit CLI flag. It remains E0 with all Phase-A seals false; Phase B and activation are not executed.
- **L-4 B8.5R4 Phase A lifecycle remediation v5**: v4 is immutable Inspector-rejected history for circular lifecycle and incomplete pass binding. v5 locks a later tracked activation checkpoint bound to the accepted gate commit and Exact-SHA Hermetic CI, strict full pass correlations, and ancestor activation-blob provenance. It remains E0 with all Phase-A seals false; Phase B and activation are not executed.
- **L-4 B8.5R5 Phase A blocked-report remediation v6**: v5 is immutable Inspector-rejected history because blocked reports were not closed-world and accepted-gate provenance was incomplete. v6 locks exact blocked artifact transitions, closed runner categories, accepted-gate ancestry, and gate-blob proof. It remains E0 with all Phase-A seals false; Phase B and activation are not executed.
- **L-4 B8.5R5 Phase-B activation checkpoint**: Inspector `ACCEPTED` v6 commit `c8d358ee23b68e11ee02bb00eec17ee7f08128dd` after Exact-SHA Hermetic CI `30384415559`. The activation checkpoint is created with validation sealed and `edge_claim none`; Phase B remains unexecuted until this checkpoint commit passes Exact-SHA CI. Then exactly one Phase B CLI execution is the next safe action.
- **L-4 B8.5R5 one-shot Phase B**: the sole CLI call is consumed and blocked with `data_root_unavailable`. The report validates; manifest/payload reads and return/value/validation access are zero. Inspector `ACCEPTED` result commit `edc922cff688256472ec1f452a51535e296fc744` after Exact-SHA Hermetic CI `30386988365` and decided no new research log because this E0 control-plane pre-data hard stop produced no market observation, empirical experiment, L-4 metric, or scientific decision. The one-shot cannot be retried; L-4 remains unresolved E0, validation sealed, `edge_claim none`; do not infer a breadth/edge result. Its historical next step required a separately owner-approved container-provisioning/new-gate order.
- **L-4 B8.6 Phase A**: a new E0/no-data provisioning gate source-binds the exact repo-relative normalized Yahoo container and its expected hash, full structural schema, U8 order, cutoff, B8.5R5 no-retry lineage, and Inspector pre-gate hash-only incident. That incident is non-evidence and cannot satisfy a future one-shot. Activation and provisioning remain forbidden pending a later Inspector checkpoint.
- **L-4 B8.6R Phase A v2**: append-only Inspector remediation replaces the future machinery only. It uses the literal repo-relative container path (never `LILY_DATA_ROOT`), closed-world Draft 2020-12 report/activation/output contracts, opaque unsafe value lexemes, and accepted-gate ancestor/blob activation proof. It remains E0 with `edge_claim none`; no activation or provisioning occurs in this order.
- **L-4 B8.6R2 Phase A v3**: B8.6R v2 is Inspector-rejected history. v3 preserves it and closes blocked scanner outcomes, byte-only numeric lexemes, nested output closure, output-file identity binding, and hermetic Draft-subset schema evaluation. E0 only, validation sealed, `edge_claim none`; no activation or provisioning occurred.
- **L-4 B8.6R3 Phase A v4**: v3 is Inspector-rejected history. v4 restores closed blocker enumeration, real-report provenance and summary binding, output identities and cross-binding. E0 only, validation sealed, `edge_claim none`.
- **L-4 B8.6R4 Phase A v5**: v4 is Inspector-rejected history. v5 requires the canonical activation blob at the producing commit and validates every manifest/payload date, coverage, count, total, and output binding. E0 only, validation sealed, `edge_claim none`.
- **L-4 B8.6R5 Phase A v6**: v5 is Inspector-rejected history. v6 adds an activation-gated, one-shot runnable path; no activation or execution occurred. E0 only, validation sealed, `edge_claim none`.
- **L-4 B8.6R6 Phase A v8**: v5/v7 are Inspector-rejected recovery history. v8 uses one identity namespace for gate, activation, runner, report, and structural outputs. Synthetic E0 only; no dataset/container read, activation, execution, or validation access occurred. Inspector acceptance is required before any later activation checkpoint.
- **L-4 B8.6R7 Phase A v9**: v8 is Inspector-rejected because its report validator accepted a coherently forged synthetic success. v9 is an E0 remediation pending Inspector review: it requires exact activation bytes/schema plus accepted-gate ancestry/blob for a future production report, and validates bounded row counters, U8 membership, ISO pre-cutoff dates, coverage, totals, and persisted output identities. No dataset/container read, activation, execution, or validation access occurred; `edge_claim none` and validation sealed.
- **L-4 B8.6R11 Phase A v13**: B8.6R8/v10 remains immutable rejected E0 history. Checkpoint `2509213` is incomplete immutable v12 history, not a completion claim. v13 supersedes its semantic contract and enforces exact top-level and nested report fields alongside committed-bootstrap provenance, activation ancestry/blob, output, U8/date/hash, and validation-seal checks. It remains E0 pending Inspector review, with no data, activation, execution, or validation access; `edge_claim none` and validation sealed.
- **L-4 B8.6R11A activation checkpoint**: Inspector accepted v13 commit `4387081407b92f50df6003f9435b19b885135daf` after Hermetic CI `30523998233`. The canonical activation checkpoint is ready at E0, `edge_claim none`, validation sealed; it is not provisioning and authorizes no production execution until this checkpoint itself is reviewed and CI-confirmed.
- **L-4 B8.6R11B one-shot provisioning**: the exact authorized command at `4cc5f3da07d09ad100f1a04043214e87a1dfc943` exited 1 once, before runtime. Inspector diagnosis found activation literal `lily_l4_breadth_b86r11_provisioning_activation_v13` disagreed with bootstrap literal `lily_l4_b86r11_provisioning_activation_v13`; activation CI was `30526156121` (source v13 acceptance `4387081407b92f50df6003f9435b19b885135daf` / `30523998233`). Invocation count is 1; marker, dataset read/hash/scan, return decode, and validation counts are all 0. No marker, report, manifest, or payload exists. This is E0 `blocked_before_runtime_schema_contract_mismatch_no_retry`, not a data or breadth result; `edge_claim none`, validation sealed, and no retry or scientific progression is authorized.
- **L-4 B8.6R12 Phase A v14**: v13 remains immutable consumed no-retry incident history. v14 is E0 machinery only: the locked gate is the single authority for `activation_schema_version`; its committed bootstrap shares one pre-import `preflight`, and activation/report validation plus future activation generation bind that gate value. Temporary-Git adversarial tests cover a matching gate-derived activation, a one-character mismatch, dirty dependency rejection, and direct-runtime refusal. No activation, provisioning, container/data, return, or validation access occurred; `edge_claim none` and validation sealed.
- **L-4 B8.6R13 Phase A v15**: v14 is immutable Inspector-rejected history because its owner authorization was caller-controlled. v15 locks both the activation schema and exact required owner authorization in its gate. Its builder, canonical committed activation, actual pre-import bootstrap `preflight`, activation validator, and schema must agree; the closed-world future report/output contract retains exact data-hash, U8, cutoff, coverage/count, disk-identity, provenance, and seal protections. Temporary-Git adversarial tests reject schema/owner drift, dirty activation/dependencies, forged success, unknown fields, and direct runtime. It is E0 only: no activation, provisioning, container/data, return, or validation access occurred; `edge_claim none`, validation sealed, and Inspector review is required.
- **L-4 B8.6R13A activation checkpoint**: Inspector accepted v15 commit `42bfe3da3c58103317a71edb33bcd0d280b3017c` after Hermetic CI `30591744500`. The canonical no-LF gate-derived activation record was committed at `ddbd096cf960f1702f75687d285b0b899a2670de`; its validator called the actual preflight and passed with matching worktree/commit bytes and accepted-gate ancestry/blob. It remains E0 with `edge_claim none` and validation sealed. It is not provisioning: no committed bootstrap/run, marker, container/data, return, or validation access is authorized.
- **L-4 B8.6R13B one-shot structural provisioning**: the sole authorized git-show committed-bootstrap invocation at `d06001b54a80321b9b7be356ef808670b17dfba6` exited `0`. It produced the canonical attempt marker, report, falsification manifest, and U8 session-date payload after one bounded container read that matched the locked SHA-256. The report validator passed; U8/order and structural dates through 2015-12-31 are bound, return decoding and validation access are zero, and the validation seal remains intact. This is E0 structural provenance, not a breadth result; `edge_claim none`. The one-shot cannot be retried.
- **L-4 B8.7 Phase A capacity**: source-bound v4 science plus the B8.6R13B committed structural date artifacts derive 465 U8-common weekly paired slots from 2007-02-05 through 2015-12-31. Each of the four mandatory metrics separately clears planning `MinTRL_falsify` 49. This is E0 capacity only, not an E1 outcome: actual weekly paired MinTRL recalculation remains mandatory; validation sealed, edge_claim none, and every later activation/execution authorization false.
- **Locked-gate manifest rotation**: `experiments/locked_gates.jsonl` is sealed v1 at 64,976 bytes to remain within the legacy B8.5R2 65,536-byte bound. New rows begin in `experiments/locked_gates_v2.jsonl`; `experiments/locked_gate_segments.json` binds both segments and their migration provenance.
- **Operating roles**: Lily's persistent GPT-5.6 Terra high subagent is the primary implementation Worker for sequential bounded orders. The root agent is Inspector, owns inspection and `research_log` authorship/decision, and the Worker must hand off and wait for Inspector acceptance before a next order.
- **Databento**: `DATABENTO_API_02` passes metadata access with USD 0 spend, but relevant US-equity coverage begins in 2018 or later and no dedicated corporate-actions history was exposed; owner-reported USD 50 credit has unverified real-payment provenance

## 11. Next Safe Action

Keep validation returns sealed and do not rerun B4.11, B4.12, B7.3, B7.6, B7.14, the consumed B8.5R5 Phase B one-shot, consumed B8.6R11B/v13, or B8.6R13B. L-3 is E1 scope_restricted and unresolved; no L-3 result may be carried forward as proof that inverse-volatility sizing passed. L-4 remains unresolved E0 with `edge_claim none`: B8.7 capacity funds four planning plans only and does not authorize activation or execution. The next step requires Inspector review and a separately owner-approved scientific execution gate, not a retry of any consumed one-shot. No UAT work is planned: a hostname reference is not a public UAT entitlement.

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

- **L-4 B8.8R v2 remediation**: Inspector rejected immutable B8.8/v1 for timing, equality, end-to-end, report, and bootstrap deficiencies. v2 remains E0 synthetic-only with every access count zero; its order forbids amend/reset/rebase/force push after the prior B8.8 force-with-lease incident. Validation stays sealed and activation/execution remain forbidden.

- **L-4 B8.8R2 v3 remediation**: B8.8R/v2 is immutable Inspector-rejected incomplete history. v3 adds gate-owned activation/report schemas, future provenance/one-shot lifecycle primitives, and closed-world future E1 evidence derivation requirements, while performing no activation, execution, or real access.

- **L-4 B8.8 Phase A machinery**: E0 synthetic-only contract binds v4/B8.7/B8.6R13B/L1/L3 and implements the later matched U4/U8 computation/report path with actual per-metric paired-week MinTRL/HAC checks, deterministic robustness/regime/decision controls, and a closed-world lifecycle. All B8.8 access counts remain zero; activation and execution are forbidden pending Inspector review and a future separate canonical gate.
