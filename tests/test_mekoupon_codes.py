"""Tests parser against representative public-page markup, no live HTTP required."""
import unittest
from datetime import datetime
from zoneinfo import ZoneInfo
from collectors import parse_mekoupon_cards, mekoupon_expiry, discount_of

NOW = datetime(2026,10,14,15,50,tzinfo=ZoneInfo('Asia/Ho_Chi_Minh'))
SOURCE='https://mekoupon.com/ma-giam-gia/shopee'

HTML='''<html><body><nav>Shopee TikTok Shop</nav>
<div class="coupon"><div>Shopee</div><p>Mã giảm giá HSD: 31-10</p>
<h3>Giảm 25% tối đa 15kđ</h3><div>Đơn tối thiểu 35kđ</div>
<code>OCT26ID44</code><a href="https://shopee.vn/">Lưu mã</a></div>
<div class="coupon"><div>Shopee</div><p>Mã giảm giá HSD: 13-10</p>
<h3>Giảm 20% tối đa 30kđ</h3><div>Đơn tối thiểu 100kđ</div>
<span>EXPIRED2026</span><button>Dùng ngay</button></div>
<div class="coupon"><div>Shopee</div><p>Mã giảm giá HSD: 31-10</p>
<h3>Giảm 18% tối đa 200kđ</h3><div>Đơn tối thiểu 80kđ</div><span>Chưa công bố</span><button>Lưu mã</button></div>
</body></html>'''

class ExtractCodeTest(unittest.TestCase):
    def test_actual_visible_code(self):
        data=parse_mekoupon_cards(HTML,'Shopee',NOW,SOURCE)
        self.assertEqual(len(data),1)
        self.assertEqual(data[0]['code'],'OCT26ID44')
        self.assertEqual(data[0]['expires_at'][:10],'2026-10-31')
        self.assertIn('35k',data[0]['min_spend'])
        self.assertEqual(data[0]['url'],SOURCE)
    def test_old_code_expired(self):
        self.assertEqual(parse_mekoupon_cards(HTML.replace('31-10','13-10'),'Shopee',NOW,SOURCE),[])
    def test_not_reading_random_article_code(self):
        html='<h3>Giảm 30%</h3><p>Mã là EXAMPLE9999</p>'
        self.assertEqual(parse_mekoupon_cards(html,'Shopee',NOW,SOURCE),[])
    def test_wrong_expiry_rejected(self):
        self.assertIsNone(mekoupon_expiry('31-02',NOW))
    def test_end_day(self):
        self.assertIn('23:59:59',mekoupon_expiry('14-10',NOW))
    def test_currency_discount_parse(self):
        self.assertEqual(discount_of('Giảm 39kđ'), '39kđ')
        self.assertEqual(discount_of('Giảm 100%'), '100%')
    def test_year_rollover_only_november(self):
        x=datetime(2026,12,13,12,0,tzinfo=ZoneInfo('Asia/Ho_Chi_Minh'))
        self.assertEqual(mekoupon_expiry('15-01',x)[:10],'2027-01-15')
    def test_code_deduplicate(self):
        self.assertEqual(len(parse_mekoupon_cards(HTML+HTML,'Shopee',NOW,SOURCE)),1)

if __name__=='__main__':unittest.main()
