# Báo cáo Tiến độ Thực hiện — NewsBot (GR2)

> **Họ tên:** [Điền họ tên]  
> **MSSV:** [Điền MSSV]  
> **Repository:** https://github.com/Duc1306/GR2_newBost_botTelegram  
> **Ngày báo cáo:** tháng 5 năm 2026  
> **Phiên bản:** 2.0.0

---

## Tóm tắt tổng quan

Dự án **NewsBot** là hệ thống tổng hợp tin tức tự động đa nguồn từ **Telegram** và **X (Twitter)**, tích hợp phân loại chủ đề bằng Machine Learning và AI, cung cấp giao diện web trực quan cho người dùng cuối.

| Hạng mục | Trạng thái | Ghi chú |
|---|---|---|
| Backend API | ✅ Hoàn thành | FastAPI 2.0, 40+ endpoints, tách route theo domain |
| Thu thập dữ liệu Telegram | ✅ Hoàn thành | Telethon MTProto, tự động |
| Thu thập dữ liệu X/Twitter | ✅ Hoàn thành | Apify scraping + on-demand admin trigger |
| Phân loại chủ đề (ML) | ✅ Hoàn thành | TF-IDF + LinearSVC, 19 chủ đề |
| Phân loại chủ đề (Rule-based) | ✅ Hoàn thành | Keyword matching vi/en |
| Phân loại địa lý (Geo) | ✅ Hoàn thành | 10 vùng, rule-based + OpenAI fallback |
| Backfill topics & geo | ✅ Hoàn thành | Batch xử lý bài cũ song song |
| Tính năng AI Hot News | ✅ Hoàn thành | GPT-4o-mini, in-memory cache |
| Public API (không auth) | ✅ Hoàn thành | /public/posts, /public/tts, /public/x/search |
| X Live Search | ✅ Hoàn thành | Tìm kiếm X/Twitter real-time qua Apify |
| Xác thực & Phân quyền | ✅ Hoàn thành | JWT + Telegram OTP |
| Giao diện Frontend | ✅ Hoàn thành | React 18 + MUI, 13 trang, 4 public tab |
| Analytics & Thống kê | ✅ Hoàn thành | Timeline, Keywords, Heatmap, Comparison, Trending |
| Text-to-Speech | ✅ Hoàn thành | Tiếng Việt, HoaiMyNeural, rate-limited |
| Triển khai Production | ✅ Hoàn thành | Render + Vercel + MongoDB Atlas |
| Testing | ✅ Hoàn thành | 9 test files, pytest |

---

## I. Hệ thống Thu thập Dữ liệu

### 1.1 Thu thập từ Telegram ✅

**Công nghệ:** Telethon 1.34 (MTProto Protocol)

Hệ thống kết nối trực tiếp vào Telegram bằng tài khoản thật (Session String), không bị giới hạn như Bot API. Tự động fetch bài viết từ các kênh đã đăng ký.

**Tính năng đã làm:**
- Fetch tự động theo lịch (quick mode: 200 bài/kênh, full mode: 1000 bài/kênh)
- Lưu text, link, ngày đăng, media metadata
- Phát hiện ngôn ngữ tự động (tiếng Việt / tiếng Anh)
- Tự động join kênh từ danh sách (`scripts/auto_join_channels.py`)
- Background worker tự động refresh mỗi 12 giờ
- Phân loại địa lý (geo) ngay khi ingest

### 1.2 Thu thập từ X / Twitter ✅

**Công nghệ:** Apify Client ≥1.7 (không cần Twitter API v2)

**Tính năng đã làm:**
- Scrape tweet theo tài khoản cụ thể (`x:username`)
- Scrape theo từ khóa / hashtag (`xkw:bitcoin`)
- Cooldown 6 giờ/nguồn để tiết kiệm Apify credits
- Tự động trigger khi user subscribe kênh mới
- **Admin endpoint** `POST /admin/x/fetch`: kích hoạt cào X theo từ khóa ngay lập tức

### 1.3 Xử lý & Làm sạch dữ liệu ✅

**Tính năng đã làm:**
- Làm sạch text: xóa emoji, chuẩn hóa khoảng trắng
- Tách và lưu riêng các URL trong bài
- Chống trùng lập bằng SHA-256 hash (dedupe_key, module `dedupe.py`)
- Enrich bài viết bằng cách scrape nội dung từ URL đính kèm (BeautifulSoup)
- Phân loại **địa lý** (geo) bằng rule-based + OpenAI fallback (module `geo_classifier.py`)
- **Backfill** hàng loạt bài cũ thiếu topics/geo bằng `src/processing/backfill_topics.py`

