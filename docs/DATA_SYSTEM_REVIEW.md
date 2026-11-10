# Data system review and implementation requirements

Status: design review, not implemented. Reviewed 10 November 2026 against `pipeline.py`, `collectors.py`, `extract_documents.py`, tests, sample runs and the scheduled workflow. Preserve the existing 85 reviewed events and 113 sources. The changes below concern durable collection and review, not automatic publication.

## Deficiencies to fix first

1. Collection deduplicates URLs only within the current run. There is no durable import ledger or queue spanning daily runs. Repeated discoveries receive a fresh pending status instead of preserving review decisions.
2. Cross-provider grouping keeps the first row's metadata and only lists the other providers. Conflicting dates, titles and publisher claims disappear. Preserve each observation before grouping.
3. Scheduled files are ignored by Git and retained as Actions artifacts for 30 days. This is temporary delivery, not a historical database. Provider usage cache can also disappear.
4. `deduplicate()` groups preassigned event IDs. It does not determine whether two reports describe the same event. Current tests establish grouping behavior, not matching quality. The existing title-similarity queue compares reviewed events only, not incoming articles against reviewed events.
5. The reviewer must manually edit research JSON. There is no explicit transition history, evidence revision reference or reversible merge decision.
6. Run IDs have second precision and may collide. Logs are written only at run end. An interrupted process can lose all completed query results. The collector may stop after one provider error without logging every unattempted state as skipped.
7. Source text is overwritten at a URL-derived cache path. A later changed page cannot be distinguished from the evidence version used to approve a claim. Extraction is currently aimed at existing reviewed sources rather than the pending discovery queue.
8. Event dates are validated, but source publication dates and their provenance are not consistently validated. Raw partial dates sort lexically; a month is placed relative to days without explaining the convention. Output file replacement is not transactional across the release.

## Minimal SQLite model

