"""Provider adapters. All output stays pending; API keys never enter saved logs."""
import argparse, hashlib, json, os, time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urlsplit
from urllib.request import Request, urlopen
from pipeline import ROOT, STATES, canonical_url, dump, fetch
import xml.etree.ElementTree as ET

KEYS={'tavily':'TAVILY_API_KEY','newsapi':'NEWSAPI_API_KEY','gnews':'GNEWS_API_KEY','exa':'EXA_API_KEY','crustdata':'CRUSTDATA_API_KEY'}
HOST_PROVIDERS={'api.tavily.com':'tavily','api.exa.ai':'exa','newsapi.org':'newsapi','gnews.io':'gnews','api.crustdata.com':'crustdata','api.firecrawl.dev':'firecrawl'}

def reserve_attempt(url):
    """Conservative monthly request limits, counting retries and failed attempts.

    These are local request caps, not a promise of free account-level billing.
    The scheduled job serializes runs and persists this file with Actions cache.
    """
    provider=HOST_PROVIDERS.get(urlsplit(url).hostname)
    if not provider:return
    cap=int(os.environ.get(provider.upper()+'_MONTHLY_REQUEST_CAP','720'))
    path=ROOT/'.cache'/'provider-usage.json'
    usage=json.loads(path.read_text()) if path.exists() else {}
    key=datetime.now(timezone.utc).strftime('%Y-%m')+':'+provider
    if usage.get(key,0)>=cap:raise RuntimeError('local_monthly_request_cap_reached')
    usage[key]=usage.get(key,0)+1
    path.parent.mkdir(parents=True,exist_ok=True);tmp=path.with_suffix('.tmp');tmp.write_text(json.dumps(usage,indent=2));tmp.replace(path)

def api(url,headers=None,body=None):
    headers={'User-Agent':'StateAIPolicyResearch/1.0',**(headers or {})}
    encoded=None
    if body is not None:encoded=json.dumps(body).encode();headers['Content-Type']='application/json'
    for attempt in range(3):
        reserve_attempt(url)
        try:
            with urlopen(Request(url,data=encoded,headers=headers),timeout=30) as r:
                raw=r.read(4_000_001)
                if len(raw)>4_000_000:raise ValueError('Response exceeds 4 MB cap')
                return json.loads(raw)
        except HTTPError as ex:
            # Do not print full URLs or server bodies that could echo credentials.
            if ex.code in (401,402,403):raise RuntimeError(f'HTTP {ex.code}; check key, plan or quota; no paid fallback') from None
            if attempt==2 or ex.code not in (429,500,502,503,504):raise RuntimeError(f'HTTP {ex.code}') from None
            time.sleep(2**attempt)
        except (URLError,TimeoutError):
            if attempt==2:raise RuntimeError('Network failure after retries') from None
            time.sleep(2**attempt)

def news_query(state):return f'"{state}" ("artificial intelligence" OR "AI mission" OR "AI policy")'

def discover(provider,state,start,end,limit):
    q=news_query(state);key=os.environ.get(KEYS.get(provider,''),'')
    if provider in KEYS and not key:raise RuntimeError('missing_key')
    if provider=='google-rss':
        url='https://news.google.com/rss/search?'+urlencode({'q':q+f' after:{start} before:{end}','hl':'en-IN','gl':'IN','ceid':'IN:en'})
        raw,_,_=fetch(url);items=ET.fromstring(raw).findall('.//item')[:limit]
        return [{'title':i.findtext('title',''),'url':i.findtext('link',''),'published_at_raw':i.findtext('pubDate',''),'publisher':i.findtext('source',''),'url_kind':'aggregator_redirect'} for i in items]
    if provider=='gdelt':
        # Geography belongs in the query. sourcecountry is publisher location, not event location.
        url='https://api.gdeltproject.org/api/v2/doc/doc?'+urlencode({'query':f'"{state}" ("artificial intelligence" OR "AI mission" OR "AI policy")','mode':'artlist','format':'json','maxrecords':min(limit,250),'startdatetime':start.replace('-','')+'000000','enddatetime':end.replace('-','')+'000000','sort':'datedesc'})
        obj=api(url)
        return [{'title':a.get('title'),'url':a.get('url'),'published_at_raw':None,'discovered_at_provider':a.get('seendate'),'publisher':a.get('domain'),'language':a.get('language'),'url_kind':'publisher'} for a in obj.get('articles',[])]
    if provider=='tavily':
        obj=api('https://api.tavily.com/search',{'Authorization':'Bearer '+key},{'query':q,'topic':'news','search_depth':'basic','auto_parameters':False,'start_date':start,'end_date':end,'max_results':min(limit,20),'include_raw_content':False,'include_answer':False})
        return [{'title':a.get('title'),'url':a.get('url'),'published_at_raw':a.get('published_date'),'publisher':None,'snippet':a.get('content','')[:800],'url_kind':'publisher'} for a in obj.get('results',[])]
    if provider=='newsapi':
        url='https://newsapi.org/v2/everything?'+urlencode({'q':q,'from':start,'to':end,'language':'en','sortBy':'publishedAt','pageSize':min(limit,100),'page':1})
        obj=api(url,{'X-Api-Key':key})
        return [{'title':a.get('title'),'url':a.get('url'),'published_at_raw':a.get('publishedAt'),'publisher':(a.get('source') or {}).get('name'),'snippet':a.get('description'),'url_kind':'publisher'} for a in obj.get('articles',[])]
    if provider=='gnews':
        url='https://gnews.io/api/v4/search?'+urlencode({'q':q,'from':start+'T00:00:00Z','to':end+'T00:00:00Z','lang':'en','max':min(limit,10),'nullable':'description,content,image','sortby':'publishedAt','apikey':key})
        obj=api(url)
        return [{'title':a.get('title'),'url':a.get('url'),'published_at_raw':a.get('publishedAt'),'publisher':(a.get('source') or {}).get('name'),'snippet':a.get('description'),'url_kind':'publisher'} for a in obj.get('articles',[])]
    if provider=='exa':
        obj=api('https://api.exa.ai/search',{'x-api-key':key},{'query':state+' state government artificial intelligence policy mission deployment','type':'auto','numResults':min(limit,10),'startPublishedDate':start+'T00:00:00Z','endPublishedDate':end+'T00:00:00Z'})
        return [{'title':a.get('title'),'url':a.get('url'),'published_at_raw':a.get('publishedDate'),'publisher':None,'author':a.get('author'),'date_note':'Provider estimate from HTML, not event date','url_kind':'publisher'} for a in obj.get('results',[])]
    if provider=='crustdata':
        stamp=lambda s:int(datetime.fromisoformat(s).replace(tzinfo=timezone.utc).timestamp())
        obj=api('https://api.crustdata.com/web/search/live',{'Authorization':'Bearer '+key,'x-api-version':'2025-11-01'},{'query':q,'sources':['news'],'location':'IN','start_date':stamp(start),'end_date':stamp(end),'page':1,'human_mode':False})
        if obj.get('success') is False:raise RuntimeError('Provider reported unsuccessful search')
        return [{'title':a.get('title'),'url':a.get('url'),'published_at_raw':None,'publisher':a.get('source'),'snippet':a.get('snippet'),'url_kind':'publisher'} for a in obj.get('results',[])[:limit]]
    raise ValueError('Unsupported provider: '+provider)

