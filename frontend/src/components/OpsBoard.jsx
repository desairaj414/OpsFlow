"use client";

import { useEffect, useState } from "react";
import { ChevronDown } from "lucide-react";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";

const SEVERITY_STYLE = {
  critical: "bg-red-600/10 text-red-600",
  warning: "bg-status-warning/10 text-status-warning",
  info: "bg-secondary text-muted-foreground",
};

const TICKET_STATUS_STYLE = {
  resolved: "bg-status-good/10 text-status-good",
  needs_approval: "bg-red-600/10 text-red-600",
  in_progress: "bg-status-warning/10 text-status-warning",
  open: "bg-secondary text-muted-foreground",
};

const TICKET_STATUS_LABEL = {
  resolved: "Resolved",
  needs_approval: "Needs approval",
  in_progress: "In progress",
  open: "Open",
};

const STATUS_FILTERS = [
  { key: "", label: "All statuses" },
  { key: "untriaged", label: "Not yet diagnosed" },
  { key: "needs_approval", label: "Needs approval" },
  { key: "in_progress", label: "In progress" },
  { key: "resolved", label: "Resolved" },
];

// fault alerts get diagnosed as an incident; a slow-creeping degradation gets diagnosed as a
// performance-tuning workflow (mirrors the fault/degradation split data_gen/alerts.py generates).
function workflowTypeForCategory(category) {
  return category === "degradation" ? "performance" : "incident";
}

// Shared pill-filter row, same visual pattern as the Knowledge Base tab's doc-type filter
// (ChunkInspector.jsx) so filtering looks and behaves the same everywhere in the app.
function FilterPills({ options, value, onChange }) {
  return (
    <div className="flex flex-wrap gap-1.5">
      {options.map((o) => (
        <button
          key={o.key}
          onClick={() => onChange(o.key)}
          className={cn(
            "rounded-full border border-border px-3 py-1 text-xs",
            value === o.key ? "bg-primary text-primary-foreground" : "text-muted-foreground hover:bg-secondary"
          )}
        >
          {o.label}
        </button>
      ))}
    </div>
  );
}

const CATEGORY_FILTERS = [
  { key: "", label: "All types" },
  { key: "fault", label: "Fault" },
  { key: "degradation", label: "Degradation" },
];

const SOURCE_LABEL = {
  snmp: "a network device (SNMP trap)",
  prometheus: "an infrastructure metrics monitor (Prometheus)",
  apm: "an application performance monitor (APM trace)",
};

// Counts UP from the moment this browser tab actually saw the alert arrive (0s, 1s, 2s... 1m...)
// rather than formatting the dataset's seeded historical `received_at` — that field is real and
// used server-side for correlation math, but showing "9 days ago" for something that just landed
// live in the feed reads as a bug, not a feature. Accepts a plain ms timestamp (Date.now() value),
// not an ISO string. `nowMs` is passed in so this re-evaluates on the ticking clock below instead
// of freezing at the value it had when the alert first rendered.
function formatSinceArrival(arrivedAtMs, nowMs) {
  if (!arrivedAtMs) return "";
  const diffSec = Math.max(0, Math.round((nowMs - arrivedAtMs) / 1000));
  if (diffSec < 1) return "0s ago";
  if (diffSec < 60) return `${diffSec}s ago`;
  const diffMin = Math.floor(diffSec / 60);
  if (diffMin < 60) return `${diffMin}m ago`;
  const diffHours = Math.floor(diffMin / 60);
  if (diffHours < 24) return `${diffHours}h ago`;
  return `${Math.floor(diffHours / 24)}d ago`;
}

// Ticks once a second so any relative "Xs/Xm ago" label in this tab counts up live instead of
// freezing at whatever value it had on last render (a new SSE alert isn't the only thing that
// should trigger a re-render — time passing should too).
function useClockTick(intervalMs = 1000) {
  const [now, setNow] = useState(() => Date.now());
  useEffect(() => {
    const id = setInterval(() => setNow(Date.now()), intervalMs);
    return () => clearInterval(id);
  }, [intervalMs]);
  return now;
}

