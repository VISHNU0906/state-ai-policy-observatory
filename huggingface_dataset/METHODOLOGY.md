# Methodology and data dictionary

## Research design

Window: 2024-01-01 through 2026-11-10, inclusive. Unit: a named state-government action or separately documented milestone. The 12-state sample is purposive, not probability sampled. No claim of exhaustive coverage, relative state performance or causal impact is made. Contemporary and retrospective documents can support events inside the window. The retrieved document itself must be available at the cutoff.

Primary research used Exa and Tavily search/retrieval, direct official documents and targeted news checks. Firecrawl was attempted but its connected account had exhausted credits. Search snippets were leads, not sufficient evidence. Six reviewed research files preserve the event assertions, source summaries, short excerpts, query logs and exclusions. These are researcher-reviewed inputs, not raw automatically extracted event labels. The pipeline generates the deliverable tables and dashboard from these inputs.

## Inclusion decisions

Require explicit AI relevance and a named state-government institution, department, state university, public authority or documented state support. Include policy development, formal approval, government partnership, institutional capacity, proposed or approved finance, procurement, government application and safeguards. A state university partnership qualifies when it creates a state public institution's capacity. Private infrastructure qualifies only when a specific state commitment is documented; that involvement must remain visible in the limitation.

Exclude national programmes without a specific state action, general digital services without AI evidence, commercial launches without a state role, duplicate coverage without a new milestone, unsupported snippets, and events outside the window. Acronym context matters: Assam's livestock 'AI' can mean artificial insemination. No amount is inferred from a nearby budget paragraph.

## Event fields

| Field | Meaning and validation |
|---|---|
| id | Stable reviewed action ID. IDs are opaque; do not derive dates from them. |
| state | One of the 12 canonical state names. Alias normalization is explicit. |
| title, summary | Concise account of the supported action, with future commitments in future/conditional language. |
| date / event_date | ISO day, month or year; null if the action date is unknown. CSV calls it date; JSON retains both for compatibility. |
| date_precision | day, month, year or unknown. No fabricated first day of a month. |
| date_basis | Why this event date was chosen, including relative-date and retrospective-document reasoning. |
| publication_date | Publication date of the event's selected reporting source when known, not necessarily event date. Source-level ledger retains source-specific dates and any update date. |
| source_name, source_url | First reviewed source anchoring the event; an official contextual source does not silently replace it. |
| source_ids | Ordered references to the evidence ledger. CSV stores a JSON array. |
| category | One principal category per event, chosen by the action's dominant purpose. |
| stage | Evidence-supported stage of this action, not the whole initiative's latest status. |
| initiative | Human-readable grouping of related actions. Names are reviewed, not inferred from title similarity. |
| confidence | high or medium, a qualitative assessment of support for the recorded action; not a numerical probability or outcome score. |
| limitations | Specific gaps, conflicts, date uncertainty, financial-scope caveats and unverified implementation. |
| has_primary_source | A primary government or partner source is attached. It does not mean every claim/date is primarily verified. |
| source_count | Number of linked documents, not independent witnesses. |

Source fields include ID, URL, publisher, original title, publication date, retrieval date, source type, retrieval status, short supporting excerpt and evidence summary. Government hosting does not make reproduced news primary evidence. Excerpts are limited; full copyrighted article bodies are not redistributed.

## Taxonomy

| Category | Boundary |
|---|---|
| Policy & strategy | Missions, policy drafts, adoption, notification and roadmaps |
| Institutions & capacity | Centres, task forces, public AI infrastructure and skills programmes |
| Partnerships | Signed government agreements with external organisations |
| Public-sector deployment | Intended, piloted or operational public-service applications; read stage separately |
| Funding | Explicit allocations, sanctions or financing rules as the central action |
| Responsible AI | Oversight, assessment, ethical or safety governance as the central action |

Announced means a stated intention, proposal, consultation or pre-procurement action. Approved means a formal authorisation supported by the evidence. Signed means an agreement was executed. Launched means publicly introduced, which can include a policy document or training programme. Pilot means limited trial use. Operational means an explicit account of actual use. These stages are not a numerical maturity scale. A launch does not prove effectiveness. The current corpus may contain no records at a defined stage.

## Deduplication and provenance

1. Canonicalize URLs: lowercase host, remove fragments and known tracking parameters; preserve document IDs and other query parameters.
2. Durable collection gives identical canonical URLs one document identity but retains each provider/query observation separately. Legacy JSON collectors collapse more metadata; the ledger cannot reconstruct observations already lost in those older exports. Google aggregator redirects are not automatically equivalent to publisher URLs.
3. Research review assigns event identity using state, institution/counterparty, initiative, action and date. Distinct agreements and later milestones remain distinct. Where an original source does not identify agreement-level boundaries, retain an explicit grouped record and caveat rather than invent instruments.
4. The build joins reviewed source associations by event ID. The audit records all linked sources. Additional source links are not automatically 'duplicate articles': a document may corroborate only part of a claim or support several events.
5. Similarity produces review suggestions only, with stage, reversal and numeric-conflict warnings. The current diagnostic retrieves 3 of 12 positive pairs and suggests 6 of 22 distinct pairs at threshold 0.45. Its precision is 0.333 and recall is 0.25 on 34 development pairs. This is not a held-out accuracy estimate and does not justify automatic merging.
6. New ledger reviews require a reviewer, reason and expected revision. Manual merges preserve source associations and the superseded ID; a guarded restore can undo them. Re-imports do not erase rejections. The frozen dashboard still builds from versioned research JSON; ledger approval alone does not publish a new dashboard event. An approved release must reconcile those inputs and review the resulting diff.

See [normalization rules](NORMALIZATION.md) for explicit state aliases, typo handling, ambiguous dates and missing values; [ledger operations](LEDGER_OPERATIONS.md) for commands; and [tracker integration findings](TRACKER_INTEGRATION_FINDINGS.md) for the external dataset audit.

Each row can be traced CSV -> event ID -> research file -> source IDs -> original URLs. Source counts are neither independent-witness counts nor recall estimates. Syndicated copies may corroborate a date but do not create independent confirmation.

## Reliability and limitations

The build validates IDs, state vocabulary, taxonomy, date precision, date window, nonempty evidence summaries and source references. Tests exercise aliases, invalid/partial dates, meaningful URL parameters, review gating and provider date semantics. A successful HTTP response or long extracted text is not a correctness test. Browser checks cover the actual filters, evidence expansion, empty states and downloads.

This release is predominantly English-web research. Local-language notices, scanned PDFs, removed pages, unindexed government systems and paywalled content can be missed. Query logs document targeted searches, not every possible search. A limited live collector test does not establish long-run availability or comparative provider quality. APIs with missing keys are not live-tested. Actual public outcomes, procurement award, spending, privacy compliance and programme effectiveness remain outside what these announcements alone establish.

Do not sum quoted amounts across rows. Programme envelopes, annual provisions, mixed-technology packages, private investment, conditional ceilings and tender estimates are different quantities. The research audit identifies overlapping and conflicting examples. A financial dataset would require separate payer, instrument, fiscal period, status and overlap fields.

## Updating

Run discovery, retrieve eligible originals, review dates/states/actions, append or amend research inputs, run tests and build, review the diff, then publish. The fixed cutoff is deliberately frozen in pipeline.py for this submission. A later release must deliberately change the cutoff and document its revision. Scheduled collection uses a rolling seven-day window and does not change the frozen research snapshot.
