/**
 * Shared helper utilities used across public and dashboard pages.
 */
import React from 'react';
import { formatDistanceToNow } from 'date-fns';
import { vi } from 'date-fns/locale';

export function timeAgo(dateStr) {
  if (!dateStr) return '';
  try {
    return formatDistanceToNow(new Date(dateStr), { addSuffix: true, locale: vi });
  } catch {
    return '';
  }
}

export function formatDateTime(dateStr) {
  if (!dateStr) return '';
  try {
    const d = new Date(dateStr);
    return `${d.getDate().toString().padStart(2, '0')}/${(d.getMonth() + 1)
      .toString()
      .padStart(2, '0')}/${d.getFullYear()} ${d.getHours().toString().padStart(2, '0')}:${d
      .getMinutes()
      .toString()
      .padStart(2, '0')}`;
  } catch {
    return '';
  }
}

export const SENTIMENT_COLOR = {
  positive: '#16a34a',
  negative: '#dc2626',
  mixed: '#d97706',
  neutral: '#6b7280',
};

export function highlightText(text, query) {
  if (!query || !text) return text;
  const words = query.trim().split(/\s+/).filter(Boolean);
  if (!words.length) return text;
  const pattern = new RegExp(
    `(${words.map((w) => w.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')).join('|')})`,
    'gi'
  );
  const parts = text.split(pattern);
  return parts.map((part, i) =>
    pattern.test(part) ? (
      <mark key={i} style={{ backgroundColor: '#fef08a', padding: '0 2px', borderRadius: 2 }}>
        {part}
      </mark>
    ) : (
      part
    )
  );
}
