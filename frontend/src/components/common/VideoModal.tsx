import React from 'react';

interface VideoModalProps {
  videoUrl: string | null;
  onClose: () => void;
}

export const VideoModal: React.FC<VideoModalProps> = ({ videoUrl, onClose }) => {
  if (!videoUrl) return null;

  return (
    <div
      style={{
        position: 'fixed',
        inset: 0,
        zIndex: 50,
        background: 'rgba(0,0,0,0.75)',
        backdropFilter: 'blur(4px)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        padding: '16px',
      }}
      onClick={onClose}
    >
      <div
        style={{
          position: 'relative',
          width: '100%',
          maxWidth: '800px',
          background: 'var(--panel)',
          border: '1px solid var(--line2)',
          borderRadius: '12px',
          overflow: 'hidden',
        }}
        onClick={(e) => e.stopPropagation()}
      >
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '12px 16px', borderBottom: '1px solid var(--line)' }}>
          <span style={{ fontSize: '13px', fontWeight: 600 }}>Xem Lại Đoạn Video Sự Kiện (10s Clip)</span>
          <button
            onClick={onClose}
            style={{
              background: 'transparent',
              border: 'none',
              color: 'var(--ink2)',
              cursor: 'pointer',
              fontSize: '14px',
              fontWeight: 700,
            }}
          >
            ✕
          </button>
        </div>
        <div style={{ position: 'relative', aspectRatio: '16/9', background: '#000' }}>
          <video src={videoUrl} controls autoPlay className="w-full h-full object-contain" />
        </div>
      </div>
    </div>
  );
};
