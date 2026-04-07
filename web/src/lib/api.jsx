// API utilities for fetching data from FastAPI backend
const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

// Auth token storage
let authToken = null;

// Set auth token (called from AuthContext after login)
export function setAuthToken(token) {
  authToken = token;
}

// Get auth token
export function getAuthToken() {
  return authToken || localStorage.getItem('auth_token');
}

// Create headers with auth token
function createHeaders(extraHeaders = {}) {
  const headers = {
    'Cache-Control': 'no-cache',
    ...extraHeaders
  };
  
  const token = getAuthToken();
  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }
  
  return headers;
}

// Wrapper for fetch with auth
async function fetchWithAuth(url, options = {}) {
  const headers = createHeaders(options.headers);
  
  const response = await fetch(url, {
    ...options,
    headers,
  });
  
  // Handle 401 Unauthorized - redirect to login
  if (response.status === 401) {
    localStorage.removeItem('auth_token');
    localStorage.removeItem('auth_user');
    authToken = null;
    window.location.href = '/login';
    throw new Error('Unauthorized - Please login again');
  }
  
  return response;
}

// Export api object for AuthContext
export const api = {
  setAuthToken,
  getAuthToken,

  async get(path, options = {}) {
    const { params, ...rest } = options;
    let url = `${API_BASE_URL}${path}`;
    if (params) {
      const qs = new URLSearchParams(
        Object.fromEntries(Object.entries(params).filter(([, v]) => v !== undefined && v !== null))
      ).toString();
      if (qs) url += `?${qs}`;
    }
    const response = await fetchWithAuth(url, { method: 'GET', ...rest });
    if (!response.ok) {
      const err = await response.text();
      throw new Error(err || response.status);
    }
    return { data: await response.json() };
  },

  async post(path, body, options = {}) {
    const url = `${API_BASE_URL}${path}`;
    const response = await fetchWithAuth(url, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
      ...options,
    });
    if (!response.ok) {
      const err = await response.text();
      throw new Error(err || response.status);
    }
    return { data: await response.json() };
  },

  async put(path, body, options = {}) {
    const url = `${API_BASE_URL}${path}`;
    const response = await fetchWithAuth(url, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
      ...options,
    });
    if (!response.ok) {
      const err = await response.text();
      throw new Error(err || response.status);
    }
    return { data: await response.json() };
  },

  async delete(path, options = {}) {
    const url = `${API_BASE_URL}${path}`;
    const response = await fetchWithAuth(url, { method: 'DELETE', ...options });
    if (!response.ok) {
      const err = await response.text();
      throw new Error(err || response.status);
    }
    return { data: await response.json() };
  },
};

export async function fetchPosts(params = {}) {
  const queryParams = new URLSearchParams();
  if (params.source) queryParams.set('source', params.source);
  if (params.topic) queryParams.set('topic', params.topic);
  if (params.lang) queryParams.set('lang', params.lang);
  if (params.q) queryParams.set('q', params.q);
  if (params.limit) queryParams.set('limit', params.limit.toString());
  if (params.skip !== undefined) queryParams.set('skip', Math.max(0, params.skip).toString());
  if (params.link_only) queryParams.set('link_only', 'true');
  if (params.topics_only) queryParams.set('topics_only', 'true');
  queryParams.set('_t', Date.now().toString());

  const url = `${API_BASE_URL}/posts?${queryParams}`;
  console.log('[API] Fetching posts:', url);

  try {
    const response = await fetchWithAuth(url, {
      cache: 'no-store',
    });
    if (!response.ok) {
      const errorText = await response.text();
      console.error('Posts API Error:', response.status, errorText);
      throw new Error(`Failed to fetch posts: ${response.status} ${errorText}`);
    }
    return response.json();
  } catch (error) {
    console.error('Failed to fetch posts:', error);
    throw error;
  }
}

export async function fetchStats(params = {}) {
  const queryParams = new URLSearchParams();
  if (params.link_only) queryParams.set('link_only', 'true');
  if (params.topics_only) queryParams.set('topics_only', 'true');
  if (params.lang) queryParams.set('lang', params.lang);
  const qs = queryParams.toString();
  try {
    const response = await fetchWithAuth(`${API_BASE_URL}/stats${qs ? `?${qs}` : ''}`);
    if (!response.ok) {
      const errorText = await response.text();
      console.error('Stats API Error:', response.status, errorText);
      throw new Error(`Failed to fetch stats: ${response.status}`);
    }
    return response.json();
  } catch (error) {
    console.error('Failed to fetch stats:', error);
    throw error;
  }
}

export async function fetchTopics() {
  try {
    const response = await fetchWithAuth(`${API_BASE_URL}/topics`);
    if (!response.ok) {
      const errorText = await response.text();
      console.error('Topics API Error:', response.status, errorText);
      throw new Error(`Failed to fetch topics: ${response.status}`);
    }
    const data = await response.json();
    if (Array.isArray(data)) return data;
    const maybeObj = data;
    if (maybeObj && Array.isArray(maybeObj.topics)) {
      const arr = maybeObj.topics;
      return arr.map((t) => (typeof t === 'string' ? t : t.topic)).filter(Boolean);
    }
    return [];
  } catch (error) {
    console.error('Failed to fetch topics:', error);
    throw error;
  }
}