// One alert, PLUS the triage status derived from it — the merged replacement for the old separate
// "correlated candidates" panel. Diagnosing one CI already sweeps up every fault alert on that CI
// (workflows/run's own scope, see supervisor.py), so a per-alert ticket-status pill gives the same
// practical outcome clustering did (one action handles every alert on that resource) without a
// second panel showing the same alerts grouped a different way — the old cluster view had grown
// low-value once topology-based correlation was fixed to stop over-merging unrelated CIs (see
// state-progress.md's CMDB relationship fix).
function AlertItem({ alert, ticket, busy, nowMs, onDiagnose, onOpenTicket }) {
  const [showRaw, setShowRaw] = useState(false);
  const rawText = typeof alert.raw_payload === "string" ? alert.raw_payload : JSON.stringify(alert.raw_payload);
  return (
    <li className="rounded-md border border-border p-3 text-sm">
      <div className="flex items-center justify-between gap-2">
        <span className="font-medium">{alert.ci_display_name || alert.ci_id || alert.id}</span>
        {alert.severity && (
          <span className={cn("shrink-0 rounded-full px-2 py-0.5 text-xs", SEVERITY_STYLE[alert.severity] || SEVERITY_STYLE.info)}>
            {alert.severity}
          </span>
        )}
      </div>
      <p className="mt-1 text-xs text-foreground">{alert.summary || rawText}</p>
      <p className="mt-0.5 text-xs text-muted-foreground">{formatSinceArrival(alert.stream_seen_at, nowMs)}</p>
      <button
        onClick={() => setShowRaw((v) => !v)}
        className="mt-1.5 flex items-center gap-1 text-xs text-muted-foreground hover:text-foreground"
      >
        <ChevronDown className={cn("h-3 w-3 transition-transform", showRaw && "rotate-180")} />
        Technical details ({alert.source})
      </button>
      {showRaw && (
        <div className="mt-1 space-y-1 rounded bg-secondary/60 p-1.5">
          <p className="text-[11px] text-muted-foreground">
            The exact, unprocessed message as sent by {SOURCE_LABEL[alert.source] || "the monitoring source"} —
            not meant to be read directly, kept here so the diagnosis above can be double-checked against
            the original signal.
          </p>
          <p className="truncate font-mono text-[11px] text-muted-foreground">{rawText}</p>
        </div>
      )}
      <div className="mt-2">
        {ticket ? (
          <button
            onClick={() => onOpenTicket(ticket)}
            className={cn("rounded-full px-2 py-0.5 text-xs hover:opacity-80", TICKET_STATUS_STYLE[ticket.status_normalized])}
            title="Open in Incident Workspace"
          >
            {TICKET_STATUS_LABEL[ticket.status_normalized]} — {ticket.external_id}
          </button>
        ) : (
          <Button size="sm" variant="outline" onClick={() => onDiagnose(alert)} disabled={busy}>
            Diagnose
          </Button>
        )}
      </div>
    </li>
  );
}

