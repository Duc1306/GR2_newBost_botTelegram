import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Box,
  Container,
  Paper,
  Typography,
  TextField,
  Button,
  Avatar,
  Divider,
  Alert,
  Chip,
  Stack,
  CircularProgress,
  Tab,
  Tabs,
  AppBar,
  Toolbar,
  IconButton,
  Tooltip,
} from '@mui/material';
import ArrowBackIcon from '@mui/icons-material/ArrowBack';
import PersonIcon from '@mui/icons-material/Person';
import TelegramIcon from '@mui/icons-material/Telegram';
import LockIcon from '@mui/icons-material/Lock';
import SaveIcon from '@mui/icons-material/Save';
import NewspaperIcon from '@mui/icons-material/Newspaper';
import { useAuth } from '../../context/AuthContext';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

function TabPanel({ children, value, index }) {
  return value === index ? <Box sx={{ pt: 3 }}>{children}</Box> : null;
}

export default function ProfilePage() {
  const { user, token, updateUser } = useAuth();
  const navigate = useNavigate();

  const [tab, setTab] = useState(0);
  const [profile, setProfile] = useState(null);
  const [loadingProfile, setLoadingProfile] = useState(true);

  // Edit info state
  const [fullName, setFullName] = useState('');
  const [email, setEmail] = useState('');
  const [savingInfo, setSavingInfo] = useState(false);
  const [infoMsg, setInfoMsg] = useState(null); // { type, text }

  // Change password state
  const [currentPwd, setCurrentPwd] = useState('');
  const [newPwd, setNewPwd] = useState('');
  const [confirmPwd, setConfirmPwd] = useState('');
  const [savingPwd, setSavingPwd] = useState(false);
  const [pwdMsg, setPwdMsg] = useState(null);

  // Fetch profile from /auth/me
  useEffect(() => {
    if (!token) return;
    setLoadingProfile(true);
    fetch(`${API_BASE_URL}/auth/me`, {
      headers: { Authorization: `Bearer ${token}` },
    })
      .then((r) => r.json())
      .then((data) => {
        setProfile(data);
        setFullName(data.full_name || '');
        setEmail(data.email || '');
      })
      .catch(() => setProfile(null))
      .finally(() => setLoadingProfile(false));
  }, [token]);

  const handleSaveInfo = async (e) => {
    e.preventDefault();
    setSavingInfo(true);
    setInfoMsg(null);
    try {
      const res = await fetch(`${API_BASE_URL}/auth/profile`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({ full_name: fullName, email: email || null }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || 'Cập nhật thất bại.');
      setInfoMsg({ type: 'success', text: 'Cập nhật thông tin thành công.' });
      // Cập nhật AuthContext + localStorage để navbar hiện tên mới ngay lập tức
      updateUser({ full_name: fullName, email: email || undefined });
      setProfile((prev) => ({ ...prev, full_name: fullName, email }));
    } catch (err) {
      setInfoMsg({ type: 'error', text: err.message });
    } finally {
      setSavingInfo(false);
    }
  };

  const handleChangePassword = async (e) => {
    e.preventDefault();
    if (newPwd !== confirmPwd) {
      setPwdMsg({ type: 'error', text: 'Mật khẩu xác nhận không khớp.' });
      return;
    }
    if (newPwd.length < 6) {
      setPwdMsg({ type: 'error', text: 'Mật khẩu mới phải từ 6 ký tự trở lên.' });
      return;
    }
    setSavingPwd(true);
    setPwdMsg(null);
    try {
      const res = await fetch(`${API_BASE_URL}/settings/change-password`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({ current_password: currentPwd, new_password: newPwd }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || 'Đổi mật khẩu thất bại.');
      setPwdMsg({ type: 'success', text: 'Đổi mật khẩu thành công.' });
      setCurrentPwd('');
      setNewPwd('');
      setConfirmPwd('');
    } catch (err) {
      setPwdMsg({ type: 'error', text: err.message });
    } finally {
      setSavingPwd(false);
    }
  };

  const isTelegramOnly = profile && !profile.has_password;

  return (
    <Box sx={{ minHeight: '100vh', bgcolor: 'background.default' }}>
      {/* Navbar */}
      <AppBar position="sticky" elevation={0}
        sx={{ bgcolor: 'background.paper', borderBottom: '1px solid', borderColor: 'divider', color: 'text.primary' }}>
        <Toolbar>
          <Tooltip title="Quay lại">
            <IconButton edge="start" onClick={() => navigate(-1)} sx={{ mr: 1 }}>
              <ArrowBackIcon />
            </IconButton>
          </Tooltip>
          <NewspaperIcon sx={{ color: 'primary.main', mr: 1 }} />
          <Typography variant="h6" fontWeight={700} color="primary" sx={{ flexGrow: 1 }}>
            NewsBot
          </Typography>
          <Typography variant="body2" color="text.secondary">
            Hồ sơ cá nhân
          </Typography>
        </Toolbar>
      </AppBar>

      <Container maxWidth="sm" sx={{ py: 4 }}>
      <Paper elevation={3} sx={{ borderRadius: 3, overflow: 'hidden' }}>
        {/* Header */}
        <Box
          sx={{
            background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
            p: 4,
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            gap: 1.5,
          }}
        >
          <Avatar sx={{ width: 72, height: 72, bgcolor: 'rgba(255,255,255,0.3)', fontSize: 32 }}>
            {profile?.full_name?.[0]?.toUpperCase() || profile?.username?.[0]?.toUpperCase() || '?'}
          </Avatar>
          <Typography variant="h6" color="white" fontWeight={700}>
            {loadingProfile ? '...' : (profile?.full_name || profile?.username)}
          </Typography>
          <Stack direction="row" spacing={1}>
            <Chip
              label={profile?.role === 'admin' ? 'Quản trị viên' : 'Người dùng'}
              size="small"
              sx={{ bgcolor: 'rgba(255,255,255,0.25)', color: 'white', fontWeight: 600 }}
            />
            {profile?.telegram_linked && (
              <Chip
                icon={<TelegramIcon sx={{ fontSize: 14, color: 'white !important' }} />}
                label="Telegram"
                size="small"
                sx={{ bgcolor: 'rgba(255,255,255,0.25)', color: 'white', fontWeight: 600 }}
              />
            )}
            {isTelegramOnly && (
              <Chip
                label="Đăng nhập Telegram"
                size="small"
                sx={{ bgcolor: 'rgba(255,255,255,0.15)', color: 'white' }}
              />
            )}
          </Stack>
        </Box>

        {loadingProfile ? (
          <Box display="flex" justifyContent="center" p={4}>
            <CircularProgress />
          </Box>
        ) : (
          <>
            <Box sx={{ borderBottom: 1, borderColor: 'divider', px: 2 }}>
              <Tabs value={tab} onChange={(_, v) => setTab(v)}>
                <Tab icon={<PersonIcon fontSize="small" />} iconPosition="start" label="Thông tin" />
                {!isTelegramOnly && (
                  <Tab icon={<LockIcon fontSize="small" />} iconPosition="start" label="Đổi mật khẩu" />
                )}
              </Tabs>
            </Box>

            <Box sx={{ p: 3 }}>
              {/* Tab: Thông tin */}
              <TabPanel value={tab} index={0}>
                {/* Read-only info */}
                <Stack spacing={1.5} mb={3}>
                  <Box>
                    <Typography variant="caption" color="text.secondary">Tên đăng nhập</Typography>
                    <Typography variant="body1" fontWeight={600}>{profile?.username}</Typography>
                  </Box>
                  {profile?.telegram_username && (
                    <Box>
                      <Typography variant="caption" color="text.secondary">Telegram</Typography>
                      <Typography variant="body1">@{profile.telegram_username}</Typography>
                    </Box>
                  )}
                  {profile?.phone_number && (
                    <Box>
                      <Typography variant="caption" color="text.secondary">Số điện thoại</Typography>
                      <Typography variant="body1">{profile.phone_number}</Typography>
                    </Box>
                  )}
                </Stack>

                <Divider sx={{ mb: 3 }} />

                <form onSubmit={handleSaveInfo}>
                  <Stack spacing={2}>
                    <TextField
                      label="Họ và tên"
                      value={fullName}
                      onChange={(e) => setFullName(e.target.value)}
                      fullWidth
                      required
                      inputProps={{ maxLength: 100 }}
                    />
                    <TextField
                      label="Email"
                      type="email"
                      value={email}
                      onChange={(e) => setEmail(e.target.value)}
                      fullWidth
                      placeholder="Không bắt buộc"
                    />
                    {infoMsg && (
                      <Alert severity={infoMsg.type} onClose={() => setInfoMsg(null)}>
                        {infoMsg.text}
                      </Alert>
                    )}
                    <Button
                      type="submit"
                      variant="contained"
                      startIcon={savingInfo ? <CircularProgress size={16} color="inherit" /> : <SaveIcon />}
                      disabled={savingInfo}
                    >
                      Lưu thay đổi
                    </Button>
                  </Stack>
                </form>
              </TabPanel>

              {/* Tab: Đổi mật khẩu (only regular accounts) */}
              {!isTelegramOnly && (
                <TabPanel value={tab} index={1}>
                  <form onSubmit={handleChangePassword}>
                    <Stack spacing={2}>
                      <TextField
                        label="Mật khẩu hiện tại"
                        type="password"
                        value={currentPwd}
                        onChange={(e) => setCurrentPwd(e.target.value)}
                        fullWidth
                        required
                        autoComplete="current-password"
                      />
                      <TextField
                        label="Mật khẩu mới"
                        type="password"
                        value={newPwd}
                        onChange={(e) => setNewPwd(e.target.value)}
                        fullWidth
                        required
                        autoComplete="new-password"
                        helperText="Tối thiểu 6 ký tự"
                      />
                      <TextField
                        label="Xác nhận mật khẩu mới"
                        type="password"
                        value={confirmPwd}
                        onChange={(e) => setConfirmPwd(e.target.value)}
                        fullWidth
                        required
                        autoComplete="new-password"
                        error={confirmPwd.length > 0 && confirmPwd !== newPwd}
                        helperText={confirmPwd.length > 0 && confirmPwd !== newPwd ? 'Không khớp' : ''}
                      />
                      {pwdMsg && (
                        <Alert severity={pwdMsg.type} onClose={() => setPwdMsg(null)}>
                          {pwdMsg.text}
                        </Alert>
                      )}
                      <Button
                        type="submit"
                        variant="contained"
                        color="warning"
                        startIcon={savingPwd ? <CircularProgress size={16} color="inherit" /> : <LockIcon />}
                        disabled={savingPwd}
                      >
                        Đổi mật khẩu
                      </Button>
                    </Stack>
                  </form>
                </TabPanel>
              )}
            </Box>
          </>
        )}
      </Paper>
      </Container>
    </Box>
  );
}
