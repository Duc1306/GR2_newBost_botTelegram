"""Quick test for blacklist functionality."""
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.processing.web_scraper import ArticleScraper

print("=" * 60)
print("Testing Web Scraper Blacklist")
print("=" * 60)

# Test 1: Facebook (should be blacklisted, no error message)
print("\n1. Testing Facebook (should return None silently)...")
fb_result = ArticleScraper.scrape_article('https://facebook.com/test')
print(f"   Result: {fb_result}")
assert fb_result is None, "Facebook should be blacklisted"
print("   ✅ PASS: Facebook blacklisted correctly")

# Test 2: Twitter (should be blacklisted)
print("\n2. Testing Twitter/X (should return None silently)...")
tw_result = ArticleScraper.scrape_article('https://twitter.com/test')
print(f"   Result: {tw_result}")
assert tw_result is None, "Twitter should be blacklisted"
print("   ✅ PASS: Twitter blacklisted correctly")

# Test 3: Telegram (should be blacklisted)
print("\n3. Testing Telegram web link (should return None silently)...")
tg_result = ArticleScraper.scrape_article('https://t.me/test')
print(f"   Result: {tg_result}")
assert tg_result is None, "Telegram should be blacklisted"
print("   ✅ PASS: Telegram blacklisted correctly")

print("\n" + "=" * 60)
print("✅ ALL TESTS PASSED!")
print("=" * 60)
print("\nBlacklist is working correctly. No error messages should")
print("appear above for blacklisted domains.")