function AlertFeed({ alerts, totalReceived, connectionStatus, tickets, incident, refetchTickets, onOpenTicket }) {
  const [category, setCategory] = useState("");
  const [status, setStatus] = useState("");
  const [runningAll, setRunningAll] = useState(false);
  const [progress, setProgress] = useState(null);
  const nowMs = useClockTick();

  // linked_incident_id is only ever set by a real workflow run (_persist_ticket_snapshot in
  // main.py) — bulk-seeded historical backlog (db/init_db.py's populate_local_tickets_bulk)
  // deliberately leaves it null, since those rows were never actually run through the agent chain.
  // Excluding null-linked rows here matters: without it, every CI's several bulk-seeded historical
  // tickets made ticketByCi.has(ci_id) true for nearly every CI, which hid the Diagnose button and
  // made "Run all untriaged" think everything was already handled — alerts silently never got
  // diagnosed even though nothing this session had actually touched them.
  const ticketByCi = new Map();
  for (const t of tickets) if (t.linked_incident_id && !ticketByCi.has(t.cmdb_ci)) ticketByCi.set(t.cmdb_ci, t); // most-recent first (GET /tickets orders DESC)

  // Neither filter changes what "Run all untriaged" acts on — that's a bulk action over
  // everything currently loaded, not scoped to whatever's visible right now.
  const filtered = alerts
    .filter((a) => !category || a.category === category)
    .filter((a) => !status || (ticketByCi.get(a.ci_id)?.status_normalized || "untriaged") === status);
  const untriagedUniqueCis = [...new Map(alerts.filter((a) => !ticketByCi.has(a.ci_id)).map((a) => [a.ci_id, a])).values()];

  async function diagnose(alert) {
    await incident.triggerRun(alert.ci_id, workflowTypeForCategory(alert.category), false);
    refetchTickets();
  }

  async function runAllUntriaged() {
    setRunningAll(true);
    for (const [i, a] of untriagedUniqueCis.entries()) {
      setProgress({ current: i + 1, total: untriagedUniqueCis.length });
      await incident.triggerRun(a.ci_id, workflowTypeForCategory(a.category), false);
    }
    setProgress(null);
    setRunningAll(false);
    refetchTickets();
  }

  const busy = incident.loading || runningAll;

  return (
    <div className="min-w-0 flex-1 space-y-2">
      <p className="text-xs text-muted-foreground">
        Live alert feed — {totalReceived} received this session
        {totalReceived > alerts.length ? ` (showing the latest ${alerts.length})` : ""} ({connectionStatus}).
      </p>
      <Button size="sm" variant="outline" onClick={runAllUntriaged} disabled={busy || untriagedUniqueCis.length === 0}>
        {progress
          ? `Diagnosing ${progress.current} of ${progress.total}…`
          : untriagedUniqueCis.length === 0
            ? "All alerts diagnosed"
            : `Run all untriaged (${untriagedUniqueCis.length})`}
      </Button>
      <div className="flex flex-wrap items-center gap-x-4 gap-y-2">
        <FilterPills options={CATEGORY_FILTERS} value={category} onChange={setCategory} />
        <FilterPills options={STATUS_FILTERS} value={status} onChange={setStatus} />
      </div>
      <ul className="max-h-[600px] space-y-2 overflow-y-auto pr-1">
        {filtered.map((alert) => (
          <AlertItem
            key={alert.id}
            alert={alert}
            ticket={ticketByCi.get(alert.ci_id)}
            busy={busy}
            nowMs={nowMs}
            onDiagnose={diagnose}
            onOpenTicket={onOpenTicket}
          />
        ))}
        {filtered.length === 0 && (
          <li className="text-sm text-muted-foreground">
            {alerts.length === 0 ? "Waiting for alerts…" : "No alerts match this filter."}
          </li>
        )}
      </ul>
    </div>
  );
}

const PATCH_SEVERITY_STYLE = {
  critical: "bg-red-600/10 text-red-600",
  high: "bg-status-warning/10 text-status-warning",
  medium: "bg-secondary text-muted-foreground",
  low: "bg-secondary text-muted-foreground",
};
const PATCH_SEVERITY_RANK = { critical: 0, high: 1, medium: 2, low: 3 };

