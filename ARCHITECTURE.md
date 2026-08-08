# OpsFlow — Architecture (Final, as-built)

> **AI-verified operations console** for IT application maintenance.
> Built for TCS AI Fridays Season 2 — Regional Round.
> Problem statement: *AI-Powered Multi-Agent Workflow Automation for IT Application Maintenance.*

This is the consolidated, demo-facing architecture doc. It reflects what the code actually does
today, not the original design intent (that lives in `PRD_FINAL.md` and `.knowledge/arch-overview.md`,
both frozen). Deep implementation detail (file-by-file, metric-by-metric) lives in
`.knowledge/architecture-as-built.md` — this file is the readable summary of that.

---

## 1. The problem, in one paragraph

IT maintenance teams repeat three classes of work forever — **patching**, **performance tuning**,
**incident resolution** — by hand, across tools that don't talk to each other: the monitoring stack
knows something's wrong, the ticketing system holds the human conversation, the CMDB is supposed to
know what's deployed and what depends on what, and the three don't agree. The same incident gets
diagnosed from scratch by a different engineer every time. OpsFlow is a coordinated team of AI
agents — each owning one narrow step, handing off under supervision — that turns that manual relay
race into a repeatable, auditable workflow: **signal received → ticket closed, CMDB updated,
knowledge captured.**

---

## 2. System tiers

```
┌──────────────────────────────────────────────────────────────────────┐
│ PRESENTATION        Next.js + shadcn/ui cockpit ("OpsFlow")        │
│                      Overview · Ops Board · Tickets · Incident       │
│                      Workspace · Autonomy Ladder + floating chat     │
├──────────────────────────────────────────────────────────────────────┤
│ INTAKE LAYER        Alert (HTTP/SSE) │ Voice (Whisper) │ Image (VLM) │
│                      → one canonical MaintenanceSignal               │
│                      → SCRUBBER (always runs after modality convert) │
├──────────────────────────────────────────────────────────────────────┤
│ AI SOLUTION LAYER   Supervisor ── A2A ──▶ Diagnosis specialist       │
│                      (Enrich/Plan/Verify/Sync/Knowledge in-process)  │
│                      Guardrails · Policy gate · Model router         │
├──────────────────────────────────────────────────────────────────────┤
│ ENTERPRISE KNOWLEDGE          │  TRANSACTIONAL SYSTEMS               │
│ Chroma: runbooks,             │  SQLite: incidents, audit log,       │
│ postmortems, ticket history,  │  workflow state, autonomy ladder,    │
│ NEGATIVE knowledge base       │  CMDB (recorded + ground-truth)      │
├──────────────────────────────────────────────────────────────────────┤
│ TOOL / INTEGRATION LAYER — MCP servers (local, one per system)       │
│ Monitoring │ ITSM │ Tracker │ CMDB │ Patch Source                    │
├──────────────────────────────────────────────────────────────────────┤
│ SIMULATED EXTERNAL SYSTEMS — our own FastAPI mocks                   │
│ ⚠ NOT third-party SaaS. "ServiceNow"/"Jira" panels are our own       │
│   API-shaped simulators, labelled as such in the UI.                 │
└──────────────────────────────────────────────────────────────────────┘
   Models: TCS GenAI Lab gateway ▸ + local Ollama ▸ — no external MaaS
   Protocols: MCP (agent→tools) · A2A (agent→agent) — open specs, local only
```

