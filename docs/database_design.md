# Database Schema Design - Multi-Platform News Aggregation System

## 📊 ERD (Entity Relationship Diagram)

```
┌─────────────────────┐       ┌──────────────────────┐
│     sources         │       │       posts          │
│─────────────────────│       │──────────────────────│
│ _id: ObjectId       │◄──────│ _id: ObjectId        │
│ platform: String    │  1:N  │ platform: String     │
│ source_id: String   │       │ source: String       │
│ source_type: String │       │ source_id: String    │
│ name: String        │       │ author: String?      │
│ username: String?   │       │ text: String         │
│ url: String         │       │ text_cleaned: String │
│ is_active: Boolean  │       │ lang: String?        │
│ metadata: Object    │       │ links: Array         │
│ created_at: Date    │       │ media: Array         │
│ updated_at: Date    │       │ created_at: Date     │
└─────────────────────┘       │ fetched_at: Date     │
                              │ dedupe_key: String   │
                              │ topics: Array        │  
                              │ score: Float         │
                              │ full_article: Object?│
                              │ topic_predictions: [ │──┐
                              │   {                  │  │
                              │     topic: String,   │  │
                              │     confidence: Float│  │
                              │     model_version: S │  │
                              │     predicted_at: D  │  │
                              │   }                  │  │
                              │ ]                    │  │
                              └──────────────────────┘  │
                                                        │
┌──────────────────────┐                               │
│   topic_stats        │                               │
│──────────────────────│                               │
│ _id: ObjectId        │◄──────────────────────────────┘
│ topic: String        │
│ date: Date           │  (Daily aggregated)
│ platform: String     │
│ post_count: Int      │
│ avg_confidence: Float│
│ top_keywords: Array  │
│ trend_score: Float   │
│ created_at: Date     │
└──────────────────────┘

┌──────────────────────┐
│   keyword_trends     │
│──────────────────────│
│ _id: ObjectId        │
│ keyword: String      │
│ date: Date           │  (Daily aggregated)
│ platforms: Object {  │
│   telegram: Int,     │
│   twitter: Int       │
│ }                    │
│ topics: Object {     │
│   Crypto: Int,       │
│   Chính trị: Int,... │
│ }                    │
│ total_count: Int     │
│ trend_velocity: Float│  (Growth rate)
│ related_keywords: [] │
│ created_at: Date     │
└──────────────────────┘

┌──────────────────────┐
│   ml_model_versions  │
│──────────────────────│
│ _id: ObjectId        │
│ version: String      │
│ model_type: String   │  (svm, bert, etc.)
│ accuracy: Float      │
│ f1_score: Float      │
│ training_samples: Int│
│ topics: Array        │
│ is_active: Boolean   │
│ trained_at: Date     │
│ model_path: String   │
└──────────────────────┘
```

## 📋 Collections Schema

### 1. **posts** - Main collection for all posts
```javascript
{
  _id: ObjectId("..."),
  
  // Platform & Source Info
  platform: "telegram" | "twitter",
  source: "telegram:channel_username",  // Composite key
  source_id: "3195",                    // Platform-specific ID
  author: "@username",                  // Optional
  
  // Content
  text: "Original raw text...",
  text_cleaned: "Cleaned preprocessed text...",  // NEW
  lang: "vi" | "en" | null,
  links: ["https://..."],
  media: [
    {
      type: "photo" | "video" | "gif" | "document",
      url: "https://...",
      thumbnail: "https://..."  // Optional
    }
  ],
  
  // Timestamps
  created_at: ISODate("2024-08-07T19:43:14.000Z"),  // Post creation time
  fetched_at: ISODate("2026-01-02T05:19:06.993Z"),  // When we fetched it
  
  // Deduplication
  dedupe_key: "bafe881de93da1095249a96d84d90338",  // SHA256 hash
  
  // Topic Classification (Legacy - Rule-based)
  topics: ["Crypto", "Kinh tế"],  // For backward compatibility
  
  // Topic Predictions (NEW - ML-based with metadata)
  topic_predictions: [
    {
      topic: "Crypto",
      confidence: 0.95,
      model_version: "svm_v1.0_20260102",
      predicted_at: ISODate("2026-01-02T05:20:00.000Z"),
      method: "ml" | "rule-based" | "manual"
    },
    {
      topic: "Kinh tế",
      confidence: 0.78,
      model_version: "svm_v1.0_20260102",
      predicted_at: ISODate("2026-01-02T05:20:00.000Z"),
      method: "ml"
    }
  ],
  
  // Scoring & Quality
  score: 0.0,  // Engagement/quality score
  
  // Full Article (if scraped)
  full_article: {
    title: "Article title",
    content: "Full article content...",
    author: "Author name",
    published_at: ISODate("..."),
    scraped_at: ISODate("...")
  }
}
```

