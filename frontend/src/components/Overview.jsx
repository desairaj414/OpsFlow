"use client";

import { useEffect, useState } from "react";
import { Activity, CheckCircle2, UserCheck, AlertTriangle, PauseCircle, ShieldAlert, Wrench, Timer } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { apiFetch } from "@/lib/api.js";

// Real elapsed seconds -> "12.4s" / "1m 03s" — these are genuinely fast (a full agent chain runs
// in seconds), which is itself the honest point: shown as a real measured number, not compared
// against an invented "manual baseline" figure (see backend/main.py's timing comment).
function formatDuration(seconds) {
  if (seconds === null || seconds === undefined) return "—";
  if (seconds < 60) return `${seconds.toFixed(1)}s`;
  const m = Math.floor(seconds / 60);
  const s = Math.round(seconds % 60);
  return `${m}m ${s.toString().padStart(2, "0")}s`;
}

// --- Stat pair (two related numbers side by side, e.g. two durations) -----
function StatPair({ items }) {
  return (
    <div className="grid w-full grid-cols-2 gap-3">
      {items.map((item) => (
        <div key={item.label} className="rounded-md border border-border p-3 text-center">
          <p className="text-xl font-semibold text-foreground">{item.value}</p>
          <p className="mt-1 text-xs text-muted-foreground">{item.label}</p>
          {item.sublabel && <p className="text-[10px] text-muted-foreground">{item.sublabel}</p>}
        </div>
      ))}
    </div>
  );
}

// --- KPI tile -------------------------------------------------------------
function KpiTile({ icon: Icon, label, value, chipClassName }) {
  return (
    <Card>
      <CardContent className="flex items-center gap-3 p-4">
        <div className={`flex h-10 w-10 shrink-0 items-center justify-center rounded-full ${chipClassName}`}>
          <Icon className="h-5 w-5" />
        </div>
        <div className="min-w-0">
          <p className="text-xs text-muted-foreground">{label}</p>
          <p className="text-xl font-semibold text-foreground">{value}</p>
        </div>
      </CardContent>
    </Card>
  );
}

// --- Bar comparison (2 categories, thin rounded marks, direct labels) -----
// dataviz skill: red/green failed the colorblind-separation check for this pair (deutan ΔE 5.0),
// so approvals/rejections use the same teal/amber "positive vs needs-attention" pairing as the
// drift donut below — one consistent 2-color status language across the whole dashboard.
function BarComparison({ items, max }) {
  return (
    <div className="space-y-3">
      {items.map((item) => (
        <div key={item.label}>
          <div className="mb-1 flex items-center justify-between text-xs">
            <span className="font-medium text-foreground">{item.label}</span>
            <span className="text-muted-foreground">{item.value}</span>
          </div>
          <svg width="100%" height="14" viewBox="0 0 200 14" preserveAspectRatio="none">
            <rect x="0" y="4" width="200" height="6" rx="3" className="fill-secondary" />
            <rect
              x="0"
              y="4"
              width={max > 0 ? Math.max((item.value / max) * 200, item.value > 0 ? 6 : 0) : 0}
              height="6"
              rx="3"
              fill={item.color}
            />
          </svg>
        </div>
      ))}
    </div>
  );
}

// --- Radial gauge (single sequential value, 0-100%) ------------------------
function RadialGauge({ percent, label }) {
  const r = 46;
  const circumference = 2 * Math.PI * r;
  const filled = (percent / 100) * circumference;
  return (
    <div className="flex flex-col items-center">
      <svg width="120" height="120" viewBox="0 0 120 120">
        <title>{`${label}: ${percent}%`}</title>
        <circle cx="60" cy="60" r={r} strokeWidth="10" className="stroke-secondary" fill="none" />
        <circle
          cx="60"
          cy="60"
          r={r}
          strokeWidth="10"
          fill="none"
          stroke="hsl(var(--primary))"
          strokeLinecap="round"
          strokeDasharray={`${filled} ${circumference - filled}`}
          transform="rotate(-90 60 60)"
        />
        <text x="60" y="66" textAnchor="middle" className="fill-foreground text-2xl font-semibold" style={{ fontSize: 22 }}>
          {percent}%
        </text>
      </svg>
      <p className="mt-1 text-center text-xs text-muted-foreground">{label}</p>
    </div>
  );
}

