"""Dependency-free collection, normalization, review gating and publication CLI."""
from __future__ import annotations
import argparse, csv, hashlib, json, re, time
from collections import Counter, defaultdict
from datetime import date, datetime, timezone
from difflib import SequenceMatcher
from email.utils import parsedate_to_datetime
from html.parser import HTMLParser
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urlsplit, urlunsplit, parse_qsl
from urllib.request import Request, urlopen
from urllib.robotparser import RobotFileParser
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parent
CUTOFF = '2026-11-10'
START = '2024-01-01'
STATES = ['Andhra Pradesh', 'Assam', 'Gujarat', 'Karnataka', 'Kerala', 'Madhya Pradesh', 'Maharashtra', 'Odisha', 'Rajasthan', 'Tamil Nadu', 'Telangana', 'Uttar Pradesh']
CATEGORIES = ['Policy & strategy', 'Institutions & capacity', 'Partnerships', 'Public-sector deployment', 'Funding', 'Responsible AI']
STAGES = ['announced', 'approved', 'signed', 'launched', 'pilot', 'operational']
UA = 'StateAIPolicyResearch/1.0 (+manual-reviewed academic research)'
ALIASES = {'up':'Uttar Pradesh','uttarpradesh':'Uttar Pradesh','tn':'Tamil Nadu','tamilnadu':'Tamil Nadu','ts':'Telangana','tg':'Telangana','telangana':'Telangana','ka':'Karnataka','karnataka':'Karnataka','mh':'Maharashtra','maharashtra':'Maharashtra','gj':'Gujarat','gujarat':'Gujarat'}
ALIASES.update({'ap':'Andhra Pradesh','andhrapradesh':'Andhra Pradesh','assam':'Assam','as':'Assam','kerala':'Kerala','kl':'Kerala','mp':'Madhya Pradesh','madhyapradesh':'Madhya Pradesh','odisha':'Odisha','orissa':'Odisha','od':'Odisha','rajasthan':'Rajasthan','rj':'Rajasthan'})

def normalize_state(value):
    key = re.sub(r'[^a-z]', '', value.lower())
    if key not in ALIASES: raise ValueError(f'Unknown/out-of-scope state: {value!r}')
    return ALIASES[key]

def normalize_date(value, precision='day'):
    if not value:
        if precision != 'unknown': raise ValueError('Missing date must have unknown precision')
        return None
    value = value.strip()
    patterns = {'day':r'\d{4}-\d{2}-\d{2}', 'month':r'\d{4}-\d{2}', 'year':r'\d{4}'}
    if precision not in patterns or not re.fullmatch(patterns[precision], value):
        raise ValueError(f'Date/precision mismatch: {value!r}, {precision}')
    full = value + {'day':'','month':'-01','year':'-01-01'}[precision]
    parsed = date.fromisoformat(full)
    if parsed < date.fromisoformat(START) or parsed > date.fromisoformat(CUTOFF):
        raise ValueError(f'Event outside research window: {value}')
    return value

def canonical_url(url):
    p = urlsplit(url.strip())
    if p.scheme not in ('http','https') or not p.netloc: raise ValueError(f'Invalid URL: {url}')
    query = [(k,v) for k,v in parse_qsl(p.query,keep_blank_values=True) if not k.lower().startswith('utm_') and k.lower() not in ('fbclid','gclid')]
    return urlunsplit((p.scheme.lower(),p.netloc.lower(),p.path or '/',urlencode(query),''))

def dump(path, value):
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')

def csv_write(path, rows, fields=None):
    path.parent.mkdir(parents=True,exist_ok=True)
    fields = fields or list(dict.fromkeys(k for row in rows for k in row))
    with path.open('w',newline='',encoding='utf-8-sig') as f:
        w=csv.DictWriter(f,fieldnames=fields,extrasaction='ignore');w.writeheader()
        for row in rows:
            cleaned={k:json.dumps(v,ensure_ascii=False) if isinstance(v,(list,dict)) else v for k,v in row.items()}
            # Prevent spreadsheet formula injection while retaining ordinary numeric values.
            cleaned={k:("'"+v if isinstance(v,str) and v.startswith(('=','+','-','@')) else v) for k,v in cleaned.items()}
            w.writerow(cleaned)

def deduplicate(candidates):
    """Only reviewed cluster identities merge; similarity never silently merges."""
    groups=defaultdict(list)
    for c in candidates:
        if c.get('review_status')!='accepted': continue
        if not c.get('event_id'): raise ValueError('Accepted candidate needs reviewed event_id')
        groups[c['event_id']].append(c)
    return groups

