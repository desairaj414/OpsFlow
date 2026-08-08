# Verascope — Jury Pitch & Demo Script

---

## 1. Elevator pitch (30 seconds)

> "IT maintenance teams patch, tune, and fix incidents by hand, across tools that don't talk to
> each other — the monitoring stack, the ticketing system, and the CMDB all disagree, and the same
> incident gets re-diagnosed from scratch every time. Verascope is a supervised team of AI agents
> that turns that manual relay race into one auditable pipeline: an alert — or a voice note, or a
> screenshot — comes in, gets correlated, enriched with real evidence, diagnosed with a citation
> for every claim, planned from an approved runbook only, gated by deterministic policy rules,
> approved by a human, executed, and then **actually verified** — not just assumed fixed. Six of
> the seven handbook models are in the primary path, doing the job each is actually suited for."

## 2. Full pitch (2 minutes) — structure to talk through

1. **The problem** (10s) — three repeated maintenance task types, fragmented tools, inconsistent
   manual diagnosis. (`ARCHITECTURE.md` §1)
2. **The shape of the fix** (20s) — not a chatbot, a *supervised agent chain*: Correlate → Enrich →
   Diagnose → Plan → Gate → Approve → Execute → Verify → Sync → Knowledge. Two levels only —
   Supervisor + specialists, typed handoffs, one real Agent-to-Agent (A2A) call.
3. **Why it's trustworthy, not just impressive** (40s) — this is the part that wins on the
   guardrails: every hypothesis must cite real evidence or it's dropped before you ever see it;
   plans can only use steps from an approved runbook; blast radius and policy checks are pure
   Python, not the model grading its own homework; and the **Fake Fix Detector** requires the
   alert *and* the underlying metric to recover and hold — not just look better for a second.
4. **Three workflow families, one engine** (15s) — incident resolution, patch management,
   performance tuning all run the identical chain over different runbook classes; performance
   tuning is *deliberately* advisory-only, it never auto-executes, because tuning changes are
   judgement calls with delayed effects.
5. **Privacy and audit** (15s) — every model boundary is scrubbed first (regex + local SLM,
   reversible tokenisation), and there's a real append-only audit trail — the DB itself rejects an
   UPDATE or DELETE on it, not just app-level discipline.
6. **The honest bit** (10s) — say the gateway-vs-external line, and name one or two things that
   are deliberately not built yet (autonomy-ladder auto-promotion, live CMDB write-back) rather
   than waiting to be caught. Jurors trust teams that self-report gaps.

## 3. The one line that pre-empts the biggest misunderstanding

> "Every model call goes to the TCS GenAI Lab gateway or a local Ollama model on this laptop —
> nothing calls out to a real third party. The 'ServiceNow' and 'Jira' panels you'll see are our
> own FastAPI simulators with realistic field shapes, clearly labelled. MCP and A2A are open
> protocols we implemented locally, not services we're subscribing to."

Say this **before** anyone asks — it's on a slide, in the README, and here.

---

## 4. Use-case story (the narrative to walk the jury through)

**Persona: Priya, an IT operations engineer**, is watching the Ops Board. It's not a demo dataset
to her — it's the live SharePoint/Power Platform/Teams estate.

1. **An alert fires.** A Power Automate flow tied to `CI-0059` starts throwing connection-refused
   errors. It lands on the Ops Board in real time (SSE feed) — no page refresh.
2. **Priya doesn't even have to triage it.** Auto-triage has already kicked off a diagnosis in the
   background; the notification bell lights up.
3. **She opens Incident Workspace.** She sees exactly what the system gathered as evidence (the
   CI record, its relationships, the live metric series, two similar past tickets it found by
   vector search) — every fact has an ID she can trace back to its source.
4. **Diagnosis.** DeepSeek R1 (handed the case over a real A2A call, not just an in-process
   function) proposes ranked root causes, each with a citation. No citation, no hypothesis — she
   never sees an unsupported guess.
5. **Plan.** The planner pulls the matching runbook steps from Chroma — nothing invented — and
   proposes a fix. Blast radius and policy checks run underneath, in plain Python: this CI isn't
   in a freeze window, isn't above the blast-radius threshold, so it's routed to her for approval
   rather than auto-run.
6. **She approves it.** One click — or she could have said "approve CI-0059" to the chat
   assistant and gotten the same audited action.
7. **Execute → Verify.** The system doesn't just trust the alert clearing. It checks the real
   underlying metric held recovered through a stabilisation window. This is the moment that sells
   the room: **run SCEN-02 instead of SCEN-01 here and watch it correctly refuse to call a
   symptom-suppressed fix "resolved."**
8. **Sync + Knowledge.** The ticket gets a work note and closes in the ITSM simulator; if it *had*
   been a fake fix, a Negative-KB entry gets seeded so the same bad remediation isn't tried blind
   next time.
9. **Priya checks Overview.** Every number just moved — completed runs, manual steps avoided,
   resolution time — computed live from what actually just happened, not a canned dashboard.

