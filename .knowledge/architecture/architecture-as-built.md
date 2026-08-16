---
type: reference
title: Architecture As-Built — Agent Chain
status: active
updated: 2026-08-16
related: [arch-overview.md, ../domain/../domain/domain-agents.md, models-routing.md, api-contract.md, architecture-as-built-metrics.md]
---

Companion to [arch-overview.md](arch-overview.md) (which mirrors the frozen PRD design intent —
do not edit it). This node instead documents **what the code actually does today**, file-by-file,
for the multi-agent flow. Every Overview-tab metric's exact computation moved to
[architecture-as-built-metrics.md](architecture-as-built-metrics.md) (split out 2026-08-16 when
this file exceeded ~200 lines). Update this node (not arch-overview.md) if the implementation
changes.

## Multi-agent flow, one agent at a time

Chain order (`orchestrator/supervisor.py::run_workflow`): **Correlate → Enrich → Diagnose → Plan
(+ Policy Gate, computed inside Plan) → Approve (human) → Execute → Verify → Sync → Knowledge**.
Two levels only — Supervisor + specialists, agents never call each other directly. Each specialist
returns a typed `SpecialistResult`, re-validated by the Supervisor before the next dispatch.

### Correlate
**File**: `backend/correlation/cluster.py`, invoked from `backend/main.py`.
**Technique**: classical ML — **scikit-learn `DBSCAN`** clustering over alert timestamps, inside
buckets formed by a deterministic union-find over the CMDB relationship graph (topology group) +
alert category. No LLM.
**Important nuance**: inside a single incident's `run_workflow`, "Correlate" is just an **audit-log
marker** — the Supervisor receives one already-identified alert/CI as input and logs a `correlate`
action; it does not re-run DBSCAN at that moment. The actual DBSCAN computation only runs when
`GET /alerts/correlated` or `GET /metrics/summary` is called — today that means it only really
executes to feed one Overview metric (see architecture-as-built-metrics.md, "Manual triage
avoided"). The dedicated
correlated-candidates UI panel that used to also trigger it was removed in this session's Ops
Board redesign.

### Enrich
**File**: `backend/agents/enrichment.py`.
**Technique**: fully deterministic — **no LLM call at all**. Gathers evidence by calling three MCP
tool servers (`cmdb_mcp.get_ci`, `cmdb_mcp.get_relationships`, `monitoring_mcp.get_metric_series`,
and `patch_mcp.*` for patch workflows only), plus **one real RAG/vector-DB lookup**:
`orchestrator/retrieval.py::query_collection("ticket_history", ...)` — embeds the query via the
gateway's `text-embedding-3-large`, does a Chroma similarity search, returns the top-2 nearest past
tickets as "precedent" evidence (each tagged with a confidence derived from vector distance).
Every fact gathered gets a stable `artifact_id` so later agents can cite it by ID rather than
re-stating it.

### Diagnose
**File**: `backend/agents/diagnosis.py`, invoked via `backend/a2a/client.py` → `backend/a2a/endpoint.py`.
**Technique**: **LLM**, resolved via `api_client.get_llm(role="reasoning", ...)` — the actual model
depends on the active provider (`backend/providers.py`'s `PROVIDERS[provider]["roles"]["reasoning"]`);
only the legacy `tcs` provider maps this to DeepSeek R1 (`azure_ai/genailab-maas-DeepSeek-R1`), e.g.
Gemini (the public-deploy default) maps it to `gemini-flash-lite-latest`. This is the one step in the
whole chain that goes over the **A2A protocol** (in-process ASGI transport in this build) instead
of a plain in-process function call — the deliberate "one real agent-to-agent handoff" the PRD
scoped. Prompted with the evidence bundle (IDs + short extracts only, never full documents) to
generate 2-4 ranked root-cause hypotheses as JSON. **Citation enforcement**: any hypothesis with an
empty `cited_artifact_ids` or one citing an ID outside the actual evidence bundle is dropped before
it's ever returned — a model can't silently "invent" a fact.

### Plan
**File**: `backend/agents/planner.py`.
**Technique**: **RAG + LLM**, then deterministic guardrails. First does a real Chroma vector search
— `query_collection("runbooks", query_text, where={"class": runbook_class})` — restricted to the
runbook class this workflow type needs, retrieving up to 4 chunks (each chunk = one atomic
numbered runbook step, see Chunking below). Then calls `api_client.get_llm(role="structured", ...)`
— provider-dependent (only the legacy `tcs` provider resolves this to `gpt-4.1-nano`
`azure/genailab-maas-gpt-4.1-nano`, the human-approved substitute after DeepSeek V3 was confirmed
unreachable; see [models-routing.md](models-routing.md) for the historical detail and
`backend/providers.py` for current per-provider mappings) to draft a plan **using only those
retrieved chunks**; any step citing a chunk ID that
wasn't actually retrieved is dropped (same runbook-bounded-action-space rule as Diagnose's citation
enforcement). After the LLM returns, three things are computed **purely deterministically, never by
the model**: `blast_radius` (`guardrails/blast_radius.py`), `policy_gate_result`
(`guardrails/policy_gate.py` — the thresholds you asked about earlier), and, for patch workflows
only, `maintenance_window` (`guardrails/scheduling.py`).

### Policy Gate
Not a separate agent — computed *inside* Plan's step, described above. Purely rule-based
(threshold comparisons), no LLM, no ML.

### Approve
A human decision point, not code. `run_workflow` returns `status: "pending_approval"` and pauses
unless `auto_approve=True` was explicitly passed (demo/scenario convenience). The decision is made
either in Incident Workspace's `ApprovalSection` or via the chat assistant's `approve_incident`/
`reject_incident` intent (see Chat Assistant below) — both paths write the identical audit entry
and reuse the identical re-run mechanism.

### Execute
Supervisor-internal (`run_workflow`) — just writes an `execute_plan` audit entry (with the executed
step IDs as `evidence_ids`). No LLM, no real script execution against live infrastructure by
design: the "world" being acted on is the seeded metric CSVs from Phase 1, which already contain a
genuine degradation curve for CIs meant to still be broken — that's what lets Verify tell a real
fix from a fake one on real numbers, not a scripted outcome.

### Verify
**File**: `backend/agents/verification.py` — the **Fake Fix Detector**. Fully deterministic, no
LLM. Requires **two independent signals**: the alert cleared, AND the metric series (real CSV data
per CI) recovered and **held** through a stabilisation window (checks the tail 30% of the series
stays under threshold, not just one data point). If only the alert cleared, the outcome is
`symptom_suppressed` (incident stays open) rather than trusted as a real fix.

### Sync
**File**: `backend/agents/sync.py`. Fully deterministic, no LLM. Writes the outcome back to the
simulated ITSM system (`itsm_mcp.add_work_note` + `update_ticket`), and if verified-resolved,
proposes a CMDB field update (`cmdb_mcp.propose_ci_update`) — one consistent record across systems.

### Knowledge
**File**: `backend/agents/knowledge.py`. Fully deterministic, no LLM. Only acts on
`symptom_suppressed` outcomes: seeds a **Negative KB** entry scoped to `(ci_class,
failure_signature)` so a remediation that failed once is remembered and can be checked against
next time — deliberately scoped narrow, never a blanket filter (bias-mitigation table,
domain-guardrails.md).

### Supporting technique — Chunking (not an agent, feeds Enrich/Plan's RAG)
**File**: `backend/chunking.py`. Splits runbooks **only on structural boundaries**
(`### Step N` headings) and postmortems/KB articles on `## Heading` boundaries — never on a
character/token count, so a numbered step is never split mid-instruction. Runbook steps inherit
the document's Prerequisites block ("preamble inheritance") so a retrieved step never loses an
"only if X" condition. This is what populates the Chroma `runbooks` collection Plan queries and the
`ticket_history`/postmortem collections Enrich queries.

### Cross-cutting techniques — not pipeline steps, wrap around the chain
- **Local SLM (Ollama, `llama-3.2-3b-it`) — PII/secret name scrubbing.** `backend/guardrails/scrubber.py`.
  Only fires on the two real free-text intake paths: voice transcription (`intake/voice_path.py`)
  and image extraction (`intake/vision_path.py`) — both reachable today only via the floating chat
  assistant's mic/image buttons. The agent chain itself never scrubs (its inputs are synthetic,
  already-clean data).
