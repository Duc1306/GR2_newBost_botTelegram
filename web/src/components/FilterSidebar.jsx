import React, { memo, useMemo } from 'react';
import Drawer from '@mui/material/Drawer';
import List from '@mui/material/List';
import ListItem from '@mui/material/ListItem';
import ListItemButton from '@mui/material/ListItemButton';
import ListItemIcon from '@mui/material/ListItemIcon';
import ListItemText from '@mui/material/ListItemText';
import Chip from '@mui/material/Chip';
import Typography from '@mui/material/Typography';
import Select from '@mui/material/Select';
import MenuItem from '@mui/material/MenuItem';
import Box from '@mui/material/Box';
import Divider from '@mui/material/Divider';
import ArticleIcon from '@mui/icons-material/Article';
import MonetizationOnIcon from '@mui/icons-material/MonetizationOn';
import ComputerIcon from '@mui/icons-material/Computer';
import CurrencyBitcoinIcon from '@mui/icons-material/CurrencyBitcoin';
import AccountBalanceIcon from '@mui/icons-material/AccountBalance';
import SportsSoccerIcon from '@mui/icons-material/SportsSoccer';
import MovieIcon from '@mui/icons-material/Movie';
import LocalHospitalIcon from '@mui/icons-material/LocalHospital';
import SchoolIcon from '@mui/icons-material/School';
import FlightIcon from '@mui/icons-material/Flight';
import RestaurantIcon from '@mui/icons-material/Restaurant';

const TOPIC_ICONS = {
  'Kinh tế': <MonetizationOnIcon fontSize="small" />,
  'Công nghệ': <ComputerIcon fontSize="small" />,
  'Crypto': <CurrencyBitcoinIcon fontSize="small" />,
  'Chính trị': <AccountBalanceIcon fontSize="small" />,
  'Thể thao': <SportsSoccerIcon fontSize="small" />,
  'Giải trí': <MovieIcon fontSize="small" />,
  'Sức khỏe': <LocalHospitalIcon fontSize="small" />,
  'Giáo dục': <SchoolIcon fontSize="small" />,
  'Du lịch': <FlightIcon fontSize="small" />,
  'Ẩm thực': <RestaurantIcon fontSize="small" />,
};

export const FilterSidebar = memo(function FilterSidebar({
  topics,
  selectedTopic,
  onTopicChange,
  languages,
  selectedLanguage,
  onLanguageChange,
  stats,
}) {
  const safeTopics = useMemo(() => Array.isArray(topics) ? topics : [], [topics]);
  const safeLanguages = useMemo(() => Array.isArray(languages) ? languages : [], [languages]);

  return (
    <Drawer
      variant="permanent"
      anchor="left"
      PaperProps={{ sx: { width: 320, bgcolor: 'background.paper', borderRight: 1, borderColor: 'divider' } }}
    >
      <Box sx={{ p: 2, display: 'flex', flexDirection: 'column', height: '100%' }}>
        {/* Header */}
        <Box sx={{ mb: 2, display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <Box>
            <Typography variant="h5" fontWeight={600} color="text.primary">NewsBot</Typography>
            <Typography variant="body2" color="text.secondary">Tổng hợp tin tức từ Telegram</Typography>
          </Box>
          <Box textAlign="right">
            {stats && (
              <Typography variant="caption" color="text.secondary">
                {(selectedTopic && stats.by_topic?.[selectedTopic] !== undefined
                  ? stats.by_topic[selectedTopic]
                  : stats.total_posts
                ).toLocaleString()} bài
              </Typography>
            )}
          </Box>
        </Box>
        <Divider sx={{ mb: 2 }} />

        {/* Topic Filter */}
        <Typography variant="subtitle2" color="text.primary" sx={{ mb: 1, textTransform: 'uppercase', letterSpacing: 1 }}>Chủ đề</Typography>
        <List dense disablePadding sx={{ mb: 2 }}>
          <ListItem disablePadding>
            <ListItemButton
              selected={!selectedTopic}
              onClick={() => onTopicChange(undefined)}
              sx={{ borderRadius: 2, mb: 0.5 }}
            >
              <ListItemIcon sx={{ minWidth: 32 }}><ArticleIcon fontSize="small" /></ListItemIcon>
              <ListItemText primary="Tất cả" />
              <Chip label={stats ? stats.total_posts.toLocaleString() : ''} size="small" sx={{ ml: 1 }} />
            </ListItemButton>
          </ListItem>
          {safeTopics.map((topic) => (
            <ListItem key={topic} disablePadding>
              <ListItemButton
                selected={selectedTopic === topic}
                onClick={() => onTopicChange(topic)}
                sx={{ borderRadius: 2, mb: 0.5 }}
              >
                <ListItemIcon sx={{ minWidth: 32 }}>{TOPIC_ICONS[topic] || <ArticleIcon fontSize="small" />}</ListItemIcon>
                <ListItemText primary={topic} />
                <Chip label={stats?.by_topic && stats.by_topic[topic] !== undefined ? stats.by_topic[topic] : ''} size="small" sx={{ ml: 1 }} />
              </ListItemButton>
            </ListItem>
          ))}
        </List>

        {/* Language Filter */}
        <Typography variant="subtitle2" color="text.primary" sx={{ mb: 1, textTransform: 'uppercase', letterSpacing: 1 }}>Ngôn ngữ</Typography>
        <Select
          value={selectedLanguage || ''}
          onChange={(e) => onLanguageChange(e.target.value || undefined)}
          displayEmpty
          size="small"
          fullWidth
          sx={{ mb: 2, borderRadius: 2 }}
          renderValue={(value) => {
            if (!value) return '🌍 Tất cả';
            if (value === 'vi') return '🇻🇳 Tiếng Việt';
            if (value === 'en') return '🇬🇧 English';
            return `🌐 ${value}`;
          }}
        >
          <MenuItem value="">🌍 Tất cả ({stats?.total_posts || 0})</MenuItem>
          {safeLanguages.map((lang) => {
            const langName = lang === 'vi' ? '🇻🇳 Tiếng Việt' : lang === 'en' ? '🇬🇧 English' : `🌐 ${lang}`;
            const count = stats?.by_language[lang] || 0;
            return (
              <MenuItem key={lang} value={lang}>
                {langName} ({count.toLocaleString()})
              </MenuItem>
            );
          })}
        </Select>

        <Box sx={{ flexGrow: 1 }} />
        <Divider sx={{ mb: 2 }} />
        {/* Footer */}
        <Typography variant="caption" color="text.secondary" sx={{ mb: 1 }}>
          Dữ liệu cập nhật tự động từ Telegram
        </Typography>
        <Typography variant="caption" color="primary">
          <a href="http://localhost:8000/docs" target="_blank" rel="noopener noreferrer" style={{ textDecoration: 'underline' }}>
            API Documentation →
          </a>
        </Typography>
      </Box>
    </Drawer>
  );
});
