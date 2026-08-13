---
type: Decision
title: Two-Level Supervisor + Specialists
description: Chose a flat Supervisor-plus-specialists topology (agents never call each other directly, every result re-validated against a schema) over a deeper hierarchy, a free agent mesh, a single do-everything agent, or an off-the-shelf framework like LangGraph/CrewAI/AutoGen.
tags: [architecture, agents, orchestration]
status: stable
generated: { by: "claude-sonnet-5/okf-produce", at: "2026-08-11T00:00:00Z" }
sources:
  - id: decisions-log
    resource: .knowledge/decisions-log.md
    title: Decisions Log
    last_modified: 2026-08-07
---

# Decision

**Two-level Supervisor + specialists**, with the Supervisor re-validating every specialist's typed
result against a schema before dispatching the next agent, and specialists never calling each other
directly. See [Supervisor](/agents/supervisor.md) and [Agents](/agents/) for the implementation.

# Alternatives considered

A single do-everything agent; fully autonomous remediation with no gate; LLM-based alert
correlation; an off-the-shelf multi-agent framework (LangGraph/CrewAI/AutoGen); routing all traffic
over A2A instead of typed in-process contracts; an MCP server that itself "coordinates agents."[^decisions-log]

# Rationale

An external multi-agent failure taxonomy (MAST) attributes 44.2% of multi-agent failures to system
design and 32.3% to inter-agent misalignment. A centralized validation bottleneck — one Supervisor
that must approve every handoff — contains error amplification to roughly 4.4x versus roughly 17x
for an uncoordinated system.[^decisions-log] Framework independence and explainability were also
weighed directly against off-the-shelf orchestration frameworks: [MCP + A2A](/agents/a2a-handoff.md)
already provide the interop a framework would otherwise supply, without opaque internal routing
logic a jury (or a maintainer) can't inspect.

[^decisions-log]: Decisions Log
