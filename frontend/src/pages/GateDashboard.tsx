import React from 'react';
import { KpiCard } from '../components/dashboard/KpiCard';
import { EventFeed } from '../components/dashboard/EventFeed';
import { Camera, Car, AlertTriangle, ShieldCheck } from 'lucide-react';
import { useApp } from '../context/AppContext';
import { ResponsiveContainer, BarChart, Bar, XAxis, YAxis, Tooltip } from 'recharts';

const mockHourlyData = [
  { hour: '08:00', lprCount: 12 },
  { hour: '09:00', lprCount: 24 },
  { hour: '10:00', lprCount: 35 },
  { hour: '11:00', lprCount: 18 },
  { hour: '12:00', lprCount: 8 },
];

export const GateDashboard: React.FC = () => {
  const { recentEvents } = useApp();

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-bold text-slate-100">Tab 1: Gate LPR Dashboard</h2>
          <p className="text-xs text-slate-400">Giám sát Cổng Vào GATE-01 & Nhận Dạng Biển Số Xe (LPR)</p>
        </div>
        <div className="px-3 py-1 bg-slate-900 border border-slate-800 text-xs text-indigo-300 rounded-lg">
          Camera: GATE-01 (1080p @ 15 FPS)
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <KpiCard
          title="Tổng Xe Vào Cổng"
          value={97}
          subtitle="Ghi nhận hôm nay"
          icon={<Car className="w-5 h-5" />}
          trend="+12%"
          trendType="positive"
        />
        <KpiCard
          title="Nhận Dạng OCR Thành Công"
          value="98.5%"
          subtitle="Độ chính xác LPR"
          icon={<ShieldCheck className="w-5 h-5" />}
          trend="Đạt chỉ tiêu"
          trendType="positive"
        />
        <KpiCard
          title="Cảnh Báo Xe Đen (Blacklist)"
          value={2}
          subtitle="Xe thuộc danh sách cấm"
          icon={<AlertTriangle className="w-5 h-5" />}
          trend="Cần xử lý"
          trendType="negative"
        />
        <KpiCard
          title="Camera Stream Status"
          value="ONLINE"
          subtitle="RTSP / OpenCV Ingestion"
          icon={<Camera className="w-5 h-5" />}
          trend="Latency 45ms"
          trendType="positive"
        />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2 space-y-4">
          <div className="bg-[#0f172a] border border-slate-800 rounded-xl p-4">
            <div className="flex items-center justify-between mb-3">
              <h3 className="text-sm font-semibold text-slate-200">
                Luồng Camera Live: GATE-01 (YOLOv26 BBox + LPR Overlay)
              </h3>
              <span className="text-[11px] text-emerald-400 font-mono">LIVE Stream 15 FPS</span>
            </div>
            <div className="aspect-video bg-slate-950 rounded-lg border border-slate-800 flex items-center justify-center relative overflow-hidden">
              <div className="text-slate-600 text-sm font-mono">[GATE-01 Simulated Video Stream Feed]</div>
              <div className="absolute top-4 left-4 bg-slate-900/90 backdrop-blur border border-slate-700 px-3 py-1.5 rounded text-xs space-y-0.5">
                <div className="text-indigo-400 font-mono font-semibold">Plate: 29A-888.88</div>
                <div className="text-slate-400 text-[10px]">Conf: 99.2% • Vehicle: Truck</div>
              </div>
            </div>
          </div>

          <div className="bg-[#0f172a] border border-slate-800 rounded-xl p-4">
            <h3 className="text-sm font-semibold text-slate-200 mb-3">
              Biểu Đồ Xu Hướng Xe Vào Cổng Theo Giờ (Recharts)
            </h3>
            <div className="h-48 w-full">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={mockHourlyData}>
                  <XAxis dataKey="hour" stroke="#64748b" fontSize={12} />
                  <YAxis stroke="#64748b" fontSize={12} />
                  <Tooltip
                    contentStyle={{ backgroundColor: '#0f172a', borderColor: '#334155', color: '#f8fafc' }}
                  />
                  <Bar dataKey="lprCount" fill="#6366f1" radius={[4, 4, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
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
