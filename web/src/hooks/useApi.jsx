import { useQuery } from '@tanstack/react-query';
import {
  fetchStats,
  fetchTrendingTopics,
  fetchKeywords,
  fetchTrendingKeywords,
  fetchTimeline,
  fetchComparison,
  fetchPosts,
  fetchPostsCount,
  fetchTopics,
  fetchHeatmap,
  fetchHotNews,
} from '../lib/api.jsx';

// Stats hook
export function useStats(params = {}) {
  return useQuery({
    queryKey: ['stats', params],
    queryFn: () => fetchStats(params),
    staleTime: 5 * 60 * 1000, // 5 minutes
  });
}

// Trending topics hook
export function useTrendingTopics(params = {}) {
  return useQuery({
    queryKey: ['trending-topics', params],
    queryFn: () => fetchTrendingTopics(params),
    staleTime: 10 * 60 * 1000, // 10 minutes
  });
}

// Keywords hook
export function useKeywords(params = {}) {
  return useQuery({
    queryKey: ['keywords', params],
    queryFn: () => fetchKeywords(params),
    staleTime: 15 * 60 * 1000, // 15 minutes
  });
}

// Trending keywords hook
export function useTrendingKeywords(params = {}) {
  return useQuery({
    queryKey: ['trending-keywords', params],
    queryFn: () => fetchTrendingKeywords(params),
    staleTime: 10 * 60 * 1000,
  });
}

// Timeline hook
export function useTimeline(params = {}) {
  return useQuery({
    queryKey: ['timeline', params],
    queryFn: () => fetchTimeline(params),
    staleTime: 5 * 60 * 1000,
  });
}

// Comparison hook
export function useComparison(params = {}) {
  return useQuery({
    queryKey: ['comparison', params],
    queryFn: () => fetchComparison(params),
    staleTime: 10 * 60 * 1000,
  });
}

// Posts hook
export function usePosts(params = {}) {
  return useQuery({
    queryKey: ['posts', params],
    queryFn: () => fetchPosts(params),
    staleTime: 2 * 60 * 1000, // 2 minutes
  });
}

// Posts count hook
export function usePostsCount(params = {}) {
  return useQuery({
    queryKey: ['postsCount', params],
    queryFn: () => fetchPostsCount(params),
    staleTime: 2 * 60 * 1000, // 2 minutes
  });
}

// Topics hook
export function useTopics() {
  return useQuery({
    queryKey: ['topics'],
    queryFn: fetchTopics,
    staleTime: 60 * 60 * 1000, // 1 hour (topics don't change often)
  });
}

// Heatmap hook
export function useHeatmap(params = {}) {
  return useQuery({
    queryKey: ['heatmap', params],
    queryFn: () => fetchHeatmap(params),
    staleTime: 10 * 60 * 1000, // 10 minutes
  });
}

// Hot News clusters hook (uses /public/hotnews — keyword-frequency + GPT clustering)
export function useHotNews(params = {}) {
  return useQuery({
    queryKey: ['hotnews', params],
    queryFn: () => fetchHotNews(params),
    staleTime: 10 * 60 * 1000, // server caches 2h anyway, 10min local is fine
    retry: 2,
  });
}