export async function fetchPostsCount(params = {}) {
  const queryParams = new URLSearchParams();
  if (params.source) queryParams.set('source', params.source);
  if (params.topic) queryParams.set('topic', params.topic);
  if (params.lang) queryParams.set('lang', params.lang);
  if (params.link_only) queryParams.set('link_only', 'true');
  if (params.topics_only) queryParams.set('topics_only', 'true');
  queryParams.set('_t', Date.now().toString());
  
  console.log('[API] Fetching posts count:', `${API_BASE_URL}/posts/count?${queryParams}`);
  
  try {
    const resp = await fetchWithAuth(`${API_BASE_URL}/posts/count?${queryParams}`, {
      cache: 'no-store',
    });
    if (!resp.ok) {
      const errorText = await resp.text();
      console.error('Posts count API Error:', resp.status, errorText);
      throw new Error(`Failed to count posts: ${resp.status}`);
    }
    const data = await resp.json();
    console.log('[API] Posts count result:', data);
    return data;
  } catch (error) {
    console.error('Failed to count posts:', error);
    throw error;
  }
}

// Analytics endpoints
export async function fetchTrendingTopics(params = {}) {
  const queryParams = new URLSearchParams();
  if (params.days) queryParams.set('days', params.days.toString());
  if (params.min_posts) queryParams.set('min_posts', params.min_posts.toString());
  
  try {
    const response = await fetch(`${API_BASE_URL}/topics/trending?${queryParams}`);
    if (!response.ok) {
      throw new Error(`Failed to fetch trending topics: ${response.status}`);
    }
    return response.json();
  } catch (error) {
    console.error('Failed to fetch trending topics:', error);
    throw error;
  }
}

export async function fetchKeywords(params = {}) {
  const queryParams = new URLSearchParams();
  if (params.limit) queryParams.set('limit', params.limit.toString());
  if (params.topic) queryParams.set('topic', params.topic);
  if (params.platform) queryParams.set('platform', params.platform);
  if (params.date_from) queryParams.set('date_from', params.date_from);
  if (params.date_to) queryParams.set('date_to', params.date_to);
  
  try {
    const response = await fetch(`${API_BASE_URL}/analytics/keywords?${queryParams}`);
    if (!response.ok) {
      throw new Error(`Failed to fetch keywords: ${response.status}`);
    }
    return response.json();
  } catch (error) {
    console.error('Failed to fetch keywords:', error);
    throw error;
  }
}

export async function fetchTrendingKeywords(params = {}) {
  const queryParams = new URLSearchParams();
  if (params.limit) queryParams.set('limit', params.limit.toString());
  if (params.min_velocity) queryParams.set('min_velocity', params.min_velocity.toString());
  
  try {
    const response = await fetch(`${API_BASE_URL}/analytics/keywords/trending?${queryParams}`);
    if (!response.ok) {
      throw new Error(`Failed to fetch trending keywords: ${response.status}`);
    }
    return response.json();
  } catch (error) {
    console.error('Failed to fetch trending keywords:', error);
    throw error;
  }
}

export async function fetchTimeline(params = {}) {
  const queryParams = new URLSearchParams();
  if (params.date_from) queryParams.set('date_from', params.date_from);
  if (params.date_to) queryParams.set('date_to', params.date_to);
  if (params.granularity) queryParams.set('granularity', params.granularity);
  if (params.topic) queryParams.set('topic', params.topic);
  if (params.platform) queryParams.set('platform', params.platform);
  
  try {
    const response = await fetch(`${API_BASE_URL}/analytics/timeline?${queryParams}`);
    if (!response.ok) {
      throw new Error(`Failed to fetch timeline: ${response.status}`);
    }
    return response.json();
  } catch (error) {
    console.error('Failed to fetch timeline:', error);
    throw error;
  }
}

export async function fetchComparison(params = {}) {
  const queryParams = new URLSearchParams();
  if (params.date_from) queryParams.set('date_from', params.date_from);
  if (params.date_to) queryParams.set('date_to', params.date_to);
  if (params.topic) queryParams.set('topic', params.topic);
  
  try {
    const response = await fetch(`${API_BASE_URL}/analytics/comparison?${queryParams}`);
    if (!response.ok) {
      throw new Error(`Failed to fetch comparison: ${response.status}`);
    }
    return response.json();
  } catch (error) {
    console.error('Failed to fetch comparison:', error);
    throw error;
  }
}

export async function fetchHeatmap(params = {}) {
  const queryParams = new URLSearchParams();
  if (params.date_from) queryParams.set('date_from', params.date_from);
  if (params.date_to) queryParams.set('date_to', params.date_to);
  if (params.topic) queryParams.set('topic', params.topic);
  queryParams.set('_t', Date.now().toString());
  
  console.log('[API] Fetching heatmap:', `${API_BASE_URL}/analytics/heatmap?${queryParams}`);
  
  try {
    const response = await fetch(`${API_BASE_URL}/analytics/heatmap?${queryParams}`, {
      cache: 'no-store',
      headers: {
        'Cache-Control': 'no-cache',
      },
    });
    if (!response.ok) {
      throw new Error(`Failed to fetch heatmap: ${response.status}`);
    }
    const data = await response.json();
    console.log('[API] Heatmap result:', data);
    return data;
  } catch (error) {
    console.error('Failed to fetch heatmap:', error);
    throw error;
  }
}
