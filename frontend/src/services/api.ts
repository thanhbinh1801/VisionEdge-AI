import { AssistantClip, EventRecord, KpiData, ZoneCacheInfo, ZoneConfig, VehicleTag } from '../types';
import {
  ApiResponse,
  BBoxSample,
  CreateBBoxSampleItem,
  DatasetSource,
  ObjectLabel,
  ObjectLabelCategory,
  ZoneSyncResult,
} from '../contracts/api/dataset.schema';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api/v1';

export interface LiveDetection {
  id: string;
  object_class: string;
  vietnamese_name: string;
  label: string;
  confidence: number;
  bbox: [number, number, number, number]; // [left, top, width, height] percentage or [xmin, ymin, xmax, ymax]
  severity: number; // 1: Green, 2: Yellow, 3: Red
  zone_violation: boolean;
  zone_name?: string;
  raw_class?: string;
  canonical_class?: string;
  bbox_xyxy_norm?: [number, number, number, number];
  zone_eval_method?: 'bottom_center' | 'footprint_overlap' | 'bbox_overlap_ratio' | 'center_point_fallback' | 'none';
  zone_overlap_ratio?: number | null;
  detection_frame_id?: string;
  track_id?: string | null;
}

/** Trạng thái OCR engine; chỉ camera cổng mới trả về, các camera khác là undefined. */
export type OcrStatus = 'ready' | 'unavailable';

export interface LiveDetectionSnapshot {
  detections: LiveDetection[];
  frameId?: string;
  frameTimestamp?: string;
  ocrStatus?: OcrStatus;
}

interface ZoneWriteEnvelopeSuccess {
  success: true;
  data: {
    zone: any | null;
    cache: ZoneCacheInfo;
  };
  error: null;
  meta: {
    timestamp: string;
    request_id: string;
  };
}

export interface VideoFrameMetadata {
  sourceName: string;
  fps?: number;
  totalFrames?: number;
  frameIndex: number;
  timestampSeconds: number;
}

export interface VideoFrameResult {
  blob: Blob;
  metadata: VideoFrameMetadata;
}

interface SourceListData {
  items: DatasetSource[];
  page: number;
  limit: number;
  total_items: number;
  total_pages: number;
}

async function readDatasetJson<T>(response: Response): Promise<T> {
  const payload = (await response.json()) as ApiResponse<T>;
  if (!payload.success) {
    const details = payload.error.details?.map((item) => `${item.field}: ${item.issue}`).join('; ');
    throw new Error(details ? `${payload.error.message} (${details})` : payload.error.message);
  }
  return payload.data;
}

export async function fetchDatasetLabels(includeDeleted = false): Promise<ObjectLabel[]> {
  const response = await fetch(`${API_BASE_URL}/dataset/labels?include_deleted=${includeDeleted}`);
  if (!response.ok) throw new Error(`Không thể tải nhãn đối tượng (HTTP ${response.status})`);
  const data = await readDatasetJson<{ items: ObjectLabel[] }>(response);
  return data.items;
}

