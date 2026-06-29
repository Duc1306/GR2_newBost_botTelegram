import React, { useCallback, useEffect, useMemo, useState } from 'react';
import {
  Alert,
  Box,
  Button,
  Chip,
  CircularProgress,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  Divider,
  FormControlLabel,
  Grid,
  IconButton,
  Paper,
  Stack,
  Switch,
  TextField,
  Tooltip,
  Typography,
} from '@mui/material';
import AddIcon from '@mui/icons-material/Add';
import AutoAwesomeIcon from '@mui/icons-material/AutoAwesome';
import CleaningServicesIcon from '@mui/icons-material/CleaningServices';
import DeleteIcon from '@mui/icons-material/Delete';
import EditIcon from '@mui/icons-material/Edit';
import PlaylistAddCheckIcon from '@mui/icons-material/PlaylistAddCheck';
import PsychologyIcon from '@mui/icons-material/Psychology';
import RefreshIcon from '@mui/icons-material/Refresh';
import { api } from '../../lib/api.jsx';

const emptyForm = {
  slug: '',
  name: '',
  description: '',
  keywords: '',
  color: '#6b7280',
  priority: 99,
  active: true,
};

function parseKeywords(value) {
  return value
    .split(',')
    .map((item) => item.trim())
    .filter(Boolean);
}

function cleanSlug(slug) {
  return (slug || '').trim();
}

function slugPath(slug) {
  return encodeURIComponent(cleanSlug(slug));
}

function toForm(topic) {
  return {
    slug: topic.slug || '',
    name: topic.name || '',
    description: topic.description || '',
    keywords: (topic.keywords || []).join(', '),
    color: topic.color || '#6b7280',
    priority: topic.priority ?? 99,
    active: topic.active !== false,
  };
}

function formatError(err) {
  try {
    return JSON.parse(err.message)?.detail || err.message;
  } catch {
    return err?.message || 'Thao tác thất bại';
  }
}

