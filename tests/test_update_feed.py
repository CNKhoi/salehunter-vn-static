"""Fast, deterministic tests: no network access, no synthetic coupons shown to users."""
import json
import tempfile
import unittest
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

from collectors import make_offer
from scripts.update_feed import refresh_sources, snapshot, read_json, write_json

TZ = ZoneInfo('Asia/Ho_Chi_Minh')
NOW = datetime(2026, 10, 14, 12, 0, tzinfo=TZ)


@dataclass(frozen=True)
class FakeSource:
    key: str
    name: str
    loader: object
    max_age_hours: int = 72


def offer(platform='Shopee', code=None, days=0, title='Chương trình thử nghiệm nội bộ'):
    # Examples exist only in unit tests and never enter the shipped feed.
    from hashlib import md5
    key = f'{platform}|{code}|{days}|{title}'
    return {
        'id': md5(key.encode()).hexdigest(), 'source_key': 'news_shopee',
        'title': title, 'platform': platform, 'code': code, 'kind': 'Voucher',
        'description': 'Mẫu kiểm thử nội bộ', 'source': 'Bài kiểm thử',
        'published_at': (NOW-timedelta(days=days)).isoformat(),
        'expires_at': None, 'direct_link': False, 'url': 'https://example.org/deal',
        'discount': '', 'min_spend': ''
    }


class StaticFeedTests(unittest.TestCase):
    def test_no_source_items(self):
        src = FakeSource('news_shopee', 'Tin Shopee', lambda: [])
        cache = {'sources': {}, 'totals': {}}
        refresh_sources(cache, [src], NOW)
        self.assertEqual(snapshot(cache, [src], NOW)['stats']['all'], 0)
        self.assertEqual(snapshot(cache, [src], NOW)['sources'][0]['ok'], True)

    def test_success_then_fail_keeps_data(self):
        item = offer(code='ABCD1234')
        s1 = FakeSource('news_shopee', 'Shopee', lambda: [dict(item)])
        cache = {'sources': {}, 'totals': {}}
        refresh_sources(cache, [s1], NOW)
        def fail():
            raise ConnectionError('secret HTTP URL: should not be logged')
        s2 = FakeSource('news_shopee', 'Shopee', fail)
        refresh_sources(cache, [s2], NOW + timedelta(minutes=30))
        out = snapshot(cache, [s2], NOW + timedelta(minutes=30))
        self.assertEqual(out['stats']['all'], 1)
        self.assertTrue(out['items'][0]['stale'])
        self.assertTrue(out['has_source_errors'])
        self.assertNotIn('secret HTTP', json.dumps(out))

    def test_success_empty_retires_prior_items(self):
        old = offer()
        cache = {'sources': {}, 'totals': {}}
        src = FakeSource('news_shopee', 'Shopee', lambda: [old])
        refresh_sources(cache, [src], NOW)
        refresh_sources(cache, [FakeSource('news_shopee', 'Shopee', lambda: [])], NOW)
        self.assertEqual(snapshot(cache, [src], NOW)['stats']['all'], 0)

    def test_old_news_cutoff(self):
        old = offer(days=10)
        cache = {'sources': {}, 'totals': {}}
        src = FakeSource('news_shopee', 'Shopee', lambda: [old])
        refresh_sources(cache, [src], NOW)
        self.assertEqual(snapshot(cache, [src], NOW)['stats']['all'], 0)

    def test_expiry(self):
        item = offer()
        item['expires_at'] = (NOW-timedelta(minutes=1)).isoformat()
        cache = {'sources': {}, 'totals': {}}
        src = FakeSource('manual', 'Nhập tay', lambda: [item])
        refresh_sources(cache, [src], NOW)
        self.assertEqual(snapshot(cache, [src], NOW)['stats']['all'], 0)

    def test_duplicate_cross_sources(self):
        item = offer(code='ABCD1234')
        copy = dict(item, id='other-ID', source_key='news_tiktok')
        cache = {'sources': {}, 'totals': {}}
        a = FakeSource('news_shopee', 'A', lambda: [item])
        b = FakeSource('news_tiktok', 'B', lambda: [copy])
        refresh_sources(cache, [a, b], NOW)
        self.assertEqual(snapshot(cache, [a, b], NOW)['stats']['all'], 1)

    def test_two_platforms_same_code_allowed(self):
        item = offer(code='ABCD1234')
        copy = dict(item, id='other-ID', source_key='news_tiktok', platform='TikTok Shop')
        a = FakeSource('news_shopee', 'A', lambda: [item])
        b = FakeSource('news_tiktok', 'B', lambda: [copy])
        cache = {'sources': {}, 'totals': {}}
        refresh_sources(cache, [a, b], NOW)
        self.assertEqual(snapshot(cache, [a, b], NOW)['stats']['all'], 2)

    def test_bad_source_no_replacement(self):
        item = offer()
        cache = {'sources': {}, 'totals': {}}
        refresh_sources(cache, [FakeSource('manual', 'M', lambda: [item])], NOW)
        refresh_sources(cache, [FakeSource('manual', 'M', lambda: {'oops':'bad'})], NOW)
        self.assertEqual(snapshot(cache, [FakeSource('manual','M',lambda:[])], NOW)['stats']['all'], 1)

    def test_first_seen_stable(self):
        item = offer()
        cache = {'sources': {}, 'totals': {}}
        src = FakeSource('news_shopee', 'S', lambda: [dict(item)])
        refresh_sources(cache, [src], NOW)
        original = cache['sources']['news_shopee']['items'][0]['first_seen']
        refresh_sources(cache, [src], NOW + timedelta(minutes=5))
        self.assertEqual(cache['sources']['news_shopee']['items'][0]['first_seen'], original)

    def test_read_write_json(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / 'feed.json'
            write_json(p, {'schema_version':1, 'unicode':'Đồng'})
            self.assertEqual(read_json(p, {})['unicode'], 'Đồng')

    def test_invalid_payload_raises(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / 'feed.json'
            p.write_text('[]', encoding='utf-8')
            with self.assertRaises(ValueError):
                read_json(p, {})

    def test_source_errors_exposed(self):
        cache = {'sources': {}, 'totals': {}}
        def fail():
            raise TimeoutError()
        src = FakeSource('news_shopee', 'S', fail)
        refresh_sources(cache, [src], NOW)
        st = snapshot(cache, [src], NOW)['sources'][0]
        self.assertEqual(st['ok'], False)
        self.assertIn('TimeoutError', st['error'])


if __name__ == '__main__':
    unittest.main()
