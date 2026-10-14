"""Conservative discovery from publicly reachable pages/feeds. No private marketplace APIs.

A discovered mention is NOT a checkout-verified coupon. All outbound URL targets are
fixed in code or restricted to operator-configured raw GitHub feeds.
"""
from __future__ import annotations

import hashlib
import json
import re
import unicodedata
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from datetime import datetime, timedelta
from email.utils import parsedate_to_datetime
from html import unescape
from pathlib import Path
from typing import Callable
from urllib.parse import parse_qsl, quote, urlencode, urljoin, urlsplit, urlunsplit
from zoneinfo import ZoneInfo

import requests
from bs4 import BeautifulSoup, Tag
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

VN = ZoneInfo('Asia/Ho_Chi_Minh')
DEAL_RE = re.compile(r'mã giảm|voucher|khuyến mãi|ưu đãi|flash.?sale|freeship|giảm giá|coupon|săn sale|\bdeal\b', re.I)
CODE_RE = re.compile(r'(?:\bmã(?:\s+giảm\s+giá)?\b|\bcode\b|\bcoupon\s+code\b)\s*(?:là|:|=|\-|：)\s*["“\']?([A-Za-z0-9][A-Za-z0-9_-]{4,27})\b', re.I)
BAD_CODES = set('SHOPEE TIKTOK TIKTOKSHOP SHOP VOUCHER FREESHIP SALE GIAMGIA GIA TRONG KHONG DEAl COUPON CODE XXXXX SAMPLE HELLO MA_GIAM_GIA'.split())
PLATFORMS = {'Shopee', 'TikTok Shop'}
TRACK_PARAMS = {'fbclid', 'gclid', 'ref', 'spm', 'igshid', 'utm_source', 'utm_campaign', 'utm_medium', 'utm_term', 'utm_content'}
MAX_BODY = 2_000_000
UA = 'SaleHunterVN/2.0 (+low-frequency public deal discovery)'


def now_vn() -> datetime:
    return datetime.now(VN)


def clean_text(value: object, limit: int = 250) -> str:
    return re.sub(r'\s+', ' ', unescape(str(value or ''))).strip()[:limit]


def link(value: object) -> str:
    raw = str(value or '').strip()
    if len(raw) > 1600 or any(ord(char) < 32 for char in raw):
        return ''
    try:
        uri = urlsplit(raw)
        if uri.scheme.lower() != 'https' or not uri.hostname or uri.username or uri.password:
            return ''
        if uri.port not in (None, 443):
            return ''
    except ValueError:
        return ''
    return raw


def canonical_url(value: str) -> str:
    uri = urlsplit(value)
    query = [(k, v) for k, v in parse_qsl(uri.query, keep_blank_values=True) if k.lower() not in TRACK_PARAMS and not k.lower().startswith('utm_')]
    return urlunsplit((uri.scheme, uri.netloc.lower(), uri.path.rstrip('/') or '/', urlencode(query), ''))


def code_from_text(value: str) -> str | None:
    matched = CODE_RE.search(value or '')
    if not matched:
        return None
    code = matched.group(1).strip('.,;:-').upper()
    return code if code not in BAD_CODES else None


def parse_date(value: object) -> datetime | None:
    if not isinstance(value, str) or not value.strip():
        return None
    try:
        parsed = datetime.fromisoformat(value.strip().replace('Z', '+00:00'))
    except (TypeError, ValueError):
        return None
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=VN)


def kind_of(value: str) -> str:
    lower = value.casefold()
    if any(key in lower for key in ('freeship', 'free ship', 'phí ship', 'vận chuyển')):
        return 'Freeship'
    if any(key in lower for key in ('flash sale', 'flashsale', 'deal sốc', 'deal hot', 'đồng giá')):
        return 'Flash sale'
    return 'Voucher'


def discount_of(value: str) -> str:
    percent = re.search(r'(?:giảm|tới|đến|ưu đãi)\s*(\d{1,2}\s*%)', value, re.I)
    if percent:
        return percent.group(1).replace(' ', '')
    amount = re.search(r'(?:giảm|tới|đến|tối đa)\s*(\d+(?:[.,]\d+)?\s*(?:triệu|tr|k|đ|vnd))\b', value, re.I)
    return clean_text(amount.group(1), 22) if amount else ''


def guess_platform(title: str, url: str = '') -> str | None:
    s = (title + ' ' + url).casefold()
    if 'tiktok' in s or 'tik tok' in s:
        return 'TikTok Shop'
    if 'shopee' in s or 'shoppe' in s:
        return 'Shopee'
    return None