Keep the original research files as versioned seed inputs. SQLite becomes the working record for discovery, review and history. Generated CSV and JSON remain exports. Use stable IDs, foreign keys and explicit transactions. Enable foreign keys on every connection; SQLite does not enable them by default. [SQLite foreign keys](https://www.sqlite.org/foreignkeys.html).

| Table | Minimum fields and constraints |
|---|---|
| `runs` | `run_id` UUID primary key; started/finished UTC; status running/complete/partial/failed/interrupted; schema and code version; parameters; input digest unique when importing an existing run file. |
| `queries` | `query_id`; run foreign key; provider; actual submitted query; state; window start and exclusive end; status; attempt count; returned count; capped flag; error code. Unique run/provider/state/query/window identity. Record planned but unattempted queries too. |
| `documents` | Stable `document_id`; conservative canonical URL unique; original URL; URL kind; first/last seen; current review state. Preserve seeded source IDs. A document can support several events. |
| `observations` | `observation_id`; query and document foreign keys; raw title, publisher, timestamp, snippet and provider metadata; observation UTC. Unique query/document/provider-result identity prevents replay duplication. Conflicting provider values remain separate rows. |
| `retrievals` | Retrieval ID; document; attempt UTC; status; final URL; content hash; extraction hash; extractor/version; publication and update candidates with their raw text/time zone; evidence reference. Append attempts, including failures. Store retained text by content hash in private storage, never overwrite by URL. |
| `events` | Existing event ID; reviewed fields; event date/precision/basis; initiative; stage/category; review state; revision; optional superseded-by ID. No event identity derived only from title, date or URL. |
| `event_sources` | Event/document pair; supporting retrieval ID or explicit legacy evidence reference; roles such as action/date/context; reviewer; decision time. Composite unique event/document. A contextual attachment is not date verification. |
| `review_actions` | Append-only action ID; entity type/ID; previous and new revision/state; reviewer; UTC; reason; before/after payload. Merge and split actions preserve old IDs and all source links. |
| `match_reviews` | Ordered pair of candidate/event identities; rule version; features and score; decision pending/same_event/distinct/uncertain; reason and reviewer. Unique pair/rule version; prior distinct decisions must not silently reappear as merge recommendations. |
| `provider_attempts` | Attempt ID; query; provider; month; reservation UTC; outcome. Reserve within a transaction before calling the provider. Failed and interrupted attempts count toward the local cap. |

A separate alias table can be added when two URLs are verified as the same document. Do not force that identity merely because pages have similar titles or equal bodies. Keep redirects and canonical-link claims as evidence until resolved. Query parameters such as document IDs must survive URL normalization. Do not lowercase paths or remove arbitrary parameters. Scheme and trailing-slash variants are not automatically identical.

## Ingestion and recovery invariants

- Bootstrap the six research files transactionally. Reimporting their identical digest changes no counts or decisions. A modified seed must produce an explicit revision or conflict, not overwrite reviewed work silently. Original research evidence remains labelled as manually reviewed; do not invent retrieval snapshots for the 113 sources.
- Validate a run before importing it. One run-file import is atomic. Replay of the same file is a no-op; a new day's observation of the same URL adds observation history while preserving one document and its review state.
- Persist query outcomes and observations together after each query. Network calls occur outside long database transactions. A crash leaves completed queries committed and the current query interrupted. Resume retries only unfinished queries, using the same logical identities.
- A successful empty response, a failed query, a missing credential, a cap stop and an unattempted query are different outcomes. A top-N response at the limit is potentially truncated, not complete coverage. Save actual provider-specific query text and requested window, rather than a generic label.
- Do not advance a provider/state coverage checkpoint after failure. Use overlapping windows and persistent URL identity when recovering. A collection gap longer than the rolling window must be reported and backfilled explicitly; daily execution alone does not repair it.
- Serialize writers and use bounded busy retries. SQLite permits only one simultaneous writer. Commit the review decision, event revision and evidence links together. [SQLite transactions](https://www.sqlite.org/lang_transaction.html).
- Keep durable history outside runner cache and expiring artifacts. For this small repository, a dedicated data-history branch holding compact run records and a validated database snapshot is a feasible starting point. Commit no keys or full licensed article text. Persist at least after each provider and at run end, recording the last durable checkpoint. A hosted runner lost before its checkpoint still has a disclosed recovery gap.
- Never silently recreate an empty database or reset a usage ledger when durable state is unavailable. Fail the stateful operation visibly and preserve the last valid snapshot. Obtain consistent database backups through SQLite's backup mechanism, not an uncontrolled copy of a live file. Test restoration. [SQLite backup API](https://www.sqlite.org/backup.html).
- Build exports into a temporary release directory from one database snapshot. Validate counts and references, then publish the completed directory and manifest together. A failed build must leave the prior release usable.

## Date and sorting rules

Keep `discovered_at`, provider `seen_at`, publication, update, retrieval and event dates separate. A provider timestamp never fills `event_date`. Preserve raw timestamps and offsets. Day-only metadata with conflicting time zones stays uncertain. Visible “updated” dates must not become original publication dates, as demonstrated by `up-google-ht`.

An event date requires an explicit evidence basis and precision. An unknown date remains null even when publication is known. A month or year remains partial ISO in exported data. Derive lower/upper bounds only for sorting and filtering, never display the lower bound as an exact date. A partial interval crossing the release cutoff needs explicit review; normalizing it to the first day must not imply the entire interval is within scope. A future event reported in advance is not a completed signing or launch. Publication before a claimed completed action is a review warning, not automatic correction.

Recommended deterministic ordering: known dates first; descending event interval lower bound; narrower precision before broader precision on an equal lower bound; state ascending; event ID ascending. Unknown dates last, state then ID. Document that intervals overlap and this order is a display convention, not exact chronology. The same ordering must govern SQL exports, CSV and dashboard. Publication-based sorting should be a separate explicit option.

## Review and false-merge safeguards

Discovery creates a pending document, never an approved event. Retrieval success can move it to evidence-ready, but text length is not evidence quality. Review creates or links one or more event drafts, or rejects the document with a reason. Approval requires canonical state, category, stage, date basis, source evidence and reviewer identity. Repeated ingestion cannot undo approval or rejection. Changed source content opens a review task while retaining the last reviewed version; it must not rewrite facts automatically.

Use URL identity only for documents. Use a shared event identity only after evidence establishes the same government action, parties, scope and milestone. Same initiative, same date, same ceremony or high title similarity is insufficient. Keep the Odisha tripartite data-centre and bilateral technology-centre agreements separate; keep Uttar Pradesh mission announcement, budget provision and approval separate. Keep Gujarat's IBM and Microsoft agreements separate despite their shared city and date. A report discussing several actions may attach to several events.

Candidate matching should produce suggestions with visible reasons, never a similarity-based automatic merge. Different stages or counterparties are strong reasons to keep records separate, unless review establishes a reporting error. Preserve corrections through reversible supersession rather than deleting event IDs. Source-link counts are not duplicate-removal counts or independent-witness counts.

## Acceptance criteria before calling the system robust

1. Import the existing seed and run files twice: exactly 85 events and 113 seeded sources remain; second identical imports add no observations or review actions. New-day observations preserve earlier reviews.
2. Two providers finding one URL retain both original metadata records. One article supporting two distinct actions creates two event links, not a forced event merge.
3. Crash after a completed query, then resume: completed observations remain, unfinished work is visible, no duplicate rows arise. A malformed import rolls back entirely. A failed provider does not discard another provider's results.
4. Simulate 40 daily runs, a missing day and a gap beyond seven days. All history survives; the gap is reported; archive restore reproduces review state, counts and hashes. An expired Actions artifact must not erase the only copy.
5. Verify unknown, day, month and year dates; invalid calendar dates; publication/update conflicts; provider-seen timestamps; UTC/IST midnight boundaries; cutoff-crossing intervals. Shuffle input files and rows: exports remain identically ordered.
6. Create a reviewed matching fixture containing genuine repeated reports and difficult distinct milestones. Include the Odisha, Gujarat and UP cases above, same company in different states, copied headlines, corrected articles and one article with several events. Report labelled-pair count, suggestion recall and the number of false merge decisions. Zero automatic merges is a policy, not proof of matching accuracy. Do not use contextual source attachments as positive duplicate labels.
7. Exercise accept, reject, attach to existing event, create new event, split, merge and reopen transitions. Every change records reason and reviewer; repeated collection cannot reset it. Only approved events appear in exports.
8. Source URL failure after approval does not delete historical evidence. A changed document produces a new version and review task. Restore a backup and verify no broken foreign keys, missing reviewed links or lost decisions.

Implement durable ingestion, review transitions and acceptance tests before expanding UI or claiming automated deduplication quality. The current curated release remains valid as a reviewed snapshot; these requirements describe the missing continuous data system.
