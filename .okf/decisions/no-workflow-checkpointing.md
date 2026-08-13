---
type: Decision
title: No Workflow Checkpointing — Approval Re-Runs Fresh
description: run_workflow has no persisted intermediate state. Approving a paused plan in the Approval Queue re-runs the same CI fresh with auto_approve=true, rather than resuming the exact paused run — labeled honestly in the UI as a new run, not a true resume.
tags: [architecture, workflow, honesty]
status: stable
generated: { by: "claude-sonnet-5/okf-produce", at: "2026-08-11T00:00:00Z" }
sources:
  - id: decisions-log
    resource: .knowledge/decisions-log.md
    title: Decisions Log
    last_modified: 2026-08-07
  - id: supervisor-py
    resource: backend/orchestrator/supervisor.py
    title: backend/orchestrator/supervisor.py
    last_modified: 2026-08-08
---

# Decision

[Supervisor](/agents/supervisor.md)'s `run_workflow` is a single straight-through async call with no
persisted intermediate state. `POST /workflows/decision` records the human approve/reject decision
to the audit log but does **not** resume the paused run — approving in the UI triggers a completely
new `POST /workflows/run` for the same CI with `auto_approve=true`, producing a new `incident_id`.[^decisions-log]

# Alternatives considered

Build real checkpointing — persist evidence/diagnosis/plan and resume from the exact pause point
(more faithful to a true "pending approval, then continue" model, but a substantial
`orchestrator/supervisor.py` refactor). Or, at the other extreme, record the approve/reject decision
only, without triggering any execution at all.[^decisions-log]

# Rationale

Chosen as the simplest option that still lets an approved plan actually execute end-to-end, given
the scope/time tradeoff of building real workflow-resume machinery. Because a fresh run means a
fresh Diagnosis call, the re-run's plan can in principle differ from what was originally approved —
this is a real, acknowledged limitation, not a cosmetic one.[^decisions-log]

# Consequence

`main.py`'s `_persist_ticket_snapshot()` has to specifically detect and update an existing
`needs_approval`-status `local_tickets` row (matched on `cmdb_ci`) rather than blindly inserting a
new one on every re-run — otherwise an approval would orphan the original pending ticket
permanently at `needs_approval` while a second, unrelated-looking row captured the real outcome.
The UI is expected to label this honestly as "a new run," never presented as a true resume of the
original one.

[^decisions-log]: Decisions Log
[^supervisor-py]: backend/orchestrator/supervisor.py
