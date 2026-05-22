# Kiến Trúc Hệ Thống — NewsBot (Telegram & X News Aggregator)

> Phiên bản: 1.0  
> Tài liệu cập nhật: 2026-05-11  
> Kho lưu trữ: `Duc1306/GR2_newBost_botTelegram`

---

## Quyết Định Thiết Kế

- **Quyết định 1 — Phân tầng theo chức năng (Layered Architecture):**  
  Backend được tổ chức theo 4 tầng rõ ràng: `ingestion → processing → db → api`. Tầng thu thập dữ liệu không biết về tầng API; tầng xử lý (ML, làm sạch) là các module thuần Python không phụ thuộc vào framework. Điều này giúp dễ test và thay thế từng tầng độc lập.

- **Quyết định 2 — MongoDB làm storage duy nhất:**  
  Toàn bộ dữ liệu (bài viết, kênh, người dùng, cài đặt, chủ đề nóng, thông báo) lưu trong MongoDB. Schema linh hoạt phù hợp với cấu trúc bài viết đa dạng từ nhiều nguồn (Telegram, X/Twitter). Collection `posts` là core; các collection còn lại là dữ liệu hỗ trợ.

- **Quyết định 3 — Pipeline phân loại topic 4 tầng ưu tiên:**  
  Mỗi bài viết được phân loại chủ đề theo thứ tự ưu tiên giảm dần: (1) Category từ `channel.json` (chính xác nhất), (2) URL pattern từ domain báo, (3) ML Classifier (TF-IDF + SVM), (4) Rule-based keywords (fallback). Cách này đạt ~99% bài viết có topic ngay sau khi fetch.

- **Quyết định 4 — Background workers tích hợp trong FastAPI (lifespan):**  
  Thay vì chạy các worker riêng biệt, hệ thống khởi tạo 3 `asyncio.Task` ngay khi API boot thông qua `@asynccontextmanager lifespan`: channel queue worker, channel refresh loop, và hotnews precompute worker. Tất cả được huỷ sạch khi API tắt.

- **Quyết định 5 — JWT Bearer token lưu trong `localStorage` (phù hợp với SPA):**  
  Frontend dùng React SPA với JWT lưu trong `localStorage`. `AuthContext` hydrate token khi reload trang. Tự động redirect về `/login` khi nhận 401. Cơ chế inactivity logout sau 60 phút không hoạt động.

- **Quyết định 6 — AI tùy chọn (graceful degradation):**  
  Toàn bộ tính năng OpenAI (phát hiện hot topic, embedding, tóm tắt kênh) được thiết kế để tắt hoàn toàn nếu `OPENAI_API_KEY` chưa được cấu hình. Hệ thống vẫn hoạt động đầy đủ với ML/rule-based fallback.

- **Quyết định 7 — X/Twitter qua Apify (không cần Twitter API v2):**  
  Do Twitter API v2 tốn phí cao, hệ thống dùng Apify Actor để thu thập tweet. Cooldown 6 giờ giữa các lần fetch tránh tiêu tốn credit. Cùng collection `channel_metadata` lưu cả kênh Telegram và tài khoản X với field `platform`.

---

## Cấu Trúc Thư Mục

```
botTele/                            Thư mục gốc dự án
├── src/                            Backend Python (FastAPI)
│   ├── config.py                   Nạp toàn bộ biến môi trường
│   ├── api/                        FastAPI routers & middleware
│   ├── db/                         MongoDB client wrapper
│   ├── ingestion/                  Thu thập dữ liệu (Telegram, X)
│   ├── models/                     Pydantic data models
│   └── processing/                 Xử lý văn bản & ML
├── web/                            Frontend React 18 + Vite + MUI
│   └── src/
│       ├── api.jsx / publicApi.js  HTTP client (Fetch API)
│       ├── context/                AuthContext, ThemeContext
│       ├── components/             UI components dùng lại
│       ├── pages/                  Trang theo vai trò (admin/user/public/auth)
│       └── hooks/                  Custom hooks
├── scripts/                        CLI scripts tiện ích & automation
├── models/                         File model ML đã train (.pkl)
├── docs/                           Tài liệu dự án
├── tests/                          Unit & integration tests (pytest)
├── channel.json                    Danh mục kênh Telegram tĩnh
├── requirements.txt                Python dependencies
└── render.yaml                     Cấu hình deploy Render.com
```

