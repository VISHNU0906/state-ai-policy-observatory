# Release verification

Research cutoff: 10 November 2026. Public release verified on the same date.

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

The scheduled workflow runs at 07:47 IST daily on a GitHub-hosted runner. Tavily and Exa secrets were installed with explicit approval. No paid subscription or automatic top-up was activated. Request caps do not control other usage or provider-side billing. Candidate artifacts expire after 30 days. Keep a separate archive for long-term monitoring.

## Local submission

The release builder creates a single local submission folder and ZIP containing the CSV/JSON data, PDFs, documentation, offline dashboard, source ZIP, Git history bundle and SHA-256 manifest. No Drive upload was performed, as requested. Full source article caches and credentials are excluded.
