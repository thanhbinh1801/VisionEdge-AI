import React, { useState } from 'react';
import { PolygonZoneEditor } from '../components/zone/PolygonZoneEditor';
import { Tag, Plus } from 'lucide-react';

interface TagItem {
  id: string;
  plate: string;
  owner: string;
  category: 'WHITELIST' | 'BLACKLIST' | 'VISITOR';
}

export const ZoneTagSettings: React.FC = () => {
  const [tags, setTags] = useState<TagItem[]>([
    { id: '1', plate: '29A-123.45', owner: 'Xe Công Ty A', category: 'WHITELIST' },
    { id: '2', plate: '30B-999.99', owner: 'Đối Tượng Vi Phạm', category: 'BLACKLIST' },
    { id: '3', plate: '51C-777.88', owner: 'Khách Hàng B', category: 'VISITOR' },
  ]);

  const [newPlate, setNewPlate] = useState('');
  const [newOwner, setNewOwner] = useState('');
  const [newCategory, setNewCategory] = useState<'WHITELIST' | 'BLACKLIST' | 'VISITOR'>('WHITELIST');

  const handleAddTag = (e: React.FormEvent) => {
    e.preventDefault();
    if (!newPlate.trim()) return;
    setTags((prev) => [
      ...prev,
      {
        id: Date.now().toString(),
        plate: newPlate.toUpperCase(),
        owner: newOwner || 'Chưa rõ',
        category: newCategory,
      },
    ]);
    setNewPlate('');
    setNewOwner('');
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-bold text-slate-100">Tab 3: Zone & Tag Settings</h2>
          <p className="text-xs text-slate-400">
            Cấu Hình Vùng Cảnh Báo Đa Giác & Quản Lý Danh Sách Biển Số Xe (Whitelist/Blacklist)
          </p>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div>
          <PolygonZoneEditor />
        </div>

        <div className="bg-[#0f172a] border border-slate-800 rounded-xl p-5 space-y-4">
          <div className="flex items-center space-x-2 border-b border-slate-800 pb-3">
            <Tag className="w-5 h-5 text-indigo-400" />
            <h3 className="text-sm font-semibold text-slate-200">Gán Nhãn Biển Số Xe (Vehicle Tagging)</h3>
          </div>

          <form onSubmit={handleAddTag} className="space-y-3 bg-slate-900 p-3 rounded-lg border border-slate-800">
            <div className="grid grid-cols-2 gap-2">
              <input
                type="text"
                placeholder="Biển số (VD: 29A-888.88)"
                value={newPlate}
                onChange={(e) => setNewPlate(e.target.value)}
                className="px-3 py-1.5 bg-slate-950 border border-slate-700 rounded text-xs text-slate-100 focus:outline-none focus:border-indigo-500"
              />
              <input
                type="text"
                placeholder="Chủ xe / Ghi chú"
                value={newOwner}
                onChange={(e) => setNewOwner(e.target.value)}
                className="px-3 py-1.5 bg-slate-950 border border-slate-700 rounded text-xs text-slate-100 focus:outline-none focus:border-indigo-500"
              />
            </div>
            <div className="flex items-center justify-between">
              <select
                value={newCategory}
                onChange={(e) => setNewCategory(e.target.value as 'WHITELIST' | 'BLACKLIST' | 'VISITOR')}
                className="px-3 py-1.5 bg-slate-950 border border-slate-700 rounded text-xs text-slate-100 focus:outline-none focus:border-indigo-500"
              >
                <option value="WHITELIST">Whitelist (Xe Đã Đăng Ký)</option>
                <option value="BLACKLIST">Blacklist (Cảnh Báo Cấm)</option>
                <option value="VISITOR">Visitor (Khách Vãng Lai)</option>
              </select>
              <button
                type="submit"
                className="flex items-center space-x-1 px-4 py-1.5 bg-indigo-600 hover:bg-indigo-500 text-white rounded text-xs font-semibold"
              >
                <Plus className="w-4 h-4" />
                <span>Thêm Nhãn</span>
              </button>
            </div>
          </form>

          <div className="space-y-2 max-h-64 overflow-y-auto">
            {tags.map((t) => (
              <div
                key={t.id}
                className="p-3 bg-slate-900 border border-slate-800 rounded-lg flex items-center justify-between text-xs"
              >
                <div className="flex items-center space-x-3">
                  <span className="font-mono font-bold text-indigo-300 px-2 py-0.5 bg-slate-950 rounded border border-slate-800">
                    {t.plate}
                  </span>
                  <span className="text-slate-300">{t.owner}</span>
                </div>
                <span
                  className={`px-2 py-0.5 text-[10px] font-semibold rounded ${
                    t.category === 'WHITELIST'
                      ? 'bg-emerald-950 text-emerald-400 border border-emerald-800'
                      : t.category === 'BLACKLIST'
                      ? 'bg-red-950 text-red-400 border border-red-800'
                      : 'bg-slate-800 text-slate-300'
                  }`}
                >
                  {t.category}
                </span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
};
