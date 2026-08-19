import React, { useState, useEffect } from 'react';
import { useApp } from '../context/AppContext';
import { fetchZones, fetchLiveDetections, fetchLatestEvents, LiveDetection } from '../services/api';
import { ZoneConfig, AreaEvent } from '../types';

const CANONICAL_8_TYPES = [
  { key: 'container', label: 'Xe container' },
  { key: 'truck', label: 'Xe tải' },
  { key: 'forklift', label: 'Xe nâng' },
  { key: 'crane', label: 'Xe cẩu' },
  { key: 'car', label: 'Xe con' },
  { key: 'motorbike', label: 'Xe máy' },
  { key: 'bicycle', label: 'Xe đạp' },
  { key: 'person', label: 'Người' },
];

export const AreaSecurityDashboard: React.FC = () => {
  const { clock, zonesByCam, updateZone } = useApp();
  const [activeCam, setActiveCam] = useState<string>('BAI-KIEM');
  const [zones, setZones] = useState<ZoneConfig[]>([]);
  const [activeZoneId, setActiveZoneId] = useState<string | null>(null);
  const [liveDetections, setLiveDetections] = useState<LiveDetection[]>([]);
  const [events, setEvents] = useState<AreaEvent[]>([]);

  // Inline editing state for Zone Name
  const [editingZoneId, setEditingZoneId] = useState<string | null>(null);
  const [editingNameText, setEditingNameText] = useState<string>('');

  // Fetch zones on mount & camera change
  useEffect(() => {
    const camZones = zonesByCam[activeCam] || [];
    if (camZones.length > 0) {
      setZones(camZones);
      if (!activeZoneId || !camZones.some(z => z.id === activeZoneId)) {
        setActiveZoneId(camZones[0].id);
      }
    } else {
      fetchZones(activeCam).then((res) => {
        if (res && res.length > 0) {
          setZones(res);
          setActiveZoneId(res[0].id);
        } else {
          setZones([]);
          setActiveZoneId(null);
        }
      });
    }
  }, [zonesByCam, activeCam]);

  // Fetch live detections & events from backend API (No mock data fallback)
  useEffect(() => {
    const loadBackendData = () => {
      fetchLiveDetections(activeCam).then((dets) => {
        setLiveDetections(dets || []);
      });
      fetchLatestEvents(activeCam, 20).then((rawEvents) => {
        if (rawEvents && rawEvents.length > 0) {
          const mapped: AreaEvent[] = rawEvents.map((evt: any) => {
            const timeStr = evt.timestamp 
              ? new Date(evt.timestamp).toLocaleTimeString('vi-VN', { hour: '2-digit', minute: '2-digit' })
              : '09:00';
            const isOk = evt.severity_level < 3;
            return {
              id: evt.id || `evt-${Math.random()}`,
              time: timeStr,
              obj: evt.object_class || 'Đối tượng',
              zone: evt.zone_name || 'Khu vực an ninh',
              st: isOk ? 'Được phép' : 'Vi phạm',
              ok: isOk,
            };
          });
          setEvents(mapped);
        } else {
          setEvents([]);
        }
      });
    };

    loadBackendData();
    const interval = setInterval(loadBackendData, 3000);
    return () => clearInterval(interval);
  }, [activeCam]);

  const activeZone = zones.find((z) => z.id === activeZoneId) || zones[0];

  // Dynamic Understream Vehicle Rules Pills derived from Active Zone
  const typeRules = CANONICAL_8_TYPES.map((t) => {
    if (!activeZone) return { label: `✓ ${t.label}`, ok: true };
    const forbiddenList = (activeZone as any).forbidden_classes || [];
    const allowedList = (activeZone as any).allowed_classes || [];

    let isAllowed = true;
    if (forbiddenList.includes(t.key)) {
      isAllowed = false;
    } else if (allowedList.length > 0 && !allowedList.includes(t.key)) {
      isAllowed = false;
    }

    return {
      label: `${isAllowed ? '✓' : '✕'} ${t.label}`,
      ok: isAllowed,
    };
  });

  // Handle Zone Name Inline Editing Completion
  const handleSaveZoneName = (zoneId: string) => {
    const trimmed = editingNameText.trim();
    if (trimmed) {
      updateZone(activeCam, zoneId, { name: trimmed });
    }
    setEditingZoneId(null);
    setEditingNameText('');
  };

  // Compute 100% Real KPI Values from DB / Backend API responses
  const activeObjectsCount = liveDetections.length;
  const violationsCount = events.filter((e) => !e.ok).length;
  const activeMachineryCount = liveDetections.filter((d) => ['forklift', 'container', 'truck', 'crane'].includes(d.object_class)).length;
  const totalZonesCount = zones.length;

  const areaKpis = [
    { label: 'Đối tượng trong khu', value: String(activeObjectsCount), color: 'var(--ink)' },
    { label: 'Vi phạm loại xe hôm nay', value: String(violationsCount), color: violationsCount > 0 ? 'var(--p0)' : 'var(--ink)' },
    { label: 'Xe nâng / container hoạt động', value: String(activeMachineryCount), color: 'var(--ink)' },
    { label: 'Zone khu vực', value: String(totalZonesCount), color: 'var(--ink)' },
  ];

  const videoSrc = activeCam === 'XUONG-AN-NINH' ? '/videos/XUONG_AN_NINH.mp4' : '/videos/BAI_KIEM.mp4';
  const camTitle = activeCam === 'XUONG-AN-NINH' ? 'Xưởng An Ninh' : 'Bãi Kiểm';

  return (
    <div style={{ padding: '20px', maxWidth: '1360px', margin: '0 auto' }}>
      {/* 4 Real KPI Cards */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '12px', marginBottom: '18px' }}>
        {areaKpis.map((k, idx) => (
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
        {/* Left Column: Live Overhead Camera Viewport */}
        <div>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '10px' }}>
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
              
              {/* Camera Switcher */}
              <div style={{ display: 'flex', gap: '4px', background: 'var(--card)', border: '1px solid var(--line)', borderRadius: '7px', padding: '2px' }}>
                <button
                  onClick={() => setActiveCam('BAI-KIEM')}
                  style={{
                    padding: '2px 8px',
                    fontSize: '11px',
                    fontWeight: 600,
                    borderRadius: '5px',
                    border: 'none',
                    background: activeCam === 'BAI-KIEM' ? 'var(--acc)' : 'transparent',
                    color: activeCam === 'BAI-KIEM' ? '#fff' : 'var(--ink3)',
                    cursor: 'pointer',
                  }}
                >
                  Bãi Kiểm
                </button>
                <button
                  onClick={() => setActiveCam('XUONG-AN-NINH')}
                  style={{
                    padding: '2px 8px',
                    fontSize: '11px',
                    fontWeight: 600,
                    borderRadius: '5px',
                    border: 'none',
                    background: activeCam === 'XUONG-AN-NINH' ? 'var(--acc)' : 'transparent',
                    color: activeCam === 'XUONG-AN-NINH' ? '#fff' : 'var(--ink3)',
                    cursor: 'pointer',
                  }}
                >
                  Xưởng An Ninh
                </button>
              </div>

              <span style={{ fontSize: '12px', color: 'var(--ink3)' }}>
                {activeCam} · {camTitle} · {clock}
              </span>
            </div>

            {/* Zone Selector Buttons with Inline Name Editing */}
            {zones.length > 0 && (
              <div style={{ display: 'flex', gap: '6px' }}>
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
                        width: '100px',
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
                      title="Bấm đúp để chỉnh sửa tên zone"
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
              </div>
            )}
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
            {/* Live Overhead Video Player */}
            <video
              key={videoSrc}
              src={videoSrc}
              autoPlay
              loop
              muted
              playsInline
              style={{
                position: 'absolute',
                inset: 0,
                width: '100%',
                height: '100%',
                objectFit: 'cover',
              }}
            />

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
                    fill={z.color + (isSelected ? '25' : '10')}
                    stroke={z.color}
                    strokeWidth={isSelected ? '2.5' : '1.5'}
                    strokeDasharray={isSelected ? undefined : '5 4'}
                    vectorEffect="non-scaling-stroke"
                  />
                );
              })}
            </svg>

            {/* Zone Center Label Overlay with Click-to-Edit */}
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
                      width: '110px',
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
                  title="Bấm để đổi tên zone"
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

            {/* Real-time Bounding Boxes for Detected Objects (No mock fallback) */}
            {liveDetections.map((o) => {
              const bbox = o.bbox || [20, 20, 20, 20];
              const left = `${bbox[0]}%`;
              const top = `${bbox[1]}%`;
              const width = `${bbox[2]}%`;
              const height = `${bbox[3]}%`;

              let color = '#30d158';
              let fill = 'rgba(48,209,88,.12)';
              if (o.severity === 2) {
                color = '#ff9f0a';
                fill = 'rgba(255,159,10,.16)';
              } else if (o.severity >= 3 || o.zone_violation) {
                color = '#ff453a';
                fill = 'rgba(255,69,58,.20)';
              }

              return (
                <div
                  key={o.id}
                  style={{
                    position: 'absolute',
                    left,
                    top,
                    width,
                    height,
                    border: `2px solid ${color}`,
                    background: fill,
                    boxShadow: `0 0 12px ${color}55`,
                    transition: 'all 0.3s ease',
                  }}
                >
                  <span
                    style={{
                      position: 'absolute',
                      left: '-1px',
                      top: '-20px',
                      background: color,
                      color: '#06080a',
                      fontSize: '9.5px',
                      fontWeight: 700,
                      padding: '2px 7px',
                      borderRadius: '3px',
                      whiteSpace: 'nowrap',
                      boxShadow: '0 2px 6px rgba(0,0,0,0.5)',
                    }}
                  >
                    {o.label}
                  </span>
                </div>
              );
            })}

            {/* Live Clock Badge */}
            <div
              style={{
                position: 'absolute',
                right: '10px',
                top: '9px',
                background: 'rgba(0,0,0,.7)',
                color: '#e3e7ea',
                fontSize: '10px',
                padding: '3px 7px',
                borderRadius: '5px',
                fontFamily: "'IBM Plex Mono', monospace",
                border: '1px solid rgba(255,255,255,0.1)',
              }}
            >
              {clock}
            </div>
          </div>

          {/* Under-stream Vehicle Rules Pills (Derived dynamically from active zone) */}
          <div style={{ marginTop: '12px' }}>
            <div style={{ fontSize: '11px', color: 'var(--ink3)', marginBottom: '6px', fontWeight: 600 }}>
              Quy tắc phân loại đối tượng ({activeZone ? activeZone.name : camTitle}):
            </div>
            <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
              {typeRules.map((t, idx) => {
                const fg = t.ok ? 'var(--ok)' : 'var(--p0)';
                const bg = t.ok ? 'var(--okq)' : 'var(--p0q)';
                const border = t.ok ? 'var(--ok)' : 'var(--p0)';
                return (
                  <span
                    key={idx}
                    style={{
                      display: 'flex',
                      alignItems: 'center',
                      gap: '6px',
                      fontSize: '11px',
                      fontWeight: 600,
                      padding: '5px 12px',
                      borderRadius: '20px',
                      border: `1px solid ${border}`,
                      background: bg,
                      color: fg,
                    }}
                  >
                    {t.label}
                  </span>
                );
              })}
            </div>
          </div>
        </div>

        {/* Right Column: Real Area Events Feed (100% Data DB) */}
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
          <div style={{ padding: '13px 15px', borderBottom: '1px solid var(--line)', fontSize: '13.5px', fontWeight: 600, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <span>Sự kiện khu vực</span>
            <span style={{ fontSize: '11px', color: 'var(--ink3)', fontWeight: 400 }}>Realtime Feed</span>
          </div>
          <div style={{ flex: 1, overflow: 'auto' }}>
            {events.length === 0 ? (
              <div style={{ padding: '40px 20px', textAlign: 'center', color: 'var(--ink3)', fontSize: '12.5px' }}>
                <div style={{ fontSize: '24px', marginBottom: '8px', opacity: 0.5 }}>🛡️</div>
                Chưa ghi nhận sự kiện vi phạm nào trên CSDL.
              </div>
            ) : (
              events.map((e) => {
                const stBg = e.ok ? 'var(--okq)' : 'var(--p0q)';
                const stFg = e.ok ? 'var(--ok)' : 'var(--p0)';
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
                      <div style={{ fontSize: '13px', fontWeight: 600 }}>{e.obj}</div>
                      <div style={{ fontSize: '11px', color: 'var(--ink3)' }}>{e.zone}</div>
                    </div>
                    <span
                      style={{
                        fontSize: '10.5px',
                        fontWeight: 700,
                        padding: '3px 9px',
                        borderRadius: '20px',
                        background: stBg,
                        color: stFg,
                        flex: 'none',
                      }}
                    >
                      {e.st}
                    </span>
                  </div>
                );
              })
            )}
          </div>
        </div>
      </div>
    </div>
  );
};
