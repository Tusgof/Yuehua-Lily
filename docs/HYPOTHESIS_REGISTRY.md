# Lily Hypothesis Registry v1

- **Machine source**: `experiments/hypothesis_registry.json`
- **Founding date**: 2026-07-15
- **Promoted founding source**: `docs/DECISION_RECORD_001_PROJECT_REFOUNDING.md`
- **Prior design source**: `Backup_/2026-07-15/IMPLEMENT_PLAN.md`

## Registry Rules

- Hypotheses own experiments.
- `MinTRL_falsify` is designed and funded before `MinTRL_validate`.
- Trend observations use autocorrelation-adjusted Sharpe variance and independent-bet-equivalent counts; raw trade counts are never assumed independent.
- Search over parameters, signals, universes, filters, or regimes requires a complete search log and DSR or an explicit blocker.
- Falsification requires the registered numeric/statistical criterion plus a mechanism autopsy.
- Resurrection requires a new ID and a new prediction.
- Three consecutive adequately powered edge/mechanism kills trigger a Lily family review. L-0 and engineering failures do not count.

## L-0 — Capital And Broker Sizing Feasibility

- **Status**: scope-restricted E0; B4.12 funded a fixed 30-second authentication window but the one authorized shared-UAT run still stopped before preview after one token create and seven checks; minimum order, funding FX, execution quality, and realized costs remain unverified
- **Statement**: At least one globally diversified US-listed fractional-ETF trend implementation can be sized honestly at USD 1,000 and USD 2,000 after broker constraints and costs, while the study can identify minimum viable capital for 4-, 8-, and 12-market micro-futures variants.
- **Rationale**: A statistical edge is operationally irrelevant if contract/share granularity, margin, cash buffers, or costs prevent risk-targeted breadth.
- **Predictions**:
  1. Fractional ETFs permit materially finer risk allocation than futures at current capital.
  2. Current capital can support 8–12 global economic sleeves only if fractional execution is available.
  3. Micro-futures feasibility requires more capital as breadth and cash buffers increase.
- **Validation**: preregister target risk, concentration, cash buffer, broker capability, cost, and feasibility thresholds; classify both USD 1,000 and USD 2,000 without using return backtests.
- **Falsification**: the current-capital claim is killed if no broker-realistic ETF configuration meets the locked breadth, cash-buffer, concentration, minimum-trade, and annualized-cost limits at either capital level. A broker/API failure alone is a scope constraint unless every allowed implementation path fails.
- **Required data**: ETF prices/volatility, broker terms, fees, fractional rules, currencies, futures contract multipliers/margins, and capability probes.
- **MinTRL**: not applicable to the deterministic feasibility classification; uncertainty and stress ranges must be reported instead.

## L-1 — Baseline Continuation

- **Status**: scope-restricted E1; B4.9 closes the unavailable broker-ledger path, while the B4.11 and B4.12 authentication stops add no L-1 evidence; validation remains sealed and edge/historical-correctness claims remain unauthorized
- **Statement**: A 60-day directional-count baseline has positive convex payoff after implementable costs on the selected global research universe.
- **Rationale**: Slow information diffusion and herding can sustain price continuation; trend systems accept frequent small losses to retain infrequent large winners.
- **Predictions**:
  1. Net performance is driven by right-tail trend episodes rather than hit rate.
  2. Whipsaw/mean-reverting regimes produce the known loss zone.
  3. The sign is not dependent on one market or one crisis episode.
- **Validation**: positive implementable net return and preregistered convexity/right-tail criteria; PSR against zero and matched benchmark; DSR if searched; regime and big-trend survival; actual effective observations at or above `MinTRL_validate`.
- **Falsification**: after `MinTRL_falsify`, net return is non-positive and the preregistered right-tail/convexity condition fails across at least two independent trend-regime buckets, followed by a mechanism autopsy.
- **Known kill zone**: whipsaw and mean-reverting regimes. Scope restriction is allowed if locked before E2 claims.

## L-2 — Multi-Lookback Candidate Versus Baseline

