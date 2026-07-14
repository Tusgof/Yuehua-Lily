# Lily Bootstrap Handoff For Codex

## Purpose

Implement Lily's foundation in bounded orders without writing strategy code or running a backtest. The governance pack must exist and verify itself before the data layer; the data layer must exist before L-0; L-0 must resolve sizing before L-1.

## Read First

1. `AGENTS.md`
2. `docs/DECISION_RECORD_001_PROJECT_REFOUNDING.md`
3. `PROJECT_BRAIN.md`
4. `docs/HYPOTHESIS_REGISTRY.md`
5. `experiments/hypothesis_registry.json`
6. `IMPLEMENT_PLAN.md`
7. `experiments/bootstrap_tracker.json`
8. `Note/Hypothesis.md` — preserve verbatim

Methodology source priority is the local LLM Wiki. Use wiki-relative citations with SHA-256 values in preregistrations.

## Repository State At Handoff

- Original Lily state reviewed at `7b25f85`.
- Founding pack contains no strategy code, backtest, data, dependency, or broker integration.
- Old control documents are archived under `Backup_/2026-07-15/`.
- `Dashboard/` remains optional visualization and does not own state.
- L-0 is active; L-1 through L-4 are proposed.
- Paid-data allowance remains USD 0 through L-0.

## Session Contract

Implement one bootstrap order per modifying session unless an order explicitly says its artifacts are atomic. State intended files and checks, then proceed. End every modifying session by committing, pushing `origin/main`, and reporting its hash.

Do not mark an order `done` in prose. `experiments/bootstrap_tracker.json` is authoritative, and a `done` claim must pass its validator against required artifacts and checks.

## B0 — Governance Foundation

### B0.1 Tracker And Hermetic Contract — first implementation commit

Create the smallest self-verifying foundation:

- `scripts/validate_bootstrap_tracker.py`
- `tests/test_validate_bootstrap_tracker.py`
- `scripts/run_test_tier.py`
- hermetic fixture proving the runner works from a clean clone
- `.github/workflows/ci.yml` running the hermetic tier on every push
- `.python-version` and a dependency manifest with one pinned supported Python line
- `.gitignore` rules for untracked machine state and credentials
- `config/machine.example.json` containing variable names/placeholders only
- a hermetic grep test rejecting absolute local paths and credential-like values in active artifacts; exclude immutable dated history under `Backup_/`

The first commit may update only B0.1 tracker state after the validator exists and passes. Do not create data or strategy modules.

Success:

```text
python scripts/run_test_tier.py hermetic
python scripts/validate_bootstrap_tracker.py
```

Both commands exit 0 on a clean clone. Missing local state is irrelevant to hermetic tests.

### B0.2 Shared Infrastructure Skeleton

Create `lib/` before any experiment script. Limit it to hypothesis-independent foundations:

- environment/interpreter metadata;
- JSON/JSONL IO;
- timestamp and calendar conventions;
- provenance and git commit capture;
- guardrail validation;
- report writing;
- search-log writing.

Add hermetic unit tests. Do not implement a signal, portfolio, or data provider.

### B0.3 Statistics Anchors

Create one statistics kernel under `lib/` with explicit conventions and golden-number tests for:

- Sharpe and autocorrelation-adjusted variance;
- PSR;
- DSR inputs/search adjustment;
- `MinTRL_falsify` and `MinTRL_validate` primitives;
- HAC/Newey-West sensitivity where the decision uses mean/alpha;
- independent-bet-equivalent counts for persistent positions.

Anchor fixtures to published worked examples and one offline reference-library calculation. Record citations, inputs, conventions, and expected values. No real strategy data.

### B0.4 Registry, Tiers, And Locked Gates

Create:

- hypothesis-registry JSON schema and validator;
- evidence-tier validator rejecting pass/edge language below E2;
- append-only `experiments/locked_gates.jsonl` plus validator and tests;
- `.gitattributes` pinning LF for hash-bound JSON, JSONL, Python, and Markdown artifacts;
- supersession fields requiring human approval and reviewer identity;
- E2 adversarial-review requirement.

The seed registry may be normalized only if the human-readable and machine-readable versions stay semantically aligned. Do not lock an experiment preregistration yet.

### B0.5 Backup And Restore

