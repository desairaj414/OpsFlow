"use client";

import { useState } from "react";

// Shared trigger for real workflow runs — used across Ops Board/Agent Trace/Incident
// Workspace/Approval Queue so a run started in one tab shows up consistently in the others
// (as far as the architecture allows: run_workflow has no checkpointing, so "approve" produces a
// genuinely new run rather than resuming the paused one — see ApprovalQueue.jsx).
export function useWorkflowRun({ apiBase, token }) {
  const [run, setRun] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  async function triggerRun(ciId, workflowType = "incident", autoApprove = true) {
    setLoading(true);
    setError("");
    try {
      const res = await fetch(`${apiBase}/workflows/run`, {
        method: "POST",
        headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
        body: JSON.stringify({ ci_id: ciId, workflow_type: workflowType, auto_approve: autoApprove }),
      });
      if (!res.ok) throw new Error(`Request failed (${res.status})`);
      const data = await res.json();
      setRun(data);
      return data;
    } catch (err) {
      setError(err.message);
      return null;
    } finally {
      setLoading(false);
    }
  }

  // Drives a workflow from an already-confirmed voice/image MaintenanceSignal (POST /intake/confirm)
  // instead of a raw CI id — same shared `run` state, so the result shows up in every tab reading it.
  async function runFromSignal(signal, workflowType = "incident") {
    setLoading(true);
    setError("");
    try {
      const res = await fetch(`${apiBase}/intake/confirm`, {
        method: "POST",
        headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
        body: JSON.stringify({ signal, workflow_type: workflowType }),
      });
      if (!res.ok) {
        const detail = await res.json().catch(() => ({}));
        throw new Error(detail.detail || `Request failed (${res.status})`);
      }
      const data = await res.json();
      setRun(data);
      return data;
    } catch (err) {
      setError(err.message);
      return null;
    } finally {
      setLoading(false);
    }
  }

  return { run, loading, error, triggerRun, runFromSignal, setRun };
}
