---
type: Module
title: Policy Gate
description: Pure-Python, no-LLM rule engine deciding allow/needs_approval/block for a proposed action — change-freeze windows, blast radius, concurrent-change limits, required-approver role, and an absolute advisory-only rule for tuning workflows.
resource: backend/guardrails/policy_gate.py
tags: [guardrails, deterministic, policy]
status: stable
generated: { by: "claude-sonnet-5/okf-produce", at: "2026-08-11T00:00:00Z" }
sources:
  - id: policy-gate-py
    resource: backend/guardrails/policy_gate.py
    title: backend/guardrails/policy_gate.py
    last_modified: 2026-08-11
---

# Overview

`evaluate_policy(request, context) -> PolicyResult` is deterministic: the same request and context
always produce the same decision — auditable and provably consistent, which the guardrail
explicitly cannot be if any part of it goes through a model.[^policy-gate-py] Precedence: any BLOCK
rule wins outright; else any NEEDS_APPROVAL rule applies; else ALLOW.

# Rules

| Rule | Trigger | Decision |
|---|---|---|
| `FREEZE_WINDOW` | requested time falls inside a change-freeze window for that environment | block |
| `BLAST_RADIUS_BLOCK` | blast radius count exceeds the hard block threshold (default 15) | block |
| `MAX_CONCURRENT_CHANGES` | active prod changes >= the concurrent-change limit (default 3) | block |
| `BLAST_RADIUS_APPROVAL` | blast radius count exceeds the approval threshold (default 5) but not the block threshold | needs_approval |
| `ADVISORY_ONLY_WORKFLOW` | `action_type` is `tuning` | needs_approval, unconditionally — see below |
| `REQUIRED_APPROVER_ROLE` | prod or P1 action, actor role not in `{sre_lead, change_manager}` | needs_approval |

[^policy-gate-py]

# Tuning is never auto-executable

`ADVISORY_ONLY_ACTION_TYPES = {"tuning"}` is a hard rule inside the gate itself, not a UI
convention — Performance Tuning workflows always route through `needs_approval` regardless of how
low the blast radius or how senior the actor role, matching the
[Workflow Families](/workflows/workflow-families.md) parity table's "advisory only, never
auto-executes" row.

# Runtime-editable thresholds

The three numeric thresholds (`blast_radius_approval_threshold`, `blast_radius_block_threshold`,
`max_concurrent_changes_prod`) live in a module-level `_current_thresholds` dict, editable at
runtime via the admin-only Model & Threshold Config panel (`GET`/`POST /config/thresholds`).
Deliberately **in-memory only** — an admin's change takes effect immediately for subsequent runs in
this process but does not persist across a backend restart, the same "live status, no persistence"
simplification used for the autonomy ladder.[^policy-gate-py]

# Consumers

Called from [Planner Agent](/agents/planner-agent.md) after the LLM drafts a plan, never before or
during — the model never sees or influences the gate's inputs.

[^policy-gate-py]: backend/guardrails/policy_gate.py
