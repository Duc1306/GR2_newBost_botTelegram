// Public API helpers – no authentication required
const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000';

/**
 * Fetch active hot topics list.
 * @returns {{ topics: Array, seeded: boolean }}
 */
export async function fetchHotTopics(signal) {
  const res = await fetch(`${API_BASE}/public/hot-topics`, { signal });
  if (!res.ok) throw new Error('Failed to fetch hot topics');
  return res.json();
}

/**
 * Fetch posts for a hot-topic slug, or all posts when slug === 'all'.
 * Returns { posts, total, topic?, skip, limit, ai_ranked? }
 */
export async function fetchTopicPosts(slug, skip = 0, limit = 20, aiRank = false, signal) {
  let url;
  if (slug === 'all') {
    const params = new URLSearchParams({ limit, skip });
    url = `${API_BASE}/public/posts?${params}`;
  } else {
    const endpoint = aiRank ? 'ai' : 'posts';
    const params = new URLSearchParams({ limit, skip });
    url = `${API_BASE}/public/hot-topics/${encodeURIComponent(slug)}/${endpoint}?${params}`;
  }

  const res = await fetch(url, { signal });
  if (!res.ok) throw new Error('Failed to fetch posts');
  return res.json();
}

/**
 * Fetch only posts that have external links, optionally filtered by topic.
 * Returns { posts: Array, total: number }
 */
export async function fetchArticlePosts(topic = '', skip = 0, limit = 20, q = '', signal, platform = '', dateFrom = '', dateTo = '', geo = '') {
  const params = new URLSearchParams({ limit, skip, link_only: 'true' });
  if (topic) params.set('topic', topic);
  if (q) params.set('q', q);
  if (platform && platform !== 'all') params.set('platform', platform);
  if (dateFrom) params.set('date_from', dateFrom);
  if (dateTo) params.set('date_to', dateTo);
  if (geo && geo !== 'all') params.set('geo', geo);
  const res = await fetch(`${API_BASE}/public/posts?${params}`, { signal });
  if (!res.ok) throw new Error('Failed to fetch article posts');
  return res.json();
}

/**
 * Search posts (public endpoint).
 */
export async function searchPublicPosts(q, limit = 20, skip = 0, signal, platform = '', dateFrom = '', dateTo = '') {
  const params = new URLSearchParams({ q, limit, skip });
  if (platform && platform !== 'all') params.set('platform', platform);
  if (dateFrom) params.set('date_from', dateFrom);
  if (dateTo) params.set('date_to', dateTo);
  const res = await fetch(`${API_BASE}/public/posts?${params}`, { signal });
  if (!res.ok) throw new Error('Search failed');
  return res.json();
}

/**
 * Search X (Twitter) posts.
 * - With query: triggers a live Apify fetch via /public/x/search, then returns results.
 *   Results are cached 5 min server-side so subsequent calls don't re-hit Apify.
 * - Without query: returns latest X posts from DB via /public/posts.
 */
export async function searchXPosts(q = '', skip = 0, limit = 20, signal) {
  if (q && q.trim()) {
    // Live fetch from Apify
    const params = new URLSearchParams({ q: q.trim(), limit, skip });
    const res = await fetch(`${API_BASE}/public/x/search?${params}`, { signal });
    if (!res.ok) throw new Error('Failed to fetch X posts');
    return res.json(); // { posts, total, live, q }
  }
  // No query — just show latest X posts from DB
  const params = new URLSearchParams({ platform: 'twitter', limit, skip });
  const res = await fetch(`${API_BASE}/public/posts?${params}`, { signal });
  if (!res.ok) throw new Error('Failed to fetch X posts');
  return res.json(); // { posts, total }
}

/**
 * Fetch hot news clusters (grouped by topic) for the last N hours.
 * @returns {{ clusters: Array, since: string, hours: number }}
 */
export async function fetchHotNewsClusters(hours = 24, signal) {
  const res = await fetch(`${API_BASE}/public/hotnews?hours=${hours}`, { signal });
  if (!res.ok) throw new Error('Failed to fetch hot news clusters');
  return res.json();
}

/**
 * Request an AI (OpenAI) summary for a hot-news cluster by slug.
 * Results are cached server-side for 30 minutes.
 * @returns {{ summary, key_points, sentiment, ai, post_count }}
 */
export async function fetchHotNewsSummary(slug, hours = 24, signal) {
  const res = await fetch(`${API_BASE}/public/hotnews/${encodeURIComponent(slug)}/summary?hours=${hours}`, {
    method: 'POST',
    signal,
  });
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.detail || `Không thể tải tóm tắt (${res.status})`);
  }
  return res.json();
}

/**
 * Fetch TTS audio (MP3) for a hot-news cluster.
 * Returns a Blob URL (revoke after use).
 */
