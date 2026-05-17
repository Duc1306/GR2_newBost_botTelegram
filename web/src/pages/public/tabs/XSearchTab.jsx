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
  Pagination,
  Tooltip,
} from '@mui/material';
import TwitterIcon from '@mui/icons-material/Twitter';
import SearchIcon from '@mui/icons-material/Search';
import ClearIcon from '@mui/icons-material/Clear';
import { searchXPosts } from '../../../lib/publicApi.js';
import ArticleCard from '../../../components/public/ArticleCard.jsx';
import { CardSkeleton } from '../../../components/public/Skeletons.jsx';
import AudioPlayer from '../../../components/AudioPlayer.jsx';

const X_LIMIT = 20;

export default function XSearchTab() {
  const [input, setInput] = useState('');
  const [query, setQuery] = useState('');
  const [posts, setPosts] = useState([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(false);
  const [isLive, setIsLive] = useState(false);
  const [error, setError] = useState(null);
  const [page, setPage] = useState(1);
  const [audioPlayer, setAudioPlayer] = useState(null);
  const abortRef = useRef(null);

  const doSearch = useCallback(async (q, currentPage) => {
    if (abortRef.current) abortRef.current.abort();
    const ac = new AbortController();
    abortRef.current = ac;
    setLoading(true);
    setError(null);
    setIsLive(false);
    try {
      const skip = (currentPage - 1) * X_LIMIT;
      const data = await searchXPosts(q, skip, X_LIMIT, ac.signal);
      if (ac.signal.aborted) return;
      setPosts(data.posts || []);
      setTotal(data.total ?? (data.posts || []).length);
      setIsLive(!!data.live);
    } catch (e) {
      if (e?.name !== 'AbortError') setError(e.message);
    } finally {
      if (!ac.signal.aborted) setLoading(false);
    }
  }, []);

  useEffect(() => {
    doSearch('', 1);
  }, [doSearch]);

  const handleSearch = () => {
    const q = input.trim();
    setQuery(q);
    setPage(1);
    doSearch(q, 1);
  };

  const handleClear = () => {
    setInput('');
    setQuery('');
    setPage(1);
    setIsLive(false);
    doSearch('', 1);
  };

  const totalPages = Math.max(1, Math.ceil(total / X_LIMIT));

  return (
    <Box>
      <Box display="flex" alignItems="center" gap={1} mb={2}>
        <TwitterIcon sx={{ color: '#1d9bf0', fontSize: 24 }} />
        <Typography variant="h6" fontWeight={700} fontSize="1rem">
          Tìm kiếm trên X (Twitter)
        </Typography>
        <Chip
          label={`${total} bài`}
          size="small"
          variant="outlined"
          sx={{ ml: 'auto', color: '#1d9bf0', borderColor: '#1d9bf0' }}
        />
      </Box>

      <Alert
        severity="info"
        icon={<TwitterIcon fontSize="small" sx={{ color: '#1d9bf0' }} />}
        sx={{
          mb: 2,
          py: 0.5,
          fontSize: '0.78rem',
          bgcolor: 'rgba(29,155,240,0.07)',
          border: '1px solid rgba(29,155,240,0.25)',
          '& .MuiAlert-icon': { color: '#1d9bf0' },
        }}
      >
        Nhập hashtag hoặc từ khóa rồi nhấn <strong>Tìm</strong> — hệ thống sẽ lấy tweet mới nhất từ X
        qua Apify (có thể mất 20–60 giây).
      </Alert>

      <Box display="flex" gap={1} mb={2} alignItems="center">
        <TextField
          size="small"
          placeholder="Nhập hashtag / từ khóa X…"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && handleSearch()}
          InputProps={{
            startAdornment: (
              <InputAdornment position="start">
                <TwitterIcon sx={{ fontSize: 16, color: '#1d9bf0' }} />
              </InputAdornment>
            ),
            endAdornment: input && (
              <InputAdornment position="end">
                <IconButton size="small" onClick={handleClear}>
                  <ClearIcon fontSize="small" />
                </IconButton>
              </InputAdornment>
            ),
          }}
          sx={{ flex: 1, maxWidth: 400 }}
        />
        <Tooltip title={loading ? 'Đang lấy dữ liệu…' : 'Tìm trên X (Apify live)'}>
          <span>
            <Button
              variant="contained"
              size="small"
              onClick={handleSearch}
              disabled={loading}
              sx={{
                textTransform: 'none',
                borderRadius: 2,
                boxShadow: 'none',
                bgcolor: '#1d9bf0',
                '&:hover': { bgcolor: '#1a8cd8' },
              }}
            >
              {loading ? <CircularProgress size={14} color="inherit" /> : 'Tìm'}
            </Button>
          </span>
        </Tooltip>
      </Box>

      {query && (
        <Box display="flex" alignItems="center" gap={1} mb={1.5}>
          <SearchIcon fontSize="small" color="action" />
          <Typography variant="subtitle2" fontWeight={700}>
            X results: "
            <Box component="span" color="#1d9bf0">
              {query}
            </Box>
            "
          </Typography>
          {isLive && (
            <Chip
              label="Mới từ Apify"
              size="small"
              sx={{ bgcolor: 'rgba(29,155,240,0.12)', color: '#1d9bf0', fontSize: '0.7rem' }}
            />
          )}
          <Button size="small" onClick={handleClear} sx={{ ml: 'auto', textTransform: 'none' }}>
            Xoá
          </Button>
        </Box>
      )}

      {error && (
        <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError(null)}>
          {error}
        </Alert>
      )}

      {loading ? (
        <Box>
          <Box display="flex" alignItems="center" gap={1} mb={2} sx={{ color: '#1d9bf0' }}>
            <CircularProgress size={14} sx={{ color: '#1d9bf0' }} />
            <Typography variant="caption" color="#1d9bf0">
              {query
                ? 'Đang lấy tweet mới nhất từ X qua Apify… (có thể mất 20–60 giây)'
                : 'Đang tải…'}
            </Typography>
          </Box>
          {[1, 2, 3].map((i) => (
            <CardSkeleton key={i} />
          ))}
        </Box>
      ) : posts.length === 0 ? (
        <Box textAlign="center" py={8}>
          <TwitterIcon sx={{ fontSize: 64, color: '#1d9bf0', opacity: 0.2, mb: 2 }} />
          <Typography color="text.secondary">
            {query ? 'Không tìm thấy tweet nào cho từ khóa này.' : 'Chưa có dữ liệu từ X.'}
          </Typography>
          <Typography variant="caption" color="text.disabled">
            {query
              ? 'Thử hashtag khác hoặc kiểm tra APIFY_API_TOKEN trong .env'
              : 'Nhập hashtag và nhấn Tìm để lấy dữ liệu mới'}
          </Typography>
        </Box>
      ) : (
        <Fade in>
          <Box>
            {posts.map((post, idx) => (
              <ArticleCard
                key={post._id || idx}
                post={post}
                selectedTopic=""
                searchQuery={query}
                onPlayAudio={(p) => setAudioPlayer(p)}
              />
            ))}
            {totalPages > 1 && (
              <Box display="flex" justifyContent="center" mt={2} mb={4}>
                <Pagination
                  count={totalPages}
                  page={page}
                  onChange={(_, v) => {
                    setPage(v);
                    doSearch(query, v);
                    window.scrollTo({ top: 0, behavior: 'smooth' });
                  }}
                  color="primary"
                  shape="rounded"
                />
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