def make_offer(*, platform: str, title: str, url: str, source_key: str, source_name: str,
               description: str = '', code: str | None = None, published_at: str | None = None,
               expires_at: str | None = None, min_spend: str = '', discount: str = '') -> dict | None:
    title = clean_text(title, 180)
    description = clean_text(description, 300)
    url = link(url)
    if not (title and url and platform in PLATFORMS):
        return None
    published = parse_date(published_at)
    expiry = parse_date(expires_at)
    if expires_at and not expiry:  # Reject malformed expiry rather than pretending timeless validity.
        return None
    if expiry and expiry <= now_vn():
        return None
    if published and published > now_vn() + timedelta(hours=3):
        return None
    code = str(code).strip().upper() if code else None
    if code and (not re.fullmatch(r'[A-Z0-9][A-Z0-9_-]{4,27}', code) or code in BAD_CODES):
        code = None
    normalized = unicodedata.normalize('NFKC', title).casefold()
    identity = f'{source_key}|{platform}|{canonical_url(url)}|{normalized}'
    # By source gives independence on provider updates and favorites stable across scans.
    key = hashlib.sha256(identity.encode('utf-8')).hexdigest()[:24]
    direct_host = urlsplit(url).hostname or ''
    direct = direct_host == 'shopee.vn' or direct_host.endswith('.shopee.vn') or direct_host == 'tiktok.com' or direct_host.endswith('.tiktok.com')
    return dict(id=key, platform=platform, title=title, description=description,
                url=url, source_key=source_key, source=clean_text(source_name, 90),
                code=code, kind=kind_of(title + ' ' + description),
                discount=clean_text(discount, 25) or discount_of(title + ' ' + description),
                min_spend=clean_text(min_spend, 75),
                published_at=published.isoformat() if published else None,
                expires_at=expiry.isoformat() if expiry else None,
                direct_link=direct, verification='Chưa xác minh tại thanh toán')


def curated_offers(file: Path, source_key='manual', source_name='Nguồn quản trị') -> list[dict]:
    # Invalid JSON is a source failure, not an empty successful scan.
    if not file.exists() and source_key == 'manual':
        return []
    data = json.loads(file.read_text(encoding='utf-8'))
    return offers_from_payload(data, source_key, source_name)


def offers_from_payload(data: object, key: str, name: str) -> list[dict]:
    if not isinstance(data, list):
        raise ValueError('Nguồn JSON phải là mảng các ưu đãi')
    if len(data) > 1000:
        raise ValueError('Nguồn vượt quá 1.000 mục')
    offers = []
    for obj in data:
        if not isinstance(obj, dict):
            continue
        result = make_offer(platform=str(obj.get('platform', '')), title=str(obj.get('title', '')),
                            url=str(obj.get('url', '')), source_key=key, source_name=name,
                            description=str(obj.get('description') or ''), code=obj.get('code'),
                            published_at=obj.get('published_at'), expires_at=obj.get('expires_at'),
                            min_spend=str(obj.get('min_spend') or ''), discount=str(obj.get('discount') or ''))
        if result:
            offers.append(result)
    return offers


def http_get(url: str) -> bytes:
    retry = Retry(total=2, connect=2, read=1, backoff_factor=.65, status_forcelist=[429, 502, 503, 504], respect_retry_after_header=True)
    session = requests.Session()
    session.mount('https://', HTTPAdapter(max_retries=retry))
    try:
        with session.get(url, headers={'User-Agent': UA, 'Accept-Language': 'vi-VN,vi;q=0.9,en;q=0.5'}, timeout=(5, 13), stream=True, allow_redirects=False) as response:
            response.raise_for_status()
            if 300 <= response.status_code < 400:
                raise ValueError('Nguồn chuyển hướng: không tự động theo đường dẫn')
            size = 0
            chunks = []
            for chunk in response.iter_content(32768):
                size += len(chunk)
                if size > MAX_BODY:
                    raise ValueError('Nguồn vượt giới hạn dung lượng')
                chunks.append(chunk)
            return b''.join(chunks)
    finally:
        session.close()


