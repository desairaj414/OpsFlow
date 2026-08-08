---
type: state
title: State & Progress
status: active
updated: 2026-08-08
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
**Phase 5 — Scenario Library, Eval & Hardening — PARTIALLY STARTED, then paused by human request.**
Atomic step 1 (6 non-edge-case scenario fixtures, `data/scenarios/SCEN-01..06.json` + `scenarios`
table wiring in `init_db.py`) is done and verified (84/84 backend tests green). Steps 2-8 not
started. Human then redirected to a series of **pre-Phase-5, off-plan passes** — a jury-readiness
UI pass, then role-based access + real authentication + a full product rebrand (Verascope) + a
light/dark theme toggle — before continuing Phase 5. See LAST VERIFIED STEP below.
See [prd-phase-5.md](prd-phase-5.md). A fifth off-plan pass (Ops Board readability + local ITSM/
Jira-shaped ticket lifecycle + a merged Knowledge Base tab + folding Metrics & Eval into Overview,
all 4 steps built, live-verified end to end on a healthy gateway) was immediately followed by a
sixth, still human-directed, still pre-Phase-5: **Incident Workspace readability + removing the demo
"Start incident" bar + click-to-open-incident + auto-diagnosing newly-arrived alerts with a
notification bell** — see the newest LAST VERIFIED STEP below.

## LAST VERIFIED STEP (superseded) — ServiceNow-only tickets, needs_approval status, Ops Board
## status filter, Approval Queue folded into Incident Workspace; Agent Trace/Knowledge Base moved
## off the main tab bar
Moved to [state-progress-history.md](state-progress-history.md) for space — two passes, both
self-verified/live-verified at the time, both superseded (in file-touch terms, not undone) by the
Demo-readiness pass below, which further edited `Tickets.jsx`, `Sidebar.jsx`, and
`ChunkInspector.jsx`. Confirmation status for both is still open, not resolved by archiving.

## LAST VERIFIED STEP (superseded) — Floating assistant (chatbot), reversing the documented "no
## chatbot" decision; push-to-talk merged into it
Moved to [state-progress-history.md](state-progress-history.md) for space — self-verified/
live-verified at the time, confirmation status still open, not resolved by archiving. Foundational
context for the chat/image work in the Demo-readiness pass directly below.