**Indexes:**
```javascript
// Unique constraint - prevent duplicates
db.posts.createIndex(
  { "platform": 1, "source": 1, "source_id": 1 },
  { unique: true, name: "idx_platform_source_id_unique" }
)

// Deduplication check
db.posts.createIndex(
  { "dedupe_key": 1 },
  { unique: true, name: "idx_dedupe_key_unique" }
)

// Query by platform & date
db.posts.createIndex(
  { "platform": 1, "created_at": -1 },
  { name: "idx_platform_created" }
)

// Query by topics (array field)
db.posts.createIndex(
  { "topics": 1, "created_at": -1 },
  { name: "idx_topics_created" }
)

// Query by topic predictions
db.posts.createIndex(
  { "topic_predictions.topic": 1, "created_at": -1 },
  { name: "idx_topic_predictions_created" }
)

// Filter by language
db.posts.createIndex(
  { "lang": 1, "platform": 1 },
  { name: "idx_lang_platform" }
)

// Text search
db.posts.createIndex(
  { "text": "text", "text_cleaned": "text" },
  { name: "idx_fulltext_search" }
)

// Query for retraining - find posts with topics but no ML predictions
db.posts.createIndex(
  { "topics": 1, "topic_predictions": 1 },
  { 
    name: "idx_topics_predictions_retrain",
    partialFilterExpression: { 
      "topics": { $exists: true, $ne: [] }
    }
  }
)
```

---

### 2. **sources** - Source metadata (channels, users, groups)
```javascript
{
  _id: ObjectId("..."),
  
  // Platform & Identification
  platform: "telegram" | "twitter",
  source_type: "channel" | "group" | "user" | "hashtag",
  source_id: "@channel_username" | "user_id",
  
  // Metadata
  name: "Channel Display Name",
  username: "@channel_username",
  url: "https://t.me/channel_username",
  description: "Channel description",
  
  // Stats
  subscriber_count: 50000,
  post_count: 1234,  // Total posts fetched
  
  // Configuration
  is_active: true,  // Whether to fetch from this source
  fetch_frequency: "hourly" | "daily" | "manual",
  
  // Custom metadata per platform
  metadata: {
    telegram: {
      chat_id: -1001234567890,
      access_hash: "...",
      is_verified: true
    },
    twitter: {
      user_id: "1234567890",
      is_verified: true
    }
  },
  
  // Timestamps
  created_at: ISODate("..."),
  updated_at: ISODate("..."),
  last_fetched_at: ISODate("...")
}
```

**Indexes:**
```javascript
// Unique constraint per platform
db.sources.createIndex(
  { "platform": 1, "source_id": 1 },
  { unique: true, name: "idx_platform_source_id_unique" }
)

// Query active sources
db.sources.createIndex(
  { "is_active": 1, "platform": 1 },
  { name: "idx_active_platform" }
)

// Query by type
db.sources.createIndex(
  { "source_type": 1, "platform": 1 },
  { name: "idx_type_platform" }
)
```

---

### 3. **topic_stats** - Daily aggregated topic statistics
```javascript
{
  _id: ObjectId("..."),
  
  // Dimensions
  topic: "Crypto",
  date: ISODate("2026-01-02T00:00:00.000Z"),  // Date only (start of day UTC)
  platform: "telegram" | "twitter" | "all",
  
  // Metrics
  post_count: 1234,
  avg_confidence: 0.87,  // Average ML confidence
  avg_score: 12.5,       // Average engagement score
  
  // Top keywords in this topic today
  top_keywords: [
    { keyword: "bitcoin", count: 456 },
    { keyword: "btc", count: 389 },
    { keyword: "ethereum", count: 234 }
  ],
  
  // Trend analysis
  trend_score: 1.23,     // Growth vs yesterday (1.0 = no change)
  trend_direction: "up" | "down" | "stable",
  
  // Breakdown by source
  top_sources: [
    { source: "telegram:crypto_news", count: 123 },
    { source: "telegram:bitcoin_updates", count: 98 }
  ],
  
  // Timestamps
  created_at: ISODate("..."),
  updated_at: ISODate("...")
}
```

