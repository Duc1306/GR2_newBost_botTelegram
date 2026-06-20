import React, { useState, useEffect } from 'react';
import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Box,
  Typography,
  Chip,
  Button,
  CircularProgress,
  Alert,
  Divider,
  useTheme,
  useMediaQuery,
} from '@mui/material';
import AutoAwesomeIcon from '@mui/icons-material/AutoAwesome';
import SentimentNeutralIcon from '@mui/icons-material/SentimentNeutral';
import HeadphonesIcon from '@mui/icons-material/Headphones';
import LinkIcon from '@mui/icons-material/Link';
import OpenInNewIcon from '@mui/icons-material/OpenInNew';
import { fetchHotNewsSummary, fetchHotNewsAudio } from '../../lib/publicApi.js';
import { SENTIMENT_COLOR } from '../../lib/helpers.jsx';

const SENTIMENT_LABEL = {
  positive: 'Tích cực',
  negative: 'Tiêu cực',
  mixed: 'Hỗn hợp',
  neutral: 'Trung lập',
};

export default function HotSummaryDialog({ cluster, open, onClose, hours = 24, onPlayAudio }) {
  const theme = useTheme();
  const isMobile = useMediaQuery(theme.breakpoints.down('sm'));
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [audioLoading, setAudioLoading] = useState(false);
  const [audioError, setAudioError] = useState(null);
  const [readUrls, setReadUrls] = useState(() => {
    try {
      return new Set(JSON.parse(localStorage.getItem('hn_read_urls') || '[]'));
    } catch {
      return new Set();
    }
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
    setReadUrls((prev) => {
      const next = new Set(prev);
      next.add(url);
      try {
        localStorage.setItem('hn_read_urls', JSON.stringify([...next]));
      } catch {}
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
      .catch((e) => {
        if (e?.name !== 'AbortError') setError(e.message);
      })
      .finally(() => setLoading(false));
    return () => ac.abort();
  }, [open, cluster, hours]);

  const sentimentColor = data ? SENTIMENT_COLOR[data.sentiment] || '#6b7280' : '#6b7280';

  return (
    <Dialog
      open={open}
      onClose={onClose}
      maxWidth="md"
      fullWidth
      fullScreen={isMobile}
      PaperProps={{ sx: { borderRadius: isMobile ? 0 : 3, maxHeight: isMobile ? '100vh' : '90vh' } }}
    >
      <DialogTitle
        sx={{
          pb: 1,
          bgcolor: cluster?.color ? `${cluster.color}14` : 'grey.50',
          borderBottom: '1px solid',
          borderColor: 'divider',
        }}
      >
        <Box display="flex" alignItems="center" gap={1.5}>
          <Box
            sx={{ width: 12, height: 12, borderRadius: '50%', bgcolor: cluster?.color || '#6b7280', flexShrink: 0 }}
          />
          <Typography
            variant="subtitle2"
            color="text.secondary"
            sx={{ textTransform: 'uppercase', letterSpacing: 0.6, fontSize: '0.7rem' }}
          >
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

        {error && <Alert severity="error" sx={{ mt: 1 }}>{error}</Alert>}

        {data && !loading && (
          <Box>
            {data.title && (
              <Typography
                variant="h5"
                fontWeight={800}
                sx={{ lineHeight: 1.35, mb: 2, color: 'text.primary' }}
              >
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
                      bgcolor:
                        data.risk_score >= 7
                          ? '#fde8e8'
                          : data.risk_score >= 4
                          ? '#fff3cd'
                          : '#e8f5e9',
                      border: '1px solid',
                      borderColor:
                        data.risk_score >= 7
                          ? '#f44336'
                          : data.risk_score >= 4
                          ? '#ff9800'
                          : '#4caf50',
                    }}
                  >
                    <Typography
                      variant="caption"
                      fontWeight={700}
                      sx={{
                        color:
                          data.risk_score >= 7
                            ? '#c62828'
                            : data.risk_score >= 4
                            ? '#e65100'
                            : '#2e7d32',
                      }}
                    >
                      ⚠ Rủi ro: {data.risk_score}/10
                    </Typography>
                  </Box>
                </>
              )}
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
              <Typography
                key={i}
                variant="body1"
                sx={{ lineHeight: 1.85, mb: 2, color: 'text.primary', fontSize: '0.97rem' }}
              >
                {para}
              </Typography>
            ))}

            {data.conclusion && (
              <Box
                sx={{
                  mt: 1,
                  mb: 2.5,
                  p: 2,
                  bgcolor: 'grey.50',
                  borderRadius: 2,
                  borderLeft: '3px solid',
                  borderColor: 'text.disabled',
                }}
              >
                <Typography
                  variant="body2"
                  sx={{ lineHeight: 1.75, color: 'text.secondary', fontStyle: 'italic' }}
                >
                  {data.conclusion}
                </Typography>
              </Box>
            )}

            {data.key_points?.length > 0 && (
              <>
                <Divider sx={{ mb: 2 }} />
                <Typography
                  variant="caption"
                  fontWeight={700}
                  color="text.secondary"
                  sx={{ textTransform: 'uppercase', letterSpacing: 0.8, display: 'block', mb: 1 }}
                >
                  Điểm nổi bật
                </Typography>
                <Box sx={{ display: 'flex', flexDirection: 'column', gap: 0.75 }}>
                  {data.key_points.map((pt, i) => (
                    <Box key={i} display="flex" alignItems="flex-start" gap={1}>
                      <Box
                        sx={{
                          width: 6,
                          height: 6,
                          borderRadius: '50%',
                          bgcolor: cluster?.color || 'primary.main',
                          mt: '7px',
                          flexShrink: 0,
                        }}
                      />
                      <Typography variant="body2" sx={{ lineHeight: 1.65, color: 'text.secondary' }}>
                        {pt}
                      </Typography>
                    </Box>
                  ))}
                </Box>
              </>
            )}

            {data &&
              (data.link_posts?.length > 0 || cluster?.posts?.length > 0) &&
              (() => {
                const rawSources =
                  data.link_posts?.length > 0
                    ? data.link_posts
                    : [
                        ...cluster.posts.filter((p) =>
                          p.links?.some((l) => l.startsWith('http') && !l.includes('t.me'))
                        ),
                        ...cluster.posts.filter(
                          (p) => !p.links?.some((l) => l.startsWith('http') && !l.includes('t.me'))
                        ),
                      ].map((p) => ({
                        title: p.full_article?.title || p.text || '',
                        url: p.links?.find((l) => l.startsWith('http') && !l.includes('t.me')) || null,
                        source: p.source || p.channel_username || '',
                        snippet: (p.text || '').slice(0, 200),
                      }));

                if (!rawSources.length) return null;

                const withLink = rawSources.filter((s) => s.url);
                const sources = [
                  ...rawSources.filter((s) => !s.url || !readUrls.has(s.url)),
                  ...rawSources.filter((s) => s.url && readUrls.has(s.url)),
                ];
                const readCount = rawSources.filter((s) => s.url && readUrls.has(s.url)).length;

                return (
                  <>
                    <Divider sx={{ my: 2.5 }} />
                    <Box display="flex" alignItems="center" gap={1} mb={1} flexWrap="wrap">
                      <Typography
                        variant="caption"
                        fontWeight={700}
                        color="text.secondary"
                        sx={{ textTransform: 'uppercase', letterSpacing: 0.8 }}
                      >
                        Nguồn tham khảo ({rawSources.length} bài
                        {withLink.length > 0 ? ` · ${withLink.length} có link` : ''})
                      </Typography>
                      {readCount > 0 && (
                        <Chip
                          label={`Đã đọc ${readCount}`}
                          size="small"
                          sx={{ height: 18, fontSize: '0.6rem', bgcolor: '#e5e7eb', color: '#6b7280' }}
                        />
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
                              border: isRead
                                ? '1px solid #e5e7eb'
                                : s.url
                                ? '1px solid #bbf7d0'
                                : '1px solid transparent',
                              opacity: isRead ? 0.6 : 1,
                              transition: 'opacity 0.2s',
                            }}
                          >
                            <Typography
                              variant="caption"
                              color="text.disabled"
                              sx={{ minWidth: 18, fontWeight: 700, pt: '2px', flexShrink: 0 }}
                            >
                              {i + 1}.
                            </Typography>
                            {s.url && !isRead && (
                              <LinkIcon sx={{ fontSize: 13, color: '#16a34a', mt: '2px', flexShrink: 0 }} />
                            )}
                            {isRead && (
                              <LinkIcon sx={{ fontSize: 13, color: '#9ca3af', mt: '2px', flexShrink: 0 }} />
                            )}
                            <Box sx={{ flex: 1, minWidth: 0 }}>
                              <Typography
                                variant="caption"
                                sx={{
                                  lineHeight: 1.6,
                                  display: 'block',
                                  fontWeight: s.url ? 600 : 400,
                                  color: isRead ? 'text.disabled' : 'text.primary',
                                }}
                              >
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
                                  textTransform: 'none',
                                  fontSize: '0.68rem',
                                  p: '1px 8px',
                                  minWidth: 0,
                                  flexShrink: 0,
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

      <DialogActions
        sx={{ px: 3, pb: 2, borderTop: '1px solid', borderColor: 'divider', gap: 1, flexWrap: 'wrap' }}
      >
        {data && !loading && (
          <>
            <Button
              onClick={handleListenClick}
              variant="contained"
              size="small"
              startIcon={
                audioLoading ? (
                  <CircularProgress size={14} color="inherit" />
                ) : (
                  <HeadphonesIcon sx={{ fontSize: '15px !important' }} />
                )
              }
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
        <Button
          onClick={onClose}
          variant="outlined"
          size="small"
          sx={{ textTransform: 'none', borderRadius: 2 }}
        >
          Đóng
        </Button>
      </DialogActions>
    </Dialog>
  );
}
