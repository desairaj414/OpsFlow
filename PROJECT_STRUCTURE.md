# OpsFlow — Project & Folder Structure

A guide to what every folder is for. Paths are relative to `my-hackathon-app/`.

```
my-hackathon-app/
├── ARCHITECTURE.md          ← system design, agent chain, protocols (this doc's sibling)
├── APP_FLOW.md              ← end-to-end data flow, sequence diagrams
├── DEMO_SCRIPT.md           ← pitch + live demo walkthrough
├── PROJECT_STRUCTURE.md     ← you are here
├── PRD_FINAL.md             ← FROZEN product requirements — do not edit, source of truth for scope
├── PRD_DRAFT.md             ← superseded draft, kept for history only
├── PHASE0_FINDINGS.md       ← environment/gateway smoke-test results from project kickoff
├── CLAUDE.md                ← index for the .knowledge/ execution-notes system (AI build log, not user-facing)
│
├── .knowledge/               ← session-to-session build memory for the AI-assisted build process.
│                                Deep implementation detail lives here (architecture-as-built.md,
│                                schema-db.md, decisions-log.md, per-phase PRDs, etc). Treat as an
│                                engineering log, not a product doc — ARCHITECTURE.md/APP_FLOW.md
│                                are the readable distillations of it.
│
├── backend/                  ← FastAPI application (Python)
├── frontend/                 ← Next.js cockpit UI (JavaScript/React)
└── data/                     ← all synthetic datasets (generated, fixed seed — see data/PROVENANCE.md)
```

---

## `backend/` — the FastAPI application

```
backend/
├── main.py                  ← the API surface — every HTTP/SSE route, ~30 endpoints (auth,
│                                alerts, workflows, tickets, chat, config, chunks, metrics, intake)
├── config.py                 ← env vars, SSL/tiktoken workarounds, model-id constants
├── api_client.py              ← get_llm()/get_embeddings() — wraps the gateway client with the
│                                local-Ollama offline fallback
├── auth_utils.py               ← JWT issue/verify, password hashing
├── chunking.py                ← structural chunker for runbooks/postmortems/KB articles (never
│                                splits mid-step; the "preamble inheritance" rule lives here)
│
├── agents/                    ← the 5 in-process specialist agents
│   ├── enrichment.py           (deterministic + RAG evidence gathering)
│   ├── diagnosis.py            (LLM — DeepSeek R1 — invoked over A2A, not called directly from here)
│   ├── planner.py               (RAG + LLM plan drafting, then deterministic guardrails)
│   ├── verification.py          (the Fake Fix Detector — two-signal check)
│   ├── sync.py                   (writes outcome back to ITSM/CMDB)
│   └── knowledge.py               (seeds the Negative KB on symptom_suppressed)
│
├── orchestrator/               ← the Supervisor and everything it depends on
│   ├── supervisor.py             (run_workflow — dispatches agents, validates each typed result)
│   ├── contracts.py                (pydantic models: MaintenanceSignal, SpecialistResult, etc.)
│   ├── limits.py                    (turn caps per agent)
│   ├── audit.py                      (append-only audit_log writer)
│   ├── retrieval.py                   (Chroma query_collection wrapper — the one place RAG happens)
│   ├── mcp_wiring.py                   (wires all MCP servers in-process for the app)
│   ├── intake_adapter.py                (bridges a confirmed voice/image signal into a real run)
│   └── workflows/
│       ├── incident.yaml                 (the reference chain)
│       ├── patch.yaml                     (same chain, runbook_class="patching")
│       └── performance.yaml                (same chain, runbook_class="tuning", advisory-only)
│
├── a2a/                        ← the one real Agent-to-Agent handoff (Supervisor → Diagnosis)
│   ├── agent_card.py              (signed Agent Card — HMAC-SHA256, /.well-known/agent-card.json)
│   ├── endpoint.py                  (the /invoke ASGI endpoint Diagnosis is served from)
│   └── client.py                     (Supervisor-side caller)
│
├── mcp_servers/                ← typed MCP tool servers, one per simulated system
│   ├── monitoring_mcp.py / itsm_mcp.py / tracker_mcp.py / cmdb_mcp.py / patch_mcp.py
│   └── simulators/               ← the actual fake systems these MCP servers wrap
│       ├── monitoring.py / itsm.py / tracker.py / cmdb.py / patch_source.py
│
├── guardrails/                  ← every deterministic (non-LLM) safety check
│   ├── policy_gate.py              (freeze windows, prod/non-prod, blast radius, max concurrent, roles)
│   ├── blast_radius.py               (BFS over CMDB adjacency graph)
│   ├── scheduling.py                  (maintenance-window rule engine, patch workflows)
│   └── scrubber.py                     (PII/secret redaction — regex + local Ollama SLM)
│
├── intake/                      ← the two non-alert entry points
│   ├── voice_path.py                (Whisper transcription → scrub → MaintenanceSignal)
│   ├── voice_intent.py                (closed-vocabulary intent parser, no LLM)
│   └── vision_path.py                  (gpt-4o extraction → scrub → MaintenanceSignal)
│
├── correlation/
│   └── cluster.py                 ← DBSCAN alert clustering (classical ML, no LLM)
│
├── data_gen/                     ← synthetic dataset generators (fixed seed, reproducible)
│   ├── alerts.py / cmdb.py / metrics.py / patch_inventory.py / pii_seed.py / runbooks.py / tickets.py
│
├── db/
│   ├── schema.sql                  ← full SQLite schema
│   ├── init_db.py                    ← builds + seeds app.db from data_gen output
│   └── load_chroma.py                  ← builds the 4 Chroma collections from chunked documents
│
└── tests/                          ← pytest suite, one file per module above (98+ tests)
```

