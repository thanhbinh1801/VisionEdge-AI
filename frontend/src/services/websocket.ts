import { EventRecord } from '../types';

export class WebSocketClient {
  private url: string;
  private ws: WebSocket | null = null;
  private listeners: ((event: EventRecord) => void)[] = [];

  constructor(url: string = 'ws://localhost:8000/ws/alerts') {
    this.url = url;
  }

  public connect() {
    try {
      this.ws = new WebSocket(this.url);

      this.ws.onmessage = (event) => {
        try {
          const data: EventRecord = JSON.parse(event.data);
          this.listeners.forEach((cb) => cb(data));
        } catch {
          // JSON parse error handling
        }
      };

      this.ws.onclose = () => {
        // Auto-reconnect stub after 5s
        setTimeout(() => this.connect(), 5000);
      };
    } catch {
      // WS connection failure fallback
    }
  }

  public subscribe(callback: (event: EventRecord) => void): () => void {
    this.listeners.push(callback);
    return () => {
      this.listeners = this.listeners.filter((cb) => cb !== callback);
    };
  }

  public disconnect() {
    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }
  }
}
