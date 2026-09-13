# AGENTS.md

## 1. Communication and boot

Communicate in simple Thai when speaking with the user; retain exact English technical terms, identifiers, commands, and paths where they carry meaning.

Before work, read in order: `PROJECT_BRAIN.md`, `IMPLEMENT_PLAN.md`, `AGENTS.md`, the active tracker and work order, then owner files `06-Final-[SETUP].txt`, `09-Order-[WORK].txt`, and `11-Operate-[HERDR_WORKERS].txt` when present. Use the local LLM Wiki as the primary methodology context for trend, portfolio, backtest, and statistics questions. It never overrides locked repository artifacts.

## 2. Scope and roles

One session serves one bounded work order and one active scientific lane. A task must unlock a named decision; unrelated discoveries go to the backlog.

- **Inspector**: repository-read-only reviewer who owns policy, decomposition, risk checkpoints, acceptance, integration recommendation, and Thai research-log authorship.
- **Worker**: workspace-write implementer in a fresh thread, autonomous within the named order until its checkpoint. The default is a standalone clone with its own `.git` under the writable root. A linked worktree needs explicit Full Access and does not broaden authority.
- The Worker does not merge, deploy, publish, write production state, or change scope. Worker commits/pushes are branch-only and include `Agent: Codex (GPT-5.6-luna)`; user integration is separate.

Stop only for ambiguity, changed risk, a failed gate, unrelated dirty state, an unexpected path, or external/material authority. Do not invent micro-checkpoints. Return to the Inspector for merge, deployment, production, publication, or a new authority boundary.

## 3. Checkpoints

- **CP-A**: clean-commit, locked-input, cutoff, data-boundary, and required-audit review before development data/return access, activation, or scientific execution.
- **CP-B**: independent review after an empirical report and before changing an outcome, registry state, or next hypothesis; the Inspector writes the Thai research log.
- **CP-C**: separate owner decision before opening the sealed validation window.
- **CP-D**: separate owner decision before paid data, provider mutation, broker preview/order, paper trading, or real money.
- **CP-X**: immediate review after an unexpected one-shot, provenance, leakage, or locked-invariant incident.

## 4. Evidence and anti-overstatement

E0 is infrastructure, fixtures, synthetic evidence, or an operational dry run: machinery only, no edge. E1 is blocked, underpowered, or under-sampled real-data diagnosis: hypothesis-generating only. E2 requires preregistered statistics, regimes, robustness, costs, and independent adversarial review. E3 additionally requires operational validation and a separate launch decision. Never promote below E2, and use `edge_claim: none` for E0/E1.

Every experiment has a registered hypothesis, preregistered decision/falsification rules, costs, sample, regimes, and search accounting. Persistent positions require serial-correlation-aware statistics, effective independent bets, PSR, DSR when searching, and HAC/Newey-West where appropriate. Killing requires the locked statistical rule plus a mechanism autopsy; resurrection needs a new ID and prediction.

## 5. Locked science and version discipline

Locked gates, manifests, schemas, validators, registries, reports, and hypothesis statuses are append-only or immutable as their contracts require. A material semantic or integrity change creates a new approved version with `supersedes_gate_id`, human approval, replacement hashes, and provenance; never silently edit locked bytes. Reuse an existing contract before adding a schema or validator. A second rejection at one critical point requires simplification and a smaller Inspector-reviewed design.

## 6. Data, leakage, and external boundaries

Use only data available at the decision time. Enforce cutoff dates before return/value decoding, explicit provenance, timestamps, corporate actions, survivorship/inception/delisting, futures rolls, missingness, currencies/FX, raw/normalized/derived boundaries, and container/content hashes. The 2016-01-04 through 2026-06-30 validation window is sealed unless CP-C and owner authority explicitly open it.

Paid-data guard is USD 0 through L-0 and cumulative USD 50 through L-1. Do not read or store credentials, account identifiers, absolute machine paths, or provider/broker state. No provider/network data call, credential use, paid action, broker action, paper trade, live trade, activation, or real-money action is implied by E0 machinery.

## 7. Verification and logs

Run focused tests during work, the static tracker check locally, and fast exact-SHA CI on every push. Full runtime audit is reserved for control/tracker/locked-gate changes, named risk/closure points, main integration, or weekly/manual review. Never run the full tracker from a dirty checkout. Do not weaken a test or validator to obtain green.

No log is written for synthetic/control-plane work. After a genuine empirical event, the Inspector alone writes the required audited Thai research log before the outcome closes. The Worker must not create or edit `research_log/`.

## 8. Session closure and pointers

For an authorized modifying session, inspect the final diff and unrelated changes, run scoped verification, then commit and push only the named branch with the model trailer and report the exact remote hash. Never merge, push main, deploy, or publish. If the order stops before commit, report no commit/push.

Active policy: `PROJECT_BRAIN.md`, `IMPLEMENT_PLAN.md`, Decision Record 008, `experiments/bootstrap_tracker.json`, locked-gate manifests, hypothesis registry, reports, and Git. Dated `Backup_/` files are immutable history, not active project state. Future BRAIN/PLAN/AGENTS edits require Inspector-authored exact policy in an owner-approved governance order.
