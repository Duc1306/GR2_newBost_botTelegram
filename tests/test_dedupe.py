import os, sys, unittest

CURRENT_DIR = os.path.dirname(__file__)
PROJECT_ROOT = os.path.abspath(os.path.join(CURRENT_DIR, ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from src.processing.dedupe import is_duplicate_text, make_dedupe_key, similarity_score

class TestDedupe(unittest.TestCase):
    def test_representative_key_is_stable_for_normalized_content(self):
        k1 = make_dedupe_key("Hello world", ["https://a.com", "https://b.com"]) 
        k2 = make_dedupe_key("hello world ", ["https://b.com", "https://a.com"]) 
        self.assertEqual(k1, k2)
        self.assertTrue(k1.startswith("tfidf:"))

    def test_near_duplicate_ignores_small_text_changes(self):
        is_dup, score = is_duplicate_text(
            "Thị trường chứng khoán hôm nay tăng mạnh",
            ["Thị trường chứng khoán hôm nay tăng mạnh!"],
            threshold=0.8,
        )
        self.assertTrue(is_dup)
        self.assertGreaterEqual(score, 0.8)

    def test_different_content_is_not_duplicate(self):
        is_dup, score = is_duplicate_text(
            "Giá vàng trong nước tiếp tục tăng",
            ["Đội tuyển bóng đá công bố huấn luyện viên mới"],
            threshold=0.8,
        )
        self.assertFalse(is_dup)
        self.assertLess(score, 0.8)

    def test_similarity_score(self):
        score = similarity_score("Hello world", "Hello world!")
        self.assertGreater(score, 0.8)

if __name__ == "__main__":
    unittest.main()
