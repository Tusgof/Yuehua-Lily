# L-0 Sizing Feasibility — E0

## Decision

**scope_restricted**. Carry a scope restriction into B3 and verify exact Webull Thailand ticker/minimum/FX and OpenAPI fractional capability before any implementation study.

No edge or deployment claim is made.

## What the evidence says

- **fact**: Public broker terms establish general fractional availability and published fees, but not a fully verified exact Thailand implementation path.
- **locked_assumption**: Capital, breadth, inverse-volatility inputs, cash, concentration, turnover, spread, margin, and stress gates are copied from the locked preregistration.
- **calculation**: ETF 8- and 10-sleeve economic sizing passes at USD 1,000 and USD 2,000; the 12-sleeve case breaches the 25% weight cap because the locked 3% volatility for SGOV creates a 29.67% target weight.
- **inference**: Fractional ETFs are the only economically plausible current-capital branch, while micro futures require capital far above USD 2,000.
- **recommendation**: Carry a scope restriction into B3 and verify exact Webull Thailand ticker/minimum/FX and OpenAPI fractional capability before any implementation study.
- **caveat**: This is deterministic E0 feasibility evidence, not evidence of trend-following returns, edge, broker approval, or deployment readiness.

## ETF economic sizing

| Capital | Breadth | Economic result | Max weight | Min trade |
|---:|---:|:---|---:|---:|
| $1,000 | 8 | feasible | 17.80% | $89.01 |
| $1,000 | 10 | feasible | 14.73% | $73.64 |
| $1,000 | 12 | infeasible | 29.67% | $44.51 |
| $2,000 | 8 | feasible | 17.80% | $178.02 |
| $2,000 | 10 | feasible | 14.73% | $147.27 |
| $2,000 | 12 | infeasible | 29.67% | $89.01 |

## Broker-path classification

| Capital | Path | Classification | Verified feasible |
|---:|:---|:---|:---|
| $1,000 | Webull_Thailand_manual_fractional | scope_restricted | false |
| $1,000 | Webull_Thailand_OpenAPI_fractional | scope_restricted | false |
| $1,000 | IBKR_fractional_reference | scope_restricted | false |
| $2,000 | Webull_Thailand_manual_fractional | scope_restricted | false |
| $2,000 | Webull_Thailand_OpenAPI_fractional | scope_restricted | false |
| $2,000 | IBKR_fractional_reference | scope_restricted | false |

## Futures minimum capital

| Contract set | Markets | Minimum capital | Binding gate |
|:---|---:|---:|:---|
| Micro | 4 | $40,600 | single_market_concentration |
| Micro | 8 | $54,200 | single_market_concentration |
| Micro | 12 | $95,400 | single_market_concentration |
| Full-size comparator | 4 | $405,900 | single_market_concentration |
| Full-size comparator | 8 | $541,200 | single_market_concentration |
| Full-size comparator | 12 | $1,614,600 | single_market_concentration |

## E0 blockers

- `no_strategy_return_evidence`
- `no_account_reported_permissions`
- `no_exact_Webull_Thailand_fractional_ticker_check`
- `no_Webull_Thailand_fractional_OpenAPI_confirmation`
- `funding_FX_cost_unverified`
- `Webull_sell_side_regulatory_fees_not_quantified`
- `futures_margin_uses_Hong_Kong_public_proxy_not_Thailand_account`
- `futures_total_round_turn_cost_and_expiry_rules_incomplete`

## Sources

- [Webull Thailand](https://www.webull.co.th/pricing) — US stock and ETF commission is 0.10% of trade value with no minimum, excluding 7% VAT; sell-side regulatory fees also apply. Caveat: Public Thailand schedule; funding FX cost is not established.
- [Webull Thailand](https://www.webull.co.th/help/faq/355-ฉันสามารถซื้อขายแบบเศษหุ้นได้หรือไม่) — Fractional trading is mobile-app only, regular-hours, market-order only, and limited to securities marked with a green diamond; quantity supports four decimals. Caveat: Does not verify the 12 candidate tickers, a minimum order, or OpenAPI support.
- [Webull Thailand](https://www.webull.co.th/open-api) — Thailand OpenAPI advertises US stock and ETF access. Caveat: Does not establish fractional-order support; other services are described as in development.
- [Webull](https://developer.webull.com/apis/docs/trade-api/overview) — Global developer documentation describes fractional trading. Caveat: Not evidence of Webull Thailand capability under the locked regional rule.
- [Interactive Brokers](https://www.interactivebrokers.com/en/accounts/required-minimums.php) — Individual account minimum is USD 0. Caveat: Trading permissions and funding methods remain account-specific.
- [Interactive Brokers](https://www.interactivebrokers.com/en/trading/fractional-trading.php) — IBKR advertises fractional trading in more than 10,500 eligible US stocks and ETFs from USD 1. Caveat: Exact candidate-ticker eligibility and Thailand-account permission were not queried.
- [Interactive Brokers](https://www.interactivebrokers.com/en/pricing/commissions-stocks.php) — IBKR Pro US stock schedules show tiered USD 0.0035/share with USD 0.35 minimum or fixed USD 0.005/share with USD 1 minimum; Lite is limited to US residents. Caveat: Annual cost depends on order count, which was not locked before measurement.
- [Interactive Brokers](https://www.interactivebrokers.com/campus/ibkr-api-page/) — IBKR publishes API options for individual clients. Caveat: No Thailand-account permission or entitlement was queried.
- [Interactive Brokers](https://www.interactivebrokers.com/en/pricing/commissions-futures.php) — Low-volume US futures broker commission is USD 0.85 per contract per side before exchange and regulatory fees. Caveat: USD 1.70 round-turn is a broker-commission floor, not total execution cost.
- [Interactive Brokers](https://www.interactivebrokers.com/en/trading/margin-futures-fops.php?hm=hk&ex=us&rgt=0&rsk=1&pm=0&rst=020204110401) — Public overnight initial-margin snapshot used for the contract roots in this study. Caveat: Hong Kong-resident schedule used because Thailand was absent from the public wizard; actual Thai-account margin is an operational blocker.
- [Yahoo Finance](https://query1.finance.yahoo.com/v8/finance/chart/ES%3DF?interval=1d&range=5d) — Public daily chart endpoints supplied the 2026-07-14 reference prices for the 12 exposure roots. Caveat: Indicative public reference prices, not executable quotes; the ES endpoint is the recorded example and the same endpoint pattern was used for other roots.
- [Vanguard, iShares, Schwab, State Street, Invesco, and iM Global Partner](https://investor.vanguard.com/investment-products/etfs/profile/vti) — Issuer product pages/factsheets identify ticker, economic sleeve, US listing, USD trading currency, inception, and expense ratio for the candidate set. Caveat: VTI is the recorded example URL; facts are research identifiers, not a recommendation, and exact broker fractional eligibility remains unverified.
- [CME Group](https://www.cmegroup.com/markets/equities/sp/e-mini-sandp500.contractSpecs.html) — Official product specifications support the contract multipliers or risk units used for CME exposure roots. Caveat: Automated page access was limited; ZN/ZT are imperfect full-size proxies for Micro Yield 10Y/2Y contracts and expiry-specific rules were not captured.

## Integrity

Producing commit: `a91f01ca029d977e04f78457148c572c4a0c7f0c`

Machine report digest: `3fc21e158e5a6d8f2dedea41f812b0fb55123c8070640cd0ae05c80e2fe6c94c`
