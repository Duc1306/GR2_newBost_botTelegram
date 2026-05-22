# Cấu Trúc Database MongoDB — `newsbot`

## Tổng quan: 11 Collections

```
newsbot (database)
├── posts              ← Bài viết chính (core)
├── users              ← Tài khoản người dùng
├── user_channels      ← Kênh đã subscribe (per user)
├── user_settings      ← Cài đặt cá nhân
├── pending_channels   ← Hàng đợi kênh chờ xử lý
├── notifications      ← Thông báo người dùng
├── sources            ← Danh mục nguồn kênh
├── keyword_trends     ← Chuỗi thời gian từ khóa
├── topic_stats        ← Thống kê chủ đề hàng ngày
├── hotnews_v2_cache   ← Cache cụm tin nóng (TTL 3 ngày)
└── ml_model_versions  ← Lịch sử phiên bản model ML
```

> **Lưu ý:** Ngoài 11 collections trên, code còn sử dụng thêm 2 collection cache phụ:
> `hotnews_summary_cache` (tóm tắt AI cho từng cụm, TTL 30 phút) và
> `hotnews_audio_cache` (TTS audio, TTL 2 giờ).

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
| `geo` | String? | Vùng địa lý phân loại: `"Việt Nam"`, `"Mỹ"`, `"Trung Quốc"`, `"Nga"`, `"Nhật Bản"`, `"Hàn Quốc"`, `"Châu Âu"`, `"Trung Đông"`, `"Đông Nam Á"`, `"Toàn cầu"` |
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
| `geo` | Single | Lọc theo vùng địa lý |
| `text_cleaned` | Text index | Full-text search |

---

## 2. Collection `users` — Tài khoản người dùng

Document schema (từ `src/models/user.py`):

| Field | Kiểu | Mô tả |
|---|---|---|
| `_id` | ObjectId | MongoDB auto-ID |
| `username` | String (**UNIQUE**) | Tên đăng nhập |
| `password_hash` | String | bcrypt hash mật khẩu |
| `role` | `"user"` \| `"admin"` | Phân quyền |
| `status` | `"pending"` \| `"active"` \| `"banned"` | Trạng thái tài khoản |
| `email` | String? | Email người dùng |
| `full_name` | String? | Họ tên đầy đủ |
| `phone_number` | String? | Số điện thoại |
| `telegram_username` | String? | Username Telegram |
| `telegram_session` | String? | Telethon session string (sau OTP login) |
| `telegram_user_id` | Int? | Telegram user ID |
| `created_at` | DateTime | Thời gian đăng ký |
| `last_login` | DateTime? | Lần đăng nhập cuối |

**Indexes:** `username` UNIQUE; `phone_number`; `email`; `telegram_user_id`

> Admin phải approve user mới (status `"pending"` → `"active"`) trước khi đăng nhập được.

---

## 3. Collection `user_channels` — Kênh đã subscribe

Document schema (từ `src/api/channels.py` — `_subscribe_one()`):

| Field | Kiểu | Mô tả |
|---|---|---|
| `_id` | ObjectId | MongoDB auto-ID |
| `user_id` | String | `str(users._id)` của người subscribe |
| `channel_username` | String | Username kênh |
| `channel_link` | String | URL đầy đủ kênh |
| `subscribed_at` | DateTime | Thời gian subscribe |

**Indexes:** `(user_id, channel_username)` UNIQUE

> Mỗi document = 1 user subscribe 1 kênh. Xóa document = unsubscribe.

---

## 4. Collection `sources` — Danh mục nguồn kênh

Document schema (từ `scripts/migrate_db_schema.py` — `generate_sources_from_posts()` + `scripts/sync_channel_categories.py`):

