"""
Test with real URLs from the log to see if they work.
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.processing.web_scraper import ArticleScraper


def test_real_urls():
    """Test with actual URLs from the log."""
    
    test_urls = [
        "https://trib.al/3YuwSdj",
        "https://bloom.bg/45Z3gAO",
        "https://tinyurl.com/2vybev8p",
        "https://bloom.bg/3QyhG5l",
        "https://trib.al/wT9VTE6",
        "https://bloom.bg/3Q773ag",
    ]
    
    print("🧪 Testing Real URLs from Log\n")
    print("=" * 80)
    
    for i, url in enumerate(test_urls, 1):
        print(f"\n[{i}/{len(test_urls)}] Testing: {url}")
        
        # First resolve to see the final URL
        resolved = ArticleScraper._resolve_redirect(url)
        print(f"  Resolved to: {resolved[:100]}...")
        
        # Then extract category
        category = ArticleScraper._extract_category_from_url(url, resolve_redirects=True)
        
        if category:
            topic = ArticleScraper._map_category_to_topic(category)
            print(f"  ✅ Category: {category} → Topic: {topic}")
        else:
            print(f"  ❌ Could not extract category")
    
    print("\n" + "=" * 80)


if __name__ == "__main__":
    test_real_urls()
