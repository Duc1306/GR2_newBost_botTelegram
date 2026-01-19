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
        'vnexpress.net',  # Has strong anti-bot protection (HTTP 406)
        'podtrac.com', 'podcasts.apple.com'  # Podcast platforms
    ]    # Mapping từ category của trang báo → topic chuẩn của chúng ta
    CATEGORY_MAPPING = {
        # Kinh tế
        'kinh-te': 'Kinh tế', 'kinh-doanh': 'Kinh tế', 'tai-chinh': 'Kinh tế', 
        'chung-khoan': 'Kinh tế', 'business': 'Kinh tế', 'finance': 'Kinh tế',
        'economy': 'Kinh tế', 'markets': 'Kinh tế', 'investing': 'Kinh tế',
        'economics': 'Kinh tế', 'stock': 'Kinh tế', 'stocks': 'Kinh tế',
        'trading': 'Kinh tế', 'investment': 'Kinh tế', 'wealth': 'Kinh tế',
        'companies': 'Kinh tế', 'company': 'Kinh tế',
        
        # Công nghệ
        'cong-nghe': 'Công nghệ', 'so-hoa': 'Công nghệ',
        'technology': 'Công nghệ', 'tech': 'Công nghệ', 'digital': 'Công nghệ',
        'ai': 'Công nghệ', 'startup': 'Công nghệ', 'innovation': 'Công nghệ',
        'software': 'Công nghệ', 'hardware': 'Công nghệ', 'gadgets': 'Công nghệ',
        
        # Crypto
        'crypto': 'Crypto', 'cryptocurrency': 'Crypto', 'bitcoin': 'Crypto',
        'blockchain': 'Crypto', 'defi': 'Crypto', 'nft': 'Crypto',
        'ethereum': 'Crypto', 'web': 'Crypto', 'btc': 'Crypto', 'eth': 'Crypto',
        
        # Chính trị (Domestic politics)
        'chinh-tri': 'Chính trị', 'thoi-su': 'Chính trị', 'xa-hoi': 'Chính trị',
        'politics': 'Chính trị', 'news': 'Chính trị',
        'government': 'Chính trị', 'policy': 'Chính trị',
        
        # Thế giới (International news)
        'the-gioi': 'Thế giới', 'quoc-te': 'Thế giới', 'world': 'Thế giới',
        'international': 'Thế giới', 'global': 'Thế giới',
        
        # Pháp luật
        'phap-luat': 'Pháp luật', 'toa-an': 'Pháp luật', 'an-ninh': 'Pháp luật',
        'law': 'Pháp luật', 'legal': 'Pháp luật', 'court': 'Pháp luật',
        'crime': 'Pháp luật', 'justice': 'Pháp luật',
        'toi-pham': 'Pháp luật', 'canh-sat': 'Pháp luật', 'cong-an': 'Pháp luật',
        
        # Ô tô - Xe máy
        'o-to-xe-may': 'Ô tô - Xe máy', 'oto-xe-may': 'Ô tô - Xe máy',
        'xe': 'Ô tô - Xe máy', 'automotive': 'Ô tô - Xe máy',
        'cars': 'Ô tô - Xe máy', 'vehicles': 'Ô tô - Xe máy',
        'xe-co': 'Ô tô - Xe máy', 'o-to': 'Ô tô - Xe máy',
        
        # Khoa học
        'khoa-hoc': 'Khoa học', 'nghien-cuu': 'Khoa học',
        'science': 'Khoa học', 'research': 'Khoa học',
        
        # Thể thao
        'the-thao': 'Thể thao', 'bong-da': 'Thể thao', 'sports': 'Thể thao',
        'football': 'Thể thao', 'soccer': 'Thể thao', 'basketball': 'Thể thao',
        'tennis': 'Thể thao', 'golf': 'Thể thao',
        'world-cup': 'Thể thao', 'olympic': 'Thể thao', 'sea-games': 'Thể thao',
        
        # Giải trí
        'giai-tri': 'Giải trí', 'showbiz': 'Giải trí', 'phim': 'Giải trí',
        'entertainment': 'Giải trí', 'celebrity': 'Giải trí', 'music': 'Giải trí',
        'movies': 'Giải trí', 'tv': 'Giải trí', 'culture': 'Giải trí',
        
        # Sức khỏe
        'suc-khoe': 'Sức khỏe', 'y-te': 'Sức khỏe', 'doi-song': 'Sức khỏe',
        'health': 'Sức khỏe', 'medical': 'Sức khỏe', 'wellness': 'Sức khỏe',
        'tam-ly': 'Sức khỏe', 'dinh-duong': 'Sức khỏe', 'healthcare': 'Sức khỏe',
        'fitness': 'Sức khỏe',
        
        # Giáo dục
        'giao-duc': 'Giáo dục', 'education': 'Giáo dục', 'hoc-tap': 'Giáo dục',
        'learning': 'Giáo dục',
        
        # Du lịch
        'du-lich': 'Du lịch', 'travel': 'Du lịch', 'tourism': 'Du lịch',
        'destinations': 'Du lịch',
        
        # Ẩm thực
        'am-thuc': 'Ẩm thực', 'food': 'Ẩm thực', 'mon-an': 'Ẩm thực',
        'dining': 'Ẩm thực', 'recipes': 'Ẩm thực'
    }
    
    # Domain-based topic mapping (for platforms without category paths)
    DOMAIN_TO_TOPIC = {
        # Crypto & Trading Platforms
        'tradingview.com': 'Crypto',
        'coindesk.com': 'Crypto',
        'cointelegraph.com': 'Crypto',
        'binance.com': 'Crypto',
        'coinbase.com': 'Crypto',
        'crypto.com': 'Crypto',
        'bitcoinmagazine.com': 'Crypto',
        'decrypt.co': 'Crypto',
        
        # Financial News (shortened URLs & international)
        'bloom.bg': 'Kinh tế',  # Bloomberg shortened
        'on.ft.com': 'Kinh tế',  # Financial Times shortened
        'reut.rs': 'Kinh tế',    # Reuters shortened
        'trib.al': 'Kinh tế',   # Bloomberg Tribune shortened
        'wsj.com': 'Kinh tế',
        'bloomberg.com': 'Kinh tế',
        'reuters.com': 'Kinh tế',
        'ft.com': 'Kinh tế',
        'cnbc.com': 'Kinh tế',
        'marketwatch.com': 'Kinh tế',
        'investing.com': 'Kinh tế',
        
        # Vietnamese Finance Sites
        'cafef.vn': 'Kinh tế',
        'vneconomy.vn': 'Kinh tế',
        'tinnhanhchungkhoan.vn': 'Kinh tế',
        'ndh.vn': 'Kinh tế',
        'dff.vn': 'Kinh tế',
        'vietstock.vn': 'Kinh tế',
        'cafebiz.vn': 'Kinh tế',
        'thoibaotaichinhvietnam.vn': 'Kinh tế',
        
        # Major Vietnamese News Sites (multi-topic - use path-based classification)
        # vnexpress.net, tuoitre.vn, dantri.com.vn, thanhnien.vn - NO domain mapping
        # They have clear category paths: /kinh-te/, /phap-luat/, /the-gioi/, etc.
        # Path-based classification will handle them automatically
        
        # Tech Platforms (International)
        'techcrunch.com': 'Công nghệ',
        'theverge.com': 'Công nghệ',
        'wired.com': 'Công nghệ',
        'arstechnica.com': 'Công nghệ',
        'engadget.com': 'Công nghệ',
        'cnet.com': 'Công nghệ',
        'zdnet.com': 'Công nghệ',
        
        # Vietnamese Tech Sites
        'genk.vn': 'Công nghệ',
        'ictnews.vn': 'Công nghệ',
        'vietnamnet.vn': 'Công nghệ',  # Has tech section
        
        # World News (Thế giới) - International
        'bbc.com': 'Thế giới',
        'bbc.co.uk': 'Thế giới',
        'cnn.com': 'Thế giới',
        'theguardian.com': 'Thế giới',
        'aljazeera.com': 'Thế giới',
        'apnews.com': 'Thế giới',
        'france24.com': 'Thế giới',
        'dw.com': 'Thế giới',  # Deutsche Welle
        
        # Vietnamese World/International News
        'voanews.com': 'Thế giới',  # Voice of America Vietnamese
        'rfi.fr': 'Thế giới',  # RFI Vietnamese
        
        # Law (Pháp luật) - Vietnamese Legal Sites
        'baophapluat.vn': 'Pháp luật',
        'phapluatplus.vn': 'Pháp luật',
        'congan.com.vn': 'Pháp luật',
        'cand.com.vn': 'Pháp luật',  # Công an nhân dân
        'vksndtc.gov.vn': 'Pháp luật',  # Viện kiểm sát
        'antg.cand.com.vn': 'Pháp luật',
        'luatkhoa.com.vn': 'Pháp luật',
        'doanhnhanphapluat.com.vn': 'Pháp luật',
        'laodong.vn': 'Pháp luật',  # Lao Động has law sections
        # Note: tuoitre.vn, baomoi.com are general news sites - use path-based classification
        
        # Science (Khoa học) - International
        'nature.com': 'Khoa học',
        'science.org': 'Khoa học',
        'sciencedaily.com': 'Khoa học',
        'scientificamerican.com': 'Khoa học',
        'newscientist.com': 'Khoa học',
        'nasa.gov': 'Khoa học',
        'space.com': 'Khoa học',
        'phys.org': 'Khoa học',
        
        # Vietnamese Science Sites
        'khoahoc.tv': 'Khoa học',
        
        # Auto/Car Sites (Vietnamese)
        'oto.com.vn': 'Ô tô - Xe máy',
        'autodaily.vn': 'Ô tô - Xe máy',
        'xeketoi.com': 'Ô tô - Xe máy',
        'otofun.net': 'Ô tô - Xe máy',
        'otosaigon.com': 'Ô tô - Xe máy',
        'xe.com.vn': 'Ô tô - Xe máy',
        'xe.tinhte.vn': 'Ô tô - Xe máy',
        
        # Auto/Car Sites (International)
        'motortrend.com': 'Ô tô - Xe máy',
        'caranddriver.com': 'Ô tô - Xe máy',
        'automoto.it': 'Ô tô - Xe máy',
        
        # Social Media & Video Platforms (None = skip, too generic)
        'youtube.com': None,
        'youtu.be': None,
        't.me': None,  # Telegram
        'facebook.com': None,
        'fb.com': None,
        'twitter.com': None,
        'x.com': None,
        'instagram.com': None,
        'tiktok.com': None,
        
        # Podcast & Event Platforms (None = skip, not news)
        'podtrac.com': None,
        'luma.com': None,
        'eventbrite.com': None,
        'spotify.com': None,
        'soundcloud.com': None,
    }
    
    # Site-specific selectors (mở rộng dần theo các nguồn)
    SELECTORS = {
        'vnexpress.net': {
            'title': 'h1.title-detail',
            'content': 'article.fck_detail',
            'author': 'p.Normal strong',
            'date': 'span.date',
            'category': 'ul.breadcrumb li a'  # Lấy từ breadcrumb
        },
        'baomoi.com': {
            'title': 'h1.article__title',
            'content': 'div.article__body',
            'author': 'div.article__author',
            'date': 'time.article__time',
            'category': 'div.breadcrumb a'
        },
        'cafef.vn': {
            'title': 'h1.title',
            'content': 'div.detail-content',
            'author': 'span.author',
            'date': 'span.time',
            'category': 'div.breadcrumb a'
        },
        'vietstock.vn': {
            'title': 'h1.title-news',
            'content': 'div.news-content',
            'author': 'span.author-name',
            'date': 'span.news-date',
            'category': 'div.breadcrumb a'
        },
        'vneconomy.vn': {
            'title': 'h1.detail__title',
            'content': 'div.detail__content',
            'author': 'span.detail__author',
            'date': 'span.detail__time',
            'category': 'div.breadcrumb a'
        },
        'tcbs.com.vn': {
            'title': 'h1',
            'content': 'div.content',
            'category': 'div.breadcrumb a'
        },
        'cafebiz.vn': {
            'title': 'h1.title',
            'content': 'div.content-detail',
            'author': 'span.author',
            'date': 'span.date',
            'category': 'div.breadcrumb a'
        },
        'kenh14.vn': {
            'title': 'h1.kltitle',
            'content': 'div.klcontent',
            'author': 'div.author',
            'date': 'span.knswli-time',
            'category': 'div.breadcrumb a'
        },
        # Nguồn tiếng Anh
        'bloomberg.com': {
            'title': 'h1',
            'content': 'div.body-content',
            'author': 'div.author-name',
            'date': 'time',
            'category': 'nav.breadcrumb a'
        },
        'cointelegraph.com': {
            'title': 'h1.post__title',
            'content': 'div.post-content',
            'author': 'a.post-meta__author-name',
            'date': 'time.post-meta__publish-date',
            'category': 'div.breadcrumbs a'
        },
        'tradingview.com': {
            'title': 'h1',
            'content': 'div.body',
            'author': 'span.author',
            'date': 'time',
            'category': 'div.breadcrumbs a'
        },
        # Generic fallback
        '_default': {
            'title': ['h1', 'h1.title', 'h1.post-title', 'h1.article-title'],
            'content': ['article', 'div.article-content', 'div.post-content', 'div.entry-content', 'div.content'],
            'author': ['span.author', 'div.author', 'a.author-name', 'span.byline'],
            'date': ['time', 'span.date', 'div.date', 'span.published'],
            'category': ['nav.breadcrumb a', 'div.breadcrumb a', 'ul.breadcrumb a', 'div.category a']
        }
    }
    
    @classmethod
    def _extract_category_from_url(cls, url: str, resolve_redirects: bool = True) -> Optional[str]:
        """
        Extract category/topic from URL path or domain.
        
        Prioritizes:
        1. Domain-based classification (DOMAIN_TO_TOPIC) - for platforms like TradingView
        2. Query parameters (utm_content, category)
        3. URL path segments (kinh-te, crypto, etc.)
        
        Examples:
          - tradingview.com/... → Crypto (domain-based)
          - vnexpress.net/kinh-te/... → Kinh tế (path-based)
          - bloom.bg/xyz → Kinh tế (resolved + domain-based)
          - bloomberg.com/...?utm_content=business → Kinh tế (query param)
        
        Args:
            url: The URL to extract category from
            resolve_redirects: If True, resolve URL shorteners first
        """
        try:
            # QUICK CHECK: Check domain-based mapping FIRST (before resolution)
            # This avoids slow resolution timeouts for already-known domains
            parsed = urlparse(url)
            original_domain = parsed.netloc.replace('www.', '').lower()
            
            if original_domain in cls.DOMAIN_TO_TOPIC:
                topic_or_category = cls.DOMAIN_TO_TOPIC[original_domain]
                # If explicitly None (social media), skip
                if topic_or_category is None:
                    return None
                # Otherwise return the topic (bloom.bg→Kinh tế, trib.al→Kinh tế, etc.)
                return topic_or_category
            
            # If NOT in domain mapping, try to resolve URL shorteners
            if resolve_redirects:
                original_url = url
                url = cls._resolve_redirect(url)
                
                # If URL changed after resolution, re-parse
                if url != original_url:
                    parsed = urlparse(url)
            
            domain = parsed.netloc.replace('www.', '').lower()
            path = parsed.path.lower()
            
            # STEP 1: Check domain-based mapping again after resolution
            if domain in cls.DOMAIN_TO_TOPIC:
                topic_or_category = cls.DOMAIN_TO_TOPIC[domain]
                if topic_or_category:  # Can be None to explicitly skip
                    return topic_or_category
                else:
                    return None  # Explicitly skip (YouTube, Telegram, etc.)
            
            # STEP 2: Check query parameters (e.g., Bloomberg's utm_content)
            if parsed.query:
                from urllib.parse import parse_qs
                query_params = parse_qs(parsed.query)
                
                # Check utm_content parameter (common in Bloomberg, Tribune)
                if 'utm_content' in query_params:
                    content = query_params['utm_content'][0].lower()
                    if content in cls.CATEGORY_MAPPING:
                        return cls.CATEGORY_MAPPING[content]
                
                # Check category parameter
                if 'category' in query_params:
                    category = query_params['category'][0].lower()
                    if category in cls.CATEGORY_MAPPING:
                        return cls.CATEGORY_MAPPING[category]
            
            # STEP 3: Check path segments (e.g., /kinh-te/, /crypto/)
            # Remove leading/trailing slashes
            path_parts = [p for p in path.split('/') if p]
            
            # Check each part of the path (skip generic ones like 'news', 'articles')
            skip_parts = ['news', 'article', 'articles', 'post', 'posts', 'story', 'stories']
            
            for part in path_parts[:5]:  # Check first 5 levels
                # Clean up the part (remove numbers, dates, etc.)
                clean_part = re.sub(r'\d+', '', part).strip('-')
                
                # Skip generic parts
                if clean_part in skip_parts:
                    continue
                
                # Check mapping
                if clean_part in cls.CATEGORY_MAPPING:
                    return cls.CATEGORY_MAPPING[clean_part]  # Return the mapped topic name
            
            return None
        except Exception:
            return None
    
    @classmethod
    def _resolve_redirect(cls, url: str, use_get: bool = False, retry_count: int = 0) -> str:
        """Resolve URL shorteners and redirects to get final URL.
        
        Args:
            url: The shortened or redirecting URL
            use_get: If True, use GET instead of HEAD (some sites don't support HEAD)
            retry_count: Number of retries attempted (internal use)
        
        Returns:
            The resolved final URL or original URL if resolution fails
        """
        try:
            # List of known URL shorteners that need resolution
            shorteners = ['trib.al', 'bloom.bg', 'tinyurl.com', 'bit.ly', 'ift.tt', 
                         'rb.gy', 'short.link', 'v.gd', 'is.gd', 't.co']
            
            domain = urlparse(url).netloc.replace('www.', '')
            needs_resolution = any(shortener in domain for shortener in shorteners)
            
            if not needs_resolution:
                return url
            
            # Use longer timeout for ift.tt (IFTTT) as it's slower
            timeout = 8 if 'ift.tt' in domain else 3
            
            # Try HEAD first (faster), fallback to GET if needed
            method = requests.get if use_get else requests.head
            response = method(url, headers=cls.HEADERS, timeout=timeout, allow_redirects=True)
            
            # If HEAD returned error codes, try with GET
            if not use_get and response.status_code in [405, 404, 400]:
                return cls._resolve_redirect(url, use_get=True, retry_count=retry_count)
            
            # Return resolved URL even if status is 403 (common with Bloomberg)
            # The redirect happened, we just don't have permission to access
            return response.url
            
        except requests.exceptions.Timeout:
            # Retry once with longer timeout if first attempt
            if retry_count == 0:
                import time
                time.sleep(1)  # Brief pause before retry
                try:
                    response = requests.head(url, headers=cls.HEADERS, timeout=5, allow_redirects=True)
                    return response.url
                except:
                    pass
            return url  # Return original if timeout
        except requests.exceptions.TooManyRedirects:
            return url  # Return original if too many redirects
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
                'images': list of image URLs,
                'category': str (extracted from URL/page),
                'source_topic': str (mapped to our standard topics)
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
            
            # Extract category from page (breadcrumb, meta tags)
            category_from_page = cls._extract_category_from_page(soup, selectors.get('category'))
            
            # Extract category from URL
            category_from_url = cls._extract_category_from_url(url)
            
            # Prefer page category, fallback to URL
            source_category = category_from_page or category_from_url
            
            # Map to our standard topics
            source_topic = None
            if source_category:
                source_topic = cls._map_category_to_topic(source_category)
            
            if not title or not content:
                return None
            
            result = {
                'title': title,
                'content': cls._clean_content(content),
                'author': author,
                'published_date': date,
                'images': images,
                'category': source_category,  # Original category from news site
                'source_topic': source_topic  # Mapped to our standard topics
            }
            
            return result
            
        except requests.exceptions.HTTPError as e:
            # HTTP errors (4xx, 5xx) - only show for non-blacklisted domains
            if e.response.status_code not in [400, 401, 403, 429]:
                print(f" HTTP {e.response.status_code} scraping {url}")
            return None
        except requests.exceptions.Timeout:
            # Timeout - skip silently (very common)
            return None
        except requests.exceptions.RequestException:
            # Other network errors - skip silently
            return None
        except Exception as e:
            # Unexpected errors - show these
            print(f" Lỗi scrape {url}: {type(e).__name__}")
            return None
    
    @classmethod
    def _extract_category_from_page(cls, soup: BeautifulSoup, selector) -> Optional[str]:
        """Extract category from breadcrumb or meta tags."""
        # Try breadcrumb first
        if selector:
            selectors = selector if isinstance(selector, list) else [selector]
            for sel in selectors:
                try:
                    # Get all breadcrumb links
                    links = soup.select(sel)
                    if links and len(links) > 0:
                        # Usually second item is the category (first is home)
                        for link in links[1:3]:  # Try 2nd and 3rd items
                            text = link.get_text(strip=True).lower()
                            if text and text not in ['home', 'trang chủ', 'tin tức', 'news']:
                                return text
                except Exception:
                    continue
        
        # Try meta tags
        try:
            # Open Graph article:section
            og_section = soup.find('meta', property='article:section')
            if og_section and og_section.get('content'):
                return og_section['content'].lower()
            
            # Meta keywords
            meta_keywords = soup.find('meta', attrs={'name': 'keywords'})
            if meta_keywords and meta_keywords.get('content'):
                keywords = meta_keywords['content'].split(',')
                if keywords:
                    return keywords[0].strip().lower()
        except Exception:
            pass
        
        return None
    
    @classmethod
    def _map_category_to_topic(cls, category: str) -> Optional[str]:
        """
        Map extracted category to our standard topics.
        Accepts both category names (kinh-te) and topic names (Kinh tế).
        If already a valid topic name, return as-is.
        """
        if not category:
            return None
        
        category_clean = category.strip()
        
        # Check if it's already a valid topic name (from DOMAIN_TO_TOPIC)
        all_topics = set(cls.CATEGORY_MAPPING.values())
        if category_clean in all_topics:
            return category_clean
        
        category_lower = category_clean.lower()
        
        # Direct mapping
        if category_lower in cls.CATEGORY_MAPPING:
            return cls.CATEGORY_MAPPING[category_lower]
        
        # Fuzzy matching - check if category contains any key
        for key, topic in cls.CATEGORY_MAPPING.items():
            if key in category_lower or category_lower in key:
                return topic
        
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
            print(f"    Scraped: {article['title'][:50]}...")
    
    return post_dict