---

## Các File Quan Trọng — Backend

### Tầng Cấu Hình & Khởi Động

| File | Mục đích | Ghi chú |
|---|---|---|
| `src/config.py` | Nạp tất cả biến `.env`: Mongo, Telegram, JWT, OpenAI, CORS, Rate Limit | Singleton module-level |
| `src/api/main.py` | FastAPI app entry point: đăng ký routers, CORS, lifespan workers | Khởi 3 background tasks |
| `src/db/mongo.py` | MongoDB client wrapper: `get_db()`, `get_posts_collection()`, `get_users_collection()` | Lazy init singleton |

### Tầng API (`src/api/`)

| File | Mục đích | Key Interface |
|---|---|---|
| `auth.py` | JWT login/register, bcrypt hash, Bearer token & API Key auth | `login()`, `get_current_user()`, `get_current_admin_user()` |
| `channels.py` | Subscribe/unsubscribe kênh Telegram & X, trigger xử lý ngay | `POST /user/channels/subscribe` |
| `middleware.py` | Rate limiting (SlowAPI), structured logging (Loguru) | `setup_rate_limiting()`, `setup_logging()` |
| `telegram_auth.py` | Xác thực Telegram bằng OTP | `router` (prefix `/auth/telegram`) |
| `main.py` (routes) | Toàn bộ endpoints posts, analytics, hotnews, TTS, admin | Inline trong `main.py` |

### Tầng Thu Thập Dữ Liệu (`src/ingestion/`)

| File | Mục đích | Ghi chú |
|---|---|---|
| `telegram_worker.py` | Thu thập tin nhắn từ kênh Telegram qua Telethon | CLI: `python -m src.ingestion.telegram_worker [--full]` |
| `x_worker.py` | Cào tweet qua Apify Actor | Cooldown 6h/channel |
| `channel_queue_worker.py` | Worker vòng lặp: xử lý `pending_channels`, fetch + tóm tắt AI, cập nhật trạng thái | 3 tasks: queue poller, refresh loop, hotnews warmer |
| `run_scheduled_refresh.py` | Chạy refresh tất cả kênh active theo lịch | Dùng cho cron/scheduler |
| `sources.py` | Lấy danh sách kênh Telegram & X từ collection `channel_metadata` | `get_channels_from_db()`, `get_x_users_from_db()` |

### Tầng Xử Lý (`src/processing/`)

| File | Mục đích | Ghi chú |
|---|---|---|
| `cleaning.py` | Tách link, bỏ emoji, chuẩn hóa khoảng trắng | `clean_text()` → `(text, links)` |
| `lang.py` | Phát hiện ngôn ngữ (langdetect) | `detect_language()` |
| `topic_classifier.py` | Rule-based classifier: keywords tiếng Việt + tiếng Anh cho 19 chủ đề | Fallback cuối |
| `ml_topic_classifier.py` | ML classifier: TF-IDF + LinearSVC, 19 labels | `MLTopicClassifier`, lazy-load từ `models/` |
| `ai_topic_detector.py` | OpenAI GPT-4o-mini: phát hiện hot topic mới, mở rộng keywords, score bằng embedding | Graceful khi không có API key |
| `category_mapper.py` | Map URL slug báo (`/kinh-te/...`) sang tên chủ đề chuẩn | Ground truth từ URL |
| `web_scraper.py` | Crawl nội dung bài báo đầy đủ từ link trong bài viết | `enrich_post_with_article()` |
| `dedupe.py` | Tính `dedupe_key` SHA-256, kiểm tra trùng | Đảm bảo unique trước khi lưu |
| `backfill_topics.py` | Gán lại topic cho bài cũ chưa có topic | Dùng khi train model mới |

### Tầng Models (`src/models/`)

