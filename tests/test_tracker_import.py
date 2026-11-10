import csv
import tempfile
import unittest
from pathlib import Path

from ledger import ROOT,Ledger


class TrackerImportTests(unittest.TestCase):
    def test_versions_and_report_dates_remain_proposals(self):
        (ROOT/'tmp').mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(dir=ROOT/'tmp') as directory:
            path=Path(directory)
            def write(name,rows):
                with (path/name).open('w',newline='',encoding='utf-8') as f:
                    w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
            record={'record_id':'EXT-1','state':'Kerala','title':'State signs AI agreement','date':'2025-01-01',
                    'source_name':'Example','source_url':'https://example.org/a','summary':'A proposed milestone','review_status':'auto'}
            write('records.csv',[record])
            write('record_sources.csv',[{'record_id':'EXT-1','is_representative':'True','link':'https://news.google.com/articles/one',
                                         'title':record['title'],'date':record['date'],'source_name':'Example','origin':'google-rss'}])
            write('rejected.csv',[{'title':'Livestock AI programme','reason':'artificial_insemination'}])
            with Ledger(path/'test.sqlite',create=True) as store:
                self.assertTrue(store.import_tracker(path));self.assertFalse(store.import_tracker(path))
                self.assertTrue(store.import_tracker_representatives(path));self.assertFalse(store.import_tracker_representatives(path))
                self.assertEqual(store.counts()['events'],0)
                self.assertEqual(store.counts()['document_links'],1)
                self.assertEqual(store.db.execute('SELECT verified FROM document_links').fetchone()[0],0)
                record['summary']='Changed external interpretation';write('records.csv',[record])
                store.import_tracker(path)
                self.assertEqual(store.counts()['proposals'],2)
                self.assertEqual(store.audit()['latest_external_proposals'],1)
                before=store.counts()
                write('record_sources.csv',[{'record_id':'missing','is_representative':'True','link':'https://example.org/a'}])
                with self.assertRaisesRegex(ValueError,'absent record'):store.import_tracker(path)
                self.assertEqual(before,store.counts())


if __name__=='__main__':unittest.main()
