import React, { useState, useEffect } from 'react';
import {
  Card,
  CardContent,
  CardActions,
  Box,
  Typography,
  Chip,
  Button,
  CircularProgress,
  Tooltip,
  IconButton,
} from '@mui/material';
import FiberManualRecordIcon from '@mui/icons-material/FiberManualRecord';
import AutoAwesomeIcon from '@mui/icons-material/AutoAwesome';
import HeadphonesIcon from '@mui/icons-material/Headphones';
import OpenInNewIcon from '@mui/icons-material/OpenInNew';
import BookmarkBorderIcon from '@mui/icons-material/BookmarkBorder';
import BookmarkIcon from '@mui/icons-material/Bookmark';
import { timeAgo } from '../../lib/helpers.jsx';
import { apiPost, authHeaders, API_BASE } from '../../lib/dashApi.js';
import { fetchBookmarkIds, addBookmark, removeBookmark } from '../../lib/publicApi.js';

const PostCard = React.memo(function PostCard({ post: p, channelUsername, onRead, isRead, onPlayAudio }) {
  const [expanded, setExpanded] = useState(false);
  const [aiSummary, setAiSummary] = useState(null);
  const [loadingSummary, setLoadingSummary] = useState(false);
  const [loadingAudio, setLoadingAudio] = useState(false);
  const [bookmarked, setBookmarked] = useState(false);
  const tgLink = p.id ? `https://t.me/${channelUsername}/${p.id.split('_').at(-1)}` : null;
  const externalLink = p.links?.find((l) => l && !l.includes('t.me') && l.startsWith('http'));
  const primaryTopic = p.topics?.[0];
  const postId = p.id;

  useEffect(() => {
    if (!postId) return;
    fetchBookmarkIds().then((ids) => setBookmarked(ids.has(postId)));
  }, [postId]);

  const handleRead = () => {
    if (onRead && p.id) onRead(p.id);
  };

  const handleBookmark = async () => {
    const newState = !bookmarked;
    setBookmarked(newState);
    if (newState) {
      const ok = await addBookmark(postId);
      if (!ok) setBookmarked(false);
    } else {
      const ok = await removeBookmark(postId);
      if (!ok) setBookmarked(true);
    }
  };

  const handleSummarize = async () => {
    if (loadingSummary || !p.id) return;
    setLoadingSummary(true);
    try {
      const result = await apiPost(
        `/user/channels/${encodeURIComponent(channelUsername)}/posts/${encodeURIComponent(p.id)}/summarize`,
        {}
      );
      setAiSummary(result || {});
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
      text = (p.text || '').slice(0, 1500);
    }
    try {
      const res = await fetch(`${API_BASE}/user/channels/tts`, {
        method: 'POST',
        headers: authHeaders(),
        body: JSON.stringify({ text: text.slice(0, 2000) }),
      });
      if (!res.ok) throw new Error('TTS failed');
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      onPlayAudio({ url, title: p.text?.slice(0, 80) || 'Bài viết' });
    } catch (_) {
      /* silent */
    }
    setLoadingAudio(false);
  };

  const hasSummary = aiSummary && (aiSummary.lead || aiSummary.body?.length > 0);

  return (
    <Card
      elevation={0}
      sx={{
        borderRadius: 2,
        border: '1px solid',
        borderColor: isRead ? '#e5e7eb' : p.is_new ? '#bfdbfe' : 'divider',
        bgcolor: isRead ? '#fafafa' : p.is_new ? '#f0f7ff' : 'white',
        opacity: isRead ? 0.72 : 1,
        transition: 'box-shadow 0.18s, opacity 0.3s',
        '&:hover': { boxShadow: '0 4px 14px rgba(0,0,0,0.08)', opacity: 1 },
      }}
    >
      <CardContent sx={{ pb: 0, pt: 1.5, px: 2 }}>
        <Box display="flex" alignItems="center" gap={0.75} mb={0.75} flexWrap="wrap">
          {isRead ? (
            <Chip
              label="Đã đọc"
              size="small"
              sx={{ height: 18, fontSize: '0.6rem', fontWeight: 600, bgcolor: '#f3f4f6', color: 'text.disabled' }}
            />
          ) : p.is_new ? (
            <Chip label="Mới" size="small" color="primary" sx={{ height: 18, fontSize: '0.6rem', fontWeight: 700 }} />
          ) : null}
          {primaryTopic && (
            <Chip
              label={primaryTopic}
              size="small"
              sx={{ height: 18, fontSize: '0.63rem', fontWeight: 600, bgcolor: '#fef3c7', color: '#92400e' }}
            />
          )}
          <Typography
            variant="caption"
            color="text.disabled"
            title={p.created_at ? new Date(p.created_at).toLocaleString('vi-VN') : ''}
          >
            <FiberManualRecordIcon
              sx={{
                fontSize: 7,
                color: isRead ? '#9ca3af' : '#2563eb',
                mr: 0.3,
                verticalAlign: 'middle',
              }}
            />
            {timeAgo(p.created_at)}
          </Typography>
        </Box>

        <Typography
          variant="body2"
          color={isRead ? 'text.disabled' : 'text.secondary'}
          sx={{
            display: '-webkit-box',
            WebkitLineClamp: expanded ? 100 : 5,
            WebkitBoxOrient: 'vertical',
            overflow: 'hidden',
            lineHeight: 1.65,
            fontSize: '0.84rem',
            whiteSpace: 'pre-line',
          }}
        >
          {p.text}
        </Typography>
        {p.text?.length > 300 && (
          <Button
            size="small"
            onClick={() => setExpanded((e) => !e)}
            sx={{ textTransform: 'none', fontSize: '0.72rem', p: 0, mt: 0.5, minWidth: 0, color: '#0369a1' }}
          >
            {expanded ? 'Thu gọn' : 'Xem thêm'}
          </Button>
        )}

        {hasSummary && (
          <Box sx={{ bgcolor: '#f0f9ff', borderRadius: 1.5, p: 1.25, mt: 1 }}>
            {aiSummary.lead && (
              <Typography
                variant="caption"
                color="#0369a1"
                sx={{ display: 'block', fontWeight: 600, mb: 0.5, lineHeight: 1.6 }}
              >
                {aiSummary.lead}
              </Typography>
            )}
            {(aiSummary.body || []).map((b, i) => (
              <Typography
                key={i}
                variant="caption"
                color="text.secondary"
                sx={{ display: 'block', lineHeight: 1.6, mb: 0.25 }}
              >
                {b}
              </Typography>
            ))}
          </Box>
        )}
      </CardContent>

      <CardActions sx={{ px: 2, pb: 1.25, pt: 0.5, gap: 0.5, flexWrap: 'wrap' }}>
        <Tooltip title={bookmarked ? 'Bỏ lưu' : 'Lưu bài'}>
          <IconButton
            size="small"
            onClick={handleBookmark}
            sx={{ color: bookmarked ? '#f59e0b' : 'text.disabled', mr: 0.5 }}
          >
            {bookmarked ? (
              <BookmarkIcon sx={{ fontSize: 18 }} />
            ) : (
              <BookmarkBorderIcon sx={{ fontSize: 18 }} />
            )}
          </IconButton>
        </Tooltip>

        <Button
          size="small"
          startIcon={
            loadingSummary ? (
              <CircularProgress size={11} color="inherit" />
            ) : (
              <AutoAwesomeIcon sx={{ fontSize: '13px !important' }} />
            )
          }
          onClick={handleSummarize}
          disabled={loadingSummary}
          sx={{
            textTransform: 'none',
            fontSize: '0.72rem',
            borderRadius: 2,
            px: 1,
            py: 0.25,
            border: '1px solid',
            borderColor: hasSummary ? '#bfdbfe' : '#e5e7eb',
            color: hasSummary ? '#0369a1' : 'text.secondary',
          }}
        >
          {loadingSummary ? 'Đang tóm…' : hasSummary ? 'Tóm tắt ✓' : 'Tóm tắt AI'}
        </Button>

        {onPlayAudio && (
          <Button
            size="small"
            startIcon={
              loadingAudio ? (
                <CircularProgress size={11} color="inherit" />
              ) : (
                <HeadphonesIcon sx={{ fontSize: '13px !important' }} />
              )
            }
            onClick={handleAudio}
            disabled={loadingAudio}
            sx={{
              textTransform: 'none',
              fontSize: '0.72rem',
              borderRadius: 2,
              px: 1,
              py: 0.25,
              border: '1px solid',
              borderColor: hasSummary ? '#bfdbfe' : '#e5e7eb',
              color: hasSummary ? '#0369a1' : 'text.secondary',
            }}
          >
            {loadingAudio ? 'Đang tạo…' : hasSummary ? 'Nghe tóm tắt' : 'Nghe'}
          </Button>
        )}

        {externalLink && (
          <Button
            size="small"
            variant="contained"
            endIcon={<OpenInNewIcon sx={{ fontSize: '13px !important' }} />}
            href={externalLink}
            target="_blank"
            rel="noopener noreferrer"
            onClick={handleRead}
            sx={{
              textTransform: 'none',
              fontSize: '0.75rem',
              borderRadius: 2,
              px: 1.5,
              py: 0.35,
              boxShadow: 'none',
            }}
          >
            Đọc bài gốc
          </Button>
        )}
        {tgLink && (
          <Button
            size="small"
            startIcon={<OpenInNewIcon sx={{ fontSize: '13px !important' }} />}
            href={tgLink}
            target="_blank"
            rel="noopener noreferrer"
            onClick={handleRead}
            sx={{ textTransform: 'none', fontSize: '0.75rem', color: '#6b7280', px: 1, py: 0.25 }}
          >
            Telegram
          </Button>
        )}
      </CardActions>
    </Card>
  );
});

export default PostCard;
