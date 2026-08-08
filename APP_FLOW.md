# OpsFlow — App & Data Flow

How data actually moves through the system, end to end, for each entry point. Pairs with
`ARCHITECTURE.md` (the "what") — this is the "where does the data go" doc.

---

## 1. The three intake paths → one canonical shape

Every incident, regardless of how it was reported, becomes the same `MaintenanceSignal` object
before anything else touches it:

```json
{
  "signal_id": "SIG-0001",
  "modality": "alert | voice | image",
  "extracted_text": "post-transcription/extraction, PRE-scrub",
  "candidate_ci_refs": ["CI-0087"],
  "candidate_alert_refs": ["ALERT-1043"],
  "confidence": 0.0,
  "requires_human_confirmation": true
}
```

```mermaid
flowchart LR
    A["Alert HTTP\n(Monitoring simulator)"] --> N["Normalise into\nMaintenanceSignal"]
    V["Voice\n(mic button, chat widget)"] --> W["Whisper\ntranscription"] --> S1["Scrubber\n(Ollama SLM + regex)"] --> N
    I["Image / screenshot\n(chat widget upload)"] --> X["gpt-4o\nextraction"] --> S2["Scrubber\n(Ollama SLM + regex)"] --> N
    N --> C{"requires_human\n_confirmation?"}
    C -- "yes (voice/image)" --> H["Human confirms\nin chat widget"]
    H --> R["intake_adapter.py\nstart_workflow_from_confirmed_signal"]
    C -- "no (alert, pre-trusted)" --> R
    R --> WF["Supervisor.run_workflow()"]
```

**Rule that never bends:** the scrubber runs *after* modality conversion (transcription/extraction)
and *before* the signal enters any workflow or model call. Raw audio/images are held in memory for
the run only — never persisted to disk.

---

## 2. Inside one workflow run — the golden path (Incident Resolution)

```mermaid
sequenceDiagram
    participant UI as Cockpit (Ops Board / Chat)
    participant Sup as Supervisor
    participant Enr as Enrichment
    participant Dia as Diagnosis (A2A)
    participant Pln as Planner
    participant Gate as Policy Gate
    participant Hum as Human (Approver)
    participant Ver as Verification
    participant Syn as Sync
    participant Know as Knowledge
    participant DB as SQLite / Chroma
    participant MCP as MCP servers (Monitoring/ITSM/CMDB)

    UI->>Sup: POST /workflows/run {ci_id, workflow_type}
    Sup->>DB: audit_log: correlate
    Sup->>Enr: dispatch
    Enr->>MCP: get_ci, get_relationships, get_metric_series
    Enr->>DB: Chroma query_collection(ticket_history)
    Enr-->>Sup: SpecialistResult (evidence + artifact_ids)
    Sup->>Dia: A2A POST /invoke {incident_id, evidence}
    Dia->>Dia: DeepSeek R1 → ranked hypotheses (citation-enforced)
    Dia-->>Sup: SpecialistResult (hypotheses)
    Sup->>Pln: dispatch
    Pln->>DB: Chroma query_collection(runbooks, class=remediation)
    Pln->>Pln: gpt-4.1-nano drafts plan from retrieved chunks only
    Pln->>Gate: blast_radius() + policy_gate_result() [deterministic]
    Pln-->>Sup: SpecialistResult (plan, blast_radius, gate result)
    Sup-->>UI: status = pending_approval
    Hum->>UI: Approve (Incident Workspace or chat "approve_incident")
    UI->>Sup: POST /workflows/decision {approve} → re-run auto_approve=true
    Sup->>DB: audit_log: execute_plan
    Sup->>Ver: dispatch
    Ver->>DB: read metric series (real CSV, stabilisation window)
    Ver-->>Sup: verified_resolved | symptom_suppressed
    Sup->>Syn: dispatch
    Syn->>MCP: add_work_note, update_ticket, propose_ci_update
    Sup->>Know: dispatch (only if symptom_suppressed)
    Know->>DB: seed negative_kb_entries
    Sup-->>UI: final trace (status, verification_status, per-step latency/tokens)
```

