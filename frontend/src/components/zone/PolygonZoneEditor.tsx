import React, { useRef } from 'react';
import { usePolygonEditor } from '../../hooks/usePolygonEditor';
import { Trash2, PlusCircle } from 'lucide-react';

interface PolygonZoneEditorProps {
  onSaveZone?: (points: [number, number][]) => void;
}

export const PolygonZoneEditor: React.FC<PolygonZoneEditorProps> = ({ onSaveZone }) => {
  const canvasRef = useRef<SVGSVGElement | null>(null);
  const { points, addPoint, clearPoints } = usePolygonEditor([
    [0.1, 0.1],
    [0.9, 0.1],
    [0.8, 0.8],
    [0.2, 0.8],
  ]);

  const handleCanvasClick = (e: React.MouseEvent<SVGSVGElement>) => {
    if (!canvasRef.current) return;
    const rect = canvasRef.current.getBoundingClientRect();
    const relX = Number(((e.clientX - rect.left) / rect.width).toFixed(3));
    const relY = Number(((e.clientY - rect.top) / rect.height).toFixed(3));
    addPoint(relX, relY);
  };

  const pointsSvgString = points.map(([x, y]) => `${x * 100}%,${y * 100}%`).join(' ');

  return (
    <div className="bg-[#0f172a] border border-slate-800 rounded-xl p-4 space-y-3">
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-semibold text-slate-200">
          Vẽ Vùng Cảnh Báo SVG (Zone Canvas)
        </h3>
        <div className="flex items-center space-x-2">
          <button
            onClick={clearPoints}
            className="flex items-center space-x-1 px-3 py-1 text-xs bg-slate-800 text-slate-300 rounded border border-slate-700 hover:bg-slate-700"
          >
            <Trash2 className="w-3.5 h-3.5" />
            <span>Xóa Đỉnh</span>
          </button>
          <button
            onClick={() => onSaveZone && onSaveZone(points)}
            className="flex items-center space-x-1 px-3 py-1 text-xs bg-indigo-600 text-white rounded font-medium hover:bg-indigo-500"
          >
            <PlusCircle className="w-3.5 h-3.5" />
            <span>Lưu Zone</span>
          </button>
        </div>
      </div>

      <div className="relative aspect-video bg-slate-950 border border-slate-800 rounded-lg overflow-hidden cursor-crosshair">
        {/* Mock background frame */}
        <div className="absolute inset-0 flex items-center justify-center text-slate-700 text-xs font-mono">
          [Camera Live Stream Preview - Click to add Polygon points]
        </div>

        <svg
          ref={canvasRef}
          onClick={handleCanvasClick}
          className="absolute inset-0 w-full h-full"
        >
          {points.length > 0 && (
            <polygon
              points={pointsSvgString}
              fill="rgba(99, 102, 241, 0.25)"
              stroke="#6366f1"
              strokeWidth="2"
            />
          )}
          {points.map(([x, y], idx) => (
            <circle
              key={idx}
              cx={`${x * 100}%`}
              cy={`${y * 100}%`}
              r="6"
              fill="#ef4444"
              stroke="#ffffff"
              strokeWidth="2"
            />
          ))}
        </svg>
      </div>

      <div className="text-[11px] text-slate-400">
        Tọa độ relative (%): {JSON.stringify(points)}
      </div>
    </div>
  );
};
