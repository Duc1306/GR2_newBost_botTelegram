/**
 * AudioPlayer – mini sticky bottom bar để phát audio TTS bản tin.
 * Props:
 *   audioUrl  {string}  – Blob URL (từ URL.createObjectURL)
 *   title     {string}  – Tên chủ đề / tiêu đề để hiển thị
 *   onClose   {fn}      – Callback khi người dùng đóng player
 */
import React, { useRef, useState, useEffect } from 'react';
import {
  Box,
  IconButton,
  Typography,
  Tooltip,
  Chip,
} from '@mui/material';
import PlayArrowIcon from '@mui/icons-material/PlayArrow';
import PauseIcon from '@mui/icons-material/Pause';
import CloseIcon from '@mui/icons-material/Close';
import VolumeUpIcon from '@mui/icons-material/VolumeUp';

const SPEEDS = [1, 1.25, 1.5, 2];

export default function AudioPlayer({ audioUrl, title, onClose }) {
  const audioRef = useRef(null);
  const [playing, setPlaying] = useState(false);
  const [speed, setSpeed] = useState(1);
  const [progress, setProgress] = useState(0);   // 0–100
  const [duration, setDuration] = useState(0);
  const [currentTime, setCurrentTime] = useState(0);

  // Auto-play khi audioUrl thay đổi
  useEffect(() => {
    if (!audioRef.current || !audioUrl) return;
    audioRef.current.src = audioUrl;
    audioRef.current.load();
    audioRef.current.play().then(() => setPlaying(true)).catch(() => {});
  }, [audioUrl]);

  // Đồng bộ playbackRate khi speed thay đổi
  useEffect(() => {
    if (audioRef.current) audioRef.current.playbackRate = speed;
  }, [speed]);

  const togglePlay = () => {
    const a = audioRef.current;
    if (!a) return;
    if (playing) { a.pause(); setPlaying(false); }
    else { a.play().then(() => setPlaying(true)).catch(() => {}); }
  };

  const handleTimeUpdate = () => {
    const a = audioRef.current;
    if (!a || !a.duration) return;
    setCurrentTime(a.currentTime);
    setProgress((a.currentTime / a.duration) * 100);
  };

  const handleLoadedMetadata = () => {
    if (audioRef.current) setDuration(audioRef.current.duration);
  };

  const handleEnded = () => {
    setPlaying(false);
    setProgress(0);
    setCurrentTime(0);
  };

  const handleSeek = (e) => {
    const a = audioRef.current;
    if (!a || !a.duration) return;
    const rect = e.currentTarget.getBoundingClientRect();
    const ratio = (e.clientX - rect.left) / rect.width;
    a.currentTime = ratio * a.duration;
  };

  const cycleSpeed = () => {
    const next = SPEEDS[(SPEEDS.indexOf(speed) + 1) % SPEEDS.length];
    setSpeed(next);
  };

  const fmt = (s) => {
    if (!s || isNaN(s)) return '0:00';
    const m = Math.floor(s / 60);
    const sec = Math.floor(s % 60).toString().padStart(2, '0');
    return `${m}:${sec}`;
  };

  if (!audioUrl) return null;

  return (
    <Box
      sx={{
        position: 'fixed',
        bottom: 0,
        left: 0,
        right: 0,
        zIndex: 1400,
        bgcolor: 'rgba(17,24,39,0.97)',
        backdropFilter: 'blur(8px)',
        color: 'white',
        borderTop: '2px solid #f97316',
        px: { xs: 1.5, sm: 3 },
        py: 0.75,
      }}
    >
      {/* Thanh progress (click để seek) */}
      <Box
        onClick={handleSeek}
        sx={{
          position: 'absolute',
          top: 0,
          left: 0,
          right: 0,
          height: 3,
          bgcolor: 'rgba(255,255,255,0.15)',
          cursor: 'pointer',
          '&:hover': { height: 5, top: -1 },
          transition: 'height 0.15s',
        }}
      >
        <Box
          sx={{
            height: '100%',
            width: `${progress}%`,
            bgcolor: '#f97316',
            borderRadius: '0 2px 2px 0',
            transition: 'width 0.3s linear',
          }}
        />
      </Box>

      <Box display="flex" alignItems="center" gap={{ xs: 0.75, sm: 1.5 }}>
        {/* Icon */}
        <VolumeUpIcon sx={{ fontSize: 18, color: '#f97316', flexShrink: 0, display: { xs: 'none', sm: 'block' } }} />

        {/* Play / Pause */}
        <Tooltip title={playing ? 'Tạm dừng' : 'Phát'}>
          <IconButton
            onClick={togglePlay}
            size="small"
            sx={{
              color: 'white',
              bgcolor: '#f97316',
              flexShrink: 0,
              width: 34,
              height: 34,
              '&:hover': { bgcolor: '#ea580c' },
            }}
          >
            {playing ? <PauseIcon sx={{ fontSize: 20 }} /> : <PlayArrowIcon sx={{ fontSize: 20 }} />}
          </IconButton>
        </Tooltip>

        {/* Tiêu đề bản tin – marquee trên mobile */}
        <Box sx={{ flex: 1, overflow: 'hidden', minWidth: 0 }}>
          <Typography
            variant="caption"
            sx={{
              display: 'block',
              color: '#9ca3af',
              fontSize: '0.65rem',
              letterSpacing: 0.5,
              mb: 0.1,
            }}
          >
            Đang phát
          </Typography>
          <Box sx={{ overflow: 'hidden' }}>
            <Typography
              component="span"
              variant="body2"
              fontWeight={600}
              sx={{
                display: 'inline-block',
                whiteSpace: 'nowrap',
                fontSize: { xs: '0.78rem', sm: '0.875rem' },
                ...(title && title.length > 50 && {
                  animation: 'marqueeScroll 12s linear infinite',
                  '@keyframes marqueeScroll': {
                    '0%': { transform: 'translateX(0)' },
                    '100%': { transform: 'translateX(-50%)' },
                  },
                }),
              }}
            >
              {title}
              {title && title.length > 50 ? `\u00A0\u00A0\u00A0\u00A0${title}` : ''}
            </Typography>
          </Box>
        </Box>

        {/* Thời gian */}
        <Typography
          variant="caption"
          sx={{ color: '#9ca3af', flexShrink: 0, fontSize: '0.72rem', display: { xs: 'none', sm: 'block' } }}
        >
          {fmt(currentTime)} / {fmt(duration)}
        </Typography>

        {/* Tốc độ */}
        <Tooltip title="Tốc độ phát">
          <Chip
            label={`${speed}x`}
            size="small"
            onClick={cycleSpeed}
            sx={{
              bgcolor: 'rgba(249,115,22,0.2)',
              color: '#f97316',
              fontWeight: 700,
              fontSize: '0.72rem',
              height: 24,
              cursor: 'pointer',
              flexShrink: 0,
              '&:hover': { bgcolor: 'rgba(249,115,22,0.35)' },
            }}
          />
        </Tooltip>

        {/* Đóng */}
        <Tooltip title="Đóng">
          <IconButton
            size="small"
            onClick={onClose}
            sx={{ color: '#6b7280', flexShrink: 0, '&:hover': { color: 'white' } }}
          >
            <CloseIcon sx={{ fontSize: 18 }} />
          </IconButton>
        </Tooltip>
      </Box>

      {/* Hidden audio element */}
      <audio
        ref={audioRef}
        onTimeUpdate={handleTimeUpdate}
        onLoadedMetadata={handleLoadedMetadata}
        onEnded={handleEnded}
        style={{ display: 'none' }}
      />
    </Box>
  );
}
