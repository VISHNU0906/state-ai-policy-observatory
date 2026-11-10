import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from ledger import Ledger,ROOT
from extract_ledger import retrieve


class EvidenceVersionTests(unittest.TestCase):
    def test_changed_text_retained_and_failures_do_not_overwrite_evidence(self):
        (ROOT/'tmp').mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(dir=ROOT/'tmp') as directory:
            root=Path(directory)
            with Ledger(root/'test.sqlite',create=True) as store,patch('extract_ledger.ROOT',root):
                with store.transaction():doc=store.document('https://example.org/policy','2026-11-10T00:00:00+00:00')
                first=retrieve(store,doc,extractor=lambda *a:{'text':'A'*150},permission=lambda *a:True)
                second=retrieve(store,doc,extractor=lambda *a:{'text':'B'*150},permission=lambda *a:True)
                third=retrieve(store,doc,permission=lambda *a:False)
                self.assertFalse(first['content_changed_since_previous_success'])
                self.assertTrue(second['content_changed_since_previous_success'])
                self.assertEqual(third['status'],'robots_disallowed')
                self.assertEqual(len(list((root/'.cache/content').glob('*/*.txt'))),2)
                self.assertEqual(store.counts()['retrievals'],3)


if __name__=='__main__':unittest.main()