**Indexes:**
```javascript
// Unique constraint - one record per topic/date/platform
db.topic_stats.createIndex(
  { "topic": 1, "date": 1, "platform": 1 },
  { unique: true, name: "idx_topic_date_platform_unique" }
)

// Query by date range
db.topic_stats.createIndex(
  { "date": -1, "topic": 1 },
  { name: "idx_date_topic" }
)

// Query trending topics
db.topic_stats.createIndex(
  { "trend_score": -1, "date": -1 },
  { name: "idx_trending" }
)
```

---

### 4. **keyword_trends** - Daily keyword frequency tracking
```javascript
{
  _id: ObjectId("..."),
  
  // Dimensions
  keyword: "bitcoin",
  keyword_normalized: "bitcoin",  // Lowercase, cleaned
  date: ISODate("2026-01-02T00:00:00.000Z"),
  
  // Platform breakdown
  platforms: {
    telegram: 456,
    twitter: 234,
    total: 690
  },
  
  // Topic breakdown
  topics: {
    "Crypto": 567,
    "Kinh tế": 123
  },
  
  // Metrics
  total_count: 690,
  unique_posts: 650,  // Deduplicated
  
  // Trend analysis
  trend_velocity: 2.5,  // Growth rate (today vs 7-day avg)
  change_from_yesterday: 120,  // Absolute change
  change_pct: 0.21,            // Percentage change
  
  // Context
  related_keywords: ["btc", "cryptocurrency", "blockchain"],
  sentiment_avg: 0.65,  // Optional: average sentiment score
  
  // Timestamps
  created_at: ISODate("..."),
  updated_at: ISODate("...")
}
```

**Indexes:**
```javascript
// Unique constraint
db.keyword_trends.createIndex(
  { "keyword_normalized": 1, "date": 1 },
  { unique: true, name: "idx_keyword_date_unique" }
)

// Query trending keywords
db.keyword_trends.createIndex(
  { "trend_velocity": -1, "date": -1 },
  { name: "idx_trending_velocity" }
)

// Query by date range
db.keyword_trends.createIndex(
  { "date": -1, "total_count": -1 },
  { name: "idx_date_count" }
)

// Search keywords
db.keyword_trends.createIndex(
  { "keyword_normalized": 1 },
  { name: "idx_keyword" }
)
```

---

### 5. **ml_model_versions** - Track ML model versions
```javascript
{
  _id: ObjectId("..."),
  
  // Model info
  version: "svm_v1.0_20260102",
  model_type: "svm" | "bert" | "lstm" | "ensemble",
  
  // Performance metrics
  accuracy: 0.9035,
  f1_score: 0.89,
  precision: 0.90,
  recall: 0.90,
  
  // Training info
  training_samples: 10000,
  topics: ["Crypto", "Kinh tế", "Công nghệ", ...],
  
  // Status
  is_active: true,  // Currently used for predictions
  
  // Metadata
  trained_at: ISODate("2026-01-02T05:30:00.000Z"),
  model_path: "models/topic_classifier_svm.pkl",
  training_config: {
    test_size: 0.2,
    max_features: 5000,
    ngram_range: [1, 2]
  }
}
```

**Indexes:**
```javascript
// Query active model
db.ml_model_versions.createIndex(
  { "is_active": 1, "trained_at": -1 },
  { name: "idx_active_trained" }
)

// Version lookup
db.ml_model_versions.createIndex(
  { "version": 1 },
  { unique: true, name: "idx_version_unique" }
)
```

---

## 🔗 Relationships

### 1. **sources → posts** (1:N)
- One source có thể có nhiều posts
- Query: `db.posts.find({ source: "telegram:crypto_news" })`

### 2. **posts → topic_predictions** (1:N embedded)
- Mỗi post có nhiều topic predictions (embedded array)
- Lưu history của tất cả predictions (rule-based + ML versions)

### 3. **posts → topic_stats** (Aggregation)
- Aggregate từ posts hàng ngày để tính stats
- Không có foreign key trực tiếp

