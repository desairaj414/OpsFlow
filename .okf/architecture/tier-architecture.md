---
type: System
title: Tier Architecture
description: The layered system diagram (presentation, intake, AI solution, knowledge/transactional storage, tool/integration, simulated systems), the routing principle, and the two-level orchestration shape.
tags: [architecture, overview]
status: stable
generated: { by: "claude-sonnet-5/okf-produce", at: "2026-08-11T00:00:00Z" }
sources:
  - id: arch-overview
    resource: .knowledge/arch-overview.md
    title: Architecture Overview
    last_modified: 2026-08-07
---

# Overview

OpsFlow's design intent (frozen in `PRD_FINAL.md`) is six layers, top to bottom:[^arch-overview]

```
PRESENTATION        Next.js cockpit (see cockpit-ui.md)
INTAKE LAYER         Alert HTTP | Voice (Whisper) | Image (Vision)
                      -> one canonical MaintenanceSignal, scrubbed before anything downstream sees it
AI SOLUTION LAYER    Supervisor --A2A--> one specialist (Diagnosis); everything else in-process, typed
                      Guardrails . Policy gate . Model router
KNOWLEDGE/STATE      Chroma (runbooks, postmortems, ticket history, negative KB)
                      SQLite (incidents, approvals, audit log, workflow state, autonomy ladder)
TOOL/INTEGRATION     MCP servers, one per simulated system (Monitoring / ITSM / Tracker / CMDB / Patch)
SIMULATED SYSTEMS    Our own FastAPI mocks — explicitly NOT third-party SaaS, labelled as such in the UI
```

The frontend is Next.js per this frozen design (migrated from an earlier Vite/React scaffold — see
[Decisions](/decisions/) for context); the backend (Phases 0-3 of the original build) is
stack-agnostic FastAPI, async throughout.

# Routing principle

Route by task shape, not model prestige: deterministic tasks (correlation, policy checks, blast
radius, voice-intent parsing, metric math) get **no LLM at all**; sensitive free text goes to a
local Ollama SLM; only genuine multi-step reasoning over conflicting evidence gets a reasoning
model. Full technique-per-step table: [Model Routing](model-routing.md).

# Orchestration shape

**Two levels only: one Supervisor + specialist agents** — deliberately not a deep hierarchy or a
free agent mesh. Specialists never call each other directly; each returns a typed result the
Supervisor re-validates against a schema before dispatching the next one. Every agent has an
explicit termination condition and a hard turn cap. Rationale: MAST failure-taxonomy analysis
attributes 44.2% of multi-agent failures to system design and 32.3% to inter-agent misalignment — a
centralized validation bottleneck contains error amplification to roughly 4.4x vs roughly 17x for
an uncoordinated system.[^arch-overview] Full chain: [Agents](/agents/).

# Protocol layer

| Layer | Protocol | What's built |
|---|---|---|
| Agent -> systems | MCP | 5 local MCP servers (Monitoring, ITSM, Tracker, CMDB, Patch Source) exposing typed tools — see [Tools](/tools/) |
| Agent -> agent | A2A | **One** real, signed Supervisor <-> Diagnosis handoff — see [A2A Handoff](/agents/a2a-handoff.md) |

Both protocols run locally and call nothing outbound.

# Memory strategy

- **Working memory** — current workflow state in SQLite, passed as a compact typed object between
  agents, never the full conversation transcript.
- **Episodic memory** — closed incidents/postmortems embedded into Chroma.
- **Negative memory** — rejected plans and failed remediations, embedded separately, consulted at
  planning time (never a blanket filter — see [Bias Mitigation](/guardrails/bias-mitigation.md)).
- **Semantic memory** — runbooks + CMDB schema, chunked structurally (see
  [Chunking](/guardrails/chunking.md)).

[^arch-overview]: Architecture Overview
