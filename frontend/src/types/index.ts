export type SeverityLevel = 1 | 2 | 3;

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

export interface ZoneConfig {
  id: string;
  name: string;
  cameraId: string;
  polygonPoints: [number, number][]; // Relative coordinates [x, y] from 0.0 to 1.0
  severity: SeverityLevel;
  allowedClasses: string[];
  active: boolean;
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

export type TabId = 'gate' | 'area' | 'settings' | 'assistant';
