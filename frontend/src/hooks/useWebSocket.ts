import { useEffect, useRef, useState, useCallback } from 'react';
import { WSEvent } from '../types';

const WS_URL = import.meta.env.VITE_WS_URL || 'ws://localhost:8000/ws';

interface UseWebSocketOptions {
  onMessage?: (event: WSEvent) => void;
  onOpen?: () => void;
  onClose?: () => void;
  onError?: (error: Event) => void;
  autoReconnect?: boolean;
  reconnectInterval?: number;
  enabled?: boolean; // Only connect when enabled is true
}

export function useWebSocket(options: UseWebSocketOptions = {}) {
  const {
    onMessage,
    onOpen,
    onClose,
    onError,
    autoReconnect = true,
    reconnectInterval = 3000,
    enabled = true, // Default to true for backward compatibility
  } = options;

  const [isConnected, setIsConnected] = useState(false);
  const [connectionStatus, setConnectionStatus] = useState<
    'connected' | 'disconnected' | 'reconnecting'
  >('disconnected');

  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const shouldReconnectRef = useRef(true);

  const connect = useCallback(() => {
    try {
      const ws = new WebSocket(WS_URL);

      ws.onopen = () => {
        console.log('WebSocket connected');
        setIsConnected(true);
        setConnectionStatus('connected');
        wsRef.current = ws;
        onOpen?.();
      };

      ws.onmessage = (event) => {
        try {
          console.log('');
          console.log('🟡 [WS_HOOK] Raw WebSocket message received');
          console.log('   Raw data:', event.data);
          const data: WSEvent = JSON.parse(event.data);
          console.log('   Parsed event type:', data.type);
          console.log('   Parsed event data:', data.data);
          console.log('   ✅ Calling onMessage handler...');
          onMessage?.(data);
          console.log('   ✅ onMessage handler complete');
        } catch (error) {
          console.error('❌ Failed to parse WebSocket message:', error);
          console.error('   Raw data:', event.data);
        }
      };

      ws.onerror = (error) => {
        console.error('WebSocket error:', error);
        onError?.(error);
      };

      ws.onclose = () => {
        console.log('WebSocket disconnected');
        setIsConnected(false);
        setConnectionStatus('disconnected');
        wsRef.current = null;
        onClose?.();

        // Attempt to reconnect
        if (autoReconnect && shouldReconnectRef.current) {
          setConnectionStatus('reconnecting');
          reconnectTimeoutRef.current = setTimeout(() => {
            connect();
          }, reconnectInterval);
        }
      };

      wsRef.current = ws;
    } catch (error) {
      console.error('Failed to create WebSocket connection:', error);
      setConnectionStatus('disconnected');
    }
  }, [onMessage, onOpen, onClose, onError, autoReconnect, reconnectInterval]);

  const disconnect = useCallback(() => {
    shouldReconnectRef.current = false;

    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
      reconnectTimeoutRef.current = null;
    }

    if (wsRef.current) {
      wsRef.current.close();
      wsRef.current = null;
    }

    setIsConnected(false);
    setConnectionStatus('disconnected');
  }, []);

  const send = useCallback((data: any) => {
    console.log('');
    console.log('🟢 [WS_HOOK] Sending message to WebSocket');
    console.log('   Message:', data);
    console.log('   WS state:', wsRef.current?.readyState);
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify(data));
      console.log('   ✅ Message sent');
    } else {
      console.warn('   ⚠️  WebSocket is not connected. Cannot send message.');
    }
  }, []);

  useEffect(() => {
    // Only connect if enabled is true
    if (enabled) {
      shouldReconnectRef.current = true;
      connect();
    } else {
      // Disconnect if enabled becomes false
      disconnect();
    }

    return () => {
      disconnect();
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [enabled]); // Only re-run when 'enabled' changes, not when connect/disconnect change

  return {
    isConnected,
    connectionStatus,
    send,
    disconnect,
  };
}
