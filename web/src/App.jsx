import React, { Suspense, lazy } from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { ThemeProvider } from './context/ThemeContext.jsx';
import { AuthProvider, useAuth } from './context/AuthContext.jsx';
import Layout from './components/layout/Layout.jsx';
import { CircularProgress, Box } from '@mui/material';

// Lazy-loaded pages
const OverviewPage = lazy(() => import('./pages/admin/OverviewPage.jsx'));
const AnalyticsPage = lazy(() => import('./pages/admin/AnalyticsPage.jsx'));
const PostsPage = lazy(() => import('./pages/admin/PostsPage.jsx'));
const TrendingPage = lazy(() => import('./pages/admin/TrendingPage.jsx'));
const SettingsPage = lazy(() => import('./pages/admin/SettingsPage.jsx'));
const UsersPage = lazy(() => import('./pages/admin/UsersPage.jsx'));
const DashboardPage = lazy(() => import('./pages/user/DashboardPage.jsx'));
const PublicHomePage = lazy(() => import('./pages/public/PublicHomePage.jsx'));
const LoginPage = lazy(() => import('./pages/auth/LoginPage.jsx'));
const RegisterPage = lazy(() => import('./pages/auth/RegisterPage.jsx'));
const TelegramLoginPage = lazy(() => import('./pages/auth/TelegramLoginPage.jsx'));

const PageLoader = () => (
  <Box display="flex" justifyContent="center" alignItems="center" minHeight="60vh">
    <CircularProgress />
  </Box>
);

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

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      refetchOnWindowFocus: false,
      retry: 1,
      staleTime: 30_000,
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
  if (!isAdmin) return <Navigate to="/dashboard" replace />;
  return children;
}

// Redirect already-logged-in users away from login/register pages
function GuestOnly({ children }) {
  const { isAuthenticated, isAdmin, loading } = useAuth();
  if (loading) return <div style={{ padding: 32 }}>Loading...</div>;
  if (isAuthenticated) return <Navigate to={isAdmin ? '/admin' : '/dashboard'} replace />;
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
      {/* ── Public (no auth required) ────────────────────────── */}
      <Route path="/" element={<Suspense fallback={<PageLoader />}><PublicHomePage /></Suspense>} />

      {/* ── Auth ────────────────────────────────────────────── */}
      <Route path="/login"    element={<GuestOnly><Suspense fallback={<PageLoader />}><LoginPage /></Suspense></GuestOnly>} />
      <Route path="/register" element={<GuestOnly><Suspense fallback={<PageLoader />}><RegisterPage /></Suspense></GuestOnly>} />
      <Route path="/login/telegram" element={<GuestOnly><Suspense fallback={<PageLoader />}><TelegramLoginPage /></Suspense></GuestOnly>} />

      {/* ── User routes (role: user or admin) ───────────────── */}
      <Route path="/dashboard" element={<UserRoute page={<Suspense fallback={<PageLoader />}><DashboardPage /></Suspense>} />} />
      <Route path="/news" element={<Navigate to="/" replace />} />

      {/* ── Admin routes (role: admin only) ─────────────────── */}
      <Route path="/admin"           element={<AdminRoute page={<Suspense fallback={<PageLoader />}><OverviewPage /></Suspense>} />} />
      <Route path="/admin/analytics" element={<AdminRoute page={<Suspense fallback={<PageLoader />}><AnalyticsPage /></Suspense>} />} />
      <Route path="/admin/posts"     element={<AdminRoute page={<Suspense fallback={<PageLoader />}><PostsPage /></Suspense>} />} />
      <Route path="/admin/trending"  element={<AdminRoute page={<Suspense fallback={<PageLoader />}><TrendingPage /></Suspense>} />} />
      <Route path="/admin/settings"  element={<AdminRoute page={<Suspense fallback={<PageLoader />}><SettingsPage /></Suspense>} />} />
      <Route path="/admin/users"     element={<AdminRoute page={<Suspense fallback={<PageLoader />}><UsersPage /></Suspense>} />} />

      {/* Legacy compat */}
      <Route path="/admin/login" element={<Navigate to="/login" replace />} />

      {/* 404 → public home */}
      <Route path="*" element={<Navigate to="/" replace />} />
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



