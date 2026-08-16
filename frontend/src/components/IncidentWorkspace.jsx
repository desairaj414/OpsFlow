"use client";

import { useState } from "react";
import { ArrowRight } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Modal } from "@/components/ui/modal";
import AgentTrace from "@/components/AgentTrace.jsx";
import { findTraceEntry as findEntry } from "@/lib/utils";
import { summarizeResult, AGENT_PIPELINE_ORDER, AGENT_DISPLAY_NAMES } from "@/lib/agentSummary";
import { apiFetch } from "@/lib/api.js";

const LLM_AGENTS = new Set(["diagnosis", "planner"]);

// What each raw evidence source_type actually means, for a reader who doesn't already know the
// backend's vocabulary — shown instead of (not just alongside) the raw string.
const SOURCE_TYPE_LABELS = {
  cmdb: "Configuration record",
  cmdb_fact: "Configuration record",
  cmdb_relationship: "Related system link",
  alert: "Alert fired",
  metrics: "Metric history",
  ticket_history_precedent: "Similar past ticket",
  patch_inventory: "Pending patches",
  change_calendar: "Change-calendar blackouts",
};

// CMDB/alert/metric facts are always confidence=1.0 — they're read directly off a system, not
// probabilistically inferred, so "confidence 1.00" reads as meaningless jargon for a plain fact.
// Only genuinely graded evidence (ticket-history similarity search) gets a percentage.
function formatEvidenceConfidence(confidence) {
  return confidence >= 0.999 ? "Verified fact" : `${Math.round(confidence * 100)}% match`;
}

