import { useState, useEffect, useRef } from 'react';

const MAX_RETRIES = 10;

export function useWebSocket(sessionId, token) {
  const [messages, setMessages] = useState([]);
  const [connected, setConnected] = useState(false);
  const wsRef = useRef(null);
  const retriesRef = useRef(0);
  // Keep a stable ref for the connect function
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
      const url = `${protocol}://${window.location.host}/ws/${sessionId}?token=${encodeURIComponent(token)}`;
      const ws = new WebSocket(url);

      ws.onopen = () => {
        setConnected(true);
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
      if (wsRef.current) {
        wsRef.current.onclose = null;
        wsRef.current.close();
        wsRef.current = null;
      }
      setConnected(false);
    };
  }, [sessionId, token]);

  return { messages, connected };
}
