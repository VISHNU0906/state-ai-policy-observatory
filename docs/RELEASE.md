# Release verification

Research cutoff: 10 November 2026. Public release verified on the same date.

## Persistent data system release

The [durable hosted verification](https://github.com/VISHNU0906/state-ai-policy-observatory/actions/runs/42860077094) succeeded after restoring and resuming an intentionally interrupted run. The first attempt was cancelled to replace repeated 12 MB whole-file snapshots with 64 KiB content-addressed blocks. Before interruption, 188 new observations and eight request reservations were already durable; 17 queries remained unfinished. The replacement workflow resumed those queries, then completed a fresh window. The recovered database passed integrity, foreign-key and semantic checks locally.

Both complete collection passes retained 358 provider observations across 328 distinct document URLs. In each pass, RSS, Tavily and Exa completed 12 state queries each. GDELT returned HTTP 429 and the remaining 11 planned states were explicitly marked skipped. Each pass is therefore marked partial in the ledger even though the workflow succeeded. Thirty-four of 36 successful queries reached their requested limit. These runs establish recovery and retention, not exhaustive coverage. `runs/durable-system-verification.json` records the underlying run IDs and per-provider outcomes.

The restored ledger contains 2,136 document URLs and 3,751 retained observations. The latest companion-tracker snapshot has 543 unverified proposals across 13 states. There are 1,093 proposal versions across two imported snapshots; those are not 1,093 distinct events. The publication corpus remains 85 reviewed events across 12 states, with 113 sources and 137 evidence associations. No new discovery was silently approved.

The local suite now has 46 passing Python tests plus a JavaScript sorting check. The hosted recovery run used its then-current 39 Python tests. Checks cover transaction rollback, replay, conflict preservation, stale review revisions, reversible merges, archive corruption, interrupted collection, request reservations, block reuse, tracker versions, source-attribution consistency and stable date ordering. The new semantic export check refuses inconsistent event/source fields while retaining the previous valid export pointer. The updated architecture PDF was rendered and visually inspected.

The active workflow uses the approved public [data-history branch](https://github.com/VISHNU0906/state-ai-policy-observatory/tree/data-history), rather than expiring artifacts or Actions cache, for history and request reservations. It runs daily at 07:47 IST with a 30-minute timeout. Candidate data is public, clearly unverified, and excludes credentials and full extracted article text. Collection failure does not replace the reviewed dashboard. The local source bundle contains the complete main-branch development history; candidate history remains separately available from GitHub and the bundled database checkpoint.

- [Live dashboard](https://vishnu0906.github.io/state-ai-policy-observatory/)
- [Public repository and commit history](https://github.com/VISHNU0906/state-ai-policy-observatory)
- [First successful Pages publication](https://github.com/VISHNU0906/state-ai-policy-observatory/actions/runs/42844745699)
- [First successful hosted collection](https://github.com/VISHNU0906/state-ai-policy-observatory/actions/runs/42844796557)

## Delivered snapshot

85 reviewed milestones, 113 unique source URLs, 137 event-source associations, 12 states. Every state has six to eight records. Four event dates remain unknown and three are month-only. The primary-source attachment indicator is true for 59 records; it does not imply primary verification of every claim.

The 137 associations are not 137 independent articles. Some documents support multiple actions, and additional sources may support only part of a claim. The 52 source associations beyond the first source per event are not advertised as 52 duplicate articles removed.

## Checks completed

- Browser loaded the public GitHub Pages URL and displayed 85 milestones, 113 documents and 12 states.
- Search, reset, source expansion, unknown-date filtering and empty-state behaviour worked in the browser.
- Filtered CSV download returned exactly four rows with empty event dates.
- Consecutive unchanged builds produced identical CSV, JSON and browser-payload hashes.
- Core regression tests passed locally; the first hosted build also passed its then-current nine tests. A tenth local test verifies monthly request-budget enforcement.
- One-page rationale, four-page research report and seven-page collection assessment were rendered and visually inspected.
- Tracked files were checked against available secret values; none appeared. Commit messages contain no co-author trailers.

## Hosted collection result

The first run completed 12 state queries each for RSS, Tavily and Exa. GDELT returned HTTP 429 and stopped after bounded retries; other providers continued. Output: 357 provider observations and 320 unique URL candidates, all pending review. The run verifies redundancy, not relevance or completeness of those candidates. A compact result is in `runs/hosted-collection-verification.json`.

The original workflow ran at 07:47 IST daily on a GitHub-hosted runner. Tavily and Exa secrets were installed with explicit approval. No paid subscription or automatic top-up was activated. Request caps do not control other usage or provider-side billing. Its candidate artifacts expire after 30 days. The persistent release described above replaces cache-dependent history with the data-history branch.

## Local submission

The release builder creates a single local submission folder and ZIP containing the CSV/JSON data, PDFs, documentation, offline dashboard, source ZIP, Git history bundle and SHA-256 manifest. No Drive upload was performed, as requested. Full source article caches and credentials are excluded.

## Submission document and dataset package

The six-page technical submission and four reproducible PNG/SVG figures were generated from the reviewed data and saved run results. All six PDF pages were rendered and inspected. The new normalization helper has six test methods covering explicit aliases, curated typos, ambiguity, invalid and partial dates, timezone boundaries and relative anchors. It is a review-time tool, not an automatic rewrite of the research corpus. The Hugging Face folder has 85 events, 113 source metadata rows and 137 associations, with a dataset card and hashes. Source excerpts are omitted from that upload package.

The native Google Doc was created in the requested account, saved to Drive and read back: all six section titles and all authored paragraphs are present. The downloaded document has eight pages and four embedded figures. The local Technical_Submission.pdf is a separately typeset six-page version. The companion tracker selected files were rechecked and remained byte-identical to the last frozen import.