def run(args):
    end=datetime.now(timezone.utc).date()-timedelta(days=1) # respects delayed free plans
    start=end-timedelta(days=args.days)
    all_rows=[];runs=[]
    selected=args.states.split(',') if args.states else STATES
    if any(s not in STATES for s in selected):raise ValueError('Use canonical selected state names')
    for provider in args.providers.split(','):
        if provider not in ['google-rss','gdelt',*KEYS]:raise ValueError('Unknown provider')
        calls=0
        if provider in KEYS and not os.environ.get(KEYS[provider]):
            runs.append({'provider':provider,'status':'skipped_missing_key','calls':0});continue
        for state in selected:
            if calls>=args.max_calls:break
            calls+=1
            try:
                rows=discover(provider,state,start.isoformat(),end.isoformat(),args.limit)
                for row in rows:
                    if not row.get('url'):continue
                    row['url']=canonical_url(row['url'])
                    row.update(candidate_id=hashlib.sha256(row['url'].encode()).hexdigest()[:20],query_state=state,provider=provider,query=news_query(state),review_status='pending',event_date=None)
                    all_rows.append(row)
                runs.append({'provider':provider,'state':state,'status':'ok','count':len(rows)})
            except Exception as ex:
                error=str(ex) if isinstance(ex,RuntimeError) else type(ex).__name__
                runs.append({'provider':provider,'state':state,'status':'failed','error':error})
                if any(code in error for code in ('401','402','403','429','request_cap')):break
            if provider in ('gdelt','crustdata'):time.sleep(6)
    groups={}
    for row in all_rows:
        key=row['candidate_id']
        if key not in groups:groups[key]={**row,'discovered_by':[],'query_states':[]}
        if row['provider'] not in groups[key]['discovered_by']:groups[key]['discovered_by'].append(row['provider'])
        if row['query_state'] not in groups[key]['query_states']:groups[key]['query_states'].append(row['query_state'])
    now=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    result={'run_id':now,'window':{'from':str(start),'to':str(end),'boundary_note':'Provider endpoints differ on inclusive boundaries; overlapping runs and URL dedup handle repeats.'},'query_cap_per_provider':args.max_calls,'max_attempts_per_query':3,'automatic_paid_fallback':False,'candidates':list(groups.values()),'provider_runs':runs,'observations':len(all_rows),'unique_urls':len(groups),'note':'URL dedup only. Cross-provider article identity and event identity require review. No coverage or accuracy estimate is implied. Query caps do not override provider-side billing; disable automatic top-ups in the account.'}
    path=ROOT/args.output_dir/f'multiprovider-{now}.json';dump(path,result)
    print(json.dumps({'path':str(path),'observations':len(all_rows),'unique_urls':len(groups),'failed_queries':sum(r['status']=='failed' for r in runs),'skipped_providers':[r['provider'] for r in runs if r['status']=='skipped_missing_key']}))
    if not any(r['status']=='ok' for r in runs):raise SystemExit('No provider completed a query; inspect saved run log')

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--providers',default='google-rss,gdelt');p.add_argument('--states',help='Comma-separated canonical states');p.add_argument('--days',type=int,default=7);p.add_argument('--limit',type=int,default=10);p.add_argument('--max-calls',type=int,default=12);p.add_argument('--output-dir',default='runs')
    args=p.parse_args()
    if not 1<=args.days<=30 or not 1<=args.max_calls<=24 or not 1<=args.limit<=100:p.error('days 1..30, max-calls 1..24, limit 1..100')
    run(args)
