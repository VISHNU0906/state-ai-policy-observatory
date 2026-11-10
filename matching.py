"""Explainable document-pair review queue. Similarity never assigns an event ID."""
import argparse
import json
import math
import re
from collections import Counter
from pathlib import Path

from ledger import DEFAULT_DB, Ledger, ROOT, digest, encoded

RULE_VERSION = 'title-review-v1'
STOP = set('a an and as at be by for from in into is it of on or the to with will govt government state states india indian ai artificial intelligence chief minister new first says said'.split())
ALIASES = {'agreement':'mou','agreements':'mou','pact':'mou','memorandum':'mou','centre':'center','centres':'center','centers':'center','varsity':'university','crores':'crore'}
REVERSAL = re.compile(r'\b(cancel\w*|scrapp?\w*|revok\w*|withdraw\w*|suspend\w*|terminat\w*|quash\w*|roll(?:s|ed)? back)\b',re.I)
STAGES = {'signed':r'\b(signs?|signed|inks?|inked|mou|pact)\b',
          'approved':r'\b(approv\w*|cabinet nod|clears?)\b',
          'launched':r'\b(launch\w*|inaugurat\w*)\b',
          'proposed':r'\b(plans?|propos\w*|to set up)\b'}


def tokens(title):
    # Keep decimal amounts intact; 122.6 must not become 122.
    raw=re.findall(r'\d+(?:[,.]\d+)*|[^\W\d_]{2,}',title.casefold(),re.UNICODE)
    return set(ALIASES.get(t,t) for t in raw if t not in STOP)


class Matcher:
    def __init__(self,titles):
        groups=[tokens(t) for t in titles]
        counts=Counter(token for group in groups for token in group)
        self.idf={token:1+math.log((1+len(groups))/(1+count)) for token,count in counts.items()}

    def compare(self,left,right):
        a=tokens(left);b=tokens(right);shared=a&b
        weight=lambda ts:sum(self.idf.get(t,1)**2 for t in ts)
        wa=weight(a);wb=weight(b);ws=weight(shared)
        score=.5*ws/math.sqrt(wa*wb)+.5*ws/min(wa,wb) if wa and wb else 0
        left_stages={s for s,p in STAGES.items() if re.search(p,left,re.I)}
        right_stages={s for s,p in STAGES.items() if re.search(p,right,re.I)}
        warnings=[]
        if bool(REVERSAL.search(left)) != bool(REVERSAL.search(right)):warnings.append('reversal_milestone_conflict')
        if left_stages and right_stages and not left_stages&right_stages:warnings.append('different_stage_cues')
        nums=lambda ts:{t for t in ts if t[0].isdigit()}
        if nums(a) and nums(b) and nums(a)!=nums(b):warnings.append('different_numeric_claims')
        return {'score':round(score,6),'shared_tokens':sorted(shared),'left_stage_cues':sorted(left_stages),
                'right_stage_cues':sorted(right_stages),'warnings':warnings,'automatic_merge':False}


def queue(store,threshold=.45,max_pairs=10000):
    documents={}
    for row in store.db.execute('SELECT id,document_id,payload FROM sources ORDER BY id'):
        s=json.loads(row['payload']);documents.setdefault(row['document_id'],set()).add(s['title'])
    for row in store.db.execute('SELECT document_id,payload FROM observations ORDER BY id'):
        s=json.loads(row['payload'])
        if s.get('title'):documents.setdefault(row['document_id'],set()).add(s['title'])
    matcher=Matcher([t for values in documents.values() for t in sorted(values)])
    ids=sorted(documents);suggestions=[]
    # Inverted token index avoids comparing documents with no shared content tokens.
    index={}
    for key in ids:
        for token in set().union(*(tokens(t) for t in documents[key])):index.setdefault(token,set()).add(key)
    for left in ids:
        candidates=set().union(*(index[t] for title in documents[left] for t in tokens(title))) if documents[left] else set()
        for right in sorted(x for x in candidates if x>left):
            best=max((matcher.compare(a,b) for a in sorted(documents[left]) for b in sorted(documents[right])),key=lambda x:x['score'])
            if best['score']>=threshold:
                suggestions.append((left,right,best))
    suggestions.sort(key=lambda p:(-p[2]['score'],p[0],p[1]))
    with store.transaction():
        for left,right,features in suggestions[:max_pairs]:
            # Decisions survive score updates and rule-version changes. A reviewed pair is never reset.
            prior=store.db.execute("SELECT decision FROM matches WHERE left_id=? AND right_id=? AND decision<>'pending' ORDER BY rowid DESC LIMIT 1",(left,right)).fetchone()
            decision=prior[0] if prior else 'pending'
            store.db.execute('INSERT INTO matches(id,left_id,right_id,rule_version,features,decision) VALUES (?,?,?,?,?,?) '
                             'ON CONFLICT(left_id,right_id,rule_version) DO UPDATE SET features=excluded.features',
                             ('match-'+digest([left,right,RULE_VERSION]),left,right,RULE_VERSION,encoded(features),decision))
    return {'rule_version':RULE_VERSION,'documents':len(documents),'above_threshold_pairs':len(suggestions),
            'saved_limit':max_pairs,'threshold':threshold,'automatic_event_merges':0,
            'note':'Document similarity suggests reading both reports. Same document or similar title does not establish one event.'}


