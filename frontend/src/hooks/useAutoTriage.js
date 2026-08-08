"use client";

import { useEffect, useRef, useState } from "react";

// Backend's `_alert_event_stream` (main.py) sends the first 20 backlog rows as an immediate
// catch-up burst, then live-tails one at a time every 10s — this mirrors that burst size so "new"
// here means genuinely newly-arrived, not the initial page-load replay.
const INITIAL_BACKLOG_SIZE = 20;
const MAX_NOTIFICATIONS = 20;

function workflowTypeForCategory(category) {
  return category === "degradation" ? "performance" : "incident";
}

// Watches the live alert stream and auto-triggers diagnosis for each newly-arrived alert's CI
// (skipping ones already ticketed or already queued), one at a time — human's explicit ask: new
// alerts diagnose themselves, but bounded/sequential like "Run all untriaged", not an uncontrolled
// flood. Runs at the CockpitShell level so it keeps working (and keeps notifying) regardless of
// which tab is active. Reads category/display_name straight off the alert itself (both already
// present on every alert payload, see main.py's `_fetch_alerts_after`) — this used to require a
// separate GET /alerts/correlated fetch just to look those two fields up, dropped along with the
// Ops Board cluster panel it was originally shared with.
export function useAutoTriage({ alerts, tickets, incident, refetchTickets }) {
  const [notifications, setNotifications] = useState([]);
  const seenAlertIds = useRef(new Set());
  const arrivalCount = useRef(0);
  const queueRef = useRef([]);
  const processingRef = useRef(false);
  const incidentRef = useRef(incident);
  incidentRef.current = incident;

  useEffect(() => {
    if (alerts.length === 0) return;
    const ticketedCis = new Set(tickets.map((t) => t.cmdb_ci));
    const queuedCis = new Set(queueRef.current.map((q) => q.ciId));

    // `alerts` is newest-first (useAlertStream prepends) — walk oldest-to-newest so arrival order
    // (and therefore the "first 20 = backlog" cutoff) is correct.
    for (const alert of [...alerts].reverse()) {
      if (seenAlertIds.current.has(alert.id)) continue;
      seenAlertIds.current.add(alert.id);
      arrivalCount.current += 1;
      if (arrivalCount.current <= INITIAL_BACKLOG_SIZE) continue;

      if (!alert.ci_id || ticketedCis.has(alert.ci_id) || queuedCis.has(alert.ci_id)) continue;
      queuedCis.add(alert.ci_id);
      queueRef.current.push({
        ciId: alert.ci_id,
        ciDisplayName: alert.ci_display_name || alert.ci_id,
        category: alert.category,
      });
    }

    processQueue();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [alerts, tickets]);

  async function processQueue() {
    if (processingRef.current) return;
    processingRef.current = true;
    while (queueRef.current.length > 0) {
      // Defer to any manual Diagnose/Run-all click already in flight — triggerRun is single-flight
      // shared state, two concurrent calls would clobber each other.
      while (incidentRef.current.loading) {
        // eslint-disable-next-line no-await-in-loop
        await new Promise((resolve) => setTimeout(resolve, 500));
      }
      const item = queueRef.current.shift();
      const notifId = `${item.ciId}-${Date.now()}`;
      setNotifications((prev) =>
        [{ id: notifId, ciId: item.ciId, ciDisplayName: item.ciDisplayName, status: "running", createdAt: new Date().toISOString(), run: null }, ...prev].slice(0, MAX_NOTIFICATIONS)
      );
      // silent: true — this must NOT change what's shown in Incident Workspace/Agent Trace; those
      // only update on an explicit click (Diagnose, Run-all, the Tickets tab's Open, or clicking
      // this notification once it's done).
      // eslint-disable-next-line no-await-in-loop
      const run = await incidentRef.current.triggerRun(item.ciId, workflowTypeForCategory(item.category), false, { silent: true });
      setNotifications((prev) => prev.map((n) => (n.id === notifId ? { ...n, status: run ? "done" : "error", run } : n)));
      refetchTickets();
    }
    processingRef.current = false;
  }

  return { notifications };
}