// The patch workflow's own entry point on Ops Board — mirrors what the alert feed already gives
// incident/performance: a real, live list of things a human could act on, not just a scenario
// fixture reachable through the admin-only Scenario Launcher. Sourced from GET /patches/pending
// (patch_inventory, ~150 seeded rows across ~40% of the CMDB — data_gen/patch_inventory.py),
// grouped by CI since one patch-workflow run already sweeps up every pending patch on that CI
// (enrichment.py's patch evidence gathering), the same "one action covers everything on this
// resource" pattern the alert feed uses for fault alerts.
function PendingPatches({ apiBase, token, incident, refetchTickets, tickets, onOpenTicket }) {
  const [patches, setPatches] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    let cancelled = false;
    fetch(`${apiBase}/patches/pending`, { headers: { Authorization: `Bearer ${token}` } })
      .then((res) => (res.ok ? res.json() : Promise.reject(new Error(`Request failed (${res.status})`))))
      .then((data) => !cancelled && setPatches(data.patches))
      .catch((err) => !cancelled && setError(err.message))
      .finally(() => !cancelled && setLoading(false));
    return () => {
      cancelled = true;
    };
  }, [apiBase, token]);

  // Same real-vs-historical distinction as AlertFeed's ticketByCi above — a CI's bulk-seeded patch
  // backlog (linked_incident_id null) must not hide the "Start patch workflow" button for patches
  // nothing this session has actually run yet.
  const ticketByCi = new Map();
  for (const t of tickets) if (t.workflow_type === "patch" && t.linked_incident_id && !ticketByCi.has(t.cmdb_ci)) ticketByCi.set(t.cmdb_ci, t);

  const byCi = new Map();
  for (const p of patches) {
    const group = byCi.get(p.ci_id) || { ci_id: p.ci_id, ci_display_name: p.ci_display_name, items: [] };
    group.items.push(p);
    byCi.set(p.ci_id, group);
  }
  const groups = [...byCi.values()].sort((a, b) => {
    const worst = (g) => Math.min(...g.items.map((p) => PATCH_SEVERITY_RANK[p.severity] ?? 9));
    return worst(a) - worst(b);
  });

  async function startPatchWorkflow(ciId) {
    await incident.triggerRun(ciId, "patch", false);
    refetchTickets();
  }

  if (loading) return <p className="text-xs text-muted-foreground">Loading pending patches…</p>;
  if (error) return <p className="text-xs text-red-500">{error}</p>;

  return (
    <div className="space-y-2">
      <p className="text-xs text-muted-foreground">
        {patches.length} pending patch{patches.length === 1 ? "" : "es"} across {groups.length} configuration item
        {groups.length === 1 ? "" : "s"} — starting a workflow for a CI schedules everything pending on it, not just one patch.
      </p>
      <ul className="max-h-[360px] space-y-2 overflow-y-auto pr-1">
        {groups.map((g) => {
          const worst = g.items.reduce((a, b) => (PATCH_SEVERITY_RANK[b.severity] < PATCH_SEVERITY_RANK[a.severity] ? b : a));
          const ticket = ticketByCi.get(g.ci_id);
          return (
            <li key={g.ci_id} className="rounded-md border border-border p-3 text-sm">
              <div className="flex items-center justify-between gap-2">
                <span className="font-medium">{g.ci_display_name || g.ci_id}</span>
                <span className={cn("shrink-0 rounded-full px-2 py-0.5 text-xs", PATCH_SEVERITY_STYLE[worst.severity])}>
                  {worst.severity}
                </span>
              </div>
              <p className="mt-1 text-xs text-foreground">
                {g.items.length} patch{g.items.length === 1 ? "" : "es"} pending — {g.items.map((p) => p.title).join("; ")}
              </p>
              <p className="mt-0.5 text-xs text-muted-foreground">
                Tightest SLA: {Math.min(...g.items.map((p) => p.sla_days))} days
                {g.items.some((p) => p.cve_ids.length > 0) && ` · ${g.items.flatMap((p) => p.cve_ids).length} CVE(s) named`}
              </p>
              <div className="mt-2">
                {ticket ? (
                  <button
                    onClick={() => onOpenTicket(ticket)}
                    className={cn("rounded-full px-2 py-0.5 text-xs hover:opacity-80", TICKET_STATUS_STYLE[ticket.status_normalized])}
                    title="Open in Incident Workspace"
                  >
                    {TICKET_STATUS_LABEL[ticket.status_normalized]} — {ticket.external_id}
                  </button>
                ) : (
                  <Button size="sm" variant="outline" onClick={() => startPatchWorkflow(g.ci_id)} disabled={incident.loading}>
                    Start patch workflow
                  </Button>
                )}
              </div>
            </li>
          );
        })}
        {groups.length === 0 && <li className="text-sm text-muted-foreground">No pending patches.</li>}
      </ul>
    </div>
  );
}

// Ops Board tab: live alert feed, each alert showing its own triage status inline. The old separate
// "correlated candidates" panel was folded into the alert feed itself — diagnosing a CI already
// covers every alert on it, so a per-alert status pill gives the same outcome without a second,
// harder-to-follow grouped view. Full ticket history lives in its own "Tickets" tab (Tickets.jsx),
// framed as the ServiceNow/Jira system of record. Image intake (PRD §7) moved into the floating
// ChatWidget alongside voice, so the assistant carries every accessibility modality in one place.
// Pending Patches gives the patch workflow the same kind of real, live entry point the alert feed
// already gives incident/performance — previously only reachable through the admin Scenario Launcher.
export default function OpsBoard({ apiBase, token, alerts, totalReceived, connectionStatus, incident, tickets, refetchTickets, onOpenTicket }) {
  return (
    <div className="space-y-6">
      <AlertFeed
        alerts={alerts}
        totalReceived={totalReceived}
        connectionStatus={connectionStatus}
        tickets={tickets}
        incident={incident}
        refetchTickets={refetchTickets}
        onOpenTicket={onOpenTicket}
      />
      <div>
        <h3 className="mb-2 text-sm font-semibold text-foreground">Pending Patches</h3>
        <PendingPatches
          apiBase={apiBase}
          token={token}
          incident={incident}
          tickets={tickets}
          refetchTickets={refetchTickets}
          onOpenTicket={onOpenTicket}
        />
      </div>
    </div>
  );
}
