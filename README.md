# State AI Policy Observatory

85 reviewed AI-related government milestones across 12 Indian states, supported by 113 source documents. Window: 1 January 2024 to 10 November 2026. This is a selected research sample, not a national census or state ranking.

[Public repository](https://github.com/VISHNU0906/state-ai-policy-observatory). The verified live dashboard link is recorded in `docs/RELEASE.md` after deployment.

## Deliverables

| Deliverable | Location |
|---|---|
| Dataset | `data/events.csv` (UTF-8 CSV), `data/events.json` |
| Source ledger | `data/sources.csv` |
| Dashboard, also opens offline | `dist/index.html` |
| One-page rationale | `output/Rationale.pdf`, `docs/RATIONALE.md` |
| Research findings and state comparison | `output/Research_Report.pdf`, `docs/RESEARCH_FINDINGS.md` |
| Provider comparison and architecture | `output/Collection_Architecture.pdf`, `docs/AGGREGATION_RESEARCH.md` |
| Definitions and data dictionary | `docs/METHODOLOGY.md` |
| Independent evidence audit | `docs/RESEARCH_AUDIT.md` |
| Tests and observed failures | `docs/VALIDATION.md`, `runs/` |
| Source associations and merge audit | `data/source_observations.csv`, `data/deduplication_audit.csv` |
| Exclusions and queries | `data/exclusions.json`, `data/query_log.json` |

## Run the snapshot

Python 3.11 or later. The build and discovery use the standard library, with no required packages or API keys.

```sh
python -m unittest discover -s tests -v
python pipeline.py build
python -m http.server 8765 --directory dist
```

Open `http://localhost:8765`, or open `dist/index.html` directly from disk. Filters, evidence panels and CSV export work offline; original sources need the internet. The data payload is packaged locally. No API keys are sent to the browser.

## Collect candidates

```sh
# Fixed submission-window Google News RSS collection
python pipeline.py collect --limit 5
# Rolling recent discovery, free baseline
python collectors.py --providers google-rss,gdelt --days 7 --limit 10 --max-calls 12
# Optional providers when credentials and suitable plans exist
python collectors.py --providers google-rss,gdelt,tavily,exa --days 7 --limit 10 --max-calls 12
python collectors.py --providers gnews,newsapi,crustdata --days 7 --limit 5 --max-calls 12
```

New results remain pending. `--max-calls` caps queries per provider per invocation; each query has at most three attempts. Keyed requests also reserve from a local monthly ledger before sending. Default cap: 720 attempts/provider/month, overridable with `<PROVIDER>_MONTHLY_REQUEST_CAP`. Failed attempts count. This does not guarantee account-wide zero billing: other usage, automatic top-ups and cache loss remain outside the cap.

The rolling collector ends at yesterday's midnight UTC to accommodate delayed free plans, intentionally omitting the newest period. The window is logged. Missing keys are skipped. Authentication, quota and repeated rate-limit failures stop that provider; others continue. If no provider completes a query, the run fails after saving its log. Files go to `runs/` or `--output-dir`.

Google News RSS and GNews API are separate services. NewsAPI's free development plan is not a production plan. GNews free-use wording conflicted across retrieved official representations; leave it disabled until account eligibility is clarified. Exa publication dates are estimates, GDELT seen dates are discovery dates, and Crustdata timestamps are not publication dates.

## Extract originals

```sh
python -m pip install -r requirements-extraction.txt
python extract_documents.py --backend local --limit 12 --diverse
python extract_documents.py --backend tavily --limit 5
python extract_documents.py --backend firecrawl --limit 5
python pipeline.py refresh-sources --limit 10
```

Local extraction uses Trafilatura for HTML and pypdf for PDFs. It checks robots rules, caps response size and logs failures. Full text stays in ignored `.cache/`; public logs contain hashes, metadata and status. Scanned PDF OCR and browser-rendered extraction are not implemented. Hosted extraction is explicit, never an automatic paid fallback.

Optional environment variables: `TAVILY_API_KEY`, `EXA_API_KEY`, `FIRECRAWL_API_KEY`, `NEWSAPI_API_KEY`, `GNEWS_API_KEY`, `CRUSTDATA_API_KEY`. `.env.example` lists names only and is not automatically loaded. Never commit credentials.

## Review and publish

1. Inspect original evidence and identify the government action, state, event date and stage.
2. Add accepted events and supporting sources to `research/*.json`; log exclusions and conflicts.
3. Keep distinct agreements and milestones separate. Repeated reports attach to the same event. `python pipeline.py suggest-duplicates` creates review suggestions, never automatic merges.
4. Run tests and build. Inspect the dataset diff and dashboard.
5. Commit and push to `main`; Pages rebuilds the reviewed snapshot.

The initial corpus was assembled through retrieved-source research and manual adjudication. It was not automatically extracted from the RSS smoke-test results. The deterministic pipeline creates CSV, audit tables and dashboard from those reviewed inputs. The fixed cutoff in `pipeline.py` is deliberately frozen; a later research release must deliberately update it. Scheduled discovery uses a rolling window independently.

## Hosting and schedule

GitHub Pages serves the static dashboard. `pages.yml` runs tests and rebuilds before publication. `collect.yml` collects daily at **02:17 UTC / 07:47 IST**, with manual dispatch and a 15-minute timeout. It uses RSS, GDELT, Tavily and Exa. The latter two have encrypted repository secrets provisioned with permission. Free sources continue if their keys fail.

The job preserves usage through Actions cache and includes it in run artifacts. Artifacts expire after 30 days; download or archive them for longer retention. Cache eviction can reset local counters. Scheduled Actions are best-effort, may be delayed, and public schedules may be disabled after 60 days of inactivity. No guaranteed uptime, automatic event publication or missed-run notification service is claimed. Verified first-run outcomes are in `docs/RELEASE.md`.

## Scope and limits

Andhra Pradesh, Assam, Gujarat, Karnataka, Kerala, Madhya Pradesh, Maharashtra, Odisha, Rajasthan, Tamil Nadu, Telangana and Uttar Pradesh provide different regional and administrative cases. Every state has at least six records. Counts are not comparable measures of government activity. Evidence is mainly English-web material; regional-language search coverage is not systematic.

Four event dates are unknown and three are month-only. A primary-source flag means a primary document is attached, not that it proves every statement. A signing is not deployment; a launch is not proof of impact. Budgets, tender estimates, private investment and actual expenditure are not interchangeable and are never summed across this corpus.

## Release and history

Commits record actual development stages. The local submission contains a source ZIP and a Git bundle preserving reachable history:

```sh
git clone state-ai-policy-history.bundle state-ai-policy-observatory
```

PDF regeneration is optional and needs ReportLab and pypdf: run `python build_reports.py`, then `python finalize_assets.py`. Windows uses Segoe UI when present; other systems fall back to Helvetica, so layout and non-Latin glyph support may differ. Supplied PDFs were rendered and inspected. Core dataset/dashboard reproduction does not need PDF tooling.

Publishers retain rights in their sources. The dataset contains short excerpts and original analytical summaries with attribution, not full article bodies. No broad relicensing claim is made over third-party material.
