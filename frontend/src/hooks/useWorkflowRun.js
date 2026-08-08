"use client";

import { useState } from "react";

// Shared trigger for real workflow runs — used across Ops Board/Agent Trace/Incident Workspace
// (including its approval section) so a run started in one tab shows up consistently in the
// others (as far as the architecture allows: run_workflow has no checkpointing, so "approve"
// produces a genuinely new run rather than resuming the paused one — see IncidentWorkspace.jsx's
// ApprovalSection).
export function useWorkflowRun({ apiBase, token }) {
  const [run, setRun] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  // `silent: true` runs the workflow (real backend call, real ticket persisted) WITHOUT touching
  // the shared `run` state Incident Workspace/Agent Trace read from — used by background
  // auto-triage (useAutoTriage.js) so a newly-arrived alert diagnosing itself never yanks the
  // screen out from under whatever the human is actually looking at. Only an explicit action
  // (Ops Board's Diagnose/Run-all, the Tickets tab's Open, clicking a notification) should ever
  // change what's on screen.
  async function triggerRun(ciId, workflowType = "incident", autoApprove = true, { silent = false } = {}) {
    if (!silent) setLoading(true);
    setError("");
    try {
      const res = await fetch(`${apiBase}/workflows/run`, {
        method: "POST",
        headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
        body: JSON.stringify({ ci_id: ciId, workflow_type: workflowType, auto_approve: autoApprove }),
      });
      if (!res.ok) throw new Error(`Request failed (${res.status})`);
      const data = await res.json();
      if (!silent) setRun(data);
      return data;
    } catch (err) {
      if (!silent) setError(err.message);
      return null;
    } finally {
      if (!silent) setLoading(false);
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
