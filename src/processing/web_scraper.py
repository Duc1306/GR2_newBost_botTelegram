"""Web scraper to fetch full article content from links.
"""
import requests
from bs4 import BeautifulSoup
from typing import Optional, Dict
import re
from urllib.parse import urlparse


class ArticleScraper:
    """Scrape full article content from news websites."""
    
    HEADERS = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'vi-VN,vi;q=0.9,en-US;q=0.8,en;q=0.7',
        'Accept-Encoding': 'gzip, deflate, br',
        'DNT': '1',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
        'Sec-Fetch-Dest': 'document',
        'Sec-Fetch-Mode': 'navigate',
        'Sec-Fetch-Site': 'none',
        'Cache-Control': 'max-age=0'
    }
    
    TIMEOUT = 10  # seconds
    
    # Domains to skip scraping (social media, messaging, anti-bot sites, etc.)
    BLACKLIST_DOMAINS = [
        'facebook.com', 'twitter.com', 'youtube.com', 't.me',
        'reddit.com', 'instagram.com', 'linkedin.com', 'tiktok.com',
        'vnexpress.net'  # Has strong anti-bot protection (HTTP 406)
    ]    # Site-specific selectors (mở rộng dần theo các nguồn)
    SELECTORS = {
        'vnexpress.net': {
            'title': 'h1.title-detail',
            'content': 'article.fck_detail',
            'author': 'p.Normal strong',
            'date': 'span.date'
        },
        'baomoi.com': {
            'title': 'h1.article__title',
            'content': 'div.article__body',
            'author': 'div.article__author',
            'date': 'time.article__time'
        },
        'cafef.vn': {
            'title': 'h1.title',
            'content': 'div.detail-content',
            'author': 'span.author',
            'date': 'span.time'
        },
        'vietstock.vn': {
            'title': 'h1.title-news',
            'content': 'div.news-content',
            'author': 'span.author-name',
            'date': 'span.news-date'
        },
        'cafebiz.vn': {
            'title': 'h1.title',
            'content': 'div.content-detail',
            'author': 'span.author',
            'date': 'span.date'
        },
        'kenh14.vn': {
            'title': 'h1.kltitle',
            'content': 'div.klcontent',
            'author': 'div.author',
            'date': 'span.knswli-time'
        },
        # Nguồn tiếng Anh
        'bloomberg.com': {
            'title': 'h1',
            'content': 'div.body-content',
            'author': 'div.author-name',
            'date': 'time'
        },
        'cointelegraph.com': {
            'title': 'h1.post__title',
            'content': 'div.post-content',
            'author': 'a.post-meta__author-name',
            'date': 'time.post-meta__publish-date'
        },
        'tradingview.com': {
            'title': 'h1',
            'content': 'div.body',
            'author': 'span.author',
            'date': 'time'
        },
        # Generic fallback
        '_default': {
            'title': ['h1', 'h1.title', 'h1.post-title', 'h1.article-title'],
            'content': ['article', 'div.article-content', 'div.post-content', 'div.entry-content', 'div.content'],
            'author': ['span.author', 'div.author', 'a.author-name', 'span.byline'],
            'date': ['time', 'span.date', 'div.date', 'span.published']
        }
    }
    
    @classmethod
    def _resolve_redirect(cls, url: str) -> str:
        """Resolve URL shorteners and redirects to get final URL."""
        try:
            # Only follow redirects, don't fetch full content
            response = requests.head(url, headers=cls.HEADERS, timeout=5, allow_redirects=True)
            return response.url
        except Exception:
            return url  # Return original if failed
    
    @classmethod
    def scrape_article(cls, url: str) -> Optional[Dict[str, str]]:
        """
        Scrape full article from URL.
        
        Returns:
            {
                'title': str,
                'content': str (full text),
                'author': str (if found),
                'published_date': str (if found),
                'images': list of image URLs
            }
            or None if failed
        """
        try:
            # Resolve redirects first (e.g., ift.tt -> real URL)
            domain = urlparse(url).netloc.replace('www.', '')
            if 'ift.tt' in domain:
                url = cls._resolve_redirect(url)
                domain = urlparse(url).netloc.replace('www.', '')
            
            # Check blacklist
            if any(blocked in domain for blocked in cls.BLACKLIST_DOMAINS):
                # Skip silently - no need to spam console
                return None
            
            # Fetch HTML with retry logic (for anti-bot protection)
            max_retries = 2
            for attempt in range(max_retries + 1):
                try:
                    # Add referer for vnexpress (they check it)
                    headers = cls.HEADERS.copy()
                    if 'vnexpress.net' in domain:
                        headers['Referer'] = 'https://vnexpress.net/'
                    
                    response = requests.get(url, headers=headers, timeout=cls.TIMEOUT)
                    response.raise_for_status()
                    response.encoding = response.apparent_encoding  # Handle Vietnamese encoding
                    break
                except requests.exceptions.HTTPError as e:
                    if e.response.status_code == 406 and attempt < max_retries:
                        # Retry with different user agent
                        continue
                    raise
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Get domain-specific selectors
            domain = urlparse(url).netloc.replace('www.', '')
            selectors = cls.SELECTORS.get(domain, cls.SELECTORS['_default'])
            
            # Extract fields
            title = cls._extract_text(soup, selectors.get('title'))
            content = cls._extract_text(soup, selectors.get('content'), full=True)
            author = cls._extract_text(soup, selectors.get('author'))
            date = cls._extract_text(soup, selectors.get('date'))
            images = cls._extract_images(soup)
            
            if not title or not content:
                return None
            
            return {
                'title': title,
                'content': cls._clean_content(content),
                'author': author,
                'published_date': date,
                'images': images
            }
            
        except requests.exceptions.HTTPError as e:
            # HTTP errors (4xx, 5xx) - only show for non-blacklisted domains
            if e.response.status_code not in [400, 401, 403, 429]:
                print(f"❌ HTTP {e.response.status_code} scraping {url}")
            return None
        except requests.exceptions.Timeout:
            # Timeout - skip silently (very common)
            return None
        except requests.exceptions.RequestException:
            # Other network errors - skip silently
            return None
        except Exception as e:
            # Unexpected errors - show these
            print(f"❌ Lỗi scrape {url}: {type(e).__name__}")
            return None
    
    @classmethod
    def _extract_text(cls, soup: BeautifulSoup, selector, full: bool = False) -> Optional[str]:
        """Extract text using selector (can be string or list of selectors)."""
        if not selector:
            return None
        
        selectors = selector if isinstance(selector, list) else [selector]
        
        for sel in selectors:
            try:
                element = soup.select_one(sel)
                if element:
                    if full:
                        # Get all text from paragraphs
                        paragraphs = element.find_all(['p', 'h2', 'h3'])
                        return '\n\n'.join(p.get_text(strip=True) for p in paragraphs if p.get_text(strip=True))
                    else:
                        return element.get_text(strip=True)
            except Exception:
                continue
        
        return None
    
    @classmethod
    def _extract_images(cls, soup: BeautifulSoup) -> list:
        """Extract image URLs from article."""
        images = []
        for img in soup.select('article img, div.content img, div.article-content img'):
            src = img.get('src') or img.get('data-src')
            if src and src.startswith('http'):
                images.append(src)
        return images[:5]  # Limit to 5 images
    
    @classmethod
    def _clean_content(cls, text: str) -> str:
        """Clean scraped content."""
        # Remove excessive whitespace
        text = re.sub(r'\n{3,}', '\n\n', text)
        text = re.sub(r' {2,}', ' ', text)
        
        # Remove common ads/tracking text
        ads_patterns = [
            r'Theo .{0,50}?VnExpress',
            r'Nguồn: .{0,50}',
            r'Chia sẻ',
            r'Like.*Facebook',
            r'Theo dõi.*Twitter',
        ]
        for pattern in ads_patterns:
            text = re.sub(pattern, '', text, flags=re.IGNORECASE)
        
        return text.strip()


def enrich_post_with_article(post_dict: dict, verbose: bool = False) -> dict:
    """
    Enrich a post with full article content if it has links.
    
    Args:
        post_dict: Post dictionary (from Post.model_dump())
        verbose: If True, print success messages
    
    Returns:
        Updated post_dict with 'full_article' field if successful
    """
    links = post_dict.get('links', [])
    if not links:
        return post_dict
    
    # Try first link (usually the main article)
    article = ArticleScraper.scrape_article(links[0])
    if article:
        post_dict['full_article'] = article
        if verbose:
            print(f"   📰 Scraped: {article['title'][:50]}...")
    
    return post_dict
