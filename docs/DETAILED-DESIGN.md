# Tài liệu Thiết kế Chi tiết — NewsBot

> **Phiên bản:** 2.0.0 | **Cập nhật:** 2026  
> Tài liệu mô tả chi tiết thiết kế kỹ thuật từng module — dành cho developer muốn hiểu sâu hoặc mở rộng hệ thống.

---

## Mục lục

1. [Stack Công nghệ](#1-stack-công-nghệ)
2. [Kiến trúc Tổng thể](#2-kiến-trúc-tổng-thể)
3. [Sơ đồ Thư mục Chi tiết](#3-sơ-đồ-thư-mục-chi-tiết)
4. [Backend — Module Breakdown](#4-backend--module-breakdown)
   - [4.1 Config Module](#41-config-module)
   - [4.2 API Module](#42-api-module)
   - [4.3 Database Module](#43-database-module)
   - [4.4 Ingestion Module](#44-ingestion-module)
   - [4.5 Processing Module](#45-processing-module)
   - [4.6 Models Module](#46-models-module)
5. [Frontend — Module Breakdown](#5-frontend--module-breakdown)
6. [Luồng Dữ liệu Chi tiết](#6-luồng-dữ-liệu-chi-tiết)
7. [Thiết kế Pipeline Phân loại Chủ đề](#7-thiết-kế-pipeline-phân-loại-chủ-đề)
8. [Thiết kế Hệ thống Xác thực](#8-thiết-kế-hệ-thống-xác-thực)
9. [Thiết kế Hot News Cache](#9-thiết-kế-hot-news-cache)
10. [Scripts & CLI Tools](#10-scripts--cli-tools)

---

## 1. Stack Công nghệ

### Backend

| Thư viện | Phiên bản | Vai trò |
|---|---|---|
| Python | 3.12 | Runtime |
| FastAPI | 0.115.0 | Web framework |
| Uvicorn | 0.30.0 | ASGI server |
| Pydantic | 2.9.0 | Data validation, schema |
| PyMongo | 4.8.0 | MongoDB driver |
| Telethon | 1.34.0 | Telegram MTProto client |
| apify-client | ≥1.7.0 | X/Twitter scraping |
| scikit-learn | 1.5.2 | ML: TF-IDF + LinearSVC |
| openai | ≥1.30.0 | GPT-4o-mini, text-embedding-3-small |
| python-jose | 3.3.0 | JWT encode/decode |
| passlib[bcrypt] | 1.7.4 | Password hashing |
| bcrypt | 4.0.1 | bcrypt backend |
| slowapi | 0.1.9 | Rate limiting |
| loguru | 0.7.2 | Structured logging |
| langdetect | 1.0.9 | Phát hiện ngôn ngữ (vi/en) |
| beautifulsoup4 | 4.12.3 | HTML parsing cho web scraper |
| requests | 2.32.3 | HTTP client sync |
| orjson | 3.10.7 | JSON serialization nhanh |
| edge-tts | ≥6.1.9 | Text-to-Speech tiếng Việt |
| numpy | >=2.0.2 | Tính toán vector (embedding) |

### Frontend

| Thư viện | Vai trò |
|---|---|
| React 18.2 | UI framework |
| Vite 7.3 | Build tool |
| Material UI (MUI) 7.3 | Component library |
| TanStack Query 5 | Server state management |
| React Router 7 | Client-side routing |
| axios 1.13 | HTTP client |
| Recharts 3.6 | Biểu đồ thống kê |
| d3-cloud 1.2 | Word cloud |
| date-fns 4.1 | Date utilities |

---

## 2. Kiến trúc Tổng thể

### Pattern: Layered Architecture + Background Workers

```
┌─────────────────────────────────────────────────────────────┐
│  Presentation Layer (React SPA — Vercel)                    │
│  App.jsx → Pages → Components → useApi hooks               │
└────────────────────────┬────────────────────────────────────┘
                         │ HTTPS REST API
┌────────────────────────▼────────────────────────────────────┐
│  API Layer (FastAPI — Render.com)                           │
│  main.py │ auth.py │ channels.py │ telegram_auth.py        │
│  ├── Auth: JWT HS256 + Telegram OTP                         │
│  ├── Rate Limiting: SlowAPI                                 │
│  └── Background Tasks: 3 asyncio workers                   │
└─────────┬───────────────────────────┬───────────────────────┘
          │                           │
┌─────────▼──────────┐   ┌───────────▼──────────────────────┐
│  Processing Layer  │   │  Ingestion Layer                  │
│  cleaning.py       │   │  telegram_worker.py               │
│  topic_classifier  │   │  x_worker.py                      │
│  ml_classifier     │   │  channel_queue_worker.py          │
│  ai_detector       │◄──┤  sources.py                       │
│  web_scraper       │   └──────────────────────────────────┘
└─────────┬──────────┘             │
          │                        │
┌─────────▼────────────────────────▼───────────────────────────┐
│  Data Layer (MongoDB Atlas)                                   │
│  posts │ channels │ users │ keyword_trends │ hot_topics      │
└──────────────────────────────────────────────────────────────┘
```

### Quyết định thiết kế chính

| # | Quyết định | Lý do |
|---|---|---|
| 1 | Dùng Apify thay vì Twitter API v2 | Twitter API v2 free tier rất hạn chế, Apify scrape không cần auth |
| 2 | Background workers trong FastAPI lifespan | Đơn giản hóa deploy — không cần Celery/Redis riêng |
| 3 | In-memory cache cho hot news | Tránh gọi OpenAI nhiều lần, response nhanh |
| 4 | 4-tầng topic classification | Độ chính xác cao (channel category > URL > ML > keywords) |
| 5 | Telethon Session String | Không bị giới hạn như Bot API; đọc được kênh public |
| 6 | Pydantic v2 tại mọi boundary | Type safety, auto-validation, tránh injection |
| 7 | SHA-256 dedupe key | Chống lưu trùng bài khi chạy fetch nhiều lần |

---

## 3. Sơ đồ Thư mục Chi tiết

```
botTele/
│
├── src/                          # Python backend
│   ├── __init__.py
│   ├── config.py                 # Env vars loader (tất cả settings)
│   │
│   ├── api/                      # HTTP interfaces
│   │   ├── __init__.py
│   │   ├── main.py               # FastAPI app, lifespan, router inclusion
│   │   ├── auth.py               # JWT + bcrypt functions
│   │   ├── channels.py           # /user/channels/* router
│   │   ├── telegram_auth.py      # /auth/telegram/* router
│   │   ├── middleware.py         # SlowAPI setup, logging middleware
│   │   └── routes/               # Route files tách theo domain
│   │       ├── auth_routes.py         # /auth/*
│   │       ├── post_routes.py         # /posts, /topics, /stats
│   │       ├── analytics_routes.py    # /analytics/* (timeline, keywords, heatmap)
│   │       ├── public_routes.py       # /public/* (no-auth, rate limited)
│   │       ├── hotnews_routes.py      # /hotnews, /hot-topics + cache
│   │       ├── tts_routes.py          # /public/tts (TTS tiếng Việt)
│   │       ├── notification_routes.py # /notifications/*
│   │       ├── settings_routes.py     # /settings
│   │       └── admin_routes.py        # /admin/* (ML, X fetch, user mgmt)
│   │
│   ├── db/                       # Data access
│   │   ├── __init__.py
│   │   └── mongo.py              # Singleton MongoClient + helpers
│   │
│   ├── ingestion/                # External data fetch
│   │   ├── __init__.py
│   │   ├── telegram_worker.py    # CLI: fetch kênh Telegram
│   │   ├── x_worker.py           # Apify X/Twitter ingest
│   │   ├── channel_queue_worker.py  # Background worker (pending/refresh)
│   │   ├── run_scheduled_refresh.py # Chạy refresh từ scheduler/cron
│   │   └── sources.py            # Đọc danh sách kênh từ MongoDB
│   │
│   ├── models/                   # Pydantic schemas
│   │   ├── __init__.py
│   │   ├── post.py               # Post, TopicPrediction, MediaItem, FullArticle
│   │   ├── user.py               # UserInDB, UserPublic, RegisterRequest
│   │   ├── channel.py            # Channel, ChannelSummary, ChannelWithSummary
│   │   ├── notification.py       # Notification model
│   │   └── settings.py           # UserSettings
│   │
│   └── processing/               # Pure business logic (no I/O)
│       ├── __init__.py
│       ├── cleaning.py           # Text cleaning + link extraction
│       ├── topic_classifier.py   # Rule-based keyword classifier
│       ├── ml_topic_classifier.py # TF-IDF + LinearSVC
│       ├── ai_topic_detector.py  # OpenAI GPT-4o-mini
│       ├── geo_classifier.py     # Phân loại địa lý 10 vùng
│       ├── backfill_topics.py    # Batch backfill topics & geo
│       ├── category_mapper.py    # Channel category → Vietnamese topic
│       ├── web_scraper.py        # Article enrichment
│       ├── dedupe.py             # SHA-256 deduplication
│       └── lang.py               # Language detection (vi/en)
│
├── scripts/                      # CLI maintenance tools
│   ├── create_indexes.py         # Tạo MongoDB indexes (tự chạy khi startup)
│   ├── train_ml_classifier.py    # Train TF-IDF + SVM model
│   ├── evaluate_model.py         # Đánh giá accuracy, F1
│   ├── predict_topics.py         # Test predict thủ công
│   ├── balance_training_data.py  # Cân bằng data training
│   ├── auto_join_channels.py     # Tự động join kênh Telegram
│   ├── migrate_db_schema.py      # DB migration
│   ├── seed_hot_topics.py        # Seed hot topics mẫu
│   └── ...                       # Nhiều scripts khác
│
├── models/                       # ML model files
│   └── topic_classifier_svm.pkl  # Trained TF-IDF + LinearSVC pipeline
│
├── web/                          # React frontend
│   ├── index.html
│   ├── package.json
│   ├── vite.config.js
│   ├── vercel.json               # Vercel SPA rewrite rules
│   └── src/
│       ├── App.jsx               # Root, routing, lazy loading
│       ├── main.jsx              # React DOM entry
│       ├── context/
│       │   └── AuthContext.jsx   # JWT state, inactivity logout
│       ├── lib/
│       │   ├── api.jsx           # fetchWithAuth wrapper
│       │   └── publicApi.js      # Public API calls (no-auth)
│       ├── hooks/
│       │   └── useApi.jsx        # TanStack Query hooks
│       ├── components/
│       │   └── public/           # ArticleCard, HotClusterCard, NewsTicker...
│       └── pages/
│           ├── admin/            # OverviewPage, PostsPage, AnalyticsPage...
│           ├── user/             # DashboardPage
│           ├── auth/             # LoginPage, RegisterPage, TelegramLoginPage
│           └── public/           # PublicHomePage + tabs/ (ArticlesTab, HotNewsTab, XSearchTab, StatsTab)
│
├── tests/                        # pytest test suite
├── docs/                         # Tài liệu dự án
├── channel.json                  # Catalog kênh có sẵn
├── requirements.txt
└── render.yaml                   # Render.com deploy config
```

---

## 4. Backend — Module Breakdown

### 4.1 Config Module

**File:** `src/config.py`

**Thiết kế:** Load-once tại import time. Không có lazy loading — tất cả biến đều sẵn sàng ngay khi module được import.

```python
# Pattern sử dụng:
from src.config import MONGO_URI, JWT_SECRET_KEY, TELEGRAM_API_ID

# Không bao giờ gọi os.getenv() trực tiếp trong code khác
```

**Dependency graph:**
```
src/config.py
    └── os (stdlib only — no external deps)
```

---

### 4.2 API Module

#### `src/api/main.py` — Chi tiết thiết kế

**Cấu trúc app:**
```python
# 1. Lifespan context manager (startup/shutdown)
@asynccontextmanager
async def lifespan(app: FastAPI):
    await loop.run_in_executor(None, create_indexes)   # Blocking I/O → thread pool
    pending_task = asyncio.create_task(run_worker())
    refresh_task = asyncio.create_task(run_refresh_loop())
    precompute_task = asyncio.create_task(_hotnews_precompute_worker())
    yield  # ← API đang chạy ở đây
    # Cleanup: cancel tất cả tasks

# 2. Middleware stack (thứ tự áp dụng từ ngoài vào trong):
#    - SlowAPI (rate limit)
#    - log_requests_middleware (logging)
#    - CORSMiddleware (CORS headers)

# 3. Tất cả routes đã được tách sang src/api/routes/
# main.py chỉ gọi app.include_router() cho 11 router
```

#### `src/api/routes/hotnews_routes.py` — Hot News Cache

```python
# In-memory cache (trong hotnews_routes.py)
_hotnews_mem: dict[str, dict] = {}
_hotnews_locks: dict[str, asyncio.Lock] = {}
# TTL: 1h cho window 24h, 2h cho 48h, 3h cho 72h+

# 8 hot topics mặc định (seed khi DB trống)
DEFAULT_HOT_TOPICS = [
    {"name": "Iran-Israel Conflict", ...},
    {"name": "Ukraine War", ...},
    {"name": "Gaza Crisis", ...},
    {"name": "US Politics", ...},
    # + 4 others
]
```

**Hot News endpoint design:**
```
Request: GET /hotnews?window_hours=24
    │
    ▼
Check _hotnews_mem[bucket]
    │ Cache hit + không expired?
    ├── YES → trả ngay
    └── NO
        ▼
    Acquire _hotnews_locks[bucket] (asyncio.Lock — ngăn concurrent OpenAI calls)
        ▼
    Fetch posts từ MongoDB (window_hours gần nhất)
        ▼
    detect_new_hot_topics(posts, window_hours)  ← OpenAI GPT-4o-mini
        ▼
    Lưu vào _hotnews_mem[bucket] + set TTL
        ▼
    Release lock + trả response
```

#### `src/api/routes/public_routes.py` — Public Endpoints (No Auth)

```
- GET /public/posts: filter by topic/lang/geo/platform/date/link_only
  Rate limit: 200 req/min
- GET /public/x/search?q=: X/Twitter live search (Apify)
  In-memory cache: 5 phút per query
```

#### `src/api/routes/tts_routes.py` — Text-to-Speech

```
- POST /public/tts { text: str (max 3000 chars) }
  Rate limit: 20 req/min
  Engine: edge-tts, voice: vi-VN-HoaiMyNeural
  Trả về: audio/mpeg binary
```

#### `src/api/channels.py` — Channel Subscription Design

**Channel username conventions:**
```
telegram/t.me channel: "channelname"          → fetch bằng Telethon
X account:             "x:username"           → fetch bằng Apify user mode
X keyword/hashtag:     "xkw:bitcoin"          → fetch bằng Apify keyword mode
```

**Subscribe flow:**
```
POST /user/channels/subscribe { username: "x:elonmusk" }
    │
    ▼
1. Validate: channel chưa tồn tại trong user's list?
2. Insert vào channels collection: { status: "pending" }
3. BackgroundTasks.add_task(_trigger_channel_processing, username)
    │
    ▼ (background)
4. _trigger_channel_processing():
   - x: → gọi Apify ingest_once() ngay
   - xkw: → check cooldown 6h → Apify hoặc skip
   - telegram: → để channel_queue_worker tự poll
5. Update status → "active" hoặc "error"
```

#### `src/api/telegram_auth.py` — OTP Flow Design

**In-memory session store:**
```python
_pending_logins: dict[str, dict] = {
    "session_id_hex": {
        "client": TelegramClient,     # giữ kết nối MTProto
        "phone": "+84912345678",
        "phone_code_hash": "...",     # cần để verify
        "created_at": 1234567890.0    # Unix timestamp
    }
}
```

**Vì sao lưu in-memory thay vì DB?**  
Telethon `TelegramClient` là Python object không thể serialize. Session OTP chỉ tồn tại 5 phút — không cần persist.

**2FA Handling:**
```python
except SessionPasswordNeededError:
    # Telegram 2FA enabled → yêu cầu password bổ sung
    raise HTTPException(400, "Tài khoản bật xác thực 2 bước. Vui lòng nhập mật khẩu Telegram.")
```

---

### 4.3 Database Module

**File:** `src/db/mongo.py`

**Singleton pattern:**
```python
_client: Optional[MongoClient] = None
_db: Optional[Database] = None

def get_db() -> Database:
    global _client, _db
    if _db is None:
        _client = MongoClient(MONGO_URI)
        _db = _client[DB_NAME]
    return _db
```

**Index strategy (`scripts/create_indexes.py`):**

```python
# posts — indexes quan trọng nhất
collection.create_index([("id", 1)], unique=True)           # lookup theo ID
collection.create_index([("dedupe_key", 1)], unique=True)   # chống duplicate
collection.create_index([("created_at", -1)])               # sort mới nhất
collection.create_index([("topics", 1)])                    # filter chủ đề
collection.create_index([("platform", 1), ("source", 1), ("created_at", -1)])  # compound
collection.create_index([("$**", "text")], default_language="none")  # full-text search

# _safe_create() — xử lý IndexOptionsConflict (code 85) và IndexKeySpecsConflict (86)
def _safe_create(collection, keys, **kwargs):
    try:
        collection.create_index(keys, **kwargs)
    except OperationFailure as e:
        if e.code in (85, 86):
            pass  # Index đã tồn tại với options khác — bỏ qua
        else:
            raise
```

---

### 4.4 Ingestion Module

#### `src/ingestion/telegram_worker.py` — Luồng chi tiết

```
TelegramClient(StringSession(TELEGRAM_SESSION_STRING), API_ID, API_HASH)
    │
    ▼ client.get_messages(channel, limit=FETCH_LIMIT)
    │
    ▼ Với mỗi message:
    │   ├── clean_text(message.text) → (text_sạch, links[])
    │   ├── langdetect.detect(text) → "vi" | "en" | ...
    │   ├── enrich_post_with_article(post) → thêm full_article nếu có URL
    │   ├── classify_post_topics(post) → topics[], topic_predictions[]
    │   ├── Tính dedupe_key = SHA256(text[:200])[:32]
    │   └── posts_col.update_one(
    │           {"dedupe_key": key},
    │           {"$setOnInsert": post_dict},
    │           upsert=True
    │       )
    └── Log: "Saved X/Y posts (Z duplicates skipped)"
```

**Lazy-load ML model:**
```python
_ml_classifier: Optional[MLTopicClassifier] = None

def _get_classifier():
    global _ml_classifier
    if _ml_classifier is None:
        _ml_classifier = MLTopicClassifier()
        _ml_classifier.load()
    return _ml_classifier
```

#### `src/ingestion/channel_queue_worker.py` — State Machine

```
channel.status = "pending"
        │
        ▼ (poll mỗi 30s)
_process_channel(username)
        │
        ├─► Telegram channel:
        │       telethon_worker.fetch_channel(username, limit=200, days=7)
        │       → posts saved
        │       → _generate_summary(username) via OpenAI
        │       → channel.status = "active"
        │
        ├─► X account ("x:username"):
        │       x_worker.ingest_once(mode="user", usernames=[username])
        │       → channel.status = "active"
        │
        └─► X keyword ("xkw:keyword"):
                check cooldown 6h
                x_worker.ingest_once(mode="keyword", keywords=[kw])
                → channel.status = "active"

Nếu exception: channel.attempts += 1
    attempts >= MAX_ATTEMPTS(3) → channel.status = "error"
```

---

### 4.5 Processing Module

**Nguyên tắc thiết kế:** Mọi function trong `processing/` đều là **pure functions** — không có database calls, không có HTTP requests trực tiếp (trừ `web_scraper.py`). Điều này giúp dễ test và reuse.

#### `src/processing/cleaning.py`

```python
def clean_text(raw: str) -> tuple[str, list[str]]:
    """
    Pipeline:
    1. extract_links(raw) → lưu URLs trước khi xóa
    2. re.sub(URL_PATTERN, '', raw) → xóa URLs khỏi text
    3. remove_emojis(text)
    4. normalize_whitespace(text)
    Returns: (clean_text, links_list)
    """
```

#### `src/processing/geo_classifier.py` — Phân loại Địa lý (Mới)

```python
_GEO_KEYWORDS: dict[str, list[str]] = {
    "Việt Nam":  ["việt nam", "vn", "hà nội", "hcm", "sài gòn", ...],
    "Mỹ":        ["mỹ", "hoa kỳ", "usa", "biden", "trump", ...],
    "Trung Quốc":["trung quốc", "china", "beijing", "tập cận bình", ...],
    "Nga":       ["nga", "russia", "putin", "moscow", ...],
    "Nhật Bản":  ["nhật bản", "japan", "tokyo", ...],
    "Hàn Quốc":  ["hàn quốc", "korea", "seoul", ...],
    "Châu Âu":   ["châu âu", "europe", "eu", "brussels", ...],
    "Trung Đông":["trung đông", "israel", "gaza", "iran", ...],
    "Đông Nam Á":["đông nam á", "asean", "thái lan", "singapore", ...],
    "Toàn cầu":  ["thế giới", "toàn cầu", "quốc tế", "global", ...],
}

def classify_geo(text: str, channel_username: str = "") -> str | None:
    """Rule-based: count keyword hits → trả region có nhiều hit nhất.
    Trả None nếu không match."""

async def classify_geo_with_ai(text: str) -> str | None:
    """OpenAI GPT-4o-mini fallback cho bài không match rule-based."""
```

#### `src/processing/backfill_topics.py` — Batch Backfill (Mới)

```python
_BATCH_SIZE = 200      # số bài mỗi batch MongoDB
_AI_CONCURRENCY = 5   # số concurrent OpenAI calls

# Modes:
# --count     : chỉ đếm bài thiếu topics/geo
# --geo-only  : chỉ classify geo cho bài thiếu
# --ai-only   : chỉ dùng AI classify topics
# --limit N   : giới hạn N bài
# (không args): rule-based + AI cascade + geo
```

#### `src/processing/web_scraper.py`

```python
class ArticleScraper:
    """
    Scrape full article từ URL.
    
    BLACKLIST_DOMAINS: list các domain bị skip
    (facebook, twitter, youtube, t.me, instagram, tiktok, vnexpress, ...)
    
    Flow:
    1. Kiểm tra domain trong BLACKLIST_DOMAINS
    2. requests.get(url, timeout=5, headers={...})
    3. BeautifulSoup parse HTML
    4. Tìm <article>, <main>, hoặc <div class="content">
    5. Extract title (<h1>) + text (p tags)
    6. Trả FullArticle(title, content, url, domain)
    """
    
CATEGORY_MAPPING = {
    "crypto": "Crypto",
    "tien-ao": "Crypto",
    "kinh-te": "Kinh tế",
    "tai-chinh": "Kinh tế",
    "cong-nghe": "Công nghệ",
    "khoa-hoc": "Khoa học",
    # ... 30+ mappings
}
```

---

### 4.6 Models Module

#### `src/models/post.py`

```python
class TopicPrediction(BaseModel):
    topic: str
    confidence: float = 0.0          # 0.0–1.0
    model_version: str = "unknown"
    method: str = "unknown"          # "ml_svm" | "rule_based" | "channel_category" | "url_slug"

class MediaItem(BaseModel):
    type: str                        # "photo" | "video" | "document"
    url: Optional[str] = None
    file_id: Optional[str] = None

class FullArticle(BaseModel):
    title: Optional[str] = None
    content: Optional[str] = None
    url: str
    domain: Optional[str] = None

class Post(BaseModel):
    id: str                          # "platform:source:source_id"
    source: str                      # channel username
    platform: str = "telegram"
    text: str
    created_at: datetime
    links: List[str] = []
    lang: Optional[str] = None       # "vi" | "en"
    topics: List[str] = []
    topic_predictions: List[TopicPrediction] = []
    source_category: Optional[str] = None
    source_topic: Optional[str] = None
    geo: Optional[str] = None        # vùng địa lý (10 regions or None)
    dedupe_key: Optional[str] = None # SHA-256[:32]
    score: float = 0.0
    media: List[MediaItem] = []
    full_article: Optional[FullArticle] = None
    manual_labels: List[str] = []
    labels_verified: bool = False
```

#### `src/models/user.py`

```python
UserStatus = Literal["active", "banned", "pending"]
UserRole = Literal["user", "admin"]

class UserInDB(BaseModel):
    username: str
    password_hash: str
    role: UserRole = "user"
    status: UserStatus = "pending"   # Admin phải approve
    email: Optional[str] = None
    full_name: Optional[str] = None
    phone_number: Optional[str] = None
    telegram_username: Optional[str] = None
    telegram_session: Optional[str] = None   # Telethon session string
    created_at: datetime = Field(default_factory=datetime.utcnow)
    last_login: Optional[datetime] = None

class RegisterRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    password: str = Field(..., min_length=8)
    full_name: Optional[str] = None
    email: Optional[str] = None
```

---

## 5. Frontend — Module Breakdown

### `web/src/App.jsx` — Router Design

```jsx
// Lazy loading để giảm initial bundle size
const OverviewPage   = lazy(() => import('./pages/OverviewPage'));
const PostsPage      = lazy(() => import('./pages/PostsPage'));
// ...

function App() {
    return (
        <AuthProvider>
            <QueryClientProvider client={queryClient}>
                <Router>
                    <Suspense fallback={<CircularProgress />}>
                        <Routes>
                            <Route path="/" element={<PublicHomePage />} />
                            <Route path="/login" element={<LoginPage />} />
                            
                            {/* Protected routes */}
                            <Route element={<PrivateRoute />}>
                                <Route path="/overview" element={<OverviewPage />} />
                                <Route path="/posts"    element={<PostsPage />} />
                                {/* ... */}
                            </Route>
                            
                            {/* Admin-only routes */}
                            <Route element={<AdminRoute />}>
                                <Route path="/users" element={<UsersPage />} />
                            </Route>
                        </Routes>
                    </Suspense>
                </Router>
            </QueryClientProvider>
        </AuthProvider>
    );
}
```

### `web/src/context/AuthContext.jsx` — State Design

```jsx
const AuthContext = createContext(null);

export function AuthProvider({ children }) {
    const [token, setToken] = useState(
        () => localStorage.getItem("auth_token")  // Khôi phục từ localStorage
    );
    const [user, setUser] = useState(null);
    
    // Inactivity timer — logout sau 60 phút không tương tác
    useEffect(() => {
        const timer = setInterval(checkInactivity, 60_000);
        return () => clearInterval(timer);
    }, []);
    
    // Decode role từ JWT payload (không cần gọi API)
    function decodeJwtRole(token) {
        const payload = JSON.parse(atob(token.split('.')[1]));
        return payload.role || "user";
    }
    
    const isAdmin = user?.role === "admin";
    // ...
}
```

### `web/src/hooks/useApi.jsx` — Query Design

```jsx
// Ví dụ pattern cho 1 hook:
export function usePosts(filters = {}) {
    return useQuery({
        queryKey: ["posts", filters],   // Cache key — thay đổi filters → refetch
        queryFn: () => fetchWithAuth(`/posts?${new URLSearchParams(filters)}`),
        staleTime: 2 * 60 * 1000,       // 2 phút
        retry: 2,
        onError: (error) => {
            if (error.status === 401) navigate("/login");
        }
    });
}

// Mutation pattern (cho subscribe/unsubscribe):
export function useSubscribeChannel() {
    const queryClient = useQueryClient();
    return useMutation({
        mutationFn: (channelData) => fetchWithAuth("/user/channels/subscribe", {
            method: "POST",
            body: JSON.stringify(channelData)
        }),
        onSuccess: () => {
            queryClient.invalidateQueries(["channels"]);  // Refresh danh sách
        }
    });
}
```

---

## 6. Luồng Dữ liệu Chi tiết

### Luồng A: Subscribe kênh Telegram mới

```
User (Frontend)
    │ POST /user/channels/subscribe { username: "vnexpress_channel" }
    ▼
channels.py:subscribe()
    ├── Check: đã subscribe chưa?
    ├── Insert: channels { username, status="pending", user_id, created_at }
    └── BackgroundTasks.add_task(_trigger_channel_processing)
                │
                ▼ (background, không block response)
channel_queue_worker._process_channel("vnexpress_channel")
    ├── TelegramClient.get_messages(limit=200, days=7)
    ├── Với mỗi message: clean → detect_lang → enrich → classify → dedupe → upsert
    ├── OpenAI: _generate_summary(channel, last_24h_posts)
    ├── Save: channel_summaries { channel_username, summary, post_count }
    └── Update: channels { status="active", post_count=N }
                │
                ▼
User refresh /user/channels → thấy channel đã "active"
```

### Luồng B: Phân loại chủ đề một bài viết

```
raw_text = "Bitcoin tăng 10% sau tin Fed..."
    │
    ▼ clean_text(raw_text)
    → (text="Bitcoin tăng 10% sau tin Fed...", links=[])
    │
    ▼ langdetect.detect(text) → "vi"
    │
    ▼ Tầng 1: source_category từ channel.json
    → channel "crypto_news" có category="Crypto" → topics=["Crypto"] ✓ STOP
    
    (Nếu không có channel category:)
    ▼ Tầng 2: URL slug trong links[]
    → link "vnexpress.net/kinh-doanh/..." → CATEGORY_MAPPING["kinh-doanh"] = "Kinh tế"
    
    (Nếu không match:)
    ▼ Tầng 3: MLTopicClassifier.predict(text)
    → TF-IDF vectorize → LinearSVC.predict → "Crypto" (confidence=0.87)
    
    (Nếu model chưa train hoặc confidence thấp:)
    ▼ Tầng 4: KeywordClassifier.classify(text)
    → ["bitcoin", "btc"] → topics=["Crypto"]
```

### Luồng C: Request `/hotnews`

```
GET /hotnews?window_hours=24
    │
    ▼ Check _hotnews_mem["24h"]
    ├── Cache hit (< 1h tuổi) → return cached data
    └── Cache miss
        │
        ▼ Acquire asyncio.Lock (chặn concurrent requests)
        │
        ▼ MongoDB: posts trong 24h gần nhất, sort by score desc, limit 500
        │
        ▼ ai_topic_detector.detect_new_hot_topics(posts, window_hours=24)
        │   ├── Group posts by topic
        │   ├── Tính frequency score
        │   ├── GPT-4o-mini: "Từ các bài này, chủ đề nào đang hot?"
        │   └── Return [HotTopic(topic, keywords, sample_posts, score)]
        │
        ▼ Lưu vào _hotnews_mem["24h"] = { data, cached_at }
        │
        ▼ Release lock + return response
```

---

## 7. Thiết kế Pipeline Phân loại Chủ đề

### Cascade Decision Tree

```
                        ┌──────────────────────────────────┐
                        │  Bài viết mới (raw text + source) │
                        └──────────────┬───────────────────┘
                                       │
                    ┌──────────────────▼──────────────────┐
                    │ Tầng 1: Channel Category              │
                    │ channel.json → source_category        │
                    │ Ví dụ: kênh "cryptoVN" → "Crypto"    │
                    └──────────────────┬──────────────────┘
                             Có category?
                            /           \
                          CÓ            KHÔNG
                           │               │
                     topics = [cat]        │
                     method="channel_cat"  │
                                           │
                    ┌──────────────────────▼──────────────────┐
                    │ Tầng 2: URL Slug Mapping                 │
                    │ links[0] → CATEGORY_MAPPING              │
                    │ "vnexpress.net/crypto" → "Crypto"        │
                    └──────────────────┬──────────────────────┘
                              Có mapping?
                             /           \
                           CÓ            KHÔNG
                            │               │
                    topics += [slug_cat]     │
                    method="url_slug"        │
                                            │
                    ┌───────────────────────▼─────────────────┐
                    │ Tầng 3: ML SVM Classifier                │
                    │ TF-IDF → LinearSVC                       │
                    │ confidence ≥ threshold → accept          │
                    └──────────────────┬──────────────────────┘
                             Model loaded?
                            /           \
                          CÓ            KHÔNG
                           │               │
                   topics = [ml_topic]     │
                   method="ml_svm"         │
                                           │
                    ┌──────────────────────▼──────────────────┐
                    │ Tầng 4: Rule-based Keywords              │
                    │ Keyword matching (vi + en)               │
                    │ Nếu không match → topics = ["Khác"]     │
                    └──────────────────────────────────────────┘
```

---

## 8. Thiết kế Hệ thống Xác thực

### Luồng JWT chuẩn

```
1. Login:
   POST /auth/login { username, password }
   → verify_password(plain, hash) ← bcrypt
   → create_access_token({ sub: username, role: admin })
   → { access_token: "eyJ...", expires_in: 86400 }
   → Frontend lưu vào localStorage

2. Request có auth:
   GET /posts
   Authorization: Bearer eyJ...
   → get_current_user(credentials)
   → decode_access_token(token)
   → jwt.decode(token, JWT_SECRET_KEY, algorithms=["HS256"])
   → Validate exp, sub
   → Return username

3. Admin check:
   DELETE /admin/users/{id}
   → get_current_admin_user()
   → get_current_user() → TokenData
   → if token_data.role != "admin": raise 403
```

### Luồng Telegram Phone Auth

```
Step 1: POST /auth/telegram/send-code { phone_number: "+84..." }
  → TelegramClient.connect()
  → client.send_code_request(phone)
  → _pending_logins[session_id] = { client, phone, hash, created_at }
  → Return { session_id, phone_code_hash }

Step 2: POST /auth/telegram/verify-code { session_id, code, phone_code_hash }
  → client = _pending_logins[session_id]["client"]
  → client.sign_in(phone, code, phone_code_hash)
  → session_string = StringSession.save(client.session)
  → users.update_one({ telegram_session: session_string })
  → create_access_token(...)
  → del _pending_logins[session_id]  # Cleanup
  → Return JWT
```

---

## 9. Thiết kế Hot News Cache

### In-Memory Structure

```python
_hotnews_mem: dict[str, dict] = {
    "24":  { "data": [...], "cached_at": datetime, "ttl_hours": 1 },
    "48":  { "data": [...], "cached_at": datetime, "ttl_hours": 2 },
    "72":  { "data": [...], "cached_at": datetime, "ttl_hours": 3 },
    "168": { "data": [...], "cached_at": datetime, "ttl_hours": 3 },
}

_hotnews_locks: dict[str, asyncio.Lock] = {
    "24":  asyncio.Lock(),
    "48":  asyncio.Lock(),
    ...
}
```

**Tại sao TTL tăng theo window?**  
Window lớn hơn (72h) = dữ liệu thay đổi chậm hơn → có thể cache lâu hơn. Window nhỏ (24h) = tin tức mới → cần refresh thường hơn.

**Tại sao dùng asyncio.Lock thay vì threading.Lock?**  
FastAPI chạy trong asyncio event loop. `asyncio.Lock` không block event loop khi `await`. `threading.Lock` sẽ block toàn bộ event loop nếu dùng trong async context.

### Precompute Worker

```python
async def _hotnews_precompute_worker():
    """Warm cache ngay khi startup, sau đó refresh theo TTL."""
    for window_hours in [24, 48, 72]:
        await _compute_hotnews(window_hours)
    
    while True:
        await asyncio.sleep(3600)  # Mỗi 1 giờ
        # Refresh bucket nào đã hết TTL
        for window_hours, ttl_hours in [(24, 1), (48, 2), (72, 3)]:
            bucket = str(window_hours)
            cached = _hotnews_mem.get(bucket, {})
            if cached:
                age = (datetime.utcnow() - cached["cached_at"]).total_seconds() / 3600
                if age >= ttl_hours:
                    await _compute_hotnews(window_hours)
```

---

## 10. Scripts & CLI Tools

### Maintenance Scripts

| Script | Lệnh | Mục đích |
|---|---|---|
| `create_indexes.py` | `python scripts/create_indexes.py` | Tạo MongoDB indexes |
| `train_ml_classifier.py` | `python scripts/train_ml_classifier.py` | Train TF-IDF + SVM |
| `evaluate_model.py` | `python scripts/evaluate_model.py` | Đánh giá accuracy, F1 per topic |
| `predict_topics.py` | `python scripts/predict_topics.py "text..."` | Test predict thủ công |
| `balance_training_data.py` | `python scripts/balance_training_data.py` | Cân bằng class distribution |
| `auto_join_channels.py` | `python scripts/auto_join_channels.py` | Tự join kênh Telegram từ list |
| `list_channels_from_db.py` | `python scripts/list_channels_from_db.py` | Liệt kê kênh trong DB |
| `migrate_db_schema.py` | `python scripts/migrate_db_schema.py` | Migration schema MongoDB |
| `seed_hot_topics.py` | `python scripts/seed_hot_topics.py` | Seed hot topics test data |
| `extract_keyword_trends.py` | `python scripts/extract_keyword_trends.py` | Tổng hợp keyword trends |
| `aggregate_topic_stats.py` | `python scripts/aggregate_topic_stats.py` | Thống kê theo chủ đề |
| `fix_misclassified_topics.py` | `python scripts/fix_misclassified_topics.py` | Sửa label sai hàng loạt |
| `verify_labels.py` | `python scripts/verify_labels.py` | Verify manual labels |

### Windows Task Scheduler

```cmd
# scripts/setup_windows_scheduler.cmd
# Đặt lịch tự động fetch Telegram + X mỗi 6 giờ
# Dùng scripts/*.cmd wrapper cho mỗi task
```

### .cmd Wrappers

Mỗi script Python có file `.cmd` tương ứng để chạy dễ từ Windows:
```cmd
:: scripts/fetch_telegram.cmd
@echo off
cd /d "%~dp0.."
python -m src.ingestion.telegram_worker %*
```
