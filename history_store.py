"""Publish/restore consistent SQLite snapshots on a separate Git branch, without switching checkout."""
import argparse
import gzip
import io
import json
import os
import sqlite3
import subprocess
import uuid
from contextlib import closing
from pathlib import Path

from ledger import DEFAULT_DB, ROOT, Ledger, digest, now

BRANCH='data-history'
REF='refs/remotes/origin/'+BRANCH
BLOCK_SIZE=65536


def block_plan(raw,old_blocks=()):
    previous={b['sha256']:b for b in old_blocks}
    blocks=[];new={}
    for offset in range(0,len(raw),BLOCK_SIZE):
        part=raw[offset:offset+BLOCK_SIZE];sha=digest(part)
        block={'sha256':sha,'bytes':len(part),'path':'block-'+sha+'.gz'}
        if sha in previous:block['git_blob']=previous[sha]['git_blob']
        else:new[sha]=gzip.compress(part,mtime=0)
        blocks.append(block)
    return blocks,new


def read_blocks(manifest):
    blocks=manifest['blocks']
    if not 0<manifest['database_bytes']<=250_000_000 or len(blocks)>4000:raise ValueError('Invalid archive bounds')
    ids=list(dict.fromkeys(b['git_blob'] for b in blocks))
    result=git('cat-file','--batch',input=('\n'.join(ids)+'\n').encode()).stdout
    stream=io.BytesIO(result);content={}
    for oid in ids:
        parts=stream.readline().decode('ascii').split()
        if len(parts)!=3 or parts[0]!=oid or parts[1]!='blob':raise ValueError('Missing archive block')
        size=int(parts[2]);compressed=stream.read(size)
        if len(compressed)!=size or stream.read(1)!=b'\n':raise ValueError('Truncated block response')
        with gzip.GzipFile(fileobj=io.BytesIO(compressed)) as source:raw=source.read(BLOCK_SIZE+1)
        if len(raw)>BLOCK_SIZE:raise ValueError('Oversized block')
        content[oid]=raw
    output=[]
    for block in blocks:
        raw=content[block['git_blob']]
        if len(raw)!=block['bytes'] or digest(raw)!=block['sha256']:raise ValueError('Archive block checksum mismatch')
        output.append(raw)
    raw=b''.join(output)
    if len(raw)!=manifest['database_bytes']:raise ValueError('Archive length mismatch')
    return raw


def git(*args,input=None,check=True):
    result=subprocess.run(['git',*args],cwd=ROOT,input=input,capture_output=True,check=False)
    if check and result.returncode:
        # Authentication helpers and remote diagnostics can contain private URLs. Do not echo them.
        error=result.stderr.decode('utf-8','replace').lower()
        category=next((label for token,label in [('permission denied','permission_denied'),('403','permission_denied'),
            ('fetch first','concurrent_update'),('non-fast-forward','concurrent_update'),('could not resolve','network_resolution'),
            ('cannot lock ref','reference_lock')] if token in error),'unspecified')
        raise RuntimeError('Git history operation failed: '+args[0]+' (exit '+str(result.returncode)+', '+category+')')
    return result


def parent_ref(initialize=False):
    result=git('ls-remote','--exit-code','--heads','origin','refs/heads/'+BRANCH,check=False)
    if result.returncode==2 and initialize:return None
    if result.returncode:raise RuntimeError('Durable history unavailable. Refusing to reset state or request budgets.')
    if initialize:raise RuntimeError('History branch already exists. Restore or persist explicitly.')
    git('fetch','--depth=1','origin','+refs/heads/'+BRANCH+':'+REF)
    return git('rev-parse',REF).stdout.decode().strip()


