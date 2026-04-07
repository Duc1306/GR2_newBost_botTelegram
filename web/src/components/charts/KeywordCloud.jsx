import React, { useEffect, useRef, useState } from 'react';
import { Box, Typography, Paper } from '@mui/material';
import cloud from 'd3-cloud';

const COLORS = ['#1976d2', '#388e3c', '#f57c00', '#7b1fa2', '#c62828', '#00838f', '#4527a0'];

export default function KeywordCloud({ keywords, title, height = 400 }) {
  const containerRef = useRef(null);
  const [layoutWords, setLayoutWords] = useState([]);
  const [width, setWidth] = useState(600);

  useEffect(() => {
    if (containerRef.current) {
      setWidth(containerRef.current.offsetWidth || 600);
    }
  }, []);

  useEffect(() => {
    if (!keywords || keywords.length === 0) return;

    const input = keywords.map(k => ({
      text: k.keyword || k.text,
      value: k.count || k.value || 1,
    }));

    const maxVal = Math.max(...input.map(w => w.value));
    const minVal = Math.min(...input.map(w => w.value));
    const scale = v =>
      maxVal === minVal ? 30 : 16 + ((v - minVal) / (maxVal - minVal)) * 44;

    cloud()
      .size([width, height])
      .words(input.map(w => ({ ...w, size: scale(w.value) })))
      .padding(2)
      .rotate(() => (Math.random() > 0.5 ? 0 : 90))
      .font('Roboto, sans-serif')
      .fontWeight('bold')
      .fontSize(d => d.size)
      .on('end', setLayoutWords)
      .start();
  }, [keywords, width, height]);

  if (!keywords || keywords.length === 0) {
    return (
      <Paper sx={{ p: 2, height }}>
        {title && <Typography variant="h6" gutterBottom>{title}</Typography>}
        <Box display="flex" alignItems="center" justifyContent="center" height={height - 60}>
          <Typography color="text.secondary">No keywords available</Typography>
        </Box>
      </Paper>
    );
  }

  return (
    <Paper sx={{ p: 2 }}>
      {title && <Typography variant="h6" gutterBottom>{title}</Typography>}
      <Box ref={containerRef} sx={{ height, overflow: 'hidden' }}>
        <svg width="100%" height={height} style={{ display: 'block' }}>
          <g transform={`translate(${width / 2},${height / 2})`}>
            {layoutWords.map((word, i) => (
              <text
                key={word.text}
                style={{
                  fontSize: word.size,
                  fontFamily: word.font,
                  fontWeight: 'bold',
                  fill: COLORS[i % COLORS.length],
                  cursor: 'default',
                }}
                textAnchor="middle"
                transform={`translate(${word.x},${word.y}) rotate(${word.rotate})`}
              >
                {word.text}
              </text>
            ))}
          </g>
        </svg>
      </Box>
    </Paper>
  );
}
