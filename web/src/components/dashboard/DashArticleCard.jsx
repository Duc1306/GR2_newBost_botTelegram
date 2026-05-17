import React, { useState } from 'react';
import {
  Box,
  Typography,
  Chip,
  Button,
  CircularProgress,
  Tooltip,
  Collapse,
} from '@mui/material';
import AutoAwesomeIcon from '@mui/icons-material/AutoAwesome';
import HeadphonesIcon from '@mui/icons-material/Headphones';
import OpenInNewIcon from '@mui/icons-material/OpenInNew';
import ExpandLessIcon from '@mui/icons-material/ExpandLess';
import ExpandMoreIcon from '@mui/icons-material/ExpandMore';
import { API_BASE } from '../../lib/dashApi.js';
import { timeAgo } from '../../lib/helpers.jsx';

const DashArticleCard = React.memo(function DashArticleCard({ article, index, onPlayAudio }) {
  const [audioLoading, setAudioLoading] = useState(false);
  const [audioError, setAudioError] = useState(null);
  const [snippetExpanded, setSnippetExpanded] = useState(false);
  const [isRead, setIsRead] = useState(() => {
    if (!article.url) return false;
    try { return JSON.parse(localStorage.getItem('ch_read_urls') || '[]').includes(article.url); }
    catch { return false; }
  });

  const aiSummary = article.ai_summary && typeof article.ai_summary === 'object' ? article.ai_summary : null;
  const snippet = (article.snippet || '').trim();
  const title = (article.title || '').trim();

  const lead = aiSummary?.lead || '';
  const body = aiSummary?.body || aiSummary?.details || [];
  const keyPoints = aiSummary?.key_points || [];
  const isThin = aiSummary?.thin ?? (body.length === 0 && snippet.length < 130);
  const hasAI = !!(lead);

  const _norm = (s) => s.toLowerCase().replace(/[.,!?:;]/g, '').replace(/\s+/g, ' ').trim();
  const leadSameAsTitle = !!(lead && title && (
    _norm(lead).startsWith(_norm(title).slice(0, 55)) ||
    _norm(title).startsWith(_norm(lead).slice(0, 55))
  ));
  const showLead = hasAI && !leadSameAsTitle;

  const snippetTooShort = snippet.length < 130;
  const snippetSameAsTitle = title && snippet && (
    snippet.toLowerCase().startsWith(title.toLowerCase().slice(0, 40)) ||
    title.toLowerCase().startsWith(snippet.toLowerCase().slice(0, 40))
  );
  const showSnippetFallback = !hasAI && snippet.length > 0 && !snippetSameAsTitle;
  const showBodySnippet = hasAI && isThin && !snippetTooShort && !snippetSameAsTitle && snippet.length > 0;

  const hasContent = showLead || body.length > 0 || keyPoints.length > 0 || showSnippetFallback;

  const audioText = (() => {
    if (!hasAI) return (snippet && !snippetSameAsTitle) ? snippet : title;
    const parts = [];
    if (title) parts.push(title);
    if (lead && !leadSameAsTitle) parts.push(lead);
    body.forEach((d) => parts.push(d));
    if (keyPoints.length > 0) parts.push('Điểm nổi bật: ' + keyPoints.join('. '));
    return parts.join('. ') || title;
  })();

  const handleRead = () => {
    if (!article.url) return;
    setIsRead(true);
    try {
      const prev = JSON.parse(localStorage.getItem('ch_read_urls') || '[]');
      const next = [...new Set([...prev, article.url])];
      localStorage.setItem('ch_read_urls', JSON.stringify(next));
    } catch {}
  };

  const handleAudio = async () => {
    if (!audioText) return;
    setAudioLoading(true);
    setAudioError(null);
    try {
      const res = await fetch(`${API_BASE}/user/channels/tts`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${localStorage.getItem('auth_token')}`,
        },
        body: JSON.stringify({ text: audioText }),
      });
      if (!res.ok) throw new Error((await res.json().catch(() => ({}))).detail || 'Lỗi tạo audio');
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      onPlayAudio({ url, title: article.title || `Bài ${index + 1}` });
    } catch (e) {
      setAudioError(e.message);
    } finally {
      setAudioLoading(false);
    }
  };

  return (
    <Box
      sx={{
        border: '1px solid',
        borderColor: isRead ? '#e5e7eb' : '#bfdbfe',
        borderRadius: 2.5,
        bgcolor: isRead ? '#fafafa' : '#f0f9ff',
        overflow: 'hidden',
        transition: 'border-color 0.2s, background 0.2s',
      }}
    >
      {/* Header */}
      <Box sx={{ px: 2, pt: 1.5, pb: 0.75 }}>
        <Box display="flex" alignItems="flex-start" gap={1}>
          <Typography
            variant="caption"
            sx={{
              minWidth: 22, height: 22, borderRadius: '50%', bgcolor: '#0369a1', color: 'white',
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              fontSize: '0.65rem', fontWeight: 700, flexShrink: 0, mt: '1px',
            }}
          >
            {index + 1}
          </Typography>
          <Box flex={1} minWidth={0}>
            <Typography
              variant="body2"
              fontWeight={700}
              sx={{
                lineHeight: 1.45,
                color: isRead ? 'text.secondary' : 'text.primary',
                display: '-webkit-box',
                WebkitLineClamp: 2,
                WebkitBoxOrient: 'vertical',
                overflow: 'hidden',
              }}
            >
              {article.title || '(Không có tiêu đề)'}
            </Typography>
            <Box display="flex" alignItems="center" gap={0.75} mt={0.35} flexWrap="wrap">
              {article.source && (
                <Typography variant="caption" sx={{ fontSize: '0.65rem', color: '#6b7280', fontWeight: 600 }}>
                  {article.source}
                </Typography>
              )}
              {article.source && article.date && (
                <Typography variant="caption" color="text.disabled" sx={{ fontSize: '0.6rem' }}>·</Typography>
              )}
              {article.date && (
                <Typography variant="caption" sx={{ fontSize: '0.63rem', color: 'text.disabled' }}>
                  {timeAgo(article.date)}
                </Typography>
              )}
              {hasAI && (
                <Chip
                  label="AI tóm tắt"
                  size="small"
                  icon={<AutoAwesomeIcon sx={{ fontSize: '10px !important' }} />}
                  sx={{ height: 16, fontSize: '0.58rem', bgcolor: '#e0f2fe', color: '#0369a1', fontWeight: 600, ml: 0.25 }}
                />
              )}
              {isRead && (
                <Chip label="Đã đọc" size="small" sx={{ height: 16, fontSize: '0.58rem', bgcolor: '#e5e7eb', color: '#9ca3af' }} />
              )}
            </Box>
          </Box>
        </Box>
      </Box>

      {/* AI Summary body */}
      {hasContent && (
        <Box sx={{ px: 2, pb: 0.75 }}>
          {hasAI ? (
            <>
              {showLead && (
                <Typography
                  variant="body2"
                  sx={{
                    lineHeight: 1.75, color: 'text.primary', fontSize: '0.85rem', fontWeight: 500,
                    borderLeft: '2.5px solid #0369a1', pl: 1.25,
                    mb: (body.length > 0 || keyPoints.length > 0) ? 0.75 : 0,
                  }}
                >
                  {lead}
                </Typography>
              )}
              {body.length > 0 && (
                <Box>
                  {body.map((d, i) => (
                    <Typography key={i} variant="body2" sx={{ lineHeight: 1.75, color: 'text.secondary', fontSize: '0.83rem', mb: 0.6 }}>
                      {d}
                    </Typography>
                  ))}
                </Box>
              )}
              {showBodySnippet && (
                <>
                  <Collapse in={snippetExpanded} collapsedSize={60}>
                    <Typography variant="body2" sx={{ lineHeight: 1.75, color: 'text.secondary', fontSize: '0.83rem' }}>
                      {snippet}
                    </Typography>
                  </Collapse>
                  {snippet.length > 250 && (
                    <Button
                      size="small"
                      onClick={() => setSnippetExpanded((v) => !v)}
                      endIcon={snippetExpanded ? <ExpandLessIcon sx={{ fontSize: '13px !important' }} /> : <ExpandMoreIcon sx={{ fontSize: '13px !important' }} />}
                      sx={{ textTransform: 'none', fontSize: '0.7rem', p: 0, mt: 0.25, color: '#0369a1', minWidth: 0 }}
                    >
                      {snippetExpanded ? 'Thu gọn' : 'Xem thêm'}
                    </Button>
                  )}
                </>
              )}
              {keyPoints.length > 0 && (
                <Box sx={{ mt: 0.75, display: 'flex', flexDirection: 'column', gap: 0.4 }}>
                  {keyPoints.map((pt, i) => (
                    <Box key={i} display="flex" alignItems="flex-start" gap={0.75}>
                      <Box sx={{ width: 5, height: 5, borderRadius: '50%', bgcolor: '#0369a1', mt: '7px', flexShrink: 0 }} />
                      <Typography variant="caption" sx={{ lineHeight: 1.65, color: '#374151', fontSize: '0.78rem' }}>{pt}</Typography>
                    </Box>
                  ))}
                </Box>
              )}
            </>
          ) : showSnippetFallback ? (
            <>
              <Collapse in={snippetExpanded} collapsedSize={60}>
                <Typography variant="body2" sx={{ lineHeight: 1.75, color: 'text.secondary', fontSize: '0.83rem' }}>
                  {snippet}
                </Typography>
              </Collapse>
              {snippet.length > 300 && (
                <Button
                  size="small"
                  onClick={() => setSnippetExpanded((v) => !v)}
                  endIcon={snippetExpanded ? <ExpandLessIcon sx={{ fontSize: '13px !important' }} /> : <ExpandMoreIcon sx={{ fontSize: '13px !important' }} />}
                  sx={{ textTransform: 'none', fontSize: '0.7rem', p: 0, mt: 0.25, color: '#0369a1', minWidth: 0 }}
                >
                  {snippetExpanded ? 'Thu gọn' : 'Xem thêm'}
                </Button>
              )}
            </>
          ) : null}
        </Box>
      )}

      {/* Actions */}
      <Box display="flex" alignItems="center" gap={0.5} sx={{ px: 1.5, pb: 1.25, pt: 0.5, flexWrap: 'wrap' }}>
        <Tooltip title={audioError || (audioText ? 'Nghe tóm tắt AI bài này' : 'Chưa có nội dung')}>
          <span>
            <Button
              size="small"
              onClick={handleAudio}
              disabled={audioLoading || !audioText}
              startIcon={
                audioLoading
                  ? <CircularProgress size={11} color="inherit" />
                  : <HeadphonesIcon sx={{ fontSize: '13px !important' }} />
              }
              sx={{
                textTransform: 'none', fontSize: '0.7rem', borderRadius: 2,
                color: audioError ? 'error.main' : '#0369a1',
                border: '1px solid', borderColor: audioError ? 'error.light' : '#bfdbfe',
                bgcolor: 'background.paper', px: 1.25, py: 0.3,
                '&:hover': { bgcolor: 'action.hover' },
              }}
            >
              {audioLoading ? 'Đang tạo…' : 'Nghe tóm tắt'}
            </Button>
          </span>
        </Tooltip>

        {article.url ? (
          <Button
            size="small"
            component="a"
            href={article.url}
            target="_blank"
            rel="noopener noreferrer"
            onClick={handleRead}
            endIcon={<OpenInNewIcon sx={{ fontSize: '11px !important' }} />}
            variant={isRead ? 'text' : 'contained'}
            sx={{
              textTransform: 'none', fontSize: '0.7rem', borderRadius: 2, px: 1.25, py: 0.3, boxShadow: 'none',
              ...(isRead
                ? { color: '#9ca3af' }
                : { bgcolor: '#0369a1', '&:hover': { bgcolor: '#075985' } }),
            }}
          >
            {isRead ? 'Đọc lại' : 'Đọc bài gốc'}
          </Button>
        ) : (
          <Typography variant="caption" color="text.disabled" sx={{ fontSize: '0.65rem' }}>
            Không có link gốc
          </Typography>
        )}
      </Box>
    </Box>
  );
});

export default DashArticleCard;
