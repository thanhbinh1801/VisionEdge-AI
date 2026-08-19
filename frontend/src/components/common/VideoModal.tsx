import React, { useEffect, useRef } from 'react';
import { X, Play, Download } from 'lucide-react';
import { useApp } from '../../context/AppContext';

export const VideoModal: React.FC = () => {
  const { selectedVideoClipUrl, setSelectedVideoClipUrl } = useApp();
  const closeButtonRef = useRef<HTMLButtonElement | null>(null);

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && selectedVideoClipUrl) {
        setSelectedVideoClipUrl(null);
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [selectedVideoClipUrl, setSelectedVideoClipUrl]);

  useEffect(() => {
    if (selectedVideoClipUrl && closeButtonRef.current) {
      closeButtonRef.current.focus();
    }
  }, [selectedVideoClipUrl]);

  if (!selectedVideoClipUrl) return null;

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-labelledby="video-modal-title"
      className="fixed inset-0 z-50 bg-black/80 backdrop-blur-sm flex items-center justify-center p-4"
    >
      <div className="bg-[#0f172a] border border-slate-700 rounded-xl w-full max-w-3xl overflow-hidden shadow-2xl animate-fade-in">
        <div className="flex items-center justify-between p-4 border-b border-slate-800">
          <div className="flex items-center space-x-2 font-semibold text-slate-200" id="video-modal-title">
            <Play className="w-5 h-5 text-indigo-400" aria-hidden="true" />
            <span>Xem Clip Bằng Chứng 10s (Ring Buffer MP4)</span>
          </div>
          <button
            ref={closeButtonRef}
            type="button"
            onClick={() => setSelectedVideoClipUrl(null)}
            aria-label="Đóng cửa sổ phát video"
            className="p-1 rounded-lg text-slate-400 hover:text-slate-100 hover:bg-slate-800 focus:outline-none focus:ring-2 focus:ring-indigo-500"
          >
            <X className="w-5 h-5" aria-hidden="true" />
          </button>
        </div>

        <div className="relative aspect-video bg-black flex items-center justify-center">
          <video
            src={selectedVideoClipUrl}
            controls
            autoPlay
            className="w-full h-full object-contain"
          >
            Trình duyệt không hỗ trợ phát video.
          </video>
        </div>

        <div className="p-4 bg-slate-900 border-t border-slate-800 flex items-center justify-between">
          <div className="text-xs text-slate-400">
            Đoạn video được trích xuất tự động trước & sau thời điểm vi phạm (cooldown 10-15s).
          </div>
          <a
            href={selectedVideoClipUrl}
            download
            className="flex items-center space-x-2 px-3 py-1.5 text-xs font-medium bg-slate-800 hover:bg-slate-700 text-slate-200 rounded-lg border border-slate-700 focus:outline-none focus:ring-2 focus:ring-indigo-500"
          >
            <Download className="w-4 h-4" aria-hidden="true" />
            <span>Tải Video MP4</span>
          </a>
        </div>
      </div>
    </div>
  );
};
