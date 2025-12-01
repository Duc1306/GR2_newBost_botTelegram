import os
import sys
import unittest

# Đảm bảo có thể import module từ thư mục gốc (chứa 'src')
CURRENT_DIR = os.path.dirname(__file__)
PROJECT_ROOT = os.path.abspath(os.path.join(CURRENT_DIR, ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from src.processing.cleaning import clean_text

class TestCleaning(unittest.TestCase):
    def test_extract_links_and_cleanup(self):
        raw = "Xin chào  https://a.com  thế giới! 😀 #tag"
        cleaned, links = clean_text(raw)
        self.assertIn("Xin chào", cleaned)
        self.assertNotIn("https://a.com", cleaned)
        self.assertTrue(len(links) == 1 and links[0]=="https://a.com")
        self.assertNotIn("😀", cleaned)
        self.assertEqual(" ", cleaned[cleaned.find("Xin chào") + len("Xin chào"):][0])

if __name__ == "__main__":
    unittest.main()
