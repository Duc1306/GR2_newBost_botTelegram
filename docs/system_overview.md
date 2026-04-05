# Tổng Quan Hệ Thống — Nền Tảng Tổng Hợp Tin Tức Tự Động từ Telegram

## 1. Giới Thiệu

Hệ thống là một **nền tảng tổng hợp và phân loại tin tức tự động** từ các kênh Telegram. Hệ thống thu thập bài viết từ nhiều kênh tin tức, tự động phân loại chủ đề bằng mô hình học máy, lưu trữ vào MongoDB và cung cấp giao diện web để đọc tin và phân tích xu hướng.

---

## 2. Stack Công Nghệ

| Tầng | Công nghệ |
|---|---|
| **Thu thập dữ liệu** | Python, Telethon (Telegram MTProto API), asyncio |
| **Xử lý & Phân loại** | scikit-learn (TF-IDF + LinearSVC), langdetect, BeautifulSoup4 |
| **AI tùy chọn** | OpenAI GPT-4o-mini, text-embedding-3-small |
| **Lưu trữ** | MongoDB (pymongo) |
| **API Backend** | FastAPI, Uvicorn, JWT (python-jose), bcrypt (passlib), slowapi |
| **Frontend** | React 18, Vite, MUI (Material UI), React Query, React Router v6 |
| **Logging** | Loguru |

---

## 3. Kiến Trúc Tổng Thể

```
┌─────────────────────────────────────────────────────────────────┐
│                        TELEGRAM API                             │
│                   (MTProto Protocol)                            │
└────────────────────────┬────────────────────────────────────────┘
                         │ Telethon
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│              TẦNG THU THẬP DỮ LIỆU (Ingestion)                  │
│  channel.json → channel_metadata (MongoDB)                      │
│  telegram_worker.py → fetch_channel_messages()                  │
└────────────────────────┬────────────────────────────────────────┘
                         │ raw messages
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│              TẦNG XỬ LÝ (Processing Pipeline)                   │
│  1. Làm sạch văn bản        (cleaning.py)                       │
│  2. Nhận dạng ngôn ngữ      (lang.py)                           │
│  3. Tạo Post + dedupe_key   (models/post.py)                    │
│  4. Phân loại chủ đề        (4-tier cascade)                    │
│  5. Làm giàu nội dung       (web_scraper.py - tuỳ chọn)         │
└────────────────────────┬────────────────────────────────────────┘
                         │ Post objects
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│              TẦNG LƯU TRỮ (MongoDB — newsbot)                   │
│  posts / channel_metadata / keyword_trends                      │
│  hot_topics / notifications / user_settings                     │
└────────────────────────┬────────────────────────────────────────┘
                         │ pymongo
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│              TẦNG API (FastAPI)                                  │
│  JWT Auth + Role-Based Access Control                           │
│  Rate Limiting: 60 req/min, 1000 req/hr                         │
│  REST Endpoints: /posts, /stats, /analytics/*, /topics          │
└────────────────────────┬────────────────────────────────────────┘
                         │ HTTP/JSON
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│              TẦNG GIAO DIỆN (React + Vite)                      │
│  NewsPage (user) — OverviewPage, PostsPage, AnalyticsPage (admin)│
│  AuthContext (JWT) + React Query (cache) + MUI                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## 4. Luồng Xử Lý Chính (End-to-End)

```
channel.json
    │  seed
    ▼
MongoDB: channel_metadata
    │  get_channels_from_db()
    ▼
telegram_worker.py
    │  build_client() → TelegramClient (Telethon)
    │  fetch_channel_messages(client, channel, limit=200)
    ▼
