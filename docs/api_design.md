# REST API Design - Social Media Analytics Dashboard

## 📋 API Overview

**Base URL:** `http://localhost:8000`  
**Framework:** FastAPI (Python)  
**Database:** MongoDB  
**Auth:** None (internal use)

---

## 🎯 Core Endpoints

### 1. Posts & Content

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/posts` | List posts with filters |
| GET | `/posts/{id}` | Get single post details |
| GET | `/posts/count` | Count posts by filter |
| POST | `/posts/search` | Advanced search with text/date range |

### 2. Topics & Classification

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/topics` | List all topics with counts |
| GET | `/topics/{topic}/posts` | Get posts by topic |
| GET | `/topics/trending` | Trending topics (7 days) |
| GET | `/topics/stats` | Topic statistics over time |

### 3. Analytics & Trends

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/analytics/trends` | Topic trends over time |
| GET | `/analytics/keywords` | Top keywords by date range |
| GET | `/analytics/keywords/trending` | Trending keywords |
| GET | `/analytics/comparison` | Compare platforms (Telegram vs Twitter) |
| GET | `/analytics/timeline` | Post volume timeline |

### 4. Statistics

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/stats` | General statistics |
| GET | `/stats/sources` | Source breakdown |
| GET | `/stats/daily` | Daily aggregated stats |

---

## 📖 API Specifications

### 1.1 GET `/posts`

**Description:** Get paginated posts with filters

**Query Parameters:**
```typescript
{
  platform?: "telegram" | "twitter" | "all"  // Default: "all"
  topic?: string                             // Filter by topic
  source?: string                            // Specific source (channel/user)
  lang?: "vi" | "en"                         // Language filter
  date_from?: string                         // ISO datetime (YYYY-MM-DD)
  date_to?: string                           // ISO datetime
  has_links?: boolean                        // Only posts with external links
  has_media?: boolean                        // Only posts with media
  min_confidence?: number                    // ML confidence threshold (0-1)
  limit?: number                             // Default: 20, Max: 100
  skip?: number                              // Pagination offset
  sort?: "created_at" | "score" | "confidence" // Default: "created_at"
  order?: "asc" | "desc"                     // Default: "desc"
}
```

**Response:**
```json
{
  "data": [
    {
      "id": "telegram:channel:3195",
      "platform": "telegram",
      "source": "telegram:crypto_news",
      "source_id": "3195",
      "text": "Bitcoin surges to new high...",
      "text_cleaned": "bitcoin surge new high",
      "lang": "en",
      "created_at": "2024-08-07T19:43:14Z",
      "fetched_at": "2026-01-02T05:19:06Z",
      "links": ["https://example.com/article"],
      "media": [
        {
          "type": "photo",
          "url": "https://...",
          "thumbnail": "https://..."
        }
      ],
      "topics": ["Crypto", "Kinh tế"],
      "topic_predictions": [
        {
          "topic": "Crypto",
          "confidence": 0.95,
          "model_version": "svm_v1.0_20260102",
          "predicted_at": "2026-01-02T05:20:00Z",
          "method": "ml"
        }
      ],
      "score": 0.0
    }
  ],
  "total": 46975,
  "limit": 20,
  "skip": 0,
  "has_more": true
}
```

---

### 1.2 POST `/posts/search`

**Description:** Advanced search with full-text and filters

**Request Body:**
```json
{
  "query": "bitcoin ethereum",           // Text search
  "platforms": ["telegram", "twitter"],  // Optional
  "topics": ["Crypto", "Công nghệ"],     // Optional
  "date_from": "2025-12-01",
  "date_to": "2026-01-02",
  "min_confidence": 0.7,
  "limit": 50
}
```

**Response:** Same as GET `/posts`

---

### 2.1 GET `/topics`

**Description:** Get all topics with post counts

**Query Parameters:**
```typescript
{
  platform?: "telegram" | "twitter" | "all"  // Default: "all"
  min_posts?: number                         // Filter topics with >= N posts
  sort?: "count" | "name"                    // Default: "count"
}
```

**Response:**
```json
{
  "data": [
    {
      "topic": "Crypto",
      "count": 9606,
      "percentage": 20.45,
      "avg_confidence": 0.92,
      "platforms": {
        "telegram": 9500,
        "twitter": 106
      }
    },
    {
      "topic": "Kinh tế",
      "count": 6968,
      "percentage": 14.83,
      "avg_confidence": 0.87,
      "platforms": {
        "telegram": 6968,
        "twitter": 0
      }
    }
  ],
  "total_topics": 10,
  "total_posts": 46975
}
```

