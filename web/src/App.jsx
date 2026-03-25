import React from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { ThemeProvider } from './context/ThemeContext.jsx';
import { AuthProvider, useAuth } from './context/AuthContext.jsx';

// Error boundary to show crash details instead of blank page
class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false, error: null };
  }
  static getDerivedStateFromError(error) {
    return { hasError: true, error };
  }
  render() {
    if (this.state.hasError) {
      return (
        <div style={{ padding: 32, fontFamily: 'monospace', background: '#fff0f0', minHeight: '100vh' }}>
          <h2 style={{ color: '#c00' }}>⚠ App Error</h2>
          <pre style={{ whiteSpace: 'pre-wrap', color: '#333', fontSize: 13 }}>
            {this.state.error?.toString()}{'\n\n'}{this.state.error?.stack}
          </pre>
        </div>
      );
    }
    return this.props.children;
  }
}
import Layout from './components/layout/Layout.jsx';

// Admin pages
import OverviewPage from './pages/admin/OverviewPage.jsx';
import AnalyticsPage from './pages/admin/AnalyticsPage.jsx';
import PostsPage from './pages/admin/PostsPage.jsx';
import TrendingPage from './pages/admin/TrendingPage.jsx';
import SettingsPage from './pages/admin/SettingsPage.jsx';

// User page
import NewsPage from './pages/user/NewsPage.jsx';

// Auth page
import LoginPage from './pages/auth/LoginPage.jsx';

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      refetchOnWindowFocus: false,
      retry: 1,
    },
  },
});

// ─── Route guards ────────────────────────────────────────────
// Requires any authenticated user
function AuthRequired({ children, redirectTo = '/login' }) {
  const { isAuthenticated, loading } = useAuth();
  if (loading) return <div style={{ padding: 32 }}>Loading...</div>;
  if (!isAuthenticated) return <Navigate to={redirectTo} replace />;
  return children;
}

// Requires admin role specifically
function AdminRequired({ children }) {
  const { isAuthenticated, isAdmin, loading } = useAuth();
  if (loading) return <div style={{ padding: 32 }}>Loading...</div>;
  if (!isAuthenticated) return <Navigate to="/login" replace />;
  if (!isAdmin) return <Navigate to="/news" replace />;
  return children;
}

// Redirect already-logged-in users away from login page
function GuestOnly({ children }) {
  const { isAuthenticated, isAdmin, loading } = useAuth();
  if (loading) return <div style={{ padding: 32 }}>Loading...</div>;
  if (isAuthenticated) return <Navigate to={isAdmin ? '/admin' : '/news'} replace />;
  return children;
}

function AdminRoute({ page }) {
  return (
    <AdminRequired>
      <Layout>{page}</Layout>
    </AdminRequired>
  );
}

function UserRoute({ page }) {
  return (
    <AuthRequired redirectTo="/login">
      {page}
    </AuthRequired>
  );
}

function AppRoutes() {
  return (
    <Routes>
      {/* ── Auth ────────────────────────────────────────────── */}
      <Route path="/login" element={<GuestOnly><LoginPage /></GuestOnly>} />

      {/* ── User routes (role: user or admin) ───────────────── */}
      <Route path="/"     element={<Navigate to="/news" replace />} />
      <Route path="/news" element={<UserRoute page={<NewsPage />} />} />

      {/* ── Admin routes (role: admin only) ─────────────────── */}
      <Route path="/admin"           element={<AdminRoute page={<OverviewPage />} />} />
      <Route path="/admin/analytics" element={<AdminRoute page={<AnalyticsPage />} />} />
      <Route path="/admin/posts"     element={<AdminRoute page={<PostsPage />} />} />
      <Route path="/admin/trending"  element={<AdminRoute page={<TrendingPage />} />} />
      <Route path="/admin/settings"  element={<AdminRoute page={<SettingsPage />} />} />

      {/* Legacy compat */}
      <Route path="/admin/login" element={<Navigate to="/login" replace />} />

      {/* 404 */}
      <Route path="*" element={<Navigate to="/news" replace />} />
    </Routes>
  );
}

function App() {
  return (
    <ErrorBoundary>
      <QueryClientProvider client={queryClient}>
        <BrowserRouter>
          <ThemeProvider>
            <AuthProvider>
              <AppRoutes />
            </AuthProvider>
          </ThemeProvider>
        </BrowserRouter>
      </QueryClientProvider>
    </ErrorBoundary>
  );
}

export default App;