- **Status**: active after B5 preregistration; depends on L-1 and remains unexecuted
- **Statement**: A 32/64/126/252 multi-lookback t-stat signal improves paired net active-return Sharpe versus the matched-horizon directional-count comparator; the 60-day L-1 baseline is secondary reference only.
- **Rationale**: Combining horizons may reduce dependence on one arbitrary lookback while preserving trend exposure.
- **Predictions**:
  1. Any improvement survives matched universe, timing, sizing, and cost assumptions.
  2. Improvement is not explained solely by greater leverage or a different effective horizon.
  3. At least one preregistered turnover/cost or risk-adjusted component improves outside the search sample.
- **Validation**: lock paired daily net active-return Sharpe against the matched comparator before execution; log all trials; require primary-margin PSR and DSR on that same series; meet `MinTRL_validate` using effective observations.
- **Falsification**: after `MinTRL_falsify`, annualized paired active-return Sharpe is below `0.10` and primary-margin PSR is at most `0.05`, followed by a mechanism autopsy.
- **Locked B5.2 design**: v3 supersedes but does not alter v1/v2; at decision close `t`, candidate and matched comparator both use exactly `r[t-k]`, `k=0..h-1`; both execute at the next actual session close `t+1`; paired active returns use the same post-execution interval; 60-day L-1 is secondary only; validation remains sealed.
- **B6 machinery**: a hash-locked, fail-closed runner validates v2/v3 independently and applies only the v3 time-index override. It cannot read data or execute until a separately approved B6.1 activation gate exists.
- **B6.2 remediation**: a superseding report contract rejects unsupported results. Only real-data falsification reports may carry a falsified/not-falsified decision, and they must bind the active contract, v2/v3 sources, checkout commit, complete decision metrics, trial inventory, timing attestation, and—if falsified—the mechanism autopsy.
- **B6.3 capacity outcome**: before any data access, the fixed window and eight-asset universe cannot fund the locked 54,048 falsification MinTRL even at their impossible 26,016 joint-bet ceiling. L-2 is underfunded/scope-restricted, not falsified.

## L-3 — Inverse-Volatility Sizing

