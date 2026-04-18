import { useState, useCallback, useEffect, useRef } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  Box, Typography, Paper, Table, TableBody, TableCell, TableContainer,
  TableHead, TableRow, TablePagination, TextField, InputAdornment, Chip,
  IconButton, Tooltip, Avatar, Stack, Select, MenuItem, FormControl,
  InputLabel, Button, Dialog, DialogTitle, DialogContent, DialogActions,
  Alert, CircularProgress, Grid, Card, CardContent, LinearProgress,
} from '@mui/material';
import {
  Search, Refresh, CheckCircle, Block, HourglassEmpty,
  AdminPanelSettings, Person, Delete, PeopleAlt,
  PersonAdd, Shield, LockOpen,
} from '@mui/icons-material';
import { api } from '../../lib/api';
import { format, formatDistanceToNow } from 'date-fns';
import { vi } from 'date-fns/locale';

// MongoDB stores naive UTC datetimes — FastAPI serialises them WITHOUT 'Z'.
// JS would then parse as local time (off by +7h in Vietnam).
// We force UTC interpretation by appending 'Z' when no tz info is present.
function parseUTC(str) {
  if (!str) return null;
  const s = /[Zz+-]\d*$/.test(str.trim()) ? str : str + 'Z';
  const d = new Date(s);
  return isNaN(d.getTime()) ? null : d;
}

// ─── helpers ──────────────────────────────────────────────────────────────────
const STATUS_CONFIG = {
  active:  { label: 'Hoạt động', color: 'success', icon: <CheckCircle fontSize="small" /> },
  banned:  { label: 'Bị khóa',   color: 'error',   icon: <Block fontSize="small" /> },
  pending: { label: 'Chờ duyệt', color: 'warning', icon: <HourglassEmpty fontSize="small" /> },
};

const ROLE_CONFIG = {
  admin: { label: 'Admin', color: 'secondary', icon: <AdminPanelSettings fontSize="small" /> },
  user:  { label: 'User',  color: 'default',   icon: <Person fontSize="small" /> },
};

function avatarColor(name = '') {
  const colors = ['#7c3aed', '#2563eb', '#059669', '#dc2626', '#d97706', '#0891b2'];
  let hash = 0;
  for (const c of name) hash = c.charCodeAt(0) + ((hash << 5) - hash);
  return colors[Math.abs(hash) % colors.length];
}

function StatCard({ icon, label, value, color }) {
  return (
    <Card variant="outlined" sx={{ borderLeft: `4px solid ${color}`, height: '100%' }}>
      <CardContent sx={{ display: 'flex', alignItems: 'center', gap: 2, py: '12px !important' }}>
        <Box sx={{ color, fontSize: 32 }}>{icon}</Box>
        <Box>
          <Typography variant="h5" fontWeight="bold">{value ?? '—'}</Typography>
          <Typography variant="caption" color="text.secondary">{label}</Typography>
        </Box>
      </CardContent>
    </Card>
  );
}

// ─── confirm dialog ────────────────────────────────────────────────────────────
function ConfirmDialog({ open, title, message, onConfirm, onClose, confirmColor = 'error' }) {
  return (
    <Dialog open={open} onClose={onClose} maxWidth="xs" fullWidth>
      <DialogTitle>{title}</DialogTitle>
      <DialogContent><Typography>{message}</Typography></DialogContent>
      <DialogActions>
        <Button onClick={onClose}>Hủy</Button>
        <Button variant="contained" color={confirmColor} onClick={onConfirm}>Xác nhận</Button>
      </DialogActions>
    </Dialog>
  );
}

// ─── API calls ────────────────────────────────────────────────────────────────
const fetchUsers = ({ q, status, role, page, rowsPerPage }) =>
  api.get('/admin/users', { params: { q: q || undefined, status: status || undefined, role: role || undefined, skip: page * rowsPerPage, limit: rowsPerPage } })
    .then((r) => r.data);

const fetchStats = () => api.get('/admin/users/stats/summary').then((r) => r.data);

