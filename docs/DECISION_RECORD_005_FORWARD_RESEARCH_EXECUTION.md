# Decision Record 005 — Forward Research Execution Simplification

- **Date**: 2026-08-02
- **Status**: accepted by the owner
- **Scope**: future Lily work only; historical artifacts, locked gates, reports, and decisions remain unchanged

## 1. Problem

Lily has strong controls against leakage, unsupported claims, and irreproducible execution. Those controls correctly exposed that L-2 was statistically underfunded and that the sole L-3 result was invalid. They also protected the sealed validation window.

However, repeated remediation layers in L-3 and L-4 allowed control-plane work to dominate empirical research. Lily still has no E2 evidence. The forward plan therefore needs to preserve scientific safeguards while reducing the number of engineering loops between a research question and an interpretable result.

## 2. Decision

### 2.1 Core system path

The minimum viable research system is:

`L-1 60-day baseline + equal-notional q sizing + L-4 breadth + locked costs`

L-2 multi-lookback and L-3 inverse-volatility sizing are optional improvements. Failure or retirement of either does not block evaluation of the core system.

### 2.2 Sequential research order

1. **Finish L-4 falsification only.** B8.8R4/v5 must receive Inspector review before any activation or real-return access. If accepted, a distinct owner-approved order may create the canonical activation and run the pre-2016 falsification exactly once. Validation remains sealed.
2. **Run a family review immediately after L-4.** The Inspector compares the L-1 through L-4 evidence, writes or updates the required Thai research log, and recommends the smallest next question.
3. **Resolve L-1 first.** L-1 is the only edge hypothesis that survived its falsification window. Before validation, the owner must choose between obtaining adequate point-in-time corporate-action evidence and collecting prospective evidence. Validation cannot be opened merely to create progress.
4. **Revisit L-2 only if a new design is statically funded.** A redesigned preregistration must prove `MinTRL_falsify` capacity before any return access. If it cannot, retire L-2 rather than repeatedly rebuilding execution machinery.
5. **Give L-3 one new preregistered attempt at most.** If a small replacement design cannot produce one valid bounded run, retire inverse-volatility sizing and retain equal-notional q as the default comparator.

## 3. Worker And Inspector Contract

- GPT-5.6 Luna Max, running in its own user-opened session, is the primary implementation Worker.
- Luna boots from `PROJECT_BRAIN.md`, `IMPLEMENT_PLAN.md`, `AGENTS.md`, and `experiments/bootstrap_tracker.json`, then the owner-supplied Yuehua-Kit files `06-Final-[SETUP].txt` and `09-Order-[WORK].txt`, before every modifying session.
- Luna works autonomously within one bounded order and must commit, push, verify exact-SHA CI, and produce a handoff packet before stopping.
- The root Codex session is the Inspector. It does not supervise every implementation step. The owner calls it at a critical point.
- Luna must not create or edit `research_log/`. The Inspector decides when a log is required and is its sole author unless the owner explicitly changes that rule.
- Separate chat sessions do not have an automatic message channel. Git artifacts and the owner-forwarded handoff packet are the interface.

## 4. Critical Points

Luna must stop after pushing and hand off at these boundaries:

1. **CP-A — Real-evidence activation**: machinery is complete and CI-green, but before reading real returns, creating an activation, or executing a falsification/validation run.
2. **CP-B — Empirical result**: a bounded real-data report exists, but before changing the hypothesis outcome, beginning another hypothesis, or claiming scientific closure.
3. **CP-C — Validation unlock**: before any access to the sealed 2016-01-04 through 2026-06-30 validation window.
4. **CP-D — External or operational action**: before paid data, provider mutation, broker preview/order, paper trading, or real-money action.
5. **CP-X — Unexpected incident**: any consumed one-shot failure, provenance mismatch, leakage risk, unexpected data access, or breach of a locked invariant.

Between critical points, Luna may complete sequential bounded orders without Inspector review, provided the next order does not cross a boundary above.

## 5. Remediation Limit

- Every future execution path must pass a clean temporary-Git end-to-end test before CP-A review.
- After the first Inspector rejection, one bounded remediation is allowed.
- A second rejection at the same critical point stops patch layering. The Worker must propose a smaller replacement design in a new namespace and wait for an Inspector decision before implementation.
- A green unit test or CI run is supporting evidence, not proof that a broad scientific claim is correct.

## 6. Claim And Safety Boundaries

- E0/E1 never supports an edge or deployment claim.
- Validation remains sealed until CP-C approval.
- Locked historical artifacts are immutable.
- No broker, provider, paid, paper-trade, or real-money scope is introduced by this decision.
- The owner’s USD 1,000–2,000 capital constraint and the preference for globally diversified fractional ETFs remain unchanged.

## 7. Consequences

This decision intentionally favors a simpler, interpretable core system over completing every originally proposed enhancement. It may retire attractive ideas without empirical resolution when the available sample or implementation process cannot answer them honestly. In exchange, future work has explicit stopping rules, fewer remediation loops, and a clearer route from L-4 to the L-1 validation decision.
