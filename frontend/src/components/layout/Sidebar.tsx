import React from 'react';
import { Camera, ShieldAlert, Settings, Bot } from 'lucide-react';
import { useApp } from '../../context/AppContext';
import { TabId } from '../../types';

export const Sidebar: React.FC = () => {
  const { activeTab, setActiveTab } = useApp();

  const navItems: { id: TabId; label: string; icon: React.ReactNode; tabIndex: number }[] = [
    { id: 'gate', label: 'Cổng Vào LPR (Tab 1)', icon: <Camera className="w-5 h-5" />, tabIndex: 1 },
    { id: 'area', label: 'Giám Sát Khu Vực (Tab 2)', icon: <ShieldAlert className="w-5 h-5" />, tabIndex: 2 },
    { id: 'settings', label: 'Zone & Nhãn Xe (Tab 3)', icon: <Settings className="w-5 h-5" />, tabIndex: 3 },
    { id: 'assistant', label: 'Hỏi Đáp AI (Tab 4)', icon: <Bot className="w-5 h-5" />, tabIndex: 4 },
  ];

  return (
    <aside
      role="navigation"
      aria-label="Sidebar Navigation"
      className="w-64 bg-[#0f172a] border-r border-slate-800 p-4 flex flex-col justify-between shrink-0 select-none"
    >
      <div className="space-y-2">
        <div className="px-3 py-2 text-xs font-semibold uppercase tracking-wider text-slate-400">
          Phân Hệ Chức Năng
        </div>

        {navItems.map((item) => {
          const isActive = activeTab === item.id;
          return (
            <button
              key={item.id}
              type="button"
              onClick={() => setActiveTab(item.id)}
              aria-current={isActive ? 'page' : undefined}
              aria-label={`Chuyển đến màn hình ${item.label}`}
              className={`w-full flex items-center space-x-3 px-4 py-3 rounded-lg text-sm font-medium transition focus:outline-none focus:ring-2 focus:ring-indigo-500 ${
                isActive
                  ? 'bg-indigo-600 text-white shadow-lg shadow-indigo-600/20'
                  : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/60'
              }`}
            >
              {item.icon}
              <span>{item.label}</span>
            </button>
          );
        })}
      </div>

      <div className="p-4 bg-slate-900 border border-slate-800 rounded-lg text-xs space-y-1.5">
        <div className="text-slate-300 font-semibold border-b border-slate-800 pb-1">
          Trạng Thái AI Engine
        </div>
        <div className="flex items-center justify-between text-slate-400">
          <span>YOLO-World v2</span>
          <span className="text-emerald-400 font-medium">Online</span>
        </div>
        <div className="flex items-center justify-between text-slate-400">
          <span>YOLOv8 + EasyOCR</span>
          <span className="text-emerald-400 font-medium">Active</span>
        </div>
        <div className="flex items-center justify-between text-slate-400">
          <span>SQLite WAL DB</span>
          <span className="text-emerald-400 font-medium">OK</span>
        </div>
      </div>
    </aside>
  );
};
