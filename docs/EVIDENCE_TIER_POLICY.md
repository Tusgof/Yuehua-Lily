# Lily Evidence Tier And Locked-Gate Policy

## Purpose

This policy prevents a research report from overstating evidence and prevents a preregistered decision gate from being weakened after results are observed.

## Required Research-Report Metadata

Every JSON research report under `reports/adversarial/`, `reports/baselines/`, `reports/diagnostics/`, `reports/experiments/`, or `reports/feasibility/` must contain:

- `hypothesis_id`: an ID in `experiments/hypothesis_registry.json`;
- `evidence_tier`: `E0`, `E1`, `E2`, or `E3`;
- `tier_blockers`: a list of unresolved gates. It must be non-empty at E0 and E1.

`scripts/validate_evidence_tiers.py` blocks positive pass, acceptance, approval, validation, or edge claims below E2. Infrastructure may say that a validator completed, but a research summary below E2 may not use those values as its result or conclusion.

## Tier Meanings

| Tier | Meaning | Maximum claim |
|:--|:--|:--|
| `E0` | Infrastructure, committed fixture, synthetic test, preregistration, or explicitly labeled operational dry run | Machinery or protocol works; `edge_claim` must be `none` |
| `E1` | Real-data diagnostic evidence that is underpowered or has an unresolved gate | Diagnostic finding within named limits; no pass or edge claim |
| `E2` | Validation-grade evidence satisfying locked sample, statistics, regime, robustness, cost, provenance, and review gates | Scoped research acceptance only |
| `E3` | E2 plus operational validation, account feasibility, and a separate launch checklist | Deployment review; real money still requires explicit owner approval |

Paper trading is permitted after E2. An E0 paper-trading dry run is allowed only to test operations, with `edge_claim: none` and no strategy-performance interpretation.

## Adversarial Review Before E2

E2 and E3 require a separate adversarial review after the candidate result exists and before promotion. The reviewer must be the user or an agent other than the result's author. The report's `adversarial_review` object must record:

- `status` as `completed` or `passed`;
- `reviewed_by` identity and `reviewer_is_independent: true`;
- a non-empty `refutation_attempts` list covering leakage/timestamps, alternative nulls, implementation bugs, selection/search effects, realistic costs, survivorship or futures-roll handling where applicable, and regime or concentration dependency;
- `unresolved_critical_issues` as an empty list.

Any unresolved critical issue blocks E2. A clean review must still say what future evidence could overturn the result.

## Locked Gates

`experiments/locked_gates.jsonl` is append-only. It begins empty because B0.4 creates governance controls but does not lock an experiment preregistration.

Every later gate record binds an artifact and its validator with SHA-256 hashes and records human approval. Active hashes must match the files. A revision must append a new gate ID; it may not edit or delete an old line. The new record must include `supersedes_gate_id`, new artifact and/or validator hashes, human approval, and `reviewed_by`. Artifact and validator paths stay fixed so supersession cannot silently redirect the gate.

`.gitattributes` pins hash-bound JSON, JSONL, Python, and Markdown files to LF line endings on Windows and Linux.

## Source Lineage And Lily Changes

- Higanbana `docs/FABLE5_UPGRADE_PROPOSAL.md`: source for E0-E3, anti-overstatement, preregistration, and the paper-trading boundary. Lily replaces 0DTE-specific validation gates with persistent-position inference, global trend regimes, independent-bet equivalents, survivorship, futures-roll, and country/sleeve concentration controls.
- Higanbana `docs/HIGANBANA_TECHNICAL_DUE_DILIGENCE.md`: source for hash-bound gates, self-verification, and adversarial review. Lily applies these controls before its first preregistration so there is no legacy migration exception.
- Higanbana `AGENTS.md`: source for append-only supersession and separate review. Lily requires reviewer identity and human approval on every supersession and keeps its manifest, registry, and credentials separate.
- Lily `Note/Hypothesis.md` and `experiments/hypothesis_registry.json`: sources for the economic mechanism, hypotheses L-0 through L-4, whipsaw kill zone, breadth precondition, and Lily-specific evidence scope.
