export type ObjectLabelCategory = 'person' | 'vehicle_shape' | 'custom';
export type ObjectLabelType = 'system' | 'custom';
export type DatasetSourceKind = 'img' | 'video';
export type ImportStatus = 'processing' | 'ready' | 'failed';
export type CoordinateSpace = 'percent_0_100';
export type ErrorCode =
  | 'BAD_REQUEST'
  | 'UNAUTHORIZED'
  | 'FORBIDDEN'
  | 'NOT_FOUND'
  | 'VALIDATION_ERROR'
  | 'DUPLICATE_LABEL_NAME'
  | 'SYSTEM_LABEL_LOCKED'
  | 'LABEL_IN_USE_BY_ZONE'
  | 'LABEL_INACTIVE'
  | 'SOURCE_NOT_READY'
  | 'UNSUPPORTED_MEDIA_TYPE'
  | 'UPLOAD_TOO_LARGE'
  | 'FRAME_NOT_AVAILABLE'
  | 'ZONE_CACHE_REFRESH_FAILED'
  | 'INTERNAL_SERVER_ERROR';

export interface ErrorPayload {
  code: ErrorCode;
  message: string;
  details?: Array<{ field: string; issue: string }>;
}

export interface MetaPayload {
  timestamp: string;
  request_id: string;
  page?: number;
  limit?: number;
  total_items?: number;
  total_pages?: number;
}

export type ApiResponse<T> =
  | { success: true; data: T; error: null; meta: MetaPayload }
  | { success: false; data: null; error: ErrorPayload; meta: MetaPayload };

export interface ObjectLabel {
  id: string;
  label_key: string;
  label_name: string;
  label_type: ObjectLabelType;
  category: ObjectLabelCategory;
  sample_count: number;
  is_active: boolean;
  deleted_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface DatasetSource {
  id: string;
  name: string;
  kind: DatasetSourceKind;
  public_url: string;
  original_filename: string;
  mime_type: 'image/jpeg' | 'image/png' | 'video/mp4' | 'video/quicktime';
  file_size_bytes: number;
  sha256: string;
  duration_seconds: number | null;
  total_frames: number | null;
  fps: number | null;
  width: number | null;
  height: number | null;
  import_status: ImportStatus;
  import_error: string | null;
  created_at: string;
  updated_at: string;
}

export interface BBoxPercent {
  x: number;
  y: number;
  w: number;
  h: number;
}

export interface BBoxSample {
  id: string;
  label_id: string;
  source_id: string;
  frame_index: number | null;
  frame_timestamp_seconds: number | null;
  bbox: BBoxPercent;
  coordinate_space: CoordinateSpace;
  label: {
    id: string;
    label_key: string;
    label_name: string;
  };
  created_at: string;
  updated_at: string;
}

export interface ZoneCacheInfo {
  camera_id: string;
  zone_version: number;
  cache_status: 'hot' | 'refreshing';
  refreshed_at: string;
}

export interface ZoneSyncResult {
  synced_labels: string[];
  affected_zones: string[];
  default_rule: 'forbidden';
  cache: ZoneCacheInfo[];
}

export interface CreateBBoxSampleItem {
  label_id: string;
  source_id: string;
  frame_index?: number | null;
  frame_timestamp_seconds?: number | null;
  bbox: BBoxPercent;
}
