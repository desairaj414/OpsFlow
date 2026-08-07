"use client";

import { useState } from "react";
import Sidebar from "@/components/Sidebar.jsx";
import OpsBoard from "@/components/OpsBoard.jsx";
import AgentTrace from "@/components/AgentTrace.jsx";
import IncidentWorkspace from "@/components/IncidentWorkspace.jsx";
import ApprovalQueue from "@/components/ApprovalQueue.jsx";
import DriftQueue from "@/components/DriftQueue.jsx";
import AutonomyLadder from "@/components/AutonomyLadder.jsx";
import ChunkInspector from "@/components/ChunkInspector.jsx";
import MetricsEval from "@/components/MetricsEval.jsx";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import { useAlertStream } from "@/hooks/useAlertStream";
import { useWorkflowRun } from "@/hooks/useWorkflowRun";

const TABS = [
  "Ops Board",
  "Incident Workspace",
  "Agent Trace",
  "Approval Queue",
  "Drift Queue",
  "Autonomy Ladder",
  "Chunk Inspector",
  "Metrics & Eval",
];

const DEMO_SCENARIOS = [
  { ciId: "CI-0059", label: "Clean fix (auto-completes)" },
  { ciId: "CI-0006", label: "Needs approval (prod)" },
  { ciId: "CI-0121", label: "Fake fix caught (degraded)" },
];

function PlaceholderTab({ name }) {
  return (
    <p className="rounded-md border border-dashed border-border p-6 text-sm text-muted-foreground">
      {name} — not yet built (see prd-phase-4.md atomic steps).
    </p>
  );
}

function GoldenPathBar({ scenario, setScenario, incident, onStart }) {
  return (
    <div className="flex shrink-0 flex-wrap items-center gap-3 border-b border-border bg-secondary/40 px-4 py-2 text-sm">
      <span className="text-xs font-medium text-muted-foreground">Active incident:</span>
      <select
        className="rounded-md border border-border bg-background px-2 py-1 text-xs"
        value={scenario.ciId}
        onChange={(e) => setScenario(DEMO_SCENARIOS.find((s) => s.ciId === e.target.value))}
        disabled={incident.loading}
      >
        {DEMO_SCENARIOS.map((s) => (
          <option key={s.ciId} value={s.ciId}>
            {s.ciId} — {s.label}
          </option>
        ))}
      </select>
      <Button size="sm" onClick={onStart} disabled={incident.loading}>
        {incident.loading ? "Running…" : "Start incident"}
      </Button>
      {incident.run && (
        <span className="text-xs text-muted-foreground">
          {incident.run.incident_id} — {incident.run.status}
          {incident.run.verification_status ? ` (${incident.run.verification_status})` : ""} ·
          modality: {incident.run.modality}
        </span>
      )}
      {incident.error && <span className="text-xs text-red-500">{incident.error}</span>}
      <span className="ml-auto text-xs text-muted-foreground">
        Shared across Incident Workspace / Agent Trace / Approval Queue — same run, different views.
      </span>
    </div>
  );
}

// Cockpit layout: sidebar + a shared "active incident" (golden path) + tabbed workspace. One
// workflow-run hook lives here and is passed to every tab that shows a run, so starting an
// incident on one tab is visible consistently on the others (as far as the no-checkpointing
// architecture allows — see ApprovalQueue.jsx for the "approve re-runs, doesn't resume" limitation).
export default function CockpitShell({ token, apiBase, username, onLogout }) {
  const [role, setRole] = useState("Ops Engineer");
  const [activeTab, setActiveTab] = useState(TABS[0]);
  const [scenario, setScenario] = useState(DEMO_SCENARIOS[0]);
  const { alerts, connectionStatus } = useAlertStream({ apiBase, token });
  const incident = useWorkflowRun({ apiBase, token });

  function startIncident() {
    // auto_approve=false so the full journey (including a possible pending_approval stop) is
    // visible — Approval Queue is what moves it forward from there, not this button.
    incident.triggerRun(scenario.ciId, "incident", false);
  }

  return (
    <div className="flex h-screen overflow-hidden">
      <Sidebar
        role={role}
        onRoleChange={setRole}
        connectionStatus={connectionStatus}
        apiBase={apiBase}
        token={token}
        incident={incident}
      />

      <div className="flex min-w-0 flex-1 flex-col">
        <header className="flex shrink-0 items-center justify-between border-b border-border px-6 py-3">
          <h1 className="text-lg font-semibold">Maintenance Control Plane</h1>
          <div className="flex items-center gap-3 text-sm text-muted-foreground">
            <span>{username}</span>
            <Button variant="outline" size="sm" onClick={onLogout}>
              Log out
            </Button>
          </div>
        </header>

        <nav className="flex shrink-0 gap-1 overflow-x-auto border-b border-border px-4 py-2">
          {TABS.map((tab) => (
            <button
              key={tab}
              onClick={() => setActiveTab(tab)}
              className={cn(
                "whitespace-nowrap rounded-md px-3 py-1.5 text-sm hover:bg-secondary",
                activeTab === tab && "bg-secondary font-medium"
              )}
            >
              {tab}
            </button>
          ))}
        </nav>

        <GoldenPathBar scenario={scenario} setScenario={setScenario} incident={incident} onStart={startIncident} />

        <main className="min-w-0 flex-1 overflow-y-auto p-6">
          {activeTab === "Ops Board" && (
            <OpsBoard
              apiBase={apiBase}
              token={token}
              alerts={alerts}
              connectionStatus={connectionStatus}
              incident={incident}
            />
          )}
          {activeTab === "Incident Workspace" && <IncidentWorkspace incident={incident} />}
          {activeTab === "Agent Trace" && <AgentTrace incident={incident} />}
          {activeTab === "Approval Queue" && <ApprovalQueue apiBase={apiBase} token={token} incident={incident} />}
          {activeTab === "Drift Queue" && <DriftQueue apiBase={apiBase} token={token} />}
          {activeTab === "Autonomy Ladder" && <AutonomyLadder apiBase={apiBase} token={token} />}
          {activeTab === "Chunk Inspector" && <ChunkInspector apiBase={apiBase} token={token} />}
          {activeTab === "Metrics & Eval" && <MetricsEval apiBase={apiBase} token={token} />}
          {![
            "Ops Board", "Incident Workspace", "Agent Trace", "Approval Queue", "Drift Queue",
            "Autonomy Ladder", "Chunk Inspector", "Metrics & Eval",
          ].includes(activeTab) && <PlaceholderTab name={activeTab} />}
        </main>
      </div>
    </div>
  );
}
