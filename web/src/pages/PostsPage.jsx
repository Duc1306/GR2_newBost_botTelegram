import React, { useState, useEffect } from 'react';
import {
  Box,
  Typography,
  Grid,
  Paper,
  TextField,
  Select,
  MenuItem,
  FormControl,
  InputLabel,
  Chip,
  Pagination,
  CircularProgress,
  InputAdornment,
  Card,
  CardContent,
  LinearProgress,
} from '@mui/material';
import SearchIcon from '@mui/icons-material/Search';
import TelegramIcon from '@mui/icons-material/Telegram';
import TwitterIcon from '@mui/icons-material/Twitter';
import LinkIcon from '@mui/icons-material/Link';
import { usePosts, useTopics } from '../hooks/useApi.jsx';
import { getTopicColor } from '../theme/colors.jsx';
import { formatDistanceToNow } from 'date-fns';
import { vi } from 'date-fns/locale';

export default function PostsPage() {
  const [selectedTopic, setSelectedTopic] = useState('');
  const [selectedLang, setSelectedLang] = useState('');
  const [searchQuery, setSearchQuery] = useState('');
  const [debouncedSearch, setDebouncedSearch] = useState('');
  const [page, setPage] = useState(1);
  const postsPerPage = 20;

  const { data: topicsData } = useTopics();
  const { data: postsData, isLoading } = usePosts({
    topic: selectedTopic || undefined,
    lang: selectedLang || undefined,
    q: debouncedSearch || undefined,
    limit: postsPerPage,
    skip: (page - 1) * postsPerPage,
    link_only: true,
    topics_only: true,
  });

  // Debounce search
  useEffect(() => {
    const timer = setTimeout(() => {
      setDebouncedSearch(searchQuery);
      setPage(1);
    }, 500);
    return () => clearTimeout(timer);
  }, [searchQuery]);

  const posts = postsData || [];
  const topics = topicsData || [];
  const totalPages = Math.ceil(posts.length / postsPerPage);

  const handleTopicChange = (value) => {
    setSelectedTopic(value);
    setPage(1);
  };

  const handleLangChange = (value) => {
    setSelectedLang(value);
    setPage(1);
  };

  const handlePageChange = (event, value) => {
    setPage(value);
  };

  return (
    <Box>
      <Typography variant="h4" gutterBottom fontWeight="bold">
        📰 Posts Feed
      </Typography>
      <Typography variant="body1" color="text.secondary" paragraph>
        Browse and search posts with filters
      </Typography>

      {/* Filters */}
      <Paper sx={{ p: 2, mb: 3 }}>
        <Grid container spacing={2}>
          <Grid item xs={12} sm={6} md={4}>
            <TextField
              fullWidth
              size="small"
              placeholder="Search posts..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              InputProps={{
                startAdornment: (
                  <InputAdornment position="start">
                    <SearchIcon />
                  </InputAdornment>
                ),
              }}
            />
          </Grid>
          <Grid item xs={12} sm={3} md={2}>
            <FormControl fullWidth size="small">
              <InputLabel>Topic</InputLabel>
              <Select
                value={selectedTopic}
                label="Topic"
                onChange={(e) => handleTopicChange(e.target.value)}
              >
                <MenuItem value="">All Topics</MenuItem>
                {topics.map((topic) => (
                  <MenuItem key={topic} value={topic}>
                    {topic}
                  </MenuItem>
                ))}
              </Select>
            </FormControl>
          </Grid>
          <Grid item xs={12} sm={3} md={2}>
            <FormControl fullWidth size="small">
              <InputLabel>Language</InputLabel>
              <Select
                value={selectedLang}
                label="Language"
                onChange={(e) => handleLangChange(e.target.value)}
              >
                <MenuItem value="">All Languages</MenuItem>
                <MenuItem value="vi">Tiếng Việt</MenuItem>
                <MenuItem value="en">English</MenuItem>
              </Select>
            </FormControl>
          </Grid>
        </Grid>
      </Paper>

      {/* Posts List */}
      {isLoading ? (
        <Box display="flex" justifyContent="center" py={4}>
          <CircularProgress />
        </Box>
      ) : posts.length === 0 ? (
        <Paper sx={{ p: 4, textAlign: 'center' }}>
          <Typography color="text.secondary">No posts found</Typography>
        </Paper>
      ) : (
        <>
          <Grid container spacing={2}>
            {posts.map((post) => (
              <Grid item xs={12} key={post._id}>
                <Card>
                  <CardContent>
                    <Box display="flex" justifyContent="space-between" alignItems="flex-start" mb={1}>
                      <Box display="flex" alignItems="center" gap={1}>
                        {post.platform === 'telegram' ? (
                          <TelegramIcon sx={{ color: '#0088cc' }} />
                        ) : (
                          <TwitterIcon sx={{ color: '#1DA1F2' }} />
                        )}
                        <Typography variant="body2" color="text.secondary">
                          {post.source || 'Unknown'}
                        </Typography>
                        <Typography variant="body2" color="text.secondary">
                          •
                        </Typography>
                        <Typography variant="body2" color="text.secondary">
                          {post.date ? formatDistanceToNow(new Date(post.date), { addSuffix: true, locale: vi }) : 'Unknown date'}
                        </Typography>
                      </Box>
                      {post.link && (
                        <a href={post.link} target="_blank" rel="noopener noreferrer">
                          <LinkIcon sx={{ color: 'primary.main', fontSize: 20 }} />
                        </a>
                      )}
                    </Box>

                    {/* Topics */}
                    {post.topics && post.topics.length > 0 && (
                      <Box display="flex" gap={0.5} mb={1.5} flexWrap="wrap">
                        {post.topics.map((topic, idx) => (
                          <Chip
                            key={idx}
                            label={topic}
                            size="small"
                            sx={{
                              bgcolor: getTopicColor(topic),
                              color: 'white',
                              fontWeight: 500,
                              fontSize: '0.75rem',
                            }}
                          />
                        ))}
                      </Box>
                    )}

                    {/* Content */}
                    <Typography variant="body1" paragraph>
                      {post.text?.slice(0, 300)}
                      {post.text?.length > 300 && '...'}
                    </Typography>

                    {/* ML Confidence */}
                    {post.topic_predictions && post.topic_predictions.length > 0 && (
                      <Box>
                        <Box display="flex" justifyContent="space-between" alignItems="center" mb={0.5}>
                          <Typography variant="caption" color="text.secondary">
                            ML Confidence
                          </Typography>
                          <Typography variant="caption" color="text.secondary" fontWeight="bold">
                            {(post.topic_predictions[0].confidence * 100).toFixed(0)}%
                          </Typography>
                        </Box>
                        <LinearProgress 
                          variant="determinate" 
                          value={post.topic_predictions[0].confidence * 100}
                          sx={{ 
                            height: 6, 
                            borderRadius: 3,
                            bgcolor: 'grey.200',
                            '& .MuiLinearProgress-bar': {
                              bgcolor: getTopicColor(post.topic_predictions[0].topic),
                            },
                          }}
                        />
                      </Box>
                    )}
                  </CardContent>
                </Card>
              </Grid>
            ))}
          </Grid>

          {/* Pagination */}
          <Box display="flex" justifyContent="center" mt={4}>
            <Pagination
              count={totalPages}
              page={page}
              onChange={handlePageChange}
              color="primary"
              size="large"
            />
          </Box>
        </>
      )}
    </Box>
  );
}