export default function HotTopicAdminPanel() {
  const [topics, setTopics] = useState([]);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState('');
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [formOpen, setFormOpen] = useState(false);
  const [editingSlug, setEditingSlug] = useState('');
  const [form, setForm] = useState(emptyForm);
  const [aiStatus, setAiStatus] = useState(null);
  const [detectHours, setDetectHours] = useState(24);
  const [maxTopics, setMaxTopics] = useState(5);
  const [autoSave, setAutoSave] = useState(false);
  const [suggestions, setSuggestions] = useState([]);

  const activeCount = useMemo(
    () => topics.filter((topic) => topic.active !== false).length,
    [topics]
  );

  const loadTopics = useCallback(async () => {
    setLoading(true);
    try {
      const { data } = await api.get('/admin/hot-topics');
      setTopics(data.topics || []);
      setError('');
    } catch (err) {
      setError(formatError(err));
    } finally {
      setLoading(false);
    }
  }, []);

  const runAction = useCallback(async (label, action, message) => {
    setBusy(label);
    setError('');
    setSuccess('');
    try {
      const result = await action();
      setSuccess(message || 'Thao tác thành công');
      return result;
    } catch (err) {
      setError(formatError(err));
      return null;
    } finally {
      setBusy('');
    }
  }, []);

  useEffect(() => {
    loadTopics();
  }, [loadTopics]);

  const openCreate = useCallback(() => {
    setEditingSlug('');
    setForm(emptyForm);
    setFormOpen(true);
  }, []);

  const openEdit = useCallback((topic) => {
    setEditingSlug(cleanSlug(topic.slug));
    setForm(toForm(topic));
    setFormOpen(true);
  }, []);

  const closeForm = useCallback(() => setFormOpen(false), []);

  const handleFormChange = useCallback((field, value) => {
    setForm((prev) => ({ ...prev, [field]: value }));
  }, []);

  const saveTopic = useCallback(async () => {
    const payload = {
      ...form,
      slug: cleanSlug(form.slug),
      keywords: parseKeywords(form.keywords),
      priority: Number(form.priority) || 99,
    };
    const result = await runAction(
      'save-topic',
      () => editingSlug
        ? api.put(`/admin/hot-topics/${slugPath(editingSlug)}`, payload)
        : api.post('/admin/hot-topics', payload),
      editingSlug ? 'Đã cập nhật hot topic' : 'Đã thêm hot topic'
    );
    if (result) {
      setFormOpen(false);
      loadTopics();
    }
  }, [editingSlug, form, loadTopics, runAction]);

  const deleteTopic = useCallback(async (slug) => {
    const result = await runAction(
      `delete-${slug}`,
      () => api.delete(`/admin/hot-topics/${slugPath(slug)}`),
      'Đã xóa hot topic'
    );
    if (result) loadTopics();
  }, [loadTopics, runAction]);

  const seedTopics = useCallback(async () => {
    const result = await runAction(
      'seed',
      () => api.post('/admin/hot-topics/seed', {}),
      'Đã seed hot topic mặc định'
    );
    if (result) loadTopics();
  }, [loadTopics, runAction]);

  const checkAiStatus = useCallback(async () => {
    const result = await runAction('ai-status', () => api.get('/admin/ai/status'));
    if (result) {
      setAiStatus(result.data);
      setSuccess('Đã kiểm tra trạng thái AI');
    }
  }, [runAction]);

  const detectHotTopics = useCallback(async () => {
    const result = await runAction(
      'detect',
      () => api.post(
        `/admin/ai/detect-hot-topics?hours=${detectHours}&max_topics=${maxTopics}&auto_save=${autoSave}`,
        {}
      ),
      autoSave ? 'AI đã phát hiện và lưu gợi ý' : 'AI đã phát hiện hot topic'
    );
    if (result) {
      setSuggestions(result.data.suggestions || []);
      if (autoSave) loadTopics();
    }
  }, [autoSave, detectHours, loadTopics, maxTopics, runAction]);

  const expandKeywords = useCallback(async (slug) => {
    const result = await runAction(
      `expand-${slug}`,
      () => api.post(`/admin/ai/expand-keywords/${slugPath(slug)}`, {}),
      'Đã mở rộng từ khóa bằng AI'
    );
    if (result) loadTopics();
  }, [loadTopics, runAction]);

  const clearCache = useCallback(async () => {
    await runAction(
      'clear-cache',
      () => api.delete('/admin/hotnews-cache'),
      'Đã xóa cache hot news'
    );
  }, [runAction]);

  return (
    <Paper sx={{ p: 3, mb: 3 }}>
      <Box display="flex" justifyContent="space-between" alignItems="flex-start" gap={2} flexWrap="wrap" mb={2}>
        <Box>
          <Box display="flex" alignItems="center" gap={1}>
            <PsychologyIcon color="primary" />
            <Typography variant="h6" fontWeight="bold">Quản trị hot topic và AI</Typography>
          </Box>
          <Typography variant="body2" color="text.secondary">
            {topics.length} hot topic, {activeCount} đang bật
          </Typography>
        </Box>
        <Stack direction="row" spacing={1} flexWrap="wrap" useFlexGap>
          <Tooltip title="Tải lại danh sách">
            <span>
              <IconButton onClick={loadTopics} disabled={loading || !!busy}>
                <RefreshIcon />
              </IconButton>
            </span>
          </Tooltip>
          <Button startIcon={<PlaylistAddCheckIcon />} variant="outlined" onClick={seedTopics} disabled={!!busy}>
            Seed mặc định
          </Button>
          <Button startIcon={<CleaningServicesIcon />} variant="outlined" color="warning" onClick={clearCache} disabled={!!busy}>
            Xóa cache
          </Button>
          <Button startIcon={<AddIcon />} variant="contained" onClick={openCreate}>
            Thêm hot topic
          </Button>
        </Stack>
      </Box>

      {error && <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError('')}>{error}</Alert>}
      {success && <Alert severity="success" sx={{ mb: 2 }} onClose={() => setSuccess('')}>{success}</Alert>}

      <Grid container spacing={2}>
        <Grid size={{ xs: 12, md: 8 }}>
          {loading ? (
            <Box display="flex" justifyContent="center" py={4}><CircularProgress /></Box>
          ) : (
            <Stack spacing={1.25}>
              {topics.map((topic) => (
                <Paper key={topic.slug} variant="outlined" sx={{ p: 1.5 }}>
                  <Box display="flex" justifyContent="space-between" gap={1.5} alignItems="flex-start">
                    <Box minWidth={0}>
                      <Box display="flex" alignItems="center" gap={1} flexWrap="wrap">
                        <Box sx={{ width: 12, height: 12, borderRadius: '50%', bgcolor: topic.color || '#6b7280' }} />
                        <Typography fontWeight="bold">{topic.name}</Typography>
                        <Chip size="small" label={topic.active === false ? 'tắt' : 'bật'} color={topic.active === false ? 'default' : 'success'} />
                        <Chip size="small" variant="outlined" label={`priority ${topic.priority ?? 99}`} />
                      </Box>
                      <Typography variant="caption" color="text.secondary">{topic.slug}</Typography>
                      {topic.description && (
                        <Typography variant="body2" color="text.secondary" sx={{ mt: 0.5 }}>
                          {topic.description}
                        </Typography>
                      )}
                      <Box display="flex" gap={0.5} flexWrap="wrap" mt={1}>
                        {(topic.keywords || []).slice(0, 10).map((keyword) => (
                          <Chip key={keyword} size="small" label={keyword} variant="outlined" />
                        ))}
                        {(topic.keywords || []).length > 10 && (
                          <Chip size="small" label={`+${topic.keywords.length - 10}`} />
                        )}
                      </Box>
                    </Box>
                    <Stack direction="row" spacing={0.5}>
                      <Tooltip title="Mở rộng từ khóa bằng AI">
                        <span>
                          <IconButton size="small" onClick={() => expandKeywords(topic.slug)} disabled={!!busy}>
                            <AutoAwesomeIcon fontSize="small" />
                          </IconButton>
                        </span>
                      </Tooltip>
                      <Tooltip title="Cập nhật hot topic">
                        <IconButton size="small" onClick={() => openEdit(topic)}>
                          <EditIcon fontSize="small" />
                        </IconButton>
                      </Tooltip>
                      <Tooltip title="Xóa hot topic">
                        <span>
                          <IconButton size="small" color="error" onClick={() => deleteTopic(topic.slug)} disabled={!!busy}>
                            <DeleteIcon fontSize="small" />
                          </IconButton>
                        </span>
                      </Tooltip>
                    </Stack>
                  </Box>
                </Paper>
              ))}
            </Stack>
          )}
        </Grid>

        <Grid size={{ xs: 12, md: 4 }}>
          <Paper variant="outlined" sx={{ p: 2 }}>
            <Typography variant="subtitle1" fontWeight="bold" gutterBottom>AI phát hiện hot topic</Typography>
            <Stack spacing={1.5}>
              <Button variant="outlined" startIcon={<PsychologyIcon />} onClick={checkAiStatus} disabled={!!busy}>
                Kiểm tra trạng thái AI
              </Button>
              {aiStatus && (
                <Alert severity={aiStatus.available ? 'success' : 'warning'}>
                  {aiStatus.available ? 'OpenAI đã sẵn sàng' : (aiStatus.message || 'AI chưa sẵn sàng')}
                </Alert>
              )}
              <TextField
                size="small"
                type="number"
                label="Khoảng giờ phân tích"
                value={detectHours}
                onChange={(e) => setDetectHours(Number(e.target.value))}
                inputProps={{ min: 1, max: 168 }}
              />
              <TextField
                size="small"
                type="number"
                label="Số gợi ý tối đa"
                value={maxTopics}
                onChange={(e) => setMaxTopics(Number(e.target.value))}
                inputProps={{ min: 1, max: 10 }}
              />
              <FormControlLabel
                control={<Switch checked={autoSave} onChange={(e) => setAutoSave(e.target.checked)} />}
                label="Tự lưu gợi ý"
              />
              <Button variant="contained" startIcon={<AutoAwesomeIcon />} onClick={detectHotTopics} disabled={!!busy}>
                Phát hiện bằng AI
              </Button>
              {busy && <LinearBusy />}
            </Stack>

            {suggestions.length > 0 && (
              <>
                <Divider sx={{ my: 2 }} />
                <Stack spacing={1}>
                  {suggestions.map((topic) => (
                    <Paper key={topic.slug} variant="outlined" sx={{ p: 1 }}>
                      <Typography variant="body2" fontWeight="bold">{topic.name}</Typography>
                      <Typography variant="caption" color="text.secondary">{topic.slug}</Typography>
                      <Box display="flex" gap={0.5} flexWrap="wrap" mt={0.75}>
                        {(topic.keywords || []).slice(0, 6).map((keyword) => (
                          <Chip key={keyword} size="small" label={keyword} />
                        ))}
                      </Box>
                    </Paper>
                  ))}
                </Stack>
              </>
            )}
          </Paper>
        </Grid>
      </Grid>

      <Dialog open={formOpen} onClose={closeForm} fullWidth maxWidth="sm">
        <DialogTitle>{editingSlug ? 'Cập nhật hot topic' : 'Thêm hot topic'}</DialogTitle>
        <DialogContent>
          <Stack spacing={2} sx={{ mt: 1 }}>
            <TextField label="Slug" value={form.slug} onChange={(e) => handleFormChange('slug', e.target.value)} disabled={!!editingSlug} fullWidth />
            <TextField label="Tên hot topic" value={form.name} onChange={(e) => handleFormChange('name', e.target.value)} fullWidth />
            <TextField label="Mô tả" value={form.description} onChange={(e) => handleFormChange('description', e.target.value)} fullWidth multiline minRows={2} />
            <TextField label="Từ khóa, cách nhau bằng dấu phẩy" value={form.keywords} onChange={(e) => handleFormChange('keywords', e.target.value)} fullWidth multiline minRows={2} />
            <Grid container spacing={2}>
              <Grid size={{ xs: 6 }}>
                <TextField label="Màu" type="color" value={form.color} onChange={(e) => handleFormChange('color', e.target.value)} fullWidth />
              </Grid>
              <Grid size={{ xs: 6 }}>
                <TextField label="Ưu tiên" type="number" value={form.priority} onChange={(e) => handleFormChange('priority', e.target.value)} fullWidth />
              </Grid>
            </Grid>
            <FormControlLabel
              control={<Switch checked={form.active} onChange={(e) => handleFormChange('active', e.target.checked)} />}
              label="Đang hoạt động"
            />
          </Stack>
        </DialogContent>
        <DialogActions>
          <Button onClick={closeForm}>Hủy</Button>
          <Button variant="contained" onClick={saveTopic} disabled={!form.slug || !form.name || !form.keywords || !!busy}>
            Lưu
          </Button>
        </DialogActions>
      </Dialog>
    </Paper>
  );
}

function LinearBusy() {
  return (
    <Box display="flex" alignItems="center" gap={1}>
      <CircularProgress size={18} />
      <Typography variant="caption" color="text.secondary">Đang xử lý...</Typography>
    </Box>
  );
}
