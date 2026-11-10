import unittest
from normalization import normalize_state, normalize_date

class NormalizationTests(unittest.TestCase):
    def test_explicit_aliases_and_typographical_variants(self):
        for raw, expected in [('U.P.','Uttar Pradesh'),(' Uttar-Pradesh ','Uttar Pradesh'),
                              ('ＴＮ','Tamil Nadu'),('Telengana','Telangana'),('Orissa','Odisha'),
                              ('Maharastra','Maharashtra'),('Karnatka','Karnataka')]:
            result=normalize_state(raw)
            self.assertEqual(result['value'],expected);self.assertEqual(result['raw'],raw)
    def test_unknown_and_prose_are_not_assigned(self):
        for raw in ['Delhi','up to 20 centres','Karnatakaa','தமிழ்நாடு']:
            self.assertIsNone(normalize_state(raw)['value'])
        self.assertEqual(normalize_state('Karnatakaa')['suggestions'],['Karnataka'])
        self.assertEqual(normalize_state(None)['status'],'missing')
    def test_partial_and_named_dates(self):
        for raw, value, precision in [('2025','2025','year'),('February 2024','2024-02','month'),
                                     ('3rd March, 2025','2025-03-03','day'),('Nov 10 2026','2026-11-10','day')]:
            r=normalize_date(raw);self.assertEqual((r['value'],r['precision']),(value,precision))
        self.assertEqual(normalize_date('February 2024')['upper_bound'],'2024-02-29')
    def test_numeric_ambiguity_is_preserved(self):
        self.assertEqual(normalize_date('02/03/2025')['reason'],'ambiguous_numeric_date')
        self.assertEqual(normalize_date('02/03/2025',numeric_order='dayfirst')['value'],'2025-03-02')
        self.assertEqual(normalize_date('02/03/2025',numeric_order='monthfirst')['value'],'2025-02-03')
        self.assertEqual(normalize_date('13/02/2025')['value'],'2025-02-13')
        self.assertEqual(normalize_date('02/13/2025')['value'],'2025-02-13')
    def test_invalid_missing_approximate(self):
        for raw in ['2025-02-29','2025-13','31/02/2025']:
            self.assertEqual(normalize_date(raw)['reason'],'invalid_date')
        for raw in ['around March 2025','early 2025','last Tuesday','2025-03-01 to 2025-03-03']:
            self.assertEqual(normalize_date(raw)['status'],'needs_review')
        for raw in [None,'N/A','unknown','']:
            self.assertEqual(normalize_date(raw)['status'],'missing')
    def test_timezone_and_relative_anchor(self):
        self.assertEqual(normalize_date('2025-01-01T22:00:00Z')['value'],'2025-01-02')
        self.assertEqual(normalize_date('Wed, 01 Jan 2025 22:00:00 GMT')['value'],'2025-01-02')
        self.assertEqual(normalize_date('2025-01-01T22:00:00')['reason'],'timestamp_without_timezone')
        self.assertEqual(normalize_date('yesterday')['reason'],'relative_date_without_anchor')
        self.assertEqual(normalize_date('yesterday',anchor='2025-01-01')['value'],'2024-12-31')

if __name__=='__main__':unittest.main()
