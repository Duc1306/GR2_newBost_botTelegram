# 🤖 NewsBot - Tổng hợp Tin tức Telegram

**Mục tiêu:** Thu thập bài viết từ Telegram, làm sạch, phân loại chủ đề và hiển thị trên web.

Lấy tin từ Telegram → Phân loại topics → Scrape full articles → Hiển thị Web

**Tech Stack:** Python 3.12, FastAPI, MongoDB, React 18, Material-UI

---

## 🚀 Khởi động nhanh

### 1. Chạy Backend + Frontend

```cmd
scripts\run_fullstack.cmd
```

- Backend: http://localhost:8000
- Frontend: http://localhost:3000

### 2. Lấy dữ liệu mới (200 posts, ~5 phút)

```cmd
scripts\fetch_telegram.cmd
```

### 3. Lấy dữ liệu đầy đủ (5000 posts, ~30-60 phút)

```cmd
scripts\fetch_telegram_full.cmd
```

---

## 📋 Yêu cầu môi trường

- Python 3.12+
- MongoDB (local hoặc MongoDB Atlas)
- Telegram API credentials (api_id, api_hash từ https://my.telegram.org/apps)
- Node.js 18+ (cho React frontend)

---

## 🔧 Cài đặt & Cấu hình

### 1. Tạo môi trường ảo và cài dependencies

```cmd
python -m venv venv
venv\Scripts\activate.bat
pip install -r requirements.txt
```

### 2. Cấu hình `.env`

```env
MONGO_URI=mongodb://localhost:27017
DB_NAME=newsbot
TELEGRAM_API_ID=your_api_id
TELEGRAM_API_HASH=your_api_hash
TELEGRAM_SESSION_STRING=your_session_string
TELEGRAM_CHANNELS=channel1;channel2;channel3
```

### 3. Tạo session Telegram (chỉ làm một lần)

```cmd
venv\Scripts\activate.bat
python scripts\create_session.py
```

Nhập SĐT + mã OTP, sau đó copy session string vào `.env` dòng `TELEGRAM_SESSION_STRING`.

### 4. Kiểm tra kênh Telegram hợp lệ

```cmd
scripts\check_channels.cmd
```

### 5. Tạo indexes MongoDB

```cmd
python scripts\create_indexes.py
```

### 6. Chạy ingestion Telegram

**Chế độ nhanh (200 tin/kênh - cập nhật hàng ngày):**

```cmd
scripts\fetch_telegram.cmd
```

**Chế độ đầy đủ (5000 tin/kênh - lần đầu hoặc training model):**

```cmd
scripts\fetch_telegram_full.cmd
```

Hoặc chạy trực tiếp:

```cmd
venv\Scripts\activate.bat
python -m src.ingestion.telegram_worker          # chế độ nhanh (200 tin/kênh)
python -m src.ingestion.telegram_worker --full   # chế độ đầy đủ (5000 tin/kênh)
python -m src.ingestion.telegram_worker --full --scrape  # đầy đủ + scraping bài báo đầy đủ
```

**Lưu ý:**
- Chế độ đầy đủ có thể mất 10-30 phút tùy số kênh và lượng tin.
- **Chế độ scraping** sẽ mất nhiều thời gian hơn (1-2 giờ) vì phải tải và phân tích từng bài báo.
- Telegram có rate limit, script sẽ tự động chờ nếu gặp FloodWait.
- Dữ liệu trùng sẽ được cập nhật (upsert) nhờ dedupe_key và id unique.
- Scraper hỗ trợ các nguồn: VnExpress, Baomoi, CafeF, VietStock, CafeBiz, Kenh14, Bloomberg, CoinTelegraph.

### 7. Chạy API server

```cmd
scripts\run_api.cmd
```

Mở http://localhost:8000/docs để xem API docs (Swagger UI).

### 8. Chạy Web Frontend

```cmd
cd web
npm install
npm start
```

Frontend sẽ chạy tại http://localhost:3000

**Cấu hình frontend:**
Tạo file `web/.env`:
```
REACT_APP_API_URL=http://localhost:8000
```

### 9. Chạy tests

```cmd
venv\Scripts\activate.bat
python -m unittest discover tests
```

---

## 🌐 Web Interface

### Features:
- ✅ Dropdown filters (Chủ đề + Ngôn ngữ)
- ✅ Click tiêu đề → mở link gốc
- ✅ Ẩn posts chưa phân loại
- ✅ Search + Pagination
- ✅ React 18 với Material-UI
- ✅ Responsive design

---

## 🎯 Phân loại Topics (10 chủ đề)

| Icon | Topic | Ví dụ |
|------|-------|-------|
| 💰 | Kinh tế | GDP, chứng khoán, VN-Index |
| 💻 | Công nghệ | AI, startup, iPhone |
| ₿ | Crypto | Bitcoin, blockchain |
| 🏛️ | Chính trị | quốc hội, bầu cử |
| ⚽ | Thể thao | World Cup, V-League |
| 🎬 | Giải trí | phim, ca sĩ |
| 🏥 | Sức khỏe | bệnh viện, vaccine |
| 📚 | Giáo dục | đại học, học bổng |
| ✈️ | Du lịch | visa, tour |
| 🍜 | Ẩm thực | nhà hàng, món ngon |

---

## 📁 Cấu trúc Project

```
botTele/
├── src/
│   ├── api/
│   │   └── main.py              # FastAPI backend
│   ├── ingestion/
│   │   ├── telegram_worker.py   # Lấy tin Telegram
│   │   └── sources.py           # Danh sách kênh nguồn
│   ├── processing/
│   │   ├── topic_classifier.py  # Phân loại topics
│   │   ├── web_scraper.py       # Scrape articles
│   │   ├── cleaning.py          # Làm sạch văn bản
│   │   ├── dedupe.py            # Loại trùng
│   │   └── lang.py              # Phát hiện ngôn ngữ
│   ├── models/
│   │   └── post.py              # Data models
│   ├── db/
│   │   └── mongo.py             # MongoDB client
│   └── config.py                # Load cấu hình
├── web/                         # React frontend
│   ├── public/
│   ├── src/
│   │   ├── components/
│   │   │   ├── PostCard.js      # Card hiển thị bài viết
│   │   │   ├── FilterSidebar.js # Sidebar filters
│   │   │   └── Pagination.js    # Pagination component
│   │   ├── lib/
│   │   │   └── api.js           # API client
│   │   ├── App.js               # Main app
│   │   └── index.js             # Entry point
│   └── package.json
├── tests/
│   ├── test_cleaning.py
│   ├── test_dedupe.py
│   └── test_post_model.py
├── scripts/
│   ├── run_fullstack.cmd        # Chạy backend + frontend
│   ├── run_api.cmd              # Chạy API server
│   ├── fetch_telegram.cmd       # Lấy dữ liệu nhanh
│   ├── fetch_telegram_full.cmd  # Lấy dữ liệu đầy đủ
│   ├── create_session.py        # Tạo Telegram session
│   ├── create_indexes.py        # Tạo MongoDB indexes
│   └── check_channels.py        # Kiểm tra kênh Telegram
├── docs/
│   └── plan.md                  # Chi tiết kế hoạch
├── .env                         # Cấu hình môi trường
├── .gitignore                   # Git ignore rules
├── requirements.txt             # Python dependencies
└── README.md
```

---

## 📊 Channels & Links

### Trong database hiện tại:

- **telegram** (Bloomberg): 16,860 posts
  - ✅ **8,003 có links** click được
  - ✅ 6,311 có topics

### ✅ Links hoạt động:

1. **bloom.bg** (Bloomberg) - 1,172 links
   - Click tiêu đề → mở bloomberg.com
2. **tradingview.com** - 70 links
   - Click tiêu đề → mở phân tích

### ❌ Không scrape (blacklist):

- t.me, youtube.com, facebook.com

---

## 📈 Database Stats

```
16,860 posts total
├─ 8,003 có links (47%)
├─ 6,311 có topics (37%)
└─ Domains: bloom.bg (1172), tradingview.com (70)
```

---

## 🔧 Troubleshooting

### Web báo "Failed to fetch"?

```cmd
# Restart backend
taskkill /F /FI "WINDOWTITLE eq *Backend*"
scripts\run_api.cmd
```

### Không có posts?

```cmd
# Lấy posts mới với topics
scripts\fetch_telegram.cmd
```

### Click tiêu đề không mở?

- Posts không có links thì không clickable
- Chỉ Bloomberg/TradingView có links đầy đủ

---

## 📞 API Endpoints

- `GET /posts?topic=Kinh+tế&limit=20` - Lấy danh sách posts
- `GET /topics` - Lấy danh sách topics
- `GET /stats` - Lấy thống kê
- `GET /posts/count` - Đếm số posts
- `GET /docs` - Swagger UI documentation

---

## 🎓 Demo cho Đồ án

1. Chạy `scripts\run_fullstack.cmd`
2. Mở http://localhost:3000
3. Filter: "💰 Kinh tế" hoặc "💻 Công nghệ"
4. Click tiêu đề → Bloomberg/TradingView
5. Search: "Bitcoin", "AI"

---

## 📝 Ghi chú pháp lý

- Việc thu thập dữ liệu phải tuân thủ điều khoản dịch vụ của từng nền tảng.
- Chỉ lấy dữ liệu từ kênh công khai (public) mà bạn có quyền truy cập.
- X (Twitter) API có thể yêu cầu gói trả phí để đọc dữ liệu.

---

## 📌 Tiến độ

Theo dõi trong `docs/plan.md` và file `STATUS.md`.

### Hoàn thành:
- ✅ Thiết lập môi trường, cài dependencies
- ✅ Thiết kế schema dữ liệu `Post`
- ✅ Cleaning & Dedupe utilities
- ✅ Ingestion Telegram
- ✅ Phân loại chủ đề (rule-based)
- ✅ API endpoints (/posts, /topics, /stats)
- ✅ Web UI React với Material-UI

### Đang làm:
- 🚧 Docker Compose
- 🚧 Tối ưu scraper
- 🚧 ML-based topic classification

---

## 🤝 Contributing

Pull requests welcome! Vui lòng tạo issue trước khi làm các thay đổi lớn.

---

**License:** MIT


