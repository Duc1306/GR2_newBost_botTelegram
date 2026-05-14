/**
 * PublicHomePage – trang tin tức công khai, không cần đăng nhập.
 * Hiển thị bảng tin tổng hợp từ các kênh hệ thống (dùng /public/* endpoints).
 */
import React, { useState, useEffect, useCallback, useRef } from 'react';
import { Link, Link as RouterLink } from 'react-router-dom';
import { formatDistanceToNow } from 'date-fns';
import { vi } from 'date-fns/locale';
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
  Tab,
  Tabs,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Divider,
  Grid,
  Pagination,
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
import NewspaperIcon from '@mui/icons-material/Newspaper';
import BoltIcon from '@mui/icons-material/Bolt';
import SentimentNeutralIcon from '@mui/icons-material/SentimentNeutral';
import TrendingUpIcon from '@mui/icons-material/TrendingUp';
import LinkIcon from '@mui/icons-material/Link';
import LoginIcon from '@mui/icons-material/Login';
import PersonAddIcon from '@mui/icons-material/PersonAdd';
import TelegramIcon from '@mui/icons-material/Telegram';
import HeadphonesIcon from '@mui/icons-material/Headphones';
import TwitterIcon from '@mui/icons-material/Twitter';
import FilterListIcon from '@mui/icons-material/FilterList';
import CalendarTodayIcon from '@mui/icons-material/CalendarToday';
import {
  searchPublicPosts,
  fetchArticlePosts,
  fetchHotNewsClusters,
  fetchHotNewsSummary,
  fetchHotNewsAudio,
  fetchPostTopics,
  searchXPosts,
} from '../../lib/publicApi.js';
import AudioPlayer from '../../components/AudioPlayer.jsx';

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

const SENTIMENT_COLOR = {
  positive: '#16a34a',
  negative: '#dc2626',
  mixed: '#d97706',
  neutral: '#6b7280',
};

// ─── Highlight keyword in text ───────────────────────────────────────────────

function highlightText(text, query) {
  if (!query || !text) return text;
  const words = query.trim().split(/\s+/).filter(Boolean);
  if (!words.length) return text;
  const pattern = new RegExp(`(${words.map(w => w.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')).join('|')})`, 'gi');
  const parts = text.split(pattern);
  return parts.map((part, i) =>
    pattern.test(part)
      ? <mark key={i} style={{ backgroundColor: '#fef08a', padding: '0 2px', borderRadius: 2 }}>{part}</mark>
      : part
  );
}

// ─── Article Card (link-only) ────────────────────────────────────────────────

