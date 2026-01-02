import React from 'react';
import { Box, Typography, Paper } from '@mui/material';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Cell } from 'recharts';
import { chartColorPalette } from '../../theme/colors.jsx';

export default function KeywordsBarChart({ data, title, height = 400 }) {
  console.log('KeywordsBarChart received data:', data);
  
  if (!data || data.length === 0) {
    return (
      <Paper sx={{ p: 3, height }}>
        <Typography variant="h6" gutterBottom fontWeight="bold">{title}</Typography>
        <Box display="flex" alignItems="center" justifyContent="center" height={height - 80}>
          <Typography color="text.secondary">Không có dữ liệu</Typography>
        </Box>
      </Paper>
    );
  }

  return (
    <Paper sx={{ 
      p: 3,
      height: height,
      width: '100%',
      borderRadius: 2,
      boxShadow: '0 2px 8px rgba(0,0,0,0.1)',
      '&:hover': { boxShadow: '0 4px 16px rgba(0,0,0,0.15)' }
    }}>
      {title && (
        <Typography variant="h6" gutterBottom fontWeight="bold" color="primary" sx={{ mb: 2 }}>
          {title}
        </Typography>
      )}
      <Box sx={{ width: '100%', height: height - 100 }}>
        <ResponsiveContainer width="100%" height="100%" minWidth={300}>
          <BarChart 
            data={data} 
            layout="vertical"
            margin={{ top: 5, right: 20, left: 100, bottom: 5 }}
          >
            <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
            <XAxis 
              type="number" 
              tick={{ fontSize: 11, fill: '#666' }}
              tickLine={false}
              axisLine={false}
            />
            <YAxis 
              dataKey="keyword" 
              type="category" 
              tick={{ fontSize: 12, fill: '#333' }}
              tickLine={false}
              axisLine={false}
              width={90}
            />
            <Tooltip 
              cursor={{ fill: 'rgba(25, 118, 210, 0.1)' }}
              contentStyle={{ 
                borderRadius: 8, 
                border: 'none',
                boxShadow: '0 2px 8px rgba(0,0,0,0.15)' 
              }}
            />
            <Bar 
              dataKey="count" 
              fill="#1976d2"
              radius={[0, 6, 6, 0]}
            >
              {data.map((entry, index) => (
                <Cell 
                  key={`cell-${index}`} 
                  fill={chartColorPalette[index % chartColorPalette.length]} 
                />
              ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
      </Box>
    </Paper>
  );
}
