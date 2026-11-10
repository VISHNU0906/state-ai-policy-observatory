"""Append retrieval attempts and content-addressed private text for pending publisher documents."""
import argparse
import json
import time
import uuid
from pathlib import Path
from urllib.parse import urlsplit

from extract_documents import allowed,extract
from ledger import DEFAULT_DB,ROOT,Ledger,digest,encoded,now


def retrieve(store,doc_id,backend='local',cache=None,extractor=extract,permission=allowed):
    row=store.db.execute('SELECT * FROM documents WHERE id=?',(doc_id,)).fetchone()
    if row is None:raise ValueError('Unknown document')
    payload={'url':row['url'],'backend':backend};text_hash=None
    try:
        if not permission(row['url'],cache if cache is not None else {}):status='robots_disallowed'
        else:
            result=extractor(row['url'],backend);text=result.pop('text','')
            payload.update(result,characters=len(text))
            status='extracted' if len(text)>=100 else 'insufficient_text'
            if text:
                text_hash=digest(text.encode())
                target=ROOT/'.cache/content'/text_hash[:2]/(text_hash+'.txt')
                target.parent.mkdir(parents=True,exist_ok=True)
                if target.exists() and digest(target.read_bytes())!=text_hash:raise ValueError('Private content hash mismatch')
                if not target.exists():target.write_bytes(text.encode())
                payload['private_content_key']=text_hash
            previous=store.db.execute("SELECT text_hash FROM retrievals WHERE document_id=? AND status='extracted' ORDER BY rowid DESC LIMIT 1",(doc_id,)).fetchone()
            payload['content_changed_since_previous_success']=bool(previous and text_hash and previous[0]!=text_hash)
            payload['publication_date_note']='Extractor metadata candidate only; may be update date or inference. No event fields changed.'
    except Exception as ex:
        status='failed';payload['error']=str(ex) if isinstance(ex,RuntimeError) and str(ex).startswith(('robots_','empty_extraction','missing_key','provider_')) else type(ex).__name__
    retrieval_id=str(uuid.uuid4())
    with store.transaction():
        store.db.execute('INSERT INTO retrievals VALUES (?,?,?,?,?,?)',(retrieval_id,doc_id,now(),status,text_hash,encoded(payload)))
    return {'retrieval_id':retrieval_id,'document_id':doc_id,'status':status,**payload}


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--db',type=Path,default=DEFAULT_DB);p.add_argument('--limit',type=int,default=10)
    p.add_argument('--backend',choices=['local','tavily','firecrawl'],default='local');p.add_argument('--document-id')
    args=p.parse_args()
    if not 1<=args.limit<=30:p.error('limit must be 1..30')
    if args.backend!='local':p.error('Hosted extraction uses the legacy adapter budget. Use local here until a query-scoped reservation is configured.')
    with Ledger(args.db) as store:
        if args.document_id:ids=[args.document_id]
        else:
            rows=store.db.execute("SELECT d.* FROM documents d WHERE d.review_status<>'rejected' AND NOT EXISTS(SELECT 1 FROM retrievals r WHERE r.document_id=d.id) ORDER BY d.id")
            ids=[];hosts=set()
            for row in rows:
                host=urlsplit(row['url']).hostname
                if host in hosts or host=='news.google.com':continue
                hosts.add(host);ids.append(row['id'])
                if len(ids)>=args.limit:break
        cache={};results=[]
        for doc_id in ids:
            results.append(retrieve(store,doc_id,args.backend,cache));time.sleep(1)
        print(json.dumps({'documents':len(results),'results':results},indent=2))


if __name__=='__main__':main()
