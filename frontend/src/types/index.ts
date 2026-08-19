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

export interface AIChatMessage {
  id: string;
  role: 'user' | 'ai';
  text: string;
  clip?: {
    cam: string;
    from: string;
    to: string;
    title: string;
    boxColor: string;
    boxLabel: string;
    tint: string;
  };
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
