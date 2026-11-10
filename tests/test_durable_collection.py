import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import collectors
from collect_durable import execute,plan,request_spec
from ledger import Ledger,ROOT


class DurableCollectionTests(unittest.TestCase):
    def setUp(self):
        (ROOT/'tmp').mkdir(exist_ok=True)
        self.temp=tempfile.TemporaryDirectory(dir=ROOT/'tmp')
        self.store=Ledger(Path(self.temp.name)/'test.sqlite',create=True)

    def tearDown(self):
        self.store.close();self.temp.cleanup()

    def plan(self,providers=None,states=None,limit=10,max_calls=12,split=False):
        return plan(self.store,providers or ['google-rss'],states or ['Kerala'],'2026-11-01','2026-11-08',limit,max_calls,split)

    def test_crash_resume_keeps_completed_query_without_repeating(self):
        run=self.plan(states=['Kerala','Tamil Nadu'])
        calls=[]
        def fetch(provider,state,*_):
            calls.append(state)
            if state=='Tamil Nadu':raise KeyboardInterrupt()
            return [{'url':'https://example.org/a','title':'Kerala policy'}]
        with self.assertRaises(KeyboardInterrupt):execute(self.store,run,fetch)
        self.assertEqual(self.store.counts()['observations'],1)
        execute(self.store,run,lambda *a:[{'url':'https://example.org/b'}])
        self.assertEqual(self.store.counts()['observations'],2)
        self.assertEqual(calls,['Kerala','Tamil Nadu'])
        execute(self.store,run,lambda *a:self.fail('Complete run replay made network call'))

    def test_rate_limit_records_skipped_states_and_other_provider_runs(self):
        run=self.plan(['gdelt','google-rss'],['Kerala','Tamil Nadu'])
        def fetch(provider,*_):
            if provider=='gdelt':raise RuntimeError('HTTP 429')
            return []
        result=execute(self.store,run,fetch,pause=lambda _:None)
        self.assertEqual([r['status'] for r in result['query_results']],['failed','skipped_provider_stopped','ok','ok'])

    def test_cross_provider_rows_not_discarded(self):
        run=self.plan(['google-rss','gdelt'])
        execute(self.store,run,lambda provider,*_:[{'url':'https://example.org/a','title':provider}],pause=lambda _:None)
        self.assertEqual(self.store.counts()['documents'],1)
        self.assertEqual(self.store.counts()['observations'],2)

    def test_budget_reservation_survives_failed_call(self):
        run=self.plan(['tavily'],['Kerala','Tamil Nadu'])
        def fetch(*_):
            collectors.reserve_attempt('https://api.tavily.com/search')
            raise RuntimeError('Network failure after retries')
        with patch.dict(os.environ,{'TAVILY_API_KEY':'test','TAVILY_MONTHLY_REQUEST_CAP':'1'}):
            execute(self.store,run,fetch)
        self.assertEqual(self.store.counts()['provider_attempts'],1)
        self.assertTrue(any('request_cap' in (r[0] or '') for r in self.store.db.execute('SELECT error FROM queries')))

    def test_saturation_splits_but_query_cap_records_unattempted_work(self):
        run=self.plan(limit=1,max_calls=2,split=True)
        result=execute(self.store,run,lambda *a:[{'url':'https://example.org/a'}])
        self.assertEqual(result['successful_queries'],2)
        self.assertGreater(result['queries'],2)
        self.assertTrue(any(r['status']=='skipped_query_budget' for r in result['query_results']))

    def test_forty_run_history_restore(self):
        for _ in range(40):execute(self.store,self.plan(),lambda *a:[{'url':'https://example.org/a'}])
        self.assertEqual(self.store.counts()['documents'],1)
        self.assertEqual(self.store.counts()['observations'],40)
        backup=Path(self.temp.name)/'copy.sqlite';self.store.backup(backup)
        with Ledger(backup) as restored:self.assertEqual(restored.audit(),self.store.audit())

    def test_submitted_query_records_exa_specific_text(self):
        spec=request_spec('exa','Kerala','2026-11-01','2026-11-08',50)
        self.assertEqual(spec['limit'],10)
        self.assertIn('state government',spec['query'])

    def test_internal_window_gap_is_reported(self):
        for start,end in [('2026-01-01','2026-01-08'),('2026-01-20','2026-01-27')]:
            run=plan(self.store,['google-rss'],['Kerala'],start,end,10,1)
            execute(self.store,run,lambda *a:[])
        self.assertEqual(self.store.collection_health()['groups'][0]['internal_window_gaps'],[['2026-01-08','2026-01-20']])


if __name__=='__main__':unittest.main()