const ArticleCard = React.memo(function ArticleCard({ post, selectedTopic, onPlayAudio, searchQuery = '' }) {
  const externalLink = post.links?.find((l) => !l.includes('t.me') && l.startsWith('http'));
  const title = post.full_article?.title || null;
  const primaryTopic = (selectedTopic && post.topics?.includes(selectedTopic))
    ? selectedTopic
    : post.topics?.[0];

  const [aiSummary, setAiSummary] = useState(null);
  const [loadingSummary, setLoadingSummary] = useState(false);
  const [loadingAudio, setLoadingAudio] = useState(false);

  const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000';

  const handleSummarize = async () => {
    if (loadingSummary || !post.id) return;
    setLoadingSummary(true);
    try {
      const res = await fetch(`${API_BASE}/public/posts/${encodeURIComponent(post.id)}/summarize`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
      });
      const data = await res.json();
      setAiSummary(res.ok ? data : {});
    } catch (_) {
      setAiSummary({});
    } finally {
      setLoadingSummary(false);
    }
  };

  const handleAudio = async () => {
    if (loadingAudio || !onPlayAudio) return;
    setLoadingAudio(true);
    let text = '';
    if (aiSummary && (aiSummary.lead || aiSummary.body?.length)) {
      const parts = [];
      if (aiSummary.lead) parts.push(aiSummary.lead);
      if (aiSummary.body?.length) parts.push(...aiSummary.body);
      text = parts.join('. ');
    } else {
      text = (post.text || '').slice(0, 1500);
    }
    try {
      const res = await fetch(`${API_BASE}/public/tts`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text: text.slice(0, 2000) }),
      });
      if (!res.ok) throw new Error('TTS failed');
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      onPlayAudio({ url, title: (title || post.text?.slice(0, 80) || 'Bài viết') });
    } catch (_) { /* silent */ }
    setLoadingAudio(false);
  };

  const hasSummary = aiSummary && (aiSummary.lead || aiSummary.body?.length > 0);

  return (
    <Card
      elevation={0}
      sx={{
        mb: 2,
        borderRadius: 2,
        border: '1px solid',
        borderColor: 'divider',
        transition: 'box-shadow 0.18s, transform 0.18s',
        '&:hover': { boxShadow: '0 6px 20px rgba(0,0,0,0.10)', transform: 'translateY(-2px)' },
      }}
    >
      <CardContent sx={{ pb: externalLink ? 0 : 1.5 }}>
        <Box display="flex" alignItems="center" gap={1} mb={0.75} flexWrap="wrap">
          {primaryTopic && (
            <Chip
              label={primaryTopic}
              size="small"
              sx={{ fontSize: '0.68rem', height: 20, bgcolor: '#fef3c7', color: '#92400e', fontWeight: 600 }}
            />
          )}
          <Typography variant="caption" color="text.secondary" sx={{ display: 'flex', alignItems: 'center', gap: 0.4 }}>
            <FiberManualRecordIcon sx={{ fontSize: 8, color: '#2563eb' }} />
            {post.source}
          </Typography>
          <Typography variant="caption" color="text.disabled" title={formatDateTime(post.created_at)}>
            · {timeAgo(post.created_at)}
          </Typography>
        </Box>

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
            }}
          >
            {searchQuery ? highlightText(title, searchQuery) : title}
          </Typography>
        )}

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
          {searchQuery ? highlightText(post.text, searchQuery) : post.text}
        </Typography>

        {/* Inline AI summary block */}
        {hasSummary && (
          <Box sx={{ bgcolor: '#f0f9ff', borderRadius: 1.5, p: 1.25, mt: 1 }}>
            {/* sentiment + risk_score badges */}
            {(aiSummary.sentiment || aiSummary.risk_score > 0) && (
              <Box display="flex" gap={0.75} mb={0.75} flexWrap="wrap">
                {aiSummary.sentiment && (() => {
                  const s = aiSummary.sentiment;
                  const map = {
                    positive: { label: '😊 Tích cực', color: '#166534', bg: '#dcfce7' },
                    negative: { label: '⚠️ Tiêu cực', color: '#991b1b', bg: '#fee2e2' },
                    mixed:    { label: '🔄 Hỗn hợp',  color: '#92400e', bg: '#fef3c7' },
                    neutral:  { label: '➖ Trung lập', color: '#374151', bg: '#f3f4f6' },
                  };
                  const style = map[s] || map.neutral;
                  return (
                    <Box component="span" sx={{
                      fontSize: '0.68rem', fontWeight: 600, px: 0.75, py: 0.2,
                      borderRadius: 1, bgcolor: style.bg, color: style.color,
                    }}>
                      {style.label}
                    </Box>
                  );
                })()}
                {aiSummary.risk_score >= 7 && (
                  <Box component="span" sx={{
                    fontSize: '0.68rem', fontWeight: 600, px: 0.75, py: 0.2,
                    borderRadius: 1, bgcolor: '#fee2e2', color: '#991b1b',
                  }}>
                    🔴 Rủi ro cao {aiSummary.risk_score}/10
                  </Box>
                )}
              </Box>
            )}
            {aiSummary.lead && (
              <Typography variant="caption" color="#0369a1"
                sx={{ display: 'block', fontWeight: 600, mb: 0.5, lineHeight: 1.6 }}>
                {aiSummary.lead}
              </Typography>
            )}
            {(aiSummary.body || []).map((b, i) => (
              <Typography key={i} variant="caption" color="text.secondary"
                sx={{ display: 'block', lineHeight: 1.6, mb: 0.25 }}>
                {b}
              </Typography>
            ))}
            {aiSummary.conclusion && (
              <Typography variant="caption"
                sx={{ display: 'block', lineHeight: 1.6, mt: 0.5, fontStyle: 'italic', color: '#0369a1', opacity: 0.8 }}>
                {aiSummary.conclusion}
              </Typography>
            )}
          </Box>
        )}
      </CardContent>

      <CardActions sx={{ px: 2, pt: 0.5, pb: 1.5, gap: 0.5, flexWrap: 'wrap' }}>
        {/* Tóm tắt AI */}
        <Button size="small"
          startIcon={loadingSummary
            ? <CircularProgress size={11} color="inherit" />
            : <AutoAwesomeIcon sx={{ fontSize: '13px !important' }} />}
          onClick={handleSummarize}
          disabled={loadingSummary}
          sx={{
            textTransform: 'none', fontSize: '0.75rem', borderRadius: 2, px: 1, py: 0.3,
            border: '1px solid', borderColor: hasSummary ? '#bfdbfe' : '#e5e7eb',
            color: hasSummary ? '#0369a1' : 'text.secondary',
          }}>
          {loadingSummary ? 'Đang tóm…' : hasSummary ? 'Tóm tắt ✓' : 'Tóm tắt AI'}
        </Button>

        {/* Nghe */}
        {onPlayAudio && (
          <Button size="small"
            startIcon={loadingAudio
              ? <CircularProgress size={11} color="inherit" />
              : <HeadphonesIcon sx={{ fontSize: '13px !important' }} />}
            onClick={handleAudio}
            disabled={loadingAudio}
            sx={{
              textTransform: 'none', fontSize: '0.75rem', borderRadius: 2, px: 1, py: 0.3,
              border: '1px solid', borderColor: hasSummary ? '#bfdbfe' : '#e5e7eb',
              color: hasSummary ? '#0369a1' : 'text.secondary',
            }}>
            {loadingAudio ? 'Đang tạo…' : hasSummary ? 'Nghe tóm tắt' : 'Nghe'}
          </Button>
        )}

        {externalLink && (
          <Button
            size="small"
            variant="contained"
            color="primary"
            endIcon={<OpenInNewIcon fontSize="small" />}
            href={externalLink}
            target="_blank"
            rel="noopener noreferrer"
            sx={{ textTransform: 'none', fontSize: '0.8rem', borderRadius: 2, px: 2, py: 0.4, boxShadow: 'none' }}
          >
            Đọc bài gốc
          </Button>
        )}
      </CardActions>
    </Card>
  );
});

// ─── Hot News Cluster Card ────────────────────────────────────────────────────

const HotClusterCard = React.memo(function HotClusterCard({ cluster, onReadSummary, isNew }) {
  return (
    <Card
      elevation={0}
      sx={{
        borderRadius: 2.5,
        border: '2px solid',
        borderColor: cluster.color || '#e5e7eb',
        transition: 'all 0.2s',
        height: '100%',
        display: 'flex',
        flexDirection: 'column',
        '&:hover': { boxShadow: `0 8px 24px ${cluster.color}33`, transform: 'translateY(-3px)' },
      }}
    >
      {/* Color header stripe */}
      <Box sx={{ height: 5, bgcolor: cluster.color || '#6b7280', borderRadius: '10px 10px 0 0' }} />

      <CardContent sx={{ flex: 1, pt: 1.5, pb: 0 }}>
        {/* Topic name */}
        <Box display="flex" alignItems="center" gap={0.75} mb={0.75} flexWrap="wrap">
          <WhatshotIcon sx={{ fontSize: 18, color: cluster.color }} />
          <Typography variant="subtitle2" fontWeight={700} sx={{ lineHeight: 1.3, color: cluster.color }}>
            {cluster.name}
          </Typography>
          {isNew && (
            <Chip label="Mới" size="small" sx={{ height: 18, fontSize: '0.6rem', fontWeight: 800, bgcolor: '#ef4444', color: 'white', px: 0.5 }} />
          )}
        </Box>

        {/* Headline */}
        <Typography
          variant="body2"
          fontWeight={500}
          mb={1}
          sx={{
            display: '-webkit-box',
            WebkitLineClamp: 3,
            WebkitBoxOrient: 'vertical',
            overflow: 'hidden',
            lineHeight: 1.55,
            color: 'text.primary',
          }}
        >
          {cluster.headline}
        </Typography>

        {/* Meta */}
        <Box display="flex" alignItems="center" gap={0.75} flexWrap="wrap">
          <Chip
            label={`${cluster.post_count} bài`}
            size="small"
            sx={{ fontSize: '0.68rem', height: 20, bgcolor: `${cluster.color}22`, color: cluster.color, fontWeight: 600 }}
          />
          {cluster.posts_with_links > 0 && (
            <Chip
              icon={<LinkIcon sx={{ fontSize: '11px !important' }} />}
              label={`${cluster.posts_with_links} link`}
              size="small"
              sx={{ fontSize: '0.68rem', height: 20, bgcolor: '#dcfce7', color: '#166534', fontWeight: 600 }}
            />
          )}
          {cluster.source === 'ai_discovered' && (
            <Chip
              label="AI phát hiện"
              size="small"
              sx={{ fontSize: '0.65rem', height: 20, bgcolor: '#fef3c7', color: '#92400e', fontWeight: 600 }}
            />
          )}
          <Typography variant="caption" color="text.disabled">
            {cluster.latest_at ? `Cập nhật ${timeAgo(cluster.latest_at)}` : ''}
          </Typography>

        </Box>
      </CardContent>

      <CardActions sx={{ px: 2, pt: 1, pb: 1.5 }}>
        <Button
          size="small"
          variant="outlined"
          startIcon={<AutoAwesomeIcon sx={{ fontSize: '14px !important' }} />}
          onClick={() => onReadSummary(cluster)}
          sx={{
            textTransform: 'none',
            fontSize: '0.78rem',
            borderRadius: 2,
            borderColor: cluster.color,
            color: cluster.color,
            '&:hover': { bgcolor: `${cluster.color}18`, borderColor: cluster.color },
          }}
        >
          Xem tóm tắt AI
        </Button>
      </CardActions>
    </Card>
  );
});

