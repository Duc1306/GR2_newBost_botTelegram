# Tài liệu Tham chiếu Kỹ thuật — NewsBot

> **Phiên bản:** 2.0.0 | **Ngôn ngữ:** Python 3.12 / React 18  
> Tài liệu này là nguồn tham chiếu đầy đủ cho mọi interface, cấu hình và hành vi của hệ thống.

---

## Mục lục

1. [Tổng quan Kiến trúc](#1-tổng-quan-kiến-trúc)
2. [Cấu trúc Thư mục](#2-cấu-trúc-thư-mục)
3. [Backend — Phân tích theo Tầng](#3-backend--phân-tích-theo-tầng)
4. [Frontend — Phân tích](#4-frontend--phân-tích)
5. [Database — Thiết kế](#5-database--thiết-kế)
6. [Xác thực & Bảo mật](#6-xác-thực--bảo-mật)
7. [API Reference đầy đủ](#7-api-reference-đầy-đủ)
8. [Biến Môi trường](#8-biến-môi-trường)
9. [Background Workers](#9-background-workers)
10. [Pipeline ML](#10-pipeline-ml)
11. [Tích hợp Bên ngoài](#11-tích-hợp-bên-ngoài)
12. [Build & Deployment](#12-build--deployment)
13. [Testing](#13-testing)
14. [Tính năng TTS](#14-tính-năng-tts)
15. [Từ điển Thuật ngữ](#15-từ-điển-thuật-ngữ)

---

## 1. Tổng quan Kiến trúc

NewsBot là hệ thống tổng hợp tin tức đa nguồn. Dữ liệu được thu thập từ Telegram (qua Telethon MTProto) và X/Twitter (qua Apify scraping), xử lý bằng pipeline ML tự động phân loại chủ đề, sau đó phục vụ qua REST API tới frontend React.

```
[Telegram Channels]──Telethon──┐
                                ├──► [Ingestion Layer]──► [Processing Layer]──► MongoDB
[X/Twitter Accounts]──Apify────┘              │
                                              ▼
                                    [FastAPI REST API]──► [React Frontend (Vercel)]
```

**Thành phần chính:**

| Thành phần | Công nghệ | Mục đích |
|---|---|---|
| API Server | FastAPI 0.115 + Uvicorn | REST API, auth, business logic |
| Database | MongoDB Atlas (PyMongo 4.8) | Lưu trữ toàn bộ dữ liệu |
| Frontend | React 18 + Vite + MUI | SPA hiển thị tin tức và analytics |
| Telegram Client | Telethon 1.34 | Fetch bài từ kênh Telegram |
| X Scraper | Apify Client ≥1.7 | Fetch tweet không cần Twitter API |
| ML Classifier | scikit-learn 1.5.2 (TF-IDF + SVM) | Phân loại 19 chủ đề |
| AI Engine | OpenAI GPT-4o-mini | Hot topic detection + embedding |
| TTS | edge-tts ≥6.1.9 | Đọc bản tin tiếng Việt |

---

## 2. Cấu trúc Thư mục

```
botTele/
├── src/                    # Backend Python source
│   ├── config.py           # Tất cả cấu hình từ env vars
│   ├── api/
│   │   ├── main.py         # FastAPI app entry point, lifespan
│   │   ├── auth.py         # JWT + bcrypt auth helpers
│   │   ├── channels.py     # /user/channels/* router
│   │   ├── telegram_auth.py# Telegram phone login (MTProto OTP)
│   │   ├── middleware.py   # SlowAPI rate limiting, loguru logging
│   │   └── routes/         # Route files tách theo domain
│   │       ├── auth_routes.py         # /auth/*
│   │       ├── post_routes.py         # /posts, /topics, /stats
│   │       ├── analytics_routes.py    # /analytics/* (timeline, keywords, heatmap)
│   │       ├── public_routes.py       # /public/* (no-auth)
│   │       ├── hotnews_routes.py      # /hotnews, /hot-topics
│   │       ├── tts_routes.py          # /public/tts
│   │       ├── notification_routes.py # /notifications/*
│   │       ├── settings_routes.py     # /settings, /settings/change-password
│   │       └── admin_routes.py        # /admin/* (ML metrics, X fetch, user mgmt)
│   ├── db/
│   │   └── mongo.py        # MongoDB singleton client
│   ├── ingestion/
│   │   ├── telegram_worker.py     # CLI: fetch từ Telegram
│   │   ├── x_worker.py            # Apify X/Twitter ingest
│   │   ├── channel_queue_worker.py# Background: process pending channels
│   │   ├── run_scheduled_refresh.py
│   │   └── sources.py             # Đọc danh sách nguồn từ DB
│   ├── models/
│   │   ├── post.py         # Post, TopicPrediction, MediaItem
│   │   ├── user.py         # UserInDB, UserPublic, RegisterRequest
│   │   ├── channel.py      # Channel, ChannelSummary
│   │   ├── notification.py
│   │   └── settings.py     # UserSettings
│   └── processing/
│       ├── cleaning.py           # clean_text(), extract_links()
│       ├── topic_classifier.py   # Rule-based keyword cascade
│       ├── ml_topic_classifier.py# TF-IDF + LinearSVC
│       ├── ai_topic_detector.py  # OpenAI GPT-4o-mini
│       ├── geo_classifier.py     # Phân loại địa lý 10 vùng
│       ├── backfill_topics.py    # Batch backfill topics & geo
│       ├── category_mapper.py    # Channel category → Vietnamese topic
│       ├── web_scraper.py        # Article enrichment
│       ├── dedupe.py             # SHA-256 deduplication
│       └── lang.py               # Language detection (vi/en)
├── scripts/                # CLI tools và maintenance scripts
├── web/                    # Frontend React/Vite
│   └── src/
│       ├── App.jsx
│       ├── context/AuthContext.jsx
│       ├── lib/api.jsx, publicApi.js
│       ├── hooks/useApi.jsx
│       └── pages/admin/, pages/user/, pages/public/, pages/auth/
├── tests/                  # pytest test suite (9 files)
├── models/                 # ML model files (.pkl)
├── docs/                   # Tài liệu dự án
└── requirements.txt
```

---

## 3. Backend — Phân tích theo Tầng

### 3.1 Config Layer (`src/config.py`)

Tất cả biến môi trường được nạp tại đây. Xem bảng đầy đủ tại [Mục 8](#8-biến-môi-trường).

**Hàm tiện ích:**

| Hàm | Trả về | Mô tả |
|---|---|---|
| `env_channels()` | `List[str]` | Đọc `TELEGRAM_CHANNELS` từ env, tách bằng dấu phẩy |
| `get_allowed_origins()` | `List[str]` | Trả danh sách CORS origin (deduplicated, có defaults) |

---

### 3.2 API Layer

#### `src/api/main.py` — App Entry Point

**Lifespan (startup/shutdown):**
```
startup:
  1. run_in_executor → create_indexes() (blocking, chạy 1 lần)
  2. asyncio.create_task → run_worker()           # poll pending_channels mỗi 30s
  3. asyncio.create_task → run_refresh_loop()     # refresh active channels mỗi 12h
  4. asyncio.create_task → _hotnews_precompute_worker()  # warm cache
shutdown:
  → cancel tất cả 3 tasks
```

**Routers được include:**
```python
app.include_router(channels_router)       # /user/channels/*
app.include_router(telegram_auth_router)  # /auth/telegram/*
app.include_router(auth_router)           # /auth/*
app.include_router(post_router)           # /posts, /topics, /stats
app.include_router(analytics_router)      # /analytics/*
app.include_router(notification_router)   # /notifications/*
app.include_router(settings_router)       # /settings
app.include_router(public_router)         # /public/*, / , /health
app.include_router(tts_router)            # /public/tts
app.include_router(hotnews_router)        # /hotnews, /hot-topics
app.include_router(admin_router)          # /admin/*
```

#### `src/api/auth.py` — Auth Logic

| Hàm | Signature | Mô tả |
|---|---|---|
| `verify_password` | `(plain, hashed) → bool` | bcrypt verify |
| `get_password_hash` | `(password) → str` | bcrypt hash |
| `create_access_token` | `(data, expires_delta?) → str` | JWT HS256 encode |
| `decode_access_token` | `(token) → TokenData` | JWT decode + validate |
| `login` | `(username, password) → LoginResponse` | Full auth flow |
| `register_user` | `(RegisterRequest) → dict` | Tạo user mới |
| `get_current_user` | `Depends` | Bearer + API Key auth |
| `get_current_admin_user` | `Depends` | Auth + role == "admin" |
| `get_current_user_token_data` | `Depends` | Trả `TokenData` (có role) |

**Pydantic Models trong auth:**
```python
class LoginRequest(BaseModel):
    username: str
    password: str

class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int          # giây
    username: str
    role: str

class TokenData(BaseModel):
    username: str
    role: str = "user"
    exp: datetime
```

#### `src/api/channels.py` — Channel Subscriptions

**Prefix:** `/user/channels`

| Method | Path | Mô tả |
|---|---|---|
| GET | `/user/channels` | Danh sách kênh đã subscribe |
| POST | `/user/channels/subscribe` | Subscribe 1 kênh |
| POST | `/user/channels/subscribe/bulk` | Subscribe nhiều kênh cùng lúc |
| DELETE | `/user/channels/{username}` | Unsubscribe |
| GET | `/user/channels/catalog` | Catalog kênh có sẵn (từ `channel.json`) |
| GET | `/user/channels/{username}/summary` | Channel summary + stats |
| POST | `/user/channels/{username}/refresh` | Trigger refresh thủ công |

**Cooldown X/Twitter:** 6 giờ giữa 2 lần Apify fetch cho cùng 1 kênh/keyword.

#### `src/api/telegram_auth.py` — Telegram Phone Login

**Luồng OTP 3 bước:**
```
1. POST /auth/telegram/send-code      { phone_number, display_name? }
                                       → { session_id, phone_code_hash }
2. POST /auth/telegram/verify-code    { session_id, phone_number, code, phone_code_hash }
                                       → { access_token, ... }  (JWT + session string lưu DB)
3. GET  /auth/telegram/channels       Authorization: Bearer <token>
                                       → [{ id, title, username, members_count }]
4. POST /auth/telegram/select-channels { channel_usernames: [...] }
```

**In-memory pending sessions:** TTL 5 phút, cleanup tự động.

---

### 3.3 Data Layer (`src/db/mongo.py`)

```python
# Singleton pattern
_client: Optional[MongoClient] = None
_db: Optional[Database] = None

def init_mongo() -> None: ...         # Khởi tạo client
def get_db() -> Database: ...         # Trả database instance
def get_posts_collection() -> Collection: ...
def get_users_collection() -> Collection:  # Tự tạo unique index trên username
    ...
```

---

### 3.4 Processing Layer (Pure Python — no I/O)

#### `src/processing/cleaning.py`

| Hàm | Input | Output | Mô tả |
|---|---|---|---|
| `clean_text(raw)` | `str` | `tuple[str, list[str]]` | Trả `(text_sạch, [links])` |
| `extract_links(text)` | `str` | `list[str]` | Extract URLs bằng regex |
| `normalize_whitespace(text)` | `str` | `str` | Bỏ whitespace thừa |
| `remove_emojis(text)` | `str` | `str` | Xóa emoji Unicode |

#### `src/processing/topic_classifier.py` — Rule-based

```python
TOPICS = [
    "Crypto", "Kinh tế", "Công nghệ", "Chính trị", "Thế giới",
    "Pháp luật", "Ô tô-Xe máy", "Khoa học", "Thể thao", "Giải trí",
    "Sức khỏe", "Giáo dục", "Việc làm", "Du lịch", "Ẩm thực",
    "Kinh doanh & Khởi nghiệp", "Trò chơi & Ứng dụng",
    "Tin tức & Truyền thông", "Khác"
]

def classify_topics(text: str) -> list[str]:
    """Keyword matching (Vietnamese + English). Trả [] nếu không match."""
```

#### `src/processing/ml_topic_classifier.py` — ML Classifier

```python
class MLTopicClassifier:
    model_path: str = "models/topic_classifier_svm.pkl"

    def load(self) -> None: ...          # Lazy load từ .pkl
    def predict(self, text: str) -> TopicPrediction: ...
    # Trả: TopicPrediction(topic, confidence, model_version, method="ml_svm")
```

**Pipeline:** `TF-IDF Vectorizer (ngram 1-2, max_features=50000)` → `LinearSVC (C=1.0)`

#### `src/processing/geo_classifier.py` — Geographic Region (Mới)

```python
_GEO_KEYWORDS: dict[str, list[str]] = {
    "Việt Nam": [...],   # ≈ 30 keywords
    "Mỹ": [...],
    "Trung Quốc": [...],
    "Nga": [...],
    "Nhật Bản": [...],
    "Hàn Quốc": [...],
    "Châu Âu": [...],
    "Trung Đông": [...],
    "Đông Nam Á": [...],
    "Toàn cầu": [...],
}

def classify_geo(text: str, channel_username: str = "") -> str | None:
    """Rule-based: return région or None. Dùng trong ingest pipeline."""

async def classify_geo_with_ai(text: str) -> str | None:
    """OpenAI fallback khi rule-based không chắc. Dùng trong backfill."""
```

#### `src/processing/backfill_topics.py` — Backfill (Mới)

```bash
# Chế độ chạy:
python -m src.processing.backfill_topics --count      # xem trước
python -m src.processing.backfill_topics              # rule-based + AI + geo
python -m src.processing.backfill_topics --geo-only   # chỉ backfill geo
python -m src.processing.backfill_topics --ai-only    # chỉ AI topic
python -m src.processing.backfill_topics --limit 500  # giới hạn bài
```

#### `src/processing/ai_topic_detector.py`

| Hàm | Input | Output |
|---|---|---|
| `detect_new_hot_topics(posts, window_hours)` | `list[Post], int` | `list[HotTopic]` |
| `expand_keywords(topic_name)` | `str` | `list[str]` |
| `classify_post_topic_with_ai(text)` | `str` | `list[str]` |
| `classify_geo_with_ai(text)` | `str` | `str \| None` |

**Graceful degradation:** Trả `[]`/giá trị gốc nếu `OPENAI_API_KEY` không có.

#### `src/processing/web_scraper.py`

```python
BLACKLIST_DOMAINS = ["facebook.com", "twitter.com", "youtube.com", "t.me", ...]
CATEGORY_MAPPING = {
    "crypto": "Crypto", "kinh-te": "Kinh tế",
    "cong-nghe": "Công nghệ", ...
}

class ArticleScraper:
    def scrape(self, url: str) -> FullArticle | None: ...

async def enrich_post_with_article(post: Post) -> Post:
    """Tự động lấy nội dung bài viết từ URL đầu tiên trong links[]."""
```

---

### 3.5 Ingestion Layer

#### `src/ingestion/telegram_worker.py`

**CLI usage:**
```bash
python -m src.ingestion.telegram_worker          # fetch limit=200/channel
python -m src.ingestion.telegram_worker --full   # fetch limit=1000/channel
```

**Pipeline per channel:**
1. `TelegramClient.get_messages()` → raw messages
2. `clean_text()` → text + links
3. `langdetect.detect()` → `lang` field
4. `enrich_post_with_article()` → full article (nếu có URL)
5. `classify_post_topics()` → ML + rule-based cascade
6. Compute `dedupe_key = SHA-256(text[:200])[:32]`
7. `update_one(upsert=True)` vào MongoDB

#### `src/ingestion/channel_queue_worker.py`

**Constants:**
```python
POLL_INTERVAL   = 30       # giây — poll pending_channels
REFRESH_INTERVAL = 43200   # giây (12h) — refresh active channels
MAX_ATTEMPTS    = 3        # thử tối đa trước khi status = "error"
FETCH_DAYS      = 7        # lấy bài trong 7 ngày gần nhất
SUMMARY_DAYS    = 1        # summary dựa trên 1 ngày gần nhất
```

**State machine channel:**
```
pending ──(fetch OK)──► active
pending ──(fail×3)───► error
active  ──(12h)──────► [refresh] ──(OK)──► active
                                ──(fail)──► error
```

#### `src/ingestion/x_worker.py`

**Apify Actor:** `quacker/twitter-scraper`

```python
async def ingest_once(
    mode: Literal["user", "keyword"],
    usernames: list[str] = [],
    keywords: list[str] = [],
    max_items: int = 20,
) -> int:  # số bài đã lưu
```

---

## 4. Frontend — Phân tích

### Công nghệ
- React 18 + Vite 5 + TypeScript (JSX)
- MUI (Material UI) v5 components
- TanStack Query v5 (React Query) — server state
- React Router v6 — client-side routing
- Deploy: Vercel (SPA, rewrites về `index.html`)

### Routing (`web/src/App.jsx`)

| Path | Component | Access |
|---|---|---|
| `/` | `PublicHomePage` | Công khai |
| `/login` | `LoginPage` | Công khai |
| `/register` | `RegisterPage` | Công khai |
| `/telegram-login` | `TelegramLoginPage` | Công khai |
| `/overview` | `OverviewPage` | Auth required |
| `/posts` | `PostsPage` | Auth required |
| `/trending` | `TrendingPage` | Auth required |
| `/analytics` | `AnalyticsPage` | Auth required |
| `/dashboard` | `DashboardPage` | Auth required |
| `/settings` | `SettingsPage` | Auth required |
| `/users` | `UsersPage` | Admin only |

### AuthContext (`web/src/context/AuthContext.jsx`)

```javascript
const { user, token, login, logout, isAdmin } = useAuth();
// Tự động logout sau 60 phút không hoạt động
// decodeJwtRole(token) — đọc role từ JWT payload
// Persist: localStorage.getItem("auth_token")
```

### API Client (`web/src/lib/api.jsx`)

```javascript
async function fetchWithAuth(url, options = {}) {
    // Tự động thêm Authorization: Bearer <token>
    // 401 → redirect về /login
}
```

### React Query Hooks (`web/src/hooks/useApi.jsx`)

| Hook | Endpoint | staleTime |
|---|---|---|
| `useStats(filters)` | GET `/stats` | 5 phút |
| `usePosts(filters)` | GET `/posts` | 2 phút |
| `usePostsCount(filters)` | GET `/posts/count` | 5 phút |
| `useTopics(platform)` | GET `/topics` | 10 phút |
| `useTrendingTopics(platform)` | GET `/topics/trending` | 5 phút |
| `useTopicStats(platform)` | GET `/topics/stats` | 10 phút |
| `useKeywords(filters)` | GET `/analytics/keywords` | 10 phút |
| `useTrendingKeywords(filters)` | GET `/analytics/keywords/trending` | 5 phút |
| `useTimeline(filters)` | GET `/analytics/timeline` | 15 phút |
| `useHotNews(window)` | GET `/hotnews` | 5 phút |

---

## 5. Database — Thiết kế

**Database name:** `newsbot`

### Collections

| Collection | Mô tả | Indexes chính |
|---|---|---|
| `posts` | Tất cả bài viết | `id` (unique), `dedupe_key` (unique), `created_at`, `topics`, `platform` |
| `channels` | Kênh user đã subscribe | `username` (unique), `(username, user_id)` |
| `channel_metadata` | Thông tin kênh Telegram/X | `username`, `platform` |
| `channel_summaries` | AI-generated channel summaries | `channel_username` |
| `users` | Tài khoản người dùng | `username` (unique), `email` |
| `user_channels` | Quan hệ user ↔ channel | `(username, channel)` compound unique |
| `keyword_trends` | Keyword frequency theo thời gian | `keyword`, `date` |
| `hot_topics` | Hot topics được phát hiện bởi AI | `detected_at` |
| `notifications` | Thông báo hệ thống | `user_id`, `created_at` |
| `pending_channels` | Hàng đợi xử lý kênh mới | `username`, `status` |

### Schema `posts`

```json
{
  "id": "telegram:channelname:123456",
  "source": "channelname",
  "platform": "telegram | twitter",
  "text": "Nội dung bài viết...",
  "created_at": "ISODate",
  "links": ["https://..."],
  "lang": "vi | en",
  "topics": ["Crypto", "Công nghệ"],
  "topic_predictions": [
    {
      "topic": "Crypto",
      "confidence": 0.87,
      "model_version": "svm_v1",
      "method": "ml_svm | rule_based | channel_category"
    }
  ],
  "source_category": "Tin tức",
  "source_topic": "Crypto",
  "dedupe_key": "abc123...(32 chars)",
  "score": 0.5,
  "full_article": {
    "title": "...", "content": "...", "url": "..."
  },
  "manual_labels": ["Crypto"],
  "labels_verified": false
}
```

### Schema `users`

```json
{
  "username": "nguyenvana",
  "password_hash": "$2b$12$...",
  "role": "user | admin",
  "status": "active | pending | banned",
  "email": "...",
  "full_name": "...",
  "phone_number": "...",
  "telegram_username": "...",
  "telegram_session": "1BVtsO...(session string)",
  "created_at": "ISODate",
  "last_login": "ISODate"
}
```

### Schema `channels`

```json
{
  "username": "x:elonmusk | xkw:bitcoin | channelname",
  "platform": "telegram | twitter",
  "display_name": "Tên hiển thị",
  "status": "pending | active | error",
  "user_id": "username_of_subscriber",
  "category": "Công nghệ",
  "post_count": 150,
  "processed_at": "ISODate",
  "last_apify_fetch": "ISODate",
  "error_message": null,
  "attempts": 0
}
```

---

## 6. Xác thực & Bảo mật

### Các phương thức xác thực

| Phương thức | Header/Cookie | Flow |
|---|---|---|
| JWT Bearer | `Authorization: Bearer <token>` | Login → nhận token → gửi mỗi request |
| API Key | `X-API-Key: <key>` | Dùng cho script/automation |
| Telegram OTP | Phone number + Telegram OTP | POST `/auth/telegram/send-code` → verify |

### JWT Specification

```
Algorithm:  HS256
Secret:     JWT_SECRET_KEY (env var)
Expiry:     1440 phút (24 giờ) — cấu hình qua JWT_ACCESS_TOKEN_EXPIRE_MINUTES
Payload:    { "sub": "username", "role": "user|admin", "exp": timestamp }
```

### Role-Based Access

| Role | Quyền |
|---|---|
| `user` | Đọc posts, analytics; quản lý channel của mình; TTS |
| `admin` | Mọi quyền của user + quản lý users, xem tất cả channels |

### Rate Limiting (SlowAPI)

```
Mặc định:     60 req/phút, 1000 req/giờ
/posts:       100 req/phút (endpoint riêng)
/auth/login:  Khuyến nghị thêm 5 req/phút (xem CODE-REVIEW.md)
```

---

## 7. API Reference đầy đủ

### Authentication

| Method | Path | Auth | Request Body | Response |
|---|---|---|---|---|
| POST | `/auth/login` | Không | `{username, password}` | `LoginResponse` |
| POST | `/auth/register` | Không | `{username, password, full_name?, email?}` | `LoginResponse` |
| POST | `/auth/logout` | Bearer | — | `{message}` |
| GET | `/auth/me` | Bearer | — | `{username, role, full_name, email, ...}` |
| POST | `/auth/telegram/send-code` | Không | `{phone_number, display_name?}` | `{session_id, phone_code_hash}` |
| POST | `/auth/telegram/verify-code` | Không | `{session_id, phone_number, code, phone_code_hash}` | `LoginResponse` |
| GET | `/auth/telegram/channels` | Bearer | — | `[{id, title, username, ...}]` |
| POST | `/auth/telegram/select-channels` | Bearer | `{channel_usernames: [...]}` | `{saved: N}` |

### Posts & Content

| Method | Path | Auth | Query Params |
|---|---|---|---|
| GET | `/posts` | Bearer | `platform, source, topic, lang, q, link_only, topics_only, limit(1-100), skip` |
| GET | `/posts/count` | Bearer | `source, topic, lang, link_only, topics_only, platform` |
| GET | `/posts/{post_id}` | Bearer | — |
| GET | `/topics` | Bearer | `platform` |
| GET | `/topics/trending` | Bearer | `platform, limit` |
| GET | `/topics/stats` | Bearer | `platform` |
| GET | `/stats` | Bearer | `link_only, topics_only, lang, platform` |

### Analytics

| Method | Path | Auth | Query Params |
|---|---|---|---|
| GET | `/analytics/trends` | Bearer | `topic, platform, days` |
| GET | `/analytics/keywords` | Bearer | `platform, limit, days` |
| GET | `/analytics/keywords/trending` | Bearer | `platform, limit` |
| GET | `/analytics/comparison` | Bearer | `topics[], platform, days` |
| GET | `/analytics/timeline` | Bearer | `platform, days, topic` |

### Hot News

| Method | Path | Auth | Query Params |
|---|---|---|---|
| GET | `/hotnews` | Bearer | `window_hours(24/48/72, default=24), limit` |

### Channel Subscriptions

| Method | Path | Auth | Notes |
|---|---|---|---|
| GET | `/user/channels` | Bearer | Danh sách kênh của user hiện tại |
| GET | `/user/channels/catalog` | Bearer | Catalog từ `channel.json` |
| POST | `/user/channels/subscribe` | Bearer | `{username, platform, display_name?, category?}` |
| POST | `/user/channels/subscribe/bulk` | Bearer | `{channels: [{...}]}` |
| DELETE | `/user/channels/{username}` | Bearer | Unsubscribe |
| GET | `/user/channels/{username}/summary` | Bearer | Channel summary + post stats |
| POST | `/user/channels/{username}/refresh` | Bearer | Trigger manual refresh |

### System

| Method | Path | Auth |
|---|---|---|
| GET | `/` | Không |
| GET | `/health` | Không |

---

## 8. Biến Môi trường

### Bắt buộc (production)

| Biến | Mô tả | Ví dụ |
|---|---|---|
| `MONGO_URI` | MongoDB connection string | `mongodb+srv://user:pass@cluster.mongodb.net/` |
| `JWT_SECRET_KEY` | JWT signing secret (random, dài ≥32 chars) | `openssl rand -hex 32` |
| `TELEGRAM_API_ID` | Từ my.telegram.org | `12345678` |
| `TELEGRAM_API_HASH` | Từ my.telegram.org | `abcdef1234...` |
| `TELEGRAM_SESSION_STRING` | Telethon session string | `1BVtsO...` |

### Tuỳ chọn (features)

| Biến | Mặc định | Mô tả |
|---|---|---|
| `DB_NAME` | `newsbot` | Tên MongoDB database |
| `ADMIN_USERNAME` | `admin` | Username tài khoản admin mặc định |
| `ADMIN_PASSWORD` | `admin123` | **Phải đổi trong production!** |
| `TELEGRAM_FETCH_LIMIT` | `200` | Số bài fetch mỗi lần chạy telegram_worker |
| `TELEGRAM_CHANNELS` | `""` | Danh sách kênh cách nhau bằng dấu phẩy |
| `JWT_ACCESS_TOKEN_EXPIRE_MINUTES` | `1440` | Thời hạn JWT (phút) |
| `ALLOWED_ORIGINS` | `""` | CORS origins bổ sung (cách nhau bằng dấu phẩy) |
| `RATE_LIMIT_PER_MINUTE` | `60` | Số request/phút tối đa |
| `RATE_LIMIT_PER_HOUR` | `1000` | Số request/giờ tối đa |
| `OPENAI_API_KEY` | `""` | Bỏ trống = tắt tính năng AI |
| `OPENAI_MODEL` | `gpt-4o-mini` | Model OpenAI |
| `APIFY_API_TOKEN` | `""` | Bỏ trống = tắt X scraping |

---

## 9. Background Workers

### Worker 1: `run_worker()` — Channel Queue Poller

- **Frequency:** Poll mỗi `POLL_INTERVAL=30` giây
- **Nhiệm vụ:** Tìm channels với `status="pending"`, gọi `_process_channel()`
- **Flow:** fetch posts → lưu DB → tạo OpenAI summary → update `status="active"`
- **Retry:** Tối đa `MAX_ATTEMPTS=3`. Sau 3 lần → `status="error"`

### Worker 2: `run_refresh_loop()` — Active Channel Refresher

- **Frequency:** Mỗi `REFRESH_INTERVAL=43200` giây (12 giờ)
- **Nhiệm vụ:** Refresh tất cả channels đang `status="active"`
- **Flow:** Tương tự run_worker nhưng cho channels đã active

### Worker 3: `_hotnews_precompute_worker()` — Cache Warmer

- **Frequency:** Chạy ngay sau startup, sau đó theo chu kỳ
- **Nhiệm vụ:** Pre-compute hot news cho window 24h, 48h, 72h
- **Cache TTL:** 1h / 2h / 3h tương ứng
- **Mục đích:** Đảm bảo response `/hotnews` luôn nhanh (không gọi OpenAI khi user request)

---

## 10. Pipeline ML

### Phân loại 4 tầng (ưu tiên giảm dần)

```
1. channel_category  — Category từ channel.json (ưu tiên cao nhất)
2. url_slug         — URL slug → CATEGORY_MAPPING trong web_scraper.py
3. ml_svm           — TF-IDF + LinearSVC (models/topic_classifier_svm.pkl)
4. rule_based       — Keyword matching (topic_classifier.py)
```

### Training ML Model

```bash
# Thu thập dữ liệu đã label
python scripts/train_ml_classifier.py

# Hoặc có class weights (khi data mất cân bằng)
python scripts/train_with_class_weight.py

# Đánh giá model
python scripts/evaluate_model.py
```

**Output:** `models/topic_classifier_svm.pkl` — TfidfVectorizer + LinearSVC pipeline

### 19 Topics

```
Crypto | Kinh tế | Công nghệ | Chính trị | Thế giới | Pháp luật
Ô tô-Xe máy | Khoa học | Thể thao | Giải trí | Sức khỏe | Giáo dục
Việc làm | Du lịch | Ẩm thực | Kinh doanh & Khởi nghiệp
Trò chơi & Ứng dụng | Tin tức & Truyền thông | Khác
```

---

## 11. Tích hợp Bên ngoài

### Telegram (Telethon)

- **Protocol:** MTProto (không phải Bot API)
- **Auth:** Session String (tương đương đăng nhập tài khoản)
- **Rate limit:** Telethon tự xử lý `FloodWaitError`
- **Dữ liệu:** `Message.text`, `Message.date`, `Message.id`, media

### X/Twitter (Apify)

- **Actor:** `quacker/twitter-scraper`
- **Auth:** `APIFY_API_TOKEN`
- **Mode:** `user` (lấy tweet từ account) hoặc `keyword` (search hashtag)
- **Cooldown:** 6 giờ/channel để tiết kiệm Apify credits
- **Dữ liệu:** tweet text, created_at, author, likes, retweets

### OpenAI

- **Model:** `gpt-4o-mini` (hot topic detection)
- **Embedding:** `text-embedding-3-small` (post scoring)
- **Graceful degradation:** Hệ thống hoạt động bình thường nếu không có API key

## 12. Build & Deployment

### Local Development

```bash
# Backend
pip install -r requirements.txt
uvicorn src.api.main:app --reload --port 8000

# Frontend
cd web && npm install && npm run dev
```

### Production (Render.com + Vercel)

| Thành phần | Platform | Config |
|---|---|---|
| Backend API | Render.com (Web Service) | `render.yaml` |
| Frontend SPA | Vercel | `web/vercel.json` |
| Database | MongoDB Atlas | Connection string qua env var |

**`render.yaml`:**
```yaml
services:
  - type: web
    name: newsbot-api
    env: python
    buildCommand: pip install -r requirements.txt
    startCommand: uvicorn src.api.main:app --host 0.0.0.0 --port $PORT
```

### Database Indexes

```bash
python scripts/create_indexes.py
# Tự động chạy khi API khởi động (lifespan)
```

---

## 13. Testing

### Chạy tests

```bash
pytest                          # Tất cả tests
pytest tests/test_auth_roles.py # Test cụ thể
pytest -v --tb=short            # Verbose output
```

### pytest.ini

```ini
[pytest]
testpaths = tests
python_files = test_*.py
asyncio_mode = auto
```

### Danh sách test files

| File | Test gì |
|---|---|
| `test_auth_roles.py` | JWT auth, role-based access control |
| `test_cleaning.py` | `clean_text()`, `extract_links()`, `remove_emojis()` |
| `test_dedupe.py` | SHA-256 deduplication logic |
| `test_ml_classifier.py` | MLTopicClassifier predict, load model |
| `test_post_model.py` | Post Pydantic model validation |
| `test_security.py` | Security headers, JWT tampering |
| `test_web_scraper.py` | ArticleScraper, blacklist domains |
| `test_x_scraper.py` | X/Twitter Apify scraper |

---

## 14. Tính năng TTS

**Engine:** Microsoft Edge TTS (`edge-tts` ≥6.1.9)  
**Voice:** `vi-VN-HoaiMyNeural` (tiếng Việt, giọng nữ)

```python
import edge_tts
import asyncio

async def text_to_speech(text: str, output_file: str):
    communicate = edge_tts.Communicate(text, voice="vi-VN-HoaiMyNeural")
    await communicate.save(output_file)
```

**Frontend:** Nút "Nghe bản tin" trên PostCard — gọi endpoint TTS, phát audio trong browser.

---

## 15. Từ điển Thuật ngữ

| Thuật ngữ | Nghĩa |
|---|---|
| **Session String** | Chuỗi mã hóa Telethon đại diện cho phiên đăng nhập Telegram — tương đương full account access |
| **Dedupe Key** | SHA-256 của 200 ký tự đầu text, dùng để phát hiện bài trùng lặp |
| **Channel** | Kênh Telegram hoặc tài khoản X/Twitter mà user subscribe để theo dõi |
| **Pending Channel** | Channel vừa được subscribe, đang chờ background worker xử lý |
| **Hot News** | Tin tức nổi bật được phát hiện bởi OpenAI GPT-4o-mini dựa trên tần suất keyword |
| **TF-IDF** | Term Frequency–Inverse Document Frequency — biểu diễn text cho ML |
| **LinearSVC** | Linear Support Vector Classifier — mô hình phân loại chủ đề |
| **MTProto** | Giao thức riêng của Telegram, nhanh và mã hóa end-to-end |
| **Apify** | Nền tảng web scraping cloud, dùng để scrape X/Twitter |
| **JWT HS256** | JSON Web Token ký bằng HMAC-SHA256 |
| **Graceful Degradation** | Hệ thống giảm tính năng thay vì crash khi service phụ (OpenAI, Apify) không khả dụng |
| **CORS** | Cross-Origin Resource Sharing — chính sách bảo mật browser |
| **Rate Limiting** | Giới hạn số request/thời gian để chống DDoS và lạm dụng API |
