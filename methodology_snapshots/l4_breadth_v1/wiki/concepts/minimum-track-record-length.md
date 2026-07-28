---
type: concept
status: active
created: 2026-07-01
updated: 2026-07-01
source_count: 1
tags: [backtesting, statistics, sharpe-ratio, sample-size]
---

# Minimum Track Record Length

## Definition

Minimum Track Record Length is the minimum number of observations needed for an observed Sharpe ratio to reject a chosen Sharpe-ratio null threshold at a selected significance level.

## Why It Matters

[[wiki/sources/how-to-use-the-sharpe-ratio|How To Use The Sharpe Ratio]] uses MinTRL to show that an attractive Sharpe ratio can still be under-supported by evidence. Raising the null threshold closer to the observed Sharpe can more than double the required track record in the paper's numerical example.

## Practical Use

Use MinTRL to answer:

- Does this backtest have enough observations to support its Sharpe claim?
- Does a short live record contain enough evidence to confirm or reject degradation?
- How much embargo or out-of-sample data is needed before approving a strategy?

## Backtest Reporting Rule

When a strategy has few trades, few months, large skewness, high kurtosis, or serial correlation, report MinTRL next to Sharpe and PSR. If actual sample length is below MinTRL, the report should mark the Sharpe evidence as under-sampled.

## Related Pages

- [[wiki/concepts/sharpe-ratio-inference|Sharpe Ratio Inference]]
- [[wiki/concepts/probabilistic-sharpe-ratio|Probabilistic Sharpe Ratio]]
- [[wiki/concepts/statistical-estimation|Statistical Estimation]]
- [[wiki/concepts/backtest-validation-protocol|Backtest Validation Protocol]]
- [[wiki/sources/how-to-use-the-sharpe-ratio|How To Use The Sharpe Ratio]]

## Open Questions

- Should the wiki's standard backtest report include a required "actual observations versus MinTRL" row?
