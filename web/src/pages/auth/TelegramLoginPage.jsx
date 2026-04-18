import { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';
import {
  Box, Container, Paper, Typography, TextField, Button,
  Alert, InputAdornment, Stepper, Step, StepLabel,
  CircularProgress, Divider,
} from '@mui/material';
import {
  Phone, Lock, Person, Telegram as TelegramIcon,
} from '@mui/icons-material';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

const STEPS = ['Nhập số điện thoại', 'Xác minh OTP'];

export default function TelegramLoginPage() {
  const navigate = useNavigate();
  const { loginWithTelegram } = useAuth();

  const [activeStep, setActiveStep] = useState(0);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  // Step 1
  const [phoneNumber, setPhoneNumber] = useState('');
  const [displayName, setDisplayName] = useState('');
  const [isReturningUser, setIsReturningUser] = useState(false);

  // Step 2
  const [sessionId, setSessionId] = useState('');
  const [phoneCodeHash, setPhoneCodeHash] = useState('');
  const [otpCode, setOtpCode] = useState('');
  const [needs2FA, setNeeds2FA] = useState(false);
  const [password2FA, setPassword2FA] = useState('');

  // ─── Step 1: Send OTP ─────────────────────────────────────
  const handleSendCode = async (e) => {
    e.preventDefault();
    setError('');
    setLoading(true);
    try {
      const res = await fetch(`${API_BASE_URL}/auth/telegram/send-code`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          phone_number: phoneNumber.trim(),
          display_name: displayName.trim() || undefined,
        }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || 'Gửi mã OTP thất bại');
      setSessionId(data.session_id);
      setPhoneCodeHash(data.phone_code_hash);
      if (data.user_exists) {
        setIsReturningUser(true);
        if (data.display_name) setDisplayName(data.display_name);
      }
      setActiveStep(1);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  // ─── Step 2: Verify OTP ───────────────────────────────────
  const handleVerifyCode = async (e) => {
    e.preventDefault();
    setError('');
    setLoading(true);
    try {
      const body = {
        session_id: sessionId,
        phone_number: phoneNumber.trim(),
        phone_code_hash: phoneCodeHash,
        code: otpCode.trim(),
      };
      if (needs2FA && password2FA) body.password = password2FA;

      const res = await fetch(`${API_BASE_URL}/auth/telegram/verify-code`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      });
      const data = await res.json();

      if (res.status === 428) {
        setNeeds2FA(true);
        setError(data.detail);
        setLoading(false);
        return;
      }
      if (!res.ok) throw new Error(data.detail || 'Xác minh OTP thất bại');

      // Login and go straight to dashboard
      await loginWithTelegram(data);
      navigate('/dashboard', { replace: true });
    } catch (err) {
      setError(err.message);
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
        background: 'linear-gradient(135deg, #0088cc 0%, #005b8c 100%)',
        py: 4,
      }}
    >
      <Container maxWidth="sm">
        <Paper elevation={10} sx={{ borderRadius: 3, overflow: 'hidden' }}>
          {/* Header */}
          <Box
            sx={{
              background: 'linear-gradient(135deg, #0088cc 0%, #005b8c 100%)',
              color: 'white',
              py: 3,
              textAlign: 'center',
            }}
          >
            <TelegramIcon sx={{ fontSize: 48, mb: 1 }} />
            <Typography variant="h4" fontWeight="bold">
              Đăng nhập Telegram
            </Typography>
            <Typography variant="body2" sx={{ opacity: 0.9, mt: 0.5 }}>
              Kết nối số điện thoại để đăng nhập nhanh
            </Typography>
          </Box>

          {/* Stepper */}
          <Box sx={{ px: 3, pt: 3 }}>
            <Stepper activeStep={activeStep} alternativeLabel>
              {STEPS.map((label) => (
                <Step key={label}>
                  <StepLabel>{label}</StepLabel>
                </Step>
              ))}
            </Stepper>
          </Box>

          <Box sx={{ p: 4 }}>
            {/* ─── Step 1: Phone Number ─────────────────────── */}
            {activeStep === 0 && (
              <form onSubmit={handleSendCode}>
                <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
                  Nhập số điện thoại Telegram. Hệ thống sẽ gửi mã OTP qua ứng dụng Telegram.
                </Typography>

                {isReturningUser && (
                  <Alert severity="success" sx={{ mb: 2 }}>
                    Xin chào lại, <strong>{displayName}</strong>! Chỉ cần xác minh OTP để đăng nhập.
                  </Alert>
                )}

                <TextField
                  fullWidth
                  label="Số điện thoại *"
                  value={phoneNumber}
                  onChange={(e) => setPhoneNumber(e.target.value)}
                  margin="normal"
                  required
                  autoFocus
                  placeholder="+84912345678"
                  helperText="Định dạng quốc tế, VD: +84912345678"
                  InputProps={{
                    startAdornment: (
                      <InputAdornment position="start"><Phone /></InputAdornment>
                    ),
                  }}
                />

                {!isReturningUser && (
                  <TextField
                    fullWidth
                    label="Tên hiển thị"
                    value={displayName}
                    onChange={(e) => setDisplayName(e.target.value)}
                    margin="normal"
                    placeholder="Nguyễn Văn A"
                    helperText="Tên sẽ hiển thị trong ứng dụng (tùy chọn)"
                    InputProps={{
                      startAdornment: (
                        <InputAdornment position="start"><Person /></InputAdornment>
                      ),
                    }}
                  />
                )}

                {error && <Alert severity="error" sx={{ mt: 2 }}>{error}</Alert>}

                <Button
                  type="submit"
                  fullWidth
                  variant="contained"
                  size="large"
                  disabled={loading || !phoneNumber.trim()}
                  sx={{
                    mt: 3, py: 1.5,
                    background: 'linear-gradient(135deg, #0088cc 0%, #005b8c 100%)',
                    '&:hover': { background: 'linear-gradient(135deg, #0077b5 0%, #004a75 100%)' },
                  }}
                >
                  {loading ? <CircularProgress size={24} color="inherit" /> : 'Gửi mã OTP'}
                </Button>
              </form>
            )}

            {/* ─── Step 2: OTP Verification ─────────────────── */}
            {activeStep === 1 && (
              <form onSubmit={handleVerifyCode}>
                <Alert severity="info" sx={{ mb: 2 }}>
                  Mã OTP đã được gửi tới Telegram trên số <strong>{phoneNumber}</strong>.
                  Kiểm tra ứng dụng Telegram để lấy mã.
                </Alert>

                <TextField
                  fullWidth
                  label="Mã OTP *"
                  value={otpCode}
                  onChange={(e) => setOtpCode(e.target.value)}
                  margin="normal"
                  required
                  autoFocus
                  placeholder="12345"
                  inputProps={{ maxLength: 8 }}
                  InputProps={{
                    startAdornment: (
                      <InputAdornment position="start"><Lock /></InputAdornment>
                    ),
                  }}
                />

                {needs2FA && (
                  <TextField
                    fullWidth
                    label="Mật khẩu 2FA *"
                    type="password"
                    value={password2FA}
                    onChange={(e) => setPassword2FA(e.target.value)}
                    margin="normal"
                    required
                    helperText="Tài khoản bật xác thực 2 lớp"
                    InputProps={{
                      startAdornment: (
                        <InputAdornment position="start"><Lock /></InputAdornment>
                      ),
                    }}
                  />
                )}

                {error && <Alert severity="error" sx={{ mt: 2 }}>{error}</Alert>}

                <Button
                  type="submit"
                  fullWidth
                  variant="contained"
                  size="large"
                  disabled={loading || !otpCode.trim()}
                  sx={{
                    mt: 3, py: 1.5,
                    background: 'linear-gradient(135deg, #0088cc 0%, #005b8c 100%)',
                    '&:hover': { background: 'linear-gradient(135deg, #0077b5 0%, #004a75 100%)' },
                  }}
                >
                  {loading ? <CircularProgress size={24} color="inherit" /> : 'Xác minh'}
                </Button>
              </form>
            )}

            <Divider sx={{ my: 3 }} />
            <Typography variant="body2" align="center" color="text.secondary">
              <Link to="/login" style={{ color: '#0088cc', fontWeight: 600, textDecoration: 'none' }}>
                ← Đăng nhập bằng tài khoản
              </Link>
            </Typography>
            <Typography variant="body2" align="center" color="text.secondary" sx={{ mt: 0.5 }}>
              <Link to="/" style={{ color: '#0088cc', textDecoration: 'none' }}>
                Xem tin tức công khai
              </Link>
            </Typography>
          </Box>
        </Paper>
      </Container>
    </Box>
  );
}