def build():
    events=[];sources={};excluded=[];queries=[];notes=[]
    files=sorted((ROOT/'research').glob('*.json'))
    if not files: raise ValueError('No reviewed research files')
    for f in files:
        doc=json.loads(f.read_text(encoding='utf-8-sig'))
        events.extend(doc['events']);excluded.extend(doc.get('excluded',[]))
        queries.extend(doc.get('queries',[]));notes.extend(doc.get('notes',[]))
        for s in doc['sources']:
            if s['id'] in sources and sources[s['id']]!=s: raise ValueError('Conflicting source ID: '+s['id'])
            s['url']=canonical_url(s['url']);sources[s['id']]=s
    ids=set();candidates=[];normalized=[]
    for e in events:
        if e['id'] in ids: raise ValueError('Duplicate event ID: '+e['id'])
        ids.add(e['id']);e['state']=normalize_state(e['state'])
        e['event_date']=normalize_date(e.get('event_date'),e['date_precision'])
        if e['category'] not in CATEGORIES or e['stage'] not in STAGES: raise ValueError('Invalid taxonomy: '+e['id'])
        if not e['source_ids']: raise ValueError('Unsourced event: '+e['id'])
        if len(set(e['source_ids']))!=len(e['source_ids']): raise ValueError('Repeated source within event')
        for sid in e['source_ids']:
            if sid not in sources: raise ValueError('Missing source: '+sid)
            s=sources[sid]
            if not s.get('evidence_summary'): raise ValueError('Missing evidence summary: '+sid)
            candidates.append({'candidate_id':e['id']+'::'+sid,'event_id':e['id'],'source_id':sid,'state':e['state'],'title':s['title'],'url':s['url'],'review_status':'accepted','merge_reason':'Reviewed evidence association for this milestone; may corroborate only part of the claim'})
        # The reviewed first source anchors the event. An official contextual page
        # must not silently replace the report establishing the action/date.
        primary=sources[e['source_ids'][0]]
        e.update({'date':e['event_date'],'source_name':primary['publisher'],'source_url':primary['url'],'source_count':len(e['source_ids']),'has_primary_source':any(sources[sid]['source_type'].startswith('primary_') for sid in e['source_ids'])})
        normalized.append(e)
    groups=deduplicate(candidates)
    normalized.sort(key=lambda e:(e['event_date'] or '',e['id']),reverse=True)
    audit=[{'event_id':k,'candidate_count':len(v),'source_ids':[c['source_id'] for c in v],'decision':'merge source observations, retain one milestone'} for k,v in sorted(groups.items())]
    payload={'meta':{'title':'State AI Policy Observatory','window_start':START,'research_cutoff':CUTOFF,'states':STATES,'events':len(normalized),'sources':len(sources),'source_observations':len(candidates),'additional_source_links':len(candidates)-len(groups),'with_primary_source':sum(e['has_primary_source'] for e in normalized),'categories':dict(Counter(e['category'] for e in normalized)),'stages':dict(Counter(e['stage'] for e in normalized)),'coverage_note':'Purposive 12-state sample. Counts reflect reviewed evidence, not total state activity or performance.'},'events':normalized,'sources':list(sources.values()),'notes':notes}
    dump(ROOT/'data/events.json',payload)
    fields=['id','state','title','date','date_precision','date_basis','publication_date','source_name','source_url','summary','category','stage','initiative','confidence','limitations','source_count','has_primary_source','source_ids']
    csv_write(ROOT/'data/events.csv',normalized,fields)
    csv_write(ROOT/'data/sources.csv',list(sources.values()))
    csv_write(ROOT/'data/source_observations.csv',candidates)
    csv_write(ROOT/'data/deduplication_audit.csv',audit)
    dump(ROOT/'data/exclusions.json',excluded);dump(ROOT/'data/query_log.json',queries)
    dump(ROOT/'data/quality_report.json',payload['meta'])
    (ROOT/'dist').mkdir(exist_ok=True)
    # JS payload also supports opening the dashboard directly from disk, offline.
    (ROOT/'dist/data.js').write_text('window.OBSERVATORY_DATA = '+json.dumps(payload,ensure_ascii=False).replace('</','<\\/')+';\n',encoding='utf-8')
    for name in ('events.csv','sources.csv','events.json','deduplication_audit.csv','exclusions.json','quality_report.json','query_log.json'):
        (ROOT/'dist'/name).write_bytes((ROOT/'data'/name).read_bytes())
    print(json.dumps(payload['meta'],indent=2))

def fetch(url, attempts=3):
    last=None
    for n in range(attempts):
        try:
            with urlopen(Request(url,headers={'User-Agent':UA}),timeout=25) as response:
                data=response.read(3_000_001)
                if len(data)>3_000_000: raise ValueError('Response exceeds 3 MB limit')
                return data,dict(response.headers),response.geturl()
        except HTTPError as ex:
            last=ex
            if ex.code not in (429,500,502,503,504): raise
        except (URLError,TimeoutError) as ex: last=ex
        if n+1<attempts: time.sleep(min(2**n,4))
    raise last

