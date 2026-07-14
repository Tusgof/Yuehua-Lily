# Lily Backup And Restore

## Recovery Contract

Lily separates four kinds of state so a repository clone is never mistaken for a complete machine restore.

| State | Authority | Backup and restore rule |
|:--|:--|:--|
| Committed project artifacts | Git remote plus recorded commit hash | Clone the remote, checkout the recorded hash, then run the hermetic tier and tracker validator |
| Machine configuration | Untracked `config/machine.json` or environment variables | Recreate from `config/machine.example.json`; never commit values or absolute paths |
| Research data | External root named by `LILY_DATA_ROOT` | Restore from the future data backup/catalog and verify hashes; no Lily data exists at B0.5 |
| Local LLM Wiki | Separate knowledge repository named by `LILY_WIKI_ROOT` | Reattach the external root and verify repo-recorded wiki-relative SHA-256 hashes |

Credentials are not project backup material. Restore them through the broker or provider's approved secret store, or issue new credentials. Never copy credentials into Git, reports, machine examples, or data catalogs.

## Committed-Artifact Restore

1. Clone `https://github.com/Tusgof/Yuehua-Lily.git` into a new empty directory.
2. Checkout the exact commit recorded by the report or decision being reproduced: `git checkout --detach <commit>`.
3. Confirm `git rev-parse HEAD` matches the recorded 40-character hash.
4. Install the Python version in `.python-version`; do not silently substitute another minor line.
5. Run `python scripts/run_test_tier.py hermetic`.
6. Run `python scripts/validate_bootstrap_tracker.py`.
7. Confirm `git status --porcelain` is empty before adding machine state.

Passing these checks proves restoration of committed artifacts only. It does not prove that external data, a Wiki checkout, broker permission, or credentials are available.

## Machine-State Restore

Create an untracked `config/machine.json` from `config/machine.example.json`, or define only the required environment variables. The example contains names and null placeholders only. At bootstrap those names are `LILY_DATA_ROOT`, `LILY_WIKI_ROOT`, `LILY_IBKR_PYTHON`, and `LILY_WEBULL_PYTHON`.

The active-path audit must continue to reject absolute paths and credential-like values in committed files. A machine manifest is local convenience, not project memory.

## Local LLM Wiki Restore

The Wiki remains a separate repository. Lily stores only wiki-relative citations and SHA-256 values, such as those in `docs/STATISTICS_CONVENTIONS.md`.

After setting `LILY_WIKI_ROOT`:

1. resolve each recorded relative source under that root;
2. calculate SHA-256 on the source bytes;
3. compare it with the hash recorded in the Lily artifact;
4. stop reproduction if a source is missing or differs, then record the new source snapshot explicitly instead of silently accepting it.

The B0.5 rehearsal verified all six statistics-convention source hashes. The absolute Wiki location was intentionally not recorded.

## External Data Restore

No local or purchased Lily dataset exists at B0.5, so external-data restoration is explicitly `pending_no_data`, not “tested.” B1 must define the data registry, raw/normalized/derived boundaries, survivorship and futures-roll controls, and the exact backup destination before acquisition.

Once data exists:

- back up irreplaceable raw containers separately from Git;
- record dataset identity, provider provenance, time coverage, schema version, and hashes in the versioned data registry;
- use dual hashes for hard-to-reproduce data and documented container hashes for freely re-downloadable daily data;
- restore the registry first, then restore or re-download the named containers, verify hashes, and rebuild derived data;
- rehearse one real data restore before claiming the data backup works.

## Rehearsal And Failure Handling

`reports/restore_rehearsal.json` is the machine-readable B0.5 record. Repeat a committed-artifact rehearsal after material changes to the bootstrap, dependency pin, or restore procedure. Repeat a data rehearsal after the first external dataset and after any backup-layout change.

If any commit, test, tracker, source hash, or data hash differs, stop and classify the mismatch. Do not repair the restored copy in place and call it reproduction; either restore the recorded inputs or create a new, explicitly versioned result.

## Source Lineage And Lily Changes

This procedure adapts Higanbana `docs/HIGANBANA_TECHNICAL_DUE_DILIGENCE.md` and `AGENTS.md` requirements for self-verification, commit-addressed reproduction, external state, and restore rehearsal. Lily applies them before data acquisition. It excludes Higanbana's 0DTE datasets, Databento state, credentials, and cost ledger; Lily will define its own data backup only after B1 establishes its data boundaries.
