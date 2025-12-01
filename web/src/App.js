import React, { useState, useEffect } from 'react';
import { fetchPosts, fetchStats, fetchTopics, fetchPostsCount } from './lib/api';
import { Pagination } from './components/Pagination';
import { PostCard } from './components/PostCard';
import { FilterSidebar } from './components/FilterSidebar';
import TextField from '@mui/material/TextField';
import Box from '@mui/material/Box';
import InputAdornment from '@mui/material/InputAdornment';
import SearchIcon from '@mui/icons-material/Search';

function App() {
  const [posts, setPosts] = useState([]);
  const [topics, setTopics] = useState([]);
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [selectedTopic, setSelectedTopic] = useState(undefined);
  const [selectedLanguage, setSelectedLanguage] = useState(undefined);
  const [searchQuery, setSearchQuery] = useState('');
  const [debouncedSearchQuery, setDebouncedSearchQuery] = useState('');
  const [page, setPage] = useState(1);
  const linkOnly = true;
  const postsPerPage = 20;
  const [totalCount, setTotalCount] = useState(null);

  // Debounce search query
  useEffect(() => {
    const timer = setTimeout(() => {
      setDebouncedSearchQuery(searchQuery);
      setPage(1);
    }, 500);

    return () => clearTimeout(timer);
  }, [searchQuery]);

  useEffect(() => {
    async function loadData() {
      try {
        setLoading(true);
        setError(null);
        
        console.log('[Page] Loading data with filters:', {
          selectedTopic,
          selectedLanguage,
          searchQuery: debouncedSearchQuery,
          page,
        });
        
        const [postsData, topicsData, statsData, total] = await Promise.all([
          fetchPosts({
            topic: selectedTopic,
            lang: selectedLanguage,
            q: debouncedSearchQuery || undefined,
            limit: postsPerPage,
            skip: (page - 1) * postsPerPage,
            link_only: linkOnly,
            topics_only: true,
          }),
          fetchTopics(),
          fetchStats({ link_only: linkOnly, topics_only: true }),
          fetchPostsCount({ topic: selectedTopic, lang: selectedLanguage, link_only: linkOnly, topics_only: true })
        ]);
        
        console.log('[Page] Data loaded:', {
          postsCount: postsData.length,
          totalCount: total,
          firstPostTopics: postsData[0]?.topics,
        });
        
        setPosts(postsData);
        setTotalCount(total);
        setTopics(topicsData);
        setStats(statsData);
      } catch (err) {
        const errorMsg = err instanceof Error ? err.message : 'Failed to load data';
        setError(errorMsg);
        console.error('API Error:', err);
        setPosts([]);
        setTopics([]);
        setStats(null);
      } finally {
        setLoading(false);
      }
    }
    loadData();
  }, [selectedTopic, selectedLanguage, debouncedSearchQuery, page, linkOnly]);

  const languages = ['vi', 'en'];

  return (
    <div className="flex min-h-screen bg-gray-50">
      <FilterSidebar
        topics={topics}
        selectedTopic={selectedTopic}
        onTopicChange={(topic) => { setSelectedTopic(topic); setPage(1); }}
        languages={languages}
        selectedLanguage={selectedLanguage}
        onLanguageChange={(lang) => { setSelectedLanguage(lang); setPage(1); }}
        stats={stats}
      />
      <main style={{ flex: 1, marginLeft: 320, minWidth: 0 }}>
        <Box sx={{ 
          position: 'sticky', 
          top: 0, 
          zIndex: 10, 
          bgcolor: '#ffffff', 
          borderBottom: '1px solid #e0e0e0', 
          px: 3, 
          py: 2,
          boxShadow: '0 1px 3px rgba(0,0,0,0.1)',
          ml: 0
        }}>
          <TextField
            fullWidth
            size="small"
            placeholder="Tìm kiếm bài viết..."
            value={searchQuery}
            onChange={(e) => { setSearchQuery(e.target.value); }}
            InputProps={{
              startAdornment: (
                <InputAdornment position="start">
                  <SearchIcon sx={{ color: '#666' }} />
                </InputAdornment>
              ),
              sx: {
                bgcolor: '#ffffff',
                '& input': {
                  color: '#000000',
                  fontSize: '16px',
                  fontWeight: 400,
                }
              }
            }}
            sx={{ 
              mb: 1,
              '& .MuiOutlinedInput-root': {
                bgcolor: '#ffffff',
                '& fieldset': {
                  borderColor: '#d0d0d0',
                },
                '&:hover fieldset': {
                  borderColor: '#2196f3',
                },
                '&.Mui-focused fieldset': {
                  borderColor: '#2196f3',
                }
              }
            }}
          />
          <Box sx={{ fontSize: '0.75rem', color: '#666' }}>
            Đang hiển thị: chỉ các bài có link bên ngoài
          </Box>
        </Box>
        <div className="max-w-4xl mx-auto">
          {loading ? (
            <div className="flex items-center justify-center h-64">
              <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
            </div>
          ) : error ? (
            <div style={{ margin: '1.5rem', padding: '1.5rem', backgroundColor: '#fee', border: '1px solid #fcc', borderRadius: '8px' }}>
              <p style={{ color: '#c00', fontWeight: 500 }}>❌ {error}</p>
              <p style={{ fontSize: '0.875rem', color: '#a00', marginTop: '0.5rem' }}>
                Backend chưa chạy. Chạy lệnh:
              </p>
              <code style={{ display: 'block', marginTop: '0.5rem', padding: '0.5rem', backgroundColor: '#fdd', borderRadius: '4px', fontSize: '0.875rem' }}>
                scripts\run_api.cmd
              </code>
            </div>
          ) :
           posts.length === 0 ? <div style={{ padding: '2rem' }}>No posts found</div> :
           <div>
             <div style={{ padding: '0.75rem 1.5rem', fontSize: '0.75rem', color: '#666', display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
               <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                 <span style={{ fontWeight: 500 }}>{selectedTopic ? `Chủ đề: ${selectedTopic}` : 'Tất cả chủ đề'}</span>
                 <span style={{ color: '#999' }}>• {totalCount ?? 0} bài</span>
               </div>
               <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
                 <Pagination
                   count={totalCount ? Math.max(1, Math.ceil(totalCount / postsPerPage)) : 1}
                   page={page}
                   onChange={(p) => setPage(p)}
                   siblingCount={1}
                   boundaryCount={1}
                 />
               </div>
             </div>
             {posts.map((post) => <PostCard key={post.id} post={post} />)}
             <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', padding: '1.5rem' }}>
               <Pagination
                 count={totalCount ? Math.max(1, Math.ceil(totalCount / postsPerPage)) : 1}
                 page={page}
                 onChange={(p) => setPage(p)}
                 siblingCount={1}
                 boundaryCount={1}
               />
             </div>
           </div>}
        </div>
      </main>
    </div>
  );
}

export default App;