def collect(limit):
    """Google News RSS discovery. Redirect links are leads, never evidence."""
    result=[];log=[];seen=set()
    for state in STATES:
        q=f'"{state}" ("artificial intelligence" OR "AI policy" OR "AI mission") after:{START} before:2026-11-11'
        url='https://news.google.com/rss/search?'+urlencode({'q':q,'hl':'en-IN','gl':'IN','ceid':'IN:en'})
        try:
            raw,headers,final=fetch(url);root=ET.fromstring(raw)
            items=root.findall('.//item')[:limit]
            for item in items:
                link=item.findtext('link','');key=hashlib.sha256(link.encode()).hexdigest()[:16]
                if key in seen: continue
                seen.add(key);published=item.findtext('pubDate','')
                try: published=parsedate_to_datetime(published).date().isoformat()
                except (ValueError,TypeError): published=None
                result.append({'candidate_id':key,'query_state':state,'title':item.findtext('title',''),'discovery_url':link,'publication_date':published,'publisher':item.findtext('source',''),'review_status':'pending','event_date':None,'event_id':None})
            log.append({'state':state,'query':q,'url':url,'status':'ok','returned':len(items),'response_sha256':hashlib.sha256(raw).hexdigest()})
        except Exception as ex: log.append({'state':state,'query':q,'url':url,'status':'failed','error':str(ex)})
    run=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    dump(ROOT/'runs'/f'collection-{run}.json',{'retrieved_at':run,'provider':'Google News RSS','candidates':result,'log':log})
    print(json.dumps({'run':run,'pending_candidates':len(result),'successful_feeds':sum(x['status']=='ok' for x in log),'failed_feeds':sum(x['status']=='failed' for x in log)}))

class MetadataParser(HTMLParser):
    def __init__(self): super().__init__();self.meta={};self.title='';self.in_title=False
    def handle_starttag(self,tag,attrs):
        attrs=dict(attrs)
        if tag=='title':self.in_title=True
        if tag=='meta':
            key=attrs.get('property',attrs.get('name',''))
            if key in ('article:published_time','date','datePublished','og:title','description'): self.meta[key]=attrs.get('content','')
    def handle_endtag(self,tag):
        if tag=='title':self.in_title=False
    def handle_data(self,data):
        if self.in_title:self.title+=data

def refresh_sources(limit):
    """Bounded direct retrieval with robots checks; no bypass, no inferred events."""
    payload=json.loads((ROOT/'data/events.json').read_text(encoding='utf-8'));results=[];robots_cache={}
    for s in payload['sources'][:limit]:
        url=s['url'];p=urlsplit(url);origin=f'{p.scheme}://{p.netloc}'
        result={'source_id':s['id'],'url':url}
        try:
            if origin not in robots_cache:
                rp=RobotFileParser();rp.set_url(origin+'/robots.txt')
                try:
                    raw,_,_=fetch(rp.url);rp.parse(raw.decode('utf-8','replace').splitlines());robots_cache[origin]=rp
                except HTTPError as ex:
                    if ex.code==404: robots_cache[origin]=None
                    else: raise
            rp=robots_cache[origin]
            if rp and not rp.can_fetch(UA,url):
                result['status']='robots_disallowed';results.append(result);continue
            if rp: time.sleep(min(max(rp.crawl_delay(UA) or 1,1),30))
            raw,headers,final=fetch(url);result.update(status='retrieved',final_url=final,sha256=hashlib.sha256(raw).hexdigest(),bytes=len(raw),content_type=headers.get('Content-Type',''))
            if 'html' in result['content_type']:
                parser=MetadataParser();parser.feed(raw.decode('utf-8','replace'));result.update(title=parser.title.strip(),metadata=parser.meta)
        except Exception as ex:result.update(status='failed',error=str(ex))
        results.append(result)
    run=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    dump(ROOT/'runs'/f'retrieval-{run}.json',{'retrieved_at':run,'results':results})
    print(json.dumps(dict(Counter(x['status'] for x in results))))

def suggestions():
    payload=json.loads((ROOT/'data/events.json').read_text(encoding='utf-8'));pairs=[]
    for i,a in enumerate(payload['events']):
        for b in payload['events'][i+1:]:
            if a['state']!=b['state']: continue
            ratio=SequenceMatcher(None,a['title'].lower(),b['title'].lower()).ratio()
            if ratio>=.55 or a['initiative'].lower()==b['initiative'].lower(): pairs.append({'left':a['id'],'right':b['id'],'title_similarity':round(ratio,3),'decision':'review only; separate milestones may be valid'})
    dump(ROOT/'data/duplicate_review_queue.json',pairs);print(f'{len(pairs)} review suggestions; zero automatic merges')

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('command',choices=['build','collect','refresh-sources','suggest-duplicates']);parser.add_argument('--limit',type=int,default=10)
    args=parser.parse_args()
    if not 1<=args.limit<=100: parser.error('--limit must be 1..100')
    {'build':build,'collect':lambda:collect(args.limit),'refresh-sources':lambda:refresh_sources(args.limit),'suggest-duplicates':suggestions}[args.command]()
