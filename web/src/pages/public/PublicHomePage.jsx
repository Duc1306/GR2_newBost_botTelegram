/**
 * PublicHomePage – trang tin tức công khai, không cần đăng nhập.
 * Refactored: extracted sub-components to components/public/ and pages/public/tabs/
 */
import React, { useState, useEffect } from 'react';
import { Link, Link as RouterLink } from 'react-router-dom';
import {
  Box,
  Container,
  Typography,
  Chip,
  Button,
  useMediaQuery,
  useTheme,
  Tab,
  Tabs,
  Alert,
} from '@mui/material';
import LocalFireDepartmentIcon from '@mui/icons-material/LocalFireDepartment';
import BoltIcon from '@mui/icons-material/Bolt';
import NewspaperIcon from '@mui/icons-material/Newspaper';
import TwitterIcon from '@mui/icons-material/Twitter';
import PublicIcon from '@mui/icons-material/Public';
import LoginIcon from '@mui/icons-material/Login';
import PersonAddIcon from '@mui/icons-material/PersonAdd';
import TelegramIcon from '@mui/icons-material/Telegram';
import { fetchArticlePosts } from '../../lib/publicApi.js';
import NewsTicker from '../../components/public/NewsTicker.jsx';
import HotNewsTab from './tabs/HotNewsTab.jsx';
import ArticlesTab from './tabs/ArticlesTab.jsx';
import XSearchTab from './tabs/XSearchTab.jsx';
import StatsTab from './tabs/StatsTab.jsx';


// ─── Main Page ────────────────────────────────────────────────────────────────