---

## II. Pipeline Phân loại Chủ đề (ML)

### 2.1 Phân loại 4 tầng (ưu tiên giảm dần) ✅

**19 chủ đề được phân loại:**
Crypto, Kinh tế, Công nghệ, Chính trị, Thế giới, Pháp luật, Ô tô-Xe máy, Khoa học, Thể thao, Giải trí, Sức khỏe, Giáo dục, Việc làm, Du lịch, Ẩm thực, Kinh doanh & Khởi nghiệp, Trò chơi & Ứng dụng, Tin tức & Truyền thông, Khác.

| Tầng | Phương pháp | Mô tả |
|---|---|---|
| 1 | Channel Category | Category cứng từ `channel.json` — độ chính xác cao nhất |
| 2 | URL Slug | Map URL path từ trang tin sang topic (30+ mappings) |
| 3 | TF-IDF + LinearSVC | ML model được train từ dữ liệu thực tế |
| 4 | Keyword Rules | Từ điển keyword vi/en cho 19 chủ đề (fallback) |

### 2.2 Training ML Model ✅

**Tính năng đã làm:**
- Script train: `scripts/train_ml_classifier.py`
- Script train có class weight (xử lý mất cân bằng dữ liệu): `scripts/train_with_class_weight.py`
- Script cân bằng dữ liệu: `scripts/balance_training_data.py`
- Script đánh giá: `scripts/evaluate_model.py` (accuracy, F1 per topic)
- Script test thủ công: `scripts/predict_topics.py`
- Script sửa label sai hàng loạt: `scripts/fix_misclassified_topics.py`
- Script xác minh label: `scripts/verify_labels.py`
- Model lưu tại: `models/topic_classifier_svm.pkl`

---

## III. Tính năng AI (OpenAI GPT-4o-mini)

### 3.1 Hot News Detection ✅

**Tính năng đã làm:**
- API endpoint: `GET /hotnews?window_hours=24|48|72`
- GPT-4o-mini phân tích xu hướng từ tập bài viết gần đây
- Phát hiện chủ đề đang nổi, tóm tắt nội dung chính
- **Cache in-memory thông minh:** TTL 1h (24h window), 2h (48h), 3h (72h+)
- Worker pre-compute ngay khi khởi động server
- Graceful degradation: hệ thống hoạt động bình thường nếu không có API key

### 3.2 AI Summary cho Kênh ✅

**Tính năng đã làm:**
- Tự động tạo tóm tắt AI cho kênh khi mới subscribe
- Tóm tắt dựa trên bài viết 24 giờ gần nhất
- Lưu vào collection `channel_summaries`
- Hiển thị trên Dashboard người dùng

### 3.3 Phân loại Địa lý (Geo) ✅

**Tình năng:** `src/processing/geo_classifier.py`

**10 vùng địa lý được phân loại:**
Việt Nam, Mỹ, Trung Quốc, Nga, Nhật Bản, Hàn Quốc, Châu Âu, Trung Đông, Đông Nam Á, Toàn cầu.

**Tính năng đã làm:**
- Rule-based: keyword matching (instant, miễn phí)
- OpenAI fallback: gọi GPT khi rule-based không chắc chắn
- Lưu trường `geo` trực tiếp vào document `posts`
- Filter theo geo qua `GET /public/posts?geo=Việt+Nam`

### 3.4 Backfill Hàng loạt ✅

**Tình năng:** `src/processing/backfill_topics.py`

**Tính năng đã làm:**
- Backfill `topics` + `geo` cho bài cũ chưa có field
- Bất đồng bộ (asyncio) với giới hạn 5 OpenAI calls song song (tránh rate-limit)
- Batch ghi DB 200 bài/lần (`bulk_write`)
- Các chế độ: `--count` (xem trước), `--geo-only`, `--ai-only`, `--limit`

---

## IV. Hệ thống Xác thực & Phân quyền

### 4.1 JWT Authentication ✅

**Tính năng đã làm:**
- Đăng ký tài khoản (`POST /auth/register`)
- Đăng nhập bằng username/password (`POST /auth/login`)
- JWT HS256, thời hạn 24 giờ
- Hỗ trợ cả Bearer Token và API Key (`X-API-Key` header)
- Phân quyền 2 cấp: `user` và `admin`

