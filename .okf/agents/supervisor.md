---
type: Module
title: Supervisor
description: The dispatch loop that runs one workflow — calls each specialist in order, re-validates its typed result, enforces the policy gate and human-approval pause, and writes every step to the audit log.
resource: backend/orchestrator/supervisor.py
tags: [orchestration, agents]
status: stable
generated: { by: "claude-sonnet-5/okf-produce", at: "2026-08-11T00:00:00Z" }
sources:
  - id: supervisor-py
    resource: backend/orchestrator/supervisor.py
    title: backend/orchestrator/supervisor.py
    last_modified: 2026-08-08
  - id: domain-agents
    resource: .knowledge/domain-agents.md
    title: Domain — Agent Chain & Orchestration
    last_modified: 2026-08-07
---

# Overview

`run_workflow(incident_id, ci, alerts, workflow_type, actor_role, auto_approve)` is the one entry
point that runs a full incident/patch/performance-tuning workflow. It loads a declarative workflow
YAML (see [Workflow Families](/workflows/workflow-families.md)), then calls specialists in a fixed
order, wrapping each in `_timed()` so the [Agent Trace Viewer](/architecture/cockpit-ui.md) gets
real latency/transport data, and re-validates every result via `SpecialistResult.model_validate()`
before trusting it — the way it would have to if a specialist crossed a real process boundary.[^supervisor-py]

# Chain order

Correlate (audit marker only — the real DBSCAN correlation ran earlier, see
[Model Routing](/architecture/model-routing.md)) -> [Enrichment](enrichment-agent.md) ->
[Diagnosis](diagnosis-agent.md) (the one [A2A handoff](a2a-handoff.md)) ->
[Planner](planner-agent.md) (computes blast radius + policy gate internally) -> **Approval** (human
decision point, not code) -> **Execute** (audit-log-only; no real script execution) ->
[Verification](verification-agent.md) -> [Sync](sync-agent.md) -> [Knowledge](knowledge-agent.md).

Steps that are NOT separate schema-validated specialists: `correlate` (the Supervisor receives an
already-clustered alert group), `policy_gate` (computed inside Planner's result), `approval` (a
human decision — the workflow returns `status: "pending_approval"` and pauses unless
`auto_approve=True`), `execute` (Supervisor-internal audit entry only).[^supervisor-py]

# Early exits

The workflow can stop before completion at several points, each with an explicit
`status`/`reason`: `stopped`/`enrichment_failed` (no evidence gathered or turn cap hit),
`stopped`/`no_valid_hypotheses` (Diagnosis returned nothing citable), `blocked`/`<policy reasons>`
(the policy gate hard-blocked), or `pending_approval` (needs a human decision and
`auto_approve` wasn't set).

# Two levels only

Specialists never call each other directly — every specialist returns a typed `SpecialistResult`
(see `backend/orchestrator/contracts.py`) to the Supervisor, which validates it against the schema
before dispatching the next agent.[^domain-agents] See
[Two-Level Supervisor](/decisions/two-level-supervisor.md) for why this topology was chosen over a
deeper hierarchy or a free agent mesh.

# Turn caps

Every specialist uses a `TurnTracker` (`backend/orchestrator/limits.py`) with a per-agent hard cap
(enrichment 3, diagnosis 3, planner 2, verification 2, sync 1, knowledge 1). Exceeding the cap
raises `TurnCapExceeded`, which the agent must catch and return as an explicit
`termination_reason` — never let it propagate as an unhandled crash. This encodes an external
finding that more agent turns are not reliably better.

[^supervisor-py]: backend/orchestrator/supervisor.py
[^domain-agents]: Domain — Agent Chain & Orchestration
