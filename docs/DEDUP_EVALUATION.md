# Duplicate-event evaluation protocol

This checkpoint contains a completed, bounded diagnostic set: **12 same-event report pairs, 22 hard negative pairs and 8 unscored context cases** in `evaluation/event_pairs.json`. No matching-system metrics have been computed. The labels were manually assigned by the research agent using the reviewed production evidence ledger. They await independent human review; they are not an assertion of perfect web truth.

## What is being compared

The unit is a source-specific event claim, identified as `event_id::source_id`, matching the production `candidate_id`. Both event IDs and source IDs must resolve in the accompanying corpus, and each source must be associated with the named event. A positive means both claims report the same named government action, counterparty and milestone. It does not mean the articles are textually identical or independently sourced.

Article identity is recorded separately. `source_document_identity` identifies whether the two claims reference the same source record. `same_underlying_article` is true only for an identical source record; otherwise it remains null. Different URLs can reproduce one article. Conversely, one article can describe several separate agreements. This set does not pretend to contain a fully adjudicated textual-syndication benchmark.

The corpus path and SHA-256 record the reviewed input snapshot. Later corpus changes should trigger ID/reference validation and reconsideration of affected labels, rather than silently rewriting benchmark history.

## Why these pairs are useful

The positives include next-day reporting of a cabinet decision, official and partner accounts of a signing, different publishers covering one agreement, and print/web coverage of the same action. The Uttar Pradesh AM Group pair retains one signing despite contradictory completion forecasts. Conflicting attributes must be preserved for review rather than creating a second event automatically.

The hard negatives target specific failure modes:

- Same initiative, later action: Rajasthan consultation, approval and launch; Maharashtra cabinet approval and resolution; Tamil Nadu mission announcement and sanction; Uttar Pradesh announcement, budget and cabinet decision.
- Same date, different agreements: Gujarat IBM and Microsoft; Rajasthan Google, IIT Delhi and NLU; Madhya Pradesh IndiaAI, BHASHINI and nasscom; Odisha HCLTech technology centre and tripartite AI data centre.
- Similar vocabulary, different states: Google or Microsoft partnerships and state AI missions.
- Same document, multiple actions: Karnataka budget proposals and Kerala education programmes.

The shared-document negatives are especially important. Exact URL or content equality can remove duplicate downloads, but it cannot collapse distinct claims extracted from the same document. A system unable to isolate those claims should abstain or retain a multi-event document for review.

## Context links are not positive duplicate labels

Eight associations are explicitly unscored. Examples include a later government circular supplying the date of an earlier resolution, an undated live portal corroborating existence, a policy index with inconsistent metadata, and a retrospective feature describing implementation. These may be valuable evidence links without being duplicate reports of the original action.

The UPDESCO labs case remains unscored: Parliament identifies an agreement in September 2025, while PIB describes a January 2026 ceremony without establishing whether it renewed or expanded the instrument. The production record's conservative association does not justify a confident document-equivalence label.

## How to evaluate without leaking the answer

1. Validate all IDs and source associations against the recorded corpus. Reject malformed or missing references.
2. Use identifiers only for lookup. Do not give the matcher event IDs, existing cluster membership, canonical event summaries, adjudicated reasons or this file's labels as features. These reveal the answer.
3. Supply captured source text and independently extracted event claims. If only manually curated event descriptions are supplied, describe results as matching tests on reviewed claims, not end-to-end news extraction performance.
4. Freeze a version and matching configuration before evaluation. This set has been shared with the implementer and is a development set. A later held-out set must be selected and reviewed independently of tuning.
5. Compare predictions with scored labels only. Count false merges and missed merges separately. Report precision and recall for same-event matching, the complete confusion matrix, and abstentions. Define treatment of abstentions explicitly; report automation coverage as well as accuracy on decided cases.
6. Report results by failure type and list every error by pair ID. Shared sources and repeated initiatives make observations dependent, so raw pair counts are not independent experiments. With this small purposive set, avoid general accuracy claims about all Indian news.

A deployment test should also evaluate clusters, not just selected pairs: a mistaken bridge can join otherwise unrelated events through transitivity. This file alone does not establish cluster-level performance, candidate-retrieval recall, extraction quality, state normalization or date parsing accuracy. Those require separate fixtures and a genuinely held-out collection.

## Review and limitations

Each scored pair includes an explicit reason, limitation and review status. Corrections should retain the previous version and explain which evidence changed. An independent reviewer should inspect the source claims, especially same-day agreement granularity and retrospective references, without seeing model predictions first.

The source ledger contains verified excerpts and summaries, but not necessarily a full immutable article snapshot. No new page retrieval was performed for this evaluation task. No facts were invented to manufacture pairs, and no additional sources or research records were added. The result is a traceable diagnostic asset for deduplication development, not a claim that the matching engine has already passed it.
