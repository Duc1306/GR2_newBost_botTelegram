import React from 'react';
import { Box, Typography, CircularProgress, Alert, Grid } from "@mui/material";
import ArticleIcon from '@mui/icons-material/Article';
import CategoryIcon from '@mui/icons-material/Category';
import LabelIcon from '@mui/icons-material/Label';
import SourceIcon from '@mui/icons-material/Source';
import DashboardIcon from '@mui/icons-material/Dashboard';
import LocalFireDepartmentIcon from '@mui/icons-material/LocalFireDepartment';
import TrendingUpIcon from '@mui/icons-material/TrendingUp';
import PieChartIcon from '@mui/icons-material/PieChart';
import BarChartIcon from '@mui/icons-material/BarChart';
import StatCard from '../../components/cards/StatCard.jsx';
import TimelineChart from '../../components/charts/TimelineChart.jsx';
import TopicPieChart from '../../components/charts/TopicPieChart.jsx';
import KeywordCloud from '../../components/charts/KeywordCloud.jsx';
import {useStats, useTrendingTopics, useTimeline, useKeywords } from '../../hooks/useApi.jsx';
import { getTopicColor } from '../../theme/colors.jsx';

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
  const labeledPosts = stats?.labeled_posts || 0;

  // Platform stats from real API data
  const byPlatform = stats?.by_platform || {};
  const telegramCount = byPlatform.telegram || 0;
  const xCount = byPlatform.x || 0;

  // Active channels from real API data
  const activeChannels = stats?.active_channels || {};
  const activeTotal = activeChannels.total || 0;
  const activeTelegram = activeChannels.telegram || 0;
  const activeX = activeChannels.x || 0;

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
        <Box display="flex" alignItems="center" gap={1} mb={1}>
          <DashboardIcon sx={{ fontSize: 32, color: 'primary.main' }} />
          <Typography variant="h3" fontWeight="bold" sx={{ color: 'primary.main' }}>
            Dashboard Overview
          </Typography>
        </Box>
        <Typography variant="body1" color="text.secondary">
          Real-time analytics from social media sources
        </Typography>
      </Box>

      {/* Stat Cards - Full Width */}
      <Grid container spacing={0} sx={{ mb: 4, mx: 0 }}>
        <Grid size={{ xs: 12, sm: 6, md: 3 }} sx={{ px: 1 }}>
          <StatCard
            title="Tổng bài viết"
            value={totalPosts.toLocaleString()}
            subtitle="Tất cả thời gian"
            icon={ArticleIcon}
          />
        </Grid>
        <Grid size={{ xs: 12, sm: 6, md: 3 }} sx={{ px: 1 }}>
          <StatCard
            title="Đã phân loại"
            value={labeledPosts.toLocaleString()}
            subtitle={totalPosts > 0 ? `${((labeledPosts / totalPosts) * 100).toFixed(1)}% có chủ đề` : '0%'}
            icon={LabelIcon}
          />
        </Grid>
        <Grid size={{ xs: 12, sm: 6, md: 3 }} sx={{ px: 1 }}>
          <StatCard
            title="Kênh đang hoạt động"
            value={activeTotal.toLocaleString()}
            subtitle={`${activeTelegram} Telegram · ${activeX} X`}
            icon={SourceIcon}
          />
        </Grid>
        <Grid size={{ xs: 12, sm: 6, md: 3 }} sx={{ px: 1 }}>
          <StatCard
            title="Chủ đề ML"
            value={totalTopics}
            subtitle={`${totalSources} nguồn · ${totalTopics} danh mục`}
            icon={CategoryIcon}
          />
        </Grid>
      </Grid>

      {/* Main Charts Section */}
      <Grid container spacing={3} sx={{ mb: 4 }}>
        {/* Trending Topics */}
        <Grid size={{ xs: 12, md: 4 }}>
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
            <Box display="flex" alignItems="center" gap={1} mb={2}>
              <LocalFireDepartmentIcon sx={{ color: 'error.main' }} />
              <Typography variant="h6" fontWeight="bold">
                Top Topics 
              </Typography>
            </Box>
            {statsLoading ? (
              <CircularProgress size={24} />
            ) : topicDistribution.length > 0 ? (
              <Box>
                {topicDistribution.slice(0, 5).map((item, index) => {
                  const percentage = ((item.value / stats?.total_posts) * 100).toFixed(1);
                  return (
                    <Box 
                      key={item.name} 
                      sx={{ 
                        mb: 2,
                        p: 1.5,
                        borderRadius: 1,
                        bgcolor: 'background.default',
                        transition: 'all 0.2s',
                        '&:hover': {
                          bgcolor: 'action.hover',
                          transform: 'translateX(4px)',
                        }
                      }}
                    >
                      <Box display="flex" justifyContent="space-between" alignItems="center" mb={0.5}>
                        <Typography variant="body1" fontWeight="600">
                          #{index + 1} {item.name}
                        </Typography>
                        <Typography variant="h6" fontWeight="bold" color="primary">
                          {item.value.toLocaleString()}
                        </Typography>
                      </Box>
                      <Box display="flex" alignItems="center" gap={1}>
                        <Box 
                          sx={{ 
                            flex: 1, 
                            height: 6, 
                            bgcolor: 'grey.200', 
                            borderRadius: 1,
                            overflow: 'hidden'
                          }}
                        >
                          <Box 
                            sx={{ 
                              width: `${percentage}%`, 
                              height: '100%', 
                              bgcolor: getTopicColor(item.name),
                              transition: 'width 0.3s'
                            }} 
                          />
                        </Box>
                        <Typography variant="caption" color="text.secondary" fontWeight="500">
                          {percentage}%
                        </Typography>
                      </Box>
                    </Box>
                  );
                })}
              </Box>
            ) : (
              <Typography color="text.secondary">No trending data yet</Typography>
            )}
          </Box>
        </Grid>

        {/* Post Volume Chart */}
        <Grid size={{ xs: 12, md: 8 }}>
          {timelineLoading ? (
            <Box display="flex" justifyContent="center" p={4}>
              <CircularProgress />
            </Box>
          ) : (
            <TimelineChart
              data={timelineData}
              title="Post Activity Over Time"
              icon={<TrendingUpIcon />}
              dataKeys={['count']}
              height={350}
            />
          )}
        </Grid>
      </Grid>

      {/* Platform & Keywords Row */}
      <Grid container spacing={3} sx={{ mb: 4 }}>
        <Grid size={{ xs: 12, md: 4 }}>
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
            <Typography variant="h6" gutterBottom fontWeight="bold">Platform Split</Typography>
            <Box sx={{ mt: 2 }}>
              {/* Telegram */}
              <Box sx={{ mb: 3 }}>
                <Box display="flex" justifyContent="space-between" mb={0.5}>
                  <Box display="flex" alignItems="center" gap={1}>
                    <Box sx={{ width: 10, height: 10, borderRadius: '50%', bgcolor: '#0088cc' }} />
                    <Typography variant="body2" fontWeight={600}>Telegram</Typography>
                  </Box>
                  <Typography variant="body2" fontWeight="bold">
                    {telegramCount.toLocaleString()} ({totalPosts > 0 ? ((telegramCount / totalPosts) * 100).toFixed(1) : 0}%)
                  </Typography>
                </Box>
                <Box sx={{ bgcolor: '#e0e0e0', borderRadius: 1, height: 20, overflow: 'hidden' }}>
                  <Box sx={{ bgcolor: '#0088cc', height: '100%', borderRadius: 1, width: `${totalPosts > 0 ? (telegramCount / totalPosts) * 100 : 0}%`, transition: 'width 0.5s' }} />
                </Box>
                <Typography variant="caption" color="text.disabled">{activeTelegram} kênh active</Typography>
              </Box>
              {/* X / Twitter */}
              <Box sx={{ mb: 3 }}>
                <Box display="flex" justifyContent="space-between" mb={0.5}>
                  <Box display="flex" alignItems="center" gap={1}>
                    <Box sx={{ width: 10, height: 10, borderRadius: '50%', bgcolor: '#000000' }} />
                    <Typography variant="body2" fontWeight={600}>X / Twitter</Typography>
                  </Box>
                  <Typography variant="body2" fontWeight="bold">
                    {xCount.toLocaleString()} ({totalPosts > 0 ? ((xCount / totalPosts) * 100).toFixed(1) : 0}%)
                  </Typography>
                </Box>
                <Box sx={{ bgcolor: '#e0e0e0', borderRadius: 1, height: 20, overflow: 'hidden' }}>
                  <Box sx={{ bgcolor: '#000000', height: '100%', borderRadius: 1, width: `${totalPosts > 0 ? (xCount / totalPosts) * 100 : 0}%`, transition: 'width 0.5s' }} />
                </Box>
                <Typography variant="caption" color="text.disabled">{activeX} kênh active</Typography>
              </Box>
              {/* Summary */}
              <Box sx={{ mt: 3, p: 1.5, bgcolor: 'action.hover', borderRadius: 1.5 }}>
                <Typography variant="caption" color="text.secondary" display="block">
                  Tổng: <strong>{totalPosts.toLocaleString()} bài</strong> · <strong>{activeTotal} kênh active</strong> · {totalTopics} chủ đề
                </Typography>
              </Box>
            </Box>
          </Box>
        </Grid>

        {/* Word Cloud - takes more space */}
        <Grid size={{ xs: 12, md: 8 }}>
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
              title="Trending Keywords"
              icon={<LocalFireDepartmentIcon />}
              height={400}
            />
          )}
        </Grid>
      </Grid>

      {/* Topic Distribution - Better Layout */}
      <Grid container spacing={3}>
        <Grid size={{ xs: 12, md: 5 }}>
          <TopicPieChart
            data={topicDistribution.sort((a, b) => b.value - a.value)}
            title="Topic Distribution"
            icon={<PieChartIcon />}
            height={520}
          />
        </Grid>
        <Grid size={{ xs: 12, md: 7 }}>
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
            {/* Header */}
            <Box display="flex" alignItems="center" justifyContent="space-between" mb={3}>
              <Box display="flex" alignItems="center" gap={1}>
                <BarChartIcon sx={{ color: 'primary.main' }} />
                <Typography variant="h6" fontWeight="bold">
                  Detailed Breakdown
                </Typography>
              </Box>
              <Typography variant="caption" color="text.secondary">
                Last 30 days
              </Typography>
            </Box>

            {/* Topic List with Enhanced Design */}
            <Box sx={{ 
              maxHeight: 440, 
              overflowY: 'auto',
              pr: 1,
              '&::-webkit-scrollbar': {
                width: '6px',
              },
              '&::-webkit-scrollbar-track': {
                background: '#f1f1f1',
                borderRadius: '10px',
              },
              '&::-webkit-scrollbar-thumb': {
                background: '#888',
                borderRadius: '10px',
                '&:hover': {
                  background: '#555',
                }
              }
            }}>
              {topicDistribution
                .sort((a, b) => b.value - a.value)
                .map((topic, index) => {
                  const percentage = ((topic.value / totalPosts) * 100).toFixed(1);
                  const isTop3 = index < 3;
                  
                  return (
                    <Box 
                      key={topic.name} 
                      sx={{ 
                        mb: 2.5,
                        p: 2,
                        borderRadius: 2,
                        bgcolor: isTop3 ? 'action.hover' : 'transparent',
                        border: '1px solid',
                        borderColor: isTop3 ? getTopicColor(topic.name) + '40' : 'divider',
                        transition: 'all 0.3s',
                        position: 'relative',
                        overflow: 'hidden',
                        '&:hover': {
                          bgcolor: 'action.hover',
                          borderColor: getTopicColor(topic.name) + '60',
                          transform: 'translateX(4px)',
                          boxShadow: `0 4px 12px ${getTopicColor(topic.name)}30`,
                        }
                      }}
                    >
                      {/* Rank Badge */}
                      {isTop3 && (
                        <Box
                          sx={{
                            position: 'absolute',
                            top: 0,
                            right: 0,
                            bgcolor: getTopicColor(topic.name),
                            color: 'white',
                            px: 1.5,
                            py: 0.5,
                            borderBottomLeftRadius: 8,
                            fontSize: '0.7rem',
                            fontWeight: 'bold',
                          }}
                        >
                          #{index + 1}
                        </Box>
                      )}

                      {/* Topic Header */}
                      <Box display="flex" justifyContent="space-between" alignItems="center" mb={1.5}>
                        <Box display="flex" alignItems="center" gap={1.5}>
                          {!isTop3 && (
                            <Typography 
                              variant="caption" 
                              sx={{ 
                                width: 24,
                                height: 24,
                                display: 'flex',
                                alignItems: 'center',
                                justifyContent: 'center',
                                borderRadius: '50%',
                                bgcolor: 'action.selected',
                                fontWeight: 'bold',
                                fontSize: '0.7rem'
                              }}
                            >
                              {index + 1}
                            </Typography>
                          )}
                          <Box
                            sx={{
                              width: 16,
                              height: 16,
                              borderRadius: '50%',
                              bgcolor: getTopicColor(topic.name),
                              boxShadow: `0 2px 8px ${getTopicColor(topic.name)}60`,
                            }}
                          />
                          <Typography 
                            variant="body1" 
                            fontWeight={isTop3 ? 700 : 600}
                            sx={{ 
                              fontSize: isTop3 ? '1rem' : '0.95rem',
                              color: isTop3 ? 'primary.main' : 'text.primary'
                            }}
                          >
                            {topic.name}
                          </Typography>
                        </Box>
                        <Box textAlign="right">
                          <Typography 
                            variant="h6" 
                            fontWeight="bold" 
                            color="primary"
                            sx={{ fontSize: isTop3 ? '1.1rem' : '1rem' }}
                          >
                            {topic.value.toLocaleString()}
                          </Typography>
                          <Typography variant="caption" color="text.secondary" fontWeight="500">
                            {percentage}%
                          </Typography>
                        </Box>
                      </Box>

                      {/* Progress Bar */}
                      <Box sx={{ position: 'relative' }}>
                        <Box sx={{ 
                          bgcolor: 'grey.200', 
                          borderRadius: 1, 
                          height: isTop3 ? 12 : 10,
                          overflow: 'hidden',
                          boxShadow: 'inset 0 1px 3px rgba(0,0,0,0.1)'
                        }}>
                          <Box
                            sx={{
                              bgcolor: getTopicColor(topic.name),
                              height: '100%',
                              width: `${percentage}%`,
                              borderRadius: 1,
                              transition: 'width 0.6s cubic-bezier(0.4, 0, 0.2, 1)',
                              position: 'relative',
                              '&::after': {
                                content: '""',
                                position: 'absolute',
                                top: 0,
                                left: 0,
                                right: 0,
                                bottom: 0,
                                background: 'linear-gradient(90deg, transparent, rgba(255,255,255,0.3), transparent)',
                                animation: 'shimmer 2s infinite',
                              },
                              '@keyframes shimmer': {
                                '0%': { transform: 'translateX(-100%)' },
                                '100%': { transform: 'translateX(100%)' }
                              }
                            }}
                          />
                        </Box>
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