// ─── AI Summary Dialog ────────────────────────────────────────────────────────

const SENTIMENT_LABEL = { positive: 'Tích cực', negative: 'Tiêu cực', mixed: 'Hỗn hợp', neutral: 'Trung lập' };

function SummaryDialog({ cluster, open, onClose, hours = 48, onPlayAudio }) {
  const theme = useTheme();
  const isMobile = useMediaQuery(theme.breakpoints.down('sm'));
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [audioLoading, setAudioLoading] = useState(false);
  const [audioError, setAudioError] = useState(null);
  const [readUrls, setReadUrls] = useState(() => {
    try { return new Set(JSON.parse(localStorage.getItem('hn_read_urls') || '[]')); }
    catch { return new Set(); }
  });

  const handleListenClick = async () => {
    if (!cluster) return;
    setAudioLoading(true);
    setAudioError(null);
    try {
      const url = await fetchHotNewsAudio(cluster.slug, hours);
      onPlayAudio({ url, title: data?.title || cluster.name });
    } catch (e) {
      setAudioError(e.message);
    } finally {
      setAudioLoading(false);
    }
  };

  const markRead = (url) => {
    if (!url) return;
    setReadUrls(prev => {
      const next = new Set(prev);
      next.add(url);
      try { localStorage.setItem('hn_read_urls', JSON.stringify([...next])); } catch {}
      return next;
    });
  };

  useEffect(() => {
    if (!open || !cluster) return;
    setData(null);
    setError(null);
    setLoading(true);
    const ac = new AbortController();
    fetchHotNewsSummary(cluster.slug, hours, ac.signal)
      .then(setData)
      .catch((e) => { if (e?.name !== 'AbortError') setError(e.message); })
      .finally(() => setLoading(false));
    return () => ac.abort();
  }, [open, cluster, hours]);

  const sentimentColor = data ? (SENTIMENT_COLOR[data.sentiment] || '#6b7280') : '#6b7280';

  return (
    <Dialog
      open={open}
      onClose={onClose}
      maxWidth="md"
      fullWidth
      fullScreen={isMobile}
      PaperProps={{ sx: { borderRadius: isMobile ? 0 : 3, maxHeight: isMobile ? '100vh' : '90vh' } }}
    >
      {/* Header bar */}
      <DialogTitle sx={{ pb: 1, bgcolor: cluster?.color ? `${cluster.color}14` : 'grey.50', borderBottom: '1px solid', borderColor: 'divider' }}>
        <Box display="flex" alignItems="center" gap={1.5}>
          <Box sx={{ width: 12, height: 12, borderRadius: '50%', bgcolor: cluster?.color || '#6b7280', flexShrink: 0 }} />
          <Typography variant="subtitle2" color="text.secondary" sx={{ textTransform: 'uppercase', letterSpacing: 0.6, fontSize: '0.7rem' }}>
            {cluster?.name}
          </Typography>
          <Chip
            icon={<AutoAwesomeIcon sx={{ fontSize: '12px !important' }} />}
            label="AI tổng hợp"
            size="small"
            color="secondary"
            sx={{ ml: 'auto', fontSize: '0.65rem', height: 20 }}
          />
        </Box>
      </DialogTitle>

      <DialogContent sx={{ px: { xs: 2.5, sm: 4 }, py: 3 }}>
        {loading && (
          <Box display="flex" flexDirection="column" alignItems="center" py={6} gap={2}>
            <CircularProgress size={36} color="secondary" />
            <Typography variant="body2" color="text.secondary">
              Đang tổng hợp bài báo với AI…
            </Typography>
          </Box>
        )}

        {error && (
          <Alert severity="error" sx={{ mt: 1 }}>{error}</Alert>
        )}

        {data && !loading && (
          <Box>
            {data.title && (
              <Typography variant="h5" fontWeight={800} sx={{ lineHeight: 1.35, mb: 2, color: 'text.primary' }}>
                {data.title}
              </Typography>
            )}

            <Box display="flex" alignItems="center" flexWrap="wrap" gap={1} mb={2.5}>
              <Box display="flex" alignItems="center" gap={0.5}>
                <SentimentNeutralIcon sx={{ fontSize: 14, color: sentimentColor }} />
                <Typography variant="caption" sx={{ color: sentimentColor, fontWeight: 600 }}>
                  {SENTIMENT_LABEL[data.sentiment] || data.sentiment}
                </Typography>
              </Box>
              {data.risk_score != null && (
                <>
                  <Typography variant="caption" color="text.disabled">·</Typography>
                  <Box
                    sx={{
                      display: 'inline-flex',
                      alignItems: 'center',
                      gap: 0.4,
                      px: 1,
                      py: 0.2,
                      borderRadius: 1,
                      bgcolor: data.risk_score >= 7 ? '#fde8e8' : data.risk_score >= 4 ? '#fff3cd' : '#e8f5e9',
                      border: '1px solid',
                      borderColor: data.risk_score >= 7 ? '#f44336' : data.risk_score >= 4 ? '#ff9800' : '#4caf50',
                    }}
                  >
                    <Typography
                      variant="caption"
                      fontWeight={700}
                      sx={{ color: data.risk_score >= 7 ? '#c62828' : data.risk_score >= 4 ? '#e65100' : '#2e7d32' }}
                    >
                      ⚠ Rủi ro: {data.risk_score}/10
                    </Typography>
                  </Box>
                </>
              )}
              <Typography variant="caption" color="text.disabled">·</Typography>
              <Typography variant="caption" color="text.disabled">{data.post_count} nguồn tổng hợp</Typography>
              <Typography variant="caption" color="text.disabled">·</Typography>
              <Typography variant="caption" color="text.disabled">{data.cached ? 'từ cache' : 'vừa tổng hợp'}</Typography>
            </Box>

            <Divider sx={{ mb: 2.5 }} />

            {data.lead && (
              <Typography
                variant="body1"
                sx={{
                  fontWeight: 600,
                  lineHeight: 1.8,
                  mb: 2.5,
                  color: 'text.primary',
                  fontSize: '1.02rem',
                  borderLeft: '3px solid',
                  borderColor: cluster?.color || 'primary.main',
                  pl: 2,
                }}
              >
                {data.lead}
              </Typography>
            )}

            {data.body?.map((para, i) => (
              <Typography key={i} variant="body1" sx={{ lineHeight: 1.85, mb: 2, color: 'text.primary', fontSize: '0.97rem' }}>
                {para}
              </Typography>
            ))}

            {data.conclusion && (
              <Box sx={{ mt: 1, mb: 2.5, p: 2, bgcolor: 'grey.50', borderRadius: 2, borderLeft: '3px solid', borderColor: 'text.disabled' }}>
                <Typography variant="body2" sx={{ lineHeight: 1.75, color: 'text.secondary', fontStyle: 'italic' }}>
                  {data.conclusion}
                </Typography>
              </Box>
            )}

            {data.key_points?.length > 0 && (
              <>
                <Divider sx={{ mb: 2 }} />
                <Typography variant="caption" fontWeight={700} color="text.secondary" sx={{ textTransform: 'uppercase', letterSpacing: 0.8, display: 'block', mb: 1 }}>
                  Điểm nổi bật
                </Typography>
                <Box sx={{ display: 'flex', flexDirection: 'column', gap: 0.75 }}>
                  {data.key_points.map((pt, i) => (
                    <Box key={i} display="flex" alignItems="flex-start" gap={1}>
                      <Box sx={{ width: 6, height: 6, borderRadius: '50%', bgcolor: cluster?.color || 'primary.main', mt: '7px', flexShrink: 0 }} />
                      <Typography variant="body2" sx={{ lineHeight: 1.65, color: 'text.secondary' }}>{pt}</Typography>
                    </Box>
                  ))}
                </Box>
              </>
            )}

            {data && (data.link_posts?.length > 0 || cluster?.posts?.length > 0) && (() => {
              const rawSources = data.link_posts?.length > 0
                ? data.link_posts
                : [
                    ...cluster.posts.filter(p => p.links?.some(l => l.startsWith('http') && !l.includes('t.me'))),
                    ...cluster.posts.filter(p => !p.links?.some(l => l.startsWith('http') && !l.includes('t.me'))),
                  ].map(p => ({
                    title: p.full_article?.title || p.text || '',
                    url: p.links?.find(l => l.startsWith('http') && !l.includes('t.me')) || null,
                    source: p.source || p.channel_username || '',
                    snippet: (p.text || '').slice(0, 200),
                  }));

              if (!rawSources.length) return null;

              const withLink = rawSources.filter(s => s.url);
              const sources = [
                ...rawSources.filter(s => !s.url || !readUrls.has(s.url)),
                ...rawSources.filter(s => s.url && readUrls.has(s.url)),
              ];
              const readCount = rawSources.filter(s => s.url && readUrls.has(s.url)).length;

              return (
                <>
                  <Divider sx={{ my: 2.5 }} />
                  <Box display="flex" alignItems="center" gap={1} mb={1} flexWrap="wrap">
                    <Typography variant="caption" fontWeight={700} color="text.secondary" sx={{ textTransform: 'uppercase', letterSpacing: 0.8 }}>
                      Nguồn tham khảo ({rawSources.length} bài{withLink.length > 0 ? ` · ${withLink.length} có link` : ''})
                    </Typography>
                    {readCount > 0 && (
                      <Chip label={`Đã đọc ${readCount}`} size="small" sx={{ height: 18, fontSize: '0.6rem', bgcolor: '#e5e7eb', color: '#6b7280' }} />
                    )}
                  </Box>
                  <Box sx={{ display: 'flex', flexDirection: 'column', gap: 0.75 }}>
                    {sources.map((s, i) => {
                      const isRead = s.url && readUrls.has(s.url);
                      return (
                        <Box
                          key={s.url || i}
                          display="flex"
                          alignItems="flex-start"
                          gap={1}
                          sx={{
                            p: 1,
                            bgcolor: isRead ? '#f9fafb' : s.url ? '#f0fdf4' : 'grey.50',
                            borderRadius: 1.5,
                            border: isRead ? '1px solid #e5e7eb' : s.url ? '1px solid #bbf7d0' : '1px solid transparent',
                            opacity: isRead ? 0.6 : 1,
                            transition: 'opacity 0.2s',
                          }}
                        >
                          <Typography variant="caption" color="text.disabled" sx={{ minWidth: 18, fontWeight: 700, pt: '2px', flexShrink: 0 }}>{i + 1}.</Typography>
                          {s.url && !isRead && <LinkIcon sx={{ fontSize: 13, color: '#16a34a', mt: '2px', flexShrink: 0 }} />}
                          {isRead && <LinkIcon sx={{ fontSize: 13, color: '#9ca3af', mt: '2px', flexShrink: 0 }} />}
                          <Box sx={{ flex: 1, minWidth: 0 }}>
                            <Typography variant="caption" sx={{ lineHeight: 1.6, display: 'block', fontWeight: s.url ? 600 : 400, color: isRead ? 'text.disabled' : 'text.primary' }}>
                              {s.title || s.snippet || '(Không có tiêu đề)'}
                            </Typography>
                            {s.source && (
                              <Typography variant="caption" color="text.disabled" sx={{ fontSize: '0.65rem' }}>
                                {s.source}
                              </Typography>
                            )}
                          </Box>
                          {s.url && (
                            <Button
                              size="small"
                              endIcon={<OpenInNewIcon sx={{ fontSize: '11px !important' }} />}
                              href={s.url}
                              target="_blank"
                              rel="noopener noreferrer"
                              onClick={() => markRead(s.url)}
                              sx={{
                                textTransform: 'none', fontSize: '0.68rem', p: '1px 8px',
                                minWidth: 0, flexShrink: 0,
                                color: isRead ? '#9ca3af' : '#16a34a',
                              }}
                            >
                              {isRead ? 'Đọc lại' : 'Đọc'}
                            </Button>
                          )}
                        </Box>
                      );
                    })}
                  </Box>
                </>
              );
            })()}
          </Box>
        )}
      </DialogContent>

      <DialogActions sx={{ px: 3, pb: 2, borderTop: '1px solid', borderColor: 'divider', gap: 1, flexWrap: 'wrap' }}>
        {data && !loading && (
          <>
            <Button
              onClick={handleListenClick}
              variant="contained"
              size="small"
              startIcon={audioLoading ? <CircularProgress size={14} color="inherit" /> : <HeadphonesIcon sx={{ fontSize: '15px !important' }} />}
              disabled={audioLoading}
              sx={{
                textTransform: 'none',
                borderRadius: 2,
                bgcolor: '#f97316',
                '&:hover': { bgcolor: '#ea580c' },
                flexShrink: 0,
              }}
            >
              {audioLoading ? 'Đang tạo audio…' : 'Nghe bản tin'}
            </Button>
            {audioError && (
              <Typography variant="caption" color="error" sx={{ alignSelf: 'center' }}>
                {audioError}
              </Typography>
            )}
          </>
        )}
        <Box sx={{ flex: 1 }} />
        <Button onClick={onClose} variant="outlined" size="small" sx={{ textTransform: 'none', borderRadius: 2 }}>
          Đóng
        </Button>
      </DialogActions>
    </Dialog>
  );
}

