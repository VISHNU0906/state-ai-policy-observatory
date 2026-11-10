import json
import sqlite3
import tempfile
import unittest
from pathlib import Path

from ledger import Ledger, ROOT, date_bounds, event_order, publication_candidate


class LedgerTests(unittest.TestCase):
    def setUp(self):
        (ROOT/'tmp').mkdir(exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(dir=ROOT/'tmp')
        self.root = Path(self.temp.name)
        self.store = Ledger(self.root/'test.sqlite',create=True)

    def tearDown(self):
        self.store.close()
        self.temp.cleanup()

    def write(self,name,value):
        path=self.root/name
        path.write_text(json.dumps(value),encoding='utf-8')
        return path

    def run_file(self,name='run.json',**extra):
        return self.write(name,{'candidates':[{'url':'https://example.org/a','title':'Policy signed','provider':'rss'}],**extra})

    def test_replay_and_new_observations_preserve_rejection(self):
        path=self.run_file()
        self.assertTrue(self.store.import_run(path))
        doc=self.store.db.execute('SELECT * FROM documents').fetchone()
        self.store.review_document(doc['id'],'rejected','tester','Unrelated article',0)
        before=self.store.counts()
        self.assertFalse(self.store.import_run(path))
        self.assertEqual(before,self.store.counts())
        self.store.import_run(self.run_file('later.json',run_id='another-day'))
        self.assertEqual(self.store.counts()['documents'],1)
        self.assertEqual(self.store.counts()['observations'],2)
        self.assertEqual(self.store.db.execute('SELECT review_status FROM documents').fetchone()[0],'rejected')
        with self.assertRaisesRegex(ValueError,'stale'):
            self.store.review_document(doc['id'],'pending','tester','Stale edit',0)

    def test_invalid_import_rolls_back_every_table(self):
        before=self.store.counts()
        path=self.write('bad.json',{'candidates':[{'url':'https://example.org/a'},{'url':'invalid'}]})
        with self.assertRaises(ValueError):self.store.import_run(path)
        self.assertEqual(before,self.store.counts())

    def test_cross_provider_conflicts_retained(self):
        path=self.write('conflict.json',{'observation_records':[
            {'url':'https://example.org/a','provider':'a','published_at_raw':'2025-01-01'},
            {'url':'https://example.org/a?utm_source=b','provider':'b','published_at_raw':'2025-02-01'}]})
        self.store.import_run(path)
        self.assertEqual(self.store.counts()['documents'],1)
        self.assertEqual(self.store.counts()['observations'],2)
        with self.assertRaises(sqlite3.IntegrityError):
            self.store.db.execute("UPDATE observations SET payload='{}'")

    def test_seed_counts_replay_and_changed_seed_rejected(self):
        self.store.seed(ROOT/'data/events.json')
        self.assertEqual(self.store.counts()['events'],85)
        self.assertEqual(self.store.counts()['sources'],113)
        self.assertEqual(self.store.counts()['event_sources'],137)
        before=self.store.counts()
        self.assertFalse(self.store.seed(ROOT/'data/events.json'))
        obj=json.loads((ROOT/'data/events.json').read_text(encoding='utf-8'))
        obj['events'][0]['title']='Changed claim'
        with self.assertRaisesRegex(ValueError,'explicit revision'):
            self.store.seed(self.write('changed.json',obj))
        self.assertEqual(before,self.store.counts())

    def test_backup_restore_and_exports(self):
        self.store.seed(ROOT/'data/events.json')
        self.store.import_run(self.run_file())
        backup=self.root/'backup.sqlite'
        self.store.backup(backup)
        with Ledger(backup) as restored:
            self.assertEqual(restored.audit(),self.store.audit())
        one=Path(self.store.export(self.root/'exports'))
        two=Path(self.store.export(self.root/'exports'))
        self.assertEqual((one/'reviewed_events.csv').read_bytes(),(two/'reviewed_events.csv').read_bytes())
        self.assertEqual((self.root/'exports/CURRENT').read_text().strip(),two.name)

    def test_missing_database_does_not_silently_reset(self):
        with self.assertRaises(FileNotFoundError):Ledger(self.root/'missing.sqlite')

    def test_partial_date_sort_and_raw_publication(self):
        self.assertEqual(date_bounds('2024-02','month'),('2024-02-01','2024-02-29'))
        with self.assertRaises(ValueError):date_bounds('2025-02-29','day')
        rows=[{'id':str(i),'state':'Kerala','event_date':d,'date_precision':p} for i,(d,p) in enumerate([(None,'unknown'),('2025','year'),('2025-01','month'),('2025-01-01','day')])]
        self.assertEqual([e['date_precision'] for e in sorted(rows,key=event_order)],['day','month','year','unknown'])
        self.assertEqual(publication_candidate('2025-01-02T01:00:00+05:30')['value'],'2025-01-01T19:30:00+00:00')
        self.assertEqual(publication_candidate('2025-01-02T01:00:00')['warning'],'timestamp_without_timezone')

    def test_foreign_keys_and_audit_immutable(self):
        self.store.import_run(self.run_file())
        doc=self.store.db.execute('SELECT id FROM documents').fetchone()[0]
        self.store.review_document(doc,'reviewed','tester','Evidence read',0)
        with self.assertRaises(sqlite3.IntegrityError):self.store.db.execute('DELETE FROM review_actions')
        with self.assertRaises(sqlite3.IntegrityError):self.store.db.execute("INSERT INTO event_sources VALUES ('absent','absent','test')")

    def test_manual_merge_restore_keeps_ids_links_and_revision_guards(self):
        self.store.seed(ROOT/'data/events.json')
        events=[json.loads(r[0]) for r in self.store.db.execute('SELECT payload FROM events')]
        a=events[0]
        b=next(e for e in events[1:] if (e['state'],e['stage'])==(a['state'],a['stage']))
        # Synthetic operation in a temporary database, not an adjudication of production events.
        before=[tuple(r) for r in self.store.db.execute('SELECT * FROM event_sources ORDER BY 1,2')]
        action=self.store.merge_events(a['id'],b['id'],1,1,'test reviewer','Synthetic reversal test')
        self.assertEqual(self.store.audit()['approved_events'],84)
        self.assertEqual(self.store.counts()['events'],85)
        self.store.restore_merge(action,'test reviewer','Restore synthetic operation')
        self.assertEqual(self.store.audit()['approved_events'],85)
        self.assertEqual(before,[tuple(r) for r in self.store.db.execute('SELECT * FROM event_sources ORDER BY 1,2')])
        with self.assertRaisesRegex(ValueError,'changed after merge'):self.store.restore_merge(action,'tester','Replay')

    def test_failed_approval_does_not_leave_event_or_review_action(self):
        self.store.seed(ROOT/'data/events.json')
        event=json.loads(self.store.db.execute('SELECT payload FROM events LIMIT 1').fetchone()[0])
        event.update(id='test-new',source_ids=['missing-source'])
        before=self.store.counts()
        with self.assertRaises(sqlite3.IntegrityError):self.store.approve_event(event,'tester','Synthetic failure',0)
        self.assertEqual(before,self.store.counts())


if __name__=='__main__':unittest.main()
