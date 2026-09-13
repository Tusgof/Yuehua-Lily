# PROJECT_BRAIN.md

## Project definition and thesis

Lily is a systematic trend-following research program. The research program is the product; dashboards, backtests, paper accounts, and broker integrations are supporting artifacts. The thesis is that persistent price movement and asymmetric payoff can support a diversified, risk-managed strategy only if costs, turnover, dependence, capacity, and implementation limits are tested honestly. These are hypotheses, not validated findings.

## Evidence tiers

| Tier | Meaning | Claim boundary |
|---|---|---|
| E0 | Infrastructure, fixtures, synthetic evidence, or operational dry run | Machinery works; no edge claim |
| E1 | Real-data diagnostic that is under-sampled, underpowered, or blocked | Hypothesis-generating only; never edge |
| E2 | Preregistered validation passes statistics, regimes, robustness, costs, and adversarial review | Edge only in tested scope |
| E3 | E2 plus operational validation, account feasibility, and launch checklist | Separate owner decision required for real money |

Below-E2 acceptance, edge, or deployment language is prohibited. `edge_claim: none` is required for E0/E1 and paper-like dry runs.

## Current capital, broker, and universe facts

- Lily capital is separate from Higanbana: USD 1,000–2,000.
- The current-capital implementation study is 8–12 US-listed fractional ETFs with globally diversified country and asset-class exposure; full-size futures are outside current-capital scope.
- Webull Thailand is the preferred ETF operational candidate. IBKR is the reference broker for micro-futures feasibility. Broker permissions, minimum order, funding FX, execution quality, and realized costs remain bounded facts, not assumptions.
- The locked CORE-1 U8 order is `VTI, VGK, EWJ, VWO, IEF, TIP, GLD, DBC`. The ETF branch is long/cash and is not equivalent to a symmetric long/short futures CTA.

## Data, cost, and validation invariants

- Daily total-return bars, timestamps, instrument identity, corporate actions, inception/delisting, survivorship/backfill, missing sessions, currencies/FX, futures rolls, raw/normalized/derived boundaries, provenance, and re-downloadability must be explicit.
- Hard-to-reproduce inputs use container and canonical/content hashes. Free re-downloadable inputs use documented container hashes until a hard-to-reproduce artifact exists.
- Paid-data guard: USD 0 through L-0 and cumulative USD 50 through L-1. No shared credentials, keys, ledgers, or budgets; never store credential values or absolute machine paths.
- Costs precede trust. Reports separate gross and implementable net return, turnover, execution costs, running expenses, drawdown, concentration, and dependence-adjusted observations.
- Candidate timing, fixed sleeves, 2-percentage-point band, locked costs/stress, matched benchmark, A-H gates, ranking, selection, and stop rules remain hash-bound in the CORE-1 artifacts.
- The 2016-01-04 through 2026-06-30 validation window is sealed. Do not resolve, read, hash, scan, count, decode, or infer validation data; no validation access is implied by E0 machinery.

## Current scientific status

- L-0: scope-restricted.
- L-1: scope-restricted E1.
- L-2: E1 `underfunded_scope_restricted`, paused.
- L-3: E1 `scope_restricted`/unresolved, paused.
- L-4: unresolved E0, `edge_claim: none`, paused.
- CORE-1: active E0 machinery, no empirical result, no edge claim.
- The R3 decision kernel commit `eec2ebf2c17957ff87d7b39cfec741b81084e9cd` passed Exact-SHA CI `34766759693`.

## GOV-2 outcome-first operating model

One active scientific lane and one bounded order are the default. Work orders must unlock a named scientific decision; if there is no direct link within two steps, backlog the work. The Worker is autonomous until the named checkpoint and stops for ambiguity, changed risk, failed gate, unrelated dirty state, or external/material authority. The Inspector owns review, integration recommendation, and Thai research-log authorship.

### Fixed CORE-1 question

On the locked U8 daily total-return universe through 2015-12-31, does any of `CORE1_DC60`, `CORE1_DC120`, or `CORE1_SMA200` pass all locked A-H gates after locked costs?

### Shortest safe queue

Finish decision/lifecycle binding → one CP-A → one development-only run → one CP-B → Inspector-written Thai research log → select exactly one candidate or stop. No parameter rescue and no fourth candidate. L-2/L-3/L-4 remain paused until this decision.

### Next safe action

Owner integration of GOV-2, then the smallest missing binding needed for one CP-A-reviewed development-only run.

## Immutable prohibitions and source pointers

No data/return/container or validation access, activation, scientific execution outside its named gate, provider/network call, credential read, broker/account action, paid spend, paper trade, real-money action, or research-log edit is authorized by this document. Do not alter locked gates, manifests, registries, reports, hypothesis statuses, or historical files.

History and exact state live in `Backup_/2026-09-13/`, `docs/DECISION_RECORD_*.md`, `experiments/bootstrap_tracker.json`, `experiments/hypothesis_registry.json`, locked-gate manifests, reports, and Git. Governance policy is in Decision Record 008; CORE-1 science is in Decision Record 007 and its preregistration. The local LLM Wiki is methodology context, not investment evidence.
