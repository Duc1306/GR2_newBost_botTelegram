import React, { useState } from 'react';
import { Box, Typography, Paper, Grid, Chip } from '@mui/material';
import { PieChart, Pie, Cell, ResponsiveContainer, Tooltip, Sector } from 'recharts';
import { getTopicColor } from '../../theme/colors.jsx';
import TrendingUpIcon from '@mui/icons-material/TrendingUp';

// Custom active shape for interactive donut
const renderActiveShape = (props) => {
  const RADIAN = Math.PI / 180;
  const { cx, cy, midAngle, innerRadius, outerRadius, startAngle, endAngle, fill, payload, percent, value } = props;
  const sin = Math.sin(-RADIAN * midAngle);
  const cos = Math.cos(-RADIAN * midAngle);
  const sx = cx + (outerRadius + 10) * cos;
  const sy = cy + (outerRadius + 10) * sin;
  const mx = cx + (outerRadius + 30) * cos;
  const my = cy + (outerRadius + 30) * sin;
  const ex = mx + (cos >= 0 ? 1 : -1) * 22;
  const ey = my;
  const textAnchor = cos >= 0 ? 'start' : 'end';

  return (
    <g>
      <Sector
        cx={cx}
        cy={cy}
        innerRadius={innerRadius}
        outerRadius={outerRadius + 8}
        startAngle={startAngle}
        endAngle={endAngle}
        fill={fill}
      />
      <Sector
        cx={cx}
        cy={cy}
        startAngle={startAngle}
        endAngle={endAngle}
        innerRadius={outerRadius + 10}
        outerRadius={outerRadius + 12}
        fill={fill}
      />
      <path d={`M${sx},${sy}L${mx},${my}L${ex},${ey}`} stroke={fill} fill="none" />
      <circle cx={ex} cy={ey} r={2} fill={fill} stroke="none" />
      <text x={ex + (cos >= 0 ? 1 : -1) * 12} y={ey} textAnchor={textAnchor} fill="#333" fontSize={14} fontWeight="bold">
        {payload.name}
      </text>
      <text x={ex + (cos >= 0 ? 1 : -1) * 12} y={ey} dy={18} textAnchor={textAnchor} fill="#999" fontSize={12}>
        {`${value.toLocaleString()} (${(percent * 100).toFixed(1)}%)`}
      </text>
    </g>
  );
};

export default function TopicPieChart({ data, title, height = 450, icon }) {
  const [activeIndex, setActiveIndex] = useState(0);

  if (!data || data.length === 0) {
    return (
      <Paper sx={{ p: 3, height, borderRadius: 2, boxShadow: '0 2px 8px rgba(0,0,0,0.1)' }}>
        <Box display="flex" alignItems="center" gap={1} mb={2}>
          {icon}
          <Typography variant="h6" fontWeight="bold">{title}</Typography>
        </Box>
        <Box display="flex" alignItems="center" justifyContent="center" height={height - 100}>
          <Typography color="text.secondary">No data available</Typography>
        </Box>
      </Paper>
    );
  }

  const onPieEnter = (_, index) => {
    setActiveIndex(index);
  };

  const totalValue = data.reduce((sum, item) => sum + item.value, 0);

  return (
    <Paper 
      sx={{ 
        p: 3, 
        height, 
        borderRadius: 2, 
        boxShadow: '0 2px 8px rgba(0,0,0,0.1)',
        transition: 'box-shadow 0.3s',
        '&:hover': {
          boxShadow: '0 4px 16px rgba(0,0,0,0.15)',
        }
      }}
    >
      {/* Header */}
      <Box display="flex" alignItems="center" justifyContent="space-between" mb={3}>
        <Box display="flex" alignItems="center" gap={1}>
          {icon}
          <Typography variant="h6" fontWeight="bold">{title}</Typography>
        </Box>
        <Chip 
          label={`${data.length} Topics`} 
          size="small" 
          color="primary" 
          variant="outlined"
        />
      </Box>

      {/* Donut Chart */}
      <ResponsiveContainer width="100%" height={280}>
        <PieChart>
          <Pie
            activeIndex={activeIndex}
            activeShape={renderActiveShape}
            data={data}
            cx="50%"
            cy="50%"
            innerRadius={70}
            outerRadius={100}
            fill="#8884d8"
            dataKey="value"
            onMouseEnter={onPieEnter}
            animationBegin={0}
            animationDuration={800}
          >
            {data.map((entry, index) => (
              <Cell 
                key={`cell-${index}`} 
                fill={getTopicColor(entry.name)}
                style={{ cursor: 'pointer' }}
              />
            ))}
          </Pie>
          <Tooltip 
            formatter={(value) => value.toLocaleString()}
            contentStyle={{ 
              borderRadius: 8, 
              border: 'none',
              boxShadow: '0 2px 8px rgba(0,0,0,0.15)'
            }}
          />
        </PieChart>
      </ResponsiveContainer>

      {/* Custom Legend - 2 Columns */}
      <Grid container spacing={1} sx={{ mt: 2 }}>
        {data.slice(0, 10).map((entry, index) => {
          const percentage = ((entry.value / totalValue) * 100).toFixed(1);
          const isActive = index === activeIndex;
          
          return (
            <Grid size={6} key={entry.name}>
              <Box
                onMouseEnter={() => setActiveIndex(index)}
                sx={{
                  p: 1,
                  borderRadius: 1,
                  cursor: 'pointer',
                  transition: 'all 0.2s',
                  bgcolor: isActive ? 'action.hover' : 'transparent',
                  transform: isActive ? 'translateX(4px)' : 'none',
                  '&:hover': {
                    bgcolor: 'action.hover',
                    transform: 'translateX(4px)',
                  }
                }}
              >
                <Box display="flex" alignItems="center" gap={1}>
                  <Box
                    sx={{
                      width: 12,
                      height: 12,
                      borderRadius: '50%',
                      bgcolor: getTopicColor(entry.name),
                      flexShrink: 0,
                      boxShadow: isActive ? `0 0 8px ${getTopicColor(entry.name)}` : 'none',
                    }}
                  />
                  <Typography 
                    variant="caption" 
                    sx={{ 
                      fontSize: '0.75rem',
                      fontWeight: isActive ? 600 : 400,
                      color: isActive ? 'primary.main' : 'text.secondary',
                      overflow: 'hidden',
                      textOverflow: 'ellipsis',
                      whiteSpace: 'nowrap',
                      flex: 1,
                    }}
                  >
                    {entry.name}
                  </Typography>
                  <Typography 
                    variant="caption" 
                    sx={{ 
                      fontWeight: 600,
                      color: isActive ? 'primary.main' : 'text.secondary',
                      fontSize: '0.7rem',
                    }}
                  >
                    {percentage}%
                  </Typography>
                </Box>
              </Box>
            </Grid>
          );
        })}
      </Grid>

      {/* Footer Stats */}
      <Box 
        sx={{ 
          mt: 3, 
          pt: 2, 
          borderTop: '1px solid',
          borderColor: 'divider',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center'
        }}
      >
        <Box display="flex" alignItems="center" gap={0.5}>
          <TrendingUpIcon sx={{ fontSize: 16, color: 'success.main' }} />
          <Typography variant="caption" color="text.secondary">
            Total Posts:
          </Typography>
          <Typography variant="caption" fontWeight="bold" color="primary">
            {totalValue.toLocaleString()}
          </Typography>
        </Box>
        <Typography variant="caption" color="text.secondary">
          Top: {data[0]?.name} ({((data[0]?.value / totalValue) * 100).toFixed(1)}%)
        </Typography>
      </Box>
    </Paper>
  );
}