Every arrow into `DB` from `Sup`/an agent is also an `audit_log` row: actor, action, target
artifact, evidence IDs, model used, timestamp — append-only, queried live by the Overview tab and
the Audit Log panel.

---

## 3. Where each number on the Overview tab comes from

Four endpoints fetched on load, every number computed **live** from real SQLite/dataset state —
nothing on this tab is canned:

| Endpoint | Feeds |
|---|---|
| `GET /metrics/summary` | Workflow runs, completed, human approvals/rejections, stopped-before-completion, negative-KB entries seeded, manual steps avoided, resolution-time averages |
| `GET /cmdb/drift` | Drift rate, CMDB accuracy donut — diffs `cmdb_ci` (recorded) vs `cmdb_ci_ground_truth` (actual) field by field |
| `GET /autonomy-ladder` | "Most-trusted runbooks" card |
| `GET /audit-log?limit=6` | Recent activity feed (role-gated to Approver/Admin) |

`metrics.total_workflow_runs_this_session` = `COUNT(audit_log WHERE action='correlate')` — one row
per real run, not a simulated counter. `manual_steps_avoided` sums the real `evidence_ids` list
length from every `execute_plan` row — a real count of runbook steps actually executed, not an
estimate.

---

## 4. Frontend data flow (who calls what)

```mermaid
flowchart TD
    subgraph Cockpit["CockpitShell.jsx"]
        Overview
        OpsBoard["Ops Board"]
        Tickets
        IncidentWorkspace["Incident Workspace"]
        AutonomyLadder["Autonomy Ladder"]
        ChatWidget
        Sidebar
    end

    OpsBoard -- "useAlertStream (SSE)" --> AlertsAPI["GET /alerts/stream"]
    OpsBoard -- "Diagnose click" --> RunAPI["POST /workflows/run"]
    useAutoTriage["useAutoTriage hook"] -- "auto-diagnoses new alerts" --> RunAPI
    IncidentWorkspace -- "Approve/Reject" --> DecisionAPI["POST /workflows/decision"]
    ChatWidget -- "text/voice/image" --> ChatAPI["POST /chat, /intake/voice, /intake/image, /intake/confirm"]
    Tickets -- "useTickets" --> TicketsAPI["GET /tickets"]
    AutonomyLadder --> LadderAPI["GET /autonomy-ladder"]
    Overview --> MetricsAPI["GET /metrics/summary, /cmdb/drift, /audit-log"]
    Sidebar -- "Admin panels" --> ConfigAPI["GET/POST /config/*, /runbooks/upload, /knowledge-base/upload"]

    RunAPI --> Backend[(FastAPI backend)]
    DecisionAPI --> Backend
    ChatAPI --> Backend
    TicketsAPI --> Backend
    LadderAPI --> Backend
    MetricsAPI --> Backend
    ConfigAPI --> Backend
    AlertsAPI --> Backend
```

One shared `useWorkflowRun` hook lives in `CockpitShell` and is passed to every tab that shows a
run — starting an incident from the Ops Board, the notification bell, or the chat widget all
converge on the same Incident Workspace state.

---

## 5. Auth flow

`POST /auth/login` → mock JWT carrying a `role` claim (`ops_engineer` / `approver` / `admin`) →
sent as `Authorization: Bearer <token>` on every call except `GET /alerts/stream` (SSE, token as a
query param since `EventSource` can't set headers). Role is enforced server-side (`require_role()`
in `main.py`) — the frontend role switcher is a display convenience, not the actual gate. Admin can
`POST /auth/view-as` to temporarily preview another role without losing their own identity (shown
honestly as "X viewing as Y", not silently swapped).

---

## 6. Failure / offline path

If `genailab.tcs.in` is unreachable mid-run, `get_llm()`/`get_embeddings()` transparently retry
against local Ollama (`llama-3.2-3b-it`) via LangChain `.with_fallbacks()` — the workflow keeps
running instead of hard-failing. This is invisible under normal conditions; it only shows up as
slightly higher latency on the step that triggered it.
