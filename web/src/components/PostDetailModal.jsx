import React from 'react';
import { 
  Dialog, 
  DialogTitle, 
  DialogContent, 
  DialogActions,
  Button,
  Chip,
  Box,
  Typography,
  IconButton,
  Divider,
  Link,
  Tooltip,
} from '@mui/material';
import CloseIcon from '@mui/icons-material/Close';
import OpenInNewIcon from '@mui/icons-material/OpenInNew';
import LinkIcon from '@mui/icons-material/Link';
import ImageIcon from '@mui/icons-material/Image';
import InfoOutlinedIcon from '@mui/icons-material/InfoOutlined';
import { formatDistanceToNow } from 'date-fns';
import { vi } from 'date-fns/locale';
import { getTopicColor } from '../theme/colors';

export default function PostDetailModal({ post, open, onClose }) {
  if (!post) return null;

  let timeAgo = 'Unknown date';
  let displayDate = 'Unknown date';
  
  try {
    if (post.created_at) {
      const date = new Date(post.created_at);
      timeAgo = formatDistanceToNow(date, {
        addSuffix: true,
        locale: vi,
      });
      displayDate = `${date.getDate().toString().padStart(2, '0')}/${(date.getMonth() + 1).toString().padStart(2, '0')}/${date.getFullYear()} ${date.getHours().toString().padStart(2, '0')}:${date.getMinutes().toString().padStart(2, '0')}`;
    }
  } catch (error) {
    console.error('Error formatting date:', error, post.created_at);
  }

  // Lấy nội dung đầy đủ (ưu tiên full_article nếu có)
  const fullContent = post.full_article?.content || post.text;
  const hasExternalLink = post.links && post.links.length > 0 && !post.links[0].includes('t.me');

  // Build a lookup map: topic → prediction info for Explainable AI tooltip
  const predictionMap = {};
  if (post.topic_predictions && post.topic_predictions.length > 0) {
    for (const pred of post.topic_predictions) {
      if (pred.topic) predictionMap[pred.topic] = pred;
    }
  }

  const METHOD_LABELS = {
    ml: 'Mô hình ML (SVM/TF-IDF)',
    keyword: 'Quy tắc từ khóa',
    ai: 'OpenAI GPT',
    openai: 'OpenAI GPT',
    hybrid: 'Kết hợp ML + Từ khóa',
  };

  const buildTooltipContent = (topic) => {
    const pred = predictionMap[topic];
    const lines = [];
    if (pred) {
      const method = METHOD_LABELS[pred.method] || pred.method || 'Tự động';
      const confidence = pred.confidence != null
        ? `${(pred.confidence * 100).toFixed(1)}%`
        : null;
      lines.push(`Phương pháp: ${method}`);
      if (confidence) lines.push(`Độ tin cậy: ${confidence}`);
    }
    if (post.source) lines.push(`Nguồn kênh: @${post.source}`);
    return lines.join('\n') || 'Phân loại tự động';
  };

  return (
    <Dialog 
      open={open} 
      onClose={onClose}
      maxWidth="md"
      fullWidth
      scroll="paper"
    >
      {/* Header */}
      <DialogTitle sx={{ 
        display: 'flex', 
        justifyContent: 'space-between', 
        alignItems: 'flex-start',
        pb: 2
      }}>
        <Box flex={1}>
          <Box display="flex" alignItems="center" gap={1} mb={1}>
            {/* Topics */}
            {post.topics && post.topics.length > 0 && (
              <Box display="flex" gap={0.5} flexWrap="wrap">
                {post.topics.slice(0, 3).map((topic, idx) => (
                  <Tooltip
                    key={idx}
                    title={
                      <Box sx={{ whiteSpace: 'pre-line', fontSize: '0.75rem', lineHeight: 1.6 }}>
                        <Typography variant="caption" fontWeight="bold" display="block" mb={0.5}>
                          🤖 Giải thích phân loại
                        </Typography>
                        {buildTooltipContent(topic)}
                      </Box>
                    }
                    arrow
                    placement="bottom-start"
                  >
                    <Chip
                      label={
                        <Box display="flex" alignItems="center" gap={0.5}>
                          #{topic}
                          <InfoOutlinedIcon sx={{ fontSize: '0.7rem', opacity: 0.8 }} />
                        </Box>
                      }
                      size="small"
                      sx={{
                        bgcolor: getTopicColor(topic),
                        color: 'white',
                        fontWeight: 500,
                        fontSize: '0.75rem',
                        cursor: 'help',
                      }}
                    />
                  </Tooltip>
                ))}
              </Box>
            )}
          </Box>
          
          {/* Metadata */}
          <Typography variant="caption" color="text.secondary" display="block">
            📡 {post.source}
            {post.author && ` • @${post.author}`}
            {` • ${displayDate}`}
          </Typography>
        </Box>
        
        <IconButton
          onClick={onClose}
          sx={{ ml: 1 }}
          size="small"
        >
          <CloseIcon />
        </IconButton>
      </DialogTitle>

      {/* Content */}
      <DialogContent dividers>
        {/* Main Text */}
        <Typography 
          variant="body1" 
          sx={{ 
            mb: 2,
            lineHeight: 1.8,
            whiteSpace: 'pre-wrap',
            wordBreak: 'break-word'
          }}
        >
          {fullContent}
        </Typography>

        {/* Full Article Info */}
        {post.full_article && (
          <Box sx={{ 
            mt: 2, 
            p: 2, 
            bgcolor: 'grey.50', 
            borderRadius: 1,
            borderLeft: '4px solid',
            borderColor: 'primary.main'
          }}>
            {post.full_article.title && (
              <Typography variant="subtitle2" fontWeight="bold" gutterBottom>
                📰 {post.full_article.title}
              </Typography>
            )}
            {post.full_article.author && (
              <Typography variant="caption" display="block" color="text.secondary">
                ✍️ {post.full_article.author}
              </Typography>
            )}
            {post.full_article.published_date && (
              <Typography variant="caption" display="block" color="text.secondary">
                📅 {new Date(post.full_article.published_date).toLocaleDateString('vi-VN')}
              </Typography>
            )}
          </Box>
        )}

        {/* Media */}
        {post.media && post.media.length > 0 && (
          <Box sx={{ mt: 2 }}>
            <Typography variant="subtitle2" gutterBottom display="flex" alignItems="center" gap={0.5}>
              <ImageIcon fontSize="small" />
              Media ({post.media.length})
            </Typography>
            <Box display="flex" gap={1} flexWrap="wrap">
              {post.media.map((media, idx) => (
                <Chip
                  key={idx}
                  label={media.type}
                  size="small"
                  variant="outlined"
                />
              ))}
            </Box>
          </Box>
        )}

        {/* Prediction Info */}
        {post.topic_predictions && post.topic_predictions.length > 0 && (
          <Box sx={{ mt: 2 }}>
            <Divider sx={{ mb: 1 }} />
            <Typography variant="caption" color="text.secondary" display="block" gutterBottom>
              🤖 Phân loại tự động
            </Typography>
            <Box display="flex" gap={1} flexWrap="wrap">
              {post.topic_predictions.slice(0, 3).map((pred, idx) => (
                <Chip
                  key={idx}
                  label={`${pred.topic} (${(pred.confidence * 100).toFixed(0)}%)`}
                  size="small"
                  variant="outlined"
                  sx={{ fontSize: '0.7rem' }}
                />
              ))}
            </Box>
          </Box>
        )}
      </DialogContent>

      {/* Actions */}
      <DialogActions sx={{ justifyContent: 'space-between', px: 3, py: 2 }}>
        {/* Links */}
        <Box display="flex" gap={1}>
          {hasExternalLink && (
            <Button
              startIcon={<OpenInNewIcon />}
              variant="contained"
              size="small"
              href={post.links[0]}
              target="_blank"
              rel="noopener noreferrer"
            >
              Đọc bài gốc
            </Button>
          )}
          {post.links && post.links.length > 1 && (
            <Button
              startIcon={<LinkIcon />}
              variant="outlined"
              size="small"
              onClick={() => {
                post.links.forEach(link => window.open(link, '_blank'));
              }}
            >
              {post.links.length} links
            </Button>
          )}
        </Box>

        <Button onClick={onClose} variant="text">
          Đóng
        </Button>
      </DialogActions>
    </Dialog>
  );
}
