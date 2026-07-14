# IMPLEMENT_PLAN.md

## Lily 0.0-1.0 Implementation Plan

## 1. Plan Definition
- **Project**: Trend Following - Lily
- **Version Range**: Lily 0.0-1.0
- **Plan Type**: Research-led implementation plan
- **Primary Driver**: Human research and decision-making by the project owner
- **AI Role**: Documentation assistant, structure keeper, checklist generator, code/tooling assistant only when explicitly requested
- **Core Principle**: This project advances when the owner researches, decides, and updates the plan; Codex should not invent missing research or silently make investment decisions.

## 2. Version Goal
Lily 1.0 is reached when the project has a documented, research-backed, paper-trading-ready trend-following system specification.

Lily 1.0 does not mean live trading, broker execution, production automation, or real-money deployment.

## 3. Assumptions
- The current project contains a static dashboard in `Main/`.
- The dashboard is a planning and monitoring surface, not the trading system itself.
- The research thesis is multi-asset futures trend following.
- Candidate signal direction is multi-lookback t-stat / delta-straddle.
- Baseline comparison is 60-day directional count.
- Position sizing direction is `signal x risk weight / volatility`.
- Portfolio construction should be covariance/correlation-aware.
- Portfolio leverage should come from target volatility and caps, not ad hoc per-asset leverage.
- Cost controls are required before any result is trusted.
- The owner will bring research findings into the project over time.

## 4. Scope for Lily 0.0-1.0
### In Scope
- Trading plan markdown.
- Research journal / decision log.
- Futures universe research.
- Data source and roll methodology selection.
- Baseline strategy definition.
- Candidate strategy definition.
- Risk engine specification.
- Backtest design specification.
- Validation gate definition.
- Paper trading process design.
- Weekly monitoring process design.

### Out of Scope
- Live broker integration.
- Automated order execution.
- Real-money deployment.
- Paid data vendor commitment without owner approval.
- Production infrastructure.
- Alerting system.
- Reconciliation automation.
- Optimization-heavy research without a documented baseline.

## 5. Success Criteria
### Lily 1.0 Is Usable When:
- A human can read the documents and understand exactly what will be tested.
- The system thesis, baseline, candidate signal, sizing, portfolio layer, cost assumptions, and validation gates are written down.
- Open questions are explicitly marked instead of hidden.
- Each research decision has a dated rationale.
- The next backtest implementation step is clear.

### Lily 1.0 Is Not Ready If:
- Futures universe is still undefined.
- Roll methodology is missing.
- Data source is undecided.
- Cost model is absent.
- Baseline is skipped.
- Candidate signal is not compared against baseline.
- Paper trading rules are vague.
- Any live trading step is implied without explicit approval.

## 6. Operating Model
- The owner researches and updates source decisions.
- Codex converts owner research into structured documents, checklists, templates, and code only when asked.
- When data or finance assumptions are missing, Codex must mark `[REQUIRES_RESEARCH]` or `[REQUIRES_INPUT]`.
- The dashboard can track progress, but markdown documents are the source of research truth.
- Research updates should be additive and dated; do not overwrite prior reasoning unless correcting an explicit error.

## 7. Artifact Map
| Artifact | Target Location | Owner | Status | Purpose |
|:---------|:----------------|:------|:-------|:--------|
| `PROJECT_BRAIN.md` | Project root | Codex + owner | Exists | Single source of project state and guardrails. |
| `IMPLEMENT_PLAN.md` | Project root | Codex + owner | Exists | Lily 0.0-1.0 implementation plan. |
| `Trading Plan.md` | Project root or research folder | Owner-led | Pending | Defines the trading system rules. |
| `Research Journal.md` | `Investment Research Log/` or project root | Owner-led | Pending | Records findings, decisions, rejected ideas. |
| `Futures Universe.md` | Research folder | Owner-led | Pending | Defines instruments, sectors, liquidity filters. |
| `Data & Roll Methodology.md` | Research folder | Owner-led | Pending | Defines data source, continuous futures construction, roll rules. |
| `Baseline Backtest Spec.md` | Research folder | Owner-led | Pending | Defines 60-day directional-count baseline. |
| `Candidate Signal Spec.md` | Research folder | Owner-led | Pending | Defines multi-lookback t-stat / delta-straddle signal. |
| `Risk Engine Spec.md` | Research folder | Owner-led | Pending | Defines sizing, covariance layer, target volatility, caps. |
| `Validation Report.md` | Research folder | Owner-led | Pending | Summarizes out-of-sample checks and promotion decision. |
| `Paper Trading Runbook.md` | Research folder | Owner-led | Pending | Defines live-like dry run process. |

## 8. Version Roadmap
### Lily 0.0 - Project Memory Exists
- **Goal**: Establish the project as a documented workspace.
- **Current State**: Static dashboard, `AGENTS.md`, and `PROJECT_BRAIN.md` exist.
- **Work**:
  - Keep dashboard as reference surface.
  - Keep `PROJECT_BRAIN.md` current when major scope decisions change.
  - Use `IMPLEMENT_PLAN.md` as the release path.
