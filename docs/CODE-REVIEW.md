# Báo cáo Code Review — NewsBot (botTele)

> **Phạm vi:** Toàn bộ codebase `src/`, `scripts/`, `web/src/`  
> **Ngày review:** 2025  
> **Phiên bản:** 2.0.0

---

## Tóm tắt điều hành

| Hạng mục | Đánh giá | Phát hiện chính |
|---|---|---|
| Bảo mật | 🟠 TRUNG BÌNH-CAO | Giá trị mặc định không an toàn trong config, JWT lưu localStorage |
| Xử lý lỗi | 🟡 TRUNG BÌNH | Chưa có retry + dead-letter-queue cho background worker |
| Hiệu năng | 🟢 TỐT | Pipeline `$facet` hiệu quả, cache in-memory cho hotnews |
| Testing | 🟡 TRUNG BÌNH | Có hạ tầng pytest nhưng coverage còn hạn chế |
| Chất lượng code | 🟢 TỐT | Phân tầng rõ ràng, Pydantic v2 đầy đủ, naming nhất quán |
| Xác thực dữ liệu | 🟢 TỐT | Pydantic validate tại mọi endpoint, index MongoDB unique |

---

## 1. Đánh giá Bảo mật

### 🟠 HIGH — Thông tin đăng nhập mặc định không an toàn

**Vị trí:** `src/config.py:60`, `src/api/main.py` (docstring `/auth/login`)

```python
# src/config.py
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "admin123")  # Change in production!
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "your-secret-key-change-in-production-2026")
```

**Rủi ro:** Nếu deploy mà quên đặt biến môi trường, hệ thống sẽ chạy với mật khẩu `admin123` và JWT secret công khai. Attacker có thể forge token hợp lệ.

**Khuyến nghị:**
```python
# Bắt buộc đặt giá trị — ném lỗi ngay khi khởi động nếu thiếu
JWT_SECRET_KEY = os.environ["JWT_SECRET_KEY"]          # KeyError nếu chưa đặt
ADMIN_PASSWORD  = os.environ.get("ADMIN_PASSWORD") or \
    (_ for _ in ()).throw(RuntimeError("ADMIN_PASSWORD chưa được đặt"))
```
Hoặc thêm validation trong lifespan:
```python
@asynccontextmanager
async def lifespan(app):
    if JWT_SECRET_KEY == "your-secret-key-change-in-production-2026":
        raise RuntimeError("JWT_SECRET_KEY chưa được thay đổi — dừng server!")
```

---

### 🟠 HIGH — JWT lưu trong `localStorage` (XSS risk)

**Vị trí:** `web/src/context/AuthContext.jsx`

```javascript
// Lưu token vào localStorage — JavaScript có thể đọc được
localStorage.setItem("auth_token", data.access_token);
```

**Rủi ro:** Mọi JavaScript (bao gồm XSS) trên trang đều đọc được token. Nếu có lỗ hổng XSS trong bất kỳ thư viện bên thứ ba nào, token bị đánh cắp.

**Khuyến nghị (nếu muốn nâng cấp):** Chuyển sang HttpOnly cookie từ server. Hiện tại, đảm bảo `Content-Security-Policy` header được thiết lập chặt.

```python
# main.py — thêm CSP header
@app.middleware("http")
async def add_security_headers(request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Content-Security-Policy"] = "default-src 'self'"
    return response
```

---

### 🟠 HIGH — Telegram Session String lộ ra

**Vị trí:** `src/config.py`, `src/ingestion/telegram_worker.py`

```python
TELEGRAM_SESSION_STRING = os.getenv("TELEGRAM_SESSION_STRING", "")
```

**Rủi ro:** Session String Telethon tương đương toàn quyền truy cập tài khoản Telegram. Nếu lộ ra trong log hoặc error message, attacker kiểm soát được tài khoản.

**Khuyến nghị:**
- Không bao giờ log giá trị này (hiện tại code đã không log — tốt)
- Đảm bảo không xuất hiện trong traceback khi `DEBUG=True`
- Dùng Render.com Secrets hoặc HashiCorp Vault cho môi trường production

---

### 🟡 MEDIUM — Không có cơ chế Refresh Token

**Vị trí:** `src/api/auth.py`, `web/src/context/AuthContext.jsx`

**Hiện trạng:** JWT có thời hạn 24 giờ (`JWT_ACCESS_TOKEN_EXPIRE_MINUTES=1440`). Khi token hết hạn, người dùng bị đăng xuất mà không có cơ hội lấy token mới.

**Hệ quả:** Nếu token bị đánh cắp, nó vẫn hợp lệ đến 24 giờ mà không có cách thu hồi.

**Khuyến nghị:** Thêm refresh token (thời hạn ngắn 1h access + 7 ngày refresh) hoặc duy trì token revocation list trong Redis/MongoDB.

---

### 🟡 MEDIUM — `/auth/register` tự động login người dùng chưa được duyệt

**Vị trí:** `src/api/main.py:register_endpoint`

