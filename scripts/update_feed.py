"""Build static JSON feed from public sources in a scheduled GitHub Actions job.

Per-source JSON cache survives HTTP errors and prevents failed sources from
silently deleting previously successful offers. No fake offers or account APIs.
"""
from __future__ import annotations

import json
import os
import re
import sys
import unicodedata
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from collectors import build_sources, parse_date  # noqa: E402

VN = ZoneInfo('Asia/Ho_Chi_Minh')
FEED_PATH = ROOT / 'data' / 'offers.json'
CACHE_PATH = ROOT / 'data' / 'source_cache.json'


def read_json(path: Path, default: dict) -> dict:
    if not path.exists():
        return default
    result = json.loads(path.read_text(encoding='utf-8'))
    if not isinstance(result, dict):
        raise ValueError(f'{path.name} phải là object JSON')
    return result


def write_json(path: Path, payload: dict):
    # Atomic replace: even a broken job cannot leave a half-written JSON file.
    tmp = path.with_suffix(path.suffix + '.tmp')
    tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + '\n', encoding='utf-8')
    tmp.replace(path)


def parse_iso(value: str | None):
    return parse_date(value) if value else None


def read_excluded_codes(path: Path) -> set[str]:
    """Operator-maintained denylist: user reports are NOT marketplace-wide verification."""
    payload = read_json(path, {'codes': []})
    codes = payload.get('codes', [])
    if not isinstance(codes, list):
        raise ValueError('excluded_codes.json: codes phải là mảng')
    import re
    valid = re.compile(r'^[A-Z0-9][A-Z0-9_-]{4,27}$')
    return {v.strip().upper() for value in codes if isinstance(value, str)
            if (v := value.strip().upper()) and valid.fullmatch(v)}



def read_recent_successes(path: Path, now: datetime) -> dict[tuple[str, str], str]:
    """Opt-in attestations by the operator, NOT marketplace API verification.

    A record is trusted for presentation for at most 24h and must mention an
    actual successful checkout application test. Merely finding a code online
    can never upgrade it to a tested code.
    """
    data = read_json(path, {'records': []})
    records = data.get('records', [])
    if not isinstance(records, list):
        raise ValueError('verified_codes.json: records phải là mảng')
    if len(records) > 300:
        raise ValueError('verified_codes.json: quá nhiều bản ghi')
    accepted = {}
    for rec in records:
        if not isinstance(rec, dict) or rec.get('basis') != 'checkout_success':
            continue
        platform = rec.get('platform')
        code = str(rec.get('code') or '').strip().upper()
        verified = parse_iso(rec.get('successful_at'))
        context = str(rec.get('context') or '').strip()
        if (platform not in ('Shopee', 'TikTok Shop')
            or not re.fullmatch(r'[A-Z0-9][A-Z0-9_-]{4,27}', code)
            or not verified or not (timedelta(0) <= now - verified <= timedelta(hours=24))
            or len(context) < 10):
            continue
        key = (platform, code)
        if key not in accepted or verified.isoformat() > accepted[key]:
            accepted[key] = verified.isoformat()
    return accepted

def refresh_sources(cache: dict, sources: list, now: datetime, max_workers: int = 4):
    cache.setdefault('sources', {})
    cache.setdefault('totals', {'scans': 0, 'failed_scans': 0})
    attempts = []
    with ThreadPoolExecutor(max_workers=max(1, min(max_workers, len(sources)))) as pool:
        futures = {pool.submit(source.loader): source for source in sources}
        for future in as_completed(futures):
            source = futures[future]
            key = source.key
            prev = cache['sources'].get(key, {})
            stamp = now.isoformat()
            try:
                items = future.result()
                if not isinstance(items, list):
                    raise ValueError('Nguồn không trả về danh sách')
                # Only validated items should be supplied by collectors.
                if any(not isinstance(x, dict) or not x.get('id') for x in items):
                    raise ValueError('Nguồn trả về item không hợp lệ')
                old_by_id = {x['id']: x for x in prev.get('items', []) if isinstance(x, dict) and x.get('id')}
                for item in items:
                    item['first_seen'] = old_by_id.get(item['id'], {}).get('first_seen', stamp)
                    item['last_seen'] = stamp
                cache['sources'][key] = {
                    'name': source.name, 'ok': True, 'count': len(items),
                    'last_attempt': stamp, 'last_success': stamp, 'error': None, 'items': items,
                }
                attempts.append((key, True, len(items)))
            except Exception as exc:
                # Error never discards the previous successful data for this source.
                cache['sources'][key] = {
                    'name': source.name, 'ok': False, 'count': prev.get('count', 0),
                    'last_attempt': stamp, 'last_success': prev.get('last_success'),
                    'error': type(exc).__name__ + ': không đọc được nguồn',
                    'items': prev.get('items', []),
                }
                attempts.append((key, False, 0))
    cache['totals']['scans'] = int(cache['totals'].get('scans', 0)) + len(attempts)
    cache['totals']['failed_scans'] = int(cache['totals'].get('failed_scans', 0)) + sum(not good for _, good, _ in attempts)
    return attempts