def news_offers(platform: str, reference: datetime | None = None) -> list[dict]:
    reference = reference or now_vn()
    query = ('Shopee' if platform == 'Shopee' else '"TikTok Shop"') + ' (voucher OR "mã giảm giá" OR "flash sale") when:3d'
    url = 'https://news.google.com/rss/search?q=' + quote(query) + '&hl=vi&gl=VN&ceid=VN:vi'
    xml = ET.fromstring(http_get(url))
    items = []
    key = 'news_shopee' if platform == 'Shopee' else 'news_tiktok'
    for entry in xml.findall('./channel/item')[:60]:
        title = clean_text(entry.findtext('title'), 180)
        description = clean_text(BeautifulSoup(entry.findtext('description') or '', 'html.parser').get_text(' ', strip=True), 300)
        if not DEAL_RE.search(title + ' ' + description) or guess_platform(title + ' ' + description) != platform:
            continue
        posted = None
        if entry.findtext('pubDate'):
            try:
                posted = parsedate_to_datetime(entry.findtext('pubDate')).astimezone(VN)
            except (TypeError, ValueError, IndexError):
                continue
            if posted > reference + timedelta(hours=2) or posted < reference - timedelta(days=4):
                continue
        record = make_offer(platform=platform, title=title, description=description,
                            url=entry.findtext('link') or '', source_key=key,
                            source_name=clean_text(entry.findtext('source') or 'Google News RSS', 80),
                            code=code_from_text(title + ' ' + description),
                            published_at=posted.isoformat() if posted else None)
        if record:
            items.append(record)
    return items


def blog_offers(reference: datetime | None = None) -> list[dict]:
    reference = reference or now_vn()
    soup = BeautifulSoup(http_get('https://bloggiamgia.vn/lich-san-sale'), 'html.parser')
    headers = [h for h in soup.find_all(['h2','h3']) if 'ưu đãi hôm nay' in h.get_text(' ', strip=True).casefold()]
    if not headers:
        return []
    head = headers[0]
    match = re.search(r'\((\d{1,2})\s*/\s*(\d{1,2})\)', head.get_text(' ', strip=True))
    if not match or (int(match.group(1)), int(match.group(2))) != (reference.day, reference.month):
        return []
    offers = []
    for element in head.next_elements:
        if isinstance(element, Tag) and element.name in ('h2', 'h3') and element is not head:
            break
        if not (isinstance(element, Tag) and element.name == 'a' and element.get('href')):
            continue
        title = clean_text(element.get_text(' ', strip=True), 230)
        if not DEAL_RE.search(title) or len(title) < 8:
            continue
        url = urljoin('https://bloggiamgia.vn/lich-san-sale', element['href'])
        platform = guess_platform(title, url)
        if not platform:
            continue
        record = make_offer(platform=platform, title=title, url=url, source_key='blog',
                            source_name='Bloggiamgia.vn', description='Thông tin từ trang tổng hợp; kiểm tra tại nguồn.',
                            code=code_from_text(title), published_at=reference.isoformat())
        if record:
            offers.append(record)
        if len(offers) >= 100:
            break
    return offers


def external_feed_offers(url: str, key: str) -> list[dict]:
    # Outbound fetching from user-specified URLs is NOT exposed through public API.
    # Operator may configure only raw GitHub/Gist domain; no internal address fetching.
    uri = urlsplit(url)
    if not link(url) or uri.hostname not in {'raw.githubusercontent.com', 'gist.githubusercontent.com'}:
        raise ValueError('EXTERNAL_FEEDS chỉ chấp nhận HTTPS raw.githubusercontent.com / gist.githubusercontent.com')
    data = json.loads(http_get(url).decode('utf-8'))
    return offers_from_payload(data, key, 'Feed JSON quản trị')


@dataclass(frozen=True)
class Source:
    key: str
    name: str
    loader: Callable[[], list[dict]]
    max_age_hours: int = 72


def build_sources(manual: Path, news: bool = True, blog: bool = True, external_feeds: list[str] | None = None) -> list[Source]:
    sources = [Source('manual','Nguồn JSON quản trị',lambda: curated_offers(manual),24*365)]
    if news:
        sources.extend((Source('news_shopee','Google News · Shopee',lambda:news_offers('Shopee'),72),
                        Source('news_tiktok','Google News · TikTok Shop',lambda:news_offers('TikTok Shop'),72)))
    if blog:
        sources.append(Source('blog','Bloggiamgia · Ưu đãi hôm nay',blog_offers,30))
    for pos,url in enumerate((external_feeds or [])[:3],1):
        sources.append(Source(f'feed_{pos}',f'Feed JSON {pos}',lambda target=url, index=pos:external_feed_offers(target,f'feed_{index}'),24*30))
    return sources
