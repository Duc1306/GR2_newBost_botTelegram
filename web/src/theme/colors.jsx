// Topic Colors (consistent across dashboard)
export const topicColors = {
  'Crypto': '#F7931A',           // Bitcoin orange
  'Chính trị': '#DC143C',        // Red
  'Công nghệ': '#1E90FF',        // Blue
  'Kinh tế': '#228B22',          // Green
  'Thể thao': '#FF6347',         // Tomato
  'Giải trí': '#9370DB',         // Purple
  'Sức khỏe': '#FF1493',         // Deep pink
  'Giáo dục': '#4169E1',         // Royal blue
  'Du lịch': '#20B2AA',          // Light sea green
  'Ẩm thực': '#FF8C00',          // Dark orange
};

// Status Colors
export const statusColors = {
  success: '#4CAF50',
  warning: '#FF9800',
  error: '#F44336',
  info: '#2196F3',
};

// Platform Colors
export const platformColors = {
  telegram: '#0088cc',
  twitter: '#1DA1F2',
};

// Trend Indicators
export const trendColors = {
  up: '#4CAF50',
  down: '#F44336',
  stable: '#9E9E9E',
};

// Get color by topic name
export const getTopicColor = (topicName) => {
  return topicColors[topicName] || '#9E9E9E';
};

// Get trend color based on percentage
export const getTrendColor = (percentage) => {
  if (percentage > 5) return trendColors.up;
  if (percentage < -5) return trendColors.down;
  return trendColors.stable;
};

// Chart color palette (for multiple series)
export const chartColorPalette = [
  '#F7931A', '#DC143C', '#1E90FF', '#228B22', '#FF6347',
  '#9370DB', '#FF1493', '#4169E1', '#20B2AA', '#FF8C00',
];
