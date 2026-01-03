import React, { useState } from 'react';
import {
  Box,
  Typography,
  Grid,
  Paper,
  CircularProgress,
  TextField,
  Button,
} from '@mui/material';
import { DatePicker } from '@mui/x-date-pickers/DatePicker';
import { LocalizationProvider } from '@mui/x-date-pickers/LocalizationProvider';
import { AdapterDateFns } from '@mui/x-date-pickers/AdapterDateFns';
import { subDays } from 'date-fns';
import TimelineChart from '../components/charts/TimelineChart.jsx';
import KeywordsBarChart from '../components/charts/KeywordsBarChart.jsx';
import { useTimeline, useKeywords, useComparison, useHeatmap } from '../hooks/useApi.jsx';
import { getTopicColor } from '../theme/colors.jsx';
import AnalyticsIcon from '@mui/icons-material/Analytics';
import TrendingUpIcon from '@mui/icons-material/TrendingUp';
import AbcIcon from '@mui/icons-material/Abc';
import BarChartIcon from '@mui/icons-material/BarChart';
import CalendarMonthIcon from '@mui/icons-material/CalendarMonth';
import TelegramIcon from '@mui/icons-material/Telegram';
import TwitterIcon from '@mui/icons-material/Twitter';

export default function AnalyticsPage() {
  const [startDate, setStartDate] = useState(subDays(new Date(), 30));
  const [endDate, setEndDate] = useState(new Date());
  
  // Format dates for API
  const date_from = startDate.toISOString().split('T')[0];
  const date_to = endDate.toISOString().split('T')[0];

  const { data: timeline, isLoading: timelineLoading } = useTimeline({ 
    date_from, 
    date_to, 
    granularity: 'day' 
  });
  const { data: keywords, isLoading: keywordsLoading } = useKeywords({ 
    limit: 20, 
    date_from, 
    date_to 
  });
  const { data: comparison, isLoading: comparisonLoading } = useComparison({ 
    date_from, 
    date_to 
  });
  const { data: heatmapData, isLoading: heatmapLoading } = useHeatmap({ 
    date_from, 
    date_to 
  });

  const handleApplyFilter = () => {
    // Dates are already reactive, component will re-render
    setStartDate(new Date(startDate));
    setEndDate(new Date(endDate));
  };

  // Prepare multi-topic timeline data
  const timelineData = timeline?.timeline?.map(item => ({
    date: item.date,
    count: item.count,
  })) || [];

  // Prepare keywords data for bar chart
  const keywordsData = keywords?.keywords?.slice(0, 10).map(k => ({
    keyword: k.keyword,
    count: k.count,
  })) || [];

  console.log('Keywords data:', keywords);
  console.log('Formatted keywordsData:', keywordsData);
  console.log('Keywords loading:', keywordsLoading);

  return (
    <Box>
      <Box display="flex" alignItems="center" gap={1} mb={1}>
        <AnalyticsIcon sx={{ fontSize: 32, color: 'primary.main' }} />
        <Typography variant="h4" fontWeight="bold">
          Analytics
        </Typography>
      </Box>
      <Typography variant="body1" color="text.secondary" paragraph>
        Deep dive into trends and patterns
      </Typography>

      {/* Date Range Filter */}
      <Paper sx={{ p: 2, mb: 3 }}>
        <LocalizationProvider dateAdapter={AdapterDateFns}>
          <Box display="flex" gap={2} alignItems="center" flexWrap="wrap">
            <DatePicker
              label="Start Date"
              value={startDate}
              onChange={(newValue) => setStartDate(newValue)}
              renderInput={(params) => <TextField {...params} />}
            />
            <DatePicker
              label="End Date"
              value={endDate}
              onChange={(newValue) => setEndDate(newValue)}
              renderInput={(params) => <TextField {...params} />}
            />
            <Button variant="contained" onClick={handleApplyFilter}>
              Apply
            </Button>
          </Box>
        </LocalizationProvider>
      </Paper>

      {/* Topic Trends Over Time */}
      <Box sx={{ mb: 3 }}>
        {timelineLoading ? (
          <Box display="flex" justifyContent="center" p={4}>
            <CircularProgress />
          </Box>
        ) : (
          <TimelineChart
            data={timelineData}
            title="Topic Trends Over Time"
            icon={<TrendingUpIcon />}
            dataKeys={['count']}
            height={400}
          />
        )}
      </Box>

      {/* Keywords and Platform Comparison */}
      <Box sx={{ width: '100%', mb: 3 }}>
        <Grid container spacing={3}>
          {/* Top Keywords */}
          <Grid item xs={12} md={8}>
            {keywordsLoading ? (
              <Box display="flex" justifyContent="center" alignItems="center" sx={{ height: 400 }}>
                <CircularProgress />
              </Box>
            ) : keywordsData.length > 0 ? (
              <KeywordsBarChart
                data={keywordsData}
                title="Top Keywords"
                icon={<AbcIcon />}
                height={400}
              />
            ) : (
              <Paper sx={{ p: 3, height: 400, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                <Typography color="text.secondary">Không có dữ liệu keywords</Typography>
              </Paper>
            )}
          </Grid>

        {/* Platform Stats */}
        <Grid item xs={12} md={4}>
          <Paper sx={{ p: 3, height: '100%' }}>
            <Box display="flex" alignItems="center" gap={1} mb={2}>
              <BarChartIcon sx={{ color: 'primary.main' }} />
              <Typography variant="h6" fontWeight="600">
                Platform Activity
              </Typography>
            </Box>
            {comparisonLoading ? (
              <Box display="flex" justifyContent="center" py={4}>
                <CircularProgress size={32} />
              </Box>
            ) : comparison?.comparison ? (
              <Box sx={{ mt: 2 }}>
                {Object.entries(comparison.comparison)
                  .filter(([_, data]) => data.total_posts > 0)
                  .map(([platform, data]) => (
                    <Box key={platform} sx={{ mb: 3, p: 2, bgcolor: 'background.default', borderRadius: 2 }}>
                      <Box display="flex" justifyContent="space-between" alignItems="center" mb={1}>
                        <Box display="flex" alignItems="center" gap={1}>
                          {platform === 'telegram' ? <TelegramIcon /> : <TwitterIcon />}
                          <Typography variant="subtitle1" fontWeight="700" textTransform="capitalize">
                            {platform === 'telegram' ? 'Telegram' : 'Twitter'}
                          </Typography>
                        </Box>
                        <Typography variant="caption" sx={{ px: 1, py: 0.5, bgcolor: 'primary.main', color: 'white', borderRadius: 1 }}>
                          {data.avg_daily} posts/day
                        </Typography>
                      </Box>
                      <Typography variant="h3" color="primary" fontWeight="bold" mb={0.5}>
                        {data.total_posts?.toLocaleString() || 0}
                      </Typography>
                      <Typography variant="caption" color="text.secondary" display="block" mb={2}>
                        Total Posts
                      </Typography>
                      {data.top_topics && data.top_topics.length > 0 && (
                        <Box>
                          <Typography variant="caption" color="text.secondary" display="block" mb={1}>
                            Top Topics:
                          </Typography>
                          {data.top_topics.slice(0, 3).map((topicItem, idx) => {
                            const topicName = typeof topicItem === 'string' ? topicItem : topicItem.topic;
                            const topicCount = typeof topicItem === 'string' ? 0 : topicItem.count;
                            return (
                              <Box 
                                key={idx}
                                sx={{ 
                                  display: 'flex',
                                  justifyContent: 'space-between',
                                  alignItems: 'center',
                                  mb: 0.5,
                                  p: 1,
                                  borderRadius: 1,
                                  bgcolor: getTopicColor(topicName),
                                  color: 'white',
                                }}
                              >
                                <Typography variant="body2" fontWeight="500">
                                  {topicName}
                                </Typography>
                                <Typography variant="caption" fontWeight="600">
                                  {topicCount.toLocaleString()}
                                </Typography>
                              </Box>
                            );
                          })}
                        </Box>
                      )}
                    </Box>
                  ))}
                {Object.values(comparison.comparison).every(d => d.total_posts === 0) && (
                  <Typography color="text.secondary" textAlign="center" py={4}>
                    No data available for this period
                  </Typography>
                )}
              </Box>
            ) : (
              <Typography color="text.secondary" textAlign="center" py={4}>
                No comparison data
              </Typography>
            )}
          </Paper>
        </Grid>
      </Grid>

      {/* Activity Heatmap */}
      <Paper sx={{ p: 3 }}>
        <Box display="flex" alignItems="center" gap={1} mb={2}>
          <CalendarMonthIcon sx={{ color: 'primary.main' }} />
          <Typography variant="h6" fontWeight="bold">
            Activity Heatmap
          </Typography>
        </Box>
        {heatmapLoading ? (
          <Box display="flex" justifyContent="center" py={4}>
            <CircularProgress />
          </Box>
        ) : (
          <Box sx={{ overflowX: 'auto' }}>
            <Box sx={{ minWidth: 800 }}>
              {/* Hours header */}
              <Box sx={{ display: 'flex', mb: 1 }}>
                <Box sx={{ width: 80 }} /> {/* Spacer for day labels */}
                {Array.from({ length: 24 }, (_, i) => (
                  <Box 
                    key={i} 
                    sx={{ 
                      flex: 1, 
                      textAlign: 'center', 
                      fontSize: '0.7rem',
                      color: 'text.secondary'
                    }}
                  >
                    {i}h
                  </Box>
                ))}
              </Box>
              
              {/* Heatmap grid */}
              {['Thứ 2', 'Thứ 3', 'Thứ 4', 'Thứ 5', 'Thứ 6', 'Thứ 7', 'CN'].map((day, dayIndex) => {
                const maxValue = heatmapData ? Math.max(...Object.values(heatmapData.heatmap).flatMap(h => Object.values(h))) : 100;
                
                return (
                  <Box key={day} sx={{ display: 'flex', mb: 0.5, alignItems: 'center' }}>
                    <Box sx={{ width: 80, fontSize: '0.875rem', fontWeight: 500 }}>
                      {day}
                    </Box>
                    {Array.from({ length: 24 }, (_, hour) => {
                      const value = heatmapData?.heatmap?.[dayIndex]?.[hour] || 0;
                      const intensity = maxValue > 0 ? value / maxValue : 0;
                  return (
                    <Box
                      key={hour}
                      sx={{
                        flex: 1,
                        height: 35,
                        mx: 0.25,
                        bgcolor: intensity > 0 ? `rgba(59, 130, 246, ${0.2 + intensity * 0.8})` : '#f3f4f6',
                        borderRadius: 0.5,
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        fontSize: '0.7rem',
                        color: intensity > 0.5 ? 'white' : 'text.secondary',
                        cursor: 'pointer',
                        transition: 'all 0.2s',
                        '&:hover': {
                          transform: 'scale(1.1)',
                          zIndex: 1,
                          boxShadow: 1,
                        }
                      }}
                      title={`${day} ${hour}h: ${value} bài`}
                    >
                      {value > 0 ? value : ''}
                    </Box>
                  );
                })}
              </Box>
            );
          })}
            
            {/* Legend */}
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 2, mt: 2, justifyContent: 'flex-end' }}>
              <Typography variant="caption" color="text.secondary">Ít</Typography>
              <Box sx={{ display: 'flex', gap: 0.5 }}>
                {[0.2, 0.4, 0.6, 0.8, 1].map((intensity) => (
                  <Box
                    key={intensity}
                    sx={{
                      width: 20,
                      height: 20,
                      bgcolor: `rgba(59, 130, 246, ${intensity})`,
                      borderRadius: 0.5,
                    }}
                  />
                ))}
              </Box>
              <Typography variant="caption" color="text.secondary">Nhiều</Typography>
            </Box>
          </Box>
        </Box>
        )}
      </Paper>
    </Box>
    </Box>
  );
}
