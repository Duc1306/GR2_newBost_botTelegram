# NewsBot Web Frontend

React 18 frontend cho NewsBot - Tổng hợp tin tức từ Telegram.

## Cài đặt

```bash
npm install
```

## Cấu hình

Tạo file `.env`:

```
REACT_APP_API_URL=http://localhost:8000
```

## Chạy Development Server

```bash
npm start
```

Mở [http://localhost:3000](http://localhost:3000)

## Build Production

```bash
npm run build
```

## Tech Stack

- React 18
- Material-UI (MUI)
- date-fns
- Emotion (CSS-in-JS)

## Features

- ✅ Responsive Material Design
- ✅ Filter theo chủ đề và ngôn ngữ
- ✅ Tìm kiếm bài viết
- ✅ Pagination
- ✅ Click tiêu đề để mở link gốc
- ✅ Thống kê realtime

## Structure

```
src/
├── components/
│   ├── PostCard.js       # Card hiển thị bài viết
│   ├── FilterSidebar.js  # Sidebar filters
│   └── Pagination.js     # Pagination component
├── lib/
│   └── api.js            # API client
├── App.js                # Main app
├── index.js              # Entry point
└── index.css             # Global styles
```
