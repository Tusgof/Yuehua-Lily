# Lily Data Acquisition Decision Tree

## Scope

This decision tree governs data selection before any download or purchase. B1 defines contracts and synthetic fixtures only: network use and paid spend are both zero.

## Decision Sequence

```text
Named hypothesis gap
  -> Can committed synthetic data answer an engineering question?
       yes: use fixtures; evidence remains E0
       no: continue
  -> Does a registered local dataset already cover the gap?
       yes: verify registry entry, hashes, license, timestamps, and scope
       no: continue
  -> Is a free, reproducible source adequate without hidden survivorship or roll construction?
       yes: preregister request, capture provider payload, and register provenance
       no: record the exact compromise as a tier blocker
  -> Would acquisition cost money or require credentials/network access?
       through L-0: stop; paid-data guard is USD 0
       after owner-approved guard change: preregister the gap, estimate, ledger key,
       remaining room, and smallest recoverable block before any action
```

No provider is preferred merely because it is easy to access. A convenient current-universe ETF history or vendor continuous-futures series is rejected if its construction cannot meet the required evidence scope.

## Mandatory Questions Before Acquisition

1. Which registered hypothesis and unresolved field require the data?
2. Is the requested layer raw provider payload, normalized canonical data, or a derived research table?
3. Are timestamps, timezone, release/availability time, revisions, and backfills observable?
4. For ETFs or equities, are inception, closure/delisting, distributions, splits, currency, and point-in-time universe membership represented?
5. For futures, are individual contracts available with expiry, first-notice, last-trade, multiplier, tick, and exchange calendar metadata?
6. If a continuous futures series is offered, are active-contract selection, roll timing, and adjustment method reproducible? Can PnL still be calculated from actual contracts?
7. Does the license permit local research storage and reproducibility?
8. Is the source freely re-downloadable, or hard to reproduce after acquisition?
9. What hash policy applies, and what exact request specification must be retained?
10. What limitation remains even if ingestion succeeds?

## Instrument Branches

### ETF And Cash-Asset Branch

Require provider-native prices plus an instrument master and point-in-time membership history. Record raw close and adjusted close separately, the adjustment basis, distribution treatment, trading currency, economic exposure currency where known, inception, closure/delisting, and provider revision. A current list of surviving ETFs cannot support a historical breadth claim.

### Futures Branch

Acquire individual-contract bars and contract reference data as the primary raw evidence. A continuous series is a derived convenience for signal research only. Its roll rule, adjustment method, and active contract must be recorded on every transition. Implementable PnL and costs must later use the contract actually held and explicit roll trades.

## Decision Outcomes

- `accept_for_declared_scope`: the source meets the locked scope and all required provenance can be stored.
- `scope_restricted`: usable for a narrower E0/E1 question; every excluded inference becomes a machine-readable blocker.
- `reject`: construction, license, timestamps, survivorship, roll logic, or provenance is too opaque for the named question.
- `pending_cost_gate`: potentially useful, but no paid action is allowed until the project guard and preregistered cost decision permit it.

## Registration Before Use

Every accepted dataset receives a versioned entry under `datasets/registry.json` before a research report consumes it. The entry identifies the storage layer, provider/request, coverage, point-in-time and survivorship status, license, parents, and required hashes. Paths use repo-relative references or `LILY_DATA_ROOT`; absolute machine paths are forbidden.

## Source Lineage

| Wiki-relative source | SHA-256 | B1 use |
|:--|:--|:--|
| `wiki/concepts/selection-bias.md` | `0d89f1914504fc556de6c919ab2f62db283b0015432d6935b9164be0d6e7e417` | Current/surviving universes can bias historical results. |
| `wiki/concepts/backtest-validation-protocol.md` | `c7f843310706d902120651e677429e66cbde9ce96ee526544de5419ee99aefa0` | Futures roll construction, timestamps, costs, and evidence labels must be explicit. |
| `wiki/concepts/event-driven-backtesting.md` | `67de01ae35c447d807384e47efc9d1b9815e9563a09dca49aa06226898b440fe` | Individual contracts, roll events, spreads, and fills cannot be hidden in one return series. |
| `wiki/concepts/lookahead-leakage.md` | `b08046e58a62e321e93e53ea008758e5be34fcd23847a11f0d8834a922f08063` | Revised, survivor-only, or post-decision data is not point-in-time evidence. |

Higanbana `docs/FABLE5_UPGRADE_PROPOSAL.md` supplies the named-gap, decision-tree, cost-gate, and smallest-recoverable-block pattern. Lily replaces 0DTE/provider-specific branches with global ETF and futures survivorship, currency, contract, and roll controls and keeps a separate budget, registry, and credentials.