| File | Model | Trường quan trọng |
|---|---|---|
| `post.py` | `Post`, `TopicPrediction`, `MediaItem`, `FullArticle` | `id`, `topics`, `topic_predictions`, `dedupe_key`, `score` |
| `user.py` | `UserInDB`, `UserPublic`, `RegisterRequest` | `role` (`user`/`admin`), `status` (`pending`/`active`/`banned`) |
| `channel.py` | `Channel`, `ChannelSummary`, `ChannelWithSummary` | `status` (`pending`/`active`/`error`) |
| `notification.py` | `Notification`, `NotificationCreate` | `type` (`info`/`success`/`warning`/`error`) |
| `settings.py` | `UserSettings` | `ml_confidence_threshold`, `fetch_frequency_hours` |

---

## Các File Quan Trọng — Frontend

| File / Thư mục | Mục đích | Pattern chính |
|---|---|---|
| `src/index.jsx` | Entry point React, khởi QueryClient + Providers | — |
| `src/App.jsx` | Router chính (React Router v6), lazy-load pages, phân quyền route | `<ProtectedRoute>`, `<AdminRoute>` |
| `src/lib/api.jsx` | HTTP client: `fetchWithAuth()`, tự động xử lý 401, thêm Bearer token | Fetch API wrapper |
| `src/lib/publicApi.js` | HTTP client không cần auth (cho trang public) | — |
| `src/context/AuthContext.jsx` | JWT state: login, logout, inactivity timeout 60p, role decode | `useAuth()` hook |
| `src/context/ThemeContext.jsx` | Dark/Light mode toggle | MUI ThemeProvider |
| `src/hooks/useApi.jsx` | Custom hook gọi API với loading/error state | — |
| `src/pages/auth/LoginPage.jsx` | Form đăng nhập tài khoản thường | — |
| `src/pages/auth/RegisterPage.jsx` | Form đăng ký tài khoản | — |
| `src/pages/public/PublicHomePage.jsx` | Trang xem tin không cần đăng nhập | — |
| `src/pages/admin/OverviewPage.jsx` | Dashboard tổng quan: thống kê, biểu đồ | — |
| `src/pages/admin/PostsPage.jsx` | Quản lý bài viết: filter, gán nhãn, xác minh | — |
| `src/pages/admin/AnalyticsPage.jsx` | Phân tích xu hướng, keyword trends | — |
| `src/pages/admin/TrendingPage.jsx` | Quản lý Hot Topics | — |
| `src/pages/admin/UsersPage.jsx` | Quản lý người dùng: duyệt, ban, đổi role | — |
| `src/pages/admin/SettingsPage.jsx` | Cài đặt hệ thống | — |
| `src/pages/user/DashboardPage.jsx` | Feed cá nhân cho user thường | — |
| `src/components/PostCard.jsx` | Card bài viết: topic badge, media, TTS | — |
| `src/components/FilterSidebar.jsx` | Bộ lọc: topic, ngôn ngữ, khoảng thời gian, nguồn | — |
| `src/components/AudioPlayer.jsx` | Trình phát TTS (Text-to-Speech) | edge-tts backend |
| `src/components/NotificationDropdown.jsx` | Dropdown thông báo realtime | — |
| `src/components/PostDetailModal.jsx` | Modal xem chi tiết bài viết + full article | — |

---

## Database MongoDB — Collection Chính

| Collection | Mục đích | Index chính |
|---|---|---|
| `posts` | Bài viết từ Telegram & X | `id` (unique), `dedupe_key` (unique), `topics`, `created_at` |
| `channels` | Kênh mà user đã subscribe (trạng thái xử lý) | `username`, `status` |
| `pending_channels` | Hàng đợi kênh chờ xử lý | `username`, `attempts` |
| `channel_metadata` | Danh mục tất cả kênh (Telegram + X) trong hệ thống | `platform`, `username`, `is_active` |
| `channel_summaries` | Tóm tắt AI hàng ngày cho từng kênh | `channel_username`, `date` |
| `users` | Tài khoản người dùng | `username` (unique) |
| `hot_topics` | Chủ đề nóng (tay + AI) | `slug` (unique), `priority` |
| `keyword_trends` | Chuỗi thời gian tần suất từ khóa | `keyword`, `date` |
| `notifications` | Thông báo cho người dùng | `user`, `read`, `created_at` |
| `user_settings` | Cài đặt cá nhân của từng user | `username` (unique) |

---

## Luồng Dữ Liệu

### Luồng Thu Thập Telegram (Manual Fetch)

