# PROJECT_BRAIN.md

## 1. Project Definition
- **Purpose**: Static interactive dashboard and working memory for building a multi-asset futures trend-following system.
- **Primary Users**: Project owner and AI agents working on the Trend Following - Lily research/build plan.
- **Problem Solved**: Keeps the long-range trading-system build plan, gates, risk controls, weekly checklist, and local progress state in one browser-based dashboard.
- **Desired Outcome**: A documented path from research to validation, paper trading, limited live deployment, and weekly monitoring.
- **In Scope**: Static dashboard, roadmap tracking, architecture map, risk engine controls, validation gates, weekly monitor checklist, journal note capture, JSON export/import, local browser state.
- **Out of Scope**: Real backtesting engine, data pipeline, broker integration, live order execution, alerts, production infrastructure, reconciliation automation.

## 2. Success Criteria
### Usable When:
- `Main/index.html` opens directly in a browser without a build step.
- Roadmap progress sliders update the summary state.
- Risk controls update target volatility, universe count, rebalance cadence, and deployment mode.
- Validation and weekly checklist states persist in browser `localStorage`.
- Journal notes can be added and exported through JSON.

### Production-Ready When:
- Trading plan and research decision log exist and are referenced from this project.
- Futures universe, data source, and roll methodology are specified.
- Baseline backtest and candidate signal backtest exist outside the static dashboard.
- Risk engine, transaction cost assumptions, validation report, and paper-trading process are implemented and documented.
- Live deployment requires explicit human approval after paper trading.

## 3. Tech Stack
| Layer | Technology | Version | Notes |
|:------|:-----------|:--------|:------|
| Language | HTML | HTML5 doctype | Verified in `Main/index.html`. |
| Language | CSS | CSS custom properties / media queries | Verified in `Main/styles.css`. |
| Language | JavaScript | Browser JavaScript | Verified in `Main/app.js`; no transpilation. |
| Runtime | Web browser | [REQUIRES_INPUT] | Runs by opening `Main/index.html`. |
| Framework | None | N/A | No framework markers found. |
| UI Library | None | N/A | DOM is created with native browser APIs. |
| Styling | Plain CSS | N/A | `Main/styles.css` only. |
| State Management | Browser `localStorage` | N/A | Uses key `trend-following-system-dashboard-v1`. |
| Database | None | N/A | No database config found. |
| ORM / Data Layer | None | N/A | No data-layer package found. |
| Authentication | None | N/A | Static local dashboard. |
| API Layer | None | N/A | No network/API code verified. |
| Testing | Node syntax check | Node version [REQUIRES_INPUT] | `node --check Main/app.js` passed on 2026-06-01. |
| Build Tool | None | N/A | No package/build config found. |
| Package Manager | None | N/A | No `package.json`, lock file, or package manager config found. |
| CI/CD | None | N/A | No CI config found in project. |
| Hosting/Deploy | Local static file | N/A | Open `Main/index.html` directly. |
| Key Dependencies | Google Fonts | Remote CSS endpoint | `index.html` loads Kanit via Google Fonts. |
| Key Assets | PNG logo | N/A | `Main/assets/yuehua-logo.png`. |

## 4. Architecture Overview
- **System Type**: Static browser app.
- **Core Flow**: User opens `Main/index.html`; CSS renders the visual system; `Main/app.js` initializes default dashboard state, merges saved `localStorage`, renders sections, binds inputs, and exports/imports JSON state.
- **Core Components**:
  - `Main/index.html`: Static HTML shell, sections, controls, script/style references.
  - `Main/styles.css`: Visual system, responsive layout, lunar/premium theme, component styling.
  - `Main/app.js`: Default state, persistence, rendering, event handlers, JSON import/export.
  - `Main/assets/yuehua-logo.png`: Watermark and monitor stamp asset.
  - `Main/README.md`: Minimal local usage note.
- **External Dependencies**: Google Fonts stylesheet for `Kanit`.
- **Persistence/State**: Browser `localStorage` plus manual JSON export/import.
- **Integration Points**: None implemented. Future integrations require explicit design for data source, broker, alerting, and reconciliation.

