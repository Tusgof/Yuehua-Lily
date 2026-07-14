# AGENTS.md

## 1. Active Scope

Lily is a hypothesis-led systematic trend-following research program. The research program is the product. The static `Dashboard/` is an optional visualization surface and never owns project state.

The current execution scope is governance, data design, sizing feasibility, and research specifications. Do not write strategy code or run a real backtest until the bootstrap governance order and the relevant preregistration are complete.

## 2. Think Before Editing

- State assumptions and competing interpretations before implementation.
- Prefer the smallest change that satisfies the named work order.
- Do not refactor or clean adjacent files.
- Every changed line must trace to the current session scope.
- Use the local LLM Wiki as the primary methodology source for trend following, portfolio construction, backtesting, and statistical validation.

## 3. One Session, One Scope

Each modifying session must serve one bounded work order from `experiments/bootstrap_tracker.json` or a later approved tracker. Do not combine governance, data acquisition, hypothesis execution, and operational work in one session merely because they are adjacent.

Before editing, state:

1. the active order and hypothesis ID, if any;
2. files expected to change;
3. verification commands;
4. stop conditions.

## 4. Evidence And Claims

- `E0`: infrastructure, fixtures, synthetic tests, or operational dry runs. Claim only that machinery works.
- `E1`: real-data diagnostic evidence that is under-sampled, underpowered, or gate-blocked. Never claim edge.
- `E2`: validation-grade evidence passing preregistered sample, PSR/DSR, regime, robustness, cost, and adversarial-review gates. Claim only within tested scope.
- `E3`: E2 plus operational validation, account feasibility, and a separate launch checklist. Real-money use still requires explicit owner approval.

Paper trading is allowed only after E2 or as an explicitly labeled E0 operational dry run with `edge_claim: none`.

Any pass, acceptance, edge, or deployment language below E2 is a blocker. Scope restriction is a valid outcome and must be recorded explicitly.

## 5. Hypothesis Governance

- Every experiment must reference a registered hypothesis ID.
- Preregister falsification, validation, sample, regime, cost, and search rules before observing the result.
- Fund `MinTRL_falsify` before `MinTRL_validate`.
- Trend-following inference must account for persistent overlapping positions, serial correlation, and independent-bet-equivalent counts. Do not copy per-trade MinTRL assumptions from Higanbana.
- Killing a hypothesis requires both its preregistered statistical criterion and a mechanism autopsy.
- Resurrection requires a new registry ID and at least one new testable prediction.
- Three consecutive adequately powered falsifications of distinct edge/mechanism hypotheses trigger the Lily family review. L-0 feasibility and engineering failures do not count toward this total.

## 6. Locked Gates And Review

Locked preregistrations and their validators must be hash-bound in an append-only manifest. Never edit a locked artifact or validator silently. A revision requires a new gate ID, `supersedes_gate_id`, human approval, and replacement hashes.

Pin LF line endings for hash-bound files through `.gitattributes` so the same gate validates on Windows and Linux.

Before promotion to E2, a separate adversarial review must try to refute the result through leakage checks, alternative nulls, cost stress, survivorship/roll analysis, and implementation-bug hypotheses.

Every engineering commit must include the actual agent model/version in a trailer, for example:

```text
Agent: Codex (GPT-5.6)
```

## 7. Repository And Test Contract

- The hermetic tier uses only committed fixtures and must pass in CI on every push.
- The state-audit tier may use local data roots and optional providers; missing state must skip loudly with the missing variable named.
- Pin the supported Python version before the first implementation module.
- Use environment variables or one untracked machine manifest. Credentials and absolute local paths are forbidden in active code, config, tests, experiments, reports, and control documents. Dated files under `Backup_/` are immutable historical exceptions and must be excluded from active-path checks.
- Put hypothesis-independent infrastructure in `lib/` before the first experiment script. New scripts must import it instead of copying loaders, timestamp logic, statistics, guardrails, or report writers.
- Every report records the producing git commit. Reproduction means checking out that commit, not preserving duplicated helpers forever.
- Golden-number tests anchored to published statistical examples must exist before a real backtest.

## 8. Data And Cost Boundaries

- Lily has its own repo, registry, data budget, cost ledger, and credentials. Never share Higanbana cost guards, state, or keys.
- Initial paid-data guard: USD 0 through L-0; then a cumulative USD 50 guard through L-1 unless the owner changes it.
- Funding uses one real account and real payment only. Record true per-key provenance; never create accounts to harvest promotional credits.
- No paid action without a named hypothesis gap, preregistered cost estimate, remaining-room check, and smallest-recoverable-block rule.
- Handle survivorship bias, delisted instruments/contracts, backfilled histories, futures rolls, timestamps, and provider schema drift explicitly.
- Use dual hashes for hard-to-reproduce data. Re-downloadable free daily data may use documented container hashes.

## 9. Capital And Broker Boundaries

- Lily capital is separate from Higanbana and currently USD 1,000–2,000.
- The current-capital branch uses globally diversified exposure through US-listed fractional ETFs; Webull Thailand is the preferred operational candidate.
- IBKR is the reference broker for micro-futures feasibility and broader API capability.
- Do not assume Webull Thailand API supports fractional orders or futures until a bounded capability probe verifies the Thai account.
- Do not assume an IBKR trading permission exists until the account reports it.
- Full-size futures are outside current-capital implementation scope. Micro futures remain a sizing study, not an approved deployment path.

## 10. Project Memory

- Versioned machine-readable files in the repo own project state.
- `Note/` is the owner's Obsidian thinking space, not machine state. Preserve owner-authored notes unless explicitly asked to edit them.
- `Dashboard/` may render exported state but may not write authoritative decisions to browser `localStorage`.
- Keep `PROJECT_BRAIN.md` concise: pointers, invariants, current state, and next safe action. History belongs in decision records, reports, and git.

## 11. Session Closure

Every session that modifies files must:

1. run the scoped verification;
2. inspect the final diff and unrelated changes;
3. commit with the agent trailer;
4. push to `origin/main`;
5. report the resulting `origin/main` hash.

Do not claim completion for anything not visible at that hash. Session summaries may claim only what the pushed commit proves.

## 12. Source Lineage

This contract adapts the following Higanbana sources without importing 0DTE-specific policy:

- `Yuehua-Higanbana/docs/FABLE5_UPGRADE_PROPOSAL.md`: evidence tiers, dual MinTRL, registry, data decision logic, kill/resurrection, and paper-trading boundary.
- `Yuehua-Higanbana/docs/HIGANBANA_TECHNICAL_DUE_DILIGENCE.md`: self-verification, shared infrastructure, golden-number anchors, locked-gate review, and control-plane limits.
- `Yuehua-Higanbana/AGENTS.md`: session closure, commit trailer, test tiers, and locked-gate integrity.
- `Yuehua-Higanbana/experiments/dd_remediation_tracker.json`: required-artifact and evidence-backed completion pattern.

Changed for Lily: per-trade 0DTE statistics, SPY regimes, Databento-specific permissions, and Higanbana budgets/credentials are excluded. Lily uses persistent-position/autocorrelation-aware inference, global trend regimes, its own budget, and its own broker feasibility gates.
