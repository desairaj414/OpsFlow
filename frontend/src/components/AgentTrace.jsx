"use client";

import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";

// LLM-calling agents produce unverified proposals; the deterministic ones (no LLM call, rule-based
// or measurement-based) are a system check, not a model guess — that's the line the badge draws.
const LLM_AGENTS = new Set(["diagnosis", "planner"]);

// Turns each agent's raw `result` payload into the plain-language line a juror actually wants —
// "what did this agent conclude", not just the metadata around the call. One case per agent_name
// because each agent's result shape is genuinely different (api-contract.md SpecialistResult.result
// is agent-specific by design); no shared shape to generalize over.
function summarizeResult(entry) {
  const r = entry.result || {};
  switch (entry.agent_name) {
    case "enrichment": {
      const count = r.evidence?.length ?? 0;
      if (!count) return "No evidence found for this CI — nothing to hand off to Diagnosis.";
      const sources = [...new Set(r.evidence.map((e) => e.source_type))].join(", ");
      return `Gathered ${count} piece${count === 1 ? "" : "s"} of evidence (${sources}) to hand to Diagnosis.`;
    }
    case "diagnosis": {
      const top = r.hypotheses?.[0];
      if (!top) return "Could not form a supportable hypothesis from the evidence gathered.";
      return `Top hypothesis (${(top.confidence * 100).toFixed(0)}% confidence): "${top.text}"`;
    }
    case "planner": {
      const steps = r.steps?.length ?? 0;
      if (!steps) return "No applicable runbook found — no plan could be drafted.";
      const gate = r.policy_gate_result?.decision;
      const gateNote = gate ? ` · Policy Gate: ${gate}` : "";
      return `Drafted a ${steps}-step plan from runbook ${r.runbook_id || "?"}${gateNote}.`;
    }
    case "verification": {
      const cleared = r.alert_cleared ? "alert cleared" : "alert still firing";
      const probe = r.health_probe_recovered ? "health probe recovered" : "health probe not recovered";
      return `${cleared}, ${probe} → verdict: ${r.status}.`;
    }
    case "sync": {
      const state = r.ticket?.state === "2" ? "left open" : "closed";
      return `Ticket ${r.ticket?.sys_id ?? "?"} ${state}; CMDB update proposed.`;
    }
    case "knowledge": {
      if (r.negative_kb_entry) return "Fix did not hold — recorded to the Negative KB so it isn't retried blindly.";
      return "Resolution verified — no failure pattern to record.";
    }
    default:
      return null;
  }
}

function HandoffCard({ entry }) {
  const summary = summarizeResult(entry);
  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between gap-2">
          <CardTitle className="text-base">{entry.agent_name}</CardTitle>
          <div className="flex items-center gap-1">
            <Badge variant={LLM_AGENTS.has(entry.agent_name) ? "ai-proposed" : "system-verified"} />
            <span className="rounded-full border border-border px-2 py-0.5 text-xs">
              {entry.transport === "a2a" ? "A2A" : "in-process"}
            </span>
          </div>
        </div>
      </CardHeader>
      <CardContent className="space-y-3">
        {summary && <p className="text-sm text-foreground">{summary}</p>}
        <div className="grid grid-cols-2 gap-x-4 gap-y-1 text-xs text-muted-foreground">
          <span>Model: {entry.model_used ?? "— (deterministic, no LLM)"}</span>
          <span>Tokens: {entry.tokens_used ?? "—"}</span>
          <span>Latency: {entry.latency_ms != null ? `${Math.round(entry.latency_ms)}ms` : "—"}</span>
          <span>Confidence: {entry.confidence.toFixed(2)}</span>
          <span>Termination: {entry.termination_reason}</span>
          <span>Citations: {entry.cited_artifact_ids.length}</span>
        </div>
      </CardContent>
    </Card>
  );
}

// Agent Trace Viewer (PRD §7 centrepiece): handoffs, model, tokens, latency, transport (in-process
// vs A2A), modality, viewable Agent Card. Reads the shared `incident` run from CockpitShell — the
// golden-path bar's "Start incident" is what triggers a run, not a button in this tab.
export default function AgentTrace({ incident }) {
  const { run, loading, error } = incident;
  const [showCard, setShowCard] = useState(false);

  if (!run && !loading && !error) {
    return (
      <p className="text-sm text-muted-foreground">
        No active incident — use the golden-path bar above ("Start incident") to trigger a real
        run through the actual agent chain (Enrichment → Diagnosis (A2A) → Planner → Verification
        → Sync → Knowledge).
      </p>
    );
  }

  return (
    <div className="space-y-4">
      {loading && <p className="text-sm text-muted-foreground">Running…</p>}
      {error && <p className="text-sm text-red-500">{error}</p>}

      {run && (
        <>
          <p className="text-sm text-muted-foreground">
            {run.incident_id} — {run.status}
            {run.verification_status ? ` (${run.verification_status})` : ""} · modality: {run.modality}
          </p>

          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
            {run.trace.map((entry, i) => (
              <HandoffCard key={`${entry.agent_name}-${i}`} entry={entry} />
            ))}
          </div>

          <div>
            <Button variant="outline" size="sm" onClick={() => setShowCard((v) => !v)}>
              {showCard ? "Hide" : "View"} Agent Card (A2A handoff)
            </Button>
            {showCard && (
              <pre className="mt-2 overflow-x-auto rounded-md border border-border bg-secondary p-3 text-xs">
                {JSON.stringify(run.agent_card, null, 2)}
              </pre>
            )}
          </div>
        </>
      )}
    </div>
  );
}