- **Exit Criteria**:
  - `PROJECT_BRAIN.md` exists.
  - `IMPLEMENT_PLAN.md` exists.
  - Next document to create is clear.

### Lily 0.1 - Trading Plan Skeleton
- **Goal**: Create the first written system constitution.
- **Work**:
  - Define thesis.
  - Define intended market universe at high level.
  - Define baseline and candidate signal families.
  - Define sizing and portfolio construction direction.
  - Define validation gates.
  - Define what is explicitly not allowed before paper trading.
- **Owner Research Needed**:
  - Preferred trading horizon.
  - Account/broker constraints, if any.
  - Risk tolerance and target volatility range.
- **Exit Criteria**:
  - `Trading Plan.md` exists.
  - Unknowns are marked `[REQUIRES_RESEARCH]`.
  - No live trading action is implied.

### Lily 0.2 - Research Journal / Decision Log
- **Goal**: Create a place to record research updates without losing context.
- **Work**:
  - Create a journal template.
  - Add fields for date, source, claim, evidence, decision, impact, open question.
  - Add rejected-idea tracking.
  - Add parameter-change tracking.
- **Owner Research Needed**:
  - Preferred folder location.
  - Preferred language style: Thai, English, or mixed.
- **Exit Criteria**:
  - Journal file exists.
  - First entry records the current thesis and pending research queue.

### Lily 0.3 - Futures Universe Definition
- **Goal**: Define what markets the system is allowed to trade or test.
- **Work**:
  - Draft candidate universe by sleeve: equity index, rates, FX, metals, energy, agriculture, softs.
  - Mark liquidity, contract multiplier, tick size, session, and roll considerations as research fields.
  - Define exclusion rules.
  - Define sleeve-level risk weight placeholder.
- **Owner Research Needed**:
  - Target exchanges.
  - Broker accessibility.
  - Data availability.
  - Contract liquidity thresholds.
- **Exit Criteria**:
  - Universe has a first-pass table.
  - Each instrument has status: `candidate`, `watch`, `excluded`, or `[REQUIRES_RESEARCH]`.

### Lily 0.4 - Data Source and Roll Methodology
- **Goal**: Define how futures price histories will be constructed.
- **Work**:
  - Compare data source options.
  - Define adjusted vs unadjusted continuous futures policy.
  - Define roll trigger: date-based, volume/open-interest-based, or vendor-provided.
  - Define timestamp and holiday handling.
  - Define data-quality checks.
- **Owner Research Needed**:
  - Vendor candidates.
  - Budget constraints.
  - Whether intraday data is needed or daily bars are enough.
- **Exit Criteria**:
  - Data source decision is documented or explicitly deferred.
  - Roll methodology is documented enough to implement a reproducible dataset.

### Lily 0.5 - Baseline Backtest Specification
- **Goal**: Define the baseline before candidate complexity is added.
- **Work**:
  - Specify 60-day directional count rule.
  - Specify signal bounds and neutral zone, if any.
  - Specify volatility estimate.
  - Specify rebalance cadence.
  - Specify costs required for baseline evaluation.
- **Owner Research Needed**:
  - Baseline formula details.
  - Cost assumptions.
  - Evaluation period.
- **Exit Criteria**:
  - Baseline spec can be implemented without guessing.
  - Metrics are defined before seeing results.

### Lily 0.6 - Candidate Signal Specification
- **Goal**: Define the multi-lookback t-stat / delta-straddle candidate.
- **Work**:
  - Define lookbacks: initial candidates are 32/64/126/252/504 days unless research changes them.
  - Define return or regression input.
  - Define t-stat calculation.
  - Define horizon aggregation.
  - Define signal clipping/bounding.
  - Define comparison against baseline.
- **Owner Research Needed**:
  - Final formula source.
  - Whether delta-straddle is used directly or as an interpretation layer.
  - Parameter ranges allowed before final test lock.
- **Exit Criteria**:
  - Candidate signal spec can be implemented without guessing.
  - Candidate promotion requires net-of-cost comparison to baseline.

### Lily 0.7 - Risk Engine Specification
- **Goal**: Define position and portfolio risk construction.
- **Work**:
  - Define inverse volatility sizing.
  - Define sleeve/asset risk weights.
  - Define covariance/correlation estimation.
  - Define portfolio target volatility scaling.
  - Define leverage cap, exposure cap, concentration cap.
  - Define trade floor and rebalance threshold.
- **Owner Research Needed**:
  - Target volatility.
  - Max leverage.
  - Sleeve weights.
  - Volatility and covariance windows.
- **Exit Criteria**:
  - Risk engine formulas and caps are documented.
  - No per-asset leverage override exists without portfolio-level control.

### Lily 0.8 - Event-Driven Backtest Design
- **Goal**: Define the backtest architecture before implementation.
- **Work**:
  - Define event types: market data, signal, rebalance, order, fill, roll, cost, portfolio valuation.
  - Define contract sizing and multiplier handling.
  - Define transaction cost model.
  - Define daily portfolio accounting.
  - Define no-lookahead constraints.
