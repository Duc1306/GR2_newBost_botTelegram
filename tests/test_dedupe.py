import os, sys, unittest

CURRENT_DIR = os.path.dirname(__file__)
PROJECT_ROOT = os.path.abspath(os.path.join(CURRENT_DIR, ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from src.processing.dedupe import make_dedupe_key

class TestDedupe(unittest.TestCase):
    def test_dedupe_stable(self):
        k1 = make_dedupe_key("Hello world", ["https://a.com", "https://b.com"]) 
        k2 = make_dedupe_key("hello world ", ["https://b.com", "https://a.com"]) 
        self.assertEqual(k1, k2)

    def test_dedupe_differs(self):
        k1 = make_dedupe_key("Hello world", ["https://a.com"]) 
        k2 = make_dedupe_key("Hello world!", ["https://a.com"]) 
        self.assertNotEqual(k1, k2)

if __name__ == "__main__":
    unittest.main()
