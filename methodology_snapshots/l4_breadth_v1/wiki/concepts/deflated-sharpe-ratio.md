---
type: concept
status: active
created: 2026-07-01
updated: 2026-07-01
source_count: 2
tags: [backtesting, sharpe-ratio, multiple-testing, overfitting]
---

# Deflated Sharpe Ratio

## Definition

Deflated Sharpe Ratio is a Sharpe-specific multiple-testing adjustment for the selected-best-strategy problem. It asks whether the best observed Sharpe remains impressive after accounting for the number and dispersion of strategy trials.

## Why It Matters

[[wiki/sources/how-to-use-the-sharpe-ratio|How To Use The Sharpe Ratio]] argues that researchers rarely test only one strategy. If many variants are tried and only the best result is reported, the observed Sharpe is inflated by selection.

DSR is designed for familywise-error-style decisions where one selected model or strategy supersedes the rest.

## Practical Inputs

DSR needs:

- Observed selected Sharpe.
- Null Sharpe threshold.
- Effective number of trials.
- Cross-sectional dispersion of Sharpe estimates across trials.
- Return-distribution diagnostics used by the Sharpe sampling variance.

[[wiki/sources/how-to-use-the-sharpe-ratio|Sharpe Ratio Inference]] gives three practical ways to estimate the effective number of trials when strategy variants are correlated: cluster the trial return-correlation matrix, count non-trivial eigenvalues beyond a Marchenko-Pastur bound, or use effective rank/eigenvalue entropy as a likely upper bound.

[[wiki/sources/epistemic-failure-methodological-reform-financial-ml|Epistemic Failure And Methodological Reform In Financial Machine Learning]] extends the same warning to financial ML: model, feature, and hyperparameter searches can manufacture "paper alpha" unless DSR, PBO, or a comparable search-aware diagnostic is reported.

## Backtest Use

Use DSR when:

- A strategy was chosen after many parameter sweeps.
- Many features, filters, universes, or models were tried.
- A paper reports the best strategy but not the full search path.
- The selected result may become a primary production strategy or published claim.

## Cautions

- DSR is only as honest as the trial count and search log. If the researcher does not record what was tried, the effective number of trials must be estimated conservatively.
- Correlated parameter variants should not be counted naively as fully independent trials, but collapsing them too aggressively can understate search bias.
- The paper notes that CPCV can also deflate Sharpe when the strategy algorithm is available, but it is simulation-based rather than the same closed-form DSR route.

## Related Pages

- [[wiki/concepts/sharpe-ratio-inference|Sharpe Ratio Inference]]
- [[wiki/concepts/probabilistic-sharpe-ratio|Probabilistic Sharpe Ratio]]
- [[wiki/concepts/overfitting|Overfitting]]
- [[wiki/concepts/selection-bias|Selection Bias]]
- [[wiki/concepts/backtest-validation-protocol|Backtest Validation Protocol]]
- [[wiki/sources/how-to-use-the-sharpe-ratio|How To Use The Sharpe Ratio]]
- [[wiki/sources/epistemic-failure-methodological-reform-financial-ml|Epistemic Failure And Methodological Reform In Financial Machine Learning]]

## Open Questions

- How should the local backtest code log parameter-search breadth so DSR can be computed honestly?
