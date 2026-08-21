import { useEffect, useRef } from 'react';
import { createAreaMetadataWebSocketClient, RealtimeEvent, WebSocketClient } from '../services/websocket';

export function useWebSocket(
  cameraId: string,
  onEventReceived?: (event: RealtimeEvent) => void,
) {
  const clientRef = useRef<WebSocketClient | null>(null);
  const eventHandlerRef = useRef<typeof onEventReceived>(onEventReceived);

  useEffect(() => {
    eventHandlerRef.current = onEventReceived;
  }, [onEventReceived]);

  useEffect(() => {
    const client = createAreaMetadataWebSocketClient(cameraId);
    client.connect();
    clientRef.current = client;

    const unsubscribe = client.subscribe((evt) => {
      if (eventHandlerRef.current) eventHandlerRef.current(evt);
    });

    return () => {
      unsubscribe();
      client.disconnect();
    };
  }, [cameraId]);
}
