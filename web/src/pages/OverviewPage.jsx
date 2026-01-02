import React from 'react';
import { Box, Typography, CircularProgress, Alert, Grid } from "@mui/material";
import ArticleIcon from '@mui/icons-material/Article';
import CategoryIcon from '@mui/icons-material/Category';
import LabelIcon from '@mui/icons-material/Label';
import SourceIcon from '@mui/icons-material/Source';
import StatCard from '../components/cards/StatCard.jsx';
import TimelineChart from '../components/charts/TimelineChart.jsx';
import TopicPieChart from '../components/charts/TopicPieChart.jsx';
import KeywordCloud from '../components/charts/KeywordCloud.jsx';
import {useStats, useTrendingTopics, useTimeline, useKeywords } from '../hooks/useApi.jsx';
import { getTopicColor } from '../theme/colors.jsx';

export default function OverviewPage() {
  // Calculate date range for API calls
  const today = new Date();
  const date_to = today.toISOString().split('T')[0];
  const date_from = new Date(today.setDate(today.getDate() - 30)).toISOString().split('T')[0];

  const { data: stats, isLoading: statsLoading, error: statsError } = useStats();
  const { data: trending, isLoading: trendingLoading } = useTrendingTopics({ days: 7 });
  const { data: timeline, isLoading: timelineLoading, error: timelineError } = useTimeline({ 
    date_from, 
    date_to, 
    granularity: 'day' 
  });
  const { data: keywords, isLoading: keywordsLoading, error: keywordsError } = useKeywords({ 
    limit: 50,
    date_from,
    date_to
  });

  if (statsLoading) {
    return (
      <Box display="flex" justifyContent="center" alignItems="center" minHeight="400px">
        <CircularProgress />
      </Box>
    );
  }

  if (statsError) {
    return (
      <Alert severity="error" sx={{ m: 2 }}>
        Failed to load dashboard data: {statsError.message}
      </Alert>
    );
  }

  // Calculate stats from API data
  const totalPosts = stats?.total_posts || 0;
  const topicStats = stats?.by_topic || {};
  const totalTopics = Object.keys(topicStats).length;
  const totalSources = stats?.by_source ? Object.keys(stats.by_source).length : 0;
  const labeledPosts = Object.values(topicStats).reduce((sum, count) => sum + count, 0);

  // Prepare pie chart data
  const topicDistribution = Object.entries(topicStats).map(([name, value]) => ({
    name,
    value,
  }));

  // Prepare timeline data with proper date formatting
  const timelineData = timeline?.timeline?.map(item => ({
    date: item.date,
    count: item.count,
  })) || [];

  // Get trending topics for display
  const trendingList = trending?.topics?.slice(0, 5) || [];

  // Keywords for word cloud
  const keywordData = keywords?.keywords?.slice(0, 50).map(k => ({
    text: k.keyword,
    value: k.total_count,
  })) || [];

  return (
    <Box sx={{ pb: 4 }}>
      {/* Header */}
      <Box sx={{ mb: 4 }}>
        <Typography variant="h3" fontWeight="bold" sx={{ mb: 1, color: 'primary.main' }}>
          📊 Dashboard Overview
        </Typography>
        <Typography variant="body1" color="text.secondary">
          Real-time analytics from social media sources
        </Typography>
      </Box>

      {/* Stat Cards - Full Width */}
      <Grid container spacing={0} sx={{ mb: 4, mx: 0 }}>
        <Grid item xs={12} sm={6} md={3} sx={{ px: 1 }}>
          <StatCard
            title="Total Posts"
            value={totalPosts.toLocaleString()}
            subtitle="All time"
            icon={ArticleIcon}
          />
        </Grid>
        <Grid item xs={12} sm={6} md={3} sx={{ px: 1 }}>
          <StatCard
            title="Topics"
            value={totalTopics}
            subtitle="ML Categories"
            icon={CategoryIcon}
          />
        </Grid>
        <Grid item xs={12} sm={6} md={3} sx={{ px: 1 }}>
          <StatCard
            title="Labeled Posts"
            value={labeledPosts.toLocaleString()}
            subtitle={`${((labeledPosts / totalPosts) * 100).toFixed(1)}% classified`}
            icon={LabelIcon}
          />
        </Grid>
        <Grid item xs={12} sm={6} md={3} sx={{ px: 1 }}>
          <StatCard
            title="Sources"
            value={totalSources}
            subtitle="Active platforms"
            icon={SourceIcon}
          />
        </Grid>
      </Grid>

      {/* Main Charts Section */}
      <Grid container spacing={3} sx={{ mb: 4 }}>
        {/* Trending Topics */}
        <Grid item xs={12} md={4}>
          <Box 
            sx={{ 
              bgcolor: 'background.paper', 
              p: 3, 
              borderRadius: 2, 
              boxShadow: '0 2px 8px rgba(0,0,0,0.1)',
              height: '100%',
              transition: 'box-shadow 0.3s',
              '&:hover': {
                boxShadow: '0 4px 16px rgba(0,0,0,0.15)',
              }
            }}
          >
            <Typography variant="h6" gutterBottom fontWeight="bold">
              🔥 Trending Topics (7 days)
            </Typography>
            {trendingLoading ? (
              <CircularProgress size={24} />
            ) : trendingList.length > 0 ? (
              <Box>
                {trendingList.map((topic, index) => (
                  <Box 
                    key={topic.topic} 
                    sx={{ 
                      py: 1.5, 
                      borderBottom: index < trendingList.length - 1 ? '1px solid #eee' : 'none',
                      display: 'flex',
                      justifyContent: 'space-between',
                      alignItems: 'center',
                    }}
                  >
                    <Box>
                      <Typography variant="body1" fontWeight="bold">
                        {index + 1}. {topic.topic}
                      </Typography>
                      <Typography variant="caption" color="text.secondary">
                        {topic.total_posts} posts • {topic.avg_confidence.toFixed(1)}% confidence
                      </Typography>
                    </Box>
                    <Typography 
                      variant="body2" 
                      fontWeight="bold"
                      sx={{ 
                        color: topic.growth_rate > 0 ? 'success.main' : 'error.main',
                      }}
                    >
                      {topic.growth_rate > 0 ? '↑' : '↓'} {Math.abs(topic.growth_rate).toFixed(0)}%
                    </Typography>
                  </Box>
                ))}
              </Box>
            ) : (
              <Typography color="text.secondary">No trending data yet</Typography>
            )}
          </Box>
        </Grid>

        {/* Post Volume Chart */}
        <Grid item xs={12} md={8}>
          {timelineLoading ? (
            <Box display="flex" justifyContent="center" p={4}>
              <CircularProgress />
            </Box>
          ) : (
            <TimelineChart
              data={timelineData}
              title="📈 Post Volume (30 days)"
              dataKeys={['count']}
              height={350}
            />
          )}
        </Grid>
      </Grid>

      {/* Platform & Keywords Row */}
      <Grid container spacing={3} sx={{ mb: 4 }}>
        <Grid item xs={12} md={4}>
          <Box 
            sx={{ 
              bgcolor: 'background.paper', 
              p: 3, 
              borderRadius: 2, 
              boxShadow: '0 2px 8px rgba(0,0,0,0.1)',
              height: '100%',
              transition: 'box-shadow 0.3s',
              '&:hover': {
                boxShadow: '0 4px 16px rgba(0,0,0,0.15)',
              }
            }}
          >
            <Typography variant="h6" gutterBottom fontWeight="bold">\ud83c\udd9a Platform Split</Typography>
            <Box sx={{ mt: 4 }}>
              <Box sx={{ mb: 3 }}>
                <Box display="flex" justifyContent="space-between" mb={1}>
                  <Typography variant="body1">Telegram</Typography>
                  <Typography variant="body1" fontWeight="bold">
                    {stats?.platform_counts?.telegram || 0} ({((stats?.platform_counts?.telegram || 0) / (stats?.total_posts || 1) * 100).toFixed(1)}%)
                  </Typography>
                </Box>
                <Box sx={{ bgcolor: '#e0e0e0', borderRadius: 1, height: 24 }}>
                  <Box 
                    sx={{ 
                      bgcolor: '#0088cc', 
                      height: '100%', 
                      borderRadius: 1,
                      width: `${(stats?.platform_counts?.telegram || 0) / (stats?.total_posts || 1) * 100}%`,
                    }}
                  />
                </Box>
              </Box>
              <Box>
                <Box display="flex" justifyContent="space-between" mb={1}>
                  <Typography variant="body1">Twitter</Typography>
                  <Typography variant="body1" fontWeight="bold">
                    {stats?.platform_counts?.twitter || 0} ({((stats?.platform_counts?.twitter || 0) / (stats?.total_posts || 1) * 100).toFixed(1)}%)
                  </Typography>
                </Box>
                <Box sx={{ bgcolor: '#e0e0e0', borderRadius: 1, height: 24 }}>
                  <Box 
                    sx={{ 
                      bgcolor: '#1DA1F2', 
                      height: '100%', 
                      borderRadius: 1,
                      width: `${(stats?.platform_counts?.twitter || 0) / (stats?.total_posts || 1) * 100}%`,
                    }}
                  />
                </Box>
              </Box>
            </Box>
          </Box>
        </Grid>

        {/* Word Cloud - takes more space */}
        <Grid item xs={12} md={8}>
          {keywordsLoading ? (
            <Box 
              display="flex" 
              justifyContent="center" 
              alignItems="center" 
              height={400} 
              bgcolor="background.paper" 
              borderRadius={2}
              boxShadow="0 2px 8px rgba(0,0,0,0.1)"
            >
              <CircularProgress />
            </Box>
          ) : (
            <KeywordCloud
              keywords={keywordData}
              title="🔥 Trending Keywords"
              height={400}
            />
          )}
        </Grid>
      </Grid>

      {/* Topic Distribution - Better Layout */}
      <Grid container spacing={3}>
        <Grid item xs={12} md={5}>
          <TopicPieChart
            data={topicDistribution.sort((a, b) => b.value - a.value)}
            title="📊 Topic Distribution"
            height={450}
          />
        </Grid>
        <Grid item xs={12} md={7}>
          <Box 
            sx={{ 
              bgcolor: 'background.paper', 
              p: 3, 
              borderRadius: 2, 
              boxShadow: '0 2px 8px rgba(0,0,0,0.1)',
              height: '100%',
            }}
          >
            <Typography variant="h6" gutterBottom fontWeight="bold">
              📈 Topic Breakdown
            </Typography>
            <Box sx={{ mt: 3 }}>
              {topicDistribution
                .sort((a, b) => b.value - a.value)
                .map((topic, index) => {
                  const percentage = ((topic.value / totalPosts) * 100).toFixed(1);
                  return (
                    <Box key={topic.name} sx={{ mb: 3 }}>
                      <Box display="flex" justifyContent="space-between" alignItems="center" mb={1}>
                        <Box display="flex" alignItems="center" gap={1}>
                          <Box
                            sx={{
                              width: 16,
                              height: 16,
                              borderRadius: '50%',
                              bgcolor: getTopicColor(topic.name),
                            }}
                          />
                          <Typography variant="body1" fontWeight="600">
                            {index + 1}. {topic.name}
                          </Typography>
                        </Box>
                        <Typography variant="body2" color="text.secondary">
                          {topic.value.toLocaleString()} posts ({percentage}%)
                        </Typography>
                      </Box>
                      <Box sx={{ bgcolor: '#e0e0e0', borderRadius: 1, height: 10, overflow: 'hidden' }}>
                        <Box
                          sx={{
                            bgcolor: getTopicColor(topic.name),
                            height: '100%',
                            width: `${percentage}%`,
                            borderRadius: 1,
                            transition: 'width 0.3s ease',
                          }}
                        />
                      </Box>
                    </Box>
                  );
                })}
            </Box>
          </Box>
        </Grid>
      </Grid>
    </Box>
  );
}
