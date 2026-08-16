---
type: reference
title: Architecture Overview
status: active
updated: 2026-08-16
related: [models-routing.md, api-contract.md, ../domain/../domain/domain-agents.md, ../rules-backend.md]
---

From PRD_INITIAL.md §3. Draw the tier diagram below when a juror asks — do not re-derive it.

## Tier diagram (PRD §3.5, verbatim)
```
┌──────────────────────────────────────────────────────────────────┐
│  PRESENTATION        Next.js + shadcn/ui cockpit                 │
├──────────────────────────────────────────────────────────────────┤
│  INTAKE LAYER        Alert HTTP │ Voice (Whisper) │ Image (Vision)│
│                      → one canonical MaintenanceSignal           │
│                      → SCRUBBER (always after modality convert)  │
├──────────────────────────────────────────────────────────────────┤
│  AI SOLUTION LAYER   Supervisor ── A2A ──▶ one specialist        │
│                      (others in-process, typed contracts)        │
│                      Guardrails · Policy gate · Model router     │
├──────────────────────────────────────────────────────────────────┤
│  ENTERPRISE KNOWLEDGE          │  TRANSACTIONAL SYSTEMS          │
│  Chroma: runbooks,             │  SQLite: incidents, approvals,  │
│  postmortems, history,         │  audit log, workflow state,     │
│  NEGATIVE knowledge base       │  autonomy ladder state          │
├──────────────────────────────────────────────────────────────────┤
│  TOOL / INTEGRATION LAYER — MCP servers (local, one per system)  │
│  Monitoring │ ITSM │ Tracker │ CMDB                              │
├──────────────────────────────────────────────────────────────────┤
│  SIMULATED EXTERNAL SYSTEMS (our FastAPI mocks)                  │
│  ⚠ NOT third-party SaaS. Labelled in UI and README.              │
│  (Optional §4.21: ONE real Jira Cloud portability probe, Ph. 6)  │
└──────────────────────────────────────────────────────────────────┘
   Models: TCS GenAI Lab gateway ▸ + local Ollama ▸ — no external MaaS
   Protocols: MCP (agent→tools) · A2A (agent→agent) — open specs, local endpoints
```
**Frontend note:** the Vite/React scaffold was migrated to Next.js in Phase 4 (complete, human-
confirmed 2026-08-07 — see [decisions-log.md](../decisions-log.md)). This diagram is the frozen PRD
tier design; do not edit it to relitigate that decision.

**Models note (post-submission pivot, see [decisions-log.md](../decisions-log.md)):** the single
"TCS GenAI Lab gateway" box above is the original PRD design. The as-built system
(`backend/providers.py`) instead supports 6 providers (gemini/openrouter/openai/grok/custom/tcs),
each resolved per-request via HTTP headers + a contextvar (`backend/provider_context.py`); Gemini
is the public-deploy default, TCS is a legacy/gated option reachable only on the TCS network. Local
Ollama fallback is unchanged. See [models-routing.md](models-routing.md) for the current-vs-legacy
distinction.

**Hosting note:** deployed on Render — backend as a Web Service (`opsflowapp-backend`), frontend as
a Static Site (`opsflowapp`, Next.js `output: "export"`). See [decisions-log.md](../decisions-log.md)'s
Render-only-hosting entry and `.okf/decisions/hosting-platform.md` for full detail.

## Routing principle (PRD §3.1)
Route by task shape, not model prestige:
- Deterministic? → no LLM at all (correlation, policy checks, blast radius, voice-intent parsing, metric math).
- Sensitive content? → local Ollama SLM.
- Genuine multi-step reasoning? → reasoning-role model (per active provider — see
  [models-routing.md](models-routing.md); DeepSeek R1 only under the legacy `tcs` provider), and
  only there.
Using an LLM for arithmetic or rule evaluation is the most common hackathon mistake — a juror will call it out. Full routing table: [models-routing.md](models-routing.md).

## Orchestration shape (PRD §3.4)
**Two levels only: one Supervisor + specialist agents.** Deliberately not a deep hierarchy, not a
free agent mesh. Agents never call each other directly — each returns a typed result to the
Supervisor, which validates against a schema before dispatching the next agent. Every agent has an
explicit termination condition and a turn cap.
Rationale (do not re-litigate, see [decisions-log.md](../decisions-log.md)): MAST analysis attributes
44.2% of multi-agent failures to system design, 32.3% to inter-agent misalignment; a centralised
validation bottleneck contains error amplification to ~4.4× vs ~17× uncoordinated.
Full agent chain and contracts: [domain-agents.md](../domain/domain-agents.md).

## Memory, caching, token strategy (PRD §3.6)
- **Working memory:** current workflow state in SQLite, passed as a compact typed object between agents — never the full conversation transcript.
- **Episodic memory:** closed incidents + postmortems embedded into Chroma (the feedback loop).
- **Negative memory:** rejected plans and failed remediations, embedded separately, consulted at planning time.
- **Semantic memory:** runbooks + CMDB schema.
- **Caching:** hash `(prompt_version, scrubbed_input)` → response, in SQLite. Applies to Whisper and Vision calls too, so a replayed demo screenshot doesn't re-bill the gateway.
- **Token discipline:** evidence bundles truncated to top-k cited chunks; agents see IDs + extracts, never whole documents. Per-step token budget with a hard cap.

## Protocol layer (PRD §3.8)
| Layer | Protocol | What we build |
|---|---|---|
| Agent → systems | **MCP** | Four local MCP servers (Monitoring, ITSM, Tracker, CMDB) exposing typed tools |
| Agent → agent | **A2A** | **One** Supervisor ↔ specialist handoff, real signed Agent Card. Rest stay in-process, typed |
| Future / pitch | **A2A** | Delegation-to-vendor-agents story (PRD §2.2 move 4) |

Both MCP and A2A run **locally, call nothing outbound** — this is the pre-empt line for the
gateway-vs-external distinction (PRD §0). If Phase 3 runs long: **cut the A2A implementation, keep
the argument** — "we designed for it and did not implement it in the time available" is an
acceptable answer; implying it was built when it wasn't is not.

## Trade-offs to state out loud (PRD §3.3)
- R1 costs latency (tens of seconds on a busy gateway) — runs on one step only, asynchronously, UI streams progress.
- Higher agent turn counts are not reliably better (ITBench finding) — hence hard turn caps per agent.
- Whisper/Llama Vision add latency only at intake, never in the main loop.
- Local SLMs are weaker — use only for narrow tasks (extraction, classification, redaction).
- Cost/latency is a graded artifact — log tokens and wall-clock per agent step and render it in the UI.