## 5. Design Principles
- Keep the dashboard static and runnable without build tooling unless a real implementation need appears.
- Separate roadmap documentation from actual trading/backtest code.
- Treat research, validation, paper trading, limited live, and monitoring as distinct gates.
- Keep leverage at portfolio level through target volatility and caps.
- Include costs, trade floors, and rebalance thresholds before judging any backtest result.
- Mark unknown operational decisions as `[REQUIRES_INPUT]` rather than guessing.

## 6. Current Verified State
- **Last Verified**: 2026-06-01
- **Current Milestone**: Research planning dashboard exists; trading plan and research journal are pending.
- **Completed**:
  - Static dashboard exists in `Main/`.
  - Dashboard has roadmap, architecture map, risk controls, validation gates, weekly monitor, journal, export/import.
  - `Main/README.md` documents direct browser opening and `localStorage` persistence.
  - `AGENTS.md` exists with caution-first coding guidelines for AI agents.
  - `IMPLEMENT_PLAN.md` exists as a Lily 0.0-1.0 research-led implementation plan.
  - Logo asset exists at `Main/assets/yuehua-logo.png`.
  - `node --check Main/app.js` passed on 2026-06-01.
- **In Progress**:
  - Project-level operational documentation.
- **Pending**:
  - Trading plan markdown.
  - Research journal / decision log.
  - Futures universe definition.
  - Data source selection.
  - Futures roll methodology.
  - Baseline 60-day directional-count backtest.
  - Candidate multi-lookback t-stat / delta-straddle backtest.
  - Inverse volatility + risk weight + covariance-aware risk engine.
  - Event-driven backtest with costs.
  - Validation report.
  - Paper trading workflow.
  - Limited live approval process.
  - Production monitoring, alerting, and reconciliation.
- **Latest Validation**: `node --check "D:\Fogust\Workspace\Investment\Project\Trend Following - Lily\Main\app.js"` exited successfully on 2026-06-01.

## 7. Next Safe Action
- **Action**: Create `Trading Plan.md` at the project root or inside a clearly named docs folder.
- **Preconditions**:
  - Keep current static dashboard unchanged unless the trading plan requires new links.
  - Confirm whether the trading plan should be Thai, English, or mixed Thai/English.
  - Confirm whether `Investment Research Log/` should hold the journal or remain separate.
- **Stop If**:
  - User requests live trading, broker execution, or real-money deployment before validation artifacts exist.
  - Required market data source, roll methodology, or broker assumption is missing for implementation work.
  - A proposed change requires modifying unrelated workspace files.
- **Verify With**:
  - Confirm the new markdown file exists.
  - Confirm it defines thesis, universe, signal, sizing, portfolio layer, costs, validation gates, paper/live rules, and stop conditions.
  - If dashboard links are added, open `Main/index.html` and confirm no broken local links.

## 8. Invariants & Guardrails
### Never:
- Never treat the dashboard as a validated trading system.
- Never add broker execution, live order routing, or real-money automation without explicit human approval.
- Never judge a signal only on gross returns; net costs must be included before promotion.
- Never tune parameters on the final untouched test period.
- Never increase leverage per asset ad hoc; use portfolio-level target volatility and caps.
- Never overwrite browser state without giving the user an export path.
- Never fabricate undocumented data source, broker, roll rules, or production controls.

### Always:
- Always preserve static-file usability unless the user explicitly asks for a framework or backend.
- Always run `node --check` after editing `Main/app.js`.
- Always check direct browser behavior after changing HTML/CSS/JS.
- Always keep research artifacts separate from execution/live trading artifacts.
- Always document assumptions and rejected decisions in the research journal once that file exists.
- Always include transaction costs, spread/slippage, trade floor, and rebalance threshold in backtest design.
- Always compare candidate signals against the 60-day directional-count baseline.

### Requires Approval:
- Selecting broker, data vendor, or paid infrastructure.
- Moving from research to paper trading.
- Moving from paper trading to limited live.
- Any live order placement, broker API credential storage, or real-money execution.
- Changing portfolio target volatility, leverage cap, concentration cap, or deployment mode for live use.

