import React, { useState } from 'react';
import { Box, Typography, Paper, Chip } from '@mui/material';
import { PieChart, Pie, Cell, ResponsiveContainer, Tooltip } from 'recharts';
import { getTopicColor } from '../../theme/colors.jsx';

// ── Dark glass tooltip ──────────────────────────────────────────────────────
const CustomTooltip = ({ active, payload }) => {
  if (!active || !payload?.length) return null;
  const { name, value, percent } = payload[0];
  const color = getTopicColor(name);
  return (
    <Box
      sx={{
        bgcolor: 'rgba(15,23,42,0.92)',
        backdropFilter: 'blur(8px)',
        color: '#f1f5f9',
        px: 2,
        py: 1.5,
        borderRadius: 2,
        border: `1px solid ${color}50`,
        boxShadow: `0 8px 32px rgba(0,0,0,0.3), 0 0 0 1px ${color}30`,
        minWidth: 160,
      }}
    >
      <Box display="flex" alignItems="center" gap={1} mb={0.5}>
        <Box sx={{ width: 8, height: 8, borderRadius: '50%', bgcolor: color, flexShrink: 0 }} />
        <Typography sx={{ fontSize: '0.8rem', fontWeight: 700, color: '#f1f5f9' }}>
          {name}
        </Typography>
      </Box>
      <Typography sx={{ fontSize: '1rem', fontWeight: 800, color }}>
        {value.toLocaleString()}
      </Typography>
      <Typography sx={{ fontSize: '0.72rem', color: '#94a3b8', mt: 0.25 }}>
        {(percent * 100).toFixed(1)}% tổng số bài
      </Typography>
    </Box>
  );
};

// ── Legend item ─────────────────────────────────────────────────────────────
const LegendItem = ({ entry, index, totalValue, isActive, onHover }) => {
  const pct = ((entry.value / totalValue) * 100).toFixed(1);
  const color = getTopicColor(entry.name);

  return (
    <Box
      onMouseEnter={() => onHover(index)}
      onMouseLeave={() => onHover(null)}
      sx={{
        display: 'flex',
        alignItems: 'center',
        gap: 0.75,
        px: 1,
        py: 0.75,
        borderRadius: 1.5,
        cursor: 'default',
        transition: 'background 0.15s',
        bgcolor: isActive ? `${color}12` : 'transparent',
        '&:hover': { bgcolor: `${color}12` },
        minWidth: 0,
      }}
    >
      {/* Rank */}
      <Typography
        sx={{
          fontSize: '0.6rem',
          fontWeight: 700,
          color: isActive ? color : '#94a3b8',
          width: 14,
          flexShrink: 0,
          transition: 'color 0.15s',
          lineHeight: 1,
        }}
      >
        {index + 1}
      </Typography>

      {/* Color swatch */}
      <Box
        sx={{
          width: 8,
          height: 8,
          borderRadius: '2px',
          bgcolor: color,
          flexShrink: 0,
          boxShadow: isActive ? `0 0 0 2px ${color}40` : 'none',
          transition: 'box-shadow 0.15s',
        }}
      />

      {/* Name — truncates, gives all leftover space */}
      <Typography
        sx={{
          flex: 1,
          fontSize: '0.73rem',
          fontWeight: isActive ? 700 : 500,
          color: isActive ? 'text.primary' : 'text.secondary',
          whiteSpace: 'nowrap',
          overflow: 'hidden',
          textOverflow: 'ellipsis',
          transition: 'all 0.15s',
          minWidth: 0,
        }}
      >
        {entry.name}
      </Typography>

      {/* Percentage — always visible, never shrinks */}
      <Typography
        sx={{
          fontSize: '0.7rem',
          fontWeight: 700,
          color: isActive ? color : 'text.disabled',
          flexShrink: 0,
          ml: 0.5,
          transition: 'color 0.15s',
        }}
      >
        {pct}%
      </Typography>
    </Box>
  );
};

