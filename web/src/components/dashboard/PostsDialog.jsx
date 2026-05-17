import React, { useState, useEffect, useCallback, useMemo } from 'react';
import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Box,
  Typography,
  Button,
  Skeleton,
  Stack,
  IconButton,
  useTheme,
  useMediaQuery,
} from '@mui/material';
import CheckIcon from '@mui/icons-material/Check';
import { apiGet, apiPost } from '../../lib/dashApi.js';
import PostCard from './PostCard.jsx';

const HOURS_OPTIONS = [
  { label: '24 giờ', value: 24 },
  { label: '3 ngày', value: 72 },
  { label: '7 ngày', value: 168 },
];

const PostsDialog = React.memo(function PostsDialog({ open, onClose, channelUsername, channelName, initialUnread, onPlayAudio }) {
  const theme = useTheme();
  const isMobile = useMediaQuery(theme.breakpoints.down('sm'));
  const [hours, setHours] = useState(24);
  const [posts, setPosts] = useState([]);
  const [loading, setLoading] = useState(false);
  const [loaded, setLoaded] = useState(false);
  const [readIds, setReadIds] = useState(() => new Set());

  useEffect(() => {
    if (!open) return;
    setLoaded(false);
    setLoading(true);
    apiGet(`/user/channels/${channelUsername}/posts?hours=${hours}&limit=100`)
      .then((data) => {
        setPosts(data);
        setReadIds(new Set(data.filter((p) => p.is_read).map((p) => p.id)));
        setLoaded(true);
      })
      .catch(() => { setPosts([]); setLoaded(true); })
      .finally(() => setLoading(false));
  }, [open, channelUsername, hours]);

  const handleRead = useCallback((postId) => {
    if (!postId) return;
    setReadIds((prev) => {
      if (prev.has(postId)) return prev;
      const next = new Set(prev);
      next.add(postId);
      return next;
    });
    apiPost(`/user/channels/${channelUsername}/posts/${postId}/read`, {}).catch(() => {});
  }, [channelUsername]);

  const sortedPosts = useMemo(() => {
    return [...posts].sort((a, b) => {
      const aRead = readIds.has(a.id);
      const bRead = readIds.has(b.id);
      if (aRead !== bRead) return aRead ? 1 : -1;
      if (a.is_new !== b.is_new) return a.is_new ? -1 : 1;
      return new Date(b.created_at) - new Date(a.created_at);
    });
  }, [posts, readIds]);

  const unreadCount = sortedPosts.filter((p) => !readIds.has(p.id)).length;

  return (
    <Dialog
      open={open}
      onClose={onClose}
      maxWidth="md"
      fullWidth
      fullScreen={isMobile}
      PaperProps={{ sx: { borderRadius: isMobile ? 0 : 3, maxHeight: '92vh' } }}
    >
      <DialogTitle sx={{ pb: 1, borderBottom: '1px solid', borderColor: 'divider' }}>
        <Box display="flex" alignItems="center" gap={1}>
          <Box flex={1}>
            <Typography variant="subtitle1" fontWeight={700}>
              Tin tức — {channelName}
            </Typography>
            <Typography variant="caption" color="text.secondary">
              {loaded
                ? `${sortedPosts.length} bài${unreadCount > 0 ? `, ${unreadCount} chưa đọc` : ' — đã đọc hết'}`
                : 'Đang tải…'}
            </Typography>
          </Box>
          <Stack direction="row" spacing={0.5}>
            {HOURS_OPTIONS.map((opt) => (
              <Button
                key={opt.value}
                size="small"
                variant={hours === opt.value ? 'contained' : 'outlined'}
                onClick={() => setHours(opt.value)}
                sx={{ textTransform: 'none', fontSize: '0.72rem', minWidth: 0, px: 1, py: 0.25, borderRadius: 2 }}
              >
                {opt.label}
              </Button>
            ))}
          </Stack>
          <IconButton size="small" onClick={onClose} sx={{ ml: 0.5 }}>
            <CheckIcon fontSize="small" />
          </IconButton>
        </Box>
      </DialogTitle>

      <DialogContent sx={{ px: { xs: 1.5, sm: 2.5 }, py: 2 }}>
        {loading ? (
          <Stack spacing={1.5}>
            {[1, 2, 3, 4].map((i) => (
              <Skeleton key={i} variant="rectangular" height={110} sx={{ borderRadius: 2 }} />
            ))}
          </Stack>
        ) : !loaded || sortedPosts.length === 0 ? (
          <Typography variant="body2" color="text.secondary" textAlign="center" py={4}>
            Không có bài viết nào trong {HOURS_OPTIONS.find((o) => o.value === hours)?.label} qua.
          </Typography>
        ) : (
          <Stack spacing={1.5}>
            {sortedPosts.map((p, i) => (
              <PostCard
                key={p.id || i}
                post={p}
                channelUsername={channelUsername}
                isRead={readIds.has(p.id)}
                onRead={handleRead}
                onPlayAudio={onPlayAudio}
              />
            ))}
          </Stack>
        )}
      </DialogContent>

      <DialogActions sx={{ px: 3, pb: 2, borderTop: '1px solid', borderColor: 'divider' }}>
        <Button onClick={onClose} variant="outlined" size="small" sx={{ textTransform: 'none', borderRadius: 2 }}>
          Đóng
        </Button>
      </DialogActions>
    </Dialog>
  );
});

export default PostsDialog;
