---
type: rules
title: Frontend Rules & Commenting Standard
status: active
updated: 2026-08-16
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

## Actual final component list (post-Phase-4, current — CONTEXT CHECKPOINT)
`frontend/src/components/{AgentTrace,AutonomyLadder,ChatWidget,ChunkInspector,CockpitShell,
DriftQueue,IncidentWorkspace,LoginModeSelector,Logo,NotificationBell,OpsBoard,Overview,Sidebar,
Tickets}.jsx` + `panels/{AuditLogPanel,ModelThresholdConfigPanel,ScenarioLauncherPanel,
UserManagementPanel}.jsx` + `ui/{badge,button,card,input,modal}.jsx`. `ApprovalQueue.jsx` and
`MetricsEval.jsx` from the original Phase 4 plan no longer exist under those names — that
functionality folded into `IncidentWorkspace`/`Overview`. Post-Phase-4 additions, one phrase each:
- **`ChatWidget`** — floating chat assistant (text/voice/image input); see the "Chat assistant"
  section below.
- **`LoginModeSelector`** — 3-mode public demo login picker; see the section below.
- **`Overview`** — landing dashboard tab, absorbed former `MetricsEval` metric displays.
- **`NotificationBell`** — header alert/notification dropdown.
- **`Tickets`** — standalone tickets list/detail view.
- **`panels/`** — admin/config surfaces split out of `Sidebar`: audit log, model/threshold config,
  scenario launcher, user management.

Two deviations from the original Phase 4 plan (`prd-phase-4.md`'s atomic-step file list), both load-bearing:
- **`CockpitShell` owns one shared `useWorkflowRun` instance** (a "golden-path bar": CI-scenario
  dropdown + "Start incident"), passed as an `incident` prop to Agent Trace/Incident Workspace/Ops
  Board's image path, instead of each tab triggering its own separate run. Not in the original
  per-tab-independent plan — added so a single incident is followably consistent across tabs,
  which the acceptance criteria's "golden path... clickable start to finish" needed.
- **Push-to-talk is real**, not a stub, but as of the 2026-08-08 chat-drawer reversal (see below)
  it lives in `ChatWidget`'s mic button, not `Sidebar` — `Sidebar`'s standalone push-to-talk was
  removed entirely. It records via `MediaRecorder`, posts to `POST /intake/voice`, and the
  resulting transcript is handled as an ordinary chat message through the same `/chat` pipeline
  (one pipeline, not two parsers).

## UI structure to build toward (PRD §7 — cockpit, not chat-first)
Centrepiece is the **Agent Trace Viewer**, not a results panel — coordination must be visible
(handoffs, scrubbed prompts, model, tokens, latency, validation result, modality, transport
in-process-vs-A2A). The original PRD §7 design deliberately cut a chat drawer in favour of voice
as the sole conversational modality; that call was **reversed 2026-08-08** ("REVERSES the §4.0
'cut scoped chat drawer' decision" in [decisions-log.md](decisions-log.md)) once it could be built
without reintroducing the risk the cut was meant to avoid — see the "Chat assistant" section below.

Tabbed workspace: Ops Board · Incident Workspace (+ Maintenance Planner panel) · Agent Trace ·
Drift Queue (+ Drift-vs-Truth split screen) · Autonomy Ladder · Chunk Inspector · Overview.
Sidebar: role switcher, ingestion/admin, model & threshold config, scenario launcher, audit log
(push-to-talk moved out of Sidebar into ChatWidget's mic button, see below). Full detail:
[prd-phase-4.md](prd-phase-4.md) (historical plan — component list above reflects current reality).

## Accessibility — mandatory, not optional (PRD §7)
Every voice action has keyboard parity. Focus states visible. Confirmation step before any
voice-initiated action is mandatory, not a preference — claiming accessibility and shipping
mouse-only would be worse than not claiming it.

## Design principles (PRD §7)
- Confidence always visible with its evidence basis.
- Nothing AI-generated shares the visual register of verified fact — use the three-badge system above.
- Every number click-throughs to its source artifact ID.
- Refusals displayed as prominently as successes.

## Chat assistant (`ChatWidget.jsx`, `POST /chat`) — added 2026-08-08
Floating assistant with text/voice/image input, deliberately built to preserve the same
LLM-proposes/code-executes split as the rest of the app rather than becoming a freeform advisor:
ticket/incident answers come from a real deterministic DB query (the LLM only extracts filters,
never writes SQL); approve/reject reuses the exact same audited, reason-required, role-gated
`/workflows/decision` path Incident Workspace's own approval section uses; voice input transcribes
through the same real Whisper+scrubber pipeline as before (`/intake/voice`). See
[decisions-log.md](decisions-log.md) (2026-08-08 entry) for the full rationale and rejected
alternatives.

## Public demo login (`LoginModeSelector.jsx`)
Visitors without TCS network access or a corporate key pick one of 3 modes: **Instant Demo**
(always works, no key needed), **Bring Your Own Key** (visitor supplies their own provider key),
**Free Demo Key** (shared rate-limited key). This is a currently-shipped, major piece of frontend
UX — touch `LoginModeSelector.jsx` or its downstream auth/session wiring only after reading
`.okf/demo-modes/public-hosting-modes.md` for the full mode contract; not duplicated here.

## Mobile-responsive convention (standing pattern, apply consistently)
- **Mobile-first Tailwind**: unprefixed classes are the mobile base; `sm:`/`md:`-prefixed classes
  override at that breakpoint and up. Do not write desktop-first with a mobile override.
- **No native `<select>`** for anything styled — mobile browsers render native selects as
  uncontrollable full-screen pickers that break the cockpit's visual register. Use a custom
  button+listbox component instead.
- **Floating/absolute-positioned panels** (dropdowns, popovers, the chat widget) use `fixed` +
  viewport-relative positioning below the `sm:` breakpoint, and switch to `absolute`-anchored
  positioning at `sm:` and above.

## Where to look before writing frontend code
- Canonical `MaintenanceSignal` and API response shapes: [api-contract.md](api-contract.md).
- Component list and demotion order if Phase 4 runs long: [prd-phase-4.md](prd-phase-4.md).
