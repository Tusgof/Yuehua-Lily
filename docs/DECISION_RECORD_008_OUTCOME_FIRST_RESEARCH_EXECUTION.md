# Decision Record 008: Outcome-First Research Execution

- **Date**: 2026-09-13
- **Scope**: prospective governance and documentation only; no historical scientific evidence or locked research rule changes.

## Problem

Lily accumulated many governance, schema, validator, and full-repository-check versions while CORE-1 still has no real development-return result. E0 machinery must not be confused with investment evidence.

## Evidence observed

- The current hermetic suite is 686 tests.
- The clean full tracker took roughly 15+ minutes locally and repeated the test tier.
- L-2 is E1 `underfunded_scope_restricted`.
- L-3 is E1 `scope_restricted`/unresolved.
- L-4 is unresolved E0.
- Validation remains sealed.

## Decision

There is one active scientific lane: the CORE-1 stable baseline. New L-2, L-3, and L-4 execution is paused until CORE-1 receives a development decision.

### Fixed question

On the locked U8 daily total-return universe through 2015-12-31, does any of `CORE1_DC60`, `CORE1_DC120`, or `CORE1_SMA200` pass all locked A-H gates after locked costs?

### Locked science preserved

Candidate definitions, U8 order, costs, timing, A-H gates, selection/stop rules, evidence tiers, provenance, and the 2016-01-04 through 2026-06-30 validation seal do not change.

### Shortest safe queue

1. Finish decision/lifecycle binding.
2. Run one CP-A.
3. Run one development-only execution.
4. Run one CP-B.
5. Have the Inspector write the Thai research log.
6. Select exactly one candidate or stop. There is no parameter rescue and no fourth candidate.

## Operating model

- Verification is risk-proportionate: focused tests during implementation; a static tracker check locally; fast CI on every push; full runtime audit only for control/tracker/locked-gate changes, before CP-A/CP-B/CP-C as applicable, on main integration, or weekly/manual—not after every small edit.
- Edit uncommitted work in place. Create a new locked version only when a locked/published artifact must be superseded for a material semantic or integrity reason. Reuse an existing contract when it safely represents the decision; do not create a new schema or validator for convenience.
- The Worker runs one bounded order autonomously to its named risk checkpoint. The Inspector reviews before work, at CP-A/B/C/D/X, and once before milestone closure. Arbitrary micro-checkpoints are not part of the flow.
- A normal Worker uses a standalone clone with its own `.git` under the writable root. Linked worktrees require explicit Full Access only when necessary and do not broaden authority.
- No log is written for synthetic or control-plane work. A Thai research log is mandatory after a genuine development empirical result and before the scientific outcome closes. The Inspector is its sole author.

Historical `match_*` checks for the superseded control-document text validate the exact bytes in the dated `Backup_/2026-09-13/` archives after GOV-2 archive presence is established. GOV-2 locks those three archive files with exact SHA-256 rules; this preserves historical verification while allowing the active control documents to remain concise. New `match_gov2_*` checks always validate the active files.

## Supersession and boundaries

This decision prospectively supersedes conflicting forward-order/process text in Decision Records 005/006 and active BRAIN/PLAN/AGENTS. It does not rewrite history, locked bytes, evidence tiers, or hypothesis statuses.

Not authorized: data/return/container access; validation access; activation or execution outside the named development gate; provider, broker, credential, paid, paper, or real-money action.

## Success measure

The next scientific milestone ends with a reproducible empirical report and an understandable Thai conclusion, or an honest stop.
