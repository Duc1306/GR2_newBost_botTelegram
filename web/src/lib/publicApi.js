// Public API helpers – no authentication required
const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000';

/**
 * Fetch active hot topics list.
 * @returns {{ topics: Array, seeded: boolean }}
 */
export async function fetchHotTopics() {
  const res = await fetch(`${API_BASE}/public/hot-topics`);
  if (!res.ok) throw new Error('Failed to fetch hot topics');
  return res.json();
}

/**
 * Fetch posts for a hot-topic slug, or all posts when slug === 'all'.
 * Returns { posts, total, topic?, skip, limit, ai_ranked? }
 */
export async function fetchTopicPosts(slug, skip = 0, limit = 20, aiRank = false) {
  let url;
  if (slug === 'all') {
    const params = new URLSearchParams({ limit, skip });
    url = `${API_BASE}/public/posts?${params}`;
  } else {
    const endpoint = aiRank ? 'ai' : 'posts';
    const params = new URLSearchParams({ limit, skip });
    url = `${API_BASE}/public/hot-topics/${encodeURIComponent(slug)}/${endpoint}?${params}`;
  }

  const res = await fetch(url);
  if (!res.ok) throw new Error('Failed to fetch posts');
  return res.json();
}

/**
 * Fetch only posts that have external links, optionally filtered by topic.
 * Returns { posts: Array, total: number }
 */
export async function fetchArticlePosts(topic = '', skip = 0, limit = 20, q = '') {
  const params = new URLSearchParams({ limit, skip, link_only: 'true' });
  if (topic) params.set('topic', topic);
  if (q) params.set('q', q);
  const res = await fetch(`${API_BASE}/public/posts?${params}`);
  if (!res.ok) throw new Error('Failed to fetch article posts');
  return res.json();
}

/**
 * Search posts (public endpoint).
 */
export async function searchPublicPosts(q, limit = 20, skip = 0) {
  const params = new URLSearchParams({ q, limit, skip });
  const res = await fetch(`${API_BASE}/public/posts?${params}`);
  if (!res.ok) throw new Error('Search failed');
  return res.json();
}

/**
 * Fetch hot news clusters (grouped by topic) for the last N hours.
 * @returns {{ clusters: Array, since: string, hours: number }}
 */
export async function fetchHotNewsClusters(hours = 48, signal) {
  const res = await fetch(`${API_BASE}/public/hotnews?hours=${hours}`, { signal });
  if (!res.ok) throw new Error('Failed to fetch hot news clusters');
  return res.json();
}

/**
 * Request an AI (OpenAI) summary for a hot-news cluster by slug.
 * Results are cached server-side for 30 minutes.
 * @returns {{ summary, key_points, sentiment, ai, post_count }}
 */
export async function fetchHotNewsSummary(slug, hours = 48) {
  const res = await fetch(`${API_BASE}/public/hotnews/${encodeURIComponent(slug)}/summary?hours=${hours}`, {
    method: 'POST',
  });
  if (!res.ok) throw new Error('Failed to fetch summary');
  return res.json();
}

/**
 * Fetch distinct ML-classified topic categories from posts that have external links.
 * Used to populate the topic filter chips on the articles tab.
 * @returns {{ topics: Array<{ name, slug, count, color }> }}
 */
export async function fetchPostTopics() {
  const res = await fetch(`${API_BASE}/public/post-topics`);
  if (!res.ok) throw new Error('Failed to fetch post topics');
  return res.json();
}