That's the whole pitch in one incident: evidence-grounded, policy-gated, human-approved,
independently verified, and it learns from its own failures.

---

## 5. Live demo flow — click path

### Setup (before the jury sits down)
```bash
# Backend
cd backend
venv\Scripts\activate
uvicorn main:app --reload --host 0.0.0.0 --port 8765

# Frontend
cd frontend
npm.cmd run dev   # http://localhost:3000
```
Log in, confirm the alert stream is live (green connection indicator), have `data/scenarios/`
open in a second window as your scenario menu.

### Recommended run order (~6-8 minutes)

| Step | Where | What to show |
|---|---|---|
| 1 | **Overview** | Land here first — it's the "session so far" headline. Point out it's all live-computed, not mocked. |
| 2 | **Ops Board** | Show the live alert feed (SSE). Click into a fresh alert, hit **Diagnose**. |
| 3 | **Incident Workspace** | Walk the evidence → diagnosis → plan panels. Open **Agent Trace** — show per-step latency/tokens and the A2A badge on the Diagnose step. |
| 4 | **Approve** | Approve the plan. Narrate: same path whether you click it or say it to the chat assistant. |
| 5 | **Verification result** | This is scenario-dependent — see the two contrast scenarios below. |
| 6 | **Overview again** | Numbers visibly moved. This closes the loop. |
| 7 | **Chat widget** | One quick voice or image intake, to show the multimodal path and the confirm-before-action gate. |
| 8 | **Autonomy Ladder** | Briefly — shows the trust-tier concept even though promotion isn't live yet; be upfront about that if asked. |

### The two scenarios that do the most work in a live demo

Use `POST /workflows/run` with these `ci_id`/`workflow_type` pairs (or the Scenario Launcher panel,
Admin/Approver sidebar) — both are fixture-backed and reproducible:

- **SCEN-01** (`CI-0059`, incident) — clean resolution. Runs the full chain to
  `verified_resolved`. This is your "happy path, everything works" beat.
- **SCEN-02** (`CI-0121`, incident) — **the Fake Fix Detector catching a fake fix.** Same chain,
  but verification correctly refuses to call it fixed (`symptom_suppressed`) because the alert
  cleared but the metric didn't actually recover. **This is the single best "we built real
  guardrails, not theater" moment in the whole demo — always show it.**
- **SCEN-03** (`CI-0009`, incident) — blast radius blocks the plan before it ever reaches a human
  for approval. Good for the "policy gate is deterministic code, not a prompt" beat.
- **SCEN-05 / SCEN-06** (`CI-0138` / `CI-0181`, performance) — tuning workflow, always lands at
  `pending_approval` and never auto-executes, on purpose. Good for the "we thought about where
  automation shouldn't go" beat.
- **SCEN-04** (`CI-0059`, patch) — grouped maintenance window, approval required. Good for showing
  workflow-family parity without a full second live run.

### If a juror asks "what's not real here?"
Answer directly from `ARCHITECTURE.md` §10 — don't improvise. The honest list: ITSM/Tracker/
Monitoring/CMDB/Patch Source are our own simulators (labelled); the autonomy ladder is seeded, not
runtime-promoted; CMDB updates are proposed, not auto-applied; no live script execution against
real infra (by design — verification runs against real generated metric data instead).

---

## 6. Anticipated questions (from the PRD's own self-flagged weak points)

- **"What agent framework do you use — LangGraph, CrewAI, AutoGen?"** — None of them. Verified in
  `requirements.txt`: only `langchain`/`langchain-openai`, used purely as an LLM client wrapper
  (`ChatOpenAI` + `.with_fallbacks()` for the offline Ollama fallback) — not for orchestration. The
  Supervisor-and-specialists dispatch loop, the typed `SpecialistResult` validation between steps,
  and the turn caps are all plain Python (`backend/orchestrator/supervisor.py`). Deliberate: the
  guardrail logic (citation enforcement, the policy gate running between two LLM steps, turn caps)
  needed to be plain, walkable code a juror can be shown line by line — not buried inside a
  framework's internal graph/state-machine runtime. The one place a real open protocol is used is
  the single Supervisor→Diagnosis handoff, which goes over an actual signed A2A call.
- **"How do you measure user satisfaction?"** — We don't claim to; we report approval rate and edit
  rate on human decisions as a stated *proxy*, and that same feedback loop feeds the Negative KB,
  so it's load-bearing, not decorative.
- **"Isn't performance tuning just missing?"** — No — full parity, same chain, deliberately
  advisory-only because tuning changes have delayed, ambiguous effects. State the design choice,
  don't apologise for it.
- **"Did you fine-tune anything?"** — No, and we won't claim to. CPU-only lab machines. The ML
  we do run is real but lightweight (scikit-learn DBSCAN for correlation) — everything else is
  prompting, RAG, deterministic rule engines, and protocol implementation.
- **"Why SQLite and not Postgres/Neo4j?"** — Data volume is deliberately moderate (hundreds of
  records) and CI relationships are covered by a simple adjacency table — the right tool for this
  scale, not a shortcut.
