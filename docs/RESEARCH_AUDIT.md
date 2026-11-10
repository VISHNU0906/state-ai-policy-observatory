# Research audit

Reviewed 10 November 2026. The initial audit read all six research files, covering 82 event records and 111 source records. Subsequent corrections split distinct agreements previously grouped by ceremony; the generated quality report gives current totals. The audit checked source roles, date reasoning, stages, financial claims and repeated milestones. It independently fetched selected pages for difficult cases, then additional agreement sources to resolve grouping; it did not independently re-fetch every citation or certify every claim. Source IDs below resolve in `data/sources.csv` and the research files.

## Findings and corrections

- **Publication versus update:** corrected `up-google-ht` to leave original publication date unknown. Its visible page says updated 8 January 2025 at 05:46 IST, while extraction metadata gives 7 January without a time zone. The print clipping supplies the event record's 8 January publication date. Its explicit Tuesday wording supports signing on 7 January. Neither a headline saying “launch” nor an update date changes the verified signing stage. [Web article](https://www.hindustantimes.com/cities/lucknow-news/up-govt-google-cloud-launch-ai-powered-agri-network-101736273606574.html).
- **Cutoff-day evidence:** independently retrieved both articles for `AP-2026-01`. Their dated bodies report the Cabinet meeting on Tuesday 10 November 2026 and approval of the Robotics and Physical AI Policy. This is genuine article content, not a current website banner. The underlying Cabinet notification remains unverified, so medium confidence is appropriate. [Hans India](https://www.thehansindia.com/andhra-pradesh/ap-cabinet-approves-major-decisions-1140821), [Telugu360](https://www.telugu360.com/ap-cabinet-clears-ai-data-centres-robotics-policy-semiconductor-reforms-and-major-industrial-projects/).
- **Retrospective official dates:** the Tamil Nadu policy note explicitly names G.O.47 dated 5 August 2026. `TN-2026-01` correctly identifies the note as retrospective evidence rather than claiming to have inspected the order itself. The note's 2026 references occur throughout substantive text. [Policy note](https://cms.tn.gov.in/cms_migrated/document/docfiles/it_e_pn_2026_27.pdf).
- **Consultation versus deployment:** the Assam RFI explicitly dates itself 15 March 2026 and says it precedes a possible formal procurement tender. `as-2026-appi` correctly remains announced. Its deployment category describes the intended application, not installation. [RFI](https://finance.assam.gov.in/sites/default/files/swf1/dms14_merged_rfi_ai_in_public_procurement.pdf).
- **Firsthand signing evidence:** Assam's signatory explicitly states that the Google Cloud MoU was signed on 11 November 2025. This resolves conflicting next-day reporting for `as-2025-google`; it does not prove the proposed centre subsequently opened. This is a personal public account used in an official capacity, not the executed agreement. [Signatory's post](https://www.linkedin.com/posts/gopinath-narayan-9948875_so-whats-it-about-tuesday-and-it-in-assam-activity-7394008007455629312-cC1d).

## Source-role limits

A primary source attached to a record may support only part of it. For `mh-marvel-approval-2024`, `west-s04` confirms establishment in March 2024, while the Cabinet approval claim comes from contemporary news. For `KA-2026-01`, `S-KA-06` corroborates the committee, while the first-meeting date comes from `S-KA-05`. The live BuildNow portal supports the service's existence, while the historical HMDA expansion date comes from reporting. A primary-source badge must mean **primary source attached**, not that every claim or date was confirmed by that source.

The Karnataka report also confirms that CATS is associated with a ₹20 crore outlay in that account, while the earlier budget proposed ₹50 crore over five years. The different figures must remain unresolved rather than being treated as additive commitments. [Official report](https://eitbt.karnataka.gov.in/uploads/media_to_upload1785224806.pdf).

Government hosting does not convert a newspaper clipping into primary evidence. Partner hosting does not make a reproduced newspaper story an independent account. Source counts count documents, not independent witnesses. Promotional government and corporate descriptions establish what their authors claim, not independently measured public benefit.

## Counting and deduplication

Policy approval, gazette publication, operational rules, budget provision and launch can be separate milestones of the same initiative. Examples include the Odisha policy, Uttar Pradesh AI Mission, Maharashtra AI policy and Gujarat CoE. Keep their initiative linkage visible. Conversely, repeated reports of one MoU should collapse into one event with multiple sources.

The consistent unit is a distinct decision or agreement, or a separately identifiable milestone of one initiative. A shared ceremony does not justify merging agreements with different parties and scopes. The Odisha correction replaces `od-2026-hcl-partnerships` with two signed records: the tripartite HCLTech, Sarvam and state AI data-centre agreement, and the bilateral HCLTech technology-centre agreement. Both retain the 24 July 2026 date and shared infrastructure initiative. Sarvam is a party to the tripartite instrument, so a third Sarvam-only row would duplicate that agreement. Separate company releases verify the distinction: [data centre](https://www.hcltech.com/press-releases/hcltech-announces-ai-data-center-bhubaneswar-partnership-sarvam-and-government), [technology centre](https://www.hcltech.com/en-us/press-releases/hcltech-establish-global-technology-center-bhubaneswar).

Follow-up Rajasthan verification identifies separate Google, IIT Delhi and NLU Jodhpur agreements and their respective scopes. The NLU original explicitly confirms its bilateral agreement and 6 January date. PIB's collective mention of Wadhwani does not by itself allocate contractual scope or prove a separately scoped fourth instrument; the dataset must preserve that uncertainty rather than invent terms. [NLU original](https://nlujodhpur.ac.in/news/362), [detailed reporting](https://government.economictimes.indiatimes.com/news/digital-india/rajasthans-ai-ml-policy-2026-pioneering-governance-and-skill-development/126411395). Event totals still must not rank states: source availability and the number of recorded milestones differ.

In the initial 82-record audit, 65 were announced, signed or approved; 14 launched and three operational. Splitting signed agreements increases the first group, without creating additional deployment claims. A launch can concern a policy document, training programme or institution. These numbers cannot be translated into 17 deployed public services or an implementation success rate. Missing events and publication bias are not measured.

## Financial controls

| Records | Amount type and aggregation restriction |
|---|---|
| UP mission announcement and budget | Approximately ₹2,000 crore programme envelope and ₹225 crore annual budget proposal are different scopes. Do not add them. The separate ₹32.82 crore labs/CoE provision needs its own scope. |
| UP AM Group and Odisha HCLTech | Proposed private project investment is not state expenditure. Odisha's reported project amount includes unspecified state assistance. Do not infer the government's share. |
| Karnataka CATS and earlier CoE | ₹50 crore over five years, later ₹20 crore and earlier ₹28 crore accounts have unresolved programme relationships. No combined total is defensible. |
| Karnataka prison package; Tamil Nadu engineering centres | ₹5 crore and ₹50 crore respectively cover mixed equipment or technologies. Neither is an AI-only allocation. |
| Maharashtra agriculture policy and Sarvam package | Proposed initial allocation and an approved two-year package are different fiscal instruments. Neither establishes disbursement. |
| Gujarat challenge rules | Per-use-case ceilings and conditional support limits are not a total programme budget. |
| Rajasthan GPU tender | ₹9 crore is an estimated procurement cost, not a contract award or expenditure. |
| Assam 2024 budget | The nearby ₹5 crore provision concerns the VR GyanDhara initiative, not the AI centre. |

No cross-state investment or expenditure total should be calculated from these records. Future financial analysis needs separate fields for instrument, payer, currency, fiscal period, scope, proposed versus sanctioned versus spent, and overlap with earlier announcements.

## Unresolved evidence

Retain the existing caveats for unknown event dates, month-only dates, the Maharashtra policy index/PDF discrepancy, AM Group's conflicting commissioning schedules, Telangana TGDeX launch inventory figures, Uttar Pradesh lab counts and the Odisha infrastructure sequence. These require original orders, contracts or implementation reports, not stronger language. The evidence supports a comparison of documented policy choices and administrative steps; it does not establish state performance, public value, legal compliance or procurement effectiveness.