### 4.2 Telegram Phone Login ✅

**Tính năng đã làm:**
- Đăng nhập bằng số điện thoại Telegram (MTProto OTP)
- Luồng 3 bước: gửi mã → xác minh → nhận JWT
- Hỗ trợ 2FA Telegram (nhập mật khẩu bổ sung)
- Session Telethon được lưu vào database, dùng để đọc kênh riêng tư của user

### 4.3 Quản lý Người dùng (Admin) ✅

**Tính năng đã làm:**
- Admin xem danh sách tất cả user
- Admin thay đổi role: `user` ↔ `admin`
- Admin thay đổi status: `active` / `pending` / `banned`
- Trang quản lý user trên giao diện web (`/users`)

---

## V. Quản lý Kênh & Nguồn tin

### 5.1 Subscribe / Unsubscribe Kênh ✅

**Tính năng đã làm:**
- Subscribe 1 kênh: `POST /user/channels/subscribe`
- Subscribe nhiều kênh cùng lúc (bulk): `POST /user/channels/subscribe/bulk`
- Unsubscribe: `DELETE /user/channels/{username}`
- Catalog kênh có sẵn từ `channel.json`
- Trigger xử lý kênh ngay sau khi subscribe (không chờ)

**Hỗ trợ các loại nguồn:**
| Prefix | Ví dụ | Nguồn |
|---|---|---|
| _(không có)_ | `vnexpress_official` | Kênh Telegram |
| `x:` | `x:elonmusk` | Tài khoản X/Twitter |
| `xkw:` | `xkw:bitcoin` | Từ khóa/Hashtag trên X |

### 5.2 Channel Summary & Refresh ✅

- Xem tóm tắt AI và thống kê kênh: `GET /user/channels/{username}/summary`
- Trigger refresh thủ công: `POST /user/channels/{username}/refresh`
- Trạng thái kênh: `pending` → `active` → (refresh mỗi 12h)

### 5.3 Public News Feed ✅

**Endpoint:** `GET /public/posts` (không cần đăng nhập)

**Tính năng đã làm:**
- Bảng tin công khai không yêu cầu JWT
- Filter: `topic`, `lang`, `geo`, `platform`, `date_from`, `date_to`, `link_only`
- Rate limit: 200 req/phút/IP

### 5.4 X Live Search ✅

**Endpoint:** `GET /public/x/search?q=keyword` (không cần đăng nhập)

**Tính năng đã làm:**
- Tìm kiếm X/Twitter real-time qua Apify Actor
- Cache per-keyword 5 phút (tránh gọi Apify lặp lại)
- Flag `live: true` khi kết quả vừa được cào mới
- Frontend tab **X Search** hiển thị kết quả kèm pagination
- Nếu không có Apify token: trả về kết quả từ DB sẵn có

---

## VI. Analytics & Thống kê

### 6.1 Thống kê Tổng quan ✅

**Endpoint:** `GET /stats`  
Hiển thị: tổng số bài, bài đã phân loại, phân bổ theo nguồn, ngôn ngữ, chủ đề, nền tảng, số kênh active.

### 6.2 Trending Topics ✅

**Endpoint:** `GET /topics/trending`  
So sánh nửa đầu vs nửa sau của khoảng thời gian, tính growth %, xác định xu hướng tăng/giảm/ổn định.

### 6.3 Keyword Analytics ✅

**Endpoints:** `GET /analytics/keywords`, `GET /analytics/keywords/trending`  
Thống kê từ khóa phổ biến nhất, trend velocity, phân bổ theo nền tảng và chủ đề.

### 6.4 Timeline ✅

**Endpoint:** `GET /analytics/timeline`  
Số lượng bài theo ngày/tuần, phân tích peak date, trung bình mỗi kỳ.

### 6.5 So sánh Nền tảng ✅

**Endpoint:** `GET /analytics/comparison`  
So sánh Telegram vs X/Twitter: volume, chủ đề nổi bật, tốc độ đăng bài.

### 6.6 Activity Heatmap ✅

**Endpoint:** `GET /analytics/heatmap`  
Bản đồ nhiệt hoạt động: giờ trong ngày × ngày trong tuần.

---

## VII. Giao diện Web (Frontend)

### 7.1 Trang Admin ✅

