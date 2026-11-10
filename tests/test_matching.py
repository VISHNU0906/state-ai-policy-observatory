import unittest
from matching import Matcher,tokens,evaluate


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


if __name__=='__main__':unittest.main()
