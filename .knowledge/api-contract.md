---
type: contract
title: API & Agent Contracts
status: draft
updated: 2026-08-07
related: [schema-db.md, domain-multimodal-intake.md, domain-agents.md, arch-overview.md]
---

**Canonical schemas per PRD §0 working method: freeze these at the end of Phase 1 and paste them
into every later request — they are the shared context across sessions. Flip `status: active` once frozen.**

## `MaintenanceSignal` — the one canonical intake object (PRD §2.4 D1, §3.5)
Produced identically by all three intake paths (alert HTTP, Whisper voice, Llama Vision image) so
everything downstream (scrubber, correlation, agents) shares one shape.
```json
{
  "signal_id": "SIG-0001",
  "modality": "alert | voice | image",
  "received_at": "ISO-8601",
  "raw_ref": "not persisted beyond the run — see domain-privacy.md",
  "extracted_text": "string, post-transcription/extraction, PRE-scrub",
  "candidate_ci_refs": ["CI-0087"],
  "candidate_alert_refs": ["ALERT-1043"],
  "confidence": 0.0,
  "requires_human_confirmation": true,
  "parsed_intent": "for voice only — closed-vocabulary intent, e.g. approve_x | show_incident | start_scenario"
}
```
Rule: the scrubber runs **after** modality conversion, **before** this object enters any workflow or
model call (PRD §1.5). Confirmation-before-action is mandatory for both voice and image paths.

## MCP tool contracts — one server per simulated system (PRD §3.5/§3.8)
Each of Monitoring / ITSM / Tracker / CMDB exposes typed tools over MCP, not bespoke HTTP. Minimum
tool set per server (exact request/response shapes are Phase 1 operational detail, fill in there):
- **Monitoring:** `list_alerts`, `get_metric_series(ci_id)`.
- **ITSM:** `create_ticket`, `update_ticket`, `add_work_note`, `get_ticket(sys_id)`.
- **Tracker:** `create_issue`, `link_issue`, `transition_issue`, `get_issue`.
- **CMDB:** `get_ci(id)`, `get_relationships(ci_id)`, `propose_ci_update` (human-approved before write).

## A2A — one handoff, real signed Agent Card (PRD §3.8, cuttable per decisions-log.md)
- Exactly **one** Supervisor→specialist handoff travels over A2A (pick the Diagnosis or
  Verification agent — decide in Phase 3, record the choice in [domain-agents.md](domain-agents.md)).
- Agent Card fields (minimum): `name`, `description`, `capabilities`, `endpoint`, `signature`.
- Everything else stays in-process with typed Python contracts, not A2A.

## Typed handoff contract — Supervisor ↔ specialist (in-process, PRD §3.4)
Every specialist returns a schema-validated result before the Supervisor dispatches the next agent:
```json
{
  "agent_name": "string",
  "incident_id": "string",
  "result": { "...specialist-specific payload..." },
  "cited_artifact_ids": ["must be non-empty for any claim"],
  "confidence": 0.0,
  "turns_used": 0,
  "termination_reason": "string — must be explicit, never implicit"
}
```

## Frontend ↔ backend
- Live updates via SSE (PRD §7 "Wire the live alert feed"). Endpoint shape TBD Phase 4 — record it here once decided, do not invent a second shape elsewhere.
- Auth: mock JWT (already working, see [state-progress.md](state-progress.md)), role claim drives the role switcher (server-side enforced, PRD §4.1).
