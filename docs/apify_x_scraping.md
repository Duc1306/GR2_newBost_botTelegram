# Hướng Dẫn Tích Hợp Apify để Thu Thập Dữ Liệu từ X (Twitter)

> **Kết luận trước:** Có — bạn **hoàn toàn lấy được** bài viết, likes, replies, profile từ X thông qua Apify mà **không cần Twitter API v2** (vốn đã giới hạn/tính phí). Apify dùng $5 credit miễn phí/tháng, đủ cào **~50.000–100.000 tweet** cho đồ án.

---

## Mục Lục

1. [Tại sao dùng Apify thay vì `tweepy`?](#1-tại-sao-dùng-apify-thay-vì-tweepy)
2. [Đăng ký và lấy API Token](#2-đăng-ký-và-lấy-api-token)
3. [Chọn Actor phù hợp](#3-chọn-actor-phù-hợp)
4. [Dữ liệu trả về trông như thế nào?](#4-dữ-liệu-trả-về-trông-như-thế-nào)
5. [Tích hợp vào Python/FastAPI (dự án này)](#5-tích-hợp-vào-pythonfastapi-dự-án-này)
6. [Tích hợp vào NodeJS](#6-tích-hợp-vào-nodejs)
7. [Bảng tính chi phí thực tế](#7-bảng-tính-chi-phí-thực-tế)
8. [Thêm vào pipeline hiện tại](#8-thêm-vào-pipeline-hiện-tại)
9. [Câu hỏi thường gặp](#9-câu-hỏi-thường-gặp)

---

## 1. Tại sao dùng Apify thay vì `tweepy`?

| Tiêu chí | `tweepy` (Twitter API v2) | Apify Twitter Scraper |
|---|---|---|
| Cần developer account | **Bắt buộc** | Không |
| Rate limit miễn phí | 500k tweet/tháng nhưng **đã bị thu hẹp mạnh từ 2023** | ~50k–100k/tháng với $5 credit |
| Tốc độ setup | Chờ duyệt tài khoản 1–7 ngày | **5 phút** |
| Độ ổn định | API thay đổi liên tục | Apify tự xử lý |
| Chi phí | Free tier rất hạn chế | **$5 free** rồi ~$0.1/1000 tweet |

> **Lưu ý:** `requirements.txt` của dự án đã có `tweepy==4.14.0` nhưng Twitter đã đóng hầu hết endpoint miễn phí vào 2023–2024. Apify là giải pháp thực tế hơn.

---

## 2. Đăng ký và lấy API Token

### Bước 1 — Tạo tài khoản Apify
1. Vào https://console.apify.com/sign-up
2. Đăng ký bằng GitHub hoặc email (khuyên dùng GitHub)
3. **Không cần thẻ ngân hàng** — $5 credit được tặng ngay sau khi xác nhận email

### Bước 2 — Lấy API Token
1. Đăng nhập → click avatar góc trên phải → **Settings**
2. Tab **Integrations** → mục **Personal API tokens**
3. Click **"+ Create token"** → đặt tên `newsbot-x-scraper`
4. Copy token dạng: `apify_api_XXXXXXXXXXXXXXXXXXXXXX`

### Bước 3 — Thêm vào `.env`
```dotenv
# .env
APIFY_API_TOKEN=apify_api_XXXXXXXXXXXXXXXXXXXXXX
```

> **Bảo mật:** Không bao giờ commit token vào git. File `.env` đã có trong `.gitignore` của dự án.

---

## 3. Chọn Actor phù hợp

Truy cập https://apify.com/store và tìm kiếm. Dự án này sử dụng Actor **Pay-Per-Result**:

### Actor chính — `kaitoeasyapi/twitter-x-data-tweet-scraper-pay-per-result-cheapest`
- **Link:** https://apify.com/kaitoeasyapi/twitter-x-data-tweet-scraper-pay-per-result-cheapest
- **Chức năng:** Cào tweet theo từ khóa, hashtag, hoặc từ tài khoản cụ thể (dùng `from:username`)
- **Input chính:** `searchTerms`, `maxItems`
- **Chi phí:** ~$0.25/1.000 tweet — rất tiết kiệm với $5 free credit
- **Ưu điểm:** Dùng chung 1 actor cho cả keyword search và user timeline

> **Lưu ý:** Các Actor khác như `apidojo/tweet-scraper` và `apidojo/twitter-user-scraper` cũng hoạt động tốt nhưng tính phí theo compute units (CU) thay vì pay-per-result.

---

## 4. Dữ liệu trả về trông như thế nào?

Một tweet trong output JSON trông như sau:

```json
{
  "id": "1775000000000000000",
  "text": "ReactJS 19 ra mắt với nhiều cải tiến đột phá về Server Components...",
  "createdAt": "2025-04-10T08:30:00.000Z",
  "author": {
    "userName": "reactjs",
    "name": "React",
    "followers": 350000,
    "verified": true
  },
  "likeCount": 4200,
  "retweetCount": 890,
  "replyCount": 156,
  "quoteCount": 74,
  "url": "https://x.com/reactjs/status/1775000000000000000",
  "lang": "en",
  "hashtags": ["ReactJS", "WebDev"],
  "media": [
    {
      "type": "photo",
      "url": "https://pbs.twimg.com/media/..."
    }
  ]
}
```

**Các trường quan trọng cho hệ thống này:**
- `text` → đưa vào pipeline phân loại chủ đề (4-tier cascade)
- `createdAt` → `post.date`
- `url` → `post.links`
- `likeCount` → có thể dùng để tính "hot score"
- `author.userName` → tương đương `channel_name` trong Telegram

---

## 5. Tích hợp vào Python/FastAPI (dự án này)

### Bước 1 — Cài thư viện

```bash
pip install apify-client
```

Thêm vào `requirements.txt`:
```
apify-client>=1.7.0
```

### Bước 2 — Tạo file `src/ingestion/x_worker.py`

```python
"""
x_worker.py — Thu thập bài viết từ X (Twitter) qua Apify
Tích hợp vào pipeline hiện tại giống telegram_worker.py
"""
import os
from datetime import datetime, timezone
from typing import Optional
from apify_client import ApifyClient
from loguru import logger

from src.models.post import Post
from src.processing.topic_classifier import TopicClassifier
from src.db.mongo import get_db


APIFY_TOKEN = os.getenv("APIFY_API_TOKEN")
# Actor Pay-Per-Result — dùng cho cả keyword search và user timeline
X_ACTOR = "kaitoeasyapi/twitter-x-data-tweet-scraper-pay-per-result-cheapest"


def fetch_tweets_by_keyword(
    keyword: str,
    max_items: int = 100,
    language: str = "vi",
) -> list[dict]:
    """
    Cào tweet theo từ khóa tìm kiếm.

    Args:
        keyword:   Từ khóa, VD: "ReactJS", "AI Vietnam", "#PyTorch"
        max_items: Số lượng tweet tối đa (mặc định 100)
        language:  Mã ngôn ngữ ISO 639-1, "vi" hoặc "en"

    Returns:
        Danh sách dict tweet thô từ Apify
    """
    client = ApifyClient(APIFY_TOKEN)
    logger.info(f"[X-Worker] Fetching tweets for keyword='{keyword}', max={max_items}")

    run_input = {
        "searchTerms": [keyword],
        "maxItems": max_items,
        "lang": language,
        "queryType": "Latest",          # "Latest" hoặc "Top"
        "includeSearchTerms": False,
    }

    run = client.actor(X_ACTOR).call(run_input=run_input)
    items = list(client.dataset(run["defaultDatasetId"]).iterate_items())
    logger.info(f"[X-Worker] Got {len(items)} tweets for '{keyword}'")
    return items


def fetch_tweets_by_user(
    usernames: list[str],
    max_tweets: int = 50,
) -> list[dict]:
    """
    Cào tweet từ một hoặc nhiều tài khoản X cụ thể.

    Args:
        usernames:  Danh sách username, VD: ["VnExpress", "tuoitrenews"]
        max_tweets: Số tweet tối đa mỗi tài khoản

    Returns:
        Danh sách dict tweet thô từ Apify
    """
    client = ApifyClient(APIFY_TOKEN)
    logger.info(f"[X-Worker] Fetching timelines for users: {usernames}")

    run_input = {
        "usernames": usernames,
        "maxTweets": max_tweets,
        "addUserInfo": True,
    }

    run = client.actor(X_ACTOR).call(run_input=run_input)
    items = list(client.dataset(run["defaultDatasetId"]).iterate_items())
    logger.info(f"[X-Worker] Got {len(items)} tweets from {usernames}")
    return items


def _tweet_to_post(tweet: dict, source_keyword: str = "x_scraper") -> Optional[Post]:
    """
    Chuyển đổi một tweet thô từ Apify thành Post object
    để tích hợp với pipeline phân loại chủ đề hiện tại.
    """
    text = tweet.get("text", "").strip()
    if not text or len(text) < 10:
        return None

    # Lấy các trường tương đương với Telegram post
    tweet_url  = tweet.get("url", "")
    created_at = tweet.get("createdAt", "")
    author     = tweet.get("author", {})
    channel    = author.get("userName", source_keyword)

    try:
        date = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
    except (ValueError, AttributeError):
        date = datetime.now(timezone.utc)

    # Tạo Post — cấu trúc giống Telegram post
    post = Post.from_raw(
        text=text,
        channel_name=f"x:{channel}",   # prefix "x:" để phân biệt nguồn
        date=date,
        links=[tweet_url] if tweet_url else [],
        message_id=int(tweet.get("id", 0) or 0),
        source="x",                     # trường nguồn mới
    )

    # Gán thêm metadata riêng của X
    post.x_metadata = {
        "likes":    tweet.get("likeCount", 0),
        "retweets": tweet.get("retweetCount", 0),
        "replies":  tweet.get("replyCount", 0),
        "author":   channel,
    }

    return post


def run_x_scraper(
    keywords: list[str] | None = None,
    usernames: list[str] | None = None,
    max_items: int = 100,
    language: str = "vi",
) -> int:
    """
    Entry point chính. Gọi hàm này từ scheduler hoặc API endpoint.
    Cào tweet, chuyển sang Post, lưu vào MongoDB.

    Returns:
        Số lượng bài viết đã lưu thành công
    """
    if not APIFY_TOKEN:
        logger.error("[X-Worker] APIFY_API_TOKEN chưa được cấu hình trong .env")
        return 0

    db = get_db()
    classifier = TopicClassifier()
    raw_tweets: list[dict] = []

    # Cào theo từ khóa
    if keywords:
        for kw in keywords:
            raw_tweets.extend(fetch_tweets_by_keyword(kw, max_items, language))

    # Cào theo tài khoản
    if usernames:
        raw_tweets.extend(fetch_tweets_by_user(usernames, max_items))

    if not raw_tweets:
        logger.warning("[X-Worker] Không có tweet nào được cào về")
        return 0

    saved = 0
    posts = []
    for tweet in raw_tweets:
        post = _tweet_to_post(tweet)
        if post is None:
            continue

        # Phân loại chủ đề (P4 rule-based, có thể nâng lên P3 ML)
        if not post.topics:
            lang = tweet.get("lang", "en")
            post.topics = classifier.classify(post.text, lang)

        posts.append(post)

    # Lưu vào MongoDB (upsert theo dedupe_key giống Telegram pipeline)
    if posts:
        from src.db.mongo import save_posts
        saved = save_posts(posts)
        logger.info(f"[X-Worker] Đã lưu {saved}/{len(posts)} tweet vào MongoDB")

    return saved
```

### Bước 3 — Thêm endpoint vào FastAPI (tuỳ chọn)

Trong `src/api/main.py`, thêm:

```python
from src.ingestion.x_worker import run_x_scraper

@app.post("/admin/scrape/x", tags=["admin"])
async def scrape_x(
    keywords: list[str] = [],
    usernames: list[str] = [],
    max_items: int = 50,
    current_user = Depends(require_admin),
):
    """Trigger cào X theo từ khóa hoặc tài khoản. Chỉ admin."""
    count = run_x_scraper(keywords=keywords, usernames=usernames, max_items=max_items)
    return {"saved": count}
```

### Bước 4 — Chạy thử nhanh

```python
# scripts/test_x_scraper.py
from dotenv import load_dotenv
load_dotenv()

from src.ingestion.x_worker import run_x_scraper

count = run_x_scraper(
    keywords=["ReactJS", "Công nghệ Việt Nam"],
    max_items=20,
    language="vi",
)
print(f"Đã lưu {count} bài viết từ X")
```

```bash
python scripts/test_x_scraper.py
```

---

## 6. Tích hợp vào NodeJS

Nếu bạn muốn tích hợp vào backend NodeJS (MovieTicketBooking hoặc project khác):

```bash
npm install apify-client
```

```javascript
// services/xScraper.js
const { ApifyClient } = require('apify-client');

const client = new ApifyClient({ token: process.env.APIFY_API_TOKEN });

/**
 * Cào tweet theo từ khóa
 * @param {string} keyword - VD: "ReactJS", "#AI"
 * @param {number} maxItems - Số tweet tối đa
 * @returns {Promise<Array>} Danh sách tweet
 */
async function fetchTweetsByKeyword(keyword, maxItems = 100) {
  const run = await client.actor('apidojo/tweet-scraper').call({
    searchTerms: [keyword],
    maxItems,
    queryType: 'Latest',
  });

  const { items } = await client
    .dataset(run.defaultDatasetId)
    .listItems();

  return items;
}

/**
 * Cào tweet từ timeline của tài khoản cụ thể  
 * @param {string[]} usernames - VD: ["VnExpress", "tuoitrenews"]
 */
async function fetchTweetsByUser(usernames, maxTweets = 50) {
  const run = await client.actor('apidojo/twitter-user-scraper').call({
    usernames,
    maxTweets,
    addUserInfo: true,
  });

  const { items } = await client
    .dataset(run.defaultDatasetId)
    .listItems();

  return items;
}

module.exports = { fetchTweetsByKeyword, fetchTweetsByUser };
```

```javascript
// Sử dụng trong route handler
const { fetchTweetsByKeyword } = require('../services/xScraper');

router.get('/api/tweets', async (req, res) => {
  const { keyword = 'ReactJS', limit = 50 } = req.query;
  const tweets = await fetchTweetsByKeyword(keyword, Number(limit));
  res.json({ count: tweets.length, data: tweets });
});
```

---

## 7. Bảng tính chi phí thực tế

| Actor | 1.000 tweet | 10.000 tweet | 50.000 tweet |
|---|---|---|---|
| `apidojo/tweet-scraper` | ~$0.05 | ~$0.50 | ~$2.50 |
| `apidojo/twitter-user-scraper` | ~$0.08 | ~$0.80 | ~$4.00 |

**Kết luận:** Với $5 credit miễn phí, bạn có thể cào **30.000–50.000 tweet** — đủ cho toàn bộ đồ án mà không tốn tiền.

> Theo dõi usage tại: https://console.apify.com/billing

---

## 8. Thêm vào pipeline hiện tại

Sơ đồ luồng sau khi tích hợp:

```
NGUỒN DỮ LIỆU
├── Telegram (telegram_worker.py)   ← hiện tại
└── X / Twitter  (x_worker.py)     ← MỚI (Apify)
         │
         ▼
    raw_tweets[]
         │
         ├── _tweet_to_post()       ← chuyển thành Post object
         │
         ▼
    Post object (text, channel_name, date, links, source="x")
         │
         ├── TopicClassifier.classify()   ← pipeline phân loại CŨ
         │
         ▼
    MongoDB: posts collection
         │
         ▼
    FastAPI: /posts endpoint
         │
         ▼
    React Frontend (hiển thị lẫn Telegram + X post)
```

**Lọc theo nguồn trong API:**
```python
# Lấy chỉ bài từ X
db.posts.find({"source": "x"})

# Lấy tất cả (Telegram + X)
db.posts.find({})
```

---

## 9. Câu hỏi thường gặp

**Q: Có vi phạm Terms of Service của X không?**  
A: Apify dùng web scraping công khai (không đăng nhập). Dữ liệu thu thập chỉ dùng cho nghiên cứu học thuật là hợp lệ trong phạm vi đồ án. Không sử dụng để thương mại hóa.

**Q: Actor có thỉnh thoảng bị lỗi không?**  
A: Có thể. Apify cam kết SLA 99%, nếu Actor lỗi thì credit **không bị trừ**. Bạn chỉ trả tiền cho run thành công.

**Q: Dữ liệu có real-time không?**  
A: Độ trễ ~2–5 phút so với khi tweet được đăng - tốt hơn nhiều so với Twitter API v2 free tier (15 phút).

**Q: Có thể cào tweet từ tài khoản private không?**  
A: Không. Apify chỉ cào được tweet public.

**Q: Thêm `APIFY_API_TOKEN` vào Render thế nào?**  
A: Vào Render dashboard → service của bạn → **Environment** → **Add Environment Variable** → điền `APIFY_API_TOKEN` và giá trị token.

---

*Tài liệu này thuộc về hệ thống newsbot — cập nhật lần cuối: 2025*