Write `docs/BACKUP_AND_RESTORE.md` covering repo, data root, local LLM Wiki citations/hashes, and untracked environment state. Rehearse a clean-clone restore of committed artifacts and record the result. External data restoration may remain a clearly named pending action until data exists.

## B1 — Data Layer Before Strategy

After all B0 workstreams pass:

1. write `docs/DATA_ACQUISITION_DECISION_TREE.md`;
2. define dataset registry and raw/normalized/derived boundaries;
3. define dual-hash/container-hash policy;
4. define ETF inception, delisting, backfill, corporate-action, currency, and point-in-time membership controls;
5. define futures individual-contract versus continuous-series purposes, roll rules, and adjusted/unadjusted provenance;
6. add provider-boundary schemas and synthetic committed fixtures;
7. add state-audit root handling that skips loudly when state is absent;
8. keep network and paid spend at zero.

Do not choose an easy data source by silently accepting survivorship or vendor-constructed histories. Any compromise becomes an explicit evidence-tier blocker.

## B2 — L-0 Sizing Feasibility

Preregister L-0 before measuring.

Required scenarios:

- capital: USD 1,000 and USD 2,000;
- ETF branch: 8–12 US-listed fractional instruments with global country and asset-class exposure;
- broker branch: Webull Thailand manual fractional, Webull Thailand OpenAPI capability, and IBKR reference capability;
- futures branch: minimum viable capital for 4, 8, and 12 micro-futures markets plus a full-size comparator.

Lock before measurement:

- target volatility or risk budget;
- maximum asset/sleeve contribution;
- cash and margin buffer;
- minimum trade/rebalance threshold;
- commission, spread, slippage, currency, and data costs;
- volatility stress and margin stress;
- definition of feasible, scope-restricted, and infeasible.

Use public terms, sandbox, or account-reported read-only permissions. Never store credentials or send orders. L-0 is an economic/engineering study and makes no edge claim.

## B3 — L-1 Baseline Preregistration

Only after L-0 and B1 decisions:

- lock the exact 60-day directional-count formula and timing;
- lock research and implementable universes separately;
- lock volatility, rebalance, cash, costs, benchmarks, and return accounting;
- define trend/whipsaw regime matrix and global country/sleeve coverage;
- define survivorship/roll controls;
- define convexity/right-tail, concentration, and big-trend-removal tests;
- compute and fund `MinTRL_falsify` before `MinTRL_validate` using effective observations;
- predeclare all searches and untouched evaluation data;
- hash the preregistration, validator, and wiki sources.

Writing or revising the L-1 preregistration and running L-1 must occur in separate sessions.

## B4 — L-1 Baseline Run

Run only the locked bounded baseline. Reports must include:

- `hypothesis_id`, `evidence_tier`, `tier_blockers`, and producing commit;
- interpreter/environment metadata;
- gross and implementable net results;
- calendar observations, trades, holding overlap, autocorrelation, and independent-bet equivalents;
- PSR/DSR/dual-MinTRL status;
- trend/whipsaw, volatility, sleeve, country/region, subperiod, and crisis matrices;
- best-market and best-trend removal;
- survivorship/roll/currency limitations;
- exact next safe action.

Default to E1. Promotion to E2 requires a separate adversarial review and no unresolved critical blocker.

## Hard Stops

Stop and report instead of guessing if:

- an action needs paid data before L-0 completes;
- a tracked credential, account identifier, or absolute local path would be introduced;
- Webull Thailand regional capability conflicts with global Webull documentation;
- IBKR permission or current margin cannot be read safely;
- data cannot meet the declared survivorship/roll standard;
- a locked gate would need in-place weakening;
- a result would require acceptance language below E2;
- broker transmission, paper trading beyond an E0 dry run, or real money is proposed.

## Source Lineage

This order adapts:

- Higanbana `docs/FABLE5_UPGRADE_PROPOSAL.md` for registry/tier/data/acceptance rules;
- Higanbana `docs/HIGANBANA_TECHNICAL_DUE_DILIGENCE.md` for self-verification, `lib/`, golden statistics, locked gates, and restore requirements;
- Higanbana `experiments/dd_remediation_tracker.json` for required-artifact completion;
- Lily `Note/Hypothesis.md` and archived `IMPLEMENT_PLAN.md` for domain content.

It intentionally excludes Higanbana's 0DTE logic, state, credentials, providers, cost guard, and legacy code patterns.
