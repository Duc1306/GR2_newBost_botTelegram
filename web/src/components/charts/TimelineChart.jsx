import React from 'react';
import { Box, Typography, Paper } from '@mui/material';
import { AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';

const CustomTooltip = ({ active, payload, label }) => {
  if (active && payload && payload.length) {
    // Get original date from payload data
    const originalDate = payload[0].payload.date;
    const date = new Date(originalDate);
    const formattedDate = date.toLocaleDateString('vi-VN', { day: '2-digit', month: 'short', year: 'numeric' });
    return (
      <Paper sx={{ p: 1.5, bgcolor: 'rgba(255, 255, 255, 0.95)' }}>
        <Typography variant="body2" fontWeight="bold">{formattedDate}</Typography>
        <Typography variant="body2" color="primary">
          {payload[0].value} bài viết
        </Typography>
      </Paper>
    );
  }
  return null;
};

export default function TimelineChart({ data, title, dataKeys = [], height = 400 }) {
  if (!data || data.length === 0) {
    return (
      <Paper sx={{ p: 3, height }}>
        <Typography variant="h6" gutterBottom fontWeight="bold">{title}</Typography>
        <Box display="flex" alignItems="center" justifyContent="center" height={height - 60}>
          <Typography color="text.secondary">Không có dữ liệu</Typography>
        </Box>
      </Paper>
    );
  }

  // Format dates for display - use original date string for proper display
  const formattedData = data.map(item => {
    const date = new Date(item.date);
    return {
      ...item,
      displayDate: `${date.getDate()}/${date.getMonth() + 1}`
    };
  });

  // Show only every 5th label to avoid crowding
  const interval = Math.max(0, Math.floor(formattedData.length / 5));

  return (
    <Paper sx={{ 
      p: 3, 
      borderRadius: 2,
      boxShadow: '0 2px 8px rgba(0,0,0,0.1)',
      '&:hover': { boxShadow: '0 4px 16px rgba(0,0,0,0.15)' }
    }}>
      {title && (
        <Typography variant="h6" gutterBottom fontWeight="bold" color="primary">
          {title}
        </Typography>
      )}
      <ResponsiveContainer width="100%" height={height}>
        <AreaChart 
          data={formattedData} 
          margin={{ top: 10, right: 10, left: 0, bottom: 5 }}
        >
          <defs>
            <linearGradient id="colorPosts" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor="#1976d2" stopOpacity={0.3}/>
              <stop offset="95%" stopColor="#1976d2" stopOpacity={0}/>
            </linearGradient>
          </defs>
          <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
          <XAxis 
            dataKey="displayDate"
            tick={{ fontSize: 11, fill: '#666' }}
            tickLine={false}
            interval={interval}
            height={40}
          />
          <YAxis 
            tick={{ fontSize: 12, fill: '#666' }}
            tickLine={false}
            axisLine={false}
          />
          <Tooltip content={<CustomTooltip />} />
          <Area
            type="monotone"
            dataKey={dataKeys[0] || 'count'}
            stroke="#1976d2"
            strokeWidth={3}
            fill="url(#colorPosts)"
            dot={false}
            activeDot={{ r: 6, fill: '#1976d2' }}
          />
        </AreaChart>
      </ResponsiveContainer>
    </Paper>
  );
}
