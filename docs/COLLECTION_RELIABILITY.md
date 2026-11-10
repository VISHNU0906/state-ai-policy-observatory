# Collection reliability and evidence retention

Inspection date: 10 November 2026. Baseline inspected: `collectors.py`, `pipeline.py`, `.github/workflows/collect.yml`, `tests/test_pipeline.py`, six reviewed research files and saved runs, with repository HEAD `22cad34`. This is an implementation brief. It describes the inspected version; subsequent code changes may close the issues below.

## What the recorded runs establish

The saved hosted verification reports 357 provider observations and 320 unique URLs. Google RSS, Tavily and Exa each completed 12 state queries. Of these 36 successful queries, 33 returned exactly the requested limit of ten. This does not prove that additional results exist, but it means the collector cannot claim that those queries exhausted accessible results. GDELT returned HTTP 429 on the first state; the remaining 11 states have no individual status records. See `runs/hosted-collection-verification.json` and its linked workflow run.

The earlier two-state run returned 14 URL candidates across RSS and GDELT, demonstrating that GDELT sometimes worked. The later rate limit shows why a provider's earlier success cannot justify treating every later query as covered. Neither run measures relevance, source accuracy or total policy activity.

The 85 reviewed events in six research files are a curated evidence corpus. The scheduled candidates have not reproduced that corpus automatically. Preserve this distinction in reports and tests.

## Highest-priority weaknesses

| Inspected behavior | Consequence | Smallest useful correction |
|---|---|---|
| One request per state/provider, fixed result limit | A successful response can conceal truncated discovery | Record saturation and provider totals; paginate where supported and split time windows within a budget |
| Provider stops after an error; later state rows absent | Missing work is indistinguishable from unplanned work | Create the entire query manifest before making requests; every planned cell receives a terminal status |
| URL merge retains the first observation plus provider/state lists | Later titles, dates, snippets and exact queries disappear | Keep an observation table; group it under a candidate without discarding fields |
| Exa sends a different query from the query saved in each candidate | The run cannot be reproduced from its log | Construct one request specification and save its sanitized form before sending |
| Crustdata result `source` is saved as publisher | The value `news` or `web` can masquerade as an outlet | Store it as `source_channel`; derive publisher only from verified metadata or domain |
| One broad English query per state | Misses local-language notices and sector-specific terminology | Version query packs and official-source lists; state missing language coverage explicitly |
| Monthly usage exists only in an Actions cache | Cache loss or failed job can reset the apparent budget | Use a durable ledger with reservations before requests; treat cache as an optimization |
| Retry delays are one and two seconds; Retry-After is ignored | Repeated requests may worsen a rate limit | Honor Retry-After, impose provider cooldown and leave unfinished work queued |
| Artifacts expire after 30 days | Evidence of collection disappears without manual download | Commit compact metadata to an archive branch and retain checksummed periodic exports |
| No collector-focused tests | Publication tests do not catch paging, partial runs or lost provenance | Add the acceptance cases below with mocked HTTP and a temporary archive |

## A manifest makes gaps visible

Create the planned work before execution. Each cell needs `query_id`, state, language, provider, query family, exact query, requested time window, effective provider window, page/result size, provider mode, configuration version and priority. Include a stable query hash plus a unique run ID. Persist `planned`, then one of `completed`, `partial`, `failed`, `skipped_missing_key`, `skipped_budget`, `skipped_plan`, `skipped_cooldown` or `not_started_interrupted`.

For each cell, save attempt count, response count, unique URL count, provider-reported total when supplied, saturation flag, pagination or subdivision continuation, sanitized error, elapsed time and estimated/actual usage. `completed` means the chosen retrieval procedure finished, not that the whole web was covered. Add `coverage_limit` when a provider returns ranked results without an exhaustion guarantee.

A run summary must show the planned denominator. For example: 48 state-provider cells planned, 36 successful, one failed and 11 skipped after a provider rate limit. The exact reasons belong in the manifest; do not call the latter 11 empty results.

Queue older unfinished cells before optional query expansion. Rotate equal-priority states deterministically between runs, so alphabetical ordering does not repeatedly favor Andhra Pradesh when a shared quota runs out. Persist the rotation or queue cursor.

## Time windows and pagination

Use UTC timestamps internally, while retaining the original timestamp and timezone. Model intended windows as `[start, end)` and record each provider's translation. Do not silently assume all endpoints share boundary rules. Overlap successive windows and deduplicate observations. A timestamp outside the intended window is a metadata exception, not a reason to invent an event date.