def persist(path,initialize=False):
    parent=parent_ref(initialize)
    marker=Path(str(path)+'.history.json')
    if parent and (not marker.exists() or json.loads(marker.read_text(encoding='utf-8'))['commit']!=parent):
        raise RuntimeError('Remote history advanced or local baseline is absent. Restore to a fresh database and reconcile local imports; refusing to overwrite newer state.')
    with Ledger(path) as ledger:
        audit=ledger.audit()
        if audit['integrity_check']!=['ok'] or audit['foreign_key_failures']:raise ValueError('Ledger validation failed')
        temporary=Path(path).parent/('archive-'+uuid.uuid4().hex+'.sqlite')
        ledger.backup(temporary)
    try:raw=temporary.read_bytes()
    finally:temporary.unlink(missing_ok=True)
    sha=digest(raw)
    if len(raw)>250_000_000:raise ValueError('Ledger exceeds the 250 MB local archive bound; migrate storage before collecting more')
    for name in ['TAVILY_API_KEY','EXA_API_KEY','FIRECRAWL_API_KEY','NEWSAPI_API_KEY','GNEWS_API_KEY','CRUSTDATA_API_KEY','GITHUB_TOKEN']:
        value=os.environ.get(name)
        if value and value.encode() in raw:raise ValueError('Credential value detected; history publication stopped')
    old={}
    if parent:
        old=json.loads(git('show',parent+':manifest.json').stdout)
        if old['database_sha256']==sha and old.get('format_version')==2:return {'unchanged':True,'commit':parent}
    blocks,new_blocks=block_plan(raw,old.get('blocks',[]))
    new_oids={key:git('hash-object','-w','--stdin',input=value).stdout.decode().strip() for key,value in new_blocks.items()}
    for block in blocks:
        if 'git_blob' not in block:block['git_blob']=new_oids[block['sha256']]
    stored_bytes=sum(len(b) for b in new_blocks.values())
    manifest=json.dumps({'format_version':2,'block_size':BLOCK_SIZE,'database_bytes':len(raw),'blocks':blocks,
          'new_compressed_block_bytes':stored_bytes,'reused_blocks':sum(b['sha256'] not in new_blocks for b in blocks),
          'created_at':now(),'database_sha256':sha,'audit':audit,
          'source_commit':git('rev-parse','HEAD').stdout.decode().strip(),
          'boundary':'Includes unverified discovery metadata and external proposals. Only approved events are publication-ready. No full publisher article bodies or credentials.'},indent=2).encode()
    readme=b'# Durable data history\n\nThe database preserves query history, observations, review actions and local provider request reservations. It contains unverified news candidates, not only approved events. Restore with history_store.py from the main branch. manifest.json contains the database checksum and validation counts. No credentials or full publisher article bodies are stored.\n'
    blobs={b['path']:b['git_blob'] for b in blocks}
    blobs.update({name:git('hash-object','-w','--stdin',input=value).stdout.decode().strip() for name,value in [('manifest.json',manifest),('README.md',readme)]})
    tree=git('mktree',input=''.join(f'100644 blob {sha}\t{name}\n' for name,sha in sorted(blobs.items())).encode()).stdout.decode().strip()
    args=['-c','user.name=Project Maintainer','-c','user.email=maintainer@localhost','commit-tree',tree]
    if parent:args+=['-p',parent]
    commit=git(*args,input=b'Checkpoint collection evidence and request reservations\n').stdout.decode().strip()
    # A competing writer causes a non-fast-forward rejection. Never force-push history.
    git('push','origin',commit+':refs/heads/'+BRANCH)
    marker.write_text(json.dumps({'commit':commit,'database_sha256':sha}),encoding='utf-8')
    return {'commit':commit,'database_sha256':sha,'counts':audit['counts'],'blocks':len(blocks),
            'new_blocks':len(new_blocks),'new_compressed_block_bytes':stored_bytes}


def restore(path):
    path=Path(path)
    if path.exists():raise ValueError('Restore destination already exists; use a fresh path to preserve local work')
    parent=parent_ref()
    manifest=json.loads(git('show',parent+':manifest.json').stdout)
    if manifest.get('format_version')==2:raw=read_blocks(manifest)
    else:
        compressed=git('show',parent+':observatory.sqlite.gz').stdout
        with gzip.GzipFile(fileobj=io.BytesIO(compressed)) as source:raw=source.read(250_000_001)
        if len(raw)>250_000_000:raise ValueError('Oversized legacy archive')
    if digest(raw)!=manifest['database_sha256']:raise ValueError('History checksum mismatch')
    path.parent.mkdir(parents=True,exist_ok=True)
    temp=path.with_name(path.name+'.'+uuid.uuid4().hex+'.tmp')
    try:
        temp.write_bytes(raw)
        with closing(sqlite3.connect(temp)) as db:
            if db.execute('PRAGMA integrity_check').fetchone()[0]!='ok' or db.execute('PRAGMA foreign_key_check').fetchone():raise ValueError('Invalid restored database')
        temp.replace(path)
        Path(str(path)+'.history.json').write_text(json.dumps({'commit':parent,'database_sha256':manifest['database_sha256']}),encoding='utf-8')
    finally:temp.unlink(missing_ok=True)
    return {'restored_commit':parent,'database_sha256':manifest['database_sha256']}


def refresh(path):
    """Adopt remote state only if local state still matches its last published/restored baseline."""
    path=Path(path);marker=Path(str(path)+'.history.json')
    if not marker.exists():raise ValueError('No baseline marker; restore to a new path and reconcile explicitly')
    baseline=json.loads(marker.read_text(encoding='utf-8'))
    backup=path.with_name(path.name+'.before-refresh-'+uuid.uuid4().hex)
    with Ledger(path) as store:store.backup(backup)
    if digest(backup.read_bytes())!=baseline['database_sha256']:
        raise ValueError('Local database has unpublished changes; preserved backup, refused automatic refresh')
    temporary=path.with_name(path.name+'.remote-'+uuid.uuid4().hex)
    result=restore(temporary)
    with Ledger(temporary) as store:store.backup(path)
    marker.write_bytes(Path(str(temporary)+'.history.json').read_bytes())
    temporary.unlink();Path(str(temporary)+'.history.json').unlink()
    return {**result,'local_backup':str(backup)}


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('command',choices=['initialize','persist','restore','refresh'])
    p.add_argument('--db',type=Path,default=DEFAULT_DB);args=p.parse_args()
    result=restore(args.db) if args.command=='restore' else refresh(args.db) if args.command=='refresh' else persist(args.db,args.command=='initialize')
    print(json.dumps(result,indent=2))


if __name__=='__main__':main()
