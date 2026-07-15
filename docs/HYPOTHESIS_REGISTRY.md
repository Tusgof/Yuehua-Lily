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

- **Status**: scope-restricted E0 after B4.6; economic ETF sizing passes at 8–10 sleeves, Webull Thailand production read-only access works, and all ten current candidates return `status=OC` with `fractionable=true`; minimum order, funding FX, execution quality, and realized costs remain unverified
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

- **Status**: scope-restricted E1 after B4.5; the owner accepts the unresolved corporate-action history as an E1 limitation and pauses further source search; validation stays sealed, and any prospective comparison must be a separately locked E0 operational dry run with no edge or historical-correctness claim
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

- **Status**: proposed; depends on L-1
- **Statement**: A matched-horizon multi-lookback t-stat signal improves preregistered risk-adjusted utility or turnover/cost efficiency versus the 60-day baseline.
- **Rationale**: Combining horizons may reduce dependence on one arbitrary lookback while preserving trend exposure.
- **Predictions**:
  1. Any improvement survives matched universe, timing, sizing, and cost assumptions.
  2. Improvement is not explained solely by greater leverage or a different effective horizon.
  3. At least one preregistered turnover/cost or risk-adjusted component improves outside the search sample.
- **Validation**: lock one utility rule before execution; compare on paired dates and identical portfolio plumbing; log all trials; require DSR or untouched revalidation; meet `MinTRL_validate` using effective observations.
- **Falsification**: after `MinTRL_falsify`, the candidate fails the locked paired utility margin and has no compensating turnover/cost advantage across required regimes, followed by a mechanism autopsy.

## L-3 — Inverse-Volatility Sizing

- **Status**: proposed; depends on baseline plumbing
- **Statement**: Inverse-volatility sizing reduces portfolio risk concentration relative to equal notional without unacceptable turnover, leverage, or cost.
- **Rationale**: Equal notional lets volatile markets dominate risk; scaling by volatility should distribute risk more evenly.
- **Predictions**:
  1. Maximum asset and sleeve risk contributions fall.
  2. Concentration reduction survives volatility regimes and estimator perturbations.
  3. The benefit is not erased by resizing turnover or leverage.
- **Validation**: preregister ex-ante and realized concentration metrics, estimator windows, leverage/cash limits, turnover, and required regimes; meet the paired effective-sample gate.
- **Falsification**: after `MinTRL_falsify`, inverse-vol sizing does not reduce the locked concentration metrics in most required regimes or its benefit is fully offset by locked cost/leverage limits, followed by a mechanism autopsy.

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

L-0 has E0 sizing and production Webull capability evidence and remains scope-restricted. B4.6 verifies read-only account endpoints plus `status=OC` and `fractionable=true` for all ten ETF candidates, but minimum order, funding FX, execution quality, and realized costs remain unknown. L-1 has E1 falsification-window, data-remediation, capacity, and independent corporate-action evidence: `MinTRL_falsify` is funded, but the full two-regime falsification rule is not met. The sealed validation calendar projects 20,376 joint independent-bet equivalents against the binding 8,673 under the locked actual-dependence rule, while the original planning sensitivity projects only 7,604. Treasury cash is resolved and fee uncertainty cannot reverse the negative primary result even under a full-credit bound. B4.4 acquires the locked Alpha Vantage matrix at zero cost, but only 11/16 pre-2016 symbol-endpoint pairs reconcile exactly and the provider has no point-in-time revision archive. B4.5 accepts that limitation at E1 and pauses further source search; it does not authorize validation or paper trading. The validation window is sealed. L-2 through L-4 remain proposed and may not be promoted by prose edits alone.

## Source Adaptation

The registry format, evidence tiers, dual MinTRL, and kill/resurrection rules adapt `Yuehua-Higanbana/docs/FABLE5_UPGRADE_PROPOSAL.md`. Lily changes the observation model from dense 0DTE trades to persistent, overlapping trend positions and adds independent-bet, survivorship, country breadth, and futures-roll requirements.
