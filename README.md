# 🤖 NewsBot - Telegram News Aggregator

Thu thập, phân loại và hiển thị tin tức từ **Telegram** với AI/ML.

**Pipeline:** Telegram → Clean → ML Topic Classification → Risk Scoring → Web UI

**Tech:** Python 3.12, FastAPI, MongoDB, React 18, scikit-learn (TF-IDF + SVM), OpenAI GPT

**Platforms:**
- ✅ **Telegram** - Channels & Groups

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
│   │   ├── main.py                    # FastAPI server (incl. /admin/ml-metrics)
│   │   ├── auth.py                    # JWT authentication
│   │   ├── channels.py                # Channel management API
│   │   └── middleware.py              # Rate limiting, logging
│   ├── ingestion/
│   │   ├── telegram_worker.py         # Telegram ingestion + auto ML predict
│   │   ├── channel_queue_worker.py    # Background worker + AI summary + risk_score
│   │   └── sources.py                 # Channel configs
│   ├── processing/
│   │   ├── ml_topic_classifier.py     # ML classifier (TF-IDF + SVM), 19 topics
│   │   ├── topic_classifier.py        # Rule-based keywords, 19 topics
│   │   ├── ai_topic_detector.py       # OpenAI GPT: summary + sentiment + risk_score
│   │   ├── category_mapper.py         # Channel category → Vietnamese topic
│   │   ├── web_scraper.py             # Article scraping + URL topic detection
│   │   ├── cleaning.py                # Text cleaning
│   │   ├── dedupe.py                  # Deduplication
│   │   └── lang.py                    # Language detection
│   ├── models/
│   │   ├── post.py                    # Post data model
│   │   ├── channel.py                 # Channel data model
│   │   └── settings.py                # Settings model
│   ├── db/mongo.py                    # MongoDB client
│   └── config.py                      # Configuration
├── web/                               # React 18 + Vite frontend
│   └── src/
│       ├── pages/
│       │   ├── admin/
│       │   │   └── AnalyticsPage.jsx  # Analytics + ML chart + Export CSV
│       │   └── public/
│       │       └── PublicHomePage.jsx # Hot news + risk_score badge
│       ├── components/
│       │   └── PostDetailModal.jsx    # Explainable AI topic tooltips
│       └── theme/colors.jsx           # 19 topic colors
├── scripts/
│   ├── train_ml_classifier.py         # Train (auto-inject + auto-balance)
│   ├── evaluate_model.py              # Evaluate → models/evaluation_report.json
│   ├── auto_retrain.py                # Auto retrain logic
│   ├── predict_topics.py              # Batch predictions
│   ├── create_session.py              # Telegram auth
│   ├── create_indexes.py              # MongoDB indexes
│   └── *.cmd                          # Windows shortcuts
├── tests/                             # Unit tests
├── models/
│   ├── topic_classifier_svm.pkl       # Trained model (19 topics)
│   └── evaluation_report.json         # Evaluation results (for ML chart)
├── docs/                              # Documentation
├── .env                               # Environment config
└── requirements.txt                   # Python dependencies
```

---

## 🔧 API Endpoints

```
GET  /posts?topic=Technology&limit=20&skip=0    # Get posts
GET  /topics                                     # List all topics
GET  /stats                                      # Database statistics  
GET  /posts/count?topic=Crypto                  # Count posts
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

### Collections Schema

#### 1. **posts** - Main collection

```javascript
{
  _id: ObjectId("..."),
  platform: "telegram",
  source: "telegram:channel_username",
  source_id: "3195",
  author: "@username",
  text: "Original raw text...",
  text_cleaned: "Cleaned text...",
  lang: "vi" | "en" | null,
  links: ["https://..."],
  media: [{type: "photo", url: "..."}],
  created_at: ISODate("..."),
  fetched_at: ISODate("..."),
  dedupe_key: "hash",
  topics: ["Crypto", "Kinh tế"],
  source_topic: "Crypto",        // Ground truth từ news URL
  topic_predictions: [
    {
      topic: "Crypto",
      confidence: 0.95,
      model_version: "svm_v1.0_20260102",
      predicted_at: ISODate("..."),
      method: "ml" | "rule" | "url" | "channel"
    }
  ],
  score: 0.0
}
```

#### 2. **channel_summaries** - AI summary + risk score

```javascript
{
  channel_id: "telegram:crypto_news",
  summary: "Tóm tắt nội dung cụm tin...",
  sentiment: "positive" | "neutral" | "negative",
  risk_score: 3,                 // 1–10, lưu từ GPT
  topics: ["Crypto"],
  created_at: ISODate("..."),
  updated_at: ISODate("...")
}
```

#### 3. **sources** - Source metadata

```javascript
{
  _id: ObjectId("..."),
  platform: "telegram",
  source_type: "channel" | "group",
  source_id: "@channel_username",
  name: "Channel Display Name",
  url: "https://...",
  is_active: true,
  post_count: 1234,
  metadata: {...}
}
```

#### 4. **topic_stats** - Daily aggregated statistics

```javascript
{
  topic: "Crypto",
  date: ISODate("2026-01-02T00:00:00Z"),
  platform: "telegram" | "all",
  post_count: 1234,
  avg_confidence: 0.87,
  top_keywords: [{keyword: "bitcoin", count: 456}],
  trend_score: 1.23,
  trend_direction: "up"
}
```

#### 5. **keyword_trends** - Keyword tracking

```javascript
{
  keyword: "bitcoin",
  date: ISODate("..."),
  topics: {"Crypto": 567, "Kinh tế": 123},
  total_count: 690,
  trend_velocity: 2.5
}
```

#### 6. **ml_model_versions** - Model tracking

```javascript
{
  version: "svm_v1.0_20260102",
  model_type: "svm",
  accuracy: 0.9868,
  f1_score: 0.99,
  training_samples: 32129,
  topic_count: 19,
  is_active: true,
  trained_at: ISODate("...")
}
```

### Key Indexes

```javascript
// Unique constraints
posts: (platform, source, source_id)
posts: dedupe_key
sources: (platform, source_id)
topic_stats: (topic, date, platform)
keyword_trends: (keyword_normalized, date)

// Query optimization
posts: (platform, created_at)
posts: (topics, created_at)
posts: (topic_predictions.topic, created_at)
posts: text (fulltext search)
```

### Database Migration

Chạy migration 1 lần:
```bash
scripts\migrate_db_schema.cmd
```

### Generate Analytics Data

```bash
# Topic statistics (7 days)
scripts\aggregate_topic_stats.cmd --days 7

# Keyword trends (7 days)
scripts\extract_keyword_trends.cmd --days 7
```

---

**Status:** ✅ Production Ready | **Version:** 3.0 (with ML + AI + 19 Topics)