### 4. **posts → keyword_trends** (Aggregation)
- Extract keywords từ posts và aggregate
- Không có foreign key trực tiếp

---

## 🚀 Query Patterns & Use Cases

### Dashboard Queries:

**1. Get posts by topic with pagination:**
```javascript
db.posts.find({
  "topic_predictions.topic": "Crypto",
  "topic_predictions.confidence": { $gte: 0.5 }
})
.sort({ created_at: -1 })
.limit(20)
```

**2. Get trending topics today:**
```javascript
db.topic_stats.find({
  date: ISODate("2026-01-02T00:00:00.000Z"),
  platform: "all"
})
.sort({ trend_score: -1 })
.limit(10)
```

**3. Get keyword trends for past 7 days:**
```javascript
db.keyword_trends.find({
  keyword_normalized: "bitcoin",
  date: { 
    $gte: ISODate("2025-12-26T00:00:00.000Z"),
    $lte: ISODate("2026-01-02T00:00:00.000Z")
  }
})
.sort({ date: 1 })
```

**4. Find posts needing ML prediction:**
```javascript
db.posts.find({
  topics: { $exists: true, $ne: [] },
  $or: [
    { topic_predictions: { $exists: false } },
    { topic_predictions: { $size: 0 } }
  ]
}).limit(1000)
```

---

## ⚠️ Data Integrity Rules

### Unique Constraints:
1. **posts**: `(platform, source, source_id)` - Prevent duplicate posts
2. **posts**: `dedupe_key` - Content-based deduplication
3. **sources**: `(platform, source_id)` - Unique source per platform
4. **topic_stats**: `(topic, date, platform)` - One stat per day
5. **keyword_trends**: `(keyword_normalized, date)` - One trend per day

### Cascading Rules:
- **Soft delete**: Set `is_active: false` thay vì xóa thật
- **Keep history**: Không xóa old predictions, chỉ add new
- **Archive**: Move old posts (>6 months) sang archive collection

---

## 📈 Performance Considerations

### Sharding Strategy (if needed):
- **posts**: Shard by `created_at` (range-based) hoặc `platform` (hash-based)
- **topic_stats**: Shard by `date` (range-based)

### TTL Indexes (auto-cleanup):
```javascript
// Auto-delete posts older than 1 year
db.posts.createIndex(
  { "created_at": 1 },
  { expireAfterSeconds: 31536000, name: "idx_ttl_posts" }
)

// Auto-delete stats older than 2 years
db.topic_stats.createIndex(
  { "created_at": 1 },
  { expireAfterSeconds: 63072000, name: "idx_ttl_stats" }
)
```

### Read/Write Optimization:
- **Write-heavy**: posts collection (continuous ingestion)
- **Read-heavy**: topic_stats, keyword_trends (dashboard queries)
- **Caching**: Cache aggregated stats for 5-10 minutes

---

## 🛠 Migration Path

### Phase 1: Extend existing schema
1. ✅ Add `platform` field (default "telegram")
2. ✅ Add `text_cleaned` field
3. ✅ Add `topic_predictions` array (keep `topics` for backward compat)
4. ✅ Create new indexes

### Phase 2: New collections
1. ✅ Create `sources` collection
2. ✅ Create `topic_stats` collection
3. ✅ Create `keyword_trends` collection
4. ✅ Create `ml_model_versions` collection

### Phase 3: Data backfill
1. ⏳ Backfill `platform` = "telegram" for existing posts
2. ⏳ Backfill `text_cleaned` from `text`
3. ⏳ Migrate `topics` → `topic_predictions` with method="rule-based"
4. ⏳ Generate `sources` from existing posts
5. ⏳ Aggregate historical `topic_stats`

---

## 📦 Estimated Storage

Với 47K posts hiện tại:
- **posts**: ~100 MB (2KB/post average)
- **sources**: ~1 MB (100 sources)
- **topic_stats**: ~5 MB (365 days × 10 topics × 2 platforms)
- **keyword_trends**: ~50 MB (top 1000 keywords × 365 days)
- **Total**: ~156 MB

Với 1M posts (production):
- **posts**: ~2 GB
- **topic_stats**: ~10 MB
- **keyword_trends**: ~100 MB
- **Total**: ~2.2 GB
