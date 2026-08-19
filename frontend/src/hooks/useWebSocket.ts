import { useEffect, useRef } from 'react';
import { WebSocketClient } from '../services/websocket';
import { EventRecord } from '../types';

export function useWebSocket(onEventReceived?: (event: EventRecord) => void) {
  const clientRef = useRef<WebSocketClient | null>(null);

  useEffect(() => {
    const client = new WebSocketClient();
    client.connect();
    clientRef.current = client;

    const unsubscribe = client.subscribe((evt) => {
      if (onEventReceived) onEventReceived(evt);
    });

    return () => {
      unsubscribe();
      client.disconnect();
    };
  }, [onEventReceived]);
}
