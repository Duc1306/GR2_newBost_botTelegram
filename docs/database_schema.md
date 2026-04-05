# Cấu Trúc Database MongoDB — `newsbot`

## Tổng quan: 6 Collections

```
newsbot (database)
├── posts              ← Bài viết chính (core)
├── channel_metadata   ← Danh mục kênh Telegram
├── keyword_trends     ← Chuỗi thời gian từ khóa
├── hot_topics         ← Chủ đề nóng
├── notifications      ← Thông báo người dùng
└── user_settings      ← Cài đặt cá nhân
```

---

## 1. Collection `posts` — Bài viết chính

Document schema (từ `src/models/post.py`):

| Field | Kiểu | Mô tả |
|---|---|---|
| `_id` | ObjectId | MongoDB auto-ID |
| `id` | String (**UNIQUE**) | `"platform:source:source_id"` |
| `platform` | `"telegram"` \| `"twitter"` | Nền tảng |
| `source` | String | Username kênh Telegram |
| `source_id` | String | ID bài gốc trên Telegram |
| `author` | String? | Tác giả (nếu có) |
| `text` | String | Nội dung gốc |
| `text_cleaned` | String? | Văn bản đã làm sạch (dùng cho ML) |
| `links` | `[String]` | Danh sách URL trích xuất |
| `media` | `[MediaItem]` | Ảnh/Video đính kèm |
| `lang` | String? | Mã ngôn ngữ (`"vi"`, `"en"`) |
| `created_at` | DateTime | Thời gian đăng (UTC) |
| `fetched_at` | DateTime | Thời gian thu thập |
| `dedupe_key` | String (**UNIQUE**) | SHA-256(text+links)[:32] — chống trùng |
| `topics` | `[String]` | Danh sách chủ đề đã phân loại |
| `topic_predictions` | `[TopicPrediction]` | Dự đoán ML kèm confidence |
| `source_category` | String? | Slug danh mục từ URL báo gốc |
| `source_topic` | String? | Chủ đề ground-truth từ URL |
| `manual_labels` | `[String]` | Nhãn gán thủ công bởi admin |
| `labels_verified` | Boolean | Đã được xác minh chưa |
| `verified_by` | String? | Username người xác minh |
| `verified_at` | DateTime? | Thời điểm xác minh |
| `score` | Float | Điểm liên quan (mặc định 0.0) |
| `full_article` | `FullArticle?` | Bài báo đầy đủ đã crawl |

### Nested Types

```
MediaItem
├── type        String    "photo" | "video" | "gif" | "document" | "other"
├── url         String
└── thumbnail   String?

TopicPrediction
├── topic           String
├── confidence      Float [0.0 – 1.0]
├── model_version   String
├── predicted_at    DateTime
└── method          "ml" | "rule-based" | "manual"

FullArticle
├── title         String
├── content       String
├── author        String?
├── published_at  DateTime?
└── scraped_at    DateTime
```

### Indexes trên `posts`

| Index | Loại | Mục đích |
|---|---|---|
| `id` | UNIQUE | Tra cứu nhanh theo ID |
| `dedupe_key` | UNIQUE | Chống lưu trùng lặp |
| `created_at` DESC | Single | Sort theo thời gian mới nhất |
| `source` | Single | Lọc theo kênh |
| `topics` | Single (Multikey) | Lọc theo chủ đề |
| `(platform, created_at)` | Compound | Lọc nền tảng + sort |
| `(topics, created_at)` | Compound | Trending query |
| `(topic_predictions.topic, created_at)` | Compound | Query ML predictions |
| `(lang, platform)` | Compound | Lọc ngôn ngữ |
| `text_cleaned` | Text index | Full-text search |

---

## 2. Collection `channel_metadata` — Kênh Telegram

Document schema (từ `channel.json` + `src/ingestion/sources.py`):

| Field | Kiểu | Mô tả |
|---|---|---|
| `_id` | ObjectId | MongoDB auto-ID |
| `platform` | `"telegram"` | Nền tảng |
| `username` | String | Username kênh (@username) |
| `link` | String | URL kênh Telegram |
| `category` | String | Danh mục tiếng Anh (vd: `"Auto & Moto"`) |
| `is_active` | Boolean | Kênh có đang hoạt động |
| `source_type` | String | Phân loại nguồn |

**Indexes:** `(username, platform)` UNIQUE; `(is_active, platform)`; `(source_type, platform)`

> **Quan hệ:** liên kết logic với `posts.source` qua `username` — không có foreign key cứng (đặc trưng NoSQL).

---

## 3. Collection `keyword_trends` — Xu hướng từ khóa

Document schema (từ `src/api/main.py` — `GET /analytics/keywords`):

| Field | Kiểu | Mô tả |
|---|---|---|
| `_id` | ObjectId | MongoDB auto-ID |
| `keyword` | String | Từ khóa |
| `date` | DateTime | Ngày ghi nhận |
| `total_count` | Int | Tổng lần xuất hiện |
| `unique_posts` | Int | Số bài chứa từ khóa |
| `platforms` | `{ telegram: Int, twitter: Int }` | Phân bổ theo nền tảng |
| `topics` | `{ topic_name: Int }` | Phân bổ theo chủ đề |
| `trend_velocity` | Float | Tốc độ tăng trưởng (kỳ hiện tại / kỳ trước) |

**Indexes:** `(keyword, date)` UNIQUE; `(date DESC, topic)`; `(trend_velocity DESC, date DESC)`.

> **Lưu ý:** Đây là collection **pre-aggregated** — dữ liệu cần được tính toán riêng bằng script offline, không tự động cập nhật từ `posts`.

---

## 4. Collection `hot_topics` — Chủ đề nóng

