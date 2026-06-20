import React, { useState, useEffect, useCallback, useRef } from 'react';
import {
  Box,
  Typography,
  Grid,
  Chip,
  IconButton,
  Tooltip,
  Alert,
  CircularProgress,
  Fade,
} from '@mui/material';
import BoltIcon from '@mui/icons-material/Bolt';
import RefreshIcon from '@mui/icons-material/Refresh';
import TrendingUpIcon from '@mui/icons-material/TrendingUp';
import { fetchHotNewsClusters } from '../../../lib/publicApi.js';
import { timeAgo } from '../../../lib/helpers.jsx';
import HotClusterCard from '../../../components/public/HotClusterCard.jsx';
import HotSummaryDialog from '../../../components/public/HotSummaryDialog.jsx';
import { ClusterSkeleton } from '../../../components/public/Skeletons.jsx';
import AudioPlayer from '../../../components/AudioPlayer.jsx';

export default function HotNewsTab() {
  const [clusters, setClusters] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [hours, setHours] = useState(24);
  const [selectedCluster, setSelectedCluster] = useState(null);
  const [summaryOpen, setSummaryOpen] = useState(false);
  const [audioPlayer, setAudioPlayer] = useState(null);
  const [pendingClusters, setPendingClusters] = useState([]);
  const [freshSlugs, setFreshSlugs] = useState(new Set());
  const [lastRefreshed, setLastRefreshed] = useState(null);
  const currentSlugsRef = useRef(new Set());

  const load = useCallback((h, signal) => {
    setLoading(true);
    setError(null);
    setPendingClusters([]);
    setFreshSlugs(new Set());
    fetchHotNewsClusters(h, signal)
      .then((d) => {
        const fresh = d.clusters || [];
        setClusters(fresh);
        currentSlugsRef.current = new Set(fresh.map((c) => c.slug));
        setLastRefreshed(new Date());
      })
      .catch((e) => {
        if (e?.name !== 'AbortError') setError(e.message);
      })
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    const ac = new AbortController();
    load(hours, ac.signal);
    return () => ac.abort();
  }, [hours, load]);

  useEffect(() => {
    const ac = new AbortController();
    const id = setInterval(() => {
      fetchHotNewsClusters(hours, ac.signal)
        .then((d) => {
          const incoming = d.clusters || [];
          const truly = incoming.filter((c) => !currentSlugsRef.current.has(c.slug));
          setClusters((prev) => prev.map((c) => incoming.find((f) => f.slug === c.slug) || c));
          if (truly.length > 0) {
            setPendingClusters((prev) => {
              const existSlugs = new Set(prev.map((p) => p.slug));
              return [...prev, ...truly.filter((c) => !existSlugs.has(c.slug))];
            });
          }
          setLastRefreshed(new Date());
        })
        .catch(() => {});
    }, 60_000);
    return () => {
      clearInterval(id);
      ac.abort();
    };
  }, [hours]);

  const applyPending = () => {
    const slugs = new Set(pendingClusters.map((c) => c.slug));
    setClusters((prev) => {
      const existSlugs = new Set(prev.map((c) => c.slug));
      const newOnes = pendingClusters.filter((c) => !existSlugs.has(c.slug));
      newOnes.forEach((c) => currentSlugsRef.current.add(c.slug));
      return [...newOnes, ...prev];
    });
    setFreshSlugs((prev) => new Set([...prev, ...slugs]));
    setPendingClusters([]);
  };

  const handleReadSummary = (cluster) => {
    setSelectedCluster(cluster);
    setSummaryOpen(true);
  };

  return (
    <Box>
      <Box
        display="flex"
        alignItems={{ xs: 'flex-start', sm: 'center' }}
        justifyContent="space-between"
        mb={2.5}
        flexWrap="wrap"
        gap={1}
      >
        <Box>
          <Typography
            variant="h6"
            fontWeight={700}
            sx={{ display: 'flex', alignItems: 'center', gap: 0.75, fontSize: { xs: '1rem', sm: '1.25rem' } }}
          >
            <BoltIcon sx={{ color: '#f97316' }} /> Tin nóng theo chủ đề
          </Typography>
          <Typography
            variant="caption"
            color="text.secondary"
            sx={{ display: { xs: 'none', sm: 'block' } }}
          >
            Click "Xem tóm tắt AI" để đọc bản tóm lược được tổng hợp bằng OpenAI
          </Typography>
        </Box>
        <Box display="flex" gap={0.75} alignItems="center" flexWrap="wrap">
          {[24, 48, 72].map((h) => {
            const active = hours === h;
            return (
              <Tooltip
                key={h}
                title={`Xem tin nóng trong ${h} giờ gần nhất`}
                arrow
              >
                <Chip
                  label={`${h}h`}
                  size="small"
                  clickable
                  onClick={() => setHours(h)}
                  color={active ? 'primary' : 'default'}
                  variant={active ? 'filled' : 'outlined'}
                  sx={{
                    fontWeight: active ? 800 : 600,
                    borderColor: active ? 'primary.main' : 'divider',
                    bgcolor: active ? 'primary.main' : 'background.paper',
                    color: active ? 'primary.contrastText' : 'text.primary',
                    transition: 'background-color 160ms ease, border-color 160ms ease, box-shadow 160ms ease, transform 160ms ease',
                    boxShadow: active ? '0 2px 8px rgba(25, 118, 210, 0.24)' : 'none',
                    '&:hover': {
                      bgcolor: active ? 'primary.dark' : 'rgba(25, 118, 210, 0.08)',
                      borderColor: 'primary.main',
                      color: active ? 'primary.contrastText' : 'primary.main',
                      boxShadow: '0 3px 10px rgba(25, 118, 210, 0.18)',
                      transform: 'translateY(-1px)',
                    },
                  }}
                />
              </Tooltip>
            );
          })}
          <Tooltip title="Làm mới">
            <span>
              <IconButton size="small" onClick={() => load(hours)} disabled={loading}>
                <RefreshIcon fontSize="small" />
              </IconButton>
            </span>
          </Tooltip>
          {lastRefreshed && (
            <Typography variant="caption" color="text.disabled" sx={{ flexShrink: 0 }}>
              · {timeAgo(lastRefreshed)}
            </Typography>
          )}
        </Box>
      </Box>

      {pendingClusters.length > 0 && (
        <Box
          onClick={applyPending}
          sx={{
            cursor: 'pointer',
            mb: 2,
            p: 1.25,
            bgcolor: '#f97316',
            color: 'white',
            borderRadius: 2,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            gap: 1,
            fontWeight: 700,
            fontSize: '0.875rem',
            userSelect: 'none',
            '&:hover': { bgcolor: '#ea580c' },
            '@keyframes pulseBar': { '0%,100%': { opacity: 1 }, '50%': { opacity: 0.82 } },
            animation: 'pulseBar 2s infinite',
          }}
        >
          <BoltIcon sx={{ fontSize: 18 }} />
          {pendingClusters.length} chủ đề mới — Nhấn để hiển thị
        </Box>
      )}

      {error && (
        <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError(null)}>
          {error}
        </Alert>
      )}

      {loading ? (
        <Grid container spacing={2}>
          {[1, 2, 3, 4, 5, 6].map((i) => (
            <Grid size={{ xs: 12, sm: 6, md: 4 }} key={i}>
              <ClusterSkeleton />
            </Grid>
          ))}
        </Grid>
      ) : clusters.length === 0 ? (
        <Box textAlign="center" py={8}>
          <TrendingUpIcon sx={{ fontSize: 64, color: 'divider', mb: 2 }} />
          <Typography color="text.secondary">Chưa có tin nóng trong {hours} giờ qua.</Typography>
          <Typography variant="caption" color="text.disabled">
            Hãy chạy fetch để thu thập dữ liệu mới.
          </Typography>
        </Box>
      ) : (
        <Fade in>
          <Grid container spacing={2}>
            {clusters.map((cluster) => (
              <Grid size={{ xs: 12, sm: 6, md: 4 }} key={cluster.slug}>
                <HotClusterCard
                  cluster={cluster}
                  onReadSummary={handleReadSummary}
                  isNew={freshSlugs.has(cluster.slug)}
                />
              </Grid>
            ))}
          </Grid>
        </Fade>
      )}

      <HotSummaryDialog
        cluster={selectedCluster}
        open={summaryOpen}
        onClose={() => setSummaryOpen(false)}
        hours={hours}
        onPlayAudio={(p) => setAudioPlayer(p)}
      />

      {audioPlayer && (
        <AudioPlayer
          audioUrl={audioPlayer.url}
          title={audioPlayer.title}
          onClose={() => {
            URL.revokeObjectURL(audioPlayer.url);
            setAudioPlayer(null);
          }}
        />
      )}
    </Box>
  );
}
