---
type: concept
status: active
created: 2026-05-31
updated: 2026-05-31
source_count: 1
tags: [probability, statistics, risk, portfolio, quant-foundations]
---

# Covariance And Correlation

## Definition

Covariance measures whether two variables tend to move together:

```text
Cov(X, Y) = E[(X - E[X])(Y - E[Y])]
Cov(X, Y) = E[XY] - E[X]E[Y]
```

Correlation scales covariance by the variables' standard deviations:

```text
rho(X, Y) = Cov(X, Y) / sqrt(Var(X) Var(Y))
```

Correlation is unitless and lies between `-1` and `1`.

## Why It Matters

Portfolio risk depends on joint movement, not only single-asset volatility. Low or negative correlation can make a portfolio less risky than its components viewed in isolation.

This concept connects directly to [[wiki/concepts/portfolio-optimization|Portfolio Optimization]], [[wiki/concepts/risk-parity|Risk Parity]], [[wiki/concepts/hierarchical-risk-budgeting|Hierarchical Risk Budgeting]], and multi-asset trend following.

## Evidence And Examples

- [[wiki/sources/mit-quant-bible-section-02-probability-fundamentals|MIT Quant Bible - Section 2]] defines covariance and correlation after joint distributions.
- It states the important caveat: independence implies zero covariance, but zero covariance does not imply independence.

## Practical Interpretation

- Positive correlation: variables tend to move in the same direction.
- Negative correlation: variables tend to move in opposite directions.
- Near-zero correlation: no strong linear relationship, but nonlinear dependence may still exist.

## Related Pages

- [[wiki/concepts/variance|Variance]]
- [[wiki/concepts/random-variables|Random Variables]]
- [[wiki/concepts/portfolio-optimization|Portfolio Optimization]]
- [[wiki/concepts/risk-management|Risk Management]]
- [[wiki/concepts/risk-parity|Risk Parity]]
- [[wiki/concepts/hierarchical-risk-budgeting|Hierarchical Risk Budgeting]]
- [[wiki/concepts/multi-lookback-trend-following|Multi-Lookback Trend Following]]

## Tensions

- Correlation estimates can be unstable in financial data. Pages that use correlation for allocation should record estimation window, rebalance frequency, and stress-period behavior.
