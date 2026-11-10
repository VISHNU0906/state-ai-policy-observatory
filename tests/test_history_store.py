import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from ledger import Ledger,ROOT
import history_store


class HistorySafetyTests(unittest.TestCase):
    def test_remote_advance_is_not_overwritten(self):
        (ROOT/'tmp').mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(dir=ROOT/'tmp') as directory:
            db=Path(directory)/'test.sqlite'
            Path(str(db)+'.history.json').write_text(json.dumps({'commit':'old'}))
            with patch('history_store.parent_ref',return_value='new'),patch('history_store.git') as git:
                with self.assertRaisesRegex(RuntimeError,'advanced'):history_store.persist(db)
                git.assert_not_called()

    def test_known_credential_value_blocks_publication(self):
        with tempfile.TemporaryDirectory(dir=ROOT/'tmp') as directory:
            db=Path(directory)/'test.sqlite'
            with Ledger(db,create=True) as store:
                with store.transaction():store.document('https://example.org/test-secret-value','2026-11-10')
            with patch('history_store.parent_ref',return_value=None),patch.dict('os.environ',{'TAVILY_API_KEY':'test-secret-value'}),patch('history_store.git') as git:
                with self.assertRaisesRegex(ValueError,'Credential'):history_store.persist(db,initialize=True)
                git.assert_not_called()

    def test_restore_never_replaces_existing_local_state(self):
        with tempfile.TemporaryDirectory(dir=ROOT/'tmp') as directory:
            db=Path(directory)/'test.sqlite';db.write_bytes(b'local')
            with self.assertRaisesRegex(ValueError,'already exists'):history_store.restore(db)
            self.assertEqual(db.read_bytes(),b'local')


if __name__=='__main__':unittest.main()
