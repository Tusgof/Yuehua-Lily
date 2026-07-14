# Lily Statistics Conventions

## Scope

`lib/statistics.py` contains dependency-free inference primitives. It does not contain a signal, strategy, portfolio rule, broker rule, or backtest.

These conventions are locked as infrastructure inputs only. A later hypothesis preregistration must still choose its return frequency, nulls, lags, regimes, power, and acceptance thresholds before seeing results.

## Core Conventions

- Sharpe is mean return divided by population standard deviation with no annualization inside the kernel.
- Skewness is the population standardized third central moment.
- Kurtosis is raw Pearson population kurtosis, not excess kurtosis. The generalized Sharpe variance formula subtracts one internally.
- PSR is the Normal CDF of the observed-minus-null Sharpe divided by the adjusted Sharpe standard error.
- Observed inference uses finite-sample Bartlett weights: `1 + 2 Σ(1-k/N)ρ_k`.
- Prospective MinTRL planning uses asymptotic inflation: `1 + 2 Σρ_k`. The lag vector must be preregistered and reported.
- `MinTRL_validate` uses the distance from the validation null to the expected alternative plus stated one-sided significance and power.
- `MinTRL_falsify` uses the distance from the claimed minimum to a preregistered adverse true Sharpe plus stated one-sided significance and power.
- DSR uses the expected maximum Sharpe hurdle from effective trial count and cross-trial Sharpe dispersion. Effective trials must come from a declared search log or a conservative correlation-based estimate.
- Newey-West uses Bartlett weights and divides autocovariances by `N`. It supports mean/alpha sensitivity and does not replace Sharpe-specific PSR/DSR.
- Cross-sectional independent bets use eigenvalue participation ratio `(Σλ)^2 / Σλ^2`.
- Joint independent-bet equivalents equal autocorrelation-adjusted time observations multiplied by cross-sectional effective dimensions. Calendar observations, trades, holding overlap, and this effective count must all be reported separately.

## Golden Anchors

`tests/fixtures/statistics_golden.json` records all inputs and expected values.

1. Published-method anchor: the Bailey/López de Prado-style PSR/MinTRL example used in the Higanbana technical review reproduces generalized variance `0.891829437576`, PSR `0.821497`, and MinTRL `285` from Sharpe `0.092203`, `N=90`, skewness `1.221374`, and raw kurtosis `3.09085`.
2. Offline library cross-check: SciPy `1.17.1` is used once to verify Normal CDF/PPF and population moment anchors. SciPy is not a runtime dependency.
3. Hand-calculation anchors cover Bartlett autocorrelation inflation, dual powered MinTRL, DSR search hurdle, Newey-West variance/t-statistic, and eigenvalue participation ratio.

The golden fixture stores a deliberately wrong excess-kurtosis variance result. The test must distinguish it from the raw-kurtosis result so a convention slip fails loudly.

## Local Methodology Sources And Hashes

Hashes were calculated on 2026-07-15 and bind the methodology snapshot used to write these conventions.

| Wiki-relative source | SHA-256 |
|:--|:--|
| `wiki/concepts/minimum-track-record-length.md` | `ca65225740673bd363be7461b8022281da08ae32e6ff42f8887f1072eb51ad81` |
| `wiki/concepts/probabilistic-sharpe-ratio.md` | `a644495d207403711a55d815abb0722018bba23d428d3d904dd6c4b5a8cef6a5` |
| `wiki/concepts/deflated-sharpe-ratio.md` | `90663b67e49dcec90bd641e801f9464e593ff8fe9091b2d70e9f4645381af556` |
| `wiki/concepts/newey-west-validation.md` | `355b37f5f64d938d254337663b5df635ce008e47f8197eac041c03790643fcc5` |
| `wiki/concepts/sharpe-ratio-inference.md` | `4a13ed9ba9d8e6539544a1259f933a5cc1137fbdb899f04e91fa49fa6f7e6f5e` |
| `wiki/sources/how-to-use-the-sharpe-ratio.md` | `0dd77f17c74091d736676c342c15034f0e05daa3b68bc0c85620b14b24ecf1fb` |

## Limitations

- The generalized Sharpe approximation and AR/Bartlett inflation are approximations, not proof of iid or Gaussian returns.
- Lag selection, frequency conversion, missing returns, risk-free series, and annualization remain hypothesis-level decisions.
- Newey-West does not repair leakage, data snooping, survivorship bias, omitted costs, or bad execution timing.
- Participation ratio measures effective dimensions, not guaranteed independent profit opportunities.
- No result may reach E2 from these metrics alone; regime, robustness, cost, provenance, and adversarial-review gates remain mandatory.
