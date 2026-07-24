---
type: concept
status: active
created: 2026-05-17
updated: 2026-06-29
source_count: 8
tags: [risk, portfolio, live-trading]
---

# Position Sizing

## Definition

Position sizing is the rule for deciding how much capital or risk to allocate to a trade, asset, or strategy.

## Why It Matters

[[wiki/sources/python-finance-algo-trading-chapter-17-from-nothing-to-live-trading|Chapter 17]] discusses bet sizing and strategy portfolios. Position sizing often determines whether a strategy is survivable even when the signal logic is unchanged.

[[wiki/sources/trend-following-strategies-a-practical-guide|Trend Following Strategies: A Practical Guide]] makes this point sharper for trend following: leverage management can dominate realized results, and excessive leverage can destroy the intended convex payoff profile.

[[wiki/sources/a-guide-to-trend-following-strategies|A Guide to Trend Following Strategies]] adds a concrete construction stack: asset-level inverse volatility weighting, portfolio-level target volatility, stop-losses, exposure limits, rebalance thresholds, and cost assumptions.

[[wiki/sources/designing-robust-trend-following-system|Designing Robust Trend-Following System]] adds signal-strength-aware sizing, risk budgeting, hierarchical risk budgeting, and a trade floor that skips small position adjustments to control costs.

[[wiki/sources/a-century-of-profitable-industry-trends|A Century of Profitable Industry Trends]] uses simple volatility-based sizing for active long industry positions and shows that rebalance thresholds can reduce unnecessary small trades.

[[wiki/sources/does-trend-following-still-work-on-stocks|Does Trend Following Still Work on Stocks?]] uses stock-level volatility sizing with a 30% annualized target, a `max(200, N_holdings)` diversification floor, and a 200% leverage cap.

The refreshed inspection clarifies that this sizing is recomputed daily using 42-day annualized volatility, with all ideal weights scaled down proportionally if gross exposure would exceed 200%.

[[wiki/sources/mit-quant-bible-section-07-question-bank|MIT Quant Bible - Section 7]] adds a betting interpretation through the [[wiki/concepts/kelly-criterion|Kelly Criterion]], where favorable repeated bets should be sized as a fraction of wealth rather than all capital.

[[wiki/sources/rethinking-trend-following-optimal-regime-dependent-allocation|Rethinking Trend Following: Optimal Regime-Dependent Allocation]] adds a regime-specific sizing approach for trend following. It estimates each regime's conditional mean and second moment, then maps regimes into exposure weights through [[wiki/concepts/optimal-regime-dependent-allocation|optimal regime-dependent allocation]] rather than using fixed Bull/Bear exposure.

## Common Approaches

- Fixed capital per trade.
- Fixed fraction of equity.
- Volatility-targeted sizing.
- Risk-per-trade sizing based on stop distance.
- Portfolio-level sizing based on correlation or contribution risk.
- [[wiki/concepts/target-volatility|Target volatility]] sizing that scales exposure to a fixed risk target.

## Practical Rules

- Size positions from risk limits, not from desired profits.
- Consider maximum drawdown and tail risk before increasing size.
- Reduce size for strategies with uncertain live execution.
- Avoid letting correlated strategies create hidden concentration.
- Define maximum leverage and exposure limits before deployment.

## Related Pages

- [[wiki/concepts/risk-management|Risk Management]]
- [[wiki/concepts/portfolio-optimization|Portfolio Optimization]]
- [[wiki/concepts/live-trading-infrastructure|Live Trading Infrastructure]]
- [[wiki/concepts/trading-plan-and-journal|Trading Plan And Journal]]
- [[wiki/concepts/target-volatility|Target Volatility]]
- [[wiki/concepts/inverse-volatility-weighting|Inverse Volatility Weighting]]
- [[wiki/concepts/risk-parity|Risk Parity]]
- [[wiki/concepts/hierarchical-risk-budgeting|Hierarchical Risk Budgeting]]
- [[wiki/concepts/rebalance-threshold|Rebalance Threshold]]
- [[wiki/concepts/turnover-control-mechanism|Turnover Control Mechanism]]
- [[wiki/concepts/stock-trend-following|Stock Trend Following]]
- [[wiki/concepts/trend-following|Trend Following]]
- [[wiki/concepts/optimal-regime-dependent-allocation|Optimal Regime-Dependent Allocation]]
- [[wiki/concepts/kelly-criterion|Kelly Criterion]]

## Open Questions

- Which sizing rule should be the default for future strategy templates?
