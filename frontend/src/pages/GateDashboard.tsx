import React, { useState, useEffect } from 'react';
import { useApp } from '../context/AppContext';
import { fetchZones } from '../services/api';
import { ZoneConfig } from '../types';

const CANONICAL_8_TYPES = [
  { key: 'container', label: 'Container' },
  { key: 'truck', label: 'Xe tải' },
  { key: 'forklift', label: 'Xe nâng' },
  { key: 'crane', label: 'Xe cẩu' },
  { key: 'car', label: 'Xe con' },
  { key: 'motorbike', label: 'Xe máy' },
  { key: 'bicycle', label: 'Xe đạp' },
  { key: 'person', label: 'Người' },
];

export const GateDashboard: React.FC = () => {
  const { clock, gateEvents, zonesByCam, updateZone, toggleZoneType, setTab, setSubTab } = useApp();

  const [zones, setZones] = useState<ZoneConfig[]>([]);
  const [activeZoneId, setActiveZoneId] = useState<string | null>(null);

  // Inline Zone Name Editing State
  const [editingZoneId, setEditingZoneId] = useState<string | null>(null);
  const [editingNameText, setEditingNameText] = useState<string>('');

  // Hydrate & Sync GATE-01 Zones from Context / Backend DB
  useEffect(() => {
    const camZones = zonesByCam['GATE-01'] || [];
    if (camZones.length > 0) {
      setZones(camZones);
      if (!activeZoneId || !camZones.some((z) => z.id === activeZoneId)) {
        setActiveZoneId(camZones[0].id);
      }
    } else {
      fetchZones('GATE-01').then((res) => {
        if (res && res.length > 0) {
          setZones(res);
          setActiveZoneId(res[0].id);
        } else {
          setZones([]);
          setActiveZoneId(null);
        }
      });
    }
  }, [zonesByCam]);

  const activeZone = zones.find((z) => z.id === activeZoneId) || zones[0];

  // Dynamic Vehicle Rules Pills derived from Active GATE-01 Zone
  const typeRules = CANONICAL_8_TYPES.map((t) => {
    if (!activeZone) return { key: t.key, label: `✓ ${t.label}`, ok: true };
    const forbiddenList = (activeZone as any).forbidden_classes || [];
    const allowedList = (activeZone as any).allowed_classes || [];

    let isAllowed = true;
    if (forbiddenList.includes(t.key)) {
      isAllowed = false;
    } else if (allowedList.length > 0 && !allowedList.includes(t.key)) {
      isAllowed = false;
    }

    return {
      key: t.key,
      label: `${isAllowed ? '✓' : '✕'} ${t.label}`,
      ok: isAllowed,
    };
  });

  const handleSaveZoneName = (zoneId: string) => {
    const trimmed = editingNameText.trim();
    if (trimmed) {
      updateZone('GATE-01', zoneId, { name: trimmed });
    }
    setEditingZoneId(null);
    setEditingNameText('');
  };

  const handleOpenZoneEditor = () => {
    setTab('set');
    setSubTab('zone');
  };

  const unreadCount = gateEvents.filter((e) => e.conf === null).length;
  const readCount = gateEvents.length - unreadCount;

  const kpis = [
    { label: 'Lượt xe qua cổng', value: String(gateEvents.length), color: 'var(--ink)' },
    { label: 'Biển số đọc được', value: String(readCount), color: 'var(--ok)' },
    { label: 'Không đọc được', value: String(unreadCount), color: 'var(--p1)' },
    { label: 'Độ tin cậy trung bình', value: '96%', color: 'var(--ink)' },
  ];

  return (
    <div style={{ padding: '20px', maxWidth: '1360px', margin: '0 auto' }}>
      {/* 4 KPI Cards */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '12px', marginBottom: '18px' }}>
        {kpis.map((k, idx) => (
          <div
            key={idx}
            style={{
              background: 'var(--card)',
              border: '1px solid var(--line)',
              borderRadius: '13px',
              padding: '14px',
            }}
          >
            <div style={{ fontSize: '11.5px', color: 'var(--ink3)', marginBottom: '8px' }}>{k.label}</div>
            <div
              style={{
                fontSize: '24px',
                fontWeight: 700,
                fontFamily: "'IBM Plex Mono', monospace",
                color: k.color,
              }}
            >
              {k.value}
            </div>
          </div>
        ))}
      </div>

      {/* Main 2-column Grid */}
      <div style={{ display: 'grid', gridTemplateColumns: '1.5fr 1fr', gap: '16px' }}>
        {/* Left Column: Live Camera Viewport */}
        <div>
          {/* Header Bar with Live Indicator, Zone Selector & Quick Edit Link */}
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '10px', flexWrap: 'wrap', gap: '8px' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '9px' }}>
              <span
                style={{
                  width: '8px',
                  height: '8px',
                  borderRadius: '50%',
                  background: 'var(--p0)',
                  animation: 'liveDot 1.4s infinite',
                }}
              />
              <span style={{ fontSize: '12.5px', fontWeight: 600, color: 'var(--p0)' }}>TRỰC TIẾP</span>
              <span style={{ fontSize: '12px', color: 'var(--ink3)' }}>
                GATE-01 · Cổng vào · {clock}
              </span>
            </div>

            {/* Zone Selector Buttons with Inline Double-Click Editing */}
            <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
              {zones.map((z) => {
                const isEditing = editingZoneId === z.id;
                const isSelected = activeZoneId === z.id;
                return isEditing ? (
                  <input
                    key={z.id}
                    type="text"
                    value={editingNameText}
                    onChange={(e) => setEditingNameText(e.target.value)}
                    onKeyDown={(e) => {
                      if (e.key === 'Enter') handleSaveZoneName(z.id);
                      if (e.key === 'Escape') setEditingZoneId(null);
                    }}
                    onBlur={() => handleSaveZoneName(z.id)}
                    autoFocus
                    style={{
                      padding: '2px 6px',
                      fontSize: '10.5px',
                      fontWeight: 600,
                      borderRadius: '6px',
                      border: `1px solid ${z.color}`,
                      background: '#0c0f13',
                      color: z.color,
                      width: '90px',
                    }}
                  />
                ) : (
                  <button
                    key={z.id}
                    onClick={() => setActiveZoneId(z.id)}
                    onDoubleClick={() => {
                      setEditingZoneId(z.id);
                      setEditingNameText(z.name);
                    }}
                    title="Bấm chọn / Bấm đúp để sửa tên zone"
                    style={{
                      padding: '3px 9px',
                      fontSize: '10.5px',
                      fontWeight: 600,
                      borderRadius: '6px',
                      border: isSelected ? `1px solid ${z.color}` : '1px solid var(--line)',
                      background: isSelected ? z.color + '22' : 'var(--card)',
                      color: isSelected ? z.color : 'var(--ink3)',
                      cursor: 'pointer',
                    }}
                  >
                    {z.name} ✎
                  </button>
                );
              })}

              {/* Direct Shortcut Button to Interactive Zone Drawer */}
              <button
                onClick={handleOpenZoneEditor}
                title="Mở trình vẽ & chỉnh sửa zone đa giác cho Cổng vào"
                style={{
                  padding: '3px 10px',
                  fontSize: '11px',
                  fontWeight: 600,
                  borderRadius: '6px',
                  border: '1px solid var(--acc)',
                  background: 'var(--acc)',
                  color: '#fff',
                  cursor: 'pointer',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '4px',
                  marginLeft: '4px',
                }}
              >
                ✏️ Vẽ / Cấu hình Zone
              </button>
            </div>
          </div>

          <div
            style={{
              position: 'relative',
              width: '100%',
              aspectRatio: '16/9',
              background: '#0c0f13',
              border: '1px solid var(--line)',
              borderRadius: '12px',
              overflow: 'hidden',
            }}
          >
            {/* Camera Simulated Feed Background */}
            <div
              style={{
                position: 'absolute',
                inset: 0,
                background: 'radial-gradient(120% 90% at 50% 18%, #1a2129 0%, #0c0f13 60%, #07090b 100%)',
              }}
            >
              <div
                style={{
                  position: 'absolute',
                  left: 0,
                  right: 0,
                  bottom: 0,
                  height: '56%',
                  background: 'linear-gradient(#0c1014,#060809)',
                  backgroundImage:
                    'repeating-linear-gradient(90deg, rgba(255,255,255,.05) 0 1px, transparent 1px 13%)',
                }}
              />
            </div>

            {/* SVG Polygon Zones Overlay */}
            <svg
              viewBox="0 0 100 100"
              preserveAspectRatio="none"
              style={{
                position: 'absolute',
                inset: 0,
                width: '100%',
                height: '100%',
                pointerEvents: 'none',
              }}
            >
              {zones.map((z) => {
                if (!z.points || z.points.length === 0) return null;
                const ptsStr = z.points.map((p) => `${p[0].toFixed(1)},${p[1].toFixed(1)}`).join(' ');
                const isSelected = activeZoneId === z.id;
                return (
                  <polygon
                    key={z.id}
                    points={ptsStr}
                    fill={z.color + (isSelected ? '25' : '12')}
                    stroke={z.color}
                    strokeWidth={isSelected ? '2.5' : '1.5'}
                    strokeDasharray={isSelected ? undefined : '5 4'}
                    vectorEffect="non-scaling-stroke"
                  />
                );
              })}
            </svg>

            {/* Interactive Zone Label Badges (Click to Edit Name) */}
            {zones.map((z) => {
              if (!z.points || z.points.length === 0) return null;
              const cx = z.points.reduce((a, p) => a + p[0], 0) / z.points.length;
              const cy = z.points.reduce((a, p) => a + p[1], 0) / z.points.length;
              const isEditing = editingZoneId === z.id;

              return isEditing ? (
                <div
                  key={z.id}
                  style={{
                    position: 'absolute',
                    left: `${cx.toFixed(1)}%`,
                    top: `${cy.toFixed(1)}%`,
                    transform: 'translate(-50%, -50%)',
                    zIndex: 10,
                  }}
                >
                  <input
                    type="text"
                    value={editingNameText}
                    onChange={(e) => setEditingNameText(e.target.value)}
                    onKeyDown={(e) => {
                      if (e.key === 'Enter') handleSaveZoneName(z.id);
                      if (e.key === 'Escape') setEditingZoneId(null);
                    }}
                    onBlur={() => handleSaveZoneName(z.id)}
                    autoFocus
                    style={{
                      fontSize: '10px',
                      fontWeight: 700,
                      color: z.color,
                      background: 'rgba(0,0,0,0.9)',
                      border: `1.5px solid ${z.color}`,
                      borderRadius: '4px',
                      padding: '2px 6px',
                      textAlign: 'center',
                      width: '100px',
                    }}
                  />
                </div>
              ) : (
                <span
                  key={z.id}
                  onClick={() => {
                    setEditingZoneId(z.id);
                    setEditingNameText(z.name);
                  }}
                  title="Bấm để chỉnh sửa tên zone"
                  style={{
                    position: 'absolute',
                    left: `${cx.toFixed(1)}%`,
                    top: `${cy.toFixed(1)}%`,
                    transform: 'translate(-50%, -50%)',
                    fontSize: '9.5px',
                    fontWeight: 700,
                    color: z.color,
                    textShadow: '0 1px 4px rgba(0,0,0,.95), 0 0 10px rgba(0,0,0,.8)',
                    whiteSpace: 'nowrap',
                    background: 'rgba(0,0,0,0.65)',
                    padding: '2px 6px',
                    borderRadius: '4px',
                    border: `1px solid ${z.color}44`,
                    cursor: 'pointer',
                    pointerEvents: 'auto',
                  }}
                >
                  {z.name.toUpperCase()} ✎
                </span>
              );
            })}

            {/* Simulated Recognized Plate Bounding Box */}
            <div
              style={{
                position: 'absolute',
                left: '79%',
                top: '79.5%',
                width: '14%',
                height: '10%',
                border: '1.5px solid #39e0d0',
                background: 'rgba(57,224,208,.1)',
              }}
            >
              <span
                style={{
                  position: 'absolute',
                  left: '-1px',
                  top: '-18px',
                  background: '#39e0d0',
                  color: '#06080a',
                  fontSize: '10px',
                  fontWeight: 700,
                  padding: '1px 7px',
                  borderRadius: '3px',
                  whiteSpace: 'nowrap',
                }}
              >
                15R-158.45 · 97%
              </span>
            </div>

            {/* Live Clock Overlay */}
            <div
              style={{
                position: 'absolute',
                right: '10px',
                top: '9px',
                background: 'rgba(0,0,0,.5)',
                color: '#e3e7ea',
                fontSize: '10px',
                padding: '3px 7px',
                borderRadius: '5px',
                fontFamily: "'IBM Plex Mono', monospace",
              }}
            >
              {clock}
            </div>
          </div>

          {/* Under-stream Interactive Vehicle Type Rule Pills */}
          <div style={{ marginTop: '12px' }}>
            <div style={{ fontSize: '11px', color: 'var(--ink3)', marginBottom: '6px', fontWeight: 600 }}>
              Chọn loại xe được phép vào zone ({activeZone ? activeZone.name : 'GATE-01'}) (bấm để đổi ✓ được phép / ✕ cấm):
            </div>
            <div style={{ display: 'flex', gap: '6px', flexWrap: 'wrap' }}>
              {typeRules.map((t, idx) => {
                const fg = t.ok ? 'var(--ok)' : 'var(--p0)';
                const bg = t.ok ? 'var(--okq)' : 'var(--p0q)';
                const border = t.ok ? 'var(--ok)' : 'rgba(255,69,58,.4)';
                return (
                  <button
                    key={idx}
                    onClick={() => activeZone && toggleZoneType('GATE-01', activeZone.id, t.key)}
                    title="Bấm để bật/tắt quyền truy cập loại phương tiện cho zone này (Lưu DB)"
                    style={{
                      display: 'flex',
                      alignItems: 'center',
                      gap: '5px',
                      fontSize: '11px',
                      fontWeight: 600,
                      padding: '4px 11px',
                      borderRadius: '20px',
                      border: `1px solid ${border}`,
                      background: bg,
                      color: fg,
                      cursor: 'pointer',
                      fontFamily: 'inherit',
                      transition: 'all 0.2s ease',
                    }}
                  >
                    {t.label}
                  </button>
                );
              })}
            </div>
          </div>
        </div>

        {/* Right Column: Recognized License Plates List */}
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
            Biển số đã nhận diện
          </div>
          <div style={{ flex: 1, overflow: 'auto' }}>
            {gateEvents.map((e) => {
              const confStr = e.conf === null ? 'không đọc được' : `${e.conf}%`;
              const confColor =
                e.conf === null ? 'var(--p1)' : e.conf >= 95 ? 'var(--ok)' : 'var(--p1)';
              return (
                <div
                  key={e.id}
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
                    {e.time}
                  </span>
                  <div style={{ flex: 1, minWidth: 0 }}>
                    <div style={{ fontSize: '13px', fontWeight: 600, fontFamily: "'IBM Plex Mono', monospace" }}>
                      {e.plate}
                    </div>
                    <div style={{ fontSize: '11px', color: 'var(--ink3)' }}>{e.zone}</div>
                  </div>
                  <span
                    style={{
                      fontSize: '11px',
                      fontWeight: 600,
                      fontFamily: "'IBM Plex Mono', monospace",
                      color: confColor,
                      flex: 'none',
                    }}
                  >
                    {confStr}
                  </span>
                </div>
              );
            })}
          </div>
        </div>
      </div>
    </div>
  );
};