## 9. Operating Commands
```powershell
# Setup
Get-ChildItem -LiteralPath "D:\Fogust\Workspace\Investment\Project\Trend Following - Lily" -Force

# Development
Start-Process "D:\Fogust\Workspace\Investment\Project\Trend Following - Lily\Main\index.html"

# Test
node --check "D:\Fogust\Workspace\Investment\Project\Trend Following - Lily\Main\app.js"

# Build
Write-Output "No build step: static HTML/CSS/JS project."

# Deploy
Write-Output "No deploy target configured. Use local static file unless hosting is explicitly added."

# Status Check
rg --files "D:\Fogust\Workspace\Investment\Project\Trend Following - Lily"

# Rollback
Write-Output "No git repository detected at D:\Fogust\Workspace\Investment. Restore from backup or browser JSON export if needed."
```

## 10. Tech Stack Details & Conventions
- **Naming Convention**: Existing files use simple lowercase names for app files: `index.html`, `app.js`, `styles.css`; project/folder names may contain spaces.
- **Directory Structure Convention**:
  - Static app lives in `Main/`.
  - Static assets live in `Main/assets/`.
  - Research artifacts can use `Investment Research Log/` after scope is confirmed.
  - Project-level coordination documents should live at the project root.
- **Import Convention**: `index.html` uses relative paths: `./styles.css`, `./app.js`, `./assets/yuehua-logo.png`.
- **Error Handling Pattern**:
  - `loadState()` catches invalid saved JSON and falls back to default state.
  - Import JSON catches parsing errors and shows browser `alert`.
  - Clipboard write failure is caught and ignored.
- **Logging Pattern**: No logging pattern implemented.

## 11. Known Risks & Failure Modes
| Symptom | Cause | Impact | First Response |
|:--------|:------|:-------|:---------------|
| Dashboard opens but saved progress is missing | Browser `localStorage` was cleared, different browser/profile used, or reset was confirmed | User loses local dashboard state | Import last exported JSON if available. |
| JSON import fails | Imported file is not valid dashboard JSON | State remains unchanged or falls back during merge | Validate JSON, export current state first, retry with known dashboard export. |
| Export copies nothing to clipboard | Clipboard API unavailable or blocked by browser context | User must manually copy JSON from textarea | Select text in export area and copy manually. |
| Thai text appears garbled in terminal output | Console/codepage encoding mismatch | Terminal inspection is unreliable | Inspect in browser or read as UTF-8 with an editor/tool that supports Thai. |
| Layout breaks on small screens | CSS change affects responsive rules | Mobile usability degrades | Open `Main/index.html` at mobile width and inspect affected sections. |
| Backtest results look strong but cannot be trusted | Costs, roll rules, or leakage checks are missing | False confidence before paper/live stage | Stop promotion and complete validation checklist. |
| Live deployment pressure appears before validation | Process gate bypass | Real capital risk | Require trading plan, validation report, paper run, and approval. |

## 12. Recovery Playbooks
### If dashboard state is corrupted:
1. Check: export current textarea content if the page still opens.
2. Run: import a known-good JSON export through the dashboard.
3. Do NOT: edit `localStorage` manually unless no export exists.
4. Escalate if: no valid export exists and the lost state is required for decision tracking.

### If `app.js` has a syntax error:
1. Check: `node --check "D:\Fogust\Workspace\Investment\Project\Trend Following - Lily\Main\app.js"`.
2. Run: inspect the line reported by Node and repair the smallest failing edit.
3. Do NOT: refactor unrelated rendering or state code while fixing syntax.
4. Escalate if: the syntax error is caused by ambiguous merge/conflicting user edits.

### If the dashboard page renders incorrectly:
1. Check: open `D:\Fogust\Workspace\Investment\Project\Trend Following - Lily\Main\index.html` in a browser.
2. Run: inspect the changed HTML/CSS/JS file and revert only the specific change that caused the rendering issue.
3. Do NOT: reset all project files or delete local state.
4. Escalate if: the issue depends on browser-specific behavior or unavailable assets.

