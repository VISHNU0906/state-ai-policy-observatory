"""Read-only tracker snapshot with a change report. No external code is executed."""
import argparse
import csv
import io
import json
from pathlib import Path

from ledger import ROOT,DEFAULT_DB,Ledger,digest,now


def snapshot(source,destination):
    source=Path(source);destination=Path(destination)
    required=['data/out/records.csv','data/out/record_sources.csv','data/out/rejected.csv']
    optional=['data/review/dedup_pairs.csv','data/review/review_notes_draft.csv','data/review/overrides.csv',
              'pipeline/dedupe.py','scripts/eval_dedupe.py','README.md']
    paths=required+[p for p in optional if (source/p).exists()]
    content={p:(source/p).read_bytes() for p in paths}
    if any((source/p).read_bytes()!=raw for p,raw in content.items()):
        raise RuntimeError('Tracker changed while reading. No partial snapshot saved; retry after its build.')
    sha=digest({p:digest(raw) for p,raw in content.items()})
    folder=destination/sha
    folder.mkdir(parents=True,exist_ok=True)
    for name,raw in content.items():
        target=folder/name;target.parent.mkdir(parents=True,exist_ok=True)
        if target.exists() and target.read_bytes()!=raw:raise RuntimeError('Snapshot collision')
        target.write_bytes(raw)
    read=lambda name:list(csv.DictReader(io.StringIO(content[name].decode('utf-8-sig'))))
    records=read(required[0]);sources=read(required[1]);rejected=read(required[2])
    ref=set(r['record_id'] for r in records)
    dangling=sorted({r['record_id'] for r in sources}-ref)
    if dangling:raise ValueError('Tracker snapshot has dangling source links; retry after build')
    label_report={}
    if 'data/review/dedup_pairs.csv' in content:
        pairs=read('data/review/dedup_pairs.csv')
        half=lambda rows:{(r['state'],r['date_'+side],r['title_'+side]) for r in rows for side in ['a','b']}
        label_report={'pairs':len(pairs),'shared_headlines_across_even_odd_halves':len(half(pairs[::2])&half(pairs[1::2])),
                      'interpretation':'Shared documents mean this is not an independent document-level holdout. Labels and test-selection history require separate review.'}
    from urllib.parse import urlsplit
    report={'snapshot_sha256':sha,'observed_at':now(),'source_directory':str(source),'snapshot_directory':str(folder),
            'files':{p:digest(raw) for p,raw in content.items()},'records':len(records),'source_links':len(sources),'rejected':len(rejected),
            'proposed_states':dict(sorted(__import__('collections').Counter(r['state'] for r in records).items())),
            'source_link_aggregator_count':sum(urlsplit(r['link']).hostname=='news.google.com' for r in sources),
            'representative_aggregator_count':sum(urlsplit(r['source_url']).hostname=='news.google.com' for r in records),
            'dedup_evaluation':label_report,
            'dedupe_literal_backspace_bytes':content.get('pipeline/dedupe.py',b'').count(bytes([8])),
            'review_boundary':'All external records are imported as proposals, regardless of the external review label. Report dates do not become event dates.'}
    prior=destination/'LATEST.json'
    if prior.exists():
        old=json.loads(prior.read_text(encoding='utf-8'))
        report['previous_snapshot']=old['snapshot_sha256']
        report['count_changes']={k:report[k]-old[k] for k in ['records','source_links','rejected']}
    (folder/'snapshot.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    prior.write_text(json.dumps(report,indent=2),encoding='utf-8')
    return report


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('source',type=Path);p.add_argument('--db',type=Path,default=DEFAULT_DB)
    p.add_argument('--destination',type=Path,default=ROOT/'imports/tracker')
    args=p.parse_args()
    report=snapshot(args.source,args.destination)
    with Ledger(args.db) as store:
        report['new_import']=store.import_tracker(Path(report['snapshot_directory'])/'data/out')
        report['new_representative_import']=store.import_tracker_representatives(Path(report['snapshot_directory'])/'data/out')
    public={k:v for k,v in report.items() if k not in ['source_directory','snapshot_directory']}
    (ROOT/'data/tracker_integration_audit.json').write_text(json.dumps(public,indent=2),encoding='utf-8')
    print(json.dumps({k:v for k,v in report.items() if k!='files'},indent=2))


if __name__=='__main__':main()
