# News aggregation: evidence, costs and operating design

Research checked 10 November 2026. Scope: finding AI-related government actions across the project's 12 Indian states. Prices below are published list prices, not a quote or a measured cost per verified event. Taxes, currency conversion, review labour and other account usage are excluded.

## Recommendation

Run a free baseline of official department sources, publisher feeds, Google News RSS and a bounded GDELT query. Fetch discovered public pages locally. Add **one** optional search provider, initially Exa or Tavily, and compare the additional verified events it finds. Keep Firecrawl or Crustdata fetching as optional extraction fallbacks. Do not make a temporary trial a dependency of the public dashboard.

The durable unit is a verified government action, not an article or an API result. Discovery can run unattended; publication should require an evidence review. A successful API request does not establish that the claimed policy exists, that the state is correct, or that an announced project is operational.

Observed in this project: the initial Google News RSS smoke test returned 60 candidates from 12 queries; Tavily extraction returned HTTP 429; the connected Firecrawl account reported no available credits. These are operational observations, not provider accuracy or coverage estimates. All comparative quality claims remain unmeasured.

## These services perform different jobs

| Mechanism | What it supplies | What it cannot establish alone |
|---|---|---|
| RSS feed | A publisher's or aggregator's current item list, usually with title, URL and a timestamp | Complete history, original event date, or coverage of every department |
| Search/news API | Searchable records from a provider's index with filters and a stable API contract | Completeness of Indian state coverage or correctness of every metadata field |
| Scraper or content extractor | HTML, text or structured fields from a known URL | Whether the text describes a state action, a repeated announcement or actual implementation |
| Reviewer and deterministic validation | A dated action supported by inspectable evidence, with state, category, stage and limitations | A population estimate of all activity unless coverage is separately measured |

**GNews API and Google News RSS are separate integrations.** A GNews account, key, pricing plan and API response do not apply to Google's RSS endpoint. Google's RSS search integration worked in the project's test, but a supported API contract or service guarantee was not established. Treat it as a replaceable discovery source.

## Provider comparison

| Option | Verified access and price | Appropriate use here | Material limit |
|---|---|---|---|
| Official department pages and publisher RSS | No third-party search fee; availability varies by publisher | Authoritative documents and recurring monitoring of known sources | Feeds are often absent or short-lived; PDFs and local-language notices need separate work |
| Google News RSS | No key in the tested integration | Broad, inexpensive candidate discovery | Undocumented integration in this assessment; redirect URLs, changing retention and ranking |
| GDELT DOC API | Public examples require no key | Additional multilingual candidate discovery | Historical documentation describes translated news, not exhaustive local-language coverage; verify live window and limits |
| Tavily | 1,000 credits/month free; basic search 1, advanced 2; basic extract 1 per 5 successful URLs; PAYG $0.008/credit | Search and selective extraction with explicit query/date settings | Credits are shared across operations; observed account rate limit; no state-level recall measurement |
| Exa | $10 recurring monthly free credit; lite $4/1,000 requests, auto $7/1,000; contents $1/1,000 pages per content type | Second discovery index and retrieval of known URLs | Lite returns index-cached content; estimated publication dates require validation |
| Firecrawl | Free 1,000 credits/month; Hobby $19/month for 5,000; simple scrape normally 1 credit/page | Selective extraction of public pages that local extraction handles poorly | Current connected account had zero available credits; operation and feature costs differ |
| Crustdata | $20 initial free credits advertised; web search 1 credit/query and web fetch 1/page; dollar conversion is account-specific | Trial a news/web search source and HTML fetch fallback | Initial credit is not verified as recurring; trial expiry and account pricing must be recorded |
| NewsAPI | Free 100 requests/day, 24-hour delay and one-month history; Business $449/month | Development comparison only on the free plan | Free plan excludes production, including internal production; article content is truncated |
| GNews API | Free 100/day, 10 articles/request, 12-hour delay and 30-day history; Essential EUR49.99/month | Optional trial, subject to eligibility clarification below | Conflicting free-plan descriptions; full content and broader access depend on plan |
| Brave Search API | Current page advertises Search at $5/1,000 requests | Optional diversification if it adds distinct verified events | Do not rely on older free-tier announcements; storage rights depend on the selected plan |

