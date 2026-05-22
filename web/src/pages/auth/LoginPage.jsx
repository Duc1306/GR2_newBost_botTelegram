import { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';
import {
  Box,
  CardContent,
  TextField,
  Button,
  Typography,
  Alert,
  Divider,
  Container,
  Paper,
  InputAdornment,
  IconButton,
  Chip,
} from '@mui/material';
import { Visibility, VisibilityOff, Lock, Person } from '@mui/icons-material';
import AdminPanelSettingsIcon from '@mui/icons-material/AdminPanelSettings';
import NewspaperIcon from '@mui/icons-material/Newspaper';
import TelegramIcon from '@mui/icons-material/Telegram';

export default function LoginPage() {
  const navigate = useNavigate();
  const { login } = useAuth();

  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setLoading(true);
    try {
      const result = await login(username, password);
      if (result.success) {
        navigate(result.role === 'admin' ? '/admin' : '/dashboard', { replace: true });
      } else {
        setError(result.error || 'Sai tên đăng nhập hoặc mật khẩu.');
      }
    } catch {
      setError('Đã xảy ra lỗi. Vui lòng thử lại.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <Box
      sx={{
        minHeight: '100vh',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
      }}
    >
      <Container maxWidth="sm">
        <Paper elevation={10} sx={{ borderRadius: 3, overflow: 'hidden' }}>
          {/* Header */}
          <Box
            sx={{
              background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
              color: 'white',
              py: 3,
              textAlign: 'center',
            }}
          >
            <Lock sx={{ fontSize: 48, mb: 1 }} />
            <Typography variant="h4" fontWeight="bold">
              MXH Aggregator
            </Typography>
            <Typography variant="body2" sx={{ opacity: 0.9, mt: 0.5 }}>
              Đăng nhập để tiếp tục
            </Typography>
          </Box>

          {/* Role hint chips */}
          <Box sx={{ px: 4, pt: 3, pb: 0 }}>
            <Stack direction="row" spacing={1} justifyContent="center">
              <Chip
                icon={<AdminPanelSettingsIcon />}
                label="Admin → Dashboard"
                size="small"
                variant="outlined"
                sx={{ fontSize: '0.75rem', color: '#764ba2', borderColor: '#764ba2' }}
              />
              <Chip
                icon={<NewspaperIcon />}
                label="User → Kênh theo dõi"
                size="small"
                variant="outlined"
                color="primary"
                sx={{ fontSize: '0.75rem' }}
              />
            </Stack>
          </Box>

          <CardContent sx={{ p: 4 }}>
            <form onSubmit={handleSubmit}>
              <TextField
                fullWidth
                label="Tên đăng nhập"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                margin="normal"
                required
                autoFocus
                InputProps={{
                  startAdornment: (
                    <InputAdornment position="start">
                      <Person />
                    </InputAdornment>
                  ),
                }}
              />

              <TextField
                fullWidth
                label="Mật khẩu"
                type={showPassword ? 'text' : 'password'}
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                autoComplete="current-password"
                margin="normal"
                required
                InputProps={{
                  startAdornment: (
                    <InputAdornment position="start">
                      <Lock />
                    </InputAdornment>
                  ),
                  endAdornment: (
                    <InputAdornment position="end">
                      <IconButton
                        onClick={() => setShowPassword(!showPassword)}
                        edge="end"
                      >
                        {showPassword ? <VisibilityOff /> : <Visibility />}
                      </IconButton>
                    </InputAdornment>
                  ),
                }}
              />

              {error && (
                <Alert severity="error" sx={{ mt: 2 }}>
                  {error}
                </Alert>
              )}

              <Button
                type="submit"
                fullWidth
                variant="contained"
                size="large"
                disabled={loading}
                sx={{
                  mt: 3,
                  py: 1.5,
                  background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
                  '&:hover': {
                    background: 'linear-gradient(135deg, #5568d3 0%, #663a8f 100%)',
                  },
                }}
              >
                {loading ? 'Đang đăng nhập...' : 'Đăng nhập'}
              </Button>
            </form>

            <Divider sx={{ my: 2 }}>hoặc</Divider>
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

            <Divider sx={{ my: 2 }} />
            <Typography variant="body2" align="center" color="text.secondary">
              Chưa có tài khoản?{' '}
              <Link to="/register" style={{ color: '#667eea', fontWeight: 600, textDecoration: 'none' }}>
                Đăng ký ngay
              </Link>
            </Typography>
            <Typography variant="body2" align="center" color="text.secondary" sx={{ mt: 0.5 }}>
              <Link to="/" style={{ color: '#667eea', textDecoration: 'none' }}>
                ← Xem tin tức công khai
              </Link>
            </Typography>
          </CardContent>
        </Paper>
      </Container>
    </Box>
  );
}
