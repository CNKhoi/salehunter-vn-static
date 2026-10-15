import unittest
from collectors import make_offer

def offer(code, title="Giảm 25%"):
    return make_offer(platform="TikTok Shop", title=title, url="https://mekoupon.com/ma-giam-gia/tiktok-shop",source_key="mekoupon_tiktok",source_name="Mekoupon",code=code)
class IdentityTests(unittest.TestCase):
    def test_separate_codes(self):
        self.assertNotEqual(offer("TIKTOKCODE11")["id"],offer("TIKTOKCODE22")["id"])
    def test_same_code_updated_title(self):
        self.assertEqual(offer("TIKTOKCODE11")["id"],offer("TIKTOKCODE11","Giảm 30%")["id"])
    def test_titles_when_no_code(self):
        self.assertNotEqual(offer(None)["id"],offer(None,"Giảm 30%")["id"])
