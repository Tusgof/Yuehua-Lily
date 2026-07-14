# Decision Record 001 — Lily Project Refounding

- **Date**: 2026-07-15
- **Status**: accepted by the owner through the founding grill session
- **Lily source state**: `Yuehua-Lily` commit `7b25f85`
- **Higanbana reference state**: local `Yuehua-Higanbana` commit `1a12249`
- **Nature of change**: refounding; not a greenfield bootstrap and not a cleanup

## 1. Owner Decisions

| # | Decision | Locked outcome |
|---:|:--|:--|
| 1 | Capital | Lily capital is separate from Higanbana and is currently USD 1,000–2,000. |
| 2 | Broker roles | Webull Thailand is the preferred candidate for the current-capital ETF branch. IBKR is the reference broker for micro-futures feasibility. No single broker is assumed to cover both roles. |
| 3 | Research versus implementation | Research is primary. Report both systems feasible with current capital and the minimum capital required for fuller implementations. |
| 4 | Current-capital universe | Use globally diversified exposure through US-listed ETFs so fractional sizing remains possible. Do not concentrate economic exposure in the United States. |
| 5 | Horizon | Medium-term trend following using daily bars, with positions held for weeks to months and weekly rebalancing as the initial design input. |
| 6 | Breadth | Current-capital ETF study targets 8–12 instruments/sleeves. Futures feasibility reports thresholds for 4, 8, and 12 markets. The research universe may be broader than the implementable account. |
| 7 | Data guard | USD 0 paid data through L-0; cumulative USD 50 through L-1. Every paid action requires preregistration, a true-provenance per-key ledger, and one real funded account only. |
| 8 | Relationship to Higanbana | Separate repo, budget, registry, state, credentials, and cost guard. Copy the `lib/` pattern; consider a shared package only after both projects are stable. |
| 9 | Family stop | Three consecutive adequately powered falsifications of distinct edge/mechanism hypotheses trigger a family review. L-0 feasibility and engineering failures are excluded. |
| 10 | Resurrection | A killed hypothesis may return only under a new ID with at least one new testable prediction. |

## 2. Broker Findings Used In The Decision

Facts observed on 2026-07-15:

- Webull Thailand's regional OpenAPI page advertises US stocks and ETFs and says additional services are still in development: <https://www.webull.co.th/open-api>.
- Webull Thailand allows fractional shares through its mobile app, during regular hours, as market orders: <https://www.webull.co.th/help/faq/355-ฉันสามารถซื้อขายแบบเศษหุ้นได้หรือไม่>.
- Webull Thailand lists US-stock/ETF commission at 0.10% of trade value with no minimum, excluding 7% VAT: <https://www.webull.co.th/pricing>.
- Global Webull API documentation is broader and lists fractional shares, short selling, options, and futures: <https://developer.webull.com/apis/docs/trade-api/overview>. This is not evidence that every feature is enabled for a Thai account.
- IBKR lists a USD 0 individual account minimum and provides Web API/TWS API plus futures access subject to account permissions: <https://www.interactivebrokers.com/en/accounts/required-minimums.php> and <https://www.interactivebrokers.com/campus/ibkr-api-page/>.

Decision implication: broker capability is a registered feasibility input, not an assumed implementation fact. A later sandbox/account probe must resolve Webull Thailand fractional-API support and actual IBKR permissions without storing credentials.

## 3. Salvage Map

### Keep And Promote

- Preserve `Note/Hypothesis.md` verbatim as the owner-authored historical source.
- Translate its rationale and four predictions into L-1 through L-4 in the registry.
- Carry forward these pre-refounding decisions from the archived `IMPLEMENT_PLAN.md`: multi-lookback t-stat candidate; 60-day directional-count baseline; `signal × risk weight / volatility` sizing direction; portfolio-level target volatility and caps; costs before trust; explicit unknown markers.
- Keep `Note/` as the owner's thinking space. It is not project state.

### Demote

- Keep `Dashboard/` as an optional visualization artifact.
- Browser `localStorage` is not authoritative project memory. The dashboard may render versioned exports but may not own decisions, gates, progress, or evidence.

### Replace After Archive

- Replace `PROJECT_BRAIN.md`, `IMPLEMENT_PLAN.md`, and `AGENTS.md` with the refounded research-governance versions.
- Dated archival copies live under `Backup_/2026-07-15/`.

### Hygiene

- Reconcile all active documentation to `Dashboard/index.html`, not the nonexistent `Main/index.html`.
- Delete the empty tracked `Main/Hypothesis` file.

## 4. Research Interpretation

“Global ETF exposure” means US-listed instruments may be used for fractional execution while the underlying economic exposures span the United States, developed markets outside the United States, emerging markets, Japan, Europe, government bonds, gold, broad commodities, real estate, and cash/short-duration bonds.

This does not lock tickers. Selection must later pass liquidity, history, inception-date, backfill, survivorship, benchmark, and implementability checks.

The ETF branch is long/cash unless a separately preregistered short implementation is proven feasible. It must not be described as equivalent to a symmetric long/short CTA futures program.

## 5. Family Stop Clarification

The family counter advances only when:

1. the entry tests the trend-continuation economic mechanism or a successor mechanism;
2. its preregistered falsification sample is met using autocorrelation-aware effective observations;
3. implementable costs and required regimes are covered; and
4. a mechanism autopsy is written.

Feasibility, data-pipeline, broker-permission, and engineering failures do not count. A family review may stop, narrow, or redesign Lily; it is not automatic deletion of the repository or its evidence.

## 6. Higanbana Policies Adapted For Lily

| Policy | Higanbana source | Lily change and reason |
|:--|:--|:--|
| Evidence tiers E0–E3 | `docs/FABLE5_UPGRADE_PROPOSAL.md` §§2, 8 | Kept. Trend paper trading remains E2-only except labeled E0 wiring dry runs. |
| Dual MinTRL | same, §4 | Kept, but observation counts use autocorrelation-adjusted Sharpe variance and independent-bet equivalents because trend positions overlap. |
| Registry and kill/resurrection | same, §3 | Kept. Seed IDs are L-0 through L-4 and the family stop is three adequately powered mechanism kills. |
| Data decision tree | same, §5 | Kept. Lily adds survivorship, delisted contracts/assets, continuous-futures roll provenance, and free-data container hashes. |
| Self-verifying repository | `docs/HIGANBANA_TECHNICAL_DUE_DILIGENCE.md` §§1, 6 | Required before research code because Lily must not become single-machine state. |
| Shared `lib/` and commit reproduction | same, §2 | Required before the first experiment script; no legacy migration is needed because Lily has no code. |
| Golden-number statistics | same, §3 | Required before any real backtest; trend-specific autocorrelation cases are added. |
| Locked gates and adversarial review | same, §4 | Required from the first preregistration and before E2. |
| Machine-checkable completion | `experiments/dd_remediation_tracker.json` | Bootstrap orders use required artifacts and validators; prose-only “done” is forbidden. |

0DTE-specific signals, SPY regimes, Higanbana data providers, budget room, credentials, and unremediated legacy patterns are not inherited.

## 7. Open Verification Items

These are not owner-decision gaps and do not block the founding pack:

- Webull Thailand API approval and fractional-order capability for the Thai account.
- Actual IBKR account type and futures/market-data permissions.
- Exact ETF tickers and country/sleeve weights.
- Target volatility, leverage, concentration caps, and cash buffer.
- Futures margin and one-contract risk at the future L-0 measurement date.

They must be resolved by preregistered, read-only or sandbox-first work orders rather than guessed.
