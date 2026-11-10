# Normalization rules and review examples

`normalization.py` is a review-time helper and command-line tool. It does not overwrite the reviewed corpus or automatically interpret every provider field. `pipeline.py` validates the frozen research inputs; `date_rules.py` supplies date intervals and ordering; `ledger.py` preserves original observations. These responsibilities are intentionally separate.

## State names

Apply Unicode NFKC, trim outside whitespace, collapse repeated whitespace, case-fold and remove punctuation for lookup in an explicit alias table. Use this on a structured state field only. `UP` is an alias there; the word `up` in an article is not evidence of Uttar Pradesh. Canonical state names cover all 28 states, while the research release covers 12. Union territories are not silently mapped to states.

| Raw value | Result | Decision |
|---|---|---|
| U.P.; Uttar-Pradesh; Uttar Pradesh | Uttar Pradesh | Explicit alias or formatting |
| Telengana | Telangana | Curated typo |
| Maharastra | Maharashtra | Curated typo |
| Karnatka | Karnataka | Curated typo |
| Orissa; Odissa | Odisha | Historical alias or curated typo |
| Uttaranchal | Uttarakhand | Historical alias |
| Karnatakaa | No accepted value; Karnataka suggested | Reviewer must decide |
| up to 20 centres | No accepted value | Prose is not a state field |
| Non-Latin state name | Unresolved | Transliteration is not implemented |

Fuzzy matching uses Python's sequence similarity only to suggest up to three canonical names at a 0.78 cutoff. It never accepts a suggestion automatically. The cutoff is a user-interface convenience, not a measured accuracy guarantee. Raw values, accepted values, method and review status are returned together.

## Dates

| Input pattern | Result or handling |
|---|---|
| 2025-03-02 | ISO day; calendar validated |
| March 2025; Mar 2025; 2025-03 | Month precision; bounds 2025-03-01 to 2025-03-31 |
| 2025 | Year precision; bounds 2025-01-01 to 2025-12-31 |
| 3rd March, 2025; March 3 2025 | Named month converted to ISO day |
| 13/02/2025; 02/13/2025 | Unambiguous numeric order inferred |
| 02/03/2025 | Unresolved unless dayfirst or monthfirst is explicitly supplied |
| 2025-01-01T22:00:00Z | 2025-01-02 in IST; method records timezone conversion |
| Wed, 01 Jan 2025 22:00:00 GMT | RFC 2822 timestamp converted to IST |
| Timestamp without timezone | Unresolved; no assumed UTC |
| yesterday | Requires explicit local calendar anchor |
| early 2025; around March 2025; last Tuesday | Unresolved approximate or relative expression |
| Date range | Unresolved; review the interval as evidence, do not choose an endpoint |
| Empty, null, N/A, unknown, TBD | Missing, unknown precision |
| 2025-02-29 | Invalid date; retained for review |

The bounds are for filtering and ordering only. A month-only value stays `2025-03`; it is never exported as a claim that the action happened on 1 March. Sort known lower bounds newest first, narrower precision first for ties, then state and stable ID. Unknown dates sort last. The dashboard implements the same order.

Publication, update, discovery and retrieval dates remain different fields. A provider's estimated publication date does not become an event date. Relative phrases require the relevant original source's date, not today's collection date. A timezone conversion is appropriate for a timestamp describing an instant; do not apply it to a date printed on a government order.

## URLs and text

The ledger removes fragments and known tracking parameters and lowercases the host. It preserves meaningful query parameters and document IDs. Credential-bearing URLs are rejected. Google News redirect URLs and publisher URLs remain separate until their relationship is verified. A canonical URL identifies a document candidate, not an event. A single article can report several government actions.

Title tokenization supports review suggestions only. Numbers, state, stage, counterparty and reversal terms can change event identity even when most words match. The project does not auto-correct policy names, monetary amounts or institution names from edit distance.

## Reproduce

```sh
python normalization.py state "U.P."
python normalization.py date "02/03/2025"
python normalization.py date "02/03/2025" --numeric-order dayfirst
python normalization.py date yesterday --anchor 2025-01-01
python -m unittest discover -s tests -p test_normalization.py -v
```

English named-month parsing uses the process locale through Python `strptime`; the tested runtime uses English month names. Regional-language date parsing, financial-year intervals, OCR correction and automatic date-range interpretation are not implemented. Every unsupported form is retained for review rather than silently coerced.