**Say this out loud to a juror** (pre-empts the #1 misreading of this system):
> "Every model call goes to the TCS-provided GenAI Lab gateway, or to a model running locally on
> this laptop via Ollama. There is no external Model-as-a-Service dependency. 'ServiceNow' and
> 'Jira' are API-compatible simulators we wrote in FastAPI. MCP and A2A are open protocols, not
> services — our MCP servers and A2A endpoint run on this laptop and call nothing outbound."

---

## 3. The agent chain (the core of the pitch)

**Reference chain (Incident Resolution — the golden path):**

```
Correlate → Enrich → Diagnose → Plan (+ Policy Gate) → Approve (human) → Execute → Verify → Sync → Knowledge
```

Two levels only: **one Supervisor + specialist agents.** Specialists never call each other directly
— each returns a typed, schema-validated result to the Supervisor, which re-validates before
dispatching the next step. Every agent has an explicit termination condition and a turn cap.

| # | Step | File | Technique | What it does |
|---|---|---|---|---|
| 1 | **Correlate** | `backend/correlation/cluster.py` | Classical ML — scikit-learn `DBSCAN` over alert timestamps within CMDB-topology + category buckets | Groups raw alert noise into incidents (feeds the "manual triage avoided" metric) |
| 2 | **Enrich** | `backend/agents/enrichment.py` | Deterministic + RAG | Pulls CI data, relationships, and metric series via MCP; retrieves top-2 precedent tickets from Chroma; tags every fact with a stable `artifact_id` |
| 3 | **Diagnose** | `backend/agents/diagnosis.py` | **LLM — DeepSeek R1**, over **A2A** (the one real agent-to-agent handoff) | Generates 2-4 ranked root-cause hypotheses; any hypothesis without a cited evidence ID is dropped before it's ever returned |
| 4 | **Plan** | `backend/agents/planner.py` | RAG (Chroma) + **LLM — gpt-4.1-nano** + deterministic guardrails | Drafts a plan using *only* retrieved runbook chunks (runbook-bounded action space); blast radius, policy gate, and (for patches) maintenance window are computed **deterministically after** the LLM drafts — never delegated to the model |
| — | **Policy Gate** | `backend/guardrails/policy_gate.py` | Pure Python rule engine | Change-freeze windows, prod/non-prod, blast-radius threshold, max concurrent changes, required approver role — computed inside Plan's step |
| 5 | **Approve** | Human decision point | — | `run_workflow` pauses at `pending_approval` unless demo auto-approve is set; identical audited path whether approved from the Incident Workspace UI or via the chat assistant |
| 6 | **Execute** | Supervisor-internal | Deterministic, audit-only | Writes an `execute_plan` audit entry against the seeded metric data (a genuine degradation curve, not a scripted outcome) |
| 7 | **Verify** | `backend/agents/verification.py` | Deterministic — **the Fake Fix Detector** | Requires **two independent signals**: alert cleared AND the metric series recovered and *held* through a stabilisation window. Alert-only clearance = `symptom_suppressed`, incident stays open |
| 8 | **Sync** | `backend/agents/sync.py` | Deterministic | Writes the outcome back to the ITSM simulator (work note + ticket update); proposes a CMDB field update on verified fixes |
| 9 | **Knowledge** | `backend/agents/knowledge.py` | Deterministic | On `symptom_suppressed` only: seeds a Negative-KB entry scoped to `(ci_class, failure_signature)` so a remediation that failed once isn't blindly repeated |

**Cross-cutting, not pipeline steps:**
- **Scrubber** (local Ollama SLM `llama-3.2-3b-it` + regex) — runs on the two free-text intake
  paths (voice, image) before any signal enters a workflow.
- **Offline fallback** — every gateway call (`get_llm`/`get_embeddings`) transparently falls back
  to local Ollama if `genailab.tcs.in` is unreachable.
- **Chat assistant** — one LLM call (`gpt-4.1-nano`) classifies intent; everything after is
  deterministic (real parameterized SQL for ticket queries, the same audited approve/reject path).

### Why this shape (design rationale, cite if asked)
MAST analysis attributes 44.2% of multi-agent failures to system design, 32.3% to inter-agent
misalignment — a centralised validation bottleneck (Supervisor) contains error amplification to
~4.4x vs ~17x for an uncoordinated mesh. ITBench found higher agent turn counts are *not* reliably
better, hence hard turn caps per agent rather than open ReAct-style loops.

---

## 4. Three workflow families, one chain

The agent chain and every guardrail are identical across all three — only the runbook class,
verification criterion, and autonomy tier change. This is *declarative data* (`orchestrator/workflows/*.yaml`), not three separate code paths.

| | Incident Resolution | Patch Management | Performance Tuning |
|---|---|---|---|
| Trigger | Fault alert / voice / image | Patch inventory + change calendar | Degradation alert (latency, memory creep, slow query) |
| Runbook class | `remediation` | `patching` | `tuning` |
| Plan output | Remediation steps | Grouped maintenance window | Ranked tuning recommendations |
| Verification | Alert cleared **and** health probe recovered | Patch applied **and** no new alerts in window | **Sustained metric improvement across a window** — not a binary clear |
| Autonomy | Up to auto-execute (ladder) | Approval required | **Advisory only — never auto-executes**, by deliberate design |

---

## 5. Models actually in use (six of the seven handbook models)

| Task | Model | Why |
|---|---|---|
| Correlation, policy gate, blast radius, scheduling | **No LLM** — Python/scikit-learn | Deterministic, auditable, must be provably consistent |
| Root-cause hypothesis generation | **DeepSeek R1** (via A2A) | Only step genuinely needing multi-step reasoning over conflicting evidence |
| Plan drafting from runbooks | **gpt-4.1-nano** | Cheap, fast, reliable structured JSON (substitute for a deprecated DeepSeek V3 deployment) |
| Voice transcription | **Whisper** | Purpose-built speech model |
| Screenshot/error-image extraction | **gpt-4o** | Substitute for a deprecated Llama Vision deployment |
| Embeddings (RAG) | **text-embedding-3-large** | Only embedding model listed; backs all Chroma retrieval |
| Chat intent classification | **gpt-4.1-nano** | Small classification task |
| PII/secret scrubbing (voice + image intake) | **Local Ollama SLM** (`llama-3.2-3b-it`) | Highest-sensitivity content never leaves the machine |
| Offline fallback (any gateway call) | **Local Ollama SLM** | Demo resilience if the gateway goes down mid-session |

Routing principle: route by task shape, not model prestige. Deterministic tasks get no LLM at all;
sensitive content gets a local SLM; only genuine multi-step reasoning gets the reasoning model.
Full table with `.env` model IDs and rejected candidates: `.knowledge/models-routing.md`.

---

## 6. Guardrails — the four pillars

1. **Domain-specific guardrails** — runbook-bounded action space (agents can't invent remediation
   steps outside the approved catalog), the deterministic policy gate, a confidence floor with an
   explicit "abstain and name what's missing" path, and the Fake Fix Detector.
2. **Automated multi-step workflows** — the 9-step chain above, fully observable, attributable, and
   replayable via the audit log.
3. **Zero data leakage** — scrub-before-send at every model boundary (reversible tokenisation,
   e.g. `svc-payments-prd` → `[HOST_7]`), local-model routing for the most sensitive content, no
   raw audio/image persistence beyond the run. Basis: India's DPDP Act 2023 (personal data in
   tickets) + secrets-leakage risk (hostnames, connection strings, tokens) — this is an IT-Ops
   privacy story, not a healthcare one.