---

### 2.2 GET `/topics/trending`

**Description:** Get trending topics (rising in popularity)

**Query Parameters:**
```typescript
{
  days?: number        // Time window (default: 7)
  platform?: string    // Filter by platform
  limit?: number       // Top N topics (default: 10)
}
```

**Response:**
```json
{
  "data": [
    {
      "topic": "Chính trị",
      "current_count": 350,
      "previous_count": 180,
      "growth_rate": 0.94,          // 94% increase
      "trend_direction": "up",
      "trend_score": 1.94,
      "avg_confidence": 0.89
    }
  ],
  "period": {
    "from": "2025-12-26",
    "to": "2026-01-02",
    "days": 7
  }
}
```

---

### 2.3 GET `/topics/stats`

**Description:** Topic statistics over time (for charts)

**Query Parameters:**
```typescript
{
  topics?: string[]     // Specific topics (default: all)
  date_from: string     // Required
  date_to: string       // Required
  platform?: string
  granularity?: "day" | "week" | "month"  // Default: "day"
}
```

**Response:**
```json
{
  "data": {
    "Crypto": [
      {
        "date": "2026-01-01",
        "count": 120,
        "avg_confidence": 0.92,
        "trend_score": 1.15
      },
      {
        "date": "2026-01-02",
        "count": 135,
        "avg_confidence": 0.93,
        "trend_score": 1.23
      }
    ],
    "Chính trị": [...]
  },
  "period": {
    "from": "2026-01-01",
    "to": "2026-01-02"
  }
}
```

---

### 3.1 GET `/analytics/trends`

**Description:** Multi-topic trend analysis

**Query Parameters:**
```typescript
{
  topics?: string[]     // Compare specific topics
  days?: number         // Time window (default: 30)
  platform?: string
}
```

**Response:**
```json
{
  "trends": [
    {
      "topic": "Crypto",
      "timeline": [
        {"date": "2025-12-01", "count": 145, "trend_velocity": 1.2},
        {"date": "2025-12-02", "count": 156, "trend_velocity": 1.08}
      ],
      "summary": {
        "total_posts": 4350,
        "avg_daily": 145,
        "peak_date": "2025-12-15",
        "peak_count": 230,
        "overall_trend": "up"
      }
    }
  ],
  "period": {
    "from": "2025-12-01",
    "to": "2026-01-01",
    "days": 30
  }
}
```

---

### 3.2 GET `/analytics/keywords`

**Description:** Top keywords by frequency

**Query Parameters:**
```typescript
{
  date_from: string     // Required
  date_to: string       // Required
  topic?: string        // Filter by topic
  platform?: string
  limit?: number        // Default: 50
  min_count?: number    // Minimum frequency
}
```

**Response:**
```json
{
  "keywords": [
    {
      "keyword": "bitcoin",
      "count": 1245,
      "unique_posts": 1180,
      "platforms": {
        "telegram": 1100,
        "twitter": 145
      },
      "topics": {
        "Crypto": 1000,
        "Kinh tế": 245
      },
      "trend_velocity": 1.45,
      "change_from_yesterday": 120,
      "change_pct": 0.11
    }
  ],
  "total": 50,
  "period": {
    "from": "2025-12-26",
    "to": "2026-01-02"
  }
}
```

---

### 3.3 GET `/analytics/keywords/trending`

**Description:** Trending keywords (fastest growing)

**Query Parameters:**
```typescript
{
  days?: number         // Time window (default: 7)
  limit?: number        // Top N (default: 20)
  min_velocity?: number // Min trend velocity (default: 1.5)
}
```

**Response:**
```json
{
  "keywords": [
    {
      "keyword": "trump",
      "current_count": 450,
      "previous_avg": 120,
      "trend_velocity": 3.75,      // 375% growth
      "trend_direction": "up",
      "related_topics": ["Chính trị"],
      "related_keywords": ["election", "president", "biden"]
    }
  ],
  "period": {
    "from": "2025-12-26",
    "to": "2026-01-02",
    "days": 7
  }
}
```

---

### 3.4 GET `/analytics/comparison`

**Description:** Compare platforms (Telegram vs Twitter)

**Query Parameters:**
```typescript
{
  date_from: string     // Required
  date_to: string       // Required
  metric?: "volume" | "topics" | "keywords"  // Default: "volume"
}
```

