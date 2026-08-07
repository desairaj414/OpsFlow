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

## Stack note — unresolved conflict, flag, do not silently resolve
PRD §0 specifies **Next.js + shadcn/ui**. The repo currently has a working **Vite/React + shadcn/ui +
Tailwind** app (`frontend/`, see `App.jsx`, `Dashboard.jsx`, `AdminControl.jsx`, `ui/*`). This is a
real conflict between a frozen product decision and existing working code — see KNOWN ISSUES in
[state-progress.md](state-progress.md). Do not migrate frameworks or decide to keep Vite without the
human explicitly saying so; this is not an operational detail this conversion is allowed to fill in.

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
