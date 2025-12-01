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
  const timeAgo = formatDistanceToNow(new Date(post.created_at), {
    addSuffix: true,
    locale: vi,
  });

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
        {/* Header: Source + Time */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', marginBottom: '0.75rem' }}>
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
          <time style={{ fontSize: '0.875rem', color: '#6b7280' }}>{timeAgo}</time>
        </div>

        {/* Main Content */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
          {/* Title - clickable to open full article */}
          {post.full_article?.title ? (
            <a 
              href={post.links[0] || '#'}
              target="_blank"
              rel="noopener noreferrer"
              onClick={(e) => e.stopPropagation()}
              style={{ display: 'block', textDecoration: 'none' }}
            >
              <h2 style={{
                fontSize: '1.25rem',
                fontWeight: 600,
                color: '#111827',
                display: '-webkit-box',
                WebkitLineClamp: 2,
                WebkitBoxOrient: 'vertical',
                overflow: 'hidden',
                transition: 'color 0.2s'
              }}
              onMouseEnter={(e) => e.currentTarget.style.color = '#2563eb'}
              onMouseLeave={(e) => e.currentTarget.style.color = '#111827'}
              >
                {post.full_article.title}
              </h2>
            </a>
          ) : post.links.length > 0 ? (
            <a
              href={post.links[0]}
              target="_blank"
              rel="noopener noreferrer"
              onClick={(e) => e.stopPropagation()}
              style={{ display: 'block', textDecoration: 'none' }}
            >
              <p style={{
                fontSize: '1.125rem',
                fontWeight: 500,
                color: '#1f2937',
                display: '-webkit-box',
                WebkitLineClamp: 2,
                WebkitBoxOrient: 'vertical',
                overflow: 'hidden',
                transition: 'color 0.2s'
              }}
              onMouseEnter={(e) => e.currentTarget.style.color = '#2563eb'}
              onMouseLeave={(e) => e.currentTarget.style.color = '#1f2937'}
              >
                {post.text}
              </p>
            </a>
          ) : (
            <p style={{
              fontSize: '1.125rem',
              fontWeight: 500,
              color: '#1f2937',
              display: '-webkit-box',
              WebkitLineClamp: 2,
              WebkitBoxOrient: 'vertical',
              overflow: 'hidden'
            }}>
              {post.text}
            </p>
          )}

          {/* Snippet */}
          {post.full_article?.content && (
            <p style={{
              fontSize: '0.875rem',
              color: '#4b5563',
              display: '-webkit-box',
              WebkitLineClamp: 3,
              WebkitBoxOrient: 'vertical',
              overflow: 'hidden'
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
