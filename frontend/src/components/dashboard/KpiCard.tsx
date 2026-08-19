import React from 'react';

interface KpiCardProps {
  title: string;
  value: string | number;
  subtitle?: string;
  icon: React.ReactNode;
  trend?: string;
  trendType?: 'positive' | 'negative' | 'neutral';
}

export const KpiCard: React.FC<KpiCardProps> = ({
  title,
  value,
  subtitle,
  icon,
  trend,
  trendType = 'neutral',
}) => {
  const getTrendClass = () => {
    if (trendType === 'positive') return 'text-emerald-400';
    if (trendType === 'negative') return 'text-red-400';
    return 'text-slate-400';
  };

  return (
    <div className="bg-[#0f172a] border border-slate-800 rounded-xl p-5 shadow-sm hover:border-slate-700 transition">
      <div className="flex items-center justify-between">
        <span className="text-xs font-medium text-slate-400 uppercase tracking-wider">{title}</span>
        <div className="p-2.5 bg-slate-900 border border-slate-800 rounded-lg text-indigo-400">
          {icon}
        </div>
      </div>

      <div className="mt-3 flex items-baseline justify-between">
        <div className="text-2xl font-bold text-slate-100">{value}</div>
        {trend && <span className={`text-xs font-medium ${getTrendClass()}`}>{trend}</span>}
      </div>

      {subtitle && <div className="mt-1 text-xs text-slate-400">{subtitle}</div>}
    </div>
  );
};
