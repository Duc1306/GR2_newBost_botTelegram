import React from 'react';
import { Box } from '@mui/material';

export default function NewsTicker({ items }) {
  const texts = items.slice(0, 8).filter(Boolean);
  if (!texts.length) return null;
  const ticker = texts.join('   ·   ');

  return (
    <Box
      sx={{
        bgcolor: '#ef4444',
        color: 'white',
        py: 0.6,
        overflow: 'hidden',
        display: 'flex',
        alignItems: 'center',
      }}
    >
      <Box
        sx={{
          px: 2,
          fontWeight: 700,
          fontSize: '0.75rem',
          letterSpacing: 1,
          whiteSpace: 'nowrap',
          flexShrink: 0,
          bgcolor: '#b91c1c',
          alignSelf: 'stretch',
          display: 'flex',
          alignItems: 'center',
        }}
      >
        BREAKING
      </Box>
      <Box
        sx={{
          overflow: 'hidden',
          flex: 1,
          maskImage: 'linear-gradient(to right, transparent 0%, black 4%, black 96%, transparent 100%)',
        }}
      >
        <Box
          component="marquee"
          scrollamount="4"
          sx={{ fontSize: '0.8rem', whiteSpace: 'nowrap', display: 'block' }}
        >
          {ticker}
        </Box>
      </Box>
    </Box>
  );
}