// Pipeline flow view (this session's redesign ask: "show the data going from where to what"):
// Enrichment -> Diagnosis -> Planner -> Verification -> Sync -> Knowledge, each node showing its
// one-line real conclusion (same summarizeResult used in Agent Trace's detail cards) so the whole
// incident reads top-to-bottom without switching tabs. A stage the chain never reached (e.g. it
// stopped at Enrichment) renders as a dashed "not reached" node instead of being silently omitted.
function FlowPipeline({ trace }) {
  return (
    <div className="flex flex-col items-stretch gap-2 sm:flex-row sm:flex-wrap sm:overflow-x-auto sm:pb-1">
      {AGENT_PIPELINE_ORDER.map((agentName, i) => {
        const entry = findEntry(trace, agentName);
        const isLast = i === AGENT_PIPELINE_ORDER.length - 1;
        return (
          <div key={agentName} className="flex flex-col items-center gap-2 sm:flex-row sm:items-stretch">
            <div
              className={
                entry
                  ? "w-full rounded-lg border border-border bg-card p-3 shadow-sm sm:w-48"
                  : "w-full rounded-lg border border-dashed border-border bg-secondary/30 p-3 text-muted-foreground sm:w-48"
              }
            >
              <div className="mb-1 flex items-center justify-between gap-1">
                <span className="text-xs font-semibold">{AGENT_DISPLAY_NAMES[agentName]}</span>
                {entry && <Badge variant={LLM_AGENTS.has(agentName) ? "ai-proposed" : "system-verified"} />}
              </div>
              <p className="text-xs leading-snug">
                {entry ? summarizeResult(entry) : "Not reached — chain stopped or was blocked earlier."}
              </p>
            </div>
            {!isLast && (
              <div className="flex items-center justify-center text-muted-foreground">
                {/* Points down while cards stack vertically on mobile, right once they're a row at sm+. */}
                <ArrowRight className="h-4 w-4 shrink-0 rotate-90 sm:rotate-0" />
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}

function SectionCaption({ children }) {
  return <p className="mb-2 text-xs text-muted-foreground">{children}</p>;
}

function EvidenceSection({ enrichment }) {
  const evidence = enrichment?.result?.evidence ?? [];
  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">Evidence ({evidence.length} artifacts)</CardTitle>
      </CardHeader>
      <CardContent className="space-y-2 text-sm">
        <SectionCaption>
          Facts the Enrichment agent gathered about this CI — configuration records, live alerts,
          metric history, and similar past tickets. Everything Diagnosis reasons from below, and
          nothing else.
        </SectionCaption>
        {evidence.map((e, i) => (
          // artifact_id isn't unique on its own: the CMDB fact and CMDB-relationship entries
          // both cite the CI itself as artifact_id, differing only by source_type.
          <div key={`${e.artifact_id}-${e.source_type}-${i}`} className="rounded-md border border-border p-2">
            <div className="flex items-center justify-between text-xs text-muted-foreground">
              <span className="font-medium text-foreground">{SOURCE_TYPE_LABELS[e.source_type] || e.source_type}</span>
              <span>
                <span className="font-mono">{e.artifact_id}</span> · {formatEvidenceConfidence(e.confidence)}
              </span>
            </div>
            <p className="mt-1">{e.extract}</p>
          </div>
        ))}
        {evidence.length === 0 && <p className="text-muted-foreground">No evidence gathered.</p>}
      </CardContent>
    </Card>
  );
}

function HypothesesSection({ diagnosis }) {
  const hypotheses = diagnosis?.result?.hypotheses ?? [];
  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between">
          <CardTitle className="text-base">Ranked Hypotheses</CardTitle>
          {hypotheses.length > 0 && <Badge variant="ai-proposed" />}
        </div>
      </CardHeader>
      <CardContent className="space-y-2 text-sm">
        <SectionCaption>
          The AI's root-cause theories, ranked by confidence. Every hypothesis must cite specific
          evidence above ("cites") to appear here at all — an uncited guess is dropped automatically,
          not just flagged.
        </SectionCaption>
        {hypotheses.map((h, i) => (
          <div key={i} className="rounded-md border border-border p-2">
            <div className="flex items-center justify-between text-xs text-muted-foreground">
              <span>#{i + 1}</span>
              <span>confidence {h.confidence.toFixed(2)}</span>
            </div>
            <p className="mt-1">{h.text}</p>
            <p className="mt-1 text-xs text-muted-foreground">
              cites: {h.cited_artifact_ids.join(", ")}
            </p>
          </div>
        ))}
        {hypotheses.length === 0 && (
          <p className="rounded-md border border-dashed border-border p-2 text-muted-foreground">
            Could not verify a root cause — no hypothesis cleared citation enforcement.
          </p>
        )}
      </CardContent>
    </Card>
  );
}

function PlanSection({ planner, knowledge }) {
  const plan = planner?.result;
  // The Planner doesn't consult the Negative KB before drafting (not implemented) — the only real
  // Negative-KB signal in this run is the Knowledge agent's post-hoc entry when the fix failed.
  const negativeKbEntry = knowledge?.result?.negative_kb_entry;
  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between">
          <CardTitle className="text-base">Plan</CardTitle>
          {plan?.steps?.length > 0 && <Badge variant="ai-proposed" />}
        </div>
      </CardHeader>
      <CardContent className="space-y-2 text-sm">
        <SectionCaption>
          The remediation runbook the Planner drafted from, and the safety check (blast radius +
          Policy Gate) it had to pass before anything could execute.
        </SectionCaption>
        {negativeKbEntry && (
          <p className="rounded-md border border-yellow-600/40 bg-yellow-600/10 p-2 text-xs">
            Negative-KB caution: this run&apos;s fix failed and was recorded as{" "}
            <span className="font-mono">{negativeKbEntry.id}</span> for{" "}
            {negativeKbEntry.ci_class} / {negativeKbEntry.failure_signature} — worth a human&apos;s
            second look before repeating this approach on a similar CI.
          </p>
        )}
        <p>
          Runbook: <span className="font-mono">{plan?.runbook_id || "—"}</span>
        </p>
        <p className="text-xs text-muted-foreground">
          Blast radius: {plan?.blast_radius?.count ?? "—"} · Policy gate:{" "}
          {plan?.policy_gate_result?.decision ?? "—"}
        </p>
        <ul className="space-y-1">
          {(plan?.steps ?? []).map((s) => (
            <li key={s.step_no} className="rounded-md border border-border p-2 text-xs">
              {s.step_no}. {s.action} (cites {s.cites_runbook_step})
            </li>
          ))}
        </ul>
        {(!plan?.steps || plan.steps.length === 0) && (
          <p className="text-muted-foreground">No runbook-bounded steps drafted.</p>
        )}
      </CardContent>
    </Card>
  );
}

const SEVERITY_BADGE_CLASS = {
  critical: "border-red-600/40 bg-red-600/10 text-red-600",
  high: "border-orange-600/40 bg-orange-600/10 text-orange-600",
  medium: "border-yellow-600/40 bg-yellow-600/10 text-yellow-600",
  low: "border-border bg-secondary/30 text-muted-foreground",
};

function formatWindowTime(iso) {
  return iso ? new Date(iso).toLocaleString() : "—";
}

// Patch Management's plan_output (PRD §7: "Maintenance Planner panel for patch runs";
// domain-workflows.md parity table: "Grouped maintenance window"). Only rendered for
// workflow_type === "patch" — the deterministic scheduling rule engine
// (backend/guardrails/scheduling.py) that produced this never runs for incident/performance.
function MaintenanceWindowSection({ planner }) {
  const window = planner?.result?.maintenance_window;
  if (!window) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Maintenance Planner</CardTitle>
        </CardHeader>
        <CardContent className="text-sm text-muted-foreground">
          <SectionCaption>
            Dependency-aware, blackout-aware, SLA-aware scheduling for this CI&apos;s pending
            patches (intelligent scheduling, no LLM — a deterministic rule engine).
          </SectionCaption>
          No pending patches for this CI right now, or the patch-source simulator was unreachable
          during this run.
        </CardContent>
      </Card>
    );
  }
  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between">
          <CardTitle className="text-base">Maintenance Planner</CardTitle>
          <Badge variant="system-verified" />
        </div>
      </CardHeader>
      <CardContent className="space-y-3 text-sm">
        <SectionCaption>
          Grouped maintenance window — patches ordered by dependency then severity, scheduled into
          the earliest slot that clears every applicable change-calendar blackout. Deterministic
          rule engine, not an LLM guess (PRD C6).
        </SectionCaption>
        <div className="rounded-md border border-border p-2">
          <p className="text-xs text-muted-foreground">Proposed window</p>
          <p className="font-mono text-xs">
            {formatWindowTime(window.proposed_window?.start)} → {formatWindowTime(window.proposed_window?.end)}
          </p>
          <p className="mt-1 text-xs text-muted-foreground">
            {window.blackout_windows_checked} blackout window(s) checked for this CI/environment
          </p>
        </div>
        {window.sla_at_risk && (
          <p className="rounded-md border border-red-600/40 bg-red-600/10 p-2 text-xs">
            SLA at risk: the earliest open window falls after the highest-severity patch&apos;s
            deadline ({formatWindowTime(window.earliest_sla_due)}).
          </p>
        )}
        {!window.sla_at_risk && window.earliest_sla_due && (
          <p className="text-xs text-muted-foreground">
            Earliest SLA deadline: {formatWindowTime(window.earliest_sla_due)} — proposed window meets it.
          </p>
        )}
        <ul className="space-y-1">
          {window.grouped_patches.map((p) => (
            <li key={p.id} className="flex items-center justify-between rounded-md border border-border p-2 text-xs">
              <span>
                {p.order}. <span className="font-mono">{p.id}</span>
                {p.depends_on_patch_ids?.length > 0 && (
                  <span className="ml-1 text-muted-foreground">(after {p.depends_on_patch_ids.join(", ")})</span>
                )}
              </span>
              <span className={`rounded border px-1.5 py-0.5 ${SEVERITY_BADGE_CLASS[p.severity] || SEVERITY_BADGE_CLASS.low}`}>
                {p.severity}
              </span>
            </li>
          ))}
        </ul>
      </CardContent>
    </Card>
  );
}

function LinkedSystemsSection({ sync, verification }) {
  const ticket = sync?.result?.ticket;
  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between">
          <CardTitle className="text-base">Linked Systems</CardTitle>
          {verification?.result?.status && <Badge variant="system-verified" />}
        </div>
      </CardHeader>
      <CardContent className="grid grid-cols-1 gap-3 text-sm sm:grid-cols-2">
        <SectionCaption>
          What was actually written back to the ticketing system and CMDB, and the Verification
          agent's final verdict (not just "alert cleared" — see modal below).
        </SectionCaption>
        <div className="rounded-md border border-border p-2">
          <p className="text-xs text-muted-foreground">ITSM ticket</p>
          <p className="font-mono text-xs">{ticket?.sys_id ?? "—"}</p>
          <p className="text-xs text-muted-foreground">state: {ticket?.state ?? "—"}</p>
        </div>
        <div className="rounded-md border border-border p-2">
          <p className="text-xs text-muted-foreground">Verification</p>
          <p>{verification?.result?.status ?? "—"}</p>
        </div>
        <p className="col-span-full text-xs text-muted-foreground">
          Tracker linkage and cross-system contradiction highlighting aren&apos;t part of the
          current agent chain&apos;s real output (only ITSM + CMDB are touched by Sync) — not shown
          here rather than fabricated.
        </p>
      </CardContent>
    </Card>
  );
}