```python
@app.post("/auth/register")
async def register_endpoint(request: RegisterRequest):
    result = register_user(request)          # tạo user với status="pending"?
    token_data = login(result["username"], request.password)  # lập tức cấp token!
    return token_data
```

**Vấn đề:** `register_user()` tạo user với `status="pending"` nhưng ngay sau đó `login()` được gọi mà không kiểm tra status. User chưa được admin duyệt vẫn nhận được JWT token hợp lệ.

**Khuyến nghị:**
```python
@app.post("/auth/register")
async def register_endpoint(request: RegisterRequest):
    result = register_user(request)
    if result.get("status") == "pending":
        return {"message": "Tài khoản đang chờ duyệt. Vui lòng liên hệ admin."}
    token_data = login(result["username"], request.password)
    return token_data
```

---

### 🟡 MEDIUM — Dictionary `_hotnews_locks` tăng trưởng không giới hạn

**Vị trí:** `src/api/main.py`

```python
_hotnews_locks: dict[str, asyncio.Lock] = {}
_hotnews_mem: dict[str, dict] = {}
# Locks không bao giờ bị xóa — memory leak tiềm ẩn
```

**Rủi ro:** Sau nhiều ngày chạy, dict tích lũy entries cho mọi `window_hours` từng được request. Tuy ít khi trở thành vấn đề nghiêm trọng nhưng nên có cleanup.

**Khuyến nghị:** Giới hạn số lượng bucket hoặc xóa lock sau khi cache hết hạn.

---

### 🟡 MEDIUM — Không có giới hạn tốc độ cho `/auth/login` (brute force)

**Vị trí:** `src/api/main.py`

```python
# Comment trong code: "PUBLIC - No rate limit for critical auth"
@app.post("/auth/login", response_model=LoginResponse)
async def login_endpoint(request: LoginRequest):
```

**Rủi ro:** Endpoint login không có rate limit — brute force password attack dễ dàng.

**Khuyến nghị:**
```python
@app.post("/auth/login")
@limiter.limit("5/minute")  # Tối đa 5 lần thử/phút
async def login_endpoint(request: Request, body: LoginRequest):
```

---

### ✅ TỐT — Các điểm bảo mật đã làm đúng

| Điểm | Chi tiết |
|---|---|
| Bcrypt password hashing | `passlib[bcrypt]` với rounds mặc định (12) |
| Pydantic v2 input validation | Validate tất cả request body tại mọi endpoint |
| Rate limiting toàn cục | SlowAPI 60 req/min, 1000 req/hour |
| CORS whitelist | `get_allowed_origins()` chỉ cho phép origin đã cấu hình |
| Không SQL injection | MongoDB query builder — không concatenate string |
| Không lưu password plaintext | Chỉ lưu `password_hash` trong database |
| Admin role check | `get_current_admin_user()` kiểm tra `role == "admin"` |

---

## 2. Xử lý lỗi

### 🟡 MEDIUM — Background worker không có dead-letter queue

**Vị trí:** `src/ingestion/channel_queue_worker.py`

```python
async def run_worker():
    while True:
        # Nếu exception xảy ra, channel bị retry MAX_ATTEMPTS=3 lần
        # Sau đó status = "error" — không có thông báo đến admin
        await asyncio.sleep(POLL_INTERVAL)
```

**Rủi ro:** Channel thất bại không có cơ chế alert. Admin phải vào database thủ công kiểm tra `status="error"`.

**Khuyến nghị:** Gửi notification (webhook, email, hoặc Telegram message) khi channel chuyển sang `status="error"`.

---

### 🟡 MEDIUM — OpenAI API lỗi im lặng

**Vị trí:** `src/processing/ai_topic_detector.py`

```python
except Exception:
    return []  # Degradation im lặng — không log chi tiết lỗi
```

**Rủi ro:** Khi OpenAI API lỗi (quota, timeout, invalid key), hệ thống fallback về rule-based mà không log warning rõ ràng. Khó debug khi ML không hoạt động như mong đợi.

**Khuyến nghị:**
```python
except Exception as e:
    logger.warning(f"OpenAI API lỗi (graceful degradation): {type(e).__name__}: {e}")
    return []
```

---

### ✅ TỐT — Xử lý lỗi tốt

- `scripts/create_indexes.py`: `_safe_create()` xử lý `OperationFailure` codes 85/86 (index conflict)
- `src/db/mongo.py`: Singleton client, init một lần, exception rõ ràng nếu không kết nối được
- FastAPI tự động trả HTTP 422 cho Pydantic validation errors với detail đầy đủ

---

## 3. Hiệu năng

### ✅ TỐT — MongoDB Pipeline tối ưu

**Vị trí:** `src/api/main.py:get_stats()`

```python
# Sử dụng $facet để chạy nhiều aggregation trong 1 collection scan
pipeline = [
    {"$match": base_query},
    {"$facet": {
        "total": [...],
        "sources": [...],
        "languages": [...],
        "topics": [...],
        "platforms": [...],
    }}
]
```

Thay vì 5 query riêng biệt, `$facet` chỉ scan collection 1 lần — giảm đáng kể I/O.

---

