import json
import tempfile
import unittest
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo
from scripts.update_feed import read_recent_successes, snapshot, refresh_sources

NOW = datetime(2026, 10, 15, 10, 0, tzinfo=ZoneInfo('Asia/Ho_Chi_Minh'))

@dataclass(frozen=True)
class TestSource:
    key: str = 'manual'
    name: str = 'Test'
    loader: object = None
    max_age_hours: int = 72

def coupon(code='DEAL123456'):
    return {'id':code,'platform':'Shopee','code':code,'source_key':'manual',
            'title':'Example voucher','url':'https://example.com',
            'published_at':NOW.isoformat(), 'expires_at':None}

class VerificationTests(unittest.TestCase):
    def make(self, record):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'verified_codes.json'
            p.write_text(json.dumps({'records':[record]}),encoding='utf-8')
            return read_recent_successes(p,NOW)

    def test_only_actual_checkout_success_accepts(self):
        rec={'platform':'Shopee','code':'DEAL123456','successful_at':NOW.isoformat(),
             'basis':'public_listed','context':'Mã chỉ được niêm yết trên website'}
        self.assertEqual(self.make(rec),{})
        rec['basis']='checkout_success'
        self.assertEqual(self.make(rec),{('Shopee','DEAL123456'):NOW.isoformat()})

    def test_old_or_future_test_not_confirmed(self):
        for t in (NOW-timedelta(hours=25),NOW+timedelta(minutes=1)):
            rec={'platform':'Shopee','code':'DEAL123456','successful_at':t.isoformat(),
                 'basis':'checkout_success','context':'Đã thử hoàn tất đơn thành công'}
            self.assertEqual(self.make(rec),{})

    def test_denylist_beats_success_report(self):
        src=TestSource(loader=lambda:[coupon()]); cache={'sources':{},'totals':{}}
        refresh_sources(cache,[src],NOW)
        result=snapshot(cache,[src],NOW,excluded_codes={'DEAL123456'},
                        verified_codes={('Shopee','DEAL123456'):NOW.isoformat()})
        self.assertEqual(result['stats']['all'],0)

    def test_unverified_not_advertised_as_success(self):
        src=TestSource(loader=lambda:[coupon()]); cache={'sources':{},'totals':{}}
        refresh_sources(cache,[src],NOW)
        result=snapshot(cache,[src],NOW)
        self.assertEqual(result['stats']['recent_success'],0)
        self.assertEqual(result['items'][0]['verification_status'],'unverified')

    def test_recent_success_flagged_in_feed(self):
        src=TestSource(loader=lambda:[coupon()]); cache={'sources':{},'totals':{}}
        refresh_sources(cache,[src],NOW)
        result=snapshot(cache,[src],NOW,verified_codes={('Shopee','DEAL123456'):NOW.isoformat()})
        self.assertEqual(result['stats']['recent_success'],1)
        self.assertEqual(result['items'][0]['verification_status'],'recent_success')

if __name__=='__main__':unittest.main()