4. **Trust and transparency** — citations are mandatory (an uncited hypothesis is suppressed at
   generation, not filtered after), an explicit "what I could not verify" block, and a real
   append-only audit trail (SQLite trigger rejects raw UPDATE/DELETE, not just app-level discipline).

---

## 7. Protocols

| Layer | Protocol | What's built |
|---|---|---|
| Agent → systems | **MCP** | 5 local MCP servers (Monitoring, ITSM, Tracker, CMDB, Patch Source), typed tools, no bespoke HTTP glue |
| Agent → agent | **A2A** | One real handoff: Supervisor → Diagnosis. HMAC-SHA256-signed Agent Card, served at `/.well-known/agent-card.json`, invoked at `/invoke`. Deliberately scoped to one handoff to prove the pattern, not implied everywhere |

Both run **locally and call nothing outbound** — same pre-empt line as the gateway distinction above.

---

## 8. Storage

- **SQLite** — transactional/session state: `cmdb_ci` (recorded) + `cmdb_ci_ground_truth` (actual,
  ~35% deliberately diverged) for the Drift screen, `alerts`, `incidents`, `audit_log`
  (append-only, trigger-enforced), `autonomy_ladder`, `negative_kb_entries`, `runbooks`,
  `scenarios`, `patch_inventory`, `change_calendar`, `pii_ground_truth`.
- **Chroma** — vector/RAG: `runbooks` (chunked on structural boundaries only — a numbered step is
  never split mid-instruction), `postmortems`, `ticket_history`, `negative_kb`.

Full schema: `.knowledge/schema-db.md`.

---

## 9. Frontend — OpsFlow cockpit

Next.js + shadcn/ui. Role-gated (server-enforced, not cosmetic): **Ops Engineer**, **Approver**,
**Admin** — all three share the same 5 main tabs (Overview, Ops Board, Tickets, Incident Workspace,
Autonomy Ladder); Admin's extra surface is Sidebar panels (Users, Config, Scenarios, Audit Log,
Knowledge Base), not extra tabs. A floating chat assistant (voice + image + text) sits on every
screen. Full tab-by-tab breakdown and every Overview metric's exact source query:
`.knowledge/architecture-as-built.md` Part 2.

---

## 10. What's real vs. simulated — stated honestly

- **Real:** every LLM/SLM call, RAG retrieval, DBSCAN clustering, policy-gate/blast-radius logic,
  the Fake Fix Detector's two-signal check (against real generated metric CSVs with genuine
  degradation curves), the audit trail, MCP tool calls, the one A2A handoff, the scrubber
  (measured precision/recall against a planted ground-truth set).
- **Simulated, labelled as such:** ITSM ("ServiceNow-shaped"), Tracker ("Jira-shaped"), Monitoring,
  CMDB, Patch Source — our own FastAPI mocks with realistic field shapes, not real vendor SaaS.
- **Deliberately not built (say so if asked, don't dodge):** live auto-promotion of the autonomy
  ladder (state is seeded, not runtime-promoted), CMDB `propose_ci_update` applying automatically
  (logs a pending proposal only — human-approval-to-apply step is a known gap, not hidden), a real
  DPDP consent-manager flow, multilingual voice intake, real script execution against live infra.

This section is the honest-answer script for "what's fake here?" — better to say it first than
have it discovered.
