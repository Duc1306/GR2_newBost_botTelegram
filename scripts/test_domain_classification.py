"""Test domain-based classification"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.processing.web_scraper import ArticleScraper

# Test URLs from user's output
test_urls = [
    # TradingView (should be Crypto)
    "https://www.tradingview.com/chart/BTCUSD/...",
    "https://tradingview.com/symbols/ETHUSDT/",
    
    # Bloomberg shortened (should resolve and classify as Kinh tế)
    "https://bloom.bg/3xyz123",
    
    # YouTube (should be None - filtered out)
    "https://www.youtube.com/watch?v=abc123",
    "https://youtu.be/xyz789",
    
    # Telegram (should be None - filtered out)
    "https://t.me/channelname/123",
    
    # Vietnamese news sites (should extract from path)
    "https://vnexpress.net/kinh-te/chung-khoan/...",
    "https://dantri.com.vn/the-gioi/...",
    "https://cafef.vn/dau-tu/...",
    
    # Vietnamese finance (should use domain)
    "https://dff.vn/some-article-123",
    "https://vneconomy.vn/article/xyz",
    
    # Podcast/Event (should be None)
    "https://podtrac.com/...",
    "https://luma.com/event/...",
]

print("=" * 80)
print("TESTING DOMAIN-BASED CLASSIFICATION")
print("=" * 80)

for url in test_urls:
    print(f"\nURL: {url}")
    
    # Extract category
    category = ArticleScraper._extract_category_from_url(url, resolve_redirects=False)
    
    # Map to topic
    topic = ArticleScraper._map_category_to_topic(category) if category else None
    
    if topic:
        print(f"  ✅ Category: {category} → Topic: {topic}")
    elif category is None:
        print(f"  ⏭️  SKIPPED (social media/platform)")
    else:
        print(f"  ❌ Category: {category} (no topic mapping)")

print("\n" + "=" * 80)
print("SUMMARY")
print("=" * 80)
print("✅ = Successfully classified")
print("⏭️  = Explicitly skipped (non-news platforms)")
print("❌ = Failed to extract or map")
