"use client";

import { useEffect, useRef, useState } from "react";

// Live alert feed via SSE (PRD §7). Token goes in the query string because
// browser EventSource cannot set an Authorization header.
export function useAlertStream({ apiBase, token, maxAlerts = 50 }) {
  const [alerts, setAlerts] = useState([]);
  const [totalReceived, setTotalReceived] = useState(0);
  const [connectionStatus, setConnectionStatus] = useState("connecting");
  const sourceRef = useRef(null);
  const seenIdsRef = useRef(new Set());

  useEffect(() => {
    if (!token) return;

    const source = new EventSource(`${apiBase}/alerts/stream?token=${encodeURIComponent(token)}`);
    sourceRef.current = source;

    source.onopen = () => setConnectionStatus("live");
    source.onerror = () => setConnectionStatus("disconnected");
    source.onmessage = (event) => {
      const raw = JSON.parse(event.data);
      // A fresh EventSource (e.g. reconnecting because "view as" or login just reissued the JWT,
      // so `token` changed) replays the backend's catch-up backlog from scratch — dedupe by id so
      // that reconnect doesn't duplicate already-seen alerts (and their React keys) in the feed.
      if (seenIdsRef.current.has(raw.id)) return;
      seenIdsRef.current.add(raw.id);
      // `received_at` on the raw alert is the dataset's seeded historical timestamp (used for real
      // correlation math server-side) — not when THIS browser tab actually saw it arrive. The Ops
      // Board displays elapsed time since arrival, so stamp that separately here, once, at first
      // sight, rather than re-deriving it from a stale field on every render.
      const alert = { ...raw, stream_seen_at: Date.now() };
      setTotalReceived((n) => n + 1);
      setAlerts((prev) => [alert, ...prev].slice(0, maxAlerts));
    };

    return () => source.close();
  }, [apiBase, token, maxAlerts]);

  return { alerts, totalReceived, connectionStatus };
}
