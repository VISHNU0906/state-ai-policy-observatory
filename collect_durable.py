"""Resumable bounded collection. Each query commits all observations before continuing."""
import argparse
import json
import os
import time
import uuid
from datetime import date, timedelta
from pathlib import Path

import collectors
from ledger import DEFAULT_DB, Ledger, digest, encoded, now
from pipeline import STATES, ROOT

PROVIDERS = ['google-rss','gdelt',*collectors.KEYS]


def request_spec(provider,state,start,end,limit):
    query = collectors.news_query(state)
    if provider == 'exa':
        query = state + ' state government artificial intelligence policy mission deployment'
    elif provider == 'google-rss':
        query += f' after:{start} before:{end}'
    limit = min(limit,{'tavily':20,'exa':10,'gnews':10,'gdelt':250,'newsapi':100}.get(provider,limit))
    return {'provider':provider,'state':state,'query':query,'start':start,'end':end,'limit':limit,
            'boundary_note':'Stored calendar bounds; provider-specific endpoint inclusion may differ. Windows overlap on repeat runs.',
            'pagination':'bounded first response; saturation triggers interval splitting when enabled'}


def plan(store,providers,states,start,end,limit,max_calls,split=False):
    run_id = str(uuid.uuid4())
    params = {'providers':providers,'states':states,'start':start,'end':end,'limit':limit,'max_calls':max_calls,'split':split}
    with store.transaction():
        store.db.execute('INSERT INTO runs VALUES (?,?,NULL,?,?)',(run_id,now(),'running',encoded(params)))
        for provider in providers:
            for state in states:
                add_query(store,run_id,request_spec(provider,state,start,end,limit))
    return run_id


def add_query(store,run_id,spec,parent=None):
    qid = 'query-' + digest([run_id,spec])
    store.db.execute('INSERT OR IGNORE INTO queries VALUES (?,?,?,?,?,?,?,?,?,?,?,?)',
        (qid,run_id,spec['provider'],spec['state'],spec['query'],spec['start'],spec['end'],'planned',None,0,None,encoded({**spec,'parent':parent})))
    return qid


