---
type: state
title: State & Progress
status: active
updated: 2026-08-07
related: [decisions-log.md, state-progress-history.md, prd-phase-0.md, prd-phase-1.md, prd-phase-2.md, prd-phase-3.md, prd-phase-4.md, env-network.md]
---

## CURRENT PHASE
**Phase 0 — DONE.** See [PHASE0_FINDINGS.md](../PHASE0_FINDINGS.md) (repo root).
**Phase 1 — DONE.** Data, Simulated Systems & MCP Layer. See [prd-phase-1.md](prd-phase-1.md).
**Phase 2 — DONE.** Deterministic Core (no LLM), 44/44 unit tests green. See [prd-phase-2.md](prd-phase-2.md).
**Phase 3 — DONE. DEMO-COMPLETE CHECKPOINT REACHED (H+4:19, ahead of the H+11:30 schedule anchor).**
Agent Chain, Supervisor, A2A & Multimodal Intake — all 14 atomic steps (both tracks) complete,
84/84 backend tests green (44 Phase 2 + 40 Phase 3). See [prd-phase-3.md](prd-phase-3.md) for the
full acceptance-criteria checklist. **Human confirmed end-to-end at H+5:48** after a live re-run of
the full suite (84/84, 136.85s, real gateway calls) plus isolated re-runs of two tests that showed
transient gateway/proxy flakiness under sustained load in the first attempt (see KNOWN ISSUES) —
gate satisfied, not just taken on the test suite's prior word.
**Phase 4 — Cockpit UI — DONE**, H+5:48 to H+8:56. See [prd-phase-4.md](prd-phase-4.md). Next.js
migration complete; all 8 PRD §7 tabs built (Ops Board, Incident Workspace, Agent Trace, Approval
Queue, Drift Queue, Autonomy Ladder, Chunk Inspector, Metrics & Eval); all 7 hard acceptance
criteria closed (golden path, Agent Trace fields incl. modality, real voice approval, real
image→IMG-nnn citation, three-badge system, SSE live feed, Drift-vs-Truth split screen) — see
LAST VERIFIED STEP below for the full closure record. CONTEXT CHECKPOINT done (`api-contract.md`,
`rules-frontend.md` both updated). **Human confirmed Phase 4 complete at H+8:59**, satisfied to
start Phase 5 in a fresh session.
**Phase 5 — Scenario Library, Eval & Hardening — NOT STARTED.** See [prd-phase-5.md](prd-phase-5.md)
— **not yet read this session**, read it fresh before starting any Phase 5 work.

## H+ HOURS ELAPSED
H+8:59 as of Fri 2026-08-07 17:59 (handover was Fri 09:00). Schedule anchors: demo-complete
checkpoint Fri 20:30 (H+11:30) — **reached early, human-confirmed**; FEATURE FREEZE Sat 09:30 (H+24:30, hard);
SUBMISSION Sat 11:00 (H+26:00, hard). Full per-phase clock table in [prd-phase-0.md](prd-phase-0.md)
through [prd-phase-7-final.md](prd-phase-7-final.md). Phases 1-3's combined ~10.5h budget
(H+1:30-11:30) was compressed to ~2.5h of wall-clock work this session (AI-assisted, single
operator) — running well ahead of the phase clock. **Do not let this pace set false expectations**
for Phase 4 (UI/frontend work, a different kind of effort) or for the human's own review time,
which this compressed pace does not substitute for.

## LAST VERIFIED STEP — Next.js migration + Phase 4 atomic steps 1-2
Moved to [state-progress-history.md](state-progress-history.md) (scaffold, base layout, Ops Board
full build — all closed and superseded by later steps, not live detail anymore).

## LAST VERIFIED STEP — Phase 4 atomic step 3 (Agent Trace Viewer)
Moved to [state-progress-history.md](state-progress-history.md) — contract extension +
`POST /workflows/run` + `AgentTrace.jsx` + the min-h-screen/flex-min-w-0 layout bug fix.