export default function PublicHomePage() {
  const theme = useTheme();
  const isMobile = useMediaQuery(theme.breakpoints.down('sm'));
  const [activeTab, setActiveTab] = useState(0); // 0 = Hot News, 1 = Articles

  const [tickerPosts, setTickerPosts] = useState([]);

  useEffect(() => {
    const ac = new AbortController();
    fetchArticlePosts('', 0, 10, '', ac.signal)
      .then((d) => setTickerPosts(d.posts || []))
      .catch(() => {});
    return () => ac.abort();
  }, []);

  const tickerTexts = tickerPosts
    .map((p) => p.full_article?.title || p.text?.slice(0, 80))
    .filter(Boolean);

  return (
    <Box sx={{ minHeight: '100vh', bgcolor: '#f8fafc' }}>
      {/* ── Header ── */}
      <Box
        sx={{
          background: 'linear-gradient(135deg, #0f172a 0%, #1e3a5f 55%, #0f3460 100%)',
          color: 'white',
          py: { xs: 2, md: 3 },
          px: 2,
        }}
      >
        <Container maxWidth="lg">
          <Box display="flex" alignItems="center" justifyContent="space-between" flexWrap="wrap" gap={1}>
            <Box display="flex" alignItems="center" gap={1.5}>
              <LocalFireDepartmentIcon sx={{ fontSize: { xs: 28, md: 36 }, color: '#ff6b35' }} />
              <Box>
                <Typography variant="h5" fontWeight={800} letterSpacing={1.5} sx={{ fontSize: { xs: '1.1rem', md: '1.4rem' } }}>
                  📡 BẢNG TIN NÓNG
                </Typography>
                <Typography variant="caption" sx={{ opacity: 0.7, display: { xs: 'none', sm: 'block' } }}>
                  Tin tức thời sự quốc tế &amp; trong nước · AI tóm tắt · Cập nhật liên tục
                </Typography>
              </Box>
              <Chip
                label="● LIVE"
                size="small"
                sx={{
                  bgcolor: '#ef4444',
                  color: 'white',
                  fontWeight: 700,
                  fontSize: '0.68rem',
                  height: 22,
                  animation: 'livePulse 2s infinite',
                  '@keyframes livePulse': { '0%, 100%': { opacity: 1 }, '50%': { opacity: 0.55 } },
                }}
              />
            </Box>

            {/* Login / Register */}
            <Box display="flex" alignItems="center" gap={1}>
              <Button
                component={RouterLink}
                to="/login"
                variant="outlined"
                size="small"
                startIcon={<LoginIcon />}
                sx={{
                  color: 'white',
                  borderColor: 'rgba(255,255,255,0.5)',
                  '&:hover': { borderColor: 'white', bgcolor: 'rgba(255,255,255,0.1)' },
                  textTransform: 'none',
                  borderRadius: 2,
                }}
              >
                {isMobile ? null : 'Đăng nhập'}
              </Button>
              <Button
                component={RouterLink}
                to="/register"
                variant="contained"
                size="small"
                startIcon={<PersonAddIcon />}
                sx={{
                  bgcolor: '#f97316',
                  '&:hover': { bgcolor: '#ea580c' },
                  textTransform: 'none',
                  borderRadius: 2,
                }}
              >
                {isMobile ? null : 'Đăng ký'}
              </Button>
            </Box>
          </Box>
        </Container>
      </Box>

      {/* ── Breaking Ticker ── */}
      <NewsTicker items={tickerTexts} />

      {/* ── Tab bar ── */}
      <Box
        sx={{
          bgcolor: 'background.paper',
          borderBottom: '1px solid',
          borderColor: 'divider',
          position: 'sticky',
          top: 0,
          zIndex: 200,
          boxShadow: '0 2px 8px rgba(0,0,0,0.06)',
        }}
      >
        <Container maxWidth="lg" disableGutters>
          <Tabs
            value={activeTab}
            onChange={(_, v) => setActiveTab(v)}
            variant="scrollable"
            scrollButtons="auto"
            allowScrollButtonsMobile
            sx={{
              minHeight: 46,
              '& .MuiTab-root': { textTransform: 'none', fontWeight: 600, fontSize: '0.9rem', minHeight: 46 },
            }}
          >
            <Tab
              icon={<BoltIcon sx={{ fontSize: 18 }} />}
              iconPosition="start"
              label="Hot News"
              sx={{ color: activeTab === 0 ? '#f97316' : undefined }}
            />
            <Tab
              icon={<NewspaperIcon sx={{ fontSize: 18 }} />}
              iconPosition="start"
              label={isMobile ? 'Bài báo' : 'Bài báo theo chủ đề'}
            />
            <Tab
              icon={<TwitterIcon sx={{ fontSize: 18 }} />}
              iconPosition="start"
              label="Tìm trên X"
              sx={{ color: activeTab === 2 ? '#1d9bf0' : undefined }}
            />
            <Tab
              icon={<PublicIcon sx={{ fontSize: 18 }} />}
              iconPosition="start"
              label="Theo khu vực"
              sx={{ color: activeTab === 3 ? '#f97316' : undefined }}
            />
          </Tabs>
        </Container>
      </Box>

      {/* ── Main Content ── */}
      <Container maxWidth="lg" sx={{ py: { xs: 2, md: 3 } }}>
        {/* CTA Banner */}
        <Alert
          severity="info"
          icon={false}
          sx={{ mb: 3, borderRadius: 2, bgcolor: '#eff6ff', border: '1px solid #bfdbfe' }}
          action={
             <Button
              fullWidth
              variant="outlined"
              size="large"
              component={Link}
              to="/login/telegram"
              startIcon={<TelegramIcon />}
              sx={{
                py: 1.4,
                textTransform: 'none',
                fontSize: '0.95rem',
                borderColor: '#0088cc',
                color: '#0088cc',
                '&:hover': { borderColor: '#006699', bgcolor: '#f0f8ff' },
              }}
            >
              Đăng nhập bằng Số điện thoại Telegram
            </Button>
          }
        >
          <Typography variant="body2" fontWeight={600}>Muốn tóm tắt kênh Telegram cá nhân?</Typography>
          <Typography variant="caption" color="text.secondary">
            Tạo tài khoản và thêm kênh bạn muốn theo dõi — AI sẽ tóm tắt tự động.
          </Typography>
        </Alert>

        <Box sx={{ display: activeTab === 0 ? 'block' : 'none' }}><HotNewsTab /></Box>
        <Box sx={{ display: activeTab === 1 ? 'block' : 'none' }}><ArticlesTab /></Box>
        <Box sx={{ display: activeTab === 2 ? 'block' : 'none' }}><XSearchTab /></Box>
        <Box sx={{ display: activeTab === 3 ? 'block' : 'none' }}><StatsTab /></Box>

        {/* Footer */}
        <Box textAlign="center" py={3} mt={2} borderTop="1px solid" borderColor="divider">
          <Typography variant="caption" color="text.disabled">
            Bản tin tổng hợp từ Telegram · AI tóm tắt bởi OpenAI · {new Date().getFullYear()}
          </Typography>
        </Box>
      </Container>
    </Box>
  );
}

