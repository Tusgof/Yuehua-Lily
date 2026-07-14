# Lily Data Integrity And Survivorship Policy

## Authority And Boundaries

`datasets/registry.json` is the versioned index of research datasets. Local files live under the untracked root named by `LILY_DATA_ROOT`; browser storage and absolute paths never own data state.

The data layers are deliberately separate:

- `raw`: immutable provider-native containers plus request metadata. Never overwrite, clean, splice, or back-adjust in place.
- `normalized`: canonical records derived from one or more raw containers. Preserve source identifiers, availability timestamps, revisions, parent hashes, and transformations.
- `derived`: research-ready tables, memberships, continuous series, features, or aggregates. Every artifact must identify normalized parents and be reproducible from code at a recorded commit.

A layer transition creates a new dataset ID and hashes; it never changes the meaning of an existing ID.

## Hash And Provenance Policy

- Hard-to-reproduce data requires dual integrity: the provider/source container SHA-256 and the normalized output SHA-256, plus a hash of the exact request/normalization specification.
- Freely re-downloadable daily data may use a documented container SHA-256 plus request-specification SHA-256. Re-downloadability, provider revision, and retrieval timestamp must be recorded.
- Derived data records its own SHA-256, all parent dataset IDs/hashes, and the producing Git commit.
- Provider, account/key provenance label, license/terms reference, request parameters, acquisition time, network use, paid amount, schema version, and timezone are mandatory registry facts. Credential values and account identifiers are forbidden.

## ETF And Cash-Asset Controls

1. Record instrument inception and first-available dates separately. A provider history that begins before legal inception is backfilled and must be flagged.
2. Retain closed, merged, renamed, and delisted instruments where the declared historical universe needs them. Missing dead instruments block survivorship-clean claims.
3. Store point-in-time universe membership with effective-from and effective-to dates. Present-day membership may not be projected backward.
4. Preserve raw close and adjusted close separately. Record whether adjustment covers splits, cash distributions, capital returns, or a provider total-return construction.
5. Record corporate actions and provider revisions when available. Never combine old raw prices with newly revised adjustment factors without a new dataset version.
6. Record trading currency, economic exposure/region, and any FX conversion series and timing. Global exposure through a US-listed ETF does not remove currency risk.
7. Distinguish ETF market price, NAV, and benchmark/index history. A pre-inception index backfill is not ETF tradability evidence.
8. Record stale/missing bars, exchange calendar, session close, and availability time. Same-close execution requires data known before that decision; otherwise use the next executable timestamp.

If delisted coverage, point-in-time membership, or corporate-action treatment is unavailable, the dataset may be retained only with a `scope_restricted` status and an explicit evidence-tier blocker.

## Futures Controls

1. Individual contracts are the raw tradable unit. Store root, contract ID, expiry, first-notice, last-trade, multiplier, tick size/value, currency, exchange, delivery type, and session calendar.
2. Continuous futures are derived signal conveniences, not tradable instruments. Record the active source contract for every date and every roll event.
3. Lock roll selection and timing: for example volume/open-interest crossover, fixed days before expiry, or a conservative earlier-of rule. Delivery and first-notice constraints override convenience.
4. Record the adjustment method (`none`, additive back-adjustment, ratio back-adjustment, or Panama-style) and every adjustment factor/gap. Adjusted price differences cannot be booked as PnL.
5. Implementable return later uses the held contract's unadjusted price, contract multiplier, roll trade, spread, commission, slippage, and collateral/currency accounting.
6. A vendor continuous series with undisclosed constituent contracts or roll logic is `scope_restricted` or rejected; it cannot support exact replication.
7. Never mix settlement, last trade, and synthetic continuous closes without a declared field priority and availability timestamp.
8. Expired or delisted contracts remain in history. Filtering the universe to contracts visible today is survivorship bias.

## Backfills, Revisions, And Schema Drift

Every record carries provider revision and `is_backfilled` status where the provider exposes them. A later backfill or correction creates a new raw container and registry version. Research reports state which version was used.

Provider-boundary payloads are validated before normalization. Unknown fields may be retained in raw containers, but missing required fields, type changes, timezone changes, symbol remaps, or semantic changes block ingestion until the boundary schema and tests are reviewed. Silent coercion is forbidden.

## Missingness And Scope Outcomes

- Missing observations stay missing until a declared transformation handles them; forward filling prices across non-trading periods is not a default.
- A gap caused by market closure, instrument nonexistence, provider outage, and delisting are distinct states.
- Any survivorship, currency, roll, revision, timestamp, or provider limitation is carried into `tier_blockers` of the consuming report.
- Scope restriction is a valid result. It is preferable to a broad claim built from opaque data.

## Synthetic Fixtures

Committed files under `tests/fixtures/data/` are synthetic E0 controls. They intentionally include an inactive ETF, historical membership changes, an expired futures contract, and a continuous-series roll. They prove only that boundary validation detects required structure and known failure modes; they are not market evidence.

## Source Lineage

| Wiki-relative source | SHA-256 | Policy consequence |
|:--|:--|:--|
| `wiki/concepts/stock-trend-following.md` | `1d45e5615df260c488d88dfa169084dedbaf6ca4b0b90983dbe9b2e3fc0e7f00` | Broad/delisted coverage is required; rare winners make survivor filtering especially dangerous. |
| `wiki/sources/does-trend-following-still-work-on-stocks.md` | `6f075d6d8b508ac8fd814f976ef3173f5433a4ccc714e40e9639e7621faba540` | Delisted names, distributions, splits, costs, and integer constraints are first-order inputs. |
| `wiki/concepts/long-only-trend-following.md` | `a80ab0cc6e9ec2807197a700ef4bfa560ed2ec3ec46e02dc88367724eac3d37f` | Country/region tests require explicit currency, dividends, and synchronized-regime treatment. |
| `wiki/concepts/event-driven-backtesting.md` | `67de01ae35c447d807384e47efc9d1b9815e9563a09dca49aa06226898b440fe` | Futures rolls and live-like costs require event-level contract provenance. |
| `wiki/questions/sigtech-trend-following-guide-inspection-refresh.md` | `02bef3c144662b13f22ab695815a89b522056bcb823db8d36c1adab477fafd42` | Reported results are not replication targets without the same universe, cleaning, roll, and fee conventions. |

This policy adapts Higanbana's data integrity, dual-hash, and silent-failure controls while excluding Higanbana datasets, 0DTE fields, Databento assumptions, credentials, and cost state. Lily's signature risks are ETF survivorship/backfill and futures contract/roll construction.