// --- Donut (2-part split, identity labeled — never color alone) ------------
function Donut({ segments, centerLabel, centerValue }) {
  const r = 46;
  const circumference = 2 * Math.PI * r;
  const gap = 3;
  let offset = 0;
  const total = segments.reduce((s, seg) => s + seg.value, 0);
  return (
    <div className="flex flex-col items-center">
      <svg width="120" height="120" viewBox="0 0 120 120">
        <title>{segments.map((s) => `${s.label}: ${s.value}`).join(", ")}</title>
        <circle cx="60" cy="60" r={r} strokeWidth="14" className="stroke-secondary" fill="none" />
        {segments.map((seg) => {
          const len = total > 0 ? (seg.value / total) * circumference : 0;
          const dash = Math.max(len - gap, 0);
          const el = (
            <circle
              key={seg.label}
              cx="60"
              cy="60"
              r={r}
              strokeWidth="14"
              fill="none"
              stroke={seg.color}
              strokeLinecap="round"
              strokeDasharray={`${dash} ${circumference - dash}`}
              strokeDashoffset={-offset}
              transform="rotate(-90 60 60)"
            />
          );
          offset += len;
          return el;
        })}
        <text x="60" y="56" textAnchor="middle" className="fill-foreground font-semibold" style={{ fontSize: 20 }}>
          {centerValue}
        </text>
        <text x="60" y="72" textAnchor="middle" className="fill-muted-foreground" style={{ fontSize: 10 }}>
          {centerLabel}
        </text>
      </svg>
      <div className="mt-2 flex flex-wrap justify-center gap-3">
        {segments.map((seg) => (
          <span key={seg.label} className="flex items-center gap-1.5 text-xs text-muted-foreground">
            <span className="h-2 w-2 rounded-full" style={{ backgroundColor: seg.color }} />
            {seg.label} ({seg.value})
          </span>
        ))}
      </div>
    </div>
  );
}

function ChartCard({ title, description, children }) {
  return (
    <Card>
      <CardHeader className="pb-2">
        <CardTitle className="text-sm font-semibold">{title}</CardTitle>
        <p className="text-xs text-muted-foreground">{description}</p>
      </CardHeader>
      <CardContent className="flex items-center justify-center pt-2">{children}</CardContent>
    </Card>
  );
}

