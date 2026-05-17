import React, { useState, useEffect, useCallback, useRef } from 'react';
import {
  Box,
  Typography,
  Chip,
  Button,
  TextField,
  InputAdornment,
  IconButton,
  CircularProgress,
  Alert,
  Fade,
  Skeleton,
  Pagination,
} from '@mui/material';
import ArticleIcon from '@mui/icons-material/Article';
import FilterListIcon from '@mui/icons-material/FilterList';
import CalendarTodayIcon from '@mui/icons-material/CalendarToday';
import SearchIcon from '@mui/icons-material/Search';
import ClearIcon from '@mui/icons-material/Clear';
import NewspaperIcon from '@mui/icons-material/Newspaper';
import { fetchArticlePosts, fetchPostTopics, searchPublicPosts } from '../../../lib/publicApi.js';
import { timeAgo } from '../../../lib/helpers.jsx';
import ArticleCard from '../../../components/public/ArticleCard.jsx';
import { CardSkeleton } from '../../../components/public/Skeletons.jsx';
import AudioPlayer from '../../../components/AudioPlayer.jsx';

const ARTICLES_LIMIT = 20;
const REFRESH_INTERVAL_MS = 60_000;

export default function ArticlesTab() {
  const [postTopics, setPostTopics] = useState([]);
  const [topicsLoading, setTopicsLoading] = useState(true);
  const [selectedTopic, setSelectedTopic] = useState('');
  const [selectedPlatform, setSelectedPlatform] = useState('all');
  const [selectedDate, setSelectedDate] = useState('all');
  const [posts, setPosts] = useState([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [searchInput, setSearchInput] = useState('');
  const [searchQuery, setSearchQuery] = useState('');
  const [searchResults, setSearchResults] = useState(null);
  const [searchLoading, setSearchLoading] = useState(false);
  const [lastUpdate, setLastUpdate] = useState(new Date());
  const [audioPlayer, setAudioPlayer] = useState(null);
  const timerRef = useRef(null);
  const loadAbortRef = useRef(null);
  const searchAbortRef = useRef(null);

  const totalPages = Math.max(1, Math.ceil(total / ARTICLES_LIMIT));

  const getDateFrom = useCallback(() => {
    const now = new Date();
    if (selectedDate === 'today') {
      return now.toISOString().slice(0, 10);
    } else if (selectedDate === '7d') {
      const d = new Date(now);
      d.setDate(d.getDate() - 7);
      return d.toISOString().slice(0, 10);
    } else if (selectedDate === '30d') {
      const d = new Date(now);
      d.setDate(d.getDate() - 30);
      return d.toISOString().slice(0, 10);
    }
    return '';
  }, [selectedDate]);

  useEffect(() => {
    const ac = new AbortController();
    fetchPostTopics(ac.signal)
      .then((d) => setPostTopics(d.topics || []))
      .catch(() => {})
      .finally(() => setTopicsLoading(false));
    return () => ac.abort();
  }, []);

  const loadPosts = useCallback(async (topic, currentPage, platform, dateFrom) => {
    if (loadAbortRef.current) loadAbortRef.current.abort();
    const ac = new AbortController();
    loadAbortRef.current = ac;
    setLoading(true);
    setError(null);
    try {
      const skip = (currentPage - 1) * ARTICLES_LIMIT;
      const data = await fetchArticlePosts(topic, skip, ARTICLES_LIMIT, '', ac.signal, platform, dateFrom, '');
      if (ac.signal.aborted) return;
      setPosts(data.posts || []);
      setTotal(data.total ?? (data.posts || []).length);
      setLastUpdate(new Date());
    } catch (e) {
      if (e?.name !== 'AbortError') setError(e.message);
    } finally {
      if (!ac.signal.aborted) setLoading(false);
    }
  }, []);

  useEffect(() => {
    setSearchQuery('');
    setSearchInput('');
    setSearchResults(null);
    setPage(1);
    loadPosts(selectedTopic, 1, selectedPlatform, getDateFrom());
  }, [selectedTopic, selectedPlatform, selectedDate, loadPosts, getDateFrom]);

  useEffect(() => {
    if (timerRef.current) clearInterval(timerRef.current);
    timerRef.current = setInterval(() => {
      if (!searchQuery) loadPosts(selectedTopic, page, selectedPlatform, getDateFrom());
    }, REFRESH_INTERVAL_MS);
    return () => clearInterval(timerRef.current);
  }, [selectedTopic, selectedPlatform, selectedDate, searchQuery, page, loadPosts, getDateFrom]);

  const handlePageChange = (newPage) => {
    setPage(newPage);
    loadPosts(selectedTopic, newPage, selectedPlatform, getDateFrom());
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  const handleSearch = async () => {
    const q = searchInput.trim();
    if (!q) {
      setSearchResults(null);
      setSearchQuery('');
      return;
    }
    if (searchAbortRef.current) searchAbortRef.current.abort();
    const ac = new AbortController();
    searchAbortRef.current = ac;
    setSearchQuery(q);
    setSearchLoading(true);
    try {
      const data = await searchPublicPosts(q, 30, 0, ac.signal, selectedPlatform, getDateFrom(), '');
      if (ac.signal.aborted) return;
      const withLinks = (data.posts || []).filter((p) =>
        p.links?.some((l) => !l.includes('t.me') && l.startsWith('http'))
      );
      setSearchResults(withLinks);
    } catch (e) {
      if (e?.name !== 'AbortError') setError(e.message);
    } finally {
      if (!ac.signal.aborted) setSearchLoading(false);
    }
  };

  const handleClearSearch = () => {
    setSearchInput('');
    setSearchQuery('');
    setSearchResults(null);
  };

  const displayPosts = searchResults !== null ? searchResults : posts;

  const PLATFORM_OPTIONS = [
    { value: 'all', label: 'Tất cả' },
    { value: 'telegram', label: 'Telegram' },
    { value: 'x', label: 'X (Twitter)' },
  ];
  const DATE_OPTIONS = [
    { value: 'all', label: 'Mọi thời gian' },
    { value: 'today', label: 'Hôm nay' },
    { value: '7d', label: '7 ngày' },
    { value: '30d', label: '30 ngày' },
  ];

  return (
    <Box>
      <Box display="flex" alignItems="center" gap={1} mb={1.5}>
        <ArticleIcon sx={{ color: '#3b82f6', fontSize: 22 }} />
        <Typography variant="h6" fontWeight={700} fontSize="1rem">
          Bài báo theo chủ đề
        </Typography>
        {!topicsLoading && postTopics.length > 0 && (
          <Typography variant="caption" color="text.disabled">
            {postTopics.length} danh mục
          </Typography>
        )}
      </Box>

      {/* Advanced Filters */}
      <Box display="flex" alignItems="center" gap={1} mb={1.5} flexWrap="wrap">
        <FilterListIcon sx={{ fontSize: 16, color: 'text.secondary' }} />
        <Typography variant="caption" color="text.secondary" fontWeight={600}>
          Nguồn:
        </Typography>
        {PLATFORM_OPTIONS.map((opt) => (
          <Chip
            key={opt.value}
            label={opt.label}
            size="small"
            clickable
            onClick={() => setSelectedPlatform(opt.value)}
            color={selectedPlatform === opt.value ? 'primary' : 'default'}
            variant={selectedPlatform === opt.value ? 'filled' : 'outlined'}
            sx={{ fontWeight: selectedPlatform === opt.value ? 700 : 500 }}
          />
        ))}
        <Box sx={{ ml: { xs: 0, sm: 1 }, display: 'flex', alignItems: 'center', gap: 1 }}>
          <CalendarTodayIcon sx={{ fontSize: 16, color: 'text.secondary' }} />
          <Typography variant="caption" color="text.secondary" fontWeight={600}>
            Thời gian:
          </Typography>
          {DATE_OPTIONS.map((opt) => (
            <Chip
              key={opt.value}
              label={opt.label}
              size="small"
              clickable
              onClick={() => setSelectedDate(opt.value)}
              color={selectedDate === opt.value ? 'secondary' : 'default'}
              variant={selectedDate === opt.value ? 'filled' : 'outlined'}
              sx={{ fontWeight: selectedDate === opt.value ? 700 : 500 }}
            />
          ))}
        </Box>
      </Box>

      {/* Topic filter chips */}
      <Box
        sx={{
          display: 'flex',
          alignItems: 'center',
          gap: 1,
          mb: 2,
          overflowX: 'auto',
          pb: 0.5,
          '&::-webkit-scrollbar': { height: 3 },
          '&::-webkit-scrollbar-thumb': { bgcolor: 'divider', borderRadius: 2 },
        }}
      >
        <Chip
          label="Tất cả"
          clickable
          onClick={() => setSelectedTopic('')}
          color={selectedTopic === '' ? 'primary' : 'default'}
          variant={selectedTopic === '' ? 'filled' : 'outlined'}
          size="small"
          sx={{ flexShrink: 0, fontWeight: selectedTopic === '' ? 700 : 500 }}
        />
        {!topicsLoading &&
          postTopics.map((t) => {
            const active = selectedTopic === t.name || selectedTopic === t.slug;
            return (
              <Chip
                key={t.slug}
                label={`${t.name} (${t.count})`}
                clickable
                onClick={() => setSelectedTopic(active ? '' : t.name)}
                size="small"
                sx={{
                  flexShrink: 0,
                  fontWeight: active ? 700 : 500,
                  bgcolor: active ? t.color : 'transparent',
                  color: active ? 'white' : t.color,
                  border: `1.5px solid ${t.color}`,
                  '&:hover': { bgcolor: t.color, color: 'white' },
                }}
              />
            );
          })}
        {topicsLoading &&
          [1, 2, 3, 4].map((i) => (
            <Skeleton key={i} variant="rounded" width={100} height={24} sx={{ flexShrink: 0 }} />
          ))}
      </Box>

      {/* Search bar */}
      <Box display="flex" gap={1} mb={2} alignItems="center" flexWrap="wrap">
        <TextField
          size="small"
          placeholder="Tìm bài báo có link…"
          value={searchInput}
          onChange={(e) => setSearchInput(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && handleSearch()}
          InputProps={{
            startAdornment: (
              <InputAdornment position="start">
                <SearchIcon sx={{ fontSize: 18 }} color="action" />
              </InputAdornment>
            ),
            endAdornment: searchInput && (
              <InputAdornment position="end">
                <IconButton size="small" onClick={handleClearSearch}>
                  <ClearIcon fontSize="small" />
                </IconButton>
              </InputAdornment>
            ),
          }}
          sx={{ flex: 1, minWidth: { xs: '100%', sm: 'auto' }, maxWidth: { xs: '100%', sm: 360 } }}
        />
        <Box display="flex" alignItems="center" gap={1} sx={{ width: { xs: '100%', sm: 'auto' } }}>
          <Button
            variant="contained"
            size="small"
            onClick={handleSearch}
            disabled={searchLoading}
            sx={{ textTransform: 'none', borderRadius: 2, boxShadow: 'none' }}
          >
            Tìm
          </Button>
          <Typography variant="caption" color="text.disabled" sx={{ ml: 'auto', flexShrink: 0 }}>
            Cập nhật {timeAgo(lastUpdate)}
          </Typography>
        </Box>
      </Box>

      {error && (
        <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError(null)}>
          {error}
        </Alert>
      )}

      {searchQuery && (
        <Box display="flex" alignItems="center" gap={1} mb={2}>
          <SearchIcon fontSize="small" color="action" />
          <Typography variant="subtitle2" fontWeight={700}>
            Kết quả cho "
            <Box component="span" color="primary.main">
              {searchQuery}
            </Box>
            "
          </Typography>
          <Chip
            label={`${displayPosts.length} bài`}
            size="small"
            variant="outlined"
            color="primary"
          />
          <Button size="small" onClick={handleClearSearch} sx={{ ml: 'auto', textTransform: 'none' }}>
            Xoá
          </Button>
        </Box>
      )}

      {loading && displayPosts.length === 0 ? (
        <>
          {[1, 2, 3, 4, 5].map((i) => (
            <CardSkeleton key={i} />
          ))}
        </>
      ) : searchLoading ? (
        <Box display="flex" justifyContent="center" py={6}>
          <CircularProgress />
        </Box>
      ) : displayPosts.length === 0 ? (
        <Box textAlign="center" py={8}>
          <NewspaperIcon sx={{ fontSize: 64, color: 'divider', mb: 2 }} />
          <Typography color="text.secondary">
            {searchQuery ? 'Không tìm thấy bài báo nào.' : 'Chưa có bài báo có link cho danh mục này.'}
          </Typography>
        </Box>
      ) : (
        <Fade in>
          <Box>
            {displayPosts.map((post, idx) => (
              <ArticleCard
                key={post._id || idx}
                post={post}
                selectedTopic={selectedTopic}
                searchQuery={searchQuery}
                onPlayAudio={(p) => setAudioPlayer(p)}
              />
            ))}
            {searchResults === null && totalPages > 1 && (
              <Box display="flex" flexDirection="column" alignItems="center" gap={1} mt={2} mb={4}>
                <Pagination
                  count={totalPages}
                  page={page}
                  onChange={(e, value) => handlePageChange(value)}
                  color="primary"
                  shape="rounded"
                  disabled={loading}
                />
                <Typography variant="caption" color="text.disabled">
                  Trang {page}/{totalPages} · {total} bài · Tự động làm mới sau 60 giây
                </Typography>
              </Box>
            )}
            {searchResults === null && totalPages <= 1 && displayPosts.length > 0 && (
              <Box textAlign="center" mt={1} mb={4}>
                <Typography variant="caption" color="text.disabled">
                  Đã hiển thị tất cả · Tự động làm mới sau 60 giây
                </Typography>
              </Box>
            )}
          </Box>
        </Fade>
      )}

      {audioPlayer && (
        <AudioPlayer
          audioUrl={audioPlayer.url}
          title={audioPlayer.title}
          onClose={() => {
            URL.revokeObjectURL(audioPlayer.url);
            setAudioPlayer(null);
          }}
        />
      )}
    </Box>
  );
}
