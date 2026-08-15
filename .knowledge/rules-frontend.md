---
type: rules
title: Frontend Rules & Commenting Standard
status: active
updated: 2026-08-07
related: [rules-backend.md, api-contract.md, domain-multimodal-intake.md]
---

**Re-read this on every coding step. It is a standing rule, not a one-time reminder.**
(Deliberately duplicated from [rules-backend.md](rules-backend.md) per the conversion spec — this
one node must be self-contained for anyone working frontend-only.)

## Code commenting standard (PRD §0 — Handbook §8.5 grades this, verbatim)
- Every React component: **one short purpose comment** (what it is for, not what each line does).
- Inline comments explain **WHY**, reserved for non-obvious logic: e.g. why a voice action requires
  on-screen confirmation before firing, why confidence badges use a specific colour threshold, why
  a citation click-through resolves to a specific artifact route.
- **No line-by-line narration of obvious JSX.** `{/* render the button */}` is worse than no comment.
- One responsibility per component; extract a sub-component rather than growing one file past ~200 lines.

## Honesty rule — non-negotiable (PRD §0)
Never render copy implying the system was fine-tuned. "AI proposed" / "human approved" / "system
verified" badges (PRD §7) must never blur into implying model training occurred.

## Stack note — RESOLVED 2026-08-07
Migrated to Next.js 16.3.0 (App Router, Tailwind v4, Turbopack) per PRD §0 in Phase 4. The old Vite
app was kept at `frontend_vite_backup/` as a rollback path during the migration; deleted 2026-08-15
once the Next.js frontend had been live, deployed, and repeatedly verified for over a week — no
longer needed. See [decisions-log.md](decisions-log.md) for the decision record and
[state-progress.md](state-progress.md) for the migration detail.

## Actual final component list (Phase 4, complete — CONTEXT CHECKPOINT)
`frontend/src/components/{Sidebar,CockpitShell,OpsBoard,AgentTrace,IncidentWorkspace,ApprovalQueue,
DriftQueue,AutonomyLadder,ChunkInspector,MetricsEval}.jsx` + `ui/{button,card,input,badge}.jsx`.
Two deviations from the original plan (`prd-phase-4.md`'s atomic-step file list), both load-bearing:
- **`CockpitShell` owns one shared `useWorkflowRun` instance** (a "golden-path bar": CI-scenario
  dropdown + "Start incident"), passed as an `incident` prop to Agent Trace/Incident
  Workspace/Approval Queue/Ops Board's image path, instead of each tab triggering its own separate
  run. Not in the original per-tab-independent plan — added so a single incident is followably
  consistent across tabs, which the acceptance criteria's "golden path... clickable start to
  finish" needed.
- **`Sidebar`'s push-to-talk is real**, not a stub: records via `MediaRecorder`, posts to
  `POST /intake/voice`, shows the parsed intent + transcript on screen, and only `approve_x`/
  `reject_x` are wired to an action (the other 4 closed-vocabulary intents are recognized and
  shown honestly, not faked, since no incidents-list/scenario-library endpoint exists to act on
  them with).

## UI structure to build toward (PRD §7 — cockpit, not chat-first)
Centrepiece is the **Agent Trace Viewer**, not a results panel or a chat drawer — coordination must
be visible (handoffs, scrubbed prompts, model, tokens, latency, validation result, modality,
transport in-process-vs-A2A). Voice commands are the conversational modality; there is deliberately
no chat drawer (cut per [decisions-log.md](decisions-log.md) trade ledger).

Tabbed workspace: Ops Board · Incident Workspace (+ Maintenance Planner panel) · Agent Trace ·
Approval Queue · Drift Queue (+ Drift-vs-Truth split screen) · Autonomy Ladder · Chunk Inspector ·
Metrics & Eval. Sidebar: role switcher, push-to-talk mic button with parsed-intent confirmation,
ingestion/admin, model & threshold config, scenario launcher, audit log. Full detail: [prd-phase-4.md](prd-phase-4.md).

## Accessibility — mandatory, not optional (PRD §7)
Every voice action has keyboard parity. Focus states visible. Confirmation step before any
voice-initiated action is mandatory, not a preference — claiming accessibility and shipping
mouse-only would be worse than not claiming it.

## Design principles (PRD §7)
- Confidence always visible with its evidence basis.
- Nothing AI-generated shares the visual register of verified fact — use the three-badge system above.
- Every number click-throughs to its source artifact ID.
- Refusals displayed as prominently as successes.

## Where to look before writing frontend code
- Canonical `MaintenanceSignal` and API response shapes: [api-contract.md](api-contract.md).
- Component list and demotion order if Phase 4 runs long: [prd-phase-4.md](prd-phase-4.md).
