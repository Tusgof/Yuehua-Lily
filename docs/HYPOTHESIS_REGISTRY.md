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

- **Status**: active, unexecuted E0 governance; edge claim none
- **Locked scope**: the fixed L1 `research_signed` eight ETFs only; candidate `q / max(annualized_volatility, 0.05)` versus comparator `q`, with identical inherited weekly rebalance, next-actual-NYSE-close execution, 90% gross/10% cash/25% asset-cap constraints, 60-session risk inputs, and scale-down-only target volatility.
- **Primary metric**: one weekly paired portfolio observation, `HHI_comparator - HHI_inverse_volatility`, using signed absolute component-risk shares after common constraints. The minimum useful mean reduction is `0.05`; there is no asset multiplier or pseudo-replication.
- **Realized confirmation**: retain each branch’s execution-close weights and use exactly `t+1` through `t+20` actual-session returns with the same HHI normalization. Missing rows or a nonzero-position undefined denominator make the pair non-evaluable; weights are retained and no row or asset is silently dropped.
- **Side effects**: turnover/cost relative increase must not exceed `0.20`; cap/cash/scale-down frequency increase must not exceed `10` percentage points. A zero denominator or other non-evaluable side effect is scope-restricted, never accepted or falsified silently.
- **Statistics**: `MinTRL_falsify = 49` for null `0.05` versus adverse `0.00`. Validation locks both `0.00` versus `0.05` and minimum-useful `0.05` versus expected `0.10` paired-mean plans; each is `49`, so binding `MinTRL_validate = 49`.
- **Regimes and capacity**: 26 weekly pairs is descriptive only. Each inferential regime must independently fund its own paired requirement; an inferential 2-of-3 statement cannot pool regimes. The locked-date optimistic regime-eligible ceiling is 366 weekly slots before actual-session, missingness, and non-evaluable-pair reductions.
- **Decision boundary**: a funded one-sided upper confidence bound below `0.05`, or a funded/evaluable primary result with a breached locked side-effect limit, may falsify the composite claim only with a mechanism autopsy. Validation needs a one-sided lower confidence bound above `0.05`, realized confirmation, every side-effect limit met, and independently funded claimed regimes.
- **Seal**: validation is sealed; B7.1 requires separate owner approval and a new activation/preflight gate before any data, return, signal, position, covariance, execution, or result observation. No market evidence is recorded by B7.
- **B7.2 hermetic source-provenance remediation**: active v2 supersedes only the v1 external-Wiki source-verification layer with byte-preserving repository snapshots for hermetic CI. The v1 research semantics remain unchanged; evidence remains E0 with edge claim none.

## L-4 — Breadth

- **Status**: proposed; depends on universe/data integrity
- **Statement**: Adding economically distinct countries, asset sleeves, and markets reduces dependency on any single-market trend after costs.
- **Rationale**: Large trends are rare and synchronized markets are not independent bets; breadth should expand opportunity only when trend-state dependence is genuinely different.
- **Predictions**:
  1. Top-market and top-sleeve PnL/risk shares fall as genuine breadth increases.
  2. Drawdown dependency and trend-state concentration decline.
  3. Benefits survive removal of the best market and the best trend episode.
- **Validation**: compare nested universes with survivorship-clean membership, matched dates, costs, trend-state correlation, concentration, and independent-bet measures; meet `MinTRL_validate`.
- **Falsification**: after `MinTRL_falsify`, broader universes fail to reduce locked dependency metrics or the apparent benefit disappears after costs/best-market removal across required regimes, followed by a mechanism autopsy.

## Seed Status

L-0 has E0 sizing and production Webull capability evidence and remains scope-restricted. B4.6 verifies read-only account endpoints plus `status=OC` and `fractionable=true` for all ten ETF candidates. B4.10 hash-locks the fail-closed UAT preview runner and fixtures. B4.11 stops after three authentication requests. B4.12 then funds one token create and seven checks over 30 seconds, but authentication still does not become NORMAL and no preview occurs; minimum order, funding FX, execution quality, and realized costs remain unknown. L-1 has E1 falsification-window, data-remediation, capacity, and independent corporate-action evidence: `MinTRL_falsify` is funded, but the full two-regime falsification rule is not met. The sealed validation calendar projects 20,376 joint independent-bet equivalents against the binding 8,673 under the locked actual-dependence rule, while the original planning sensitivity projects only 7,604. Treasury cash is resolved and fee uncertainty cannot reverse the negative primary result even under a full-credit bound. B4.4 acquires the locked Alpha Vantage matrix at zero cost, but only 11/16 pre-2016 symbol-endpoint pairs reconcile exactly and the provider has no point-in-time revision archive. B4.5 accepts that limitation at E1 and pauses further source search. B4.7 locks a forward three-stream design and B4.8 blocks it before observation. B4.9 closes the unavailable Webull ledger path. B4.10 through B4.12 add no L-1 evidence. The validation window is sealed. L-2 through L-4 remain proposed and may not be promoted by prose edits alone.

## Source Adaptation

The registry format, evidence tiers, dual MinTRL, and kill/resurrection rules adapt `Yuehua-Higanbana/docs/FABLE5_UPGRADE_PROPOSAL.md`. Lily changes the observation model from dense 0DTE trades to persistent, overlapping trend positions and adds independent-bet, survivorship, country breadth, and futures-roll requirements.