Replace the universal midnight cutoff with an explicit per-provider freshness policy. Real-time sources can search through the current run time; a delayed plan uses its known delay plus a safety margin. The existing common cutoff excludes at least the current UTC day and can delay real-time sources unnecessarily. A single conservative cutoff is acceptable for a comparison run if disclosed, but should not govern every monitoring source.

Persist a watermark for each query family/provider. Advance it only when the relevant retrieval procedure finishes without a known gap. Use a seven-day overlap for late indexing as a configurable starting assumption, plus a weekly wider reconciliation run. It is not a proven completeness guarantee. Keep historical research/backfill separate from incremental monitoring, and never ask a free plan for inaccessible 2024 history while reporting the empty response as no activity.

| Provider | Verified endpoint behavior | Retrieval rule |
|---|---|---|
| NewsAPI | `/v2/everything` supports `page`, `pageSize` up to 100 and `totalResults` | Keep the query/window fixed while paging. Stop on exhausted accessible results, an empty page, no new IDs, an error or the configured request cap. Record plan-imposed access limits. Split large windows when totals exceed what the plan can retrieve. |
| GNews | Search supports page numbers and plan-dependent `max`; pagination ends at 1,000 articles; `from` and `to` are inclusive | Translate the half-open boundary with an explicit precision policy or intentionally overlap. Inspect `totalArticles` and free-plan removal notices. Split windows before the 1,000 ceiling. A short page alone is not proof of exhaustion when plan filters removed records. |
| Tavily | `max_results` up to 20; the documented search schema has no page/cursor parameter | Mark full responses as potentially saturated. Subdivide dates or query families under a cap; do not invent pagination. Keep undated discovery separate from strict date-window monitoring. |
| Exa | Search exposes `numResults`, date/domain filters and search modes, but no documented page/cursor in the inspected schema | Subdivide time/domain/query families when capped. Log mode and requested result count. A small result set is not proof that no more relevant pages exist. |
| GDELT DOC | ArticleList supports `maxrecords` up to 250 in the official reference; no paging cursor is documented there | Increase the requested limit sensibly, then subdivide capped windows. Retain a minimum window and maximum split depth to prevent runaway requests. Recheck historical-window behavior with a live bounded test. |
| Google News RSS | The tested feed supplies a finite result list; no supported paging contract was established | Save the actual feed count before any local slice. Query smaller overlapping windows and distinct families, labeling coverage as bounded. Do not equate a local slice of ten with a ten-item feed. |