```
CLI / Scheduler
  │── python -m src.ingestion.telegram_worker
  │                    │
  │       sources.py → get_channels_from_db()
  │                    │  (lấy danh sách kênh từ channel_metadata)
  │                    │
  │       TelegramClient (Telethon + StringSession)
  │                    │  iter_messages(channel, limit)
  │                    │
  │       cleaning.clean_text()       ← Bỏ emoji, tách link, chuẩn hóa
  │       lang.detect_language()      ← Phát hiện vi/en/...
  │       web_scraper.enrich_post()   ← Crawl full article nếu có link
  │                    │
  │       ┌────────────▼────────────────────────────────┐
  │       │       Pipeline Phân Loại Topic (4 tầng)     │
  │       │  1. channel.json category (chính xác nhất)  │
  │       │  2. URL slug từ link báo                    │
  │       │  3. ML: TF-IDF + LinearSVC                  │
  │       │  4. Rule-based keywords (fallback)          │
  │       └────────────┬────────────────────────────────┘
  │                    │
  │       dedupe.check() → SHA-256(text+links)
  │                    │
  │       posts_collection.upsert()   ← Lưu MongoDB
```

### Luồng Subscribe Kênh Mới (User Action)

```
React Frontend (DashboardPage)
  │── POST /user/channels/subscribe { channel_link }
  │                                        │
  │                             channels.py router
  │                                        │
  │                             (1) Validate link format
  │                             (2) Upsert vào collection "channels" (status=pending)
  │                             (3) Upsert vào "pending_channels"
  │                             (4) BackgroundTask: _trigger_channel_processing()
  │◄── 201 { channel }                     │
  │                                        │
  │                    ┌───────────────────▼────────────────────┐
  │                    │  channel_queue_worker (background)      │
  │                    │  Poll "pending_channels" mỗi 30 giây   │
  │                    │    → Telethon fetch messages            │
  │                    │    → Process + save posts              │
  │                    │    → OpenAI tóm tắt 24h gần nhất       │
  │                    │    → Update channel status = "active"  │
  │                    └────────────────────────────────────────┘
```

### Luồng Xem Tin Tức (User Read)

```
React Frontend
  │── GET /posts?topic=Crypto&lang=vi&hours=24&page=1
  │                                     │
  │                          FastAPI main.py
  │                                     │  Query MongoDB "posts":
  │                                     │  - Filter: topics, lang, created_at
  │                                     │  - Sort: score DESC, created_at DESC
  │                                     │  - Paginate
  │◄── 200 { posts: [...], total, page }
  │
  │── GET /hotnews?hours=24             │
  │                          ┌──────────▼──────────────────────────┐
  │                          │  In-memory cache (TTL 1-3h)          │
  │                          │  Nếu cache miss:                     │
  │                          │  → Aggregate posts theo từ khóa     │
  │                          │  → OpenAI GPT-4o-mini phân tích     │
  │                          │  → Trả về top trending topics       │
  │                          └─────────────────────────────────────┘
  │◄── 200 { topics: [...] }
```

### Luồng Xác Thực (JWT)

```
Browser (LoginPage)
  │── POST /auth/login { username, password }
  │                            │
  │                  auth.py: verify_password (bcrypt)
  │                            │  users collection lookup
  │                            │  create_access_token() → JWT (HS256, 24h)
  │◄── 200 { access_token, username, role }
  │
  AuthContext: setUser(), localStorage.setItem("auth_token")
  │
  │── Mọi request tiếp theo:
  │   headers: { Authorization: "Bearer <token>" }
  │                            │
  │                  get_current_user() → decode JWT → inject user
  │                  get_current_admin_user() → thêm kiểm tra role="admin"
```

---

## Đồ Thị Phụ Thuộc

```
src/config.py
    ↑ sử dụng bởi tất cả module

src/db/mongo.py          src/models/
    ↑                        ↑
    └──────────┬─────────────┘
               │
   src/ingestion/          src/processing/
   (telegram_worker,   ←── (cleaning, lang, topic_classifier,
    x_worker,               ml_topic_classifier, ai_topic_detector,
    channel_queue_worker)   web_scraper, dedupe)
               │
               ↓
          MongoDB (posts, channels, ...)
               ↑
          src/api/ (FastAPI routers)
               ↑
          web/ (React SPA)
```

