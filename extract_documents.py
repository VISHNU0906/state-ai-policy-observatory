"""Extract allowed public documents locally, with optional explicit hosted backends."""
import argparse, hashlib, io, json, os, time
from datetime import datetime, timezone
from urllib.error import HTTPError
from urllib.parse import urlsplit
from urllib.robotparser import RobotFileParser
from pipeline import ROOT, UA, dump, fetch
from collectors import api

def allowed(url,cache):
    p=urlsplit(url);origin=p.scheme+'://'+p.netloc
    if origin not in cache:
        rp=RobotFileParser();rp.set_url(origin+'/robots.txt')
        try:
            raw,_,_=fetch(rp.url);rp.parse(raw.decode('utf-8','replace').splitlines());cache[origin]=rp
        except HTTPError as ex:
            if ex.code==404:cache[origin]=None
            else:raise RuntimeError('robots_unavailable_HTTP_'+str(ex.code)) from None
        except Exception:raise RuntimeError('robots_unavailable') from None
    rp=cache[origin]
    if rp and not rp.can_fetch(UA,url):return False
    if rp:
        delay=rp.crawl_delay(UA) or 1
        if delay>30:raise RuntimeError('robots_delay_exceeds_run_budget')
        time.sleep(max(delay,1))
    return True

def extract(url,backend):
    if backend=='local':
        raw,headers,final=fetch(url);kind=headers.get('Content-Type','').lower()
        if raw.startswith(b'%PDF') or 'pdf' in kind:
            from pypdf import PdfReader
            reader=PdfReader(io.BytesIO(raw));text='\n'.join(p.extract_text() or '' for p in reader.pages)
            return {'text':text,'title':str((reader.metadata or {}).get('/Title','')),'publication_date_candidate':None,'pages':len(reader.pages),'extractor':'pypdf','bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest(),'final_url':final}
        import trafilatura
        doc=trafilatura.bare_extraction(raw,url=final,with_metadata=True,include_comments=False,include_tables=True,favor_precision=True)
        if doc is None:raise RuntimeError('empty_extraction')
        # Trafilatura Document implements attribute access; older dict API is supported.
        get=lambda key:doc.get(key) if isinstance(doc,dict) else getattr(doc,key,None)
        return {'text':get('text') or '', 'title':get('title'),'publication_date_candidate':get('date'),'extractor':'trafilatura','bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest(),'final_url':final}
    if backend=='tavily':
        key=os.environ.get('TAVILY_API_KEY')
        if not key:raise RuntimeError('missing_key')
        obj=api('https://api.tavily.com/extract',{'Authorization':'Bearer '+key},{'urls':[url],'extract_depth':'basic','format':'markdown'})
        if not obj.get('results'):raise RuntimeError('provider_no_document')
        row=obj['results'][0];return {'text':row.get('raw_content',''),'extractor':'tavily_basic','final_url':row.get('url',url),'publication_date_candidate':None}
    key=os.environ.get('FIRECRAWL_API_KEY')
    if not key:raise RuntimeError('missing_key')
    obj=api('https://api.firecrawl.dev/v2/scrape',{'Authorization':'Bearer '+key},{'url':url,'formats':['markdown'],'onlyMainContent':True})
    if not obj.get('success'):raise RuntimeError('provider_no_document')
    row=obj.get('data',{});meta=row.get('metadata',{})
    if meta.get('statusCode',200)>=400:raise RuntimeError('provider_returned_error_page')
    return {'text':row.get('markdown',''),'title':meta.get('title'),'extractor':'firecrawl_markdown','final_url':meta.get('sourceURL',url),'publication_date_candidate':None}

def run(args):
    data=json.loads((ROOT/'data/events.json').read_text(encoding='utf-8'));selected=data['sources']
    if args.ids:selected=[s for s in selected if s['id'] in args.ids.split(',')]
    if args.diverse:
        chosen=[];hosts=set()
        for s in selected:
            host=urlsplit(s['url']).netloc
            if host not in hosts:chosen.append(s);hosts.add(host)
        selected=chosen
    logs=[];cache={}
    for s in selected[:args.limit]:
        began=time.monotonic();row={'source_id':s['id'],'url':s['url'],'backend':args.backend}
        try:
            if not allowed(s['url'],cache):row['status']='robots_disallowed'
            else:
                doc=extract(s['url'],args.backend);text=doc.pop('text','')
                row.update(doc,characters=len(text),status='extracted' if len(text)>=100 else 'insufficient_text')
                if text:
                    h=hashlib.sha256(s['url'].encode()).hexdigest()
                    target=ROOT/'.cache'/'extracted'/(h+'.txt');target.parent.mkdir(parents=True,exist_ok=True);target.write_text(text,encoding='utf-8')
                    row['text_sha256']=hashlib.sha256(text.encode()).hexdigest()
        except Exception as ex:row.update(status='failed',error=str(ex) if isinstance(ex,RuntimeError) else type(ex).__name__)
        row['seconds']=round(time.monotonic()-began,2);logs.append(row)
    stamp=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ');dump(ROOT/'runs'/f'extraction-{stamp}.json',{'run_id':stamp,'sample_selection':'first unique host' if args.diverse else 'ordered source ledger','results':logs,'note':'Text is private local cache, excluded from Git and submission. Extraction length does not measure correctness. No event fields are automatically approved.'})
    print(json.dumps({'documents':len(logs),'extracted':sum(r['status']=='extracted' for r in logs),'blocked_or_failed':sum(r['status']!='extracted' for r in logs)}))

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--backend',choices=['local','tavily','firecrawl'],default='local');p.add_argument('--limit',type=int,default=12);p.add_argument('--ids');p.add_argument('--diverse',action='store_true');args=p.parse_args()
    if not 1<=args.limit<=30:p.error('--limit must be 1..30')
    run(args)