// ─── Skeleton loaders ─────────────────────────────────────────────────────────

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

function ClusterSkeleton() {
  return (
    <Card elevation={0} sx={{ borderRadius: 2.5, border: '1px solid', borderColor: 'divider', height: 200 }}>
      <Box sx={{ height: 5, bgcolor: 'grey.200', borderRadius: '10px 10px 0 0' }} />
      <CardContent>
        <Skeleton variant="text" width="60%" height={24} />
        <Skeleton variant="text" width="100%" />
        <Skeleton variant="text" width="85%" />
        <Box mt={1}><Skeleton variant="rounded" width={80} height={20} /></Box>
      </CardContent>
    </Card>
  );
}

// ─── Breaking News Ticker ─────────────────────────────────────────────────────

function NewsTicker({ items }) {
  const texts = items.slice(0, 8).filter(Boolean);
  if (!texts.length) return null;
  const ticker = texts.join('   ·   ');

  return (
    <Box sx={{ bgcolor: '#ef4444', color: 'white', py: 0.6, overflow: 'hidden', display: 'flex', alignItems: 'center' }}>
      <Box sx={{ px: 2, fontWeight: 700, fontSize: '0.75rem', letterSpacing: 1, whiteSpace: 'nowrap', flexShrink: 0, bgcolor: '#b91c1c', alignSelf: 'stretch', display: 'flex', alignItems: 'center' }}>
        BREAKING
      </Box>
      <Box sx={{ overflow: 'hidden', flex: 1, maskImage: 'linear-gradient(to right, transparent 0%, black 4%, black 96%, transparent 100%)' }}>
        <Box component="marquee" scrollamount="4" sx={{ fontSize: '0.8rem', whiteSpace: 'nowrap', display: 'block' }}>
          {ticker}
        </Box>
      </Box>
    </Box>
  );
}