---

## Quy Trình Phát Triển Tính Năng Mới

1. **Model dữ liệu** — Định nghĩa Pydantic model trong `src/models/<feature>.py`
2. **Database** — Thêm collection và index trong `scripts/create_indexes.py`
3. **Processing** (nếu cần) — Thêm module xử lý trong `src/processing/`
4. **API endpoint** — Thêm route trong `src/api/main.py` hoặc tạo router mới `src/api/<feature>.py`, đăng ký trong `main.py`
5. **Frontend API client** — Thêm hàm gọi API trong `web/src/lib/api.jsx` hoặc `publicApi.js`
6. **UI Page/Component** — Tạo trong `web/src/pages/<role>/` và component tái sử dụng trong `web/src/components/`
7. **Scripts tiện ích** (nếu cần) — Thêm `.py` + `.cmd` trong `scripts/`
8. **Tests** — Thêm test trong `tests/test_<feature>.py`

---

## Files Cần Sửa Khi Thêm Route Mới

| File | Thay đổi |
|---|---|
| `src/models/<name>.py` | Định nghĩa Pydantic model mới |
| `src/api/<name>.py` | FastAPI router với các endpoint |
| `src/api/main.py` | `app.include_router(router)` |
| `scripts/create_indexes.py` | Index MongoDB cho collection mới |
| `web/src/lib/api.jsx` | Hàm gọi API tương ứng |
| `web/src/pages/<role>/<Page>.jsx` | UI page mới |
| `tests/test_<name>.py` | Unit tests |

---

## Stack Công Nghệ

### Backend
| Công nghệ | Phiên bản | Vai trò |
|---|---|---|
| Python | 3.12 | Ngôn ngữ chính |
| FastAPI | 0.115 | Web framework (async) |
| Uvicorn | 0.30 | ASGI server |
| Pydantic v2 | 2.9 | Validation & serialization |
| PyMongo | 4.8 | MongoDB driver |
| Telethon | 1.34 | Telegram MTProto client |
| Apify Client | ≥1.7 | X/Twitter scraping |
| scikit-learn | 1.5.2 | TF-IDF + LinearSVC |
| OpenAI SDK | ≥1.30 | GPT-4o-mini + embeddings (tùy chọn) |
| python-jose | 3.3 | JWT encode/decode |
| passlib + bcrypt | — | Password hashing |
| SlowAPI | 0.1.9 | Rate limiting |
| Loguru | 0.7.2 | Structured logging |
| BeautifulSoup4 | 4.12 | Web scraping |
| edge-tts | ≥6.1.9 | Text-to-Speech (vi-VN) |

### Frontend
| Công nghệ | Vai trò |
|---|---|
| React 18 | UI framework |
| Vite | Build tool & dev server |
| React Router v6 | Client-side routing |
| MUI (Material UI) | Component library |
| TanStack Query | Server state & caching |
| Fetch API | HTTP client |

### Infrastructure
| Công nghệ | Vai trò |
|---|---|
| MongoDB Atlas | Database (production) |
| Render.com | Backend hosting (Python) |
| Vercel | Frontend hosting (SPA) |

---

## Ghi Chú Bảo Mật

- **JWT** lưu trong `localStorage` — phù hợp SPA, cần HTTPS trên production
- **Mật khẩu** hash bằng bcrypt (`passlib`) trước khi lưu MongoDB — không lưu plaintext
- **Rate limiting** áp dụng toàn bộ API: 60 req/phút, 1000 req/giờ mặc định
- **CORS** whitelist cứng các origin cho phép qua `ALLOWED_ORIGINS` trong `.env`
- **Admin routes** kiểm tra `role="admin"` bằng `get_current_admin_user()` dependency
- **User status** mặc định `"pending"` — admin phải duyệt trước khi user có thể login
- **Input validation** qua Pydantic model ở mọi endpoint (tự động 422 nếu sai schema)
- **`JWT_SECRET_KEY`** phải đổi khỏi giá trị mặc định trên production (Render tự sinh nếu dùng `generateValue: true`)
- **Telegram Session String** cần bảo vệ tuyệt đối — tương đương full quyền tài khoản Telegram