## LAST VERIFIED STEP (self-verified, awaiting human confirmation) — Demo-readiness pass: dev-text
## sweep, dark scrollbar, Sidebar panel consolidation, chat ticket table, image intake moved to chat
Human's asks while preparing to submit: (1) chat's ticket-query replies truncated at 5 with "(+N
more)" — show all matches in a table instead; (2) Sidebar's "Ingestion / Admin" panel and the
Knowledge Base panel both had upload controls — duplicated, consolidate; (3) sweep every screen for
leftover dev/testing-facing text now that the app is heading to demo; (4) dark theme's scrollbar
still used the browser's light default; (5) move image intake out of Ops Board into the chat
widget so voice+vision+text all live on one assistant surface. Mid-pass the human also asked to (6)
add a "restart chat" control, and (7) flagged that the sample screenshot used for testing image
intake read as a generic/fake error rather than something a real Microsoft product would show.
**Dev-text sweep**: grep swept every `.jsx` for internal/dev-facing language actually rendered to
users (not code comments) — fixed 8 instances: `IncidentWorkspace.jsx`'s "Evidence gaps: not
computed by the current agent chain..." line (removed outright, nothing behind it anyway) and its
"fresh run... no checkpointing exists" / "same shared incident" approval-confirmation text
(reworded to plain "Executing the approved plan."); `Tickets.jsx`'s "Simulated — ...(an admin can
set one under Model & Threshold Config)" banner and `ModelThresholdConfigPanel.jsx`'s matching
"nothing here connects to it yet" copy (both reworded, same honest meaning, no dev tone);
`Overview.jsx`'s two chart descriptions that read as internal disclaimers ("not compared against a
claimed manual baseline, since none was measured here", "this demo has no real end users to
survey" — both trimmed to the plain metric description); `ScenarioLauncherPanel.jsx`'s "golden-path
bar" internal jargon (reworded, that label was never shown anywhere else in the UI); two stale
comments (`IncidentWorkspace.jsx`, `Sidebar.jsx`) still referencing the old Sidebar push-to-talk
after it moved into ChatWidget. (`Overview.jsx`'s scenario-eval line, `PlaceholderTab`,
`AutonomyLadder` wording, the "Edit (not yet supported)" button, and dead `Dashboard.jsx`/
`AdminControl.jsx` were already fixed in the immediately-prior turn of this same pass.)
**Dark scrollbar**: `globals.css` gained a `:root[data-theme="dark"]` block (Firefox
`scrollbar-color` + WebKit `::-webkit-scrollbar*`) using the existing `--border`/`--background`/
`--muted-foreground` tokens — same explicit-toggle-only mechanism as the rest of the theme system,
deliberately no `prefers-color-scheme` media query. Verified by setting `data-theme="dark"` directly
and reading `getComputedStyle(...).scrollbarColor` (`rgb(41,47,61) rgb(12,17,29)`, matching the dark
tokens) — the real toggle button itself is intermittently covered by Next.js's dev-mode indicator
badge in the same bottom-left corner, a `next dev`-only artifact (confirmed via bounding-box
inspection), not present in the production build already verified via `npm run build`.
**Sidebar panel consolidation**: `IngestionAdminPanel.jsx` deleted outright, replaced by new
`UserManagementPanel.jsx` (Users section only — runbook/KB-article upload removed, since
`ChunkInspector.jsx`'s `UploadControls` already does the identical `/runbooks/upload` and
`/knowledge-base/upload` calls). `roles.js`'s `PANEL_PERMISSIONS` key renamed `ingestion` →
`users`; `Sidebar.jsx`'s `NAV_ITEMS` entry relabeled "User Management" with a `Users` icon (was
`UploadCloud`). Two stale comments referencing the old panel name fixed (`ChunkInspector.jsx`,
`ui/modal.jsx`).
**Chat ticket table**: backend's `_format_ticket_query_reply` (`main.py`) no longer builds a
truncated "(+N more)" example list — just the status breakdown line, plus "Full list below." when
there are more than 5. The `/chat` endpoint's `query_tickets` action now returns every row the SQL
query found (up to its existing `LIMIT 200`) instead of slicing to `tickets[:20]`. `ChatWidget.jsx`
gained a `TicketsTable` component (scrollable, sticky header, click-to-open via the same
`onOpenTicket` path `Tickets.jsx`/`OpsBoard.jsx` already use) rendered for any `query_tickets`
action; the message bubble goes full-width instead of the usual 85% cap when a table is attached.
`CockpitShell.jsx` now passes `onOpenTicket` through to `ChatWidget` (previously only
`onOpenIncident`).
**Image intake moved to chat**: `OpsBoard.jsx`'s `ImageDropZone` component deleted outright (drag-
drop zone, preview, extract, confirm-and-start — all of it); `ChatWidget.jsx` gained the same
`/intake/image` flow as an image-upload button (`ImagePlus` icon) next to the mic — the upload
lands as a user message with the image thumbnail, the extraction as an assistant message carrying
an `image_signal` action, and (since `requires_human_confirmation` is unconditional for images) an
explicit "Confirm and start incident" button that calls the same `incident.runFromSignal` used
before, updating that same message in place with a "started — Open Incident Workspace" link once
confirmed. The "no screenshot handy? download a sample" hint moved to a small line under the chat's
input row.
**Restart chat**: header gained a second icon button (`RotateCcw`) next to Close that resets
`messages` back to a single shared `GREETING` constant — no confirmation dialog, matches how
lightweight the rest of the widget is.
**Sample screenshot replaced**: the old `public/sample-incident-screenshot.png` was literal plain
red/black text on white ("ERROR Connection refused / Service: CI-0056 unreachable") with no product
identity — regenerated as an actual Microsoft Power Automate-styled error dialog (rendered from HTML
via Playwright screenshot, not hand-drawn) citing the same `CI-0056`, whose real generated CMDB
identity (fixed seed `20260807`) is `power-automate-gateway-develop-056` — so the sample now matches
what it claims to be a screenshot of. Re-verified through the real vision pipeline directly
(`run_vision_intake`): extracts the connection-failure text, `candidate_ci_refs: ['CI-0056']`,
`requires_human_confirmation: True` — unchanged behavior, better-looking input.
**Verified**: `npm run build` clean; full backend suite 98/98 (184s, real gateway calls, venv at
`backend/venv`); live Playwright pass covering the whole set in one run against the already-running
dev backend (port 8765) — login page confirmed free of the old demo-credential lines, User
Management panel shows only Users (no "Runbook ingestion" text), Knowledge Base panel confirmed
still has both upload controls, chat's image button uploaded the new sample and correctly extracted
`CI-0056`, "Confirm and start incident" produced a real `INC-IMG-*` run that reached `complete`
(visible in the post-run Overview dashboard's incremented counters), asking the chat for "all
incidents from the last 30 days" rendered a real 20-row table (not truncated text), and "Restart
chat" correctly reset to the greeting.
**Answered inline, not a code change**: human asked what the three Model & Threshold Config policy
numbers mean (blast radius approval/block thresholds, max concurrent prod changes) — explained via
`guardrails/policy_gate.py`'s actual gating logic, no doc file changed.

## LAST VERIFIED STEP (self-verified, awaiting human confirmation) — Drift Queue hidden; Autonomy
## Ladder seeded (was permanently empty, not a bug)
Human asked to hide Drift Queue (not deemed demo-ready) and asked whether Autonomy Ladder's empty
table was an error. Investigated: it wasn't an error — `autonomy_ladder` had **zero rows and no
writer anywhere in the codebase** (confirmed via grep, `db/init_db.py`'s own self-test explicitly
asserted it must be empty after seeding). This meant both the Autonomy Ladder tab AND Overview's
"Most-trusted runbooks" card (same table) were permanently blank, not "static but populated" as
previously assumed when writing `architecture-as-built.md`. Asked which fix the human wanted; chose
seeding one starting-tier row per runbook.
**Drift Queue hidden**: removed from `roles.js`'s `TAB_PERMISSIONS` (all 3 roles) and
`CockpitShell.jsx`'s `TABS` array only — `DriftQueue.jsx` and its route logic untouched, so
restoring it later is a one-line revert, not a rebuild.
**Autonomy Ladder seeded**: new `populate_autonomy_ladder()` in `db/init_db.py` — one row per
runbook (`current_tier='suggest_only'`, `verified_resolution_count=0`, `last_promoted_at=NULL`),
wired into `main()` after `populate_runbooks`. Self-test's `empty_expected` list corrected (removed
`autonomy_ladder`, since it's no longer meant to be empty) and a new assertion added
(`counts["autonomy_ladder"] == counts["runbooks"]`). Applied to the **live** `data/app.db` via a
targeted call to just `populate_autonomy_ladder()` on the existing connection — deliberately did
NOT run `init_db.py`'s full `main()`, which drops and rebuilds the whole DB file and would have
wiped this session's real `audit_log`/`local_tickets`/every workflow run so far. Confirmed
untouched afterward (audit_log still had 1315 rows). Still genuinely static after this fix —
`current_tier`/`verified_resolution_count` still have no runtime writer anywhere; seeding the
starting state is not the same as building the (deliberately out-of-scope, PRD §4.0) live
promotion engine.
**Docs**: `architecture-as-built.md`'s "Most-trusted runbooks" row corrected (was: "static seed
data, not live promotions" — now accurate; before this fix it should have said "no seed data at
all, permanently empty").
**Verified**: `npm run build` clean; full backend suite 98/98 (170s); live Playwright pass —
Drift Queue absent from nav for all 3 roles, Autonomy Ladder tab shows all 22 runbooks at "Suggest
only"/0 verified, Overview's "Most-trusted runbooks" card now populated; direct DB query confirmed
seed applied without disturbing existing session rows.

## NEXT STEP
Human confirmation still open on this pass, the ServiceNow/Approval-Queue pass, the Agent-Trace/
Knowledge-Base pass, the chatbot pass, the Patch Management pass, and the ones before that (the
underlying logic for all of it is now live-verified end-to-end on a healthy gateway, not just
self-verified). Once confirmed: resume **Phase 5** (Scenario Library, Eval
& Hardening) — read
[prd-phase-5.md](prd-phase-5.md) in full (only step 1 of 8 is done — 6 scenario fixtures). Two items
still owed from earlier sessions, unchanged by this pass:
- Real recorded voice sample (PRD §6.1: ≥2 noisy/accented samples) — still not done.
- `evidence`/`hypotheses`/`plans`/`approvals`/`incidents` tables (`schema-db.md`) are still empty —
  decide whether Phase 5's eval work needs structured per-incident queries before starting step 4
  (eval harness).

## H+ HOURS ELAPSED
Approximately H+13:00 (exact wall-clock not logged this session — estimate from work volume: role
system + real-auth conversion + full visual rebrand with a new dashboard + theme toggle, each with
its own backend-test-suite reruns and live Playwright QA pass, since the H+10:00 mark). Schedule anchors: demo-complete
checkpoint Fri 20:30 (H+11:30) — **reached early, human-confirmed**; FEATURE FREEZE Sat 09:30 (H+24:30, hard);
SUBMISSION Sat 11:00 (H+26:00, hard). Full per-phase clock table in [prd-phase-0.md](prd-phase-0.md)
through [prd-phase-7-final.md](prd-phase-7-final.md). Phases 1-3's combined ~10.5h budget
(H+1:30-11:30) was compressed to ~2.5h of wall-clock work this session (AI-assisted, single
operator) — running well ahead of the phase clock. **Do not let this pace set false expectations**
for Phase 4 (UI/frontend work, a different kind of effort) or for the human's own review time,
which this compressed pace does not substitute for.

## DONE (verified)
Phase 0-3 detailed checklists moved to [state-progress-history.md](state-progress-history.md).
Phase 4 fully closed (see history for the detailed record). Role-based access, real auth, the
Verascope rebrand, and the theme toggle are implemented and self-verified — tracked in LAST VERIFIED
STEP above, **awaiting human confirmation** (not yet marked done-and-confirmed).

## MOCKED & DEFERRED
Phase 0-3 items (simulators, real Jira, PDF runbooks, real voice sample, A2A PKI, live ports) moved
to [state-progress-history.md](state-progress-history.md) — still true, just not new this session.
Push-to-talk is real. 4 of the 6 voice intents (show_open_incidents, show_incident,
what_changed_on_ci, start_scenario) are recognized+displayed but not wired to an action — no
incidents-list endpoint exists yet to act on them with. Plan editing in Approval Queue is honestly
disabled, not built. **RESOLVED this pass:** the Sidebar role dropdown being cosmetic-only (it's now
real, server-enforced — see LAST VERIFIED STEP) and all 4 Sidebar admin panels being placeholders
(all 4 now fully built). **New, deliberate (not a gap):** Model & Threshold Config's model-routing
display is read-only by design — live-editing which model each agent calls would mean changing
frozen, tested agent modules (`backend/agents/*.py`'s `DIAGNOSIS_MODEL`/`PLANNER_MODEL` constants);
policy thresholds on the same panel ARE genuinely live-editable, in-memory only, resets on backend
restart.

## FILE INVENTORY
Phase 0-4, jury-readiness, and role/auth/rebrand/theme file lists all moved to
[state-progress-history.md](state-progress-history.md) for space. This pass's new/changed files:
- **Backend, new**: `data/knowledge_base/KB-{SHAREPOINT,TEAMS,POWER-AUTOMATE,POWER-APPS,AZURE-AD}.md`.
- **Backend, edited**: `backend/data_gen/alerts.py` (+`summary` field), `backend/data_gen/cmdb.py`
  (+`display_name`, `CI_TYPE_LABEL`), `backend/db/schema.sql` (+`alerts.ci_id/category/severity/
  summary`, `cmdb_ci.display_name`, new `local_tickets`/`integration_settings` tables), `backend/db/
  init_db.py` (`populate_integration_settings`, updated `populate_cmdb`/`populate_alerts`),
  `backend/chunking.py` (`chunk_postmortem` now passes through all frontmatter), `backend/db/
  load_chroma.py` (`build_knowledge_base_chunks`, `doc_type` tagging on both paths), `backend/main.py`
  (`_fetch_alerts_after`/`/alerts/correlated` carry the new fields; `_persist_ticket_snapshot`, `GET
  /tickets`, `GET /tickets/{id}`, `GET/POST /config/integrations`, `POST /knowledge-base/upload`,
  `doc_type` filter on `GET /chunks`, `doc_type` tag on `/runbooks/upload`), `hnsw:search_ef=500` on
  both `get_or_create_collection("runbooks", ...)` calls. `backend/config.py` (+`OLLAMA_BASE_URL`/
  `OLLAMA_FALLBACK_CHAT_MODEL`/`OLLAMA_FALLBACK_EMBED_MODEL`). `backend/api_client.py` (`get_llm`/
  `get_embeddings` now offline-fallback to local Ollama; new `_EmbeddingsWithFallback`).
  `backend/orchestrator/retrieval.py` (`_embed` comment only — deliberately NOT given a fallback,
  see errors-solved.md). `backend/db/load_chroma.py` (`build_knowledge_base_chunks`, `doc_type`
  tagging on both paths, `hnsw:search_ef=500`).
- **Frontend, new**: none (all changes to existing components).
- **Frontend, edited**: `OpsBoard.jsx` (human-readable alerts/candidates, scroll containers, Diagnose/
  Run-all-untriaged, Ticket History), `ChunkInspector.jsx` (renamed concept to Knowledge Base —
  doc_type filter, in-tab upload), `Overview.jsx` (2 new KPI tiles + eval-status footer),
  `ModelThresholdConfigPanel.jsx` (ServiceNow/Jira integration section), `CockpitShell.jsx`/
  `roles.js`/`tabInfo.js` (tab rename + Metrics & Eval removal). `MetricsEval.jsx` deleted.

**Patch Management pass, new/changed files:**
- **Backend, new**: `data_gen/patch_inventory.py`, `mcp_servers/simulators/patch_source.py`,
  `mcp_servers/patch_mcp.py`, `guardrails/scheduling.py`, `tests/test_scheduling.py`.
- **Backend, edited**: `db/schema.sql` (+`patch_inventory`/`change_calendar` tables), `db/init_db.py`
  (`populate_patch_inventory`/`populate_change_calendar`, row-count assertions), `orchestrator/
  mcp_wiring.py` (+patch_mcp wiring), `agents/enrichment.py` (+`workflow_type` param, patch evidence
  gathering), `agents/planner.py` (+`maintenance_window` for `runbook_class == "patching"`),
  `orchestrator/supervisor.py` (threads `workflow_type` into `run_enrichment`), `main.py`
  (`_format_workflow_outcome` +`workflow_type` field, both call sites updated), `tests/
  test_enrichment.py`/`test_planner.py`/`test_supervisor.py` (extended with patch-specific
  assertions).
- **Frontend, edited**: `IncidentWorkspace.jsx` (+`MaintenanceWindowSection`/"Maintenance Planner"
  panel, +`patch_inventory`/`change_calendar` evidence labels), rendered only when
  `run.workflow_type === "patch"`.
- **Data, new (generated, fixed seed)**: `data/patch_inventory.json`, `data/change_calendar.json`.

## KNOWN ISSUES
- **Gateway/proxy flakiness under sustained load (2026-08-07, WATCHING):** first live full-suite
  re-run (H+5:48 gate confirmation) hit a proxy-level stall (frozen CPU, same signature as the
  logged `gpt-5.1` sweep hang in `env-network.md`) on one test and a flaky FAILED on another;
  **both passed cleanly in isolation** (15s each) and a clean full rerun (84/84, 136.85s) confirmed
  it wasn't a code defect. Same category as the Phi-4-reasoning flakiness below — non-blocking, but
  re-check near submission if it recurs. **Refined understanding (2026-08-07, Patch Management
  pass):** root cause narrowed further — the Chroma `"runbooks"` collection's `hnsw:search_ef=500`
  fix (see errors-solved.md) holds for any single request, but **two `query_collection()` calls
  landing concurrently in the same backend process** (e.g. a manual `/workflows/run` call racing an
  open browser tab's `useAutoTriage` background diagnosis) can still trip hnswlib's
  `RuntimeError: Cannot return the results in a contigious 2D array` — a real concurrent-access
  limitation in the underlying C extension, not a config gap. Confirmed by direct reproduction: the
  same query reliably succeeds standalone/in pytest (single caller) and reliably fails only when a
  second live caller (the auto-triage hook) is active on the same process at the same moment. Not
  fixed (would mean adding retry/locking to the shared `orchestrator/retrieval.py`, out of scope for
  the Patch Management ask) — worth a real fix (retry-once-on-this-specific-RuntimeError, or a lock
  around `query_collection`) if it starts affecting the actual demo, since auto-triage running
  continuously means this concurrency window is now open for the whole session, not just occasional
  sustained-load bursts.
- **Gateway auth-DB outage (2026-08-07, RESOLVED):** during the Ops Board readability step, live
  gateway calls started failing with a 503 `"Service Unavailable, the authentication database is
  temporarily unreachable"`, then later a distinct total-outage 404 ("Azure Container App -
  Unavailable") that also took down `/embeddings` and `/audio/transcriptions` for a stretch — hit all
  14 gateway-dependent backend tests at worst. Confirmed not code-related throughout (isolated
  re-runs, same errors, no assertion failures). **Human confirmed with TCS the gateway is back; full
  32-model smoke sweep + a full backend suite re-run both confirm it — 84/84 real tests, every model
  this app actually uses (incl. all 3 Phase 0 blocking checks) PASS.** Prompted implementing the
  offline Ollama fallback (models-routing.md, decisions-log.md) that PRD §3.2 had specified but never
  wired into code — kept, not reverted, since a future outage should degrade instead of hard-failing.
- **Phi-4-reasoning flakiness (2026-08-07, WATCHING):** intermittent 404s (3 rechecks: 404, 404, 200) — gateway-side instability, not a deprecation. Non-blocking (smoke-test-only model, unused in primary path), no substitute applicable. Re-run `python smoke_test.py` closer to the demo/submission checkpoint to see if it's cleared.
- Team-member-to-phase assignment (PRD §9 Q1) is still open; phase nodes use role placeholders ("Owner: Simulators/MCP", etc.) instead of names — fill in real names in each `prd-phase-N.md` as soon as known.
- Resolved issues (stack mismatch, model deprecations) moved to [state-progress-history.md](state-progress-history.md).

## RESUME INSTRUCTION
If resuming a stalled session: read this file, then [decisions-log.md](decisions-log.md), then the
current phase node named above. Do not re-read `PRD_FINAL.md` in full — it is frozen and already
distilled into `.knowledge/`. Only open [state-progress-history.md](state-progress-history.md) if
you need Phase 0-3 closed detail — not needed for normal Phase 4+ resume. Update H+ HOURS ELAPSED
and CURRENT PHASE only after the human confirms the next step actually works.
