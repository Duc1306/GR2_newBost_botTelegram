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
  Tab,
  Tabs,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Divider,
  Grid,
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

import NewspaperIcon from '@mui/icons-material/Newspaper';
import BoltIcon from '@mui/icons-material/Bolt';
import SentimentNeutralIcon from '@mui/icons-material/SentimentNeutral';
import TrendingUpIcon from '@mui/icons-material/TrendingUp';
import LinkIcon from '@mui/icons-material/Link';
import {
  searchPublicPosts,
  fetchArticlePosts,
  fetchHotNewsClusters,
  fetchHotNewsSummary,
  fetchPostTopics,
} from '../../lib/publicApi.js';

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

// ─── Article Card (link-only) ────────────────────────────────────────────────

function ArticleCard({ post }) {
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
            {title}
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
            sx={{ textTransform: 'none', fontSize: '0.8rem', borderRadius: 2, px: 2, py: 0.5, boxShadow: 'none' }}
          >
            Đọc bài gốc
          </Button>
        </CardActions>
      )}
    </Card>
  );
}

// ─── Hot News Cluster Card ────────────────────────────────────────────────────

function HotClusterCard({ cluster, onReadSummary, isNew }) {
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
            {cluster.latest_at ? timeAgo(cluster.latest_at) : ''}
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
}

// ─── AI Summary Dialog ────────────────────────────────────────────────────────

const SENTIMENT_LABEL = { positive: 'Tích cực', negative: 'Tiêu cực', mixed: 'Hỗn hợp', neutral: 'Trung lập' };

