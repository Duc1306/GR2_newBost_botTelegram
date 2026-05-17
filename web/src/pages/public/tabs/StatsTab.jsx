import React, { useState, useEffect, useCallback, useRef } from 'react';
import {
  Box,
  Typography,
  Chip,
  CircularProgress,
  Alert,
  Grid,
  Pagination,
  TextField,
  InputAdornment,
  Stack,
} from '@mui/material';
import PublicIcon from '@mui/icons-material/Public';
import SearchIcon from '@mui/icons-material/Search';
import { fetchGeoStats, fetchArticlePosts } from '../../../lib/publicApi.js';
import ArticleCard from '../../../components/public/ArticleCard.jsx';
import AudioPlayer from '../../../components/AudioPlayer.jsx';

const PAGE_SIZE = 12;

export default function StatsTab() {
  // ── Geo region list ─────────────────────────────────────────────────────
  const [regions, setRegions] = useState([]);
  const [loadingRegions, setLoadingRegions] = useState(true);

  // ── Selected filter ──────────────────────────────────────────────────────
  const [selectedRegion, setSelectedRegion] = useState(null); // null = all
  const [searchQuery, setSearchQuery] = useState('');

  // ── Articles ─────────────────────────────────────────────────────────────
  const [articles, setArticles] = useState([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [loadingArticles, setLoadingArticles] = useState(false);
  const [error, setError] = useState('');

  const [audioPlayer, setAudioPlayer] = useState(null);
  const abortRef = useRef(null);

  // Load regions on mount
  useEffect(() => {
    fetchGeoStats(30)
      .then((d) => setRegions(d.has_data ? (d.geo || []) : []))
      .catch(() => setRegions([]))
      .finally(() => setLoadingRegions(false));
  }, []);

  const loadArticles = useCallback(async (region, q, pg) => {
    abortRef.current?.abort();
    const ac = new AbortController();
    abortRef.current = ac;

    setLoadingArticles(true);
    setError('');
    try {
      const skip = (pg - 1) * PAGE_SIZE;
      const data = await fetchArticlePosts(
        '',          // topic
        skip,
        PAGE_SIZE,
        q,           // search query
        ac.signal,
        '',          // platform
        '',          // dateFrom
        '',          // dateTo
        region || '', // geo
      );
      setArticles(data.posts || []);
      setTotal(data.total || 0);
    } catch (e) {
      if (e?.name !== 'AbortError') setError('Không tải được bài viết.');
    } finally {
      setLoadingArticles(false);
    }
  }, []);

  // Reload when filters change
  useEffect(() => {
    loadArticles(selectedRegion, searchQuery, page);
  }, [selectedRegion, searchQuery, page, loadArticles]);

  const handleRegionClick = (region) => {
    const next = selectedRegion === region ? null : region;
    setSelectedRegion(next);
    setPage(1);
  };

  const handleSearch = (e) => {
    setSearchQuery(e.target.value);
    setPage(1);
  };

  const handlePlayAudio = ({ url, title }) => {
    setAudioPlayer((prev) => {
      if (prev?.url && prev.url !== url) URL.revokeObjectURL(prev.url);
      return { url, title };
    });
  };
  const handleCloseAudio = () => {
    setAudioPlayer((prev) => {
      if (prev?.url) URL.revokeObjectURL(prev.url);
      return null;
    });
  };

  const totalPages = Math.ceil(total / PAGE_SIZE);

  return (
    <Box>
      {/* ── Header ── */}
      <Box display="flex" alignItems="center" gap={1} mb={2}>
        <PublicIcon sx={{ color: '#f97316' }} />
        <Typography variant="h6" fontWeight={700} fontSize="1rem">
          Khám phá theo khu vực địa lý
        </Typography>
      </Box>
      <Typography variant="body2" color="text.secondary" mb={2.5}>
        Chọn một khu vực để xem các bài báo liên quan — ví dụ: Ukraine, Mỹ, Trung Đông…
      </Typography>

      {/* ── Region chips ── */}
      {loadingRegions ? (
        <Box display="flex" alignItems="center" gap={1} mb={2}>
          <CircularProgress size={18} />
          <Typography variant="caption" color="text.secondary">Đang tải khu vực…</Typography>
        </Box>
      ) : regions.length === 0 ? (
        <Alert severity="info" sx={{ mb: 2, borderRadius: 2 }}>
          Chưa có dữ liệu phân loại địa lý. Hãy chạy pipeline backfill để phân loại bài viết theo khu vực.
        </Alert>
      ) : (
        <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap', mb: 2.5 }}>
          <Chip
            label="🌐 Tất cả"
            onClick={() => handleRegionClick(null)}
            color={!selectedRegion ? 'primary' : 'default'}
            variant={!selectedRegion ? 'filled' : 'outlined'}
            sx={{ fontWeight: !selectedRegion ? 700 : 400, cursor: 'pointer' }}
          />
          {regions.map((r) => (
            <Chip
              key={r.region}
              label={`${r.emoji} ${r.region} (${r.count.toLocaleString()})`}
              onClick={() => handleRegionClick(r.region)}
              color={selectedRegion === r.region ? 'primary' : 'default'}
              variant={selectedRegion === r.region ? 'filled' : 'outlined'}
              sx={{
                fontWeight: selectedRegion === r.region ? 700 : 400,
                cursor: 'pointer',
                borderColor: selectedRegion === r.region ? undefined : r.color,
                '&:hover': { borderColor: r.color },
              }}
            />
          ))}
        </Box>
      )}

      {/* ── Search within region ── */}
      <TextField
        size="small"
        placeholder={selectedRegion ? `Tìm trong ${selectedRegion}…` : 'Tìm kiếm bài viết…'}
        value={searchQuery}
        onChange={handleSearch}
        sx={{ mb: 2.5, width: { xs: '100%', sm: 360 } }}
        InputProps={{
          startAdornment: (
            <InputAdornment position="start">
              <SearchIcon fontSize="small" sx={{ color: 'text.disabled' }} />
            </InputAdornment>
          ),
        }}
      />

      {/* ── Result count ── */}
      {!loadingArticles && !error && (
        <Typography variant="caption" color="text.secondary" display="block" mb={1.5}>
          {selectedRegion
            ? `${total.toLocaleString()} bài viết về "${selectedRegion}"`
            : `${total.toLocaleString()} bài viết`}
          {searchQuery ? ` · tìm kiếm: "${searchQuery}"` : ''}
        </Typography>
      )}

      {/* ── Articles ── */}
      {loadingArticles ? (
        <Box display="flex" justifyContent="center" py={6}>
          <CircularProgress />
        </Box>
      ) : error ? (
        <Alert severity="error" sx={{ borderRadius: 2 }}>{error}</Alert>
      ) : articles.length === 0 ? (
        <Box textAlign="center" py={6}>
          <PublicIcon sx={{ fontSize: 48, color: '#e5e7eb', mb: 1 }} />
          <Typography color="text.secondary">
            {selectedRegion
              ? `Không có bài viết nào cho khu vực "${selectedRegion}"${searchQuery ? ` với từ khóa "${searchQuery}"` : ''}.`
              : 'Chưa có bài viết nào.'}
          </Typography>
        </Box>
      ) : (
        <>
          <Grid container spacing={2} mb={3}>
            {articles.map((post) => (
              <Grid item xs={12} sm={6} md={4} key={post.id || post._id}>
                <ArticleCard
                  post={post}
                  selectedTopic={null}
                  onPlayAudio={handlePlayAudio}
                  searchQuery={searchQuery}
                />
              </Grid>
            ))}
          </Grid>

          {totalPages > 1 && (
            <Stack alignItems="center" mt={1}>
              <Pagination
                count={totalPages}
                page={page}
                onChange={(_, v) => { setPage(v); window.scrollTo({ top: 0, behavior: 'smooth' }); }}
                color="primary"
                shape="rounded"
              />
            </Stack>
          )}
        </>
      )}

      {audioPlayer && (
        <AudioPlayer audioUrl={audioPlayer.url} title={audioPlayer.title} onClose={handleCloseAudio} />
      )}
    </Box>
  );
}

