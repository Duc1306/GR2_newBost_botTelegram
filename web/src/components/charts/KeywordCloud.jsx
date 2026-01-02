import React from 'react';
import { Box, Typography, Paper } from '@mui/material';
import ReactWordcloud from 'react-wordcloud';

const options = {
  rotations: 2,
  rotationAngles: [0, 90],
  fontSizes: [16, 60],
  padding: 2,
  enableTooltip: true,
  deterministic: true,
  fontFamily: 'Roboto',
  fontWeight: 'bold',
};

export default function KeywordCloud({ keywords, title, height = 400 }) {
  if (!keywords || keywords.length === 0) {
    return (
      <Paper sx={{ p: 2, height }}>
        <Typography variant="h6" gutterBottom>{title}</Typography>
        <Box display="flex" alignItems="center" justifyContent="center" height={height - 60}>
          <Typography color="text.secondary">No keywords available</Typography>
        </Box>
      </Paper>
    );
  }

  // Transform data to wordcloud format
  const words = keywords.map(k => ({
    text: k.keyword || k.text,
    value: k.count || k.value || 1,
  }));

  return (
    <Paper sx={{ p: 2 }}>
      {title && <Typography variant="h6" gutterBottom>{title}</Typography>}
      <Box sx={{ height }}>
        <ReactWordcloud 
          words={words} 
          options={options}
        />
      </Box>
    </Paper>
  );
}