- **Local SLM offline fallback (Ollama).** `backend/api_client.py`'s `get_llm()`/`get_embeddings()`
  wrap every gateway call used above (Diagnose, Plan, Chat classifier, embeddings for RAG) with
  `.with_fallbacks()` to a local Ollama model if the active provider's endpoint is unreachable
  (originally framed around `genailab.tcs.in`; now applies to whichever provider is active per
  request — see `backend/provider_context.py`). Invisible under normal conditions — no dedicated
  UI, it's a resilience net.
- **Chat Assistant** (outside the core 8-step chain). `backend/main.py`'s `POST /chat`. One LLM call
  via `api_client.get_llm(role="default"/"structured", ...)` (only the legacy `tcs` provider
  resolves this to `gpt-4.1-nano`) classifies the user's message into an intent + structured
  filters; everything
  after that is deterministic — `query_tickets` runs a real parameterized SQL query (the model
  never invents a number), `approve_incident`/`reject_incident` reuses the exact same audited path
  Incident Workspace's own approval section uses.

Overview-tab metrics moved to [architecture-as-built-metrics.md](architecture-as-built-metrics.md).

## Quick reference — LLM vs SLM vs classical ML vs deterministic, by step
Model ids are no longer fixed — every LLM step below resolves its model via
`api_client.get_llm(role=..., ...)` against whichever provider is active for that request
(`backend/providers.py`'s `PROVIDERS[provider]["roles"]`). The "Historical/tcs id" column is what
that role resolves to only under the legacy `tcs` provider; other providers resolve differently
(e.g. Gemini, the public-deploy default, uses `gemini-flash-lite-latest` for reasoning/structured).
See [models-routing.md](models-routing.md).

| Step | Uses | Role | Historical/tcs id |
|---|---|---|---|
| Correlate | Classical ML (scikit-learn DBSCAN) | n/a | n/a |
| Enrich | Deterministic + RAG/vector search (Chroma, gateway embeddings) | n/a (embeddings pinned to `EMBEDDING_PROVIDER`) | n/a |
| Diagnose | LLM, via A2A | `reasoning` | DeepSeek R1 |
| Plan | RAG (Chroma) + LLM + deterministic guardrails | `structured` | gpt-4.1-nano |
| Policy Gate | Deterministic rule engine | n/a | n/a |
| Execute | Deterministic (audit log only) | n/a | n/a |
| Verify | Deterministic (Fake Fix Detector) | n/a | n/a |
| Sync | Deterministic | n/a | n/a |
| Knowledge | Deterministic | n/a | n/a |
| Voice/image intake scrub | Local SLM (Ollama) + regex | n/a | n/a |
| Any provider call, if that provider's endpoint is down | Local SLM offline fallback (Ollama) | n/a | n/a |
| Chat assistant intent classification | LLM | `default`/`structured` | gpt-4.1-nano |