Primary pricing sources: [Tavily credits](https://docs.tavily.com/documentation/api-credits), [Exa pricing](https://exa.ai/docs/admin/pricing), [Firecrawl pricing](https://www.firecrawl.dev/pricing), [Crustdata offer](https://crustdata.com/pricing), [Crustdata credit rules](https://docs.crustdata.com/general/pricing), [NewsAPI pricing](https://newsapi.org/pricing), [GNews pricing](https://gnews.io/pricing), [Brave API](https://brave.com/search/api/). These pages were retrieved for this assessment. Do not infer production eligibility from a numerical request quota.

### GNews eligibility is unresolved

Two retrieved representations of the same official pricing URL disagreed. One described the free plan as development and testing only, with the paid plan for production. Another included non-commercial use; the official `llms.txt` also described non-commercial use. The latter also documents a 10-day paid-plan trial requiring a payment method, with restrictions on commercial use of trial data when the trial is not converted. Before using GNews for a published deployment, check the terms shown for the actual account and obtain clarification if inconsistent. Keep it disabled meanwhile. This is a documented source conflict, not permission to choose the more permissive wording. [Pricing](https://gnews.io/pricing), [official documentation index and plan descriptions](https://gnews.io/llms.txt).

### GDELT needs a current operational check

The original DOC documentation describes searches over monitored news translated from 65 languages. A subsequent official update expanded the search window, but both documents are old. Neither establishes present-day completeness, a guaranteed current retention window or successful backfill to January 2024. Start with short incremental queries, inspect returned dates and record failures. A publisher's country is not the state where the action occurred. [Original DOC API](https://blog.gdeltproject.org/gdelt-doc-2-0-api-debuts/), [window update](https://blog.gdeltproject.org/doc-geo-2-0-api-updates-full-year-searching-and-more/).

## Collection and evidence workflow

1. **Maintain a source register.** Record department, jurisdiction, language, URL, feed or listing pattern, expected format, access restrictions and last successful check. Include budgets, cabinet decisions, government orders, IT departments, sector departments, tenders and partner pressrooms. Search engines supplement this register.
2. **Generate explicit queries.** Combine canonical state names and aliases with AI terms and action terms: policy, mission, approval, agreement, procurement, pilot, deployment and allocation. Use a rolling seven-day window with overlap. Run broader weekly queries because narrow terminology misses sector programmes. Keep each query, provider, time window, language, run time and error.
3. **Store candidates before interpretation.** Preserve provider title, original URL, raw publication timestamp, discovery timestamp and query state separately. A query mentioning Kerala does not prove that Kerala's government acted. Empty results, missing credentials, exhausted credits and failed requests are different outcomes.
4. **Resolve and fetch sources.** Keep both the original URL and resolved publisher URL. Remove known tracking parameters without deleting meaningful query parameters. Fetch public HTML with timeouts, response-size limits and a descriptive user agent. Respect access restrictions; do not bypass paywalls or bot controls. Unresolved aggregator redirects remain unresolved candidates. Extract PDFs separately and flag scanned documents for OCR and review.
5. **Extract evidence locally first.** Save the body hash, response status, retrieval time, extractor version and short supporting excerpt. Trafilatura can return metadata when explicitly requested, but its date extraction remains heuristic. Inspect the relevant source passage and document heading rather than accepting an extractor's date as truth. Keep copyrighted full text out of public exports. [Trafilatura usage](https://trafilatura.readthedocs.io/en/latest/usage-python.html).
6. **Normalize without inventing precision.** Use a controlled state alias table and preserve raw names. Store event date, publication date and retrieval date independently. Explicit dates in the action description take precedence for the event date. Relative dates require an unambiguous publication date and time zone. Store month-only dates as `YYYY-MM`, unknown dates as null. Reject dates beyond the research cutoff and flag suspicious current-year metadata on older documents.
7. **Deduplicate at two levels.** Canonical URLs and content hashes reduce repeated articles. Event identity then compares state, initiative, actor, action and milestone date. Syndicated reports of one signing support one event. A later approval, launch or deployment may be a distinct milestone of the same initiative. Similar headlines alone never justify automatic merging. Preserve source links and a merge decision log.
8. **Review before publishing.** Require the source to establish a state-government role and an AI-specific action. Record category, stage, evidence strength and unresolved limitations. A partner release is primary evidence of the partner's statement, not independent proof of claimed outcomes. A second article copying the first is not independent corroboration. Exclusions receive a reason.
9. **Publish a versioned snapshot.** Validate schemas, source IDs, URLs, dates and duplicate decisions. Build CSV, JSON and dashboard from the same reviewed dataset. Expose last successful collection and last reviewed publication separately. A collection outage leaves the last reviewed snapshot available with its date.

Conditional feed requests can reduce unnecessary downloads: preserve ETag and Last-Modified, and treat HTTP 304 as unchanged, not an empty feed. [Feedparser HTTP caching documentation](https://feedparser.readthedocs.io/en/stable/http-etag.html).

### Multilingual coverage

Maintain native-language query packs and official-source lists for each selected state. Preserve original titles and evidence; label translations and have a competent reader inspect ambiguous action verbs, dates and government roles. Kannada, Tamil, Telugu, Malayalam, Marathi, Gujarati, Hindi, Bengali and Odia coverage requires more than English translations of state names. Transliteration, image notices and scanned budgets can evade both feeds and search APIs. Report coverage by language and source type, and treat unsearched languages as a known gap. Do not interpret fewer records as less policy activity.

## Operating costs: illustrative 30-day scenarios

Assume 12 states, two searches per state per day: **720 search requests/month**. Assume 300 distinct pages need remote extraction after local fetching. These are planning assumptions, not measured throughput or expected event counts. Batching, retries and other account use can change the bill.

| Configuration | Arithmetic | Estimated provider charge under stated assumptions |
|---|---|---|
| RSS, official sources, GDELT and local extraction | No paid search or extraction calls | $0 external API invoice; compute, maintenance and review still have a cost |
| Tavily basic search and basic extraction | 720 + 300/5 = 780 credits | Within 1,000 monthly free credits if available; leaves 220 credits for other use/retries |
| Tavily advanced search and basic extraction | 1,440 + 60 = 1,500 credits | 500 credits beyond a fully available free allowance: $4 at PAYG, only if enabled |
| Exa lite plus separate one-type contents requests | 720 x $4/1,000 + 300 x $1/1,000 | $3.18 list usage, within an unused $10 monthly allowance |
| Exa auto plus the same contents requests | 720 x $7/1,000 + $0.30 | $5.34 list usage, within an unused $10 monthly allowance |
| Firecrawl extraction fallback only | 300 simple pages | 300 credits; fits the advertised free allowance if available; current connected balance was zero |
| Crustdata search and fetch | 720 + 300 = 1,020 credits | Dollar cost cannot be calculated from the public credit count alone; inspect account pricing and expiry |
| NewsAPI or GNews free quota | 24 requests/day before retries | Below 100/day, but this does not resolve production eligibility, delay or historical limits |

Exa search can include text/highlights for its first ten results under the documented pricing; the table conservatively models separate contents calls, not mandatory additional calls for every result. Request only the content needed. Firecrawl paid entry is $19/month even if only 300 pages are required. Crustdata promotional credit is a trial resource, not a sustainable free operating budget. Pricing sources are linked above.

### Budget and failure controls

Track per-provider daily request count, monthly credit estimate, actual reported usage where available, maximum spend, trial expiry and remaining allowance. Reserve a margin for retries. Count HTTP attempts, not just successful queries. Disable automatic top-ups and paid fallback unless deliberately configured. Stop a provider on missing credentials, expired trial, unknown balance where a hard free limit cannot be enforced, or a spend cap. Retry transient failures with bounded backoff; stop repeated rate limits. Continue the free baseline and record the degraded run.

A cap on queries per invocation alone is insufficient: scheduled reruns and retries can exceed the daily or monthly budget. Persist counters between runs. Crustdata documents `X-Credits-Used` and account-dependent credit expiry. [Credit rules](https://docs.crustdata.com/general/pricing).

## Integration reference

The project collector accepts optional credentials through environment variables. It does not require every service. At the time of this research, its interface supports the following commands; consult `python collectors.py --help` for the final packaged version.

```powershell
Set-Location E:/kosuri/state-ai-policy-observatory
python collectors.py --providers google-rss,gdelt --days 7 --limit 5 --max-calls 12
python collectors.py --providers google-rss,tavily --days 7 --limit 5 --max-calls 12
python collectors.py --providers google-rss,exa --days 7 --limit 5 --max-calls 12
```

The second and third commands use a credential only if already provisioned. Missing keys should be recorded as skipped, not silently replaced with paid access. Current optional names are `TAVILY_API_KEY`, `EXA_API_KEY`, `CRUSTDATA_API_KEY`, `NEWSAPI_API_KEY` and `GNEWS_API_KEY`. The extraction adapter uses `FIRECRAWL_API_KEY`; a Brave adapter would use `BRAVE_API_KEY`. An installed MCP connection does not automatically provide a reusable API key to the standalone Python pipeline.

For local use, enter keys through a password manager or masked prompt into the process environment. Never paste keys into chat, source code, examples or committed `.env` files. In hosted runs, create repository Actions secrets through the hosting UI and map only the selected keys into the job environment. Do not print headers, bodies or credential-bearing query URLs. GNews places the key in a query parameter, so URL logging must be redacted. Rotate any accidentally exposed credential.

### Crustdata contract

Search: `POST https://api.crustdata.com/web/search/live`. Headers: `Authorization: Bearer <environment key>`, `x-api-version: 2025-11-01`, `Content-Type: application/json`.

```json
{
  "query": "Karnataka government artificial intelligence policy",
  "sources": ["news"],
  "location": "IN",
  "page": 1,
  "human_mode": false
}
```

Optional `start_date` and `end_date` are Unix seconds. Use `sources:["web"]` for the web index. The response contains `success`, `query`, `timestamp`, `results` and `metadata`; result fields include `source`, `title`, `url`, `snippet` and `position`. Inspect `metadata.failed_pages` and `empty_pages`. Search timestamps are ingestion/search time in milliseconds, not article publication time. A publication date is not guaranteed. `page` controls the number of aggregated pages, not an offset; values above one require one source. Default rate limit is ten requests/minute. [Search introduction](https://docs.crustdata.com/web-docs/search/introduction), [search reference](https://docs.crustdata.com/web-docs/search/reference).

Fetch: `POST https://api.crustdata.com/web/enrich/live` with the same headers and `{"urls":["https://example.com"],"human_mode":false}`. Maximum ten URLs. It returns an array with `success`, `url`, `timestamp`, `title`, `content`; content is HTML and the timestamp is Unix seconds. Match successful entries by URL because order may differ. HTTP 200 can contain failed entries with null fields. This is server-side HTML retrieval, so do not assume JavaScript application content is present. [Fetch introduction](https://docs.crustdata.com/web-docs/fetch/introduction).

### Exa contract

Search: `POST https://api.exa.ai/search`, with `x-api-key: <environment key>` or Bearer authorization and JSON content type.

```json
{
  "query": "Karnataka state government artificial intelligence policy mission deployment",
  "type": "auto",
  "numResults": 10,
  "startPublishedDate": "2026-11-01T00:00:00Z",
  "endPublishedDate": "2026-11-10T00:00:00Z",
  "userLocation": "IN"
}
```

Optional `contents:{"text":true,"highlights":true}` requests content. `lite` is a lower-cost alternative but serves cached index content. Response `results` includes title and URL, with optional `publishedDate`, `author`, `id`, text and highlights. Optional top-level `requestId`, `costDollars`, warnings and notices support logging. The documentation defines `publishedDate` as an estimate derived from HTML; it is not an event date. Author is not publisher. Use domain filters for official-source runs, and a separate unrestricted run for additional coverage. [Search schema](https://exa.ai/docs/reference/search).

NewsAPI's `GET /v2/everything` uses `X-Api-Key` and returns article URLs, titles, source metadata and UTC `publishedAt`; its `content` is truncated to 200 characters. Fetch original sources independently. [Endpoint documentation](https://newsapi.org/docs/endpoints/everything).

## Running while the laptop is off

Use a hosted scheduled job, such as a standard GitHub-hosted Actions runner, to collect candidates and save a run artifact. A local scheduler or self-hosted runner on this laptop cannot run while it is off. Standard public-repository Actions runners are free under GitHub's published billing rules; private repositories have plan-specific allowances. [Actions billing](https://docs.github.com/en/actions/concepts/billing-and-usage).

Configured schedule: daily `17 2 * * *` in UTC, equivalent to 07:47 IST, with manual dispatch, a job timeout and concurrency protection. Keep the workflow on the default branch. Scheduled Actions can be delayed or dropped under load, and public-repository schedules can be disabled after 60 days of inactivity. Therefore, inspect last success rather than claiming guaranteed daily delivery. [Scheduling documentation](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows).

The hosted job should collect and validate candidates, retain a compact audit artifact and prepare review work. Publication builds should use the reviewed dataset. A static dashboard remains available when collection fails and does not need a continuously running server. Hosting credentials, a repository destination and any selected API keys are the only additional setup needed; none should be pasted into chat. This is the recommended operating design, not a claim that an unattended deployment has been enabled.

## Benchmark before adding paid redundancy

Run a four-week prospective comparison with a fixed query manifest, shared date windows and recorded budgets. Build an adjudicated reference set across the 12 states, source types, languages and categories, including difficult PDFs and irrelevant results. Separate historical backfill from fresh discovery. The existing reviewed corpus can seed the reference set, but it is biased toward the sources used to build it.

Measure:

- Candidate precision: relevant state-government AI actions divided by inspected candidates.
- Reference-set recall: known eligible events recovered; label it relative recall, not total web recall.
- Marginal yield: new verified events added by a provider beyond the baseline and beyond other enabled providers.
- Evidence retrieval: usable supporting text and metadata, not HTTP 200 alone.
- Date/state correctness: agreement with adjudicated fields, excluding unknown dates from exact-date denominators.
- Deduplication errors: separate false merges from missed duplicates; inspect initiative milestones.
- Freshness: delay from source publication to discovery, with event date kept separate.
- Operating effort: requests, credits, failed runs, cost per accepted event and reviewer minutes per accepted event.

Use the same review rubric, record disagreements and audit a second sample independently. Retain provider provenance even when URLs merge. A provider earning many repeated headlines but no new supported actions adds little value. Keep an extra service only when its verified marginal yield or outage recovery justifies its cost and maintenance. No such comparative result has yet been measured for this project.

## Implemented release controls

Tavily and Exa are stored as encrypted repository secrets with explicit user approval. The scheduled job includes RSS, GDELT, Tavily and Exa. Each keyed provider has a conservative 720-request monthly local cap, including failed attempts and retries. The usage ledger persists locally and through an Actions cache, and is saved with run artifacts. Cache eviction or another machine can reset local accounting; this is not an account-wide billing guarantee. Other account usage and automatic top-ups remain outside these caps. NewsAPI, GNews, Crustdata and hosted extraction are optional commands, not enabled recurring dependencies. No new paid plan or automatic top-up was activated.

Local extraction was tested on 12 distinct source hosts: nine returned text, one was disallowed by robots, one failed robots verification, and one produced no usable text. Two of seven comparable extracted publication dates disagreed with the reviewed ledger. These are convenience-sample results, not a general accuracy estimate. See VALIDATION.md for the selection rule and exact cases.

The first hosted collection run completed 12 queries each through Google News RSS, Tavily and Exa. GDELT hit HTTP 429 and stopped; the others continued. It saved 357 provider observations and 320 unique URL candidates, all pending review. The run demonstrates provider failure isolation and live Tavily/Exa integration, not 320 distinct policy events or a coverage benchmark. [Run and downloadable artifact](https://github.com/VISHNU0906/state-ai-policy-observatory/actions/runs/42844796557).
