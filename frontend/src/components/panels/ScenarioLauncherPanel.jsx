"use client";

import { useEffect, useState } from "react";
import { Button } from "@/components/ui/button";
import { apiFetch } from "@/lib/api.js";
import { getProviderMode } from "@/lib/providerMode.js";

// Reveals the one pregenerated PII-scrubbing demo fixture (backend's GET /demo/pii-sample) — a
// real scrubbed MaintenanceSignal from the unmodified vision-intake pipeline (scripts/
// pregenerate_demo_outputs.py), proving guardrails/scrubber.py actually redacts a name/email
// without needing a live model call. Shown only in Instant Demo mode, where nothing else in this
// panel's neighboring chat/voice/image surfaces can demonstrate that live.
function PiiScrubbingDemoCard({ apiBase, token }) {
  const [sample, setSample] = useState(null);
  const [error, setError] = useState("");

  useEffect(() => {
    let cancelled = false;
    apiFetch(apiBase, "/demo/pii-sample", { token })
      .then((res) => (res.ok ? res.json() : Promise.reject(res.status)))
      .then((data) => !cancelled && setSample(data))
      .catch(() => !cancelled && setError("Not generated yet."));
    return () => {
      cancelled = true;
    };
  }, [apiBase, token]);

  if (error) return null;
  if (!sample) return <p className="text-xs text-muted-foreground">Loading PII-scrubbing sample…</p>;

  return (
    <div className="rounded-md border border-border p-2 text-xs">
      <p className="font-medium">Privacy scrubber, proven — not just claimed</p>
      <p className="mt-1 text-muted-foreground">
        A screenshot naming a person and an email address, run through the real, unmodified vision-intake
        pipeline. The name/email were redacted before this text was ever shown here:
      </p>
      <p className="mt-1.5 whitespace-pre-wrap rounded bg-secondary p-1.5 font-mono">{sample.extracted_text}</p>
    </div>
  );
}

// Scenario Launcher (PRD Phase 5 scenario library): lists the named scenarios seeded into the
// `scenarios` table (data/scenarios/*.json) and launches one through the exact same POST
// /workflows/run path the golden-path bar uses — this is not a separate simulated path.
export default function ScenarioLauncherPanel({ apiBase, token, incident }) {
  const [scenarios, setScenarios] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [launchingId, setLaunchingId] = useState(null);
  const [mode] = useState(getProviderMode);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const res = await apiFetch(apiBase, "/scenarios", { token });
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
      {mode.mode === "instant_demo" && <PiiScrubbingDemoCard apiBase={apiBase} token={token} />}
    </div>
  );
}
