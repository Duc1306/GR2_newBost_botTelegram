# Hướng Dẫn Lập Trình — NewsBot

## Xây Dựng Tính Năng Mới Từ A đến Z

---

### Bạn Sẽ Học Được Gì

Sau khi hoàn thành tutorial này, bạn có thể:

- Điều hướng trong cấu trúc phân tầng của dự án (ingestion → processing → db → api → frontend)
- Thêm một tính năng backend hoàn chỉnh (Pydantic model → MongoDB → FastAPI endpoint)
- Viết module xử lý dữ liệu riêng trong `src/processing/`
- Kết nối frontend React qua `useQuery` + `api.jsx`
- Hiểu cơ chế xác thực JWT và phân quyền admin/user

---

### Yêu Cầu Trước Khi Bắt Đầu

| Kiến thức | Nơi học |
|---|---|
| Python cơ bản (class, async/await) | [docs.python.org](https://docs.python.org/3/tutorial/) |
| FastAPI cơ bản | [fastapi.tiangolo.com](https://fastapi.tiangolo.com/tutorial/) |
| Pydantic v2 | [docs.pydantic.dev](https://docs.pydantic.dev/latest/) |
| React hooks (useState, useEffect) | [react.dev/learn](https://react.dev/learn) |
| MongoDB cơ bản (find, insert, update) | [mongodb.com/docs](https://www.mongodb.com/docs/manual/crud/) |

> **Môi trường cần có:** Python 3.12+, MongoDB 6+ (local hoặc Atlas), Node.js 18+.  
> Xem `README.md` để cài đặt toàn bộ dependencies.

---

### Ước Tính Thời Gian

| Phần | Thời gian |
|---|---|
| Phần 1 — Định hướng | 20 phút |
| Phần 2 — Backend | 45 phút |
| Phần 3 — Frontend | 30 phút |
| Phần 4 — Thử thách mở rộng | Tùy ý |

**Tổng hướng dẫn ≈ 95 phút**

---

### Kết Quả Cuối Cùng

Bạn sẽ xây dựng tính năng **Bookmark (Lưu bài viết)**: cho phép user đăng nhập lưu các bài viết yêu thích vào danh sách riêng, xem lại, và xoá bookmark.

Tính năng này có đầy đủ các thành phần đặc trưng của dự án: Pydantic model, MongoDB collection, FastAPI router, auth dependency, và React hook — là bài tập lý tưởng để nắm vững kiến trúc.

---

## Phần 1 — Định Hướng

### 1.1 Cấu Trúc Dự Án

Dự án được chia làm 2 phần chính:

```
botTele/
├── src/                  ← Backend Python (FastAPI)
│   ├── config.py         ← Mọi biến môi trường nạp ở đây
│   ├── api/              ← HTTP layer: routers, middleware, auth
│   ├── db/               ← MongoDB client (singleton)
│   ├── ingestion/        ← Thu thập dữ liệu từ Telegram & X
│   ├── models/           ← Pydantic schemas (kiểu dữ liệu)
│   └── processing/       ← Xử lý văn bản, ML, AI (không phụ thuộc framework)
└── web/                  ← Frontend React 18 + Vite + MUI
    └── src/
        ├── lib/          ← HTTP client (api.jsx, publicApi.js)
        ├── context/      ← AuthContext, ThemeContext
        ├── hooks/        ← useApi.jsx (TanStack Query wrappers)
        ├── components/   ← UI components tái sử dụng
        └── pages/        ← Trang phân theo vai trò: admin/, user/, public/, auth/
```

---

### 1.2 Các Tầng Kiến Trúc

Dữ liệu luôn chảy theo một chiều: **thu thập → xử lý → lưu trữ → API → giao diện**.

```
┌──────────────────────────────────────────────┐
│  web/ (React SPA)                            │  ← Hiển thị & tương tác
│  ┌────────────────────────────────────────┐  │
│  │  src/api/ (FastAPI routers)            │  │  ← Nhận HTTP request, trả JSON
│  │  ┌──────────────────────────────────┐  │  │
│  │  │  src/processing/ (ML, cleaning)  │  │  │  ← Xử lý thuần Python, không I/O
│  │  │  ┌────────────────────────────┐  │  │  │
│  │  │  │  src/db/ + src/models/     │  │  │  │  ← Lưu trữ & schema dữ liệu
│  │  │  └────────────────────────────┘  │  │  │
│  │  └──────────────────────────────────┘  │  │
│  └────────────────────────────────────────┘  │
└──────────────────────────────────────────────┘
         ↑ Thu thập: src/ingestion/ (Telegram, X)
```

**Nguyên tắc quan trọng:** Module trong `processing/` không được import từ `fastapi`, `pymongo`, hay bất kỳ I/O framework nào. Chúng là hàm thuần Python — dễ test độc lập.

---

### 1.3 Cơ Chế Xác Thực

Mọi request cần auth đều mang JWT trong header `Authorization: Bearer <token>`.

```
Client (React)
  │── POST /auth/login { username, password }
  │                           │
  │                  auth.py: verify_password (bcrypt)
  │                           │  lookup users collection
  │                           │  create_access_token() → JWT HS256 (24h)
  │◄── { access_token, role }
  │
  AuthContext → localStorage.setItem("auth_token", ...)
  │
  │── Mọi request tiếp theo:
  │   Authorization: Bearer eyJ...
  │                           │
  │                  Depends(get_current_user)   → kiểm tra JWT
  │                  Depends(get_current_admin_user) → thêm kiểm tra role="admin"
```

---

### 1.4 Đọc Tính Năng Có Sẵn Trước

Trước khi viết code mới, hãy đọc **Channel Subscription** — đây là tính năng đơn giản nhất có đầy đủ các lớp.

| File | Điều cần chú ý |
|---|---|
| `src/models/channel.py` | Pydantic model `Channel`, `SubscribeChannelRequest` |
| `src/api/channels.py` | FastAPI `APIRouter`, `Depends(get_current_user)` |
| `src/db/mongo.py` | `get_db()` → truy cập collection bất kỳ |
| `scripts/create_indexes.py` | Cách tạo index MongoDB idempotent |
| `web/src/lib/api.jsx` | Hàm `fetchWithAuth()` và pattern gọi API |
| `web/src/hooks/useApi.jsx` | `useQuery` wrapping hàm API |

> **Checkpoint ✓** — Bạn có thể trace một request `POST /user/channels/subscribe` qua hết các file không? Viết ra trước khi tiếp tục.

---

## Phần 2 — Xây Dựng Backend

Chúng ta sẽ thêm tính năng **Bookmark** với các endpoints:

- `POST /bookmarks` — lưu một bài viết
- `GET /bookmarks` — lấy danh sách bookmark của user hiện tại
- `DELETE /bookmarks/{post_id}` — xoá bookmark

---

### Bước 1 — Pydantic Model

**Tạo** `src/models/bookmark.py`:

```python
"""Bookmark model — lưu bài viết yêu thích của user."""
from __future__ import annotations
from datetime import datetime
from pydantic import BaseModel, Field


class Bookmark(BaseModel):
    """Document lưu trong MongoDB collection 'bookmarks'."""
    username: str                    # Người dùng sở hữu bookmark
    post_id: str                     # ID bài viết (trùng với Post.id)
    saved_at: datetime = Field(default_factory=datetime.utcnow)
    note: str = ""                   # Ghi chú tùy chọn của user


class BookmarkRequest(BaseModel):
    """Request body khi tạo bookmark mới."""
    post_id: str = Field(
        ...,
        description="ID bài viết cần lưu (dạng 'platform:source:source_id')",
        min_length=5,
        max_length=200,
    )
    note: str = Field(default="", max_length=500)


class BookmarkResponse(BaseModel):
    """Response trả về sau khi tạo bookmark thành công."""
    username: str
    post_id: str
    saved_at: datetime
    note: str
    message: str = "Đã lưu bài viết"
```

> **Tại sao dùng Pydantic?** FastAPI tự động validate request body, trả 422 nếu sai schema, và generate OpenAPI docs. Không cần viết validation thủ công.

---

### Bước 2 — Tạo Index MongoDB

**Mở** `scripts/create_indexes.py` và thêm vào hàm `create_indexes()`:

```python
# ── bookmarks collection ──
bookmarks = db["bookmarks"]
_safe_create(bookmarks, [("username", 1), ("post_id", 1)], unique=True)
_safe_create(bookmarks, [("username", 1), ("saved_at", -1)])
```

> **Tại sao cần index `(username, post_id)` unique?** Tránh user lưu trùng bài viết. MongoDB sẽ tự báo lỗi `DuplicateKeyError` — chúng ta bắt lỗi này để trả về 409 Conflict.

Chạy thử để tạo index ngay:

```bash
python scripts/create_indexes.py
```

---

### Bước 3 — FastAPI Router

**Tạo** `src/api/bookmarks.py`:

```python
"""Bookmark API — lưu & quản lý bài viết yêu thích."""
from __future__ import annotations
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from pymongo.errors import DuplicateKeyError

from src.api.auth import get_current_user
from src.db.mongo import get_db
from src.models.bookmark import Bookmark, BookmarkRequest, BookmarkResponse

router = APIRouter(prefix="/bookmarks", tags=["Bookmarks"])


@router.post("", response_model=BookmarkResponse, status_code=status.HTTP_201_CREATED)
async def create_bookmark(
    body: BookmarkRequest,
    current_user: str = Depends(get_current_user),
):
    """Lưu bài viết vào danh sách bookmark của user."""
    db = get_db()

    # Kiểm tra bài viết có tồn tại không
    post = db["posts"].find_one({"id": body.post_id}, {"id": 1})
    if not post:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Không tìm thấy bài viết: {body.post_id}",
        )

    bookmark = Bookmark(
        username=current_user,
        post_id=body.post_id,
        note=body.note,
    )

    try:
        db["bookmarks"].insert_one(bookmark.model_dump())
    except DuplicateKeyError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Bài viết này đã được lưu trước đó",
        )

    return BookmarkResponse(**bookmark.model_dump())


@router.get("", tags=["Bookmarks"])
async def list_bookmarks(
    skip: int = 0,
    limit: int = 20,
    current_user: str = Depends(get_current_user),
):
    """Lấy danh sách bài viết đã bookmark của user hiện tại."""
    db = get_db()
    cursor = (
        db["bookmarks"]
        .find({"username": current_user}, {"_id": 0})
        .sort("saved_at", -1)
        .skip(skip)
        .limit(limit)
    )
    bookmarks = list(cursor)
    total = db["bookmarks"].count_documents({"username": current_user})

    # Enrich với nội dung bài viết
    post_ids = [b["post_id"] for b in bookmarks]
    posts = {
        p["id"]: p
        for p in db["posts"].find(
            {"id": {"$in": post_ids}},
            {"id": 1, "text": 1, "source": 1, "topics": 1, "created_at": 1},
        )
    }

    for b in bookmarks:
        b["post"] = posts.get(b["post_id"])

    return {"bookmarks": bookmarks, "total": total, "skip": skip, "limit": limit}


@router.delete("/{post_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_bookmark(
    post_id: str,
    current_user: str = Depends(get_current_user),
):
    """Xoá bookmark theo post_id."""
    db = get_db()
    result = db["bookmarks"].delete_one(
        {"username": current_user, "post_id": post_id}
    )
    if result.deleted_count == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Không tìm thấy bookmark này",
        )
```

> **Lưu ý bảo mật:** `current_user` luôn lấy từ `Depends(get_current_user)` — không bao giờ dùng username từ request body để filter dữ liệu. Điều này ngăn user A đọc/xoá bookmark của user B.

---

### Bước 4 — Đăng Ký Router vào App

**Mở** `src/api/main.py`, thêm vào phần import và `include_router`:

```python
# Thêm vào phần import (cùng nhóm với các router khác):
from src.api.bookmarks import router as bookmarks_router

# Thêm sau app.include_router(telegram_auth_router):
app.include_router(bookmarks_router)
```

> **Checkpoint ✓** — Khởi động API và kiểm tra:
> ```bash
> uvicorn src.api.main:app --reload --port 8000
> ```
> Truy cập `http://localhost:8000/docs` → bạn thấy nhóm **Bookmarks** với 3 endpoint mới.  
> Thử `POST /bookmarks` với token (lấy từ `POST /auth/login` trước) — phải nhận được 201.

---

### Bước 5 — Viết Test

**Tạo** `tests/test_bookmarks.py`:

```python
"""Tests cho Bookmark API."""
import pytest
from fastapi.testclient import TestClient
from src.api.main import app

client = TestClient(app)


def get_token(username="admin", password="admin123"):
    res = client.post("/auth/login", json={"username": username, "password": password})
    return res.json().get("access_token")


def auth_headers(token):
    return {"Authorization": f"Bearer {token}"}


class TestBookmarkCreate:
    def test_requires_auth(self):
        res = client.post("/bookmarks", json={"post_id": "telegram:test:1"})
        assert res.status_code == 403

    def test_post_not_found(self):
        token = get_token()
        res = client.post(
            "/bookmarks",
            json={"post_id": "telegram:nonexistent:999"},
            headers=auth_headers(token),
        )
        assert res.status_code == 404

    def test_duplicate_bookmark(self):
        """Lưu cùng bài hai lần → 409 lần thứ hai."""
        # Cần có post_id hợp lệ trong DB khi test này chạy
        pass  # TODO: seed test data


class TestBookmarkList:
    def test_requires_auth(self):
        res = client.get("/bookmarks")
        assert res.status_code == 403

    def test_returns_paginated(self):
        token = get_token()
        res = client.get("/bookmarks", headers=auth_headers(token))
        assert res.status_code == 200
        data = res.json()
        assert "bookmarks" in data
        assert "total" in data
```

Chạy test:

```bash
pytest tests/test_bookmarks.py -v
```

> **Bài tập 5a** — Thêm test cho `DELETE /bookmarks/{post_id}`:
> - Xoá bookmark tồn tại → 204
> - Xoá bookmark không tồn tại → 404
> - User A không xoá được bookmark của User B

---

## Phần 3 — Kết Nối Frontend

### Bước 6 — Thêm API Client

**Mở** `web/src/lib/api.jsx` và thêm ở cuối file:

```javascript
// ─── Bookmarks ────────────────────────────────────────────────────────────────

export async function fetchBookmarks({ skip = 0, limit = 20 } = {}) {
  const res = await fetchWithAuth(
    `${API_BASE_URL}/bookmarks?skip=${skip}&limit=${limit}`
  );
  if (!res.ok) throw new Error("Không thể tải danh sách bookmark");
  return res.json();
}

export async function createBookmark({ post_id, note = "" }) {
  const res = await fetchWithAuth(`${API_BASE_URL}/bookmarks`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ post_id, note }),
  });
  if (res.status === 409) throw new Error("Bài viết đã được lưu trước đó");
  if (!res.ok) throw new Error("Không thể lưu bài viết");
  return res.json();
}

export async function deleteBookmark(post_id) {
  const res = await fetchWithAuth(
    `${API_BASE_URL}/bookmarks/${encodeURIComponent(post_id)}`,
    { method: "DELETE" }
  );
  if (res.status === 404) throw new Error("Bookmark không tồn tại");
  if (!res.ok) throw new Error("Không thể xoá bookmark");
}
```

---

### Bước 7 — Thêm React Query Hooks

**Mở** `web/src/hooks/useApi.jsx` và thêm ở cuối:

```javascript
import {
  // ... các import hiện có
  fetchBookmarks,
  createBookmark,
  deleteBookmark,
} from '../lib/api.jsx';
import { useMutation, useQueryClient } from '@tanstack/react-query';

// Hook lấy danh sách bookmark
export function useBookmarks(params = {}) {
  return useQuery({
    queryKey: ['bookmarks', params],
    queryFn: () => fetchBookmarks(params),
    staleTime: 2 * 60 * 1000, // 2 phút
  });
}

// Hook tạo bookmark mới
export function useCreateBookmark() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: createBookmark,
    onSuccess: () => {
      // Làm mới cache danh sách bookmark
      queryClient.invalidateQueries({ queryKey: ['bookmarks'] });
    },
  });
}

// Hook xoá bookmark
export function useDeleteBookmark() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: deleteBookmark,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['bookmarks'] });
    },
  });
}
```

---

### Bước 8 — Tạo Trang Bookmark

**Tạo** `web/src/pages/user/BookmarksPage.jsx`:

```jsx
import React, { useState } from "react";
import {
  Box, Typography, Card, CardContent, CardActions,
  Button, CircularProgress, Alert, Chip, IconButton,
  Tooltip,
} from "@mui/material";
import DeleteIcon from "@mui/icons-material/Delete";
import BookmarkIcon from "@mui/icons-material/Bookmark";
import { formatDistanceToNow } from "date-fns";
import { vi } from "date-fns/locale";
import { useBookmarks, useDeleteBookmark } from "../../hooks/useApi.jsx";
import { getTopicColor } from "../../theme/colors.jsx";

export default function BookmarksPage() {
  const { data, isLoading, error } = useBookmarks();
  const deleteMutation = useDeleteBookmark();

  if (isLoading) {
    return (
      <Box display="flex" justifyContent="center" mt={4}>
        <CircularProgress />
      </Box>
    );
  }

  if (error) {
    return <Alert severity="error">Không thể tải bookmark: {error.message}</Alert>;
  }

  const bookmarks = data?.bookmarks || [];

  return (
    <Box p={3}>
      <Box display="flex" alignItems="center" gap={1} mb={3}>
        <BookmarkIcon color="primary" />
        <Typography variant="h5" fontWeight={600}>
          Bài Viết Đã Lưu
        </Typography>
        <Chip label={`${data?.total || 0} bài`} size="small" color="primary" />
      </Box>

      {bookmarks.length === 0 ? (
        <Alert severity="info">Bạn chưa lưu bài viết nào.</Alert>
      ) : (
        <Box display="flex" flexDirection="column" gap={2}>
          {bookmarks.map((bm) => (
            <Card key={bm.post_id} variant="outlined">
              <CardContent>
                {/* Topics */}
                <Box display="flex" gap={0.5} flexWrap="wrap" mb={1}>
                  {(bm.post?.topics || []).map((t) => (
                    <Chip
                      key={t}
                      label={t}
                      size="small"
                      sx={{ bgcolor: getTopicColor(t), color: "#fff", fontSize: 11 }}
                    />
                  ))}
                </Box>

                {/* Text */}
                <Typography variant="body2" color="text.secondary" noWrap>
                  {bm.post?.text || bm.post_id}
                </Typography>

                {/* Meta */}
                <Typography variant="caption" color="text.disabled" mt={0.5} display="block">
                  Lưu lúc{" "}
                  {formatDistanceToNow(new Date(bm.saved_at), {
                    addSuffix: true,
                    locale: vi,
                  })}
                  {bm.note && ` · Ghi chú: ${bm.note}`}
                </Typography>
              </CardContent>

              <CardActions sx={{ pt: 0 }}>
                <Tooltip title="Xoá bookmark">
                  <IconButton
                    size="small"
                    color="error"
                    onClick={() => deleteMutation.mutate(bm.post_id)}
                    disabled={deleteMutation.isPending}
                  >
                    <DeleteIcon fontSize="small" />
                  </IconButton>
                </Tooltip>
              </CardActions>
            </Card>
          ))}
        </Box>
      )}
    </Box>
  );
}
```

---

### Bước 9 — Đăng Ký Route trong App.jsx

**Mở** `web/src/App.jsx` và thêm:

```jsx
// Thêm vào phần lazy imports:
const BookmarksPage = lazy(() => import('./pages/user/BookmarksPage.jsx'));

// Thêm vào phần <Routes> (trong ProtectedRoute):
<Route path="/bookmarks" element={<BookmarksPage />} />
```

---

### Bước 10 — Nút Bookmark trên PostCard

**Mở** `web/src/components/PostCard.jsx`, thêm nút lưu vào mỗi card:

```jsx
import { useCreateBookmark } from '../hooks/useApi.jsx';
import BookmarkBorderIcon from '@mui/icons-material/BookmarkBorder';
import BookmarkIcon from '@mui/icons-material/Bookmark';

// Trong component PostCard:
const bookmarkMutation = useCreateBookmark();

// Trong JSX, thêm nút vào phần actions:
<Tooltip title="Lưu bài viết">
  <IconButton
    size="small"
    onClick={() => bookmarkMutation.mutate({ post_id: post.id })}
    disabled={bookmarkMutation.isPending}
    color={bookmarkMutation.isSuccess ? "primary" : "default"}
  >
    {bookmarkMutation.isSuccess
      ? <BookmarkIcon fontSize="small" />
      : <BookmarkBorderIcon fontSize="small" />}
  </IconButton>
</Tooltip>
```

> **Checkpoint ✓** — Khởi động frontend:
> ```bash
> cd web && npm run dev
> ```
> Đăng nhập → nhấn nút bookmark trên một bài viết → vào `/bookmarks` → bài đã lưu xuất hiện → nhấn xoá → bài biến mất.  
> Tất cả thay đổi phải xảy ra **không cần reload trang** (nhờ `invalidateQueries`).

---

## Phần 4 — Thử Thách Mở Rộng

Sau khi hoàn thành phần hướng dẫn, hãy tự thử các bài sau:

### Thử thách 4.1 — Tìm Kiếm Trong Bookmark
Thêm query param `q` vào `GET /bookmarks` để tìm theo nội dung bài viết.

*Gợi ý:* Dùng `$regex` trong MongoDB query hoặc `$text` search nếu collection `posts` đã có text index.

### Thử thách 4.2 — Đếm Bookmark Theo Topic
Thêm endpoint `GET /bookmarks/stats` trả về số lượng bookmark theo từng topic.

*Gợi ý:* Dùng MongoDB aggregation pipeline `$lookup` (join với `posts`) và `$group` theo `topics`.

### Thử thách 4.3 — Export Bookmark
Thêm endpoint `GET /bookmarks/export` trả về file CSV chứa tất cả bookmark kèm nội dung bài.

*Gợi ý:* Dùng `StreamingResponse` của FastAPI với `io.StringIO` và `csv.writer`.

### Thử thách 4.4 — Gợi Ý Bài Viết Tương Tự
Khi user bookmark một bài về topic X, gọi `GET /posts?topic=X&limit=5` để hiển thị sidebar "Bài tương tự".

*Gợi ý:* Tạo hook `useRelatedPosts(post_id)` trong `useApi.jsx`, lấy topics từ bài đã bookmark rồi query lại.

---

## Phụ Lục — Tra Cứu Nhanh

### Các Dependency FastAPI Hay Dùng

```python
from src.api.auth import get_current_user, get_current_admin_user

# Chỉ cần đăng nhập (bất kỳ role)
@router.get("/my-data")
async def my_endpoint(current_user: str = Depends(get_current_user)):
    ...

# Chỉ admin mới vào được
@router.delete("/admin/users/{uid}")
async def admin_delete(uid: str, _=Depends(get_current_admin_user)):
    ...
```

### Truy Cập MongoDB

```python
from src.db.mongo import get_db

db = get_db()

# Tìm một document
doc = db["posts"].find_one({"id": post_id})

# Tìm nhiều document có phân trang
docs = list(db["posts"].find({"topics": "Crypto"}).sort("created_at", -1).limit(20))

# Insert
db["bookmarks"].insert_one({"username": "alice", "post_id": "..."})

# Update
db["posts"].update_one({"id": pid}, {"$set": {"score": 1.5}})

# Xoá
db["bookmarks"].delete_one({"username": user, "post_id": pid})
```

### Tạo API Client trong Frontend

```javascript
// web/src/lib/api.jsx — pattern chuẩn

// GET có params
export async function fetchMyData({ topic, page = 1 }) {
  const params = new URLSearchParams({ ...(topic && { topic }), page });
  const res = await fetchWithAuth(`${API_BASE_URL}/my-endpoint?${params}`);
  if (!res.ok) throw new Error("Lỗi tải dữ liệu");
  return res.json();
}

// POST với body
export async function createMyData(payload) {
  const res = await fetchWithAuth(`${API_BASE_URL}/my-endpoint`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!res.ok) throw new Error("Lỗi tạo dữ liệu");
  return res.json();
}
```

### Tạo React Query Hook

```javascript
// web/src/hooks/useApi.jsx — pattern chuẩn

// Query (đọc dữ liệu)
export function useMyData(params) {
  return useQuery({
    queryKey: ['my-data', params],          // Cache key — thay đổi params → refetch tự động
    queryFn: () => fetchMyData(params),
    staleTime: 5 * 60 * 1000,              // Dữ liệu tươi trong 5 phút
  });
}

// Mutation (thay đổi dữ liệu)
export function useCreateMyData() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: createMyData,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['my-data'] }); // Làm mới cache
    },
  });
}
```

### Biến Môi Trường Quan Trọng (`.env`)

| Biến | Mô tả | Bắt buộc |
|---|---|---|
| `MONGO_URI` | Chuỗi kết nối MongoDB | ✅ |
| `DB_NAME` | Tên database (mặc định `newsbot`) | ✅ |
| `JWT_SECRET_KEY` | Key ký JWT — **phải đổi trên production** | ✅ |
| `TELEGRAM_API_ID` | API ID từ my.telegram.org | ✅ |
| `TELEGRAM_API_HASH` | API Hash từ my.telegram.org | ✅ |
| `TELEGRAM_SESSION_STRING` | Session string (tạo bằng `create_session.py`) | ✅ |
| `OPENAI_API_KEY` | Key OpenAI (bỏ trống → tắt AI features) | ⬜ |
| `APIFY_API_TOKEN` | Token Apify (cần cho X/Twitter) | ⬜ |
| `ALLOWED_ORIGINS` | CORS origins cho phép, phân cách bằng dấu phẩy | ⬜ |

---

## Tham Khảo Thêm

| Tài liệu | Mô tả |
|---|---|
| [docs/ARCHITECTURE.md](ARCHITECTURE.md) | Kiến trúc tổng thể, luồng dữ liệu, quyết định thiết kế |
| [docs/database_schema.md](database_schema.md) | Chi tiết schema MongoDB từng collection |
| [docs/system_overview.md](system_overview.md) | Cách chạy từng thành phần, biến môi trường |
| [README.md](../README.md) | Quick start, danh sách scripts |
| [FastAPI Docs](https://fastapi.tiangolo.com/) | Tham khảo framework backend |
| [TanStack Query](https://tanstack.com/query/latest) | Tham khảo thư viện data fetching frontend |