- **Status**: E1 scope-restricted after the one authorized falsification-window run; edge claim none
- **Locked scope**: the fixed L1 `research_signed` eight ETFs only; candidate `q / max(annualized_volatility, 0.05)` versus comparator `q`, with identical inherited weekly rebalance, next-actual-NYSE-close execution, 90% gross/10% cash/25% asset-cap constraints, 60-session risk inputs, and scale-down-only target volatility.
- **Primary metric**: one weekly paired portfolio observation, `HHI_comparator - HHI_inverse_volatility`, using signed absolute component-risk shares after common constraints. The minimum useful mean reduction is `0.05`; there is no asset multiplier or pseudo-replication.
- **Realized confirmation**: retain each branch’s execution-close weights and use exactly `t+1` through `t+20` actual-session returns with the same HHI normalization. Missing rows or a nonzero-position undefined denominator make the pair non-evaluable; weights are retained and no row or asset is silently dropped.
- **Side effects**: turnover/cost relative increase must not exceed `0.20`; cap/cash/scale-down frequency increase must not exceed `10` percentage points. A zero denominator or other non-evaluable side effect is scope-restricted, never accepted or falsified silently.
- **Statistics**: `MinTRL_falsify = 49` for null `0.05` versus adverse `0.00`. Validation locks both `0.00` versus `0.05` and minimum-useful `0.05` versus expected `0.10` paired-mean plans; each is `49`, so binding `MinTRL_validate = 49`.
- **Regimes and capacity**: 26 weekly pairs is descriptive only. Each inferential regime must independently fund its own paired requirement; an inferential 2-of-3 statement cannot pool regimes. The locked-date optimistic regime-eligible ceiling is 366 weekly slots before actual-session, missingness, and non-evaluable-pair reductions.
- **Decision boundary**: a funded one-sided upper confidence bound below `0.05`, or a funded/evaluable primary result with a breached locked side-effect limit, may falsify the composite claim only with a mechanism autopsy. Validation needs a one-sided lower confidence bound above `0.05`, realized confirmation, every side-effect limit met, and independently funded claimed regimes.
- **B7.1 locked E0 gate-only preflight**: all six authorization flags false (data, container inspection, return parsing, execution, report decision, validation access); validation remains sealed and no market evidence was read. Inspector review and successful exact-SHA CI must precede a separate owner-authorized one-run execution order; this gate does not authorize data or execution.
- **B7.2 hermetic source-provenance remediation**: active v2 supersedes only the v1 external-Wiki source-verification layer with byte-preserving repository snapshots for hermetic CI. The v1 research semantics remain unchanged; evidence remains E0 with edge claim none.
- **B7.3 result**: the one permitted run passed the falsification-only container preflight but recorded 500 weekly observations, exceeding the locked 465 ceiling. Its provisional result is invalid; no rerun is authorized. Validation remains sealed.
- **B7.4 ledger remediation**: the original ledger decision `falsified` is explicitly provisional and invalid. One append-only invalidation event binds the original ledger row and final report; the only authoritative outcome is `scope_restricted`, with validation sealed and no additional run authorized.
- **B7.5 corrected rerun schedule gate**: E0 no-data governance only. It preserves the locked scientific semantics while requiring future weekly decisions from 2007-02-05 through 2015-12-31, complete `t+1` through `t+20` confirmation by the end boundary, no more than 465 weekly pairs, and a hash-bound date-only schedule attestation before returns. All B7.5 authorizations remain false. B7.3 remains invalidated E1 `scope_restricted`; validation is sealed, edge claim none, and a future one-run needs Inspector acceptance plus new explicit owner authorization. The owner authorization wording is retained as a required B7.5 control mirror.
- **B7.6 corrected rerun attempt**: the one owner-authorized attempt hard-stopped at `date_only_schema_metadata_missing` before return parsing. It created neither a schedule attestation nor a fresh ledger row; its only authoritative outcome is E1 `scope_restricted`, with edge claim none and validation sealed. B7.3/B7.4 history remains invalidated and unchanged.
- **B7.7 remediation**: E0 synthetic-only v2 execution machinery supersedes B7.6's defective parser/contract only. It preserves locked research semantics and uses structural per-symbol session intersection, explicit side-effect diagnostics, and a closed-world future report validator. No data access, rerun, or validation access is authorized; a future rerun needs Inspector acceptance and new owner authorization.
- **B7.8 remediation**: E0 synthetic-only supersession of defective B7.7 machinery. Hermetic contracts bind B7.7/v2 and locked science, enforce exact scanner/schedule/side-effect/report invariants, and keep all access flags false. L-3 remains E1 `scope_restricted`, validation sealed, edge_claim none; no rerun is authorized.
- **B7.9 remediation**: E0 synthetic-only adversarial supersession of B7.8/v4 machinery. Hermetic v5 rejects every individual post-end session before intersection while accepting the inclusive end, recomputes finite primary/realized/side-effect/funding/regime evidence, and binds only committed synthetic identity files by actual SHA-256. All fourteen flags remain false; L-3 remains E1 `scope_restricted`, validation sealed, edge_claim none; no rerun is authorized.
- **B7.10 remediation**: E0 synthetic-only decision-integrity supersession of B7.9/v5. Hermetic v6 recomputes locked UCB/MinTRL dependence arithmetic, enforces HHI/event/regime conservation and mutually exclusive decisions, and permits only synthetic-fixture provenance. All fourteen flags remain false; L-3 remains E1 `scope_restricted`, validation sealed, edge_claim none; no rerun is authorized.
- **B7.10 Inspector rejection / B7.11 remediation**: Inspector rejected v6 because it trusted reporter-authored summaries, accepted MinTRL/effective-bet mismatches, and allowed synthetic E1 decisions. B7.11 preserves locked v6 artifacts and replaces only this machinery with an E0 synthetic-only hash-bound closed-world observation vector. v7 derives all paired statistics, raw-observation MinTRL, regime funding, HHI, and side-effect results directly; the only report mode is `synthetic_evaluation` with `not_run`, E0, and edge_claim none. All fourteen flags remain false; L-3 stays E1 `scope_restricted`, validation sealed, and no rerun is authorized.
- **B7.12 remediation**: v8 preserves immutable v7 and corrects only its inclusive float-boundary, committed-runner-fixture, and golden-assertion defects. The active E0 fixture is hash-bound in the v8 gate, the runner permits only that fixture, and decimal side-effect comparisons implement the locked inclusive 20% and 10-percentage-point limits. All fourteen flags remain false; L-3 stays E1 `scope_restricted`, validation sealed, and edge_claim none.
- **B7.13 contract**: v3 restores the original v2 manifest row and directly supersedes its sole missing `human_approval` field with a hash-bound E0 gate. It preserves the future B7.14 date-only structural preflight: an approved falsification-only container must bind its identity/hash/schema and reject each post-end symbol session before intersection; failure precedes return parsing, execution, ledger, or decision. L-3 remains E1 `scope_restricted`, validation sealed, edge_claim none; B7.14 is unauthorized.
- **B7.14 v3 rejected / B7.14R v4 rejected / B7.14R3 v5 blocked / B7.14R4 v6**: v3 decoded a skipped timestamp; v4 lacked binding/closed-world controls; v5's inert runner failed `audit_new_script_lib_usage` for no shared `lib` import. v6 supersedes v5 at E0 only, preserves all prior bytes, adds the required shared-lib runner guard, and opens no container access.
- **B7.14R7/v9 rejected; B7.14R8/v10 complete E0**: v9 failed Phase A. v10 is snapshot-only governance at `d2a9001` (CI 30351502467), closed at `cf0fa3d` (CI 30351716462), and opens no data, container, execution, decision, ledger, or validation path. All fourteen authorizations remain false; L-3 is E1 `scope_restricted`, validation sealed, edge_claim none, and no rerun is authorized.
- **B7.15 current-preregistration closure**: L-3 remains E1 `scope_restricted` and unresolved, not falsified or validated; no rerun is planned under the current preregistration; validation is sealed; edge_claim none; no L-3 result may be carried forward as proof that inverse-volatility sizing passed. The next gate is L-4 preregistration/planning only.

