"use client";

import { useEffect, useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { cn } from "@/lib/utils";
import { AGENT_DISPLAY_NAMES, AGENT_PIPELINE_ORDER, summarizeResult } from "@/lib/agentSummary";
import { apiFetch } from "@/lib/api.js";

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

const SYSTEM_LABEL = { itsm: "ServiceNow", tracker: "Jira" };

const SYSTEM_FILTERS = [
  { key: "", label: "All systems" },
  { key: "itsm", label: "ServiceNow" },
  { key: "tracker", label: "Jira" },
];

const WORKFLOW_TYPE_FILTERS = [
  { key: "", label: "All types" },
  { key: "incident", label: "Incident" },
  { key: "patch", label: "Patch" },
  { key: "performance", label: "Performance" },
];

// Same pill-filter pattern used everywhere else (Knowledge Base's doc-type filter, Ops Board's
// category filter) — kept local rather than shared/imported, matching how small this component is.
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

function formatWhen(iso) {
  if (!iso) return "";
  const date = new Date(iso);
  const diffMs = Date.now() - date.getTime();
  const diffSec = diffMs / 1000;
  if (diffSec < 60) return "just now";
  const diffHours = diffMs / 36e5;
  if (diffHours < 1) return `${Math.round(diffSec / 60)}m ago`;
  if (diffHours < 24) return `${Math.round(diffHours)}h ago`;
  const diffDays = Math.round(diffHours / 24);
  if (diffDays <= 14) return `${diffDays}d ago`;
  return date.toLocaleDateString(undefined, { year: "numeric", month: "short", day: "numeric" });
}

function TicketDetail({ apiBase, token, ticketId }) {
  const [detail, setDetail] = useState(null);
  const [error, setError] = useState("");

  useEffect(() => {
    let cancelled = false;
    apiFetch(apiBase, `/tickets/${ticketId}`, { token })
      .then((res) => (res.ok ? res.json() : Promise.reject(new Error(`Request failed (${res.status})`))))
      .then((json) => !cancelled && setDetail(json))
      .catch((err) => !cancelled && setError(err.message));
    return () => {
      cancelled = true;
    };
  }, [apiBase, token, ticketId]);

  if (error) return <p className="text-xs text-red-500">{error}</p>;
  if (!detail) return <p className="text-xs text-muted-foreground">Loading…</p>;

  const trace = detail.trace_snapshot?.trace || [];
  const byAgent = new Map(trace.map((entry) => [entry.agent_name, entry]));

  return (
    <div className="mt-2 space-y-1.5 border-t border-border pt-2">
      {AGENT_PIPELINE_ORDER.filter((name) => byAgent.has(name)).map((name) => {
        const entry = byAgent.get(name);
        return (
          <div key={name} className="text-xs">
            <span className="font-medium text-foreground">{AGENT_DISPLAY_NAMES[name]}</span>
            {entry.model_used && <span className="text-muted-foreground"> ({entry.model_used})</span>}
            <p className="text-muted-foreground">{summarizeResult(entry)}</p>
          </div>
        );
      })}
      {trace.length === 0 && <p className="text-xs text-muted-foreground">No agent trace recorded for this run.</p>}
    </div>
  );
}

// Tickets tab: the ServiceNow/Jira system-of-record view, browsed and "pulled" independently of
// the Ops Board triage flow. No real ServiceNow/Jira instance is connected in this build
// (integration_settings' URLs are inert, decisions-log.md) — "Pull latest" honestly re-reads the
// same local `local_tickets` record every real diagnosis already writes to (POST /tickets/sync),
// and stamps `last_synced_at` so this reads like a genuine periodic sync status, not a live feed
// pretending to reach a real instance.
export default function Tickets({ apiBase, token, tickets, refetchTickets, onOpenTicket }) {
  const [expandedId, setExpandedId] = useState(null);
  const [workflowType, setWorkflowType] = useState("");
  const [system, setSystem] = useState("");
  const [search, setSearch] = useState("");
  const [lastSyncedAt, setLastSyncedAt] = useState(null);
  const [syncing, setSyncing] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    let cancelled = false;
    apiFetch(apiBase, "/config/integrations", { token })
      .then((res) => (res.ok ? res.json() : null))
      .then((data) => !cancelled && data && setLastSyncedAt(data.last_synced_at))
      .catch(() => {});
    return () => {
      cancelled = true;
    };
  }, [apiBase, token]);

  async function pullLatest() {
    setSyncing(true);
    setError("");
    try {
      const res = await apiFetch(apiBase, "/tickets/sync", { method: "POST", token });
      if (!res.ok) throw new Error(`Request failed (${res.status})`);
      const data = await res.json();
      setLastSyncedAt(data.synced_at);
      await refetchTickets();
    } catch (err) {
      setError(err.message);
    } finally {
      setSyncing(false);
    }
  }

  const searchTerm = search.trim().toLowerCase();
  const filtered = tickets.filter(
    (t) =>
      (!workflowType || t.workflow_type === workflowType) &&
      (!system || t.system === system) &&
      (!searchTerm ||
        t.external_id?.toLowerCase().includes(searchTerm) ||
        t.linked_incident_id?.toLowerCase().includes(searchTerm) ||
        t.cmdb_ci?.toLowerCase().includes(searchTerm))
  );

  return (
    <div className="space-y-3">
      <div className="rounded-md border border-dashed border-border p-3 text-xs text-muted-foreground">
        No external ServiceNow/Jira instance is connected in this environment. &quot;Pull
        latest&quot; re-syncs this workspace&apos;s own records in the same shape a live periodic
        sync would return.
      </div>
      <div className="flex flex-wrap items-center gap-3">
        <Button size="sm" onClick={pullLatest} disabled={syncing}>
          {syncing ? "Pulling…" : "Pull latest"}
        </Button>
        <span className="text-xs text-muted-foreground">Last synced: {lastSyncedAt ? formatWhen(lastSyncedAt) : "never"}</span>
      </div>
      {error && <p className="text-sm text-red-500">{error}</p>}
      <Input
        placeholder="Search by ticket or incident number…"
        value={search}
        onChange={(e) => setSearch(e.target.value)}
        className="max-w-sm"
      />
      <div className="flex flex-wrap items-center gap-x-4 gap-y-2">
        <FilterPills options={SYSTEM_FILTERS} value={system} onChange={setSystem} />
        <FilterPills options={WORKFLOW_TYPE_FILTERS} value={workflowType} onChange={setWorkflowType} />
      </div>
      <ul className="space-y-2">
        {filtered.map((t) => (
          <li key={t.id} className="rounded-md border border-border p-3 text-sm">
            <div className="flex items-start justify-between gap-2">
              <button className="min-w-0 flex-1 text-left" onClick={() => setExpandedId(expandedId === t.id ? null : t.id)}>
                <div className="flex items-center justify-between gap-2">
                  <span className="font-medium">{t.external_id}</span>
                  <span className={cn("shrink-0 rounded-full px-2 py-0.5 text-xs", TICKET_STATUS_STYLE[t.status_normalized])}>
                    {TICKET_STATUS_LABEL[t.status_normalized]}
                  </span>
                </div>
                <p className="mt-1 truncate text-xs text-muted-foreground">{t.summary}</p>
                <p className="mt-0.5 text-xs text-muted-foreground">
                  {SYSTEM_LABEL[t.system] || t.system} · {t.cmdb_ci} · {t.workflow_type} · {formatWhen(t.created_at)}
                </p>
              </button>
              <Button size="sm" variant="outline" className="shrink-0" onClick={() => onOpenTicket(t)}>
                Open
              </Button>
            </div>
            {expandedId === t.id && <TicketDetail apiBase={apiBase} token={token} ticketId={t.id} />}
          </li>
        ))}
        {filtered.length === 0 && (
          <li className="text-sm text-muted-foreground">
            {tickets.length === 0 ? "Nothing synced yet this session." : "No tickets match this filter."}
          </li>
        )}
      </ul>
    </div>
  );
}
