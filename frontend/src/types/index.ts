export type TabId = 'mon' | 'area' | 'set' | 'qa';
export type SubTabId = 'label' | 'zone' | 'obj';
export type SeverityLevel = 1 | 2 | 3;

export interface VehicleRecord {
  plate: string;
  type: string;
  visits: number;
  last: string;
  tag: 'quen' | 'la';
  tint?: string;
}

export interface GateEvent {
  id: string;
  time: string;
  plate: string;
  zone: string;
  conf: number | null;
}

export interface AreaEvent {
  id: string;
  time: string;
  obj: string;
  zone: string;
  st: string;
  ok: boolean;
}

export interface ZoneConfig {
  id: string;
  name: string;
  camera_id?: string;
  color: string;
  points: [number, number][]; // Relative coordinates [x, y] in percentage (0 to 100)
  types: Record<string, number>; // Label name -> 1 (allowed/✓) or 0 (forbidden/✕)
  allowed_classes?: string[];
  forbidden_classes?: string[];
}

export interface ZoneCacheInfo {
  camera_id: string;
  zone_version: number;
  cache_status: 'hot' | 'refreshing';
  refreshed_at: string;
}

export interface AreaMetadataObject {
  track_id: string;
  object_class: string;
  display_name?: string;
  confidence: number;
  bbox: [number, number, number, number];
  center_point: {
    x: number;
    y: number;
  };
  zone_hits: Array<{
    zone_id: string;
    zone_name: string;
    rule_result: 'allowed' | 'prohibited' | 'observed';
  }>;
}

export interface AreaFrameMetadataPayload {
  camera_id: 'BAI-KIEM';
  frame_id: string;
  captured_at: string;
  zone_version: number;
  stream_status: 'online' | 'degraded' | 'offline';
  pipeline_latency_ms: number;
  objects: AreaMetadataObject[];
  kpi_delta: {
    area_active_objects: number;
    area_zone_violations: number;
    area_active_machinery: number;
    area_total_zones: number;
  };
}

export interface AreaFrameMetadataEvent {
  event_type: 'AREA_FRAME_METADATA';
  timestamp: string;
  payload: AreaFrameMetadataPayload;
}

export interface ObjectLabel {
  id: string;
  name: string;
  kind: 'nguoi' | 'xe';
  tint: string;
  samples: number;
}

export interface AnnotationSource {
  id: string;
  name: string;
  kind: 'img' | 'video';
  img?: string;
  tint?: string;
}

export interface AnnotationSample {
  id: string;
  labelId: string;
  srcId: string;
  frame?: number | null;
  x: number;
  y: number;
  w: number;
  h: number;
  session?: number;
}

/** Một clip bằng chứng trả kèm câu trả lời của trợ lý. */
export interface AssistantClip {
  event_id?: string | null;
  url: string;
  timestamp?: string | null;
  camera?: string | null;
  label?: string | null;
}

export interface AIChatMessage {
  id: string;
  role: 'user' | 'ai';
  text: string;
  /** Câu SQL do backend sinh ra, hiển thị để người dùng kiểm chứng câu trả lời. */
  sqlQuery?: string;
  /** Các clip 10s bằng chứng của đúng những sự kiện có trong câu trả lời. */
  clips?: AssistantClip[];
  /** `QuerySpec` backend đã dùng cho lượt này; gửi lại để hỏi tiếp. */
  spec?: Record<string, unknown> | null;
  /** `pending` khi đang chờ backend, `error` khi gọi thất bại. */
  status?: 'pending' | 'error';
}

export interface KpiCardData {
  label: string;
  value: string;
  color: string;
}

/* Backward compatibility legacy types */
export interface EventRecord {
  id: string;
  timestamp: string;
  cameraId: string;
  cameraName: string;
  zoneId?: string;
  zoneName?: string;
  eventType: 'LPR' | 'ZONE_INTRUSION' | 'UNAUTHORIZED_VEHICLE' | 'SAFETY_VIOLATION';
  severity: SeverityLevel;
  plateNumber?: string;
  objectClass: string;
  confidence: number;
  cropUrl?: string;
  videoClipUrl?: string;
  status: 'NEW' | 'ACKNOWLEDGED' | 'RESOLVED';
}

export interface VehicleTag {
  id: string;
  plateNumber: string;
  ownerName: string;
  vehicleType: string;
  category: 'WHITELIST' | 'BLACKLIST' | 'VISITOR' | 'CONTRACTOR';
  notes?: string;
  updatedAt: string;
}

export interface KpiData {
  totalEventsToday: number;
  criticalAlertsToday: number;
  vehiclesEnteredToday: number;
  activeZones: number;
  hourlyTrends: { hour: string; events: number; lprCount: number }[];
}
