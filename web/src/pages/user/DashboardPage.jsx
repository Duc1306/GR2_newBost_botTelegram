/**
 * DashboardPage – bảng điều khiển cá nhân dành cho user đã đăng nhập.
 *
 * Tính năng:
 *   • Hiển thị kênh Telegram đã đăng ký + tóm tắt AI mới nhất
 *   • Ô nhập link kênh mới → gọi POST /user/channels
 *   • Hủy đăng ký kênh
 *   • Nút xem trang tin công khai
 */
import React, { useState, useEffect, useCallback, useMemo, useRef } from 'react';
import { Link as RouterLink, useNavigate } from 'react-router-dom';
import { formatDistanceToNow } from 'date-fns';
import { vi } from 'date-fns/locale';
import { useAuth } from '../../context/AuthContext.jsx';
import {
  Box,
  Container,
  Typography,
  TextField,
  Button,
  Card,
  CardContent,
  CardActions,
  Chip,
  CircularProgress,
  Alert,
  Snackbar,
  IconButton,
  Tooltip,
  AppBar,
  Toolbar,
  Stack,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogContentText,
  DialogActions,
  Skeleton,
  Avatar,
  InputAdornment,
  Paper,
  Grid,
  Collapse,
} from '@mui/material';
import AddIcon from '@mui/icons-material/Add';
import DeleteOutlineIcon from '@mui/icons-material/DeleteOutline';
import RefreshIcon from '@mui/icons-material/Refresh';
import TelegramIcon from '@mui/icons-material/Telegram';
import AutoAwesomeIcon from '@mui/icons-material/AutoAwesome';
import NewspaperIcon from '@mui/icons-material/Newspaper';
import LogoutIcon from '@mui/icons-material/Logout';
import LinkIcon from '@mui/icons-material/Link';
import HourglassTopIcon from '@mui/icons-material/HourglassTop';
import CheckCircleOutlineIcon from '@mui/icons-material/CheckCircleOutline';
import ErrorOutlineIcon from '@mui/icons-material/ErrorOutline';
import OpenInNewIcon from '@mui/icons-material/OpenInNew';
import ContentPasteIcon from '@mui/icons-material/ContentPaste';
import CheckIcon from '@mui/icons-material/Check';
import FiberManualRecordIcon from '@mui/icons-material/FiberManualRecord';
import OpenWithIcon from '@mui/icons-material/OpenWith';
import ExpandLessIcon from '@mui/icons-material/ExpandLess';
import ExpandMoreIcon from '@mui/icons-material/ExpandMore';
import PublicIcon from '@mui/icons-material/Public';
import GroupsIcon from '@mui/icons-material/Groups';
import useMediaQuery from '@mui/material/useMediaQuery';
import { useTheme } from '@mui/material/styles';


const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000';

// ---------------------------------------------------------------------------
// API helpers
// ---------------------------------------------------------------------------