export async function createDatasetLabel(payload: {
  label_name: string;
  category: Exclude<ObjectLabelCategory, 'custom'>;
}): Promise<{ label: ObjectLabel; sync?: ZoneSyncResult }> {
  const response = await fetch(`${API_BASE_URL}/dataset/labels`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
  if (!response.ok) return readDatasetJson(response);
  return readDatasetJson(response);
}

export async function updateDatasetLabel(
  labelId: string,
  payload: { label_name?: string; category?: Exclude<ObjectLabelCategory, 'custom'> },
): Promise<{ label: ObjectLabel; sync?: ZoneSyncResult }> {
  const response = await fetch(`${API_BASE_URL}/dataset/labels/${encodeURIComponent(labelId)}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
  if (!response.ok) return readDatasetJson(response);
  return readDatasetJson(response);
}

export async function deleteDatasetLabel(labelId: string): Promise<{ label: ObjectLabel }> {
  const response = await fetch(`${API_BASE_URL}/dataset/labels/${encodeURIComponent(labelId)}`, {
    method: 'DELETE',
  });
  if (!response.ok) return readDatasetJson(response);
  return readDatasetJson(response);
}

export async function restoreDatasetLabel(labelId: string): Promise<{ label: ObjectLabel; sync?: ZoneSyncResult }> {
  const response = await fetch(`${API_BASE_URL}/dataset/labels/${encodeURIComponent(labelId)}/restore`, {
    method: 'POST',
  });
  if (!response.ok) return readDatasetJson(response);
  return readDatasetJson(response);
}

export async function fetchDatasetSources(kind?: DatasetSource['kind']): Promise<SourceListData> {
  const params = new URLSearchParams({ page: '1', limit: '50' });
  if (kind) params.set('kind', kind);
  const response = await fetch(`${API_BASE_URL}/dataset/sources?${params.toString()}`);
  if (!response.ok) throw new Error(`Không thể tải media source (HTTP ${response.status})`);
  return readDatasetJson<SourceListData>(response);
}

export async function uploadDatasetSource(file: File, name?: string): Promise<DatasetSource> {
  const form = new FormData();
  form.append('file', file);
  if (name) form.append('name', name);
  form.append('idempotency_key', `${file.name}-${file.size}-${file.lastModified}`);

  const response = await fetch(`${API_BASE_URL}/dataset/sources`, {
    method: 'POST',
    body: form,
  });
  if (!response.ok) {
    const data = await readDatasetJson<{ source: DatasetSource }>(response);
    return data.source;
  }
  const data = await readDatasetJson<{ source: DatasetSource }>(response);
  return data.source;
}

export async function deleteDatasetSource(sourceId: string): Promise<{
  deleted_id: string;
  deleted_sample_count: number;
  labels: ObjectLabel[];
}> {
  const response = await fetch(`${API_BASE_URL}/dataset/sources/${encodeURIComponent(sourceId)}`, {
    method: 'DELETE',
  });
  if (!response.ok) return readDatasetJson(response);
  return readDatasetJson(response);
}

export async function fetchDatasetFrame(
  sourceId: string,
  selector: { timestamp?: number; frameIndex?: number } = {},
): Promise<VideoFrameResult> {
  const params = new URLSearchParams();
  if (selector.timestamp !== undefined) params.set('timestamp', String(selector.timestamp));
  if (selector.frameIndex !== undefined) params.set('frame_index', String(selector.frameIndex));
  const response = await fetch(`${API_BASE_URL}/dataset/sources/${encodeURIComponent(sourceId)}/frame?${params.toString()}`);
  if (!response.ok) throw new Error(`Không thể tải frame dataset (HTTP ${response.status})`);

  const frameIndex = Number(response.headers.get('X-Frame-Index'));
  const timestampSeconds = Number(response.headers.get('X-Frame-Timestamp'));
  const fps = Number(response.headers.get('X-Video-Fps'));
  const totalFrames = Number(response.headers.get('X-Video-Frame-Count'));
  return {
    blob: await response.blob(),
    metadata: {
      sourceName: response.headers.get('X-Dataset-Source-Id') || sourceId,
      fps: Number.isFinite(fps) && fps > 0 ? fps : undefined,
      totalFrames: Number.isFinite(totalFrames) && totalFrames > 0 ? totalFrames : undefined,
      frameIndex: Number.isFinite(frameIndex) ? frameIndex : selector.frameIndex ?? 0,
      timestampSeconds: Number.isFinite(timestampSeconds) ? timestampSeconds : selector.timestamp ?? 0,
    },
  };
}

export async function fetchDatasetSamples(filters: {
  sourceId?: string;
  frameIndex?: number | null;
  labelId?: string;
} = {}): Promise<BBoxSample[]> {
  const params = new URLSearchParams();
  if (filters.sourceId) params.set('source_id', filters.sourceId);
  if (filters.frameIndex !== undefined && filters.frameIndex !== null) params.set('frame_index', String(filters.frameIndex));
  if (filters.labelId) params.set('label_id', filters.labelId);
  const response = await fetch(`${API_BASE_URL}/dataset/samples?${params.toString()}`);
  if (!response.ok) throw new Error(`Không thể tải BBox samples (HTTP ${response.status})`);
  const data = await readDatasetJson<{ items: BBoxSample[] }>(response);
  return data.items;
}

export async function batchCreateDatasetSamples(samples: CreateBBoxSampleItem[]): Promise<{
  saved_count: number;
  samples: BBoxSample[];
  labels: ObjectLabel[];
}> {
  const response = await fetch(`${API_BASE_URL}/dataset/samples:batch`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ samples }),
  });
  if (!response.ok) return readDatasetJson(response);
  return readDatasetJson(response);
}

export async function updateDatasetSample(
  sampleId: string,
  payload: Partial<CreateBBoxSampleItem>,
): Promise<{ sample?: BBoxSample; labels: ObjectLabel[] }> {
  const response = await fetch(`${API_BASE_URL}/dataset/samples/${encodeURIComponent(sampleId)}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
  if (!response.ok) return readDatasetJson(response);
  return readDatasetJson(response);
}

export async function deleteDatasetSample(sampleId: string): Promise<{ deleted_id?: string; labels: ObjectLabel[] }> {
  const response = await fetch(`${API_BASE_URL}/dataset/samples/${encodeURIComponent(sampleId)}`, {
    method: 'DELETE',
  });
  if (!response.ok) return readDatasetJson(response);
  return readDatasetJson(response);
}

export async function syncDatasetZones(): Promise<ZoneSyncResult> {
  const response = await fetch(`${API_BASE_URL}/dataset/sync-zones`, {
    method: 'POST',
  });
  if (!response.ok) return readDatasetJson<{ sync: ZoneSyncResult }>(response).then((data) => data.sync);
  const data = await readDatasetJson<{ sync: ZoneSyncResult }>(response);
  return data.sync;
}

export async function fetchLatestEvents(cameraId?: string, limit: number = 20): Promise<EventRecord[]> {
  const url = cameraId
    ? `${API_BASE_URL}/events?camera_id=${encodeURIComponent(cameraId)}&limit=${limit}`
    : `${API_BASE_URL}/events?limit=${limit}`;
  const res = await fetch(url);
  if (!res.ok) throw new Error(`Không thể tải sự kiện (HTTP ${res.status})`);
  return await res.json();
}

/** Bốn chỉ số của dashboard cổng, do backend tính trên toàn bộ dữ liệu. */
export interface GateKpi {
  camera_id: string;
  vehicles_total: number;
  lpr_success: number;
  lpr_failed: number;
  /** Thang 0-100. */
  avg_confidence: number;
}

/**
 * Lấy KPI cổng từ backend.
 *
 * Trước đây dashboard tự đếm trên mảng sự kiện vừa tải về, mà mảng đó bị chặn ở
 * `limit = 20` — nên "Lượt xe qua cổng" đứng cứng ở 20 ngay khi cơ sở dữ liệu vượt
 * ngưỡng đó, và "Không đọc được" luôn bằng 0 vì lượt đọc hỏng không sinh bản ghi nào.
 */
export async function fetchGateKpi(cameraId: string): Promise<GateKpi> {
  const res = await fetch(`${API_BASE_URL}/events/gate-kpi?camera_id=${encodeURIComponent(cameraId)}`);
  if (!res.ok) throw new Error(`Không thể tải KPI cổng (HTTP ${res.status})`);
  return await res.json();
}

const CLASS_ALIAS_MAP: Record<string, string[]> = {
  container: ['container', 'Container', 'Xe container'],
  truck: ['truck', 'Xe tải'],
  forklift: ['forklift', 'Xe nâng'],
  crane: ['crane', 'Xe cẩu'],
  car: ['car', 'Xe con'],
  motorbike: ['motorbike', 'Xe máy'],
  bicycle: ['bicycle', 'Xe đạp'],
  person: ['person', 'Người'],
};

function buildTypesMap(allowedClasses: string[] = []): Record<string, number> {
  const acc: Record<string, number> = {};
  allowedClasses.forEach((cls) => {
    acc[cls] = 1;
    const lower = cls.toLowerCase();
    for (const [key, aliases] of Object.entries(CLASS_ALIAS_MAP)) {
      if (key === lower || aliases.includes(cls)) {
        aliases.forEach((a) => { acc[a] = 1; });
        acc[key] = 1;
      }
    }
  });
  return acc;
}

function mapZone(z: any): ZoneConfig {
  return {
    id: z.id,
    name: z.name,
    camera_id: z.camera_id,
    color: z.color || '#EF4444',
    points: Array.isArray(z.vertices)
      ? z.vertices.map((pt: any) => (Array.isArray(pt) ? pt : [pt.x, pt.y]))
      : [],
    types: buildTypesMap(z.allowed_classes),
    allowed_classes: z.allowed_classes || [],
    forbidden_classes: z.forbidden_classes || [],
  };
}

function unwrapZonesPayload(data: any): ZoneConfig[] {
  if (Array.isArray(data)) {
    return data.map(mapZone);
  }
  if (data && data.success === true && data.data && Array.isArray(data.data.items)) {
    return data.data.items.map(mapZone);
  }
  return [];
}

export async function fetchZones(cameraId?: string): Promise<ZoneConfig[]> {
  try {
    const url = cameraId ? `${API_BASE_URL}/zones?camera_id=${cameraId}` : `${API_BASE_URL}/zones`;
    const res = await fetch(url);
    if (!res.ok) throw new Error(`HTTP error ${res.status}`);
    const data = await res.json();
    return unwrapZonesPayload(data);
  } catch {
    return [];
  }
}

export async function fetchZonesStrict(cameraId?: string): Promise<ZoneConfig[]> {
  const url = cameraId
    ? `${API_BASE_URL}/zones?camera_id=${encodeURIComponent(cameraId)}`
    : `${API_BASE_URL}/zones`;
  const res = await fetch(url);
  if (!res.ok) throw new Error(`Không thể tải cấu hình zone (HTTP ${res.status})`);
  const data = await res.json();
  return unwrapZonesPayload(data);
}

export async function createZoneApi(zone: {
  camera_id: string;
  name: string;
  vertices: [number, number][];
  allowed_classes?: string[];
  forbidden_classes?: string[];
  color?: string;
}): Promise<ZoneConfig | null> {
  try {
    const res = await fetch(`${API_BASE_URL}/zones`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        camera_id: zone.camera_id,
        name: zone.name,
        vertices: zone.vertices,
        allowed_classes: zone.allowed_classes || [],
        forbidden_classes: zone.forbidden_classes || [],
        color: zone.color || '#30d158'
      }),
    });
    if (!res.ok) throw new Error(`HTTP error ${res.status}`);
    const payload = (await res.json()) as ZoneWriteEnvelopeSuccess;
    if (!payload.data.zone) return null;
    return mapZone(payload.data.zone);
  } catch {
    return null;
  }
}

