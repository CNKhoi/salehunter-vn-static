import json
import tempfile
import unittest
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo
from scripts.update_feed import read_excluded_codes, snapshot, refresh_sources

@dataclass(frozen=True)
class Stub:
    key: str = 'news_shopee'
    name: str = 'test'
    loader: object = None
    max_age_hours: int = 72

class TrustTests(unittest.TestCase):
    def test_rejected_never_rendered_even_if_cache_contains_it(self):
        now=datetime(2026,10,14,15,0,tzinfo=ZoneInfo('Asia/Ho_Chi_Minh'))
        item={'id':'1','platform':'Shopee','source_key':'news_shopee','title':'Example',
              'code':'SVIPDDVKH0110MOC200A','last_seen':now.isoformat(),'url':'https://example.org',
              'published_at':now.isoformat()}
        cache={'sources':{},'totals':{}}
        src=Stub(loader=lambda:[item])
        refresh_sources(cache,[src],now)
        self.assertEqual(snapshot(cache,[src],now)['stats']['codes'],1)
        self.assertEqual(snapshot(cache,[src],now,excluded_codes={'SVIPDDVKH0110MOC200A'})['stats']['codes'],0)

    def test_denylist_load_validation(self):
        with tempfile.TemporaryDirectory() as temp:
            p=Path(temp)/'excluded_codes.json'
            p.write_text(json.dumps({'codes':[' abc123 ','evil!',42,'ABCD234']}),encoding='utf-8')
            self.assertEqual(read_excluded_codes(p),{'ABC123','ABCD234'})

    def test_bad_denylist_shape_is_error(self):
        with tempfile.TemporaryDirectory() as temp:
            p=Path(temp)/'excluded_codes.json'
            p.write_text(json.dumps({'codes':{}}),encoding='utf-8')
            with self.assertRaises(ValueError):read_excluded_codes(p)

if __name__=='__main__':unittest.main()
