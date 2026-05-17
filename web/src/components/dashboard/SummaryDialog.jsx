import React, { useState, useEffect } from 'react';
import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Box,
  Typography,
  Button,
  CircularProgress,
  Alert,
  IconButton,
  Pagination,
  useTheme,
  useMediaQuery,
} from '@mui/material';
import AutoAwesomeIcon from '@mui/icons-material/AutoAwesome';
import CheckIcon from '@mui/icons-material/Check';
import NewspaperIcon from '@mui/icons-material/Newspaper';
import { apiGet } from '../../lib/dashApi.js';
import DashArticleCard from './DashArticleCard.jsx';

const SUMMARY_PAGE_SIZE = 20;

const SummaryDialog = React.memo(function SummaryDialog({ open, onClose, channelUsername, channelName, onPlayAudio }) {
  const theme = useTheme();
  const isMobile = useMediaQuery(theme.breakpoints.down('sm'));
  const [linkPosts, setLinkPosts] = useState([]);
  const [summaryMeta, setSummaryMeta] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [page, setPage] = useState(1);

  useEffect(() => {
    if (!open || !channelUsername) return;
    setLinkPosts([]);
    setSummaryMeta(null);
    setError(null);
    setLoading(true);
    setPage(1);
    const ac = new AbortController();
    apiGet(`/user/channels/${encodeURIComponent(channelUsername)}/summary`, ac.signal)
      .then((res) => {
        const latest = (res.summaries || [])[0] || null;
        if (latest) {
          setLinkPosts(latest.link_posts || []);
          setSummaryMeta({ date: latest.date, post_count: latest.post_count, generated_at: latest.generated_at });
        }
      })
      .catch((e) => { if (e?.name !== 'AbortError') setError(e.message); })
      .finally(() => setLoading(false));
    return () => ac.abort();
  }, [open, channelUsername]);

  return (
    <Dialog
      open={open}
      onClose={onClose}
      maxWidth="md"
      fullWidth
      fullScreen={isMobile}
      PaperProps={{ sx: { borderRadius: isMobile ? 0 : 3, maxHeight: '92vh' } }}
    >
      <DialogTitle sx={{ pb: 1, borderBottom: '1px solid', borderColor: 'divider', bgcolor: '#f0f9ff' }}>
        <Box display="flex" alignItems="center" gap={1}>
          <AutoAwesomeIcon sx={{ color: '#0369a1', fontSize: 20 }} />
          <Box flex={1} minWidth={0}>
            <Typography variant="subtitle1" fontWeight={700} color="#0369a1" noWrap>
              Bản tin — {channelName}
            </Typography>
            <Typography variant="caption" color="text.secondary">
              {linkPosts.length > 0 ? `${linkPosts.length} bài` : ''}
              {summaryMeta?.date ? ` · ${summaryMeta.date}` : ''}
            </Typography>
          </Box>
          <IconButton size="small" onClick={onClose} sx={{ flexShrink: 0 }}>
            <CheckIcon fontSize="small" />
          </IconButton>
        </Box>
      </DialogTitle>

      <DialogContent sx={{ px: { xs: 1.5, sm: 3 }, py: 2 }}>
        {loading && (
          <Box display="flex" flexDirection="column" alignItems="center" py={6} gap={2}>
            <CircularProgress size={32} color="primary" />
            <Typography variant="body2" color="text.secondary">Đang tải bản tin…</Typography>
          </Box>
        )}
        {error && <Alert severity="error" sx={{ mb: 1 }}>{error}</Alert>}

        {!loading && !error && linkPosts.length === 0 && (
          <Box textAlign="center" py={6}>
            <NewspaperIcon sx={{ fontSize: 48, color: 'text.disabled', mb: 1 }} />
            <Typography variant="body2" color="text.secondary">
              Chưa có bài nào. Hãy tạo tóm tắt AI trước.
            </Typography>
          </Box>
        )}

        {!loading && linkPosts.length > 0 && (
          <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1.5 }}>
            {linkPosts
              .slice((page - 1) * SUMMARY_PAGE_SIZE, page * SUMMARY_PAGE_SIZE)
              .map((article, i) => (
                <DashArticleCard
                  key={article.url || i}
                  article={article}
                  index={(page - 1) * SUMMARY_PAGE_SIZE + i}
                  onPlayAudio={onPlayAudio}
                />
              ))}
            {linkPosts.length > SUMMARY_PAGE_SIZE && (
              <Box display="flex" justifyContent="center" pt={1} pb={0.5}>
                <Pagination
                  count={Math.ceil(linkPosts.length / SUMMARY_PAGE_SIZE)}
                  page={page}
                  onChange={(_, v) => setPage(v)}
                  size="small"
                  color="primary"
                  siblingCount={1}
                  boundaryCount={1}
                />
              </Box>
            )}
          </Box>
        )}
      </DialogContent>

      <DialogActions sx={{ px: 3, pb: 2, borderTop: '1px solid', borderColor: 'divider' }}>
        <Typography variant="caption" color="text.disabled" sx={{ flex: 1 }}>
          {linkPosts.length > 0 ? `${linkPosts.length} bài trong bản tin` : ''}
        </Typography>
        <Button onClick={onClose} variant="outlined" size="small" sx={{ textTransform: 'none', borderRadius: 2 }}>
          Đóng
        </Button>
      </DialogActions>
    </Dialog>
  );
});

export default SummaryDialog;
