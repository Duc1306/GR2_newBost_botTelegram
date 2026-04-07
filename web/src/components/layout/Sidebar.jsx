import React from 'react';
import {
  Drawer,
  List,
  ListItem,
  ListItemButton,
  ListItemIcon,
  ListItemText,
  Toolbar,
  Divider,
  Box,
  Tooltip,
} from '@mui/material';
import { useNavigate, useLocation } from 'react-router-dom';
import DashboardIcon from '@mui/icons-material/Dashboard';
import AnalyticsIcon from '@mui/icons-material/Analytics';
import ArticleIcon from '@mui/icons-material/Article';
import TrendingUpIcon from '@mui/icons-material/TrendingUp';
import SettingsIcon from '@mui/icons-material/Settings';
import LocalFireDepartmentIcon from '@mui/icons-material/LocalFireDepartment';
import OpenInNewIcon from '@mui/icons-material/OpenInNew';
import PeopleAltIcon from '@mui/icons-material/PeopleAlt';

const drawerWidth = 240;

const menuItems = [
  { text: 'Overview',   icon: <DashboardIcon />,   path: '/admin' },
  { text: 'Analytics',  icon: <AnalyticsIcon />,   path: '/admin/analytics' },
  { text: 'Posts',      icon: <ArticleIcon />,     path: '/admin/posts' },
  { text: 'Trending',   icon: <TrendingUpIcon />,  path: '/admin/trending' },
  { text: 'Người dùng', icon: <PeopleAltIcon />,   path: '/admin/users' },
];

const bottomItems = [
  { text: 'Settings', icon: <SettingsIcon />, path: '/admin/settings' },
];

export default function Sidebar({ open, onClose, variant = 'permanent' }) {
  const navigate = useNavigate();
  const location = useLocation();

  const handleNavigation = (path) => {
    navigate(path);
    if (variant === 'temporary') {
      onClose();
    }
  };

  const drawer = (
    <Box sx={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
      <Toolbar />
      <Box sx={{ flexGrow: 1, overflow: 'auto' }}>
        <List>
          {menuItems.map((item) => (
            <ListItem key={item.text} disablePadding>
              <ListItemButton
                selected={location.pathname === item.path}
                onClick={() => handleNavigation(item.path)}
              >
                <ListItemIcon sx={{ color: location.pathname === item.path ? 'primary.main' : 'inherit' }}>
                  {item.icon}
                </ListItemIcon>
                <ListItemText primary={item.text} />
              </ListItemButton>
            </ListItem>
          ))}
        </List>
      </Box>
      <Divider />
      <List>
        {bottomItems.map((item) => (
          <ListItem key={item.text} disablePadding>
            <ListItemButton
              selected={location.pathname === item.path}
              onClick={() => handleNavigation(item.path)}
            >
              <ListItemIcon>
                {item.icon}
              </ListItemIcon>
              <ListItemText primary={item.text} />
            </ListItemButton>
          </ListItem>
        ))}

        {/* Link to user news page */}
        <Divider sx={{ my: 0.5 }} />
        <Tooltip title="Mở trang bảng tin người dùng" placement="right">
          <ListItem disablePadding>
            <ListItemButton
              component="a"
              href="/news"
              target="_blank"
              rel="noopener noreferrer"
              sx={{
                color: '#ff6b35',
                '&:hover': { bgcolor: 'rgba(255,107,53,0.08)' },
              }}
            >
              <ListItemIcon sx={{ color: '#ff6b35', minWidth: 40 }}>
                <LocalFireDepartmentIcon />
              </ListItemIcon>
              <ListItemText
                primary="Bảng tin Nóng"
                secondary="Trang người dùng"
                primaryTypographyProps={{ fontSize: '0.875rem', fontWeight: 600 }}
                secondaryTypographyProps={{ fontSize: '0.7rem' }}
              />
              <OpenInNewIcon sx={{ fontSize: 14, opacity: 0.6 }} />
            </ListItemButton>
          </ListItem>
        </Tooltip>
      </List>
    </Box>
  );

  return (
    <Drawer
      variant={variant}
      open={open}
      onClose={onClose}
      sx={{
        width: drawerWidth,
        flexShrink: 0,
        '& .MuiDrawer-paper': {
          width: drawerWidth,
          boxSizing: 'border-box',
        },
      }}
    >
      {drawer}
    </Drawer>
  );
}
