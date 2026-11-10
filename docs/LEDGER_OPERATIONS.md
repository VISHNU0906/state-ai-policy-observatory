# Durable collection and evidence ledger

Implemented on 10 November 2026. The user explicitly approved public candidate history and workflow repository write access. The replacement collector is enabled in `.github/workflows/collect.yml`; `proposals/durable-collection.yml` preserves the original reviewable proposal. Verified hosted outcomes and remaining limitations are recorded in `docs/RELEASE.md`.

## Data boundaries

There are three distinct units:

1. A document is an exact conservatively normalized URL. Tracking parameters and fragments are removed. HTTP/HTTPS, path case, trailing slashes and substantive query parameters remain distinct. A publisher destination reported by another pipeline is recorded as an unverified relationship, not silently substituted.
2. An observation is what a provider or imported snapshot said about that document at a particular query/import. Titles, date candidates and publisher claims can conflict. Observation rows are immutable. Repeated import of identical bytes is a no-op. Another run or changed snapshot adds provenance without resetting review decisions.
3. An event is a reviewed government action. A document may support multiple events. A signing, approval, launch and cancellation are different milestones unless explicit evidence and a recorded review establish otherwise. Discovery and similarity do not create approved events.

The reviewed seed remains 85 events, 113 source records and 137 evidence associations. Its review provenance is labelled legacy research. Importing it does not invent retrieval snapshots or independent verification. External tracker classifications and dates remain proposals even if that tracker labels a row reviewed. Its date is an earliest report date, not a formal event date.

## Local operation

Run from the project directory with Python 3.11 or later. The ledger, collection, matching and export paths use the standard library. Local page extraction additionally uses `requirements-extraction.txt`.

```powershell
python -m unittest discover -s tests -v
# First installation only. A missing database otherwise fails closed.
python ledger.py init
python ledger.py seed data/events.json
python ledger.py import-run path/to/saved-run.json
python sync_tracker.py E:/vishnu/state-ai-policy-tracker
python collect_durable.py --providers google-rss,gdelt --states 'Kerala,Tamil Nadu' --days 7 --limit 10 --max-calls 2
python matching.py queue
python matching.py evaluate
python extract_ledger.py --limit 3
python ledger.py audit
python ledger.py export ledger-exports
python ledger.py backup state/backup.sqlite
```

`state/observatory.sqlite` is the working database. `ledger-exports/CURRENT` names the last complete export directory. Every export is a new directory, with SHA-256 checksums and a quality report; the pointer changes only after all files are written. An interrupted export may leave an incomplete unreferenced directory, but the previous pointer remains valid. Do not edit generated exports to make a review decision.

Key export files:

| File | Meaning |
|---|---|
| reviewed_events.csv | Only approved events, ordered consistently with the research build |
| candidate_observations.csv | Flat discovery rows with raw and normalized publication candidates, state hints and provenance; event dates remain empty |
| latest_external_proposals.csv | Latest tracker snapshot only; dates and categories are proposals |
| proposals.csv | All imported proposal versions, not a count of distinct events |
| documents.csv, document_links.csv | Stable URL identities and unverified reported redirects |
| sources.csv, event_sources.csv | Reviewed source records and event associations |
| queries.csv, runs.csv | Attempted, successful, failed, capped and skipped query history |
| review_actions.csv, matches.csv | Explicit decisions, reasons, reviewers and revisions |
| retrievals.csv | Successful and failed retrieval attempts, content hashes and metadata candidates |
| external_rejections.csv | Other pipeline's rejected rows and reasons, not our own final decisions |
| collection_health.json | Completed request windows, gaps between them, capped counts and failures |

## Queries, retries and cost

The collector saves the entire plan before requests. Each completed query and its observations commit in one SQLite transaction. A process interruption leaves its current query running. `--resume RUN_ID` retries unfinished queries in that run. `--resume-unfinished` recovers interrupted runs before planning the new window. Completed queries do not run again. Failed and skipped queries remain explicit gaps; they are not silently labelled complete.

Every keyed API attempt, including retries, reserves a request transactionally before the call. The local default is 720 attempts per provider per UTC month, configurable with `PROVIDER_MONTHLY_REQUEST_CAP`. Import historical usage with `ledger.py import-usage`. The legacy migration assumes snapshots of one cumulative legacy ledger; separate independent accounts or machines require explicit accounting. The ledger is a local request cap, not an account-wide billing limit. Provider prices, credit multipliers, extraction costs and activity outside this repository are separate.

`--split-saturated` divides a capped multi-day window into smaller windows subject to the same per-provider query budget. Subqueries that cannot run are recorded as skipped. Reaching the requested result limit is a warning, not proof that more results exist. A response below the limit is not proof of exhaustive coverage either. Interval splitting cannot recover everything omitted by a search index or a top-N search endpoint. Full pagination is not implemented.

Default windows end at the current UTC day's start. To use a delayed NewsAPI or GNews plan, set `--end` explicitly to an allowed older date. Provider endpoint boundaries can differ. Repeated daily windows overlap, and document identities remove exact URL duplicates. Google RSS remains unofficial; GDELT historical limits and rate limits still apply. Missing keys and rate limits produce explicit outcomes for every planned state.