// The former standalone Approval Queue tab, folded in here: "one incident, start to finish"
// (this tab's own tagline) means the decision point belongs where the rest of the incident
// already lives, not a separate tab reading the same shared `run` state. Voice/chat approval via
// ChatWidget.jsx's mic+/chat still works globally regardless of which tab is open.
function ApprovalSection({ apiBase, token, incident, canDecide }) {
  const [reason, setReason] = useState("");
  const [decisionError, setDecisionError] = useState("");
  const [decided, setDecided] = useState(null); // "approved" | "rejected"
  const [approvedRun, setApprovedRun] = useState(null);
  const [deciding, setDeciding] = useState(false);

  const run = incident.run;
  const planner = findEntry(run.trace, "planner");
  const diagnosis = findEntry(run.trace, "diagnosis");
  const hypotheses = diagnosis?.result?.hypotheses ?? [];
  const topHypothesis = hypotheses[0];
  const counterHypothesis = hypotheses[1];
  const enrichment = findEntry(run.trace, "enrichment");
  const ciId = enrichment?.result?.evidence?.[0]?.artifact_id;

  async function recordDecision(decision) {
    if (!reason.trim()) {
      setDecisionError("A reason is required.");
      return;
    }
    setDecisionError("");
    setDeciding(true);
    try {
      const res = await apiFetch(apiBase, "/workflows/decision", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        token,
        body: JSON.stringify({ incident_id: run.incident_id, decision, reason }),
      });
      if (!res.ok) throw new Error(`Request failed (${res.status})`);
      setDecided(decision === "approve" ? "approved" : "rejected");

      if (decision === "approve" && ciId) {
        // Honest limitation: run_workflow has no checkpointing, so there's no way to resume the
        // exact paused run above. This triggers a FRESH re-run with auto_approve=true — not a
        // continuation of run.incident_id, which gets a new incident_id of its own. It updates
        // the SAME shared `incident` state, so this same view reflects it once done.
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

  if (decided === "approved") {
    return (
      <Card className="border-status-good/40">
        <CardContent className="space-y-2 pt-4 text-sm">
          <div className="flex items-center gap-2">
            <Badge variant="human-approved" />
            <p>Reason logged to the audit trail. Executing the approved plan.</p>
          </div>
          {approvedRun && (
            <p className="text-muted-foreground">
              New run {approvedRun.incident_id}: {approvedRun.status}
              {approvedRun.verification_status ? ` (${approvedRun.verification_status})` : ""}
            </p>
          )}
          <Button size="sm" variant="outline" onClick={reset}>
            Done
          </Button>
        </CardContent>
      </Card>
    );
  }

  if (decided === "rejected") {
    return (
      <Card className="border-status-warning/40">
        <CardContent className="space-y-2 pt-4 text-sm">
          <div className="flex items-center gap-2">
            <Badge variant="human-rejected" />
            <p>Reason logged to the audit trail. No execution follows.</p>
          </div>
          <Button size="sm" variant="outline" onClick={reset}>
            Done
          </Button>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card className="border-red-600/40">
      <CardHeader>
        <div className="flex items-center justify-between">
          <CardTitle className="text-base">Needs approval</CardTitle>
          <Badge variant="ai-proposed" />
        </div>
      </CardHeader>
      <CardContent className="space-y-3 text-sm">
        <SectionCaption>
          Recommendation, counter-hypothesis, and the safety-gate summary this plan had to pass —
          decide before anything executes.
        </SectionCaption>
        <div>
          <p className="text-xs font-medium text-muted-foreground">Recommendation</p>
          <p>{topHypothesis?.text ?? "—"}</p>
          {topHypothesis && <p className="text-xs text-muted-foreground">confidence {topHypothesis.confidence.toFixed(2)}</p>}
        </div>
        {counterHypothesis && (
          <div>
            <p className="text-xs font-medium text-muted-foreground">Counter-hypothesis</p>
            <p>{counterHypothesis.text}</p>
            <p className="text-xs text-muted-foreground">confidence {counterHypothesis.confidence.toFixed(2)}</p>
          </div>
        )}
        <div className="rounded-md border border-border p-2 text-xs">
          Runbook: <span className="font-mono">{planner?.result?.runbook_id || "—"}</span> ·
          Blast radius: {planner?.result?.blast_radius?.count ?? "—"} · Policy gate:{" "}
          {planner?.result?.policy_gate_result?.decision ?? "—"}
        </div>

        {canDecide ? (
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
            </div>
            <p className="text-xs text-muted-foreground">
              Or ask the Assistant (bottom right) — say &quot;approve {run.incident_id}&quot;.
            </p>
          </div>
        ) : (
          <p className="rounded-md border border-dashed border-border p-2 text-xs text-muted-foreground">
            Only an Approver or Admin can decide this — you&apos;re signed in as an Ops Engineer.
          </p>
        )}
      </CardContent>
    </Card>
  );
}

const SYSTEM_LABEL = { itsm: "ServiceNow", tracker: "Jira" };

// A bulk-seeded historical ticket (system-of-record backlog that pre-dates this session — see
// db/init_db.py's populate_local_tickets_bulk) was never run through the agent chain, so it has no
// evidence/hypotheses/plan/verification to show. Rendering the normal pipeline view for one of
// these produced six "not reached" cards and nothing else — technically accurate, but reads as a
// broken page, not an empty-but-honest one. This is the dedicated, honest view for that case: the
// real ticket fields that DO exist, and a plain explanation of why there's no agent trace.
function HistoricalTicketCard({ run }) {
  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between">
          <CardTitle className="text-base">
            {SYSTEM_LABEL[run.system] || run.system} ticket {run.external_id}
          </CardTitle>
          <Badge variant="system-verified" />
        </div>
      </CardHeader>
      <CardContent className="space-y-3 text-sm">
        <p className="rounded-md border border-dashed border-border p-2 text-xs text-muted-foreground">
          {run.reason || "Historical ticket — pre-dates this session, never run through the agent chain."} This
          is browsable ticket history, not a live incident — there's no evidence, diagnosis, or plan
          to show because the agent chain never touched it.
        </p>
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-3">
          <div>
            <p className="text-xs text-muted-foreground">Configuration item</p>
            <p className="font-mono text-xs">{run.ci_id || "—"}</p>
          </div>
          <div>
            <p className="text-xs text-muted-foreground">Priority</p>
            <p>{run.priority || "—"}</p>
          </div>
          <div>
            <p className="text-xs text-muted-foreground">Status</p>
            <p>{run.status_label || "—"}</p>
          </div>
          <div>
            <p className="text-xs text-muted-foreground">Opened</p>
            <p className="text-xs">{run.opened_at ? new Date(run.opened_at).toLocaleString() : "—"}</p>
          </div>
          <div>
            <p className="text-xs text-muted-foreground">Closed</p>
            <p className="text-xs">{run.closed_at ? new Date(run.closed_at).toLocaleString() : "still open"}</p>
          </div>
        </div>
        <div>
          <p className="text-xs text-muted-foreground">Summary</p>
          <p>{run.summary || "—"}</p>
        </div>
      </CardContent>
    </Card>
  );
}

// Unified Incident Record (PRD §7): evidence w/ citations, ranked hypotheses, plan w/ blast
// radius + Negative-KB caution, linked systems. Reads the shared `incident` run from
// CockpitShell — same real run data the Agent Trace Viewer shows, organized as a case file.
export default function IncidentWorkspace({ incident, apiBase, token, identity }) {
  const { run, loading, error } = incident;
  const canDecide = identity?.role === "approver" || identity?.role === "admin";
  const [showTrace, setShowTrace] = useState(false);

  if (!run && !loading && !error) {
    return (
      <p className="text-sm text-muted-foreground">
        No active incident — click "Diagnose" on an alert group in Ops Board (or open one from the
        notification bell / Ticket History) to build the record from a real run.
      </p>
    );
  }

  if (run?.status === "historical") {
    return (
      <div className="space-y-4">
        <HistoricalTicketCard run={run} />
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {loading && <p className="text-sm text-muted-foreground">Running…</p>}
      {error && <p className="text-sm text-red-500">{error}</p>}

      {run && (
        <>
          <p className="text-sm text-muted-foreground">
            {run.incident_id} — {run.status} · modality: {run.modality}
          </p>

          <div>
            <div className="mb-2 flex items-center justify-between gap-2">
              <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                How this incident moved through the agent chain
              </p>
              <Button size="sm" variant="outline" onClick={() => setShowTrace(true)}>
                View full Agent Trace
              </Button>
            </div>
            <FlowPipeline trace={run.trace} />
          </div>

          <Modal
            open={showTrace}
            onClose={() => setShowTrace(false)}
            title="Agent Trace"
            description="Every AI hand-off in this incident — which model ran, how confident it was, and what it actually concluded."
            className="max-w-4xl"
          >
            <AgentTrace incident={incident} />
          </Modal>

          {run.status === "pending_approval" && (
            <ApprovalSection apiBase={apiBase} token={token} incident={incident} canDecide={canDecide} />
          )}

          <div className="grid gap-4 lg:grid-cols-2">
            <EvidenceSection enrichment={findEntry(run.trace, "enrichment")} />
            <HypothesesSection diagnosis={findEntry(run.trace, "diagnosis")} />
            <PlanSection
              planner={findEntry(run.trace, "planner")}
              knowledge={findEntry(run.trace, "knowledge")}
            />
            {run.workflow_type === "patch" && (
              <MaintenanceWindowSection planner={findEntry(run.trace, "planner")} />
            )}
            <LinkedSystemsSection
              sync={findEntry(run.trace, "sync")}
              verification={findEntry(run.trace, "verification")}
            />
          </div>
        </>
      )}
    </div>
  );
}
