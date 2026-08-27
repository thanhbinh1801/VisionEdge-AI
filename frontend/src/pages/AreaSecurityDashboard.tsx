import React, { useState, useEffect } from 'react';
import { useWebSocket } from '../hooks/useWebSocket';
import { useApp } from '../context/AppContext';
import {
  fetchLatestEvents,
  fetchZonesStrict,
  getVideoFeedUrl,
} from '../services/api';
import { AreaEvent, AreaFrameMetadataEvent, ZoneConfig } from '../types';

const CANONICAL_8_TYPES = [
  // Label legacy "Container" đại diện cho xe container trong rule vận hành;
  // thùng container tĩnh đi theo class riêng shipping_container.
  { key: 'container', label: 'Container' },
  { key: 'truck', label: 'Xe tải' },
  { key: 'forklift', label: 'Xe nâng' },
  { key: 'crane', label: 'Xe cẩu' },
  { key: 'car', label: 'Xe con' },
  { key: 'motorbike', label: 'Xe máy' },
  { key: 'bicycle', label: 'Xe đạp' },
  { key: 'person', label: 'Người' },
];

const RULE_CLASS_ALIASES: Record<string, string[]> = {
  container: ['container', 'Container', 'Xe container', 'container_truck'],
  truck: ['truck', 'Xe tải'],
  forklift: ['forklift', 'Xe nâng'],
  crane: ['crane', 'Xe cẩu'],
  car: ['car', 'Xe con'],
  motorbike: ['motorbike', 'Xe máy'],
  bicycle: ['bicycle', 'Xe đạp'],
  person: ['person', 'Người'],
};

function ruleClassMatches(ruleClasses: string[] = [], key: string): boolean {
  const aliases = RULE_CLASS_ALIASES[key] || [key];
  return ruleClasses.some((item) => aliases.includes(item) || aliases.includes(item.toLowerCase()));
}

