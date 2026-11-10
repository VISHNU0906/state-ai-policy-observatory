# Independent checks of the companion tracker

Checked read-only at `E:/vishnu/state-ai-policy-tracker` on 10 November 2026. Changes in that checkout are not copied over the observatory's code. `sync_tracker.py` captures selected files twice, refuses a changing read or dangling source reference, records SHA-256 hashes, and imports the frozen snapshot as proposals. Its code is inspected, never executed as part of this import.

The attached handoff describes 787 records and 1,419 source links. At the first inspection, the files contained 567 records and 1,151 links. At the first frozen import they contained 550 and 1,086. At the next frozen import they contained 543 and 1,076. These changes are consistent with ongoing edits, but they do not themselves establish improving accuracy. The retained import versions make the differences inspectable. See `data/tracker_integration_audit.json` for the latest checkpoint and exact hashes.

## Findings that affect integration

- The current representative URLs resolve to publisher-shaped URLs in the saved data. However, 977 of the 1,076 article-level links in the 543-record snapshot still use Google News URLs. The statement that no Google redirects remain applies to representative records, not every source observation. Both forms are retained. A reported redirect is not verified article equivalence.
- The inspected `pipeline/dedupe.py` contains two literal backspace bytes in the reversal regex. A Python regex word boundary needs the characters `\\b` in a raw string, not a backspace character. This can disable the claimed reversal guard. The new observatory matcher has a regression test for a signing versus cancellation. No file in the companion checkout was edited.
- The 140 labelled pairs share 31 exact state/date/headline identities across the even/odd split. That split is not independent at the document level. The labels themselves have not been independently adjudicated here. The reported precision and recall should not be carried over as production evidence for the combined system.
- `scripts/eval_dedupe.py` prints results for every threshold on both halves. This is useful for development, but repeated inspection can influence selection. The handoff does not establish an untouched final test set.
- URL identity and event identity are joined inside the companion clustering function. A single article can discuss multiple government actions, so an identical URL does not prove identical event claims. The observatory stores documents and event associations separately.
- Transitive title links can connect endpoints that were never directly judged equivalent. A reversal guard on pair edges alone does not prove every resulting cluster contains one milestone. The observatory does not turn connected components into approved events.
- The companion SQLite output is rebuilt from its CSV tables. It is an export, not persistent observation or review history. The observatory ledger preserves imports and review revisions across reruns.
- Dates in the companion main records are dates of the earliest report, according to its code and handoff. They are retained as external date claims and never used to fill the reviewed event-date field automatically.

## Reused work

The companion dataset expands candidate coverage to 13 states, including Bihar. Its source-level table, rejection reasons, review notes and proposed event groups are useful inputs. Original classifications, summaries and external IDs are preserved so a reviewer can compare both pipelines. The reviewed 85-event corpus remains a separate research reference and publication dataset. New imports never acquire approval merely because another pipeline assigned a confidence score or review label.

## Next checks

Re-run `python sync_tracker.py E:/vishnu/state-ai-policy-tracker` at each integration checkpoint. Review changes to the reversal regex, URL mappings and labelled set before adopting new claims. For a credible future evaluation, split by document and initiative before tuning, keep the final labels untouched, and score complete clusters as well as pairs. A representative relevance sample also needs an explicit sampling frame and independent review; the handoff's estimated 75 to 80 percent relevance precision is not a measured result we can reproduce from the summary alone.
