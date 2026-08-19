import React from 'react';
import { useApp } from '../../context/AppContext';

export const PolygonZoneEditor: React.FC = () => {
  const { zonesByCam, toggleZoneType, objLabels } = useApp();
  const zones = zonesByCam['BAI-KIEM'] || [];

  return (
    <div
      style={{
        background: 'var(--card)',
        border: '1px solid var(--line)',
        borderRadius: '13px',
        padding: '16px',
      }}
    >
      <div style={{ fontSize: '13.5px', fontWeight: 600, marginBottom: '12px' }}>
        Danh Sách Zone Đa Giác (Bãi Kiểm)
      </div>

      <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
        {zones.map((z) => (
          <div
            key={z.id}
            style={{
              background: 'var(--panel)',
              border: `1px solid ${z.color}`,
              borderRadius: '10px',
              padding: '12px',
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '8px' }}>
              <span style={{ width: '10px', height: '10px', borderRadius: '3px', background: z.color }} />
              <span style={{ fontSize: '13px', fontWeight: 600 }}>{z.name}</span>
            </div>

            <div style={{ display: 'flex', gap: '6px', flexWrap: 'wrap' }}>
              {objLabels.map((o) => {
                const isAllowed = !!z.types[o.name];
                return (
                  <button
                    key={o.id}
                    onClick={() => toggleZoneType('BAI-KIEM', z.id, o.name)}
                    style={{
                      fontSize: '11px',
                      fontWeight: 600,
                      padding: '4px 11px',
                      borderRadius: '20px',
                      border: `1px solid ${isAllowed ? 'var(--ok)' : 'rgba(255,69,58,.4)'}`,
                      background: isAllowed ? 'var(--okq)' : 'var(--p0q)',
                      color: isAllowed ? 'var(--ok)' : 'var(--p0)',
                      cursor: 'pointer',
                      fontFamily: 'inherit',
                    }}
                  >
                    {isAllowed ? '✓ ' : '✕ '}
                    {o.name}
                  </button>
                );
              })}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};