function SummaryDialog({ cluster, open, onClose }) {
  const theme = useTheme();
  const isMobile = useMediaQuery(theme.breakpoints.down('sm'));
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [readUrls, setReadUrls] = useState(() => {
    try { return new Set(JSON.parse(localStorage.getItem('hn_read_urls') || '[]')); }
    catch { return new Set(); }
  });

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
    fetchHotNewsSummary(cluster.slug)
      .then(setData)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, [open, cluster]);

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
        {/* Loading */}
        {loading && (
          <Box display="flex" flexDirection="column" alignItems="center" py={6} gap={2}>
            <CircularProgress size={36} color="secondary" />
            <Typography variant="body2" color="text.secondary">
              Đang tổng hợp bài báo với AI…
            </Typography>
          </Box>
        )}

        {/* Error */}
        {error && (
          <Alert severity="error" sx={{ mt: 1 }}>{error}</Alert>
        )}

        {/* Article body */}
        {data && !loading && (
          <Box>
            {/* Article title */}
            {data.title && (
              <Typography
                variant="h5"
                fontWeight={800}
                sx={{ lineHeight: 1.35, mb: 2, color: 'text.primary' }}
              >
                {data.title}
              </Typography>
            )}

            {/* Meta row */}
            <Box display="flex" alignItems="center" flexWrap="wrap" gap={1} mb={2.5}>
              <Box display="flex" alignItems="center" gap={0.5}>
                <SentimentNeutralIcon sx={{ fontSize: 14, color: sentimentColor }} />
                <Typography variant="caption" sx={{ color: sentimentColor, fontWeight: 600 }}>
                  {SENTIMENT_LABEL[data.sentiment] || data.sentiment}
                </Typography>
              </Box>
              <Typography variant="caption" color="text.disabled">·</Typography>
              <Typography variant="caption" color="text.disabled">
                {data.post_count} nguồn tổng hợp
              </Typography>
              <Typography variant="caption" color="text.disabled">·</Typography>
              <Typography variant="caption" color="text.disabled">
                {data.cached ? 'từ cache' : 'vừa tổng hợp'}
              </Typography>
            </Box>

            <Divider sx={{ mb: 2.5 }} />

            {/* Lead paragraph */}
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

            {/* Body paragraphs */}
            {data.body?.map((para, i) => (
              <Typography
                key={i}
                variant="body1"
                sx={{ lineHeight: 1.85, mb: 2, color: 'text.primary', fontSize: '0.97rem' }}
              >
                {para}
              </Typography>
            ))}

            {/* Conclusion */}
            {data.conclusion && (
              <Box sx={{ mt: 1, mb: 2.5, p: 2, bgcolor: 'grey.50', borderRadius: 2, borderLeft: '3px solid', borderColor: 'text.disabled' }}>
                <Typography variant="body2" sx={{ lineHeight: 1.75, color: 'text.secondary', fontStyle: 'italic' }}>
                  {data.conclusion}
                </Typography>
              </Box>
            )}

            {/* Key points */}
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

            {/* Source links — ALL link posts from summary API */}
            {data && (data.link_posts?.length > 0 || cluster?.posts?.length > 0) && (() => {
              // Prefer link_posts from API (full list); fall back to cluster.posts
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

              // Sort: unread first, read ones pushed to bottom
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
                      Nguồn tham khảo ({sources.length} bài{data.link_posts?.length > 0 ? ` · ${data.link_posts.length} có link` : ''})
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
                            isRead ? (
                              <Typography variant="caption" sx={{ fontSize: '0.65rem', color: '#9ca3af', flexShrink: 0, alignSelf: 'center' }}>
                                Đã đọc
                              </Typography>
                            ) : (
                              <Button
                                size="small"
                                endIcon={<OpenInNewIcon sx={{ fontSize: '11px !important' }} />}
                                href={s.url}
                                target="_blank"
                                rel="noopener noreferrer"
                                onClick={() => markRead(s.url)}
                                sx={{ textTransform: 'none', fontSize: '0.68rem', p: '1px 8px', minWidth: 0, flexShrink: 0, color: '#16a34a' }}
                              >
                                Đọc
                              </Button>
                            )
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

      <DialogActions sx={{ px: 3, pb: 2, borderTop: '1px solid', borderColor: 'divider' }}>
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
  const [pendingClusters, setPendingClusters] = useState([]);
  const [freshSlugs, setFreshSlugs] = useState(new Set());
  const [lastRefreshed, setLastRefreshed] = useState(null);
  const currentSlugsRef = useRef(new Set());

  const load = useCallback((h) => {
    setLoading(true);
    setError(null);
    setPendingClusters([]);
    setFreshSlugs(new Set());
    fetchHotNewsClusters(h)
      .then((d) => {
        const fresh = d.clusters || [];
        setClusters(fresh);
        currentSlugsRef.current = new Set(fresh.map(c => c.slug));
        setLastRefreshed(new Date());
      })
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => { load(hours); }, [hours, load]);

  // Real-time polling every 60s
  useEffect(() => {
    const id = setInterval(() => {
      fetchHotNewsClusters(hours)
        .then((d) => {
          const incoming = d.clusters || [];
          const truly = incoming.filter(c => !currentSlugsRef.current.has(c.slug));
          // Silently update counts on existing clusters
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
    return () => clearInterval(id);
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
      {/* Controls */}
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
            <IconButton size="small" onClick={() => load(hours)} disabled={loading}>
              <RefreshIcon fontSize="small" />
            </IconButton>
          </Tooltip>
          {lastRefreshed && (
            <Typography variant="caption" color="text.disabled" sx={{ flexShrink: 0 }}>
              · {timeAgo(lastRefreshed)}
            </Typography>
          )}
        </Box>
      </Box>

      {/* Pending banner — tap to apply new clusters */}
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
            <Grid item xs={12} sm={6} md={4} key={i}>
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
              <Grid item xs={12} sm={6} md={4} key={cluster.slug}>
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
      />
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
  const [posts, setPosts] = useState([]);
  const [total, setTotal] = useState(0);
  const [skip, setSkip] = useState(0);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [searchInput, setSearchInput] = useState('');
  const [searchQuery, setSearchQuery] = useState('');
  const [searchResults, setSearchResults] = useState(null);
  const [searchLoading, setSearchLoading] = useState(false);
  const [lastUpdate, setLastUpdate] = useState(new Date());
  const timerRef = useRef(null);

  useEffect(() => {
    fetchPostTopics()
      .then((d) => setPostTopics(d.topics || []))
      .catch(() => {})
      .finally(() => setTopicsLoading(false));
  }, []);

  const loadPosts = useCallback(async (topic, currentSkip, append = false) => {
    setLoading(true);
    setError(null);
    try {
      const data = await fetchArticlePosts(topic, currentSkip, ARTICLES_LIMIT);
      const incoming = data.posts || [];
      setPosts((prev) => (append ? [...prev, ...incoming] : incoming));
      setTotal(data.total ?? incoming.length);
      setLastUpdate(new Date());
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    setSearchQuery('');
    setSearchInput('');
    setSearchResults(null);
    setSkip(0);
    loadPosts(selectedTopic, 0);
  }, [selectedTopic, loadPosts]);

  useEffect(() => {
    if (timerRef.current) clearInterval(timerRef.current);
    timerRef.current = setInterval(() => {
      if (!searchQuery) { setSkip(0); loadPosts(selectedTopic, 0); }
    }, REFRESH_INTERVAL_MS);
    return () => clearInterval(timerRef.current);
  }, [selectedTopic, searchQuery, loadPosts]);

  const handleLoadMore = () => {
    const newSkip = skip + ARTICLES_LIMIT;
    setSkip(newSkip);
    loadPosts(selectedTopic, newSkip, true);
  };

  const handleSearch = async () => {
    const q = searchInput.trim();
    if (!q) { setSearchResults(null); setSearchQuery(''); return; }
    setSearchQuery(q);
    setSearchLoading(true);
    try {
      const data = await searchPublicPosts(q, 30);
      // keep only posts with links
      const withLinks = (data.posts || []).filter((p) =>
        p.links?.some((l) => !l.includes('t.me') && l.startsWith('http'))
      );
      setSearchResults(withLinks);
    } catch (e) {
      setError(e.message);
    } finally {
      setSearchLoading(false);
    }
  };

  const handleClearSearch = () => { setSearchInput(''); setSearchQuery(''); setSearchResults(null); };

  const displayPosts = searchResults !== null ? searchResults : posts;
  const hasMore = searchResults === null && posts.length < total;

  return (
    <Box>
      {/* Topic filter bar */}
      {/* Section header */}
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
              <ArticleCard key={post._id || idx} post={post} />
            ))}
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
    </Box>
  );
}

// ─── Main Page ────────────────────────────────────────────────────────────────

export default function UserNewsPage() {
  const theme = useTheme();
  const isMobile = useMediaQuery(theme.breakpoints.down('sm'));
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  const handleLogout = async () => {
    await logout();
    navigate('/login');
  };

  const [activeTab, setActiveTab] = useState(0); // 0 = Hot News, 1 = Articles

  // Breaking ticker state (latest posts for marquee)
  const [tickerPosts, setTickerPosts] = useState([]);

  // Load ticker from latest posts
  useEffect(() => {
    fetchArticlePosts('', 0, 10)
      .then((d) => setTickerPosts(d.posts || []))
      .catch(() => {});
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

            <Box display="flex" alignItems="center" gap={1}>
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
          </Tabs>
        </Container>
      </Box>

      {/* ── Main Content ── */}
      <Container maxWidth="lg" sx={{ py: { xs: 2, md: 3 } }}>
        {activeTab === 0 && <HotNewsTab />}
        {activeTab === 1 && <ArticlesTab />}

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
