import React from 'react';
import { useApp } from '../../context/AppContext';
import { TabId } from '../../types';

export const Sidebar: React.FC = () => {
  const { tab, setTab } = useApp();

  const menuItems: { id: TabId; label: string }[] = [
    { id: 'mon', label: 'Giám sát cổng' },
    { id: 'area', label: 'Giám sát khu vực' },
    { id: 'set', label: 'Cài đặt' },
    { id: 'qa', label: 'Hỏi đáp AI' },
  ];

  return (
    <aside style={{ width: '220px', background: 'var(--panel)', borderRight: '1px solid var(--line)', padding: '16px' }}>
      <div style={{ fontSize: '14px', fontWeight: 700, marginBottom: '16px', color: 'var(--ink)' }}>SentriAI Mini</div>
      <nav style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
        {menuItems.map((item) => {
          const isActive = tab === item.id;
          return (
            <button
              key={item.id}
              onClick={() => setTab(item.id)}
              style={{
                textAlign: 'left',
                padding: '9px 12px',
                borderRadius: '8px',
                border: 'none',
                background: isActive ? 'var(--acc)' : 'transparent',
                color: isActive ? '#fff' : 'var(--ink2)',
                fontWeight: 600,
                fontSize: '12.5px',
                cursor: 'pointer',
                fontFamily: 'inherit',
              }}
            >
              {item.label}
            </button>
          );
        })}
      </nav>
    </aside>
  );
};