Document schema (từ `DEFAULT_HOT_TOPICS` trong `src/api/main.py`, seed qua `POST /admin/hot-topics/seed`):

| Field | Kiểu | Mô tả |
|---|---|---|
| `_id` | ObjectId | MongoDB auto-ID |
| `slug` | String (**UNIQUE**) | Định danh URL-safe (vd: `"crypto"`) |
| `name` | String | Tên hiển thị tiếng Việt |
| `keywords` | `[String]` | Từ khóa liên quan dùng để matching |
| `color` | String | Màu hiển thị (hex, vd: `"#F7931A"`) |
| `priority` | Int | Thứ tự ưu tiên hiển thị |
| `active` | Boolean | Có hiển thị trên frontend không |

**Query chính:** `{ slug: <slug>, active: true }` — dùng khi load danh sách chủ đề nóng cho trang tin tức.

---

## 5. Collection `notifications` — Thông báo

Document schema (từ `src/models/notification.py`):

| Field | Kiểu | Mô tả |
|---|---|---|
| `_id` | ObjectId | MongoDB auto-ID (dùng làm `notification_id`) |
| `user` | String | Username người nhận |
| `type` | `"info"` \| `"success"` \| `"warning"` \| `"error"` | Loại thông báo |
| `title` | String | Tiêu đề |
| `message` | String | Nội dung |
| `link` | String? | Link tài nguyên liên quan |
| `read` | Boolean | Đã đọc chưa (mặc định `false`) |
| `created_at` | DateTime | Thời gian tạo |

> **Quan hệ:** `notifications.user` liên kết logic với username trong JWT — không có bảng `users` cứng.

---

## 6. Collection `user_settings` — Cài đặt người dùng

Document schema (từ `src/models/settings.py`):

| Field | Kiểu | Mặc định | Mô tả |
|---|---|---|---|
| `_id` | ObjectId | — | MongoDB auto-ID |
| `username` | String (**UNIQUE**) | — | Username (khóa tra cứu) |
| `theme` | String | `"light"` | `"light"` hoặc `"dark"` |
| `notifications_enabled` | Boolean | `true` | Bật/tắt thông báo |
| `email_notifications` | Boolean | `false` | Thông báo qua email |
| `telegram_enabled` | Boolean | `true` | Hiển thị nguồn Telegram |
| `twitter_enabled` | Boolean | `true` | Hiển thị nguồn Twitter |
| `fetch_frequency_hours` | Int | `6` | Tần suất lấy tin (giờ) |
| `ml_auto_classify` | Boolean | `true` | Tự động phân loại bằng ML |
| `ml_confidence_threshold` | Float | `0.5` | Ngưỡng confidence tối thiểu |
| `default_date_range_days` | Int | `7` | Phạm vi ngày mặc định |
| `posts_per_page` | Int | `20` | Số bài/trang |

> **Tạo tự động** khi user đăng nhập lần đầu gọi `GET /settings` (upsert với giá trị mặc định).

---

## Quan Hệ Giữa Các Collections

```
channel_metadata
┌─────────────────┐
│  username       │──────────────────────────────┐
│  category       │                              │ logic join
└─────────────────┘                              ▼
                                         ┌──────────────────┐
                                         │      posts       │
hot_topics                               │  source          │ ← từ channel_metadata.username
┌─────────────┐    slug filter           │  topics[]        │ ← từ channel_metadata.category
│  slug       │ ◄──────────────────────  │  dedupe_key      │ (UNIQUE — chống trùng)
│  keywords   │                          │  full_article    │ ← từ web_scraper
│  active     │                          └──────────────────┘
└─────────────┘                                  │
                                                 │ offline aggregation
                                                 ▼
keyword_trends                           ┌──────────────────┐
┌─────────────┐                          │  keyword_trends  │
│  keyword    │ ◄───── computed from     │  keyword         │
│  date       │        posts.text        │  date            │
│  velocity   │                          │  total_count     │
└─────────────┘                          └──────────────────┘

notifications                        user_settings
┌─────────────┐                      ┌──────────────┐
│  user  ─────┼─────────────────────►│  username    │
│  type       │   username join       │  theme       │
│  read       │   (via JWT)           │  ml_*        │
└─────────────┘                      └──────────────┘
```

---

## Các Điểm Thiết Kế Quan Trọng

### 1. Không có Collection `users`
Hệ thống **không lưu user trong database**. Thông tin đăng nhập được hardcode trong `src/config.py`:
- `admin / admin123` (quyền admin)
- `user / user123` (quyền user thường)

Authentication dùng **JWT stateless** — username và role được encode trực tiếp vào token.

### 2. Deduplication bằng SHA-256
`dedupe_key = SHA-256(text + sorted_links)[:32]` được tạo **trước khi insert**, sau đó dùng `upsert` với điều kiện `dedupe_key`. Không cần query DB để kiểm tra trùng — hiệu quả hơn so với `find_one()` trước rồi insert.

### 3. Phân loại chủ đề nhiều tầng
`posts.topics[]` được điền bởi pipeline 4 tầng ưu tiên:
1. `channel_metadata.category` (độ tin cậy cao nhất)
2. URL path extraction từ link bài báo
3. ML TF-IDF + LinearSVC (`topic_predictions`)
4. Rule-based keyword matching (fallback)

### 4. Multikey Index trên `topics`
Vì `topics` là mảng, MongoDB tự tạo **Multikey Index** — cho phép query `{ topics: "Crypto" }` cực nhanh dù một post có nhiều topic.

### 5. `keyword_trends` là Pre-aggregated
Collection này không tự cập nhật — cần chạy script offline để tổng hợp từ `posts`. Đây là trade-off giữa **tốc độ đọc** (nhanh) và **độ tươi dữ liệu** (không real-time).
