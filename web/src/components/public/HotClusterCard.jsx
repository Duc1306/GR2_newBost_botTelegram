import React from 'react';
import { Card, CardContent, CardActions, Box, Typography, Chip, Button } from '@mui/material';
import WhatshotIcon from '@mui/icons-material/Whatshot';
import AutoAwesomeIcon from '@mui/icons-material/AutoAwesome';
import LinkIcon from '@mui/icons-material/Link';
import { timeAgo } from '../../lib/helpers.jsx';

const HotClusterCard = React.memo(function HotClusterCard({ cluster, onReadSummary, isNew }) {
  return (
    <Card
      elevation={0}
      sx={{
        borderRadius: 2.5,
        border: '2px solid',
        borderColor: cluster.color || '#e5e7eb',
        transition: 'all 0.2s',
        height: '100%',
        display: 'flex',
        flexDirection: 'column',
        '&:hover': { boxShadow: `0 8px 24px ${cluster.color}33`, transform: 'translateY(-3px)' },
      }}
    >
      <Box sx={{ height: 5, bgcolor: cluster.color || '#6b7280', borderRadius: '10px 10px 0 0' }} />

      <CardContent sx={{ flex: 1, pt: 1.5, pb: 0 }}>
        <Box display="flex" alignItems="center" gap={0.75} mb={0.75} flexWrap="wrap">
          <WhatshotIcon sx={{ fontSize: 18, color: cluster.color }} />
          <Typography variant="subtitle2" fontWeight={700} sx={{ lineHeight: 1.3, color: cluster.color }}>
            {cluster.name}
          </Typography>
          {isNew && (
            <Chip
              label="Mới"
              size="small"
              sx={{ height: 18, fontSize: '0.6rem', fontWeight: 800, bgcolor: '#ef4444', color: 'white', px: 0.5 }}
            />
          )}
        </Box>

        <Typography
          variant="body2"
          fontWeight={500}
          mb={1}
          sx={{
            display: '-webkit-box',
            WebkitLineClamp: 3,
            WebkitBoxOrient: 'vertical',
            overflow: 'hidden',
            lineHeight: 1.55,
            color: 'text.primary',
          }}
        >
          {cluster.headline}
        </Typography>

        <Box display="flex" alignItems="center" gap={0.75} flexWrap="wrap">
          <Chip
            label={`${cluster.post_count} bài`}
            size="small"
            sx={{
              fontSize: '0.68rem',
              height: 20,
              bgcolor: `${cluster.color}22`,
              color: cluster.color,
              fontWeight: 600,
            }}
          />
          {cluster.posts_with_links > 0 && (
            <Chip
              icon={<LinkIcon sx={{ fontSize: '11px !important' }} />}
              label={`${cluster.posts_with_links} link`}
              size="small"
              sx={{ fontSize: '0.68rem', height: 20, bgcolor: '#dcfce7', color: '#166534', fontWeight: 600 }}
            />
          )}
          {cluster.source === 'ai_discovered' && (
            <Chip
              label="AI phát hiện"
              size="small"
              sx={{ fontSize: '0.65rem', height: 20, bgcolor: '#fef3c7', color: '#92400e', fontWeight: 600 }}
            />
          )}
          <Typography variant="caption" color="text.disabled">
            {cluster.latest_at ? `Cập nhật ${timeAgo(cluster.latest_at)}` : ''}
          </Typography>
        </Box>
      </CardContent>

      <CardActions sx={{ px: 2, pt: 1, pb: 1.5 }}>
        <Button
          size="small"
          variant="outlined"
          startIcon={<AutoAwesomeIcon sx={{ fontSize: '14px !important' }} />}
          onClick={() => onReadSummary(cluster)}
          sx={{
            textTransform: 'none',
            fontSize: '0.78rem',
            borderRadius: 2,
            borderColor: cluster.color,
            color: cluster.color,
            '&:hover': { bgcolor: `${cluster.color}18`, borderColor: cluster.color },
          }}
        >
          Xem tóm tắt AI
        </Button>
      </CardActions>
    </Card>
  );
});

export default HotClusterCard;
