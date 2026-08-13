---
type: Module
title: Planner Agent
description: Drafts a remediation/patch/tuning plan strictly from retrieved runbook chunks (runbook-bounded action space), then computes blast radius, the policy-gate decision, and (for patch workflows) a maintenance window — all three deterministically, never by the model.
resource: backend/agents/planner.py
tags: [agents, llm, rag, guardrails]
status: stable
generated: { by: "claude-sonnet-5/okf-produce", at: "2026-08-11T00:00:00Z" }
sources:
  - id: planner-py
    resource: backend/agents/planner.py
    title: backend/agents/planner.py
    last_modified: 2026-08-11
---

# Overview

`run_planner(incident_id, ci, runbook_class, hypothesis, actor_role)` first does a real Chroma
vector search — `query_collection("runbooks", query_text, where={"class": runbook_class})` — scoped
to the workflow's runbook class, retrieving up to 4 chunks. It then prompts the active provider's
`structured`-role model to draft a plan **using only those retrieved chunks**; `_parse_and_filter_steps()`
drops any step citing a chunk ID that wasn't actually retrieved — the same bounded-action-space
pattern as [Diagnosis](diagnosis-agent.md)'s citation enforcement.[^planner-py]

# Deterministic guardrails, computed after the LLM drafts

Three things are computed purely deterministically, never delegated to the model:

1. **Blast radius** — `guardrails/blast_radius.py`, BFS over the CMDB adjacency graph.
2. **Policy-gate decision** — `guardrails/policy_gate.py`, threshold rules over blast radius,
   environment, criticality, and actor role.
3. **Maintenance window** (`runbook_class == "patching"` only) — `guardrails/scheduling.py`,
   dependency- and blackout-aware scheduling. See [Guardrails](/guardrails/) for all three.

# Consumers

[Supervisor](supervisor.md) reads `result["policy_gate_result"]["decision"]` to decide whether the
workflow blocks, pauses for human approval, or proceeds; a `block` decision stops the workflow
entirely. `IncidentWorkspace.jsx`'s Maintenance Planner panel renders `result["maintenance_window"]`
only when `workflow_type === "patch"`.

[^planner-py]: backend/agents/planner.py
