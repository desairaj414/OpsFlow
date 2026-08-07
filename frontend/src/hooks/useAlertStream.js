"use client";

import { useEffect, useRef, useState } from "react";

// Live alert feed via SSE (PRD §7). Token goes in the query string because
// browser EventSource cannot set an Authorization header.
export function useAlertStream({ apiBase, token, maxAlerts = 50 }) {
  const [alerts, setAlerts] = useState([]);
  const [connectionStatus, setConnectionStatus] = useState("connecting");
  const sourceRef = useRef(null);

  useEffect(() => {
    if (!token) return;

    const source = new EventSource(`${apiBase}/alerts/stream?token=${encodeURIComponent(token)}`);
    sourceRef.current = source;

    source.onopen = () => setConnectionStatus("live");
    source.onerror = () => setConnectionStatus("disconnected");
    source.onmessage = (event) => {
      const alert = JSON.parse(event.data);
      setAlerts((prev) => [alert, ...prev].slice(0, maxAlerts));
    };

    return () => source.close();
  }, [apiBase, token, maxAlerts]);

  return { alerts, connectionStatus };
}