raw Message objects (Telethon)
    │
    ├─── process_message(m, channel_name)
    │         │
    │         ├── 1. clean_text(raw)
    │         │       ├── extract_links()       → (text, [urls])
    │         │       ├── remove_emojis()
    │         │       └── normalize_whitespace()
    │         │
    │         ├── 2. detect_language(text)      → "vi" | "en" | None
    │         │
    │         ├── 3. Post.from_raw(...)
    │         │       └── dedupe_key = SHA-256(text + sorted_links)[:32]
    │         │
    │         └── 4. Topic Classification (4-tier priority)
    │                 │
    │                 ├── P1: channel_metadata.category  (DB lookup)
    │                 ├── P2: URL path extraction         (web_scraper)
    │                 ├── P3: MLTopicClassifier.predict() (TF-IDF + SVM, conf ≥ 0.3)
    │                 └── P4: TopicClassifier keywords    (rule-based, fallback)
    │
    ├─── (tùy chọn) enrich_post_with_article()
    │         └── ArticleScraper.scrape(url) → FullArticle
    │
    └─── save_posts(posts)
              └── upsert by dedupe_key → MongoDB: posts
```

---

## 5. Module Phân Loại Chủ Đề (4-Tier Cascade)

Đây là thành phần cốt lõi của hệ thống. Mỗi bài viết được phân loại qua 4 tầng theo thứ tự ưu tiên giảm dần:

```
┌──────────────────────────────────────────────────────────────┐
│  INPUT: post.text + channel_name                             │
└──────────────────┬───────────────────────────────────────────┘
                   │
                   ▼
    ┌─────────────────────────────────────┐
    │  P1: DB Category Lookup             │  ← Độ tin cậy CAO NHẤT
    │  channel_metadata.category          │
    │  → map_category_to_topic()          │
    └────────────────┬────────────────────┘
                     │ Không tìm thấy
                     ▼
    ┌─────────────────────────────────────┐
    │  P2: URL Path Extraction            │  ← Không tốn HTTP
    │  _extract_category_from_url(link)   │
    │  → _map_category_to_topic()         │
    └────────────────┬────────────────────┘
                     │ Không match
                     ▼
    ┌─────────────────────────────────────┐
    │  P3: ML Classifier                  │  ← TF-IDF + LinearSVC
    │  MLTopicClassifier.predict(text)    │
    │  → (topic, confidence)              │
    │  Chỉ chấp nhận nếu confidence ≥ 0.3 │
    └────────────────┬────────────────────┘
                     │ confidence thấp
                     ▼
    ┌─────────────────────────────────────┐
    │  P4: Rule-Based Keywords            │  ← Fallback cuối cùng
    │  TopicClassifier.classify(text, lang)│
    │  Đối chiếu từ điển song ngữ vi/en   │
    └────────────────┬────────────────────┘
                     │
                     ▼
    ┌─────────────────────────────────────┐
    │  OUTPUT: post.topics = [topic_name] │
    └─────────────────────────────────────┘
```

**14 chủ đề được hỗ trợ:**
Kinh tế · Công nghệ · Crypto · Chính trị · Thế giới · Pháp luật · Ô tô - Xe máy · Khoa học · Thể thao · Giải trí · Sức khỏe · Giáo dục · Du lịch · Ẩm thực

---

## 6. Mô Hình ML (TF-IDF + LinearSVC)

**File:** `src/processing/ml_topic_classifier.py`, model lưu tại `models/topic_classifier_svm.pkl`

```
Văn bản đầu vào
    │
    ▼
TfidfVectorizer
  max_features = 5,000
  ngram_range  = (1, 2)   ← unigram + bigram
  sublinear_tf = True     ← log(tf) thay vì tf

    │
    ▼
LinearSVC
  class_weight = 'balanced'  ← xử lý mất cân bằng nhãn

    │
    ▼