Sources: [NewsAPI Everything](https://newsapi.org/docs/endpoints/everything), [GNews Search](https://docs.gnews.io/endpoints/search-endpoint), [GNews response fields](https://docs.gnews.io/json-response), [Tavily Search](https://docs.tavily.com/documentation/api-reference/endpoint/search), [Exa Search](https://exa.ai/docs/reference/search), [GDELT DOC reference](https://blog.gdeltproject.org/gdelt-doc-2-0-api-debuts/).

GNews explicitly documents silent plan-window filtering: recent free-plan requests are moved back by 12 hours, and inaccessible historical records can be removed while the response remains successful. Preserve `information` and `articlesRemovedFromResponse`. The requested and effective windows must both be visible. [Article availability](https://docs.gnews.io/article-availability).

Tavily dates require special handling. Its current schema says publication metadata can represent publication or last update. Date filters retain undated results by default. Choose `filter_by_published_date:true` for a strict stream and a second, lower-frequency stream retaining undated sources. `max_age_hours` controls cached content age, not the event date; free-tier live-fetch requests can return HTTP 434 under capacity pressure. Do not turn such a failure into zero findings. [Tavily Search](https://docs.tavily.com/documentation/api-reference/endpoint/search).

For GNews language filters, use only the current documented values. Its inspected language list includes Hindi, Bengali, Malayalam, Marathi, Tamil and Telugu but does not list every language needed by the 12-state sample. Unsupported codes need a different provider or direct source monitoring, not an assumed translation layer. A provider's `country` normally describes publishing location, not the government jurisdiction involved. [GNews Search](https://docs.gnews.io/endpoints/search-endpoint).

### Bounded splitting algorithm

1. Execute a manifest cell with a known result/page cap.
2. If the API has paging, continue within its accessible range while pages add new article IDs or URLs.
3. If results remain capped, split the time interval at its midpoint, preserving a small boundary overlap. Enqueue both child intervals and retain the parent as partial.
4. Stop subdivision at the provider's supported minimum granularity, a configured split depth, or the run budget. Mark the unsatisfied interval `partial` with the continuation needed.
5. For undated results or a ranked index without exhaustion guarantees, use query/domain diversification and report the limit. Do not recursively split dates forever.

Repeated pages, unstable totals and article movement during a run are possible. Keep the window fixed, deduplicate within the run and schedule reconciliation; never rely solely on page count arithmetic.

## Keep observations, articles and events separate

Use three linked records rather than one merged row:

- **Observation:** one provider response item from one query and run. Preserve original URL, provider article ID, title, raw date, snippet, rank, exact query ID, retrieval time and provider fields. An observation ID can hash the run ID, query ID, page and provider item ID or original URL.
- **Article candidate:** a canonical publisher URL with all observation IDs, first/last seen, resolved URL, redirect evidence, content hash and extraction attempts. Repeated discoveries update this index without deleting earlier observations.
- **Reviewed event:** a state-government action or dated milestone, linked to supporting articles and a review decision. Announcement, approval, signing, launch and deployment remain distinct when independently evidenced.

Keep `original_url`, `canonical_url` and `resolved_url` separate. The current canonicalizer removes common tracking parameters and fragments, which is useful, but cannot identify all AMP/mobile aliases or syndicated copies. Merge URL aliases only with supporting canonical/redirect evidence. Identical content on different publishers can be marked as syndication without erasing source attribution. Similar titles should generate a review suggestion, not an automatic event merge.

Sorting should be stable and explicit: reviewed events by known event date and precision, with unknown dates grouped separately; candidate queues by review priority, source quality, discovery time and stable ID. Provider publication dates can help prioritize a queue, but must not overwrite verified event dates. Store date conflicts for review. Partial dates represent intervals, so do not silently sort a month-only date as a confirmed first day.

## Durable storage without a paid database

Keep small, append-only metadata files in a dedicated `collection-archive` branch of the public repository. Suggested layout:

```text
archive/YYYY/MM/DD/run-id/manifest.json
archive/YYYY/MM/DD/run-id/observations.jsonl
archive/YYYY/MM/DD/run-id/errors.jsonl
archive/YYYY/MM/DD/run-id/checksums.sha256
state/query-watermarks.json
state/provider-budget.json
state/pending-queries.json
```

Use compact JSONL for observations. Save metadata and short excerpts only; do not archive full third-party articles publicly. Monthly compressed metadata snapshots with a checksum can be attached to a release if repository growth becomes material. Keep the reviewed release dataset on the normal source branch. Configure workflow triggers so archive commits do not launch another collection loop.

A hosted job should fetch the latest archive state, validate it, reserve its request allowance, commit the reservation, execute requests, then append results and finalize state. It needs narrowly scoped `contents:write` for the archive job, with trusted schedule/manual triggers and a concurrency group shared by every archive writer. If the reservation cannot be pushed, do not spend API credits. If the final push fails, keep the reservation consumed and upload a recovery artifact. A later run imports the recovery data by run ID without duplicating observations.

This is durable versioned project metadata, not an unlimited backup service. Monitor archive growth; avoid repeatedly committing large full database snapshots. GitHub warns above 50 MiB/file, blocks files above 100 MiB and recommends small repositories. Release assets are the documented alternative for distributing larger files. [GitHub large-file guidance](https://docs.github.com/en/repositories/working-with-files/managing-large-files/about-large-files-on-github).

The present 30-day workflow artifact remains useful for recovery but is not permanent storage. GitHub artifacts expire, and caches can be evicted after seven days without access. The combined cache action normally saves a new cache only after a successful job. Therefore neither should be the sole archive or budget authority. [Artifact retention](https://docs.github.com/en/actions/how-tos/manage-workflow-runs/download-workflow-artifacts), [cache behavior and eviction](https://docs.github.com/en/actions/reference/dependency-caching-reference).

## Budgets and rate limits

Maintain both request and estimated-credit limits. A request is not a universal billing unit: provider modes, extraction features, number of returned results and account terms can change its cost. Record provider account identity only as a non-secret label, plan, allowance reset date, trial expiry and latest known credit balance. The local ledger cannot observe unrelated use of the same account. Keep provider-side spending limits and automatic top-ups disabled where available; local caps alone do not guarantee a zero invoice.

For a small GitHub workflow, reserve the worst-case calls for a run before making them. A crash leaves unused reservation consumed, which is conservative. Reconcile against actual attempts after successful archival, with a clear audit record. Missing/corrupt state or an unrecognized billing month should require safe initialization or stop paid providers, never silently reset usage to zero. UTC month rollover is insufficient if the provider resets on a different schedule.

For HTTP 429 and transient failures, record status and a redacted request ID. Honor a valid Retry-After value, whether seconds or HTTP date. If its delay exceeds the job's remaining time, save a cooldown and resume later. Otherwise use bounded backoff with jitter. Authentication, payment and persistent permission errors stop that provider. HTTP 434 from Tavily should be recorded as capacity failure. A quota or rate-limit error in the first state must produce explicit skipped statuses for the remaining planned states. Never retry malformed queries indefinitely.

Count every outbound attempt, including retries and failures. Keep a per-run cap, a daily cap for providers with daily quotas, and a monthly credit estimate. Query pagination and splitting share these limits. Account-wide exhaustion can still occur before the local cap, so handle it without a paid fallback.

## Acceptance tests and implementation order

These tests are proposed, not claimed as passing. Use recorded or synthetic fixtures and mocked HTTP for deterministic behavior; one small live smoke test can verify the integration afterward.

| Priority | Acceptance case | Required result |
|---|---|---|
| P0 | Plan 12 states; first provider request returns 429 | One failed cell and 11 explicit cooldown/skipped cells; other providers continue; no false empty-results claim |
| P0 | Same canonical URL appears in two providers with conflicting dates | One candidate, two intact observations, preserved original URLs/queries and a date-conflict flag |
| P0 | A run fails after making requests, or the cache is absent | Durable reservation remains charged; the next run cannot reset usage or exceed the configured allowance |
| P0 | Archive push fails before reservation | No API requests are sent; failure is saved and visible |
| P0 | A secret appears in a request URL or provider error body | Saved logs and artifacts contain no key or authorization value |
| P0 | Exa request uses its provider-specific query | Saved sanitized request and query hash exactly describe the request sent |
| P1 | NewsAPI returns 10 + 10 + 3 articles across pages | All 23 observations retained; pages stop correctly; provider total and attempts recorded |
| P1 | GNews total exceeds accessible results and removal notices are present | Status records plan restriction; no completeness claim; notices preserved |
| P1 | Ranked provider returns exactly its cap | Cell marked potentially saturated; bounded subdivision/continuation created; no infinite loop |
| P1 | Same page repeats or returns no new IDs | Stop safely with partial status and a reason |
| P1 | An article occurs exactly at a window boundary | It is retained once at candidate level while both discovery observations remain auditable |
| P1 | An undated Tavily result and an old updated page appear | They retain uncertainty; neither becomes an exact event date |
| P1 | Retry-After requests a delay longer than job time remaining | Cooldown saved; no immediate retry; query remains resumable |
| P1 | A run is re-imported twice | Archive index and candidate count are unchanged; duplicate import is recorded or ignored safely |
| P1 | Announcement and launch share an initiative and similar titles | Two reviewed milestones remain; no title-based automatic merge |
| P2 | English and native-language variants find the same article | Both query/language observations retained under the candidate |
| P2 | Monthly archive export is restored into an empty workspace | Checksums validate and derived candidate indexes reproduce exactly |

Implement P0 first: full manifest, observation retention, exact request logging and durable budget/archive state. Next add endpoint-aware paging, bounded time splitting and resume logic. Then expand query families, native-language sources and source extraction. Evaluate success using recovered verified events, exposed coverage gaps and preserved evidence, rather than larger headline counts.

## Unresolved at this checkpoint

- Pagination, subdivision, archive recovery and budget-reservation acceptance tests above have not been implemented or executed by this research task. The root implementation may change after the inspected baseline.
- The current GDELT accessible history and minimum useful time-window behavior need a bounded live test. Older documentation is insufficient to promise historical coverage.
- GNews free-plan eligibility for a published non-commercial project remains conflicted across retrieved official representations, as documented in `AGGREGATION_RESEARCH.md`. Endpoint capability does not resolve licensing.
- No provider-by-provider relevance, recall, marginal event yield or multilingual accuracy benchmark has been completed. Returned headline counts must not be presented as such a benchmark.
- No provider account-wide spending audit was performed. Other account users, promotional expiry and account-specific limits can invalidate a local free-budget estimate.
