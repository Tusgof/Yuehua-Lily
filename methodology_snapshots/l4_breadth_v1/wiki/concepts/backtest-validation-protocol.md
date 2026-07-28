---
type: concept
status: active
created: 2026-05-17
updated: 2026-07-01
source_count: 13
tags: [backtesting, validation, risk]
---

# Backtest Validation Protocol

## Definition

A backtest validation protocol is a checklist of controls used to decide whether a historical strategy test is credible enough to keep researching.

## Why It Matters

[[wiki/sources/python-finance-algo-trading-chapter-06-advanced-backtest-methods|Chapter 6]] explicitly warns that a backtest should not be used as an unrestricted search tool. Without a protocol, a researcher can accidentally select noise, leak future information, or overfit parameters.

## Minimum Validation Checklist

- Use chronological splits, not random splits, for time-series strategy evaluation.
- Keep final test data untouched until the strategy design is mostly fixed.
- Verify every feature is available at the decision timestamp.
- Include transaction costs, spread, slippage, and execution delays where relevant.
- For futures strategies, document roll construction and roll timing.
- For event-driven tests, document rebalance frequency, rebalance thresholds, commissions, bid-ask spread, and fill assumptions.
- Check whether performance depends on a few extreme days or trades.
- Report drawdown, tail risk, turnover, exposure, and leverage, not only return.
- Compare against simple baselines such as buy-and-hold, moving-average rules, or linear/logistic models.
- For ML-enhanced strategies, compare against the unfiltered rule-based signal and report whether improvements come from fewer trades, higher average trade return, lower drawdown, or hidden leverage.
- Compare flexible models against simple baselines to see whether lower training error actually improves out-of-sample trading behavior.
- Tune regularization strength, selected feature subset, or number of principal components only inside the training/validation workflow, not on the final test period.
- For regression-based strategies, inspect residual behavior rather than trusting coefficients alone.
- Distinguish predictive claims from causal claims; observational backtests rarely identify causality without additional assumptions.
- Test parameter sensitivity around the chosen values.
- Check performance across subperiods and market regimes.
- Treat reported metrics as estimates with uncertainty, especially when the sample has few trades, few regimes, or highly skewed outcomes.
- Record why the strategy should work before seeing the final backtest.
- For intraday option strategies, lock the decision timestamp and verify every feature is observable before entry.
- For conditional timing rules, train and standardize only inside rolling or expanding training windows.
- For option structures, report mid PNL and implementable PNL separately, and include per-leg bid/ask cost assumptions.
- Label evidence type clearly: historical backtest, calibrated simulation, paper result, or live-forward result.
- For regime-conditioned strategies, distinguish ex-ante regime labels from after-the-fact economic period labels.
- When using sector-ranking robustness, report whether the ranking rule would have been computable at the decision date.
- For volatility-scaled momentum strategies, separate signal validity from compounding quality by reporting arithmetic return, geometric return, realized volatility, turnover, leverage, and volatility-regime results.
- When strategy returns are autocorrelated or heteroskedastic, report HAC/Newey-West style statistical evidence rather than only naive t-statistics.
- When a strategy is selected or ranked by Sharpe ratio, report [[wiki/concepts/sharpe-ratio-inference|Sharpe Ratio Inference]] diagnostics rather than only the Sharpe point estimate: [[wiki/concepts/probabilistic-sharpe-ratio|Probabilistic Sharpe Ratio]], [[wiki/concepts/minimum-track-record-length|Minimum Track Record Length]], power where possible, and [[wiki/concepts/deflated-sharpe-ratio|Deflated Sharpe Ratio]] when multiple trials were searched.
- For financial ML strategies, avoid iid random k-fold validation; use chronological, purged, embargoed, or [[wiki/concepts/combinatorial-purged-cross-validation|Combinatorial Purged Cross-Validation]] designs.
- For LLM-based financial signals, document the model checkpoint, training cutoff, retrieval window, document timestamps, and entity handling to control [[wiki/concepts/llm-training-data-contamination|LLM Training Data Contamination]].
- Report net-of-cost metrics, turnover, spread/slippage assumptions, and market-impact assumptions before treating an ML signal as implementable.

## Interpretation Rules

