import React from 'react';
import { formatDistanceToNow } from 'date-fns';
import { vi } from 'date-fns/locale';
import LinkIcon from '@mui/icons-material/Link';
import ImageIcon from '@mui/icons-material/Image';
import CheckCircleIcon from '@mui/icons-material/CheckCircle';
import FiberManualRecordIcon from '@mui/icons-material/FiberManualRecord';

function TopicBadge({ topic }) {
  return (
    <span style={{
      padding: '0.125rem 0.5rem',
      backgroundColor: '#f3f4f6',
      fontSize: '0.75rem',
      borderRadius: '0.25rem',
      color: '#374151'
    }}>
      #{topic}
    </span>
  );
}

export function PostCard({ post, onClick }) {
  let timeAgo = 'Unknown date';
  let displayDate = 'Unknown date';
  
  try {
    if (post.created_at) {
      const date = new Date(post.created_at);
      timeAgo = formatDistanceToNow(date, {
        addSuffix: true,
        locale: vi,
      });
      // Format: "02/01/2026 05:19"
      displayDate = `${date.getDate().toString().padStart(2, '0')}/${(date.getMonth() + 1).toString().padStart(2, '0')}/${date.getFullYear()} ${date.getHours().toString().padStart(2, '0')}:${date.getMinutes().toString().padStart(2, '0')}`;
    }
  } catch (error) {
    console.error('Error formatting date:', error, post.created_at);
  }

  return (
    <article
      style={{
        backgroundColor: 'white',
        borderBottom: '1px solid #e5e7eb',
        transition: 'background-color 0.2s',
        cursor: 'pointer'
      }}
      onClick={onClick}
      onMouseEnter={(e) => e.currentTarget.style.backgroundColor = '#f9fafb'}
      onMouseLeave={(e) => e.currentTarget.style.backgroundColor = 'white'}
    >
      <div style={{ padding: '1.25rem 1.5rem' }}>
        {/* Header: Source + Author + Time */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', marginBottom: '0.75rem', flexWrap: 'wrap' }}>
          <span style={{ display: 'inline-flex', alignItems: 'center', gap: '0.375rem', fontSize: '0.875rem', fontWeight: 500, color: '#111827' }}>
            <span style={{ display: 'inline-flex', alignItems: 'center' }}>
              <FiberManualRecordIcon sx={{ color: '#2563eb', fontSize: 12 }} />
            </span>
            {post.source}
          </span>
          {post.author && (
            <>
              <span style={{ color: '#d1d5db' }}>•</span>
              <span style={{ fontSize: '0.875rem', color: '#4b5563' }}>@{post.author}</span>
            </>
          )}
          <span style={{ color: '#d1d5db' }}>•</span>
          <time style={{ fontSize: '0.875rem', color: '#6b7280' }} title={displayDate}>
            {displayDate}
          </time>
        </div>

        {/* Main Content */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
          {/* Post Text - Always show */}
          <p style={{
            fontSize: '1rem',
            color: '#1f2937',
            lineHeight: '1.6',
            display: '-webkit-box',
            WebkitLineClamp: 4,
            WebkitBoxOrient: 'vertical',
            overflow: 'hidden'
          }}>
            {post.text}
          </p>
          
          {/* Show "Đọc thêm" button if has external link */}
          {post.links && post.links.length > 0 && !post.links[0].includes('t.me') && (
            <a
              href={post.links[0]}
              target="_blank"
              rel="noopener noreferrer"
              onClick={(e) => e.stopPropagation()}
              style={{
                display: 'inline-flex',
                alignItems: 'center',
                gap: '0.25rem',
                fontSize: '0.875rem',
                color: '#2563eb',
                fontWeight: 500,
                textDecoration: 'none',
                width: 'fit-content'
              }}
              onMouseEnter={(e) => e.currentTarget.style.textDecoration = 'underline'}
              onMouseLeave={(e) => e.currentTarget.style.textDecoration = 'none'}
            >
              <LinkIcon sx={{ fontSize: 16 }} />
              Đọc bài gốc
            </a>
          )}

          {/* Full article snippet if available */}
          {post.full_article?.content && (
            <p style={{
              fontSize: '0.875rem',
              color: '#4b5563',
              display: '-webkit-box',
              WebkitLineClamp: 3,
              WebkitBoxOrient: 'vertical',
              overflow: 'hidden',
              fontStyle: 'italic',
              borderLeft: '3px solid #e5e7eb',
              paddingLeft: '0.75rem'
            }}>
              {post.full_article.content.slice(0, 200)}...
            </p>
          )}
        </div>

        {/* Footer: Topics + Stats */}
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginTop: '1rem' }}>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.5rem' }}>
            {post.topics && post.topics.length > 0 ? (
              post.topics.slice(0, 3).map((topic) => (
                <TopicBadge key={topic} topic={topic} />
              ))
            ) : (
              <span style={{ fontSize: '0.75rem', color: '#9ca3af', fontStyle: 'italic' }}>Chưa phân loại</span>
            )}
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: '1rem', fontSize: '0.875rem', color: '#6b7280' }}>
            {post.links.length > 0 && (
              <span style={{ display: 'flex', alignItems: 'center', gap: '0.25rem' }}>
                <LinkIcon sx={{ fontSize: 16, color: '#6b7280' }} />
                {post.links.length}
              </span>
            )}
            {post.media.length > 0 && (
              <span style={{ display: 'flex', alignItems: 'center', gap: '0.25rem' }}>
                <ImageIcon sx={{ fontSize: 16, color: '#6b7280' }} />
                {post.media.length}
              </span>
            )}
            <span style={{ display: 'flex', alignItems: 'center', gap: '0.25rem' }}>
              <CheckCircleIcon sx={{ fontSize: 16, color: '#6b7280' }} />
              {post.score}
            </span>
          </div>
        </div>
      </div>
    </article>
  );
}