| Field | Kiểu | Mô tả |
|---|---|---|
| `_id` | ObjectId | MongoDB auto-ID |
| `username` | String (**UNIQUE** per platform) | Username kênh |
| `platform` | `"telegram"` \| `"twitter"` | Nền tảng |
| `link` | String | URL kênh |
| `category` | String | Danh mục tiếng Anh (vd: `"Auto & Moto"`) |
| `category_vi` | String? | Danh mục tiếng Việt |
| `is_active` | Boolean | Kênh có đang hoạt động |
| `source_type` | String | Phân loại (`"telegram"`, `"x_user"`, `"x_keyword"`) |
| `post_count` | Int | Số bài đã thu thập |
| `created_at` | DateTime | Thời gian thêm vào |
| `updated_at` | DateTime | Lần cập nhật cuối |

**Indexes:** `(username, platform)` UNIQUE; `(is_active, platform)`; `(source_type, platform)`

> Đây là catalog tổng hợp mọi nguồn. Được sync từ `channel.json` qua `scripts/sync_channel_categories.py`.

---

## 5. Collection `keyword_trends` — Xu hướng từ khóa

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

## 6. Collection `hotnews_v2_cache` — Cache tin nóng

Document schema (từ `src/api/routes/hotnews_routes.py` — `_compute_hotnews_clusters()`):

| Field | Kiểu | Mô tả |
|---|---|---|
| `_id` | ObjectId | MongoDB auto-ID |
| `key` | String (**UNIQUE**) | Cache bucket key: `"hotnews_kw:{hours}:{date}{hour}"` |
| `clusters` | `[Cluster]` | Danh sách cụm tin nóng đã tính |
| `created_at` | DateTime | Thời gian tính toán |
| `expires_at` | DateTime | Hết hạn sau 3 ngày (TTL index tự xóa) |

**Cluster object:**
```
{
  slug, name, description, color,
  post_count, posts_with_links,
  latest_at, headline,
  posts: [...],       // tối đa 15 bài
  source: "embedding_cluster" | "ml_velocity",
  first_seen_at
}
```

**Indexes:** `key` UNIQUE; `expires_at` TTL (expireAfterSeconds=0, tự xóa khi quá `expires_at`)

> **2-tầng cache:** L1 = in-memory `_hotnews_mem` (TTL 1–3h); L2 = MongoDB `hotnews_v2_cache` (TTL 3 ngày). Stale-while-revalidate pattern.

---

## 7. Collection `topic_stats` — Thống kê chủ đề hàng ngày

Document schema (từ `scripts/aggregate_topic_stats.py`):

| Field | Kiểu | Mô tả |
|---|---|---|
| `_id` | ObjectId | MongoDB auto-ID |
| `topic` | String | Tên chủ đề |
| `date` | DateTime | Ngày tính (00:00:00 UTC) |
| `platform` | `"telegram"` \| `"twitter"` \| `"all"` | Nền tảng |
| `post_count` | Int | Số bài thuộc chủ đề trong ngày |
| `avg_confidence` | Float | Confidence trung bình của ML predictions |
| `avg_score` | Float | Score trung bình |
| `top_keywords` | `[{keyword, count}]` | Top 10 từ khóa |
| `top_sources` | `[{source, count}]` | Top 5 kênh nguồn |
| `trend_score` | Float | Tỉ lệ tăng trưởng so với ngày hôm qua |
| `trend_direction` | `"up"` \| `"down"` \| `"stable"` | Hướng xu hướng |
| `created_at` | DateTime | Thời gian tạo |
| `updated_at` | DateTime | Lần cập nhật cuối |

**Indexes:** `(topic, date, platform)` UNIQUE; `(date DESC, topic)`; `(trend_score DESC, date DESC)`

```bash
# Cập nhật thống kê
scripts\aggregate_topic_stats.cmd --days 7
```

---

## 8. Collection `ml_model_versions` — Phiên bản model ML

Document schema (từ `scripts/migrate_db_schema.py` — `register_current_ml_model()`):