## L-4 — Breadth

- **Status**: active planning E0; `edge_claim none`; no data, execution, or validation access
- **Statement**: Adding economically distinct countries, asset sleeves, and markets reduces dependency on any single-market trend after costs.
- **Rationale**: Large trends are rare and synchronized markets are not independent bets; breadth should expand opportunity only when trend-state dependence is genuinely different.
- **Predictions**:
  1. Top-market and top-sleeve PnL/risk shares fall as genuine breadth increases.
  2. Drawdown dependency and trend-state concentration decline.
  3. Benefits survive removal of the best market and the best trend episode.
- **Validation**: compare nested universes with survivorship-clean membership, matched dates, costs, trend-state correlation, concentration, and independent-bet measures; meet `MinTRL_validate`.
- **Falsification**: after `MinTRL_falsify`, broader universes fail to reduce locked dependency metrics or the apparent benefit disappears after costs/best-market removal across required regimes, followed by a mechanism autopsy.
- **B8 preregistration**: locks U1 descriptive-only, U4 (VTI/IEF/GLD/DBC) versus ordered U8 equal-notional `q[i,t]` on identical U8-common dates, a 0.05 HHI reduction, 0.5 effective-opportunity increase, 0.10 top-dependency reduction, and at least half HHI benefit after best-market and best-episode removal. It is E0/no-data only; L-4 has no empirical result or edge claim, validation remains sealed, and a separate owner-approved activation gate is required.
- **B8.1 v2 remediation**: supersedes B8/v1 without changing its bytes. It replaces the pseudo-independence count with trailing-52-week continuous-`q` correlation/eigenvalue `N_eff`, locks component-risk HHI, deterministic removals and side effects, separately funded per-metric MinTRL and regime matrix, and a mutually exclusive decision matrix. It is E0/no-data only; `edge_claim none`, validation sealed, and no activation is authorized.
- **B8.2 v3 completion**: supersedes B8.1 without changing prior bytes. It restores the scoped question, data/search/claim controls, explicitly fixes primary `u=q` before downstream constraints, locks all three MinTRL plans per metric, and gives E1 and future-validation scope predicates fixed precedence. It is E0/no-data only; `edge_claim none`, validation sealed, and Inspector review is the only next action.
- **B8.3 v4 exact-preservation remediation**: supersedes B8.2 without changing v1/v2/v3. It restores the exact 465 weekly-paired capacity, fixed macro sleeves, best-market and neutral-bridge/end/tie/removal best-trend-episode rules, complete regime states/dates, `N_eff` and component-risk missingness, side-effect limits, and four-outcome future-validation precedence. It is E0/no-data only; `edge_claim none`, validation sealed, all authorizations false, and Inspector review is the only next action.
- **B8.4 synthetic future-preflight machinery**: Inspector accepted B8.3. B8.4 source-binds v4 without superseding its scientific preregistration, accepts only committed synthetic fixtures, and hard-stops date/schema/path/hash/membership ambiguity or any post-2015-12-31 session before return parsing. It is E0 only; `edge_claim none`, validation sealed, and B8.5 owner approval is required before any real-container access.
- **B8.5 Phase A activation/order lock**: source-binds accepted B8.4R2/v3, v4 science, and the B8.4R2 report/runner/schema/fixture. It records a future single structural U8 symbol/session-date preflight only: missing/ambiguous U8, schema/path/hash mismatch, or any session after 2015-12-31 must stop before return or value decoding. It is E0; all 24 Phase A authorizations are false, validation sealed, `edge_claim none`. Phase B is not executed and awaits Inspector acceptance plus exact-SHA CI success.
- **B8.5R Phase A remediation**: v1 remains immutable Inspector-rejected history because it did not lock runnable machinery or deterministic storage resolution. v2 hash-binds the byte-level scanner, one-shot future runner, report schema/validator, and synthetic structural envelope. Future Phase B resolves only `LILY_DATA_ROOT` plus literal references, records observed raw manifest/payload hashes and structural counts, and hard-stops before return/value decoding. It remains E0; validation sealed, `edge_claim none`, and Phase B is not executed pending Inspector acceptance.
- **B8.5R2 Phase A remediation v3**: v1/v2 remain immutable Inspector-rejected history. v3 hash-binds bounded reads, multiple strictly ordered calendar-valid session dates for every exact U8 member, atomic durable one-shot consumption before environment access, fixed repo-relative report/attempt-marker paths, and real-report validation. It remains E0; validation sealed, `edge_claim none`, and Phase B is not executed pending Inspector acceptance.