- **Owner Research Needed**:
  - Required fidelity level.
  - Cost model assumptions.
  - Whether backtest should be built in this workspace or another repo.
- **Exit Criteria**:
  - Backtest design can be converted to code later.
  - Known simplifications are documented.

### Lily 0.9 - Validation and Paper Trading Design
- **Goal**: Define promotion gates before any live use.
- **Work**:
  - Define chronological split.
  - Define untouched final test.
  - Define gross vs net reporting.
  - Define turnover, drawdown, skew, crash-period, and sleeve-level checks.
  - Define paper trading workflow.
  - Define weekly review checklist.
- **Owner Research Needed**:
  - Minimum acceptable result profile.
  - Paper trading duration.
  - Pause/reduce/retire rules.
- **Exit Criteria**:
  - Validation report template exists.
  - Paper trading runbook exists.
  - Limited live is still blocked until owner approval.

### Lily 1.0 - Research-Backed Paper-Ready Specification
- **Goal**: Complete a human-reviewed system specification ready for implementation or paper trading preparation.
- **Work**:
  - Review all documents for contradictions.
  - Lock v1 research assumptions.
  - Mark unresolved items clearly.
  - Decide whether the next phase is code implementation, deeper research, or pause.
- **Owner Research Needed**:
  - Final sign-off on thesis, universe, signal, risk, costs, and validation plan.
- **Exit Criteria**:
  - Trading plan is complete enough for implementation.
  - Journal contains decision history.
  - Universe and data methodology are defined.
  - Baseline and candidate specs are ready.
  - Risk engine and validation gates are ready.
  - No live deployment is authorized by default.

## 9. Priority Order
1. Trading Plan
2. Research Journal / Decision Log
3. Futures Universe
4. Data Source and Roll Methodology
5. Baseline Backtest Spec
6. Candidate Signal Spec
7. Risk Engine Spec
8. Event-Driven Backtest Design
9. Validation Report Template
10. Paper Trading Runbook

## 10. Quality Bar
- Documents must be clear enough that a future implementation does not need hidden assumptions.
- Unknowns must be labeled, not guessed.
- Each promoted idea needs evidence or a dated rationale.
- Each backtest rule must be reproducible.
- Each risk rule must state the stop condition or cap.
- Each live-related step must remain blocked until explicit owner approval.

## 11. Codex Operating Rules for This Plan
- Do not turn research gaps into invented facts.
- Do not choose broker, vendor, universe, roll rule, target volatility, or leverage cap without owner input.
- Do not implement backtest code until the relevant spec exists or the owner explicitly asks to prototype.
- Do not update dashboard state as if research is complete unless the owner confirms.
- When asked to help, produce small, reviewable artifacts.
- When editing files, keep changes scoped to the requested document or directly related index.

## 12. Update Cadence
- **After each research session**: Add journal entry.
- **After each major decision**: Update relevant spec and decision log.
- **After each artifact is created**: Update this plan status if useful.
- **Before backtest implementation**: Review `Trading Plan.md`, `Baseline Backtest Spec.md`, `Candidate Signal Spec.md`, and `Risk Engine Spec.md`.
- **Before paper trading**: Review validation report and paper trading runbook.

## 13. Current Next Action
- **Action**: Create `Trading Plan.md`.
- **Reason**: It becomes the constitution for all later research and implementation.
- **Minimum Contents**:
  - Thesis
  - Universe assumptions
  - Baseline signal
  - Candidate signal
  - Position sizing
  - Portfolio construction
  - Cost controls
  - Validation gates
  - Paper trading rules
  - Explicit stop conditions
- **Stop If**:
  - The plan starts requiring specific data vendor or broker decisions that the owner has not researched yet.
  - The document begins implying live trading before validation and paper trading.

## 14. Status Snapshot
| Version | Status | Notes |
|:--------|:-------|:------|
| Lily 0.0 | Complete | Project memory and dashboard exist. |
| Lily 0.1 | Next | Trading plan skeleton. |
| Lily 0.2 | Pending | Research journal / decision log. |
| Lily 0.3 | Pending | Futures universe. |
| Lily 0.4 | Pending | Data source and roll methodology. |
| Lily 0.5 | Pending | Baseline backtest spec. |
| Lily 0.6 | Pending | Candidate signal spec. |
| Lily 0.7 | Pending | Risk engine spec. |
| Lily 0.8 | Pending | Event-driven backtest design. |
| Lily 0.9 | Pending | Validation and paper trading design. |
| Lily 1.0 | Pending | Paper-ready research-backed specification. |

## 15. Last Updated
- **Last Updated**: 2026-06-01
- **Updated By**: Codex AI agent
- **Basis**: Existing `PROJECT_BRAIN.md`, dashboard files, and owner instruction that this should be a research-led plan maintained primarily by the owner.