def decide(store,match_id,decision,reviewer,reason,revision):
    if decision not in ['same_event','distinct','uncertain','pending']:raise ValueError('Invalid match decision')
    with store.transaction():
        row=store.db.execute('SELECT * FROM matches WHERE id=?',(match_id,)).fetchone()
        if row is None or row['revision']!=revision:raise ValueError('Missing match or stale revision')
        store._action('match',match_id,reviewer,reason,dict(row),{'decision':decision,'revision':revision+1})
        store.db.execute('UPDATE matches SET decision=?,revision=revision+1 WHERE id=?',(decision,match_id))


def evaluate(threshold=.45):
    corpus=json.loads((ROOT/'data/events.json').read_text(encoding='utf-8'))
    sources={s['id']:s for s in corpus['sources']}
    labels=json.loads((ROOT/'evaluation/event_pairs.json').read_text(encoding='utf-8'))
    matcher=Matcher([sources[k]['title'] for k in sorted(sources)])
    results=[]
    for pair in labels['pairs']:
        if pair.get('label') not in ['same_event','different_event']:continue
        a=sources[pair['left']['source_id']];b=sources[pair['right']['source_id']]
        features=matcher.compare(a['title'],b['title'])
        results.append({'pair_id':pair['pair_id'],'label':pair['label'],'suggested':features['score']>=threshold,**features})
    tp=sum(r['suggested'] and r['label']=='same_event' for r in results)
    fp=sum(r['suggested'] and r['label']=='different_event' for r in results)
    positives=sum(r['label']=='same_event' for r in results)
    return {'rule_version':RULE_VERSION,'threshold':threshold,'labelled_pairs':len(results),'positive_pairs':positives,
            'suggested_true_pairs':tp,'suggested_distinct_pairs':fp,'suggestion_precision':tp/(tp+fp) if tp+fp else None,
            'suggestion_recall':tp/positives if positives else None,'results':results,
            'limitations':'Diagnostic development labels from research agents, pending independent human review. Not representative or held out. Uses source headlines only, no event IDs, summaries, shared event membership or label reasons as features. These are review-queue metrics, not automatic merge accuracy.'}


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--db',type=Path,default=DEFAULT_DB)
    p.add_argument('command',choices=['queue','evaluate','decide']);p.add_argument('--threshold',type=float,default=.45)
    p.add_argument('--match-id');p.add_argument('--decision');p.add_argument('--reviewer');p.add_argument('--reason');p.add_argument('--revision',type=int)
    args=p.parse_args()
    if not 0<=args.threshold<=1:p.error('Threshold must be 0..1')
    if args.command=='evaluate':
        result=evaluate(args.threshold)
        (ROOT/'evaluation/title_matching_results.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
        print(json.dumps({k:v for k,v in result.items() if k!='results'},indent=2));return
    with Ledger(args.db) as store:
        if args.command=='queue':result=queue(store,args.threshold)
        else:
            if any(v is None for v in [args.match_id,args.decision,args.reviewer,args.reason,args.revision]):p.error('Decision requires match-id, decision, reviewer, reason, revision')
            result=decide(store,args.match_id,args.decision,args.reviewer,args.reason,args.revision)
        print(json.dumps(result,indent=2))


if __name__=='__main__':main()
