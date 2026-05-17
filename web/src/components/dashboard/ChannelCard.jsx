import React, { useState, memo } from 'react';
import {
  Card,
  CardContent,
  CardActions,
  Box,
  Typography,
  Chip,
  Button,
  Alert,
  Avatar,
  IconButton,
  Tooltip,
  Stack,
} from '@mui/material';
import TelegramIcon from '@mui/icons-material/Telegram';
import HourglassTopIcon from '@mui/icons-material/HourglassTop';
import AutoAwesomeIcon from '@mui/icons-material/AutoAwesome';
import OpenInNewIcon from '@mui/icons-material/OpenInNew';
import DeleteOutlineIcon from '@mui/icons-material/DeleteOutline';
import StatusBadge from './StatusBadge.jsx';
import PostsDialog from './PostsDialog.jsx';
import { apiPost } from '../../lib/dashApi.js';

const ChannelCard = memo(function ChannelCard({ ch, onUnsubscribe, onSummarized, onPlayAudio }) {
  const [postsDialogOpen, setPostsDialogOpen] = useState(false);

  const handleOpenPosts = async () => {
    setPostsDialogOpen(true);
    try {
      await apiPost(`/user/channels/${ch.username}/seen`, {});
      if (onSummarized) onSummarized();
    } catch (_) { /* ignore */ }
  };

  const unread = ch.unread_count || 0;
  const isX = ch.username.startsWith('x:') || ch.username.startsWith('xkw:');

  return (
    <Card
      elevation={0}
      sx={{
        borderRadius: 2.5,
        border: '1px solid',
        borderColor: unread > 0 ? 'primary.light' : 'divider',
        transition: 'box-shadow 0.18s',
        '&:hover': { boxShadow: '0 4px 16px rgba(0,0,0,0.08)' },
      }}
    >
      <CardContent sx={{ pb: 0 }}>
        {/* Header row */}
        <Box display="flex" alignItems="center" gap={1.5} mb={1}>
          <Box position="relative" flexShrink={0}>
            <Avatar sx={{ bgcolor: isX ? '#000' : '#e0f2fe', color: isX ? '#fff' : '#0369a1', width: 40, height: 40 }}>
              {isX
                ? <Typography variant="caption" fontWeight={900} sx={{ fontSize: '1.1rem' }}>𝕏</Typography>
                : <TelegramIcon fontSize="small" />}
            </Avatar>
            {unread > 0 && (
              <Box
                sx={{
                  position: 'absolute', top: -4, right: -4,
                  bgcolor: 'error.main', color: 'white',
                  borderRadius: '50%', width: 18, height: 18,
                  fontSize: '0.6rem', fontWeight: 800,
                  display: 'flex', alignItems: 'center', justifyContent: 'center',
                  border: '2px solid white',
                }}
              >
                {unread > 99 ? '99+' : unread}
              </Box>
            )}
          </Box>
          <Box flex={1} minWidth={0}>
            <Typography variant="subtitle2" fontWeight={700} noWrap>
              {ch.display_name || `@${ch.username}`}
            </Typography>
            <Typography variant="caption" color="text.secondary" noWrap>
              {ch.channel_link}
            </Typography>
          </Box>
          <StatusBadge status={ch.status} />
        </Box>

        {ch.status === 'pending' && (
          <Alert
            severity="info"
            icon={<HourglassTopIcon fontSize="inherit" />}
            sx={{ py: 0.5, px: 1.5, borderRadius: 1.5, mb: 1, fontSize: '0.8rem' }}
          >
            Hệ thống đang thu thập dữ liệu, tự động cập nhật sau ít phút.
          </Alert>
        )}
        {ch.status === 'error' && (
          <Alert severity="error" sx={{ py: 0.5, px: 1.5, borderRadius: 1.5, mb: 1, fontSize: '0.8rem' }}>
            {ch.error_message
              ? ch.error_message.replace('Không thể truy cập kênh', 'Không thể kết nối').replace(/^.*?: /, 'Lỗi: ')
              : 'Không thể kết nối kênh. Vui lòng kiểm tra link.'}
            <Typography variant="caption" display="block" color="error.dark" mt={0.5}>
              Hãy hủy đăng ký và thêm lại với link đúng.
            </Typography>
          </Alert>
        )}

        {/* Stats row */}
        <Box display="flex" alignItems="center" gap={1} flexWrap="wrap">
          {ch.post_count > 0 && (
            <Chip
              label={`${ch.post_count} bài`}
              size="small"
              sx={{ height: 19, fontSize: '0.67rem', bgcolor: '#f3f4f6', color: 'text.secondary' }}
            />
          )}
          {unread > 0 && (
            <Chip
              label={`${unread} tin mới`}
              size="small"
              color="primary"
              variant="outlined"
              sx={{ height: 19, fontSize: '0.67rem' }}
            />
          )}
          <Typography variant="caption" color="text.disabled">
            Đăng ký {new Date(ch.subscribed_at).toLocaleDateString('vi-VN')}
          </Typography>
        </Box>
      </CardContent>

      <CardActions sx={{ px: 2, py: 1, justifyContent: 'space-between', flexWrap: 'wrap', gap: 0.5 }}>
        <Stack direction="row" spacing={0.5}>
          <Button
            size="small"
            startIcon={<OpenInNewIcon sx={{ fontSize: '14px !important' }} />}
            href={`https://${ch.channel_link}`}
            target="_blank"
            rel="noopener noreferrer"
            sx={{ textTransform: 'none', fontSize: '0.78rem', color: 'text.secondary' }}
          >
            {isX ? 'Xem trên X' : 'Telegram'}
          </Button>

          {ch.status === 'active' && (
            <Button
              size="small"
              startIcon={<AutoAwesomeIcon sx={{ fontSize: '14px !important' }} />}
              onClick={handleOpenPosts}
              sx={{ textTransform: 'none', fontSize: '0.78rem', color: '#0369a1' }}
            >
              {unread > 0 ? `Xem tin (${unread} mới)` : 'Xem tin & Tóm tắt AI'}
            </Button>
          )}
        </Stack>

        <Tooltip title="Hủy đăng ký">
          <IconButton size="small" color="error" onClick={() => onUnsubscribe(ch)}>
            <DeleteOutlineIcon fontSize="small" />
          </IconButton>
        </Tooltip>
      </CardActions>

      <PostsDialog
        open={postsDialogOpen}
        onClose={() => setPostsDialogOpen(false)}
        channelUsername={ch.username}
        channelName={ch.display_name || `@${ch.username}`}
        initialUnread={unread}
        onPlayAudio={onPlayAudio}
      />
    </Card>
  );
});

export default ChannelCard;
