"""Publish/restore consistent SQLite snapshots on a separate Git branch, without switching checkout."""
import argparse
import gzip
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
    git('fetch','origin','+refs/heads/'+BRANCH+':'+REF)
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
    if parent:
        old=json.loads(git('show',parent+':manifest.json').stdout)
        if old['database_sha256']==sha:return {'unchanged':True,'commit':parent}
    manifest=json.dumps({'created_at':now(),'database_sha256':sha,'audit':audit,
          'source_commit':git('rev-parse','HEAD').stdout.decode().strip(),
          'boundary':'Includes unverified discovery metadata and external proposals. Only approved events are publication-ready. No full publisher article bodies or credentials.'},indent=2).encode()
    readme=b'# Durable data history\n\nThe database preserves query history, observations, review actions and local provider request reservations. It contains unverified news candidates, not only approved events. Restore with history_store.py from the main branch. manifest.json contains the database checksum and validation counts. No credentials or full publisher article bodies are stored.\n'
    compressed=gzip.compress(raw,mtime=0)
    if len(compressed)>45_000_000:raise ValueError('Compressed ledger exceeds the 45 MB Git storage bound')
    blobs={name:git('hash-object','-w','--stdin',input=value).stdout.decode().strip() for name,value in [('observatory.sqlite.gz',compressed),('manifest.json',manifest),('README.md',readme)]}
    tree=git('mktree',input=''.join(f'100644 blob {sha}\t{name}\n' for name,sha in sorted(blobs.items())).encode()).stdout.decode().strip()
    args=['-c','user.name=Project Maintainer','-c','user.email=maintainer@localhost','commit-tree',tree]
    if parent:args+=['-p',parent]
    commit=git(*args,input=b'Checkpoint collection evidence and request reservations\n').stdout.decode().strip()
    # A competing writer causes a non-fast-forward rejection. Never force-push history.
    git('push','origin',commit+':refs/heads/'+BRANCH)
    marker.write_text(json.dumps({'commit':commit,'database_sha256':sha}),encoding='utf-8')
    return {'commit':commit,'database_sha256':sha,'counts':audit['counts']}


def restore(path):
    path=Path(path)
    if path.exists():raise ValueError('Restore destination already exists; use a fresh path to preserve local work')
    parent=parent_ref()
    manifest=json.loads(git('show',parent+':manifest.json').stdout)
    raw=gzip.decompress(git('show',parent+':observatory.sqlite.gz').stdout)
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


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('command',choices=['initialize','persist','restore'])
    p.add_argument('--db',type=Path,default=DEFAULT_DB);args=p.parse_args()
    result=restore(args.db) if args.command=='restore' else persist(args.db,args.command=='initialize')
    print(json.dumps(result,indent=2))


if __name__=='__main__':main()
