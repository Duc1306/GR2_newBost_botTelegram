import React, { useState } from 'react';
import {
  Card,
  CardContent,
  Box,
  Skeleton,
} from '@mui/material';

export function CardSkeleton() {
  return (
    <Card elevation={0} sx={{ mb: 2, borderRadius: 2, border: '1px solid', borderColor: 'divider' }}>
      <CardContent>
        <Box display="flex" gap={1} mb={1}>
          <Skeleton variant="rounded" width={70} height={20} />
          <Skeleton variant="rounded" width={90} height={20} />
        </Box>
        <Skeleton variant="text" sx={{ fontSize: '1rem' }} width="90%" />
        <Skeleton variant="text" sx={{ fontSize: '0.875rem' }} width="100%" />
        <Skeleton variant="text" sx={{ fontSize: '0.875rem' }} width="75%" />
      </CardContent>
    </Card>
  );
}

export function ClusterSkeleton() {
  return (
    <Card elevation={0} sx={{ borderRadius: 2.5, border: '1px solid', borderColor: 'divider', height: 200 }}>
      <Box sx={{ height: 5, bgcolor: 'grey.200', borderRadius: '10px 10px 0 0' }} />
      <CardContent>
        <Skeleton variant="text" width="60%" height={24} />
        <Skeleton variant="text" width="100%" />
        <Skeleton variant="text" width="85%" />
        <Box mt={1}>
          <Skeleton variant="rounded" width={80} height={20} />
        </Box>
      </CardContent>
    </Card>
  );
}
