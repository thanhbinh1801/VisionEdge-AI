import React, { useState, useEffect } from 'react';
import { Shield, Bell, Activity, Radio, Volume2, VolumeX } from 'lucide-react';

interface HeaderProps {
  isMuted?: boolean;
  onToggleMute?: () => void;
}

export const Header: React.FC<HeaderProps> = ({ isMuted = false, onToggleMute }) => {
  const [time, setTime] = useState<string>(new Date().toLocaleTimeString('vi-VN'));

  useEffect(() => {
    const timer = setInterval(() => {
      setTime(new Date().toLocaleTimeString('vi-VN'));
    }, 1000);
    return () => clearInterval(timer);
  }, []);

  return (
    <header
      role="banner"
      aria-label="SentriAI Mini Header Navigation"
      className="h-16 bg-[#0f172a] border-b border-slate-800 px-6 flex items-center justify-between text-slate-100 sticky top-0 z-30 shadow-md"
    >
      <div className="flex items-center space-x-3">
        <div className="p-2 bg-indigo-600 rounded-lg shadow-lg shadow-indigo-500/30">
          <Shield className="w-6 h-6 text-white" aria-hidden="true" />
        </div>
        <div>
          <h1 className="text-lg font-bold tracking-wide flex items-center space-x-2">
            <span>SentriAI Mini</span>
            <span className="text-xs px-2 py-0.5 rounded bg-indigo-950 text-indigo-400 border border-indigo-800">
              v1.0.0
            </span>
          </h1>
          <p className="text-xs text-slate-400">Hệ Thống Giám Sát An Ninh AI Real-time</p>
        </div>
      </div>

      <div className="flex items-center space-x-4">
        <div className="flex items-center space-x-2 text-xs text-emerald-400 bg-emerald-950/60 px-3 py-1.5 rounded-full border border-emerald-800/80">
          <Radio className="w-4 h-4 animate-pulse" aria-hidden="true" />
          <span className="font-medium font-mono">YOLOv11s & OCR | FPS: 15.2 | Latency: 42ms</span>
        </div>

        <div className="flex items-center space-x-2 text-xs text-slate-300 bg-slate-900 px-3 py-1.5 rounded-lg border border-slate-800 font-mono">
          <Activity className="w-4 h-4 text-indigo-400" aria-hidden="true" />
          <span>{time}</span>
        </div>

        {onToggleMute && (
          <button
            type="button"
            onClick={onToggleMute}
            aria-label={isMuted ? 'Bật âm thanh cảnh báo bíp' : 'Tắt âm thanh cảnh báo bíp'}
            className={`p-2 rounded-lg border transition focus:outline-none focus:ring-2 focus:ring-indigo-500 ${
              isMuted
                ? 'bg-slate-900 border-red-800 text-red-400 hover:bg-slate-800'
                : 'bg-slate-900 border-slate-800 text-slate-300 hover:bg-slate-800'
            }`}
          >
            {isMuted ? <VolumeX className="w-5 h-5" /> : <Volume2 className="w-5 h-5" />}
          </button>
        )}

        <button
          type="button"
          aria-label="Thông báo cảnh báo mới"
          className="relative p-2 rounded-lg bg-slate-900 border border-slate-800 hover:bg-slate-800 transition text-slate-300 focus:outline-none focus:ring-2 focus:ring-indigo-500"
        >
          <Bell className="w-5 h-5" aria-hidden="true" />
          <span className="absolute top-1.5 right-1.5 w-2 h-2 rounded-full bg-red-500 animate-ping" />
        </button>
      </div>
    </header>
  );
};
