import { useState, useEffect, useRef } from 'react';

const MAX_RETRIES = 10;

export function useWebSocket(sessionId, token) {
  const [messages, setMessages] = useState([]);
  const [connected, setConnected] = useState(false);
  const [reconnecting, setReconnecting] = useState(false);
  const wsRef = useRef(null);
  const retriesRef = useRef(0);
  const reconnectTimerRef = useRef(null);
  const sessionIdRef = useRef(sessionId);
  const tokenRef = useRef(token);

  useEffect(() => {
    sessionIdRef.current = sessionId;
    tokenRef.current = token;
  });

  useEffect(() => {
    setMessages([]);
    if (!sessionId || !token) return;

    let cancelled = false;

    function connect() {
      if (cancelled) return;
      const protocol = window.location.protocol === 'https:' ? 'wss' : 'ws';
      const url = `${protocol}://${window.location.host}/ws/${sessionId}`;
      const ws = new WebSocket(url);

      ws.onopen = () => {
        clearTimeout(reconnectTimerRef.current);
        ws.send(JSON.stringify({ type: 'auth', token: tokenRef.current }));
        setConnected(true);
        setReconnecting(false);
        retriesRef.current = 0;
      };

      ws.onmessage = (e) => {
        try {
          const msg = JSON.parse(e.data);
          setMessages(prev => [...prev.slice(-99), msg]);
        } catch (_) {}
      };

      ws.onclose = (e) => {
        setConnected(false);
        if (cancelled) return;
        if (e.code === 4001 || e.code === 4003) return;
        if (retriesRef.current < MAX_RETRIES) {
          // Only surface "Reconnecting..." label if retry takes > 1.5s (debounce)
          reconnectTimerRef.current = setTimeout(() => setReconnecting(true), 1500);
          const delay = Math.min(1000 * 2 ** retriesRef.current, 30000);
          retriesRef.current++;
          setTimeout(connect, delay);
        }
      };

      wsRef.current = ws;
    }

    connect();

    return () => {
      cancelled = true;
      clearTimeout(reconnectTimerRef.current);
      setReconnecting(false);
      if (wsRef.current) {
        wsRef.current.onclose = null;
        wsRef.current.close();
        wsRef.current = null;
      }
      setConnected(false);
    };
  }, [sessionId, token]);

  return { messages, connected, reconnecting };
}