## LAST VERIFIED STEP — Phase 4 atomic steps 5-8
Moved to [state-progress-history.md](state-progress-history.md) — Approval Queue (original
text-only version, later rebuilt), Drift Queue (35.0% drift rate matched exactly), Autonomy Ladder
(table seeded, was empty), Chunk Inspector + Metrics & Eval (real session aggregates). All 8
`prd-phase-4.md` atomic-step tabs built as of H+8:04.

## LAST VERIFIED STEP — Phase 4 acceptance-criteria closure (golden path, badges, voice, image)
Went through `prd-phase-4.md`'s hard acceptance criteria line by line against the 8 built tabs;
3 real gaps + 1 partial were found and closed (human said "build everything, including voice/image
intake wiring" when asked how deep to go):
- **Modality field**: `_format_workflow_outcome()` helper (factored out of `/workflows/run`, now
  shared with `/intake/confirm`) adds `modality` to every run response; shown in Agent Trace +
  Incident Workspace headers.
- **Three-badge system**: new `ui/badge.jsx` — violet "AI-proposed" (diagnosis/planner, the only
  LLM-calling agents), blue "System-verified" (enrichment/verification/sync/knowledge, deterministic),
  green/red "Human-approved"/"Human-rejected" (Approval Queue decisions). Applied across
  IncidentWorkspace, AgentTrace, ApprovalQueue.
- **Golden-path continuity**: `useWorkflowRun` lifted to `CockpitShell` as one shared `incident`
  state, with a new golden-path bar (CI-scenario dropdown + "Start incident") visible on every tab.
  Agent Trace / Incident Workspace / Approval Queue all read the SAME run instead of each triggering
  their own on different CIs. Approving still re-runs fresh (no checkpointing, per the step-5
  architecture decision) but now updates the shared state, so other tabs reflect it immediately.
- **Image → IMG-nnn citation (real, not mocked)**: `POST /intake/image` (real gpt-4o extraction) +
  `POST /intake/confirm` (bridges a confirmed `MaintenanceSignal` into a real run via
  `intake_adapter.start_workflow_from_confirmed_signal`, extended to also return its generated
  `incident_id` — additive, reran `test_intake_adapter.py`/`test_voice_path.py`/`test_vision_path.py`,
  8/8 no regression). `OpsBoard.jsx`'s drop zone now actually uploads, shows extracted text +
  candidate CI, requires an explicit "Confirm and start incident" click. Verified live: `CI-0056`
  (no pre-existing alerts) → synthesized `ALERT-FROM-IMG-xxxxx` evidence artifact, genuinely cited,
  run completes. Added `frontend/public/sample-incident-screenshot.png` for easy testing.
- **Voice approval with on-screen confirmation (real, not mocked)**: `POST /intake/voice` (real
  Whisper). First built scoped to Approval Queue only — **human caught this was wrong**: the PRD's
  actual "push to talk" is a global Sidebar control, not a tab-local one. Rebuilt: `Sidebar.jsx` now
  has the real mic button (all 6 closed-vocabulary intents recognized and shown honestly; only
  `approve_x`/`reject_x` are wired to an action, the other 4 say "not wired to an action in this
  build" rather than faking one), `ApprovalQueue.jsx`'s duplicate voice UI removed.
- **Two real bugs caught before/during this push:**
  1. (self-review) `voice_path.py` hardcoded the Whisper upload filename as `.wav` — real browser
     `MediaRecorder` output is WebM, so format detection would have broken on genuine mic input
     (existing test used synthetic WAV, didn't catch it). Added a `filename` param, threaded through
     from `main.py`'s `file.filename`.
  2. (self-review) Draft `Sidebar.jsx` referenced `signal.params.reason` for voice-reject —
     `MaintenanceSignal` has no `params` field (voice_intent.py's captured reason never makes it
     into the signal). Fixed to use the full transcript instead of a fabricated field.
- **Two real bugs caught by human testing after shipping:**
  1. React key collision: `IncidentWorkspace.jsx`'s evidence list used `key={artifact_id}`, but
     `artifact_id` isn't unique (the CMDB-fact and CMDB-relationship evidence entries both cite the
     CI itself, differing only by `source_type`). Fixed to a compound key.
  2. Confusing error surfaced from `/intake/confirm`: a transient gateway hiccup deep in the agent
     chain raised `json.JSONDecodeError` (a `ValueError` subclass), and the endpoint's broad
     `except ValueError` mislabeled it as a 400 client-input error with a cryptic raw Python message.
     Reproduced (retried the identical request — succeeded, confirming it was transient, not a real
     bug), then narrowed the handler to only 400 on the two genuine validation messages and 502
     ("likely transient — try again") otherwise.
- **Human confirmed working:** image flow explicitly confirmed; voice flow confirmed via "It is
  working" after the Sidebar rebuild (session boundary occurred between the fix and this
  confirmation — both dev servers were independently re-verified alive/functional post-boundary,
  restart wasn't actually needed).

## NEXT STEP
**For the next session (fresh, Phase 5 start):** read this file, then [decisions-log.md](decisions-log.md),
then [prd-phase-5.md](prd-phase-5.md) in full (Scenario Library, Eval & Hardening — not yet read any
session so far). Two things Phase 5 should pick up that were flagged as owed along the way:
- Real recorded voice sample (PRD §6.1: ≥2 noisy/accented samples) — flagged since Phase 2, still
  owed; this session's voice testing used live browser mic input but not a saved noisy/accented
  sample set.
- `evidence`/`hypotheses`/`plans`/`approvals`/`incidents` tables (`schema-db.md`) are still empty —
  Phase 3's agent chain only writes to `audit_log` + `negative_kb_entries`. Decide whether Phase 5's
  eval work needs structured per-incident queries; if so, this gap needs closing first.
Do not re-open [state-progress-history.md](state-progress-history.md) or re-read `PRD_FINAL.md` in
full for a normal Phase 5 start — everything needed is in this file + `prd-phase-5.md`.

## DONE (verified)
Phase 0-3 detailed checklists moved to [state-progress-history.md](state-progress-history.md).
Phase 4 progress tracked in LAST VERIFIED STEP above (active phase, kept live here).

## MOCKED & DEFERRED
Phase 0-3 items (simulators, real Jira, PDF runbooks, real voice sample, A2A PKI, live ports) moved
to [state-progress-history.md](state-progress-history.md) — still true, just not new this session.
Push-to-talk is now real (see LAST VERIFIED STEP) — resolved, no longer a stub. **New Phase 4 item:**
4 of the 6 voice intents (show_open_incidents, show_incident, what_changed_on_ci, start_scenario)
are recognized+displayed but not wired to an action — no incidents-list/scenario-library endpoint
exists yet to act on them with. Plan editing in Approval Queue is honestly disabled, not built.

## FILE INVENTORY
Phase 0-3 file list moved to [state-progress-history.md](state-progress-history.md). Active/Phase 4:
- `backend/main.py` — real routes beyond the Phase 0 stub: `GET /alerts/stream` (SSE, query-token
  auth), `GET /alerts/correlated` (header-JWT auth), `POST /workflows/run` (triggers a real agent
  chain run + joins `model_used` from `audit_log`), `POST /workflows/decision` (approve/reject +
  mandatory reason → `audit_log`), `GET /cmdb/drift` (recorded vs ground-truth field diff),
  `GET /autonomy-ladder` (read-only), `GET /chunks` (Chroma runbook chunks), `GET /metrics/summary`
  (real session aggregates from `audit_log` + the correlation engine).
- `backend/main.py` also now has: `POST /intake/voice`, `POST /intake/image` (real Whisper/gpt-4o),
  `POST /intake/confirm` (bridges a confirmed signal into a real run via `intake_adapter.py`),
  `_format_workflow_outcome()` (shared response-formatting helper, factored out of `/workflows/run`).
- `backend/orchestrator/contracts.py` — `SpecialistResult` extended with `latency_ms`/`tokens_used`/
  `transport` (all optional/defaulted — backward compatible).
- `backend/orchestrator/supervisor.py` — `_timed()` wrapper brackets every handoff.
- `backend/orchestrator/intake_adapter.py` — `start_workflow_from_confirmed_signal` now also
  returns its generated `incident_id` (additive).
- `backend/agents/{diagnosis,planner}.py` — capture real token usage via `api_client.extract_token_usage()`.
- `backend/api_client.py` — `extract_token_usage()` helper added.
- `backend/intake/voice_path.py` — `run_voice_intake`/`_transcribe` take a real `filename` param
  (was hardcoded `.wav`, broke real browser WebM uploads).
- `frontend_vite_backup/` — old Vite/React app preserved intact, migration source + rollback path.
- `frontend/` — Next.js 16.3.0 (App Router, Tailwind v4, Turbopack). `src/app/page.js` (login, renders
  `CockpitShell` post-auth), `src/app/globals.css` (ported theme), `src/lib/utils.js`
  (+ `findTraceEntry` shared helper),
  `src/components/{Dashboard,AdminControl,Sidebar,CockpitShell,OpsBoard,AgentTrace,IncidentWorkspace,ApprovalQueue,DriftQueue,AutonomyLadder,ChunkInspector,MetricsEval}.jsx`
  — **all 8 PRD §7 tabs built, acceptance criteria closed** (golden path, 3-badge system, real
  voice+image intake). `src/components/ui/{button,card,input,badge}.jsx`,
  `src/hooks/{useAlertStream,useWorkflowRun}.js` (`useWorkflowRun` now also exposes `runFromSignal`
  for the image-confirm path), `.env.local`, `public/sample-incident-screenshot.png`.
  `Dashboard.jsx`/`AdminControl.jsx` ported but no longer rendered (superseded by `CockpitShell`) —
  kept as reference, safe to delete once nothing imports them.

## KNOWN ISSUES
- **Gateway/proxy flakiness under sustained load (2026-08-07, WATCHING):** first live full-suite
  re-run (H+5:48 gate confirmation) hit a proxy-level stall (frozen CPU, same signature as the
  logged `gpt-5.1` sweep hang in `env-network.md`) on one test and a flaky FAILED on another;
  **both passed cleanly in isolation** (15s each) and a clean full rerun (84/84, 136.85s) confirmed
  it wasn't a code defect. Same category as the Phi-4-reasoning flakiness below — non-blocking, but
  re-check near submission if it recurs.
- **Phi-4-reasoning flakiness (2026-08-07, WATCHING):** intermittent 404s (3 rechecks: 404, 404, 200) — gateway-side instability, not a deprecation. Non-blocking (smoke-test-only model, unused in primary path), no substitute applicable. Re-run `python smoke_test.py` closer to the demo/submission checkpoint to see if it's cleared.
- Team-member-to-phase assignment (PRD §9 Q1) is still open; phase nodes use role placeholders ("Owner: Simulators/MCP", etc.) instead of names — fill in real names in each `prd-phase-N.md` as soon as known.
- Resolved issues (stack mismatch, model deprecations) moved to [state-progress-history.md](state-progress-history.md).

## RESUME INSTRUCTION
If resuming a stalled session: read this file, then [decisions-log.md](decisions-log.md), then the
current phase node named above. Do not re-read `PRD_FINAL.md` in full — it is frozen and already
distilled into `.knowledge/`. Only open [state-progress-history.md](state-progress-history.md) if
you need Phase 0-3 closed detail — not needed for normal Phase 4+ resume. Update H+ HOURS ELAPSED
and CURRENT PHASE only after the human confirms the next step actually works.