### If research work needs implementation:
1. Check: whether `Trading Plan.md` and `Research Journal.md` exist.
2. Run: create or update the missing planning document before writing backtest code.
3. Do NOT: build broker/live execution before validation and paper-trading gates.
4. Escalate if: data vendor, roll methodology, or broker assumptions are not confirmed.

## 13. Decision Log
| Date | Decision | Reason | Consequence |
|:-----|:---------|:-------|:------------|
| 2026-06-01 | Keep dashboard as static HTML/CSS/JS | Verified project has no build tooling and README says open `index.html` directly | Future edits should preserve no-build usability. |
| 2026-06-01 | Store dashboard state in browser `localStorage` | Verified `Main/app.js` uses `trend-following-system-dashboard-v1` | State is local to browser/profile and should be exported for backups. |
| 2026-06-01 | Treat trading/backtest/live system as pending | No backtest, broker, data pipeline, or production code exists in project | Next work should start with plan/journal and then baseline backtest. |
| 2026-06-01 | Candidate system path uses multi-asset futures, multi-lookback t-stat, inverse volatility, covariance-aware portfolio construction, and portfolio-level target volatility | Verified in dashboard content and project context | Validation must compare baseline and candidate net of realistic costs. |
| 2026-06-01 | Lily 0.0-1.0 plan is research-led by the owner | Owner stated that the work mainly depends on their research and updates, not Codex-led implementation | Codex should support structure, documentation, and small requested artifacts without inventing research decisions. |

## 14. Document Map
| Document | Purpose | Location |
|:---------|:--------|:---------|
| PROJECT_BRAIN.md | Single source of truth for project state and next actions | `D:\Fogust\Workspace\Investment\Project\Trend Following - Lily\PROJECT_BRAIN.md` |
| IMPLEMENT_PLAN.md | Lily 0.0-1.0 research-led implementation plan | `D:\Fogust\Workspace\Investment\Project\Trend Following - Lily\IMPLEMENT_PLAN.md` |
| README.md | Dashboard usage note | `D:\Fogust\Workspace\Investment\Project\Trend Following - Lily\Main\README.md` |
| index.html | Static dashboard shell | `D:\Fogust\Workspace\Investment\Project\Trend Following - Lily\Main\index.html` |
| app.js | Dashboard state/rendering/event logic | `D:\Fogust\Workspace\Investment\Project\Trend Following - Lily\Main\app.js` |
| styles.css | Dashboard visual system and responsive layout | `D:\Fogust\Workspace\Investment\Project\Trend Following - Lily\Main\styles.css` |
| yuehua-logo.png | Dashboard logo/watermark asset | `D:\Fogust\Workspace\Investment\Project\Trend Following - Lily\Main\assets\yuehua-logo.png` |
| AGENTS.md | AI agent behavioral guidelines | `D:\Fogust\Workspace\Investment\Project\Trend Following - Lily\AGENTS.md` |
| Trading Plan.md | Trading system rules and validation gates | `[REQUIRES_INPUT]` |
| Research Journal.md | Research notes and decision log | `[REQUIRES_INPUT]` |

## 15. Roles
- **Owner**: [REQUIRES_INPUT]
- **Architect**: [REQUIRES_INPUT]
- **Implementer**: Human user and AI agent, subject to owner approval.
- **Reviewer**: [REQUIRES_INPUT]

## 16. Operating Policy
- **Main Policy**: Use the dashboard as a planning and monitoring surface; use markdown research artifacts and code repositories for actual trading-system implementation.
- **Sub Policy**: Follow `D:\Fogust\Workspace\Investment\Project\Trend Following - Lily\AGENTS.md`: state assumptions, keep changes surgical, prefer simplicity, and verify each change.
- **Escalation Policy**: Stop and ask the human before broker/data vendor selection, paid services, real-money execution, live credential handling, or any ambiguous change to trading risk controls.

## 17. Last Updated / Last Verified
- **Last Updated**: 2026-06-01
- **Last Verified**: 2026-06-01
- **Verified By**: Codex AI agent
- **Verification Method**: Read project files, mapped file tree with `rg --files`, confirmed no package/build config files were present, read `AGENTS.md`, created `IMPLEMENT_PLAN.md`, and ran `node --check` against `Main/app.js`.
