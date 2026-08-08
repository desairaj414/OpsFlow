// Turns an agent's raw SpecialistResult.result payload into the plain-language line a human
// actually wants — "what did this agent conclude", not just the metadata around the call. One case
// per agent_name because each agent's result shape is genuinely different (api-contract.md
// SpecialistResult.result is agent-specific by design); no shared shape to generalize over.
// Shared by AgentTrace.jsx (per-handoff detail cards) and IncidentWorkspace.jsx (pipeline flow).
export function summarizeResult(entry) {
  const r = entry?.result || {};
  switch (entry?.agent_name) {
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

// Fixed pipeline order (domain-workflows.md: Correlate -> Enrich -> Diagnose -> Plan -> Gate ->
// Approve -> Execute -> Verify -> Sync -> Learn) — the subset that actually produces a
// SpecialistResult in the current chain, in the order the Supervisor dispatches them.
export const AGENT_PIPELINE_ORDER = ["enrichment", "diagnosis", "planner", "verification", "sync", "knowledge"];

export const AGENT_DISPLAY_NAMES = {
  enrichment: "Enrichment",
  diagnosis: "Diagnosis",
  planner: "Planner",
  verification: "Verification",
  sync: "Sync",
  knowledge: "Knowledge",
};
