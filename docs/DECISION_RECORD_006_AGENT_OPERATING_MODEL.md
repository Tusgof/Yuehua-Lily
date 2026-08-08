# Decision Record 006 - Agent Operating Model

- **Date**: 2026-08-09
- **Status**: accepted through the GOV-1 work order after its acceptance gates pass
- **Scope**: governance and control-plane operation only
- **Effective boundary**: work orders created after GOV-1 acceptance
- **Scientific effect**: none; no scientific, evidence, hypothesis, locked-gate, activation, data, validation, broker, provider, deployment, production, or external-publication action is authorized by this record

## 1. Context and problem

Lily uses a continuous Inspector conversation and separate implementation sessions. The prior documents established the Luna Worker and root Inspector relationship, but they did not fully specify model identity, repository permissions, fresh-thread boundaries, branch-only integration, review points, or the exact exception needed when a Worker mechanically applies an approved governance change to `PROJECT_BRAIN.md` and `IMPLEMENT_PLAN.md`.

GOV-1 adopts one explicit operating model for future work. It reduces role ambiguity and file-collision risk while preserving the scientific and operational seals already in force.

## 2. Adopted model and role boundaries

### 2.1 Inspector

The Inspector is `gpt-5.6-sol / high` with repository read-only access. The Inspector chat remains continuous and is the primary reasoning partner. The Inspector owns Project Vision, the approved content of `PROJECT_BRAIN.md` and `IMPLEMENT_PLAN.md`, work-order decomposition, acceptance gates, and independent review of Architecture, Scope, Security, and quality.

The Inspector reviews before work starts, at explicit risk checkpoints, and before milestone closure. Read-only means the Inspector does not directly modify repository files or merge branches; it may author exact approved content in the handoff or owner-facing instruction for a Worker to apply under the governance protocol below.

### 2.2 Worker

The Worker is `gpt-5.6-luna / max` with workspace-write access. A fresh Worker thread is required for every milestone or work order. The Worker independently implements exactly one bounded work order, runs its tests, updates the tracker, commits with the actual agent trailer, pushes only the milestone branch, and returns evidence.

The Worker is the sole implementation writer during a work order to avoid file collisions. The Worker must not merge, deploy, write production state, publish externally, or change scope. It must not autonomously change `PROJECT_BRAIN.md`, `IMPLEMENT_PLAN.md`, locked gates, or scientific state.

### 2.3 User and integration authority

The user receives the evidence and decides material questions and merge/integration. Merge authority is outside both roles: neither the Worker nor the read-only Inspector merges. The user performs integration or separately delegates it.

## 3. Branch and thread lifecycle

1. Every Inspector and Worker session runs the project boot sequence before project action: read `AGENTS.md`, `PROJECT_BRAIN.md`, `IMPLEMENT_PLAN.md`, `experiments/bootstrap_tracker.json`, and the owner-supplied Yuehua-Kit files `06-Final-[SETUP].txt` and `09-Order-[WORK].txt`.
2. The Inspector reviews the named work order, base, scope, expected files, verification, and stop conditions before the Worker starts.
3. The Worker creates or uses only the named milestone branch, never pushes `main`, and does not merge. One fresh Worker thread handles one milestone or work order.
4. The Worker stops at an explicit risk checkpoint, reports evidence, and returns to the Inspector. After commit, branch push, and exact-SHA CI verification, it stops for Inspector review before closure.
5. A handoff contains the pushed commit identity, changed-file scope, verification, CI evidence, seals, and residual risks. Git state and the owner-forwarded handoff are the interface between sessions.

Previous direct-main Worker behavior is superseded prospectively by this lifecycle. Historical commits, decisions, and reports are not rewritten.

## 4. Three review points and stop conditions

The three review points are:

1. **Before work starts**: Inspector review of the order, base, scope, files, verification, and acceptance gates.
2. **At explicit risk checkpoints**: Inspector review is required at CP-A before real-return access, activation, or scientific execution; CP-B after an empirical report and before outcome, registry-state, or next-hypothesis changes; CP-C before access to the sealed validation window; CP-D before paid data, provider mutation, broker preview/order, paper trading, or real-money action; and CP-X after an unexpected one-shot, provenance, leakage, or locked-invariant incident.
3. **Before milestone closure**: Inspector reviews the final diff, tracker state, acceptance evidence, exact-SHA CI result, and residual risks. The milestone is not closed by a Worker summary alone.

The Worker stops and returns to the Inspector whenever the plan is ambiguous, risk changes, an acceptance gate fails, unrelated dirty state appears, or merge, deployment, production, or external publication would be needed.

## 5. Exact governance-document change protocol

The Inspector owns the approved content of `PROJECT_BRAIN.md` and `IMPLEMENT_PLAN.md`, while repository read-only access prevents the Inspector from applying changes directly. The Worker normally may not change either document.

GOV-1 is a narrowly bounded exception: the Worker may mechanically apply this exact Inspector-approved policy to `AGENTS.md`, `PROJECT_BRAIN.md`, and `IMPLEMENT_PLAN.md`, and may reconcile only role statements that directly conflict with it. This exception does not permit reinterpretation and does not permit changing scientific status, evidence tier, hypothesis state, locked gates, scope, or the L-4 next-safe-action substance.

After GOV-1, any `PROJECT_BRAIN.md` or `IMPLEMENT_PLAN.md` change requires an Inspector-authored exact change inside an owner-approved governance work order. The Worker may apply that exact text but may not rewrite, broaden, or infer it.

## 6. Research-log and scientific boundary

Research logs remain Inspector-authored only when a genuine research event or result warrants one. GOV-1 creates no research log because it changes governance machinery only.

This record makes no scientific or evidence claim. At GOV-1 acceptance, L-4 remains unresolved E0, `edge_claim` remains `none`, validation remains sealed, and the existing L-4 next-safe-action substance is unchanged. No strategy code, research result, locked-gate change, activation, data, validation, broker, provider, credential, deployment, production, or external-publication work is included.

## 7. Consequence

The adopted model applies prospectively to work orders created after GOV-1 acceptance. It establishes a continuous Inspector chat, fresh Worker threads, sole Worker implementation authorship within an order, branch-only Worker pushes, explicit review points, user-only integration decisions, and a mechanically bounded governance-document exception. It preserves historical state and stops the Worker at the Inspector whenever the work would exceed the approved boundary.