def snapshot(cache: dict, sources: list, now: datetime, limit: int = 200, excluded_codes: set[str] | None = None,
             verified_codes: dict[tuple[str, str], str] | None = None) -> dict:
    known = cache.get('sources', {})
    excluded_codes = excluded_codes or set()
    verified_codes = verified_codes or {}
    candidates = []
    statuses = []
    for source in sources:
        st = known.get(source.key, {})
        stale = st.get('ok') is False
        statuses.append({
            'key': source.key, 'name': source.name, 'ok': st.get('ok'),
            'count': st.get('count', 0), 'last_success': st.get('last_success'),
            'last_attempt': st.get('last_attempt'), 'error': st.get('error'),
        })
        for item in st.get('items', []):
            if not isinstance(item, dict) or not item.get('id'):
                continue
            if str(item.get('code') or '').strip().upper() in excluded_codes:
                continue
            expires = parse_iso(item.get('expires_at'))
            if expires and expires <= now:
                continue
            seen = parse_iso(item.get('last_seen'))
            if not seen:
                continue
            published = parse_iso(item.get('published_at'))
            relevant = published or seen
            if source.key != 'manual' and not source.key.startswith('feed_'):
                if now - relevant > timedelta(hours=source.max_age_hours):
                    continue
            record = dict(item)
            record['stale'] = stale
            record['source_unavailable'] = stale
            code = str(record.get('code') or '').strip().upper()
            verified_at = verified_codes.get((record.get('platform'), code)) if code and not stale else None
            record['verification_status'] = 'recent_success' if verified_at else 'unverified'
            record['verified_at'] = verified_at
            record['verification'] = ('Đã có thử áp dụng thành công gần đây (theo quản trị viên; không bảo đảm cho mọi tài khoản)'
                                      if verified_at else 'Chưa có bằng chứng áp dụng thành công tại thanh toán')
            candidates.append(record)
    def rank(o):
        return (not o['stale'], o['source_key'] == 'manual' or o['source_key'].startswith('feed_'),
                bool(o.get('code')), bool(o.get('direct_link')),
                o.get('published_at') or o.get('last_seen') or '')
    candidates.sort(key=rank, reverse=True)
    chosen = []
    signatures = set()
    per_source = {}
    quota = max(15, limit // 2)
    # Two-pass selection avoids a large RSS provider hiding all other sources.
    for limit_by_source in (True, False):
        for item in candidates:
            name = item['source_key']
            normalized = unicodedata.normalize('NFKC', str(item['title'])).casefold().strip()
            signature = (item['platform'], item.get('code') or normalized)
            if signature in signatures:
                continue
            if limit_by_source and per_source.get(name, 0) >= quota:
                continue
            signatures.add(signature)
            per_source[name] = per_source.get(name, 0) + 1
            chosen.append(item)
            if len(chosen) >= limit:
                break
        if len(chosen) >= limit:
            break
    success = max((s['last_success'] for s in statuses if s['last_success']), default=None)
    attempt = max((s['last_attempt'] for s in statuses if s['last_attempt']), default=None)
    totals = cache.get('totals', {})
    stats = {
        'all': len(chosen),
        'shopee': sum(x['platform'] == 'Shopee' for x in chosen),
        'tiktok': sum(x['platform'] == 'TikTok Shop' for x in chosen),
        'codes': sum(bool(x.get('code')) for x in chosen),
        'recent_success': sum(x.get('verification_status') == 'recent_success' for x in chosen),
        'stale': sum(bool(x.get('stale')) for x in chosen),
        'scans': totals.get('scans', 0),
        'failed_scans': totals.get('failed_scans', 0),
    }
    return {
        'schema_version': 1, 'items': chosen, 'sources': statuses, 'stats': stats,
        'last_updated': success, 'last_attempt': attempt,
        'is_scanning': False,
        'has_source_errors': any(s['ok'] is False for s in statuses),
        'refresh_minutes': 30,
        'notice': 'Mã nhập tay từ nguồn ngoài chưa được mặc định xem là mã dùng được. Chỉ mã đã thử áp dụng gần đây do quản trị viên xác nhận mới xuất hiện ở tab chính.',
    }


def main():
    now = datetime.now(VN)
    feeds = [s.strip() for s in os.getenv('EXTERNAL_FEEDS', '').split(',') if s.strip()]
    sources = build_sources(
        ROOT / 'data' / 'manual_offers.json',
        news=os.getenv('ENABLE_NEWS', 'true').lower() in ('1', 'true', 'yes'),
        blog=os.getenv('ENABLE_BLOG', 'true').lower() in ('1', 'true', 'yes'),
        external_feeds=feeds,
    )
    cache = read_json(CACHE_PATH, {'schema_version': 1, 'sources': {}, 'totals': {}})
    attempts = refresh_sources(cache, sources, now)
    result = snapshot(cache, sources, now,
                      excluded_codes=read_excluded_codes(ROOT / 'data' / 'excluded_codes.json'),
                      verified_codes=read_recent_successes(ROOT / 'data' / 'verified_codes.json', now))
    write_json(CACHE_PATH, cache)
    write_json(FEED_PATH, result)
    print('Nguồn:', len(sources), '| Kết quả:', [(k, ok, n) for k, ok, n in sorted(attempts)])
    print('Ưu đãi hợp lệ:', result['stats']['all'], '| Mã:', result['stats']['codes'])


if __name__ == '__main__':
    main()
