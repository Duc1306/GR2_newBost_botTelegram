"""
Debug URL redirect resolution.
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.processing.web_scraper import ArticleScraper
import requests


def test_redirect():
    """Test redirect resolution directly."""
    
    test_urls = [
        "https://bloom.bg/3QGhnqf",
        "https://trib.al/3YuwSdj",
        "https://tinyurl.com/2vybev8p",
    ]
    
    print("🔍 Testing Redirect Resolution\n")
    
    for url in test_urls:
        print(f"\nTesting: {url}")
        
        try:
            # Try HEAD request
            print("  Trying HEAD request...")
            response = requests.head(url, headers=ArticleScraper.HEADERS, timeout=5, allow_redirects=True)
            print(f"    Status: {response.status_code}")
            print(f"    Final URL: {response.url}")
            
        except Exception as e:
            print(f"    HEAD failed: {e}")
            
            try:
                # Try GET request
                print("  Trying GET request...")
                response = requests.get(url, headers=ArticleScraper.HEADERS, timeout=5, allow_redirects=True)
                print(f"    Status: {response.status_code}")
                print(f"    Final URL: {response.url}")
                
            except Exception as e2:
                print(f"    GET failed: {e2}")


if __name__ == "__main__":
    test_redirect()
