# Decision Record 007 — L-4 B8.9 Replacement Execution Design

## Decision

B8.9-D locks a small, static replacement design for the L-4 execution namespace. It is a control-plane artifact at E0 only: it changes no L-4 science, produces no market observation, and authorizes no activation or execution.

The design replaces only the consumed B8.8R5/v6 execution machinery. It does not replace the accepted L-4 v4 preregistration, the B8.7 no-return capacity result, or the B8.8R5AR-X/X2 incident record. The consumed legacy one-shot remains incident history and is not retried, read, hashed, statted, edited, or reused by this order.

## Why a new namespace is required

B8.8R5AR-X established a control-plane incident: the historical tracker invoked an activation-capable bootstrap while checking a pre-activation denial condition. The incident report records no scientific report, ledger, or scientific outcome, keeps validation sealed, and requires both a new owner-approved gate and a new namespace. B8.8R5AR-X2 closes the evidence-audit classification without changing those facts.

The replacement therefore uses `b89` for every future activation, one-shot marker, report, ledger, and attempt path. The B8.9-D contract deliberately contains no binding to the consumed legacy output namespace. Its static validator binds the incident report as provenance but does not invoke the historical incident validator or dereference the consumed output.

## Preserved scientific contract

B8.9-D source-binds:

- accepted L-4 v4 science, including U4/U8 matching, the 465 weekly-paired capacity ceiling, HHI and `N_eff`, regime and robustness controls, costs/turnover, side-effect constraints, exact four-outcome precedence, and per-metric/per-plan actual paired-week `MinTRL` recalculation;
- B8.7 capacity and its requirement that planning capacity is not an E1 result;
- the B8.6R13B structural manifest and U8 session-date payload as committed structural provenance; and
- the B8.8R5AR-X incident report plus the B8.8R5AR-X2 closure commit and selected Git-blob provenance.

The contract additionally records that a future falsification report must include a mechanism autopsy when a falsification outcome is claimed. This is a governance completeness requirement, not a change to the L-4 hypothesis or thresholds.

## Replacement lifecycle

The only permitted sequence is:

`B8.9-D → CP-A design review → B8.9-M → CP-A machinery review → owner-approved B8.9A`

`B8.9-M` is a future implementation order and `B8.9A` is a future canonical activation order. Neither is authorized by B8.9-D. Before the machinery review, the future work must provide a pure preflight path, a poison test proving that denial cannot invoke an activation-capable path, and a clean temporary-Git synthetic lifecycle proof.

The future tracker contract is existence-only for required artifacts. It must never invoke an activation-capable runner merely to prove that activation is absent. Any denial decision must come from a pure, fail-closed preflight that checks provenance and state without activation side effects.

## Evidence and boundaries

This record and its contract are E0 static governance only. All data, container, market, return, signal, position, covariance, regime, cost, PnL, validation, provider, network, credential, broker, paid, paper-trade, real-money, activation, execution, report-decision, and ledger authorizations are false and all access counters are zero. Validation remains sealed and `edge_claim` remains `none`.

No research log is created: B8.9-D records design/provenance, not an empirical experiment or result. The Inspector must review this design at CP-A before any owner-approved order can authorize implementation.
