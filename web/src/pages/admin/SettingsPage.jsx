import { useState, useEffect } from 'react';
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

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

function TabPanel({ children, value, index }) {
  return (
    <div hidden={value !== index}>
      {value === index && <Box sx={{ p: 3 }}>{children}</Box>}
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

  useEffect(() => {
    fetchSettings();
  }, []);

  const fetchSettings = async () => {
    try {
      const token = localStorage.getItem('auth_token');
      const response = await fetch(`${API_BASE_URL}/settings`, {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });
      
      if (response.ok) {
        const data = await response.json();
        setSettings(data);
      }
    } catch (err) {
      console.error('Failed to load settings:', err);
      setError(err?.message || 'Failed to load settings');
    } finally {
      setLoading(false);
    }
  };

  const updateSettings = async (updates) => {
    try {
      const token = localStorage.getItem('auth_token');
      const response = await fetch(`${API_BASE_URL}/settings`, {
        method: 'PUT',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify(updates)
      });
      
      if (response.ok) {
        setSuccess('Settings updated successfully!');
        setTimeout(() => setSuccess(''), 3000);
        fetchSettings();
      }
    } catch (err) {
      console.error('Failed to update settings:', err);
      setError(err?.message || 'Failed to update settings');
    }
  };

  const handlePasswordChange = async () => {
    if (newPassword !== confirmPassword) {
      setError('New passwords do not match');
      return;
    }
    
    if (newPassword.length < 8) {
      setError('Password must be at least 8 characters');
      return;
    }

    try {
      const token = localStorage.getItem('auth_token');
      const response = await fetch(`${API_BASE_URL}/settings/change-password`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          current_password: currentPassword,
          new_password: newPassword
        })
      });
      
      if (response.ok) {
        setSuccess('Password changed successfully!');
        setCurrentPassword('');
        setNewPassword('');
        setConfirmPassword('');
      } else {
        const data = await response.json();
        const errorMsg = typeof data.detail === 'string' ? data.detail : 'Failed to change password';
        setError(errorMsg);
      }
    } catch (err) {
      console.error('Failed to change password:', err);
      setError(err?.message || 'Failed to change password');
    }
  };

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
          onChange={(e, newValue) => setTabValue(newValue)}
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
              onChange={(e) => {
                if (e.target.value !== mode) {
                  toggleTheme();
                  updateSettings({ theme: e.target.value });
                }
              }}
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
                onChange={(e) => {
                  const enabled = e.target.checked;
                  setSettings({ ...settings, notifications_enabled: enabled });
                  updateSettings({ notifications_enabled: enabled });
                }}
              />
            }
            label="Enable notifications"
          />
          
          <FormControlLabel
            control={
              <Switch
                checked={settings.email_notifications}
                onChange={(e) => {
                  const enabled = e.target.checked;
                  setSettings({ ...settings, email_notifications: enabled });
                  updateSettings({ email_notifications: enabled });
                }}
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
                onChange={(e) => {
                  const enabled = e.target.checked;
                  setSettings({ ...settings, telegram_enabled: enabled });
                  updateSettings({ telegram_enabled: enabled });
                }}
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
        </TabPanel>

        {/* ML Settings Tab */}
        <TabPanel value={tabValue} index={4}>
          <Typography variant="h6" gutterBottom>Machine Learning</Typography>
          
          <FormControlLabel
            control={
              <Switch
                checked={settings.ml_auto_classify}
                onChange={(e) => {
                  const enabled = e.target.checked;
                  setSettings({ ...settings, ml_auto_classify: enabled });
                  updateSettings({ ml_auto_classify: enabled });
                }}
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
