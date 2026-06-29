import { useState, useEffect, useCallback } from 'react';
import {
  Box,
  Container,
  Paper,
  Tabs,
  Tab,
  Typography,
  TextField,
  Button,
  Switch,
  FormControlLabel,
  Slider,
  Alert,
  Divider,
  Grid,
  Select,
  MenuItem,
  FormControl,
  InputLabel
} from '@mui/material';
import { useTheme } from '../../context/ThemeContext.jsx';
import {
  Person as PersonIcon,
  Palette as PaletteIcon,
  Notifications as NotificationsIcon,
  DataUsage as DataIcon,
  SmartToy as AIIcon,
  LightMode as LightModeIcon,
  DarkMode as DarkModeIcon
} from '@mui/icons-material';
import { api } from '../../lib/api.jsx';
import OperationsPanel from './OperationsPanel.jsx';

function TabPanel({ children, value, index }) {
  return (
    <div style={{ display: value === index ? 'block' : 'none' }}>
      <Box sx={{ p: 3 }}>{children}</Box>
    </div>
  );
}

export default function SettingsPage() {
  const { mode, toggleTheme } = useTheme();
  const [tabValue, setTabValue] = useState(0);
  const [settings, setSettings] = useState(null);
  const [loading, setLoading] = useState(true);
  const [success, setSuccess] = useState('');
  const [error, setError] = useState('');
  
  // Password change
  const [currentPassword, setCurrentPassword] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');

  const fetchSettings = useCallback(async (signal) => {
    try {
      const { data } = await api.get('/settings', { signal });
      setSettings(data);
    } catch (err) {
      if (err.name !== 'AbortError') {
        setError(err?.message || 'Failed to load settings');
      }
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    const controller = new AbortController();
    fetchSettings(controller.signal);
    return () => controller.abort();
  }, [fetchSettings]);

  const updateSettings = useCallback(async (updates) => {
    try {
      await api.put('/settings', updates);
      setSuccess('Settings updated successfully!');
      setTimeout(() => setSuccess(''), 3000);
      fetchSettings();
    } catch (err) {
      setError(err?.message || 'Failed to update settings');
    }
  }, [fetchSettings]);

  const handlePasswordChange = useCallback(async () => {
    if (newPassword !== confirmPassword) {
      setError('New passwords do not match');
      return;
    }
    if (newPassword.length < 8) {
      setError('Password must be at least 8 characters');
      return;
    }
    try {
      await api.post('/settings/change-password', {
        current_password: currentPassword,
        new_password: newPassword,
      });
      setSuccess('Password changed successfully!');
      setCurrentPassword('');
      setNewPassword('');
      setConfirmPassword('');
    } catch (err) {
      try {
        const detail = JSON.parse(err.message)?.detail;
        setError(detail || 'Failed to change password');
      } catch {
        setError(err?.message || 'Failed to change password');
      }
    }
  }, [currentPassword, newPassword, confirmPassword]);

  const handleTabChange = useCallback((_, newValue) => setTabValue(newValue), []);
  const handleThemeChange = useCallback((e) => {
    if (e.target.value !== mode) { toggleTheme(); updateSettings({ theme: e.target.value }); }
  }, [mode, toggleTheme, updateSettings]);
  const handleNotificationsChange = useCallback((e) => {
    const enabled = e.target.checked;
    setSettings(prev => ({ ...prev, notifications_enabled: enabled }));
    updateSettings({ notifications_enabled: enabled });
  }, [updateSettings]);
  const handleEmailNotifChange = useCallback((e) => {
    const enabled = e.target.checked;
    setSettings(prev => ({ ...prev, email_notifications: enabled }));
    updateSettings({ email_notifications: enabled });
  }, [updateSettings]);
  const handleTelegramChange = useCallback((e) => {
    const enabled = e.target.checked;
    setSettings(prev => ({ ...prev, telegram_enabled: enabled }));
    updateSettings({ telegram_enabled: enabled });
  }, [updateSettings]);
  const handleMLChange = useCallback((e) => {
    const enabled = e.target.checked;
    setSettings(prev => ({ ...prev, ml_auto_classify: enabled }));
    updateSettings({ ml_auto_classify: enabled });
  }, [updateSettings]);

  if (loading) return <Box>Loading...</Box>;
  if (!settings) return <Box>Error loading settings</Box>;

  return (
    <Container maxWidth="lg">
      <Box sx={{ mb: 4 }}>
        <Typography variant="h4" fontWeight="bold">
          Settings
        </Typography>
        <Typography variant="body2" color="text.secondary">
          Manage your account and application preferences
        </Typography>
      </Box>

      {success && <Alert severity="success" sx={{ mb: 2 }}>{success}</Alert>}
      {error && <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError('')}>{error}</Alert>}

      <Paper sx={{ width: '100%' }}>
        <Tabs
          value={tabValue}
          onChange={handleTabChange}
          variant="scrollable"
          scrollButtons="auto"
        >
          <Tab icon={<PersonIcon />} label="Account" />
          <Tab icon={<PaletteIcon />} label="Appearance" />
          <Tab icon={<NotificationsIcon />} label="Notifications" />
          <Tab icon={<DataIcon />} label="Data Collection" />
          <Tab icon={<AIIcon />} label="ML Settings" />
        </Tabs>

        {/* Account Tab */}
        <TabPanel value={tabValue} index={0}>
          <Typography variant="h6" gutterBottom>Account Information</Typography>
          <Box sx={{ mb: 3 }}>
            <TextField
              fullWidth
              label="Username"
              value={settings.username}
              disabled
              sx={{ mb: 2 }}
            />
          </Box>

          <Divider sx={{ my: 3 }} />

          <Typography variant="h6" gutterBottom>Change Password</Typography>
          <Box sx={{ maxWidth: 400, display: 'flex', gap: 2, alignItems: 'flex-end' }}>
            <TextField
              size="small"
              type="password"
              label="Current"
              value={currentPassword}
              onChange={(e) => setCurrentPassword(e.target.value)}
              sx={{ flex: 1 }}
            />
            <TextField
              size="small"
              type="password"
              label="New"
              value={newPassword}
              onChange={(e) => setNewPassword(e.target.value)}
              sx={{ flex: 1 }}
            />
            <TextField
              size="small"
              type="password"
              label="Confirm"
              value={confirmPassword}
              onChange={(e) => setConfirmPassword(e.target.value)}
              sx={{ flex: 1 }}
            />
            <Button 
              variant="contained" 
              onClick={handlePasswordChange} 
              sx={{ whiteSpace: 'nowrap' }}
              disabled={!currentPassword || !newPassword || !confirmPassword}
            >
              Update
            </Button>
          </Box>
        </TabPanel>

        {/* Appearance Tab */}
        <TabPanel value={tabValue} index={1}>
          <Typography variant="h6" gutterBottom>Theme</Typography>
          <FormControl fullWidth sx={{ maxWidth: 300, mb: 3 }}>
            <InputLabel>Theme</InputLabel>
            <Select
              value={mode}
              onChange={handleThemeChange}
            >
              <MenuItem value="light">
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                  <LightModeIcon fontSize="small" />
                  Light
                </Box>
              </MenuItem>
              <MenuItem value="dark">
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                  <DarkModeIcon fontSize="small" />
                  Dark
                </Box>
              </MenuItem>
            </Select>
          </FormControl>
        </TabPanel>

        {/* Notifications Tab */}
        <TabPanel value={tabValue} index={2}>
          <Typography variant="h6" gutterBottom>Notification Preferences</Typography>
          
          <FormControlLabel
            control={
              <Switch
                checked={settings.notifications_enabled}
                onChange={handleNotificationsChange}
              />
            }
            label="Enable notifications"
          />
          
          <FormControlLabel
            control={
              <Switch
                checked={settings.email_notifications}
                onChange={handleEmailNotifChange}
              />
            }
            label="Email notifications (not implemented)"
          />
        </TabPanel>

        {/* Data Collection Tab */}
        <TabPanel value={tabValue} index={3}>
          <Typography variant="h6" gutterBottom>Data Sources</Typography>
          
          <FormControlLabel
            control={
              <Switch
                checked={settings.telegram_enabled}
                onChange={handleTelegramChange}
              />
            }
            label="Enable Telegram data collection"
          />

          <Divider sx={{ my: 3 }} />

          <Typography variant="h6" gutterBottom>Fetch Frequency</Typography>
          <Typography variant="body2" color="text.secondary" gutterBottom>
            How often to fetch new posts: {settings.fetch_frequency_hours} hours
          </Typography>
          <Slider
            value={settings.fetch_frequency_hours}
            onChange={(e, value) => {
              setSettings({ ...settings, fetch_frequency_hours: value });
            }}
            onChangeCommitted={(e, value) => {
              updateSettings({ fetch_frequency_hours: value });
            }}
            min={1}
            max={24}
            marks={[
              { value: 1, label: '1h' },
              { value: 6, label: '6h' },
              { value: 12, label: '12h' },
              { value: 24, label: '24h' }
            ]}
            sx={{ maxWidth: 400, mt: 2 }}
          />

          <OperationsPanel />
        </TabPanel>

        {/* ML Settings Tab */}
        <TabPanel value={tabValue} index={4}>
          <Typography variant="h6" gutterBottom>Machine Learning</Typography>
          
          <FormControlLabel
            control={
              <Switch
                checked={settings.ml_auto_classify}
                onChange={handleMLChange}
              />
            }
            label="Enable automatic topic classification"
          />

          <Divider sx={{ my: 3 }} />

          <Typography variant="h6" gutterBottom>Confidence Threshold</Typography>
          <Typography variant="body2" color="text.secondary" gutterBottom>
            Minimum confidence to display topic: {(settings.ml_confidence_threshold * 100).toFixed(0)}%
          </Typography>
          <Slider
            value={settings.ml_confidence_threshold}
            onChange={(e, value) => {
              setSettings({ ...settings, ml_confidence_threshold: value });
            }}
            onChangeCommitted={(e, value) => {
              updateSettings({ ml_confidence_threshold: value });
            }}
            min={0.3}
            max={0.9}
            step={0.05}
            marks={[
              { value: 0.3, label: '30%' },
              { value: 0.5, label: '50%' },
              { value: 0.7, label: '70%' },
              { value: 0.9, label: '90%' }
            ]}
            sx={{ maxWidth: 400, mt: 2 }}
          />
        </TabPanel>
      </Paper>
    </Container>
  );
}