export async function updateZoneApi(zoneId: string, patch: {
  name?: string;
  vertices?: [number, number][];
  allowed_classes?: string[];
  forbidden_classes?: string[];
  color?: string;
}): Promise<boolean> {
  try {
    const res = await fetch(`${API_BASE_URL}/zones/${zoneId}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(patch),
    });
    return res.ok;
  } catch {
    return false;
  }
}

export async function deleteZoneApi(zoneId: string): Promise<boolean> {
  try {
    const res = await fetch(`${API_BASE_URL}/zones/${zoneId}`, {
      method: 'DELETE',
    });
    return res.ok;
  } catch {
    return false;
  }
}

export async function fetchLiveDetections(cameraId: string = 'BAI-KIEM', confThreshold: number = 0.35, videoTime?: number): Promise<LiveDetectionSnapshot> {
  let url = `${API_BASE_URL}/events/live-detections?camera_id=${encodeURIComponent(cameraId)}&conf_threshold=${confThreshold}`;
  if (typeof videoTime === 'number') {
    url += `&video_time=${videoTime.toFixed(2)}`;
  }
  const res = await fetch(url);
  if (!res.ok) throw new Error(`Dịch vụ AI không phản hồi (HTTP ${res.status})`);
  const ocrStatus = res.headers.get('X-OCR-Status');
  return {
    detections: await res.json(),
    frameId: res.headers.get('X-Frame-Id') || undefined,
    frameTimestamp: res.headers.get('X-Frame-Timestamp') || undefined,
    ocrStatus: ocrStatus === 'ready' || ocrStatus === 'unavailable' ? ocrStatus : undefined,
  };
}

/** Một lượt hội thoại gửi kèm để trợ lý hiểu câu hỏi rút gọn ("còn nữa không"). */
export interface AssistantTurn {
  role: 'user' | 'ai';
  text: string;
}

/** Phản hồi của `POST /assistant/query` — khớp `QueryResponse` tại backend/app/models/schemas/assistant.py. */
export interface AssistantQueryResult {
  answer: string;
  sql_query?: string | null;
  clips: AssistantClip[];
  /** `QuerySpec` backend đã dùng; gửi lại ở lượt sau để hỏi tiếp. */
  spec?: Record<string, unknown> | null;
}

function parseClips(raw: unknown): AssistantClip[] {
  if (!Array.isArray(raw)) return [];
  return raw.flatMap((item) => {
    if (!item || typeof item !== 'object') return [];
    const clip = item as Record<string, unknown>;
    if (typeof clip.url !== 'string' || !clip.url) return [];
    return [
      {
        event_id: typeof clip.event_id === 'string' ? clip.event_id : null,
        url: clip.url,
        timestamp: typeof clip.timestamp === 'string' ? clip.timestamp : null,
        camera: typeof clip.camera === 'string' ? clip.camera : null,
        label: typeof clip.label === 'string' ? clip.label : null,
      },
    ];
  });
}

export async function askAssistant(
  query: string,
  options: { history?: AssistantTurn[]; previousSpec?: Record<string, unknown> | null } = {}
): Promise<AssistantQueryResult> {
  const res = await fetch(`${API_BASE_URL}/assistant/query`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      query,
      history: options.history ?? [],
      previous_spec: options.previousSpec ?? null,
    }),
  });
  if (!res.ok) throw new Error(`Trợ lý không phản hồi (HTTP ${res.status})`);
  const data = await res.json();
  if (typeof data?.answer !== 'string') {
    throw new Error('Phản hồi của trợ lý thiếu trường `answer`');
  }

  // Backend cũ chỉ trả `clip_url`; quy về cùng một hình dạng `clips` để UI chỉ có
  // một đường render.
  const clips = parseClips(data.clips);
  if (clips.length === 0 && typeof data.clip_url === 'string' && data.clip_url) {
    clips.push({ url: data.clip_url });
  }

  return {
    answer: data.answer,
    sql_query: typeof data.sql_query === 'string' ? data.sql_query : null,
    clips,
    spec: data.spec && typeof data.spec === 'object' ? data.spec : null,
  };
}

export async function fetchVehicles(): Promise<VehicleTag[]> {
  try {
    const res = await fetch(`${API_BASE_URL}/vehicles`);
    if (!res.ok) throw new Error(`HTTP error ${res.status}`);
    return await res.json();
  } catch {
    return [];
  }
}

export async function updateVehicleTagApi(plate: string, tag: 'known' | 'unknown' | 'blacklisted'): Promise<boolean> {
  try {
    const res = await fetch(`${API_BASE_URL}/vehicles/${encodeURIComponent(plate)}/tag`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ tag_label: tag }),
    });
    return res.ok;
  } catch {
    return false;
  }
}

export async function fetchKpiMetrics(): Promise<KpiData> {
  try {
    const res = await fetch(`${API_BASE_URL}/kpi`);
    if (!res.ok) throw new Error(`HTTP error ${res.status}`);
    return await res.json();
  } catch {
    return {
      totalEventsToday: 0,
      criticalAlertsToday: 0,
      vehiclesEnteredToday: 0,
      activeZones: 0,
      hourlyTrends: [],
    };
  }
}

export async function fetchZoneFrame(
  cameraId: string,
  selector: { timestamp?: number; frameIndex?: number } = {},
): Promise<VideoFrameResult> {
  const params = new URLSearchParams({ camera_id: cameraId });
  if (selector.timestamp !== undefined) params.set('timestamp', String(selector.timestamp));
  if (selector.frameIndex !== undefined) params.set('frame_index', String(selector.frameIndex));
  const response = await fetch(`${API_BASE_URL}/zones/video-frame?${params.toString()}`);
  if (!response.ok) throw new Error(`Không thể tải frame preview (HTTP ${response.status})`);

  const frameIndex = Number(response.headers.get('X-Frame-Index'));
  const timestampSeconds = Number(response.headers.get('X-Frame-Timestamp'));
  const fps = Number(response.headers.get('X-Video-Fps'));
  const totalFrames = Number(response.headers.get('X-Video-Frame-Count'));
  const encodedSource = response.headers.get('X-Video-Source');
  return {
    blob: await response.blob(),
    metadata: {
      sourceName: encodedSource ? decodeURIComponent(encodedSource) : cameraId,
      fps: Number.isFinite(fps) && fps > 0 ? fps : undefined,
      totalFrames: Number.isFinite(totalFrames) && totalFrames > 0 ? totalFrames : undefined,
      frameIndex: Number.isFinite(frameIndex) ? frameIndex : selector.frameIndex ?? 0,
      timestampSeconds: Number.isFinite(timestampSeconds)
        ? timestampSeconds
        : selector.timestamp ?? 0,
    },
  };
}

export function getVideoFeedUrl(
  cameraId: string,
  options: { drawZones?: boolean; confThreshold?: number; showStaticContainers?: boolean } = {},
): string {
  const params = new URLSearchParams({ camera_id: cameraId });
  if (options.drawZones !== undefined) {
    params.set('draw_zones', String(options.drawZones));
  }
  if (typeof options.confThreshold === 'number') {
    const clampedThreshold = Math.min(1, Math.max(0, options.confThreshold));
    params.set('conf_threshold', clampedThreshold.toFixed(2));
  }
  if (options.showStaticContainers !== undefined) {
    params.set('show_static_containers', String(options.showStaticContainers));
  }
  return `${API_BASE_URL}/events/video-feed?${params.toString()}`;
}
