/**
 * DashboardPage – bảng điều khiển cá nhân dành cho user đã đăng nhập.
 * Refactored: extracted sub-components to components/dashboard/ and pages/user/tabs/
 */
import React, { useState, useEffect, useCallback } from 'react';
import { Link as RouterLink, useNavigate } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext.jsx';
import {
  Box,
  Container,
  Typography,
  TextField,
  Button,
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
  Tab,
  Tabs,
} from '@mui/material';
import AddIcon from '@mui/icons-material/Add';
import RefreshIcon from '@mui/icons-material/Refresh';
import TelegramIcon from '@mui/icons-material/Telegram';
import NewspaperIcon from '@mui/icons-material/Newspaper';
import LogoutIcon from '@mui/icons-material/Logout';
import LinkIcon from '@mui/icons-material/Link';
import ContentPasteIcon from '@mui/icons-material/ContentPaste';
import CheckIcon from '@mui/icons-material/Check';
import ExpandLessIcon from '@mui/icons-material/ExpandLess';
import ExpandMoreIcon from '@mui/icons-material/ExpandMore';
import PublicIcon from '@mui/icons-material/Public';
import GroupsIcon from '@mui/icons-material/Groups';
import BookmarkIcon from '@mui/icons-material/Bookmark';
import HistoryIcon from '@mui/icons-material/History';
import { apiGet, apiPost, apiDelete } from '../../lib/dashApi.js';
import AudioPlayer from '../../components/AudioPlayer.jsx';
import ChannelCard from '../../components/dashboard/ChannelCard.jsx';
import BookmarksDashTab from '../../components/dashboard/BookmarksDashTab.jsx';
import ReadHistoryTab from '../../components/dashboard/ReadHistoryTab.jsx';

// ---------------------------------------------------------------------------
// Main page
// ---------------------------------------------------------------------------


export default function DashboardPage() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  const [dashTab, setDashTab] = useState(0); // 0=Kênh, 1=Đã lưu, 2=Đã đọc

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

  // ── Audio player state (global sticky bar) ───────────────────────────────
  const [audioState, setAudioState] = useState(null); // { url, title }
  const handlePlayAudio = useCallback(({ url, title }) => {
    setAudioState((prev) => {
      if (prev?.url && prev.url !== url) URL.revokeObjectURL(prev.url);
      return { url, title };
    });
  }, []);
  const handleCloseAudio = useCallback(() => {
    setAudioState((prev) => {
      if (prev?.url) URL.revokeObjectURL(prev.url);
      return null;
    });
  }, []);

  // ── Render ────────────────────────────────────────────────────────────────
  return (
    <Box sx={{ minHeight: '100vh', bgcolor: 'background.default' }}>
      {/* ── Navbar ── */}
      <AppBar position="sticky" elevation={0}
        sx={{ bgcolor: 'background.paper', borderBottom: '1px solid', borderColor: 'divider', color: 'text.primary' }}>
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
        {/* ── Top header ── */}
        <Typography variant="h5" fontWeight={800} gutterBottom>
          Bảng điều khiển
        </Typography>

        {/* ── Main tab navigation ── */}
        <Tabs
          value={dashTab}
          onChange={(_, v) => setDashTab(v)}
          sx={{
            mb: 3,
            borderBottom: '1px solid',
            borderColor: 'divider',
            '& .MuiTab-root': { textTransform: 'none', fontWeight: 600, fontSize: '0.9rem' },
          }}
        >
          <Tab icon={<TelegramIcon sx={{ fontSize: 18 }} />} iconPosition="start" label="Kênh theo dõi" />
          <Tab icon={<BookmarkIcon sx={{ fontSize: 18 }} />} iconPosition="start" label="Đã lưu" />
          <Tab icon={<HistoryIcon sx={{ fontSize: 18 }} />} iconPosition="start" label="Đã đọc" />
        </Tabs>

        {/* ── Tab: Đã lưu ── */}
        {dashTab === 1 && <BookmarksDashTab />}

        {/* ── Tab: Đã đọc ── */}
        {dashTab === 2 && <ReadHistoryTab />}

        {/* ── Tab: Kênh theo dõi (hidden but mounted when other tabs active) ── */}
        <Box sx={{ display: dashTab === 0 ? 'block' : 'none' }}>
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
          <Box textAlign="center" py={8} sx={{ bgcolor: 'background.paper', borderRadius: 3, border: '1px dashed', borderColor: 'divider' }}>
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
              <ChannelCard key={ch.username} ch={ch} onUnsubscribe={setToDelete} onSummarized={handleSummarized} onPlayAudio={handlePlayAudio} />
            ))}
          </Box>
        )}
        </Box> {/* end dashTab === 0 wrapper */}
      </Container>

      {audioState && (
        <AudioPlayer
          audioUrl={audioState.url}
          title={audioState.title}
          onClose={handleCloseAudio}
        />
      )}

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
