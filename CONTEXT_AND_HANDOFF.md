# Current project context and handoff

Updated 10 November 2026. Working directory: `E:/kosuri/state-ai-policy-observatory`. This file describes the current implementation, not the older dump or the companion tracker's claims.

## User decisions and scope

Build a research-backed pipeline for AI-related Indian state government activity, with a clean dataset, live webpage, meaningful Git history, runnable code archive, README and one-page rationale. Cover 10 to 15 states well rather than assert nationwide completeness. The reviewed window is 1 January 2024 through 10 November 2026. Data aggregation, sorting, deduplication and evidence consistency take priority over UI polish.

The user chose local submission assets, a public GitHub repository and dashboard, free scheduled hosting where practical, and free collection plus optional keyed providers. Tavily and Exa were explicitly authorized as encrypted GitHub Actions secrets. Public candidate history and workflow write access were separately approved after automatic approval review requested that specific permission. No Drive upload, custom-domain change, new subscription or automatic top-up was performed. No AI co-author trailers are used. Keep prose direct, with no em dashes or unsupported quality claims.

## Locations

- Live dashboard: https://vishnu0906.github.io/state-ai-policy-observatory/
- Source: https://github.com/VISHNU0906/state-ai-policy-observatory
- Durable candidate history: the separate `data-history` branch in that repository.
- Working database: `state/observatory.sqlite`.
- Latest export: read the directory name in `ledger-exports/CURRENT`.
- Local checkpoint: `output/Data_System_Checkpoint_2026-11-10.zip`.
- Complete submission: `release/State_AI_Policy_Submission_2026-11-10.zip` after running the release builder.
- Companion tracker: `E:/vishnu/state-ai-policy-tracker`, read-only from this project.

## Current data

The publication corpus remains 85 reviewed events across 12 states, 113 source documents and 137 evidence associations. Four event dates are unknown and three are month-only. Fifty-nine events have a primary source attached, which does not prove every associated claim or date. No financial totals are summed across announcements.

After hosted recovery, the ledger contains 2,136 document URLs and 3,751 observations. The latest imported tracker snapshot has 543 unverified proposals across 13 states, including Bihar. Two retained snapshots contain 1,093 proposal versions, not that many distinct events. Original external classifications and earliest-report dates are preserved as proposals. An imported confidence score or review label never confers approval here.

Read `data/tracker_integration_audit.json` and `docs/TRACKER_INTEGRATION_FINDINGS.md`. The handoff's 787-record figure was outdated when inspected. The inspected reversal regex contained literal backspace bytes; 31 headlines overlapped across its even/odd evaluation halves; and most article-level links still used Google News despite representative URLs pointing to publishers. These findings were checked against saved code and data, not accepted from either agent's narrative. No companion files were modified. Recheck its files at integration checkpoints with `python sync_tracker.py E:/vishnu/state-ai-policy-tracker`.

## Implemented system

`ledger.py` stores imports, query history, stable document URLs, immutable observations, versioned external proposals, reviewed events, source links, retrieval metadata, match decisions and append-only review actions. Imports are atomic and repeat-safe. Review revisions prevent stale edits. Manual event merges retain IDs and evidence and can be restored if there are no intervening edits. Approval derives source attribution from evidence; exports reject inconsistent counts or associations.

`collect_durable.py` saves query plans before requests, commits each completed query, preserves every provider observation, reports skipped states and capped results, and resumes interrupted work. Request attempts are reserved transactionally before keyed calls. A local 720-attempt monthly default is not an account-wide billing guarantee. Optional interval splitting is bounded; full provider pagination is not implemented.

`history_store.py` takes consistent SQLite backups and stores compressed 64 KiB blocks by content hash. Unchanged blocks are reused. A manifest verifies the reconstructed database. Missing history, corrupt blocks, concurrent remote updates and unpublished local edits fail visibly rather than resetting state. `refresh` preserves a backup and refuses to replace local changes. History publication stops above a 250 MB working database pending a storage migration.

`extract_ledger.py` performs robots-aware local extraction, records failures and retains private text by content hash. Changed content is flagged for review. Full source text remains excluded from Git and release archives. `matching.py` creates document-pair suggestions, never automatic event merges. The headline baseline has weak diagnostic performance: 3 of 12 positive pairs retrieved and 6 distinct pairs suggested at threshold 0.45. Its 34 labels are a development fixture from research agents, pending independent human review.

`date_rules.py` preserves day, month, year and unknown precision. Default ordering uses descending interval lower bound, narrower precision on ties, state and ID, with unknown dates last. The dashboard and CSV build use the same convention. A partial date is never displayed as an invented exact day.

## Verified recovery

Hosted run 42858624366 was deliberately cancelled to replace repeated whole-file snapshots. The remote snapshot retained 188 new observations and eight reservations with 17 unfinished queries. Run 42860077094 restored the block archive, recovered those queries, then completed a fresh window. Each collection pass retained 358 observations across 328 distinct document URLs. RSS, Tavily and Exa each completed 12 queries. GDELT returned HTTP 429 and 11 remaining states were explicitly skipped, so the ledger correctly labels each pass partial even though the workflow succeeded. Thirty-four successful queries per pass hit the requested result limit.

The final remote snapshot restored locally with no unfinished queries, corruption, broken foreign keys or semantic source failures. See `runs/durable-system-verification.json`. Forty local Python tests and the JavaScript ordering check pass. The hosted recovery run used its then-current 39 tests. The source deployment runs the current suite before Pages publication.

## Commands and next work

Read `docs/LEDGER_OPERATIONS.md` for full commands, review transitions and limits. On an existing installation, do not initialize an empty replacement database. Refresh from history first if local state is unchanged. If it has unpublished edits, restore a separate database and reconcile deliberately. Keep only one collection writer active.

The live dashboard still builds from reviewed `research/*.json`; ledger approval does not silently change that publication input. A reviewed release must deliberately transfer accepted evidence. Open work includes regional-language coverage, systematic official-document backfills, verified Google redirect mappings, full pagination, independent relevance labels, claim-level matching evaluation, atomic multi-event splits and automatic reviewed-release synchronization. These are explicit limits, not hidden stubs presented as completed features.

The old dump and old submission outside this project remain historical snapshots. Current deliverables are built inside this working directory. `build_ledger_bundle.py` creates the local database/data/code checkpoint. `build_release.py` packages source, complete main-branch development history, reports, datasets, the offline dashboard and that checkpoint into one submission ZIP.
