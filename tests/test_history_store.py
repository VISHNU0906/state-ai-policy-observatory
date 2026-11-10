import json
import tempfile
import gzip
from types import SimpleNamespace
import unittest
from pathlib import Path
from unittest.mock import patch

from ledger import Ledger,ROOT,digest
import history_store


class HistorySafetyTests(unittest.TestCase):
    def setUp(self):
        (ROOT/'tmp').mkdir(exist_ok=True)

    def test_small_edit_reuses_unchanged_blocks_and_restores_exact_bytes(self):
        size=history_store.BLOCK_SIZE
        original=b'A'*size+b'B'*size+b'C'*123
        first,new=history_store.block_plan(original)
        for i,b in enumerate(first):b['git_blob']=str(i)*40
        changed=original[:size+10]+b'X'+original[size+11:]
        blocks,new=history_store.block_plan(changed,first)
        self.assertEqual(len(new),1)
        for b in blocks:
            if 'git_blob' not in b:b['git_blob']='f'*40
        contents={b['git_blob']:gzip.compress(changed[i*size:(i+1)*size],mtime=0) for i,b in enumerate(blocks)}
        response=b''.join(f'{oid} blob {len(raw)}\n'.encode()+raw+b'\n' for oid,raw in contents.items())
        manifest={'database_bytes':len(changed),'blocks':blocks}
        with patch('history_store.git',return_value=SimpleNamespace(stdout=response)):
            self.assertEqual(history_store.read_blocks(manifest),changed)
            manifest['blocks'][0]['sha256']='bad'
            with self.assertRaisesRegex(ValueError,'checksum'):history_store.read_blocks(manifest)

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

    def test_refresh_refuses_unpublished_local_reviews(self):
        with tempfile.TemporaryDirectory(dir=ROOT/'tmp') as directory:
            path=Path(directory);db=path/'test.sqlite'
            with Ledger(db,create=True) as store:
                store.backup(path/'baseline.sqlite')
                Path(str(db)+'.history.json').write_text(json.dumps({'commit':'old','database_sha256':digest((path/'baseline.sqlite').read_bytes())}))
                with store.transaction():store.document('https://example.org/new','2026-11-10')
            with patch('history_store.restore') as restore:
                with self.assertRaisesRegex(ValueError,'unpublished changes'):history_store.refresh(db)
                restore.assert_not_called()


if __name__=='__main__':unittest.main()
