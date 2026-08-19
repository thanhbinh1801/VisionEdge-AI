import { EventRecord, ZoneConfig, VehicleTag, KpiData } from '../types';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api/v1';

export async function fetchLatestEvents(limit: number = 20): Promise<EventRecord[]> {
  try {
    const res = await fetch(`${API_BASE_URL}/events?limit=${limit}`);
    if (!res.ok) throw new Error(`HTTP error ${res.status}`);
    return await res.json();
  } catch {
    return [];
  }
}

export async function fetchZones(): Promise<ZoneConfig[]> {
  try {
    const res = await fetch(`${API_BASE_URL}/zones`);
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