### ✅ TỐT — Cache in-memory cho Hot News

```python
_hotnews_mem: dict[str, dict] = {}
# TTL theo window: 1h (24h window), 2h (48h), 3h (72h+)
```

Cache ngăn gọi OpenAI API trùng lặp — tiết kiệm chi phí và giảm latency.

---

### 🟡 MEDIUM — Không có connection pooling rõ ràng cho MongoDB

**Vị trí:** `src/db/mongo.py`

PyMongo có connection pool mặc định nhưng kích thước không được cấu hình tường minh. Với nhiều concurrent request, nên đặt `maxPoolSize`.

**Khuyến nghị:**
```python
client = MongoClient(MONGO_URI, maxPoolSize=50, minPoolSize=5)
```

---

### 🟡 MEDIUM — `find_one()` trong request loop không có projection

**Vị trí:** `src/api/main.py:get_current_user_info()`

```python
user_doc = users_col.find_one({"username": token_data.username})
# Không có projection — tải toàn bộ document kể cả password_hash
```

**Khuyến nghị:**
```python
user_doc = users_col.find_one(
    {"username": token_data.username},
    {"password_hash": 0}  # Không lấy password_hash
)
```

---

## 4. Testing

### Trạng thái hiện tại

| File test | Coverage |
|---|---|
| `tests/test_auth_roles.py` | Auth flow, role check |
| `tests/test_cleaning.py` | `clean_text()`, `extract_links()` |
| `tests/test_dedupe.py` | Deduplication logic |
| `tests/test_ml_classifier.py` | MLTopicClassifier |
| `tests/test_post_model.py` | Post Pydantic model |
| `tests/test_security.py` | Security headers, JWT validation |
| `tests/test_web_scraper.py` | ArticleScraper |
| `tests/test_x_scraper.py` | X/Twitter scraper |

### 🟡 Thiếu — Integration tests cho API endpoints

Chưa có test cho các endpoint `/posts`, `/stats`, `/analytics/*`, `/hotnews`. Cần mock MongoDB và kiểm tra toàn bộ request-response cycle.

**Ví dụ cần thêm:**
```python
# tests/test_api_posts.py
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock

def test_get_posts_requires_auth(client):
    response = client.get("/posts")
    assert response.status_code == 403

def test_get_posts_with_topic_filter(client, auth_headers):
    response = client.get("/posts?topic=Crypto&limit=5", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert all("Crypto" in p.get("topics", []) for p in data)
```

---

### 🟡 Thiếu — Tests cho background workers

`channel_queue_worker.py` và `run_refresh_loop()` chưa có unit test. Những đoạn code phức tạp nhất (retry logic, status transitions) không được kiểm tra tự động.

---

## 5. Chất lượng Code

### ✅ TỐT — Phân tầng kiến trúc rõ ràng

```
src/
├── config.py        — Config layer (env vars)
├── api/             — HTTP layer (FastAPI routers)
├── db/              — Data access layer (MongoDB)
├── ingestion/       — External data fetching
├── processing/      — Pure business logic (không có I/O)
└── models/          — Pydantic schemas
```

Các module trong `processing/` là pure Python functions — không import từ `api/` hoặc `db/`. Dễ test, dễ reuse.

---

### ✅ TỐT — Type hints và Pydantic models đầy đủ

```python
class Post(BaseModel):
    id: str
    source: str
    platform: str = "telegram"
    text: str
    created_at: datetime
    topics: List[str] = []
    topic_predictions: List[TopicPrediction] = []
    dedupe_key: Optional[str] = None
```

---

### 🟡 CẢI THIỆN — Magic numbers không có tên

**Vị trí:** `src/ingestion/channel_queue_worker.py`

```python
POLL_INTERVAL = 30        # giây
REFRESH_INTERVAL = 43200  # giây — là 12 giờ, không rõ ràng
MAX_ATTEMPTS = 3
FETCH_DAYS = 7
SUMMARY_DAYS = 1
```

`43200` nên được viết là `12 * 60 * 60` hoặc có comment `# 12 giờ` rõ ràng hơn.

---

## 6. Tóm tắt hành động

### Ưu tiên cao (nên xử lý trước production)

1. **Bắt buộc** đặt `JWT_SECRET_KEY` và `ADMIN_PASSWORD` qua biến môi trường — thêm startup validation
2. **Thêm rate limit** cho `/auth/login` (5 lần/phút)
3. **Kiểm tra status** user trong `register_endpoint` trước khi cấp token

### Ưu tiên trung bình (sprint tiếp theo)

4. Thêm security headers middleware (`X-Content-Type-Options`, `X-Frame-Options`)
5. Thêm projection vào `find_one()` để không trả `password_hash`
6. Log warning khi OpenAI API lỗi (graceful degradation)
7. Thêm integration tests cho API endpoints chính

### Cải thiện dài hạn

8. Chuyển JWT từ `localStorage` sang HttpOnly cookie
9. Thêm refresh token mechanism
10. Cấu hình `maxPoolSize` cho MongoDB connection pool
11. Alert tự động khi channel chuyển sang `status="error"`
