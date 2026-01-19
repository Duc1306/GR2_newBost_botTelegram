"""
Quick test to verify URL category extraction works with redirects.
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.processing.web_scraper import ArticleScraper


def test_url_extraction():
    """Test URL extraction with various shorteners."""
    
    test_urls = [
        # Bloomberg shortened
        "https://bloom.bg/3QGhnqf",
        "https://bloom.bg/45Z3gAO",
        
        # Tribune shortened  
        "https://trib.al/3YuwSdj",
        "https://trib.al/vbpGfWS",
        
        # TinyURL
        "https://tinyurl.com/2vybev8p",
        "https://tinyurl.com/26pxbzuf",
        
        # Direct URLs (for comparison)
        "https://www.bloomberg.com/news/articles/2023-01-15/bitcoin-rises-on-crypto-market",
        "https://www.cointelegraph.com/news/bitcoin/btc-price-prediction",
    ]
    
    print("🧪 Testing URL Category Extraction\n")
    print("=" * 80)
    
    success = 0
    failed = 0
    
    for i, url in enumerate(test_urls, 1):
        print(f"\n[{i}/{len(test_urls)}] Testing: {url}")
        
        try:
            # Test with redirect resolution
            category = ArticleScraper._extract_category_from_url(url, resolve_redirects=True)
            
            if category:
                topic = ArticleScraper._map_category_to_topic(category)
                print(f"  ✅ Category: {category} → Topic: {topic}")
                success += 1
            else:
                print(f"  ❌ Could not extract category")
                failed += 1
                
        except Exception as e:
            print(f"  ❌ Error: {e}")
            failed += 1
    
    print("\n" + "=" * 80)
    print(f"📊 Results: {success} success, {failed} failed out of {len(test_urls)} URLs")
    print("=" * 80)


if __name__ == "__main__":
    test_url_extraction()