// ── Main Component ───────────────────────────────────────────────────────────
export default function TopicPieChart({ data, total, title, height = 520, icon }) {
  const [activeIndex, setActiveIndex] = useState(null);

  if (!data || data.length === 0) {
    return (
      <Paper sx={{ p: 3, height, borderRadius: 2.5, border: '1px solid', borderColor: 'divider' }}>
        <Box display="flex" alignItems="center" gap={1} mb={2}>
          {icon}
          <Typography variant="h6" fontWeight={700}>{title}</Typography>
        </Box>
        <Box display="flex" alignItems="center" justifyContent="center" height={height - 100}>
          <Typography color="text.secondary">No data available</Typography>
        </Box>
      </Paper>
    );
  }

  const totalValue = data.reduce((sum, item) => sum + item.value, 0);
  // Use passed-in total (unique posts) for the center label to avoid
  // double-counting posts that belong to multiple topics.
  const centerTotal = total ?? totalValue;
  const activeItem = activeIndex !== null ? data[activeIndex] : null;

  // Split into 2 columns
  const half = Math.ceil(data.length / 2);
  const col1 = data.slice(0, half);
  const col2 = data.slice(half);

  return (
    <Paper
      elevation={0}
      sx={{
        p: 3,
        borderRadius: 2.5,
        border: '1px solid',
        borderColor: 'divider',
        bgcolor: 'background.paper',
        transition: 'box-shadow 0.2s',
        '&:hover': { boxShadow: '0 4px 20px rgba(0,0,0,0.08)' },
      }}
    >
      {/* ── Header ── */}
      <Box display="flex" alignItems="center" justifyContent="space-between" mb={2.5}>
        <Box display="flex" alignItems="center" gap={1}>
          <Box
            sx={{
              width: 32,
              height: 32,
              borderRadius: 1.5,
              bgcolor: 'primary.main',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              color: 'white',
            }}
          >
            {icon}
          </Box>
          <Typography variant="h6" fontWeight={700} fontSize="0.95rem">
            {title}
          </Typography>
        </Box>
        <Chip
          label={`${data.length} Topics`}
          size="small"
          variant="outlined"
          color="primary"
          sx={{ fontSize: '0.7rem', height: 22, borderRadius: 1 }}
        />
      </Box>

      {/* ── Donut chart with center label ── */}
      <Box sx={{ position: 'relative', mb: 1 }}>
        <ResponsiveContainer width="100%" height={220}>
          <PieChart>
            <Pie
              data={data}
              cx="50%"
              cy="50%"
              innerRadius={68}
              outerRadius={96}
              dataKey="value"
              paddingAngle={1.5}
              animationBegin={0}
              animationDuration={700}
              onMouseEnter={(_, index) => setActiveIndex(index)}
              onMouseLeave={() => setActiveIndex(null)}
            >
              {data.map((entry, index) => {
                const isActive = index === activeIndex;
                return (
                  <Cell
                    key={`cell-${index}`}
                    fill={getTopicColor(entry.name)}
                    stroke="none"
                    style={{
                      filter: isActive ? `drop-shadow(0 0 6px ${getTopicColor(entry.name)}80)` : 'none',
                      transform: isActive ? 'scale(1.04)' : 'scale(1)',
                      transformOrigin: 'center',
                      transition: 'transform 0.15s, filter 0.15s',
                    }}
                  />
                );
              })}
            </Pie>
            <Tooltip content={<CustomTooltip />} />
          </PieChart>
        </ResponsiveContainer>

        {/* Center label overlay */}
        <Box
          sx={{
            position: 'absolute',
            top: '50%',
            left: '50%',
            transform: 'translate(-50%, -50%)',
            textAlign: 'center',
            pointerEvents: 'none',
            transition: 'all 0.15s',
          }}
        >
          {activeItem ? (
            <>
              <Typography
                sx={{
                  fontSize: '0.68rem',
                  fontWeight: 700,
                  color: getTopicColor(activeItem.name),
                  letterSpacing: '0.04em',
                  textTransform: 'uppercase',
                  mb: 0.25,
                  lineHeight: 1,
                }}
              >
                {activeItem.name}
              </Typography>
              <Typography
                sx={{ fontSize: '1.45rem', fontWeight: 800, lineHeight: 1.1, color: 'text.primary' }}
              >
                {activeItem.value.toLocaleString()}
              </Typography>
              <Typography sx={{ fontSize: '0.7rem', color: 'text.disabled', mt: 0.25 }}>
                {((activeItem.value / totalValue) * 100).toFixed(1)}%
              </Typography>
            </>
          ) : (
            <>
              <Typography
                sx={{ fontSize: '1.6rem', fontWeight: 800, lineHeight: 1.1, color: 'text.primary' }}
              >
                {centerTotal.toLocaleString()}
              </Typography>
              <Typography sx={{ fontSize: '0.7rem', color: 'text.disabled', mt: 0.25 }}>
                bài viết
              </Typography>
            </>
          )}
        </Box>
      </Box>

      {/* ── Divider ── */}
      <Box sx={{ height: '1px', bgcolor: 'divider', mb: 1.5 }} />

      {/* ── Legend: 2 columns ── */}
      <Box sx={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 0, overflow: 'hidden' }}>
        <Box>
          {col1.map((entry, i) => (
            <LegendItem
              key={entry.name}
              entry={entry}
              index={i}
              totalValue={totalValue}
              isActive={activeIndex === i}
              onHover={setActiveIndex}
            />
          ))}
        </Box>
        <Box>
          {col2.map((entry, i) => (
            <LegendItem
              key={entry.name}
              entry={entry}
              index={i + half}
              totalValue={totalValue}
              isActive={activeIndex === i + half}
              onHover={setActiveIndex}
            />
          ))}
        </Box>
      </Box>
    </Paper>
  );
}
