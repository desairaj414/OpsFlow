---
type: Domain
title: Workflow Families — Incident, Patch, Performance Tuning
description: The same Supervisor + specialist agent chain and the same guardrails serve all three IT-ops workflow families, because the workflow is declarative YAML data, not three separate code paths.
tags: [domain, workflows]
status: stable
generated: { by: "claude-sonnet-5/okf-produce", at: "2026-08-11T00:00:00Z" }
sources:
  - id: domain-workflows
    resource: .knowledge/domain-workflows.md
    title: Domain — Three Workflow Families
    last_modified: 2026-08-07
  - id: incident-yaml
    resource: backend/orchestrator/workflows/incident.yaml
    title: backend/orchestrator/workflows/incident.yaml
    last_modified: 2026-08-07
---

# Parity table

| | Incident Resolution | Patch Management | Performance Tuning |
|---|---|---|---|
| Trigger | Fault alert / voice / image | Patch inventory + schedule | Degradation alert (latency, memory creep, slow query) |
| Runbook class | `remediation` | `patching` | `tuning` |
| Key evidence | Alerts, logs, CI graph, past incidents | Patch inventory, dependencies, change calendar | Metric trend, query stats, resource history |
| Plan output | Remediation steps | Grouped maintenance window | Ranked tuning recommendations |
| Verification criterion | Alert cleared **and** health probe recovered | Patch applied **and** no new alerts in window | Sustained metric improvement across a window — not a binary clear |
| Autonomy tier | Up to auto-execute (ladder) | Approval required | **Advisory only — never auto-executes** |

[^domain-workflows]

Performance tuning is deliberately advisory-only: tuning changes are judgement calls with delayed,
ambiguous effects, so this is a considered choice not to automate rather than a scope cut. Encoded
as a hard rule in [Policy Gate](/guardrails/policy-gate.md), not left to a UI convention.

# One chain, three YAML files

`backend/orchestrator/workflows/{incident,patch,performance}.yaml` each declare the same 10-step
chain (`correlate, enrichment, diagnosis, planner, policy_gate, approval, execute, verification,
sync, knowledge`) and differ **only** in `runbook_class`, `verification_criterion`, and
`autonomy_tier`.[^incident-yaml] Incident Resolution is the reference chain, built first; Patch
Management and Performance Tuning are derived from it. This derivation being nearly free (a new
YAML file, zero new [Supervisor](/agents/supervisor.md) or agent code) was the confirmation that the
declarative-workflow design assumption held — the explicit fallback plan, had it not been nearly
free, was to surface that as a design-assumption failure rather than silently hand-writing three
separate code paths.[^domain-workflows]

# What actually differs at runtime

[Enrichment Agent](/agents/enrichment-agent.md) takes a `workflow_type` parameter and only gathers
patch-inventory/change-calendar evidence for `workflow_type == "patch"`.
[Planner Agent](/agents/planner-agent.md) only computes a maintenance window
(`guardrails/scheduling.py`) when `runbook_class == "patching"`. Everything else in the chain
(Diagnosis, the policy gate's rule set, Verification's structure, Sync, Knowledge) runs unchanged
across all three families.

[^domain-workflows]: Domain — Three Workflow Families
[^incident-yaml]: backend/orchestrator/workflows/incident.yaml