## Review and corrections

All review commands require a reviewer, a reason and the expected current revision. Stale revisions fail rather than replacing another person's decision.

```powershell
python ledger.py review-document DOCUMENT_ID rejected --reviewer 'Reviewer name' --reason 'No state government action in the article' --revision 0
python ledger.py register-source reviewed-source.json --reviewer 'Reviewer name' --reason 'Original page read; supporting claim recorded'
python ledger.py approve-event reviewed-event.json --reviewer 'Reviewer name' --reason 'Action, date and parties checked against attached sources' --revision 0
python matching.py decide --match-id MATCH_ID --decision distinct --reviewer 'Reviewer name' --reason 'Different agreement and counterparty' --revision 0
python ledger.py merge-events SOURCE_EVENT TARGET_EVENT --source-revision 1 --target-revision 1 --reviewer 'Reviewer name' --reason 'Both records describe the same signed instrument'
python ledger.py restore-merge ACTION_ID --reviewer 'Reviewer name' --reason 'Evidence establishes separate milestones'
```

A reviewed same-event pair does not itself merge events. The explicit merge command retains both IDs, supersedes the source event, unions evidence into the target and records before/after state. Restoration checks that neither event changed meanwhile, restores the evidence links and increments revisions. Cross-state or cross-stage merges are refused; correct an erroneous field with evidence first. A single-command split operation is not implemented. Creating and revising events is supported, but a multi-event split needs a separately reviewed transaction before claiming atomic split support.

Approval in the ledger does not update the live dashboard automatically. The existing research JSON remains the publication input until a deliberate reviewed release incorporates the change. This avoids an unexpected change in the published corpus during migration. The separate ledger export includes approved ledger events.

## Dates and evidence versions

Event dates, publication candidates, provider-seen timestamps, import times and retrieval times remain separate. Offset-aware timestamps normalize to UTC while retaining the raw value. Offset-free timestamps remain uncertain. GDELT seen dates and Crustdata response timestamps are not publication dates. Extractor dates may be update dates or guesses; they never replace event dates automatically.

Partial event dates stay `YYYY-MM` or `YYYY`. Sorting uses the interval's lower bound descending, narrower precision first when lower bounds tie, then state and event ID ascending. Unknown dates sort last. Intervals may overlap, so this is a display convention, not an exact chronology. The upper bound is available for range checks; a partial interval crossing a research cutoff still requires a review judgement.

`extract_ledger.py` checks robots rules before local retrieval. It records every attempt, including failures, and stores extracted text privately by its SHA-256 hash. A changed page retains the older text and sets a change flag. The public ledger holds hashes and metadata, not article bodies. The private text cache is excluded from Git and release archives. Changed evidence creates a flag for review, not automatic fact revision. Hosted extraction in this ledger CLI is currently disabled until it has query-scoped budget reservations.

## Durable hosting

`history_store.py` uses SQLite's backup API, validates integrity and foreign keys, and divides a consistent snapshot into 64 KiB blocks. Each block is compressed separately and identified by its uncompressed SHA-256. Unchanged blocks reuse their existing Git objects. The ordered manifest retains a whole-database checksum. Restore checks every block and the reconstructed database, then runs integrity and foreign-key checks. This follows the [SQLite backup documentation](https://www.sqlite.org/backup.html), enables [foreign key checks](https://www.sqlite.org/foreignkeys.html), and uses [Git batch object reads](https://git-scm.com/docs/git-cat-file) to avoid starting a process for every restored block.

The workflow publishes a snapshot before each keyed request reservation is used and after each query. It uses a separate `data-history` branch without switching the source checkout. A missing history branch, network failure, checksum mismatch, unexpected remote revision or concurrent push stops stateful collection. It never force-pushes and never silently resets the request ledger. The main branch and reviewed dashboard are separate from the data branch. Shallow fetching retrieves the current data snapshot without downloading every prior version. Historical snapshots remain available from GitHub.

A paid call may finish just before a runner disappears. Its reservation survives, but its response may need fetching again. A hard cancellation can interrupt the current checkpoint. GitHub schedules are best-effort and do not promise a specific start time. Archive publication stops above a 250 MB working database; move to object storage before approaching that bound or if Git history growth becomes excessive. Block reuse reduces repeated transfer but does not make history growth free or unbounded. Restores require Git and the repository remote.

To adopt hosted updates locally, run `python history_store.py refresh`. It first saves a local backup and compares local state to the last published/restored baseline. Unpublished local changes cause refusal, not replacement. Reconcile those changes in a separately restored database. `python history_store.py restore --db state/fresh.sqlite` always requires a new destination. Keep one collection writer active at a time.

## What is not established

No nationwide completeness, independent-source count, automatic event extraction accuracy or production deduplication accuracy is claimed. The diagnostic matcher currently has weak recall and precision on a small development set. Regional-language coverage, historical official-document crawling, Google redirect verification, full provider pagination, independent review of the external labels, atomic event splitting and automatic propagation from the ledger to the published research release remain open work.
