import React, { useState, useCallback, useMemo } from 'react';
import {
  Box, Typography, Grid, Paper, Chip, CircularProgress, Card, CardContent,
  LinearProgress, IconButton, Tooltip, ButtonGroup, Button, Stack,
} from '@mui/material';
import TrendingUpIcon from '@mui/icons-material/TrendingUp';
import TrendingDownIcon from '@mui/icons-material/TrendingDown';
import WhatshotIcon from '@mui/icons-material/Whatshot';
import TelegramIcon from '@mui/icons-material/Telegram';
import OpenInNewIcon from '@mui/icons-material/OpenInNew';
import RocketLaunchIcon from '@mui/icons-material/RocketLaunch';
import LocalFireDepartmentIcon from '@mui/icons-material/LocalFireDepartment';
import ChatBubbleIcon from '@mui/icons-material/ChatBubble';
import ArticleIcon from '@mui/icons-material/Article';
import { useTrendingTopics, useKeywords, useHotNews } from '../../hooks/useApi.jsx';
import { getTopicColor } from '../../theme/colors.jsx';

// Backend stores naive UTC — append 'Z' so JS parses correctly
function parseUTC(str) {
  if (!str) return null;
  const s = /[Zz+-]\d*$/.test(str.trim()) ? str : str + 'Z';
  const d = new Date(s);
  return isNaN(d.getTime()) ? null : d;
}

function formatAgo(dateStr) {
  const d = parseUTC(dateStr);
  if (!d) return '—';
  const diffMs = Date.now() - d.getTime();
  const diffMins = Math.floor(diffMs / 60000);
  const diffHours = Math.floor(diffMs / 3600000);
  const diffDays = Math.floor(diffMs / 86400000);
  if (diffMins < 1) return 'vừa xong';
  if (diffMins < 60) return `${diffMins} phút trước`;
  if (diffHours < 24) return `${diffHours} giờ trước`;
  if (diffDays < 7) return `${diffDays} ngày trước`;
  return `${d.getDate()}/${d.getMonth() + 1}/${d.getFullYear()}`;
}

// Get first external article link from cluster posts
function getClusterLink(cluster) {
  for (const post of cluster.posts || []) {
    const extLink = (post.links || []).find(
      (l) => /^https?:\/\//.test(l) && !/t\.me/.test(l)
    );
    if (extLink) return extLink;
  }
  return null;
}

// Top 3 rank colours
const RANK_COLORS = ['#f59e0b', '#8b5cf6', '#ec4899'];

