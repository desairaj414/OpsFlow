"use client";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { findTraceEntry as findEntry } from "@/lib/utils";

function EvidenceSection({ enrichment }) {
  const evidence = enrichment?.result?.evidence ?? [];
  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">Evidence ({evidence.length} artifacts)</CardTitle>
      </CardHeader>
      <CardContent className="space-y-2 text-sm">
        {evidence.map((e, i) => (
          // artifact_id isn't unique on its own: the CMDB fact and CMDB-relationship entries
          // both cite the CI itself as artifact_id, differing only by source_type.
          <div key={`${e.artifact_id}-${e.source_type}-${i}`} className="rounded-md border border-border p-2">
            <div className="flex items-center justify-between text-xs text-muted-foreground">
              <span className="font-mono">{e.artifact_id}</span>
              <span>
                {e.source_type} · confidence {e.confidence.toFixed(2)}
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
        {negativeKbEntry && (
          <p className="rounded-md border border-yellow-600/40 bg-yellow-600/10 p-2 text-xs">
            Negative-KB caution: this run&apos;s fix failed and was recorded as{" "}
            <span className="font-mono">{negativeKbEntry.id}</span> for{" "}
            {negativeKbEntry.ci_class} / {negativeKbEntry.failure_signature} — future plans for
            this CI class + failure signature should see this (not yet wired: the Planner doesn't
            consult the Negative KB before drafting).
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

// Unified Incident Record (PRD §7): evidence w/ citations, ranked hypotheses, plan w/ blast
// radius + Negative-KB caution, linked systems. Reads the shared `incident` run from
// CockpitShell — same real run data the Agent Trace Viewer shows, organized as a case file.
export default function IncidentWorkspace({ incident }) {
  const { run, loading, error } = incident;

  if (!run && !loading && !error) {
    return (
      <p className="text-sm text-muted-foreground">
        No active incident — use the golden-path bar above ("Start incident") to build the record
        from a real run.
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
            {run.incident_id} — {run.status} · modality: {run.modality}
          </p>
          <div className="grid gap-4 lg:grid-cols-2">
            <EvidenceSection enrichment={findEntry(run.trace, "enrichment")} />
            <HypothesesSection diagnosis={findEntry(run.trace, "diagnosis")} />
            <PlanSection
              planner={findEntry(run.trace, "planner")}
              knowledge={findEntry(run.trace, "knowledge")}
            />
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
