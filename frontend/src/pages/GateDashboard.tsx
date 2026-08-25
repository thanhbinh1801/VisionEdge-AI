import React, { useState, useEffect, useMemo, useCallback, useRef } from 'react';
import {
  ResponsiveContainer,
  AreaChart,
  Area,
  BarChart,
  Bar,
  LineChart,
  Line,
  RadialBarChart,
  RadialBar,
  PolarAngleAxis,
  Tooltip,
} from 'recharts';
import { useApp } from '../context/AppContext';
import { fetchZones, fetchLatestEvents, fetchLiveDetections, LiveDetection } from '../services/api';
import { ZoneConfig, GateEvent } from '../types';

const CAMERA_ID = 'GATE-01';
const VIDEO_SRC = '/videos/GATE-01.mp4';
const POLL_INTERVAL_MS = 3000;
// Vòng lặp detection tự lên lịch lại sau mỗi lần hoàn tất, thay vì setInterval cố định:
// suy luận YOLO mất vài trăm ms, dùng interval ngắn sẽ chồng request. Nghỉ ngắn giữa
// hai lần gọi để bbox bám sát video, vì khoảng nghỉ chính là độ trễ tối đa của overlay.
const DETECTION_GAP_MS = 700;
const STALE_AFTER_MS = 12000;
const NARROW_BREAKPOINT = 980;

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

/** Một dòng biển số đã nhận diện, kèm mốc thời gian gốc để dựng biểu đồ. */
interface GateEventRow extends GateEvent {
  ts: number;
}

interface TrendPoint {
  t: string;
  total: number;
  read: number;
  unread: number;
}

/** Backend trả confidence dạng 0..1; một số bản ghi cũ lưu sẵn 0..100. */
function toPercent(raw: number | null | undefined): number | null {
  if (raw === null || raw === undefined) return null;
  const value = raw <= 1 ? raw * 100 : raw;
  return Math.round(value);
}

function formatClockTime(iso: string | undefined, withSeconds = false): string {
  if (!iso) return '--:--';
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return '--:--';
  return date.toLocaleTimeString('vi-VN', {
    hour: '2-digit',
    minute: '2-digit',
    ...(withSeconds ? { second: '2-digit' } : {}),
  });
}

function mapEventRow(evt: any): GateEventRow {
  const plate: string = evt.license_plate || '—';
  const hasPlate = Boolean(evt.license_plate);
  const date = evt.timestamp ? new Date(evt.timestamp) : null;
  return {
    id: evt.id || `evt-${Math.random().toString(16).slice(2)}`,
    time: formatClockTime(evt.timestamp),
    plate,
    zone: evt.zone_name || 'Cổng vào',
    conf: hasPlate ? toPercent(evt.confidence) : null,
    ts: date && !Number.isNaN(date.getTime()) ? date.getTime() : 0,
  };
}

/** Gom sự kiện theo từng phút để dựng 4 biểu đồ KPI Recharts. */
function buildTrendSeries(rows: GateEventRow[]): TrendPoint[] {
  const buckets = new Map<number, TrendPoint>();
  rows
    .filter((row) => row.ts > 0)
    .forEach((row) => {
      const minute = Math.floor(row.ts / 60000) * 60000;
      const existing = buckets.get(minute);
      const isRead = row.conf !== null;
      if (existing) {
        existing.total += 1;
        existing.read += isRead ? 1 : 0;
        existing.unread += isRead ? 0 : 1;
      } else {
        buckets.set(minute, {
          t: new Date(minute).toLocaleTimeString('vi-VN', { hour: '2-digit', minute: '2-digit' }),
          total: 1,
          read: isRead ? 1 : 0,
          unread: isRead ? 0 : 1,
        });
      }
    });

  return Array.from(buckets.entries())
    .sort((a, b) => a[0] - b[0])
    .map(([, point]) => point);
}

const cardStyle: React.CSSProperties = {
  background: 'var(--card)',
  border: '1px solid var(--line)',
  borderRadius: '13px',
  padding: '14px',
};

