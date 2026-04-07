import { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';
import {
  Box, Container, Paper, Typography, TextField, Button,
  Alert, InputAdornment, IconButton, Divider,
} from '@mui/material';
import {
  Visibility, VisibilityOff, Lock, Person, Email, BadgeOutlined,
} from '@mui/icons-material';
import NewspaperIcon from '@mui/icons-material/Newspaper';

export default function RegisterPage() {
  const navigate = useNavigate();
  const { register } = useAuth();

  const [form, setForm] = useState({
    username: '', password: '', confirmPassword: '', email: '', full_name: '',
  });
  const [showPwd, setShowPwd] = useState(false);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const handleChange = (e) => setForm((f) => ({ ...f, [e.target.name]: e.target.value }));

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    if (form.password !== form.confirmPassword) {
      setError('Mật khẩu xác nhận không khớp.');
      return;
    }
    setLoading(true);
    try {
      const result = await register({
        username: form.username,
        password: form.password,
        email: form.email || undefined,
        full_name: form.full_name || undefined,
      });
      if (result.success) {
        navigate('/news', { replace: true });
      } else {
        setError(result.error || 'Đăng ký thất bại.');
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
            <NewspaperIcon sx={{ fontSize: 48, mb: 1 }} />
            <Typography variant="h4" fontWeight="bold">
              Tạo tài khoản
            </Typography>
            <Typography variant="body2" sx={{ opacity: 0.9, mt: 0.5 }}>
              Đăng ký để đọc tin tức tổng hợp
            </Typography>
          </Box>

          <Box sx={{ p: 4 }}>
            <form onSubmit={handleSubmit}>
              {/* Username */}
              <TextField
                fullWidth name="username" label="Tên đăng nhập *"
                value={form.username} onChange={handleChange}
                margin="normal" required autoFocus
                helperText="3–32 ký tự, chỉ gồm chữ, số, _ . -"
                InputProps={{
                  startAdornment: <InputAdornment position="start"><Person /></InputAdornment>,
                }}
              />

              {/* Full name */}
              <TextField
                fullWidth name="full_name" label="Họ và tên"
                value={form.full_name} onChange={handleChange}
                margin="normal"
                InputProps={{
                  startAdornment: <InputAdornment position="start"><BadgeOutlined /></InputAdornment>,
                }}
              />

              {/* Email */}
              <TextField
                fullWidth name="email" label="Email" type="email"
                value={form.email} onChange={handleChange}
                margin="normal"
                InputProps={{
                  startAdornment: <InputAdornment position="start"><Email /></InputAdornment>,
                }}
              />

              {/* Password */}
              <TextField
                fullWidth name="password" label="Mật khẩu *"
                type={showPwd ? 'text' : 'password'}
                value={form.password} onChange={handleChange}
                autoComplete="new-password"
                margin="normal" required
                helperText="Tối thiểu 6 ký tự"
                InputProps={{
                  startAdornment: <InputAdornment position="start"><Lock /></InputAdornment>,
                  endAdornment: (
                    <InputAdornment position="end">
                      <IconButton onClick={() => setShowPwd((v) => !v)} edge="end">
                        {showPwd ? <VisibilityOff /> : <Visibility />}
                      </IconButton>
                    </InputAdornment>
                  ),
                }}
              />

              {/* Confirm password */}
              <TextField
                fullWidth name="confirmPassword" label="Xác nhận mật khẩu *"
                type={showPwd ? 'text' : 'password'}
                value={form.confirmPassword} onChange={handleChange}
                autoComplete="new-password"
                margin="normal" required
                InputProps={{
                  startAdornment: <InputAdornment position="start"><Lock /></InputAdornment>,
                }}
              />

              {error && <Alert severity="error" sx={{ mt: 2 }}>{error}</Alert>}

              <Button
                type="submit" fullWidth variant="contained" size="large"
                disabled={loading}
                sx={{
                  mt: 3, py: 1.5,
                  background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
                  '&:hover': { background: 'linear-gradient(135deg, #5568d3 0%, #663a8f 100%)' },
                }}
              >
                {loading ? 'Đang đăng ký...' : 'Đăng ký'}
              </Button>
            </form>

            <Divider sx={{ my: 3 }} />
            <Typography variant="body2" align="center" color="text.secondary">
              Đã có tài khoản?{' '}
              <Link to="/login" style={{ color: '#667eea', fontWeight: 600, textDecoration: 'none' }}>
                Đăng nhập
              </Link>
            </Typography>
          </Box>
        </Paper>
      </Container>
    </Box>
  );
}
