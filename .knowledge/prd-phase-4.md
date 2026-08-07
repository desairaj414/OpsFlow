---
type: phase
title: "Phase 4 — Cockpit UI"
status: draft
updated: 2026-08-07
related: [rules-frontend.md, api-contract.md, domain-workflows.md, prd-phase-5.md]
---

**Duration ~3.5h · H+11:30–15:00 · Fri 20:30–Sat 00:00.**
⚠ **Most likely place the plan breaks** (per PRD §5). Pre-agreed demotion order below — use it,
don't improvise a different cut under pressure. Owner: **Person F — Frontend/UI.**

## Atomic steps
1. *(30 min)* Base layout: sidebar (role switcher, mic button, ingestion/admin, model & threshold config, scenario launcher, audit log) + tabbed workspace shell + SSE wiring to the live alert feed. Files: `frontend/src/App.jsx`, `frontend/src/components/Sidebar.jsx`.
2. *(40 min)* Ops Board tab: live alert feed (left) + correlated candidates (right) + noise-reduction-ratio headline number + image drop zone. Files: `frontend/src/components/OpsBoard.jsx`.
3. *(45 min, highest priority)* Agent Trace Viewer — handoffs, scrubbed prompt, model, tokens, latency, validation result, modality, transport (in-process vs A2A, Agent Card viewable), Replay button. Files: `frontend/src/components/AgentTrace.jsx`.
4. *(35 min)* Incident Workspace: Unified Incident Record (evidence w/ citations incl. `IMG-nnn`, ranked hypotheses w/ confidence + "could not verify" block, plan w/ blast radius + Negative-KB caution, linked ITSM/tracker/CI side by side with contradictions highlighted) + Maintenance Planner panel. Files: `frontend/src/components/IncidentWorkspace.jsx`.
5. *(30 min)* Approval Queue — recommendation + counter-hypothesis + evidence gaps; approve/edit/reject with mandatory reason; **approvable by voice with on-screen confirmation**. Files: `frontend/src/components/ApprovalQueue.jsx`.
6. *(30 min)* Drift Queue + Drift-vs-Truth split screen. Files: `frontend/src/components/DriftQueue.jsx`.
7. *(20 min)* Autonomy Ladder panel — **static status display, not a live promotion engine** (per PRD §4.0 trade ledger). Files: `frontend/src/components/AutonomyLadder.jsx`.
8. *(20 min)* Chunk Inspector + Metrics & Eval dashboard. Files: `frontend/src/components/{ChunkInspector,MetricsEval}.jsx`.

## Files created/modified
`frontend/src/components/{Sidebar,OpsBoard,AgentTrace,IncidentWorkspace,ApprovalQueue,DriftQueue,AutonomyLadder,ChunkInspector,MetricsEval}.jsx`, `frontend/src/App.jsx`.

## [MOCK-P1] markers
- Autonomy Ladder is a static status panel, not a live promotion engine (deliberate scope cut, see [decisions-log.md](decisions-log.md)).

## Pre-agreed demotion order if this phase runs long (use this, don't improvise)
1. Chunk Inspector → static screenshot (never dropped entirely)
2. Autonomy Ladder → static (already scoped static; if still tight, reduce to a single summary line)
3. Metrics dashboard → single summary card instead of the full panel

## Hard acceptance criteria (re-verify by someone who did NOT build it)
- [ ] The golden path (incident scenario) is clickable start to finish by a teammate unfamiliar with the code
- [ ] Agent Trace Viewer shows a real completed run with all required fields (model, tokens, latency, modality, transport)
- [ ] A voice-approved action shows the parsed intent on screen before it commits
- [ ] An image dropped into the Ops Board reaches the Incident Workspace as a cited `IMG-nnn` artifact after confirmation
- [ ] Drift-vs-Truth split screen visibly shows at least one CI where recorded ≠ ground truth
- [ ] Every AI-generated element is visually distinct from human-approved/system-verified (three-badge system, PRD §7)
- [ ] SSE live feed updates the Ops Board without a manual refresh

## CONTEXT CHECKPOINT — update on completion
- [.knowledge/state-progress.md](state-progress.md) — CURRENT PHASE → Phase 5, DONE list, note any demotions actually applied
- [.knowledge/rules-frontend.md](rules-frontend.md) — record final component file list if it changed from the plan
- [.knowledge/api-contract.md](api-contract.md) — record the final SSE endpoint shape used
