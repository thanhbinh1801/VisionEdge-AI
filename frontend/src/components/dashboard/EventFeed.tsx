import React from 'react';
import { EventRecord } from '../../types';

interface EventFeedProps {
  events: EventRecord[];
}

export const EventFeed: React.FC<EventFeedProps> = ({ events }) => {
  return (
    <div
      style={{
        background: 'var(--panel)',
        border: '1px solid var(--line)',
        borderRadius: '14px',
        display: 'flex',
        flexDirection: 'column',
        overflow: 'hidden',
        maxHeight: '560px',
      }}
    >
      <div style={{ padding: '13px 15px', borderBottom: '1px solid var(--line)', fontSize: '13.5px', fontWeight: 600 }}>
        Nhật ký sự kiện gần đây
      </div>
      <div style={{ flex: 1, overflow: 'auto' }}>
        {events.map((evt) => (
          <div
            key={evt.id}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '11px',
              padding: '11px 15px',
              borderBottom: '1px solid var(--line)',
            }}
          >
            <span
              style={{
                fontSize: '11px',
                color: 'var(--ink3)',
                fontFamily: "'IBM Plex Mono', monospace",
                width: '42px',
                flex: 'none',
              }}
            >
              {evt.timestamp}
            </span>
            <div style={{ flex: 1, minWidth: 0 }}>
              <div style={{ fontSize: '13px', fontWeight: 600, fontFamily: "'IBM Plex Mono', monospace" }}>
                {evt.plateNumber || evt.objectClass}
              </div>
              <div style={{ fontSize: '11px', color: 'var(--ink3)' }}>{evt.cameraName}</div>
            </div>
            <span
              style={{
                fontSize: '10.5px',
                fontWeight: 700,
                padding: '3px 9px',
                borderRadius: '20px',
                background: evt.severity === 3 ? 'var(--p0q)' : 'var(--okq)',
                color: evt.severity === 3 ? 'var(--p0)' : 'var(--ok)',
                flex: 'none',
              }}
            >
              Mức {evt.severity}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
};