| Trang | Đường dẫn | Nội dung |
|---|---|---|
| **Overview** | `/overview` | StatCards, Timeline chart, Topic pie chart, Keyword cloud |
| **Analytics** | `/analytics` | Timeline, Keywords bar, Heatmap, Comparison, ML Evaluation chart, Export CSV |
| **Posts** | `/posts` | Bảng danh sách bài viết, filter |
| **Trending** | `/trending` | Top trending topics + keywords |
| **Users** | `/users` | Quản lý tài khoản (chỉ admin) |
| **Settings** | `/settings` | Cài đặt hệ thống |

### 7.2 Trang Người dùng ✅

| Trang | Đường dẫn | Nội dung |
|---|---|---|
| **Dashboard** | `/dashboard` | Kênh đã subscribe, tóm tắt AI, nghè bản tin TTS |

### 7.3 Trang Công khai (không cần đăng nhập) ✅

| Tab | Nội dung |
|---|---|
| **Bài viết** | Filter theo chủ đề, ngôn ngữ, nền tảng, ngày |
| **Tin Nóng (AI)** | Clusters tin nóng GPT-4o-mini + TTS audio |
| **Thống kê** | Quick stats, top topics, post count |
| **Tìm kiếm X** | Tìm kiếm X/Twitter real-time qua Apify |

### 7.4 Trang Xác thực ✅

| Trang | Đường dẫn |
|---|---|
| Đăng nhập | `/login` |
| Đăng ký | `/register` |
| Đăng nhập Telegram | `/telegram-login` |

### 7.4 Tính năng Giao diện ✅

- Dark/Light mode (ThemeContext)
- Lazy loading tất cả các trang (giảm bundle size)
- Inactivity logout sau 60 phút không tương tác
- Route guard: `AuthRequired`, `AdminRequired`
- ErrorBoundary để hiển thị lỗi thay vì blank page
- Responsive design (MUI Grid)
- Tất cả data dùng TanStack Query (staleTime, cache, retry)
- AudioPlayer component cho TTS
- NewsTicker cho PublicHomePage

---

## VIII. Tính năng Text-to-Speech ✅

**Công nghệ:** Microsoft Edge TTS (`edge-tts` ≥6.1.9)  
**Giọng đọc:** `vi-VN-HoaiMyNeural` (tiếng Việt, giọng nữ)

**Tính năng đã làm:**
- Endpoint `POST /public/tts` (không cần JWT) — rate limit 20 req/phút/IP
- Endpoint `GET /user/channels/{slug}/audio` → trả file MP3
- Pre-generate audio ngay sau khi tạo channel summary
- Stream MP3 trực tiếp (`StreamingResponse`)
- Giới hạn 3000 ký tự/lần đọc (public endpoint)
- Nút "Nghe bản tin" trên giao diện Dashboard và HotNewsTab

---

## IX. Hệ thống Thông báo ✅

**Tính năng đã làm:**
- `GET /notifications` — lấy thông báo (lọc unread)
- Lưu trong collection `notifications`
- Phân loại theo user

---

## X. Background Workers (Tự động hóa)

### Worker 1: Channel Queue Poller ✅
- Poll mỗi **30 giây** → xử lý kênh `pending`
- Retry tối đa 3 lần trước khi đánh dấu `error`

### Worker 2: Active Channel Refresher ✅
- Refresh tất cả kênh đang active mỗi **12 giờ**
- Cập nhật bài mới + tạo lại AI summary

### Worker 3: Hot News Cache Warmer ✅
- Pre-compute hot news ngay khi server khởi động
- Refresh định kỳ theo TTL (1h/2h/3h)

---

## XI. Bảo mật ✅

| Tính năng | Triển khai |
|---|---|
| Mã hóa mật khẩu | bcrypt (passlib, rounds=12) |
| JWT HS256 | python-jose, 24h expiry |
| Rate limiting | SlowAPI: 60 req/phút, 1000 req/giờ |
| CORS whitelist | Chỉ cho phép origin đã cấu hình |
| Input validation | Pydantic v2 tại tất cả endpoints |
| Chống SQL/NoSQL injection | MongoDB query builder, không concatenate |

---

## XII. Triển khai Production ✅

| Thành phần | Platform | Trạng thái |
|---|---|---|
| Backend API | Render.com (Web Service) | ✅ Đang chạy |
| Frontend SPA | Vercel | ✅ Đang chạy |
| Database | MongoDB Atlas | ✅ Đang chạy |

