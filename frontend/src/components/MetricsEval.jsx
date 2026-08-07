"use client";

import { useEffect, useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

function StatCard({ label, value }) {
  return (
    <Card>
      <CardHeader className="pb-2">
        <CardTitle className="text-xs font-normal text-muted-foreground">{label}</CardTitle>
      </CardHeader>
      <CardContent>
        <p className="text-2xl font-semibold">{value}</p>
      </CardContent>
    </Card>
  );
}

// Real operational aggregates from this session's actual runs (audit_log, correlation engine) —
// NOT a Phase 5 scenario-eval report. Phase 5 (Scenario Library, Eval & Hardening) hasn't started,
// so there's no accuracy/pass-rate metric here; shown honestly rather than faked.
export default function MetricsEval({ apiBase, token }) {
  const [data, setData] = useState(null);
  const [error, setError] = useState("");

  useEffect(() => {
    let cancelled = false;
    fetch(`${apiBase}/metrics/summary`, { headers: { Authorization: `Bearer ${token}` } })
      .then((res) => {
        if (!res.ok) throw new Error(`Request failed (${res.status})`);
        return res.json();
      })
      .then((json) => {
        if (!cancelled) setData(json);
      })
      .catch((err) => {
        if (!cancelled) setError(err.message);
      });
    return () => {
      cancelled = true;
    };
  }, [apiBase, token]);

  if (error) return <p className="text-sm text-red-500">{error}</p>;
  if (!data) return <p className="text-sm text-muted-foreground">Loading…</p>;

  return (
    <div className="space-y-4">
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-3">
        <StatCard label="Workflow runs this session" value={data.total_workflow_runs_this_session} />
        <StatCard label="Completed" value={data.completed_runs} />
        <StatCard label="Stopped before completion" value={data.stopped_before_completion} />
        <StatCard label="Human approvals" value={data.human_approvals} />
        <StatCard label="Human rejections" value={data.human_rejections} />
        <StatCard label="Negative-KB entries seeded" value={data.negative_kb_entries_seeded} />
        <StatCard label="Correlation noise reduction" value={`${Math.round(data.correlation_noise_reduction_ratio * 100)}%`} />
      </div>
      <p className="rounded-md border border-dashed border-border p-3 text-xs text-muted-foreground">
        Scenario eval status: {data.scenario_eval_status}. These are live operational counters from
        real runs this session, not a scenario pass/fail accuracy report — that requires the
        Scenario Library (Phase 5), not yet built.
      </p>
    </div>
  );
}
