import unittest
from pipeline import normalize_state, normalize_date, canonical_url, deduplicate

class DataIntegrityTests(unittest.TestCase):
    def test_state_variants(self):
        for raw in ['UP','Uttar Pradesh','Uttar-Pradesh','uttar pradesh']:
            self.assertEqual(normalize_state(raw),'Uttar Pradesh')
        with self.assertRaises(ValueError): normalize_state('Punjab')
    def test_partial_dates_are_not_invented(self):
        self.assertEqual(normalize_date('2025-09','month'),'2025-09')
        self.assertIsNone(normalize_date(None,'unknown'))
        for v,p in [('2025-02-30','day'),('01/02/2025','day'),('2026-11-11','day'),(None,'day'),('2025-01','day')]:
            with self.assertRaises(ValueError):normalize_date(v,p)
    def test_url_preserves_document_identity(self):
        self.assertEqual(canonical_url('https://EXAMPLE.org/doc?id=12&utm_source=x#top'),'https://example.org/doc?id=12')
    def test_duplicates_merge_but_milestones_and_pending_do_not(self):
        rows=[{'event_id':'mission-announcement','review_status':'accepted'},{'event_id':'mission-announcement','review_status':'accepted'},{'event_id':'mission-approval','review_status':'accepted'},{'event_id':None,'review_status':'pending'}]
        groups=deduplicate(rows)
        self.assertEqual(len(groups),2);self.assertEqual(len(groups['mission-announcement']),2)
    def test_accepted_observation_needs_identity(self):
        with self.assertRaises(ValueError):deduplicate([{'review_status':'accepted'}])

if __name__=='__main__':unittest.main()
