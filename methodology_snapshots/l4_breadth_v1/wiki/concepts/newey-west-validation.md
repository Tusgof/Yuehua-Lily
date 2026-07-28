---
type: concept
status: active
created: 2026-06-29
updated: 2026-07-01
source_count: 2
tags: [backtesting, statistics, validation, time-series]
---

# Newey-West Validation

## Definition

Newey-West validation uses heteroskedasticity-and-autocorrelation-consistent standard errors to test whether a strategy's average return or alpha is statistically distinguishable from zero when returns may be serially correlated and heteroskedastic.

## Why It Matters

Financial strategy returns often violate the assumptions behind naive t-tests. Momentum strategies can have autocorrelation because positions persist, and volatility changes across regimes. A naive standard error can overstate significance.

[[wiki/sources/time-series-momentum-theory-strategies-volatility-scaling|Time Series Momentum: Theory, Strategies, And Volatility Scaling]] applies Newey-West with six lags to volatility-scaled TSMOM results and claims scaled strategies have t-statistics above `2.5`.

[[wiki/sources/how-to-use-the-sharpe-ratio|How To Use The Sharpe Ratio]] strengthens this caution from a Sharpe-specific angle. HAC/Newey-West style validation is useful for mean returns and regression alpha, but Sharpe-ratio decisions should also account for sample length, skewness, kurtosis, autocorrelation, and multiple testing through [[wiki/concepts/sharpe-ratio-inference|Sharpe Ratio Inference]].

## Practical Use

Use Newey-West or a comparable HAC estimator when:

- Testing mean strategy returns.
- Testing regression alpha from time-series returns.
- Comparing strategies with overlapping signals or persistent positions.
- Reporting statistical evidence for volatility-scaled or regime-conditioned strategies.

## Cautions

- Lag choice matters and should be reported.
- Newey-West does not fix lookahead leakage, data snooping, or omitted transaction costs.
- A statistically significant mean can still be unusable if drawdown, tail risk, turnover, or capacity is poor.
- Newey-West is not a substitute for Sharpe-specific corrections such as PSR or DSR when the decision is based on Sharpe-ratio ranking.

## Related Pages

- [[wiki/concepts/backtest-validation-protocol|Backtest Validation Protocol]]
- [[wiki/concepts/residual-autocorrelation|Residual Autocorrelation]]
- [[wiki/concepts/robust-standard-errors|Robust Standard Errors]]
- [[wiki/concepts/time-series-momentum|Time-Series Momentum]]
- [[wiki/concepts/sharpe-ratio-inference|Sharpe Ratio Inference]]
- [[wiki/concepts/probabilistic-sharpe-ratio|Probabilistic Sharpe Ratio]]
- [[wiki/concepts/deflated-sharpe-ratio|Deflated Sharpe Ratio]]
- [[wiki/sources/time-series-momentum-theory-strategies-volatility-scaling|Time Series Momentum: Theory, Strategies, And Volatility Scaling]]
