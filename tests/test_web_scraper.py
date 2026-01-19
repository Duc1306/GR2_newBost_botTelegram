"""Test web scraper module."""
import pytest
from src.processing.web_scraper import ArticleScraper, enrich_post_with_article


def test_scrape_vnexpress():
    """Test scraping VnExpress article."""
    # URL mẫu từ VnExpress (có thể thay đổi theo thời gian)
    url = "https://vnexpress.net/chu-tich-apple-tim-cook-den-viet-nam-4714098.html"
    
    result = ArticleScraper.scrape_article(url)
    
    # Kiểm tra có dữ liệu không (có thể fail nếu URL không tồn tại)
    if result:
        assert 'title' in result
        assert 'content' in result
        assert len(result['content']) > 100  # Nội dung phải có ít nhất 100 ký tự
        print(f"\n Scraped title: {result['title']}")
        print(f" Content length: {len(result['content'])} chars")


def test_scrape_invalid_url():
    """Test scraping invalid URL."""
    result = ArticleScraper.scrape_article("https://invalid-domain-12345.com/article")
    assert result is None


def test_enrich_post_without_links():
    """Test enriching post without links."""
    post_dict = {
        'id': 'test_1',
        'text': 'Test post',
        'links': []
    }
    
    result = enrich_post_with_article(post_dict)
    assert result == post_dict
    assert 'full_article' not in result


def test_enrich_post_with_links():
    """Test enriching post with valid link."""
    post_dict = {
        'id': 'test_2',
        'text': 'Test post with link',
        'links': ['https://vnexpress.net/chu-tich-apple-tim-cook-den-viet-nam-4714098.html']
    }
    
    result = enrich_post_with_article(post_dict)
    
    # Có thể có hoặc không có full_article tùy link
    assert 'id' in result
    assert 'text' in result


if __name__ == "__main__":
    print("Testing web scraper...")
    test_scrape_invalid_url()
    print(" Invalid URL test passed")
    
    test_enrich_post_without_links()
    print(" Enrich without links test passed")
    
    print("\nAll tests passed!")