export default function TrendingPage() {
  const [timeRange, setTimeRange] = useState('24h');

  // API limits hotnews to 168h max (7 days)
  const hoursMap = { '24h': 24, '7d': 168 };
  const hours = hoursMap[timeRange];
  const days = timeRange === '24h' ? 1 : 7;

  const today = useMemo(() => new Date().toISOString().split('T')[0], []);
  const dateFrom = useMemo(() => {
    const d = new Date();
    d.setDate(d.getDate() - days);
    return d.toISOString().split('T')[0];
  }, [days]);

  const { data: hotNewsData, isLoading: hotLoading } = useHotNews({ hours });
  const { data: trendingTopics, isLoading: topicsLoading } = useTrendingTopics({ days });
  const { data: keywordsData, isLoading: keywordsLoading } = useKeywords({
    limit: 20,
    date_from: dateFrom,
    date_to: today,
  });

  const clusters = hotNewsData?.clusters || [];
  const maxPostCount = useMemo(
    () => Math.max(...clusters.map((c) => c.post_count), 1),
    [clusters]
  );
  const trendingTopicsList = trendingTopics?.data || [];
  const keywords = keywordsData?.keywords || [];

  const handleTimeRangeChange = useCallback((e) => {
    setTimeRange(e.currentTarget.dataset.range);
  }, []);

  return (
    <Box>
      {/* ── Header ── */}
      <Box display="flex" justifyContent="space-between" alignItems="flex-start" mb={3} flexWrap="wrap" gap={2}>
        <Box>
          <Box display="flex" alignItems="center" gap={1} mb={0.5}>
            <LocalFireDepartmentIcon sx={{ fontSize: 36, color: '#f97316' }} />
            <Typography variant="h4" fontWeight="bold">Trending Now</Typography>
          </Box>
          <Typography variant="body1" color="text.secondary">
            Sự kiện được nhắc đến nhiều nhất – phân tích theo tần suất từ khoá
          </Typography>
        </Box>
        <ButtonGroup variant="outlined" size="large">
          {[['24h', '24 giờ'], ['7d', '7 ngày']].map(([range, label]) => (
            <Button
              key={range}
              data-range={range}
              onClick={handleTimeRangeChange}
              variant={timeRange === range ? 'contained' : 'outlined'}
              sx={{ fontWeight: timeRange === range ? 'bold' : 'normal', minWidth: 90 }}
            >
              {label}
            </Button>
          ))}
        </ButtonGroup>
      </Box>

      <Grid container spacing={3}>
        {/* ── Left: Hot News Clusters ── */}
        <Grid size={{ xs: 12, md: 8 }}>
          <Box display="flex" alignItems="center" gap={1.5} mb={2}>
            <WhatshotIcon sx={{ color: '#f97316' }} />
            <Typography variant="h6" fontWeight="bold">
              {hotLoading
                ? 'Đang phân tích bài viết…'
                : `${clusters.length} sự kiện nổi bật`}
            </Typography>
            {hotNewsData?.cached === true && (
              <Chip label="cached" size="small" variant="outlined" sx={{ fontSize: 10, height: 20 }} />
            )}
          </Box>

          {hotLoading ? (
            <Box display="flex" flexDirection="column" alignItems="center" py={8} gap={2}>
              <CircularProgress size={48} />
              <Typography variant="body2" color="text.secondary">
                Đang phân tích từ khoá và nhóm tin tức… (có thể mất ~10 giây)
              </Typography>
            </Box>
          ) : clusters.length === 0 ? (
            <Paper sx={{ p: 4, textAlign: 'center' }}>
              <Typography color="text.secondary">
                Chưa đủ dữ liệu để phân tích trong {hours} giờ qua
              </Typography>
            </Paper>
          ) : (
            <Stack spacing={2}>
              {clusters.map((cluster, index) => {
                const extLink = getClusterLink(cluster);
                const clusterTopics = [
                  ...new Set((cluster.posts || []).flatMap((p) => p.topics || [])),
                ].slice(0, 4);
                const intensity = cluster.post_count / maxPostCount;
                const borderColor = index < 3 ? RANK_COLORS[index] : (cluster.color || '#6b7280');

                return (
                  <Card
                    key={cluster.slug}
                    variant="outlined"
                    sx={{
                      borderLeft: `4px solid ${borderColor}`,
                      transition: 'box-shadow 0.2s',
                      '&:hover': { boxShadow: 3 },
                    }}
                  >
                    <CardContent sx={{ pb: '12px !important' }}>
                      {/* Rank + Name */}
                      <Box display="flex" alignItems="flex-start" justifyContent="space-between" gap={1}>
                        <Box display="flex" alignItems="center" gap={1} flex={1} minWidth={0}>
                          {index < 3 ? (
                            <WhatshotIcon sx={{ color: borderColor, fontSize: 22, flexShrink: 0 }} />
                          ) : (
                            <Typography
                              variant="body2"
                              color="text.disabled"
                              fontWeight="bold"
                              sx={{ minWidth: 26, flexShrink: 0 }}
                            >
                              #{index + 1}
                            </Typography>
                          )}
                          <Typography variant="h6" fontWeight="bold" sx={{ lineHeight: 1.35 }}>
                            {cluster.name}
                          </Typography>
                        </Box>
                        {extLink && (
                          <Tooltip title="Đọc bài gốc">
                            <IconButton
                              size="small"
                              component="a"
                              href={extLink}
                              target="_blank"
                              rel="noopener noreferrer"
                              sx={{ flexShrink: 0 }}
                            >
                              <OpenInNewIcon fontSize="small" />
                            </IconButton>
                          </Tooltip>
                        )}
                      </Box>

                      {/* Headline */}
                      {cluster.headline && (
                        <Typography
                          variant="body2"
                          color="text.secondary"
                          sx={{
                            mt: 0.75, mb: 1.5,
                            display: '-webkit-box',
                            WebkitLineClamp: 2,
                            WebkitBoxOrient: 'vertical',
                            overflow: 'hidden',
                          }}
                        >
                          {cluster.headline}
                        </Typography>
                      )}

                      {/* Stats row */}
                      <Box display="flex" alignItems="center" gap={2.5} mb={1.5} flexWrap="wrap">
                        <Box display="flex" alignItems="center" gap={0.5}>
                          <ArticleIcon sx={{ fontSize: 15, color: 'text.secondary' }} />
                          <Typography variant="caption" fontWeight="600">
                            {cluster.post_count} bài nhắc đến
                          </Typography>
                        </Box>
                        {cluster.posts_with_links > 0 && (
                          <Box display="flex" alignItems="center" gap={0.5}>
                            <OpenInNewIcon sx={{ fontSize: 14, color: 'success.main' }} />
                            <Typography variant="caption" color="success.main" fontWeight="600">
                              {cluster.posts_with_links} có link bài viết
                            </Typography>
                          </Box>
                        )}
                        <Box display="flex" alignItems="center" gap={0.5}>
                          <TelegramIcon sx={{ fontSize: 14, color: '#0088cc' }} />
                          <Typography variant="caption" color="text.disabled">
                            {formatAgo(cluster.latest_at)}
                          </Typography>
                        </Box>
                      </Box>

                      {/* Trending intensity bar */}
                      <LinearProgress
                        variant="determinate"
                        value={Math.round(intensity * 100)}
                        sx={{
                          mb: 1.5, height: 5, borderRadius: 3,
                          bgcolor: 'grey.100',
                          '& .MuiLinearProgress-bar': { bgcolor: borderColor, borderRadius: 3 },
                        }}
                      />

                      {/* Topics */}
                      {clusterTopics.length > 0 && (
                        <Box display="flex" flexWrap="wrap" gap={0.5}>
                          {clusterTopics.map((t) => (
                            <Chip
                              key={t}
                              label={t}
                              size="small"
                              sx={{
                                bgcolor: getTopicColor(t),
                                color: 'white',
                                fontWeight: 600,
                                fontSize: 11,
                              }}
                            />
                          ))}
                        </Box>
                      )}
                    </CardContent>
                  </Card>
                );
              })}
            </Stack>
          )}
        </Grid>

        {/* ── Right Sidebar ── */}
        <Grid size={{ xs: 12, md: 4 }}>
          {/* Trending Topics */}
          <Paper
            sx={{
              p: 3, mb: 3,
              background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
              color: 'white',
            }}
          >
            <Box display="flex" alignItems="center" gap={1} mb={2}>
              <RocketLaunchIcon />
              <Typography variant="h6" fontWeight="bold">Chủ đề hot</Typography>
            </Box>

            {topicsLoading ? (
              <Box display="flex" justifyContent="center" py={2}>
                <CircularProgress size={32} sx={{ color: 'white' }} />
              </Box>
            ) : trendingTopicsList.length > 0 ? (
              <Stack spacing={1.5}>
                {trendingTopicsList.slice(0, 8).map((topic, index) => (
                  <Box
                    key={topic.topic}
                    sx={{
                      p: 1.5,
                      bgcolor: 'rgba(255,255,255,0.12)',
                      borderRadius: 2,
                      border: '1px solid rgba(255,255,255,0.2)',
                      transition: 'all 0.2s',
                      '&:hover': {
                        bgcolor: 'rgba(255,255,255,0.22)',
                        transform: 'translateX(4px)',
                      },
                    }}
                  >
                    <Box display="flex" alignItems="center" justifyContent="space-between">
                      <Box display="flex" alignItems="center" gap={1}>
                        <Typography variant="caption" sx={{ opacity: 0.65, minWidth: 22 }}>
                          #{index + 1}
                        </Typography>
                        <Typography variant="body2" fontWeight="600">
                          {topic.topic}
                        </Typography>
                      </Box>
                      <Chip
                        icon={topic.trend_direction === 'up' ? <TrendingUpIcon /> : <TrendingDownIcon />}
                        label={`${topic.growth_percentage > 0 ? '+' : ''}${(topic.growth_percentage ?? 0).toFixed(0)}%`}
                        size="small"
                        sx={{
                          bgcolor: 'rgba(255,255,255,0.25)',
                          color: 'white',
                          fontWeight: 'bold',
                          '& .MuiChip-icon': { color: 'white' },
                        }}
                      />
                    </Box>
                    <Typography variant="caption" sx={{ opacity: 0.65, mt: 0.25, display: 'block' }}>
                      {topic.current_count} bài trong {days} ngày
                    </Typography>
                  </Box>
                ))}
              </Stack>
            ) : (
              <Typography variant="body2" sx={{ opacity: 0.7, textAlign: 'center', py: 2 }}>
                Không có dữ liệu
              </Typography>
            )}
          </Paper>

          {/* Trending Keywords */}
          <Paper sx={{ p: 3 }}>
            <Box display="flex" alignItems="center" gap={1} mb={2}>
              <ChatBubbleIcon sx={{ color: 'primary.main' }} />
              <Typography variant="h6" fontWeight="bold">Từ khoá nổi bật</Typography>
            </Box>

            {keywordsLoading ? (
              <Box display="flex" justifyContent="center" py={2}>
                <CircularProgress size={28} />
              </Box>
            ) : keywords.length > 0 ? (
              <Box display="flex" flexWrap="wrap" gap={1}>
                {keywords.slice(0, 20).map((kw) => {
                  const maxCount = keywords[0]?.count || 1;
                  const intensity = kw.count / maxCount;
                  return (
                    <Chip
                      key={kw.keyword}
                      label={`${kw.keyword} ${kw.count}`}
                      size="small"
                      sx={{
                        bgcolor: `rgba(102,126,234,${0.15 + intensity * 0.65})`,
                        color: intensity > 0.45 ? 'white' : 'primary.main',
                        fontWeight: 600,
                        fontSize: 11 + intensity * 4,
                        transition: 'transform 0.15s',
                        '&:hover': { transform: 'scale(1.08)' },
                      }}
                    />
                  );
                })}
              </Box>
            ) : (
              <Typography variant="body2" color="text.secondary" textAlign="center">
                Không có dữ liệu
              </Typography>
            )}
          </Paper>
        </Grid>
      </Grid>
    </Box>
  );
}
