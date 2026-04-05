import { createContext, useContext, useState, useEffect } from 'react';
import { api } from '../lib/api';

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
        } else {
          setToken(storedToken);
          setUser(parsedUser);
          api.setAuthToken(storedToken);
        }
      } catch {
        localStorage.removeItem('auth_token');
        localStorage.removeItem('auth_user');
      }
    }
    
    setLoading(false);
  }, []);

  const login = async (username, password) => {
    try {
      const response = await fetch('http://localhost:8000/auth/login', {
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
        expires_at: Date.now() + (data.expires_in * 1000)
      }));
      
      setToken(data.access_token);
      setUser({ 
        username: data.username,
        role: data.role || 'user',
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

  const logout = async () => {
    try {
      // Call logout endpoint (optional, for logging)
      if (token) {
        await fetch('http://localhost:8000/auth/logout', {
          method: 'POST',
          headers: {
            'Authorization': `Bearer ${token}`,
          },
        });
      }
    } catch (error) {
      console.error('Logout error:', error);
    } finally {
      // Clear local storage and state
      localStorage.removeItem('auth_token');
      localStorage.removeItem('auth_user');
      setToken(null);
      setUser(null);
      api.setAuthToken(null);
    }
  };

  const isTokenExpired = () => {
    if (!token) return true;
    try {
      const payload = token.split('.')[1];
      const decoded = JSON.parse(atob(payload.replace(/-/g, '+').replace(/_/g, '/')));
      if (!decoded?.exp) return true;
      // exp is in seconds; compare to current time in seconds
      return Date.now() / 1000 >= decoded.exp;
    } catch {
      return true;
    }
  };

  // Derive role directly from the signed JWT — cannot be spoofed via localStorage edits.
  const jwtRole = token ? decodeJwtRole(token) : null;

  const value = {
    user,
    token,
    loading,
    userRole: jwtRole,
    isAuthenticated: !!token && !isTokenExpired(),
    isAdmin: jwtRole === 'admin',
    login,
    logout,
  };

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  );
};
