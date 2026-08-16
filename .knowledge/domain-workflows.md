---
type: domain
title: Domain — Three Workflow Families
status: active
updated: 2026-08-16
related: [domain-agents.md, schema-db.md, prd-phase-3.md]
---

From PRD §2.4 D7 and §1.2 clauses A1-A3. **Same agent chain, same guardrails, all three run because
the workflow is declarative data, not code (PRD B9) — do not build three separate code paths.**

## Problem restatement (PRD §1.1, do not rephrase)
IT maintenance teams repeat three classes of work by hand across tools that don't talk to each
other: patching, performance tuning, incident resolution. A coordinated agent team, each owning one
narrow step and handing off under supervision, turns the manual relay race into a repeatable,
auditable workflow from "signal received" to "ticket closed, CMDB updated, knowledge captured." The
prototype proves the *coordination*, not just the chat.

## Parity table (PRD §2.4, verbatim)
| | Incident Resolution | Patch Management | Performance Tuning |
|---|---|---|---|
| Trigger | Fault alert / voice / image | Patch inventory + schedule | Degradation alert (latency, memory creep, slow query) |
| Runbook class | `remediation` | `patching` | `tuning` |
| Key evidence | Alerts, logs, CI graph, past incidents | Patch inventory, dependencies, change calendar | Metric trend, query stats, resource history |
| Plan output | Remediation steps | Grouped maintenance window | Ranked tuning recommendations |
| Verification criterion | Alert cleared **and** health probe recovered | Patch applied **and** no new alerts in window | **Sustained metric improvement across a window** — not a binary clear |
| Autonomy tier | Up to auto-execute (ladder) | Approval required | **Advisory only — never auto-executes** |

**Performance tuning is deliberately advisory-only** — tuning changes are judgement calls with
delayed, ambiguous effects. This was a deliberate choice not to automate; state it as such if asked.

## Reference chain — incident resolution is the golden path (PRD §1.2 A3)
Correlate → Enrich → Diagnose → Plan → Gate → Approve → Execute → Verify → Sync → Knowledge. Patch and
performance derive from the same chain over different runbook classes and verification criteria.
Agent-level detail: [domain-agents.md](domain-agents.md).

## Build order (PRD §5 Phase 3)
Build incident first, then derive patch and performance workflow YAML from it. **If this derivation
is not nearly free, the declarative-workflow design assumption was wrong — surface that immediately,
do not silently fall back to hardcoded per-workflow code.**

**CONFIRMED 2026-08-07: the derivation WAS nearly free.** `backend/orchestrator/workflows/patch.yaml`
and `performance.yaml` differ from `incident.yaml` only in `runbook_class`, `verification_criterion`,
and `autonomy_tier` — same 10-step chain, same agents, same code. The Supervisor (`supervisor.py`)
and every agent are workflow-type-agnostic; `run_workflow(..., workflow_type="patch")` required zero
new code, only a new YAML file. Verified live: `backend/tests/test_supervisor.py` runs all 3
workflow types through the real agent chain, including confirming tuning's `advisory_only` tier
never reaches `allow` regardless of other factors (`policy_gate.py` `ADVISORY_ONLY_ACTION_TYPES`).

## Demo coverage (PRD §9 known risk)
One deep golden-path scenario (incident) shown fully live; patch and performance shown in compressed
form. Coverage proven by the eval dashboard and clause coverage map, not by three full live runs.

## Auto-triage trigger scope (session addition, not PRD-specified)
`frontend/src/hooks/useAutoTriage.js` auto-runs diagnosis for newly-arrived alerts, but deliberately
only those — the SSE stream's initial catch-up burst (the first `INITIAL_BACKLOG_SIZE`, currently 20,
matching `main.py`'s `_alert_event_stream` replay size) is explicitly excluded. This means: alerts
that arrive while a session is connected diagnose themselves one at a time; whatever backlog already
existed before that session opened does not, and needs a manual Diagnose / "Run all untriaged" click
on Ops Board. This is intentional (bounded, sequential auto-triage rather than an uncontrolled flood
of every historical alert on connect), surfaced in the Ops Board tab's own description
(`frontend/src/lib/tabInfo.js`) so it's not a silent behavior.
