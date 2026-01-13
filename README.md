# 🤖 NewsBot - Multi-Platform News Aggregator

Thu thập, phân loại và hiển thị tin tức từ **Telegram & Twitter** với AI/ML.

**Pipeline:** Telegram/Twitter → Clean → ML Topic Classification → Web UI

**Tech:** Python 3.12, FastAPI, MongoDB, React 18, scikit-learn (TF-IDF + SVM)

**Platforms:** 
- ✅ **Telegram** - Channels & Groups
- ✅ **Twitter** - Users & Hashtags

---

## 📚 Mục Lục

1. [🚀 Quick Start](#-quick-start)
2. [🤖 ML Topic Classification](#-ml-topic-classification)
3. [📂 Project Structure](#-project-structure)
4. [🔧 API Documentation](#-api-documentation)
5. [💾 Database Design](#-database-design)
6. [🐦 Twitter Integration](#-twitter-integration)
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

# Create session (1 lần duy nhất)
python scripts\create_session.py
```

### 2. Thu Thập & Train ML Model

```bash
# Thu thập từ Telegram
scripts\fetch_telegram.cmd          # Quick mode (200 posts)
scripts\fetch_telegram.cmd --full   # Full mode (1000 posts)

# Thu thập từ Twitter (NEW!)
scripts\fetch_twitter.cmd           # Quick mode (100 tweets)
scripts\fetch_twitter.cmd --full    # Full mode (500 tweets)

# Hoặc dùng trực tiếp
python -m src.ingestion.telegram_worker          # Telegram
python -m src.ingestion.twitter_worker           # Twitter

# Train ML topic classifier (từ cả Telegram + Twitter data)
scripts\train_ml_classifier.cmd

# Migrate database schema (1 lần duy nhất)
scripts\migrate_db_schema.cmd

# Generate analytics data
scripts\aggregate_topic_stats.cmd --days 7
scripts\extract_keyword_trends.cmd --days 7
```

### 3. Chạy Ứng Dụng

```bash
# Backend + Frontend
scripts\run_fullstack.cmd
```

- **Backend:** http://localhost:8000 (API docs: /docs)
- **Frontend:** http://localhost:3000

---

## 🤖 ML Topic Classification

### Tính Năng

- **TF-IDF + SVM** baseline classifier
- **10 Topics:** Crypto, Kinh tế, Công nghệ, Chính trị, Thể thao, Giải trí, Sức khỏe, Giáo dục, Du lịch, Ẩm thực
- **Auto-predict:** Mỗi post mới tự động được phân loại
- **Confidence tracking:** Lưu topic với confidence + model version + timestamp
- **Multi-platform:** Hỗ trợ Telegram & Twitter (chuẩn bị sẵn)

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

## 📊 Requirements

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

## 🐦 Twitter Integration

### Tính năng
- ✅ Thu thập tweets từ user accounts (@username)
- ✅ Thu thập tweets từ hashtags (#keyword)
- ✅ Tự động phân loại topic với ML
- ✅ Deduplicate và clean data
- ✅ Enrich với full articles
- ✅ Store vào MongoDB
- ✅ Expose qua REST API

### Cài đặt nhanh

#### 1. Lấy Twitter API Credentials

1. **Đăng ký Twitter Developer Account**
   - Truy cập: https://developer.twitter.com/
   - Chọn "Essential" (Free)
   - Chờ phê duyệt (~5 phút)

2. **Tạo App và lấy Bearer Token**
   - Vào Dashboard → Create Project → Create App
   - Vào "Keys and tokens" → Generate Bearer Token
   - **LƯU TOKEN NGAY** (chỉ hiện 1 lần!)

3. **Thêm vào .env**
```env
TWITTER_BEARER_TOKEN=AAAAAAAAAxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

#### 2. Cấu hình Sources

Thêm vào `.env`:
```env
# @ = theo dõi user, # = theo dõi hashtag
TWITTER_SOURCES=@BBCBreaking;@Reuters;@VNExpress;#technology;#vietnam;#AI
```

**Gợi ý sources hay:**
- Tin tức: `@BBCBreaking;@Reuters;@CNN;@VNExpress`
- Tech: `@TechCrunch;@TheVerge;#startup;#AI`
- Business: `@business;@Forbes;@CNBC`

#### 3. Thu thập dữ liệu

```bash
# Lần đầu: Full mode (500 tweets/source)
scripts\fetch_twitter.cmd --full

# Thường xuyên: Quick mode (100 tweets/source)
scripts\fetch_twitter.cmd
```

#### 4. Xem kết quả

```bash
# Qua API
scripts\run_api.cmd
# http://localhost:8000/posts?platform=twitter

# Qua Web Dashboard
scripts\run_fullstack.cmd
# http://localhost:5173
```

### Twitter Rate Limits

- ✅ 500,000 tweets/month (Essential tier)
- ⚠️ ~16,000 tweets/day
- 🔄 450 requests/15 minutes

**Khuyến nghị:**
- Chạy mỗi 1-2 giờ
- 5-10 sources tối ưu
- Avoid quá nhiều sources (>20)

### Schedule tự động

**Windows Task Scheduler:**
1. Mở Task Scheduler
2. Create Basic Task → Name: `Twitter Bot Fetch`
3. Trigger: Daily, repeat every 1 hour
4. Action: Start program → `C:\Users\84328\botTele\scripts\fetch_twitter.cmd`

**Linux/Mac Cron:**
```bash
crontab -e
# Thêm dòng (chạy mỗi giờ)
0 * * * * cd /path/to/botTele && python -m src.ingestion.twitter_worker
```

### Twitter Troubleshooting

**❌ "401 Unauthorized"**
- Check Bearer Token trong `.env`
- Regenerate token nếu cần

**❌ "Rate limit exceeded"**
- Chờ 15 phút
- Giảm số sources
- Tăng interval

**❌ Không lấy được tweets**
- Check `TWITTER_SOURCES` có được config?
- Sources đúng format (@user hoặc #hashtag)?
- User/hashtag có public không?

---

## 🔧 API Documentation

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
  platform?: "telegram" | "twitter" | "all"  // Default: "all"
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


