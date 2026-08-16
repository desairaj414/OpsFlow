---
type: Module
title: Planner Agent
description: Drafts a remediation/patch/tuning plan strictly from retrieved runbook chunks (runbook-bounded action space), then computes blast radius, the policy-gate decision, and (for patch workflows) a maintenance window — all three deterministically, never by the model.
resource: backend/agents/planner.py
tags: [agents, llm, rag, guardrails]
status: stable
generated: { by: "claude-sonnet-5/okf-maintain", at: "2026-08-17T00:00:00Z" }
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
   environment, criticality, and actor role, evaluated against a `PolicyContext` built by
   `_load_policy_context()` (added 2026-08-17 — found the module's `FREEZE_WINDOW`/
   `MAX_CONCURRENT_CHANGES` rules were fully built and unit-tested but never reachable, since this
   used to always pass an empty context). `active_changes_in_environment` is a live COUNT of
   `local_tickets` rows at `status_normalized='needs_approval'` in the CI's environment — that
   status is set exclusively by a live run pausing for approval, never by the 4000 bulk-seeded
   historical rows. `freeze_windows` reuses the `patch_mcp.get_change_calendar()` call directly
   below, **scoped to `runbook_class == "patching"` only** — wiring it to every workflow type broke
   incident/tuning tests, because `data/change_calendar.json`'s global blackout window is
   deliberately date-ranged to include "now" for the Patch Management demo below, and blocking
   incident remediation because of an unrelated code freeze isn't correct behavior (real ITSM
   practice exempts emergency changes from standard freezes).[^planner-py]
3. **Maintenance window** (`runbook_class == "patching"` only) — `guardrails/scheduling.py`,
   dependency- and blackout-aware scheduling. See [Guardrails](/guardrails/) for all three.

# Consumers

[Supervisor](supervisor.md) reads `result["policy_gate_result"]["decision"]` to decide whether the
workflow blocks, pauses for human approval, or proceeds; a `block` decision stops the workflow
entirely. `IncidentWorkspace.jsx`'s Maintenance Planner panel renders `result["maintenance_window"]`
only when `workflow_type === "patch"`.

# Model-call cache

Checks [the model-call cache](/architecture/model-call-cache.md) for an exact-match prompt
(hypothesis text + retrieved chunks) before calling the live gateway; `SpecialistResult.cache_hit`
records which happened. Only stores a response once it parses successfully.[^planner-py]

[^planner-py]: backend/agents/planner.py