// ─── Hot News Tab ─────────────────────────────────────────────────────────────

function HotNewsTab() {
  const [clusters, setClusters] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [hours, setHours] = useState(48);
  const [selectedCluster, setSelectedCluster] = useState(null);
  const [summaryOpen, setSummaryOpen] = useState(false);
  const [audioPlayer, setAudioPlayer] = useState(null); // { url, title }
  const [pendingClusters, setPendingClusters] = useState([]);
  const [freshSlugs, setFreshSlugs] = useState(new Set());
  const [lastRefreshed, setLastRefreshed] = useState(null);
  const currentSlugsRef = useRef(new Set());

  const load = useCallback((h, signal) => {
    setLoading(true);
    setError(null);
    setPendingClusters([]);
    setFreshSlugs(new Set());
    fetchHotNewsClusters(h, signal)
      .then((d) => {
        const fresh = d.clusters || [];
        setClusters(fresh);
        currentSlugsRef.current = new Set(fresh.map(c => c.slug));
        setLastRefreshed(new Date());
      })
      .catch((e) => { if (e?.name !== 'AbortError') setError(e.message); })
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    const ac = new AbortController();
    load(hours, ac.signal);
    return () => ac.abort();
  }, [hours, load]);

  useEffect(() => {
    const ac = new AbortController();
    const id = setInterval(() => {
      fetchHotNewsClusters(hours, ac.signal)
        .then((d) => {
          const incoming = d.clusters || [];
          const truly = incoming.filter(c => !currentSlugsRef.current.has(c.slug));
          setClusters(prev => prev.map(c => incoming.find(f => f.slug === c.slug) || c));
          if (truly.length > 0) {
            setPendingClusters(prev => {
              const existSlugs = new Set(prev.map(p => p.slug));
              return [...prev, ...truly.filter(c => !existSlugs.has(c.slug))];
            });
          }
          setLastRefreshed(new Date());
        })
        .catch(() => {});
    }, 60_000);
    return () => { clearInterval(id); ac.abort(); };
  }, [hours]);

  const applyPending = () => {
    const slugs = new Set(pendingClusters.map(c => c.slug));
    setClusters(prev => {
      const existSlugs = new Set(prev.map(c => c.slug));
      const newOnes = pendingClusters.filter(c => !existSlugs.has(c.slug));
      newOnes.forEach(c => currentSlugsRef.current.add(c.slug));
      return [...newOnes, ...prev];
    });
    setFreshSlugs(prev => new Set([...prev, ...slugs]));
    setPendingClusters([]);
  };

  const handleReadSummary = (cluster) => {
    setSelectedCluster(cluster);
    setSummaryOpen(true);
  };

  return (
    <Box>
      <Box display="flex" alignItems={{ xs: 'flex-start', sm: 'center' }} justifyContent="space-between" mb={2.5} flexWrap="wrap" gap={1}>
        <Box>
          <Typography variant="h6" fontWeight={700} sx={{ display: 'flex', alignItems: 'center', gap: 0.75, fontSize: { xs: '1rem', sm: '1.25rem' } }}>
            <BoltIcon sx={{ color: '#f97316' }} /> Tin nóng theo chủ đề
          </Typography>
          <Typography variant="caption" color="text.secondary" sx={{ display: { xs: 'none', sm: 'block' } }}>
            Click "Xem tóm tắt AI" để đọc bản tóm lược được tổng hợp bằng OpenAI
          </Typography>
        </Box>
        <Box display="flex" gap={0.75} alignItems="center" flexWrap="wrap">
          {[24, 48, 72].map((h) => (
            <Chip
              key={h}
              label={`${h}h`}
              size="small"
              clickable
              onClick={() => setHours(h)}
              color={hours === h ? 'primary' : 'default'}
              variant={hours === h ? 'filled' : 'outlined'}
              sx={{ fontWeight: hours === h ? 700 : 500 }}
            />
          ))}
          <Tooltip title="Làm mới">
            <span>
              <IconButton size="small" onClick={() => load(hours)} disabled={loading}>
                <RefreshIcon fontSize="small" />
              </IconButton>
            </span>
          </Tooltip>
          {lastRefreshed && (
            <Typography variant="caption" color="text.disabled" sx={{ flexShrink: 0 }}>
              · {timeAgo(lastRefreshed)}
            </Typography>
          )}
        </Box>
      </Box>

      {pendingClusters.length > 0 && (
        <Box
          onClick={applyPending}
          sx={{
            cursor: 'pointer',
            mb: 2,
            p: 1.25,
            bgcolor: '#f97316',
            color: 'white',
            borderRadius: 2,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            gap: 1,
            fontWeight: 700,
            fontSize: '0.875rem',
            userSelect: 'none',
            '&:hover': { bgcolor: '#ea580c' },
            '@keyframes pulseBar': { '0%,100%': { opacity: 1 }, '50%': { opacity: 0.82 } },
            animation: 'pulseBar 2s infinite',
          }}
        >
          <BoltIcon sx={{ fontSize: 18 }} />
          {pendingClusters.length} chủ đề mới — Nhấn để hiển thị
        </Box>
      )}

      {error && <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError(null)}>{error}</Alert>}

      {loading ? (
        <Grid container spacing={2}>
          {[1, 2, 3, 4, 5, 6].map((i) => (
            <Grid size={{ xs: 12, sm: 6, md: 4 }} key={i}>
              <ClusterSkeleton />
            </Grid>
          ))}
        </Grid>
      ) : clusters.length === 0 ? (
        <Box textAlign="center" py={8}>
          <TrendingUpIcon sx={{ fontSize: 64, color: 'divider', mb: 2 }} />
          <Typography color="text.secondary">Chưa có tin nóng trong {hours} giờ qua.</Typography>
          <Typography variant="caption" color="text.disabled">Hãy chạy fetch để thu thập dữ liệu mới.</Typography>
        </Box>
      ) : (
        <Fade in>
          <Grid container spacing={2}>
            {clusters.map((cluster) => (
              <Grid size={{ xs: 12, sm: 6, md: 4 }} key={cluster.slug}>
                <HotClusterCard
                  cluster={cluster}
                  onReadSummary={handleReadSummary}
                  isNew={freshSlugs.has(cluster.slug)}
                />
              </Grid>
            ))}
          </Grid>
        </Fade>
      )}

      <SummaryDialog
        cluster={selectedCluster}
        open={summaryOpen}
        onClose={() => setSummaryOpen(false)}
        hours={hours}
        onPlayAudio={(p) => setAudioPlayer(p)}
      />

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

// ─── Articles Tab ─────────────────────────────────────────────────────────────

const ARTICLES_LIMIT = 20;
const REFRESH_INTERVAL_MS = 60_000;

function ArticlesTab() {
  const [postTopics, setPostTopics] = useState([]);
  const [topicsLoading, setTopicsLoading] = useState(true);
  const [selectedTopic, setSelectedTopic] = useState('');
  const [selectedPlatform, setSelectedPlatform] = useState('all');
  const [selectedDate, setSelectedDate] = useState('all'); // 'all' | 'today' | '7d' | '30d'
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

  // Compute date_from based on selectedDate filter
  const getDateFrom = useCallback(() => {
    const now = new Date();
    if (selectedDate === 'today') {
      return now.toISOString().slice(0, 10);
    } else if (selectedDate === '7d') {
      const d = new Date(now); d.setDate(d.getDate() - 7); return d.toISOString().slice(0, 10);
    } else if (selectedDate === '30d') {
      const d = new Date(now); d.setDate(d.getDate() - 30); return d.toISOString().slice(0, 10);
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
    if (!q) { setSearchResults(null); setSearchQuery(''); return; }
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

  const handleClearSearch = () => { setSearchInput(''); setSearchQuery(''); setSearchResults(null); };

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

      {/* ── Advanced Filters Row ──────────────────────── */}
      <Box display="flex" alignItems="center" gap={1} mb={1.5} flexWrap="wrap">
        <FilterListIcon sx={{ fontSize: 16, color: 'text.secondary' }} />
        <Typography variant="caption" color="text.secondary" fontWeight={600}>Nguồn:</Typography>
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
          <Typography variant="caption" color="text.secondary" fontWeight={600}>Thời gian:</Typography>
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
        {topicsLoading && [1, 2, 3, 4].map((i) => <Skeleton key={i} variant="rounded" width={100} height={24} sx={{ flexShrink: 0 }} />)}
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
            startAdornment: <InputAdornment position="start"><SearchIcon sx={{ fontSize: 18 }} color="action" /></InputAdornment>,
            endAdornment: searchInput && (
              <InputAdornment position="end">
                <IconButton size="small" onClick={handleClearSearch}><ClearIcon fontSize="small" /></IconButton>
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

      {error && <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError(null)}>{error}</Alert>}

      {searchQuery && (
        <Box display="flex" alignItems="center" gap={1} mb={2}>
          <SearchIcon fontSize="small" color="action" />
          <Typography variant="subtitle2" fontWeight={700}>
            Kết quả cho "<Box component="span" color="primary.main">{searchQuery}</Box>"
          </Typography>
          <Chip label={`${displayPosts.length} bài`} size="small" variant="outlined" color="primary" />
          <Button size="small" onClick={handleClearSearch} sx={{ ml: 'auto', textTransform: 'none' }}>Xoá</Button>
        </Box>
      )}

      {loading && displayPosts.length === 0 ? (
        <>{[1, 2, 3, 4, 5].map((i) => <CardSkeleton key={i} />)}</>
      ) : searchLoading ? (
        <Box display="flex" justifyContent="center" py={6}><CircularProgress /></Box>
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
              <ArticleCard key={post._id || idx} post={post} selectedTopic={selectedTopic} searchQuery={searchQuery} onPlayAudio={(p) => setAudioPlayer(p)} />
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
          onClose={() => { URL.revokeObjectURL(audioPlayer.url); setAudioPlayer(null); }}
        />
      )}
    </Box>
  );
}

// ─── X Search Tab ─────────────────────────────────────────────────────────────

function XSearchTab() {
  const [input, setInput] = useState('');
  const [query, setQuery] = useState('');
  const [posts, setPosts] = useState([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(false);
  const [isLive, setIsLive] = useState(false); // true = results just fetched from Apify
  const [error, setError] = useState(null);
  const [page, setPage] = useState(1);
  const [audioPlayer, setAudioPlayer] = useState(null);
  const abortRef = useRef(null);
  const X_LIMIT = 20;

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
      setIsLive(!!data.live); // backend returns live:true when Apify was triggered
    } catch (e) {
      if (e?.name !== 'AbortError') setError(e.message);
    } finally {
      if (!ac.signal.aborted) setLoading(false);
    }
  }, []);

  // Load latest X posts on mount
  useEffect(() => {
    doSearch('', 1);
  }, [doSearch]);

  const handleSearch = () => {
    const q = input.trim();
    setQuery(q);
    setPage(1);
    doSearch(q, 1);
  };

  const handleClear = () => { setInput(''); setQuery(''); setPage(1); setIsLive(false); doSearch('', 1); };

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

      {/* Hint: searches are live from Apify */}
      <Alert
        severity="info"
        icon={<TwitterIcon fontSize="small" sx={{ color: '#1d9bf0' }} />}
        sx={{
          mb: 2, py: 0.5, fontSize: '0.78rem',
          bgcolor: 'rgba(29,155,240,0.07)', border: '1px solid rgba(29,155,240,0.25)',
          '& .MuiAlert-icon': { color: '#1d9bf0' },
        }}
      >
        Nhập hashtag hoặc từ khóa rồi nhấn <strong>Tìm</strong> — hệ thống sẽ lấy tweet mới nhất từ X qua Apify (có thể mất 20–60 giây).
      </Alert>

      <Box display="flex" gap={1} mb={2} alignItems="center">
        <TextField
          size="small"
          placeholder="Nhập hashtag / từ khóa X…"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && handleSearch()}
          InputProps={{
            startAdornment: <InputAdornment position="start"><TwitterIcon sx={{ fontSize: 16, color: '#1d9bf0' }} /></InputAdornment>,
            endAdornment: input && (
              <InputAdornment position="end">
                <IconButton size="small" onClick={handleClear}><ClearIcon fontSize="small" /></IconButton>
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
              sx={{ textTransform: 'none', borderRadius: 2, boxShadow: 'none', bgcolor: '#1d9bf0', '&:hover': { bgcolor: '#1a8cd8' } }}
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
            X results: "<Box component="span" color="#1d9bf0">{query}</Box>"
          </Typography>
          {isLive && (
            <Chip label="Mới từ Apify" size="small" sx={{ bgcolor: 'rgba(29,155,240,0.12)', color: '#1d9bf0', fontSize: '0.7rem' }} />
          )}
          <Button size="small" onClick={handleClear} sx={{ ml: 'auto', textTransform: 'none' }}>Xoá</Button>
        </Box>
      )}

      {error && <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError(null)}>{error}</Alert>}

      {loading ? (
        <Box>
          <Box display="flex" alignItems="center" gap={1} mb={2} sx={{ color: '#1d9bf0' }}>
            <CircularProgress size={14} sx={{ color: '#1d9bf0' }} />
            <Typography variant="caption" color="#1d9bf0">
              {query ? 'Đang lấy tweet mới nhất từ X qua Apify… (có thể mất 20–60 giây)' : 'Đang tải…'}
            </Typography>
          </Box>
          {[1, 2, 3].map((i) => <CardSkeleton key={i} />)}
        </Box>
      ) : posts.length === 0 ? (
        <Box textAlign="center" py={8}>
          <TwitterIcon sx={{ fontSize: 64, color: '#1d9bf0', opacity: 0.2, mb: 2 }} />
          <Typography color="text.secondary">
            {query ? 'Không tìm thấy tweet nào cho từ khóa này.' : 'Chưa có dữ liệu từ X.'}
          </Typography>
          <Typography variant="caption" color="text.disabled">
            {query ? 'Thử hashtag khác hoặc kiểm tra APIFY_API_TOKEN trong .env' : 'Nhập hashtag và nhấn Tìm để lấy dữ liệu mới'}
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
                  onChange={(_, v) => { setPage(v); doSearch(query, v); window.scrollTo({ top: 0, behavior: 'smooth' }); }}
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
          onClose={() => { URL.revokeObjectURL(audioPlayer.url); setAudioPlayer(null); }}
        />
      )}
    </Box>
  );
}

