import React from 'react';
import { Card, CardContent, Typography, Box } from '@mui/material';
import TrendingUpIcon from '@mui/icons-material/TrendingUp';
import TrendingDownIcon from '@mui/icons-material/TrendingDown';
import TrendingFlatIcon from '@mui/icons-material/TrendingFlat';
import { getTrendColor } from '../../theme/colors.jsx';

export default function StatCard({ title, value, subtitle, trend, icon: Icon }) {
  const getTrendIcon = () => {
    if (!trend) return null;
    if (trend > 5) return <TrendingUpIcon sx={{ color: getTrendColor(trend) }} />;
    if (trend < -5) return <TrendingDownIcon sx={{ color: getTrendColor(trend) }} />;
    return <TrendingFlatIcon sx={{ color: getTrendColor(trend) }} />;
  };

  const getTrendText = () => {
    if (!trend) return null;
    const sign = trend > 0 ? '+' : '';
    return `${sign}${trend.toFixed(1)}%`;
  };

  return (
    <Card sx={{ height: '100%' }}>
      <CardContent>
        <Box display="flex" justifyContent="space-between" alignItems="flex-start">
          <Box>
            <Typography color="text.secondary" variant="body2" gutterBottom>
              {title}
            </Typography>
            <Typography variant="h4" component="div" fontWeight="bold">
              {typeof value === 'number' ? value.toLocaleString() : value}
            </Typography>
            {subtitle && (
              <Typography variant="body2" color="text.secondary" mt={1}>
                {subtitle}
              </Typography>
            )}
            {trend !== undefined && (
              <Box display="flex" alignItems="center" mt={1} gap={0.5}>
                {getTrendIcon()}
                <Typography 
                  variant="body2" 
                  fontWeight="bold"
                  sx={{ color: getTrendColor(trend) }}
                >
                  {getTrendText()}
                </Typography>
              </Box>
            )}
          </Box>
          {Icon && (
            <Box
              sx={{
                backgroundColor: 'primary.light',
                borderRadius: 2,
                p: 1,
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
              }}
            >
              <Icon sx={{ fontSize: 32, color: 'primary.main' }} />
            </Box>
          )}
        </Box>
      </CardContent>
    </Card>
  );
}