export const AreaSecurityDashboard: React.FC = () => {
  const { clock, zonesByCam, updateZone } = useApp();
  const activeCam = 'BAI-KIEM';
  const [zones, setZones] = useState<ZoneConfig[]>([]);
  const [activeZoneId, setActiveZoneId] = useState<string | null>(null);
  const [events, setEvents] = useState<AreaEvent[]>([]);
  const [streamStatus, setStreamStatus] = useState<'loading' | 'live' | 'error'>('loading');
  const [metadataStatus, setMetadataStatus] = useState<'connecting' | 'online' | 'degraded' | 'offline'>('connecting');
  const [streamAttempt, setStreamAttempt] = useState(0);
  const [aiError, setAiError] = useState<string | null>(null);
  const [eventsError, setEventsError] = useState<string | null>(null);
  const [zonesError, setZonesError] = useState<string | null>(null);
  const [metadataClock, setMetadataClock] = useState<string | null>(null);
  const [pipelineLatencyMs, setPipelineLatencyMs] = useState<number | null>(null);
  const [zoneVersion, setZoneVersion] = useState<number | null>(null);
  const [debugConfThreshold, setDebugConfThreshold] = useState(0.35);
  const [showStaticContainers, setShowStaticContainers] = useState(false);
  const [areaKpis, setAreaKpis] = useState([
    { label: 'Đối tượng trong khu', value: '0', color: 'var(--ink)' },
    { label: 'Vi phạm loại xe hôm nay', value: '0', color: 'var(--ink)' },
    { label: 'Xe nâng / container hoạt động', value: '0', color: 'var(--ink)' },
    { label: 'Zone khu vực', value: '0', color: 'var(--ink)' },
  ]);

  // Inline editing state for Zone Name
  const [editingZoneId, setEditingZoneId] = useState<string | null>(null);
  const [editingNameText, setEditingNameText] = useState<string>('');

  // Fetch zones on mount & camera change. Prefer the latest backend rules so the
  // dashboard chips match Cài đặt > Vẽ zone even when local context is stale.
  useEffect(() => {
    const camZones = zonesByCam[activeCam] || [];
    if (camZones.length > 0 && zones.length === 0) {
      setZones(camZones);
    }
    setZonesError(null);
    fetchZonesStrict(activeCam)
      .then((res) => {
        setZones(res);
        setActiveZoneId((current) => current && res.some(z => z.id === current) ? current : res[0]?.id ?? null);
      })
      .catch((error: unknown) => {
        if (camZones.length > 0) {
          setZones(camZones);
          setActiveZoneId((current) => current && camZones.some(z => z.id === current) ? current : camZones[0].id);
        }
        setZonesError(error instanceof Error ? error.message : 'Không thể tải cấu hình zone.');
      });

  }, [zonesByCam]);

  useWebSocket(activeCam, (event) => {
    if (!('event_type' in event) || event.event_type !== 'AREA_FRAME_METADATA') return;
    const metadataEvent = event as AreaFrameMetadataEvent;
    const payload = metadataEvent.payload;
    setMetadataStatus(payload.stream_status === 'degraded' ? 'degraded' : payload.stream_status === 'offline' ? 'offline' : 'online');
    setMetadataClock(payload.captured_at);
    setPipelineLatencyMs(payload.pipeline_latency_ms);
    setZoneVersion(payload.zone_version);
    setAreaKpis([
      { label: 'Đối tượng trong khu', value: String(payload.kpi_delta.area_active_objects), color: 'var(--ink)' },
      {
        label: 'Vi phạm loại xe hôm nay',
        value: String(payload.kpi_delta.area_zone_violations),
        color: payload.kpi_delta.area_zone_violations > 0 ? 'var(--p0)' : 'var(--ink)',
      },
      { label: 'Xe nâng / container hoạt động', value: String(payload.kpi_delta.area_active_machinery), color: 'var(--ink)' },
      { label: 'Zone khu vực', value: String(payload.kpi_delta.area_total_zones), color: 'var(--ink)' },
    ]);
    setAiError(null);
  });

  // Fetch events from backend API; metadata lane drives KPI/status, while MJPEG remains bbox source of truth.
  useEffect(() => {
    let cancelled = false;

    const loadEvents = async () => {
      try {
        const rawEvents = await fetchLatestEvents(activeCam, 20);
        if (!cancelled) {
          const mapped: AreaEvent[] = rawEvents.map((evt: any) => {
            const timeStr = new Date(evt.timestamp).toLocaleTimeString('vi-VN', {
              hour: '2-digit',
              minute: '2-digit',
            });
            const isOk = evt.severity_level < 3;
            return {
              id: evt.id,
              time: timeStr,
              obj: evt.object_class,
              zone: evt.zone_name || 'Ngoài zone',
              st: isOk ? 'Được phép' : 'Vi phạm',
              ok: isOk,
            };
          });
          setEvents(mapped);
          setEventsError(null);
        }
      } catch (error) {
        if (!cancelled) {
          setEventsError(error instanceof Error ? error.message : 'Không thể tải sự kiện.');
        }
      }
    };

    loadEvents();

    const evtInterval = setInterval(loadEvents, 2000);

    return () => {
      cancelled = true;
      clearInterval(evtInterval);
    };
  }, [activeCam]);

  const activeZone = zones.find((z) => z.id === activeZoneId) || zones[0];

  // Dynamic Understream Vehicle Rules Pills derived from Active Zone
  const typeRules = CANONICAL_8_TYPES.map((t) => {
    if (!activeZone) return { label: `✓ ${t.label}`, ok: true };
    const forbiddenList = (activeZone as any).forbidden_classes || [];
    const allowedList = (activeZone as any).allowed_classes || [];

    const isAllowed = allowedList.length > 0
      ? ruleClassMatches(allowedList, t.key)
      : !ruleClassMatches(forbiddenList, t.key);

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
  const videoSrc = `${getVideoFeedUrl(activeCam, {
    drawZones: false,
    confThreshold: debugConfThreshold,
    showStaticContainers,
  })}&attempt=${streamAttempt}`;
  const camTitle = 'Bãi Kiểm';

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
                  background: streamStatus === 'live' ? 'var(--ok)' : streamStatus === 'error' ? 'var(--p0)' : 'var(--warn)',
                  animation: streamStatus === 'live' ? 'liveDot 1.4s infinite' : undefined,
                }}
              />
              <span style={{ fontSize: '12.5px', fontWeight: 600, color: streamStatus === 'live' ? 'var(--ok)' : 'var(--ink3)' }}>
                {streamStatus === 'live' ? 'TRỰC TIẾP' : streamStatus === 'error' ? 'MẤT LUỒNG' : 'ĐANG KẾT NỐI'}
              </span>

              <span style={{ fontSize: '12px', color: 'var(--ink3)' }}>
                {camTitle} · {clock}
              </span>
              <span style={{ fontSize: '12px', color: metadataStatus === 'online' ? 'var(--ok)' : metadataStatus === 'degraded' ? 'var(--warn)' : 'var(--ink3)' }}>
                Metadata: {metadataStatus.toUpperCase()}
              </span>
            </div>

            <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginLeft: '12px' }}>
              <label
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '6px',
                  fontSize: '11px',
                  color: 'var(--ink3)',
                  whiteSpace: 'nowrap',
                }}
              >
                <span>Ngưỡng bbox</span>
                <input
                  type="range"
                  min="0"
                  max="1"
                  step="0.05"
                  value={debugConfThreshold}
                  onChange={(event) => {
                    setDebugConfThreshold(Number(event.target.value));
                    setStreamStatus('loading');
                    setStreamAttempt((attempt) => attempt + 1);
                  }}
                  aria-label="Ngưỡng hiển thị bbox debug"
                  style={{ width: '86px' }}
                />
                <span style={{ fontFamily: "'IBM Plex Mono', monospace", color: 'var(--ink2)' }}>
                  {Math.round(debugConfThreshold * 100)}%
                </span>
              </label>
              <label
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '6px',
                  fontSize: '11px',
                  color: 'var(--ink3)',
                  whiteSpace: 'nowrap',
                }}
              >
                <input
                  type="checkbox"
                  checked={showStaticContainers}
                  onChange={(event) => {
                    setShowStaticContainers(event.target.checked);
                    setStreamStatus('loading');
                    setStreamAttempt((attempt) => attempt + 1);
                  }}
                />
                Container tĩnh
              </label>
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
            <img
              key={videoSrc}
              src={videoSrc}
              alt="Area Security live stream"
              onLoad={() => setStreamStatus('live')}
              onError={() => setStreamStatus('error')}
              style={{
                position: 'absolute',
                inset: 0,
                width: '100%',
                height: '100%',
                objectFit: 'cover',
                zIndex: 1,
              }}
            />

            {/* Zone geometry comes from shared editor state; the MJPEG stream remains the only bbox renderer. */}
            <svg
              viewBox="0 0 100 100"
              preserveAspectRatio="none"
              aria-label="Các zone giám sát đã đồng bộ"
              style={{
                position: 'absolute',
                inset: 0,
                width: '100%',
                height: '100%',
                zIndex: 2,
                pointerEvents: 'none',
              }}
            >
              {zones.map((zone) => {
                if (!zone.points || zone.points.length < 3) return null;
                const selected = zone.id === activeZoneId;
                return (
                  <polygon
                    key={zone.id}
                    points={zone.points.map(([x, y]) => `${x},${y}`).join(' ')}
                    fill={`${zone.color}${selected ? '2e' : '18'}`}
                    stroke={zone.color}
                    strokeWidth={selected ? 2.25 : 1.5}
                    strokeDasharray={selected ? undefined : '5 4'}
                    vectorEffect="non-scaling-stroke"
                  />
                );
              })}
            </svg>

            {zones.map((zone) => {
              if (!zone.points || zone.points.length < 3) return null;
              const anchor = zone.points.reduce((top, point) => point[1] < top[1] ? point : top);
              return (
                <span
                  key={`label-${zone.id}`}
                  style={{
                    position: 'absolute',
                    left: `${anchor[0]}%`,
                    top: `${anchor[1]}%`,
                    transform: 'translateY(-110%)',
                    zIndex: 2,
                    padding: '2px 6px',
                    borderRadius: '4px',
                    background: zone.color,
                    color: '#06080a',
                    fontSize: '9.5px',
                    fontWeight: 700,
                    pointerEvents: 'none',
                    whiteSpace: 'nowrap',
                  }}
                >
                  {zone.name}
                </span>
              );
            })}

            {streamStatus !== 'live' && (
              <div
                role={streamStatus === 'error' ? 'alert' : 'status'}
                aria-live="polite"
                style={{
                  position: 'absolute',
                  inset: 0,
                  zIndex: 3,
                  display: 'grid',
                  placeItems: 'center',
                  background: 'rgba(6,8,10,.78)',
                  color: 'var(--ink2)',
                  textAlign: 'center',
                }}
              >
                <div>
                  <div style={{ fontWeight: 700, marginBottom: '8px' }}>
                    {streamStatus === 'error' ? 'Không thể tải luồng MJPEG' : 'Đang chờ frame đầu tiên…'}
                  </div>
                  {streamStatus === 'error' && (
                    <button
                      type="button"
                      onClick={() => {
                        setStreamStatus('loading');
                        setStreamAttempt((attempt) => attempt + 1);
                      }}
                      style={{ padding: '6px 12px', cursor: 'pointer' }}
                    >
                      Thử kết nối lại
                    </button>
                  )}
                </div>
              </div>
            )}

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

            <div
              style={{
                position: 'absolute',
                left: '10px',
                top: '9px',
                background: 'rgba(0,0,0,.7)',
                color: '#e3e7ea',
                fontSize: '10px',
                padding: '3px 7px',
                borderRadius: '5px',
                fontFamily: "'IBM Plex Mono', monospace",
                border: '1px solid rgba(255,255,255,0.1)',
                zIndex: 4,
              }}
            >
              {`v${zoneVersion ?? '—'} · ${pipelineLatencyMs !== null ? `${Math.round(pipelineLatencyMs)}ms` : '—'} · ${metadataClock ? new Date(metadataClock).toLocaleTimeString('vi-VN') : 'chờ metadata'}`}
            </div>
          </div>

          {(aiError || zonesError) && (
            <div role="alert" style={{ marginTop: '10px', padding: '9px 12px', border: '1px solid var(--warn)', borderRadius: '8px', color: 'var(--warn)', fontSize: '12px' }}>
              {aiError ? `AI degraded: ${aiError}` : `Zone degraded: ${zonesError}`}
            </div>
          )}

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
            {eventsError ? (
              <div role="alert" style={{ padding: '40px 20px', textAlign: 'center', color: 'var(--p0)', fontSize: '12.5px' }}>
                {eventsError}
              </div>
            ) : events.length === 0 ? (
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