## `frontend/` — the OpsFlow cockpit (Next.js)

```
frontend/src/
├── app/
│   ├── layout.js / page.js        ← Next.js app router entry, login gate
│   └── globals.css                  ← theme tokens (light/dark), scrollbar styling
│
├── components/
│   ├── CockpitShell.jsx            ← the shell: sidebar + tab bar + shared incident state + chat
│   ├── Overview.jsx                  ← session-wide metrics dashboard (the landing tab)
│   ├── OpsBoard.jsx                    ← live alert feed (SSE) + Diagnose action
│   ├── Tickets.jsx                      ← ITSM-simulator ticket browser
│   ├── IncidentWorkspace.jsx             ← one incident's full record: evidence → diagnosis → plan
│   │                                        → approval → verification, plus Agent Trace modal
│   ├── AutonomyLadder.jsx                 ← per-runbook trust-tier view
│   ├── DriftQueue.jsx                      ← CMDB drift screen (currently hidden from nav, code intact)
│   ├── ChatWidget.jsx                       ← floating assistant: text + voice + image intake
│   ├── AgentTrace.jsx                        ← per-step latency/tokens/model/citations viewer
│   ├── ChunkInspector.jsx                     ← Knowledge Base tab: chunk boundaries + upload
│   ├── Sidebar.jsx                             ← nav + role-gated admin panels
│   ├── NotificationBell.jsx                     ← auto-triage notifications
│   ├── panels/                                   ← Admin/Approver sidebar panels
│   │   ├── UserManagementPanel.jsx, ModelThresholdConfigPanel.jsx,
│   │   └── ScenarioLauncherPanel.jsx, AuditLogPanel.jsx
│   └── ui/                                        ← shadcn/ui primitives (button, card, modal, badge, input)
│
├── hooks/
│   ├── useAlertStream.js           ← SSE connection to /alerts/stream
│   ├── useWorkflowRun.js             ← the shared incident-run state used across tabs
│   ├── useAutoTriage.js               ← auto-diagnoses newly arrived alerts in the background
│   ├── useTickets.js                   ← ticket list + refetch
│   └── useTheme.js                      ← light/dark toggle
│
└── lib/
    ├── roles.js                    ← TAB_PERMISSIONS / PANEL_PERMISSIONS (mirrors backend role gating)
    ├── tabInfo.js                    ← plain-language tagline/description per tab, jury-facing
    ├── agentSummary.js                ← human-readable summaries of agent trace steps
    └── theme.js / utils.js              ← theme tokens, misc helpers
```

## `data/` — every synthetic dataset

```
data/
├── PROVENANCE.md              ← which script generated which file, and when (no mystery data)
├── alerts.json / cmdb.json / cmdb_ground_truth.json
├── patch_inventory.json / change_calendar.json
├── tickets.csv / pii_ground_truth.json / failed_remediations.json
├── metrics/CI-NNNN.csv          ← per-CI metric time series (real degradation/recovery curves)
├── metrics_index.json
├── runbooks/RB-NNN.md             ← 22 runbooks, structurally chunkable, one deliberate "trap" case
├── postmortems/PM-NNN.md            ← narrative RCA docs, feed the ticket_history/postmortem RAG
├── knowledge_base/KB-*.md             ← SharePoint/Teams/Power Automate/Power Apps/Azure AD articles
├── scenarios/SCEN-0N.json               ← the 6 replayable demo scenarios (see DEMO_SCRIPT.md §5)
├── chroma_db/                             ← persisted Chroma vector store (binary, generated)
└── app.db                                   ← a copy of the SQLite database (generated)
```

---

## How to read this codebase in 15 minutes

1. Skim `ARCHITECTURE.md` §3 (the agent chain table) — that's the spine everything else hangs off.
2. Open `backend/orchestrator/supervisor.py` — see the actual dispatch loop.
3. Open `backend/agents/verification.py` — the shortest, highest-signal file: the Fake Fix
   Detector in ~40 lines, no LLM.
4. Open `backend/orchestrator/workflows/incident.yaml` vs `patch.yaml` — see how little changes
   between workflow families (proof the declarative-workflow design assumption held).
5. Open `frontend/src/components/CockpitShell.jsx` — see how the 5 tabs share one incident state.
6. Skim `data/scenarios/*.json` — the fastest way to understand what the system is *supposed* to
   do in each case, in plain JSON.