**Response:**
```json
{
  "comparison": {
    "telegram": {
      "total_posts": 45000,
      "avg_daily": 1500,
      "top_topics": [
        {"topic": "Crypto", "count": 9000},
        {"topic": "Chính trị", "count": 5000}
      ],
      "top_keywords": [
        {"keyword": "bitcoin", "count": 1200}
      ]
    },
    "twitter": {
      "total_posts": 2000,
      "avg_daily": 67,
      "top_topics": [
        {"topic": "Công nghệ", "count": 800}
      ],
      "top_keywords": [
        {"keyword": "ai", "count": 350}
      ]
    }
  },
  "period": {
    "from": "2025-12-01",
    "to": "2026-01-01"
  }
}
```

---

### 3.5 GET `/analytics/timeline`

**Description:** Post volume timeline (for line charts)

**Query Parameters:**
```typescript
{
  date_from: string
  date_to: string
  platform?: string
  topic?: string
  granularity?: "hour" | "day" | "week"  // Default: "day"
}
```

**Response:**
```json
{
  "timeline": [
    {
      "date": "2026-01-01T00:00:00Z",
      "count": 1580,
      "by_platform": {
        "telegram": 1500,
        "twitter": 80
      },
      "by_topic": {
        "Crypto": 450,
        "Chính trị": 320
      }
    }
  ],
  "summary": {
    "total_posts": 45000,
    "avg_per_period": 1500,
    "peak_date": "2025-12-15",
    "peak_count": 2300
  }
}
```

---

### 4.1 GET `/stats`

**Description:** General statistics

**Response:**
```json
{
  "overview": {
    "total_posts": 46975,
    "total_sources": 15,
    "total_topics": 10,
    "date_range": {
      "earliest": "2024-08-07T19:43:14Z",
      "latest": "2026-01-02T05:19:06Z"
    }
  },
  "by_platform": {
    "telegram": 45000,
    "twitter": 1975
  },
  "by_language": {
    "en": 28500,
    "vi": 18475
  },
  "ml_stats": {
    "posts_with_predictions": 26417,
    "avg_confidence": 0.87,
    "active_model": "svm_v1.0_20260102"
  }
}
```

---

### 4.2 GET `/stats/sources`

**Description:** Source breakdown

**Query Parameters:**
```typescript
{
  platform?: string
  sort?: "count" | "name"  // Default: "count"
  limit?: number           // Default: 20
}
```

**Response:**
```json
{
  "sources": [
    {
      "source_id": "@crypto_news",
      "platform": "telegram",
      "source_type": "channel",
      "name": "Crypto News",
      "post_count": 3450,
      "is_active": true,
      "last_fetched_at": "2026-01-02T05:00:00Z"
    }
  ],
  "total": 15
}
```

---

### 4.3 GET `/stats/daily`

**Description:** Daily aggregated statistics

**Query Parameters:**
```typescript
{
  date_from: string
  date_to: string
  platform?: string
}
```

**Response:**
```json
{
  "daily_stats": [
    {
      "date": "2026-01-01",
      "total_posts": 1580,
      "by_platform": {"telegram": 1500, "twitter": 80},
      "by_topic": {"Crypto": 450, "Chính trị": 320},
      "top_keywords": [
        {"keyword": "bitcoin", "count": 125}
      ]
    }
  ]
}
```

---

## 🔧 Implementation Notes

### Technology Stack
- **Backend:** FastAPI (Python 3.12)
- **Database:** MongoDB
- **Validation:** Pydantic v2
- **CORS:** Enabled for localhost:3000

### Performance Considerations
1. **Caching:** Redis for frequently accessed endpoints (5-10 min TTL)
2. **Pagination:** Max 100 items per request
3. **Indexes:** All time-based queries use indexed fields
4. **Aggregation:** Pre-computed stats in topic_stats/keyword_trends collections

### Error Responses
```json
{
  "detail": "Error message",
  "error_code": "INVALID_DATE_RANGE",
  "timestamp": "2026-01-02T05:30:00Z"
}
```

**Common Error Codes:**
- `400` - Invalid parameters
- `404` - Resource not found
- `422` - Validation error
- `500` - Internal server error

---

## 📊 Dashboard Priority Endpoints

For MVP dashboard, implement in this order:

1. **Overview:**
   - `GET /stats` - General statistics
   - `GET /topics` - Topic distribution

2. **Main Content:**
   - `GET /posts` - Post list with filters
   - `GET /topics/trending` - Trending topics

3. **Analytics:**
   - `GET /analytics/timeline` - Volume chart
   - `GET /analytics/keywords` - Word cloud
   - `GET /topics/stats` - Topic trends chart

4. **Advanced:**
   - `GET /analytics/comparison` - Platform comparison
   - `GET /analytics/keywords/trending` - Trending keywords