// ─── Main Page ────────────────────────────────────────────────────────────────

export default function PublicHomePage() {
  const theme = useTheme();
  const isMobile = useMediaQuery(theme.breakpoints.down('sm'));
  const [activeTab, setActiveTab] = useState(0); // 0 = Hot News, 1 = Articles

  const [tickerPosts, setTickerPosts] = useState([]);

  useEffect(() => {
    const ac = new AbortController();
    fetchArticlePosts('', 0, 10, '', ac.signal)
      .then((d) => setTickerPosts(d.posts || []))
      .catch(() => {});
    return () => ac.abort();
  }, []);

  const tickerTexts = tickerPosts
    .map((p) => p.full_article?.title || p.text?.slice(0, 80))
    .filter(Boolean);

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
            <Box display="flex" alignItems="center" gap={1.5}>
              <LocalFireDepartmentIcon sx={{ fontSize: { xs: 28, md: 36 }, color: '#ff6b35' }} />
              <Box>
                <Typography variant="h5" fontWeight={800} letterSpacing={1.5} sx={{ fontSize: { xs: '1.1rem', md: '1.4rem' } }}>
                  📡 BẢNG TIN NÓNG
                </Typography>
                <Typography variant="caption" sx={{ opacity: 0.7, display: { xs: 'none', sm: 'block' } }}>
                  Tin tức thời sự quốc tế &amp; trong nước · AI tóm tắt · Cập nhật liên tục
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
                  '@keyframes livePulse': { '0%, 100%': { opacity: 1 }, '50%': { opacity: 0.55 } },
                }}
              />
            </Box>

            {/* Login / Register */}
            <Box display="flex" alignItems="center" gap={1}>
              <Button
                component={RouterLink}
                to="/login"
                variant="outlined"
                size="small"
                startIcon={<LoginIcon />}
                sx={{
                  color: 'white',
                  borderColor: 'rgba(255,255,255,0.5)',
                  '&:hover': { borderColor: 'white', bgcolor: 'rgba(255,255,255,0.1)' },
                  textTransform: 'none',
                  borderRadius: 2,
                }}
              >
                {isMobile ? null : 'Đăng nhập'}
              </Button>
              <Button
                component={RouterLink}
                to="/register"
                variant="contained"
                size="small"
                startIcon={<PersonAddIcon />}
                sx={{
                  bgcolor: '#f97316',
                  '&:hover': { bgcolor: '#ea580c' },
                  textTransform: 'none',
                  borderRadius: 2,
                }}
              >
                {isMobile ? null : 'Đăng ký'}
              </Button>
            </Box>
          </Box>
        </Container>
      </Box>

      {/* ── Breaking Ticker ── */}
      <NewsTicker items={tickerTexts} />

      {/* ── Tab bar ── */}
      <Box
        sx={{
          bgcolor: 'background.paper',
          borderBottom: '1px solid',
          borderColor: 'divider',
          position: 'sticky',
          top: 0,
          zIndex: 200,
          boxShadow: '0 2px 8px rgba(0,0,0,0.06)',
        }}
      >
        <Container maxWidth="lg" disableGutters>
          <Tabs
            value={activeTab}
            onChange={(_, v) => setActiveTab(v)}
            variant="scrollable"
            scrollButtons="auto"
            allowScrollButtonsMobile
            sx={{
              minHeight: 46,
              '& .MuiTab-root': { textTransform: 'none', fontWeight: 600, fontSize: '0.9rem', minHeight: 46 },
            }}
          >
            <Tab
              icon={<BoltIcon sx={{ fontSize: 18 }} />}
              iconPosition="start"
              label="Hot News"
              sx={{ color: activeTab === 0 ? '#f97316' : undefined }}
            />
            <Tab
              icon={<NewspaperIcon sx={{ fontSize: 18 }} />}
              iconPosition="start"
              label={isMobile ? 'Bài báo' : 'Bài báo theo chủ đề'}
            />
            <Tab
              icon={<TwitterIcon sx={{ fontSize: 18 }} />}
              iconPosition="start"
              label="Tìm trên X"
              sx={{ color: activeTab === 2 ? '#1d9bf0' : undefined }}
            />
          </Tabs>
        </Container>
      </Box>

      {/* ── Main Content ── */}
      <Container maxWidth="lg" sx={{ py: { xs: 2, md: 3 } }}>
        {/* CTA Banner */}
        <Alert
          severity="info"
          icon={false}
          sx={{ mb: 3, borderRadius: 2, bgcolor: '#eff6ff', border: '1px solid #bfdbfe' }}
          action={
             <Button
              fullWidth
              variant="outlined"
              size="large"
              component={Link}
              to="/login/telegram"
              startIcon={<TelegramIcon />}
              sx={{
                py: 1.4,
                textTransform: 'none',
                fontSize: '0.95rem',
                borderColor: '#0088cc',
                color: '#0088cc',
                '&:hover': { borderColor: '#006699', bgcolor: '#f0f8ff' },
              }}
            >
              Đăng nhập bằng Số điện thoại Telegram
            </Button>
          }
        >
          <Typography variant="body2" fontWeight={600}>Muốn tóm tắt kênh Telegram cá nhân?</Typography>
          <Typography variant="caption" color="text.secondary">
            Tạo tài khoản và thêm kênh bạn muốn theo dõi — AI sẽ tóm tắt tự động.
          </Typography>
        </Alert>

        <Box sx={{ display: activeTab === 0 ? 'block' : 'none' }}><HotNewsTab /></Box>
        <Box sx={{ display: activeTab === 1 ? 'block' : 'none' }}><ArticlesTab /></Box>
        <Box sx={{ display: activeTab === 2 ? 'block' : 'none' }}><XSearchTab /></Box>

        {/* Footer */}
        <Box textAlign="center" py={3} mt={2} borderTop="1px solid" borderColor="divider">
          <Typography variant="caption" color="text.disabled">
            Bản tin tổng hợp từ Telegram · AI tóm tắt bởi OpenAI · {new Date().getFullYear()}
          </Typography>
        </Box>
      </Container>
    </Box>
  );
}

