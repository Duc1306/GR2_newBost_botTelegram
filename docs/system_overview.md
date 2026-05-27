# Hướng Dẫn Chạy Dự Án & Luồng Dữ Liệu — NewsBot

> Tài liệu này bao gồm: cách cài đặt, cách chạy từng thành phần, và sơ đồ chi tiết các luồng dữ liệu (Telegram, X/Twitter, Subscribe).

---

## Mục Lục

1. [Quick Start](#1-quick-start)  
2. [Cấu Trúc Thư Mục Quan Trọng](#2-cấu-trúc-thư-mục-quan-trọng)  
3. [Cách Chạy Từng Thành Phần](#3-cách-chạy-từng-thành-phần)  
4. [Luồng Dữ Liệu Telegram](#4-luồng-dữ-liệu-telegram)  
5. [Luồng Dữ Liệu X/Twitter](#5-luồng-dữ-liệu-xtwitter)  
6. [Luồng Subscribe Kênh](#6-luồng-subscribe-kênh)  
7. [Background Workers (Auto-Start)](#7-background-workers-auto-start)  
8. [Pipeline Phân Loại ML (4 Tầng)](#8-pipeline-phân-loại-ml-4-tầng)  
9. [Scripts Tiện Ích](#9-scripts-tiện-ích)  
10. [Biến Môi Trường (.env)](#10-biến-môi-trường-env)  
11. [Stack Công Nghệ](#11-stack-công-nghệ)

---

## 1. Quick Start

### 1.1 Yêu Cầu

| Công cụ | Phiên bản | Ghi chú |
|---|---|---|
| Python | 3.12+ | |
| MongoDB | 6+ | local hoặc Atlas |
| Node.js | 18+ | chỉ cần nếu chạy frontend |
| Telegram API credentials | — | từ [my.telegram.org](https://my.telegram.org) |
| Apify account + token | — | cho luồng X/Twitter ($5 credit/tháng miễn phí) |

### 1.2 Cài Đặt

```bash
# 1. Clone và cài Python dependencies
git clone <repo>
cd botTele
pip install -r requirements.txt

# 2. Tạo file .env (xem Mục 10 để biết tất cả biến)
cp .env.example .env   # hoặc tạo mới từ mục 10

# 3. Tạo session Telegram (chỉ cần làm 1 lần)
python scripts/create_session.py
# → Điền số điện thoại + OTP → tạo file telegram_session.session

# 4. (Tuỳ chọn) Seed danh sách kênh X/Twitter vào DB
python scripts/seed_x_sources.py
```

### 1.3 Chạy Lần Đầu

```bash
# Khởi động API server (tự động bật cả 2 background workers)
uvicorn src.api.main:app --reload --port 8000
```

API sẽ lắng nghe tại `http://localhost:8000`. Swagger UI: `http://localhost:8000/docs`.

---



## 2. Cấu Trúc Thư Mục Quan Trọng

```
botTele/
├── src/
│   ├── api/
│   │   ├── main.py              ← FastAPI app, lifespan (khởi động background workers)
│   │   ├── auth.py              ← JWT + bcrypt auth helpers
│   │   ├── channels.py          ← Subscribe/Unsubscribe kênh (trigger ingestion)
│   │   ├── telegram_auth.py     ← Telegram phone OTP login
│   │   ├── middleware.py        ← SlowAPI rate limiting, logging
│   │   └── routes/              ← Route files tách theo domain
│   │       ├── auth_routes.py        # /auth/*
│   │       ├── post_routes.py        # /posts, /topics, /stats
│   │       ├── analytics_routes.py   # /analytics/*
│   │       ├── public_routes.py      # /public/* (no-auth)
│   │       ├── hotnews_routes.py     # /hotnews, /hot-topics + in-memory cache
│   │       ├── tts_routes.py         # /public/tts (edge-tts)
│   │       ├── notification_routes.py# /notifications/*
│   │       ├── settings_routes.py    # /settings
│   │       └── admin_routes.py       # /admin/*
│   ├── ingestion/
│   │   ├── telegram_worker.py   ← Fetch tin từ Telegram (Telethon)
│   │   ├── x_worker.py          ← Fetch tweet từ X/Twitter (Apify)
│   │   ├── channel_queue_worker.py  ← Background worker: poll queue + refresh 12h
│   │   └── run_scheduled_refresh.py ← Cron one-shot: refresh toàn bộ kênh active
│   ├── processing/
│   │   ├── cleaning.py          ← Làm sạch text, tách link
│   │   ├── lang.py              ← Nhận dạng ngôn ngữ (langdetect)
│   │   ├── topic_classifier.py  ← 4-tier cascade (P1→P2→P3→P4)
│   │   ├── ml_topic_classifier.py ← TF-IDF + LinearSVC
│   │   ├── ai_topic_detector.py ← OpenAI GPT-4o-mini
│   │   ├── geo_classifier.py    ← Phân loại địa lý 10 vùng (rule-based + AI)
│   │   ├── backfill_topics.py   ← Batch backfill topics & geo cho bài cũ
│   │   ├── category_mapper.py   ← Channel category → Vietnamese topic
│   │   ├── web_scraper.py       ← Làm giàu nội dung từ URL gốc (tuỳ chọn)
│   │   └── dedupe.py            ← SHA-256 deduplication
│   ├── models/
│   │   └── post.py              ← Dataclass Post (includes geo field)
│   └── config.py                ← Tất cả biến môi trường, đọc từ .env
├── models/
│   └── topic_classifier_svm.pkl ← Model ML đã train (TF-IDF + SVM)
├── scripts/
│   ├── create_session.py        ← Tạo Telegram session (chỉ làm 1 lần)
│   ├── fetch_telegram.cmd       ← Trigger thủ công: fetch Telegram
│   ├── fetch_x.cmd              ← Trigger thủ công: fetch X/Twitter
│   ├── seed_x_sources.py        ← Seed danh sách tài khoản X vào DB
│   └── train_ml_classifier.py   ← Train lại model offline
├── web/
│   └── src/
│       ├── App.jsx
│       ├── context/AuthContext.jsx
│       ├── lib/api.jsx, publicApi.js
│       ├── hooks/useApi.jsx
│       └── pages/
│           ├── admin/    # OverviewPage, PostsPage, AnalyticsPage, TrendingPage, UsersPage, SettingsPage
│           ├── user/     # DashboardPage
│           ├── auth/     # LoginPage, RegisterPage, TelegramLoginPage
│           └── public/   # PublicHomePage + tabs/ (ArticlesTab, HotNewsTab, XSearchTab, StatsTab)
├── docs/
│   ├── system_overview.md       ← File này
│   ├── deploy.md                ← Hướng dẫn deploy (Render + Vercel + Atlas)
│   └── database_schema.md       ← Schema MongoDB chi tiết
├── telegram_session.session     ← Telegram session file (không commit)
└── .env                         ← Biến môi trường (không commit)
```

---

## 3. Cách Chạy Từng Thành Phần

### 3.1 API Server (+ Background Workers tự khởi động)

```bash
uvicorn src.api.main:app --reload --port 8000
```

Khi API server khởi động, FastAPI **tự động bật 3 background workers** (xem Mục 7):
- `run_worker()` — poll hàng đợi `pending_channels` mỗi 30 giây
- `run_refresh_loop()` — refresh tất cả kênh active mỗi 12 giờ
- `_hotnews_precompute_worker()` — warm hot news cache

> **Lưu ý:** Để chạy trong production, bỏ `--reload` và thêm `--workers 1`.

---

### 3.2 Fetch Telegram Thủ Công

```bash
# CMD script (Windows)
scripts\fetch_telegram.cmd           # fetch bình thường (100 tin/kênh)
scripts\fetch_telegram.cmd full      # fetch đầy đủ (1000 tin/kênh)
scripts\fetch_telegram.cmd full scrape  # + scrape bài báo gốc

# Hoặc chạy trực tiếp
python -m src.ingestion.telegram_worker
```

---

### 3.3 Fetch X/Twitter Thủ Công

```bash
# CMD script (Windows)
scripts\fetch_x.cmd                  # mode=both, max=50
scripts\fetch_x.cmd user 100         # chỉ từ user accounts, tối đa 100 tweet
scripts\fetch_x.cmd keyword 200      # chỉ từ từ khóa, tối đa 200 tweet
scripts\fetch_x.cmd both 500         # cả user + keyword, tối đa 500 tweet

# Hoặc chạy trực tiếp
python -m src.ingestion.x_worker
```

> **Chi phí:** Actor Apify `kaitoeasyapi` tính phí ~$0.25/1,000 tweets. Free plan: $5 credit/tháng ≈ 20,000 tweets.

---

### 3.4 Scheduled Refresh (Cron One-Shot)

```bash
# Chạy một lần, refresh toàn bộ kênh đang active trong DB
python -m src.ingestion.run_scheduled_refresh
```

Dùng để cài làm cron job (cron/Task Scheduler) nếu không chạy API server liên tục.

---

### 3.5 Frontend (React)

```bash
cd web
npm install
npm run dev    # Development: http://localhost:5173
npm run build  # Build production
```

---

## 4. Luồng Dữ Liệu Telegram

```
channel.json (danh sách username kênh)
    │
    ▼ scripts/seed_channels.py  (hoặc API POST /channels)
MongoDB: channel_metadata
  {username, category, platform="telegram", status="active"}
    │
    ▼ telegram_worker.py: get_channels_from_db()
Danh sách username[] cần fetch
    │
    ▼ build_client() → TelegramClient (Telethon, MTProto)
    │   Session: telegram_session.session
    │   Credentials: TELEGRAM_API_ID + TELEGRAM_API_HASH
    │
    ▼ fetch_channel_messages(client, channel, limit=200)
Raw Message objects từ Telegram API
    │
    ┌──────────────────────────────────────────┐
    │           process_message(m, channel)    │
    │                                          │
    │  1. clean_text(raw.message)              │
    │     └─ extract_links() → (text, [urls])  │
    │     └─ remove_emojis()                   │
    │     └─ normalize_whitespace()            │
    │                                          │
    │  2. detect_language(text)                │
    │     └─ "vi" | "en" | "other" | None      │
    │                                          │
    │  3. Post.from_raw(...)                   │
    │     └─ dedupe_key = SHA-256(             │
    │            text + sorted(links)          │
    │         )[:32]                           │
    │                                          │
    │  4. Phân loại chủ đề (4-tier cascade)    │
    │     P1 → P2 → P3 → P4                   │
    │     (xem Mục 8)                          │
    └───────────────────┬──────────────────────┘
                        │
    (tuỳ chọn) enrich_post_with_article(post)
        └─ ArticleScraper.scrape(url)
           → title, summary, full_content
                        │
                        ▼
    MongoDB: posts  (upsert by dedupe_key)
    {
      source: "telegram",
      channel: "vnexpress",
      text, links, language, topics,
      date, dedupe_key
    }
```

**Khi nào chạy:**
- Thủ công: `scripts\fetch_telegram.cmd`
- Tự động: `run_worker()` poll queue mỗi 30s (khi có channel mới subscribe)
- Tự động: `run_refresh_loop()` refresh mỗi 12h

---

## 5. Luồng Dữ Liệu X/Twitter

```
MongoDB: channels
  {username, platform="x", status="active"}
    │
    ▼ x_worker.py: get_x_channels_from_db()
Danh sách username[] (VD: ["Reuters", "BBCBreaking"])
    │
    ▼ fetch_by_users(usernames, max_items)
Apify API call:
  Actor: kaitoeasyapi/twitter-x-data-tweet-scraper-pay-per-result-cheapest
  Input:
    searchTerms: ["from:Reuters", "from:BBCBreaking"]
    maxItems: max(20, max_items)   ← Actor tối thiểu 20
    lang: "en"                     ← tuỳ cấu hình
    │
    ▼ actor.call(run_input=input)
    │  (Apify chạy actor, poll đến khi xong)
    │
    ▼ dataset.iterate_items()
Raw tweet objects từ Apify dataset
    │
    ┌──────────────────────────────────────────┐
    │           parse_tweet(item)              │
    │                                          │
    │  text   = item["text"]                   │
    │  author = item["author"]["userName"]     │
    │  date   = item["createdAt"]              │
    │  url    = item["url"]                    │
    │  links  = item["urls"] + [url]           │
    │                                          │
    │  → Post object                           │
    │    dedupe_key = SHA-256(text+links)[:32] │
    └───────────────────┬──────────────────────┘
                        │
    Phân loại chủ đề (4-tier cascade)
    P1 → P2 → P3 → P4
                        │
                        ▼
    MongoDB: posts  (upsert by dedupe_key)
    {
      source: "twitter",
      channel: "Reuters",
      text, links, language, topics,
      date, dedupe_key
    }
```

**Khi nào chạy:**
- Thủ công: `scripts\fetch_x.cmd [user|keyword|both] [max]`
- Tự động: ngay khi user subscribe kênh X (BackgroundTask, xem Mục 6)
- Tự động: `run_refresh_loop()` phát hiện kênh X → gọi `x_worker.ingest_once()`

---

## 6. Luồng Subscribe Kênh

Khi user gọi `POST /channels/subscribe`, hệ thống thực hiện 3 bước:

```
POST /channels/subscribe
  Body: { "channel": "@vnexpress" }  hoặc  { "channel": "https://x.com/Reuters" }
    │
    ▼ BƯỚC 1: DEDUPLICATION
    parse_channel_input(channel)
    └─ Nhận dạng platform: telegram | x
    └─ Chuẩn hoá username (bỏ @, bỏ URL prefix)
    
    Kiểm tra user_channels collection:
    └─ Nếu đã subscribe → trả về 409 Conflict
    │
    ▼ BƯỚC 2: LƯU VÀO DB
    Insert vào user_channels:
    {user_id, channel_username, platform, subscribed_at}
    
    Upsert vào channels:
    {username, platform, status="active"}
    │
    ▼ BƯỚC 3: TRIGGER INGESTION (BackgroundTasks)
    
    ┌─────────────────────────────────────────────────┐
    │  if platform == "x":                            │
    │      BackgroundTask → x_worker.ingest_once()   │
    │      (Apify call ngay lập tức, ~30-60 giây)    │
    │                                                 │
    │  if platform == "telegram":                     │
    │      Insert vào pending_channels collection     │
    │      {username, requested_at, status="pending"} │
    │      → channel_queue_worker poll mỗi 30s       │
    │      → Telethon fetch sau tối đa 30 giây        │
    └─────────────────────────────────────────────────┘
    │
    ▼
    202 Accepted  (ingestion đang chạy ở background)
```

---

## 7. Background Workers (Auto-Start)

`src/api/main.py` dùng FastAPI `lifespan` để tự động khởi động 3 workers khi API server bật:

```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    asyncio.create_task(run_worker())                    # Worker 1: Poll pending queue
    asyncio.create_task(run_refresh_loop())              # Worker 2: Refresh kênh active
    asyncio.create_task(_hotnews_precompute_worker())    # Worker 3: Warm hot news cache
    yield
```

### Worker 1: Pending Queue (`run_worker`)

```
Vòng lặp vô hạn (interval = 30 giây):
    │
    ▼
Poll MongoDB: pending_channels
  {status: "pending", platform: "telegram"|"x"}
    │
    ├─ Không có gì → sleep 30s → lặp lại
    │
    └─ Có channels pending:
         │
         ├─ platform = "telegram"
         │    └─ telegram_worker.fetch_channel(username)
         │
         └─ platform = "x"
              └─ x_worker.ingest_once(mode="user", usernames=[...])
         │
         ▼
         Cập nhật status = "done" trong pending_channels
         sleep 30s → lặp lại
```

### Worker 2: Active Refresh (`run_refresh_loop`)

```
Vòng lặp vô hạn (interval = 12 giờ = 43200 giây):
    │
    ▼
refresh_active_channels(db)
    │
    ▼ Lấy tất cả kênh có status="active" từ MongoDB
    │
    ├─ tg_channels = [kênh có platform="telegram"]
    │    └─ telegram_worker.fetch_channels(tg_channels)
    │
    └─ x_channels = [kênh có platform="x"]
         └─ x_worker.ingest_once(
              mode="user",
              usernames=[c.username for c in x_channels]
            )
    │
    ▼
sleep 43200s → lặp lại
```

---

## 8. Pipeline Phân Loại ML (4 Tầng)

Mỗi bài viết được phân loại qua 4 tầng theo thứ tự ưu tiên:

```
INPUT: text + channel_name + links[]
    │
    ▼
P1: DB Category Lookup  (channel_metadata.category → map_category_to_topic)
    │ Tìm thấy → DONE (độ tin cậy cao nhất)
    │ Không tìm thấy ↓
    ▼
P2: URL Path Extraction  (_extract_category_from_url → regex trên đường dẫn)
    │ Match → DONE
    │ Không match ↓
    ▼
P3: ML Classifier  (TF-IDF + LinearSVC, confidence ≥ 0.3)
    │ confidence đủ cao → DONE
    │ confidence thấp ↓
    ▼
P4: Rule-Based Keywords  (từ điển song ngữ vi/en — luôn có kết quả)
    │
    ▼
OUTPUT: post.topics = ["Kinh tế"] (hoặc chủ đề khác)
```

**19 chủ đề:** Crypto · Kinh tế · Công nghệ · Chính trị · Thế giới · Pháp luật · Ô tô - Xe máy · Khoa học · Thể thao · Giải trí · Sức khỏe · Giáo dục · Việc làm · Du lịch · Ẩm thực · Kinh doanh & Khởi nghiệp · Trò chơi & Ứng dụng · Tin tức & Truyền thông · Khác

---

## 9. Scripts Tiện Ích

| Script | Lệnh | Mục đích |
|---|---|---|
| `create_session.py` | `python scripts/create_session.py` | Tạo file session Telegram (chỉ 1 lần) |
| `fetch_telegram.cmd` | `scripts\fetch_telegram.cmd [full] [scrape]` | Fetch thủ công từ Telegram |
| `fetch_x.cmd` | `scripts\fetch_x.cmd [user\|keyword\|both] [max]` | Fetch thủ công từ X/Twitter |
| `seed_x_sources.py` | `python scripts/seed_x_sources.py` | Thêm tài khoản X mẫu vào DB |
| `train_ml_classifier.py` | `python scripts/train_ml_classifier.py` | Train lại model ML từ dữ liệu DB |
| `evaluate_model.py` | `python scripts/evaluate_model.py` | Đánh giá model hiện tại |
| `balance_training_data.py` | `python scripts/balance_training_data.py` | Cân bằng nhãn training |
| `auto_retrain.cmd` | `scripts\auto_retrain.cmd` | Pipeline train + evaluate tự động |
| `run_scheduled_refresh.py` | `python -m src.ingestion.run_scheduled_refresh` | Refresh tất cả kênh active (cron) |
| `aggregate_topic_stats.py` | `python scripts/aggregate_topic_stats.py` | Cập nhật thống kê chủ đề |
| `extract_keyword_trends.py` | `python scripts/extract_keyword_trends.py` | Trích xuất từ khóa nổi bật |

---

## 10. Biến Môi Trường (.env)

Tạo file `.env` ở thư mục gốc `botTele/`:

```env
# === MongoDB ===
MONGO_URI=mongodb://localhost:27017        # local, hoặc Atlas connection string
DB_NAME=newsbot

# === Telegram (bắt buộc cho luồng Telegram) ===
TELEGRAM_API_ID=12345678                   # từ my.telegram.org
TELEGRAM_API_HASH=abcdef1234567890         # từ my.telegram.org
TELEGRAM_SESSION_STRING=...                # chuỗi session từ scripts/create_session.py
TELEGRAM_BOT_TOKEN=...                     # (tuỳ chọn) bot token
TELEGRAM_FETCH_LIMIT=200                   # số tin tối đa mỗi kênh

# === Apify (bắt buộc cho luồng X/Twitter) ===
APIFY_API_TOKEN=apify_api_xxxxxxxxxxxx     # từ console.apify.com
X_KEYWORDS=ReactJS;AI Việt Nam             # từ khóa cào tweet, phân cách bằng ;
X_USERNAMES=VnExpress;tuoitrenews          # tài khoản X theo dõi, phân cách bằng ;
X_FETCH_LIMIT=50                           # số tweet tối đa mỗi lần fetch

# === Security & Auth ===
JWT_SECRET_KEY=your-very-long-secret-key   # dùng: openssl rand -hex 32
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=1440       # 24 giờ
ADMIN_USERNAME=admin
ADMIN_PASSWORD=your-strong-password        # BẮT BUỘC đổi trên production
API_KEY=your-api-key-for-scripts           # tuỳ chọn, cho X-API-Key header
ENV=development                            # đổi thành "production" trên server

# === Rate Limiting ===
RATE_LIMIT_ENABLED=true
RATE_LIMIT_PER_MINUTE=60
RATE_LIMIT_PER_HOUR=1000

# === OpenAI (tuỳ chọn — hệ thống chạy được mà không có) ===
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-4o-mini
OPENAI_EMBED_MODEL=text-embedding-3-small

# === CORS (Frontend URLs) ===
ALLOWED_ORIGINS=http://localhost:5173,https://newsbot-web.vercel.app

# === Scheduling ===
CHANNEL_REFRESH_INTERVAL=43200         # 12 giờ (giây)
QUEUE_POLL_INTERVAL=30                 # giây

# === Logging ===
LOG_LEVEL=INFO
LOG_FILE=logs/api.log
```

---

## 11. Stack Công Nghệ

| Tầng | Công nghệ |
|---|---|
| **Thu thập Telegram** | Python 3.12, Telethon (MTProto), asyncio |
| **Thu thập X/Twitter** | Apify Python SDK, Actor `kaitoeasyapi` (PPR) |
| **Xử lý & Phân loại** | scikit-learn (TF-IDF + LinearSVC), langdetect, BeautifulSoup4 |
| **AI tùy chọn** | OpenAI GPT-4o-mini, text-embedding-3-small |
| **Lưu trữ** | MongoDB Atlas (pymongo 4.8, dnspython) |
| **API Backend** | FastAPI, Uvicorn, python-jose (JWT), passlib (bcrypt), slowapi |
| **Frontend** | React 18.2, Vite 7.3, MUI 7.3, TanStack Query 5, React Router 7, Recharts 3 |
| **Logging** | Loguru (file rotation 500MB, giữ 30 ngày) |
| **Deploy** | Render (API), Vercel (Frontend), MongoDB Atlas (DB) |

