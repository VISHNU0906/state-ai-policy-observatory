import unittest
import json
import tempfile
from pathlib import Path
from unittest.mock import patch
from ledger import ROOT,Ledger
from matching import Matcher,tokens,evaluate,queue,decide


class MatchingTests(unittest.TestCase):
    def test_reversal_guard_uses_word_boundaries(self):
        a='UP signs Puch AI agreement';b='UP cancels Puch AI agreement'
        result=Matcher([a,b]).compare(a,b)
        self.assertIn('reversal_milestone_conflict',result['warnings'])
        self.assertFalse(result['automatic_merge'])

    def test_decimals_preserved_and_stage_conflicts_visible(self):
        self.assertIn('122.6',tokens('Rs 122.6 crore'))
        result=Matcher([]).compare('State approves AI mission','State signs AI mission agreement')
        self.assertIn('different_stage_cues',result['warnings'])

    def test_diagnostic_evaluation_has_all_labelled_pairs(self):
        report=evaluate()
        self.assertEqual(report['labelled_pairs'],34)
        self.assertEqual(report['positive_pairs'],12)
        self.assertTrue(all(not r['automatic_merge'] for r in report['results']))

    def test_distinct_decision_survives_rerun_and_rule_revision(self):
        with tempfile.TemporaryDirectory(dir=ROOT/'tmp') as directory:
            path=Path(directory);run=path/'run.json'
            run.write_text(json.dumps({'candidates':[{'url':'https://example.org/a','title':'Kerala Sarvam AI agreement signed'},
                                                     {'url':'https://example.org/b','title':'Kerala Sarvam AI agreement signed'}]}))
            with Ledger(path/'test.sqlite',create=True) as store:
                store.import_run(run);queue(store)
                match=store.db.execute('SELECT * FROM matches').fetchone()
                decide(store,match['id'],'distinct','test reviewer','Same title, different instruments',0)
                queue(store)
                self.assertEqual(store.db.execute('SELECT decision FROM matches').fetchone()[0],'distinct')
                with patch('matching.RULE_VERSION','next-rule'):queue(store)
                self.assertTrue(all(r[0]=='distinct' for r in store.db.execute('SELECT decision FROM matches')))
                self.assertEqual(store.counts()['events'],0)


if __name__=='__main__':unittest.main()
