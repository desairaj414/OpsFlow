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

## RESOLVED ISSUES (historical)
- ~~Stack mismatch~~ **RESOLVED 2026-08-07:** human decided to migrate to Next.js per the frozen PRD (see [decisions-log.md](decisions-log.md)). Migration work happens in Phase 4, not now — Phase 0/1 stay backend-only.
- **Model deprecations (2026-08-07), both RESOLVED:** Llama Vision and DeepSeek V3 deployments both permanently gone (HTTP 404/410, confirmed on repeated recheck). Human asked Claude to pick the best substitute for each; `genailab-maas-gpt-4o` (vision) and `azure/genailab-maas-gpt-4.1-nano` (V3's role) chosen after real task-shaped tests, wired into `.env`/`smoke_test.py`, re-verified end to end. See [decisions-log.md](decisions-log.md).
