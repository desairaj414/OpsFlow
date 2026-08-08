"use client";

import { useState } from "react";
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

// Relative-or-date, whichever a human would actually reach for — "3h ago" close in, an actual date
// once it's old enough that "14d ago" stops being useful at a glance.
function formatWhen(iso) {
  if (!iso) return "";
  const date = new Date(iso);
  const diffMs = Date.now() - date.getTime();
  const diffHours = diffMs / 36e5;
  if (diffHours < 1) return "just now";
  if (diffHours < 24) return `${Math.round(diffHours)}h ago`;
  const diffDays = Math.round(diffHours / 24);
  if (diffDays <= 14) return `${diffDays}d ago`;
  return date.toLocaleDateString(undefined, { year: "numeric", month: "short", day: "numeric" });
}

// One alert, PLUS the triage status derived from it — the merged replacement for the old separate
// "correlated candidates" panel. Diagnosing one CI already sweeps up every fault alert on that CI
// (workflows/run's own scope, see supervisor.py), so a per-alert ticket-status pill gives the same
// practical outcome clustering did (one action handles every alert on that resource) without a
// second panel showing the same alerts grouped a different way — the old cluster view had grown
// low-value once topology-based correlation was fixed to stop over-merging unrelated CIs (see
// state-progress.md's CMDB relationship fix).
function AlertItem({ alert, ticket, busy, onDiagnose, onOpenTicket }) {
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
      <p className="mt-0.5 text-xs text-muted-foreground">{formatWhen(alert.received_at)}</p>
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

function AlertFeed({ alerts, connectionStatus, tickets, incident, refetchTickets, onOpenTicket }) {
  const [category, setCategory] = useState("");
  const [status, setStatus] = useState("");
  const [runningAll, setRunningAll] = useState(false);
  const [progress, setProgress] = useState(null);

  const ticketByCi = new Map();
  for (const t of tickets) if (!ticketByCi.has(t.cmdb_ci)) ticketByCi.set(t.cmdb_ci, t); // most-recent first (GET /tickets orders DESC)

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
        Live alert feed — {alerts.length} received this session ({connectionStatus}).
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

// Ops Board tab: live alert feed, each alert showing its own triage status inline. The old separate
// "correlated candidates" panel was folded into the alert feed itself — diagnosing a CI already
// covers every alert on it, so a per-alert status pill gives the same outcome without a second,
// harder-to-follow grouped view. Full ticket history lives in its own "Tickets" tab (Tickets.jsx),
// framed as the ServiceNow/Jira system of record. Image intake (PRD §7) moved into the floating
// ChatWidget alongside voice, so the assistant carries every accessibility modality in one place.
export default function OpsBoard({ apiBase, token, alerts, connectionStatus, incident, tickets, refetchTickets, onOpenTicket }) {
  return (
    <div className="space-y-4">
      <AlertFeed
        alerts={alerts}
        connectionStatus={connectionStatus}
        tickets={tickets}
        incident={incident}
        refetchTickets={refetchTickets}
        onOpenTicket={onOpenTicket}
      />
    </div>
  );
}
