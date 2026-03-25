import React, { useState, useEffect, useCallback, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { formatDistanceToNow } from 'date-fns';
import { vi } from 'date-fns/locale';
import { useAuth } from '../../context/AuthContext.jsx';
import {
  Box,
  Container,
  Typography,
  Chip,
  Card,
  CardContent,
  CardActions,
  Button,
  CircularProgress,
  Alert,
  IconButton,
  Tooltip,
  TextField,
  InputAdornment,
  Skeleton,
  useMediaQuery,
  useTheme,
  Fade,
} from '@mui/material';
import OpenInNewIcon from '@mui/icons-material/OpenInNew';
import RefreshIcon from '@mui/icons-material/Refresh';
import WhatshotIcon from '@mui/icons-material/Whatshot';
import FiberManualRecordIcon from '@mui/icons-material/FiberManualRecord';
import SearchIcon from '@mui/icons-material/Search';
import ArticleIcon from '@mui/icons-material/Article';
import LocalFireDepartmentIcon from '@mui/icons-material/LocalFireDepartment';
import ClearIcon from '@mui/icons-material/Clear';
import AutoAwesomeIcon from '@mui/icons-material/AutoAwesome';
import LogoutIcon from '@mui/icons-material/Logout';
import DashboardIcon from '@mui/icons-material/Dashboard';
import { fetchHotTopics, fetchTopicPosts, searchPublicPosts } from '../../lib/publicApi.js';

// ─── Helpers ────────────────────────────────────────────────────────────────

function timeAgo(dateStr) {
  if (!dateStr) return '';
  try {
    return formatDistanceToNow(new Date(dateStr), { addSuffix: true, locale: vi });
  } catch {
    return '';
  }
}

function formatDateTime(dateStr) {
  if (!dateStr) return '';
  try {
    const d = new Date(dateStr);
    return `${d.getDate().toString().padStart(2, '0')}/${(d.getMonth() + 1)
      .toString()
      .padStart(2, '0')}/${d.getFullYear()} ${d.getHours().toString().padStart(2, '0')}:${d
      .getMinutes()
      .toString()
      .padStart(2, '0')}`;
  } catch {
    return '';
  }
}

// ─── News Card ───────────────────────────────────────────────────────────────

function NewsCard({ post }) {
  const externalLink = post.links?.find((l) => !l.includes('t.me') && l.startsWith('http'));
  const title = post.full_article?.title || null;
  const primaryTopic = post.topics?.[0];

  return (
    <Card
      elevation={0}
      sx={{
        mb: 2,
        borderRadius: 2,
        border: '1px solid',
        borderColor: 'divider',
        transition: 'box-shadow 0.18s, transform 0.18s',
        '&:hover': {
          boxShadow: '0 6px 20px rgba(0,0,0,0.10)',
          transform: 'translateY(-2px)',
        },
      }}
    >
      <CardContent sx={{ pb: externalLink ? 0 : 1.5 }}>
        {/* Meta row */}
        <Box display="flex" alignItems="center" gap={1} mb={0.75} flexWrap="wrap">
          {primaryTopic && (
            <Chip
              label={primaryTopic}
              size="small"
              sx={{
                fontSize: '0.68rem',
                height: 20,
                bgcolor: '#fef3c7',
                color: '#92400e',
                fontWeight: 600,
              }}
            />
          )}
          <Typography
            variant="caption"
            color="text.secondary"
            sx={{ display: 'flex', alignItems: 'center', gap: 0.4 }}
          >
            <FiberManualRecordIcon sx={{ fontSize: 8, color: '#2563eb' }} />
            {post.source}
          </Typography>
          <Typography variant="caption" color="text.disabled" title={formatDateTime(post.created_at)}>
            · {timeAgo(post.created_at)}
          </Typography>
        </Box>

        {/* Article title (if scraped) */}
        {title && (
          <Typography
            variant="subtitle1"
            fontWeight={700}
            mb={0.5}
            sx={{
              display: '-webkit-box',
              WebkitLineClamp: 2,
              WebkitBoxOrient: 'vertical',
              overflow: 'hidden',
              lineHeight: 1.4,
              fontSize: '0.975rem',
              color: 'text.primary',
            }}
          >
            {title}
          </Typography>
        )}

        {/* Post body */}
        <Typography
          variant="body2"
          color="text.secondary"
          sx={{
            display: '-webkit-box',
            WebkitLineClamp: title ? 3 : 5,
            WebkitBoxOrient: 'vertical',
            overflow: 'hidden',
            lineHeight: 1.65,
          }}
        >
          {post.text}
        </Typography>
      </CardContent>

      {externalLink && (
        <CardActions sx={{ px: 2, pt: 0.5, pb: 1.5 }}>
          <Button
            size="small"
            variant="contained"
            color="primary"
            endIcon={<OpenInNewIcon fontSize="small" />}
            href={externalLink}
            target="_blank"
            rel="noopener noreferrer"
            onClick={(e) => e.stopPropagation()}
            sx={{
              textTransform: 'none',
              fontSize: '0.8rem',
              borderRadius: 2,
              px: 2,
              py: 0.5,
              boxShadow: 'none',
              '&:hover': { boxShadow: '0 2px 8px rgba(37,99,235,0.3)' },
            }}
          >
            Đọc bài gốc
          </Button>
        </CardActions>
      )}
    </Card>
  );
}

// ─── Skeleton loader ─────────────────────────────────────────────────────────

function CardSkeleton() {
  return (
    <Card elevation={0} sx={{ mb: 2, borderRadius: 2, border: '1px solid', borderColor: 'divider' }}>
      <CardContent>
        <Box display="flex" gap={1} mb={1}>
          <Skeleton variant="rounded" width={70} height={20} />
          <Skeleton variant="rounded" width={90} height={20} />
        </Box>
        <Skeleton variant="text" sx={{ fontSize: '1rem' }} width="90%" />
        <Skeleton variant="text" sx={{ fontSize: '0.875rem' }} width="100%" />
        <Skeleton variant="text" sx={{ fontSize: '0.875rem' }} width="75%" />
      </CardContent>
    </Card>
  );
}

// ─── Breaking News Ticker ─────────────────────────────────────────────────────

function NewsTicker({ posts }) {
  const texts = posts
    .slice(0, 8)
    .map((p) => p.full_article?.title || p.text?.slice(0, 80))
    .filter(Boolean);

  if (!texts.length) return null;

  const ticker = texts.join('   ·   ');

  return (
    <Box
      sx={{
        bgcolor: '#ef4444',
        color: 'white',
        py: 0.6,
        overflow: 'hidden',
        display: 'flex',
        alignItems: 'center',
      }}
    >
      <Box
        sx={{
          px: 2,
          fontWeight: 700,
          fontSize: '0.75rem',
          letterSpacing: 1,
          whiteSpace: 'nowrap',
          flexShrink: 0,
          bgcolor: '#b91c1c',
          alignSelf: 'stretch',
          display: 'flex',
          alignItems: 'center',
        }}
      >
        BREAKING
      </Box>
      <Box
        sx={{
          overflow: 'hidden',
          flex: 1,
          maskImage: 'linear-gradient(to right, transparent 0%, black 4%, black 96%, transparent 100%)',
        }}
      >
        <Box
          component="marquee"
          scrollamount="4"
          sx={{ fontSize: '0.8rem', whiteSpace: 'nowrap', display: 'block' }}
        >
          {ticker}
        </Box>
      </Box>
    </Box>
  );
}

// ─── Main Page ────────────────────────────────────────────────────────────────

const LIMIT = 20;
const REFRESH_INTERVAL_MS = 60_000;

export default function UserNewsPage() {
  const theme = useTheme();
  useMediaQuery(theme.breakpoints.down('sm'));
  const { user, isAdmin, logout } = useAuth();
  const navigate = useNavigate();

  const handleLogout = async () => {
    await logout();
    navigate('/login');
  };

  const [hotTopics, setHotTopics] = useState([]);
  const [topicsLoading, setTopicsLoading] = useState(true);

  const [selectedSlug, setSelectedSlug] = useState('all');
  const [posts, setPosts] = useState([]);
  const [total, setTotal] = useState(0);
  const [skip, setSkip] = useState(0);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const [searchInput, setSearchInput] = useState('');
  const [searchQuery, setSearchQuery] = useState('');
  const [searchResults, setSearchResults] = useState(null); // null = no active search
  const [searchLoading, setSearchLoading] = useState(false);
  const [aiRank, setAiRank] = useState(false);

  const [lastUpdate, setLastUpdate] = useState(new Date());
  const timerRef = useRef(null);

  // Load hot topics once on mount
  useEffect(() => {
    fetchHotTopics()
      .then((data) => setHotTopics(data.topics || []))
      .catch((err) => console.error('Hot topics error:', err))
      .finally(() => setTopicsLoading(false));
  }, []);

  // Core post loader
  const loadPosts = useCallback(async (slug, currentSkip, append = false, useAi = false) => {
    setLoading(true);
    setError(null);
    try {
      const data = await fetchTopicPosts(slug, currentSkip, LIMIT, useAi);
      const incoming = data.posts || [];
      setPosts((prev) => (append ? [...prev, ...incoming] : incoming));
      setTotal(data.total ?? incoming.length);
      setLastUpdate(new Date());
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }, []);

  // Reset & load when topic or aiRank changes
  useEffect(() => {
    setSearchQuery('');
    setSearchInput('');
    setSearchResults(null);
    setSkip(0);
    loadPosts(selectedSlug, 0, false, aiRank);
  }, [selectedSlug, aiRank, loadPosts]);

  // Auto-refresh
  useEffect(() => {
    if (timerRef.current) clearInterval(timerRef.current);
    timerRef.current = setInterval(() => {
      if (!searchQuery) {
        setSkip(0);
        loadPosts(selectedSlug, 0, false, aiRank);
      }
    }, REFRESH_INTERVAL_MS);
    return () => clearInterval(timerRef.current);
  }, [selectedSlug, searchQuery, aiRank, loadPosts]);

  const handleLoadMore = () => {
    const newSkip = skip + LIMIT;
    setSkip(newSkip);
    loadPosts(selectedSlug, newSkip, true, aiRank);
  };

  const handleRefresh = () => {
    setSkip(0);
    setSearchQuery('');
    setSearchInput('');
    setSearchResults(null);
    loadPosts(selectedSlug, 0, false, aiRank);
  };

  // Search
  const handleSearch = async () => {
    const q = searchInput.trim();
    if (!q) {
      setSearchResults(null);
      setSearchQuery('');
      return;
    }
    setSearchQuery(q);
    setSearchLoading(true);
    try {
      const data = await searchPublicPosts(q, 30);
      setSearchResults(data.posts || []);
    } catch (err) {
      setError(err.message);
    } finally {
      setSearchLoading(false);
    }
  };

  const handleClearSearch = () => {
    setSearchInput('');
    setSearchQuery('');
    setSearchResults(null);
  };

  // Which posts to show
  const displayPosts = searchResults !== null ? searchResults : posts;
  const selectedTopic = hotTopics.find((t) => t.slug === selectedSlug);
  const hasMore = searchResults === null && posts.length < total;

  return (
    <Box sx={{ minHeight: '100vh', bgcolor: '#f8fafc' }}>
      {/* ── Header ── */}
      <Box
        sx={{
          background: 'linear-gradient(135deg, #0f172a 0%, #1e3a5f 55%, #0f3460 100%)',
          color: 'white',
          py: { xs: 2, md: 3 },
          px: 2,
        }}
      >
        <Container maxWidth="lg">
          <Box display="flex" alignItems="center" justifyContent="space-between" flexWrap="wrap" gap={1}>
            {/* Brand */}
            <Box display="flex" alignItems="center" gap={1.5}>
              <LocalFireDepartmentIcon sx={{ fontSize: { xs: 28, md: 36 }, color: '#ff6b35' }} />
              <Box>
                <Typography
                  variant="h5"
                  fontWeight={800}
                  letterSpacing={1.5}
                  sx={{ fontSize: { xs: '1.1rem', md: '1.4rem' } }}
                >
                  📡 BẢNG TIN NÓNG
                </Typography>
                <Typography variant="caption" sx={{ opacity: 0.7, display: { xs: 'none', sm: 'block' } }}>
                  Tin tức thời sự quốc tế &amp; trong nước · Cập nhật liên tục
                </Typography>
              </Box>
              <Chip
                label="● LIVE"
                size="small"
                sx={{
                  bgcolor: '#ef4444',
                  color: 'white',
                  fontWeight: 700,
                  fontSize: '0.68rem',
                  height: 22,
                  animation: 'livePulse 2s infinite',
                  '@keyframes livePulse': {
                    '0%, 100%': { opacity: 1 },
                    '50%': { opacity: 0.55 },
                  },
                }}
              />
            </Box>

            {/* Search + Refresh */}
            <Box display="flex" alignItems="center" gap={1}>
              <TextField
                size="small"
                placeholder="Tìm kiếm tin tức…"
                value={searchInput}
                onChange={(e) => setSearchInput(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && handleSearch()}
                InputProps={{
                  startAdornment: (
                    <InputAdornment position="start">
                      <SearchIcon sx={{ color: 'rgba(255,255,255,0.6)', fontSize: 18 }} />
                    </InputAdornment>
                  ),
                  endAdornment: searchInput && (
                    <InputAdornment position="end">
                      <IconButton size="small" onClick={handleClearSearch} sx={{ color: 'rgba(255,255,255,0.6)' }}>
                        <ClearIcon fontSize="small" />
                      </IconButton>
                    </InputAdornment>
                  ),
                  sx: {
                    bgcolor: 'rgba(255,255,255,0.12)',
                    borderRadius: 3,
                    color: 'white',
                    '& fieldset': { border: '1px solid rgba(255,255,255,0.2)' },
                    '&:hover fieldset': { borderColor: 'rgba(255,255,255,0.4) !important' },
                    '& input': { color: 'white', '&::placeholder': { color: 'rgba(255,255,255,0.5)' } },
                  },
                }}
                sx={{ width: { xs: 160, sm: 220 } }}
              />
              <Button
                variant="contained"
                size="small"
                onClick={handleSearch}
                disabled={searchLoading}
                sx={{
                  bgcolor: 'rgba(255,255,255,0.18)',
                  color: 'white',
                  textTransform: 'none',
                  borderRadius: 3,
                  '&:hover': { bgcolor: 'rgba(255,255,255,0.28)' },
                  boxShadow: 'none',
                }}
              >
                Tìm
              </Button>
              <Tooltip title="Làm mới">
                <IconButton onClick={handleRefresh} sx={{ color: 'rgba(255,255,255,0.8)' }}>
                  <RefreshIcon />
                </IconButton>
              </Tooltip>

              {/* User actions */}
              {isAdmin && (
                <Tooltip title="Vào Dashboard Admin">
                  <IconButton onClick={() => navigate('/admin')} sx={{ color: 'rgba(255,255,255,0.8)' }}>
                    <DashboardIcon />
                  </IconButton>
                </Tooltip>
              )}
              <Tooltip title={`Đăng xuất (${user?.username})`}>
                <IconButton onClick={handleLogout} sx={{ color: 'rgba(255,255,255,0.8)' }}>
                  <LogoutIcon />
                </IconButton>
              </Tooltip>
            </Box>
          </Box>
        </Container>
      </Box>

      {/* ── Breaking Ticker ── */}
      {posts.length > 0 && !searchQuery && <NewsTicker posts={posts} />}

      {/* ── Hot Topics Bar ── */}
      <Box
        sx={{
          bgcolor: 'background.paper',
          borderBottom: '1px solid',
          borderColor: 'divider',
          py: 1.25,
          px: 2,
          position: 'sticky',
          top: 0,
          zIndex: 200,
          boxShadow: '0 2px 8px rgba(0,0,0,0.06)',
        }}
      >
        <Container maxWidth="lg" disableGutters>
          <Box
            display="flex"
            alignItems="center"
            gap={1}
            sx={{
              overflowX: 'auto',
              pb: 0.25,
              '&::-webkit-scrollbar': { height: 3 },
              '&::-webkit-scrollbar-thumb': { bgcolor: 'divider', borderRadius: 2 },
            }}
          >
            <WhatshotIcon sx={{ color: '#f97316', flexShrink: 0, fontSize: 20 }} />

            {/* "All" chip */}
            <Chip
              label="🌐 Tất cả"
              clickable
              onClick={() => setSelectedSlug('all')}
              color={selectedSlug === 'all' ? 'primary' : 'default'}
              variant={selectedSlug === 'all' ? 'filled' : 'outlined'}
              size="small"
              sx={{ flexShrink: 0, fontWeight: selectedSlug === 'all' ? 700 : 500 }}
            />

            {/* Hot topic chips */}
            {!topicsLoading &&
              hotTopics.map((topic) => {
                const active = selectedSlug === topic.slug;
                return (
                  <Chip
                    key={topic.slug}
                    label={topic.name}
                    clickable
                    onClick={() => setSelectedSlug(topic.slug)}
                    size="small"
                    sx={{
                      flexShrink: 0,
                      fontWeight: active ? 700 : 500,
                      bgcolor: active ? topic.color : 'transparent',
                      color: active ? 'white' : topic.color,
                      border: `1.5px solid ${topic.color}`,
                      '&:hover': { bgcolor: topic.color, color: 'white' },
                    }}
                  />
                );
              })}

            {topicsLoading && (
              <>
                {[1, 2, 3, 4].map((i) => (
                  <Skeleton key={i} variant="rounded" width={90} height={24} sx={{ flexShrink: 0 }} />
                ))}
              </>
            )}
          </Box>
        </Container>
      </Box>

      {/* ── Main Content ── */}
      <Container maxWidth="lg" sx={{ py: { xs: 2, md: 3 } }}>
        {/* Section header */}
        {!searchQuery ? (
          <Box display="flex" alignItems="flex-start" justifyContent="space-between" mb={2} flexWrap="wrap" gap={1}>
            <Box>
              <Typography variant="h6" fontWeight={700}>
                {selectedTopic ? selectedTopic.name : '🌐 Tất cả bản tin'}
              </Typography>
              {selectedTopic?.description && (
                <Typography variant="caption" color="text.secondary">
                  {selectedTopic.description}
                </Typography>
              )}
            </Box>
            <Box display="flex" alignItems="center" gap={1}>
              {selectedSlug !== 'all' && (
                <Tooltip title={aiRank ? 'Đang dùng AI ranking (OpenAI embeddings) – click để tắt' : 'Bật AI ranking: sắp xếp bài viết theo độ liên quan bằng AI (yêu cầu OPENAI_API_KEY)'}>
                  <Chip
                    icon={<AutoAwesomeIcon sx={{ fontSize: '14px !important' }} />}
                    label="AI Rank"
                    size="small"
                    clickable
                    onClick={() => setAiRank((v) => !v)}
                    color={aiRank ? 'secondary' : 'default'}
                    variant={aiRank ? 'filled' : 'outlined'}
                    sx={{ fontWeight: 600, fontSize: '0.72rem' }}
                  />
                </Tooltip>
              )}
              <Typography variant="caption" color="text.disabled" sx={{ flexShrink: 0 }}>
                Cập nhật {timeAgo(lastUpdate)}
              </Typography>
            </Box>
          </Box>
        ) : (
          <Box display="flex" alignItems="center" gap={1} mb={2}>
            <SearchIcon fontSize="small" color="action" />
            <Typography variant="h6" fontWeight={700}>
              Kết quả cho "
              <Box component="span" color="primary.main">
                {searchQuery}
              </Box>
              "
            </Typography>
            <Chip
              label={`${searchResults?.length ?? 0} bài`}
              size="small"
              variant="outlined"
              color="primary"
            />
            <Button size="small" onClick={handleClearSearch} sx={{ ml: 'auto', textTransform: 'none' }}>
              Xoá tìm kiếm
            </Button>
          </Box>
        )}

        {error && (
          <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError(null)}>
            {error}
          </Alert>
        )}

        {/* ── Posts list ── */}
        {loading && displayPosts.length === 0 ? (
          // Skeletons on initial load
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
            <ArticleIcon sx={{ fontSize: 64, color: 'divider', mb: 2 }} />
            <Typography color="text.secondary">
              {searchQuery ? 'Không tìm thấy kết quả nào.' : 'Chưa có bài viết nào cho chủ đề này.'}
            </Typography>
          </Box>
        ) : (
          <Fade in>
            <Box>
              {displayPosts.map((post, idx) => (
                <NewsCard key={post._id || post.id || idx} post={post} />
              ))}

              {/* Load more */}
              {hasMore && (
                <Box textAlign="center" mt={2} mb={4}>
                  <Button
                    variant="outlined"
                    onClick={handleLoadMore}
                    disabled={loading}
                    startIcon={loading ? <CircularProgress size={14} /> : null}
                    sx={{ textTransform: 'none', borderRadius: 3, px: 4 }}
                  >
                    {loading ? 'Đang tải…' : `Xem thêm (còn ${total - posts.length} bài)`}
                  </Button>
                </Box>
              )}

              {/* Refresh hint at bottom */}
              {!hasMore && displayPosts.length > 0 && (
                <Box textAlign="center" mt={1} mb={4}>
                  <Typography variant="caption" color="text.disabled">
                    Đã hiển thị tất cả · Tự động làm mới sau 60 giây
                  </Typography>
                </Box>
              )}
            </Box>
          </Fade>
        )}

        {/* Footer */}
        <Box textAlign="center" py={3} mt={2} borderTop="1px solid" borderColor="divider">
          <Typography variant="caption" color="text.disabled">
            Bản tin được tổng hợp từ Telegram &amp; các nguồn tin tức
          </Typography>
        </Box>
      </Container>
    </Box>
  );
}
