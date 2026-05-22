import { createContext, useContext, useState, useEffect, useRef, useMemo } from 'react';
import { api } from '../lib/api';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

// Tự động logout sau X phút không hoạt động (0 = tắt tính năng)
const INACTIVITY_TIMEOUT_MS = 60 * 60 * 1000; // 60 phút

const AuthContext = createContext(null);

/** Decode JWT payload without verifying signature (read-only claim extraction). */
function decodeJwtRole(token) {
  try {
    const payload = token.split('.')[1];
    const decoded = JSON.parse(atob(payload.replace(/-/g, '+').replace(/_/g, '/')));
    return decoded?.role || 'user';
  } catch {
    return 'user';
  }
}

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within AuthProvider');
  }
  return context;
};

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [token, setToken] = useState(null);
  const [loading, setLoading] = useState(true);
  const inactivityTimerRef = useRef(null);

  // Load token from localStorage on mount
  useEffect(() => {
    const storedToken = localStorage.getItem('auth_token');
    const storedUser = localStorage.getItem('auth_user');
    
    if (storedToken && storedUser) {
      try {
        const parsedUser = JSON.parse(storedUser);
        // Invalidate old sessions that pre-date the role system
        if (!parsedUser.role) {
          localStorage.removeItem('auth_token');
          localStorage.removeItem('auth_user');
          setLoading(false);
          return;
        }
        setToken(storedToken);
        setUser(parsedUser);
        api.setAuthToken(storedToken);

        // Nếu chưa có full_name trong localStorage → gọi /auth/me để lấy
        if (!parsedUser.full_name || parsedUser.full_name === parsedUser.username) {
          fetch(`${API_BASE_URL}/auth/me`, {
            headers: { Authorization: `Bearer ${storedToken}` },
          })
            .then((r) => r.ok ? r.json() : null)
            .then((data) => {
              if (data?.full_name) {
                const updated = { ...parsedUser, full_name: data.full_name };
                localStorage.setItem('auth_user', JSON.stringify(updated));
                setUser(updated);
              }
            })
            .catch(() => {});
        }
      } catch {
        localStorage.removeItem('auth_token');
        localStorage.removeItem('auth_user');
      }
    }
    
    setLoading(false);
  }, []);

  // ── Inactivity auto-logout ───────────────────────────────────────────────
  useEffect(() => {
    if (!token || !INACTIVITY_TIMEOUT_MS) return;

    const resetTimer = () => {
      if (inactivityTimerRef.current) clearTimeout(inactivityTimerRef.current);
      inactivityTimerRef.current = setTimeout(() => logout(), INACTIVITY_TIMEOUT_MS);
    };

    const events = ['mousemove', 'keydown', 'click', 'scroll', 'touchstart'];
    events.forEach((e) => window.addEventListener(e, resetTimer, { passive: true }));
    resetTimer(); // bắt đầu đếm ngay khi đăng nhập

    return () => {
      events.forEach((e) => window.removeEventListener(e, resetTimer));
      if (inactivityTimerRef.current) clearTimeout(inactivityTimerRef.current);
    };
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [token]);

  const login = async (username, password) => {
    try {
      const response = await fetch(`${API_BASE_URL}/auth/login`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ username, password }),
      });

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || 'Login failed');
      }

      const data = await response.json();
      
      // Store token and user
      localStorage.setItem('auth_token', data.access_token);
      localStorage.setItem('auth_user', JSON.stringify({
        username: data.username,
        role: data.role || 'user',
        full_name: data.full_name || data.username,
        expires_at: Date.now() + (data.expires_in * 1000)
      }));
      
      setToken(data.access_token);
      setUser({ 
        username: data.username,
        role: data.role || 'user',
        full_name: data.full_name || data.username,
        expires_at: Date.now() + (data.expires_in * 1000)
      });
      
      // Set token for API client
      api.setAuthToken(data.access_token);
      
      return { success: true, role: data.role };
    } catch (error) {
      console.error('Login error:', error);
      return { success: false, error: error.message };
    }
  };

  const register = async ({ username, password, email, full_name }) => {
    try {
      const response = await fetch(`${API_BASE_URL}/auth/register`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username, password, email, full_name }),
      });
      if (!response.ok) {
        const err = await response.json();
        throw new Error(err.detail || 'Registration failed');
      }
      const data = await response.json();
      localStorage.setItem('auth_token', data.access_token);
      localStorage.setItem('auth_user', JSON.stringify({
        username: data.username,
        role: data.role || 'user',
        full_name: data.full_name || full_name || data.username,
        expires_at: Date.now() + (data.expires_in * 1000),
      }));
      setToken(data.access_token);
      setUser({ username: data.username, role: data.role || 'user', full_name: data.full_name || full_name || data.username, expires_at: Date.now() + (data.expires_in * 1000) });
      api.setAuthToken(data.access_token);
      return { success: true, role: data.role };
    } catch (error) {
      console.error('Register error:', error);
      return { success: false, error: error.message };
    }
  };

  const loginWithTelegram = async (telegramAuthData) => {
    try {
      const { access_token, username, role, expires_in, full_name } = telegramAuthData;
      localStorage.setItem('auth_token', access_token);
      localStorage.setItem('auth_user', JSON.stringify({
        username,
        role: role || 'user',
        full_name: full_name || username,
        expires_at: Date.now() + (expires_in * 1000),
      }));
      setToken(access_token);
      setUser({
        username,
        role: role || 'user',
        full_name: full_name || username,
        expires_at: Date.now() + (expires_in * 1000),
      });
      api.setAuthToken(access_token);
      return { success: true, role };
    } catch (error) {
      console.error('Telegram login error:', error);
      return { success: false, error: error.message };
    }
  };

  const logout = () => {
    // Xóa state ngay lập tức — không đợi server
    const currentToken = token;
    localStorage.removeItem('auth_token');
    localStorage.removeItem('auth_user');
    setToken(null);
    setUser(null);
    api.setAuthToken(null);
    if (inactivityTimerRef.current) clearTimeout(inactivityTimerRef.current);
    // Gọi server fire-and-forget (chỉ để ghi log)
    if (currentToken) {
      fetch(`${API_BASE_URL}/auth/logout`, {
        method: 'POST',
        headers: { Authorization: `Bearer ${currentToken}` },
      }).catch(() => {});
    }
  };

  const isTokenExpired = useMemo(() => {
    if (!token) return true;
    try {
      const payload = token.split('.')[1];
      const decoded = JSON.parse(atob(payload.replace(/-/g, '+').replace(/_/g, '/')));
      if (!decoded?.exp) return true;
      return Date.now() / 1000 >= decoded.exp;
    } catch {
      return true;
    }
  }, [token]);

  // Derive role directly from the signed JWT — cannot be spoofed via localStorage edits.
  const jwtRole = token ? decodeJwtRole(token) : null;

  const value = useMemo(() => ({
    user,
    token,
    loading,
    userRole: jwtRole,
    isAuthenticated: !!token && !isTokenExpired,
    isAdmin: jwtRole === 'admin',
    login,
    loginWithTelegram,
    register,
    logout,
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }), [user, token, loading, jwtRole, isTokenExpired]);

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  );
};