// Overview — the default landing tab, and now the sole home for /metrics/summary's numbers (the
// standalone Metrics & Eval tab was folded in here and removed). /cmdb/drift, /autonomy-ladder, and
// /audit-log are all endpoints that already existed for their own tabs (Drift Queue, Autonomy
// Ladder, the admin Audit Log panel) — this gives the operator the headline view first, instead of
// landing cold on a raw alert feed.
export default function Overview({ apiBase, token }) {
  const [metrics, setMetrics] = useState(null);
  const [drift, setDrift] = useState(null);
  const [ladder, setLadder] = useState(null);
  const [audit, setAudit] = useState(null);
  const [error, setError] = useState("");

  useEffect(() => {
    let cancelled = false;
    Promise.all([
      apiFetch(apiBase, "/metrics/summary", { token }).then((r) => (r.ok ? r.json() : Promise.reject(r.status))),
      apiFetch(apiBase, "/cmdb/drift", { token }).then((r) => (r.ok ? r.json() : Promise.reject(r.status))),
      apiFetch(apiBase, "/autonomy-ladder", { token }).then((r) => (r.ok ? r.json() : Promise.reject(r.status))),
      apiFetch(apiBase, "/audit-log?limit=6", { token }).then((r) => (r.ok ? r.json() : { entries: null })),
    ])
      .then(([m, d, l, a]) => {
        if (cancelled) return;
        setMetrics(m);
        setDrift(d);
        setLadder(l);
        setAudit(a.entries);
      })
      .catch((status) => {
        if (!cancelled) setError(typeof status === "number" ? `Request failed (${status})` : "Failed to load overview data.");
      });
    return () => {
      cancelled = true;
    };
  }, [apiBase, token]);

  if (error) return <p className="text-sm text-red-500">{error}</p>;
  if (!metrics || !drift || !ladder) return <p className="text-sm text-muted-foreground">Loading overview…</p>;

  const driftAccurate = drift.total_cis - drift.drifted_count;
  const topRunbooks = [...ladder.runbooks]
    .sort((a, b) => b.verified_resolution_count - a.verified_resolution_count)
    .slice(0, 5);

  return (
    <div className="space-y-4">
      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-4">
        <KpiTile
          icon={Activity}
          label="Workflow runs this session"
          value={metrics.total_workflow_runs_this_session}
          chipClassName="bg-accent-soft text-primary"
        />
        <KpiTile
          icon={CheckCircle2}
          label="Completed"
          value={metrics.completed_runs}
          chipClassName="bg-status-good/10 text-status-good"
        />
        <KpiTile
          icon={UserCheck}
          label="Human approvals"
          value={metrics.human_approvals}
          chipClassName="bg-accent-soft text-primary"
        />
        <KpiTile
          icon={AlertTriangle}
          label="CMDB drift rate"
          value={`${Math.round(drift.drift_rate * 100)}%`}
          chipClassName="bg-status-warning/10 text-status-warning"
        />
        <KpiTile
          icon={PauseCircle}
          label="Stopped before completion"
          value={metrics.stopped_before_completion}
          chipClassName="bg-status-warning/10 text-status-warning"
        />
        <KpiTile
          icon={ShieldAlert}
          label="Negative-KB entries seeded"
          value={metrics.negative_kb_entries_seeded}
          chipClassName="bg-accent-soft text-primary"
        />
        <KpiTile
          icon={Wrench}
          label="Manual steps avoided"
          value={metrics.manual_steps_avoided}
          chipClassName="bg-status-good/10 text-status-good"
        />
      </div>

      <div className="grid grid-cols-1 gap-3 lg:grid-cols-3">
        <ChartCard title="Human decisions" description="Approvals vs. rejections this session.">
          <div className="w-full max-w-xs">
            <BarComparison
              max={Math.max(metrics.human_approvals, metrics.human_rejections, 1)}
              items={[
                { label: "Approved", value: metrics.human_approvals, color: "hsl(var(--primary))" },
                { label: "Rejected", value: metrics.human_rejections, color: "hsl(var(--status-warning))" },
              ]}
            />
          </div>
        </ChartCard>
        <ChartCard
          title="Manual triage avoided"
          description="Raw alerts collapsed into candidate incidents — fewer things a human had to look at one by one."
        >
          <RadialGauge percent={Math.round(metrics.correlation_noise_reduction_ratio * 100)} label="alerts collapsed" />
        </ChartCard>
        <ChartCard title="CMDB accuracy" description="Recorded configuration vs. verified ground truth.">
          <Donut
            centerValue={drift.total_cis}
            centerLabel="CIs tracked"
            segments={[
              { label: "Accurate", value: driftAccurate, color: "hsl(var(--primary))" },
              { label: "Drifted", value: drift.drifted_count, color: "hsl(var(--status-warning))" },
            ]}
          />
        </ChartCard>
      </div>

      <div className="grid grid-cols-1 gap-3 lg:grid-cols-3">
        <ChartCard
          title="Incident resolution time"
          description="Elapsed time from signal to plan drafted, and from signal to verified resolution."
        >
          <StatPair
            items={[
              { label: "Signal → plan drafted", value: formatDuration(metrics.avg_signal_to_plan_seconds), sublabel: `${metrics.incidents_with_plan_timing} incidents` },
              { label: "Signal → verified resolution", value: formatDuration(metrics.avg_signal_to_verified_resolution_seconds), sublabel: `${metrics.incidents_with_resolution_timing} incidents` },
            ]}
          />
        </ChartCard>
        <ChartCard
          title="Human satisfaction (proxy)"
          description="Approval rate — the share of AI-proposed plans a human accepted rather than rejected."
        >
          {metrics.approval_rate_satisfaction_proxy === null ? (
            <p className="text-xs text-muted-foreground">No approve/reject decisions yet this session.</p>
          ) : (
            <RadialGauge percent={Math.round(metrics.approval_rate_satisfaction_proxy * 100)} label="plans approved" />
          )}
        </ChartCard>
        <ChartCard title="Toil removed" description="Runbook steps the agent chain executed on its own this session — each one a manual action avoided.">
          <div className="flex flex-col items-center justify-center">
            <p className="text-4xl font-semibold text-foreground">{metrics.manual_steps_avoided}</p>
            <p className="mt-1 text-xs text-muted-foreground">runbook steps auto-executed</p>
          </div>
        </ChartCard>
      </div>

      <div className="grid grid-cols-1 gap-3 lg:grid-cols-2">
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-semibold">Recent activity</CardTitle>
            <p className="text-xs text-muted-foreground">Latest entries from the append-only audit trail.</p>
          </CardHeader>
          <CardContent className="space-y-1.5">
            {audit === null && (
              <p className="text-xs text-muted-foreground">Sign in as Approver or Admin to see the audit trail here.</p>
            )}
            {audit?.map((e) => (
              <div key={e.id} className="flex items-center justify-between gap-2 rounded-md border border-border px-3 py-2 text-xs">
                <span className="font-medium text-foreground">{e.action}</span>
                <span className="truncate text-muted-foreground">{e.actor}</span>
                <span className="shrink-0 text-muted-foreground">{new Date(e.timestamp).toLocaleTimeString()}</span>
              </div>
            ))}
            {audit?.length === 0 && <p className="text-xs text-muted-foreground">No actions recorded yet this session.</p>}
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-semibold">Most-trusted runbooks</CardTitle>
            <p className="text-xs text-muted-foreground">Ranked by verified resolutions on the autonomy ladder.</p>
          </CardHeader>
          <CardContent className="space-y-1.5">
            {topRunbooks.map((rb) => (
              <div key={rb.runbook_id} className="flex items-center justify-between gap-2 rounded-md border border-border px-3 py-2 text-xs">
                <span className="font-mono font-medium text-foreground">{rb.runbook_id}</span>
                <span className="text-muted-foreground">{rb.class}</span>
                <span className="text-muted-foreground">{rb.current_tier}</span>
                <span className="shrink-0 font-medium text-primary">{rb.verified_resolution_count} verified</span>
              </div>
            ))}
            {topRunbooks.length === 0 && <p className="text-xs text-muted-foreground">No runbooks on the ladder yet.</p>}
          </CardContent>
        </Card>
      </div>

      <p className="rounded-md border border-dashed border-border p-3 text-xs text-muted-foreground">
        Every number above reflects live activity from real runs this session.
      </p>
    </div>
  );
}
