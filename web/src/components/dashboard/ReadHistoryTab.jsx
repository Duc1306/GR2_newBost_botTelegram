import React, { useState, useEffect, useCallback } from 'react';
import {
  Box,
  Typography,
  Card,
  CardContent,
  CardActions,
  Chip,
  Button,
  Skeleton,
  IconButton,
  Tooltip,
} from '@mui/material';
import HistoryIcon from '@mui/icons-material/History';
import RefreshIcon from '@mui/icons-material/Refresh';
import OpenInNewIcon from '@mui/icons-material/OpenInNew';
import { fetchReadHistory } from '../../lib/publicApi.js';

export default function ReadHistoryTab() {
  const [posts, setPosts] = useState([]);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    setLoading(true);
    const data = await fetchReadHistory(100);
    setPosts(data);
    setLoading(false);
  }, []);

  useEffect(() => { load(); }, [load]);

  if (loading) {
    return (
      <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1.5, mt: 2 }}>
        {[1, 2, 3].map((i) => (
          <Skeleton key={i} variant="rectangular" height={100} sx={{ borderRadius: 2 }} />
        ))}
      </Box>
    );
  }

  if (posts.length === 0) {
    return (
      <Box textAlign="center" py={8}>
        <HistoryIcon sx={{ fontSize: 48, color: 'text.disabled', mb: 1 }} />
        <Typography color="text.secondary" variant="subtitle2">Chưa có bài nào được đọc.</Typography>
        <Typography variant="caption" color="text.disabled">
          Mở bài viết từ một kênh — hệ thống sẽ tự động lưu lại.
        </Typography>
      </Box>
    );
  }

  return (
    <Box>
      <Box display="flex" alignItems="center" justifyContent="space-between" mb={2}>
        <Typography variant="subtitle2" color="text.secondary">{posts.length} bài đã đọc</Typography>
        <Tooltip title="Làm mới">
          <IconButton size="small" onClick={load}>
            <RefreshIcon fontSize="small" />
          </IconButton>
        </Tooltip>
      </Box>
      {posts.map((post) => {
        const postId = post.id || post._id;
        const summary = post.ai_summary;
        const externalLink = post.links?.find((l) => l && !l.includes('t.me') && l.startsWith('http'));
        const tgLink = post.channel_username && post.id
          ? `https://t.me/${post.channel_username}/${post.id.split('_').at(-1)}`
          : null;
        return (
          <Card
            key={postId}
            elevation={0}
            sx={{
              mb: 2, borderRadius: 2, border: '1px solid #e5e7eb', bgcolor: '#fafafa',
              '&:hover': { boxShadow: '0 4px 14px rgba(0,0,0,0.06)' },
            }}
          >
            <CardContent sx={{ pb: 0, pt: 1.5, px: 2 }}>
              <Box display="flex" alignItems="center" gap={0.75} mb={0.75} flexWrap="wrap">
                <Chip
                  label="Đã đọc"
                  size="small"
                  sx={{ height: 18, fontSize: '0.6rem', fontWeight: 600, bgcolor: '#f3f4f6', color: 'text.disabled' }}
                />
                {post.topics?.[0] && (
                  <Chip
                    label={post.topics[0]}
                    size="small"
                    sx={{ height: 18, fontSize: '0.63rem', fontWeight: 600, bgcolor: '#fef3c7', color: '#92400e' }}
                  />
                )}
                {post.channel_username && (
                  <Chip
                    label={`@${post.channel_username}`}
                    size="small"
                    sx={{ height: 18, fontSize: '0.63rem', bgcolor: '#f3f4f6', color: 'text.secondary' }}
                  />
                )}
              </Box>
              {summary?.lead && (
                <Typography
                  variant="body2"
                  fontWeight={600}
                  color="text.secondary"
                  gutterBottom
                  sx={{ lineHeight: 1.55, fontSize: '0.84rem' }}
                >
                  {summary.lead}
                </Typography>
              )}
              <Typography
                variant="body2"
                color="text.disabled"
                sx={{
                  display: '-webkit-box',
                  WebkitLineClamp: 3,
                  WebkitBoxOrient: 'vertical',
                  overflow: 'hidden',
                  lineHeight: 1.65,
                  fontSize: '0.82rem',
                  whiteSpace: 'pre-line',
                }}
              >
                {post.text}
              </Typography>
            </CardContent>
            <CardActions sx={{ px: 2, pb: 1.25, pt: 0.5, gap: 0.5 }}>
              {externalLink && (
                <Button
                  size="small"
                  variant="outlined"
                  endIcon={<OpenInNewIcon sx={{ fontSize: '13px !important' }} />}
                  href={externalLink}
                  target="_blank"
                  rel="noopener noreferrer"
                  sx={{ textTransform: 'none', fontSize: '0.75rem', borderRadius: 2, px: 1.5, py: 0.3, borderColor: '#e5e7eb', color: 'text.secondary' }}
                >
                  Đọc bài gốc
                </Button>
              )}
              {tgLink && (
                <Button
                  size="small"
                  endIcon={<OpenInNewIcon sx={{ fontSize: '13px !important' }} />}
                  href={tgLink}
                  target="_blank"
                  rel="noopener noreferrer"
                  sx={{ textTransform: 'none', fontSize: '0.75rem', color: '#9ca3af', px: 1, py: 0.25 }}
                >
                  Telegram
                </Button>
              )}
            </CardActions>
          </Card>
        );
      })}
    </Box>
  );
}
