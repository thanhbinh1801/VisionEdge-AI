import React from 'react';
import { KpiCard } from '../components/dashboard/KpiCard';
import { EventFeed } from '../components/dashboard/EventFeed';
import { ShieldAlert, AlertTriangle, Eye, Video } from 'lucide-react';
import { useApp } from '../context/AppContext';

export const AreaSecurityDashboard: React.FC = () => {
  const { recentEvents } = useApp();

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-bold text-slate-100">Tab 2: Area Security Dashboard</h2>
          <p className="text-xs text-slate-400">Giám Sát Vùng Cấm / Vùng Nguy Hiểm Bãi Kiểm (BAI-KIEM)</p>
        </div>
        <div className="px-3 py-1 bg-slate-900 border border-slate-800 text-xs text-amber-300 rounded-lg">
          Camera: BAI-KIEM (1080p @ 15 FPS)
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <KpiCard
          title="Vi Phạm Mức 3 (Đỏ)"
          value={3}
          subtitle="Cảnh báo khẩn cấp"
          icon={<AlertTriangle className="w-5 h-5 text-red-400" />}
          trend="Phát Beep Sound"
          trendType="negative"
        />
        <KpiCard
          title="Vi Phạm Mức 2 (Vàng)"
          value={8}
          subtitle="Xâm nhập vùng chú ý"
          icon={<ShieldAlert className="w-5 h-5 text-amber-400" />}
          trend="Đã ghi nhận"
          trendType="neutral"
        />
        <KpiCard
          title="Zone Đang Kích Hoạt"
          value={4}
          subtitle="Đa giác Ray-Casting PIP"
          icon={<Eye className="w-5 h-5" />}
          trend="Bảo vệ 24/7"
          trendType="positive"
        />
        <KpiCard
          title="Ring Buffer Video Clips"
          value="12 Files"
          subtitle="Video 10s tự động trích xuất"
          icon={<Video className="w-5 h-5" />}
          trend="Cooldown 10-15s"
          trendType="positive"
        />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2 space-y-4">
          <div className="bg-[#0f172a] border border-slate-800 rounded-xl p-4">
            <div className="flex items-center justify-between mb-3">
              <h3 className="text-sm font-semibold text-slate-200">
                Luồng Camera Live: BAI-KIEM (Zone Polygon Bounding Polygon Overlay)
              </h3>
              <span className="text-[11px] text-amber-400 font-mono">Ray-Casting Active</span>
            </div>
            <div className="aspect-video bg-slate-950 rounded-lg border border-slate-800 flex items-center justify-center relative overflow-hidden">
              <div className="text-slate-600 text-sm font-mono">[BAI-KIEM Simulated Video Stream Feed]</div>
              <svg className="absolute inset-0 w-full h-full">
                <polygon
                  points="20%,20% 80%,20% 70%,80% 30%,80%"
                  fill="rgba(239, 68, 68, 0.2)"
                  stroke="#ef4444"
                  strokeWidth="2"
                  strokeDasharray="4 4"
                />
              </svg>
            </div>
          </div>
        </div>

        <div>
          <EventFeed events={recentEvents} />
        </div>
      </div>
    </div>
  );
};
