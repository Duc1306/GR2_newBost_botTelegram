# 🤖 NewsBot - Telegram News Aggregator

Thu thập, phân loại và hiển thị tin tức từ **Telegram** với AI/ML.

**Pipeline:** Telegram → Clean → ML Topic Classification → Web UI

**Tech:** Python 3.12, FastAPI, MongoDB, React 18, scikit-learn (TF-IDF + SVM)

**Platforms:** 
- ✅ **Telegram** - Channels & Groups

---

## 📚 Mục Lục

1. [🚀 Quick Start](#-quick-start)
2. [🔒 Security & Authentication](#-security--authentication)
3. [🤖 ML Topic Classification](#-ml-topic-classification)
4. [📂 Project Structure](#-project-structure)
5. [🔧 API Documentation](#-api-documentation)
6. [💾 Database Design](#-database-design)
7. [⚠️ Troubleshooting](#-troubleshooting)
8. [📊 Requirements](#-requirements)

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

### 2.1. Quản Lý Channel Categories

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

### 14 Topics Được Hỗ Trợ

Hệ thống phân loại **19 chủ đề** bao gồm các lĩnh vực chính:

1. 💰 **Crypto** - Bitcoin, Ethereum, blockchain, DeFi, NFT
2. 📈 **Kinh tế** - Tài chính, chứng khoán, ngân hàng, thương mại
3. 💻 **Công nghệ** - AI, smartphone, software, cloud computing
4. 🏛️ **Chính trị** - Chính phủ, nghị viện, chính sách, bầu cử
5. 🌍 **Thế giới** - Tin tức quốc tế, quan hệ ngoại giao, xung đột
6. ⚖️ **Pháp luật** - Tòa án, luật pháp, tội phạm, công an
7. 🚗 **Ô tô - Xe máy** - Xe hơi, xe điện, thị trường ô tô
8. 🔬 **Khoa học** - Nghiên cứu khoa học, khám phá, công nghệ mới
9. ⚽ **Thể thao** - Bóng đá, World Cup, Olympic, thể thao điện tử
10. 🎬 **Giải trí** - Phim ảnh, âm nhạc, showbiz, celebrity
11. 💊 **Sức khỏe** - Y tế, dinh dưỡng, fitness, tâm lý
12. 📚 **Giáo dục** - Đào tạo, học tập, trường học, giáo dục
13. ✈️ **Du lịch** - Điểm đến, khách sạn, tour, du lịch
14. 🍜 **Ẩm thực** - Món ăn, nhà hàng, công thức nấu ăn
15. 💼 **Việc làm** - Tuyển dụng, career, jobs, freelance
16. 🚀 **Kinh doanh & Khởi nghiệp** - Startup, business, entrepreneur
17. 🎮 **Trò chơi & Ứng dụng** - Games, apps, gaming, mobile
18. 📰 **Tin tức & Truyền thông** - News, media, journalism
19. 📦 **Khác** - Các chủ đề khác

**Frontend Support:**
- ✅ 19 màu sắc riêng biệt cho mỗi topic
- ✅ 19 icons Material-UI tương ứng
- ✅ Filter sidebar với tất cả topics
- ✅ Dynamic topic fetching từ API

### Phương Pháp Phân Loại

**1. URL-based Classification (Ground Truth - 10% posts)**
- Extract category từ URL path: `/kinh-te/`, `/phap-luat/`, `/the-gioi/`
- Domain mapping: `tradingview.com` → Crypto, `bloom.bg` → Kinh tế
- Resolve URL shorteners: `ift.tt` → VnExpress, `bloom.bg` → Bloomberg
- **Ưu điểm:** Chính xác 100% cho news sites
- **Nhược điểm:** Chỉ hoạt động với 10% URLs (news sites)

**2. Content-based Classification (AI/Keywords - 99% posts)**
- Keyword matching với 300+ keywords tiếng Việt + English
- Multi-topic detection (1 post có thể có nhiều topics)
- Scoring system dựa trên frequency + context
- **Ưu điểm:** Hoạt động với MỌI post (YouTube, Telegram, GitHub, etc.)
- **Nhược điểm:** Có thể sai với posts ngắn hoặc technical content

**3. ML Classification (TF-IDF + SVM - Fallback)**
- Machine learning dựa trên training data
- TF-IDF vectorization + LinearSVC classifier
- Auto-retrain khi có data mới
- **Ưu điểm:** Học từ patterns, cải thiện theo thời gian
- **Nhược điểm:** Cần training data đủ lớn (≥500 posts per topic)

### Tính Năng

- **Multi-method Classification:** URL → Content → ML (cascade)
- **Auto-predict:** Mỗi post mới tự động được phân loại
- **Confidence tracking:** Lưu topic với confidence + model version + timestamp
- **Data Quality Tiers:**
  1. **Ground Truth** (source_topic từ news sites)
  2. **Manual Labels** (manual_labels từ admin)
  3. **ML Predictions** (topics từ classifier)

### Workflow

```
1. Thu thập data → python -m src.ingestion.telegram_worker --full
2. Train model    → python scripts/train_ml_classifier.py
3. Ingest mới     → python -m src.ingestion.telegram_worker (auto predict)
4. Retrain        → python scripts/auto_retrain.py (khi có data mới)
```

### Commands

```bash
# Train model với data từ DB
scripts\train_ml_classifier.cmd

# Train với sample data (demo only)
scripts\train_ml_classifier.cmd --use-sample-data

# Comprehensive model evaluation (với baseline comparison)
scripts\evaluate_model.cmd

# Evaluate với verified data only
scripts\evaluate_model.cmd --verified-only

# Auto retrain khi có data mới (≥100 posts)
scripts\auto_retrain.cmd

# Force retrain
python scripts\auto_retrain.py --force

# Predict cho posts cũ trong DB
scripts\predict_topics.cmd

# Database migration (1 lần duy nhất)
scripts\migrate_db_schema.cmd

# Generate topic stats (for dashboard)
scripts\aggregate_topic_stats.cmd --days 7

# Extract keyword trends
scripts\extract_keyword_trends.cmd --days 7

# Test model
python -m src.processing.ml_topic_classifier
```

### Model Evaluation & Metrics

**Đánh giá đầy đủ với baseline comparison:**
```bash
# Evaluate all models (Rule-based, Naive Bayes, SVM)
scripts\evaluate_model.cmd

# Evaluate với nhiều data hơn
scripts\evaluate_model.cmd --limit 5000

# Evaluate với test split khác
scripts\evaluate_model.cmd --test-size 0.3
```

**Metrics được báo cáo:**
- ✅ **Overall:** Accuracy, Macro-F1, Weighted-F1, Precision, Recall
- ✅ **Per-Topic:** Precision, Recall, F1-score cho từng topic
- ✅ **Confusion Matrix:** Ma trận nhầm lẫn với labels
- ✅ **Baseline Comparison:** So sánh với Rule-based và Naive Bayes
- ✅ **JSON Report:** Lưu kết quả vào `models/evaluation_report.json`

**Expected output:**
```
=== Overall Metrics ===
Accuracy:          0.7845 (78.45%)
Macro F1-Score:    0.7532
Weighted F1-Score: 0.7823
Macro Precision:   0.7621
Macro Recall:      0.7445

MODEL COMPARISON
Model                     Accuracy     Macro-F1     Weighted-F1
--------------------------------------------------------------------------------
🏆 Main: SVM              0.7845       0.7532       0.7823
   Baseline: Naive Bayes  0.7234       0.6891       0.7156
   Baseline: Rule-Based   0.5678       0.5123       0.5589

📈 Improvement over baseline: +38.1%
```

### Database Schema

**Collections:**
- `posts` - Main posts (với platform, topic_predictions)
- `sources` - Source metadata (channels, groups)
- `topic_stats` - Daily topic statistics (cho trending)
- `keyword_trends` - Daily keyword tracking (cho word cloud)
- `ml_model_versions` - Model version history

**Xem chi tiết:** [docs/database_design.md](docs/database_design.md)

### Khi Nào Retrain?

✅ **CẦN retrain:**
- Có ≥100 posts mới với labels
- Model > 1 tuần
- Thêm channels/sources mới
- Accuracy giảm

❌ **KHÔNG CẦN:**
- Model mới train < 24h
- Không có data mới
- Chỉ predict vài posts

### Performance Tips

- Minimum: 1000 samples (100+/topic)
- Recommended: 5000 samples
- Target accuracy: > 70%
- Retrain frequency: Daily/Weekly (dùng `auto_retrain.py`)

### ⚠️ Về Data Quality & Manual Labeling

**QUAN TRỌNG:** Training data hiện tại được gán nhãn TỰ ĐỘNG (pseudo-labels) - không phải ground truth!

**Để đảm bảo chất lượng model:**

1. **Verify labels thủ công** (tối thiểu 500-1000 samples):
```bash
# Xem thống kê verification
scripts\verify_labels.cmd --stats

# Verify 50 posts
scripts\verify_labels.cmd --limit 50

# Verify với username tracking
scripts\verify_labels.cmd --limit 100 --username john
```

2. **Train với verified data:**
```bash
# Train với chỉ verified labels (KHUYẾN NGHỊ)
python scripts\train_ml_classifier.py --verified-only

# Hoặc train mixed nhưng có warning rõ ràng
python scripts\train_ml_classifier.py
```

3. **Xem chi tiết quy trình:** [docs/LABELING_PROCESS.md](docs/LABELING_PROCESS.md)

**Data Quality Levels:**
- ❌ 100% pseudo-labels: Không đảm bảo accuracy
- ⚠️ 20-50% verified: Chấp nhận được
- ✅ 50-80% verified: Tốt cho production
- ⭐ 100% verified: Tốt nhất (ground truth)

---

## � Project Structure

```
botTele/
├── src/
│   ├── api/main.py                    # FastAPI server
│   ├── ingestion/
│   │   ├── telegram_worker.py         # Telegram ingestion + auto ML predict
│   │   └── sources.py                 # Channel configs
│   ├── processing/
│   │   ├── ml_topic_classifier.py     # ML classifier (TF-IDF + SVM)
│   │   ├── topic_classifier.py        # Rule-based (fallback)
│   │   ├── cleaning.py                # Text cleaning
│   │   ├── dedupe.py                  # Deduplication
│   │   ├── lang.py                    # Language detection
│   │   └── web_scraper.py             # Article scraping
│   ├── models/post.py                 # Data models
│   ├── db/mongo.py                    # MongoDB client
│   └── config.py                      # Configuration
├── web/                               # React frontend
│   ├── src/
│   │   ├── components/                # UI components
│   │   └── lib/api.js                 # API client
│   └── package.json
├── scripts/
│   ├── fetch_telegram.cmd             # Fetch posts (quick/full/scrape modes)
│   ├── train_ml_classifier.py         # Train ML model
│   ├── auto_retrain.py                # Auto retrain logic
│   ├── predict_topics.py              # Batch predictions
│   ├── create_session.py              # Telegram auth
│   ├── create_indexes.py              # MongoDB indexes
│   ├── check_channels.py              # Validate channels
│   ├── run_api.cmd                    # Start backend
│   ├── run_fullstack.cmd              # Start both
│   └── *.cmd                          # Windows shortcuts
├── tests/                             # Unit tests
├── models/                            # Saved ML models
│   └── topic_classifier_svm.pkl       # Trained model (after training)
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

**ML model accuracy thấp?**
```bash
# Thu thập thêm data
python -m src.ingestion.telegram_worker --full

# Retrain với nhiều data hơn
python scripts/train_ml_classifier.py --limit 20000
```

**Warning "ML model not found"?**
```bash
# Train model lần đầu
python scripts/train_ml_classifier.py
```

---

## � Scripts Reference

### 🎯 Classification Scripts (Phân loại tự động)

#### classify_by_content.py ⭐ RECOMMENDED
Phân loại posts dựa trên TEXT CONTENT (success rate ~99%)

```bash
# Dry run - Test trước, không lưu database
python scripts\classify_by_content.py --limit 100

# Apply cho 1000 posts
python scripts\classify_by_content.py --limit 1000 --apply

# Apply cho TẤT CẢ posts
python scripts\classify_by_content.py --apply
```

**Khi nào dùng:**
- ✅ Posts không có URL hoặc URL không phải news (YouTube, Telegram, GitHub)
- ✅ Muốn classify nhanh toàn bộ database
- ✅ Cần success rate cao (~99%)
- ✅ Posts có text content đủ dài (>20 chars)

#### extract_categories_from_urls.py
Extract category từ NEWS URLs (success rate 2-10%)

```bash
# Dry run - Test 500 URLs
python scripts\extract_categories_from_urls.py --limit 500

# Apply và lưu database
python scripts\extract_categories_from_urls.py --limit 5000 --apply
```

**Khi nào dùng:**
- ✅ Posts có URLs từ news sites chính thống (VnExpress, Bloomberg, etc.)
- ✅ Muốn ground truth từ trang báo
- ✅ Override ML predictions với data chính xác hơn

**Best Practice Workflow:**
```bash
# 1. Classify tất cả posts bằng content (nhanh, 99% success)
python scripts\classify_by_content.py --apply

# 2. Override với ground truth từ URLs (chậm, 10% success)
python scripts\extract_categories_from_urls.py --limit 10000 --apply

# 3. Train ML model
python scripts\train_ml_classifier.py --verified-only
```

### 🤖 ML Training & Evaluation

```bash
# Train model
scripts\train_ml_classifier.cmd
python scripts\train_ml_classifier.py --balanced --target-samples 500

# Evaluate model
scripts\evaluate_model.cmd
python scripts\evaluate_model.py --verified-only

# Auto retrain
scripts\auto_retrain.cmd
python scripts\auto_retrain.py --force
```

### 📊 Analytics & Stats

```bash
# Topic statistics
scripts\aggregate_topic_stats.cmd --days 7

# Keyword trends
scripts\extract_keyword_trends.cmd --days 7

# Predict topics
scripts\predict_topics.cmd
```

### 🔧 Maintenance

```bash
# Database migration (1 lần duy nhất)
scripts\migrate_db_schema.cmd

# Create indexes
scripts\create_indexes.cmd

# Check labels
scripts\check_db_labels.cmd

# Balance data
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

# Security test
scripts\test_security.cmd
```

---

## �📊 Requirements

- Python 3.12+
- MongoDB (local or Atlas)
- Node.js 18+ (for frontend)
- Telegram API credentials (get from https://my.telegram.org/apps)

---

## 📝 License & Legal

- MIT License
- Thu thập data phải tuân thủ TOS của platforms
- Chỉ lấy từ public channels có quyền truy cập

---

##  API Documentation

### Base URL
`http://localhost:8000`

### Core Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/posts` | List posts with filters |
| GET | `/posts/{id}` | Get single post details |
| GET | `/posts/count` | Count posts by filter |
| GET | `/topics` | List all topics with counts |
| GET | `/topics/trending` | Trending topics (7 days) |
| GET | `/analytics/keywords` | Top keywords |
| GET | `/analytics/timeline` | Post volume timeline |
| GET | `/analytics/comparison` | Platform comparison |
| GET | `/stats` | General statistics |

### Query Parameters cho `/posts`

```typescript
{
  platform?: "telegram"                      // Default: "telegram"
  topic?: string                             // Filter by topic
  source?: string                            // Specific source
  lang?: "vi" | "en"                         // Language filter
  date_from?: string                         // ISO datetime
  date_to?: string                           // ISO datetime
  has_links?: boolean                        // Only with links
  has_media?: boolean                        // Only with media
  min_confidence?: number                    // ML confidence (0-1)
  limit?: number                             // Default: 20, Max: 100
  skip?: number                              // Pagination offset
  sort?: "created_at" | "score"             // Default: "created_at"
  order?: "asc" | "desc"                     // Default: "desc"
}
```

### Response Example

```json
{
  "data": [
    {
      "id": "telegram:channel:3195",
      "platform": "telegram",
      "source": "telegram:crypto_news",
      "text": "Bitcoin surges to new high...",
      "lang": "en",
      "created_at": "2024-08-07T19:43:14Z",
      "links": ["https://example.com/article"],
      "topics": ["Crypto", "Kinh tế"],
      "topic_predictions": [
        {
          "topic": "Crypto",
          "confidence": 0.95,
          "model_version": "svm_v1.0_20260102",
          "predicted_at": "2026-01-02T05:20:00Z",
          "method": "ml"
        }
      ]
    }
  ],
  "total": 46975,
  "limit": 20,
  "skip": 0,
  "has_more": true
}
```

### API Dashboard Priority

**1. Overview Page:**
- `GET /stats` - Overall statistics
- `GET /topics` - Topic distribution

**2. Main Content:**
- `GET /posts` - Post list with filters
- `GET /topics/trending` - Trending topics

**3. Analytics Page:**
- `GET /analytics/timeline` - Volume chart
- `GET /analytics/keywords` - Word cloud
- `GET /analytics/comparison` - Platform comparison

### Swagger UI

Xem API documentation đầy đủ tại: **http://localhost:8000/docs**

---

## 💾 Database Design

### Collections Schema

#### 1. **posts** - Main collection

```javascript
{
  _id: ObjectId("..."),
  platform: "telegram" | "twitter",
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
  topic_predictions: [
    {
      topic: "Crypto",
      confidence: 0.95,
      model_version: "svm_v1.0_20260102",
      predicted_at: ISODate("..."),
      method: "ml"
    }
  ],
  score: 0.0
}
```

#### 2. **sources** - Source metadata

```javascript
{
  _id: ObjectId("..."),
  platform: "telegram" | "twitter",
  source_type: "channel" | "group" | "user" | "hashtag",
  source_id: "@channel_username",
  name: "Channel Display Name",
  url: "https://...",
  is_active: true,
  post_count: 1234,
  metadata: {...}
}
```

#### 3. **topic_stats** - Daily aggregated statistics

```javascript
{
  topic: "Crypto",
  date: ISODate("2026-01-02T00:00:00Z"),
  platform: "telegram" | "twitter" | "all",
  post_count: 1234,
  avg_confidence: 0.87,
  top_keywords: [{keyword: "bitcoin", count: 456}],
  trend_score: 1.23,
  trend_direction: "up"
}
```

#### 4. **keyword_trends** - Keyword tracking

```javascript
{
  keyword: "bitcoin",
  date: ISODate("..."),
  platforms: {telegram: 456, twitter: 234},
  topics: {"Crypto": 567, "Kinh tế": 123},
  total_count: 690,
  trend_velocity: 2.5
}
```

#### 5. **ml_model_versions** - Model tracking

```javascript
{
  version: "svm_v1.0_20260102",
  model_type: "svm",
  accuracy: 0.9035,
  f1_score: 0.89,
  training_samples: 10000,
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

## ⚠️ Class Imbalance Problem

### Vấn đề phát hiện

Training results cho thấy:
- **90.3% dữ liệu là "Chính trị"** - Mất cân bằng nghiêm trọng
- Accuracy 94.5% nhưng **misleading**
- Các topic khác có **0% recall** (Du lịch, Giải trí, Thể thao...)
- Model không học được gì về topic thiểu số

### Nguyên nhân

1. **Nguồn dữ liệu thiên về Chính trị**
   - 13/15 kênh là tin tức tổng hợp (chủ yếu chính trị)
   
2. **Rule-based classifier có keywords quá rộng**
   - Keywords như 'law', 'policy', 'government' → Bị label nhầm

### Giải pháp

#### ✅ 1. Balance Training Data (Nhanh - 5 phút)

```bash
# Undersample (giảm Chính trị)
scripts\train_ml_classifier.cmd --balanced --method undersample

# Oversample (nhân bản topic thiểu số)
scripts\train_ml_classifier.cmd --balanced --method oversample

# Combined (cân bằng)
scripts\train_ml_classifier.cmd --balanced --method combined
```

**Ưu điểm:**
- ✅ Nhanh, không cần thu thập thêm
- ✅ Model học đều các topic
- ✅ Cải thiện recall cho topic thiểu số

#### ✅ 2. Thêm Nguồn Dữ Liệu Đa Dạng (Tốt nhất)

**Thêm kênh Telegram:**
```env
TELEGRAM_CHANNELS=hanoi24hnews;tuoitre;vietnamnet;dantri;\
bongdavn;thethao247;\
afamily;kenh14;\
dulichvietnam;vntrip;\
world_of_cooking;cookpad;\
vinmec;hellobacsi;\
topdev;itviec
```

**Thêm Twitter sources:**
```env
TWITTER_SOURCES=@BBCBreaking;@Reuters;@TechCrunch;\
@BBCSport;@espn;\
@FoodNetwork;@Tasty;\
@TravelChannel;\
#Technology;#Sport;#Travel;#Food;#Health
```

Thu thập dữ liệu:
```bash
scripts\fetch_telegram.cmd --full
scripts\fetch_twitter.cmd --full
```

#### ✅ 3. Sử dụng Class Weights

Cập nhật `src/processing/ml_topic_classifier.py`:
```python
self.model = LinearSVC(
    C=1.0,
    max_iter=1000,
    random_state=42,
    class_weight='balanced'  # ← Thêm dòng này
)
```

### Kết quả tốt là gì?

```
✅ Label distribution: Cân bằng (mỗi topic 10-30%)
✅ Accuracy: 75-85%
✅ Precision mỗi topic: > 0.60
✅ Recall mỗi topic: > 0.50
✅ F1-score mỗi topic: > 0.55
✅ Không có topic nào 0% recall
```

### Khuyến nghị

| Giải pháp | Thời gian | Hiệu quả | Khuyến nghị |
|-----------|-----------|----------|-------------|
| Balance data | 5 phút | 70% | ⭐⭐⭐ Test ngay |
| Thêm nguồn đa dạng | 10 phút + 24h | 95% | ⭐⭐⭐⭐⭐ Tốt nhất |
| Sửa keywords | 30 phút | 60% | ⭐⭐ Bổ sung |
| Class weights | 2 phút | 50% | ⭐⭐ Bổ sung |

**Kết hợp tất cả cho kết quả tốt nhất!**

---

**Status:** ✅ Production Ready | **Version:** 2.0 (with ML & Twitter)


