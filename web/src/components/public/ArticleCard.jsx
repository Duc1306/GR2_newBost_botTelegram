import React, { useState } from 'react';
import {
  Card,
  CardContent,
  CardActions,
  Box,
  Typography,
  Chip,
  Button,
  CircularProgress,
} from '@mui/material';
import FiberManualRecordIcon from '@mui/icons-material/FiberManualRecord';
import AutoAwesomeIcon from '@mui/icons-material/AutoAwesome';
import HeadphonesIcon from '@mui/icons-material/Headphones';
import OpenInNewIcon from '@mui/icons-material/OpenInNew';
import { timeAgo, formatDateTime, highlightText } from '../../lib/helpers.jsx';

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000';

const ArticleCard = React.memo(function ArticleCard({ post, selectedTopic, onPlayAudio, searchQuery = '' }) {
  const externalLink = post.links?.find((l) => !l.includes('t.me') && l.startsWith('http'));
  const title = post.full_article?.title || null;
  const primaryTopic =
    selectedTopic && post.topics?.includes(selectedTopic) ? selectedTopic : post.topics?.[0];

  const [aiSummary, setAiSummary] = useState(null);
  const [loadingSummary, setLoadingSummary] = useState(false);
  const [loadingAudio, setLoadingAudio] = useState(false);

  const handleSummarize = async () => {
    if (loadingSummary || !post.id) return;
    setLoadingSummary(true);
    try {
      const res = await fetch(
        `${API_BASE}/public/posts/${encodeURIComponent(post.id)}/summarize`,
        { method: 'POST', headers: { 'Content-Type': 'application/json' } }
      );
      const data = await res.json();
      setAiSummary(res.ok ? data : {});
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
      text = (post.text || '').slice(0, 1500);
    }
    try {
      const res = await fetch(`${API_BASE}/public/tts`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text: text.slice(0, 2000) }),
      });
      if (!res.ok) throw new Error('TTS failed');
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      onPlayAudio({ url, title: title || post.text?.slice(0, 80) || 'Bài viết' });
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
        mb: 2,
        borderRadius: 2,
        border: '1px solid',
        borderColor: 'divider',
        transition: 'box-shadow 0.18s, transform 0.18s',
        '&:hover': { boxShadow: '0 6px 20px rgba(0,0,0,0.10)', transform: 'translateY(-2px)' },
      }}
    >
      <CardContent sx={{ pb: externalLink ? 0 : 1.5 }}>
        <Box display="flex" alignItems="center" gap={1} mb={0.75} flexWrap="wrap">
          {primaryTopic && (
            <Chip
              label={primaryTopic}
              size="small"
              sx={{ fontSize: '0.68rem', height: 20, bgcolor: '#fef3c7', color: '#92400e', fontWeight: 600 }}
            />
          )}
          <Typography variant="caption" color="text.secondary" sx={{ display: 'flex', alignItems: 'center', gap: 0.4 }}>
            <FiberManualRecordIcon sx={{ fontSize: 8, color: '#2563eb' }} />
            {post.source}
          </Typography>
          <Typography variant="caption" color="text.disabled" title={formatDateTime(post.created_at)}>
            · {timeAgo(post.created_at)}
          </Typography>
        </Box>

        {title && (
          <Typography
            variant="subtitle1"
            fontWeight={700}
            mb={0.5}
            sx={{
              display: '-webkit-box',
              WebkitLineClamp: 2,
              WebkitBoxOrient: 'vertical',
              overflow: 'hidden',
              lineHeight: 1.4,
              fontSize: '0.975rem',
            }}
          >
            {searchQuery ? highlightText(title, searchQuery) : title}
          </Typography>
        )}

        <Typography
          variant="body2"
          color="text.secondary"
          sx={{
            display: '-webkit-box',
            WebkitLineClamp: title ? 3 : 5,
            WebkitBoxOrient: 'vertical',
            overflow: 'hidden',
            lineHeight: 1.65,
          }}
        >
          {searchQuery ? highlightText(post.text, searchQuery) : post.text}
        </Typography>

        {hasSummary && (
          <Box sx={{ bgcolor: '#f0f9ff', borderRadius: 1.5, p: 1.25, mt: 1 }}>
            {(aiSummary.sentiment || aiSummary.risk_score > 0) && (
              <Box display="flex" gap={0.75} mb={0.75} flexWrap="wrap">
                {aiSummary.sentiment &&
                  (() => {
                    const s = aiSummary.sentiment;
                    const map = {
                      positive: { label: '😊 Tích cực', color: '#166534', bg: '#dcfce7' },
                      negative: { label: '⚠️ Tiêu cực', color: '#991b1b', bg: '#fee2e2' },
                      mixed: { label: '🔄 Hỗn hợp', color: '#92400e', bg: '#fef3c7' },
                      neutral: { label: '➖ Trung lập', color: '#374151', bg: '#f3f4f6' },
                    };
                    const style = map[s] || map.neutral;
                    return (
                      <Box
                        component="span"
                        sx={{
                          fontSize: '0.68rem',
                          fontWeight: 600,
                          px: 0.75,
                          py: 0.2,
                          borderRadius: 1,
                          bgcolor: style.bg,
                          color: style.color,
                        }}
                      >
                        {style.label}
                      </Box>
                    );
                  })()}
                {aiSummary.risk_score >= 7 && (
                  <Box
                    component="span"
                    sx={{
                      fontSize: '0.68rem',
                      fontWeight: 600,
                      px: 0.75,
                      py: 0.2,
                      borderRadius: 1,
                      bgcolor: '#fee2e2',
                      color: '#991b1b',
                    }}
                  >
                    🔴 Rủi ro cao {aiSummary.risk_score}/10
                  </Box>
                )}
              </Box>
            )}
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
            {aiSummary.conclusion && (
              <Typography
                variant="caption"
                sx={{
                  display: 'block',
                  lineHeight: 1.6,
                  mt: 0.5,
                  fontStyle: 'italic',
                  color: '#0369a1',
                  opacity: 0.8,
                }}
              >
                {aiSummary.conclusion}
              </Typography>
            )}
          </Box>
        )}
      </CardContent>

      <CardActions sx={{ px: 2, pt: 0.5, pb: 1.5, gap: 0.5, flexWrap: 'wrap' }}>
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
            fontSize: '0.75rem',
            borderRadius: 2,
            px: 1,
            py: 0.3,
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
              fontSize: '0.75rem',
              borderRadius: 2,
              px: 1,
              py: 0.3,
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
            color="primary"
            endIcon={<OpenInNewIcon fontSize="small" />}
            href={externalLink}
            target="_blank"
            rel="noopener noreferrer"
            sx={{
              textTransform: 'none',
              fontSize: '0.8rem',
              borderRadius: 2,
              px: 2,
              py: 0.4,
              boxShadow: 'none',
            }}
          >
            Đọc bài gốc
          </Button>
        )}
      </CardActions>
    </Card>
  );
});

export default ArticleCard;
