import os, sys, unittest
from datetime import datetime, UTC

CURRENT_DIR = os.path.dirname(__file__)
PROJECT_ROOT = os.path.abspath(os.path.join(CURRENT_DIR, ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from src.models.post import Post, MediaItem

class TestPostModel(unittest.TestCase):
    def test_from_raw_and_dedupe(self):
        p = Post.from_raw(
            source="telegram",
            source_id="12345",
            author="tester",
            text="Hello world",
            links=["https://example.com"],
            media=[MediaItem(type="photo", url="https://img")],
            created_at=datetime.now(UTC),
        )
        self.assertTrue(p.id.startswith("telegram:"))
        self.assertEqual(len(p.dedupe_key), 32)
        self.assertEqual(p.links[0], "https://example.com")

if __name__ == "__main__":
    unittest.main()
