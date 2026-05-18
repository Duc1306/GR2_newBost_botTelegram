# 🤖 NewsBot - Multi-Source News Aggregator

Thu thập, phân loại và hiển thị tin tức từ **Telegram** và **X (Twitter)** với AI/ML.

**Pipeline:** Telegram / X → Clean → Geo Classify → ML Topic Classification → AI Hot News → Web UI

**Tech:** Python 3.12, FastAPI, MongoDB, React 18, scikit-learn (TF-IDF + SVM), OpenAI GPT-4o-mini, edge-tts

**Platforms:**
- ✅ **Telegram** - Channels & Groups
- ✅ **X (Twitter)** - Accounts & Keywords (via Apify)

---

## 📚 Mục Lục

1. [🚀 Quick Start](#-quick-start)
2. [🔒 Security & Authentication](#-security--authentication)
3. [🤖 ML Topic Classification](#-ml-topic-classification)
4. [🧠 Tính Năng AI Nâng Cao](#-tính-năng-ai-nâng-cao)
5. [📊 Analytics & Báo Cáo](#-analytics--báo-cáo)
6. [📂 Project Structure](#-project-structure)
7. [🔧 API Endpoints](#-api-endpoints)
8. [⚙️ Configuration](#-configuration-env)
9. [🔧 Troubleshooting](#-troubleshooting)
10. [📜 Scripts Reference](#-scripts-reference)
11. [📋 Requirements](#-requirements)
12. [💾 Database Design](#-database-design)

---

## 🚀 Quick Start

### 1. Setup & Cài Đặt

```bash
# Clone & Install
git clone <repo>
cd botTele
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt

# Config .env
MONGO_URI=mongodb://localhost:27017
DB_NAME=newsbot
TELEGRAM_API_ID=your_id
TELEGRAM_API_HASH=your_hash
TELEGRAM_SESSION_STRING=your_session

# Security (IMPORTANT!)
JWT_SECRET_KEY=your-secret-key-change-in-production
ADMIN_USERNAME=admin
ADMIN_PASSWORD=admin123  # CHANGE THIS!

# Create session (1 lần duy nhất)
python scripts\create_session.py

# Test security features
scripts\test_security.cmd
```

### 2. Thu Thập Dữ Liệu (Tự Động Phân Loại Topic)

```bash
# Thu thập từ Telegram với TỰ ĐỘNG phân loại topic
scripts\fetch_telegram.cmd          # Quick mode: 200 posts/kênh
scripts\fetch_telegram.cmd --full   # Full mode: 1000 posts/kênh

# Hoặc dùng trực tiếp Python
python -m src.ingestion.telegram_worker          # Quick mode
python -m src.ingestion.telegram_worker --full   # Full mode
```

**✨ Phân Loại Topic Tự Động (4 Cấp Ưu Tiên):**

Khi fetch dữ liệu, hệ thống TỰ ĐỘNG phân loại topic theo thứ tự:

1. 🎯 **Channel Category** (từ channel.json) - Chính xác nhất
2. 📰 **URL Pattern** (từ domain news site) - Cho bài có link
3. 🤖 **ML Classifier** (TF-IDF + SVM) - Phân tích nội dung text
4. 📋 **Rule-based** (Keywords) - Fallback cuối cùng

**Kết quả:** ~99% posts có topic ngay sau khi fetch!

Để tăng độ chính xác, thêm category cho channels trong [channel.json](channel.json):

```json
{
  "platform": "telegram",
  "username": "channelname",
  "category": "Crypto"  // ← Thêm category
}
```

**Import vào database:**
```bash
python scripts\reclassify_with_channel_categories.py --apply
```

### 2.2. Scripts Quan Trọng

#### 📥 Thu Thập & Quản Lý Kênh

| Script | Mô tả | Sử dụng |
|--------|-------|---------|
| `fetch_telegram.cmd` | Thu thập tin từ Telegram (tự động classify) | `scripts\fetch_telegram.cmd [--full]` |
| `auto_join_channels.cmd` | Tự động join kênh mới từ channel.json | `scripts\auto_join_channels.cmd` |
| `list_channels_from_db.cmd` | Liệt kê channels trong database | `scripts\list_channels_from_db.cmd` |
| `create_session.cmd` | Tạo session Telegram (1 lần duy nhất) | `scripts\create_session.cmd` |

#### 🤖 ML Model & Training

| Script | Mô tả | Sử dụng |
|--------|-------|---------|
| `train_ml_classifier.cmd` | Train ML model từ data | `scripts\train_ml_classifier.cmd` |
| `evaluate_model.cmd` | Đánh giá độ chính xác model | `scripts\evaluate_model.cmd` |
| `auto_retrain.cmd` | Tự động retrain khi có data mới | `scripts\auto_retrain.cmd` |
| `balance_training_data.cmd` | Cân bằng data giữa các topics | `scripts\balance_training_data.cmd` |
| `predict_topics.cmd` | Predict topics cho posts cũ | `scripts\predict_topics.cmd` |

#### 🔧 Bảo Trì Database

| Script | Mô tả | Sử dụng |
|--------|-------|---------|
| `migrate_db_schema.cmd` | Migrate schema (1 lần) | `scripts\migrate_db_schema.cmd` |
| `create_indexes.cmd` | Tạo indexes cho performance | `scripts\create_indexes.cmd` |
| `migrate_env_to_db.cmd` | Import config từ .env vào DB | `scripts\migrate_env_to_db.cmd` |
| `verify_labels.cmd` | Verify tính hợp lệ của labels | `scripts\verify_labels.cmd` |

#### 📊 Analytics & Reports

| Script | Mô tả | Sử dụng |
|--------|-------|---------|
| `aggregate_topic_stats.cmd` | Tạo thống kê topics | `scripts\aggregate_topic_stats.cmd --days 7` |
| `extract_keyword_trends.cmd` | Phân tích từ khóa trending | `scripts\extract_keyword_trends.cmd --days 7` |

#### 🔐 Security & Testing

| Script | Mô tả | Sử dụng |
|--------|-------|---------|
| `test_security.cmd` | Test authentication & rate limiting | `scripts\test_security.cmd` |

#### 🚀 Chạy Ứng Dụng

| Script | Mô tả | Sử dụng |
|--------|-------|---------|
| `run_fullstack.cmd` | Chạy Backend + Frontend cùng lúc | `scripts\run_fullstack.cmd` |
| `run_api.cmd` | Chỉ chạy Backend API | `scripts\run_api.cmd` |

#### ⚠️ Advanced (Chỉ Khi Cần)

| Script | Mô tả | Khi Nào Dùng |
|--------|-------|--------------|
| `reclassify_with_channel_categories.py` | Re-classify toàn bộ posts theo channel category | Khi update channel.json hoặc thêm categories mới |
| `classify_by_content.py` | Classify posts thiếu topics | Khi có posts chưa có topics |
| `fix_misclassified_topics.cmd` | Fix topics bị phân loại sai | Khi phát hiện lỗi phân loại |
| `full_retrain_pipeline.cmd` | Full pipeline: balance → train → evaluate | Khi cần retrain toàn bộ từ đầu |

### 2.3. Chạy Ứng Dụng

```bash
# Backend + Frontend
scripts\run_fullstack.cmd
```

- **Backend:** http://localhost:8000 (API docs: /docs)
- **Frontend:** http://localhost:5173
- **Login:** admin / admin123 (change in production!)

---

## 🔒 Security & Authentication

### Tính Năng Bảo Mật

- ✅ **JWT Authentication** - Token-based auth cho dashboard
- ✅ **API Key Support** - Alternative auth cho external clients
- ✅ **Rate Limiting** - 60 requests/minute, 1000/hour per IP
- ✅ **Structured Logging** - Track all requests & errors with loguru
- ✅ **Frontend Integration** - Login/logout UI với Material-UI

### Quick Test

```bash
# Test all security features
scripts\test_security.cmd
```

**Expected output:**
```
✅ PASS - Authentication
✅ PASS - Logging  
✅ PASS - Rate Limiting
🎉 All security features are working correctly!
```

### Login Credentials (Default)

```
Username: admin
Password: admin123
```

⚠️ **CHANGE IN PRODUCTION!** Edit `.env`:
```bash
ADMIN_USERNAME=your_admin
ADMIN_PASSWORD=StrongPassword123!
JWT_SECRET_KEY=generate-32-char-random-string
```

### API Authentication

**Option 1: JWT Token (Recommended)**
```bash
# 1. Login
curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "admin123"}'

# Response:
# {
#   "access_token": "eyJhbGci...",
#   "token_type": "bearer",
#   "expires_in": 86400,
#   "username": "admin"
# }

# 2. Use token
curl http://localhost:8000/posts \
  -H "Authorization: Bearer eyJhbGci..."
```

**Option 2: API Key**
```bash
# Set in .env
API_KEY=your-secret-api-key-2026

# Use X-API-Key header
curl http://localhost:8000/posts \
  -H "X-API-Key: your-secret-api-key-2026"
```

### Rate Limiting

```python
# Configure in .env
RATE_LIMIT_ENABLED=true
RATE_LIMIT_PER_MINUTE=60   # Max 60 requests/minute
RATE_LIMIT_PER_HOUR=1000   # Max 1000 requests/hour
```

**Response when exceeded:**
```json
HTTP/429 - Too Many Requests
{
  "error": "Rate limit exceeded"
}
```

### Logging

All requests logged to `logs/api.log`:

```
2026-01-13 23:09:02 | INFO | → GET /posts from 127.0.0.1
2026-01-13 23:09:02 | INFO | ← GET /posts status=200 duration=0.124s
2026-01-13 23:09:05 | ERROR | API error: /posts | Unauthorized
```

**View logs:**
```bash
# All logs
tail -f logs/api.log

# Errors only
tail -f logs/api.log | grep ERROR
```

**Full documentation:** [docs/API_SECURITY.md](docs/API_SECURITY.md)

---

## 🤖 ML Topic Classification

### 19 Topics Được Hỗ Trợ

Hệ thống phân loại **19 chủ đề**, đồng bộ hoàn toàn giữa ML classifier, rule-based classifier, và UI:

| # | Topic | Mô tả |
|---|-------|--------|
| 1 | 💰 **Crypto** | Bitcoin, Ethereum, blockchain, DeFi, NFT |
| 2 | 📈 **Kinh tế** | Tài chính, chứng khoán, ngân hàng, thương mại |
| 3 | 💻 **Công nghệ** | AI, smartphone, software, cloud computing |
| 4 | 🏛️ **Chính trị** | Chính phủ, nghị viện, chính sách, bầu cử |
| 5 | 🌍 **Thế giới** | Tin tức quốc tế, quan hệ ngoại giao, xung đột |
| 6 | ⚖️ **Pháp luật** | Tòa án, luật pháp, tội phạm, công an |
| 7 | 🚗 **Ô tô - Xe máy** | Xe hơi, xe điện, thị trường ô tô |
| 8 | 🔬 **Khoa học** | Nghiên cứu khoa học, khám phá, công nghệ mới |
| 9 | ⚽ **Thể thao** | Bóng đá, World Cup, Olympic, thể thao điện tử |
| 10 | 🎬 **Giải trí** | Phim ảnh, âm nhạc, showbiz, celebrity |
| 11 | 💊 **Sức khỏe** | Y tế, dinh dưỡng, fitness, tâm lý |
| 12 | 📚 **Giáo dục** | Đào tạo, học tập, trường học, giáo dục |
| 13 | ✈️ **Du lịch** | Điểm đến, khách sạn, tour, du lịch |
| 14 | 🍜 **Ẩm thực** | Món ăn, nhà hàng, công thức nấu ăn |
| 15 | 💼 **Việc làm** | Tuyển dụng, career, jobs, freelance |
| 16 | 🚀 **Kinh doanh & Khởi nghiệp** | Startup, business, entrepreneur, IPO |
| 17 | 🎮 **Trò chơi & Ứng dụng** | Games, apps, gaming, mobile, esports |
| 18 | 📰 **Tin tức & Truyền thông** | News, media, journalism, broadcasting |
| 19 | 📦 **Khác** | Các chủ đề khác |

### Phương Pháp Phân Loại

**1. URL-based Classification (Ground Truth)**
- Extract category từ URL path: `/kinh-te/`, `/phap-luat/`, `/the-gioi/`
- Domain mapping: `tradingview.com` → Crypto, `bloom.bg` → Kinh tế
- Ưu điểm: Chính xác 100% cho news sites

**2. Rule-based Classification (Keywords)**
- Keyword matching với 300+ từ khóa tiếng Việt + English cho 19 topics
- Scoring system dựa trên frequency + context
- Ưu điểm: Hoạt động với MỌI post

**3. ML Classification (TF-IDF + SVM)**
- Machine learning dựa trên training data
- TF-IDF vectorization + LinearSVC classifier
- **Auto-inject:** Tự bổ sung sample data cho topic thiếu dữ liệu (< 10 samples)
- **Auto-balance:** Tự bật oversample khi imbalance ratio > 10:1
- Accuracy hiện tại: **~98.68%** (balanced, 32k samples)

### Training Model

```bash
# Train thông thường (khuyến nghị - tự động xử lý imbalance)
scripts\train_ml_classifier.cmd
python scripts\train_ml_classifier.py

# Train với nhiều data hơn
python scripts\train_ml_classifier.py --limit 20000

# Train chỉ với verified labels
python scripts\train_ml_classifier.py --verified-only

# Evaluate model
scripts\evaluate_model.cmd
```

**Train script tự động:**
- 💉 Inject sample data khi topic có < 10 mẫu trong DB
- ⚖️ Bật oversample khi imbalance ratio > 10:1
- Không cần thêm flag `--balanced` thủ công

### Model Evaluation Metrics

- ✅ **Overall:** Accuracy, Macro-F1, Weighted-F1, Precision, Recall
- ✅ **Per-Topic:** Precision, Recall, F1-score cho từng topic
- ✅ **Confusion Matrix:** Ma trận nhầm lẫn với labels
- ✅ **JSON Report:** Lưu vào `models/evaluation_report.json`

---

## 🧠 Tính Năng AI Nâng Cao

### 1. Explainable AI — Topic Tooltip

Mỗi topic chip trong **PostDetailModal** hiển thị tooltip giải thích:
- **Phương pháp dự đoán:** ML (SVM), Rule-based, URL, Channel Category
- **Confidence:** % độ chắc chắn của model
- **Nguồn kênh:** Channel gốc của bài post

### 2. AI Summary với Risk Score

Khi AI tóm tắt cụm tin nóng (hot topics), hệ thống GPT trả về:
- 📝 **Summary:** Tóm tắt nội dung
- 😊 **Sentiment:** Tích cực / Trung lập / Tiêu cực
- ⚠️ **Risk Score (1–10):** Mức độ rủi ro / nhạy cảm của thông tin

**Hiển thị badge risk score:**
- 🟢 **Xanh** (1–3): Rủi ro thấp
- 🟡 **Vàng** (4–6): Rủi ro trung bình
- 🔴 **Đỏ** (7–10): Rủi ro cao

Risk score được lưu vào MongoDB collection `channel_summaries`.

### 3. Cấu Hình AI

```env
OPENAI_API_KEY=your_openai_api_key
```

---

## 📊 Analytics & Báo Cáo

### Dashboard Analytics

**AnalyticsPage** cung cấp:
- 📈 **Timeline Chart:** Số lượng bài đăng theo ngày
- 🔑 **Keywords Chart:** Top từ khóa trending
- 📊 **ML Model Evaluation Chart:** Bar chart Accuracy + Macro F1 theo model
- 📤 **Export CSV:** Xuất báo cáo timeline ra file CSV (UTF-8 BOM)

### Export CSV

Nút **Export CSV** trên trang Analytics cho phép tải về file `analytics_<from>_<to>.csv` với dữ liệu:
```
Date,Post Count
2026-05-01,123
2026-05-02,456
...
```

### ML Model Chart

Hiển thị kết quả từ `models/evaluation_report.json` (tạo bằng `scripts\evaluate_model.cmd`).

Cần chạy evaluate trước khi chart hiện dữ liệu:
```bash
scripts\evaluate_model.cmd
```

---

## 📂 Project Structure

```
botTele/
├── src/
│   ├── api/
│   │   ├── main.py                    # FastAPI app + lifespan (khởi động workers)
│   │   ├── auth.py                    # JWT + bcrypt, Google OAuth helpers
│   │   ├── channels.py                # /user/channels/* router
│   │   ├── telegram_auth.py           # /auth/telegram/* (Telegram OTP flow)
│   │   ├── middleware.py              # SlowAPI rate limiting, loguru logging
│   │   └── routes/                    # Tách route theo domain
│   │       ├── auth_routes.py         # /auth/* (login, register, Google, me)
│   │       ├── post_routes.py         # /posts, /topics, /stats, bookmarks
│   │       ├── analytics_routes.py    # /analytics/* (timeline, keywords, heatmap...)
│   │       ├── public_routes.py       # /public/* (no-auth feed, X search, TTS)
│   │       ├── hotnews_routes.py      # /hotnews, /hot-topics/* (AI clusters)
│   │       ├── tts_routes.py          # /public/tts (edge-tts MP3)
│   │       ├── notification_routes.py # /notifications/*
│   │       ├── settings_routes.py     # /settings, change-password
│   │       └── admin_routes.py        # /admin/* (users, ML metrics, X fetch)
│   ├── ingestion/
│   │   ├── telegram_worker.py         # Telegram ingestion + auto classify
│   │   ├── x_worker.py                # Apify X/Twitter ingest
│   │   ├── channel_queue_worker.py    # Background worker + AI summary
│   │   ├── run_scheduled_refresh.py   # Cron one-shot: refresh toàn bộ kênh
│   │   └── sources.py                 # Đọc danh sách nguồn từ MongoDB
│   ├── processing/
│   │   ├── ml_topic_classifier.py     # ML classifier (TF-IDF + LinearSVC), 19 topics
│   │   ├── topic_classifier.py        # Rule-based keyword cascade (4 tầng)
│   │   ├── ai_topic_detector.py       # OpenAI GPT-4o-mini: summary + sentiment + risk_score
│   │   ├── geo_classifier.py          # Phân loại địa lý (10 vùng), rule-based + AI fallback
│   │   ├── backfill_topics.py         # Batch backfill topics & geo cho bài cũ
│   │   ├── category_mapper.py         # Channel category → Vietnamese topic
│   │   ├── web_scraper.py             # Article scraping + URL topic detection
│   │   ├── cleaning.py                # Text cleaning, extract_links()
│   │   ├── dedupe.py                  # SHA-256 deduplication
│   │   └── lang.py                    # Language detection (vi/en)
│   ├── models/
│   │   ├── post.py                    # Post, TopicPrediction, MediaItem, FullArticle
│   │   ├── channel.py                 # Channel, ChannelSummary
│   │   ├── user.py                    # UserInDB, UserPublic, RegisterRequest
│   │   ├── notification.py            # Notification model
│   │   └── settings.py                # UserSettings model
│   ├── db/mongo.py                    # MongoDB singleton client + helpers
│   └── config.py                      # Tất cả env vars, CORS, safety checks
├── web/                               # React 18 + Vite frontend
│   └── src/
│       ├── pages/
│       │   ├── admin/
│       │   │   ├── AnalyticsPage.jsx  # Analytics + ML chart + Export CSV + Heatmap
│       │   │   ├── OverviewPage.jsx   # Tổng quan hệ thống
│       │   │   ├── PostsPage.jsx      # Quản lý bài viết
│       │   │   ├── TrendingPage.jsx   # Xu hướng chủ đề
│       │   │   ├── SettingsPage.jsx   # Cài đặt hệ thống
│       │   │   └── UsersPage.jsx      # Quản lý người dùng (admin)
│       │   ├── user/
│       │   │   └── DashboardPage.jsx  # Dashboard người dùng + kênh đã subscribe
│       │   ├── public/
│       │   │   ├── PublicHomePage.jsx # Trang chủ công khai (4 tab)
│       │   │   └── tabs/
│       │   │       ├── ArticlesTab.jsx  # Danh sách bài viết công khai
│       │   │       ├── HotNewsTab.jsx   # AI Hot News clusters + TTS
│       │   │       ├── StatsTab.jsx     # Thống kê nhanh
│       │   │       └── XSearchTab.jsx   # Tìm kiếm X/Twitter live
│       │   └── auth/
│       │       ├── LoginPage.jsx
│       │       ├── RegisterPage.jsx
│       │       └── TelegramLoginPage.jsx
│       ├── components/
│       │   ├── PostDetailModal.jsx    # Explainable AI topic tooltips
│       │   ├── AudioPlayer.jsx        # TTS audio player
│       │   ├── NotificationDropdown.jsx
│       │   ├── public/                # ArticleCard, HotClusterCard, NewsTicker...
│       │   └── charts/                # TimelineChart, KeywordsBarChart...
│       ├── lib/
│       │   ├── api.jsx                # fetchWithAuth() + auth token
│       │   └── publicApi.js           # Public API calls (no auth)
│       └── theme/colors.jsx           # 19 topic colors
├── scripts/
│   ├── train_ml_classifier.py         # Train (auto-inject + auto-balance)
│   ├── evaluate_model.py              # Evaluate → models/evaluation_report.json
│   ├── auto_retrain.py                # Auto retrain theo lịch
│   ├── predict_topics.py              # Batch predict topics cho posts cũ
│   ├── create_session.py              # Tạo Telegram session
│   ├── create_indexes.py              # Tạo MongoDB indexes
│   └── *.cmd                          # Windows shortcuts
├── tests/                             # pytest: 9 test files
│   ├── test_auth_jwt.py, test_auth_roles.py, test_cleaning.py
│   ├── test_dedupe.py, test_ml_classifier.py, test_post_model.py
│   ├── test_security.py, test_web_scraper.py, test_x_scraper.py
├── models/
│   ├── topic_classifier_svm.pkl       # Trained model (19 topics)
│   └── evaluation_report.json         # Evaluation results (cho ML chart)
├── docs/                              # Documentation
├── .env                               # Environment config
└── requirements.txt                   # Python dependencies
```

---

## 🔧 API Endpoints

### Public (không cần đăng nhập)
```
GET  /                                           # Root info
GET  /health                                     # Health check
GET  /public/posts                               # Bảng tin công khai (filter: topic, lang, geo, platform, date)
GET  /public/x/search?q=keyword                 # Tìm kiếm X/Twitter live (Apify)
POST /public/tts                                 # Text-to-Speech MP3 (vi-VN-HoaiMyNeural)
GET  /hotnews?window_hours=48                    # AI hot news clusters (cached)
GET  /hot-topics                                 # Danh sách hot topics
```

### Auth
```
POST /auth/login                                 # Đăng nhập (username/password)
POST /auth/register                              # Đăng ký tài khoản
POST /auth/google                                # Đăng nhập Google OAuth
POST /auth/logout                                # Đăng xuất
GET  /auth/me                                    # Thông tin user hiện tại
```

### Posts & Analytics (yêu cầu JWT)
```
GET  /posts?topic=Crypto&limit=20&skip=0         # Danh sách bài viết
GET  /posts/count                                # Đếm bài viết
GET  /topics                                     # Danh sách chủ đề + count
GET  /topics/trending?days=7                     # Chủ đề đang nổi
GET  /stats                                      # Thống kê tổng quan
GET  /analytics/timeline?date_from=...           # Timeline chart
GET  /analytics/keywords?limit=20               # Top từ khóa
GET  /analytics/keywords/trending               # Từ khóa tăng tốc
GET  /analytics/comparison                      # So sánh platform/topic
GET  /analytics/heatmap                         # Heatmap ngày/giờ
```

### User & Settings
```
GET  /user/channels                              # Kênh đã subscribe
POST /user/channels/subscribe                    # Subscribe kênh
DEL  /user/channels/{username}                   # Unsubscribe
GET  /settings                                   # Cài đặt người dùng
PUT  /settings                                   # Cập nhật cài đặt
POST /settings/change-password                  # Đổi mật khẩu
GET  /notifications                              # Danh sách thông báo
POST /notifications/{id}/read                   # Đánh dấu đã đọc
POST /notifications/mark-all-read              # Đánh dấu tất cả đã đọc
```

### Telegram Auth
```
POST /auth/telegram/send-code                   # Gửi OTP
POST /auth/telegram/verify                      # Xác minh OTP → JWT
POST /auth/telegram/verify-2fa                  # Xác minh 2FA
```

### Admin (yêu cầu role=admin)
```
GET  /admin/ml-metrics                           # Evaluation report ML model
POST /admin/x/fetch                              # Kích hoạt cào X theo từ khóa
POST /admin/hot-topics/seed                      # Seed hot topics mặc định
GET  /admin/hot-topics                           # Danh sách hot topics (admin)
PUT  /admin/hot-topics/{slug}                    # Cập nhật hot topic
GET  /admin/users                                # Danh sách users
PUT  /admin/users/{username}/role                # Đổi role
PUT  /admin/users/{username}/status              # Đổi status

GET  /docs                                       # Swagger UI
```

---

## ⚙️ Configuration (.env)

```env
# MongoDB
MONGO_URI=mongodb://localhost:27017
DB_NAME=newsbot

# Telegram
TELEGRAM_API_ID=your_api_id
TELEGRAM_API_HASH=your_api_hash
TELEGRAM_SESSION_STRING=your_session_string
TELEGRAM_CHANNELS=channel1;channel2;channel3
TELEGRAM_FETCH_LIMIT=200

# Web
REACT_APP_API_URL=http://localhost:8000
```

---

## 🔧 Troubleshooting

**Web báo "Failed to fetch"?**
```bash
taskkill /F /FI "WINDOWTITLE eq *Backend*"
scripts\run_api.cmd
```

**Không có posts?**
```bash
python -m src.ingestion.telegram_worker --full
```

**AnalyticsPage lỗi "Cannot access before initialization"?**
- Đã fix: `timelineData` phải khai báo trước `handleExportCSV` trong AnalyticsPage.jsx

**ML model accuracy thấp?**
```bash
# Retrain với nhiều data hơn
python scripts\train_ml_classifier.py --limit 20000
```

**ML chart trên Analytics không hiện?**
```bash
# Cần chạy evaluate để tạo evaluation_report.json
scripts\evaluate_model.cmd
```

**Warning "ML model not found"?**
```bash
# Train model lần đầu (tự động inject sample + balance)
python scripts\train_ml_classifier.py
```

**Topic mới không được predict?**
- Nếu topic không có data trong DB, script tự inject sample rồi oversample — chạy lại train là đủ.

---

## 📜 Scripts Reference

### 🤖 ML Training & Evaluation

```bash
# Train model (tự inject sample + balance nếu cần)
scripts\train_ml_classifier.cmd
python scripts\train_ml_classifier.py

# Evaluate model → tạo evaluation_report.json
scripts\evaluate_model.cmd
python scripts\evaluate_model.py

# Auto retrain theo lịch
scripts\auto_retrain.cmd
python scripts\auto_retrain.py --force
```

### 📊 Analytics & Stats

```bash
# Topic statistics
scripts\aggregate_topic_stats.cmd --days 7

# Keyword trends
scripts\extract_keyword_trends.cmd --days 7

# Predict topics cho posts mới
scripts\predict_topics.cmd
```

### 🔧 Maintenance

```bash
# Database migration (1 lần duy nhất)
scripts\migrate_db_schema.cmd

# Create indexes
scripts\create_indexes.cmd

# Balance training data
scripts\balance_training_data.cmd

# Verify labels
scripts\verify_labels.cmd --limit 50
```

### 🌐 Data Collection

```bash
# Telegram
scripts\fetch_telegram.cmd          # Quick (200 posts)
scripts\fetch_telegram.cmd --full   # Full (1000 posts)
```

### 🚀 Application

```bash
# Full stack
scripts\run_fullstack.cmd

# API only
scripts\run_api.cmd
```

---

## 📋 Requirements

- Python 3.12+
- MongoDB (local or Atlas)
- Node.js 18+ (for frontend)
- Telegram API credentials (get from https://my.telegram.org/apps)

---

## 💾 Database Design

Database: **MongoDB `newsbot`** — 7 collections.

### Collections Schema

#### 1. **posts** - Main collection

```javascript
{
  _id: ObjectId("..."),
  id: "telegram:channel_username:3195",   // UNIQUE
  platform: "telegram" | "twitter",
  source: "channel_username",
  source_id: "3195",
  author: "@username",
  text: "Original raw text...",
  text_cleaned: "Cleaned text...",
  lang: "vi" | "en" | null,
  links: ["https://..."],
  media: [{type: "photo", url: "..."}],
  created_at: ISODate("..."),
  fetched_at: ISODate("..."),
  dedupe_key: "sha256_hash[:32]",         // UNIQUE — chống trùng
  topics: ["Crypto", "Kinh tế"],
  topic_predictions: [
    {
      topic: "Crypto",
      confidence: 0.95,
      model_version: "svm_v1.0_20260102",
      predicted_at: ISODate("..."),
      method: "ml" | "rule-based" | "manual"
    }
  ],
  source_category: "crypto",             // Slug category từ URL báo gốc
  source_topic: "Crypto",                // Ground truth từ URL
  manual_labels: ["Crypto"],
  labels_verified: false,
  geo: "Việt Nam" | "Mỹ" | "Trung Quốc" | "Nga" | "Nhật Bản"
       | "Hàn Quốc" | "Châu Âu" | "Trung Đông" | "Đông Nam Á"
       | "Toàn cầu" | null,              // Phân loại địa lý (mới)
  score: 0.0,
  full_article: {                         // Bài báo gốc đã crawl (tuỳ chọn)
    title, content, author, published_at, scraped_at
  }
}
```

#### 2. **channel_metadata** - Kênh Telegram

```javascript
{
  platform: "telegram",
  username: "channel_username",
  link: "https://t.me/channel_username",
  category: "Auto & Moto",               // Category tiếng Anh
  is_active: true,
  source_type: "channel"
}
```

#### 3. **hot_topics** - Chủ đề nóng

```javascript
{
  slug: "crypto",                        // UNIQUE, URL-safe
  name: "💰 Crypto",
  description: "Bitcoin, Ethereum...",
  keywords: ["bitcoin", "ethereum"],
  color: "#F7931A",
  priority: 1,
  active: true
}
```

#### 4. **keyword_trends** - Xu hướng từ khóa (pre-aggregated)

```javascript
{
  keyword: "bitcoin",
  date: ISODate("..."),
  total_count: 690,
  unique_posts: 456,
  platforms: {telegram: 500, twitter: 190},
  topics: {"Crypto": 567, "Kinh tế": 123},
  trend_velocity: 2.5
}
```

#### 5. **notifications** - Thông báo người dùng

```javascript
{
  user: "username",
  type: "info" | "success" | "warning" | "error",
  title: "Tiêu đề",
  message: "Nội dung",
  link: "https://...",
  read: false,
  created_at: ISODate("...")
}
```

#### 6. **user_settings** - Cài đặt người dùng

```javascript
{
  username: "admin",
  // các preference của user
}
```

#### 7. **channels** - Kênh đã subscribe (per user)

```javascript
{
  username: "user",
  channel: "channel_username",
  platform: "telegram",
  status: "active",
  subscribed_at: ISODate("...")
}
```

### Key Indexes

```javascript
// Unique constraints
posts: id (UNIQUE)
posts: dedupe_key (UNIQUE)
channel_metadata: (username, platform) UNIQUE
hot_topics: slug UNIQUE

// Query optimization
posts: (platform, created_at)
posts: (topics, created_at)
posts: (topic_predictions.topic, created_at)
posts: (lang, platform)
posts: text_cleaned TEXT (full-text search)
```

### Database Migration

Chạy migration 1 lần:
```bash
scripts\migrate_db_schema.cmd
```

### Backfill topics & geo cho bài cũ

```bash
# Xem trước số bài thiếu topics/geo
python -m src.processing.backfill_topics --count

# Backfill đầy đủ (rule-based + OpenAI fallback + geo)
python -m src.processing.backfill_topics

# Chỉ backfill geo
python -m src.processing.backfill_topics --geo-only

# Giới hạn số bài
python -m src.processing.backfill_topics --limit 500
```

### Generate Analytics Data

```bash
# Topic statistics (7 days)
scripts\aggregate_topic_stats.cmd --days 7

# Keyword trends (7 days)
scripts\extract_keyword_trends.cmd --days 7
```

---

**Status:** ✅ Production Ready | **Version:** 2.0.0 (ML + AI + Geo + Public API + X Search)