def execute(store,run_id,discover=collectors.discover,checkpoint=None,pause=time.sleep):
    run = store.db.execute('SELECT * FROM runs WHERE id=?',(run_id,)).fetchone()
    if run is None:
        raise ValueError('Unknown run')
    params = json.loads(run['parameters'])
    if run['status'] == 'complete':
        return summary(store,run_id)
    # Only unfinished requests resume. Failed/skipped queries remain explicit gaps in this run.
    with store.transaction():
        store.db.execute("UPDATE queries SET status='planned',error='interrupted_before_commit' WHERE run_id=? AND status='running'",(run_id,))
        store.db.execute("UPDATE runs SET status='running',finished_at=NULL WHERE id=?",(run_id,))
    for provider in params['providers']:
        stop_reason = None
        while True:
            row = store.db.execute("SELECT * FROM queries WHERE run_id=? AND provider=? AND status='planned' ORDER BY rowid LIMIT 1",(run_id,provider)).fetchone()
            if row is None:break
            spec=json.loads(row['metadata']);qid=row['id']
            used=store.db.execute("SELECT count(*) FROM queries WHERE run_id=? AND provider=? AND status IN ('ok','failed','running')",(run_id,provider)).fetchone()[0]
            skip = stop_reason
            if provider in collectors.KEYS and not os.environ.get(collectors.KEYS[provider]):skip='missing_key'
            if used >= params['max_calls']:skip='query_budget'
            if skip:
                with store.transaction():
                    store.db.execute("UPDATE queries SET status=?,error=? WHERE id=?",('skipped_'+skip,skip,qid))
                continue
            with store.transaction():store.db.execute("UPDATE queries SET status='running' WHERE id=?",(qid,))

            def reserve(p):
                store.reserve_attempt(qid,p,int(os.environ.get(p.upper()+'_MONTHLY_REQUEST_CAP','720')))
                # Optional durable remote checkpoint occurs BEFORE paid request, including retries.
                if checkpoint:checkpoint(store)

            previous=collectors.ATTEMPT_RESERVER
            collectors.ATTEMPT_RESERVER=reserve
            try:
                rows=discover(provider,row['state'],row['window_start'],row['window_end'],spec['limit'])
                if not isinstance(rows,list):raise ValueError('adapter_result_not_list')
                stamp=now()
                with store.transaction():
                    for item in rows:
                        store._observe({**item,'provider':provider,'query_state':row['state'],'submitted_query':row['query']},stamp,query_id=qid)
                    capped=len(rows)>=spec['limit']
                    store.db.execute("UPDATE queries SET status='ok',result_count=?,capped=?,error=NULL WHERE id=?",(len(rows),int(capped),qid))
                    if capped and params.get('split'):
                        start=date.fromisoformat(row['window_start']);end=date.fromisoformat(row['window_end'])
                        if (end-start).days>1:
                            middle=start+timedelta(days=(end-start).days//2)
                            for left,right in [(start,middle),(middle,end)]:
                                add_query(store,run_id,request_spec(provider,row['state'],str(left),str(right),spec['limit']),qid)
            except Exception as ex:
                # Never persist server bodies, credential URLs, or arbitrary exception strings.
                error=str(ex) if isinstance(ex,RuntimeError) and str(ex).startswith(('HTTP ','missing_key','local_monthly_','Network failure')) else type(ex).__name__
                with store.transaction():store.db.execute("UPDATE queries SET status='failed',error=? WHERE id=?",(error,qid))
                if any(code in error for code in ['401','402','403','429','request_cap']):stop_reason='provider_stopped'
            finally:
                collectors.ATTEMPT_RESERVER=previous
            if checkpoint:checkpoint(store)
            if provider in ['gdelt','crustdata']:pause(6)
        if checkpoint:checkpoint(store)
    result=summary(store,run_id)
    status='complete' if result['successful_queries']==result['queries'] else 'partial'
    with store.transaction():store.db.execute('UPDATE runs SET status=?,finished_at=? WHERE id=?',(status,now(),run_id))
    if checkpoint:checkpoint(store)
    return summary(store,run_id)


def summary(store,run_id):
    rows=[dict(r) for r in store.db.execute('SELECT * FROM queries WHERE run_id=? ORDER BY rowid',(run_id,))]
    return {'run_id':run_id,'queries':len(rows),'successful_queries':sum(r['status']=='ok' for r in rows),
            'potentially_truncated_queries':sum(r['capped'] for r in rows),'query_results':rows,
            'note':'Successful bounded queries do not establish complete coverage. No candidates are approved automatically.'}


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--db',type=Path,default=DEFAULT_DB)
    p.add_argument('--providers',default='google-rss,gdelt,tavily,exa')
    p.add_argument('--states',default=','.join(STATES));p.add_argument('--days',type=int,default=7)
    p.add_argument('--start');p.add_argument('--end');p.add_argument('--limit',type=int,default=10)
    p.add_argument('--max-calls',type=int,default=12);p.add_argument('--split-saturated',action='store_true')
    p.add_argument('--resume');p.add_argument('--output-dir',type=Path,default=ROOT/'scheduled-runs')
    p.add_argument('--resume-unfinished',action='store_true',help='Recover interrupted runs before planning the current window')
    p.add_argument('--checkpoint-command',nargs='+',help='Explicit argv invoked after durable backup; no shell interpretation')
    args=p.parse_args()
    providers=list(dict.fromkeys(args.providers.split(',')));states=list(dict.fromkeys(args.states.split(',')))
    if any(v not in PROVIDERS for v in providers) or any(v not in STATES for v in states):p.error('Unknown provider/state')
    if not 1<=args.limit<=100 or not 1<=args.max_calls<=100 or not 1<=args.days<=366:p.error('Invalid bounds')
    end=date.fromisoformat(args.end) if args.end else date.fromisoformat(now()[:10])
    # NewsAPI/GNews free plans can lag. Use an explicit older --end when enabling those plans.
    start=date.fromisoformat(args.start) if args.start else end-timedelta(days=args.days)
    if start>=end:p.error('start must precede exclusive end')
    checkpoint=None
    if args.checkpoint_command:
        import subprocess
        checkpoint=lambda store:subprocess.run(args.checkpoint_command,check=True)
    with Ledger(args.db) as store:
        if args.resume_unfinished:
            unfinished=[r[0] for r in store.db.execute("SELECT id FROM runs WHERE status='running' ORDER BY started_at")]
            for prior in unfinished:execute(store,prior,checkpoint=checkpoint)
        run_id=args.resume or plan(store,providers,states,str(start),str(end),args.limit,args.max_calls,args.split_saturated)
        args.output_dir.mkdir(parents=True,exist_ok=True)
        print('run_id='+run_id,flush=True)
        result=execute(store,run_id,checkpoint=checkpoint)
        (args.output_dir/(run_id+'.json')).write_text(json.dumps(result,indent=2),encoding='utf-8')
        print(json.dumps({k:v for k,v in result.items() if k!='query_results'},indent=2))
        if not result['successful_queries']:raise SystemExit('No query succeeded; failure ledger retained')


if __name__=='__main__':main()
