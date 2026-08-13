---
type: Module
title: Enrichment Agent
description: Deterministic evidence gathering across MCP-exposed simulated systems plus one real Chroma/RAG lookup for ticket-history precedent — no LLM call.
resource: backend/agents/enrichment.py
tags: [agents, evidence, rag]
status: stable
generated: { by: "claude-sonnet-5/okf-produce", at: "2026-08-11T00:00:00Z" }
sources:
  - id: enrichment-py
    resource: backend/agents/enrichment.py
    title: backend/agents/enrichment.py
    last_modified: 2026-08-11
---

# Overview

`run_enrichment(incident_id, ci_id, alerts, workflow_type)` gathers evidence by calling
[MCP tools](/tools/mcp-tool-layer.md) — CMDB facts + relationships, monitoring metric-series trend,
and for patch workflows, pending patches + change-calendar blackouts — plus one real
retrieval-augmented lookup: `orchestrator/retrieval.py`'s `query_collection("ticket_history", ...)`,
returning the top-2 nearest past tickets as "precedent" evidence, each confidence-scored from
vector distance.[^enrichment-py] No LLM call — pulling facts and doing a similarity search is not a
reasoning task, per [Model Routing](/architecture/model-routing.md).

# Evidence shape and token discipline

Every fact gets a stable `artifact_id` (e.g. `CI-0087`, `ALERT-1043`, `PATCHINV-CI-0059`) so later
agents cite it by ID rather than re-stating it. Extracts are truncated to 240 characters —
downstream agents see IDs + short extracts, never whole documents, per the tier architecture's
token-discipline strategy.

# Graceful degradation

Metrics, patch/change-calendar, and precedent lookups are each wrapped in a bare `except Exception:
pass` — a missing metric series, an unreachable patch simulator, or an unavailable Chroma/embedding
call each degrade the evidence bundle rather than crashing the whole workflow.[^enrichment-py]

# Consumers

[Diagnosis Agent](diagnosis-agent.md) receives `result["evidence"]` as its prompt input;
[Supervisor](supervisor.md) treats an empty evidence list (or a hit turn cap) as
`stopped`/`enrichment_failed`.

[^enrichment-py]: backend/agents/enrichment.py