const chartHeight = 44;

export const GateDashboard: React.FC = () => {
  const { clock, zonesByCam, updateZone, toggleZoneType, setTab, setSubTab } = useApp();

  const [zones, setZones] = useState<ZoneConfig[]>([]);
  const [activeZoneId, setActiveZoneId] = useState<string | null>(null);
  const [events, setEvents] = useState<GateEventRow[]>([]);
  const [detections, setDetections] = useState<LiveDetection[]>([]);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [lastSyncAt, setLastSyncAt] = useState<number | null>(null);
  const [isNarrow, setIsNarrow] = useState<boolean>(false);
  const [videoFailed, setVideoFailed] = useState<boolean>(false);
  const videoRef = useRef<HTMLVideoElement>(null);

  // Inline Zone Name Editing State
  const [editingZoneId, setEditingZoneId] = useState<string | null>(null);
  const [editingNameText, setEditingNameText] = useState<string>('');

  // Responsive breakpoint — chỉ chạm `window` bên trong useEffect để render đầu tiên luôn tất định.
  useEffect(() => {
    const applyWidth = () => setIsNarrow(window.innerWidth < NARROW_BREAKPOINT);
    applyWidth();
    window.addEventListener('resize', applyWidth);
    return () => window.removeEventListener('resize', applyWidth);
  }, []);

  // Hydrate & Sync GATE-01 Zones from Context / Backend DB
  useEffect(() => {
    const camZones = zonesByCam[CAMERA_ID] || [];
    if (camZones.length > 0) {
      setZones(camZones);
      setActiveZoneId((prev) => (prev && camZones.some((z) => z.id === prev) ? prev : camZones[0].id));
      return;
    }
    let cancelled = false;
    fetchZones(CAMERA_ID).then((res) => {
      if (cancelled) return;
      if (res && res.length > 0) {
        setZones(res);
        setActiveZoneId(res[0].id);
      } else {
        setZones([]);
        setActiveZoneId(null);
      }
    });
    return () => {
      cancelled = true;
    };
  }, [zonesByCam]);

  // BBox bám theo đúng khung hình đang phát: gửi kèm video.currentTime để backend
  // suy luận trên chính frame đó, thay vì trên frame nào đó nó tự đọc được.
  useEffect(() => {
    let cancelled = false;
    let timer: number | undefined;

    const tick = async () => {
      const video = videoRef.current;
      // Đọc mốc thời gian ngay trước khi gọi để sai lệch chỉ còn bằng độ trễ suy luận.
      const at = video && !video.paused ? video.currentTime : undefined;
      const liveResult = await fetchLiveDetections(CAMERA_ID, at);
      if (cancelled) return;
      setDetections(liveResult.detections);
      if (liveResult.detections.length > 0) setLastSyncAt(Date.now());
      timer = window.setTimeout(tick, DETECTION_GAP_MS);
    };

    tick();
    return () => {
      cancelled = true;
      if (timer !== undefined) window.clearTimeout(timer);
    };
  }, []);

  // Realtime LPR polling: biển số nhận diện từ CSDL.
  useEffect(() => {
    let cancelled = false;

    const loadBackendData = async () => {
      const rawEvents = await fetchLatestEvents(CAMERA_ID, 20);
      if (cancelled) return;

      // Chỉ lấy sự kiện LPR: endpoint /events?camera_id=GATE-01 còn trả cả ZONE_VIOLATION
      // (license_plate = null) — nếu không lọc, người đi vào zone sẽ bị đếm nhầm thành
      // "biển số không đọc được" trong danh sách và cả 2 thẻ KPI.
      const mapped = (rawEvents || [])
        .filter((e: any) => e.event_type === 'LPR' || Boolean(e.license_plate))
        .map(mapEventRow)
        .sort((a, b) => b.ts - a.ts);
      setEvents(mapped);
      setIsLoading(false);
      if (rawEvents && rawEvents.length > 0) {
        setLastSyncAt(Date.now());
      }
    };

    loadBackendData();
    const interval = setInterval(loadBackendData, POLL_INTERVAL_MS);
    return () => {
      cancelled = true;
      clearInterval(interval);
    };
  }, []);

  const activeZone = zones.find((z) => z.id === activeZoneId) || zones[0];

  // Dynamic Vehicle Rules Pills derived from Active GATE-01 Zone
  const typeRules = useMemo(
    () =>
      CANONICAL_8_TYPES.map((t) => {
        if (!activeZone) return { key: t.key, name: t.label, label: `✓ ${t.label}`, ok: true };
        const forbiddenList = activeZone.forbidden_classes || [];
        const allowedList = activeZone.allowed_classes || [];

        let isAllowed = true;
        if (forbiddenList.includes(t.key)) {
          isAllowed = false;
        } else if (allowedList.length > 0 && !allowedList.includes(t.key)) {
          isAllowed = false;
        }

        return {
          key: t.key,
          name: t.label,
          label: `${isAllowed ? '✓' : '✕'} ${t.label}`,
          ok: isAllowed,
        };
      }),
    [activeZone]
  );

  const handleSaveZoneName = useCallback(
    (zoneId: string) => {
      const trimmed = editingNameText.trim();
      if (trimmed) {
        updateZone(CAMERA_ID, zoneId, { name: trimmed });
      }
      setEditingZoneId(null);
      setEditingNameText('');
    },
    [editingNameText, updateZone]
  );

  const handleOpenZoneEditor = useCallback(() => {
    setTab('set');
    setSubTab('zone');
  }, [setTab, setSubTab]);

  // KPI numbers computed from real backend event rows.
  const readEvents = events.filter((e) => e.conf !== null);
  const unreadCount = events.length - readEvents.length;
  const avgConfValue =
    readEvents.length > 0
      ? Math.round(readEvents.reduce((sum, e) => sum + (e.conf || 0), 0) / readEvents.length)
      : 0;

  const trend = useMemo(() => buildTrendSeries(events), [events]);
  const hasTrend = trend.length > 0;
  const isStale = lastSyncAt !== null && Date.now() - lastSyncAt > STALE_AFTER_MS;
  const isEmpty = !isLoading && events.length === 0;

  const kpis = [
    {
      label: 'Lượt xe qua cổng',
      value: String(events.length),
      color: 'var(--ink)',
      chart: (
        <AreaChart data={trend} margin={{ top: 2, right: 0, bottom: 0, left: 0 }}>
          <defs>
            <linearGradient id="gateTotalFill" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="#2f9bff" stopOpacity={0.55} />
              <stop offset="100%" stopColor="#2f9bff" stopOpacity={0.04} />
            </linearGradient>
          </defs>
          <Tooltip
            cursor={{ stroke: 'var(--line2)' }}
            contentStyle={{
              background: 'var(--raise)',
              border: '1px solid var(--line2)',
              borderRadius: '8px',
              fontSize: '11px',
            }}
            labelStyle={{ color: 'var(--ink2)' }}
          />
          <Area
            type="monotone"
            dataKey="total"
            name="Lượt xe"
            stroke="#2f9bff"
            strokeWidth={1.8}
            fill="url(#gateTotalFill)"
            isAnimationActive={false}
          />
        </AreaChart>
      ),
    },
    {
      label: 'Biển số đọc được',
      value: String(readEvents.length),
      color: 'var(--ok)',
      chart: (
        <BarChart data={trend} margin={{ top: 2, right: 0, bottom: 0, left: 0 }}>
          <Tooltip
            cursor={{ fill: 'rgba(48,209,88,.12)' }}
            contentStyle={{
              background: 'var(--raise)',
              border: '1px solid var(--line2)',
              borderRadius: '8px',
              fontSize: '11px',
            }}
            labelStyle={{ color: 'var(--ink2)' }}
          />
          <Bar dataKey="read" name="Đọc được" fill="#30d158" radius={[2, 2, 0, 0]} isAnimationActive={false} />
        </BarChart>
      ),
    },
    {
      label: 'Không đọc được',
      value: String(unreadCount),
      color: 'var(--p1)',
      chart: (
        <LineChart data={trend} margin={{ top: 4, right: 2, bottom: 0, left: 2 }}>
          <Tooltip
            cursor={{ stroke: 'var(--line2)' }}
            contentStyle={{
              background: 'var(--raise)',
              border: '1px solid var(--line2)',
              borderRadius: '8px',
              fontSize: '11px',
            }}
            labelStyle={{ color: 'var(--ink2)' }}
          />
          <Line
            type="monotone"
            dataKey="unread"
            name="Không đọc được"
            stroke="#ff9f0a"
            strokeWidth={1.8}
            dot={false}
            isAnimationActive={false}
          />
        </LineChart>
      ),
    },
    {
      label: 'Độ tin cậy trung bình',
      value: `${avgConfValue}%`,
      color: avgConfValue >= 95 ? 'var(--ok)' : 'var(--ink)',
      chart: (
        <RadialBarChart
          data={[{ name: 'Độ tin cậy', value: avgConfValue }]}
          startAngle={90}
          endAngle={-270}
          innerRadius="72%"
          outerRadius="100%"
          margin={{ top: 0, right: 0, bottom: 0, left: 0 }}
        >
          <PolarAngleAxis type="number" domain={[0, 100]} tick={false} axisLine={false} />
          <RadialBar
            dataKey="value"
            cornerRadius={6}
            fill={avgConfValue >= 95 ? '#30d158' : '#2f9bff'}
            background={{ fill: 'rgba(255,255,255,.07)' }}
            isAnimationActive={false}
          />
        </RadialBarChart>
      ),
    },
  ];

  // BBox biển số ưu tiên detection có độ tin cậy cao nhất từ AI Vision Pipeline.
  const primaryDetection = useMemo(() => {
    if (detections.length === 0) return null;
    return detections.reduce((best, d) => (d.confidence > best.confidence ? d : best), detections[0]);
  }, [detections]);

  const latestPlate = events.find((e) => e.plate !== '—');

  return (
    <div style={{ padding: '20px', maxWidth: '1360px', margin: '0 auto' }}>
      {/* 4 Recharts KPI Visualizers */}
      <div
        role="group"
        aria-label="Chỉ số KPI cổng vào GATE-01"
        style={{
          display: 'grid',
          gridTemplateColumns: isNarrow ? 'repeat(2, minmax(0, 1fr))' : 'repeat(4, minmax(0, 1fr))',
          gap: '12px',
          marginBottom: '18px',
        }}
      >
        {kpis.map((k) => (
          <div key={k.label} style={cardStyle}>
            <div style={{ fontSize: '11.5px', color: 'var(--ink3)', marginBottom: '8px' }}>{k.label}</div>
            <div
              style={{
                fontSize: '24px',
                fontWeight: 700,
                fontFamily: "'IBM Plex Mono', monospace",
                color: k.color,
              }}
            >
              {isLoading ? '…' : k.value}
            </div>
            {/* Biểu đồ chỉ mang tính minh hoạ; số liệu đã có trong text phía trên. */}
            <div style={{ height: `${chartHeight}px`, marginTop: '6px' }} aria-hidden="true">
              {hasTrend ? (
                <ResponsiveContainer width="100%" height="100%">
                  {k.chart}
                </ResponsiveContainer>
              ) : (
                <div
                  style={{
                    height: '100%',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    fontSize: '10.5px',
                    color: 'var(--ink3)',
                    border: '1px dashed var(--line)',
                    borderRadius: '8px',
                  }}
                >
                  {isLoading ? 'Đang tải…' : 'Chưa có dữ liệu'}
                </div>
              )}
            </div>
          </div>
        ))}
      </div>

      {/* Main Grid */}
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: isNarrow ? 'minmax(0, 1fr)' : 'minmax(0, 1.5fr) minmax(0, 1fr)',
          gap: '16px',
        }}
      >
        {/* Left Column: Live Camera Viewport */}
        <div>
          {/* Header Bar with Live Indicator, Zone Selector & Quick Edit Link */}
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              marginBottom: '10px',
              flexWrap: 'wrap',
              gap: '8px',
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: '9px' }} role="status" aria-live="polite">
              <span
                aria-hidden="true"
                style={{
                  width: '8px',
                  height: '8px',
                  borderRadius: '50%',
                  background: isStale ? 'var(--p1)' : 'var(--p0)',
                  animation: 'liveDot 1.4s infinite',
                }}
              />
              <span style={{ fontSize: '12.5px', fontWeight: 600, color: isStale ? 'var(--p1)' : 'var(--p0)' }}>
                {isStale ? 'MẤT ĐỒNG BỘ' : 'TRỰC TIẾP'}
              </span>
              <span style={{ fontSize: '12px', color: 'var(--ink3)' }}>
                {CAMERA_ID} · Cổng vào · {clock}
              </span>
            </div>

            {/* Zone Selector Buttons with Inline Double-Click Editing */}
            <div style={{ display: 'flex', alignItems: 'center', gap: '6px', flexWrap: 'wrap' }}>
              {zones.map((z) => {
                const isEditing = editingZoneId === z.id;
                const isSelected = activeZoneId === z.id;
                return isEditing ? (
                  <input
                    key={z.id}
                    type="text"
                    value={editingNameText}
                    aria-label={`Đổi tên zone ${z.name}`}
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
                    aria-pressed={isSelected}
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
            {/* Live Gate Camera Stream */}
            {videoFailed ? (
              <div
                style={{
                  position: 'absolute',
                  inset: 0,
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  flexDirection: 'column',
                  gap: '6px',
                  color: 'var(--ink3)',
                  fontSize: '12px',
                  textAlign: 'center',
                  padding: '16px',
                }}
              >
                <span style={{ fontSize: '20px' }} aria-hidden="true">
                  ⚠️
                </span>
                Không tải được luồng camera {CAMERA_ID}.
                <span style={{ fontSize: '11px' }}>Kiểm tra tệp {VIDEO_SRC} trên backend.</span>
              </div>
            ) : (
              <video
                key={VIDEO_SRC}
                ref={videoRef}
                src={VIDEO_SRC}
                autoPlay
                loop
                muted
                playsInline
                aria-label={`Luồng camera trực tiếp ${CAMERA_ID} tại cổng vào`}
                onError={() => setVideoFailed(true)}
                style={{
                  position: 'absolute',
                  inset: 0,
                  width: '100%',
                  height: '100%',
                  objectFit: 'cover',
                }}
              />
            )}

            {/* SVG Polygon Zones Overlay */}
            <svg
              viewBox="0 0 100 100"
              preserveAspectRatio="none"
              aria-hidden="true"
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
                    aria-label={`Đổi tên zone ${z.name}`}
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
                <button
                  key={z.id}
                  onClick={() => {
                    setEditingZoneId(z.id);
                    setEditingNameText(z.name);
                  }}
                  aria-label={`Chỉnh sửa tên zone ${z.name}`}
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
                    fontFamily: 'inherit',
                  }}
                >
                  {z.name.toUpperCase()} ✎
                </button>
              );
            })}

            {/* Realtime BBox Overlay từ AI Vision Pipeline (bbox: [left, top, width, height] %) */}
            {detections.map((d) => {
              const [left, top, width, height] = d.bbox;
              const isPrimary = primaryDetection !== null && d.id === primaryDetection.id;
              const boxColor = d.zone_violation ? '#ff453a' : isPrimary ? '#39e0d0' : '#2f9bff';
              const badge =
                isPrimary && latestPlate
                  ? `${latestPlate.plate} · ${latestPlate.conf !== null ? `${latestPlate.conf}%` : 'không đọc được'}`
                  : `${d.vietnamese_name} · ${Math.round(d.confidence * 100)}%`;
              return (
                <div
                  key={d.id}
                  style={{
                    position: 'absolute',
                    left: `${left}%`,
                    top: `${top}%`,
                    width: `${width}%`,
                    height: `${height}%`,
                    border: `1.5px solid ${boxColor}`,
                    background: `${boxColor}1a`,
                    pointerEvents: 'none',
                  }}
                >
                  <span
                    style={{
                      position: 'absolute',
                      left: '-1px',
                      top: '-18px',
                      background: boxColor,
                      color: '#06080a',
                      fontSize: '10px',
                      fontWeight: 700,
                      padding: '1px 7px',
                      borderRadius: '3px',
                      whiteSpace: 'nowrap',
                      fontFamily: "'IBM Plex Mono', monospace",
                    }}
                  >
                    {badge}
                  </span>
                </div>
              );
            })}

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
            <div style={{ fontSize: '11px', color: 'var(--ink3)', marginBottom: '6px', fontWeight: 600 }} id="gate-rules-label">
              Chọn loại xe được phép vào zone ({activeZone ? activeZone.name : CAMERA_ID}) (bấm để đổi ✓ được phép / ✕ cấm):
            </div>
            <div style={{ display: 'flex', gap: '6px', flexWrap: 'wrap' }} role="group" aria-labelledby="gate-rules-label">
              {typeRules.map((t) => {
                const fg = t.ok ? 'var(--ok)' : 'var(--p0)';
                const bg = t.ok ? 'var(--okq)' : 'var(--p0q)';
                const border = t.ok ? 'var(--ok)' : 'rgba(255,69,58,.4)';
                return (
                  <button
                    key={t.key}
                    onClick={() => activeZone && toggleZoneType(CAMERA_ID, activeZone.id, t.key)}
                    disabled={!activeZone}
                    aria-pressed={t.ok}
                    aria-label={`${t.name}: ${t.ok ? 'được phép' : 'bị cấm'}`}
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
                      cursor: activeZone ? 'pointer' : 'not-allowed',
                      opacity: activeZone ? 1 : 0.55,
                      fontFamily: 'inherit',
                      transition: 'all 0.2s ease',
                    }}
                  >
                    {t.label}
                  </button>
                );
              })}
            </div>
            {zones.length === 0 && !isLoading && (
              <div style={{ marginTop: '8px', fontSize: '11px', color: 'var(--ink3)' }}>
                Chưa cấu hình zone nào cho {CAMERA_ID}. Bấm “Vẽ / Cấu hình Zone” để tạo zone đầu tiên.
              </div>
            )}
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
          <div
            style={{
              padding: '13px 15px',
              borderBottom: '1px solid var(--line)',
              fontSize: '13.5px',
              fontWeight: 600,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              gap: '8px',
            }}
          >
            <span id="gate-plate-list-label">Biển số đã nhận diện</span>
            <span style={{ fontSize: '11px', color: 'var(--ink3)', fontWeight: 500 }}>
              {lastSyncAt ? `Cập nhật ${formatClockTime(new Date(lastSyncAt).toISOString(), true)}` : '—'}
            </span>
          </div>

          <div style={{ flex: 1, overflow: 'auto' }} role="list" aria-labelledby="gate-plate-list-label" aria-busy={isLoading}>
            {isLoading && (
              <div style={{ padding: '18px 15px', fontSize: '12px', color: 'var(--ink3)' }}>
                Đang tải dữ liệu nhận diện từ {CAMERA_ID}…
              </div>
            )}

            {isEmpty && (
              <div style={{ padding: '18px 15px', fontSize: '12px', color: 'var(--ink3)', lineHeight: 1.6 }}>
                Chưa ghi nhận biển số nào tại {CAMERA_ID}.
                {isStale && (
                  <>
                    <br />
                    Dữ liệu chưa được đồng bộ gần đây — kiểm tra backend đang chạy ở cổng 8000.
                  </>
                )}
              </div>
            )}

            {events.map((e) => {
              const confStr = e.conf === null ? 'không đọc được' : `${e.conf}%`;
              const confColor = e.conf === null ? 'var(--p1)' : e.conf >= 95 ? 'var(--ok)' : 'var(--p1)';
              return (
                <div
                  key={e.id}
                  role="listitem"
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
