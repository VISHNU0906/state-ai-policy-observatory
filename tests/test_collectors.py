import unittest
import tempfile
from pathlib import Path
from unittest.mock import patch
import collectors

class AdapterContractTests(unittest.TestCase):
    def test_monthly_attempt_budget_stops_before_request(self):
        with tempfile.TemporaryDirectory() as directory,patch('collectors.ROOT',Path(directory)),patch.dict('os.environ',{'TAVILY_MONTHLY_REQUEST_CAP':'2'}):
            collectors.reserve_attempt('https://api.tavily.com/search')
            collectors.reserve_attempt('https://api.tavily.com/search')
            with self.assertRaisesRegex(RuntimeError,'request_cap'):
                collectors.reserve_attempt('https://api.tavily.com/search')
    def test_exa_date_is_not_event_date_and_author_not_publisher(self):
        fixture={'results':[{'title':'Policy','url':'https://example.org/p','publishedDate':'2026-11-01','author':'Reporter'}]}
        with patch.dict('os.environ',{'EXA_API_KEY':'test-only'}),patch('collectors.api',return_value=fixture):
            row=collectors.discover('exa','Kerala','2026-11-01','2026-11-08',5)[0]
        self.assertIsNone(row['publisher']);self.assertEqual(row['author'],'Reporter');self.assertNotIn('event_date',row)
    def test_crustdata_timestamp_is_not_publication(self):
        fixture={'success':True,'timestamp':123456,'results':[{'title':'Policy','url':'https://example.org/p','source':'news'}]}
        with patch.dict('os.environ',{'CRUSTDATA_API_KEY':'test-only'}),patch('collectors.api',return_value=fixture) as call:
            row=collectors.discover('crustdata','Kerala','2026-11-01','2026-11-08',5)[0]
        self.assertIsNone(row['published_at_raw']);self.assertEqual(call.call_args.args[2]['page'],1)
    def test_missing_credentials_never_call_service(self):
        with patch.dict('os.environ',{},clear=True),patch('collectors.api') as call:
            with self.assertRaisesRegex(RuntimeError,'missing_key'):collectors.discover('gnews','Kerala','2026-11-01','2026-11-08',5)
            call.assert_not_called()
    def test_gdelt_seen_date_not_published_date(self):
        with patch('collectors.api',return_value={'articles':[{'url':'https://example.org/p','seendate':'20261101T000000Z'}]}):
            row=collectors.discover('gdelt','Kerala','2026-11-01','2026-11-08',5)[0]
        self.assertIsNone(row['published_at_raw']);self.assertEqual(row['discovered_at_provider'],'20261101T000000Z')

if __name__=='__main__':unittest.main()