- Strong in-sample and weak out-of-sample results usually mean overfitting.
- High return with deep drawdown may be unusable even if final equity is positive.
- A strategy that only works under zero-cost assumptions is probably not deployable.
- A strategy that cannot be explained is hard to monitor in live trading.
- Very large ML improvements in a preprint should be treated as a replication target unless data splits, features, labels, costs, and execution assumptions are specified.
- A high hit rate is not enough for options because payoff asymmetry can make correct small wins coexist with rare large losses.
- A simulation with disclosed assumptions is useful, but it should not be merged with historical backtest evidence unless real-data validation is complete.
- Regime explanations can be useful diagnostics, but they are not automatically predictive unless the future regime classification is available without lookahead.
- A signal that remains profitable in high-volatility regimes can still compound poorly if variance drag and whipsaw tax are large.
- A high Sharpe ratio can still be weak evidence when the sample is short, negatively skewed, fat-tailed, autocorrelated, or selected from many trials. [[wiki/sources/how-to-use-the-sharpe-ratio|How To Use The Sharpe Ratio]] argues that annualized Sharpe point estimates should not be used as standalone approval criteria.
- A strong ML backtest can still be weak evidence when the feature set is mostly price-derived transformations, validation assumes iid samples, or the result ignores costs and regime drift.

## Related Pages

- [[wiki/concepts/backtesting|Backtesting]]
- [[wiki/concepts/lookahead-leakage|Lookahead Leakage]]
- [[wiki/concepts/train-test-validation-for-time-series|Train Test Validation For Time Series]]
- [[wiki/concepts/performance-metrics-for-trading|Performance Metrics For Trading]]
- [[wiki/concepts/event-driven-backtesting|Event-Driven Backtesting]]
- [[wiki/concepts/machine-learning-signal-filtering|Machine Learning Signal Filtering]]
- [[wiki/concepts/train-test-validation-for-time-series|Train Test Validation For Time Series]]
- [[wiki/concepts/statistical-estimation|Statistical Estimation]]
- [[wiki/concepts/confidence-intervals|Confidence Intervals]]
- [[wiki/concepts/bias-variance-tradeoff|Bias-Variance Tradeoff]]
- [[wiki/concepts/overfitting|Overfitting]]
- [[wiki/concepts/regularization|Regularization]]
- [[wiki/concepts/dimensionality-reduction|Dimensionality Reduction]]
- [[wiki/concepts/linear-regression-assumptions|Linear Regression Assumptions]]
- [[wiki/concepts/residual-autocorrelation|Residual Autocorrelation]]
- [[wiki/concepts/selection-bias|Selection Bias]]
- [[wiki/concepts/omitted-variable-bias|Omitted Variable Bias]]
- [[wiki/concepts/zero-dte-conditional-trading-rules|0DTE Conditional Trading Rules]]
- [[wiki/concepts/implementable-option-pnl|Implementable Option PNL]]
- [[wiki/concepts/monte-carlo-trading-simulation|Monte Carlo Trading Simulation]]
- [[wiki/concepts/momentum-regime-shifts|Momentum Regime Shifts]]
- [[wiki/concepts/sector-momentum-rotation|Sector Momentum Rotation]]
- [[wiki/concepts/volatility-drag-and-whipsaw-tax|Volatility Drag And Whipsaw Tax]]
- [[wiki/concepts/newey-west-validation|Newey-West Validation]]
- [[wiki/concepts/sharpe-ratio-inference|Sharpe Ratio Inference]]
- [[wiki/concepts/probabilistic-sharpe-ratio|Probabilistic Sharpe Ratio]]
- [[wiki/concepts/minimum-track-record-length|Minimum Track Record Length]]
- [[wiki/concepts/deflated-sharpe-ratio|Deflated Sharpe Ratio]]
- [[wiki/concepts/sequential-false-discovery-rate|Sequential False Discovery Rate]]
- [[wiki/concepts/financial-ml-generalization-crisis|Financial ML Generalization Crisis]]
- [[wiki/concepts/combinatorial-purged-cross-validation|Combinatorial Purged Cross-Validation]]
- [[wiki/concepts/llm-training-data-contamination|LLM Training Data Contamination]]

## Open Questions

- Which exact acceptance thresholds should this wiki use for PSR, DSR, max drawdown, cVaR, and turnover?
