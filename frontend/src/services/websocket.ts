import { AreaFrameMetadataEvent, EventRecord } from '../types';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api/v1';

function buildWebSocketUrl(cameraId: string): string {
  const base = API_BASE_URL.replace(/\/api\/v1\/?$/, '');
  const wsBase = base.replace(/^http/i, 'ws');
  const params = new URLSearchParams({
    camera_id: cameraId,
    conf_threshold: '0.35',
  });
  return `${wsBase}/ws/v1/events?${params.toString()}`;
}

export type RealtimeEvent = EventRecord | AreaFrameMetadataEvent;

export class WebSocketClient {
  private url: string;
  private ws: WebSocket | null = null;
  private listeners: ((event: RealtimeEvent) => void)[] = [];
  private reconnectTimer: number | null = null;
  private shouldReconnect = true;

  constructor(url: string = buildWebSocketUrl('BAI-KIEM')) {
    this.url = url;
  }

  public connect() {
    this.shouldReconnect = true;
    if (this.reconnectTimer !== null) {
      window.clearTimeout(this.reconnectTimer);
      this.reconnectTimer = null;
    }
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      return;
    }
    if (this.ws && this.ws.readyState === WebSocket.CONNECTING) {
      return;
    }

    try {
      this.ws = new WebSocket(this.url);

      this.ws.onmessage = (event) => {
        try {
          const data: RealtimeEvent = JSON.parse(event.data);
          this.listeners.forEach((cb) => cb(data));
        } catch {
          // JSON parse error handling
        }
      };

      this.ws.onclose = () => {
        this.ws = null;
        if (!this.shouldReconnect) {
          return;
        }
        this.reconnectTimer = window.setTimeout(() => {
          this.reconnectTimer = null;
          this.connect();
        }, 5000);
      };
    } catch {
      // WS connection failure fallback
    }
  }

  public subscribe(callback: (event: RealtimeEvent) => void): () => void {
    this.listeners.push(callback);
    return () => {
      this.listeners = this.listeners.filter((cb) => cb !== callback);
    };
  }

  public disconnect() {
    this.shouldReconnect = false;
    if (this.reconnectTimer !== null) {
      window.clearTimeout(this.reconnectTimer);
      this.reconnectTimer = null;
    }
    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }
  }
}

export function createAreaMetadataWebSocketClient(cameraId: string): WebSocketClient {
  return new WebSocketClient(buildWebSocketUrl(cameraId));
}
