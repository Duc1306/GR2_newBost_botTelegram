# 🤖 NewsBot - Telegram News Aggregator

Thu thập, phân loại và hiển thị tin tức từ Telegram với AI/ML.

**Pipeline:** Telegram → Clean → ML Topic Classification → Web UI

**Tech:** Python 3.12, FastAPI, MongoDB, React 18, scikit-learn (TF-IDF + SVM)

---

## 🚀 Quick Start (3 bước)

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
# Thu thập dữ liệu (quick: 200 posts, full: 1000 posts)
scripts\fetch_telegram.cmd          # Quick mode
scripts\fetch_telegram.cmd full     # Full mode
scripts\fetch_telegram.cmd scrape   # With article scraping

# Hoặc dùng trực tiếp
python -m src.ingestion.telegram_worker          # Quick (200 posts)
python -m src.ingestion.telegram_worker --full   # Full (1000 posts)

# Train ML topic classifier
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

**Status:** ✅ Production Ready | **Version:** 2.0 (with ML)


