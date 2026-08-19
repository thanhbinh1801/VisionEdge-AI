import React from 'react';
import { EventRecord } from '../../types';
import { Video, Clock } from 'lucide-react';
import { useApp } from '../../context/AppContext';

interface EventFeedProps {
  events: EventRecord[];
}

export const EventFeed: React.FC<EventFeedProps> = ({ events }) => {
  const { setSelectedVideoClipUrl } = useApp();

  const getBadgeClass = (severity: number) => {
    if (severity === 1) return 'badge-severity-1';
    if (severity === 2) return 'badge-severity-2';
    return 'badge-severity-3';
  };

  return (
    <div className="bg-[#0f172a] border border-slate-800 rounded-xl overflow-hidden flex flex-col h-full">
      <div className="p-4 border-b border-slate-800 flex items-center justify-between">
        <h3 className="text-sm font-semibold text-slate-200 flex items-center space-x-2">
          <Clock className="w-4 h-4 text-indigo-400" />
          <span>Sự Kiện Real-time Bãi Kiểm / Cổng</span>
        </h3>
        <span className="text-xs text-slate-400">{events.length} ghi nhận</span>
      </div>

      <div className="p-4 space-y-3 overflow-y-auto max-h-[480px]">
        {events.length === 0 ? (
          <div className="text-center py-8 text-slate-500 text-xs">
            Chưa có sự kiện vi phạm hoặc nhận dạng mới.
          </div>
        ) : (
          events.map((evt) => (
            <div
              key={evt.id}
              className="p-3 bg-slate-900 border border-slate-800 rounded-lg flex items-center justify-between hover:border-slate-700 transition"
            >
              <div className="flex items-center space-x-3">
                <div
                  className={`px-2 py-1 text-xs font-semibold rounded ${getBadgeClass(
                    evt.severity
                  )}`}
                >
                  Mức {evt.severity}
                </div>
                <div>
                  <div className="text-xs font-semibold text-slate-200 flex items-center space-x-2">
                    <span>{evt.cameraName}</span>
                    {evt.plateNumber && (
                      <span className="px-1.5 py-0.5 text-[10px] bg-slate-800 text-indigo-300 rounded border border-slate-700 font-mono">
                        {evt.plateNumber}
                      </span>
                    )}
                  </div>
                  <div className="text-[11px] text-slate-400 mt-0.5">
                    {evt.eventType} • {evt.objectClass} ({Math.round(evt.confidence * 100)}%)
                  </div>
                </div>
              </div>

              <div className="flex items-center space-x-2">
                <span className="text-[10px] text-slate-400">{evt.timestamp}</span>
                {evt.videoClipUrl && (
                  <button
                    onClick={() => setSelectedVideoClipUrl(evt.videoClipUrl || null)}
                    className="p-1.5 text-xs bg-indigo-950 text-indigo-300 hover:bg-indigo-900 rounded border border-indigo-800 flex items-center space-x-1"
                  >
                    <Video className="w-3.5 h-3.5" />
                    <span>Clip 10s</span>
                  </button>
                )}
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
};
