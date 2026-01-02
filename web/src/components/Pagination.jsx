import React from 'react';
import FirstPageIcon from '@mui/icons-material/FirstPage';
import LastPageIcon from '@mui/icons-material/LastPage';
import ChevronLeftIcon from '@mui/icons-material/ChevronLeft';
import ChevronRightIcon from '@mui/icons-material/ChevronRight';

function usePagination({ count, page, siblingCount = 1, boundaryCount = 1 }) {
  const DOTS = '…';

  if (count <= 0) return [];

  const totalNumbers = siblingCount * 2 + 3 + boundaryCount * 2;
  if (count <= totalNumbers) {
    return Array.from({ length: count }, (_, i) => i + 1);
  }

  const leftSiblingIndex = Math.max(page - siblingCount, 1);
  const rightSiblingIndex = Math.min(page + siblingCount, count);

  const showLeftDots = leftSiblingIndex > (boundaryCount + 2);
  const showRightDots = rightSiblingIndex < (count - boundaryCount - 1);

  const range = [];

  const startPages = Array.from({ length: boundaryCount }, (_, i) => i + 1);
  const endPages = Array.from({ length: boundaryCount }, (_, i) => count - boundaryCount + 1 + i);

  if (!showLeftDots && showRightDots) {
    const leftRange = Array.from({ length: boundaryCount + 2 * siblingCount + 2 }, (_, i) => i + 1);
    return [...leftRange, DOTS, ...endPages];
  }

  if (showLeftDots && !showRightDots) {
    const rightRange = Array.from(
      { length: boundaryCount + 2 * siblingCount + 2 },
      (_, i) => count - (boundaryCount + 2 * siblingCount + 2) + 1 + i
    );
    return [...startPages, DOTS, ...rightRange];
  }

  if (showLeftDots && showRightDots) {
    const middleRange = Array.from({ length: 2 * siblingCount + 1 }, (_, i) => leftSiblingIndex + i);
    return [...startPages, DOTS, ...middleRange, DOTS, ...endPages];
  }

  return Array.from({ length: count }, (_, i) => i + 1);
}

export const Pagination = ({ count, page, onChange, siblingCount = 1, boundaryCount = 1, disabled }) => {
  const items = usePagination({ count, page, siblingCount, boundaryCount });
  const canPrev = page > 1 && !disabled;
  const canNext = page < count && !disabled;

  if (count <= 1) return null;

  const buttonStyle = (isActive, canClick) => ({
    padding: '0.5rem 0.75rem',
    borderRadius: '0.25rem',
    border: '1px solid #d1d5db',
    fontSize: '0.875rem',
    fontWeight: 500,
    backgroundColor: isActive ? '#eff6ff' : canClick ? 'white' : '#f3f4f6',
    color: isActive ? '#1d4ed8' : canClick ? '#374151' : '#9ca3af',
    cursor: canClick ? 'pointer' : 'not-allowed',
    borderColor: isActive ? '#bfdbfe' : '#d1d5db',
    transition: 'all 0.2s'
  });

  return (
    <nav style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', userSelect: 'none' }} aria-label="Pagination">
      <button
        style={buttonStyle(false, canPrev)}
        onClick={() => canPrev && onChange(1)}
        disabled={!canPrev}
        aria-label="Trang đầu"
        title="Trang đầu"
        onMouseEnter={(e) => canPrev && (e.currentTarget.style.backgroundColor = '#f9fafb')}
        onMouseLeave={(e) => canPrev && (e.currentTarget.style.backgroundColor = 'white')}
      ><FirstPageIcon sx={{ fontSize: 16 }} /></button>
      <button
        style={buttonStyle(false, canPrev)}
        onClick={() => canPrev && onChange(page - 1)}
        disabled={!canPrev}
        aria-label="Trang trước"
        title="Trang trước"
        onMouseEnter={(e) => canPrev && (e.currentTarget.style.backgroundColor = '#f9fafb')}
        onMouseLeave={(e) => canPrev && (e.currentTarget.style.backgroundColor = 'white')}
      ><ChevronLeftIcon sx={{ fontSize: 16 }} /></button>

      {items.map((item, idx) => {
        if (typeof item === 'string') {
          return (
            <span key={`dots-${idx}`} style={{ padding: '0.5rem 0.75rem', fontSize: '0.875rem', color: '#6b7280' }}>…</span>
          );
        }
        const isActive = item === page;
        return (
          <button
            key={item}
            onClick={() => onChange(item)}
            style={buttonStyle(isActive, true)}
            aria-current={isActive ? 'page' : undefined}
            onMouseEnter={(e) => !isActive && (e.currentTarget.style.backgroundColor = '#f9fafb')}
            onMouseLeave={(e) => !isActive && (e.currentTarget.style.backgroundColor = 'white')}
          >{item}</button>
        );
      })}

      <button
        style={buttonStyle(false, canNext)}
        onClick={() => canNext && onChange(page + 1)}
        disabled={!canNext}
        aria-label="Trang sau"
        title="Trang sau"
        onMouseEnter={(e) => canNext && (e.currentTarget.style.backgroundColor = '#f9fafb')}
        onMouseLeave={(e) => canNext && (e.currentTarget.style.backgroundColor = 'white')}
      ><ChevronRightIcon sx={{ fontSize: 16 }} /></button>
      <button
        style={buttonStyle(false, canNext)}
        onClick={() => canNext && onChange(count)}
        disabled={!canNext}
        aria-label="Trang cuối"
        title="Trang cuối"
        onMouseEnter={(e) => canNext && (e.currentTarget.style.backgroundColor = '#f9fafb')}
        onMouseLeave={(e) => canNext && (e.currentTarget.style.backgroundColor = 'white')}
      ><LastPageIcon sx={{ fontSize: 16 }} /></button>
    </nav>
  );
};
