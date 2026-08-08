---
type: state
title: State & Progress — Closed-Phase History
status: active
updated: 2026-08-07
related: [state-progress.md, prd-phase-0.md, prd-phase-1.md, prd-phase-2.md, prd-phase-3.md, prd-phase-4.md]
---

Split out of [state-progress.md](state-progress.md) when it crossed ~200 lines (maintenance
protocol item 5). This file holds **closed-phase detail** (Phase 0-3) that's no longer live —
read it only if you need the historical record, not every session. The live file stays the
single source of truth for current phase / next step.

## LAST VERIFIED STEP (superseded) — Jury-readiness pass: Microsoft 365 data pivot + UI redesign
Moved to this file — the data pivot (M365 vocabulary across all 200 CIs) and per-tab explainer
copy both stayed; the Microsoft-admin-center visual direction from this pass was itself superseded
by the Verascope rebrand directly below.

## LAST VERIFIED STEP (superseded) — Role-based access, real authentication, Verascope rebrand, theme toggle
Four passes (real server-enforced roles, real PBKDF2 authentication with 3 seeded accounts, the
full Verascope rebrand+Overview dashboard, light/dark toggle), self-verified via 84/84 + Playwright
QA. Login credentials: `alex.chen`/`OpsEngineer!123`, `priya.sharma`/`Approver!123`,
`admin`/`Admin!123`.

## LAST VERIFIED STEP (superseded) — Ops Board readability, ticket-lifecycle Steps 2-4, offline Ollama fallback
Ops Board readability was human-confirmed; the ticket-lifecycle Steps 2-4 pass; the offline Ollama
fallback (PRD §3.2) is implemented and live-verified. The `hnsw:search_ef=500` fix logged here
turned out to be only a partial fix for the Chroma flakiness — see KNOWN ISSUES' refined entry in
state-progress.md.

## LAST VERIFIED STEP (superseded) — Incident Workspace readability pass; Patch Management (real patch data, scheduling, Maintenance Planner panel)
Both human-confirmed-in-spirit/self-verified-and-live-checked at the time. `useCorrelatedCandidates`
(introduced in the Incident Workspace pass) was later deleted once Ops Board's cluster panel was
removed — see the Ops Board redesign entry in state-progress.md.

## LAST VERIFIED STEP (superseded) — Auto-triage fix; success metrics; Knowledge Base upload
## investigation; CMDB relationship fix; upload one-click fix + filters; Ops Board/Tickets tab split
Six passes, all self-verified/live-verified at the time, all superseded by later passes in the same
session (Ops Board and Knowledge Base especially were each touched again later). Still-open items
called out there: an in-app CI/ALERT/INC/TCK/OPS ID legend, and scoping "Diagnose" to a whole
cluster's alerts instead of just the first CI — both explained to the human inline but never built.

## LAST VERIFIED STEP (superseded) — ServiceNow-only tickets, needs_approval status, Ops Board
## status filter, Approval Queue folded into Incident Workspace
Human's 3 asks after the Ops Board simplification pass: (1) tickets from an alert-driven diagnosis
should only ever be ServiceNow — the performance-workflow branch that also raised a Jira issue was
confusing, remove it; (2) confirmed Ops Board already just has the alert table; (3) remove the
standalone Approval Queue tab, fold its decision UI into Incident Workspace; (4) add an Ops Board
status filter so "what needs human approval" is answerable at a glance.
`main.py`'s `_persist_ticket_snapshot` no longer creates a `tracker_mcp` (Jira) issue for
`workflow_type == "performance"` — every alert-driven run writes exactly one `local_tickets` row,
`system='itsm'`. `_normalize_ticket_status`'s `pending_approval` became its own `needs_approval`
value instead of collapsing into `in_progress` — `TICKET_STATUS_STYLE`/`_LABEL` (`OpsBoard.jsx`,
`Tickets.jsx`) both gained a red entry for it. Ops Board gained a second filter-pill row (All
statuses / Not yet diagnosed / Needs approval / In progress / Resolved). `ApprovalQueue.jsx`
deleted; its recommendation/counter-hypothesis/blast-radius/policy-gate/reason/Approve-Reject UI
moved into a new `ApprovalSection` inside `IncidentWorkspace.jsx`, rendered only when `run.status
=== "pending_approval"`, role-gated (`canDecide = identity.role in {approver, admin}`).
**Verified**: `npm run build` clean; full backend suite 98/98; live Playwright pass — nav no longer
shows "Approval Queue", Ops Board shows both filter rows, a real advisory-only scenario (SCEN-05)
shows the red "Needs approval" section inline with working Approve/Reject; direct API check confirms
a real performance-workflow run now persists only an `itsm` ticket, zero `tracker` rows.

## LAST VERIFIED STEP (superseded) — Floating assistant (chatbot), reversing the documented "no
## chatbot" decision; push-to-talk merged into it
Human asked for a floating chat assistant (bottom-right icon, popup) answering real questions about
ticket/incident data via an AI-built filter, basic app questions, approve/reject a pending incident,
and voice input — replacing Sidebar's push-to-talk entirely. Flagged before building: this reverses
`decisions-log.md`'s "cut scoped chat drawer" call and PRD §2.2's "vs. a general chat assistant"
differentiation argument; confirmed via AskUserQuestion to build it so as to keep those same
properties (grounded, real audit trail, no fabrication) rather than become what they warned against.
`POST /chat` (`main.py`): one classification LLM call (`gpt-4.1-nano`) turns the message into
`{intent, filters/target_ref/reason/help_topic}`; everything after is deterministic —
`query_tickets` runs a real parameterized SQL query, `approve_incident`/`reject_incident` reuses the
exact same audited, role-gated, reason-required path `/workflows/decision` uses. `ChatWidget.jsx`:
floating button + popup, mic reuses the real `/intake/voice` pipeline. Sidebar's old `PushToTalk`
component removed.
**Verified**: `npm run build` clean; backend suite 97/98 (1 unrelated pre-existing flake); direct API
tests on all 4 intents; live Playwright pass with a real conversation.

## LAST VERIFIED STEP (superseded) — Agent Trace and Knowledge Base moved off the main tab bar
Human asks: Agent Trace doesn't need its own tab — a button that expands it in a popup is enough
(it only ever showed the same shared `run` Incident Workspace already displays). Knowledge Base
isn't "main, always-needed" data — move it to a Sidebar panel like the other admin panels.
`IncidentWorkspace.jsx` gained a "View full Agent Trace" button opening `AgentTrace.jsx` unchanged
inside a `Modal`; `AgentTrace`/`Tickets` tab renders removed from `CockpitShell.jsx`. Knowledge Base
moved into `Sidebar.jsx`'s `NAV_ITEMS` as `ChunkInspector.jsx` (imported as `KnowledgeBasePanel`);
`roles.js`'s `PANEL_PERMISSIONS` gained a `"knowledge"` key for all 3 roles. `TAB_PERMISSIONS`/
`TABS`/`tabInfo.js` all had Agent Trace and Knowledge Base removed.
**Verified**: `npm run build` clean; live Playwright pass — nav bar confirmed down to 6 tabs, Sidebar
Knowledge Base icon opens the real chunk browser in a modal, "View full Agent Trace" opens the real
per-agent handoff cards in a modal. No backend changes this pass, full suite not re-run.

## LAST VERIFIED STEP — Phase 4, Next.js migration (scaffold)
- Old Vite app preserved at `frontend_vite_backup/` (no git repo in this project — this backup is
  the only rollback path, not disposable).
- `frontend/` replaced with a fresh Next.js scaffold: **Next.js 16.3.0, React 19.2.8, Tailwind v4,
  App Router, Turbopack** (`npx create-next-app@latest --js --tailwind --eslint --app --src-dir
  --import-alias "@/*" --use-npm --no-git`).
- **Version note:** newer than the Tailwind v3 setup the old shadcn/ui components
  (`Button`/`Card`/`Input`, `frontend_vite_backup/src/`) were written against — Tailwind v4 uses a
  CSS-based config, not `tailwind.config.js`. Porting meant re-initializing shadcn/ui for v4, not
  copy-pasting the old config.
- Tailwind v4 theme rebuilt in `globals.css` (`@theme inline` mapping to the old HSL CSS variables).
  `cn()` util + `Button`/`Card`/`Input` ported byte-for-byte from `frontend_vite_backup/`.
- `App.jsx` login logic ported to `frontend/src/app/page.js`; `Dashboard.jsx`/`AdminControl.jsx`
  ported unchanged. `VITE_API_BASE_URL` → `NEXT_PUBLIC_API_BASE_URL` in `frontend/.env.local`.
- **Human-verified end to end (H+5:58):** backend on :8765, logged in through the browser, mock-auth
  flow fully round-tripped through the new Next.js stack.

