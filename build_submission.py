"""Build figures, a technical submission, and a metadata-only Hugging Face package.

Optional authoring dependencies: matplotlib and reportlab. Core pipeline is stdlib.
"""
from pathlib import Path
from collections import Counter
import csv, hashlib, html, json, shutil
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image, PageBreak
from normalization import normalize_state, normalize_date

ROOT=Path(__file__).resolve().parent
OUT=ROOT/'output'; FIG=OUT/'figures'; HF=ROOT/'huggingface_dataset'
SITE='https://vishnu0906.github.io/state-ai-policy-observatory/'
REPO='https://github.com/VISHNU0906/state-ai-policy-observatory'

def read_csv(path):
    with path.open(encoding='utf-8-sig',newline='') as f:return list(csv.DictReader(f))

def dump(path,data):path.write_text(json.dumps(data,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')

def savefig(fig,name):
    fig.savefig(FIG/(name+'.png'),dpi=180,bbox_inches='tight',facecolor='white')
    fig.savefig(FIG/(name+'.svg'),bbox_inches='tight',facecolor='white')
    plt.close(fig)

def figures(events,verification):
    FIG.mkdir(parents=True,exist_ok=True)
    plt.rcParams.update({'font.family':'DejaVu Sans','font.size':10,'axes.spines.top':False,
        'axes.spines.right':False,'axes.titleweight':'bold','axes.labelcolor':'#303b44','text.color':'#172934'})
    states=sorted({e['state'] for e in events})
    primary=[sum(e['state']==s and e['has_primary_source']=='True' for e in events) for s in states]
    total=[sum(e['state']==s for e in events) for s in states]
    fig,ax=plt.subplots(figsize=(9.3,5.2))
    ax.barh(states,primary,color='#176a77',label='Primary source attached')
    ax.barh(states,[t-p for t,p in zip(total,primary)],left=primary,color='#bac8ce',label='Other sources only')
    for i,n in enumerate(total):ax.text(n+.1,i,str(n),va='center')
    ax.invert_yaxis();ax.set_xlim(0,10);ax.set_xticks(range(0,11,2));ax.set_xlabel('Reviewed events');ax.legend(loc='upper center',bbox_to_anchor=(.5,-.13),ncol=2,frameon=False)
    ax.set_title('Coverage and attached evidence',loc='left',pad=15)
    fig.text(.01,-.08,'85 selected events across 12 states. Alphabetical order. Counts are not a ranking of state activity.',fontsize=9)
    fig.tight_layout();savefig(fig,'01_state_coverage')
    fig,axes=plt.subplots(1,2,figsize=(10,4.1),gridspec_kw={'width_ratios':[1.5,1]})
    cats=Counter(e['category'] for e in events); order=sorted(cats,key=lambda k:(-cats[k],k))
    axes[0].barh(order,[cats[k] for k in order],color='#176a77');axes[0].invert_yaxis()
    axes[0].set_title('Type of government action',loc='left');axes[0].set_xlabel('Reviewed events')
    for i,k in enumerate(order):axes[0].text(cats[k]+.2,i,str(cats[k]),va='center')
    axes[0].set_xlim(0,max(cats.values())+5)
    precision=Counter(e['date_precision'] for e in events); keys=['day','month','unknown']
    axes[1].bar(keys,[precision[k] for k in keys],color=['#176a77','#bf8532','#bac8ce'])
    for i,k in enumerate(keys):axes[1].text(i,precision[k]+1,str(precision[k]),ha='center')
    axes[1].set_title('Event-date precision',loc='left');axes[1].set_ylim(0,90)
    fig.tight_layout();savefig(fig,'02_actions_dates')
    latest=verification['runs'][-1]; rows=latest['providers'];providers=['google-rss','tavily','exa','gdelt']
    ok=[sum(r['queries'] for r in rows if r['provider']==p and r['status']=='ok') for p in providers]
    failed=[sum(r['queries'] for r in rows if r['provider']==p and r['status']=='failed') for p in providers]
    skipped=[sum(r['queries'] for r in rows if r['provider']==p and r['status'].startswith('skipped')) for p in providers]
    fig,ax=plt.subplots(figsize=(9.3,3.5))
    ax.barh(providers,ok,color='#176a77',label='Completed');ax.barh(providers,failed,left=ok,color='#b14d3f',label='Failed')
    ax.barh(providers,skipped,left=[a+b for a,b in zip(ok,failed)],color='#bac8ce',label='Skipped after provider stop')
    ax.set_xlim(0,13);ax.set_xticks(range(0,13,2));ax.set_xlabel('Planned queries');ax.invert_yaxis()
    ax.set_title('Observed hosted run: partial collection',loc='left');ax.legend(loc='lower center',bbox_to_anchor=(.5,-.43),ncol=3,frameon=False)
    fig.tight_layout();savefig(fig,'03_provider_health')
    fig,ax=plt.subplots(figsize=(10,5));ax.set_xlim(0,10);ax.set_ylim(0,5);ax.axis('off')
    boxes=[(.1,3.7,'DISCOVER\nRSS, GDELT, Tavily, Exa'),(3.45,3.7,'RETAIN\nEvery provider observation'),(6.8,3.7,'IDENTIFY DOCUMENTS\nConservative URL identity'),
           (6.8,1.5,'REVIEW ACTIONS\nState, institution, stage, date'),(3.45,1.5,'APPROVE WITH EVIDENCE\nSources, reason, revision'),(.1,1.5,'PUBLISH SNAPSHOT\nEvents, sources, links')]
    for x,y,label in boxes:
        ax.add_patch(FancyBboxPatch((x,y),3,1,boxstyle='round,pad=0.04',facecolor='#eef4f5',edgecolor='#176a77'))
        ax.text(x+1.5,y+.5,label,ha='center',va='center',fontsize=10,linespacing=1.6)
    for a,b in [((3.15,4.2),(3.4,4.2)),((6.5,4.2),(6.75,4.2)),((8.3,3.65),(8.3,2.55)),((6.75,2),(6.5,2)),((3.4,2),(3.15,2))]:
        ax.annotate('',xy=b,xytext=a,arrowprops=dict(arrowstyle='->',color='#176a77',lw=2))
    ax.text(5,.65,'SQLite history, query checkpoints, immutable observations and revision-checked reviews',ha='center',fontsize=10)
    ax.text(5,.15,'Matching proposes pairs. It cannot approve an event or merge government actions automatically.',ha='center',fontsize=10)
    fig.tight_layout();savefig(fig,'04_data_flow')
    dump(FIG/'figure_data.json',{'reviewed_events':len(events),'state_counts':dict(zip(states,total)),
        'primary_attached':dict(zip(states,primary)),'categories':dict(cats),'date_precision':dict(precision),
        'provider_health':rows,'run_id':latest['id'],'source_files':['data/events.csv','runs/durable-system-verification.json']})
    (FIG/'README.md').write_text('# Figure sources\n\nReproduce with `python build_submission.py`. PNG files are for documents; SVG files preserve editable vectors. Values are in figure_data.json.\n\n01: Selected coverage, alphabetical state order. Primary attachment does not verify every claim.\n02: Action categories and date precision, not policy effectiveness.\n03: One observed hosted run, not a provider reliability benchmark. 34 of its 36 completed queries hit their result cap.\n04: System flow; reviewer approval is separate from retrieval and document matching.\n',encoding='utf-8')

def dataset(events,sources,links):
    HF.mkdir(exist_ok=True)
    shutil.copy2(ROOT/'data/events.csv',HF/'reviewed_events.csv')
    metadata=[{k:v for k,v in s.items() if k not in ['evidence_excerpt','evidence_summary']} for s in sources]
    associations=[{k:r[k] for k in ['event_id','source_id','merge_reason']} for r in links]
    for name,rows in [('source_documents.csv',metadata),('event_sources.csv',associations)]:
        with (HF/name).open('w',encoding='utf-8',newline='') as f:
            writer=csv.DictWriter(f,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)
    (HF/'reviewed_events.jsonl').write_text(''.join(json.dumps({**e,'source_ids':json.loads(e['source_ids']),
        'source_count':int(e['source_count']),'has_primary_source':e['has_primary_source']=='True'},ensure_ascii=False)+'\n' for e in events),encoding='utf-8')
    shutil.copy2(ROOT/'docs/METHODOLOGY.md',HF/'METHODOLOGY.md')
    shutil.copy2(ROOT/'docs/NORMALIZATION.md',HF/'NORMALIZATION.md')
    definitions={'id':'Stable event identifier; not a date encoding','state':'Canonical Indian state',
      'title':'Reviewed action headline','date':'Event date: ISO day, month or year; empty means unknown',
      'date_precision':'day, month, year or unknown','date_basis':'Evidence and reasoning for event date',
      'publication_date':'Publication date of selected reporting source, not event date',
      'source_name':'Publisher of selected reporting source','source_url':'URL of selected reporting source',
      'summary':'Original analytical summary of the supported action','category':'Principal action category',
      'stage':'Evidence-supported milestone stage','initiative':'Reviewed grouping of related actions',
      'confidence':'Qualitative support, not a probability or impact score','limitations':'Record-specific uncertainty',
      'source_count':'Number of linked documents, not independent witnesses','has_primary_source':'At least one primary document attached',
      'source_ids':'JSON array of source IDs in CSV; native array in JSONL'}
    dump(HF/'data_dictionary.json',{'reviewed_events':definitions,'source_documents':{
        'id':'Source primary key','url':'Original source URL','publisher':'Publisher or issuing body',
        'title':'Original source title','published_date':'Source publication date, if known',
        'accessed_date':'Research retrieval date','source_type':'Evidence classification',
        'retrieval_status':'Recorded research retrieval outcome','updated_date':'Separate update date if known',
        'retrieval_method':'Recorded retrieval method, if supplied','date_conflict':'Documented date discrepancy, if any'},
        'event_sources':{'event_id':'Foreign key to reviewed_events.id','source_id':'Foreign key to source_documents.id',
            'merge_reason':'Reason for evidence association; not a duplicate classification'},
        'null_policy':'Empty CSV fields mean missing/not recorded. Unknown event dates require date_precision=unknown.'})
    card='''---
pretty_name: Indian State AI Policy Observatory
language:
- en
size_categories:
- n<1K
tags:
- india
- public-policy
- artificial-intelligence
configs:
- config_name: reviewed_events
  default: true
  data_files:
  - split: records
    path: reviewed_events.csv
- config_name: source_documents
  data_files:
  - split: records
    path: source_documents.csv
- config_name: event_sources
  data_files:
  - split: records
    path: event_sources.csv
---
# Indian State AI Policy Observatory

85 reviewed government-action milestones across 12 Indian states, supported by 113 source documents and 137 event-source associations. Research window: 2024-01-01 through 2026-11-10. The `records` split is a table label, not a model-training or evaluation split.

## Unit and scope

An event is a separately documented state-government action. Approvals, signings and later launches remain distinct. The purposive state sample is Andhra Pradesh, Assam, Gujarat, Karnataka, Kerala, Madhya Pradesh, Maharashtra, Odisha, Rajasthan, Tamil Nadu, Telangana and Uttar Pradesh. It is not exhaustive or representative. Do not rank state performance from record counts.

## Creation and evidence

The reviewed corpus was assembled through source research and adjudication, then validated and exported by a deterministic Python build. It was not generated by automatically accepting news-search results. Government orders, gazettes, budgets and departmental documents are preferred when relevant; attributed reporting supplies additional evidence. Source IDs join the tables. The full research package retains short supporting excerpts; this upload package omits excerpts and article bodies from the source table.

## Dates, missing values and duplicates

Dates represent government actions, not collection time. There are 78 day-precision, three month-precision and four unknown dates. Empty CSV values are missing, never zero. `date_precision` and `date_basis` preserve uncertainty. See NORMALIZATION.md for parsing rules and METHODOLOGY.md for inclusion and deduplication decisions. Event-source associations are not a count of removed duplicates or independent witnesses.

## Use and limits

Use this dataset for source-linked policy exploration and methods inspection. Do not use it as a complete census, impact evaluation, spending total, legal compliance determination or supervised deduplication benchmark. English-web and accessible-document selection introduces coverage bias. Primary attachment does not prove every claim. An announcement does not establish implementation.

## Rights and distribution

No blanket open license is asserted over publisher titles, source metadata or other third-party material. Original source rights remain with their holders. The project includes original analytical summaries and attribution. Assess rights for your intended reuse; no unrestricted model-training license is implied. The metadata deliberately omits an unsupported license label.

## Files and reproducibility

`reviewed_events.csv` and `reviewed_events.jsonl` contain the same events. `source_documents.csv` contains source metadata. `event_sources.csv` joins the tables. `data_dictionary.json` explains every field. `MANIFEST.json` stores SHA-256 hashes. Rebuild with `python pipeline.py build` followed by `python build_submission.py` in the source repository.

Dashboard: https://vishnu0906.github.io/state-ai-policy-observatory/

Source: https://github.com/VISHNU0906/state-ai-policy-observatory

Suggested attribution: Vishnu Kosuri, State AI Policy Observatory, research snapshot 10 November 2026; cite the exact repository commit and source URLs used.

## Upload

Create a dataset repository in your Hugging Face account. Upload this folder's contents at the repository root. Preserve README.md and the relative CSV paths so each table appears as a separate configuration. Check the preview and row counts after upload. This prepared folder has not itself been uploaded to Hugging Face.

Format references: [dataset cards](https://huggingface.co/docs/hub/datasets-cards) and [configuration](https://huggingface.co/docs/hub/datasets-manual-configuration), checked 10 November 2026.
'''
    (HF/'README.md').write_text(card,encoding='utf-8')
    dump(HF/'MANIFEST.json',{'research_cutoff':'2026-11-10','counts':{'events':len(events),'sources':len(sources),'links':len(links)},
        'files':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(HF.iterdir()) if p.is_file() and p.name!='MANIFEST.json'}})

SECTIONS=[
('Work Test Submission SAFL Vishnu Kosuri',[
('p','AI-related policy activity across Indian states | Research cutoff: 10 November 2026'),
('p','The project records 85 reviewed government-action milestones across 12 states, with 113 source documents and 137 event-source associations. It combines a source-linked research dataset with a persistent collection system. New search results remain unverified candidates until their government action, state, date and evidence have been reviewed.'),
('p','Live dashboard: '+SITE),('p','Public source and commit history: '+REPO),
('h','What is delivered'),
('p','The submission folder contains the reviewed CSV and JSON data, source and association tables, a runnable source ZIP, a Git history bundle, an offline dashboard, three research reports, this technical submission, figures with underlying values, a persistent database checkpoint, and a Hugging Face upload-ready dataset folder. START_HERE.md is the file index.'),
('h','Research scope'),
('p','The window is 1 January 2024 through 10 November 2026. The 12 states cover southern, western, northern, central, eastern and northeastern cases. Selection favours verifiable government actions and varied administrative routes: policies, budgets, institutions, agreements, public services and safeguards. Every state has at least six reviewed records. The sample supports comparisons of documented approaches, not state rankings or national prevalence estimates.'),
('h','The key design decision'),
('p','Keep provider observations, source documents and government events separate. Ten outlets can report one signing. One article can describe three separate agreements. Treating either an article URL or a similar headline as event identity loses those distinctions.'),
('fig','04_data_flow')]),
('1. Research design and evidence',[
('p','Include a record when the evidence identifies an AI-related action and a state-government institution, department, public authority, state university or specific state commitment. Exclude Union-only announcements without a state action, private launches without a documented state role, unsupported snippets, generic digitisation and out-of-window actions. AI must mean artificial intelligence in context; some Assam results use it for artificial insemination.'),
('p','The initial corpus comes from six versioned research inputs. Exa and Tavily supported targeted discovery and retrieval; official orders, budgets, gazettes, departmental publications and attributable news reports support the records. Firecrawl was attempted during research but the connected account had exhausted credits. A retrieved snippet is a lead, not sufficient evidence.'),
('fig','01_state_coverage'),
('p','A primary-source flag means a primary document is attached. It does not certify every statement or date. Syndicated reports can repeat the same briefing, so source counts are not independent confirmations.'),
('h','Interpretation'),
('p','Approval establishes a decision; signing establishes an agreement; launch establishes public introduction; operational status requires evidence of actual use. None alone proves accuracy, fairness, adoption or public benefit. Do not sum programme envelopes, annual budgets, tender estimates, private investment and actual spending.')]),
('2. Collection and recovery',[
('p','Google News RSS supplies free news discovery. GDELT is a second free discovery channel, but provider-seen timestamps are not publication dates. Tavily and Exa add optional search coverage through encrypted repository secrets. GNews API, NewsAPI and Crustdata adapters are available but require suitable credentials and plan terms. Google News RSS and GNews API are different services. Optional extraction uses local Trafilatura for HTML and pypdf for PDFs; hosted extraction must be explicitly selected.'),
('p','The scheduled GitHub Actions workflow runs daily at 02:17 UTC, or 07:47 IST, on a best-effort schedule. Each planned query is saved before the request. Each completed query commits its observations. Failed, skipped and capped queries remain visible. Keyed request attempts reserve from persistent monthly limits before dispatch; failures count. These controls limit this workflow, not all activity or billing in a provider account.'),
('p','SQLite stores immutable observations, query status, review decisions, source links and import versions. Public data-history snapshots use compressed, content-addressed 64 KiB blocks and a checksum manifest. Restore failures stop collection. Concurrent remote changes prevent overwrite. The system does not depend on expiring Actions artifacts to preserve history or request budgets.'),
('fig','03_provider_health'),
('p','The latest verified hosted run returned 358 observations across 328 distinct document URLs. It completed 36 queries; 34 reached the configured result cap. GDELT failed once and its 11 remaining queries were skipped. The workflow finished successfully while the data run correctly remained partial. This is an observed run, not a long-run reliability benchmark.'),
('p','A deliberate interruption retained 188 observations and eight request reservations. Recovery resumed 17 unfinished queries; the final audit found none unfinished. Details and run links are in docs/RELEASE.md and runs/durable-system-verification.json.')]),
('3. Normalization and sorting',[
('p','State normalization applies Unicode NFKC, whitespace cleanup, case folding and explicit aliases to structured state fields. U.P. and Uttar-Pradesh become Uttar Pradesh; Telengana becomes Telangana; Orissa becomes Odisha. Curated typo mappings are auditable. Other near matches produce suggestions only. An occurrence of the word up in article text does not identify Uttar Pradesh. Non-Latin transliteration is not implemented.'),
('p','The review helper returns raw input, normalized value, method and status. It accepts valid ISO dates, English named months, ordinal day forms and timezone-aware ISO or RFC 2822 timestamps. For timestamps describing an instant, conversion to IST is explicit. A date printed on an order remains a calendar date.'),
('p','02/03/2025 stays ambiguous unless the source convention declares day-first or month-first. 13/02/2025 is unambiguous. Yesterday needs an explicit source-date anchor. Early 2025, approximate dates and date ranges remain unresolved for review. Invalid dates, including 29 February in a non-leap year, are not accepted. Missing markers become unknown values.'),
('fig','02_actions_dates'),
('p','A month-only date stays YYYY-MM and a year-only date stays YYYY. Lower and upper bounds support sorting and filtering without pretending an exact action day is known. Known lower bounds sort newest first; narrower precision breaks ties, followed by state and stable ID. Unknown dates sort last. Python and dashboard tests verify this ordering.'),
('p','The new helper is available for review-time use; it does not retroactively rewrite the 85 reviewed events. Provider publication estimates, retrieval timestamps and event dates remain distinct. Full examples, commands and limits are in docs/NORMALIZATION.md.')]),
('4. Deduplication and review controls',[
('p','The first layer identifies repeated document URLs conservatively: lowercase hosts, remove fragments and known tracking parameters, preserve document IDs and meaningful query values. Google News redirects remain separate from publisher URLs until verified. Every durable provider/query observation remains stored even when its document identity is shared.'),
('p','The second layer proposes related document pairs using title-token inverse-frequency weights, cosine similarity and token overlap. Stage, reversal and numeric conflicts are recorded as warnings. Suggestions cannot merge documents into approved events. At threshold 0.45, a 34-pair development diagnostic retrieves 3 of 12 positive pairs and also suggests 6 of 22 distinct pairs: precision 0.333, recall 0.25. This weak result is reported rather than presented as production accuracy.'),
('h','Worked event boundaries'),
('p','Uttar Pradesh has separate AI mission announcement, budget and cabinet approval records. Similar mission wording does not make those actions duplicates. Madhya Pradesh has separate AI-lab, BHASHINI and proposed-centre agreements even when a conference account discusses several together. Odisha policy notification and later operational rules are separate milestones. Repeated reports of the same signing attach to one reviewed action.'),
('p','An event decision checks state, responsible body, counterparty, initiative, action, stage and date together. A changed amount, cancelled tender or later rollout must not be absorbed by title similarity. Where the evidence does not support finer instrument boundaries, retain an explicitly qualified grouped record rather than inventing agreements.'),
('h','Companion dataset integration'),
('p','The current external snapshot contributes 543 proposals across 13 states and 1,076 source links. These remain proposals, not additions to the 85-event release. The audit found 977 source links still using Google redirect URLs, two literal backspace characters in a reversal pattern, and 31 shared headlines across the external evaluation halves. These defects weaken claims of clean URLs and independent evaluation.'),
('p','Imports are frozen by content hash and repeated imports do not erase decisions. Reviewer actions require a reason and expected revision. Manual event merges preserve evidence and the superseded ID; guarded restoration can undo them. The published dashboard remains built from reviewed research JSON, so new database approval requires an explicit release reconciliation before publication.')]),
('5. Reproduction, limits and submission map',[
('h','Run the project'),
('p','Extract state-ai-policy-source.zip. With Python 3.11 or later, run python -m unittest discover -s tests -v, then python pipeline.py build. Serve dist with python -m http.server 8765 --directory dist. The static dashboard can also open offline. Run node tests/test_dashboard_sort.js for the browser ordering check. API keys are unnecessary for the frozen build and tests.'),
('p','Optional report and figure regeneration uses matplotlib and ReportLab through build_submission.py. Local article extraction has separate requirements-extraction.txt dependencies. The source Git bundle preserves development history; the database checkpoint preserves candidate state and export tables. SHA-256 manifests identify file contents.'),
('h','Validation and limits'),
('p','Tests cover repeat-safe imports, failed-transaction rollback, immutable audit rows, review revision conflicts, source references, rejection persistence, merge restoration, interrupted-run recovery, request limits, history corruption, concurrent updates, date ordering and normalization. Tests demonstrate those behaviours, not factual completeness of the internet corpus.'),
('p','Current limits include predominantly English-web evidence, incomplete regional-language discovery, unresolved Google redirects, no scanned-PDF OCR, no comprehensive browser-rendered extraction, result caps, and no measured corpus-wide recall. Title matching is unsuitable for automatic event merging. A single successful extraction is not proof of relevance. No API fallback is treated as a guarantee of free account-wide use.'),
('h','Files for review'),
('p','data/events.csv is the submission dataset. data/sources.csv and data/source_observations.csv provide evidence and joins. reports/Rationale.pdf is the one-page rationale. reports/Research_Report.pdf interprets the state evidence. reports/Collection_Architecture.pdf compares collection options. reports/Technical_Submission.pdf is this document. figures/ contains editable SVG and PNG charts with values. huggingface_dataset/ is ready to upload, with separate event, source and association configurations.'),
('p','The Hugging Face package excludes source excerpts and full article bodies. No blanket third-party content license is asserted. Its dataset card explains scope, missingness, joins, limitations and rights. It has not been uploaded automatically.'),
('h','Final handover'),
('p','Upload the complete release directory to Drive and add the resulting folder link to the submission copy. The native Google Doc contains the same technical account and public project links. Confirm the reviewer access and copy settings required by the assignment before submitting its link in ClassMarker. Creating this package does not submit the work or notify a hiring contact.')])]

def report():
    OUT.mkdir(exist_ok=True)
    styles=getSampleStyleSheet()
    styles.add(ParagraphStyle(name='ReportBody',fontName='Helvetica',fontSize=9.3,leading=13,spaceAfter=8,textColor=colors.HexColor('#172934')))
    styles.add(ParagraphStyle(name='ReportHeading',fontName='Helvetica-Bold',fontSize=17,leading=21,spaceAfter=14))
    styles.add(ParagraphStyle(name='ReportSub',fontName='Helvetica-Bold',fontSize=11,leading=14,spaceBefore=5,spaceAfter=6))
    story=[];md=[];web=['<!doctype html><meta charset="utf-8"><title>Work Test Submission SAFL Vishnu Kosuri</title>',
        '<style>body{font:11pt Arial;max-width:760px;margin:48px auto;line-height:1.45;color:#172934}h1{font-size:20pt}h2{font-size:13pt}img{max-width:100%}section{page-break-after:always}a{color:#176a77}</style>']
    for i,(title,items) in enumerate(SECTIONS):
        if i:story.append(PageBreak())
        story.append(Paragraph(html.escape(title),styles['ReportHeading']));md.extend(['# '+title,'']);web.append('<section><h1>'+html.escape(title)+'</h1>')
        for kind,text in items:
            if kind=='fig':
                path=FIG/(text+'.png')
                from PIL import Image as PILImage
                with PILImage.open(path) as im:w,h=im.size
                width=490;story.append(Image(str(path),width=width,height=width*h/w));story.append(Spacer(1,9))
                md.extend(['![Figure](../output/figures/'+text+'.png)','']);web.append('<img src="figures/'+text+'.png">')
            else:
                story.append(Paragraph(html.escape(text),styles['ReportSub' if kind=='h' else 'ReportBody']))
                md.extend([('## ' if kind=='h' else '')+text,'']);tag='h2' if kind=='h' else 'p';web.append('<'+tag+'>'+html.escape(text)+'</'+tag+'>')
        web.append('</section>')
    def footer(canvas,doc):
        canvas.setFont('Helvetica',8);canvas.setFillColor(colors.HexColor('#596770'))
        canvas.drawString(42,25,'State AI Policy Observatory | 10 November 2026');canvas.drawRightString(A4[0]-42,25,str(doc.page))
    SimpleDocTemplate(str(OUT/'Technical_Submission.pdf'),pagesize=A4,rightMargin=42,leftMargin=42,topMargin=38,bottomMargin=42,
        title='Work Test Submission SAFL Vishnu Kosuri',author='Vishnu Kosuri').build(story,onFirstPage=footer,onLaterPages=footer)
    (ROOT/'docs/SUBMISSION.md').write_text('\n'.join(md),encoding='utf-8')
    (OUT/'Technical_Submission.html').write_text('\n'.join(web),encoding='utf-8')
    dump(OUT/'submission_sections.json',SECTIONS)

def main():
    events=read_csv(ROOT/'data/events.csv');sources=read_csv(ROOT/'data/sources.csv');links=read_csv(ROOT/'data/source_observations.csv')
    assert len({e['id'] for e in events})==85 and len(sources)==113 and len(links)==137
    event_ids={e['id'] for e in events};source_ids={s['id'] for s in sources}
    assert all(r['event_id'] in event_ids and r['source_id'] in source_ids for r in links)
    figures(events,json.loads((ROOT/'runs/durable-system-verification.json').read_text(encoding='utf-8')))
    dataset(events,sources,links);report()
    dump(ROOT/'data/normalization_examples.json',{'states':[normalize_state(x) for x in ['U.P.','Uttar-Pradesh','Telengana','Maharastra','Karnatakaa']],
        'dates':[normalize_date(x) for x in ['March 2025','02/03/2025','13/02/2025','early 2025','2025-02-29','2025-01-01T22:00:00Z',None]]})
    print(json.dumps({'events':len(events),'sources':len(sources),'links':len(links),'figures':4,'report':str(OUT/'Technical_Submission.pdf'),'dataset':str(HF)},indent=2))

if __name__=='__main__':main()
