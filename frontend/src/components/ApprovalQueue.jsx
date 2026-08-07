"use client";

import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { findTraceEntry } from "@/lib/utils";

// Approval Queue (PRD §7): recommendation + counter-hypothesis + evidence gaps; approve/edit/reject
// with mandatory reason. Voice approval lives globally in Sidebar.jsx's push-to-talk (visible on
// every tab, not just this one) — it posts the same /workflows/decision this tab does. Reads the
// shared `incident` run from CockpitShell's golden-path bar rather than triggering its own run.
export default function ApprovalQueue({ apiBase, token, incident }) {
  const [reason, setReason] = useState("");
  const [decisionError, setDecisionError] = useState("");
  const [decided, setDecided] = useState(null); // "approved" | "rejected"
  const [approvedRun, setApprovedRun] = useState(null);
  const [deciding, setDeciding] = useState(false);

  const run = incident.run;
  const planner = run && findTraceEntry(run.trace, "planner");
  const diagnosis = run && findTraceEntry(run.trace, "diagnosis");
  const hypotheses = diagnosis?.result?.hypotheses ?? [];
  const topHypothesis = hypotheses[0];
  const counterHypothesis = hypotheses[1];
  const enrichment = run && findTraceEntry(run.trace, "enrichment");
  const ciId = enrichment?.result?.evidence?.[0]?.artifact_id;

  async function recordDecision(decision) {
    if (!reason.trim()) {
      setDecisionError("A reason is required.");
      return;
    }
    setDecisionError("");
    setDeciding(true);
    try {
      const res = await fetch(`${apiBase}/workflows/decision`, {
        method: "POST",
        headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
        body: JSON.stringify({ incident_id: run.incident_id, decision, reason }),
      });
      if (!res.ok) throw new Error(`Request failed (${res.status})`);
      setDecided(decision === "approve" ? "approved" : "rejected");

      if (decision === "approve" && ciId) {
        // Honest limitation: run_workflow has no checkpointing, so there's no way to resume
        // the exact paused run above. This triggers a FRESH re-run with auto_approve=true —
        // not a continuation of run.incident_id, which gets a new incident_id of its own. It
        // updates the SAME shared `incident` state, so Agent Trace/Incident Workspace reflect it.
        const fresh = await incident.triggerRun(ciId, "incident", true);
        setApprovedRun(fresh);
      }
    } catch (err) {
      setDecisionError(err.message);
    } finally {
      setDeciding(false);
    }
  }

  function reset() {
    setReason("");
    setDecisionError("");
    setDecided(null);
    setApprovedRun(null);
  }

  if (!run && !incident.loading && !incident.error) {
    return (
      <p className="text-sm text-muted-foreground">
        No active incident — use the golden-path bar above ("Start incident", pick the "Needs
        approval" scenario) to queue something real here.
      </p>
    );
  }

  return (
    <div className="space-y-4">
      {incident.loading && <p className="text-sm text-muted-foreground">Running…</p>}
      {incident.error && <p className="text-sm text-red-500">{incident.error}</p>}

      {run && run.status !== "pending_approval" && !decided && (
        <p className="text-sm text-muted-foreground">
          Current incident ({run.incident_id}) status is &quot;{run.status}&quot;, not
          pending_approval — nothing to decide here. Switch the golden-path scenario to the
          "Needs approval" one and click Start incident.
        </p>
      )}

      {run && run.status === "pending_approval" && !decided && (
        <Card>
          <CardHeader>
            <CardTitle className="text-base">{run.incident_id} — needs approval</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3 text-sm">
            <div>
              <p className="text-xs font-medium text-muted-foreground">Recommendation</p>
              <p>{topHypothesis?.text ?? "—"}</p>
              <p className="text-xs text-muted-foreground">confidence {topHypothesis?.confidence.toFixed(2)}</p>
            </div>
            {counterHypothesis && (
              <div>
                <p className="text-xs font-medium text-muted-foreground">Counter-hypothesis</p>
                <p>{counterHypothesis.text}</p>
                <p className="text-xs text-muted-foreground">confidence {counterHypothesis.confidence.toFixed(2)}</p>
              </div>
            )}
            <p className="text-xs text-muted-foreground">
              Evidence gaps: not computed by the current agent chain — no agent produces this signal
              yet, so nothing is shown here rather than a fabricated placeholder.
            </p>
            <div className="rounded-md border border-border p-2 text-xs">
              Runbook: <span className="font-mono">{planner?.result?.runbook_id || "—"}</span> ·
              Blast radius: {planner?.result?.blast_radius?.count ?? "—"} · Policy gate:{" "}
              {planner?.result?.policy_gate_result?.decision ?? "—"}
            </div>

            <div className="space-y-2 pt-2">
              <Input
                placeholder="Reason (mandatory for approve or reject)"
                value={reason}
                onChange={(e) => setReason(e.target.value)}
              />
              {decisionError && <p className="text-xs text-red-500">{decisionError}</p>}
              <div className="flex gap-2">
                <Button size="sm" onClick={() => recordDecision("approve")} disabled={deciding}>
                  Approve
                </Button>
                <Button size="sm" variant="outline" onClick={() => recordDecision("reject")} disabled={deciding}>
                  Reject
                </Button>
                <Button size="sm" variant="ghost" disabled title="Plan editing not yet supported — approve or reject only">
                  Edit (not yet supported)
                </Button>
              </div>
              <p className="text-xs text-muted-foreground">
                Or use Push to talk in the sidebar — say &quot;approve {run.incident_id}&quot;.
              </p>
            </div>
          </CardContent>
        </Card>
      )}

      {decided === "approved" && (
        <div className="space-y-2">
          <div className="flex items-center gap-2">
            <Badge variant="human-approved" />
            <p className="text-sm">
              Reason logged to the audit trail. Re-running the same CI with auto_approve=true (a
              fresh run — {run.incident_id} above is not being resumed, no checkpointing exists).
            </p>
          </div>
          {approvedRun && (
            <p className="text-sm text-muted-foreground">
              New run {approvedRun.incident_id}: {approvedRun.status}
              {approvedRun.verification_status ? ` (${approvedRun.verification_status})` : ""} —
              check Agent Trace / Incident Workspace, same shared incident.
            </p>
          )}
          <Button size="sm" variant="outline" onClick={reset}>
            Done
          </Button>
        </div>
      )}

      {decided === "rejected" && (
        <div className="space-y-2">
          <div className="flex items-center gap-2">
            <Badge variant="human-rejected" />
            <p className="text-sm">Reason logged to the audit trail. No execution follows.</p>
          </div>
          <Button size="sm" variant="outline" onClick={reset}>
            Done
          </Button>
        </div>
      )}
    </div>
  );
}
