---
type: contract
title: API & Agent Contracts
status: active
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
**IMPLEMENTED 2026-08-07** as a pydantic model, `backend/orchestrator/contracts.py`
`MaintenanceSignal`. Voice path: `backend/intake/voice_path.py`. Image path:
`backend/intake/vision_path.py`. Both confirmed via tests to scrub before parsing/before the
signal is built. `backend/orchestrator/intake_adapter.py` bridges a *confirmed* signal into a
real Supervisor workflow run (enforces `requires_human_confirmation is False` before proceeding —
tested that an unconfirmed signal is rejected, not just documented as a rule).

## MCP tool contracts — one server per simulated system (PRD §3.5/§3.8)
Each of Monitoring / ITSM / Tracker / CMDB exposes typed tools over MCP, not bespoke HTTP.
**Implemented and verified 2026-08-07** — `backend/mcp_servers/{monitoring,itsm,tracker,cmdb}_mcp.py`
wrap `backend/mcp_servers/simulators/{monitoring,itsm,tracker,cmdb}.py` (ports 9001-9004) exactly
as specified below, self-tested end to end via `--test` (ASGI in-process, no real port needed):
- **Monitoring:** `list_alerts`, `get_metric_series(ci_id)`.
- **ITSM:** `create_ticket`, `update_ticket`, `add_work_note`, `get_ticket(sys_id)`.
- **Tracker:** `create_issue`, `link_issue`, `transition_issue`, `get_issue`.
- **CMDB:** `get_ci(id)`, `get_relationships(ci_id)`, `propose_ci_update` (records a proposal only —
  never mutates the CI directly; human approval step still TBD, not yet built).

## A2A — one handoff, real signed Agent Card (PRD §3.8, cuttable per decisions-log.md)
**IMPLEMENTED 2026-08-07** — Supervisor→Diagnosis, see [domain-agents.md](domain-agents.md) for
the full rationale. Actual Agent Card as implemented (`backend/a2a/agent_card.py`):
```json
{
  "name": "diagnosis-agent",
  "description": "Root-cause hypothesis generation & ranking (DeepSeek R1). Every hypothesis cites at least one evidence artifact ID; uncited hypotheses are dropped before being returned.",
  "capabilities": ["generate_diagnosis"],
  "endpoint": "http://localhost:9010/invoke",
  "signature": "<hex HMAC-SHA256 over the other 4 fields, canonical JSON, sorted keys>"
}
```
- Signature is a real HMAC-SHA256 (verifiable — `verify_agent_card()` rejects any tampered field),
  keyed by a local-only secret (`A2A_SECRET`) — **not** asymmetric/PKI signing; documented as a
  deliberate hackathon-scope simplification, not claimed to be more than it is.
- Discovery: `GET /.well-known/agent-card.json`. Invocation: `POST /invoke` with
  `{incident_id, evidence}`, returns a `SpecialistResult`.
- Everything else (Enrichment, Planner, Verification, Sync, Knowledge) stays in-process with typed
  Python contracts, not A2A.

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
  "termination_reason": "string — must be explicit, never implicit",
  "latency_ms": "float | null — set by the Supervisor's _timed() wrapper, not the agent itself",
  "tokens_used": "int | null — null means no LLM call, not \"unknown\"; only diagnosis/planner set this",
  "transport": "\"in_process\" | \"a2a\" — default in_process, Supervisor overrides for the diagnosis handoff"
}
```
**Extended 2026-08-07 (Phase 4 atomic step 3, Agent Trace Viewer)** — `latency_ms`/`tokens_used`/`transport`
added to `backend/orchestrator/contracts.py`. All optional/defaulted, so this is additive, not
breaking; re-ran the full diagnosis/planner/supervisor test suite (14/14) after the change.

## Frontend ↔ backend
- **`GET /alerts/stream`** (SSE, `?token=<JWT>` query param — browser `EventSource` can't set an
  Authorization header). Replays recent `alerts` table history, then polls every 3s for new rows.
  Each event: `data: {"id","source","raw_payload","received_at","modality"}`.
- **`GET /alerts/correlated`** (header `Authorization: Bearer <JWT>`). Runs the Phase 2 correlation
  engine live (`backend/correlation/cluster.py`, no LLM) and returns
  `{"total_alerts","total_clusters","noise_reduction_ratio","candidates":[{"cluster_id","topology_group","category","alert_count","alert_ids","representative_summary"}]}`.
- **`POST /workflows/run`** (header JWT). Body `{"ci_id","workflow_type","auto_approve"}`. Triggers a
  real Supervisor run and returns
  `{"incident_id","modality","status","reason","verification_status","trace":[SpecialistResult + "model_used"],"agent_card"}`
  — `model_used` is joined in from `audit_log` per handoff (not on `SpecialistResult` itself);
  `modality` is `"alert"` for this endpoint (added Phase 4 acceptance-criteria closure).
  Response shape built by the shared `_format_workflow_outcome()` helper in `main.py`.
- **`POST /workflows/decision`** (header JWT). Body `{"incident_id","decision":"approve"|"reject","reason"}`.
  Records a human decision to `audit_log` (`human_approve_plan`/`human_reject_plan`, reason in
  `approval_ref`) — does NOT resume the paused run (`run_workflow` has no checkpointing); the
  frontend separately re-triggers `/workflows/run` with `auto_approve=true` on approve.
- **`POST /intake/voice`** / **`POST /intake/image`** (header JWT, multipart `file`). Real
  Whisper/gpt-4o intake, return a `MaintenanceSignal` with `requires_human_confirmation` set —
  no workflow starts yet.
- **`POST /intake/confirm`** (header JWT). Body `{"signal": MaintenanceSignal, "workflow_type"}`.
  Forces `requires_human_confirmation=False` and calls `intake_adapter.start_workflow_from_confirmed_signal`
  — same response shape as `/workflows/run` (`modality` reflects the signal's, `"voice"`/`"image"`).
  400 on the two genuine validation errors (unconfirmed signal, no resolvable CI); 502 for anything
  else (e.g. a transient downstream gateway failure) — do not conflate the two, see `errors-solved.md`.
- **`GET /cmdb/drift`**, **`GET /autonomy-ladder`**, **`GET /chunks`**, **`GET /metrics/summary`**
  (all header JWT, read-only) — Drift Queue / Autonomy Ladder / Chunk Inspector / Metrics & Eval
  tab data sources respectively. See `state-progress.md` FILE INVENTORY for what each computes.
- Auth: mock JWT (already working, see [state-progress.md](state-progress.md)), role claim drives the role switcher (server-side enforced, PRD §4.1).