export async function fetchHotNewsAudio(slug, hours = 24, signal) {
  const res = await fetch(
    `${API_BASE}/public/hotnews/${encodeURIComponent(slug)}/audio?hours=${hours}`,
    { signal },
  );
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.detail || 'Không thể tải audio');
  }
  const blob = await res.blob();
  return URL.createObjectURL(blob);
}

/**
 * Fetch distinct ML-classified topic categories from posts that have external links.
 * Used to populate the topic filter chips on the articles tab.
 * @returns {{ topics: Array<{ name, slug, count, color }> }}
 */
export async function fetchPostTopics(signal) {
  const res = await fetch(`${API_BASE}/public/post-topics`, { signal });
  if (!res.ok) throw new Error('Failed to fetch post topics');
  return res.json();
}

/**
 * Fetch daily post counts for the last N days.
 * @returns {{ daily: Array<{date, posts, topics, by_platform}>, days, total_posts, avg_per_day }}
 */
export async function fetchDailyStats(days = 30, signal) {
  const res = await fetch(`${API_BASE}/public/stats/daily?days=${days}`, { signal });
  if (!res.ok) throw new Error('Failed to fetch daily stats');
  return res.json();
}

/**
 * Fetch geographic distribution of posts for the last N days.
 * @returns {{ geo: Array<{region, count, percent, emoji, color}>, total, days, has_data }}
 */
export async function fetchGeoStats(days = 7, signal) {
  const res = await fetch(`${API_BASE}/public/stats/geo?days=${days}`, { signal });
  if (!res.ok) throw new Error('Failed to fetch geo stats');
  return res.json();
}

// ─── Auth helpers ─────────────────────────────────────────────────────────────

export function isLoggedIn() {
  return !!localStorage.getItem('auth_token');
}

function authHeaders() {
  const token = localStorage.getItem('auth_token');
  return token ? { Authorization: `Bearer ${token}` } : {};
}

// ─── Bookmark API (DB-based, requires login) ──────────────────────────────────

// In-memory cache of bookmarked post IDs so we don't call the API per card
let _bookmarkIdsCache = null;    // null = not loaded yet; [] = loaded (possibly empty)
let _bookmarkIdsPromise = null;  // in-flight promise — prevents stampede from simultaneous card mounts

export function invalidateBookmarkCache() {
  _bookmarkIdsCache = null;
  _bookmarkIdsPromise = null;
}

export async function fetchBookmarkIds(signal) {
  if (!isLoggedIn()) return new Set();
  if (_bookmarkIdsCache !== null) return new Set(_bookmarkIdsCache);
  // All concurrent callers share the same in-flight request instead of firing their own
  if (_bookmarkIdsPromise) return _bookmarkIdsPromise;

  _bookmarkIdsPromise = fetch(`${API_BASE}/user/bookmarks/ids`, { headers: authHeaders(), signal })
    .then(async (res) => {
      if (!res.ok) { _bookmarkIdsCache = []; return new Set(); }
      const data = await res.json();
      _bookmarkIdsCache = data.post_ids || [];
      return new Set(_bookmarkIdsCache);
    })
    .catch(() => {
      _bookmarkIdsCache = []; // stop retrying on any error
      return new Set();
    })
    .finally(() => {
      _bookmarkIdsPromise = null;
    });

  return _bookmarkIdsPromise;
}

export async function fetchBookmarks(signal) {
  if (!isLoggedIn()) return [];
  try {
    const res = await fetch(`${API_BASE}/user/bookmarks`, { headers: authHeaders(), signal });
    if (!res.ok) return [];
    const data = await res.json();
    return data.posts || [];
  } catch {
    return [];
  }
}

export async function addBookmark(postId) {
  if (!isLoggedIn()) return false;
  try {
    const res = await fetch(`${API_BASE}/user/bookmarks`, {
      method: 'POST',
      headers: { ...authHeaders(), 'Content-Type': 'application/json' },
      body: JSON.stringify({ post_id: postId }),
    });
    if (res.ok) {
      if (_bookmarkIdsCache !== null) _bookmarkIdsCache = [..._bookmarkIdsCache, postId];
    }
    return res.ok;
  } catch {
    return false;
  }
}

export async function removeBookmark(postId) {
  if (!isLoggedIn()) return false;
  try {
    const res = await fetch(`${API_BASE}/user/bookmarks/${encodeURIComponent(postId)}`, {
      method: 'DELETE',
      headers: authHeaders(),
    });
    if (res.ok && _bookmarkIdsCache !== null) {
      _bookmarkIdsCache = _bookmarkIdsCache.filter((id) => id !== postId);
    }
    return res.ok;
  } catch {
    return false;
  }
}

export async function fetchReadHistory(limit = 50, signal) {
  if (!isLoggedIn()) return [];
  try {
    const res = await fetch(`${API_BASE}/user/channels/read-history?limit=${limit}`, {
      headers: authHeaders(),
      signal,
    });
    if (!res.ok) return [];
    const data = await res.json();
    return Array.isArray(data) ? data : [];
  } catch {
    return [];
  }
}