predict()  →  (topic_label, confidence_score)
```

- **Training:** script offline `scripts/train_ml_classifier.py`
- **Đánh giá:** stratified train/test split 80/20, in classification report + confusion matrix
- **Lazy load:** worker chỉ load model 1 lần khi khởi động (singleton)
- **Fallback:** nếu file `.pkl` không tồn tại → tự động dùng rule-based (P4)

---

## 7. Tầng API (FastAPI)

**File:** `src/api/main.py`

### Xác thực & Phân quyền

```
Client Request
    │
    ├── Header: Authorization: Bearer <JWT>
    │       └── decode_access_token() → TokenData(username, role)
    │
    └── Header: X-API-Key: <key>
            └── validate API key

Role:
  admin → toàn quyền (dashboard, analytics, quản lý)
  user  → chỉ đọc tin tức (/news)
```

### Các Endpoint Chính

| Nhóm | Endpoint | Mô tả |
|---|---|---|
| **Auth** | `POST /auth/login` | Đăng nhập, trả JWT + role |
| **Auth** | `GET /auth/me` | Thông tin user hiện tại |
| **Core** | `GET /posts` | Danh sách bài (filter: topic, lang, source, q) |
| **Core** | `GET /posts/{id}` | Chi tiết một bài |
| **Core** | `GET /stats` | Thống kê tổng quan |
| **Core** | `GET /topics` | Danh sách chủ đề + số lượng |
| **Analytics** | `GET /topics/trending` | Chủ đề tăng trưởng (2 kỳ so sánh) |
| **Analytics** | `GET /analytics/keywords` | Tần suất từ khóa theo ngày |
| **Analytics** | `GET /analytics/keywords/trending` | Từ khóa tăng nhanh nhất |
| **Analytics** | `GET /analytics/timeline` | Chuỗi thời gian số bài |
| **Analytics** | `GET /analytics/comparison` | So sánh Telegram vs Twitter |
| **Analytics** | `GET /analytics/heatmap` | Hoạt động theo giờ/ngày trong tuần |
| **Public** | `GET /public/hot-topics` | Chủ đề nóng cho trang tin tức |
| **Settings** | `GET/PUT /settings` | Cài đặt người dùng |
| **Notifications** | `GET /notifications` | Danh sách thông báo |

### Middleware & Bảo Mật

| Thành phần | Cấu hình |
|---|---|
| **Rate Limiting** | 60 req/phút, 1000 req/giờ (theo IP) |
| **CORS** | `localhost:3000`, `localhost:5173`, `localhost:3001` |
| **JWT** | HS256, TTL 24 giờ |
| **Password** | bcrypt (passlib) |
| **Logging** | loguru — file `logs/api.log`, xoay vòng 500MB, giữ 30 ngày |

---

## 8. Tầng Giao Diện (React)

**Thư mục:** `web/src/`

### Phân Quyền Route

```
/login          → GuestOnly (redirect nếu đã đăng nhập)
/news           → AuthRequired (user + admin)
/admin          → AdminRequired (chỉ admin)
/admin/analytics → AdminRequired
/admin/posts    → AdminRequired
/admin/trending → AdminRequired
/admin/settings → AdminRequired
```

### Các Trang Chính

**NewsPage** (`/news`) — Giao diện người dùng thường:
- Ticker breaking news (8 bài mới nhất)
- Chip lọc chủ đề nóng (từ `hot_topics`)
- Tìm kiếm debounce 500ms
- Card bài viết: chip chủ đề, tên kênh, thời gian, tiêu đề bài scraped, link gốc

**OverviewPage** (`/admin`) — Dashboard admin:
- Thống kê tổng: tổng bài, bài có nhãn, phân bổ nguồn
- Cards số liệu nhanh

**AnalyticsPage** (`/admin/analytics`) — Phân tích:
- `TimelineChart` — chuỗi thời gian số bài
- `TopicPieChart` — phân bổ chủ đề (pie chart)
- `KeywordsBarChart` — top từ khóa
- `KeywordCloud` — word cloud

**PostsPage** (`/admin/posts`) — Quản lý bài viết:
- Filter: topic, lang, search (debounce)
- Pagination + tổng số kết quả
- Click card → `PostDetailModal` (nội dung đầy đủ, media, link, topic predictions)

**TrendingPage** (`/admin/trending`) — Xu hướng chủ đề:
- Danh sách chủ đề tăng trưởng với % thay đổi và arrow indicator

### State Management

| Cơ chế | Dùng cho |
|---|---|
| **React Query** | Cache API calls, tự refetch, loading/error state |
| **AuthContext** | JWT token, user info, role — persist localStorage |
| **ThemeContext** | Dark/Light mode toggle |

---

## 9. Sơ Đồ Luồng Dữ Liệu Tổng Thể

```
channel.json ──► MongoDB: channel_metadata
                          │
                    CHANNELS list (username[])
                          │
              Telethon ◄──┘──► Telegram MTProto API
                          │
               raw messages (200/kênh)
                          │
              ┌───────────▼───────────────┐
              │     process_message()     │
              │  1. clean_text()          │
              │  2. detect_language()     │
              │  3. Post.from_raw()       │
              │     dedupe_key (SHA-256)  │
              │  4. Topic (4-tier)        │
              │     P1→P2→P3→P4          │
              └───────────┬───────────────┘
                          │
              (optional) enrich_post_with_article()
              ArticleScraper → bài báo gốc
                          │
              MongoDB: posts (upsert by dedupe_key)
                          │
                    FastAPI REST API
              (JWT HS256 + rate limiting + logging)
                          │
              ┌───────────┴───────────┐
              │                       │
         /news (user)        /admin/* (admin)
         NewsPage            OverviewPage
         - Hot topics        AnalyticsPage
         - Search            PostsPage
         - Feed              TrendingPage
```

---

## 10. Các Điểm Kỹ Thuật Nổi Bật

### 10.1 Chiến Lược Phân Loại Cascade
Phân loại 4 tầng đảm bảo **tối đa hóa độ chính xác** với chi phí tính toán hợp lý:
- Tầng P1 và P2 không tốn CPU (chỉ lookup DB / regex URL)
- Tầng P3 (ML) chỉ chạy khi 2 tầng trên không đủ
- Tầng P4 (keyword) luôn có kết quả → không có bài nào bị bỏ sót hoàn toàn

### 10.2 Deduplication Deterministic
`SHA-256(text + sorted_links)[:32]` là hàm thuần túy (không phụ thuộc thời gian, ID Telegram). Cùng một bài đăng từ nhiều lần fetch → luôn ra cùng key → `upsert` an toàn mà không cần query trước.

### 10.3 Dual Authentication
```
Bearer JWT  → cho người dùng tương tác (web frontend)
X-API-Key   → cho tích hợp bên ngoài (scripts, services)
```
Cả hai đều được xác thực bởi cùng một dependency FastAPI `get_current_user()`.

### 10.4 Tính Năng AI Tùy Chọn
OpenAI GPT-4o-mini được dùng để:
- Phát hiện chủ đề nóng mới (`detect_new_hot_topics()`)
- Mở rộng danh sách từ khóa (`expand_keywords()`)
- Xếp hạng bài viết theo semantic similarity (`score_posts_by_embedding()`)

Tất cả các hàm này đều kiểm tra `OPENAI_API_KEY` trước và **trả về giá trị rỗng/mặc định** nếu không có key — hệ thống hoạt động đầy đủ mà không cần OpenAI.

### 10.5 ML Model Training Offline
```
scripts/train_ml_classifier.py
    │
    ├── Lấy dữ liệu training từ MongoDB (posts có labels)
    ├── build_pipeline(): TfidfVectorizer → LinearSVC
    ├── Stratified split 80/20
    ├── In classification report + confusion matrix
    └── Lưu models/topic_classifier_svm.pkl
```
Worker lazy-load model 1 lần khi khởi động. Việc train lại không ảnh hưởng đến uptime của API.
