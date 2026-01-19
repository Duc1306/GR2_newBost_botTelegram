"""
Debug why some Bloomberg URLs are failing.
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.processing.web_scraper import ArticleScraper
import time


def debug_urls():
    """Debug specific failing URLs."""
    
    # Mix of working and failing URLs from the log
    test_urls = [
        ("https://trib.al/uXvKKqm", "Working"),  # This worked
        ("https://bloom.bg/46n6PT5", "Failing"),  # This failed
        ("https://bloom.bg/46bFuDj", "Failing"),  # This failed
        ("https://trib.al/BCst7oB", "Working"),  # This worked
        ("https://bloom.bg/46c4cmV", "Failing"),  # This failed
        ("https://bloom.bg/3Wr9QhV", "Failing"),  # This failed
    ]
    
    print("🔍 Debugging Bloomberg URL Failures\n")
    print("=" * 80)
    
    for url, status in test_urls:
        print(f"\n{'='*80}")
        print(f"URL: {url}")
        print(f"Expected: {status}")
        print(f"{'='*80}")
        
        # Step 1: Try to resolve
        print("\n1️⃣ Testing redirect resolution...")
        try:
            resolved = ArticleScraper._resolve_redirect(url)
            print(f"   Resolved: {resolved[:120]}...")
            
            if resolved == url:
                print("   ⚠️ URL didn't resolve (might be timeout or error)")
            else:
                print("   ✅ Successfully resolved")
                
                # Check for utm_content
                if 'utm_content=' in resolved:
                    import re
                    match = re.search(r'utm_content=([^&]+)', resolved)
                    if match:
                        print(f"   📌 utm_content: {match.group(1)}")
                else:
                    print("   ⚠️ No utm_content parameter in resolved URL")
                    
        except Exception as e:
            print(f"   ❌ Error resolving: {e}")
            resolved = url
        
        # Step 2: Try category extraction
        print("\n2️⃣ Testing category extraction...")
        try:
            category = ArticleScraper._extract_category_from_url(url, resolve_redirects=True)
            if category:
                topic = ArticleScraper._map_category_to_topic(category)
                print(f"   ✅ Category: {category} → Topic: {topic}")
            else:
                print(f"   ❌ Could not extract category")
        except Exception as e:
            print(f"   ❌ Error extracting: {e}")
        
        # Small delay to avoid overwhelming
        time.sleep(0.5)
    
    print("\n" + "=" * 80)


if __name__ == "__main__":
    debug_urls()