function authHeaders() {
  const token = localStorage.getItem('auth_token');
  return { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' };
}

async function apiGet(path, signal) {
  const res = await fetch(`${API_BASE}${path}`, { headers: authHeaders(), signal });
  if (!res.ok) { const e = await res.json().catch(() => ({})); throw new Error(e.detail || res.status); }
  return res.json();
}

async function apiPost(path, body) {
  const res = await fetch(`${API_BASE}${path}`, { method: 'POST', headers: authHeaders(), body: JSON.stringify(body) });
  if (!res.ok) { const e = await res.json().catch(() => ({})); throw new Error(e.detail || res.status); }
  return res.json();
}

async function apiDelete(path) {
  const res = await fetch(`${API_BASE}${path}`, { method: 'DELETE', headers: authHeaders() });
  if (!res.ok) { const e = await res.json().catch(() => ({})); throw new Error(e.detail || res.status); }
  return res.json();
}

// ---------------------------------------------------------------------------
// Time helper
// ---------------------------------------------------------------------------

function timeAgo(dateStr) {
  if (!dateStr) return '';
  try {
    return formatDistanceToNow(new Date(dateStr), { addSuffix: true, locale: vi });
  } catch {
    return '';
  }
}

// ---------------------------------------------------------------------------
// Status badge
// ---------------------------------------------------------------------------

const STATUS_META = {
  pending: { label: 'Đang xử lý', color: 'warning', icon: <HourglassTopIcon sx={{ fontSize: 14 }} /> },
  active:  { label: 'Đang hoạt động', color: 'success', icon: <CheckCircleOutlineIcon sx={{ fontSize: 14 }} /> },
  error:   { label: 'Lỗi', color: 'error', icon: <ErrorOutlineIcon sx={{ fontSize: 14 }} /> },
};

function StatusBadgeInner({ status }) {
  const m = STATUS_META[status] || STATUS_META.pending;
  return (
    <Chip
      icon={m.icon}
      label={m.label}
      color={m.color}
      size="small"
      sx={{ height: 22, fontSize: '0.68rem', fontWeight: 600 }}
    />
  );
}
const StatusBadge = React.memo(StatusBadgeInner);

// ---------------------------------------------------------------------------
// Post card (used inside ChannelCard posts panel)
// ---------------------------------------------------------------------------

const PostCard = React.memo(function PostCard({ post: p, channelUsername, onRead, isRead }) {
  const [expanded, setExpanded] = useState(false);
  const tgLink = p.id ? `https://t.me/${channelUsername}/${p.id.split('_').at(-1)}` : null;
  const externalLink = p.links?.find((l) => l && !l.includes('t.me') && l.startsWith('http'));
  const primaryTopic = p.topics?.[0];

  const handleRead = () => { if (onRead && p.id) onRead(p.id); };

  return (
    <Card elevation={0} sx={{
      borderRadius: 2,
      border: '1px solid',
      borderColor: isRead ? '#e5e7eb' : p.is_new ? '#bfdbfe' : 'divider',
      bgcolor: isRead ? '#fafafa' : p.is_new ? '#f0f7ff' : 'white',
      opacity: isRead ? 0.72 : 1,
      transition: 'box-shadow 0.18s, opacity 0.3s',
      '&:hover': { boxShadow: '0 4px 14px rgba(0,0,0,0.08)', opacity: 1 },
    }}>
      <CardContent sx={{ pb: 0, pt: 1.5, px: 2 }}>
        {/* Meta row */}
        <Box display="flex" alignItems="center" gap={0.75} mb={0.75} flexWrap="wrap">
          {isRead ? (
            <Chip label="Đã đọc" size="small"
              sx={{ height: 18, fontSize: '0.6rem', fontWeight: 600, bgcolor: '#f3f4f6', color: 'text.disabled' }} />
          ) : p.is_new ? (
            <Chip label="Mới" size="small" color="primary"
              sx={{ height: 18, fontSize: '0.6rem', fontWeight: 700 }} />
          ) : null}
          {primaryTopic && (
            <Chip label={primaryTopic} size="small"
              sx={{ height: 18, fontSize: '0.63rem', fontWeight: 600, bgcolor: '#fef3c7', color: '#92400e' }} />
          )}
          <Typography variant="caption" color="text.disabled"
            title={p.created_at ? new Date(p.created_at).toLocaleString('vi-VN') : ''}>
            <FiberManualRecordIcon sx={{ fontSize: 7, color: isRead ? '#9ca3af' : '#2563eb', mr: 0.3, verticalAlign: 'middle' }} />
            {timeAgo(p.created_at)}
          </Typography>
        </Box>

        {/* Text */}
        <Typography variant="body2" color={isRead ? 'text.disabled' : 'text.secondary'} sx={{
          display: '-webkit-box',
          WebkitLineClamp: expanded ? 100 : 5,
          WebkitBoxOrient: 'vertical',
          overflow: 'hidden',
          lineHeight: 1.65,
          fontSize: '0.84rem',
          whiteSpace: 'pre-line',
        }}>
          {p.text}
        </Typography>
        {p.text?.length > 300 && (
          <Button size="small" onClick={() => setExpanded(e => !e)}
            sx={{ textTransform: 'none', fontSize: '0.72rem', p: 0, mt: 0.5, minWidth: 0, color: '#0369a1' }}>
            {expanded ? 'Thu gọn' : 'Xem thêm'}
          </Button>
        )}
      </CardContent>

      <CardActions sx={{ px: 2, pb: 1.25, pt: 0.5, gap: 0.5 }}>
        {tgLink && (
          <Button size="small" startIcon={<OpenInNewIcon sx={{ fontSize: '13px !important' }} />}
            href={tgLink} target="_blank" rel="noopener noreferrer"
            onClick={handleRead}
            sx={{ textTransform: 'none', fontSize: '0.75rem', color: '#0369a1', px: 1, py: 0.25 }}>
            Telegram
          </Button>
        )}
        {externalLink && (
          <Button size="small" variant="contained"
            endIcon={<OpenInNewIcon sx={{ fontSize: '13px !important' }} />}
            href={externalLink} target="_blank" rel="noopener noreferrer"
            onClick={handleRead}
            sx={{ textTransform: 'none', fontSize: '0.75rem', borderRadius: 2, px: 1.5, py: 0.35, boxShadow: 'none' }}>
            Đọc bài gốc
          </Button>
        )}
      </CardActions>
    </Card>
  );
});

// ---------------------------------------------------------------------------
// Full-summary popup dialog
// ---------------------------------------------------------------------------

const SummaryDialog = React.memo(function SummaryDialog({ open, onClose, channelName, summaryDate, summary }) {
  const theme = useTheme();
  const isMobile = useMediaQuery(theme.breakpoints.down('sm'));

  // Parse bullet points (• or -) into array for nicer rendering
  const lines = summary
    ? summary.split('\n').map((l) => l.trim()).filter(Boolean)
    : [];

  return (
    <Dialog
      open={open}
      onClose={onClose}
      maxWidth="md"
      fullWidth
      fullScreen={isMobile}
      PaperProps={{ sx: { borderRadius: isMobile ? 0 : 3, maxHeight: '90vh' } }}
    >
      <DialogTitle sx={{ pb: 1, borderBottom: '1px solid', borderColor: 'divider', bgcolor: '#f0f9ff' }}>
        <Box display="flex" alignItems="center" gap={1}>
          <AutoAwesomeIcon sx={{ color: '#0369a1', fontSize: 20 }} />
          <Box flex={1}>
            <Typography variant="subtitle1" fontWeight={700} color="#0369a1">
              Tóm tắt AI — {channelName}
            </Typography>
            {summaryDate && (
              <Typography variant="caption" color="text.secondary">
                {summaryDate}
              </Typography>
            )}
          </Box>
          <IconButton size="small" onClick={onClose}>
            <CheckIcon fontSize="small" />
          </IconButton>
        </Box>
      </DialogTitle>

      <DialogContent sx={{ px: { xs: 2.5, sm: 4 }, py: 2.5 }}>
        {lines.length === 0 ? (
          <Typography variant="body2" color="text.secondary">Không có tóm tắt.</Typography>
        ) : (
          <Box sx={{ display: 'flex', flexDirection: 'column', gap: 0.75 }}>
            {lines.map((line, i) => {
              const isBullet = line.startsWith('•') || line.startsWith('-');
              const text = isBullet ? line.replace(/^[•-]\s*/, '') : line;
              return (
                <Box key={i} display="flex" alignItems="flex-start" gap={1.25}>
                  <Box sx={{
                    width: 6, height: 6, borderRadius: '50%',
                    bgcolor: '#0369a1', mt: '8px', flexShrink: 0,
                  }} />
                  <Typography variant="body2" sx={{ lineHeight: 1.75, color: 'text.primary', fontSize: '0.9rem' }}>
                    {text}
                  </Typography>
                </Box>
              );
            })}
          </Box>
        )}
      </DialogContent>

      <DialogActions sx={{ px: 3, pb: 2, borderTop: '1px solid', borderColor: 'divider' }}>
        <Typography variant="caption" color="text.disabled" sx={{ flex: 1 }}>
          {lines.length} điểm tóm tắt
        </Typography>
        <Button onClick={onClose} variant="outlined" size="small" sx={{ textTransform: 'none', borderRadius: 2 }}>
          Đóng
        </Button>
      </DialogActions>
    </Dialog>
  );
});

// ---------------------------------------------------------------------------
// Posts popup dialog
// ---------------------------------------------------------------------------

const HOURS_OPTIONS = [
  { label: '24 giờ', value: 24 },
  { label: '3 ngày', value: 72 },
  { label: '7 ngày', value: 168 },
];

const PostsDialog = React.memo(function PostsDialog({ open, onClose, channelUsername, channelName, initialUnread }) {
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
        // Seed readIds from server-side is_read on initial load
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
    // Persist to backend (fire-and-forget)
    apiPost(`/user/channels/${channelUsername}/posts/${postId}/read`, {}).catch(() => {});
  }, [channelUsername]);

  // Re-sort whenever posts or readIds change:
  // unread+new → unread+old → read (sinks to bottom), then by date desc within each group
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
          {/* Time-range toggle */}
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
            Không có bài viết nào trong {HOURS_OPTIONS.find(o => o.value === hours)?.label} qua.
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

// ---------------------------------------------------------------------------
// Channel card
// ---------------------------------------------------------------------------

const ChannelCard = React.memo(function ChannelCard({ ch, onUnsubscribe, onSummarized }) {
  const [expanded, setExpanded] = useState(false);
  const [summarizing, setSummarizing] = useState(false);
  const [summaryDone, setSummaryDone] = useState(false);
  const [localSummary, setLocalSummary] = useState(null);
  const [localSummaryDate, setLocalSummaryDate] = useState(null);
  const [summaryDialogOpen, setSummaryDialogOpen] = useState(false);
  const [postsDialogOpen, setPostsDialogOpen] = useState(false);
  const mountedRef = useRef(true);

  useEffect(() => { return () => { mountedRef.current = false; }; }, []);

  const displaySummary = localSummary || ch.latest_summary;
  const displaySummaryDate = localSummaryDate || ch.summary_date;

  const handleSummarize = async () => {
    setSummarizing(true);
    setSummaryDone(false);
    // Clear local summary so card shows "Đang tải…" rather than stale content
    setLocalSummary(null);
    setLocalSummaryDate(null);
    try {
      await apiPost(`/user/channels/${ch.username}/summarize`, {});
      // Poll until worker finishes re-fetching and generates a NEW summary.
      // Server deletes old summaries before re-queuing, so any result = fresh.
      for (let i = 0; i < 15; i++) {          // up to 45 s (exponential backoff)
        const delay = i < 5 ? 2000 : i < 10 ? 3000 : 4000;
        await new Promise((r) => setTimeout(r, delay));
        if (!mountedRef.current) break;
        try {
          const res = await apiGet(`/user/channels/${ch.username}/summary`);
          if (res.summaries?.length > 0) {
            setLocalSummary(res.summaries[0].summary_text);
            setLocalSummaryDate(res.summaries[0].date);
            break;
          }
        } catch (_) { /* ignore poll errors */ }
      }
      setSummaryDone(true);
      if (onSummarized) onSummarized(); // silent refresh to sync post_count / status
    } catch (err) {
      alert(err.message);
    } finally {
      setSummarizing(false);
    }
  };

  const handleOpenPosts = async () => {
    setPostsDialogOpen(true);
    // Mark as seen so unread badge resets
    try {
      await apiPost(`/user/channels/${ch.username}/seen`, {});
      if (onSummarized) onSummarized();
    } catch (_) { /* ignore */ }
  };

  const unread = ch.unread_count || 0;

  return (
    <Card elevation={0} sx={{
      borderRadius: 2.5,
      border: '1px solid',
      borderColor: unread > 0 ? 'primary.light' : 'divider',
      transition: 'box-shadow 0.18s',
      '&:hover': { boxShadow: '0 4px 16px rgba(0,0,0,0.08)' },
    }}>
      <CardContent sx={{ pb: 0 }}>
        {/* Header row */}
        <Box display="flex" alignItems="center" gap={1.5} mb={1}>
          <Box position="relative" flexShrink={0}>
            {/* Avatar: X (𝕏) for Twitter channels, Telegram bird for others */}
            {(() => { const isX = ch.username.startsWith('x:') || ch.username.startsWith('xkw:'); return (
            <Avatar sx={{ bgcolor: isX ? '#000' : '#e0f2fe', color: isX ? '#fff' : '#0369a1', width: 40, height: 40 }}>
              {isX
                ? <Typography variant="caption" fontWeight={900} sx={{ fontSize: '1.1rem' }}>𝕏</Typography>
                : <TelegramIcon fontSize="small" />}
            </Avatar>); })()}
            {unread > 0 && (
              <Box sx={{
                position: 'absolute', top: -4, right: -4,
                bgcolor: 'error.main', color: 'white',
                borderRadius: '50%', width: 18, height: 18,
                fontSize: '0.6rem', fontWeight: 800,
                display: 'flex', alignItems: 'center', justifyContent: 'center',
                border: '2px solid white',
              }}>
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

        {/* Pending / error banners */}
        {ch.status === 'pending' && (
          <Alert severity="info" icon={<HourglassTopIcon fontSize="inherit" />}
            sx={{ py: 0.5, px: 1.5, borderRadius: 1.5, mb: 1, fontSize: '0.8rem' }}>
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

        {/* AI Summary block */}
        {summarizing && !displaySummary ? (
          <Box sx={{ bgcolor: '#f0f9ff', borderRadius: 1.5, p: 1.5, mb: 1, textAlign: 'center' }}>
            <Typography variant="caption" color="#0369a1">
              ⏳ Đang tải tin mới &amp; tạo tóm tắt AI…
            </Typography>
          </Box>
        ) : displaySummary ? (
          <>
            <Box sx={{ bgcolor: '#f0f9ff', borderRadius: 1.5, p: 1.5, mb: 1 }}>
              <Box display="flex" alignItems="center" gap={0.5} mb={0.5}>
                <AutoAwesomeIcon sx={{ fontSize: 14, color: '#0369a1' }} />
                <Typography variant="caption" fontWeight={700} color="#0369a1">
                  Tóm tắt AI{displaySummaryDate ? ` – ${displaySummaryDate}` : ''}
                </Typography>
              </Box>
              <Typography variant="body2" color="text.secondary"
                sx={{
                  display: '-webkit-box',
                  WebkitLineClamp: expanded ? 100 : 5,
                  WebkitBoxOrient: 'vertical',
                  overflow: 'hidden',
                  lineHeight: 1.6,
                  fontSize: '0.82rem',
                  whiteSpace: 'pre-line',
                }}>
                {displaySummary}
              </Typography>
              <Box display="flex" alignItems="center" gap={0.5} mt={0.5}>
                {displaySummary.length > 200 && (
                  <Button size="small" onClick={() => setExpanded((e) => !e)}
                    sx={{ textTransform: 'none', fontSize: '0.73rem', p: 0, minWidth: 0 }}>
                    {expanded ? 'Thu gọn' : 'Xem thêm'}
                  </Button>
                )}
                <Button
                  size="small"
                  startIcon={<OpenWithIcon sx={{ fontSize: '12px !important' }} />}
                  onClick={() => setSummaryDialogOpen(true)}
                  sx={{ textTransform: 'none', fontSize: '0.73rem', ml: 'auto', color: '#0369a1' }}
                >
                  Xem đầy đủ
                </Button>
              </Box>
            </Box>

            <SummaryDialog
              open={summaryDialogOpen}
              onClose={() => setSummaryDialogOpen(false)}
              channelName={ch.display_name || `@${ch.username}`}
              summaryDate={displaySummaryDate}
              summary={displaySummary}
            />
          </>
        ) : ch.status === 'active' && (
          <Box sx={{ bgcolor: '#fafafa', borderRadius: 1.5, p: 1.5, mb: 1, textAlign: 'center' }}>
            <Typography variant="caption" color="text.disabled">
              Chưa có tóm tắt — nhấn <strong>Tóm tắt AI</strong> để tạo.
            </Typography>
          </Box>
        )}

        {/* Stats row */}
        <Box display="flex" alignItems="center" gap={1} flexWrap="wrap">
          {ch.post_count > 0 && (
            <Chip label={`${ch.post_count} bài`} size="small"
              sx={{ height: 19, fontSize: '0.67rem', bgcolor: '#f3f4f6', color: 'text.secondary' }} />
          )}
          {unread > 0 && (
            <Chip label={`${unread} tin mới`} size="small" color="primary" variant="outlined"
              sx={{ height: 19, fontSize: '0.67rem' }} />
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
            target="_blank" rel="noopener noreferrer"
            sx={{ textTransform: 'none', fontSize: '0.78rem', color: 'text.secondary' }}
          >
            {(ch.username.startsWith('x:') || ch.username.startsWith('xkw:')) ? 'Xem trên X' : 'Telegram'}
          </Button>

          {(ch.status === 'active') && (
            <Button
              size="small"
              startIcon={
                summarizing
                  ? <CircularProgress size={12} color="inherit" />
                  : summaryDone
                  ? <CheckIcon sx={{ fontSize: '14px !important' }} />
                  : <AutoAwesomeIcon sx={{ fontSize: '14px !important' }} />
              }
              onClick={handleSummarize}
              disabled={summarizing}
              sx={{ textTransform: 'none', fontSize: '0.78rem', color: '#0369a1' }}
            >
              {summarizing ? 'Đang tải tin & tóm tắt…' : summaryDone ? 'Xong!' : 'Tóm tắt AI'}
            </Button>
          )}

          {ch.status === 'active' && ch.post_count > 0 && (
            <Button
              size="small"
              onClick={handleOpenPosts}
              sx={{ textTransform: 'none', fontSize: '0.78rem', color: 'text.secondary' }}
            >
              {`Xem tin${unread > 0 ? ` (${unread} mới)` : ''}`}
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
      />
    </Card>
  );
});

// ---------------------------------------------------------------------------
// Main page
// ---------------------------------------------------------------------------

export default function DashboardPage() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  const [channels, setChannels] = useState([]);
  const [loadingChannels, setLoadingChannels] = useState(true);
  const [toDelete, setToDelete] = useState(null);
  const [deleting, setDeleting] = useState(false);
  const [snack, setSnack] = useState({ open: false, msg: '', severity: 'info' });

  // Bulk import state
  const [bulkInput, setBulkInput] = useState('');
  const [bulkAdding, setBulkAdding] = useState(false);
  const [bulkResult, setBulkResult] = useState(null); // { added, skipped, errors, results }

  // Per-channel quick-subscribe (suggestions)
  const [quickSubscribing, setQuickSubscribing] = useState(new Set()); // Set of usernames in flight

  // My Telegram channels (from Telegram account)
  const [tgChannels, setTgChannels] = useState([]);          // channels fetched from Telegram
  const [tgChannelsVisible, setTgChannelsVisible] = useState(true); // toggle show/hide without re-fetch
  const [tgChannelsLoading, setTgChannelsLoading] = useState(false);
  const [tgChannelsError, setTgChannelsError] = useState('');
  const [tgSubscribing, setTgSubscribing] = useState(new Set()); // channel IDs in flight

  // Channel catalog (106 curated channels from channel.json, grouped by category)
  const [catalog, setCatalog] = useState([]);       // [{category, channels[]}]
  const [catalogLoading, setCatalogLoading] = useState(true);
  const [activeCategory, setActiveCategory] = useState(null);

  const loadDiscover = useCallback(async (signal) => {
    setCatalogLoading(true);
    try {
      const data = await apiGet('/user/channels/catalog', signal);
      setCatalog(Array.isArray(data) ? data : []);
    } catch (e) {
      if (e?.name !== 'AbortError') console.error(e);
    } finally { setCatalogLoading(false); }
  }, []);

  useEffect(() => {
    const ac = new AbortController();
    loadDiscover(ac.signal);
    return () => ac.abort();
  }, [loadDiscover]);

  const loadChannels = useCallback(async (silent = false, signal) => {
    if (!silent) setLoadingChannels(true);
    try {
      const data = await apiGet('/user/channels', signal);
      setChannels(Array.isArray(data) ? data : []);
    } catch (e) {
      if (e?.name === 'AbortError') return;
      if (!silent) setSnack({ open: true, msg: `Không tải được danh sách kênh: ${e.message}`, severity: 'error' });
    } finally {
      if (!silent) setLoadingChannels(false);
    }
  }, []);

  useEffect(() => {
    const ac = new AbortController();
    loadChannels(false, ac.signal);
    return () => ac.abort();
  }, [loadChannels]);

  // ── Fetch my Telegram channels (from user's Telegram account) ───────────────
  const loadTelegramChannels = useCallback(async () => {
    setTgChannelsLoading(true);
    setTgChannelsError('');
    try {
      const data = await apiGet('/auth/telegram/channels');
      setTgChannels(Array.isArray(data) ? data : []);
    } catch (e) {
      setTgChannelsError(e.message || 'Không thể lấy danh sách kênh Telegram');
    } finally {
      setTgChannelsLoading(false);
    }
  }, []);

  // Subscribe one Telegram channel by its ID
  const handleTgSubscribe = useCallback(async (channel) => {
    setTgSubscribing((prev) => new Set([...prev, channel.id]));
    try {
      await apiPost('/auth/telegram/select-channels', { channel_ids: [channel.id] });
      setSnack({ open: true, msg: `Đã theo dõi "${channel.name}"!`, severity: 'success' });
      loadChannels();
    } catch (err) {
      if (err.message?.includes('đã đăng ký')) {
        setSnack({ open: true, msg: 'Bạn đã theo dõi kênh này rồi.', severity: 'info' });
      } else {
        setSnack({ open: true, msg: err.message || 'Không thể thêm kênh', severity: 'error' });
      }
    } finally {
      setTgSubscribing((prev) => { const s = new Set(prev); s.delete(channel.id); return s; });
    }
  }, [loadChannels]);

  // ── Bulk import ─────────────────────────────────────────────────────────────
  const handleBulkAdd = useCallback(async () => {
    // Parse comma/newline/space-separated links
    const links = bulkInput
      .split(/[\s,;|\n]+/)
      .map((s) => s.trim())
      .filter(Boolean);
    if (!links.length) return;

    setBulkAdding(true);
    setBulkResult(null);
    try {
      if (links.length === 1) {
        // Use single endpoint for single link
        const res = await apiPost('/user/channels', { channel_link: links[0] });
        setBulkResult({ added: 1, skipped: 0, errors: 0, results: [{ ...res, status: res.status }] });
      } else {
        const res = await apiPost('/user/channels/bulk', { channel_links: links });
        setBulkResult({ ...res.summary, results: res.results });
      }
      setBulkInput('');
      loadChannels();
    } catch (err) {
      // 409 from single endpoint
      if (err.message?.includes('đã đăng ký')) {
        setBulkResult({ added: 0, skipped: 1, errors: 0, results: [{ status: 'duplicate', message: err.message }] });
      } else {
        setSnack({ open: true, msg: err.message || 'Lỗi không xác định', severity: 'error' });
      }
    } finally {
      setBulkAdding(false);
    }
  }, [bulkInput, loadChannels]);

  // ── Quick subscribe (from suggestions) ─────────────────────────────────────
  const handleQuickSubscribe = useCallback(async (channelUsername) => {
    setQuickSubscribing((prev) => new Set([...prev, channelUsername]));
    try {
      await apiPost('/user/channels', { channel_link: `t.me/${channelUsername}` });
      setSnack({ open: true, msg: `Đã theo dõi @${channelUsername}!`, severity: 'success' });
      loadChannels();
      loadDiscover();
    } catch (err) {
      if (err.message?.includes('đã đăng ký')) {
        setSnack({ open: true, msg: 'Bạn đã theo dõi kênh này rồi.', severity: 'info' });
      } else {
        setSnack({ open: true, msg: err.message || 'Không thể thêm kênh', severity: 'error' });
      }
    } finally {
      setQuickSubscribing((prev) => { const s = new Set(prev); s.delete(channelUsername); return s; });
    }
  }, [loadChannels, loadDiscover]);

  // ── Unsubscribe ─────────────────────────────────────────────────────────────
  const handleConfirmDelete = useCallback(async () => {
    if (!toDelete) return;
    setDeleting(true);
    try {
      await apiDelete(`/user/channels/${toDelete.username}`);
      setChannels((prev) => prev.filter((c) => c.username !== toDelete.username));
      setSnack({ open: true, msg: 'Đã hủy đăng ký kênh.', severity: 'success' });
    } catch (err) {
      setSnack({ open: true, msg: `Lỗi: ${err.message}`, severity: 'error' });
    } finally {
      setDeleting(false);
      setToDelete(null);
    }
  }, [toDelete]);

  const handleLogout = useCallback(async () => { await logout(); navigate('/'); }, [logout, navigate]);

  const handleSummarized = useCallback(() => loadChannels(true), [loadChannels]);

  // ── Render ────────────────────────────────────────────────────────────────
  return (
    <Box sx={{ minHeight: '100vh', bgcolor: '#f9fafb' }}>
      {/* ── Navbar ── */}
      <AppBar position="sticky" elevation={0}
        sx={{ bgcolor: 'white', borderBottom: '1px solid #e5e7eb', color: 'text.primary' }}>
        <Toolbar gap={2}>
          <NewspaperIcon sx={{ color: 'primary.main', mr: 1 }} />
          <Typography variant="h6" fontWeight={700} color="primary" sx={{ flexGrow: 1 }}>
            NewsBot
          </Typography>
          <Stack direction="row" spacing={1} alignItems="center">
            <Button component={RouterLink} to="/" size="small"
              sx={{ textTransform: 'none', color: 'text.secondary' }}>
              Trang công khai
            </Button>
            <Typography variant="body2" color="text.secondary" sx={{ display: { xs: 'none', sm: 'block' } }}>
              Xin chào, <strong>{user?.full_name || user?.username}</strong>
            </Typography>
            <Tooltip title="Đăng xuất">
              <IconButton size="small" onClick={handleLogout}>
                <LogoutIcon fontSize="small" />
              </IconButton>
            </Tooltip>
          </Stack>
        </Toolbar>
      </AppBar>

      <Container maxWidth="lg" sx={{ py: 4 }}>
        <Typography variant="h5" fontWeight={800} gutterBottom>
          Kênh đang theo dõi
        </Typography>
        <Typography variant="body2" color="text.secondary" mb={3}>
          Thêm kênh <strong>Telegram</strong> hoặc tài khoản <strong>X (Twitter)</strong> để AI tóm tắt nội dung mới nhất mỗi ngày.
        </Typography>

        {/* ══════════════════════════════════════════════════════════
            HYBRID ADD PANEL
            ══════════════════════════════════════════════════════════ */}
        <Paper elevation={0} sx={{ mb: 4, borderRadius: 3, border: '1px solid #e5e7eb', overflow: 'hidden' }}>

          {/* ── Section A: Bulk import ── */}
          <Box sx={{ p: 3 }}>
            <Typography variant="subtitle1" fontWeight={700} mb={0.5} sx={{ display: 'flex', alignItems: 'center', gap: 0.75 }}>
              <ContentPasteIcon fontSize="small" color="primary" />
              Thêm kênh (dán link)
            </Typography>
            <Typography variant="caption" color="text.secondary" display="block" mb={1.5}>
              Dán một hoặc nhiều link cùng lúc — phân cách bằng dấu phẩy, Enter, hoặc dấu cách.<br />
              <strong>Telegram:</strong> dùng <code>t.me/ten_kenh</code> hoặc <code>@ten_kenh</code> &nbsp;·&nbsp;
              <strong>X tài khoản:</strong> <code>x.com/username</code> &nbsp;·&nbsp;
              <strong>X hashtag:</strong> <code>#bitcoin</code>, <code>#AI</code>
            </Typography>

            <Box sx={{ display: 'flex', gap: 1.5, flexWrap: { xs: 'wrap', sm: 'nowrap' }, alignItems: 'flex-start' }}>
              <TextField
                multiline
                minRows={1}
                maxRows={4}
                size="small"
                placeholder="Telegram: t.me/vnexpress, @devvn  ·  X user: x.com/Reuters  ·  X hashtag: #bitcoin, #AI"
                value={bulkInput}
                onChange={(e) => { setBulkInput(e.target.value); setBulkResult(null); }}
                onKeyDown={(e) => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); handleBulkAdd(); } }}
                disabled={bulkAdding}
                sx={{ flexGrow: 1 }}
                InputProps={{
                  startAdornment: (
                    <InputAdornment position="start" sx={{ alignSelf: 'flex-start', mt: '6px' }}>
                      <LinkIcon fontSize="small" sx={{ color: 'text.disabled' }} />
                    </InputAdornment>
                  ),
                }}
              />
              <Button
                variant="contained"
                onClick={handleBulkAdd}
                disabled={bulkAdding || !bulkInput.trim()}
                startIcon={bulkAdding ? <CircularProgress size={14} color="inherit" /> : <AddIcon />}
                sx={{ textTransform: 'none', borderRadius: 2, boxShadow: 'none', whiteSpace: 'nowrap', alignSelf: 'flex-start', mt: '1px' }}
              >
                {bulkAdding ? 'Đang thêm…' : 'Thêm'}
              </Button>
            </Box>

            {/* Bulk result summary */}
            {bulkResult && (
              <Collapse in>
                <Box mt={1.5}>
                  {(bulkResult.added > 0 || bulkResult.skipped > 0) && (
                    <Alert severity={bulkResult.errors > 0 ? 'warning' : 'success'} sx={{ borderRadius: 2, mb: 1 }}>
                      {bulkResult.added > 0 && <><strong>+{bulkResult.added} kênh</strong> đã thêm thành công. </>}
                      {bulkResult.skipped > 0 && <>{bulkResult.skipped} kênh đã theo dõi trước đó. </>}
                      {bulkResult.errors > 0 && <>{bulkResult.errors} link không hợp lệ (xem chi tiết bên dưới).</>}
                    </Alert>
                  )}
                  {bulkResult.results?.filter(r => r.status === 'error').map((r, i) => (
                    <Alert key={i} severity="error" sx={{ borderRadius: 2, mb: 0.5, fontSize: '0.8rem' }}>
                      <code>{r.channel_link}</code> — {r.message}
                    </Alert>
                  ))}
                </Box>
              </Collapse>
            )}

            <Typography variant="caption" color="text.disabled" display="block" mt={1}>
              📱 <strong>Telegram:</strong> <code>t.me/ten_kenh</code> · <code>@ten_kenh</code> · <code>ten_kenh</code>
              &nbsp;&nbsp;|&nbsp;&nbsp;
              🐦 <strong>X tài khoản:</strong> <code>x.com/username</code> · <code>twitter.com/username</code>
              &nbsp;&nbsp;|&nbsp;&nbsp;
              🔍 <strong>X hashtag:</strong> <code>#bitcoin</code> · <code>#AI</code>
            </Typography>
          </Box>
        </Paper>

        {/* ══════════════════════════════════════════════════════════
            KÊNH TELEGRAM CỦA TÔI (quét từ tài khoản Telegram)
            ══════════════════════════════════════════════════════════ */}
        <Paper elevation={0} sx={{ mb: 4, borderRadius: 3, border: '1px solid #e5e7eb', overflow: 'hidden' }}>
          <Box sx={{ p: 3 }}>
            <Box display="flex" alignItems="center" justifyContent="space-between" mb={1}>
              <Typography variant="subtitle1" fontWeight={700} sx={{ display: 'flex', alignItems: 'center', gap: 0.75 }}>
                <TelegramIcon fontSize="small" color="primary" />
                Kênh Telegram của tôi
              </Typography>
              <Stack direction="row" gap={0.5}>
                {tgChannels.length > 0 && tgChannelsVisible && (
                  <Tooltip title="Làm mới">
                    <span>
                      <IconButton size="small" onClick={loadTelegramChannels} disabled={tgChannelsLoading}>
                        <RefreshIcon fontSize="small" />
                      </IconButton>
                    </span>
                  </Tooltip>
                )}
                {tgChannels.length > 0 && (
                  <Tooltip title={tgChannelsVisible ? 'Ẩn danh sách' : 'Hiện danh sách'}>
                    <IconButton size="small" onClick={() => setTgChannelsVisible(v => !v)}>
                      {tgChannelsVisible ? <ExpandLessIcon fontSize="small" /> : <ExpandMoreIcon fontSize="small" />}
                    </IconButton>
                  </Tooltip>
                )}
              </Stack>
            </Box>
            <Typography variant="caption" color="text.secondary" display="block" mb={2}>
              Quét tài khoản Telegram để tìm các kênh công khai bạn đang theo dõi.
              Chọn kênh nào muốn AI tóm tắt — bạn có thể thay đổi bất cứ lúc nào.
            </Typography>

            {tgChannels.length === 0 && !tgChannelsLoading && !tgChannelsError && (
              <Button
                variant="outlined"
                onClick={() => { setTgChannelsVisible(true); loadTelegramChannels(); }}
                startIcon={<TelegramIcon />}
                sx={{ textTransform: 'none', borderRadius: 2 }}
              >
                Quét kênh từ Telegram
              </Button>
            )}

            {tgChannels.length > 0 && !tgChannelsVisible && (
              <Typography variant="caption" color="text.secondary">
                {tgChannels.length} kênh đã quét —{' '}
                <Box component="span" sx={{ color: 'primary.main', cursor: 'pointer', textDecoration: 'underline' }}
                  onClick={() => setTgChannelsVisible(true)}>
                  Hiện lại
                </Box>
              </Typography>
            )}

            {tgChannelsLoading && (
              <Box sx={{ textAlign: 'center', py: 3 }}>
                <CircularProgress size={28} />
                <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>
                  Đang quét kênh Telegram...
                </Typography>
              </Box>
            )}

            {tgChannelsError && (
              <Alert severity="error" sx={{ borderRadius: 2, mb: 1 }}>
                {tgChannelsError}
                {tgChannelsError.includes('Chưa liên kết') && (
                  <Typography variant="caption" display="block" mt={0.5}>
                    Bạn cần đăng nhập bằng Telegram trước để sử dụng tính năng này.
                  </Typography>
                )}
              </Alert>
            )}

            {tgChannels.length > 0 && !tgChannelsLoading && tgChannelsVisible && (
              <>
                <Typography variant="body2" color="text.secondary" mb={1}>
                  Tìm thấy <strong>{tgChannels.length}</strong> kênh công khai. Nhấp vào kênh để theo dõi.
                </Typography>
                <Grid container spacing={1.5}>
                  {tgChannels.map((ch) => {
                    const alreadySubscribed = channels.some(
                      (sub) => sub.username === (ch.username || '').toLowerCase() || sub.username === `tg_id_${ch.id}`
                    );
                    const inFlight = tgSubscribing.has(ch.id);
                    return (
                      <Grid item xs={12} sm={6} md={4} key={ch.id}>
                        <Paper elevation={0} sx={{
                          p: 1.5, borderRadius: 2, border: '1px solid',
                          borderColor: alreadySubscribed ? 'success.main' : '#e5e7eb',
                          bgcolor: alreadySubscribed ? '#f0fdf4' : 'white',
                          display: 'flex', alignItems: 'center', gap: 1.5,
                          transition: 'all 0.15s',
                          cursor: alreadySubscribed ? 'default' : 'pointer',
                          '&:hover': !alreadySubscribed ? { borderColor: 'primary.main', bgcolor: '#f0f7ff', boxShadow: '0 2px 8px rgba(0,0,0,0.08)' } : {},
                        }}
                          onClick={() => !alreadySubscribed && !inFlight && handleTgSubscribe(ch)}
                        >
                          <Avatar sx={{
                            bgcolor: alreadySubscribed ? '#dcfce7' : '#e8f4fd',
                            color: alreadySubscribed ? '#16a34a' : '#0088cc',
                            width: 38, height: 38, flexShrink: 0,
                          }}>
                            {ch.is_megagroup ? <GroupsIcon sx={{ fontSize: 20 }} /> : <PublicIcon sx={{ fontSize: 20 }} />}
                          </Avatar>
                          <Box flex={1} minWidth={0}>
                            <Typography variant="body2" fontWeight={700} noWrap
                              color={alreadySubscribed ? 'success.main' : 'text.primary'}>
                              {ch.name}
                            </Typography>
                            <Stack direction="row" gap={0.5} flexWrap="wrap" mt={0.25}>
                              {ch.username && (
                                <Chip label={`@${ch.username}`} size="small" variant="outlined" sx={{ height: 18, fontSize: '0.65rem' }} />
                              )}
                              <Chip
                                label={ch.is_megagroup ? 'Nhóm' : 'Kênh'}
                                size="small"
                                color={ch.is_megagroup ? 'success' : 'primary'}
                                sx={{ height: 18, fontSize: '0.65rem' }}
                              />
                            </Stack>
                          </Box>
                          <Box flexShrink={0}>
                            {inFlight ? (
                              <CircularProgress size={20} />
                            ) : alreadySubscribed ? (
                              <Tooltip title="Đang theo dõi">
                                <CheckIcon sx={{ color: 'success.main', fontSize: 22 }} />
                              </Tooltip>
                            ) : (
                              <Tooltip title={`Theo dõi "${ch.name}"`}>
                                <AddIcon sx={{ color: '#9ca3af', fontSize: 22 }} />
                              </Tooltip>
                            )}
                          </Box>
                        </Paper>
                      </Grid>
                    );
                  })}
                </Grid>
              </>
            )}
          </Box>
        </Paper>

        {/* ══════════════════════════════════════════════════════════
            DANH MỤC KÊNH GỢI Ý
            ══════════════════════════════════════════════════════════ */}
        <Box mb={4}>
          <Box display="flex" alignItems="center" justifyContent="space-between" mb={1.5}>
            <Typography variant="subtitle1" fontWeight={700}>
              Khám phá kênh theo chủ đề
            </Typography>
            <Tooltip title="Làm mới">
              <span>
                <IconButton size="small" onClick={loadDiscover} disabled={catalogLoading}>
                  <RefreshIcon fontSize="small" />
                </IconButton>
              </span>
            </Tooltip>
          </Box>

          {catalogLoading ? (
            <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap' }}>
              {[1,2,3,4,5,6].map(i => <Skeleton key={i} variant="rounded" width={110} height={30} />)}
            </Box>
          ) : (
            <>
              {/* Category chips — click to expand */}
              <Box sx={{ display: 'flex', gap: 0.75, flexWrap: 'wrap', mb: activeCategory ? 2 : 0 }}>
                {catalog.map((g) => {
                  const selected = activeCategory === g.category;
                  return (
                    <Chip
                      key={g.category}
                      label={`${g.category} (${g.channels.length})`}
                      size="small"
                      onClick={() => setActiveCategory(selected ? null : g.category)}
                      color={selected ? 'primary' : 'default'}
                      variant={selected ? 'filled' : 'outlined'}
                      sx={{ fontSize: '0.73rem', cursor: 'pointer', fontWeight: selected ? 700 : 400 }}
                    />
                  );
                })}
              </Box>

              {/* Channels grid — only shown when a category is selected */}
              <Collapse in={!!activeCategory}>
                <Grid container spacing={1.5}>
                  {(catalog.find(g => g.category === activeCategory)?.channels ?? []).map((ch) => {
                    const isSubscribed = ch.subscribed;
                    const inFlight = quickSubscribing.has(ch.username);
                    return (
                      <Grid item xs={12} sm={6} md={3} key={ch.username}>
                        <Paper elevation={0} sx={{
                          p: 1.5, borderRadius: 2, border: '1px solid',
                          borderColor: isSubscribed ? 'primary.main' : '#e5e7eb',
                          bgcolor: isSubscribed ? '#f0f7ff' : 'white',
                          display: 'flex', alignItems: 'center', gap: 1.5,
                          transition: 'all 0.15s',
                          cursor: isSubscribed ? 'default' : 'pointer',
                          '&:hover': !isSubscribed ? { borderColor: 'primary.main', bgcolor: '#f0f7ff', boxShadow: '0 2px 8px rgba(0,0,0,0.08)' } : {},
                        }}
                          onClick={() => !isSubscribed && !inFlight && handleQuickSubscribe(ch.username)}
                        >
                          <Avatar sx={{ bgcolor: '#e8f4fd', color: '#0088cc', width: 38, height: 38, flexShrink: 0 }}>
                            <TelegramIcon sx={{ fontSize: 20 }} />
                          </Avatar>
                          <Box flex={1} minWidth={0}>
                            <Typography variant="body2" fontWeight={700} noWrap
                              color={isSubscribed ? 'primary' : 'text.primary'}>
                              {ch.display_name || `@${ch.username}`}
                            </Typography>
                            <Typography variant="caption" color="text.secondary" noWrap display="block">
                              @{ch.username}
                            </Typography>
                          </Box>
                          <Box flexShrink={0}>
                            {inFlight ? (
                              <CircularProgress size={20} />
                            ) : isSubscribed ? (
                              <Tooltip title="Đang theo dõi">
                                <CheckIcon sx={{ color: 'primary.main', fontSize: 22 }} />
                              </Tooltip>
                            ) : (
                              <Tooltip title={`Theo dõi @${ch.username}`}>
                                <AddIcon sx={{ color: '#9ca3af', fontSize: 22 }} />
                              </Tooltip>
                            )}
                          </Box>
                        </Paper>
                      </Grid>
                    );
                  })}
                </Grid>
              </Collapse>
            </>
          )}
        </Box>

        {/* ── Channel list ── */}
        <Box display="flex" alignItems="center" justifyContent="space-between" mb={1.5}>
          <Typography variant="subtitle1" fontWeight={700}>
            {loadingChannels ? 'Đang tải…' : `${channels.length} kênh đang theo dõi`}
          </Typography>
          <Tooltip title="Làm mới">
            <span>
              <IconButton size="small" onClick={loadChannels} disabled={loadingChannels}>
                <RefreshIcon fontSize="small" />
              </IconButton>
            </span>
          </Tooltip>
        </Box>

        {loadingChannels ? (
          <Box sx={{ display: 'grid', gap: 2, gridTemplateColumns: { xs: '1fr', sm: 'repeat(2,1fr)', md: 'repeat(3,1fr)' } }}>
            {[1, 2, 3].map((i) => (
              <Skeleton key={i} variant="rectangular" height={160} sx={{ borderRadius: 2.5 }} />
            ))}
          </Box>
        ) : channels.length === 0 ? (
          <Box textAlign="center" py={8} sx={{ bgcolor: 'white', borderRadius: 3, border: '1px dashed #d1d5db' }}>
            <TelegramIcon sx={{ fontSize: 48, color: 'text.disabled', mb: 1 }} />
            <Typography color="text.secondary" variant="subtitle2">
              Bạn chưa theo dõi kênh nào.
            </Typography>
            <Typography variant="caption" color="text.disabled">
              Chọn kênh phổ biến bên trên hoặc dán link kênh để bắt đầu.
            </Typography>
          </Box>
        ) : (
          <Box sx={{ display: 'grid', gap: 2, gridTemplateColumns: { xs: '1fr', sm: 'repeat(2,1fr)', md: 'repeat(3,1fr)' } }}>
            {channels.map((ch) => (
              <ChannelCard key={ch.username} ch={ch} onUnsubscribe={setToDelete} onSummarized={handleSummarized} />
            ))}
          </Box>
        )}
      </Container>

      {/* ── Confirm unsubscribe dialog ── */}
      <Dialog open={!!toDelete} onClose={() => setToDelete(null)}>
        <DialogTitle>Hủy đăng ký kênh?</DialogTitle>
        <DialogContent>
          <DialogContentText>
            Bạn có chắc muốn hủy theo dõi kênh&nbsp;
            <strong>@{toDelete?.username}</strong>?
            Tóm tắt của kênh này sẽ không còn hiển thị trên trang của bạn.
          </DialogContentText>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setToDelete(null)} sx={{ textTransform: 'none' }}>Hủy</Button>
          <Button onClick={handleConfirmDelete} color="error" variant="contained" disabled={deleting}
            sx={{ textTransform: 'none', boxShadow: 'none' }}>
            {deleting ? <CircularProgress size={16} color="inherit" /> : 'Xác nhận hủy'}
          </Button>
        </DialogActions>
      </Dialog>

      {/* ── Snackbar ── */}
      <Snackbar
        open={snack.open}
        autoHideDuration={4000}
        onClose={() => setSnack((s) => ({ ...s, open: false }))}
        anchorOrigin={{ vertical: 'bottom', horizontal: 'center' }}
      >
        <Alert severity={snack.severity} onClose={() => setSnack((s) => ({ ...s, open: false }))}
          sx={{ borderRadius: 2 }}>
          {snack.msg}
        </Alert>
      </Snackbar>
    </Box>
  );
}
