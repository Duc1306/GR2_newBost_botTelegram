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
import BookmarkBorderIcon from '@mui/icons-material/BookmarkBorder';
import BookmarkIcon from '@mui/icons-material/Bookmark';
import HistoryIcon from '@mui/icons-material/History';
import OpenInNewIcon from '@mui/icons-material/OpenInNew';
import { fetchBookmarks, removeBookmark, invalidateBookmarkCache } from '../../lib/publicApi.js';

export default function BookmarksDashTab() {
  const [posts, setPosts] = useState([]);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    setLoading(true);
    const data = await fetchBookmarks();
    setPosts(data);
    setLoading(false);
  }, []);

  useEffect(() => { load(); }, [load]);

  const handleRemove = useCallback(async (postId) => {
    setPosts((prev) => prev.filter((p) => (p.id || p._id) !== postId));
    await removeBookmark(postId);
    invalidateBookmarkCache();
  }, []);

  if (loading) {
    return (
      <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1.5, mt: 2 }}>
        {[1, 2, 3].map((i) => (
          <Skeleton key={i} variant="rectangular" height={110} sx={{ borderRadius: 2 }} />
        ))}
      </Box>
    );
  }

  if (posts.length === 0) {
    return (
      <Box textAlign="center" py={8}>
        <BookmarkBorderIcon sx={{ fontSize: 48, color: 'text.disabled', mb: 1 }} />
        <Typography color="text.secondary" variant="subtitle2">Chưa có bài nào được lưu.</Typography>
        <Typography variant="caption" color="text.disabled">
          Nhấn biểu tượng <BookmarkBorderIcon sx={{ fontSize: 12, verticalAlign: 'middle' }} /> trên bất kỳ bài viết nào để lưu.
        </Typography>
      </Box>
    );
  }

  return (
    <Box>
      <Box display="flex" alignItems="center" justifyContent="space-between" mb={2}>
        <Typography variant="subtitle2" color="text.secondary">{posts.length} bài đã lưu</Typography>
        <Tooltip title="Làm mới">
          <IconButton size="small" onClick={load}>
            <HistoryIcon fontSize="small" />
          </IconButton>
        </Tooltip>
      </Box>
      {posts.map((post) => {
        const postId = post.id || post._id;
        const summary = post.ai_summary;
        const externalLink = post.links?.find((l) => l && !l.includes('t.me') && l.startsWith('http'));
        return (
          <Card
            key={postId}
            elevation={0}
            sx={{
              mb: 2, borderRadius: 2, border: '1px solid #e5e7eb', bgcolor: 'white',
              '&:hover': { boxShadow: '0 4px 14px rgba(0,0,0,0.08)' },
            }}
          >
            <CardContent sx={{ pb: 0, pt: 1.5, px: 2 }}>
              <Box display="flex" alignItems="center" gap={0.75} mb={0.75} flexWrap="wrap">
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
                  color="text.primary"
                  gutterBottom
                  sx={{ lineHeight: 1.55, fontSize: '0.84rem' }}
                >
                  {summary.lead}
                </Typography>
              )}
              <Typography
                variant="body2"
                color="text.secondary"
                sx={{
                  display: '-webkit-box',
                  WebkitLineClamp: 4,
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
              <Tooltip title="Bỏ lưu">
                <IconButton size="small" onClick={() => handleRemove(postId)} sx={{ color: '#f59e0b', mr: 0.5 }}>
                  <BookmarkIcon sx={{ fontSize: 18 }} />
                </IconButton>
              </Tooltip>
              {externalLink && (
                <Button
                  size="small"
                  variant="contained"
                  endIcon={<OpenInNewIcon sx={{ fontSize: '13px !important' }} />}
                  href={externalLink}
                  target="_blank"
                  rel="noopener noreferrer"
                  sx={{ textTransform: 'none', fontSize: '0.75rem', borderRadius: 2, px: 1.5, py: 0.35, boxShadow: 'none' }}
                >
                  Đọc bài gốc
                </Button>
              )}
            </CardActions>
          </Card>
        );
      })}
    </Box>
  );
}
