# Validation and observed failures

## Data and code

The repository includes nine regression tests covering state aliases, partial and invalid dates, cutoff enforcement, review gating, event-level deduplication, meaningful URL parameters, missing credentials, and provider timestamp semantics. API tests use explicitly synthetic fixtures; they are not live-provider performance measurements.

The offline build validates every reviewed event's ID, state, date precision, category, stage, source references and supporting source summaries. CSV, JSON and dashboard are generated together. A separate build reproducibility check compares output hashes across consecutive unchanged builds.

## Live discovery

The first restricted-network RSS run failed DNS for all six then-configured states. Its failure log is retained. After network access was enabled and scope expanded, 12 Google News RSS queries returned 60 pending candidates without a failed feed. This proves the tested integration executed; it does not measure relevance or historical completeness.

A separate recent-window run queried Google News RSS and GDELT for Tamil Nadu and Gujarat. It returned 14 URL-distinct candidates across four completed queries with zero failures. Provider provenance is retained. Google redirect URLs can prevent cross-provider article matching, so this is a URL count, not 14 distinct events.

Optional Tavily, Exa, GNews, NewsAPI and Crustdata adapters are implemented against retrieved provider contracts. Keyed adapter contract tests use fixtures. No new paid plan, automatic top-up or trial subscription was activated. Connected research tools were used during source research; that is distinct from testing every standalone API adapter with the user's own account.

## Local extraction experiment

Selection rule: first source from each distinct host in the ordered source ledger, up to 12. This is a convenience sample, mainly Rajasthan/Madhya Pradesh documents, not a representative benchmark across 12 states. Python Trafilatura extracted HTML and pypdf extracted PDFs; robots rules and conservative failure handling were enforced.

| Result | Count | Interpretation |
|---|---:|---|
| Text extracted | 9 | At least 100 characters returned, not proof of relevance or correctness |
| Robots disallowed | 1 | LinkedIn source intentionally not scraped |
| Robots unavailable | 1 | MPSeDC source not fetched when robots verification failed |
| Empty extraction | 1 | Odisha Gazette endpoint returned no usable text through this path |

The nine extracted documents included eight HTML pages and one 29-page PDF. Full extracted bodies remain in the ignored local cache and are excluded from the public repository and release. Run logs preserve URL, hash, extractor, title, character count, date candidate and status.

Among seven HTML results with both an extracted date and a reviewed source publication date, five dates matched and two disagreed. DD News yielded 10 November 2026 instead of the reviewed 31 December 2025 publication date. PIB yielded 20 November 2025 instead of the reviewed 7 January 2026 publication date. A live AI portal also yielded 1 January 2026 despite lacking an established publication date. These observations are a concrete reason to keep extracted date candidates separate from reviewed dates. The sample is too small and biased to estimate general date accuracy.

## Provider failures during research

Firecrawl's connected account reported exhausted credits. Tavily extraction encountered HTTP 429. Exa and alternative retrieval paths supplied the retained evidence. No access controls or paywalls were bypassed. Partial retrieval and unresolved original-document gaps remain in source and event limitations.

## Verification boundary

The research audit independently re-fetched eight difficult evidence pages in addition to initial retrieval. It did not independently re-fetch every source. Browser interaction results and deployment verification are recorded in the release checklist. Scheduled collection is best-effort; a successful first run does not guarantee future delivery. Candidate artifacts expire after 30 days unless downloaded or otherwise archived.

## First hosted multi-provider run

The [10 November hosted run](https://github.com/VISHNU0906/state-ai-policy-observatory/actions/runs/42844796557) completed on GitHub without the laptop running the job. Google News RSS, Tavily and Exa each completed 12 state queries. GDELT returned HTTP 429 on its first state after bounded retries; the adapter stopped that provider and the others continued. The run saved 357 provider observations and 320 unique URL candidates. They were not automatically accepted or counted as additional policy events. This verifies the live Tavily and Exa adapters, as well as the free baseline's failure isolation. NewsAPI, GNews and Crustdata still lack live account tests.

The current dashboard was checked in a browser for search, source expansion, unknown-date filtering, reset and empty-state behaviour. Filtered CSV download produced four rows, all with empty event dates, matching the four unknown-date records. Consecutive unchanged builds produced identical hashes for the event CSV, full JSON and browser data payload. All nine regression tests passed locally and in the first hosted build.
