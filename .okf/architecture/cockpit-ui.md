---
type: System
title: Cockpit UI
description: The Next.js frontend — tab structure, the Agent Trace Viewer centerpiece, the three-badge trust system, the floating chat assistant, and accessibility requirements.
tags: [frontend, ui]
status: stable
generated: { by: "claude-sonnet-5/okf-maintain", at: "2026-08-16T00:00:00Z" }
sources:
  - id: rules-frontend
    resource: .knowledge/rules-frontend.md
    title: Frontend Rules & Commenting Standard
    last_modified: 2026-08-07
  - id: decisions-log
    resource: .knowledge/decisions-log.md
    title: Decisions Log
    last_modified: 2026-08-07
---

# Overview

The cockpit is explicitly a coordination-visibility tool, not a results panel or a chat-first
interface — its centerpiece is the **Agent Trace Viewer**, not a summary card.[^rules-frontend]
Coordination between agents (handoffs, scrubbed prompts, model used, tokens, latency, validation
result, modality, in-process-vs-A2A transport) is meant to be visibly inspectable, not hidden
behind a single "done" state.

# Tab structure

`frontend/src/components/`: `CockpitShell` (shell + shared `useWorkflowRun` instance so one
incident stays consistent across tabs), `Overview` (KPI dashboard, see
[Overview Metrics](overview-metrics.md)), `OpsBoard` (live alert feed + click-to-diagnose),
`IncidentWorkspace` (evidence/diagnosis/plan/approval for one incident, plus a Maintenance Planner
panel for patch workflows), `AgentTrace`, `Tickets`, `ChunkInspector` (doubles as the Knowledge
Base browser), `AutonomyLadder`, `ChatWidget` (floating assistant, including the mic — push-to-talk moved out of
`Sidebar` into `ChatWidget`'s mic button, see [Decisions](/decisions/)), `Sidebar` (admin-only "view
as" impersonation control, not a general role switcher; admin panels), `NotificationBell`,
`DriftQueue` (currently hidden from navigation, not deleted).

# Three-badge trust system

Nothing AI-generated shares the visual register of verified fact: an "AI proposed" / "human
approved" / "system verified" badge distinguishes provenance on every claim, so a reviewer never
has to guess whether a number on screen came from a model, a human decision, or a deterministic
check.[^rules-frontend] Every number click-throughs to its source artifact ID.

# Floating chat assistant

Reverses an earlier "no chatbot" decision (voice was originally meant to be the sole conversational
modality) — see [Decisions](/decisions/) for the full reversal record.[^decisions-log] The chat's
intent classifier is the only LLM call in the widget; everything the classifier's intent triggers
is deterministic (`query_tickets` runs a real parameterized SQL query, never model-invented
numbers; `approve_incident`/`reject_incident` reuses the exact same audited, role-gated
`/workflows/decision` path Incident Workspace's own approval section uses). Voice input in the
widget transcribes through the same real Whisper + scrubber pipeline as
[Voice Intake](/intake/voice-intake.md) — one pipeline, not two parsers. Image upload uses the same
[Vision Intake](/intake/vision-intake.md) flow.

# Provider mode selection

`LoginModeSelector.jsx`, rendered below the credentials form on the login screen, is the mode-
selector UI for the 3 [demo modes](/demo-modes/) — see [Public Hosting Modes](/demo-modes/public-hosting-modes.md)
for the full mode-card/BYOK-panel/role-quick-fill breakdown. The login screen also carries a
light/dark theme toggle (reuses the same `useTheme()` hook post-login screens already had), so a
visitor's theme preference applies before signing in, not just after.

# Responsive layout

Mobile-first Tailwind throughout: unprefixed classes are the mobile base, `sm:`/`md:`-prefixed
classes override at that breakpoint up. `Sidebar` renders as a permanent column at `md:` and above;
below that it's a full-screen slide-in drawer (`mobileOpen`/`onMobileClose` props), opened via a
hamburger button in the header. Native `<select>` elements were replaced with custom button+listbox
dropdowns (e.g. `Sidebar.jsx`'s "View as" control) since mobile browsers render native selects as
full-screen OS pickers with no CSS control. `IncidentWorkspace.jsx`'s agent-chain `FlowPipeline`
stacks into full-width cards with down-arrows below `sm:`, row-with-right-arrows above it.
Floating/absolute-positioned panels (`ChatWidget.jsx`, `NotificationBell.jsx`) switch from
viewport-relative `fixed` positioning below `sm:` to their original `absolute`-anchored positioning
above it, since a panel anchored to a small wrapper's `right-0` can render off-screen on a narrow
viewport otherwise.

# Accessibility

Mandatory, not optional: every voice action has keyboard parity, focus states are visible, and a
confirmation step before any voice-initiated side-effecting action is required — claiming
accessibility while shipping mouse-only interaction would be worse than not claiming it at
all.[^rules-frontend]

[^rules-frontend]: Frontend Rules & Commenting Standard
[^decisions-log]: Decisions Log