## Seed Status

L-0 has E0 sizing and production Webull capability evidence and remains scope-restricted. B4.6 verifies read-only account endpoints plus `status=OC` and `fractionable=true` for all ten ETF candidates. B4.10 hash-locks the fail-closed UAT preview runner and fixtures. B4.11 stops after three authentication requests. B4.12 then funds one token create and seven checks over 30 seconds, but authentication still does not become NORMAL and no preview occurs; minimum order, funding FX, execution quality, and realized costs remain unknown. L-1 has E1 falsification-window, data-remediation, capacity, and independent corporate-action evidence: `MinTRL_falsify` is funded, but the full two-regime falsification rule is not met. The sealed validation calendar projects 20,376 joint independent-bet equivalents against the binding 8,673 under the locked actual-dependence rule, while the original planning sensitivity projects only 7,604. Treasury cash is resolved and fee uncertainty cannot reverse the negative primary result even under a full-credit bound. B4.4 acquires the locked Alpha Vantage matrix at zero cost, but only 11/16 pre-2016 symbol-endpoint pairs reconcile exactly and the provider has no point-in-time revision archive. B4.5 accepts that limitation at E1 and pauses further source search. B4.7 locks a forward three-stream design and B4.8 blocks it before observation. B4.9 closes the unavailable Webull ledger path. B4.10 through B4.12 add no L-1 evidence. The validation window is sealed. L-2 through L-4 remain proposed and may not be promoted by prose edits alone.

## Source Adaptation

The registry format, evidence tiers, dual MinTRL, and kill/resurrection rules adapt `Yuehua-Higanbana/docs/FABLE5_UPGRADE_PROPOSAL.md`. Lily changes the observation model from dense 0DTE trades to persistent, overlapping trend positions and adds independent-bet, survivorship, country breadth, and futures-roll requirements.

B8.4R2: L-4 remains edge_claim none; v3 synthetic E0 preflight active, validation sealed. B8.5/v1 and B8.5R/v2 are immutable rejected history; B8.5R2/v3 is the bounded structural E0 contract. Phase B is not executed and awaits Inspector acceptance.
