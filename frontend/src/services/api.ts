import { EventRecord, ZoneConfig, VehicleTag, KpiData } from '../types';

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
}

export async function fetchLatestEvents(cameraId?: string, limit: number = 20): Promise<EventRecord[]> {
  try {
    const url = cameraId 
      ? `${API_BASE_URL}/events?camera_id=${cameraId}&limit=${limit}`
      : `${API_BASE_URL}/events?limit=${limit}`;
    const res = await fetch(url);
    if (!res.ok) throw new Error(`HTTP error ${res.status}`);
    return await res.json();
  } catch {
    return [];
  }
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

export async function fetchZones(cameraId?: string): Promise<ZoneConfig[]> {
  try {
    const url = cameraId ? `${API_BASE_URL}/zones?camera_id=${cameraId}` : `${API_BASE_URL}/zones`;
    const res = await fetch(url);
    if (!res.ok) throw new Error(`HTTP error ${res.status}`);
    const data = await res.json();
    return data.map((z: any) => ({
      id: z.id,
      name: z.name,
      camera_id: z.camera_id,
      color: z.color || '#EF4444',
      points: Array.isArray(z.vertices) 
        ? z.vertices.map((pt: any) => (Array.isArray(pt) ? pt : [pt.x, pt.y])) 
        : [],
      types: buildTypesMap(z.allowed_classes),
      allowed_classes: z.allowed_classes || [],
      forbidden_classes: z.forbidden_classes || []
    }));
  } catch {
    return [];
  }
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
    const z = await res.json();
    return {
      id: z.id,
      name: z.name,
      camera_id: z.camera_id,
      color: z.color || '#30d158',
      points: Array.isArray(z.vertices) 
        ? z.vertices.map((pt: any) => (Array.isArray(pt) ? pt : [pt.x, pt.y])) 
        : [],
      types: buildTypesMap(z.allowed_classes),
      allowed_classes: z.allowed_classes || [],
      forbidden_classes: z.forbidden_classes || []
    };
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

export async function fetchLiveDetections(cameraId: string = 'BAI-KIEM'): Promise<LiveDetection[]> {
  try {
    const res = await fetch(`${API_BASE_URL}/events/live-detections?camera_id=${cameraId}`);
    if (!res.ok) throw new Error(`HTTP error ${res.status}`);
    return await res.json();
  } catch {
    return [];
  }
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
