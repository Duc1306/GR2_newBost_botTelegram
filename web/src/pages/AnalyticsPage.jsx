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
import { useTimeline, useKeywords, useComparison } from '../hooks/useApi.jsx';
import { getTopicColor } from '../theme/colors.jsx';

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
      <Typography variant="h4" gutterBottom fontWeight="bold">
        📈 Analytics
      </Typography>
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
            title="📊 Topic Trends Over Time"
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
                title="🔤 Top Keywords"
                height={400}
              />
            ) : (
              <Paper sx={{ p: 3, height: 400, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                <Typography color="text.secondary">Không có dữ liệu keywords</Typography>
              </Paper>
            )}
          </Grid>

        {/* Platform Comparison */}
        <Grid item xs={12} md={4}>
          <Paper sx={{ p: 2, height: '100%' }}>
            <Typography variant="h6" gutterBottom>
              🆚 Platform Comparison
            </Typography>
            {comparisonLoading ? (
              <CircularProgress size={24} />
            ) : comparison?.comparison ? (
              <Box sx={{ mt: 2 }}>
                {Object.entries(comparison.comparison).map(([platform, data]) => (
                  <Box key={platform} sx={{ mb: 3 }}>
                    <Typography variant="subtitle1" fontWeight="bold" textTransform="capitalize">
                      {platform}
                    </Typography>
                    <Typography variant="h4" color="primary" fontWeight="bold">
                      {data.total_posts?.toLocaleString() || 0}
                    </Typography>
                    <Typography variant="body2" color="text.secondary">
                      posts
                    </Typography>
                    {data.top_topics && data.top_topics.length > 0 && (
                      <Box sx={{ mt: 1 }}>
                        <Typography variant="caption" color="text.secondary">
                          Top Topics:
                        </Typography>
                        {data.top_topics.slice(0, 3).map((topicItem, idx) => {
                          const topicName = typeof topicItem === 'string' ? topicItem : topicItem.topic;
                          return (
                            <Box 
                              key={idx}
                              sx={{ 
                                display: 'inline-block',
                                bgcolor: getTopicColor(topicName),
                                color: 'white',
                                px: 1,
                                py: 0.5,
                                borderRadius: 1,
                                fontSize: '0.75rem',
                                mr: 0.5,
                                mt: 0.5,
                              }}
                            >
                              {topicName}
                            </Box>
                          );
                        })}
                      </Box>
                    )}
                  </Box>
                ))}
              </Box>
            ) : (
              <Typography color="text.secondary">No comparison data</Typography>
            )}
          </Paper>
        </Grid>
      </Grid>

      {/* Activity Heatmap Placeholder */}
      <Paper sx={{ p: 2 }}>
        <Typography variant="h6" gutterBottom>
          📅 Activity Heatmap (Coming Soon)
        </Typography>
        <Box 
          sx={{ 
            height: 200, 
            display: 'flex', 
            alignItems: 'center', 
            justifyContent: 'center',
            bgcolor: 'background.default',
            borderRadius: 1,
          }}
        >
          <Typography color="text.secondary">
            Activity heatmap by day of week & hour
          </Typography>
        </Box>
      </Paper>
    </Box>
    </Box>
  );
}
