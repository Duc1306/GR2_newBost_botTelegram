# Hướng dẫn Deploy

## Kiến trúc
- **Frontend** (React + Vite) → **Vercel**
- **Backend** (FastAPI) → **Render**
- **Database** (MongoDB) → **MongoDB Atlas** (miễn phí)

---

## Bước 1: Chuẩn bị MongoDB Atlas

1. Tạo tài khoản tại https://cloud.mongodb.com
2. Tạo cluster miễn phí (M0 Free Tier)
3. Tạo database user (username/password)
4. Whitelist IP: chọn **"Allow access from anywhere"** (`0.0.0.0/0`)
5. Lấy **Connection String** dạng:
   ```
   mongodb+srv://<user>:<password>@cluster0.xxxxx.mongodb.net/newsbot?retryWrites=true&w=majority
   ```

---

## Bước 2: Deploy Backend lên Render

1. Đẩy code lên GitHub (nếu chưa)
2. Vào https://dashboard.render.com → **New Web Service**
3. Kết nối repository GitHub
4. Render sẽ tự detect `render.yaml` → bấm **Apply**
5. Điền các **Environment Variables** sau trong Render dashboard:
   | Key | Value |
   |-----|-------|
   | `MONGO_URI` | Connection string MongoDB Atlas |
   | `ADMIN_USERNAME` | Tên đăng nhập admin |
   | `ADMIN_PASSWORD` | Mật khẩu admin (mạnh) |
   | `USER_USERNAME` | Tên đăng nhập user thường |
   | `USER_PASSWORD` | Mật khẩu user thường |
   | `ALLOWED_ORIGINS` | URL Vercel (điền sau bước 3) |
   | `TELEGRAM_API_ID` | (nếu dùng) |
   | `TELEGRAM_API_HASH` | (nếu dùng) |
   | `OPENAI_API_KEY` | (nếu dùng AI features) |
6. Deploy xong → lấy URL dạng `https://newsbot-api.onrender.com`

---

## Bước 3: Deploy Frontend lên Vercel

1. Vào https://vercel.com → **Add New Project**
2. Import repository GitHub
3. Cấu hình **Project Settings**:
   - **Root Directory**: `web`
   - **Framework Preset**: Vite (tự detect)
   - **Build Command**: `npm run build`
   - **Output Directory**: `dist`
4. Thêm **Environment Variable**:
   | Key | Value |
   |-----|-------|
   | `VITE_API_URL` | URL backend Render từ bước 2 |
5. Bấm **Deploy** → lấy URL dạng `https://newsbot-web.vercel.app`

---

## Bước 4: Cập nhật CORS trên Render

Sau khi có URL Vercel, quay lại Render dashboard:
- Cập nhật `ALLOWED_ORIGINS` = `https://newsbot-web.vercel.app`
- Nếu có custom domain, thêm cách nhau bằng dấu phẩy:
  `https://newsbot-web.vercel.app,https://yourdomain.com`
- Bấm **Save** → Render sẽ tự redeploy

---

## Lưu ý quan trọng

- File `web/.env.production` chỉ là **template** — thực tế nên set `VITE_API_URL` trong Vercel dashboard để bảo mật hơn
- Render free tier sẽ **spin down sau 15 phút** không có traffic → request đầu tiên có thể chậm ~30s
- Đổi `JWT_SECRET_KEY` thành giá trị ngẫu nhiên (Render dashboard → `JWT_SECRET_KEY` → **Generate** hoặc tự tạo)