| Field | Kiểu | Mô tả |
|---|---|---|
| `_id` | ObjectId | MongoDB auto-ID |
| `version` | String (**UNIQUE**) | Định danh phiên bản (vd: `"svm_v1.0_20260102"`) |
| `model_type` | String | Loại model (`"svm"`) |
| `accuracy` | Float | Accuracy trên test set |
| `f1_score` | Float | F1-score macro |
| `precision` | Float | Precision |
| `recall` | Float | Recall |
| `training_samples` | Int | Số mẫu dùng để train |
| `topics` | `[String]` | Danh sách 19 chủ đề |
| `is_active` | Boolean | Model đang được dùng (chỉ 1 cái active) |
| `trained_at` | DateTime | Thời gian train |
| `model_path` | String | Đường dẫn file `.pkl` |
| `training_config` | Object | `{test_size, max_features, ngram_range}` |

**Indexes:** `version` UNIQUE; `(is_active, trained_at DESC)`

> Khi train model mới: `is_active=True` trên tất cả model cũ bị set `False` trước khi insert bản mới.

---

## 9. Collection `pending_channels` — Hàng đợi xử lý kênh

Document schema (từ `src/ingestion/channel_queue_worker.py`):

| Field | Kiểu | Mô tả |
|---|---|---|
| `_id` | ObjectId | MongoDB auto-ID |
| `channel_username` | String (**UNIQUE**) | Username kênh đang chờ |
| `channel_link` | String | URL đầy đủ kênh |
| `queued_at` | DateTime | Thời gian vào hàng đợi |
| `attempts` | Int | Số lần đã thử xử lý (mặc định 0) |
| `last_attempt` | DateTime? | Lần thử cuối |
| `next_attempt` | DateTime? | Thử lại sau (retry với backoff 5 phút) |

**Indexes:** `channel_username` UNIQUE

> Worker poll collection này mỗi 30 giây. Sau 3 lần thất bại → xóa khỏi queue, cập nhật `channels.status = "error"`.

---

## 10. Collection `notifications` — Thông báo

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

> **Quan hệ:** `notifications.user` join logic với `users.username` qua username trong JWT.

---

## 11. Collection `user_settings` — Cài đặt người dùng

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
users
┌────────────────┐
│  _id  ──────────────────────────────────────────────────┐
│  username       │──────────────┐                        │
└────────────────┘               │ username join (JWT)    │ user_id join
                                 ▼                        ▼
                     notifications          user_channels
                     user_settings          ┌──────────────────┐
                                            │  user_id         │
                                            │  channel_username │──── join logic
                                            └──────────────────┘          │
                                                                           │
sources                                                                    │
┌─────────────────┐                                                        │
│  username       │◄───────────────────────────────────────────────────────┘
│  category       │──── logic join ───►  posts
└─────────────────┘                    ┌──────────────────┐
                                       │  source          │ ← sources.username
                                       │  topics[]        │ ← sources.category
                                       │  dedupe_key      │ (UNIQUE — chống trùng)
                                       └──────────────────┘
                                                │
                                                │ offline scripts
                               ┌────────────────┴────────────────┐
                               ▼                                 ▼
                    keyword_trends                         topic_stats
                    ┌─────────────┐                        ┌─────────────┐
                    │  keyword    │                        │  topic      │
                    │  date       │                        │  date       │
                    │  velocity   │                        │  trend_score│
                    └─────────────┘                        └─────────────┘

pending_channels                        hotnews_v2_cache
┌────────────────┐                      ┌──────────────────────┐
│ channel_username│ (worker poll 30s)   │  key (bucket)        │
│ attempts       │ → khi done:         │  clusters[]          │
│ next_attempt   │   delete + update   │  expires_at (TTL 3d) │
└────────────────┘   channels.status   └──────────────────────┘
                                          ↑ computed from posts

ml_model_versions
┌────────────────┐
│  version       │
│  is_active     │ ← chỉ 1 model active tại 1 thời điểm
│  accuracy/f1   │
└────────────────┘
```

---

## Các Điểm Thiết Kế Quan Trọng

### 1. Collection `users` lưu trong DB (không hardcode)
User được lưu hoàn toàn trong MongoDB `users` collection. Authentication dùng **JWT stateless** — sau khi verify username+password, server sign token HS256 với role và username. Không có session server-side.

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