---

## XIII. Testing ✅

| File Test | Nội dung kiểm tra |
|---|---|
| `test_auth_jwt.py` | JWT encode/decode, token expiry |
| `test_auth_roles.py` | JWT auth flow, role-based access |
| `test_cleaning.py` | `clean_text()`, `extract_links()`, `remove_emojis()` |
| `test_dedupe.py` | SHA-256 deduplication |
| `test_ml_classifier.py` | MLTopicClassifier predict, load model |
| `test_post_model.py` | Post Pydantic model validation |
| `test_security.py` | Security headers, JWT tampering |
| `test_web_scraper.py` | ArticleScraper, blacklist domains |
| `test_x_scraper.py` | X/Twitter Apify scraper |

---

## XIV. Tài liệu dự án ✅

| File | Mô tả |
|---|---|
| `docs/ARCHITECTURE.md` | Kiến trúc hệ thống, quyết định thiết kế |
| `docs/TUTORIAL.md` | Hướng dẫn developer thêm tính năng mới |
| `docs/CODE-REVIEW.md` | Đánh giá chất lượng, bảo mật, hiệu năng |
| `docs/TECHNICAL-REFERENCE.md` | Tham chiếu API đầy đủ, env vars, schemas |
| `docs/DETAILED-DESIGN.md` | Thiết kế chi tiết từng module |
| `docs/database_schema.md` | Thiết kế cơ sở dữ liệu MongoDB |
| `docs/system_overview.md` | Tổng quan hệ thống, data flow |
| `docs/deploy.md` | Hướng dẫn triển khai production |
| `docs/apify_x_scraping.md` | Tích hợp X/Twitter qua Apify |

---

## XV. Tổng kết

### Các tính năng cốt lõi đã hoàn thành

| # | Tính năng | Mức độ hoàn thành |
|---|---|---|
| 1 | Thu thập dữ liệu Telegram tự động | ✅ 100% |
| 2 | Thu thập dữ liệu X/Twitter tự động | ✅ 100% |
| 3 | Phân loại chủ đề bằng ML (TF-IDF + SVM) | ✅ 100% |
| 4 | Phân loại chủ đề bằng Rule-based | ✅ 100% |
| 5 | AI phát hiện Hot News (GPT-4o-mini) | ✅ 100% |
| 6 | AI tóm tắt kênh tự động | ✅ 100% |
| 7 | Xác thực JWT + Telegram OTP | ✅ 100% |
| 8 | Phân quyền Admin / User | ✅ 100% |
| 9 | Quản lý kênh (subscribe/unsubscribe) | ✅ 100% |
| 10 | Analytics: trend, keyword, timeline, heatmap | ✅ 100% |
| 11 | Giao diện web 13 trang (3 trang public, 6 admin, 1 user, 3 auth) | ✅ 100% |
| 12 | Text-to-Speech tiếng Việt (public + authenticated) | ✅ 100% |
| 13 | Background workers tự động hóa | ✅ 100% |
| 14 | Triển khai production (Render + Vercel + Atlas) | ✅ 100% |
| 15 | Phân loại địa lý (Geo) 10 vùng | ✅ 100% |
| 16 | Public API + X Live Search | ✅ 100% |
| 17 | Backfill hàng loạt topics & geo | ✅ 100% |
| 18 | Tài liệu kỹ thuật đầy đủ (9 files) | ✅ 100% |

### Điểm nổi bật kỹ thuật

- **Pipeline phân loại 4 tầng** đảm bảo phân loại tối đa — không bỏ sót bài nào
- **Graceful degradation** cho OpenAI và Apify — hệ thống hoạt động ngay cả khi không có API key
- **Cache thông minh** cho hot news — tránh gọi OpenAI lặp lại, tiết kiệm chi phí
- **2 phương thức đăng nhập** — mật khẩu, Telegram OTP
- **Không cần Twitter API** — dùng Apify scraping, tránh chi phí và giới hạn Twitter

### Hướng phát triển tiếp theo (đề xuất)

- [ ] Thêm pagination infinite scroll cho PostsPage
- [ ] Push notification khi có hot news mới
- [ ] Xuất báo cáo CSV/PDF
- [ ] Thêm nguồn RSS feed
- [ ] Tối ưu: chuyển JWT từ localStorage sang HttpOnly cookie