const updateStatus = ({ username, status }) =>
  api.put(`/admin/users/${username}/status`, { status }).then((r) => r.data);

const updateRole = ({ username, role }) =>
  api.put(`/admin/users/${username}/role`, { role }).then((r) => r.data);

const deleteUser = (username) =>
  api.delete(`/admin/users/${username}`).then((r) => r.data);

// ─── main component ────────────────────────────────────────────────────────────
export default function AdminUsersPage() {
  const qc = useQueryClient();

  // ── filters ──
  const [q, setQ] = useState('');
  const [debouncedQ, setDebouncedQ] = useState('');
  const [statusFilter, setStatusFilter] = useState('');
  const [roleFilter, setRoleFilter] = useState('');
  const [page, setPage] = useState(0);
  const [rowsPerPage, setRowsPerPage] = useState(20);

  // Debounce search input
  const debounceRef = useRef(null);
  useEffect(() => {
    debounceRef.current = setTimeout(() => {
      setDebouncedQ(q);
      setPage(0);
    }, 400);
    return () => clearTimeout(debounceRef.current);
  }, [q]);

  // ── confirm dialog state ──
  const [confirm, setConfirm] = useState(null); // { type, username, payload }

  // ── queries ──
  const usersKey = ['admin-users', debouncedQ, statusFilter, roleFilter, page, rowsPerPage];
  const { data, isLoading, isFetching, error, refetch, dataUpdatedAt } = useQuery({
    queryKey: usersKey,
    queryFn: () => fetchUsers({ q: debouncedQ, status: statusFilter, role: roleFilter, page, rowsPerPage }),
    keepPreviousData: true,
    refetchInterval: 15_000,
    refetchIntervalInBackground: false,
  });

  const { data: stats } = useQuery({
    queryKey: ['admin-users-stats'],
    queryFn: fetchStats,
    refetchInterval: 15_000,
    refetchIntervalInBackground: false,
  });

  // ── mutations ──
  const invalidate = () => qc.invalidateQueries({ queryKey: ['admin-users'] });

  const statusMut = useMutation({ mutationFn: updateStatus, onSuccess: invalidate });
  const roleMut   = useMutation({ mutationFn: updateRole,   onSuccess: () => { invalidate(); qc.invalidateQueries({ queryKey: ['admin-users-stats'] }); } });
  const deleteMut = useMutation({ mutationFn: deleteUser,   onSuccess: () => { invalidate(); qc.invalidateQueries({ queryKey: ['admin-users-stats'] }); } });

  // api.jsx throws new Error(responseText) — need to parse JSON detail if possible
  const extractErr = (e) => {
    if (!e) return null;
    try { return JSON.parse(e.message)?.detail || e.message; } catch { return e.message; }
  };
  const mutError = extractErr(statusMut.error) || extractErr(roleMut.error) || extractErr(deleteMut.error);

  // ── confirm handlers ──
  const openConfirm = useCallback((type, username, payload) =>
    setConfirm({ type, username, payload }), []);

  const handleConfirm = useCallback(() => {
    if (!confirm) return;
    if (confirm.type === 'status') statusMut.mutate({ username: confirm.username, status: confirm.payload });
    if (confirm.type === 'role')   roleMut.mutate({ username: confirm.username, role: confirm.payload });
    if (confirm.type === 'delete') deleteMut.mutate(confirm.username);
    setConfirm(null);
  }, [confirm, statusMut, roleMut, deleteMut]);

  const users = data?.users ?? [];
  const total = data?.total ?? 0;

  const lastUpdated = dataUpdatedAt ? new Date(dataUpdatedAt) : null;
  const lastUpdatedLabel = lastUpdated
    ? `Cập nhật lúc ${lastUpdated.toLocaleTimeString('vi-VN', { hour: '2-digit', minute: '2-digit', second: '2-digit' })}`
    : null;

  const handleRefresh = useCallback(() => {
    refetch();
    qc.invalidateQueries({ queryKey: ['admin-users-stats'] });
  }, [refetch, qc]);

  const handleQChange = useCallback((e) => setQ(e.target.value), []);
  const handleStatusFilterChange = useCallback((e) => { setStatusFilter(e.target.value); setPage(0); }, []);
  const handleRoleFilterChange = useCallback((e) => { setRoleFilter(e.target.value); setPage(0); }, []);
  const handleClearFilters = useCallback(() => { setQ(''); setDebouncedQ(''); setStatusFilter(''); setRoleFilter(''); setPage(0); }, []);
  const handlePageChange = useCallback((_, p) => setPage(p), []);
  const handleRowsPerPageChange = useCallback((e) => { setRowsPerPage(+e.target.value); setPage(0); }, []);

  return (
    <Box sx={{ p: { xs: 2, md: 3 } }}>
      {/* ── Header ── */}
      <Stack direction="row" alignItems="center" justifyContent="space-between" mb={3}>
        <Stack direction="row" alignItems="center" gap={1}>
          <PeopleAlt color="primary" sx={{ fontSize: 32 }} />
          <Box>
            <Typography variant="h5" fontWeight="bold">Quản lý người dùng</Typography>
            <Typography variant="caption" color="text.secondary">Xem, duyệt và quản lý tài khoản</Typography>
          </Box>
        </Stack>
        <Stack direction="row" alignItems="center" gap={1.5}>
          {/* Live indicator */}
          <Stack direction="row" alignItems="center" gap={0.75}>
            <Box
              sx={{
                width: 8, height: 8, borderRadius: '50%',
                bgcolor: isFetching ? 'warning.main' : 'success.main',
                animation: 'pulse 2s ease-in-out infinite',
                '@keyframes pulse': {
                  '0%, 100%': { opacity: 1, transform: 'scale(1)' },
                  '50%': { opacity: 0.5, transform: 'scale(1.4)' },
                },
              }}
            />
            <Typography variant="caption" color="text.secondary" sx={{ whiteSpace: 'nowrap' }}>
              {isFetching ? 'Đang cập nhật…' : lastUpdatedLabel ?? 'Live'}
            </Typography>
          </Stack>
          <Tooltip title="Làm mới ngay">
            <span>
              <IconButton onClick={handleRefresh} disabled={isFetching}>
                <Refresh sx={{ transition: 'transform 0.6s', ...(isFetching && { animation: 'spin 1s linear infinite', '@keyframes spin': { from: { transform: 'rotate(0deg)' }, to: { transform: 'rotate(360deg)' } } }) }} />
              </IconButton>
            </span>
          </Tooltip>
        </Stack>
      </Stack>

      {/* ── Stats cards ── */}
      <Grid container spacing={2} mb={3}>
        {[
          { icon: <PeopleAlt />, label: 'Tổng users',    value: stats?.total,                   color: '#7c3aed' },
          { icon: <CheckCircle />, label: 'Hoạt động',   value: stats?.by_status?.active  ?? 0, color: '#16a34a' },
          { icon: <Block />,       label: 'Bị khóa',     value: stats?.by_status?.banned  ?? 0, color: '#dc2626' },
          { icon: <HourglassEmpty />, label: 'Chờ duyệt', value: stats?.by_status?.pending ?? 0, color: '#d97706' },
          { icon: <Shield />,      label: 'Admin',       value: stats?.by_role?.admin     ?? 0, color: '#2563eb' },
        ].map((s) => (
          <Grid size={{ xs: 12, sm: 6, md: 2.4 }} key={s.label}>
            <StatCard {...s} />
          </Grid>
        ))}
      </Grid>

      {mutError && <Alert severity="error" sx={{ mb: 2 }}>{mutError}</Alert>}

      {/* ── Filters ── */}
      <Paper sx={{ p: 2, mb: 2, display: 'flex', flexWrap: 'wrap', gap: 2, alignItems: 'center' }}>
        <TextField
          size="small" placeholder="Tìm username / email…"
          value={q} onChange={handleQChange}
          sx={{ minWidth: 220 }}
          InputProps={{ startAdornment: <InputAdornment position="start"><Search /></InputAdornment> }}
        />
        <FormControl size="small" sx={{ minWidth: 150 }}>
          <InputLabel>Trạng thái</InputLabel>
          <Select value={statusFilter} label="Trạng thái" onChange={handleStatusFilterChange}>
            <MenuItem value="">Tất cả</MenuItem>
            <MenuItem value="active">Hoạt động</MenuItem>
            <MenuItem value="banned">Bị khóa</MenuItem>
            <MenuItem value="pending">Chờ duyệt</MenuItem>
          </Select>
        </FormControl>
        <FormControl size="small" sx={{ minWidth: 130 }}>
          <InputLabel>Vai trò</InputLabel>
          <Select value={roleFilter} label="Vai trò" onChange={handleRoleFilterChange}>
            <MenuItem value="">Tất cả</MenuItem>
            <MenuItem value="user">User</MenuItem>
            <MenuItem value="admin">Admin</MenuItem>
          </Select>
        </FormControl>
        {(q || statusFilter || roleFilter) && (
          <Button size="small" onClick={handleClearFilters}>
            Xóa bộ lọc
          </Button>
        )}
      </Paper>

      {/* ── Table ── */}
      <Paper sx={{ position: 'relative' }}>
        {isFetching && !isLoading && (
          <LinearProgress sx={{ position: 'absolute', top: 0, left: 0, right: 0, borderRadius: '4px 4px 0 0', zIndex: 1 }} />
        )}
        <TableContainer>
          <Table size="small">
            <TableHead>
              <TableRow sx={{ '& th': { fontWeight: 700, bgcolor: 'grey.50' } }}>
                <TableCell>Người dùng</TableCell>
                <TableCell>Email</TableCell>
                <TableCell>Vai trò</TableCell>
                <TableCell>Trạng thái</TableCell>
                <TableCell>Ngày tạo</TableCell>
                <TableCell>Đăng nhập cuối</TableCell>
                <TableCell align="right">Hành động</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {isLoading ? (
                <TableRow>
                  <TableCell colSpan={7} align="center" sx={{ py: 4 }}>
                    <CircularProgress size={28} />
                  </TableCell>
                </TableRow>
              ) : error ? (
                <TableRow>
                  <TableCell colSpan={7}>
                    <Alert severity="error">Không tải được danh sách user.</Alert>
                  </TableCell>
                </TableRow>
              ) : users.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={7} align="center" sx={{ py: 4 }}>
                    <Stack alignItems="center" gap={1}>
                      <PersonAdd sx={{ fontSize: 40, color: 'text.disabled' }} />
                      <Typography color="text.secondary">Không có user nào.</Typography>
                    </Stack>
                  </TableCell>
                </TableRow>
              ) : users.map((user) => {
                const sc = STATUS_CONFIG[user.status] ?? STATUS_CONFIG.pending;
                const rc = ROLE_CONFIG[user.role] ?? ROLE_CONFIG.user;
                return (
                  <TableRow key={user.username} hover>
                    {/* Avatar + name */}
                    <TableCell>
                      <Stack direction="row" alignItems="center" gap={1.5}>
                        <Avatar sx={{ width: 34, height: 34, bgcolor: avatarColor(user.username), fontSize: 14 }}>
                          {user.username[0].toUpperCase()}
                        </Avatar>
                        <Box>
                          <Typography variant="body2" fontWeight={600}>{user.username}</Typography>
                          {user.full_name && (
                            <Typography variant="caption" color="text.secondary">{user.full_name}</Typography>
                          )}
                        </Box>
                      </Stack>
                    </TableCell>

                    <TableCell>
                      <Typography variant="body2" color="text.secondary">
                        {user.email || '—'}
                      </Typography>
                    </TableCell>

                    {/* Role chip + toggle */}
                    <TableCell>
                      <Chip
                        icon={rc.icon} label={rc.label} size="small"
                        color={rc.color}
                        onClick={() => openConfirm('role', user.username, user.role === 'admin' ? 'user' : 'admin')}
                        sx={{ cursor: 'pointer' }}
                      />
                    </TableCell>

                    {/* Status chip */}
                    <TableCell>
                      <Chip icon={sc.icon} label={sc.label} size="small" color={sc.color} variant="outlined" />
                    </TableCell>

                    <TableCell>
                      <Typography variant="caption">
                        {parseUTC(user.created_at) ? format(parseUTC(user.created_at), 'dd/MM/yyyy', { locale: vi }) : '—'}
                      </Typography>
                    </TableCell>

                    <TableCell>
                      {(() => {
                        const d = parseUTC(user.last_login);
                        if (!d) return <Typography variant="caption" color="text.disabled">Chưa đăng nhập</Typography>;
                        return (
                          <Tooltip title={format(d, 'dd/MM/yyyy HH:mm:ss', { locale: vi })}>
                            <Typography variant="caption" color="text.secondary">
                              {formatDistanceToNow(d, { addSuffix: true, locale: vi })}
                            </Typography>
                          </Tooltip>
                        );
                      })()}
                    </TableCell>

                    {/* Actions */}
                    <TableCell align="right">
                      <Stack direction="row" justifyContent="flex-end" gap={0.5}>
                        {user.status !== 'active' && (
                          <Tooltip title="Kích hoạt">
                            <IconButton size="small" color="success"
                              onClick={() => openConfirm('status', user.username, 'active')}>
                              <LockOpen fontSize="small" />
                            </IconButton>
                          </Tooltip>
                        )}
                        {user.status !== 'pending' && (
                          <Tooltip title="Đặt chờ duyệt">
                            <IconButton size="small" color="warning"
                              onClick={() => openConfirm('status', user.username, 'pending')}>
                              <HourglassEmpty fontSize="small" />
                            </IconButton>
                          </Tooltip>
                        )}
                        {user.status !== 'banned' && (
                          <Tooltip title="Khóa tài khoản">
                            <IconButton size="small" color="error"
                              onClick={() => openConfirm('status', user.username, 'banned')}>
                              <Block fontSize="small" />
                            </IconButton>
                          </Tooltip>
                        )}
                        <Tooltip title="Xóa tài khoản">
                          <IconButton size="small" color="error"
                            onClick={() => openConfirm('delete', user.username, null)}>
                            <Delete fontSize="small" />
                          </IconButton>
                        </Tooltip>
                      </Stack>
                    </TableCell>
                  </TableRow>
                );
              })}
            </TableBody>
          </Table>
        </TableContainer>

        <TablePagination
          component="div" count={total} page={page} rowsPerPage={rowsPerPage}
          onPageChange={handlePageChange}
          onRowsPerPageChange={handleRowsPerPageChange}
          rowsPerPageOptions={[10, 20, 50, 100]}
          labelRowsPerPage="Hiển thị:"
          labelDisplayedRows={({ from, to, count }) => `${from}–${to} / ${count}`}
        />
      </Paper>

      {/* ── Confirm Dialog ── */}
      {confirm && (
        <ConfirmDialog
          open
          onClose={() => setConfirm(null)}
          onConfirm={handleConfirm}
          confirmColor={confirm.type === 'delete' ? 'error' : confirm.type === 'status' && confirm.payload === 'banned' ? 'error' : 'primary'}
          title={
            confirm.type === 'delete' ? 'Xóa tài khoản?' :
            confirm.type === 'status' ? `Thay đổi trạng thái?` :
            `Thay đổi vai trò?`
          }
          message={
            confirm.type === 'delete'
              ? `Bạn chắc chắn muốn xóa tài khoản "${confirm.username}"? Hành động này không thể hoàn tác.`
              : confirm.type === 'status'
              ? `Đặt trạng thái của "${confirm.username}" thành "${STATUS_CONFIG[confirm.payload]?.label}".`
              : `Đổi vai trò của "${confirm.username}" thành "${ROLE_CONFIG[confirm.payload]?.label}".`
          }
        />
      )}
    </Box>
  );
}
