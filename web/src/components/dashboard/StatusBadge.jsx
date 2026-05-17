import React from 'react';
import { Chip } from '@mui/material';
import HourglassTopIcon from '@mui/icons-material/HourglassTop';
import CheckCircleOutlineIcon from '@mui/icons-material/CheckCircleOutline';
import ErrorOutlineIcon from '@mui/icons-material/ErrorOutline';

const STATUS_META = {
  pending: { label: 'Đang xử lý', color: 'warning', icon: <HourglassTopIcon sx={{ fontSize: 14 }} /> },
  active: { label: 'Đang hoạt động', color: 'success', icon: <CheckCircleOutlineIcon sx={{ fontSize: 14 }} /> },
  error: { label: 'Lỗi', color: 'error', icon: <ErrorOutlineIcon sx={{ fontSize: 14 }} /> },
};

function StatusBadgeInner({ status }) {
  const m = STATUS_META[status] || STATUS_META.pending;
  return (
    <Chip
      icon={m.icon}
      label={m.label}
      color={m.color}
      size="small"
      sx={{ height: 22, fontSize: '0.68rem', fontWeight: 600 }}
    />
  );
}

const StatusBadge = React.memo(StatusBadgeInner);
export default StatusBadge;
