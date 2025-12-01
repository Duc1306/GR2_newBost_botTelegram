# Kế hoạch chi tiết dự án Chatbot Tổng Hợp MXH

Ngày cập nhật: 2025-11-07

## 1) Phạm vi & mục tiêu
- Thu thập bài/nhắn từ Telegram và X (nếu có API), có thể mở rộng nguồn khác sau.
- Làm sạch, loại trùng, gán chủ đề.
- Xuất bản lên web dạng trang tin có lọc theo chủ đề/nguồn/thời gian.

## 2) Ràng buộc & pháp lý
- Tuân thủ TOS của Telegram, X. Không scrape trái phép.
- Telegram: dung bot (giới hạn) hoặc user (MTProto) qua Telethon, chỉ lấy từ nơi được phép.
- X: cần API v2 (khả năng trả phí). Nếu không có, khoanh lại phạm vi (ưu tiên Telegram) hoặc dùng nguồn công khai hợp lệ khác.

## 3) Kiến trúc đề xuất (phiên bản đơn giản ổn định)
- Ingestion workers (cron/scheduler): TelegramWorker, XWorker
- Processing pipeline: cleaner → deduper → language detector → topic classifier
- Storage: MongoDB (đã chọn), collections: `posts`, `topics`
- API (FastAPI): /posts, /topics, /stats
- Web UI: Next.js hoặc server-side template (FastAPI+Jinja) cho demo nhanh

Luồng dữ liệu: Source → Ingestion → Normalize → Clean/Dedupe → Classify → Store → API → Web UI

## 4) Schema dữ liệu `Post` (normalized)
```
Post {
  id: string            // id nguồn + hash
  source: "telegram" | "x"
  source_id: string     // id message/tweet
  author: string|null
  text: string
  links: string[]
  media: {type: "photo"|"video"|"gif"|"other", url: string}[]
  lang: string|null
  created_at: datetime
  fetched_at: datetime
  dedupe_key: string     // hash(text+links)
  topics: string[]       // nhãn chủ đề
  score: number          // tùy chọn xếp hạng/độ liên quan
}
```

## 5) Kế hoạch phân kỳ
- P0 (Telegram-only):
  - Đăng ký Telegram API (bot hoặc MTProto user)
  - Ingestion Telegram vào DB
  - Cleaning + Dedupe + Rule-based topics
  - API + Web UI đơn giản
- P1 (Thêm X):
  - Đăng ký X API v2, ingestion tweet
  - Gộp pipeline, thống nhất schema
- P2 (Nâng cao):
  - Model phân loại ML nhẹ, search, stats, alert

## 6) Công nghệ
- Python 3.10+
  - Telethon (Telegram), httpx/requests
  - (Nếu dùng X) tweepy hoặc client v2 chính thức
  - FastAPI, pydantic
  - MongoDB (pymongo) hoặc PostgreSQL (SQLAlchemy)
  - NLP: regex, scikit-learn/fastText (tùy chọn)
- Web UI: Next.js 14 (hoặc FastAPI+Jinja cho bản nhanh)

## 7) Các bước thao tác cụ thể (step-by-step)
1. Tạo credentials:
   - Telegram: tạo ứng dụng (api_id, api_hash) hoặc bot token
   - X: tạo app, lấy Bearer Token/keys (nếu có)
2. Tạo file cấu hình `.env`:
   - TELEGRAM_API_ID, TELEGRAM_API_HASH, TELEGRAM_BOT_TOKEN (hoặc SESSION)
   - X_BEARER_TOKEN (nếu có), DB_URL
3. Thiết kế danh sách nguồn ban đầu:
   - Telegram: list kênh/nhóm public
   - X: list hashtag/tài khoản cần theo dõi
4. Cài DB (local):
   - MongoDB (đơn giản, linh hoạt) hoặc PostgreSQL
5. Cài libs & khởi tạo dự án Python:
   - Tạo `pyproject.toml` hoặc `requirements.txt`
   - Thiết lập cấu trúc thư mục `src/` (đã tạo)
6. Viết ingestion Telegram đầu tiên:
   - Kết nối, đọc message gần đây (ví dụ 100-500 tin), normalize
   - Lưu DB
7. Viết processing cơ bản:
   - Clean text (bỏ URL tracking, khoảng trắng, emoji đặc biệt)
   - Dedupe bằng hash
   - Detect language (langdetect/fasttext lid)
8. Phân loại chủ đề:
   - Bản 1: từ khóa
   - Cấu hình file từ khóa theo chủ đề
9. API (FastAPI):
   - GET /posts?source=&topic=&from=&to=&q=
   - GET /topics
10. Web UI:
    - Trang danh sách, lọc nhanh; trang chi tiết
11. Docker Compose (nếu cần):
    - services: db, api, web
12. Viết tests (pytest):
    - Test cleaner và dedupe
13. Viết tài liệu sử dụng & báo cáo kỹ thuật

## 8) Rủi ro & đối sách
- X API hạn chế: khóa phạm vi P0 vào Telegram; dành phương án thay thế nguồn.
- Rate limit: đặt cron giãn cách, retry/backoff.
- Dữ liệu rác/spam: filter độ dài, blacklist.
- Unicode/emoji: chuẩn hóa NFKC, test tiếng Việt & English.

## 9) Tiêu chí hoàn thành P0
- Ingestion Telegram hoạt động, có dữ liệu trong DB
- API trả danh sách bài với filter
- Web UI hiển thị tin theo chủ đề
- Tối thiểu 1-2 tests pass
