import React, { useCallback, useState } from 'react';
import {
  Alert,
  Box,
  Button,
  Checkbox,
  Divider,
  FormControlLabel,
  Grid,
  Paper,
  Stack,
  TextField,
  Typography,
} from '@mui/material';
import CloudDownloadIcon from '@mui/icons-material/CloudDownload';
import FactCheckIcon from '@mui/icons-material/FactCheck';
import PlayArrowIcon from '@mui/icons-material/PlayArrow';
import QueryStatsIcon from '@mui/icons-material/QueryStats';
import { api } from '../../lib/api.jsx';

function formatError(err) {
  try {
    return JSON.parse(err.message)?.detail || err.message;
  } catch {
    return err?.message || 'Thao tác thất bại';
  }
}

export default function OperationsPanel() {
  const [keywords, setKeywords] = useState('');
  const [maxItems, setMaxItems] = useState(50);
  const [language, setLanguage] = useState('vi');
  const [limit, setLimit] = useState(5000);
  const [geoOnly, setGeoOnly] = useState(false);
  const [aiOnly, setAiOnly] = useState(false);
  const [busy, setBusy] = useState('');
  const [result, setResult] = useState(null);
  const [error, setError] = useState('');

  const runAction = useCallback(async (label, action) => {
    setBusy(label);
    setError('');
    setResult(null);
    try {
      const { data } = await action();
      setResult(data);
    } catch (err) {
      setError(formatError(err));
    } finally {
      setBusy('');
    }
  }, []);

  const fetchX = useCallback(() => {
    const parsedKeywords = keywords
      .split(',')
      .map((item) => item.trim())
      .filter(Boolean);
    if (parsedKeywords.length === 0) {
      setError('Cần nhập ít nhất một từ khóa');
      return;
    }
    runAction('x-fetch', () => api.post('/admin/x/fetch', {
      keywords: parsedKeywords,
      max_items: Number(maxItems) || 50,
      language: language || 'vi',
    }));
  }, [keywords, language, maxItems, runAction]);

  const backfill = useCallback((countOnly) => {
    runAction(countOnly ? 'backfill-count' : 'backfill-run', () => api.post('/admin/backfill/topics-geo', {
      limit: Number(limit) || 5000,
      geo_only: geoOnly,
      ai_only: aiOnly,
      count_only: countOnly,
    }));
  }, [aiOnly, geoOnly, limit, runAction]);

  return (
    <Paper variant="outlined" sx={{ p: 2.5, mt: 3 }}>
      <Box display="flex" alignItems="center" gap={1} mb={0.5}>
        <FactCheckIcon color="primary" />
        <Typography variant="h6" fontWeight="bold">Tác vụ vận hành</Typography>
      </Box>
      <Typography variant="body2" color="text.secondary" mb={2}>
        Chạy thu thập X theo từ khóa và xử lý lại topic/geo cho dữ liệu còn thiếu.
      </Typography>

      {error && <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError('')}>{error}</Alert>}

      <Grid container spacing={3}>
        <Grid size={{ xs: 12, md: 6 }}>
          <Typography variant="subtitle1" fontWeight="bold" gutterBottom>Thu thập dữ liệu X</Typography>
          <Stack spacing={1.5}>
            <TextField
              size="small"
              label="Từ khóa"
              value={keywords}
              onChange={(e) => setKeywords(e.target.value)}
              placeholder="ví dụ: bão, lũ, giao thông"
              helperText="Nhập nhiều từ khóa bằng dấu phẩy"
              fullWidth
            />
            <Grid container spacing={1.5}>
              <Grid size={{ xs: 6 }}>
                <TextField
                  size="small"
                  type="number"
                  label="Số tweet tối đa"
                  value={maxItems}
                  onChange={(e) => setMaxItems(e.target.value)}
                  fullWidth
                />
              </Grid>
              <Grid size={{ xs: 6 }}>
                <TextField
                  size="small"
                  label="Ngôn ngữ"
                  value={language}
                  onChange={(e) => setLanguage(e.target.value)}
                  fullWidth
                />
              </Grid>
            </Grid>
            <Button
              variant="contained"
              startIcon={<CloudDownloadIcon />}
              onClick={fetchX}
              disabled={!!busy}
            >
              Kích hoạt thu thập dữ liệu X
            </Button>
          </Stack>
        </Grid>

        <Grid size={{ xs: 12, md: 6 }}>
          <Typography variant="subtitle1" fontWeight="bold" gutterBottom>Backfill topic/geo</Typography>
          <Stack spacing={1.5}>
            <TextField
              size="small"
              type="number"
              label="Giới hạn bài xử lý"
              value={limit}
              onChange={(e) => setLimit(e.target.value)}
              fullWidth
            />
            <Box display="flex" gap={1} flexWrap="wrap">
              <FormControlLabel
                control={<Checkbox checked={geoOnly} onChange={(e) => setGeoOnly(e.target.checked)} />}
                label="Chỉ geo"
              />
              <FormControlLabel
                control={<Checkbox checked={aiOnly} onChange={(e) => setAiOnly(e.target.checked)} />}
                label="Chỉ OpenAI"
              />
            </Box>
            <Stack direction="row" spacing={1} flexWrap="wrap" useFlexGap>
              <Button
                variant="outlined"
                startIcon={<QueryStatsIcon />}
                onClick={() => backfill(true)}
                disabled={!!busy}
              >
                Đếm dữ liệu cần backfill
              </Button>
              <Button
                variant="contained"
                color="warning"
                startIcon={<PlayArrowIcon />}
                onClick={() => backfill(false)}
                disabled={!!busy}
              >
                Chạy backfill topic/geo
              </Button>
            </Stack>
          </Stack>
        </Grid>
      </Grid>

      {busy && (
        <Alert severity="info" sx={{ mt: 2 }}>
          Đang xử lý tác vụ, vui lòng chờ...
        </Alert>
      )}

      {result && (
        <>
          <Divider sx={{ my: 2 }} />
          <Typography variant="subtitle2" fontWeight="bold" gutterBottom>Kết quả tác vụ</Typography>
          <Box
            component="pre"
            sx={{
              m: 0,
              p: 1.5,
              borderRadius: 1,
              bgcolor: 'grey.100',
              overflow: 'auto',
              fontSize: 12,
            }}
          >
            {JSON.stringify(result, null, 2)}
          </Box>
        </>
      )}
    </Paper>
  );
}