## LAST VERIFIED STEP — Phase 4 atomic step 1 (base layout)
- Backend: `GET /alerts/stream` added to `main.py` (first real HTTP route beyond the Phase 0
  auth/health/chat stub — Phases 1-3 logic was previously only exercised via pytest, never over
  HTTP). Query-string JWT auth (EventSource can't set headers); replays recent alert history then
  polls the `alerts` table every 3s for new rows.
- Frontend: `Sidebar.jsx` (role switcher, live-feed status, push-to-talk button — visibly
  disabled/labeled "not wired yet"), `CockpitShell.jsx` (8-tab workspace shell per PRD §7),
  `hooks/useAlertStream.js`. `page.js` renders `CockpitShell` post-login instead of the old
  `Dashboard` demo (dropped — no chat drawer, per decisions-log.md trade ledger).
- **Human confirmed working (H+6:11):** Ops Board tab live-updates from the real SSE feed with no
  manual refresh, other 7 tabs show placeholders.
- Visual polish deliberately minimal at this stage — matches the atomic-step sequencing in
  `prd-phase-4.md` (structure first, real design per-tab in later steps).

## LAST VERIFIED STEP — Phase 4 atomic step 2 (Ops Board full build)
- Backend: `GET /alerts/correlated` added to `main.py`, header-JWT auth. Reuses
  `correlation/cluster.py`'s tested functions directly. Verified live: 500 alerts → 420 clusters,
  16% noise reduction — matches the Phase 2 closeout numbers exactly.
- Frontend: `OpsBoard.jsx` (alert feed + correlated-candidates pane + noise-reduction headline +
  image drop zone). Image drop zone supports drag-and-drop and click-to-browse (hidden file input
  + ref) — preview only, labeled not yet wired to `backend/intake/vision_path.py`.
- **Human confirmed working (H+6:25):** correlated candidates + noise-reduction % render correctly;
  click-to-browse fix (human caught drag-only wasn't a complete drop zone) applied same step.
- Two transient `ReferenceError`s during editing (`OpsBoardTab`, then `useRef`) were mid-edit races
  in Turbopack hot-reload — each self-healed on the next compile once the paired edit landed.

## LAST VERIFIED STEP — Phase 4 atomic step 5 (Approval Queue, original text-only version)
- Resolved architecture question (asked human first): `run_workflow` has no checkpointing — a
  `pending_approval` run cannot be resumed mid-flight. Approving re-runs the same CI/workflow_type
  with `auto_approve=true` (a fresh run, new incident_id) — labeled honestly, not presented as a resume.
- Backend: `POST /workflows/decision` — records approve/reject + mandatory reason to `audit_log`.
  400 on empty reason, 400 on invalid decision value.
- Real bug found+fixed (human caught): shared `useWorkflowRun` hook hardcoded `auto_approve: true`
  on every call, so Approval Queue's trigger could never land in `pending_approval`. Fixed by
  making `auto_approve` a real parameter.
- Human confirmed working (H+7:46). Note: this tab was substantially rebuilt in the later
  golden-path/voice-approval push — see the live file for the current version.

## LAST VERIFIED STEP — Phase 4 atomic step 3 (Agent Trace Viewer)
- **Contract extension (asked human first — touches the frozen, 84/84-tested `SpecialistResult`
  contract):** added `latency_ms`, `tokens_used`, `transport` — optional/defaulted, no existing
  construction call breaks. `supervisor.py` brackets every handoff with a `_timed()` wrapper;
  `diagnosis.py`/`planner.py` capture real token usage via `api_client.extract_token_usage()`.
  Reran `test_diagnosis.py`/`test_planner.py`/`test_supervisor.py` (14/14) — no regression.
- Backend: `POST /workflows/run` — triggers a real workflow, joins `model_used` from `audit_log`,
  returns trace + real signed A2A Agent Card. Verified live on `CI-0059`: diagnosis
  `transport: a2a, tokens: ~1480`, planner `transport: in_process, tokens: ~570`.
- Frontend: `AgentTrace.jsx` — run/replay button, one card per handoff, Agent Card JSON viewer.
- **Layout bug fix (human caught):** shell used `min-h-screen` instead of fixed `h-screen` (whole
  page scrolled instead of just `main`); Ops Board panels were `flex-1` without `min-w-0` (classic
  flexbox `truncate` overflow gotcha). Fixed in `CockpitShell.jsx`/`Sidebar.jsx`/`OpsBoard.jsx`.
  Human confirmed working (H+7:04).

## LAST VERIFIED STEP — Phase 4 atomic step 4 (Incident Workspace)
- Frontend: `IncidentWorkspace.jsx` — Evidence (w/ citations), Ranked Hypotheses (+ "could not
  verify" fallback), Plan (blast radius + policy gate), Linked Systems (real ITSM ticket +
  verification status). Reused `POST /workflows/run` — no new backend endpoint needed.
- Caught (self-review) and fixed a reference to a nonexistent `plan.negative_kb_caution` field
  before shipping — used the Knowledge agent's real `negative_kb_entry` instead.
- Did NOT build fake "Tracker linkage" or "contradiction highlighting" — not real agent-chain
  output, noted honestly in-UI instead.
- `hooks/useWorkflowRun.js` extracted (shared by Agent Trace + Incident Workspace).
- Human confirmed working (H+7:15).

## LAST VERIFIED STEP — Phase 2 closeout
- **Correlation engine** (`backend/correlation/cluster.py`, scikit-learn DBSCAN + CMDB-topology
  connected components + category fingerprint, no LLM): 500 alerts → 420 clusters across 10
  topology groups. Reproducibility confirmed (2 identical runs, byte-for-byte same output).
- **Policy gate** (`backend/guardrails/policy_gate.py`): pure Python rule engine, 12/12 unit tests
  green — freeze-window, prod-vs-non-prod, blast-radius (approval + block thresholds), max-concurrent,
  required-approver-role, and the advisory-only-tuning-never-auto-executes rule.
- **Blast radius** (`backend/guardrails/blast_radius.py`): BFS over CMDB adjacency, 9/9 unit tests
  against hand-built chain/star fixtures.
- **Audit log** (`backend/orchestrator/audit.py`): append-only enforced by a real SQLite trigger
  (`schema.sql` — raw SQL UPDATE/DELETE is rejected by the DB itself, not just by module discipline). 5/5 tests.
- **Voice intent parser** (`backend/intake/voice_intent.py`): closed-vocabulary, all 6 intents,
  11/11 tests incl. near-miss/misheard-fragment cases that correctly fall through to UNRECOGNIZED.
- **Scrubber** (`backend/guardrails/scrubber.py`): regex pass + local Ollama SLM pass
  (`llama-3.2-3b-it`) for names, reversible tokenisation. Measured against `pii_ground_truth.json`
  (31 planted items, `backend/data_gen/pii_seed.py`): 100% recall regex-covered types, 100% recall
  local-SLM names (this run), adversarial injection line correctly flagged, zero false positives.
  7/7 tests. One real bug found+fixed during testing (phone regex gap) — see `errors-solved.md`.
- `pii_ground_truth` SQLite table populated (31 rows, was empty since Phase 1).
- `pytest==8.3.3` added; `backend/conftest.py` added so `from guardrails.x import y`-style imports
  resolve regardless of pytest invocation directory.
- Full suite: `pytest backend/tests/ -v` → 44 passed.

## LAST VERIFIED STEP — Phase 3 closeout (DEMO-COMPLETE CHECKPOINT)
- **Typed contracts** (`orchestrator/contracts.py`): `SpecialistResult` + `MaintenanceSignal`, pydantic, pasted from `api-contract.md`.
- **Turn caps** (`orchestrator/limits.py`): per-agent caps, `TurnCapExceeded` -> explicit `termination_reason`, never silent.
- **Workflow YAML**: `incident.yaml` built first; `patch.yaml`/`performance.yaml` derivation confirmed "nearly free" (only 3 fields differ) — see `domain-workflows.md`.
- **6 specialist agents**, all real-gateway/real-tool tested: Enrichment (MCP+Chroma, deterministic), Diagnosis (DeepSeek R1, citation enforcement), Planner (gpt-4.1-nano, runbook-bounded + deterministic blast-radius/policy-gate), Verification (Fake Fix Detector, tested against REAL Phase 1 degradation-curve data), Sync (ITSM+CMDB via MCP), Knowledge (Negative KB seeding).
- **Supervisor** (`orchestrator/supervisor.py`): dispatch loop, schema re-validation at every handoff, all 3 workflow families tested end to end against real data (happy path, Fake-Fix-catch, blast-radius block, tuning-never-auto-executes).
- **A2A**: Supervisor→Diagnosis, real HMAC-SHA256-signed Agent Card (`a2a/agent_card.py`), discovery + invoke endpoint (`a2a/endpoint.py`, port 9010), client (`a2a/client.py`). Decision + rationale recorded in `domain-agents.md`.
- **Multimodal intake**: voice (`intake/voice_path.py`, real Whisper, scrub-before-parse verified) and vision (`intake/vision_path.py`, gpt-4o substitute, real extraction from a synthetic screenshot, correctly pulled `CI-0087`). `orchestrator/intake_adapter.py` bridges a *confirmed* signal into a real workflow run — confirmation gate enforced in code, tested that an unconfirmed signal is rejected.
- Dependencies added: `pyyaml==6.0.3`, `pillow==11.0.0` (for generating a real test screenshot with readable text — a blank image doesn't exercise vision extraction, learned from re-fixing the smoke-test vision check the same way in Phase 0).
- **Full suite: `pytest backend/tests/ -v` → 84 passed** (44 Phase 2 + 40 Phase 3), ~3.4 min wall-clock (most of that real gateway/LLM calls).

## DONE (verified)
### Phase 0 (closed)
- [x] Backend FastAPI skeleton running, CORS to frontend origin configured.
- [x] Frontend Vite/React + shadcn/ui skeleton running, JWT mock-auth login flow works end to end.
- [x] SSL bypass + `TIKTOKEN_CACHE_DIR` fix applied and confirmed working (see [env-network.md](env-network.md)).
- [x] `ollama list` recorded, no models pulled.
- [x] Whisper confirmed via real audio/transcriptions call.
- [x] `text-embedding-3-large` → Chroma round-trip confirmed.
- [x] HANDBOOK_MODELS chat subset: gpt-4o-mini ✅, gpt-4.1-nano (V3 substitute) ✅, DeepSeek R1 ✅, Phi-4-reasoning ⚠ intermittent (non-blocking).
- [x] Vision path confirmed via substitute `genailab-maas-gpt-4o` (Llama Vision permanently gone) — 1323ms, correct image read.
- [x] DeepSeek V3's role confirmed via substitute `azure/genailab-maas-gpt-4.1-nano` (V3 permanently gone) — 1206ms, valid structured JSON output on a realistic remediation-plan prompt.
- [x] Repo scaffold re-verified booting live (backend `/health`, frontend `/`) after all Phase 0 dependency/env changes.
- [x] Jira probe attempted (reachable, signup deferred to human), `PHASE0_FINDINGS.md` written.

### Phase 1 (closed)
- [x] All Phase 1 synthetic data generated at spec'd volumes (see LAST VERIFIED STEP), `data/PROVENANCE.md` complete.
- [x] 4 simulators + 4 MCP wrappers built, tool sets match `api-contract.md` exactly, all self-tested end to end.
- [x] Canonical schemas frozen (`api-contract.md`, `schema-db.md` both `active`).
- [x] SQLite populated (17 tables, correct volumes), Chroma populated (3 collections, 668 chunks/records total).
- [x] Structural chunker + `assert_chunks.py` passing, trap case verified.
- [x] Agent-free gate script passing, human-approval gate confirmed intact.

### Phase 2 (closed)
- [x] Correlation engine: 500 alerts → 420 clusters, reproducible, no LLM.
- [x] Policy gate: 12/12 unit tests, all 4 required cases + 3 more.
- [x] Blast radius: 9/9 unit tests against known fixtures.
- [x] Audit log: append-only enforced at the DB layer (trigger), 5/5 tests.
- [x] Voice intent parser: all 6 intents, closed-vocabulary, 11/11 tests.
- [x] Scrubber: 100%/100% measured recall this run, reversible tokenisation confirmed, 7/7 tests.
- [x] `pii_ground_truth` table populated (31 rows).

### Phase 3 (closed) — DEMO-COMPLETE CHECKPOINT
- [x] 6 specialist agents + Supervisor built, all real-gateway/real-tool tested (40 tests).
- [x] All 3 workflow families (incident/patch/performance) run end to end through the real agent chain.
- [x] Citation enforcement: Diagnosis never returns an uncited or hallucinated-artifact hypothesis.
- [x] Runbook-bounded action space: Planner never returns a step citing a non-retrieved chunk.
- [x] Fake Fix Detector distinguishes `verified_resolved` vs `symptom_suppressed` against real degradation-curve data (not a synthetic fixture).
- [x] A2A: Supervisor→Diagnosis, signed Agent Card, tampering detected, discovery + invoke tested.
- [x] Voice + Vision intake paths built, scrub-before-parse ordering verified, confirmation gate enforced in code.
- [x] Turn caps enforced, every termination reason explicit.
- [x] Patch/performance derivation from incident confirmed "nearly free" (design assumption held).

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
  IncidentWorkspace, AgentTrace, ApprovalQueue. (Colors later re-mapped to brand tokens in the
  Verascope rebrand — see state-progress.md.)
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

## LAST VERIFIED STEP — Jury-readiness pass: Microsoft 365 data pivot + UI redesign (human-directed, off-plan)
Human found the demo too technical/generic for a jury and asked for 3 things before resuming Phase
5: (1) re-theme the whole simulated domain from generic IT infra to Microsoft 365/Power Platform
business services, (2) explain what each tab does in plain language, (3) an enterprise visual
redesign. **Human confirmed working** via a live screenshot of Incident Workspace after this pass.
(Superseded by the later Verascope rebrand — state-progress.md — which replaced the Microsoft-
admin-center visual direction below entirely; the data pivot and per-tab-copy work stayed.)
- **Data pivot (all 200 CIs)**: `backend/data_gen/{cmdb,alerts,runbooks}.py` — `CI_TYPES`/`OWNER_TEAMS`/
  `FAULT_SUMMARIES`/`DEGRADATION_SUMMARIES`/`CI_CONTEXTS`/failure-signature pools relabelled to M365
  vocabulary (SharePoint, OneDrive, Power Platform, Teams, Exchange Online, Dataverse, Azure AD),
  **keeping every pool's exact length** so the seeded `random.choice` draws stay index-aligned —
  verified CI-0059/CI-0121/CI-0009/CI-0138/CI-0181's environment/criticality/blast-radius and every
  ALERT-id→ci_id mapping are byte-identical to pre-pivot. Regenerated all `data/*.json`, reran
  `init_db.py --test` and the **full 84/84 backend suite — green**. `data/scenarios/SCEN-05.json`/
  `SCEN-06.json` names updated (stale "app-server" wording only, IDs/logic untouched).
- **Per-tab explainer copy**: new `frontend/src/lib/tabInfo.js` (plain-language tagline+description
  per PRD §7 tab), rendered as a banner in `CockpitShell.jsx`'s `<main>` and as nav-button tooltips.
- **Agent Trace now shows what each agent concluded, not just metadata**: `AgentTrace.jsx`'s
  `summarizeResult()` derives a human-readable line per `agent_name` from `SpecialistResult.result`
  (already sent by the backend, previously unrendered) — e.g. diagnosis's actual top hypothesis text,
  planner's step count + policy-gate decision, verification's alert/probe verdict.
- **Enterprise visual redesign** (Microsoft-admin-center direction, chosen over a neutral-SaaS
  alternative — later itself superseded, see above): new token layer in `globals.css` (deep azure
  `--primary`, dedicated `--header`/`--accent` chrome tokens), navy branded header with a 4-square
  logo mark in `CockpitShell.jsx`, Fluent-style underline tab nav, accent-highlighted sidebar nav in
  `Sidebar.jsx`, `Card` given `hover:shadow-md`.
- **Live QA**: installed Playwright + Chromium locally (corporate-proxy SSL bypass needed —
  `NODE_TLS_REJECT_UNAUTHORIZED=0`, same class of issue as `env-network.md`'s tiktoken bypass) since
  no `chromium-cli`/project run-skill existed; drove the golden path on CI-0059 end-to-end with real
  gateway calls, screenshotted Ops Board + Agent Trace. **Caught and fixed a real bug along the way**:
  an orphaned backend process from an earlier session was already squatting on port 8765, silently
  swallowing the fresh instance's bind and serving stale code — killed it, confirmed a clean bind.
  DeepSeek-R1 correctly reasoned over the new domain in a live diagnosis ("the exchange-online-connector
  (CI-0059) is experiencing throttling errors during queue.publish operations...").

## MOCKED & DEFERRED
- [MOCK-P1] Monitoring, ITSM, Tracker, CMDB — built as FastAPI simulators (`backend/mcp_servers/simulators/*.py`), never real ServiceNow/Jira/Prometheus. Labelled as simulators; real field-name conventions used deliberately.
- Real-Jira portability probe (PRD §4.21) — network reachability confirmed (`atlassian.net` → HTTP 302); actual instance creation deferred to the human (requires manual signup/ToS), never wired into anything per PRD instruction.
- 2-3 runbooks as PDF (PRD §6.1) — not generated, needs a PDF-writing dependency not yet in `requirements.txt`. Markdown runbooks (22) are complete and cover the full requirement otherwise.
- Real multi-process port reachability for the 4 simulators (9001-9004) — see Phase 1 LAST VERIFIED STEP known gap; logic proven via self-test, live-port re-check deferred to the actual event environment.
- Real recorded voice sample (PRD §6.1: ≥2 noisy/accented voice samples) — no audio recording capability in this session; intent-recognition logic is tested directly (scrub→parse), but never through an actual spoken Whisper round-trip. **Owed before Phase 5** (scenario library / eval).
- A2A signing uses a local-only HMAC secret, not asymmetric/PKI keys — documented as a deliberate hackathon-scope simplification in `a2a/agent_card.py`, not hidden.
- Real multi-process reachability for the A2A endpoint (port 9010) and the Diagnosis-over-A2A call — same category of gap as the 4 simulators above (in-process ASGI transport proven, real port not yet re-checked in this sandboxed dev environment).

## FILE INVENTORY — Phase 0-3
- `PHASE0_FINDINGS.md` (repo root) — Phase 0 closeout record.
- `backend/config.py`, `backend/api_client.py`, `backend/smoke_test.py`, `backend/requirements.txt` — exist, working.
- `backend/data_gen/{cmdb,alerts,metrics,tickets,runbooks}.py` — new, Phase 1 data generators.
- `backend/mcp_servers/simulators/{monitoring,itsm,tracker,cmdb}.py` — new, the 4 simulators.
- `backend/mcp_servers/{monitoring,itsm,tracker,cmdb}_mcp.py` — new, the 4 MCP wrappers.
- `backend/db/{schema.sql,init_db.py,load_chroma.py}` — new, SQLite + Chroma population.
- `backend/chunking.py` — new, structural chunker.
- `scripts/{assert_chunks.py,gate_scenario.py}` — new, Phase 1 verification scripts.
- `data/*.json|csv`, `data/runbooks/*.md`, `data/postmortems/*.md`, `data/app.db`, `data/chroma_db/` — new, generated/populated this session.
- `backend/correlation/cluster.py` — new, Phase 2 correlation engine.
- `backend/guardrails/{policy_gate,blast_radius,scrubber}.py` — new, Phase 2 guardrails.
- `backend/orchestrator/audit.py` — new, append-only audit log.
- `backend/intake/voice_intent.py` — new, closed-vocabulary voice intent parser.
- `backend/data_gen/pii_seed.py`, `data/pii_ground_truth.json` — new, planted PII/secrets test data.
- `backend/conftest.py`, `backend/tests/test_{policy_gate,blast_radius,audit,voice_intent,scrubber}.py` — new, 44 Phase 2 unit tests.
- `backend/orchestrator/{contracts,limits,mcp_wiring,retrieval,supervisor,intake_adapter}.py` — new, Phase 3 orchestration core.
- `backend/orchestrator/workflows/{incident,patch,performance}.yaml` — new, declarative workflow definitions.
- `backend/agents/{enrichment,diagnosis,planner,verification,sync,knowledge}.py` — new, the 6 specialist agents.
- `backend/intake/{voice_path,vision_path}.py` — new, multimodal intake paths.
- `backend/a2a/{agent_card,endpoint,client}.py` — new, the Supervisor→Diagnosis A2A handoff.
- `backend/tests/test_{enrichment,diagnosis,planner,verification,sync_knowledge,supervisor,voice_path,vision_path,a2a,intake_adapter}.py` — new, 40 Phase 3 tests.
- `frontend_vite_backup/` — new, the old Vite/React app preserved intact (`App.jsx`, `Dashboard.jsx`,
  `AdminControl.jsx`, `ui/{button,card,input}.jsx`) as the migration source + rollback path.

## Role-based access, real authentication, full Verascope rebrand, light/dark toggle (2026-08-07)
Four back-to-back human-directed passes, all off the original phase plan, all before Phase 5 resumed
(moved here from state-progress.md to keep that file under its ~200-line budget — this content was
still awaiting explicit human browser confirmation when archived, not superseded, so treat "not yet
confirmed" as still current unless a later state-progress.md entry says otherwise):

**1. Role-based access (real, server-enforced).** `ROLE_TO_ACTOR_ROLE` maps the UI role vocabulary
(ops_engineer/approver/admin) to `guardrails/policy_gate.py`'s frozen `actor_role` vocabulary
(operator/sre_lead/change_manager) without changing that tested module. **Fixed a real bug**:
`/workflows/run` was passing the raw *username* as `actor_role`, so the approver check could never
match any real login — every prod/P1 action silently required approval regardless of who was
"logged in." `/workflows/decision` now requires Approver/Admin (403 otherwise). Built all 4 Sidebar
admin panels for real: Scenario Launcher (lists/launches the 6 Phase 5 scenarios), Audit Log (read
view of `audit_log`), Model & Threshold Config (policy thresholds genuinely live-editable; model
routing shown read-only, since editing that would touch frozen agent modules), Ingestion/Admin
(real runbook upload: structural chunking + real embedding + Chroma upsert).

**2. Real authentication** (SUPERSEDES the PRD's "no real auth" decision — decisions-log.md). A
`users` table with salted PBKDF2-HMAC-SHA256 password hashes (stdlib `hashlib`, no new pip
dependency — corporate-proxy SSL friction has hit every new-package install this session).
`POST /auth/login` now actually validates credentials (401 on bad password, verified live). Each
account has one fixed role; the old free-for-self-elevation switcher was replaced with an
admin-only, audited "View as" (`POST /auth/view-as` / `POST /auth/stop-view-as`) carrying `real_*`
JWT claims so the UI shows an honest "Admin viewing as Priya Sharma (Approver)" banner rather than
silently pretending to be someone else. **3 seeded demo accounts** (passwords in `init_db.py`'s
`_DEFAULT_USERS`, printed by `--test`): `alex.chen`/`OpsEngineer!123` (Ops Engineer),
`priya.sharma`/`Approver!123` (Approver), `admin`/`Admin!123` (Admin).

**3. Full Verascope rebrand** (SUPERSEDES the Microsoft-admin-center visual direction — human judged
it still too close to implying a Microsoft product). New name **Verascope** ("vera" + "scope" — an
instrument for seeing a true signal through noise), new logo (scope-ring mark, SVG, no external
asset), light-by-default card-based token system (`--signal` teal `#0D9488` as the one brand hue,
reused for logo/primary actions/"system-verified" badge). Used the `frontend-design` skill for the
identity work and the `dataviz` skill for 3 new real charts on a new **Overview dashboard** (KPI
tiles + bar/gauge/donut, backed by `/metrics/summary` + `/cmdb/drift` + `/autonomy-ladder` +
`/audit-log` — all pre-existing endpoints, nothing fabricated) — Overview replaces Ops Board as the
default landing tab for every role. `dataviz`'s colorblind-safety validator caught a real issue:
red/green (the obvious choice for approvals-vs-rejections) fails the deutan separation check, so
charts use a consistent teal/amber pairing instead. Sidebar admin panels now open in a
dependency-free Modal instead of expanding inline in the 256px sidebar.

**4. Light/dark theme toggle.** Light is the *true* default — removed the `prefers-color-scheme`
auto-detect media query entirely so an OS set to dark no longer silently overrides it (verified via
Playwright with `colorScheme: "dark"` context — app still rendered light). Dark theme kept, values
unchanged, now reachable only via an explicit toggle (Sidebar, both collapsed/expanded — sun/moon
icon) persisted to `localStorage`; an inline script in `layout.js`'s `<head>` applies the stored
theme before first paint (no flash), with `suppressHydrationWarning` on `<html>` for the resulting
(expected — same pattern `next-themes` uses) attribute mismatch.

**Verification**: 84/84 backend tests green after every backend change in this pass. Playwright QA
after each sub-pass: role gating confirmed per-role (Ops Engineer has no Approval Queue/no admin
panels; Admin has both), bad-password login genuinely rejected, view-as banner + return-to-admin
round-tripped, Overview's 3 charts render real numbers, modal opens/closes (Escape + backdrop
click), dark theme renders correctly across cards/charts/badges. Zero console errors on every pass.

**File inventory for this pass** — backend, new: `backend/auth_utils.py` (PBKDF2 hash/verify).
`backend/db/schema.sql` — `users` table (replaces the short-lived `profiles` table). `backend/db/
init_db.py` — `populate_users()`, `_DEFAULT_USERS` (3 seeded accounts + passwords). Backend, edited:
`backend/main.py` — real `Identity`/`get_current_identity`/`require_role`, `ROLE_TO_ACTOR_ROLE`, real
`POST /auth/login`, `GET/POST/DELETE /users`, `POST /auth/view-as`+`/auth/stop-view-as`, `GET
/audit-log`, `GET /scenarios`, `GET/POST /config/thresholds`, `GET /runbooks`+`POST
/runbooks/upload`; `/workflows/run` and `/workflows/decision` now use real role enforcement (the
actor_role bug fix). `backend/guardrails/policy_gate.py` — `get_thresholds()`/`set_thresholds()`
(module-level mutable, defaults unchanged so `test_policy_gate.py` stays green untouched). Frontend,
new: `src/lib/roles.js` (role/tab/panel permission matrix), `src/lib/theme.js` + `src/hooks/
useTheme.js` (light-default toggle, localStorage), `src/components/Logo.jsx` (Verascope scope-ring
mark), `src/components/Overview.jsx` (new default landing tab — KPI tiles + bar/gauge/donut charts),
`src/components/ui/modal.jsx` (dependency-free), `src/components/panels/
{ScenarioLauncherPanel,AuditLogPanel,ModelThresholdConfigPanel,IngestionAdminPanel}.jsx` (the 4 admin
panels, real), `src/app/icon.svg` (favicon, Verascope mark). Frontend, edited: `globals.css` (full
new Verascope token system — light default, teal `--signal`/`--primary`, `--status-*` reserved
palette, no more `prefers-color-scheme` auto-dark), `layout.js` (theme-init inline script,
`suppressHydrationWarning`, title/description, Geist font actually wired to
`--font-sans`/`--font-mono` — was loaded but unused before), `page.js` (full login redesign —
Verascope brand panel, ring watermark, real-credential form, no role picker), `CockpitShell.jsx` (new
logo/header, Overview added to `TABS`, identity now decodes `display_name`/`real_*` claims),
`Sidebar.jsx` (`ViewAsControl` replaces the old self-service profile switcher, panels open in
`Modal`, `ThemeToggle` wired in both collapsed/expanded), `roles.js`/`tabInfo.js` (Overview added,
"Microsoft 365" wording removed from body copy), `ui/badge.jsx` (colors now draw from the brand's
`--status-*`/`--accent` tokens instead of raw Tailwind palette classes), `useAlertStream.js`
(dedupe-by-id fix — a token change from view-as/login reconnects the SSE stream and replays the
backlog).

## FILE INVENTORY — Phase 4 (condensed) + Jury-readiness pass (moved from state-progress.md for space)
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
- **Jury-readiness pass additions**: `frontend/src/lib/tabInfo.js` (per-tab copy). `backend/data_gen/
  {cmdb,alerts,runbooks}.py` relabelled to M365 vocabulary. `data/scenarios/SCEN-05.json`/`SCEN-06.json`
  name text updated.

## LAST VERIFIED STEP (moved from state-progress.md) — Ops Board readability (Step 1 of 4, Ops Board/ticket-lifecycle/KB-merge pass)
Human-confirmed 2026-08-07. Ops Board no longer leads with raw vendor payloads (SNMP traps,
Prometheus JSON, APM spans) — alerts and correlated candidate groups now show a plain-language
headline (`{CI display name} — {summary}` + severity badge) with the raw payload collapsed behind a
"Technical details" toggle that itself explains what it is ("the exact, unprocessed message as sent
by a network device (SNMP trap)..."). Correlated-candidate groups also show `first_seen`/`last_seen`
so it's visible *why* two same-CI/same-category alerts land in different groups (>15min apart —
correlation.py's DBSCAN window — not a clustering miss). Both the live alert feed and candidate list
are now in a fixed-height (600px) scrollable container so the live SSE stream doesn't reflow the page
as new alerts arrive.
Backend: `data_gen/alerts.py` alerts now carry an explicit `summary` field; `data_gen/cmdb.py` CIs
now carry a `display_name` (product-label map); both regenerated (same fixed seed). `alerts` SQLite
table gained `ci_id/category/severity/summary` columns, `cmdb_ci` gained `display_name` — `db/app.db`
rebuilt. `/alerts/correlated` and `/alerts/stream` (`_fetch_alerts_after`) now join/return the new
fields. Frontend: `OpsBoard.jsx`'s `AlertItem`/`CorrelatedCandidates` rewritten for the above.
**Two real bugs hit and fixed during this step** (see errors-solved.md candidates): a stale backend
process from an earlier session was still holding port 8765 and silently served old code until
killed; the new `alerts`⋈`cmdb_ci` join had an ambiguous `id` column that crashed the SSE stream
mid-response (fixed by qualifying `alerts.id`).
**Verification**: `data_gen/alerts.py`, `data_gen/cmdb.py`, `correlation/cluster.py --test`,
`db/init_db.py --test` all clean; backend suite 70/84 (14 failures are a live TCS GenAI Lab gateway
503 "authentication database temporarily unreachable" — confirmed external/unrelated via isolated
re-run, see KNOWN ISSUES); live Playwright browser check (screenshots + DOM assertions) confirmed
rendering, the scroll-container fix (600px visible vs. 2852-4552px full content), and zero new
console errors (pre-existing login-page hydration warning and expected 403s on Overview's audit-log
for a non-Approver role, both unrelated).

## LAST VERIFIED STEP (moved from state-progress.md, self-verified, human confirmation status unchanged by the move) — Steps 2-4 of the Ops Board/ticket-lifecycle/KB-merge/Metrics-fold pass
Human said "move to phase 2 directly without confirming" after Step 1 — steps 2-4 were built and
self-verified back-to-back in the same session, not yet clicked through by the human at time of writing.

**Step 2 — click-to-diagnose + local ticket persistence + history.** `local_tickets` table (additive,
does not touch frozen `supervisor.py`/`sync.py`/`itsm_mcp.py`): `system`/`external_id`/`cmdb_ci`/
`workflow_type`/`status_raw`/`status_normalized`/`priority`/`summary`/`opened_at`/`closed_at`/
`linked_incident_id`/`trace_snapshot` (JSON, the same shape `/workflows/run` already returns)/
`created_at`. `_persist_ticket_snapshot()` in `main.py` writes one row per `/workflows/run` call
(additive, after the existing response is built) — `performance` workflow_type also creates a
Jira-shaped tracker issue via `tracker_mcp.create_issue`. New `GET /tickets` (filterable) /
`GET /tickets/{id}` (with trace_snapshot) / `GET/POST /config/integrations` (inert instance-URL
slot, single-row `integration_settings` table) endpoints. `OpsBoard.jsx`: "Diagnose" button per
correlated group, one bounded "Run all untriaged (N)" button (sequential, not concurrent — human's
explicit ask), a "Ticket history" panel below reusing `agentSummary.js`'s existing per-agent
summarizer. `ModelThresholdConfigPanel.jsx` gained a ServiceNow/Jira instance-URL section.
**Verified**: an isolated script exercised `_persist_ticket_snapshot` directly (itsm-only path,
itsm+tracker path, no-sys_id no-op path) plus all 4 new endpoints via `TestClient` — all passed.
**Then live-verified for real**: a real "Diagnose" click on Ops Board produced `INC-4A9DA080`
(`pending_approval`) and genuinely persisted BOTH an itsm ticket (`TCK-0501`) and a tracker issue
(`OPS-159`, `performance` workflow_type) linked to the same incident — the candidate's card correctly
flipped from a "Diagnose" button to an "In progress — OPS-159" pill, and "Run all untriaged" correctly
decremented its count.

**Step 3 — merged Knowledge Base tab.** 5 new dummy reference articles
(`data/knowledge_base/KB-{SHAREPOINT,TEAMS,POWER-AUTOMATE,POWER-APPS,AZURE-AD}.md`), chunked with
`chunking.py`'s `chunk_postmortem` (now passes through all frontmatter, not just `postmortem_id`) and
upserted into the same `"runbooks"` Chroma collection as real runbooks, tagged `doc_type: kb_article`
— deliberately no `class` field, so `agents/planner.py`'s `where={"class": runbook_class}` retrieval
filter can never surface one as a citable plan step (verified explicitly). `/chunks` now takes an
optional `doc_type` filter; `/runbooks/upload` chunks now also get `doc_type: "runbook"`; new
`POST /knowledge-base/upload` mirrors it for articles (admin-only, rejects a `class` field). Tab
renamed "Chunk Inspector" → "Knowledge Base" (`CockpitShell.jsx`/`roles.js`/`tabInfo.js`);
`ChunkInspector.jsx` gained an All/Runbooks/Knowledge Base filter + an in-tab admin upload control
(both file types) alongside the existing browse/inspect UI. **Verified for real**: the gateway's
`/embeddings` endpoint recovered mid-session — `python db/load_chroma.py --test` ran clean (152
runbooks-collection chunks: 132 runbook + 20 kb_article, all self-checks passed, including the
Planner-safety invariant), and `GET /chunks?doc_type=kb_article` returns all 20 real chunks.

**Step 4 — Metrics & Eval folded into Overview.** `Overview.jsx` gained 2 KPI tiles (Stopped before
completion, Negative-KB entries seeded) + the honest scenario-eval-status footer caption — all 8
of Metrics & Eval's numbers now live in Overview. `MetricsEval.jsx` deleted; removed from
`CockpitShell.jsx`/`roles.js`/`tabInfo.js`. **Verified** live in browser (clean-DB state): tab gone
from nav for all 3 roles, Overview renders all values correctly, zero console errors.

**Also from this pass (Step 1 follow-up, human-requested)**: Ops Board's alert feed and correlated-
candidates lists are now fixed-height (600px) scrollable containers so the live SSE stream doesn't
reflow the page.

**Cross-cutting**: full backend suite run 4 times across this pass, consistently 70/84 — the same 14
failures every time, all gateway-dependent (diagnosis/planner/supervisor/intake/vision/voice/A2A),
zero regressions introduced.

## LAST VERIFIED STEP (moved from state-progress.md) — Offline Ollama fallback for chat models (PRD §3.2, implemented not just planned)
Human hit "Failed to fetch" clicking "Diagnose" during a total TCS gateway outage and asked whether a
working model could be used instead — models-routing.md already specified this exact requirement
("Offline fallback for demo resilience... must still run if the gateway dies mid-demo") but it had
never been implemented. `api_client.get_llm()` now wraps the enterprise `ChatOpenAI` with LangChain's
`.with_fallbacks([...])`, transparently retrying against local Ollama (`llama-3.2-3b-it`, picked
after testing 3 candidates against a realistic structured-JSON diagnosis prompt — see
models-routing.md's newest entry for the comparison) on any enterprise-call failure. `timeout=45`/
`max_retries=1` on the primary deliberately stays generous so R1's legitimate "tens of seconds"
latency doesn't falsely trigger fallback. `get_embeddings()` got the same treatment but is **not**
wired into the live retrieval path (`orchestrator/retrieval.py`'s `_embed()`) — confirmed by direct
test that a query-time-only fallback to Ollama's 1024-dim `gte-large` raises Chroma's
`InvalidDimensionException` against collections already indexed at the enterprise model's 3072 dims;
a real embeddings fallback needs a separate Ollama-indexed collection, out of scope for now.
**Also fixed the root cause of "Failed to fetch"'s severity**: `agents/diagnosis.py`/`planner.py`
call `llm.invoke()` (synchronous) inside `async def` handlers, blocking the single-threaded asyncio
event loop for the full retry+timeout duration — during a total outage this stalled everything else
uvicorn was serving (including the open SSE connection), which is what the browser surfaced as a
network-level "Failed to fetch" rather than a clean error. Later superseded: `llm.invoke()` →
`await llm.ainvoke()` migration happened in the Incident Workspace pass (see state-progress.md)
once auto-triage made the blocking cost recurring instead of one-off.
**Verified live, end to end**: a real "Diagnose" click on Ops Board (gateway had partially recovered)
produced `INC-4A9DA080` and genuinely persisted both an itsm ticket and a tracker issue. The fallback
branch itself (Ollama actually answering) was verified via a direct `api_client.get_llm()` call while
the gateway was confirmed down (46.8s to a real `PONG` from Ollama).
**Gateway fully recovered later the same session** (human confirmed via TCS) — full 32-model smoke
sweep re-run: 22/32 PASS, and critically every model this app actually uses passed, including all 3
Phase 0 blocking checks (Whisper, Vision, embedding→Chroma round-trip) and the primary routing models
(DeepSeek R1, gpt-4.1-nano, gpt-4o-mini, gpt-4o) — the 10 failures are all models this app doesn't use
(already-documented deprecations, or codex/gpt-4.1/realtime-whisper variants outside the routing
table). A second live "Diagnose" click on a healthy gateway completed in 15s end-to-end (enrichment →
A2A diagnosis → planner → verification → sync), correctly caught a `symptom_suppressed` fake fix, and
persisted its own ticket — full pipeline genuinely exercised, not just individual pieces.
**A real regression surfaced and got fixed along the way**: the `"runbooks"` Chroma collection had no
`hnsw:search_ef` set, so a `where`-filtered Planner query whose candidate pool grew past the library's
tiny default `ef` crashed with `RuntimeError: ... ef or M is too small` — intermittent at first
(looked like gateway flakiness) until it started failing consistently for tuning/performance/patching
runbook classes once the Knowledge Base's 20 chunks pushed the collection past the threshold. Fixed via
`collection.modify(metadata={"hnsw:search_ef": 500})` plus baking the same metadata into every
`get_or_create_collection("runbooks", ...)` call site so a future rebuild doesn't reintroduce it — see
errors-solved.md. **This turned out to be only a partial fix** — see state-progress.md KNOWN ISSUES'
"Refined understanding (Patch Management pass)" entry: the same error can still occur when two
`query_collection()` calls land concurrently in the same backend process, a separate hnswlib
concurrent-access limitation the `search_ef` fix doesn't address.
**Backend suite, final**: 84/84 real tests passed (the 4 `smoke_test.py` "errors" are pytest
auto-discovering that standalone script's `test_*`-named functions and failing to find a fixture —
pre-existing, harmless, unrelated to this session's work).

## LAST VERIFIED STEP (moved from state-progress.md) — Incident Workspace readability, bar removal, click-to-open, auto-triage + notifications
Human feedback after using the Ops Board/ticket-lifecycle pass live: Evidence cards still showed raw
`CI-0065 · confidence 1.00` / a raw Python-dict dump for alert evidence; the old demo "Start incident"
CI-picker bar was now redundant since real alerts drive diagnosis; no way to click a ticket/incident
to open its record; and "whenever a new alert comes it should notify and auto-start diagnosis instead
of a manual click" (confirmed via AskUserQuestion: bounded to genuinely new arrivals, not the ~420
backlog — "Run all untriaged" stays for that).

**Readability**: `agents/enrichment.py`'s alert evidence extract now uses the alert's plain-language
`summary` (Step 1's field) instead of dumping `str(raw_payload)` — this is both what a human reads
AND what Diagnosis reasons over, so it helps the model too, not just the display. `IncidentWorkspace.jsx`
now shows "Verified fact" instead of "confidence 1.00" for CMDB/alert/metric evidence (always 1.0,
deterministic — a percentage was meaningless jargon there); genuinely graded evidence (ticket-history
similarity) still shows a percentage.

**Start incident bar removed**: `GoldenPathBar` (CI dropdown + button) deleted from `CockpitShell.jsx`,
replaced with a read-only `IncidentStatusBar` that only renders when a run is actually active.

**Click-to-open-incident**: `useTickets`/`useCorrelatedCandidates` hooks lifted from `OpsBoard.jsx` to
`CockpitShell.jsx` so ticket state is available app-wide, not just on the Ops Board tab. New
`openIncident`/`openTicket` handlers in `CockpitShell.jsx`: fetch `/tickets/{id}`, call
`incident.setRun(trace_snapshot)`, switch to Incident Workspace. Wired to Ticket History's new "Open"
button and Ops Board's ticket-status pills. (`useCorrelatedCandidates` itself was later deleted once
Ops Board's cluster panel was removed — see state-progress.md's Ops Board redesign entry.)

**Auto-triage + notifications**: new `frontend/src/hooks/useAutoTriage.js` — watches the live alert
stream, treats the first 20 arrivals (matching the backend's own catch-up-burst size) as "backlog,
not new", and for every genuinely new arrival auto-calls the same `triggerRun` a manual "Diagnose"
click uses, one at a time (bounded/sequential, reusing the existing single-flight `incident` state —
never concurrent with a manual click). New `frontend/src/components/NotificationBell.jsx` in the
header (visible from any tab) shows recent auto-diagnosed alerts with live status; clicking a
completed one jumps straight to its Incident Workspace record.

**A real bug found and fixed while verifying this**: once auto-triage started running real diagnosis
continuously in the background, an unrelated `fetch()` (clicking "Open" on a ticket) started hanging
indefinitely — confirmed via a raw `page.evaluate(fetch(...))` bypassing all app code that the
backend itself was unresponsive, not a frontend issue. Root cause: `agents/diagnosis.py` and
`agents/planner.py` called `llm.invoke()` (synchronous) inside `async def` handlers, blocking
uvicorn's single-threaded event loop for the whole gateway round-trip — previously a one-off cost
(one manual click at a time), now a recurring one with auto-triage running continuously. Fixed:
`llm.invoke(...)` → `await llm.ainvoke(...)` in both files (the offline-fallback `.with_fallbacks(...)`
wrapper supports async natively, no other change needed). See errors-solved.md.

**Verified live**: fresh Diagnose click showed clean Evidence text end to end; notification bell
populated in real time while auto-triage ran; "Open" on a ticket correctly switched to Incident
Workspace and loaded that exact run (previously hung — confirmed fixed after the async change).
**Backend suite, final**: 84/84 real tests (`test_diagnosis`/`test_planner`/`test_supervisor` re-run
explicitly after the `ainvoke` change, 14/14), same 4 harmless `smoke_test.py` pytest-collection
artifacts as every other run this session.

## LAST VERIFIED STEP (moved from state-progress.md) — Patch Management: real patch data source, intelligent scheduling, Maintenance Planner panel
Human asked to close the PRD gap `domain-workflows.md`/PRD row 816/clause C6 already specified but
Phase 3 never built: Patch Management's `key_evidence` (`patch_inventory`, `change_calendar`) was
declared in `orchestrator/workflows/patch.yaml` but never actually gathered, and "intelligent
scheduling — dependency-aware, blackout-aware, SLA-aware" (a rule engine, not an LLM, per PRD line
482) didn't exist. Confirmed via AskUserQuestion: simulated patch-source data (same pattern as every
other system in this app), rule-engine scheduling, no new Performance Tuning work.
**New simulated system** (same MCP-server-per-system pattern as CMDB/ITSM/Tracker/Monitoring):
`data_gen/patch_inventory.py` generates `patch_inventory.json` (pending patches per CI — vendor,
severity, CVE ids, SLA days, same-CI `depends_on_patch_ids`) and `change_calendar.json` (blackout
windows, scope = `global`|environment|a specific CI); `mcp_servers/simulators/patch_source.py`
(port 9005) serves them; `mcp_servers/patch_mcp.py` wraps it (`get_pending_patches`,
`get_change_calendar`), wired into `orchestrator/mcp_wiring.py`. Two new SQLite tables
(`patch_inventory`, `change_calendar`, see schema-db.md), populated in `db/init_db.py`. CI-0059 (the
scenario library's fixed patch-workflow CI, `SCEN-04`) and CI-0121 get guaranteed pending-patch
coverage so the feature is never silently untested by chance.
**Scheduling rule engine**: `guardrails/scheduling.py` `propose_maintenance_window()` — pure Python,
no LLM (same category as `blast_radius.py`/`policy_gate.py` per PRD line 482's explicit
auditability requirement). Orders a CI's pending patches by same-CI dependency then severity, finds
the earliest window that clears every applicable blackout (global + environment + CI-specific),
flags `sla_at_risk` when that window falls after the highest-severity patch's deadline. 10 unit
tests against hand-built fixtures (dependency-vs-severity ordering, each blackout scope in
isolation, SLA-at-risk true/false cases, determinism).
**Wiring**: `agents/enrichment.py` gained a `workflow_type` param (threaded through from
`orchestrator/supervisor.py`) — when `"patch"`, gathers `patch_inventory`/`change_calendar` evidence
folded into the existing turn-1 budget (no new `tracker.use_turn()`, still ≤3 turns total, matching
`TURN_CAPS`). `agents/planner.py` calls `propose_maintenance_window()` when `runbook_class ==
"patching"` (same deterministic-post-processing pattern as blast radius/policy gate, after the LLM
drafts the plan, never delegated to it) and attaches `plan["maintenance_window"]`. `main.py`'s
`_format_workflow_outcome()` now echoes `workflow_type` in every `/workflows/run` and
`/intake/confirm` response, so the frontend knows when to render the new panel.
**Frontend**: `IncidentWorkspace.jsx` gained a `MaintenanceWindowSection` ("Maintenance Planner"
panel, PRD §7's named panel for patch runs) — proposed window, grouped/ordered patches with severity
badges, SLA-at-risk warning — rendered only when `run.workflow_type === "patch"`.
**Verified**: 10/10 new `test_scheduling.py` unit tests; extended `test_enrichment.py` (patch vs.
non-patch evidence gathering), `test_planner.py` (`maintenance_window` present/absent by
`runbook_class`), `test_supervisor.py`'s existing patch-workflow test (now asserts real evidence +
window). Full backend suite: 98/100 on the roughest run, with the only failures being the
pre-existing "ef or M is too small" Chroma/hnswlib flakiness (see KNOWN ISSUES in state-progress.md)
— every one of those specific tests re-ran clean in isolation (multiple times). **Live-verified in
the real browser**: a genuine `run_enrichment`/`run_planner` call against CI-0059 (real gateway,
real MCP calls) produced real evidence (`patch_inventory`, `change_calendar` artifacts) and a real
`maintenance_window` (1 pending patch, 4 applicable blackouts, a genuine `sla_at_risk: true` case) —
opened via Ticket History's "Open" flow and screenshotted rendering correctly in the Maintenance
Planner panel (proposed window, red SLA-at-risk banner with the real deadline, severity-badged
patch list).

## LAST VERIFIED STEP (moved from state-progress.md) — Auto-triage no longer hijacks the on-screen incident
Human feedback while trying to demo Patch Management: auto-triage's background diagnosis of newly-
arrived alerts was silently overwriting whatever incident was on screen (Incident Workspace/Agent
Trace/Approval Queue all read one shared `run` state), so a manually-launched patch run could vanish
seconds later with no user action. Root cause: `useAutoTriage.js` called the same `triggerRun()` a
manual Diagnose click uses, which always calls `setRun()`. Fix: `useWorkflowRun.js`'s `triggerRun`
gained a `{ silent: true }` option that runs the workflow (real backend call, ticket still persisted,
notification still populated) without calling `setRun()`/`setLoading()`; `useAutoTriage.js` now
passes it. Explicit actions (Ops Board Diagnose/Run-all, Ticket History Open, clicking a notification)
are unaffected — none of them pass `silent`. **Verified live**: launched SCEN-04 explicitly, confirmed
the displayed `incident_id` stayed identical for 50s while a second `/workflows/run` call fired in the
background (auto-triage genuinely running) — display never changed. `npm run build` clean.

## LAST VERIFIED STEP (moved from state-progress.md) — Success metrics: real resolution timing, manual-steps-avoided, satisfaction proxy
Human asked where success metrics (manual task reduction, incident resolution time, user
satisfaction) are visible. Per PRD §2.6/C13's exact instrumentation list ("no fabricated numbers on
any slide"), added only what's honestly computable from real data — confirmed scope via
AskUserQuestion (real timing metric: yes; user satisfaction: approximate from a labeled proxy, not
fabricate a survey score; manual task reduction: reframe + add a real steps-automated count).
`backend/main.py`: `_compute_resolution_timing()` derives real signal→plan and signal→verified-
resolution durations per incident from `audit_log` timestamps (no invented "manual baseline" —
PRD says compare "vs a stated manual baseline," which nobody has stated, so none is shown);
`_compute_manual_steps_avoided()` sums real runbook step counts from `execute_plan` audit entries'
`evidence_ids`; `approval_rate_satisfaction_proxy` (human approvals / total decisions) added,
explicitly labeled a proxy, `None` (not a misleading 0%) when no decisions exist yet. All three new
fields returned from `/metrics/summary`. `Overview.jsx`: new "Manual steps avoided" KPI tile, new
"Incident resolution time" (StatPair) and "Human satisfaction (proxy)" (gauge, explicit
not-a-survey caption) chart cards, "Toil removed" stat, correlation gauge relabeled "Manual triage
avoided" for clarity. **Verified**: `npm run build` clean, `/metrics/summary` returns real non-zero
values reflecting actual session activity, live browser screenshot confirms correct rendering
including the `None`→"no data yet" case path.

## LAST VERIFIED STEP (moved from state-progress.md) — Knowledge Base upload "not working" — root cause found: silent admin-only gating, plus a missing sidebar upload path
Human reported runbook/article upload "not working" in Knowledge Base. Direct testing (curl +
Playwright driving real clicks) found `/runbooks/upload` and `/knowledge-base/upload` both work
correctly end to end as admin, with a clear rejection message for a malformed file — the backend
pipeline was never broken. Two real frontend gaps found instead: (1) `ChunkInspector.jsx`'s upload
controls are admin-only (`identity?.role === "admin"`) with **no explanation shown** to the other two
roles (ops_engineer/approver) that can see the tab per `roles.js` — silently missing, reading as
broken rather than role-gated; (2) the Sidebar's separate "Ingestion / Admin" panel
(`IngestionAdminPanel.jsx`) only ever had runbook upload, no article upload at all, plus a stale
"Check Chunk Inspector" reference to the pre-rename tab name.
**Fixed**: `ChunkInspector.jsx` now shows "Sign in as Admin to upload..." for non-admin roles
(matches Overview.jsx's existing role-gate-message pattern). `IngestionAdminPanel.jsx` gained a
second upload form (`/knowledge-base/upload`, same real chunk+embed+upsert pipeline) and the stale
tab-name reference was corrected to "Knowledge Base".
**Verified live**: `npm run build` clean; Playwright confirmed the explanatory note renders for
`alex.chen` (ops_engineer) on the Knowledge Base tab, and a real article upload via the Sidebar
panel succeeds ("Indexed KB-POWER-APPS: 4 chunks embedded and upserted into Chroma").
**Still open**: could not reproduce total failure as admin in the Knowledge Base tab itself — if the
human's original repro was as a non-admin role, this closes it; if it recurs as admin, it's likely
the same pre-existing Chroma-under-concurrent-load flakiness logged above, not a new defect.

## LAST VERIFIED STEP (moved from state-progress.md) — Fixed CMDB relationship generation: localized neighborhoods, not one 190-CI blob
Human asked what the CI/ALERT/INC/TCK/OPS ID scheme means (answered inline — deliberate, each
mirrors a real system's actual ID convention, not simplifiable without losing that realism) and
separately raised a doubt: shouldn't two alerts on genuinely different SharePoint sites get separate
tickets instead of being merged into one incident? Investigation confirmed the doubt was correct and
found the real cause: `correlation/cluster.py` groups alerts by `(topology_group, category,
time-window)`, where `topology_group` = connected component of the CMDB relationship graph — but
`data_gen/cmdb.py`'s old `generate_relationships()` connected each CI to a **uniformly random**
other CI, which (simple random-graph math, confirmed empirically) collapsed into one **190-of-200-CI
connected component**. So "topology-based" correlation was barely discriminating anything — 62 of
420 clusters spanned more than one CI, merged only because both happened to be in that one blob, not
because of any real dependency. Human picked (of 3 offered fixes) only this one: fix the relationship
data generation; the other two (scoping Diagnose to the whole cluster's alerts/CIs instead of just
the first one, and an in-app ID legend) were offered but not selected — still open if wanted later.
**Fix**: `generate_relationships()` now builds small localized neighborhoods (2-6 CIs, a random
spanning tree + light extra edges) grouped by `(environment, owner)` — modeling one team's one
environment's real dependency chain, not random edges across the whole dataset. `CI-0009`
(`HUB_CI_ID`) is a deliberate exception — explicitly wired as a ~20-spoke hub so its blast radius
stays > the policy gate's block threshold (SCEN-03/test_supervisor.py's high-blast-radius-block case
needs this); `CI-0059`/`CI-0121` (`ISOLATED_CI_IDS`) are explicitly excluded from any neighborhood so
their low-blast-radius happy-path scenarios (SCEN-01/02) keep working — same guaranteed-coverage
pattern `data_gen/patch_inventory.py` already established.
**Verified**: new self-test in `data_gen/cmdb.py` (non-hub component sizes, hub blast radius > 15,
isolated CIs' blast radius <= 5) — confirmed 56 non-hub components, largest 6 CIs (was one 190-CI
blob); `CI-0009=40` (>15), `CI-0059=CI-0121=0`. `correlation/cluster.py --test` and full backend
suite both re-run clean (98/98 effective — the 2 that failed on the roughest run were the same
pre-existing gateway-JSON and Chroma-under-load flakiness already logged, confirmed by isolated
rerun). Multi-CI clusters dropped from 62/420 to 7/492 (the 7 remaining are genuine small
neighborhoods, not blob artifacts). Live-verified via `/alerts/correlated`.
**Honest side effect**: the "noise reduction" number on Overview will visibly drop (was ~16%, now
~2%) — this is the metric becoming honest, not a regression: the old 16% was partly inflated by
alerts being incorrectly merged across unrelated CIs.

## LAST VERIFIED STEP (moved from state-progress.md) — Real upload bug found & fixed; type filters added to Ops Board/Ticket History
Human reported Knowledge Base upload still not working: "click upload, it doesn't open any panel."
Reproduced exactly by simulating the natural click order (click "Upload runbook" BEFORE choosing a
file, matching what most people try first): **nothing happened at all** — no dialog, no error, no
feedback. Root cause: the old design required two separate clicks (a small native "Choose File"
input, then a separate "Upload" submit button) and `upload()` silently early-returned
(`if (!file) return`) when no file was staged yet — clicking "Upload" first, the natural instinct,
looked exactly like a dead button.
**Fixed** in both upload surfaces (`ChunkInspector.jsx`'s inline `UploadControls`,
`IngestionAdminPanel.jsx`'s sidebar forms): collapsed to one click — the button itself opens the
native file picker (hidden `<input type=file>`, opened via `ref.current.click()`), and the upload
fires the instant a file is chosen, no second click. Buttons relabeled "Choose file & upload
runbook/article" so the one-click behavior is signaled, not just implied.
**Verified live** with Playwright's real `filechooser` event (not `setInputFiles`, which would have
masked this exact bug by bypassing the click path entirely) — one click opens the OS picker, upload
completes automatically after selection, on both the Knowledge Base tab and the Sidebar panel.
**Also added**: type filter pills (same visual pattern as the Knowledge Base tab's existing
doc_type filter) to the 3 places in Ops Board that mix types with no way to narrow them — alert feed
and correlated candidates (All/Fault/Degradation), ticket history (All/Incident/Patch/Performance).
"Run all untriaged" deliberately still acts on the full untriaged set regardless of the visible
filter (a bulk action, not scoped to whatever's currently shown). Verified live: filtering Ticket
History to "Performance" correctly narrowed the list (73 -> 62 tickets) and highlighted the active
pill.
**Also answered, not yet built** (from the same conversation, human explicitly deferred): an in-app
CI/ALERT/INC/TCK/OPS ID legend, and scoping "Diagnose" to a whole cluster's alerts instead of just
the first CI — both explained inline but out of scope for this pass.

## LAST VERIFIED STEP (moved from state-progress.md) — Ops Board simplified to one alert list, new Tickets tab, slower alert pacing, generic login copy
Human's 4 asks in one message: (1) remove the Ops Board cluster panel (no longer valuable now that
the CMDB relationship fix above stopped it over-merging unrelated CIs — noise reduction dropped to
~2%, so a second grouped view of the same alerts wasn't earning its place); (2) merge triage status
directly into the alert feed instead; (3) a dedicated tab browsing all ServiceNow/Jira tickets with
a "Pull latest" action and a last-synced timestamp; (4) alert arrival paced at 1 every 10s, not a
burst; (5) generic login copy, no demo-account credentials shown. (Two of these — login copy, alert
pacing — were implemented once already in this session but reverted, apparently by the human's own
editor, before being confirmed; redone here.)
**Ops Board**: `CorrelatedCandidates` and the embedded `TicketHistory`/`TicketDetail` removed from
`OpsBoard.jsx` entirely. `AlertItem` now renders its own ticket-status pill (Open/In progress/
Resolved + external_id, clickable to Incident Workspace) or a "Diagnose" button per alert, sourced
from the same `tickets` list Ops Board already had — diagnosing one CI still sweeps up every fault
alert on it (`workflows/run`'s existing scope), so this gives the same practical "one action per
resource" outcome clustering did, without a second panel. "Run all untriaged" moved to the top of
the single alert list, still a bulk action over the full set regardless of the category filter.
**New Tickets tab** (`Tickets.jsx`, all 3 roles): browses the same `local_tickets` data framed as
"the ServiceNow/Jira system of record" rather than an Ops Board sub-panel — System (ServiceNow/
Jira) and workflow-type filter pills, click a row to expand its agent-trace summary inline or
"Open" it in Incident Workspace. New `POST /tickets/sync` ("Pull latest") re-reads `local_tickets`
and stamps `integration_settings.last_synced_at` — explicitly labeled in-UI as simulated (no real
instance connected, `servicenow_instance_url`/`jira_instance_url` stay inert per decisions-log.md),
not a fabricated "synced with ServiceNow" claim.
**Alert pacing**: `_alert_event_stream`'s live-tail loop (`main.py`) changed from up to 20 alerts
every 3s to exactly 1 every 10s — the old pace blew through the full 500-alert seed file in under
two minutes, both overwhelming the feed and making auto-triage fire far faster than watchable.
Initial 20-alert catch-up burst on connect is unchanged (that's replaying history, not simulating
live arrival). `useAutoTriage.js` simplified to read `category`/`ci_display_name` straight off each
alert (already present on the payload) instead of a separate `GET /alerts/correlated` fetch it used
only for those two fields — `useCorrelatedCandidates.js` hook deleted, now genuinely unused.
**Login page**: removed "Real accounts, real passwords..." and the "Demo accounts: alex.chen..."
credential-listing footer from `frontend/src/app/page.js`; replaced with a generic "Enter your
credentials to access your workspace."
**Verified**: `npm run build` clean; full backend suite 98/98 clean (no flaky reruns needed this
time); live Playwright pass confirmed — login page shows neither removed line, Ops Board shows no
"noise reduction" cluster panel while still offering "Run all untriaged", Tickets tab renders, Pull
latest flips "Last synced: never" to "just now" and lists tickets with system/workflow-type filters
working. `POST /tickets/sync` verified directly (returns real `synced_at` + real ticket count).

## RESOLVED ISSUES (historical)
- ~~Stack mismatch~~ **RESOLVED 2026-08-07:** human decided to migrate to Next.js per the frozen PRD (see [decisions-log.md](decisions-log.md)). Migration work happens in Phase 4, not now — Phase 0/1 stay backend-only.
- **Model deprecations (2026-08-07), both RESOLVED:** Llama Vision and DeepSeek V3 deployments both permanently gone (HTTP 404/410, confirmed on repeated recheck). Human asked Claude to pick the best substitute for each; `genailab-maas-gpt-4o` (vision) and `azure/genailab-maas-gpt-4.1-nano` (V3's role) chosen after real task-shaped tests, wired into `.env`/`smoke_test.py`, re-verified end to end. See [decisions-log.md](decisions-log.md).
