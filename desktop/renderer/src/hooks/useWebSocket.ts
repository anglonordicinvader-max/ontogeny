import { useState, useEffect, useCallback, useRef } from 'react';
import type { AgentStatus, ActivityEvent } from '@/types';

const RECONNECT_DELAY = 3000;
const MAX_RECONNECT_ATTEMPTS = 10;

export function useWebSocket() {
  const [status, setStatus] = useState<AgentStatus | null>(null);
  const [events, setEvents] = useState<ActivityEvent[]>([]);
  const [connected, setConnected] = useState(false);
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectAttempts = useRef(0);
  const reconnectTimeout = useRef<NodeJS.Timeout | null>(null);
  const disposed = useRef(false);

  const connect = useCallback(async () => {
    if (disposed.current) return;
    try {
      let port: number;
      if (window.electronAPI) {
        port = await window.electronAPI.getBackendPort();
      } else {
        port = parseInt(new URLSearchParams(window.location.search).get('port') || '8765');
      }

      // Wait for backend to be ready before connecting
      await new Promise(resolve => setTimeout(resolve, 2000));
      
      const ws = new WebSocket(`ws://127.0.0.1:${port}/ws`);
      wsRef.current = ws;

      ws.onopen = () => {
        setConnected(true);
        reconnectAttempts.current = 0;
      };

      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          if (data.type === 'status') {
            setStatus(data.payload);
          } else if (data.type === 'event') {
            setEvents((prev) => [data.payload, ...prev].slice(0, 500));
          }
        } catch {
          console.error('Failed to parse WebSocket message');
        }
      };

      ws.onclose = () => {
        setConnected(false);
        wsRef.current = null;
        if (!disposed.current && reconnectAttempts.current < MAX_RECONNECT_ATTEMPTS) {
          reconnectTimeout.current = setTimeout(() => {
            reconnectAttempts.current++;
            connect();
          }, RECONNECT_DELAY);
        }
      };

      ws.onerror = () => {
        ws.close();
      };
    } catch (error) {
      console.error('WebSocket connection failed:', error);
    }
  }, []);

  useEffect(() => {
    disposed.current = false;
    connect();
    return () => {
      disposed.current = true;
      wsRef.current?.close();
      if (reconnectTimeout.current) {
        clearTimeout(reconnectTimeout.current);
      }
    };
  }, [connect]);

  const send = useCallback((type: string, payload?: unknown) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({ type, payload }));
    }
  }, []);

  return { status, events, connected, send };
}
