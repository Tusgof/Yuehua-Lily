---
type: concept
status: active
created: 2026-05-17
updated: 2026-06-29
source_count: 1
tags: [portfolio-construction, risk-management, position-sizing]
---

# Inverse Volatility Weighting

## Definition

Inverse volatility weighting allocates less capital to more volatile assets and more capital to less volatile assets, typically by setting weights proportional to `1 / volatility`.

## Why It Matters

[[wiki/sources/a-guide-to-trend-following-strategies|A Guide to Trend Following Strategies]] uses inverse volatility weighting to convert trend signals into portfolio positions. This makes positions more comparable across futures markets with very different volatility levels.

The refreshed inspection clarifies the estimation stack in that guide: asset risk is estimated with an exponentially weighted historical volatility estimate using a 60-day span, then the overall portfolio is scaled with a 60-day covariance estimate toward a 5% long-term volatility target.

## Practical Use

- Estimate each asset's volatility using only historical information available at the rebalance date.
- Convert raw trend signals into risk-scaled exposures.
- Cap weights and leverage to avoid oversized positions in assets with artificially low recent volatility.
- Combine with [[wiki/concepts/target-volatility|target volatility]] at the portfolio level if the strategy has an overall risk target.

## Related Pages

- [[wiki/concepts/position-sizing|Position Sizing]]
- [[wiki/concepts/risk-parity|Risk Parity]]
- [[wiki/concepts/target-volatility|Target Volatility]]
- [[wiki/concepts/trend-following|Trend Following]]
- [[wiki/questions/sigtech-trend-following-guide-inspection-refresh|SigTech Trend Following Guide Inspection Refresh]]

## Tensions

- Low recent volatility can invite larger positions just before volatility rises. Future backtests should report leverage, concentration, and volatility-estimation sensitivity.
