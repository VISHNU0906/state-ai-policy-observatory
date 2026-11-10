"""Durable evidence ledger. Discovery is never approval. Python 3.11+, stdlib only."""
from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import sqlite3
import uuid
from contextlib import contextmanager, closing
from datetime import date, datetime, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path
from urllib.parse import urlsplit,parse_qsl

from pipeline import ROOT, CATEGORIES, STAGES, canonical_url, csv_write, normalize_state
from date_rules import date_bounds,event_order

VERSION = 2
DEFAULT_DB = ROOT / 'state' / 'observatory.sqlite'


def encoded(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'))


def digest(value):
    return hashlib.sha256(value if isinstance(value, bytes) else encoded(value).encode()).hexdigest()


def now():
    return datetime.now(timezone.utc).isoformat(timespec='microseconds')


def publication_candidate(raw):
    if not raw:
        return {'value': None, 'precision': 'unknown', 'warning': 'not_supplied'}
    value = str(raw).strip()
    try:
        if len(value) == 10:
            return {'value': date.fromisoformat(value).isoformat(), 'precision': 'day', 'warning': None}
        try:
            parsed = datetime.fromisoformat(value.replace('Z', '+00:00'))
        except ValueError:
            parsed = parsedate_to_datetime(value)
        if parsed.tzinfo is None:
            return {'value': None, 'precision': 'unknown', 'warning': 'timestamp_without_timezone'}
        return {'value': parsed.astimezone(timezone.utc).isoformat(), 'precision': 'timestamp', 'warning': None}
    except (ValueError, TypeError, OverflowError):
        return {'value': None, 'precision': 'unknown', 'warning': 'unparsed'}


SCHEMA = """
CREATE TABLE meta(key TEXT PRIMARY KEY, value TEXT NOT NULL);
CREATE TABLE imports(digest TEXT PRIMARY KEY, kind TEXT NOT NULL, origin TEXT NOT NULL, imported_at TEXT NOT NULL, notes TEXT NOT NULL);
CREATE TABLE runs(id TEXT PRIMARY KEY, started_at TEXT NOT NULL, finished_at TEXT, status TEXT NOT NULL, parameters TEXT NOT NULL);
CREATE TABLE queries(id TEXT PRIMARY KEY, run_id TEXT NOT NULL REFERENCES runs(id), provider TEXT NOT NULL, state TEXT NOT NULL,
 query TEXT NOT NULL, window_start TEXT, window_end TEXT, status TEXT NOT NULL, result_count INTEGER,
 capped INTEGER NOT NULL DEFAULT 0, error TEXT, metadata TEXT NOT NULL);
CREATE TABLE documents(id TEXT PRIMARY KEY, url TEXT UNIQUE NOT NULL, first_seen TEXT NOT NULL, last_seen TEXT NOT NULL,
 review_status TEXT NOT NULL DEFAULT 'pending' CHECK(review_status IN ('pending','reviewed','rejected')), revision INTEGER NOT NULL DEFAULT 0);
CREATE TABLE document_links(id TEXT PRIMARY KEY, left_id TEXT NOT NULL REFERENCES documents(id), right_id TEXT NOT NULL REFERENCES documents(id),
 relation TEXT NOT NULL, evidence TEXT NOT NULL, verified INTEGER NOT NULL DEFAULT 0);
CREATE TABLE observations(id TEXT PRIMARY KEY, document_id TEXT NOT NULL REFERENCES documents(id), query_id TEXT REFERENCES queries(id),
 import_digest TEXT REFERENCES imports(digest), observed_at TEXT NOT NULL, payload TEXT NOT NULL);
CREATE INDEX observation_document ON observations(document_id);
CREATE TABLE sources(id TEXT PRIMARY KEY, document_id TEXT NOT NULL REFERENCES documents(id), payload TEXT NOT NULL);
CREATE TABLE events(id TEXT PRIMARY KEY, payload TEXT NOT NULL, review_status TEXT NOT NULL CHECK(review_status IN ('approved','superseded','draft')),
 revision INTEGER NOT NULL DEFAULT 1, superseded_by TEXT REFERENCES events(id));
CREATE TABLE event_sources(event_id TEXT NOT NULL REFERENCES events(id), source_id TEXT NOT NULL REFERENCES sources(id),
 evidence_basis TEXT NOT NULL, PRIMARY KEY(event_id,source_id));
CREATE TABLE proposals(id TEXT PRIMARY KEY, import_digest TEXT NOT NULL REFERENCES imports(digest), external_id TEXT NOT NULL,
 payload TEXT NOT NULL, UNIQUE(import_digest,external_id));
CREATE TABLE proposal_documents(proposal_id TEXT NOT NULL REFERENCES proposals(id), document_id TEXT NOT NULL REFERENCES documents(id),
 PRIMARY KEY(proposal_id,document_id));
CREATE TABLE external_rejections(id TEXT PRIMARY KEY, import_digest TEXT NOT NULL REFERENCES imports(digest), payload TEXT NOT NULL);
CREATE TABLE review_actions(id TEXT PRIMARY KEY, entity_type TEXT NOT NULL, entity_id TEXT NOT NULL, reviewer TEXT NOT NULL,
 decided_at TEXT NOT NULL, reason TEXT NOT NULL, before_payload TEXT NOT NULL, after_payload TEXT NOT NULL);
CREATE TABLE retrievals(id TEXT PRIMARY KEY, document_id TEXT NOT NULL REFERENCES documents(id), retrieved_at TEXT NOT NULL,
 status TEXT NOT NULL, text_hash TEXT, payload TEXT NOT NULL);
CREATE TABLE matches(id TEXT PRIMARY KEY, left_id TEXT NOT NULL REFERENCES documents(id), right_id TEXT NOT NULL REFERENCES documents(id),
 rule_version TEXT NOT NULL, features TEXT NOT NULL, decision TEXT NOT NULL DEFAULT 'pending'
 CHECK(decision IN ('pending','same_event','distinct','uncertain')), revision INTEGER NOT NULL DEFAULT 0,
 UNIQUE(left_id,right_id,rule_version), CHECK(left_id<right_id));
CREATE TABLE provider_attempts(id TEXT PRIMARY KEY, query_id TEXT NOT NULL REFERENCES queries(id), provider TEXT NOT NULL,
 month TEXT NOT NULL, reserved_at TEXT NOT NULL, outcome TEXT NOT NULL DEFAULT 'reserved');
CREATE INDEX attempt_month ON provider_attempts(provider,month);
CREATE TRIGGER observations_no_update BEFORE UPDATE ON observations BEGIN SELECT RAISE(ABORT,'immutable observations'); END;
CREATE TRIGGER observations_no_delete BEFORE DELETE ON observations BEGIN SELECT RAISE(ABORT,'immutable observations'); END;
CREATE TRIGGER reviews_no_update BEFORE UPDATE ON review_actions BEGIN SELECT RAISE(ABORT,'immutable reviews'); END;
CREATE TRIGGER reviews_no_delete BEFORE DELETE ON review_actions BEGIN SELECT RAISE(ABORT,'immutable reviews'); END;
"""


class Ledger:
    def __init__(self, path=DEFAULT_DB, create=False):
        self.path = Path(path)
        if not self.path.exists() and not create:
            raise FileNotFoundError(f'Ledger absent: {self.path}. Explicit init or restore required.')
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(self.path, timeout=30, isolation_level=None)
        self.db.row_factory = sqlite3.Row
        self.db.execute('PRAGMA foreign_keys=ON')
        self.db.execute('PRAGMA busy_timeout=30000')
        if not self.db.execute("SELECT 1 FROM sqlite_master WHERE name='meta'").fetchone():
            if not create:
                self.close()
                raise ValueError('Uninitialized ledger')
            self.db.executescript('BEGIN IMMEDIATE;\n' + SCHEMA + '\nCOMMIT;')
            self.db.execute('INSERT INTO meta VALUES (?,?)', ('schema_version', str(VERSION)))
        version=self.db.execute("SELECT value FROM meta WHERE key='schema_version'").fetchone()[0]
        if version=='1':
            with self.transaction():
                self.db.execute('CREATE TABLE document_links(id TEXT PRIMARY KEY, left_id TEXT NOT NULL REFERENCES documents(id), right_id TEXT NOT NULL REFERENCES documents(id), relation TEXT NOT NULL, evidence TEXT NOT NULL, verified INTEGER NOT NULL DEFAULT 0)')
                self.db.execute("UPDATE meta SET value=? WHERE key='schema_version'",(str(VERSION),))
            version=str(VERSION)
        if version != str(VERSION):
            self.close()
            raise ValueError('Unsupported schema version')

    def close(self):
        self.db.close()

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.close()

    @contextmanager
    def transaction(self):
        self.db.execute('BEGIN IMMEDIATE')
        try:
            yield
            self.db.execute('COMMIT')
        except BaseException:
            self.db.execute('ROLLBACK')
            raise

    def document(self, url, observed_at):
        url = canonical_url(url)
        parts=urlsplit(url)
        if parts.username or parts.password or any(k.lower() in ['api_key','apikey','access_token','authorization'] for k,v in parse_qsl(parts.query)):
            raise ValueError('Credential-bearing URL cannot enter the public evidence ledger')
        # Do not merge http/https, path case, trailing slash or arbitrary query parameters.
        doc_id = 'doc-' + digest(url)
        self.db.execute('INSERT INTO documents(id,url,first_seen,last_seen) VALUES (?,?,?,?) '
                        'ON CONFLICT(url) DO UPDATE SET first_seen=min(first_seen,excluded.first_seen),last_seen=max(last_seen,excluded.last_seen)',
                        (doc_id, url, observed_at, observed_at))
        return doc_id

    def _register_import(self, sha, kind, origin, notes=''):
        if self.db.execute('SELECT 1 FROM imports WHERE digest=?', (sha,)).fetchone():
            return False
        self.db.execute('INSERT INTO imports VALUES (?,?,?,?,?)', (sha, kind, origin, now(), notes))
        return True

    def _observe(self, row, stamp, query_id=None, import_sha=None, identity=None):
        url = row.get('url') or row.get('discovery_url')
        doc_id = self.document(url, stamp)
        payload = dict(row)
        payload['publication_candidate'] = publication_candidate(row.get('published_at_raw') or row.get('publication_date'))
        obs_id = 'obs-' + digest([query_id, import_sha, identity, payload])
        self.db.execute('INSERT OR IGNORE INTO observations VALUES (?,?,?,?,?,?)',
                        (obs_id, doc_id, query_id, import_sha, stamp, encoded(payload)))
        return doc_id

    def seed(self, path):
        raw = Path(path).read_bytes()
        payload = json.loads(raw)
        sha = digest(raw)
        with self.transaction():
            if not self._register_import(sha, 'reviewed_seed', Path(path).name, 'Legacy research review; no reconstructed retrieval evidence'):
                return False
            stamp = now()
            source_map = {}
            for s in payload['sources']:
                doc_id = self.document(s['url'], stamp)
                old = self.db.execute('SELECT payload FROM sources WHERE id=?', (s['id'],)).fetchone()
                if old and old[0] != encoded(s):
                    raise ValueError('Changed reviewed source needs explicit revision: ' + s['id'])
                self.db.execute('INSERT OR IGNORE INTO sources VALUES (?,?,?)', (s['id'], doc_id, encoded(s)))
                source_map[s['id']] = s
            for event in payload['events']:
                self._validate_event(event)
                old = self.db.execute('SELECT payload FROM events WHERE id=?', (event['id'],)).fetchone()
                if old and old[0] != encoded(event):
                    raise ValueError('Changed reviewed event needs explicit revision: ' + event['id'])
                self.db.execute("INSERT OR IGNORE INTO events(id,payload,review_status) VALUES (?,?,'approved')", (event['id'], encoded(event)))
                for sid in event['source_ids']:
                    if sid not in source_map:
                        raise ValueError('Unknown source reference: ' + sid)
                    self.db.execute('INSERT OR IGNORE INTO event_sources VALUES (?,?,?)',
                                    (event['id'], sid, 'legacy research evidence summary; supporting claim scope may be partial'))
            return True

    @staticmethod
    def _validate_event(event):
        if normalize_state(event['state']) != event['state']:
            raise ValueError('Canonical state required')
        date_bounds(event.get('event_date'), event['date_precision'])
        if event['category'] not in CATEGORIES or event['stage'] not in STAGES:
            raise ValueError('Unknown event taxonomy')
        for field in ['id', 'title', 'summary', 'date_basis', 'source_ids']:
            if not event.get(field):
                raise ValueError('Missing event field: ' + field)

    def import_run(self, path):
        raw = Path(path).read_bytes()
        obj = json.loads(raw)
        sha = digest(raw)
        rows = obj.get('observation_records', obj.get('candidates'))
        if not isinstance(rows, list):
            raise ValueError('Run must contain a list of candidates/observations')
        with self.transaction():
            if not self._register_import(sha, 'discovery_run', Path(path).name,
                    'legacy URL-merged metadata; discarded provider observations cannot be recovered' if 'observation_records' not in obj else 'lossless observation records'):
                return False
            stamp = now()
            run_id = 'import-' + sha
            self.db.execute('INSERT INTO runs VALUES (?,?,?,?,?)', (run_id, stamp, stamp, 'imported', encoded({k:v for k,v in obj.items() if k not in ['candidates','observation_records']})))
            for i, q in enumerate(obj.get('provider_runs', obj.get('log', []))):
                self.db.execute('INSERT INTO queries VALUES (?,?,?,?,?,?,?,?,?,?,?,?)',
                    (run_id + '-' + str(i), run_id, q.get('provider', obj.get('provider','unknown')), q.get('state','unknown'),
                     q.get('query','legacy_not_recorded'), obj.get('window',{}).get('from'), obj.get('window',{}).get('to'),
                     q['status'], q.get('count', q.get('returned')), int(q.get('capped',False)), q.get('error'), encoded(q)))
            for row in rows:
                self._observe(row, stamp, import_sha=sha)
            return True

    def import_tracker(self, folder):
        """Snapshot read-only input twice; changed files or dangling cluster links fail closed."""
        folder = Path(folder)
        names = ['records.csv', 'record_sources.csv', 'rejected.csv']
        blobs = {name: (folder / name).read_bytes() for name in names}
        if any((folder/name).read_bytes() != blobs[name] for name in names):
            raise ValueError('Tracker output changed during snapshot; retry after its build')
        sha = digest({name:digest(raw) for name,raw in blobs.items()})
        tables = {name:list(csv.DictReader(io.StringIO(raw.decode('utf-8-sig')))) for name,raw in blobs.items()}
        with self.transaction():
            if not self._register_import(sha, 'external_tracker', str(folder), encoded({name:digest(raw) for name,raw in blobs.items()})):
                return False
            stamp = now()
            records = {r['record_id']:r for r in tables['records.csv']}
            if len(records) != len(tables['records.csv']):
                raise ValueError('Duplicate external record ID')
            for key, row in records.items():
                # Report date and external classification remain proposals, never event_date.
                self.db.execute('INSERT INTO proposals VALUES (?,?,?,?)',
                                ('proposal-'+digest([sha,key]), sha, key, encoded(row)))
            for row in tables['record_sources.csv']:
                if row['record_id'] not in records:
                    raise ValueError('External source references absent record')
                proposal_id = 'proposal-' + digest([sha,row['record_id']])
                observation = {'url':row['link'], 'title':row['title'], 'publisher':row['source_name'],
                               'published_at_raw':row['date'], 'provider':row['origin'],
                               'proposed_state':records[row['record_id']]['state'], 'external_record_id':row['record_id'],
                               'date_note':'External earliest report date; not an event date', 'origin':'external_tracker'}
                doc_id = self._observe(observation, stamp, import_sha=sha)
                self.db.execute('INSERT OR IGNORE INTO proposal_documents VALUES (?,?)', (proposal_id,doc_id))
            for row in tables['rejected.csv']:
                self.db.execute('INSERT OR IGNORE INTO external_rejections VALUES (?,?,?)', ('reject-'+digest([sha,row]),sha,encoded(row)))
            return True

    def import_tracker_representatives(self,folder):
        """Retain resolved representative URLs without trusting claimed redirect equivalence."""
        folder=Path(folder)
        blobs={name:(folder/name).read_bytes() for name in ['records.csv','record_sources.csv','rejected.csv']}
        origin_sha=digest({name:digest(raw) for name,raw in blobs.items()})
        sha=digest(['tracker_representatives_v1',origin_sha])
        records=list(csv.DictReader(io.StringIO(blobs['records.csv'].decode('utf-8-sig'))))
        members=list(csv.DictReader(io.StringIO(blobs['record_sources.csv'].decode('utf-8-sig'))))
        with self.transaction():
            if not self._register_import(sha,'external_representatives',str(folder),'Reported publisher destinations; redirect equivalence unverified'):
                return False
            if not self.db.execute('SELECT 1 FROM imports WHERE digest=?',(origin_sha,)).fetchone():
                raise ValueError('Import tracker snapshot first')
            stamp=now()
            for row in records:
                doc_id=self._observe({'url':row['source_url'],'title':row['title'],'publisher':row['source_name'],
                        'published_at_raw':row['date'],'snippet':row['summary'],'proposed_state':row['state'],
                        'external_record_id':row['record_id'],'origin':'external_representative',
                        'date_note':'Earliest report date assigned by external pipeline, not verified publication or event date'},stamp,import_sha=sha)
                proposal='proposal-'+digest([origin_sha,row['record_id']])
                self.db.execute('INSERT OR IGNORE INTO proposal_documents VALUES (?,?)',(proposal,doc_id))
                for member in members:
                    if member['record_id']==row['record_id'] and member['is_representative'].lower() in ['true','1']:
                        original=self.document(member['link'],stamp)
                        if original!=doc_id:
                            self.db.execute('INSERT OR IGNORE INTO document_links VALUES (?,?,?,?,?,0)',
                                ('link-'+digest([original,doc_id]),original,doc_id,'reported_redirect',encoded({'import_digest':sha,'claim':'External pipeline reported this publisher destination; no local redirect trace'})))
            return True

    def _action(self, kind, entity, reviewer, reason, before, after):
        if not reviewer.strip() or not reason.strip():
            raise ValueError('Reviewer and reason are required')
        self.db.execute('INSERT INTO review_actions VALUES (?,?,?,?,?,?,?,?)',
                        (str(uuid.uuid4()),kind,entity,reviewer,now(),reason,encoded(before),encoded(after)))

    def review_document(self, doc_id, status, reviewer, reason, expected_revision):
        if status not in ['pending','reviewed','rejected']:
            raise ValueError('Invalid review status')
        with self.transaction():
            row = self.db.execute('SELECT * FROM documents WHERE id=?', (doc_id,)).fetchone()
            if not row or row['revision'] != expected_revision:
                raise ValueError('Missing document or stale review revision')
            self._action('document',doc_id,reviewer,reason,dict(row),{'review_status':status,'revision':expected_revision+1})
            self.db.execute('UPDATE documents SET review_status=?,revision=revision+1 WHERE id=?', (status,doc_id))

    def approve_event(self, event, reviewer, reason, expected_revision=0):
        self._validate_event(event)
        with self.transaction():
            row = self.db.execute('SELECT * FROM events WHERE id=?', (event['id'],)).fetchone()
            if (row['revision'] if row else 0) != expected_revision:
                raise ValueError('Stale event revision')
            if row and row['review_status'] == 'superseded':
                raise ValueError('Cannot approve a superseded event without explicit restoration')
            self._action('event',event['id'],reviewer,reason,dict(row) if row else {},event)
            self.db.execute("INSERT INTO events(id,payload,review_status,revision) VALUES (?,?,'approved',?) "
                            "ON CONFLICT(id) DO UPDATE SET payload=excluded.payload,review_status='approved',revision=excluded.revision",
                            (event['id'],encoded(event),expected_revision+1))
            self.db.execute('DELETE FROM event_sources WHERE event_id=?', (event['id'],))
            for sid in event['source_ids']:
                self.db.execute('INSERT INTO event_sources VALUES (?,?,?)',(event['id'],sid,event['date_basis']))

    def register_source(self,source,reviewer,reason):
        for field in ['id','url','title','publisher','evidence_summary','source_type']:
            if not source.get(field):raise ValueError('Missing evidence field: '+field)
        with self.transaction():
            if self.db.execute('SELECT 1 FROM sources WHERE id=?',(source['id'],)).fetchone():
                raise ValueError('Source ID already exists; use a new evidence version ID')
            doc_id=self.document(source['url'],now())
            self._action('source',source['id'],reviewer,reason,{},source)
            self.db.execute('INSERT INTO sources VALUES (?,?,?)',(source['id'],doc_id,encoded(source)))

    def merge_events(self,source_id,target_id,source_revision,target_revision,reviewer,reason):
        if source_id==target_id:raise ValueError('Cannot merge an event into itself')
        with self.transaction():
            rows=[self.db.execute('SELECT * FROM events WHERE id=?',(key,)).fetchone() for key in [source_id,target_id]]
            if any(r is None or r['review_status']!='approved' for r in rows):raise ValueError('Both events must be approved')
            source,target=[dict(r) for r in rows]
            if [source['revision'],target['revision']]!=[source_revision,target_revision]:raise ValueError('Stale event revisions')
            a=json.loads(source['payload']);b=json.loads(target['payload'])
            if (a['state'],a['stage'])!=(b['state'],b['stage']):raise ValueError('Different state or milestone stage; revise erroneous fields with evidence first')
            b['source_ids']=list(dict.fromkeys(b['source_ids']+a['source_ids']));b['source_count']=len(b['source_ids'])
            b['has_primary_source']=any(json.loads(self.db.execute('SELECT payload FROM sources WHERE id=?',(sid,)).fetchone()[0])['source_type'].startswith('primary_') for sid in b['source_ids'])
            before={'source':source,'target':target}
            for role,key in [('source',source_id),('target',target_id)]:
                before[role+'_links']=[dict(r) for r in self.db.execute('SELECT * FROM event_sources WHERE event_id=?',(key,))]
            self._action('event_merge',source_id,reviewer,reason,before,
                         {'source_id':source_id,'target_id':target_id,'source_revision':source_revision+1,'target_revision':target_revision+1})
            self.db.execute("UPDATE events SET review_status='superseded',superseded_by=?,revision=revision+1 WHERE id=?",(target_id,source_id))
            self.db.execute('UPDATE events SET payload=?,revision=revision+1 WHERE id=?',(encoded(b),target_id))
            self.db.execute('INSERT OR IGNORE INTO event_sources SELECT ?,source_id,evidence_basis FROM event_sources WHERE event_id=?',(target_id,source_id))
            return self.db.execute("SELECT id FROM review_actions WHERE entity_type='event_merge' ORDER BY rowid DESC LIMIT 1").fetchone()[0]

    def restore_merge(self,action_id,reviewer,reason):
        with self.transaction():
            action=self.db.execute("SELECT * FROM review_actions WHERE id=? AND entity_type='event_merge'",(action_id,)).fetchone()
            if action is None:raise ValueError('Unknown merge action')
            before=json.loads(action['before_payload']);after=json.loads(action['after_payload'])
            for role in ['source','target']:
                old=before[role];current=self.db.execute('SELECT * FROM events WHERE id=?',(old['id'],)).fetchone()
                if current['revision']!=after[role+'_revision']:raise ValueError('Events changed after merge; review intervening edits before restoration')
            self._action('event_merge_restore',action_id,reviewer,reason,after,before)
            for role in ['source','target']:
                old=before[role]
                self.db.execute('UPDATE events SET payload=?,review_status=?,superseded_by=?,revision=revision+1 WHERE id=?',
                                (old['payload'],old['review_status'],old['superseded_by'],old['id']))
                self.db.execute('DELETE FROM event_sources WHERE event_id=?',(old['id'],))
                for link in before[role+'_links']:
                    self.db.execute('INSERT INTO event_sources VALUES (?,?,?)',(old['id'],link['source_id'],link['evidence_basis']))

    def reserve_attempt(self, query_id, provider, cap):
        month = now()[:7]
        with self.transaction():
            used = self.db.execute('SELECT count(*) FROM provider_attempts WHERE provider=? AND month=?',(provider,month)).fetchone()[0]
            if used >= cap:
                raise RuntimeError('local_monthly_request_cap_reached')
            attempt_id = str(uuid.uuid4())
            self.db.execute('INSERT INTO provider_attempts(id,query_id,provider,month,reserved_at) VALUES (?,?,?,?,?)',
                            (attempt_id,query_id,provider,month,now()))
            return attempt_id

    def import_usage(self,path):
        raw=Path(path).read_bytes();sha=digest(raw);usage=json.loads(raw)
        with self.transaction():
            if not self._register_import(sha,'legacy_request_usage',Path(path).name,'Historical request reservations, conservative local cap migration'):
                return False
            run_id='usage-'+sha;stamp=now()
            self.db.execute('INSERT INTO runs VALUES (?,?,?,?,?)',(run_id,stamp,stamp,'imported',encoded({'kind':'legacy_request_usage'})))
            for key,count in usage.items():
                month,provider=key.split(':',1)
                if not isinstance(count,int) or count<0 or count>100000:raise ValueError('Invalid historical usage')
                date.fromisoformat(month+'-01')
                qid=run_id+'-'+provider
                self.db.execute('INSERT INTO queries VALUES (?,?,?,?,?,?,?,?,?,?,?,?)',(qid,run_id,provider,'account','historical usage baseline',None,None,'usage_import',count,0,None,'{}'))
                # Repeated snapshots of this cumulative legacy ledger must not double-charge.
                existing=self.db.execute("SELECT count(*) FROM provider_attempts WHERE provider=? AND month=? AND outcome='legacy_reserved'",(provider,month)).fetchone()[0]
                for i in range(max(0,count-existing)):
                    self.db.execute('INSERT INTO provider_attempts VALUES (?,?,?,?,?,?)',(str(uuid.uuid4()),qid,provider,month,stamp,'legacy_reserved'))
            return True

    def counts(self):
        tables = ['imports','runs','queries','documents','document_links','observations','sources','events','event_sources',
                  'proposals','proposal_documents','external_rejections','review_actions','retrievals','matches','provider_attempts']
        return {name:self.db.execute('SELECT count(*) FROM '+name).fetchone()[0] for name in tables}

    def audit(self):
        return {'schema_version':VERSION,'counts':self.counts(),
                'integrity_check':[r[0] for r in self.db.execute('PRAGMA integrity_check')],
                'foreign_key_failures':[list(r) for r in self.db.execute('PRAGMA foreign_key_check')],
                'pending_documents':self.db.execute("SELECT count(*) FROM documents WHERE review_status='pending'").fetchone()[0],
                'approved_events':self.db.execute("SELECT count(*) FROM events WHERE review_status='approved'").fetchone()[0],
                'latest_external_proposals':self.db.execute("SELECT count(*) FROM proposals WHERE import_digest=(SELECT digest FROM imports WHERE kind='external_tracker' ORDER BY imported_at DESC,digest DESC LIMIT 1)").fetchone()[0],
                'unfinished_queries':self.db.execute("SELECT count(*) FROM queries WHERE status IN ('planned','running')").fetchone()[0]}

    def collection_health(self):
        groups={}
        for row in self.db.execute("SELECT * FROM queries WHERE status<>'usage_import' ORDER BY provider,state,window_start,window_end"):
            key=(row['provider'],row['state'])
            group=groups.setdefault(key,{'provider':key[0],'state':key[1],'successful_windows':[],
                                         'potentially_truncated_queries':0,'failed_or_skipped':0,'unattempted_windows':[]})
            if row['status']=='ok' and row['window_start'] and row['window_end']:
                group['successful_windows'].append([row['window_start'],row['window_end']])
            if row['capped']:group['potentially_truncated_queries']+=1
            if row['status']!='ok':
                group['failed_or_skipped']+=1
                group['unattempted_windows'].append({'from':row['window_start'],'to':row['window_end'],'status':row['status']})
        for group in groups.values():
            merged=[];gaps=[]
            for low,high in sorted(set(tuple(w) for w in group['successful_windows'])):
                if not merged or low>merged[-1][1]:
                    if merged:gaps.append([merged[-1][1],low])
                    merged.append([low,high])
                else:merged[-1][1]=max(merged[-1][1],high)
            group['successful_windows']=merged;group['internal_window_gaps']=gaps
        return {'groups':list(groups.values()),'note':'Windows describe queries completed, not exhaustive article coverage. Capped and failed requests remain visible. This does not infer coverage before the first or after the last request.'}

    def backup(self, target):
        target = Path(target)
        target.parent.mkdir(parents=True, exist_ok=True)
        if target.resolve() == self.path.resolve():
            raise ValueError('Backup target must differ from active ledger')
        temporary = target.with_name(target.name + '.' + uuid.uuid4().hex + '.tmp')
        try:
            with closing(sqlite3.connect(temporary)) as dest:
                self.db.backup(dest)
                if dest.execute('PRAGMA integrity_check').fetchone()[0] != 'ok' or dest.execute('PRAGMA foreign_key_check').fetchone():
                    raise ValueError('Invalid backup')
            temporary.replace(target)
        finally:
            temporary.unlink(missing_ok=True)

    def export(self, directory):
        """Immutable export generation plus atomic CURRENT pointer; readers never see half a release."""
        directory = Path(directory)
        generation = directory / ('snapshot-' + uuid.uuid4().hex)
        generation.mkdir(parents=True)
        with self.transaction():
            events = [json.loads(r[0]) for r in self.db.execute("SELECT payload FROM events WHERE review_status='approved'")]
            events.sort(key=event_order)
            csv_write(generation/'reviewed_events.csv',events)
            latest=[json.loads(r[0]) for r in self.db.execute("SELECT payload FROM proposals WHERE import_digest=(SELECT digest FROM imports WHERE kind='external_tracker' ORDER BY imported_at DESC,digest DESC LIMIT 1) ORDER BY external_id")]
            csv_write(generation/'latest_external_proposals.csv',latest,['record_id','state','date','date_precision','title','summary','category','stage','source_name','source_url','review_status'])
            current=self.db.execute("SELECT value FROM meta WHERE key='matching_generation'").fetchone()
            matches=[]
            if current:
                for row in self.db.execute('SELECT * FROM matches ORDER BY id'):
                    features=json.loads(row['features'])
                    if features.get('input_generation')==current[0]:
                        matches.append({'match_id':row['id'],'left_document':row['left_id'],'right_document':row['right_id'],
                                        'score':features['score'],'warnings':features['warnings'],'shared_tokens':features['shared_tokens'],
                                        'decision':row['decision'],'revision':row['revision'],'rule_version':row['rule_version']})
            matches.sort(key=lambda r:(-r['score'],r['match_id']))
            csv_write(generation/'current_match_review_queue.csv',matches,['match_id','left_document','right_document','score','warnings','shared_tokens','decision','revision','rule_version'])
            for table in ['sources','documents','document_links','observations','queries','runs','proposals','proposal_documents','external_rejections','event_sources','review_actions','retrievals','matches']:
                cur = self.db.execute('SELECT * FROM '+table+' ORDER BY 1')
                csv_write(generation/(table+'.csv'),[dict(r) for r in cur], [c[0] for c in cur.description])
            report = self.audit()
            (generation/'quality.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
            observations=[]
            for row in self.db.execute('SELECT o.*,d.url,d.review_status FROM observations o JOIN documents d ON d.id=o.document_id ORDER BY o.observed_at,o.id'):
                item=json.loads(row['payload']);publication=item.get('publication_candidate',{})
                observations.append({'observation_id':row['id'],'document_id':row['document_id'],'title':item.get('title'),
                    'url':row['url'],'publisher':item.get('publisher'),'provider':item.get('provider',item.get('origin')),
                    'query_state_hint':item.get('query_state'),'external_state_hint':item.get('proposed_state'),
                    'publication_raw':item.get('published_at_raw',item.get('publication_date')),
                    'publication_candidate':publication.get('value'),'publication_warning':publication.get('warning'),
                    'observed_at':row['observed_at'],'review_status':row['review_status'],'query_id':row['query_id'],
                    'import_digest':row['import_digest'],'event_date':None})
            csv_write(generation/'candidate_observations.csv',observations,
                ['observation_id','document_id','title','url','publisher','provider','query_state_hint','external_state_hint',
                 'publication_raw','publication_candidate','publication_warning','observed_at','review_status','query_id','import_digest','event_date'])
            (generation/'collection_health.json').write_text(json.dumps(self.collection_health(),indent=2),encoding='utf-8')
        files = {p.name:digest(p.read_bytes()) for p in sorted(generation.iterdir())}
        (generation/'manifest.json').write_text(json.dumps({'files':files,'review_boundary':'Only reviewed_events.csv contains approved events; proposals and observations remain unverified.'},indent=2),encoding='utf-8')
        pointer = directory/('CURRENT.'+uuid.uuid4().hex+'.tmp')
        pointer.write_text(generation.name+'\n',encoding='utf-8')
        pointer.replace(directory/'CURRENT')
        return str(generation)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--db',type=Path,default=DEFAULT_DB)
    sub = p.add_subparsers(dest='command',required=True)
    sub.add_parser('init')
    for name in ['seed','import-run','import-tracker','import-usage','export','backup']:
        sub.add_parser(name).add_argument('path',type=Path)
    sub.add_parser('audit')
    r = sub.add_parser('review-document')
    r.add_argument('id');r.add_argument('status',choices=['pending','reviewed','rejected'])
    r.add_argument('--reviewer',required=True);r.add_argument('--reason',required=True);r.add_argument('--revision',type=int,required=True)
    for name in ['approve-event','register-source']:
        r=sub.add_parser(name);r.add_argument('path',type=Path);r.add_argument('--reviewer',required=True);r.add_argument('--reason',required=True)
        if name=='approve-event':r.add_argument('--revision',type=int,required=True)
    r=sub.add_parser('merge-events');r.add_argument('source');r.add_argument('target');r.add_argument('--source-revision',type=int,required=True);r.add_argument('--target-revision',type=int,required=True)
    r.add_argument('--reviewer',required=True);r.add_argument('--reason',required=True)
    r=sub.add_parser('restore-merge');r.add_argument('action_id');r.add_argument('--reviewer',required=True);r.add_argument('--reason',required=True)
    args=p.parse_args()
    with Ledger(args.db,create=args.command=='init') as ledger:
        if args.command in ['seed','import-run','import-tracker','import-usage','export','backup']:
            result=getattr(ledger,args.command.replace('-','_'))(args.path)
        elif args.command=='review-document':
            result=ledger.review_document(args.id,args.status,args.reviewer,args.reason,args.revision)
        elif args.command=='register-source':result=ledger.register_source(json.loads(args.path.read_text(encoding='utf-8')),args.reviewer,args.reason)
        elif args.command=='approve-event':result=ledger.approve_event(json.loads(args.path.read_text(encoding='utf-8')),args.reviewer,args.reason,args.revision)
        elif args.command=='merge-events':result=ledger.merge_events(args.source,args.target,args.source_revision,args.target_revision,args.reviewer,args.reason)
        elif args.command=='restore-merge':result=ledger.restore_merge(args.action_id,args.reviewer,args.reason)
        else:result=ledger.audit()
        print(json.dumps(result,indent=2))


if __name__=='__main__':
    main()
