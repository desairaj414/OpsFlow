"use client";

import { useEffect, useState } from "react";
import { Button } from "@/components/ui/button";

// Scenario Launcher (PRD Phase 5 scenario library): lists the named scenarios seeded into the
// `scenarios` table (data/scenarios/*.json) and launches one through the exact same POST
// /workflows/run path the golden-path bar uses — this is not a separate simulated path.
export default function ScenarioLauncherPanel({ apiBase, token, incident }) {
  const [scenarios, setScenarios] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [launchingId, setLaunchingId] = useState(null);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const res = await fetch(`${apiBase}/scenarios`, { headers: { Authorization: `Bearer ${token}` } });
        if (!res.ok) throw new Error(`Request failed (${res.status})`);
        const data = await res.json();
        if (!cancelled) setScenarios(data.scenarios);
      } catch (err) {
        if (!cancelled) setError(err.message);
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [apiBase, token]);

  async function launch(scenario) {
    setLaunchingId(scenario.id);
    await incident.triggerRun(scenario.ci_id, scenario.workflow_type, scenario.auto_approve);
    setLaunchingId(null);
  }

  if (loading) return <p className="text-xs text-muted-foreground">Loading scenarios…</p>;
  if (error) return <p className="text-xs text-red-500">{error}</p>;

  return (
    <div className="space-y-2">
      <p className="text-xs text-muted-foreground">
        {scenarios.length} named scenario{scenarios.length === 1 ? "" : "s"} from the scenario
        library — launching one runs the full agent chain end to end.
      </p>
      {scenarios.map((s) => (
        <div key={s.id} className="rounded-md border border-border p-2 text-xs">
          <div className="flex items-center justify-between gap-2">
            <span className="font-medium">{s.id}</span>
            <span className="text-muted-foreground">
              {s.workflow_type}
              {s.is_edge_case ? " · edge case" : ""}
            </span>
          </div>
          <p className="mt-1 text-muted-foreground">{s.name}</p>
          <Button
            size="sm"
            className="mt-2 w-full"
            onClick={() => launch(s)}
            disabled={launchingId === s.id || incident.loading}
          >
            {launchingId === s.id ? "Launching…" : `Launch on ${s.ci_id}`}
          </Button>
        </div>
      ))}
      {scenarios.length === 0 && <p className="text-xs text-muted-foreground">No scenarios seeded yet.</p>}
    </div>
  );
}
